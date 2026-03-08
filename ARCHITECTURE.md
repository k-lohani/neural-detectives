# Architecture

## System Overview

Noir Deductions is a three-tier application with an AI agent layer that orchestrates multiple Google Gemini and Imagen models to generate, run, and voice a unique murder mystery each session.

```
┌─────────────────────────────────────────────────────────┐
│                      FRONTEND                           │
│  React 18 + Vite 5 + React Router                       │
│                                                         │
│  Home ──navigate──► CasePage                            │
│                       ├── VoicePanel (mic / text / TTS) │
│                       ├── CenterPedestal (suspects)     │
│                       ├── EntityCard[] (weapons/locs)   │
│                       ├── LogicGrid (deduction matrix)  │
│                       ├── ComicStrip (intro panels)     │
│                       └── EndGameOverlay (score)        │
│                                                         │
│  State: useGameEngine hook (no global store)            │
│  Transport: fetch (REST) + WebSocket (gameplay)         │
└──────────┬────────────────────────┬─────────────────────┘
           │ HTTP                   │ WebSocket
           ▼                        ▼
┌─────────────────────────────────────────────────────────┐
│                      BACKEND                            │
│  FastAPI + Uvicorn (async)                              │
│                                                         │
│  POST /api/game/new ──► Case Factory Agent              │
│  POST /api/game/{id}/comic-panels ──► Comic Agent       │
│  WS   /ws/game/{id} ──► Runtime Agent (per message)     │
│                                                         │
│  In-memory: active_cases, active_solvers, active_sessions│
└──────────┬────────────────────────┬─────────────────────┘
           │                        │
           ▼                        ▼
┌──────────────────┐   ┌──────────────────────────────────┐
│    MongoDB        │   │       Google AI Platform         │
│  (Motor async)    │   │                                  │
│                   │   │  Gemini 2.5 Pro                  │
│  Collections:     │   │  Gemini 2.5 Flash                │
│  • cases          │   │  Gemini 2.5 Flash TTS            │
│  • sessions       │   │  Imagen 4.0 Fast                 │
└──────────────────┘   └──────────────────────────────────┘
```

---

## AI Agentic Architecture

The backend runs three distinct AI agent workflows, each composed of one or more model calls chained together with deterministic logic.

### Agent 1: Case Factory (`agents/case_factory.py`)

Responsible for generating the complete mystery at game start.

```
                    ┌──────────────────────┐
                    │   Difficulty Input    │
                    │   (easy/medium/hard)  │
                    └──────────┬───────────┘
                               │
                               ▼
                ┌──────────────────────────────┐
                │   GEMINI 2.5 PRO             │
                │   generate_case_premise()    │
                │                              │
                │   Input: difficulty, counts   │
                │   Output (structured JSON):   │
                │   • title, premise            │
                │   • suspects[] (traits, detail)│
                │   • weapons[] (detail)        │
                │   • locations[] (detail)      │
                │   • clues[]                   │
                │   • solution (who/what/where) │
                └──────────────┬───────────────┘
                               │
                               ▼
                ┌──────────────────────────────┐
                │   IMAGEN 4.0 FAST            │
                │   generate_entity_icons()    │
                │                              │
                │   Sequential (1 per second)  │
                │   to avoid rate limits       │
                │                              │
                │   Style: "high-contrast B&W  │
                │   ink illustration, film     │
                │   noir, white lines on       │
                │   solid black background"    │
                │                              │
                │   • Suspect portraits (3:4)  │
                │   • Weapon icons (1:1)       │
                │   • Location icons (1:1)     │
                └──────────────┬───────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Case Package       │
                    │   (returned to FE)   │
                    └──────────────────────┘
```

**Comic panels** are generated separately via a background endpoint after the case page loads:

```
POST /api/game/{id}/comic-panels
        │
        ▼
┌───────────────────────┐     ┌───────────────────────┐
│  GEMINI 2.5 FLASH     │     │  IMAGEN 4.0 FAST      │
│  Plan 4 panel scenes  │────►│  Generate 4 images     │
│  (prompts + captions) │     │  (parallel, 4:3 ratio) │
└───────────────────────┘     └───────────────────────┘
```

### Agent 2: Runtime Agent (`agents/runtime.py`)

Handles every player message during gameplay. Runs as a pipeline per WebSocket message.

