# Дипломын Ажлын Аудит — Boloroo (Тэгшбот) Чатбот

**Огноо:** 2026-04-30
**Хянасан:** Senior software engineer / thesis reviewer (Claude Opus 4.7)
**Төслийн байршил:** `C:\Users\bolor\Diploma2026\Boloroo`
**Python орчин:** 3.14.2 (.venv бэлэн)
**Платформ:** Windows 11 Pro
**Хяналт хийсэн арга:** Source code review + safe runtime validation (loaded RAG index, ran classifier, reachability-checked Ollama, built frontend).

---

## 1. Төслийн Ерөнхий Дүгнэлт

**Boloroo (UI дээр «Тэгшбот»)** нь хүйсийн тэгш эрх, ялгаварлан гадуурхалт, хөгжлийн бэрхшээлтэй иргэдийн эрхийн талаар Монгол хэл дээр мэдээлэл өгдөг RAG-д суурилсан туслах чатбот юм. Бакалаврын дипломын ажлын хүрээнд боловсруулагдсан.

Систем нь **бодитоор хэрэгжсэн ажиллагаатай прототип** юм — зөвхөн загвар (mock-up) биш. Backend, frontend, RAG pipeline, custom classifier, нийт 12 эх сурвалжийн баримт бичиг, бэлэн FAISS индекс (3408 vector) бүгд бэлэн.

### Нийт үнэлгээ: **7.5 / 10** — Хамгаалалтад орох боломжтой, гэхдээ түргэн хугацаанд хэдэн тулгуур ажил хийх шаардлагатай.

| Бүрэлдэхүүн | Байдал | Үнэлгээ |
|---|---|---|
| Backend (FastAPI) | ✅ Импорт амжилттай, endpoint бүрэн | 9/10 |
| RAG Pipeline | ✅ Индекс ачаалагдаж, search ажиллаж байна | 9/10 |
| Frontend (React + Vite) | ✅ `vite build` амжилттай гарав | 8/10 |
| Custom Classifier | ⚠️ Ажилладаг, гэхдээ sklearn хувилбарын зөрчилтэй | 6/10 |
| Мэдлэгийн сан | ✅ 12 баримт, 3408 chunk, 5 MB FAISS | 8/10 |
| Ollama LLM | ✅ Локал серверт `qwen2.5:7b` ачаалагдсан | 8/10 |
| SQLite метадата | ⚠️ chat_logs/feedback бичигддэг, documents/chunks ХООСОН | 4/10 |
| Тест | ❌ Хоосон __init__.py-аас өөр юм байхгүй | 1/10 |
| Evaluation тайлан | ❌ Скрипт байгаа боловч тоон тайлан байхгүй | 2/10 |
| Деплой / Docker | ⚠️ Конфиг бэлэн, туршигдаагүй | 5/10 |
| Аюулгүй байдал | ⚠️ Admin endpoint-д auth байхгүй | 4/10 |
| Баримт бичиг (docs) | ⚠️ thesis_notes.md дотоод тэмдэглэл, академик хэлбэргүй | 5/10 |

---

## 2. Одоогийн Байдлаар Ажиллаж Байгаа Хэсгүүд (Validated)

### 2.1 RAG Pipeline — Live тестээр баталгаажсан
- `data/vectors/index.faiss` — **3408 vector**, 5.0 MB.
- `data/vectors/chunks.pkl` — **3408 chunk metadata**, 3.1 MB.
- Embedding model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384-dim, олон хэлний).
- Жишээ хайлт «Хүйсийн тэгш байдлын тухай хуулиар юу хамгаалагддаг вэ?» → Top-1 score = **0.949** (FAQ chunk-аас, маш сайн).
- FAQ-аар индексжүүлэх стратеги ажиллаж байна (`metadata.is_faq=True`, `_FAQ_SCORE_BOOST=0.12`, `_FAQ_DIRECT_THRESHOLD=0.55`).
- Дедупликаци, source citation, law-reference extraction (`_LAW_REF_RE`) бүгд хэрэгжсэн.

