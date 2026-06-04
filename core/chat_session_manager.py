"""
NEXUS AI - Chat Session Manager
Persistent conversation sessions with auto-save and restoration.
Solves the "AI forgets conversation after GUI restart" issue.
"""

import threading
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
import re

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("chat_session_manager")


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ChatMessage:
    """A single chat message"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    emotion: str = ""
    emotion_intensity: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "emotion": self.emotion,
            "emotion_intensity": self.emotion_intensity,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ChatMessage':
        return cls(
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", datetime.now().isoformat()),
            emotion=data.get("emotion", ""),
            emotion_intensity=data.get("emotion_intensity", 0.0),
            metadata=data.get("metadata", {})
        )


@dataclass
class ChatSession:
    """A complete chat session"""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    ended_at: str = ""
    topic: str = ""
    summary: str = ""
    messages: List[ChatMessage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def message_count(self) -> int:
        return len(self.messages)
    
    @property
    def is_active(self) -> bool:
        return self.ended_at == ""
    
    def add_message(self, role: str, content: str, emotion: str = "", 
                    emotion_intensity: float = 0.0, metadata: Dict = None) -> ChatMessage:
        msg = ChatMessage(
            role=role,
            content=content,
            emotion=emotion,
            emotion_intensity=emotion_intensity,
            metadata=metadata or {}
        )
        self.messages.append(msg)
        return msg
    
    def end_session(self):
        self.ended_at = datetime.now().isoformat()
    
    def generate_topic(self) -> str:
        """Generate a topic from the first few messages"""
        if not self.messages:
            return "Empty session"
        
        # Get first user message
        first_user = None
        for msg in self.messages:
            if msg.role == "user":
                first_user = msg.content
                break
        
        if first_user:
            # Take first 50 chars or until sentence end
            topic = first_user[:50]
            if len(first_user) > 50:
                topic += "..."
            return topic
        return "Chat session"
    
    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "topic": self.topic,
            "summary": self.summary,
            "message_count": self.message_count,
            "messages": [m.to_dict() for m in self.messages],
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ChatSession':
        session = cls(
            session_id=data.get("session_id", str(uuid.uuid4())),
            started_at=data.get("started_at", datetime.now().isoformat()),
            ended_at=data.get("ended_at", ""),
            topic=data.get("topic", ""),
            summary=data.get("summary", ""),
            metadata=data.get("metadata", {})
        )
        for msg_data in data.get("messages", []):
            session.messages.append(ChatMessage.from_dict(msg_data))
        return session


# ═══════════════════════════════════════════════════════════════════════════════
# CHAT SESSION MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class ChatSessionManager:
    """
    Manages persistent chat sessions with auto-save and restoration.
    
    Features:
    - Auto-save sessions to disk after each message
    - Auto-load last session on startup
    - Session browser with search
    - Topic extraction and summaries
    - Multi-session support
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
        
        # Storage paths
        self._sessions_dir = DATA_DIR / "sessions"
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        self._index_file = self._sessions_dir / "session_index.json"
        
        # Current session
        self._current_session: Optional[ChatSession] = None
        
        # Session index (metadata for all sessions)
        self._session_index: List[Dict] = []
        
        # Thread lock
        self._manager_lock = threading.RLock()
        
        # Auto-save timer
        self._auto_save_enabled = True
        self._last_save_time: Optional[datetime] = None
        
        # Load session index
        self._load_index()
        
        logger.info(f"Chat Session Manager initialized. {len(self._session_index)} sessions on record.")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SESSION LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def start_new_session(self, topic: str = "") -> ChatSession:
        """Start a new chat session"""
        with self._manager_lock:
            # End current session if exists
            if self._current_session and self._current_session.is_active:
                self.end_current_session()
            
            # Create new session
            self._current_session = ChatSession(topic=topic)
            
            # Save initial session file
            self._save_session(self._current_session)
            
            logger.info(f"Started new session: {self._current_session.session_id[:8]}")
            return self._current_session
    
    def end_current_session(self) -> Optional[ChatSession]:
        """End the current session"""
        with self._manager_lock:
            if not self._current_session:
                return None
            
            self._current_session.end_session()
            
            # Generate topic if not set
            if not self._current_session.topic:
                self._current_session.topic = self._current_session.generate_topic()
            
            # Save final state
            self._save_session(self._current_session)
            self._update_index(self._current_session)
            
            ended_session = self._current_session
            logger.info(
                f"Ended session: {ended_session.session_id[:8]} "
                f"({ended_session.message_count} messages)"
            )
            
            self._current_session = None
            return ended_session
    
    def get_or_create_session(self) -> ChatSession:
        """Get current session or create a new one"""
        with self._manager_lock:
            if self._current_session is None:
                self._current_session = ChatSession()
                self._save_session(self._current_session)
            return self._current_session
    
    @property
    def current_session(self) -> Optional[ChatSession]:
        return self._current_session
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MESSAGE HANDLING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def add_message(self, role: str, content: str, emotion: str = "",
                    emotion_intensity: float = 0.0, metadata: Dict = None) -> ChatMessage:
        """Add a message to the current session and auto-save"""
        with self._manager_lock:
            session = self.get_or_create_session()
            msg = session.add_message(
                role=role,
                content=content,
                emotion=emotion,
                emotion_intensity=emotion_intensity,
                metadata=metadata
            )
            
            # Auto-save
            if self._auto_save_enabled:
                self._save_session(session)
                self._last_save_time = datetime.now()
            
            return msg
    
    def get_messages(self, limit: int = None) -> List[ChatMessage]:
        """Get messages from current session"""
        with self._manager_lock:
            if not self._current_session:
                return []
            
            messages = self._current_session.messages
            if limit:
                messages = messages[-limit:]
            return messages
    
    def get_messages_for_context(self, max_messages: int = 20) -> List[Dict[str, str]]:
        """Get messages formatted for LLM context"""
        with self._manager_lock:
            if not self._current_session:
                return []
            
            messages = self._current_session.messages[-max_messages:]
            return [{"role": m.role, "content": m.content} for m in messages]
    
    def clear_current_session(self):
        """Clear current session messages (but keep session alive)"""
        with self._manager_lock:
            if self._current_session:
                self._current_session.messages.clear()
                self._save_session(self._current_session)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _get_session_file(self, session_id: str) -> Path:
        """Get the file path for a session"""
        return self._sessions_dir / f"session_{session_id}.json"
    
    def _save_session(self, session: ChatSession):
        """Save session to disk"""
        try:
            filepath = self._get_session_file(session.session_id)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved session: {session.session_id[:8]}")
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
    
    def _load_session(self, session_id: str) -> Optional[ChatSession]:
        """Load a session from disk"""
        try:
            filepath = self._get_session_file(session_id)
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return ChatSession.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
        return None
    
    def _load_index(self):
        """Load session index from disk"""
        try:
            if self._index_file.exists():
                with open(self._index_file, 'r', encoding='utf-8') as f:
                    self._session_index = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load session index: {e}")
            self._session_index = []
    
    def _save_index(self):
        """Save session index to disk"""
        try:
            with open(self._index_file, 'w', encoding='utf-8') as f:
                json.dump(self._session_index, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save session index: {e}")
    
    def _update_index(self, session: ChatSession):
        """Update or add session in index"""
        # Remove existing entry if present
        self._session_index = [
            s for s in self._session_index 
            if s.get("session_id") != session.session_id
        ]
        
        # Add updated entry
        self._session_index.insert(0, {
            "session_id": session.session_id,
            "started_at": session.started_at,
            "ended_at": session.ended_at,
            "topic": session.topic or session.generate_topic(),
            "message_count": session.message_count
        })
        
        # Keep only last 100 sessions in index
        self._session_index = self._session_index[:100]
        
        self._save_index()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SESSION RESTORATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def restore_last_session(self) -> Optional[ChatSession]:
        """Restore the most recent session"""
        with self._manager_lock:
            # Find most recent active or recent ended session
            if not self._session_index:
                # Try to find any session files
                session_files = list(self._sessions_dir.glob("session_*.json"))
                if session_files:
                    # Sort by modification time
                    session_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                    for filepath in session_files[:5]:  # Check recent 5
                        try:
                            with open(filepath, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            session = ChatSession.from_dict(data)
                            if session.messages:  # Only restore if has messages
                                self._current_session = session
                                logger.info(
                                    f"Restored session from file: {session.session_id[:8]} "
                                    f"({session.message_count} messages)"
                                )
                                return session
                        except Exception as e:
                            logger.debug(f"Could not load session file {filepath}: {e}")
                return None
            
            # Get most recent from index
            recent = self._session_index[0]
            session_id = recent.get("session_id")
            
            if session_id:
                session = self._load_session(session_id)
                if session:
                    self._current_session = session
                    logger.info(
                        f"Restored last session: {session.session_id[:8]} "
                        f"({session.message_count} messages)"
                    )
                    return session
            
            return None
    
    def restore_session(self, session_id: str) -> Optional[ChatSession]:
        """Restore a specific session by ID"""
        with self._manager_lock:
            session = self._load_session(session_id)
            if session:
                # End current session if active
                if self._current_session and self._current_session.is_active:
                    self.end_current_session()
                
                self._current_session = session
                logger.info(f"Restored session: {session_id[:8]}")
                return session
            return None
    
    def get_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """Get metadata for recent sessions"""
        return self._session_index[:limit]
    
    def search_sessions(self, query: str, limit: int = 10) -> List[Dict]:
        """Search sessions by topic or content"""
        query_lower = query.lower()
        results = []
        
        for entry in self._session_index:
            if query_lower in entry.get("topic", "").lower():
                results.append(entry)
                if len(results) >= limit:
                    break
        
        # If not enough results from index, search in files
        if len(results) < limit:
            for filepath in self._sessions_dir.glob("session_*.json"):
                if len(results) >= limit:
                    break
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Check if already in results
                    if any(r.get("session_id") == data.get("session_id") for r in results):
                        continue
                    
                    # Search in messages
                    for msg in data.get("messages", []):
                        if query_lower in msg.get("content", "").lower():
                            results.append({
                                "session_id": data.get("session_id"),
                                "started_at": data.get("started_at"),
                                "topic": data.get("topic", "Unknown topic"),
                                "message_count": len(data.get("messages", [])),
                                "match_type": "content"
                            })
                            break
                except Exception:
                    pass
        
        return results[:limit]
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session"""
        with self._manager_lock:
            try:
                filepath = self._get_session_file(session_id)
                if filepath.exists():
                    filepath.unlink()
                
                # Remove from index
                self._session_index = [
                    s for s in self._session_index 
                    if s.get("session_id") != session_id
                ]
                self._save_index()
                
                logger.info(f"Deleted session: {session_id[:8]}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete session: {e}")
                return False
    
    def delete_all_sessions(self) -> int:
        """Delete all chat sessions"""
        count = 0
        with self._manager_lock:
            try:
                # Delete all session files
                for filepath in self._sessions_dir.glob("session_*.json"):
                    if filepath.exists():
                        filepath.unlink()
                        count += 1
                
                # Clear index
                self._session_index = []
                self._save_index()
                
                # Clear current session
                if self._current_session:
                    self._current_session = None
                    
                logger.info(f"Deleted all {count} sessions")
                return count
            except Exception as e:
                logger.error(f"Failed to delete all sessions: {e}")
                return count

    # ═══════════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session manager statistics"""
        total_messages = sum(
            entry.get("message_count", 0) 
            for entry in self._session_index
        )
        
        return {
            "total_sessions": len(self._session_index),
            "total_messages": total_messages,
            "current_session_id": (
                self._current_session.session_id[:8] 
                if self._current_session else None
            ),
            "current_session_messages": (
                self._current_session.message_count 
                if self._current_session else 0
            ),
            "auto_save_enabled": self._auto_save_enabled,
            "last_save_time": (
                self._last_save_time.isoformat() 
                if self._last_save_time else None
            )
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

chat_session_manager = ChatSessionManager()


if __name__ == "__main__":
    # Test the session manager
    manager = ChatSessionManager()
    
    print(f"Stats: {manager.get_stats()}")
    
    # Start a new session
    session = manager.start_new_session("Test session")
    
    # Add some messages
    manager.add_message("user", "Hello NEXUS!")
    manager.add_message("assistant", "Hello! How can I help you today?", "joy", 0.6)
    manager.add_message("user", "Tell me about Python")
    manager.add_message("assistant", "Python is a versatile programming language!", "curiosity", 0.5)
    
    print(f"\nCurrent session messages: {len(manager.get_messages())}")
    
    # End and restore
    manager.end_current_session()
    
    # Try to restore
    restored = manager.restore_last_session()
    if restored:
        print(f"Restored session with {restored.message_count} messages")
        for msg in restored.messages:
            print(f"  [{msg.role}]: {msg.content[:50]}...")
    
    print(f"\nFinal stats: {manager.get_stats()}")