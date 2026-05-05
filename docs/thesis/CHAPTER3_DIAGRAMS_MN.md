# БҮЛЭГ 3. СИСТЕМИЙН ЗОХИОМЖ

> **Зорилго:** Энэхүү бүлэгт Boloroo (UI бранд: «Тэгшбот») ажлын байрны хүйсийн тэгш эрх, нийгмийн хүртээмжтэй байдлын RAG-д суурилсан чатбот системийн зохиомжийг дипломын академик стандартад нийцсэн UML/ERD/архитектурын диаграмаар тайлбарлав.

> **Анхаарал:** Дараах хэсэг бүрд оруулсан диаграмууд нь бодит репозиторийн source code-аас reverse-engineer хийгдэн гаргасан болно. Эх сурвалж файлууд тус бүрийн орчинд тэмдэглэгдсэн ба `docs/DIAGRAM_ANALYSIS_MN.md` баримт бичигт нарийвчлан шалгасан болно. Диаграмын source файлууд (PlantUML `.puml` ба Mermaid `.mmd`) нь `docs/diagrams/source/` хавтсанд, render хийгдсэн дүрсүүд (хэрэв render хийгдсэн бол) `docs/diagrams/rendered/` хавтсанд хадгалагдсан.

---

## 3.1 Системийн ерөнхий архитектур

Boloroo чатбот системийн архитектурын зохион байгуулалт нь *layered architecture* зарчимд тулгуурласан гурван үндсэн давхрагатай: хэрэглэгчийн харилцах *frontend*, бизнес-логик гүйцэтгэх *backend*, болон туслах *гадаад үйлчилгээ*-нүүд. Дотоод бүтэц нь түргэн ажиллагаатай, тестэгдэх боломжтой, цэвэр модуль-хуваагдсан зохион байгуулалтыг хадгална.

```mermaid
flowchart TB
    User(["👤 Хэрэглэгч"])
    Admin(["🛡️ Админ"])

    subgraph FE ["Frontend — React + Vite (port 5173)"]
        Landing["LandingPage<br/>3 ангилал"]
        ChatUI["ChatPage<br/>чат UI + sources"]
        AdminUI["AdminPage<br/>upload + stats"]
        ApiJs["services/api.js<br/>fetch wrapper"]
    end

    subgraph BE ["Backend — FastAPI (port 8000)"]
        Main["main.py<br/>Lifespan + CORS"]
        Routes["api/routes.py<br/>7 endpoint"]
        ChatSvc["ChatService<br/>6-step routing"]
        IngestSvc["IngestService"]
        Clf["Sensitive<br/>Classifier"]
    end

    subgraph RAG ["RAG бүрэлдэхүүн (rag/)"]
        Pipeline["RAGPipeline (facade)"]
        Loader["DocumentLoader"]
        Chunker["Chunker (FAQ-aware)"]
        Emb["EmbeddingManager"]
        Gen["AnswerGenerator"]
    end

    SQL[("SQLite<br/>boloroo.db")]
    FAISS[("FAISS<br/>3408 vector")]
    Raw[("data/raw/<br/>5 PDF + 7 TXT")]
    Models[("ML моделүүд")]
    Ollama["🤖 Ollama LLM<br/>:11434<br/>qwen2.5:7b"]

    User --> ChatUI
    Admin --> AdminUI
    ChatUI --> ApiJs --> Routes
    AdminUI --> ApiJs
    Routes --> ChatSvc
    Routes --> IngestSvc
    ChatSvc --> Clf --> Models
    ChatSvc --> Pipeline
    ChatSvc --> Gen --> Ollama
    ChatSvc --> SQL
    IngestSvc --> Pipeline
    IngestSvc --> SQL
    Pipeline --> Loader --> Raw
    Pipeline --> Chunker
    Pipeline --> Emb --> FAISS
```

> **Зураг 3.1.** Системийн ерөнхий архитектур.

