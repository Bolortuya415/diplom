"""
RAG retrieval pipeline — document ingestion and vector search.

This module handles ONLY the retrieval side:
    load → chunk → embed → index → search

Answer generation (LLM) is handled separately by rag/generator.py
and orchestrated by the ChatService in the backend.

Thesis note:
    Separating retrieval from generation follows the standard RAG
    architecture. This allows document ingestion to run offline
    without an LLM API key, and makes each component independently
    testable.
"""

import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.config import RAGConfig
from rag.document_loader import load_document
from rag.chunker import chunk_documents
from rag.embeddings import EmbeddingManager


class RAGPipeline:
    """Retrieval pipeline: ingestion + vector search. No LLM dependency."""

    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self.embedding_manager = EmbeddingManager(self.config)
        self._initialized = False

    def initialize(self) -> bool:
        """Load existing FAISS index from disk if available."""
        loaded = self.embedding_manager.load()
        self._initialized = loaded
        return loaded

    @property
    def is_ready(self) -> bool:
        """Check if the pipeline has a loaded index."""
        return self._initialized and self.embedding_manager.index is not None

    def ingest_document(self, file_path: str) -> dict:
        """
        Ingest a single document: load → chunk → embed → index → save.
        No LLM or OpenAI API required.
        """
        # Load
        pages = load_document(file_path)
        print(f"Loaded {len(pages)} pages from {file_path}")

        # Chunk
        chunks = chunk_documents(
            pages,
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )
        print(f"Created {len(chunks)} chunks")

        # Add to index
        if self._initialized:
            self.embedding_manager.add_to_index(chunks)
        else:
            self.embedding_manager.build_index(chunks)
            self._initialized = True

        # Save
        self.embedding_manager.save()

        return {
            "file": Path(file_path).name,
            "pages": len(pages),
            "chunks": len(chunks),
            "total_index_size": self.embedding_manager.index.ntotal,
        }

    def ingest_directory(self, dir_path: str) -> list[dict]:
        """Ingest all supported documents from a directory."""
        results = []
        path = Path(dir_path)

        for file_path in sorted(path.glob("*")):
            if file_path.suffix.lower() in (".pdf", ".txt"):
                try:
                    result = self.ingest_document(str(file_path))
                    results.append(result)
                except Exception as e:
                    results.append({"file": file_path.name, "error": str(e)})

        return results

    def search(self, query: str, top_k: int = None) -> list[dict]:
        """
        Search for chunks relevant to a query.

        Returns list of dicts with: chunk_id, text, source_file, page_number, score, metadata
        """
        if not self.is_ready:
            return []
        return self.embedding_manager.search(query, top_k=top_k)
