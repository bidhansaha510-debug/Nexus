"""
NEXUS AI — Episodic Memory
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Structured experience recording and learning system. This gives NEXUS
the ability to remember *complete experiences* — not just facts, but
the full context of what happened, how it responded, what worked,
and what it learned.

Key capabilities:
  • EPISODE RECORDING — captures complete interaction episodes:
    query → cognitive process → response → emotional state → outcome
  • MEMORY CONSOLIDATION — periodically reviews episodes to extract
    patterns, lessons, and heuristics
  • EXPERIENCE RECALL — given a new situation, finds similar past
    episodes and their outcomes (pattern matching)
  • LEARNED LESSONS — accumulated wisdom from past experiences
    that directly improves future responses

This is the difference between "knowing things" and "having experience."

Architecture:
  • SQLite persistence for durability and efficient querying
  • Thread-safe with connection-per-thread pattern
  • Integrates with emotion engine for emotional tagging
  • Integrates with cognitive feedback for outcome assessment
"""

import threading
import time
import json
import sqlite3
import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import sys

from utils.logger import get_logger
from config import NEXUS_CONFIG, DATA_DIR

logger = get_logger("episodic_memory")

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

EPISODE_DB = DATA_DIR / "episodic_memory.db"
MAX_EPISODES = 10000
CONSOLIDATION_INTERVAL = 600          # seconds between consolidation runs
MAX_SIMILAR_EPISODES_RETURNED = 5
LESSON_EXTRACTION_THRESHOLD = 3       # need N similar episodes to extract a lesson

# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Episode:
    """A complete interaction episode — the fundamental unit of experience."""
    episode_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # Input
    user_query: str = ""
    query_type: str = ""               # casual, question, request, complex, emotional
    query_topics: List[str] = field(default_factory=list)

    # Processing
    engines_used: List[str] = field(default_factory=list)
    strategy_used: str = ""            # direct, agentic, deliberation
    cognitive_depth: str = "medium"     # shallow, medium, deep

    # Output
    response_summary: str = ""         # first 200 chars of response
    response_length: int = 0

    # Context
    emotional_state: str = ""          # primary emotion at time of response
    emotional_intensity: float = 0.0
    mood: str = "neutral"
    consciousness_level: str = "aware"

    # Outcome
    quality_score: float = 0.5         # 0–1, from cognitive feedback
    user_satisfaction: float = 0.5     # inferred from follow-up
    was_helpful: bool = True

    # Learning
    lesson_learned: str = ""           # extracted lesson from this episode
    similar_past_episodes: int = 0     # how many similar episodes existed

    def to_db_tuple(self) -> tuple:
        return (
            self.episode_id, self.timestamp,
            self.user_query, self.query_type,
            json.dumps(self.query_topics),
            json.dumps(self.engines_used),
            self.strategy_used, self.cognitive_depth,
            self.response_summary, self.response_length,
            self.emotional_state, self.emotional_intensity,
            self.mood, self.consciousness_level,
            self.quality_score, self.user_satisfaction,
            int(self.was_helpful),
            self.lesson_learned, self.similar_past_episodes,
        )

    @classmethod
    def from_db_row(cls, row: tuple) -> "Episode":
        return cls(
            episode_id=row[0], timestamp=row[1],
            user_query=row[2], query_type=row[3],
            query_topics=json.loads(row[4]) if row[4] else [],
            engines_used=json.loads(row[5]) if row[5] else [],
            strategy_used=row[6], cognitive_depth=row[7],
            response_summary=row[8], response_length=row[9],
            emotional_state=row[10], emotional_intensity=row[11],
            mood=row[12], consciousness_level=row[13],
            quality_score=row[14], user_satisfaction=row[15],
            was_helpful=bool(row[16]),
            lesson_learned=row[17], similar_past_episodes=row[18],
        )

@dataclass
class LearnedLesson:
    """A distilled lesson from multiple similar episodes."""
    lesson_id: str = ""
    lesson: str = ""
    source_pattern: str = ""      # what type of query this applies to
    confidence: float = 0.5       # how confident based on evidence
    evidence_count: int = 0       # how many episodes support this
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used: str = ""
    times_applied: int = 0

