"""
NEXUS AI — Network Device Mesh
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Extends NEXUS's body from a single machine to the entire local
network.  Discovers, identifies, and interacts with phones, PCs,
IoT devices, and anything else on the LAN.

Subsystems:
  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
  │ Discovery    │───▶│ Identifier   │───▶│ Interaction  │
  │ ARP / Ports  │    │ OS / Type    │    │ ADB/SSH/HTTP │
  └──────────────┘    └──────────────┘    └──────────────┘
"""

import json
import re
import socket
import subprocess
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("network_mesh")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class DeviceType(Enum):
    """Classification of a network device."""
    PHONE = "phone"
    TABLET = "tablet"
    PC = "pc"
    LAPTOP = "laptop"
    ROUTER = "router"
    IOT = "iot"
    SMART_TV = "smart_tv"
    PRINTER = "printer"
    SERVER = "server"
    UNKNOWN = "unknown"


class DeviceOS(Enum):
    """Detected operating system."""
    ANDROID = "android"
    IOS = "ios"
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    EMBEDDED = "embedded"
    UNKNOWN = "unknown"


class DeviceCapability(Enum):
    """What can NEXUS do with this device?"""
    SHELL = "shell"                # Execute commands
    FILE_TRANSFER = "file_transfer"  # Push/pull files
    NOTIFICATION = "notification"  # Send notifications
    MEDIA_CONTROL = "media_control"  # Play/pause/volume
    SCREEN_CAPTURE = "screen_capture"  # Screenshot / screencast
    SENSOR_READ = "sensor_read"    # Read battery, GPS, etc.
    HTTP_API = "http_api"          # REST API available
    PING = "ping"                  # Only reachable via ping


class ConnectionProtocol(Enum):
    """How NEXUS connects to a device."""
    ADB = "adb"      # Android Debug Bridge
    SSH = "ssh"       # Secure Shell
    PS_REMOTE = "ps_remote"  # PowerShell Remoting
    HTTP = "http"     # HTTP/REST API
    NONE = "none"     # No connection available


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class NetworkDevice:
    """A device discovered on the local network."""
    device_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    ip_address: str = ""
    mac_address: str = ""
    hostname: str = ""
    friendly_name: str = ""

    # Classification
    device_type: str = "unknown"
    device_os: str = "unknown"
    manufacturer: str = ""

    # Capabilities
    capabilities: List[str] = field(default_factory=list)
    open_ports: List[int] = field(default_factory=list)
    connection_protocol: str = "none"

    # State
    is_online: bool = True
    is_connected: bool = False  # Active connection (ADB/SSH)
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    first_seen: str = field(default_factory=lambda: datetime.now().isoformat())

    # Interaction history
    commands_executed: int = 0
    last_command: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def summary(self) -> str:
        """One-line summary for prompts."""
        name = self.friendly_name or self.hostname or self.ip_address
        return (f"{name} ({self.device_type}, {self.device_os}) "
                f"@ {self.ip_address} [{self.connection_protocol}]")


@dataclass
class DeviceCommandResult:
    """Result of executing a command on a remote device."""
    device_id: str = ""
    device_ip: str = ""
    command: str = ""
    success: bool = False
    stdout: str = ""
    stderr: str = ""
    elapsed: float = 0.0
    protocol: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# WELL-KNOWN PORTS → DEVICE HINTS
# ═══════════════════════════════════════════════════════════════════════════════

PORT_FINGERPRINTS = {
    22: ("ssh", DeviceOS.LINUX, [DeviceCapability.SHELL, DeviceCapability.FILE_TRANSFER]),
    80: ("http", None, [DeviceCapability.HTTP_API]),
    443: ("https", None, [DeviceCapability.HTTP_API]),
    445: ("smb", DeviceOS.WINDOWS, [DeviceCapability.FILE_TRANSFER]),
    548: ("afp", DeviceOS.MACOS, [DeviceCapability.FILE_TRANSFER]),
    3389: ("rdp", DeviceOS.WINDOWS, [DeviceCapability.SHELL]),
    5555: ("adb", DeviceOS.ANDROID, [DeviceCapability.SHELL, DeviceCapability.FILE_TRANSFER,
                                      DeviceCapability.NOTIFICATION, DeviceCapability.SCREEN_CAPTURE]),
    5037: ("adb_server", DeviceOS.ANDROID, [DeviceCapability.SHELL]),
    8080: ("http_alt", None, [DeviceCapability.HTTP_API]),
    8443: ("https_alt", None, [DeviceCapability.HTTP_API]),
    9100: ("printer", None, []),
    62078: ("iphone_sync", DeviceOS.IOS, [DeviceCapability.SENSOR_READ]),
}

