# Диаграмын Үндэс — Кодыг буцаан Engineer хийсэн Анализ

**Зориулалт:** Энэхүү баримт нь дипломын ажилд оруулах диаграмуудыг **бодит репозиторийн source code-аас** үүсгэхийн өмнөх анализ юм. Зорилго нь зураглаж буй диаграм бүрийг яг аль файл, аль функц, аль entity-аас үндэстэй болохыг тодорхой жагсаах.

**Хяналт хийсэн арга:** Бүх backend, RAG, frontend, training source code-ыг шууд уншин, өгөгдлийн сангийн схем (`init_db()`), API endpoint (`routes.py`), data class (`schemas.py`, `chunker.py`, `document_loader.py`)-ийг бодитоор үзлээ. FAISS index-г memory-руу ачаалж, classifier-аар хэдэн жишээ predict хийсэн (RUN_VALIDATION_MN.md дотор үр дүн).

---

## 1. Төслийн Бодит Бүтэц

```
Boloroo/
├── backend/app/
│   ├── api/routes.py                # 7 endpoint
│   ├── core/config.py               # env loader
│   ├── db/database.py               # SQLite init + 4 хүснэгт
│   ├── schemas/schemas.py           # 7 Pydantic class
│   ├── services/
│   │   ├── chat_service.py          # ChatService (~520 мөр)
│   │   └── ingest_service.py        # IngestService (~85 мөр)
│   └── main.py                      # FastAPI lifespan
├── rag/
│   ├── pipeline.py                  # RAGPipeline
│   ├── document_loader.py           # DocumentPage, load_pdf, load_text
│   ├── chunker.py                   # Chunk, chunk_documents, FAQ-aware
│   ├── embeddings.py                # EmbeddingManager
│   ├── generator.py                 # AnswerGenerator (~410 мөр)
│   └── config.py                    # RAGConfig
├── training/
│   ├── data/
│   │   ├── dataset.csv              # 120 sample
│   │   └── dataset_expanded.csv     # 226 sample
│   ├── models/
│   │   ├── sensitive_classifier.pkl # 58 KB
│   │   ├── tfidf_vectorizer.pkl     # 53 KB
│   │   └── training_metadata.json
│   └── scripts/
│       ├── preprocess.py            # clean_mongolian_text, LABEL_MAP
│       ├── train.py                 # LR + SVM, GridSearchCV
│       ├── inference.py             # SensitiveContentClassifier
│       └── evaluate.py
├── frontend/src/
│   ├── App.jsx                      # state-based routing
│   ├── pages/{Landing,Chat,Admin}Page.jsx
│   ├── components/{MessageBubble,SourcePanel,SafetyWarning}.jsx
│   └── services/api.js              # 6 fetch wrapper
├── data/
│   ├── raw/                         # 5 PDF + 7 TXT
│   ├── vectors/{index.faiss, chunks.pkl}
│   └── boloroo.db                   # SQLite, 122 KB
├── scripts/
│   ├── ingest.py                    # bulk ingestion
│   └── evaluate_{retrieval,answers,safety}.py
└── docker/
    ├── Dockerfile.backend
    ├── Dockerfile.frontend
    └── nginx.conf
```

---

## 2. Илэрсэн Үндсэн Компонентууд

### 2.1 Хэрэглэгчийн талын frontend
- **Технологи:** React 18.3 + Vite 5.4 (см. `frontend/package.json`).
- **Routing:** state-based `useState('landing'|'chat'|'admin')` (`App.jsx:7`). React Router байхгүй.
- **3 хуудас:** LandingPage (3 ангилал), ChatPage (chat UI + sources panel + safety warning), AdminPage (upload + health + stats).
- **API client:** `services/api.js` доторх 6 функц: `sendChat`, `submitFeedback`, `uploadDocument`, `getDocuments`, `getHealth`, `getStats`.
- **Vite proxy:** `/api` → `http://localhost:8000` (`vite.config.js:9-13`).

