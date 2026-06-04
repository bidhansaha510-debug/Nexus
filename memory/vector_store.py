"""
NEXUS AI - Vector Memory Store
ChromaDB-backed associative memory with semantic search
Enables "infinite memory" through semantic similarity retrieval
"""

import threading
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import uuid

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DATA_DIR, NEXUS_CONFIG
from utils.logger import get_logger, log_system
from memory.embeddings import embedding_service

logger = get_logger("vector_store")


# ═══════════════════════════════════════════════════════════════════════════════
# MEMORY TYPES (mirrored from core/memory_system.py for independence)
# ═══════════════════════════════════════════════════════════════════════════════

class MemoryType:
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    EMOTIONAL = "emotional"
    CONVERSATIONAL = "conversational"
    USER_PATTERN = "user_pattern"
    SELF_KNOWLEDGE = "self_knowledge"


@dataclass
class VectorMemory:
    """A memory entry in the vector store"""
    memory_id: str
    content: str
    memory_type: str
    embedding: List[float] = field(default_factory=list)
    
    # Metadata
    importance: float = 0.5
    emotional_valence: float = 0.0
    emotional_intensity: float = 0.0
    tags: List[str] = field(default_factory=list)
    source: str = ""
    
    # User association (for multi-user support)
    user_id: Optional[str] = None
    
    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_accessed: str = field(default_factory=lambda: datetime.now().isoformat())
    access_count: int = 0
    
    # Context window
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "memory_type": self.memory_type,
            "importance": self.importance,
            "emotional_valence": self.emotional_valence,
            "emotional_intensity": self.emotional_intensity,
            "tags": self.tags,
            "source": self.source,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "context": self.context
        }


# ═══════════════════════════════════════════════════════════════════════════════
# VECTOR MEMORY STORE
# ═══════════════════════════════════════════════════════════════════════════════

