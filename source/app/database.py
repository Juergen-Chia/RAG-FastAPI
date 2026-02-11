"""Database connection and schema management."""
import asyncpg
from typing import Optional
from contextlib import asynccontextmanager
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Create database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                host=settings.postgres_host,
                port=settings.postgres_port,
                user=settings.postgres_user,
                password=settings.postgres_password,
                database=settings.postgres_db,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            logger.info("Database connection pool created")
            
            # Initialize schema
            await self.init_schema()
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    async def disconnect(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def init_schema(self):
        """Initialize database schema with pgvector extension."""
        async with self.pool.acquire() as conn:
            # Enable pgvector extension and upgrade to latest
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            # Try to upgrade pgvector to get latest functions
            try:
                await conn.execute("ALTER EXTENSION vector UPDATE")
                logger.info("pgvector extension updated to latest version")
            except Exception as e:
                logger.info(f"Could not update pgvector extension (might be at latest version): {e}")
            
            # Create repositories table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS repositories (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create documents table (repository_id removed - simplified)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    format VARCHAR(50) NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
                    file_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create chunks table with vector embeddings (Ali Cloud text-embedding-v4: 1024-dim)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id SERIAL PRIMARY KEY,
                    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    content TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    embedding vector(1024),
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for performance
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_document_id
                ON chunks(document_id)
            """)

            # Add full-text search index for keyword matching (names, titles, etc.)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_content_fts
                ON chunks USING gin(to_tsvector('english', content))
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chunks_embedding
                ON chunks USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)
            
            # Create trigger for updated_at
            await conn.execute("""
                CREATE OR REPLACE FUNCTION update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql'
            """)
            
            await conn.execute("""
                DROP TRIGGER IF EXISTS update_repositories_updated_at ON repositories
            """)
            
            await conn.execute("""
                CREATE TRIGGER update_repositories_updated_at
                BEFORE UPDATE ON repositories
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column()
            """)
            
            await conn.execute("""
                DROP TRIGGER IF EXISTS update_documents_updated_at ON documents
            """)
            
            await conn.execute("""
                CREATE TRIGGER update_documents_updated_at
                BEFORE UPDATE ON documents
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column()
            """)
            
            logger.info("Database schema initialized successfully")
    
    @asynccontextmanager
    async def acquire(self):
        """Context manager for acquiring database connection."""
        async with self.pool.acquire() as conn:
            yield conn


# Singleton instance
db = Database()
