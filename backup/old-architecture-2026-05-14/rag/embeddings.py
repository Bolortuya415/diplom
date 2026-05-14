"""
Embedding generation and FAISS index management.

Thesis note:
    We use the paraphrase-multilingual-MiniLM-L12-v2 model from
    sentence-transformers. This model supports 50+ languages including
    Mongolian, produces 384-dimensional embeddings, and is small enough
    to run on a laptop CPU. FAISS (Facebook AI Similarity Search) provides
    efficient nearest-neighbor search over the embedding vectors.

    FAQ chunks are indexed using their question text only (not the full
    Q+A block). This makes user queries match FAQ questions with higher
    cosine similarity than they would against the combined block.
    An additive score boost (_FAQ_SCORE_BOOST) further promotes FAQ
    chunks in the re-ranked result list.
"""

import pickle
from pathlib import Path
from typing import Optional

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from rag.chunker import Chunk
from rag.config import RAGConfig

# Additive score boost applied to FAQ chunks after FAISS retrieval.
# Keeps them ranked above generic document chunks when scores are close.
_FAQ_SCORE_BOOST = 0.12


class EmbeddingManager:
    """Manages embedding generation and FAISS index operations."""

    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self.model = SentenceTransformer(self.config.embedding_model)
        self.index: Optional[faiss.IndexFlatIP] = None
        self.chunks: list[Chunk] = []

    def _embed_text_for_chunk(self, chunk: Chunk) -> str:
        """
        Return the text that should be embedded for this chunk.

        For FAQ chunks, embed the question text only so that user queries
        (which resemble questions) achieve higher cosine similarity.
        The full Q+A block is stored in chunk.text for display purposes.
        """
        meta = chunk.metadata or {}
        if meta.get("is_faq") and meta.get("faq_question"):
            return meta["faq_question"]
        return chunk.text

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        embeddings = self.model.encode(
            texts,
            show_progress_bar=True,
            normalize_embeddings=True,
            batch_size=32,
        )
        return embeddings.astype("float32")

    def embed_query(self, query: str) -> np.ndarray:
        """Generate embedding for a single query."""
        embedding = self.model.encode(
            [query],
            normalize_embeddings=True,
        )
        return embedding.astype("float32")

    def build_index(self, chunks: list[Chunk]) -> faiss.IndexFlatIP:
        """
        Build a FAISS index from document chunks.

        Uses IndexFlatIP (inner product) with normalized vectors,
        which is equivalent to cosine similarity.
        FAQ chunks are indexed by their question text for better query matching.
        """
        self.chunks = chunks
        texts = [self._embed_text_for_chunk(c) for c in chunks]
        embeddings = self.embed_texts(texts)

        # Using inner product (cosine similarity with normalized vectors)
        self.index = faiss.IndexFlatIP(self.config.embedding_dimension)
        self.index.add(embeddings)

        print(f"FAISS index built: {self.index.ntotal} vectors, "
              f"dimension={self.config.embedding_dimension}")

        return self.index

    def add_to_index(self, new_chunks: list[Chunk]):
        """Add new chunks to an existing index."""
        if self.index is None:
            return self.build_index(new_chunks)

        texts = [self._embed_text_for_chunk(c) for c in new_chunks]
        embeddings = self.embed_texts(texts)
        self.index.add(embeddings)
        self.chunks.extend(new_chunks)

    def search(self, query: str, top_k: int = None) -> list[dict]:
        """
        Search the index for chunks similar to the query.

        Fetches a wider candidate pool (4× top_k, min 8) so that FAQ
        chunks are not pushed out by generic document chunks before
        re-ranking. FAQ chunks receive an additive score boost and are
        sorted to the top when their question closely matches the query.

        Returns a list of dicts with chunk data and similarity scores.
        """
        if self.index is None or self.index.ntotal == 0:
            return []

        k = top_k or self.config.top_k
        # Fetch more candidates so FAQ re-ranking has material to work with
        fetch_k = min(max(k * 4, 8), self.index.ntotal)

        query_embedding = self.embed_query(query)
        scores, indices = self.index.search(query_embedding, fetch_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue
            if score < self.config.similarity_threshold:
                continue

            chunk = self.chunks[idx]
            meta = chunk.metadata or {}
            boosted_score = float(score)
            if meta.get("is_faq"):
                boosted_score = min(1.0, boosted_score + _FAQ_SCORE_BOOST)

            results.append({
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "source_file": chunk.source_file,
                "page_number": chunk.page_number,
                "score": boosted_score,
                "metadata": chunk.metadata,
            })

        # Re-rank by boosted score so FAQ entries surface above generic chunks
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:k]

    def save(self, index_path: str = None, chunks_path: str = None):
        """Save the FAISS index and chunk metadata to disk."""
        idx_path = Path(index_path or self.config.vector_index_path)
        chk_path = Path(chunks_path or self.config.chunk_metadata_path)

        idx_path.parent.mkdir(parents=True, exist_ok=True)
        chk_path.parent.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self.index, str(idx_path))
        with open(chk_path, "wb") as f:
            pickle.dump(self.chunks, f)

        print(f"Index saved to: {idx_path}")
        print(f"Chunks saved to: {chk_path}")

    def load(self, index_path: str = None, chunks_path: str = None):
        """Load a previously saved FAISS index and chunk metadata."""
        idx_path = Path(index_path or self.config.vector_index_path)
        chk_path = Path(chunks_path or self.config.chunk_metadata_path)

        if not idx_path.exists() or not chk_path.exists():
            print("No saved index found. Build an index first.")
            return False

        self.index = faiss.read_index(str(idx_path))
        with open(chk_path, "rb") as f:
            self.chunks = pickle.load(f)

        print(f"Loaded index: {self.index.ntotal} vectors, {len(self.chunks)} chunks")
        return True
