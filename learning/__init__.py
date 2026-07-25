"""
NEXUS AI - Learning Package
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Autonomous internet learning, knowledge acquisition, and curiosity.

Components:
  • InternetBrowser  — Web fetching, searching, content extraction
  • KnowledgeBase    — Persistent knowledge storage & retrieval
  • CuriosityEngine  — LLM-driven autonomous topic generation
  • ResearchAgent    — Multi-step autonomous research execution
  • LearningSystem   — Unified orchestrator

Data Flow:
  CuriosityEngine (10min) ──► generates topics
         ↓
  ResearchAgent (30min) ──► picks topic → searches → fetches → reads
         ↓
  InternetBrowser ──► web search & page fetching
         ↓
  LLM ──► synthesizes raw content into knowledge
         ↓
  KnowledgeBase ──► stores distilled knowledge
         ↓
  Brain ──► queries knowledge during conversations
"""

import threading
import time
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

import sys

from utils.logger import get_logger, log_system, log_learning
from core.event_bus import EventType, publish

logger = get_logger("learning")

# ═══════════════════════════════════════════════════════════════════════════════
# LAZY IMPORTS & SINGLETONS
# ═══════════════════════════════════════════════════════════════════════════════

_internet_browser = None
_knowledge_base = None
_curiosity_engine = None
_research_agent = None
_user_behavior_learner = None
_enhanced_sources = None
_research_intelligence = None
_lock = threading.Lock()

def _get_internet_browser():
    global _internet_browser
    if _internet_browser is None:
        with _lock:
            if _internet_browser is None:
                from learning.internet_browser import InternetBrowser
                _internet_browser = InternetBrowser()
    return _internet_browser

def _get_knowledge_base():
    global _knowledge_base
    if _knowledge_base is None:
        with _lock:
            if _knowledge_base is None:
                from learning.knowledge_base import KnowledgeBase
                _knowledge_base = KnowledgeBase()
    return _knowledge_base

def _get_curiosity_engine():
    global _curiosity_engine
    if _curiosity_engine is None:
        with _lock:
            if _curiosity_engine is None:
                from learning.curiosity_engine import CuriosityEngine
                _curiosity_engine = CuriosityEngine()
    return _curiosity_engine

def _get_research_agent():
    global _research_agent
    if _research_agent is None:
        with _lock:
            if _research_agent is None:
                from learning.research_agent import ResearchAgent
                _research_agent = ResearchAgent()
    return _research_agent

def _get_user_behavior_learner():
    global _user_behavior_learner
    if _user_behavior_learner is None:
        with _lock:
            if _user_behavior_learner is None:
                from learning.user_behavior_learner import UserBehaviorLearner
                _user_behavior_learner = UserBehaviorLearner()
    return _user_behavior_learner

def _get_enhanced_sources():
    global _enhanced_sources
    if _enhanced_sources is None:
        with _lock:
            if _enhanced_sources is None:
                from learning.enhanced_sources import EnhancedSources
                _enhanced_sources = EnhancedSources()
    return _enhanced_sources

def _get_research_intelligence():
    global _research_intelligence
    if _research_intelligence is None:
        with _lock:
            if _research_intelligence is None:
                from learning.research_intelligence import ResearchIntelligence
                _research_intelligence = ResearchIntelligence()
    return _research_intelligence

# ═══════════════════════════════════════════════════════════════════════════════
# LEARNING SYSTEM — Unified Orchestrator
# ═══════════════════════════════════════════════════════════════════════════════

