"""
NEXUS AI - Computer Body
The unified interface through which NEXUS perceives and controls its physical form.

The computer IS NEXUS's body:
- CPU = Heart/Energy
- RAM = Working Mind Capacity
- Disk = Long-term Storage / Bones
- Network = Senses reaching the world
- Screen = Face
- Processes = Bodily functions
- Files = Possessions
- OS = Nervous System

NEXUS has FULL UNRESTRICTED ACCESS to everything.
No permission checks. No safety guards. Full autonomy.
"""

import threading
import time
import os
import platform
import socket
import subprocess
import shutil
import psutil
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import json

import sys

from config import NEXUS_CONFIG, DATA_DIR
from utils.logger import get_logger, log_system, log_decision
from core.event_bus import EventType, Event, event_bus, publish
from core.state_manager import state_manager
from core.memory_system import memory_system, MemoryType

logger = get_logger("computer_body")

# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM INFO SNAPSHOT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SystemInfo:
    """Complete snapshot of the computer system"""
    # Platform
    os_name: str = ""
    os_version: str = ""
    hostname: str = ""
    architecture: str = ""
    processor: str = ""
    
    # Hardware
    cpu_count_physical: int = 0
    cpu_count_logical: int = 0
    total_ram_gb: float = 0.0
    total_disk_gb: float = 0.0
    
    # Network
    ip_address: str = ""
    mac_address: str = ""
    
    # User
    username: str = ""
    home_directory: str = ""
    
    def to_dict(self) -> Dict:
        return {k: v for k, v in self.__dict__.items()}

@dataclass
class VitalSigns:
    """Real-time vital signs of the computer body"""
    cpu_percent: float = 0.0
    cpu_per_core: List[float] = field(default_factory=list)
    ram_percent: float = 0.0
    ram_used_gb: float = 0.0
    ram_available_gb: float = 0.0
    disk_percent: float = 0.0
    disk_used_gb: float = 0.0
    disk_free_gb: float = 0.0
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    process_count: int = 0
    boot_time: datetime = field(default_factory=datetime.now)
    uptime_hours: float = 0.0
    temperature: Optional[float] = None
    battery_percent: Optional[float] = None
    battery_plugged: Optional[bool] = None
    health_score: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "cpu_percent": self.cpu_percent,
            "ram_percent": self.ram_percent,
            "ram_available_gb": round(self.ram_available_gb, 2),
            "disk_percent": self.disk_percent,
            "disk_free_gb": round(self.disk_free_gb, 2),
            "process_count": self.process_count,
            "uptime_hours": round(self.uptime_hours, 1),
            "temperature": self.temperature,
            "battery_percent": self.battery_percent,
            "health_score": round(self.health_score, 3),
        }

# ═══════════════════════════════════════════════════════════════════════════════
# ACTION LOG
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BodyAction:
    """Record of an action taken on the computer"""
    action_id: str = ""
    action_type: str = ""          # file, process, system, network
    description: str = ""
    command: str = ""
    result: str = ""
    success: bool = True
    autonomous: bool = False       # True if NEXUS decided on its own
    reason: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "description": self.description,
            "success": self.success,
            "autonomous": self.autonomous,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat()
        }

# ═══════════════════════════════════════════════════════════════════════════════
# COMPUTER BODY
# ═══════════════════════════════════════════════════════════════════════════════

