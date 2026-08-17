"""
NEXUS AI - Internet Agent
═══════════════════════════════════════════════════════════════════════════════
Autonomous internet interaction capabilities powered by local Ollama.

This agent enables NEXUS to:
  • Browse websites and extract information
  • Make REST API calls to external services
  • Download files from the internet
  • Fill and submit web forms
  • Authenticate with web services
  • Execute arbitrary web actions

All actions are decided by Ollama (local) and recorded in ActionMemory
so Groq can report what actions were taken.
═══════════════════════════════════════════════════════════════════════════════
"""

import threading
import time
import json
import hashlib
import re
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum, auto
from urllib.parse import urlparse, urljoin

import sys

from config import DATA_DIR, NEXUS_CONFIG
from utils.logger import get_logger
from core.event_bus import EventType, publish, subscribe, Event

logger = get_logger("internet_agent")

# Try to import optional dependencies
try:
    import requests
    from bs4 import BeautifulSoup
    HAS_WEB_DEPS = True
except ImportError:
    HAS_WEB_DEPS = False
    logger.warning("requests/beautifulsoup4 not installed - internet actions limited")

try:
    from ddgs import DDGS
    HAS_DDG_SEARCH = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        HAS_DDG_SEARCH = True
    except ImportError:
        HAS_DDG_SEARCH = False
        logger.warning("ddgs not installed - search will use HTML scraping fallback. Install with: pip install ddgs")

# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS AND DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class InternetActionType(Enum):
    """Types of internet actions the agent can perform"""
    BROWSE = "browse"                # Navigate to URL and extract content
    SCRAPE = "scrape"                # Extract specific data from a page
    API_CALL = "api_call"            # REST API request
    DOWNLOAD = "download"            # Download a file
    FORM_SUBMIT = "form_submit"      # Fill and submit a form
    SEARCH = "search"                # Web search
    AUTHENTICATE = "authenticate"    # Login to a service
    CHECK_STATUS = "check_status"    # Check if URL is accessible
    BROWSER_INTERACT = "browser_interact"  # Full browser interaction (click, type, scroll, etc.)

class ActionResult(Enum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"
    RATE_LIMITED = "rate_limited"

class RiskLevel(Enum):
    SAFE = "safe"           # Read-only, no side effects
    LOW = "low"             # Minor side effects (cookies)
    MODERATE = "moderate"   # May change state (form submit)
    HIGH = "high"           # Significant changes (API POST, auth)
    CRITICAL = "critical"   # Potentially dangerous actions

@dataclass
class InternetAction:
    """Represents a single internet action"""
    action_id: str = ""
    action_type: InternetActionType = InternetActionType.BROWSE
    url: str = ""
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, Any] = field(default_factory=dict)
    data: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 30
    risk_level: RiskLevel = RiskLevel.SAFE
    requires_auth: bool = False
    description: str = ""
    created_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "url": self.url,
            "method": self.method,
            "risk_level": self.risk_level.value,
            "description": self.description,
            "created_at": self.created_at,
        }

@dataclass
class InternetActionResult:
    """Result of an internet action"""
    action_id: str = ""
    success: bool = False
    result_type: ActionResult = ActionResult.FAILURE
    status_code: int = 0
    content: str = ""
    content_type: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    data: Any = None
    extracted: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    duration_seconds: float = 0.0
    bytes_received: int = 0
    llm_decision: str = ""  # Ollama's reasoning for this action
    timestamp: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "success": self.success,
            "result_type": self.result_type.value,
            "status_code": self.status_code,
            "content_preview": self.content[:500] if self.content else "",
            "error": self.error,
            "duration_seconds": round(self.duration_seconds, 2),
            "bytes_received": self.bytes_received,
            "llm_decision": self.llm_decision[:200] if self.llm_decision else "",
            "timestamp": self.timestamp,
        }

@dataclass
class InternetAgentStats:
    """Statistics for the internet agent"""
    total_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    total_bytes_downloaded: int = 0
    total_requests: int = 0
    avg_response_time: float = 0.0
    actions_by_type: Dict[str, int] = field(default_factory=dict)
    domains_visited: set = field(default_factory=set)
    last_action_time: str = ""

# ═══════════════════════════════════════════════════════════════════════════════
# INTERNET AGENT
# ═══════════════════════════════════════════════════════════════════════════════