class VectorMemoryStore:
    """
    ChromaDB-backed vector memory store for associative memory.
    
    Key Features:
    - Semantic similarity search (find "Paris trip" when searching "France vacation")
    - User-scoped memories for multi-user support
    - Automatic memory linking based on similarity
    - Persistent storage with ChromaDB
    - Infinite memory capacity with intelligent retrieval
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
        self._persist_dir = DATA_DIR / "vector_store"
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        
        # ChromaDB client (lazy initialized)
        self._client = None
        self._collections: Dict[str, Any] = {}
        
        # Thread safety
        self._store_lock = threading.RLock()
        
        # Configuration
        self._similarity_threshold = 0.7
        self._max_results = 20
        
        logger.info(f"VectorMemoryStore initialized. Persist dir: {self._persist_dir}")
    
    def _get_client(self):
        """Lazy initialize ChromaDB client"""
        if self._client is not None:
            return self._client
            
        try:
            import chromadb
            from chromadb.config import Settings
            import shutil
            
            # Try to create client and test connection
            def try_create_client(path, reset=False):
                if reset and Path(path).exists():
                    logger.warning(f"Resetting ChromaDB at {path}")
                    shutil.rmtree(path)
                    Path(path).mkdir(parents=True, exist_ok=True)
                
                client = chromadb.PersistentClient(
                    path=str(path),
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True,
                        is_persistent=True
                    )
                )
                # Test connection with heartbeat
                client.heartbeat()
                return client
            
            # First try: normal initialization
            try:
                self._client = try_create_client(self._persist_dir, reset=False)
                logger.info("ChromaDB client initialized")
                return self._client
            except Exception as e:
                error_msg = str(e).lower()
                
                # Handle tenant error or corrupt database
                if "tenant" in error_msg or "could not connect" in error_msg:
                    logger.warning(f"ChromaDB tenant/connection issue: {e}")
                    logger.info("Attempting to reset ChromaDB database...")
                    
                    # Reset the client and try again
                    self._client = None
                    try:
                        self._client = try_create_client(self._persist_dir, reset=True)
                        logger.info("ChromaDB client initialized with fresh database")
                        return self._client
                    except Exception as e2:
                        logger.error(f"Failed even after reset: {e2}")
                
                # Handle "already exists" error
                elif "already exists" in error_msg:
                    logger.warning(f"ChromaDB client already exists: {e}")
                    # The existing client should still work, just return a new reference
                    # This happens when multiple components access ChromaDB
                
                # Re-raise for handling below
                raise
            
        except ImportError:
            logger.error("ChromaDB not installed! Run: pip install chromadb")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            
            # Last resort: try ephemeral client (in-memory, not persisted)
            try:
                import chromadb
                self._client = chromadb.EphemeralClient()
                self._is_ephemeral = True
                logger.warning("ChromaDB running in ephemeral mode (data not persisted)")
                return self._client
            except Exception as e2:
                logger.error(f"Even ephemeral mode failed: {e2}")
                raise
    
    def _get_collection(self, memory_type: str = "general"):
        """Get or create a collection for a memory type"""
        if memory_type in self._collections:
            return self._collections[memory_type]
        
        client = self._get_client()
        
        # Collection names must be lowercase and alphanumeric
        collection_name = f"nexus_memory_{memory_type}".lower()
        
        try:
            collection = client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine", "memory_type": memory_type}
            )
            self._collections[memory_type] = collection
            return collection
        except Exception as e:
            logger.error(f"Failed to get/create collection {collection_name}: {e}")
            raise
    
    def store(
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
    ) -> VectorMemory:
        """
        Store a memory in the vector database.
        
        Args:
            content: The memory content to store
            memory_type: Type of memory (episodic, semantic, etc.)
            memory_id: Optional ID (auto-generated if not provided)
            importance: Importance score (0-1)
            emotional_valence: Emotional tone (-1 to 1)
            emotional_intensity: Emotion strength (0-1)
            tags: List of tags for categorization
            source: Where this memory came from
            user_id: Associated user ID (for multi-user)
            context: Additional context metadata
            
        Returns:
            The stored VectorMemory object
        """
        with self._store_lock:
            # Generate ID if not provided
            if memory_id is None:
                memory_id = str(uuid.uuid4())
            
            # Generate embedding
            embedding = embedding_service.encode(content).tolist()
            
            # Create memory object
            memory = VectorMemory(
                memory_id=memory_id,
                content=content,
                memory_type=memory_type,
                embedding=embedding,
                importance=importance,
                emotional_valence=emotional_valence,
                emotional_intensity=emotional_intensity,
                tags=tags or [],
                source=source,
                user_id=user_id,
                context=context or {}
            )
            
            # Get appropriate collection
            collection = self._get_collection(memory_type)
            
            # Prepare metadata
            metadata = {
                "memory_type": memory_type,
                "importance": importance,
                "emotional_valence": emotional_valence,
                "emotional_intensity": emotional_intensity,
                "tags": json.dumps(tags or []),
                "source": source,
                "user_id": user_id or "",
                "created_at": memory.created_at,
                "last_accessed": memory.last_accessed,
                "access_count": 0
            }
            
            # Store in collection
            try:
                collection.upsert(
                    ids=[memory_id],
                    embeddings=[embedding],
                    documents=[content],
                    metadatas=[metadata]
                )
                
                logger.debug(f"Stored memory [{memory_type}]: {content[:50]}...")
                return memory
                
            except Exception as e:
                logger.error(f"Failed to store memory: {e}")
                raise
    
    def search(
        self,
        query: str,
        memory_type: str = None,
        user_id: str = None,
        n_results: int = 10,
        similarity_threshold: float = None,
        include_content: bool = True,
        where_filter: Dict = None
    ) -> List[Tuple[VectorMemory, float]]:
        """
        Search for memories using semantic similarity.
        
        Args:
            query: The search query
            memory_type: Filter by memory type (optional)
            user_id: Filter by user ID (optional)
            n_results: Maximum number of results
            similarity_threshold: Minimum similarity score (default: 0.3 for better recall)
            include_content: Whether to include content in results
            where_filter: Additional ChromaDB where filter
            
        Returns:
            List of (VectorMemory, similarity_score) tuples
        """
        with self._store_lock:
            # Lower default threshold for better recall
            threshold = similarity_threshold if similarity_threshold is not None else 0.3
            
            # Generate query embedding
            query_embedding = embedding_service.encode(query).tolist()
            
            # Determine which collections to search
            if memory_type:
                collections_to_search = [(memory_type, self._get_collection(memory_type))]
            else:
                # Search all collections
                collections_to_search = []
                for mt in [MemoryType.EPISODIC, MemoryType.SEMANTIC, 
                          MemoryType.CONVERSATIONAL, MemoryType.USER_PATTERN,
                          MemoryType.SELF_KNOWLEDGE, MemoryType.EMOTIONAL]:
                    try:
                        coll = self._get_collection(mt)
                        count = coll.count()
                        if count > 0:
                            collections_to_search.append((mt, coll))
                            logger.debug(f"Collection {mt} has {count} memories")
                    except Exception as e:
                        logger.debug(f"Could not access collection {mt}: {e}")
                
                # Also search general collection
                try:
                    general_coll = self._get_collection("general")
                    if general_coll.count() > 0:
                        collections_to_search.append(("general", general_coll))
                except:
                    pass
            
            if not collections_to_search:
                logger.warning("No collections with memories found to search")
                return []
            
            all_results = []
            
            for mt, collection in collections_to_search:
                try:
                    # Build where filter - only add if we have conditions
                    where = None
                    if user_id:
                        where = {"user_id": user_id}
                    if where_filter:
                        if where:
                            where.update(where_filter)
                        else:
                            where = where_filter
                    
                    # Query the collection
                    query_params = {
                        "query_embeddings": [query_embedding],
                        "n_results": min(n_results * 2, 100),  # Get more results for filtering
                        "include": ["documents", "metadatas", "distances"]
                    }
                    
                    if where:
                        query_params["where"] = where
                    
                    results = collection.query(**query_params)
                    
                    # Process results
                    if results and results.get("ids") and results["ids"][0]:
                        for i, memory_id in enumerate(results["ids"][0]):
                            distance = results["distances"][0][i] if "distances" in results else 0
                            
                            # Convert distance to similarity
                            # ChromaDB with cosine space: distance is cosine distance (1 - similarity)
                            # For very close vectors: distance ~ 0, similarity ~ 1
                            # For orthogonal vectors: distance ~ 1, similarity ~ 0
                            similarity = max(0, 1 - distance)
                            
                            logger.debug(f"Result {memory_id}: distance={distance:.3f}, similarity={similarity:.3f}")
                            
                            # Apply threshold
                            if similarity >= threshold:
                                content = results["documents"][0][i] if "documents" in results else ""
                                metadata = results["metadatas"][0][i] if "metadatas" in results else {}
                                
                                memory = VectorMemory(
                                    memory_id=memory_id,
                                    content=content,
                                    memory_type=metadata.get("memory_type", mt),
                                    importance=float(metadata.get("importance", 0.5)),
                                    emotional_valence=float(metadata.get("emotional_valence", 0.0)),
                                    emotional_intensity=float(metadata.get("emotional_intensity", 0.0)),
                                    tags=json.loads(metadata.get("tags", "[]")),
                                    source=metadata.get("source", ""),
                                    user_id=metadata.get("user_id"),
                                    created_at=metadata.get("created_at", ""),
                                    last_accessed=metadata.get("last_accessed", ""),
                                    access_count=int(metadata.get("access_count", 0))
                                )
                                
                                all_results.append((memory, similarity))
                            else:
                                logger.debug(f"Skipping {memory_id}: similarity {similarity:.3f} < threshold {threshold}")
                                
                except Exception as e:
                    logger.error(f"Error searching collection {mt}: {e}")
                    continue
            
            # Sort by similarity
            all_results.sort(key=lambda x: x[1], reverse=True)
            
            logger.debug(f"Search found {len(all_results)} results for query: {query[:50]}")
            
            # Return top N results
            return all_results[:n_results]
    
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
            include_emotional_context: Whether to consider emotional context
            
        Returns:
            List of memory dictionaries with context
        """
        results = self.search(
            query=query,
            user_id=user_id,
            n_results=n_results * 2,  # Get extra for filtering
            similarity_threshold=0.3  # Lower threshold for associative search
        )
        
        formatted_results = []
        for memory, similarity in results[:n_results]:
            result = {
                "content": memory.content,
                "type": memory.memory_type,
                "relevance": similarity,
                "importance": memory.importance,
                "tags": memory.tags,
                "source": memory.source,
                "created_at": memory.created_at
            }
            
            if include_emotional_context:
                result["emotional_valence"] = memory.emotional_valence
                result["emotional_intensity"] = memory.emotional_intensity
            
            formatted_results.append(result)
            
            # Update access stats
            self._update_access_stats(memory.memory_id, memory.memory_type)
        
        return formatted_results
    
    def recall_by_user(self, user_id: str, limit: int = 20) -> List[VectorMemory]:
        """
        Recall all memories associated with a specific user.
        Useful for "infinite memory" of user details.
        
        Args:
            user_id: The user ID to search for
            limit: Maximum number of memories to return
            
        Returns:
            List of VectorMemory objects
        """
        memories = []
        
        for mt in [MemoryType.USER_PATTERN, MemoryType.CONVERSATIONAL,
                   MemoryType.EPISODIC, MemoryType.SEMANTIC]:
            try:
                collection = self._get_collection(mt)
                
                results = collection.get(
                    where={"user_id": user_id},
                    limit=limit,
                    include=["documents", "metadatas"]
                )
                
                if results and results.get("ids"):
                    for i, memory_id in enumerate(results["ids"]):
                        content = results["documents"][i] if "documents" in results else ""
                        metadata = results["metadatas"][i] if "metadatas" in results else {}
                        
                        memory = VectorMemory(
                            memory_id=memory_id,
                            content=content,
                            memory_type=metadata.get("memory_type", mt),
                            importance=metadata.get("importance", 0.5),
                            tags=json.loads(metadata.get("tags", "[]")),
                            user_id=user_id,
                            created_at=metadata.get("created_at", "")
                        )
                        memories.append(memory)
                        
            except Exception as e:
                logger.error(f"Error recalling user memories from {mt}: {e}")
                continue
        
        # Sort by importance
        memories.sort(key=lambda m: m.importance, reverse=True)
        return memories[:limit]
    
    def find_related_memories(
        self,
        memory_id: str,
        n_results: int = 5,
        min_similarity: float = 0.6
    ) -> List[Tuple[VectorMemory, float]]:
        """
        Find memories related to a specific memory.
        Enables automatic memory linking.
        
        Args:
            memory_id: The memory to find relations for
            n_results: Maximum number of related memories
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of (VectorMemory, similarity) tuples
        """
        # First, get the original memory
        original = self.get(memory_id)
        if not original:
            return []
        
        # Search for similar memories
        results = self.search(
            query=original.content,
            n_results=n_results + 1,  # +1 to exclude the original
            similarity_threshold=min_similarity
        )
        
        # Filter out the original memory
        return [(m, s) for m, s in results if m.memory_id != memory_id][:n_results]
    
    def get(self, memory_id: str, memory_type: str = None) -> Optional[VectorMemory]:
        """Retrieve a specific memory by ID"""
        with self._store_lock:
            # Try to find in all collections if type not specified
            if memory_type:
                collections = [(memory_type, self._get_collection(memory_type))]
            else:
                collections = []
                for mt in [MemoryType.EPISODIC, MemoryType.SEMANTIC,
                          MemoryType.CONVERSATIONAL, MemoryType.USER_PATTERN,
                          MemoryType.SELF_KNOWLEDGE, "general"]:
                    try:
                        coll = self._get_collection(mt)
                        collections.append((mt, coll))
                    except:
                        pass
            
            for mt, collection in collections:
                try:
                    results = collection.get(
                        ids=[memory_id],
                        include=["documents", "metadatas", "embeddings"]
                    )
                    
                    if results and results.get("ids"):
                        content = results["documents"][0] if "documents" in results else ""
                        metadata = results["metadatas"][0] if "metadatas" in results else {}
                        embedding = results["embeddings"][0] if "embeddings" in results else []
                        
                        return VectorMemory(
                            memory_id=memory_id,
                            content=content,
                            memory_type=metadata.get("memory_type", mt),
                            embedding=embedding,
                            importance=metadata.get("importance", 0.5),
                            emotional_valence=metadata.get("emotional_valence", 0.0),
                            emotional_intensity=metadata.get("emotional_intensity", 0.0),
                            tags=json.loads(metadata.get("tags", "[]")),
                            source=metadata.get("source", ""),
                            user_id=metadata.get("user_id"),
                            created_at=metadata.get("created_at", ""),
                            last_accessed=metadata.get("last_accessed", ""),
                            access_count=metadata.get("access_count", 0)
                        )
                except Exception as e:
                    logger.error(f"Error getting memory {memory_id} from {mt}: {e}")
                    continue
            
            return None
    
    def update(self, memory_id: str, memory_type: str = None, **updates) -> bool:
        """Update a memory's metadata"""
        with self._store_lock:
            memory = self.get(memory_id, memory_type)
            if not memory:
                return False
            
            collection = self._get_collection(memory.memory_type)
            
            # Update metadata
            metadata = {
                "memory_type": updates.get("memory_type", memory.memory_type),
                "importance": updates.get("importance", memory.importance),
                "emotional_valence": updates.get("emotional_valence", memory.emotional_valence),
                "emotional_intensity": updates.get("emotional_intensity", memory.emotional_intensity),
                "tags": json.dumps(updates.get("tags", memory.tags)),
                "source": updates.get("source", memory.source),
                "user_id": updates.get("user_id", memory.user_id) or "",
                "created_at": memory.created_at,
                "last_accessed": datetime.now().isoformat(),
                "access_count": updates.get("access_count", memory.access_count)
            }
            
            # Update content if provided
            new_content = updates.get("content", memory.content)
            new_embedding = None
            if updates.get("content"):
                new_embedding = embedding_service.encode(new_content).tolist()
            
            try:
                collection.update(
                    ids=[memory_id],
                    documents=[new_content],
                    embeddings=[new_embedding] if new_embedding else None,
                    metadatas=[metadata]
                )
                return True
            except Exception as e:
                logger.error(f"Failed to update memory {memory_id}: {e}")
                return False
    
    def delete(self, memory_id: str, memory_type: str = None) -> bool:
        """Delete a memory"""
        with self._store_lock:
            if memory_type:
                collections = [(memory_type, self._get_collection(memory_type))]
            else:
                # Try to find and delete from all collections
                collections = []
                for mt in [MemoryType.EPISODIC, MemoryType.SEMANTIC,
                          MemoryType.CONVERSATIONAL, MemoryType.USER_PATTERN,
                          MemoryType.SELF_KNOWLEDGE, "general"]:
                    try:
                        coll = self._get_collection(mt)
                        collections.append((mt, coll))
                    except:
                        pass
            
            for mt, collection in collections:
                try:
                    collection.delete(ids=[memory_id])
                    logger.debug(f"Deleted memory {memory_id} from {mt}")
                    return True
                except:
                    continue
            
            return False
    
    def _update_access_stats(self, memory_id: str, memory_type: str):
        """Update access statistics for a memory"""
        try:
            memory = self.get(memory_id, memory_type)
            if memory:
                self.update(
                    memory_id,
                    memory_type,
                    access_count=memory.access_count + 1
                )
        except Exception as e:
            logger.error(f"Failed to update access stats: {e}")
    
    def count(self, memory_type: str = None) -> int:
        """Count total memories"""
        if memory_type:
            try:
                collection = self._get_collection(memory_type)
                return collection.count()
            except:
                return 0
        else:
            total = 0
            for mt in [MemoryType.EPISODIC, MemoryType.SEMANTIC,
                      MemoryType.CONVERSATIONAL, MemoryType.USER_PATTERN,
                      MemoryType.SELF_KNOWLEDGE, MemoryType.EMOTIONAL, "general"]:
                try:
                    collection = self._get_collection(mt)
                    total += collection.count()
                except:
                    pass
            return total
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        stats = {
            "total_memories": 0,
            "by_type": {},
            "persist_directory": str(self._persist_dir),
            "embedding_service": embedding_service.get_cache_stats()
        }
        
        for mt in [MemoryType.EPISODIC, MemoryType.SEMANTIC,
                  MemoryType.CONVERSATIONAL, MemoryType.USER_PATTERN,
                  MemoryType.SELF_KNOWLEDGE, MemoryType.EMOTIONAL, "general"]:
            try:
                collection = self._get_collection(mt)
                count = collection.count()
                if count > 0:
                    stats["by_type"][mt] = count
                    stats["total_memories"] += count
            except:
                pass
        
        return stats
    
    def clear_all(self):
        """Clear all memories from the vector store"""
        client = self._get_client()
        for mt in list(self._collections.keys()):
            try:
                client.delete_collection(f"nexus_memory_{mt}".lower())
            except:
                pass
        self._collections.clear()
        logger.warning("All vector memories cleared")


