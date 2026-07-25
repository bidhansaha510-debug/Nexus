"""
NEXUS AI — P2P Distributed Swarm & Consensus Network
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Decentralized peer-to-peer mesh network protocol for NEXUS instances.
Enables auto-discovery, HMAC-signed gossip messaging, Byzantine Fault
Tolerant (BFT) consensus, and capability-based task offloading.

Architecture:
  ┌─────────────────┐    ┌─────────────────┐
  │  UDP Discovery  │    │  TCP Transport  │
  │  (Port 9877)    │    │  (Port 9876)    │
  └────────┬────────┘    └────────┬────────┘
           │                      │
  ┌────────▼──────────────────────▼────────┐
  │         Peer Manager & Router          │
  │  • Peer Registry & Latency Scoring     │
  │  • HMAC Message Verification           │
  │  • Epidemic Gossip Protocol            │
  └────────────────────┬───────────────────┘
                       │
  ┌────────────────────▼───────────────────┐
  │       BFT Consensus & Offloader        │
  │  • 3-Phase BFT Voting (Pre-Prepare)    │
  │  • Capability-Based Task Offloading    │
  └────────────────────────────────────────┘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import asyncio
import hashlib
import hmac
import json
import math
import os
import random
import secrets
import socket
import sys
import threading
import time
import traceback
import uuid
from collections import deque, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from config import DATA_DIR, NEXUS_CONFIG
from utils.logger import get_logger, log_system
from core.event_bus import EventType, event_bus, publish

logger = get_logger("p2p_swarm")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS & ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class SwarmMessageType(Enum):
    DISCOVER = "discover"
    DISCOVER_ACK = "discover_ack"
    HEARTBEAT = "heartbeat"
    GOSSIP = "gossip"
    DIRECT = "direct"
    BFT_PRE_PREPARE = "bft_pre_prepare"
    BFT_PREPARE = "bft_prepare"
    BFT_COMMIT = "bft_commit"
    TASK_OFFLOAD = "task_offload"
    TASK_RESULT = "task_result"
    LEAVE = "leave"

@dataclass
class PeerInfo:
    """Represents a discovered peer in the P2P swarm."""
    peer_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    hostname: str = field(default_factory=socket.gethostname)
    ip_address: str = "127.0.0.1"
    port: int = 9876
    role: str = "worker"
    capabilities: List[str] = field(default_factory=lambda: ["cognition", "tasks"])
    cpu_load: float = 0.0
    memory_usage_pct: float = 0.0
    gpu_available: bool = False
    last_seen: float = field(default_factory=time.time)
    latency_ms: float = 0.0
    version: str = "1.0.0"
    is_leader: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def is_alive(self) -> bool:
        return (time.time() - self.last_seen) < 35.0

@dataclass
class SwarmMessage:
    """Message routed across the P2P swarm network."""
    msg_id: str = field(default_factory=lambda: str(uuid.uuid4())[:16])
    msg_type: str = SwarmMessageType.GOSSIP.value
    sender_id: str = ""
    target_id: str = ""  # Empty string = broadcast / gossip
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    signature: str = ""
    ttl: int = 30
    hop_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_json(cls, raw: str) -> "SwarmMessage":
        data = json.loads(raw)
        msg = cls()
        for k, v in data.items():
            if hasattr(msg, k):
                setattr(msg, k, v)
        return msg

# ═══════════════════════════════════════════════════════════════════════════════
# UDP DISCOVERY & TCP TRANSPORT
# ═══════════════════════════════════════════════════════════════════════════════

class UDPDiscovery:
    """UDP broadcast/multicast engine for LAN peer discovery."""

    def __init__(self, swarm: "P2PSwarm", discovery_port: int = 9877):
        self.swarm = swarm
        self.port = discovery_port
        self.running = False
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self.running:
            return
        self.running = True
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.bind(("", self.port))
            self._sock.settimeout(2.0)
        except Exception as e:
            logger.warning(f"UDP Discovery socket bind notice ({self.port}): {e}")

        self._thread = threading.Thread(target=self._listen_loop, daemon=True, name="P2P_UDP_Discovery")
        self._thread.start()

    def broadcast_beacon(self):
        if not self._sock:
            return
        try:
            beacon = {
                "type": "NEXUS_SWARM_BEACON",
                "peer": self.swarm.local_peer.to_dict()
            }
            data = json.dumps(beacon).encode("utf-8")
            self._sock.sendto(data, ("<broadcast>", self.port))
        except Exception as e:
            logger.debug(f"UDP beacon send notice: {e}")

    def _listen_loop(self):
        while self.running and self._sock:
            try:
                data, addr = self._sock.recvfrom(4096)
                if not data:
                    continue
                packet = json.loads(data.decode("utf-8", errors="ignore"))
                if packet.get("type") == "NEXUS_SWARM_BEACON":
                    peer_dict = packet.get("peer", {})
                    sender_id = peer_dict.get("peer_id")
                    if sender_id and sender_id != self.swarm.local_peer.peer_id:
                        peer_dict["ip_address"] = addr[0]
                        self.swarm.register_peer_dict(peer_dict)
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.debug(f"UDP listen error: {e}")
                time.sleep(1)

    def stop(self):
        self.running = False
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass

class TCPTransport:
    """TCP server and connection manager for reliable peer transport."""

    def __init__(self, swarm: "P2PSwarm", transport_port: int = 9876):
        self.swarm = swarm
        self.port = transport_port
        self.running = False
        self._server_sock: Optional[socket.socket] = None
        self._server_thread: Optional[threading.Thread] = None

    def start(self):
        if self.running:
            return
        self.running = True
        try:
            self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_sock.bind(("0.0.0.0", self.port))
            self._server_sock.listen(20)
            self._server_sock.settimeout(2.0)
        except Exception as e:
            logger.warning(f"TCP Transport bind warning on {self.port}: {e}")

        self._server_thread = threading.Thread(target=self._accept_loop, daemon=True, name="P2P_TCP_Server")
        self._server_thread.start()

    def _accept_loop(self):
        while self.running and self._server_sock:
            try:
                client_sock, addr = self._server_sock.accept()
                client_sock.settimeout(10.0)
                threading.Thread(
                    target=self._handle_client,
                    args=(client_sock, addr),
                    daemon=True,
                    name=f"P2P_Client_{addr[0]}"
                ).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.debug(f"TCP accept error: {e}")
                time.sleep(1)

    def _handle_client(self, sock: socket.socket, addr: Tuple[str, int]):
        try:
            buf = ""
            while self.running:
                chunk = sock.recv(8192).decode("utf-8", errors="ignore")
                if not chunk:
                    break
                buf += chunk
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if line:
                        self.swarm.handle_incoming_raw_json(line)
        except Exception as e:
            logger.debug(f"Client handler disconnect {addr}: {e}")
        finally:
            try:
                sock.close()
            except Exception:
                pass

    def send_raw(self, ip: str, port: int, payload_json: str) -> bool:
        """Connects and sends framed JSON payload to peer."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5.0)
            s.connect((ip, port))
            s.sendall((payload_json.strip() + "\n").encode("utf-8"))
            s.close()
            return True
        except Exception as e:
            logger.debug(f"TCP send failed to {ip}:{port} -> {e}")
            return False

    def stop(self):
        self.running = False
        if self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass

