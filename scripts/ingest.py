"""
Document ingestion script.

Loads documents, chunks text, generates BGE-M3 embeddings, and stores
them in ChromaDB. Does NOT require any LLM API key — embeddings run
locally via sentence-transformers.

Usage:
    python scripts/ingest.py
    python scripts/ingest.py path/to/specific/file.pdf
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rag.pipeline import RAGPipeline
from rag.config import RAGConfig
from backend.app.db.database import init_db


def main():
    init_db()

    # RAGConfig resolves Chroma's persist directory under the project
    # root, so this script works regardless of the current working dir.
    config = RAGConfig()
    pipeline = RAGPipeline(config=config)  # No LLM API key needed for ingestion
    pipeline.initialize()

    if len(sys.argv) > 1:
        # Ingest specific file
        file_path = sys.argv[1]
        print(f"Ingesting: {file_path}")
        result = pipeline.ingest_document(file_path)
        print(f"Done: {result}")
    else:
        # Ingest all from data/raw/
        raw_dir = PROJECT_ROOT / "data" / "raw"
        if not raw_dir.exists() or not any(raw_dir.iterdir()):
            print(f"No documents found in {raw_dir}")
            print("Place PDF or TXT files in data/raw/ and run again.")
            return

        results = pipeline.ingest_directory(str(raw_dir))
        for r in results:
            if "error" in r:
                print(f"  ERROR: {r['file']}: {r['error']}")
            else:
                print(f"  OK: {r['file']} — {r['pages']} pages, {r['chunks']} chunks")

        print(f"\nTotal index size: {pipeline.vector_store.count} vectors")


if __name__ == "__main__":
    main()
