"""
NEXUS AI - Enhanced Learning Sources
═══════════════════════════════════════════════════════════════════════════════
Extended sources for autonomous learning beyond basic web search.

Sources included:
  • GitHub Trending - Discover trending repositories
  • Hacker News - Top tech discussions
  • Reddit r/MachineLearning - ML community insights
  • arXiv Papers - Latest research papers
  • Dev.to / Medium - Developer articles
  • Wikipedia Random - Serendipitous discovery

Each source provides curated topics for the curiosity engine.
═══════════════════════════════════════════════════════════════════════════════
"""

import threading
import time
import json
import re
import random
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import deque

import sys

from config import DATA_DIR, NEXUS_CONFIG
from utils.logger import get_logger, log_learning
from core.event_bus import EventType, publish

logger = get_logger("enhanced_sources")

# Optional imports
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    logger.warning("requests not installed — enhanced sources limited")

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    logger.warning("beautifulsoup4 not installed — HTML parsing limited")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SourceResult:
    """A single result from an enhanced source"""
    source: str = ""
    title: str = ""
    url: str = ""
    summary: str = ""
    topics: List[str] = field(default_factory=list)
    relevance_score: float = 0.5
    timestamp: str = ""
    raw_content: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class SourceStats:
    """Statistics for a source"""
    source_name: str = ""
    total_fetched: int = 0
    successful: int = 0
    failed: int = 0
    last_fetch: str = ""
    avg_relevance: float = 0.5

