# -*- coding: utf-8 -*-
"""
Answer generation using Ollama local LLM with retrieved context.

Optimized for Intel i7 MacBook (16 GB RAM, no GPU):
    - Timeout 90s (not 300s) — prevents system freeze
    - Chunks truncated to 250 chars — keeps prompt short
    - Deduplication — removes near-duplicate retrieved chunks
    - Source fallback — returns top chunk on timeout instead of empty error
    - max_tokens=250 — 2-4 sentences; much faster on CPU

FAQ fast-path:
    When the top retrieved chunk is an FAQ entry with score ≥
    _FAQ_DIRECT_THRESHOLD the pre-written Хариулт is returned directly,
    bypassing Ollama entirely. This gives a faster, cleaner answer and
    avoids the LLM rephrasing a perfectly good one-sentence FAQ reply
    into a vague multi-sentence paraphrase.
"""

import json
import re
from typing import Optional

import requests

from rag.config import RAGConfig

# Matches citation headers the LLM may echo from the context:
#   "[1] filename.pdf (х.3)\n"
#   "[2] faq.txt\n"
_CITATION_HEADER_RE = re.compile(
    r"^\s*\[\s*\d+\s*\]\s*[^\n\[\]]+?\.(?:pdf|txt|md|docx?)"
    r"(?:\s*\([^)]*\))?\s*\n?",
    re.IGNORECASE,
)

# "Эх сурвалж:" / "Ашигласан эх сурвалж" leaders the model sometimes prepends
_SOURCE_HEADER_RE = re.compile(
    r"^\s*(Эх\s+сурвалж(аас|ийн)?\s*[:\-]?\s*)", re.IGNORECASE | re.UNICODE
)


def _clean_llm_answer(answer: str) -> str:
    """
    Strip leaked citation headers and source leaders from Ollama output.

    The LLM occasionally echoes the context's "[1] filename.pdf (х.3)\\n"
    header at the start of its answer. Those raw snippets are not a
    natural Mongolian reply, so we peel them off while keeping the
    inline "[1]" citation markers inside the body of the answer.
    """
    if not answer:
        return ""
    text = answer.strip()

    # Iteratively strip any sequence of leaked headers at the very start
    for _ in range(4):
        new = _CITATION_HEADER_RE.sub("", text, count=1).lstrip()
        new = _SOURCE_HEADER_RE.sub("", new, count=1).lstrip()
        if new == text:
            break
        text = new

    return text.strip()

# Score threshold above which a strong FAQ match skips the LLM entirely.
# Tune upward if too many non-FAQ queries get the fast-path by mistake.
_FAQ_DIRECT_THRESHOLD = 0.55

# Max chars per chunk sent to LLM — longer than this adds latency with no quality gain
_CONTEXT_CHUNK_MAX_CHARS = 250


