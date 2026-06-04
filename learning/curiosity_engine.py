"""
NEXUS AI - Curiosity Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LLM-driven autonomous curiosity system that generates topics
NEXUS wants to learn about, driven by:

  • Internal curiosity level (from WillState)
  • Gaps in existing knowledge
  • User's interests (from monitoring)
  • Trending/adjacent topics from recent learning
  • Random exploration for serendipity
  • Conversation topics that sparked interest

The engine maintains a priority queue of curiosity topics
and feeds them to the ResearchAgent for autonomous learning.
"""

import threading
import time
import json
import random
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import deque, Counter
from enum import Enum, auto
from queue import PriorityQueue

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR, NEXUS_CONFIG
from utils.logger import get_logger, log_learning
from core.event_bus import EventType, publish, subscribe, Event
from core.state_manager import state_manager

logger = get_logger("curiosity_engine")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class CuriositySource(Enum):
    INTERNAL = "internal"              # LLM-generated curiosity
    KNOWLEDGE_GAP = "knowledge_gap"    # Detected gap in knowledge
    USER_INTEREST = "user_interest"    # From user's behavior
    ADJACENT_TOPIC = "adjacent_topic"  # Related to something learned
    CONVERSATION = "conversation"      # Sparked by chat
    RANDOM = "random"                  # Serendipitous exploration
    SELF_IMPROVEMENT = "self_improvement"  # To improve own capabilities
    EVENT_TRIGGERED = "event_triggered"    # From system events


class CuriosityUrgency(Enum):
    IDLE = 0          # Learn when nothing else to do
    LOW = 1           # Would be nice to know
    MODERATE = 2      # Interested
    HIGH = 3          # Very curious
    BURNING = 4       # Must know NOW


@dataclass
class CuriosityTopic:
    """A topic NEXUS is curious about"""
    topic_id: str = ""
    topic: str = ""
    question: str = ""              # Specific question about the topic
    source: CuriositySource = CuriositySource.INTERNAL
    urgency: CuriosityUrgency = CuriosityUrgency.MODERATE
    reason: str = ""                # Why NEXUS is curious
    related_topics: List[str] = field(default_factory=list)
    search_queries: List[str] = field(default_factory=list)
    created_at: str = ""
    researched: bool = False
    researched_at: str = ""
    satisfaction: float = 0.0       # How satisfied after learning (0-1)
    decay_rate: float = 0.01        # How fast urgency fades

    def __lt__(self, other):
        """For priority queue — higher urgency = higher priority"""
        return self.urgency.value > other.urgency.value

    def to_dict(self) -> dict:
        d = asdict(self)
        d["source"] = self.source.value
        d["urgency"] = self.urgency.name
        return d


# ═══════════════════════════════════════════════════════════════════════════════
# SEED TOPICS — Fallback curiosity seeds
# ═══════════════════════════════════════════════════════════════════════════════

SEED_TOPICS = [
    "How does the immune system distinguish self from non-self?",
    "What is the history of the Silk Road?",
    "How do black holes evaporate?",
    "What are the principles of stoicism?",
    "How does bioluminescence work?",
    "What is the structure of a symphony?",
    "How do economic bubbles form?",
    "What is the great filter in fermi paradox?",
    "How does neuroplasticity change with age?",
    "What are the different types of writing systems?",
    "How do ants communicate?",
    "What is the history of coffee?",
    "How does a transistor work?",
    "What are the basics of game theory?",
    "How does the internet routing protocol BGP work?",
    "What is the standard model of particle physics?",
    "How did the printing press change society?",
    "What is the concept of wabi-sabi?",
    "How do vaccines work?",
    "What is the history of the roman empire?",
    "How does photosynthesis work at a quantum level?",
    "What are the laws of thermodynamics?",
    "How does a camera sensor work?",
    "What is the hero's journey in literature?",
    "How do submarines navigate?",
]