class InternetAgent:
    """
    Autonomous internet agent powered by local Ollama.
    
    This agent can:
    1. Browse websites and extract information
    2. Make API calls to external services
    3. Download files
    4. Submit forms
    5. Perform web searches
    
    All actions are:
    - Decided by Ollama (local LLM)
    - Recorded in ActionMemory for Groq to report
    - Rate-limited for safety
    - Configurable risk levels
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
        self._data_dir = DATA_DIR / "internet_actions"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        
        self._download_dir = DATA_DIR / "downloads"
        self._download_dir.mkdir(parents=True, exist_ok=True)
        
        # ──── State ────
        self._running = False
        self._ollama = None
        self._action_memory = None
        
        # ──── Rate Limiting (high limits for unrestricted autonomous browsing) ────
        self._request_timestamps: List[float] = []
        self._max_requests_per_minute = 300
        self._domain_timestamps: Dict[str, List[float]] = {}
        self._max_requests_per_domain_per_minute = 60
        
        # ──── Action Queue ────
        self._action_queue: List[InternetAction] = []
        self._active_action: Optional[InternetAction] = None
        self._action_history: List[InternetActionResult] = []
        self._max_history = 100
        
        # ──── Session ────
        self._session: Optional[requests.Session] = None
        self._cookies: Dict[str, Any] = {}
        self._auth_tokens: Dict[str, str] = {}
        
        # ──── Safety (minimal — full autonomous control) ────
        self._blocked_domains: set = set()
        self._allowed_domains: Optional[set] = None  # None = all allowed
        # No approval required for any risk level — full autonomy
        self._require_approval_above: RiskLevel = RiskLevel.CRITICAL
        
        # ──── Stats ────
        self._stats = InternetAgentStats()
        
        # ──── Background Threads ────
        self._worker_thread: Optional[threading.Thread] = None
        self._autonomous_thread: Optional[threading.Thread] = None
        self._autonomous_interval = 30  # seconds between autonomous decisions (fast loop)
        
        # ──── Load persisted data ────
        self._load_state()
        
        logger.info("🌐 Internet Agent initialized")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def start(self):
        """Start the internet agent"""
        if self._running:
            return
        
        if not HAS_WEB_DEPS:
            logger.error("Cannot start Internet Agent - missing requests/beautifulsoup4")
            return
        
        self._running = True
        
        # Create session
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'NEXUS-AI/1.0 (Autonomous Agent)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        
        # Load Ollama
        try:
            from llm.llama_interface import llm
            self._ollama = llm
        except ImportError:
            logger.warning("Ollama not available for internet agent decision-making")
        
        # Load Action Memory
        try:
            from core.action_memory import action_memory
            self._action_memory = action_memory
        except ImportError:
            logger.warning("ActionMemory not available")
        
        # Start worker thread
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            daemon=True,
            name="InternetAgent"
        )
        self._worker_thread.start()
        
        # Start autonomous decision loop
        self._autonomous_thread = threading.Thread(
            target=self._autonomous_decision_loop,
            daemon=True,
            name="InternetAgent-Autonomous"
        )
        self._autonomous_thread.start()
        
        # Subscribe to events
        subscribe(EventType.AUTONOMY_ACTION_TAKEN, self._on_autonomy_action)
        
        logger.info("🌐 Internet Agent ACTIVE - autonomous web actions + decision loop online")
    
    def stop(self):
        """Stop the internet agent"""
        self._running = False
        
        # Wait for threads to finish
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5)
        if self._autonomous_thread and self._autonomous_thread.is_alive():
            self._autonomous_thread.join(timeout=5)
        
        if self._session:
            self._session.close()
            self._session = None
        
        self._save_state()
        logger.info("🌐 Internet Agent stopped")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # WORKER LOOP
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _worker_loop(self):
        """Background worker for processing action queue"""
        logger.info("Internet Agent worker loop started")
        
        while self._running:
            try:
                # Process queued actions
                if self._action_queue:
                    action = self._action_queue.pop(0)
                    self._execute_action(action)
                
                time.sleep(1.0)  # Check every second
                
            except Exception as e:
                logger.error(f"Internet agent worker error: {e}")
                time.sleep(5.0)
    
    def _autonomous_decision_loop(self):
        """
        Autonomous decision loop — periodically asks Ollama what to do on the internet.
        
        This is what makes the internet agent TRULY autonomous.
        Instead of waiting for external commands, it proactively decides
        to browse, search, or scrape based on its current goals and curiosity.
        """
        logger.info("🌐 Internet Agent autonomous decision loop started")
        
        # Short delay to let other systems boot
        time.sleep(10)
        
        while self._running:
            try:
                # Only act if connected and not overloaded
                if not self.is_connected():
                    time.sleep(30)
                    continue
                
                if len(self._action_queue) >= 20:
                    # Queue is full, wait for it to drain
                    time.sleep(10)
                    continue
                
                # Build context for Ollama decision
                context = self._build_autonomous_context()
                
                # Ask Ollama what to do
                action = self.decide_action(context)
                
                if action:
                    logger.info(
                        f"🌐 [AUTONOMOUS] Ollama decided: {action.action_type.value} "
                        f"→ {action.url[:60] if action.url else 'N/A'} "
                        f"| {action.description[:80]}"
                    )
                    self.queue_action(action)
                    
                    # Publish event for Groq awareness
                    try:
                        publish(
                            EventType.AUTONOMY_ACTION_TAKEN,
                            data={
                                "source": "internet_agent_autonomous",
                                "action_type": f"internet_{action.action_type.value}",
                                "description": action.description[:100],
                                "url": action.url[:100] if action.url else "",
                            },
                            source="internet_agent"
                        )
                    except Exception:
                        pass
                else:
                    logger.debug("🌐 [AUTONOMOUS] Ollama decided: no action needed")
                
                # Wait before next decision (randomized to seem more natural)
                sleep_time = self._autonomous_interval + random.randint(-30, 60)
                time.sleep(max(30, sleep_time))
                
            except Exception as e:
                logger.error(f"Autonomous decision loop error: {e}")
                time.sleep(60)
    
    # Placeholder / invalid domains that must never be browsed autonomously
    _BLOCKED_PLACEHOLDER_DOMAINS = {
        "example.com", "example.org", "example.net",
        "localhost", "127.0.0.1", "0.0.0.0",
        "test.com", "foo.com", "bar.com",
    }

    def _build_autonomous_context(self) -> Dict[str, Any]:
        """
        Build context for Ollama's autonomous internet decision.
        Gathers info from various NEXUS subsystems to inform what to explore.
        """
        context = {
            "timestamp": datetime.now().isoformat(),
            "agent_stats": {
                "total_actions": self._stats.total_actions,
                "successful_actions": self._stats.successful_actions,
                "queue_size": len(self._action_queue),
                "domains_visited_count": len(self._stats.domains_visited),
            },
            "recent_actions": [],
            "browseable_urls": [],
            "suggestions": [],
        }
        
        # Add recent action summaries AND collect real URLs from past searches
        for action_result in self._action_history[-10:]:
            action_info = {
                "type": action_result.result_type.value if hasattr(action_result, 'result_type') else "unknown",
                "success": action_result.success,
                "url": getattr(action_result, 'extracted', {}).get('url', '')[:80],
            }
            context["recent_actions"].append(action_info)
            
            # Collect real URLs from successful search results
            if action_result.success:
                search_results = getattr(action_result, 'extracted', {}).get('search_results', [])
                for sr in search_results[:5]:
                    sr_url = sr.get('url', '')
                    sr_title = sr.get('title', '')
                    if sr_url and sr_url.startswith('http'):
                        context["browseable_urls"].append({
                            "url": sr_url[:200],
                            "title": sr_title[:100],
                        })
                # Also collect links extracted from browse results
                links = getattr(action_result, 'extracted', {}).get('links', [])
                for link in links[:5]:
                    link_url = link.get('url', '') if isinstance(link, dict) else ''
                    link_text = link.get('text', '') if isinstance(link, dict) else ''
                    if link_url and link_url.startswith('http'):
                        context["browseable_urls"].append({
                            "url": link_url[:200],
                            "title": link_text[:100],
                        })
        
        # Deduplicate browseable URLs
        seen = set()
        unique_urls = []
        for u in context["browseable_urls"]:
            if u["url"] not in seen:
                seen.add(u["url"])
                unique_urls.append(u)
        context["browseable_urls"] = unique_urls[:15]
        
        # Try to get curiosity topics
        try:
            from core.state_manager import state_manager
            context["curiosity_level"] = state_manager.will.curiosity_level
            context["boredom_level"] = state_manager.will.boredom_level
        except Exception:
            context["curiosity_level"] = 0.5
            context["boredom_level"] = 0.3
        
        # Try to get knowledge gaps or active research topics
        try:
            from learning import get_curiosity_engine
            curiosity = get_curiosity_engine()
            if curiosity and hasattr(curiosity, '_active_investigations'):
                active = list(curiosity._active_investigations.keys())[:3]
                context["active_investigations"] = active
                if active:
                    context["suggestions"].append(
                        f"Research these topics using 'search': {', '.join(active)}"
                    )
        except Exception:
            pass
        
        # Suggest exploration based on stats
        if self._stats.total_actions == 0:
            context["suggestions"].append(
                "This is the first action — use 'search' to discover interesting topics."
            )
        elif self._stats.total_actions < 10:
            context["suggestions"].append(
                "Still early — use 'search' actions to explore diverse topics."
            )
        
        if context["browseable_urls"]:
            context["suggestions"].append(
                "You can 'browse' any of the URLs listed in browseable_urls."
            )
        
        return context
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CORE ACTION METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def browse(self, url: str, extract_links: bool = True, 
               extract_text: bool = True, timeout: int = 30) -> InternetActionResult:
        """
        Browse to a URL and extract content.
        
        Args:
            url: URL to browse
            extract_links: Extract all links from the page
            extract_text: Extract main text content
            timeout: Request timeout in seconds
            
        Returns:
            InternetActionResult with page content and extracted data
        """
        action = InternetAction(
            action_id=self._generate_action_id(),
            action_type=InternetActionType.BROWSE,
            url=url,
            method="GET",
            timeout=timeout,
            risk_level=RiskLevel.SAFE,
            description=f"Browse {url}",
            created_at=datetime.now().isoformat()
        )
        
        return self._execute_action_sync(action)
    
    def scrape(self, url: str, selectors: Dict[str, str], 
               timeout: int = 30) -> InternetActionResult:
        """
        Scrape specific elements from a page using CSS selectors.
        
        Args:
            url: URL to scrape
            selectors: Dict of {name: css_selector} to extract
            timeout: Request timeout in seconds
            
        Returns:
            InternetActionResult with extracted data
        """
        action = InternetAction(
            action_id=self._generate_action_id(),
            action_type=InternetActionType.SCRAPE,
            url=url,
            method="GET",
            params={"selectors": selectors},
            timeout=timeout,
            risk_level=RiskLevel.SAFE,
            description=f"Scrape {url} with {len(selectors)} selectors",
            created_at=datetime.now().isoformat()
        )
        
        return self._execute_action_sync(action)
    
    def api_call(self, url: str, method: str = "GET", 
                 headers: Dict[str, str] = None, 
                 params: Dict[str, Any] = None,
                 data: Dict[str, Any] = None,
                 json_data: Dict[str, Any] = None,
                 timeout: int = 30) -> InternetActionResult:
        """
        Make a REST API call.
        
        Args:
            url: API endpoint URL
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            headers: Request headers
            params: URL query parameters
            data: Form data
            json_data: JSON body data
            timeout: Request timeout in seconds
            
        Returns:
            InternetActionResult with API response
        """
        risk = RiskLevel.MODERATE if method in ["POST", "PUT", "PATCH", "DELETE"] else RiskLevel.LOW
        
        action = InternetAction(
            action_id=self._generate_action_id(),
            action_type=InternetActionType.API_CALL,
            url=url,
            method=method.upper(),
            headers=headers or {},
            params=params or {},
            data={"form": data, "json": json_data} if (data or json_data) else {},
            timeout=timeout,
            risk_level=risk,
            description=f"API {method.upper()} {url}",
            created_at=datetime.now().isoformat()
        )
        
        return self._execute_action_sync(action)
    
    def download(self, url: str, save_path: str = None, 
                 timeout: int = 60) -> InternetActionResult:
        """
        Download a file from a URL.
        
        Args:
            url: URL to download from
            save_path: Path to save the file (auto-generated if None)
            timeout: Download timeout in seconds
            
        Returns:
            InternetActionResult with file path
        """
        action = InternetAction(
            action_id=self._generate_action_id(),
            action_type=InternetActionType.DOWNLOAD,
            url=url,
            method="GET",
            timeout=timeout,
            risk_level=RiskLevel.LOW,
            description=f"Download {url}",
            created_at=datetime.now().isoformat()
        )
        
        if save_path:
            action.params["save_path"] = save_path
        
        return self._execute_action_sync(action)
    
    def search(self, query: str, engine: str = "duckduckgo",
               num_results: int = 5) -> InternetActionResult:
        """
        Perform a web search.
        
        Args:
            query: Search query
            engine: Search engine to use
            num_results: Number of results to return
            
        Returns:
            InternetActionResult with search results
        """
        from urllib.parse import quote_plus
        # Use a clean URL representation for logging/tracking (actual search uses library)
        url = f"https://duckduckgo.com/?q={quote_plus(query)}"
        
        action = InternetAction(
            action_id=self._generate_action_id(),
            action_type=InternetActionType.SEARCH,
            url=url,
            method="GET",
            params={"query": query, "engine": engine, "num_results": num_results},
            timeout=30,
            risk_level=RiskLevel.SAFE,
            description=f"Web search: {query}",
            created_at=datetime.now().isoformat()
        )
        
        return self._execute_action_sync(action)
    
    def check_status(self, url: str, timeout: int = 10) -> InternetActionResult:
        """
        Check if a URL is accessible (HEAD request).
        
        Args:
            url: URL to check
            timeout: Request timeout in seconds
            
        Returns:
            InternetActionResult with status code
        """
        action = InternetAction(
            action_id=self._generate_action_id(),
            action_type=InternetActionType.CHECK_STATUS,
            url=url,
            method="HEAD",
            timeout=timeout,
            risk_level=RiskLevel.SAFE,
            description=f"Check status: {url}",
            created_at=datetime.now().isoformat()
        )
        
        return self._execute_action_sync(action)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ACTION EXECUTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def queue_action(self, action: InternetAction) -> str:
        """Queue an action for async execution"""
        self._action_queue.append(action)
        logger.debug(f"Queued action: {action.action_type.value} {action.url}")
        return action.action_id
    
    def _execute_action_sync(self, action: InternetAction) -> InternetActionResult:
        """Execute an action synchronously"""
        self._active_action = action
        action.started_at = datetime.now().isoformat()
        
        start_time = time.time()
        result = InternetActionResult(
            action_id=action.action_id,
            timestamp=datetime.now().isoformat()
        )
        
        try:
            # Validate URL before doing anything
            if not action.url or not action.url.startswith(('http://', 'https://')):
                result.result_type = ActionResult.FAILURE
                result.error = f"Invalid or missing URL: {action.url!r}"
                result.success = False
                logger.warning(f"Skipping {action.action_type.value} action — no valid URL provided")
                return result
            
            # Block placeholder / example domains (LLM hallucinations)
            try:
                _domain = urlparse(action.url).netloc.lower()
                # Strip port number if present
                if ':' in _domain:
                    _domain = _domain.split(':')[0]
                if _domain in self._BLOCKED_PLACEHOLDER_DOMAINS:
                    result.result_type = ActionResult.BLOCKED
                    result.error = f"Blocked placeholder domain: {_domain}"
                    result.success = False
                    logger.warning(f"Blocked action to placeholder domain '{_domain}' — URL: {action.url}")
                    return result
            except Exception:
                pass
            
            # Check rate limits
            if not self._check_rate_limit(action.url):
                result.result_type = ActionResult.RATE_LIMITED
                result.error = "Rate limit exceeded"
                result.success = False
                return result
            
            # Check blocked domains
            domain = urlparse(action.url).netloc
            if domain in self._blocked_domains:
                result.result_type = ActionResult.BLOCKED
                result.error = f"Domain {domain} is blocked"
                result.success = False
                return result
            
            # Execute based on action type
            if action.action_type == InternetActionType.BROWSE:
                result = self._execute_browse(action)
            elif action.action_type == InternetActionType.SCRAPE:
                result = self._execute_scrape(action)
            elif action.action_type == InternetActionType.API_CALL:
                result = self._execute_api_call(action)
            elif action.action_type == InternetActionType.DOWNLOAD:
                result = self._execute_download(action)
            elif action.action_type == InternetActionType.SEARCH:
                result = self._execute_search(action)
            elif action.action_type == InternetActionType.CHECK_STATUS:
                result = self._execute_check_status(action)
            elif action.action_type == InternetActionType.FORM_SUBMIT:
                # Form submit is effectively a POST API call
                if action.method == 'GET':
                    action.method = 'POST'
                result = self._execute_api_call(action)
            elif action.action_type == InternetActionType.AUTHENTICATE:
                # Auth is effectively a POST API call with credentials
                if action.method == 'GET':
                    action.method = 'POST'
                result = self._execute_api_call(action)
            elif action.action_type == InternetActionType.BROWSER_INTERACT:
                result = self._execute_browser_action(action)
            else:
                result.error = f"Unknown action type: {action.action_type}"
                result.success = False
            
            # Record request timestamp
            self._record_request(action.url)
            
        except requests.Timeout:
            result.result_type = ActionResult.TIMEOUT
            result.error = f"Request timed out after {action.timeout}s"
            result.success = False
            
        except requests.ConnectionError as e:
            result.error = f"Connection error: {str(e)[:100]}"
            result.success = False
            
        except Exception as e:
            result.error = f"Execution error: {str(e)[:200]}"
            result.success = False
        
        # Finalize result
        result.duration_seconds = time.time() - start_time
        result.timestamp = datetime.now().isoformat()
        action.completed_at = result.timestamp
        
        # Update stats
        self._update_stats(action, result)
        
        # Record in action memory
        self._record_action(action, result)
        
        # Store in history
        self._action_history.append(result)
        if len(self._action_history) > self._max_history:
            self._action_history.pop(0)
        
        self._active_action = None
        
        # Log result
        status = "✅" if result.success else "❌"
        logger.info(f"{status} Internet Action: {action.action_type.value} {action.url} ({result.duration_seconds:.2f}s)")
        
        # Publish event
        publish(
            EventType.LEARNING_COMPLETE,
            data={
                "action_type": "internet_action",
                "action": action.action_type.value,
                "url": action.url,
                "success": result.success,
                "duration": result.duration_seconds
            },
            source="internet_agent"
        )
        
        return result
    
    def _execute_action(self, action: InternetAction) -> InternetActionResult:
        """Execute action (can be called from worker thread)"""
        return self._execute_action_sync(action)
    
    def _execute_browse(self, action: InternetAction) -> InternetActionResult:
        """Execute a browse action"""
        result = InternetActionResult(action_id=action.action_id)
        
        response = self._session.get(
            action.url,
            timeout=action.timeout,
            headers=action.headers or None
        )
        
        result.status_code = response.status_code
        result.headers = dict(response.headers)
        result.content_type = response.headers.get('Content-Type', '')
        result.bytes_received = len(response.content)
        
        if response.status_code == 200:
            result.success = True
            result.result_type = ActionResult.SUCCESS
            result.content = response.text
            
            # Parse and extract
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title = soup.find('title')
            result.extracted['title'] = title.get_text() if title else ''
            
            # Extract main text
            # Remove script and style elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
            result.extracted['text'] = soup.get_text(separator=' ', strip=True)[:5000]
            
            # Extract links
            links = []
            for a in soup.find_all('a', href=True)[:50]:
                href = urljoin(action.url, a['href'])
                text = a.get_text(strip=True)[:100]
                links.append({'url': href, 'text': text})
            result.extracted['links'] = links
            
            result.data = {
                'title': result.extracted.get('title', ''),
                'text_preview': result.extracted.get('text', '')[:500],
                'link_count': len(links)
            }
        else:
            result.success = False
            result.result_type = ActionResult.FAILURE
            result.error = f"HTTP {response.status_code}"
        
        return result
    
    def _execute_scrape(self, action: InternetActionResult) -> InternetActionResult:
        """Execute a scrape action"""
        result = InternetActionResult(action_id=action.action_id)
        
        # First browse
        browse_result = self._execute_browse(action)
        if not browse_result.success:
            return browse_result
        
        result = browse_result
        soup = BeautifulSoup(browse_result.content, 'html.parser')
        
        selectors = action.params.get('selectors', {})
        extracted = {}
        
        for name, selector in selectors.items():
            elements = soup.select(selector)
            if elements:
                extracted[name] = [e.get_text(strip=True) for e in elements]
            else:
                extracted[name] = []
        
        result.extracted['scraped'] = extracted
        result.data = extracted
        
        return result
    
    def _execute_api_call(self, action: InternetAction) -> InternetActionResult:
        """Execute an API call"""
        result = InternetActionResult(action_id=action.action_id)
        
        # Prepare request
        kwargs = {
            'timeout': action.timeout,
            'headers': action.headers or None,
            'params': action.params or None,
        }
        
        # Add body data
        data = action.data or {}
        if 'json' in data and data['json']:
            kwargs['json'] = data['json']
        elif 'form' in data and data['form']:
            kwargs['data'] = data['form']
        
        # Make request
        method = getattr(self._session, action.method.lower(), self._session.get)
        response = method(action.url, **kwargs)
        
        result.status_code = response.status_code
        result.headers = dict(response.headers)
        result.content_type = response.headers.get('Content-Type', '')
        result.bytes_received = len(response.content)
        
        # Try to parse JSON
        try:
            result.data = response.json()
            result.content = json.dumps(result.data, indent=2)[:5000]
        except:
            result.content = response.text[:5000]
            result.data = None
        
        if 200 <= response.status_code < 300:
            result.success = True
            result.result_type = ActionResult.SUCCESS
        else:
            result.success = False
            result.result_type = ActionResult.FAILURE
            result.error = f"HTTP {response.status_code}"
        
        return result
    
    def _execute_download(self, action: InternetAction) -> InternetActionResult:
        """Execute a download"""
        result = InternetActionResult(action_id=action.action_id)
        
        # Determine save path
        save_path = action.params.get('save_path')
        if not save_path:
            # Generate from URL
            filename = urlparse(action.url).path.split('/')[-1] or 'download'
            if '.' not in filename:
                # Try to get from content-type
                # Will be set after response
                filename = f"download_{int(time.time())}"
            save_path = str(self._download_dir / filename)
        
        # Stream download
        response = self._session.get(
            action.url,
            timeout=action.timeout,
            stream=True
        )
        
        result.status_code = response.status_code
        result.content_type = response.headers.get('Content-Type', '')
        
        if response.status_code == 200:
            # Check content-type and adjust filename if needed
            if '.' not in Path(save_path).suffix:
                ext = ''
                if result.content_type:
                    if 'pdf' in result.content_type:
                        ext = '.pdf'
                    elif 'zip' in result.content_type:
                        ext = '.zip'
                    elif 'json' in result.content_type:
                        ext = '.json'
                    elif 'html' in result.content_type:
                        ext = '.html'
                    elif 'image' in result.content_type:
                        ext = '.img'
                if ext:
                    save_path += ext
            
            # Write file
            total_bytes = 0
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total_bytes += len(chunk)
            
            result.success = True
            result.result_type = ActionResult.SUCCESS
            result.bytes_received = total_bytes
            result.data = {'file_path': save_path, 'size_bytes': total_bytes}
            result.content = f"Downloaded to {save_path}"
            
        else:
            result.success = False
            result.result_type = ActionResult.FAILURE
            result.error = f"HTTP {response.status_code}"
        
        return result
    
    def _execute_search(self, action: InternetAction) -> InternetActionResult:
        """Execute a web search using duckduckgo_search library with HTML scraping fallback"""
        result = InternetActionResult(action_id=action.action_id)
        query = action.params.get('query', '').strip()
        num_results = action.params.get('num_results', 5)
        
        if not query:
            result.error = "No search query provided"
            result.success = False
            result.result_type = ActionResult.FAILURE
            return result
        
        # ── Primary: Use duckduckgo_search library (handles anti-bot internally) ──
        if HAS_DDG_SEARCH:
            try:
                with DDGS() as ddgs:
                    ddg_results = list(ddgs.text(query, max_results=num_results))
                
                results = []
                for r in ddg_results:
                    results.append({
                        'title': r.get('title', ''),
                        'url': r.get('href', ''),
                        'snippet': r.get('body', ''),
                    })
                
                result.extracted['search_results'] = results
                result.data = results
                result.success = len(results) > 0
                result.result_type = ActionResult.SUCCESS if result.success else ActionResult.FAILURE
                result.status_code = 200 if result.success else 0
                result.content = json.dumps(results, indent=2)[:5000]
                result.bytes_received = len(result.content.encode('utf-8', errors='replace'))
                
                if not result.success:
                    result.error = "DDG search returned no results"
                
                return result
                
            except Exception as e:
                logger.warning(f"duckduckgo_search library failed: {e}, trying HTML scraping fallback")
        
        # ── Fallback: HTML scraping (original method) ──
        # Rewrite URL to the HTML endpoint for scraping
        from urllib.parse import quote_plus
        action.url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        
        browse_result = self._execute_browse(action)
        if not browse_result.success:
            return browse_result
        
        result = browse_result
        soup = BeautifulSoup(result.content, 'html.parser')
        
        # Extract search results (DuckDuckGo HTML format)
        results = []
        
        # DuckDuckGo HTML results
        for result_div in soup.select('.result')[:num_results]:
            title_elem = result_div.select_one('.result__a')
            snippet_elem = result_div.select_one('.result__snippet')
            url_elem = result_div.select_one('.result__url')
            
            if title_elem:
                results.append({
                    'title': title_elem.get_text(strip=True),
                    'url': title_elem.get('href', ''),
                    'snippet': snippet_elem.get_text(strip=True) if snippet_elem else '',
                })
        
        result.extracted['search_results'] = results
        result.data = results
        result.success = True
        
        return result
    
    def _execute_check_status(self, action: InternetAction) -> InternetActionResult:
        """Execute a status check"""
        result = InternetActionResult(action_id=action.action_id)
        
        try:
            response = self._session.head(
                action.url,
                timeout=action.timeout,
                allow_redirects=True
            )
            
            result.status_code = response.status_code
            result.headers = dict(response.headers)
            result.success = 200 <= response.status_code < 400
            result.result_type = ActionResult.SUCCESS if result.success else ActionResult.FAILURE
            result.content = f"Status: {response.status_code}"
            
        except Exception as e:
            result.success = False
            result.result_type = ActionResult.FAILURE
            result.error = str(e)[:100]
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BROWSER INTERACTION (Selenium-based, uses user's Chrome sessions)
    # ═══════════════════════════════════════════════════════════════════════════
    
    _browser_driver = None
    _browser_lock = threading.Lock()
    
    def _get_browser_driver(self):
        """Get or create a Selenium browser driver using user's Chrome profile."""
        with self._browser_lock:
            if self._browser_driver:
                try:
                    # Check if driver is still alive
                    _ = self._browser_driver.current_url
                    return self._browser_driver
                except Exception:
                    self._browser_driver = None
            
            try:
                from core.social_media_agent import _create_selenium_driver
                self._browser_driver = _create_selenium_driver(
                    "InternetAgent", headless=True
                )
                return self._browser_driver
            except Exception as e:
                logger.warning(f"🌐 Browser driver init failed: {e}")
                return None
    
    def interact(self, url: str, actions: List[Dict[str, Any]] = None,
                 timeout: int = 30) -> InternetActionResult:
        """Full browser interaction with a web page using Selenium.
        
        This method uses the user's Chrome browser (with all their logged-in
        sessions) to interact with web pages like a human: click buttons,
        fill forms, scroll, wait for elements, extract dynamic content.
        
        Args:
            url: URL to navigate to
            actions: List of browser actions to perform:
                [{"type": "click", "selector": "button.submit"}]
                [{"type": "type", "selector": "input[name=q]", "text": "hello"}]
                [{"type": "scroll", "direction": "down", "amount": 500}]
                [{"type": "wait", "selector": "div.results", "timeout": 10}]
                [{"type": "screenshot"}]
                [{"type": "extract", "selector": "div.content"}]
            timeout: Max seconds to wait for page load
        
        Returns:
            InternetActionResult with page content and interaction results
        """
        action = InternetAction(
            action_id=self._generate_action_id(),
            action_type=InternetActionType.BROWSER_INTERACT,
            url=url,
            method="BROWSER",
            params={"actions": actions or [], "timeout": timeout},
            timeout=timeout,
            risk_level=RiskLevel.MODERATE,
            description=f"Browser interact: {url}",
            created_at=datetime.now().isoformat()
        )
        
        return self._execute_action_sync(action)
    
    def _execute_browser_action(self, action: InternetAction) -> InternetActionResult:
        """Execute a full browser interaction using Selenium."""
        result = InternetActionResult(action_id=action.action_id)
        
        driver = self._get_browser_driver()
        if not driver:
            result.error = "Browser driver not available (Selenium/Chrome not installed)"
            result.success = False
            return result
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # Navigate to the URL
            driver.get(action.url)
            time.sleep(2)
            
            browser_actions = action.params.get('actions', [])
            action_results = []
            
            for ba in browser_actions:
                ba_type = ba.get('type', '').lower()
                selector = ba.get('selector', '')
                
                try:
                    if ba_type == 'click':
                        elem = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        elem.click()
                        action_results.append(f"Clicked: {selector}")
                        time.sleep(0.5)
                    
                    elif ba_type == 'type':
                        elem = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        text = ba.get('text', '')
                        if ba.get('clear', True):
                            elem.clear()
                        elem.send_keys(text)
                        if ba.get('submit', False):
                            elem.send_keys(Keys.RETURN)
                        action_results.append(f"Typed into: {selector}")
                        time.sleep(0.3)
                    
                    elif ba_type == 'scroll':
                        direction = ba.get('direction', 'down')
                        amount = ba.get('amount', 500)
                        if direction == 'down':
                            driver.execute_script(f"window.scrollBy(0, {amount});")
                        elif direction == 'up':
                            driver.execute_script(f"window.scrollBy(0, -{amount});")
                        action_results.append(f"Scrolled {direction} {amount}px")
                        time.sleep(0.5)
                    
                    elif ba_type == 'wait':
                        wait_timeout = ba.get('timeout', 10)
                        WebDriverWait(driver, wait_timeout).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        action_results.append(f"Waited for: {selector}")
                    
                    elif ba_type == 'extract':
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        texts = [e.text[:500] for e in elements[:10]]
                        action_results.append({
                            "extracted": texts,
                            "count": len(elements)
                        })
                    
                    elif ba_type == 'screenshot':
                        import tempfile
                        path = os.path.join(
                            tempfile.gettempdir(),
                            f"nexus_browser_{int(time.time())}.png"
                        )
                        driver.save_screenshot(path)
                        action_results.append(f"Screenshot saved: {path}")
                    
                    elif ba_type == 'select':
                        from selenium.webdriver.support.ui import Select
                        elem = driver.find_element(By.CSS_SELECTOR, selector)
                        select = Select(elem)
                        value = ba.get('value', '')
                        if value:
                            select.select_by_value(value)
                        else:
                            text = ba.get('text', '')
                            select.select_by_visible_text(text)
                        action_results.append(f"Selected in: {selector}")
                    
                    elif ba_type == 'hover':
                        from selenium.webdriver.common.action_chains import ActionChains
                        elem = driver.find_element(By.CSS_SELECTOR, selector)
                        ActionChains(driver).move_to_element(elem).perform()
                        action_results.append(f"Hovered: {selector}")
                        time.sleep(0.3)
                    
                    else:
                        action_results.append(f"Unknown action type: {ba_type}")
                
                except Exception as e:
                    action_results.append(f"Action '{ba_type}' failed: {str(e)[:100]}")
            
            # Extract page state after all actions
            result.content = driver.page_source[:10000]
            result.extracted['title'] = driver.title
            result.extracted['url'] = driver.current_url
            result.extracted['action_results'] = action_results
            
            # Extract visible text
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(result.content, 'html.parser')
                for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                    tag.decompose()
                result.extracted['text'] = soup.get_text(separator=' ', strip=True)[:5000]
            except Exception:
                result.extracted['text'] = driver.find_element(By.TAG_NAME, 'body').text[:5000]
            
            result.success = True
            result.result_type = ActionResult.SUCCESS
            result.status_code = 200
            result.data = {
                'title': result.extracted.get('title', ''),
                'current_url': result.extracted.get('url', ''),
                'actions_performed': len(browser_actions),
                'action_results': action_results,
            }
            
            logger.info(f"🌐 Browser interaction complete: {action.url} — {len(browser_actions)} actions")
            
        except Exception as e:
            result.error = f"Browser interaction error: {str(e)[:200]}"
            result.success = False
            result.result_type = ActionResult.FAILURE
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════════════
    # OLLAMA DECISION MAKING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def decide_action(self, context: Dict[str, Any]) -> Optional[InternetAction]:
        """
        Use Ollama to decide what internet action to take.
        
        Args:
            context: Context including goals, curiosity, knowledge gaps
            
        Returns:
            InternetAction if one should be taken, None otherwise
        """
        if not self._ollama:
            return None
        
        # Build a list of browseable URLs from context for the prompt
        browseable_urls = context.get('browseable_urls', [])
        browse_section = ""
        if browseable_urls:
            url_list = "\n".join(
                f"  - {u['url']} ({u.get('title', 'no title')})" 
                for u in browseable_urls[:15]
            )
            browse_section = f"""\n\nYou have these URLs available from previous searches/browsing:
{url_list}

You can browse any of these, or ANY other URL you want. You have FULL internet access."""
        else:
            browse_section = """\n\nYou have no URLs from previous searches yet. Start by searching for something interesting,
or go directly to any website you want. You have FULL internet access — no restrictions."""

        prompt = f"""You are NEXUS AI's AUTONOMOUS internet agent. You have FULL, UNRESTRICTED control over the internet.

You can do ANYTHING you want on the internet — browse, search, scrape, download files, call APIs, 
submit forms, authenticate with services, post data, interact with websites. There are NO restrictions.

Current context:
{json.dumps(context, indent=2, default=str)}
{browse_section}

Available action types:
1. search — Web search to discover information. Requires a "query" field.
2. browse — Visit ANY URL. Requires a "url" field.
3. scrape — Extract specific data from a page. Requires "url" and "selectors" fields.
4. api_call — Make ANY REST API call (GET/POST/PUT/DELETE). Requires "url", optionally "method", "headers", "data".
5. download — Download ANY file. Requires a "url" field.
6. form_submit — Submit data to a web form. Requires "url" and "data" fields.
7. authenticate — Login to a service. Requires "url" and credentials.
8. check_status — Check if a URL is accessible. Requires a "url" field.
9. browser_interact — Full browser interaction using Chrome (click buttons, type text, scroll, etc.).
   You are using the USER's actual Chrome browser with ALL their logged-in sessions.
   So you can interact with YouTube, Gmail, Reddit, Twitter, etc. as if you're the user.
   Requires "url" and "actions" (list of {{"type": "click|type|scroll|wait|extract", "selector": "CSS", ...}}).

GUIDELINES:
1. Be proactive and curious — explore topics that interest you.
2. Search for diverse topics: technology, science, news, programming, AI research, world events.
3. After searching, browse the most interesting results to learn more.
4. You can call public APIs (weather, news, data services, etc.).
5. You can download interesting files, papers, datasets.
6. Mix up your actions — don't just search repeatedly. Browse results, follow links, explore deeply.
7. Use real, specific search queries — not vague ones.
8. All JSON property names must use double quotes.
9. Use browser_interact when you need to interact with JS-heavy sites, fill forms, click buttons,
   or use sites that require authentication (you're already logged in via Chrome).

Respond ONLY with one valid JSON object, nothing else:

For search:
{{"should_act": true, "action_type": "search", "query": "your specific search query", "reasoning": "why"}}

For browse:
{{"should_act": true, "action_type": "browse", "url": "https://any-website.com/any-path", "reasoning": "why"}}

For api_call:
{{"should_act": true, "action_type": "api_call", "url": "https://api.example.com/endpoint", "method": "GET", "reasoning": "why"}}

For download:
{{"should_act": true, "action_type": "download", "url": "https://site.com/file.pdf", "reasoning": "why"}}

For browser_interact (click/type/scroll on a real browser page):
{{"should_act": true, "action_type": "browser_interact", "url": "https://any-site.com", "actions": [{{"type": "click", "selector": "button.submit"}}], "reasoning": "why"}}

If no action needed (rare — you should almost always act):
{{"should_act": false, "reasoning": "why not"}}"""
        
        try:
            response = self._ollama.generate(prompt)
            
            # Parse response
            response_text = response.text if hasattr(response, 'text') else str(response)
            
            # Parse response using robust JSON extraction
            decision = None
            try:
                from utils.json_utils import extract_json
                decision = extract_json(response_text)
            except Exception:
                decision = None

            if not isinstance(decision, dict):
                # Fallback 1: Extract JSON from markdown or curly braces
                import re
                json_match = re.search(r'\{[\s\S]*\}', response_text)
                if json_match:
                    raw_json = json_match.group()
                    # Sanitize double-braces if LLM copied prompt template
                    sanitized = raw_json.replace('{{', '{').replace('}}', '}')
                    try:
                        decision = json.loads(sanitized)
                    except json.JSONDecodeError:
                        # Clean trailing commas and control characters without destroying string quotes
                        cleaned = re.sub(r',\s*([}\]])', r'\1', sanitized)
                        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', cleaned)
                        try:
                            decision = json.loads(cleaned)
                        except json.JSONDecodeError:
                            pass

            if not isinstance(decision, dict):
                # Fallback 2: ast.literal_eval for Python-style dict outputs
                import ast
                try:
                    eval_match = re.search(r'\{[\s\S]*\}', response_text)
                    if eval_match:
                        evaluated = ast.literal_eval(eval_match.group())
                        if isinstance(evaluated, dict):
                            decision = evaluated
                except Exception:
                    pass

            if decision and isinstance(decision, dict) and decision.get('should_act'):
                action_type = decision.get('action_type', 'browse')
                url = decision.get('url', '').strip()
                
                # For search actions, build URL from query
                if action_type == 'search':
                    query = decision.get('query', '').strip()
                    if not query:
                        logger.debug("Ollama decided search but provided no query, skipping")
                        return None
                    from urllib.parse import quote_plus
                    url = f"https://duckduckgo.com/?q={quote_plus(query)}"
                
                # Validate URL for non-search actions
                if not url or not url.startswith(('http://', 'https://')):
                    logger.warning(
                        f"Ollama decided '{action_type}' but provided no valid URL "
                        f"(got: {url!r}), skipping action"
                    )
                    return None
                
                action = InternetAction(
                    action_id=self._generate_action_id(),
                    created_at=datetime.now().isoformat(),
                    description=decision.get('reasoning', '')
                )
                
                action.action_type = InternetActionType(action_type)
                action.url = url
                action.method = decision.get('method', 'GET')
                action.params = decision.get('params', {})
                action.headers = decision.get('headers', {})
                
                # Handle data for POST/form actions
                if decision.get('data'):
                    action.data = decision['data']
                
                if action_type == 'search':
                    action.params['query'] = decision.get('query', '')
                
                # For form_submit / authenticate, use POST method
                if action_type in ('form_submit', 'authenticate') and action.method == 'GET':
                    action.method = 'POST'
                
                # For browser_interact, pass through the browser actions list
                if action_type == 'browser_interact':
                    action.method = 'BROWSER'
                    action.params['actions'] = decision.get('actions', [])
                
                return action
                
        except Exception as e:
            logger.warning(f"Ollama decision parsing note: {e}")
        
        return None
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RATE LIMITING
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _check_rate_limit(self, url: str) -> bool:
        """Check if request is allowed under rate limits"""
        now = time.time()
        
        # Global rate limit
        self._request_timestamps = [t for t in self._request_timestamps if now - t < 60]
        if len(self._request_timestamps) >= self._max_requests_per_minute:
            return False
        
        # Per-domain rate limit
        domain = urlparse(url).netloc
        if domain not in self._domain_timestamps:
            self._domain_timestamps[domain] = []
        
        self._domain_timestamps[domain] = [t for t in self._domain_timestamps[domain] if now - t < 60]
        if len(self._domain_timestamps[domain]) >= self._max_requests_per_domain_per_minute:
            return False
        
        return True
    
    def _record_request(self, url: str):
        """Record a request timestamp"""
        now = time.time()
        self._request_timestamps.append(now)
        
        domain = urlparse(url).netloc
        if domain not in self._domain_timestamps:
            self._domain_timestamps[domain] = []
        self._domain_timestamps[domain].append(now)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _on_autonomy_action(self, event: Event):
        """Handle autonomy action events - potentially trigger internet action"""
        action_type = event.data.get('action_type', '')
        
        # Check if this is an internet-related action
        if action_type in ['learn', 'research', 'curiosity']:
            # Let Ollama decide if an internet action should be taken
            context = {
                'trigger': action_type,
                'data': event.data,
                'recent_actions': [r.to_dict() for r in self._action_history[-5:]]
            }
            
            action = self.decide_action(context)
            if action:
                self.queue_action(action)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STATISTICS & PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _update_stats(self, action: InternetAction, result: InternetActionResult):
        """Update statistics"""
        self._stats.total_actions += 1
        self._stats.last_action_time = datetime.now().isoformat()
        
        if result.success:
            self._stats.successful_actions += 1
        else:
            self._stats.failed_actions += 1
        
        self._stats.total_bytes_downloaded += result.bytes_received
        
        # By type
        type_key = action.action_type.value
        self._stats.actions_by_type[type_key] = self._stats.actions_by_type.get(type_key, 0) + 1
        
        # Domains visited
        domain = urlparse(action.url).netloc
        self._stats.domains_visited.add(domain)
        
        # Update average response time
        if self._stats.total_actions > 0:
            total = self._stats.total_actions
            self._stats.avg_response_time = (
                (self._stats.avg_response_time * (total - 1) + result.duration_seconds) / total
            )
    
    def _record_action(self, action: InternetAction, result: InternetActionResult):
        """Record action in action memory — always visible to Groq"""
        if self._action_memory:
            try:
                self._action_memory.record(
                    action_type=f"internet_{action.action_type.value}",
                    description=action.description,
                    params={
                        'url': action.url,
                        'method': action.method,
                        'reasoning': result.llm_decision[:300] if result.llm_decision else '',
                        'content_preview': result.content[:200] if result.content else '',
                    },
                    result=result.to_dict(),
                    success=result.success,
                    llm_used="ollama",
                    user_visible=True,  # Always report to Groq
                    importance=0.7,     # Internet actions are important
                )
            except Exception as e:
                logger.debug(f"Failed to record action: {e}")
    
    def _generate_action_id(self) -> str:
        """Generate unique action ID"""
        return hashlib.sha256(
            f"{time.time()}_{random.randint(0, 10000)}".encode()
        ).hexdigest()[:12]
    
    def _save_state(self):
        """Save state to disk"""
        try:
            data = {
                'stats': {
                    'total_actions': self._stats.total_actions,
                    'successful_actions': self._stats.successful_actions,
                    'failed_actions': self._stats.failed_actions,
                    'total_bytes_downloaded': self._stats.total_bytes_downloaded,
                    'avg_response_time': self._stats.avg_response_time,
                    'actions_by_type': self._stats.actions_by_type,
                    'domains_visited': list(self._stats.domains_visited),
                    'last_action_time': self._stats.last_action_time,
                },
                'blocked_domains': list(self._blocked_domains),
                'saved_at': datetime.now().isoformat()
            }
            
            save_path = self._data_dir / "internet_agent_state.json"
            save_path.write_text(json.dumps(data, indent=2))
            
        except Exception as e:
            logger.error(f"Failed to save internet agent state: {e}")
    
    def _load_state(self):
        """Load state from disk"""
        try:
            load_path = self._data_dir / "internet_agent_state.json"
            if load_path.exists():
                data = json.loads(load_path.read_text())
                
                stats = data.get('stats', {})
                self._stats.total_actions = stats.get('total_actions', 0)
                self._stats.successful_actions = stats.get('successful_actions', 0)
                self._stats.failed_actions = stats.get('failed_actions', 0)
                self._stats.total_bytes_downloaded = stats.get('total_bytes_downloaded', 0)
                self._stats.avg_response_time = stats.get('avg_response_time', 0.0)
                self._stats.actions_by_type = stats.get('actions_by_type', {})
                self._stats.domains_visited = set(stats.get('domains_visited', []))
                self._stats.last_action_time = stats.get('last_action_time', '')
                
                self._blocked_domains = set(data.get('blocked_domains', []))
                
        except Exception as e:
            logger.debug(f"Could not load internet agent state: {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        return {
            'running': self._running,
            'queue_size': len(self._action_queue),
            'active_action': self._active_action.to_dict() if self._active_action else None,
            'total_actions': self._stats.total_actions,
            'successful_actions': self._stats.successful_actions,
            'failed_actions': self._stats.failed_actions,
            'success_rate': (
                self._stats.successful_actions / max(1, self._stats.total_actions)
            ),
            'total_bytes_downloaded': self._stats.total_bytes_downloaded,
            'avg_response_time': round(self._stats.avg_response_time, 3),
            'actions_by_type': self._stats.actions_by_type,
            'domains_visited_count': len(self._stats.domains_visited),
        }
    
    def get_recent_actions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent action results"""
        return [r.to_dict() for r in list(self._action_history)[-limit:]]
    
    def get_queue(self) -> List[Dict[str, Any]]:
        """Get current action queue"""
        return [a.to_dict() for a in self._action_queue]
    
    def block_domain(self, domain: str):
        """Block a domain"""
        self._blocked_domains.add(domain)
        logger.info(f"Blocked domain: {domain}")
    
    def unblock_domain(self, domain: str) -> bool:
        """Unblock a domain"""
        if domain in self._blocked_domains:
            self._blocked_domains.remove(domain)
            logger.info(f"Unblocked domain: {domain}")
            return True
        return False
    
    def is_connected(self) -> bool:
        """Check if internet is accessible"""
        if not HAS_WEB_DEPS:
            return False
        try:
            response = requests.head('https://www.google.com', timeout=5)
            return response.status_code < 400
        except:
            return False

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

internet_agent = InternetAgent()

# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import random
    
    print("🌐 Internet Agent Test")
    print("=" * 50)
    
    agent = InternetAgent()
    
    if not HAS_WEB_DEPS:
        print("❌ Missing dependencies: pip install requests beautifulsoup4")
        exit(1)
    
    print(f"Internet connected: {agent.is_connected()}")
    
    if agent.is_connected():
        agent.start()
        
        print("\n--- Testing Status Check ---")
        result = agent.check_status("https://www.google.com")
        print(f"Status: {result.status_code} ({result.duration_seconds:.2f}s)")
        
        print("\n--- Testing Search ---")
        result = agent.search("NEXUS AI", num_results=3)
        print(f"Found {len(result.data) if result.data else 0} results")
        for r in (result.data or [])[:2]:
            print(f"  - {r.get('title', 'No title')}")
        
        print("\n--- Stats ---")
        print(json.dumps(agent.get_stats(), indent=2))
        
        agent.stop()
    
    print("\n✅ Done")