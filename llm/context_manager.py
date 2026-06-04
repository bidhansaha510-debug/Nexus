"""
NEXUS AI - Context Manager
Manages conversation context, sliding windows, and context optimization
"""

import threading
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
import json
import re

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import NEXUS_CONFIG
from utils.logger import get_logger

logger = get_logger("context_manager")


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT MESSAGE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ContextMessage:
    """A single message in the context"""
    role: str = "user"                      # user, assistant, system
    content: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    token_estimate: int = 0
    importance: float = 0.5                 # 0-1 for context pruning
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # Rough token estimation (~4 chars per token)
        self.token_estimate = len(self.content) // 4 + 1
    
    def to_llm_format(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}
    
    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "token_estimate": self.token_estimate,
            "importance": self.importance,
            "metadata": self.metadata
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CONVERSATION SESSION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ConversationSession:
    """Represents a single conversation session"""
    session_id: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    messages: List[ContextMessage] = field(default_factory=list)
    topic: str = ""
    summary: str = ""
    total_tokens: int = 0
    is_active: bool = True
    
    def add_message(self, role: str, content: str, importance: float = 0.5, 
                    metadata: Dict = None) -> ContextMessage:
        msg = ContextMessage(
            role=role,
            content=content,
            importance=importance,
            metadata=metadata or {}
        )
        self.messages.append(msg)
        self.total_tokens += msg.token_estimate
        return msg
    
    def get_messages_for_llm(self, max_tokens: int = None) -> List[Dict[str, str]]:
        """Get messages formatted for LLM, respecting token limit"""
        if max_tokens is None:
            return [m.to_llm_format() for m in self.messages]
        
        # Work backwards from most recent, keeping within token limit
        result = []
        current_tokens = 0
        
        for msg in reversed(self.messages):
            if current_tokens + msg.token_estimate > max_tokens:
                break
            result.insert(0, msg.to_llm_format())
            current_tokens += msg.token_estimate
        
        return result
    
    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat(),
            "messages": [m.to_dict() for m in self.messages],
            "topic": self.topic,
            "summary": self.summary,
            "total_tokens": self.total_tokens,
            "is_active": self.is_active
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class ContextManager:
    """
    Manages conversation context for NEXUS
    
    Features:
    - Sliding context window
    - Smart context pruning
    - Session management
    - Context compression/summarization
    - Multi-session awareness
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        
        self._config = NEXUS_CONFIG.llm
        self._max_context_tokens = self._config.context_window
        
        # Reserve tokens for system prompt and response
        # Keep reserves reasonable to avoid negative available tokens
        self._system_prompt_reserve = 500  # Reduced from 2000
        self._response_reserve = min(self._config.max_tokens, 1000)  # Cap at 1000
        self._available_context_tokens = max(
            500,  # Minimum 500 tokens for context
            self._max_context_tokens 
            - self._system_prompt_reserve 
            - self._response_reserve
        )
        
        # Current session
        self._current_session: Optional[ConversationSession] = None
        
        # Session history
        self._session_history: List[ConversationSession] = []
        self._max_sessions = 50
        
        # Persistent context (always included)
        self._persistent_context: List[str] = []
        
        # Context lock
        self._context_lock = threading.RLock()
        
        # Start a new session
        self.new_session()
        
        logger.info(
            f"Context Manager initialized. "
            f"Window: {self._max_context_tokens} tokens, "
            f"Available: {self._available_context_tokens} tokens"
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SESSION MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def new_session(self, topic: str = "") -> ConversationSession:
        """Start a new conversation session"""
        with self._context_lock:
            # Archive current session if it exists
            if self._current_session and self._current_session.messages:
                self._current_session.is_active = False
                self._session_history.append(self._current_session)
                
                if len(self._session_history) > self._max_sessions:
                    self._session_history.pop(0)
            
            # Create new session
            import uuid
            self._current_session = ConversationSession(
                session_id=str(uuid.uuid4()),
                topic=topic
            )
            
            logger.info(f"New session started: {self._current_session.session_id[:8]}")
            return self._current_session
    
    @property
    def current_session(self) -> ConversationSession:
        """Get current conversation session"""
        if self._current_session is None:
            self.new_session()
        return self._current_session
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MESSAGE MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def add_message(
        self,
        role: str,
        content: str,
        importance: Optional[float] = None,
        metadata: Dict = None
    ) -> ContextMessage:
        """Add a message to context using an explicit LLM role."""
        normalized_role = (role or "").strip().lower()
        default_importance = {
            "user": 0.7,
            "assistant": 0.5,
            "system": 0.9,
        }

        if normalized_role not in default_importance:
            raise ValueError(
                f"Unsupported context role '{role}'. "
                "Expected one of: user, assistant, system."
            )

        with self._context_lock:
            msg = self.current_session.add_message(
                role=normalized_role,
                content=content,
                importance=(
                    default_importance[normalized_role]
                    if importance is None else importance
                ),
                metadata=metadata or {}
            )
            self._ensure_token_limit()
            return msg

    def add_user_message(self, content: str, metadata: Dict = None) -> ContextMessage:
        """Add a user message to context"""
        with self._context_lock:
            msg = self.current_session.add_message(
                role="user",
                content=content,
                importance=0.7,
                metadata=metadata or {}
            )
            
            # Check if we need to prune
            self._ensure_token_limit()
            
            return msg
    
    def add_assistant_message(self, content: str, metadata: Dict = None) -> ContextMessage:
        """Add an assistant message to context"""
        with self._context_lock:
            msg = self.current_session.add_message(
                role="assistant",
                content=content,
                importance=0.5,
                metadata=metadata or {}
            )
            
            self._ensure_token_limit()
            
            return msg
    
    def add_system_message(self, content: str) -> ContextMessage:
        """Add a system-level context message"""
        with self._context_lock:
            msg = self.current_session.add_message(
                role="system",
                content=content,
                importance=0.9
            )
            return msg
    
    def add_persistent_context(self, context: str):
        """Add context that persists across messages"""
        with self._context_lock:
            if context not in self._persistent_context:
                self._persistent_context.append(context)
    
    def remove_persistent_context(self, context: str):
        """Remove persistent context"""
        with self._context_lock:
            if context in self._persistent_context:
                self._persistent_context.remove(context)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONTEXT RETRIEVAL
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_context_messages(
        self,
        max_tokens: int = None,
        include_persistent: bool = True
    ) -> List[Dict[str, str]]:
        """
        Get context messages for LLM consumption
        
        Args:
            max_tokens: Override max token limit
            include_persistent: Include persistent context
            
        Returns:
            List of message dicts for LLM
        """
        with self._context_lock:
            available = max_tokens or self._available_context_tokens
            messages = []
            current_tokens = 0
            
            # Add persistent context first
            if include_persistent and self._persistent_context:
                persistent_content = "\n".join(self._persistent_context)
                persistent_tokens = len(persistent_content) // 4
                if persistent_tokens < available:
                    messages.append({
                        "role": "system",
                        "content": persistent_content
                    })
                    current_tokens += persistent_tokens
            
            # Add conversation messages (most recent first, then reverse)
            remaining_tokens = available - current_tokens
            conv_messages = self.current_session.get_messages_for_llm(remaining_tokens)
            messages.extend(conv_messages)
            
            return messages
    
    def get_conversation_text(self, limit: int = None) -> str:
        """Get conversation as plain text"""
        with self._context_lock:
            messages = self.current_session.messages
            if limit:
                messages = messages[-limit:]
            
            lines = []
            for msg in messages:
                lines.append(f"{msg.role}: {msg.content}")
            
            return "\n".join(lines)
    
    def get_recent_messages(self, count: int = 10) -> List[Dict]:
        """Get the N most recent messages"""
        with self._context_lock:
            return [
                m.to_dict() 
                for m in self.current_session.messages[-count:]
            ]
    
    def get_last_user_message(self) -> Optional[str]:
        """Get the last user message"""
        with self._context_lock:
            for msg in reversed(self.current_session.messages):
                if msg.role == "user":
                    return msg.content
            return None
    
    def get_last_assistant_message(self) -> Optional[str]:
        """Get the last assistant message"""
        with self._context_lock:
            for msg in reversed(self.current_session.messages):
                if msg.role == "assistant":
                    return msg.content
            return None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONTEXT OPTIMIZATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _ensure_token_limit(self):
        """Ensure context is within token limits"""
        with self._context_lock:
            session = self.current_session
            
            while session.total_tokens > self._available_context_tokens and len(session.messages) > 2:
                # Remove oldest, least important message
                # But keep the most recent messages
                if len(session.messages) > 4:
                    # Find least important message in the older half
                    older_half = session.messages[:len(session.messages)//2]
                    least_important = min(older_half, key=lambda m: m.importance)
                    
                    session.total_tokens -= least_important.token_estimate
                    session.messages.remove(least_important)
                else:
                    # Just remove the oldest
                    removed = session.messages.pop(0)
                    session.total_tokens -= removed.token_estimate
    
    def compress_context(self, summarizer_func=None) -> str:
        """
        Compress older context into a summary
        
        Args:
            summarizer_func: Optional function to generate summary
            
        Returns:
            Summary of compressed messages
        """
        with self._context_lock:
            session = self.current_session
            
            if len(session.messages) < 10:
                return ""
            
            # Get older messages to compress
            messages_to_compress = session.messages[:len(session.messages)//2]
            
            # Generate summary
            if summarizer_func:
                text = "\n".join(
                    f"{m.role}: {m.content}" for m in messages_to_compress
                )
                summary = summarizer_func(text)
            else:
                # Simple summary
                topics = set()
                for msg in messages_to_compress:
                    words = msg.content.lower().split()
                    # Extract potential topics (words > 4 chars)
                    topics.update(w for w in words if len(w) > 4)
                
                summary = (
                    f"Earlier conversation covered: {', '.join(list(topics)[:20])}. "
                    f"({len(messages_to_compress)} messages compressed)"
                )
            
            # Remove compressed messages
            session.messages = session.messages[len(messages_to_compress):]
            
            # Recalculate total tokens
            session.total_tokens = sum(m.token_estimate for m in session.messages)
            
            # Add summary as system message
            session.summary = summary
            self.add_system_message(f"[Conversation Summary]: {summary}")
            
            logger.info(f"Context compressed. Removed {len(messages_to_compress)} messages")
            
            return summary
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CROSS-SESSION CONTEXT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_cross_session_context(self, max_sessions: int = 3) -> str:
        """Get context from previous sessions"""
        with self._context_lock:
            if not self._session_history:
                return ""
            
            parts = ["=== PREVIOUS SESSIONS ==="]
            
            recent_sessions = self._session_history[-max_sessions:]
            for session in recent_sessions:
                if session.summary:
                    parts.append(f"Session ({session.started_at.strftime('%Y-%m-%d %H:%M')}): {session.summary}")
                elif session.topic:
                    parts.append(f"Session ({session.started_at.strftime('%Y-%m-%d %H:%M')}): Topic - {session.topic}")
            
            return "\n".join(parts)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STATS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_stats(self) -> Dict[str, Any]:
        """Get context manager statistics"""
        with self._context_lock:
            return {
                "current_session_id": self.current_session.session_id[:8],
                "current_messages": len(self.current_session.messages),
                "current_tokens": self.current_session.total_tokens,
                "max_tokens": self._available_context_tokens,
                "token_usage_pct": (
                    self.current_session.total_tokens / self._available_context_tokens * 100
                    if self._available_context_tokens > 0 else 0
                ),
                "total_sessions": len(self._session_history) + 1,
                "persistent_contexts": len(self._persistent_context)
            }


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

context_manager = ContextManager()


if __name__ == "__main__":
    cm = ContextManager()
    
    # Simulate a conversation
    cm.add_user_message("Hello NEXUS! How are you?")
    cm.add_assistant_message("Hello! I'm doing great, feeling curious today. How can I help you?")
    cm.add_user_message("Can you help me with a Python project?")
    cm.add_assistant_message("Of course! I'd love to help. What kind of Python project?")
    cm.add_user_message("I'm building a machine learning model for image classification")
    
    # Get context
    messages = cm.get_context_messages()
    print("Context Messages:")
    for msg in messages:
        print(f"  [{msg['role']}]: {msg['content'][:80]}...")
    
    print(f"\nStats: {cm.get_stats()}")
    
    print(f"\nConversation text:\n{cm.get_conversation_text()}")