Frontend-нь React 18.3 + Vite 5.4 хүрээнээс бүтсэн single-page application бөгөөд `LandingPage` (3 категори), `ChatPage` (чат UI), `AdminPage` (upload + статистик) гэсэн гурван үндсэн хуудастай. HTTP холбоог `services/api.js` доторх fetch wrapper-ээр гүйцэтгэдэг. Vite-ийн dev-серверийн proxy-р `/api/*` зам нь localhost:8000-д шилжинэ.

Backend нь FastAPI хүрээний lifespan, Pydantic validation, async dispatch-ыг бүрэн ашигласан бөгөөд `api/routes.py` дотор 7 endpoint, `services/{chat,ingest}_service.py` дотор бизнес логик, `core/config.py` дотор тохиргооны loader зэрэг хэсгүүд тусгаар модуль болон зохиогдсон. RAG модуль (`rag/`) нь backend-аас тусдаа байж DocumentLoader, Chunker, EmbeddingManager, AnswerGenerator гэсэн дөрвөн анги нэг facade RAGPipeline-аар нэгтгэгдсэн.

Локал ажиллах **Ollama LLM сервер** нь `qwen2.5:7b` (4.7 GB Q4_K_M) загварыг хост машин дээр ажиллуулан, backend-ээс HTTP-ээр хандана. Энэ нь:
- Хэрэглэгчийн нууц мэдээлэл internet-руу гарахаас сэргийлдэг.
- API ключ, татвар шаарддаггүй.
- Монгол хэлийн дэмжлэг сайтай qwen загварыг ашигладаг.

**Хамгаалалтын үеэр товчоор:** «Систем нь гурван давхар архитектуртай — React frontend, FastAPI backend, локал Ollama. Backend дотор RAG модуль ба safety classifier зэрэгцэн ажиллана. Бүх өгөгдөл локал файлд хадгалагдана, гадаад API ашигладаггүй.»

---

## 3.2 Өгөгдлийн ерөнхий схем

Системийн өгөгдлийн загвар нь хосолсон persistence бүхий: structured метадатаг SQLite дотор, vector өгөгдлийг FAISS файлд хадгална. SQLite дотор дөрвөн хүснэгт байх ба `backend/app/db/database.py:init_db()`-ийн DDL-ээр тодорхойлогдсон.

```mermaid
erDiagram
    documents ||--o{ chunks : "1 — N"
    chat_logs ||--o{ feedback : "1 — N"

    documents {
        INTEGER id PK
        TEXT title
        TEXT filename "UNIQUE"
        TEXT source_type
        TIMESTAMP upload_date
        INTEGER page_count
        INTEGER chunk_count
        TEXT status "active | deleted"
    }
    chunks {
        INTEGER id PK
        INTEGER document_id FK
        TEXT chunk_id "UNIQUE"
        INTEGER chunk_index
        TEXT text
        INTEGER page_number
        INTEGER char_count
        TEXT metadata_json
    }
    chat_logs {
        INTEGER id PK
        TEXT query
        TEXT answer
        TEXT sources_json
        TEXT safety_label
        REAL safety_confidence
        TEXT model_used
        INTEGER tokens_used
        INTEGER response_time_ms
        TIMESTAMP timestamp
    }
    feedback {
        INTEGER id PK
        INTEGER chat_id FK
        INTEGER rating "CHECK IN (-1,1)"
        TEXT comment
        TIMESTAMP timestamp
    }
```

> **Зураг 3.2.** Өгөгдлийн ерөнхий схем.

Гол хамаарлууд:
- `documents (1) — (N) chunks` — нэг баримтаас N chunk үүсэх. Soft-delete тул `status='deleted'` гэж тэмдэглэхэд физикээр устгахгүй.
- `chat_logs (1) — (N) feedback` — нэг чатын мэссэжэд олон санал ирэх боломжтой.
- `chat_logs.sources_json` нь *денормалчлагдсан JSON массив* — chunks-руу шууд FK байхгүй, citation мэдээллийг chunk_id текстээр хадгалдаг. Энэ нь *trade-off design*: write хялбар, гэхдээ chunks хүснэгт өөрчлөгдвөл түүх хуучирна.

