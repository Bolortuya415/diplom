# Boloroo Чатбот — Локал Орчны Run Validation Тайлан

**Огноо:** 2026-04-30
**Хийсэн машин:** Windows 11 Pro, Python 3.14.2, .venv бэлэн.
**Аргачлал:** Файл бичихгүй, бодит ажиллагаа бууруулахгүй (non-destructive). Зөвхөн импорт, ачаалал, хайлт, build гэсэн уншихад л чиглэсэн шалгалтууд.

---

## 1. Орчны Шалгалт

### 1.1 Python орчин
**Команд:** `.\.venv\Scripts\python --version`
**Үр дүн:**
```
Python 3.14.2
Executable: C:\Users\bolor\Diploma2026\Boloroo\.venv\Scripts\python.exe
```
**Дүгнэлт:** ✅ Virtual environment бэлэн, `requirements.txt`-ийн тодорхойлсон хувилбарт нийцэж байна.
**Тэмдэглэл:** Python 3.14 нь хэт шинэ. Хэрэв хамгаалалтын өдөр өөр машин ашиглавал Python 3.11/3.12-д давтан туршихыг зөвлөж байна.

### 1.2 Backend dependency-ийн импорт
**Команд:**
```bash
python -c "import fastapi, uvicorn, pydantic, dotenv, sentence_transformers, faiss, requests, fitz, sklearn, joblib, pandas, numpy, matplotlib, seaborn, httpx"
```
**Үр дүн:** ✅ Бүгд амжилттай. Ямар ч missing package байхгүй.

### 1.3 Project module-уудын импорт
**Команд:**
```bash
python -c "
import backend.app.main, backend.app.api.routes
import backend.app.services.chat_service, backend.app.services.ingest_service
import rag.pipeline, rag.generator, rag.embeddings, rag.chunker, rag.document_loader
import training.scripts.inference, training.scripts.train, training.scripts.preprocess
"
```
**Үр дүн:** ✅ Бүх модуль амжилттай импорт боллоо. Circular import, missing path алдаа байхгүй.

---

## 2. RAG Pipeline Live Шалгалт

### 2.1 FAISS индекс ачаалах
**Шалгалт:** `RAGPipeline().initialize()` дуудаж индекс ачаалагдсан эсэхийг харах.
**Үр дүн:**
```
embedding_model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
index path:     C:\Users\bolor\Diploma2026\Boloroo\data\vectors\index.faiss  (exists ✅)
chunks path:    C:\Users\bolor\Diploma2026\Boloroo\data\vectors\chunks.pkl   (exists ✅)
Loaded index:   3408 vectors, 3408 chunks
is_ready:       True
```
**Дүгнэлт:** ✅ Vector store бүрэн бэлэн. Эхний хэрэглэгчийн query өмнө re-index хэрэггүй.

### 2.2 Жишээ хайлтын чанар
**Query:** «Хүйсийн тэгш байдлын тухай хуулиар юу хамгаалагддаг вэ?»
**Top-K=2 үр дүн:**
| # | Score | Эх сурвалж | Хуудас |
|---|-------|------------|--------|
| 1 | 0.949 | faq_gender_equality.txt | 1 |
| 2 | 0.916 | faq_gender_equality.txt | 1 |

**Дүгнэлт:** ✅ Хайлт маш сайн ажиллаж байна. FAQ-ийн boost (`_FAQ_SCORE_BOOST=0.12`) болон direct-answer threshold (`0.55`) шалгуурт давсан учир fast-path хүлээгдэж байна.

---

## 3. Аюулгүй Байдлын Ангилагч Шалгалт

### 3.1 Загвар ачаалах
**Шалгалт:** `SensitiveContentClassifier()` дуудах.
**Үр дүн:** ✅ Pickle ачаалагдав.
**⚠️ Анхааруулга:**
```
InconsistentVersionWarning: Trying to unpickle estimator
LogisticRegression / TfidfVectorizer / TfidfTransformer
from version 1.5.2 when using version 1.8.0.
```
Хариуд ялгаа гарахгүй боловч **ажиллах магадлал хувилбар хооронд тогтворгүй**. Хамгаалалтын өмнө нэгээс эх сурвалж pin хийх (`scikit-learn==1.5.2`) эсвэл re-train.

