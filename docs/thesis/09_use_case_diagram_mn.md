# 3.9 Use case диаграм

> **Зураг 3.9.** Boloroo системийн use case-ууд — энгийн хэрэглэгч, админ хэрэглэгч, систем гэсэн 3 actor-той.
> Эх сурвалж файлууд: `frontend/src/pages/LandingPage.jsx`, `frontend/src/pages/ChatPage.jsx`, `frontend/src/pages/AdminPage.jsx`, `backend/app/api/routes.py` (бүх 7 endpoint), `backend/app/services/chat_service.py`, `backend/app/services/ingest_service.py`.
> Source: `docs/diagrams/source/09_use_case_diagram.puml` · `docs/diagrams/source/09_use_case_diagram.mmd`
> Rendered: `docs/diagrams/rendered/09_use_case_diagram.png`

## Диаграм

```mermaid
flowchart LR
    User(["👤 Энгийн<br/>хэрэглэгч"])
    Admin(["🛡️ Админ"])
    System(["⚙️ Систем"])

    subgraph Boundary ["Boloroo чатбот"]
        UC1((["UC1: Ангилал сонгох"]))
        UC2((["UC2: Асуулт асуух"]))
        UC3((["UC3: Хариулт авах"]))
        UC4((["UC4: Эх сурвалж харах"]))
        UC5((["UC5: Санал өгөх"]))
        UC6((["UC6: Жишээ асуулт сонгох"]))
        UC7((["UC7: Баримт<br/>байршуулах"]))
        UC8((["UC8: Баримт жагсаалт"]))
        UC9((["UC9: Баримт устгах"]))
        UC10((["UC10: Health check"]))
        UC11((["UC11: Статистик"]))
        UC12((["UC12: Аюулгүй байдлыг<br/>ангилах"]))
        UC13((["UC13: Shortcut шалгах"]))
        UC14((["UC14: Vector хайлт"]))
        UC15((["UC15: FAQ fast-path"]))
        UC16((["UC16: LLM хариу"]))
        UC17((["UC17: Лог хадгалах"]))
        UC18((["UC18: Баримт<br/>боловсруулах"]))
        UC19((["UC19: FAISS шинэчлэх"]))
    end

    User --> UC1
    User --> UC2
    User --> UC3
    User --> UC4
    User --> UC5
    User --> UC6
    Admin --> UC7
    Admin --> UC8
    Admin --> UC9
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
    UC4 -.->|extend| UC2
```

## Тайлбар

Use case диаграм нь системийн **functional requirement**-уудыг гадаад хандлагаар (хэрэглэгчийн талаас) харуулдаг. Boloroo системд **гурван actor**:

### Actor бүрийн тайлбар

**1. Энгийн хэрэглэгч (UC1–UC6).** Эдгээр use case-ууд нь Frontend ChatPage болон LandingPage-аар авч болох бүх боломжуудыг хамруулна:
- *UC1: Ангилал сонгох* — `LandingPage.jsx`-д 3 категори (gender_equality, discrimination, disability) эх сурвалжийг карт хэлбэрээр харуулах ба `onSelectCategory(catId)`-аар state-руу шилжих.
- *UC2: Асуулт асуух* — ChatPage textarea-д текст бичиж Enter эсвэл «Илгээх» товч даран `sendChat(message, category)`-ыг triggers.
- *UC3: Хариулт авах* — `MessageBubble` component-аар render хийгдэх, `responseTime` (ms) харагдана.
- *UC4: Эх сурвалж харах* — `SourcePanel` modal-аар citation, document_title, page_number, law_references, relevance_score харуулна.
- *UC5: Санал өгөх* — thumbs up/down товчлуурууд `submitFeedback(chat_id, rating)`-ыг дуудна.
- *UC6: Жишээ асуулт сонгох* — `ChatPage.examples` массивт жишээ асуулт click хийхэд textarea-руу автоматаар орно.

**2. Админ хэрэглэгч (UC7–UC11).** Эдгээр use case-ууд нь AdminPage-аас явагдана:
- *UC7: Баримт байршуулах* — `<input type="file" accept=".pdf,.txt">` + title input → `uploadDocument(file, title)` → `POST /api/ingest`.
- *UC8: Баримт жагсаалт* — `getDocuments()` → `GET /api/documents` → table render.
- *UC9: Баримт устгах* — backend-д `DELETE /api/documents/{id}` endpoint бий, **гэхдээ UI-д устгах товч одоогоор хэрэгжээгүй**. Use case диаграмд тэмдэглэв.
- *UC10: Health check* — `getHealth()` → `GET /api/health` → admin dashboard-д статус, нийт chunk, classifier ачаалагдсан эсэх.
- *UC11: Статистик* — `getStats()` → `GET /api/stats` → нийт чат, эерэг санал, аюултай асуулт, дундаж хариу хугацаа.

