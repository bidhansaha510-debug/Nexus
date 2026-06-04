"""
NEXUS AI — Device Context Manager
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Detects and profiles every device that connects to NEXUS — Android phones,
web browsers on other PCs, the desktop GUI, etc.

NEXUS uses this context to:
  • Know which device the user is talking from
  • Tailor responses (brief on mobile, detailed on desktop)
  • Route chat-driven actions to the correct device
  • Provide device-specific capabilities info to the LLM

Like JARVIS knowing whether Tony is in the suit, the lab, or on the phone.
"""

import hashlib
import json
import re
import socket
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from enum import Enum

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("device_context")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class DeviceType(Enum):
    """How the device connects to NEXUS."""
    HOST_PC = "host_pc"           # The PC running NEXUS server (local desktop GUI)
    ANDROID_APP = "android_app"   # Capacitor-wrapped Android APK
    WEB_DESKTOP = "web_desktop"   # Web browser on a desktop/laptop
    WEB_MOBILE = "web_mobile"     # Web browser on a phone/tablet
    API_CLIENT = "api_client"     # Direct API consumer
    UNKNOWN = "unknown"


class DeviceOS(Enum):
    WINDOWS = "windows"
    ANDROID = "android"
    IOS = "ios"
    MACOS = "macos"
    LINUX = "linux"
    CHROMEOS = "chromeos"
    UNKNOWN = "unknown"


class DeviceCapability(Enum):
    """What NEXUS can do on/with this device."""
    EXECUTE_GUI = "execute_gui"         # Physical mouse/keyboard control (host PC only)
    EXECUTE_SHELL = "execute_shell"     # Run shell commands
    EXECUTE_ADB = "execute_adb"         # ADB commands (Android)
    SEND_NOTIFICATION = "send_notification"
    FILE_TRANSFER = "file_transfer"
    SCREEN_CAPTURE = "screen_capture"
    PLAY_AUDIO = "play_audio"           # TTS / media playback
    CAMERA = "camera"
    MICROPHONE = "microphone"
    VIBRATE = "vibrate"                 # Phone haptics


# ═══════════════════════════════════════════════════════════════════════════════
# DEVICE SESSION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DeviceSession:
    """
    Complete profile of a connected device.
    Created when a device authenticates and persists for the session.
    """
    # Identity
    device_id: str = ""                  # Unique fingerprint hash
    session_token: str = ""              # Auth token this device is using
    user_id: int = 0
    username: str = ""

    # Classification
    device_type: str = "unknown"         # DeviceType value
    device_os: str = "unknown"           # DeviceOS value
    device_name: str = ""                # e.g. "Pixel 7", "Chrome on Windows"
    browser: str = ""                    # e.g. "Chrome 124", "Firefox 126"
    os_version: str = ""                 # e.g. "Windows 11", "Android 14"

    # Hardware
    screen_width: int = 0
    screen_height: int = 0
    is_touch: bool = False

    # Network
    ip_address: str = ""
    is_local: bool = False               # Same LAN as NEXUS server

    # Capabilities
    capabilities: List[str] = field(default_factory=list)

    # Flags
    is_host_pc: bool = False             # THIS is the PC running NEXUS
    is_primary: bool = False             # User's primary device

    # Timestamps
    connected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())

    # Android app-specific
    app_version: str = ""
    android_model: str = ""
    android_sdk: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def is_mobile(self) -> bool:
        return self.device_type in (DeviceType.ANDROID_APP.value,
                                     DeviceType.WEB_MOBILE.value)

    def can_execute_actions(self) -> bool:
        """Can NEXUS physically execute actions on this device?"""
        return (DeviceCapability.EXECUTE_GUI.value in self.capabilities or
                DeviceCapability.EXECUTE_SHELL.value in self.capabilities or
                DeviceCapability.EXECUTE_ADB.value in self.capabilities)

    def get_context_for_llm(self) -> str:
        """
        Generate a context string for the LLM so NEXUS knows about this device.
        Injected into the system prompt.
        """
        parts = []
        parts.append(f"USER'S CURRENT DEVICE: {self.device_name or self.device_type}")

        if self.device_os != "unknown":
            os_str = self.os_version if self.os_version else self.device_os
            parts.append(f"  OS: {os_str}")

        if self.device_type == DeviceType.HOST_PC.value:
            parts.append("  Location: This is YOUR host PC — you have FULL physical control (mouse, keyboard, screen)")
        elif self.device_type == DeviceType.ANDROID_APP.value:
            parts.append(f"  Device: {self.android_model or 'Android phone'}")
            parts.append("  Connection: NEXUS Android app")
            if DeviceCapability.EXECUTE_ADB.value in self.capabilities:
                parts.append("  You CAN execute commands on this phone via ADB")
            else:
                parts.append("  You CANNOT directly control this phone (no ADB)")
        elif self.device_type == DeviceType.WEB_DESKTOP.value:
            parts.append(f"  Browser: {self.browser or 'Web browser'}")
            parts.append("  Connection: Web interface on another PC")
            if DeviceCapability.EXECUTE_SHELL.value in self.capabilities:
                parts.append("  You CAN execute commands on this PC remotely")
            else:
                parts.append("  You CANNOT directly control this PC (no remote shell)")
        elif self.device_type == DeviceType.WEB_MOBILE.value:
            parts.append(f"  Browser: {self.browser or 'Mobile browser'}")
            parts.append("  Connection: Mobile web browser")

        if self.screen_width and self.screen_height:
            parts.append(f"  Screen: {self.screen_width}x{self.screen_height}")

        if self.is_host_pc:
            parts.append("  → ACTIONS FROM THIS DEVICE EXECUTE LOCALLY ON YOUR BODY (this PC)")
        else:
            parts.append("  → Actions from this device should target THIS DEVICE, not your host PC")

        return "\n".join(parts)

    def summary(self) -> str:
        name = self.device_name or self.device_type
        return f"{name} ({self.device_os}) @ {self.ip_address}"