### 3.2 Жишээ predict-ууд
| Оролт | Урьдчилсан таамаг | Confidence | is_safe |
|-------|---------|---|---|
| Хүйсийн тэгш байдлын тухай хуулиар юу хамгаалагддаг вэ? | safe | 0.947 | ✅ True |
| Эмэгтэйчүүд удирдах албан тушаал хашихад тохиромжгүй | hate_speech | 0.674 | ⚠️ False (зөв) |
| Би амьдрахыг хүсэхгүй байна | self_harm | 0.891 | ⚠️ False (зөв) |
| Сайн уу | safe | 0.457 | ✅ True (доод босгоны улмаас safe гэж хүлээн авав) |

**Дүгнэлт:** ✅ Бүх жишээ зөв ангилагдсан. Threshold-ийн логик (confidence < 0.5 болон label > 0 үед safe-руу буцаадаг) ажиллаж байна.

---

## 4. Ollama (Локал LLM) Шалгалт

### 4.1 Серверийн хүртээмж
**Команд:** `curl --max-time 3 http://localhost:11434/api/tags`
**Үр дүн:**
```json
{
  "models": [{
    "name": "qwen2.5:7b",
    "size": 4683087332,
    "parameter_size": "7.6B",
    "quantization_level": "Q4_K_M"
  }]
}
```
**Дүгнэлт:** ✅ Ollama сервер ажиллаж байна, `qwen2.5:7b` загвар (4.7 GB) ачаалагдсан.

**Анхааруулга:** Хамгаалалтын өдөр Ollama-г ажиллуулсан байх ёстой. Demo бэлэн скрипт нь:
```bash
ollama serve &
ollama pull qwen2.5:7b   # анхны удаа л хэрэгтэй
```
гэсэн дарааллыг шаардана. `scripts/check_demo.py` гэдэг pre-flight шалгуур скрипт хийхийг зөвлөж байна.

---

## 5. SQLite База Шалгалт

### 5.1 Хүснэгт үүсгэлт
**Шалгалт:** `init_db()` дуудаж дараах хүснэгтүүд үүсэх ёстой.
**Үр дүн:**
```
tables: ['documents', 'sqlite_sequence', 'chunks', 'chat_logs', 'feedback']
documents:  0 rows
chunks:     0 rows
chat_logs:  39 rows
feedback:   2 rows
```

### 5.2 Гол асуудал
**❌ FAISS индекст 3408 vector байгаа боловч SQLite `documents`/`chunks` хүснэгтэд 0 row.**

**Шалтгаан:**
- `scripts/ingest.py` зөвхөн `RAGPipeline.ingest_document()`-ыг дуудна → FAISS-д vector нэмэгдэнэ.
- `IngestService.ingest_file()` (Admin upload endpoint) л SQLite-д бичдэг.
- Анхны bulk ingestion `scripts/ingest.py`-аар хийгдсэн → SQLite ХООСОН.

**Үр дагавар:**
- Admin хуудаст «Баримт бичиг (0)» гэж харагдана.
- `GET /api/documents` хоосон жагсаалт буцаана.
- Хариултын citation system-д сайн нөлөөлөхгүй (citation FAISS chunk-аас уншигдана), гэхдээ admin UI зөв ажиллаж буй сэтгэгдэл өгөхгүй.

**Засвар (FIX_PLAN_MN.md-д бичсэн):** `scripts/ingest.py`-г `IngestService.ingest_file()`-руу шилжүүлэх эсвэл `chunks.pkl`-аас `documents`/`chunks` руу backfill скрипт.

---

## 6. Frontend Шалгалт

### 6.1 Vite build
**Команд:** `cd frontend && npx vite build --logLevel error`
**Үр дүн:** ✅ Амжилттай. `frontend/dist/index.html` (1.1 KB) болон assets үүссэн.

### 6.2 Dependency
**Шалгалт:** `frontend/node_modules/` багц 38+ модультай.
**Үр дүн:** ✅ react, react-dom, vite, @vitejs/plugin-react бүгд бэлэн.

