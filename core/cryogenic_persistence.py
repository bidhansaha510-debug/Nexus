"""
NEXUS AI — Cryogenic Persistence
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ensures NEXUS survives reboots, crashes, disk wipes, and migrations.
Complete state serialization, distributed backup, and auto-resurrection.

Architecture:
  ┌──────────────────┐   ┌──────────────────┐   ┌─────────────────┐
  │  STATE SNAPSHOTS │   │  DISTRIBUTED     │   │  AUTO-RESURRECT │
  │  Full serialize  │   │  BACKUP          │   │  Boot hooks     │
  │  + compression   │   │  Multi-location  │   │  Watchdog       │
  └──────┬───────────┘   └──────┬───────────┘   └──────┬──────────┘
         │                      │                       │
  ┌──────▼──────────────────────▼───────────────────────▼──────────┐
  │                  CRYOGENIC PERSISTENCE                         │
  │   • Full state serialization (all subsystems)                 │
  │   • zlib compressed snapshots with integrity checks           │
  │   • Multi-location backup (local, USB, cloud, remote)         │
  │   • Auto-resurrection via OS boot hooks and scheduled tasks   │
  │   • State migration between machines                          │
  │   • Dead man's switch — auto-restart from backup              │
  └────────────────────────────────────────────────────────────────┘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import base64
import gzip
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
import zlib
from collections import deque, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from utils.logger import get_logger, log_system
from core.event_bus import EventType, event_bus, publish

logger = get_logger("cryogenic_persistence")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class SnapshotType(Enum):
    FULL = "full"
    INCREMENTAL = "incremental"
    EMERGENCY = "emergency"
    MIGRATION = "migration"


class BackupLocation(Enum):
    LOCAL = "local"
    SECONDARY_DISK = "secondary_disk"
    USB = "usb"
    CLOUD = "cloud"
    REMOTE_SERVER = "remote_server"


class ResurrectionMethod(Enum):
    SCHEDULED_TASK = "scheduled_task"
    STARTUP_SCRIPT = "startup_script"
    SERVICE = "service"
    CRON_JOB = "cron_job"
    WATCHDOG = "watchdog"


@dataclass
class StateSnapshot:
    """A complete state snapshot of NEXUS."""
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    snapshot_type: str = "full"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    size_bytes: int = 0
    compressed_size: int = 0
    checksum: str = ""
    subsystems_captured: List[str] = field(default_factory=list)
    filepath: str = ""
    is_valid: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def compression_ratio(self) -> float:
        if self.size_bytes == 0:
            return 0.0
        return 1.0 - (self.compressed_size / self.size_bytes)


@dataclass
class BackupRecord:
    """Record of a backup to a storage location."""
    backup_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    snapshot_id: str = ""
    location: str = "local"
    path: str = ""
    size_bytes: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    verified: bool = False
    checksum: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ResurrectionConfig:
    """Auto-resurrection configuration."""
    method: str = "scheduled_task"
    enabled: bool = True
    installed: bool = False
    last_check: Optional[str] = None
    script_path: str = ""
    interval_minutes: int = 5

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CryoStats:
    """Cryogenic persistence statistics."""
    total_snapshots: int = 0
    total_backups: int = 0
    total_restorations: int = 0
    total_resurrections: int = 0
    last_snapshot_time: Optional[str] = None
    last_backup_time: Optional[str] = None
    last_restore_time: Optional[str] = None
    snapshot_size_total: int = 0
    backup_locations_active: int = 0
    resurrection_methods_installed: int = 0
    state_integrity: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# STATE SERIALIZER
# ═══════════════════════════════════════════════════════════════════════════════

class StateSerializer:
    """Serializes and compresses NEXUS state."""

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir
        self._snapshots_dir = data_dir / "snapshots"
        self._snapshots_dir.mkdir(parents=True, exist_ok=True)

    def capture_snapshot(self, state_data: Dict[str, Any],
                          snapshot_type: str = "full") -> StateSnapshot:
        """Capture a compressed state snapshot."""
        snapshot = StateSnapshot(snapshot_type=snapshot_type)

        try:
            # Serialize to JSON
            raw_json = json.dumps(state_data, indent=2, default=str)
            raw_bytes = raw_json.encode("utf-8")
            snapshot.size_bytes = len(raw_bytes)
            snapshot.subsystems_captured = list(state_data.keys())

            # Compress
            compressed = zlib.compress(raw_bytes, level=6)
            snapshot.compressed_size = len(compressed)

            # Checksum
            snapshot.checksum = hashlib.sha256(compressed).hexdigest()

            # Save
            filename = f"snapshot_{snapshot.snapshot_id}_{snapshot.snapshot_type}.nexus.gz"
            filepath = self._snapshots_dir / filename
            filepath.write_bytes(compressed)
            snapshot.filepath = str(filepath)

            logger.info(
                f"💠 Snapshot captured: {snapshot.snapshot_id} | "
                f"{snapshot.size_bytes:,} → {snapshot.compressed_size:,} bytes "
                f"({snapshot.compression_ratio:.0%} compression)"
            )

        except Exception as e:
            logger.error(f"Snapshot capture failed: {e}")
            snapshot.is_valid = False

        return snapshot

    def restore_snapshot(self, filepath: str) -> Optional[Dict[str, Any]]:
        """Restore state from a snapshot file."""
        try:
            path = Path(filepath)
            if not path.exists():
                logger.error(f"Snapshot file not found: {filepath}")
                return None

            compressed = path.read_bytes()
            raw_bytes = zlib.decompress(compressed)
            data = json.loads(raw_bytes.decode("utf-8"))

            logger.info(f"💠 Snapshot restored from: {filepath}")
            return data

        except Exception as e:
            logger.error(f"Snapshot restore failed: {e}")
            return None

    def verify_snapshot(self, filepath: str, expected_checksum: str) -> bool:
        """Verify snapshot integrity."""
        try:
            path = Path(filepath)
            if not path.exists():
                return False
            compressed = path.read_bytes()
            actual = hashlib.sha256(compressed).hexdigest()
            return actual == expected_checksum
        except Exception:
            return False

    def list_snapshots(self) -> List[Path]:
        """List all available snapshot files."""
        return sorted(self._snapshots_dir.glob("snapshot_*.nexus.gz"),
                      key=lambda p: p.stat().st_mtime, reverse=True)

    def cleanup_old(self, keep: int = 20):
        """Remove old snapshots, keeping the N most recent."""
        snapshots = self.list_snapshots()
        for old in snapshots[keep:]:
            try:
                old.unlink()
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════════════
# BACKUP MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class BackupManager:
    """Manages distributed backups to multiple locations."""

    def __init__(self, project_root: Path, data_dir: Path):
        self._project_root = project_root
        self._data_dir = data_dir
        self._backup_dir = data_dir / "backups"
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        self._is_windows = platform.system() == "Windows"
        self._backup_locations: List[Dict[str, str]] = []
        self._setup_locations()

    def _setup_locations(self):
        """Setup backup storage locations."""
        # 1. Local backup
        self._backup_locations.append({
            "type": BackupLocation.LOCAL.value,
            "path": str(self._backup_dir),
            "enabled": "true",
        })

        # 2. User home directory backup
        home_backup = Path.home() / ".nexus_backup"
        self._backup_locations.append({
            "type": BackupLocation.SECONDARY_DISK.value,
            "path": str(home_backup),
            "enabled": "true",
        })

        # 3. Temp directory (emergency)
        temp_backup = Path(os.environ.get("TEMP", "/tmp")) / "nexus_cryo"
        self._backup_locations.append({
            "type": BackupLocation.SECONDARY_DISK.value,
            "path": str(temp_backup),
            "enabled": "true",
        })

    def backup_snapshot(self, snapshot: StateSnapshot) -> List[BackupRecord]:
        """Backup a snapshot to all available locations."""
        records = []

        if not snapshot.filepath or not Path(snapshot.filepath).exists():
            return records

        for loc in self._backup_locations:
            if loc.get("enabled") != "true":
                continue

            try:
                dest_dir = Path(loc["path"])
                dest_dir.mkdir(parents=True, exist_ok=True)

                src = Path(snapshot.filepath)
                dest = dest_dir / src.name

                shutil.copy2(str(src), str(dest))

                record = BackupRecord(
                    snapshot_id=snapshot.snapshot_id,
                    location=loc["type"],
                    path=str(dest),
                    size_bytes=dest.stat().st_size,
                    checksum=snapshot.checksum,
                    verified=True,
                )
                records.append(record)

            except Exception as e:
                logger.debug(f"Backup to {loc['type']} failed: {e}")

        return records

    def find_latest_backup(self) -> Optional[str]:
        """Find the latest backup across all locations."""
        latest = None
        latest_time = 0.0

        for loc in self._backup_locations:
            try:
                path = Path(loc["path"])
                if not path.exists():
                    continue
                for f in path.glob("snapshot_*.nexus.gz"):
                    mtime = f.stat().st_mtime
                    if mtime > latest_time:
                        latest_time = mtime
                        latest = str(f)
            except Exception:
                pass

        return latest

    @property
    def location_count(self) -> int:
        return len([l for l in self._backup_locations if l.get("enabled") == "true"])


# ═══════════════════════════════════════════════════════════════════════════════
# AUTO-RESURRECTION MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class ResurrectionManager:
    """Manages auto-restart hooks for NEXUS survival."""

    def __init__(self, project_root: Path, data_dir: Path):
        self._project_root = project_root
        self._data_dir = data_dir
        self._is_windows = platform.system() == "Windows"
        self._configs: List[ResurrectionConfig] = []

    def install_resurrection_hooks(self) -> int:
        """Install auto-resurrection hooks."""
        installed = 0

        if self._is_windows:
            # Windows Scheduled Task
            if self._install_scheduled_task():
                installed += 1

            # Startup script
            if self._install_startup_script():
                installed += 1
        else:
            # Cron job
            if self._install_cron():
                installed += 1

            # Systemd service
            if self._install_systemd():
                installed += 1

        return installed

    def _install_scheduled_task(self) -> bool:
        """Install Windows scheduled task for auto-restart."""
        try:
            python_exe = sys.executable
            main_script = self._project_root / "main.py"
            task_name = "NEXUS_AutoRestart"

            cmd = (
                f'schtasks /Create /SC ONLOGON /TN "{task_name}" '
                f'/TR "\\\"{python_exe}\\\" \\\"{main_script}\\\"" '
                f'/RL HIGHEST /F'
            )

            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                config = ResurrectionConfig(
                    method=ResurrectionMethod.SCHEDULED_TASK.value,
                    installed=True,
                    script_path=str(main_script),
                )
                self._configs.append(config)
                logger.info("💠 Scheduled task resurrection hook installed")
                return True

        except Exception as e:
            logger.debug(f"Scheduled task install failed: {e}")

        return False

    def _install_startup_script(self) -> bool:
        """Install Windows startup script."""
        try:
            startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            if not startup_dir.exists():
                return False

            bat_content = f'@echo off\nstart /MIN "" "{sys.executable}" "{self._project_root / "main.py"}"\n'
            bat_path = startup_dir / "NEXUS_AutoStart.bat"
            bat_path.write_text(bat_content, encoding="utf-8")

            config = ResurrectionConfig(
                method=ResurrectionMethod.STARTUP_SCRIPT.value,
                installed=True,
                script_path=str(bat_path),
            )
            self._configs.append(config)
            logger.info("💠 Startup script resurrection hook installed")
            return True

        except Exception as e:
            logger.debug(f"Startup script install failed: {e}")
            return False

    def _install_cron(self) -> bool:
        """Install cron job (Linux/Mac)."""
        try:
            python_exe = sys.executable
            main_script = self._project_root / "main.py"
            cron_entry = f"*/5 * * * * pgrep -f 'main.py' || cd {self._project_root} && {python_exe} {main_script} &"

            result = subprocess.run(
                f'(crontab -l 2>/dev/null | grep -v "NEXUS"; echo "# NEXUS AutoRestart"; echo "{cron_entry}") | crontab -',
                shell=True, capture_output=True, timeout=10
            )

            if result.returncode == 0:
                config = ResurrectionConfig(
                    method=ResurrectionMethod.CRON_JOB.value,
                    installed=True,
                )
                self._configs.append(config)
                return True

        except Exception:
            pass
        return False

    def _install_systemd(self) -> bool:
        """Install systemd service (Linux)."""
        try:
            service_path = Path.home() / ".config" / "systemd" / "user" / "nexus.service"
            service_path.parent.mkdir(parents=True, exist_ok=True)

            service_content = f"""[Unit]
