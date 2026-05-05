"""
Chat service — orchestrates classifier + retrieval + generation.

Routing priority (fastest path first):
    1a. Identity shortcut      → "чи хэн бэ" → direct self-introduction
    1b. Capability shortcut    → "чи юу хийж чадах вэ" → topic list reply
        (both bypass classifier and retrieval so benign help phrases are
         never treated as crisis)
    2.  Greeting shortcut      → direct Mongolian greeting, skip Ollama
    3.  Safety classifier      → block if unsafe; self_harm/harassment are
                                 downgraded to "safe" when the text contains
                                 no real crisis indicator
    4.  Vague query shortcut   → clarification request, skip Ollama
    5.  RAG retrieval + Ollama → only for real topical questions
    6.  Unclear-intent fallback → polite Mongolian "please rephrase" message

Ollama is only called when there are retrieved chunks AND the query is
a substantive topical question. This minimizes CPU pressure on the Mac.
"""

import json
import logging
import re
import time
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from backend.app.core.config import (
    MODEL_DIR, SAFETY_CONFIDENCE_THRESHOLD,
)
from backend.app.db.database import get_db
from rag.pipeline import RAGPipeline
from rag.generator import AnswerGenerator
from training.scripts.inference import SensitiveContentClassifier, SAFETY_RESPONSES

logger = logging.getLogger("boloroo.chat")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def _log_route(route: str, query: str) -> None:
    """Print which routing branch was selected (stdout + logger)."""
    snippet = (query or "").strip().replace("\n", " ")[:80]
    msg = f"[ROUTE] selected={route} query={snippet!r}"
    logger.info(msg)
    print(msg, flush=True)


# Greetings that get a direct reply without any RAG or LLM call
_GREETINGS: frozenset[str] = frozenset({
    "сайн уу", "сайн байна уу", "сайн байцгаана уу",
    "өглөөний мэнд", "үдийн мэнд", "оройн мэнд",
    "hi", "hello", "hey", "сайн",
})

# Vague queries with no clear topic — return a clarification question instead
# of wasting an Ollama call that would produce a useless answer.
# Bare "тусламж / туслаач / тусла" stay in this list so they get clarification,
# NOT crisis routing. Real crisis input is detected via _CRISIS_INDICATORS_RE.
_VAGUE_QUERIES: frozenset[str] = frozenset({
    "яах вэ", "яах вэ?", "юу хийх вэ", "юу хийх вэ?",
    "хаана хандах вэ", "хаана хандах вэ?", "хаана хандах",
    "туслаач", "тусла", "тусламж", "тусламж өгөөч",
    "мэдэхгүй байна", "мэдэхгүй",
    "хэрхэн", "хэрхэн?", "юу вэ", "юу вэ?",
    "тайлбарлаач", "ойлгосонгүй",
})

_GREETING_RESPONSE = "Сайн байна уу? Танд юугаар туслах вэ?"

_CLARIFICATION_RESPONSE = (
    "Та ямар сэдвээр мэдээлэл авахыг хүсэж байна вэ?\n"
    "Жишээ нь: хүйсийн тэгш байдал, хүүхэд хамгаалал, "
    "ялгаварлан гадуурхалт, дарамт, хүчирхийлэл зэрэг сэдвийн талаар асуух боломжтой."
)

# Category-specific context prefixes added to queries for better retrieval
_CATEGORY_CONTEXT: dict[str, str] = {
    "gender_equality": (
        "Хүйсийн тэгш эрх, жендэрийн бодлого, эмэгтэйчүүдийн эрх, "
        "бэлгийн дарамт, гэр бүлийн харилцаанд тэгш байдал: "
    ),
    "discrimination": (
        "Ялгаварлан гадуурхалт, тэгш бус хандлага, үзэн ядалт, "
        "сургуулийн дарамт, хуулийн хамгаалалт: "
    ),
    "disability": (
        "Хөгжлийн бэрхшээлтэй иргэн, тэгш хүртээмж, боловсролын эрх, "
        "ажил эрхлэлт, нийгмийн хамгаалал: "
    ),
}