### 2.2 Backend API — Импорт ба endpoint бүрэн
Хэрэгжсэн endpoint-ууд (`backend/app/api/routes.py`):
- `POST /api/chat` — гол чат endpoint (safety → routing → RAG → Ollama).
- `POST /api/feedback` — thumbs up/down хүлээн авах.
- `POST /api/ingest` — PDF/TXT баримт бичиг оруулах.
- `GET /api/documents` — оруулсан баримт бичгийн жагсаалт.
- `DELETE /api/documents/{id}` — soft delete.
- `GET /api/health` — индекс/classifier ачаалагдсан эсэхийг шалгах.
- `GET /api/stats` — admin dashboard-д зориулсан статистик.
- Pydantic schema (`schemas/schemas.py`) бүх request/response-ыг баталгаажуулна.
- Lifespan context manager-аар RAG, classifier, ingest service-ийг startup-д ачаалдаг.

### 2.3 Аюулгүй Байдлын Ангилагч — Live тестээр баталгаажсан
- 5 анги: `safe`, `hate_speech`, `harassment`, `discrimination`, `self_harm`.
- TF-IDF char n-gram (2–5) + Logistic Regression.
- Жишээ:
  - «Хүйсийн тэгш байдлын тухай хуулиар юу хамгаалагддаг вэ?» → `safe` (0.947) ✅
  - «Эмэгтэйчүүд удирдах албан тушаал хашихад тохиромжгүй» → `hate_speech` (0.674) ✅
  - «Би амьдрахыг хүсэхгүй байна» → `self_harm` (0.891) ✅
- `chat_service.py` дотор «туслаач», «тусла» зэрэг үгийг хямрал гэж андуурахгүй downgrade логик бичигдсэн.

### 2.4 Ollama LLM — Локал серверт ачаалагдсан
- `http://localhost:11434/api/tags` шалгалт амжилттай.
- `qwen2.5:7b` (4.7 GB, Q4_K_M quantization) бэлэн.
- Хариулт үүсгэх дараах тохиргоотой: temperature=0.15, num_predict=250, timeout=90s.
- FAQ fast-path Ollama-г тойрч хурдан хариулна (score ≥ 0.55 үед).

### 2.5 Frontend — Build амжилттай
- `npx vite build` → `frontend/dist/` амжилттай үүссэн (1.1 KB index.html + assets).
- 3 хуудас: LandingPage, ChatPage (3 ангиллын meta-тай), AdminPage.
- 3 component: MessageBubble, SourcePanel (citation + law refs + relevance %), SafetyWarning.
- Vite proxy: `/api` → `http://localhost:8000`.
- Бүх UI текст Монгол хэл дээр.

### 2.6 Эх Сурвалж Баримт Бичгүүд
| Файл | Хэлбэр | Хэмжээ |
|---|---|---|
| ГЭР БҮЛИЙН ТУХАЙ.pdf | PDF (хууль) | 161 KB |
| Гэр бүлийн хүчирхийлэлтэй тэмцэх тухай.pdf | PDF | 165 KB |
| Жендэрийн эрх тэгш байдал.pdf | PDF | 127 KB |
| ИРГЭНИЙ ХУУЛЬ.pdf | PDF | 1.05 MB |
| ХӨГЖЛИЙН БЭРХШЭЭЛТЭЙ ХҮНИЙ ЭРХИЙН ТУХАЙ.pdf | PDF | 173 KB |
| disability_rights_guide.txt | Гарын авлага | 9.4 KB |
| discrimination_guide.txt | Гарын авлага | 8.4 KB |
| gender_equality_guide.txt | Гарын авлага | 6.6 KB |
| faq.txt | Нийтлэг FAQ | 11 KB |
| faq_disability.txt | FAQ | 21 KB |
| faq_discrimination.txt | FAQ | 18 KB |
| faq_gender_equality.txt | FAQ | 19 KB |

---

## 3. Дутуу Болон Эрсдэлтэй Хэсгүүд

### 🔴 ЧУХАЛ ЭРСДЭЛ

#### 3.1 Тест бүрэн хоосон (Critical)
```
tests/
├── test_backend/    ← __init__.py л байна
├── test_integration/ ← хоосон
├── test_rag/        ← хоосон
└── test_training/   ← хоосон
```
**Эрсдэл:** «Та системийг хэрхэн шалгасан бэ?» гэж асуухад баталгаа байхгүй. Дипломын комисст энэ нь сул талыг харуулна.
**Засвар:** Хамгийн наад зах нь 5–7 нэгж/integration тест нэмэх (FIX_PLAN_MN.md-д тодорхой санал).

