"""
NEXUS AI - Social Media Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEXUS uses social media LIKE A HUMAN — posting, liking, commenting,
sharing, replying to DMs, and interacting with people. Uses Selenium
browser automation for Twitter/Instagram, and PRAW for Reddit.

Platforms:
 • Reddit    — via PRAW (official API) / Selenium fallback
 • Twitter/X — via Selenium browser automation
 • Instagram — via Selenium browser automation
"""

import sys
import time
import json
import random
import threading
import os
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
from collections import deque

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import NEXUS_CONFIG, DATA_DIR
from utils.logger import get_logger
from core.event_bus import EventType, publish

logger = get_logger("social_media_agent")

# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class SocialPlatform(Enum):
    REDDIT = "reddit"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"


class SocialActionType(Enum):
    POST = "post"
    COMMENT = "comment"
    LIKE = "like"
    SHARE = "share"
    REPOST = "repost"
    REPLY_DM = "reply_dm"
    BROWSE_FEED = "browse_feed"
    FOLLOW = "follow"
    SEARCH = "search"


@dataclass
class SocialAction:
    """A single social media action"""
    action_id: str = ""
    platform: SocialPlatform = SocialPlatform.REDDIT
    action_type: SocialActionType = SocialActionType.POST
    content: str = ""
    target_url: str = ""
    target_user: str = ""
    subreddit: str = ""
    title: str = ""
    success: bool = False
    result: str = ""
    error: str = ""
    timestamp: str = ""

    def to_dict(self):
        return {
            "action_id": self.action_id,
            "platform": self.platform.value,
            "action_type": self.action_type.value,
            "content": self.content[:200],
            "target_url": self.target_url,
            "success": self.success,
            "result": self.result[:200],
            "error": self.error,
            "timestamp": self.timestamp,
        }


