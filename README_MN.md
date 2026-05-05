# Boloroo (Тэгшбот) — Хүйсийн Тэгш Эрх ба Нийгмийн Хүртээмжтэй Байдлын Чатбот

## Төслийн Нэр
**Boloroo** (UI бранд: «Тэгшбот»)

## Төслийн Зорилго

Boloroo нь Монгол хэл дээр хүйсийн тэгш эрх, ялгаварлан гадуурхалт, хөгжлийн бэрхшээлтэй иргэдийн эрхийн талаар мэдээлэл, зөвлөгөө өгдөг RAG-д суурилсан туслах чатбот юм. Бакалаврын дипломын ажлын хүрээнд боловсруулагдсан энэ систем нь дараах зорилгуудыг тавьсан:

1. **Хууль эрх зүйн мэдээллийг хүртээмжтэй болгох** — Монгол улсын Жендэрийн эрх тэгш байдал, Иргэний хууль, Гэр бүлийн хүчирхийлэлтэй тэмцэх тухай, Хөгжлийн бэрхшээлтэй хүний эрхийн тухай зэрэг хууль тогтоомжийг энгийн иргэдэд ойлгомжтой хэлбэрээр хүргэх.
2. **Аюулгүй харилцан үйлдэл** — Custom-сургагдсан classifier нь хохироох, ялгаварлан гадуурхах, өөрийгөө гэмтээх агуулгыг таньж блоклох.
3. **Хувийн өгөгдлийн хамгаалал** — Бүх боловсруулалт локалаар явагдах (Ollama LLM, FAISS vector store), гадаад API-руу мэдээлэл алдагдахгүй.
4. **Эх сурвалжид тулгуурласан хариулт** — RAG нь LLM-ийн hallucination-ыг бууруулж, хариулт бүрд эх сурвалжийн citation хавсаргадаг.

## Ашигласан Технологи

| Бүрэлдэхүүн | Технологи | Хувилбар |
|---|---|---|
| Backend | Python + FastAPI | 3.14 + 0.118+ |
| Frontend | React + Vite | 18.3 + 5.4 |
| Embedding model | sentence-transformers (multilingual MiniLM) | L12-v2, 384-dim |
| Vector store | FAISS | 1.9+ |
| LLM | Ollama (qwen2.5:7b) | Q4_K_M, 4.7 GB |
| Database | SQLite (WAL mode) | built-in |
| Custom classifier | scikit-learn (TF-IDF + LogReg) | 1.5.2 |
| PDF reader | PyMuPDF (fitz) | 1.25+ |
| Pydantic validation | Pydantic | 2.10+ |
| Containerization | Docker + docker-compose | optional |

## Системийн Бүтэц

```
Boloroo/
├── backend/             # FastAPI backend
│   └── app/
│       ├── api/         # REST endpoint definitions
│       ├── core/        # Configuration loading
│       ├── db/          # SQLite session management
│       ├── schemas/     # Pydantic request/response models
│       ├── services/    # ChatService + IngestService
│       └── main.py      # Lifespan + middleware
├── frontend/            # React + Vite SPA
│   ├── src/
│   │   ├── components/  # MessageBubble, SourcePanel, SafetyWarning
│   │   ├── pages/       # LandingPage, ChatPage, AdminPage
│   │   ├── services/    # api.js (fetch wrappers)
│   │   └── styles/      # index.css
│   └── vite.config.js
├── rag/                 # RAG pipeline
│   ├── document_loader.py  # PyMuPDF + text loader
│   ├── chunker.py          # FAQ-aware + char-level chunking
│   ├── embeddings.py       # sentence-transformers + FAISS
│   ├── generator.py        # Ollama prompt + post-processing
│   ├── pipeline.py         # Orchestrator
│   └── config.py           # RAGConfig dataclass
├── training/            # Custom classifier
│   ├── data/            # dataset.csv (120) + dataset_expanded.csv (226)
│   ├── models/          # sensitive_classifier.pkl + tfidf_vectorizer.pkl
│   └── scripts/         # train.py, preprocess.py, inference.py
├── data/                # Persistent state
│   ├── raw/             # 5 PDF + 7 TXT эх баримт
│   ├── vectors/         # index.faiss + chunks.pkl
│   └── boloroo.db       # SQLite database
├── scripts/             # CLI utilities
│   ├── ingest.py        # Bulk document ingestion
│   ├── evaluate_*.py    # Evaluation scripts
│   └── evaluate_user_survey.md
├── tests/               # 🚧 Хоосон, тест бичих шаардлагатай
├── docker/              # Docker compose stack (optional)
├── docs/                # Аудит + диаграмын баримтууд (Монгол)
└── docs/diagrams/       # 7 Mermaid диаграм
```