#### 3.2 Evaluation тайлан байхгүй (Critical)
`scripts/evaluate_answers.py`, `evaluate_retrieval.py`, `evaluate_safety.py` гэсэн **3 evaluation скрипт байна**, гэвч **дүн тайлан, графикыг өгүүлэхүйц гаралт байхгүй**. `evaluate_user_survey.md` нь судалгааны загвар (template) бөгөөд бөглөгдөөгүй.
**Эрсдэл:** «Системийн чанарыг хэрхэн хэмжсэн бэ? Recall@k хэд вэ? Аюулгүй байдлын classifier F1 хэд вэ?» — комиссын стандарт асуулт.
**Засвар:** Скриптүүдийг ажиллуулж, `docs/evaluation/` хавтсанд CSV+JSON+PNG гаргах. Тоон үр дүн дипломын тайланд орох ёстой.

#### 3.3 SQLite metadata vs FAISS index зөрчилтэй (High → Critical Demo Risk)
- FAISS индекст **3408 vector**.
- SQLite `documents` хүснэгт: **0 row**.
- SQLite `chunks` хүснэгт: **0 row**.
- Шалтгаан: `scripts/ingest.py` зөвхөн `RAGPipeline.ingest_document()` дуудна. Энэ нь FAISS-д vector нэмдэг боловч `documents`/`chunks` хүснэгтэд бичдэггүй. SQL метадата-г зөвхөн `IngestService.ingest_file()` (Admin upload endpoint) бичдэг.
- **Үр дагавар:** Admin хуудсан дээр «Баримт бичиг (0)» гэж харагдана, статистик буруу — чат логууд ажиллаж байгаа боловч эх сурвалжийн жагсаалт хоосон.
- **Засвар (FIX_PLAN_MN.md-д дэлгэрэнгүй):** `scripts/ingest.py`-г `IngestService.ingest_file()`-г дуудах, эсвэл одоогийн chunks.pkl-аас SQL-руу backfill скрипт бичих.

#### 3.4 Sklearn хувилбарын зөрчил (High)
Сургагдсан pickle файлууд `sklearn 1.5.2`-д үүссэн боловч одоогийн орчин `sklearn 1.8.0`. `InconsistentVersionWarning` гарна. Хуурамч ажиллагаатай мэт боловч ямар нэг нийцгүй хувилбарын дараах өөрчлөлт гэнэт хариуны чанарыг бууруулж болно.
**Засвар:** `requirements.txt`-д `scikit-learn==1.5.2` болгон pin хийх **эсвэл** одоогийн орчинд `python training/scripts/train.py` ажиллуулж загварыг дахин сургах.

#### 3.5 Сургалтын dataset хэт жижиг (High)
- `training/data/dataset.csv`: 120 sample.
- `training/data/dataset_expanded.csv`: 226 sample.
- Хадгалагдсан загвар (training_metadata.json) **120 sample-аар сургагдсан** — өргөтгөсөн dataset ашиглагдаагүй.
- F1 macro = 0.949 гэсэн өндөр дүн **хэт жижиг тест set-ээс гарсан** (тест 24 sample, нэг ангид 4 sample).
- **Эрсдэл:** «Та дөнгөж 24 sample-аар тест хийж F1=0.94 гэж тайлагнаж байна — энэ статистикийн хувьд утгагүй» — комисс энэ дээр гацуулна.
- **Засвар:** `dataset_expanded.csv`-аар дахин сургах + cross-validation үр дүнг тайланд оруулах.

### 🟠 ДУНД ЗЭРГИЙН ЭРСДЭЛ

#### 3.6 Admin endpoint-д нэвтрэлт байхгүй (High)
`POST /api/ingest`, `DELETE /api/documents/{id}`, `GET /api/stats` бүгд open. Хэн ч баримт оруулах, устгах боломжтой.
**Хамгаалалтад дурдах эсвэл:** «Зөвхөн локал орчинд ажиллах прототип учир auth дараагийн алхамд орох болно» гэж тайлбарлах.
**Засвар:** HTTP Basic Auth эсвэл environment-token-based middleware (5–10 минутын ажил).

