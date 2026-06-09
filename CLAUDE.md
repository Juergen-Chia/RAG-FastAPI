# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**Agentic RAG Application v2.0.0** — A FastAPI-based Retrieval-Augmented Generation system using PostgreSQL+pgvector for hybrid vector/keyword search, Redis for conversation memory, local sentence-transformers for embeddings (`BAAI/bge-large-en-v1.5`, 1024-dim), and Ali Cloud DashScope for LLM (Qwen models via OpenAI-compatible API).

---

## Commands

All commands are run from the `source/` directory.

### Setup

```powershell
cd source
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### GPU acceleration (NVIDIA — recommended)

`sentence-transformers` pulls CPU-only PyTorch by default. For CUDA (RTX 4050 / any NVIDIA GPU), install CUDA-enabled PyTorch **before** `requirements.txt`:

```powershell
# Install CUDA 12.1 PyTorch first (works for RTX 40-series / Ada Lovelace)
pip install torch --index-url https://download.pytorch.org/whl/cu121
# Then install the rest
pip install -r requirements.txt
```

The embedding service auto-detects CUDA at startup and logs the device name. No code changes needed — it falls back to CPU automatically if CUDA is unavailable.

### Run FastAPI server

```powershell
cd source
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Or via module:

```powershell
python -m app.main
```

### Run Streamlit UI (separate terminal)

```powershell
cd source
streamlit run streamlit_app.py --server.port 8501
```

### Verify infrastructure

```powershell
cd source
python verify_setup.py
```

### Run tests

```powershell
cd source
pytest
pytest tests/test_specific.py::test_name -v
pytest --cov=app
```

### Windows combined startup (requires Docker — skip infra step if running locally)

```bat
source\start.bat
```

---

## Architecture

```
Streamlit UI (8501)
      │
FastAPI (8000)       source/app/main.py
      │
      ├── EmbeddingService      embedding_service.py   — local sentence-transformers BAAI/bge-large-en-v1.5 (1024-dim)
      ├── LLMService            llm_service.py          — Qwen via OpenAI-compatible API
      ├── RAGService            rag_service.py          — hybrid search + LLM orchestration
      ├── DocumentService       document_service.py     — upload, chunk, embed, store
      ├── DocumentProcessor     document_processor.py   — PDF/TXT/MD/DOCX/HTML extraction
      ├── RepositoryService     repository_service.py   — repository CRUD
      ├── ConversationMemory    conversation_memory.py  — Redis-backed chat history (7-day TTL)
      └── WebSearchService      web_search_service.py   — SerpAPI (DISABLED, not wired in)

Infrastructure:
  PostgreSQL 16 + pgvector   — documents, chunks, vector index (IVFFlat, cosine)
  Redis 7                    — conversation history storage
```

### Data flow for `/search`

1. Query → `EmbeddingService.embed_query()` → L2-normalized 1024-dim vector (via local sentence-transformers)
2. `RAGService.hybrid_search()`:
   - Vector search via pgvector `<=>` cosine distance (fetches K×5, returns K)
   - Keyword search via PostgreSQL full-text (`GIN` index, `plainto_tsquery`)
   - Deduplicate by `hash(content[:200])` + boost keyword matches ×1.2
3. Top results → `LLMService.generate_answer()` → structured JSON or plain-text fallback
4. Answer + conversation turn stored in Redis

### Database schema (`database.py`)

- `repositories`: id, name (UNIQUE), description, timestamps
- `documents`: id, name, format, status, file_path, timestamps
- `chunks`: id, document_id, content, chunk_index, `embedding vector(1024)`, metadata JSONB, created_at

Schema is auto-initialized on startup (`Database.init_schema()`). pgvector extension must already exist.

### Key design decisions

- **L2 normalization**: All embeddings normalized before storage and at query time — enables cosine similarity via inner product.
- **Repository filtering is disabled**: `rag_service.py` silently ignores `repository_id` on search — all chunks are searched globally ("SIMPLIFIED" per code comment).
- **Batch embedding**: Ali Cloud DashScope API limit is 10 texts per request — `embedding_service.py` batches accordingly.
- **Conversation memory fallback**: If Redis is unavailable, `ConversationMemory` falls back to in-memory (conversations lost on restart).

---

## Configuration

All settings in `source/app/config.py` (Pydantic BaseSettings). Create `source/.env`:

