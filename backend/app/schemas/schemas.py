"""
Pydantic schemas for API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Chat ──

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User question in Mongolian")
    category: Optional[str] = Field(None, description="Topic category: gender_equality, discrimination, disability")


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
    rating: int = Field(..., ge=-1, le=1, description="1 = thumbs up, -1 = thumbs down")
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    status: str = "ok"
    feedback_id: int


# ── Document Ingestion ──

class IngestResponse(BaseModel):
    filename: str
    pages: int
    chunks: int
    total_index_size: int
    status: str = "ok"


# ── Health ──

class HealthResponse(BaseModel):
    status: str
    index_loaded: bool
    total_chunks: int
    total_documents: int
    classifier_loaded: bool


# ── Document List ──

class DocumentInfo(BaseModel):
    id: int
    title: str
    filename: str
    source_type: str
    upload_date: str
    page_count: int
    chunk_count: int
    status: str
