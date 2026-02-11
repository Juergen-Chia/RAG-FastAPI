"""Repository service for CRUD operations."""
from typing import List, Optional
import logging

from app.database import db
from app.models import RepositoryCreate, RepositoryUpdate, RepositoryResponse

logger = logging.getLogger(__name__)


class RepositoryService:
    """Service for managing repositories."""
    
    async def create_repository(
        self,
        repository_data: RepositoryCreate
    ) -> RepositoryResponse:
        """Create a new repository."""
        try:
            async with db.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO repositories (name, description)
                    VALUES ($1, $2)
                    RETURNING id, name, description, created_at, updated_at
                    """,
                    repository_data.name,
                    repository_data.description
                )
                
                logger.info(f"Created repository: {row['id']}")
                
                return RepositoryResponse(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    document_count=0
                )
                
        except Exception as e:
            logger.error(f"Error creating repository: {e}")
            raise
    
    async def get_repository(self, repository_id: int) -> Optional[RepositoryResponse]:
        """Get repository by ID."""
        try:
            async with db.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT 
                        r.id,
                        r.name,
                        r.description,
                        r.created_at,
                        r.updated_at,
                        COUNT(d.id) as document_count
                    FROM repositories r
                    LEFT JOIN documents d ON d.repository_id = r.id
                    WHERE r.id = $1
                    GROUP BY r.id
                    """,
                    repository_id
                )
                
                if not row:
                    return None
                
                return RepositoryResponse(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    document_count=row['document_count']
                )
                
        except Exception as e:
            logger.error(f"Error getting repository: {e}")
            raise
    
    async def list_repositories(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[RepositoryResponse]:
        """List all repositories."""
        try:
            async with db.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT 
                        r.id,
                        r.name,
                        r.description,
                        r.created_at,
                        r.updated_at,
                        COUNT(d.id) as document_count
                    FROM repositories r
                    LEFT JOIN documents d ON d.repository_id = r.id
                    GROUP BY r.id
                    ORDER BY r.created_at DESC
                    LIMIT $1 OFFSET $2
                    """,
                    limit,
                    skip
                )
                
                return [
                    RepositoryResponse(
                        id=row['id'],
                        name=row['name'],
                        description=row['description'],
                        created_at=row['created_at'],
                        updated_at=row['updated_at'],
                        document_count=row['document_count']
                    )
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Error listing repositories: {e}")
            raise
    
    async def update_repository(
        self,
        repository_id: int,
        repository_data: RepositoryUpdate
    ) -> Optional[RepositoryResponse]:
        """Update repository."""
        try:
            # Build update query dynamically
            updates = []
            params = []
            param_count = 1
            
            if repository_data.name is not None:
                updates.append(f"name = ${param_count}")
                params.append(repository_data.name)
                param_count += 1
            
            if repository_data.description is not None:
                updates.append(f"description = ${param_count}")
                params.append(repository_data.description)
                param_count += 1
            
            if not updates:
                return await self.get_repository(repository_id)
            
            params.append(repository_id)
            
            async with db.acquire() as conn:
                row = await conn.fetchrow(
                    f"""
                    UPDATE repositories
                    SET {', '.join(updates)}
                    WHERE id = ${param_count}
                    RETURNING id, name, description, created_at, updated_at
                    """,
                    *params
                )
                
                if not row:
                    return None
                
                logger.info(f"Updated repository: {repository_id}")
                
                # Get document count
                doc_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM documents WHERE repository_id = $1",
                    repository_id
                )
                
                return RepositoryResponse(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'],
                    created_at=row['created_at'],
                    updated_at=row['updated_at'],
                    document_count=doc_count
                )
                
        except Exception as e:
            logger.error(f"Error updating repository: {e}")
            raise
    
    async def delete_repository(self, repository_id: int) -> bool:
        """Delete repository and all its documents."""
        try:
            async with db.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM repositories WHERE id = $1",
                    repository_id
                )
                
                deleted = result.split()[-1] == "1"
                if deleted:
                    logger.info(f"Deleted repository: {repository_id}")
                
                return deleted
                
        except Exception as e:
            logger.error(f"Error deleting repository: {e}")
            raise


# Singleton instance
repository_service = RepositoryService()
