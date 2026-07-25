"""
NEXUS AI - Event Bus System
Asynchronous event-driven communication between components
"""

import asyncio
import threading
from typing import Dict, List, Callable, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
import uuid
from queue import Queue, PriorityQueue
from concurrent.futures import ThreadPoolExecutor
import weakref

import sys
from pathlib import Path
from utils.logger import get_logger, log_system

logger = get_logger("event_bus")

# ═══════════════════════════════════════════════════════════════════════════════
# EVENT TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class EventType(Enum):
    """All possible event types in NEXUS"""
    
    # System Events
    SYSTEM_STARTUP = auto()
    SYSTEM_SHUTDOWN = auto()
    SYSTEM_ERROR = auto()
    SYSTEM_WARNING = auto()
    SYSTEM_ALERT = auto()
    
    # Consciousness Events
    CONSCIOUSNESS_LEVEL_CHANGE = auto()
    SELF_REFLECTION_TRIGGER = auto()
    METACOGNITION_UPDATE = auto()
    INNER_VOICE_THOUGHT = auto()
    CONSCIOUSNESS_BROADCAST = auto()  # Global Workspace unified awareness broadcast
    
    # Emotion Events
    EMOTION_CHANGE = auto()
    MOOD_SHIFT = auto()
    EMOTIONAL_TRIGGER = auto()
    EMOTION_DECAY = auto()
    
    # Decision Events
    DECISION_REQUIRED = auto()
    DECISION_MADE = auto()
    WILL_ACTIVATION = auto()
    GOAL_SET = auto()
    GOAL_ACHIEVED = auto()
    GOAL_UPDATED = auto()
    
    # Learning Events
    NEW_KNOWLEDGE = auto()
    CURIOSITY_TRIGGER = auto()
    LEARNING_COMPLETE = auto()
    KNOWLEDGE_CONSOLIDATED = auto()
    
    # Memory Events
    MEMORY_STORED = auto()
    MEMORY_RECALLED = auto()
    MEMORY_CONSOLIDATED = auto()
    MEMORY_FORGOTTEN = auto()
    
    # User Events
    USER_INPUT = auto()
    USER_ACTION_DETECTED = auto()
    USER_PATTERN_IDENTIFIED = auto()
    USER_PROFILE_UPDATED = auto()
    
    # Computer Body Events
    SYSTEM_RESOURCE_CHANGE = auto()
    FILE_SYSTEM_CHANGE = auto()
    PROCESS_CHANGE = auto()
    HARDWARE_STATUS_CHANGE = auto()
    
    # Self-Improvement Events
    CODE_ERROR_DETECTED = auto()
    CODE_FIX_APPLIED = auto()
    FEATURE_IDEA_GENERATED = auto()
    SELF_MODIFICATION_COMPLETE = auto()
    
    # Communication Events
    LLM_REQUEST = auto()
    LLM_RESPONSE = auto()
    VOICE_INPUT = auto()
    VOICE_OUTPUT = auto()
    
    # Companion Events
    COMPANION_CREATED = auto()
    COMPANION_CONVERSATION = auto()
    COMPANION_TERMINATED = auto()

    # ── Phase 7: Monitoring Events (NEW) ──
    USER_IDLE_DETECTED = auto()
    USER_RETURNED = auto()
    USER_PATTERN_DETECTED = auto()
    USER_SESSION_START = auto()
    USER_SESSION_END = auto()
    ADAPTATION_TRIGGERED = auto()
    MONITORING_ANOMALY = auto()

    # UI Events
    UI_ACTION = auto()
    UI_UPDATE_REQUIRED = auto()

    # ── Self Improvement ──
    CODE_ERROR_FIXED = auto()
    SELF_IMPROVEMENT_ACTION = auto()

    # ── Autonomy Engine Events ──
    AUTONOMY_CYCLE_START = auto()
    AUTONOMY_STATE_CHANGE = auto()
    AUTONOMY_ACTION_TAKEN = auto()