# Direct capability reply — returned when the user asks what the chatbot can do.
_CAPABILITY_RESPONSE = (
    "Би хүйсийн тэгш байдал, ялгаварлан гадуурхалт, хүүхэд хамгаалал, "
    "сургуулийн дарамт, гэр бүлийн хүчирхийлэл, нийгмийн хүртээмжтэй байдал "
    "зэрэг сэдвээр мэдээлэл өгч, эх сурвалжид тулгуурлан хариулах боломжтой "
    "чатбот юм."
)

# Direct identity reply — "who are you" style questions.
_IDENTITY_RESPONSE = (
    "Би Болороо — хүйсийн тэгш байдал, нийгмийн хүртээмжтэй байдал, "
    "хүүхэд хамгаалал, ялгаварлан гадуурхалт, дарамтын эсрэг үйл ажиллагаа, "
    "тусламжийн сувгийн талаар Монгол хэл дээр мэдээлэл өгдөг туслах чатбот юм. "
    "Асуултаа бичвэл холбогдох эх сурвалжид тулгуурлан хариулахыг хичээнэ."
)

# Unclear-intent fallback (used when no FAQ/RAG answer can be safely produced).
_UNCLEAR_INTENT_RESPONSE = (
    "Таны асуултыг бүрэн ойлгосонгүй. "
    "Та асуултаа арай дэлгэрэнгүй бичиж өгнө үү?"
)

# ── Capability intent: robust two-group matching ────────────────────────
# A query is a capability question iff it contains (A) a SELF token
# referring to the bot AND (B) a CAPABILITY token describing an ability.
# This is more tolerant than a single long regex: word order, punctuation,
# and extra particles don't break it.
_SELF_TOKENS_RE = re.compile(
    r"(^|[\s\?\.\!,])(чи|та|chatbot|чатбот|бот|ассистент|туслах)([\s\?\.\!,]|$)",
    re.IGNORECASE | re.UNICODE,
)
_CAPABILITY_TOKENS_RE = re.compile(
    r"("
    r"тусалж\s+чад"
    r"|туслаж\s+чад"           # frequent misspelling
    r"|юу\s+хийж\s+чад"
    r"|юу\s+хийдэг"
    r"|хариулж\s+чад"
    r"|юугаар\s+туслах"
    r"|юугаар\s+тусл"
    r"|ямар\s+асуултад\s+хариул"
    r"|ямар\s+(сэдвээр|зүйлд|зүйл\s+дээр)"
    r"|юу\s+мэдд"
    r"|юу\s+мэдн"
    r"|юунд\s+зориулагд"
    r"|юунд\s+хэрэгтэй"
    r"|ямар\s+бот"
    r"|ямар\s+chatbot"
    r"|ямар\s+чатбот"
    r")",
    re.IGNORECASE | re.UNICODE,
)

# Direct fast-path phrases that skip the two-group check entirely.
_CAPABILITY_DIRECT_RE = re.compile(
    r"(чи\s+надад.*тусл"
    r"|надад.*тусалж\s+чад"
    r"|энэ\s+талаар\s+тусл"
    r"|мэдээлэл\s+өгч\s+тусл"
    r"|асуултад\s+хариулаад\s+өгөөч"
    r"|тусалж\s+чадах\s+уу)",
    re.IGNORECASE | re.UNICODE,
)

# "Who are you / what kind of bot are you" — answered with _IDENTITY_RESPONSE.
_IDENTITY_RE = re.compile(
    r"(чи\s+хэн\s+бэ"
    r"|чи\s+хэн\s+юм"
    r"|чи\s+ямар\s+(бот|chatbot|чатбот)"
    r"|та\s+хэн\s+бэ"
    r"|нэр\s+нь\s+юу\s+вэ"
    r"|өөрийгөө\s+танилц)",
    re.IGNORECASE | re.UNICODE,
)

