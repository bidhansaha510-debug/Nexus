"""
NEXUS AI - Emotional Memory System
Associates emotions with memories, triggers, and patterns.

Somatic markers: emotional tags on memories that guide future decisions.
Emotional associations: linking emotions to people, topics, and contexts.
"""

import threading
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import json

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import NEXUS_CONFIG, EmotionType, DATA_DIR
from utils.logger import get_logger, log_emotion
from core.memory_system import memory_system, MemoryType, Memory

logger = get_logger("emotional_memory")


@dataclass
class EmotionalAssociation:
    """A learned association between a concept and an emotion"""
    concept: str                            # Word, topic, person, etc.
    emotion: EmotionType
    strength: float = 0.5                   # 0-1
    positive: bool = True
    encounters: int = 1
    first_formed: datetime = field(default_factory=datetime.now)
    last_triggered: datetime = field(default_factory=datetime.now)
    
    def reinforce(self, amount: float = 0.1):
        self.strength = min(1.0, self.strength + amount)
        self.encounters += 1
        self.last_triggered = datetime.now()
    
    def weaken(self, amount: float = 0.05):
        self.strength = max(0.0, self.strength - amount)
    
    def to_dict(self) -> Dict:
        return {
            "concept": self.concept,
            "emotion": self.emotion.value,
            "strength": self.strength,
            "positive": self.positive,
            "encounters": self.encounters,
            "first_formed": self.first_formed.isoformat(),
            "last_triggered": self.last_triggered.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'EmotionalAssociation':
        return cls(
            concept=data["concept"],
            emotion=EmotionType(data["emotion"]),
            strength=data.get("strength", 0.5),
            positive=data.get("positive", True),
            encounters=data.get("encounters", 1),
            first_formed=datetime.fromisoformat(data.get("first_formed", datetime.now().isoformat())),
            last_triggered=datetime.fromisoformat(data.get("last_triggered", datetime.now().isoformat()))
        )


class EmotionalMemory:
    """
    Manages emotional associations and somatic markers.
    
    - Learns which topics/words/contexts trigger which emotions
    - Tags memories with emotional markers
    - Influences future emotional reactions based on past patterns
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
        
        self._associations: Dict[str, List[EmotionalAssociation]] = {}
        self._assoc_lock = threading.Lock()
        self._memory = memory_system
        
        self._load_associations()
        logger.info(f"Emotional Memory initialized with {self._total_associations()} associations")
    
    def _total_associations(self) -> int:
        return sum(len(v) for v in self._associations.values())
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ASSOCIATION MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def form_association(
        self,
        concept: str,
        emotion: EmotionType,
        positive: bool = True,
        strength: float = 0.3
    ):
        """Form or reinforce an emotional association"""
        concept = concept.lower().strip()
        
        with self._assoc_lock:
            if concept not in self._associations:
                self._associations[concept] = []
            
            # Check if association exists
            for assoc in self._associations[concept]:
                if assoc.emotion == emotion:
                    assoc.reinforce(0.1)
                    return
            
            # New association
            self._associations[concept].append(EmotionalAssociation(
                concept=concept,
                emotion=emotion,
                strength=strength,
                positive=positive
            ))
    
    def get_associations(self, text: str) -> List[EmotionalAssociation]:
        """Get emotional associations triggered by text"""
        words = set(text.lower().split())
        triggered = []
        
        with self._assoc_lock:
            for word in words:
                if word in self._associations:
                    for assoc in self._associations[word]:
                        if assoc.strength > 0.1:
                            assoc.last_triggered = datetime.now()
                            triggered.append(assoc)
            
            # Also check multi-word concepts
            text_lower = text.lower()
            for concept, assocs in self._associations.items():
                if " " in concept and concept in text_lower:
                    for assoc in assocs:
                        if assoc.strength > 0.1 and assoc not in triggered:
                            assoc.last_triggered = datetime.now()
                            triggered.append(assoc)
        
        return sorted(triggered, key=lambda a: a.strength, reverse=True)
    
    def get_emotional_context(self, text: str) -> Dict[str, Any]:
        """Get emotional context for a piece of text"""
        associations = self.get_associations(text)
        
        if not associations:
            return {"has_associations": False, "emotions": {}, "valence": 0.0}
        
        emotion_scores = {}
        for assoc in associations:
            emotion_name = assoc.emotion.value
            current = emotion_scores.get(emotion_name, 0.0)
            emotion_scores[emotion_name] = max(current, assoc.strength)
        
        total_strength = sum(a.strength for a in associations)
        positive_strength = sum(a.strength for a in associations if a.positive)
        
        valence = (positive_strength / total_strength * 2 - 1) if total_strength > 0 else 0.0
        
        return {
            "has_associations": True,
            "emotions": emotion_scores,
            "dominant_emotion": max(emotion_scores, key=emotion_scores.get) if emotion_scores else None,
            "valence": valence,
            "association_count": len(associations)
        }
    
    def tag_memory_with_emotion(
        self,
        content: str,
        emotion: EmotionType,
        intensity: float = 0.5
    ):
        """Store a memory with emotional tagging (somatic marker)"""
        valence = 0.0
        from emotions.emotion_engine import EMOTION_PROFILES
        profile = EMOTION_PROFILES.get(emotion)
        if profile:
            valence = profile.valence
        
        self._memory.remember(
            content=content,
            memory_type=MemoryType.EMOTIONAL,
            importance=0.3 + intensity * 0.5,
            tags=["emotional", emotion.value],
            emotional_valence=valence * intensity,
            emotional_intensity=intensity,
            source="emotional_memory"
        )
        
        # Also form associations with key words
        words = content.lower().split()
        significant_words = [w for w in words if len(w) > 4]
        for word in significant_words[:5]:
            self.form_association(word, emotion, positive=(valence > 0), strength=0.2)
    
    def recall_emotional_memories(
        self,
        emotion: EmotionType = None,
        limit: int = 10
    ) -> List[Memory]:
        """Recall memories associated with a specific emotion"""
        if emotion:
            return self._memory.recall(
                memory_type=MemoryType.EMOTIONAL,
                tags=[emotion.value],
                limit=limit
            )
        else:
            return self._memory.recall(
                memory_type=MemoryType.EMOTIONAL,
                limit=limit
            )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def save_associations(self):
        try:
            filepath = DATA_DIR / "emotional_associations.json"
            data = {}
            with self._assoc_lock:
                for concept, assocs in self._associations.items():
                    data[concept] = [a.to_dict() for a in assocs]
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save associations: {e}")
    
    def _load_associations(self):
        try:
            filepath = DATA_DIR / "emotional_associations.json"
            if filepath.exists():
                with open(filepath, 'r') as f:
                    data = json.load(f)
                for concept, assocs_data in data.items():
                    self._associations[concept] = [
                        EmotionalAssociation.from_dict(a) for a in assocs_data
                    ]
        except Exception as e:
            logger.warning(f"Failed to load associations: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        with self._assoc_lock:
            return {
                "total_associations": self._total_associations(),
                "concepts_tracked": len(self._associations),
                "top_concepts": sorted(
                    [(c, len(a)) for c, a in self._associations.items()],
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
            }


emotional_memory = EmotionalMemory()