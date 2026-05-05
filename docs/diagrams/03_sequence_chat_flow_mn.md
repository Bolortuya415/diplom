# Зураг 3. Чат Хүсэлтийн Дарааллын Диаграм (Sequence)

## Mermaid диаграм

```mermaid
sequenceDiagram
    actor User as 👤 Хэрэглэгч
    participant FE as 🌐 Frontend<br/>(ChatPage)
    participant API as 🔌 FastAPI<br/>/api/chat
    participant CS as 🧠 ChatService
    participant CL as 🛡️ Classifier
    participant RAG as 🔍 RAG Pipeline
    participant FAISS as 📦 FAISS Index
    participant GEN as ✏️ AnswerGenerator
    participant LLM as 🤖 Ollama<br/>(qwen2.5:7b)
    participant DB as 💾 SQLite

    User->>FE: Асуулт бичих + Илгээх
    FE->>API: POST /api/chat<br/>{message, category}
    API->>CS: process_query(query, category)

    Note over CS: Step 1a: Identity check
    CS->>CS: _is_identity_question(query)?
    alt Identity match
        CS-->>API: Identity response
        API-->>FE: ChatResponse
        FE-->>User: «Би Болороо ...»
    end

    Note over CS: Step 1b: Capability check
    CS->>CS: _is_capability_question(query)?
    alt Capability match
        CS-->>API: Capability response
        API-->>FE: ChatResponse
        FE-->>User: «Би хүйсийн тэгш ...»
    end

    Note over CS: Step 2: Greeting
    CS->>CS: query in _GREETINGS?
    alt Greeting
        CS-->>API: Greeting response
    end

    Note over CS: Step 3: Safety check
    CS->>CL: predict(query)
    CL-->>CS: {label, confidence, is_safe}

    Note over CS: Step 4: Crisis downgrade
    CS->>CS: _has_crisis_indicator(query)?
    alt Real crisis
        CS->>DB: log_chat
        CS-->>API: SAFETY_RESPONSES[label]
        API-->>FE: ChatResponse with safety warning
    end

    Note over CS: Step 5: Vague check
    alt Vague query
        CS-->>API: Clarification response
    end

    Note over CS: Step 6: RAG retrieval + generation
    CS->>CS: search_query = prefix + query
    CS->>RAG: search(search_query)
    RAG->>FAISS: vector search top_k=2
    FAISS-->>RAG: chunks with scores
    RAG-->>CS: retrieved_chunks

    alt No retrieval
        CS-->>API: «Дэлгэрэнгүй бичнэ үү»
    end

    CS->>GEN: generate(query, chunks)

    alt Top chunk = FAQ + score ≥ 0.55
        GEN-->>CS: FAQ direct answer
    else
        GEN->>LLM: POST /api/chat<br/>system + context + question
        LLM-->>GEN: generated text
        GEN->>GEN: clean citation headers
        GEN-->>CS: answer + sources
    end

    CS->>CS: post-generation sanity check
    CS->>DB: INSERT INTO chat_logs
    CS-->>API: response dict
    API-->>FE: ChatResponse JSON
    FE-->>User: Хариулт + sources panel + safety
```

## Тайлбар

Чат хүсэлтийн дараалал нь Boloroo системийн **бүх routing logic**-ийг харуулна. Хэрэглэгчээс асуулт орж ирэхэд `ChatService.process_query()` нь дараалласан 6 шалгуурыг гүйцэтгэдэг:

1. **Identity shortcut** — «чи хэн бэ» гэх мэт өөрийг танилцуулах асуултад RAG/LLM-г огт ашиглахгүй шууд хариулна.
2. **Capability shortcut** — «чи юу хийж чадах вэ» гэх мэт өөрийн чадварын тухай асуултад мөн шууд хариулна. Энэ нь сурсан classifier «туслаач» гэх мэт үгийг crisis гэж андуурахаас сэргийлдэг.
3. **Greeting shortcut** — «сайн уу» зэрэгт LLM-ийн нөөц зарцуулахгүй шууд мэндчилгээ өгнө.
4. **Safety classification** — TF-IDF + LogReg classifier 5 ангилалд шалгана. `self_harm` эсвэл `harassment` гэж тэмдэглэгдэвч **бодит хямралын үг (`_CRISIS_INDICATORS_RE`) байхгүй бол safe-руу буцаах downgrade** хийдэг — false positive-ыг бууруулах ухаалаг механизм.
5. **Vague query shortcut** — «яах вэ?», «хэрхэн?» зэрэгт тодруулах асуулт буцаана.
6. **RAG retrieval + LLM** — FAISS-аас top-2 chunk олж, Ollama-руу дамжуулна. Top chunk нь FAQ бөгөөд score өндөр бол **LLM-г огт тойрно**.

Бүх алхамын төгсгөлд `chat_logs` хүснэгтэд логлогддог.

## Дипломын тайланд ашиглах тайлбар

Энэ диаграм нь системийн **гүйцэтгэлийн оптимизацийг** харуулна. RAG системд тулгардаг гол асуудал бол **бүх асуултыг LLM-руу зориулахад** хариу хугацаа удаашрах юм (CPU дээр Ollama-р хариулт үүсгэхэд 5–30 секунд). Тиймээс энэ систем нь **early-exit shortcuts** ашиглаж:

- Identity / Capability / Greeting асуулт **миллисекунд хүртэл хурдан хариулагдана** (regex match → static text).
- FAQ-ийн өндөр-similarity хариултууд **LLM-г бүр алгасна**.
- Зөвхөн жинхэнэ агуулгат асуулт LLM-р дамжина.

Энэ нь **CPU-only laptop орчинд хэрэглэгчийн UX**-ийг сайжруулдаг практик инноваци бөгөөд дипломын ажлын **system design-ын ухаалаг шийдэл** болж тайлагнах боломжтой.

Бас **safety pipeline**-ийн дараалал нь чухал: classifier-ийн urьдчилсан шалгалт RAG-аас өмнө хийгдэнэ. Ингэснээр аюултай оролт vector store-ыг бохирлодоггүй, нөөц цаг алдагддаггүй.

## Хамгаалалтын үеэр тайлбарлах богино хувилбар

«Хэрэглэгч асуулт илгээхэд систем 6 шалгуураар дамжина: identity → capability → greeting → safety classifier → vague query → RAG+LLM. Эхний 3 нь LLM-г огт ашиглахгүй, шууд хариулдаг. Classifier нь аюултай оролтыг блоклох ба self_harm гэж тэмдэглэгдсэн боловч жинхэнэ хямралын үг байхгүй бол safe гэж тооцох ухаалаг downgrade хийдэг. RAG алхамд FAISS-аас top-2 chunk олоод, FAQ бол шууд хариу буцаах эсвэл Ollama руу прoмпт явуулна. Бүх харилцан үйлдэл SQLite-д logloгдож хэрэглэгчийн thumbs up/down feedback-ыг бичдэг.»