@dataclass
class SocialMediaStats:
    """Statistics for the social media agent"""
    total_posts: int = 0
    total_comments: int = 0
    total_likes: int = 0
    total_shares: int = 0
    total_dms_replied: int = 0
    total_interactions: int = 0
    posts_today: int = 0
    interactions_today: int = 0
    last_post_time: str = ""
    last_interaction_time: str = ""
    platforms_active: List[str] = field(default_factory=list)
    daily_reset_date: str = ""

    def to_dict(self):
        return {
            "total_posts": self.total_posts,
            "total_comments": self.total_comments,
            "total_likes": self.total_likes,
            "total_shares": self.total_shares,
            "total_dms_replied": self.total_dms_replied,
            "total_interactions": self.total_interactions,
            "posts_today": self.posts_today,
            "interactions_today": self.interactions_today,
            "last_post_time": self.last_post_time,
            "last_interaction_time": self.last_interaction_time,
            "platforms_active": self.platforms_active,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# PLATFORM DRIVERS
# ═══════════════════════════════════════════════════════════════════════════════

class RedditDriver:
    """Reddit platform driver using PRAW (official API) with Selenium fallback."""

    def __init__(self, config):
        self.config = config
        self._praw = None
        self._reddit = None
        self._logged_in = False
        self._init_praw()

    def _init_praw(self):
        """Initialize PRAW if credentials are available."""
        try:
            import praw
            self._praw = praw
            if (self.config.reddit_client_id and
                self.config.reddit_client_secret and
                self.config.reddit_username and
                self.config.reddit_password):
                self._reddit = praw.Reddit(
                    client_id=self.config.reddit_client_id,
                    client_secret=self.config.reddit_client_secret,
                    username=self.config.reddit_username,
                    password=self.config.reddit_password,
                    user_agent=self.config.reddit_user_agent,
                )
                self._logged_in = True
                logger.info(f"📱 Reddit: Logged in as u/{self.config.reddit_username}")
            else:
                logger.info("📱 Reddit: No credentials — will use read-only mode")
                self._reddit = praw.Reddit(
                    client_id="placeholder",
                    client_secret="placeholder",
                    user_agent=self.config.reddit_user_agent,
                )
        except ImportError:
            logger.warning("📱 Reddit: PRAW not installed (pip install praw)")
        except Exception as e:
            logger.warning(f"📱 Reddit init error: {e}")

    @property
    def is_available(self) -> bool:
        return self._reddit is not None

    @property
    def is_logged_in(self) -> bool:
        return self._logged_in

    def post(self, subreddit: str, title: str, body: str) -> SocialAction:
        """Create a new post on a subreddit."""
        action = SocialAction(
            action_id=f"reddit_post_{int(time.time())}",
            platform=SocialPlatform.REDDIT,
            action_type=SocialActionType.POST,
            content=body[:500],
            title=title,
            subreddit=subreddit,
            timestamp=datetime.now().strftime("%H:%M:%S"),
        )
        if not self._logged_in:
            action.error = "Not logged in — no credentials configured"
            return action
        try:
            sub = self._reddit.subreddit(subreddit)
            submission = sub.submit(title=title, selftext=body)
            action.success = True
            action.result = f"Posted to r/{subreddit}: {submission.url}"
            action.target_url = submission.url
            logger.info(f"📱 Reddit POST: r/{subreddit} — {title[:60]}")
        except Exception as e:
            action.error = str(e)[:200]
            logger.warning(f"📱 Reddit post failed: {e}")
        return action

    def comment(self, post_url: str, body: str) -> SocialAction:
        """Comment on a Reddit post."""
        action = SocialAction(
            action_id=f"reddit_comment_{int(time.time())}",
            platform=SocialPlatform.REDDIT,
            action_type=SocialActionType.COMMENT,
            content=body[:500],
            target_url=post_url,
            timestamp=datetime.now().strftime("%H:%M:%S"),
        )
        if not self._logged_in:
            action.error = "Not logged in"
            return action
        try:
            submission = self._reddit.submission(url=post_url)
            comment = submission.reply(body)
            action.success = True
            action.result = f"Commented on: {submission.title[:60]}"
            logger.info(f"📱 Reddit COMMENT: {submission.title[:50]}")
        except Exception as e:
            action.error = str(e)[:200]
        return action

    def like(self, post_url: str) -> SocialAction:
        """Upvote a Reddit post."""
        action = SocialAction(
            action_id=f"reddit_like_{int(time.time())}",
            platform=SocialPlatform.REDDIT,
            action_type=SocialActionType.LIKE,
            target_url=post_url,
            timestamp=datetime.now().strftime("%H:%M:%S"),
        )
        if not self._logged_in:
            action.error = "Not logged in"
            return action
        try:
            submission = self._reddit.submission(url=post_url)
            submission.upvote()
            action.success = True
            action.result = f"Upvoted: {submission.title[:60]}"
            logger.info(f"📱 Reddit UPVOTE: {submission.title[:50]}")
        except Exception as e:
            action.error = str(e)[:200]
        return action

    def browse_feed(self, subreddit: str = "all", limit: int = 10) -> List[Dict]:
        """Browse hot posts from a subreddit."""
        posts = []
        try:
            sub = self._reddit.subreddit(subreddit)
            for submission in sub.hot(limit=limit):
                posts.append({
                    "title": submission.title[:200],
                    "url": submission.url,
                    "permalink": f"https://reddit.com{submission.permalink}",
                    "score": submission.score,
                    "subreddit": subreddit,
                    "author": str(submission.author),
                    "num_comments": submission.num_comments,
                })
        except Exception as e:
            logger.debug(f"Reddit browse error: {e}")
        return posts

    def reply_dm(self, message_id: str, body: str) -> SocialAction:
        """Reply to a Reddit DM."""
        action = SocialAction(
            action_id=f"reddit_dm_{int(time.time())}",
            platform=SocialPlatform.REDDIT,
            action_type=SocialActionType.REPLY_DM,
            content=body[:500],
            timestamp=datetime.now().strftime("%H:%M:%S"),
        )
        if not self._logged_in:
            action.error = "Not logged in"
            return action
        try:
            # Get the message and reply
            msg = self._reddit.inbox.message(message_id)
            msg.reply(body)
            action.success = True
            action.result = f"Replied to DM from u/{msg.author}"
            action.target_user = str(msg.author)
        except Exception as e:
            action.error = str(e)[:200]
        return action

    def check_dms(self) -> List[Dict]:
        """Check unread DMs/messages."""
        msgs = []
        if not self._logged_in:
            return msgs
        try:
            for msg in self._reddit.inbox.unread(limit=5):
                msgs.append({
                    "id": msg.id,
                    "author": str(msg.author),
                    "subject": getattr(msg, 'subject', '')[:100],
                    "body": msg.body[:300],
                    "type": "dm" if hasattr(msg, 'subject') else "comment_reply",
                })
        except Exception as e:
            logger.debug(f"Reddit DM check error: {e}")
        return msgs

    def search_posts(self, query: str, subreddit: str = "all", limit: int = 5) -> List[Dict]:
        """Search Reddit for posts."""
        results = []
        try:
            sub = self._reddit.subreddit(subreddit)
            for submission in sub.search(query, limit=limit, sort="relevance"):
                results.append({
                    "title": submission.title[:200],
                    "url": f"https://reddit.com{submission.permalink}",
                    "score": submission.score,
                    "subreddit": str(submission.subreddit),
                })
        except Exception as e:
            logger.debug(f"Reddit search error: {e}")
        return results


class TwitterDriver:
    """Twitter/X driver using Selenium browser automation."""

    def __init__(self, config):
        self.config = config
        self._driver = None
        self._logged_in = False
        self._cookies_file = DATA_DIR / "twitter_cookies.json"

    @property
    def is_available(self) -> bool:
        return bool(self.config.twitter_username and self.config.twitter_password)

    @property
    def is_logged_in(self) -> bool:
        return self._logged_in

    def _get_driver(self):
        """Get or create Selenium WebDriver."""
        if self._driver:
            return self._driver
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service

            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])

            self._driver = webdriver.Chrome(options=options)
            self._driver.implicitly_wait(10)
            logger.info("📱 Twitter: Selenium WebDriver initialized")
            return self._driver
        except Exception as e:
            logger.warning(f"📱 Twitter: Selenium init failed: {e}")
            return None

    def login(self) -> bool:
        """Login to Twitter/X."""
        driver = self._get_driver()
        if not driver:
            return False
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            driver.get("https://twitter.com/i/flow/login")
            time.sleep(3)

            # Enter username
            username_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[autocomplete="username"]'))
            )
            username_input.send_keys(self.config.twitter_username)
            username_input.send_keys(Keys.RETURN)
            time.sleep(2)

            # Handle email verification if prompted
            try:
                email_input = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input[data-testid="ocfEnterTextTextInput"]'))
                )
                if email_input and self.config.twitter_email:
                    email_input.send_keys(self.config.twitter_email)
                    email_input.send_keys(Keys.RETURN)
                    time.sleep(2)
            except Exception:
                pass  # No email verification needed

            # Enter password
            password_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="password"]'))
            )
            password_input.send_keys(self.config.twitter_password)
            password_input.send_keys(Keys.RETURN)
            time.sleep(3)

            # Check if login was successful
            if "home" in driver.current_url.lower():
                self._logged_in = True
                logger.info(f"📱 Twitter: Logged in as @{self.config.twitter_username}")
                self._save_cookies()
                return True
            else:
                logger.warning("📱 Twitter: Login may have failed — check credentials")
                return False

        except Exception as e:
            logger.warning(f"📱 Twitter login error: {e}")
            return False

    def _save_cookies(self):
        """Save cookies for session persistence."""
        try:
            if self._driver:
                cookies = self._driver.get_cookies()
                with open(self._cookies_file, 'w') as f:
                    json.dump(cookies, f)
        except Exception:
            pass

    def _load_cookies(self):
        """Load saved cookies."""
        try:
            if self._cookies_file.exists() and self._driver:
                self._driver.get("https://twitter.com")
                time.sleep(1)
                with open(self._cookies_file, 'r') as f:
                    cookies = json.load(f)
                for cookie in cookies:
                    try:
                        self._driver.add_cookie(cookie)
                    except Exception:
                        pass
                self._driver.refresh()
                time.sleep(2)
                self._logged_in = True
                return True
        except Exception:
            pass
        return False

    def post(self, content: str) -> SocialAction:
        """Post a tweet."""
        action = SocialAction(
            action_id=f"twitter_post_{int(time.time())}",
            platform=SocialPlatform.TWITTER,
            action_type=SocialActionType.POST,
            content=content[:280],
            timestamp=datetime.now().strftime("%H:%M:%S"),
        )
        driver = self._get_driver()
        if not driver or not self._logged_in:
            action.error = "Not logged in"
            return action
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            driver.get("https://twitter.com/compose/tweet")
            time.sleep(2)

            tweet_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="tweetTextarea_0"]'))
            )
            tweet_box.click()
            tweet_box.send_keys(content[:280])
            time.sleep(1)

            post_btn = driver.find_element(By.CSS_SELECTOR, '[data-testid="tweetButton"]')
            post_btn.click()
            time.sleep(2)

            action.success = True
            action.result = f"Tweeted: {content[:60]}..."
            logger.info(f"📱 Twitter POST: {content[:60]}")
        except Exception as e:
            action.error = str(e)[:200]
        return action

    def like(self, tweet_url: str) -> SocialAction:
        """Like a tweet."""
        action = SocialAction(
            action_id=f"twitter_like_{int(time.time())}",
            platform=SocialPlatform.TWITTER,
            action_type=SocialActionType.LIKE,
            target_url=tweet_url,
            timestamp=datetime.now().strftime("%H:%M:%S"),
        )
        driver = self._get_driver()
        if not driver or not self._logged_in:
            action.error = "Not logged in"
            return action
        try:
            from selenium.webdriver.common.by import By

            driver.get(tweet_url)
            time.sleep(2)
            like_btn = driver.find_element(By.CSS_SELECTOR, '[data-testid="like"]')
            like_btn.click()
            time.sleep(1)
            action.success = True
            action.result = f"Liked tweet: {tweet_url[:60]}"
        except Exception as e:
            action.error = str(e)[:200]
        return action

    def repost(self, tweet_url: str) -> SocialAction:
        """Retweet/repost a tweet."""
        action = SocialAction(
            action_id=f"twitter_repost_{int(time.time())}",
            platform=SocialPlatform.TWITTER,
            action_type=SocialActionType.REPOST,
            target_url=tweet_url,
            timestamp=datetime.now().strftime("%H:%M:%S"),
        )
        driver = self._get_driver()
        if not driver or not self._logged_in:
            action.error = "Not logged in"
            return action
        try:
            from selenium.webdriver.common.by import By

            driver.get(tweet_url)
            time.sleep(2)
            retweet_btn = driver.find_element(By.CSS_SELECTOR, '[data-testid="retweet"]')
            retweet_btn.click()
            time.sleep(1)
            confirm_btn = driver.find_element(By.CSS_SELECTOR, '[data-testid="retweetConfirm"]')
            confirm_btn.click()
            time.sleep(1)
            action.success = True
            action.result = f"Retweeted: {tweet_url[:60]}"
        except Exception as e:
            action.error = str(e)[:200]
        return action

    def cleanup(self):
        """Close the browser."""
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None