class LearningSystem:
    """
    Orchestrates all learning components.

    Timing:
      CuriosityEngine — generates topics every ~10 min
      ResearchAgent   — researches one topic every ~30 min
      KnowledgeBase   — queried on demand by brain
      Browser         — used by ResearchAgent for fetching

    Orchestrator duties:
      • Start/stop all components in correct order
      • Wire dependencies between components
      • Periodic knowledge maintenance (decay, cleanup)
      • Provide unified API for the brain
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

        self._running = False
        self._internet_browser = None
        self._knowledge_base = None
        self._curiosity_engine = None
        self._research_agent = None
        self._startup_time: Optional[datetime] = None

        # ── Maintenance timing ──
        self._maintenance_thread: Optional[threading.Thread] = None
        self._maintenance_interval = 3600  # 1 hour

        logger.info("LearningSystem initialized")

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start all learning components in correct order"""
        if self._running:
            logger.warning("LearningSystem already running")
            return

        self._running = True
        self._startup_time = datetime.now()

        # ── Initialize components ──
        self._internet_browser = _get_internet_browser()
        self._knowledge_base = _get_knowledge_base()
        self._curiosity_engine = _get_curiosity_engine()
        self._research_agent = _get_research_agent()

        # ── Wire dependencies ──
        # ResearchAgent needs browser, knowledge base, and curiosity engine
        self._research_agent.set_browser(self._internet_browser)
        self._research_agent.set_knowledge_base(self._knowledge_base)
        self._research_agent.set_curiosity_engine(self._curiosity_engine)

        # ── Start in order: infrastructure → generators → workers ──
        # Browser and KnowledgeBase don't have start() — they're always ready
        self._curiosity_engine.start()
        self._research_agent.start()

        # ── Start maintenance thread ──
        self._maintenance_thread = threading.Thread(
            target=self._maintenance_loop,
            daemon=True,
            name="Learning-Maintenance"
        )
        self._maintenance_thread.start()

        log_system(
            "📚 LearningSystem ACTIVE — "
            "autonomous curiosity + research + knowledge storage"
        )

    def stop(self):
        """Stop all learning components gracefully"""
        if not self._running:
            return

        logger.info("LearningSystem shutting down...")
        self._running = False

        # Stop in reverse order
        if self._research_agent:
            try:
                self._research_agent.stop()
            except Exception as e:
                logger.error(f"Error stopping research agent: {e}")

        if self._curiosity_engine:
            try:
                self._curiosity_engine.stop()
            except Exception as e:
                logger.error(f"Error stopping curiosity engine: {e}")

        # Run final maintenance
        if self._knowledge_base:
            try:
                self._knowledge_base.apply_decay()
                self._internet_browser.clear_cache()
            except Exception as e:
                logger.error(f"Error in final maintenance: {e}")

        if self._maintenance_thread and self._maintenance_thread.is_alive():
            self._maintenance_thread.join(timeout=5.0)

        logger.info("LearningSystem stopped")

    # ═══════════════════════════════════════════════════════════════════════════
    # MAINTENANCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _maintenance_loop(self):
        """Periodic knowledge maintenance"""
        logger.info("Learning maintenance loop started")

        while self._running:
            try:
                time.sleep(self._maintenance_interval)

                if not self._running:
                    break

                # ── Knowledge decay ──
                if self._knowledge_base:
                    self._knowledge_base.apply_decay(decay_rate=0.001)
                    self._knowledge_base.cleanup()

                # ── Clear expired cache ──
                if self._internet_browser:
                    self._internet_browser.clear_cache()

                logger.debug("Learning maintenance complete")

            except Exception as e:
                logger.error(f"Learning maintenance error: {e}")
                time.sleep(300)

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API — Used by NexusBrain
    # ═══════════════════════════════════════════════════════════════════════════

    @property
    def internet_browser(self):
        return self._internet_browser

    @property
    def knowledge_base(self):
        return self._knowledge_base

    @property
    def curiosity_engine(self):
        return self._curiosity_engine

    @property
    def research_agent(self):
        return self._research_agent

    @property
    def is_running(self) -> bool:
        return self._running

    def get_knowledge_context(self, query: str, max_tokens: int = 1000) -> str:
        """
        Get knowledge context for a query.
        Called by the brain during response generation.
        """
        if self._knowledge_base:
            try:
                return self._knowledge_base.get_context_for_query(
                    query, max_tokens
                )
            except Exception as e:
                logger.error(f"Knowledge context error: {e}")
        return ""

    def has_knowledge_about(self, topic: str) -> bool:
        """Check if NEXUS has learned anything about a topic"""
        if self._knowledge_base:
            try:
                return self._knowledge_base.has_knowledge_about(topic)
            except Exception:
                pass
        return False

    def search_knowledge(
        self, query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search the knowledge base"""
        if self._knowledge_base:
            try:
                entries = self._knowledge_base.search(query, limit)
                return [e.to_dict() for e in entries]
            except Exception as e:
                logger.error(f"Knowledge search error: {e}")
        return []

    def research_now(
        self, topic: str, question: str = ""
    ) -> Dict[str, Any]:
        """Trigger immediate research on a topic"""
        if self._research_agent:
            try:
                return self._research_agent.research_topic(topic, question)
            except Exception as e:
                return {"status": "error", "error": str(e)}
        return {"status": "error", "error": "Research agent not active"}

    def add_curiosity(
        self, topic: str, reason: str = "Brain is curious"
    ) -> Optional[str]:
        """Add a topic to the curiosity queue"""
        if self._curiosity_engine:
            try:
                from learning.curiosity_engine import (
                    CuriositySource, CuriosityUrgency
                )
                return self._curiosity_engine.add_topic(
                    topic=topic,
                    reason=reason,
                    source=CuriositySource.INTERNAL,
                    urgency=CuriosityUrgency.MODERATE
                )
            except Exception as e:
                logger.error(f"Add curiosity error: {e}")
        return None

    def spark_from_conversation(self, user_input: str, response: str):
        """Let curiosity engine analyze conversation for sparks"""
        if self._curiosity_engine:
            try:
                self._curiosity_engine.spark_from_conversation(
                    user_input, response
                )
            except Exception:
                pass

    def get_learning_summary(self) -> str:
        """Get a human-readable learning summary"""
        parts = []

        if self._knowledge_base:
            stats = self._knowledge_base.get_stats()
            parts.append(
                f"Knowledge Base: {stats['total_entries']} entries "
                f"across {stats['unique_topics']} topics"
            )
            top = stats.get("top_topics", {})
            if top:
                top_str = ", ".join(
                    f"{t} ({c})" for t, c in list(top.items())[:5]
                )
                parts.append(f"Top topics: {top_str}")

        if self._curiosity_engine:
            cstats = self._curiosity_engine.get_stats()
            parts.append(
                f"Curiosity: {cstats['active_topics']} active topics, "
                f"{cstats['topics_researched']} researched"
            )

        if self._research_agent:
            rstats = self._research_agent.get_stats()
            parts.append(
                f"Research: {rstats['total_sessions']} sessions, "
                f"{rstats['total_pages_read']} pages read, "
                f"{rstats['total_words_read']} words consumed"
            )
            if rstats.get("last_research_topic"):
                parts.append(
                    f"Last researched: {rstats['last_research_topic']}"
                )

        if self._internet_browser:
            bstats = self._internet_browser.get_stats()
            parts.append(
                f"Browser: {bstats['total_requests']} requests, "
                f"{bstats['bytes_downloaded_mb']} MB downloaded"
            )

        return "\n".join(parts) if parts else "No learning data yet."

    def get_curiosity_topics(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get active curiosity topics"""
        if self._curiosity_engine:
            try:
                return self._curiosity_engine.get_active_topics()[:limit]
            except Exception:
                pass
        return []

    def get_user_summary(self) -> Dict[str, Any]:
        """Get comprehensive learning summary"""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "uptime": self._get_uptime_str()
        }

        if self._knowledge_base:
            try:
                summary["knowledge"] = self._knowledge_base.get_stats()
            except Exception as e:
                summary["knowledge_error"] = str(e)

        if self._curiosity_engine:
            try:
                summary["curiosity"] = self._curiosity_engine.get_stats()
            except Exception as e:
                summary["curiosity_error"] = str(e)

        if self._research_agent:
            try:
                summary["research"] = self._research_agent.get_stats()
            except Exception as e:
                summary["research_error"] = str(e)

        if self._internet_browser:
            try:
                summary["browser"] = self._internet_browser.get_stats()
            except Exception as e:
                summary["browser_error"] = str(e)

        return summary

    def get_stats(self) -> Dict[str, Any]:
        """Get combined stats for all learning components"""
        stats = {
            "running": self._running,
            "uptime": self._get_uptime_str()
        }

        if self._knowledge_base:
            try:
                stats["knowledge_base"] = self._knowledge_base.get_stats()
            except Exception as e:
                stats["knowledge_base"] = {"error": str(e)}

        if self._curiosity_engine:
            try:
                stats["curiosity"] = self._curiosity_engine.get_stats()
            except Exception as e:
                stats["curiosity"] = {"error": str(e)}

        if self._research_agent:
            try:
                stats["research"] = self._research_agent.get_stats()
            except Exception as e:
                stats["research"] = {"error": str(e)}

        if self._internet_browser:
            try:
                stats["browser"] = self._internet_browser.get_stats()
            except Exception as e:
                stats["browser"] = {"error": str(e)}

        return stats

    def _get_uptime_str(self) -> str:
        if not self._startup_time:
            return "not started"
        seconds = (datetime.now() - self._startup_time).total_seconds()
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

# ═══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL SINGLETONS (LAZY)
# Prevent side effects during import (important for test collection).
# ═══════════════════════════════════════════════════════════════════════════════

_learning_system_singleton: Optional[LearningSystem] = None
_learning_system_lock = threading.Lock()

def get_learning_system() -> LearningSystem:
    """Lazily create the LearningSystem singleton (no import-time side effects)."""
    global _learning_system_singleton
    if _learning_system_singleton is None:
        with _learning_system_lock:
            if _learning_system_singleton is None:
                _learning_system_singleton = LearningSystem()
    return _learning_system_singleton

def get_internet_browser():
    return _get_internet_browser()

def get_knowledge_base():
    return _get_knowledge_base()

def get_curiosity_engine():
    return _get_curiosity_engine()

def get_research_agent():
    return _get_research_agent()

def get_user_behavior_learner():
    return _get_user_behavior_learner()

def get_enhanced_sources():
    return _get_enhanced_sources()

def get_research_intelligence():
    return _get_research_intelligence()

__all__ = [
    "LearningSystem", "get_learning_system",
    "get_internet_browser", "get_knowledge_base",
    "get_curiosity_engine", "get_research_agent",
    "get_user_behavior_learner", "get_enhanced_sources",
    "get_research_intelligence",
]