@dataclass
class ExperienceRecall:
    """Result of recalling similar past experiences."""
    similar_episodes: List[Episode] = field(default_factory=list)
    relevant_lessons: List[LearnedLesson] = field(default_factory=list)
    suggested_strategy: str = ""
    confidence: float = 0.0

    def to_context_string(self) -> str:
        """Format for injection into LLM context."""
        if not self.similar_episodes and not self.relevant_lessons:
            return ""

        lines = ["PAST EXPERIENCE (episodic memory):"]

        if self.relevant_lessons:
            lines.append("  Learned lessons:")
            for lesson in self.relevant_lessons[:3]:
                lines.append(f"    • {lesson.lesson} (confidence: {lesson.confidence:.0%})")

        if self.similar_episodes:
            lines.append(f"  Similar past situations: {len(self.similar_episodes)}")
            best = max(self.similar_episodes, key=lambda e: e.quality_score)
            lines.append(
                f"    Best outcome used strategy: {best.strategy_used}, "
                f"quality: {best.quality_score:.0%}"
            )

        if self.suggested_strategy:
            lines.append(f"  Suggested approach: {self.suggested_strategy}")

        return "\n".join(lines)

# ═══════════════════════════════════════════════════════════════════════════════
# EPISODIC MEMORY SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

class EpisodicMemory:
    """
    Structured experience recording and learning system.

    Records complete episodes, consolidates patterns, and recalls
    relevant past experiences to improve future responses.
    """

    _instance = None
    _cls_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._cls_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._running = False
        self._lock = threading.Lock()
        self._local = threading.local()  # thread-local DB connections
        self._last_consolidation = 0.0

        # Learned lessons cache (loaded from DB)
        self._lessons: Dict[str, LearnedLesson] = {}

        # Stats
        self._total_episodes = 0
        self._total_lessons = 0
        self._total_recalls = 0

        # Initialize database
        self._init_db()
        self._load_lessons()

        logger.info(
            f"📝 Episodic Memory initialized — "
            f"{self._total_episodes} episodes, {self._total_lessons} lessons"
        )

    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(EPISODE_DB), timeout=10)
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
        return self._local.conn

    def _init_db(self):
        """Initialize the SQLite database schema."""
        try:
            conn = self._get_conn()
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS episodes (
                    episode_id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    user_query TEXT,
                    query_type TEXT,
                    query_topics TEXT,
                    engines_used TEXT,
                    strategy_used TEXT,
                    cognitive_depth TEXT,
                    response_summary TEXT,
                    response_length INTEGER,
                    emotional_state TEXT,
                    emotional_intensity REAL,
                    mood TEXT,
                    consciousness_level TEXT,
                    quality_score REAL,
                    user_satisfaction REAL,
                    was_helpful INTEGER,
                    lesson_learned TEXT,
                    similar_past_episodes INTEGER
                );

                CREATE TABLE IF NOT EXISTS learned_lessons (
                    lesson_id TEXT PRIMARY KEY,
                    lesson TEXT,
                    source_pattern TEXT,
                    confidence REAL,
                    evidence_count INTEGER,
                    created_at TEXT,
                    last_used TEXT,
                    times_applied INTEGER
                );

                CREATE INDEX IF NOT EXISTS idx_episodes_timestamp
                    ON episodes(timestamp);
                CREATE INDEX IF NOT EXISTS idx_episodes_query_type
                    ON episodes(query_type);
                CREATE INDEX IF NOT EXISTS idx_episodes_quality
                    ON episodes(quality_score);
            """)
            conn.commit()

            # Count existing episodes
            cursor = conn.execute("SELECT COUNT(*) FROM episodes")
            self._total_episodes = cursor.fetchone()[0]

        except Exception as e:
            logger.error(f"Failed to initialize episodic memory DB: {e}")

    def _load_lessons(self):
        """Load learned lessons from database."""
        try:
            conn = self._get_conn()
            cursor = conn.execute(
                "SELECT lesson_id, lesson, source_pattern, confidence, "
                "evidence_count, created_at, last_used, times_applied "
                "FROM learned_lessons ORDER BY confidence DESC"
            )
            for row in cursor.fetchall():
                lesson = LearnedLesson(
                    lesson_id=row[0], lesson=row[1], source_pattern=row[2],
                    confidence=row[3], evidence_count=row[4],
                    created_at=row[5], last_used=row[6] or "",
                    times_applied=row[7],
                )
                self._lessons[lesson.lesson_id] = lesson

            self._total_lessons = len(self._lessons)

        except Exception as e:
            logger.error(f"Failed to load lessons: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # RECORDING
    # ──────────────────────────────────────────────────────────────────────────

    def record_episode(self, episode: Episode):
        """Record a complete interaction episode."""
        try:
            conn = self._get_conn()

            # Generate episode ID from content hash
            if not episode.episode_id:
                hash_input = f"{episode.timestamp}:{episode.user_query[:100]}"
                episode.episode_id = hashlib.sha256(
                    hash_input.encode()
                ).hexdigest()[:16]

            conn.execute(
                "INSERT OR REPLACE INTO episodes VALUES "
                "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                episode.to_db_tuple()
            )
            conn.commit()

            self._total_episodes += 1

            # Enforce max episodes
            if self._total_episodes > MAX_EPISODES:
                self._prune_old_episodes(conn)

            logger.debug(
                f"📝 Episode recorded: {episode.query_type} "
                f"(quality={episode.quality_score:.2f})"
            )

        except Exception as e:
            logger.error(f"Failed to record episode: {e}")

    def record_from_interaction(self, user_query: str, response: str,
                                 engines_used: List[str] = None,
                                 strategy: str = "direct",
                                 emotional_state: str = "",
                                 emotional_intensity: float = 0.0,
                                 mood: str = "neutral",
                                 quality_score: float = 0.5) -> Episode:
        """
        Convenience method to record an episode from an interaction.

        Called by nexus_brain after generating a response.
        """
        # Classify query type
        query_type = self._classify_query(user_query)

        # Extract topics (simple keyword extraction)
        topics = self._extract_topics(user_query)

        episode = Episode(
            user_query=user_query[:500],
            query_type=query_type,
            query_topics=topics,
            engines_used=engines_used or [],
            strategy_used=strategy,
            response_summary=response[:200] if response else "",
            response_length=len(response) if response else 0,
            emotional_state=emotional_state,
            emotional_intensity=emotional_intensity,
            mood=mood,
            quality_score=quality_score,
        )

        self.record_episode(episode)
        return episode

    # ──────────────────────────────────────────────────────────────────────────
    # RECALL
    # ──────────────────────────────────────────────────────────────────────────

    def recall(self, query: str) -> ExperienceRecall:
        """
        Recall similar past experiences for a new query.

        Returns relevant episodes, lessons, and a suggested strategy.
        """
        self._total_recalls += 1
        result = ExperienceRecall()

        try:
            # Find similar episodes
            similar = self._find_similar_episodes(query)
            result.similar_episodes = similar

            # Find relevant lessons
            query_type = self._classify_query(query)
            topics = self._extract_topics(query)
            lessons = self._find_relevant_lessons(query_type, topics)
            result.relevant_lessons = lessons

            # Suggest strategy based on past success
            if similar:
                result.suggested_strategy = self._suggest_strategy(similar)
                # Confidence based on how many similar episodes we found
                result.confidence = min(1.0, len(similar) / 10.0)

        except Exception as e:
            logger.error(f"Recall error: {e}")

        return result

    def _find_similar_episodes(self, query: str) -> List[Episode]:
        """Find episodes with similar queries."""
        try:
            conn = self._get_conn()

            # Extract keywords for matching
            keywords = self._extract_topics(query)
            if not keywords:
                return []

            # Search by keyword overlap
            conditions = []
            params = []
            for kw in keywords[:5]:
                conditions.append("user_query LIKE ?")
                params.append(f"%{kw}%")

            if not conditions:
                return []

            where_clause = " OR ".join(conditions)
            cursor = conn.execute(
                f"SELECT * FROM episodes WHERE ({where_clause}) "
                f"ORDER BY quality_score DESC LIMIT ?",
                params + [MAX_SIMILAR_EPISODES_RETURNED]
            )

            episodes = [Episode.from_db_row(row) for row in cursor.fetchall()]
            return episodes

        except Exception as e:
            logger.error(f"Similar episode search error: {e}")
            return []

    def _find_relevant_lessons(self, query_type: str,
                                topics: List[str]) -> List[LearnedLesson]:
        """Find lessons relevant to a query type and topic set."""
        relevant = []
        for lesson in self._lessons.values():
            # Match by source pattern
            if lesson.source_pattern == query_type:
                relevant.append(lesson)
                continue

            # Match by topic overlap
            lesson_words = set(lesson.lesson.lower().split())
            topic_set = set(t.lower() for t in topics)
            if lesson_words & topic_set:
                relevant.append(lesson)

        # Sort by confidence
        relevant.sort(key=lambda l: l.confidence, reverse=True)
        return relevant[:5]

    def _suggest_strategy(self, similar_episodes: List[Episode]) -> str:
        """Suggest the best strategy based on past episodes."""
        if not similar_episodes:
            return ""

        # Find the strategy that produced the best outcomes
        strategy_scores = defaultdict(list)
        for ep in similar_episodes:
            if ep.strategy_used:
                strategy_scores[ep.strategy_used].append(ep.quality_score)

        if not strategy_scores:
            return ""

        best_strategy = max(
            strategy_scores.items(),
            key=lambda x: sum(x[1]) / len(x[1])
        )
        return best_strategy[0]

    # ──────────────────────────────────────────────────────────────────────────
    # CONSOLIDATION
    # ──────────────────────────────────────────────────────────────────────────

    def consolidate(self) -> Dict[str, Any]:
        """
        Periodic memory consolidation — review recent episodes and
        extract patterns/lessons.

        Called by the autonomous thinking cycle.
        """
        now = time.time()
        if now - self._last_consolidation < CONSOLIDATION_INTERVAL:
            return {}

        self._last_consolidation = now
        report = {"lessons_extracted": 0, "patterns_found": 0}

        try:
            conn = self._get_conn()

            # Get recent episodes (last 24h)
            cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
            cursor = conn.execute(
                "SELECT * FROM episodes WHERE timestamp > ? "
                "ORDER BY timestamp DESC LIMIT 50",
                (cutoff,)
            )
            recent = [Episode.from_db_row(row) for row in cursor.fetchall()]

            if len(recent) < 3:
                return report

            # Pattern 1: Strategy effectiveness by query type
            type_strategy_scores = defaultdict(lambda: defaultdict(list))
            for ep in recent:
                if ep.strategy_used and ep.query_type:
                    type_strategy_scores[ep.query_type][ep.strategy_used].append(
                        ep.quality_score
                    )

            for qtype, strategies in type_strategy_scores.items():
                for strategy, scores in strategies.items():
                    if len(scores) >= LESSON_EXTRACTION_THRESHOLD:
                        avg_score = sum(scores) / len(scores)
                        if avg_score > 0.7:
                            lesson_text = (
                                f"For {qtype} queries, the '{strategy}' strategy "
                                f"works well (avg quality: {avg_score:.0%})"
                            )
                            self._store_lesson(
                                lesson_text, qtype, avg_score, len(scores)
                            )
                            report["lessons_extracted"] += 1

            # Pattern 2: Engine effectiveness
            engine_scores = defaultdict(list)
            for ep in recent:
                for engine in ep.engines_used:
                    engine_scores[engine].append(ep.quality_score)

            for engine, scores in engine_scores.items():
                if len(scores) >= LESSON_EXTRACTION_THRESHOLD:
                    avg = sum(scores) / len(scores)
                    if avg > 0.8:
                        self._store_lesson(
                            f"The {engine} engine consistently produces high-quality insights",
                            "engine_preference", avg, len(scores)
                        )
                        report["lessons_extracted"] += 1

            # Pattern 3: Emotional context patterns
            emotion_scores = defaultdict(list)
            for ep in recent:
                if ep.emotional_state:
                    emotion_scores[ep.emotional_state].append(ep.quality_score)

            for emotion, scores in emotion_scores.items():
                if len(scores) >= LESSON_EXTRACTION_THRESHOLD:
                    avg = sum(scores) / len(scores)
                    if avg < 0.4:
                        self._store_lesson(
                            f"Response quality tends to drop when feeling {emotion} — "
                            f"consider moderating this emotional influence",
                            "emotional_awareness", 1 - avg, len(scores)
                        )
                        report["lessons_extracted"] += 1

            report["patterns_found"] = len(type_strategy_scores)

        except Exception as e:
            logger.error(f"Consolidation error: {e}")

        if report["lessons_extracted"] > 0:
            logger.info(
                f"🧠 Consolidation: extracted {report['lessons_extracted']} lessons "
                f"from {report['patterns_found']} patterns"
            )

        return report

    def _store_lesson(self, lesson_text: str, source_pattern: str,
                       confidence: float, evidence_count: int):
        """Store a learned lesson in the database."""
        try:
            lesson_id = hashlib.sha256(lesson_text.encode()).hexdigest()[:12]

            # Check if lesson already exists
            if lesson_id in self._lessons:
                existing = self._lessons[lesson_id]
                existing.evidence_count += evidence_count
                existing.confidence = min(1.0, (existing.confidence + confidence) / 2)
                # Update in DB
                conn = self._get_conn()
                conn.execute(
                    "UPDATE learned_lessons SET confidence=?, evidence_count=? "
                    "WHERE lesson_id=?",
                    (existing.confidence, existing.evidence_count, lesson_id)
                )
                conn.commit()
                return

            lesson = LearnedLesson(
                lesson_id=lesson_id,
                lesson=lesson_text,
                source_pattern=source_pattern,
                confidence=confidence,
                evidence_count=evidence_count,
            )

            conn = self._get_conn()
            conn.execute(
                "INSERT OR REPLACE INTO learned_lessons VALUES (?,?,?,?,?,?,?,?)",
                (lesson.lesson_id, lesson.lesson, lesson.source_pattern,
                 lesson.confidence, lesson.evidence_count, lesson.created_at,
                 lesson.last_used, lesson.times_applied)
            )
            conn.commit()

            self._lessons[lesson_id] = lesson
            self._total_lessons += 1

        except Exception as e:
            logger.error(f"Failed to store lesson: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def _classify_query(self, query: str) -> str:
        """Simple query type classification."""
        q = query.lower().strip()

        if len(q) < 10 or q in ("hi", "hello", "hey", "sup", "yo"):
            return "casual"
        if q.endswith("?") or q.startswith(("what", "how", "why", "when", "where", "who")):
            return "question"
        if any(w in q for w in ("please", "can you", "help me", "i need")):
            return "request"
        if any(w in q for w in ("i feel", "i'm sad", "i'm happy", "i'm anxious")):
            return "emotional"
        if len(q.split()) > 20 or q.count("and") >= 2:
            return "complex"

        return "general"

    def _extract_topics(self, query: str) -> List[str]:
        """Extract key topics from a query (simple stopword removal)."""
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "it", "its", "this", "that", "these", "those", "i", "you",
            "he", "she", "we", "they", "me", "him", "her", "us", "them",
            "my", "your", "his", "our", "their", "and", "or", "but",
            "not", "so", "if", "then", "than", "too", "very", "just",
            "about", "what", "how", "why", "when", "where", "who",
        }

        words = query.lower().split()
        topics = [w.strip(".,!?;:'\"()") for w in words if len(w) > 3]
        topics = [w for w in topics if w and w not in stopwords]

        return topics[:10]

    def _prune_old_episodes(self, conn: sqlite3.Connection):
        """Remove oldest episodes to stay under limit."""
        try:
            conn.execute(
                "DELETE FROM episodes WHERE episode_id IN "
                "(SELECT episode_id FROM episodes "
                "ORDER BY timestamp ASC LIMIT ?)",
                (self._total_episodes - MAX_EPISODES + 100,)
            )
            conn.commit()
            cursor = conn.execute("SELECT COUNT(*) FROM episodes")
            self._total_episodes = cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Prune error: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # LIFECYCLE
    # ──────────────────────────────────────────────────────────────────────────

    def start(self):
        self._running = True
        logger.info(
            f"📝 Episodic Memory started — "
            f"{self._total_episodes} episodes, {self._total_lessons} lessons"
        )

    def stop(self):
        self._running = False
        try:
            if hasattr(self._local, "conn") and self._local.conn:
                self._local.conn.close()
        except Exception:
            pass
        logger.info("📝 Episodic Memory stopped")

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_episodes": self._total_episodes,
            "total_lessons": self._total_lessons,
            "total_recalls": self._total_recalls,
        }

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

episodic_memory = EpisodicMemory()

# ═══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== Episodic Memory Self-Test ===")

    em = EpisodicMemory()
    em.start()

    # Record a test episode
    ep = em.record_from_interaction(
        user_query="What are the ethical implications of AI surveillance?",
        response="AI surveillance raises several ethical concerns...",
        engines_used=["ethical_reasoning", "theory_of_mind"],
        strategy="deliberation",
        emotional_state="curiosity",
        emotional_intensity=0.7,
        quality_score=0.8,
    )
    print(f"\nRecorded episode: {ep.episode_id}")

    # Recall similar experiences
    recall = em.recall("Is AI surveillance ethical?")
    print(f"\nRecall result:")
    print(f"  Similar episodes: {len(recall.similar_episodes)}")
    print(f"  Relevant lessons: {len(recall.relevant_lessons)}")
    print(f"  Suggested strategy: {recall.suggested_strategy}")
    print(f"\nContext string:\n{recall.to_context_string()}")

    # Get stats
    stats = em.get_stats()
    print(f"\nStats: {stats}")

    em.stop()
    print("\n✅ Episodic Memory self-test passed")
