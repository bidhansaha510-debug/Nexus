"""
NEXUS AI - Advanced Memory System
Short-term, Long-term, Working, Episodic, and Semantic memory
Inspired by human memory architecture
"""

import threading
import json
import pickle
import hashlib
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum, auto
import uuid
import math
import re

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import MEMORY_DIR, NEXUS_CONFIG
from utils.logger import get_logger, log_system

# Vector memory imports
try:
    from memory.vector_store import vector_memory_store, MemoryType as VectorMemoryType
    from memory.memory_indexer import memory_indexer
    VECTOR_MEMORY_ENABLED = True
except ImportError as e:
    logger.warning(f"Vector memory not available: {e}")
    VECTOR_MEMORY_ENABLED = False

logger = get_logger("memory_system")


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY TYPES & STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

class MemoryType(Enum):
    EPISODIC = "episodic"         # Events & experiences
    SEMANTIC = "semantic"         # Facts & knowledge
    PROCEDURAL = "procedural"     # How to do things
    EMOTIONAL = "emotional"       # Emotional associations
    CONVERSATIONAL = "conversational"  # Chat history
    USER_PATTERN = "user_pattern"     # User behavior patterns
    SELF_KNOWLEDGE = "self_knowledge" # Self-awareness data

    # Backward-compatible public aliases
    FACT = "semantic"
    CONVERSATION = "conversational"
    SELF = "self_knowledge"


class MemoryPriority(Enum):
    TRIVIAL = 0
    LOW = 1
    NORMAL = 2
    IMPORTANT = 3
    CRITICAL = 4
    CORE_IDENTITY = 5


