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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.core.config import (
    CORS_ORIGINS, DEBUG, HOST, PORT,
    LLM_MODEL, TOP_K, CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL,
)
from backend.app.db.database import init_db
from backend.app.api import routes
from backend.app.services.chat_service import ChatService
from backend.app.services.ingest_service import IngestService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    print("Starting Boloroo chatbot backend...")

    # Initialize database
    init_db()

    # Initialize shared RAG pipeline — config values come from .env
    from rag.pipeline import RAGPipeline
    from rag.config import RAGConfig
    rag = RAGPipeline(config=RAGConfig(
        llm_model=LLM_MODEL,
        top_k=TOP_K,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        embedding_model=EMBEDDING_MODEL,
    ))
    rag.initialize()

    # Initialize chat service (uses RAG + classifier + LLM generator)
    chat_svc = ChatService()
    chat_svc.initialize_with_rag(rag)

    # Initialize ingest service (uses RAG only, no LLM)
    ingest_svc = IngestService(rag)

    # Inject into routes
    routes.chat_service = chat_svc
    routes.ingest_service = ingest_svc

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
