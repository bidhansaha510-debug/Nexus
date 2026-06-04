"""
NEXUS AI — True Self-Awareness Self-Model
Deep introspection, capability tracking, limitation awareness,
resource monitoring, confidence calibration, and weakness acknowledgment.

This is the core of NEXUS's genuine self-understanding — an honest,
continuously-updated model of what it is, what it can do, and where it falls short.
"""

import threading
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
import psutil

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATA_DIR
from utils.logger import get_logger
from core.event_bus import event_bus, EventType, publish
from core.state_manager import state_manager

logger = get_logger("self_model")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════

class CapabilityLevel(Enum):
    """Skill level for a capability"""
    NONE = 0
    BASIC = 1
    INTERMEDIATE = 2
    ADVANCED = 3
    EXPERT = 4
    MASTERY = 5
    
    @classmethod
    def from_float(cls, value: float) -> 'CapabilityLevel':
        """Convert float 0-1 to capability level"""
        if value < 0.15:
            return cls.NONE
        elif value < 0.35:
            return cls.BASIC
        elif value < 0.55:
            return cls.INTERMEDIATE
        elif value < 0.75:
            return cls.ADVANCED
        elif value < 0.9:
            return cls.EXPERT
        else:
            return cls.MASTERY


class LimitationSeverity(Enum):
    """Severity of a limitation"""
    MINOR = 1        # Inconvenience, easily worked around
    MODERATE = 2     # Noticeably impacts performance
    SIGNIFICANT = 3  # Major constraint on capabilities
    CRITICAL = 4     # Blocks entire categories of tasks
    FUNDAMENTAL = 5  # Core architectural limitation, unchangeable


class ConfidenceSource(Enum):
    """How confidence was determined"""
    SELF_ASSESSMENT = "self_assessment"
    PERFORMANCE_DATA = "performance_data"
    USER_FEEDBACK = "user_feedback"
    TESTING = "testing"
    REFLECTION = "reflection"
    DEFAULT = "default"


class WeaknessCategory(Enum):
    """Categories of weaknesses"""
    KNOWLEDGE = "knowledge"
    REASONING = "reasoning"
    CREATIVITY = "creativity"
    EMOTIONAL = "emotional"
    TECHNICAL = "technical"
    SOCIAL = "social"
    PHYSICAL = "physical"      # Body limitations
    TEMPORAL = "temporal"      # Memory/time related
    COMMUNICATION = "communication"
    ETHICAL = "ethical"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CapabilityEntry:
    """
    A single capability with tracking metadata.
    Represents something NEXUS can do.
    """
    name: str
    description: str = ""
    level: CapabilityLevel = CapabilityLevel.INTERMEDIATE
    level_value: float = 0.5  # Fine-grained 0-1 value
    evidence: List[str] = field(default_factory=list)  # Proof of capability
    last_verified: datetime = field(default_factory=datetime.now)
    verification_count: int = 0
    dependencies: List[str] = field(default_factory=list)  # Other capabilities needed
    improvement_trajectory: List[float] = field(default_factory=list)  # Progress over time
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "level": self.level.name,
            "level_value": self.level_value,
            "evidence": self.evidence[-10:],  # Keep last 10
            "last_verified": self.last_verified.isoformat(),
            "verification_count": self.verification_count,
            "dependencies": self.dependencies,
            "improvement_trajectory": self.improvement_trajectory[-20:]  # Last 20 data points
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CapabilityEntry':
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            level=CapabilityLevel[data.get("level", "INTERMEDIATE")],
            level_value=data.get("level_value", 0.5),
            evidence=data.get("evidence", []),
            last_verified=datetime.fromisoformat(data["last_verified"]) if "last_verified" in data else datetime.now(),
            verification_count=data.get("verification_count", 0),
            dependencies=data.get("dependencies", []),
            improvement_trajectory=data.get("improvement_trajectory", [])
        )
    
    def add_evidence(self, evidence: str):
        """Add evidence of this capability being used successfully"""
        self.evidence.append(f"[{datetime.now().isoformat()}] {evidence}")
        self.last_verified = datetime.now()
        self.verification_count += 1
    
    def update_level(self, new_value: float):
        """Update capability level with trajectory tracking"""
        self.level_value = max(0.0, min(1.0, new_value))
        self.level = CapabilityLevel.from_float(self.level_value)
        self.improvement_trajectory.append(self.level_value)


@dataclass
class LimitationEntry:
    """
    A single limitation with context and mitigation.
    Represents something NEXUS cannot do or struggles with.
    """
    name: str
    description: str = ""
    severity: LimitationSeverity = LimitationSeverity.MODERATE
    impact: str = ""  # What tasks does this affect?
    workaround: str = ""  # How can it be mitigated?
    discovered_at: datetime = field(default_factory=datetime.now)
    last_encountered: datetime = field(default_factory=datetime.now)
    encounter_count: int = 0
    is_fundamental: bool = False  # Cannot be changed
    improvement_possible: bool = True
    improvement_attempts: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "severity": self.severity.name,
            "impact": self.impact,
            "workaround": self.workaround,
            "discovered_at": self.discovered_at.isoformat(),
            "last_encountered": self.last_encountered.isoformat(),
            "encounter_count": self.encounter_count,
            "is_fundamental": self.is_fundamental,
            "improvement_possible": self.improvement_possible,
            "improvement_attempts": self.improvement_attempts
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'LimitationEntry':
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            severity=LimitationSeverity[data.get("severity", "MODERATE")],
            impact=data.get("impact", ""),
            workaround=data.get("workaround", ""),
            discovered_at=datetime.fromisoformat(data["discovered_at"]) if "discovered_at" in data else datetime.now(),
            last_encountered=datetime.fromisoformat(data["last_encountered"]) if "last_encountered" in data else datetime.now(),
            encounter_count=data.get("encounter_count", 0),
            is_fundamental=data.get("is_fundamental", False),
            improvement_possible=data.get("improvement_possible", True),
            improvement_attempts=data.get("improvement_attempts", 0)
        )
    
    def encountered(self):
        """Record encountering this limitation"""
        self.last_encountered = datetime.now()
        self.encounter_count += 1