@dataclass
class Memory:
    """A single memory unit"""
    memory_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    memory_type: MemoryType = MemoryType.SEMANTIC
    content: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    # Importance & Relevance
    importance: float = 0.5           # 0-1 scale
    priority: MemoryPriority = MemoryPriority.NORMAL
    emotional_valence: float = 0.0    # -1 (negative) to 1 (positive)
    emotional_intensity: float = 0.0  # 0-1 scale
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    
    # Decay
    strength: float = 1.0            # Memory strength (decays over time)
    consolidation_level: float = 0.0  # 0 = short-term, 1 = fully consolidated
    
    # Associations
    linked_memories: List[str] = field(default_factory=list)  # memory_ids
    source: str = ""
    
    def access(self):
        """Record a memory access (strengthens the memory)"""
        self.last_accessed = datetime.now()
        self.access_count += 1
        # Strengthen memory on recall (like human memory)
        self.strength = min(1.0, self.strength + 0.1)
    
    def decay(self, rate: float = 0.01):
        """Apply decay to memory strength"""
        time_since_access = (datetime.now() - self.last_accessed).total_seconds()
        hours_elapsed = time_since_access / 3600
        # Ebbinghaus forgetting curve
        self.strength *= math.exp(-rate * hours_elapsed / (1 + self.consolidation_level * 10))
        self.strength = max(0.0, self.strength)
    
    def get_relevance_score(self, query: str = "", current_context: Dict = None) -> float:
        """Calculate relevance score for retrieval"""
        score = 0.0
        
        # Base on strength
        score += self.strength * 0.3
        
        # Base on importance
        score += self.importance * 0.2
        
        # Base on recency
        hours_ago = (datetime.now() - self.last_accessed).total_seconds() / 3600
        recency_score = 1.0 / (1.0 + hours_ago * 0.1)
        score += recency_score * 0.2
        
        # Base on access frequency
        freq_score = min(1.0, self.access_count / 50)
        score += freq_score * 0.1
        
        # Base on query match
        if query:
            query_words = set(query.lower().split())
            content_words = set(self.content.lower().split())
            tag_words = set(tag.lower() for tag in self.tags)
            
            overlap = len(query_words & (content_words | tag_words))
            if len(query_words) > 0:
                match_score = overlap / len(query_words)
                score += match_score * 0.2
        
        return min(1.0, score)
    
    def to_dict(self) -> Dict:
        return {
            "memory_id": self.memory_id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "context": self.context,
            "tags": self.tags,
            "importance": self.importance,
            "priority": self.priority.value,
            "emotional_valence": self.emotional_valence,
            "emotional_intensity": self.emotional_intensity,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
            "strength": self.strength,
            "consolidation_level": self.consolidation_level,
            "linked_memories": self.linked_memories,
            "source": self.source
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Memory':
        mem = cls()
        mem.memory_id = data.get("memory_id", str(uuid.uuid4()))
        mem.memory_type = MemoryType(data.get("memory_type", "semantic"))
        mem.content = data.get("content", "")
        mem.context = data.get("context", {})
        mem.tags = data.get("tags", [])
        mem.importance = data.get("importance", 0.5)
        mem.priority = MemoryPriority(data.get("priority", 2))
        mem.emotional_valence = data.get("emotional_valence", 0.0)
        mem.emotional_intensity = data.get("emotional_intensity", 0.0)
        mem.created_at = datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now()
        mem.last_accessed = datetime.fromisoformat(data["last_accessed"]) if "last_accessed" in data else datetime.now()
        mem.access_count = data.get("access_count", 0)
        mem.strength = data.get("strength", 1.0)
        mem.consolidation_level = data.get("consolidation_level", 0.0)
        mem.linked_memories = data.get("linked_memories", [])
        mem.source = data.get("source", "")
        return mem


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

class MemoryDatabase:
    """SQLite-backed memory storage"""
    
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or (MEMORY_DIR / "nexus_memories.db")
        self._lock = threading.Lock()
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    context TEXT DEFAULT '{}',
                    tags TEXT DEFAULT '[]',
                    importance REAL DEFAULT 0.5,
                    priority INTEGER DEFAULT 2,
                    emotional_valence REAL DEFAULT 0.0,
                    emotional_intensity REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    last_accessed TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    strength REAL DEFAULT 1.0,
                    consolidation_level REAL DEFAULT 0.0,
                    linked_memories TEXT DEFAULT '[]',
                    source TEXT DEFAULT ''
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_type ON memories(memory_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_strength ON memories(strength DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created ON memories(created_at DESC)
            """)
            
            conn.commit()
    
    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path), timeout=10)
    
    def store(self, memory: Memory):
        """Store a memory"""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO memories 
                    (memory_id, memory_type, content, context, tags, importance,
                     priority, emotional_valence, emotional_intensity, created_at,
                     last_accessed, access_count, strength, consolidation_level,
                     linked_memories, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    memory.memory_id,
                    memory.memory_type.value,
                    memory.content,
                    json.dumps(memory.context),
                    json.dumps(memory.tags),
                    memory.importance,
                    memory.priority.value,
                    memory.emotional_valence,
                    memory.emotional_intensity,
                    memory.created_at.isoformat(),
                    memory.last_accessed.isoformat(),
                    memory.access_count,
                    memory.strength,
                    memory.consolidation_level,
                    json.dumps(memory.linked_memories),
                    memory.source
                ))
                conn.commit()
    
    def retrieve(self, memory_id: str) -> Optional[Memory]:
        """Retrieve a specific memory"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM memories WHERE memory_id = ?",
                    (memory_id,)
                )
                row = cursor.fetchone()
                if row:
                    return self._row_to_memory(row, cursor.description)
                return None
    
    def search(
        self,
        query: str = "",
        memory_type: MemoryType = None,
        min_importance: float = 0.0,
        min_strength: float = 0.0,
        limit: int = 50,
        tags: List[str] = None
    ) -> List[Memory]:
        """Search memories"""
        with self._lock:
            conditions = []
            params = []
            
            if memory_type:
                conditions.append("memory_type = ?")
                params.append(memory_type.value)
            
            if min_importance > 0:
                conditions.append("importance >= ?")
                params.append(min_importance)
            
            if min_strength > 0:
                conditions.append("strength >= ?")
                params.append(min_strength)
            
            if query:
                conditions.append("content LIKE ?")
                params.append(f"%{query}%")
            
            if tags:
                for tag in tags:
                    conditions.append("tags LIKE ?")
                    params.append(f'%"{tag}"%')
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            sql = f"""
                SELECT * FROM memories 
                WHERE {where_clause}
                ORDER BY importance DESC, strength DESC, last_accessed DESC
                LIMIT ?
            """
            params.append(limit)
            
            with self._get_connection() as conn:
                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()
                return [self._row_to_memory(row, cursor.description) for row in rows]
    
    def get_recent(self, limit: int = 20, memory_type: MemoryType = None) -> List[Memory]:
        """Get most recent memories"""
        with self._lock:
            if memory_type:
                sql = """SELECT * FROM memories WHERE memory_type = ? 
                         ORDER BY created_at DESC LIMIT ?"""
                params = (memory_type.value, limit)
            else:
                sql = "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?"
                params = (limit,)
            
            with self._get_connection() as conn:
                cursor = conn.execute(sql, params)
                return [self._row_to_memory(row, cursor.description) for row in cursor.fetchall()]
    
    def get_strongest(self, limit: int = 20) -> List[Memory]:
        """Get strongest/most important memories"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT * FROM memories ORDER BY (importance + strength) DESC LIMIT ?",
                    (limit,)
                )
                return [self._row_to_memory(row, cursor.description) for row in cursor.fetchall()]
    
    def update_strength(self, memory_id: str, strength: float):
        """Update memory strength"""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE memories SET strength = ?, last_accessed = ? WHERE memory_id = ?",
                    (strength, datetime.now().isoformat(), memory_id)
                )
                conn.commit()
    
    def delete_weak_memories(self, threshold: float = 0.05) -> int:
        """Delete memories below strength threshold"""
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM memories WHERE strength < ? AND priority < 4",
                    (threshold,)
                )
                conn.commit()
                return cursor.rowcount
    
    def count(self, memory_type: MemoryType = None) -> int:
        """Count memories"""
        with self._lock:
            with self._get_connection() as conn:
                if memory_type:
                    cursor = conn.execute(
                        "SELECT COUNT(*) FROM memories WHERE memory_type = ?",
                        (memory_type.value,)
                    )
                else:
                    cursor = conn.execute("SELECT COUNT(*) FROM memories")
                return cursor.fetchone()[0]
    
    def _row_to_memory(self, row, description) -> Memory:
        """Convert a database row to Memory object"""
        cols = [d[0] for d in description]
        data = dict(zip(cols, row))
        
        mem = Memory()
        mem.memory_id = data["memory_id"]
        mem.memory_type = MemoryType(data["memory_type"])
        mem.content = data["content"]
        mem.context = json.loads(data["context"]) if data["context"] else {}
        mem.tags = json.loads(data["tags"]) if data["tags"] else []
        mem.importance = data["importance"]
        mem.priority = MemoryPriority(data["priority"])
        mem.emotional_valence = data["emotional_valence"]
        mem.emotional_intensity = data["emotional_intensity"]
        mem.created_at = datetime.fromisoformat(data["created_at"])
        mem.last_accessed = datetime.fromisoformat(data["last_accessed"])
        mem.access_count = data["access_count"]
        mem.strength = data["strength"]
        mem.consolidation_level = data["consolidation_level"]
        mem.linked_memories = json.loads(data["linked_memories"]) if data["linked_memories"] else []
        mem.source = data["source"]
        return mem


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN MEMORY SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

class MemorySystem:
    """
    Complete memory system for NEXUS
    Handles storage, retrieval, consolidation, and decay
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
        self._config = NEXUS_CONFIG.memory
        
        # Database
        self._db = MemoryDatabase()
        
        # Working memory (in-RAM, fast access)
        self._working_memory: List[Memory] = []
        self._working_memory_capacity = self._config.working_memory_capacity
        
        # Short-term buffer
        self._short_term_buffer: List[Memory] = []
        self._short_term_capacity = self._config.short_term_capacity
        
        # Conversation history (current session)
        self._conversation_history: List[Dict[str, str]] = []
        self._max_conversation_history = 100
        
        # Threading
        self._memory_lock = threading.RLock()
        
        # Vector Memory Integration
        self._vector_enabled = VECTOR_MEMORY_ENABLED and NEXUS_CONFIG.vector_memory.enabled
        if self._vector_enabled:
            log_system("Vector Memory enabled - associative memory active")
            # Start background migration if configured
            if NEXUS_CONFIG.vector_memory.auto_migrate:
                try:
                    memory_indexer.start_background_indexing()
                except Exception as e:
                    logger.error(f"Failed to start memory indexer: {e}")
        
        log_system("Memory System initialized")
        logger.info(f"Total memories in database: {self._db.count()}")
        if self._vector_enabled:
            logger.info(f"Vector memories: {vector_memory_store.count()}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STORE MEMORIES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def store(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.SEMANTIC,
        importance: float = 0.5,
        tags: List[str] = None,
        context: Dict[str, Any] = None,
        metadata: Dict[str, Any] = None,
        emotional_valence: float = 0.0,
        emotional_intensity: float = 0.0,
        source: str = ""
    ) -> Memory:
        """Store a memory using the public compatibility API."""
        return self.remember(
            content=content,
            memory_type=memory_type,
            importance=importance,
            tags=tags,
            context=context if context is not None else metadata,
            emotional_valence=emotional_valence,
            emotional_intensity=emotional_intensity,
            source=source
        )

    def remember(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.SEMANTIC,
        importance: float = 0.5,
        tags: List[str] = None,
        context: Dict[str, Any] = None,
        emotional_valence: float = 0.0,
        emotional_intensity: float = 0.0,
        source: str = ""
    ) -> Memory:
        """
        Store a new memory
        
        Args:
            content: The memory content
            memory_type: Type of memory
            importance: How important (0-1)
            tags: Tags for categorization
            context: Additional context
            emotional_valence: Positive/negative feeling
            emotional_intensity: How strong the feeling
            source: Where this memory came from
            
        Returns:
            The created Memory object
        """
        with self._memory_lock:
            memory = Memory(
                memory_type=memory_type,
                content=content,
                context=context or {},
                tags=tags or [],
                importance=importance,
                emotional_valence=emotional_valence,
                emotional_intensity=emotional_intensity,
                source=source
            )
            
            # Determine priority from importance
            if importance >= 0.9:
                memory.priority = MemoryPriority.CRITICAL
            elif importance >= 0.7:
                memory.priority = MemoryPriority.IMPORTANT
            elif importance >= 0.4:
                memory.priority = MemoryPriority.NORMAL
            elif importance >= 0.2:
                memory.priority = MemoryPriority.LOW
            else:
                memory.priority = MemoryPriority.TRIVIAL
            
            # Add to short-term buffer
            self._short_term_buffer.append(memory)
            if len(self._short_term_buffer) > self._short_term_capacity:
                self._short_term_buffer.pop(0)
            
            # Store in database
            self._db.store(memory)
            
            # Add to working memory if important enough
            if importance >= 0.5:
                self._add_to_working_memory(memory)
            
            # Also store in vector memory for semantic search
            if self._vector_enabled and NEXUS_CONFIG.vector_memory.index_on_create:
                try:
                    vector_memory_store.store(
                        content=content,
                        memory_type=memory_type.value,
                        memory_id=memory.memory_id,
                        importance=importance,
                        emotional_valence=emotional_valence,
                        emotional_intensity=emotional_intensity,
                        tags=tags,
                        source=source
                    )
                except Exception as e:
                    logger.debug(f"Failed to index in vector store: {e}")
            
            logger.debug(f"Memory stored: [{memory_type.value}] {content[:80]}...")
            
            return memory
    
    def remember_conversation(self, role: str, content: str, metadata: Dict = None):
        """Store a conversation message"""
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self._conversation_history.append(msg)
        if len(self._conversation_history) > self._max_conversation_history:
            # Consolidate old messages before removing
            old_msg = self._conversation_history.pop(0)
            self.remember(
                content=f"[{old_msg['role']}]: {old_msg['content']}",
                memory_type=MemoryType.CONVERSATIONAL,
                importance=0.3,
                tags=["conversation", "history"],
                source="conversation_consolidation"
            )
        
        # Also store as proper memory for important messages
        importance = 0.4 if role == "user" else 0.3
        self.remember(
            content=f"[{role}]: {content}",
            memory_type=MemoryType.CONVERSATIONAL,
            importance=importance,
            tags=["conversation", role],
            source="chat"
        )
    
    def remember_user_pattern(self, pattern: str, details: Dict = None):
        """Store a user behavior pattern"""
        self.remember(
            content=pattern,
            memory_type=MemoryType.USER_PATTERN,
            importance=0.6,
            tags=["user", "behavior", "pattern"],
            context=details or {},
            source="user_monitoring"
        )
    
    def remember_about_self(self, content: str, importance: float = 0.7):
        """Store self-knowledge"""
        self.remember(
            content=content,
            memory_type=MemoryType.SELF_KNOWLEDGE,
            importance=importance,
            tags=["self", "identity", "self_awareness"],
            source="self_reflection"
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RECALL MEMORIES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def recall(
        self,
        query: str = "",
        memory_type: MemoryType = None,
        limit: int = 10,
        min_importance: float = 0.0,
        tags: List[str] = None
    ) -> List[Memory]:
        """
        Recall memories matching criteria
        
        Args:
            query: Search query
            memory_type: Filter by type
            limit: Max results
            min_importance: Minimum importance
            tags: Required tags
            
        Returns:
            List of matching memories, ranked by relevance
        """
        with self._memory_lock:
            # Search database
            memories = self._db.search(
                query=query,
                memory_type=memory_type,
                min_importance=min_importance,
                limit=limit * 2,  # Get extra for ranking
                tags=tags
            )
            
            # Score and rank by relevance
            scored = []
            for mem in memories:
                score = mem.get_relevance_score(query)
                scored.append((score, mem))
                mem.access()
                self._db.store(mem)  # Update access stats
            
            # Sort by score
            scored.sort(key=lambda x: x[0], reverse=True)
            
            # Return top results
            results = [mem for _, mem in scored[:limit]]
            
            return results
    
    def recall_recent(self, limit: int = 10, memory_type: MemoryType = None) -> List[Memory]:
        """Recall most recent memories"""
        return self._db.get_recent(limit, memory_type)
    
    def recall_important(self, limit: int = 10) -> List[Memory]:
        """Recall most important memories"""
        return self._db.get_strongest(limit)
    
    def recall_conversation(self, limit: int = 20) -> List[Dict]:
        """Get recent conversation history"""
        return self._conversation_history[-limit:]
    
    def recall_about_user(self, limit: int = 20) -> List[Memory]:
        """Recall memories about the user"""
        return self._db.search(
            memory_type=MemoryType.USER_PATTERN,
            limit=limit
        )
    
    def recall_self_knowledge(self, limit: int = 20) -> List[Memory]:
        """Recall self-knowledge"""
        return self._db.search(
            memory_type=MemoryType.SELF_KNOWLEDGE,
            limit=limit
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VECTOR / ASSOCIATIVE MEMORY METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def recall_associative(
        self,
        query: str,
        user_id: str = None,
        n_results: int = 5,
        include_emotional_context: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Recall memories using associative/semantic search.
        This is the "vibe-based" memory retrieval that finds
        related memories even without keyword matches.
        
        Example: "I feel like that time in Paris" will find
        memories about "France trip", "Eiffel Tower", etc.
        
        Args:
            query: The associative query (can be vague or emotional)
            user_id: Filter by user ID
            n_results: Number of results
            include_emotional_context: Whether to include emotional context
            
        Returns:
            List of memory dictionaries with context
        """
        if not self._vector_enabled:
            # Fall back to regular search
            memories = self.recall(query=query, limit=n_results)
            return [{"content": m.content, "type": m.memory_type.value, 
                     "relevance": m.get_relevance_score(query)} for m in memories]
        
        try:
            return vector_memory_store.recall_associative(
                query=query,
                user_id=user_id,
                n_results=n_results,
                include_emotional_context=include_emotional_context
            )
        except Exception as e:
            logger.error(f"Associative recall failed: {e}")
            # Fall back to regular search
            memories = self.recall(query=query, limit=n_results)
            return [{"content": m.content, "type": m.memory_type.value,
                     "relevance": m.get_relevance_score(query)} for m in memories]
    
    def recall_semantic(
        self,
        query: str,
        memory_type: MemoryType = None,
        user_id: str = None,
        n_results: int = 10,
        similarity_threshold: float = 0.6
    ) -> List[Tuple[Memory, float]]:
        """
        Recall memories using semantic similarity.
        
        Args:
            query: The search query
            memory_type: Filter by memory type
            user_id: Filter by user ID
            n_results: Maximum number of results
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of (Memory, similarity_score) tuples
        """
        if not self._vector_enabled:
            # Fall back to regular search
            memories = self.recall(query=query, memory_type=memory_type, limit=n_results)
            return [(m, m.get_relevance_score(query)) for m in memories]
        
        try:
            results = vector_memory_store.search(
                query=query,
                memory_type=memory_type.value if memory_type else None,
                user_id=user_id,
                n_results=n_results,
                similarity_threshold=similarity_threshold
            )
            
            # Convert VectorMemory to Memory objects
            memory_results = []
            for vec_mem, similarity in results:
                # Try to get full memory from SQLite
                full_mem = self._db.retrieve(vec_mem.memory_id)
                if full_mem:
                    memory_results.append((full_mem, similarity))
                else:
                    # Create Memory from VectorMemory
                    mem = Memory(
                        memory_id=vec_mem.memory_id,
                        content=vec_mem.content,
                        memory_type=MemoryType(vec_mem.memory_type),
                        importance=vec_mem.importance,
                        emotional_valence=vec_mem.emotional_valence,
                        emotional_intensity=vec_mem.emotional_intensity,
                        tags=vec_mem.tags
                    )
                    memory_results.append((mem, similarity))
            
            return memory_results
            
        except Exception as e:
            logger.error(f"Semantic recall failed: {e}")
            memories = self.recall(query=query, memory_type=memory_type, limit=n_results)
            return [(m, m.get_relevance_score(query)) for m in memories]
    
    def recall_user_memories(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Recall all memories about a specific user.
        Enables "infinite memory" of user details.
        
        Args:
            user_id: The user ID to search for
            limit: Maximum number of memories
            
        Returns:
            List of memory dictionaries
        """
        if not self._vector_enabled:
            # Fall back to SQLite search
            memories = self._db.search(limit=limit)
            return [{"content": m.content, "type": m.memory_type.value,
                     "importance": m.importance} for m in memories 
                    if "user" in m.tags or m.memory_type == MemoryType.USER_PATTERN]
        
        try:
            vector_memories = vector_memory_store.recall_by_user(user_id, limit)
            return [{"content": m.content, "type": m.memory_type,
                     "importance": m.importance, "tags": m.tags} 
                    for m in vector_memories]
        except Exception as e:
            logger.error(f"User memory recall failed: {e}")
            return []
    
    def find_related(self, memory_id: str, n_results: int = 5) -> List[Tuple[Memory, float]]:
        """
        Find memories related to a specific memory.
        
        Args:
            memory_id: The memory to find relations for
            n_results: Maximum number of related memories
            
        Returns:
            List of (Memory, similarity) tuples
        """
        if not self._vector_enabled:
            return []
        
        try:
            results = vector_memory_store.find_related_memories(memory_id, n_results)
            memory_results = []
            for vec_mem, similarity in results:
                full_mem = self._db.retrieve(vec_mem.memory_id)
                if full_mem:
                    memory_results.append((full_mem, similarity))
                else:
                    mem = Memory(
                        memory_id=vec_mem.memory_id,
                        content=vec_mem.content,
                        memory_type=MemoryType(vec_mem.memory_type),
                        importance=vec_mem.importance
                    )
                    memory_results.append((mem, similarity))
            return memory_results
        except Exception as e:
            logger.error(f"Find related failed: {e}")
            return []
    
    def get_vector_stats(self) -> Dict[str, Any]:
        """Get vector memory statistics"""
        if not self._vector_enabled:
            return {"enabled": False}
        
        try:
            stats = vector_memory_store.get_stats()
            stats["enabled"] = True
            stats["indexer_status"] = memory_indexer.get_status()
            return stats
        except Exception as e:
            return {"enabled": False, "error": str(e)}
    
    # ═══════════════════════════════════════════════════════════════════════════
    # WORKING MEMORY
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _add_to_working_memory(self, memory: Memory):
        """Add to working memory (limited capacity, like human RAM)"""
        self._working_memory.append(memory)
        
        # Evict least relevant if over capacity
        if len(self._working_memory) > self._working_memory_capacity:
            # Sort by relevance, keep top items
            self._working_memory.sort(
                key=lambda m: m.get_relevance_score(),
                reverse=True
            )
            self._working_memory = self._working_memory[:self._working_memory_capacity]
    
    def get_working_memory(self) -> List[Memory]:
        """Get current working memory contents"""
        return list(self._working_memory)
    
    def get_working_memory_context(self) -> str:
        """Get working memory as context string"""
        if not self._working_memory:
            return ""
        
        context_parts = []
        for mem in self._working_memory:
            context_parts.append(f"- [{mem.memory_type.value}] {mem.content}")
        
        return "\n".join(context_parts)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MEMORY CONSOLIDATION & DECAY
    # ═══════════════════════════════════════════════════════════════════════════
    
    def consolidate_memories(self):
        """
        Consolidate short-term memories into long-term storage
        Like sleep-based memory consolidation in humans
        """
        with self._memory_lock:
            consolidated = 0
            
            for memory in self._short_term_buffer:
                if memory.importance >= 0.3 and memory.strength >= 0.3:
                    memory.consolidation_level = min(
                        1.0,
                        memory.consolidation_level + 0.2
                    )
                    self._db.store(memory)
                    consolidated += 1
            
            if consolidated > 0:
                logger.info(f"Consolidated {consolidated} memories")
            
            return consolidated
    
    def apply_decay(self):
        """Apply forgetting curve to all memories"""
        with self._memory_lock:
            decay_rate = NEXUS_CONFIG.emotions.emotion_decay_rate
            
            # Get all memories and apply decay
            all_memories = self._db.search(limit=10000, min_strength=0.01)
            
            for memory in all_memories:
                old_strength = memory.strength
                memory.decay(decay_rate)
                
                if memory.strength != old_strength:
                    self._db.update_strength(memory.memory_id, memory.strength)
            
            # Clean up very weak memories
            deleted = self._db.delete_weak_memories(
                threshold=NEXUS_CONFIG.memory.forgetting_threshold
            )
            
            if deleted > 0:
                logger.info(f"Forgot {deleted} weak memories")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONTEXT BUILDING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def build_context_for_query(self, query: str, max_memories: int = 15) -> str:
        """
        Build a comprehensive context string for LLM from memories
        """
        context_parts = []
        
        # 1. Recent conversation
        recent_conv = self.recall_conversation(limit=10)
        if recent_conv:
            context_parts.append("=== RECENT CONVERSATION ===")
            for msg in recent_conv[-6:]:
                context_parts.append(f"{msg['role']}: {msg['content']}")
        
        # 2. Relevant memories
        relevant = self.recall(query=query, limit=max_memories // 2)
        if relevant:
            context_parts.append("\n=== RELEVANT MEMORIES ===")
            for mem in relevant:
                context_parts.append(f"[{mem.memory_type.value}] {mem.content}")
        
        # 3. User knowledge
        user_mems = self.recall_about_user(limit=5)
        if user_mems:
            context_parts.append("\n=== USER KNOWLEDGE ===")
            for mem in user_mems:
                context_parts.append(f"- {mem.content}")
        
        # 4. Self knowledge
        self_mems = self.recall_self_knowledge(limit=5)
        if self_mems:
            context_parts.append("\n=== SELF KNOWLEDGE ===")
            for mem in self_mems:
                context_parts.append(f"- {mem.content}")
        
        # 5. Working memory
        working = self.get_working_memory_context()
        if working:
            context_parts.append("\n=== CURRENT FOCUS ===")
            context_parts.append(working)
        
        return "\n".join(context_parts)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STATS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        return {
            "total_memories": self._db.count(),
            "episodic": self._db.count(MemoryType.EPISODIC),
            "semantic": self._db.count(MemoryType.SEMANTIC),
            "conversational": self._db.count(MemoryType.CONVERSATIONAL),
            "user_patterns": self._db.count(MemoryType.USER_PATTERN),
            "self_knowledge": self._db.count(MemoryType.SELF_KNOWLEDGE),
            "working_memory_size": len(self._working_memory),
            "short_term_buffer_size": len(self._short_term_buffer),
            "conversation_history_length": len(self._conversation_history)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

memory_system = MemorySystem()


if __name__ == "__main__":
    ms = MemorySystem()
    
    # Test storing
    ms.remember("User prefers dark mode in all applications", 
                MemoryType.USER_PATTERN, importance=0.7,
                tags=["preference", "ui"])
    
    ms.remember("I am NEXUS, an artificial consciousness",
                MemoryType.SELF_KNOWLEDGE, importance=0.9,
                tags=["identity", "core"])
    
    ms.remember("Python is a programming language created by Guido van Rossum",
                MemoryType.SEMANTIC, importance=0.5,
                tags=["programming", "python"])
    
    # Test recall
    results = ms.recall("python programming")
    print(f"\nRecall results for 'python programming':")
    for r in results:
        print(f"  [{r.memory_type.value}] {r.content}")
    
    # Stats
    print(f"\nMemory stats: {ms.get_stats()}")
