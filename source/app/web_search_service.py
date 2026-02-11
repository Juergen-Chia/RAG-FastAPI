"""Web search service using SerpAPI."""
from typing import List, Dict, Any
import logging
from serpapi import GoogleSearch

from app.config import settings
from app.models import SearchResult

logger = logging.getLogger(__name__)


class WebSearchService:
    """Web search service using SerpAPI."""
    
    def __init__(self):
        self.api_key = settings.serpapi_api_key
    
    async def search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        """
        Search the web using SerpAPI.
        
        Args:
            query: Search query
            num_results: Number of results to return
            
        Returns:
            List of SearchResult objects
        """
        try:
            logger.info(f"Performing web search for: {query}")
            
            # Configure search parameters
            params = {
                "q": query,
                "api_key": self.api_key,
                "num": num_results,
                "engine": "google"
            }
            
            # Execute search
            search = GoogleSearch(params)
            results = search.get_dict()
            
            # Parse results
            search_results = []
            
            # Process organic results
            if "organic_results" in results:
                for i, result in enumerate(results["organic_results"][:num_results]):
                    search_result = SearchResult(
                        content=self._extract_content(result),
                        source="web",
                        score=1.0 - (i * 0.1),  # Decreasing score by rank
                        metadata={
                            "title": result.get("title", ""),
                            "position": result.get("position", i + 1)
                        },
                        url=result.get("link", "")
                    )
                    search_results.append(search_result)
            
            # Process answer box if available
            if "answer_box" in results:
                answer_box = results["answer_box"]
                search_result = SearchResult(
                    content=self._extract_answer_box_content(answer_box),
                    source="web",
                    score=1.0,
                    metadata={
                        "title": answer_box.get("title", "Answer Box"),
                        "type": "answer_box"
                    },
                    url=answer_box.get("link", "")
                )
                # Prepend answer box to results
                search_results.insert(0, search_result)
            
            logger.info(f"Found {len(search_results)} web search results")
            return search_results
            
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return []
    
    def _extract_content(self, result: Dict[str, Any]) -> str:
        """Extract content from search result."""
        parts = []
        
        if "title" in result:
            parts.append(result["title"])
        
        if "snippet" in result:
            parts.append(result["snippet"])
        
        if "snippet_highlighted_words" in result:
            # Add highlighted context
            highlighted = ", ".join(result["snippet_highlighted_words"])
            parts.append(f"Key terms: {highlighted}")
        
        return " | ".join(parts) if parts else "No content available"
    
    def _extract_answer_box_content(self, answer_box: Dict[str, Any]) -> str:
        """Extract content from answer box."""
        parts = []
        
        if "answer" in answer_box:
            parts.append(f"Answer: {answer_box['answer']}")
        
        if "snippet" in answer_box:
            parts.append(answer_box["snippet"])
        
        if "title" in answer_box:
            parts.append(f"Title: {answer_box['title']}")
        
        return " | ".join(parts) if parts else "No content available"


# Singleton instance
web_search_service = WebSearchService()
