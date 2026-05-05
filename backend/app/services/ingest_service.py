"""
Document ingestion service.
"""

import json
from pathlib import Path

from backend.app.core.config import UPLOAD_DIR
from backend.app.db.database import get_db
from rag.pipeline import RAGPipeline


class IngestService:
    """Handles document upload and ingestion into the RAG pipeline."""

    def __init__(self, rag_pipeline: RAGPipeline):
        self.rag = rag_pipeline

    def ingest_file(self, file_path: str, title: str = None) -> dict:
        """
        Ingest a document file into the system.

        Steps:
            1. RAG pipeline: parse → chunk → embed → index
            2. Save metadata to SQLite (using chunks already in pipeline)
        """
        path = Path(file_path)
        title = title or path.stem

        # Capture chunk count before ingestion to compute new chunks added
        old_count = (
            self.rag.embedding_manager.index.ntotal
            if self.rag.embedding_manager.index is not None else 0
        )

        # Ingest via RAG pipeline (handles load + chunk + embed + index)
        result = self.rag.ingest_document(file_path)

        # Get the newly added chunks from the embedding manager
        new_chunk_count = result["chunks"]
        new_chunks = self.rag.embedding_manager.chunks[-new_chunk_count:]

        # Save document metadata to DB
        with get_db() as conn:
            cursor = conn.execute(
                """INSERT OR REPLACE INTO documents
                   (title, filename, source_type, page_count, chunk_count)
                   VALUES (?, ?, ?, ?, ?)""",
                (title, path.name, path.suffix.lstrip("."),
                 result["pages"], new_chunk_count),
            )
            doc_id = cursor.lastrowid

            for chunk in new_chunks:
                conn.execute(
                    """INSERT OR REPLACE INTO chunks
                       (document_id, chunk_id, chunk_index, text, page_number,
                        char_count, metadata_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        doc_id, chunk.chunk_id, chunk.chunk_index, chunk.text,
                        chunk.page_number, len(chunk.text),
                        json.dumps(chunk.metadata, ensure_ascii=False),
                    ),
                )

        result["title"] = title
        result["document_id"] = doc_id
        return result

    def list_documents(self) -> list[dict]:
        """List all ingested documents."""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM documents ORDER BY upload_date DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_document(self, doc_id: int) -> bool:
        """Mark a document as deleted (soft delete)."""
        with get_db() as conn:
            conn.execute(
                "UPDATE documents SET status = 'deleted' WHERE id = ?", (doc_id,)
            )
        return True