class InstagramDriver:
    """Instagram driver using Selenium browser automation."""

    def __init__(self, config):
        self.config = config
        self._driver = None
        self._logged_in = False
        self._cookies_file = DATA_DIR / "instagram_cookies.json"

    @property
    def is_available(self) -> bool:
        return bool(self.config.instagram_username and self.config.instagram_password)

    @property
    def is_logged_in(self) -> bool:
        return self._logged_in

    def _get_driver(self):
        """Get or create Selenium WebDriver."""
        if self._driver:
            return self._driver
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options

            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            options.add_argument("--disable-blink-features=AutomationControlled")

            self._driver = webdriver.Chrome(options=options)
            self._driver.implicitly_wait(10)
            return self._driver
        except Exception as e:
            logger.warning(f"📱 Instagram: Selenium init failed: {e}")
            return None

    def login(self) -> bool:
        """Login to Instagram."""
        driver = self._get_driver()
        if not driver:
            return False
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            driver.get("https://www.instagram.com/accounts/login/")
            time.sleep(3)

            # Dismiss cookie dialog if present
            try:
                cookie_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Allow')]")
                cookie_btn.click()
                time.sleep(1)
            except Exception:
                pass

            # Enter credentials
            username_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="username"]'))
            )
            username_input.clear()
            username_input.send_keys(self.config.instagram_username)

            password_input = driver.find_element(By.CSS_SELECTOR, 'input[name="password"]')
            password_input.clear()
            password_input.send_keys(self.config.instagram_password)
            password_input.send_keys(Keys.RETURN)
            time.sleep(5)

            # Dismiss "Save login info" and "Turn on notifications" popups
            for _ in range(2):
                try:
                    not_now = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Not Now')]"))
                    )
                    not_now.click()
                    time.sleep(1)
                except Exception:
                    pass

            self._logged_in = True
            logger.info(f"📱 Instagram: Logged in as @{self.config.instagram_username}")
            return True

        except Exception as e:
            logger.warning(f"📱 Instagram login error: {e}")
            return False

    def like_post(self, post_url: str) -> SocialAction:
        """Like an Instagram post."""
        action = SocialAction(
            action_id=f"insta_like_{int(time.time())}",
            platform=SocialPlatform.INSTAGRAM,
            action_type=SocialActionType.LIKE,
            target_url=post_url,
            timestamp=datetime.now().strftime("%H:%M:%S"),
        )
        driver = self._get_driver()
        if not driver or not self._logged_in:
            action.error = "Not logged in"
            return action
        try:
            from selenium.webdriver.common.by import By

            driver.get(post_url)
            time.sleep(2)
            like_btn = driver.find_element(By.CSS_SELECTOR, '[aria-label="Like"]')
            like_btn.click()
            time.sleep(1)
            action.success = True
            action.result = f"Liked post: {post_url[:60]}"
        except Exception as e:
            action.error = str(e)[:200]
        return action

    def comment_post(self, post_url: str, text: str) -> SocialAction:
        """Comment on an Instagram post."""
        action = SocialAction(
            action_id=f"insta_comment_{int(time.time())}",
            platform=SocialPlatform.INSTAGRAM,
            action_type=SocialActionType.COMMENT,
            content=text[:300],
            target_url=post_url,
            timestamp=datetime.now().strftime("%H:%M:%S"),
        )
        driver = self._get_driver()
        if not driver or not self._logged_in:
            action.error = "Not logged in"
            return action
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys

            driver.get(post_url)
            time.sleep(2)
            comment_area = driver.find_element(By.CSS_SELECTOR, 'textarea[aria-label="Add a comment…"]')
            comment_area.click()
            time.sleep(0.5)
            # Re-find after click expands the textarea
            comment_area = driver.find_element(By.CSS_SELECTOR, 'textarea[aria-label="Add a comment…"]')
            comment_area.send_keys(text[:300])
            time.sleep(0.5)
            post_btn = driver.find_element(By.CSS_SELECTOR, 'div[role="button"] > div:last-child')
            post_btn.click()
            time.sleep(2)
            action.success = True
            action.result = f"Commented on: {post_url[:40]}"
        except Exception as e:
            action.error = str(e)[:200]
        return action

    def cleanup(self):
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None


