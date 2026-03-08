from google import genai
from pydantic import BaseModel, Field
from typing import List
import os
import json
import uuid
import asyncio
import base64


class GeneratedEntity(BaseModel):
    id: str
    name: str = Field(description="Creative names matching a noir mystery.")
    description: str = Field(description="Short physical and personality description.")
    detail: str = Field(description="2-3 sentences of atmospheric flavor text about this entity, subtly tied to the case. For weapons: its origin, condition, or how it was found. For locations: the mood, what's notable, who frequents it. Should contain deduction-worthy info.")

class GeneratedSuspect(GeneratedEntity):
    traits: List[str] = Field(description="A list of 2 or 3 defining characteristics (e.g., '6ft tall', 'Left-handed', 'Chain smoker', 'Gemini', 'Lover of orchids', etc.)")

class CaseGenerationOutput(BaseModel):
    title: str = Field(description="A short, catchy title for the case. e.g. 'THE MYSTERIOUS BOOKSHOP MYSTERY'")
    premise: str = Field(description="A 2-3 paragraph intriguing premise for the murder mystery. Set a dark, cinematic, soft noir vibe.")
    suspects: List[GeneratedSuspect]
    weapons: List[GeneratedEntity]
    locations: List[GeneratedEntity]
    clues: List[str] = Field(description="List of factual clues and witness statements. These MUST provide enough deduction constraints to uniquely identify the murderer, weapon, and location via elimination. MAKE EACH CLUE A SHORT, SINGLE SENTENCE.")
    solution_who: str = Field(description="The ID of the murderer suspect.")
    solution_what: str = Field(description="The ID of the murder weapon.")
    solution_where: str = Field(description="The ID of the murder location.")

class ComicPanel(BaseModel):
    image_prompt: str = Field(description="Simplified Imagen prompt (under 40 words). Start with 'soft noir comic panel, ink illustration, muted amber and shadow tones,' then describe a calm, understated scene. NO graphic violence or blood. Focus on mood: wet streets, dim lamp light, cigarette smoke, silhouettes, quiet rooms.")
    scene_text: str = Field(description="A short 1-2 sentence narrator description of what is happening in this panel (max 20 words). Written as a visual scene description, NOT character dialogue. E.g. 'Rain hammers the empty docks as fog rolls in from the bay.'")
    caption: str = Field(description="A 1-sentence hardboiled noir narrator caption for the bottom strip, 1940s voice. Understated and wry.")

class ComicSceneOutput(BaseModel):
    panels: List[ComicPanel] = Field(description="Exactly 4 comic panels telling the opening story.")


def get_genai_client():
    from dotenv import load_dotenv
    from pathlib import Path
    env_path = Path(__file__).resolve().parent.parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)

    if os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true":
        return genai.Client(
            vertexai=True,
            project=os.getenv("GOOGLE_CLOUD_PROJECT"),
            location=os.getenv("GOOGLE_CLOUD_LOCATION")
        )
    return genai.Client()


async def generate_case_premise(difficulty: str) -> dict:
    client = get_genai_client()

    counts = {"easy": 3, "medium": 4, "hard": 5}
    count = counts.get(difficulty.lower(), 3)

    prompt = f"""
    You are a master mystery writer creating a logic puzzle inspired by Murdle.
    The setting is a dark, cinematic, soft noir world.

    Create a {difficulty} murder mystery case.
    We need exactly:
    - {count} suspects
    - {count} weapons
    - {count} locations

    You must provide:
    1. A short, catchy title.
    2. For each suspect, provide 2 to 3 random traits in their 'traits' array (e.g., height, eye color, zodiac sign, handedness, hobbies, weight).
    3. For EVERY entity (suspect, weapon, location), provide a 'detail' field: 2-3 sentences of atmospheric flavor text tied to the mystery.
       - For suspects: their alibi, demeanor, what they were doing that night.
       - For weapons: its origin, condition, where it was found, any marks on it.
       - For locations: the mood, what's notable about the scene, who was last seen there.
       These details should contain subtle clue-worthy information that helps the player deduce the solution.

    CRITICAL INSTRUCTION - CLUES:
    Keep all clues very short, factual, and cryptic. EXACTLY one short sentence per clue. DO NOT make them too direct.
    Instead of saying "Beatrice was in the Study", write "A heavy cigar smell lingered in the Study" (where Beatrice has the trait 'Chain smoker'). Make the player think!
    Use the newly assigned traits to form clues that require deduction to link back to the suspect. There is exactly one murderer, using ONE weapon, at ONE location. Every other suspect is associated with exactly one other different weapon and location uniquely.
    5. The canonical solution specifying the IDs of the WHO, WHAT, and WHERE.

    Ensure the clues provide enough intersecting information to eliminate false combinations and leave only the canonical solution.
    Do NOT write paragraph-long clues. Keep them punchy and factual like: "A smudge of toxic ink was found by the front counter."
    """

    response = client.models.generate_content(
        model='gemini-2.5-pro',
        contents=prompt,
        config={
            'response_mime_type': 'application/json',
            'response_schema': CaseGenerationOutput,
        }
    )

    return json.loads(response.text)


def _generate_icon_sync(client: genai.Client, prompt: str, aspect_ratio: str = "1:1") -> str:
    """Generate a single Imagen icon synchronously. Returns base64 string."""
    try:
        response = client.models.generate_images(
            model='imagen-4.0-fast-generate-001',
            prompt=prompt,
            config={"number_of_images": 1, "aspect_ratio": aspect_ratio},
        )
        if response.generated_images:
            img_bytes = response.generated_images[0].image.image_bytes
            try:
                return img_bytes.decode('utf-8')
            except (AttributeError, UnicodeDecodeError):
                return base64.b64encode(img_bytes).decode('utf-8')
    except Exception as e:
        print(f"[Icon] ERROR generating icon: {e}")
    return ""