#### 3.7 .env commit хийгдсэн
`.gitignore`-д байгаа боловч одоогийн `.env` файл репозитор дотор байна. Нууц мэдээлэл агуулаагүй (зөвхөн локал host/port) ч энэ нь академик хувьд буруу дадал.
**Засвар:** `git rm --cached .env` (хэрэв git ашиглаж байгаа бол).

#### 3.8 Python 3.14 — Хэт шинэ хувилбар
Python 3.14 нь 2024 онд гарсан, faiss-cpu/sentence-transformers зэрэг сангуудын идэвхтэй дэмжлэгийн талбараас гадуур. Боловч одоогоор бүх pip install амжилттай, импорт ажиллаж байгаа.
**Зөвлөмж:** Хамгаалалтын ноут-буукт ажиллаж байгаа эсэхийг урьдчилан баталгаажуулах. Хэрэв backup машин хэрэглэвэл Python 3.11/3.12-д suit-аар туршиж үзэх.

#### 3.9 TOP_K=2 — Маш бага (Medium)
.env дотор `TOP_K=2`. Зөвхөн 2 chunk-аар хариулт үүсгэх нь олон сэдэвт асуултанд хангалтгүй мэдээлэл өгнө.
**Тайлбар:** CPU laptop-д хурдны үүднээс ингэсэн (rag/config.py-д бичигдсэн).
**Засвар:** Demo-гийн өмнө `TOP_K=3` болгох эсвэл хэвээр үлдээж шалтгааныг тайлбарлах.

#### 3.10 Docker туршигдаагүй (Medium)
`docker-compose.yml` бий боловч сургалтын моделийн volume mount, Ollama service эзэн backend-д байхгүй (`OLLAMA_BASE_URL=http://localhost:11434` нь container дотроос хост Ollama-руу хүрэхгүй).
**Засвар:** Хэрэв demo-д Docker ашиглах бол `OLLAMA_BASE_URL=http://host.docker.internal:11434` гэж тохируулах эсвэл `extra_hosts` нэмэх.

### 🟡 БАГА ЗЭРГИЙН ЭРСДЭЛ

#### 3.11 React Router байхгүй
Routing нь state-based (`useState`). URL хаяг өөрчлөгдөхгүй, share хийх боломжгүй. Production-нд асуудал, демо-д асуудалгүй.

#### 3.12 docs/ хавтас академик стандарт хүрэхгүй
- Зөвхөн `thesis_notes.md` (дотоод тэмдэглэл).
- Албан ёсны архитектурын зураг, диаграм байхгүй (шинээр нэмж байна — `docs/diagrams/`).

#### 3.13 Rate limiting байхгүй
Чат endpoint хязгааргүй. DOS эрсдэл бага (локал) ч production-д шаардлагатай.

#### 3.14 thesis_notes.md commit
Дотоод тэмдэглэл хэвээр commit хийгдсэн. Final тайланд PR description дотор хадгалах эсвэл `.gitignore`-т нэмэх нь зүйтэй.

#### 3.15 Default `bot` нэр vs UI нэр зөрчилтэй
Backend system prompt дээр өөрийгөө «Болороо» гэж нэрлэдэг (chat_service.py:_IDENTITY_RESPONSE), Frontend бранд нь «Тэгшбот». Энэ давхар нэрийг ширтэхдээ гайхаж магад. Ялангуяа дипломын тайланд аль нэрийг ашиглах ёстойг шийдэх.

---

## 4. Хамгаалалтад Ороход Хангалттай Эсэх Үнэлгээ

### Дүгнэлт: ✅ **Хамгаалалтад орох боломжтой — гэхдээ 4–6 цагийн нэмэлт ажил шаардлагатай**

**Давуу талууд (комисст хүчтэй харагдах):**
- Бодит ажиллах систем — frontend `vite build`, backend ийм, classifier predict, RAG search бүгд live тестээр баталгаажсан.
- Архитектур цэвэр зохион байгуулагдсан (api → services → db pattern).
- Олон оролтын стратегитай (capability shortcut, identity shortcut, greeting shortcut, vague-query, classifier downgrade) — энэ нь техникийн хувьд гүнзгий бодсон гэдгийг харуулна.
- FAQ fast-path optimization (LLM-ийг тойрох) бол шууд хэрэгтэй инноваци.
- Custom-trained classifier бий — энэ бол дипломын мөн чанарын хүчтэй элемент.
- Локал Ollama — судалгаа-аж ахуйн нууц өгөгдөл руу нийтийн API руу хазайхгүй.

