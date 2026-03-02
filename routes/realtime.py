# routes/realtime.py
# WebSocket endpoint that proxies browser ↔ OpenAI Realtime API.

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from services.realtime_service import proxy_realtime_session
from services import ai_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/realtime", tags=["Realtime"])

VOICE_MAP = {
    "neutral": "alloy",
    "male":    "echo",
    "female":  "nova",
}


@router.websocket("/ws")
async def realtime_ws(
    websocket: WebSocket,
    prompt: str   = Query(default="You are a helpful AI voice assistant. Be concise and friendly."),
    dialect: str  = Query(default="American English"),
    language: str = Query(default="en"),
    gender: str   = Query(default="neutral"),
):
    """
    WebSocket endpoint for real-time voice interaction.

    The browser connects here, streams PCM-16 audio, and receives:
    - audio_delta events (base64 PCM-16) → play through speakers
    - transcript_done events → show user transcript
    - response_text_delta events → show agent text
    """
    await websocket.accept()
    logger.info(f"Realtime WS connected | dialect={dialect}, language={language}, gender={gender}")

    # Build full system prompt with dialect/language instructions
    full_prompt = (
        f"{prompt}\n\n"
        f"Speak in {dialect}. Respond in language code: {language}. "
        f"Be conversational, warm, and concise."
    )

    voice = VOICE_MAP.get(gender, "alloy")

    # Save config so regular /agent/talk also reflects the setting
    ai_service.save_agent_config({
        "prompt": prompt,
        "dialect": dialect,
        "language": language,
        "gender": gender,
    })

    try:
        await proxy_realtime_session(websocket, system_prompt=full_prompt, voice=voice)
    except WebSocketDisconnect:
        logger.info("Realtime WS client disconnected.")
    except Exception as exc:
        logger.error(f"Realtime WS error: {exc}")
