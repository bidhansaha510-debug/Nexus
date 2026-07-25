"""
NEXUS AI - Internet Browser
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Web scraping and content extraction engine for autonomous learning.

Capabilities:
  • Fetch web pages with rate limiting & retries
  • Extract clean text from HTML (strips nav, ads, scripts)
  • Search the web via DuckDuckGo (no API key needed)
  • Follow links for deep research
  • Respect domain whitelist from config
  • Extract structured data (headings, code blocks, lists)
  • Cache pages to avoid redundant fetches

Dependencies:
  pip install requests beautifulsoup4 lxml
"""

import threading
import time
import re
import hashlib
import json
import sqlite3
import socket
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import deque
from urllib.parse import urlparse, urljoin, quote_plus

import sys

from config import DATA_DIR, NEXUS_CONFIG
from utils.logger import get_logger

logger = get_logger("internet_browser")

# ── Optional imports with graceful fallback ──
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    logger.warning("requests not installed — pip install requests")

# PySocks required for Tor SOCKS5 proxy (pip install PySocks)
try:
    import socks
    HAS_SOCKS = True
except ImportError:
    HAS_SOCKS = False
    socks = None

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    logger.warning("beautifulsoup4 not installed — pip install beautifulsoup4 lxml")

# ── DuckDuckGo search (new package name: ddgs, old: duckduckgo_search) ──
DDGS = None
try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        logger.warning("Search not available — pip install ddgs")
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    logger.warning("requests not installed — pip install requests")

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    logger.warning("beautifulsoup4 not installed — pip install beautifulsoup4 lxml")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class WebPage:
    """Extracted web page content"""
    url: str = ""
    title: str = ""
    text: str = ""
    summary: str = ""
    headings: List[str] = field(default_factory=list)
    code_blocks: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    domain: str = ""
    word_count: int = 0
    fetch_time: str = ""
    status_code: int = 0
    success: bool = False
    error: str = ""
    content_hash: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class SearchResult:
    """A single search result"""
    title: str = ""
    url: str = ""
    snippet: str = ""
    domain: str = ""
    position: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class SearchResults:
    """Collection of search results"""
    query: str = ""
    results: List[SearchResult] = field(default_factory=list)
    total_results: int = 0
    search_time: str = ""
    success: bool = False
    error: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["results"] = [r.to_dict() for r in self.results]
        return d

# ═══════════════════════════════════════════════════════════════════════════════
# HTML CLEANER
# ═══════════════════════════════════════════════════════════════════════════════