**Сул талууд (хамгаалалтын өмнө заавал засах):**
- Тест **бүрэн хоосон** — энэ дотор магадгүй хамгийн их дайралттай асуулт орно.
- Evaluation тоон тайлан байхгүй — F1, recall@k, latency аль нь ч баримтжуулагдаагүй.
- SQLite documents/chunks vs FAISS зөрчил — Admin хуудас хоосон харагдана.
- Загвар хуурамч ажиллах магадлал (sklearn хувилбар тохирохгүй) — re-train эсвэл pin шаардлагатай.

---

## 5. Нэн Түрүүнд Засах Шаардлагатай Зүйлс (Сэргээх ажил)

| # | Ажил | Хугацаа | Файл/команд |
|---|------|---------|---|
| 1 | Sklearn pin хийж classifier-ыг дахин сургах | 30 мин | `pip install scikit-learn==1.5.2 ; python training/scripts/train.py` |
| 2 | dataset_expanded.csv-аар сургах | 30 мин | `train.py` аль хэдийн expanded preference-тэй, дахин ажиллуулах л хэрэгтэй |
| 3 | scripts/ingest.py-г SQL-д бичдэг болгох | 30 мин | `IngestService.ingest_file()`-г дуудах эсвэл backfill скрипт бичих |
| 4 | 5–7 нэгж тест бичих | 2 цаг | `tests/test_rag/test_pipeline.py`, `tests/test_backend/test_chat_api.py`, `tests/test_training/test_classifier.py` |
| 5 | Evaluation скриптүүдийг ажиллуулж тоон үр дүн гаргах | 1 цаг | `python scripts/evaluate_*.py` |
| 6 | Demo сценари бэлдэх (3–5 жишээ асуулт) | 30 мин | `docs/DEMO_SCRIPT_MN.md` |
| 7 | TOP_K=3 болгох (эсвэл шалтгааныг тайлбарлах) | 5 мин | `.env` |
| 8 | Admin endpoint-д наад зах нь Basic Auth нэмэх | 30 мин | `backend/app/api/routes.py` |
| 9 | README_MN.md үүсгэх | 30 мин | (FIX_PLAN_MN-д хэвлэгдсэн) |

**Нийт: ~6 цаг тулгуур ажил.**

---

## 6. Дараагийн Сайжруулалтын Roadmap

### 6.1 Хамгаалалтын өмнө (заавал)
- 5-р хэсгийн жагсаалт.

### 6.2 Хамгаалалтын дараа (ажил эрхлэх / нийтлэх стандартад хүргэх)
- JWT-based admin auth.
- Rate limiting (slowapi эсвэл fastapi-limiter).
- Chat history persistence хэрэглэгчийн тал руу.
- Streaming response (Server-Sent Events) — UX мэдэгдэхүйц сайжирна.
- React Router нэмэх (URL-based navigation).
- Docker compose дотор Ollama сервисийг (GPU-d) нэмэх.
- I18n switch — Англи UI дэмжлэг.

### 6.3 Урт хугацааны судалгаа
- Хариулт үнэлэх human-rater + LLM-judge hybrid pipeline.
- Илүү олон тооны эрх зүйн баримт бичиг (Засгийн газрын тогтоол, олон улсын конвенци).
- Хэрэглэгчийн thumbs-down feedback-ыг сургалтад оруулах (active learning).
- Hybrid retrieval (BM25 + vector) — pure semantic search-ийн мэт ондоо тоо чанарыг сайжруулах.

---

## 7. «Багш Асуувал Тайлбарлах Боломжтой Эсэх» Үнэлгээ

