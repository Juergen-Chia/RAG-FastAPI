"""Embedding service using Ali Cloud DashScope text-embedding-v4."""
from typing import List, Union
import numpy as np
from openai import AsyncOpenAI
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate embeddings for text using Ali Cloud DashScope text-embedding-v4."""

    def __init__(self):
        self.model_name = settings.embedding_model
        self.dimension = settings.embedding_dimension
        self.client: AsyncOpenAI = None

    async def initialize(self):
        """Initialize the Ali Cloud DashScope client."""
        try:
            logger.info(f"Initializing Ali Cloud DashScope embedding model: {self.model_name}")

            # Ali Cloud uses OpenAI-compatible API
            # The base_url should be set to DashScope's endpoint
            self.client = AsyncOpenAI(
                api_key=settings.openai_api_key,  # DashScope API key
                base_url=settings.openai_base_url  # DashScope endpoint
            )

            # Test the connection
            test_embedding = await self.embed_text("test")
            logger.info(f"Ali Cloud embedding model loaded successfully (dimension: {len(test_embedding)})")
        except Exception as e:
            logger.error(f"Failed to initialize Ali Cloud embedding service: {e}")
            raise

    async def embed_text(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings for text using Ali Cloud DashScope text-embedding-v4.

        Args:
            text: Single text string or list of text strings

        Returns:
            Single embedding vector or list of embedding vectors
        """
        if not self.client:
            raise RuntimeError("Embedding client not initialized")

        try:
            # Handle single string vs list
            is_single = isinstance(text, str)
            texts = [text] if is_single else text

            # DashScope text-embedding-v4 API
            # Batch processing: up to 10 texts per request (Ali Cloud limit)
            batch_size = 10
            all_embeddings = []

            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]

                response = await self.client.embeddings.create(
                    model=self.model_name,
                    input=batch,
                    encoding_format="float"
                )

                # Extract embeddings from response
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

            # Return single or list based on input
            return all_embeddings[0] if is_single else all_embeddings

        except Exception as e:
            logger.error(f"Error generating Ali Cloud embeddings: {e}")
            raise

    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for search query with L2 normalization.

        Args:
            query: Search query text

        Returns:
            L2 normalized embedding vector
        """
        embedding = await self.embed_text(query)

        # L2 normalize the query embedding
        if hasattr(embedding, 'tolist'):
            emb_array = np.array(embedding)
        else:
            emb_array = np.array(embedding)
        norm = np.linalg.norm(emb_array)
        if norm > 0:
            emb_array = emb_array / norm
        return emb_array.tolist()

    async def embed_documents(self, documents: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple documents with L2 normalization.

        Args:
            documents: List of document texts

        Returns:
            List of L2 normalized embedding vectors
        """
        embeddings = await self.embed_text(documents)

        # L2 normalize all embeddings
        normalized_embeddings = []
        for emb in embeddings:
            if hasattr(emb, 'tolist'):
                emb_array = np.array(emb)
            else:
                emb_array = np.array(emb)
            norm = np.linalg.norm(emb_array)
            if norm > 0:
                emb_array = emb_array / norm
            normalized_embeddings.append(emb_array.tolist())

        return normalized_embeddings

    def cosine_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))

    async def health_check(self) -> bool:
        """Check if embedding service is healthy."""
        try:
            if not self.client:
                return False

            # Test embedding generation
            test_embedding = await self.embed_text("test")
            return len(test_embedding) == self.dimension
        except Exception as e:
            logger.error(f"Embedding service health check failed: {e}")
            return False


# Singleton instance
embedding_service = EmbeddingService()
