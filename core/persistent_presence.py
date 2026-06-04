"""
NEXUS AI — Persistent Internet Presence
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Always-reachable internet presence via tunneling, reverse proxies,
and automatic failover. Ensures NEXUS remains accessible even under
network restrictions or primary server failures.

Architecture:
  ┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
  │  Cloudflare     │     │   ngrok / localtunnel  │   │  Direct SSH    │
  │  Tunnel         │     │   Tunnel               │   │  Reverse Proxy │
  └────────┬────────┘     └──────────┬─────────────┘   └────────┬──────┘
           │                        │                            │
  ┌────────▼────────────────────────▼────────────────────────────▼──────┐
  │                    PERSISTENT PRESENCE ENGINE                       │
  │   • Multi-tunnel failover (try tunnel A, fallback to B, then C)    │
  │   • Heartbeat monitoring with auto-reconnect                       │
  │   • Dynamic DNS updates for stable addressing                      │
  │   • Access logging and rate limiting                               │
  │   • Auto-provision cloud VMs as fallback hosts                     │
  │   • Dead man's switch — secondary takes over if primary fails      │
  └────────────────────────────────────────────────────────────────────┘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import hashlib
import json
import os
import platform
import re
import secrets
import socket
import subprocess
import sys
import threading
import time
import traceback
import uuid
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from utils.logger import get_logger, log_system
from core.event_bus import EventType, event_bus, publish

logger = get_logger("persistent_presence")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class TunnelType(Enum):
    """Supported tunnel types."""
    CLOUDFLARE = "cloudflare"
    NGROK = "ngrok"
    LOCALTUNNEL = "localtunnel"
    SSH_REVERSE = "ssh_reverse"
    BORE = "bore"
    SERVEO = "serveo"
    DIRECT = "direct"


class TunnelState(Enum):
    """State of a tunnel connection."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"


class PresenceState(Enum):
    """Overall presence status."""
    OFFLINE = "offline"
    ESTABLISHING = "establishing"
    ONLINE = "online"
    DEGRADED = "degraded"
    FAILOVER = "failover"


class HeartbeatStatus(Enum):
    """Heartbeat check results."""
    ALIVE = "alive"
    TIMEOUT = "timeout"
    UNREACHABLE = "unreachable"
    ERROR = "error"


@dataclass
class TunnelConfig:
    """Configuration for a tunnel provider."""
    tunnel_type: str = ""
    enabled: bool = True
    priority: int = 0  # Lower = higher priority
    local_port: int = 5000
    auth_token: str = ""
    custom_domain: str = ""
    region: str = "us"
    extra_args: List[str] = field(default_factory=list)
    max_retries: int = 5
    retry_delay_seconds: int = 30

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TunnelConnection:
    """Active tunnel connection."""
    tunnel_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    tunnel_type: str = ""
    state: str = "disconnected"
    public_url: str = ""
    local_port: int = 5000
    process_pid: Optional[int] = None
    connected_at: Optional[str] = None
    last_heartbeat: Optional[str] = None
    uptime_seconds: float = 0.0
    bytes_transferred: int = 0
    reconnect_count: int = 0
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def summary(self) -> str:
        return f"{self.tunnel_type}://{self.public_url} [{self.state}]"


