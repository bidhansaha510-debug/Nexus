"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     NEXUS — System Health Monitor                          ║
║                                                                            ║
║  Real-time system resource tracking with composite health scoring,         ║
║  configurable alert thresholds, exponential moving average trend           ║
║  detection, resource hog identification, and SQLite-backed 24hr history.   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
import os
import platform
import shutil
import sqlite3
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import psutil

from core.event_bus import EventType, publish

logger = logging.getLogger("NEXUS.HealthMonitor")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

class AlertSeverity:
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ResourceSnapshot:
    """Single point-in-time capture of all system resources"""
    timestamp: str = ""

    # CPU
    cpu_percent_total: float = 0.0
    cpu_percent_per_core: List[float] = field(default_factory=list)
    cpu_frequency_mhz: float = 0.0
    cpu_count_logical: int = 0
    cpu_count_physical: int = 0
    cpu_load_avg_1m: float = 0.0

    # Memory
    memory_total_gb: float = 0.0
    memory_used_gb: float = 0.0
    memory_available_gb: float = 0.0
    memory_percent: float = 0.0
    swap_total_gb: float = 0.0
    swap_used_gb: float = 0.0
    swap_percent: float = 0.0

    # Disk
    disk_total_gb: float = 0.0
    disk_used_gb: float = 0.0
    disk_free_gb: float = 0.0
    disk_percent: float = 0.0
    disk_read_mb_s: float = 0.0
    disk_write_mb_s: float = 0.0

    # Network
    net_bytes_sent_per_sec: float = 0.0
    net_bytes_recv_per_sec: float = 0.0
    net_connections_count: int = 0

    # GPU (optional)
    gpu_available: bool = False
    gpu_name: str = ""
    gpu_utilization_percent: float = 0.0
    gpu_memory_used_mb: float = 0.0
    gpu_memory_total_mb: float = 0.0
    gpu_temperature_c: float = 0.0

    # Battery (optional)
    battery_available: bool = False
    battery_percent: float = 0.0
    battery_plugged: bool = False
    battery_time_left_minutes: float = -1.0

    # Process count
    process_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HealthScore:
    """Composite health score from all resources"""
    overall: float = 1.0          # 0.0 (critical) to 1.0 (healthy)
    cpu_health: float = 1.0
    memory_health: float = 1.0
    disk_health: float = 1.0
    gpu_health: float = 1.0
    battery_health: float = 1.0
    network_health: float = 1.0
    severity: str = AlertSeverity.NORMAL

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ResourceAlert:
    """Alert when a resource crosses a threshold"""
    alert_id: str = ""
    resource: str = ""
    severity: str = AlertSeverity.WARNING
    message: str = ""
    current_value: float = 0.0
    threshold: float = 0.0
    timestamp: str = ""
    resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ResourceTrend:
    """Exponential moving average trend for a resource"""
    resource: str = ""
    ema_short: float = 0.0    # short-term EMA (alpha=0.3, ~last 5 readings)
    ema_long: float = 0.0     # long-term EMA (alpha=0.05, ~last 30 readings)
    direction: str = "stable"  # "rising", "falling", "stable"
    slope: float = 0.0        # rate of change

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ResourceHog:
    """A process consuming excessive resources"""
    pid: int = 0
    name: str = ""
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    is_runaway: bool = False  # consistent high CPU over multiple checks
    first_seen: str = ""
    check_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM HEALTH MONITOR
# ═══════════════════════════════════════════════════════════════════════════════