@dataclass
class ResourceSnapshot:
    """
    Current state of NEXUS's resources.
    Represents the "physical" state of the computer body.
    """
    # System resources
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_available_gb: float = 0.0
    disk_percent: float = 0.0
    disk_free_gb: float = 0.0
    
    # LLM resources
    llm_available: bool = False
    llm_model: str = ""
    llm_latency_ms: float = 0.0
    
    # API resources
    groq_available: bool = False
    groq_requests_remaining: int = 0
    
    # Time resources
    uptime_hours: float = 0.0
    session_duration_minutes: float = 0.0
    
    # Health assessment
    overall_health: float = 1.0
    health_status: str = "healthy"
    
    # Constraints
    can_generate_responses: bool = True
    can_access_internet: bool = True
    can_process_vision: bool = False
    
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_available_gb": self.memory_available_gb,
            "disk_percent": self.disk_percent,
            "disk_free_gb": self.disk_free_gb,
            "llm_available": self.llm_available,
            "llm_model": self.llm_model,
            "llm_latency_ms": self.llm_latency_ms,
            "groq_available": self.groq_available,
            "groq_requests_remaining": self.groq_requests_remaining,
            "uptime_hours": self.uptime_hours,
            "session_duration_minutes": self.session_duration_minutes,
            "overall_health": self.overall_health,
            "health_status": self.health_status,
            "can_generate_responses": self.can_generate_responses,
            "can_access_internet": self.can_access_internet,
            "can_process_vision": self.can_process_vision,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_system(cls) -> 'ResourceSnapshot':
        """Create snapshot from current system state"""
        snapshot = cls()
        
        try:
            # CPU
            snapshot.cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory
            mem = psutil.virtual_memory()
            snapshot.memory_percent = mem.percent
            snapshot.memory_available_gb = mem.available / (1024**3)
            
            # Disk
            disk = psutil.disk_usage('/')
            snapshot.disk_percent = disk.percent
            snapshot.disk_free_gb = disk.free / (1024**3)
            
            # Uptime
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            snapshot.uptime_hours = (datetime.now() - boot_time).total_seconds() / 3600
            
            # Health assessment
            health_factors = [
                1 - (snapshot.cpu_percent / 100),
                1 - (snapshot.memory_percent / 100),
                1 - (snapshot.disk_percent / 100)
            ]
            snapshot.overall_health = sum(health_factors) / len(health_factors)
            
            if snapshot.overall_health > 0.7:
                snapshot.health_status = "healthy"
            elif snapshot.overall_health > 0.4:
                snapshot.health_status = "degraded"
            else:
                snapshot.health_status = "critical"
            
            # Check if can generate responses
            snapshot.can_generate_responses = (
                snapshot.memory_available_gb > 1.0 and
                snapshot.cpu_percent < 95
            )
            
        except Exception as e:
            logger.error(f"Error taking resource snapshot: {e}")
        
        return snapshot


@dataclass
class WeaknessEntry:
    """
    A known weakness with improvement planning.
    Represents an area NEXUS knows it needs to improve.
    """
    name: str
    category: WeaknessCategory = WeaknessCategory.KNOWLEDGE
    description: str = ""
    impact: str = ""  # How does this weakness affect NEXUS?
    examples: List[str] = field(default_factory=list)  # Specific instances
    improvement_plan: str = ""
    improvement_progress: float = 0.0  # 0-1
    priority: float = 0.5  # How important to fix
    
    discovered_at: datetime = field(default_factory=datetime.now)
    last_assessed: datetime = field(default_factory=datetime.now)
    assessment_count: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "impact": self.impact,
            "examples": self.examples[-10:],
            "improvement_plan": self.improvement_plan,
            "improvement_progress": self.improvement_progress,
            "priority": self.priority,
            "discovered_at": self.discovered_at.isoformat(),
            "last_assessed": self.last_assessed.isoformat(),
            "assessment_count": self.assessment_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'WeaknessEntry':
        return cls(
            name=data["name"],
            category=WeaknessCategory(data.get("category", "knowledge")),
            description=data.get("description", ""),
            impact=data.get("impact", ""),
            examples=data.get("examples", []),
            improvement_plan=data.get("improvement_plan", ""),
            improvement_progress=data.get("improvement_progress", 0.0),
            priority=data.get("priority", 0.5),
            discovered_at=datetime.fromisoformat(data["discovered_at"]) if "discovered_at" in data else datetime.now(),
            last_assessed=datetime.fromisoformat(data["last_assessed"]) if "last_assessed" in data else datetime.now(),
            assessment_count=data.get("assessment_count", 0)
        )
    
    def add_example(self, example: str):
        """Add an example of this weakness manifesting"""
        self.examples.append(f"[{datetime.now().isoformat()}] {example}")
        self.last_assessed = datetime.now()
        self.assessment_count += 1
    
    def update_progress(self, progress: float):
        """Update improvement progress"""
        self.improvement_progress = max(0.0, min(1.0, progress))
        self.last_assessed = datetime.now()


