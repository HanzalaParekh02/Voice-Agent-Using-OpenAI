# services/ai_service.py
# Wraps all OpenAI API calls.
# Falls back to mock responses if OPENAI_API_KEY is not set,
# making the PoC fully runnable offline.

import logging
import base64
import urllib.request
import urllib.error
from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

from openai import OpenAI

_client = OpenAI(api_key=OPENAI_API_KEY)


# ── In-memory agent config store (PoC) ───────────────────────────────────────
_agent_config: dict = {}

# Soft limit for how much external knowledge base text we pass into the model.
_MAX_KB_CHARS = 4000


def save_agent_config(config: dict) -> None:
    """Persist agent configuration in memory."""
    global _agent_config
    _agent_config = config
    logger.info(f"Agent config saved: {config}")


def get_agent_config() -> dict:
    """Retrieve the current agent configuration."""
    return _agent_config


# ── Chat / Response ───────────────────────────────────────────────────────────

def _fetch_knowledge_base(url: str) -> str:
    """
    Fetch text content from a URL to use as an external knowledge base.
    This is intentionally lightweight and avoids extra dependencies.
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        logger.warning("Rejected knowledge base URL with disallowed scheme: %s", url)
        return ""

    if len(url) > 2048:
        logger.warning("Rejected knowledge base URL that is too long.")
        return ""

    try:
        logger.info(f"Fetching knowledge base content from URL: {url}")
        with urllib.request.urlopen(url, timeout=10) as resp:
            content_type = resp.headers.get_content_type()
            raw_bytes = resp.read()

            # Decode as text if possible
            if content_type.startswith("text/"):
                encoding = resp.headers.get_content_charset() or "utf-8"
                text = raw_bytes.decode(encoding, errors="ignore")
            else:
                return (
                    f"External resource at {url} could not be converted to plain text. "
                    f"Content-Type was '{content_type}'."
                )

        # If it looks like HTML, strip tags in a very naive way
        lower = text.lower()
        if "<html" in lower:
            import re

            body_match = re.search(
                r"<body[^>]*>(.*?)</body>", text, flags=re.IGNORECASE | re.DOTALL
            )
            if body_match:
                text = body_match.group(1)
            # Strip all remaining tags
            text = re.sub(r"<[^>]+>", " ", text)

        # Normalise whitespace and truncate
        text = " ".join(text.split())
        if len(text) > _MAX_KB_CHARS:
            text = text[:_MAX_KB_CHARS] + " ..."

        return text
    except Exception as exc:
        logger.error(f"Failed to fetch knowledge base from {url}: {exc}")
        return ""


def generate_agent_response(transcript: str, knowledge_base_url: str | None = None) -> str:
    """
    Send the user transcript to GPT and return the agent's reply.
    """
    config = get_agent_config()
    system_prompt = config.get(
        "prompt",
        "You are a helpful AI voice agent. Be concise and professional.",
    )

    # If a language was configured for the agent (e.g. Arabic, Urdu),
    # append a directive so the model always answers in that language.
    language = config.get("language")
    if language:
        system_prompt = (
            f"{system_prompt}\n\n"
            f"When responding to the user, always reply in this language: {language}."
        )

    kb_text = ""
    if knowledge_base_url:
        kb_text = _fetch_knowledge_base(knowledge_base_url)

    try:
        logger.info("Sending transcript to OpenAI Chat API.")

        messages = [
            {"role": "system", "content": system_prompt},
        ]

        if kb_text:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "The following external knowledge base content was provided by the user. "
                        "Use it as the primary source of truth when relevant to their query:\n\n"
                        f"{kb_text}"
                    ),
                }
            )

        messages.append({"role": "user", "content": transcript})

        completion = _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=300,
            temperature=0.7,
        )
        return completion.choices[0].message.content.strip()
    except Exception as exc:
        logger.error(f"OpenAI chat error: {exc}")
        raise


# ── Transcription ─────────────────────────────────────────────────────────────

def transcribe_audio(audio_input: str) -> tuple[str, str]:
    """
    Transcribe base64 audio using OpenAI Whisper.
    If the input looks like plain text (PoC mock), return it directly.
    Returns (transcript_text, source_label).
    """
    try:
        logger.info("Transcribing audio with OpenAI gpt-4o-transcribe.")
        audio_bytes = base64.b64decode(audio_input)

        # gpt-4o-transcribe requires a file-like object with filename hint
        import io
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.webm"

        result = _client.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=audio_file,
        )
        return result.text.strip(), "gpt-4o-transcribe"
    except Exception as exc:
        logger.error(f"Whisper transcription error: {exc}")
        raise


# ── Summary & Sentiment ───────────────────────────────────────────────────────

def generate_summary(transcript: str) -> str:
    """Summarise a conversation transcript using GPT."""
    try:
        logger.info("Generating summary via OpenAI.")
        completion = _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful assistant. "
                        "Summarise the following conversation transcript in 2-3 concise sentences."
                    ),
                },
                {"role": "user", "content": transcript},
            ],
            max_tokens=150,
            temperature=0.3,
        )
        return completion.choices[0].message.content.strip()
    except Exception as exc:
        logger.error(f"Summary generation error: {exc}")
        raise


def generate_sentiment(transcript: str) -> str:
    """Analyse sentiment of a conversation transcript using GPT."""
    try:
        logger.info("Analysing sentiment via OpenAI.")
        completion = _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a sentiment analysis assistant. "
                        "Analyse the following conversation and respond with exactly one word: "
                        "Positive, Negative, or Neutral."
                    ),
                },
                {"role": "user", "content": transcript},
            ],
            max_tokens=10,
            temperature=0,
        )
        raw = completion.choices[0].message.content.strip()
        for label in ("Positive", "Negative", "Neutral"):
            if label.lower() in raw.lower():
                return label
        return raw
    except Exception as exc:
        logger.error(f"Sentiment analysis error: {exc}")
        raise
