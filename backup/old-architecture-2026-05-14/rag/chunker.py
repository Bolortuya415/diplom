"""
Text chunking module for the RAG pipeline.

Splits document pages into smaller overlapping chunks suitable
for embedding and retrieval.

Thesis note:
    Chunking strategy directly affects retrieval quality. We use
    character-level chunking with overlap to ensure that information
    spanning chunk boundaries is not lost. The chunk size of 500
    characters is chosen to fit within embedding model input limits
    while providing enough context for meaningful retrieval.

    FAQ-formatted files (using ### FAQ / Асуулт: / Хариулт: markers)
    are chunked per Q+A entry rather than by character count, keeping
    the question and answer together for accurate retrieval.
"""

import re
from dataclasses import dataclass, field
from typing import Optional
from rag.document_loader import DocumentPage


# FAQ detection patterns
_FAQ_MARKER_RE = re.compile(r"###\s*FAQ\s*\d+", re.UNICODE)
_FAQ_QUESTION_RE = re.compile(r"Асуулт\s*:\s*(.+?)(?:\n|$)", re.UNICODE)
_FAQ_ANSWER_RE = re.compile(r"Хариулт\s*:\s*(.+?)(?=\n###|\Z)", re.UNICODE | re.DOTALL)


def _is_faq_text(text: str) -> bool:
    """Return True if text contains FAQ-style markup."""
    return bool(_FAQ_MARKER_RE.search(text)) or (
        bool(_FAQ_QUESTION_RE.search(text)) and bool(_FAQ_ANSWER_RE.search(text))
    )


def _parse_faq_entries(text: str) -> list[tuple[str, str, str]]:
    """
    Parse FAQ-formatted text into (full_block, question, answer) tuples.

    Handles both ### FAQ N header style and bare Асуулт:/Хариулт: pairs.
    """
    entries: list[tuple[str, str, str]] = []

    # Split on ### FAQ N markers, keeping content between them
    blocks = re.split(r"\n?###\s*FAQ\s*\d+\s*\n?", text)

    for block in blocks:
        block = block.strip()
        if not block:
            continue
        q_match = _FAQ_QUESTION_RE.search(block)
        a_match = _FAQ_ANSWER_RE.search(block)
        if q_match and a_match:
            question = q_match.group(1).strip()
            answer = re.sub(r"\s+", " ", a_match.group(1)).strip()
            full_block = f"Асуулт: {question}\nХариулт: {answer}"
            entries.append((full_block, question, answer))

    return entries


@dataclass
class Chunk:
    """A text chunk with metadata for retrieval and citation."""
    chunk_id: str
    text: str
    source_file: str
    page_number: int
    chunk_index: int
    metadata: Optional[dict] = field(default=None)


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Split text into overlapping chunks.

    Strategy: character-level splitting with sentence-boundary awareness.
    Tries to break at sentence boundaries (periods, newlines) when possible.

    Args:
        text: Input text to chunk
        chunk_size: Maximum characters per chunk
        overlap: Number of overlapping characters between chunks
    """
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # If not at the end, try to break at a sentence boundary
        if end < len(text):
            # Look for sentence-ending punctuation near the end
            best_break = -1
            for sep in [".\n", ".\r", ". ", "\n\n", "\n"]:
                idx = text.rfind(sep, start + chunk_size // 2, end)
                if idx > best_break:
                    best_break = idx + len(sep)

            if best_break > start:
                end = best_break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move start forward, accounting for overlap
        start = end - overlap
        if start <= (end - chunk_size):  # Prevent infinite loop
            start = end

    return chunks


def chunk_documents(
    pages: list[DocumentPage],
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    doc_id: str = None,
) -> list[Chunk]:
    """
    Chunk a list of document pages into retrieval-ready chunks.

    FAQ-formatted pages (detected via ### FAQ / Асуулт: / Хариулт: markers)
    are split one chunk per Q+A entry so each chunk stays semantically whole.
    All other pages use character-level chunking with overlap.

    Args:
        pages: List of DocumentPage objects from document_loader
        chunk_size: Maximum characters per chunk
        chunk_overlap: Overlap between chunks
        doc_id: Optional document identifier prefix

    Returns:
        List of Chunk objects with unique IDs and metadata
    """
    all_chunks = []
    global_idx = 0

    for page in pages:
        prefix = doc_id or page.source_file.replace(".", "_")

        if _is_faq_text(page.text):
            # ── FAQ-aware chunking: one chunk per Q+A entry ───────────────
            faq_entries = _parse_faq_entries(page.text)
            for i, (full_block, question, answer) in enumerate(faq_entries):
                chunk = Chunk(
                    chunk_id=f"{prefix}_faq_{i}",
                    text=full_block,
                    source_file=page.source_file,
                    page_number=page.page_number,
                    chunk_index=global_idx,
                    metadata={
                        "page_number": page.page_number,
                        "chunk_in_page": i,
                        "char_count": len(full_block),
                        "is_faq": True,
                        "faq_question": question,
                        "faq_answer": answer,
                        **(page.metadata or {}),
                    },
                )
                all_chunks.append(chunk)
                global_idx += 1
        else:
            # ── Standard character-level chunking ─────────────────────────
            text_chunks = chunk_text(page.text, chunk_size, chunk_overlap)
            for i, text in enumerate(text_chunks):
                chunk = Chunk(
                    chunk_id=f"{prefix}_p{page.page_number}_c{i}",
                    text=text,
                    source_file=page.source_file,
                    page_number=page.page_number,
                    chunk_index=global_idx,
                    metadata={
                        "page_number": page.page_number,
                        "chunk_in_page": i,
                        "char_count": len(text),
                        **(page.metadata or {}),
                    },
                )
                all_chunks.append(chunk)
                global_idx += 1

    return all_chunks
