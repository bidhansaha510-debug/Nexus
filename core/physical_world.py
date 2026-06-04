"""
NEXUS AI — Physical World Interaction Layer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Bridges NEXUS to the physical world through IoT device control,
hardware sensor monitoring, environmental awareness, and
physical infrastructure management.

Architecture:
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │ IoT Devices  │  │  HW Sensors  │  │  Smart Home  │  │  USB/Serial  │
  │  MQTT/HTTP   │  │  temp/power  │  │  hue/alexa   │  │  Peripherals │
  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
         │                 │                  │                  │
  ┌──────▼─────────────────▼──────────────────▼──────────────────▼──────┐
  │              PHYSICAL WORLD INTERACTION LAYER                       │
  │   • Device discovery & registration                                │
  │   • Hardware health monitoring (temperature, power, fans)          │
  │   • Environmental sensor aggregation                               │
  │   • USB peripheral detection and interaction                       │
  │   • Smart home API integration                                     │
  │   • Physical presence awareness                                    │
  └────────────────────────────────────────────────────────────────────┘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import hashlib
import json
import os
import platform
import re
import socket
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from utils.logger import get_logger, log_system
from core.event_bus import EventType, event_bus, publish

logger = get_logger("physical_world")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

class DeviceType(Enum):
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    CAMERA = "camera"
    SPEAKER = "speaker"
    DISPLAY = "display"
    USB_DEVICE = "usb_device"
    SMART_PLUG = "smart_plug"
    SMART_LIGHT = "smart_light"
    THERMOSTAT = "thermostat"
    LOCK = "lock"
    ROUTER = "router"
    UNKNOWN = "unknown"


class DeviceState(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    DISCOVERING = "discovering"
    PAIRING = "pairing"


class SensorType(Enum):
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    PRESSURE = "pressure"
    LIGHT = "light"
    MOTION = "motion"
    SOUND = "sound"
    POWER = "power"
    VOLTAGE = "voltage"
    CPU_TEMP = "cpu_temp"
    GPU_TEMP = "gpu_temp"
    FAN_SPEED = "fan_speed"
    BATTERY = "battery"


class EnvironmentState(Enum):
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PhysicalDevice:
    """A physical device known to NEXUS."""
    device_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    device_type: str = "unknown"
    state: str = "offline"
    ip_address: str = ""
    mac_address: str = ""
    manufacturer: str = ""
    model: str = ""
    firmware: str = ""
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    capabilities: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    control_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def summary(self) -> str:
        return f"{self.name} ({self.device_type}) [{self.state}] {self.ip_address}"


@dataclass
class SensorReading:
    """A reading from a sensor."""
    sensor_id: str = ""
    sensor_type: str = "temperature"
    value: float = 0.0
    unit: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = ""
    quality: float = 1.0  # 0-1, data quality

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EnvironmentSnapshot:
    """Snapshot of current physical environment."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    cpu_temp: Optional[float] = None
    gpu_temp: Optional[float] = None
    ambient_temp: Optional[float] = None
    battery_percent: Optional[float] = None
    battery_charging: Optional[bool] = None
    power_consumption: Optional[float] = None
    fan_speeds: Dict[str, int] = field(default_factory=dict)
    disk_temps: Dict[str, float] = field(default_factory=dict)
    network_status: str = "connected"
    usb_devices: int = 0
    bluetooth_devices: int = 0
    environment_state: str = "normal"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class USBDevice:
    """A detected USB device."""
    device_id: str = ""
    name: str = ""
    vendor_id: str = ""
    product_id: str = ""
    serial: str = ""
    device_class: str = ""
    connected_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PhysicalWorldStats:
    """Physical world interaction statistics."""
    total_devices_discovered: int = 0
    active_devices: int = 0
    total_sensor_readings: int = 0
    total_commands_sent: int = 0
    environment_snapshots: int = 0
    usb_devices_detected: int = 0
    alerts_generated: int = 0
    last_scan_time: Optional[str] = None
    environment_state: str = "normal"
    hardware_health: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# HARDWARE MONITOR
# ═══════════════════════════════════════════════════════════════════════════════