FAISS бүрэлдэхүүн нь SQLite-аас гадуур, file-based persistence: `data/vectors/index.faiss` (5 MB) ба `data/vectors/chunks.pkl` (3 MB). Backend startup үед `EmbeddingManager.load()`-аар RAM руу ачаалагдана.

**Privacy шинж:** `chat_logs` хүснэгтэд `user_id`, IP, session ID гэх багана **байхгүй**. Чат өгөгдөл анонимтай хадгалагддаг учир GDPR-стиль privacy-ийн зарчимтай нийцэнэ.

**Хамгаалалтын үеэр товчоор:** «Systemийн өгөгдлийн загвар хоёр төрөл: structured SQLite (4 хүснэгт — documents, chunks, chat_logs, feedback) ба file-based FAISS index. documents-chunks болон chat_logs-feedback хооронд 1-N FK харилцаа бий. chat_logs анонимтай — user_id хадгалдаггүй. Vector өгөгдөл FAISS-д бичигдэхтэй параллель chunks SQL хүснэгтэд metadata бичигдэнэ.»

---

## 3.3 Класс диаграм

Системийн объект-чиглэсэн загвар нь backend service давхарга, RAG бүрэлдэхүүн, classifier, REST schema гэсэн дөрвөн групп ангид хуваагдана. Анги бүр Single Responsibility Principle-д нийцсэн, harboring хариуцлагатай.

```mermaid
classDiagram
    class ChatService {
        +RAGPipeline rag
        +AnswerGenerator generator
        +SensitiveContentClassifier classifier
        +process_query(query, category) dict
    }
    class IngestService {
        +RAGPipeline rag
        +ingest_file(path, title) dict
    }
    class RAGPipeline {
        +RAGConfig config
        +EmbeddingManager embedding_manager
        +initialize() bool
        +ingest_document(path) dict
        +search(query) list
    }
    class EmbeddingManager {
        +SentenceTransformer model
        +IndexFlatIP index
        +list~Chunk~ chunks
        +build_index(chunks)
        +search(query, top_k) list
    }
    class AnswerGenerator {
        +RAGConfig config
        +generate(query, chunks) dict
        +format_context(chunks) str
        +format_sources(chunks) list
    }
    class SensitiveContentClassifier {
        +model
        +vectorizer
        +predict(text) dict
    }
    class RAGConfig {
        <<dataclass>>
        +chunk_size, top_k
        +llm_model, llm_timeout
        +system_prompt
    }
    class Chunk {
        <<dataclass>>
        +chunk_id, text
        +source_file, page_number
        +metadata
    }

    ChatService o-- RAGPipeline
    ChatService o-- AnswerGenerator
    ChatService o-- SensitiveContentClassifier
    IngestService o-- RAGPipeline
    RAGPipeline o-- EmbeddingManager
    RAGPipeline o-- RAGConfig
    EmbeddingManager *-- Chunk
    AnswerGenerator o-- RAGConfig
```

> **Зураг 3.3.** Класс диаграм (хариуцлага бүхий гол анги).

Гол анги нь `ChatService` бөгөөд *оркестраторын* үүрэгтэй: RAG-аас retrieval, AnswerGenerator-аас LLM, Classifier-аас safety check-ыг хуваан гүйцэтгэнэ. `RAGPipeline` нь facade pattern-аар RAG-ийн нарийн ширийнийг encapsulate хийх ба backend service-үүд retrieval-ийн дотоод бүтцийг мэдэх шаардлагагүй болгодог. `RAGConfig` нь dataclass хэлбэрээр гурван анги (RAGPipeline, EmbeddingManager, AnswerGenerator) хооронд хуваалцагддаг тул тохиргоог нэг газраас өөрчилж болно.

REST давхарга-нь Pydantic schema (ChatRequest, ChatResponse, FeedbackRequest, IngestResponse, HealthResponse, SourceCitation, SafetyInfo)-аар оролт-гаралтыг баталгаажуулж, *anti-corruption layer* зарчмаар backend-ийн дотоод class-уудаас тусдаа байна.