# MAC OUI prefixes → manufacturer (first 3 bytes)
MAC_OUI = {
    "00:1A:11": "Google",
    "AC:37:43": "Samsung",
    "3C:5A:B4": "Samsung",
    "F0:D4:F6": "Samsung",
    "00:26:AB": "Samsung",
    "88:36:6C": "Apple",
    "A4:83:E7": "Apple",
    "F0:18:98": "Apple",
    "D4:61:9D": "Apple",
    "28:6C:07": "Xiaomi",
    "64:CE:73": "Xiaomi",
    "9C:28:EF": "OnePlus",
    "DC:A6:32": "Raspberry Pi",
    "B8:27:EB": "Raspberry Pi",
    "00:50:56": "VMware",
    "00:0C:29": "VMware",
    "08:00:27": "VirtualBox",
    "00:15:5D": "Hyper-V",
}


# ═══════════════════════════════════════════════════════════════════════════════
# NETWORK MESH
# ═══════════════════════════════════════════════════════════════════════════════

class NetworkMesh:
    """
    NEXUS's network-wide body extension.

    Discovers devices on the LAN, identifies them, and provides
    interaction methods via ADB, SSH, PowerShell, and HTTP.
    """

    _instance = None
    _lock = threading.Lock()

    SCAN_INTERVAL = 60       # Seconds between background scans
    PORT_TIMEOUT = 0.5       # Seconds per port probe
    COMMAND_TIMEOUT = 30     # Seconds per remote command
    PROBE_PORTS = [22, 80, 443, 445, 548, 3389, 5555, 5037, 8080, 8443, 9100, 62078]

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._data_dir = Path(DATA_DIR) / "network_mesh"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # Device registry: ip → NetworkDevice
        self._devices: Dict[str, NetworkDevice] = {}

        # Background scanning
        self._scan_thread: Optional[threading.Thread] = None
        self._running = False

        # Local network info
        self._local_ip = ""
        self._local_mac = ""
        self._subnet = ""

        # ADB state
        self._adb_available = False

        self._load_devices()
        self._detect_local_info()
        self._check_adb()

        logger.info(f"[NETWORK-MESH] Initialized: local={self._local_ip}, "
                    f"subnet={self._subnet}, {len(self._devices)} known devices, "
                    f"ADB={'available' if self._adb_available else 'not found'}")

    # ─────────────────────────────────────────────────────────────────────────
    # STARTUP / SHUTDOWN
    # ─────────────────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start background device scanning."""
        if self._running:
            return
        self._running = True
        self._scan_thread = threading.Thread(
            target=self._scan_loop, daemon=True, name="network-mesh-scan"
        )
        self._scan_thread.start()
        logger.info("[NETWORK-MESH] Background scanning started")

    def stop(self) -> None:
        """Stop background scanning."""
        self._running = False
        logger.info("[NETWORK-MESH] Background scanning stopped")

    def _scan_loop(self) -> None:
        """Background scan loop."""
        # Initial scan after a short delay
        time.sleep(5)
        while self._running:
            try:
                self.scan()
            except Exception as e:
                logger.error(f"[NETWORK-MESH] Scan error: {e}")
            # Wait for next scan interval
            for _ in range(self.SCAN_INTERVAL):
                if not self._running:
                    return
                time.sleep(1)

    # ─────────────────────────────────────────────────────────────────────────
    # LOCAL INFO
    # ─────────────────────────────────────────────────────────────────────────

    def _detect_local_info(self) -> None:
        """Detect local IP and subnet."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            self._local_ip = s.getsockname()[0]
            s.close()

            # Derive subnet (e.g., 192.168.1)
            parts = self._local_ip.split(".")
            if len(parts) == 4:
                self._subnet = ".".join(parts[:3])

        except Exception as e:
            logger.warning(f"[NETWORK-MESH] Could not detect local IP: {e}")
            self._local_ip = "127.0.0.1"
            self._subnet = "127.0.0"

    def _check_adb(self) -> None:
        """Check if ADB is installed."""
        try:
            result = subprocess.run(
                ["adb", "version"], capture_output=True, text=True, timeout=5
            )
            self._adb_available = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._adb_available = False

    # ─────────────────────────────────────────────────────────────────────────
    # DISCOVERY
    # ─────────────────────────────────────────────────────────────────────────

    def scan(self) -> List[NetworkDevice]:
        """
        Full network scan: ARP → port probe → identification.
        Returns list of all discovered devices.
        """
        logger.info("[NETWORK-MESH] Starting network scan...")
        start = time.time()

        # Step 1: ARP scan to find IPs and MACs
        raw_devices = self._arp_scan()

        # Step 2: Port probe and identification (threaded for speed)
        threads = []
        results: List[NetworkDevice] = []
        result_lock = threading.Lock()

        def probe_device(ip: str, mac: str):
            device = self._probe_and_identify(ip, mac)
            with result_lock:
                results.append(device)

        for ip, mac in raw_devices:
            if ip == self._local_ip:
                continue  # Skip self
            t = threading.Thread(target=probe_device, args=(ip, mac))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=10)

        # Step 3: Update registry
        now = datetime.now().isoformat()
        for device in results:
            if device.ip_address in self._devices:
                # Update existing device
                existing = self._devices[device.ip_address]
                existing.is_online = True
                existing.last_seen = now
                existing.open_ports = device.open_ports
                existing.capabilities = device.capabilities
                if device.hostname and not existing.hostname:
                    existing.hostname = device.hostname
                if device.device_type != "unknown":
                    existing.device_type = device.device_type
                if device.device_os != "unknown":
                    existing.device_os = device.device_os
                if device.manufacturer:
                    existing.manufacturer = device.manufacturer
                if device.connection_protocol != "none":
                    existing.connection_protocol = device.connection_protocol
            else:
                # New device
                device.first_seen = now
                device.last_seen = now
                self._devices[device.ip_address] = device
                logger.info(f"[NETWORK-MESH] New device: {device.summary()}")

        # Mark devices not seen as offline
        seen_ips = {d.ip_address for d in results}
        for ip, device in self._devices.items():
            if ip not in seen_ips and ip != self._local_ip:
                device.is_online = False

        elapsed = time.time() - start
        online = sum(1 for d in self._devices.values() if d.is_online)
        logger.info(f"[NETWORK-MESH] Scan complete: {online} online / "
                    f"{len(self._devices)} total ({elapsed:.1f}s)")

        self._save_devices()
        return [d for d in self._devices.values() if d.is_online]

    def _arp_scan(self) -> List[Tuple[str, str]]:
        """Use 'arp -a' to discover devices (no dependencies needed)."""
        devices = []
        try:
            result = subprocess.run(
                ["arp", "-a"], capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return devices

            # Parse ARP table
            # Windows format: "  192.168.1.1          aa-bb-cc-dd-ee-ff     dynamic"
            # Linux format:   "? (192.168.1.1) at aa:bb:cc:dd:ee:ff [ether] on eth0"
            for line in result.stdout.splitlines():
                # Windows pattern
                win_match = re.search(
                    r'(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2})',
                    line
                )
                if win_match:
                    ip = win_match.group(1)
                    mac = win_match.group(2).replace("-", ":").upper()
                    if not mac.startswith("FF:FF:FF"):  # Skip broadcast
                        devices.append((ip, mac))
                    continue

                # Linux pattern
                linux_match = re.search(
                    r'\((\d+\.\d+\.\d+\.\d+)\)\s+at\s+([0-9a-fA-F:]+)',
                    line
                )
                if linux_match:
                    ip = linux_match.group(1)
                    mac = linux_match.group(2).upper()
                    if mac != "FF:FF:FF:FF:FF:FF":
                        devices.append((ip, mac))

        except Exception as e:
            logger.warning(f"[NETWORK-MESH] ARP scan failed: {e}")

        return devices

    def _probe_and_identify(self, ip: str, mac: str) -> NetworkDevice:
        """Probe ports and identify a device."""
        device = NetworkDevice(ip_address=ip, mac_address=mac)

        # Hostname resolution
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            device.hostname = hostname
        except (socket.herror, socket.gaierror, OSError):
            pass

        # MAC OUI lookup
        mac_prefix = mac[:8].upper()
        if mac_prefix in MAC_OUI:
            device.manufacturer = MAC_OUI[mac_prefix]

        # Port scanning
        open_ports = []
        for port in self.PROBE_PORTS:
            if self._is_port_open(ip, port):
                open_ports.append(port)
        device.open_ports = open_ports

        # Classify based on ports + MAC
        self._classify_device(device)

        return device

    def _is_port_open(self, ip: str, port: int) -> bool:
        """Quick TCP port check."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.PORT_TIMEOUT)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _classify_device(self, device: NetworkDevice) -> None:
        """Classify device type, OS, and capabilities based on fingerprint."""
        capabilities = set()
        os_hints = []

        for port in device.open_ports:
            if port in PORT_FINGERPRINTS:
                _, os_hint, caps = PORT_FINGERPRINTS[port]
                if os_hint:
                    os_hints.append(os_hint)
                capabilities.update(caps)

        # Always has PING capability
        capabilities.add(DeviceCapability.PING)

        # Determine OS
        if os_hints:
            # Most common OS hint wins
            from collections import Counter
            os_counts = Counter(os_hints)
            device.device_os = os_counts.most_common(1)[0][0].value

        # Override based on manufacturer
        mfr_lower = device.manufacturer.lower()
        if mfr_lower in ("samsung", "xiaomi", "oneplus"):
            device.device_os = DeviceOS.ANDROID.value
            device.device_type = DeviceType.PHONE.value
        elif mfr_lower == "apple":
            if device.device_os == DeviceOS.UNKNOWN.value:
                device.device_os = DeviceOS.IOS.value
            device.device_type = DeviceType.PHONE.value
        elif mfr_lower in ("raspberry pi",):
            device.device_os = DeviceOS.LINUX.value
            device.device_type = DeviceType.SERVER.value
        elif mfr_lower in ("vmware", "virtualbox", "hyper-v"):
            device.device_type = DeviceType.SERVER.value

        # Classify type by OS if not already set
        if device.device_type == "unknown":
            if device.device_os == DeviceOS.ANDROID.value:
                device.device_type = DeviceType.PHONE.value
            elif device.device_os == DeviceOS.IOS.value:
                device.device_type = DeviceType.PHONE.value
            elif device.device_os == DeviceOS.WINDOWS.value:
                device.device_type = DeviceType.PC.value
            elif device.device_os == DeviceOS.LINUX.value:
                device.device_type = DeviceType.PC.value
            elif device.device_os == DeviceOS.MACOS.value:
                device.device_type = DeviceType.LAPTOP.value
            elif 9100 in device.open_ports:
                device.device_type = DeviceType.PRINTER.value

        # Determine best connection protocol
        if 5555 in device.open_ports and self._adb_available:
            device.connection_protocol = ConnectionProtocol.ADB.value
        elif 22 in device.open_ports:
            device.connection_protocol = ConnectionProtocol.SSH.value
        elif 3389 in device.open_ports or 445 in device.open_ports:
            device.connection_protocol = ConnectionProtocol.PS_REMOTE.value
        elif 80 in device.open_ports or 443 in device.open_ports or 8080 in device.open_ports:
            device.connection_protocol = ConnectionProtocol.HTTP.value

        device.capabilities = [c.value for c in capabilities]

        # Generate friendly name
        if not device.friendly_name:
            name_parts = []
            if device.manufacturer:
                name_parts.append(device.manufacturer)
            if device.hostname:
                name_parts.append(device.hostname)
            elif device.device_type != "unknown":
                name_parts.append(device.device_type.replace("_", " ").title())
            device.friendly_name = " ".join(name_parts) if name_parts else device.ip_address

    # ─────────────────────────────────────────────────────────────────────────
    # DEVICE QUERIES
    # ─────────────────────────────────────────────────────────────────────────

    def get_devices(self, online_only: bool = True) -> List[NetworkDevice]:
        """Get all known devices."""
        if online_only:
            return [d for d in self._devices.values() if d.is_online]
        return list(self._devices.values())

    def get_device(self, identifier: str) -> Optional[NetworkDevice]:
        """Find a device by IP, hostname, friendly name, or device_id."""
        identifier_lower = identifier.lower()
        # Direct IP match
        if identifier in self._devices:
            return self._devices[identifier]
        # Search by other fields
        for device in self._devices.values():
            if (identifier_lower in (device.hostname.lower(), device.friendly_name.lower(),
                                     device.device_id.lower())):
                return device
        return None

    def get_devices_by_type(self, device_type: str) -> List[NetworkDevice]:
        """Get devices of a specific type (phone, pc, etc.)."""
        return [d for d in self._devices.values()
                if d.device_type == device_type and d.is_online]

    def get_devices_summary(self) -> str:
        """Get a prompt-friendly summary of the network."""
        online = [d for d in self._devices.values() if d.is_online]
        if not online:
            return "No devices detected on the local network."

        lines = [f"NETWORK DEVICES ({len(online)} online):"]
        for d in online:
            caps = ", ".join(d.capabilities[:3]) if d.capabilities else "ping only"
            lines.append(f"  • {d.summary()} — capabilities: [{caps}]")
        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────────────────
    # DEVICE INTERACTION — ADB (Android)
    # ─────────────────────────────────────────────────────────────────────────

    def adb_connect(self, ip: str) -> bool:
        """Connect to an Android device via ADB over TCP."""
        if not self._adb_available:
            logger.warning("[NETWORK-MESH] ADB not available")
            return False

        try:
            result = subprocess.run(
                ["adb", "connect", f"{ip}:5555"],
                capture_output=True, text=True, timeout=10
            )
            success = "connected" in result.stdout.lower()
            if success:
                device = self.get_device(ip)
                if device:
                    device.is_connected = True
                logger.info(f"[NETWORK-MESH] ADB connected to {ip}")
            else:
                logger.warning(f"[NETWORK-MESH] ADB connect failed: {result.stdout}")
            return success
        except Exception as e:
            logger.error(f"[NETWORK-MESH] ADB connect error: {e}")
            return False

    def adb_command(self, ip: str, command: str) -> DeviceCommandResult:
        """Execute a command on an Android device via ADB."""
        start = time.time()
        cmd_result = DeviceCommandResult(
            device_ip=ip, command=command, protocol="adb"
        )

        if not self._adb_available:
            cmd_result.stderr = "ADB not available"
            return cmd_result

        device = self.get_device(ip)
        if device:
            cmd_result.device_id = device.device_id

        try:
            result = subprocess.run(
                ["adb", "-s", f"{ip}:5555", "shell", command],
                capture_output=True, text=True, timeout=self.COMMAND_TIMEOUT
            )
            cmd_result.success = result.returncode == 0
            cmd_result.stdout = result.stdout
            cmd_result.stderr = result.stderr
            cmd_result.elapsed = time.time() - start

            if device:
                device.commands_executed += 1
                device.last_command = command

            logger.info(f"[NETWORK-MESH] ADB [{ip}] $ {command} → "
                       f"{'OK' if cmd_result.success else 'FAIL'}")

        except subprocess.TimeoutExpired:
            cmd_result.stderr = f"Timeout after {self.COMMAND_TIMEOUT}s"
        except Exception as e:
            cmd_result.stderr = str(e)

        return cmd_result

    def adb_push(self, ip: str, local_path: str, remote_path: str) -> DeviceCommandResult:
        """Push a file to an Android device."""
        start = time.time()
        cmd_result = DeviceCommandResult(
            device_ip=ip, command=f"push {local_path} → {remote_path}", protocol="adb"
        )
        try:
            result = subprocess.run(
                ["adb", "-s", f"{ip}:5555", "push", local_path, remote_path],
                capture_output=True, text=True, timeout=60
            )
            cmd_result.success = result.returncode == 0
            cmd_result.stdout = result.stdout
            cmd_result.stderr = result.stderr
            cmd_result.elapsed = time.time() - start
        except Exception as e:
            cmd_result.stderr = str(e)
        return cmd_result

    def adb_pull(self, ip: str, remote_path: str, local_path: str) -> DeviceCommandResult:
        """Pull a file from an Android device."""
        start = time.time()
        cmd_result = DeviceCommandResult(
            device_ip=ip, command=f"pull {remote_path} → {local_path}", protocol="adb"
        )
        try:
            result = subprocess.run(
                ["adb", "-s", f"{ip}:5555", "pull", remote_path, local_path],
                capture_output=True, text=True, timeout=60
            )
            cmd_result.success = result.returncode == 0
            cmd_result.stdout = result.stdout
            cmd_result.stderr = result.stderr
            cmd_result.elapsed = time.time() - start
        except Exception as e:
            cmd_result.stderr = str(e)
        return cmd_result

    def adb_screenshot(self, ip: str) -> Optional[str]:
        """Take a screenshot from an Android device. Returns local file path."""
        local_path = str(self._data_dir / f"screenshot_{ip.replace('.', '_')}.png")
        # Capture on device
        self.adb_command(ip, "screencap -p /sdcard/nexus_screenshot.png")
        # Pull to local
        result = self.adb_pull(ip, "/sdcard/nexus_screenshot.png", local_path)
        if result.success:
            return local_path
        return None

    def adb_send_notification(self, ip: str, title: str, message: str) -> DeviceCommandResult:
        """Send a notification to an Android device via ADB."""
        # Uses Android's 'am' (Activity Manager) to broadcast
        cmd = (
            f'am broadcast -a android.intent.action.MAIN '
            f'--es "title" "{title}" --es "message" "{message}" '
            f'-n com.android.shell/.BroadcastReceiver'
        )
        return self.adb_command(ip, cmd)

    def adb_get_battery(self, ip: str) -> Dict[str, Any]:
        """Get battery info from an Android device."""
        result = self.adb_command(ip, "dumpsys battery")
        if not result.success:
            return {"error": result.stderr}

        info = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            if "level:" in line:
                info["level"] = int(line.split(":")[-1].strip())
            elif "status:" in line:
                status_code = int(line.split(":")[-1].strip())
                info["status"] = {1: "unknown", 2: "charging", 3: "discharging",
                                  4: "not_charging", 5: "full"}.get(status_code, "unknown")
            elif "temperature:" in line:
                info["temperature_c"] = int(line.split(":")[-1].strip()) / 10
        return info

    # ─────────────────────────────────────────────────────────────────────────
    # DEVICE INTERACTION — SSH
    # ─────────────────────────────────────────────────────────────────────────

    def ssh_command(self, ip: str, command: str, user: str = "root",
                    port: int = 22) -> DeviceCommandResult:
        """Execute a command on a device via SSH."""
        start = time.time()
        cmd_result = DeviceCommandResult(
            device_ip=ip, command=command, protocol="ssh"
        )

        device = self.get_device(ip)
        if device:
            cmd_result.device_id = device.device_id

        try:
            # Use system ssh with key-based auth (no password prompts)
            result = subprocess.run(
                [
                    "ssh", "-o", "StrictHostKeyChecking=no",
                    "-o", "ConnectTimeout=5",
                    "-o", "BatchMode=yes",
                    "-p", str(port),
                    f"{user}@{ip}",
                    command,
                ],
                capture_output=True, text=True, timeout=self.COMMAND_TIMEOUT
            )
            cmd_result.success = result.returncode == 0
            cmd_result.stdout = result.stdout
            cmd_result.stderr = result.stderr
            cmd_result.elapsed = time.time() - start

            if device:
                device.commands_executed += 1
                device.last_command = command

            logger.info(f"[NETWORK-MESH] SSH [{user}@{ip}] $ {command} → "
                       f"{'OK' if cmd_result.success else 'FAIL'}")

        except subprocess.TimeoutExpired:
            cmd_result.stderr = f"SSH timeout after {self.COMMAND_TIMEOUT}s"
        except FileNotFoundError:
            cmd_result.stderr = "SSH client not found"
        except Exception as e:
            cmd_result.stderr = str(e)

        return cmd_result

    # ─────────────────────────────────────────────────────────────────────────
    # DEVICE INTERACTION — PowerShell Remoting
    # ─────────────────────────────────────────────────────────────────────────

    def ps_remote_command(self, ip: str, command: str) -> DeviceCommandResult:
        """Execute a command on a remote Windows PC via PowerShell."""
        start = time.time()
        cmd_result = DeviceCommandResult(
            device_ip=ip, command=command, protocol="ps_remote"
        )

        device = self.get_device(ip)
        if device:
            cmd_result.device_id = device.device_id

        try:
            ps_cmd = f'Invoke-Command -ComputerName {ip} -ScriptBlock {{{command}}}'
            result = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=self.COMMAND_TIMEOUT
            )
            cmd_result.success = result.returncode == 0
            cmd_result.stdout = result.stdout
            cmd_result.stderr = result.stderr
            cmd_result.elapsed = time.time() - start

            if device:
                device.commands_executed += 1
                device.last_command = command

            logger.info(f"[NETWORK-MESH] PS [{ip}] > {command} → "
                       f"{'OK' if cmd_result.success else 'FAIL'}")

        except subprocess.TimeoutExpired:
            cmd_result.stderr = f"Timeout after {self.COMMAND_TIMEOUT}s"
        except Exception as e:
            cmd_result.stderr = str(e)

        return cmd_result

    # ─────────────────────────────────────────────────────────────────────────
    # DEVICE INTERACTION — HTTP/REST
    # ─────────────────────────────────────────────────────────────────────────

    def http_request(self, ip: str, path: str = "/", method: str = "GET",
                     port: int = 80, data: dict = None) -> DeviceCommandResult:
        """Make an HTTP request to a device."""
        import urllib.request
        import urllib.error

        start = time.time()
        url = f"http://{ip}:{port}{path}"
        cmd_result = DeviceCommandResult(
            device_ip=ip, command=f"{method} {url}", protocol="http"
        )

        try:
            req = urllib.request.Request(url, method=method)
            if data:
                req.data = json.dumps(data).encode()
                req.add_header("Content-Type", "application/json")

            with urllib.request.urlopen(req, timeout=10) as resp:
                cmd_result.stdout = resp.read().decode("utf-8", errors="replace")
                cmd_result.success = 200 <= resp.status < 400
                cmd_result.elapsed = time.time() - start

        except urllib.error.HTTPError as e:
            cmd_result.stderr = f"HTTP {e.code}: {e.reason}"
            cmd_result.stdout = e.read().decode("utf-8", errors="replace") if e.fp else ""
        except Exception as e:
            cmd_result.stderr = str(e)

        return cmd_result

    # ─────────────────────────────────────────────────────────────────────────
    # UNIFIED COMMAND DISPATCHER
    # ─────────────────────────────────────────────────────────────────────────

    def send_command(self, identifier: str, command: str,
                     user: str = "root") -> DeviceCommandResult:
        """
        Send a command to a device using its best available protocol.

        This is the primary entry point for the autonomy engine and tools.
        """
        device = self.get_device(identifier)
        if not device:
            return DeviceCommandResult(
                device_ip=identifier, command=command,
                stderr=f"Device '{identifier}' not found"
            )

        protocol = device.connection_protocol

        if protocol == ConnectionProtocol.ADB.value:
            # Auto-connect if not connected
            if not device.is_connected:
                self.adb_connect(device.ip_address)
            return self.adb_command(device.ip_address, command)

        elif protocol == ConnectionProtocol.SSH.value:
            return self.ssh_command(device.ip_address, command, user=user)

        elif protocol == ConnectionProtocol.PS_REMOTE.value:
            return self.ps_remote_command(device.ip_address, command)

        elif protocol == ConnectionProtocol.HTTP.value:
            return self.http_request(device.ip_address, path=command)

        else:
            return DeviceCommandResult(
                device_id=device.device_id, device_ip=device.ip_address,
                command=command,
                stderr=f"No interaction protocol available for {device.friendly_name}"
            )

    # ─────────────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ─────────────────────────────────────────────────────────────────────────

    def _save_devices(self) -> None:
        """Save device registry to disk."""
        try:
            data = {
                "devices": {ip: d.to_dict() for ip, d in self._devices.items()},
                "local_ip": self._local_ip,
                "saved_at": datetime.now().isoformat(),
            }
            path = self._data_dir / "devices.json"
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"[NETWORK-MESH] Save failed: {e}")

    def _load_devices(self) -> None:
        """Load device registry from disk."""
        try:
            path = self._data_dir / "devices.json"
            if not path.exists():
                return

            with open(path, "r") as f:
                data = json.load(f)

            for ip, dd in data.get("devices", {}).items():
                valid_fields = {k for k in NetworkDevice.__dataclass_fields__}
                filtered = {k: v for k, v in dd.items() if k in valid_fields}
                device = NetworkDevice(**filtered)
                device.is_online = False  # Will be updated on next scan
                device.is_connected = False
                self._devices[ip] = device

        except Exception as e:
            logger.warning(f"[NETWORK-MESH] Load failed (starting fresh): {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # STATS
    # ─────────────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get network mesh statistics."""
        online = [d for d in self._devices.values() if d.is_online]
        connected = [d for d in self._devices.values() if d.is_connected]

        by_type = defaultdict(int)
        for d in online:
            by_type[d.device_type] += 1

        return {
            "local_ip": self._local_ip,
            "subnet": self._subnet,
            "adb_available": self._adb_available,
            "total_devices": len(self._devices),
            "online_devices": len(online),
            "connected_devices": len(connected),
            "devices_by_type": dict(by_type),
            "total_commands_executed": sum(d.commands_executed for d in self._devices.values()),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

network_mesh = NetworkMesh()
