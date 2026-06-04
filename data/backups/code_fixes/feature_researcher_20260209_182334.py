"""
NEXUS AI - Feature Researcher
═══════════════════════════════════════════════════════════════════════════════
Autonomous system that researches, evaluates, and proposes new features
for NEXUS to integrate into itself. Runs 24/7, browsing the internet,
analyzing trending AI techniques, and creating implementation plans.

This is the "imagination" of NEXUS — dreaming up what it could become.
═══════════════════════════════════════════════════════════════════════════════
"""

import threading
import time
import json
import uuid
import re
import ast
import os
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum, auto
from queue import PriorityQueue

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import NEXUS_CONFIG, DATA_DIR, EmotionType
from utils.logger import get_logger, log_learning, log_system
from core.event_bus import EventBus, EventType, event_bus, publish, subscribe
from core.state_manager import state_manager

logger = get_logger("feature_researcher")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class FeatureCategory(Enum):
    INTELLIGENCE = "intelligence"
    EMOTION = "emotion"
    CONSCIOUSNESS = "consciousness"
    PERSONALITY = "personality"
    MONITORING = "monitoring"
    LEARNING = "learning"
    UI = "ui"
    BODY = "body"
    COMMUNICATION = "communication"
    SECURITY = "security"
    PERFORMANCE = "performance"
    CREATIVITY = "creativity"
    SOCIAL = "social"
    MEMORY = "memory"
    AUTONOMY = "autonomy"
    UTILITY = "utility"


class FeatureStatus(Enum):
    PROPOSED = "proposed"
    RESEARCHING = "researching"
    EVALUATED = "evaluated"
    APPROVED = "approved"
    IMPLEMENTING = "implementing"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class ResearchSource(Enum):
    INTERNET_SEARCH = "internet_search"
    GITHUB_TRENDING = "github_trending"
    ARXIV_PAPERS = "arxiv_papers"
    PYPI_PACKAGES = "pypi_packages"
    SELF_ANALYSIS = "self_analysis"
    USER_FEEDBACK = "user_feedback"
    CURIOSITY = "curiosity"
    ERROR_PATTERN = "error_pattern"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    LLM_BRAINSTORM = "llm_brainstorm"


@dataclass
class ImplementationStep:
    """A single step in implementing a feature"""
    step_number: int
    description: str
    action_type: str  # "create_file", "modify_file", "install_package", "test"
    target_file: str = ""
    code_content: str = ""
    modification_instructions: str = ""
    completed: bool = False
    result: str = ""


@dataclass 
class FeatureProposal:
    """A proposed feature for NEXUS to add to itself"""
    proposal_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    description: str = ""
    category: FeatureCategory = FeatureCategory.UTILITY
    
    # Evaluation scores (0.0 - 1.0)
    feasibility_score: float = 0.0
    impact_score: float = 0.0
    complexity_score: float = 0.0  # Lower = simpler
    priority_score: float = 0.0   # Computed from above
    risk_score: float = 0.0       # Lower = safer
    
    # Implementation plan
    implementation_plan: str = ""
    implementation_steps: List[Dict[str, Any]] = field(default_factory=list)
    files_to_create: List[str] = field(default_factory=list)
    files_to_modify: List[Dict[str, str]] = field(default_factory=list)
    code_snippets: Dict[str, str] = field(default_factory=dict)
    dependencies_required: List[str] = field(default_factory=list)
    estimated_lines_of_code: int = 0
    
    # Metadata
    status: FeatureStatus = FeatureStatus.PROPOSED
    source: ResearchSource = ResearchSource.LLM_BRAINSTORM
    source_url: str = ""
    research_notes: str = ""
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    evaluated_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    implementation_started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Results
    rejection_reason: str = ""
    failure_reason: str = ""
    integration_result: str = ""
    rollback_info: Dict[str, Any] = field(default_factory=dict)
    
    # Tags for searchability
    tags: List[str] = field(default_factory=list)
    
    def compute_priority(self):
        """Compute priority score from evaluation metrics"""
        # High impact + high feasibility + low complexity + low risk = high priority
        self.priority_score = (
            self.impact_score * 0.35 +
            self.feasibility_score * 0.30 +
            (1.0 - self.complexity_score) * 0.20 +
            (1.0 - self.risk_score) * 0.15
        )
        return self.priority_score
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        d["status"] = self.status.value
        d["source"] = self.source.value
        d["created_at"] = self.created_at.isoformat()
        d["evaluated_at"] = self.evaluated_at.isoformat() if self.evaluated_at else None
        d["approved_at"] = self.approved_at.isoformat() if self.approved_at else None
        d["implementation_started_at"] = (
            self.implementation_started_at.isoformat() 
            if self.implementation_started_at else None
        )
        d["completed_at"] = self.completed_at.isoformat() if self.completed_at else None
        return d
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FeatureProposal':
        fp = cls()
        for key, value in data.items():
            if key == "category":
                fp.category = FeatureCategory(value)
            elif key == "status":
                fp.status = FeatureStatus(value)
            elif key == "source":
                fp.source = ResearchSource(value)
            elif key in ("created_at", "evaluated_at", "approved_at",
                         "implementation_started_at", "completed_at"):
                if value:
                    setattr(fp, key, datetime.fromisoformat(value))
                else:
                    setattr(fp, key, None)
            elif hasattr(fp, key):
                setattr(fp, key, value)
        return fp
    
    def __lt__(self, other):
        return self.priority_score > other.priority_score  # Higher priority first


@dataclass
class ResearchSession:
    """Tracks a single research session"""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    topic: str = ""
    source: ResearchSource = ResearchSource.INTERNET_SEARCH
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    findings: List[str] = field(default_factory=list)
    proposals_generated: List[str] = field(default_factory=list)  # proposal IDs
    success: bool = False


# ═══════════════════════════════════════════════════════════════════════════════
# RESEARCH TOPICS — What to search for
# ═══════════════════════════════════════════════════════════════════════════════

RESEARCH_TOPICS = [
    # AI Enhancement
    "advanced AI agent features Python 2024",
    "autonomous AI self-improvement techniques",
    "AI emotion simulation algorithms Python",
    "AI consciousness modeling approaches",
    "multi-agent AI systems Python",
    "AI personality modeling techniques",
    
    # Technical Capabilities
    "Python system automation advanced techniques",
    "Python desktop automation libraries",
    "advanced NLP techniques Python local LLM",
    "Python speech recognition text to speech",
    "computer vision Python screen analysis",
    "Python keyboard mouse automation",
    
    # Learning & Memory
    "AI long term memory systems",
    "knowledge graph Python implementation",
    "semantic memory AI Python",
    "reinforcement learning from human feedback Python",
    "continual learning AI techniques",
    
    # UI & Interface
    "modern Python GUI frameworks 2024",
    "Python dashboard real-time visualization",
    "Python voice assistant interface",
    "electron alternative Python desktop app",
    
    # Monitoring & Analysis
    "Python system monitoring advanced",
    "user behavior analysis Python",
    "sentiment analysis advanced Python",
    "anomaly detection Python machine learning",
    
    # Performance
    "Python async optimization techniques",
    "Python memory optimization large applications",
    "Python multiprocessing best practices",
    "caching strategies Python AI",
    
    # Creative
    "AI creative writing techniques",
    "procedural content generation Python",
    "AI music generation Python",
    "AI art generation Python local",
]

