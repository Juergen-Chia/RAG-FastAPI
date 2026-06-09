# RAG API

A production-grade Retrieval-Augmented Generation (RAG) API built with FastAPI, featuring hybrid vector + keyword search, multi-format document processing, and Redis-backed conversation memory.

## Features

- **Document Processing**: Upload and process PDF, TXT, MD, DOCX, and HTML files
- **Vector Search**: Semantic similarity search using pgvector and local sentence-transformers embeddings (BAAI/bge-large-en-v1.5, 1024-dim)
- **Keyword Search**: Full-text search using PostgreSQL GIN indexes
- **Hybrid Search**: Combines vector and keyword search for optimal results
- **Conversation Memory**: Maintains chat context using Redis-backed storage (7-day TTL)
- **LLM Integration**: Ali Cloud DashScope Qwen models via OpenAI-compatible API
- **Bulk Upload**: Upload multiple documents in parallel
- **Web UI**: Streamlit-based interface for easy interaction

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Streamlit     │────▶│    FastAPI      │────▶│   PostgreSQL    │
│     Frontend    │     │     Backend     │     │   + pgvector    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │  Embedding      │     │      Redis      │
                        │  DashScope      │     │  Conversation   │
                        └─────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │   LLM Service   │
                        │  (Qwen / Any    │
                        │  OpenAI-compat) │
                        └─────────────────┘
```

## Prerequisites

- Docker Desktop (for PostgreSQL + Redis)
- Python 3.11+
- Ali Cloud DashScope API key (for LLM only — embeddings now run locally)
- SerpAPI key (optional — web search is currently disabled)

## Quick Start

### 1. Start Infrastructure

From the project root:

```bash
docker compose up -d
```

This starts:
- PostgreSQL 16 with pgvector on port `5432`
- Redis 7 on port `6379`

Verify both are healthy:

```bash
docker compose ps
```

### 2. Configure Environment

Create `source/.env`:

```env
# Required
OPENAI_API_KEY=your_dashscope_api_key_here
SERPAPI_API_KEY=your_serpapi_key_here
API_KEY=your_secret_api_key_here

# LLM (Ali Cloud DashScope — Qwen models)
OPENAI_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-plus

# Embeddings (local model — downloads ~1.3 GB from HuggingFace on first run)
EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
EMBEDDING_DIMENSION=1024

# Database (matches docker-compose.yml defaults — no changes needed)
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=rag_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis (matches docker-compose.yml defaults — no changes needed)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Chunking
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
MAX_CONVERSATION_HISTORY=10
```

> `OPENAI_API_KEY`, `SERPAPI_API_KEY`, and `API_KEY` are required — the app will not start without them.

### 3. Install Dependencies

```bash
cd source
pip install -r requirements.txt
```

### 4. Run the Application

**FastAPI backend** (from `source/`):

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The schema (`repositories`, `documents`, `chunks`, indexes) is created automatically on first startup.

**Streamlit frontend** (separate terminal, from `source/`):

```bash
streamlit run streamlit_app.py --server.port 8501
```

### 5. Access the Application

| Service | URL |
|---------|-----|
| API Documentation | http://localhost:8000/docs |
| Streamlit UI | http://localhost:8501 |
| Health Check | http://localhost:8000/health |

## API Endpoints

### Repositories

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/repositories` | Create a new repository |
| GET | `/repositories` | List all repositories |
| GET | `/repositories/{id}` | Get repository by ID |
| PUT | `/repositories/{id}` | Update repository |
| DELETE | `/repositories/{id}` | Delete repository |

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/documents` | Upload a single document |
| POST | `/documents/bulk` | Upload multiple documents |
| GET | `/documents` | List documents |
| GET | `/documents/{id}` | Get document by ID |
| DELETE | `/documents/{id}` | Delete document |

### Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/search` | Perform RAG search with LLM answer |

### Health & Debug

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Check service health |
| GET | `/debug/chunks` | View stored chunks |
| GET | `/debug/vector-search` | Test vector similarity |
| GET | `/debug/pgvector-version` | Check pgvector version |
| POST | `/debug/reprocess-embeddings` | Reprocess all embeddings |

## Authentication

All endpoints require an `X-API-Key` header. Set `API_KEY` in `source/.env` and pass it with every request.

| Response | Meaning |
|----------|---------|
| `401 Unauthorized` | Header missing |
| `403 Forbidden` | Key is wrong |

