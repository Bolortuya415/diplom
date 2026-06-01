"""
FastAPI application entry point for Boloroo chatbot.

Thesis note:
    FastAPI was chosen for its async support, automatic OpenAPI documentation,
    built-in validation with Pydantic, and excellent performance. The application
    follows a modular service pattern: routes delegate to services, which
    orchestrate business logic across the classifier, RAG pipeline, and database.
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Force UTF-8 on stdout/stderr so the chat service's print() of Cyrillic
# query text does not raise UnicodeEncodeError under Windows cp1252.
# Must happen before any module that uses print() is imported.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.core.config import (
    CORS_ORIGINS, DEBUG, HOST, PORT,
    GEMINI_MODEL, TOP_K, CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL,
)
from backend.app.db.database import init_db
from backend.app.api import routes
from backend.app.services.chat_service import ChatService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    print("Starting Boloroo chatbot backend...")

    # Initialize database
    init_db()

    # Initialize shared RAG pipeline — values forwarded from backend config
    # so a single .env controls both layers.
    from rag.pipeline import RAGPipeline
    from rag.config import RAGConfig
    rag = RAGPipeline(config=RAGConfig(
        llm_model=GEMINI_MODEL,
        top_k=TOP_K,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        embedding_model=EMBEDDING_MODEL,
    ))
    rag.initialize()

    # Initialize chat service (uses RAG + LLM generator)
    chat_svc = ChatService()
    chat_svc.initialize_with_rag(rag)

    # Inject into routes
    routes.chat_service = chat_svc

    print("Backend ready.")
    yield

    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title="Boloroo — Хүйсийн тэгш байдлын чатбот",
    description="RAG-based chatbot for gender equality and social inclusion in Mongolian",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(routes.router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=HOST, port=PORT, reload=DEBUG)