class HTMLCleaner:
    """Extract clean, readable text from HTML"""

    # Tags to remove entirely (including content)
    REMOVE_TAGS = {
        'script', 'style', 'noscript', 'iframe', 'svg', 'canvas',
        'video', 'audio', 'source', 'picture', 'map', 'object',
        'embed', 'applet', 'form', 'input', 'button', 'select',
        'textarea', 'fieldset', 'legend', 'datalist', 'output',
        'template', 'dialog'
    }

    # Tags that typically contain navigation/ads
    NOISE_TAGS = {
        'nav', 'header', 'footer', 'aside', 'menu', 'menuitem'
    }

    # CSS classes/ids that typically contain noise
    NOISE_PATTERNS = [
        re.compile(r'(nav|menu|sidebar|footer|header|ad|banner|cookie|popup|modal|overlay)', re.I),
        re.compile(r'(social|share|comment|related|recommend|newsletter|subscribe)', re.I),
    ]

    @classmethod
    def clean(cls, html: str, url: str = "") -> WebPage:
        """Extract clean text from HTML"""
        if not HAS_BS4:
            return WebPage(url=url, error="beautifulsoup4 not installed", success=False)

        try:
            soup = BeautifulSoup(html, 'lxml')
        except Exception:
            try:
                soup = BeautifulSoup(html, 'html.parser')
            except Exception as e:
                return WebPage(url=url, error=f"Parse error: {e}", success=False)

        page = WebPage(url=url, fetch_time=datetime.now().isoformat())

        # ── Extract title ──
        title_tag = soup.find('title')
        if title_tag:
            page.title = title_tag.get_text(strip=True)

        # ── Extract headings ──
        for level in ['h1', 'h2', 'h3']:
            for heading in soup.find_all(level):
                text = heading.get_text(strip=True)
                if text and len(text) > 2:
                    page.headings.append(text)

        # ── Extract code blocks ──
        for code_tag in soup.find_all(['code', 'pre']):
            code_text = code_tag.get_text(strip=True)
            if code_text and len(code_text) > 10:
                page.code_blocks.append(code_text[:2000])

        # ── Remove noise tags ──
        for tag_name in cls.REMOVE_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        for tag_name in cls.NOISE_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # Remove elements with noisy class/id names
        for tag in soup.find_all(True):
            tag_classes = ' '.join(tag.get('class', []))
            tag_id = tag.get('id', '')
            combined = f"{tag_classes} {tag_id}"
            for pattern in cls.NOISE_PATTERNS:
                if pattern.search(combined):
                    tag.decompose()
                    break

        # ── Extract main content ──
        # Try to find article or main content area
        main_content = (
            soup.find('article') or
            soup.find('main') or
            soup.find('div', {'role': 'main'}) or
            soup.find('div', class_=re.compile(r'(content|article|post|entry|body)', re.I)) or
            soup.find('body') or
            soup
        )

        # Get text
        text = main_content.get_text(separator='\n', strip=True)

        # ── Clean up text ──
        # Remove excessive whitespace
        lines = []
        for line in text.split('\n'):
            line = line.strip()
            if line and len(line) > 1:
                lines.append(line)

        # Remove duplicate consecutive lines
        cleaned_lines = []
        prev_line = ""
        for line in lines:
            if line != prev_line:
                cleaned_lines.append(line)
                prev_line = line

        page.text = '\n'.join(cleaned_lines)
        page.word_count = len(page.text.split())

        # ── Extract links ──
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if href.startswith('http'):
                page.links.append(href)
            elif href.startswith('/') and url:
                page.links.append(urljoin(url, href))

        # Remove duplicate links
        page.links = list(dict.fromkeys(page.links))[:50]

        # ── Domain ──
        if url:
            parsed = urlparse(url)
            page.domain = parsed.netloc

        # ── Content hash ──
        page.content_hash = hashlib.sha256(
            page.text.encode()
        ).hexdigest()[:16]

        page.success = True
        return page

    @classmethod
    def extract_summary(cls, text: str, max_sentences: int = 5) -> str:
        """Extract first N meaningful sentences as summary"""
        sentences = re.split(r'[.!?]+', text)
        meaningful = []
        for s in sentences:
            s = s.strip()
            if len(s) > 30 and len(s.split()) > 5:
                meaningful.append(s + '.')
                if len(meaningful) >= max_sentences:
                    break
        return ' '.join(meaningful)

# ═══════════════════════════════════════════════════════════════════════════════
# INTERNET BROWSER
# ═══════════════════════════════════════════════════════════════════════════════

