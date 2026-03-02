# services/realtime_service.py
# Proxies a FastAPI WebSocket connection to the OpenAI Realtime API.
# The browser sends raw PCM-16 audio (base64-encoded) and receives back
# audio delta events (base64 PCM-16) plus transcript text events.

import asyncio
import json
import logging
import os

import websockets

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"


async def proxy_realtime_session(client_ws, system_prompt: str, voice: str = "alloy"):
    """
    Opens a WebSocket connection to OpenAI Realtime API and proxies audio
    between the browser client and OpenAI.

    Protocol (messages sent by browser → this function):
      { "type": "audio", "data": "<base64 PCM16 chunk>" }
      { "type": "commit" }   ← user finished speaking (optional, VAD handles it)
      { "type": "close" }    ← end session

    Messages sent back to browser:
      { "type": "audio_delta", "data": "<base64 PCM16>" }
      { "type": "transcript_delta", "text": "..." }
      { "type": "response_text_delta", "text": "..." }
      { "type": "session_ready" }
      { "type": "error", "message": "..." }
    """
    if not OPENAI_API_KEY:
        await client_ws.send_text(json.dumps({
            "type": "error",
            "message": "OPENAI_API_KEY not set on server."
        }))
        return

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "realtime=v1",
    }

    try:
        async with websockets.connect(REALTIME_URL, additional_headers=headers) as oai_ws:
            logger.info("Connected to OpenAI Realtime API")

            # ── Send session configuration ────────────────────────────────
            session_config = {
                "type": "session.update",
                "session": {
                    "modalities": ["audio", "text"],
                    "instructions": system_prompt,
                    "voice": voice,
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {
                        "model": "gpt-4o-transcribe",
                    },
                    "turn_detection": {
                        "type": "server_vad",          # auto detect end-of-speech
                        "threshold": 0.5,
                        "prefix_padding_ms": 300,
                        "silence_duration_ms": 600,
                    },
                    "temperature": 0.8,
                    "max_response_output_tokens": 4096,
                },
            }
            await oai_ws.send(json.dumps(session_config))
            logger.info("Session config sent to OpenAI")

            # Notify browser that session is ready
            await client_ws.send_text(json.dumps({"type": "session_ready"}))

            # ── Run two concurrent loops ──────────────────────────────────
            async def browser_to_openai():
                """Forward browser audio chunks → OpenAI."""
                try:
                    while True:
                        msg = await client_ws.receive_text()
                        data = json.loads(msg)

                        if data["type"] == "audio":
                            # Forward audio chunk
                            await oai_ws.send(json.dumps({
                                "type": "input_audio_buffer.append",
                                "audio": data["data"],
                            }))

                        elif data["type"] == "commit":
                            # Manually commit audio buffer and request response
                            await oai_ws.send(json.dumps({"type": "input_audio_buffer.commit"}))
                            await oai_ws.send(json.dumps({"type": "response.create"}))

                        elif data["type"] == "close":
                            break

                except Exception as e:
                    logger.error(f"browser_to_openai error: {e}")

            async def openai_to_browser():
                """Forward OpenAI events → browser."""
                try:
                    async for raw in oai_ws:
                        event = json.loads(raw)
                        etype = event.get("type", "")

                        if etype == "response.audio.delta":
                            await client_ws.send_text(json.dumps({
                                "type": "audio_delta",
                                "data": event.get("delta", ""),
                            }))

                        elif etype == "response.audio_transcript.delta":
                            await client_ws.send_text(json.dumps({
                                "type": "response_text_delta",
                                "text": event.get("delta", ""),
                            }))

                        elif etype == "conversation.item.input_audio_transcription.completed":
                            await client_ws.send_text(json.dumps({
                                "type": "transcript_done",
                                "text": event.get("transcript", ""),
                            }))

                        elif etype == "response.done":
                            await client_ws.send_text(json.dumps({"type": "response_done"}))

                        elif etype == "error":
                            logger.error(f"OpenAI Realtime error: {event}")
                            await client_ws.send_text(json.dumps({
                                "type": "error",
                                "message": event.get("error", {}).get("message", "Unknown error"),
                            }))

                except Exception as e:
                    logger.error(f"openai_to_browser error: {e}")

            await asyncio.gather(browser_to_openai(), openai_to_browser())

    except Exception as exc:
        logger.error(f"Realtime proxy error: {exc}")
        try:
            await client_ws.send_text(json.dumps({
                "type": "error",
                "message": f"Could not connect to OpenAI Realtime API: {exc}",
            }))
        except Exception:
            pass
