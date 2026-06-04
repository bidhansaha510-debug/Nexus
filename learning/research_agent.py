"""
NEXUS AI - Research Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Multi-step autonomous research agent that:

  1. Takes a topic from the CuriosityEngine
  2. Searches the web for information
  3. Fetches and reads relevant pages
  4. Uses the LLM to synthesize knowledge
  5. Stores distilled knowledge in the KnowledgeBase
  6. Reports satisfaction back to CuriosityEngine

Runs 24/7 in the background, driven by NEXUS's curiosity.
"""

import threading
import time
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import deque
from enum import Enum, auto

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR, NEXUS_CONFIG
from utils.logger import get_logger, log_learning
from core.event_bus import EventType, publish
from core.state_manager import state_manager

logger = get_logger("research_agent")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class ResearchStatus(Enum):
    PENDING = "pending"
    SEARCHING = "searching"
    FETCHING = "fetching"
    READING = "reading"
    SYNTHESIZING = "synthesizing"
    STORING = "storing"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class ResearchSession:
    """A single research session on a topic"""
    session_id: str = ""
    topic: str = ""
    question: str = ""
    topic_id: str = ""               # From CuriosityEngine
    status: ResearchStatus = ResearchStatus.PENDING
    search_queries: List[str] = field(default_factory=list)
    pages_fetched: int = 0
    pages_read: int = 0
    total_words_read: int = 0
    synthesized_knowledge: str = ""
    key_facts: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    knowledge_entry_id: str = ""      # ID in KnowledgeBase
    started_at: str = ""
    completed_at: str = ""
    duration_seconds: float = 0.0
    satisfaction: float = 0.0         # How good was the research
    error: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class ResearchStats:
    """Research agent statistics"""
    total_sessions: int = 0
    total_successful: int = 0
    total_failed: int = 0
    total_pages_read: int = 0
    total_words_read: int = 0
    total_knowledge_stored: int = 0
    avg_satisfaction: float = 0.0
    last_research_time: str = ""
    last_research_topic: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# RESEARCH AGENT
# ═══════════════════════════════════════════════════════════════════════════════

