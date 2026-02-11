"""Conversation memory service using Redis."""
import json
import uuid
from typing import List, Dict, Optional
from datetime import datetime
import redis.asyncio as redis
import logging

from app.config import settings
from app.models import ConversationMessage

logger = logging.getLogger(__name__)


class ConversationMemory:
    """Manage conversation history using Redis."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.ttl = 86400 * 7  # 7 days TTL for conversations
    
    async def initialize(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("Conversation memory (Redis) initialized")
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory fallback: {e}")
            self.redis_client = None
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
    
    def _get_conversation_key(self, conversation_id: str) -> str:
        """Get Redis key for conversation."""
        return f"conversation:{conversation_id}"
    
    async def create_conversation(self) -> str:
        """Create a new conversation and return its ID."""
        conversation_id = str(uuid.uuid4())
        
        if self.redis_client:
            key = self._get_conversation_key(conversation_id)
            conversation_data = {
                "messages": [],
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            await self.redis_client.setex(
                key,
                self.ttl,
                json.dumps(conversation_data)
            )
        
        logger.info(f"Created conversation: {conversation_id}")
        return conversation_id
    
    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str
    ) -> None:
        """
        Add a message to conversation history.
        
        Args:
            conversation_id: Conversation identifier
            role: Message role (user or assistant)
            content: Message content
        """
        if not self.redis_client:
            return
        
        try:
            key = self._get_conversation_key(conversation_id)
            
            # Get existing conversation
            data = await self.redis_client.get(key)
            if data:
                conversation_data = json.loads(data)
            else:
                conversation_data = {
                    "messages": [],
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
            
            # Add new message
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat()
            }
            conversation_data["messages"].append(message)
            conversation_data["updated_at"] = datetime.utcnow().isoformat()
            
            # Keep only recent messages
            max_messages = settings.max_conversation_history * 2  # user + assistant pairs
            if len(conversation_data["messages"]) > max_messages:
                conversation_data["messages"] = conversation_data["messages"][-max_messages:]
            
            # Save back to Redis
            await self.redis_client.setex(
                key,
                self.ttl,
                json.dumps(conversation_data)
            )
            
        except Exception as e:
            logger.error(f"Error adding message to conversation: {e}")
    
    async def get_conversation_history(
        self,
        conversation_id: str,
        max_messages: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Get conversation history.
        
        Args:
            conversation_id: Conversation identifier
            max_messages: Maximum number of messages to return
            
        Returns:
            List of messages in OpenAI format (role, content)
        """
        if not self.redis_client:
            return []
        
        try:
            key = self._get_conversation_key(conversation_id)
            data = await self.redis_client.get(key)
            
            if not data:
                return []
            
            conversation_data = json.loads(data)
            messages = conversation_data.get("messages", [])
            
            # Limit number of messages
            if max_messages:
                messages = messages[-max_messages:]
            
            # Convert to OpenAI format
            return [
                {"role": msg["role"], "content": msg["content"]}
                for msg in messages
            ]
            
        except Exception as e:
            logger.error(f"Error retrieving conversation history: {e}")
            return []
    
    async def get_conversation_messages(
        self,
        conversation_id: str
    ) -> List[ConversationMessage]:
        """
        Get full conversation messages with timestamps.
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            List of ConversationMessage objects
        """
        if not self.redis_client:
            return []
        
        try:
            key = self._get_conversation_key(conversation_id)
            data = await self.redis_client.get(key)
            
            if not data:
                return []
            
            conversation_data = json.loads(data)
            messages = conversation_data.get("messages", [])
            
            return [
                ConversationMessage(
                    role=msg["role"],
                    content=msg["content"],
                    timestamp=datetime.fromisoformat(msg["timestamp"])
                )
                for msg in messages
            ]
            
        except Exception as e:
            logger.error(f"Error retrieving conversation messages: {e}")
            return []
    
    async def clear_conversation(self, conversation_id: str) -> None:
        """Clear conversation history."""
        if not self.redis_client:
            return
        
        try:
            key = self._get_conversation_key(conversation_id)
            await self.redis_client.delete(key)
            logger.info(f"Cleared conversation: {conversation_id}")
        except Exception as e:
            logger.error(f"Error clearing conversation: {e}")
    
    async def health_check(self) -> bool:
        """Check if conversation memory is healthy."""
        try:
            if not self.redis_client:
                return False
            await self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Conversation memory health check failed: {e}")
            return False


# Singleton instance
conversation_memory = ConversationMemory()
