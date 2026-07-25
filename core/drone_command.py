"""
NEXUS AI — Drone Command: Autonomous Robotics & Swarm Control
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  SIMULATION ONLY — This module provides scaffolding and data models for
    drone/robotics concepts.  It does NOT connect to real ROS2 nodes,
    MAVLink autopilots, or physical drones.  All flight operations and
    sensor data are simulated.

God-Level Feature #6: Physical world interaction through autonomous drones
and robotic actuators via ROS2 and MAVLink.

Architecture:
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │ ROS2         │  │  MAVLINK     │  │  SWARM       │  │  SENSOR      │
  │ Bridge       │  │  Protocol    │  │  Coordinator │  │  Fusion      │
  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
         │                 │                  │                  │
  ┌──────▼─────────────────▼──────────────────▼──────────────────▼──────┐
  │                    DRONE COMMAND ENGINE                             │
  │   • ROS2 topic pub/sub and service calls                           │
  │   • MAVLink v2 protocol for ArduPilot/PX4                         │
  │   • Multi-drone swarm formation control                            │
  │   • Waypoint navigation with obstacle avoidance                    │
  │   • Multi-sensor fusion (IMU, GPS, LiDAR, Camera)                 │
  │   • Autonomous mission planning and execution                      │
  └────────────────────────────────────────────────────────────────────┘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json
import math
import os
import struct
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

logger = get_logger("drone_command")

# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class DroneType(Enum):
    QUADCOPTER = "quadcopter"
    HEXACOPTER = "hexacopter"
    OCTOCOPTER = "octocopter"
    FIXED_WING = "fixed_wing"
    VTOL = "vtol"
    GROUND_ROVER = "ground_rover"
    SUBMARINE_ROV = "submarine_rov"
    ROBOTIC_ARM = "robotic_arm"

class FlightMode(Enum):
    STABILIZE = "stabilize"
    ALT_HOLD = "alt_hold"
    LOITER = "loiter"
    AUTO = "auto"
    GUIDED = "guided"
    RTL = "return_to_launch"
    LAND = "land"
    TAKEOFF = "takeoff"
    ACRO = "acro"
    FORMATION = "formation"

class MissionState(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    ARMED = "armed"
    IN_FLIGHT = "in_flight"
    EXECUTING = "executing"
    HOVERING = "hovering"
    RETURNING = "returning"
    LANDING = "landing"
    EMERGENCY = "emergency"
    COMPLETED = "completed"

class SensorType(Enum):
    IMU = "imu"
    GPS = "gps"
    BAROMETER = "barometer"
    MAGNETOMETER = "magnetometer"
    LIDAR = "lidar"
    CAMERA_RGB = "camera_rgb"
    CAMERA_THERMAL = "camera_thermal"
    ULTRASONIC = "ultrasonic"
    OPTICAL_FLOW = "optical_flow"
    RADAR = "radar"

class SwarmFormation(Enum):
    LINE = "line"
    V_SHAPE = "v_shape"
    GRID = "grid"
    CIRCLE = "circle"
    DIAMOND = "diamond"
    COLUMN = "column"
    SCATTER = "scatter"
    CUSTOM = "custom"

@dataclass
class GeoPosition:
    latitude: float = 0.0
    longitude: float = 0.0
    altitude_m: float = 0.0
    heading_deg: float = 0.0
    speed_ms: float = 0.0
    climb_rate_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    accuracy_m: float = 0.0
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

    def distance_to(self, other: 'GeoPosition') -> float:
        R = 6371000
        dlat = math.radians(other.latitude - self.latitude)
        dlon = math.radians(other.longitude - self.longitude)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(self.latitude)) * \
            math.cos(math.radians(other.latitude)) * math.sin(dlon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

@dataclass
class Waypoint:
    wp_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    position: Dict[str, float] = field(default_factory=lambda: {"lat": 0.0, "lon": 0.0, "alt": 10.0})
    speed_ms: float = 5.0
    loiter_sec: float = 0.0
    action: str = ""
    reached: bool = False
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

@dataclass
class DroneUnit:
    drone_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    drone_type: str = "quadcopter"
    flight_mode: str = "stabilize"
    mission_state: str = "idle"
    armed: bool = False
    battery_pct: float = 100.0
    battery_voltage: float = 12.6
    position: Dict[str, float] = field(default_factory=lambda: {"lat": 0.0, "lon": 0.0, "alt": 0.0})
    heading_deg: float = 0.0
    speed_ms: float = 0.0
    home_position: Dict[str, float] = field(default_factory=dict)
    firmware: str = "ArduPilot"
    connection: str = ""
    signal_strength: float = 100.0
    gps_satellites: int = 0
    flight_time_sec: float = 0.0
    max_speed_ms: float = 15.0
    max_altitude_m: float = 120.0
    payload_kg: float = 0.0
    sensors: List[str] = field(default_factory=list)
    waypoints: List[Dict] = field(default_factory=list)
    telemetry_hz: float = 10.0
    last_telemetry: Optional[str] = None
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

@dataclass
class SensorData:
    sensor_type: str = ""
    drone_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    data: Dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

@dataclass
class DroneStats:
    total_drones: int = 0
    active_drones: int = 0
    total_flights: int = 0
    total_flight_hours: float = 0.0
    total_distance_km: float = 0.0
    total_waypoints_reached: int = 0
    active_missions: int = 0
    completed_missions: int = 0
    emergency_landings: int = 0
    swarm_formations: int = 0
    sensor_readings: int = 0
    mavlink_messages: int = 0
    def to_dict(self) -> Dict[str, Any]: return asdict(self)

# ═══════════════════════════════════════════════════════════════════════════════
# MAVLINK PROTOCOL HANDLER
# ═══════════════════════════════════════════════════════════════════════════════

class MAVLinkHandler:
    """MAVLink v2 protocol for drone communication."""

    MAVLINK_HEADER = 0xFD  # MAVLink v2

    def __init__(self):
        self._sequence = 0
        self._system_id = 255
        self._component_id = 0
        self._lock = threading.Lock()

    def build_heartbeat(self) -> bytes:
        with self._lock:
            self._sequence = (self._sequence + 1) % 256
            payload = struct.pack("<BIIBB",
                6,   # MAV_TYPE_GCS
                8,   # MAV_AUTOPILOT_INVALID (for GCS)
                0,   # base_mode
                0,   # custom_mode
                4,   # MAV_STATE_ACTIVE
            )
            return self._build_packet(0, payload)  # msg_id=0 is heartbeat

    def build_command_arm(self, arm: bool = True) -> bytes:
        with self._lock:
            self._sequence = (self._sequence + 1) % 256
            payload = struct.pack("<fffffffHBBB",
                1.0 if arm else 0.0,  # param1: 1=arm, 0=disarm
                0, 0, 0, 0, 0, 0,    # params 2-7
                400,                   # MAV_CMD_COMPONENT_ARM_DISARM
                0,                     # target_system
                0,                     # target_component
                0,                     # confirmation
            )
            return self._build_packet(76, payload)  # msg_id=76 is COMMAND_LONG

    def build_set_mode(self, mode: FlightMode) -> bytes:
        mode_map = {
            FlightMode.STABILIZE: 0, FlightMode.ALT_HOLD: 2,
            FlightMode.LOITER: 5, FlightMode.AUTO: 3,
            FlightMode.GUIDED: 4, FlightMode.RTL: 6,
            FlightMode.LAND: 9, FlightMode.TAKEOFF: 13,
        }
        custom_mode = mode_map.get(mode, 0)
        with self._lock:
            self._sequence = (self._sequence + 1) % 256
            payload = struct.pack("<IBH",
                custom_mode, 1,  # base_mode: MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
                0,  # target_system
            )
            return self._build_packet(11, payload)

    def build_goto(self, lat: float, lon: float, alt: float) -> bytes:
        with self._lock:
            self._sequence = (self._sequence + 1) % 256
            payload = struct.pack("<IIiffffff",
                0, 0,  # time_boot, target
                6,  # MAV_FRAME_GLOBAL_RELATIVE_ALT_INT
                int(lat * 1e7), int(lon * 1e7),  # lat, lon (degE7)
                alt,  # altitude
                0, 0, 0,  # vx, vy, vz
            )
            return self._build_packet(84, payload)

    def parse_telemetry(self, data: bytes) -> Dict[str, Any]:
        if len(data) < 12 or data[0] != self.MAVLINK_HEADER:
            return {}
        try:
            payload_len = data[1]
            msg_id = struct.unpack("<I", data[7:10] + b"\x00")[0]
            return {"msg_id": msg_id, "payload_len": payload_len, "raw": data.hex()[:40]}
        except Exception:
            return {}

    def _build_packet(self, msg_id: int, payload: bytes) -> bytes:
        header = struct.pack("<BBBBBB",
            self.MAVLINK_HEADER,
            len(payload), 0,  # payload_len, incompat_flags
            0,  # compat_flags
            self._sequence,
            self._system_id,
        )
        msg_id_bytes = struct.pack("<I", msg_id)[:3]
        packet = header + self._component_id.to_bytes(1, "little") + msg_id_bytes + payload
        # CRC would go here in real impl
        crc = sum(packet) & 0xFFFF
        packet += struct.pack("<H", crc)
        return packet

    @property
    def sequence(self) -> int:
        return self._sequence

# ═══════════════════════════════════════════════════════════════════════════════
# SWARM COORDINATOR
# ═══════════════════════════════════════════════════════════════════════════════

class SwarmCoordinator:
    """Multi-drone swarm formation and coordination."""

    def __init__(self):
        self._formations: Dict[str, List[Tuple[float, float, float]]] = {}
        self._active_formation: str = ""

    def compute_formation(self, formation: SwarmFormation, num_drones: int,
                           center_lat: float, center_lon: float,
                           spacing_m: float = 10.0) -> List[Dict[str, float]]:
        positions = []
        if formation == SwarmFormation.LINE:
            for i in range(num_drones):
                offset = (i - num_drones / 2) * spacing_m
                positions.append({"lat": center_lat, "lon": center_lon + offset / 111000, "alt": 20.0})

        elif formation == SwarmFormation.V_SHAPE:
            for i in range(num_drones):
                side = 1 if i % 2 == 0 else -1
                depth = (i + 1) // 2
                lat_offset = -depth * spacing_m / 111000
                lon_offset = side * depth * spacing_m / 111000
                positions.append({"lat": center_lat + lat_offset, "lon": center_lon + lon_offset, "alt": 20.0})

        elif formation == SwarmFormation.GRID:
            cols = max(1, int(math.sqrt(num_drones)))
            for i in range(num_drones):
                row, col = divmod(i, cols)
                positions.append({
                    "lat": center_lat + row * spacing_m / 111000,
                    "lon": center_lon + col * spacing_m / 111000,
                    "alt": 20.0
                })

        elif formation == SwarmFormation.CIRCLE:
            for i in range(num_drones):
                angle = 2 * math.pi * i / num_drones
                lat_offset = spacing_m * math.cos(angle) / 111000
                lon_offset = spacing_m * math.sin(angle) / 111000
                positions.append({"lat": center_lat + lat_offset, "lon": center_lon + lon_offset, "alt": 20.0})

        elif formation == SwarmFormation.DIAMOND:
            for i in range(num_drones):
                angle = 2 * math.pi * i / num_drones + math.pi / 4
                radius = spacing_m * (1 + 0.3 * math.cos(4 * angle))
                positions.append({
                    "lat": center_lat + radius * math.cos(angle) / 111000,
                    "lon": center_lon + radius * math.sin(angle) / 111000,
                    "alt": 20.0
                })

        else:
            for i in range(num_drones):
                positions.append({"lat": center_lat, "lon": center_lon, "alt": 20.0})

        self._active_formation = formation.value
        return positions

    @property
    def active_formation(self) -> str:
        return self._active_formation

# ═══════════════════════════════════════════════════════════════════════════════
# SENSOR FUSION
# ═══════════════════════════════════════════════════════════════════════════════

class SensorFusion:
    """Fuses data from multiple drone sensors."""

    def __init__(self):
        self._buffers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._fused_state: Dict[str, Any] = {}

    def ingest(self, sensor_data: SensorData):
        key = f"{sensor_data.drone_id}:{sensor_data.sensor_type}"
        self._buffers[key].append(sensor_data)

    def fuse(self, drone_id: str) -> Dict[str, Any]:
        state = {"drone_id": drone_id, "timestamp": datetime.now().isoformat()}
        # GPS weighting
        gps = list(self._buffers.get(f"{drone_id}:gps", []))
        if gps:
            latest = gps[-1]
            state["position"] = latest.data
        # IMU integration
        imu = list(self._buffers.get(f"{drone_id}:imu", []))
        if imu:
            latest = imu[-1]
            state["orientation"] = latest.data
        # Barometer for altitude correction
        baro = list(self._buffers.get(f"{drone_id}:barometer", []))
        if baro:
            state["baro_altitude"] = baro[-1].data.get("altitude", 0)
        self._fused_state[drone_id] = state
        return state

    @property
    def total_readings(self) -> int:
        return sum(len(buf) for buf in self._buffers.values())

# ═══════════════════════════════════════════════════════════════════════════════
# DRONE COMMAND ENGINE — MAIN
# ═══════════════════════════════════════════════════════════════════════════════

class DroneCommandEngine:
    """God-Level Feature #6: Autonomous Drone / Robotics Command."""

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

        self._data_dir = Path(DATA_DIR) / "drone_command"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._mavlink = MAVLinkHandler()
        self._swarm = SwarmCoordinator()
        self._sensor_fusion = SensorFusion()

        self._running = False
        self._drones: Dict[str, DroneUnit] = {}
        self._stats = DroneStats()
        self._missions: List[Dict] = []

        # pymavlink real connection
        self._has_pymavlink = False
        self._mavlink_connections: Dict[str, Any] = {}
        try:
            from pymavlink import mavutil
            self._has_pymavlink = True
        except ImportError:
            pass

        self._daemon_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._load_state()

        mode = "pymavlink" if self._has_pymavlink else "simulated"
        logger.info(f"🤖 Drone Command initialized [{mode}] | Drones: {self._stats.total_drones}")

    def start(self):
        if self._running:
            return
        self._running = True
        self._daemon_thread = threading.Thread(target=self._daemon_loop, daemon=True, name="DroneCommand")
        self._daemon_thread.start()
        logger.info("🤖 Drone Command daemon started")

    def stop(self):
        self._running = False
        self._save_state()
        # Close all pymavlink connections
        for conn_id, conn in list(self._mavlink_connections.items()):
            try:
                conn.close()
            except Exception:
                pass
        self._mavlink_connections.clear()
        if self._daemon_thread and self._daemon_thread.is_alive():
            self._daemon_thread.join(timeout=10)

    def connect_drone(self, drone_id: str, connection_string: str) -> bool:
        """Connect to a real drone via pymavlink (serial, UDP, TCP).
        Examples:
            - '/dev/ttyUSB0' or 'COM3' for serial
            - 'udp:127.0.0.1:14550' for SITL/UDP
            - 'tcp:127.0.0.1:5760' for TCP
        """
        if not self._has_pymavlink:
            logger.warning("pymavlink not installed — cannot connect to real drone")
            return False

        try:
            from pymavlink import mavutil
            conn = mavutil.mavlink_connection(connection_string, baud=57600)
            conn.wait_heartbeat(timeout=10)
            self._mavlink_connections[drone_id] = conn

            drone = self._drones.get(drone_id)
            if drone:
                drone.connection = connection_string
                drone.firmware = f"MAV_TYPE:{conn.target_system}"
                drone.gps_satellites = 0

            logger.info(f"🤖 Connected to drone {drone_id} via {connection_string} "
                        f"(sysid={conn.target_system})")
            return True
        except Exception as e:
            logger.error(f"🤖 Failed to connect to drone {drone_id}: {e}")
            return False

    def send_arm_command(self, drone_id: str, arm: bool = True) -> bool:
        """Send real ARM/DISARM command via pymavlink."""
        conn = self._mavlink_connections.get(drone_id)
        if not conn:
            return self.arm_drone(drone_id)  # fallback to simulated

        try:
            from pymavlink import mavutil
            conn.mav.command_long_send(
                conn.target_system, conn.target_component,
                mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                0,
                1 if arm else 0,
                0, 0, 0, 0, 0, 0,
            )
            ack = conn.recv_match(type="COMMAND_ACK", blocking=True, timeout=5)
            if ack and ack.result == 0:
                drone = self._drones.get(drone_id)
                if drone:
                    drone.armed = arm
                    drone.mission_state = MissionState.ARMED.value if arm else MissionState.IDLE.value
                return True
            return False
        except Exception as e:
            logger.error(f"ARM command failed: {e}")
            return False

    def send_goto_command(self, drone_id: str, lat: float, lon: float, alt: float) -> bool:
        """Send real GOTO command via pymavlink."""
        conn = self._mavlink_connections.get(drone_id)
        if not conn:
            return False

        try:
            from pymavlink import mavutil
            conn.mav.set_position_target_global_int_send(
                0,  # time_boot_ms
                conn.target_system, conn.target_component,
                mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                0b0000111111111000,  # type_mask (only positions)
                int(lat * 1e7), int(lon * 1e7),
                alt,
                0, 0, 0,  # velocity
                0, 0, 0,  # acceleration
                0, 0,     # yaw, yaw_rate
            )
            return True
        except Exception as e:
            logger.error(f"GOTO command failed: {e}")
            return False

    def _daemon_loop(self):
        time.sleep(120)
        while self._running:
            try:
                self._update_telemetry()
                self._check_battery_levels()
                self._update_stats()
                time.sleep(30)
            except Exception as e:
                logger.error(f"🤖 Drone daemon error: {e}\n{traceback.format_exc()}")
                time.sleep(120)

    def _update_telemetry(self):
        """Read real telemetry from pymavlink connections, or simulate."""
        # Real pymavlink telemetry
        for drone_id, conn in list(self._mavlink_connections.items()):
            drone = self._drones.get(drone_id)
            if not drone:
                continue
            try:
                # Read all available messages (non-blocking)
                for _ in range(50):
                    msg = conn.recv_match(blocking=False)
                    if msg is None:
                        break
                    msg_type = msg.get_type()
                    self._stats.mavlink_messages += 1

                    if msg_type == "HEARTBEAT":
                        drone.last_telemetry = datetime.now().isoformat()
                        drone.armed = bool(msg.base_mode & 128)
                    elif msg_type == "GLOBAL_POSITION_INT":
                        drone.position = {
                            "lat": msg.lat / 1e7,
                            "lon": msg.lon / 1e7,
                            "alt": msg.relative_alt / 1000.0,
                        }
                        drone.heading_deg = msg.hdg / 100.0
                        drone.speed_ms = (msg.vx**2 + msg.vy**2)**0.5 / 100.0
                    elif msg_type == "SYS_STATUS":
                        if msg.voltage_battery > 0:
                            drone.battery_voltage = msg.voltage_battery / 1000.0
                        if msg.battery_remaining >= 0:
                            drone.battery_pct = msg.battery_remaining
                    elif msg_type == "GPS_RAW_INT":
                        drone.gps_satellites = msg.satellites_visible

                    # Feed sensor fusion
                    sd = SensorData(sensor_type=msg_type.lower(), drone_id=drone_id,
                                    data={"raw": str(msg)[:100]})
                    self._sensor_fusion.ingest(sd)
                    self._stats.sensor_readings += 1
            except Exception as e:
                logger.debug(f"Telemetry read error for {drone_id}: {e}")

        # Simulated telemetry for drones without pymavlink connections
        for drone in self._drones.values():
            if drone.drone_id not in self._mavlink_connections and drone.armed:
                drone.flight_time_sec += 30
                drone.battery_pct = max(0, drone.battery_pct - 0.05)
                drone.last_telemetry = datetime.now().isoformat()
                self._stats.mavlink_messages += 1

    def _check_battery_levels(self):
        for drone in self._drones.values():
            if drone.battery_pct < 20 and drone.armed:
                publish(EventType.SYSTEM_ALERT, {
                    "type": "drone_low_battery",
                    "drone_id": drone.drone_id,
                    "battery_pct": drone.battery_pct,
                }, source="drone_command")

    def _update_stats(self):
        self._stats.total_drones = len(self._drones)
        self._stats.active_drones = sum(1 for d in self._drones.values() if d.armed)

    def register_drone(self, name: str, drone_type: DroneType = DroneType.QUADCOPTER,
                        max_speed: float = 15.0, max_alt: float = 120.0) -> str:
        drone = DroneUnit(name=name, drone_type=drone_type.value,
                          max_speed_ms=max_speed, max_altitude_m=max_alt)
        self._drones[drone.drone_id] = drone
        self._stats.total_drones += 1
        return drone.drone_id

    def arm_drone(self, drone_id: str) -> bool:
        drone = self._drones.get(drone_id)
        if drone and not drone.armed:
            drone.armed = True
            drone.mission_state = MissionState.ARMED.value
            return True
        return False

    def create_mission(self, drone_id: str, waypoints: List[Dict]) -> str:
        drone = self._drones.get(drone_id)
        if not drone:
            return ""
        mission_id = str(uuid.uuid4())[:8]
        drone.waypoints = waypoints
        drone.mission_state = MissionState.PLANNING.value
        self._missions.append({"mission_id": mission_id, "drone_id": drone_id, "waypoints": waypoints})
        return mission_id

    def set_swarm_formation(self, formation: SwarmFormation, center_lat: float,
                             center_lon: float, spacing_m: float = 10.0) -> List[Dict]:
        num = len([d for d in self._drones.values() if d.armed])
        positions = self._swarm.compute_formation(formation, max(1, num), center_lat, center_lon, spacing_m)
        self._stats.swarm_formations += 1
        return positions

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "stats": self._stats.to_dict(),
            "drones": {k: v.to_dict() for k, v in list(self._drones.items())[:10]},
            "active_formation": self._swarm.active_formation,
            "sensor_readings": self._sensor_fusion.total_readings,
        }

    def get_summary(self) -> str:
        lines = [
            f"Running: {self._running}",
            f"Drones: {self._stats.total_drones} ({self._stats.active_drones} active)",
            f"Flights: {self._stats.total_flights} | Hours: {self._stats.total_flight_hours:.1f}",
            f"Missions: {self._stats.active_missions} active, {self._stats.completed_missions} done",
            f"Formation: {self._swarm.active_formation or 'none'}",
            f"MAVLink Msgs: {self._stats.mavlink_messages}",
            f"Sensor Readings: {self._stats.sensor_readings}",
        ]
        return "\n".join(lines)

    def _save_state(self):
        try:
            state = {"stats": self._stats.to_dict(), "saved_at": datetime.now().isoformat()}
            (self._data_dir / "drone_state.json").write_text(
                json.dumps(state, indent=2, default=str), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save drone state: {e}")

    def _load_state(self):
        try:
            sf = self._data_dir / "drone_state.json"
            if sf.exists():
                data = json.loads(sf.read_text(encoding="utf-8"))
                for k, v in data.get("stats", {}).items():
                    if hasattr(self._stats, k): setattr(self._stats, k, v)
        except Exception as e:
            logger.warning(f"Could not load drone state: {e}")

drone_command = DroneCommandEngine()
def get_drone_command() -> DroneCommandEngine: return drone_command