```
┌──────────────────┐
│  Player Message   │
│  (voice or text)  │
└────────┬─────────┘
         │
         ▼
┌────────────────────────────────────┐
│  GEMINI 2.5 FLASH                  │
│  process_voice_intent()            │
│                                    │
│  Input: transcript + entity list   │
│  Output (structured JSON):         │
│  • intent: make_deduction |        │
│    ask_question | final_accusation │
│    | ask_hint | general_chat       │
│  • extracted_relations[]           │
│  • focus_entity                    │
│  • accusation_who/what/where       │
└────────────────┬───────────────────┘
                 │
                 ▼
┌────────────────────────────────────┐
│  GRID SOLVER (deterministic)       │
│  Constraint propagation            │
│                                    │
│  • Apply extracted relations       │
│  • Propagate: 1-to-1 mapping +    │
│    transitivity rules              │
│  • Detect contradictions           │
│  • Check for unique solution       │
│    → suggested_accusation          │
└────────────────┬───────────────────┘
                 │
                 ▼
┌────────────────────────────────────┐
│  SCORING & GAME LOGIC              │
│                                    │
│  • Hint tracking (−10 pts each)    │
│  • Accusation checking (name match)│
│  • Score = 100 − hints − wrong     │
│    accusations − time penalty      │
│  • Session persistence (MongoDB)   │
└────────────────┬───────────────────┘
                 │
                 ▼
┌────────────────────────────────────┐
│  GEMINI 2.5 FLASH                  │
│  generate_louis_response()         │
│                                    │
│  Input: intent, validation         │
│         feedback, transcript       │
│  System prompt: Detective Louis    │
│         persona (hardboiled noir)  │
│  Output: 1-3 sentence response     │
└────────────────┬───────────────────┘
                 │
                 ▼
┌────────────────────────────────────┐
│  GEMINI 2.5 FLASH TTS             │
│  synthesize_detective_voice()      │
│                                    │
│  Model: gemini-2.5-flash-preview-tts│
│  Voice: Charon                     │
│  Output: PCM audio → WAV → base64 │
└────────────────┬───────────────────┘
                 │
                 ▼
┌────────────────────────────────────┐
│  WebSocket Payload                 │
│  {                                 │
│    voice_response,                 │
│    audio_base64,                   │
│    grid_update,                    │
│    focus_entity,                   │
│    suggested_accusation,           │
│    is_solved, score, solution      │
│  }                                 │
└────────────────────────────────────┘
```

### Agent 3: Grid Solver (`grid/solver.py`)

A deterministic (non-AI) constraint propagation engine that maintains the deduction state.

```
Grid: suspects × weapons × locations
Each cell: True | False | None (unknown)

Rules applied iteratively until no changes:

1. ONE-TO-ONE MAPPING
   If A=B (True), then A≠C, A≠D... for all other items in B's category
   If A≠B, A≠C, A≠D (all False except one), then A=E (the remaining one)

2. TRANSITIVITY
   If A=B and B=C → A=C
   If A=B and B≠C → A≠C

Returns False on contradiction (impossible state).
```

---

## AI Model Summary

| Model | API | Use Case | Latency |
|-------|-----|----------|---------|
| Gemini 2.5 Pro | `generate_content` (JSON schema) | Case premise generation | ~15-30s |
| Gemini 2.5 Flash | `generate_content` (JSON schema) | Intent extraction, Louis response, comic planning | ~2-5s |
| Gemini 2.5 Flash TTS | `generate_content` (audio modality) | Detective voice synthesis (Charon) | ~2-4s |
| Imagen 4.0 Fast | `generate_images` | Entity icons, comic panel images | ~3-6s each |

---

## Data Flow Diagram

```
    ┌─────────┐  POST /api/game/new   ┌──────────┐  Gemini Pro   ┌──────────┐
    │ Browser │ ─────────────────────► │ FastAPI  │ ────────────► │ Gemini   │
    │ (React) │ ◄───────────────────── │ (Python) │ ◄──────────── │ (Google) │
    └────┬────┘   case + icons         └────┬─────┘   JSON        └──────────┘
         │                                  │
         │  WebSocket                       │  Imagen 4 Fast
         │  /ws/game/{id}                   │  (sequential icons)
         │                                  │
         ▼                                  ▼
    ┌─────────┐  transcript           ┌──────────┐  insert/update  ┌──────────┐
    │  Game   │ ─────────────────────►│ WS       │ ──────────────► │ MongoDB  │
    │  Loop   │ ◄─────────────────────│ Handler  │ ◄────────────── │ (Motor)  │
    └─────────┘  grid + voice + audio └──────────┘  cases/sessions └──────────┘
```

---

## Frontend State Architecture

```
useGameEngine() — custom hook, single source of truth
│
├── Connection State
│   ├── ws (WebSocket ref)
│   ├── caseIdRef (current case)
│   └── fetchingRef (prevent double-fetch)
│
├── Game State
│   ├── caseData (full case package)
│   ├── gridState (serialized grid)
│   ├── detectiveMessage (Louis's last response)
│   ├── isCaseSolved, score, solution
│   ├── focusEntity, suggestedAccusation
│   ├── hintCount, incorrectAccusations
│   └── elapsedSeconds (timer)
│
├── Media State
│   ├── comicPanels, comicLoading
│   ├── isRecording (mic active)
│   └── isSpeaking (audio playing)
│
└── Actions
    ├── generateNewCase(difficulty)
    ├── sendTranscript(text)
    ├── submitFinalAccusation(who, what, where)
    ├── requestHint()
    └── toggleRecording()
```

---

## MongoDB Schema

### `cases` Collection

```json
{
  "case_id": "uuid",
  "difficulty": "easy",
  "title": "The Velvet Dagger Affair",
  "premise": "...",
  "suspects": [{ "id", "name", "description", "detail", "traits", "icon" }],
  "weapons": [{ "id", "name", "description", "detail", "icon" }],
  "locations": [{ "id", "name", "description", "detail", "icon" }],
  "clues": ["..."],
  "canonical_solution": { "who", "what", "where" },
  "comic_panels": [{ "image", "scene_text", "caption" }]
}
```

### `sessions` Collection

```json
{
  "session_id": "uuid (same as case_id)",
  "case_id": "uuid",
  "start_time": 1709900000,
  "hint_count": 2,
  "incorrect_accusations": 1,
  "transcript": [{ "role", "text", "time" }],
  "grid_state": { "Suspect|Weapon": true },
  "elapsed_seconds": 340,
  "is_solved": true,
  "score": 65
}
```
