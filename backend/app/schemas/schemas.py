"""
Pydantic schemas for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Chat ──

class HistoryMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User question in Mongolian")
    category: Optional[str] = Field(None, description="Topic category: gender_equality, discrimination, disability")
    history: list[HistoryMessage] = Field(default_factory=list, description="Recent conversation turns (oldest first), capped client-side")


class SourceCitation(BaseModel):
    ref_number: int
    source_file: str
    document_title: Optional[str] = None
    page_number: Optional[int] = None
    snippet: str
    relevance_score: float
    law_references: list[str] = []


class SafetyInfo(BaseModel):
    label: str
    confidence: float
    is_safe: bool


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceCitation] = []
    safety: SafetyInfo
    chat_id: int
    response_time_ms: int
    model_used: str = ""


# ── Feedback ──

class FeedbackRequest(BaseModel):
    chat_id: int
    rating: int = Field(..., ge=1, le=5, description="Likert rating from 1 (worst) to 5 (best)")
    comment: Optional[str] = None
    session_id: Optional[str] = Field(
        None, max_length=128,
        description="Optional client-generated session/conversation ID",
    )


class FeedbackResponse(BaseModel):
    status: str = "ok"
    feedback_id: int


# ── Health ──

class HealthResponse(BaseModel):
    status: str
    index_loaded: bool
    total_chunks: int
    total_documents: int
    classifier_loaded: bool