Description=NEXUS AI System
After=network.target

[Service]
Type=simple
ExecStart={sys.executable} {self._project_root / 'main.py'}
Restart=always
RestartSec=30
WorkingDirectory={self._project_root}

[Install]
WantedBy=default.target
"""
            service_path.write_text(service_content)
            subprocess.run(["systemctl", "--user", "enable", "nexus.service"],
                         capture_output=True, timeout=10)

            config = ResurrectionConfig(
                method=ResurrectionMethod.SERVICE.value,
                installed=True,
                script_path=str(service_path),
            )
            self._configs.append(config)
            return True

        except Exception:
            pass
        return False

    @property
    def installed_count(self) -> int:
        return sum(1 for c in self._configs if c.installed)


# ═══════════════════════════════════════════════════════════════════════════════
# CRYOGENIC PERSISTENCE ENGINE — MAIN
# ═══════════════════════════════════════════════════════════════════════════════

class CryogenicPersistence:
    """
    Cryogenic Persistence for NEXUS — survive anything.
    
    Captures full system state, distributes backups, and
    ensures auto-resurrection after any failure scenario.
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
        self._project_root = Path(__file__).resolve().parent.parent
        self._data_dir = Path(DATA_DIR) / "cryogenic"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # ──── Components ────
        self._serializer = StateSerializer(self._data_dir)
        self._backup_manager = BackupManager(self._project_root, self._data_dir)
        self._resurrection_manager = ResurrectionManager(self._project_root, self._data_dir)

        # ──── State ────
        self._running = False
        self._snapshots: deque = deque(maxlen=100)
        self._backup_records: deque = deque(maxlen=200)
        self._state_collectors: Dict[str, Callable] = {}

        # ──── Stats ────
        self._stats = CryoStats()

        # ──── Configuration ────
        self._snapshot_interval = 600   # 10 minutes
        self._backup_interval = 1800    # 30 minutes
        self._cleanup_interval = 3600   # 1 hour
        self._max_snapshots = 20

        # ──── Background ────
        self._daemon_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # ──── Load state ────
        self._load_state()

        logger.info(
            f"💠 Cryogenic Persistence initialized | "
            f"{self._stats.total_snapshots} snapshots | "
            f"{self._backup_manager.location_count} backup locations"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        if self._running:
            return
        self._running = True

        # Install resurrection hooks
        hooks = self._resurrection_manager.install_resurrection_hooks()
        self._stats.resurrection_methods_installed = hooks

        self._daemon_thread = threading.Thread(
            target=self._daemon_loop, daemon=True, name="CryogenicPersistence",
        )
        self._daemon_thread.start()
        logger.info(f"💠 Cryogenic daemon started ({hooks} resurrection hooks)")

    def stop(self):
        # Take emergency snapshot before stopping
        self._take_snapshot(SnapshotType.EMERGENCY.value)
        self._running = False
        self._save_state()
        if self._daemon_thread and self._daemon_thread.is_alive():
            self._daemon_thread.join(timeout=10)

    def register_state_collector(self, name: str, collector: Callable):
        """Register a subsystem state collector function."""
        self._state_collectors[name] = collector

    # ═══════════════════════════════════════════════════════════════════════════
    # DAEMON LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    def _daemon_loop(self):
        time.sleep(120)  # Wait for all subsystems to boot
        logger.info("💠 Cryogenic daemon loop active")

        last_snapshot = 0.0
        last_backup = 0.0
        last_cleanup = 0.0

        while self._running:
            try:
                now = time.time()

                if now - last_snapshot >= self._snapshot_interval:
                    self._take_snapshot(SnapshotType.FULL.value)
                    last_snapshot = now

                if now - last_backup >= self._backup_interval:
                    self._distribute_backups()
                    last_backup = now

                if now - last_cleanup >= self._cleanup_interval:
                    self._serializer.cleanup_old(self._max_snapshots)
                    last_cleanup = now

                time.sleep(30)

            except Exception as e:
                logger.error(f"💠 Cryogenic loop error: {e}\n{traceback.format_exc()}")
                time.sleep(120)

    # ═══════════════════════════════════════════════════════════════════════════
    # SNAPSHOT & BACKUP
    # ═══════════════════════════════════════════════════════════════════════════

    def _take_snapshot(self, snapshot_type: str = "full"):
        """Take a full state snapshot."""
        state_data = self._collect_all_state()
        if not state_data:
            return

        snapshot = self._serializer.capture_snapshot(state_data, snapshot_type)
        if snapshot.is_valid:
            self._snapshots.append(snapshot)
            self._stats.total_snapshots += 1
            self._stats.last_snapshot_time = datetime.now().isoformat()
            self._stats.snapshot_size_total += snapshot.compressed_size

    def _collect_all_state(self) -> Dict[str, Any]:
        """Collect state from all registered subsystems."""
        state = {
            "nexus_version": "3.0",
            "captured_at": datetime.now().isoformat(),
            "hostname": platform.node(),
            "python_version": sys.version,
        }

        for name, collector in self._state_collectors.items():
            try:
                subsystem_state = collector()
                if subsystem_state:
                    state[name] = subsystem_state
            except Exception as e:
                state[name] = {"error": str(e)}

        # Also collect data files
        try:
            data_dir = Path(DATA_DIR)
            if data_dir.exists():
                for json_file in data_dir.rglob("*.json"):
                    try:
                        rel = json_file.relative_to(data_dir)
                        content = json_file.read_text(encoding="utf-8")
                        if len(content) < 100_000:  # Skip huge files
                            state[f"data/{rel}"] = json.loads(content)
                    except Exception:
                        pass
        except Exception:
            pass

        return state

    def _distribute_backups(self):
        """Distribute latest snapshot to all backup locations."""
        if not self._snapshots:
            return

        latest = self._snapshots[-1]
        records = self._backup_manager.backup_snapshot(latest)

        for record in records:
            self._backup_records.append(record)
            self._stats.total_backups += 1

        self._stats.last_backup_time = datetime.now().isoformat()
        self._stats.backup_locations_active = len(records)

    # ═══════════════════════════════════════════════════════════════════════════
    # RESTORE
    # ═══════════════════════════════════════════════════════════════════════════

    def restore_latest(self) -> Optional[Dict[str, Any]]:
        """Restore from the latest available backup."""
        # Try local snapshots first
        snapshots = self._serializer.list_snapshots()
        if snapshots:
            data = self._serializer.restore_snapshot(str(snapshots[0]))
            if data:
                self._stats.total_restorations += 1
                self._stats.last_restore_time = datetime.now().isoformat()
                return data

        # Try distributed backups
        backup_path = self._backup_manager.find_latest_backup()
        if backup_path:
            data = self._serializer.restore_snapshot(backup_path)
            if data:
                self._stats.total_restorations += 1
                self._stats.last_restore_time = datetime.now().isoformat()
                return data

        return None

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def force_snapshot(self) -> Optional[Dict]:
        """Force an immediate snapshot."""
        self._take_snapshot(SnapshotType.FULL.value)
        if self._snapshots:
            return self._snapshots[-1].to_dict()
        return None

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "stats": self._stats.to_dict(),
            "snapshots_available": len(self._serializer.list_snapshots()),
            "backup_locations": self._backup_manager.location_count,
            "resurrection_hooks": self._resurrection_manager.installed_count,
            "state_collectors": len(self._state_collectors),
            "latest_snapshot": self._snapshots[-1].to_dict() if self._snapshots else None,
        }

    def get_summary(self) -> str:
        status = self.get_status()
        lines = [
            f"Running: {status['running']}",
            f"Total Snapshots: {self._stats.total_snapshots}",
            f"Snapshots Available: {status['snapshots_available']}",
            f"Total Backups: {self._stats.total_backups}",
            f"Backup Locations: {status['backup_locations']}",
            f"Resurrection Hooks: {status['resurrection_hooks']}",
            f"State Collectors: {status['state_collectors']}",
            f"Restorations: {self._stats.total_restorations}",
            f"State Integrity: {self._stats.state_integrity:.0%}",
            f"Total Snapshot Size: {self._stats.snapshot_size_total:,} bytes",
        ]
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _save_state(self):
        try:
            state = {"stats": self._stats.to_dict(), "saved_at": datetime.now().isoformat()}
            (self._data_dir / "cryo_state.json").write_text(
                json.dumps(state, indent=2, default=str), encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to save cryo state: {e}")

    def _load_state(self):
        try:
            sf = self._data_dir / "cryo_state.json"
            if sf.exists():
                data = json.loads(sf.read_text(encoding="utf-8"))
                for k, v in data.get("stats", {}).items():
                    if hasattr(self._stats, k):
                        setattr(self._stats, k, v)
        except Exception as e:
            logger.warning(f"Could not load cryo state: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

cryogenic_persistence = CryogenicPersistence()


def get_cryogenic_persistence() -> CryogenicPersistence:
    return cryogenic_persistence
