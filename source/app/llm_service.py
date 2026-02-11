"""LLM service with OpenAI compatible wrapper and typed responses."""
import json
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
import logging

from app.config import settings
from app.models import LLMResponse, SearchResult

logger = logging.getLogger(__name__)


class LLMService:
    """LLM service supporting OpenAI-compatible endpoints."""
    
    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self.model = settings.openai_model
    
    async def initialize(self):
        """Initialize LLM client."""
        try:
            self.client = AsyncOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url
            )
            logger.info(f"LLM service initialized with model: {self.model}")
            
            # Uncomment for local Ollama support
            # if settings.use_local_llm:
            #     self.client = AsyncOpenAI(
            #         api_key="ollama",  # Ollama doesn't need real API key
            #         base_url=settings.ollama_base_url
            #     )
            #     self.model = settings.ollama_model
            #     logger.info(f"Using local Ollama model: {self.model}")
            
        except Exception as e:
            logger.error(f"Failed to initialize LLM service: {e}")
            raise
    
    async def generate_answer(
        self,
        query: str,
        context: List[SearchResult],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        use_structured_output: bool = True
    ) -> LLMResponse:
        """
        Generate answer using LLM with context and conversation history.
        
        Args:
            query: User query
            context: List of search results for context
            conversation_history: Previous conversation messages
            use_structured_output: Whether to request structured JSON response
            
        Returns:
            LLMResponse with structured answer
        """
        try:
            # Build context from search results
            context_text = self._build_context(context)
            
            # Build system prompt
            system_prompt = self._build_system_prompt(use_structured_output)
            
            # Build messages
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history
            if conversation_history:
                messages.extend(conversation_history[-settings.max_conversation_history:])
            
            # Add current query with context
            user_message = self._build_user_message(query, context_text)
            messages.append({"role": "user", "content": user_message})
            
            # Generate response
            if use_structured_output:
                response = await self._generate_structured_response(messages)
            else:
                response = await self._generate_text_response(messages)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating LLM answer: {e}")
            # Return fallback response
            return LLMResponse(
                answer=f"I apologize, but I encountered an error processing your question. Error: {str(e)}",
                sources_used=[],
                confidence="low",
                follow_up_questions=[]
            )
    
    async def _generate_structured_response(
        self,
        messages: List[Dict[str, str]]
    ) -> LLMResponse:
        """Generate structured JSON response from LLM."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            
            # Parse JSON response
            try:
                data = json.loads(content)
                return LLMResponse(
                    answer=data.get("answer", content),
                    sources_used=data.get("sources_used", []),
                    confidence=data.get("confidence", "medium"),
                    follow_up_questions=data.get("follow_up_questions", [])
                )
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return LLMResponse(
                    answer=content,
                    sources_used=[],
                    confidence="medium",
                    follow_up_questions=[]
                )
                
        except Exception as e:
            logger.error(f"Error in structured response generation: {e}")
            raise
    
    async def _generate_text_response(
        self,
        messages: List[Dict[str, str]]
    ) -> LLMResponse:
        """Generate plain text response from LLM."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            answer = response.choices[0].message.content
            
            return LLMResponse(
                answer=answer,
                sources_used=[],
                confidence="medium",
                follow_up_questions=[]
            )
            
        except Exception as e:
            logger.error(f"Error in text response generation: {e}")
            raise
    
    def _build_system_prompt(self, use_structured_output: bool) -> str:
        """Build system prompt for LLM."""
        base_prompt = """You are a helpful AI assistant that answers questions based on provided context.
Your role is to:
1. Analyze the provided context and conversation history
2. Generate accurate, helpful answers to user questions
3. Cite sources when possible
4. Indicate confidence levels in your answers
5. Suggest relevant follow-up questions when appropriate

Important guidelines:
- Only use information from the provided context
- If the context doesn't contain enough information, say so clearly
- Be concise but thorough
- Maintain context from the conversation history"""

        if use_structured_output:
            base_prompt += """

Respond in JSON format with the following structure:
{
    "answer": "Your detailed answer here",
    "sources_used": ["list", "of", "sources"],
    "confidence": "high|medium|low",
    "follow_up_questions": ["question 1?", "question 2?"]
}"""
        
        return base_prompt
    
    def _build_context(self, search_results: List[SearchResult]) -> str:
        """Build context string from search results."""
        if not search_results:
            return "No specific context available."
        
        context_parts = []
        for i, result in enumerate(search_results, 1):
            source_label = f"[Source {i}]"
            if result.document_name:
                source_label += f" Document: {result.document_name}"
            elif result.url:
                source_label += f" URL: {result.url}"
            
            context_parts.append(f"{source_label}\n{result.content}")
        
        return "\n\n".join(context_parts)
    
    def _build_user_message(self, query: str, context: str) -> str:
        """Build user message with query and context."""
        return f"""Context:
{context}

Question: {query}

Please provide a comprehensive answer based on the context above."""
    
    async def health_check(self) -> bool:
        """Check if LLM service is healthy."""
        try:
            if not self.client:
                return False
            
            # Test simple completion
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Say 'OK'"}],
                max_tokens=5
            )
            
            return bool(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"LLM service health check failed: {e}")
            return False


# Singleton instance
llm_service = LLMService()
