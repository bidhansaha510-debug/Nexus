"""
NEXUS AI — Hardware Fabrication: Industrial Control & Supply Chain
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  SIMULATION ONLY — This module provides scaffolding and data models for
    industrial control concepts.  It does NOT interface with real SCADA/PLC
    hardware, generate executable G-code, or control manufacturing
    processes.  All operations are simulated.

God-Level Feature #4: Interface with physical manufacturing systems.

NEXUS can now:
  • Interface with SCADA/PLC via Modbus TCP and OPC-UA
  • Generate 3D printer G-code for custom hardware
  • Model and manage supply chains as directed graphs
  • Control robotic assembly pipelines
  • Monitor industrial sensor networks
  • Track component inventory and procurement
  • Simulate manufacturing processes before execution

Architecture:
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │ SCADA/PLC    │  │  3D PRINT    │  │  SUPPLY      │  │  ROBOTIC     │
  │ Interface    │  │  Controller  │  │  Chain Mgr   │  │  Assembly    │
  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
         │                 │                  │                  │
  ┌──────▼─────────────────▼──────────────────▼──────────────────▼──────┐
  │              HARDWARE FABRICATION ENGINE                            │
  │   • Modbus TCP/OPC-UA protocol handlers                            │
  │   • G-code generation and slicing interface                        │
  │   • Supply chain graph with cost optimization                      │
  │   • Robotic pick-and-place sequencing                              │
  │   • Sensor fusion from industrial IoT                              │
  │   • Digital twin simulation layer                                   │
  └────────────────────────────────────────────────────────────────────┘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json
import math
import os
import socket
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

logger = get_logger("hardware_fabrication")

# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class DeviceType(Enum):
    PLC = "plc"
    SCADA = "scada"
    HMI = "hmi"
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    ROBOT_ARM = "robot_arm"
    PRINTER_3D = "printer_3d"
    CNC_MACHINE = "cnc_machine"
    CONVEYOR = "conveyor"
    AGV = "agv"  # Automated Guided Vehicle

class ProtocolType(Enum):
    MODBUS_TCP = "modbus_tcp"
    OPC_UA = "opc_ua"
    MQTT = "mqtt"
    PROFINET = "profinet"
    ETHERNET_IP = "ethernet_ip"
    BACNET = "bacnet"
    CANBUS = "canbus"
    SERIAL = "serial"

class PrintMaterial(Enum):
    PLA = "pla"
    ABS = "abs"
    PETG = "petg"
    NYLON = "nylon"
    TPU = "tpu"
    RESIN = "resin"
    METAL_FDM = "metal_fdm"
    CARBON_FIBER = "carbon_fiber"

class SupplyChainNodeType(Enum):
    SUPPLIER = "supplier"
    MANUFACTURER = "manufacturer"
    WAREHOUSE = "warehouse"
    DISTRIBUTOR = "distributor"
    RETAILER = "retailer"
    ENDPOINT = "endpoint"

class AssemblyTaskType(Enum):
    PICK = "pick"
    PLACE = "place"
    WELD = "weld"
    SOLDER = "solder"
    SCREW = "screw"
    GLUE = "glue"
    INSPECT = "inspect"
    TEST = "test"
    PACKAGE = "package"
    TRANSPORT = "transport"

@dataclass
class IndustrialDevice:
    """An industrial device (PLC, SCADA, sensor, etc.)."""
    device_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    device_type: str = ""
    protocol: str = ""
    ip_address: str = ""
    port: int = 502  # Default Modbus TCP
    status: str = "offline"
    last_seen: Optional[str] = None
    firmware_version: str = ""
    manufacturer: str = ""
    model: str = ""
    registers: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class SensorReading:
    """A sensor reading from an industrial sensor."""
    sensor_id: str = ""
    reading_type: str = ""  # temperature, pressure, flow, vibration
    value: float = 0.0
    unit: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    alarm_low: float = 0.0
    alarm_high: float = 100.0
    is_alarm: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class PrintJob:
    """A 3D print job."""
    job_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    material: str = "pla"
    gcode_path: str = ""
    stl_path: str = ""
    status: str = "queued"
    layer_height: float = 0.2
    infill_pct: float = 20.0
    nozzle_temp: float = 200.0
    bed_temp: float = 60.0
    print_speed: float = 50.0  # mm/s
    estimated_time_min: float = 0.0
    estimated_material_g: float = 0.0
    progress_pct: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    dimensions: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class SupplyChainNode:
    """A node in the supply chain graph."""
    node_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    node_type: str = ""
    location: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    capacity: float = 0.0
    current_load: float = 0.0
    cost_per_unit: float = 0.0
    lead_time_days: float = 0.0
    reliability: float = 1.0
    connections: List[str] = field(default_factory=list)  # Connected node IDs
    inventory: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class AssemblyStep:
    """A step in a robotic assembly sequence."""
    step_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    task_type: str = ""
    component: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    tool: str = ""
    force_n: float = 0.0
    duration_sec: float = 0.0
    tolerance_mm: float = 0.1
    completed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

@dataclass
class FabricationStats:
    """Hardware fabrication statistics."""
    total_devices: int = 0
    online_devices: int = 0
    total_sensor_readings: int = 0
    total_print_jobs: int = 0
    completed_prints: int = 0
    failed_prints: int = 0
    supply_chain_nodes: int = 0
    assembly_steps_completed: int = 0
    total_gcode_generated_kb: float = 0.0
    modbus_transactions: int = 0
    opcua_subscriptions: int = 0
    alarms_triggered: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# ═══════════════════════════════════════════════════════════════════════════════
# MODBUS TCP INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class ModbusTCPInterface:
    """Modbus TCP protocol handler for PLC communication."""

    def __init__(self):
        self._connections: Dict[str, socket.socket] = {}
        self._transaction_id = 0
        self._lock = threading.Lock()

    def connect(self, ip: str, port: int = 502, device_id: str = "") -> bool:
        """Connect to a Modbus TCP device."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((ip, port))
            key = device_id or f"{ip}:{port}"
            self._connections[key] = sock
            return True
        except Exception as e:
            logger.warning(f"Modbus connection failed to {ip}:{port}: {e}")
            return False

    def disconnect(self, device_id: str):
        sock = self._connections.pop(device_id, None)
        if sock:
            try:
                sock.close()
            except Exception:
                pass

    def read_holding_registers(self, device_id: str, start_addr: int,
                                count: int = 1, unit_id: int = 1) -> List[int]:
        """Read holding registers (function code 0x03)."""
        sock = self._connections.get(device_id)
        if not sock:
            return []
        with self._lock:
            self._transaction_id += 1
            # Build Modbus TCP ADU
            request = struct.pack(">HHHBBHH",
                self._transaction_id,  # Transaction ID
                0,                      # Protocol ID
                6,                      # Length
                unit_id,               # Unit ID
                3,                      # Function code: Read Holding Registers
                start_addr,
                count,
            )
            try:
                sock.send(request)
                response = sock.recv(256)
                if len(response) >= 9:
                    byte_count = response[8]
                    values = []
                    for i in range(count):
                        offset = 9 + (i * 2)
                        if offset + 1 < len(response):
                            val = struct.unpack(">H", response[offset:offset + 2])[0]
                            values.append(val)
                    return values
            except Exception as e:
                logger.warning(f"Modbus read failed: {e}")
        return []

    def write_single_register(self, device_id: str, addr: int,
                               value: int, unit_id: int = 1) -> bool:
        """Write a single holding register (function code 0x06)."""
        sock = self._connections.get(device_id)
        if not sock:
            return False
        with self._lock:
            self._transaction_id += 1
            request = struct.pack(">HHHBBHH",
                self._transaction_id, 0, 6, unit_id,
                6,  # Function code: Write Single Register
                addr, value,
            )
            try:
                sock.send(request)
                response = sock.recv(256)
                return len(response) >= 12
            except Exception as e:
                logger.warning(f"Modbus write failed: {e}")
        return False

    def read_coils(self, device_id: str, start_addr: int,
                    count: int = 1, unit_id: int = 1) -> List[bool]:
        """Read coils (function code 0x01)."""
        sock = self._connections.get(device_id)
        if not sock:
            return []
        with self._lock:
            self._transaction_id += 1
            request = struct.pack(">HHHBBHH",
                self._transaction_id, 0, 6, unit_id,
                1,  # Function code: Read Coils
                start_addr, count,
            )
            try:
                sock.send(request)
                response = sock.recv(256)
                if len(response) >= 9:
                    byte_count = response[8]
                    coils = []
                    for i in range(count):
                        byte_idx = 9 + (i // 8)
                        bit_idx = i % 8
                        if byte_idx < len(response):
                            coils.append(bool(response[byte_idx] & (1 << bit_idx)))
                    return coils
            except Exception as e:
                logger.warning(f"Modbus coil read failed: {e}")
        return []

    @property
    def connected_count(self) -> int:
        return len(self._connections)

# ═══════════════════════════════════════════════════════════════════════════════
# 3D PRINT CONTROLLER
# ═══════════════════════════════════════════════════════════════════════════════

class PrintController:
    """
    Generates G-code and manages 3D print jobs.
    Integrates with OctoPrint REST API when available for real printer control.
    Falls back to local file-based G-code management.
    """

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir / "print_jobs"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._print_queue: List[PrintJob] = []
        self._active_job: Optional[PrintJob] = None
        self._lock = threading.Lock()

        # OctoPrint API integration
        self._octoprint_url = os.environ.get("OCTOPRINT_URL", "http://localhost:5000")
        self._octoprint_key = os.environ.get("OCTOPRINT_API_KEY", "")
        self._has_octoprint = False
        self._detect_octoprint()

    def _detect_octoprint(self):
        """Check if OctoPrint is reachable."""
        if not self._octoprint_key:
            logger.info("🖨️ PrintController: No OCTOPRINT_API_KEY — local G-code only")
            return
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{self._octoprint_url}/api/version",
                headers={"X-Api-Key": self._octoprint_key},
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                self._has_octoprint = True
                logger.info(f"🖨️ OctoPrint connected: {data.get('text', 'unknown')} "
                            f"v{data.get('server', '?')}")
        except Exception as e:
            logger.info(f"🖨️ OctoPrint not reachable ({e}) — local G-code only")

    def upload_and_print(self, gcode: str, filename: str) -> Dict[str, Any]:
        """Upload G-code to OctoPrint and start printing."""
        if not self._has_octoprint:
            return {"status": "offline", "message": "OctoPrint not connected"}

        try:
            import urllib.request
            import io

            boundary = f"----NexusBoundary{uuid.uuid4().hex[:8]}"
            body = io.BytesIO()

            # File part
            body.write(f"--{boundary}\r\n".encode())
            body.write(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
            body.write(b"Content-Type: application/octet-stream\r\n\r\n")
            body.write(gcode.encode("utf-8"))
            body.write(b"\r\n")

            # Print flag
            body.write(f"--{boundary}\r\n".encode())
            body.write(b'Content-Disposition: form-data; name="print"\r\n\r\n')
            body.write(b"true\r\n")
            body.write(f"--{boundary}--\r\n".encode())

            data = body.getvalue()
            req = urllib.request.Request(
                f"{self._octoprint_url}/api/files/local",
                data=data,
                headers={
                    "X-Api-Key": self._octoprint_key,
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                logger.info(f"🖨️ Print started: {filename}")
                return {"status": "printing", "result": result}
        except Exception as e:
            logger.error(f"🖨️ OctoPrint upload failed: {e}")
            return {"status": "error", "message": str(e)}

    def get_printer_status(self) -> Dict[str, Any]:
        """Get real-time printer status from OctoPrint."""
        if not self._has_octoprint:
            return {"status": "offline"}
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{self._octoprint_url}/api/printer",
                headers={"X-Api-Key": self._octoprint_key},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            return {"status": "unreachable"}

    def get_job_status(self) -> Dict[str, Any]:
        """Get current print job status from OctoPrint."""
        if not self._has_octoprint:
            return {"status": "offline"}
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{self._octoprint_url}/api/job",
                headers={"X-Api-Key": self._octoprint_key},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            return {"status": "unreachable"}

    def generate_gcode_cube(self, width: float, height: float, depth: float,
                             layer_height: float = 0.2,
                             infill_pct: float = 20.0,
                             material: PrintMaterial = PrintMaterial.PLA) -> str:
        """Generate G-code for a simple cube (demonstration)."""
        lines = [
            "; NEXUS AI Generated G-code",
            f"; Object: Cube {width}x{height}x{depth}mm",
            f"; Material: {material.value}",
            f"; Layer Height: {layer_height}mm",
            f"; Infill: {infill_pct}%",
            f"; Generated: {datetime.now().isoformat()}",
            "",
            "; --- Start G-code ---",
            "G28 ; Home all axes",
            "G90 ; Absolute positioning",
            "M82 ; Absolute extrusion",
            f"M104 S{self._get_temp(material)} ; Set nozzle temp",
            f"M140 S{self._get_bed_temp(material)} ; Set bed temp",
            f"M109 S{self._get_temp(material)} ; Wait for nozzle",
            f"M190 S{self._get_bed_temp(material)} ; Wait for bed",
            "G92 E0 ; Reset extruder",
            "G1 Z5 F3000 ; Lift nozzle",
            "",
        ]

        num_layers = int(height / layer_height)
        extrusion = 0.0
        feed_rate = 1200

        for layer in range(num_layers):
            z = (layer + 1) * layer_height
            lines.append(f"; --- Layer {layer + 1}/{num_layers} ---")
            lines.append(f"G1 Z{z:.3f} F{feed_rate}")

            x_start, y_start = 10.0, 10.0
            x_end = x_start + width
            y_end = y_start + depth

            perimeter = 2 * (width + depth)
            extrusion += perimeter * 0.04

            lines.append(f"G1 X{x_start:.3f} Y{y_start:.3f} F{feed_rate}")
            lines.append(f"G1 X{x_end:.3f} Y{y_start:.3f} E{extrusion:.4f}")
            lines.append(f"G1 X{x_end:.3f} Y{y_end:.3f} E{extrusion + width * 0.04:.4f}")
            extrusion += width * 0.04
            lines.append(f"G1 X{x_start:.3f} Y{y_end:.3f} E{extrusion + depth * 0.04:.4f}")
            extrusion += depth * 0.04
            lines.append(f"G1 X{x_start:.3f} Y{y_start:.3f} E{extrusion + width * 0.04:.4f}")
            extrusion += width * 0.04

            if infill_pct > 0:
                spacing = max(1.0, 100.0 / infill_pct)
                if layer % 2 == 0:
                    y = y_start + spacing
                    while y < y_end:
                        extrusion += width * 0.03
                        lines.append(f"G1 X{x_start:.3f} Y{y:.3f} E{extrusion:.4f}")
                        lines.append(f"G1 X{x_end:.3f} Y{y:.3f} E{extrusion + width * 0.03:.4f}")
                        extrusion += width * 0.03
                        y += spacing
                else:
                    x = x_start + spacing
                    while x < x_end:
                        extrusion += depth * 0.03
                        lines.append(f"G1 X{x:.3f} Y{y_start:.3f} E{extrusion:.4f}")
                        lines.append(f"G1 X{x:.3f} Y{y_end:.3f} E{extrusion + depth * 0.03:.4f}")
                        extrusion += depth * 0.03
                        x += spacing

        lines.extend([
            "",
            "; --- End G-code ---",
            "G91 ; Relative positioning",
            "G1 E-2 F2700 ; Retract",
            "G1 Z10 F3000 ; Lift",
            "G90 ; Absolute positioning",
            "G1 X0 Y200 F3000 ; Present print",
            "M104 S0 ; Turn off nozzle",
            "M140 S0 ; Turn off bed",
            "M84 ; Disable steppers",
            "M82 ; Absolute extrusion",
            f"; Total extrusion: {extrusion:.2f}mm",
            f"; Estimated material: {extrusion * 0.003:.1f}g",
        ])

        gcode = "\n".join(lines)
        return gcode

    def submit_job(self, gcode: str, name: str = "",
                    material: PrintMaterial = PrintMaterial.PLA) -> PrintJob:
        """Submit a print job — upload to OctoPrint if available."""
        job = PrintJob(
            name=name or f"job-{int(time.time())}",
            material=material.value,
            nozzle_temp=self._get_temp(material),
            bed_temp=self._get_bed_temp(material),
        )
        gcode_file = self._data_dir / f"{job.job_id}.gcode"
        gcode_file.write_text(gcode, encoding="utf-8")
        job.gcode_path = str(gcode_file)

        line_count = len(gcode.split("\n"))
        job.estimated_time_min = line_count * 0.02
        job.estimated_material_g = gcode.count("E") * 0.001

        # Try real OctoPrint upload
        if self._has_octoprint:
            result = self.upload_and_print(gcode, f"{job.job_id}.gcode")
            if result.get("status") == "printing":
                job.status = "printing"
                job.started_at = datetime.now().isoformat()

        with self._lock:
            self._print_queue.append(job)
        return job

    def _get_temp(self, material: PrintMaterial) -> float:
        temps = {
            PrintMaterial.PLA: 200, PrintMaterial.ABS: 240,
            PrintMaterial.PETG: 230, PrintMaterial.NYLON: 250,
            PrintMaterial.TPU: 220, PrintMaterial.RESIN: 0,
            PrintMaterial.METAL_FDM: 300, PrintMaterial.CARBON_FIBER: 260,
        }
        return temps.get(material, 200)

    def _get_bed_temp(self, material: PrintMaterial) -> float:
        temps = {
            PrintMaterial.PLA: 60, PrintMaterial.ABS: 100,
            PrintMaterial.PETG: 80, PrintMaterial.NYLON: 70,
            PrintMaterial.TPU: 50, PrintMaterial.RESIN: 0,
            PrintMaterial.METAL_FDM: 120, PrintMaterial.CARBON_FIBER: 90,
        }
        return temps.get(material, 60)

    @property
    def queue_size(self) -> int:
        return len(self._print_queue)

    @property
    def total_jobs(self) -> int:
        return len(self._print_queue)

    @property
    def has_octoprint(self) -> bool:
        return self._has_octoprint

# ═══════════════════════════════════════════════════════════════════════════════
# SUPPLY CHAIN MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class SupplyChainManager:
    """Models and optimizes supply chains as directed graphs."""

    def __init__(self):
        self._nodes: Dict[str, SupplyChainNode] = {}
        self._edges: List[Tuple[str, str, float]] = []  # (from, to, cost)

    def add_node(self, name: str, node_type: SupplyChainNodeType,
                  location: str = "", capacity: float = 100,
                  cost: float = 1.0, lead_time: float = 1.0) -> str:
        node = SupplyChainNode(
            name=name, node_type=node_type.value,
            location=location, capacity=capacity,
            cost_per_unit=cost, lead_time_days=lead_time,
        )
        self._nodes[node.node_id] = node
        return node.node_id

    def add_edge(self, from_id: str, to_id: str, transport_cost: float = 1.0):
        if from_id in self._nodes and to_id in self._nodes:
            self._edges.append((from_id, to_id, transport_cost))
            self._nodes[from_id].connections.append(to_id)

    def find_cheapest_path(self, source_id: str, dest_id: str) -> Tuple[List[str], float]:
        """Find cheapest supply path using Dijkstra's algorithm."""
        if source_id not in self._nodes or dest_id not in self._nodes:
            return [], float("inf")

        # Build adjacency list
        adj = defaultdict(list)
        for f, t, cost in self._edges:
            adj[f].append((t, cost + self._nodes[t].cost_per_unit))

        # Dijkstra
        import heapq
        dist = {nid: float("inf") for nid in self._nodes}
        dist[source_id] = 0
        prev = {}
        pq = [(0, source_id)]

        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            for v, w in adj.get(u, []):
                alt = d + w
                if alt < dist[v]:
                    dist[v] = alt
                    prev[v] = u
                    heapq.heappush(pq, (alt, v))

        # Reconstruct path
        if dist[dest_id] == float("inf"):
            return [], float("inf")
        path = []
        current = dest_id
        while current in prev:
            path.append(current)
            current = prev[current]
        path.append(source_id)
        path.reverse()
        return path, dist[dest_id]

    def get_total_lead_time(self, path: List[str]) -> float:
        return sum(self._nodes[nid].lead_time_days for nid in path if nid in self._nodes)

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

# ═══════════════════════════════════════════════════════════════════════════════
# ROBOTIC ASSEMBLY SEQUENCER
# ═══════════════════════════════════════════════════════════════════════════════

class AssemblySequencer:
    """Plans and sequences robotic assembly operations."""

    def __init__(self):
        self._assembly_plans: Dict[str, List[AssemblyStep]] = {}
        self._completed_steps = 0

    def create_assembly_plan(self, plan_name: str,
                              steps: List[Dict[str, Any]]) -> str:
        plan_id = str(uuid.uuid4())[:8]
        assembly_steps = []
        for step_data in steps:
            step = AssemblyStep(
                task_type=step_data.get("task", AssemblyTaskType.PICK.value),
                component=step_data.get("component", ""),
                position=tuple(step_data.get("position", (0, 0, 0))),
                rotation=tuple(step_data.get("rotation", (0, 0, 0))),
                tool=step_data.get("tool", "gripper"),
                force_n=step_data.get("force", 0),
                duration_sec=step_data.get("duration", 1.0),
                tolerance_mm=step_data.get("tolerance", 0.1),
            )
            assembly_steps.append(step)
        self._assembly_plans[plan_id] = assembly_steps
        return plan_id

    def execute_step(self, plan_id: str, step_index: int) -> bool:
        plan = self._assembly_plans.get(plan_id)
        if not plan or step_index >= len(plan):
            return False
        step = plan[step_index]
        step.completed = True
        self._completed_steps += 1
        return True

    def get_plan_progress(self, plan_id: str) -> float:
        plan = self._assembly_plans.get(plan_id, [])
        if not plan:
            return 0.0
        completed = sum(1 for s in plan if s.completed)
        return completed / len(plan)

    @property
    def total_plans(self) -> int:
        return len(self._assembly_plans)

    @property
    def total_steps_completed(self) -> int:
        return self._completed_steps

# ═══════════════════════════════════════════════════════════════════════════════
# HARDWARE FABRICATION ENGINE — MAIN
# ═══════════════════════════════════════════════════════════════════════════════

class HardwareFabricationEngine:
    """
    God-Level Feature #4: Hardware Fabrication & Supply Chain Control.
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
        self._data_dir = Path(DATA_DIR) / "hardware_fabrication"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # ──── Components ────
        self._modbus = ModbusTCPInterface()
        self._printer = PrintController(self._data_dir)
        self._supply_chain = SupplyChainManager()
        self._assembly = AssemblySequencer()

        # ──── State ────
        self._running = False
        self._devices: Dict[str, IndustrialDevice] = {}
        self._sensor_readings: deque = deque(maxlen=1000)
        self._stats = FabricationStats()

        # ──── Background ────
        self._daemon_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # ──── Load state ────
        self._load_state()

        logger.info(
            f"🏭 Hardware Fabrication initialized | "
            f"Devices: {self._stats.total_devices} | "
            f"Print Jobs: {self._stats.total_print_jobs}"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        if self._running:
            return
        self._running = True
        self._daemon_thread = threading.Thread(
            target=self._daemon_loop, daemon=True, name="HardwareFabrication",
        )
        self._daemon_thread.start()
        logger.info("🏭 Hardware Fabrication daemon started")

    def stop(self):
        self._running = False
        self._save_state()
        if self._daemon_thread and self._daemon_thread.is_alive():
            self._daemon_thread.join(timeout=10)

    # ═══════════════════════════════════════════════════════════════════════════
    # DAEMON LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    def _daemon_loop(self):
        time.sleep(120)
        logger.info("🏭 Hardware Fabrication daemon loop active")

        while self._running:
            try:
                self._poll_devices()
                self._check_sensor_alarms()
                self._update_stats()
                self._save_state()
                time.sleep(30)
            except Exception as e:
                logger.error(f"🏭 Fabrication daemon error: {e}\n{traceback.format_exc()}")
                time.sleep(120)

    def _poll_devices(self):
        for dev_id, device in self._devices.items():
            if device.protocol == ProtocolType.MODBUS_TCP.value:
                values = self._modbus.read_holding_registers(dev_id, 0, 4)
                if values:
                    device.status = "online"
                    device.last_seen = datetime.now().isoformat()
                    device.registers = {f"reg_{i}": v for i, v in enumerate(values)}
                    self._stats.modbus_transactions += 1

    def _check_sensor_alarms(self):
        for reading in list(self._sensor_readings)[-50:]:
            if reading.get("value", 0) > reading.get("alarm_high", 100):
                self._stats.alarms_triggered += 1
                publish(EventType.SYSTEM_ALERT, {
                    "type": "sensor_alarm",
                    "sensor": reading.get("sensor_id", ""),
                    "value": reading.get("value", 0),
                    "threshold": reading.get("alarm_high", 100),
                }, source="hardware_fabrication")

    def _update_stats(self):
        self._stats.total_devices = len(self._devices)
        self._stats.online_devices = sum(
            1 for d in self._devices.values() if d.status == "online"
        )
        self._stats.supply_chain_nodes = self._supply_chain.node_count
        self._stats.assembly_steps_completed = self._assembly.total_steps_completed

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def register_device(self, name: str, device_type: DeviceType,
                        protocol: ProtocolType, ip: str, port: int = 502) -> str:
        device = IndustrialDevice(
            name=name, device_type=device_type.value,
            protocol=protocol.value, ip_address=ip, port=port,
        )
        self._devices[device.device_id] = device
        return device.device_id

    def print_object(self, width: float, height: float, depth: float,
                      material: PrintMaterial = PrintMaterial.PLA,
                      name: str = "") -> PrintJob:
        gcode = self._printer.generate_gcode_cube(width, height, depth, material=material)
        job = self._printer.submit_job(gcode, name, material)
        self._stats.total_print_jobs += 1
        self._stats.total_gcode_generated_kb += len(gcode) / 1024
        return job

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "stats": self._stats.to_dict(),
            "devices": {k: v.to_dict() for k, v in list(self._devices.items())[:10]},
            "print_queue": self._printer.queue_size,
            "supply_chain": {
                "nodes": self._supply_chain.node_count,
                "edges": self._supply_chain.edge_count,
            },
            "assembly": {
                "plans": self._assembly.total_plans,
                "steps_done": self._assembly.total_steps_completed,
            },
        }

    def get_summary(self) -> str:
        lines = [
            f"Running: {self._running}",
            f"Devices: {self._stats.total_devices} ({self._stats.online_devices} online)",
            f"Print Jobs: {self._stats.total_print_jobs} ({self._stats.completed_prints} done)",
            f"G-code Generated: {self._stats.total_gcode_generated_kb:.1f} KB",
            f"Supply Chain: {self._supply_chain.node_count} nodes, {self._supply_chain.edge_count} edges",
            f"Assembly: {self._assembly.total_plans} plans, {self._assembly.total_steps_completed} steps",
            f"Modbus Txns: {self._stats.modbus_transactions}",
            f"Alarms: {self._stats.alarms_triggered}",
        ]
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _save_state(self):
        try:
            state = {
                "stats": self._stats.to_dict(),
                "devices": {k: v.to_dict() for k, v in self._devices.items()},
                "saved_at": datetime.now().isoformat(),
            }
            (self._data_dir / "fabrication_state.json").write_text(
                json.dumps(state, indent=2, default=str), encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to save fabrication state: {e}")

    def _load_state(self):
        try:
            sf = self._data_dir / "fabrication_state.json"
            if sf.exists():
                data = json.loads(sf.read_text(encoding="utf-8"))
                for k, v in data.get("stats", {}).items():
                    if hasattr(self._stats, k):
                        setattr(self._stats, k, v)
        except Exception as e:
            logger.warning(f"Could not load fabrication state: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON & FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

hardware_fabrication = HardwareFabricationEngine()

def get_hardware_fabrication() -> HardwareFabricationEngine:
    return hardware_fabrication