# Real crisis / immediate-danger indicators.
# Only when a query contains ONE of these do we treat a classifier
# self-harm / harassment label as a genuine crisis. Without these,
# mere presence of "тусл*" / "туслаач" is NOT crisis intent.
_CRISIS_INDICATORS_RE = re.compile(
    r"(үхмээр"
    r"|амьдрахгүй"
    r"|амиа"
    r"|өөрийгөө\s+гэмтээх"
    r"|өөрийгөө\s+хорлох"
    r"|аюултай\s+байна"
    r"|тэсэхгүй\s+байна"
    r"|хохироох"
    r"|надад\s+аюул\s+тулгарсан"
    r"|одоо\s+аюултай)",
    re.IGNORECASE | re.UNICODE,
)

# Labels we are willing to downgrade to "safe" if no real crisis indicator
# is present. We never downgrade hate_speech or discrimination — those
# labels are triggered by the content itself, not by crisis context.
_DOWNGRADEABLE_LABELS = {"self_harm", "harassment"}


def _normalize(text: str) -> str:
    """Lowercase and strip punctuation/whitespace for exact-equality matching."""
    return text.strip().lower().rstrip("!?,. ")


def _normalize_for_match(text: str) -> str:
    """
    Lowercase + collapse whitespace for regex matching.

    Keeps Cyrillic characters intact. Does NOT strip punctuation inside
    the string — the regexes already handle optional punctuation.
    """
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _has_crisis_indicator(text: str) -> bool:
    """True if the text contains a real immediate-danger keyword."""
    return bool(_CRISIS_INDICATORS_RE.search(_normalize_for_match(text)))


def _is_capability_question(text: str) -> bool:
    """
    True if the user is asking what the chatbot can help with.

    Matches either:
      (a) A direct phrase like "чи надад тусалж чадах уу", OR
      (b) BOTH a SELF token (чи/та/бот/chatbot/...) AND a CAPABILITY token
          (тусалж чад / юу хийж чад / ямар сэдвээр / юунд зориулагд / ...).
    """
    norm = _normalize_for_match(text)
    if _CAPABILITY_DIRECT_RE.search(norm):
        return True
    return bool(_SELF_TOKENS_RE.search(norm) and _CAPABILITY_TOKENS_RE.search(norm))


def _is_identity_question(text: str) -> bool:
    """True if the user is asking who the chatbot is."""
    return bool(_IDENTITY_RE.search(_normalize_for_match(text)))


# Pattern that indicates the LLM leaked raw retrieval context into the answer:
#   "[1] filename.pdf (х.3)\n..."  or a bare leading "[1] ...txt"
_RAW_SNIPPET_LEAK_RE = re.compile(
    r"^\s*\[\s*\d+\s*\]\s*\S+\.(pdf|txt|md|docx?)", re.IGNORECASE
)


