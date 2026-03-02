# main.py
# ─────────────────────────────────────────────────────────────────────────────
# Voice Intelligent Platform — Backend (PoC)
# FastAPI entry point: registers middleware, routers, and global exception handler.
# ─────────────────────────────────────────────────────────────────────────────

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import APP_VERSION
from routes import niches, agent, transcription, analysis, realtime, tts

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Rate Limiter (slowapi) ────────────────────────────────────────────────────
# Default: 60 requests per minute per IP.
# Swap the limit string to tighten/loosen in production.
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


# ── Lifespan (startup / shutdown hook) ───────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 AI Voice Agent Backend starting up...")
    yield
    logger.info("🛑 AI Voice Agent Backend shutting down.")


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Voice Intelligent Platform API",
    description=(
        "PoC backend for an AI Voice Agent supporting niche prompt templates, "
        "agent configuration, voice interaction, transcription, summary, and sentiment analysis."
    ),
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Attach rate-limiter state and error handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── CORS ──────────────────────────────────────────────────────────────────────
# Allow all origins for PoC. Lock down to specific origins in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # CRA / other common ports
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    logger.info(f"→ {request.method} {request.url.path}")
    response = await call_next(request)
    elapsed = (time.perf_counter() - start) * 1000
    logger.info(f"← {request.method} {request.url.path} | {response.status_code} | {elapsed:.1f}ms")
    return response


# ── Global exception handler ──────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )


# ── Register routers ──────────────────────────────────────────────────────────
app.include_router(niches.router)
app.include_router(agent.router)
app.include_router(transcription.router)
app.include_router(analysis.router)
app.include_router(realtime.router)
app.include_router(tts.router)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"], summary="Health check")
async def root():
    """
    Simple health check endpoint.
    Returns app status and version — useful for uptime monitors and load balancers.
    """
    return {
        "message": "AI Voice Agent Backend Running",
        "version": APP_VERSION,
        "docs": "/docs",
    }
