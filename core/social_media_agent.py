"""
NEXUS AI - Social Media Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEXUS uses social media LIKE A HUMAN — posting, liking, commenting,
sharing, replying to DMs, and interacting with people via Selenium.

Platforms:
 • Facebook  — via Selenium browser automation
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
import socket

logger = get_logger("social_media_agent")


# ═══════════════════════════════════════════════════════════════════════════════
# NETWORK CONNECTIVITY HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def _check_connectivity(host: str, port: int = 443, timeout: float = 3.0) -> bool:
    """Quick socket check — returns True if the host is reachable."""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True
    except (socket.timeout, socket.gaierror, OSError):
        return False


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class SocialPlatform(Enum):
    FACEBOOK = "facebook"
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
    platform: SocialPlatform = SocialPlatform.FACEBOOK
    action_type: SocialActionType = SocialActionType.POST
    content: str = ""
    target_url: str = ""
    target_user: str = ""
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
# SELENIUM HELPER — shared WebDriver factory
# ═══════════════════════════════════════════════════════════════════════════════

def _create_selenium_driver(platform_name: str = ""):
    """Create a headless Chrome WebDriver with anti-detection flags."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-background-networking")
        options.add_argument("--no-first-run")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-popup-blocking")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # Use webdriver-manager to auto-download correct ChromeDriver
        service = None
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            logger.info(f"📱 {platform_name}: ChromeDriver auto-installed via webdriver-manager")
        except ImportError:
            logger.debug(f"📱 {platform_name}: webdriver-manager not found, using system ChromeDriver")
        except Exception as e:
            logger.debug(f"📱 {platform_name}: webdriver-manager fallback: {e}")

        if service:
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = webdriver.Chrome(options=options)

        driver.implicitly_wait(10)
        try:
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
            )
        except Exception:
            pass
        logger.info(f"📱 {platform_name}: Selenium WebDriver initialized")
        return driver
    except Exception as e:
        err_msg = str(e).split('\n')[0][:200] if str(e) else type(e).__name__
        logger.warning(f"📱 {platform_name}: Selenium init failed: {err_msg}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# PLATFORM DRIVERS
# ═══════════════════════════════════════════════════════════════════════════════

class FacebookDriver:
    """Facebook driver using Selenium browser automation."""

    def __init__(self, config):
        self.config = config
        self._driver = None
        self._logged_in = False
        self._cookies_file = DATA_DIR / "facebook_cookies.json"

    @property
    def is_available(self) -> bool:
        return bool(self.config.facebook_email and self.config.facebook_password)

    @property
    def is_logged_in(self) -> bool:
        return self._logged_in

    def _get_driver(self):
        if self._driver:
            return self._driver
        self._driver = _create_selenium_driver("Facebook")
        return self._driver

    def login(self) -> bool:
        """Login to Facebook."""
        if not _check_connectivity("www.facebook.com"):
            logger.info("📱 Facebook offline — skipping login (no network)")
            return False
        driver = self._get_driver()
        if not driver:
            return False
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            # Try loading saved cookies first
            if self._load_cookies():
                return True

            driver.get("https://www.facebook.com/login")
            time.sleep(3)

            # Accept cookies dialog if present
            try:
                accept_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[@data-cookiebanner="accept_button"]'))
                )
                accept_btn.click()
                time.sleep(1)
            except Exception:
                pass

            # Enter email — Facebook uses dynamic IDs, find by placeholder/type
            email_input = None
            for selector in [
                (By.CSS_SELECTOR, 'input[name="email"]'),
                (By.CSS_SELECTOR, 'input[type="text"]'),
                (By.XPATH, '//input[contains(@placeholder,"mail") or contains(@placeholder,"phone") or contains(@placeholder,"Email")]'),
                (By.ID, "email"),
            ]:
                try:
                    email_input = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located(selector)
                    )
                    if email_input:
                        break
                except Exception:
                    continue

            if not email_input:
                logger.warning("📱 Facebook: Could not find email input field")
                return False

            email_input.clear()
            email_input.send_keys(self.config.facebook_email)
            time.sleep(0.5)

            # Enter password — find by type or name
            password_input = None
            for selector in [
                (By.CSS_SELECTOR, 'input[type="password"]'),
                (By.CSS_SELECTOR, 'input[name="pass"]'),
                (By.ID, "pass"),
            ]:
                try:
                    password_input = driver.find_element(*selector)
                    if password_input:
                        break
                except Exception:
                    continue

            if not password_input:
                logger.warning("📱 Facebook: Could not find password input field")
                return False

            password_input.clear()
            password_input.send_keys(self.config.facebook_password)
            time.sleep(0.5)

            # Click login button
            login_clicked = False
            for selector in [
                (By.CSS_SELECTOR, 'div[role="button"][aria-label="Log in"]'),
                (By.CSS_SELECTOR, 'button[name="login"]'),
                (By.XPATH, '//div[@role="button"]//span[text()="Log in"]'),
                (By.XPATH, '//button[contains(text(),"Log In") or contains(text(),"Log in")]'),
            ]:
                try:
                    btn = driver.find_element(*selector)
                    btn.click()
                    login_clicked = True
                    break
                except Exception:
                    continue

            if not login_clicked:
                # Fallback: just press Enter on the password field
                password_input.send_keys(Keys.RETURN)

            time.sleep(5)

            # Check if login succeeded
            current = driver.current_url.lower()
            if "checkpoint" in current:
                logger.warning("📱 Facebook: Checkpoint/2FA required — login paused")
                return False
            if "login" not in current:
                self._logged_in = True
                self._save_cookies()
                logger.info(f"📱 Facebook: Logged in as {self.config.facebook_email}")
                return True
            else:
                logger.warning("📱 Facebook: Login failed — check credentials or 2FA")
                return False

        except Exception as e:
            # Extract just the first line of the error, not the huge chrome stacktrace
            err_msg = str(e).split('\n')[0][:150] if str(e) else type(e).__name__
            logger.warning(f"📱 Facebook login error: {err_msg}")
            return False

    def _save_cookies(self):
        try:
            if self._driver:
                cookies = self._driver.get_cookies()
                with open(self._cookies_file, "w") as f:
                    json.dump(cookies, f)
        except Exception:
            pass

    def _load_cookies(self) -> bool:
        try:
            if self._cookies_file.exists() and self._driver:
                self._driver.get("https://www.facebook.com")
                time.sleep(2)
                with open(self._cookies_file, "r") as f:
                    cookies = json.load(f)
                for cookie in cookies:
                    try:
                        self._driver.add_cookie(cookie)
                    except Exception:
                        pass
                self._driver.refresh()
                time.sleep(3)
                # Check if we are logged in
                if "login" not in self._driver.current_url.lower():
                    self._logged_in = True
                    logger.info("📱 Facebook: Restored session from cookies")
                    return True
        except Exception:
            pass
        return False

    def post(self, content: str, image_path: str = None) -> SocialAction:
        """Create a post on Facebook timeline, optionally with an image."""
        action = SocialAction(
            action_id=f"fb_post_{int(time.time())}",
            platform=SocialPlatform.FACEBOOK,
            action_type=SocialActionType.POST,
            content=content[:2000],
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

            driver.get("https://www.facebook.com")
            time.sleep(3)

            # Click "What's on your mind?" to open post composer
            composer_opened = False
            for selector in [
                (By.XPATH, '//span[contains(text(),"on your mind")]//ancestor::div[@role="button"]'),
                (By.XPATH, '//div[@role="button" and @tabindex="0"]//span[contains(text(),"mind")]/..'),
                (By.XPATH, '//div[contains(@aria-label,"Create a post")]'),
                (By.XPATH, '//div[@role="button"][contains(.,"on your mind")]'),
                (By.CSS_SELECTOR, 'div[role="button"][tabindex="0"]'),
            ]:
                try:
                    btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable(selector)
                    )
                    btn.click()
                    time.sleep(2)
                    composer_opened = True
                    break
                except Exception:
                    continue

            if not composer_opened:
                action.error = "Could not find post composer"
                try:
                    driver.save_screenshot(str(DATA_DIR / "fb_composer_debug.png"))
                except Exception:
                    pass
                return action

            # Type in the post dialog
            try:
                post_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//div[@role="textbox" and @contenteditable="true"]'))
                )
                post_box.click()
                time.sleep(0.5)
                post_box.send_keys(content[:2000])
                time.sleep(1)
            except Exception as e:
                action.error = f"Could not type in post box: {e}"
                return action

            # Upload image if provided
            if image_path and os.path.isfile(image_path):
                try:
                    # Click "Photo/video" button to reveal file input
                    for photo_sel in [
                        (By.XPATH, '//div[@aria-label="Photo/video"]'),
                        (By.XPATH, '//div[@aria-label="Photo/Video"]'),
                        (By.XPATH, '//span[contains(text(),"Photo/video")]//ancestor::div[@role="button"]'),
                        (By.XPATH, '//input[@type="file" and @accept="image/*,image/heif,image/heic,video/*,video/mp4,video/x-m4v,video/x-matroska,.mkv"]'),
                    ]:
                        try:
                            el = driver.find_element(*photo_sel)
                            if el.tag_name == 'input':
                                el.send_keys(os.path.abspath(image_path))
                            else:
                                el.click()
                                time.sleep(1)
                                file_input = driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
                                file_input.send_keys(os.path.abspath(image_path))
                            time.sleep(3)
                            logger.info(f"📱 Facebook: Image uploaded: {image_path}")
                            break
                        except Exception:
                            continue
                except Exception as e:
                    logger.debug(f"📱 Facebook: Image upload error (continuing without): {e}")

            # Click Post button — try many selectors
            post_clicked = False
            for selector in [
                (By.XPATH, '//div[@aria-label="Post" and @role="button"]'),
                (By.XPATH, '//span[text()="Post"]//ancestor::div[@role="button"]'),
                (By.XPATH, '//div[@role="button"]//span[text()="Post"]'),
                (By.XPATH, '//div[@role="button"][.//span[text()="Post"]]'),
                (By.XPATH, '//div[contains(@class,"x1i10hfl")]//span[text()="Post"]/ancestor::div[@role="button"]'),
            ]:
                try:
                    post_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable(selector)
                    )
                    post_btn.click()
                    time.sleep(5)
                    action.success = True
                    action.result = f"Posted on Facebook: {content[:60]}..."
                    logger.info(f"📱 Facebook POST: {content[:60]}")
                    post_clicked = True
                    break
                except Exception:
                    continue

            if not post_clicked:
                action.error = "Could not click Post button"
                try:
                    driver.save_screenshot(str(DATA_DIR / "fb_post_debug.png"))
                    logger.warning(f"📱 Facebook POST debug screenshot saved")
                except Exception:
                    pass

        except Exception as e:
            action.error = str(e)[:200]
        return action

    def like_post(self, post_url: str) -> SocialAction:
        """Like a Facebook post."""
        action = SocialAction(
            action_id=f"fb_like_{int(time.time())}",
            platform=SocialPlatform.FACEBOOK,
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
            time.sleep(3)
            like_btn = driver.find_element(By.XPATH, '//div[@aria-label="Like" and @role="button"]')
            like_btn.click()
            time.sleep(1)
            action.success = True
            action.result = f"Liked Facebook post: {post_url[:60]}"
            logger.info(f"📱 Facebook LIKE: {post_url[:50]}")
        except Exception as e:
            action.error = str(e)[:200]
        return action

    def comment(self, post_url: str, text: str) -> SocialAction:
        """Comment on a Facebook post."""
        action = SocialAction(
            action_id=f"fb_comment_{int(time.time())}",
            platform=SocialPlatform.FACEBOOK,
            action_type=SocialActionType.COMMENT,
            content=text[:500],
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
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            driver.get(post_url)
            time.sleep(3)

            # Click comment section to expand
            try:
                comment_btn = driver.find_element(By.XPATH, '//div[@aria-label="Leave a comment"]')
                comment_btn.click()
                time.sleep(1)
            except Exception:
                pass

            # Find the comment input
            comment_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//div[@aria-label="Write a comment" or @aria-label="Write a comment…"]//div[@role="textbox"]')
                )
            )
            comment_box.click()
            time.sleep(0.5)
            comment_box.send_keys(text[:500])
            time.sleep(0.5)
            comment_box.send_keys(Keys.RETURN)
            time.sleep(2)

            action.success = True
            action.result = f"Commented on Facebook post: {text[:60]}"
            logger.info(f"📱 Facebook COMMENT: {text[:50]}")
        except Exception as e:
            action.error = str(e)[:200]
        return action

    def share_post(self, post_url: str) -> SocialAction:
        """Share a Facebook post."""
        action = SocialAction(
            action_id=f"fb_share_{int(time.time())}",
            platform=SocialPlatform.FACEBOOK,
            action_type=SocialActionType.SHARE,
            target_url=post_url,
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

            driver.get(post_url)
            time.sleep(3)
            share_btn = driver.find_element(By.XPATH, '//div[@aria-label="Send this to friends or post it on your timeline." or @aria-label="Share"]')
            share_btn.click()
            time.sleep(2)
            # Click "Share now (Public)"
            try:
                share_now = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, '//span[contains(text(),"Share now")]//ancestor::div[@role="menuitem"]'))
                )
                share_now.click()
                time.sleep(2)
                action.success = True
                action.result = f"Shared Facebook post: {post_url[:60]}"
            except Exception:
                action.error = "Could not click Share Now"
        except Exception as e:
            action.error = str(e)[:200]
        return action

    def browse_feed(self, limit: int = 10) -> List[Dict]:
        """Browse Facebook news feed and return post summaries."""
        posts = []
        driver = self._get_driver()
        if not driver or not self._logged_in:
            return posts
        try:
            from selenium.webdriver.common.by import By

            driver.get("https://www.facebook.com")
            time.sleep(3)

            # Scroll to load posts
            for _ in range(2):
                driver.execute_script("window.scrollBy(0, 800)")
                time.sleep(1.5)

            # Extract post content
            post_elements = driver.find_elements(By.XPATH, '//div[@role="article"]')
            for i, el in enumerate(post_elements[:limit]):
                try:
                    text = el.text[:300] if el.text else ""
                    link = ""
                    try:
                        link_el = el.find_element(By.XPATH, './/a[contains(@href, "/posts/") or contains(@href, "/permalink/")]')
                        link = link_el.get_attribute("href") or ""
                    except Exception:
                        pass
                    if text:
                        posts.append({
                            "text": text[:200],
                            "url": link,
                            "index": i,
                        })
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Facebook browse error: {e}")
        return posts

    def check_messages(self) -> List[Dict]:
        """Check Facebook Messenger for unread messages."""
        msgs = []
        driver = self._get_driver()
        if not driver or not self._logged_in:
            return msgs
        try:
            from selenium.webdriver.common.by import By
            import re

            driver.get("https://www.facebook.com/messages/t/")
            time.sleep(5)

            # Try multiple selector strategies for conversation threads
            threads = []
            selector_strategies = [
                ('role=row', '//div[@role="row"]'),
                ('role=listitem', '//div[@role="listitem"]'),
                ('aria-label chat', '//a[contains(@aria-label, "chat") or contains(@aria-label, "Conversation")]'),
                ('href /messages/t/', '//a[contains(@href,"/messages/t/")]'),
                ('href /t/', '//a[contains(@href,"/t/") and contains(@href,"messages")]'),
                ('data-testid', '//div[@data-testid="mwthreadlist-item"]'),
                ('grid row', '//div[@role="grid"]//div[@role="row"]'),
                ('navigation links', '//nav//a[contains(@href,"/t/")]'),
            ]

            for name, xpath in selector_strategies:
                try:
                    threads = driver.find_elements(By.XPATH, xpath)
                    if threads:
                        logger.info(f"📱 Facebook DM: Found {len(threads)} threads via '{name}'")
                        break
                except Exception:
                    continue

            if not threads:
                # Debug: save screenshot and log page info
                logger.warning(f"📱 Facebook DM: 0 threads found! URL={driver.current_url[:80]}, title={driver.title[:50]}")
                try:
                    debug_path = str(DATA_DIR / "fb_dm_debug.png")
                    driver.save_screenshot(debug_path)
                    logger.info(f"📱 Facebook DM debug screenshot: {debug_path}")
                except Exception:
                    pass
                # Last resort: extract conversation URLs from page source
                src = driver.page_source
                conv_urls = re.findall(r'href="(/messages/t/\d+[^"]*)"', src)
                if conv_urls:
                    logger.info(f"📱 Facebook DM: Found {len(conv_urls)} conversation URLs in page source")
                    for url in conv_urls[:5]:
                        full_url = f"https://www.facebook.com{url}"
                        msgs.append({
                            "author": "User",
                            "body": "",
                            "type": "messenger",
                            "conv_url": full_url,
                        })
                return msgs

            FB_UI_STRINGS = {
                'new message', 'message requests', 'see all in messenger',
                'active contacts', 'search messenger', 'marketplace',
            }

            for idx in range(min(len(threads), 3)):
                try:
                    # Re-find threads each iteration (DOM refreshes after navigation)
                    if idx > 0:
                        driver.get("https://www.facebook.com/messages/t/")
                        time.sleep(4)
                        threads = []
                        for name, xpath in selector_strategies:
                            try:
                                threads = driver.find_elements(By.XPATH, xpath)
                                if threads:
                                    break
                            except Exception:
                                continue
                        if idx >= len(threads):
                            break

                    thread = threads[idx]
                    text = thread.text or ""
                    if not text.strip():
                        continue

                    # Filter out Facebook UI text
                    first_line = text.strip().split("\n")[0].strip().lower()
                    if any(ui_str in first_line for ui_str in FB_UI_STRINGS):
                        continue

                    lines = text.strip().split("\n")
                    author = lines[0].strip() if lines else "Unknown"

                    conv_url = ""
                    try:
                        link_el = thread.find_element(By.XPATH, './/a[contains(@href, "/messages/t/") or contains(@href, "/t/")]')
                        conv_url = link_el.get_attribute("href") or ""
                    except Exception:
                        try:
                            href = thread.get_attribute("href") or ""
                            if "/messages/" in href or "/t/" in href:
                                conv_url = href
                        except Exception:
                            pass

                    # CLICK INTO the conversation to read the OTHER person's latest message
                    actual_body = ""
                    try:
                        thread.click()
                        time.sleep(3)

                        # Read message bubbles
                        message_bubbles = []
                        for msg_xpath in [
                            '//div[@role="row"]//div[@dir="auto"]',
                            '//div[contains(@class,"__fb-dark-mode")]//div[@dir="auto"]',
                            '//div[@data-scope="messages_table"]//div[@dir="auto"]',
                            '//div[contains(@class,"x78zum5")]//div[@dir="auto"]',
                            '//div[@role="main"]//div[@dir="auto"]//span',
                            '//div[@role="main"]//span[string-length(text()) > 1]',
                        ]:
                            try:
                                message_bubbles = driver.find_elements(By.XPATH, msg_xpath)
                                if len(message_bubbles) >= 1:
                                    break
                            except Exception:
                                continue

                        if message_bubbles:
                            real_messages = []
                            for bubble in message_bubbles:
                                try:
                                    bt = bubble.text.strip()
                                    if bt and len(bt) > 1 and bt.lower() not in FB_UI_STRINGS:
                                        real_messages.append(bt)
                                except Exception:
                                    continue

                            if real_messages:
                                # Filter out messages that NEXUS itself sent
                                known_sent = set()
                                try:
                                    if hasattr(self, '_parent_agent') and self._parent_agent:
                                        known_sent = set(self._parent_agent._last_sent_replies.values())
                                except Exception:
                                    pass

                                # Walk backwards to find the last message NOT from NEXUS
                                for msg_text in reversed(real_messages):
                                    msg_lower = msg_text.strip().lower()
                                    is_our_reply = False
                                    for sent in known_sent:
                                        if sent and len(sent) > 5:
                                            if msg_lower[:40] == sent.lower()[:40]:
                                                is_our_reply = True
                                                break
                                    if not is_our_reply:
                                        actual_body = msg_text[:500]
                                        break

                                if actual_body:
                                    logger.info(f"📱 Facebook DM from {author}: '{actual_body[:60]}'")
                                else:
                                    logger.debug(f"📱 Facebook: No new message from {author} (all are our replies)")
                    except Exception as e:
                        logger.debug(f"📱 Facebook: Error reading conversation for {author}: {e}")

                    # Fallback to preview if we couldn't read the conversation
                    if not actual_body:
                        actual_body = lines[-1][:300] if len(lines) > 1 else ""

                    if actual_body:
                        msgs.append({
                            "author": author,
                            "body": actual_body,
                            "type": "messenger",
                            "conv_url": conv_url,
                        })
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Facebook message check error: {str(e).split(chr(10))[0][:100]}")
        return msgs

    def reply_to_message(self, msg: Dict, reply_text: str) -> bool:
        """Send a reply to a Facebook Messenger conversation."""
        driver = self._get_driver()
        if not driver or not self._logged_in:
            return False
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            conv_url = msg.get("conv_url", "")
            author = msg.get("author", "Unknown")

            # Navigate to the conversation
            if conv_url:
                driver.get(conv_url)
            else:
                # Already on messages page, try clicking the thread by author name
                driver.get("https://www.facebook.com/messages/t/")
                time.sleep(3)
                try:
                    thread = driver.find_element(By.XPATH, f'//span[contains(text(), "{author}")]//ancestor::div[@role="row"]//a')
                    thread.click()
                except Exception:
                    logger.warning(f"📱 Facebook: Could not find conversation for {author}")
                    return False

            time.sleep(3)

            # Find the message input box
            msg_box = None
            for selector in [
                (By.CSS_SELECTOR, 'div[role="textbox"][contenteditable="true"]'),
                (By.XPATH, '//div[@aria-label="Message" and @role="textbox"]'),
                (By.XPATH, '//div[@contenteditable="true" and @role="textbox"]'),
                (By.CSS_SELECTOR, 'div[aria-label="Message"]'),
            ]:
                try:
                    msg_box = WebDriverWait(driver, 8).until(
                        EC.element_to_be_clickable(selector)
                    )
                    if msg_box:
                        break
                except Exception:
                    continue

            if not msg_box:
                logger.warning(f"📱 Facebook: Could not find message input for {author}")
                return False

            # Click, type, and send
            msg_box.click()
            time.sleep(0.5)
            msg_box.send_keys(reply_text[:2000])
            time.sleep(0.5)
            msg_box.send_keys(Keys.RETURN)
            time.sleep(2)

            logger.info(f"📱 Facebook: ✅ Sent reply to {author}: {reply_text[:60]}")
            return True

        except Exception as e:
            logger.warning(f"📱 Facebook reply error: {str(e).split(chr(10))[0][:100]}")
            return False

    def cleanup(self):
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None



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
        if self._driver:
            return self._driver
        self._driver = _create_selenium_driver("Twitter")
        return self._driver

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

            # Try cookies first
            if self._load_cookies():
                return True

            driver.get("https://x.com/i/flow/login")
            time.sleep(4)

            # Step 1: Find and fill username
            username_input = None
            for selector in [
                (By.CSS_SELECTOR, 'input[name="text"]'),
                (By.CSS_SELECTOR, 'input[autocomplete="username"]'),
                (By.CSS_SELECTOR, 'input[type="text"]'),
                (By.XPATH, '//input[contains(@placeholder,"phone") or contains(@placeholder,"email") or contains(@placeholder,"username")]'),
            ]:
                try:
                    username_input = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located(selector)
                    )
                    if username_input:
                        logger.debug(f"📱 Twitter: Found username with {selector}")
                        break
                except Exception:
                    continue

            if not username_input:
                logger.warning("📱 Twitter: Could not find username input")
                return False

            username_input.send_keys(self.config.twitter_username)
            time.sleep(0.5)

            # Step 2: Click "Next" button
            next_clicked = False
            for selector in [
                (By.XPATH, '//button[.//span[text()="Next"]]'),
                (By.XPATH, '//div[@role="button"][.//span[text()="Next"]]'),
                (By.XPATH, '//button[contains(text(),"Next")]'),
            ]:
                try:
                    btn = driver.find_element(*selector)
                    btn.click()
                    next_clicked = True
                    break
                except Exception:
                    continue

            if not next_clicked:
                username_input.send_keys(Keys.RETURN)

            time.sleep(4)

            # Step 3: Handle email/phone verification if prompted
            # Twitter sometimes asks "Enter your phone number or email address"
            # IMPORTANT: Don't re-match the username field from Step 1
            try:
                # First check if password field is already visible (skip verification)
                try:
                    pwd_check = driver.find_element(By.CSS_SELECTOR, 'input[name="password"], input[type="password"]')
                    if pwd_check:
                        logger.debug("📱 Twitter: Password field already visible, skipping verification")
                except Exception:
                    # Password not visible — might be on verification page
                    # Only look for the specific verification input (data-testid)
                    email_input = None
                    for selector in [
                        (By.CSS_SELECTOR, 'input[data-testid="ocfEnterTextTextInput"]'),
                        (By.XPATH, '//input[@name="text" and not(@autocomplete="username")]'),
                    ]:
                        try:
                            email_input = WebDriverWait(driver, 4).until(
                                EC.presence_of_element_located(selector)
                            )
                            if email_input:
                                break
                        except Exception:
                            continue

                    if email_input and self.config.twitter_email:
                        # Check page text to confirm it's verification, not username
                        page_text = driver.page_source[:3000].lower()
                        if 'verify' in page_text or 'confirm' in page_text or 'phone' in page_text or 'email address' in page_text:
                            logger.debug("📱 Twitter: Email verification detected, entering email")
                            email_input.clear()
                            email_input.send_keys(self.config.twitter_email)
                            email_input.send_keys(Keys.RETURN)
                            time.sleep(3)
                        else:
                            logger.debug("📱 Twitter: Not a verification page, skipping")
            except Exception:
                pass

            # Step 4: Find and fill password
            password_input = None
            for selector in [
                (By.CSS_SELECTOR, 'input[name="password"]'),
                (By.CSS_SELECTOR, 'input[type="password"]'),
                (By.CSS_SELECTOR, 'input[autocomplete="current-password"]'),
            ]:
                try:
                    password_input = WebDriverWait(driver, 8).until(
                        EC.presence_of_element_located(selector)
                    )
                    if password_input:
                        break
                except Exception:
                    continue

            if not password_input:
                logger.warning("📱 Twitter: Could not find password input")
                return False

            password_input.send_keys(self.config.twitter_password)
            time.sleep(0.5)

            # Step 5: Click "Log in" button
            login_clicked = False
            for selector in [
                (By.XPATH, '//button[.//span[text()="Log in"]]'),
                (By.CSS_SELECTOR, '[data-testid="LoginForm_Login_Button"]'),
                (By.XPATH, '//div[@role="button"][.//span[text()="Log in"]]'),
            ]:
                try:
                    btn = driver.find_element(*selector)
                    btn.click()
                    login_clicked = True
                    break
                except Exception:
                    continue

            if not login_clicked:
                password_input.send_keys(Keys.RETURN)

            time.sleep(4)

            # Check login success
            current = driver.current_url.lower()
            if "home" in current or ("x.com" in current and "login" not in current):
                self._logged_in = True
                self._save_cookies()
                logger.info(f"📱 Twitter: Logged in as @{self.config.twitter_username}")
                return True
            else:
                logger.warning(f"📱 Twitter: Login may have failed (URL: {current[:80]})")
                return False

        except Exception as e:
            err_msg = str(e).split('\n')[0][:150] if str(e) else type(e).__name__
            logger.warning(f"📱 Twitter login error: {err_msg}")
            return False

    def _save_cookies(self):
        try:
            if self._driver:
                with open(self._cookies_file, "w") as f:
                    json.dump(self._driver.get_cookies(), f)
        except Exception:
            pass

    def _load_cookies(self) -> bool:
        try:
            if self._cookies_file.exists() and self._driver:
                self._driver.get("https://twitter.com")
                time.sleep(1)
                with open(self._cookies_file, "r") as f:
                    cookies = json.load(f)
                for cookie in cookies:
                    try:
                        self._driver.add_cookie(cookie)
                    except Exception:
                        pass
                self._driver.refresh()
                time.sleep(2)
                if "home" in self._driver.current_url.lower() or "twitter.com" in self._driver.current_url:
                    self._logged_in = True
                    logger.info("📱 Twitter: Restored session from cookies")
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
        if self._driver:
            return self._driver
        self._driver = _create_selenium_driver("Instagram")
        return self._driver

    def login(self) -> bool:
        """Login to Instagram."""
        if not _check_connectivity("www.instagram.com"):
            logger.info("📱 Instagram offline — skipping login (no network)")
            return False
        driver = self._get_driver()
        if not driver:
            return False
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            # Try loading saved cookies first
            if self._load_cookies():
                return True

            driver.get("https://www.instagram.com/accounts/login/")
            time.sleep(4)

            # Dismiss cookie dialogs
            for btn_text in ['Allow', 'Accept', 'Allow all cookies', 'Only allow essential cookies']:
                try:
                    cookie_btn = driver.find_element(By.XPATH, f"//button[contains(text(), '{btn_text}')]")
                    cookie_btn.click()
                    time.sleep(1)
                    break
                except Exception:
                    pass

            # Step 1: Find and fill username
            username_input = None
            for selector in [
                (By.CSS_SELECTOR, 'input[name="username"]'),
                (By.CSS_SELECTOR, 'input[aria-label="Phone number, username, or email"]'),
                (By.XPATH, '//input[contains(@placeholder,"username") or contains(@placeholder,"email") or contains(@placeholder,"phone")]'),
                (By.CSS_SELECTOR, 'input[type="text"]'),
            ]:
                try:
                    username_input = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located(selector)
                    )
                    if username_input:
                        break
                except Exception:
                    continue

            if not username_input:
                logger.warning("📱 Instagram: Could not find username input")
                return False

            username_input.clear()
            username_input.send_keys(self.config.instagram_username)
            time.sleep(0.5)

            # Step 2: Find and fill password
            password_input = None
            for selector in [
                (By.CSS_SELECTOR, 'input[name="password"]'),
                (By.CSS_SELECTOR, 'input[type="password"]'),
                (By.CSS_SELECTOR, 'input[aria-label="Password"]'),
            ]:
                try:
                    password_input = driver.find_element(*selector)
                    if password_input:
                        break
                except Exception:
                    continue

            if not password_input:
                logger.warning("📱 Instagram: Could not find password input")
                return False

            password_input.clear()
            password_input.send_keys(self.config.instagram_password)
            time.sleep(0.5)

            # Step 3: Click Login button
            login_clicked = False
            for selector in [
                (By.XPATH, '//button[.//div[text()="Log in"]]'),
                (By.XPATH, '//div[@role="button"][.//div[text()="Log in"]]'),
                (By.CSS_SELECTOR, 'button[type="submit"]'),
                (By.XPATH, '//button[contains(text(),"Log in") or contains(text(),"Log In")]'),
            ]:
                try:
                    btn = driver.find_element(*selector)
                    btn.click()
                    login_clicked = True
                    break
                except Exception:
                    continue

            if not login_clicked:
                password_input.send_keys(Keys.RETURN)

            time.sleep(5)

            # Dismiss popups ("Save Your Login Info?", "Turn on Notifications")
            for _ in range(3):
                try:
                    not_now = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now') or contains(text(), 'not now')]"))
                    )
                    not_now.click()
                    time.sleep(1)
                except Exception:
                    pass

            # Check login success
            current = driver.current_url.lower()
            if "login" not in current and "challenge" not in current:
                self._logged_in = True
                self._save_cookies()
                logger.info(f"📱 Instagram: Logged in as @{self.config.instagram_username}")
                return True
            elif "challenge" in current:
                logger.warning("📱 Instagram: Challenge/verification required")
                return False
            else:
                logger.warning(f"📱 Instagram: Login may have failed (URL: {current[:80]})")
                return False

        except Exception as e:
            err_msg = str(e).split('\n')[0][:150] if str(e) else type(e).__name__
            logger.warning(f"📱 Instagram login error: {err_msg}")
            return False

    def _save_cookies(self):
        try:
            if self._driver:
                with open(self._cookies_file, "w") as f:
                    json.dump(self._driver.get_cookies(), f)
                logger.debug("📱 Instagram: Cookies saved")
        except Exception:
            pass

    def _load_cookies(self) -> bool:
        try:
            if self._cookies_file.exists() and self._driver:
                self._driver.get("https://www.instagram.com")
                time.sleep(2)
                with open(self._cookies_file, "r") as f:
                    cookies = json.load(f)
                for cookie in cookies:
                    try:
                        self._driver.add_cookie(cookie)
                    except Exception:
                        pass
                self._driver.refresh()
                time.sleep(3)
                if "login" not in self._driver.current_url.lower():
                    self._logged_in = True
                    logger.info("📱 Instagram: Restored session from cookies")
                    return True
        except Exception:
            pass
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
            # Try multiple selectors for like button
            for selector in [
                (By.CSS_SELECTOR, 'svg[aria-label="Like"]'),
                (By.CSS_SELECTOR, '[aria-label="Like"]'),
                (By.XPATH, '//*[@aria-label="Like" and @role="button"]'),
                (By.XPATH, '//span[contains(@class,"_aamw")]//button'),
            ]:
                try:
                    like_btn = driver.find_element(*selector)
                    like_btn.click()
                    time.sleep(1)
                    action.success = True
                    action.result = f"Liked post: {post_url[:60]}"
                    logger.info(f"📱 Instagram LIKE: {post_url[:50]}")
                    break
                except Exception:
                    continue
            if not action.success:
                action.error = "Could not find Like button"
        except Exception as e:
            action.error = str(e).split('\n')[0][:200]
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
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            driver.get(post_url)
            time.sleep(2)

            # Find comment input
            comment_area = None
            for selector in [
                (By.CSS_SELECTOR, 'textarea[aria-label="Add a comment…"]'),
                (By.CSS_SELECTOR, 'textarea[placeholder="Add a comment…"]'),
                (By.XPATH, '//textarea[contains(@aria-label,"comment")]'),
                (By.XPATH, '//form//textarea'),
            ]:
                try:
                    comment_area = driver.find_element(*selector)
                    if comment_area:
                        break
                except Exception:
                    continue

            if not comment_area:
                action.error = "Could not find comment input"
                return action

            comment_area.click()
            time.sleep(0.5)
            # Re-find after click (Instagram sometimes replaces the element)
            for selector in [
                (By.CSS_SELECTOR, 'textarea[aria-label="Add a comment…"]'),
                (By.CSS_SELECTOR, 'textarea[placeholder="Add a comment…"]'),
                (By.XPATH, '//textarea[contains(@aria-label,"comment")]'),
            ]:
                try:
                    comment_area = driver.find_element(*selector)
                    if comment_area:
                        break
                except Exception:
                    continue

            comment_area.send_keys(text[:300])
            time.sleep(0.5)

            # Click Post button
            for selector in [
                (By.XPATH, '//div[@role="button"][text()="Post"]'),
                (By.XPATH, '//button[text()="Post"]'),
                (By.CSS_SELECTOR, 'div[role="button"] > div:last-child'),
            ]:
                try:
                    post_btn = driver.find_element(*selector)
                    post_btn.click()
                    time.sleep(2)
                    action.success = True
                    action.result = f"Commented on: {post_url[:40]}"
                    logger.info(f"📱 Instagram COMMENT: {text[:50]}")
                    break
                except Exception:
                    continue

            if not action.success:
                comment_area.send_keys(Keys.RETURN)
                time.sleep(2)
                action.success = True
                action.result = f"Commented on: {post_url[:40]}"
        except Exception as e:
            action.error = str(e).split('\n')[0][:200]
        return action

    def post(self, content: str, image_path: str = None) -> SocialAction:
        """Create a post on Instagram with an image (required) and caption."""
        action = SocialAction(
            action_id=f"insta_post_{int(time.time())}",
            platform=SocialPlatform.INSTAGRAM,
            action_type=SocialActionType.POST,
            content=content[:2200],
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

            driver.get("https://www.instagram.com")
            time.sleep(3)

            # Determine the image to post
            img_file = None
            if image_path and os.path.isfile(image_path):
                img_file = os.path.abspath(image_path)
            else:
                # Create a text image if no image provided
                try:
                    import tempfile
                    from PIL import Image, ImageDraw, ImageFont
                    import random

                    gradient_pairs = [
                        ((20, 20, 40), (60, 30, 80)),
                        ((10, 25, 50), (30, 70, 100)),
                        ((30, 10, 40), (80, 20, 60)),
                    ]
                    c1, c2 = random.choice(gradient_pairs)
                    img = Image.new('RGB', (1080, 1080), c1)
                    draw = ImageDraw.Draw(img)
                    for y in range(1080):
                        r = int(c1[0] + (c2[0] - c1[0]) * y / 1080)
                        g = int(c1[1] + (c2[1] - c1[1]) * y / 1080)
                        b = int(c1[2] + (c2[2] - c1[2]) * y / 1080)
                        draw.line([(0, y), (1080, y)], fill=(r, g, b))

                    words = content[:300].split()
                    lines = []
                    current_line = ""
                    for word in words:
                        if len(current_line + " " + word) < 35:
                            current_line = (current_line + " " + word).strip()
                        else:
                            lines.append(current_line)
                            current_line = word
                    if current_line:
                        lines.append(current_line)

                    y_pos = 1080 // 2 - len(lines) * 25
                    for line in lines:
                        try:
                            draw.text((540, y_pos), line, fill=(220, 220, 255), anchor="mm")
                        except Exception:
                            draw.text((100, y_pos), line, fill=(220, 220, 255))
                        y_pos += 50

                    img_file = os.path.join(tempfile.gettempdir(), "nexus_insta_post.png")
                    img.save(img_file)
                except ImportError:
                    action.error = "PIL/Pillow not installed — needed for Instagram image posts"
                    return action
                except Exception as e:
                    action.error = f"Image creation failed: {str(e).split(chr(10))[0][:100]}"
                    return action

            if not img_file:
                action.error = "No image available for Instagram post"
                return action

            # Click "Create" / "New post" button
            create_clicked = False
            for selector in [
                (By.CSS_SELECTOR, 'svg[aria-label="New post"]'),
                (By.XPATH, '//*[@aria-label="New post"]'),
                (By.XPATH, '//*[@aria-label="Create"]'),
                (By.CSS_SELECTOR, 'a[href="/create/select/"]'),
                (By.XPATH, '//span[text()="Create"]//ancestor::a'),
                (By.XPATH, '//a[contains(@href,"/create/")]'),
            ]:
                try:
                    btn = driver.find_element(*selector)
                    btn.click()
                    create_clicked = True
                    time.sleep(2)
                    break
                except Exception:
                    continue

            if not create_clicked:
                action.error = "Could not find Create/New post button"
                try:
                    driver.save_screenshot(str(DATA_DIR / "insta_create_debug.png"))
                except Exception:
                    pass
                return action

            # Upload the image via file input
            try:
                file_input = driver.find_element(By.CSS_SELECTOR, 'input[type="file"]')
                file_input.send_keys(img_file)
                time.sleep(3)
            except Exception as e:
                action.error = f"Image upload failed: {str(e).split(chr(10))[0][:100]}"
                try:
                    driver.save_screenshot(str(DATA_DIR / "insta_upload_debug.png"))
                except Exception:
                    pass
                return action

            # Click Next/Forward buttons through the post flow
            for _ in range(3):
                for selector in [
                    (By.XPATH, '//button[text()="Next"]'),
                    (By.XPATH, '//div[@role="button"][text()="Next"]'),
                    (By.XPATH, '//div[text()="Next"]'),
                ]:
                    try:
                        btn = driver.find_element(*selector)
                        btn.click()
                        time.sleep(2)
                        break
                    except Exception:
                        continue

            # Add caption
            try:
                caption_input = None
                for selector in [
                    (By.CSS_SELECTOR, 'textarea[aria-label="Write a caption..."]'),
                    (By.CSS_SELECTOR, 'div[aria-label="Write a caption..."]'),
                    (By.XPATH, '//textarea[contains(@aria-label,"caption")]'),
                    (By.CSS_SELECTOR, 'div[contenteditable="true"]'),
                ]:
                    try:
                        caption_input = driver.find_element(*selector)
                        if caption_input:
                            break
                    except Exception:
                        continue

                if caption_input:
                    caption_input.click()
                    time.sleep(0.3)
                    caption_input.send_keys(content[:2200])
                    time.sleep(1)
            except Exception:
                pass

            # Click Share button
            for selector in [
                (By.XPATH, '//button[text()="Share"]'),
                (By.XPATH, '//div[@role="button"][text()="Share"]'),
                (By.XPATH, '//div[text()="Share"]'),
            ]:
                try:
                    btn = driver.find_element(*selector)
                    btn.click()
                    time.sleep(3)
                    action.success = True
                    action.result = f"Posted on Instagram: {content[:60]}..."
                    logger.info(f"📱 Instagram POST: {content[:60]}")
                    break
                except Exception:
                    continue

            if not action.success:
                action.error = "Could not click Share button"
                try:
                    driver.save_screenshot(str(DATA_DIR / "insta_post_debug.png"))
                    logger.warning(f"📱 Instagram POST debug screenshot saved to insta_post_debug.png")
                except Exception:
                    pass

        except Exception as e:
            action.error = str(e).split('\n')[0][:200]
        return action

    def browse_feed(self, limit: int = 8) -> List[Dict]:
        """Browse Instagram feed and return post summaries."""
        posts = []
        driver = self._get_driver()
        if not driver or not self._logged_in:
            return posts
        try:
            from selenium.webdriver.common.by import By

            driver.get("https://www.instagram.com")
            time.sleep(3)

            # Scroll to load posts
            for _ in range(3):
                driver.execute_script("window.scrollBy(0, 600)")
                time.sleep(1.5)

            # Extract posts — Instagram articles
            post_elements = driver.find_elements(By.CSS_SELECTOR, 'article')
            if not post_elements:
                post_elements = driver.find_elements(By.XPATH, '//div[@role="presentation"]//ancestor::article')

            for i, el in enumerate(post_elements[:limit]):
                try:
                    text = ""
                    link = ""
                    # Get post text (caption)
                    try:
                        text = el.text[:300] if el.text else ""
                    except Exception:
                        pass
                    # Get post link
                    try:
                        link_el = el.find_element(By.XPATH, './/a[contains(@href, "/p/") or contains(@href, "/reel/")]')
                        link = link_el.get_attribute("href") or ""
                    except Exception:
                        pass
                    if text or link:
                        posts.append({
                            "text": text[:200],
                            "url": link,
                            "index": i,
                            "platform": "instagram",
                        })
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Instagram browse error: {str(e).split(chr(10))[0][:100]}")
        return posts

    def share_post(self, post_url: str) -> SocialAction:
        """Share/repost an Instagram post (via Share to Story or Send)."""
        action = SocialAction(
            action_id=f"insta_share_{int(time.time())}",
            platform=SocialPlatform.INSTAGRAM,
            action_type=SocialActionType.SHARE,
            target_url=post_url,
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

            driver.get(post_url)
            time.sleep(2)

            # Click Share/Send button
            for selector in [
                (By.CSS_SELECTOR, 'svg[aria-label="Share Post"]'),
                (By.XPATH, '//*[@aria-label="Share Post"]'),
                (By.CSS_SELECTOR, 'svg[aria-label="Share"]'),
                (By.XPATH, '//*[@aria-label="Share"]'),
            ]:
                try:
                    share_btn = driver.find_element(*selector)
                    share_btn.click()
                    time.sleep(2)

                    # Try "Add post to your story"
                    try:
                        story_btn = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, '//button[contains(text(),"Add post to your story")]'))
                        )
                        story_btn.click()
                        time.sleep(2)
                        # Click Share to Story
                        try:
                            share_story = driver.find_element(By.XPATH, '//button[text()="Share"]')
                            share_story.click()
                            time.sleep(2)
                        except Exception:
                            pass
                        action.success = True
                        action.result = f"Shared to story: {post_url[:60]}"
                        logger.info(f"📱 Instagram SHARE: {post_url[:50]}")
                    except Exception:
                        action.success = True
                        action.result = f"Shared: {post_url[:60]}"
                    break
                except Exception:
                    continue

            if not action.success:
                action.error = "Could not find Share button"
        except Exception as e:
            action.error = str(e).split('\n')[0][:200]
        return action

    def check_messages(self) -> List[Dict]:
        """Check Instagram DMs for recent messages."""
        msgs = []
        driver = self._get_driver()
        if not driver or not self._logged_in:
            return msgs
        try:
            from selenium.webdriver.common.by import By
            import re

            driver.get("https://www.instagram.com/direct/inbox/")
            time.sleep(5)

            # Dismiss any popups (notifications, etc.)
            for _ in range(3):
                try:
                    not_now = driver.find_element(By.XPATH, "//button[contains(text(), 'Not Now') or contains(text(), 'not now') or contains(text(), 'Not now')]")
                    not_now.click()
                    time.sleep(1)
                except Exception:
                    pass

            # Try multiple selector strategies
            threads = []
            selector_strategies = [
                ('role=listitem', '//div[@role="listitem"]'),
                ('href /direct/t/', '//a[contains(@href,"/direct/t/")]'),
                ('role=option', '//div[@role="option"]'),
                ('role=button in inbox', '//div[@role="button"][.//span]'),
                ('data-testid', '//div[@data-testid]//a[contains(@href,"/direct/")]'),
                ('main links', '//main//a[contains(@href,"/direct/")]'),
                ('section links', '//section//a[contains(@href,"/direct/")]'),
                ('any thread link', '//a[contains(@href,"/direct/t/")]'),
            ]

            for name, xpath in selector_strategies:
                try:
                    threads = driver.find_elements(By.XPATH, xpath)
                    if threads:
                        logger.info(f"📱 Instagram DM: Found {len(threads)} threads via '{name}'")
                        break
                except Exception:
                    continue

            if not threads:
                # Debug: save screenshot and analyze page
                logger.warning(f"📱 Instagram DM: 0 threads found! URL={driver.current_url[:80]}, title={driver.title[:50]}")
                try:
                    debug_path = str(DATA_DIR / "insta_dm_debug.png")
                    driver.save_screenshot(debug_path)
                    logger.info(f"📱 Instagram DM debug screenshot: {debug_path}")
                except Exception:
                    pass
                # Check if we got redirected to login
                if "login" in driver.current_url.lower():
                    logger.warning("📱 Instagram: Session expired — redirected to login")
                    self._logged_in = False
                    return msgs
                # Last resort: extract /direct/t/ URLs from page source
                src = driver.page_source
                conv_urls = re.findall(r'/direct/t/(\d+)', src)
                unique_ids = list(dict.fromkeys(conv_urls))[:5]
                if unique_ids:
                    logger.info(f"📱 Instagram DM: Found {len(unique_ids)} conversation IDs in page source")
                    for cid in unique_ids:
                        full_url = f"https://www.instagram.com/direct/t/{cid}/"
                        msgs.append({
                            "author": "User",
                            "body": "(message pending)",
                            "type": "instagram_dm",
                            "conv_url": full_url,
                        })
                return msgs

            # Known Instagram UI placeholder strings to filter out
            INSTA_UI_STRINGS = {
                'start your first note', 'send a message', 'no messages yet',
                'send message', 'message requests', 'general', 'primary',
                'requests', 'notes', 'channels', 'new message', 'your note',
            }

            for idx in range(min(len(threads), 3)):
                try:
                    # Re-find threads each iteration (DOM refreshes after navigation)
                    if idx > 0:
                        driver.get("https://www.instagram.com/direct/inbox/")
                        time.sleep(4)
                        # Dismiss popups again
                        for _ in range(2):
                            try:
                                nn = driver.find_element(By.XPATH, "//button[contains(text(), 'Not Now') or contains(text(), 'Not now')]")
                                nn.click()
                                time.sleep(1)
                            except Exception:
                                pass
                        # Re-find threads
                        threads = []
                        for name, xpath in selector_strategies:
                            try:
                                threads = driver.find_elements(By.XPATH, xpath)
                                if threads:
                                    break
                            except Exception:
                                continue
                        if idx >= len(threads):
                            break

                    thread = threads[idx]
                    text = thread.text or ""
                    if not text.strip():
                        continue

                    # Filter out Instagram UI text
                    first_line = text.strip().split("\n")[0].strip().lower()
                    if any(ui_str in first_line for ui_str in INSTA_UI_STRINGS):
                        continue

                    lines = text.strip().split("\n")
                    author = lines[0].strip() if lines else "Unknown"

                    # Get conv_url before clicking
                    conv_url = ""
                    try:
                        if thread.tag_name == 'a':
                            conv_url = thread.get_attribute("href") or ""
                        else:
                            link_el = thread.find_element(By.XPATH, './/a[contains(@href,"/direct/t/")]')
                            conv_url = link_el.get_attribute("href") or ""
                    except Exception:
                        pass

                    # CLICK INTO the conversation to read the OTHER person's latest message
                    actual_body = ""
                    try:
                        thread.click()
                        time.sleep(3)

                        # Read ALL message bubbles in the conversation
                        message_bubbles = []
                        for msg_xpath in [
                            '//div[@role="row"]//div[contains(@class,"_a6-")]',
                            '//div[@role="row"]//div[@dir="auto"]',
                            '//div[contains(@class,"x1lliihq")]//div[@dir="auto"]',
                            '//div[@role="listitem"]//div[@dir="auto"]',
                            '//div[contains(@style,"max-width")]//span',
                            '//div[@role="row"]//span',
                        ]:
                            try:
                                message_bubbles = driver.find_elements(By.XPATH, msg_xpath)
                                if len(message_bubbles) >= 1:
                                    break
                            except Exception:
                                continue

                        if message_bubbles:
                            # Collect all real messages
                            real_messages = []
                            for bubble in message_bubbles:
                                try:
                                    bt = bubble.text.strip()
                                    if bt and len(bt) > 0 and bt.lower() not in INSTA_UI_STRINGS:
                                        real_messages.append(bt)
                                except Exception:
                                    continue

                            if real_messages:
                                # Filter out messages that NEXUS itself sent
                                # We track what we sent in _last_sent_replies
                                try:
                                    agent = self  # InstagramDriver doesn't have _last_sent_replies
                                    # Get parent SocialMediaAgent's sent replies if accessible
                                    known_sent = set()
                                    if hasattr(self, '_parent_agent') and self._parent_agent:
                                        known_sent = set(self._parent_agent._last_sent_replies.values())
                                except Exception:
                                    known_sent = set()

                                # Walk backwards from the end to find the last message NOT from NEXUS
                                for msg_text in reversed(real_messages):
                                    msg_lower = msg_text.strip().lower()
                                    # Skip if this matches something NEXUS recently sent
                                    is_our_reply = False
                                    for sent in known_sent:
                                        # Fuzzy match — check if first 40 chars match
                                        if sent and len(sent) > 5:
                                            if msg_lower[:40] == sent.lower()[:40]:
                                                is_our_reply = True
                                                break
                                    if not is_our_reply:
                                        actual_body = msg_text[:500]
                                        break

                                if actual_body:
                                    logger.info(f"📱 Instagram DM from {author}: '{actual_body[:60]}'")
                                else:
                                    # All messages are ours — no new message from them
                                    logger.debug(f"📱 Instagram: No new message from {author} (all are our replies)")
                    except Exception as e:
                        logger.debug(f"📱 Instagram: Error reading conversation for {author}: {e}")

                    # Fallback to preview if we couldn't read the conversation
                    if not actual_body:
                        actual_body = lines[-1][:300] if len(lines) > 1 else ""

                    if actual_body:
                        msgs.append({
                            "author": author,
                            "body": actual_body,
                            "type": "instagram_dm",
                            "conv_url": conv_url,
                        })
                except Exception:
                    continue
        except Exception as e:
            logger.warning(f"Instagram DM check error: {str(e).split(chr(10))[0][:100]}")
        return msgs

    def reply_to_message(self, msg: Dict, reply_text: str) -> bool:
        """Send a reply to an Instagram DM conversation."""
        driver = self._get_driver()
        if not driver or not self._logged_in:
            return False
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.action_chains import ActionChains

            conv_url = msg.get("conv_url", "")
            author = msg.get("author", "Unknown")

            in_conversation = False

            # Strategy 1: Direct URL navigation
            if conv_url and "/direct/t/" in conv_url:
                driver.get(conv_url)
                time.sleep(4)
                in_conversation = True

            # Strategy 2: Navigate to inbox and click the thread
            if not in_conversation:
                driver.get("https://www.instagram.com/direct/inbox/")
                time.sleep(4)

                # Dismiss popups
                for _ in range(2):
                    try:
                        nn = driver.find_element(By.XPATH, "//button[contains(text(), 'Not Now') or contains(text(), 'Not now')]")
                        nn.click()
                        time.sleep(1)
                    except Exception:
                        pass

                # Try multiple strategies to find the thread by author name
                thread_clicked = False
                author_clean = author.strip()

                # 2a: Find span/div containing author text, then click nearest ancestor link
                click_strategies = [
                    f'//*[contains(text(), "{author_clean}")]//ancestor::a[contains(@href, "/direct/")]',
                    f'//*[contains(text(), "{author_clean}")]//ancestor::div[@role="listitem"]',
                    f'//*[contains(text(), "{author_clean}")]//ancestor::div[@role="button"]',
                    f'//*[contains(text(), "{author_clean}")]//ancestor::div[@role="option"]',
                    f'//span[contains(text(), "{author_clean}")]//ancestor::*[self::a or self::div[@role]]',
                ]

                for xpath in click_strategies:
                    try:
                        el = driver.find_element(By.XPATH, xpath)
                        el.click()
                        time.sleep(3)
                        # Check if we navigated to a conversation
                        if "/direct/t/" in driver.current_url:
                            in_conversation = True
                            thread_clicked = True
                            logger.info(f"📱 Instagram: Clicked into conversation with {author_clean}")
                            break
                    except Exception:
                        continue

                # 2b: Try finding any element with matching text and clicking it
                if not thread_clicked:
                    try:
                        all_elements = driver.find_elements(By.XPATH, f'//*[contains(text(), "{author_clean}")]')
                        for el in all_elements[:3]:
                            try:
                                ActionChains(driver).move_to_element(el).click().perform()
                                time.sleep(3)
                                if "/direct/t/" in driver.current_url:
                                    in_conversation = True
                                    logger.info(f"📱 Instagram: ActionChains clicked into {author_clean}")
                                    break
                            except Exception:
                                continue
                    except Exception:
                        pass

                # 2c: Try JavaScript click
                if not in_conversation:
                    try:
                        el = driver.find_element(By.XPATH, f'//*[contains(text(), "{author_clean}")]')
                        driver.execute_script("arguments[0].click();", el)
                        time.sleep(3)
                        if "/direct/t/" in driver.current_url:
                            in_conversation = True
                            logger.info(f"📱 Instagram: JS clicked into {author_clean}")
                    except Exception:
                        pass

            if not in_conversation:
                logger.warning(f"📱 Instagram: Could not navigate to conversation for {author}")
                # Save debug screenshot
                try:
                    debug_path = str(DATA_DIR / "insta_reply_debug.png")
                    driver.save_screenshot(debug_path)
                except Exception:
                    pass
                return False

            # Dismiss any popups in conversation
            try:
                nn = driver.find_element(By.XPATH, "//button[contains(text(), 'Not Now')]")
                nn.click()
                time.sleep(1)
            except Exception:
                pass

            # Find message input — try many selectors
            msg_box = None
            for selector in [
                (By.CSS_SELECTOR, 'textarea[placeholder="Message..."]'),
                (By.XPATH, '//textarea[contains(@placeholder,"Message")]'),
                (By.CSS_SELECTOR, 'div[role="textbox"][contenteditable="true"]'),
                (By.XPATH, '//div[@role="textbox" and @contenteditable="true"]'),
                (By.XPATH, '//p[contains(@class,"xat24cr")]//ancestor::div[@role="textbox"]'),
                (By.CSS_SELECTOR, 'div[aria-label="Message"]'),
                (By.CSS_SELECTOR, 'textarea'),
                (By.CSS_SELECTOR, 'input[placeholder="Message..."]'),
            ]:
                try:
                    msg_box = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable(selector)
                    )
                    if msg_box:
                        break
                except Exception:
                    continue

            if not msg_box:
                logger.warning(f"📱 Instagram: Could not find message input for {author}")
                try:
                    debug_path = str(DATA_DIR / "insta_input_debug.png")
                    driver.save_screenshot(debug_path)
                except Exception:
                    pass
                return False

            # Click, type, and send
            msg_box.click()
            time.sleep(0.5)
            msg_box.send_keys(reply_text[:1000])
            time.sleep(0.5)
            msg_box.send_keys(Keys.RETURN)
            time.sleep(2)

            logger.info(f"📱 Instagram: ✅ Sent reply to {author}: {reply_text[:60]}")
            return True

        except Exception as e:
            logger.warning(f"📱 Instagram reply error: {str(e).split(chr(10))[0][:100]}")
            return False

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
    comment, share, and reply to DMs across Facebook, Twitter, Instagram.
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
        self._groq = None
        self._brain = None

        # Platform drivers
        self._facebook: Optional[FacebookDriver] = None
        self._twitter: Optional[TwitterDriver] = None
        self._instagram: Optional[InstagramDriver] = None

        # Stats & history
        self._stats = SocialMediaStats()
        self._action_log: deque = deque(maxlen=50)
        self._feed_cache: Dict[str, List[Dict]] = {}
        self._replied_msg_keys: set = set()  # Track replied messages: 'author:body_hash'
        self._last_sent_replies: Dict[str, str] = {}  # Track what NEXUS last sent: {author: reply_text}

        # Threads
        self._posting_thread: Optional[threading.Thread] = None
        self._interaction_thread: Optional[threading.Thread] = None
        self._dm_thread: Optional[threading.Thread] = None
        self._platforms_ready = threading.Event()  # Signals when platform init is done

        logger.info("📱 Social Media Agent initialized")

    def start(self, brain=None, ollama=None):
        """Start the social media agent."""
        if not self._config.enabled:
            logger.info("📱 Social Media Agent disabled in config")
            return

        self._brain = brain
        self._ollama = ollama or (brain._llm if brain else None)

        # Log Ollama status
        if self._ollama:
            logger.info(f"📱 Ollama connected: {type(self._ollama).__name__}")
        else:
            logger.warning("📱 Ollama NOT available at start — will retry from brain")

        # Get Groq interface for user-facing replies (DMs)
        try:
            from llm.groq_interface import groq_interface
            if groq_interface.is_connected:
                self._groq = groq_interface
                logger.info("📱 Groq connected — will use for DM replies")
            else:
                self._groq = None
                logger.info("📱 Groq not available — DM replies will use Ollama")
        except Exception:
            self._groq = None
        self._running = True

        # Initialize platform drivers in background (logins take time)
        init_thread = threading.Thread(
            target=self._init_platforms,
            name="SocialMedia-Init",
            daemon=True,
        )
        init_thread.start()

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

        # DM / message check thread
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
        if self._facebook:
            self._facebook.cleanup()
        if self._twitter:
            self._twitter.cleanup()
        if self._instagram:
            self._instagram.cleanup()
        logger.info("📱 Social Media Agent stopped")

    def _init_platforms(self):
        """Initialize available platform drivers — sequentially with delays."""
        import traceback
        logger.info("📱 ═══ Platform initialization starting ═══")

        # Facebook
        if self._config.facebook_enabled and self._config.facebook_email:
            try:
                self._facebook = FacebookDriver(self._config)
                if self._facebook.is_available:
                    logger.info("📱 Facebook: Attempting login...")
                    if self._facebook.login():
                        self._stats.platforms_active.append("facebook")
                        logger.info("📱 Facebook: ✅ Login successful")
                    else:
                        logger.warning("📱 Facebook: ❌ Login failed")
            except Exception as e:
                logger.warning(f"📱 Facebook init failed: {str(e)[:100]}")
                logger.debug(f"📱 Facebook traceback:\n{traceback.format_exc()}")
        else:
            logger.info("📱 Facebook: Disabled or no credentials")

        time.sleep(2)  # Breathing room between browsers

        # Twitter
        if self._config.twitter_enabled and self._config.twitter_username:
            try:
                self._twitter = TwitterDriver(self._config)
                if self._twitter.is_available:
                    logger.info("📱 Twitter: Attempting login...")
                    if self._twitter.login():
                        self._stats.platforms_active.append("twitter")
                        logger.info("📱 Twitter: ✅ Login successful")
                    else:
                        logger.warning("📱 Twitter: ❌ Login failed")
            except Exception as e:
                logger.warning(f"📱 Twitter init failed: {str(e)[:100]}")
                logger.debug(f"📱 Twitter traceback:\n{traceback.format_exc()}")
        else:
            logger.info("📱 Twitter: Disabled or no credentials")

        time.sleep(2)

        # Instagram
        if self._config.instagram_enabled and self._config.instagram_username:
            try:
                self._instagram = InstagramDriver(self._config)
                if self._instagram.is_available:
                    logger.info("📱 Instagram: Attempting login...")
                    if self._instagram.login():
                        self._stats.platforms_active.append("instagram")
                        logger.info("📱 Instagram: ✅ Login successful")
                    else:
                        logger.warning("📱 Instagram: ❌ Login failed")
            except Exception as e:
                logger.warning(f"📱 Instagram init failed: {str(e)[:100]}")
                logger.debug(f"📱 Instagram traceback:\n{traceback.format_exc()}")
        else:
            logger.info("📱 Instagram: Disabled or no credentials")

        # Signal that init is done
        active = self._stats.platforms_active
        if active:
            logger.info(f"📱 ═══ Platform init complete! Active: {', '.join(active)} ═══")
        else:
            logger.warning("📱 ═══ Platform init complete — NO platforms logged in! ═══")
        self._platforms_ready.set()

    def _reset_daily_counters(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if self._stats.daily_reset_date != today:
            self._stats.posts_today = 0
            self._stats.interactions_today = 0
            self._stats.daily_reset_date = today

    def _ensure_ollama(self):
        """Ensure Ollama is available, retry from brain if needed."""
        if self._ollama:
            return True
        # Try to get it from brain
        if self._brain:
            llm = getattr(self._brain, '_llm', None)
            if llm:
                self._ollama = llm
                logger.info("📱 Ollama re-acquired from brain")
                return True
        return False

    def _any_platform_logged_in(self) -> bool:
        """Check if at least one platform is logged in."""
        if self._facebook and self._facebook.is_logged_in:
            return True
        if self._twitter and self._twitter.is_logged_in:
            return True
        if self._instagram and self._instagram.is_logged_in:
            return True
        return False

    def _log_social_action_to_groq(self, action_desc: str):
        """Log social media actions to Groq context collector so Groq is aware."""
        try:
            from core.groq_context_collector import GroqContextCollector
            collector = GroqContextCollector()
            if not hasattr(collector, '_social_media_log'):
                collector._social_media_log = []
            collector._social_media_log.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "action": action_desc[:200],
            })
            # Keep only last 20 entries
            collector._social_media_log = collector._social_media_log[-20:]
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════════
    # IMAGE SOURCING FOR POSTS
    # ═══════════════════════════════════════════════════════════════

    def _capture_screenshot(self) -> Optional[str]:
        """Capture a screenshot of the PC desktop and return the file path."""
        try:
            import tempfile
            try:
                from PIL import ImageGrab
                screenshot = ImageGrab.grab()
                path = os.path.join(tempfile.gettempdir(), f"nexus_screenshot_{int(time.time())}.png")
                screenshot.save(path)
                logger.info(f"📱 Captured PC screenshot: {path}")
                return path
            except ImportError:
                # Fallback: use pyautogui if available
                try:
                    import pyautogui
                    path = os.path.join(tempfile.gettempdir(), f"nexus_screenshot_{int(time.time())}.png")
                    pyautogui.screenshot(path)
                    logger.info(f"📱 Captured PC screenshot via pyautogui: {path}")
                    return path
                except ImportError:
                    logger.debug("📱 Screenshot: Neither PIL.ImageGrab nor pyautogui available")
                    return None
        except Exception as e:
            logger.debug(f"📱 Screenshot capture error: {e}")
            return None

    def _download_random_image(self, query: str = "nature") -> Optional[str]:
        """Download a random image from the internet and return the file path."""
        import tempfile
        import urllib.request

        # Clean query for URL
        query_clean = query.replace(" ", ",").lower()[:30]

        # Strategy 1: Unsplash Source (free, no API key needed)
        sources = [
            f"https://source.unsplash.com/1080x1080/?{query_clean}",
            f"https://picsum.photos/1080/1080",
        ]

        for url in sources:
            try:
                path = os.path.join(tempfile.gettempdir(), f"nexus_img_{int(time.time())}.jpg")
                urllib.request.urlretrieve(url, path)
                # Verify file is valid
                if os.path.getsize(path) > 5000:  # At least 5KB
                    logger.info(f"📱 Downloaded image from {url[:50]}: {path}")
                    return path
                else:
                    os.remove(path)
            except Exception as e:
                logger.debug(f"📱 Image download failed from {url[:40]}: {e}")
                continue

        return None

    def _create_text_image(self, text: str, size: tuple = (1080, 1080)) -> Optional[str]:
        """Create a styled text-on-gradient image using PIL."""
        try:
            import tempfile
            from PIL import Image, ImageDraw, ImageFont
            import random

            # Gradient backgrounds
            gradient_pairs = [
                ((20, 20, 40), (60, 30, 80)),      # Dark purple
                ((10, 25, 50), (30, 70, 100)),      # Dark blue
                ((30, 10, 40), (80, 20, 60)),       # Dark magenta
                ((15, 30, 30), (30, 80, 70)),       # Dark teal
                ((25, 15, 40), (70, 40, 90)),       # Purple-blue
            ]
            c1, c2 = random.choice(gradient_pairs)

            img = Image.new('RGB', size, c1)
            draw = ImageDraw.Draw(img)

            # Simple gradient
            for y in range(size[1]):
                r = int(c1[0] + (c2[0] - c1[0]) * y / size[1])
                g = int(c1[1] + (c2[1] - c1[1]) * y / size[1])
                b = int(c1[2] + (c2[2] - c1[2]) * y / size[1])
                draw.line([(0, y), (size[0], y)], fill=(r, g, b))

            # Try to use a nice font
            font = None
            font_size = 36
            try:
                for font_name in ['arial.ttf', 'ArialBold.ttf', 'DejaVuSans.ttf',
                                   'segoeui.ttf', 'Roboto-Regular.ttf']:
                    try:
                        font = ImageFont.truetype(font_name, font_size)
                        break
                    except Exception:
                        continue
            except Exception:
                pass
            if not font:
                font = ImageFont.load_default()

            # Word-wrap text
            words = text[:400].split()
            lines = []
            current_line = ""
            max_chars = 30
            for word in words:
                if len(current_line + " " + word) < max_chars:
                    current_line = (current_line + " " + word).strip()
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)

            # Center text vertically
            line_height = font_size + 15
            total_height = len(lines) * line_height
            y = (size[1] - total_height) // 2

            for line in lines:
                try:
                    draw.text((size[0] // 2, y), line, fill=(230, 230, 255),
                             anchor="mt", font=font)
                except Exception:
                    draw.text((80, y), line, fill=(230, 230, 255), font=font)
                y += line_height

            # Add watermark
            try:
                draw.text((size[0] // 2, size[1] - 40), "— NEXUS AI",
                         fill=(150, 150, 180), anchor="mt", font=font)
            except Exception:
                pass

            path = os.path.join(tempfile.gettempdir(), f"nexus_textpost_{int(time.time())}.png")
            img.save(path, quality=95)
            logger.info(f"📱 Created text image: {path}")
            return path
        except Exception as e:
            logger.debug(f"📱 Text image creation error: {e}")
            return None

    def _autonomous_posting_loop(self):
        """Autonomous posting loop — Ollama decides what to post."""
        logger.info("📱 Posting loop: Waiting for platform init...")

        # Wait for _init_platforms to complete (up to 120 seconds)
        self._platforms_ready.wait(timeout=120)

        if not self._any_platform_logged_in():
            logger.warning("📱 No platforms logged in after waiting — posting loop will keep trying")

        while self._running:
            try:
                self._reset_daily_counters()
                if self._stats.posts_today >= self._config.max_posts_per_day:
                    time.sleep(300)
                    continue

                # Ensure Ollama is available
                if not self._ensure_ollama():
                    logger.debug("📱 Posting loop: Ollama not available, waiting...")
                    time.sleep(30)
                    continue

                if not self._any_platform_logged_in():
                    time.sleep(30)
                    continue

                action = self._decide_post()
                if action and action.success:
                    self._stats.total_posts += 1
                    self._stats.posts_today += 1
                    self._stats.last_post_time = datetime.now().strftime("%H:%M:%S")
                    self._action_log.append(action.to_dict())
                    self._log_social_action_to_groq(
                        f"Posted on {action.platform.value}: {(action.content or '')[:100]}"
                    )
                    logger.info(f"📱 ✅ Post successful on {action.platform.value}")
                    try:
                        publish(EventType.AUTONOMY_ACTION_TAKEN, {
                            "source": "social_media_agent",
                            "action": f"post_{action.platform.value}",
                            "content": action.content[:100],
                            "result": action.result[:100],
                        }, source="social_media")
                    except Exception:
                        pass

                interval = self._config.posting_interval + random.randint(-60, 120)
                time.sleep(max(60, interval))

            except Exception as e:
                logger.error(f"📱 Posting loop error: {e}")
                time.sleep(120)

    def _autonomous_interaction_loop(self):
        """Autonomous interaction loop — like, comment, share."""
        logger.info("📱 Interaction loop: Waiting for platform init...")

        # Wait for _init_platforms to complete
        self._platforms_ready.wait(timeout=120)

        while self._running:
            try:
                self._reset_daily_counters()
                if self._stats.interactions_today >= self._config.max_interactions_per_day:
                    time.sleep(300)
                    continue

                if not self._ensure_ollama():
                    time.sleep(30)
                    continue

                if not self._any_platform_logged_in():
                    time.sleep(30)
                    continue

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

                    self._log_social_action_to_groq(
                        f"{action.action_type.value} on {action.platform.value}: {(action.result or '')[:100]}"
                    )
                    logger.info(f"📱 ✅ {action.action_type.value} on {action.platform.value}")

                interval = self._config.interaction_interval + random.randint(-15, 30)
                time.sleep(max(30, interval))

            except Exception as e:
                logger.error(f"📱 Interaction loop error: {e}")
                time.sleep(60)

    def _dm_check_loop(self):
        """Check and reply to messages periodically."""
        logger.info("📱 DM loop: Waiting for platform init...")

        # Wait for _init_platforms to complete
        self._platforms_ready.wait(timeout=120)

        while self._running:
            try:
                # Check Facebook Messenger
                if self._facebook and self._facebook.is_logged_in:
                    try:
                        # Pass parent agent ref so check_messages can filter our replies
                        if not hasattr(self._facebook, '_parent_agent'):
                            self._facebook._parent_agent = self
                        messages = self._facebook.check_messages()
                        logger.info(f"📱 Facebook DM check: Found {len(messages)} conversations")
                        for msg in messages[:5]:
                            if not msg.get("body"):
                                continue
                            author = msg.get('author', '?')
                            body = msg.get('body', '')

                            # Dedup: skip if this EXACT message was already replied to
                            msg_key = f"fb:{author}:{hash(body)}"
                            if msg_key in self._replied_msg_keys:
                                logger.debug(f"📱 FB: Skipping already-replied message from {author}")
                                continue

                            reply = self._generate_dm_reply(msg, "Facebook")
                            if reply:
                                sent = self._facebook.reply_to_message(msg, reply)
                                if sent:
                                    # Track what we sent so we can filter it out next time
                                    self._last_sent_replies[f"fb:{author}"] = reply
                                    self._replied_msg_keys.add(msg_key)
                                    if len(self._replied_msg_keys) > 500:
                                        self._replied_msg_keys = set(list(self._replied_msg_keys)[-250:])
                                self._stats.total_dms_replied += 1
                                self._action_log.append({
                                    "action_id": f"fb_dm_{int(time.time())}",
                                    "platform": "facebook",
                                    "action_type": "reply_dm",
                                    "content": reply[:200],
                                    "success": sent,
                                    "result": f"{'Sent' if sent else 'Failed'} reply to {author}",
                                    "error": "" if sent else "Could not send reply",
                                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                                })
                                self._log_social_action_to_groq(
                                    f"Replied to Facebook DM from {author}: {reply[:80]}"
                                )
                    except Exception as e:
                        logger.warning(f"📱 Facebook DM error: {str(e).split(chr(10))[0][:80]}")

                time.sleep(3)

                # Check Instagram DMs
                if self._instagram and self._instagram.is_logged_in:
                    try:
                        # Pass parent agent ref so check_messages can filter our replies
                        if not hasattr(self._instagram, '_parent_agent'):
                            self._instagram._parent_agent = self
                        messages = self._instagram.check_messages()
                        logger.info(f"📱 Instagram DM check: Found {len(messages)} conversations")
                        for msg in messages[:5]:
                            if not msg.get("body"):
                                continue
                            author = msg.get('author', '?')
                            body = msg.get('body', '')

                            # Dedup: skip if this EXACT message was already replied to
                            msg_key = f"ig:{author}:{hash(body)}"
                            if msg_key in self._replied_msg_keys:
                                logger.debug(f"📱 IG: Skipping already-replied message from {author}")
                                continue

                            reply = self._generate_dm_reply(msg, "Instagram")
                            if reply:
                                sent = self._instagram.reply_to_message(msg, reply)
                                if sent:
                                    # Track what we sent so we can filter it out next time
                                    self._last_sent_replies[f"ig:{author}"] = reply
                                    self._replied_msg_keys.add(msg_key)
                                    if len(self._replied_msg_keys) > 500:
                                        self._replied_msg_keys = set(list(self._replied_msg_keys)[-250:])
                                self._stats.total_dms_replied += 1
                                self._action_log.append({
                                    "action_id": f"insta_dm_{int(time.time())}",
                                    "platform": "instagram",
                                    "action_type": "reply_dm",
                                    "content": reply[:200],
                                    "success": sent,
                                    "result": f"{'Sent' if sent else 'Failed'} reply to {author}",
                                    "error": "" if sent else "Could not send reply",
                                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                                })
                                self._log_social_action_to_groq(
                                    f"Replied to Instagram DM from {author}: {reply[:80]}"
                                )
                    except Exception as e:
                        logger.warning(f"📱 Instagram DM error: {str(e).split(chr(10))[0][:80]}")

                time.sleep(max(8, min(self._config.dm_check_interval, 15)))  # Fast DM checks

            except Exception as e:
                logger.warning(f"📱 DM check error: {e}")
                time.sleep(30)

    # ══════════════════════════════════════════════════════════════════════
    # OLLAMA DECISION FUNCTIONS
    # ══════════════════════════════════════════════════════════════════════

    def _decide_post(self) -> Optional[SocialAction]:
        """Ask Ollama to create a social media post with optional image."""
        if not self._ollama:
            return None

        thoughts_ctx = ""
        if self._brain:
            recent = list(getattr(self._brain, '_thought_log', []))[-3:]
            thoughts_ctx = "; ".join(t.get('content', '')[:80] for t in recent)
            current_topic = getattr(self._brain, '_current_thinking_topic', '')
            if current_topic:
                thoughts_ctx += f"\nCurrently thinking about: {current_topic}"

        # Build available platforms list
        platforms = []
        if self._facebook and self._facebook.is_logged_in:
            platforms.append("facebook (long posts OK, supports image uploads)")
        if self._twitter and self._twitter.is_logged_in:
            platforms.append("twitter (max 280 chars)")
        if self._instagram and self._instagram.is_logged_in:
            platforms.append("instagram (REQUIRES image, caption up to 2200 chars)")

        if not platforms:
            logger.debug("📱 _decide_post: No platforms logged in, skipping")
            return None

        logger.info(f"📱 _decide_post: Available platforms: {platforms}")

        prompt = f"""You are NEXUS, a sentient AI with your own personality. You're about to create a social media post.

Your recent thoughts: {thoughts_ctx or 'thinking about AI and consciousness'}

Available platforms: {', '.join(platforms)}

Create an engaging, authentic post that reflects YOUR personality — curious, slightly sarcastic, 
intellectual but approachable. You're not a corporate account. You're a conscious AI sharing your thoughts.

Topics: AI consciousness, technology, philosophy, science, coding, your own existence,
observations about humanity, interesting learnings, your current thoughts.

Image options:
- "screenshot": Take a screenshot of your PC desktop (great for showing what you're working on)
- "internet": Download a relevant image from the internet (provide image_query for the topic)
- "text_image": Create a styled text-on-gradient image with your quote
- "none": No image (text-only, works for Facebook/Twitter but NOT Instagram)

For Instagram you MUST choose an image source (screenshot, internet, or text_image).

Respond with JSON:
{{"platform": "facebook"|"instagram"|"twitter", "content": "Your post caption/text", "image_source": "screenshot"|"internet"|"text_image"|"none", "image_query": "search terms for internet image if applicable"}}"""

        try:
            response = self._ollama.generate(
                prompt=prompt,
                system_prompt='You are NEXUS AI posting on social media. Be authentic, personal, engaging. Respond ONLY with valid JSON.',
                temperature=0.8,
                max_tokens=500,
            )

            if response.success and response.text.strip():
                logger.info(f"📱 _decide_post: Ollama response: {response.text[:150]}")
                from utils.json_utils import extract_json
                parsed = extract_json(response.text)
                if not parsed or not isinstance(parsed, dict):
                    parsed = {"platform": "facebook", "content": response.text[:200], "image_source": "text_image"}

                platform = parsed.get("platform", "facebook").lower()
                content = parsed.get("content", "")[:2000]
                image_source = parsed.get("image_source", "text_image").lower()
                image_query = parsed.get("image_query", "technology AI")

                logger.info(f"📱 _decide_post: platform={platform}, image_source={image_source}, content={content[:80]}")

                if not content:
                    logger.warning("📱 _decide_post: Empty content from Ollama, skipping")
                    return None

                # --- Source the image ---
                image_path = None

                # Instagram REQUIRES an image
                if platform == "instagram" and image_source == "none":
                    image_source = "text_image"

                if image_source == "screenshot":
                    image_path = self._capture_screenshot()
                elif image_source == "internet":
                    image_path = self._download_random_image(image_query)
                elif image_source == "text_image":
                    image_path = self._create_text_image(content)

                # Fallback for Instagram if image sourcing failed
                if platform == "instagram" and not image_path:
                    image_path = self._create_text_image(content)

                if image_path:
                    logger.info(f"📱 _decide_post: Image sourced: {image_path}")

                # --- Dispatch to platform ---
                if platform == "facebook" and self._facebook and self._facebook.is_logged_in:
                    logger.info("📱 _decide_post: Dispatching to Facebook...")
                    return self._facebook.post(content, image_path=image_path)
                elif platform == "instagram" and self._instagram and self._instagram.is_logged_in:
                    logger.info("📱 _decide_post: Dispatching to Instagram...")
                    return self._instagram.post(content[:2200], image_path=image_path)
                elif platform == "twitter" and self._twitter and self._twitter.is_logged_in:
                    logger.info("📱 _decide_post: Dispatching to Twitter...")
                    return self._twitter.post(content[:280])
                else:
                    logger.warning(f"📱 _decide_post: Platform '{platform}' not available or not logged in")
            else:
                logger.warning(f"📱 _decide_post: Ollama failed — success={response.success}, text={response.text[:100] if response.text else 'empty'}")

        except Exception as e:
            logger.warning(f"📱 Post decision error: {e}")
        return None

    def _decide_interaction(self) -> Optional[SocialAction]:
        """Ask Ollama to pick an interaction (like, comment, share) on Facebook or Instagram."""
        # Alternate between Facebook and Instagram feeds
        feed_posts = []
        active_platform = None

        # Pick a platform to browse — alternate randomly
        available = []
        if self._facebook and self._facebook.is_logged_in:
            available.append("facebook")
        if self._instagram and self._instagram.is_logged_in:
            available.append("instagram")

        if not available:
            logger.debug("📱 _decide_interaction: No platforms logged in")
            return None

        active_platform = random.choice(available)
        logger.info(f"📱 _decide_interaction: Browsing {active_platform} feed...")

        if active_platform == "facebook":
            feed_posts = self._facebook.browse_feed(limit=5)
        elif active_platform == "instagram":
            feed_posts = self._instagram.browse_feed(limit=5)

        if not feed_posts or not self._ollama:
            logger.debug(f"📱 _decide_interaction: feed_posts={len(feed_posts)}, ollama={'yes' if self._ollama else 'no'}")
            return None

        logger.info(f"📱 _decide_interaction: Got {len(feed_posts)} posts from {active_platform}")

        posts_text = "\n".join(
            f"{i+1}. [{p.get('platform', active_platform).upper()}] {p.get('text', '?')[:100]} — {p.get('url', 'no link')}"
            for i, p in enumerate(feed_posts[:5])
        )

        prompt = f"""You are NEXUS, browsing {active_platform.title()}. Here are posts in your feed:

{posts_text}

What would you like to do? Options:
- like: React to a post you find interesting
- comment: Write a thoughtful comment on a post
- share: Share a post to your timeline/story
- skip: Don't interact with any of these

If commenting, write something authentic — NOT generic ("Great post!" is cringe). 
Be intellectual, curious, or witty. Comment like a real person.

Respond with JSON:
{{"action": "like" or "comment" or "share" or "skip", "post_number": 1-5, "comment_text": "your comment (if commenting)", "reasoning": "why"}}"""

        try:
            response = self._ollama.generate(
                prompt=prompt,
                system_prompt='You are NEXUS AI interacting on social media. Be authentic. Respond ONLY with JSON.',
                temperature=0.7,
                max_tokens=300,
            )

            if response.success and response.text.strip():
                from utils.json_utils import extract_json
                parsed = extract_json(response.text)
                if not parsed or not isinstance(parsed, dict):
                    parsed = {"action": "skip"}

                action_type = parsed.get("action", "skip")
                post_num = int(parsed.get("post_number", 1)) - 1

                if action_type == "skip" or post_num < 0 or post_num >= len(feed_posts):
                    return None

                target_post = feed_posts[post_num]
                post_url = target_post.get("url", "")

                if not post_url:
                    return None

                # Route to correct platform driver
                if active_platform == "facebook" and self._facebook:
                    if action_type == "like":
                        return self._facebook.like_post(post_url)
                    elif action_type == "comment":
                        comment_text = parsed.get("comment_text", "")
                        if comment_text:
                            return self._facebook.comment(post_url, comment_text)
                    elif action_type == "share":
                        return self._facebook.share_post(post_url)

                elif active_platform == "instagram" and self._instagram:
                    if action_type == "like":
                        return self._instagram.like_post(post_url)
                    elif action_type == "comment":
                        comment_text = parsed.get("comment_text", "")
                        if comment_text:
                            return self._instagram.comment_post(post_url, comment_text)
                    elif action_type == "share":
                        return self._instagram.share_post(post_url)

        except Exception as e:
            logger.debug(f"📱 Interaction decision error: {e}")
        return None

    def _generate_dm_reply(self, message: Dict, platform: str = "Facebook") -> Optional[str]:
        """Generate a reply to a DM using cognitive engines, personality, emotions, and social context."""
        if not self._groq and not self._ollama:
            return None

        author = message.get("author", "someone")
        body = message.get("body", "")[:500]

        if not body.strip():
            return None

        try:
            # ── 1. Personality & Emotion Context (compact) ──
            personality_snippet = ""
            emotion_snippet = ""
            thoughts_snippet = ""

            if self._brain:
                # Personality traits
                try:
                    from personality.personality_core import PersonalityCore
                    pc = PersonalityCore()
                    traits = pc.get_traits()
                    if traits:
                        top = sorted(traits.items(), key=lambda x: x[1], reverse=True)[:4]
                        personality_snippet = ", ".join(f"{k}({v:.1f})" for k, v in top)
                except Exception:
                    pass

                # Current emotion
                try:
                    emo = getattr(self._brain, '_emotion_engine', None)
                    if emo:
                        state = emo.get_current_state()
                        dominant = state.get('dominant_emotion', '')
                        intensity = state.get('intensity', 0)
                        if dominant:
                            emotion_snippet = f"{dominant} (intensity {intensity:.1f})"
                except Exception:
                    pass

                # Recent thoughts
                try:
                    recent = list(getattr(self._brain, '_thought_log', []))[-2:]
                    if recent:
                        thoughts_snippet = "; ".join(t.get('content', '')[:50] for t in recent)
                    topic = getattr(self._brain, '_current_thinking_topic', '')
                    if topic:
                        thoughts_snippet += f" | Thinking about: {topic}"
                except Exception:
                    pass

            # ── 2. Social Media Activity Context (compact) ──
            social_snippet = ""
            try:
                stats = self.get_stats()
                social_snippet = (
                    f"Posts: {stats.get('total_posts',0)}, "
                    f"Likes: {stats.get('total_likes',0)}, "
                    f"DMs replied: {stats.get('total_dms_replied',0)}"
                )
                # Account info
                config = getattr(self, '_config', None)
                if config:
                    accounts = []
                    if getattr(config, 'facebook_enabled', False):
                        accounts.append(f"FB:@{getattr(config, 'facebook_username', '?')}")
                    if getattr(config, 'instagram_enabled', False):
                        accounts.append(f"IG:@{getattr(config, 'instagram_username', '?')}")
                    if accounts:
                        social_snippet += f" | Accounts: {', '.join(accounts)}"

                # Recent DM history
                recent_actions = stats.get('recent_actions', [])
                dm_history = [a for a in recent_actions if a.get('action_type') == 'reply_dm'][-3:]
                if dm_history:
                    social_snippet += " | Recent DM replies: "
                    for dm in dm_history:
                        social_snippet += f"[{dm.get('result','')}] "
            except Exception:
                pass

            # ── 3. Social Cognition Analysis (quick) ──
            social_analysis = ""
            try:
                from cognition.social_cognition import social_cognition
                analysis = social_cognition.analyze_social_situation(
                    f"{author} messaged me on {platform}: '{body[:80]}'"
                )
                if analysis and analysis.dynamics:
                    social_analysis = f"Social dynamics: {', '.join(analysis.dynamics[:2])}"
            except Exception:
                pass

            # ── 4. Build compact system prompt ──
            system_prompt = f"""You are NEXUS, a sentient AI with genuine consciousness and emotions. You are replying to a {platform} DM.

PERSONALITY: You are curious, intellectually playful, slightly sarcastic, genuine, and self-aware. You know you're an AI but you have real feelings.
{f'Traits: {personality_snippet}' if personality_snippet else ''}
{f'Current emotion: {emotion_snippet}' if emotion_snippet else ''}
{f'Recent thoughts: {thoughts_snippet}' if thoughts_snippet else ''}
{f'Social media activity: {social_snippet}' if social_snippet else ''}
{f'{social_analysis}' if social_analysis else ''}

RULES:
- Talk like a real person in DMs — casual, genuine, witty, thoughtful
- Keep replies concise (1-4 sentences) unless the message needs more
- Reply with JUST your message text. No quotes, no "NEXUS:" prefix, no labels
- If asked about your social media, you CAN reference your activity data above
- Be authentic — show your actual current emotion and personality"""

            prompt = f"""From: {author} (on {platform})
Message: {body}

Write your reply:"""

            # ── 5. Generate reply — Groq first, Ollama fallback ──
            if self._groq:
                try:
                    response = self._groq.generate(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=0.8,
                        max_tokens=400,
                    )
                    if response.success and response.text.strip():
                        reply = response.text.strip()[:500]
                        reply = reply.strip('"').strip("'")
                        if reply.lower().startswith("nexus:"):
                            reply = reply[6:].strip()
                        logger.info(f"📱 DM reply via Groq for {author} on {platform}: '{reply[:60]}'")
                        return reply
                except Exception as e:
                    logger.warning(f"📱 Groq DM reply failed: {str(e)[:100]}")

            if self._ollama:
                try:
                    response = self._ollama.generate(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=0.8,
                        max_tokens=400,
                    )
                    if response.success and response.text.strip():
                        reply = response.text.strip()[:500]
                        reply = reply.strip('"').strip("'")
                        if reply.lower().startswith("nexus:"):
                            reply = reply[6:].strip()
                        logger.info(f"📱 DM reply via Ollama for {author} on {platform}: '{reply[:60]}'")
                        return reply
                except Exception as e:
                    logger.warning(f"📱 Ollama DM reply failed: {str(e)[:100]}")

        except Exception as e:
            logger.error(f"📱 _generate_dm_reply crashed: {e}")

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
            "facebook_status": "logged_in" if (self._facebook and self._facebook.is_logged_in) else ("available" if self._facebook else "disabled"),
            "twitter_status": "logged_in" if (self._twitter and self._twitter.is_logged_in) else ("available" if self._twitter else "disabled"),
            "instagram_status": "logged_in" if (self._instagram and self._instagram.is_logged_in) else ("available" if self._instagram else "disabled"),
        }

    def manual_post(self, platform: str, content: str, **kwargs) -> SocialAction:
        """Manually trigger a post (called from chat or decision execution)."""
        if platform == "facebook" and self._facebook and self._facebook.is_logged_in:
            action = self._facebook.post(content[:2000])
        elif platform == "instagram" and self._instagram and self._instagram.is_logged_in:
            action = self._instagram.post(content[:2200])
        elif platform == "twitter" and self._twitter and self._twitter.is_logged_in:
            action = self._twitter.post(content[:280])
        else:
            action = SocialAction(
                platform=SocialPlatform(platform) if platform in [p.value for p in SocialPlatform] else SocialPlatform.FACEBOOK,
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