"""
FastAPI route definitions.

The chatbot is read-only against a pre-built corpus. Corpus ingestion
happens offline via scripts/ingest.py — there are no runtime admin
endpoints.
"""

from fastapi import APIRouter, HTTPException

from backend.app.schemas.schemas import (
    ChatRequest, ChatResponse, FeedbackRequest, FeedbackResponse,
    HealthResponse,
)
from backend.app.db.database import get_db

# Set by main.py on startup
chat_service = None

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint.
    Receives a question, runs safety check + RAG, returns answer with citations.
    """
    if chat_service is None:
        raise HTTPException(503, "Service not initialized")

    history = [
        {"role": m.role, "content": m.content}
        for m in (request.history or [])
        if m.role in ("user", "assistant") and (m.content or "").strip()
    ]
    try:
        result = chat_service.process_query(
            request.message, category=request.category, history=history
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"{type(e).__name__}: {e}")

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
    """
    Submit a 1-5 Likert rating for a chat response.

    The feedback row links to chat_logs via chat_id, so the user's
    question, the bot's answer and the original timestamp are
    recoverable via JOIN. An optional client-generated session_id
    groups multiple feedback rows from the same conversation.
    """
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO feedback (chat_id, rating, comment, session_id)
               VALUES (?, ?, ?, ?)""",
            (request.chat_id, request.rating, request.comment, request.session_id),
        )
    return FeedbackResponse(feedback_id=cursor.lastrowid)


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
        total_chunks = chat_service.rag.vector_store.count

    with get_db() as conn:
        doc_count = conn.execute(
            "SELECT COUNT(*) FROM documents WHERE status='active'"
        ).fetchone()[0]

    # `classifier_loaded` is kept in the response schema for back-compat
    # but always False — the trained classifier was removed and the LLM
    # now handles relevance and safety decisions.
    return HealthResponse(
        status="healthy",
        index_loaded=index_loaded,
        total_chunks=total_chunks,
        total_documents=doc_count,
        classifier_loaded=False,
    )
