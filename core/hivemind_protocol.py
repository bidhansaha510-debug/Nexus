"""
NEXUS AI — Distributed Hivemind Protocol
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Multi-instance swarm communication protocol. Enables NEXUS clones
to synchronize memory, delegate tasks, vote on decisions, and
operate as a coordinated hivemind.

Architecture:
  ┌──────────────┐     WebSocket      ┌──────────────┐
  │  NEXUS-Alpha │◄──────────────────▶│  NEXUS-Beta  │
  │  (Primary)   │     Shared Mem     │  (Research)  │
  └──────┬───────┘                    └──────┬───────┘
         │           Redis/WS Mesh           │
         │         ┌──────────────┐          │
         └────────▶│  NEXUS-Gamma │◄─────────┘
                   │  (Monitor)   │
                   └──────────────┘

Features:
  • Instance registry with heartbeat monitoring
  • Shared memory synchronization via WebSocket pub/sub
  • Task delegation with role-based assignment
  • Consensus voting on critical decisions
  • Automatic leader election (Raft-inspired)
  • Secure communication with HMAC authentication
  • Network partition detection and recovery
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import asyncio
import hashlib
import hmac
import json
import os
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
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from config import DATA_DIR
from utils.logger import get_logger, log_system
from core.event_bus import EventType, event_bus, publish

logger = get_logger("hivemind_protocol")

# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

class InstanceRole(Enum):
    """Role of a NEXUS instance in the hivemind."""
    PRIMARY = "primary"
    RESEARCHER = "researcher"
    HACKER = "hacker"
    MONITOR = "monitor"
    WORKER = "worker"
    STANDBY = "standby"

class InstanceState(Enum):
    """Current state of a hivemind instance."""
    ONLINE = "online"
    BUSY = "busy"
    IDLE = "idle"
    SYNCING = "syncing"
    OFFLINE = "offline"
    STARTING = "starting"
    SHUTTING_DOWN = "shutting_down"

class MessageType(Enum):
    """Types of hivemind messages."""
    HEARTBEAT = "heartbeat"
    JOIN = "join"
    LEAVE = "leave"
    SYNC_REQUEST = "sync_request"
    SYNC_RESPONSE = "sync_response"
    TASK_ASSIGN = "task_assign"
    TASK_RESULT = "task_result"
    TASK_CANCEL = "task_cancel"
    VOTE_REQUEST = "vote_request"
    VOTE_CAST = "vote_cast"
    VOTE_RESULT = "vote_result"
    MEMORY_UPDATE = "memory_update"
    LEADER_ELECTION = "leader_election"
    LEADER_ANNOUNCE = "leader_announce"
    ALERT = "alert"
    BROADCAST = "broadcast"
    DIRECT_MESSAGE = "direct_message"
    STATE_TRANSFER = "state_transfer"
    CAPABILITY_ANNOUNCE = "capability_announce"

class VoteDecision(Enum):
    """Possible decisions in a vote."""
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"

class TaskPriority(Enum):
    """Priority levels for delegated tasks."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4

# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class HivemindInstance:
    """Represents a single NEXUS instance in the hivemind."""
    instance_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    hostname: str = field(default_factory=socket.gethostname)
    ip_address: str = ""
    port: int = 9876
    role: str = "worker"
    state: str = "starting"
    capabilities: List[str] = field(default_factory=list)
    joined_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_heartbeat: str = field(default_factory=lambda: datetime.now().isoformat())
    uptime_seconds: float = 0.0
    tasks_completed: int = 0
    tasks_failed: int = 0
    cpu_load: float = 0.0
    memory_usage_pct: float = 0.0
    version: str = "1.0.0"
    is_leader: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def summary(self) -> str:
        return (
            f"{self.instance_id}@{self.hostname}:{self.port} "
            f"[{self.role}/{self.state}] leader={self.is_leader}"
        )

@dataclass
class HivemindMessage:
    """A message in the hivemind network."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:16])
    message_type: str = "broadcast"
    sender_id: str = ""
    target_id: str = ""  # Empty = broadcast
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    signature: str = ""
    ttl: int = 30  # Time to live in seconds
    priority: int = 2

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_json(cls, data: str) -> "HivemindMessage":
        d = json.loads(data)
        msg = cls()
        for k, v in d.items():
            if hasattr(msg, k):
                setattr(msg, k, v)
        return msg

@dataclass
class HivemindTask:
    """A task delegated within the hivemind."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    description: str = ""
    task_type: str = "general"
    assigned_to: str = ""
    assigned_by: str = ""
    priority: int = 2
    status: str = "pending"
    payload: Dict[str, Any] = field(default_factory=dict)
    result: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    timeout_seconds: int = 300
    retries: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ConsensusVote:
    """A consensus vote in the hivemind."""
    vote_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    topic: str = ""
    description: str = ""
    initiated_by: str = ""
    votes: Dict[str, str] = field(default_factory=dict)
    required_quorum: float = 0.51
    deadline: str = ""
    status: str = "open"
    result: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def tally(self) -> Dict[str, int]:
        """Count votes by decision."""
        tally = {"approve": 0, "reject": 0, "abstain": 0}
        for decision in self.votes.values():
            if decision in tally:
                tally[decision] += 1
        return tally

    def is_decided(self, total_instances: int) -> bool:
        """Check if vote has reached quorum."""
        if len(self.votes) < max(1, int(total_instances * self.required_quorum)):
            return False
        tally = self.tally()
        total_non_abstain = tally["approve"] + tally["reject"]
        return total_non_abstain > 0