The Swagger UI at `http://localhost:8000/docs` has an **Authorize** button (lock icon) where you can enter the key once for all requests in that session.

## Usage Examples

### Upload Documents via API

```bash
# Single document
curl -X POST "http://localhost:8000/documents" \
  -H "X-API-Key: your_secret_api_key_here" \
  -F "file=@document.pdf"

# Bulk upload
curl -X POST "http://localhost:8000/documents/bulk" \
  -H "X-API-Key: your_secret_api_key_here" \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.pdf"
```

### Search Query

```bash
curl -X POST "http://localhost:8000/search" \
  -H "X-API-Key: your_secret_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the main topic?",
    "source": "vector",
    "top_k": 5,
    "use_conversation_memory": true
  }'
```

### Python Client

```python
import requests

HEADERS = {"X-API-Key": "your_secret_api_key_here"}

# Upload document
with open("document.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/documents",
        headers=HEADERS,
        files={"file": f}
    )
    print(response.json())

# Search
response = requests.post(
    "http://localhost:8000/search",
    headers=HEADERS,
    json={
        "query": "Summarize the document",
        "source": "vector",
        "top_k": 5
    }
)
print(response.json()["answer"])
```

## Configuration

### Chunking

- **Chunk Size**: 1000 characters (configurable via `CHUNK_SIZE`)
- **Chunk Overlap**: 200 characters (configurable via `CHUNK_OVERLAP`)

### Embedding Model

Default: `BAAI/bge-large-en-v1.5` via local sentence-transformers (1024 dimensions, ~1.3 GB, downloaded from HuggingFace on first run and cached at `~/.cache/huggingface`).

To use a different model, update `EMBEDDING_MODEL` and `EMBEDDING_DIMENSION` in `.env`. If you change dimensions, drop and recreate the `chunks` table (or run `POST /debug/reprocess-embeddings`).

### LLM Provider

Any OpenAI-compatible endpoint. Configure via `OPENAI_BASE_URL`, `OPENAI_MODEL`, and `OPENAI_API_KEY` in `.env`.

## Project Structure

```
RAG-FastAPI/
├── docker-compose.yml          # PostgreSQL 16 + pgvector, Redis 7
├── README.md
└── source/
    ├── app/
    │   ├── main.py             # FastAPI application + endpoints
    │   ├── config.py           # Pydantic settings (reads .env)
    │   ├── database.py         # Connection pool + schema init
    │   ├── models.py           # Pydantic request/response schemas
    │   ├── rag_service.py      # Hybrid search + LLM orchestration
    │   ├── embedding_service.py   # DashScope embeddings (batch=10)
    │   ├── llm_service.py         # LLM completion + conversation history
    │   ├── document_service.py    # Document upload + chunking pipeline
    │   ├── document_processor.py  # PDF/TXT/MD/DOCX/HTML extraction
    │   ├── repository_service.py  # Repository CRUD
    │   ├── conversation_memory.py # Redis conversation storage
    │   └── web_search_service.py  # SerpAPI (disabled)
    ├── migrations/
    │   └── 002_add_rbac.sql    # Optional RBAC schema (not applied)
    ├── streamlit_app.py        # Web UI
    ├── verify_setup.py         # Infrastructure connectivity check
    ├── requirements.txt
    └── uploads/                # Uploaded document storage
```

## Troubleshooting

**Docker containers conflict on startup**
```bash
docker compose down -v
docker compose up -d
```

**Database connection error**
- Verify containers are running and healthy: `docker compose ps`
- Check `POSTGRES_*` values in `source/.env`

**pgAdmin connection refused / password error**
- Run `docker compose down -v && docker compose up -d` to reset the volume with correct credentials
- Connect with: host `localhost`, port `5432`, user `postgres`, password `password`

**Embedding dimension mismatch**
- Verify `EMBEDDING_DIMENSION` in `.env` matches your model (default: `1024` for text-embedding-v4)
- Reprocess: `POST /debug/reprocess-embeddings`

**LLM API errors**
- Verify `OPENAI_API_KEY` is a valid DashScope key
- Verify `OPENAI_BASE_URL` is reachable from your machine

**App won't start — validation error**
- `OPENAI_API_KEY` and `SERPAPI_API_KEY` have no defaults and must be present in `source/.env`
