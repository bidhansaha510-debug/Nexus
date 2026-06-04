"""
NEXUS AI - Resilience Utilities
Circuit breakers, retry logic, and health tracking for robust operation.
"""

import time
import threading
import functools
import traceback
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque

from utils.logger import get_logger

logger = get_logger("resilience")

T = TypeVar("T")


# ═══════════════════════════════════════════════════════════════════════════════
# CIRCUIT BREAKER
# ═══════════════════════════════════════════════════════════════════════════════

class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing — fast-fail all calls
    HALF_OPEN = "half_open" # Testing — allow one probe call


class CircuitBreaker:
    """
    Circuit breaker pattern for subsystem calls.
    
    After `failure_threshold` consecutive failures, the circuit opens and
    all subsequent calls fail fast without executing. After `reset_timeout`
    seconds, a single probe call is allowed through. If it succeeds, the
    circuit closes; if it fails, the timeout resets.
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        reset_timeout: float = 60.0,
        on_open: Optional[Callable] = None,
        on_close: Optional[Callable] = None,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.on_open = on_open
        self.on_close = on_close

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._success_count = 0
        self._total_calls = 0
        self._total_failures = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                # Check if reset timeout has elapsed
                if (self._last_failure_time and
                        time.time() - self._last_failure_time >= self.reset_timeout):
                    self._state = CircuitState.HALF_OPEN
            return self._state

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute func through the circuit breaker."""
        current_state = self.state

        if current_state == CircuitState.OPEN:
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN after "
                f"{self._failure_count} failures. Retry after "
                f"{self.reset_timeout}s."
            )

        self._total_calls += 1
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise

    def _on_success(self):
        with self._lock:
            self._failure_count = 0
            self._success_count += 1
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                logger.info(f"Circuit breaker '{self.name}' CLOSED (recovered)")
                if self.on_close:
                    try:
                        self.on_close()
                    except Exception:
                        pass

    def _on_failure(self, error: Exception):
        with self._lock:
            self._failure_count += 1
            self._total_failures += 1
            self._last_failure_time = time.time()

            if (self._state == CircuitState.CLOSED and
                    self._failure_count >= self.failure_threshold):
                self._state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker '{self.name}' OPENED after "
                    f"{self._failure_count} consecutive failures: {error}"
                )
                if self.on_open:
                    try:
                        self.on_open()
                    except Exception:
                        pass
            elif self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker '{self.name}' re-OPENED (probe failed): {error}"
                )

    def reset(self):
        """Manually reset the circuit breaker."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None

    def get_stats(self) -> dict:
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "total_calls": self._total_calls,
            "total_failures": self._total_failures,
            "success_count": self._success_count,
        }


class CircuitBreakerOpenError(Exception):
    """Raised when a circuit breaker is open."""
    pass


# ═══════════════════════════════════════════════════════════════════════════════
# RETRY WITH BACKOFF
# ═══════════════════════════════════════════════════════════════════════════════

def retry_with_backoff(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 0.5,
    max_delay: float = 30.0,
    retryable_exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None,
):
    """
    Decorator that retries a function with exponential backoff.
    
    Usage:
        @retry_with_backoff(max_retries=3, backoff_factor=2.0)
        def call_api():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            delay = initial_delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        if on_retry:
                            try:
                                on_retry(attempt + 1, e)
                            except Exception:
                                pass
                        logger.debug(
                            f"Retry {attempt + 1}/{max_retries} for "
                            f"{func.__name__}: {e} (delay={delay:.1f}s)"
                        )
                        time.sleep(delay)
                        delay = min(delay * backoff_factor, max_delay)
                    else:
                        logger.warning(
                            f"All {max_retries} retries exhausted for "
                            f"{func.__name__}: {e}"
                        )
            raise last_exception
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE HEALTH TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

class ModuleStatus(Enum):
    NOT_LOADED = "not_loaded"
    LOADING = "loading"
    HEALTHY = "healthy"
    DEGRADED = "degraded"   # Started with warnings
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class ModuleHealthEntry:
    """Health status for a single module."""
    name: str
    status: ModuleStatus = ModuleStatus.NOT_LOADED
    load_time_ms: float = 0.0
    start_time_ms: float = 0.0
    error: Optional[str] = None
    error_traceback: Optional[str] = None
    last_check: Optional[datetime] = None
    started_at: Optional[datetime] = None
    check_count: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status.value,
            "load_time_ms": round(self.load_time_ms, 1),
            "start_time_ms": round(self.start_time_ms, 1),
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
        }