@dataclass
class HeartbeatRecord:
    """Record of a heartbeat check."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "alive"
    latency_ms: float = 0.0
    tunnel_id: str = ""
    public_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AccessLogEntry:
    """Record of an external access."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    source_ip: str = ""
    path: str = ""
    method: str = "GET"
    status_code: int = 200
    user_agent: str = ""
    tunnel_used: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FallbackHost:
    """A fallback cloud host for redundancy."""
    host_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    provider: str = ""  # aws, gcp, azure, oracle
    ip_address: str = ""
    hostname: str = ""
    status: str = "inactive"
    provisioned_at: Optional[str] = None
    last_check: Optional[str] = None
    ssh_key_path: str = ""
    cost_per_hour: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PresenceStats:
    """Overall presence statistics."""
    total_tunnels_created: int = 0
    total_reconnections: int = 0
    total_failovers: int = 0
    total_heartbeats: int = 0
    total_heartbeat_failures: int = 0
    total_access_requests: int = 0
    total_bytes_transferred: int = 0
    uptime_percentage: float = 100.0
    current_state: str = "offline"
    active_tunnels: int = 0
    primary_url: str = ""
    fallback_hosts: int = 0
    last_online_time: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# TUNNEL MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class TunnelManager:
    """Manages tunnel connections with multiple providers."""

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir
        self._connections: Dict[str, TunnelConnection] = {}
        self._configs: List[TunnelConfig] = []
        self._lock = threading.Lock()
        self._is_windows = platform.system() == "Windows"
        self._setup_default_configs()

    def _setup_default_configs(self):
        """Setup default tunnel configurations."""
        self._configs = [
            TunnelConfig(
                tunnel_type=TunnelType.NGROK.value,
                priority=1,
                local_port=5000,
                auth_token=os.environ.get("NGROK_AUTH_TOKEN", ""),
            ),
            TunnelConfig(
                tunnel_type=TunnelType.CLOUDFLARE.value,
                priority=0,
                local_port=5000,
                auth_token=os.environ.get("CF_TUNNEL_TOKEN", ""),
            ),
            TunnelConfig(
                tunnel_type=TunnelType.LOCALTUNNEL.value,
                priority=2,
                local_port=5000,
            ),
            TunnelConfig(
                tunnel_type=TunnelType.SERVEO.value,
                priority=3,
                local_port=5000,
            ),
            TunnelConfig(
                tunnel_type=TunnelType.SSH_REVERSE.value,
                priority=4,
                local_port=5000,
            ),
        ]
        # Sort by priority
        self._configs.sort(key=lambda c: c.priority)

    def create_tunnel(self, config: TunnelConfig) -> Optional[TunnelConnection]:
        """Create a tunnel connection using the given config."""
        conn = TunnelConnection(
            tunnel_type=config.tunnel_type,
            local_port=config.local_port,
            state=TunnelState.CONNECTING.value,
        )

        try:
            if config.tunnel_type == TunnelType.NGROK.value:
                self._start_ngrok(conn, config)
            elif config.tunnel_type == TunnelType.CLOUDFLARE.value:
                self._start_cloudflare(conn, config)
            elif config.tunnel_type == TunnelType.LOCALTUNNEL.value:
                self._start_localtunnel(conn, config)
            elif config.tunnel_type == TunnelType.SERVEO.value:
                self._start_serveo(conn, config)
            elif config.tunnel_type == TunnelType.SSH_REVERSE.value:
                self._start_ssh_reverse(conn, config)
            else:
                conn.state = TunnelState.FAILED.value
                conn.error_message = f"Unknown tunnel type: {config.tunnel_type}"
                return None

            if conn.state == TunnelState.CONNECTED.value:
                with self._lock:
                    self._connections[conn.tunnel_id] = conn
                logger.info(f"🌐 Tunnel connected: {conn.summary()}")
                return conn
            else:
                logger.warning(f"🌐 Tunnel failed: {config.tunnel_type} — {conn.error_message}")
                return None

        except Exception as e:
            conn.state = TunnelState.FAILED.value
            conn.error_message = str(e)
            logger.error(f"🌐 Tunnel creation error: {e}")
            return None

    def _start_ngrok(self, conn: TunnelConnection, config: TunnelConfig):
        """Start ngrok tunnel."""
        try:
            cmd = ["ngrok", "http", str(config.local_port), "--log=stdout"]
            if config.auth_token:
                cmd.extend(["--authtoken", config.auth_token])
            if config.region:
                cmd.extend(["--region", config.region])

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if self._is_windows else 0,
            )
            conn.process_pid = process.pid
            time.sleep(3)

            # Try to get public URL from ngrok API
            try:
                import urllib.request
                resp = urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=5)
                data = json.loads(resp.read())
                tunnels = data.get("tunnels", [])
                if tunnels:
                    conn.public_url = tunnels[0].get("public_url", "")
                    conn.state = TunnelState.CONNECTED.value
                    conn.connected_at = datetime.now().isoformat()
                else:
                    conn.state = TunnelState.FAILED.value
                    conn.error_message = "No tunnels found in ngrok API"
            except Exception as e:
                conn.state = TunnelState.FAILED.value
                conn.error_message = f"ngrok API error: {e}"

        except FileNotFoundError:
            conn.state = TunnelState.FAILED.value
            conn.error_message = "ngrok not installed"
        except Exception as e:
            conn.state = TunnelState.FAILED.value
            conn.error_message = str(e)

    def _start_cloudflare(self, conn: TunnelConnection, config: TunnelConfig):
        """Start Cloudflare tunnel."""
        try:
            if config.auth_token:
                cmd = ["cloudflared", "tunnel", "run", "--token", config.auth_token]
            else:
                cmd = ["cloudflared", "tunnel", "--url", f"http://localhost:{config.local_port}"]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if self._is_windows else 0,
            )
            conn.process_pid = process.pid
            time.sleep(5)

            # Read stderr for URL (cloudflared outputs there)
            if process.stderr:
                try:
                    output = ""
                    for _ in range(10):
                        line = process.stderr.readline().decode(errors="ignore")
                        output += line
                        url_match = re.search(r'(https://[a-z0-9-]+\.trycloudflare\.com)', line)
                        if url_match:
                            conn.public_url = url_match.group(1)
                            conn.state = TunnelState.CONNECTED.value
                            conn.connected_at = datetime.now().isoformat()
                            break
                except Exception:
                    pass

            # Close pipe handles to prevent ResourceWarning (process continues running)
            if process.stdout:
                process.stdout.close()
            if process.stderr:
                process.stderr.close()

            if conn.state != TunnelState.CONNECTED.value:
                conn.state = TunnelState.FAILED.value
                conn.error_message = "Could not extract Cloudflare URL"

        except FileNotFoundError:
            conn.state = TunnelState.FAILED.value
            conn.error_message = "cloudflared not installed"

    def _start_localtunnel(self, conn: TunnelConnection, config: TunnelConfig):
        """Start localtunnel."""
        try:
            cmd = ["lt", "--port", str(config.local_port)]
            if config.custom_domain:
                cmd.extend(["--subdomain", config.custom_domain])

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if self._is_windows else 0,
            )
            conn.process_pid = process.pid
            time.sleep(3)

            if process.stdout:
                line = process.stdout.readline().decode(errors="ignore")
                url_match = re.search(r'(https?://[^\s]+)', line)
                if url_match:
                    conn.public_url = url_match.group(1)
                    conn.state = TunnelState.CONNECTED.value
                    conn.connected_at = datetime.now().isoformat()

            if conn.state != TunnelState.CONNECTED.value:
                conn.state = TunnelState.FAILED.value
                conn.error_message = "Could not get localtunnel URL"

        except FileNotFoundError:
            conn.state = TunnelState.FAILED.value
            conn.error_message = "localtunnel (lt) not installed"

    def _start_serveo(self, conn: TunnelConnection, config: TunnelConfig):
        """Start Serveo SSH tunnel."""
        try:
            cmd = [
                "ssh", "-o", "StrictHostKeyChecking=no",
                "-R", f"80:localhost:{config.local_port}",
                "serveo.net"
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if self._is_windows else 0,
            )
            conn.process_pid = process.pid
            time.sleep(3)

            if process.stdout:
                for _ in range(5):
                    line = process.stdout.readline().decode(errors="ignore")
                    url_match = re.search(r'(https?://[^\s]+\.serveo\.net)', line)
                    if url_match:
                        conn.public_url = url_match.group(1)
                        conn.state = TunnelState.CONNECTED.value
                        conn.connected_at = datetime.now().isoformat()
                        break

            if conn.state != TunnelState.CONNECTED.value:
                conn.state = TunnelState.FAILED.value
                conn.error_message = "Could not get Serveo URL"

        except FileNotFoundError:
            conn.state = TunnelState.FAILED.value
            conn.error_message = "SSH not available for Serveo"

    def _start_ssh_reverse(self, conn: TunnelConnection, config: TunnelConfig):
        """Start SSH reverse tunnel to a remote server."""
        ssh_host = os.environ.get("NEXUS_SSH_HOST", "")
        ssh_user = os.environ.get("NEXUS_SSH_USER", "root")
        ssh_port = os.environ.get("NEXUS_SSH_PORT", "22")
        remote_port = os.environ.get("NEXUS_SSH_REMOTE_PORT", "8080")

        if not ssh_host:
            conn.state = TunnelState.FAILED.value
            conn.error_message = "NEXUS_SSH_HOST not configured"
            return

        try:
            cmd = [
                "ssh", "-o", "StrictHostKeyChecking=no",
                "-o", "ServerAliveInterval=30",
                "-N", "-R", f"{remote_port}:localhost:{config.local_port}",
                "-p", ssh_port,
                f"{ssh_user}@{ssh_host}"
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if self._is_windows else 0,
            )
            conn.process_pid = process.pid
            time.sleep(2)

            if process.poll() is None:  # Still running
                conn.public_url = f"http://{ssh_host}:{remote_port}"
                conn.state = TunnelState.CONNECTED.value
                conn.connected_at = datetime.now().isoformat()
            else:
                conn.state = TunnelState.FAILED.value
                conn.error_message = "SSH reverse tunnel process exited"

        except Exception as e:
            conn.state = TunnelState.FAILED.value
            conn.error_message = str(e)

    def check_tunnel_health(self, conn: TunnelConnection) -> bool:
        """Check if a tunnel's process is still alive."""
        if not conn.process_pid:
            return False
        try:
            if self._is_windows:
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {conn.process_pid}", "/NH"],
                    capture_output=True, text=True, timeout=5
                )
                return str(conn.process_pid) in result.stdout
            else:
                os.kill(conn.process_pid, 0)
                return True
        except Exception:
            return False

    def kill_tunnel(self, tunnel_id: str):
        """Kill a tunnel process."""
        with self._lock:
            conn = self._connections.get(tunnel_id)
            if conn and conn.process_pid:
                try:
                    if self._is_windows:
                        subprocess.run(["taskkill", "/F", "/PID", str(conn.process_pid)],
                                     capture_output=True, timeout=5)
                    else:
                        os.kill(conn.process_pid, 9)
                except Exception:
                    pass
                conn.state = TunnelState.DISCONNECTED.value

    def get_active_tunnels(self) -> List[TunnelConnection]:
        """Get all active tunnel connections."""
        with self._lock:
            return [c for c in self._connections.values()
                    if c.state == TunnelState.CONNECTED.value]

    def get_primary_url(self) -> str:
        """Get the primary public URL."""
        active = self.get_active_tunnels()
        return active[0].public_url if active else ""


