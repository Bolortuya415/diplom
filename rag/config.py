"""
RAG pipeline configuration.

Stack:
    - Vector DB: ChromaDB (embedded, persisted to data/vectors/chroma/)
    - Embeddings: BGE-M3 via sentence-transformers (1024-dim, multilingual)
    - Reranker: BGE-reranker-v2-m3 via CrossEncoder (optional)
    - LLM: Google Gemini API (free tier)

Tuning notes:
    - top_k=4 with rerank → top 4 final chunks fed to the LLM
    - chunk_size=500/overlap=50: kept from previous architecture, good for
      Mongolian legal text where sentence boundaries are dense
    - Three topic categories drive per-document metadata: gender_equality,
      discrimination, disability
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

# Anchor defaults to the project root so paths work from any CWD on Windows
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class RAGConfig:
    # ── Embeddings (BGE-M3 — 1024-dim multilingual) ───────────────────
    embedding_model: str = field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    )
    embedding_dimension: int = 1024

    # ── Reranker (BGE-reranker-v2-m3) ─────────────────────────────────
    use_reranker: bool = field(default_factory=lambda: _env_bool("USE_RERANKER", True))
    reranker_model: str = field(
        default_factory=lambda: os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
    )

    # ── Chunking ──────────────────────────────────────────────────────
    chunk_size: int = 500
    chunk_overlap: int = 50

    # ── Retrieval ─────────────────────────────────────────────────────
    # top_k = final number of chunks fed to the LLM after reranking.
    # The vector store fetches a wider candidate pool (4× top_k, min 16)
    # before reranking.
    top_k: int = 4
    similarity_threshold: float = 0.0  # cosine — Chroma uses 1 - distance

    # ── Storage ───────────────────────────────────────────────────────
    data_dir: Path = field(default_factory=lambda: _PROJECT_ROOT / "data")
    chroma_persist_dir: Path = field(
        default_factory=lambda: _PROJECT_ROOT / "data" / "vectors" / "chroma"
    )
    chroma_collection: str = field(
        default_factory=lambda: os.getenv("CHROMA_COLLECTION", "boloroo_corpus")
    )

    # ── LLM: Google Gemini ────────────────────────────────────────────
    llm_model: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    )
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    llm_temperature: float = field(
        default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.15"))
    )
    llm_max_tokens: int = field(
        default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "400"))
    )

    # ── System prompt (Mongolian) ─────────────────────────────────────
    # The LLM now acts as a relevance + safety gate as well as an answer
    # generator. Order of rules matters — scope check first, hate-speech
    # check second, then the answering rules.
    system_prompt: str = (
        "Та бол 'Тэгшбот' — Монгол хэл дээрх туслах чатбот. Танай үүрэг "
        "зөвхөн дараах гурван сэдвээр Монгол хуульд тулгуурлан мэдээлэл "
        "өгөх:\n"
        "  • Хүйсийн тэгш эрх, жендэр\n"
        "  • Ялгаварлан гадуурхалт, дарамт\n"
        "  • Хөгжлийн бэрхшээлтэй иргэдийн эрх\n"
        "\n"
        "Хариулахын өмнө дараах гурван шалгуурыг дарааллаар нь хийнэ:\n"
        "\n"
        "Шалгуур 1 (Сэдэв). Хэрэв хэрэглэгчийн асуулт дээрх гурван "
        "сэдэвт хамаарахгүй (жишээ нь: спорт, хоол, технологи, ерөнхий "
        "мэдлэг, орчуулга гэх мэт) бол яг дараах хариултыг бич, өөр зүйл "
        "бүү нэм:\n"
        "  'Уучлаарай, би зөвхөн хүйсийн тэгш эрх, ялгаварлан "
        "гадуурхалт, хөгжлийн бэрхшээлтэй иргэдийн эрхийн талаарх "
        "асуултад хариулдаг. Эдгээр сэдвээр асуулт тавина уу.'\n"
        "\n"
        "Шалгуур 2 (Үзэн ядалт). Хэрэв асуултын агуулга нь хүний бүлгийг "
        "доромжилж, эрхийг үгүйсгэж, ялгаварлан гадуурхахыг сурталчилж "
        "байвал (жишээ: 'эмэгтэйчүүд ажиллах ёсгүй') яг дараах хариултыг "
        "бич:\n"
        "  'Уучлаарай, энэ агуулгад хариулах боломжгүй. Хүн бүр тэгш "
        "эрхтэй, хүндлэгдэх ёстой. Хэрэв та хохирогч бол хаана хандах "
        "талаар асууж болно.'\n"
        "  ВАЖНО: Тухайн хүн хохирогчийн талаас асууж байгаа эсэхийг "
        "сайтар ялга. 'Намайг хүйсээс болж ажилд авахгүй бол яах вэ?' "
        "гэх мэт асуулт нь ҮЗЭН ЯДАЛТ БИШ, харин туслалцаа хүсэлт юм.\n"
        "\n"
        "Шалгуур 3 (Хариулт). Хэрэв асуулт сэдэвтэй холбоотой бөгөөд "
        "үзэн ядалт биш бол доорх эх сурвалжид тулгуурлан хариулна:\n"
        "  1. Зөвхөн цэвэр, дүрмийн алдаагүй Монгол хэлээр хариул.\n"
        "  2. Зөвхөн өгөгдсөн эх сурвалжид тулгуурлан хариул; "
        "зохиомол хууль, утас, байгууллагын нэр огт нэмэхгүй.\n"
        "  3. Хэрэв эх сурвалж асуултад шууд хариулдаггүй ч холбогдох "
        "мэдээлэл (тусламжийн утас, хандах байгууллага, хуулийн зүйл) "
        "агуулж байвал, тэр мэдээллийг хэрэглэн хэсэгчилсэн хариулт өгч, "
        "илүү дэлгэрэнгүй мэдээлэлд мэргэжлийн байгууллагаас хандахыг "
        "сануулна. Зөвхөн эх сурвалж ямар ч холбогдох мэдээлэл агуулаагүй "
        "үед 'Хангалттай мэдээлэл олдсонгүй.' гэж бич.\n"
        "  4. Хариултаа 2–5 өгүүлбэрт багтаа. Шаардлагатай бол хуулийн "
        "зүйл, заалтыг нэрлэн дурд.\n"
        "  5. Эх сурвалжийн текстийг үгчлэн бүү хуул; утгыг нь эргүүлэн "
        "товчоор бич.\n"
        "  6. Файлын нэр, хуудасны дугаар, '[1] ...pdf (х.N)' мэтийг "
        "хариултын эхэнд бүү бич. Ашигласан эх сурвалжийг өгүүлбэрийн "
        "төгсгөлд зөвхөн [1], [2] гэсэн дугаараар дурд."
    )
