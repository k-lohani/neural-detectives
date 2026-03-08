import json
import time
import uuid
from typing import Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from database import get_database, close_database_connection
import os
import uvicorn

from schemas.session import SessionState
from agents.runtime import process_voice_intent, generate_louis_response
from grid.solver import GridSolver
from agents.case_factory import build_new_case_workflow, generate_comic_panels

app = FastAPI(title="Noir Deductions API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_db_client():
    get_database()

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_database_connection()

@app.get("/")
async def root():
    return {"message": "Welcome to Noir Deductions API"}


# ── In-memory stores (prototype) ──
active_solvers: Dict[str, GridSolver] = {}
active_cases: Dict[str, dict] = {}
active_sessions: Dict[str, dict] = {}


def _find_best_match(name: str, options) -> str:
    name_lower = name.lower()
    for option in options:
        if name_lower in option.lower() or option.lower() in name_lower:
            return option
    return name


def _find_entity_by_name(name: str, entities: list) -> Optional[dict]:
    """Fuzzy-match an entity name to its dict in the list."""
    name_lower = name.lower()
    for e in entities:
        if name_lower in e["name"].lower() or e["name"].lower() in name_lower:
            return e
        if name_lower == e["id"].lower():
            return e
    return None


def _check_accusation(case_data: dict, who: str, what: str, where: str) -> bool:
    """Compare accusation by name OR ID against the canonical solution."""
    sol = case_data.get("canonical_solution", {})
    all_entities = case_data.get("suspects", []) + case_data.get("weapons", []) + case_data.get("locations", [])

    def matches(value, sol_id):
        if not value:
            return False
        if value == sol_id:
            return True
        entity = _find_entity_by_name(value, all_entities)
        return entity is not None and entity["id"] == sol_id

    return (matches(who, sol["who"]) and
            matches(what, sol["what"]) and
            matches(where, sol["where"]))


def _compute_score(session: dict) -> int:
    elapsed_minutes = session.get("elapsed_seconds", 0) / 60.0
    hints = session.get("hint_count", 0)
    wrong = session.get("incorrect_accusations", 0)
    score = 100 - (hints * 10) - (wrong * 15) - int(elapsed_minutes * 2)
    return max(0, score)


def _extract_suggested_accusation(solver: GridSolver, case_data: dict) -> Optional[dict]:
    """If the grid has a unique solution, return {who, what, where} names."""
    suspects = [s["name"] for s in case_data.get("suspects", [])]
    weapons = [w["name"] for w in case_data.get("weapons", [])]
    locations = [l["name"] for l in case_data.get("locations", [])]

    who = what = where = None
    for s in suspects:
        for w in weapons:
            if solver.get_relation(s, w) is True:
                for l in locations:
                    if solver.get_relation(s, l) is True and solver.get_relation(w, l) is True:
                        who, what, where = s, w, l
                        break

    if who and what and where:
        return {"who": who, "what": what, "where": where}
    return None


@app.post("/api/game/new")
async def start_new_game(difficulty: str = "easy"):
    case_package = await build_new_case_workflow(difficulty)

    case_id = case_package["case_id"]

    try:
        db_doc = json.loads(json.dumps(case_package))
        for entity_list in ("suspects", "weapons", "locations"):
            for e in db_doc.get(entity_list, []):
                e.pop("icon", None)
        db_doc.pop("comic_panels", None)
        db = get_database()
        await db["cases"].insert_one(db_doc)
    except Exception as e:
        print(f"[DB] Could not persist case to MongoDB: {e}")
    active_cases[case_id] = case_package

    suspects = [s["name"] for s in case_package["suspects"]]
    weapons = [w["name"] for w in case_package["weapons"]]
    locations = [l["name"] for l in case_package["locations"]]
    active_solvers[case_id] = GridSolver(suspects, weapons, locations)

    return {"status": "success", "case_id": case_id, "case": case_package}


@app.post("/api/game/{case_id}/comic-panels")
async def generate_comic_panels_background(case_id: str):
    """Background endpoint: generate comic panels for an existing case."""
    case_data = active_cases.get(case_id)
    if not case_data:
        db = get_database()
        case_data = await db["cases"].find_one({"case_id": case_id})
        if case_data:
            case_data.pop("_id", None)
        else:
            return {"error": "Case not found"}

    if case_data.get("comic_panels"):
        return {"comic_panels": case_data["comic_panels"]}

    panels = await generate_comic_panels(
        case_data["premise"],
        case_data.get("title", "The Mystery")
    )

    case_data["comic_panels"] = panels
    if case_id in active_cases:
        active_cases[case_id]["comic_panels"] = panels

    try:
        metadata_only = [
            {"scene_text": p.get("scene_text", ""), "caption": p.get("caption", "")}
            for p in panels
        ]
        db = get_database()
        await db["cases"].update_one(
            {"case_id": case_id},
            {"$set": {"comic_panels_meta": metadata_only}}
        )
    except Exception as e:
        print(f"[Comic] Skipped DB persist (too large): {e}")

    return {"comic_panels": panels}


@app.websocket("/ws/game/{session_id}")
async def game_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()

    solver = active_solvers.get(session_id)
    case_data = active_cases.get(session_id)

    if not case_data:
        db = get_database()
        case_data = await db["cases"].find_one({"case_id": session_id})
        if case_data:
            case_data.pop("_id", None)
            active_cases[session_id] = case_data

            suspects = [s["name"] for s in case_data.get("suspects", [])]
            weapons = [w["name"] for w in case_data.get("weapons", [])]
            locations = [l["name"] for l in case_data.get("locations", [])]
            solver = GridSolver(suspects, weapons, locations)
            active_solvers[session_id] = solver
        else:
            await websocket.send_text(json.dumps({"error": "No active case data found for this session."}))
            return

    # Initialize session tracking
    session = active_sessions.get(session_id)
    if not session:
        session = {
            "session_id": session_id,
            "case_id": session_id,
            "start_time": time.time(),
            "hint_count": 0,
            "incorrect_accusations": 0,
            "transcript": [],
            "is_solved": False,
            "score": None,
            "elapsed_seconds": 0,
        }
        active_sessions[session_id] = session

        db = get_database()
        await db["sessions"].insert_one({k: v for k, v in session.items()})

    try:
        while True:
            raw_text = await websocket.receive_text()
            data = json.loads(raw_text)

            user_transcript = data.get("transcript", "")
            session["transcript"].append({"role": "user", "text": user_transcript, "time": time.time()})
            session["elapsed_seconds"] = time.time() - session["start_time"]

            # 1. Process Voice Intent via Gemini
            intent_data = await process_voice_intent(None, user_transcript, case_data)

            # 2. Apply deductions to GridSolver
            validation_feedback = "The grid has been successfully updated with the deductions."

            if intent_data.get("extracted_relations"):
                for rel in intent_data["extracted_relations"]:
                    item1 = rel.get("item1")
                    item2 = rel.get("item2")
                    is_pos = rel.get("is_positive")

                    if item1 and item2:
                        item1_match = _find_best_match(item1, solver.item_to_cat.keys())
                        item2_match = _find_best_match(item2, solver.item_to_cat.keys())

                        try:
                            success = solver.set_relation(item1_match, item2_match, is_pos)
                            if not success:
                                validation_feedback = f"Wait, {item1_match} and {item2_match} being linked as {is_pos} contradicts previous facts on our grid."
                                break
                        except KeyError:
                            validation_feedback = f"I'm not sure which suspect, weapon, or location you mean by {item1} or {item2}."

            # 3. Handle hints
            is_hint = intent_data.get("intent") == "ask_hint"
            if is_hint:
                session["hint_count"] += 1
                hint_penalty = session["hint_count"] * 10
                validation_feedback = f"The user is asking for a hint. Give them a subtle nudge based on the clues without revealing the answer. Mention that this hint costs them points (penalty so far: {hint_penalty} points)."

            # 4. Handle accusations
            is_solved = False
            if intent_data.get("intent") == "final_accusation":
                who = intent_data.get("accusation_who", "")
                what = intent_data.get("accusation_what", "")
                where = intent_data.get("accusation_where", "")

                if _check_accusation(case_data, who, what, where):
                    is_solved = True
                    session["is_solved"] = True
                    session["elapsed_seconds"] = time.time() - session["start_time"]
                    session["score"] = _compute_score(session)
                    validation_feedback = "The user has solved the case correctly!"
                else:
                    session["incorrect_accusations"] += 1
                    validation_feedback = "The user has made an incorrect final accusation. Remind them gently that they need to review the facts."

            # 5. Generate Detective Louis response
            louis_response_data = await generate_louis_response(None, intent_data, validation_feedback, user_transcript)
            louis_text = louis_response_data.get("text", "")
            louis_audio = louis_response_data.get("audio_b64", "")

            session["transcript"].append({"role": "louis", "text": louis_text, "time": time.time()})

            # 6. Build payload
            serializable_grid = {f"{k[0]}|{k[1]}": v for k, v in solver.grid.items()}

            payload = {
                "type": "game_update",
                "voice_response": louis_text,
                "audio_base64": louis_audio,
                "grid_update": serializable_grid,
                "is_solved": is_solved,
                "focus_entity": intent_data.get("focus_entity"),
                "hint_count": session["hint_count"],
                "incorrect_accusations": session["incorrect_accusations"],
                "elapsed_seconds": int(session["elapsed_seconds"]),
            }

            if is_solved:
                payload["score"] = session["score"]
                sol = case_data.get("canonical_solution", {})
                payload["solution"] = {
                    "who": _find_entity_by_name(sol["who"], case_data["suspects"]) or {"name": sol["who"]},
                    "what": _find_entity_by_name(sol["what"], case_data["weapons"]) or {"name": sol["what"]},
                    "where": _find_entity_by_name(sol["where"], case_data["locations"]) or {"name": sol["where"]},
                }

            suggested = _extract_suggested_accusation(solver, case_data)
            if suggested:
                payload["suggested_accusation"] = suggested

            await websocket.send_text(json.dumps(payload))

            # Persist session to DB
            db = get_database()
            await db["sessions"].update_one(
                {"session_id": session_id},
                {"$set": {
                    "transcript": session["transcript"],
                    "hint_count": session["hint_count"],
                    "incorrect_accusations": session["incorrect_accusations"],
                    "elapsed_seconds": int(session["elapsed_seconds"]),
                    "is_solved": session["is_solved"],
                    "score": session["score"],
                    "grid_state": serializable_grid,
                }},
                upsert=True
            )

    except WebSocketDisconnect:
        print(f"Client disconnected from session {session_id}")
    except Exception as e:
        print(f"WebSocket Error: {e}")
        try:
            await websocket.send_text(json.dumps({"error": str(e)}))
        except Exception:
            pass

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