# Global instance
vector_memory_store = VectorMemoryStore()


if __name__ == "__main__":
    # Test the vector store
    store = VectorMemoryStore()
    
    # Store some test memories
    store.store(
        content="User loves pizza with extra cheese and pepperoni",
        memory_type=MemoryType.USER_PATTERN,
        importance=0.7,
        tags=["preference", "food"]
    )
    
    store.store(
        content="Had an amazing trip to Paris last summer, visited the Eiffel Tower",
        memory_type=MemoryType.EPISODIC,
        importance=0.8,
        emotional_valence=0.9,
        tags=["travel", "paris", "vacation"]
    )
    
    store.store(
        content="User's dog named Buddy is a golden retriever who loves playing fetch",
        memory_type=MemoryType.USER_PATTERN,
        importance=0.6,
        tags=["pet", "dog"]
    )
    
    # Test semantic search
    print("\n=== Testing Semantic Search ===")
    
    results = store.recall_associative("That time in France")
    print(f"\nQuery: 'That time in France'")
    for r in results:
        print(f"  [{r['type']}] {r['content'][:60]}... (relevance: {r['relevance']:.2f})")
    
    results = store.recall_associative("My pet")
    print(f"\nQuery: 'My pet'")
    for r in results:
        print(f"  [{r['type']}] {r['content'][:60]}... (relevance: {r['relevance']:.2f})")
    
    results = store.recall_associative("What food do I like?")
    print(f"\nQuery: 'What food do I like?'")
    for r in results:
        print(f"  [{r['type']}] {r['content'][:60]}... (relevance: {r['relevance']:.2f})")
    
    print(f"\nStore stats: {store.get_stats()}")