**3. Систем (UC12–UC19).** Дотоод автомат use case-ууд. Эдгээр нь `system` actor-руу буюу backend дотор автоматаар гүйцэтгэгдэх ажилуудыг харуулна:
- *UC12: Аюулгүй байдлыг ангилах* — `SensitiveContentClassifier.predict(query)` нь TF-IDF + LR-ээр 5 ангилалд predict хийнэ.
- *UC13: Shortcut шалгах* — `_is_identity_question`, `_is_capability_question`, `_normalize(query) in _GREETINGS` гэсэн гурван давхар regex check.
- *UC14: Vector хайлт* — `RAGPipeline.search(query)` нь query embedding + FAISS IndexFlatIP search.
- *UC15: FAQ fast-path шалгах* — `top.is_faq && score >= 0.55` бол LLM-ийг тойрно.
- *UC16: LLM хариу үүсгэх* — `AnswerGenerator.generate()` дотроос Ollama POST /api/chat.
- *UC17: Лог хадгалах* — `_log_chat()` нь `INSERT INTO chat_logs`.
- *UC18: Баримт боловсруулах* — `RAGPipeline.ingest_document()` нь load → chunk → embed.
- *UC19: FAISS шинэчлэх* — `EmbeddingManager.save()` нь файл руу бичих.

### Хамаарлууд

- **`include` (заавал)** — UC2 (Асуулт асуух) нь UC13 (shortcut), UC12 (classifier), UC14 (vector хайлт), UC15 (FAQ check), UC16 (LLM)-ыг бүгдийг шаардана. UC3 нь UC17-ыг шаардана. UC7 (баримт байршуулах) нь UC18 + UC19-ыг шаардана.
- **`extend` (нэмэлт)** — UC4 (Эх сурвалж харах) нь UC2-ийн нэмэлт буюу хариу гарсны дараа шаардлагатай үед нэмж очдог.

### Auth-ийн тэмдэглэл

Одоогоор системд **role-based access control хэрэгжээгүй**. Энгийн хэрэглэгч ↔ Админ хэрэглэгчийн ялгаа нь зөвхөн Frontend navigation-аар (LandingPage/ChatPage vs AdminPage) ялгагдана. Backend-ийн бүх endpoint open. UC7–UC11 use case-ууд нь физикээр хэн ч хийж болно. Энэ нь use case диаграмд тэмдэглэгдсэн боловч код-логик дотор хэрэгжүүлэх гэх FIX_PLAN_MN.md, Засвар №7 байна.

### Frontend-ээс хэрэгжээгүй endpoint

Backend-д `DELETE /api/documents/{id}` бий боловч AdminPage.jsx-д устгах товч одоогоор хэрэгжсэн биш — UI хязгаарлалт. UC9-ыг диаграмд тэмдэглэсэн боловч *«backend-only»* анхааруулгатай.

## Дипломын ажилд оруулах тайлбар

Уг диаграмыг *«3.9 Use case диаграм»* эсвэл *«2-р бүлэг — Шаардлагын анализ»*-д оруулна. Энэ нь:

1. **Functional requirements** — системийн хийх ёстой ажлуудыг хүний-уншихуйц хэлбэрээр харуулна.
2. **Actor-ийн ялгаа** — энгийн хэрэглэгч (мэдлэгийн хэрэглэгч) ба админ (мэдлэг тэжээгч)-ийг тодорхой ялгаж буйг харуулдаг.
3. **System actor** — *системийн дотоод автомат* use case-уудыг тусдаа ангилсан нь *«хэн юу хийдэг вэ»* гэсэн асуултанд тодорхой хариу болно.
4. **Include/extend** — нэг use case дотор олон туслах use case дамжих гэдгийг харуулдаг (UC2 → 5 include).

## Хамгаалалтын үеэр товчоор тайлбарлах

«Системд гурван actor байна: энгийн хэрэглэгч (асуулт асуух, хариу авах, эх сурвалж харах, санал өгөх), админ хэрэглэгч (баримт байршуулах, жагсаалт харах, статистик харах, health check), систем (аюулгүй байдлыг ангилах, shortcut шалгах, vector хайлт, FAQ fast-path, LLM-ээр хариу үүсгэх, лог хадгалах). UC2 (асуулт асуух) нь дотоод 5 use case-ыг include хийсэн compound use case. Одоогоор role-based access control хэрэгжээгүй, ирээдүйн ажил болж backend-д auth middleware нэмэх төлөвлөгөөтэй.»
