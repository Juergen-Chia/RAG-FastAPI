"""Embedding service using sentence-transformers (BAAI/bge-large-en-v1.5)."""
import asyncio
from typing import List, Union
import numpy as np
import logging
import torch
from sentence_transformers import SentenceTransformer

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate embeddings using a local sentence-transformers model."""

    def __init__(self):
        self.model_name = settings.embedding_model
        self.dimension = settings.embedding_dimension
        self.model: SentenceTransformer = None
        self.device: str = None

    async def initialize(self):
        """Load the sentence-transformers model, using CUDA GPU if available."""
        try:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            if self.device == "cuda":
                logger.info(f"GPU detected: {torch.cuda.get_device_name(0)} — using CUDA")
            else:
                logger.info("No CUDA GPU detected — using CPU")

            logger.info(f"Loading sentence-transformers model: {self.model_name}")
            # Model loading is synchronous — run in a thread to avoid blocking the event loop
            self.model = await asyncio.to_thread(
                SentenceTransformer, self.model_name, device=self.device
            )
            logger.info(f"Embedding model loaded on {self.device} (dimension: {self.dimension})")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    async def embed_text(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Generate L2-normalized embeddings for one or more texts.

        Args:
            text: Single string or list of strings

        Returns:
            Single embedding vector or list of embedding vectors
        """
        if not self.model:
            raise RuntimeError("Embedding model not initialized")

        is_single = isinstance(text, str)
        texts = [text] if is_single else text

        # encode() is synchronous — run in thread pool to avoid blocking the event loop
        embeddings = await asyncio.to_thread(
            self.model.encode,
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        result = [emb.tolist() for emb in embeddings]
        return result[0] if is_single else result

    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a search query."""
        return await self.embed_text(query)

    async def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple documents."""
        return await self.embed_text(documents)

    def cosine_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float],
    ) -> float:
        """Calculate cosine similarity between two embeddings."""
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))

    async def health_check(self) -> bool:
        """Check if embedding service is healthy."""
        try:
            if not self.model:
                return False
            test_embedding = await self.embed_text("test")
            return len(test_embedding) == self.dimension
        except Exception as e:
            logger.error(f"Embedding service health check failed: {e}")
            return False


# Singleton instance
embedding_service = EmbeddingService()
