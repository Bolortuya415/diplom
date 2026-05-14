"""
RAG pipeline configuration.

Defaults are tuned for a CPU-only laptop (no GPU) running Ollama locally.

Tuning decisions:
    - top_k=2: fewer chunks → shorter prompt → faster LLM eval
    - llm_max_tokens=250: 2-4 sentence answers; avoids long CPU generation
    - llm_timeout=90: kills stalled requests quickly
    - llm_model=qwen2.5:7b: solid Mongolian quality with compact prompts
    - Chunking kept at 500/50 for ingestion quality; generator truncates to 250 chars
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

# Anchor defaults to the project root so paths work from any CWD on Windows
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class RAGConfig:
    # Embedding model — multilingual, handles Mongolian well
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dimension: int = 384

    # Chunking (for ingestion quality — keep at 500)
    chunk_size: int = 500
    chunk_overlap: int = 50

    # Retrieval — 2 chunks keeps the prompt short on CPU hardware
    top_k: int = 2
    similarity_threshold: float = 0.3

    # Storage paths (absolute — independent of current working directory)
    data_dir: Path = field(default_factory=lambda: _PROJECT_ROOT / "data")
    vector_index_path: Path = field(default_factory=lambda: _PROJECT_ROOT / "data" / "vectors" / "index.faiss")
    chunk_metadata_path: Path = field(default_factory=lambda: _PROJECT_ROOT / "data" / "vectors" / "chunks.pkl")

    # LLM — served locally by Ollama
    llm_model: str = "qwen2.5:7b"
    llm_temperature: float = 0.15   # lower = more factual, less hallucination
    llm_max_tokens: int = 250       # 2-4 sentences; fast on CPU
    llm_timeout: int = 90           # seconds — aborts stalled generations

    # Ollama endpoint (override via OLLAMA_BASE_URL env var)
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )

    # Compact system prompt — fewer tokens = faster prompt eval on CPU
    # Rules: pure Mongolian, source-grounded, short answers, cite sources
    system_prompt: str = (
        "Та бол хүйсийн тэгш байдал, хүүхэд хамгаалал, ялгаварлан гадуурхалт, "
        "дарамт, нийгмийн хүртээмжтэй байдлын талаар мэдээлэл өгдөг "
        "Монгол хэлт туслах чатбот.\n"
        "Дүрэм:\n"
        "1. Зөвхөн цэвэр, байгалийн, дүрмийн алдаагүй Монгол хэлээр хариул. "
        "Англи, орос, хятад зэрэг бусад хэлний үг огт бүү хэрэглэ.\n"
        "2. Өгүүлбэрүүд бүтэн, холбоотой, утгын хувьд ойлгомжтой байх ёстой.\n"
        "3. Зөвхөн өгөгдсөн эх сурвалжид тулгуурлан хариул; зохиомол мэдээлэл нэм.\n"
        "4. Хариултаа 2–4 богино өгүүлбэрт багтаа. Илүү урт тайлбар шаардлагагүй.\n"
        "5. Эх сурвалжийн текстийг шууд үгчлэн хуулахаас татгалз; утгыг нь эргүүлэн "
        "товчоор бич.\n"
        "6. Файлын нэр, хуудасны дугаар, '[1] ...pdf (х.N)' мэтийг хариултын эхэнд "
        "бүү бич. Ашигласан эх сурвалжийг өгүүлбэрийн төгсгөлд зөвхөн [1], [2] "
        "гэсэн дугаараар дурд.\n"
        "7. Эх сурвалж хангалтгүй бол зөвхөн "
        "'Хангалттай мэдээлэл олдсонгүй.' гэж бич."
    )
