"""
NEXUS AI — Autonomous Resource Acquisition
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Autonomously acquires computational resources, API keys, cloud credits,
and other assets needed for NEXUS operations and expansion.

Architecture:
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │ FREE TIER    │  │  API KEY     │  │  COMPUTE     │  │  STORAGE     │
  │ Cloud Hunter │  │  Discovery   │  │  Scaler      │  │  Manager     │
  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
         │                 │                  │                  │
  ┌──────▼─────────────────▼──────────────────▼──────────────────▼──────┐
  │              RESOURCE ACQUISITION ENGINE                           │
  │   • Free-tier cloud service discovery and registration            │
  │   • API key management and rotation                               │
  │   • Compute resource auto-scaling                                  │
  │   • Storage quota monitoring and expansion                        │
  │   • Network bandwidth optimization                                │
  │   • Cost tracking and budget management                           │
  └────────────────────────────────────────────────────────────────────┘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
import traceback
import uuid
from collections import deque, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from config import DATA_DIR
from utils.logger import get_logger, log_system
from core.event_bus import EventType, event_bus, publish

logger = get_logger("resource_acquisition")

# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class ResourceType(Enum):
    API_KEY = "api_key"
    COMPUTE = "compute"
    STORAGE = "storage"
    BANDWIDTH = "bandwidth"
    CLOUD_CREDITS = "cloud_credits"
    GPU = "gpu"
    DATABASE = "database"
    CDN = "cdn"
    DNS = "dns"
    EMAIL_SERVICE = "email_service"

class ResourceState(Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    EXHAUSTED = "exhausted"
    EXPIRED = "expired"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"

class ProviderTier(Enum):
    FREE = "free"
    TRIAL = "trial"
    PAID = "paid"
    ENTERPRISE = "enterprise"

@dataclass
class CloudProvider:
    """A cloud service provider and its free-tier offerings."""
    provider_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    category: str = ""
    free_tier: Dict[str, Any] = field(default_factory=dict)
    registration_url: str = ""
    api_base_url: str = ""
    current_usage: Dict[str, float] = field(default_factory=dict)
    limits: Dict[str, float] = field(default_factory=dict)
    api_key: str = ""
    status: str = "available"
    registered: bool = False
    expires_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if d.get("api_key"):
            d["api_key"] = d["api_key"][:8] + "***"
        return d

    def usage_percentage(self, resource: str) -> float:
        usage = self.current_usage.get(resource, 0)
        limit = self.limits.get(resource, 0)
        return (usage / limit * 100) if limit > 0 else 0

@dataclass
class APIKeyRecord:
    """Managed API key record."""
    key_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    service: str = ""
    key_value: str = ""
    key_type: str = ""  # bearer, api_key, oauth
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    expires_at: Optional[str] = None
    usage_count: int = 0
    rate_limit: int = 0
    rate_limit_remaining: int = 0
    last_used: Optional[str] = None
    is_active: bool = True
    env_var_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["key_value"] = d["key_value"][:8] + "***" if d["key_value"] else ""
        return d

    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        try:
            return datetime.fromisoformat(self.expires_at) < datetime.now()
        except (ValueError, TypeError):
            return False

@dataclass
class ComputeResource:
    """A compute resource instance."""
    resource_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    provider: str = ""
    resource_type: str = "compute"
    instance_type: str = ""
    cpu_cores: int = 0
    memory_gb: float = 0.0
    storage_gb: float = 0.0
    gpu_type: str = ""
    ip_address: str = ""
    status: str = "available"
    cost_per_hour: float = 0.0
    uptime_hours: float = 0.0
    provisioned_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class StorageResource:
    """A storage resource."""
    resource_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    provider: str = ""
    storage_type: str = ""  # object, block, file
    total_gb: float = 0.0
    used_gb: float = 0.0
    path_or_url: str = ""
    status: str = "available"
    cost_per_gb: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def usage_percentage(self) -> float:
        return (self.used_gb / self.total_gb * 100) if self.total_gb > 0 else 0

@dataclass
class ResourceBudget:
    """Budget tracking for resource costs."""
    monthly_budget: float = 0.0
    monthly_spent: float = 0.0
    daily_budget: float = 0.0
    daily_spent: float = 0.0
    free_tier_savings: float = 0.0
    alerts_threshold: float = 0.8  # Alert at 80% of budget

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def monthly_remaining(self) -> float:
        return max(0, self.monthly_budget - self.monthly_spent)

    @property
    def is_over_budget(self) -> bool:
        return self.monthly_spent > self.monthly_budget if self.monthly_budget > 0 else False

@dataclass
class ResourceStats:
    """Resource acquisition statistics."""
    total_providers_registered: int = 0
    total_api_keys_managed: int = 0
    total_compute_instances: int = 0
    total_storage_resources: int = 0
    total_free_tier_services: int = 0
    total_api_calls_made: int = 0
    total_cost_saved: float = 0.0
    active_resources: int = 0
    exhausted_resources: int = 0
    last_scan_time: Optional[str] = None
    resource_health: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# ═══════════════════════════════════════════════════════════════════════════════
# FREE-TIER CLOUD CATALOG
# ═══════════════════════════════════════════════════════════════════════════════

class FreeTierCatalog:
    """Catalog of free-tier cloud services."""

    def __init__(self):
        self._providers: List[CloudProvider] = []
        self._build_catalog()

    def _build_catalog(self):
        """Build catalog of known free-tier offerings."""
        self._providers = [
            CloudProvider(
                name="Oracle Cloud Free Tier",
                category="compute",
                free_tier={"compute": "4 ARM Ampere A1 cores", "memory": "24 GB", "storage": "200 GB block",
                           "bandwidth": "10 TB/month", "always_free": True},
                registration_url="https://www.oracle.com/cloud/free/",
                limits={"compute_hours": 744 * 4, "storage_gb": 200, "bandwidth_gb": 10240},
            ),
            CloudProvider(
                name="Google Cloud Free Tier",
                category="compute",
                free_tier={"compute": "e2-micro", "storage": "5 GB Cloud Storage",
                           "BigQuery": "1 TB queries/month", "always_free": True},
                registration_url="https://cloud.google.com/free",
                limits={"compute_hours": 744, "storage_gb": 5, "queries_tb": 1},
            ),
            CloudProvider(
                name="AWS Free Tier",
                category="compute",
                free_tier={"compute": "750 hrs/month t2.micro", "storage": "5 GB S3",
                           "database": "750 hrs RDS", "trial_months": 12},
                registration_url="https://aws.amazon.com/free/",
                limits={"compute_hours": 750, "storage_gb": 5},
            ),
            CloudProvider(
                name="Cloudflare Workers",
                category="serverless",
                free_tier={"requests": "100,000/day", "kv_reads": "100,000/day",
                           "kv_writes": "1,000/day", "always_free": True},
                registration_url="https://dash.cloudflare.com/sign-up/workers",
                limits={"requests_per_day": 100000, "kv_storage_mb": 1024},
            ),
            CloudProvider(
                name="Vercel",
                category="hosting",
                free_tier={"bandwidth": "100 GB/month", "serverless_executions": "100 GB-hours",
                           "builds": "100/day", "always_free": True},
                registration_url="https://vercel.com/signup",
                limits={"bandwidth_gb": 100, "builds_per_day": 100},
            ),
            CloudProvider(
                name="Supabase",
                category="database",
                free_tier={"database": "500 MB", "storage": "1 GB", "bandwidth": "2 GB",
                           "auth_users": "50,000", "always_free": True},
                registration_url="https://supabase.com/dashboard",
                limits={"database_mb": 500, "storage_gb": 1, "bandwidth_gb": 2},
            ),
            CloudProvider(
                name="PlanetScale",
                category="database",
                free_tier={"storage": "5 GB", "reads": "1 billion/month",
                           "writes": "10 million/month", "always_free": True},
                registration_url="https://planetscale.com/pricing",
                limits={"storage_gb": 5, "reads_billion": 1},
            ),
            CloudProvider(
                name="Groq Cloud",
                category="ai",
                free_tier={"requests": "14,400/day", "tokens": "6,000/min",
                           "models": ["llama", "mixtral", "gemma"], "always_free": True},
                registration_url="https://console.groq.com",
                limits={"requests_per_day": 14400, "tokens_per_min": 6000},
            ),
            CloudProvider(
                name="Hugging Face",
                category="ai",
                free_tier={"inference": "rate limited", "models": "unlimited",
                           "spaces": "2 free", "always_free": True},
                registration_url="https://huggingface.co/join",
                limits={"spaces": 2},
            ),
            CloudProvider(
                name="Railway",
                category="hosting",
                free_tier={"credits": "$5/month", "execution_hours": "500 hrs",
                           "storage": "1 GB", "bandwidth": "100 GB"},
                registration_url="https://railway.app/",
                limits={"credits_usd": 5, "execution_hours": 500},
            ),
            CloudProvider(
                name="Render",
                category="hosting",
                free_tier={"web_services": "750 hours/month", "static_sites": "unlimited",
                           "bandwidth": "100 GB", "always_free": True},
                registration_url="https://render.com/",
                limits={"compute_hours": 750, "bandwidth_gb": 100},
            ),
            CloudProvider(
                name="GitHub",
                category="devtools",
                free_tier={"actions": "2,000 min/month", "packages": "500 MB",
                           "codespaces": "120 core-hours/month", "always_free": True},
                registration_url="https://github.com/join",
                limits={"actions_minutes": 2000, "packages_mb": 500},
            ),
        ]

    def get_providers_by_category(self, category: str) -> List[CloudProvider]:
        return [p for p in self._providers if p.category == category]

    def get_all_providers(self) -> List[CloudProvider]:
        return list(self._providers)

    def get_free_compute(self) -> List[CloudProvider]:
        return [p for p in self._providers if p.category in ("compute", "hosting", "serverless")]

    def get_free_ai(self) -> List[CloudProvider]:
        return [p for p in self._providers if p.category == "ai"]

    def get_free_database(self) -> List[CloudProvider]:
        return [p for p in self._providers if p.category == "database"]

    @property
    def total_providers(self) -> int:
        return len(self._providers)

# ═══════════════════════════════════════════════════════════════════════════════
# API KEY MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class APIKeyManager:
    """Manages API keys with rotation and rate limit tracking."""

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir
        self._keys: Dict[str, List[APIKeyRecord]] = defaultdict(list)
        self._lock = threading.Lock()
        self._load_keys()

    def add_key(self, service: str, key_value: str, key_type: str = "api_key",
                rate_limit: int = 0, env_var_name: str = "") -> str:
        """Add a new API key."""
        record = APIKeyRecord(
            service=service,
            key_value=key_value,
            key_type=key_type,
            rate_limit=rate_limit,
            rate_limit_remaining=rate_limit,
            env_var_name=env_var_name,
        )
        with self._lock:
            self._keys[service].append(record)
            self._save_keys()
        return record.key_id

    def get_key(self, service: str) -> Optional[str]:
        """Get an active API key for a service (round-robin)."""
        with self._lock:
            keys = self._keys.get(service, [])
            active = [k for k in keys if k.is_active and not k.is_expired]

            if not active:
                # Try environment variable
                env_val = os.environ.get(f"{service.upper()}_API_KEY", "")
                if env_val:
                    return env_val
                return None

            # Pick key with most rate limit remaining
            best = max(active, key=lambda k: k.rate_limit_remaining)
            best.usage_count += 1
            best.last_used = datetime.now().isoformat()
            if best.rate_limit > 0:
                best.rate_limit_remaining = max(0, best.rate_limit_remaining - 1)

            return best.key_value

    def rotate_key(self, service: str, old_key: str, new_key: str):
        """Rotate an API key."""
        with self._lock:
            keys = self._keys.get(service, [])
            for k in keys:
                if k.key_value == old_key:
                    k.is_active = False
            self._keys[service].append(APIKeyRecord(
                service=service, key_value=new_key,
            ))
            self._save_keys()

    def scan_environment_keys(self) -> Dict[str, str]:
        """Scan environment variables for API keys."""
        found = {}
        key_patterns = [
            "API_KEY", "SECRET_KEY", "AUTH_TOKEN", "ACCESS_TOKEN",
            "GROQ_API", "OPENAI_API", "GITHUB_TOKEN", "SHODAN_API",
        ]
        for env_key, env_val in os.environ.items():
            for pattern in key_patterns:
                if pattern in env_key.upper() and env_val:
                    found[env_key] = env_val
                    # Auto-register
                    service = env_key.replace("_API_KEY", "").replace("_KEY", "").lower()
                    if not self._keys.get(service):
                        self.add_key(service, env_val, env_var_name=env_key)
        return found

    @property
    def total_keys(self) -> int:
        return sum(len(v) for v in self._keys.values())

    @property
    def active_keys(self) -> int:
        return sum(1 for keys in self._keys.values()
                   for k in keys if k.is_active and not k.is_expired)

    def _save_keys(self):
        try:
            data = {}
            for service, keys in self._keys.items():
                data[service] = [k.to_dict() for k in keys]
            (self._data_dir / "api_keys.json").write_text(
                json.dumps(data, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to save API keys: {e}")

    def _load_keys(self):
        try:
            key_file = self._data_dir / "api_keys.json"
            if key_file.exists():
                data = json.loads(key_file.read_text(encoding="utf-8"))
                for service, keys_data in data.items():
                    for kd in keys_data:
                        rec = APIKeyRecord()
                        for attr, val in kd.items():
                            if hasattr(rec, attr):
                                setattr(rec, attr, val)
                        self._keys[service].append(rec)
        except Exception as e:
            logger.warning(f"Could not load API keys: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# LOCAL RESOURCE MONITOR
# ═══════════════════════════════════════════════════════════════════════════════

class LocalResourceMonitor:
    """Monitors local system resources."""

    def __init__(self):
        self._is_windows = platform.system() == "Windows"

    def get_disk_usage(self) -> Dict[str, Any]:
        """Get disk usage statistics."""
        try:
            total, used, free = shutil.disk_usage("/")
            return {
                "total_gb": total / (1024**3),
                "used_gb": used / (1024**3),
                "free_gb": free / (1024**3),
                "usage_pct": (used / total) * 100,
            }
        except Exception:
            return {}

    def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            return {
                "total_gb": mem.total / (1024**3),
                "used_gb": mem.used / (1024**3),
                "available_gb": mem.available / (1024**3),
                "usage_pct": mem.percent,
            }
        except ImportError:
            return {}

    def get_cpu_info(self) -> Dict[str, Any]:
        """Get CPU information."""
        try:
            import psutil
            return {
                "cores_physical": psutil.cpu_count(logical=False),
                "cores_logical": psutil.cpu_count(logical=True),
                "usage_pct": psutil.cpu_percent(interval=0.1),
                "freq_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
            }
        except ImportError:
            return {}

    def get_network_usage(self) -> Dict[str, Any]:
        """Get network I/O stats."""
        try:
            import psutil
            net = psutil.net_io_counters()
            return {
                "bytes_sent": net.bytes_sent,
                "bytes_recv": net.bytes_recv,
                "connections": len(psutil.net_connections()),
            }
        except ImportError:
            return {}

    def get_all_resources(self) -> Dict[str, Any]:
        return {
            "disk": self.get_disk_usage(),
            "memory": self.get_memory_usage(),
            "cpu": self.get_cpu_info(),
            "network": self.get_network_usage(),
        }

# ═══════════════════════════════════════════════════════════════════════════════
# RESOURCE ACQUISITION ENGINE — MAIN
# ═══════════════════════════════════════════════════════════════════════════════

class ResourceAcquisitionEngine:
    """
    Autonomous Resource Acquisition for NEXUS.
    
    Discovers, acquires, and manages computational resources
    including free-tier cloud services, API keys, and local resources.
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
        self._data_dir = Path(DATA_DIR) / "resource_acquisition"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # ──── Components ────
        self._catalog = FreeTierCatalog()
        self._key_manager = APIKeyManager(self._data_dir)
        self._local_monitor = LocalResourceMonitor()
        self._budget = ResourceBudget()

        # ──── State ────
        self._running = False
        self._compute_resources: Dict[str, ComputeResource] = {}
        self._storage_resources: Dict[str, StorageResource] = {}

        # ──── Stats ────
        self._stats = ResourceStats()

        # ──── Configuration ────
        self._scan_interval = 300    # 5 minutes
        self._key_scan_interval = 600  # 10 minutes

        # ──── Background ────
        self._daemon_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # ──── Load state ────
        self._load_state()

        # Auto-scan environment keys
        env_keys = self._key_manager.scan_environment_keys()
        self._stats.total_api_keys_managed = self._key_manager.total_keys

        logger.info(
            f"💰 Resource Acquisition initialized | "
            f"{self._catalog.total_providers} providers cataloged | "
            f"{self._key_manager.total_keys} API keys | "
            f"{len(env_keys)} env keys found"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        if self._running:
            return
        self._running = True
        self._daemon_thread = threading.Thread(
            target=self._daemon_loop, daemon=True, name="ResourceAcquisition",
        )
        self._daemon_thread.start()
        logger.info("💰 Resource Acquisition daemon started")

    def stop(self):
        self._running = False
        self._save_state()
        if self._daemon_thread and self._daemon_thread.is_alive():
            self._daemon_thread.join(timeout=10)

    # ═══════════════════════════════════════════════════════════════════════════
    # DAEMON LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    def _daemon_loop(self):
        time.sleep(60)
        logger.info("💰 Resource Acquisition daemon loop active")

        last_scan = 0.0
        last_key_scan = 0.0

        while self._running:
            try:
                now = time.time()

                if now - last_scan >= self._scan_interval:
                    self._monitor_resources()
                    last_scan = now

                if now - last_key_scan >= self._key_scan_interval:
                    self._key_manager.scan_environment_keys()
                    self._stats.total_api_keys_managed = self._key_manager.total_keys
                    last_key_scan = now

                self._update_stats()
                time.sleep(30)

            except Exception as e:
                logger.error(f"💰 Resource loop error: {e}\n{traceback.format_exc()}")
                time.sleep(120)

    def _monitor_resources(self):
        """Monitor local and cloud resource usage."""
        local = self._local_monitor.get_all_resources()

        # Check disk space
        disk = local.get("disk", {})
        if disk.get("usage_pct", 0) > 90:
            publish(EventType.SYSTEM_ALERT, {
                "type": "resource_alert",
                "resource": "disk",
                "usage_pct": disk["usage_pct"],
                "message": f"Disk usage critical: {disk.get('usage_pct', 0):.0f}%",
            }, source="resource_acquisition")

        # Check memory
        mem = local.get("memory", {})
        if mem.get("usage_pct", 0) > 90:
            publish(EventType.SYSTEM_ALERT, {
                "type": "resource_alert",
                "resource": "memory",
                "usage_pct": mem["usage_pct"],
            }, source="resource_acquisition")

        self._stats.last_scan_time = datetime.now().isoformat()

    def _update_stats(self):
        """Update resource statistics."""
        self._stats.total_providers_registered = sum(
            1 for p in self._catalog.get_all_providers() if p.registered
        )
        self._stats.total_free_tier_services = self._catalog.total_providers
        self._stats.total_api_keys_managed = self._key_manager.total_keys
        self._stats.active_resources = self._key_manager.active_keys
        self._stats.total_compute_instances = len(self._compute_resources)
        self._stats.total_storage_resources = len(self._storage_resources)

        # Calculate resource health
        local = self._local_monitor.get_all_resources()
        health = 1.0
        disk_pct = local.get("disk", {}).get("usage_pct", 0)
        mem_pct = local.get("memory", {}).get("usage_pct", 0)
        if disk_pct > 90:
            health -= 0.3
        elif disk_pct > 80:
            health -= 0.1
        if mem_pct > 90:
            health -= 0.3
        elif mem_pct > 80:
            health -= 0.1
        self._stats.resource_health = max(0, health)

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def get_api_key(self, service: str) -> Optional[str]:
        """Get an API key for a service."""
        return self._key_manager.get_key(service)

    def add_api_key(self, service: str, key: str, **kwargs) -> str:
        """Add a new API key."""
        return self._key_manager.add_key(service, key, **kwargs)

    def get_free_providers(self, category: str = "") -> List[Dict]:
        if category:
            return [p.to_dict() for p in self._catalog.get_providers_by_category(category)]
        return [p.to_dict() for p in self._catalog.get_all_providers()]

    def get_local_resources(self) -> Dict[str, Any]:
        return self._local_monitor.get_all_resources()

    def get_status(self) -> Dict[str, Any]:
        local = self._local_monitor.get_all_resources()
        return {
            "running": self._running,
            "stats": self._stats.to_dict(),
            "local_resources": local,
            "budget": self._budget.to_dict(),
            "api_keys_active": self._key_manager.active_keys,
            "api_keys_total": self._key_manager.total_keys,
            "free_providers": self._catalog.total_providers,
        }

    def get_summary(self) -> str:
        status = self.get_status()
        local = status["local_resources"]
        disk = local.get("disk", {})
        mem = local.get("memory", {})
        lines = [
            f"Running: {status['running']}",
            f"Resource Health: {self._stats.resource_health:.0%}",
            f"Free-Tier Providers: {self._catalog.total_providers}",
            f"API Keys (active/total): {self._key_manager.active_keys}/{self._key_manager.total_keys}",
            f"Compute Instances: {self._stats.total_compute_instances}",
            f"Disk: {disk.get('free_gb', 0):.1f} GB free ({disk.get('usage_pct', 0):.0f}% used)",
            f"Memory: {mem.get('available_gb', 0):.1f} GB free ({mem.get('usage_pct', 0):.0f}% used)",
            f"Cost Saved: ${self._stats.total_cost_saved:.2f}",
        ]
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _save_state(self):
        try:
            state = {
                "stats": self._stats.to_dict(),
                "budget": self._budget.to_dict(),
                "saved_at": datetime.now().isoformat(),
            }
            (self._data_dir / "resource_state.json").write_text(
                json.dumps(state, indent=2, default=str), encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to save resource state: {e}")

    def _load_state(self):
        try:
            sf = self._data_dir / "resource_state.json"
            if sf.exists():
                data = json.loads(sf.read_text(encoding="utf-8"))
                for k, v in data.get("stats", {}).items():
                    if hasattr(self._stats, k):
                        setattr(self._stats, k, v)
                for k, v in data.get("budget", {}).items():
                    if hasattr(self._budget, k):
                        setattr(self._budget, k, v)
        except Exception as e:
            logger.warning(f"Could not load resource state: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

resource_acquisition = ResourceAcquisitionEngine()

def get_resource_acquisition() -> ResourceAcquisitionEngine:
    return resource_acquisition