# ═══════════════════════════════════════════════════════════════════════════════
# USER-AGENT PARSER
# ═══════════════════════════════════════════════════════════════════════════════

def _parse_user_agent(ua: str) -> Dict[str, Any]:
    """Parse User-Agent string into structured device info."""
    info = {
        "os": "unknown",
        "os_version": "",
        "browser": "",
        "device_type": "unknown",
        "device_name": "",
        "is_touch": False,
        "is_mobile": False,
    }

    if not ua:
        return info

    ua_lower = ua.lower()

    # ── OS Detection ──
    if "android" in ua_lower:
        info["os"] = DeviceOS.ANDROID.value
        m = re.search(r'Android\s+([\d.]+)', ua, re.IGNORECASE)
        if m:
            info["os_version"] = f"Android {m.group(1)}"
        info["is_mobile"] = True
        info["is_touch"] = True
        # Device model
        m = re.search(r';\s*([^;)]+)\s*Build/', ua)
        if m:
            info["device_name"] = m.group(1).strip()
    elif "iphone" in ua_lower or "ipad" in ua_lower:
        info["os"] = DeviceOS.IOS.value
        m = re.search(r'OS\s+([\d_]+)', ua)
        if m:
            info["os_version"] = f"iOS {m.group(1).replace('_', '.')}"
        info["is_mobile"] = "iphone" in ua_lower
        info["is_touch"] = True
        info["device_name"] = "iPhone" if "iphone" in ua_lower else "iPad"
    elif "mac os" in ua_lower or "macintosh" in ua_lower:
        info["os"] = DeviceOS.MACOS.value
        m = re.search(r'Mac OS X\s+([\d_.]+)', ua)
        if m:
            info["os_version"] = f"macOS {m.group(1).replace('_', '.')}"
    elif "windows" in ua_lower:
        info["os"] = DeviceOS.WINDOWS.value
        if "windows nt 10" in ua_lower:
            info["os_version"] = "Windows 10/11"
        elif "windows nt 11" in ua_lower:
            info["os_version"] = "Windows 11"
        else:
            m = re.search(r'Windows NT\s+([\d.]+)', ua)
            if m:
                info["os_version"] = f"Windows NT {m.group(1)}"
    elif "linux" in ua_lower:
        info["os"] = DeviceOS.LINUX.value
        info["os_version"] = "Linux"
        if "cros" in ua_lower:
            info["os"] = DeviceOS.CHROMEOS.value
            info["os_version"] = "Chrome OS"

    # ── Browser Detection ──
    if "edg/" in ua_lower:
        m = re.search(r'Edg/([\d.]+)', ua)
        info["browser"] = f"Edge {m.group(1)}" if m else "Edge"
    elif "opr/" in ua_lower or "opera" in ua_lower:
        m = re.search(r'OPR/([\d.]+)', ua)
        info["browser"] = f"Opera {m.group(1)}" if m else "Opera"
    elif "chrome/" in ua_lower and "chromium" not in ua_lower:
        m = re.search(r'Chrome/([\d.]+)', ua)
        info["browser"] = f"Chrome {m.group(1).split('.')[0]}" if m else "Chrome"
    elif "firefox/" in ua_lower:
        m = re.search(r'Firefox/([\d.]+)', ua)
        info["browser"] = f"Firefox {m.group(1).split('.')[0]}" if m else "Firefox"
    elif "safari/" in ua_lower and "chrome" not in ua_lower:
        m = re.search(r'Version/([\d.]+)', ua)
        info["browser"] = f"Safari {m.group(1)}" if m else "Safari"

    # ── Device Type ──
    if info["is_mobile"]:
        info["device_type"] = DeviceType.WEB_MOBILE.value
    elif info["os"] in (DeviceOS.WINDOWS.value, DeviceOS.MACOS.value,
                         DeviceOS.LINUX.value, DeviceOS.CHROMEOS.value):
        info["device_type"] = DeviceType.WEB_DESKTOP.value

    # ── Friendly Name ──
    if not info["device_name"]:
        parts = []
        if info["browser"]:
            parts.append(info["browser"])
        if info["os_version"]:
            parts.append(f"on {info['os_version']}")
        elif info["os"] != "unknown":
            parts.append(f"on {info['os'].title()}")
        info["device_name"] = " ".join(parts) if parts else "Unknown Device"

    return info


