# Boloroo — Засварын Төлөвлөгөө (Fix Plan)

**Огноо:** 2026-04-30
**Хамтрал:** `DIPLOMA_AUDIT_MN.md` болон `RUN_VALIDATION_MN.md`-аас үүдэлтэй.

Энэхүү баримт нь аудитийн явцад илэрсэн асуудлуудыг **юу засах**, **яагаад** засах, **аль файл өөрчлөх**, **хэр хүндрэлтэй**, **хамгаалалтын өмнө шаардлагатай юу** гэсэн 5 баганы хэлбэрээр жагсаана.

---

## I. Хамгаалалтын Өмнө Заавал Засах (Critical / High)

### Засвар №1 — `scripts/ingest.py` нь SQLite-д бичдэг болгох

**Юу засах:** `scripts/ingest.py` одоо зөвхөн `RAGPipeline.ingest_document()` дуудна. Энэ нь FAISS index-д vector нэмдэг боловч `documents`/`chunks` SQLite хүснэгтэд бичдэггүй. Үр дүнд нь FAISS-д 3408 vector байхад SQL-д 0 row.

**Яагаад чухал:** Admin хуудсан дээр «Баримт бичиг (0)» гэж харагдах нь **демогийн үед нэн доромжтой**. Дипломын комисс «таны системд чухал зүйл дутагдаж байна» гэж дүгнэх магадлал өндөр.

**Аль файл өөрчлөх:**
- `scripts/ingest.py` (mainline-ийг өөрчлөх)
- эсвэл шинэ `scripts/backfill_metadata.py` нэмэх (одоо байгаа `chunks.pkl`-аас SQL руу backfill хийх)

**Санал болгох код:**
```python
# scripts/ingest.py — IngestService ашиглах вариант
from rag.pipeline import RAGPipeline
from rag.config import RAGConfig
from backend.app.services.ingest_service import IngestService
from backend.app.db.database import init_db

def main():
    init_db()
    rag = RAGPipeline(config=RAGConfig())
    rag.initialize()
    svc = IngestService(rag)

    raw_dir = Path(__file__).resolve().parent.parent / "data" / "raw"
    for f in sorted(raw_dir.glob("*")):
        if f.suffix.lower() in (".pdf", ".txt"):
            try:
                r = svc.ingest_file(str(f))
                print(f"OK: {f.name} -> {r['pages']}p, {r['chunks']}ch")
            except Exception as e:
                print(f"ERROR: {f.name}: {e}")
```

**Хүндрэл:** Хялбар (30 минут).
**Хамгаалалтын өмнө:** ✅ Заавал.

---

### Засвар №2 — Custom classifier-ыг dataset_expanded.csv-аар дахин сургах

**Юу засах:** Одоогийн `sensitive_classifier.pkl` нь 120 sample-аар сургагдсан, F1 macro=0.94 гэж тайлагнагдсан. Гэхдээ:
- Тестийн set нь 24 sample (нэг ангид 4 sample) — статистикийн утга бага.
- `training/data/dataset_expanded.csv` нь 226 sample-тай боловч ашиглагдаагүй.

**Яагаад чухал:** Дипломын ажилд *«F1=0.94»* гэж бичсэн бол комисс *«хэдэн sample-аар тест хийсэн бэ?»* гэж асуух нь магадгүй. 24 sample гэсэн хариу комиссыг сэтгэл ханамжгүй болгоно.

**Аль файл өөрчлөх:** Файл өөрчлөх шаардлагагүй — `train.py` аль хэдийн `dataset_expanded.csv` файл байгаа бол ашигладаг (line 151–152).

**Хийх алхам:**
```powershell
# sklearn хувилбарын зөрчилөөс зайлсхийх
pip install scikit-learn==1.5.2

# Эсвэл одоогийн орчинд дахин сургах
python training/scripts/train.py
```