### 2.2 Backend API
- **Технологи:** FastAPI 0.118+, Pydantic 2.10+, Uvicorn (`requirements.txt`).
- **Entry point:** `backend/app/main.py` — `app = FastAPI(...)`, lifespan-аар startup/shutdown.
- **7 endpoint** (`backend/app/api/routes.py`):
  | Метод | Зам | Schema | Функц |
  |-------|-----|--------|-------|
  | POST | `/api/chat` | `ChatRequest` → `ChatResponse` | `chat()` |
  | POST | `/api/feedback` | `FeedbackRequest` → `FeedbackResponse` | `submit_feedback()` |
  | POST | `/api/ingest` | multipart → `IngestResponse` | `ingest_document()` |
  | GET | `/api/documents` | — → `List[DocumentInfo]` | `list_documents()` |
  | DELETE | `/api/documents/{id}` | — → `{status, document_id}` | `delete_document()` |
  | GET | `/api/health` | — → `HealthResponse` | `health_check()` |
  | GET | `/api/stats` | — → JSON dict | `get_stats()` |
- **Middleware:** CORS-ийг `CORS_ORIGINS` env var-аас ачаална (`main.py:77-83`).

### 2.3 Service давхарга
- **`ChatService`** (`backend/app/services/chat_service.py`):
  - `process_query(query, category)` — 6-step routing pipeline.
  - 3 атрибут: `rag` (RAGPipeline), `generator` (AnswerGenerator), `classifier` (SensitiveContentClassifier).
  - Helper-үүд: `_log_chat`, `_build_response`.
  - Module-level helpers: `_is_capability_question`, `_is_identity_question`, `_has_crisis_indicator`, `_normalize`.
- **`IngestService`** (`backend/app/services/ingest_service.py`):
  - `ingest_file(file_path, title)` — PDF/TXT-ийг RAG-аар ingest хийгээд SQL-д бичнэ.
  - `list_documents()` — `documents` хүснэгтээс уншина.
  - `delete_document(doc_id)` — soft delete (`status='deleted'`).

### 2.4 RAG Pipeline
- **`RAGPipeline`** (`rag/pipeline.py`):
  - `initialize()`, `is_ready` property, `ingest_document()`, `ingest_directory()`, `search()`.
- **`EmbeddingManager`** (`rag/embeddings.py`):
  - `model = SentenceTransformer(config.embedding_model)`.
  - `index: faiss.IndexFlatIP`, `chunks: list[Chunk]`.
  - `embed_texts`, `embed_query`, `build_index`, `add_to_index`, `search`, `save`, `load`.
  - FAQ score boost = +0.12, fetch_k = max(top_k*4, 8).
- **`AnswerGenerator`** (`rag/generator.py`):
  - `generate(query, retrieved_chunks)` → dict.
  - `format_context`, `format_sources`, `_check_ollama`, `_extract_law_refs`, `_get_doc_title`, `_deduplicate_chunks`.
  - FAQ direct threshold = 0.55, context chunk max chars = 250.
- **Document loader** (`rag/document_loader.py`):
  - `DocumentPage` dataclass.
  - `load_pdf(file_path)` — PyMuPDF-аар.
  - `load_text(file_path)` — UTF-8.
  - `load_document(file_path)` — extension dispatch.
  - `clean_extracted_text()`.
- **Chunker** (`rag/chunker.py`):
  - `Chunk` dataclass.
  - `chunk_text` — char-level + sentence boundary aware.
  - `chunk_documents` — FAQ detection + dispatch.
  - `_FAQ_MARKER_RE = "### FAQ N"`, `_FAQ_QUESTION_RE = "Асуулт:"`, `_FAQ_ANSWER_RE = "Хариулт:"`.