| Асуулт | Бэлдэлт |
|--------|---------|
| Яагаад RAG-г сонгосон бэ? | ✅ Бэлэн — эх сурвалжид тулгуурласан, hallucination бууруулдаг, Монгол хууль шинэчлэгдэхэд яаж бодит цагт мэдлэг шинэчилснийг тайлбарлаж чадна. |
| Яагаад FAISS, ChromaDB/Weaviate биш? | ✅ Локал, нээлттэй эх, баазын сервер шаарддаггүй, инлайн файл (5MB) хэлбэрээр хадгалагддаг. |
| Яагаад Ollama (OpenAI биш)? | ✅ API key шаарддаггүй, өгөгдлийн нууцлал, Монгол хэлийн дэмжлэг (qwen2.5), нэг ноут буукт ажилладаг. |
| Яагаад TF-IDF + LogReg classifier? | ✅ Жижиг dataset (~120 sample)-д тохиромжтой, тайлбарлах боломжтой (interpretable), CPU-д хурдан, deploy хялбар. |
| Chunk size=500 яагаад? | ✅ rag/config.py:7-12-д тайлбар бичигдсэн. |
| FAQ fast-path юу хийдэг вэ? | ✅ rag/generator.py:_FAQ_DIRECT_THRESHOLD-д тайлбар. |
| Capability shortcut яагаад хэрэгтэй вэ? | ✅ chat_service.py:_is_capability_question-д тайлбар (false-positive crisis ангилалаас сэргийлэх). |
| Тест юу бичсэн бэ? | ❌ **Хамгийн эрсдэлтэй асуулт** — одоогоор хариулт байхгүй. ЗААВАЛ ЗАСАХ. |
| Evaluation хийсэн үү? Recall@k? | ⚠️ Скрипт байгаа боловч тоон тайлан байхгүй. |
| Хариултын хариу хугацаа хэд вэ? | ⚠️ chat_logs дотор response_time_ms бичигддэг боловч нийт дундаж тооцоологдоогүй. |
| Аюулгүй байдлын тестийг хэрхэн хийсэн бэ? | ⚠️ scripts/evaluate_safety.py байгаа, гэвч ажиллуулж тайлан гаргах хэрэгтэй. |
| Deploy хэрхэн? | ⚠️ Docker compose байгаа, туршигдаагүй. Локал uvicorn deploy-р хязгаарлахыг зөвлөж байна. |
| Custom model F1=0.94 гэдэг үнэн үү? | ⚠️ 24 sample-аас гарсан учир статистикийн утгагүй. dataset_expanded.csv-аар дахин сургах хэрэгтэй. |
| Хэн нь secrets хариуцлага хүлээх вэ? | ✅ Локал deployment, нууц өгөгдөл түр хадгалдаггүй (chat_logs SQLite дотор хадгалагдах ч хэрэглэгчийн ID байхгүй — анонимах). |

**Нийт:** 14 асуултаас 8 нь бэлэн, 5 нь дутуу, 1 нь шууд эрсдэлтэй.

---

## 8. Priority Table — Засах ажлын тэргүүлэх дараалал

| Зэрэг | Асуудал | Файл / Байршил | Засвар | Цаг |
|---|---|---|---|---|
| 🔴 Critical | Тест байхгүй | `tests/` | 5–7 pytest тест нэмэх | 2 цаг |
| 🔴 Critical | Evaluation тоон тайлан байхгүй | `scripts/evaluate_*.py` | Скриптүүдийг ажиллуулж `docs/evaluation/` руу гаргах | 1 цаг |
| 🔴 Critical | SQLite documents хоосон / FAISS-тай таарахгүй | `scripts/ingest.py`, `backend/app/services/ingest_service.py` | `IngestService.ingest_file` дуудах эсвэл backfill | 30 мин |
| 🟠 High | Sklearn хувилбарын зөрчил | `requirements.txt`, `training/models/*.pkl` | Pin хийх эсвэл re-train | 30 мин |
| 🟠 High | Classifier expanded dataset-аар сургагдаагүй | `training/scripts/train.py` | `python training/scripts/train.py` | 15 мин |
| 🟠 High | Admin endpoint open | `backend/app/api/routes.py` | HTTP Basic Auth middleware | 30 мин |
| 🟠 High | Demo Ollama бэлэн эсэхийг урьдчилан шалгах | `scripts/check_demo.py` (шинэ) | Pre-flight check скрипт | 30 мин |
| 🟡 Medium | TOP_K=2 бага | `.env` | TOP_K=3 болгох эсвэл тайлбарлах | 5 мин |
| 🟡 Medium | .env репо дотор | `.gitignore` | `git rm --cached .env` | 5 мин |
| 🟡 Medium | Bot нэрийн зөрчил (Болороо vs Тэгшбот) | `chat_service.py`, `App.jsx` | Нэг нэрэнд нэгтгэх | 10 мин |
| 🟡 Medium | Docker compose Ollama хүрэхгүй | `docker-compose.yml` | `host.docker.internal` тохируулах | 10 мин |
| 🟢 Low | React Router байхгүй | `frontend/src/App.jsx` | Хамгаалалтын дараа | 1 цаг |
| 🟢 Low | Rate limiting | `backend/app/api/routes.py` | Хамгаалалтын дараа | 30 мин |
| 🟢 Low | thesis_notes.md commit-той | `.gitignore` | `.gitignore`-д нэмэх | 5 мин |