class SystemHealthMonitor:
    """
    Monitors system resource health in real-time.
    
    Features:
    - Per-core CPU, RAM, disk, GPU, battery, network tracking
    - Composite health score (0.0 – 1.0)
    - Configurable alert thresholds (warning / critical)
    - Exponential moving average trend detection
    - Resource hog identification with runaway detection
    - SQLite-backed 24hr rolling history
    """

    def __init__(self):
        # ── Configuration ──
        self._check_interval: float = 10.0          # seconds
        self._cpu_warning: float = 80.0
        self._cpu_critical: float = 95.0
        self._memory_warning: float = 80.0
        self._memory_critical: float = 95.0
        self._disk_warning: float = 85.0
        self._disk_critical: float = 95.0
        self._track_gpu: bool = True
        self._track_battery: bool = True
        self._history_retention_hours: int = 24
        self._hog_cpu_threshold: float = 30.0       # % CPU to be considered a hog
        self._hog_memory_threshold_mb: float = 500.0 # MB to be considered a hog
        self._runaway_check_threshold: int = 6       # N consecutive checks = runaway

        # ── State ──
        self._running: bool = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        self._current_snapshot: ResourceSnapshot = ResourceSnapshot()
        self._health_score: HealthScore = HealthScore()
        self._snapshot_history: deque = deque(maxlen=8640)  # 24hr at 10s interval
        self._active_alerts: Dict[str, ResourceAlert] = {}
        self._alert_history: deque = deque(maxlen=200)

        # Trends (EMA)
        self._trends: Dict[str, ResourceTrend] = {
            "cpu": ResourceTrend(resource="cpu"),
            "memory": ResourceTrend(resource="memory"),
            "disk_io": ResourceTrend(resource="disk_io"),
            "network": ResourceTrend(resource="network"),
        }

        # Resource hogs
        self._resource_hogs: Dict[int, ResourceHog] = {}  # pid -> hog

        # Network I/O baseline (for per-second calc)
        self._last_net_io: Optional[Any] = None
        self._last_disk_io: Optional[Any] = None
        self._last_check_time: float = 0.0

        # Stats
        self._total_checks: int = 0
        self._total_alerts_fired: int = 0
        self._start_time: Optional[datetime] = None

        # Database
        self._db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "health_history.db"
        )
        self._db_conn: Optional[sqlite3.Connection] = None
        self._init_database()

    # ═══════════════════════════════════════════════════════════════════════════
    # DATABASE
    # ═══════════════════════════════════════════════════════════════════════════

    def _init_database(self):
        """Initialize SQLite database for health history"""
        try:
            self._db_conn = sqlite3.connect(
                self._db_path, check_same_thread=False
            )
            self._db_conn.row_factory = sqlite3.Row
            self._db_conn.execute("PRAGMA journal_mode=WAL")
            self._db_conn.execute("PRAGMA synchronous=NORMAL")

            self._db_conn.executescript("""
                CREATE TABLE IF NOT EXISTS health_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    cpu_percent REAL,
                    memory_percent REAL,
                    disk_percent REAL,
                    gpu_percent REAL,
                    net_recv_bps REAL,
                    net_sent_bps REAL,
                    health_score REAL,
                    severity TEXT,
                    snapshot_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS health_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT,
                    resource TEXT,
                    severity TEXT,
                    message TEXT,
                    current_value REAL,
                    threshold REAL,
                    timestamp TEXT,
                    resolved INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_snapshots_time
                    ON health_snapshots(timestamp);
                CREATE INDEX IF NOT EXISTS idx_alerts_time
                    ON health_alerts(timestamp);
            """)

            self._db_conn.commit()
            logger.debug("Health database initialized")

        except Exception as e:
            logger.error(f"Failed to initialize health DB: {e}")

    def _db_execute(
        self, query: str, params: tuple = (), fetch: bool = False
    ):
        """Execute a database query with error handling"""
        try:
            if not self._db_conn:
                return [] if fetch else None
            cursor = self._db_conn.execute(query, params)
            if fetch:
                return [dict(row) for row in cursor.fetchall()]
            self._db_conn.commit()
            return None
        except Exception as e:
            logger.error(f"Health DB error: {e}")
            return [] if fetch else None

    def _cleanup_old_records(self):
        """Remove records older than retention period"""
        cutoff = (
            datetime.now() - timedelta(hours=self._history_retention_hours)
        ).isoformat()
        self._db_execute(
            "DELETE FROM health_snapshots WHERE timestamp < ?", (cutoff,)
        )
        self._db_execute(
            "DELETE FROM health_alerts WHERE timestamp < ? AND resolved = 1",
            (cutoff,)
        )
        logger.debug("Health DB: old records cleaned up")

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start the health monitoring loop"""
        if self._running:
            return
        self._running = True
        self._start_time = datetime.now()

        # Get initial I/O baselines
        try:
            self._last_net_io = psutil.net_io_counters()
            self._last_disk_io = psutil.disk_io_counters()
            self._last_check_time = time.time()
        except Exception:
            pass

        # Cleanup old records on startup
        self._cleanup_old_records()

        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="HealthMonitor"
        )
        self._monitor_thread.start()
        logger.info("🏥 SystemHealthMonitor ACTIVE")

    def stop(self):
        """Stop the health monitoring loop"""
        if not self._running:
            return
        self._running = False

        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)

        if self._db_conn:
            try:
                self._db_conn.close()
            except Exception:
                pass

        logger.info("SystemHealthMonitor stopped")

    # ═══════════════════════════════════════════════════════════════════════════
    # MONITORING LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    def _monitoring_loop(self):
        """Main monitoring loop — runs every check_interval seconds"""
        logger.info("Health monitoring loop started")

        while self._running:
            try:
                snapshot = self._collect_snapshot()
                with self._lock:
                    self._current_snapshot = snapshot
                    self._snapshot_history.append(snapshot)

                self._calculate_health_score(snapshot)
                self._check_thresholds(snapshot)
                self._update_trends(snapshot)
                self._detect_resource_hogs()
                self._persist_snapshot(snapshot)

                self._total_checks += 1

                # Periodic cleanup (every ~1 hour = 360 checks at 10s)
                if self._total_checks % 360 == 0:
                    self._cleanup_old_records()

                time.sleep(self._check_interval)

            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                time.sleep(15)

    # ═══════════════════════════════════════════════════════════════════════════
    # DATA COLLECTION
    # ═══════════════════════════════════════════════════════════════════════════

    def _collect_snapshot(self) -> ResourceSnapshot:
        """Collect a complete snapshot of system resources"""
        snap = ResourceSnapshot()
        snap.timestamp = datetime.now().isoformat()
        now = time.time()
        elapsed = max(now - self._last_check_time, 0.1)

        # ── CPU ──
        try:
            snap.cpu_percent_total = psutil.cpu_percent(interval=0)
            snap.cpu_percent_per_core = psutil.cpu_percent(
                interval=0, percpu=True
            )
            freq = psutil.cpu_freq()
            if freq:
                snap.cpu_frequency_mhz = freq.current
            snap.cpu_count_logical = psutil.cpu_count(logical=True) or 0
            snap.cpu_count_physical = psutil.cpu_count(logical=False) or 0

            # Load average (Unix-like only)
            if hasattr(os, "getloadavg"):
                snap.cpu_load_avg_1m = os.getloadavg()[0]
            else:
                snap.cpu_load_avg_1m = snap.cpu_percent_total / 100.0
        except Exception as e:
            logger.debug(f"CPU collection error: {e}")

        # ── Memory ──
        try:
            mem = psutil.virtual_memory()
            snap.memory_total_gb = round(mem.total / (1024 ** 3), 2)
            snap.memory_used_gb = round(mem.used / (1024 ** 3), 2)
            snap.memory_available_gb = round(mem.available / (1024 ** 3), 2)
            snap.memory_percent = mem.percent

            swap = psutil.swap_memory()
            snap.swap_total_gb = round(swap.total / (1024 ** 3), 2)
            snap.swap_used_gb = round(swap.used / (1024 ** 3), 2)
            snap.swap_percent = swap.percent
        except Exception as e:
            logger.debug(f"Memory collection error: {e}")

        # ── Disk ──
        try:
            disk = shutil.disk_usage("/") if platform.system() != "Windows" \
                else shutil.disk_usage("C:\\")
            snap.disk_total_gb = round(disk.total / (1024 ** 3), 2)
            snap.disk_used_gb = round(disk.used / (1024 ** 3), 2)
            snap.disk_free_gb = round(disk.free / (1024 ** 3), 2)
            snap.disk_percent = round(
                (disk.used / disk.total) * 100, 1
            ) if disk.total > 0 else 0.0

            # Disk I/O per second
            current_disk_io = psutil.disk_io_counters()
            if current_disk_io and self._last_disk_io:
                snap.disk_read_mb_s = round(
                    (current_disk_io.read_bytes -
                     self._last_disk_io.read_bytes) / elapsed / (1024 ** 2), 2
                )
                snap.disk_write_mb_s = round(
                    (current_disk_io.write_bytes -
                     self._last_disk_io.write_bytes) / elapsed / (1024 ** 2), 2
                )
            self._last_disk_io = current_disk_io
        except Exception as e:
            logger.debug(f"Disk collection error: {e}")

        # ── Network ──
        try:
            current_net_io = psutil.net_io_counters()
            if current_net_io and self._last_net_io:
                snap.net_bytes_sent_per_sec = round(
                    (current_net_io.bytes_sent -
                     self._last_net_io.bytes_sent) / elapsed, 1
                )
                snap.net_bytes_recv_per_sec = round(
                    (current_net_io.bytes_recv -
                     self._last_net_io.bytes_recv) / elapsed, 1
                )
            self._last_net_io = current_net_io

            snap.net_connections_count = len(psutil.net_connections(kind="inet"))
        except Exception as e:
            logger.debug(f"Network collection error: {e}")

        # ── GPU (nvidia-smi) ──
        if self._track_gpu:
            self._collect_gpu(snap)

        # ── Battery ──
        if self._track_battery:
            self._collect_battery(snap)

        # ── Process count ──
        try:
            snap.process_count = len(psutil.pids())
        except Exception:
            pass

        self._last_check_time = now
        return snap

    def _collect_gpu(self, snap: ResourceSnapshot):
        """Try to collect GPU metrics via nvidia-smi"""
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                    "--format=csv,noheader,nounits"
                ],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
                if platform.system() == "Windows" else 0
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split(",")
                if len(parts) >= 5:
                    def _safe_float(val: str) -> float:
                        """Parse nvidia-smi value, returning 0.0 for N/A or non-numeric."""
                        val = val.strip().strip("[]")
                        try:
                            return float(val)
                        except (ValueError, TypeError):
                            return 0.0

                    snap.gpu_available = True
                    snap.gpu_name = parts[0].strip()
                    snap.gpu_utilization_percent = _safe_float(parts[1])
                    snap.gpu_memory_used_mb = _safe_float(parts[2])
                    snap.gpu_memory_total_mb = _safe_float(parts[3])
                    snap.gpu_temperature_c = _safe_float(parts[4])
        except FileNotFoundError:
            # nvidia-smi not available
            pass
        except Exception as e:
            logger.debug(f"GPU collection error: {e}")

    def _collect_battery(self, snap: ResourceSnapshot):
        """Collect battery status"""
        try:
            battery = psutil.sensors_battery()
            if battery:
                snap.battery_available = True
                snap.battery_percent = battery.percent
                snap.battery_plugged = battery.power_plugged
                if battery.secsleft and battery.secsleft > 0:
                    snap.battery_time_left_minutes = round(
                        battery.secsleft / 60, 1
                    )
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════════════════════
    # HEALTH SCORE
    # ═══════════════════════════════════════════════════════════════════════════

    def _calculate_health_score(self, snap: ResourceSnapshot):
        """Calculate composite health score from resource metrics"""
        score = HealthScore()

        # CPU health: 100% usage → 0.0 health
        score.cpu_health = max(0.0, 1.0 - (snap.cpu_percent_total / 100.0))

        # Memory health
        score.memory_health = max(0.0, 1.0 - (snap.memory_percent / 100.0))

        # Disk health (space)
        score.disk_health = max(0.0, 1.0 - (snap.disk_percent / 100.0))

        # GPU health
        if snap.gpu_available:
            score.gpu_health = max(
                0.0, 1.0 - (snap.gpu_utilization_percent / 100.0)
            )
        else:
            score.gpu_health = 1.0

        # Battery health
        if snap.battery_available and not snap.battery_plugged:
            score.battery_health = snap.battery_percent / 100.0
        else:
            score.battery_health = 1.0

        # Network health (basic — high throughput isn't necessarily bad)
        score.network_health = 1.0

        # ── Weighted composite ──
        weights = {
            "cpu": 0.30,
            "memory": 0.30,
            "disk": 0.15,
            "gpu": 0.10,
            "battery": 0.10,
            "network": 0.05,
        }

        score.overall = round(
            score.cpu_health * weights["cpu"] +
            score.memory_health * weights["memory"] +
            score.disk_health * weights["disk"] +
            score.gpu_health * weights["gpu"] +
            score.battery_health * weights["battery"] +
            score.network_health * weights["network"],
            3
        )

        # Severity
        if score.overall >= 0.6:
            score.severity = AlertSeverity.NORMAL
        elif score.overall >= 0.3:
            score.severity = AlertSeverity.WARNING
        else:
            score.severity = AlertSeverity.CRITICAL

        with self._lock:
            self._health_score = score

    # ═══════════════════════════════════════════════════════════════════════════
    # ALERTS
    # ═══════════════════════════════════════════════════════════════════════════

    def _check_thresholds(self, snap: ResourceSnapshot):
        """Check resource values against thresholds and fire alerts"""
        checks = [
            ("cpu", snap.cpu_percent_total,
             self._cpu_warning, self._cpu_critical, "CPU usage"),
            ("memory", snap.memory_percent,
             self._memory_warning, self._memory_critical, "Memory usage"),
            ("disk", snap.disk_percent,
             self._disk_warning, self._disk_critical, "Disk usage"),
        ]

        if snap.gpu_available:
            checks.append((
                "gpu", snap.gpu_utilization_percent,
                80.0, 95.0, "GPU usage"
            ))

        if snap.battery_available and not snap.battery_plugged:
            # Battery: alert when LOW (inverted logic)
            checks.append((
                "battery_low", 100.0 - snap.battery_percent,
                80.0, 90.0, "Battery low"
            ))

        for resource, value, warn_thresh, crit_thresh, label in checks:
            alert_id = f"alert_{resource}"

            if value >= crit_thresh:
                self._fire_alert(
                    alert_id, resource, AlertSeverity.CRITICAL,
                    f"{label} CRITICAL: {value:.1f}% (threshold: {crit_thresh:.0f}%)",
                    value, crit_thresh
                )
            elif value >= warn_thresh:
                self._fire_alert(
                    alert_id, resource, AlertSeverity.WARNING,
                    f"{label} WARNING: {value:.1f}% (threshold: {warn_thresh:.0f}%)",
                    value, warn_thresh
                )
            else:
                # Resolve existing alert if any
                if alert_id in self._active_alerts:
                    self._resolve_alert(alert_id)

    def _fire_alert(
        self, alert_id: str, resource: str, severity: str,
        message: str, current_value: float, threshold: float
    ):
        """Fire or update an alert"""
        now = datetime.now().isoformat()

        if alert_id not in self._active_alerts:
            alert = ResourceAlert(
                alert_id=alert_id,
                resource=resource,
                severity=severity,
                message=message,
                current_value=current_value,
                threshold=threshold,
                timestamp=now
            )
            self._active_alerts[alert_id] = alert
            self._alert_history.append(alert)
            self._total_alerts_fired += 1

            # Persist
            self._db_execute(
                """INSERT INTO health_alerts
                   (alert_id, resource, severity, message,
                    current_value, threshold, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (alert_id, resource, severity, message,
                 current_value, threshold, now)
            )

            # Publish event
            publish(
                EventType.MONITORING_ANOMALY,
                {
                    "type": "health_alert",
                    "alert_id": alert_id,
                    "resource": resource,
                    "severity": severity,
                    "message": message,
                    "value": current_value,
                    "threshold": threshold
                },
                source="health_monitor"
            )

            logger.warning(f"🚨 Health alert: {message}")
        else:
            # Update existing alert
            existing = self._active_alerts[alert_id]
            existing.severity = severity
            existing.message = message
            existing.current_value = current_value

    def _resolve_alert(self, alert_id: str):
        """Mark an alert as resolved"""
        if alert_id in self._active_alerts:
            alert = self._active_alerts.pop(alert_id)
            alert.resolved = True
            self._alert_history.append(alert)

            self._db_execute(
                "UPDATE health_alerts SET resolved = 1 WHERE alert_id = ? AND resolved = 0",
                (alert_id,)
            )

            logger.info(f"✅ Alert resolved: {alert.resource}")

    # ═══════════════════════════════════════════════════════════════════════════
    # TREND DETECTION (EMA)
    # ═══════════════════════════════════════════════════════════════════════════

    def _update_trends(self, snap: ResourceSnapshot):
        """Update exponential moving averages for trend detection"""
        alpha_short = 0.3    # responsive to recent changes
        alpha_long = 0.05    # smooth long-term trend

        metrics = {
            "cpu": snap.cpu_percent_total,
            "memory": snap.memory_percent,
            "disk_io": snap.disk_read_mb_s + snap.disk_write_mb_s,
            "network": (
                snap.net_bytes_sent_per_sec + snap.net_bytes_recv_per_sec
            ) / 1024.0,  # convert to KB/s
        }

        for resource, value in metrics.items():
            trend = self._trends[resource]

            if self._total_checks <= 1:
                # Initialize EMAs with first value
                trend.ema_short = value
                trend.ema_long = value
            else:
                trend.ema_short = (
                    alpha_short * value +
                    (1 - alpha_short) * trend.ema_short
                )
                trend.ema_long = (
                    alpha_long * value +
                    (1 - alpha_long) * trend.ema_long
                )

            # Direction
            diff = trend.ema_short - trend.ema_long
            if abs(diff) < 2.0:
                trend.direction = "stable"
            elif diff > 0:
                trend.direction = "rising"
            else:
                trend.direction = "falling"

            trend.slope = round(diff, 2)

    # ═══════════════════════════════════════════════════════════════════════════
    # RESOURCE HOGS
    # ═══════════════════════════════════════════════════════════════════════════

    def _detect_resource_hogs(self):
        """Identify top resource-consuming processes"""
        try:
            current_hogs: Dict[int, ResourceHog] = {}
            now = datetime.now().isoformat()

            for proc in psutil.process_iter(
                ["pid", "name", "cpu_percent", "memory_info"]
            ):
                try:
                    info = proc.info
                    pid = info["pid"]
                    cpu = info.get("cpu_percent", 0) or 0
                    mem_bytes = (
                        info.get("memory_info").rss
                        if info.get("memory_info") else 0
                    )
                    mem_mb = mem_bytes / (1024 ** 2)

                    if (cpu > self._hog_cpu_threshold or
                            mem_mb > self._hog_memory_threshold_mb):
                        # Check if already tracked
                        if pid in self._resource_hogs:
                            hog = self._resource_hogs[pid]
                            hog.cpu_percent = cpu
                            hog.memory_mb = round(mem_mb, 1)
                            hog.check_count += 1
                            hog.is_runaway = (
                                hog.check_count >= self._runaway_check_threshold
                                and cpu > self._hog_cpu_threshold
                            )
                        else:
                            hog = ResourceHog(
                                pid=pid,
                                name=info.get("name", "unknown"),
                                cpu_percent=cpu,
                                memory_mb=round(mem_mb, 1),
                                first_seen=now,
                                check_count=1
                            )

                        current_hogs[pid] = hog
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            self._resource_hogs = current_hogs

        except Exception as e:
            logger.debug(f"Resource hog detection error: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _persist_snapshot(self, snap: ResourceSnapshot):
        """Save snapshot to database (every 6th check = ~1 min at 10s interval)"""
        if self._total_checks % 6 != 0:
            return

        self._db_execute(
            """INSERT INTO health_snapshots
               (timestamp, cpu_percent, memory_percent, disk_percent,
                gpu_percent, net_recv_bps, net_sent_bps,
                health_score, severity, snapshot_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                snap.timestamp,
                snap.cpu_percent_total,
                snap.memory_percent,
                snap.disk_percent,
                snap.gpu_utilization_percent if snap.gpu_available else None,
                snap.net_bytes_recv_per_sec,
                snap.net_bytes_sent_per_sec,
                self._health_score.overall,
                self._health_score.severity,
                json.dumps(snap.to_dict(), default=str)
            )
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def get_current_snapshot(self) -> Dict[str, Any]:
        """Get current resource snapshot"""
        with self._lock:
            return self._current_snapshot.to_dict()

    def get_health_score(self) -> Dict[str, Any]:
        """Get current composite health score"""
        with self._lock:
            return self._health_score.to_dict()

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get all currently active alerts"""
        return [a.to_dict() for a in self._active_alerts.values()]

    def get_trends(self) -> Dict[str, Any]:
        """Get EMA trends for all tracked resources"""
        return {k: v.to_dict() for k, v in self._trends.items()}

    def get_resource_hogs(self) -> List[Dict[str, Any]]:
        """Get current resource hogs (top consumers)"""
        hogs = sorted(
            self._resource_hogs.values(),
            key=lambda h: h.cpu_percent + (h.memory_mb / 100),
            reverse=True
        )
        return [h.to_dict() for h in hogs[:10]]

    def get_history(
        self, hours: float = 1.0
    ) -> List[Dict[str, Any]]:
        """Get health history for the last N hours"""
        cutoff = (
            datetime.now() - timedelta(hours=hours)
        ).isoformat()
        rows = self._db_execute(
            """SELECT timestamp, cpu_percent, memory_percent,
                      disk_percent, gpu_percent, health_score, severity
               FROM health_snapshots
               WHERE timestamp > ?
               ORDER BY timestamp ASC""",
            (cutoff,), fetch=True
        )
        return rows or []

    def get_context_for_brain(self) -> str:
        """
        Get concise system health context string for brain prompt injection.
        Only includes noteworthy information.
        """
        parts = []
        score = self._health_score

        if score.severity != AlertSeverity.NORMAL:
            parts.append(
                f"⚠️ System health: {score.severity.upper()} "
                f"(score: {score.overall:.0%})"
            )

        # Active alerts
        if self._active_alerts:
            alert_msgs = [a.message for a in self._active_alerts.values()]
            parts.append(f"Active alerts: {'; '.join(alert_msgs)}")

        # Trends
        rising = [
            k for k, v in self._trends.items()
            if v.direction == "rising" and v.slope > 5.0
        ]
        if rising:
            parts.append(
                f"Rising resource usage: {', '.join(rising)}"
            )

        # Runaway processes
        runaways = [
            h for h in self._resource_hogs.values() if h.is_runaway
        ]
        if runaways:
            names = [f"{h.name} (PID {h.pid})" for h in runaways[:3]]
            parts.append(
                f"Runaway processes detected: {', '.join(names)}"
            )

        # Battery
        snap = self._current_snapshot
        if (snap.battery_available and not snap.battery_plugged
                and snap.battery_percent < 20):
            parts.append(
                f"Battery low: {snap.battery_percent:.0f}% "
                f"({snap.battery_time_left_minutes:.0f} min remaining)"
            )

        return "\n".join(parts) if parts else ""

    def get_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of system health"""
        snap = self._current_snapshot
        return {
            "health_score": self._health_score.to_dict(),
            "cpu": {
                "percent": snap.cpu_percent_total,
                "cores": snap.cpu_count_logical,
                "frequency_mhz": snap.cpu_frequency_mhz,
                "trend": self._trends["cpu"].direction,
            },
            "memory": {
                "used_gb": snap.memory_used_gb,
                "total_gb": snap.memory_total_gb,
                "percent": snap.memory_percent,
                "trend": self._trends["memory"].direction,
            },
            "disk": {
                "used_gb": snap.disk_used_gb,
                "total_gb": snap.disk_total_gb,
                "percent": snap.disk_percent,
                "io_read_mb_s": snap.disk_read_mb_s,
                "io_write_mb_s": snap.disk_write_mb_s,
            },
            "network": {
                "recv_kb_s": round(snap.net_bytes_recv_per_sec / 1024, 1),
                "sent_kb_s": round(snap.net_bytes_sent_per_sec / 1024, 1),
                "connections": snap.net_connections_count,
                "trend": self._trends["network"].direction,
            },
            "gpu": {
                "available": snap.gpu_available,
                "name": snap.gpu_name,
                "utilization_percent": snap.gpu_utilization_percent,
                "memory_used_mb": snap.gpu_memory_used_mb,
                "temperature_c": snap.gpu_temperature_c,
            } if snap.gpu_available else {"available": False},
            "battery": {
                "available": snap.battery_available,
                "percent": snap.battery_percent,
                "plugged": snap.battery_plugged,
                "time_left_min": snap.battery_time_left_minutes,
            } if snap.battery_available else {"available": False},
            "active_alerts": self.get_active_alerts(),
            "resource_hogs": self.get_resource_hogs()[:5],
            "process_count": snap.process_count,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get monitor operational stats"""
        return {
            "running": self._running,
            "total_checks": self._total_checks,
            "total_alerts_fired": self._total_alerts_fired,
            "active_alert_count": len(self._active_alerts),
            "health_score": self._health_score.overall,
            "severity": self._health_score.severity,
            "resource_hog_count": len(self._resource_hogs),
            "runaway_count": sum(
                1 for h in self._resource_hogs.values() if h.is_runaway
            ),
            "trends": {
                k: v.direction for k, v in self._trends.items()
            },
            "uptime": str(
                datetime.now() - self._start_time
            ) if self._start_time else "not started",
            "history_snapshots": len(self._snapshot_history),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

health_monitor = SystemHealthMonitor()

if __name__ == "__main__":
    monitor = SystemHealthMonitor()
    monitor.start()

    print("Monitoring system health... (Ctrl+C to stop)")
    try:
        for _ in range(6):
            time.sleep(10)
            print(f"\n--- Check #{monitor._total_checks} ---")
            print(json.dumps(monitor.get_summary(), indent=2, default=str))
    except KeyboardInterrupt:
        pass

    monitor.stop()