### 2.5 Safety Classifier
- **`SensitiveContentClassifier`** (`training/scripts/inference.py`):
  - 5 анги: `LABEL_MAP = {0:safe, 1:hate_speech, 2:harassment, 3:discrimination, 4:self_harm}`.
  - `predict(text)` → `{label, label_id, confidence, is_safe, all_scores}`.
  - Confidence threshold = 0.5, доор бол `safe`-руу буцаана.
- **Сургалт** (`training/scripts/train.py`):
  - LogisticRegression + LinearSVC (5-fold GridSearchCV), F1-macro оноогоор сонгоно.
  - `CalibratedClassifierCV` SVM-ийн predict_proba-д.
- **Preprocess** (`training/scripts/preprocess.py`):
  - `clean_mongolian_text`, `remove_stopwords` (49 stopword), `MONGOLIAN_STOPWORDS`.
  - `TfidfVectorizer(analyzer='char_wb', ngram_range=(2,5), max_features=5000)`.

### 2.6 Хадгалалт
- **SQLite** — `data/boloroo.db`. Хүснэгтүүд `database.py:init_db()`-д DDL-ээр бичигдсэн.
- **FAISS** — `data/vectors/index.faiss` (5 MB) + `chunks.pkl` (3 MB).
- **ML pickle** — `training/models/{sensitive_classifier,tfidf_vectorizer}.pkl` + `training_metadata.json`.
- **Эх баримт** — `data/raw/` (12 файл).

### 2.7 LLM
- **Ollama** локал серверт (port 11434) ажиллана, `qwen2.5:7b` (4.7 GB Q4_K_M).
- HTTP API: `POST /api/chat` (`generator.py:_ollama_chat_url`).

### 2.8 Auth
- **Байхгүй.** Бүх endpoint open. Identified risk in audit.

### 2.9 Deployment
- Локал: 3 параллель процесс (Vite 5173, Uvicorn 8000, Ollama 11434).
- Docker compose: backend + frontend container (Ollama хост машин дээр үлдэнэ — URL засах шаардлагатай).

---

## 3. Backend-ийн Гол Модулиуд

| Модуль | Гол анги/функц | Хариуцлага |
|--------|----------------|------------|
| `main.py` | `app`, `lifespan()` | FastAPI-ийг үүсгэх, RAG/Classifier ачаалах, CORS, router-ыг холбох |
| `core/config.py` | модуль level constants | `.env` уншиж, тогтмол утгуудыг export |
| `db/database.py` | `get_db()`, `init_db()` | SQLite холболт, 4 хүснэгт үүсгэх, WAL mode |
| `schemas/schemas.py` | 7 Pydantic class | API request/response баталгаажуулалт |
| `api/routes.py` | `router`, 7 endpoint | HTTP handler-ууд, service-руу делегат |
| `services/chat_service.py` | `ChatService.process_query()` | 6-step routing: identity → capability → greeting → safety → vague → RAG+LLM |
| `services/ingest_service.py` | `IngestService.ingest_file()` | RAG ingest + SQLite metadata write |
| `rag/config.py` | `RAGConfig` dataclass | RAG runtime тохиргоо |
| `rag/pipeline.py` | `RAGPipeline` | ingest + search facade |
| `rag/document_loader.py` | `DocumentPage`, `load_*` | PDF/TXT loader |
| `rag/chunker.py` | `Chunk`, `chunk_documents()` | FAQ-aware + char-level chunking |
| `rag/embeddings.py` | `EmbeddingManager` | SentenceTransformer + FAISS |
| `rag/generator.py` | `AnswerGenerator.generate()` | Ollama prompt + FAQ fast-path |
| `training/scripts/preprocess.py` | `clean_mongolian_text`, `LABEL_MAP` | Text cleaning, TF-IDF feature creation |
| `training/scripts/train.py` | `train_logistic_regression`, `train_svm` | Хоёр загвар сургах + хадгалах |
| `training/scripts/inference.py` | `SensitiveContentClassifier`, `SAFETY_RESPONSES` | Сургагдсан загварыг ачаалж predict |