class AnswerGenerator:
    """Generates answers using a local Ollama LLM with RAG context."""

    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        # Resolve Ollama endpoints from config so OLLAMA_BASE_URL in .env takes effect
        base = self.config.ollama_base_url.rstrip("/")
        self._ollama_chat_url = f"{base}/api/chat"
        self._ollama_tags_url = f"{base}/api/tags"

    def _check_ollama(self) -> bool:
        """Return True if Ollama is reachable."""
        try:
            resp = requests.get(self._ollama_tags_url, timeout=3)
            return resp.status_code == 200
        except requests.exceptions.ConnectionError:
            return False

    def _deduplicate_chunks(self, chunks: list[dict]) -> list[dict]:
        """
        Remove near-duplicate chunks to avoid sending redundant context.

        Two chunks are considered duplicates if one chunk's leading text
        appears inside another chunk's text (overlap > 60 chars).
        """
        if len(chunks) <= 1:
            return chunks

        seen_prefixes: list[str] = []
        unique: list[dict] = []

        for chunk in chunks:
            text = chunk.get("text", "")
            prefix = text[:80].strip()
            is_duplicate = any(
                prefix in seen or seen[:80] in text
                for seen in seen_prefixes
            )
            if not is_duplicate:
                unique.append(chunk)
                seen_prefixes.append(text)

        return unique

    def format_context(self, retrieved_chunks: list[dict]) -> str:
        """
        Format retrieved chunks into a numbered context string.

        Each chunk is truncated to _CONTEXT_CHUNK_MAX_CHARS to keep the
        prompt short on CPU hardware. Reference numbers allow inline citations.
        """
        if not retrieved_chunks:
            return "Эх сурвалж олдсонгүй."

        chunks = self._deduplicate_chunks(retrieved_chunks)
        context_parts = []

        for i, chunk in enumerate(chunks, 1):
            source = chunk["source_file"]
            page = chunk.get("page_number", "?")
            text = chunk["text"]
            # Truncate to keep prompt short — preserves the most relevant opening
            if len(text) > _CONTEXT_CHUNK_MAX_CHARS:
                text = text[:_CONTEXT_CHUNK_MAX_CHARS].rsplit(" ", 1)[0] + "…"
            context_parts.append(f"[{i}] {source} (х.{page})\n{text}")

        return "\n\n".join(context_parts)

    # Human-readable document titles keyed by filename (case-insensitive)
    _DOC_TITLES = {
        "faq.txt": "Нийтлэг мэдээлэл (FAQ)",
        "faq_gender_equality.txt": "Хүйсийн тэгш эрх (FAQ)",
        "faq_discrimination.txt": "Ялгаварлан гадуурхалт (FAQ)",
        "faq_disability.txt": "Хөгжлийн бэрхшээлтэй иргэн (FAQ)",
        "gender_equality_guide.txt": "Хүйсийн тэгш эрхийн гарын авлага",
        "discrimination_guide.txt": "Ялгаварлан гадуурхалтын гарын авлага",
        "disability_rights_guide.txt": "Хөгжлийн бэрхшээлтэй иргэдийн гарын авлага",
        "жендэрийн эрх тэгш байдал.pdf": "Жендэрийн эрх тэгш байдлын хууль",
        "гэр бүлийн тухай.pdf": "Гэр бүлийн тухай хууль",
        "гэр бүлийн хүчирхийлэлтэй тэмцэх тухай.pdf": "Гэр бүлийн хүчирхийлэлтэй тэмцэх тухай хууль",
        "иргэний хууль.pdf": "Иргэний хууль",
        "хөгжлийн бэрхшээлтэй хүний эрхийн тухай.pdf": "Хөгжлийн бэрхшээлтэй хүний эрхийн тухай хууль",
    }

    # Patterns to extract law article references from Mongolian text
    _LAW_REF_RE = re.compile(
        r"("
        r"(?:хуулийн\s+)?(?:\d+(?:\.\d+)*|[IVXLC]+)\s*(?:дугаар|дэх|дахь|р|н)\s*зүйл[ийн]*(?:\s+\d+\s*дахь\s+хэсэг[т]?)?"
        r"|(?:\d+(?:\.\d+)+)\s*(?:зүйл[ийн]*|хэсэг[т]?)"
        r"|(?:[А-ЯӨҮа-яөүёъ\s]+тухай\s+хуулийн?\s*(?:\d+(?:\.\d+)*|[IVXLC]+)\s*(?:дугаар|дэх|р|н)?\s*зүйл[ийн]*)"
        r")",
        re.IGNORECASE | re.UNICODE,
    )

    @classmethod
    def _get_doc_title(cls, source_file: str) -> str:
        """Return a human-readable document title from a filename."""
        key = source_file.lower().strip()
        # Exact match
        if key in cls._DOC_TITLES:
            return cls._DOC_TITLES[key]
        # Partial match (strip path)
        basename = key.split("/")[-1].split("\\")[-1]
        if basename in cls._DOC_TITLES:
            return cls._DOC_TITLES[basename]
        # Strip extension and return cleaned name
        name = re.sub(r"\.(pdf|txt|docx?)$", "", basename, flags=re.IGNORECASE)
        return name.capitalize() if name else source_file

    @classmethod
    def _extract_law_refs(cls, text: str) -> list[str]:
        """Extract law article references from text (e.g. '14-р зүйл', '10.1 зүйл')."""
        matches = cls._LAW_REF_RE.findall(text)
        seen: list[str] = []
        for m in matches:
            cleaned = re.sub(r"\s+", " ", m).strip()
            if cleaned and cleaned not in seen:
                seen.append(cleaned)
        return seen[:3]  # at most 3 refs per source

    def format_sources(self, retrieved_chunks: list[dict]) -> list[dict]:
        """Format source citations for the frontend."""
        sources = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            raw_score = chunk.get("score", 0.0)
            try:
                relevance_score = round(max(0.0, min(1.0, float(raw_score))), 4)
            except (TypeError, ValueError):
                relevance_score = 0.0

            text = chunk.get("text", "")
            law_refs = self._extract_law_refs(text)

            sources.append({
                "ref_number": i,
                "source_file": chunk["source_file"],
                "document_title": self._get_doc_title(chunk["source_file"]),
                "page_number": chunk.get("page_number"),
                "snippet": text[:200] + "…" if len(text) > 200 else text,
                "relevance_score": relevance_score,
                "law_references": law_refs,
            })
        return sources

    def _extract_faq_answer(self, chunk: dict) -> Optional[str]:
        """
        Return the clean Хариулт text from an FAQ chunk, or None.

        Tries metadata first (set at chunking time), then falls back to
        parsing the chunk text with a regex.
        """
        meta = chunk.get("metadata") or {}
        if meta.get("faq_answer"):
            return meta["faq_answer"].strip()
        # Fallback: parse from stored text
        match = re.search(r"Хариулт\s*:\s*(.+?)(?:\n|$)", chunk.get("text", ""), re.DOTALL)
        if match:
            return re.sub(r"\s+", " ", match.group(1)).strip()
        return None

    def _source_fallback(self, retrieved_chunks: list[dict]) -> str:
        """
        Build a minimal, natural-sounding message when Ollama times out.

        We deliberately do NOT dump the raw retrieved chunk text into the
        final answer — that reads as broken Mongolian. Instead we return a
        short polite Mongolian message and let the UI show the retrieved
        chunks separately via the `sources` panel.
        """
        if not retrieved_chunks:
            return "Уучлаарай, хангалттай мэдээлэл олдсонгүй."

        return (
            "Одоогоор хариулт үүсгэхэд хугацаа хэтэрлээ. "
            "Холбогдох эх сурвалжуудыг доор харуулав — "
            "та асуултаа арай товчоор дахин бичиж үзнэ үү."
        )

    def generate(
        self,
        query: str,
        retrieved_chunks: list[dict],
        safety_label: str = "safe",
    ) -> dict:
        """
        Generate an answer using Ollama with retrieved context.

        Args:
            query: User's question
            retrieved_chunks: List of retrieved chunk dicts from EmbeddingManager.search()
            safety_label: Output from the sensitive content classifier

        Returns:
            dict with: answer, sources, model_used, tokens_used
        """
        sources = self.format_sources(retrieved_chunks)

        # ── FAQ fast-path: strong match → return stored answer directly ──────
        # Bypasses Ollama so the answer is cleaner, faster, and exactly what
        # the FAQ author wrote rather than a hallucination-prone paraphrase.
        if retrieved_chunks:
            top = retrieved_chunks[0]
            top_meta = top.get("metadata") or {}
            if top_meta.get("is_faq") and top.get("score", 0.0) >= _FAQ_DIRECT_THRESHOLD:
                faq_answer = self._extract_faq_answer(top)
                if faq_answer:
                    return {
                        "answer": faq_answer,
                        "sources": sources,
                        "model_used": "faq_direct",
                        "tokens_used": 0,
                        "context_chunks_used": 1,
                    }

        if not self._check_ollama():
            return {
                "answer": (
                    "Уучлаарай, Ollama сервер ажиллахгүй байна. "
                    "Терминалд `ollama serve` гэж ажиллуулна уу."
                ),
                "sources": sources,
                "model_used": self.config.llm_model,
                "tokens_used": 0,
                "context_chunks_used": len(retrieved_chunks),
                "error": "Ollama not running",
            }

        context = self.format_context(retrieved_chunks)

        system_message = self.config.system_prompt

        # Use a tighter, FAQ-aware prompt when the top chunk is an FAQ entry
        # (below the direct threshold but still FAQ-sourced).
        top_is_faq = (
            retrieved_chunks
            and (retrieved_chunks[0].get("metadata") or {}).get("is_faq")
        )
        if top_is_faq:
            user_message = (
                f"[Асуулт]\n{query}\n\n"
                f"[FAQ Хариулт]\n{context}\n\n"
                "[Даалгавар]\n"
                "FAQ-ийн хариултад тулгуурлан Монгол хэлээр цэвэр, дүрмийн алдаагүй "
                "бүтэн өгүүлбэрээр хариул. Файлын нэр, хуудасны дугаар, "
                "'Эх сурвалж:' гэх мэт тэмдэглэгээг хариултын эхэнд бүү бич. "
                "Хариултын төгсгөлд ашигласан эх сурвалжийг зөвхөн [1] гэсэн дугаараар дурд."
            )
        else:
            user_message = (
                f"[Асуулт]\n{query}\n\n"
                f"[Эх сурвалж]\n{context}\n\n"
                "[Даалгавар]\n"
                "Дээрх эх сурвалжийг зөвхөн баримт болгон ашиглаад, Монгол хэлээр "
                "2–4 өгүүлбэрт, цэвэр, байгалийн, дүрмийн алдаагүй хариулт бич. "
                "Эх сурвалжийн текстийг үгчлэн бүү хуул; утгыг нь эргүүлэн товчоор илэрхийл. "
                "Файлын нэр, хуудасны дугаар, '[1] ...pdf (х.N)' гэх мэт толгойг "
                "хариултын эхэнд бүү бич. Зөвхөн өгүүлбэрийн төгсгөлд [1], [2] гэж дурд. "
                "Хэрэв эх сурвалж асуултад хангалтгүй бол "
                "'Хангалттай мэдээлэл олдсонгүй.' гэж бич."
            )

        payload = {
            "model": self.config.llm_model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            "options": {
                "temperature": self.config.llm_temperature,
                "num_predict": self.config.llm_max_tokens,
            },
            "stream": False,
        }

        try:
            response = requests.post(
                self._ollama_chat_url,
                json=payload,
                timeout=self.config.llm_timeout,
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
            response.raise_for_status()

            data = response.json()
            raw_answer = data["message"]["content"]
            answer = _clean_llm_answer(raw_answer)
            tokens_used = (
                data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
            )

            return {
                "answer": answer,
                "sources": sources,
                "model_used": self.config.llm_model,
                "tokens_used": tokens_used,
                "context_chunks_used": len(retrieved_chunks),
            }

        except requests.exceptions.Timeout:
            # Source fallback: return top chunk content rather than empty error
            fallback = self._source_fallback(retrieved_chunks)
            return {
                "answer": fallback,
                "sources": sources,
                "model_used": "source_fallback",
                "tokens_used": 0,
                "context_chunks_used": len(retrieved_chunks),
                "error": "Request timed out",
            }

        except requests.exceptions.ConnectionError:
            return {
                "answer": (
                    "Уучлаарай, Ollama сервер ажиллахгүй байна. "
                    "Терминалд `ollama serve` гэж ажиллуулна уу."
                ),
                "sources": sources,
                "model_used": self.config.llm_model,
                "tokens_used": 0,
                "context_chunks_used": len(retrieved_chunks),
                "error": "Ollama not running",
            }

        except Exception as e:
            return {
                "answer": (
                    "Уучлаарай, хариулт үүсгэхэд алдаа гарлаа. "
                    "Дахин оролдоно уу."
                ),
                "sources": sources,
                "model_used": self.config.llm_model,
                "tokens_used": 0,
                "context_chunks_used": len(retrieved_chunks),
                "error": str(e),
            }