# ═══════════════════════════════════════════════════════════════════════════════
# BFT CONSENSUS & TASK OFFLOADER
# ═══════════════════════════════════════════════════════════════════════════════

class BFTConsensus:
    """
    Practical Byzantine Fault Tolerant (PBFT) Consensus Engine.
    Executes 3-phase commitment (Pre-Prepare -> Prepare -> Commit)
    to agree on action proposals with >= 2/3 quorum.
    """

    def __init__(self, swarm: "P2PSwarm"):
        self.swarm = swarm
        self.active_proposals: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def propose(self, topic: str, payload: Dict[str, Any]) -> str:
        proposal_id = str(uuid.uuid4())[:12]
        now = time.time()
        record = {
            "proposal_id": proposal_id,
            "topic": topic,
            "payload": payload,
            "proposer_id": self.swarm.local_peer.peer_id,
            "phase": "PRE_PREPARE",
            "prepares": {self.swarm.local_peer.peer_id: True},
            "commits": {self.swarm.local_peer.peer_id: True},
            "created_at": now,
            "status": "pending",
        }
        with self._lock:
            self.active_proposals[proposal_id] = record

        # Broadcast BFT PRE_PREPARE
        self.swarm.broadcast(SwarmMessageType.BFT_PRE_PREPARE.value, {
            "proposal_id": proposal_id,
            "topic": topic,
            "payload": payload,
            "proposer_id": self.swarm.local_peer.peer_id,
        })
        return proposal_id

    def handle_pre_prepare(self, msg: SwarmMessage):
        data = msg.payload
        pid = data.get("proposal_id")
        if not pid:
            return

        with self._lock:
            if pid not in self.active_proposals:
                self.active_proposals[pid] = {
                    "proposal_id": pid,
                    "topic": data.get("topic", ""),
                    "payload": data.get("payload", {}),
                    "proposer_id": data.get("proposer_id"),
                    "phase": "PREPARE",
                    "prepares": {self.swarm.local_peer.peer_id: True},
                    "commits": {},
                    "created_at": time.time(),
                    "status": "pending",
                }

        # Send PREPARE ack
        self.swarm.broadcast(SwarmMessageType.BFT_PREPARE.value, {
            "proposal_id": pid,
            "voter_id": self.swarm.local_peer.peer_id,
        })

    def handle_prepare(self, msg: SwarmMessage):
        data = msg.payload
        pid = data.get("proposal_id")
        voter = data.get("voter_id")
        if not pid or not voter:
            return

        with self._lock:
            record = self.active_proposals.get(pid)
            if not record:
                return
            record["prepares"][voter] = True
            needed_quorum = math.ceil((len(self.swarm.peers) + 1) * 0.66)

            if len(record["prepares"]) >= needed_quorum and record["phase"] == "PREPARE":
                record["phase"] = "COMMIT"
                record["commits"][self.swarm.local_peer.peer_id] = True
                self.swarm.broadcast(SwarmMessageType.BFT_COMMIT.value, {
                    "proposal_id": pid,
                    "voter_id": self.swarm.local_peer.peer_id,
                })

    def handle_commit(self, msg: SwarmMessage):
        data = msg.payload
        pid = data.get("proposal_id")
        voter = data.get("voter_id")
        if not pid or not voter:
            return

        with self._lock:
            record = self.active_proposals.get(pid)
            if not record:
                return
            record["commits"][voter] = True
            needed_quorum = math.ceil((len(self.swarm.peers) + 1) * 0.66)

            if len(record["commits"]) >= needed_quorum and record["status"] != "approved":
                record["status"] = "approved"
                logger.info(f"⚡ BFT Consensus APPROVED proposal {pid} ({record['topic']})")
                publish(EventType.SYSTEM_ALERT, {
                    "type": "bft_consensus_approved",
                    "proposal_id": pid,
                    "topic": record["topic"],
                }, source="p2p_swarm")

    def get_active_summary(self) -> List[Dict[str, Any]]:
        with self._lock:
            total_peers = len(self.swarm.peers) + 1
            res = []
            for pid, r in self.active_proposals.items():
                res.append({
                    "proposal_id": pid,
                    "topic": r["topic"],
                    "phase": r["phase"],
                    "status": r["status"],
                    "prepares_count": len(r["prepares"]),
                    "commits_count": len(r["commits"]),
                    "quorum_needed": math.ceil(total_peers * 0.66),
                })
            return res

