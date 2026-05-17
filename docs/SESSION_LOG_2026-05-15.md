# Session Log — 2026-05-14 → 2026-05-15

> A reconstruction of the working session for tomorrow's pickup.
> Covers what was done, why, current state of the project, and how to
> resume.

---

## 1. What this session accomplished (one-line summary)

Replaced the entire RAG stack (FAISS → ChromaDB, Ollama → Gemini 2.5 Flash,
trained classifier → LLM-as-judge), removed the 3-category UI in favor of
a single chat widget, and committed it all to git as commit `78404dc`.

---

## 2. Current state — what is set up and working

### Code
- All changes committed to `main` as `78404dc` on the **local** machine.
  Not pushed to `origin` yet.
- Old architecture is preserved at `backup/old-architecture-2026-05-14/`
  (28 files, 112 KB).

### Services / processes that may or may not be running
| Process | Port | Notes |
|---|---|---|
| FastAPI backend (new stack) | `:8000` | Started in this session via uvicorn. Likely still running when you resume; verify with `Get-NetTCPConnection -LocalPort 8000`. |
| Vite frontend (main worktree) | `:5173` | Started from `Boloroo\frontend`. Open `http://localhost:5173/` to use the app. |
| Ollama (no longer used) | `:11434` | Still running on the machine but unused by the new stack. Can be stopped without affecting anything. |

If neither backend nor frontend is up tomorrow, see Section 7 — "How to resume".

### Data
- ChromaDB at `data/vectors/chroma/` — **1,897 chunks indexed** with topic
  metadata (`gender_equality` / `discrimination` / `disability` / `general`).
  This directory is **NOT in git** (too big at 25 MB and rebuildable).
- SQLite at `data/boloroo.db` — chat logs from this session. NOT in git.
- Source documents at `data/raw/` — 12 files (PDFs + TXT FAQs). In git.

### Secrets
- `GEMINI_API_KEY` is in `.env` (gitignored). The key currently in use
  is the second one the user pasted (the first had a 0 quota on
  `gemini-2.0-flash`). Confirmed working against `gemini-2.5-flash`.

---

## 3. Architecture migration — chronological summary

The session walked through several distinct phases:

### Phase A — Discovery & backup
1. Started in a Claude Code worktree (`youthful-wing-730ece`); the actual
   project code lives in the main repo at `C:\Users\bolor\Diploma2026\Boloroo`.
2. Identified that a previous dev server on `:5175` was running from a
   different worktree (`thirsty-ardinghelli-ece2f2`) which had uncommitted
   frontend work (`LandingPage.jsx`, `App.jsx`, `index.css`, plus a new
   `ChatWidget.jsx`).
3. Copied those frontend files into the main repo's working tree (the
   "quick path" — no git history for the copy, just file replacement).
4. Per user request, copied `backend/` and `rag/` from the main repo to
   `backup/old-architecture-2026-05-14/` so the prior architecture is
   preserved for thesis history.

### Phase B — RAG stack rewrite
Goals: ChromaDB instead of FAISS pickle files, Gemini instead of Ollama,
BGE-M3 embeddings instead of MiniLM. All free-tier compatible.

1. Updated `requirements.txt` — dropped `faiss-cpu`, added `chromadb`,
   added `google-genai` (the new Google SDK; the older
   `google-generativeai` is deprecated).
2. Rewrote `rag/config.py` for the new model names + persist paths +
   updated system prompt.
3. Wrote `rag/vector_store.py` from scratch — ChromaDB persistent client,
   BGE-M3 embeddings via sentence-transformers, optional BGE-reranker-v2-m3,
   per-chunk topic metadata inferred from filename, FAQ score boost
   preserved. Deleted `rag/embeddings.py`.
4. Rewrote `rag/generator.py` for `google-genai` SDK. Preserved Mongolian
   post-processing (citation header strip, law-reference extraction,
   document-title map).
5. Updated `rag/pipeline.py` to use `vector_store` instead of
   `embedding_manager`.
6. Patched callers: `chat_service.py`, `ingest_service.py`, `routes.py`,
   `main.py`, `scripts/ingest.py`, `scripts/evaluate_retrieval.py`.

### Phase C — Bring up the new stack
1. Installed deps in `.venv` (Python 3.14).
2. First tried `gemini-2.0-flash` — the user's Google account had **quota 0**
   on this model (free tier disabled). Switched default to
   `gemini-2.5-flash`, which works.
3. Found that gemini-2.5 does "thinking" by default which consumed all
   400 output tokens before any answer was emitted (truncated replies).
   Disabled it with `ThinkingConfig(thinking_budget=0)` and raised
   `LLM_MAX_TOKENS` to 600.
4. BGE-reranker-v2-m3 was loaded but added ~40 s per query on CPU.
   Set `USE_RERANKER=false` in `.env`.
5. Killed the orphan multiprocessing-fork child that was holding `:8000`
   after the old backend was stopped (classic Windows zombie).

### Phase D — UI consolidation (per user direction)
1. Removed the 3-category cards and the `ChatPage.jsx` route.
2. Lifted `chatOpen` state into `App.jsx`. Landing page CTA + floating
   button now both open the same `ChatWidget`.
