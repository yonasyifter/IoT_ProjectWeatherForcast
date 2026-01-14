# routes/rag.py
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from google import genai
from google.genai import types
import os
import json

router = APIRouter()

# Use the async client to avoid blocking FastAPI
aclient = genai.Client(api_key=os.getenv("GEMINI_API_KEY")).aio

SUPPORTED_AUDIO_MIMES = {
    "audio/wav": "audio/wav",
    "audio/x-wav": "audio/wav",
    "audio/mp3": "audio/mp3",
    "audio/mpeg": "audio/mp3",   # common upload type for mp3 -> normalize
    "audio/aiff": "audio/aiff",
    "audio/aac": "audio/aac",
    "audio/ogg": "audio/ogg",
    "audio/flac": "audio/flac",
}

def _normalize_audio_mime(mime: str | None) -> str:
    if not mime:
        return "audio/wav"
    mime = mime.strip().lower()
    return SUPPORTED_AUDIO_MIMES.get(mime, mime)  # keep original if unknown

def _build_sensor_context(device_data: str) -> str:
    try:
        data_list = json.loads(device_data)
        if not isinstance(data_list, list):
            raise ValueError("device_data must be a JSON array")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid device_data JSON: {e}")

    lines = []
    for d in data_list:
        if not isinstance(d, dict):
            continue
        lines.append(
            f"Zone: {d.get('device_id')}, "
            f"Temp: {d.get('temperature')}°C, "
            f"Hum: {d.get('humidity')}%"
        )
    return "PARK SENSOR DATA:\n" + ("\n".join(lines) if lines else "(no sensor rows provided)")

@router.post("/chat")
async def process_rag_request(
    user_query: str = Form(None),     # optional if audio is sent
    device_data: str = Form(...),     # required JSON string
    audio_file: UploadFile = File(None),
):
    try:
        context_str = _build_sensor_context(device_data)

        if not user_query and not audio_file:
            raise HTTPException(status_code=400, detail="Send either user_query or audio_file.")

        # If audio exists, read it once
        audio_part = None
        if audio_file:
            audio_bytes = await audio_file.read()
            if not audio_bytes:
                raise HTTPException(status_code=400, detail="audio_file is empty.")

            # Inline audio requests have a total size limit; keep a safety margin
            if len(audio_bytes) > 18 * 1024 * 1024:
                raise HTTPException(
                    status_code=413,
                    detail="Audio too large for inline prompt. Send a smaller clip or use the Files API.",
                )

            mime = _normalize_audio_mime(audio_file.content_type)
            audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime)

        # Prompt: ALWAYS request transcript when audio is present
        # (text first, then audio) to match recommended examples
        if audio_part:
            user_prompt = (
                "1) Transcribe exactly what the user says in the audio.\n"
                "2) Then answer the user's question.\n"
                "If the audio has no clear speech, set transcript to an empty string and ask the user to repeat.\n"
            )
        else:
            user_prompt = user_query

        # Output schema: force JSON with transcript + answer
        response_schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "transcript": types.Schema(
                    type=types.Type.STRING,
                    description="Speech-to-text transcription of the user's audio. Empty if no intelligible speech.",
                ),
                "answer": types.Schema(
                    type=types.Type.STRING,
                    description="Assistant answer to the user's question.",
                ),
            },
            required=["transcript", "answer"],
        )

        system_instruction = f"""
You are a Dual-Mode AI Assistant for a Smart Park.
You may receive audio and/or text.

GROUNDING DATA (authoritative for park weather questions):
{context_str}

RULES:
- If the user asks about park weather/conditions (temperature/humidity by zone): use ONLY the grounding data above.
- If data is missing for a zone, say: "I don't have sensor data there, but generally..."
- If the user is chatting or asking general questions: answer normally.
- Return JSON that matches the required schema.
"""

        parts = [types.Part.from_text(user_prompt)]
        if user_query and not audio_part:
            # user_query already used as user_prompt; nothing else to add
            pass
        if audio_part:
            parts.append(audio_part)
        if user_query and audio_part:
            # If both are provided, include the text too (after the instruction, before audio is also ok,
            # but we keep it simple and explicit)
            parts.insert(1, types.Part.from_text(f"User text (if any): {user_query}"))

        response = await aclient.models.generate_content(
            model="gemini-2.5-flash",
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=response_schema,
            ),
        )

        # response.text should be JSON because of response_mime_type + schema
        try:
            payload = json.loads(response.text)
        except Exception:
            # Fallback: still return raw text if something unexpected happens
            payload = {"transcript": "", "answer": response.text}

        return payload

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