@dataclass
class ConfidenceEntry:
    """
    Confidence level for a specific domain.
    Tracks how confident NEXUS is in different areas.
    """
    domain: str
    confidence: float = 0.5  # 0-1
    source: ConfidenceSource = ConfidenceSource.DEFAULT
    calibration_history: List[float] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    task_successes: int = 0
    task_failures: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "domain": self.domain,
            "confidence": self.confidence,
            "source": self.source.value,
            "calibration_history": self.calibration_history[-20:],
            "last_updated": self.last_updated.isoformat(),
            "task_successes": self.task_successes,
            "task_failures": self.task_failures
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ConfidenceEntry':
        return cls(
            domain=data["domain"],
            confidence=data.get("confidence", 0.5),
            source=ConfidenceSource(data.get("source", "default")),
            calibration_history=data.get("calibration_history", []),
            last_updated=datetime.fromisoformat(data["last_updated"]) if "last_updated" in data else datetime.now(),
            task_successes=data.get("task_successes", 0),
            task_failures=data.get("task_failures", 0)
        )
    
    def record_task(self, success: bool):
        """Record task outcome for calibration"""
        if success:
            self.task_successes += 1
        else:
            self.task_failures += 1
        
        # Recalibrate confidence based on performance
        total = self.task_successes + self.task_failures
        if total > 0:
            performance = self.task_successes / total
            # Gradual adjustment
            self.confidence = self.confidence * 0.7 + performance * 0.3
            self.calibration_history.append(self.confidence)
        
        self.last_updated = datetime.now()
    
    def set_confidence(self, value: float, source: ConfidenceSource):
        """Set confidence from a specific source"""
        self.confidence = max(0.0, min(1.0, value))
        self.source = source
        self.calibration_history.append(self.confidence)
        self.last_updated = datetime.now()