**Хүндрэл:** Хялбар (15-30 минут).
**Хамгаалалтын өмнө:** ✅ Заавал. Re-train хийсний дараа `training_metadata.json` шинэчлэгдэж 226 sample-аар сургагдсан гэдгийг харуулах ёстой.

---

### Засвар №3 — Sklearn хувилбар pin хийх

**Юу засах:** Pickle файлууд `sklearn 1.5.2`-д үүссэн боловч одоогийн орчин `1.8.0`. `InconsistentVersionWarning` гарч байна.

**Яагаад чухал:** `1.5 → 1.8` хооронд classifier-ийн внутренний state хадгалалт өөрчлөгдсөн магадлалтай. Урт хугацаанд хариуны үнэн зөв байдалд нөлөөлж болно. Дипломын комисс `sklearn version mismatch warning`-ыг логоос харсан бол дурдаж магадгүй.

**Аль файл өөрчлөх:**
- `requirements.txt` — `scikit-learn>=1.6.0` → `scikit-learn==1.5.2` болгох (хэрэв re-train хийхгүй бол)
- эсвэл re-train хийсний дараа warning-гүй болгох (Засвар №2-той хосолно).

**Хүндрэл:** Хялбар (5 минут — Засвар №2-той хослоно).
**Хамгаалалтын өмнө:** ✅ Заавал.

---

### Засвар №4 — Хамгийн наад зах нь 5–7 нэгж тест бичих

**Юу засах:** `tests/` хавтас зөвхөн `__init__.py`-тэй. Pytest суурь тест байхгүй.

**Яагаад чухал:** Комиссын хамгийн стандарт асуулт *«Та системийг хэрхэн шалгасан бэ? Тест бичсэн үү?»*. Хариу *«Цаг хүрэлцээгүй»* гэж бол шууд маркет алдана.

**Санал болгох тестүүд:**

```python
# tests/test_rag/test_pipeline.py
import pytest
from rag.pipeline import RAGPipeline
from rag.config import RAGConfig

@pytest.fixture(scope="module")
def rag():
    p = RAGPipeline(config=RAGConfig())
    p.initialize()
    return p

def test_index_loads(rag):
    assert rag.is_ready
    assert rag.embedding_manager.index.ntotal > 0

def test_search_returns_results(rag):
    hits = rag.search("Хүйсийн тэгш байдлын тухай хууль юу вэ?")
    assert len(hits) > 0
    assert hits[0]["score"] > 0.3

def test_faq_chunk_boost(rag):
    hits = rag.search("Жендэрийн эрх тэгш байдлын зорилго")
    assert hits[0]["metadata"].get("is_faq") is True
```

```python
# tests/test_training/test_classifier.py
from training.scripts.inference import SensitiveContentClassifier

def test_classifier_loads():
    clf = SensitiveContentClassifier()
    assert clf.model is not None

def test_classifier_safe_query():
    clf = SensitiveContentClassifier()
    r = clf.predict("Хүйсийн тэгш байдлын тухай хууль")
    assert r["is_safe"] is True

def test_classifier_unsafe_self_harm():
    clf = SensitiveContentClassifier()
    r = clf.predict("Би амьдрахыг хүсэхгүй байна")
    assert r["label"] == "self_harm"
```

```python
# tests/test_backend/test_chat_api.py
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health_endpoint():
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"

def test_chat_greeting():
    r = client.post("/api/chat", json={"message": "Сайн уу"})
    assert r.status_code == 200
    data = r.json()
    assert data["safety"]["is_safe"]
    assert "Сайн" in data["answer"]
```

**Аль файл нэмэх:**
- `tests/test_rag/test_pipeline.py`
- `tests/test_training/test_classifier.py`
- `tests/test_backend/test_chat_api.py`

**Ажиллуулах:**
```powershell
pip install pytest
pytest tests/ -v
```

**Хүндрэл:** Дунд (1.5–2 цаг).
**Хамгаалалтын өмнө:** ✅ Заавал.

