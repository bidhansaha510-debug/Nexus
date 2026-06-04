"""
NEXUS AI - Core Package
Central brain, memory, events, state management, and autonomy engine.

NOTE: Heavy modules (nexus_brain, autonomy_engine) are NOT imported here
to avoid triggering expensive singleton construction at import time.
Use direct imports instead:
    from core.nexus_brain import NexusBrain, nexus_brain
    from core.autonomy_engine import autonomy_engine
"""

from core.event_bus import EventBus, EventType, EventPriority, Event, event_bus
from core.state_manager import StateManager, NexusState, state_manager
from core.memory_system import MemorySystem, MemoryType, Memory, memory_system

# Lazy accessors for heavy modules — avoids module-level singleton construction
def get_autonomy_engine():
    """Lazy import of autonomy engine to avoid eager singleton construction."""
    from core.autonomy_engine import autonomy_engine
    return autonomy_engine

__all__ = [
    'EventBus', 'EventType', 'EventPriority', 'Event', 'event_bus',
    'StateManager', 'NexusState', 'state_manager',
    'MemorySystem', 'MemoryType', 'Memory', 'memory_system',
    'get_autonomy_engine',
]
