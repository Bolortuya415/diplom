"""
FastAPI route definitions.
"""

import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Form

from backend.app.schemas.schemas import (
    ChatRequest, ChatResponse, FeedbackRequest, FeedbackResponse,
    IngestResponse, HealthResponse, DocumentInfo,
)
from backend.app.core.config import UPLOAD_DIR
from backend.app.db.database import get_db

# These will be set by main.py on startup
chat_service = None
ingest_service = None

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint.
    Receives a question, runs safety check + RAG, returns answer with citations.
    """
    if chat_service is None:
        raise HTTPException(503, "Service not initialized")

    result = chat_service.process_query(request.message, category=request.category)

    return ChatResponse(
        answer=result["answer"],
        sources=result.get("sources", []),
        safety={
            "label": result["safety"]["label"],
            "confidence": result["safety"]["confidence"],
            "is_safe": result["safety"]["is_safe"],
        },
        chat_id=result["chat_id"],
        response_time_ms=result["response_time_ms"],
        model_used=result.get("model_used", ""),
    )


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest):
    """Submit user feedback (thumbs up/down) for a chat response."""
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO feedback (chat_id, rating, comment) VALUES (?, ?, ?)",
            (request.chat_id, request.rating, request.comment),
        )
    return FeedbackResponse(feedback_id=cursor.lastrowid)


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
):
    """
    Upload and ingest a document into the RAG pipeline.
    Supports PDF and TXT files.
    """
    if ingest_service is None:
        raise HTTPException(503, "Service not initialized")

    # Validate file type
    allowed = {".pdf", ".txt"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed:
        raise HTTPException(400, f"Unsupported file type: {suffix}. Allowed: {allowed}")

    # Save uploaded file
    save_path = UPLOAD_DIR / file.filename
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        result = ingest_service.ingest_file(str(save_path), title=title)
        return IngestResponse(
            filename=file.filename,
            pages=result["pages"],
            chunks=result["chunks"],
            total_index_size=result["total_index_size"],
        )
    except Exception as e:
        raise HTTPException(500, f"Ingestion failed: {str(e)}")


@router.get("/documents", response_model=list[DocumentInfo])
async def list_documents():
    """List all ingested documents."""
    if ingest_service is None:
        raise HTTPException(503, "Service not initialized")
    docs = ingest_service.list_documents()
    return docs


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: int):
    """Soft-delete a document."""
    if ingest_service is None:
        raise HTTPException(503, "Service not initialized")
    ingest_service.delete_document(doc_id)
    return {"status": "deleted", "document_id": doc_id}


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """System health check."""
    index_loaded = (
        chat_service is not None
        and chat_service.rag is not None
        and chat_service.rag.is_ready
    )
    total_chunks = 0
    if index_loaded:
        total_chunks = chat_service.rag.embedding_manager.index.ntotal

    with get_db() as conn:
        doc_count = conn.execute(
            "SELECT COUNT(*) FROM documents WHERE status='active'"
        ).fetchone()[0]

    classifier_loaded = chat_service is not None and chat_service.classifier is not None

    return HealthResponse(
        status="healthy",
        index_loaded=index_loaded,
        total_chunks=total_chunks,
        total_documents=doc_count,
        classifier_loaded=classifier_loaded,
    )


@router.get("/stats")
async def get_stats():
    """Get usage statistics for the admin dashboard."""
    with get_db() as conn:
        total_chats = conn.execute("SELECT COUNT(*) FROM chat_logs").fetchone()[0]
        total_feedback = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
        positive_feedback = conn.execute(
            "SELECT COUNT(*) FROM feedback WHERE rating = 1"
        ).fetchone()[0]
        unsafe_queries = conn.execute(
            "SELECT COUNT(*) FROM chat_logs WHERE safety_label != 'safe'"
        ).fetchone()[0]
        avg_response_time = conn.execute(
            "SELECT AVG(response_time_ms) FROM chat_logs"
        ).fetchone()[0]

    return {
        "total_chats": total_chats,
        "total_feedback": total_feedback,
        "positive_feedback": positive_feedback,
        "negative_feedback": total_feedback - positive_feedback,
        "unsafe_queries": unsafe_queries,
        "avg_response_time_ms": round(avg_response_time or 0, 1),
    }