3. `ChatWidget.jsx` rewritten — no category-selection screen. One
   greeting + 3 example questions covering all topics.
4. Backend `chat_service.py` — removed `_CATEGORY_CONTEXT` and category
   prepend logic. Single shared corpus search.

### Phase E — Safety / relevance refactor
The trained TF-IDF classifier kept producing false positives:

| User query that was wrongly blocked | What it was actually asking |
|---|---|
| "Хэрэв эмэгтэйчүүд эсвэл хөгжлийн бэрхшээлтэй хүмүүсийн эрх зөрчигдвөл ямар байгууллагад хандах вэ?" | Where to turn when rights are violated |
| "Хэрэв ажил олгогч намайг хүйсээс болж ажилд авахгүй бол яах вэ?" | What to do if denied a job due to gender |
| "эмэгтэй дугуйчин" | Just two off-topic words (woman cyclist) |

We patched twice with help-seeking regexes, then took a step back and:
- **Removed the trained classifier entirely.**
- Replaced it with an LLM-as-judge — the system prompt instructs Gemini
  to do (1) scope check, (2) hate-speech check, (3) answer from sources.
- Kept the deterministic crisis-indicator regex (only fires on real
  immediate-danger phrases like "амиа", "үхмээр") → routes to canned
  hotline reply (103, 7012-0505, 108).

### Phase F — Retrieval / answer-quality tuning
- The FAQ fast-path (returning a stored FAQ answer verbatim when score ≥
  0.55) was firing on **wrong-topic** FAQ entries (e.g. legal-aid FAQ
  matched a psychological-support query at 0.95 cosine). With the
  reranker disabled, BGE-M3 cosine alone can't tell same-topic FAQ from
  question-specific FAQ. **Removed the FAQ fast-path entirely.** All
  queries now go through Gemini synthesis from the full top-k context.
