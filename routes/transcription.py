# routes/transcription.py
# Standalone transcription endpoint.
# Accepts a raw audio file upload (multipart/form-data) or base64 text body.

import logging
import base64
from fastapi import APIRouter, File, UploadFile, HTTPException
from schemas.models import TranscribeResponse
from services import ai_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/transcribe", tags=["Transcription"])


@router.post(
    "",
    response_model=TranscribeResponse,
    summary="Transcribe an uploaded audio file",
)
async def transcribe_audio_file(file: UploadFile = File(...)):
    """
    Accepts an audio file upload (e.g. .webm, .mp3, .wav, .m4a).
    Converts it to base64 and passes it to the transcription service.
    Falls back to a mock transcript if OpenAI Whisper is unavailable.
    """
    logger.info(f"Transcription request: filename={file.filename}, content_type={file.content_type}")

    # Validate file type loosely
    allowed_types = {"audio/webm", "audio/mpeg", "audio/wav", "audio/mp4", "audio/ogg", "audio/m4a"}
    if file.content_type and file.content_type not in allowed_types:
        logger.warning(f"Unexpected content_type: {file.content_type} — proceeding anyway.")

    try:
        raw_bytes = await file.read()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read uploaded file: {exc}")

    # Encode to base64 so it fits the existing service interface
    b64_audio = base64.b64encode(raw_bytes).decode("utf-8")

    transcript, source = ai_service.transcribe_audio(b64_audio)

    return TranscribeResponse(transcript=transcript, source=source)
