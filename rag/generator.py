# -*- coding: utf-8 -*-
"""
Answer generation using the Google Gemini API with retrieved context.

Free tier:
    Gemini 2.0 Flash (the default model) ships a generous free quota on
    Google AI Studio — fine for a thesis demo. No card on file required.
    Get a key at https://aistudio.google.com/app/apikey

Preserved from the previous Ollama-based generator:
    - Mongolian post-processing: strips leaked citation headers
      ('[1] file.pdf (х.3)') the model sometimes echoes from the context.
    - Mongolian doc titles + law-article reference extraction for the
      source citation panel.

What changed:
    - Ollama HTTP call → Gemini SDK call.
    - max_tokens raised (CPU constraint gone) to allow 2–5 sentence answers.
    - Lazy model init so the backend boots without a key; generate()
      returns a clear Mongolian message if the key is missing.
    - FAQ fast-path removed: BGE-M3 cosine similarity alone can't
      distinguish a same-topic FAQ from the question-specific one, so
      the path could short-circuit to a misleading answer. The LLM now
      synthesises every reply from the full retrieved context.
"""

import os
import re
import time
from typing import Optional

from rag.config import RAGConfig

# Number of retries on transient Gemini errors (503 / 504 / brief 5xx).
# Free tier returns 503s sporadically; one or two retries with short
# backoff masks them without blowing the request latency budget.
_GEMINI_TRANSIENT_RETRIES = 2
_GEMINI_RETRY_BACKOFF_S = 0.8


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
    """Strip leaked citation headers / source leaders from the model output."""
    if not answer:
        return ""
    text = answer.strip()
    for _ in range(4):
        new = _CITATION_HEADER_RE.sub("", text, count=1).lstrip()
        new = _SOURCE_HEADER_RE.sub("", new, count=1).lstrip()
        if new == text:
            break
        text = new
    return text.strip()


# Max chars per chunk sent to the LLM — keeps prompts small and focused.
_CONTEXT_CHUNK_MAX_CHARS = 600


