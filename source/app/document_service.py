"""Document service for managing uploads and processing."""
from typing import List, Optional, Dict, Any
import logging
from pathlib import Path
import aiofiles
import json
from datetime import datetime

from app.database import db
from app.document_processor import document_processor
from app.embedding_service import embedding_service
from app.models import DocumentResponse, DocumentStatus, DocumentFormat

logger = logging.getLogger(__name__)


class DocumentService:
    """Service for managing documents."""
    
    def __init__(self):
        # Use relative path that works on both Windows and Linux
        self.upload_dir = Path("uploads")
        self.upload_dir.mkdir(exist_ok=True)
    
    async def create_document(
        self,
        name: str,
        file_content: bytes,
        content_type: str,
        repository_id: Optional[int] = None
    ) -> DocumentResponse:
        """Create and process a new document."""
        try:
            # Determine format from filename
            file_format = self._get_format_from_filename(name)
            
            # Save file
            file_path = self.upload_dir / f"{name}"
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_content)
            
            # Create document record
            async with db.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO documents (name, format, status, repository_id, file_path)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id, name, format, status, repository_id, created_at, updated_at
                    """,
                    name,
                    file_format,
                    DocumentStatus.PENDING.value,
                    repository_id,
                    str(file_path)
                )
                
                document_id = row['id']
                logger.info(f"Created document: {document_id}")
                
                # Process document asynchronously
                await self._process_document(document_id, file_content, name, file_format)
                
                # Get updated document
                return await self.get_document(document_id)
                
        except Exception as e:
            logger.error(f"Error creating document: {e}")
            raise
    
    async def _process_document(
        self,
        document_id: int,
        file_content: bytes,
        file_name: str,
        file_format: str
    ) -> None:
        """Process document and create embeddings."""
        try:
            # Update status to processing
            async with db.acquire() as conn:
                await conn.execute(
                    "UPDATE documents SET status = $1 WHERE id = $2",
                    DocumentStatus.PROCESSING.value,
                    document_id
                )
            
            # Extract text
            text = await document_processor.process_document(
                file_content,
                file_name,
                file_format
            )
            
            # Chunk text with document name for metadata enrichment
            chunks = document_processor.chunk_text(text, document_name=file_name)
            
            # Generate embeddings for all chunks
            chunk_texts = [chunk[0] for chunk in chunks]
            embeddings = await embedding_service.embed_documents(chunk_texts)

            # Normalize embeddings to unit length (L2 normalization)
            # This ensures cosine distance is between 0 and 2
            import numpy as np
            normalized_embeddings = []
            for emb in embeddings:
                if hasattr(emb, 'tolist'):
                    emb_array = np.array(emb)
                else:
                    emb_array = np.array(emb)
                # L2 normalize
                norm = np.linalg.norm(emb_array)
                if norm > 0:
                    emb_array = emb_array / norm
                normalized_embeddings.append(emb_array.tolist())

            # Store chunks with embeddings
            async with db.acquire() as conn:
                for (chunk_text, chunk_index), embedding in zip(chunks, normalized_embeddings):
                    # Format as pgvector string: [1,2,3]
                    vector_str = '[' + ','.join(str(x) for x in embedding) + ']'

                    # Embed the vector directly in SQL instead of using parameter
                    await conn.execute(
                        f"""
                        INSERT INTO chunks (document_id, content, chunk_index, embedding, metadata)
                        VALUES ($1, $2, $3, '{vector_str}'::vector, $4)
                        """,
                        document_id,
                        chunk_text,
                        chunk_index,
                        json.dumps({"length": len(chunk_text)})
                    )
                
                # Update status to completed
                await conn.execute(
                    "UPDATE documents SET status = $1 WHERE id = $2",
                    DocumentStatus.COMPLETED.value,
                    document_id
                )
            
            logger.info(f"Processed document {document_id} with {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e}")
            
            # Update status to failed
            async with db.acquire() as conn:
                await conn.execute(
                    "UPDATE documents SET status = $1 WHERE id = $2",
                    DocumentStatus.FAILED.value,
                    document_id
                )
    
    async def get_document(self, document_id: int) -> Optional[DocumentResponse]:
        """Get document by ID."""
        try:
            async with db.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT 
                        d.id,
                        d.name,
                        d.format,
                        d.status,
                        d.repository_id,
                        d.created_at,
                        d.updated_at,
                        COUNT(c.id) as chunk_count
                    FROM documents d
                    LEFT JOIN chunks c ON c.document_id = d.id
                    WHERE d.id = $1
                    GROUP BY d.id
                    """,
                    document_id
                )
                
                if not row:
                    return None
                
                return DocumentResponse(
                    id=row['id'],
                    name=row['name'],
                    format=row['format'],
                    status=DocumentStatus(row['status']),
                    repository_id=row['repository_id'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    chunk_count=row['chunk_count']
                )
                
        except Exception as e:
            logger.error(f"Error getting document: {e}")
            raise
    
    async def list_documents(
        self,
        repository_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[DocumentResponse]:
        """List documents, optionally filtered by repository."""
        try:
            async with db.acquire() as conn:
                if repository_id:
                    rows = await conn.fetch(
                        """
                        SELECT 
                            d.id,
                            d.name,
                            d.format,
                            d.status,
                            d.repository_id,
                            d.created_at,
                            d.updated_at,
                            COUNT(c.id) as chunk_count
                        FROM documents d
                        LEFT JOIN chunks c ON c.document_id = d.id
                        WHERE d.repository_id = $1
                        GROUP BY d.id
                        ORDER BY d.created_at DESC
                        LIMIT $2 OFFSET $3
                        """,
                        repository_id,
                        limit,
                        skip
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT 
                            d.id,
                            d.name,
                            d.format,
                            d.status,
                            d.repository_id,
                            d.created_at,
                            d.updated_at,
                            COUNT(c.id) as chunk_count
                        FROM documents d
                        LEFT JOIN chunks c ON c.document_id = d.id
                        GROUP BY d.id
                        ORDER BY d.created_at DESC
                        LIMIT $1 OFFSET $2
                        """,
                        limit,
                        skip
                    )
                
                return [
                    DocumentResponse(
                        id=row['id'],
                        name=row['name'],
                        format=row['format'],
                        status=DocumentStatus(row['status']),
                        repository_id=row['repository_id'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        chunk_count=row['chunk_count']
                    )
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            raise
    
    async def delete_document(self, document_id: int) -> bool:
        """Delete document and its chunks."""
        try:
            # Get file path
            async with db.acquire() as conn:
                file_path = await conn.fetchval(
                    "SELECT file_path FROM documents WHERE id = $1",
                    document_id
                )
                
                # Delete from database
                result = await conn.execute(
                    "DELETE FROM documents WHERE id = $1",
                    document_id
                )
                
                deleted = result.split()[-1] == "1"
            
            # Delete file
            if deleted and file_path:
                try:
                    Path(file_path).unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"Could not delete file {file_path}: {e}")
            
            if deleted:
                logger.info(f"Deleted document: {document_id}")
            
            return deleted
            
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise

    async def create_documents_bulk(
        self,
        files: List[Dict[str, Any]],
        repository_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create and process multiple documents in bulk.

        Args:
            files: List of dicts with keys: name, content, content_type
            repository_id: Optional repository ID

        Returns:
            Dict with upload results including success/failure counts
        """
        results = []
        successful = 0
        failed = 0

        for file_info in files:
            try:
                document = await self.create_document(
                    name=file_info["name"],
                    file_content=file_info["content"],
                    content_type=file_info["content_type"],
                    repository_id=repository_id
                )

                results.append({
                    "name": file_info["name"],
                    "status": "success",
                    "document_id": document.id,
                    "error": None
                })
                successful += 1

            except Exception as e:
                logger.error(f"Error uploading document {file_info.get('name', 'unknown')}: {e}")
                results.append({
                    "name": file_info.get("name", "unknown"),
                    "status": "error",
                    "document_id": None,
                    "error": str(e)
                })
                failed += 1

        return {
            "success": failed == 0,
            "total_files": len(files),
            "successful": successful,
            "failed": failed,
            "results": results,
            "timestamp": datetime.utcnow()
        }

    def _get_format_from_filename(self, filename: str) -> str:
        """Determine document format from filename."""
        suffix = Path(filename).suffix.lower()
        
        format_map = {
            '.pdf': DocumentFormat.PDF.value,
            '.txt': DocumentFormat.TXT.value,
            '.md': DocumentFormat.MD.value,
            '.docx': DocumentFormat.DOCX.value,
            '.html': DocumentFormat.HTML.value,
            '.htm': DocumentFormat.HTML.value
        }
        
        return format_map.get(suffix, DocumentFormat.TXT.value)


# Singleton instance
document_service = DocumentService()