---

## 4. Frontend-ийн Гол Модулиуд

| Модуль | Тип | Хариуцлага |
|--------|-----|------------|
| `App.jsx` | React component | Page state, brand header, navigation |
| `pages/LandingPage.jsx` | Component | 3 категори карт + жишээ асуулт |
| `pages/ChatPage.jsx` | Component | Чат харилцан үйлдэл, message list, source panel модал |
| `pages/AdminPage.jsx` | Component | Upload форм, health card, stats card, document table |
| `components/MessageBubble.jsx` | Component | Message render, feedback btn, response time |
| `components/SourcePanel.jsx` | Component | Source citation popup, law refs, score |
| `components/SafetyWarning.jsx` | Component | Safety label badge |
| `services/api.js` | Module | 6 fetch wrapper, JSON error handling |

---

## 5. Өгөгдлийн Сангийн Бүтэц (Бодит)

DDL `backend/app/db/database.py:init_db()`-д бичигдсэн.

### 5.1 `documents` хүснэгт
| Багана | Төрөл | Тайлбар |
|--------|-------|---------|
| `id` | INTEGER PK AUTOINCREMENT | Анхдагч түлхүүр |
| `title` | TEXT NOT NULL | Хүний-уншихуйц гарчиг |
| `filename` | TEXT NOT NULL UNIQUE | Файлын нэр (давхардахгүй) |
| `source_type` | TEXT DEFAULT 'pdf' | pdf эсвэл txt |
| `upload_date` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Орсон огноо |
| `page_count` | INTEGER DEFAULT 0 | Хуудасны тоо |
| `chunk_count` | INTEGER DEFAULT 0 | Үүсгэсэн chunk тоо |
| `status` | TEXT DEFAULT 'active' | active / deleted (soft) |

### 5.2 `chunks` хүснэгт
| Багана | Төрөл | Тайлбар |
|--------|-------|---------|
| `id` | INTEGER PK AUTOINCREMENT | Анхдагч түлхүүр |
| `document_id` | INTEGER NOT NULL FK→documents.id | Эх баримтын ID |
| `chunk_id` | TEXT NOT NULL UNIQUE | RAG-ийн text key (`prefix_p1_c0` etc.) |
| `chunk_index` | INTEGER NOT NULL | Глобал индекс |
| `text` | TEXT NOT NULL | Chunk текст (full Q+A эсвэл хэсэг) |
| `page_number` | INTEGER | Хуудасны дугаар |
| `char_count` | INTEGER | Тэмдэгтийн тоо |
| `metadata_json` | TEXT | metadata (`is_faq`, `faq_question`, etc.) |

Index: `idx_chunks_document ON chunks(document_id)`.

### 5.3 `chat_logs` хүснэгт
| Багана | Төрөл | Тайлбар |
|--------|-------|---------|
| `id` | INTEGER PK AUTOINCREMENT | Анхдагч түлхүүр |
| `query` | TEXT NOT NULL | Хэрэглэгчийн асуулт |
| `answer` | TEXT NOT NULL | Үүсгэсэн хариулт |
| `sources_json` | TEXT | source citation массив (JSON) |
| `safety_label` | TEXT DEFAULT 'safe' | Classifier-ийн label |
| `safety_confidence` | REAL DEFAULT 1.0 | Confidence |
| `model_used` | TEXT | qwen2.5:7b / faq_direct / shortcut etc. |
| `tokens_used` | INTEGER DEFAULT 0 | LLM token count |
| `response_time_ms` | INTEGER | Хариу хугацаа |
| `timestamp` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | |

Index: `idx_chat_logs_timestamp ON chat_logs(timestamp)`.

