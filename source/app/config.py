"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = Field(
        default="postgresql://postgres:password@localhost:5432/rag_db",
        alias="DATABASE_URL"
    )
    postgres_user: str = Field(default="postgres", alias="POSTGRES_USER")
    postgres_password: str = Field(default="password", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="rag_db", alias="POSTGRES_DB")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    
    # LLM Configuration
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    openai_base_url: str = Field(
        default="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        alias="OPENAI_BASE_URL"
    )
    openai_model: str = Field(
        default="qwen-plus",
        alias="OPENAI_MODEL"
    )
    
    # Local LLM (Ollama) - Commented
    # ollama_base_url: str = Field(
    #     default="http://localhost:11434",
    #     alias="OLLAMA_BASE_URL"
    # )
    # ollama_model: str = Field(default="llama2", alias="OLLAMA_MODEL")
    
    # Embedding Model - local sentence-transformers (1024-dim, matches pgvector column)
    embedding_model: str = Field(
        default="BAAI/bge-large-en-v1.5",
        alias="EMBEDDING_MODEL"
    )
    embedding_dimension: int = Field(default=1024, alias="EMBEDDING_DIMENSION")
    
    # Search
    serpapi_api_key: str = Field(..., alias="SERPAPI_API_KEY")
    
    # Application
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    streamlit_port: int = Field(default=8501, alias="STREAMLIT_PORT")
    chunk_size: int = Field(default=1000, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, alias="CHUNK_OVERLAP")
    max_conversation_history: int = Field(
        default=10,
        alias="MAX_CONVERSATION_HISTORY"
    )
    
    # Redis
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Singleton instance
settings = Settings()