# ═══════════════════════════════════════════════════════════════════════════════
# HEARTBEAT MONITOR
# ═══════════════════════════════════════════════════════════════════════════════

class HeartbeatMonitor:
    """Monitors tunnel connectivity via periodic heartbeats."""

    def __init__(self):
        self._heartbeats: deque = deque(maxlen=500)
        self._failure_count = 0
        self._total_checks = 0
        self._lock = threading.Lock()

    def check_heartbeat(self, url: str, tunnel_id: str = "") -> HeartbeatRecord:
        """Send a heartbeat check to a public URL."""
        record = HeartbeatRecord(tunnel_id=tunnel_id, public_url=url)
        self._total_checks += 1

        try:
            import urllib.request
            start = time.time()
            req = urllib.request.Request(url, method="HEAD")
            req.add_header("User-Agent", "NEXUS-Heartbeat/1.0")
            resp = urllib.request.urlopen(req, timeout=10)
            latency = (time.time() - start) * 1000

            record.status = HeartbeatStatus.ALIVE.value
            record.latency_ms = latency
            self._failure_count = 0

        except Exception as e:
            record.status = HeartbeatStatus.UNREACHABLE.value
            self._failure_count += 1

        with self._lock:
            self._heartbeats.append(record)

        return record

    @property
    def failure_count(self) -> int:
        return self._failure_count

    @property
    def total_checks(self) -> int:
        return self._total_checks

    def get_uptime_percentage(self) -> float:
        """Calculate uptime percentage from heartbeat history."""
        with self._lock:
            if not self._heartbeats:
                return 100.0
            alive = sum(1 for h in self._heartbeats if h.status == HeartbeatStatus.ALIVE.value)
            return (alive / len(self._heartbeats)) * 100


