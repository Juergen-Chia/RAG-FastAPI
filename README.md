# RAG API

A production-grade Retrieval-Augmented Generation (RAG) API built with FastAPI, featuring vector similarity search, document processing, and conversation memory.

## Features

- **Document Processing**: Upload and process PDF, TXT, MD, DOCX, and HTML files
- **Vector Search**: Semantic similarity search using pgvector and sentence-transformers embeddings
- **Keyword Search**: Full-text search using PostgreSQL GIN indexes
- **Hybrid Search**: Combines vector and keyword search for optimal results
- **Conversation Memory**: Maintains chat context using Redis-backed storage
- **LLM Integration**: OpenAI-compatible API support for answer generation
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
                        │    Service      │     │ Conversation    │
                        └─────────────────┘     └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │   LLM Service   │
                        │  (OpenAI API)   │
                        └─────────────────┘
```

## Prerequisites

- Docker and Docker Compose
- Python 3.11+
- OpenAI API key (or compatible endpoint)

## Quick Start

### 1. Clone and Setup

```bash
cd RAG-FastAPI-v02
```

### 2. Start Infrastructure

```bash
docker-compose up -d
```

This starts:
- PostgreSQL 16 with pgvector on port 5432
- Redis 7 on port 6379

### 3. Configure Environment

Copy `.env.example` to `source/.env` and update:

```bash
cp .env.example source/.env
```

Edit `source/.env` with your values:

```env
# LLM (Ali Cloud Qwen model)
OPENAI_MODEL=qwen3-max-preview

# Embeddings (Ali Cloud text embedding model)
EMBEDDING_MODEL=text-embedding-v4

# Optional: Web Search (SerpAPI)
SERPAPI_API_KEY=your_serpapi_key_here
```

### 4. Install Dependencies

```bash
cd source
pip install -r requirements.txt
```

### 5. Run the Application

**Start FastAPI Backend:**

```bash
# Windows
start.bat

# Linux/Mac
./start.sh

# Or manually:
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Start Streamlit Frontend (separate terminal):**

```bash
cd source
streamlit run streamlit_app.py --server.port 8501
```

### 6. Access the Application

- **API Documentation**: http://localhost:8000/docs
- **Streamlit UI**: http://localhost:8501
- **Health Check**: http://localhost:8000/health

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
| POST | `/search` | Perform RAG search with LLM |

### Health & Debug

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Check service health |
| GET | `/debug/chunks` | View chunk information |
| GET | `/debug/vector-search` | Test vector search |
| POST | `/debug/reprocess-embeddings` | Reprocess document embeddings |

## Usage Examples

### Upload Documents via API

```bash
# Single document
curl -X POST "http://localhost:8000/documents" \
  -F "file=@document.pdf"

# Bulk upload
curl -X POST "http://localhost:8000/documents/bulk" \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.pdf"
```

### Search Query

```bash
curl -X POST "http://localhost:8000/search" \
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

# Upload document
with open("document.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/documents",
        files={"file": f}
    )
    print(response.json())

# Search
response = requests.post(
    "http://localhost:8000/search",
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

Default: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)

To use a different model, update `EMBEDDING_MODEL` and `EMBEDDING_DIMENSION` in `.env`.

### LLM Provider

The API supports any OpenAI-compatible endpoint. Configure via:

```env
# LLM (Ali Cloud Qwen model)
OPENAI_MODEL=qwen3-max-preview

# Embeddings (Ali Cloud text embedding model)
EMBEDDING_MODEL=text-embedding-v4

# Optional: Web Search (SerpAPI)
SERPAPI_API_KEY=your_serpapi_key_here
```

## Project Structure

```
RAG-FastAPI-v02/
├── docker-compose.yml          # Infrastructure services
├── requirements.txt            # Python dependencies
├── source/
│   ├── app/
│   │   ├── main.py            # FastAPI application
│   │   ├── config.py          # Configuration settings
│   │   ├── database.py        # Database connection
│   │   ├── models.py          # Pydantic models
│   │   ├── rag_service.py     # RAG orchestration
│   │   ├── embedding_service.py  # Vector embeddings
│   │   ├── llm_service.py     # LLM integration
│   │   ├── document_service.py    # Document CRUD
│   │   ├── document_processor.py  # Text extraction
│   │   ├── repository_service.py  # Repository CRUD
│   │   ├── conversation_memory.py # Chat history
│   │   └── web_search_service.py  # Web search (optional)
│   ├── streamlit_app.py       # Web UI
│   ├── .env                   # Environment variables
│   ├── requirements.txt       # Source dependencies
│   └── uploads/               # Uploaded documents
└── README.md
```

## Development

### Database Migrations

SQL migrations are located in `source/migrations/`.

### Debugging

Use the debug endpoints to inspect:
- `/debug/chunks` - View stored chunks and embeddings
- `/debug/vector-search` - Test vector similarity
- `/debug/pgvector-version` - Check pgvector installation

## Troubleshooting

**Database connection error**
- Ensure Docker containers are running: `docker-compose ps`
- Check DATABASE_URL in `.env`

**Embedding dimension mismatch**
- Verify `EMBEDDING_DIMENSION` matches your model
- Reprocess embeddings: `POST /debug/reprocess-embeddings`

**LLM API errors**
- Check OPENAI_API_KEY is valid
- Verify OPENAI_BASE_URL is accessible

## License

MIT License