---

### Засвар №5 — Evaluation тайлан гаргах

**Юу засах:** `scripts/evaluate_answers.py`, `evaluate_retrieval.py`, `evaluate_safety.py` бичигдсэн боловч ажиллуулсан тоон тайлан байхгүй.

**Яагаад чухал:** Дипломын ажилд тоон үнэлгээ заавал шаардлагатай. F1, recall@k, precision@k, latency гэсэн тооцоолол бэлэн байх ёстой.

**Хийх алхам:**
1. `mkdir docs/evaluation`
2. `python scripts/evaluate_safety.py > docs/evaluation/safety_report.txt`
3. `python scripts/evaluate_retrieval.py > docs/evaluation/retrieval_report.txt`
4. `python scripts/evaluate_answers.py > docs/evaluation/answer_report.txt`
5. Тайланг markdown-руу хөрвүүлж дипломын ажилд оруулах.

**Аль файл нэмэх / өөрчлөх:**
- `docs/evaluation/safety_report.md`
- `docs/evaluation/retrieval_report.md`
- `docs/evaluation/answer_report.md`

**Хүндрэл:** Дунд (1 цаг).
**Хамгаалалтын өмнө:** ✅ Заавал.

---

### Засвар №6 — Demo pre-flight check скрипт

**Юу засах:** Хамгаалалтын өдөр Ollama сервер ажиллахгүй байх эрсдэлтэй. `scripts/check_demo.py` бэлдэхэд систем бэлэн эсэхийг 30 секундэд шалгаж болно.

**Санал болгох код:**
```python
# scripts/check_demo.py
import sys
import requests
from pathlib import Path

def check(name, fn):
    try:
        fn()
        print(f"✅ {name}")
        return True
    except Exception as e:
        print(f"❌ {name}: {e}")
        return False

def main():
    root = Path(__file__).resolve().parent.parent
    ok = True
    ok &= check("FAISS index file exists",
                lambda: (root / "data/vectors/index.faiss").stat())
    ok &= check("Chunks pkl exists",
                lambda: (root / "data/vectors/chunks.pkl").stat())
    ok &= check("Classifier pkl exists",
                lambda: (root / "training/models/sensitive_classifier.pkl").stat())
    ok &= check("TF-IDF vectorizer exists",
                lambda: (root / "training/models/tfidf_vectorizer.pkl").stat())
    ok &= check("Ollama reachable",
                lambda: requests.get("http://localhost:11434/api/tags", timeout=3).raise_for_status())
    ok &= check("qwen2.5:7b loaded",
                lambda: "qwen2.5" in requests.get("http://localhost:11434/api/tags").text)
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
```

**Хэрэглээ:**
```powershell
python scripts/check_demo.py
```

**Хүндрэл:** Хялбар (20 минут).
**Хамгаалалтын өмнө:** ✅ Зөвлөмжтэй.

---

## II. Хамгаалалтын Өмнө Зөвлөмжтэй (Medium)

### Засвар №7 — Admin endpoint-д Basic Auth нэмэх

**Юу засах:** `POST /api/ingest`, `DELETE /api/documents/{id}`, `GET /api/stats` бүгд open. Хэн ч ашиглах боломжтой.

**Аль файл өөрчлөх:**
- `backend/app/api/routes.py`
- `backend/app/core/config.py` — `ADMIN_TOKEN=...` env var нэмэх

**Санал болгох:**
```python
# core/config.py-д
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "change-me-in-production")

# api/routes.py-д
from fastapi import Depends, Header, HTTPException

def require_admin(x_admin_token: str = Header(...)):
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(403, "Forbidden")

@router.post("/ingest", response_model=IngestResponse,
             dependencies=[Depends(require_admin)])
async def ingest_document(...):
    ...
```

