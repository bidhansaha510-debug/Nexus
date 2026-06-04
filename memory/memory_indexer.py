"""
NEXUS AI - Memory Indexer
Background service for indexing and migrating memories to vector store
"""

import threading
import time
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DATA_DIR, MEMORY_DIR, NEXUS_CONFIG
from utils.logger import get_logger, log_system
from memory.vector_store import vector_memory_store, MemoryType

logger = get_logger("memory_indexer")


class MemoryIndexer:
    """
    Background service that indexes memories into the vector store.
    
    Features:
    - Migrate existing SQLite memories to ChromaDB
    - Auto-index new memories as they're created
    - Periodic reindexing for optimization
    - Track indexing progress and status
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
        self._running = False
        self._index_thread: Optional[threading.Thread] = None
        
        # Status tracking
        self._indexed_count = 0
        self._error_count = 0
        self._last_index_time: Optional[datetime] = None
        self._index_status = "idle"
        
        # Configuration
        self._batch_size = 100
        self._index_interval = 3600  # 1 hour between reindex checks
        
        logger.info("MemoryIndexer initialized")
    
    def start_background_indexing(self):
        """Start the background indexing thread"""
        if self._running:
            logger.warning("Memory indexer already running")
            return
        
        # Check if vector store already has enough data
        try:
            existing_count = vector_memory_store.count()
            if existing_count > 100:
                logger.info(f"Vector store already has {existing_count} memories, skipping migration")
                return
        except Exception as e:
            logger.debug(f"Could not check vector store: {e}")
        
        self._running = True
        self._index_thread = threading.Thread(
            target=self._indexing_loop,
            daemon=True,
            name="MemoryIndexer"
        )
        self._index_thread.start()
        log_system("Memory indexer started")
    
    def stop_background_indexing(self):
        """Stop the background indexing thread"""
        self._running = False
        if self._index_thread:
            self._index_thread.join(timeout=5)
        logger.info("Memory indexer stopped")
    
    def _indexing_loop(self):
        """Main indexing loop"""
        # Initial migration on startup
        self.migrate_sqlite_memories()
        
        while self._running:
            try:
                time.sleep(self._index_interval)
                
                if self._running:
                    # Periodic maintenance
                    self._reindex_check()
                    
            except Exception as e:
                logger.error(f"Error in indexing loop: {e}")
                time.sleep(60)
    
    def migrate_sqlite_memories(self):
        """
        Migrate existing SQLite memories to the vector store.
        Reads from the nexus_memories.db SQLite database.
        """
        self._index_status = "migrating"
        logger.info("Starting SQLite to ChromaDB migration...")
        
        db_path = MEMORY_DIR / "nexus_memories.db"
        if not db_path.exists():
            logger.info("No SQLite memory database found, skipping migration")
            self._index_status = "idle"
            return
        
        try:
            import sqlite3
            
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get total count
            cursor.execute("SELECT COUNT(*) FROM memories")
            total = cursor.fetchone()[0]
            
            if total == 0:
                logger.info("No memories to migrate")
                conn.close()
                self._index_status = "idle"
                return
            
            logger.info(f"Found {total} memories to migrate")
            
            # Get the current vector store count to avoid duplicates
            existing_count = vector_memory_store.count()
            
            # Fetch all memories
            cursor.execute("""
                SELECT memory_id, memory_type, content, context, tags,
                       importance, priority, emotional_valence, emotional_intensity,
                       created_at, last_accessed, access_count, strength,
                       consolidation_level, linked_memories, source
                FROM memories
                ORDER BY created_at DESC
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            # Process in batches
            batch = []
            processed = 0
            
            for row in rows:
                try:
                    # Skip if already indexed (check by memory_id)
                    existing = vector_memory_store.get(row["memory_id"])
                    if existing:
                        continue
                    
                    # Parse JSON fields
                    context = json.loads(row["context"]) if row["context"] else {}
                    tags = json.loads(row["tags"]) if row["tags"] else []
                    
                    # Map memory type
                    memory_type = row["memory_type"]
                    if memory_type == "episodic":
                        mt = MemoryType.EPISODIC
                    elif memory_type == "semantic":
                        mt = MemoryType.SEMANTIC
                    elif memory_type == "conversational":
                        mt = MemoryType.CONVERSATIONAL
                    elif memory_type == "user_pattern":
                        mt = MemoryType.USER_PATTERN
                    elif memory_type == "self_knowledge":
                        mt = MemoryType.SELF_KNOWLEDGE
                    elif memory_type == "emotional":
                        mt = MemoryType.EMOTIONAL
                    else:
                        mt = MemoryType.SEMANTIC
                    
                    # Add to vector store
                    vector_memory_store.store(
                        content=row["content"],
                        memory_type=mt,
                        memory_id=row["memory_id"],
                        importance=row["importance"],
                        emotional_valence=row["emotional_valence"],
                        emotional_intensity=row["emotional_intensity"],
                        tags=tags,
                        source=row["source"] or "migration",
                        context=context
                    )
                    
                    processed += 1
                    self._indexed_count += 1
                    
                    if processed % 50 == 0:
                        logger.info(f"Migrated {processed} memories...")
                    
                except Exception as e:
                    logger.error(f"Error migrating memory {row['memory_id']}: {e}")
                    self._error_count += 1
            
            self._last_index_time = datetime.now()
            self._index_status = "idle"
            
            logger.info(f"Migration complete. Migrated {processed} memories, {self._error_count} errors")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self._index_status = "error"
    
    def _reindex_check(self):
        """Check if reindexing is needed"""
        # For now, just log stats
        stats = vector_memory_store.get_stats()
        logger.info(f"Vector store stats: {stats['total_memories']} memories indexed")
    
    def index_memory(
        self,
        content: str,
        memory_type: str = MemoryType.SEMANTIC,
        memory_id: str = None,
        importance: float = 0.5,
        emotional_valence: float = 0.0,
        emotional_intensity: float = 0.0,
        tags: List[str] = None,
        source: str = "",
        user_id: str = None,
        context: Dict[str, Any] = None
    ) -> bool:
        """
        Index a single memory into the vector store.
        
        Args:
            content: Memory content
            memory_type: Type of memory
            memory_id: Optional memory ID
            importance: Importance score
            emotional_valence: Emotional tone
            emotional_intensity: Emotion strength
            tags: Tags for categorization
            source: Memory source
            user_id: Associated user
            context: Additional context
            
        Returns:
            True if indexed successfully
        """
        try:
            vector_memory_store.store(
                content=content,
                memory_type=memory_type,
                memory_id=memory_id,
                importance=importance,
                emotional_valence=emotional_valence,
                emotional_intensity=emotional_intensity,
                tags=tags,
                source=source,
                user_id=user_id,
                context=context
            )
            self._indexed_count += 1
            return True
            
        except Exception as e:
            logger.error(f"Failed to index memory: {e}")
            self._error_count += 1
            return False
    
    def index_batch(self, memories: List[Dict[str, Any]], show_progress: bool = False) -> int:
        """
        Index multiple memories in batch.
        
        Args:
            memories: List of memory dictionaries
            show_progress: Whether to show progress
            
        Returns:
            Number of successfully indexed memories
        """
        indexed = 0
        
        for i, mem in enumerate(memories):
            if show_progress and i % 100 == 0:
                logger.info(f"Indexing batch: {i}/{len(memories)}")
            
            if self.index_memory(**mem):
                indexed += 1
        
        self._last_index_time = datetime.now()
        return indexed
    
    def index_conversation(
        self,
        role: str,
        content: str,
        user_id: str = None,
        emotion: str = "neutral",
        intensity: float = 0.5
    ):
        """
        Index a conversation message.
        
        Args:
            role: 'user' or 'assistant'
            content: Message content
            user_id: User ID
            emotion: Associated emotion
            intensity: Emotion intensity
        """
        # Map emotion to valence
        emotion_valences = {
            "joy": 0.8, "happiness": 0.7, "contentment": 0.5,
            "sadness": -0.6, "anger": -0.8, "fear": -0.7,
            "anxiety": -0.5, "neutral": 0.0, "curiosity": 0.3,
            "excitement": 0.8, "love": 0.9, "empathy": 0.6
        }
        
        valence = emotion_valences.get(emotion.lower(), 0.0)
        
        self.index_memory(
            content=f"[{role}]: {content}",
            memory_type=MemoryType.CONVERSATIONAL,
            importance=0.4 if role == "user" else 0.3,
            emotional_valence=valence,
            emotional_intensity=intensity,
            tags=["conversation", role, emotion],
            source="chat",
            user_id=user_id
        )
    
    def index_user_fact(
        self,
        fact: str,
        user_id: str,
        importance: float = 0.6,
        category: str = "general"
    ):
        """
        Index a fact about a user.
        
        Args:
            fact: The fact to remember
            user_id: User ID
            importance: Importance score
            category: Category tag
        """
        self.index_memory(
            content=fact,
            memory_type=MemoryType.USER_PATTERN,
            importance=importance,
            tags=["user_fact", category],
            source="user_profile",
            user_id=user_id
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get indexing status"""
        return {
            "status": self._index_status,
            "indexed_count": self._indexed_count,
            "error_count": self._error_count,
            "last_index_time": self._last_index_time.isoformat() if self._last_index_time else None,
            "running": self._running,
            "vector_store_stats": vector_memory_store.get_stats()
        }
    
    def reindex_all(self):
        """Force a complete reindex of all memories"""
        logger.info("Starting full reindex...")
        
        # Clear existing vector store
        vector_memory_store.clear_all()
        
        # Reset counters
        self._indexed_count = 0
        self._error_count = 0
        
        # Migrate from SQLite
        self.migrate_sqlite_memories()


# Global instance
memory_indexer = MemoryIndexer()


if __name__ == "__main__":
    # Test the indexer
    indexer = MemoryIndexer()
    
    print("Starting migration...")
    indexer.migrate_sqlite_memories()
    
    print(f"\nStatus: {indexer.get_status()}")
    
    # Test indexing a conversation
    indexer.index_conversation(
        role="user",
        content="I really enjoy playing guitar in my free time",
        user_id="test_user",
        emotion="joy",
        intensity=0.7
    )
    
    indexer.index_conversation(
        role="assistant",
        content="That's wonderful! Music is such a fulfilling hobby.",
        user_id="test_user",
        emotion="empathy",
        intensity=0.6
    )
    
    # Test indexing a user fact
    indexer.index_user_fact(
        fact="User's favorite color is blue",
        user_id="test_user",
        importance=0.5,
        category="preference"
    )
    
    print(f"\nFinal status: {indexer.get_status()}")