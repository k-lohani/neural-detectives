from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import base64
import struct

from schemas.session import SessionState

class ExtractedRelation(BaseModel):
    item1: str = Field(description="The first entity (e.g., suspect name, weapon, or location).")
    item2: str = Field(description="The second entity related to item1.")
    is_positive: bool = Field(description="True if the user asserts they are linked, False if they assert they are NOT linked.")

class UserIntentExtraction(BaseModel):
    intent: str = Field(description="Enum: 'make_deduction', 'ask_question', 'final_accusation', 'ask_hint', 'general_chat'.")
    referenced_entities: List[str] = Field(description="List of exact names of suspects, weapons, or locations mentioned by the user.")
    extracted_relations: List[ExtractedRelation] = Field(description="Any logical deductions the user is trying to make for the grid.")
    focus_entity: Optional[str] = Field(default=None, description="If the user is asking about or focusing on a specific entity, its exact name from the available entities list. Used to highlight it in the UI.")
    accusation_who: Optional[str] = None
    accusation_what: Optional[str] = None
    accusation_where: Optional[str] = None

def get_genai_client():
    # Load from the parent directory of 'neural-detectives'
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

async def process_voice_intent(session: SessionState, user_transcript: str, case_package: dict) -> dict:
    """
    Takes the player's transcript, extracts entity references, intent, and possible grid deductions.
    Returns structured data detailing the analysis to ground Detective Louis.
    """
    client = get_genai_client()
    
    # We provide the available entities so the LLM knows what to map to
    available_entities = [s["name"] for s in case_package.get("suspects", [])] + \
                         [w["name"] for w in case_package.get("weapons", [])] + \
                         [l["name"] for l in case_package.get("locations", [])]

    prompt = f"""
    You are the rigorous logic engine for a murder mystery game.
    Available entities in this case: {', '.join(available_entities)}
    
    User transcript: "{user_transcript}"
    
    Task: Extract the user's intent, the entities they mentioned, and any logical relations they are trying to assert for the deduction grid.

    INTENT VALUES:
    - "make_deduction": The user is asserting a logical relation (X was/wasn't at Y).
    - "ask_question": The user is asking about a suspect, weapon, or location.
    - "final_accusation": The user is making a final guess (WHO did it with WHAT in WHERE).
    - "ask_hint": The user is explicitly requesting a hint or clue ("give me a hint", "I need help", "any hints?").
    - "general_chat": Anything else.

    FOCUS_ENTITY: If the user asks about or mentions a specific entity ("tell me about Victor", "what about the knife"), set focus_entity to the EXACT matching name from the available entities list.
    
    CRITICAL ACCURACY RULES for ExtractedRelations:
    1. Only use EXACT names from the "Available entities" list for item1 and item2.
    2. If the user says "the letter opener was on the roof", item1 must be the exact Weapon name (e.g., "Antique Letter Opener") and item2 must be the exact Location name (e.g., "The Rooftop Terrace").
    3. Do not invent entities. 
    
    If they are making a final accusation, populate the accusation fields.
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config={
            'response_mime_type': 'application/json',
            'response_schema': UserIntentExtraction,
        }
    )
    
    import json
    return json.loads(response.text)

def synthesize_detective_voice(text: str) -> str:
    """Use Gemini's native TTS to voice Detective Louis."""
    try:
        client = get_genai_client()
        response = client.models.generate_content(
            model='gemini-2.5-flash-preview-tts',
            contents=f'Say in a deep, grizzled, world-weary detective voice: {text}',
            config=types.GenerateContentConfig(
                response_modalities=['AUDIO'],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name='Charon',
                        )
                    )
                ),
            )
        )
        raw_data = response.candidates[0].content.parts[0].inline_data.data

        # Vertex AI returns audio bytes as pre-encoded base64 text — decode to get raw PCM
        try:
            pcm_data = base64.b64decode(raw_data.decode('utf-8'))
        except (UnicodeDecodeError, AttributeError):
            pcm_data = raw_data

        # Wrap raw PCM (24kHz, 16-bit, mono) in a WAV header so the browser can play it
        data_size = len(pcm_data)
        wav_header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF', 36 + data_size, b'WAVE',
            b'fmt ', 16, 1, 1, 24000,
            24000 * 1 * 16 // 8, 1 * 16 // 8, 16,
            b'data', data_size,
        )
        return base64.b64encode(wav_header + pcm_data).decode('utf-8')
    except Exception as e:
        print(f"Gemini TTS Error: {e}")
        return ""

async def generate_louis_response(session: SessionState, intent_data: dict, validation_feedback: str, user_transcript: str) -> dict:
    """
    Generates the final voice reply for Detective Louis based on retrieved context.
    """
    client = get_genai_client()
    
    system_prompt = """
    You are Detective Louis, a grizzled, deep-voiced Noir detective solving a murder puzzle with the user.
    Vary your responses to feel like a natural conversation. If it's a simple deduction, give a short, blunt 1-sentence confirmation. If they ask a deeper question or make a major deduction, give a slightly more detailed (but still very direct and hardboiled) 2-3 sentence response.
    Never be overly verbose. Stay in character.
    Do NOT give away the final answers. Guide the user based on the validation feedback.
    If validation_feedback says a deduction contradicts the facts, point it out bluntly.
    """
    
    context = f"User Intent: {intent_data.get('intent')}\nSystem Validation Feedback: {validation_feedback}\nUser Transcript: {user_transcript}"
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=f"{system_prompt}\n\n{context}",
    )
    
    text_content = response.text
    audio_b64 = synthesize_detective_voice(text_content)
    
    return {"text": text_content, "audio_b64": audio_b64}