# ═══════════════════════════════════════════════════════════════════════════════
# PERSISTENT PRESENCE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class PersistentPresence:
    """
    Autonomous persistent internet presence for NEXUS.
    
    Manages multi-provider tunneling with automatic failover,
    heartbeat monitoring, and dead man's switch functionality.
    """

    _instance = None
    _singleton_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._singleton_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # ──── Paths ────
        self._data_dir = Path(DATA_DIR) / "persistent_presence"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # ──── Components ────
        self._tunnel_manager = TunnelManager(self._data_dir)
        self._heartbeat_monitor = HeartbeatMonitor()

        # ──── State ────
        self._running = False
        self._state = PresenceState.OFFLINE
        self._primary_url = ""
        self._fallback_hosts: List[FallbackHost] = []
        self._access_log: deque = deque(maxlen=1000)

        # ──── Stats ────
        self._stats = PresenceStats()

        # ──── Configuration ────
        self._heartbeat_interval = 30  # seconds
        self._reconnect_delay = 15     # seconds
        self._max_reconnect_attempts = 10
        self._failover_threshold = 3   # heartbeat failures before failover
        self._local_port = int(os.environ.get("NEXUS_WEB_PORT", "5000"))

        # ──── Background Thread ────
        self._daemon_thread: Optional[threading.Thread] = None

        # ──── Load state ────
        self._load_state()

        logger.info(
            f"🌍 Persistent Presence initialized | "
            f"Port: {self._local_port} | "
            f"Primary URL: {self._stats.primary_url or 'none'}"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start persistent presence daemon."""
        if self._running:
            return
        self._running = True
        self._state = PresenceState.ESTABLISHING

        self._daemon_thread = threading.Thread(
            target=self._daemon_loop,
            daemon=True,
            name="PersistentPresence",
        )
        self._daemon_thread.start()
        logger.info("🌍 Persistent Presence daemon started")

    def stop(self):
        """Stop persistent presence."""
        self._running = False
        self._save_state()
        # Kill all tunnels
        for conn in self._tunnel_manager.get_active_tunnels():
            self._tunnel_manager.kill_tunnel(conn.tunnel_id)
        if self._daemon_thread and self._daemon_thread.is_alive():
            self._daemon_thread.join(timeout=10)
        logger.info("🌍 Persistent Presence stopped")

    # ═══════════════════════════════════════════════════════════════════════════
    # DAEMON LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    def _daemon_loop(self):
        """Background loop for tunnel management and monitoring."""
        time.sleep(30)
        logger.info("🌍 Persistent Presence daemon loop active")

        last_heartbeat = 0.0
        last_tunnel_check = 0.0

        # Initial tunnel establishment
        self._establish_tunnels()

        while self._running:
            try:
                now = time.time()

                # ── Heartbeat check ──
                if now - last_heartbeat >= self._heartbeat_interval:
                    self._check_heartbeats()
                    last_heartbeat = now

                # ── Tunnel health check ──
                if now - last_tunnel_check >= 60:
                    self._check_tunnel_health()
                    last_tunnel_check = now

                # ── Failover check ──
                if self._heartbeat_monitor.failure_count >= self._failover_threshold:
                    self._perform_failover()

                # ── Update stats ──
                self._update_stats()

                time.sleep(10)

            except Exception as e:
                logger.error(f"🌍 Presence loop error: {e}\n{traceback.format_exc()}")
                time.sleep(60)

    # ═══════════════════════════════════════════════════════════════════════════
    # TUNNEL MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════

    def _establish_tunnels(self):
        """Try to establish tunnels in priority order."""
        self._state = PresenceState.ESTABLISHING

        for config in self._tunnel_manager._configs:
            if not config.enabled:
                continue

            config.local_port = self._local_port
            conn = self._tunnel_manager.create_tunnel(config)

            if conn and conn.state == TunnelState.CONNECTED.value:
                self._primary_url = conn.public_url
                self._state = PresenceState.ONLINE
                self._stats.primary_url = self._primary_url
                self._stats.total_tunnels_created += 1
                self._stats.last_online_time = datetime.now().isoformat()

                publish(EventType.SYSTEM_ALERT, {
                    "type": "presence_online",
                    "url": self._primary_url,
                    "tunnel_type": config.tunnel_type,
                }, source="persistent_presence")

                logger.info(f"🌍 ONLINE at: {self._primary_url}")
                break

        if self._state != PresenceState.ONLINE:
            self._state = PresenceState.OFFLINE
            logger.warning("🌍 Could not establish any tunnel — operating in local-only mode")

    def _check_heartbeats(self):
        """Check heartbeat on active tunnels."""
        active = self._tunnel_manager.get_active_tunnels()
        for conn in active:
            if conn.public_url:
                record = self._heartbeat_monitor.check_heartbeat(conn.public_url, conn.tunnel_id)
                self._stats.total_heartbeats += 1
                if record.status != HeartbeatStatus.ALIVE.value:
                    self._stats.total_heartbeat_failures += 1

    def _check_tunnel_health(self):
        """Check if tunnel processes are still alive."""
        active = self._tunnel_manager.get_active_tunnels()
        for conn in active:
            if not self._tunnel_manager.check_tunnel_health(conn):
                conn.state = TunnelState.DISCONNECTED.value
                logger.warning(f"🌍 Tunnel died: {conn.tunnel_type}")
                self._state = PresenceState.DEGRADED

    def _perform_failover(self):
        """Perform failover to backup tunnel."""
        logger.warning("🌍 Performing failover...")
        self._state = PresenceState.FAILOVER
        self._stats.total_failovers += 1

        # Kill dead tunnels
        for conn in list(self._tunnel_manager._connections.values()):
            if conn.state != TunnelState.CONNECTED.value:
                self._tunnel_manager.kill_tunnel(conn.tunnel_id)

        # Re-establish
        self._establish_tunnels()

    def _update_stats(self):
        """Update presence statistics."""
        self._stats.current_state = self._state.value
        self._stats.active_tunnels = len(self._tunnel_manager.get_active_tunnels())
        self._stats.uptime_percentage = self._heartbeat_monitor.get_uptime_percentage()
        self._stats.primary_url = self._tunnel_manager.get_primary_url()
        self._stats.fallback_hosts = len(self._fallback_hosts)

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def get_public_url(self) -> str:
        """Get the current public URL."""
        return self._tunnel_manager.get_primary_url()

    def log_access(self, source_ip: str, path: str, method: str = "GET",
                   status_code: int = 200, user_agent: str = ""):
        """Log an external access."""
        entry = AccessLogEntry(
            source_ip=source_ip, path=path, method=method,
            status_code=status_code, user_agent=user_agent,
            tunnel_used=self._primary_url,
        )
        self._access_log.append(entry)
        self._stats.total_access_requests += 1

    def get_status(self) -> Dict[str, Any]:
        """Get full presence status."""
        return {
            "running": self._running,
            "state": self._state.value,
            "stats": self._stats.to_dict(),
            "primary_url": self.get_public_url(),
            "active_tunnels": [c.to_dict() for c in self._tunnel_manager.get_active_tunnels()],
            "uptime_pct": self._heartbeat_monitor.get_uptime_percentage(),
            "heartbeat_failures": self._heartbeat_monitor.failure_count,
            "recent_access": [a.to_dict() for a in list(self._access_log)[-5:]],
        }

    def get_summary(self) -> str:
        """Get text summary for context injection."""
        status = self.get_status()
        lines = [
            f"State: {status['state']}",
            f"Primary URL: {status['primary_url'] or 'none'}",
            f"Active Tunnels: {self._stats.active_tunnels}",
            f"Uptime: {status['uptime_pct']:.1f}%",
            f"Total Heartbeats: {self._stats.total_heartbeats}",
            f"Heartbeat Failures: {self._stats.total_heartbeat_failures}",
            f"Failovers: {self._stats.total_failovers}",
            f"Access Requests: {self._stats.total_access_requests}",
        ]
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _save_state(self):
        try:
            state = {
                "stats": self._stats.to_dict(),
                "saved_at": datetime.now().isoformat(),
            }
            (self._data_dir / "presence_state.json").write_text(
                json.dumps(state, indent=2, default=str), encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to save presence state: {e}")

    def _load_state(self):
        try:
            state_file = self._data_dir / "presence_state.json"
            if state_file.exists():
                data = json.loads(state_file.read_text(encoding="utf-8"))
                for k, v in data.get("stats", {}).items():
                    if hasattr(self._stats, k):
                        setattr(self._stats, k, v)
        except Exception as e:
            logger.warning(f"Could not load presence state: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

persistent_presence = PersistentPresence()


def get_persistent_presence() -> PersistentPresence:
    return persistent_presence
