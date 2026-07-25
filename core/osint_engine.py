"""
NEXUS AI — Real-Time OSINT Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Continuous open-source intelligence gathering engine. Monitors public
feeds, social media, news, vulnerability databases, and paste sites
for threat detection, trend analysis, and actionable intelligence.

Pipeline:
  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
  │  SCRAPER     │───▶│  ANALYZER    │───▶│  REPORTER    │
  │  Multi-Feed  │    │  NLP / TF-IDF│    │  Auto-Report │
  └──────────────┘    └──────────────┘    └──────────────┘
       │                    │                     │
       ▼                    ▼                     ▼
  ┌──────────┐      ┌──────────────┐      ┌──────────────┐
  │ Twitter  │      │ Threat Score │      │ Intelligence │
  │ Reddit   │      │ Sentiment    │      │   Reports    │
  │ News RSS │      │ Entity Ext.  │      │ Target Track │
  │ Shodan   │      │ Trend Detect │      │   Alerts     │
  │ Pastebin │      │ Keyword Mon  │      │              │
  └──────────┘      └──────────────┘      └──────────────┘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import hashlib
import json
import math
import os
import re
import sys
import threading
import time
import traceback
import uuid
import xml.etree.ElementTree as ET
from collections import Counter, deque, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import quote_plus, urlparse

from config import DATA_DIR
from utils.logger import get_logger, log_system
from core.event_bus import EventType, event_bus, publish

logger = get_logger("osint_engine")

# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

class FeedType(Enum):
    """Types of OSINT feeds."""
    RSS_NEWS = "rss_news"
    REDDIT = "reddit"
    TWITTER = "twitter"
    SHODAN = "shodan"
    CVE_DATABASE = "cve_database"
    PASTEBIN = "pastebin"
    GITHUB = "github"
    DARKWEB = "darkweb"
    CUSTOM = "custom"

class ThreatCategory(Enum):
    """Categories of detected threats."""
    VULNERABILITY = "vulnerability"
    MALWARE = "malware"
    DATA_BREACH = "data_breach"
    PHISHING = "phishing"
    APT = "apt"
    DDOS = "ddos"
    RANSOMWARE = "ransomware"
    ZERO_DAY = "zero_day"
    SOCIAL_ENGINEERING = "social_engineering"
    INSIDER_THREAT = "insider_threat"
    GENERAL = "general"

class SentimentLevel(Enum):
    """Sentiment analysis results."""
    VERY_NEGATIVE = "very_negative"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    VERY_POSITIVE = "very_positive"

class AlertPriority(Enum):
    """Alert priority levels."""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    INFO = 4

# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class OSINTArticle:
    """A piece of intelligence gathered from a feed."""
    article_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    source: str = ""
    feed_type: str = "rss_news"
    title: str = ""
    content: str = ""
    url: str = ""
    author: str = ""
    published_at: str = ""
    scraped_at: str = field(default_factory=lambda: datetime.now().isoformat())
    threat_score: float = 0.0
    sentiment: float = 0.0
    categories: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    is_relevant: bool = False
    content_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def summary(self) -> str:
        return f"[{self.source}] {self.title[:80]} (threat={self.threat_score:.1f})"

@dataclass
class FeedConfig:
    """Configuration for an OSINT feed source."""
    feed_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    feed_type: str = "rss_news"
    url: str = ""
    enabled: bool = True
    poll_interval: int = 300  # seconds
    api_key: str = ""
    max_results: int = 50
    keywords_filter: List[str] = field(default_factory=list)
    last_polled: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if d.get("api_key"):
            d["api_key"] = "***"  # Redact
        return d

@dataclass
class ThreatAlert:
    """An alert generated from OSINT analysis."""
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    priority: int = 2
    category: str = "general"
    title: str = ""
    description: str = ""
    source_articles: List[str] = field(default_factory=list)
    indicators: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    acknowledged: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class IntelligenceReport:
    """An auto-generated intelligence report."""
    report_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    title: str = ""
    period: str = ""
    summary: str = ""
    threat_landscape: Dict[str, int] = field(default_factory=dict)
    top_threats: List[Dict[str, Any]] = field(default_factory=list)
    trending_topics: List[str] = field(default_factory=list)
    sentiment_overview: Dict[str, float] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    article_count: int = 0
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class TrackedTarget:
    """An entity being tracked across OSINT feeds."""
    target_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    aliases: List[str] = field(default_factory=list)
    target_type: str = ""  # person, org, domain, ip, etc
    keywords: List[str] = field(default_factory=list)
    mentions: int = 0
    last_seen: Optional[str] = None
    threat_level: float = 0.0
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class OSINTStats:
    """OSINT engine statistics."""
    total_articles_scraped: int = 0
    total_articles_relevant: int = 0
    total_alerts_generated: int = 0
    total_reports_generated: int = 0
    total_feeds_active: int = 0
    total_targets_tracked: int = 0
    avg_threat_score: float = 0.0
    last_scrape_time: Optional[str] = None
    last_report_time: Optional[str] = None
    articles_per_hour: float = 0.0
    top_categories: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# ═══════════════════════════════════════════════════════════════════════════════
# TEXT ANALYZER (Built-in NLP)
# ═══════════════════════════════════════════════════════════════════════════════

class TextAnalyzer:
    """Lightweight NLP for text analysis without external dependencies."""

    def __init__(self):
        self._threat_keywords = {
            "vulnerability": 3.0, "exploit": 3.0, "zero-day": 4.0, "0day": 4.0,
            "breach": 3.5, "leaked": 3.0, "ransomware": 3.5, "malware": 3.0,
            "backdoor": 3.5, "trojan": 3.0, "phishing": 2.5, "attack": 2.0,
            "hacked": 3.0, "compromised": 3.0, "infected": 2.5, "botnet": 3.0,
            "ddos": 2.5, "injection": 2.5, "rce": 4.0, "remote code": 4.0,
            "privilege escalation": 3.5, "data leak": 3.5, "credentials": 2.0,
            "cve-": 3.0, "critical": 2.0, "severity": 1.5, "patch": 1.5,
            "apt": 3.0, "threat actor": 3.0, "campaign": 2.0,
            "supply chain": 3.0, "cryptojacking": 2.5, "skimmer": 2.5,
        }
        self._positive_words = {
            "good", "great", "excellent", "secure", "safe", "patched",
            "fixed", "resolved", "improved", "success", "strong", "stable",
        }
        self._negative_words = {
            "bad", "critical", "severe", "dangerous", "exposed", "vulnerable",
            "unpatched", "failure", "weak", "broken", "leaked", "compromised",
            "malicious", "threat", "attack", "exploit", "breach", "risk",
        }
        self._stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "shall",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "as", "into", "through", "during", "before", "after",
            "and", "but", "or", "nor", "not", "so", "yet", "both",
            "this", "that", "these", "those", "it", "its", "they",
        }

    def calculate_threat_score(self, text: str) -> float:
        """Calculate threat score (0-10) for a piece of text."""
        text_lower = text.lower()
        score = 0.0
        matches = 0

        for keyword, weight in self._threat_keywords.items():
            count = text_lower.count(keyword)
            if count > 0:
                score += weight * min(count, 3)
                matches += count

        # Normalize to 0-10
        if matches > 0:
            score = min(10.0, score / max(1, matches) * min(matches, 5))

        return round(score, 2)

    def analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment (-1 to 1)."""
        words = set(re.findall(r'\w+', text.lower()))
        pos = len(words & self._positive_words)
        neg = len(words & self._negative_words)
        total = pos + neg
        if total == 0:
            return 0.0
        return round((pos - neg) / total, 3)

    def extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """Extract top keywords using TF scoring."""
        words = re.findall(r'[a-zA-Z]{3,}', text.lower())
        words = [w for w in words if w not in self._stop_words]
        counter = Counter(words)
        return [word for word, _ in counter.most_common(top_n)]

    def extract_entities(self, text: str) -> List[str]:
        """Extract named entities (simple pattern-based)."""
        entities = set()
        # IP addresses
        ips = re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', text)
        entities.update(ips)
        # CVE IDs
        cves = re.findall(r'CVE-\d{4}-\d{4,}', text, re.IGNORECASE)
        entities.update(cves)
        # Domains
        domains = re.findall(r'\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:com|org|net|io|gov|edu|mil)\b', text.lower())
        entities.update(domains)
        # Hashes (MD5, SHA1, SHA256)
        hashes = re.findall(r'\b[a-f0-9]{32,64}\b', text.lower())
        entities.update(hashes[:5])
        # Email addresses
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        entities.update(emails)

        return list(entities)[:20]

    def categorize_threat(self, text: str) -> List[str]:
        """Categorize text into threat categories."""
        text_lower = text.lower()
        categories = []

        category_keywords = {
            ThreatCategory.VULNERABILITY.value: ["vulnerability", "cve", "exploit", "patch", "unpatched"],
            ThreatCategory.MALWARE.value: ["malware", "trojan", "virus", "worm", "payload"],
            ThreatCategory.DATA_BREACH.value: ["breach", "leak", "exposed", "stolen", "dump"],
            ThreatCategory.PHISHING.value: ["phishing", "spear-phishing", "credential", "fake login"],
            ThreatCategory.RANSOMWARE.value: ["ransomware", "ransom", "encrypt", "decrypt key"],
            ThreatCategory.DDOS.value: ["ddos", "denial of service", "botnet", "flooding"],
            ThreatCategory.ZERO_DAY.value: ["zero-day", "0day", "unknown vulnerability"],
            ThreatCategory.APT.value: ["apt", "threat actor", "nation state", "campaign"],
        }

        for category, keywords in category_keywords.items():
            if any(kw in text_lower for kw in keywords):
                categories.append(category)

        return categories or [ThreatCategory.GENERAL.value]