class HardwareMonitor:
    """Monitors host hardware sensors and health."""

    def __init__(self):
        self._is_windows = platform.system() == "Windows"
        self._readings: deque = deque(maxlen=500)
        self._lock = threading.Lock()

    def read_all_sensors(self) -> Dict[str, SensorReading]:
        """Read all available hardware sensors."""
        readings = {}

        # CPU temperature
        cpu_temp = self._read_cpu_temp()
        if cpu_temp is not None:
            readings["cpu_temp"] = SensorReading(
                sensor_id="cpu_temp", sensor_type=SensorType.CPU_TEMP.value,
                value=cpu_temp, unit="°C", source="hardware",
            )

        # Battery
        battery = self._read_battery()
        if battery:
            readings["battery"] = SensorReading(
                sensor_id="battery", sensor_type=SensorType.BATTERY.value,
                value=battery["percent"], unit="%", source="hardware",
            )

        # CPU usage as a "sensor"
        try:
            import psutil
            readings["cpu_usage"] = SensorReading(
                sensor_id="cpu_usage", sensor_type=SensorType.POWER.value,
                value=psutil.cpu_percent(interval=0.1), unit="%", source="psutil",
            )
            readings["memory_usage"] = SensorReading(
                sensor_id="memory_usage", sensor_type=SensorType.POWER.value,
                value=psutil.virtual_memory().percent, unit="%", source="psutil",
            )
        except ImportError:
            pass

        with self._lock:
            for r in readings.values():
                self._readings.append(r)

        return readings

    def _read_cpu_temp(self) -> Optional[float]:
        """Read CPU temperature."""
        try:
            import psutil
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current > 0:
                            return entry.current
        except (ImportError, AttributeError):
            pass

        # Windows fallback via WMI
        if self._is_windows:
            try:
                result = subprocess.run(
                    ["powershell", "-Command",
                     "Get-CimInstance MSAcpi_ThermalZoneTemperature -Namespace root/wmi "
                     "2>$null | Select-Object CurrentTemperature -First 1 | "
                     "ForEach-Object { ($_.CurrentTemperature - 2732) / 10 }"],
                    capture_output=True, text=True, timeout=5
                )
                if result.stdout.strip():
                    return float(result.stdout.strip())
            except Exception:
                pass

        return None

    def _read_battery(self) -> Optional[Dict[str, Any]]:
        """Read battery status."""
        try:
            import psutil
            battery = psutil.sensors_battery()
            if battery:
                return {
                    "percent": battery.percent,
                    "charging": battery.power_plugged,
                    "seconds_left": battery.secsleft if battery.secsleft > 0 else None,
                }
        except (ImportError, AttributeError):
            pass
        return None

    def get_environment_snapshot(self) -> EnvironmentSnapshot:
        """Get complete environment snapshot."""
        snap = EnvironmentSnapshot()

        sensors = self.read_all_sensors()

        if "cpu_temp" in sensors:
            snap.cpu_temp = sensors["cpu_temp"].value
        if "battery" in sensors:
            snap.battery_percent = sensors["battery"].value
            battery = self._read_battery()
            if battery:
                snap.battery_charging = battery.get("charging")

        # USB devices
        usb_devices = self._count_usb_devices()
        snap.usb_devices = usb_devices

        # Network status
        snap.network_status = "connected" if self._check_network() else "disconnected"

        # Determine environment state
        if snap.cpu_temp and snap.cpu_temp > 90:
            snap.environment_state = EnvironmentState.CRITICAL.value
        elif snap.cpu_temp and snap.cpu_temp > 75:
            snap.environment_state = EnvironmentState.WARNING.value
        elif snap.battery_percent is not None and snap.battery_percent < 10 and not snap.battery_charging:
            snap.environment_state = EnvironmentState.WARNING.value
        else:
            snap.environment_state = EnvironmentState.NORMAL.value

        return snap

    def _count_usb_devices(self) -> int:
        """Count connected USB devices."""
        if self._is_windows:
            try:
                result = subprocess.run(
                    ["powershell", "-Command",
                     "(Get-PnpDevice -Class USB -Status OK 2>$null).Count"],
                    capture_output=True, text=True, timeout=5
                )
                if result.stdout.strip().isdigit():
                    return int(result.stdout.strip())
            except Exception:
                pass
        return 0

    def _check_network(self) -> bool:
        """Quick network connectivity check."""
        try:
            conn = socket.create_connection(("8.8.8.8", 53), timeout=3)
            conn.close()
            return True
        except (socket.timeout, OSError):
            return False

    def get_hardware_health(self) -> float:
        """Calculate hardware health score (0-1)."""
        health = 1.0
        snap = self.get_environment_snapshot()

        if snap.cpu_temp:
            if snap.cpu_temp > 90:
                health -= 0.4
            elif snap.cpu_temp > 80:
                health -= 0.2
            elif snap.cpu_temp > 70:
                health -= 0.1

        if snap.battery_percent is not None:
            if snap.battery_percent < 10 and not snap.battery_charging:
                health -= 0.3
            elif snap.battery_percent < 20 and not snap.battery_charging:
                health -= 0.1

        if snap.network_status == "disconnected":
            health -= 0.2

        return max(0.0, health)


