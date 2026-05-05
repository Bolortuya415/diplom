"""
Document loading and parsing module.

Handles PDF and TXT file ingestion for the RAG pipeline.

Thesis note:
    Document ingestion is the first step of the RAG pipeline. This module
    extracts raw text from uploaded documents while preserving metadata
    (source filename, page numbers) for citation generation.
"""

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DocumentPage:
    """A single page/section from a document."""
    text: str
    page_number: int
    source_file: str
    metadata: Optional[dict] = field(default=None)


def clean_extracted_text(text: str) -> str:
    """
    Clean text extracted from PDFs.

    Handles common PDF extraction artifacts:
    - Excessive whitespace
    - Hyphenated line breaks
    - Page headers/footers patterns
    """
    # Remove excessive newlines (keep paragraph breaks)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Fix hyphenated line breaks (Mongolian doesn't typically hyphenate,
    # but English-mixed content might)
    text = re.sub(r"-\n", "", text)
    # Normalize whitespace within lines
    text = re.sub(r"[ \t]+", " ", text)
    # Strip leading/trailing whitespace per line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)
    return text.strip()


def load_pdf(file_path: str) -> list[DocumentPage]:
    """
    Extract text from a PDF file page by page.

    Uses PyMuPDF (fitz) for reliable Mongolian Cyrillic extraction.
    """
    import fitz  # PyMuPDF

    doc = fitz.open(file_path)
    pages = []
    filename = Path(file_path).name

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        text = clean_extracted_text(text)

        if text.strip():  # Skip empty pages
            pages.append(DocumentPage(
                text=text,
                page_number=page_num + 1,
                source_file=filename,
                metadata={"total_pages": len(doc)},
            ))

    doc.close()
    return pages


def load_text(file_path: str) -> list[DocumentPage]:
    """Load a plain text file as a single document."""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    text = clean_extracted_text(text)
    filename = Path(file_path).name

    return [DocumentPage(
        text=text,
        page_number=1,
        source_file=filename,
        metadata={"format": "txt"},
    )]


def load_document(file_path: str) -> list[DocumentPage]:
    """
    Load a document based on file extension.

    Supported formats: .pdf, .txt
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        return load_pdf(file_path)
    elif ext == ".txt":
        return load_text(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}. Supported: .pdf, .txt")