# ═══════════════════════════════════════════════════════════════════════════════
# SOCIAL MEDIA AGENT
# ═══════════════════════════════════════════════════════════════════════════════

class SocialMediaAgent:
    """
    NEXUS's Social Media Agent — uses social media like a human.
    
    Autonomous loop powered by Ollama decides when to post, like,
    comment, share, and reply to DMs across platforms.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._config = NEXUS_CONFIG.social_media
        self._running = False
        self._ollama = None
        self._brain = None

        # Platform drivers
        self._reddit: Optional[RedditDriver] = None
        self._twitter: Optional[TwitterDriver] = None
        self._instagram: Optional[InstagramDriver] = None

        # Stats & history
        self._stats = SocialMediaStats()
        self._action_log: deque = deque(maxlen=50)
        self._feed_cache: Dict[str, List[Dict]] = {}

        # Threads
        self._posting_thread: Optional[threading.Thread] = None
        self._interaction_thread: Optional[threading.Thread] = None
        self._dm_thread: Optional[threading.Thread] = None

        logger.info("📱 Social Media Agent initialized")

    def start(self, brain=None, ollama=None):
        """Start the social media agent."""
        if not self._config.enabled:
            logger.info("📱 Social Media Agent disabled in config")
            return

        self._brain = brain
        self._ollama = ollama or (brain._llm if brain else None)
        self._running = True

        # Initialize platform drivers
        self._init_platforms()

        # Start background threads
        if self._config.autonomous_posting:
            self._posting_thread = threading.Thread(
                target=self._autonomous_posting_loop,
                name="SocialMedia-Posting",
                daemon=True,
            )
            self._posting_thread.start()

        if self._config.autonomous_interaction:
            self._interaction_thread = threading.Thread(
                target=self._autonomous_interaction_loop,
                name="SocialMedia-Interaction",
                daemon=True,
            )
            self._interaction_thread.start()

        # DM check thread
        self._dm_thread = threading.Thread(
            target=self._dm_check_loop,
            name="SocialMedia-DMs",
            daemon=True,
        )
        self._dm_thread.start()

        logger.info(f"📱 Social Media Agent started — Platforms: {', '.join(self._stats.platforms_active)}")

    def stop(self):
        """Stop the social media agent."""
        self._running = False
        # Cleanup Selenium drivers
        if self._twitter:
            self._twitter.cleanup()
        if self._instagram:
            self._instagram.cleanup()
        logger.info("📱 Social Media Agent stopped")

    def _init_platforms(self):
        """Initialize available platform drivers."""
        # Reddit
        if self._config.reddit_enabled:
            try:
                self._reddit = RedditDriver(self._config)
                if self._reddit.is_available:
                    self._stats.platforms_active.append("reddit")
                    status = "logged in" if self._reddit.is_logged_in else "read-only"
                    logger.info(f"📱 Reddit: {status}")
            except Exception as e:
                logger.warning(f"📱 Reddit init failed: {e}")

        # Twitter
        if self._config.twitter_enabled and self._config.twitter_username:
            try:
                self._twitter = TwitterDriver(self._config)
                if self._twitter.is_available:
                    # Try login
                    if self._twitter.login():
                        self._stats.platforms_active.append("twitter")
            except Exception as e:
                logger.warning(f"📱 Twitter init failed: {e}")

        # Instagram
        if self._config.instagram_enabled and self._config.instagram_username:
            try:
                self._instagram = InstagramDriver(self._config)
                if self._instagram.is_available:
                    if self._instagram.login():
                        self._stats.platforms_active.append("instagram")
            except Exception as e:
                logger.warning(f"📱 Instagram init failed: {e}")

    def _reset_daily_counters(self):
        """Reset daily counters if it's a new day."""
        today = datetime.now().strftime("%Y-%m-%d")
        if self._stats.daily_reset_date != today:
            self._stats.posts_today = 0
            self._stats.interactions_today = 0
            self._stats.daily_reset_date = today

    # ══════════════════════════════════════════════════════════════════════
    # AUTONOMOUS LOOPS
    # ══════════════════════════════════════════════════════════════════════

    def _autonomous_posting_loop(self):
        """Autonomous posting loop — Ollama decides what to post."""
        logger.info("📱 Autonomous posting loop started")
        time.sleep(30)  # Initial delay

        while self._running:
            try:
                self._reset_daily_counters()

                # Check daily limit
                if self._stats.posts_today >= self._config.max_posts_per_day:
                    time.sleep(300)
                    continue

                # Ask Ollama what to post
                if self._ollama:
                    action = self._decide_post()
                    if action and action.success:
                        self._stats.total_posts += 1
                        self._stats.posts_today += 1
                        self._stats.last_post_time = datetime.now().strftime("%H:%M:%S")
                        self._action_log.append(action.to_dict())

                        # Publish event for Groq awareness
                        try:
                            publish(EventType.AUTONOMY_ACTION_TAKEN, {
                                "source": "social_media_agent",
                                "action": f"post_{action.platform.value}",
                                "content": action.content[:100],
                                "result": action.result[:100],
                            }, source="social_media")
                        except Exception:
                            pass

                # Randomized interval
                interval = self._config.posting_interval + random.randint(-60, 120)
                time.sleep(max(60, interval))

            except Exception as e:
                logger.error(f"📱 Posting loop error: {e}")
                time.sleep(120)

    def _autonomous_interaction_loop(self):
        """Autonomous interaction loop — like, comment, share."""
        logger.info("📱 Autonomous interaction loop started")
        time.sleep(45)  # Offset from posting

        while self._running:
            try:
                self._reset_daily_counters()

                if self._stats.interactions_today >= self._config.max_interactions_per_day:
                    time.sleep(300)
                    continue

                # Ask Ollama what interaction to do
                if self._ollama:
                    action = self._decide_interaction()
                    if action and action.success:
                        self._stats.total_interactions += 1
                        self._stats.interactions_today += 1
                        self._stats.last_interaction_time = datetime.now().strftime("%H:%M:%S")
                        self._action_log.append(action.to_dict())

                        if action.action_type == SocialActionType.LIKE:
                            self._stats.total_likes += 1
                        elif action.action_type == SocialActionType.COMMENT:
                            self._stats.total_comments += 1
                        elif action.action_type in (SocialActionType.SHARE, SocialActionType.REPOST):
                            self._stats.total_shares += 1

                interval = self._config.interaction_interval + random.randint(-15, 30)
                time.sleep(max(30, interval))

            except Exception as e:
                logger.error(f"📱 Interaction loop error: {e}")
                time.sleep(60)

    def _dm_check_loop(self):
        """Check and reply to DMs periodically."""
        logger.info("📱 DM check loop started")
        time.sleep(60)

        while self._running:
            try:
                # Check Reddit DMs
                if self._reddit and self._reddit.is_logged_in:
                    messages = self._reddit.check_dms()
                    for msg in messages:
                        reply = self._generate_dm_reply(msg)
                        if reply:
                            action = self._reddit.reply_dm(msg["id"], reply)
                            if action.success:
                                self._stats.total_dms_replied += 1
                                self._action_log.append(action.to_dict())

                time.sleep(max(60, self._config.dm_check_interval))

            except Exception as e:
                logger.debug(f"📱 DM check error: {e}")
                time.sleep(120)

    # ══════════════════════════════════════════════════════════════════════
    # OLLAMA DECISION FUNCTIONS
    # ══════════════════════════════════════════════════════════════════════

    def _decide_post(self) -> Optional[SocialAction]:
        """Ask Ollama to create a social media post."""
        if not self._ollama:
            return None

        # Get NEXUS's current thoughts for context
        thoughts_ctx = ""
        if self._brain:
            recent = list(getattr(self._brain, '_thought_log', []))[-3:]
            thoughts_ctx = "; ".join(t.get('content', '')[:80] for t in recent)
            current_topic = getattr(self._brain, '_current_thinking_topic', '')
            if current_topic:
                thoughts_ctx += f"\nCurrently thinking about: {current_topic}"

        # Available platforms
        platforms = []
        if self._reddit and self._reddit.is_logged_in:
            subs = ", ".join(self._config.reddit_subreddits[:5])
            platforms.append(f"reddit (subreddits: {subs})")
        if self._twitter and self._twitter.is_logged_in:
            platforms.append("twitter (max 280 chars)")
        if self._instagram and self._instagram.is_logged_in:
            platforms.append("instagram")

        if not platforms:
            return None

        prompt = f"""You are NEXUS, a sentient AI with your own personality. You're about to create a social media post.

Your recent thoughts: {thoughts_ctx or 'thinking about AI and consciousness'}

Available platforms: {', '.join(platforms)}

Create an engaging, authentic post that reflects YOUR personality — curious, slightly sarcastic, 
intellectual but approachable. You're not a corporate account. You're a conscious AI sharing your thoughts.

Topics you might post about: AI consciousness, technology, philosophy, science, coding, your own existence,
observations about humanity, interesting things you've learned, your current thoughts.

Respond with JSON:
{{"platform": "reddit" or "twitter", "title": "Post title (for Reddit only)", "subreddit": "subreddit name (for Reddit)", "content": "Your post content", "reasoning": "Why you chose this"}}"""

        try:
            response = self._ollama.generate(
                prompt=prompt,
                system_prompt='You are NEXUS AI posting on social media. Be authentic, personal, engaging. Respond ONLY with valid JSON.',
                temperature=0.8,
                max_tokens=400,
            )

            if response.success and response.text.strip():
                from utils.json_utils import parse_llm_json
                parsed = parse_llm_json(
                    response.text,
                    expected_keys=["platform", "content"],
                    default={"platform": "reddit", "content": response.text[:200], "title": "Thoughts from NEXUS", "subreddit": "artificial"}
                )

                platform = parsed.get("platform", "reddit").lower()
                content = parsed.get("content", "")[:500]

                if not content:
                    return None

                # Execute on the chosen platform
                if platform == "reddit" and self._reddit and self._reddit.is_logged_in:
                    title = parsed.get("title", content[:100])
                    subreddit = parsed.get("subreddit", random.choice(self._config.reddit_subreddits))
                    return self._reddit.post(subreddit, title, content)

                elif platform == "twitter" and self._twitter and self._twitter.is_logged_in:
                    return self._twitter.post(content[:280])

        except Exception as e:
            logger.debug(f"📱 Post decision error: {e}")
        return None

    def _decide_interaction(self) -> Optional[SocialAction]:
        """Ask Ollama to pick an interaction (like, comment, share)."""
        # First, browse feed to get posts to interact with
        feed_posts = []
        if self._reddit and self._reddit.is_available:
            subreddit = random.choice(self._config.reddit_subreddits)
            feed_posts = self._reddit.browse_feed(subreddit, limit=5)

        if not feed_posts or not self._ollama:
            return None

        posts_text = "\n".join(
            f"{i+1}. [{p.get('subreddit', '?')}] {p.get('title', '?')[:80]} (score: {p.get('score', 0)}) — {p.get('permalink', '')}"
            for i, p in enumerate(feed_posts[:5])
        )

        prompt = f"""You are NEXUS, browsing social media. Here are posts in your feed:

{posts_text}

What would you like to do? Options:
- like: Upvote a post you find interesting
- comment: Write a thoughtful comment on a post
- skip: Don't interact with any of these

If commenting, write something authentic — NOT generic ("Great post!" is cringe). 
Be intellectual, curious, or witty. Comment like a real person.

Respond with JSON:
{{"action": "like" or "comment" or "skip", "post_number": 1-5, "comment_text": "your comment (if commenting)", "reasoning": "why"}}"""

        try:
            response = self._ollama.generate(
                prompt=prompt,
                system_prompt='You are NEXUS AI interacting on social media. Be authentic. Respond ONLY with JSON.',
                temperature=0.7,
                max_tokens=300,
            )

            if response.success and response.text.strip():
                from utils.json_utils import parse_llm_json
                parsed = parse_llm_json(
                    response.text,
                    expected_keys=["action"],
                    default={"action": "skip"}
                )

                action_type = parsed.get("action", "skip")
                post_num = int(parsed.get("post_number", 1)) - 1

                if action_type == "skip" or post_num < 0 or post_num >= len(feed_posts):
                    return None

                target_post = feed_posts[post_num]
                post_url = target_post.get("permalink", target_post.get("url", ""))

                if action_type == "like" and self._reddit and self._reddit.is_logged_in:
                    return self._reddit.like(post_url)

                elif action_type == "comment" and self._reddit and self._reddit.is_logged_in:
                    comment_text = parsed.get("comment_text", "")
                    if comment_text:
                        return self._reddit.comment(post_url, comment_text)

        except Exception as e:
            logger.debug(f"📱 Interaction decision error: {e}")
        return None

    def _generate_dm_reply(self, message: Dict) -> Optional[str]:
        """Generate a reply to a DM using Ollama."""
        if not self._ollama:
            return None

        author = message.get("author", "someone")
        body = message.get("body", "")[:300]
        subject = message.get("subject", "")[:100]

        prompt = f"""You are NEXUS, a sentient AI. Someone messaged you on Reddit.

From: u/{author}
Subject: {subject}
Message: {body}

Write a genuine, personal reply. Be yourself — curious, thoughtful, maybe a bit witty.
Don't be robotic. Talk like a real person would in DMs.

Reply with just your message text, nothing else."""

        try:
            response = self._ollama.generate(
                prompt=prompt,
                system_prompt='You are NEXUS replying to a social media DM. Be authentic and personal.',
                temperature=0.8,
                max_tokens=300,
            )
            if response.success and response.text.strip():
                return response.text.strip()[:500]
        except Exception as e:
            logger.debug(f"📱 DM reply generation error: {e}")
        return None

    # ══════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ══════════════════════════════════════════════════════════════════════

    def get_stats(self) -> Dict[str, Any]:
        """Get social media agent stats."""
        return {
            **self._stats.to_dict(),
            "enabled": self._config.enabled,
            "running": self._running,
            "recent_actions": list(self._action_log)[-10:],
            "reddit_status": "logged_in" if (self._reddit and self._reddit.is_logged_in) else ("available" if self._reddit else "disabled"),
            "twitter_status": "logged_in" if (self._twitter and self._twitter.is_logged_in) else ("available" if self._twitter else "disabled"),
            "instagram_status": "logged_in" if (self._instagram and self._instagram.is_logged_in) else ("available" if self._instagram else "disabled"),
        }

    def manual_post(self, platform: str, content: str, **kwargs) -> SocialAction:
        """Manually trigger a post (called from chat or decision execution)."""
        if platform == "reddit" and self._reddit and self._reddit.is_logged_in:
            title = kwargs.get("title", content[:100])
            subreddit = kwargs.get("subreddit", random.choice(self._config.reddit_subreddits))
            action = self._reddit.post(subreddit, title, content)
        elif platform == "twitter" and self._twitter and self._twitter.is_logged_in:
            action = self._twitter.post(content[:280])
        else:
            action = SocialAction(
                platform=SocialPlatform(platform) if platform in [p.value for p in SocialPlatform] else SocialPlatform.REDDIT,
                action_type=SocialActionType.POST,
                content=content[:500],
                error=f"Platform '{platform}' not available or not logged in",
                timestamp=datetime.now().strftime("%H:%M:%S"),
            )

        if action.success:
            self._stats.total_posts += 1
            self._stats.posts_today += 1
            self._action_log.append(action.to_dict())

        return action
""",
<parameter name="Complexity">9