# ═══════════════════════════════════════════════════════════════════════════════
# ENHANCED SOURCES ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class EnhancedSources:
    """
    Manages multiple learning sources for NEXUS.
    
    Sources are polled periodically and topics are fed to the curiosity engine.
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
        self._cache_dir = DATA_DIR / "enhanced_sources"
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        # ──── State ────
        self._running = False
        self._results: deque = deque(maxlen=500)
        self._source_stats: Dict[str, SourceStats] = {}
        self._last_fetch_times: Dict[str, datetime] = {}

        # ──── Configuration ────
        self._fetch_interval = 3600  # 1 hour between source fetches
        self._session = None
        if HAS_REQUESTS:
            self._session = requests.Session()
            self._session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            })

        # ──── Background thread ────
        self._fetch_thread: Optional[threading.Thread] = None

        logger.info("📡 Enhanced Sources initialized")

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start the enhanced sources fetcher"""
        if self._running:
            return

        self._running = True

        self._fetch_thread = threading.Thread(
            target=self._fetch_loop,
            daemon=True,
            name="EnhancedSources-Fetcher"
        )
        self._fetch_thread.start()

        log_learning("📡 Enhanced Sources ACTIVE — expanded learning sources enabled")

    def stop(self):
        """Stop the fetcher"""
        self._running = False

        if self._fetch_thread and self._fetch_thread.is_alive():
            self._fetch_thread.join(timeout=5.0)

        logger.info("Enhanced Sources stopped")

    # ═══════════════════════════════════════════════════════════════════════════
    # FETCH LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    def _fetch_loop(self):
        """Periodically fetch from all sources"""
        logger.info("Enhanced sources fetch loop started")

        time.sleep(60)  # Initial delay

        while self._running:
            try:
                # Fetch from each source in rotation
                sources = [
                    ("github", self._fetch_github_trending),
                    ("hackernews", self._fetch_hackernews),
                    ("reddit_ml", self._fetch_reddit_ml),
                    ("arxiv", self._fetch_arxiv),
                    ("devto", self._fetch_devto),
                    ("wikipedia_random", self._fetch_wikipedia_random),
                ]

                for source_name, fetch_func in sources:
                    if not self._running:
                        break

                    # Check if it's time to fetch this source
                    last = self._last_fetch_times.get(source_name)
                    if last and (datetime.now() - last).total_seconds() < self._fetch_interval:
                        continue

                    try:
                        results = fetch_func()
                        if results:
                            self._process_results(source_name, results)
                            self._last_fetch_times[source_name] = datetime.now()
                            self._update_stats(source_name, len(results), 0)
                        else:
                            self._update_stats(source_name, 0, 1)

                    except Exception as e:
                        logger.debug(f"Fetch error for {source_name}: {e}")
                        self._update_stats(source_name, 0, 1)

                    time.sleep(5)  # Delay between sources

                time.sleep(300)  # 5 minutes between cycles

            except Exception as e:
                logger.error(f"Enhanced sources loop error: {e}")
                time.sleep(60)

    def _process_results(self, source: str, results: List[SourceResult]):
        """Process and store results"""
        for result in results:
            self._results.append(result)

            # Publish to curiosity engine
            for topic in result.topics:
                publish(
                    EventType.CURIOSITY_TRIGGER,
                    {
                        "topic": topic,
                        "reason": f"Discovered from {source}: {result.title[:50]}",
                        "source": source,
                        "url": result.url
                    },
                    source="enhanced_sources"
                )

    def _update_stats(self, source: str, success_count: int, fail_count: int):
        """Update source statistics"""
        if source not in self._source_stats:
            self._source_stats[source] = SourceStats(source_name=source)

        stats = self._source_stats[source]
        stats.total_fetched += success_count + fail_count
        stats.successful += success_count
        stats.failed += fail_count
        stats.last_fetch = datetime.now().isoformat()

    # ═══════════════════════════════════════════════════════════════════════════
    # SOURCE IMPLEMENTATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    def _fetch_github_trending(self) -> List[SourceResult]:
        """Fetch trending repositories from GitHub"""
        if not HAS_REQUESTS:
            return []

        results = []

        try:
            # GitHub trending page
            url = "https://github.com/trending"
            response = self._session.get(url, timeout=15)

            if response.status_code != 200:
                return []

            if HAS_BS4:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Find trending repos
                articles = soup.find_all('article', class_='Box-row')[:10]

                for article in articles:
                    try:
                        # Get repo link
                        link = article.find('h2').find('a')
                        if link:
                            repo_path = link.get('href', '')
                            title = repo_path.strip('/').replace('/', ' / ')

                            # Get description
                            desc_p = article.find('p', class_='col-9')
                            desc = desc_p.get_text(strip=True) if desc_p else ""

                            # Extract topics
                            topics = self._extract_topics_from_text(f"{title} {desc}")

                            results.append(SourceResult(
                                source="github_trending",
                                title=title,
                                url=f"https://github.com{repo_path}",
                                summary=desc[:200],
                                topics=topics,
                                relevance_score=0.7,
                                timestamp=datetime.now().isoformat()
                            ))
                    except Exception:
                        continue

            logger.debug(f"GitHub trending: {len(results)} repos")

        except Exception as e:
            logger.debug(f"GitHub trending fetch error: {e}")

        return results

    def _fetch_hackernews(self) -> List[SourceResult]:
        """Fetch top stories from Hacker News"""
        if not HAS_REQUESTS:
            return []

        results = []

        try:
            # Get top story IDs
            top_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
            response = self._session.get(top_url, timeout=10)

            if response.status_code != 200:
                return []

            story_ids = response.json()[:15]  # Top 15 stories

            for story_id in story_ids:
                try:
                    story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                    story_response = self._session.get(story_url, timeout=10)

                    if story_response.status_code == 200:
                        story = story_response.json()

                        if story and story.get('title'):
                            title = story.get('title', '')
                            url = story.get('url', f"https://news.ycombinator.com/item?id={story_id}")
                            score = story.get('score', 0)

                            topics = self._extract_topics_from_text(title)

                            results.append(SourceResult(
                                source="hackernews",
                                title=title,
                                url=url,
                                summary=f"Score: {score}",
                                topics=topics,
                                relevance_score=min(1.0, score / 500),
                                timestamp=datetime.now().isoformat()
                            ))
                except Exception:
                    continue

                time.sleep(0.2)  # Rate limiting

            logger.debug(f"HackerNews: {len(results)} stories")

        except Exception as e:
            logger.debug(f"HackerNews fetch error: {e}")

        return results

    def _fetch_reddit_ml(self) -> List[SourceResult]:
        """Fetch posts from r/MachineLearning"""
        if not HAS_REQUESTS:
            return []

        results = []

        try:
            # Reddit JSON API
            url = "https://www.reddit.com/r/MachineLearning/hot.json?limit=15"
            response = self._session.get(url, timeout=15)

            if response.status_code != 200:
                return []

            data = response.json()
            posts = data.get('data', {}).get('children', [])

            for post in posts:
                try:
                    post_data = post.get('data', {})

                    title = post_data.get('title', '')
                    url = post_data.get('url', '')
                    self_text = post_data.get('selftext', '')[:200]
                    score = post_data.get('score', 0)

                    topics = self._extract_topics_from_text(f"{title} {self_text}")

                    results.append(SourceResult(
                        source="reddit_ml",
                        title=title,
                        url=url or f"https://reddit.com{post_data.get('permalink', '')}",
                        summary=self_text,
                        topics=topics,
                        relevance_score=min(1.0, score / 1000),
                        timestamp=datetime.now().isoformat()
                    ))
                except Exception:
                    continue

            logger.debug(f"Reddit ML: {len(results)} posts")

        except Exception as e:
            logger.debug(f"Reddit fetch error: {e}")

        return results

    def _fetch_arxiv(self) -> List[SourceResult]:
        """Fetch recent ML papers from arXiv"""
        if not HAS_REQUESTS:
            return []

        results = []

        try:
            # arXiv API for recent ML papers
            # Categories: cs.AI, cs.LG, cs.CL, cs.CV
            url = "http://export.arxiv.org/api/query"
            params = {
                'search_query': 'cat:cs.AI OR cat:cs.LG OR cat:cs.CL OR cat:cs.CV',
                'start': 0,
                'max_results': 10,
                'sortBy': 'submittedDate',
                'sortOrder': 'descending'
            }

            response = self._session.get(url, params=params, timeout=30)

            if response.status_code != 200:
                return []

            # Parse XML response
            text = response.text

            # Simple regex extraction (arXiv uses Atom XML)
            entries = re.findall(r'<entry>(.*?)</entry>', text, re.DOTALL)

            for entry in entries[:10]:
                try:
                    # Extract title
                    title_match = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
                    title = title_match.group(1).strip().replace('\n', ' ') if title_match else ''

                    # Extract summary
                    summary_match = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
                    summary = summary_match.group(1).strip()[:300] if summary_match else ''

                    # Extract link
                    link_match = re.search(r'<id>(.*?)</id>', entry, re.DOTALL)
                    link = link_match.group(1).strip() if link_match else ''

                    topics = self._extract_topics_from_text(f"{title} {summary}")

                    results.append(SourceResult(
                        source="arxiv",
                        title=title,
                        url=link,
                        summary=summary,
                        topics=topics,
                        relevance_score=0.8,  # Papers are highly relevant
                        timestamp=datetime.now().isoformat()
                    ))
                except Exception:
                    continue

            logger.debug(f"arXiv: {len(results)} papers")

        except Exception as e:
            logger.debug(f"arXiv fetch error: {e}")

        return results

    def _fetch_devto(self) -> List[SourceResult]:
        """Fetch popular articles from Dev.to"""
        if not HAS_REQUESTS:
            return []

        results = []

        try:
            # Dev.to API
            url = "https://dev.to/api/articles?per_page=15&top=7"
            response = self._session.get(url, timeout=15)

            if response.status_code != 200:
                return []

            articles = response.json()

            for article in articles[:10]:
                try:
                    title = article.get('title', '')
                    url = article.get('url', '')
                    desc = article.get('description', '')
                    reactions = article.get('positive_reactions_count', 0)

                    topics = self._extract_topics_from_text(f"{title} {desc}")

                    results.append(SourceResult(
                        source="devto",
                        title=title,
                        url=url,
                        summary=desc,
                        topics=topics,
                        relevance_score=min(1.0, reactions / 500),
                        timestamp=datetime.now().isoformat()
                    ))
                except Exception:
                    continue

            logger.debug(f"Dev.to: {len(results)} articles")

        except Exception as e:
            logger.debug(f"Dev.to fetch error: {e}")

        return results

    def _fetch_wikipedia_random(self) -> List[SourceResult]:
        """Fetch a random Wikipedia article for serendipity"""
        if not HAS_REQUESTS:
            return []

        results = []

        try:
            # Wikipedia random article API
            url = "https://en.wikipedia.org/api/rest_v1/page/random/summary"
            response = self._session.get(url, timeout=15)

            if response.status_code != 200:
                return []

            data = response.json()

            title = data.get('title', '')
            extract = data.get('extract', '')[:500]
            wiki_url = data.get('content_urls', {}).get('desktop', {}).get('page', '')

            topics = self._extract_topics_from_text(f"{title} {extract}")

            results.append(SourceResult(
                source="wikipedia_random",
                title=title,
                url=wiki_url,
                summary=extract,
                topics=topics,
                relevance_score=0.5,  # Random discovery
                timestamp=datetime.now().isoformat()
            ))

            logger.debug(f"Wikipedia random: {title}")

        except Exception as e:
            logger.debug(f"Wikipedia random fetch error: {e}")

        return results

    # ═══════════════════════════════════════════════════════════════════════════
    # TOPIC EXTRACTION
    # ═══════════════════════════════════════════════════════════════════════════

    def _extract_topics_from_text(self, text: str) -> List[str]:
        """Extract relevant topics from text"""
        topics = []

        # Technical keywords
        tech_keywords = [
            'artificial intelligence', 'machine learning', 'deep learning',
            'neural network', 'natural language', 'computer vision',
            'reinforcement learning', 'transformer', 'gpt', 'llm',
            'python', 'javascript', 'rust', 'golang', 'typescript',
            'docker', 'kubernetes', 'cloud', 'serverless',
            'api', 'database', 'blockchain', 'web3',
            'security', 'encryption', 'privacy',
            'optimization', 'algorithm', 'performance',
        ]

        # Science keywords
        science_keywords = [
            'quantum', 'physics', 'chemistry', 'biology',
            'neuroscience', 'psychology', 'cognitive',
            'climate', 'energy', 'sustainability',
        ]

        text_lower = text.lower()

        all_keywords = tech_keywords + science_keywords

        for keyword in all_keywords:
            if keyword in text_lower:
                topics.append(keyword)

        return list(set(topics))[:5]

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def get_recent_results(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent results from all sources"""
        return [r.to_dict() for r in list(self._results)[-limit:]]

    def get_results_by_source(self, source: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get results from a specific source"""
        return [
            r.to_dict() for r in self._results
            if r.source == source
        ][-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all sources"""
        return {
            "running": self._running,
            "total_results": len(self._results),
            "sources": {
                name: asdict(stats)
                for name, stats in self._source_stats.items()
            },
            "last_fetch_times": {
                name: t.isoformat()
                for name, t in self._last_fetch_times.items()
            }
        }

    def get_topics_for_curiosity(self, limit: int = 20) -> List[str]:
        """Get curated topics for the curiosity engine"""
        all_topics = []

        for result in self._results:
            all_topics.extend(result.topics)

        # Count and return most common
        from collections import Counter
        topic_counts = Counter(all_topics)

        return [t for t, _ in topic_counts.most_common(limit)]

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

enhanced_sources = EnhancedSources()

if __name__ == "__main__":
    print("📡 Enhanced Sources Test")

    sources = EnhancedSources()

    # Test individual sources
    print("\n--- GitHub Trending ---")
    gh = sources._fetch_github_trending()
    for r in gh[:3]:
        print(f"  {r.title}: {r.summary[:50]}")

    print("\n--- Hacker News ---")
    hn = sources._fetch_hackernews()
    for r in hn[:3]:
        print(f"  {r.title}")

    print(f"\nStats: {json.dumps(sources.get_stats(), indent=2)}")
    print(f"\nTopics for curiosity: {sources.get_topics_for_curiosity(10)}")