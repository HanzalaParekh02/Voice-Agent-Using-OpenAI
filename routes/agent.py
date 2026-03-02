# routes/agent.py
# Endpoints for agent configuration and voice interaction.

import logging
from fastapi import APIRouter
from schemas.models import (
    AgentConfigRequest,
    AgentConfigResponse,
    TalkRequest,
    TalkResponse,
)
from services import ai_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["Agent"])


# ── POST /agent/configure ─────────────────────────────────────────────────────

@router.post(
    "/configure",
    response_model=AgentConfigResponse,
    summary="Configure the AI voice agent",
)
async def configure_agent(config: AgentConfigRequest):
    """
    Stores the agent configuration in memory (PoC).
    Accepts dialect, language, gender, and the final merged prompt
    (niche template + any user edits from the frontend prompt box).
    """
    logger.info(f"Configuring agent: dialect={config.dialect}, language={config.language}, gender={config.gender}")

    # Save config to in-memory store in ai_service
    ai_service.save_agent_config(config.model_dump())

    return AgentConfigResponse(
        status="success",
        message="Agent configured successfully. Ready to accept voice interactions.",
        config=config,
    )


# ── POST /agent/talk ──────────────────────────────────────────────────────────

@router.post(
    "/talk",
    response_model=TalkResponse,
    summary="Send audio or text input and receive agent response",
)
async def talk_to_agent(body: TalkRequest):
    """
    Main voice interaction endpoint.
    - Accepts base64 audio OR plain mock text (PoC friendly).
    - Transcribes the input (or passes through mock text).
    - Generates an AI agent response using the configured prompt.
    - Optionally returns summary and/or sentiment if enabled.
    """
    logger.info(
        "Talk request received | summary=%s | sentiment=%s | kb_url=%s",
        body.enable_summary,
        body.enable_sentiment,
        getattr(body, "knowledge_base_url", None),
    )

    # Step 1: Transcribe (or pass through mock text)
    transcript, _ = ai_service.transcribe_audio(body.audio_input)
    logger.info(f"Transcript: {transcript[:80]}...")

    # Step 2: Generate agent response (optionally grounded in external knowledge base URL)
    agent_reply = ai_service.generate_agent_response(
        transcript,
        knowledge_base_url=body.knowledge_base_url,
    )

    # Step 3: Optionally run summary and/or sentiment on the transcript
    summary = None
    sentiment = None

    if body.enable_summary:
        summary = ai_service.generate_summary(transcript)

    if body.enable_sentiment:
        sentiment = ai_service.generate_sentiment(transcript)

    return TalkResponse(
        transcript=transcript,
        agent_response_text=agent_reply,
        summary=summary,
        sentiment=sentiment,
    )