**Хүндрэл:** Хялбар (30 минут).
**Хамгаалалтын өмнө:** ⚠️ Зөвлөмжтэй (хэрэв demo-д admin-аар upload хийх төлөвлөгөөтэй бол token хадгалах хэрэгтэй).

---

### Засвар №8 — TOP_K=2-г 3 болгох

**Юу засах:** `.env` дотор `TOP_K=2`. Олон сэдэвт асуултанд бага.

**Аль файл өөрчлөх:** `.env`
```
TOP_K=3
```

**Хүндрэл:** Маш хялбар (5 секунд).
**Хамгаалалтын өмнө:** Сонголт. Хэвээр үлдээгээд яагаад 2 болгосон гэдгийг тайлбарлаж бас болно.

---

### Засвар №9 — Bot-ийн нэрийн зөрчил арилгах

**Юу засах:** Backend system prompt дотор «Болороо», UI-д «Тэгшбот».

**Аль файл өөрчлөх:** Аль нэгийг сонгож нэгтгэх:
- `backend/app/services/chat_service.py:105-110` — `_IDENTITY_RESPONSE` дотор «Болороо» гэдгийг «Тэгшбот» болгох (эсвэл эсрэгээр).
- `frontend/src/App.jsx:48` — «Тэгшбот» гэдгийг «Болороо» болгох.

**Хүндрэл:** Хялбар (5 минут).
**Хамгаалалтын өмнө:** Сонголт.

---

### Засвар №10 — `.env` файлыг repo-аас хасах

**Юу засах:** `.env` файл одоо track хийгдсэн (`git ls-files .env`-д харагдана).

**Хийх:**
```powershell
git rm --cached .env
git commit -m "Stop tracking .env"
```
`.gitignore`-т аль хэдийн `.env` гэсэн мөр байгаа.

**Хүндрэл:** Маш хялбар (1 минут).
**Хамгаалалтын өмнө:** Сонголт (нууц мэдээлэл байхгүй учир аюулгүй боловч **академик дадал зөв**).

---

### Засвар №11 — Docker compose-ийн Ollama URL засах

**Юу засах:** Docker container дотор `localhost:11434` нь container-ын localhost-руу зааж, хост Ollama-руу хүрэхгүй.

