# Boloroo — Architecture & Workflow Diagrams

Mermaid diagrams describing the current system (no admin, ChromaDB + Gemini stack).
Render on GitHub, VS Code (with the Mermaid preview extension), or any Mermaid live editor (https://mermaid.live).

---

## Architecture diagram

```mermaid
flowchart TB
    subgraph Client["Client layer"]
        Browser["Хэрэглэгчийн браузер"]
        UI["React + Vite<br/>Chat UI"]
    end

    subgraph Backend["Backend (FastAPI, port 8000)"]
        API["REST API<br/>/chat &nbsp; /feedback &nbsp; /health"]
        Chat["ChatService"]
        Router["Route classifier<br/>(regex shortcuts)"]
        RAG["RAG Pipeline"]
        Embed["bge-m3 embedding<br/>(1024-dim, multilingual)"]
        Rerank["bge-reranker-v2-m3<br/>(cross-encoder)"]
    end

    subgraph Stores["Storage"]
        Chroma[("ChromaDB<br/>1,897 chunks<br/>persistent")]
        SQL[("SQLite<br/>chat_logs, feedback")]
    end

    Gemini["Google Gemini 2.5 Flash<br/>(REST API, external)"]

    subgraph Offline["Offline ingestion (scripts/ingest.py)"]
        direction LR
        Docs["PDF / TXT<br/>corpus"]
        Ingest["ingest.py CLI"]
        Docs --> Ingest
    end

    Browser --> UI
    UI -- "HTTP / JSON" --> API
    API --> Chat
    Chat --> Router
    Chat --> RAG
    RAG --> Embed
    Embed --> Chroma
    Embed --> Rerank
    Rerank -- "top-4 contexts" --> Gemini
    Gemini -- "answer" --> Chat
    Chat --> SQL

    Ingest -. "embed + upsert" .-> Chroma
    Ingest -. "metadata" .-> SQL

    classDef client fill:#dbe9ff,stroke:#3a6db5,color:#000
    classDef backend fill:#e6f5d0,stroke:#5b8a3c,color:#000
    classDef store fill:#fff3b0,stroke:#a07c00,color:#000
    classDef external fill:#fde0dc,stroke:#a32220,color:#000
    classDef offline fill:#e8e3d8,stroke:#6b6353,color:#000

    class Browser,UI client
    class API,Chat,Router,RAG,Embed,Rerank backend
    class Chroma,SQL store
    class Gemini external
    class Docs,Ingest offline
```

### Components at a glance

| Layer | Component | Purpose |
|---|---|---|
| Client | React + Vite | Chat UI, source panel, feedback buttons |
| Backend | FastAPI | 3 endpoints: `/chat`, `/feedback`, `/health` |
| Backend | ChatService | Routes incoming queries; orchestrates RAG |
| Backend | Route classifier | Regex shortcuts (identity, capability, greeting, crisis, vague) — no LLM |
| Backend | RAG pipeline | Embed → search → rerank → generate |
| Embedding | bge-m3 | 1024-dim multilingual dense vectors |
| Reranker | bge-reranker-v2-m3 | Cross-encoder, top-4 selection |
| Store | ChromaDB | Persistent vector store (1,897 chunks) |
| Store | SQLite | chat_logs, feedback |
| External | Gemini 2.5 Flash | Answer generation via REST API |
| Offline | `scripts/ingest.py` | One-time corpus build (CLI) |

---

## Workflow diagram (chat query lifecycle)

```mermaid
flowchart TD
    Q(["Хэрэглэгчийн асуулт"]) --> D1{"Identity?<br/>чи хэн бэ"}
    D1 -- "Тийм" --> R1["Identity reply"]
    D1 -- "Үгүй" --> D2{"Capability?<br/>чи юу хийдэг"}
    D2 -- "Тийм" --> R2["Capability reply"]
    D2 -- "Үгүй" --> D3{"Greeting?<br/>сайн уу"}
    D3 -- "Тийм" --> R3["Greeting reply"]
    D3 -- "Үгүй" --> D4{"Crisis indicator?<br/>амиа / гэмтээх"}
    D4 -- "Тийм" --> R4["Hotline reply"]
    D4 -- "Үгүй" --> D5{"Vague query?<br/>туслаач / яах вэ"}
    D5 -- "Тийм" --> R5["Clarification request"]
    D5 -- "Үгүй" --> RAG["RAG path"]

    RAG --> S1["1. bge-m3 embedding<br/>(query → 1024-dim vector)"]
    S1 --> S2["2. ChromaDB similarity search<br/>(cosine, top-10)"]
    S2 --> S3["3. bge-reranker-v2-m3<br/>(cross-encoder → top-4)"]
    S3 --> S4["4. Gemini 2.5 Flash<br/>(prompt + 4 contexts)"]
    S4 --> S5["5. Answer + ишлэл (sources)"]

    R1 --> LOG["Log to chat_logs<br/>(SQLite)"]
    R2 --> LOG
    R3 --> LOG
    R4 --> LOG
    R5 --> LOG
    S5 --> LOG
    LOG --> END(["Хариулт + sources<br/>back to user"])

    classDef start fill:#dbe9ff,stroke:#3a6db5,color:#000
    classDef decision fill:#fff3b0,stroke:#a07c00,color:#000
    classDef shortcut fill:#ffd9b3,stroke:#a05c20,color:#000
    classDef rag fill:#d4eaa7,stroke:#5b8a3c,color:#000
    classDef crisis fill:#fde0dc,stroke:#a32220,color:#000
    classDef terminal fill:#e8d8ff,stroke:#603a8a,color:#000

    class Q,END start
    class D1,D2,D3,D5 decision
    class D4 crisis
    class R1,R2,R3,R5 shortcut
    class R4 crisis
    class RAG,S1,S2,S3,S4,S5 rag
    class LOG terminal
```

### Routing logic at a glance

| Order | Route | Trigger | LLM call? | Typical latency |
|---|---|---|---|---|
| 1 | identity_shortcut | "чи хэн бэ", "өөрийгөө танилцуул" | No | ~4 ms |
| 2 | capability_shortcut | "чи юу хийж чадах вэ" | No | ~5 ms |
| 3 | greeting (shortcut) | "сайн уу", "hello" | No | ~3 ms |
| 4 | **crisis_hotline** | "амиа", "өөрийгөө хорлох", "тэсэхгүй байна" | **No (regex)** | ~5 ms |
| 5 | vague_shortcut | "туслаач", "яах вэ" (short queries) | No | ~5 ms |
| 6 | **RAG path** | Everything else | **Yes (Gemini)** | ~2.6 s p50 |

The crisis path is deterministic and runs *before* the RAG path so safety-critical phrasing never depends on the LLM being available.

---

## Offline corpus ingestion (sub-flow)

```mermaid
flowchart LR
    A["PDF / TXT documents<br/>in data/raw/"] --> B["scripts/ingest.py"]
    B --> C["Document loader<br/>(PyMuPDF for PDF)"]
    C --> D["Chunker<br/>(500 chars + 50 overlap)"]
    D --> E["bge-m3 embedding<br/>(1024-dim vectors)"]
    E --> F[("ChromaDB upsert<br/>collection: boloroo_corpus")]
    D --> G[("SQLite<br/>documents + chunks tables")]

    classDef step fill:#e6f5d0,stroke:#5b8a3c,color:#000
    classDef io fill:#fff3b0,stroke:#a07c00,color:#000
    classDef store fill:#dbe9ff,stroke:#3a6db5,color:#000

    class A io
    class B,C,D,E step
    class F,G store
```

Run once after adding/updating documents:

```bash
.venv/Scripts/python.exe scripts/ingest.py
```

The chatbot itself is read-only against the corpus at runtime — no document upload API exists.