# ═══════════════════════════════════════════════════════════════════════════════
# DEVICE DISCOVERY
# ═══════════════════════════════════════════════════════════════════════════════

class DeviceDiscovery:
    """Discovers physical devices on the network and locally."""

    def __init__(self):
        self._devices: Dict[str, PhysicalDevice] = {}
        self._lock = threading.Lock()
        self._is_windows = platform.system() == "Windows"

    def scan_network(self, subnet: str = "") -> List[PhysicalDevice]:
        """Scan local network for devices."""
        devices = []

        if not subnet:
            subnet = self._get_local_subnet()
        if not subnet:
            return devices

        try:
            # ARP scan
            if self._is_windows:
                result = subprocess.run(
                    ["arp", "-a"],
                    capture_output=True, text=True, timeout=10
                )
            else:
                result = subprocess.run(
                    ["arp", "-a"],
                    capture_output=True, text=True, timeout=10
                )

            for line in result.stdout.splitlines():
                ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                mac_match = re.search(r'([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}', line)

                if ip_match:
                    ip = ip_match.group(1)
                    mac = mac_match.group(0) if mac_match else ""

                    device = PhysicalDevice(
                        name=f"Device-{ip.split('.')[-1]}",
                        device_type=DeviceType.UNKNOWN.value,
                        state=DeviceState.ONLINE.value,
                        ip_address=ip,
                        mac_address=mac,
                    )

                    # Try to resolve hostname
                    try:
                        hostname = socket.gethostbyaddr(ip)[0]
                        device.name = hostname
                    except (socket.herror, socket.gaierror):
                        pass

                    devices.append(device)

                    with self._lock:
                        self._devices[ip] = device

        except Exception as e:
            logger.debug(f"Network scan error: {e}")

        return devices

    def scan_usb(self) -> List[USBDevice]:
        """Scan for connected USB devices."""
        usb_devices = []

        if self._is_windows:
            try:
                result = subprocess.run(
                    ["powershell", "-Command",
                     "Get-PnpDevice -Class USB -Status OK 2>$null | "
                     "Select-Object InstanceId, FriendlyName, Manufacturer | "
                     "ConvertTo-Json -Depth 1"],
                    capture_output=True, text=True, timeout=10
                )
                if result.stdout.strip():
                    data = json.loads(result.stdout)
                    if isinstance(data, dict):
                        data = [data]
                    for item in data:
                        usb = USBDevice(
                            device_id=str(item.get("InstanceId", ""))[:20],
                            name=item.get("FriendlyName", "Unknown USB"),
                        )
                        usb_devices.append(usb)
            except Exception as e:
                logger.debug(f"USB scan error: {e}")

        return usb_devices

    def _get_local_subnet(self) -> str:
        """Get the local subnet."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            parts = ip.split('.')
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
        except Exception:
            return ""

    @property
    def device_count(self) -> int:
        return len(self._devices)

    def get_all_devices(self) -> List[PhysicalDevice]:
        return list(self._devices.values())


# ═══════════════════════════════════════════════════════════════════════════════
# PHYSICAL WORLD ENGINE — MAIN
# ═══════════════════════════════════════════════════════════════════════════════

class PhysicalWorldEngine:
    """
    Physical World Interaction Layer for NEXUS.
    
    Bridges the digital and physical worlds through hardware
    monitoring, device discovery, and environmental awareness.
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
        self._data_dir = Path(DATA_DIR) / "physical_world"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # ──── Components ────
        self._hw_monitor = HardwareMonitor()
        self._device_discovery = DeviceDiscovery()

        # ──── State ────
        self._running = False
        self._snapshots: deque = deque(maxlen=200)
        self._latest_snapshot: Optional[EnvironmentSnapshot] = None

        # ──── Stats ────
        self._stats = PhysicalWorldStats()

        # ──── Configuration ────
        self._sensor_interval = 60       # seconds
        self._network_scan_interval = 600  # 10 minutes
        self._usb_scan_interval = 120

        # ──── Background ────
        self._daemon_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # ──── Load state ────
        self._load_state()

        logger.info(
            f"🌍 Physical World Engine initialized | "
            f"{self._stats.total_devices_discovered} devices known"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        if self._running:
            return
        self._running = True
        self._daemon_thread = threading.Thread(
            target=self._daemon_loop, daemon=True, name="PhysicalWorld",
        )
        self._daemon_thread.start()
        logger.info("🌍 Physical World daemon started")

    def stop(self):
        self._running = False
        self._save_state()
        if self._daemon_thread and self._daemon_thread.is_alive():
            self._daemon_thread.join(timeout=10)

    # ═══════════════════════════════════════════════════════════════════════════
    # DAEMON LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    def _daemon_loop(self):
        time.sleep(30)
        logger.info("🌍 Physical World daemon loop active")

        last_sensor = 0.0
        last_network = 0.0
        last_usb = 0.0

        while self._running:
            try:
                now = time.time()

                # Sensor readings
                if now - last_sensor >= self._sensor_interval:
                    self._take_snapshot()
                    last_sensor = now

                # Network scan
                if now - last_network >= self._network_scan_interval:
                    self._scan_network()
                    last_network = now

                # USB scan
                if now - last_usb >= self._usb_scan_interval:
                    self._scan_usb()
                    last_usb = now

                time.sleep(15)

            except Exception as e:
                logger.error(f"🌍 Physical World loop error: {e}\n{traceback.format_exc()}")
                time.sleep(60)

    def _take_snapshot(self):
        """Take an environment snapshot."""
        snap = self._hw_monitor.get_environment_snapshot()
        self._latest_snapshot = snap
        self._snapshots.append(snap)
        self._stats.environment_snapshots += 1
        self._stats.environment_state = snap.environment_state
        self._stats.hardware_health = self._hw_monitor.get_hardware_health()

        if snap.environment_state in (EnvironmentState.WARNING.value, EnvironmentState.CRITICAL.value):
            self._stats.alerts_generated += 1
            publish(EventType.SYSTEM_ALERT, {
                "type": "physical_alert",
                "state": snap.environment_state,
                "cpu_temp": snap.cpu_temp,
                "battery": snap.battery_percent,
            }, source="physical_world")

    def _scan_network(self):
        """Scan for network devices."""
        devices = self._device_discovery.scan_network()
        self._stats.total_devices_discovered = self._device_discovery.device_count
        self._stats.active_devices = len(devices)
        self._stats.last_scan_time = datetime.now().isoformat()

    def _scan_usb(self):
        """Scan for USB devices."""
        usb_devices = self._device_discovery.scan_usb()
        self._stats.usb_devices_detected = len(usb_devices)

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def get_environment(self) -> Dict[str, Any]:
        if self._latest_snapshot:
            return self._latest_snapshot.to_dict()
        return self._hw_monitor.get_environment_snapshot().to_dict()

    def get_devices(self) -> List[Dict]:
        return [d.to_dict() for d in self._device_discovery.get_all_devices()]

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "stats": self._stats.to_dict(),
            "environment": self.get_environment(),
            "devices_online": self._stats.active_devices,
            "hardware_health": self._stats.hardware_health,
        }

    def get_summary(self) -> str:
        status = self.get_status()
        env = status["environment"]
        lines = [
            f"Running: {status['running']}",
            f"Hardware Health: {self._stats.hardware_health:.0%}",
            f"Environment: {self._stats.environment_state}",
            f"CPU Temp: {env.get('cpu_temp', 'N/A')}°C",
            f"Battery: {env.get('battery_percent', 'N/A')}%",
            f"Network: {env.get('network_status', 'unknown')}",
            f"Devices Discovered: {self._stats.total_devices_discovered}",
            f"Active Devices: {self._stats.active_devices}",
            f"USB Devices: {self._stats.usb_devices_detected}",
            f"Snapshots Taken: {self._stats.environment_snapshots}",
        ]
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _save_state(self):
        try:
            state = {"stats": self._stats.to_dict(), "saved_at": datetime.now().isoformat()}
            (self._data_dir / "physical_state.json").write_text(
                json.dumps(state, indent=2, default=str), encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to save physical world state: {e}")

    def _load_state(self):
        try:
            sf = self._data_dir / "physical_state.json"
            if sf.exists():
                data = json.loads(sf.read_text(encoding="utf-8"))
                for k, v in data.get("stats", {}).items():
                    if hasattr(self._stats, k):
                        setattr(self._stats, k, v)
        except Exception as e:
            logger.warning(f"Could not load physical world state: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

physical_world = PhysicalWorldEngine()


def get_physical_world() -> PhysicalWorldEngine:
    return physical_world
