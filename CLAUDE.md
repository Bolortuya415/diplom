# Boloroo Project — Claude Code Instructions

## Project Overview
Mongolian RAG chatbot for gender equality and social inclusion (bachelor thesis).

## Architecture
- Backend: FastAPI (backend/app/)
- Frontend: React + Vite (frontend/)
- RAG: FAISS + sentence-transformers (rag/)
- Custom Model: Sensitive content classifier (training/)
- Database: SQLite (data/boloroo.db)

## Conventions
- Python code uses type hints
- Backend follows service pattern: api/ → services/ → db/
- All Mongolian text uses UTF-8 Cyrillic
- Environment variables in .env (never committed)
- Custom model artifacts saved to training/models/

## Key Commands
- Backend: `cd backend && uvicorn app.main:app --reload`
- Frontend: `cd frontend && npm run dev`
- Train classifier: `python training/scripts/train.py`
- Ingest documents: `python scripts/ingest.py`
- Run tests: `pytest tests/`
- Docker: `docker-compose up`