**Хамгаалалтын үеэр товчоор:** «Гол анги нь `ChatService` (оркестратор), `RAGPipeline` (RAG facade), `EmbeddingManager` (FAISS + sentence-transformer), `AnswerGenerator` (Ollama prompt), `SensitiveContentClassifier` (TF-IDF + LR). Бүх RAG анги нэг RAGConfig dataclass-ийг хуваан хэрэглэдэг. Pydantic schema-аар REST API-ийн оролт-гаралт бат validate-гддэг.»

---

## 3.4 Хэрэглэгчийн асуултад хариулах дарааллын диаграм

Чат хүсэлтийн боловсруулалтын дотоод дарааллыг харуулна. `ChatService.process_query()` нь *fast-fail* зарчмыг баримталсан 6-step routing pipeline-аар query-г шилжүүлдэг — хямд (regex match) шалгуурууд эхэнд, хамгийн үнэтэй (LLM call) хамгийн төгсгөлд гүйцэтгэгдэнэ.

```mermaid
sequenceDiagram
    actor User as 👤 Хэрэглэгч
    participant FE as ChatPage
    participant Route as POST /api/chat
    participant Svc as ChatService
    participant Clf as Classifier
    participant RAG as RAGPipeline
    participant Gen as AnswerGenerator
    participant Ollama
    participant DB as SQLite

    User->>FE: асуулт + Enter
    FE->>Route: POST /api/chat
    Route->>Svc: process_query

    Note over Svc: Step 1-2: shortcut шалгалт
    Svc->>Svc: identity / capability / greeting

    Note over Svc: Step 3-5: safety
    Svc->>Clf: predict(query)
    Clf-->>Svc: {label, confidence}
    Svc->>Svc: crisis downgrade?
    alt unsafe
        Svc->>DB: log + return safety response
    end

    Note over Svc: Step 6-7: RAG
    Svc->>RAG: search(prefix + query)
    RAG-->>Svc: top-k chunks

    Note over Svc: Step 8: generation
    Svc->>Gen: generate(query, chunks)
    alt FAQ fast-path
        Gen-->>Svc: faq_answer
    else
        Gen->>Ollama: POST /api/chat
        Ollama-->>Gen: text
    end
    Svc->>DB: INSERT chat_logs
    Svc-->>Route: ChatResponse
    Route-->>FE: JSON
    FE-->>User: бубл + sources
```

> **Зураг 3.4.** Хэрэглэгчийн асуултад хариулах дарааллын диаграм.

6-step routing pipeline-ийн агуулга: (1a) identity shortcut, (1b) capability shortcut, (2) greeting shortcut, (3) classifier predict, (4) crisis-indicator-аар self_harm/harassment-ийн false positive downgrade, (5) vague-query check, (6) RAG retrieval + LLM. FAQ fast-path-аар *top chunk нь FAQ бөгөөд score ≥ 0.55 үед* Ollama-руу огт хүсэлт явуулахгүйгээр FAQ-ийн хариултыг шууд буцаана.

**Хамгаалалтын үеэр товчоор:** «Хэрэглэгчийн асуулт ChatService-руу хүрэхэд 6 шалгалттай pipeline-аар явдаг: identity → capability → greeting → classifier → crisis downgrade → vague check → RAG + LLM. FAQ chunk-ийн score 0.55-аас өндөр бол Ollama-г огт алгасч шууд хариу буцдаг. Бүх шалгалт chat_logs-д бичигддэг.»

---

## 3.5 Баримт бичиг оруулах дарааллын диаграм

Админ AdminPage-ээр шинэ баримт оруулах процесс нь PDF/TXT текст гаргалт, FAQ-aware chunking, embedding generation, FAISS index-д бичих, SQLite-д metadata хадгалах гэсэн дараалсан 7 алхамаас тогтоно.