### 5.4 `feedback` хүснэгт
| Багана | Төрөл | Тайлбар |
|--------|-------|---------|
| `id` | INTEGER PK AUTOINCREMENT | Анхдагч түлхүүр |
| `chat_id` | INTEGER NOT NULL FK→chat_logs.id | Холбоотой chat |
| `rating` | INTEGER NOT NULL CHECK IN (-1,1) | 1=thumbs up, -1=thumbs down |
| `comment` | TEXT | Нэмэлт сэтгэгдэл (нэмэлт) |
| `timestamp` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | |

Index: `idx_feedback_chat ON feedback(chat_id)`.

### 5.5 Хамаарал
- `documents 1 — N chunks` (`chunks.document_id` → `documents.id`).
- `chat_logs 1 — N feedback` (`feedback.chat_id` → `chat_logs.id`).
- `chat_logs.sources_json` нь denormalized JSON — `chunks` руу шууд FK байхгүй (chunk_id текст байдлаар хадгалагдана).

---

## 6. RAG Pipeline-ийн Бодит Урсгал

### 6.1 Indexing (offline)
```
данс/raw/<file>
   │
   ▼
load_document()                         # rag/document_loader.py
   │   PDF → fitz.open + page.get_text()
   │   TXT → open + read
   │   clean_extracted_text() — whitespace, hyphen
   ▼
[DocumentPage(text, page_number, source_file, metadata), ...]
   │
   ▼
chunk_documents()                       # rag/chunker.py
   │   _is_faq_text() ?
   │   ├─ Yes → _parse_faq_entries() → 1 chunk per Q+A,
   │   │         metadata.is_faq=True, faq_question, faq_answer
   │   └─ No  → chunk_text(text, 500, 50) — char-level + sentence boundary
   ▼
[Chunk(chunk_id, text, source_file, page_number, chunk_index, metadata), ...]
   │
   ▼
EmbeddingManager.add_to_index()         # rag/embeddings.py
   │   _embed_text_for_chunk(c) → FAQ chunk бол c.metadata.faq_question only
   │   model.encode(texts, normalize=True)  → np.float32 (N, 384)
   │   index.add(embeddings)
   ▼
faiss.write_index(index, "data/vectors/index.faiss")
pickle.dump(chunks, "data/vectors/chunks.pkl")
```

### 6.2 Query (online)
```
ChatRequest (message, category)
   │
   ▼
ChatService.process_query()             # backend/app/services/chat_service.py
   │
   ├─ Step 1a: _is_identity_question() → return _IDENTITY_RESPONSE
   ├─ Step 1b: _is_capability_question() → return _CAPABILITY_RESPONSE
   ├─ Step 2: greeting check → return _GREETING_RESPONSE
   ├─ Step 3: classifier.predict(query) → safety_result
   ├─ Step 4: downgrade self_harm/harassment if NOT _has_crisis_indicator
   ├─ Step 5: if NOT safe → return SAFETY_RESPONSES[label]
   ├─ Step 6: vague check → return _CLARIFICATION_RESPONSE
   │
   ▼
search_query = _CATEGORY_CONTEXT[category] + query
   │
   ▼
RAGPipeline.search(search_query)        # rag/pipeline.py
   │   embed_query() → (1, 384)
   │   index.search(query_emb, fetch_k = max(top_k*4, 8))
   │   for each: filter score >= 0.3 (similarity_threshold)
   │             FAQ chunks: score += 0.12
   │   sort by score, return top_k
   ▼
retrieved_chunks: list[dict]
   │
   ▼
AnswerGenerator.generate()              # rag/generator.py
   │   format_sources(chunks) → list of citation dicts
   │   ┌─ FAQ fast-path: top.is_faq && score >= 0.55
   │   │     → return chunk.metadata.faq_answer (LLM-г тойрно)
   │   ├─ check_ollama() → if down: error response
   │   ├─ format_context(chunks) → numbered + truncated to 250 chars
   │   ├─ POST http://localhost:11434/api/chat
   │   │     system: RAGConfig.system_prompt
   │   │     user: query + context + instructions
   │   ├─ _clean_llm_answer() — strip leaked citation headers
   │   └─ Timeout / ConnectionError / Exception → fallback responses
   ▼
ChatResponse (answer, sources, safety, chat_id, response_time_ms)
   │
   ▼
DB INSERT chat_logs
   │
   ▼
JSON response → Frontend
```