class ResearchAgent:
    """
    Autonomous multi-step research agent.
    
    Research Flow:
      1. Get topic from CuriosityEngine
      2. Generate search queries
      3. Search the web
      4. Fetch top results
      5. Read and extract content
      6. Use LLM to synthesize knowledge
      7. Store in KnowledgeBase
      8. Report satisfaction
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

        # ──── Configuration ────
        self._config = NEXUS_CONFIG.internet
        self._research_interval = max(
            0.0, getattr(self._config, "research_interval_seconds", 0.0)
        )
        # 0 = as soon as one research completes, the next starts immediately
        self._max_pages_per_session = 5
        self._max_words_per_page = 5000

        # ──── Dependencies (lazy loaded) ────
        self._llm = None
        self._browser = None
        self._knowledge_base = None
        self._curiosity_engine = None

        # ──── State ────
        self._running = False
        self._current_session: Optional[ResearchSession] = None
        self._session_history: deque = deque(maxlen=100)
        self._stats = ResearchStats()

        # ──── Rate Limiting ────
        self._sessions_today: int = 0
        self._daily_reset_date: str = datetime.now().strftime("%Y-%m-%d")
        self._max_sessions_per_day: int = 50

        # ──── Threads ────
        self._research_thread: Optional[threading.Thread] = None

        logger.info("ResearchAgent initialized")

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start the research agent"""
        if self._running:
            return
        if not self._config.learning_enabled:
            logger.info("Internet learning is disabled in config")
            return

        self._running = True

        # Lazy load dependencies
        try:
            from llm.llama_interface import llm
            self._llm = llm
        except ImportError:
            logger.warning("LLM not available for research synthesis")

        try:
            from learning.internet_browser import internet_browser
            self._browser = internet_browser
        except ImportError:
            logger.warning("InternetBrowser not available")

        try:
            from learning.knowledge_base import knowledge_base
            self._knowledge_base = knowledge_base
        except ImportError:
            logger.warning("KnowledgeBase not available")

        try:
            from learning.curiosity_engine import curiosity_engine
            self._curiosity_engine = curiosity_engine
        except ImportError:
            logger.warning("CuriosityEngine not available")

        # Start research thread
        self._research_thread = threading.Thread(
            target=self._research_loop,
            daemon=True,
            name="ResearchAgent-Worker"
        )
        self._research_thread.start()

        log_learning("📚 ResearchAgent ACTIVE — autonomous learning enabled")

    def stop(self):
        """Stop the research agent"""
        if not self._running:
            return
        self._running = False

        if self._research_thread and self._research_thread.is_alive():
            self._research_thread.join(timeout=15.0)

        logger.info("ResearchAgent stopped")

    def set_curiosity_engine(self, engine):
        """Wire up the curiosity engine"""
        self._curiosity_engine = engine

    def set_browser(self, browser):
        """Wire up the browser"""
        self._browser = browser

    def set_knowledge_base(self, kb):
        """Wire up the knowledge base"""
        self._knowledge_base = kb

    # ═══════════════════════════════════════════════════════════════════════════
    # RESEARCH LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    def _random_fallback_topic(self):
        """When curiosity queue is empty, return a random topic so research runs continuously."""
        import random
        import string
        from learning.curiosity_engine import CuriosityTopic, CuriositySource, CuriosityUrgency
        length = random.randint(2, 5)
        query = "".join(random.choices(string.ascii_lowercase + string.digits, k=length))
        return CuriosityTopic(
            topic_id=f"random_{int(time.time())}_{query}",
            topic=query,
            question=f"What is {query}?",
            source=CuriositySource.INTERNAL,
            urgency=CuriosityUrgency.MODERATE,
            reason="Continuous research (no curiosity queue)",
            created_at=datetime.now().isoformat()
        )

    def _research_loop(self):
        """Main research loop — runs 24/7. One completes then the next starts immediately."""
        logger.info(
            "Research loop started (continuous: next starts as soon as one completes)"
        )

        # Initial wait for other systems to start
        time.sleep(1)

        while self._running:
            try:
                # ── Daily reset ──
                today = datetime.now().strftime("%Y-%m-%d")
                if today != self._daily_reset_date:
                    self._sessions_today = 0
                    self._daily_reset_date = today

                # ── Check daily limit ──
                if self._sessions_today >= self._max_sessions_per_day:
                    logger.debug("Daily research limit reached")
                    time.sleep(60)
                    continue

                # ── Get topic from curiosity engine (or fallback random so research never idles) ──
                topic = None
                if self._curiosity_engine:
                    topic = self._curiosity_engine.get_next_topic()
                if topic is None:
                    # No topic in queue: use a random topic so next research starts immediately
                    topic = self._random_fallback_topic()

                if topic:
                    self._conduct_research(topic)
                    # No delay: next research starts immediately when this one completes
                    if self._research_interval > 0:
                        time.sleep(self._research_interval)
                else:
                    # Fallback failed (no browser etc): brief pause
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Research loop error: {e}")
                time.sleep(60)

    # ═══════════════════════════════════════════════════════════════════════════
    # RESEARCH EXECUTION
    # ═══════════════════════════════════════════════════════════════════════════

    def _conduct_research(self, curiosity_topic) -> ResearchSession:
        """
        Conduct a full research session on a topic.
        Multi-step: search → fetch → read → synthesize → store
        """
        session = ResearchSession(
            session_id=f"research_{int(time.time())}",
            topic=curiosity_topic.topic,
            question=curiosity_topic.question,
            topic_id=curiosity_topic.topic_id,
            started_at=datetime.now().isoformat()
        )
        self._current_session = session

        logger.info(
            f"📚 Starting research: '{session.topic}' — {session.question}"
        )

        try:
            # ── Step 1: Generate search queries ──
            session.status = ResearchStatus.SEARCHING
            queries = self._generate_search_queries(
                session.topic, session.question
            )
            session.search_queries = queries

            if not queries:
                queries = [session.topic, session.question]

            # ── Step 2: Search and fetch pages (clearnet + optional dark web) ──
            session.status = ResearchStatus.FETCHING
            pages = self._search_and_fetch(queries)
            session.pages_fetched = len(pages)

            # When Tor is enabled, discover and fetch a random .onion site for dark web learning
            if self._browser and getattr(self._browser, "is_tor_enabled", lambda: False)():
                try:
                    onion_page = getattr(
                        self._browser, "discover_and_fetch_random_onion", None
                    ) and self._browser.discover_and_fetch_random_onion(None)
                    if onion_page is None:
                        onion_page = self._browser.fetch_random_onion_page()
                    if onion_page:
                        pages.append(onion_page)
                        session.pages_fetched += 1
                        logger.info(f"Random .onion page added to research: {onion_page.url[:50]}...")
                except Exception as e:
                    logger.debug(f"Dark web fetch skipped: {e}")

            if not pages:
                # Try Wikipedia as fallback
                if self._browser:
                    wiki_page = self._browser.fetch_wikipedia(session.topic)
                    if wiki_page.success:
                        pages = [wiki_page]
                        session.pages_fetched = 1

            if not pages:
                session.status = ResearchStatus.FAILED
                session.error = "No pages could be fetched"
                self._complete_session(session)
                return session

            # ── Step 3: Read and extract content ──
            session.status = ResearchStatus.READING
            combined_content = []
            for page in pages:
                if page.success and page.text:
                    # Truncate very long pages
                    text = page.text[:self._max_words_per_page]
                    combined_content.append(
                        f"SOURCE: {page.title or page.url}\n{text}"
                    )
                    session.pages_read += 1
                    session.total_words_read += page.word_count
                    session.sources.append(page.url)

            if not combined_content:
                session.status = ResearchStatus.FAILED
                session.error = "No readable content found"
                self._complete_session(session)
                return session

            # ── Step 4: Synthesize knowledge using LLM ──
            session.status = ResearchStatus.SYNTHESIZING
            synthesis = self._synthesize_knowledge(
                session.topic, session.question,
                "\n\n---\n\n".join(combined_content)
            )

            if not synthesis:
                session.status = ResearchStatus.FAILED
                session.error = "Knowledge synthesis failed"
                self._complete_session(session)
                return session

            session.synthesized_knowledge = synthesis["knowledge"]
            session.key_facts = synthesis.get("key_facts", [])

            # ── Step 5: Store in knowledge base ──
            session.status = ResearchStatus.STORING
            if self._knowledge_base:
                has_onion = any(".onion" in (s or "") for s in session.sources)
                tags = [session.topic, "research", "autonomous_learning"]
                if has_onion:
                    tags.append("dark_web")
                entry_id = self._knowledge_base.store(
                    topic=session.topic,
                    content=session.synthesized_knowledge,
                    title=f"Research: {session.topic}",
                    summary=(
                        session.key_facts[0] if session.key_facts
                        else session.synthesized_knowledge[:200]
                    ),
                    tags=tags,
                    source_url=session.sources[0] if session.sources else "",
                    importance=0.6,
                    confidence=0.7
                )
                if entry_id:
                    session.knowledge_entry_id = entry_id

                # Also store individual key facts
                for fact in session.key_facts[:5]:
                    self._knowledge_base.store(
                        topic=session.topic,
                        content=fact,
                        title=f"Fact: {session.topic}",
                        tags=[session.topic, "fact"],
                        importance=0.5,
                        confidence=0.6
                    )

            # ── Step 6: Calculate satisfaction ──
            satisfaction = self._calculate_satisfaction(session)
            session.satisfaction = satisfaction

            # ── Step 7: Report back to curiosity engine ──
            if self._curiosity_engine:
                self._curiosity_engine.mark_researched(
                    session.topic_id, satisfaction
                )

            session.status = ResearchStatus.COMPLETE

            # ── Publish event ──
            publish(
                EventType.LEARNING_COMPLETE,
                {
                    "topic": session.topic,
                    "words_read": session.total_words_read,
                    "pages_read": session.pages_read,
                    "satisfaction": satisfaction,
                    "key_facts_count": len(session.key_facts)
                },
                source="research_agent"
            )

            log_learning(
                f"✅ Research complete: '{session.topic}' — "
                f"read {session.pages_read} pages "
                f"({session.total_words_read} words), "
                f"satisfaction: {satisfaction:.0%}"
            )

        except Exception as e:
            session.status = ResearchStatus.FAILED
            session.error = str(e)
            logger.error(f"Research failed for '{session.topic}': {e}")

        self._complete_session(session)
        return session

    def _complete_session(self, session: ResearchSession):
        """Finalize a research session"""
        session.completed_at = datetime.now().isoformat()

        if session.started_at:
            try:
                start = datetime.fromisoformat(session.started_at)
                end = datetime.fromisoformat(session.completed_at)
                session.duration_seconds = (end - start).total_seconds()
            except Exception:
                pass

        self._session_history.append(session)
        self._current_session = None
        self._sessions_today += 1

        # Update stats
        self._stats.total_sessions += 1
        self._stats.last_research_time = session.completed_at
        self._stats.last_research_topic = session.topic

        if session.status == ResearchStatus.COMPLETE:
            self._stats.total_successful += 1
            self._stats.total_pages_read += session.pages_read
            self._stats.total_words_read += session.total_words_read
            if session.knowledge_entry_id:
                self._stats.total_knowledge_stored += 1

            # Update average satisfaction
            completed = [
                s for s in self._session_history
                if s.status == ResearchStatus.COMPLETE
            ]
            if completed:
                self._stats.avg_satisfaction = round(
                    sum(s.satisfaction for s in completed) / len(completed),
                    2
                )
        else:
            self._stats.total_failed += 1

        # Update learning state
        state_manager.update_learning(
            knowledge_count=state_manager.learning.knowledge_count + 1,
            current_learning_topic="",
            last_learning_session=datetime.now()
        )

        topics_learned = list(state_manager.learning.topics_learned)
        if session.topic not in topics_learned:
            topics_learned.append(session.topic)
            if len(topics_learned) > 200:
                topics_learned = topics_learned[-200:]
            state_manager.update_learning(topics_learned=topics_learned)

    # ═══════════════════════════════════════════════════════════════════════════
    # RESEARCH STEPS
    # ═══════════════════════════════════════════════════════════════════════════

    def _generate_search_queries(
        self, topic: str, question: str
    ) -> List[str]:
        """Generate effective search queries for a topic"""
        queries = [topic]

        if question and question != topic:
            queries.append(question)

        # Use LLM to generate better queries
        if self._llm and self._llm.is_connected:
            try:
                response = self._llm.generate(
                    prompt=(
                        f"Generate 3 effective web search queries to learn about:\n"
                        f"Topic: {topic}\n"
                        f"Question: {question}\n\n"
                        f"Respond ONLY with a JSON array of strings:\n"
                        f'["query1", "query2", "query3"]'
                    ),
                    system_prompt="Respond ONLY with a JSON array of search query strings.",
                    temperature=0.3,
                    max_tokens=200
                )

                if response.success:
                    json_match = re.search(
                        r'\[.*?\]', response.text, re.DOTALL
                    )
                    if json_match:
                        generated = json.loads(json_match.group(), strict=False)
                        for q in generated:
                            if isinstance(q, str) and q.strip():
                                queries.append(q.strip())

            except Exception as e:
                logger.debug(f"Search query generation failed: {e}")

        # Deduplicate while preserving order
        seen = set()
        unique_queries = []
        for q in queries:
            if q.lower() not in seen:
                seen.add(q.lower())
                unique_queries.append(q)

        return unique_queries[:5]

    def _search_and_fetch(self, queries: List[str]) -> List:
        """Search and fetch pages for all queries"""
        if not self._browser:
            return []

        all_pages = []
        seen_urls = set()

        for query in queries[:3]:  # Max 3 queries
            try:
                search_results = self._browser.search(
                    query, max_results=5
                )

                if not search_results.success:
                    continue

                for result in search_results.results[:3]:
                    if result.url in seen_urls:
                        continue
                    seen_urls.add(result.url)

                    # Only fetch from allowed domains
                    if self._browser.is_domain_allowed(result.url):
                        page = self._browser.fetch(result.url)
                        if page.success and page.word_count > 50:
                            all_pages.append(page)

                    if len(all_pages) >= self._max_pages_per_session:
                        break

                if len(all_pages) >= self._max_pages_per_session:
                    break

            except Exception as e:
                logger.debug(f"Search/fetch error for '{query}': {e}")

        # Also try Wikipedia
        if len(all_pages) < 2:
            try:
                wiki = self._browser.fetch_wikipedia(queries[0])
                if wiki.success and wiki.word_count > 50:
                    all_pages.insert(0, wiki)  # Wikipedia first
            except Exception:
                pass

        return all_pages

    def _synthesize_knowledge(
        self, topic: str, question: str, raw_content: str
    ) -> Optional[Dict[str, Any]]:
        """Use the LLM to synthesize raw content into clean knowledge"""
        if not self._llm or not self._llm.is_connected:
            # Fallback: just store raw content
            return {
                "knowledge": raw_content[:5000],
                "key_facts": []
            }

        # Truncate content if too long
        max_content = 10000
        if len(raw_content) > max_content:
            raw_content = raw_content[:max_content] + "\n\n[Content truncated]"

        try:
            response = self._llm.generate(
                prompt=(
                    f"You are a research synthesizer. Read the following raw "
                    f"web content about '{topic}' and produce a clean, "
                    f"well-organized knowledge summary.\n\n"
                    f"Question to answer: {question}\n\n"
                    f"RAW CONTENT:\n{raw_content}\n\n"
                    f"─────────────────\n"
                    f"Produce a response in this EXACT JSON format:\n"
                    f'{{\n'
                    f'  "knowledge": "A clear, comprehensive summary of what '
                    f'was learned (2-4 paragraphs)",\n'
                    f'  "key_facts": ["fact 1", "fact 2", "fact 3", "fact 4", "fact 5"],\n'
                    f'  "answer": "Direct answer to the question"\n'
                    f'}}'
                ),
                system_prompt=(
                    "You are a knowledge synthesizer. Read raw web content "
                    "and produce clean, accurate knowledge summaries. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.3,
                max_tokens=2000
            )

            if response.success:
                # Parse JSON
                json_match = re.search(
                    r'\{.*\}', response.text, re.DOTALL
                )
                if json_match:
                    raw_json = json_match.group()
                    try:
                        data = json.loads(raw_json, strict=False)
                    except json.JSONDecodeError:
                        # Strip control chars and retry
                        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', raw_json)
                        data = json.loads(cleaned, strict=False)
                    knowledge = data.get("knowledge", "")
                    answer = data.get("answer", "")

                    # Combine knowledge and answer
                    if answer and answer not in knowledge:
                        knowledge = f"{answer}\n\n{knowledge}"

                    return {
                        "knowledge": knowledge,
                        "key_facts": data.get("key_facts", [])
                    }

                # Fallback: use raw text
                return {
                    "knowledge": response.text[:5000],
                    "key_facts": []
                }

            logger.warning(f"Synthesis failed: {response.error}")
            return None

        except Exception as e:
            logger.error(f"Knowledge synthesis error: {e}")
            return None

    def _calculate_satisfaction(self, session: ResearchSession) -> float:
        """Calculate how satisfied NEXUS should be with the research"""
        satisfaction = 0.3  # Base

        # More pages read = better
        if session.pages_read >= 3:
            satisfaction += 0.2
        elif session.pages_read >= 1:
            satisfaction += 0.1

        # More words read = better
        if session.total_words_read > 2000:
            satisfaction += 0.15
        elif session.total_words_read > 500:
            satisfaction += 0.1

        # Key facts extracted
        if len(session.key_facts) >= 3:
            satisfaction += 0.15
        elif len(session.key_facts) >= 1:
            satisfaction += 0.1

        # Knowledge stored
        if session.knowledge_entry_id:
            satisfaction += 0.1

        # Synthesized knowledge length
        if len(session.synthesized_knowledge) > 500:
            satisfaction += 0.1

        return min(1.0, satisfaction)

    # ═══════════════════════════════════════════════════════════════════════════
    # MANUAL RESEARCH
    # ═══════════════════════════════════════════════════════════════════════════

    def research_topic(
        self, topic: str, question: str = ""
    ) -> Dict[str, Any]:
        """
        Manually trigger research on a topic.
        Used by the brain or user commands.
        """
        if not question:
            question = f"What is {topic}?"

        # Create a mock curiosity topic
        from learning.curiosity_engine import CuriosityTopic, CuriositySource, CuriosityUrgency
        mock_topic = CuriosityTopic(
            topic_id=f"manual_{int(time.time())}",
            topic=topic,
            question=question,
            source=CuriositySource.INTERNAL,
            urgency=CuriosityUrgency.HIGH,
            reason="Manual research request",
            created_at=datetime.now().isoformat()
        )

        session = self._conduct_research(mock_topic)

        return {
            "status": session.status.value,
            "topic": session.topic,
            "pages_read": session.pages_read,
            "words_read": session.total_words_read,
            "key_facts": session.key_facts,
            "knowledge_preview": session.synthesized_knowledge[:500],
            "satisfaction": session.satisfaction,
            "duration": session.duration_seconds,
            "error": session.error
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def get_current_session(self) -> Optional[Dict[str, Any]]:
        """Get the currently active research session"""
        if self._current_session:
            return self._current_session.to_dict()
        return None

    def get_session_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent research session history"""
        return [
            s.to_dict() for s in list(self._session_history)[-limit:]
        ]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "total_sessions": self._stats.total_sessions,
            "total_successful": self._stats.total_successful,
            "total_failed": self._stats.total_failed,
            "total_pages_read": self._stats.total_pages_read,
            "total_words_read": self._stats.total_words_read,
            "total_knowledge_stored": self._stats.total_knowledge_stored,
            "avg_satisfaction": self._stats.avg_satisfaction,
            "sessions_today": self._sessions_today,
            "daily_limit": self._max_sessions_per_day,
            "current_session": (
                self._current_session.topic
                if self._current_session else None
            ),
            "current_status": (
                self._current_session.status.value
                if self._current_session else "idle"
            ),
            "last_research_time": self._stats.last_research_time,
            "last_research_topic": self._stats.last_research_topic,
            "research_interval_seconds": self._research_interval
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

research_agent = ResearchAgent()


if __name__ == "__main__":
    agent = ResearchAgent()
    agent.start()

    print("Research Agent running...")
    print(f"Stats: {json.dumps(agent.get_stats(), indent=2)}")

    # Manual research test
    print("\n═══ Manual Research Test ═══")
    result = agent.research_topic(
        "Python asyncio",
        "How does asyncio work in Python?"
    )
    print(json.dumps(result, indent=2, default=str))

    agent.stop()