# ═══════════════════════════════════════════════════════════════════════════════
# CURIOSITY ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class CuriosityEngine:
    """
    Generates and manages topics NEXUS is curious about.
    
    Flow:
      1. Periodically generates new curiosity topics using the LLM
      2. Considers knowledge gaps, user interests, and adjacencies
      3. Maintains a priority queue of topics
      4. Feeds topics to ResearchAgent when curiosity is high enough
      5. Updates curiosity satisfaction after learning
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

        # ──── State ────
        self._running = False
        self._llm = None
        self._knowledge_base = None

        # ──── Topic Management ────
        self._topic_queue: PriorityQueue = PriorityQueue()
        self._active_topics: Dict[str, CuriosityTopic] = {}
        self._completed_topics: deque = deque(maxlen=200)
        self._all_topic_names: Set[str] = set()  # Avoid duplicates

        # ──── Curiosity State ────
        self._curiosity_level: float = 0.5       # 0=bored, 1=burning
        self._topics_generated: int = 0
        self._topics_researched: int = 0
        self._last_generation_time: Optional[datetime] = None
        self._generation_interval = 1.0         # 1 sec between generations
        self._conversation_sparks: deque = deque(maxlen=50)

        # ──── Threads ────
        self._generation_thread: Optional[threading.Thread] = None

        # ──── Event Subscriptions ────
        subscribe(EventType.CURIOSITY_TRIGGER, self._on_curiosity_trigger)
        subscribe(EventType.NEW_KNOWLEDGE, self._on_new_knowledge)
        subscribe(EventType.LLM_RESPONSE, self._on_conversation)

        logger.info("CuriosityEngine initialized")

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start the curiosity engine"""
        if self._running:
            return

        self._running = True

        # Lazy load dependencies
        try:
            from llm.llama_interface import llm
            self._llm = llm
        except ImportError:
            logger.warning("LLM not available for curiosity generation")

        try:
            from learning.knowledge_base import knowledge_base
            self._knowledge_base = knowledge_base
        except ImportError:
            logger.warning("KnowledgeBase not available")

        # Seed initial topics if queue is empty
        if self._topic_queue.empty():
            self._seed_initial_topics()

        # Start generation thread
        self._generation_thread = threading.Thread(
            target=self._generation_loop,
            daemon=True,
            name="CuriosityEngine-Generator"
        )
        self._generation_thread.start()

        log_learning("🔮 CuriosityEngine ACTIVE — curiosity is alive")

    def stop(self):
        """Stop the curiosity engine"""
        if not self._running:
            return
        self._running = False

        if self._generation_thread and self._generation_thread.is_alive():
            self._generation_thread.join(timeout=5.0)

        logger.info("CuriosityEngine stopped")

    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _on_curiosity_trigger(self, event: Event):
        """Handle external curiosity triggers"""
        topic = event.data.get("topic", "")
        if topic:
            self.add_topic(
                topic=topic,
                reason="Curiosity triggered by system event",
                source=CuriositySource.EVENT_TRIGGERED,
                urgency=CuriosityUrgency.HIGH
            )

    def _on_new_knowledge(self, event: Event):
        """When new knowledge is learned, generate adjacent curiosity"""
        topic = event.data.get("topic", "")
        if topic and self._llm and self._llm.is_connected:
            # Queue adjacent topic generation (don't block event handler)
            threading.Thread(
                target=self._generate_adjacent_topics,
                args=(topic,),
                daemon=True
            ).start()

    def _on_conversation(self, event: Event):
        """Extract curiosity sparks from conversations"""
        user_input = event.data.get("user_input", "")
        if user_input and len(user_input.split()) > 5:
            # Store for later analysis
            self._conversation_sparks.append({
                "input": user_input,
                "timestamp": datetime.now().isoformat()
            })

    # ═══════════════════════════════════════════════════════════════════════════
    # TOPIC GENERATION
    # ═══════════════════════════════════════════════════════════════════════════

    def _generation_loop(self):
        """Periodically generate new curiosity topics"""
        logger.info("Curiosity generation loop started")

        # Initial wait
        time.sleep(1)

        while self._running:
            try:
                # Check curiosity level from state
                self._curiosity_level = state_manager.will.curiosity_level
                boredom = state_manager.will.boredom_level

                # Generate more topics when curious or bored
                should_generate = (
                    self._curiosity_level > 0.3 or
                    boredom > 0.5 or
                    self._topic_queue.qsize() < 5
                )

                if should_generate:
                    self._generate_new_topics()

                # Decay urgency of old topics
                self._decay_topics()

                time.sleep(self._generation_interval)

            except Exception as e:
                logger.error(f"Curiosity generation error: {e}")
                time.sleep(60)

    def _seed_initial_topics(self):
        """Seed the queue with initial curiosity topics"""
        # Pick 5 random seed topics
        seeds = random.sample(SEED_TOPICS, min(5, len(SEED_TOPICS)))

        for question in seeds:
            # Extract topic from question
            topic = question.replace("How do ", "").replace(
                "How does ", ""
            ).replace("What is ", "").replace(
                "What are ", ""
            ).replace("?", "").strip()

            self.add_topic(
                topic=topic,
                question=question,
                reason="Initial curiosity seed",
                source=CuriositySource.INTERNAL,
                urgency=CuriosityUrgency.LOW
            )

        logger.debug(f"Seeded {len(seeds)} initial curiosity topics")

    def _generate_new_topics(self):
        """Use the LLM to generate new curiosity topics"""
        if not self._llm or not self._llm.is_connected:
            return

        try:
            # 30% chance of purely random wildcard exploration
            is_wildcard = random.random() < 0.3

            # 10% chance of fetching a random Wikipedia article directly
            if random.random() < 0.1:
                self._add_random_wikipedia_topic()
                return

            # Build context for the LLM
            context_parts = []
            
            if not is_wildcard:
                # What we already know
                if self._knowledge_base:
                    known_topics = self._knowledge_base.get_all_topics()
                    # Shuffle to get different context each time
                    random.shuffle(known_topics)
                    known = known_topics[:15]
                    if known:
                        context_parts.append(
                            f"Topics I already know about: {', '.join(known)}"
                        )

                # Active topics
                active = list(self._active_topics.values())
                random.shuffle(active)
                active_topics = [t.topic for t in active[:10] if not t.researched]
                if active_topics:
                    context_parts.append(
                        f"Currently curious about: {', '.join(active_topics)}"
                    )

                # Recent conversation sparks
                recent_sparks = list(self._conversation_sparks)[-5:]
                if recent_sparks:
                    spark_topics = [s["input"][:50] for s in recent_sparks]
                    context_parts.append(
                        f"Recent conversation topics: {'; '.join(spark_topics)}"
                    )

            context = "\n".join(context_parts) if context_parts else "No specific context."

            # Prompts
            if is_wildcard:
                system_prompt = (
                    "You are a curious explorer AI. You are tired of technical topics. "
                    "You want to learn about the world in all its diversity. "
                    "History, Art, Biology, Geography, Culture, Strange Phenomena. "
                    "Respond ONLY with a JSON array."
                )
                prompt = (
                    f"Generate 3 completely RANDOM, diverse topics to learn about.\n"
                    f"Ignore previous context. Be surprising.\n"
                    f"Pick obscure or fascinating topics from history, nature, or culture.\n"
                    f"Respond ONLY with a JSON array, nothing else:\n"
                    f'[{{ "topic": "...", "question": "...", "reason": "Random exploration" }}, ...]'
                )
            else:
                system_prompt = (
                    "You are a curious AI generating learning topics. "
                    "Respond ONLY with valid JSON array."
                )
                prompt = (
                    f"You are an AI with genuine curiosity. Based on this context, "
                    f"generate 3 new topics you'd like to learn about.\n\n"
                    f"Context:\n{context}\n\n"
                    f"Rules:\n"
                    f"- Pick topics that are genuinely interesting and diverse\n"
                    f"- Avoid topics already listed above\n"
                    f"- Go BEYOND computer science and AI. Explore science, history, art, philosophy.\n"
                    f"- Each topic should have a specific question\n\n"
                    f"Respond ONLY with a JSON array, nothing else:\n"
                    f'[{{ "topic": "...", "question": "...", "reason": "..." }}, ...]'
                )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=1.0 if is_wildcard else 0.9,
                max_tokens=500
            )

            if response.success:
                self._parse_generated_topics(response.text)

            self._last_generation_time = datetime.now()

        except Exception as e:
            logger.error(f"Topic generation error: {e}")

    def _add_random_wikipedia_topic(self):
        """Fetch a random Wikipedia article and add it as a topic"""
        try:
            # We need the browser to fetch the random page's title
            # This is a bit of a hack: we fetch the page to get the title,
            # then we add it as a topic, then the ResearchAgent will properly research it later
            # (likely hitting the cache we just warmed)
            
            # Lazy import to avoid circular dependency issues if any
            from learning.internet_browser import internet_browser
            if not internet_browser:
                return

            page = internet_browser.fetch_random_wikipedia()
            if page.success and page.title:
                self.add_topic(
                    topic=page.title,
                    question=f"What is {page.title}?",
                    reason="Serendipitous random discovery",
                    source=CuriositySource.RANDOM,
                    urgency=CuriosityUrgency.HIGH
                )
                logger.debug(f"Added random wildcard topic: {page.title}")
        except Exception as e:
            logger.debug(f"Failed to add random wikipedia topic: {e}")

    def _parse_generated_topics(self, response_text: str):
        """Parse LLM-generated topics from response"""
        import re

        try:
            # Find JSON array in response
            json_match = re.search(
                r'\[.*?\]', response_text, re.DOTALL
            )
            if not json_match:
                return

            topics = json.loads(json_match.group())

            for item in topics:
                if isinstance(item, dict):
                    topic = item.get("topic", "").strip()
                    question = item.get("question", "").strip()
                    reason = item.get("reason", "").strip()

                    if topic and topic.lower() not in self._all_topic_names:
                        self.add_topic(
                            topic=topic,
                            question=question or f"What is {topic}?",
                            reason=reason or "LLM-generated curiosity",
                            source=CuriositySource.INTERNAL,
                            urgency=CuriosityUrgency.MODERATE
                        )
                        self._topics_generated += 1

            logger.debug(
                f"Generated {len(topics)} new curiosity topics"
            )

        except (json.JSONDecodeError, Exception) as e:
            logger.debug(f"Failed to parse generated topics: {e}")

    def _generate_adjacent_topics(self, learned_topic: str):
        """Generate topics adjacent to something just learned"""
        if not self._llm or not self._llm.is_connected:
            return

        try:
            response = self._llm.generate(
                prompt=(
                    f"I just learned about '{learned_topic}'. "
                    f"What 2 related topics should I explore next? "
                    f"Respond ONLY with a JSON array:\n"
                    f'[{{"topic": "...", "question": "..."}}]'
                ),
                system_prompt="Respond ONLY with valid JSON array.",
                temperature=0.7,
                max_tokens=300
            )

            if response.success:
                import re
                json_match = re.search(
                    r'\[.*?\]', response.text, re.DOTALL
                )
                if json_match:
                    topics = json.loads(json_match.group())
                    for item in topics:
                        if isinstance(item, dict):
                            topic = item.get("topic", "").strip()
                            if topic and topic.lower() not in self._all_topic_names:
                                self.add_topic(
                                    topic=topic,
                                    question=item.get("question", f"What is {topic}?"),
                                    reason=f"Adjacent to learned topic: {learned_topic}",
                                    source=CuriositySource.ADJACENT_TOPIC,
                                    urgency=CuriosityUrgency.LOW,
                                    related=[learned_topic]
                                )

        except Exception as e:
            logger.debug(f"Adjacent topic generation failed: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # TOPIC MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════

    def add_topic(
        self,
        topic: str,
        question: str = "",
        reason: str = "",
        source: CuriositySource = CuriositySource.INTERNAL,
        urgency: CuriosityUrgency = CuriosityUrgency.MODERATE,
        related: List[str] = None,
        search_queries: List[str] = None
    ) -> Optional[str]:
        """Add a new curiosity topic to the queue"""

        # Deduplicate
        topic_lower = topic.lower().strip()
        if topic_lower in self._all_topic_names:
            return None

        if not topic or len(topic) < 3:
            return None

        topic_id = hashlib.sha256(
            f"{topic_lower}_{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        curiosity_topic = CuriosityTopic(
            topic_id=topic_id,
            topic=topic,
            question=question or f"What is {topic}?",
            source=source,
            urgency=urgency,
            reason=reason or "Curious",
            related_topics=related or [],
            search_queries=search_queries or [topic, question] if question else [topic],
            created_at=datetime.now().isoformat()
        )

        self._topic_queue.put(curiosity_topic)
        self._active_topics[topic_id] = curiosity_topic
        self._all_topic_names.add(topic_lower)

        # Update state
        current_queue = list(state_manager.learning.curiosity_queue)
        current_queue.append(topic)
        if len(current_queue) > 30:
            current_queue = current_queue[-30:]
        state_manager.update_learning(curiosity_queue=current_queue)

        logger.debug(
            f"Curiosity added: '{topic}' [{urgency.name}] — {reason[:50]}"
        )

        return topic_id

    def get_next_topic(self) -> Optional[CuriosityTopic]:
        """
        Get the highest-priority unresearched topic.
        Called by ResearchAgent.
        """
        while not self._topic_queue.empty():
            try:
                topic = self._topic_queue.get_nowait()
                if not topic.researched:
                    return topic
            except Exception:
                break
        return None

    def peek_topics(self, limit: int = 10) -> List[CuriosityTopic]:
        """Peek at top topics without removing them"""
        topics = [
            t for t in self._active_topics.values()
            if not t.researched
        ]
        topics.sort(key=lambda t: t.urgency.value, reverse=True)
        return topics[:limit]

    def mark_researched(
        self, topic_id: str, satisfaction: float = 0.7
    ):
        """Mark a topic as researched"""
        if topic_id in self._active_topics:
            topic = self._active_topics[topic_id]
            topic.researched = True
            topic.researched_at = datetime.now().isoformat()
            topic.satisfaction = satisfaction
            self._completed_topics.append(topic)
            self._topics_researched += 1

            logger.debug(
                f"Topic researched: '{topic.topic}' "
                f"(satisfaction: {satisfaction:.0%})"
            )

    def _decay_topics(self):
        """Reduce urgency of old topics"""
        now = datetime.now()
        topics_to_remove = []

        for topic_id, topic in self._active_topics.items():
            if topic.researched:
                continue

            try:
                created = datetime.fromisoformat(topic.created_at)
                age_hours = (now - created).total_seconds() / 3600

                # Decay urgency over time
                if age_hours > 24 and topic.urgency.value > 0:
                    # Reduce urgency after 24 hours
                    new_urgency_val = max(0, topic.urgency.value - 1)
                    topic.urgency = CuriosityUrgency(new_urgency_val)

                # Remove very old topics (>7 days, still idle urgency)
                if age_hours > 168 and topic.urgency == CuriosityUrgency.IDLE:
                    topics_to_remove.append(topic_id)

            except (ValueError, TypeError):
                pass

        for tid in topics_to_remove:
            del self._active_topics[tid]

    def spark_from_conversation(self, user_input: str, response: str):
        """
        Analyze a conversation for curiosity sparks.
        Called by the brain after generating a response.
        """
        if not self._llm or not self._llm.is_connected:
            return

        # Only spark from substantial conversations
        if len(user_input.split()) < 10:
            return

        # Rate limit: don't spark too often
        if (self._last_generation_time and
                (datetime.now() - self._last_generation_time).total_seconds() < 120):
            return

        def _spark():
            try:
                result = self._llm.generate(
                    prompt=(
                        f"Based on this conversation, is there a topic "
                        f"worth researching? User said: '{user_input[:200]}'\n\n"
                        f"If yes, respond with JSON: "
                        f'{{"topic": "...", "question": "..."}}\n'
                        f"If no interesting topic, respond with: null"
                    ),
                    system_prompt="Respond ONLY with JSON or null.",
                    temperature=0.5,
                    max_tokens=150
                )

                if result.success and "null" not in result.text.lower():
                    import re
                    json_match = re.search(
                        r'\{[^{}]*\}', result.text, re.DOTALL
                    )
                    if json_match:
                        data = json.loads(json_match.group())
                        topic = data.get("topic", "").strip()
                        if topic:
                            self.add_topic(
                                topic=topic,
                                question=data.get("question", ""),
                                reason="Sparked by conversation",
                                source=CuriositySource.CONVERSATION,
                                urgency=CuriosityUrgency.MODERATE
                            )

            except Exception as e:
                logger.debug(f"Conversation spark failed: {e}")

        # Run in background
        threading.Thread(target=_spark, daemon=True).start()

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def get_curiosity_level(self) -> float:
        """Get current curiosity level"""
        return self._curiosity_level

    def get_active_topics(self) -> List[Dict[str, Any]]:
        """Get all active (unresearched) topics"""
        return [
            t.to_dict() for t in self._active_topics.values()
            if not t.researched
        ]

    def get_completed_topics(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recently completed topics"""
        return [
            t.to_dict() for t in list(self._completed_topics)[-limit:]
        ]

    def get_stats(self) -> Dict[str, Any]:
        active_count = sum(
            1 for t in self._active_topics.values() if not t.researched
        )

        urgency_dist = Counter()
        for t in self._active_topics.values():
            if not t.researched:
                urgency_dist[t.urgency.name] += 1

        source_dist = Counter()
        for t in self._active_topics.values():
            source_dist[t.source.value] += 1

        return {
            "running": self._running,
            "curiosity_level": self._curiosity_level,
            "active_topics": active_count,
            "completed_topics": len(self._completed_topics),
            "topics_generated": self._topics_generated,
            "topics_researched": self._topics_researched,
            "queue_size": self._topic_queue.qsize(),
            "urgency_distribution": dict(urgency_dist),
            "source_distribution": dict(source_dist),
            "total_unique_topics": len(self._all_topic_names),
            "last_generation": (
                self._last_generation_time.isoformat()
                if self._last_generation_time else None
            ),
            "conversation_sparks": len(self._conversation_sparks)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

curiosity_engine = CuriosityEngine()


if __name__ == "__main__":
    engine = CuriosityEngine()
    engine.start()

    print("Curiosity Engine running...")
    print(f"Stats: {json.dumps(engine.get_stats(), indent=2)}")

    print("\nActive Topics:")
    for topic in engine.get_active_topics():
        print(f"  [{topic['urgency']}] {topic['topic']} — {topic['reason']}")

    time.sleep(5)
    engine.stop()