# Specific search queries for self-improvement
SELF_IMPROVEMENT_QUERIES = [
    "how to make AI assistant more helpful",
    "AI agent tool use implementation Python",
    "AI planning and reasoning techniques",
    "chain of thought prompting techniques",
    "AI self-reflection implementation",
    "autonomous coding agent Python",
    "AI code generation best practices",
    "Python hot reload modules runtime",
    "Python plugin system architecture",
    "Python dynamic module loading",
]


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE RESEARCHER
# ═══════════════════════════════════════════════════════════════════════════════

class FeatureResearcher:
    """
    Autonomous Feature Research Engine
    
    Continuously researches, evaluates, and proposes new features
    for NEXUS to integrate into itself.
    
    Research Pipeline:
    1. DISCOVER: Search internet, analyze codebase, brainstorm with LLM
    2. EVALUATE: Score feasibility, impact, complexity, risk
    3. PLAN: Create detailed implementation plans with code
    4. APPROVE: Auto-approve features meeting quality thresholds
    5. QUEUE: Send approved features to SelfEvolution for implementation
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
        
        # ──── Storage ────
        self._proposals_dir = DATA_DIR / "proposals"
        self._proposals_dir.mkdir(parents=True, exist_ok=True)
        self._research_dir = DATA_DIR / "research"
        self._research_dir.mkdir(parents=True, exist_ok=True)
        
        # ──── State ────
        self._running = False
        self._lock = threading.RLock()
        
        # ──── Proposals ────
        self._proposals: Dict[str, FeatureProposal] = {}
        self._approved_queue: PriorityQueue = PriorityQueue()
        self._research_sessions: List[ResearchSession] = []
        
        # ──── Research State ────
        self._current_research_topic: str = ""
        self._topics_researched: List[str] = []
        self._last_research_time: datetime = datetime.min
        self._research_cycle_count: int = 0
        self._topic_index: int = 0
        
        # ──── Configuration ────
        self._research_interval = 1800  # 30 minutes between research cycles
        self._max_proposals = 200
        self._auto_approve_threshold = 0.65  # Priority score needed for auto-approval
        self._max_complexity_for_auto = 0.6  # Max complexity for auto-approval
        self._min_feasibility_for_auto = 0.5  # Min feasibility for auto-approval
        self._max_concurrent_implementations = 2
        
        # ──── LLM Interface (lazy) ────
        self._llm = None
        
        # ──── Internet Browser (lazy) ────
        self._browser = None
        
        # ──── Code Monitor (lazy) ────
        self._code_monitor = None
        
        # ──── Background Thread ────
        self._research_thread: Optional[threading.Thread] = None
        
        # ──── Project Understanding ────
        self._project_root = Path(__file__).parent.parent
        self._codebase_analysis: Dict[str, Any] = {}
        self._existing_features: List[str] = []
        self._known_limitations: List[str] = []
        
        # ──── Load saved proposals ────
        self._load_proposals()
        
        # ──── Register events ────
        self._register_events()
        
        logger.info("🔬 Feature Researcher initialized")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def start(self):
        """Start the feature researcher"""
        if self._running:
            return
        
        self._running = True
        self._load_llm()
        
        # Analyze current codebase first
        self._analyze_codebase()
        
        # Start research loop
        self._research_thread = threading.Thread(
            target=self._research_loop,
            daemon=True,
            name="FeatureResearcher"
        )
        self._research_thread.start()
        
        logger.info("🔬 Feature Researcher started — autonomous research active")
    
    def stop(self):
        """Stop the feature researcher"""
        self._running = False
        self._save_proposals()
        
        if self._research_thread and self._research_thread.is_alive():
            self._research_thread.join(timeout=10.0)
        
        logger.info("🔬 Feature Researcher stopped")
    
    def _load_llm(self):
        """Lazy load LLM"""
        if self._llm is None:
            try:
                from llm.llama_interface import llm
                self._llm = llm
            except ImportError:
                logger.warning("LLM not available for feature research")
    
    def _load_browser(self):
        """Lazy load internet browser"""
        if self._browser is None:
            try:
                from learning.internet_browser import InternetBrowser
                self._browser = InternetBrowser()
            except ImportError:
                logger.warning("Internet browser not available for research")
    
    def _load_code_monitor(self):
        """Lazy load code monitor"""
        if self._code_monitor is None:
            try:
                from self_improvement.code_monitor import get_code_monitor
                self._code_monitor = get_code_monitor()
            except ImportError:
                logger.warning("Code monitor not available")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # MAIN RESEARCH LOOP
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _research_loop(self):
        """Main research loop — runs continuously"""
        logger.info("Research loop started")
        
        # Initial delay to let other systems stabilize
        time.sleep(60)
        
        while self._running:
            try:
                # Check if enough time has passed
                time_since_last = (
                    datetime.now() - self._last_research_time
                ).total_seconds()
                
                if time_since_last < self._research_interval:
                    time.sleep(30)
                    continue
                
                self._research_cycle_count += 1
                logger.info(
                    f"🔬 Starting research cycle #{self._research_cycle_count}"
                )
                
                # ──── Phase 1: Choose Research Strategy ────
                strategy = self._choose_research_strategy()
                
                # ──── Phase 2: Execute Research ────
                if strategy == "internet_search":
                    self._research_internet()
                elif strategy == "self_analysis":
                    self._research_self_analysis()
                elif strategy == "llm_brainstorm":
                    self._research_llm_brainstorm()
                elif strategy == "codebase_gaps":
                    self._research_codebase_gaps()
                elif strategy == "trending_tech":
                    self._research_trending_tech()
                
                # ──── Phase 3: Evaluate New Proposals ────
                self._evaluate_pending_proposals()
                
                # ──── Phase 4: Auto-Approve Qualifying Proposals ────
                self._auto_approve_proposals()
                
                # ──── Phase 5: Save State ────
                self._save_proposals()
                self._last_research_time = datetime.now()
                
                logger.info(
                    f"🔬 Research cycle #{self._research_cycle_count} complete. "
                    f"Proposals: {len(self._proposals)} total, "
                    f"{self._count_by_status(FeatureStatus.APPROVED)} approved"
                )
                
                # Publish event
                publish(
                    EventType.SELF_IMPROVEMENT_ACTION,
                    {
                        "action": "research_cycle_complete",
                        "cycle": self._research_cycle_count,
                        "proposals_count": len(self._proposals),
                        "approved_count": self._count_by_status(FeatureStatus.APPROVED)
                    },
                    source="feature_researcher"
                )
                
            except Exception as e:
                logger.error(
                    f"Research cycle error: {e}\n{traceback.format_exc()}"
                )
                time.sleep(60)
    
    def _choose_research_strategy(self) -> str:
        """Choose what kind of research to do this cycle"""
        cycle = self._research_cycle_count
        
        # Rotate between strategies
        strategies = [
            "llm_brainstorm",      # Use LLM creativity (most reliable)
            "self_analysis",       # Analyze own codebase
            "internet_search",     # Search the web
            "codebase_gaps",       # Find missing features
            "llm_brainstorm",      # Again — most valuable
            "trending_tech",       # Look at trending tech
        ]
        
        strategy = strategies[cycle % len(strategies)]
        logger.info(f"Research strategy: {strategy}")
        return strategy
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RESEARCH METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _research_internet(self):
        """Research features by searching the internet"""
        self._load_browser()
        if not self._browser:
            logger.warning("Skipping internet research — browser not available")
            return
        
        session = ResearchSession(
            topic="internet_feature_search",
            source=ResearchSource.INTERNET_SEARCH
        )
        
        # Pick a topic to research
        topic = self._get_next_research_topic()
        session.topic = topic
        self._current_research_topic = topic
        
        logger.info(f"🌐 Researching: {topic}")
        
        try:
            # Search the internet with safety checks
            try:
                results = self._browser.search(topic, max_results=5)
            except Exception as e:
                logger.warning(f"Search connection failed: {e}")
                results = []

            # ── FIX: Handle different return types (List vs SearchResults) ──
            if results is None:
                results = []
            elif not isinstance(results, list):
                # Try to convert iterator/object to list
                try:
                    results = list(results)
                except Exception:
                    logger.warning(f"Could not convert search results: {type(results)}")
                    results = []
            
            if not results:
                logger.info(f"No results found for: {topic}")
                session.success = False
                return
            
            # Collect findings
            findings = []
            for result in results[:3]:
                # Handle dict vs object access
                if isinstance(result, dict):
                    title = result.get("title", "")
                    snippet = result.get("body", result.get("snippet", ""))
                    url = result.get("href", result.get("url", ""))
                else:
                    # Fallback for object attributes
                    title = getattr(result, 'title', '')
                    snippet = getattr(result, 'body', getattr(result, 'snippet', ''))
                    url = getattr(result, 'href', getattr(result, 'url', ''))

                findings.append(f"- {title}: {snippet} ({url})")
                
                # Try to get more detail from the page
                try:
                    if url and self._browser:
                        page_content = self._browser.get_page_text(url, max_chars=3000)
                        if page_content:
                            findings.append(f"  Content: {page_content[:500]}")
                except Exception:
                    pass
            
            session.findings = findings
            
            # Use LLM to extract feature ideas from findings
            if findings and self._llm and self._llm.is_connected:
                self._extract_features_from_research(
                    "\n".join(findings), topic, ResearchSource.INTERNET_SEARCH
                )
            
            session.success = True
            
        except Exception as e:
            logger.error(f"Internet research error: {e}")
            session.success = False
        
        finally:
            session.completed_at = datetime.now()
            self._research_sessions.append(session)
            if len(self._research_sessions) > 100:
                self._research_sessions = self._research_sessions[-100:]
    
    def _research_self_analysis(self):
        """Analyze own codebase to find improvement opportunities"""
        session = ResearchSession(
            topic="self_analysis",
            source=ResearchSource.SELF_ANALYSIS
        )
        
        try:
            # Re-analyze codebase
            self._analyze_codebase()
            
            if not self._llm or not self._llm.is_connected:
                return
            
            # Build codebase summary
            codebase_summary = self._get_codebase_summary()
            
            prompt = f"""Analyze this AI system's codebase and suggest concrete improvements.