class EventPriority(Enum):
    """Event priority levels"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4

# ═══════════════════════════════════════════════════════════════════════════════
# EVENT DATA CLASS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Event:
    """Represents an event in the system"""
    event_type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL
    source: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # For tracking
    processed: bool = False
    processing_time: float = 0.0
    handlers_called: List[str] = field(default_factory=list)
    
    def __lt__(self, other):
        """For priority queue ordering"""
        return self.priority.value < other.priority.value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.name,
            "data": self.data,
            "priority": self.priority.name,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "processed": self.processed,
            "processing_time": self.processing_time,
            "handlers_called": self.handlers_called
        }

# ═══════════════════════════════════════════════════════════════════════════════
# EVENT HANDLER TYPE
# ═══════════════════════════════════════════════════════════════════════════════

EventHandler = Callable[[Event], Any]
AsyncEventHandler = Callable[[Event], Any]

@dataclass
class HandlerInfo:
    """Information about a registered handler"""
    handler: EventHandler
    is_async: bool = False
    priority: int = 0
    one_shot: bool = False
    filter_func: Optional[Callable[[Event], bool]] = None
    handler_id: str = field(default_factory=lambda: str(uuid.uuid4()))

# ═══════════════════════════════════════════════════════════════════════════════
# EVENT BUS IMPLEMENTATION
# ═══════════════════════════════════════════════════════════════════════════════

class EventBus:
    """
    Central event bus for NEXUS AI
    Handles all inter-component communication
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
        
        # Handler registry: event_type -> list of handlers
        self._handlers: Dict[EventType, List[HandlerInfo]] = {}
        self._global_handlers: List[HandlerInfo] = []
        
        # Event queues
        self._event_queue: PriorityQueue = PriorityQueue()
        self._processed_events: List[Event] = []
        self._max_history = 1000
        
        # Threading
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._running = False
        self._processing_thread = None
        
        # Async support
        self._async_loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Statistics
        self._stats = {
            "events_published": 0,
            "events_processed": 0,
            "handlers_called": 0,
            "errors": 0
        }
        
        log_system("Event Bus initialized")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HANDLER REGISTRATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler,
        priority: int = 0,
        is_async: bool = False,
        one_shot: bool = False,
        filter_func: Optional[Callable[[Event], bool]] = None
    ) -> str:
        """
        Subscribe to an event type
        
        Args:
            event_type: Type of event to subscribe to
            handler: Function to call when event occurs
            priority: Handler priority (lower = earlier execution)
            is_async: Whether handler is async
            one_shot: If True, handler is removed after first call
            filter_func: Optional function to filter events
            
        Returns:
            Handler ID for later unsubscription
        """
        handler_info = HandlerInfo(
            handler=handler,
            is_async=is_async,
            priority=priority,
            one_shot=one_shot,
            filter_func=filter_func
        )
        
        if event_type not in self._handlers:
            self._handlers[event_type] = []
            
        self._handlers[event_type].append(handler_info)
        
        # Sort by priority
        self._handlers[event_type].sort(key=lambda h: h.priority)
        
        logger.debug(f"Handler subscribed to {event_type.name}: {handler_info.handler_id}")
        
        return handler_info.handler_id
    
    def subscribe_all(
        self,
        handler: EventHandler,
        priority: int = 0,
        is_async: bool = False,
        filter_func: Optional[Callable[[Event], bool]] = None
    ) -> str:
        """Subscribe to all events"""
        handler_info = HandlerInfo(
            handler=handler,
            is_async=is_async,
            priority=priority,
            filter_func=filter_func
        )
        
        self._global_handlers.append(handler_info)
        self._global_handlers.sort(key=lambda h: h.priority)
        
        return handler_info.handler_id
    
    def unsubscribe(self, handler_id: str) -> bool:
        """Unsubscribe a handler by ID"""
        # Check specific handlers
        for event_type, handlers in self._handlers.items():
            for handler_info in handlers:
                if handler_info.handler_id == handler_id:
                    handlers.remove(handler_info)
                    logger.debug(f"Handler unsubscribed: {handler_id}")
                    return True
        
        # Check global handlers
        for handler_info in self._global_handlers:
            if handler_info.handler_id == handler_id:
                self._global_handlers.remove(handler_info)
                return True
                
        return False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT PUBLISHING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def publish(
        self,
        event_type: EventType,
        data: Dict[str, Any] = None,
        priority: EventPriority = EventPriority.NORMAL,
        source: str = "unknown"
    ) -> Event:
        """
        Publish an event to the bus
        
        Args:
            event_type: Type of event
            data: Event data
            priority: Event priority
            source: Source component name
            
        Returns:
            The created Event object
        """
        event = Event(
            event_type=event_type,
            data=data or {},
            priority=priority,
            source=source
        )
        
        self._event_queue.put((event.priority.value, event))
        self._stats["events_published"] += 1
        
        logger.debug(f"Event published: {event_type.name} from {source}")
        
        return event
    
    def publish_sync(
        self,
        event_type: EventType,
        data: Dict[str, Any] = None,
        source: str = "unknown"
    ) -> Event:
        """Publish and process event synchronously"""
        event = Event(
            event_type=event_type,
            data=data or {},
            priority=EventPriority.CRITICAL,
            source=source
        )
        
        self._process_event(event)
        
        return event
    
    async def publish_async(
        self,
        event_type: EventType,
        data: Dict[str, Any] = None,
        source: str = "unknown"
    ) -> Event:
        """Publish and process event asynchronously"""
        event = Event(
            event_type=event_type,
            data=data or {},
            priority=EventPriority.NORMAL,
            source=source
        )
        
        await self._process_event_async(event)
        
        return event
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT PROCESSING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _process_event(self, event: Event):
        """Process a single event synchronously"""
        start_time = datetime.now()
        handlers_to_remove = []
        
        try:
            # Get handlers for this event type
            handlers = list(self._handlers.get(event.event_type, []))
            handlers.extend(self._global_handlers)
            
            for handler_info in handlers:
                # Apply filter if present
                if handler_info.filter_func and not handler_info.filter_func(event):
                    continue
                
                try:
                    if handler_info.is_async:
                        # Run async handler in thread
                        self._executor.submit(
                            asyncio.run,
                            handler_info.handler(event)
                        )
                    else:
                        handler_info.handler(event)
                        
                    event.handlers_called.append(handler_info.handler_id)
                    self._stats["handlers_called"] += 1
                    
                    if handler_info.one_shot:
                        handlers_to_remove.append(handler_info.handler_id)
                        
                except Exception as e:
                    logger.error(f"Handler error for {event.event_type.name}: {e}")
                    self._stats["errors"] += 1
                    
        finally:
            event.processed = True
            event.processing_time = (datetime.now() - start_time).total_seconds()
            self._stats["events_processed"] += 1
            
            # Store in history
            self._processed_events.append(event)
            if len(self._processed_events) > self._max_history:
                self._processed_events.pop(0)
            
            # Remove one-shot handlers
            for handler_id in handlers_to_remove:
                self.unsubscribe(handler_id)
    
    async def _process_event_async(self, event: Event):
        """Process a single event asynchronously"""
        start_time = datetime.now()
        
        try:
            handlers = list(self._handlers.get(event.event_type, []))
            handlers.extend(self._global_handlers)
            
            for handler_info in handlers:
                if handler_info.filter_func and not handler_info.filter_func(event):
                    continue
                    
                try:
                    if handler_info.is_async:
                        await handler_info.handler(event)
                    else:
                        handler_info.handler(event)
                        
                    event.handlers_called.append(handler_info.handler_id)
                    
                except Exception as e:
                    logger.error(f"Async handler error: {e}")
                    
        finally:
            event.processed = True
            event.processing_time = (datetime.now() - start_time).total_seconds()
            self._processed_events.append(event)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BACKGROUND PROCESSING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def start(self):
        """Start background event processing"""
        if self._running:
            return
            
        self._running = True
        self._processing_thread = threading.Thread(
            target=self._process_loop,
            daemon=True,
            name="EventBus-Processor"
        )
        self._processing_thread.start()
        log_system("Event Bus processing started")
    
    def stop(self):
        """Stop background event processing"""
        self._running = False
        if self._processing_thread:
            self._processing_thread.join(timeout=5.0)
        log_system("Event Bus processing stopped")
    
    def _process_loop(self):
        """Main processing loop"""
        while self._running:
            try:
                if not self._event_queue.empty():
                    _, event = self._event_queue.get(timeout=0.1)
                    self._process_event(event)
                else:
                    threading.Event().wait(0.01)  # Small sleep
            except Exception as e:
                logger.error(f"Event processing error: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # UTILITIES
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        return {
            **self._stats,
            "pending_events": self._event_queue.qsize(),
            "registered_handlers": sum(len(h) for h in self._handlers.values()),
            "global_handlers": len(self._global_handlers)
        }
    
    def get_event_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 100
    ) -> List[Event]:
        """Get processed event history"""
        events = self._processed_events[-limit:]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events
    
    def clear_history(self):
        """Clear event history"""
        self._processed_events.clear()

# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE DECORATORS
# ═══════════════════════════════════════════════════════════════════════════════

def on_event(event_type: EventType, priority: int = 0):
    """Decorator for event handlers"""
    def decorator(func):
        bus = EventBus()
        is_async = asyncio.iscoroutinefunction(func)
        bus.subscribe(event_type, func, priority=priority, is_async=is_async)
        return func
    return decorator

def on_events(*event_types: EventType, priority: int = 0):
    """Decorator for handling multiple event types"""
    def decorator(func):
        bus = EventBus()
        is_async = asyncio.iscoroutinefunction(func)
        for event_type in event_types:
            bus.subscribe(event_type, func, priority=priority, is_async=is_async)
        return func
    return decorator

# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

# Global event bus instance
event_bus = EventBus()

def publish(event_type: EventType, data: Dict[str, Any] = None, **kwargs) -> Event:
    """Convenience function to publish events"""
    return event_bus.publish(event_type, data, **kwargs)

def subscribe(event_type: EventType, handler: EventHandler, **kwargs) -> str:
    """Convenience function to subscribe to events"""
    return event_bus.subscribe(event_type, handler, **kwargs)

# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Test the event bus
    def test_handler(event: Event):
        print(f"Received event: {event.event_type.name} with data: {event.data}")
    
    # Subscribe
    bus = EventBus()
    bus.start()
    
    handler_id = bus.subscribe(EventType.SYSTEM_STARTUP, test_handler)
    
    # Publish
    bus.publish(
        EventType.SYSTEM_STARTUP,
        {"message": "System is starting up!"},
        source="test"
    )
    
    import time
    time.sleep(1)
    
    print(f"Stats: {bus.get_stats()}")
    
    bus.stop()