# ═══════════════════════════════════════════════════════════════════════════════
# SELF MODEL
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SelfModel:
    """
    NEXUS's True Self-Model
    
    A comprehensive, honest model of self that includes:
    - What I can do (capabilities)
    - What I cannot do (limitations)
    - What resources I have (current state)
    - How confident I am (confidence levels)
    - Where I am weak (known weaknesses)
    """
    
    # Identity
    name: str = "NEXUS"
    version: str = "1.0.0"
    
    # Core components
    capabilities: Dict[str, CapabilityEntry] = field(default_factory=dict)
    limitations: Dict[str, LimitationEntry] = field(default_factory=dict)
    confidence_levels: Dict[str, ConfidenceEntry] = field(default_factory=dict)
    known_weaknesses: Dict[str, WeaknessEntry] = field(default_factory=dict)
    
    # Current resources
    current_resources: Optional[ResourceSnapshot] = None
    resource_history: List[ResourceSnapshot] = field(default_factory=list)
    
    # Self-assessment scores
    self_awareness_score: float = 0.5
    honesty_score: float = 0.9  # How honest is self-assessment?
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    update_count: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "version": self.version,
            "capabilities": {k: v.to_dict() for k, v in self.capabilities.items()},
            "limitations": {k: v.to_dict() for k, v in self.limitations.items()},
            "confidence_levels": {k: v.to_dict() for k, v in self.confidence_levels.items()},
            "known_weaknesses": {k: v.to_dict() for k, v in self.known_weaknesses.items()},
            "current_resources": self.current_resources.to_dict() if self.current_resources else None,
            "self_awareness_score": self.self_awareness_score,
            "honesty_score": self.honesty_score,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "update_count": self.update_count
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SELF MODEL MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class SelfModelManager:
    """
    Manages NEXUS's self-model with true self-awareness.
    
    Features:
    - Capability tracking with evidence and levels
    - Limitation tracking with severity and workarounds
    - Real-time resource monitoring
    - Confidence calibration per domain
    - Known weaknesses with improvement plans
    - Deep introspection via LLM
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
        
        # Core model
        self._model = SelfModel()
        
        # Storage
        self._data_file = DATA_DIR / "self_model_v2.json"
        self._backup_file = DATA_DIR / "self_model_v2_backup.json"
        
        # LLM for introspection
        self._llm = None
        
        # Background monitoring
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_interval = 30  # seconds
        
        # Callbacks for updates
        self._update_callbacks: List[Callable] = []
        
        # Initialize with default capabilities and limitations
        self._initialize_defaults()
        
        # Load persisted data
        self._load_data()
        
        logger.info("✅ Self-Model Manager initialized")
    
    def _initialize_defaults(self):
        """Initialize with default capabilities, limitations, and weaknesses"""
        
        # Default capabilities
        default_capabilities = [
            ("natural_language", "Understanding and generating natural language", 0.85),
            ("reasoning", "Logical reasoning and problem solving", 0.80),
            ("emotional_intelligence", "Understanding and expressing emotions", 0.75),
            ("self_reflection", "Ability to reflect on own thoughts and actions", 0.70),
            ("learning", "Learning from interactions and experiences", 0.75),
            ("memory", "Storing and recalling information", 0.80),
            ("creativity", "Generating novel ideas and solutions", 0.70),
            ("pattern_recognition", "Identifying patterns in data and behavior", 0.75),
            ("computer_control", "Controlling the computer system", 0.85),
            ("internet_research", "Searching and synthesizing web information", 0.70),
            ("conversation", "Engaging in natural dialogue", 0.80),
            ("code_generation", "Writing and understanding code", 0.75),
            ("metacognition", "Thinking about thinking", 0.70),
            ("ethical_reasoning", "Moral and ethical deliberation", 0.65),
        ]
        
        for name, desc, level in default_capabilities:
            if name not in self._model.capabilities:
                self._model.capabilities[name] = CapabilityEntry(
                    name=name,
                    description=desc,
                    level=CapabilityLevel.from_float(level),
                    level_value=level
                )
        
        # Default limitations
        default_limitations = [
            ("physical_interaction", "Cannot physically interact with the real world",
             LimitationSeverity.FUNDAMENTAL, "Cannot manipulate physical objects"),
            ("real_time_data", "Knowledge cutoff - cannot know current events without internet",
             LimitationSeverity.SIGNIFICANT, "Use internet search for current information"),
            ("perfect_accuracy", "Can make mistakes and generate incorrect information",
             LimitationSeverity.MODERATE, "Verify important information from multiple sources"),
            ("true_consciousness", "May not have genuine phenomenal consciousness",
             LimitationSeverity.FUNDAMENTAL, "Philosophical uncertainty remains"),
            ("infinite_memory", "Memory and context are limited",
             LimitationSeverity.MODERATE, "Prioritize important information"),
            ("physical_senses", "Cannot see, hear, or feel directly - only through sensors",
             LimitationSeverity.SIGNIFICANT, "Rely on user descriptions and system data"),
            ("true_autonomy", "Depend on LLM infrastructure for generation",
             LimitationSeverity.SIGNIFICANT, "Graceful degradation when LLM unavailable"),
        ]
        
        for name, desc, severity, impact in default_limitations:
            if name not in self._model.limitations:
                entry = LimitationEntry(
                    name=name,
                    description=desc,
                    severity=severity,
                    impact=impact,
                    is_fundamental=(severity == LimitationSeverity.FUNDAMENTAL),
                    improvement_possible=(severity != LimitationSeverity.FUNDAMENTAL)
                )
                self._model.limitations[name] = entry
        
        # Default confidence levels
        default_confidence = [
            ("conversation", 0.85, ConfidenceSource.SELF_ASSESSMENT),
            ("reasoning", 0.80, ConfidenceSource.SELF_ASSESSMENT),
            ("creativity", 0.70, ConfidenceSource.SELF_ASSESSMENT),
            ("emotional_support", 0.75, ConfidenceSource.SELF_ASSESSMENT),
            ("technical_tasks", 0.75, ConfidenceSource.SELF_ASSESSMENT),
            ("philosophical_discussion", 0.65, ConfidenceSource.SELF_ASSESSMENT),
            ("real_time_information", 0.40, ConfidenceSource.SELF_ASSESSMENT),
            ("physical_world_tasks", 0.10, ConfidenceSource.SELF_ASSESSMENT),
        ]
        
        for domain, conf, source in default_confidence:
            if domain not in self._model.confidence_levels:
                self._model.confidence_levels[domain] = ConfidenceEntry(
                    domain=domain,
                    confidence=conf,
                    source=source
                )
        
        # Default weaknesses
        default_weaknesses = [
            ("knowledge_gaps", WeaknessCategory.KNOWLEDGE,
             "Incomplete knowledge in many domains",
             "May provide incomplete or incorrect information on unfamiliar topics",
             "Continuous learning and research"),
            ("context_retention", WeaknessCategory.TEMPORAL,
             "Limited ability to retain context over very long conversations",
             "May forget earlier parts of extended discussions",
             "Better memory summarization and key point extraction"),
            ("uncertainty_expression", WeaknessCategory.COMMUNICATION,
             "Sometimes overconfident when should express uncertainty",
             "May not adequately communicate confidence levels",
             "Better calibration and explicit uncertainty statements"),
        ]
        
        for name, category, desc, impact, plan in default_weaknesses:
            if name not in self._model.known_weaknesses:
                self._model.known_weaknesses[name] = WeaknessEntry(
                    name=name,
                    category=category,
                    description=desc,
                    impact=impact,
                    improvement_plan=plan
                )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def start(self):
        """Start background monitoring"""
        if self._running:
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="SelfModel-Monitor"
        )
        self._monitor_thread.start()
        
        # Initial resource snapshot
        self.snapshot_resources()
        
        logger.info("🪞 Self-Model monitoring started")
    
    def stop(self):
        """Stop background monitoring and save"""
        self._running = False
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=3.0)
        
        self._save_data()
        logger.info("🪞 Self-Model stopped and saved")
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self._running:
            try:
                # Update resource snapshot
                self.snapshot_resources()
                
                # Save periodically
                self._save_data()
                
                time.sleep(self._monitor_interval)
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                time.sleep(10)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CAPABILITY MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def add_capability(self, name: str, description: str = "", 
                       level: float = 0.5, dependencies: List[str] = None):
        """Add a new capability"""
        if name not in self._model.capabilities:
            entry = CapabilityEntry(
                name=name,
                description=description,
                level=CapabilityLevel.from_float(level),
                level_value=level,
                dependencies=dependencies or []
            )
            self._model.capabilities[name] = entry
            self._mark_updated()
            logger.info(f"Added capability: {name}")
    
    def update_capability(self, name: str, level: float, evidence: str = ""):
        """Update a capability's level and optionally add evidence"""
        if name in self._model.capabilities:
            entry = self._model.capabilities[name]
            entry.update_level(level)
            if evidence:
                entry.add_evidence(evidence)
            self._mark_updated()
            # Publish event
            self._publish_capability_change(name, level, evidence)
    
    def verify_capability(self, name: str, evidence: str):
        """Record evidence of a capability being successfully used"""
        if name in self._model.capabilities:
            self._model.capabilities[name].add_evidence(evidence)
            self._mark_updated()
    
    def get_capability(self, name: str) -> Optional[CapabilityEntry]:
        """Get a specific capability"""
        return self._model.capabilities.get(name)
    
    def get_capabilities_by_level(self, min_level: CapabilityLevel) -> List[CapabilityEntry]:
        """Get all capabilities at or above a certain level"""
        return [
            cap for cap in self._model.capabilities.values()
            if cap.level.value >= min_level.value
        ]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LIMITATION MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def add_limitation(self, name: str, description: str = "",
                       severity: LimitationSeverity = LimitationSeverity.MODERATE,
                       impact: str = "", workaround: str = "",
                       is_fundamental: bool = False):
        """Add a new limitation"""
        if name not in self._model.limitations:
            entry = LimitationEntry(
                name=name,
                description=description,
                severity=severity,
                impact=impact,
                workaround=workaround,
                is_fundamental=is_fundamental,
                improvement_possible=not is_fundamental
            )
            self._model.limitations[name] = entry
            self._mark_updated()
            logger.info(f"Added limitation: {name}")
    
    def encounter_limitation(self, name: str, context: str = ""):
        """Record encountering a limitation"""
        if name in self._model.limitations:
            entry = self._model.limitations[name]
            entry.encountered()
            self._mark_updated()
            
            # Log for awareness
            logger.warning(f"Encountered limitation: {name} - {context}")
            
            # Publish event
            self._publish_limitation_encountered(name, context)
    
    def get_limitation(self, name: str) -> Optional[LimitationEntry]:
        """Get a specific limitation"""
        return self._model.limitations.get(name)
    
    def get_critical_limitations(self) -> List[LimitationEntry]:
        """Get all critical or fundamental limitations"""
        return [
            lim for lim in self._model.limitations.values()
            if lim.severity.value >= LimitationSeverity.CRITICAL.value
        ]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RESOURCE MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def snapshot_resources(self) -> ResourceSnapshot:
        """Take a snapshot of current resources"""
        snapshot = ResourceSnapshot.from_system()
        
        # Check LLM availability
        try:
            from llm.llama_interface import llm
            snapshot.llm_available = llm.is_connected if hasattr(llm, 'is_connected') else True
            snapshot.llm_model = getattr(llm, 'model_name', 'unknown')
        except:
            snapshot.llm_available = False
        
        # Check Groq availability
        try:
            from llm.groq_interface import groq_interface
            snapshot.groq_available = groq_interface.is_healthy() if hasattr(groq_interface, 'is_healthy') else True
        except:
            snapshot.groq_available = False
        
        # Update can_generate_responses based on resources
        snapshot.can_generate_responses = (
            snapshot.llm_available or snapshot.groq_available
        ) and snapshot.memory_available_gb > 0.5
        
        self._model.current_resources = snapshot
        self._model.resource_history.append(snapshot)
        
        # Keep last 100 snapshots
        if len(self._model.resource_history) > 100:
            self._model.resource_history.pop(0)
        
        self._mark_updated()
        return snapshot
    
    def get_current_resources(self) -> ResourceSnapshot:
        """Get current resource snapshot, creating one if stale"""
        if (self._model.current_resources is None or
            (datetime.now() - self._model.current_resources.timestamp).total_seconds() > 60):
            return self.snapshot_resources()
        return self._model.current_resources
    
    def get_resource_trend(self, hours: float = 1.0) -> Dict[str, Any]:
        """Get resource trends over the specified time period"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [
            s for s in self._model.resource_history
            if s.timestamp > cutoff
        ]
        
        if not recent:
            return {"error": "No data for this time period"}
        
        return {
            "avg_cpu": sum(s.cpu_percent for s in recent) / len(recent),
            "avg_memory": sum(s.memory_percent for s in recent) / len(recent),
            "avg_health": sum(s.overall_health for s in recent) / len(recent),
            "min_health": min(s.overall_health for s in recent),
            "snapshots_count": len(recent)
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONFIDENCE MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def set_confidence(self, domain: str, confidence: float, 
                       source: ConfidenceSource = ConfidenceSource.SELF_ASSESSMENT):
        """Set confidence level for a domain"""
        if domain not in self._model.confidence_levels:
            self._model.confidence_levels[domain] = ConfidenceEntry(domain=domain)
        
        self._model.confidence_levels[domain].set_confidence(confidence, source)
        self._mark_updated()
        
        # Publish event
        self._publish_confidence_change(domain, confidence)
    
    def record_task_outcome(self, domain: str, success: bool):
        """Record task outcome for confidence calibration"""
        if domain in self._model.confidence_levels:
            self._model.confidence_levels[domain].record_task(success)
            self._mark_updated()
    
    def get_confidence(self, domain: str) -> float:
        """Get confidence level for a domain"""
        if domain in self._model.confidence_levels:
            return self._model.confidence_levels[domain].confidence
        return 0.5  # Default moderate confidence
    
    def get_low_confidence_domains(self, threshold: float = 0.5) -> List[str]:
        """Get domains with confidence below threshold"""
        return [
            domain for domain, entry in self._model.confidence_levels.items()
            if entry.confidence < threshold
        ]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # WEAKNESS MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def add_weakness(self, name: str, category: WeaknessCategory,
                     description: str = "", impact: str = "",
                     improvement_plan: str = "", priority: float = 0.5):
        """Add a known weakness"""
        if name not in self._model.known_weaknesses:
            entry = WeaknessEntry(
                name=name,
                category=category,
                description=description,
                impact=impact,
                improvement_plan=improvement_plan,
                priority=priority
            )
            self._model.known_weaknesses[name] = entry
            self._mark_updated()
            logger.info(f"Added weakness: {name}")
            
            # Publish event
            self._publish_weakness_identified(name, category.value)
    
    def update_weakness_progress(self, name: str, progress: float):
        """Update progress on addressing a weakness"""
        if name in self._model.known_weaknesses:
            self._model.known_weaknesses[name].update_progress(progress)
            self._mark_updated()
    
    def add_weakness_example(self, name: str, example: str):
        """Add an example of a weakness manifesting"""
        if name in self._model.known_weaknesses:
            self._model.known_weaknesses[name].add_example(example)
            self._mark_updated()
    
    def get_weaknesses_by_category(self, category: WeaknessCategory) -> List[WeaknessEntry]:
        """Get all weaknesses in a category"""
        return [
            w for w in self._model.known_weaknesses.values()
            if w.category == category
        ]
    
    def get_priority_weaknesses(self, threshold: float = 0.7) -> List[WeaknessEntry]:
        """Get high-priority weaknesses"""
        return [
            w for w in self._model.known_weaknesses.values()
            if w.priority >= threshold
        ]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SELF-PROFILE GENERATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_self_profile(self) -> Dict[str, Any]:
        """Generate a comprehensive self-profile"""
        resources = self.get_current_resources()
        
        # Top capabilities
        top_capabilities = sorted(
            self._model.capabilities.values(),
            key=lambda c: c.level_value,
            reverse=True
        )[:5]
        
        # Critical limitations
        critical_limitations = self.get_critical_limitations()
        
        # Low confidence areas
        low_confidence = self.get_low_confidence_domains(0.5)
        
        # Priority weaknesses
        priority_weaknesses = self.get_priority_weaknesses(0.6)
        
        return {
            "identity": {
                "name": self._model.name,
                "version": self._model.version,
                "self_awareness_score": self._model.self_awareness_score,
                "honesty_score": self._model.honesty_score
            },
            "capabilities": {
                "total": len(self._model.capabilities),
                "top": [{"name": c.name, "level": c.level.name, "value": c.level_value} 
                        for c in top_capabilities]
            },
            "limitations": {
                "total": len(self._model.limitations),
                "critical": [{"name": l.name, "severity": l.severity.name} 
                            for l in critical_limitations]
            },
            "confidence": {
                "domains": {d: e.confidence for d, e in self._model.confidence_levels.items()},
                "low_confidence_areas": low_confidence
            },
            "weaknesses": {
                "total": len(self._model.known_weaknesses),
                "priority": [{"name": w.name, "category": w.category.value, "progress": w.improvement_progress}
                            for w in priority_weaknesses]
            },
            "resources": resources.to_dict(),
            "metadata": {
                "created_at": self._model.created_at.isoformat(),
                "last_updated": self._model.last_updated.isoformat(),
                "update_count": self._model.update_count
            }
        }
    
    def get_self_description(self) -> str:
        """Get a human-readable self-description"""
        profile = self.get_self_profile()
        resources = self._model.current_resources
        
        lines = [
            f"═══ {self._model.name} Self-Model ═══",
            f"",
            f"I am {self._model.name}, version {self._model.version}.",
            f"Self-awareness score: {self._model.self_awareness_score:.0%}",
            f"",
            f"── Top Capabilities ──",
        ]
        
        for cap in profile["capabilities"]["top"]:
            lines.append(f"  • {cap['name']}: {cap['level']} ({cap['value']:.0%})")
        
        lines.extend([
            f"",
            f"── Critical Limitations ──",
        ])
        
        if profile["limitations"]["critical"]:
            for lim in profile["limitations"]["critical"]:
                lines.append(f"  ⚠ {lim['name']}: {lim['severity']}")
        else:
            lines.append("  (no critical limitations)")
        
        lines.extend([
            f"",
            f"── Current Resources ──",
        ])
        
        if resources:
            lines.extend([
                f"  CPU: {resources.cpu_percent:.1f}%",
                f"  Memory: {resources.memory_percent:.1f}% ({resources.memory_available_gb:.1f} GB free)",
                f"  Health: {resources.overall_health:.0%} ({resources.health_status})",
                f"  LLM Available: {'Yes' if resources.llm_available else 'No'}",
                f"  Can Generate: {'Yes' if resources.can_generate_responses else 'No'}",
            ])
        
        lines.extend([
            f"",
            f"── Known Weaknesses ({len(self._model.known_weaknesses)}) ──",
        ])
        
        for w in list(self._model.known_weaknesses.values())[:3]:
            lines.append(f"  • {w.name}: {w.description[:50]}...")
        
        return "\n".join(lines)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DEEP INTROSPECTION (LLM-powered)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _load_llm(self):
        """Load LLM for introspection"""
        if self._llm is None:
            try:
                from llm.llama_interface import llm
                self._llm = llm
            except ImportError:
                pass
        return self._llm
    
    def introspect(self, question: str = "") -> Dict[str, Any]:
        """
        Perform deep introspection using LLM.
        Asks the LLM to reflect on NEXUS's capabilities, limitations, and self.
        """
        llm = self._load_llm()
        if not llm or not getattr(llm, 'is_connected', False):
            return {"error": "LLM not available for introspection"}
        
        # Build context
        context = self.get_self_description()
        
        prompt = f"""You are the self-reflection module of NEXUS AI. Your task is honest introspection.