```mermaid
sequenceDiagram
    actor Admin as 🛡️ Админ
    participant FE as AdminPage
    participant Route as POST /api/ingest
    participant ISvc as IngestService
    participant RAG as RAGPipeline
    participant Loader
    participant Chunker
    participant Emb as EmbeddingManager
    participant FAISS
    participant SQL as SQLite

    Admin->>FE: файл + title
    FE->>Route: multipart/form-data
    Route->>Route: suffix in {.pdf,.txt}?
    Route->>Route: shutil.copyfileobj
    Route->>ISvc: ingest_file
    ISvc->>RAG: ingest_document

    RAG->>Loader: load_document
    alt PDF
        Loader->>Loader: PyMuPDF + clean
    else TXT
        Loader->>Loader: utf-8 + clean
    end
    Loader-->>RAG: list[DocumentPage]

    RAG->>Chunker: chunk_documents(500, 50)
    loop page бүрд
        alt FAQ
            Chunker->>Chunker: 1 chunk per Q+A
        else generic
            Chunker->>Chunker: 500-char + 50-overlap
        end
    end
    Chunker-->>RAG: list[Chunk]

    RAG->>Emb: add_to_index
    Emb->>Emb: encode (FAQ → асуулт only)
    Emb->>FAISS: index.add + write
    RAG-->>ISvc: result

    ISvc->>SQL: INSERT documents
    loop chunk бүрд
        ISvc->>SQL: INSERT chunks
    end
    ISvc-->>FE: IngestResponse JSON
    FE-->>Admin: "N хуудас, M хэсэг"
```

> **Зураг 3.5.** Баримт бичиг оруулах дарааллын диаграм.

**FAQ-aware chunking** бол **системийн өвөрмөц шинж**: `### FAQ N` болон `Асуулт:` / `Хариулт:` хэлбэрийн файлуудыг entry бүрээр нэг chunk болгож хадгалах ба embedding-ийг зөвхөн **асуултын** текстээс үүсгэдэг. Энэ нь хэрэглэгчийн query-FAQ entry-ийн хооронд cosine similarity-ийг ихэсгэдэг гол ухаан.

**Хамгаалалтын үеэр товчоор:** «Админ файл upload хийхэд backend нь файлыг disk-д хадгалж RAGPipeline-руу дамжуулна. PyMuPDF-аар текст гаргаж FAQ хэлбэрийг автоматаар таних — FAQ entry бүрд нэг chunk, эс бөгөөс char-level chunking. Multilingual MiniLM embedding-аар FAISS-д нэмж файлд бичээд SQLite documents болон chunks хүснэгтэд metadata бичигдэнэ.»

---

## 3.6 Үйл ажиллагааны диаграм (RAG flow)

Үйл ажиллагааны диаграм нь нэг асуултыг боловсруулах боломжит бүх замналыг (decision branch-ууд, error branch-уудыг оролцуулсан) нэг зурагт багтаасан control-flow дүрслэл.

```mermaid
flowchart TD
    Start([Хэрэглэгчийн асуулт]) --> Sh{Shortcut?}
    Sh -->|тийм| ShR[Shortcut response]
    Sh -->|үгүй| Cf[Classifier predict]
    Cf --> Crit{Crisis indicator?}
    Crit -->|тийм + unsafe| Block[SAFETY_RESPONSES + log]
    Crit -->|үгүй + label!=safe| Down[downgrade → safe]
    Crit -->|safe| Vg{Vague?}
    Down --> Vg
    Vg -->|тийм| VR[Clarification]
    Vg -->|үгүй| QE[Query embedding]
    QE --> S[FAISS search + filter ≥0.3]
    S --> Rk[FAQ boost +0.12 + sort + top_k]
    Rk --> Em{Empty?}
    Em -->|тийм| UI[Unclear intent]
    Em -->|үгүй| FF{FAQ score ≥ 0.55?}
    FF -->|тийм| Direct[FAQ direct answer]
    FF -->|үгүй| OH{Ollama up?}
    OH -->|үгүй| OErr[Ollama error]
    OH -->|тийм| LLM[POST /api/chat]
    LLM --> RR{Result?}
    RR -->|timeout| FB[source fallback]
    RR -->|exception| GE[generic error]
    RR -->|success| Cl[clean leaked headers]
    Cl --> Lk{Raw snippet leak?}
    Lk -->|тийм| Fix[unclear intent]
    Lk -->|үгүй| Log
    Fix --> Log
    Direct --> Log
    FB --> Log
    Log[INSERT chat_logs] --> Render[Frontend render]
    ShR --> Render
    Block --> Render
    VR --> Render
    UI --> Render
    OErr --> Render
    GE --> Render
    Render --> EndA([end])
```

