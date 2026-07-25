"""
NEXUS AI - Research Intelligence
═══════════════════════════════════════════════════════════════════════════════
Intelligent research orchestration that enhances the ResearchAgent.

Capabilities:
  • Smart topic prioritization based on relevance and gaps
  • Research depth optimization (when to go deep vs broad)
  • Cross-reference validation across multiple sources
  • Insight extraction and synthesis
  • Research fatigue detection (avoid over-researching)
  • Learning from research effectiveness

This makes NEXUS's autonomous research more efficient and targeted.
═══════════════════════════════════════════════════════════════════════════════
"""

import threading
import time
import json
import re
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import deque, Counter
from enum import Enum, auto

import sys

from config import DATA_DIR, NEXUS_CONFIG
from utils.logger import get_logger, log_learning
from core.event_bus import EventType, publish, subscribe, Event
from core.state_manager import state_manager

logger = get_logger("research_intelligence")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class ResearchPriority(Enum):
    CRITICAL = 5    # Urgent knowledge gap
    HIGH = 4        # Important for current goal
    MODERATE = 3    # Valuable but not urgent
    LOW = 2         # Nice to have
    EXPLORATORY = 1 # Serendipitous learning

class ResearchDepth(Enum):
    QUICK = 1       # Single source, basic summary
    STANDARD = 2    # Multiple sources, cross-reference
    DEEP = 3        # Comprehensive, synthesis, examples
    EXHAUSTIVE = 4  # Academic-level, all sources

class ResearchStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    DEFERRED = "deferred"

@dataclass
class ResearchTopic:
    """A topic to research with metadata"""
    topic_id: str = ""
    topic: str = ""
    question: str = ""
    priority: ResearchPriority = ResearchPriority.MODERATE
    depth: ResearchDepth = ResearchDepth.STANDARD
    status: ResearchStatus = ResearchStatus.PENDING
    source: str = ""  # curiosity, user_request, gap_detection
    related_topics: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    created_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    sources_consulted: List[str] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    usefulness_score: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["priority"] = self.priority.name
        d["depth"] = self.depth.name
        d["status"] = self.status.value
        return d

@dataclass
class ResearchSession:
    """A research session with results"""
    session_id: str = ""
    topic: str = ""
    started_at: str = ""
    ended_at: str = ""
    sources_queried: int = 0
    pages_fetched: int = 0
    insights_extracted: int = 0
    knowledge_stored: int = 0
    tokens_used: int = 0
    duration_seconds: float = 0.0
    quality_score: float = 0.0
    errors: List[str] = field(default_factory=list)

@dataclass
class KnowledgeGap:
    """Detected gap in knowledge"""
    gap_id: str = ""
    area: str = ""
    description: str = ""
    impact: float = 0.5  # How much this gap affects capabilities
    frequency: int = 0   # How often this gap is encountered
    last_encountered: str = ""

@dataclass
class ResearchIntelligenceStats:
    """Statistics for research intelligence"""
    total_topics_researched: int = 0
    successful_researches: int = 0
    failed_researches: int = 0
    avg_quality_score: float = 0.0
    avg_duration_seconds: float = 0.0
    total_insights: int = 0
    knowledge_gaps_filled: int = 0
    research_efficiency: float = 0.0  # insights per minute

