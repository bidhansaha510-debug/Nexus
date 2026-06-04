"""
NEXUS AI - Per-User Chat Context Manager
Provides isolated conversation contexts for each web user,
preventing chat history and emotional state from mixing between users.
"""

import threading
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logger import get_logger

logger = get_logger("user_context")


class UserChatContext:
    """
    Stores one user's isolated chat state.
    Each user gets their own instance so conversations never mix.
    """

    def __init__(self, user_id: int, username: str = ""):
        self.user_id = user_id
        self.username = username
        self.messages: List[Dict[str, Any]] = []
        self._lock = threading.RLock()
        self._max_context_messages = 40  # Sliding window for LLM
        self._loaded = False

    def load_history(self, history: List[Dict[str, Any]]):
        """Load chat history from database (called once on first access)."""
        with self._lock:
            if self._loaded:
                return
            self.messages = []
            for msg in history:
                self.messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                    "emotion": msg.get("emotion", "neutral"),
                    "intensity": msg.get("intensity", 0.5),
                    "timestamp": msg.get("timestamp", ""),
                })
            self._loaded = True
            logger.info(
                f"Loaded {len(self.messages)} messages for user {self.user_id}"
            )

    def add_message(self, role: str, content: str,
                    emotion: str = "neutral", intensity: float = 0.5):
        """Add a message to this user's context."""
        with self._lock:
            self.messages.append({
                "role": role,
                "content": content,
                "emotion": emotion,
                "intensity": intensity,
                "timestamp": datetime.now().isoformat(),
            })

    def get_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent messages for display."""
        with self._lock:
            return list(self.messages[-limit:])

    def get_llm_context(self, max_messages: int = None) -> List[Dict[str, str]]:
        """
        Get messages formatted for LLM consumption.
        Returns only role + content in the sliding window.
        """
        max_msg = max_messages or self._max_context_messages
        with self._lock:
            recent = self.messages[-max_msg:]
            return [
                {"role": m["role"], "content": m["content"]}
                for m in recent
                if m["role"] in ("user", "assistant")
            ]

    def clear(self):
        """Clear all messages from this context."""
        with self._lock:
            self.messages.clear()
            self._loaded = False


class UserContextManager:
    """
    Manages per-user conversation contexts.
    Each user_id maps to an isolated UserChatContext.
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
        self._contexts: Dict[int, UserChatContext] = {}
        self._ctx_lock = threading.Lock()
        logger.info("UserContextManager initialized")

    def get_context(self, user_id: int, username: str = "") -> UserChatContext:
        """Get or create a chat context for a user."""
        with self._ctx_lock:
            if user_id not in self._contexts:
                ctx = UserChatContext(user_id, username)
                self._contexts[user_id] = ctx
                logger.info(f"Created new context for user {user_id} ({username})")
            return self._contexts[user_id]

    def clear_context(self, user_id: int):
        """Clear and remove a user's context."""
        with self._ctx_lock:
            if user_id in self._contexts:
                self._contexts[user_id].clear()
                del self._contexts[user_id]
                logger.info(f"Cleared context for user {user_id}")

    def get_active_users(self) -> int:
        """Get count of active user contexts."""
        with self._ctx_lock:
            return len(self._contexts)


# Global instance
user_context_manager = UserContextManager()