```env
# Required — no defaults
OPENAI_API_KEY=<dashscope-api-key>
SERPAPI_API_KEY=<serpapi-key>

# Database (defaults match local install)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=rag_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# LLM (Ali Cloud DashScope)
OPENAI_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-plus

# Embeddings (local model — no API key needed; downloads ~1.3 GB on first run)
EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
EMBEDDING_DIMENSION=1024

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Chunking
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_CONVERSATION_HISTORY=10
```

`OPENAI_API_KEY` and `SERPAPI_API_KEY` are required (`Field(...)`) — the app crashes at import time if they are missing.

---

## Infrastructure Setup

### Start with Docker Compose (recommended)

`docker-compose.yml` at the project root starts PostgreSQL 16 + pgvector and Redis 7 with the exact credentials the app's defaults expect — no extra configuration needed.

```powershell
# From project root: D:\00-CODES\RAG-FastAPI\RAG-FastAPI\
docker compose up -d        # start in background
docker compose down         # stop
docker compose down -v      # stop + wipe all data (clean slate)
```

The app calls `Database.init_schema()` on startup — all tables, indexes, triggers, and the `vector` extension are created automatically. No manual SQL required.

**Credential alignment** (docker-compose ↔ config.py defaults — no `.env` overrides needed for infra):

| | docker-compose.yml | config.py default |
|-|--------------------|--------------------|
| PG host:port | `localhost:5432` | `localhost:5432` |
| PG user/pass/db | `postgres` / `password` / `rag_db` | same |
| Redis | `localhost:6379` | `localhost:6379` |

### Verify containers are healthy

```powershell
docker compose ps          # both services should show "healthy"
docker exec rag_postgres psql -U postgres -d rag_db -c "SELECT extversion FROM pg_extension WHERE extname='vector';"
docker exec rag_redis redis-cli ping   # expects PONG
```

---

## Known Issues & Bugs

These are confirmed issues in the current codebase that will cause failures or security problems:

### Critical (fixed)

| # | File | Fix applied |
|---|------|-------------|
| 1 | `database.py` | Added `repository_id INTEGER REFERENCES repositories(id) ON DELETE SET NULL` to `documents` table. |
| 2 | `rag_service.py`, `document_service.py`, `main.py` | Replaced vector f-string interpolation with parameterized `$N::vector` in all INSERT and SELECT queries. |
| 4 | `__init__.py` / `main.py` | Unified version to `2.0.0` in FastAPI app constructor and root endpoint. |

### Critical (open)

| # | File | Issue |
|---|------|-------|
| 3 | `main.py` | Debug endpoints (`/debug/*`) are public with no authentication — they expose raw chunk content and trigger full embedding reprocessing. |

### High Priority

| # | File | Issue |
|---|------|-------|
| 5 | `main.py` line ~73 | CORS `allow_origins=["*"]` — restrict before any production deployment. |
| 6 | `models.py` | `SearchSource.WEB` and `SearchSource.BOTH` are defined but web search is disabled; the API contract is misleading. |
| 7 | Entire API | No authentication or authorization on any endpoint. |

### Medium Priority

| # | File | Issue |
|---|------|-------|
| 8 | `document_service.py` | No file size validation — large uploads can exhaust memory during processing. |
| 9 | `llm_service.py` | `temperature=0.7` and `max_tokens=1000` are hardcoded; no request timeout. |
| 10 | `document_processor.py` | Sentence splitting uses a simple `.!?` regex — fails on abbreviations like "Dr. Smith". |
| 11 | `document_service.py` line 22 | Upload path is relative (`uploads/`) — fragile if working directory changes. |
| 12 | `conversation_memory.py` | Redis fallback to in-memory is silent — users expect persistence but lose history on restart. |
| 13 | `streamlit_app.py` | Large blocks of commented-out code — should be cleaned up. |

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | API info |
| GET | `/health` | Service health (DB, embeddings, LLM) |
| POST | `/repositories` | Create repository |
| GET/PUT/DELETE | `/repositories/{id}` | Repository CRUD |
| POST | `/documents` | Upload single document |
| POST | `/documents/bulk` | Bulk upload |
| GET/DELETE | `/documents/{id}` | Document CRUD |
| POST | `/search` | RAG search + LLM answer |
| GET | `/debug/chunks` | View stored chunks (public, no auth) |
| GET | `/debug/pgvector-version` | pgvector version info |
| GET | `/debug/vector-search` | Test vector similarity |
| POST | `/debug/reprocess-embeddings` | Reprocess all embeddings |

Interactive docs: `http://localhost:8000/docs`