---

## 9. Архитектурын Хүчтэй Талууд (Хамгаалалтын үед онцлох зүйлс)

1. **Service-pattern архитектур** — `api/ → services/ → db/ + rag/` цэвэр, тестлэгдэх боломжтой.
2. **Lifespan context manager** — startup/shutdown зохицуулалт зөв хийгдсэн.
3. **Pydantic validation** — бүх API-ийн request/response 100% баталгаажсан.
4. **Routing priority (6-level)** — capability → identity → greeting → safety → vague → RAG → fallback. Энэ нь UX-ийг сайжруулдаг сэтгэгдсэн design.
5. **FAQ fast-path** — LLM-г тойрч хурдан, хариултыг автор бичсэнтэй адил буцаадаг.
6. **Source fallback (timeout үед)** — Ollama хариу өгөхгүй үед хэрэглэгчид цэвэр Монгол хэлээр тайлбар + sources panel харуулна.
7. **FAQ-question-only embedding** — асуулт + хариултыг бүтнээр embedding хийхгүй, зөвхөн асуулт текстийг embedding хийдэг → query-FAQ similarity илүү өндөр.
8. **Soft delete** — баримт бичиг устгахдаа физик устгал хийдэггүй (`status='deleted'`).
9. **WAL mode SQLite** — concurrent бичих гүйцэтгэл сайн.
10. **Duplicate chunk detection** — давхардсан context хасдаг (rag/generator.py:_deduplicate_chunks).
11. **Category-aware query augmentation** — chat_service:_CATEGORY_CONTEXT prefix-аар retrieval-ийг чиглүүлдэг.
12. **Crisis indicator regex** — classifier-ийн false positive-ыг бодит хямрал болон энгийн «туслаач» гэхээс ялгадаг.
13. **Law-reference extraction** — sources panel дээр «14-р зүйл», «10.1 хэсэг» гэх мэт хууль зүйлийн дугаарыг автоматаар тэмдэглэж харуулдаг.
14. **Document title mapping** — гар бичсэн `_DOC_TITLES` dict-ээр source-ыг файлын нэрнээс илүү хүний унших боломжтой нэрээр харуулна.

---

## 10. Бодитоор Хийж Үзсэн Туршилтын Үр Дүн (Live)

| Шалгалт | Үр дүн |
|---|---|
| `python -c "import backend.app.main"` | ✅ Pass |
| `python -c "import rag.pipeline; rag.embeddings; rag.generator"` | ✅ Pass |
| `pipeline.initialize()` | ✅ FAISS index loaded: 3408 vectors, 3408 chunks |
| RAG search (`Хүйсийн тэгш байдлын ...`) | ✅ Top-1 score=0.949 (FAQ) |
| Classifier load + predict (3 жишээ) | ✅ Бүх 3 жишээ зөв ангилагдсан, гэхдээ sklearn version warning |
| `curl http://localhost:11434/api/tags` | ✅ Ollama reachable, qwen2.5:7b бэлэн |
| `npx vite build` | ✅ frontend/dist/ үүссэн (амжилттай) |
| SQLite tables (init_db) | ✅ documents/chunks/chat_logs/feedback бүгд үүссэн |
| SQLite row count (chat_logs / feedback) | ✅ 39 / 2 (өмнөх жишээ хэрэглээний логууд) |
| SQLite row count (documents / chunks) | ❌ 0 / 0 — FAISS-тай зөрчилтэй |

---

*Энэхүү аудитыг senior software engineer түвшний шалгалтаар бэлдэв. Бүх дүгнэлт source code болон бодит runtime туршилтад тулгуурлав.*
*Огноо: 2026-04-30. Хянагч: Claude Opus 4.7 (1M context).*