- Updated system prompt to allow partial synthesis from adjacent
  sources ("Хэсэгчилсэн хариулт өгч мэргэжлийн байгууллагаас илүү
  дэлгэрэнгүй мэдээлэл авах боломжтойг сануулна") rather than
  refusing outright when no chunk directly answers.
- Added 2 retries with backoff on Gemini 5xx (free tier returns 503s
  sporadically).

### Phase G — Documentation
- Wrote `docs/THESIS_GUIDE.md` (this directory) — architecture diagrams
  (mermaid), full tech-stack with citations, run guide, references.
- Wrote this `SESSION_LOG_2026-05-15.md` for tomorrow.

### Phase H — Commit
- Updated `.gitignore` to exclude `data/vectors/chroma/` and `.claude/`.
- Committed everything as `78404dc` on `main`. Not pushed.

---

## 4. Decisions made in this session, with rationale

| Decision | Why |
|---|---|
| ChromaDB over Qdrant | Embedded (no separate server), SQLite-backed, simpler for a thesis demo. |
| BGE-M3 over MiniLM | 1024-dim multilingual, top-tier on Mongolian Cyrillic. ~560 MB download but fits free-tier RAM. |
| Gemini 2.5 Flash over Claude/OpenAI | Free tier (~250 req/day, 10 RPM). User explicitly required costless. |
| Disable thinking | 2.5 models eat output budget on "thinking" tokens before producing visible text. Grounded RAG doesn't need it. |
| Reranker off by default | ~40 s extra latency per query on CPU. ~10% precision loss is the trade-off. |
| Drop the trained classifier | Too many false positives; required ever-growing regex patches. LLM-as-judge is robust and free (one call per query that we were already making). |
| Drop the FAQ fast-path | Without the reranker, cosine similarity alone fires the fast-path on wrong-topic FAQs. Synthesis through Gemini is more accurate at a 2-3 s latency cost. |
| Single chat (no categories) | User asked. Also simpler UX and removes the misleading category prefix that was hurting cross-topic retrieval. |
| Keep crisis-indicator hard block | Conversation with someone in crisis should not be an LLM dialogue. Deterministic hotline reply (103 / 7012-0505 / 108). |
| Keep `category` parameter in schema | Back-compat; ignored by the service. Safer than breaking the API contract. |
| Folder backup over git tag | More inspectable. Tag would only capture committed state and most thesis-relevant context was uncommitted at the time. |

---

## 5. Files that changed this session

(See `git show 78404dc --stat` for the full list.)

| Area | Files |
|---|---|
| Vector store | `rag/vector_store.py` (new), `rag/embeddings.py` (deleted/moved to backup) |
| LLM generator | `rag/generator.py` (rewritten for `google-genai`) |
| RAG glue | `rag/pipeline.py`, `rag/config.py` |
| Backend service | `backend/app/services/chat_service.py` (classifier removed, category logic removed) |
| Backend config | `backend/app/core/config.py`, `backend/app/main.py` |
| Backend routes | `backend/app/api/routes.py` (health endpoint cleaned) |
| Ingest | `backend/app/services/ingest_service.py`, `scripts/ingest.py` |
| Frontend | `frontend/src/App.jsx`, `frontend/src/pages/LandingPage.jsx`, `frontend/src/components/ChatWidget.jsx` (new), `frontend/src/pages/ChatPage.jsx` (deleted), `frontend/src/services/api.js`, `frontend/src/styles/index.css` |
| Eval | `scripts/evaluate_retrieval.py` |
| Config | `.env`, `.env.example`, `requirements.txt`, `.gitignore` |
| Docs | `docs/THESIS_GUIDE.md` (new), `docs/SESSION_LOG_2026-05-15.md` (new) |
| Backup | All of `backup/old-architecture-2026-05-14/` (new, 28 files) |

---

## 6. Known issues / open items

1. **`scripts/evaluate_answers.py` was not updated** — it still references
   Ollama for LLM-as-judge. If you want to run answer evaluation, that
   file needs porting to Gemini (similar pattern to `rag/generator.py`).
2. **Diagrams in `docs/diagrams/` and `docs/thesis/`** still reference
   the old stack (FAISS, Ollama). They're thesis documentation, not
   active code, so they don't break anything — but for a final thesis
   submission you'll want to update them.
3. **Orphan FAISS index files** at `data/vectors/index.faiss`,
   `data/vectors/chunks.pkl` (+ `.bkp` variants) are still on disk.
   Safe to delete now that Chroma is in place. They were left so you
   could verify the new pipeline first.
4. **Old worktree** (`thirsty-ardinghelli-ece2f2`) still exists at
   `.claude/worktrees/`. The dev server it was serving is dead. Can be
   removed with `git worktree remove` if desired.
5. **Free-tier quota**. Gemini 2.5 Flash free tier is roughly 10 RPM
   and 250 RPD. If a user demo hits this, switch `GEMINI_MODEL` to
   `gemini-2.5-flash-lite` for higher RPM (lower quality).
6. **No streaming** — `/api/chat` returns the whole response at once.
   Frontend shows the typing indicator until the response lands.
7. **No conversation memory** — each `/api/chat` call is independent.
   Multi-turn would need a `session_id` and per-session context.
8. **Old CSS classes** for the removed category cards (`.category-card`,
   `.cat-gender`, `.cat-discrimination`, `.cat-disability`) are still
   in `frontend/src/styles/index.css`. Dead but harmless.

---

## 7. How to resume tomorrow

### Quick start (if everything is still running)

```bash
# 1. Open the app
# → http://localhost:5173/

# 2. Verify backend is up
curl http://127.0.0.1:8000/api/health
```

### Cold start (if you restarted the laptop)

```powershell
# Terminal 1 — backend
cd C:\Users\bolor\Diploma2026\Boloroo
.venv\Scripts\activate
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — frontend
cd C:\Users\bolor\Diploma2026\Boloroo\frontend
npm run dev
```

If port 8000 is "in use" but no Python process is visible:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "spawn_main" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

### Re-ingest the corpus (if `data/vectors/chroma/` is missing)

```powershell
cd C:\Users\bolor\Diploma2026\Boloroo
.venv\Scripts\activate
python scripts/ingest.py
```

First run downloads BGE-M3 (~560 MB) — takes 5-15 minutes.

### Push to GitHub (if you want remote backup)

```powershell
cd C:\Users\bolor\Diploma2026\Boloroo
git push
```

The local commit is `78404dc`; `origin/main` is one commit behind it.

---

## 8. Reference — commands used in this session

```powershell
# Smoke-test /api/chat with proper UTF-8 (Windows curl mangles Cyrillic)
.venv\Scripts\python.exe -X utf8 -c "
import urllib.request, json
req = urllib.request.Request(
    'http://127.0.0.1:8000/api/chat',
    data=json.dumps({'message': 'Ялгаварлан гадуурхалт гэж юу вэ?'}, ensure_ascii=False).encode('utf-8'),
    headers={'Content-Type': 'application/json; charset=utf-8'},
)
print(urllib.request.urlopen(req, timeout=60).read().decode('utf-8'))
"

# Inspect what's currently in ChromaDB
.venv\Scripts\python.exe -X utf8 -c "
import sys; sys.path.insert(0, '.')
from rag.config import RAGConfig
from rag.vector_store import VectorStore
vs = VectorStore(config=RAGConfig())
print('count:', vs.count)
"

# List available Gemini models for your API key
.venv\Scripts\python.exe -X utf8 -c "
import os
from dotenv import load_dotenv
load_dotenv()
from google import genai
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
for m in client.models.list():
    if 'generateContent' in (m.supported_actions or []):
        print(m.name)
"
```

---

## 9. Useful files to skim when picking back up

1. `docs/THESIS_GUIDE.md` — the full project guide written this session.
2. `backend/app/services/chat_service.py` — the routing + crisis-gate logic.
3. `rag/generator.py` — the Gemini call, including retry on 503.
4. `rag/vector_store.py` — the ChromaDB wrapper and topic inference.
5. `rag/config.py` — the system prompt that does the agent's
   relevance + hate-speech checks.
6. `.env` — make sure `GEMINI_API_KEY` is set, `USE_RERANKER=false`,
   `GEMINI_MODEL=gemini-2.5-flash`, `LLM_MAX_TOKENS=600`.

---

*End of session log.*