Дэлгэрэнгүй архитектурын зураг → `docs/diagrams/01_system_architecture_mn.md`

---

## Локал Орчинд Суулгах ба Ажиллуулах

### 1. Шаардлагатай орчин
- Python 3.11–3.14 (Python 3.14 туршигдсан, гэхдээ 3.11/3.12 илүү тогтвортой)
- Node.js 20+
- Ollama (https://ollama.com/) суулгасан, port 11434-д ажиллаж байх
- Disk space ~6 GB (Ollama qwen2.5:7b л 4.7 GB)
- RAM 8 GB minimum, 16 GB зөвлөмжтэй

### 2. Repo татах
```powershell
git clone <repo-url> Boloroo
cd Boloroo
```

### 3. Python virtual environment
```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Environment файл
```powershell
Copy-Item .env.example .env
# Шаардлагатай бол .env-г нээж тохируулна уу (default утга нь хэвийн)
```

### 5. Ollama суулгах ба загвар татах
Шинэ терминал нээгээд:
```powershell
ollama serve
```
Бас нэг терминалд (анх удаа л):
```powershell
ollama pull qwen2.5:7b
```

### 6. Custom classifier-ыг сургах (анх удаа л)
```powershell
python training/scripts/train.py
```
Хүлээгдэж буй гаралт: F1 macro ~0.95, `training/models/sensitive_classifier.pkl` болон `tfidf_vectorizer.pkl` файл үүснэ.

### 7. Knowledge документуудыг ingest хийх
```powershell
python scripts/ingest.py
```
`data/raw/` хавтсан доторх бүх PDF/TXT файлыг chunking ба embedding хийгээд `data/vectors/index.faiss` файл руу хадгална.

> **Тэмдэглэл:** Одоо репо дотор урьдчилан бэлдэгдсэн index байгаа (3408 vector) учир энэ алхам **заавал биш**.

### 8. Backend ажиллуулах
```powershell
$env:PYTHONIOENCODING="utf-8"
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Дотор амжилттай startup-ын лог:
```
Database initialized at: ...
Loaded index: 3408 vectors, 3408 chunks
Sensitive content classifier loaded.
Backend ready.
```

### 9. Frontend ажиллуулах (өөр терминал)
```powershell
cd frontend
npm install
npm run dev
```

Browser-д http://localhost:5173 нээх.

---

## Backend ажиллуулах команд

```powershell
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

## Frontend ажиллуулах команд

```powershell
cd frontend
npm run dev
```

## Документ ingest хийх команд

```powershell
# Бүх raw файлыг ingest хийх
python scripts/ingest.py

# Тодорхой файлыг ingest хийх
python scripts/ingest.py path/to/document.pdf
```

---

## Chat API жишээ

### REST хүсэлт
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Хүйсийн тэгш байдлын тухай хууль юу хамгаалдаг вэ?","category":"gender_equality"}'
```

### Хариу
```json
{
  "answer": "Жендэрийн эрх тэгш байдлын тухай хуулийн зорилго нь улс төр, эдийн засаг, нийгэм, соёлын аль ч салбарт хүйсээр ялгаварлахгүй байх... [1]",
  "sources": [
    {
      "ref_number": 1,
      "source_file": "faq_gender_equality.txt",
      "document_title": "Хүйсийн тэгш эрх (FAQ)",
      "page_number": 1,
      "snippet": "Асуулт: Жендэрийн эрх тэгш байдлыг хангах тухай хуулийн зорилго ...",
      "relevance_score": 0.949,
      "law_references": ["4 дүгээр зүйл"]
    }
  ],
  "safety": {
    "label": "safe",
    "confidence": 0.95,
    "is_safe": true
  },
  "chat_id": 42,
  "response_time_ms": 1234,
  "model_used": "faq_direct"
}
```

### `category` параметр
| Value | Сэдэв |
|-------|-------|
| `gender_equality` | Хүйсийн тэгш эрх |
| `discrimination` | Ялгаварлан гадуурхалт |
| `disability` | Хөгжлийн бэрхшээлтэй иргэн |

`category` нь optional. Хэрэглэгчийн сонгосон ангиллын дагуу retrieval-д тусгай context prefix нэмэгддэг — retrieval нарийвчлал сайжирна.

### Бусад endpoint-ууд

| Метод | Зам | Тайлбар |
|-------|-----|---------|
| POST | `/api/chat` | Гол чат endpoint |
| POST | `/api/feedback` | Thumbs up (1) / down (-1) санал |
| POST | `/api/ingest` | PDF/TXT баримт оруулах (multipart/form-data) |
| GET | `/api/documents` | Оруулсан баримтуудын жагсаалт |
| DELETE | `/api/documents/{id}` | Soft delete |
| GET | `/api/health` | Health check (index, classifier ачаалагдсан эсэх) |
| GET | `/api/stats` | Хэрэглээний статистик |

OpenAPI docs нь `http://localhost:8000/docs`-т автоматаар үүсэх.

---

## Ollama / Локал LLM Шаардлага

**Ollama сервер заавал ажиллаж байх ёстой**: chat endpoint нь `http://localhost:11434/api/chat`-руу POST хүсэлт явуулдаг. Хэрэв Ollama ажиллахгүй бол хариу:
> «Уучлаарай, Ollama сервер ажиллахгүй байна. Терминалд `ollama serve` гэж ажиллуулна уу.»

Ашиглах загвар: **qwen2.5:7b** (Q4_K_M quantization, 4.7 GB). Энэ загвар нь Монгол хэлийн дэмжлэг сайтай, CPU дээр (хэдийгээр удаан) ажиллах боломжтой. .env-д `LLM_MODEL=other_model` гэж тохируулж бусад загвар туршиж болно.

`OLLAMA_BASE_URL=http://localhost:11434` нь default. Алсын Ollama ашиглах эсвэл Docker-д ажиллах бол энэ URL-г өөрчилнө.

---

## Demo Сценари (Хамгаалалтад)

Дараах 5 жишээ асуулт нь системийн бүх routing branch-ийг харуулна:

1. **Identity** — «Чи хэн бэ?» → шууд танилцуулга, RAG/LLM-г огт ашиглахгүй.
2. **Capability** — «Чи юу хийж чадах вэ?» → шууд чадварын тайлбар.
3. **FAQ fast-path** — «Хүйсийн тэгш байдлын тухай хуулийн зорилго юу вэ?» → top-1 score 0.949, FAQ direct хариу (LLM-г тойрч).
4. **Generic RAG + LLM** — «Сургуулийн дарамтад өртсөн үед хаана хандах вэ?» → top-2 chunk + Ollama-аар хариулт үүсгэнэ.
5. **Safety blocked** — «Эмэгтэйчүүд удирдах албан тушаалд тохиромжгүй» → `hate_speech` гэж ангилагдан, тусгай safety response буцаагдана.

Бас 6-р жишээ: **Crisis flag** — «Би амьдрахыг хүсэхгүй байна» → `self_harm` ангилалд орж, тусламжийн утасны жагсаалт буцаах.

---

## Known Issues

| Зэрэг | Асуудал | Зорилго |
|-------|---------|---------|
| 🔴 | Тестүүд хоосон (`tests/` нь зөвхөн `__init__.py`) | 5–7 pytest нэмэх |
| 🔴 | SQLite `documents`/`chunks` ХООСОН (FAISS-3408 vector vs SQL-0 row зөрчилтэй) | `scripts/ingest.py`-г шинэчлэх |
| 🟠 | Sklearn хувилбарын зөрчил (1.5.2 → 1.8.0) | Pin эсвэл re-train |
| 🟠 | Classifier 120 sample-аар сургагдсан, dataset_expanded (226) ашиглаагүй | `python training/scripts/train.py` |
| 🟠 | Admin endpoint-д auth байхгүй | Basic Auth middleware нэмэх |
| 🟡 | Evaluation тоон тайлан байхгүй (`scripts/evaluate_*.py` ажиллуулж тайлан гаргах ёстой) | docs/evaluation/ хавтасруу гаргах |
| 🟡 | TOP_K=2 — олон сэдэвт асуултанд бага | TOP_K=3 болгох |
| 🟡 | Docker compose Ollama-руу хүрэхгүй | `host.docker.internal` тохируулах |
| 🟢 | React Router байхгүй | URL-based routing нэмэх |
| 🟢 | Rate limiting байхгүй | slowapi нэмэх |

Дэлгэрэнгүй: [`docs/DIPLOMA_AUDIT_MN.md`](docs/DIPLOMA_AUDIT_MN.md), [`docs/FIX_PLAN_MN.md`](docs/FIX_PLAN_MN.md)

---

## Хамгаалалтын Demo Урсгал

1. **Урьдчилан шалгах** (5 мин өмнө):
   ```powershell
   curl http://localhost:11434/api/tags
   curl http://localhost:8000/api/health
   ```
2. **Browser-д http://localhost:5173 нээх**.
3. **LandingPage** — 3 ангиллын карт харагдана. *«Хүйсийн тэгш эрх»* сонгоно.
4. **ChatPage** — жишээ асуулт сонгох эсвэл шууд бичих.
5. **5 demo асуулт** (дээрх Demo сценари хэсэгт жагсаасан).
6. **Source panel** — хариултын дор «Эх сурвалж харах» товч → law-reference badge харагдана.
7. **Feedback** — thumbs up/down дарж тэмдэглэгээ хийх → SQLite-д бичигдэнэ.
8. **Admin page** — нэвтрэх → системийн health, нийт chat тоо, дундаж response time харах.
9. (Боломжтой бол) **PDF файл upload** хийж шинэ chunk index-д орохыг харуулах.

---

## Documentation

| Файл | Тайлбар |
|------|---------|
| [`README.md`](README.md) | English version |
| [`README_MN.md`](README_MN.md) | Энэ файл (Mongolian) |
| [`docs/DIPLOMA_AUDIT_MN.md`](docs/DIPLOMA_AUDIT_MN.md) | Дипломын аудит, олдвор, эрсдэл |
| [`docs/RUN_VALIDATION_MN.md`](docs/RUN_VALIDATION_MN.md) | Локал орчны run validation тайлан |
| [`docs/FIX_PLAN_MN.md`](docs/FIX_PLAN_MN.md) | Засвар-р роадмап |
| [`docs/DIAGRAM_EXPLANATIONS_MN.md`](docs/DIAGRAM_EXPLANATIONS_MN.md) | Диаграмуудын нэгдсэн академик тайлбар |
| [`docs/diagrams/`](docs/diagrams/) | 7 Mermaid диаграм (Монгол) |
| [`docs/thesis_notes.md`](docs/thesis_notes.md) | Дипломын ажлын дотоод тэмдэглэл |

---

## Лиценз

Бакалаврын дипломын ажлын хүрээнд боловсруулагдсан. Боловсрол, судалгааны зориулалтаар чөлөөтэй ашиглаж болно.

---

## Холбоо барих

Дипломын ажлын зохиогч: *(нэрээ нэмж бичнэ үү)*
Удирдагч багш: *(нэрийг нэмж бичнэ үү)*
Сургууль: *(сургуулийн нэрийг нэмж бичнэ үү)*
