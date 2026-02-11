"""FastAPI application with async endpoints."""
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import List, Optional
import logging
import aiofiles
import json
import re

from app.config import settings
from app.database import db
from app.embedding_service import embedding_service
from app.llm_service import llm_service
from app.conversation_memory import conversation_memory
from app.repository_service import repository_service
from app.document_service import document_service
from app.rag_service import rag_service
from app.models import (
    RepositoryCreate,
    RepositoryUpdate,
    RepositoryResponse,
    DocumentResponse,
    BulkDocumentUploadResponse,
    SearchRequest,
    SearchResponse,
    HealthResponse
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more verbose logging
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting application...")
    
    try:
        await db.connect()
        await embedding_service.initialize()
        await llm_service.initialize()
        await conversation_memory.initialize()
        logger.info("All services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await db.disconnect()
    await conversation_memory.close()


# Create FastAPI app
app = FastAPI(
    title="Agentic RAG API",
    description="Production-grade RAG API with vector and web search",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check health of all services."""
    db_healthy = db.pool is not None
    embedding_healthy = await embedding_service.health_check()
    llm_healthy = await llm_service.health_check()
    
    status = "healthy" if all([db_healthy, embedding_healthy, llm_healthy]) else "unhealthy"
    
    return HealthResponse(
        status=status,
        database="healthy" if db_healthy else "unhealthy",
        embedding_service="healthy" if embedding_healthy else "unhealthy",
        llm_service="healthy" if llm_healthy else "unhealthy"
    )


# Repository endpoints
@app.post("/repositories", response_model=RepositoryResponse, status_code=201)
async def create_repository(repository: RepositoryCreate):
    """Create a new repository."""
    try:
        return await repository_service.create_repository(repository)
    except Exception as e:
        logger.error(f"Error creating repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/repositories", response_model=List[RepositoryResponse])
async def list_repositories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """List all repositories."""
    try:
        return await repository_service.list_repositories(skip, limit)
    except Exception as e:
        logger.error(f"Error listing repositories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/repositories/{repository_id}", response_model=RepositoryResponse)
async def get_repository(repository_id: int):
    """Get repository by ID."""
    try:
        repository = await repository_service.get_repository(repository_id)
        if not repository:
            raise HTTPException(status_code=404, detail="Repository not found")
        return repository
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/repositories/{repository_id}", response_model=RepositoryResponse)
async def update_repository(repository_id: int, repository: RepositoryUpdate):
    """Update repository."""
    try:
        updated = await repository_service.update_repository(repository_id, repository)
        if not updated:
            raise HTTPException(status_code=404, detail="Repository not found")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/repositories/{repository_id}", status_code=204)
async def delete_repository(repository_id: int):
    """Delete repository."""
    try:
        deleted = await repository_service.delete_repository(repository_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Repository not found")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Document endpoints
@app.post("/documents", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    repository_id: Optional[int] = Query(None)
):
    """Upload and process a document."""
    try:
        # Read file content
        content = await file.read()
        
        # Create and process document
        document = await document_service.create_document(
            name=file.filename,
            file_content=content,
            content_type=file.content_type,
            repository_id=repository_id
        )
        
        return document
        
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/documents/bulk", response_model=BulkDocumentUploadResponse, status_code=201)
async def upload_documents_bulk(
    files: List[UploadFile] = File(...),
    repository_id: Optional[int] = Query(None)
):
    """
    Upload and process multiple documents at once.

    This endpoint accepts multiple files and processes them in parallel.
    Returns a summary of successful and failed uploads.
    """
    try:
        # Read all file contents
        file_data = []
        for file in files:
            content = await file.read()
            file_data.append({
                "name": file.filename,
                "content": content,
                "content_type": file.content_type
            })

        # Process all documents
        result = await document_service.create_documents_bulk(
            files=file_data,
            repository_id=repository_id
        )

        return result

    except Exception as e:
        logger.error(f"Error in bulk document upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents", response_model=List[DocumentResponse])
async def list_documents(
    repository_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """List documents, optionally filtered by repository."""
    try:
        return await document_service.list_documents(repository_id, skip, limit)
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: int):
    """Get document by ID."""
    try:
        document = await document_service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        return document
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/documents/{document_id}", status_code=204)
async def delete_document(document_id: int):
    """Delete document."""
    try:
        deleted = await document_service.delete_document(document_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Document not found")
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Search endpoint
@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Perform agentic RAG search with conversation memory.

    Searches against vector database and/or web, then generates
    an answer using LLM with conversation context.
    """
    try:
        response = await rag_service.search_and_generate(request)
        return response
    except Exception as e:
        logger.error(f"Error in search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Debug endpoint - get chunk info
@app.get("/debug/chunks")
async def debug_chunks(repository_id: Optional[int] = None):
    """Debug endpoint to check chunks in database."""
    try:
        async with db.acquire() as conn:
            if repository_id:
                rows = await conn.fetch(
                    """
                    SELECT
                        c.id,
                        c.document_id,
                        d.name as document_name,
                        c.chunk_index,
                        LENGTH(c.content) as content_length,
                        CASE WHEN c.embedding IS NULL THEN 0 ELSE 1 END as has_embedding,
                        vector_dims(c.embedding) as embedding_dim
                    FROM chunks c
                    JOIN documents d ON c.document_id = d.id
                    WHERE d.repository_id = $1
                    ORDER BY c.document_id, c.chunk_index
                    LIMIT 10
                    """,
                    repository_id
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT
                        c.id,
                        c.document_id,
                        d.name as document_name,
                        c.chunk_index,
                        LENGTH(c.content) as content_length,
                        CASE WHEN c.embedding IS NULL THEN 0 ELSE 1 END as has_embedding,
                        vector_dims(c.embedding) as embedding_dim
                    FROM chunks c
                    JOIN documents d ON c.document_id = d.id
                    ORDER BY c.document_id, c.chunk_index
                    LIMIT 10
                    """
                )

            return {
                "repository_id": repository_id,
                "chunks_found": len(rows) if rows else 0,
                "chunks": [
                    {
                        "id": row["id"],
                        "document_id": row["document_id"],
                        "document_name": row["document_name"],
                        "chunk_index": row["chunk_index"],
                        "content_length": row["content_length"],
                        "has_embedding": bool(row["has_embedding"]),
                        "embedding_dim": row["embedding_dim"]
                    }
                    for row in (rows or [])
                ]
            }
    except Exception as e:
        logger.error(f"Debug endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Debug endpoint - reprocess all embeddings with normalization
@app.post("/debug/reprocess-embeddings")
async def reprocess_embeddings():
    """Reprocess all document embeddings with L2 normalization and fixed text cleaning."""
    try:
        from app.embedding_service import embedding_service
        from app.document_processor import document_processor
        import numpy as np

        async with db.acquire() as conn:
            # Get all documents with their file paths
            docs = await conn.fetch(
                """
                SELECT d.id, d.name, d.file_path, d.repository_id
                FROM documents d
                WHERE d.status = 'completed'
                ORDER BY d.id
                """
            )

            results = []
            for doc in docs:
                try:
                    doc_id = doc['id']
                    file_path = doc['file_path']

                    # Read file content
                    from pathlib import Path
                    if not Path(file_path).exists():
                        results.append({"id": doc_id, "name": doc['name'], "status": "file_not_found"})
                        continue

                    async with aiofiles.open(file_path, 'rb') as f:
                        file_content = await f.read()

                    # Determine format
                    file_format = Path(file_path).suffix.lower().replace('.', '')
                    format_map = {
                        '.pdf': 'pdf',
                        '.txt': 'txt',
                        '.md': 'md',
                        '.docx': 'docx',
                        '.html': 'html'
                    }
                    doc_format = format_map.get('.' + file_format, 'txt')

                    # Process document (with fixed text cleaning)
                    text = await document_processor.process_document(
                        file_content,
                        doc['name'],
                        doc_format
                    )

                    # Chunk text with document name for metadata enrichment
                    chunks = document_processor.chunk_text(text, document_name=doc['name'])

                    # Generate normalized embeddings
                    chunk_texts = [chunk[0] for chunk in chunks]
                    embeddings = await embedding_service.embed_documents(chunk_texts)

                    # Delete old chunks
                    await conn.execute("DELETE FROM chunks WHERE document_id = $1", doc_id)

                    # Store new chunks with normalized embeddings
                    for (chunk_text, chunk_index), embedding in zip(chunks, embeddings):
                        # L2 normalize
                        if hasattr(embedding, 'tolist'):
                            emb_array = np.array(embedding)
                        else:
                            emb_array = np.array(embedding)
                        norm = np.linalg.norm(emb_array)
                        if norm > 0:
                            emb_array = emb_array / norm

                        vector_str = '[' + ','.join(str(x) for x in emb_array.tolist()) + ']'

                        await conn.execute(
                            f"""
                            INSERT INTO chunks (document_id, content, chunk_index, embedding, metadata)
                            VALUES ($1, $2, $3, '{vector_str}'::vector, $4)
                            """,
                            doc_id,
                            chunk_text,
                            chunk_index,
                            json.dumps({"length": len(chunk_text)})
                        )

                    results.append({"id": doc_id, "name": doc['name'], "status": "reprocessed", "chunks": len(chunks)})

                except Exception as e:
                    logger.error(f"Error reprocessing document {doc['id']}: {e}")
                    results.append({"id": doc_id, "name": doc['name'], "status": "error", "error": str(e)})

            return {
                "success": True,
                "total_documents": len(docs),
                "results": results
            }
    except Exception as e:
        logger.error(f"Reprocess embeddings error: {e}", exc_info=True)
        return {
            "error": str(e)
        }


# Debug endpoint - check pgvector version
@app.get("/debug/pgvector-version")
async def debug_pgvector_version():
    """Debug endpoint to check pgvector version and available functions."""
    try:
        async with db.acquire() as conn:
            # Get pgvector version
            version = await conn.fetchval(
                "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
            )

            # Check available functions
            functions = await conn.fetch(
                """
                SELECT routine_name
                FROM information_schema.routines
                WHERE routine_schema = 'public'
                AND routine_name LIKE '%vector%'
                ORDER BY routine_name
                """
            )

            # Check vector type
            type_info = await conn.fetchrow(
                """
                SELECT typname, typlen
                FROM pg_type
                WHERE typname = 'vector'
                """
            )

            return {
                "pgvector_version": version,
                "vector_type": {
                    "name": type_info["typname"] if type_info else None,
                    "length": type_info["typlen"] if type_info else None
                } if type_info else None,
                "available_vector_functions": [row["routine_name"] for row in (functions or [])]
            }
    except Exception as e:
        logger.error(f"Debug pgvector version error: {e}", exc_info=True)
        return {
            "error": str(e)
        }


# Debug endpoint - test vector search
@app.get("/debug/vector-search")
async def debug_vector_search(repository_id: int, query: str = "test", top_k: int = 50):
    """Debug endpoint to test vector search directly."""
    try:
        from app.embedding_service import embedding_service

        # Generate query embedding
        query_embedding = await embedding_service.embed_query(query)

        # Convert to list
        if hasattr(query_embedding, 'tolist'):
            embedding_list = query_embedding.tolist()
        else:
            embedding_list = list(query_embedding)

        vector_str = '[' + ','.join(str(x) for x in embedding_list) + ']'

        async with db.acquire() as conn:
            # Get ALL chunks with their distances
            all_chunks = await conn.fetch(
                f"""
                SELECT
                    c.id,
                    c.content,
                    d.name as document_name,
                    c.embedding <=> '{vector_str}'::vector as distance,
                    1 - (c.embedding <=> '{vector_str}'::vector) as similarity
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE d.repository_id = $1
                AND c.embedding IS NOT NULL
                ORDER BY c.embedding <=> '{vector_str}'::vector
                """,
                repository_id
            )

            # Group by document
            from collections import defaultdict
            docs_by_name = defaultdict(list)
            for chunk in all_chunks:
                docs_by_name[chunk['document_name']].append({
                    'id': chunk['id'],
                    'distance': float(chunk['distance']),
                    'similarity': float(chunk['similarity']),
                    'content_preview': chunk['content'][:100]
                })

            return {
                "query": query,
                "query_embedding_dim": len(embedding_list),
                "total_chunks": len(all_chunks),
                "unique_documents": len(docs_by_name),
                "documents": {
                    name: {
                        'chunk_count': len(chunks),
                        'best_distance': min(c['distance'] for c in chunks),
                        'best_similarity': max(c['similarity'] for c in chunks),
                        'chunks': chunks[:3]  # First 3 chunks for preview
                    }
                    for name, chunks in docs_by_name.items()
                }
            }
    except Exception as e:
        logger.error(f"Debug vector search error: {e}", exc_info=True)
        return {
            "error": str(e),
            "query": query,
            "repository_id": repository_id
        }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Agentic RAG API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