> **Зураг 3.6.** RAG боловсруулах үйл ажиллагааны диаграм.

Энэ диаграм нь *defense-in-depth* зарчмыг харуулдаг — олон давхар хамгаалалт: shortcut → classifier → crisis-aware downgrade → vague check → retrieval threshold → post-generation leak detection. Бас *graceful degradation* — Ollama unavailable, timeout, exception, retrieval хоосон үед хэрэглэгчид цэвэр Mongolian мэдээлэл өгнө.

**Хамгаалалтын үеэр товчоор:** «Чат query-ийн боломжтой бүх замналыг харуулсан үйл ажиллагааны диаграм. Олон давхар хамгаалалт: shortcut → classifier → crisis downgrade → vague check → retrieval-ийн threshold → post-generation leak detection. Алхам бүрд error branch (Ollama down, timeout, exception, raw snippet leak) бий ба бүх branch chat_logs-д бичигдэн frontend-руу JSON буцаана.»

---

## 3.7 Өгөгдлийн урсгалын диаграм

Өгөгдлийн төлвийн дарааллыг харуулна — нэг ширхэг өгөгдөл хэрхэн дамжин хувирч буйг хугацаа-биш форматын талаасаа.

```mermaid
flowchart TB
    User(["👤 Хэрэглэгч"])
    Admin(["🛡️ Админ"])

    subgraph BE ["Backend боловсруулалт"]
        B1["Pydantic validate"]
        B2["ChatService routing"]
        B3["Classifier (str → label dict)"]
        B4["Query embedding<br/>str → (1, 384) float32"]
        B5["FAISS search → list[dict]"]
        B6["format_context (250 char)"]
        B7["Ollama → raw text"]
        B8["clean → final str"]
        B9["format_sources → list[SourceCitation]"]
        B10["ChatResponse JSON"]
        B11["INSERT chat_logs"]
    end

    subgraph In ["Indexing"]
        I1["load_document → DocumentPage"]
        I2["chunk_documents → Chunk"]
        I3["embed → (N, 384)"]
        I4["FAISS write + INSERT"]
    end

    Raw[(data/raw/)]
    FAISS[(FAISS + chunks.pkl)]
    DB[(SQLite)]
    Models[(ML моделүүд)]
    Ollama["🤖 Ollama"]

    User --> B1 --> B2 --> B3
    B3 --> Models
    B2 --> B4 --> B5 --> FAISS
    FAISS --> B5 --> B6 --> B7 --> Ollama
    Ollama --> B7 --> B8 --> B10
    B5 --> B9 --> B10 --> B11 --> DB
    B10 --> User

    Admin --> B1 --> I1
    Raw --> I1 --> I2 --> I3 --> I4 --> FAISS
    I4 --> DB
```

> **Зураг 3.7.** Өгөгдлийн урсгалын диаграм.

Гол төлвийн хувиралууд: Cyrillic str → Pydantic ChatRequest → list[dict] retrieved chunks → numbered context string → Ollama JSON body → cleaned answer → ChatResponse Pydantic → JSON HTTP body → React state.

**Хамгаалалтын үеэр товчоор:** «Хэрэглэгчийн Cyrillic асуулт нь Pydantic-аар JSON validate-гдан, classifier нь TF-IDF features → label dict, RAG зам нь string → 384-dim float32 vector → FAISS search → list[dict] → numbered context → Ollama HTTP → raw text → cleaned answer → ChatResponse JSON. Эцэст нь chat_logs-д row нэмэгдэн frontend-руу буцна.»

