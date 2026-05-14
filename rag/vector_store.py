"""
Vector store backed by ChromaDB with BGE-M3 embeddings and optional reranking.

Replaces the previous FAISS-based EmbeddingManager. Same public surface
(build_index / add_to_index / search / load / save) so the rest of the
pipeline doesn't need to know which backend is in use.

Key changes vs. the FAISS version:
    - ChromaDB persists automatically (no pickle file for chunks).
    - Per-chunk `topic` metadata enables filtered retrieval by category
      (gender_equality / discrimination / disability / general).
    - BGE-M3 embeddings (1024-dim) are noticeably stronger on Mongolian
      Cyrillic than the prior MiniLM model.
    - BGE-reranker-v2-m3 cross-encodes (query, chunk) pairs to lift the
      truly relevant chunks before the LLM sees them.

FAQ behaviour preserved:
    - FAQ chunks are embedded using the question text only, so user
      questions hit them with higher similarity.
    - An additive score boost still promotes FAQ matches above generic
      document chunks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from rag.chunker import Chunk
from rag.config import RAGConfig


_FAQ_SCORE_BOOST = 0.12

# Topic inference from filename. Mongolian + English keywords.
_TOPIC_KEYWORDS: dict[str, tuple[str, ...]] = {
    "gender_equality": (
        "gender", "жендэр", "хүйс", "тэгш эрх", "тэгш_эрх",
        "эмэгтэйчүүд", "gender_equality",
    ),
    "discrimination": (
        "discrimination", "ялгаварлан", "discrim", "гадуурх",
    ),
    "disability": (
        "disability", "хөгжлийн бэрхшээл", "хөгжлийн_бэрхшээл",
        "бэрхшээлтэй", "disabled",
    ),
}


def infer_topic(source_file: str) -> str:
    """Return one of: gender_equality, discrimination, disability, general."""
    name = source_file.lower()
    for topic, keywords in _TOPIC_KEYWORDS.items():
        if any(kw in name for kw in keywords):
            return topic
    return "general"


def _flatten_metadata(chunk: Chunk) -> dict:
    """Build the flat metadata dict that ChromaDB will store for a chunk."""
    raw = chunk.metadata or {}
    flat: dict = {
        "source_file": chunk.source_file,
        "page_number": int(chunk.page_number or 0),
        "chunk_index": int(chunk.chunk_index),
        "topic": infer_topic(chunk.source_file),
    }
    # Pull in primitive metadata keys; skip anything non-primitive.
    for k, v in raw.items():
        if isinstance(v, (str, int, float, bool)):
            flat[k] = v
    return flat


class VectorStore:
    """ChromaDB-backed vector store with BGE-M3 embeddings + reranker."""

    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self._embedder: Optional[SentenceTransformer] = None
        self._reranker = None  # lazy CrossEncoder

        # Persistent Chroma client — data survives restarts under
        # data/vectors/chroma/.
        persist_dir = Path(self.config.chroma_persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        # get_or_create gives us the collection on both fresh installs and
        # subsequent runs without branching.
        self._collection = self._client.get_or_create_collection(
            name=self.config.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )

        # In-session chunk list — used by IngestService to fetch the most
        # recently added chunks for SQLite logging.
        self.chunks: list[Chunk] = []

    # ── Lazy model loaders ────────────────────────────────────────────

    @property
    def embedder(self) -> SentenceTransformer:
        if self._embedder is None:
            print(f"Loading embedding model: {self.config.embedding_model}")
            self._embedder = SentenceTransformer(self.config.embedding_model)
        return self._embedder

    @property
    def reranker(self):
        if not self.config.use_reranker:
            return None
        if self._reranker is None:
            from sentence_transformers import CrossEncoder
            print(f"Loading reranker: {self.config.reranker_model}")
            self._reranker = CrossEncoder(self.config.reranker_model)
        return self._reranker

    # ── Index size (replaces FAISS `.index.ntotal`) ──────────────────

    @property
    def count(self) -> int:
        return int(self._collection.count())

    # ── Embedding helpers ────────────────────────────────────────────

    @staticmethod
    def _embed_text_for_chunk(chunk: Chunk) -> str:
        """For FAQ chunks, embed the question only; otherwise the chunk text."""
        meta = chunk.metadata or {}
        if meta.get("is_faq") and meta.get("faq_question"):
            return meta["faq_question"]
        return chunk.text

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors = self.embedder.encode(
            texts,
            normalize_embeddings=True,
            batch_size=16,
            show_progress_bar=len(texts) > 8,
        )
        return [v.tolist() for v in vectors]

    def _embed_query(self, query: str) -> list[float]:
        vec = self.embedder.encode([query], normalize_embeddings=True)[0]
        return vec.tolist()

    # ── Index population ─────────────────────────────────────────────

    def build_index(self, chunks: list[Chunk]) -> None:
        """Add the initial batch of chunks to the collection."""
        self._upsert_chunks(chunks)

    def add_to_index(self, chunks: list[Chunk]) -> None:
        """Append more chunks to an existing collection."""
        self._upsert_chunks(chunks)

    def _upsert_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return

        embed_texts = [self._embed_text_for_chunk(c) for c in chunks]
        embeddings = self._embed_texts(embed_texts)

        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = [_flatten_metadata(c) for c in chunks]

        # upsert (rather than add) so re-ingesting a document doesn't error
        # on duplicate ids.
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        self.chunks.extend(chunks)
        print(f"Indexed {len(chunks)} chunks. Total in collection: {self.count}")

    # ── Search ────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        topic: Optional[str] = None,
    ) -> list[dict]:
        """
        Retrieve relevant chunks. Returns a list of dicts shaped like:
            { chunk_id, text, source_file, page_number, score, metadata }

        Pipeline:
            1. Fetch a wider candidate pool from Chroma (4× top_k, min 16).
            2. Optionally rerank with BGE-reranker-v2-m3.
            3. Apply additive FAQ score boost and final ranking.
            4. Return top_k.
        """
        if self.count == 0:
            return []

        k = top_k or self.config.top_k
        fetch_k = min(max(k * 4, 16), self.count)

        query_embedding = self._embed_query(query)

        where = {"topic": topic} if topic else None

        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=fetch_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        candidates: list[dict] = []
        for chunk_id, doc, meta, dist in zip(ids, documents, metadatas, distances):
            # Chroma with cosine: similarity = 1 - distance
            similarity = max(0.0, min(1.0, 1.0 - float(dist)))
            if similarity < self.config.similarity_threshold:
                continue
            candidates.append({
                "chunk_id": chunk_id,
                "text": doc,
                "source_file": (meta or {}).get("source_file", "unknown"),
                "page_number": (meta or {}).get("page_number", 0),
                "score": similarity,
                "metadata": meta or {},
            })

        if not candidates:
            return []

        # ── Reranker pass ───────────────────────────────────────────
        # Cross-encode (query, doc) pairs and re-score. Replaces the
        # cosine similarity with the reranker's score so downstream
        # ranking reflects true relevance, not just vector closeness.
        if self.reranker is not None and len(candidates) > 1:
            pairs = [(query, c["text"]) for c in candidates]
            rerank_scores = self.reranker.predict(pairs)
            for c, s in zip(candidates, rerank_scores):
                # BGE reranker outputs sigmoid logits — clamp to [0,1] for
                # consistency with cosine scores.
                c["score"] = max(0.0, min(1.0, float(s)))

        # ── FAQ boost + final sort ──────────────────────────────────
        for c in candidates:
            if (c.get("metadata") or {}).get("is_faq"):
                c["score"] = min(1.0, c["score"] + _FAQ_SCORE_BOOST)

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:k]

    # ── Persistence (kept for API compatibility with FAISS code) ─────
    # ChromaDB writes on every operation, so these are effectively no-ops.

    def save(self) -> None:
        # PersistentClient flushes on each write; nothing to do here.
        pass

    def load(self) -> bool:
        """Return True if a non-empty collection already exists."""
        return self.count > 0

    # ── Maintenance helpers ──────────────────────────────────────────

    def delete_by_source(self, source_file: str) -> int:
        """Remove all chunks belonging to a given source filename."""
        existing = self._collection.get(
            where={"source_file": source_file},
            include=[],
        )
        ids = existing.get("ids") or []
        if ids:
            self._collection.delete(ids=ids)
        return len(ids)

    def reset(self) -> None:
        """Drop and recreate the collection. Used for full re-ingest."""
        self._client.delete_collection(name=self.config.chroma_collection)
        self._collection = self._client.get_or_create_collection(
            name=self.config.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )
        self.chunks = []