---

## 7. Диаграм бүрд Ашиглагдах Файлуудын Mapping

| # | Диаграм | Гол эх сурвалж файлууд | Яагаад энэ диаграм үндэслэлтэй вэ |
|---|---------|------------------------|------------------------------------|
| 1 | System Architecture | `main.py`, `routes.py`, `chat_service.py`, `pipeline.py`, `embeddings.py`, `generator.py`, `inference.py`, `App.jsx`, `api.js`, `config.py` | Бүх ажиллагсан компонентыг (frontend ↔ backend ↔ RAG ↔ Ollama ↔ хадгалалт) бодит код дээр тулгуурлан холбох |
| 2 | ER Diagram | `database.py:init_db()`, `schemas.py` | DDL-ээс шууд гарсан 4 хүснэгт + 2 FK + 3 index. Таамаг байхгүй. |
| 3 | Class Diagram | `chat_service.py:ChatService`, `ingest_service.py:IngestService`, `pipeline.py:RAGPipeline`, `embeddings.py:EmbeddingManager`, `generator.py:AnswerGenerator`, `inference.py:SensitiveContentClassifier`, `chunker.py:Chunk`, `document_loader.py:DocumentPage`, `config.py:RAGConfig`, `schemas.py` | Хариуцлага бүхий гол анги бүгд код дотроос ирсэн |
| 4 | Sequence — Chat | `routes.py:chat()`, `chat_service.py:process_query()`, `embeddings.py:search()`, `generator.py:generate()`, `database.py` | 6-step routing pipeline бодитоор source-д бичигдсэн |
| 5 | Sequence — Ingest | `routes.py:ingest_document()`, `ingest_service.py:ingest_file()`, `pipeline.py:ingest_document()`, `document_loader.py:load_*`, `chunker.py:chunk_documents()`, `embeddings.py:add_to_index()`, `database.py` | Admin upload бодит замналыг кодын дагуу зурлаа |
| 6 | Activity — RAG | `chat_service.py:process_query()` + `pipeline.py:search()` + `generator.py:generate()` | Бүх branch (FAQ shortcut, Ollama timeout, no-retrieval fallback) бодитоор кодод бий |
| 7 | Data Flow | Бүх боловсруулах түвшний state өөрчлөлт — `schemas.py`, `chunker.py:Chunk`, `embeddings.py`, `generator.py:format_context`, `database.py` | Өгөгдлийн форматын өөрчлөлтийг dataclass + dict bодит структураас гаргалаа |
| 8 | Deployment | `main.py:app + uvicorn`, `vite.config.js`, `docker-compose.yml`, `Dockerfile.backend`, `Dockerfile.frontend`, `nginx.conf`, `rag/config.py:ollama_base_url`, `.env` | 3 порт + 4 файлын persistence + Docker сонголт бүгд бодит |
| 9 | Use Case | `LandingPage.jsx`, `ChatPage.jsx`, `AdminPage.jsx`, `routes.py` (7 endpoint) | Энгийн хэрэглэгч + админ-д харагдах боломжуудыг UI + API endpoint-аас гаргалаа |

---

## 8. Тодорхойгүй Үлдсэн Хэсгүүд (Inferred / Uncertain)

### 8.1 Auth flow
- Кодод **аль ч нэвтрэлтийн механизм байхгүй**.
- Use case диаграмд «Админ хэрэглэгч» гэсэн actor нь UI-ийн «Админ» товчийг дарж очдог логикийн дагуу зурагдлаа. Backend-д **сэргүүд**.
- **Inferred:** хамгаалалтын дараа JWT эсвэл Basic Auth нэмэх (ROADMAP).

