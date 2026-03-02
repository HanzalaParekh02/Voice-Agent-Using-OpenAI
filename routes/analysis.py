# routes/analysis.py
# Toggle-based summary and sentiment analysis endpoint.

import logging
from fastapi import APIRouter, HTTPException
from schemas.models import AnalyzeRequest, AnalyzeResponse
from services import ai_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["Analysis"])


@router.post(
    "",
    response_model=AnalyzeResponse,
    summary="Generate summary and/or sentiment from a transcript",
)
async def analyze_transcript(body: AnalyzeRequest):
    """
    Accepts a conversation transcript and returns:
    - Summary   (if summary_enabled = true)
    - Sentiment (if sentiment_enabled = true)

    If both flags are false, returns an empty object — no OpenAI calls are made.
    """
    if not body.summary_enabled and not body.sentiment_enabled:
        logger.info("Both summary and sentiment disabled — returning empty response.")
        return AnalyzeResponse()

    if not body.transcript or not body.transcript.strip():
        raise HTTPException(status_code=422, detail="Transcript cannot be empty.")

    logger.info(f"Analysis request | summary={body.summary_enabled} | sentiment={body.sentiment_enabled}")

    summary = None
    sentiment = None

    # Only call OpenAI for what is actually enabled — saves tokens and latency
    if body.summary_enabled:
        summary = ai_service.generate_summary(body.transcript)
        logger.info("Summary generated.")

    if body.sentiment_enabled:
        sentiment = ai_service.generate_sentiment(body.transcript)
        logger.info(f"Sentiment: {sentiment}")

    return AnalyzeResponse(summary=summary, sentiment=sentiment)