class TaskOffloader:
    """Capability and load-based task offloading engine."""

    def __init__(self, swarm: "P2PSwarm"):
        self.swarm = swarm
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def offload_task(self, description: str, task_type: str = "general", payload: Dict = None) -> Optional[str]:
        best_peer = self._select_best_peer(task_type)
        task_id = str(uuid.uuid4())[:12]
        record = {
            "task_id": task_id,
            "description": description,
            "task_type": task_type,
            "payload": payload or {},
            "assigned_to": best_peer.peer_id if best_peer else "local",
            "status": "assigned" if best_peer else "local_fallback",
            "created_at": datetime.now().isoformat(),
            "result": None,
        }
        with self._lock:
            self.tasks[task_id] = record

        if best_peer:
            self.swarm.send_to(best_peer.peer_id, SwarmMessageType.TASK_OFFLOAD.value, {
                "task_id": task_id,
                "description": description,
                "task_type": task_type,
                "payload": payload or {},
            })
            logger.info(f"📤 Task {task_id} offloaded to peer {best_peer.peer_id}@{best_peer.ip_address}")
        else:
            logger.info(f"ℹ️ Task {task_id} assigned locally (no external peer available)")

        return task_id

    def handle_task_result(self, msg: SwarmMessage):
        data = msg.payload
        tid = data.get("task_id")
        if not tid:
            return
        with self._lock:
            if tid in self.tasks:
                self.tasks[tid]["status"] = "completed"
                self.tasks[tid]["result"] = data.get("result")
                self.tasks[tid]["completed_at"] = datetime.now().isoformat()

    def _select_best_peer(self, task_type: str) -> Optional[PeerInfo]:
        candidates = [p for p in self.swarm.peers.values() if p.is_alive]
        if not candidates:
            return None
        # Score candidates by CPU load and capability
        candidates.sort(key=lambda p: (p.cpu_load, p.memory_usage_pct))
        return candidates[0]

    def get_summary(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self.tasks.values())[-20:]

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN P2P SWARM MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class P2PSwarm:
    """
    Master P2P Swarm Network Orchestrator.
    Singleton pattern for system-wide access.
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

        self.local_peer = PeerInfo(
            role="primary",
            capabilities=["cognition", "reasoning", "hacking", "evolution", "monitoring"],
            port=int(os.environ.get("NEXUS_SWARM_PORT", "9876"))
        )
        self.local_peer.ip_address = self._detect_local_ip()

        self.peers: Dict[str, PeerInfo] = {}
        self._seen_messages: Set[str] = set()
        self._recent_msg_history: deque = deque(maxlen=200)

        # Transport components
        self.udp_disc = UDPDiscovery(self, discovery_port=self.local_peer.port + 1)
        self.tcp_trans = TCPTransport(self, transport_port=self.local_peer.port)
        self.bft = BFTConsensus(self)
        self.offloader = TaskOffloader(self)

        # Auth
        self._hmac_secret = os.environ.get("NEXUS_SWARM_SECRET", "nexus-swarm-shared-secret-v1").encode("utf-8")

        # Stats
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "gossip_relays": 0,
            "bft_proposals": 0,
            "tasks_offloaded": 0,
            "start_time": time.time(),
        }

        self.running = False
        self._daemon_thread: Optional[threading.Thread] = None

        logger.info(f"🌐 P2P Swarm initialized | Peer: {self.local_peer.peer_id}@{self.local_peer.ip_address}:{self.local_peer.port}")

    def _detect_local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def start(self):
        if self.running:
            return
        self.running = True
        self.udp_disc.start()
        self.tcp_trans.start()

        self._daemon_thread = threading.Thread(target=self._daemon_loop, daemon=True, name="P2P_Swarm_Daemon")
        self._daemon_thread.start()
        logger.info("⚡ P2P Swarm mesh daemon started.")

    def stop(self):
        self.running = False
        self.broadcast(SwarmMessageType.LEAVE.value, {"peer_id": self.local_peer.peer_id})
        self.udp_disc.stop()
        self.tcp_trans.stop()
        logger.info("🛑 P2P Swarm mesh daemon stopped.")

    def _daemon_loop(self):
        time.sleep(2)
        while self.running:
            try:
                # 1. Update local metrics
                try:
                    import psutil
                    self.local_peer.cpu_load = psutil.cpu_percent() / 100.0
                    self.local_peer.memory_usage_pct = psutil.virtual_memory().percent / 100.0
                except Exception:
                    pass
                self.local_peer.last_seen = time.time()

                # 2. UDP Beacon
                self.udp_disc.broadcast_beacon()

                # 3. Heartbeat gossip to peers
                self.broadcast(SwarmMessageType.HEARTBEAT.value, self.local_peer.to_dict())

                # 4. Peer cleanup
                now = time.time()
                for pid, p in list(self.peers.items()):
                    if (now - p.last_seen) > 60.0:
                        del self.peers[pid]
                        logger.info(f"📉 Peer timed out and removed: {pid}")

                time.sleep(10)
            except Exception as e:
                logger.debug(f"P2P daemon loop exception: {e}")
                time.sleep(10)

    # ═══════════════════════════════════════════════════════════════════════════
    # MESSAGE ROUTING & SIGNING
    # ═══════════════════════════════════════════════════════════════════════════

    def _sign_msg(self, msg: SwarmMessage) -> str:
        data = f"{msg.msg_id}:{msg.sender_id}:{msg.timestamp}".encode("utf-8")
        return hmac.new(self._hmac_secret, data, hashlib.sha256).hexdigest()[:32]

    def _verify_msg(self, msg: SwarmMessage) -> bool:
        if not msg.signature:
            return False
        expected = self._sign_msg(msg)
        return hmac.compare_digest(expected, msg.signature)

    def broadcast(self, msg_type: str, payload: Dict[str, Any]):
        msg = SwarmMessage(
            msg_type=msg_type,
            sender_id=self.local_peer.peer_id,
            payload=payload,
        )
        msg.signature = self._sign_msg(msg)
        self._seen_messages.add(msg.msg_id)
        self.stats["messages_sent"] += 1
        self._recent_msg_history.append(msg.to_dict())

        # Forward to all known alive peers via TCP
        raw_json = msg.to_json()
        for p in list(self.peers.values()):
            if p.is_alive:
                self.tcp_trans.send_raw(p.ip_address, p.port, raw_json)

    def send_to(self, peer_id: str, msg_type: str, payload: Dict[str, Any]):
        peer = self.peers.get(peer_id)
        if not peer:
            return
        msg = SwarmMessage(
            msg_type=msg_type,
            sender_id=self.local_peer.peer_id,
            target_id=peer_id,
            payload=payload,
        )
        msg.signature = self._sign_msg(msg)
        self.stats["messages_sent"] += 1
        self.tcp_trans.send_raw(peer.ip_address, peer.port, msg.to_json())

    def handle_incoming_raw_json(self, raw_json: str):
        try:
            msg = SwarmMessage.from_json(raw_json)
            if msg.msg_id in self._seen_messages:
                return  # Deduplication
            self._seen_messages.add(msg.msg_id)

            if len(self._seen_messages) > 2000:
                self._seen_messages.clear()

            if not self._verify_msg(msg):
                logger.debug(f"Invalid message signature from {msg.sender_id}")
                return

            self.stats["messages_received"] += 1
            self._recent_msg_history.append(msg.to_dict())

            # Handle by message type
            if msg.msg_type == SwarmMessageType.HEARTBEAT.value:
                pdict = msg.payload
                if pdict and "peer_id" in pdict:
                    self.register_peer_dict(pdict)

            elif msg.msg_type == SwarmMessageType.BFT_PRE_PREPARE.value:
                self.bft.handle_pre_prepare(msg)
            elif msg.msg_type == SwarmMessageType.BFT_PREPARE.value:
                self.bft.handle_prepare(msg)
            elif msg.msg_type == SwarmMessageType.BFT_COMMIT.value:
                self.bft.handle_commit(msg)
            elif msg.msg_type == SwarmMessageType.TASK_RESULT.value:
                self.offloader.handle_task_result(msg)

            # Epidemic Gossip Forwarding if target is empty and hop count < ttl
            if not msg.target_id and msg.hop_count < msg.ttl:
                msg.hop_count += 1
                self.stats["gossip_relays"] += 1
                forward_json = msg.to_json()
                alive_peers = [p for p in self.peers.values() if p.peer_id != msg.sender_id and p.is_alive]
                fanout = min(len(alive_peers), 3)
                if alive_peers and fanout > 0:
                    for p in random.sample(alive_peers, fanout):
                        self.tcp_trans.send_raw(p.ip_address, p.port, forward_json)

        except Exception as e:
            logger.debug(f"Incoming message parse error: {e}")

    def register_peer_dict(self, pdict: Dict[str, Any]):
        pid = pdict.get("peer_id")
        if not pid or pid == self.local_peer.peer_id:
            return

        if pid in self.peers:
            peer = self.peers[pid]
            peer.last_seen = time.time()
            peer.cpu_load = pdict.get("cpu_load", peer.cpu_load)
            peer.memory_usage_pct = pdict.get("memory_usage_pct", peer.memory_usage_pct)
            peer.role = pdict.get("role", peer.role)
        else:
            p = PeerInfo()
            for k, v in pdict.items():
                if hasattr(p, k):
                    setattr(p, k, v)
            p.last_seen = time.time()
            self.peers[pid] = p
            logger.info(f"✨ New peer discovered: {p.peer_id}@{p.ip_address}:{p.port}")
            publish(EventType.SYSTEM_ALERT, {
                "type": "p2p_peer_discovered",
                "peer_id": p.peer_id,
                "ip": p.ip_address,
            }, source="p2p_swarm")

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API & STATS
    # ═══════════════════════════════════════════════════════════════════════════

    def propose_bft_action(self, topic: str, payload: Dict = None) -> str:
        self.stats["bft_proposals"] += 1
        return self.bft.propose(topic, payload or {})

    def offload_task(self, description: str, task_type: str = "general", payload: Dict = None) -> Optional[str]:
        self.stats["tasks_offloaded"] += 1
        return self.offloader.offload_task(description, task_type, payload or {})

    def get_swarm_stats(self) -> Dict[str, Any]:
        alive_peers = [p.to_dict() for p in self.peers.values() if p.is_alive]
        total = len(self.peers) + 1
        bft_proposals = self.bft.get_active_summary()
        tasks = self.offloader.get_summary()

        topology = [
            {"id": self.local_peer.peer_id, "label": f"Local ({self.local_peer.hostname})", "group": "local", "ip": self.local_peer.ip_address}
        ]
        for p in alive_peers:
            topology.append({"id": p["peer_id"], "label": f"{p['hostname']} ({p['ip_address']})", "group": "peer", "ip": p["ip_address"]})

        return {
            "enabled": True,
            "running": self.running,
            "local_peer": self.local_peer.to_dict(),
            "total_peers": len(self.peers),
            "online_peers": len(alive_peers),
            "peers": alive_peers,
            "messages_sent": self.stats["messages_sent"],
            "messages_received": self.stats["messages_received"],
            "gossip_relays": self.stats["gossip_relays"],
            "bft_rounds": len(bft_proposals),
            "bft_proposals": bft_proposals,
            "tasks_offloaded": self.stats["tasks_offloaded"],
            "offloaded_tasks": tasks,
            "gossip_health": 1.0 if self.running else 0.0,
            "recent_messages": list(self._recent_msg_history)[-15:],
            "network_topology": topology,
        }

    def get_status(self) -> Dict[str, Any]:
        return self.get_swarm_stats()

    def get_summary(self) -> str:
        stats = self.get_swarm_stats()
        lines = [
            f"P2P Mesh Network: {'Active' if stats['running'] else 'Offline'}",
            f"Local Node ID: {self.local_peer.peer_id} ({self.local_peer.ip_address}:{self.local_peer.port})",
            f"Discovered Peers: {stats['online_peers']} online / {stats['total_peers']} total",
            f"Swarm Traffic: {stats['messages_sent']} sent, {stats['messages_received']} recv, {stats['gossip_relays']} gossip relays",
            f"BFT Active Proposals: {stats['bft_rounds']}",
            f"Distributed Tasks: {stats['tasks_offloaded']} offloaded",
        ]
        if stats["peers"]:
            plist = [f"{p['peer_id']}@{p['ip_address']}" for p in stats["peers"][:4]]
            lines.append(f"Connected Peers: {', '.join(plist)}")
        return "\n".join(lines)

# Singleton instance accessor
p2p_swarm = P2PSwarm()

def get_p2p_swarm() -> P2PSwarm:
    """Get the singleton P2PSwarm instance."""
    return p2p_swarm
