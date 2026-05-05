# Boloroo — Хүйсийн болон нийгмийн тэгш байдлын чатбот

**Boloroo** is a Mongolian-language RAG-based chatbot for gender equality and social inclusion education.

## Architecture

The system has three core components:

1. **Sensitive Content Classifier** — Custom-trained model that detects harmful input (hate speech, harassment, discrimination, self-harm indicators)
2. **RAG Pipeline** — Retrieves relevant document chunks from verified sources using vector similarity search
3. **LLM Answer Generation** — Generates factual, cited answers using retrieved context via a **local Ollama** model (no OpenAI required)

## Tech Stack

| Component | Technology |
|---|---|
| Backend | Python 3.14 + FastAPI |
| Frontend | React + Vite |
| Embeddings | sentence-transformers (multilingual) |
| Vector Store | FAISS |
| Database | SQLite |
| Custom Model | scikit-learn (TF-IDF + LogReg/SVM) |
| LLM | Ollama (local) — default `qwen2.5:7b` |

## Quick Start (Windows + Python 3.14 + PowerShell)

```powershell
# 1. Create & activate a virtual environment
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install backend deps
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3. Copy env file
Copy-Item .env.example .env

# 4. Start Ollama (in a separate terminal) and pull the model
ollama serve
ollama pull qwen2.5:7b

# 5. Train the safety classifier (one time)
python training/scripts/train.py

# 6. Ingest knowledge documents
python scripts/ingest.py

# 7. Run the backend
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

# 8. In a second terminal — run the frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

## Project Structure

```
Boloroo/
├── backend/          # FastAPI application
├── frontend/         # React chat interface
├── rag/              # RAG pipeline modules
├── training/         # Custom classifier training code + data
├── data/             # Source documents + SQLite DB + FAISS index
├── scripts/          # Ingestion and evaluation scripts
└── docs/             # Thesis notes
```

## License

Developed as a bachelor thesis project.