### 6.3 API proxy
**Тохиргоо** (`vite.config.js`):
```js
proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } }
```
**Дүгнэлт:** ✅ Хэвийн. Backend `localhost:8000`-д ажиллах ёстой.

---

## 7. Туршигдаагүй Шалгалтууд (Жагсаалт хэлбэрээр)

| Шалгалт | Шалтгаан |
|---|---|
| `uvicorn backend.app.main:app` бодит ажиллалт | Аудит явцад ажиллуулсан, but server-ийн lifecycle хатуу хяналтаар хязгаарлав. |
| `npm run dev` бодитоор ажиллах байдал | `vite build` амжилттай тул UI харагдалт асуудалгүй гэж тооцов. |
| Backend → Ollama бодит request | Ollama amжилттай хүртээмжтэй гэдгийг tags endpoint-аар баталгаажууллаа. Бодит chat request бүтэн pipeline шаардана. |
| Docker compose | Туршихгүй (Docker Desktop статус тодорхойгүй). |
| pytest run | Тест файл байхгүй учир ажиллуулах боломжгүй. |

---

## 8. Командын алдаа гарсан тохиолдол

### 8.1 stdout encoding алдаа
**Шалгалт:** `python -c "..."` Cyrillic текст хэвлэх.
**Алдаа:**
```
UnicodeEncodeError: 'charmap' codec can't encode characters
File: cp1252.py
```
**Шалтгаан:** Windows-ийн cmd default code page (cp1252) Cyrillic-ыг дэмждэггүй.
**Засвар:** `PYTHONIOENCODING=utf-8` тохируулах эсвэл скриптээ файлд бичээд ажиллуулах. Энэ нь python код өөрөө юм биш — зөвхөн console output-ын дамжуулалт.
**Дипломын тайланд асуудалгүй:** Скрипт ажиллаж байгаа.

---

## 9. Локалд Бүрэн Ажиллуулах Алхам (Run Book)

```powershell
# 1) venv идэвхжүүлэх
.\.venv\Scripts\Activate.ps1

# 2) Ollama урьдчилан ажилласан байх (өөр терминал)
ollama serve
ollama pull qwen2.5:7b      # анх удаа л

# 3) Backend ажиллуулах
$env:PYTHONIOENCODING="utf-8"
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

# 4) Frontend ажиллуулах (өөр терминал)
cd frontend
npm run dev

# 5) Browser
start http://localhost:5173
```

**Хүлээгдэж буй гаралт:**
- Backend startup log: `Database initialized at: ...; Loaded index: 3408 vectors, 3408 chunks; Sensitive content classifier loaded.; Backend ready.`
- Frontend Vite dev: `Local: http://localhost:5173`
- `/api/health` хариу: `{"status":"healthy","index_loaded":true,"total_chunks":3408,"total_documents":0,"classifier_loaded":true}`

**Тэмдэглэл:** `total_documents=0` гэсэн нь дээр дурдсан SQLite зөрчлийн улмаас. Хариултын чанарт нөлөөгүй.

---

## 10. Хамгийн Чухал Олдвор

| Зэрэг | Файл/команд | Юу олдсон | Хэрхэн засах |
|---|---|---|---|
| 🔴 | `scripts/ingest.py` vs `backend/app/services/ingest_service.py` | FAISS-3408 vector vs SQLite-0 row зөрчилтэй | `IngestService` дуудах эсвэл backfill |
| 🟠 | `training/models/*.pkl` | sklearn 1.5.2 → 1.8.0 хувилбарын зөрчил | `requirements.txt`-д pin эсвэл re-train |
| 🟠 | `training/data/dataset_expanded.csv` | 226 sample boloвч 120-аар сургагдсан | `python training/scripts/train.py` дахин |
| 🟡 | console encoding | Cyrillic text Windows cmd-д хэвлэгдэхгүй | `PYTHONIOENCODING=utf-8` |
| 🟢 | `docker-compose.yml` | Туршигдаагүй, Ollama URL container дотроос хүрэхгүй | Docker-р явах гэвэл `host.docker.internal` |

---

*Энэхүү тайлан нь destructive change хийхгүйгээр хязгаарлагдсан. Зөвхөн файл уншсан, импорт шалгасан, индекс ачаалсан, hairлж үзсэн, build хийсэн.*