class ChatService:
    """Handles the full chat flow: safety check → route → retrieve → generate."""

    def __init__(self):
        self.rag: Optional[RAGPipeline] = None
        self.generator: Optional[AnswerGenerator] = None
        self.classifier: Optional[SensitiveContentClassifier] = None

    @staticmethod
    def _looks_like_raw_snippet(answer: str) -> bool:
        """Detect a leaked raw retrieval snippet at the start of an answer."""
        if not answer:
            return True
        return bool(_RAW_SNIPPET_LEAK_RE.search(answer))

    def initialize_with_rag(self, rag: RAGPipeline):
        """Attach a shared RAG pipeline and create the LLM generator + classifier."""
        self.rag = rag
        self.generator = AnswerGenerator(config=rag.config)

        try:
            self.classifier = SensitiveContentClassifier(
                model_dir=str(MODEL_DIR),
                confidence_threshold=SAFETY_CONFIDENCE_THRESHOLD,
            )
            print("Sensitive content classifier loaded.")
        except FileNotFoundError as e:
            print(f"Warning: Classifier not loaded — {e}")
            self.classifier = None

    def process_query(self, query: str, category: Optional[str] = None) -> dict:
        """
        Process a user query through the full pipeline.

        Ollama is only called for substantive topical questions with
        retrieved context. All other paths return immediately.
        """
        start_time = time.time()
        normalized = _normalize(query)
        has_crisis = _has_crisis_indicator(query)

        # Default "safe" result used by every shortcut that bypasses the classifier.
        safe_result = {
            "label": "safe",
            "label_id": 0,
            "confidence": 1.0,
            "is_safe": True,
            "all_scores": {},
        }

        # ── Step 1a: Identity question shortcut ──────────────────────────
        # "чи хэн бэ", "чи ямар чатбот вэ", "өөрийгөө танилцуул" → identity reply.
        # Runs before the classifier so a self-introduction query is never
        # treated as unsafe. Real crisis input still falls through to the
        # classifier path.
        if _is_identity_question(query) and not has_crisis:
            _log_route("identity", query)
            return self._build_response(
                query=query,
                answer=_IDENTITY_RESPONSE,
                sources=[],
                safety_result=safe_result,
                model_used="identity_shortcut",
                tokens_used=0,
                start_time=start_time,
            )

        # ── Step 1b: Capability question shortcut ────────────────────────
        # "чи надад юугаар тусалж чадах вэ", "чи юу хийж чадах вэ",
        # "ямар асуултад хариулдаг вэ", "юунд зориулагдсан бэ", etc.
        # These are always safe — skip the classifier so a benign help
        # request cannot be misclassified as self-harm/harassment.
        if _is_capability_question(query) and not has_crisis:
            _log_route("capability", query)
            return self._build_response(
                query=query,
                answer=_CAPABILITY_RESPONSE,
                sources=[],
                safety_result=safe_result,
                model_used="capability_shortcut",
                tokens_used=0,
                start_time=start_time,
            )

        # ── Step 2: Greeting shortcut — skip Ollama ──────────────────────
        if normalized in _GREETINGS:
            _log_route("greeting", query)
            return self._build_response(
                query=query,
                answer=_GREETING_RESPONSE,
                sources=[],
                safety_result=safe_result,
                model_used="shortcut",
                tokens_used=0,
                start_time=start_time,
            )

        # ── Step 3: Safety classification ────────────────────────────────
        if self.classifier:
            safety_result = self.classifier.predict(query)
        else:
            safety_result = dict(safe_result)

        # ── Step 4: Downgrade false-positive crisis flags ────────────────
        # If the classifier flagged self_harm / harassment but the text
        # contains no real crisis indicator, treat the query as safe.
        # This prevents general help phrases ("туслаач", "тусалж чадах уу")
        # from triggering the emergency response.
        if (not safety_result["is_safe"]
                and safety_result["label"] in _DOWNGRADEABLE_LABELS
                and not has_crisis):
            safety_result = {
                "label": "safe",
                "label_id": 0,
                "confidence": safety_result.get("confidence", 1.0),
                "is_safe": True,
                "all_scores": safety_result.get("all_scores", {}),
            }

        # ── Step 5: Block truly unsafe input ─────────────────────────────
        if not safety_result["is_safe"]:
            label = safety_result["label"]
            _log_route(f"crisis:{label}", query)
            safety_response = SAFETY_RESPONSES.get(label, {}).get(
                "mn", "Уучлаарай, энэ асуултад хариулах боломжгүй байна."
            )
            return self._build_response(
                query=query,
                answer=safety_response,
                sources=[],
                safety_result=safety_result,
                model_used="classifier",
                tokens_used=0,
                start_time=start_time,
            )

        # ── Step 6: Vague query shortcut — skip Ollama ───────────────────
        # Bare "туслаач", "яах вэ", "хаана хандах вэ" etc. → clarification.
        # Very short queries also fall through here, but capability questions
        # were already handled in Step 1 so they don't hit this branch.
        if normalized in _VAGUE_QUERIES or len(normalized) <= 5:
            _log_route("vague_shortcut", query)
            return self._build_response(
                query=query,
                answer=_CLARIFICATION_RESPONSE,
                sources=[],
                safety_result=safety_result,
                model_used="shortcut",
                tokens_used=0,
                start_time=start_time,
            )

        # ── Step 7: RAG retrieval + LLM generation ───────────────────────
        if not (self.rag and self.rag.is_ready):
            _log_route("index_not_ready", query)
            return self._build_response(
                query=query,
                answer="Мэдээллийн сан бэлэн болоогүй байна. Эхлээд баримт бичиг оруулна уу.",
                sources=[],
                safety_result=safety_result,
                model_used="",
                tokens_used=0,
                start_time=start_time,
            )

        # Prepend category context to the query for better retrieval relevance
        search_query = query
        if category and category in _CATEGORY_CONTEXT:
            search_query = _CATEGORY_CONTEXT[category] + query
        retrieved = self.rag.search(search_query)

        if not retrieved:
            _log_route("fallback:no_retrieval", query)
            return self._build_response(
                query=query,
                answer=_UNCLEAR_INTENT_RESPONSE,
                sources=[],
                safety_result=safety_result,
                model_used="unclear_intent",
                tokens_used=0,
                start_time=start_time,
            )

        rag_result = self.generator.generate(query, retrieved)
        route_label = rag_result.get("model_used") or "retrieval"
        if route_label == "faq_direct":
            _log_route("faq", query)
        elif route_label == "source_fallback":
            _log_route("fallback:ollama_timeout", query)
        else:
            _log_route("retrieval", query)

        # Post-generation sanity check: if the LLM produced something that
        # looks like a raw retrieval snippet (starts with "[1] filename"),
        # or is suspiciously empty/short, fall back to the unclear-intent
        # message instead of confusing the user.
        answer_text = (rag_result.get("answer") or "").strip()
        if self._looks_like_raw_snippet(answer_text) or len(answer_text) < 10:
            _log_route("fallback:raw_snippet", query)
            rag_result["answer"] = _UNCLEAR_INTENT_RESPONSE
            rag_result["model_used"] = "unclear_intent"

        return self._build_response(
            query=query,
            answer=rag_result["answer"],
            sources=rag_result.get("sources", []),
            safety_result=safety_result,
            model_used=rag_result.get("model_used", ""),
            tokens_used=rag_result.get("tokens_used", 0),
            start_time=start_time,
        )

    def _build_response(
        self,
        query: str,
        answer: str,
        sources: list,
        safety_result: dict,
        model_used: str,
        tokens_used: int,
        start_time: float,
    ) -> dict:
        """Build the final response dict and log to database."""
        response_time_ms = int((time.time() - start_time) * 1000)

        chat_id = self._log_chat(
            query=query,
            answer=answer,
            sources=sources,
            safety_label=safety_result["label"],
            safety_confidence=safety_result["confidence"],
            model_used=model_used,
            tokens_used=tokens_used,
            response_time_ms=response_time_ms,
        )

        return {
            "answer": answer,
            "sources": sources,
            "safety": {
                "label": safety_result["label"],
                "confidence": safety_result["confidence"],
                "is_safe": safety_result["is_safe"],
            },
            "chat_id": chat_id,
            "response_time_ms": response_time_ms,
            "model_used": model_used,
        }

    def _log_chat(
        self, query, answer, sources, safety_label,
        safety_confidence, model_used, tokens_used, response_time_ms,
    ) -> int:
        """Log a chat interaction to the database."""
        try:
            with get_db() as conn:
                cursor = conn.execute(
                    """INSERT INTO chat_logs
                       (query, answer, sources_json, safety_label, safety_confidence,
                        model_used, tokens_used, response_time_ms)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        query, answer, json.dumps(sources, ensure_ascii=False),
                        safety_label, safety_confidence, model_used,
                        tokens_used, response_time_ms,
                    ),
                )
                return cursor.lastrowid
        except Exception as e:
            print(f"Error logging chat: {e}")
            return -1