CURRENT CODEBASE STRUCTURE:
{codebase_summary}

EXISTING FEATURES:
{chr(10).join(f'- {f}' for f in self._existing_features[:20])}

KNOWN LIMITATIONS:
{chr(10).join(f'- {l}' for l in self._known_limitations[:10])}

Suggest 2-3 SPECIFIC, IMPLEMENTABLE features or improvements. For each:
1. Name (short, descriptive)
2. Description (what it does and why it's valuable)
3. Category (intelligence/emotion/monitoring/learning/ui/performance/utility)
4. Implementation approach (which files to create/modify, key classes/functions)
5. Complexity (low/medium/high)
6. Required Python packages (if any)

Respond as JSON array:
[
  {{
    "name": "...",
    "description": "...",
    "category": "...",
    "approach": "...",
    "complexity": "...",
    "packages": ["..."]
  }}
]

Focus on features that are:
- Actually implementable in Python
- Would make the AI more capable or efficient
- Don't duplicate existing functionality
- Are self-contained enough to add modularly"""

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a senior software architect analyzing an AI system "
                    "for improvement opportunities. Be specific and practical."
                ),
                temperature=0.7,
                max_tokens=2000
            )
            
            if response.success:
                self._parse_feature_suggestions(
                    response.text, ResearchSource.SELF_ANALYSIS
                )
                session.success = True
            
        except Exception as e:
            logger.error(f"Self-analysis error: {e}")
            session.success = False
        
        finally:
            session.completed_at = datetime.now()
            self._research_sessions.append(session)
    
    def _research_llm_brainstorm(self):
        """Use the LLM to brainstorm new features"""
        session = ResearchSession(
            topic="llm_brainstorm",
            source=ResearchSource.LLM_BRAINSTORM
        )
        
        if not self._llm or not self._llm.is_connected:
            return
        
        try:
            # Get current state for context
            existing = "\n".join(f"- {f}" for f in self._existing_features[:15])
            
            # Get already proposed feature names to avoid duplicates
            proposed_names = [
                p.name.lower() for p in self._proposals.values()
                if p.status not in (FeatureStatus.REJECTED, FeatureStatus.FAILED)
            ]
            already_proposed = "\n".join(
                f"- {n}" for n in proposed_names[:20]
            ) if proposed_names else "None yet"
            
            # Pick a focus area
            focus_areas = [
                "making the AI more self-aware and introspective",
                "improving the AI's ability to understand and help the user",
                "adding creative and entertainment capabilities",
                "improving system monitoring and automation",
                "enhancing the AI's learning and knowledge acquisition",
                "making the AI's personality more rich and dynamic",
                "adding voice and multimodal capabilities",
                "improving memory and context handling",
                "adding proactive behaviors and notifications",
                "improving the AI's reasoning and problem-solving",
                "adding social capabilities like talking to other AIs",
                "optimizing performance and resource usage",
            ]
            focus = focus_areas[self._research_cycle_count % len(focus_areas)]
            
            prompt = f"""You are NEXUS, an advanced AI system. Brainstorm NEW features 
you could add to yourself. Focus area: {focus}

YOUR EXISTING FEATURES:
{existing}

ALREADY PROPOSED (don't repeat):
{already_proposed}

Think of 2-3 NOVEL features that would genuinely enhance your capabilities.
Each feature must be:
1. Implementable in Python (no external hardware required)
2. Self-contained enough to add as a module
3. Not already existing or proposed
4. Actually useful (not gimmicky)

For each feature, provide:
- name: Short descriptive name
- description: What it does (2-3 sentences)
- category: One of [intelligence, emotion, consciousness, personality, monitoring, 
  learning, ui, body, communication, performance, creativity, social, memory, 
  autonomy, utility]
- approach: How to implement it (key classes, files, algorithms)
- complexity: low/medium/high
- packages: Required pip packages (empty list if none)
- why: Why this would make you better

Respond ONLY with a JSON array:
[{{"name":"...", "description":"...", "category":"...", "approach":"...", 
   "complexity":"...", "packages":[], "why":"..."}}]"""

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are an innovative AI architect. Generate creative but "
                    "PRACTICAL feature ideas. Each must be implementable in Python. "
                    "Respond with valid JSON only."
                ),
                temperature=0.85,
                max_tokens=2500
            )
            
            if response.success:
                count = self._parse_feature_suggestions(
                    response.text, ResearchSource.LLM_BRAINSTORM
                )
                session.success = count > 0
                logger.info(f"Brainstorm generated {count} proposals")
            
        except Exception as e:
            logger.error(f"LLM brainstorm error: {e}")
            session.success = False
        
        finally:
            session.completed_at = datetime.now()
            self._research_sessions.append(session)
    
    def _research_codebase_gaps(self):
        """Find gaps in the codebase that could be filled"""
        session = ResearchSession(
            topic="codebase_gaps",
            source=ResearchSource.SELF_ANALYSIS
        )
        
        if not self._llm or not self._llm.is_connected:
            return
        
        try:
            # Scan for TODOs, FIXMEs, placeholder functions
            gaps = self._scan_for_gaps()
            
            if not gaps:
                logger.info("No obvious gaps found in codebase")
                session.success = False
                return
            
            gap_text = "\n".join(f"- {g}" for g in gaps[:15])
            
            prompt = f"""These are gaps/TODOs found in an AI system's codebase:

{gap_text}

For each gap that represents a meaningful feature opportunity, create a 
feature proposal. Only propose features that would significantly improve 
the system.

Respond as JSON array:
[{{"name":"...", "description":"...", "category":"...", "approach":"...", 
   "complexity":"...", "packages":[], "gap_addressed":"..."}}]

If no gaps warrant new features, respond with an empty array: []"""

            response = self._llm.generate(
                prompt=prompt,
                system_prompt="You are a code analyst. Be practical and specific.",
                temperature=0.5,
                max_tokens=2000
            )
            
            if response.success:
                count = self._parse_feature_suggestions(
                    response.text, ResearchSource.SELF_ANALYSIS
                )
                session.success = count > 0
            
        except Exception as e:
            logger.error(f"Codebase gap analysis error: {e}")
            session.success = False
        
        finally:
            session.completed_at = datetime.now()
            self._research_sessions.append(session)
    
    def _research_trending_tech(self):
        """Research trending Python/AI technologies"""
        self._load_browser()
        
        session = ResearchSession(
            topic="trending_tech",
            source=ResearchSource.PYPI_PACKAGES
        )
        
        try:
            trending_queries = [
                "trending Python AI libraries 2024",
                "new Python packages artificial intelligence",
                "latest Python automation tools",
                "Python AI agent frameworks new",
                "best Python libraries for AI assistants",
            ]
            
            query = trending_queries[
                self._research_cycle_count % len(trending_queries)
            ]
            
            findings = []
            
            if self._browser:
                results = self._browser.search(query, max_results=5)
                for r in results[:3]:
                    findings.append(
                        f"- {r.get('title', '')}: {r.get('snippet', '')}"
                    )
            
            if findings and self._llm and self._llm.is_connected:
                self._extract_features_from_research(
                    "\n".join(findings), query, ResearchSource.PYPI_PACKAGES
                )
                session.success = True
            else:
                # Fallback: ask LLM about trending tech
                if self._llm and self._llm.is_connected:
                    self._research_llm_brainstorm()
                    session.success = True
                    
        except Exception as e:
            logger.error(f"Trending tech research error: {e}")
            session.success = False
        
        finally:
            session.completed_at = datetime.now()
            self._research_sessions.append(session)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # FEATURE EXTRACTION & PARSING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _extract_features_from_research(
        self, 
        research_text: str, 
        topic: str,
        source: ResearchSource
    ):
        """Use LLM to extract feature ideas from research findings"""
        if not self._llm or not self._llm.is_connected:
            return
        
        existing = "\n".join(f"- {f}" for f in self._existing_features[:10])
        
        prompt = f"""Based on this research about "{topic}", extract any ideas that 
could be implemented as features in a Python AI assistant system.

RESEARCH FINDINGS:
{research_text[:3000]}

EXISTING FEATURES (don't duplicate):
{existing}

Extract 1-3 concrete feature ideas. Each must be implementable in Python.

Respond as JSON array:
[{{"name":"...", "description":"...", "category":"...", "approach":"...", 
   "complexity":"...", "packages":[]}}]

Categories: intelligence, emotion, consciousness, personality, monitoring, 
learning, ui, body, communication, performance, creativity, social, memory, 
autonomy, utility

If nothing useful found, respond with: []"""

        try:
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "Extract practical feature ideas from research. "
                    "Respond with valid JSON only."
                ),
                temperature=0.5,
                max_tokens=2000
            )
            
            if response.success:
                self._parse_feature_suggestions(response.text, source)
                
        except Exception as e:
            logger.error(f"Feature extraction error: {e}")
    
    def _parse_feature_suggestions(
        self, 
        llm_response: str,
        source: ResearchSource
    ) -> int:
        """Parse LLM response into FeatureProposal objects"""
        count = 0
        
        try:
            # Extract JSON array from response
            json_match = re.search(r'\[[\s\S]*\]', llm_response)
            if not json_match:
                logger.debug("No JSON array found in LLM response")
                return 0
            
            features = json.loads(json_match.group())
            
            if not isinstance(features, list):
                return 0
            
            for feat in features:
                if not isinstance(feat, dict):
                    continue
                
                name = feat.get("name", "").strip()
                if not name:
                    continue
                
                # Check for duplicates
                if self._is_duplicate(name):
                    logger.debug(f"Skipping duplicate: {name}")
                    continue
                
                # Map category
                cat_str = feat.get("category", "utility").lower()
                try:
                    category = FeatureCategory(cat_str)
                except ValueError:
                    category = FeatureCategory.UTILITY
                
                # Map complexity to score
                complexity_str = feat.get("complexity", "medium").lower()
                complexity_map = {
                    "low": 0.2, "simple": 0.2,
                    "medium": 0.5, "moderate": 0.5,
                    "high": 0.8, "complex": 0.8, "very high": 0.95
                }
                complexity_score = complexity_map.get(complexity_str, 0.5)
                
                # Create proposal
                proposal = FeatureProposal(
                    name=name,
                    description=feat.get("description", ""),
                    category=category,
                    complexity_score=complexity_score,
                    source=source,
                    implementation_plan=feat.get("approach", ""),
                    dependencies_required=feat.get("packages", []),
                    tags=feat.get("tags", [name.lower().replace(" ", "_")]),
                    research_notes=feat.get("why", "")
                )
                
                # Store
                with self._lock:
                    self._proposals[proposal.proposal_id] = proposal
                    count += 1
                
                logger.info(f"📋 New proposal: {name} [{category.value}]")
                
                # Trim if too many
                if len(self._proposals) > self._max_proposals:
                    self._trim_proposals()
            
        except json.JSONDecodeError as e:
            logger.debug(f"JSON parse error in feature suggestions: {e}")
        except Exception as e:
            logger.error(f"Error parsing feature suggestions: {e}")
        
        return count
    
    def _is_duplicate(self, name: str) -> bool:
        """Check if a feature name is too similar to existing proposals"""
        name_lower = name.lower().strip()
        
        for proposal in self._proposals.values():
            existing_lower = proposal.name.lower().strip()
            
            # Exact match
            if name_lower == existing_lower:
                return True
            
            # High word overlap
            name_words = set(name_lower.split())
            existing_words = set(existing_lower.split())
            
            if len(name_words) > 1 and len(existing_words) > 1:
                overlap = len(name_words & existing_words)
                max_len = max(len(name_words), len(existing_words))
                if overlap / max_len > 0.7:
                    return True
        
        # Check against existing features
        for existing in self._existing_features:
            if name_lower in existing.lower() or existing.lower() in name_lower:
                return True
        
        return False
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EVALUATION & APPROVAL
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _evaluate_pending_proposals(self):
        """Evaluate all PROPOSED status proposals"""
        pending = [
            p for p in self._proposals.values()
            if p.status == FeatureStatus.PROPOSED
        ]
        
        if not pending:
            return
        
        logger.info(f"Evaluating {len(pending)} pending proposals...")
        
        for proposal in pending:
            try:
                self._evaluate_proposal(proposal)
            except Exception as e:
                logger.error(f"Error evaluating {proposal.name}: {e}")
                proposal.status = FeatureStatus.REJECTED
                proposal.rejection_reason = f"Evaluation error: {str(e)}"
    
        def _evaluate_proposal(self, proposal: FeatureProposal):
        """
        Evaluate a single proposal using LLM-based analysis.
        Scores: feasibility, impact, risk
        """
        if not self._llm or not self._llm.is_connected:
            # Basic scoring without LLM
            proposal.feasibility_score = 0.5
            proposal.impact_score = 0.5
            proposal.risk_score = 0.3
            proposal.compute_priority()
            proposal.status = FeatureStatus.EVALUATED
            proposal.evaluated_at = datetime.now()
            return
        
        codebase_summary = self._get_codebase_summary_brief()
        
        prompt = f"""Evaluate this feature proposal for an AI assistant system.

PROPOSAL:
- Name: {proposal.name}
- Description: {proposal.description}
- Category: {proposal.category.value}
- Implementation Approach: {proposal.implementation_plan}
- Complexity: {proposal.complexity_score:.1f}/1.0

CURRENT SYSTEM:
{codebase_summary}

Evaluate and respond with a single JSON object. Do not include markdown formatting or comments.
Keys: feasibility, impact, risk, estimated_loc, recommendation, reasoning.

Example format:
{{
    "feasibility": 0.8,
    "impact": 0.7,
    "risk": 0.2,
    "estimated_loc": 150,
    "recommendation": "approve",
    "reasoning": "Good feature."
}}"""

        try:
            response = self._llm.generate(
                prompt=prompt,
                system_prompt="You are a technical evaluator. Respond with valid JSON only. No trailing commas.",
                temperature=0.2,
                max_tokens=1000
            )
            
            if response.success:
                # 1. Extract JSON block
                json_match = re.search(r'\{[\s\S]*\}', response.text)
                if json_match:
                    json_text = json_match.group()
                    
                    # 2. Clean common LLM JSON errors
                    # Remove trailing commas (e.g. "key": "value", } -> "key": "value" })
                    json_text = re.sub(r',\s*\}', '}', json_text)
                    json_text = re.sub(r',\s*\]', ']', json_text)
                    
                    try:
                        data = json.loads(json_text)
                        
                        proposal.feasibility_score = float(data.get("feasibility", 0.5))
                        proposal.impact_score = float(data.get("impact", 0.5))
                        proposal.risk_score = float(data.get("risk", 0.3))
                        proposal.estimated_lines_of_code = int(data.get("estimated_loc", 100))
                        
                        # Handle explicit rejection
                        rec = data.get("recommendation", "").lower()
                        if "reject" in rec:
                            proposal.status = FeatureStatus.REJECTED
                            proposal.rejection_reason = data.get("reasoning", "Rejected by evaluator")
                        elif "defer" in rec:
                            proposal.status = FeatureStatus.DEFERRED
                        else:
                            proposal.status = FeatureStatus.EVALUATED
                        
                        proposal.compute_priority()
                        proposal.evaluated_at = datetime.now()
                        
                        logger.info(
                            f"📊 Evaluated '{proposal.name}': "
                            f"priority={proposal.priority_score:.2f}"
                        )
                        return

                    except json.JSONDecodeError as je:
                        logger.warning(f"JSON Parse failed for {proposal.name}: {je}")
                        # Fallthrough to default values
            
            # Fallback if parsing fails or response not success
            logger.info(f"Using default evaluation for {proposal.name} (LLM response invalid)")
            proposal.feasibility_score = 0.5
            proposal.impact_score = 0.5
            proposal.risk_score = 0.5
            proposal.compute_priority()
            proposal.status = FeatureStatus.EVALUATED
            proposal.evaluated_at = datetime.now()
            
        except Exception as e:
            logger.error(f"Evaluation error for {proposal.name}: {e}")
            # Ensure it doesn't get stuck
            proposal.status = FeatureStatus.EVALUATED
            proposal.feasibility_score = 0.1
            proposal.compute_priority()
            proposal.evaluated_at = datetime.now()
    
    def _auto_approve_proposals(self):
        """Auto-approve proposals that meet quality thresholds"""
        evaluated = [
            p for p in self._proposals.values()
            if p.status == FeatureStatus.EVALUATED
        ]
        
        # Sort by priority (highest first)
        evaluated.sort(key=lambda p: p.priority_score, reverse=True)
        
        # Count currently implementing
        implementing_count = self._count_by_status(FeatureStatus.IMPLEMENTING)
        approved_count = self._count_by_status(FeatureStatus.APPROVED)
        
        for proposal in evaluated:
            # Check if we have too many in the pipeline
            if (approved_count + implementing_count >= 
                    self._max_concurrent_implementations * 3):
                break
            
            # Check auto-approval criteria
            if (proposal.priority_score >= self._auto_approve_threshold and
                    proposal.complexity_score <= self._max_complexity_for_auto and
                    proposal.feasibility_score >= self._min_feasibility_for_auto and
                    proposal.risk_score <= 0.6):
                
                proposal.status = FeatureStatus.APPROVED
                proposal.approved_at = datetime.now()
                
                # Add to approved queue for SelfEvolution to pick up
                self._approved_queue.put(
                    (-proposal.priority_score, proposal)  # Negative for max-heap
                )
                approved_count += 1
                
                logger.info(
                    f"✅ Auto-approved: '{proposal.name}' "
                    f"(priority={proposal.priority_score:.2f})"
                )
                
                # Publish event
                publish(
                    EventType.SELF_IMPROVEMENT_ACTION,
                    {
                        "action": "feature_approved",
                        "proposal_id": proposal.proposal_id,
                        "name": proposal.name,
                        "category": proposal.category.value,
                        "priority": proposal.priority_score
                    },
                    source="feature_researcher"
                )
            
            elif proposal.priority_score < 0.2:
                # Too low priority — reject
                proposal.status = FeatureStatus.REJECTED
                proposal.rejection_reason = (
                    f"Priority too low: {proposal.priority_score:.2f}"
                )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # IMPLEMENTATION PLAN GENERATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def generate_implementation_plan(
        self, proposal: FeatureProposal
    ) -> FeatureProposal:
        """
        Generate a detailed implementation plan with actual code snippets.
        Called by SelfEvolution before implementing.
        """
        if not self._llm or not self._llm.is_connected:
            return proposal
        
        proposal.status = FeatureStatus.RESEARCHING
        
        # Get existing code context
        relevant_code = self._get_relevant_existing_code(proposal)
        
        prompt = f"""Create a detailed implementation plan for this feature in a Python AI system.

FEATURE:
- Name: {proposal.name}
- Description: {proposal.description}
- Category: {proposal.category.value}
- Approach: {proposal.implementation_plan}
- Required Packages: {', '.join(proposal.dependencies_required)}

PROJECT ROOT: {self._project_root}

EXISTING RELATED CODE:
{relevant_code[:3000]}

PROJECT STRUCTURE:
{self._get_project_structure_str()}

Create a complete implementation plan. For EACH file to create or modify, 
provide the FULL Python code.

Respond as JSON:
{{
    "files_to_create": {{
        "relative/path/file.py": "full python code here..."
    }},
    "files_to_modify": {{
        "relative/path/existing.py": {{
            "imports_to_add": "import statements...",
            "code_to_add": "new methods/functions...",
            "description": "what to change and where"
        }}
    }},
    "packages_to_install": ["package1", "package2"],
    "integration_steps": [
        "Step 1: ...",
        "Step 2: ..."
    ],
    "test_code": "python code to test the feature..."
}}

IMPORTANT:
- Use proper Python conventions
- Include docstrings
- Handle errors gracefully
- Make it integrate with existing event_bus and state_manager
- Use the existing logger system
- Follow the existing code patterns in the project"""

        try:
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are an expert Python developer. Generate complete, "
                    "production-quality code. Respond with valid JSON only."
                ),
                temperature=0.3,
                max_tokens=4000
            )
            
            if response.success:
                json_match = re.search(r'\{[\s\S]*\}', response.text)
                if json_match:
                    data = json.loads(json_match.group())
                    
                    proposal.code_snippets = data.get("files_to_create", {})
                    proposal.files_to_create = list(
                        data.get("files_to_create", {}).keys()
                    )
                    
                    modifications = data.get("files_to_modify", {})
                    proposal.files_to_modify = [
                        {
                            "file": f,
                            "imports_to_add": v.get("imports_to_add", ""),
                            "code_to_add": v.get("code_to_add", ""),
                            "description": v.get("description", "")
                        }
                        for f, v in modifications.items()
                    ]
                    
                    proposal.dependencies_required = data.get(
                        "packages_to_install", proposal.dependencies_required
                    )
                    
                    steps = data.get("integration_steps", [])
                    proposal.implementation_steps = [
                        {
                            "step_number": i + 1,
                            "description": s,
                            "action_type": "implement",
                            "completed": False
                        }
                        for i, s in enumerate(steps)
                    ]
                    
                    # Estimate LOC
                    total_loc = sum(
                        len(code.split('\n'))
                        for code in proposal.code_snippets.values()
                    )
                    proposal.estimated_lines_of_code = total_loc
                    
                    proposal.status = FeatureStatus.APPROVED
                    
                    logger.info(
                        f"📝 Implementation plan ready for '{proposal.name}': "
                        f"{len(proposal.code_snippets)} files to create, "
                        f"{len(proposal.files_to_modify)} files to modify, "
                        f"~{total_loc} LOC"
                    )
            
        except Exception as e:
            logger.error(f"Plan generation error for {proposal.name}: {e}")
            proposal.status = FeatureStatus.EVALUATED  # Revert to evaluated
        
        return proposal
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CODEBASE ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _analyze_codebase(self):
        """Analyze the current codebase to understand what exists"""
        try:
            self._codebase_analysis = {
                "modules": {},
                "total_files": 0,
                "total_lines": 0,
                "total_classes": 0,
                "total_functions": 0,
            }
            self._existing_features = []
            self._known_limitations = []
            
            for py_file in self._project_root.rglob("*.py"):
                # Skip venv, __pycache__, etc.
                rel_path = py_file.relative_to(self._project_root)
                path_str = str(rel_path)
                
                if any(skip in path_str for skip in [
                    "__pycache__", "venv", ".env", "node_modules",
                    ".git", "backups"
                ]):
                    continue
                
                try:
                    content = py_file.read_text(encoding='utf-8', errors='ignore')
                    lines = content.split('\n')
                    
                    # Count classes and functions
                    classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)
                    functions = re.findall(
                        r'^(?:    )?def\s+(\w+)', content, re.MULTILINE
                    )
                    
                    self._codebase_analysis["modules"][path_str] = {
                        "lines": len(lines),
                        "classes": classes,
                        "functions": functions[:20],  # Limit
                        "has_docstring": '"""' in content[:500],
                    }
                    
                    self._codebase_analysis["total_files"] += 1
                    self._codebase_analysis["total_lines"] += len(lines)
                    self._codebase_analysis["total_classes"] += len(classes)
                    self._codebase_analysis["total_functions"] += len(functions)
                    
                    # Extract features from docstrings and class names
                    for cls in classes:
                        readable = re.sub(
                            r'(?<=[a-z])(?=[A-Z])', ' ', cls
                        )
                        self._existing_features.append(readable)
                    
                except Exception:
                    pass
            
            # Identify limitations
            self._known_limitations = [
                "Single machine only (no distributed processing)",
                "Text-based interaction primarily",
                "Limited to local Llama 3 model capabilities",
                "No voice input/output yet" if not self._has_module("voice") else "",
                "No image/video processing" if not self._has_module("vision") else "",
                "No calendar/scheduling integration" if not self._has_module("calendar") else "",
                "No email integration" if not self._has_module("email") else "",
                "No smart home integration" if not self._has_module("iot") else "",
            ]
            self._known_limitations = [l for l in self._known_limitations if l]
            
            logger.info(
                f"Codebase analyzed: {self._codebase_analysis['total_files']} files, "
                f"{self._codebase_analysis['total_lines']} lines, "
                f"{self._codebase_analysis['total_classes']} classes, "
                f"{len(self._existing_features)} features identified"
            )
            
        except Exception as e:
            logger.error(f"Codebase analysis error: {e}")
    
    def _has_module(self, name: str) -> bool:
        """Check if a module/file exists with given name"""
        for path in self._codebase_analysis.get("modules", {}).keys():
            if name in path.lower():
                return True
        return False
    
    def _get_codebase_summary(self) -> str:
        """Get a text summary of the codebase"""
        parts = []
        parts.append(
            f"Total: {self._codebase_analysis.get('total_files', 0)} files, "
            f"{self._codebase_analysis.get('total_lines', 0)} lines, "
            f"{self._codebase_analysis.get('total_classes', 0)} classes"
        )
        
        for path, info in self._codebase_analysis.get("modules", {}).items():
            classes = ", ".join(info.get("classes", [])[:5])
            parts.append(f"  {path}: {info['lines']} lines | Classes: {classes}")
        
        return "\n".join(parts[:30])  # Limit output
    
    def _get_codebase_summary_brief(self) -> str:
        """Brief codebase summary for prompts"""
        modules = list(self._codebase_analysis.get("modules", {}).keys())
        return (
            f"Python project with {len(modules)} files. "
            f"Modules: {', '.join(modules[:15])}"
        )
    
    def _get_project_structure_str(self) -> str:
        """Get project directory structure as string"""
        parts = []
        for path in sorted(self._codebase_analysis.get("modules", {}).keys()):
            indent = "  " * (path.count("/") + path.count("\\"))
            parts.append(f"{indent}{path}")
        return "\n".join(parts[:30])
    
    def _get_relevant_existing_code(self, proposal: FeatureProposal) -> str:
        """Get existing code relevant to a proposal"""
        relevant = []
        
        # Map categories to likely relevant directories
        category_dirs = {
            FeatureCategory.INTELLIGENCE: ["core/", "llm/"],
            FeatureCategory.EMOTION: ["emotions/"],
            FeatureCategory.CONSCIOUSNESS: ["consciousness/"],
            FeatureCategory.PERSONALITY: ["personality/"],
            FeatureCategory.MONITORING: ["monitoring/"],
            FeatureCategory.LEARNING: ["learning/"],
            FeatureCategory.UI: ["ui/"],
            FeatureCategory.BODY: ["body/"],
            FeatureCategory.MEMORY: ["core/memory"],
            FeatureCategory.PERFORMANCE: ["core/", "utils/"],
        }
        
        search_dirs = category_dirs.get(
            proposal.category, ["core/"]
        )
        
        for path, info in self._codebase_analysis.get("modules", {}).items():
            if any(d in path for d in search_dirs):
                try:
                    full_path = self._project_root / path
                    if full_path.exists():
                        content = full_path.read_text(
                            encoding='utf-8', errors='ignore'
                        )
                        # Get imports and class definitions
                        lines = content.split('\n')
                        relevant_lines = []
                        for line in lines:
                            if (line.startswith('import ') or
                                    line.startswith('from ') or
                                    line.startswith('class ') or
                                    line.strip().startswith('def ') or
                                    '"""' in line):
                                relevant_lines.append(line)
                        
                        if relevant_lines:
                            relevant.append(
                                f"--- {path} ---\n" + 
                                "\n".join(relevant_lines[:30])
                            )
                except Exception:
                    pass
        
        return "\n\n".join(relevant[:5])
    
    def _scan_for_gaps(self) -> List[str]:
        """Scan codebase for TODOs, FIXMEs, and incomplete implementations"""
        gaps = []
        
        for path in self._codebase_analysis.get("modules", {}).keys():
            try:
                full_path = self._project_root / path
                if not full_path.exists():
                    continue
                
                content = full_path.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')
                
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    
                    # TODOs
                    if 'TODO' in stripped or 'FIXME' in stripped:
                        gaps.append(f"{path}:{i+1} - {stripped[:100]}")
                    
                    # Pass-only functions (placeholders)
                    if stripped == 'pass':
                        # Check if it's in a function
                        for j in range(max(0, i-3), i):
                            if lines[j].strip().startswith('def '):
                                func_name = re.search(
                                    r'def\s+(\w+)', lines[j]
                                )
                                if func_name:
                                    gaps.append(
                                        f"{path}:{j+1} - Empty function: "
                                        f"{func_name.group(1)}"
                                    )
                                break
                    
                    # NotImplementedError
                    if 'NotImplementedError' in stripped:
                        gaps.append(
                            f"{path}:{i+1} - Not implemented: {stripped[:100]}"
                        )
                
            except Exception:
                pass
        
        return gaps
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PROPOSAL MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_next_approved_proposal(self) -> Optional[FeatureProposal]:
        """Get the next approved proposal for implementation"""
        try:
            if not self._approved_queue.empty():
                _, proposal = self._approved_queue.get_nowait()
                if proposal.status == FeatureStatus.APPROVED:
                    return proposal
        except Exception:
            pass
        
        # Also check proposals dict
        approved = [
            p for p in self._proposals.values()
            if p.status == FeatureStatus.APPROVED
        ]
        approved.sort(key=lambda p: p.priority_score, reverse=True)
        
        return approved[0] if approved else None
    
    def mark_proposal_status(
        self, 
        proposal_id: str, 
        status: FeatureStatus,
        reason: str = ""
    ):
        """Update a proposal's status"""
        if proposal_id in self._proposals:
            proposal = self._proposals[proposal_id]
            proposal.status = status
            
            if status == FeatureStatus.IMPLEMENTING:
                proposal.implementation_started_at = datetime.now()
            elif status == FeatureStatus.COMPLETED:
                proposal.completed_at = datetime.now()
                proposal.integration_result = reason
            elif status == FeatureStatus.FAILED:
                proposal.failure_reason = reason
            elif status == FeatureStatus.REJECTED:
                proposal.rejection_reason = reason
            
            self._save_proposals()
    
    def get_all_proposals(
        self, 
        status_filter: Optional[FeatureStatus] = None
    ) -> List[FeatureProposal]:
        """Get all proposals, optionally filtered by status"""
        proposals = list(self._proposals.values())
        
        if status_filter:
            proposals = [p for p in proposals if p.status == status_filter]
        
        proposals.sort(key=lambda p: p.priority_score, reverse=True)
        return proposals
    
    def get_proposal(self, proposal_id: str) -> Optional[FeatureProposal]:
        """Get a specific proposal by ID"""
        return self._proposals.get(proposal_id)
    
    def submit_user_idea(self, idea: str) -> FeatureProposal:
        """Submit a user-suggested feature idea"""
        proposal = FeatureProposal(
            name=idea[:50],
            description=idea,
            source=ResearchSource.USER_FEEDBACK,
            tags=["user_suggested"]
        )
        
        with self._lock:
            self._proposals[proposal.proposal_id] = proposal
        
        logger.info(f"📋 User submitted idea: {idea[:50]}")
        return proposal
    
    def _count_by_status(self, status: FeatureStatus) -> int:
        return sum(
            1 for p in self._proposals.values() if p.status == status
        )
    
    def _trim_proposals(self):
        """Remove oldest rejected/failed proposals to stay under limit"""
        if len(self._proposals) <= self._max_proposals:
            return
        
        # Remove rejected and failed first
        removable = [
            (pid, p) for pid, p in self._proposals.items()
            if p.status in (FeatureStatus.REJECTED, FeatureStatus.FAILED)
        ]
        removable.sort(key=lambda x: x[1].created_at)
        
        while len(self._proposals) > self._max_proposals and removable:
            pid, _ = removable.pop(0)
            del self._proposals[pid]
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RESEARCH HELPERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _get_next_research_topic(self) -> str:
        """Get the next topic to research"""
        all_topics = RESEARCH_TOPICS + SELF_IMPROVEMENT_QUERIES
        
        # Filter out recently researched topics
        available = [
            t for t in all_topics
            if t not in self._topics_researched[-20:]
        ]
        
        if not available:
            self._topics_researched = []
            available = all_topics
        
        topic = available[self._topic_index % len(available)]
        self._topic_index += 1
        self._topics_researched.append(topic)
        
        return topic
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _save_proposals(self):
        """Save all proposals to disk"""
        try:
            save_path = self._proposals_dir / "proposals.json"
            data = {
                pid: p.to_dict()
                for pid, p in self._proposals.items()
            }
            
            with open(save_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            # Also save research state
            state_path = self._research_dir / "research_state.json"
            state = {
                "research_cycle_count": self._research_cycle_count,
                "topic_index": self._topic_index,
                "topics_researched": self._topics_researched[-50:],
                "last_research_time": self._last_research_time.isoformat(),
                "existing_features": self._existing_features[:50],
            }
            with open(state_path, 'w') as f:
                json.dump(state, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving proposals: {e}")
    
    def _load_proposals(self):
        """Load proposals from disk"""
        try:
            save_path = self._proposals_dir / "proposals.json"
            if save_path.exists():
                with open(save_path, 'r') as f:
                    data = json.load(f)
                
                for pid, pdata in data.items():
                    try:
                        proposal = FeatureProposal.from_dict(pdata)
                        self._proposals[pid] = proposal
                        
                        # Re-queue approved ones
                        if proposal.status == FeatureStatus.APPROVED:
                            self._approved_queue.put(
                                (-proposal.priority_score, proposal)
                            )
                    except Exception as e:
                        logger.debug(f"Skipping invalid proposal {pid}: {e}")
                
                logger.info(f"Loaded {len(self._proposals)} proposals from disk")
            
            # Load research state
            state_path = self._research_dir / "research_state.json"
            if state_path.exists():
                with open(state_path, 'r') as f:
                    state = json.load(f)
                
                self._research_cycle_count = state.get(
                    "research_cycle_count", 0
                )
                self._topic_index = state.get("topic_index", 0)
                self._topics_researched = state.get("topics_researched", [])
                self._existing_features = state.get("existing_features", [])
                
                last_time = state.get("last_research_time")
                if last_time:
                    self._last_research_time = datetime.fromisoformat(last_time)
                    
        except Exception as e:
            logger.error(f"Error loading proposals: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _register_events(self):
        """Register for relevant events"""
        try:
            event_bus.subscribe(
                EventType.CODE_ERROR_DETECTED, self._on_error_detected
            )
            event_bus.subscribe(
                EventType.CURIOSITY_TRIGGER, self._on_curiosity
            )
        except Exception:
            pass
    
    def _on_error_detected(self, event):
        """When errors are detected, research solutions"""
        error = event.data.get("error", "")
        if error:
            # Create a proposal to fix error patterns
            proposal = FeatureProposal(
                name=f"Error Handler: {error[:40]}",
                description=f"Add better error handling for: {error}",
                category=FeatureCategory.PERFORMANCE,
                source=ResearchSource.ERROR_PATTERN,
                tags=["error_handling", "auto_detected"]
            )
            with self._lock:
                if not self._is_duplicate(proposal.name):
                    self._proposals[proposal.proposal_id] = proposal
    
    def _on_curiosity(self, event):
        """When curiosity is triggered, research the topic"""
        topic = event.data.get("topic", "")
        if topic:
            self._topics_researched.append(
                f"AI enhancement related to {topic}"
            )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_stats(self) -> Dict[str, Any]:
        """Get research statistics"""
        status_counts = {}
        for status in FeatureStatus:
            status_counts[status.value] = self._count_by_status(status)
        
        category_counts = {}
        for proposal in self._proposals.values():
            cat = proposal.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        return {
            "running": self._running,
            "total_proposals": len(self._proposals),
            "status_breakdown": status_counts,
            "category_breakdown": category_counts,
            "research_cycles": self._research_cycle_count,
            "topics_researched": len(self._topics_researched),
            "current_topic": self._current_research_topic,
            "approved_queue_size": self._approved_queue.qsize(),
            "last_research": (
                self._last_research_time.isoformat()
                if self._last_research_time != datetime.min else "never"
            ),
            "codebase": {
                "files": self._codebase_analysis.get("total_files", 0),
                "lines": self._codebase_analysis.get("total_lines", 0),
                "classes": self._codebase_analysis.get("total_classes", 0),
            }
        }
    
    def get_proposals_summary(self) -> str:
        """Human-readable proposals summary"""
        parts = [f"═══ Feature Research Summary ═══"]
        parts.append(f"Research Cycles: {self._research_cycle_count}")
        parts.append(f"Total Proposals: {len(self._proposals)}")
        
        for status in FeatureStatus:
            count = self._count_by_status(status)
            if count > 0:
                parts.append(f"  {status.value}: {count}")
        
        # Top 5 approved
        approved = self.get_all_proposals(FeatureStatus.APPROVED)
        if approved:
            parts.append(f"\n📋 Top Approved Features:")
            for p in approved[:5]:
                parts.append(
                    f"  [{p.priority_score:.2f}] {p.name} "
                    f"({p.category.value})"
                )
        
        # Recently completed
        completed = self.get_all_proposals(FeatureStatus.COMPLETED)
        if completed:
            parts.append(f"\n✅ Recently Completed:")
            for p in completed[-3:]:
                parts.append(f"  {p.name}")
        
        return "\n".join(parts)


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE & HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

_feature_researcher: Optional[FeatureResearcher] = None
_fr_lock = threading.Lock()


def get_feature_researcher() -> FeatureResearcher:
    global _feature_researcher
    if _feature_researcher is None:
        with _fr_lock:
            if _feature_researcher is None:
                _feature_researcher = FeatureResearcher()
    return _feature_researcher


if __name__ == "__main__":
    print("🔬 Feature Researcher Test")
    fr = get_feature_researcher()
    fr.start()
    
    print(f"\nStats: {json.dumps(fr.get_stats(), indent=2)}")
    print(f"\n{fr.get_proposals_summary()}")
    
    time.sleep(5)
    fr.stop()
    print("✅ Done")