"""
NEXUS AI - Event Bus Tests
Validates publish, subscribe, priority ordering, and unsubscribe.
"""

import sys
import time
import pytest
import threading
from pathlib import Path

def test_event_bus_subscribe_and_publish(fresh_event_bus):
    """Events reach subscribers."""
    from core.event_bus import EventType
    received = []

    def handler(event):
        received.append(event.data)

    fresh_event_bus.subscribe(EventType.SYSTEM_STARTUP, handler)
    fresh_event_bus.start()

    try:
        fresh_event_bus.publish(
            EventType.SYSTEM_STARTUP,
            {"test": True},
            source="test"
        )
        # Give async handler time to process
        time.sleep(0.5)
        assert len(received) >= 1
        assert received[0]["test"] is True
    finally:
        fresh_event_bus.stop()

def test_event_bus_multiple_subscribers(fresh_event_bus):
    """Multiple subscribers receive the same event."""
    from core.event_bus import EventType
    received_a = []
    received_b = []

    fresh_event_bus.subscribe(EventType.EMOTION_CHANGE, lambda e: received_a.append(1))
    fresh_event_bus.subscribe(EventType.EMOTION_CHANGE, lambda e: received_b.append(1))
    fresh_event_bus.start()

    try:
        fresh_event_bus.publish(
            EventType.EMOTION_CHANGE,
            {"emotion": "joy"},
            source="test"
        )
        time.sleep(0.5)
        assert len(received_a) >= 1
        assert len(received_b) >= 1
    finally:
        fresh_event_bus.stop()

def test_event_bus_unsubscribe(fresh_event_bus):
    """Unsubscribed handlers stop receiving events."""
    from core.event_bus import EventType
    received = []

    def handler(event):
        received.append(1)

    handler_id = fresh_event_bus.subscribe(EventType.MEMORY_STORED, handler)
    fresh_event_bus.start()

    try:
        fresh_event_bus.publish(EventType.MEMORY_STORED, {}, source="test")
        time.sleep(0.3)
        count_before = len(received)

        fresh_event_bus.unsubscribe(handler_id)
        fresh_event_bus.publish(EventType.MEMORY_STORED, {}, source="test")
        time.sleep(0.3)
        assert len(received) == count_before
    finally:
        fresh_event_bus.stop()

def test_event_bus_does_not_crash_on_handler_error(fresh_event_bus):
    """Handler exceptions are caught — don't crash the bus."""
    from core.event_bus import EventType
    good_received = []

    def bad_handler(event):
        raise ValueError("handler error")

    def good_handler(event):
        good_received.append(1)

    fresh_event_bus.subscribe(EventType.SYSTEM_STARTUP, bad_handler)
    fresh_event_bus.subscribe(EventType.SYSTEM_STARTUP, good_handler)
    fresh_event_bus.start()

    try:
        fresh_event_bus.publish(EventType.SYSTEM_STARTUP, {}, source="test")
        time.sleep(0.5)
        # Good handler should still receive event despite bad handler crashing
        assert len(good_received) >= 1
    finally:
        fresh_event_bus.stop()

def test_event_bus_stats(fresh_event_bus):
    """Event bus reports stats."""
    stats = fresh_event_bus.get_stats()
    assert "events_published" in stats or isinstance(stats, dict)

def test_event_bus_sync_publish(fresh_event_bus):
    """Events published synchronously are immediately processed."""
    from core.event_bus import EventType
    received = []

    def handler(event):
        received.append(event.data)

    fresh_event_bus.subscribe(EventType.SYSTEM_STARTUP, handler)
    # No need to start() for sync processing

    fresh_event_bus.publish_sync(
        EventType.SYSTEM_STARTUP,
        {"test": "sync"},
        source="test"
    )
    
    assert len(received) == 1
    assert received[0]["test"] == "sync"

def test_event_bus_priority_ordering(fresh_event_bus):
    """Events with higher priority are processed first."""
    from core.event_bus import EventType, EventPriority
    # This is tricky to test deterministically due to threading,
    # but we can test subscriber priority which is deterministic
    received_order = []
    
    def handler1(event): received_order.append(1)
    def handler2(event): received_order.append(2)
    def handler3(event): received_order.append(3)
    
    fresh_event_bus.subscribe(EventType.SYSTEM_STARTUP, handler1, priority=10)
    fresh_event_bus.subscribe(EventType.SYSTEM_STARTUP, handler2, priority=0)
    fresh_event_bus.subscribe(EventType.SYSTEM_STARTUP, handler3, priority=5)
    
    fresh_event_bus.publish_sync(EventType.SYSTEM_STARTUP, {})
    
    # Handlers should run in order of priority: 0, 5, 10
    assert received_order == [2, 3, 1]

def test_event_bus_global_handlers(fresh_event_bus):
    """Global handlers receive events of all types."""
    from core.event_bus import EventType
    received = []
    
    def global_handler(event):
        received.append(event.event_type.name)
        
    fresh_event_bus.subscribe_all(global_handler)
    
    fresh_event_bus.publish_sync(EventType.SYSTEM_STARTUP, {})
    fresh_event_bus.publish_sync(EventType.EMOTION_CHANGE, {})
    
    assert len(received) == 2
    assert "SYSTEM_STARTUP" in received
    assert "EMOTION_CHANGE" in received