class InternetBrowser:
    """
    Web browsing engine with rate limiting, caching, and content extraction.
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
        self._timeout = self._config.browsing_timeout
        self._allowed_domains = set(self._config.allowed_domains)
        self._tor_enabled = getattr(self._config, "tor_enabled", False)
        self._allow_onion_when_tor = getattr(self._config, "allow_onion_when_tor", True)
        self._tor_exe_path = getattr(self._config, "tor_exe_path", "")
        self._tor_process: Optional[subprocess.Popen] = None
        self._tor_available = False  # True only after successful SOCKS probe
        self._tor_fail_backoff_until = 0.0  # timestamp; skip onion attempts until this
        self._tor_backoff_seconds = 300  # 5 minutes between retries
        if self._tor_enabled:
            self._timeout = max(self._timeout, 60)  # Tor is slower; use at least 60s

        # ──── Rate Limiting ────
        self._request_history: deque = deque(maxlen=100)
        self._min_request_interval = 1.0    # seconds between requests
        self._last_request_time = 0.0
        self._requests_per_minute_limit = 6000  # High limit for autonomous browsing
        self._rate_lock = threading.Lock()

        # ──── Session ────
        self._session: Optional[requests.Session] = None
        if HAS_REQUESTS:
            self._session = requests.Session()
            self._session.headers.update({
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
            })
            # Tor proxy: route all traffic through Tor (enables clearnet + .onion)
            if self._tor_enabled and HAS_SOCKS:
                proxy_url = getattr(self._config, "tor_proxy_url", "socks5h://127.0.0.1:9050")
                # Check if Tor SOCKS proxy is reachable; auto-launch if not
                if not self._probe_tor_socks():
                    logger.warning("Tor SOCKS proxy not reachable, attempting auto-launch...")
                    self._try_launch_tor()
                    # Poll for Tor bootstrap (up to 15s in 3s intervals)
                    for _attempt in range(5):
                        time.sleep(3)
                        if self._probe_tor_socks():
                            break
                    if not self._probe_tor_socks():
                        logger.warning(
                            "Tor still not reachable after launch attempt. "
                            "Onion features disabled until Tor is running."
                        )
                        self._tor_available = False
                    else:
                        self._tor_available = True
                else:
                    self._tor_available = True

                if self._tor_available:
                    self._session.proxies = {
                        "http": proxy_url,
                        "https": proxy_url,
                    }
                    logger.info(f"Tor proxy enabled: {proxy_url}")
                else:
                    logger.warning(
                        "Tor proxy configured but not reachable — "
                        "clearnet browsing will work, onion features disabled"
                    )
            elif self._tor_enabled and not HAS_SOCKS:
                logger.warning("Tor enabled but PySocks not installed — pip install PySocks")

        # ──── Cache ────
        self._cache_dir = DATA_DIR / "knowledge" / "web_cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_db_path = self._cache_dir / "cache.db"
        self._cache_lock = threading.Lock()
        self._cache_ttl_hours = 24
        self._init_cache_db()

        # ──── Statistics ────
        self._total_requests = 0
        self._total_successful = 0
        self._total_failed = 0
        self._total_cached = 0
        self._total_bytes_downloaded = 0
        self._pages_fetched: deque = deque(maxlen=200)

        logger.info("InternetBrowser initialized (tor_available=%s)", self._tor_available)

    # ═══════════════════════════════════════════════════════════════════════════
    # TOR HELPERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _probe_tor_socks(self) -> bool:
        """Check if the Tor SOCKS proxy port is listening."""
        proxy_url = getattr(self._config, "tor_proxy_url", "socks5h://127.0.0.1:9050")
        try:
            # Parse host:port from socks5h://host:port
            parts = proxy_url.split("://")[-1].split(":")
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 9050
        except Exception:
            host, port = "127.0.0.1", 9050
        try:
            sock = socket.create_connection((host, port), timeout=3)
            sock.close()
            return True
        except (ConnectionRefusedError, OSError, socket.timeout):
            return False

    def _try_launch_tor(self):
        """Try to auto-start the Tor process from the configured exe path."""
        exe_path = self._tor_exe_path
        if not exe_path:
            logger.debug("No tor_exe_path configured, cannot auto-launch Tor")
            return
        import os
        if not os.path.isfile(exe_path):
            logger.warning(f"Tor executable not found at: {exe_path}")
            return
        try:
            self._tor_process = subprocess.Popen(
                [exe_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            logger.info(f"Launched Tor process (PID {self._tor_process.pid})")
        except Exception as e:
            logger.error(f"Failed to launch Tor: {e}")

    def _ensure_tor_available(self) -> bool:
        """
        Check if Tor is available, respecting backoff.
        Returns True if Tor SOCKS proxy is reachable.
        """
        if not self._tor_enabled or not HAS_SOCKS:
            return False
        if self._tor_available:
            return True
        # Backoff: don't re-probe until cooldown expires
        now = time.time()
        if now < self._tor_fail_backoff_until:
            return False
        # Try probing / re-launching
        if self._probe_tor_socks():
            self._tor_available = True
            # Re-attach proxy to session
            proxy_url = getattr(self._config, "tor_proxy_url", "socks5h://127.0.0.1:9050")
            if self._session:
                self._session.proxies = {"http": proxy_url, "https": proxy_url}
            logger.info("Tor became available, re-enabled onion features")
            return True
        # Still down — try launch once more
        self._try_launch_tor()
        time.sleep(3)
        if self._probe_tor_socks():
            self._tor_available = True
            proxy_url = getattr(self._config, "tor_proxy_url", "socks5h://127.0.0.1:9050")
            if self._session:
                self._session.proxies = {"http": proxy_url, "https": proxy_url}
            logger.info("Tor launched successfully, onion features enabled")
            return True
        # Failed — set backoff
        self._tor_fail_backoff_until = now + self._tor_backoff_seconds
        logger.debug(
            f"Tor still unavailable, backoff for {self._tor_backoff_seconds}s"
        )
        return False

    # ═══════════════════════════════════════════════════════════════════════════
    # CACHE
    # ═══════════════════════════════════════════════════════════════════════════

    def _init_cache_db(self):
        with self._cache_lock:
            try:
                conn = sqlite3.connect(str(self._cache_db_path))
                cursor = conn.cursor()
                cursor.executescript("""
                    CREATE TABLE IF NOT EXISTS page_cache (
                        url_hash TEXT PRIMARY KEY,
                        url TEXT NOT NULL,
                        html TEXT,
                        title TEXT,
                        text TEXT,
                        word_count INTEGER,
                        fetched_at TEXT,
                        expires_at TEXT,
                        content_hash TEXT
                    );

                    CREATE INDEX IF NOT EXISTS idx_cache_url
                        ON page_cache(url);
                    CREATE INDEX IF NOT EXISTS idx_cache_expires
                        ON page_cache(expires_at);
                """)
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Cache DB init error: {e}")

    def _get_cached(self, url: str) -> Optional[WebPage]:
        """Get a cached page if still valid"""
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        with self._cache_lock:
            try:
                conn = sqlite3.connect(str(self._cache_db_path))
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT * FROM page_cache 
                       WHERE url_hash = ? AND expires_at > ?""",
                    (url_hash, datetime.now().isoformat())
                )
                row = cursor.fetchone()
                conn.close()

                if row:
                    self._total_cached += 1
                    return WebPage(
                        url=row["url"],
                        title=row["title"] or "",
                        text=row["text"] or "",
                        word_count=row["word_count"] or 0,
                        fetch_time=row["fetched_at"] or "",
                        content_hash=row["content_hash"] or "",
                        success=True
                    )
            except Exception as e:
                logger.debug(f"Cache read error: {e}")

        return None

    def _cache_page(self, url: str, page: WebPage, html: str = ""):
        """Cache a fetched page"""
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        expires = (
            datetime.now() + timedelta(hours=self._cache_ttl_hours)
        ).isoformat()

        with self._cache_lock:
            try:
                conn = sqlite3.connect(str(self._cache_db_path))
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT OR REPLACE INTO page_cache
                       (url_hash, url, html, title, text, word_count,
                        fetched_at, expires_at, content_hash)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        url_hash, url, html[:100000],
                        page.title, page.text[:50000],
                        page.word_count, page.fetch_time,
                        expires, page.content_hash
                    )
                )
                conn.commit()
                conn.close()
            except Exception as e:
                logger.debug(f"Cache write error: {e}")

    def clear_cache(self):
        """Clear expired cache entries"""
        with self._cache_lock:
            try:
                conn = sqlite3.connect(str(self._cache_db_path))
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM page_cache WHERE expires_at < ?",
                    (datetime.now().isoformat(),)
                )
                deleted = cursor.rowcount
                conn.commit()
                conn.close()
                if deleted > 0:
                    logger.debug(f"Cleared {deleted} expired cache entries")
            except Exception as e:
                logger.debug(f"Cache clear error: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # RATE LIMITING
    # ═══════════════════════════════════════════════════════════════════════════

    def _wait_for_rate_limit(self):
        """Wait if needed to respect rate limits"""
        with self._rate_lock:
            now = time.time()

            # Enforce minimum interval
            elapsed = now - self._last_request_time
            if elapsed < self._min_request_interval:
                time.sleep(self._min_request_interval - elapsed)

            # Check requests per minute
            one_minute_ago = now - 60
            recent = sum(
                1 for t in self._request_history if t > one_minute_ago
            )
            if recent >= self._requests_per_minute_limit:
                wait_time = 60 - (now - self._request_history[0])
                if wait_time > 0:
                    logger.debug(f"Rate limited, waiting {wait_time:.1f}s")
                    time.sleep(wait_time)

            self._last_request_time = time.time()
            self._request_history.append(time.time())

    # ═══════════════════════════════════════════════════════════════════════════
    # DOMAIN CHECKING
    # ═══════════════════════════════════════════════════════════════════════════

    def is_domain_allowed(self, url: str) -> bool:
        """Check if URL domain is in whitelist. When Tor is enabled, .onion is allowed."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # When Tor is on, allow any .onion for dark web learning
            if self._tor_enabled and self._allow_onion_when_tor and domain.endswith(".onion"):
                return True

            if not self._allowed_domains:
                return True  # No whitelist = allow all

            for allowed in self._allowed_domains:
                if domain == allowed or domain.endswith('.' + allowed):
                    return True

            return False
        except Exception:
            return False

    def add_allowed_domain(self, domain: str):
        """Add a domain to the whitelist"""
        self._allowed_domains.add(domain.lower())
        logger.info(f"Added allowed domain: {domain}")

    # ═══════════════════════════════════════════════════════════════════════════
    # FETCHING
    # ═══════════════════════════════════════════════════════════════════════════

    def fetch(self, url: str, use_cache: bool = True) -> WebPage:
        """
        Fetch a URL and return cleaned content.
        
        Args:
            url: URL to fetch
            use_cache: Whether to use cached version if available
            
        Returns:
            WebPage with extracted content
        """
        if not HAS_REQUESTS or not HAS_BS4:
            return WebPage(
                url=url,
                error="Required packages not installed (requests, beautifulsoup4)",
                success=False
            )

        # ── Check domain whitelist ──
        if not self.is_domain_allowed(url):
            return WebPage(
                url=url,
                error=f"Domain not in allowed list: {urlparse(url).netloc}",
                success=False
            )

        # ── Check cache ──
        if use_cache:
            cached = self._get_cached(url)
            if cached:
                logger.debug(f"Cache hit: {url}")
                return cached

        # ── Rate limit ──
        self._wait_for_rate_limit()

        # ── Fetch ──
        self._total_requests += 1

        try:
            response = self._session.get(
                url,
                timeout=self._timeout,
                allow_redirects=True
            )
            response.raise_for_status()

            self._total_bytes_downloaded += len(response.content)

            # ── Parse ──
            page = HTMLCleaner.clean(response.text, url)
            page.status_code = response.status_code
            page.summary = HTMLCleaner.extract_summary(page.text)
            page.domain = urlparse(url).netloc

            if page.success:
                self._total_successful += 1
                self._cache_page(url, page, response.text)
                self._pages_fetched.append({
                    "url": url,
                    "title": page.title[:100],
                    "words": page.word_count,
                    "time": datetime.now().isoformat()
                })
            else:
                self._total_failed += 1

            logger.debug(
                f"Fetched: {url} ({page.word_count} words, "
                f"{response.status_code})"
            )

            return page

        except requests.exceptions.Timeout:
            self._total_failed += 1
            return WebPage(url=url, error="Request timed out", success=False)
        except requests.exceptions.ConnectionError:
            self._total_failed += 1
            return WebPage(url=url, error="Connection error", success=False)
        except requests.exceptions.HTTPError as e:
            self._total_failed += 1
            return WebPage(
                url=url,
                error=f"HTTP error: {e.response.status_code}",
                status_code=e.response.status_code,
                success=False
            )
        except Exception as e:
            self._total_failed += 1
            return WebPage(url=url, error=f"Fetch error: {str(e)}", success=False)

    def fetch_multiple(
        self, urls: List[str], max_pages: int = 10
    ) -> List[WebPage]:
        """Fetch multiple URLs with rate limiting"""
        pages = []
        for url in urls[:max_pages]:
            page = self.fetch(url)
            pages.append(page)
            if not page.success:
                continue
        return pages

    # DuckDuckGo .onion base URL for discovering random .onion sites via search
    _DDG_ONION_BASE = "http://duckduckgogg42xjoc72x3sjasowoarfbgcmvfimaftt6twagswzczad.onion/"

    def _discover_onion_urls_from_search(self, query: str, max_links: int = 30) -> List[str]:
        """
        Fetch DuckDuckGo .onion search page for query, parse HTML, return list of .onion URLs.
        Used to discover random .onion sites for learning.
        """
        if not self._tor_enabled or not HAS_REQUESTS or not HAS_BS4:
            return []
        # Check Tor availability with backoff to avoid log spam
        if not self._ensure_tor_available():
            return []
        search_url = self._DDG_ONION_BASE + "?q=" + quote_plus(query)
        try:
            self._wait_for_rate_limit()
            resp = self._session.get(search_url, timeout=self._timeout, allow_redirects=True)
            resp.raise_for_status()
        except Exception as e:
            logger.debug(f"Onion search fetch failed: {e}")
            # Mark Tor as unavailable so we don't retry immediately
            self._tor_available = False
            self._tor_fail_backoff_until = time.time() + self._tor_backoff_seconds
            return []
        onion_urls = []
        try:
            soup = BeautifulSoup(resp.text, "lxml") if HAS_BS4 else None
            if not soup:
                return []
            for a in soup.find_all("a", href=True):
                href = (a.get("href") or "").strip()
                if ".onion" in href and href.startswith("http"):
                    # Normalize: take the first http(s) .onion URL
                    if href not in onion_urls:
                        onion_urls.append(href)
                if len(onion_urls) >= max_links:
                    break
        except Exception as e:
            logger.debug(f"Onion link parse error: {e}")
        return onion_urls[:max_links]

    def _random_search_query(self) -> str:
        """Generate a fully random search query (letters and/or digits) so discovered .onion sites are random."""
        import random
        import string
        # Random length 2-5, mix of lowercase letters and digits so every run gets different results
        length = random.randint(2, 5)
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def discover_and_fetch_random_onion(self, query: Optional[str] = None) -> Optional[WebPage]:
        """
        Discover .onion sites by searching DuckDuckGo .onion with a random query,
        pick one result at random, fetch it. Sites are fully random (no fixed topic list).
        """
        if not self._tor_enabled or not HAS_REQUESTS:
            return None
        if not self._ensure_tor_available():
            return None
        import random
        if not query or not query.strip():
            query = self._random_search_query()
        urls = self._discover_onion_urls_from_search(query, max_links=25)
        if not urls:
            # Fallback: fetch from default_onion_urls
            return self.fetch_random_onion_page()
        url = random.choice(urls)
        page = self.fetch(url, use_cache=False)
        if page.success:
            logger.info(
                f"Random .onion fetch: {urlparse(url).netloc[:24]}... ({page.word_count} words)"
            )
        return page if page.success else None

    def fetch_random_onion_page(self) -> Optional[WebPage]:
        """
        When Tor is enabled, fetch one random page from default_onion_urls
        for dark web learning. Returns None if Tor off or fetch fails.
        """
        if not self._tor_enabled or not HAS_REQUESTS:
            return None
        if not self._ensure_tor_available():
            return None
        urls = getattr(self._config, "default_onion_urls", [])
        if not urls:
            return None
        import random
        url = random.choice(urls)
        page = self.fetch(url, use_cache=False)
        if page.success:
            logger.info(f"Dark web fetch: {urlparse(url).netloc[:20]}... ({page.word_count} words)")
        return page if page.success else None

    def is_tor_enabled(self) -> bool:
        """Whether traffic is routed through Tor (and .onion is allowed)."""
        return getattr(self, "_tor_enabled", False)

    # ═══════════════════════════════════════════════════════════════════════════
    # SEARCH
    # ═══════════════════════════════════════════════════════════════════════════

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        Perform a web search using DuckDuckGo.
        Uses the `ddgs` package (formerly `duckduckgo_search`).
        """
        if DDGS is None:
            logger.warning("Search unavailable — pip install ddgs")
            return [{
                "title": f"Search Error: {query}",
                "url": "",
                "snippet": "Search package not installed. Run: pip install ddgs"
            }]

        results = []

        try:
            with DDGS(timeout=20) as ddgs:
                # Try new API first (ddgs package: positional `query`)
                # then fall back to old API (duckduckgo_search: `keywords=`)
                try:
                    search_gen = ddgs.text(query, max_results=max_results)
                except TypeError:
                    search_gen = ddgs.text(keywords=query, max_results=max_results)

                if search_gen:
                    for r in search_gen:
                        if len(results) >= max_results:
                            break

                        item = {
                            "title": r.get("title", ""),
                            "url": r.get("href", r.get("url", "")),
                            "snippet": r.get("body", r.get("snippet", ""))
                        }
                        results.append(item)

        except Exception as e:
            logger.warning(f"Search failed for '{query}': {e}")
            return [{
                "title": f"Search Error: {query}",
                "url": "",
                "snippet": "Unable to connect to search engine. Please check internet connection."
            }]

        return results

    def search_and_fetch(
        self, query: str, max_results: int = 3, max_pages: int = 3
    ) -> Tuple[SearchResults, List[WebPage]]:
        """
        Search and fetch the top results.
        Only fetches pages from allowed domains.
        """
        search_results = self.search(query, max_results)

        pages = []
        if search_results.success:
            for result in search_results.results[:max_pages]:
                if self.is_domain_allowed(result.url):
                    page = self.fetch(result.url)
                    if page.success:
                        pages.append(page)

        return search_results, pages

    # ═══════════════════════════════════════════════════════════════════════════
    # WIKIPEDIA SHORTCUT
    # ═══════════════════════════════════════════════════════════════════════════

    def fetch_wikipedia(self, topic: str) -> WebPage:
        """
        Fetch a Wikipedia article using the API for clean text.
        No HTML parsing needed.
        """
        if not HAS_REQUESTS:
            return WebPage(
                url="",
                error="requests not installed",
                success=False
            )

        try:
            self._wait_for_rate_limit()

            api_url = "https://en.wikipedia.org/api/rest_v1/page/summary/"
            encoded_topic = quote_plus(topic.replace(' ', '_'))
            url = f"{api_url}{encoded_topic}"

            response = self._session.get(url, timeout=self._timeout)

            if response.status_code == 404:
                return WebPage(
                    url=url,
                    error=f"Wikipedia article not found: {topic}",
                    success=False
                )

            response.raise_for_status()
            data = response.json()

            page = WebPage(
                url=data.get("content_urls", {}).get("desktop", {}).get("page", url),
                title=data.get("title", topic),
                text=data.get("extract", ""),
                summary=data.get("description", ""),
                domain="wikipedia.org",
                word_count=len(data.get("extract", "").split()),
                fetch_time=datetime.now().isoformat(),
                success=True,
                status_code=200,
                content_hash=hashlib.sha256(
                    data.get("extract", "").encode()
                ).hexdigest()[:16]
            )

            self._total_successful += 1
            self._total_requests += 1

            # Also try to get the full article
            if page.word_count < 100:
                full_page = self._fetch_wikipedia_full(topic)
                if full_page and full_page.success:
                    page.text = full_page.text
                    page.word_count = full_page.word_count

            logger.debug(
                f"Wikipedia: {topic} ({page.word_count} words)"
            )
            return page

        except Exception as e:
            self._total_failed += 1
            self._total_requests += 1
            return WebPage(
                url="",
                error=f"Wikipedia error: {str(e)}",
                success=False
            )

    def _fetch_wikipedia_full(self, topic: str) -> Optional[WebPage]:
        """Fetch full Wikipedia article text via API"""
        try:
            self._wait_for_rate_limit()

            api_url = (
                f"https://en.wikipedia.org/w/api.php?"
                f"action=query&titles={quote_plus(topic)}"
                f"&prop=extracts&explaintext=1&format=json"
            )
            response = self._session.get(api_url, timeout=self._timeout)
            response.raise_for_status()
            data = response.json()

            pages = data.get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                if page_id == "-1":
                    return None
                extract = page_data.get("extract", "")
                if extract:
                    return WebPage(
                        url=f"https://en.wikipedia.org/wiki/{quote_plus(topic)}",
                        title=page_data.get("title", topic),
                        text=extract[:20000],
                        word_count=len(extract.split()),
                        success=True
                    )
        except Exception:
            pass

    def fetch_random_wikipedia(self) -> WebPage:
        """
        Fetch a random Wikipedia article using the API.
        Great for serendipitous discovery.
        """
        if not HAS_REQUESTS:
            return WebPage(
                url="",
                error="requests not installed",
                success=False
            )

        try:
            self._wait_for_rate_limit()

            # API endpoint for random summary
            api_url = "https://en.wikipedia.org/api/rest_v1/page/random/summary"

            response = self._session.get(api_url, timeout=self._timeout)
            response.raise_for_status()
            data = response.json()

            title = data.get("title", "Random Article")
            url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
            
            # If we got a valid URL, treat it as a normal fetch
            # But use the data we already have if possible
            if url:
                page = WebPage(
                    url=url,
                    title=title,
                    text=data.get("extract", ""),
                    summary=data.get("description", ""),
                    domain="wikipedia.org",
                    word_count=len(data.get("extract", "").split()),
                    fetch_time=datetime.now().isoformat(),
                    success=True,
                    status_code=200,
                    content_hash=hashlib.sha256(
                        data.get("extract", "").encode()
                    ).hexdigest()[:16]
                )

                # Fetch full content if summary is too short
                if page.word_count < 100:
                    full_page = self._fetch_wikipedia_full(title)
                    if full_page and full_page.success:
                        page.text = full_page.text
                        page.word_count = full_page.word_count

                self._total_successful += 1
                self._total_requests += 1

                logger.debug(f"Random Wikipedia: {title}")
                return page
            else:
                 return WebPage(
                    url="",
                    error="No URL in random response",
                    success=False
                )

        except Exception as e:
            self._total_failed += 1
            self._total_requests += 1
            return WebPage(
                url="",
                error=f"Random Wikipedia error: {str(e)}",
                success=False
            )
        return None

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def get_recent_pages(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recently fetched pages"""
        return list(self._pages_fetched)[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_requests": self._total_requests,
            "total_successful": self._total_successful,
            "total_failed": self._total_failed,
            "total_cached": self._total_cached,
            "total_bytes_downloaded": self._total_bytes_downloaded,
            "bytes_downloaded_mb": round(
                self._total_bytes_downloaded / (1024 * 1024), 2
            ),
            "allowed_domains": len(self._allowed_domains),
            "cache_ttl_hours": self._cache_ttl_hours,
            "has_requests": HAS_REQUESTS,
            "has_bs4": HAS_BS4,
            "pages_fetched_recently": len(self._pages_fetched)
        }

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

internet_browser = InternetBrowser()

if __name__ == "__main__":
    browser = InternetBrowser()

    # Test Wikipedia
    print("═══ Wikipedia Test ═══")
    page = browser.fetch_wikipedia("Artificial intelligence")
    if page.success:
        print(f"Title: {page.title}")
        print(f"Words: {page.word_count}")
        print(f"Text preview: {page.text[:300]}...")
    else:
        print(f"Error: {page.error}")

    # Test search
    print("\n═══ Search Test ═══")
    results = browser.search("Python programming tutorials", max_results=5)
    if results.success:
        for r in results.results:
            print(f"  [{r.position}] {r.title}")
            print(f"      {r.url}")
    else:
        print(f"Error: {results.error}")

    print(f"\nStats: {json.dumps(browser.get_stats(), indent=2)}")