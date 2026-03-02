# routes/tts.py
# Text-to-speech endpoint — converts agent reply text to audio using OpenAI TTS.
# Returns raw audio bytes (MP3) so the frontend can play it directly.

import logging
from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel, Field
from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)
router = APIRouter(tags=["TTS"])

# ── OpenAI client (reuse pattern from ai_service) ─────────────────────────────
_client = None
if OPENAI_API_KEY:
    try:
        from openai import OpenAI
        _client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as exc:
        logger.warning(f"TTS: OpenAI client init failed: {exc}")

VALID_VOICES = {"alloy", "echo", "fable", "onyx", "nova", "shimmer"}


class TTSRequest(BaseModel):
    text:  str         = Field(..., min_length=1, max_length=4096)
    voice: str         = Field(default="alloy")
    speed: float       = Field(default=1.0, ge=0.25, le=4.0)


@router.post("/tts", summary="Convert text to speech")
async def text_to_speech(body: TTSRequest):
    """
    Accepts text and returns an MP3 audio stream.
    The browser plays it directly via an <Audio> element.
    """
    voice = body.voice if body.voice in VALID_VOICES else "alloy"

    if _client:
        try:
            logger.info(f"TTS request: voice={voice}, len={len(body.text)}")
            response = _client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=body.text,
                speed=body.speed,
                response_format="mp3",
            )
            audio_bytes = response.content
            return Response(
                content=audio_bytes,
                media_type="audio/mpeg",
                headers={"Content-Disposition": "inline; filename=speech.mp3"},
            )
        except Exception as exc:
            logger.error(f"TTS error: {exc}")
            return Response(status_code=503, content=f"TTS unavailable: {exc}")

    # No API key — return a friendly 503
    logger.warning("TTS: No OpenAI client — returning 503")
    return Response(status_code=503, content="TTS not available: OPENAI_API_KEY not set")
