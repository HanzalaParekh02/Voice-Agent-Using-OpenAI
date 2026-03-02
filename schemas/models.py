# schemas/models.py
# All Pydantic request and response models used across the API

from pydantic import BaseModel, Field
from typing import Optional


# ──────────────────────────────────────────────
# Niche Schemas
# ──────────────────────────────────────────────

class NichePromptResponse(BaseModel):
    niche: str
    prompt_template: str


class NicheListResponse(BaseModel):
    niches: list[str]


# ──────────────────────────────────────────────
# Agent Configuration Schemas
# ──────────────────────────────────────────────

class AgentConfigRequest(BaseModel):
    dialect: str = Field(..., example="US")
    language: str = Field(..., example="English")
    gender: str = Field(..., example="Male")
    prompt: str = Field(..., example="You are a professional AI voice agent...")


class AgentConfigResponse(BaseModel):
    status: str
    message: str
    config: AgentConfigRequest


# ──────────────────────────────────────────────
# Voice Interaction Schemas
# ──────────────────────────────────────────────

class TalkRequest(BaseModel):
    audio_input: str = Field(
        ...,
        description="Base64 encoded audio OR plain mock text for PoC",
        example="Hello, I want to know about your pricing plans.",
    )
    enable_summary: bool = Field(default=False)
    enable_sentiment: bool = Field(default=False)
    knowledge_base_url: Optional[str] = Field(
        default=None,
        description="Optional URL to use as an external knowledge base for grounding the agent's response.",
        example="https://example.com/your-product-docs",
    )


class TalkResponse(BaseModel):
    transcript: str
    agent_response_text: str
    summary: Optional[str] = None
    sentiment: Optional[str] = None


# ──────────────────────────────────────────────
# Transcription Schemas
# ──────────────────────────────────────────────

class TranscribeResponse(BaseModel):
    transcript: str
    source: str = Field(description="'openai_whisper' or 'mock'")


# ──────────────────────────────────────────────
# Analysis Schemas
# ──────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    transcript: str = Field(..., example="The customer was very happy with the pricing...")
    summary_enabled: bool = True
    sentiment_enabled: bool = True


class AnalyzeResponse(BaseModel):
    summary: Optional[str] = None
    sentiment: Optional[str] = None