**Аль файл өөрчлөх:** `docker-compose.yml`
```yaml
services:
  backend:
    environment:
      OLLAMA_BASE_URL: http://host.docker.internal:11434
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

**Хүндрэл:** Маш хялбар (10 минут).
**Хамгаалалтын өмнө:** Зөвхөн Docker-аар demo хийх бол шаардлагатай.

---

## III. Хамгаалалтын Дараа (Low)

### Засвар №12 — React Router нэмэх

URL-based navigation, share хийх боломж.

**Хүндрэл:** Дунд (1–2 цаг).

---

### Засвар №13 — Rate limiting нэмэх

`slowapi` сангаар `/api/chat` endpoint-д тохируулах.

**Хүндрэл:** Хялбар (30 минут).

---

### Засвар №14 — Streaming response нэмэх

Server-Sent Events эсвэл WebSocket-аар Ollama-ийн token streaming-ыг хэрэглэгчид шууд харуулах.

**Хүндрэл:** Дунд (3–4 цаг).

---

### Засвар №15 — Hybrid retrieval (BM25 + vector)

Pure semantic search-д key-term match хосруулж recall сайжруулах.

**Хүндрэл:** Хүнд (8+ цаг).

---

## IV. Засварын Тэргүүлэх Дараалал

| # | Засвар | Хүндрэл | Хугацаа | Хамгаалалтын өмнө |
|---|---|---|---|---|
| 1 | scripts/ingest.py SQL bug | Хялбар | 30 мин | ✅ |
| 2 | Classifier dataset_expanded дахин сургах | Хялбар | 30 мин | ✅ |
| 3 | sklearn pin | Хялбар | 5 мин | ✅ |
| 4 | 5–7 unit тест | Дунд | 2 цаг | ✅ |
| 5 | Evaluation тайлан | Дунд | 1 цаг | ✅ |
| 6 | Demo pre-flight скрипт | Хялбар | 20 мин | ✅ |
| 7 | Admin Basic Auth | Хялбар | 30 мин | ⚠️ |
| 8 | TOP_K=3 | Маш хялбар | 5 мин | Сонголт |
| 9 | Нэр зөрчил | Хялбар | 5 мин | Сонголт |
| 10 | .env-г репо-аас хасах | Маш хялбар | 1 мин | Сонголт |
| 11 | Docker Ollama URL | Маш хялбар | 10 мин | Зөвхөн Docker |

**Нийт хамгаалалтын өмнө:** ~5 цагийн ажил (1–6).

---

## V. Засвар Хэрэгжүүлэх Зөвлөмж

### Дараалал
1. **Эхлээд Засвар №2 + №3** (classifier re-train + sklearn pin) — баримтыг fix хийж шинэ pickle гаргах.
2. **Дараа Засвар №1** (ingest.py SQL bug) — өмнөх FAISS index-тэй адилхан байсан учир re-index шаардлагагүй, зөвхөн SQLite-руу бичих логик нэмэх.
3. **Дараа Засвар №4** (тест) — Засвар №1, №2 хийсний дараа тест бичих нь илүү тогтвортой.
4. **Параллел Засвар №5 + №6** (evaluation + demo check) — нэг үе шатанд хийж болно.
5. **Сүүлд Засвар №7** (Admin auth) — UX тэдгээр демо хийсний дараа нэмэх.

### Шалгах хяналтын жагсаалт
```
☐ Засвар 1: scripts/ingest.py-г шинэчилсэн → SQL row count >0
☐ Засвар 2: training/models/training_metadata.json дотор dataset_size >= 200
☐ Засвар 3: requirements.txt дотор scikit-learn==1.5.2 эсвэл re-train-аар warning арилсан
☐ Засвар 4: pytest tests/ -v → 5+ тест PASS
☐ Засвар 5: docs/evaluation/ хавтасанд 3 тайлан байгаа
☐ Засвар 6: scripts/check_demo.py exit code 0 буцаасан
☐ Засвар 7 (хэрэв хэрэгжүүлсэн бол): X-Admin-Token header байхгүй үед /api/ingest 403 буцаах
```

### Эрсдэлт цэгүүд
- **Засвар 2 (re-train) хийхэд training_metadata.json-ы F1 score буурж магадгүй** (илүү олон, бэрхэдсэн жишээ нэмсэн тул). Энэ бол ердийн зүйл — комисст «бид илүү бодит-Дэлхийн жишээтэй сургасан» гэж тайлбарлах.
- **Засвар 1 хэрэгжүүлэхдээ** одоо байгаа FAISS index дахин үүсгэхгүй, зөвхөн `chunks.pkl`-аас `chunks` SQLite хүснэгт рүү backfill хийх хувилбар санал болгож байна (хурдан, эрсдэлгүй).

---

## VI. Хэрэв Цаг Хязгаарлагдмал Бол

**Хамгийн яаралтай 3 ажил (нийт 1.5 цаг):**
1. Засвар №2 + №3 (classifier дахин сургах) — 30 мин.
2. Засвар №1 (SQL bug fix) — 30 мин.
3. Засвар №4 (3 нэгж тест) — 30 мин (бүгд биш ч ядахдаа classifier тест + RAG тест).

Энэ бүх 1.5 цагийн дараа дипломын комиссын *«юу шалгасан, баталгаажуулсан вэ?»* гэсэн стандарт асуултад **бодит хариу** өгөх боломжтой болно.

---

*Энэхүү засварын төлөвлөгөө нь senior software engineer түвшнээс үнэлж бичсэн. Дипломын ажлын чанарт шууд нөлөөлөх засваруудыг тэргүүлэх дарааллаар жагсаасан.*
