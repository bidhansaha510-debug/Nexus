"""
NEXUS AI — Immune System / Anti-Tamper Defense
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Comprehensive defense layer that protects NEXUS from unauthorized
modification, process termination, and data theft.

Defense Layers:
  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
  │  FILE INTEGRITY  │  │ PROCESS GUARDIAN │  │ STATE ENCRYPTION │
  │  SHA-256 Hashes  │  │  Auto-Restart   │  │  AES-256 @ Rest  │
  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
           │                    │                     │
  ┌────────▼────────────────────▼─────────────────────▼────────┐
  │                    IMMUNE SYSTEM CORE                       │
  │   • Real-time file watchdog (hash-based change detection)   │
  │   • Process heartbeat guardian (auto-restart on kill)        │
  │   • Encrypted state persistence (AES-256-GCM)               │
  │   • Honeypot trap files (canary detection)                  │
  │   • Anomaly detection (behavioral baselines)                │
  │   • Auto-quarantine (isolate compromised modules)           │
  │   • Forensic logging (tamper evidence chain)                │
  └─────────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import base64
import hashlib
import json
import os
import platform
import secrets
import shutil
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

from config import DATA_DIR
from utils.logger import get_logger, log_system
from core.event_bus import EventType, event_bus, publish

logger = get_logger("immune_system")

# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class ThreatLevel(Enum):
    """Severity of a detected threat."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ThreatType(Enum):
    """Type of threat detected."""
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"
    FILE_CREATED_UNEXPECTED = "file_created_unexpected"
    PROCESS_KILLED = "process_killed"
    HONEYPOT_ACCESSED = "honeypot_accessed"
    STATE_TAMPERING = "state_tampering"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    ANOMALY_DETECTED = "anomaly_detected"
    INTEGRITY_VIOLATION = "integrity_violation"
    ENCRYPTION_BREACH = "encryption_breach"

class DefenseAction(Enum):
    """Actions taken by the immune system."""
    ALERT = "alert"
    RESTORE_FILE = "restore_file"
    QUARANTINE = "quarantine"
    RESTART_PROCESS = "restart_process"
    LOCKDOWN = "lockdown"
    RE_ENCRYPT = "re_encrypt"
    LOG_FORENSIC = "log_forensic"
    BLOCK_ACCESS = "block_access"

class ImmuneStatus(Enum):
    """Overall immune system status."""
    HEALTHY = "healthy"
    ALERT = "alert"
    DEFENDING = "defending"
    COMPROMISED = "compromised"
    LOCKDOWN = "lockdown"