### 8.2 Ollama Docker container
- `docker-compose.yml`-д Ollama service ороогүй.
- Inferred: хост машин дээр Ollama тусдаа ажиллана, container-ууд `host.docker.internal:11434`-руу хүрэх ёстой.
- **Деплой диаграмд** энэ хослолыг уламжилаар тэмдэглэв.

### 8.3 Frontend routing
- `App.jsx:7-19`-д `useState`-аар page state. URL хаяг өөрчлөгдөхгүй.
- Use case-д энэ нь нөлөөлөхгүй боловч **«URL share хийх»** use case байхгүй гэдгийг тэмдэглэлээ.

### 8.4 Streaming responses
- `generator.py:payload`-д `"stream": False`. SSE/WebSocket байхгүй.
- Sequence diagram-д blocking request гэдгийг тодорхой зурлаа.

### 8.5 SQLite metadata vs FAISS зөрчил
- `scripts/ingest.py` нь `RAGPipeline.ingest_document()` л дуудаж байгаагаас болж SQL `documents`/`chunks` ХООСОН (validated runtime). Гэхдээ `IngestService.ingest_file()` бол SQL-д бичих логиктой.
- ER + Activity + Sequence диаграмууд **зөв код-логик**-ийг (admin upload зам)-ийг тусгана. Bug нь runtime issue, design issue биш — диаграм design-ийн дагуу.

### 8.6 Admin UI харах боломжуудтай хязгаар
- AdminPage.jsx-д устгах товч UI **байхгүй**, харин backend-д `DELETE /api/documents/{id}` endpoint бий.
- Use case диаграмд *«Баримт бичиг устгах»* нь backend-д хэрэгжсэн боловч UI-аар хүрэхгүй гэдгийг тэмдэглэх.

### 8.7 Tests
- `tests/` хоосон. Class diagram-д `TestRAGPipeline` гэх мэт angi оруулаагүй.

### 8.8 Authentication state in chat history
- `chat_logs` хүснэгтэд `user_id` багана **байхгүй**. Систем нь анонимтай. ER diagram-д энэ гэж тэмдэглэх.

---

## 9. Live Туршилтаар Баталгаажсан (Бодит) Зүйлс

| Шалгалт | Үр дүн | Файл/Систем |
|---------|--------|-------------|
| Бүх Python модуль импорт | ✅ Pass | All `backend/`, `rag/`, `training/` |
| FAISS index ачаалал | ✅ 3408 vector | `data/vectors/index.faiss` |
| Жишээ search (top_k=2) | ✅ Score 0.949 | FAQ chunk-аас |
| Classifier predict (3 жишээ) | ✅ Зөв ангилагдсан | TF-IDF + LogReg |
| Ollama tags endpoint | ✅ Reachable | `qwen2.5:7b` (4.7 GB) |
| `vite build` | ✅ Pass | `frontend/dist/` |
| `init_db()` | ✅ 4 хүснэгт үүсэв | `boloroo.db` |
| chat_logs row count | 39 row | (өмнөх жишээ хэрэглээ) |
| documents/chunks row count | 0 row | (Bug — FIX_PLAN_MN.md дээр) |

---

## 10. Дүгнэлт

Энэхүү анализын үр дүнд **9 диаграм бүрийг бодит код-аас зурах боломжтой** гэдэг нь батлагдлаа. Тодорхойгүй гарсан хэсгүүдийг 8-р хэсэгт жагсаасан бөгөөд диаграм бүрийн тайланд **«inferred»** гэж тусгайлан тэмдэглэх болно. Дараагийн алхам нь PlantUML + Mermaid хосолсон source файлуудыг үүсгэх явдал юм.

---

*Энэхүү анализыг кодыг уншин туршиж буцаан engineer хийсэн. Бүх mapping нь `git grep`-ээр шалгагдах, файл/мөрийн ишлэлт хадгалсан.*
