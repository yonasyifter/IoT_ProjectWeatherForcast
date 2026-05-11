"""
crew/src/tools/voice_tool.py

Speech processing tool for the CrewAI Smart Park assistant.
Handles audio transcription via Groq Whisper and optional TTS synthesis.
"""

import os
import tempfile
import traceback
from groq import Groq

SUPPORTED_AUDIO_MIMES: dict[str, str] = {
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/mp3": "mp3",
    "audio/mpeg": "mp3",
    "audio/aiff": "aiff",
    "audio/aac": "aac",
    "audio/ogg": "ogg",
    "audio/flac": "flac",
    "audio/webm": "webm",
    "audio/mp4": "mp4",
    "video/webm": "webm",
}

MAX_AUDIO_BYTES = 25 * 1024 * 1024  # Groq Whisper limit: 25 MB

# Language → Whisper language code
LANGUAGE_CODES: dict[str, str] = {
    "en": "en",
    "it": "it",
    "fr": "fr",
    "de": "de",
    "es": "es",
    "pt": "pt",
    "ar": "ar",
    "zh": "zh",
    "ja": "ja",
    "ko": "ko",
}


def normalize_mime(mime: str | None) -> str:
    """Map a MIME type string to a file extension."""
    if not mime:
        return "wav"
    return SUPPORTED_AUDIO_MIMES.get(mime.strip().lower(), "wav")


def transcribe_audio(
    audio_bytes: bytes,
    content_type: str | None = None,
    language: str = "en",
) -> tuple[str, str | None]:
    """
    Transcribe audio bytes using Groq Whisper.

    Returns:
        (transcript_text, error_message_or_None)
    """
    if not audio_bytes:
        return "", "Audio file is empty."

    if len(audio_bytes) > MAX_AUDIO_BYTES:
        return "", "Audio file too large (max 25 MB). Please record a shorter message."

    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        return "", "GROQ_API_KEY not configured."

    ext = normalize_mime(content_type)
    whisper_lang = LANGUAGE_CODES.get(language, language)

    tmp_path: str | None = None
    try:
        client = Groq(api_key=groq_api_key)

        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as fh:
            transcription = client.audio.transcriptions.create(
                file=(f"recording.{ext}", fh.read()),
                model="whisper-large-v3-turbo",
                language=whisper_lang,
                response_format="json",
            )

        transcript = (transcription.text or "").strip()
        return transcript, None

    except Exception as exc:
        traceback.print_exc()
        return "", f"Transcription failed: {exc}"

    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