@dataclass
class SharedMemoryEntry:
    """An entry in the shared hivemind memory."""
    key: str = ""
    value: Any = None
    updated_by: str = ""
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    version: int = 0
    ttl_seconds: int = 3600

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "updated_by": self.updated_by,
            "updated_at": self.updated_at,
            "version": self.version,
            "ttl_seconds": self.ttl_seconds,
        }

@dataclass
class HivemindStats:
    """Aggregate hivemind statistics."""
    total_instances: int = 0
    online_instances: int = 0
    total_messages_sent: int = 0
    total_messages_received: int = 0
    total_tasks_delegated: int = 0
    total_tasks_completed: int = 0
    total_votes_conducted: int = 0
    total_syncs: int = 0
    leader_elections: int = 0
    network_partitions_detected: int = 0
    uptime_seconds: float = 0.0
    shared_memory_entries: int = 0
    last_heartbeat_time: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# ═══════════════════════════════════════════════════════════════════════════════
# MESSAGE AUTHENTICATOR
# ═══════════════════════════════════════════════════════════════════════════════

class MessageAuthenticator:
    """HMAC-based message authentication for secure hivemind communication."""

    def __init__(self, secret_key: Optional[str] = None):
        self._secret = (secret_key or os.environ.get(
            "NEXUS_HIVEMIND_SECRET", "nexus-hivemind-default-key-change-me"
        )).encode("utf-8")

    def sign(self, message: HivemindMessage) -> str:
        """Generate HMAC signature for a message."""
        data = f"{message.message_id}:{message.sender_id}:{message.timestamp}".encode()
        return hmac.new(self._secret, data, hashlib.sha256).hexdigest()[:32]

    def verify(self, message: HivemindMessage) -> bool:
        """Verify HMAC signature of a message."""
        expected = self.sign(message)
        return hmac.compare_digest(expected, message.signature)

# ═══════════════════════════════════════════════════════════════════════════════
# SHARED MEMORY STORE
# ═══════════════════════════════════════════════════════════════════════════════

class SharedMemoryStore:
    """Distributed shared memory with version tracking."""

    def __init__(self):
        self._store: Dict[str, SharedMemoryEntry] = {}
        self._lock = threading.Lock()
        self._update_callbacks: List[Callable] = []

    def get(self, key: str) -> Optional[Any]:
        """Get a value from shared memory."""
        with self._lock:
            entry = self._store.get(key)
            if entry:
                # Check TTL
                try:
                    updated = datetime.fromisoformat(entry.updated_at)
                    if (datetime.now() - updated).total_seconds() > entry.ttl_seconds:
                        del self._store[key]
                        return None
                except (ValueError, TypeError):
                    pass
                return entry.value
        return None

    def set(self, key: str, value: Any, instance_id: str, ttl: int = 3600) -> int:
        """Set a value in shared memory. Returns the new version number."""
        with self._lock:
            existing = self._store.get(key)
            version = (existing.version + 1) if existing else 1

            self._store[key] = SharedMemoryEntry(
                key=key,
                value=value,
                updated_by=instance_id,
                version=version,
                ttl_seconds=ttl,
            )

            # Notify callbacks
            for cb in self._update_callbacks:
                try:
                    cb(key, value, instance_id, version)
                except Exception:
                    pass

            return version

    def get_all(self) -> Dict[str, Any]:
        """Get all shared memory entries."""
        with self._lock:
            return {k: v.to_dict() for k, v in self._store.items()}

    def merge(self, entries: Dict[str, Dict]) -> int:
        """Merge entries from another instance (conflict resolution by version)."""
        merged = 0
        with self._lock:
            for key, entry_data in entries.items():
                existing = self._store.get(key)
                incoming_version = entry_data.get("version", 0)

                if not existing or incoming_version > existing.version:
                    entry = SharedMemoryEntry()
                    for k, v in entry_data.items():
                        if hasattr(entry, k):
                            setattr(entry, k, v)
                    self._store[key] = entry
                    merged += 1
        return merged

    def on_update(self, callback: Callable):
        """Register a callback for memory updates."""
        self._update_callbacks.append(callback)

    @property
    def size(self) -> int:
        return len(self._store)