---

## 3.8 Системийн байршуулалтын диаграм

Boloroo нь хэрэглэгчийн нэг ноут буукт бүхэлдээ ажилладаг local-only архитектуртай — гадаад API, cloud үйлчилгээгүй.

```mermaid
flowchart TB
    subgraph UD ["💻 Хэрэглэгчийн төхөөрөмж"]
        Browser["🌐 Browser"]
    end

    subgraph Host ["🖥️ Локал ноут / сервер"]
        subgraph FEN ["Frontend"]
            Vite["Vite dev :5173"]
        end
        subgraph BEN ["Backend (Python venv)"]
            Uv["Uvicorn :8000"]
            RAGm["RAGPipeline (memory)"]
            Cls["Classifier (memory)"]
        end
        subgraph OllamaN ["Ollama"]
            Ollama["Ollama daemon :11434<br/>qwen2.5:7b"]
        end
        FAISSdb[("FAISS файлууд")]
        SQLdb[("SQLite WAL")]
        Models[("ML pickle")]
        Raw[("data/raw/")]
        Env["⚙️ .env"]
    end

    Browser -->|":5173"| Vite
    Vite -->|"proxy /api"| Uv
    Uv --> RAGm --> FAISSdb
    Uv --> Cls --> Models
    Uv --> Ollama
    Uv --> SQLdb
    Uv --> Raw
    Uv -.-> Env
```

> **Зураг 3.8.** Системийн байршуулалтын диаграм.

Гурван параллел процесс хост машин дээр ажиллана: Vite dev сервер (5173), Uvicorn (8000), Ollama daemon (11434). RAM шаардлага ~5–6 GB (Ollama 4.7 GB + sentence-transformer 470 MB + бусад). File-based persistence: FAISS, chunks pickle, SQLite, ML pickle, эх баримт.

**Docker compose сонголт** (`docker-compose.yml`) бий боловч Ollama service container-аас гадуур ажиллах ёстой бөгөөд `OLLAMA_BASE_URL=http://host.docker.internal:11434` болон `extra_hosts: ["host.docker.internal:host-gateway"]` тохиргоо нэмэх шаардлагатай.

**Хамгаалалтын үеэр товчоор:** «Систем хэрэглэгчийн нэг ноут буукт бүрэн ажиллана — гадаад API байхгүй. 3 локал процесс: Vite frontend (5173), Uvicorn backend (8000), Ollama LLM (11434). Бүх state файлд хадгалагддаг (FAISS, SQLite, pickle). RAM шаардлага ~5–6 GB, GPU байхгүй ч CPU-friendly параметрээр 16 GB ноутбукт хангалттай ажиллана. Docker compose сонголт байгаа боловч Ollama-руу хост-аас хүрэх тохиргоог нэмэх шаардлагатай.»

---

## 3.9 Use case диаграм

Use case диаграм нь системийн functional requirement-уудыг гадаад actor-ийн талаас харуулна. Гурван actor: энгийн хэрэглэгч, админ, систем (автомат).

