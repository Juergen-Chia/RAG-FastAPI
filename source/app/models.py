"""Pydantic models for request/response validation."""
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class DocumentStatus(str, Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentFormat(str, Enum):
    """Supported document formats."""
    PDF = "pdf"
    TXT = "txt"
    MD = "md"
    DOCX = "docx"
    HTML = "html"


class DocumentCreate(BaseModel):
    """Request model for document upload."""
    name: str = Field(..., description="Document name")
    content_type: str = Field(..., description="Document MIME type")
    repository_id: Optional[int] = Field(None, description="Repository ID")


class DocumentResponse(BaseModel):
    """Response model for document."""
    id: int
    name: str
    format: str
    status: DocumentStatus
    repository_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    chunk_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class BulkDocumentUploadItem(BaseModel):
    """Response model for a single document in bulk upload."""
    name: str
    status: str  # "success", "error"
    document_id: Optional[int] = None
    error: Optional[str] = None


class BulkDocumentUploadResponse(BaseModel):
    """Response model for bulk document upload."""
    success: bool
    total_files: int
    successful: int
    failed: int
    results: List[BulkDocumentUploadItem]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RepositoryCreate(BaseModel):
    """Request model for repository creation."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)


class RepositoryUpdate(BaseModel):
    """Request model for repository update."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class RepositoryResponse(BaseModel):
    """Response model for repository."""
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    document_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)


class ChunkResponse(BaseModel):
    """Response model for document chunk."""
    id: int
    document_id: int
    content: str
    chunk_index: int
    metadata: Dict[str, Any] = {}
    
    model_config = ConfigDict(from_attributes=True)


class SearchSource(str, Enum):
    """Search source type."""
    VECTOR = "vector"
    WEB = "web"
    BOTH = "both"


class SearchRequest(BaseModel):
    """Request model for search."""
    query: str = Field(..., min_length=1)
    repository_id: Optional[int] = None
    conversation_id: Optional[str] = None
    source: SearchSource = SearchSource.VECTOR  # Changed from BOTH - WEB SEARCH DISABLED
    top_k: int = Field(default=5, ge=1, le=20)
    use_conversation_memory: bool = True


class SearchResult(BaseModel):
    """Individual search result."""
    content: str
    source: str  # "vector" or "web"
    score: Optional[float] = None
    metadata: Dict[str, Any] = {}
    document_name: Optional[str] = None
    url: Optional[str] = None


class LLMResponse(BaseModel):
    """Structured LLM response."""
    answer: str = Field(..., description="Generated answer")
    sources_used: List[str] = Field(
        default_factory=list,
        description="Sources used for answer"
    )
    confidence: Optional[str] = Field(
        None,
        description="Confidence level: high, medium, low"
    )
    follow_up_questions: List[str] = Field(
        default_factory=list,
        description="Suggested follow-up questions"
    )


class SearchResponse(BaseModel):
    """Response model for search."""
    conversation_id: str
    query: str
    answer: str
    sources: List[SearchResult]
    llm_response: Optional[LLMResponse] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversationMessage(BaseModel):
    """Conversation message."""
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversationHistory(BaseModel):
    """Conversation history."""
    conversation_id: str
    messages: List[ConversationMessage]
    created_at: datetime
    updated_at: datetime


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database: str
    embedding_service: str
    llm_service: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