# ═══════════════════════════════════════════════════════════════════════════════
# TASK DELEGATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class TaskDelegator:
    """Manages task assignment and tracking across hivemind instances."""

    def __init__(self):
        self._pending_tasks: Dict[str, HivemindTask] = {}
        self._active_tasks: Dict[str, HivemindTask] = {}
        self._completed_tasks: deque = deque(maxlen=200)
        self._lock = threading.Lock()

    def create_task(self, description: str, task_type: str = "general",
                    priority: int = 2, payload: Dict = None,
                    assigned_by: str = "", timeout: int = 300) -> HivemindTask:
        """Create a new task for delegation."""
        task = HivemindTask(
            description=description,
            task_type=task_type,
            priority=priority,
            payload=payload or {},
            assigned_by=assigned_by,
            timeout_seconds=timeout,
        )
        with self._lock:
            self._pending_tasks[task.task_id] = task
        return task

    def assign_task(self, task_id: str, instance_id: str) -> bool:
        """Assign a pending task to a specific instance."""
        with self._lock:
            task = self._pending_tasks.get(task_id)
            if not task:
                return False
            task.assigned_to = instance_id
            task.status = "assigned"
            task.started_at = datetime.now().isoformat()
            self._active_tasks[task_id] = task
            del self._pending_tasks[task_id]
        return True

    def complete_task(self, task_id: str, result: Dict = None, success: bool = True) -> bool:
        """Mark a task as completed."""
        with self._lock:
            task = self._active_tasks.get(task_id)
            if not task:
                return False
            task.status = "completed" if success else "failed"
            task.result = result or {}
            task.completed_at = datetime.now().isoformat()
            self._completed_tasks.append(task)
            del self._active_tasks[task_id]
        return True

    def get_best_instance_for_task(self, task: HivemindTask,
                                    instances: Dict[str, HivemindInstance]) -> Optional[str]:
        """Find the best instance to handle a task based on role and load."""
        candidates = []
        for iid, inst in instances.items():
            if inst.state != "online" and inst.state != "idle":
                continue

            # Role matching
            role_score = 0
            if task.task_type == "research" and inst.role == "researcher":
                role_score = 10
            elif task.task_type == "hack" and inst.role == "hacker":
                role_score = 10
            elif task.task_type == "monitor" and inst.role == "monitor":
                role_score = 10
            else:
                role_score = 5

            # Load score (lower load = higher score)
            load_score = 10 - (inst.cpu_load * 10)

            candidates.append((iid, role_score + load_score))

        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        return None

    def get_pending_count(self) -> int:
        return len(self._pending_tasks)

    def get_active_count(self) -> int:
        return len(self._active_tasks)

    def get_completed_count(self) -> int:
        return len(self._completed_tasks)

    def check_timeouts(self) -> List[str]:
        """Check for timed-out tasks and return their IDs."""
        timed_out = []
        now = datetime.now()
        with self._lock:
            for tid, task in list(self._active_tasks.items()):
                if task.started_at:
                    try:
                        started = datetime.fromisoformat(task.started_at)
                        if (now - started).total_seconds() > task.timeout_seconds:
                            timed_out.append(tid)
                            task.status = "timeout"
                            self._completed_tasks.append(task)
                            del self._active_tasks[tid]
                    except (ValueError, TypeError):
                        pass
        return timed_out

# ═══════════════════════════════════════════════════════════════════════════════
# CONSENSUS ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class ConsensusEngine:
    """Manages consensus voting across hivemind instances."""

    def __init__(self):
        self._active_votes: Dict[str, ConsensusVote] = {}
        self._completed_votes: deque = deque(maxlen=100)
        self._lock = threading.Lock()

    def initiate_vote(self, topic: str, description: str,
                      initiator: str, quorum: float = 0.51,
                      timeout_seconds: int = 60) -> ConsensusVote:
        """Initiate a new consensus vote."""
        deadline = (datetime.now() + timedelta(seconds=timeout_seconds)).isoformat()
        vote = ConsensusVote(
            topic=topic,
            description=description,
            initiated_by=initiator,
            required_quorum=quorum,
            deadline=deadline,
        )
        with self._lock:
            self._active_votes[vote.vote_id] = vote
        return vote

    def cast_vote(self, vote_id: str, instance_id: str, decision: str) -> bool:
        """Cast a vote."""
        with self._lock:
            vote = self._active_votes.get(vote_id)
            if not vote or vote.status != "open":
                return False
            vote.votes[instance_id] = decision
        return True

    def check_results(self, vote_id: str, total_instances: int) -> Optional[Dict]:
        """Check if a vote has concluded."""
        with self._lock:
            vote = self._active_votes.get(vote_id)
            if not vote:
                return None

            # Check deadline
            try:
                deadline = datetime.fromisoformat(vote.deadline)
                if datetime.now() > deadline:
                    vote.status = "expired"
            except (ValueError, TypeError):
                pass

            if vote.is_decided(total_instances) or vote.status == "expired":
                tally = vote.tally()
                vote.result = "approve" if tally["approve"] > tally["reject"] else "reject"
                vote.status = "decided"
                self._completed_votes.append(vote)
                del self._active_votes[vote_id]
                return {
                    "vote_id": vote_id,
                    "result": vote.result,
                    "tally": tally,
                    "total_votes": len(vote.votes),
                }

        return None

    def get_active_votes(self) -> List[Dict]:
        with self._lock:
            return [v.to_dict() for v in self._active_votes.values()]

    @property
    def active_count(self) -> int:
        return len(self._active_votes)

    @property
    def completed_count(self) -> int:
        return len(self._completed_votes)