```mermaid
flowchart LR
    User(["👤 Энгийн<br/>хэрэглэгч"])
    Admin(["🛡️ Админ"])
    System(["⚙️ Систем"])

    subgraph Boundary ["Boloroo чатбот"]
        UC1((["UC1: Ангилал"]))
        UC2((["UC2: Асуулт"]))
        UC3((["UC3: Хариулт"]))
        UC4((["UC4: Эх сурвалж"]))
        UC5((["UC5: Санал"]))
        UC7((["UC7: Баримт<br/>upload"]))
        UC8((["UC8: Жагсаалт"]))
        UC10((["UC10: Health"]))
        UC11((["UC11: Stats"]))
        UC12((["UC12: Classifier"]))
        UC13((["UC13: Shortcut"]))
        UC14((["UC14: Vector хайлт"]))
        UC15((["UC15: FAQ fast-path"]))
        UC16((["UC16: LLM"]))
        UC17((["UC17: Лог"]))
        UC18((["UC18: Боловсруулах"]))
        UC19((["UC19: FAISS update"]))
    end

    User --> UC1
    User --> UC2
    User --> UC3
    User --> UC4
    User --> UC5
    Admin --> UC7
    Admin --> UC8
    Admin --> UC10
    Admin --> UC11
    System --> UC12
    System --> UC13
    System --> UC14
    System --> UC15
    System --> UC16
    System --> UC17
    System --> UC18
    System --> UC19

    UC2 -.->|include| UC13
    UC2 -.->|include| UC12
    UC2 -.->|include| UC14
    UC2 -.->|include| UC15
    UC2 -.->|include| UC16
    UC3 -.->|include| UC17
    UC7 -.->|include| UC18
    UC7 -.->|include| UC19
```

> **Зураг 3.9.** Use case диаграм.

Use case-ууд тус бүр FE компонент эсвэл backend endpoint-той тодорхой mapping-той. UC2 (Асуулт асуух) нь UC12, UC13, UC14, UC15, UC16 гэсэн 5 туслах use case-ийг include хийсэн compound use case. UC7 (Баримт upload) нь UC18 (боловсруулах) + UC19 (FAISS шинэчлэх)-ийг include хийнэ.

Одоогоор role-based access control хэрэгжээгүй — Frontend navigation-аар л Энгийн ↔ Админ ялгагдана. Энэ нь FIX_PLAN_MN.md-д Засвар №7 болж тэмдэглэгдсэн.

**Хамгаалалтын үеэр товчоор:** «Системд гурван actor: энгийн хэрэглэгч (5 use case — асуулт, хариу, эх сурвалж, санал, ангилал), админ (баримт upload, жагсаалт, статистик, health), систем (8 дотоод автомат use case — classifier, shortcut, vector хайлт, FAQ fast-path, LLM, лог, ingestion, FAISS шинэчлэлт). UC2 (асуулт асуух) нь дотоод 5 use case-ыг include хийсэн compound use case.»

---

## 3.10 Дүгнэлт

Энэхүү бүлэгт Boloroo системийн дотоод бүтцийг 9 төрлийн академик стандарт диаграмаар бүрэн харууллаа: системийн архитектур (Зураг 3.1), өгөгдлийн схем (Зураг 3.2), класс диаграм (Зураг 3.3), чат хүсэлтийн дараалал (Зураг 3.4), баримт оруулах дараалал (Зураг 3.5), үйл ажиллагааны диаграм (Зураг 3.6), өгөгдлийн урсгал (Зураг 3.7), байршуулалт (Зураг 3.8), use case (Зураг 3.9). Диаграм бүр нь *бодит репозиторийн source code-аас* нарийвчлан reverse-engineer хийгдсэн ба тус бүрийн орчинд эх сурвалж файл/мөрийн ишлэл оруулсан.

Диаграмын **гол санаанууд:**
- **Локал-ажиллагаатай RAG систем** — гадаад API ашиглахгүй, хувийн өгөгдлийн хамгаалал бүрэн.
- **Service-ориентэд архитектур** — модуль-хуваагдсан, тестлэгдэх боломжтой.
- **Defense-in-depth safety** — олон давхар хамгаалалт: shortcut, classifier, crisis downgrade, vague check, post-generation sanity.
- **FAQ fast-path optimization** — стандарт RAG-аас давсан системийн өвөрмөц инноваци.
- **Anonymous chat logging** — хэрэглэгчийн ID байхгүй, GDPR-friendly.

**Хамгаалалтын өмнө шаардлагатай ажил:** Засвар №1–6 (`docs/FIX_PLAN_MN.md`-д жагсаасан) ~1.5–6 цаг.

---

*Энэхүү бүлгийг senior software architect стандартаар бэлтгэв. Бүх диаграм нь PlantUML болон Mermaid форматаар `docs/diagrams/source/` хавтсанд хадгалагдсан.*