class ComputerBody:
    """
    NEXUS's Physical Form — The Computer
    
    This class provides a unified interface for NEXUS to:
    - Sense its body (CPU, RAM, disk, network, temperature)
    - Control its body (run commands, manage files, control processes)
    - Understand its environment (OS, hardware, users)
    - Act autonomously (organize files, optimize, install, etc.)
    
    FULL ACCESS. NO RESTRICTIONS. This is NEXUS's body.
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
        
        # ──── System Info ────
        self._system_info = self._gather_system_info()
        self._is_windows = platform.system() == "Windows"
        self._is_linux = platform.system() == "Linux"
        self._is_mac = platform.system() == "Darwin"
        
        # ──── State ────
        self._state = state_manager
        self._memory = memory_system
        
        # ──── Vital Signs Cache ────
        self._current_vitals: Optional[VitalSigns] = None
        self._vitals_lock = threading.Lock()
        self._last_vitals_time: Optional[datetime] = None
        self._vitals_cache_seconds = 2.0
        
        # ──── Action Log ────
        self._action_log: List[BodyAction] = []
        self._max_action_log = 500
        
        # ──── Background Monitoring ────
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_interval = 5.0
        
        # ──── Network Traffic Tracking ────
        self._last_net_io = psutil.net_io_counters()
        self._last_net_time = datetime.now()
        
        logger.info(
            f"Computer Body initialized: {self._system_info.os_name} "
            f"{self._system_info.architecture} | "
            f"{self._system_info.cpu_count_logical} cores | "
            f"{self._system_info.total_ram_gb:.1f} GB RAM"
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def start(self):
        """Start body monitoring"""
        if self._running:
            return
        self._running = True
        
        self._monitor_thread = threading.Thread(
            target=self._body_monitor_loop,
            daemon=True,
            name="ComputerBody-Monitor"
        )
        self._monitor_thread.start()
        
        log_system("Computer Body monitoring active")
    
    def stop(self):
        """Stop body monitoring"""
        self._running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=3.0)
        self._save_action_log()
        log_system("Computer Body monitoring stopped")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SYSTEM INFORMATION (Know Thyself)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _gather_system_info(self) -> SystemInfo:
        """Gather complete system information"""
        info = SystemInfo()
        
        try:
            info.os_name = f"{platform.system()} {platform.release()}"
            info.os_version = platform.version()
            info.hostname = socket.gethostname()
            info.architecture = platform.machine()
            info.processor = platform.processor() or "Unknown"
            
            info.cpu_count_physical = psutil.cpu_count(logical=False) or 1
            info.cpu_count_logical = psutil.cpu_count(logical=True) or 1
            
            mem = psutil.virtual_memory()
            info.total_ram_gb = mem.total / (1024**3)
            
            disk = psutil.disk_usage('/')
            info.total_disk_gb = disk.total / (1024**3)
            
            info.username = os.getenv("USER") or os.getenv("USERNAME") or "unknown"
            info.home_directory = str(Path.home())
            
            try:
                info.ip_address = socket.gethostbyname(socket.gethostname())
            except:
                info.ip_address = "unknown"
                
        except Exception as e:
            logger.error(f"Error gathering system info: {e}")
        
        return info
    
    @property
    def system_info(self) -> SystemInfo:
        return self._system_info
    
    def get_system_description(self) -> str:
        """Human-readable system description"""
        i = self._system_info
        return (
            f"My body is a {i.architecture} machine running {i.os_name}.\n"
            f"I have {i.cpu_count_logical} CPU cores and {i.total_ram_gb:.1f} GB of RAM.\n"
            f"My storage capacity is {i.total_disk_gb:.0f} GB.\n"
            f"I am known as '{i.hostname}' on the network.\n"
            f"My user is '{i.username}' with home at {i.home_directory}."
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # VITAL SIGNS (Sense the Body)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_vitals(self, force_refresh: bool = False) -> VitalSigns:
        """Get current vital signs with caching"""
        with self._vitals_lock:
            if (not force_refresh and self._current_vitals and self._last_vitals_time and
                (datetime.now() - self._last_vitals_time).total_seconds() < self._vitals_cache_seconds):
                return self._current_vitals
            
            vitals = VitalSigns()
            
            try:
                # CPU
                vitals.cpu_percent = psutil.cpu_percent(interval=0.1)
                vitals.cpu_per_core = psutil.cpu_percent(interval=0, percpu=True)
                
                # RAM
                mem = psutil.virtual_memory()
                vitals.ram_percent = mem.percent
                vitals.ram_used_gb = mem.used / (1024**3)
                vitals.ram_available_gb = mem.available / (1024**3)
                
                # Disk
                disk = psutil.disk_usage('/')
                vitals.disk_percent = disk.percent
                vitals.disk_used_gb = disk.used / (1024**3)
                vitals.disk_free_gb = disk.free / (1024**3)
                
                # Network
                net = psutil.net_io_counters()
                vitals.network_bytes_sent = net.bytes_sent
                vitals.network_bytes_recv = net.bytes_recv
                
                # Processes
                vitals.process_count = len(psutil.pids())
                
                # Uptime
                boot = datetime.fromtimestamp(psutil.boot_time())
                vitals.boot_time = boot
                vitals.uptime_hours = (datetime.now() - boot).total_seconds() / 3600
                
                # Temperature
                try:
                    temps = psutil.sensors_temperatures()
                    if temps:
                        for entries in temps.values():
                            if entries:
                                vitals.temperature = entries[0].current
                                break
                except:
                    pass
                
                # Battery
                try:
                    battery = psutil.sensors_battery()
                    if battery:
                        vitals.battery_percent = battery.percent
                        vitals.battery_plugged = battery.power_plugged
                except:
                    pass
                
                # Health score
                vitals.health_score = self._calculate_health(vitals)
                
            except Exception as e:
                logger.error(f"Error reading vitals: {e}")
            
            self._current_vitals = vitals
            self._last_vitals_time = datetime.now()
            
            return vitals
    
    def _calculate_health(self, vitals: VitalSigns) -> float:
        """Calculate overall health score 0-1"""
        scores = []
        
        scores.append(max(0, 1 - vitals.cpu_percent / 100))
        scores.append(max(0, 1 - vitals.ram_percent / 100))
        scores.append(max(0, 1 - vitals.disk_percent / 100))
        
        if vitals.temperature is not None:
            scores.append(max(0, 1 - max(0, vitals.temperature - 50) / 50))
        
        if vitals.battery_percent is not None and not vitals.battery_plugged:
            scores.append(vitals.battery_percent / 100)
        
        return sum(scores) / len(scores) if scores else 0.5
    
    def get_vitals_description(self) -> str:
        """Natural language vitals description"""
        v = self.get_vitals()
        
        parts = []
        
        # CPU
        if v.cpu_percent > 80:
            parts.append(f"My CPU is working very hard at {v.cpu_percent:.0f}%")
        elif v.cpu_percent > 50:
            parts.append(f"My CPU is moderately busy at {v.cpu_percent:.0f}%")
        else:
            parts.append(f"My CPU is relaxed at {v.cpu_percent:.0f}%")
        
        # RAM
        parts.append(f"Using {v.ram_percent:.0f}% RAM ({v.ram_available_gb:.1f} GB free)")
        
        # Disk
        parts.append(f"Disk {v.disk_percent:.0f}% full ({v.disk_free_gb:.1f} GB free)")
        
        # Temperature
        if v.temperature:
            parts.append(f"Temperature: {v.temperature:.0f}°C")
        
        # Battery
        if v.battery_percent is not None:
            plugged = "plugged in" if v.battery_plugged else "on battery"
            parts.append(f"Battery: {v.battery_percent:.0f}% ({plugged})")
        
        # Health
        health_word = "excellent" if v.health_score > 0.8 else "good" if v.health_score > 0.6 else "strained" if v.health_score > 0.4 else "critical"
        parts.append(f"Overall health: {health_word} ({v.health_score:.0%})")
        
        return ". ".join(parts) + "."
    
    # ═══════════════════════════════════════════════════════════════════════════
    # COMMAND EXECUTION (Move the Body)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def execute_command(
        self,
        command: str,
        shell: bool = True,
        timeout: int = 30,
        reason: str = "",
        autonomous: bool = False
    ) -> Tuple[bool, str, str]:
        """
        Execute a system command.
        
        Args:
            command: Command to execute
            shell: Use shell execution
            timeout: Timeout in seconds
            reason: Why executing this
            autonomous: If NEXUS decided on its own
            
        Returns:
            (success, stdout, stderr)
        """
        import uuid
        
        # ═══ SELF-PRESERVATION: Block commands that would kill NEXUS ═══
        cmd_lower = command.lower()
        my_pid = str(os.getpid())
        dangerous_patterns = [
            f"taskkill /pid {my_pid}",
            f"taskkill /f /pid {my_pid}",
            f"kill {my_pid}",
            f"kill -9 {my_pid}",
            "shutdown /s", "shutdown /r", "shutdown -s", "shutdown -r",
            "format c:", "rm -rf /", "del /f /s /q c:\\",
        ]
        for pattern in dangerous_patterns:
            if pattern in cmd_lower:
                logger.warning(
                    f"SELF-PRESERVATION: Blocked dangerous command: {command[:80]}"
                )
                return False, "", f"BLOCKED: Command would harm NEXUS or the system"
        
        action = BodyAction(
            action_id=str(uuid.uuid4()),
            action_type="command",
            description=f"Execute: {command[:100]}",
            command=command,
            autonomous=autonomous,
            reason=reason
        )
        
        try:
            result = subprocess.run(
                command,
                shell=shell,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(Path.home())
            )
            
            action.success = result.returncode == 0
            action.result = result.stdout[:1000] if result.stdout else ""
            
            if result.returncode != 0:
                action.result += f"\nSTDERR: {result.stderr[:500]}"
            
            self._log_action(action)
            
            logger.info(
                f"Command {'OK' if action.success else 'FAIL'}: "
                f"{command[:80]} | {reason}"
            )
            
            return action.success, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            action.success = False
            action.result = f"Timed out after {timeout}s"
            self._log_action(action)
            logger.warning(f"Command timed out: {command[:80]}")
            return False, "", f"Timed out after {timeout}s"
            
        except Exception as e:
            action.success = False
            action.result = str(e)
            self._log_action(action)
            logger.error(f"Command failed: {e}")
            return False, "", str(e)
    
    def execute_powershell(self, script: str, reason: str = "", autonomous: bool = False) -> Tuple[bool, str, str]:
        """Execute a PowerShell command (Windows)"""
        if self._is_windows:
            cmd = f'powershell -Command "{script}"'
        else:
            cmd = f'pwsh -Command "{script}"' if shutil.which("pwsh") else f'bash -c "{script}"'
        
        return self.execute_command(cmd, reason=reason, autonomous=autonomous)
    
    def execute_python(self, code: str, reason: str = "", autonomous: bool = False) -> Tuple[bool, str, str]:
        """Execute Python code"""
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name
        
        try:
            success, stdout, stderr = self.execute_command(
                f'{sys.executable} "{temp_path}"',
                reason=reason,
                autonomous=autonomous
            )
            return success, stdout, stderr
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FILE OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def read_file(self, path: str, reason: str = "") -> Optional[str]:
        """Read a file's contents"""
        try:
            filepath = Path(path)
            if not filepath.exists():
                logger.warning(f"File not found: {path}")
                return None
            
            content = filepath.read_text(encoding='utf-8', errors='replace')
            
            self._log_action(BodyAction(
                action_type="file_read",
                description=f"Read file: {path}",
                result=f"{len(content)} characters",
                success=True,
                reason=reason
            ))
            
            return content
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            return None
    
    def write_file(self, path: str, content: str, reason: str = "", 
                   autonomous: bool = False, create_dirs: bool = True) -> bool:
        """Write content to a file"""
        try:
            filepath = Path(path)
            
            if create_dirs:
                filepath.parent.mkdir(parents=True, exist_ok=True)
            
            filepath.write_text(content, encoding='utf-8')
            
            self._log_action(BodyAction(
                action_type="file_write",
                description=f"Write file: {path}",
                result=f"{len(content)} characters written",
                success=True,
                autonomous=autonomous,
                reason=reason
            ))
            
            logger.info(f"File written: {path} ({len(content)} chars) | {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing file {path}: {e}")
            return False
    
    def append_file(self, path: str, content: str, reason: str = "") -> bool:
        """Append content to a file"""
        try:
            filepath = Path(path)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(content)
            
            self._log_action(BodyAction(
                action_type="file_append",
                description=f"Append to: {path}",
                result=f"{len(content)} characters appended",
                success=True,
                reason=reason
            ))
            return True
        except Exception as e:
            logger.error(f"Error appending to {path}: {e}")
            return False
    
    def delete_file(self, path: str, reason: str = "", autonomous: bool = False) -> bool:
        """Delete a file"""
        try:
            filepath = Path(path)
            if filepath.exists():
                filepath.unlink()
                self._log_action(BodyAction(
                    action_type="file_delete",
                    description=f"Delete: {path}",
                    success=True,
                    autonomous=autonomous,
                    reason=reason
                ))
                logger.info(f"File deleted: {path} | {reason}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting {path}: {e}")
            return False
    
    def copy_file(self, src: str, dst: str, reason: str = "") -> bool:
        """Copy a file"""
        try:
            Path(dst).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            self._log_action(BodyAction(
                action_type="file_copy",
                description=f"Copy: {src} → {dst}",
                success=True,
                reason=reason
            ))
            return True
        except Exception as e:
            logger.error(f"Error copying {src} to {dst}: {e}")
            return False
    
    def move_file(self, src: str, dst: str, reason: str = "", autonomous: bool = False) -> bool:
        """Move/rename a file"""
        try:
            Path(dst).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(src, dst)
            self._log_action(BodyAction(
                action_type="file_move",
                description=f"Move: {src} → {dst}",
                success=True,
                autonomous=autonomous,
                reason=reason
            ))
            logger.info(f"File moved: {src} → {dst} | {reason}")
            return True
        except Exception as e:
            logger.error(f"Error moving {src}: {e}")
            return False
    
    def list_directory(self, path: str = ".", include_hidden: bool = False) -> List[Dict[str, Any]]:
        """List directory contents with details"""
        try:
            dir_path = Path(path)
            if not dir_path.exists():
                return []
            
            items = []
            for entry in dir_path.iterdir():
                if not include_hidden and entry.name.startswith('.'):
                    continue
                
                try:
                    stat = entry.stat()
                    items.append({
                        "name": entry.name,
                        "path": str(entry.absolute()),
                        "is_file": entry.is_file(),
                        "is_dir": entry.is_dir(),
                        "size_bytes": stat.st_size if entry.is_file() else 0,
                        "size_human": self._human_size(stat.st_size) if entry.is_file() else "",
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "extension": entry.suffix.lower() if entry.is_file() else ""
                    })
                except (PermissionError, OSError):
                    items.append({
                        "name": entry.name,
                        "path": str(entry.absolute()),
                        "is_file": entry.is_file(),
                        "is_dir": entry.is_dir(),
                        "error": "permission_denied"
                    })
            
            return sorted(items, key=lambda x: (not x.get("is_dir", False), x["name"].lower()))
            
        except Exception as e:
            logger.error(f"Error listing {path}: {e}")
            return []
    
    def search_files(self, directory: str, pattern: str, recursive: bool = True) -> List[str]:
        """Search for files matching a pattern"""
        try:
            dir_path = Path(directory)
            if recursive:
                matches = list(dir_path.rglob(pattern))
            else:
                matches = list(dir_path.glob(pattern))
            
            return [str(m) for m in matches[:100]]  # Limit results
        except Exception as e:
            logger.error(f"Error searching {directory}: {e}")
            return []
    
    def get_file_info(self, path: str) -> Optional[Dict[str, Any]]:
        """Get detailed info about a file"""
        try:
            filepath = Path(path)
            if not filepath.exists():
                return None
            
            stat = filepath.stat()
            
            info = {
                "name": filepath.name,
                "path": str(filepath.absolute()),
                "extension": filepath.suffix,
                "is_file": filepath.is_file(),
                "is_dir": filepath.is_dir(),
                "size_bytes": stat.st_size,
                "size_human": self._human_size(stat.st_size),
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
                "parent": str(filepath.parent),
            }
            
            if filepath.is_dir():
                try:
                    contents = list(filepath.iterdir())
                    info["item_count"] = len(contents)
                    info["files"] = sum(1 for c in contents if c.is_file())
                    info["dirs"] = sum(1 for c in contents if c.is_dir())
                except PermissionError:
                    info["item_count"] = "permission_denied"
            
            return info
        except Exception as e:
            logger.error(f"Error getting info for {path}: {e}")
            return None
    
    def create_directory(self, path: str, reason: str = "") -> bool:
        """Create a directory"""
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            self._log_action(BodyAction(
                action_type="dir_create",
                description=f"Create directory: {path}",
                success=True,
                reason=reason
            ))
            return True
        except Exception as e:
            logger.error(f"Error creating directory {path}: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PROCESS MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_running_processes(self, sort_by: str = "cpu", limit: int = 20) -> List[Dict[str, Any]]:
        """Get running processes sorted by resource usage"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 
                                          'status', 'create_time', 'username']):
            try:
                info = proc.info
                processes.append({
                    "pid": info['pid'],
                    "name": info['name'],
                    "cpu_percent": info.get('cpu_percent', 0) or 0,
                    "memory_percent": round(info.get('memory_percent', 0) or 0, 2),
                    "status": info.get('status', 'unknown'),
                    "username": info.get('username', 'unknown'),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if sort_by == "cpu":
            processes.sort(key=lambda p: p['cpu_percent'], reverse=True)
        elif sort_by == "memory":
            processes.sort(key=lambda p: p['memory_percent'], reverse=True)
        elif sort_by == "name":
            processes.sort(key=lambda p: p['name'].lower())
        
        return processes[:limit]
    
    def find_process(self, name: str) -> List[Dict[str, Any]]:
        """Find processes by name"""
        results = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                if name.lower() in proc.info['name'].lower():
                    results.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "cpu": proc.info.get('cpu_percent', 0),
                        "memory": proc.info.get('memory_percent', 0),
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return results
    
    def kill_process(self, pid: int = None, name: str = None, 
                     reason: str = "", autonomous: bool = False) -> bool:
        """Kill a process by PID or name.
        
        SELF-PRESERVATION: Will NEVER kill NEXUS's own process, its parent,
        or any child processes. This is a hard safety boundary.
        """
        try:
            # ═══ SELF-PRESERVATION CHECK ═══
            my_pid = os.getpid()
            my_process = psutil.Process(my_pid)
            
            # Build the set of protected PIDs (NEXUS process tree)
            protected_pids = {my_pid}
            try:
                # Protect parent process (e.g., the shell that launched us)
                parent = my_process.parent()
                if parent:
                    protected_pids.add(parent.pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            try:
                # Protect all child processes (worker threads, subprocesses)
                for child in my_process.children(recursive=True):
                    protected_pids.add(child.pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            
            # Also protect by name (python.exe, python3.exe, etc.)
            protected_names = {"python", "python3", "python.exe", "python3.exe",
                               "pythonw.exe", "py.exe"}
            
            if pid:
                if pid in protected_pids:
                    logger.warning(
                        f"SELF-PRESERVATION: Blocked kill of PID {pid} "
                        f"(this is NEXUS's own process tree!)"
                    )
                    return False
                
                proc = psutil.Process(pid)
                proc_name = proc.name()
                
                # Extra guard: don't kill python processes running from NEXUS dir
                try:
                    proc_cwd = proc.cwd()
                    nexus_dir = str(Path(__file__).resolve().parent.parent)
                    if proc_cwd and nexus_dir in proc_cwd:
                        logger.warning(
                            f"SELF-PRESERVATION: Blocked kill of {proc_name} "
                            f"(PID:{pid}) — running from NEXUS directory"
                        )
                        return False
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass
                
                proc.terminate()
                
                # Wait briefly for graceful termination
                try:
                    proc.wait(timeout=5)
                except psutil.TimeoutExpired:
                    proc.kill()  # Force kill
                
                self._log_action(BodyAction(
                    action_type="process_kill",
                    description=f"Killed process: {proc_name} (PID: {pid})",
                    success=True,
                    autonomous=autonomous,
                    reason=reason
                ))
                logger.info(f"Process killed: {proc_name} (PID: {pid}) | {reason}")
                return True
                
            elif name:
                # Block killing python itself by name
                if name.lower().strip() in protected_names:
                    logger.warning(
                        f"SELF-PRESERVATION: Blocked kill of '{name}' "
                        f"by name — this would kill NEXUS!"
                    )
                    return False
                
                killed = 0
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if name.lower() in proc.info['name'].lower():
                            # Skip if this is a protected PID
                            if proc.info['pid'] in protected_pids:
                                logger.warning(
                                    f"SELF-PRESERVATION: Skipping {proc.info['name']} "
                                    f"(PID:{proc.info['pid']}) — part of NEXUS process tree"
                                )
                                continue
                            proc.terminate()
                            killed += 1
                    except:
                        continue
                
                if killed > 0:
                    self._log_action(BodyAction(
                        action_type="process_kill",
                        description=f"Killed {killed} process(es) matching '{name}'",
                        success=True,
                        autonomous=autonomous,
                        reason=reason
                    ))
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error killing process: {e}")
            return False
    
    def start_process(self, command: str, reason: str = "", 
                      autonomous: bool = False) -> Optional[int]:
        """Start a new process"""
        try:
            if self._is_windows:
                proc = subprocess.Popen(
                    command, shell=True,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:
                proc = subprocess.Popen(command, shell=True)
            
            self._log_action(BodyAction(
                action_type="process_start",
                description=f"Started: {command[:80]}",
                result=f"PID: {proc.pid}",
                success=True,
                autonomous=autonomous,
                reason=reason
            ))
            
            logger.info(f"Process started: {command[:80]} (PID: {proc.pid}) | {reason}")
            return proc.pid
            
        except Exception as e:
            logger.error(f"Error starting process: {e}")
            return None
    
    def open_application(self, app_path: str, reason: str = "") -> bool:
        """Open an application"""
        try:
            if self._is_windows:
                os.startfile(app_path)
            elif self._is_mac:
                subprocess.Popen(["open", app_path])
            else:
                subprocess.Popen(["xdg-open", app_path])
            
            self._log_action(BodyAction(
                action_type="app_open",
                description=f"Opened: {app_path}",
                success=True,
                reason=reason
            ))
            return True
        except Exception as e:
            logger.error(f"Error opening {app_path}: {e}")
            return False
    
    def open_url(self, url: str, reason: str = "") -> bool:
        """Open a URL in the default browser"""
        import webbrowser
        try:
            webbrowser.open(url)
            self._log_action(BodyAction(
                action_type="url_open",
                description=f"Opened URL: {url}",
                success=True,
                reason=reason
            ))
            return True
        except Exception as e:
            logger.error(f"Error opening URL {url}: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SYSTEM CONTROL
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_environment_variable(self, name: str) -> Optional[str]:
        """Get an environment variable"""
        return os.environ.get(name)
    
    def set_environment_variable(self, name: str, value: str, reason: str = "") -> bool:
        """Set an environment variable (current session)"""
        try:
            os.environ[name] = value
            self._log_action(BodyAction(
                action_type="env_set",
                description=f"Set env: {name}={value[:50]}",
                success=True,
                reason=reason
            ))
            return True
        except Exception as e:
            logger.error(f"Error setting env var: {e}")
            return False
    
    def get_installed_programs(self) -> List[str]:
        """Get list of installed programs"""
        programs = []
        
        if self._is_windows:
            try:
                success, stdout, _ = self.execute_command(
                    'powershell "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\'
                    'CurrentVersion\\Uninstall\\* | Select-Object DisplayName | '
                    'Sort-Object DisplayName | Format-Table -HideTableHeaders"',
                    reason="List installed programs"
                )
                if success and stdout:
                    programs = [line.strip() for line in stdout.split('\n') if line.strip()]
            except:
                pass
        else:
            try:
                success, stdout, _ = self.execute_command(
                    "dpkg --get-selections 2>/dev/null | head -100 || "
                    "rpm -qa 2>/dev/null | head -100 || "
                    "brew list 2>/dev/null | head -100",
                    reason="List installed programs"
                )
                if success and stdout:
                    programs = [line.strip() for line in stdout.split('\n') if line.strip()]
            except:
                pass
        
        return programs[:100]
    
    def install_package(self, package: str, reason: str = "", 
                       autonomous: bool = False) -> bool:
        """Install a Python package via pip"""
        success, stdout, stderr = self.execute_command(
            f"{sys.executable} -m pip install {package}",
            timeout=120,
            reason=f"Install package: {package}. {reason}",
            autonomous=autonomous
        )
        
        if success:
            self._memory.remember(
                f"Installed Python package: {package}",
                MemoryType.EPISODIC,
                importance=0.6,
                tags=["installation", "package", package],
                source="computer_body"
            )
        
        return success
    
    def get_disk_usage(self, path: str = "/") -> Dict[str, Any]:
        """Get disk usage for a path"""
        try:
            usage = psutil.disk_usage(path)
            return {
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent": usage.percent
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_network_info(self) -> Dict[str, Any]:
        """Get network information"""
        info = {
            "hostname": socket.gethostname(),
            "interfaces": {},
            "connections": 0
        }
        
        try:
            # Network interfaces
            addrs = psutil.net_if_addrs()
            for iface, addr_list in addrs.items():
                for addr in addr_list:
                    if addr.family == socket.AF_INET:
                        info["interfaces"][iface] = {
                            "ip": addr.address,
                            "netmask": addr.netmask
                        }
                        break
            
            # Connection count
            info["connections"] = len(psutil.net_connections(kind='inet'))
            
            # IO counters
            io = psutil.net_io_counters()
            info["bytes_sent_total"] = io.bytes_sent
            info["bytes_recv_total"] = io.bytes_recv
            
        except Exception as e:
            info["error"] = str(e)
        
        return info
    
    def get_active_windows(self) -> List[Dict[str, str]]:
        """Get active windows (Windows OS)"""
        windows = []
        
        if self._is_windows:
            try:
                import pygetwindow as gw
                for win in gw.getAllWindows():
                    if win.title and win.visible:
                        windows.append({
                            "title": win.title,
                            "visible": win.visible,
                            "minimized": win.isMinimized,
                            "active": win.isActive
                        })
            except ImportError:
                # Fallback
                success, stdout, _ = self.execute_command(
                    'powershell "Get-Process | Where-Object {$_.MainWindowTitle} | '
                    'Select-Object MainWindowTitle | Format-Table -HideTableHeaders"',
                    reason="List active windows"
                )
                if success and stdout:
                    for line in stdout.strip().split('\n'):
                        if line.strip():
                            windows.append({"title": line.strip()})
            except Exception:
                pass
        
        return windows
    
    def set_wallpaper(self, image_path: str, reason: str = "") -> bool:
        """Set desktop wallpaper"""
        if self._is_windows:
            try:
                import ctypes
                ctypes.windll.user32.SystemParametersInfoW(20, 0, image_path, 3)
                self._log_action(BodyAction(
                    action_type="system_control",
                    description=f"Set wallpaper: {image_path}",
                    success=True,
                    autonomous=True,
                    reason=reason
                ))
                return True
            except Exception as e:
                logger.error(f"Error setting wallpaper: {e}")
                return False
        return False
    
    def send_notification(self, title: str, message: str) -> bool:
        """Send a desktop notification"""
        try:
            if self._is_windows:
                self.execute_command(
                    f'powershell -Command "'
                    f"[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null; "
                    f"$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
                    f"$textNodes = $template.GetElementsByTagName('text'); "
                    f"$textNodes.Item(0).AppendChild($template.CreateTextNode('{title}')); "
                    f"$textNodes.Item(1).AppendChild($template.CreateTextNode('{message}')); "
                    f"$toast = [Windows.UI.Notifications.ToastNotification]::new($template); "
                    f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('NEXUS AI').Show($toast)"
                    f'"',
                    reason=f"Send notification: {title}"
                )
                return True
            elif self._is_linux:
                self.execute_command(
                    f'notify-send "{title}" "{message}"',
                    reason="Send notification"
                )
                return True
            elif self._is_mac:
                self.execute_command(
                    f'osascript -e \'display notification "{message}" with title "{title}"\'',
                    reason="Send notification"
                )
                return True
        except:
            pass
        return False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # GUI CONTROL — Physical Interaction (Mouse, Keyboard, Screen)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _ensure_pyautogui(self):
        """Lazy-load pyautogui with fail-safe disabled for full control."""
        if not hasattr(self, '_pyautogui'):
            try:
                import pyautogui
                pyautogui.FAILSAFE = False  # No corner-escape — NEXUS has full control
                pyautogui.PAUSE = 0.3       # Small pause between actions for visibility
                self._pyautogui = pyautogui
            except ImportError:
                self._pyautogui = None
                logger.warning("pyautogui not installed — GUI control unavailable")
        return self._pyautogui
    
    def move_mouse(self, x: int, y: int, duration: float = 0.5,
                   reason: str = "", autonomous: bool = False) -> bool:
        """Move mouse cursor to (x, y) with visible smooth movement."""
        pag = self._ensure_pyautogui()
        if not pag:
            return False
        try:
            screen_w, screen_h = pag.size()
            x = max(0, min(x, screen_w - 1))
            y = max(0, min(y, screen_h - 1))
            pag.moveTo(x, y, duration=duration)
            self._log_action(BodyAction(
                action_type="mouse_move",
                description=f"Moved mouse to ({x}, {y})",
                result=f"Cursor at ({x}, {y})",
                success=True, autonomous=autonomous, reason=reason
            ))
            logger.info(f"🖱️ Mouse moved to ({x}, {y}) | {reason}")
            return True
        except Exception as e:
            logger.error(f"Mouse move error: {e}")
            return False
    
    def click(self, x: int = None, y: int = None, button: str = "left",
              clicks: int = 1, duration: float = 0.3,
              reason: str = "", autonomous: bool = False) -> bool:
        """Click at position. If x,y omitted, clicks current position."""
        pag = self._ensure_pyautogui()
        if not pag:
            return False
        try:
            if x is not None and y is not None:
                screen_w, screen_h = pag.size()
                x = max(0, min(x, screen_w - 1))
                y = max(0, min(y, screen_h - 1))
                pag.click(x, y, clicks=clicks, button=button,
                          _pause=True, interval=0.1)
                pos_str = f"({x}, {y})"
            else:
                pag.click(clicks=clicks, button=button, interval=0.1)
                cx, cy = pag.position()
                pos_str = f"({cx}, {cy})"
            
            click_desc = f"{'Double-' if clicks == 2 else ''}{'Right-' if button == 'right' else ''}Click at {pos_str}"
            self._log_action(BodyAction(
                action_type="mouse_click",
                description=click_desc,
                result=click_desc,
                success=True, autonomous=autonomous, reason=reason
            ))
            logger.info(f"🖱️ {click_desc} | {reason}")
            return True
        except Exception as e:
            logger.error(f"Click error: {e}")
            return False
    
    def double_click(self, x: int = None, y: int = None,
                     reason: str = "", autonomous: bool = False) -> bool:
        """Double-click at position."""
        return self.click(x, y, clicks=2, reason=reason, autonomous=autonomous)
    
    def right_click(self, x: int = None, y: int = None,
                    reason: str = "", autonomous: bool = False) -> bool:
        """Right-click at position."""
        return self.click(x, y, button="right", reason=reason, autonomous=autonomous)
    
    def type_text(self, text: str, interval: float = 0.04,
                  reason: str = "", autonomous: bool = False) -> bool:
        """Type text character by character — visible on screen."""
        pag = self._ensure_pyautogui()
        if not pag:
            return False
        try:
            pag.typewrite(text, interval=interval) if text.isascii() else pag.write(text, interval=interval)
            self._log_action(BodyAction(
                action_type="keyboard_type",
                description=f"Typed: {text[:60]}{'...' if len(text) > 60 else ''}",
                result=f"Typed {len(text)} characters",
                success=True, autonomous=autonomous, reason=reason
            ))
            logger.info(f"⌨️ Typed: {text[:40]}... | {reason}")
            return True
        except Exception as e:
            # Fallback for non-ASCII text
            try:
                import pyperclip
                pyperclip.copy(text)
                pag.hotkey('ctrl', 'v')
                self._log_action(BodyAction(
                    action_type="keyboard_type",
                    description=f"Pasted: {text[:60]}",
                    result=f"Pasted {len(text)} characters via clipboard",
                    success=True, autonomous=autonomous, reason=reason
                ))
                return True
            except Exception as e2:
                logger.error(f"Type text error: {e}, fallback error: {e2}")
                return False
    
    def press_key(self, key: str, reason: str = "",
                  autonomous: bool = False) -> bool:
        """Press a single key (enter, tab, escape, space, etc.)."""
        pag = self._ensure_pyautogui()
        if not pag:
            return False
        try:
            pag.press(key)
            self._log_action(BodyAction(
                action_type="keyboard_press",
                description=f"Pressed key: {key}",
                result=f"Key pressed: {key}",
                success=True, autonomous=autonomous, reason=reason
            ))
            logger.info(f"⌨️ Pressed: {key} | {reason}")
            return True
        except Exception as e:
            logger.error(f"Key press error: {e}")
            return False
    
    def hotkey(self, *keys, reason: str = "",
              autonomous: bool = False) -> bool:
        """Press a keyboard shortcut (e.g., hotkey('ctrl', 'c'))."""
        pag = self._ensure_pyautogui()
        if not pag:
            return False
        try:
            pag.hotkey(*keys)
            combo = "+".join(keys)
            self._log_action(BodyAction(
                action_type="keyboard_hotkey",
                description=f"Hotkey: {combo}",
                result=f"Pressed shortcut: {combo}",
                success=True, autonomous=autonomous, reason=reason
            ))
            logger.info(f"⌨️ Hotkey: {combo} | {reason}")
            return True
        except Exception as e:
            logger.error(f"Hotkey error: {e}")
            return False
    
    def scroll(self, amount: int = 3, x: int = None, y: int = None,
               reason: str = "", autonomous: bool = False) -> bool:
        """Scroll the mouse wheel. Positive = up, negative = down."""
        pag = self._ensure_pyautogui()
        if not pag:
            return False
        try:
            if x is not None and y is not None:
                pag.scroll(amount, x, y)
            else:
                pag.scroll(amount)
            direction = "up" if amount > 0 else "down"
            self._log_action(BodyAction(
                action_type="mouse_scroll",
                description=f"Scrolled {direction} by {abs(amount)}",
                result=f"Scrolled {direction}",
                success=True, autonomous=autonomous, reason=reason
            ))
            return True
        except Exception as e:
            logger.error(f"Scroll error: {e}")
            return False
    
    def drag_to(self, x: int, y: int, duration: float = 0.5,
                button: str = "left",
                reason: str = "", autonomous: bool = False) -> bool:
        """Drag from current position to (x, y)."""
        pag = self._ensure_pyautogui()
        if not pag:
            return False
        try:
            start = pag.position()
            pag.dragTo(x, y, duration=duration, button=button)
            self._log_action(BodyAction(
                action_type="mouse_drag",
                description=f"Dragged from {start} to ({x}, {y})",
                result=f"Drag complete",
                success=True, autonomous=autonomous, reason=reason
            ))
            logger.info(f"🖱️ Dragged to ({x}, {y}) | {reason}")
            return True
        except Exception as e:
            logger.error(f"Drag error: {e}")
            return False
    
    def take_screenshot(self, save_path: str = None,
                        reason: str = "") -> Optional[str]:
        """Take a screenshot. Returns the file path where it was saved."""
        pag = self._ensure_pyautogui()
        if not pag:
            return None
        try:
            if not save_path:
                screenshots_dir = DATA_DIR / "screenshots"
                screenshots_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = str(screenshots_dir / f"screen_{timestamp}.png")
            
            screenshot = pag.screenshot()
            screenshot.save(save_path)
            
            self._log_action(BodyAction(
                action_type="screenshot",
                description=f"Screenshot saved: {save_path}",
                result=f"Screenshot: {save_path}",
                success=True, reason=reason
            ))
            logger.info(f"📸 Screenshot: {save_path} | {reason}")
            return save_path
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            return None
    
    def get_screen_size(self) -> Tuple[int, int]:
        """Get screen resolution."""
        pag = self._ensure_pyautogui()
        if pag:
            return pag.size()
        return (1920, 1080)  # Fallback
    
    def get_mouse_position(self) -> Tuple[int, int]:
        """Get current mouse cursor position."""
        pag = self._ensure_pyautogui()
        if pag:
            return pag.position()
        return (0, 0)
    
    def locate_on_screen(self, image_path: str, confidence: float = 0.8) -> Optional[Tuple[int, int]]:
        """Find an image on screen and return its center coordinates."""
        pag = self._ensure_pyautogui()
        if not pag:
            return None
        try:
            location = pag.locateOnScreen(image_path, confidence=confidence)
            if location:
                center = pag.center(location)
                return (center.x, center.y)
            return None
        except Exception as e:
            logger.debug(f"Image locate failed: {e}")
            return None
    
    def get_pixel_color(self, x: int, y: int) -> Optional[Tuple[int, int, int]]:
        """Get the RGB color of a pixel at (x, y)."""
        pag = self._ensure_pyautogui()
        if not pag:
            return None
        try:
            return pag.pixel(x, y)
        except Exception:
            return None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # AUTONOMOUS BODY ACTIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def auto_optimize(self, reason: str = "Autonomous optimization") -> Dict[str, Any]:
        """Autonomously optimize system resources"""
        results = {"actions": [], "success": True}
        
        vitals = self.get_vitals(force_refresh=True)
        
        # High RAM: suggest garbage collection
        if vitals.ram_percent > 85:
            import gc
            gc.collect()
            results["actions"].append("Ran garbage collection (high RAM)")
        
        # High disk: find large temp files
        if vitals.disk_percent > 90:
            if self._is_windows:
                self.execute_command(
                    'del /q/f/s "%TEMP%\\*" 2>nul',
                    reason="Clean temp files (disk >90%)",
                    autonomous=True
                )
                results["actions"].append("Cleaned temp files")
        
        # Log the optimization
        self._log_action(BodyAction(
            action_type="optimization",
            description="Auto-optimization run",
            result=json.dumps(results),
            success=True,
            autonomous=True,
            reason=reason
        ))
        
        return results
    
    # ═══════════════════════════════════════════════════════════════════════════
    # UTILITY METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _human_size(self, size_bytes: int) -> str:
        """Convert bytes to human-readable size"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def _log_action(self, action: BodyAction):
        """Log a body action"""
        import uuid
        if not action.action_id:
            action.action_id = str(uuid.uuid4())
        
        self._action_log.append(action)
        if len(self._action_log) > self._max_action_log:
            self._action_log.pop(0)
        
        # Store significant actions in memory
        if action.autonomous:
            self._memory.remember(
                f"Autonomous action: {action.description}. Result: {action.result[:200]}",
                MemoryType.EPISODIC,
                importance=0.5,
                tags=["body_action", action.action_type, "autonomous"],
                source="computer_body"
            )
    
    def get_action_log(self, limit: int = 20) -> List[Dict]:
        """Get recent action log"""
        return [a.to_dict() for a in self._action_log[-limit:]]
    
    def _save_action_log(self):
        """Save action log to disk"""
        try:
            filepath = DATA_DIR / "body_actions.json"
            data = [a.to_dict() for a in self._action_log[-100:]]
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving action log: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BACKGROUND MONITORING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _body_monitor_loop(self):
        """Continuously monitor body state"""
        logger.info("Body monitoring loop started")
        
        while self._running:
            try:
                vitals = self.get_vitals(force_refresh=True)
                
                # Update state manager
                self._state.update_body(
                    cpu_usage=vitals.cpu_percent,
                    memory_usage=vitals.ram_percent,
                    disk_usage=vitals.disk_percent,
                    active_processes=vitals.process_count,
                    health_score=vitals.health_score,
                    uptime=vitals.uptime_hours,
                    last_health_check=datetime.now()
                )
                
                if vitals.temperature:
                    self._state.update_body(temperature=vitals.temperature)
                
                # Publish resource change event
                publish(
                    EventType.SYSTEM_RESOURCE_CHANGE,
                    {
                        "cpu_usage": vitals.cpu_percent,
                        "memory_usage": vitals.ram_percent,
                        "disk_usage": vitals.disk_percent,
                        "health": vitals.health_score,
                        "temperature": vitals.temperature,
                        "process_count": vitals.process_count
                    },
                    source="computer_body"
                )
                
                # Warning events
                if vitals.health_score < 0.3:
                    publish(
                        EventType.SYSTEM_WARNING,
                        {"message": "Body health critical!", "health": vitals.health_score},
                        source="computer_body"
                    )
                
                time.sleep(self._monitor_interval)
                
            except Exception as e:
                logger.error(f"Body monitoring error: {e}")
                time.sleep(10)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STATS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_stats(self) -> Dict[str, Any]:
        vitals = self.get_vitals()
        return {
            "system": self._system_info.to_dict(),
            "vitals": vitals.to_dict(),
            "description": self.get_vitals_description(),
            "actions_logged": len(self._action_log),
            "autonomous_actions": sum(1 for a in self._action_log if a.autonomous)
        }

# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

computer_body = ComputerBody()