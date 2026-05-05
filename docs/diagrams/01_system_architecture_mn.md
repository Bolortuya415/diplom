# Зураг 1. Системийн Ерөнхий Архитектур

## Mermaid диаграм

```mermaid
flowchart TB
    User["👤 Хэрэглэгч<br/>(Хөтөч)"]

    subgraph Frontend ["Frontend (React + Vite)"]
        Landing["LandingPage<br/>3 ангилал"]
        Chat["ChatPage<br/>Чат харилцан үйлдэл"]
        Admin["AdminPage<br/>Баримт оруулалт + Статистик"]
    end

    subgraph Backend ["FastAPI Backend (Python 3.14)"]
        API["/api router<br/>(routes.py)"]
        ChatSvc["ChatService<br/>Аюулгүй байдал → RAG → LLM<br/>(chat_service.py)"]
        IngestSvc["IngestService<br/>Баримт оруулалт<br/>(ingest_service.py)"]
        Classifier["Sensitive Content<br/>Classifier<br/>(TF-IDF + LogReg)"]
    end

    subgraph RAG ["RAG бүрэлдэхүүн"]
        Loader["DocumentLoader<br/>PDF / TXT уншигч<br/>(PyMuPDF)"]
        Chunker["Chunker<br/>500 тэмдэгт + 50 overlap<br/>FAQ-aware"]
        Embedder["EmbeddingManager<br/>multilingual-MiniLM-L12-v2<br/>(384-dim)"]
        Generator["AnswerGenerator<br/>Ollama prompt формат<br/>+ FAQ fast-path"]
    end

    subgraph Storage ["Хадгалалт"]
        Faiss[("FAISS Index<br/>data/vectors/<br/>3408 vector")]
        Sqlite[("SQLite<br/>data/boloroo.db<br/>chat_logs · feedback · documents")]
        Models[("ML загварууд<br/>training/models/<br/>tfidf · classifier")]
        Raw[("Эх баримтууд<br/>data/raw/<br/>5 PDF + 7 TXT")]
    end

    Ollama["🤖 Ollama Local LLM<br/>qwen2.5:7b<br/>(localhost:11434)"]

    User -->|"HTTP"| Landing
    User -->|"HTTP"| Chat
    User -->|"HTTP"| Admin

    Landing -->|"category select"| Chat
    Chat -->|"POST /api/chat"| API
    Chat -->|"POST /api/feedback"| API
    Admin -->|"POST /api/ingest<br/>GET /api/health<br/>GET /api/stats<br/>GET /api/documents"| API

    API --> ChatSvc
    API --> IngestSvc

    ChatSvc --> Classifier
    ChatSvc --> Embedder
    ChatSvc --> Generator
    Classifier --> Models

    IngestSvc --> Loader
    Loader --> Raw
    Loader --> Chunker
    Chunker --> Embedder
    Embedder --> Faiss

    Generator -->|"chat completion"| Ollama
    ChatSvc --> Sqlite
    IngestSvc --> Sqlite

    Generator -->|"answer + sources"| ChatSvc
    ChatSvc -->|"ChatResponse JSON"| API
    API -->|"answer + safety + sources"| Chat
```

## Тайлбар

Boloroo (Тэгшбот) системийн архитектур нь хэрэглэгч-frontend-backend гэсэн классик 3-давхар бүтэцтэй. **Frontend** (React + Vite) хэрэглэгчийн үйлдлийг хүлээн авч HTTP хүсэлтээр **FastAPI backend**-руу дамжуулна. Backend дотор RAG pipeline ба safety classifier хоёр гол бүрэлдэхүүн зэрэгцэн ажиллана. RAG нь FAISS вектор индексд хайлт хийж, олдсон контекстийг **локалаар ажилладаг Ollama LLM (qwen2.5:7b)**-руу дамжуулан хариулт үүсгэдэг. Classifier нь хэрэглэгчийн оруулсан текстийг 5 ангилал (`safe`, `hate_speech`, `harassment`, `discrimination`, `self_harm`) дунд урьдчилан шалган, аюултай оролтыг шууд блоклож хариу буцаана.

Чухал шинж чанар нь **бүх зүйл локал орчинд ажилладаг** — гадаад API, OpenAI, cloud үйлчилгээ ашигладаггүй. Энэ нь хувийн өгөгдөл хамгаалал, Монгол хэрэглэгчийн интернэтийн хязгаарлалт, дипломын ажлын төсөвт нийцтэй.

## Дипломын тайланд ашиглах тайлбар

Дипломын ажлын *«Системийн архитектур»* бүлэгт уг диаграм нь системийн модульчлал, давхар-бүтэц, болон гадаад/дотоод дамжуулалтыг харуулна. Архитектур нь *«clean separation of concerns»* зарчмыг баримталсан — UI давхарга, API давхарга, business logic (services), retrieval logic (rag/), persistence (FAISS + SQLite + загварын pickle файл) нь бүгд тусгаар. Энэ нь модульчлал, тестлэгдэх чадвар, дараа сайжруулах боломжийг хадгалдаг.

Системийн гол **онцлог технологиуд:**
- **FastAPI** нь async дэмжлэг, автоматаар OpenAPI баримт үүсгэх, Pydantic-аар оролтын баталгаажуулалт хийдэг.
- **FAISS** нь Facebook-ийн нээлттэй эх вектор индекс — тусгай сервер шаарддаггүй, файл хэлбэрээр хадгалагддаг.
- **sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2** нь 50+ хэлийг дэмждэг бөгөөд Монгол кирилл текстэд тохиромжтой.
- **Ollama** нь локалаар LLM ажиллуулдаг хөнгөн server — хэрэглэгчийн нууц өгөгдөл гадагш гарахгүй.

## Хамгаалалтын үеэр тайлбарлах богино хувилбар

«Систем 3 давхараас бүрдэнэ — React frontend, FastAPI backend, локал Ollama LLM. Backend нь RAG (FAISS-аар вектор хайлт) болон custom-тэй TF-IDF classifier хосолно. Хэрэглэгч асуулт оруулахад эхлээд classifier шалгаж, дараа FAISS-аас хамгийн ойролцоо chunk-уудыг олж, тэдгээрийг Ollama-руу дамжуулан Монгол хэлээр хариулт үүсгэнэ. Бүх зүйл локал, гадаад API үгүй.»