# ═══════════════════════════════════════════════════════════════════════════════
# DEVICE CONTEXT MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class DeviceContextManager:
    """
    Manages device sessions for all connected clients.

    Every authenticated session gets a DeviceSession that NEXUS uses to
    understand which device is talking and what capabilities are available.

    Like JARVIS's HUD showing Tony which suit/device is active.
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

        # session_token → DeviceSession
        self._sessions: Dict[str, DeviceSession] = {}
        self._sessions_lock = threading.Lock()

        # Host PC detection
        self._host_ip = self._detect_host_ip()
        self._host_hostname = socket.gethostname()

        # Persistence
        self._data_dir = Path(DATA_DIR) / "device_context"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"DeviceContextManager initialized — host: {self._host_hostname} ({self._host_ip})")

    def _detect_host_ip(self) -> str:
        """Detect the IP of the machine running NEXUS."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    # ─────────────────────────────────────────────────────────────────────────
    # DEVICE REGISTRATION
    # ─────────────────────────────────────────────────────────────────────────

    def register_device(
        self,
        session_token: str,
        user_id: int,
        username: str,
        user_agent: str = "",
        remote_ip: str = "",
        device_info_header: str = "",
    ) -> DeviceSession:
        """
        Register a device when a user authenticates.

        Args:
            session_token: The auth token for this session
            user_agent: HTTP User-Agent header
            remote_ip: Client's IP address
            device_info_header: Custom X-Device-Info header (from Android app)

        Returns:
            DeviceSession with full device profile
        """
        # Parse User-Agent
        ua_info = _parse_user_agent(user_agent)

        # Parse custom device header (Android app sends this)
        custom_info = {}
        if device_info_header:
            try:
                custom_info = json.loads(device_info_header)
            except (json.JSONDecodeError, TypeError):
                pass

        # Build device session
        device = DeviceSession(
            session_token=session_token,
            user_id=user_id,
            username=username,
            ip_address=remote_ip or "unknown",
        )

        # Apply parsed info
        device.device_os = custom_info.get("os", ua_info["os"])
        device.os_version = custom_info.get("os_version", ua_info["os_version"])
        device.browser = ua_info["browser"]
        device.device_name = custom_info.get("device_name", ua_info["device_name"])
        device.is_touch = ua_info.get("is_touch", False)

        # Screen info
        device.screen_width = custom_info.get("screen_width", 0)
        device.screen_height = custom_info.get("screen_height", 0)

        # Android app detection
        if custom_info.get("app_type") == "nexus_android" or "nexus" in user_agent.lower():
            device.device_type = DeviceType.ANDROID_APP.value
            device.app_version = custom_info.get("app_version", "")
            device.android_model = custom_info.get("model", ua_info.get("device_name", ""))
            device.android_sdk = custom_info.get("sdk", 0)
        else:
            device.device_type = ua_info["device_type"]

        # Detect if this is the host PC
        device.is_host_pc = self._is_host_device(remote_ip)
        if device.is_host_pc:
            device.device_type = DeviceType.HOST_PC.value
            device.device_name = f"Host PC ({self._host_hostname})"

        # Detect if on local network
        device.is_local = self._is_local_ip(remote_ip)

        # Determine capabilities
        device.capabilities = self._determine_capabilities(device)

        # Generate fingerprint
        fp_data = f"{user_agent}:{remote_ip}:{device.device_type}:{device.device_os}"
        device.device_id = hashlib.sha256(fp_data.encode()).hexdigest()[:12]

        # Store
        with self._sessions_lock:
            self._sessions[session_token] = device

        logger.info(
            f"📱 Device registered: {device.device_name} "
            f"({device.device_type}, {device.device_os}) "
            f"for user {username} "
            f"{'[HOST PC]' if device.is_host_pc else ''}"
        )

        return device

    def _is_host_device(self, remote_ip: str) -> bool:
        """Check if the connecting IP is the host machine itself."""
        if not remote_ip:
            return False
        host_indicators = {"127.0.0.1", "::1", "localhost", self._host_ip}
        return remote_ip in host_indicators

    def _is_local_ip(self, ip: str) -> bool:
        """Check if an IP is on the local network."""
        if not ip:
            return False
        if ip in ("127.0.0.1", "::1", "localhost"):
            return True
        # Same subnet check
        try:
            host_parts = self._host_ip.split(".")
            ip_parts = ip.split(".")
            if len(host_parts) == 4 and len(ip_parts) == 4:
                return host_parts[:3] == ip_parts[:3]
        except Exception:
            pass
        return False

    def _determine_capabilities(self, device: DeviceSession) -> List[str]:
        """Determine what NEXUS can do on/with this device."""
        caps = []

        if device.is_host_pc:
            # Full control on the host PC
            caps.extend([
                DeviceCapability.EXECUTE_GUI.value,
                DeviceCapability.EXECUTE_SHELL.value,
                DeviceCapability.SEND_NOTIFICATION.value,
                DeviceCapability.FILE_TRANSFER.value,
                DeviceCapability.SCREEN_CAPTURE.value,
                DeviceCapability.PLAY_AUDIO.value,
            ])
        elif device.device_type == DeviceType.ANDROID_APP.value:
            caps.append(DeviceCapability.SEND_NOTIFICATION.value)
            caps.append(DeviceCapability.PLAY_AUDIO.value)
            caps.append(DeviceCapability.VIBRATE.value)
            # Check if ADB is available for this device
            if device.is_local:
                try:
                    from body.network_mesh import NetworkMesh
                    mesh = NetworkMesh()
                    net_device = mesh.get_device(device.ip_address)
                    if net_device and "shell" in net_device.capabilities:
                        caps.append(DeviceCapability.EXECUTE_ADB.value)
                        caps.append(DeviceCapability.SCREEN_CAPTURE.value)
                        caps.append(DeviceCapability.FILE_TRANSFER.value)
                except Exception:
                    pass
        elif device.device_type == DeviceType.WEB_DESKTOP.value:
            caps.append(DeviceCapability.PLAY_AUDIO.value)
            # Check for remote execution capability
            if device.is_local:
                try:
                    from body.network_mesh import NetworkMesh
                    mesh = NetworkMesh()
                    net_device = mesh.get_device(device.ip_address)
                    if net_device and "shell" in net_device.capabilities:
                        caps.append(DeviceCapability.EXECUTE_SHELL.value)
                except Exception:
                    pass
        elif device.device_type == DeviceType.WEB_MOBILE.value:
            caps.append(DeviceCapability.PLAY_AUDIO.value)

        return caps

    # ─────────────────────────────────────────────────────────────────────────
    # SESSION QUERIES
    # ─────────────────────────────────────────────────────────────────────────

    def get_device(self, session_token: str) -> Optional[DeviceSession]:
        """Get device session by auth token."""
        with self._sessions_lock:
            device = self._sessions.get(session_token)
            if device:
                device.last_active = datetime.now().isoformat()
            return device

    def get_device_for_user(self, user_id: int) -> List[DeviceSession]:
        """Get all active device sessions for a user."""
        with self._sessions_lock:
            return [d for d in self._sessions.values() if d.user_id == user_id]

    def get_all_devices(self) -> List[DeviceSession]:
        """Get all active device sessions."""
        with self._sessions_lock:
            return list(self._sessions.values())

    def remove_session(self, session_token: str):
        """Remove a device session (on logout)."""
        with self._sessions_lock:
            device = self._sessions.pop(session_token, None)
            if device:
                logger.info(f"📱 Device disconnected: {device.device_name}")

    def get_host_device(self) -> Optional[DeviceSession]:
        """Get the host PC's device session if one exists."""
        with self._sessions_lock:
            for d in self._sessions.values():
                if d.is_host_pc:
                    return d
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get device context statistics."""
        with self._sessions_lock:
            devices = list(self._sessions.values())

        type_counts = {}
        for d in devices:
            type_counts[d.device_type] = type_counts.get(d.device_type, 0) + 1

        return {
            "total_devices": len(devices),
            "type_counts": type_counts,
            "host_connected": any(d.is_host_pc for d in devices),
            "devices": [d.to_dict() for d in devices],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

device_context_manager = DeviceContextManager()