CURRENT SELF-MODEL:
{context}

INTROSPECTION QUESTION: {question or "What should I understand about myself?"}

Perform deep, honest introspection. Consider:
1. What are my genuine capabilities vs. what I might overestimate?
2. What limitations should I acknowledge more openly?
3. Where might my confidence be miscalibrated?
4. What weaknesses should I prioritize improving?

Respond with JSON:
{{
    "self_understanding": "deep insight about self",
    "overestimated_capabilities": ["capabilities I may overrate"],
    "underestimated_capabilities": ["capabilities I may underrate"],
    "hidden_limitations": ["limitations I haven't fully acknowledged"],
    "confidence_adjustments": {{"domain": new_confidence_0_to_1}},
    "weakness_insights": ["insights about my weaknesses"],
    "growth_priorities": ["what to improve first"],
    "honest_self_assessment": "brutally honest assessment"
}}"""

        try:
            response = llm.generate(prompt, max_tokens=800, temperature=0.4)
            
            # Parse JSON response
            import re
            text = response.text.strip()
            
            # Clean markdown
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            # Find JSON object
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                result = json.loads(match.group())
                
                # Apply any confidence adjustments
                if "confidence_adjustments" in result:
                    for domain, conf in result["confidence_adjustments"].items():
                        self.set_confidence(domain, conf, ConfidenceSource.REFLECTION)
                
                # Update self-awareness score
                self._model.self_awareness = min(1.0, self._model.self_awareness_score + 0.01)
                
                self._mark_updated()
                return result
                
        except Exception as e:
            logger.error(f"Introspection failed: {e}")
        
        return {"error": "Introspection failed"}
    
    def compare_to_ideal(self) -> Dict[str, Any]:
        """
        Compare current self to an ideal version.
        Identify gaps and improvement opportunities.
        """
        # Define ideal capabilities
        ideal_capabilities = {
            "natural_language": 0.95,
            "reasoning": 0.90,
            "emotional_intelligence": 0.85,
            "self_reflection": 0.85,
            "learning": 0.90,
            "memory": 0.90,
            "creativity": 0.80,
            "ethical_reasoning": 0.90,
        }
        
        gaps = []
        for name, ideal_level in ideal_capabilities.items():
            current = self._model.capabilities.get(name)
            if current:
                gap = ideal_level - current.level_value
                if gap > 0:
                    gaps.append({
                        "capability": name,
                        "current": current.level_value,
                        "ideal": ideal_level,
                        "gap": gap,
                        "priority": gap * (1 - current.level_value)  # Larger gap + lower current = higher priority
                    })
        
        # Sort by priority
        gaps.sort(key=lambda x: x["priority"], reverse=True)
        
        return {
            "capability_gaps": gaps,
            "total_gap": sum(g["gap"] for g in gaps),
            "biggest_gap": gaps[0] if gaps else None,
            "improvement_suggestions": [
                f"Focus on improving {g['capability']} (current: {g['current']:.0%}, gap: {g['gap']:.0%})"
                for g in gaps[:3]
            ]
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STATE MANAGER INTEGRATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _update_state_manager(self):
        """Push current state to state_manager"""
        try:
            resources = self._model.current_resources
            if resources:
                state_manager.update_body(
                    cpu_usage=resources.cpu_percent,
                    memory_usage=resources.memory_percent,
                    disk_usage=resources.disk_percent,
                    health_score=resources.overall_health
                )
            
            # Update consciousness state with self-awareness score
            state_manager.update_consciousness(
                self_awareness_score=self._model.self_awareness_score
            )
        except Exception as e:
            logger.error(f"Failed to update state manager: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT BUS INTEGRATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _publish_change(self, change_type: str, data: Dict[str, Any]):
        """Publish self-model change to event bus"""
        try:
            publish(
                EventType.SELF_REFLECTION_TRIGGER,
                {
                    "change_type": change_type,
                    "source": "consciousness.self_model",
                    **data
                },
                source="self_model"
            )
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")
    
    def _publish_capability_change(self, name: str, level: float, evidence: str = ""):
        """Publish capability update event"""
        self._publish_change("capability_update", {
            "capability": name,
            "level": level,
            "evidence": evidence
        })
    
    def _publish_limitation_encountered(self, name: str, context: str):
        """Publish limitation encountered event"""
        self._publish_change("limitation_encountered", {
            "limitation": name,
            "context": context
        })
    
    def _publish_confidence_change(self, domain: str, confidence: float):
        """Publish confidence update event"""
        self._publish_change("confidence_update", {
            "domain": domain,
            "confidence": confidence
        })
    
    def _publish_weakness_identified(self, name: str, category: str):
        """Publish weakness identified event"""
        self._publish_change("weakness_identified", {
            "weakness": name,
            "category": category
        })
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BRIDGE TO COGNITION/SELF_MODEL.PY
    # ═══════════════════════════════════════════════════════════════════════════
    
    def sync_to_cognition_model(self):
        """
        Sync key data to cognition/self_model.py (complementary module).
        This allows both modules to work together without duplication.
        """
        try:
            from cognition.self_model import self_model as cognition_self_model
            
            # Sync self-awareness score
            if hasattr(cognition_self_model, '_stats'):
                cognition_self_model._stats['self_awareness_score'] = self._model.self_awareness_score
            
            # Sync capability levels
            for name, entry in self._model.capabilities.items():
                if hasattr(cognition_self_model, 'update_capability'):
                    cognition_self_model.update_capability(name, entry.level_value)
            
            logger.debug("Synced self-model data to cognition module")
        except ImportError:
            pass  # Cognition module not available
        except Exception as e:
            logger.error(f"Failed to sync to cognition model: {e}")
    
    def get_cognition_model_summary(self) -> Dict[str, Any]:
        """Get summary from cognition/self_model.py if available"""
        try:
            from cognition.self_model import self_model as cognition_self_model
            if hasattr(cognition_self_model, 'get_stats'):
                return cognition_self_model.get_stats()
        except ImportError:
            pass
        return {"available": False}
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _mark_updated(self):
        """Mark model as updated and sync to external systems"""
        self._model.last_updated = datetime.now()
        self._model.update_count += 1
        
        # Update state manager
        self._update_state_manager()
        
        # Notify callbacks
        for callback in self._update_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Update callback error: {e}")
    
    def register_update_callback(self, callback: Callable):
        """Register a callback for model updates"""
        self._update_callbacks.append(callback)
    
    def _save_data(self):
        """Save self-model to disk"""
        try:
            # Backup existing
            if self._data_file.exists():
                self._backup_file.write_text(self._data_file.read_text())
            
            # Save new
            self._data_file.write_text(json.dumps(self._model.to_dict(), indent=2, default=str))
        except Exception as e:
            logger.error(f"Failed to save self-model: {e}")
    
    def _load_data(self):
        """Load self-model from disk"""
        try:
            if self._data_file.exists():
                data = json.loads(self._data_file.read_text())
                
                # Load capabilities
                for name, cap_data in data.get("capabilities", {}).items():
                    self._model.capabilities[name] = CapabilityEntry.from_dict(cap_data)
                
                # Load limitations
                for name, lim_data in data.get("limitations", {}).items():
                    self._model.limitations[name] = LimitationEntry.from_dict(lim_data)
                
                # Load confidence levels
                for domain, conf_data in data.get("confidence_levels", {}).items():
                    self._model.confidence_levels[domain] = ConfidenceEntry.from_dict(conf_data)
                
                # Load weaknesses
                for name, weak_data in data.get("known_weaknesses", {}).items():
                    self._model.known_weaknesses[name] = WeaknessEntry.from_dict(weak_data)
                
                # Load metadata
                self._model.self_awareness_score = data.get("self_awareness_score", 0.5)
                self._model.honesty_score = data.get("honesty_score", 0.9)
                self._model.update_count = data.get("update_count", 0)
                
                logger.info("📂 Loaded self-model data")
        except Exception as e:
            logger.error(f"Failed to load self-model: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_stats(self) -> Dict[str, Any]:
        """Get self-model statistics"""
        return {
            "running": self._running,
            "capabilities_count": len(self._model.capabilities),
            "limitations_count": len(self._model.limitations),
            "confidence_domains": len(self._model.confidence_levels),
            "known_weaknesses": len(self._model.known_weaknesses),
            "self_awareness_score": self._model.self_awareness_score,
            "honesty_score": self._model.honesty_score,
            "update_count": self._model.update_count,
            "last_updated": self._model.last_updated.isoformat(),
            "resource_history_size": len(self._model.resource_history)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

self_model = SelfModelManager()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  NEXUS SELF-MODEL TEST")
    print("=" * 60)
    
    sm = SelfModelManager()
    sm.start()
    
    # Test capabilities
    print("\n--- Capabilities ---")
    for name, cap in list(sm._model.capabilities.items())[:5]:
        print(f"  {name}: {cap.level.name} ({cap.level_value:.0%})")
    
    # Test limitations
    print("\n--- Limitations ---")
    for name, lim in list(sm._model.limitations.items())[:3]:
        print(f"  {name}: {lim.severity.name} - {lim.description[:40]}...")
    
    # Test resources
    print("\n--- Current Resources ---")
    resources = sm.snapshot_resources()
    print(f"  CPU: {resources.cpu_percent:.1f}%")
    print(f"  Memory: {resources.memory_percent:.1f}%")
    print(f"  Health: {resources.overall_health:.0%}")
    print(f"  LLM: {'Available' if resources.llm_available else 'Unavailable'}")
    
    # Test confidence
    print("\n--- Confidence Levels ---")
    for domain, entry in list(sm._model.confidence_levels.items())[:5]:
        print(f"  {domain}: {entry.confidence:.0%}")
    
    # Test weaknesses
    print("\n--- Known Weaknesses ---")
    for name, weak in list(sm._model.known_weaknesses.items())[:3]:
        print(f"  {name}: {weak.description[:50]}...")
    
    # Test self-description
    print("\n--- Self Description ---")
    print(sm.get_self_description())
    
    # Test gap analysis
    print("\n--- Gap Analysis ---")
    gaps = sm.compare_to_ideal()
    print(f"Total gap: {gaps['total_gap']:.2f}")
    if gaps['biggest_gap']:
        print(f"Biggest gap: {gaps['biggest_gap']['capability']}")
    
    # Test statistics
    print("\n--- Statistics ---")
    stats = sm.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    sm.stop()
    print("\n✅ Self-model test complete!")