# ═══════════════════════════════════════════════════════════════════════════════
# RESEARCH INTELLIGENCE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class ResearchIntelligence:
    """
    Intelligent research orchestration system.
    
    Features:
    1. Prioritize research topics intelligently
    2. Determine optimal research depth
    3. Detect and track knowledge gaps
    4. Synthesize insights from multiple sources
    5. Track research effectiveness
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
        self._data_dir = DATA_DIR / "research_intelligence"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # ──── State ────
        self._running = False
        self._llm = None
        self._knowledge_base = None

        # ──── Research queue ────
        self._research_queue: List[ResearchTopic] = []
        self._active_research: Optional[ResearchTopic] = None
        self._completed_research: deque = deque(maxlen=200)
        self._research_sessions: deque = deque(maxlen=100)

        # ──── Knowledge gaps ────
        self._knowledge_gaps: Dict[str, KnowledgeGap] = {}

        # ──── Intelligence state ────
        self._research_history: deque = deque(maxlen=500)
        self._topic_effectiveness: Dict[str, List[float]] = {}  # topic -> [scores]
        self._source_reliability: Dict[str, float] = {}  # source -> reliability
        self._research_fatigue: float = 0.0  # Increases with research, decreases with rest

        # ──── Stats ────
        self._stats = ResearchIntelligenceStats()

        # ──── Background thread ────
        self._analysis_thread: Optional[threading.Thread] = None

        # ──── Load persisted data ────
        self._load_data()

        # ──── Subscribe to events ────
        subscribe(EventType.CURIOSITY_TRIGGER, self._on_curiosity_trigger)
        subscribe(EventType.LEARNING_COMPLETE, self._on_learning_complete)
        subscribe(EventType.LLM_RESPONSE, self._on_llm_response)

        logger.info("🔬 Research Intelligence initialized")

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start the research intelligence system"""
        if self._running:
            return

        self._running = True

        # Load dependencies
        try:
            from llm.llama_interface import llm
            self._llm = llm
        except ImportError:
            logger.warning("LLM not available for research intelligence")

        try:
            from learning.knowledge_base import knowledge_base
            self._knowledge_base = knowledge_base
        except ImportError:
            logger.warning("KnowledgeBase not available")

        # Start analysis thread
        self._analysis_thread = threading.Thread(
            target=self._analysis_loop,
            daemon=True,
            name="ResearchIntelligence"
        )
        self._analysis_thread.start()

        log_learning("🔬 Research Intelligence ACTIVE — smarter research enabled")

    def stop(self):
        """Stop and persist data"""
        self._running = False
        self._save_data()

        if self._analysis_thread and self._analysis_thread.is_alive():
            self._analysis_thread.join(timeout=5.0)

        logger.info("Research Intelligence stopped")

    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _on_curiosity_trigger(self, event: Event):
        """Handle curiosity-triggered research"""
        topic = event.data.get("topic", "")
        reason = event.data.get("reason", "")
        urgency = event.data.get("urgency", "moderate")

        if topic:
            priority = ResearchPriority.MODERATE
            if urgency == "high":
                priority = ResearchPriority.HIGH
            elif urgency == "critical":
                priority = ResearchPriority.CRITICAL

            self.queue_research(
                topic=topic,
                question=event.data.get("question", f"What is {topic}?"),
                source="curiosity",
                priority=priority
            )

    def _on_learning_complete(self, event: Event):
        """Handle learning completion"""
        topic = event.data.get("topic", "")
        success = event.data.get("success", True)

        if self._active_research and topic:
            self._active_research.status = ResearchStatus.COMPLETED
            self._active_research.completed_at = datetime.now().isoformat()
            self._active_research.quality_score = event.data.get("quality", 0.7)

            self._completed_research.append(self._active_research)
            self._stats.total_topics_researched += 1
            self._stats.successful_researches += 1

            # Update effectiveness tracking
            self._update_effectiveness(self._active_research)

            self._active_research = None

    def _on_llm_response(self, event: Event):
        """Monitor LLM responses for knowledge gaps"""
        user_input = event.data.get("user_input", "")
        response = event.data.get("response", "")

        # Detect potential knowledge gaps
        gap_indicators = [
            "I'm not sure about",
            "I don't have enough information",
            "I couldn't find",
            "I'm not familiar with",
            "This is outside my knowledge",
        ]

        for indicator in gap_indicators:
            if indicator.lower() in response.lower():
                # Extract potential gap topic
                self._detect_knowledge_gap(user_input, response, indicator)
                break

    # ═══════════════════════════════════════════════════════════════════════════
    # RESEARCH MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════

    def queue_research(
        self,
        topic: str,
        question: str = "",
        source: str = "manual",
        priority: ResearchPriority = ResearchPriority.MODERATE,
        depth: ResearchDepth = None,
        prerequisites: List[str] = None
    ) -> str:
        """Queue a topic for research"""

        # Check for duplicates
        for existing in self._research_queue:
            if existing.topic.lower() == topic.lower():
                # Boost priority if already queued
                if priority.value > existing.priority.value:
                    existing.priority = priority
                return existing.topic_id

        topic_id = hashlib.sha256(
            f"{topic}_{time.time()}".encode()
        ).hexdigest()[:12]

        # Determine optimal depth if not specified
        if depth is None:
            depth = self._determine_depth(topic, priority)

        research_topic = ResearchTopic(
            topic_id=topic_id,
            topic=topic,
            question=question or f"What is {topic}?",
            priority=priority,
            depth=depth,
            status=ResearchStatus.PENDING,
            source=source,
            prerequisites=prerequisites or [],
            created_at=datetime.now().isoformat()
        )

        # Insert sorted by priority
        inserted = False
        for i, existing in enumerate(self._research_queue):
            if priority.value > existing.priority.value:
                self._research_queue.insert(i, research_topic)
                inserted = True
                break

        if not inserted:
            self._research_queue.append(research_topic)

        logger.debug(f"Queued research: '{topic}' [{priority.name}]")

        return topic_id

    def get_next_research(self) -> Optional[ResearchTopic]:
        """Get the next topic to research"""
        # Check for prerequisites
        while self._research_queue:
            topic = self._research_queue[0]

            # Check if prerequisites are met
            prereqs_met = True
            for prereq in topic.prerequisites:
                if self._knowledge_base:
                    if not self._knowledge_base.has_knowledge(prereq):
                        prereqs_met = False
                        break

            if prereqs_met:
                self._research_queue.pop(0)
                topic.status = ResearchStatus.IN_PROGRESS
                topic.started_at = datetime.now().isoformat()
                self._active_research = topic
                return topic
            else:
                # Move to end of queue
                self._research_queue.pop(0)
                self._research_queue.append(topic)

        return None

    def _determine_depth(
        self, topic: str, priority: ResearchPriority
    ) -> ResearchDepth:
        """Determine optimal research depth"""
        # Higher priority = deeper research
        if priority.value >= ResearchPriority.HIGH.value:
            return ResearchDepth.DEEP

        # Check if topic is in an area with known gaps
        for gap in self._knowledge_gaps.values():
            if gap.area.lower() in topic.lower():
                if gap.impact > 0.7:
                    return ResearchDepth.DEEP
                elif gap.impact > 0.5:
                    return ResearchDepth.STANDARD

        # Check research fatigue
        if self._research_fatigue > 0.7:
            return ResearchDepth.QUICK

        # Default
        return ResearchDepth.STANDARD

    def report_research_result(
        self,
        topic_id: str,
        success: bool,
        insights: List[str] = None,
        sources: List[str] = None,
        quality_score: float = 0.7
    ):
        """Report the result of a research session"""
        if self._active_research and self._active_research.topic_id == topic_id:
            self._active_research.status = (
                ResearchStatus.COMPLETED if success else ResearchStatus.FAILED
            )
            self._active_research.completed_at = datetime.now().isoformat()
            self._active_research.insights = insights or []
            self._active_research.sources_consulted = sources or []
            self._active_research.quality_score = quality_score

            self._completed_research.append(self._active_research)

            # Update stats
            self._stats.total_topics_researched += 1
            if success:
                self._stats.successful_researches += 1
                self._stats.total_insights += len(insights or [])
            else:
                self._stats.failed_researches += 1

            # Update effectiveness
            self._update_effectiveness(self._active_research)

            # Update research fatigue
            self._research_fatigue = min(1.0, self._research_fatigue + 0.1)

            self._active_research = None

    # ═══════════════════════════════════════════════════════════════════════════
    # KNOWLEDGE GAP DETECTION
    # ═══════════════════════════════════════════════════════════════════════════

    def _detect_knowledge_gap(
        self, user_input: str, response: str, indicator: str
    ):
        """Detect and record a knowledge gap"""
        # Extract topic from context
        gap_topic = self._extract_gap_topic(user_input, response)

        if not gap_topic:
            return

        gap_id = hashlib.sha256(gap_topic.encode()).hexdigest()[:12]

        if gap_id in self._knowledge_gaps:
            # Update existing gap
            gap = self._knowledge_gaps[gap_id]
            gap.frequency += 1
            gap.last_encountered = datetime.now().isoformat()
            gap.impact = min(1.0, gap.impact + 0.1)
        else:
            # Create new gap
            gap = KnowledgeGap(
                gap_id=gap_id,
                area=gap_topic,
                description=f"Encountered when responding to: {user_input[:100]}",
                impact=0.5,
                frequency=1,
                last_encountered=datetime.now().isoformat()
            )
            self._knowledge_gaps[gap_id] = gap

            # Queue research for this gap
            self.queue_research(
                topic=gap_topic,
                question=f"What is {gap_topic}?",
                source="gap_detection",
                priority=ResearchPriority.HIGH
            )

        logger.debug(f"Knowledge gap detected: {gap_topic}")

    def _extract_gap_topic(self, user_input: str, response: str) -> str:
        """Extract the topic of a knowledge gap"""
        # Use NLP patterns to extract topic
        patterns = [
            r"about ([\w\s]+)",
            r"familiar with ([\w\s]+)",
            r"information (?:about|on) ([\w\s]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, response.lower())
            if match:
                return match.group(1).strip()

        # Fall back to user input
        words = user_input.split()
        if len(words) > 5:
            # Extract nouns or key terms
            return " ".join(words[:3])

        return ""

    # ═══════════════════════════════════════════════════════════════════════════
    # INTELLIGENCE ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════

    def _analysis_loop(self):
        """Periodic analysis of research effectiveness"""
        logger.info("Research intelligence analysis loop started")

        time.sleep(60)

        while self._running:
            try:
                # Decay research fatigue
                self._research_fatigue = max(0.0, self._research_fatigue - 0.05)

                # Analyze research patterns
                self._analyze_research_patterns()

                # Update source reliability
                self._update_source_reliability()

                # Save data
                self._save_data()

                time.sleep(300)  # Every 5 minutes

            except Exception as e:
                logger.error(f"Research intelligence analysis error: {e}")
                time.sleep(60)

    def _analyze_research_patterns(self):
        """Analyze research patterns for optimization"""
        if len(self._completed_research) < 5:
            return

        recent = list(self._completed_research)[-20:]

        # Calculate average quality
        qualities = [r.quality_score for r in recent if r.quality_score > 0]
        if qualities:
            self._stats.avg_quality_score = sum(qualities) / len(qualities)

        # Calculate research efficiency
        if self._stats.total_topics_researched > 0:
            self._stats.research_efficiency = (
                self._stats.total_insights / max(1, self._stats.total_topics_researched)
            )

    def _update_source_reliability(self):
        """Update reliability scores for sources"""
        for research in self._completed_research:
            for source in research.sources_consulted:
                if source not in self._source_reliability:
                    self._source_reliability[source] = 0.5

                # Adjust based on quality
                self._source_reliability[source] = (
                    0.9 * self._source_reliability[source] +
                    0.1 * research.quality_score
                )

    def _update_effectiveness(self, research: ResearchTopic):
        """Track effectiveness of research on a topic"""
        topic_key = research.topic.lower()[:50]

        if topic_key not in self._topic_effectiveness:
            self._topic_effectiveness[topic_key] = []

        self._topic_effectiveness[topic_key].append(research.quality_score)

        # Keep only recent scores
        if len(self._topic_effectiveness[topic_key]) > 10:
            self._topic_effectiveness[topic_key] = (
                self._topic_effectiveness[topic_key][-10:]
            )

    # ═══════════════════════════════════════════════════════════════════════════
    # INSIGHT SYNTHESIS
    # ═══════════════════════════════════════════════════════════════════════════

    def synthesize_insights(
        self, topic: str, sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Synthesize insights from multiple sources"""
        if not sources:
            return {"synthesis": "", "confidence": 0.0}

        synthesis_result = {
            "topic": topic,
            "source_count": len(sources),
            "synthesis": "",
            "key_points": [],
            "contradictions": [],
            "confidence": 0.0,
            "sources_used": []
        }

        # Extract key points from each source
        all_points = []
        for source in sources:
            content = source.get("content", "") or source.get("summary", "")
            points = self._extract_key_points(content)
            all_points.extend(points)
            synthesis_result["sources_used"].append(source.get("url", source.get("source", "unknown")))

        # Find common points (appear in multiple sources)
        point_counts = Counter(all_points)
        common_points = [
            point for point, count in point_counts.most_common(5)
            if count >= 2
        ]
        synthesis_result["key_points"] = common_points

        # Detect contradictions
        synthesis_result["contradictions"] = self._detect_contradictions(sources)

        # Calculate confidence based on source agreement
        if common_points:
            synthesis_result["confidence"] = min(1.0, len(common_points) * 0.2)

        # Generate synthesis text
        if common_points:
            synthesis_result["synthesis"] = (
                f"Based on {len(sources)} sources, key insights about {topic}: " +
                "; ".join(common_points[:3])
            )

        return synthesis_result

    def _extract_key_points(self, content: str) -> List[str]:
        """Extract key points from content"""
        points = []

        # Split into sentences
        sentences = re.split(r'[.!?]', content)

        for sentence in sentences:
            sentence = sentence.strip()
            # Look for informative sentences
            if len(sentence) > 20 and len(sentence) < 200:
                # Check for key indicator phrases
                indicators = [
                    "is", "are", "means", "refers to", "involves",
                    "important", "key", "main", "primary", "significant"
                ]
                for ind in indicators:
                    if f" {ind} " in sentence.lower():
                        points.append(sentence[:100])
                        break

        return points[:5]

    def _detect_contradictions(self, sources: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Detect contradictions between sources"""
        contradictions = []

        # Simple contradiction detection based on opposing phrases
        opposing_pairs = [
            ("increases", "decreases"),
            ("positive", "negative"),
            ("good", "bad"),
            ("beneficial", "harmful"),
            ("causes", "prevents"),
        ]

        for i, source1 in enumerate(sources):
            for source2 in sources[i+1:]:
                content1 = source1.get("content", "").lower()
                content2 = source2.get("content", "").lower()

                for pos, neg in opposing_pairs:
                    if pos in content1 and neg in content2:
                        contradictions.append({
                            "source1": source1.get("source", "unknown"),
                            "source2": source2.get("source", "unknown"),
                            "conflict": f"'{pos}' vs '{neg}'"
                        })

        return contradictions[:3]

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def get_queue(self) -> List[Dict[str, Any]]:
        """Get current research queue"""
        return [r.to_dict() for r in self._research_queue]

    def get_active_research(self) -> Optional[Dict[str, Any]]:
        """Get currently active research"""
        if self._active_research:
            return self._active_research.to_dict()
        return None

    def get_knowledge_gaps(self) -> List[Dict[str, Any]]:
        """Get detected knowledge gaps"""
        return [asdict(gap) for gap in self._knowledge_gaps.values()]

    def get_stats(self) -> Dict[str, Any]:
        """Get research intelligence statistics"""
        return {
            "running": self._running,
            "queue_size": len(self._research_queue),
            "active_research": self._active_research.topic if self._active_research else None,
            "research_fatigue": self._research_fatigue,
            "knowledge_gaps": len(self._knowledge_gaps),
            "source_reliability": self._source_reliability,
            "stats": asdict(self._stats)
        }

    def get_recent_research(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent completed research"""
        return [r.to_dict() for r in list(self._completed_research)[-limit:]]

    def prioritize_topic(self, topic_id: str, priority: ResearchPriority):
        """Update priority of a queued topic"""
        for research in self._research_queue:
            if research.topic_id == topic_id:
                research.priority = priority
                # Re-sort queue
                self._research_queue.sort(
                    key=lambda r: r.priority.value,
                    reverse=True
                )
                return True
        return False

    def cancel_research(self, topic_id: str) -> bool:
        """Cancel a queued research topic"""
        for i, research in enumerate(self._research_queue):
            if research.topic_id == topic_id:
                self._research_queue.pop(i)
                return True
        return False

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _save_data(self):
        """Save data to disk"""
        try:
            data = {
                "knowledge_gaps": {
                    gid: asdict(gap) for gid, gap in self._knowledge_gaps.items()
                },
                "source_reliability": self._source_reliability,
                "stats": asdict(self._stats),
                "research_fatigue": self._research_fatigue,
                "saved_at": datetime.now().isoformat()
            }

            save_path = self._data_dir / "research_intelligence.json"
            save_path.write_text(
                json.dumps(data, indent=2, default=str),
                encoding="utf-8"
            )

            logger.debug("Research intelligence data saved")

        except Exception as e:
            logger.error(f"Error saving research intelligence data: {e}")

    def _load_data(self):
        """Load persisted data"""
        try:
            load_path = self._data_dir / "research_intelligence.json"
            if load_path.exists():
                data = json.loads(load_path.read_text(encoding="utf-8"))

                # Restore knowledge gaps
                for gid, gap_data in data.get("knowledge_gaps", {}).items():
                    self._knowledge_gaps[gid] = KnowledgeGap(**gap_data)

                # Restore source reliability
                self._source_reliability = data.get("source_reliability", {})

                # Restore stats
                stats_data = data.get("stats", {})
                for key, value in stats_data.items():
                    if hasattr(self._stats, key):
                        setattr(self._stats, key, value)

                self._research_fatigue = data.get("research_fatigue", 0.0)

                logger.info(f"Loaded research intelligence data: {len(self._knowledge_gaps)} gaps")

        except Exception as e:
            logger.error(f"Error loading research intelligence data: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

research_intelligence = ResearchIntelligence()

if __name__ == "__main__":
    print("🔬 Research Intelligence Test")

    ri = ResearchIntelligence()
    ri.start()

    # Queue some research
    ri.queue_research(
        topic="quantum computing",
        question="What are the basics of quantum computing?",
        source="test",
        priority=ResearchPriority.HIGH
    )

    print(f"Queue: {json.dumps(ri.get_queue(), indent=2)}")
    print(f"Stats: {json.dumps(ri.get_stats(), indent=2)}")
    print(f"Gaps: {json.dumps(ri.get_knowledge_gaps(), indent=2)}")

    ri.stop()
    print("✅ Done")