# ═══════════════════════════════════════════════════════════════════════════════
# FEED SCRAPER
# ═══════════════════════════════════════════════════════════════════════════════

class FeedScraper:
    """Scrapes OSINT data from various feed sources."""

    def __init__(self):
        self._session_headers = {
            "User-Agent": "NEXUS-OSINT/1.0 (Threat Intelligence Platform)",
            "Accept": "application/json, text/xml, text/html",
        }

    def scrape_feed(self, config: FeedConfig) -> List[OSINTArticle]:
        """Scrape articles from a configured feed."""
        try:
            if config.feed_type == FeedType.RSS_NEWS.value:
                return self._scrape_rss(config)
            elif config.feed_type == FeedType.REDDIT.value:
                return self._scrape_reddit(config)
            elif config.feed_type == FeedType.CVE_DATABASE.value:
                return self._scrape_cve(config)
            elif config.feed_type == FeedType.GITHUB.value:
                return self._scrape_github(config)
            elif config.feed_type == FeedType.SHODAN.value:
                return self._scrape_shodan(config)
            else:
                return self._scrape_generic(config)
        except Exception as e:
            logger.warning(f"Feed scrape failed [{config.name}]: {e}")
            return []

    def _scrape_rss(self, config: FeedConfig) -> List[OSINTArticle]:
        """Scrape RSS/Atom feeds."""
        articles = []
        try:
            import urllib.request
            req = urllib.request.Request(config.url, headers=self._session_headers)
            resp = urllib.request.urlopen(req, timeout=15)
            data = resp.read().decode("utf-8", errors="ignore")

            root = ET.fromstring(data)
            items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')

            for item in items[:config.max_results]:
                title = ""
                content = ""
                link = ""
                pub_date = ""

                # RSS format
                title_el = item.find('title')
                desc_el = item.find('description')
                link_el = item.find('link')
                date_el = item.find('pubDate')

                # Atom format fallback
                if title_el is None:
                    title_el = item.find('{http://www.w3.org/2005/Atom}title')
                if desc_el is None:
                    desc_el = item.find('{http://www.w3.org/2005/Atom}summary')
                if link_el is None:
                    link_el = item.find('{http://www.w3.org/2005/Atom}link')
                    if link_el is not None:
                        link = link_el.get('href', '')
                if date_el is None:
                    date_el = item.find('{http://www.w3.org/2005/Atom}updated')

                if title_el is not None and title_el.text:
                    title = title_el.text.strip()
                if desc_el is not None and desc_el.text:
                    content = desc_el.text.strip()
                if link_el is not None and link_el.text and not link:
                    link = link_el.text.strip()
                if date_el is not None and date_el.text:
                    pub_date = date_el.text.strip()

                if title:
                    article = OSINTArticle(
                        source=config.name,
                        feed_type=config.feed_type,
                        title=title,
                        content=content[:2000],
                        url=link,
                        published_at=pub_date,
                        content_hash=hashlib.md5(
                            (title + content[:200]).encode()
                        ).hexdigest(),
                    )
                    articles.append(article)

        except Exception as e:
            logger.debug(f"RSS scrape error [{config.name}]: {e}")

        return articles

    def _scrape_reddit(self, config: FeedConfig) -> List[OSINTArticle]:
        """Scrape Reddit via JSON API."""
        articles = []
        try:
            import urllib.request
            url = config.url.rstrip("/") + ".json?limit=25"
            req = urllib.request.Request(url, headers={
                **self._session_headers,
                "User-Agent": "NEXUS-OSINT/1.0",
            })
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read())

            posts = data.get("data", {}).get("children", [])
            for post in posts[:config.max_results]:
                post_data = post.get("data", {})
                title = post_data.get("title", "")
                content = post_data.get("selftext", "")[:1000]
                url_val = f"https://reddit.com{post_data.get('permalink', '')}"
                author = post_data.get("author", "")

                if title:
                    article = OSINTArticle(
                        source=f"Reddit/{config.name}",
                        feed_type=FeedType.REDDIT.value,
                        title=title,
                        content=content,
                        url=url_val,
                        author=author,
                        content_hash=hashlib.md5(title.encode()).hexdigest(),
                    )
                    articles.append(article)

        except Exception as e:
            logger.debug(f"Reddit scrape error: {e}")

        return articles

    def _scrape_cve(self, config: FeedConfig) -> List[OSINTArticle]:
        """Scrape CVE database feeds."""
        articles = []
        try:
            import urllib.request
            url = config.url or "https://cve.circl.lu/api/last/20"
            req = urllib.request.Request(url, headers=self._session_headers)
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read())

            if isinstance(data, list):
                for cve in data[:config.max_results]:
                    cve_id = cve.get("id", "UNKNOWN")
                    summary = cve.get("summary", "")
                    cvss = cve.get("cvss", 0)

                    article = OSINTArticle(
                        source="CVE-Database",
                        feed_type=FeedType.CVE_DATABASE.value,
                        title=f"{cve_id}: {summary[:100]}",
                        content=summary,
                        url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                        threat_score=min(10, float(cvss) if cvss else 0),
                        content_hash=hashlib.md5(cve_id.encode()).hexdigest(),
                    )
                    articles.append(article)

        except Exception as e:
            logger.debug(f"CVE scrape error: {e}")

        return articles

    def _scrape_github(self, config: FeedConfig) -> List[OSINTArticle]:
        """Scrape GitHub security advisories."""
        articles = []
        try:
            import urllib.request
            search_terms = "+".join(config.keywords_filter) if config.keywords_filter else "security+vulnerability"
            url = f"https://api.github.com/search/repositories?q={search_terms}&sort=updated&per_page=10"
            req = urllib.request.Request(url, headers={
                **self._session_headers,
                "Accept": "application/vnd.github.v3+json",
            })
            if config.api_key:
                req.add_header("Authorization", f"token {config.api_key}")

            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read())

            for repo in data.get("items", [])[:config.max_results]:
                article = OSINTArticle(
                    source="GitHub",
                    feed_type=FeedType.GITHUB.value,
                    title=f"{repo.get('full_name', '')}: {repo.get('description', '')[:100]}",
                    content=repo.get("description", ""),
                    url=repo.get("html_url", ""),
                    author=repo.get("owner", {}).get("login", ""),
                    content_hash=hashlib.md5(
                        repo.get("full_name", "").encode()
                    ).hexdigest(),
                )
                articles.append(article)

        except Exception as e:
            logger.debug(f"GitHub scrape error: {e}")

        return articles

    def _scrape_shodan(self, config: FeedConfig) -> List[OSINTArticle]:
        """Scrape Shodan exploits feed."""
        articles = []
        if not config.api_key:
            return articles
        try:
            import urllib.request
            url = f"https://exploits.shodan.io/api/search?query=type:exploit&key={config.api_key}"
            req = urllib.request.Request(url, headers=self._session_headers)
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read())

            for exploit in data.get("matches", [])[:config.max_results]:
                article = OSINTArticle(
                    source="Shodan",
                    feed_type=FeedType.SHODAN.value,
                    title=exploit.get("description", "")[:100],
                    content=exploit.get("description", ""),
                    url=exploit.get("source", ""),
                    content_hash=hashlib.md5(
                        str(exploit.get("_id", "")).encode()
                    ).hexdigest(),
                )
                articles.append(article)

        except Exception as e:
            logger.debug(f"Shodan scrape error: {e}")

        return articles

    def _scrape_generic(self, config: FeedConfig) -> List[OSINTArticle]:
        """Generic URL scraper."""
        articles = []
        try:
            import urllib.request
            req = urllib.request.Request(config.url, headers=self._session_headers)
            resp = urllib.request.urlopen(req, timeout=15)
            data = resp.read().decode("utf-8", errors="ignore")

            article = OSINTArticle(
                source=config.name,
                feed_type=FeedType.CUSTOM.value,
                title=f"Raw data from {config.name}",
                content=data[:5000],
                url=config.url,
                content_hash=hashlib.md5(data[:500].encode()).hexdigest(),
            )
            articles.append(article)

        except Exception as e:
            logger.debug(f"Generic scrape error: {e}")

        return articles