async def generate_entity_icons(case_package: dict):
    """
    Generate silhouette-style noir icons for all entities sequentially
    to avoid Imagen rate limits.
    """
    client = get_genai_client()
    loop = asyncio.get_event_loop()

    STYLE = "high-contrast black and white ink illustration, film noir style, white lines on solid black background, no color, no shading, clean vector art, 1940s detective aesthetic"

    entities = []
    for s in case_package.get("suspects", []):
        entities.append((s, f"{STYLE}. Portrait bust of a noir mystery character named {s['name']}. Face and shoulders only, dramatic lighting from one side.", "3:4"))
    for w in case_package.get("weapons", []):
        entities.append((w, f"{STYLE}. Single isolated object: {w['name']}. Centered on black background, simple iconic depiction.", "1:1"))
    for l in case_package.get("locations", []):
        entities.append((l, f"{STYLE}. Exterior or interior scene: {l['name']}. Simple architectural silhouette, moody atmosphere.", "1:1"))

    print(f"[Icons] Generating {len(entities)} entity icons sequentially...")
    for entity_dict, prompt, ratio in entities:
        icon_b64 = await loop.run_in_executor(None, _generate_icon_sync, client, prompt, ratio)
        entity_dict["icon"] = icon_b64
        if icon_b64:
            print(f"[Icons] Generated icon for {entity_dict['name']} ({len(icon_b64)} chars)")
        else:
            print(f"[Icons] Failed for {entity_dict['name']}")
        await asyncio.sleep(1)

    print("[Icons] Done generating entity icons.")


def _generate_single_panel_sync(client: genai.Client, scene_prompt: str) -> str:
    """Synchronous Imagen call for a comic panel."""
    try:
        response = client.models.generate_images(
            model='imagen-4.0-fast-generate-001',
            prompt=scene_prompt,
            config={"number_of_images": 1, "aspect_ratio": "4:3"},
        )
        if response.generated_images:
            img_bytes = response.generated_images[0].image.image_bytes
            try:
                return img_bytes.decode('utf-8')
            except (AttributeError, UnicodeDecodeError):
                return base64.b64encode(img_bytes).decode('utf-8')
    except Exception as e:
        print(f"[Imagen] Panel error: {e}")
    return ""


async def _generate_single_panel(client: genai.Client, scene_prompt: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _generate_single_panel_sync, client, scene_prompt)


async def generate_comic_panels(premise: str, title: str) -> list:
    """
    Generate 4 comic panel images from the premise. Called as a background task
    after the case page loads.
    """
    client = get_genai_client()

    scene_prompt = f"""
    You are an art director writing a soft noir comic strip that opens a murder mystery game.
    The tone should be calm, moody, and intriguing — like a classic detective comic, NOT a horror comic.

    For each of the 4 panels provide:
    1. image_prompt: Simple Imagen scene (under 40 words). Start with
       "soft noir comic panel, ink illustration, muted amber and shadow tones," then describe
       a calm scene. NO violence, blood, or shock. Mood over drama.
       Panel 1 = a quiet city street or the mystery location at night.
       Panel 2 = a key character — coat collar up, face half in shadow.
       Panel 3 = an empty room or a small overlooked detail — something feels off.
       Panel 4 = the detective steps in, notebook out, surveying the scene.
    2. scene_text: A short narrator description of what is visible in this panel (max 20 words).
       Describe what the viewer SEES — no character speech, no dialogue. Pure visual narration.
    3. caption: One punchy hardboiled narrator sentence for the bottom caption strip (1940s voice).

    Mystery Title: {title}
    Premise: {premise}
    """

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=scene_prompt,
        config={
            'response_mime_type': 'application/json',
            'response_schema': ComicSceneOutput,
        }
    )

    scenes_data = json.loads(response.text)
    panel_data = scenes_data.get("panels", [])[:4]

    if not panel_data:
        print("No panel data generated.")
        return []

    print(f"Generating {len(panel_data)} comic panel images in parallel...")
    panel_tasks = [_generate_single_panel(client, p["image_prompt"]) for p in panel_data]
    images = await asyncio.gather(*panel_tasks)

    result = []
    for img_b64, panel in zip(images, panel_data):
        if img_b64:
            result.append({
                "image": img_b64,
                "scene_text": panel["scene_text"],
                "caption": panel["caption"],
            })
    return result


async def build_new_case_workflow(difficulty: str) -> dict:
    """
    Orchestrates case generation:
    1. Generate premise + entities via Gemini
    2. Generate entity icons sequentially via Imagen
    3. Return case immediately (comic panels generated separately via background endpoint)
    """
    generated_data = await generate_case_premise(difficulty)

    case_id = str(uuid.uuid4())

    case_package = {
        "case_id": case_id,
        "difficulty": difficulty,
        "title": generated_data.get("title", "The Mystery"),
        "premise": generated_data["premise"],
        "suspects": generated_data["suspects"],
        "weapons": generated_data["weapons"],
        "locations": generated_data["locations"],
        "clues": generated_data["clues"],
        "canonical_solution": {
            "who": generated_data["solution_who"],
            "what": generated_data["solution_what"],
            "where": generated_data["solution_where"]
        },
        "canonical_grid_solution": {},
        "comic_panels": [],
    }

    await generate_entity_icons(case_package)

    return case_package
