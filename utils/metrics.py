"""
NEXUS AI - Metrics Collection System
Lightweight Prometheus-style metrics for observability.
No external dependencies — just in-memory counters, gauges, and histograms.
"""

import time
import threading
import psutil
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict


# ═══════════════════════════════════════════════════════════════════════════════
# METRIC TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class Counter:
    """Monotonically increasing counter."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._values: Dict[str, float] = defaultdict(float)
        self._lock = threading.Lock()

    def inc(self, labels: str = "", amount: float = 1.0):
        with self._lock:
            self._values[labels] += amount

    def get(self, labels: str = "") -> float:
        return self._values.get(labels, 0.0)

    def get_all(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._values)


class Gauge:
    """Value that can go up and down."""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._values: Dict[str, float] = defaultdict(float)
        self._lock = threading.Lock()

    def set(self, value: float, labels: str = ""):
        with self._lock:
            self._values[labels] = value

    def inc(self, amount: float = 1.0, labels: str = ""):
        with self._lock:
            self._values[labels] += amount

    def dec(self, amount: float = 1.0, labels: str = ""):
        with self._lock:
            self._values[labels] -= amount

    def get(self, labels: str = "") -> float:
        return self._values.get(labels, 0.0)

    def get_all(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._values)


class Histogram:
    """Tracks distribution of values with configurable buckets."""

    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0,
                       2.5, 5.0, 10.0, 30.0, 60.0, float('inf'))

    def __init__(self, name: str, description: str = "",
                 buckets: tuple = None):
        self.name = name
        self.description = description
        self._buckets = buckets or self.DEFAULT_BUCKETS
        self._counts: Dict[str, List[int]] = {}
        self._sums: Dict[str, float] = defaultdict(float)
        self._totals: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

    def observe(self, value: float, labels: str = ""):
        with self._lock:
            if labels not in self._counts:
                self._counts[labels] = [0] * len(self._buckets)

            self._sums[labels] += value
            self._totals[labels] += 1

            for i, bucket in enumerate(self._buckets):
                if value <= bucket:
                    self._counts[labels][i] += 1

    def get_stats(self, labels: str = "") -> dict:
        with self._lock:
            total = self._totals.get(labels, 0)
            s = self._sums.get(labels, 0.0)
            return {
                "count": total,
                "sum": s,
                "avg": s / total if total > 0 else 0.0,
            }

    def get_all(self) -> dict:
        with self._lock:
            result = {}
            for labels in self._totals:
                total = self._totals[labels]
                s = self._sums[labels]
                result[labels or "default"] = {
                    "count": total,
                    "sum": round(s, 3),
                    "avg": round(s / total, 3) if total > 0 else 0.0,
                }
            return result


# ═══════════════════════════════════════════════════════════════════════════════
# METRICS COLLECTOR SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

class MetricsCollector:
    """
    Central metrics collection for NEXUS.
    
    Pre-registers standard system metrics. Modules can register additional
    metrics via counter(), gauge(), histogram().
    
    Usage:
        metrics.counter("llm_requests").inc(labels="success")
        metrics.histogram("llm_latency").observe(1.23)
        report = metrics.get_all()
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

        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._startup_time = datetime.now()
        self._rlock = threading.RLock()

        # Register standard metrics
        self._register_standard_metrics()

    def _register_standard_metrics(self):
        """Register built-in system metrics."""
        # LLM metrics
        self.register_counter("nexus_llm_requests_total", "Total LLM requests")
        self.register_histogram("nexus_llm_request_duration_seconds", "LLM request latency")

        # Memory metrics
        self.register_counter("nexus_memory_operations_total", "Total memory operations")

        # Event bus metrics
        self.register_counter("nexus_events_published_total", "Total events published")
        self.register_counter("nexus_events_handled_total", "Total events handled")

        # Module health
        self.register_gauge("nexus_modules_healthy", "Number of healthy modules")
        self.register_gauge("nexus_modules_failed", "Number of failed modules")

        # Brain metrics
        self.register_counter("nexus_thoughts_processed_total", "Total thoughts processed")
        self.register_counter("nexus_responses_generated_total", "Total responses generated")
        self.register_histogram("nexus_response_duration_seconds", "Response generation time")

        # Process metrics
        self.register_gauge("nexus_process_memory_bytes", "Process RSS memory")
        self.register_gauge("nexus_process_cpu_percent", "Process CPU usage")
        self.register_gauge("nexus_process_threads", "Process thread count")

        # Autonomous cycle metrics
        self.register_counter("nexus_autonomous_cycles_total", "Total autonomous thinking cycles")
        self.register_histogram("nexus_cycle_duration_seconds", "Autonomous cycle duration")

        # Error metrics
        self.register_counter("nexus_errors_total", "Total errors by module")

    def register_counter(self, name: str, description: str = "") -> Counter:
        with self._rlock:
            if name not in self._counters:
                self._counters[name] = Counter(name, description)
            return self._counters[name]

    def register_gauge(self, name: str, description: str = "") -> Gauge:
        with self._rlock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(name, description)
            return self._gauges[name]

    def register_histogram(self, name: str, description: str = "",
                           buckets: tuple = None) -> Histogram:
        with self._rlock:
            if name not in self._histograms:
                self._histograms[name] = Histogram(name, description, buckets)
            return self._histograms[name]

    def counter(self, name: str) -> Counter:
        """Get or create a counter."""
        return self.register_counter(name)

    def gauge(self, name: str) -> Gauge:
        """Get or create a gauge."""
        return self.register_gauge(name)

    def histogram(
        self,
        name: str,
        description: str = "",
        buckets: tuple = None
    ) -> Histogram:
        """Get or create a histogram."""
        return self.register_histogram(name, description, buckets)

    def collect_process_metrics(self):
        """Collect current process metrics (call periodically)."""
        try:
            process = psutil.Process()
            mem_info = process.memory_info()
            self.gauge("nexus_process_memory_bytes").set(mem_info.rss)
            self.gauge("nexus_process_cpu_percent").set(process.cpu_percent())
            self.gauge("nexus_process_threads").set(process.num_threads())
        except Exception:
            pass

    def get_all(self) -> dict:
        """Get all metrics as a dictionary."""
        self.collect_process_metrics()

        result = {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self._startup_time).total_seconds(),
            "counters": {},
            "gauges": {},
            "histograms": {},
        }

        with self._rlock:
            for name, c in self._counters.items():
                values = c.get_all()
                if values:
                    result["counters"][name] = values
                else:
                    result["counters"][name] = {"": 0.0}

            for name, g in self._gauges.items():
                values = g.get_all()
                if values:
                    result["gauges"][name] = values
                else:
                    result["gauges"][name] = {"": 0.0}

            for name, h in self._histograms.items():
                result["histograms"][name] = h.get_all()

        return result

    def get_display(self) -> str:
        """Get formatted metrics string for console display."""
        data = self.get_all()
        lines = []
        lines.append(f"  ═══ 📊 System Metrics ═══")
        lines.append(f"  Uptime: {data['uptime_seconds']:.0f}s")

        # Counters
        lines.append(f"\n  ── Counters ──")
        for name, values in sorted(data["counters"].items()):
            if isinstance(values, dict):
                total = sum(values.values())
                if total > 0:
                    detail = ", ".join(
                        f"{k or 'total'}={v:.0f}" for k, v in values.items()
                        if v > 0
                    )
                    lines.append(f"  {name}: {detail}")
            else:
                if values > 0:
                    lines.append(f"  {name}: {values}")

        # Gauges
        lines.append(f"\n  ── Gauges ──")
        for name, values in sorted(data["gauges"].items()):
            if isinstance(values, dict):
                for label, val in values.items():
                    if val != 0:
                        if "memory" in name:
                            lines.append(
                                f"  {name}: {val / 1024 / 1024:.1f} MB"
                            )
                        elif "cpu" in name:
                            lines.append(f"  {name}: {val:.1f}%")
                        else:
                            lines.append(f"  {name}: {val}")

        # Histograms
        lines.append(f"\n  ── Histograms ──")
        for name, values in sorted(data["histograms"].items()):
            if values:
                for label, stats in values.items():
                    if stats.get("count", 0) > 0:
                        lines.append(
                            f"  {name}: count={stats['count']}, "
                            f"avg={stats['avg']:.3f}s, "
                            f"sum={stats['sum']:.3f}s"
                        )

        return "\n".join(lines)


# Global singleton
metrics = MetricsCollector()