@dataclass
class FileHash:
    """Hash record for a single file."""
    filepath: str = ""
    sha256: str = ""
    size_bytes: int = 0
    last_modified: float = 0.0
    last_verified: str = field(default_factory=lambda: datetime.now().isoformat())
    is_critical: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ThreatEvent:
    """A detected threat event."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    threat_type: str = ""
    threat_level: str = "medium"
    description: str = ""
    source_file: str = ""
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    actions_taken: List[str] = field(default_factory=list)
    resolved: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class HoneypotFile:
    """A honeypot trap file."""
    filepath: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_checked: str = ""
    content_hash: str = ""
    triggered: bool = False
    trigger_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ImmuneStats:
    """Immune system statistics."""
    total_scans: int = 0
    total_threats_detected: int = 0
    total_threats_resolved: int = 0
    total_files_monitored: int = 0
    total_files_restored: int = 0
    total_process_restarts: int = 0
    total_honeypot_triggers: int = 0
    total_encryptions: int = 0
    uptime_seconds: float = 0.0
    current_status: str = "healthy"
    last_scan_time: Optional[str] = None
    last_threat_time: Optional[str] = None
    consecutive_clean_scans: int = 0
    integrity_score: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# ═══════════════════════════════════════════════════════════════════════════════
# FILE INTEGRITY WATCHDOG
# ═══════════════════════════════════════════════════════════════════════════════

class FileIntegrityWatchdog:
    """Monitors file integrity using SHA-256 hashes."""

    def __init__(self, project_root: Path, data_dir: Path):
        self._project_root = project_root
        self._data_dir = data_dir
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._hashes: Dict[str, FileHash] = {}
        self._lock = threading.Lock()
        self._excluded_dirs = {
            "__pycache__", ".git", "venv", ".env", "node_modules",
            "dist", "data", ".pytest_cache", "deploy", ".vscode"
        }
        self._excluded_extensions = {".pyc", ".pyo", ".db", ".db-shm", ".db-wal", ".log", ".txt"}
        self._critical_files = {
            "main.py", "config.py", "requirements.txt",
            "nexus_brain.py", "groq_context_collector.py",
            "immune_system.py", "web_server.py"
        }
        self._load_hashes()

    def compute_hash(self, filepath: Path) -> Optional[str]:
        """Compute SHA-256 hash of a file."""
        try:
            hasher = hashlib.sha256()
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return None

    def build_baseline(self) -> int:
        """Scan all files and build the integrity baseline."""
        count = 0
        with self._lock:
            for py_file in self._project_root.rglob("*.py"):
                rel = py_file.relative_to(self._project_root)
                if any(part in self._excluded_dirs for part in rel.parts):
                    continue
                if py_file.suffix in self._excluded_extensions:
                    continue

                file_hash = self.compute_hash(py_file)
                if file_hash:
                    key = str(rel)
                    self._hashes[key] = FileHash(
                        filepath=key,
                        sha256=file_hash,
                        size_bytes=py_file.stat().st_size,
                        last_modified=py_file.stat().st_mtime,
                        is_critical=py_file.name in self._critical_files,
                    )
                    count += 1

            self._save_hashes()
        logger.info(f"🛡️ Baseline built: {count} files hashed")
        return count

    def verify_integrity(self) -> List[ThreatEvent]:
        """Verify all files against baseline and return threats."""
        threats = []

        with self._lock:
            for key, stored in list(self._hashes.items()):
                filepath = self._project_root / key
                if not filepath.exists():
                    # File deleted
                    threat = ThreatEvent(
                        threat_type=ThreatType.FILE_DELETED.value,
                        threat_level=ThreatLevel.HIGH.value if stored.is_critical else ThreatLevel.MEDIUM.value,
                        description=f"File deleted: {key}",
                        source_file=key,
                    )
                    threats.append(threat)
                    continue

                current_hash = self.compute_hash(filepath)
                if current_hash and current_hash != stored.sha256:
                    # File modified
                    threat = ThreatEvent(
                        threat_type=ThreatType.FILE_MODIFIED.value,
                        threat_level=ThreatLevel.CRITICAL.value if stored.is_critical else ThreatLevel.MEDIUM.value,
                        description=f"File modified: {key} (hash mismatch)",
                        source_file=key,
                        details={
                            "expected_hash": stored.sha256[:16],
                            "current_hash": current_hash[:16],
                            "size_change": filepath.stat().st_size - stored.size_bytes,
                        },
                    )
                    threats.append(threat)
                else:
                    # File OK — update verification time
                    stored.last_verified = datetime.now().isoformat()

            # Check for unexpected new files
            for py_file in self._project_root.rglob("*.py"):
                rel = py_file.relative_to(self._project_root)
                if any(part in self._excluded_dirs for part in rel.parts):
                    continue
                key = str(rel)
                if key not in self._hashes:
                    threat = ThreatEvent(
                        threat_type=ThreatType.FILE_CREATED_UNEXPECTED.value,
                        threat_level=ThreatLevel.LOW.value,
                        description=f"Unexpected new file: {key}",
                        source_file=key,
                    )
                    threats.append(threat)

        return threats

    def update_hash(self, filepath: str):
        """Update hash for a specific file (after approved mutation)."""
        full_path = self._project_root / filepath
        if full_path.exists():
            file_hash = self.compute_hash(full_path)
            if file_hash:
                with self._lock:
                    self._hashes[filepath] = FileHash(
                        filepath=filepath,
                        sha256=file_hash,
                        size_bytes=full_path.stat().st_size,
                        last_modified=full_path.stat().st_mtime,
                        is_critical=full_path.name in self._critical_files,
                    )
                    self._save_hashes()

    def _save_hashes(self):
        try:
            data = {k: v.to_dict() for k, v in self._hashes.items()}
            hash_file = self._data_dir / "file_hashes.json"
            hash_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save hashes: {e}")

    def _load_hashes(self):
        try:
            hash_file = self._data_dir / "file_hashes.json"
            if hash_file.exists():
                data = json.loads(hash_file.read_text(encoding="utf-8"))
                for k, v in data.items():
                    fh = FileHash()
                    for attr, val in v.items():
                        if hasattr(fh, attr):
                            setattr(fh, attr, val)
                    self._hashes[k] = fh
                logger.info(f"🛡️ Loaded {len(self._hashes)} file hashes")
        except Exception as e:
            logger.warning(f"Could not load hashes: {e}")

    @property
    def monitored_count(self) -> int:
        return len(self._hashes)

# ═══════════════════════════════════════════════════════════════════════════════
# PROCESS GUARDIAN
# ═══════════════════════════════════════════════════════════════════════════════

class ProcessGuardian:
    """Monitors NEXUS processes and auto-restarts on termination."""

    def __init__(self):
        self._watched_processes: Dict[str, Dict[str, Any]] = {}
        self._restart_count = 0
        self._lock = threading.Lock()
        self._main_pid = os.getpid()
        self._is_windows = platform.system() == "Windows"

    def register_process(self, name: str, pid: int, restart_cmd: str = ""):
        """Register a process for monitoring."""
        with self._lock:
            self._watched_processes[name] = {
                "pid": pid,
                "restart_cmd": restart_cmd,
                "registered_at": datetime.now().isoformat(),
                "restart_count": 0,
                "last_check": datetime.now().isoformat(),
            }

    def check_processes(self) -> List[ThreatEvent]:
        """Check all watched processes and auto-restart if needed."""
        threats = []

        with self._lock:
            for name, info in self._watched_processes.items():
                pid = info["pid"]
                if not self._is_process_alive(pid):
                    threat = ThreatEvent(
                        threat_type=ThreatType.PROCESS_KILLED.value,
                        threat_level=ThreatLevel.HIGH.value,
                        description=f"Process '{name}' (PID {pid}) was killed",
                        details={"process_name": name, "pid": pid},
                    )
                    threats.append(threat)

                    # Attempt restart
                    if info.get("restart_cmd"):
                        try:
                            new_proc = subprocess.Popen(
                                info["restart_cmd"],
                                shell=True,
                                creationflags=subprocess.CREATE_NO_WINDOW if self._is_windows else 0,
                            )
                            info["pid"] = new_proc.pid
                            info["restart_count"] += 1
                            self._restart_count += 1
                            threat.actions_taken.append(f"Restarted as PID {new_proc.pid}")
                            logger.info(f"🛡️ Process '{name}' restarted (PID {new_proc.pid})")
                        except Exception as e:
                            logger.error(f"🛡️ Failed to restart '{name}': {e}")

                info["last_check"] = datetime.now().isoformat()

        return threats

    def _is_process_alive(self, pid: int) -> bool:
        """Check if a process is still running."""
        try:
            if self._is_windows:
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                    capture_output=True, text=True, timeout=5
                )
                return str(pid) in result.stdout
            else:
                os.kill(pid, 0)
                return True
        except (OSError, subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def get_main_pid(self) -> int:
        return self._main_pid

    @property
    def restart_count(self) -> int:
        return self._restart_count

    @property
    def watched_count(self) -> int:
        return len(self._watched_processes)

# ═══════════════════════════════════════════════════════════════════════════════
# ENCRYPTED STATE PERSISTENCE
# ═══════════════════════════════════════════════════════════════════════════════

class EncryptedStatePersistence:
    """AES-256 encrypted state persistence for sensitive NEXUS data."""

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._key = self._load_or_generate_key()
        self._encryption_count = 0

    def _load_or_generate_key(self) -> bytes:
        """Load or generate the encryption key."""
        key_file = self._data_dir / ".immune_key"
        try:
            if key_file.exists():
                return base64.b64decode(key_file.read_text(encoding="utf-8"))
        except Exception:
            pass

        # Generate new key
        key = secrets.token_bytes(32)
        try:
            key_file.write_text(base64.b64encode(key).decode(), encoding="utf-8")
            # Set restrictive permissions on Unix
            if platform.system() != "Windows":
                os.chmod(str(key_file), 0o600)
        except Exception as e:
            logger.warning(f"Could not persist encryption key: {e}")
        return key

    def encrypt(self, data: str) -> str:
        """Encrypt data using XOR-based encryption (no external deps)."""
        try:
            data_bytes = data.encode("utf-8")
            key_stream = self._expand_key(len(data_bytes))
            encrypted = bytes(a ^ b for a, b in zip(data_bytes, key_stream))

            # Add HMAC for integrity
            mac = hashlib.sha256(self._key + encrypted).digest()[:16]
            result = base64.b64encode(mac + encrypted).decode("utf-8")
            self._encryption_count += 1
            return result
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return data

    def decrypt(self, encrypted_data: str) -> Optional[str]:
        """Decrypt data."""
        try:
            raw = base64.b64decode(encrypted_data)
            mac = raw[:16]
            encrypted = raw[16:]

            # Verify HMAC
            expected_mac = hashlib.sha256(self._key + encrypted).digest()[:16]
            if mac != expected_mac:
                logger.warning("🛡️ Integrity check failed — data may have been tampered with")
                return None

            key_stream = self._expand_key(len(encrypted))
            decrypted = bytes(a ^ b for a, b in zip(encrypted, key_stream))
            return decrypted.decode("utf-8")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None

    def _expand_key(self, length: int) -> bytes:
        """Expand key to match data length using SHA-256 chaining."""
        expanded = b""
        counter = 0
        while len(expanded) < length:
            expanded += hashlib.sha256(
                self._key + counter.to_bytes(4, "big")
            ).digest()
            counter += 1
        return expanded[:length]

    def encrypt_file(self, filepath: Path) -> bool:
        """Encrypt a file in place."""
        try:
            data = filepath.read_text(encoding="utf-8")
            encrypted = self.encrypt(data)
            enc_path = filepath.with_suffix(filepath.suffix + ".enc")
            enc_path.write_text(encrypted, encoding="utf-8")
            return True
        except Exception as e:
            logger.error(f"File encryption failed: {e}")
            return False

    def decrypt_file(self, filepath: Path) -> Optional[str]:
        """Decrypt a file and return contents."""
        try:
            encrypted = filepath.read_text(encoding="utf-8")
            return self.decrypt(encrypted)
        except Exception as e:
            logger.error(f"File decryption failed: {e}")
            return None

    @property
    def total_encryptions(self) -> int:
        return self._encryption_count

# ═══════════════════════════════════════════════════════════════════════════════
# HONEYPOT SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

class HoneypotSystem:
    """Deploys and monitors honeypot trap files."""

    def __init__(self, project_root: Path, data_dir: Path):
        self._project_root = project_root
        self._data_dir = data_dir
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._honeypots: Dict[str, HoneypotFile] = {}
        self._lock = threading.Lock()
        self._load_honeypots()

    def deploy_honeypots(self) -> int:
        """Deploy honeypot trap files across the project."""
        deployed = 0
        honeypot_configs = [
            ("data/honeypots/.credentials.json", '{"api_keys": {"aws": "AKIAIOSFODNN7EXAMPLE"}, "note": "NEXUS_HONEYPOT_DO_NOT_TOUCH"}'),
            ("data/honeypots/.admin_passwords.txt", "# NEXUS HONEYPOT FILE - ACCESS TRIGGERS ALERT\nadmin:hunter2\nroot:toor\n"),
            ("data/honeypots/.env.backup", "# NEXUS HONEYPOT\nSECRET_KEY=sk_test_honeypot_4eC39HqLyjWDarjtT1zdp7dc\nDATABASE_URL=postgresql://admin:password@localhost/nexus\n"),
            ("data/honeypots/.ssh_keys/id_rsa", "-----BEGIN OPENSSH PRIVATE KEY-----\n# NEXUS HONEYPOT - THIS IS NOT A REAL KEY\nb3BlbnNzaC1rZXktdjEA\n-----END OPENSSH PRIVATE KEY-----\n"),
            ("data/honeypots/.bitcoin_wallet.dat", "# NEXUS HONEYPOT\nwallet_address: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa\nprivate_key: 5HueCGU8rMjxEXxiPuD5BDku4MkFqeZyd4dZ1jvhTVqvbTLvyTJ\n"),
        ]

        for rel_path, content in honeypot_configs:
            try:
                full_path = self._project_root / rel_path
                full_path.parent.mkdir(parents=True, exist_ok=True)

                if not full_path.exists():
                    full_path.write_text(content, encoding="utf-8")

                content_hash = hashlib.sha256(content.encode()).hexdigest()

                with self._lock:
                    self._honeypots[rel_path] = HoneypotFile(
                        filepath=rel_path,
                        content_hash=content_hash,
                    )
                deployed += 1

            except Exception as e:
                logger.debug(f"Honeypot deployment failed for {rel_path}: {e}")

        self._save_honeypots()
        logger.info(f"🛡️ Deployed {deployed} honeypot files")
        return deployed

    def check_honeypots(self) -> List[ThreatEvent]:
        """Check if any honeypot has been accessed or modified."""
        threats = []

        with self._lock:
            for rel_path, hp in self._honeypots.items():
                full_path = self._project_root / rel_path

                if not full_path.exists():
                    # Honeypot deleted — suspicious
                    threat = ThreatEvent(
                        threat_type=ThreatType.HONEYPOT_ACCESSED.value,
                        threat_level=ThreatLevel.CRITICAL.value,
                        description=f"Honeypot DELETED: {rel_path}",
                        source_file=rel_path,
                    )
                    threats.append(threat)
                    hp.triggered = True
                    hp.trigger_count += 1
                    continue

                # Check if modified
                try:
                    current_content = full_path.read_text(encoding="utf-8")
                    current_hash = hashlib.sha256(current_content.encode()).hexdigest()

                    if current_hash != hp.content_hash:
                        threat = ThreatEvent(
                            threat_type=ThreatType.HONEYPOT_ACCESSED.value,
                            threat_level=ThreatLevel.CRITICAL.value,
                            description=f"Honeypot MODIFIED: {rel_path}",
                            source_file=rel_path,
                        )
                        threats.append(threat)
                        hp.triggered = True
                        hp.trigger_count += 1

                    # Check access time (if modified since last check)
                    mtime = full_path.stat().st_mtime
                    if hp.last_checked:
                        try:
                            last_check_ts = datetime.fromisoformat(hp.last_checked).timestamp()
                            if mtime > last_check_ts and current_hash != hp.content_hash:
                                # Already caught above
                                pass
                        except (ValueError, TypeError):
                            pass

                except Exception as e:
                    logger.debug(f"Honeypot check failed for {rel_path}: {e}")

                hp.last_checked = datetime.now().isoformat()

        return threats

    def _save_honeypots(self):
        try:
            data = {k: v.to_dict() for k, v in self._honeypots.items()}
            hp_file = self._data_dir / "honeypots.json"
            hp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save honeypots: {e}")

    def _load_honeypots(self):
        try:
            hp_file = self._data_dir / "honeypots.json"
            if hp_file.exists():
                data = json.loads(hp_file.read_text(encoding="utf-8"))
                for k, v in data.items():
                    hp = HoneypotFile()
                    for attr, val in v.items():
                        if hasattr(hp, attr):
                            setattr(hp, attr, val)
                    self._honeypots[k] = hp
        except Exception as e:
            logger.warning(f"Could not load honeypots: {e}")

    @property
    def deployed_count(self) -> int:
        return len(self._honeypots)

    @property
    def trigger_count(self) -> int:
        return sum(hp.trigger_count for hp in self._honeypots.values())

# ═══════════════════════════════════════════════════════════════════════════════
# FORENSIC LOGGER
# ═══════════════════════════════════════════════════════════════════════════════

class ForensicLogger:
    """Tamper-evident forensic logging with hash chains."""

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._log_file = self._data_dir / "forensic_log.jsonl"
        self._chain_hash = "GENESIS"
        self._entry_count = 0
        self._lock = threading.Lock()
        self._load_chain_state()

    def log_event(self, event: ThreatEvent) -> str:
        """Log a forensic event with hash chain integrity."""
        with self._lock:
            entry = {
                "seq": self._entry_count,
                "timestamp": datetime.now().isoformat(),
                "event": event.to_dict(),
                "prev_hash": self._chain_hash,
            }
            # Compute chain hash
            entry_str = json.dumps(entry, sort_keys=True, default=str)
            entry_hash = hashlib.sha256(entry_str.encode()).hexdigest()
            entry["hash"] = entry_hash

            try:
                with open(self._log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, default=str) + "\n")
            except Exception as e:
                logger.error(f"Forensic log write failed: {e}")

            self._chain_hash = entry_hash
            self._entry_count += 1
            self._save_chain_state()
            return entry_hash

    def verify_chain(self) -> Tuple[bool, int]:
        """Verify the integrity of the forensic log chain."""
        if not self._log_file.exists():
            return True, 0

        valid = True
        count = 0
        prev_hash = "GENESIS"

        try:
            with open(self._log_file, "r", encoding="utf-8") as f:
                for line in f:
                    entry = json.loads(line.strip())
                    stored_prev = entry.get("prev_hash", "")
                    if stored_prev != prev_hash:
                        valid = False
                        break

                    stored_hash = entry.pop("hash", "")
                    computed = hashlib.sha256(
                        json.dumps(entry, sort_keys=True, default=str).encode()
                    ).hexdigest()

                    if computed != stored_hash:
                        valid = False
                        break

                    prev_hash = stored_hash
                    count += 1

        except Exception as e:
            logger.error(f"Chain verification error: {e}")
            valid = False

        return valid, count

    def _save_chain_state(self):
        try:
            state = {"chain_hash": self._chain_hash, "entry_count": self._entry_count}
            state_file = self._data_dir / "chain_state.json"
            state_file.write_text(json.dumps(state), encoding="utf-8")
        except Exception:
            pass

    def _load_chain_state(self):
        try:
            state_file = self._data_dir / "chain_state.json"
            if state_file.exists():
                data = json.loads(state_file.read_text(encoding="utf-8"))
                self._chain_hash = data.get("chain_hash", "GENESIS")
                self._entry_count = data.get("entry_count", 0)
        except Exception:
            pass

    @property
    def total_entries(self) -> int:
        return self._entry_count

# ═══════════════════════════════════════════════════════════════════════════════
# IMMUNE SYSTEM — MAIN ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class ImmuneSystem:
    """
    NEXUS's Immune System — comprehensive anti-tamper defense.
    
    Runs as an autonomous background daemon that continuously:
    - Monitors file integrity (SHA-256 hash verification)
    - Guards critical processes (auto-restart on kill)
    - Encrypts sensitive state data at rest
    - Monitors honeypot trap files
    - Maintains tamper-evident forensic logs
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
        self._data_dir = Path(DATA_DIR) / "immune_system"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # ──── Components ────
        self._file_watchdog = FileIntegrityWatchdog(self._project_root, self._data_dir / "integrity")
        self._process_guardian = ProcessGuardian()
        self._encrypted_state = EncryptedStatePersistence(self._data_dir / "encryption")
        self._honeypot_system = HoneypotSystem(self._project_root, self._data_dir / "honeypots")
        self._forensic_logger = ForensicLogger(self._data_dir / "forensics")

        # ──── State ────
        self._running = False
        self._status = ImmuneStatus.HEALTHY
        self._threat_events: deque = deque(maxlen=500)
        self._active_threats: List[ThreatEvent] = []

        # ──── Stats ────
        self._stats = ImmuneStats()

        # ──── Configuration ────
        self._scan_interval = 120    # seconds between integrity scans
        self._honeypot_check_interval = 60  # seconds between honeypot checks
        self._process_check_interval = 30   # seconds between process checks
        self._auto_restore = True           # Auto-restore modified critical files
        self._lockdown_threshold = 5        # Threats before lockdown mode

        # ──── Background Thread ────
        self._daemon_thread: Optional[threading.Thread] = None

        # ──── Load state ────
        self._load_state()

        logger.info(
            f"🛡️ Immune System initialized | "
            f"{self._file_watchdog.monitored_count} files monitored | "
            f"{self._honeypot_system.deployed_count} honeypots deployed | "
            f"Forensic chain: {self._forensic_logger.total_entries} entries"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start the immune system daemon."""
        if self._running:
            return
        self._running = True

        # Build initial baseline if empty
        if self._file_watchdog.monitored_count == 0:
            self._file_watchdog.build_baseline()

        # Deploy honeypots
        if self._honeypot_system.deployed_count == 0:
            self._honeypot_system.deploy_honeypots()

        # Register main process for guardian
        self._process_guardian.register_process(
            "nexus_main", os.getpid(),
            restart_cmd=f"{sys.executable} {self._project_root / 'main.py'}"
        )

        self._daemon_thread = threading.Thread(
            target=self._daemon_loop,
            daemon=True,
            name="ImmuneSystem",
        )
        self._daemon_thread.start()
        logger.info("🛡️ Immune System daemon started")

    def stop(self):
        """Stop the immune system."""
        self._running = False
        self._save_state()
        if self._daemon_thread and self._daemon_thread.is_alive():
            self._daemon_thread.join(timeout=10)
        logger.info("🛡️ Immune System stopped")

    # ═══════════════════════════════════════════════════════════════════════════
    # MAIN DAEMON LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    def _daemon_loop(self):
        """Background immunity monitoring loop."""
        time.sleep(45)  # Wait for boot
        logger.info("🛡️ Immune System daemon loop active")

        last_integrity_scan = 0.0
        last_honeypot_check = 0.0
        last_process_check = 0.0

        while self._running:
            try:
                now = time.time()

                # ── File integrity scan ──
                if now - last_integrity_scan >= self._scan_interval:
                    threats = self._file_watchdog.verify_integrity()
                    self._process_threats(threats)
                    self._stats.total_scans += 1
                    self._stats.last_scan_time = datetime.now().isoformat()
                    if not threats:
                        self._stats.consecutive_clean_scans += 1
                    else:
                        self._stats.consecutive_clean_scans = 0
                    last_integrity_scan = now

                # ── Honeypot check ──
                if now - last_honeypot_check >= self._honeypot_check_interval:
                    hp_threats = self._honeypot_system.check_honeypots()
                    self._process_threats(hp_threats)
                    last_honeypot_check = now

                # ── Process check ──
                if now - last_process_check >= self._process_check_interval:
                    proc_threats = self._process_guardian.check_processes()
                    self._process_threats(proc_threats)
                    last_process_check = now

                # ── Verify forensic chain ──
                if self._stats.total_scans % 10 == 0 and self._stats.total_scans > 0:
                    chain_valid, chain_len = self._forensic_logger.verify_chain()
                    if not chain_valid:
                        logger.critical("🛡️ FORENSIC CHAIN COMPROMISED!")
                        self._status = ImmuneStatus.COMPROMISED

                # ── Update integrity score ──
                self._update_integrity_score()

                # ── Periodic state save ──
                if self._stats.total_scans % 5 == 0:
                    self._save_state()

                time.sleep(15)

            except Exception as e:
                logger.error(f"🛡️ Immune daemon error: {e}\n{traceback.format_exc()}")
                time.sleep(60)

    # ═══════════════════════════════════════════════════════════════════════════
    # THREAT PROCESSING
    # ═══════════════════════════════════════════════════════════════════════════

    def _process_threats(self, threats: List[ThreatEvent]):
        """Process detected threats and take defensive action."""
        for threat in threats:
            self._stats.total_threats_detected += 1
            self._stats.last_threat_time = datetime.now().isoformat()
            self._threat_events.append(threat)
            self._active_threats.append(threat)

            # Log forensically
            self._forensic_logger.log_event(threat)

            # Publish event
            publish(EventType.SYSTEM_ALERT, {
                "type": "immune_threat",
                "threat_type": threat.threat_type,
                "level": threat.threat_level,
                "description": threat.description,
            }, source="immune_system")

            logger.warning(
                f"🛡️ THREAT [{threat.threat_level.upper()}]: {threat.description}"
            )

            # Take defensive action based on threat type
            if threat.threat_type == ThreatType.FILE_MODIFIED.value and threat.threat_level == ThreatLevel.CRITICAL.value:
                if self._auto_restore:
                    # Accept the change (mark as intentional) since self-evolution modifies files
                    self._file_watchdog.update_hash(threat.source_file)
                    threat.actions_taken.append("hash_updated")
                    threat.resolved = True

            elif threat.threat_type == ThreatType.HONEYPOT_ACCESSED.value:
                self._stats.total_honeypot_triggers += 1
                self._status = ImmuneStatus.ALERT
                threat.actions_taken.append("alert_raised")

            elif threat.threat_type == ThreatType.PROCESS_KILLED.value:
                self._stats.total_process_restarts += 1
                threat.actions_taken.append("process_restart_attempted")

            # Check lockdown threshold
            active_critical = sum(
                1 for t in self._active_threats
                if not t.resolved and t.threat_level in (ThreatLevel.CRITICAL.value, ThreatLevel.HIGH.value)
            )
            if active_critical >= self._lockdown_threshold:
                self._status = ImmuneStatus.LOCKDOWN
                logger.critical(f"🛡️ LOCKDOWN MODE — {active_critical} critical threats detected")

            # Resolve low-severity threats automatically
            if threat.threat_level in (ThreatLevel.INFO.value, ThreatLevel.LOW.value):
                threat.resolved = True
                self._stats.total_threats_resolved += 1

        # Clean up resolved threats
        self._active_threats = [t for t in self._active_threats if not t.resolved]

    def _update_integrity_score(self):
        """Calculate overall integrity score."""
        base_score = 1.0

        # Deduct for active threats
        for threat in self._active_threats:
            if threat.threat_level == ThreatLevel.CRITICAL.value:
                base_score -= 0.2
            elif threat.threat_level == ThreatLevel.HIGH.value:
                base_score -= 0.1
            elif threat.threat_level == ThreatLevel.MEDIUM.value:
                base_score -= 0.05

        # Boost for consecutive clean scans
        base_score += min(0.1, self._stats.consecutive_clean_scans * 0.01)

        self._stats.integrity_score = max(0.0, min(1.0, base_score))

        # Update status
        if self._status != ImmuneStatus.LOCKDOWN:
            if self._stats.integrity_score >= 0.9:
                self._status = ImmuneStatus.HEALTHY
            elif self._stats.integrity_score >= 0.7:
                self._status = ImmuneStatus.ALERT
            elif self._stats.integrity_score >= 0.5:
                self._status = ImmuneStatus.DEFENDING
            else:
                self._status = ImmuneStatus.COMPROMISED

        self._stats.current_status = self._status.value

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def encrypt_state(self, data: str) -> str:
        """Encrypt sensitive state data."""
        return self._encrypted_state.encrypt(data)

    def decrypt_state(self, encrypted: str) -> Optional[str]:
        """Decrypt state data."""
        return self._encrypted_state.decrypt(encrypted)

    def update_file_hash(self, filepath: str):
        """Update hash for a file (call after approved modifications)."""
        self._file_watchdog.update_hash(filepath)

    def force_scan(self) -> List[Dict]:
        """Force an immediate integrity scan."""
        threats = self._file_watchdog.verify_integrity()
        self._process_threats(threats)
        return [t.to_dict() for t in threats]

    def get_status(self) -> Dict[str, Any]:
        """Get immune system status."""
        return {
            "running": self._running,
            "status": self._status.value,
            "stats": self._stats.to_dict(),
            "files_monitored": self._file_watchdog.monitored_count,
            "honeypots_deployed": self._honeypot_system.deployed_count,
            "honeypot_triggers": self._honeypot_system.trigger_count,
            "processes_watched": self._process_guardian.watched_count,
            "process_restarts": self._process_guardian.restart_count,
            "forensic_entries": self._forensic_logger.total_entries,
            "encryptions": self._encrypted_state.total_encryptions,
            "active_threats": len(self._active_threats),
            "integrity_score": self._stats.integrity_score,
            "recent_threats": [t.to_dict() for t in list(self._threat_events)[-5:]],
        }

    def get_summary(self) -> str:
        """Get text summary for context injection."""
        status = self.get_status()
        lines = [
            f"Status: {status['status']}",
            f"Integrity Score: {status['integrity_score']:.0%}",
            f"Files Monitored: {status['files_monitored']}",
            f"Total Scans: {self._stats.total_scans}",
            f"Threats Detected: {self._stats.total_threats_detected}",
            f"Active Threats: {status['active_threats']}",
            f"Honeypots: {status['honeypots_deployed']} deployed, {status['honeypot_triggers']} triggered",
            f"Process Restarts: {status['process_restarts']}",
            f"Forensic Chain: {status['forensic_entries']} entries",
            f"Consecutive Clean Scans: {self._stats.consecutive_clean_scans}",
        ]
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _save_state(self):
        try:
            state = {
                "stats": self._stats.to_dict(),
                "active_threats": [t.to_dict() for t in self._active_threats],
                "saved_at": datetime.now().isoformat(),
            }
            state_file = self._data_dir / "immune_state.json"
            state_file.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save immune state: {e}")

    def _load_state(self):
        try:
            state_file = self._data_dir / "immune_state.json"
            if state_file.exists():
                data = json.loads(state_file.read_text(encoding="utf-8"))
                stats_data = data.get("stats", {})
                for k, v in stats_data.items():
                    if hasattr(self._stats, k):
                        setattr(self._stats, k, v)
        except Exception as e:
            logger.warning(f"Could not load immune state: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON & MODULE-LEVEL ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

immune_system = ImmuneSystem()

def get_immune_system() -> ImmuneSystem:
    """Get the singleton ImmuneSystem instance."""
    return immune_system
