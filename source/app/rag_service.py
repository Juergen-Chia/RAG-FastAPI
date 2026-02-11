"""RAG orchestration service combining vector search, keyword search, and LLM."""
from typing import List, Optional
import logging
from datetime import datetime
import json

from app.database import db
from app.embedding_service import embedding_service
from app.llm_service import llm_service
from app.conversation_memory import conversation_memory
from app.models import SearchRequest, SearchResponse, SearchResult, SearchSource

logger = logging.getLogger(__name__)


class RAGService:
    """RAG service for document search and answer generation."""

    async def vector_search(
        self,
        query: str,
        repository_id: Optional[int] = None,  # Kept for API compatibility, ignored
        top_k: int = 5
    ) -> List[SearchResult]:
        """
        Perform vector similarity search using pgvector.

        NOTE: repository_id parameter is kept for API compatibility but NOT used.
        All documents are searched.

        Args:
            query: Search query text
            repository_id: IGNORED (kept for API compatibility)
            top_k: Number of results to return

        Returns:
            List of SearchResult objects
        """
        try:
            # Generate query embedding
            query_embedding = await embedding_service.embed_query(query)

            # Convert to list and format as pgvector string
            if hasattr(query_embedding, 'tolist'):
                embedding_list = query_embedding.tolist()
            else:
                embedding_list = list(query_embedding)
            vector_str = '[' + ','.join(str(x) for x in embedding_list) + ']'

            logger.info(f"Vector search: query='{query}', dim={len(embedding_list)}, top_k={top_k}")

            # SIMPLIFIED: Always search ALL documents (no repository filter)
            async with db.acquire() as conn:
                sql = f"""
                    SELECT
                        c.id,
                        c.content,
                        c.metadata,
                        d.name as document_name,
                        c.embedding <=> '{vector_str}'::vector as distance
                    FROM chunks c
                    JOIN documents d ON c.document_id = d.id
                    WHERE c.embedding IS NOT NULL
                    ORDER BY c.embedding <=> '{vector_str}'::vector
                    LIMIT $1
                """

                all_chunks = await conn.fetch(sql, top_k * 5)
                logger.info(f"Fetched {len(all_chunks)} chunks")

                # Sort by distance (lower is better for cosine distance)
                if all_chunks:
                    sorted_chunks = sorted(
                        all_chunks,
                        key=lambda x: float(x['distance']) if x['distance'] is not None else float('inf')
                    )
                    rows = sorted_chunks[:top_k]
                else:
                    rows = []

            # Convert to SearchResult objects
            results = []
            for row in rows:
                distance = float(row['distance']) if row['distance'] is not None else 1.0
                similarity = 1.0 - distance

                # Deserialize metadata
                metadata = row['metadata']
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}

                result = SearchResult(
                    content=row['content'],
                    source="vector",
                    score=similarity,
                    metadata=metadata,
                    document_name=row['document_name']
                )
                results.append(result)

            logger.info(f"Vector search found {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Vector search error: {e}", exc_info=True)
            return []

    async def keyword_search(
        self,
        query: str,
        repository_id: Optional[int] = None,  # Kept for API compatibility, ignored
        top_k: int = 5
    ) -> List[SearchResult]:
        """
        Perform full-text keyword search using PostgreSQL GIN index.

        NOTE: repository_id parameter is kept for API compatibility but NOT used.

        Args:
            query: Search query
            repository_id: IGNORED (kept for API compatibility)
            top_k: Number of results to return

        Returns:
            List of SearchResult objects
        """
        try:
            async with db.acquire() as conn:
                # SIMPLIFIED: Search ALL documents (no repository filter)
                rows = await conn.fetch(
                    """
                    SELECT
                        c.id,
                        c.content,
                        c.metadata,
                        d.name as document_name,
                        ts_rank(to_tsvector('english', c.content),
                                plainto_tsquery('english', $1)) as rank
                    FROM chunks c
                    JOIN documents d ON c.document_id = d.id
                    WHERE to_tsvector('english', c.content) @@ plainto_tsquery('english', $1)
                    ORDER BY rank DESC
                    LIMIT $2
                    """,
                    query,
                    top_k
                )

            # Convert to SearchResult objects
            results = []
            for row in rows:
                metadata = row['metadata']
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}

                result = SearchResult(
                    content=row['content'],
                    source="keyword",
                    score=float(row['rank']),
                    metadata=metadata,
                    document_name=row['document_name']
                )
                results.append(result)

            logger.info(f"Keyword search found {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Keyword search error: {e}", exc_info=True)
            return []

    async def hybrid_search(
        self,
        query: str,
        repository_id: Optional[int] = None,  # Kept for API compatibility, ignored
        source: SearchSource = SearchSource.VECTOR,
        top_k: int = 5
    ) -> List[SearchResult]:
        """
        Perform hybrid search combining vector and keyword search.

        NOTE: repository_id parameter is kept for API compatibility but NOT used.

        Args:
            query: Search query
            repository_id: IGNORED (kept for API compatibility)
            source: Search source (VECTOR or WEB - WEB DISABLED)
            top_k: Number of results per source

        Returns:
            Combined list of SearchResult objects
        """
        results = []
        seen_content = set()  # For deduplication

        # Vector search (semantic similarity)
        if source in [SearchSource.VECTOR, SearchSource.BOTH]:
            vector_results = await self.vector_search(query, repository_id, top_k)
            for result in vector_results:
                content_hash = hash(result.content[:200])
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    results.append(result)

        # Keyword search (exact phrase matching)
        if source in [SearchSource.VECTOR, SearchSource.BOTH]:
            keyword_results = await self.keyword_search(query, repository_id, top_k)
            for result in keyword_results:
                content_hash = hash(result.content[:200])
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    # Boost keyword matches slightly
                    result.score = result.score * 1.2
                    results.append(result)

        # Sort by score (descending)
        results.sort(key=lambda x: x.score or 0, reverse=True)

        # Return top results
        results = results[:top_k * 2]

        logger.info(f"Hybrid search found {len(results)} results (vector+keyword)")
        return results

    async def search_and_generate(
        self,
        request: SearchRequest
    ) -> SearchResponse:
        """
        Perform search and generate answer using LLM.

        NOTE: repository_id is ignored - searches ALL documents.

        Args:
            request: SearchRequest with query and parameters

        Returns:
            SearchResponse with answer and sources
        """
        try:
            # Create or use existing conversation
            conversation_id = request.conversation_id
            if not conversation_id:
                conversation_id = await conversation_memory.create_conversation()

            # Perform hybrid search (ignores repository_id)
            search_results = await self.hybrid_search(
                query=request.query,
                repository_id=request.repository_id,  # Passed but ignored
                source=request.source,
                top_k=request.top_k
            )

            # Check if no results found
            if not search_results:
                no_results_msg = (
                    "No search results found. Please upload documents to the system first."
                )
                return SearchResponse(
                    conversation_id=conversation_id,
                    query=request.query,
                    answer=no_results_msg,
                    sources=[],
                    timestamp=datetime.utcnow()
                )

            # Get conversation history if enabled
            conversation_history = None
            if request.use_conversation_memory:
                conversation_history = await conversation_memory.get_conversation_history(
                    conversation_id
                )

            # Generate answer using LLM
            llm_response = await llm_service.generate_answer(
                query=request.query,
                context=search_results,
                conversation_history=conversation_history,
                use_structured_output=True
            )

            # Store conversation
            if request.use_conversation_memory:
                await conversation_memory.add_message(
                    conversation_id=conversation_id,
                    role="user",
                    content=request.query
                )
                await conversation_memory.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=llm_response.answer
                )

            return SearchResponse(
                conversation_id=conversation_id,
                query=request.query,
                answer=llm_response.answer,
                sources=[
                    SearchResult(
                        content=r.content,
                        source=r.source,
                        score=r.score,
                        metadata=r.metadata,
                        document_name=r.document_name
                    )
                    for r in search_results[:10]
                ],
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Search and generate error: {e}", exc_info=True)
            raise


# Singleton instance
rag_service = RAGService()
