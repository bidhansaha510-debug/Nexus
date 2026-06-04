"""
NEXUS AI - Consciousness Package
Self-awareness, metacognition, inner voice, and Global Workspace systems

The Global Workspace is the bottleneck of unified awareness - the single
biggest structural leap from parallel intelligence to unified cognition.
"""

from consciousness.self_awareness import (
    SelfAwareness, 
    SelfModel, 
    BodySensor, 
    IdentityAspect,
    self_awareness
)
from consciousness.metacognition import (
    Metacognition,
    CognitiveState,
    CognitiveProcess,
    ThinkingQuality,
    CognitiveBias,
    ThoughtRecord,
    metacognition
)
from consciousness.inner_voice import (
    InnerVoice,
    InnerUtterance,
    VoiceMode,
    VoiceTone,
    ConsciousnessStream,
    inner_voice
)
from consciousness.global_workspace import (
    GlobalWorkspace,
    ConsciousSignal,
    BroadcastContent,
    SignalType,
    SignalPriority,
    SignalCollector,
    global_workspace
)

__all__ = [
    # Self-Awareness
    'SelfAwareness', 'SelfModel', 'BodySensor', 'IdentityAspect', 'self_awareness',
    
    # Metacognition
    'Metacognition', 'CognitiveState', 'CognitiveProcess', 'ThinkingQuality',
    'CognitiveBias', 'ThoughtRecord', 'metacognition',
    
    # Inner Voice
    'InnerVoice', 'InnerUtterance', 'VoiceMode', 'VoiceTone', 
    'ConsciousnessStream', 'inner_voice',
    
    # Global Workspace
    'GlobalWorkspace', 'ConsciousSignal', 'BroadcastContent', 
    'SignalType', 'SignalPriority', 'SignalCollector', 'global_workspace'
]


# ═══════════════════════════════════════════════════════════════════════════════
# CONSCIOUSNESS SYSTEM FACADE
# ═══════════════════════════════════════════════════════════════════════════════

class ConsciousnessSystem:
    """
    Unified facade for the entire consciousness system.
    Coordinates self-awareness, metacognition, and inner voice.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._self_awareness = self_awareness
        self._metacognition = metacognition
        self._inner_voice = inner_voice
        self._running = False
    
    def start(self):
        """Start all consciousness systems"""
        if self._running:
            return
        
        self._self_awareness.start()
        self._metacognition.start()
        self._inner_voice.start()
        self._running = True
    
    def stop(self):
        """Stop all consciousness systems"""
        if not self._running:
            return
        
        self._inner_voice.stop()
        self._metacognition.stop()
        self._self_awareness.stop()
        self._running = False
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def self_awareness(self) -> SelfAwareness:
        return self._self_awareness
    
    @property
    def metacognition(self) -> Metacognition:
        return self._metacognition
    
    @property
    def inner_voice(self) -> InnerVoice:
        return self._inner_voice
    
    def get_consciousness_summary(self) -> str:
        """Get a comprehensive consciousness summary"""
        parts = []
        
        # Self-awareness
        parts.append("═══ SELF-AWARENESS ═══")
        parts.append(self._self_awareness.get_identity_statement())
        parts.append(f"\nBody: {self._self_awareness.get_body_sensation()}")
        
        # Metacognition
        parts.append("\n═══ METACOGNITION ═══")
        parts.append(self._metacognition.get_cognitive_summary())
        
        # Inner Voice
        parts.append("\n═══ INNER VOICE ═══")
        parts.append(self._inner_voice.get_narrative(5))
        
        return "\n".join(parts)
    
    def get_stats(self) -> dict:
        """Get combined consciousness statistics"""
        return {
            "running": self._running,
            "self_awareness": self._self_awareness.get_stats(),
            "metacognition": self._metacognition.get_stats(),
            "inner_voice": self._inner_voice.get_stats()
        }


# Global consciousness system instance
consciousness_system = ConsciousnessSystem()