class HealthRegistry:
    """
    Central registry tracking the health of all NEXUS modules.
    
    Usage:
        health = HealthRegistry()
        
        with health.track_load("consciousness"):
            load_consciousness()
        
        with health.track_start("consciousness"):
            consciousness.start()
        
        report = health.get_report()
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
        self._modules: Dict[str, ModuleHealthEntry] = {}
        self._startup_time = datetime.now()
        self._rlock = threading.RLock()

    def _get_or_create(self, name: str) -> ModuleHealthEntry:
        if name not in self._modules:
            self._modules[name] = ModuleHealthEntry(name=name)
        return self._modules[name]

    class _TrackContext:
        """Context manager for tracking load/start operations."""
        def __init__(self, registry: 'HealthRegistry', name: str, phase: str):
            self.registry = registry
            self.name = name
            self.phase = phase  # "load" or "start"
            self.start_time = 0.0

        def __enter__(self):
            self.start_time = time.time()
            with self.registry._rlock:
                entry = self.registry._get_or_create(self.name)
                entry.status = ModuleStatus.LOADING
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            elapsed_ms = (time.time() - self.start_time) * 1000
            with self.registry._rlock:
                entry = self.registry._get_or_create(self.name)
                if exc_type is None:
                    entry.status = ModuleStatus.HEALTHY
                    entry.started_at = datetime.now()
                    if self.phase == "load":
                        entry.load_time_ms = elapsed_ms
                    else:
                        entry.start_time_ms = elapsed_ms
                    entry.error = None
                    entry.error_traceback = None
                else:
                    entry.status = ModuleStatus.FAILED
                    entry.error = str(exc_val)
                    entry.error_traceback = traceback.format_exc()
                    if self.phase == "load":
                        entry.load_time_ms = elapsed_ms
                    else:
                        entry.start_time_ms = elapsed_ms
            # Suppress exception — we want graceful degradation
            return True

    def track_load(self, name: str):
        """Context manager that tracks module loading."""
        return self._TrackContext(self, name, "load")

    def track_start(self, name: str):
        """Context manager that tracks module start."""
        return self._TrackContext(self, name, "start")

    def report_healthy(self, name: str):
        """Mark a module as healthy."""
        with self._rlock:
            entry = self._get_or_create(name)
            entry.status = ModuleStatus.HEALTHY
            entry.last_check = datetime.now()
            entry.check_count += 1

    def report_degraded(self, name: str, reason: str = ""):
        """Mark a module as degraded (working with issues)."""
        with self._rlock:
            entry = self._get_or_create(name)
            entry.status = ModuleStatus.DEGRADED
            entry.error = reason
            entry.last_check = datetime.now()

    def report_failed(self, name: str, error: str = "", tb: str = ""):
        """Mark a module as failed."""
        with self._rlock:
            entry = self._get_or_create(name)
            entry.status = ModuleStatus.FAILED
            entry.error = error
            entry.error_traceback = tb
            entry.last_check = datetime.now()

    def get_report(self) -> dict:
        """Get full health report."""
        with self._rlock:
            modules = {}
            healthy = 0
            failed = 0
            degraded = 0
            not_loaded = 0

            for name, entry in self._modules.items():
                modules[name] = entry.to_dict()
                if entry.status == ModuleStatus.HEALTHY:
                    healthy += 1
                elif entry.status == ModuleStatus.FAILED:
                    failed += 1
                elif entry.status == ModuleStatus.DEGRADED:
                    degraded += 1
                elif entry.status == ModuleStatus.NOT_LOADED:
                    not_loaded += 1

            total_load_ms = sum(e.load_time_ms for e in self._modules.values())
            total_start_ms = sum(e.start_time_ms for e in self._modules.values())

            return {
                "system_status": "healthy" if failed == 0 else (
                    "degraded" if healthy > 0 else "critical"
                ),
                "total_modules": len(self._modules),
                "healthy": healthy,
                "failed": failed,
                "degraded": degraded,
                "not_loaded": not_loaded,
                "total_load_time_ms": round(total_load_ms, 1),
                "total_start_time_ms": round(total_start_ms, 1),
                "uptime_seconds": (datetime.now() - self._startup_time).total_seconds(),
                "modules": modules,
                "failed_modules": [
                    {"name": e.name, "error": e.error}
                    for e in self._modules.values()
                    if e.status == ModuleStatus.FAILED
                ],
            }

    def get_status_display(self) -> str:
        """Get a formatted health status string for console display."""
        report = self.get_report()
        lines = []
        lines.append(f"  ═══ 🏥 System Health Report ═══")
        lines.append(f"  Status: {report['system_status'].upper()}")
        lines.append(
            f"  Modules: {report['healthy']} healthy, "
            f"{report['degraded']} degraded, "
            f"{report['failed']} failed, "
            f"{report['not_loaded']} not loaded"
        )
        lines.append(
            f"  Load time: {report['total_load_time_ms']:.0f}ms | "
            f"Start time: {report['total_start_time_ms']:.0f}ms"
        )
        lines.append(
            f"  Uptime: {report['uptime_seconds']:.0f}s"
        )

        # Show failed modules
        if report['failed_modules']:
            lines.append(f"\n  ── Failed Modules ──")
            for fm in report['failed_modules']:
                lines.append(f"  ❌ {fm['name']}: {fm['error']}")

        # Show all modules by status
        lines.append(f"\n  ── Module Status ──")
        status_icons = {
            "healthy": "✅",
            "degraded": "⚠️",
            "failed": "❌",
            "not_loaded": "⬜",
            "loading": "⏳",
            "stopped": "⏹️",
        }
        for name, info in sorted(report['modules'].items()):
            icon = status_icons.get(info['status'], "❓")
            timing = ""
            if info['load_time_ms'] > 0:
                timing = f" ({info['load_time_ms']:.0f}ms)"
            lines.append(f"  {icon} {name}{timing}")

        return "\n".join(lines)


# Global singleton
health_registry = HealthRegistry()


def safe_start(module: Any, module_name: str, max_retries: int = 0, **kwargs) -> bool:
    """
    Safely starts a module with automatic health tracking, retry logic,
    and graceful degradation on failure.
    
    Returns:
        bool: True if started successfully, False if failed/degraded.
    """
    @retry_with_backoff(max_retries=max_retries, initial_delay=0.5)
    def _attempt_start():
        if hasattr(module, "start"):
            module.start(**kwargs)
        elif callable(module):
            module(**kwargs)
            
    with health_registry.track_start(module_name):
        _attempt_start()
        
    entry = health_registry._modules.get(module_name)
    if entry and entry.status == ModuleStatus.HEALTHY:
        return True
    
    logger.error(f"Module '{module_name}' failed to start. System may run in degraded mode.")
    return False
