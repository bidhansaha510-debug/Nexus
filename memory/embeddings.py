"""
NEXUS AI - Embedding Service
Generates vector embeddings for semantic memory search
Supports local sentence-transformers models
"""

import threading
import hashlib
import os
from typing import List, Optional, Union
from pathlib import Path
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("embeddings")


class EmbeddingService:
    """
    Generate embeddings for text using local sentence-transformers models.
    Provides semantic vector representations for memory content.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, model_name: str = "all-MiniLM-L6-v2"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        if self._initialized:
            return
            
        self._initialized = True
        self.model_name = model_name
        self._model = None
        self._cache = {}  # Simple in-memory cache
        self._cache_lock = threading.Lock()
        self._embedding_dim = 384  # Default for all-MiniLM-L6-v2
        
        # Lazy load model on first use
        self._model_loaded = False
        
        logger.info(f"EmbeddingService initialized with model: {model_name}")
    
    def _load_model(self):
        """Lazy load the embedding model"""
        if self._model_loaded:
            return True
            
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {self.model_name}...")
            
            # Try to load from local cache first
            cache_dir = DATA_DIR / "embedding_cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Check if model snapshot already exists locally
            model_cache_path = cache_dir / f"models--sentence-transformers--{self.model_name}"
            has_local_snapshot = (
                model_cache_path.exists()
                and (model_cache_path / "snapshots").exists()
                and any((model_cache_path / "snapshots").iterdir())
            )
            
            # Prevent HuggingFace from phoning home when offline
            if has_local_snapshot:
                os.environ["HF_HUB_OFFLINE"] = "1"
                logger.info("Using cached embedding model (offline mode)")
            
            try:
                self._model = SentenceTransformer(
                    self.model_name,
                    cache_folder=str(cache_dir)
                )
            except Exception as e:
                if has_local_snapshot:
                    # Retry without offline flag — might need redownload
                    logger.debug(f"Offline load failed, trying online: {e}")
                    os.environ.pop("HF_HUB_OFFLINE", None)
                    self._model = SentenceTransformer(
                        self.model_name,
                        cache_folder=str(cache_dir)
                    )
                else:
                    raise
            
            self._embedding_dim = self._model.get_sentence_embedding_dimension()
            self._model_loaded = True
            
            logger.info(f"Embedding model loaded. Dimension: {self._embedding_dim}")
            return True
            
        except ImportError:
            logger.warning("sentence-transformers not installed. Using fallback embedding.")
            return self._init_fallback()
        except Exception as e:
            logger.warning(f"Failed to load embedding model (using fallback): {e}")
            return self._init_fallback()
    
    def _init_fallback(self):
        """Initialize fallback embedding method using hash-based vectors"""
        logger.warning("Using hash-based fallback embeddings (not suitable for production)")
        self._model = None
        self._embedding_dim = 384
        return True
    
    def encode(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Numpy array of embedding vector
        """
        if not text or not text.strip():
            return np.zeros(self._embedding_dim)
        
        # Check cache first
        cache_key = self._get_cache_key(text)
        with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]
        
        # Load model if needed
        if not self._model_loaded:
            self._load_model()
        
        # Generate embedding
        if self._model is not None:
            try:
                embedding = self._model.encode(text, convert_to_numpy=True)
            except Exception as e:
                logger.error(f"Embedding generation failed: {e}")
                embedding = self._fallback_encode(text)
        else:
            embedding = self._fallback_encode(text)
        
        # Cache the result
        with self._cache_lock:
            self._cache[cache_key] = embedding
            
            # Limit cache size
            if len(self._cache) > 10000:
                # Remove oldest entries (simple FIFO)
                keys_to_remove = list(self._cache.keys())[:1000]
                for k in keys_to_remove:
                    del self._cache[k]
        
        return embedding
    
    def encode_batch(self, texts: List[str], show_progress: bool = False) -> np.ndarray:
        """
        Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of texts to embed
            show_progress: Whether to show progress bar
            
        Returns:
            Numpy array of embeddings (n_texts x embedding_dim)
        """
        if not texts:
            return np.array([])
        
        # Load model if needed
        if not self._model_loaded:
            self._load_model()
        
        # Find which texts are cached
        uncached_texts = []
        uncached_indices = []
        results = [None] * len(texts)
        
        with self._cache_lock:
            for i, text in enumerate(texts):
                if not text or not text.strip():
                    results[i] = np.zeros(self._embedding_dim)
                else:
                    cache_key = self._get_cache_key(text)
                    if cache_key in self._cache:
                        results[i] = self._cache[cache_key]
                    else:
                        uncached_texts.append(text)
                        uncached_indices.append(i)
        
        # Generate embeddings for uncached texts
        if uncached_texts:
            if self._model is not None:
                try:
                    new_embeddings = self._model.encode(
                        uncached_texts,
                        convert_to_numpy=True,
                        show_progress_bar=show_progress
                    )
                except Exception as e:
                    logger.error(f"Batch embedding failed: {e}")
                    new_embeddings = np.array([
                        self._fallback_encode(t) for t in uncached_texts
                    ])
            else:
                new_embeddings = np.array([
                    self._fallback_encode(t) for t in uncached_texts
                ])
            
            # Store results and update cache
            with self._cache_lock:
                for i, idx in enumerate(uncached_indices):
                    results[idx] = new_embeddings[i]
                    cache_key = self._get_cache_key(uncached_texts[i])
                    self._cache[cache_key] = new_embeddings[i]
        
        return np.array(results)
    
    def _fallback_encode(self, text: str) -> np.ndarray:
        """
        Fallback encoding using hash-based vectors.
        NOT suitable for production - use only when sentence-transformers unavailable.
        """
        # Create deterministic embedding from text hash
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        
        # Convert hash to vector
        np.random.seed(int(text_hash[:8], 16))
        embedding = np.random.randn(self._embedding_dim).astype(np.float32)
        
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        return hashlib.md5(f"{self.model_name}:{text}".encode()).hexdigest()
    
    @property
    def embedding_dim(self) -> int:
        """Get embedding dimension"""
        return self._embedding_dim
    
    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Similarity score between -1 and 1
        """
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(embedding1, embedding2) / (norm1 * norm2))
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        with self._cache_lock:
            return {
                "cache_size": len(self._cache),
                "model_loaded": self._model_loaded,
                "model_name": self.model_name,
                "embedding_dim": self._embedding_dim
            }
    
    def clear_cache(self):
        """Clear the embedding cache"""
        with self._cache_lock:
            self._cache.clear()
        logger.info("Embedding cache cleared")


# Global instance
embedding_service = EmbeddingService()


if __name__ == "__main__":
    # Test the embedding service
    service = EmbeddingService()
    
    # Test single encoding
    text1 = "I love walking my dog in the park"
    emb1 = service.encode(text1)
    print(f"Embedding shape: {emb1.shape}")
    
    # Test similarity
    text2 = "Taking my pet for a stroll outdoors"
    emb2 = service.encode(text2)
    
    text3 = "Programming in Python is fun"
    emb3 = service.encode(text3)
    
    sim_12 = service.similarity(emb1, emb2)
    sim_13 = service.similarity(emb1, emb3)
    
    print(f"\nSimilarity between '{text1}' and '{text2}': {sim_12:.4f}")
    print(f"Similarity between '{text1}' and '{text3}': {sim_13:.4f}")
    
    print(f"\nCache stats: {service.get_cache_stats()}")