class AnswerGenerator:
    """Generates Mongolian answers using Gemini with retrieved context."""

    def __init__(self, config: Optional[RAGConfig] = None):
        self.config = config or RAGConfig()
        self._client = None  # lazy-initialised genai.Client

    # ── Lazy Gemini client ───────────────────────────────────────────

    def _get_client(self):
        """Return a configured Gemini client, or None if no API key is set."""
        if self._client is not None:
            return self._client

        api_key = self.config.gemini_api_key or os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            return None

        from google import genai

        self._client = genai.Client(api_key=api_key)
        return self._client

    # ── Chunk formatting ─────────────────────────────────────────────

    def _deduplicate_chunks(self, chunks: list[dict]) -> list[dict]:
        """Drop near-duplicate chunks (one's prefix contained in another)."""
        if len(chunks) <= 1:
            return chunks

        seen_texts: list[str] = []
        unique: list[dict] = []
        for chunk in chunks:
            text = chunk.get("text", "")
            prefix = text[:80].strip()
            duplicate = any(
                prefix and (prefix in seen or seen[:80] in text)
                for seen in seen_texts
            )
            if not duplicate:
                unique.append(chunk)
                seen_texts.append(text)
        return unique

    def format_context(self, retrieved_chunks: list[dict]) -> str:
        if not retrieved_chunks:
            return "Эх сурвалж олдсонгүй."

        chunks = self._deduplicate_chunks(retrieved_chunks)
        parts = []
        for i, chunk in enumerate(chunks, 1):
            source = chunk["source_file"]
            page = chunk.get("page_number", "?")
            text = chunk["text"]
            if len(text) > _CONTEXT_CHUNK_MAX_CHARS:
                text = text[:_CONTEXT_CHUNK_MAX_CHARS].rsplit(" ", 1)[0] + "…"
            parts.append(f"[{i}] {source} (х.{page})\n{text}")
        return "\n\n".join(parts)

    # ── Source citation panel ────────────────────────────────────────

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
        key = source_file.lower().strip()
        if key in cls._DOC_TITLES:
            return cls._DOC_TITLES[key]
        basename = key.split("/")[-1].split("\\")[-1]
        if basename in cls._DOC_TITLES:
            return cls._DOC_TITLES[basename]
        name = re.sub(r"\.(pdf|txt|docx?)$", "", basename, flags=re.IGNORECASE)
        return name.capitalize() if name else source_file

    @classmethod
    def _extract_law_refs(cls, text: str) -> list[str]:
        matches = cls._LAW_REF_RE.findall(text)
        seen: list[str] = []
        for m in matches:
            cleaned = re.sub(r"\s+", " ", m).strip()
            if cleaned and cleaned not in seen:
                seen.append(cleaned)
        return seen[:3]

    def format_sources(self, retrieved_chunks: list[dict]) -> list[dict]:
        sources = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            raw_score = chunk.get("score", 0.0)
            try:
                relevance_score = round(max(0.0, min(1.0, float(raw_score))), 4)
            except (TypeError, ValueError):
                relevance_score = 0.0
            text = chunk.get("text", "")
            sources.append({
                "ref_number": i,
                "source_file": chunk["source_file"],
                "document_title": self._get_doc_title(chunk["source_file"]),
                "page_number": chunk.get("page_number"),
                "snippet": text[:200] + "…" if len(text) > 200 else text,
                "relevance_score": relevance_score,
                "law_references": self._extract_law_refs(text),
            })
        return sources

    # ── Main entry point ─────────────────────────────────────────────

    def generate(
        self,
        query: str,
        retrieved_chunks: list[dict],
        safety_label: str = "safe",
    ) -> dict:
        """Return a dict with: answer, sources, model_used, tokens_used."""
        sources = self.format_sources(retrieved_chunks)

        # The previous FAQ fast-path (returning the top FAQ's stored answer
        # verbatim when its embedding score cleared a threshold) is removed:
        # BGE-M3 cosine alone can't distinguish a same-topic FAQ from the
        # specific-question FAQ, so the path would short-circuit to the
        # wrong stored answer. The LLM gets all retrieved chunks and
        # synthesises a faithful, question-specific reply instead.

        client = self._get_client()
        if client is None:
            return {
                "answer": (
                    "Gemini API түлхүүр тохируулагдаагүй байна. "
                    ".env файлд GEMINI_API_KEY-г оруулаад серверийг "
                    "дахин ажиллуулна уу."
                ),
                "sources": sources,
                "model_used": self.config.llm_model,
                "tokens_used": 0,
                "context_chunks_used": len(retrieved_chunks),
                "error": "Missing GEMINI_API_KEY",
            }

        context = self.format_context(retrieved_chunks)

        top_is_faq = (
            retrieved_chunks
            and (retrieved_chunks[0].get("metadata") or {}).get("is_faq")
        )
        if top_is_faq:
            user_message = (
                f"[Асуулт]\n{query}\n\n"
                f"[FAQ Хариулт]\n{context}\n\n"
                "[Даалгавар]\n"
                "FAQ-ийн хариултад тулгуурлан Монгол хэлээр цэвэр, дүрмийн "
                "алдаагүй бүтэн өгүүлбэрээр хариул. Файлын нэр, хуудасны "
                "дугаар, 'Эх сурвалж:' гэх мэт тэмдэглэгээг хариултын эхэнд "
                "бүү бич. Хариултын төгсгөлд ашигласан эх сурвалжийг зөвхөн "
                "[1] гэсэн дугаараар дурд."
            )
        else:
            user_message = (
                f"[Асуулт]\n{query}\n\n"
                f"[Эх сурвалж]\n{context}\n\n"
                "[Даалгавар]\n"
                "Дээрх эх сурвалжийг зөвхөн баримт болгон ашиглаад, Монгол "
                "хэлээр 2–5 өгүүлбэрт, цэвэр, байгалийн, дүрмийн алдаагүй "
                "хариулт бич. Шаардлагатай бол хуулийн зүйл, заалтыг нэрлэн "
                "дурд. Эх сурвалжийн текстийг үгчлэн бүү хуул; утгыг нь "
                "эргүүлэн товчоор илэрхийл. Файлын нэр, хуудасны дугаар, "
                "'[1] ...pdf (х.N)' гэх мэт толгойг хариултын эхэнд бүү бич. "
                "Зөвхөн өгүүлбэрийн төгсгөлд [1], [2] гэж дурд. "
                "Хэрэв эх сурвалж асуултад хангалтгүй бол "
                "'Хангалттай мэдээлэл олдсонгүй.' гэж бич."
            )

        try:
            from google.genai import types

            # 2.5 models do internal "thinking" by default which eats the
            # output budget before any visible answer is produced. We're
            # grounded in retrieved context so a thinking pass adds latency
            # without quality gain — disable it.
            thinking = types.ThinkingConfig(thinking_budget=0)
            gen_config = types.GenerateContentConfig(
                system_instruction=self.config.system_prompt,
                temperature=self.config.llm_temperature,
                max_output_tokens=self.config.llm_max_tokens,
                thinking_config=thinking,
            )

            response = None
            last_err: Optional[Exception] = None
            for attempt in range(_GEMINI_TRANSIENT_RETRIES + 1):
                try:
                    response = client.models.generate_content(
                        model=self.config.llm_model,
                        contents=user_message,
                        config=gen_config,
                    )
                    break
                except Exception as inner:
                    last_err = inner
                    msg = str(inner)
                    is_transient = (
                        "503" in msg or "504" in msg
                        or "unavailable" in msg.lower()
                        or "deadline" in msg.lower()
                    )
                    if not is_transient or attempt >= _GEMINI_TRANSIENT_RETRIES:
                        raise
                    time.sleep(_GEMINI_RETRY_BACKOFF_S * (attempt + 1))

            if response is None:
                # Defensive — _shouldn't_ reach here without an exception above.
                raise last_err or RuntimeError("Empty response from Gemini")

            raw_answer = (response.text or "").strip()
            answer = _clean_llm_answer(raw_answer)

            usage = getattr(response, "usage_metadata", None)
            tokens_used = 0
            if usage is not None:
                tokens_used = int(
                    (getattr(usage, "prompt_token_count", 0) or 0)
                    + (getattr(usage, "candidates_token_count", 0) or 0)
                )

            return {
                "answer": answer,
                "sources": sources,
                "model_used": self.config.llm_model,
                "tokens_used": tokens_used,
                "context_chunks_used": len(retrieved_chunks),
            }

        except Exception as e:
            # Gemini surface errors: rate limit, invalid key, safety block, etc.
            err = str(e)
            lower = err.lower()
            if "api key" in lower or "permission" in lower or "401" in err or "403" in err:
                friendly = (
                    "Gemini API түлхүүр буруу эсвэл хүчингүй байна. "
                    "Шинэ түлхүүрийг .env файлд оруулна уу."
                )
            elif "quota" in lower or "rate" in lower or "429" in err:
                friendly = (
                    "Gemini API-ийн үнэгүй хязгаар дуусчээ. "
                    "Хэдэн минутын дараа дахин оролдоно уу."
                )
            else:
                friendly = (
                    "Уучлаарай, хариулт үүсгэхэд алдаа гарлаа. "
                    "Дахин оролдоно уу."
                )
            return {
                "answer": friendly,
                "sources": sources,
                "model_used": self.config.llm_model,
                "tokens_used": 0,
                "context_chunks_used": len(retrieved_chunks),
                "error": err,
            }