# ═══════════════════════════════════════════════════════════════════════════════
# REPORT GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

class ReportGenerator:
    """Generates intelligence reports from analyzed articles."""

    def generate_report(self, articles: List[OSINTArticle],
                         period: str = "last_24h") -> IntelligenceReport:
        """Generate an intelligence report."""
        if not articles:
            return IntelligenceReport(title="No Data", period=period)

        # Aggregate categories
        cat_counts: Dict[str, int] = defaultdict(int)
        for a in articles:
            for cat in a.categories:
                cat_counts[cat] += 1

        # Top threats
        sorted_articles = sorted(articles, key=lambda a: a.threat_score, reverse=True)
        top_threats = [
            {"title": a.title, "score": a.threat_score, "source": a.source}
            for a in sorted_articles[:10]
        ]

        # Trending keywords
        all_keywords = []
        for a in articles:
            all_keywords.extend(a.keywords)
        trending = [kw for kw, _ in Counter(all_keywords).most_common(15)]

        # Sentiment overview
        sentiments = [a.sentiment for a in articles if a.sentiment != 0]
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0

        # Summary
        total = len(articles)
        relevant = sum(1 for a in articles if a.is_relevant)
        avg_threat = sum(a.threat_score for a in articles) / total if total > 0 else 0

        summary = (
            f"Analyzed {total} articles ({relevant} relevant). "
            f"Average threat score: {avg_threat:.1f}/10. "
            f"Sentiment: {'negative' if avg_sentiment < -0.2 else 'neutral' if avg_sentiment < 0.2 else 'positive'}. "
            f"Top categories: {', '.join(list(cat_counts.keys())[:5])}."
        )

        report = IntelligenceReport(
            title=f"NEXUS OSINT Report — {period}",
            period=period,
            summary=summary,
            threat_landscape=dict(cat_counts),
            top_threats=top_threats,
            trending_topics=trending,
            sentiment_overview={
                "average": avg_sentiment,
                "positive_pct": sum(1 for s in sentiments if s > 0.2) / max(1, len(sentiments)),
                "negative_pct": sum(1 for s in sentiments if s < -0.2) / max(1, len(sentiments)),
            },
            article_count=total,
        )

        return report