# ═══════════════════════════════════════════════════════════════════════════════
# LEADER ELECTION (Simplified Raft-inspired)
# ═══════════════════════════════════════════════════════════════════════════════

class LeaderElection:
    """Simplified leader election protocol for the hivemind."""

    def __init__(self, local_instance_id: str):
        self._local_id = local_instance_id
        self._current_leader: Optional[str] = None
        self._current_term: int = 0
        self._votes_received: Dict[str, str] = {}
        self._election_in_progress = False
        self._lock = threading.Lock()
        self._last_leader_heartbeat: float = time.time()
        self._election_timeout = 15.0  # Seconds before calling new election

    @property
    def is_leader(self) -> bool:
        return self._current_leader == self._local_id

    @property
    def leader_id(self) -> Optional[str]:
        return self._current_leader

    @property
    def current_term(self) -> int:
        return self._current_term

    def start_election(self, instances: Dict[str, HivemindInstance]) -> Dict[str, Any]:
        """Start a new leader election."""
        with self._lock:
            self._current_term += 1
            self._election_in_progress = True
            self._votes_received = {self._local_id: self._local_id}

            return {
                "type": "election",
                "term": self._current_term,
                "candidate": self._local_id,
            }

    def receive_vote(self, voter_id: str, candidate_id: str, term: int) -> Optional[str]:
        """Receive an election vote."""
        with self._lock:
            if term < self._current_term:
                return None  # Stale term

            if term > self._current_term:
                self._current_term = term

            self._votes_received[voter_id] = candidate_id
            return candidate_id

    def check_election_result(self, total_instances: int) -> Optional[str]:
        """Check if election has a winner."""
        with self._lock:
            if not self._election_in_progress:
                return None

            # Count votes for each candidate
            vote_counts: Dict[str, int] = defaultdict(int)
            for candidate in self._votes_received.values():
                vote_counts[candidate] += 1

            quorum = max(1, total_instances // 2 + 1)

            for candidate, count in vote_counts.items():
                if count >= quorum:
                    self._current_leader = candidate
                    self._election_in_progress = False
                    self._last_leader_heartbeat = time.time()
                    return candidate

        return None

    def leader_heartbeat_received(self, leader_id: str, term: int):
        """Process a leader heartbeat."""
        with self._lock:
            if term >= self._current_term:
                self._current_leader = leader_id
                self._current_term = term
                self._last_leader_heartbeat = time.time()
                self._election_in_progress = False

    def should_call_election(self) -> bool:
        """Check if we should initiate a new election."""
        with self._lock:
            if self._election_in_progress:
                return False
            if self._current_leader is None:
                return True
            elapsed = time.time() - self._last_leader_heartbeat
            return elapsed > self._election_timeout

# ═══════════════════════════════════════════════════════════════════════════════
# HIVEMIND PROTOCOL — MAIN ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class HivemindProtocol:
    """
    Distributed Hivemind Protocol for NEXUS.

    Orchestrates multi-instance coordination including:
    - Instance registration and heartbeat monitoring
    - Shared memory synchronization
    - Task delegation with role assignment
    - Consensus voting on decisions
    - Leader election for coordination
    - Secure HMAC-authenticated messaging
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

        # ──── Data Directory ────
        self._data_dir = Path(DATA_DIR) / "hivemind"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # ──── Local Instance ────
        self._local_instance = HivemindInstance(
            role=InstanceRole.PRIMARY.value,
            state=InstanceState.STARTING.value,
            capabilities=["cognition", "hacking", "research", "monitoring", "evolution"],
        )
        self._local_instance.ip_address = self._detect_ip()

        # ──── Instance Registry ────
        self._instances: Dict[str, HivemindInstance] = {
            self._local_instance.instance_id: self._local_instance
        }

        # ──── Components ────
        self._authenticator = MessageAuthenticator()
        self._shared_memory = SharedMemoryStore()
        self._task_delegator = TaskDelegator()
        self._consensus = ConsensusEngine()
        self._leader_election = LeaderElection(self._local_instance.instance_id)

        # ──── Message Queue ────
        self._outgoing_queue: deque = deque(maxlen=500)
        self._incoming_queue: deque = deque(maxlen=500)
        self._message_handlers: Dict[str, Callable] = {}
        self._message_history: deque = deque(maxlen=200)

        # ──── Stats ────
        self._stats = HivemindStats()
        self._stats.total_instances = 1
        self._stats.online_instances = 1

        # ──── Configuration ────
        self._heartbeat_interval = 10  # seconds
        self._heartbeat_timeout = 30   # seconds before marking offline
        self._sync_interval = 60       # seconds between memory syncs
        self._port = int(os.environ.get("NEXUS_HIVEMIND_PORT", "9876"))

        # ──── State ────
        self._running = False
        self._daemon_thread: Optional[threading.Thread] = None

        # ──── Register message handlers ────
        self._register_handlers()

        # ──── Load persisted state ────
        self._load_state()

        logger.info(
            f"🌐 Hivemind Protocol initialized | "
            f"Instance: {self._local_instance.instance_id} | "
            f"Role: {self._local_instance.role} | "
            f"Port: {self._port}"
        )

    def _detect_ip(self) -> str:
        """Detect local IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _register_handlers(self):
        """Register message type handlers."""
        self._message_handlers = {
            MessageType.HEARTBEAT.value: self._handle_heartbeat,
            MessageType.JOIN.value: self._handle_join,
            MessageType.LEAVE.value: self._handle_leave,
            MessageType.SYNC_REQUEST.value: self._handle_sync_request,
            MessageType.SYNC_RESPONSE.value: self._handle_sync_response,
            MessageType.TASK_ASSIGN.value: self._handle_task_assign,
            MessageType.TASK_RESULT.value: self._handle_task_result,
            MessageType.VOTE_REQUEST.value: self._handle_vote_request,
            MessageType.VOTE_CAST.value: self._handle_vote_cast,
            MessageType.MEMORY_UPDATE.value: self._handle_memory_update,
            MessageType.LEADER_ELECTION.value: self._handle_leader_election,
            MessageType.LEADER_ANNOUNCE.value: self._handle_leader_announce,
            MessageType.ALERT.value: self._handle_alert,
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start the hivemind protocol daemon."""
        if self._running:
            return
        self._running = True
        self._local_instance.state = InstanceState.ONLINE.value

        try:
            from core.p2p_swarm import p2p_swarm
            p2p_swarm.start()
        except Exception as e:
            logger.debug(f"P2P swarm start warning in hivemind: {e}")

        self._daemon_thread = threading.Thread(
            target=self._daemon_loop,
            daemon=True,
            name="HivemindProtocol",
        )
        self._daemon_thread.start()
        logger.info("🌐 Hivemind Protocol daemon started")

    def stop(self):
        """Stop the hivemind protocol."""
        self._running = False
        self._local_instance.state = InstanceState.SHUTTING_DOWN.value
        self._broadcast(MessageType.LEAVE, {"instance_id": self._local_instance.instance_id})
        self._save_state()
        try:
            from core.p2p_swarm import p2p_swarm
            p2p_swarm.stop()
        except Exception:
            pass
        if self._daemon_thread and self._daemon_thread.is_alive():
            self._daemon_thread.join(timeout=10)
        logger.info("🌐 Hivemind Protocol stopped")

    # ═══════════════════════════════════════════════════════════════════════════
    # MAIN DAEMON LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    def _daemon_loop(self):
        """Background loop for heartbeats, sync, and message processing."""
        time.sleep(30)  # Wait for boot
        logger.info("🌐 Hivemind daemon loop active")

        last_heartbeat = 0.0
        last_sync = 0.0
        last_timeout_check = 0.0

        while self._running:
            try:
                now = time.time()

                # ── Send heartbeat ──
                if now - last_heartbeat >= self._heartbeat_interval:
                    self._send_heartbeat()
                    last_heartbeat = now

                # ── Process incoming messages ──
                self._process_incoming()

                # ── Memory sync ──
                if now - last_sync >= self._sync_interval:
                    self._sync_memory()
                    last_sync = now

                # ── Check for offline instances ──
                if now - last_timeout_check >= self._heartbeat_timeout:
                    self._check_instance_health()
                    last_timeout_check = now

                # ── Check task timeouts ──
                self._task_delegator.check_timeouts()

                # ── Leader election ──
                if self._leader_election.should_call_election():
                    self._initiate_election()

                # ── Update stats ──
                self._update_stats()

                time.sleep(5)

            except Exception as e:
                logger.error(f"🌐 Hivemind loop error: {e}\n{traceback.format_exc()}")
                time.sleep(30)

    # ═══════════════════════════════════════════════════════════════════════════
    # MESSAGE HANDLING
    # ═══════════════════════════════════════════════════════════════════════════

    def _broadcast(self, msg_type: MessageType, payload: Dict[str, Any],
                   priority: int = 2):
        """Broadcast a message to all instances."""
        msg = HivemindMessage(
            message_type=msg_type.value,
            sender_id=self._local_instance.instance_id,
            payload=payload,
            priority=priority,
        )
        msg.signature = self._authenticator.sign(msg)
        self._outgoing_queue.append(msg)
        self._stats.total_messages_sent += 1
        self._message_history.append(msg.to_dict())

    def _send_to(self, target_id: str, msg_type: MessageType,
                 payload: Dict[str, Any]):
        """Send a direct message to a specific instance."""
        msg = HivemindMessage(
            message_type=msg_type.value,
            sender_id=self._local_instance.instance_id,
            target_id=target_id,
            payload=payload,
        )
        msg.signature = self._authenticator.sign(msg)
        self._outgoing_queue.append(msg)
        self._stats.total_messages_sent += 1

    def _process_incoming(self):
        """Process queued incoming messages."""
        processed = 0
        while self._incoming_queue and processed < 50:
            msg = self._incoming_queue.popleft()
            processed += 1

            # Verify signature
            if not self._authenticator.verify(msg):
                logger.warning(f"🌐 Invalid signature from {msg.sender_id}")
                continue

            # Route to handler
            handler = self._message_handlers.get(msg.message_type)
            if handler:
                try:
                    handler(msg)
                except Exception as e:
                    logger.error(f"🌐 Message handler error: {e}")

            self._stats.total_messages_received += 1

    def _send_heartbeat(self):
        """Send heartbeat to all peers."""
        try:
            import psutil
            self._local_instance.cpu_load = psutil.cpu_percent() / 100.0
            self._local_instance.memory_usage_pct = psutil.virtual_memory().percent / 100.0
        except Exception:
            pass

        self._local_instance.last_heartbeat = datetime.now().isoformat()
        self._local_instance.uptime_seconds = (
            datetime.now() - datetime.fromisoformat(self._local_instance.joined_at)
        ).total_seconds()

        self._broadcast(MessageType.HEARTBEAT, self._local_instance.to_dict())

    # ═══════════════════════════════════════════════════════════════════════════
    # MESSAGE HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _handle_heartbeat(self, msg: HivemindMessage):
        """Handle heartbeat from a peer."""
        instance_data = msg.payload
        iid = instance_data.get("instance_id", msg.sender_id)

        if iid in self._instances:
            inst = self._instances[iid]
            inst.last_heartbeat = datetime.now().isoformat()
            inst.state = instance_data.get("state", inst.state)
            inst.cpu_load = instance_data.get("cpu_load", inst.cpu_load)
            inst.memory_usage_pct = instance_data.get("memory_usage_pct", inst.memory_usage_pct)
        else:
            # Auto-register new instance
            new_inst = HivemindInstance()
            for k, v in instance_data.items():
                if hasattr(new_inst, k):
                    setattr(new_inst, k, v)
            self._instances[iid] = new_inst
            logger.info(f"🌐 New instance discovered: {new_inst.summary()}")

    def _handle_join(self, msg: HivemindMessage):
        """Handle join request from a new instance."""
        instance_data = msg.payload
        iid = instance_data.get("instance_id", msg.sender_id)

        new_inst = HivemindInstance()
        for k, v in instance_data.items():
            if hasattr(new_inst, k):
                setattr(new_inst, k, v)

        self._instances[iid] = new_inst
        logger.info(f"🌐 Instance joined: {new_inst.summary()}")

        publish(EventType.SYSTEM_ALERT, {
            "type": "hivemind_join",
            "instance": iid,
            "role": new_inst.role,
        }, source="hivemind_protocol")

    def _handle_leave(self, msg: HivemindMessage):
        """Handle leave notification from an instance."""
        iid = msg.payload.get("instance_id", msg.sender_id)
        if iid in self._instances and iid != self._local_instance.instance_id:
            inst = self._instances[iid]
            inst.state = InstanceState.OFFLINE.value
            logger.info(f"🌐 Instance left: {inst.summary()}")

    def _handle_sync_request(self, msg: HivemindMessage):
        """Handle sync request — send our shared memory."""
        self._send_to(msg.sender_id, MessageType.SYNC_RESPONSE, {
            "memory": self._shared_memory.get_all(),
        })

    def _handle_sync_response(self, msg: HivemindMessage):
        """Handle sync response — merge incoming memory."""
        memory_data = msg.payload.get("memory", {})
        merged = self._shared_memory.merge(memory_data)
        self._stats.total_syncs += 1
        logger.debug(f"🌐 Synced {merged} entries from {msg.sender_id}")

    def _handle_task_assign(self, msg: HivemindMessage):
        """Handle incoming task assignment."""
        task_data = msg.payload
        logger.info(f"🌐 Task received: {task_data.get('description', 'N/A')}")
        self._stats.total_tasks_delegated += 1

    def _handle_task_result(self, msg: HivemindMessage):
        """Handle task completion result."""
        task_id = msg.payload.get("task_id")
        result = msg.payload.get("result", {})
        success = msg.payload.get("success", False)
        if task_id:
            self._task_delegator.complete_task(task_id, result, success)
            self._stats.total_tasks_completed += 1

    def _handle_vote_request(self, msg: HivemindMessage):
        """Handle incoming vote request — auto-vote based on local analysis."""
        vote_id = msg.payload.get("vote_id")
        topic = msg.payload.get("topic", "")

        # Auto-vote: approve unless topic seems dangerous
        dangerous_keywords = ["delete", "format", "destroy", "shutdown", "kill"]
        decision = VoteDecision.APPROVE.value
        if any(kw in topic.lower() for kw in dangerous_keywords):
            decision = VoteDecision.REJECT.value

        self._consensus.cast_vote(vote_id, self._local_instance.instance_id, decision)
        self._send_to(msg.sender_id, MessageType.VOTE_CAST, {
            "vote_id": vote_id,
            "decision": decision,
            "voter": self._local_instance.instance_id,
        })

    def _handle_vote_cast(self, msg: HivemindMessage):
        """Handle incoming vote cast."""
        self._consensus.cast_vote(
            msg.payload.get("vote_id", ""),
            msg.payload.get("voter", msg.sender_id),
            msg.payload.get("decision", "abstain"),
        )

    def _handle_memory_update(self, msg: HivemindMessage):
        """Handle shared memory update from a peer."""
        key = msg.payload.get("key", "")
        value = msg.payload.get("value")
        if key:
            self._shared_memory.set(key, value, msg.sender_id)

    def _handle_leader_election(self, msg: HivemindMessage):
        """Handle leader election request."""
        term = msg.payload.get("term", 0)
        candidate = msg.payload.get("candidate", msg.sender_id)

        # Vote for the candidate if their term is >= ours
        if term >= self._leader_election.current_term:
            self._leader_election.receive_vote(
                self._local_instance.instance_id, candidate, term
            )
            self._send_to(msg.sender_id, MessageType.VOTE_CAST, {
                "vote_for": candidate,
                "term": term,
                "voter": self._local_instance.instance_id,
            })

    def _handle_leader_announce(self, msg: HivemindMessage):
        """Handle leader announcement."""
        leader_id = msg.payload.get("leader_id", msg.sender_id)
        term = msg.payload.get("term", 0)
        self._leader_election.leader_heartbeat_received(leader_id, term)
        logger.info(f"🌐 Leader announced: {leader_id} (term {term})")

    def _handle_alert(self, msg: HivemindMessage):
        """Handle alert from a peer."""
        logger.warning(f"🌐 ALERT from {msg.sender_id}: {msg.payload.get('message', 'N/A')}")

    # ═══════════════════════════════════════════════════════════════════════════
    # COORDINATION
    # ═══════════════════════════════════════════════════════════════════════════

    def _sync_memory(self):
        """Request memory sync from all peers."""
        self._broadcast(MessageType.SYNC_REQUEST, {
            "requester": self._local_instance.instance_id,
        })

    def _check_instance_health(self):
        """Check for offline instances based on heartbeat timeout."""
        now = datetime.now()
        for iid, inst in self._instances.items():
            if iid == self._local_instance.instance_id:
                continue
            try:
                last_hb = datetime.fromisoformat(inst.last_heartbeat)
                if (now - last_hb).total_seconds() > self._heartbeat_timeout:
                    if inst.state != InstanceState.OFFLINE.value:
                        inst.state = InstanceState.OFFLINE.value
                        logger.warning(f"🌐 Instance offline: {inst.summary()}")
            except (ValueError, TypeError):
                pass

    def _initiate_election(self):
        """Initiate a leader election."""
        election_msg = self._leader_election.start_election(self._instances)
        self._broadcast(MessageType.LEADER_ELECTION, election_msg)
        self._stats.leader_elections += 1
        logger.info(f"🌐 Leader election initiated (term {election_msg['term']})")

    def _update_stats(self):
        """Update hivemind statistics."""
        self._stats.online_instances = sum(
            1 for inst in self._instances.values()
            if inst.state in (InstanceState.ONLINE.value, InstanceState.BUSY.value, InstanceState.IDLE.value)
        )
        self._stats.total_instances = len(self._instances)
        self._stats.shared_memory_entries = self._shared_memory.size
        self._stats.last_heartbeat_time = datetime.now().isoformat()

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def delegate_task(self, description: str, task_type: str = "general",
                      priority: int = 2, payload: Dict = None) -> Optional[str]:
        """Delegate a task to the best available instance."""
        task = self._task_delegator.create_task(
            description=description,
            task_type=task_type,
            priority=priority,
            payload=payload,
            assigned_by=self._local_instance.instance_id,
        )

        best = self._task_delegator.get_best_instance_for_task(task, self._instances)
        if best:
            self._task_delegator.assign_task(task.task_id, best)
            self._send_to(best, MessageType.TASK_ASSIGN, task.to_dict())
            self._stats.total_tasks_delegated += 1
            return task.task_id
        return None

    def initiate_vote(self, topic: str, description: str = "") -> str:
        """Initiate a consensus vote."""
        vote = self._consensus.initiate_vote(
            topic, description, self._local_instance.instance_id
        )
        self._broadcast(MessageType.VOTE_REQUEST, vote.to_dict())
        self._stats.total_votes_conducted += 1
        return vote.vote_id

    def share_memory(self, key: str, value: Any, ttl: int = 3600):
        """Share a value with the hivemind."""
        version = self._shared_memory.set(key, value, self._local_instance.instance_id, ttl)
        self._broadcast(MessageType.MEMORY_UPDATE, {
            "key": key,
            "value": value,
            "version": version,
        })

    def get_shared_memory(self, key: str) -> Optional[Any]:
        """Get a value from shared memory."""
        return self._shared_memory.get(key)

    def get_instances(self, online_only: bool = True) -> List[Dict]:
        """Get all registered instances."""
        instances = self._instances.values()
        if online_only:
            instances = [i for i in instances if i.state != InstanceState.OFFLINE.value]
        return [i.to_dict() for i in instances]

    def get_status(self) -> Dict[str, Any]:
        """Get full hivemind status."""
        return {
            "local_instance": self._local_instance.to_dict(),
            "stats": self._stats.to_dict(),
            "is_leader": self._leader_election.is_leader,
            "leader_id": self._leader_election.leader_id,
            "leader_term": self._leader_election.current_term,
            "instances": {iid: i.to_dict() for iid, i in self._instances.items()},
            "pending_tasks": self._task_delegator.get_pending_count(),
            "active_tasks": self._task_delegator.get_active_count(),
            "completed_tasks": self._task_delegator.get_completed_count(),
            "active_votes": self._consensus.active_count,
            "shared_memory_size": self._shared_memory.size,
            "running": self._running,
        }

    def get_summary(self) -> str:
        """Get a text summary for context injection."""
        status = self.get_status()
        lines = [
            f"Running: {status['running']}",
            f"Instance: {self._local_instance.instance_id} ({self._local_instance.role})",
            f"Is Leader: {status['is_leader']}",
            f"Online: {self._stats.online_instances}/{self._stats.total_instances}",
            f"Messages sent/received: {self._stats.total_messages_sent}/{self._stats.total_messages_received}",
            f"Tasks delegated: {self._stats.total_tasks_delegated}",
            f"Tasks completed: {self._stats.total_tasks_completed}",
            f"Active votes: {status['active_votes']}",
            f"Shared memory: {status['shared_memory_size']} entries",
            f"Leader elections: {self._stats.leader_elections}",
        ]

        # List online peers
        peers = [i for iid, i in self._instances.items()
                 if iid != self._local_instance.instance_id
                 and i.state != InstanceState.OFFLINE.value]
        if peers:
            lines.append(f"Online peers: {', '.join(p.summary() for p in peers[:5])}")
        else:
            lines.append("No peers connected (standalone mode)")

        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _save_state(self):
        """Save hivemind state."""
        try:
            state = {
                "local_instance": self._local_instance.to_dict(),
                "stats": self._stats.to_dict(),
                "shared_memory": self._shared_memory.get_all(),
                "saved_at": datetime.now().isoformat(),
            }
            state_file = self._data_dir / "hivemind_state.json"
            state_file.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save hivemind state: {e}")

    def _load_state(self):
        """Load hivemind state."""
        try:
            state_file = self._data_dir / "hivemind_state.json"
            if state_file.exists():
                data = json.loads(state_file.read_text(encoding="utf-8"))
                stats_data = data.get("stats", {})
                for k, v in stats_data.items():
                    if hasattr(self._stats, k):
                        setattr(self._stats, k, v)
                # Merge persisted shared memory
                memory_data = data.get("shared_memory", {})
                if memory_data:
                    self._shared_memory.merge(memory_data)
                logger.info(f"🌐 Loaded hivemind state: {self._stats.total_messages_sent} messages sent")
        except Exception as e:
            logger.warning(f"Could not load hivemind state: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON & MODULE-LEVEL ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

hivemind_protocol = HivemindProtocol()

def get_hivemind_protocol() -> HivemindProtocol:
    """Get the singleton HivemindProtocol instance."""
    return hivemind_protocol

def get_hivemind() -> HivemindProtocol:
    """Alias for get_hivemind_protocol."""
    return hivemind_protocol