# ═══════════════════════════════════════════════════════════════════════════════
# OSINT ENGINE — MAIN
# ═══════════════════════════════════════════════════════════════════════════════

class OSINTEngine:
    """
    Real-Time OSINT Engine for NEXUS.
    
    Continuously scrapes intelligence feeds, analyzes content,
    detects threats, tracks targets, and generates reports.
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

        # ──── Paths ────
        self._data_dir = Path(DATA_DIR) / "osint_engine"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # ──── Components ────
        self._scraper = FeedScraper()
        self._analyzer = TextAnalyzer()
        self._reporter = ReportGenerator()

        # ──── Feed configs ────
        self._feeds: List[FeedConfig] = []
        self._setup_default_feeds()

        # ──── Storage ────
        self._articles: deque = deque(maxlen=2000)
        self._alerts: deque = deque(maxlen=500)
        self._reports: deque = deque(maxlen=50)
        self._seen_hashes: Set[str] = set()
        self._tracked_targets: Dict[str, TrackedTarget] = {}

        # ──── Stats ────
        self._stats = OSINTStats()

        # ──── State ────
        self._running = False
        self._daemon_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # ──── Configuration ────
        self._scrape_interval = 300    # 5 minutes
        self._report_interval = 3600   # 1 hour
        self._threat_threshold = 4.0   # Alert if score > this
        self._relevance_threshold = 2.0

        # ──── Load state ────
        self._load_state()

        logger.info(
            f"🕵️ OSINT Engine initialized | "
            f"{len(self._feeds)} feeds configured | "
            f"{self._stats.total_articles_scraped} articles in history"
        )

    def _setup_default_feeds(self):
        """Setup default OSINT feed sources."""
        self._feeds = [
            FeedConfig(name="TheHackerNews", feed_type=FeedType.RSS_NEWS.value,
                       url="https://feeds.feedburner.com/TheHackersNews"),
            FeedConfig(name="BleepingComputer", feed_type=FeedType.RSS_NEWS.value,
                       url="https://www.bleepingcomputer.com/feed/"),
            FeedConfig(name="ThreatPost", feed_type=FeedType.RSS_NEWS.value,
                       url="https://threatpost.com/feed/"),
            FeedConfig(name="KrebsOnSecurity", feed_type=FeedType.RSS_NEWS.value,
                       url="https://krebsonsecurity.com/feed/"),
            FeedConfig(name="DarkReading", feed_type=FeedType.RSS_NEWS.value,
                       url="https://www.darkreading.com/rss.xml"),
            FeedConfig(name="r/netsec", feed_type=FeedType.REDDIT.value,
                       url="https://www.reddit.com/r/netsec"),
            FeedConfig(name="r/cybersecurity", feed_type=FeedType.REDDIT.value,
                       url="https://www.reddit.com/r/cybersecurity"),
            FeedConfig(name="CVE-Recent", feed_type=FeedType.CVE_DATABASE.value,
                       url="https://cve.circl.lu/api/last/20"),
            FeedConfig(name="GitHub-Security", feed_type=FeedType.GITHUB.value,
                       url="", keywords_filter=["security", "exploit", "vulnerability"]),
            FeedConfig(name="Shodan-Exploits", feed_type=FeedType.SHODAN.value,
                       url="", api_key=os.environ.get("SHODAN_API_KEY", ""),
                       enabled=bool(os.environ.get("SHODAN_API_KEY"))),
        ]

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        if self._running:
            return
        self._running = True
        self._daemon_thread = threading.Thread(
            target=self._daemon_loop, daemon=True, name="OSINTEngine",
        )
        self._daemon_thread.start()
        logger.info("🕵️ OSINT Engine daemon started")

    def stop(self):
        self._running = False
        self._save_state()
        if self._daemon_thread and self._daemon_thread.is_alive():
            self._daemon_thread.join(timeout=10)

    # ═══════════════════════════════════════════════════════════════════════════
    # DAEMON LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    def _daemon_loop(self):
        time.sleep(60)
        logger.info("🕵️ OSINT Engine daemon loop active")

        last_scrape = 0.0
        last_report = 0.0

        while self._running:
            try:
                now = time.time()

                if now - last_scrape >= self._scrape_interval:
                    self._scrape_all_feeds()
                    last_scrape = now

                if now - last_report >= self._report_interval:
                    self._generate_periodic_report()
                    last_report = now

                self._check_target_mentions()
                time.sleep(30)

            except Exception as e:
                logger.error(f"🕵️ OSINT loop error: {e}\n{traceback.format_exc()}")
                time.sleep(120)

    # ═══════════════════════════════════════════════════════════════════════════
    # SCRAPING & ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════

    def _scrape_all_feeds(self):
        """Scrape all configured feeds and analyze results."""
        logger.info("🕵️ Scraping all OSINT feeds...")
        total_new = 0

        for feed in self._feeds:
            if not feed.enabled:
                continue

            articles = self._scraper.scrape_feed(feed)
            feed.last_polled = datetime.now().isoformat()

            for article in articles:
                if article.content_hash in self._seen_hashes:
                    continue

                self._seen_hashes.add(article.content_hash)
                self._analyze_article(article)
                self._articles.append(article)
                self._stats.total_articles_scraped += 1
                total_new += 1

                if article.threat_score >= self._threat_threshold:
                    self._generate_alert(article)

        # Keep seen_hashes bounded
        if len(self._seen_hashes) > 10000:
            self._seen_hashes = set(list(self._seen_hashes)[-5000:])

        self._stats.last_scrape_time = datetime.now().isoformat()
        self._stats.total_feeds_active = sum(1 for f in self._feeds if f.enabled)

        logger.info(f"🕵️ Scrape complete: {total_new} new articles")

    def _analyze_article(self, article: OSINTArticle):
        """Run NLP analysis on an article."""
        full_text = f"{article.title} {article.content}"

        article.threat_score = self._analyzer.calculate_threat_score(full_text)
        article.sentiment = self._analyzer.analyze_sentiment(full_text)
        article.keywords = self._analyzer.extract_keywords(full_text)
        article.entities = self._analyzer.extract_entities(full_text)
        article.categories = self._analyzer.categorize_threat(full_text)
        article.is_relevant = article.threat_score >= self._relevance_threshold

        if article.is_relevant:
            self._stats.total_articles_relevant += 1

    def _generate_alert(self, article: OSINTArticle):
        """Generate a threat alert from a high-score article."""
        alert = ThreatAlert(
            priority=AlertPriority.HIGH.value if article.threat_score >= 7 else AlertPriority.MEDIUM.value,
            category=article.categories[0] if article.categories else "general",
            title=f"OSINT Alert: {article.title[:80]}",
            description=f"Threat score {article.threat_score}/10 from {article.source}. {article.content[:200]}",
            source_articles=[article.article_id],
            indicators=article.entities[:10],
        )
        self._alerts.append(alert)
        self._stats.total_alerts_generated += 1

        publish(EventType.SYSTEM_ALERT, {
            "type": "osint_threat",
            "priority": alert.priority,
            "title": alert.title,
            "threat_score": article.threat_score,
        }, source="osint_engine")

    def _generate_periodic_report(self):
        """Generate a periodic intelligence report."""
        recent = [a for a in self._articles
                  if a.is_relevant and self._is_recent(a.scraped_at, hours=24)]

        if not recent:
            return

        report = self._reporter.generate_report(recent, "last_24h")
        self._reports.append(report)
        self._stats.total_reports_generated += 1
        self._stats.last_report_time = datetime.now().isoformat()

        logger.info(f"🕵️ Report generated: {report.title} ({report.article_count} articles)")

    def _check_target_mentions(self):
        """Check recent articles for tracked target mentions."""
        if not self._tracked_targets:
            return

        recent = list(self._articles)[-50:]
        for article in recent:
            text = f"{article.title} {article.content}".lower()
            for tid, target in self._tracked_targets.items():
                names = [target.name.lower()] + [a.lower() for a in target.aliases]
                for name in names:
                    if name in text:
                        target.mentions += 1
                        target.last_seen = datetime.now().isoformat()

    def _is_recent(self, timestamp: str, hours: int = 24) -> bool:
        try:
            t = datetime.fromisoformat(timestamp)
            return (datetime.now() - t) < timedelta(hours=hours)
        except (ValueError, TypeError):
            return False

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def add_target(self, name: str, target_type: str = "general",
                    aliases: List[str] = None, keywords: List[str] = None) -> str:
        """Add a target to track."""
        target = TrackedTarget(
            name=name, target_type=target_type,
            aliases=aliases or [], keywords=keywords or [name],
        )
        self._tracked_targets[target.target_id] = target
        self._stats.total_targets_tracked = len(self._tracked_targets)
        return target.target_id

    def get_latest_articles(self, limit: int = 20, relevant_only: bool = True) -> List[Dict]:
        articles = list(self._articles)
        if relevant_only:
            articles = [a for a in articles if a.is_relevant]
        return [a.to_dict() for a in articles[-limit:]]

    def get_alerts(self, limit: int = 20) -> List[Dict]:
        return [a.to_dict() for a in list(self._alerts)[-limit:]]

    def get_latest_report(self) -> Optional[Dict]:
        return self._reports[-1].to_dict() if self._reports else None

    def get_status(self) -> Dict[str, Any]:
        # Calculate avg threat score
        recent = list(self._articles)[-100:]
        avg_threat = sum(a.threat_score for a in recent) / max(1, len(recent))
        self._stats.avg_threat_score = round(avg_threat, 2)

        # Top categories
        cat_counts: Dict[str, int] = defaultdict(int)
        for a in recent:
            for c in a.categories:
                cat_counts[c] += 1
        self._stats.top_categories = dict(sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)[:5])

        return {
            "running": self._running,
            "stats": self._stats.to_dict(),
            "feeds": [f.to_dict() for f in self._feeds],
            "recent_alerts": [a.to_dict() for a in list(self._alerts)[-3:]],
            "tracked_targets": len(self._tracked_targets),
        }

    def get_summary(self) -> str:
        status = self.get_status()
        lines = [
            f"Running: {status['running']}",
            f"Feeds Active: {self._stats.total_feeds_active}",
            f"Articles Scraped: {self._stats.total_articles_scraped}",
            f"Relevant Articles: {self._stats.total_articles_relevant}",
            f"Alerts Generated: {self._stats.total_alerts_generated}",
            f"Reports Generated: {self._stats.total_reports_generated}",
            f"Avg Threat Score: {self._stats.avg_threat_score:.1f}/10",
            f"Targets Tracked: {self._stats.total_targets_tracked}",
            f"Top Categories: {', '.join(self._stats.top_categories.keys()) if self._stats.top_categories else 'N/A'}",
        ]
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _save_state(self):
        try:
            state = {
                "stats": self._stats.to_dict(),
                "targets": {k: v.to_dict() for k, v in self._tracked_targets.items()},
                "saved_at": datetime.now().isoformat(),
            }
            (self._data_dir / "osint_state.json").write_text(
                json.dumps(state, indent=2, default=str), encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to save OSINT state: {e}")

    def _load_state(self):
        try:
            state_file = self._data_dir / "osint_state.json"
            if state_file.exists():
                data = json.loads(state_file.read_text(encoding="utf-8"))
                for k, v in data.get("stats", {}).items():
                    if hasattr(self._stats, k):
                        setattr(self._stats, k, v)
        except Exception as e:
            logger.warning(f"Could not load OSINT state: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

osint_engine = OSINTEngine()

def get_osint_engine() -> OSINTEngine:
    return osint_engine
