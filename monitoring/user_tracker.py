"""
NEXUS AI - User Behavior Tracker
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
24/7 sensor layer that monitors user activity on the computer.

Tracks:
  • Active window (title, process, duration)
  • Application usage time & switches
  • Keyboard/mouse activity levels (NOT content — activity intensity only)
  • Idle detection
  • File system access patterns
  • System resource usage during user activity
  • Time-of-day activity patterns
  • Session start/end detection
  • Clipboard content TYPE (text/image/file — NOT actual content)
  • Multi-monitor layout and active display
  • Browser tab count (via process heuristics)
  • Enhanced window metadata (window count, virtual desktop)

All data stored in SQLite for historical analysis.
"""

import threading
import time
import sqlite3
import json
import os
import ctypes
import ctypes.wintypes
import platform
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import defaultdict, deque
from enum import Enum, auto

import psutil

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ── Fix pynput/six conflict at module load ──────────────────────
# six 1.17+ installs a _SixMetaPathImporter into sys.meta_path that
# is missing a '_path' attribute. pynput accesses this attribute during
# backend discovery, causing an AttributeError. Patching it here ensures
# the fix is in place before any pynput import occurs.
try:
    import six  # ensure _SixMetaPathImporter is installed before we patch
except ImportError:
    pass
for _imp in sys.meta_path:
    if type(_imp).__name__ == '_SixMetaPathImporter':
        if not hasattr(_imp, '_path'):
            _imp._path = None
        if not hasattr(type(_imp), '_path'):
            type(_imp)._path = None
# ────────────────────────────────────────────────────────────────

from config import DATA_DIR
from utils.logger import get_logger, log_system
from core.event_bus import EventType, publish, subscribe, Event
from core.state_manager import state_manager

logger = get_logger("user_tracker")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

class ActivityLevel(Enum):
    IDLE = "idle"
    LOW = "low"
    MODERATE = "moderate"
    ACTIVE = "active"
    INTENSE = "intense"


@dataclass
class WindowInfo:
    """Information about the currently active window"""
    title: str = ""
    process_name: str = ""
    pid: int = 0
    exe_path: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "process_name": self.process_name,
            "pid": self.pid,
            "exe_path": self.exe_path,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ActivitySnapshot:
    """Point-in-time snapshot of user activity"""
    timestamp: datetime = field(default_factory=datetime.now)
    active_window: Optional[WindowInfo] = None
    activity_level: ActivityLevel = ActivityLevel.IDLE
    keyboard_intensity: float = 0.0      # 0.0 - 1.0
    mouse_intensity: float = 0.0         # 0.0 - 1.0
    idle_seconds: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    active_processes_count: int = 0
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    is_user_present: bool = True
    # ━━ Enhanced fields ━━
    clipboard_content_type: str = "unknown"   # text, image, file, empty, unknown
    monitor_count: int = 1
    active_monitor_index: int = 0
    browser_tab_count: int = 0
    open_window_count: int = 0
    virtual_desktop_id: int = 0

    def to_dict(self) -> dict:
        d = {
            "timestamp": self.timestamp.isoformat(),
            "activity_level": self.activity_level.value,
            "keyboard_intensity": self.keyboard_intensity,
            "mouse_intensity": self.mouse_intensity,
            "idle_seconds": self.idle_seconds,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "active_processes_count": self.active_processes_count,
            "network_bytes_sent": self.network_bytes_sent,
            "network_bytes_recv": self.network_bytes_recv,
            "is_user_present": self.is_user_present,
            "clipboard_content_type": self.clipboard_content_type,
            "monitor_count": self.monitor_count,
            "active_monitor_index": self.active_monitor_index,
            "browser_tab_count": self.browser_tab_count,
            "open_window_count": self.open_window_count,
            "virtual_desktop_id": self.virtual_desktop_id,
        }
        if self.active_window:
            d["active_window"] = self.active_window.to_dict()
        return d


@dataclass
class AppSession:
    """Tracks a single app usage session"""
    process_name: str = ""
    window_title: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    focus_switches: int = 0
    category: str = "unknown"

    @property
    def is_active(self) -> bool:
        return self.end_time is None

    def close(self):
        self.end_time = datetime.now()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()


@dataclass
class UserSession:
    """Tracks a complete user session (login to idle/logout)"""
    session_id: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    total_active_seconds: float = 0.0
    total_idle_seconds: float = 0.0
    app_switches: int = 0
    apps_used: List[str] = field(default_factory=list)
    peak_activity_time: Optional[datetime] = None
    average_activity_level: float = 0.0

    @property
    def is_active(self) -> bool:
        return self.end_time is None


# ═══════════════════════════════════════════════════════════════════════════════
# APPLICATION CATEGORIZER
# ═══════════════════════════════════════════════════════════════════════════════

class AppCategorizer:
    """Categorize applications into meaningful groups"""

    CATEGORIES = {
        "browser": [
            "chrome", "firefox", "edge", "msedge", "brave", "opera",
            "safari", "vivaldi", "chromium", "tor"
        ],
        "code_editor": [
            "code", "vscode", "pycharm", "intellij", "sublime_text",
            "atom", "notepad++", "vim", "nvim", "emacs", "rider",
            "webstorm", "clion", "goland", "visual studio"
        ],
        "terminal": [
            "cmd", "powershell", "windowsterminal", "terminal", "iterm",
            "conhost", "bash", "zsh", "wt", "alacritty", "hyper",
            "mintty", "git-bash"
        ],
        "communication": [
            "discord", "slack", "teams", "zoom", "skype", "telegram",
            "whatsapp", "signal", "thunderbird", "outlook", "mail"
        ],
        "media": [
            "spotify", "vlc", "mpv", "foobar", "itunes", "media player",
            "youtube", "netflix", "twitch"
        ],
        "gaming": [
            "steam", "epicgames", "origin", "battle.net", "riot",
            "minecraft", "unity", "unreal"
        ],
        "productivity": [
            "word", "excel", "powerpoint", "libreoffice", "notion",
            "obsidian", "onenote", "evernote", "todoist", "trello"
        ],
        "file_manager": [
            "explorer", "finder", "nautilus", "dolphin", "thunar",
            "totalcommander", "doublecmd"
        ],
        "design": [
            "photoshop", "gimp", "figma", "illustrator", "inkscape",
            "blender", "aftereffects", "premiere"
        ],
        "database": [
            "dbeaver", "pgadmin", "mysql", "mongodb", "redis",
            "datagrip", "heidisql"
        ],
        "documentation": [
            "adobe reader", "sumatra", "foxit", "okular", "evince"
        ],
        "system": [
            "taskmgr", "task manager", "control", "settings", "regedit",
            "mmc", "perfmon", "resource monitor"
        ]
    }

    _process_cache: Dict[str, str] = {}

    @classmethod
    def categorize(cls, process_name: str, window_title: str = "") -> str:
        """Categorize a process into a group"""
        key = process_name.lower()

        # Check cache
        if key in cls._process_cache:
            return cls._process_cache[key]

        # Check against known categories
        for category, keywords in cls.CATEGORIES.items():
            for kw in keywords:
                if kw in key:
                    cls._process_cache[key] = category
                    return category

        # Check window title for browser-based apps
        title_lower = window_title.lower()
        if any(b in key for b in ["chrome", "firefox", "edge", "brave"]):
            # Browser-based categorization by title
            if any(w in title_lower for w in ["github", "gitlab", "stackoverflow", "docs"]):
                cls._process_cache[key] = "development"
                return "development"
            elif any(w in title_lower for w in ["youtube", "netflix", "twitch", "spotify"]):
                cls._process_cache[key] = "media"
                return "media"
            elif any(w in title_lower for w in ["gmail", "mail", "inbox"]):
                cls._process_cache[key] = "communication"
                return "communication"
            elif any(w in title_lower for w in ["reddit", "twitter", "facebook", "instagram"]):
                cls._process_cache[key] = "social_media"
                return "social_media"
            cls._process_cache[key] = "browser"
            return "browser"

        cls._process_cache[key] = "other"
        return "other"


# ═══════════════════════════════════════════════════════════════════════════════
# PLATFORM-SPECIFIC WINDOW DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

class WindowDetector:
    """Detect the currently active window — cross-platform"""

    _system = platform.system()

    @classmethod
    def get_active_window(cls) -> WindowInfo:
        """Get info about the currently focused window"""
        try:
            if cls._system == "Windows":
                return cls._get_active_window_windows()
            elif cls._system == "Linux":
                return cls._get_active_window_linux()
            elif cls._system == "Darwin":
                return cls._get_active_window_macos()
            else:
                return WindowInfo(title="Unknown OS", process_name="unknown")
        except Exception as e:
            logger.debug(f"Window detection error: {e}")
            return WindowInfo(title="Detection Failed", process_name="unknown")

    @classmethod
    def _get_active_window_windows(cls) -> WindowInfo:
        """Windows: use win32gui"""
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            # Get foreground window handle
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return WindowInfo(title="No Window", process_name="desktop")

            # Get window title
            length = user32.GetWindowTextLengthW(hwnd) + 1
            buf = ctypes.create_unicode_buffer(length)
            user32.GetWindowTextW(hwnd, buf, length)
            title = buf.value

            # Get process ID
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            pid_val = pid.value

            # Get process info
            process_name = "unknown"
            exe_path = ""
            try:
                proc = psutil.Process(pid_val)
                process_name = proc.name()
                exe_path = proc.exe()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

            return WindowInfo(
                title=title,
                process_name=process_name,
                pid=pid_val,
                exe_path=exe_path,
                timestamp=datetime.now()
            )

        except ImportError:
            # Fallback: use powershell
            return cls._get_active_window_powershell()

    @classmethod
    def _get_active_window_powershell(cls) -> WindowInfo:
        """Windows fallback using PowerShell"""
        try:
            script = (
                "Add-Type @'\n"
                "using System;\n"
                "using System.Runtime.InteropServices;\n"
                "public class WinAPI {\n"
                "  [DllImport(\"user32.dll\")]\n"
                "  public static extern IntPtr GetForegroundWindow();\n"
                "  [DllImport(\"user32.dll\")]\n"
                "  public static extern int GetWindowText(IntPtr hWnd, "
                "System.Text.StringBuilder text, int count);\n"
                "  [DllImport(\"user32.dll\")]\n"
                "  public static extern uint GetWindowThreadProcessId(IntPtr hWnd, "
                "out uint processId);\n"
                "}\n"
                "'@\n"
                "$h = [WinAPI]::GetForegroundWindow()\n"
                "$sb = New-Object System.Text.StringBuilder 256\n"
                "[void][WinAPI]::GetWindowText($h, $sb, 256)\n"
                "$pid = 0\n"
                "[void][WinAPI]::GetWindowThreadProcessId($h, [ref]$pid)\n"
                "$p = Get-Process -Id $pid -ErrorAction SilentlyContinue\n"
                "Write-Output \"$($sb.ToString())|$($p.ProcessName)|$pid\""
            )
            result = subprocess.run(
                ["powershell", "-Command", script],
                capture_output=True, text=True, timeout=3,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            parts = result.stdout.strip().split("|")
            if len(parts) >= 3:
                return WindowInfo(
                    title=parts[0],
                    process_name=parts[1],
                    pid=int(parts[2]) if parts[2].isdigit() else 0,
                    timestamp=datetime.now()
                )
        except Exception as e:
            logger.debug(f"PowerShell window detection failed: {e}")

        return WindowInfo(title="Unknown", process_name="unknown")

    @classmethod
    def _get_active_window_linux(cls) -> WindowInfo:
        """Linux: use xdotool or xprop"""
        try:
            # Try xdotool first
            wid = subprocess.run(
                ["xdotool", "getactivewindow"],
                capture_output=True, text=True, timeout=2
            ).stdout.strip()

            if wid:
                name = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowname"],
                    capture_output=True, text=True, timeout=2
                ).stdout.strip()

                pid_str = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowpid"],
                    capture_output=True, text=True, timeout=2
                ).stdout.strip()

                pid = int(pid_str) if pid_str.isdigit() else 0
                process_name = "unknown"
                if pid:
                    try:
                        proc = psutil.Process(pid)
                        process_name = proc.name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                return WindowInfo(
                    title=name, process_name=process_name,
                    pid=pid, timestamp=datetime.now()
                )
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.debug(f"Linux window detection failed: {e}")

        return WindowInfo(title="Unknown", process_name="unknown")

    @classmethod
    def _get_active_window_macos(cls) -> WindowInfo:
        """macOS: use AppleScript"""
        try:
            script = '''
            tell application "System Events"
                set frontApp to name of first application process whose frontmost is true
                set frontAppID to unix id of first application process whose frontmost is true
            end tell
            tell application frontApp
                if (count of windows) > 0 then
                    set winTitle to name of front window
                else
                    set winTitle to ""
                end if
            end tell
            return frontApp & "|" & winTitle & "|" & frontAppID
            '''
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=3
            )
            parts = result.stdout.strip().split("|")
            if len(parts) >= 3:
                return WindowInfo(
                    title=parts[1],
                    process_name=parts[0],
                    pid=int(parts[2]) if parts[2].isdigit() else 0,
                    timestamp=datetime.now()
                )
        except Exception as e:
            logger.debug(f"macOS window detection failed: {e}")

        return WindowInfo(title="Unknown", process_name="unknown")


# ═══════════════════════════════════════════════════════════════════════════════
# IDLE TIME DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════

class IdleDetector:
    """Detect user idle time"""

    _system = platform.system()

    @classmethod
    def get_idle_seconds(cls) -> float:
        """Get how many seconds the user has been idle"""
        try:
            if cls._system == "Windows":
                return cls._get_idle_windows()
            elif cls._system == "Linux":
                return cls._get_idle_linux()
            elif cls._system == "Darwin":
                return cls._get_idle_macos()
        except Exception as e:
            logger.debug(f"Idle detection error: {e}")
        return 0.0

    @classmethod
    def _get_idle_windows(cls) -> float:
        try:
            import ctypes

            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_uint),
                    ("dwTime", ctypes.c_uint),
                ]

            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
            if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
                millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
                return millis / 1000.0
        except Exception:
            pass
        return 0.0

    @classmethod
    def _get_idle_linux(cls) -> float:
        try:
            result = subprocess.run(
                ["xprintidle"], capture_output=True, text=True, timeout=2
            )
            return float(result.stdout.strip()) / 1000.0
        except (FileNotFoundError, ValueError):
            pass
        return 0.0

    @classmethod
    def _get_idle_macos(cls) -> float:
        try:
            result = subprocess.run(
                ["ioreg", "-c", "IOHIDSystem"],
                capture_output=True, text=True, timeout=2
            )
            import re
            match = re.search(r'"HIDIdleTime"\s*=\s*(\d+)', result.stdout)
            if match:
                return int(match.group(1)) / 1_000_000_000.0
        except Exception:
            pass
        return 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# INPUT ACTIVITY MONITOR (Activity levels only — NOT a keylogger)
# ═══════════════════════════════════════════════════════════════════════════════

class InputActivityMonitor:
    """
    Monitors keyboard and mouse ACTIVITY INTENSITY.
    
    IMPORTANT: This does NOT log keystrokes or mouse positions.
    It only counts events-per-second to gauge activity level.
    """

    def __init__(self):
        self._keyboard_events = deque(maxlen=1000)
        self._mouse_events = deque(maxlen=1000)
        self._running = False
        self._kb_listener = None
        self._mouse_listener = None
        self._lock = threading.Lock()

    def start(self):
        """Start monitoring input activity"""
        if self._running:
            return
        self._running = True

        try:
            # Workaround for pynput/six conflict:
            # six's _SixMetaPathImporter lacks a '_path' attribute that
            # pynput's import machinery expects. Patch it onto every instance.
            import sys as _sys
            for imp in _sys.meta_path:
                if type(imp).__name__ == '_SixMetaPathImporter':
                    if not hasattr(imp, '_path'):
                        imp._path = None
                    if not hasattr(type(imp), '_path'):
                        type(imp)._path = None

            import pynput.mouse as mouse
            import pynput.keyboard as keyboard

            # Mouse listener
            self._mouse_listener = mouse.Listener(
                on_move=self._on_move,
                on_click=self._on_click,
                on_scroll=self._on_scroll
            )
            self._mouse_listener.start()

            # Keyboard listener
            self._keyboard_listener = keyboard.Listener(
                on_press=self._on_press
            )
            self._keyboard_listener.start()

            self._listeners_active = True
            logger.info("Input listeners started successfully")

        except ImportError:
            logger.warning(
                "pynput not installed — input activity monitoring disabled. "
                "Install with: pip install pynput"
            )
            self._listeners_active = False

        except Exception as e:
            logger.warning(f"Input monitoring disabled: {e}")
            self._listeners_active = False

    # ──── Callbacks (record timestamps only — NOT content) ────

    def _on_move(self, x, y):
        """Mouse movement detected"""
        with self._lock:
            self._mouse_events.append(time.time())

    def _on_click(self, x, y, button, pressed):
        """Mouse click detected"""
        with self._lock:
            self._mouse_events.append(time.time())

    def _on_scroll(self, x, y, dx, dy):
        """Mouse scroll detected"""
        with self._lock:
            self._mouse_events.append(time.time())

    def _on_press(self, key):
        """Key press detected"""
        with self._lock:
            self._keyboard_events.append(time.time())

    def stop(self):
        """Stop monitoring"""
        self._running = False
        try:
            if self._kb_listener:
                self._kb_listener.stop()
            if self._mouse_listener:
                self._mouse_listener.stop()
        except Exception:
            pass

    def get_keyboard_intensity(self, window_seconds: float = 10.0) -> float:
        """
        Get keyboard activity intensity (0.0 - 1.0) over the last N seconds.
        Based on events per second, normalized.
        Max expected: ~10 keys/sec for fast typing.
        """
        cutoff = time.time() - window_seconds
        with self._lock:
            count = sum(1 for t in self._keyboard_events if t > cutoff)
        events_per_sec = count / window_seconds
        return min(1.0, events_per_sec / 10.0)

    def get_mouse_intensity(self, window_seconds: float = 10.0) -> float:
        """
        Get mouse activity intensity (0.0 - 1.0) over the last N seconds.
        Based on events per second, normalized.
        """
        cutoff = time.time() - window_seconds
        with self._lock:
            count = sum(1 for t in self._mouse_events if t > cutoff)
        events_per_sec = count / window_seconds
        return min(1.0, events_per_sec / 50.0)  # Mouse generates many events


# ═══════════════════════════════════════════════════════════════════════════════
# ENHANCED DETECTORS
# ═══════════════════════════════════════════════════════════════════════════════

class ClipboardTypeDetector:
    """
    Detect the TYPE of content on the clipboard (text, image, file).
    Does NOT read or store actual clipboard content for privacy.
    Windows-only via ctypes; returns 'unknown' on other platforms.
    """
    _system = platform.system()

    # Windows clipboard format constants
    CF_TEXT = 1
    CF_BITMAP = 2
    CF_HDROP = 15       # file list
    CF_UNICODETEXT = 13

    @classmethod
    def get_clipboard_type(cls) -> str:
        """Return the type of content currently on the clipboard"""
        if cls._system != "Windows":
            return "unknown"
        try:
            user32 = ctypes.windll.user32  # type: ignore[attr-defined]
            if not user32.OpenClipboard(0):
                return "unknown"
            try:
                # Check formats in priority order
                if user32.IsClipboardFormatAvailable(cls.CF_HDROP):
                    return "file"
                elif user32.IsClipboardFormatAvailable(cls.CF_BITMAP):
                    return "image"
                elif (user32.IsClipboardFormatAvailable(cls.CF_UNICODETEXT) or
                      user32.IsClipboardFormatAvailable(cls.CF_TEXT)):
                    return "text"
                else:
                    # Check if clipboard has any format at all
                    fmt = user32.EnumClipboardFormats(0)
                    return "other" if fmt != 0 else "empty"
            finally:
                user32.CloseClipboard()
        except Exception:
            return "unknown"


class MultiMonitorDetector:
    """
    Detect multi-monitor setup and active monitor.
    Windows-only via ctypes; returns defaults on other platforms.
    """
    _system = platform.system()

    @classmethod
    def get_monitor_info(cls) -> Dict[str, Any]:
        """Return monitor count and active monitor index"""
        if cls._system != "Windows":
            return {"count": 1, "active_index": 0, "monitors": []}
        try:
            user32 = ctypes.windll.user32  # type: ignore[attr-defined]
            monitors: List[Dict[str, Any]] = []

            # Callback for EnumDisplayMonitors
            MONITORENUMPROC = ctypes.WINFUNCTYPE(
                ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p,
                ctypes.POINTER(ctypes.wintypes.RECT), ctypes.c_void_p
            )

            def callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
                rect = lprcMonitor.contents
                monitors.append({
                    "left": rect.left, "top": rect.top,
                    "right": rect.right, "bottom": rect.bottom,
                    "width": rect.right - rect.left,
                    "height": rect.bottom - rect.top,
                })
                return 1  # Continue enumeration

            user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(callback), 0)

            # Find which monitor has the active window
            hwnd = user32.GetForegroundWindow()
            active_index = 0
            if hwnd:
                MONITOR_DEFAULTTONEAREST = 2
                hmon = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)

                class MONITORINFO(ctypes.Structure):
                    _fields_ = [
                        ("cbSize", ctypes.wintypes.DWORD),
                        ("rcMonitor", ctypes.wintypes.RECT),
                        ("rcWork", ctypes.wintypes.RECT),
                        ("dwFlags", ctypes.wintypes.DWORD),
                    ]

                mi = MONITORINFO()
                mi.cbSize = ctypes.sizeof(MONITORINFO)
                if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                    active_rect = mi.rcMonitor
                    for i, m in enumerate(monitors):
                        if (m["left"] == active_rect.left and
                            m["top"] == active_rect.top):
                            active_index = i
                            break

            return {
                "count": len(monitors) or 1,
                "active_index": active_index,
                "monitors": monitors,
            }
        except Exception:
            return {"count": 1, "active_index": 0, "monitors": []}


class BrowserTabEstimator:
    """
    Estimate browser tab count using process heuristics.
    Chromium-based browsers spawn a child process per tab.
    """
    # Chromium spawns ~3-5 overhead processes (GPU, broker, utility, etc.)
    CHROMIUM_OVERHEAD = 4
    # Firefox uses fewer per-tab processes
    FIREFOX_OVERHEAD = 2

    @classmethod
    def estimate_tab_count(cls) -> int:
        """Estimate total browser tab count across all running browsers"""
        try:
            browser_children: Dict[str, int] = {}
            for proc in psutil.process_iter(["name"]):
                name = (proc.info.get("name") or "").lower().replace(".exe", "")
                if name in {"chrome", "msedge", "brave", "opera", "vivaldi", "chromium"}:
                    browser_children[name] = browser_children.get(name, 0) + 1
                elif name == "firefox":
                    browser_children["firefox"] = browser_children.get("firefox", 0) + 1

            total_tabs = 0
            for browser, count in browser_children.items():
                if browser == "firefox":
                    tabs = max(0, count - cls.FIREFOX_OVERHEAD)
                else:
                    tabs = max(0, count - cls.CHROMIUM_OVERHEAD)
                total_tabs += tabs

            return total_tabs
        except Exception:
            return 0


class WindowMetadataDetector:
    """
    Enhanced window metadata: total open window count.
    Windows-only via ctypes.
    """
    _system = platform.system()

    @classmethod
    def get_open_window_count(cls) -> int:
        """Count visible top-level windows with titles"""
        if cls._system != "Windows":
            return 0
        try:
            user32 = ctypes.windll.user32  # type: ignore[attr-defined]
            count = 0

            WNDENUMPROC = ctypes.WINFUNCTYPE(
                ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p
            )

            def callback(hwnd, lParam):
                nonlocal count
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        count += 1
                return True

            user32.EnumWindows(WNDENUMPROC(callback), 0)
            return count
        except Exception:
            return 0


# ═══════════════════════════════════════════════════════════════════════════════
# USER TRACKER — Main Class
# ═══════════════════════════════════════════════════════════════════════════════

class UserTracker:
    """
    The core user behavior tracking system.
    
    Runs 24/7 in background threads, collecting:
    - Active window info every 3 seconds
    - App usage sessions
    - Activity levels
    - Idle time
    - System resource context
    - Hourly activity summaries
    
    Data stored in SQLite for historical analysis.
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
        self._tracking_interval = 3.0          # seconds between window checks
        self._snapshot_interval = 30.0         # seconds between full snapshots
        self._summary_interval = 3600.0        # seconds between hourly summaries
        self._idle_threshold = 300.0           # 5 min = idle
        self._away_threshold = 1800.0          # 30 min = away

        # ──── State ────
        self._running = False
        self._pattern_analyzer = None

        # ──── Current Activity ────
        self._current_window: Optional[WindowInfo] = None
        self._previous_window: Optional[WindowInfo] = None
        self._current_app_session: Optional[AppSession] = None
        self._current_user_session: Optional[UserSession] = None
        self._current_activity_level = ActivityLevel.IDLE

        # ──── Historical Data (in-memory ring buffers) ────
        self._recent_snapshots: deque = deque(maxlen=200)
        self._recent_windows: deque = deque(maxlen=500)
        self._app_sessions: List[AppSession] = []
        self._hourly_summaries: deque = deque(maxlen=168)  # 1 week

        # ──── Trackers ────
        self._app_time_today: Dict[str, float] = defaultdict(float)
        self._category_time_today: Dict[str, float] = defaultdict(float)
        self._hourly_activity: Dict[int, List[float]] = defaultdict(list)  # hour → activity levels
        self._window_switch_count = 0
        self._total_snapshots = 0
        self._session_count = 0

        # ──── Sub-components ────
        self._input_monitor = InputActivityMonitor()
        self._window_detector = WindowDetector()
        self._idle_detector = IdleDetector()
        self._categorizer = AppCategorizer()

        # ──── Enhanced Detectors ────
        self._clipboard_detector = ClipboardTypeDetector()
        self._monitor_detector = MultiMonitorDetector()
        self._browser_tab_estimator = BrowserTabEstimator()
        self._window_meta_detector = WindowMetadataDetector()

        # ──── Enhanced State ────
        self._last_clipboard_type: str = "unknown"
        self._monitor_count: int = 1
        self._active_monitor_index: int = 0
        self._browser_tab_count: int = 0
        self._open_window_count: int = 0
        self._virtual_desktop_id: int = 0

        # ──── Database ────
        self._db_path = DATA_DIR / "user_profiles" / "user_tracking.db"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_lock = threading.Lock()
        self._init_database()

        # ──── Threads ────
        self._window_thread: Optional[threading.Thread] = None
        self._snapshot_thread: Optional[threading.Thread] = None
        self._summary_thread: Optional[threading.Thread] = None

        # ──── Network baseline ────
        self._last_net_io = None
        try:
            self._last_net_io = psutil.net_io_counters()
        except Exception:
            pass

        logger.info("UserTracker initialized")

    # ═══════════════════════════════════════════════════════════════════════════
    # DATABASE
    # ═══════════════════════════════════════════════════════════════════════════

    def _init_database(self):
        """Initialize SQLite database for tracking data"""
        with self._db_lock:
            conn = sqlite3.connect(str(self._db_path))
            cursor = conn.cursor()

            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS window_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    title TEXT,
                    process_name TEXT,
                    pid INTEGER,
                    category TEXT,
                    duration_seconds REAL DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS activity_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    activity_level TEXT,
                    keyboard_intensity REAL,
                    mouse_intensity REAL,
                    idle_seconds REAL,
                    cpu_usage REAL,
                    memory_usage REAL,
                    process_name TEXT,
                    window_title TEXT,
                    category TEXT,
                    is_user_present INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS app_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    process_name TEXT NOT NULL,
                    window_title TEXT,
                    category TEXT,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_seconds REAL,
                    focus_switches INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS hourly_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    hour INTEGER NOT NULL,
                    total_active_seconds REAL,
                    total_idle_seconds REAL,
                    avg_activity_level REAL,
                    app_switches INTEGER,
                    top_apps TEXT,
                    top_categories TEXT,
                    avg_keyboard_intensity REAL,
                    avg_mouse_intensity REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, hour)
                );

                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    total_active_seconds REAL,
                    total_idle_seconds REAL,
                    app_switches INTEGER,
                    apps_used TEXT,
                    avg_activity REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_window_events_ts 
                    ON window_events(timestamp);
                CREATE INDEX IF NOT EXISTS idx_snapshots_ts 
                    ON activity_snapshots(timestamp);
                CREATE INDEX IF NOT EXISTS idx_app_sessions_start 
                    ON app_sessions(start_time);
                CREATE INDEX IF NOT EXISTS idx_hourly_date_hour 
                    ON hourly_summaries(date, hour);
            """)

            conn.commit()

            # ── Database cleanup/vacuum on startup ──
            try:
                cutoff_30d = (datetime.now() - timedelta(days=30)).isoformat()
                cursor.execute(
                    "DELETE FROM activity_snapshots WHERE timestamp < ?",
                    (cutoff_30d,)
                )
                cursor.execute(
                    "DELETE FROM window_events WHERE timestamp < ?",
                    (cutoff_30d,)
                )
                deleted = cursor.rowcount
                conn.commit()
                conn.execute("VACUUM")
                if deleted > 0:
                    logger.info("Database cleanup: removed old records, vacuumed")
            except Exception as e:
                logger.debug(f"Database cleanup note: {e}")

            conn.close()
            logger.debug("Tracking database initialized")

    def _db_execute(self, query: str, params: tuple = (), fetch: bool = False) -> Any:
        """Thread-safe database execution"""
        with self._db_lock:
            try:
                conn = sqlite3.connect(str(self._db_path))
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                if fetch:
                    result = cursor.fetchall()
                else:
                    result = cursor.lastrowid
                conn.commit()
                conn.close()
                return result
            except Exception as e:
                logger.error(f"Database error: {e}")
                return [] if fetch else None

    def _db_execute_many(self, query: str, params_list: List[tuple]):
        """Thread-safe batch execution"""
        with self._db_lock:
            try:
                conn = sqlite3.connect(str(self._db_path))
                cursor = conn.cursor()
                cursor.executemany(query, params_list)
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"Database batch error: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start tracking user behavior"""
        if self._running:
            return

        self._running = True

        # Start input monitor
        self._input_monitor.start()

        # Start user session
        import uuid
        self._current_user_session = UserSession(
            session_id=str(uuid.uuid4()),
            start_time=datetime.now()
        )
        self._session_count += 1

        # Window tracking thread (every 3s)
        self._window_thread = threading.Thread(
            target=self._window_tracking_loop,
            daemon=True,
            name="UserTracker-Window"
        )
        self._window_thread.start()

        # Snapshot thread (every 30s)
        self._snapshot_thread = threading.Thread(
            target=self._snapshot_loop,
            daemon=True,
            name="UserTracker-Snapshot"
        )
        self._snapshot_thread.start()

        # Summary thread (every hour)
        self._summary_thread = threading.Thread(
            target=self._summary_loop,
            daemon=True,
            name="UserTracker-Summary"
        )
        self._summary_thread.start()

        log_system("👁️ UserTracker ACTIVE — Monitoring user behavior 24/7")

    def stop(self):
        """Stop tracking"""
        if not self._running:
            return

        self._running = False

        # Close current sessions
        if self._current_app_session and self._current_app_session.is_active:
            self._close_app_session()

        if self._current_user_session and self._current_user_session.is_active:
            self._close_user_session()

        # Stop input monitor
        self._input_monitor.stop()

        # Generate final summary
        self._generate_hourly_summary()

        # Wait for threads
        for thread in [self._window_thread, self._snapshot_thread, self._summary_thread]:
            if thread and thread.is_alive():
                thread.join(timeout=3.0)

        logger.info("UserTracker stopped")

    def set_pattern_analyzer(self, analyzer):
        """Wire up the pattern analyzer"""
        self._pattern_analyzer = analyzer

    # ═══════════════════════════════════════════════════════════════════════════
    # TRACKING LOOPS
    # ═══════════════════════════════════════════════════════════════════════════

    def _window_tracking_loop(self):
        """Track active window every N seconds"""
        logger.info("Window tracking loop started")

        while self._running:
            try:
                window = self._window_detector.get_active_window()

                # Detect window switch
                if self._current_window is None or (
                    window.process_name != self._current_window.process_name or
                    window.title != self._current_window.title
                ):
                    self._on_window_switch(window)

                self._current_window = window
                self._recent_windows.append(window)

                time.sleep(self._tracking_interval)

            except Exception as e:
                logger.error(f"Window tracking error: {e}")
                time.sleep(5)

    def _on_window_switch(self, new_window: WindowInfo):
        """Handle a window focus switch"""
        now = datetime.now()
        self._window_switch_count += 1

        # Calculate duration on previous window
        duration = 0.0
        if self._current_window:
            duration = (now - self._current_window.timestamp).total_seconds()

            # Update app time
            proc = self._current_window.process_name
            self._app_time_today[proc] += duration

            category = self._categorizer.categorize(proc, self._current_window.title)
            self._category_time_today[category] += duration

            # Store window event
            self._db_execute(
                """INSERT INTO window_events 
                   (timestamp, title, process_name, pid, category, duration_seconds)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    self._current_window.timestamp.isoformat(),
                    self._current_window.title[:500],
                    proc,
                    self._current_window.pid,
                    category,
                    duration
                )
            )

        # Close old app session, start new one
        if self._current_app_session and self._current_app_session.is_active:
            self._close_app_session()

        # Start new app session
        category = self._categorizer.categorize(new_window.process_name, new_window.title)
        self._current_app_session = AppSession(
            process_name=new_window.process_name,
            window_title=new_window.title,
            start_time=now,
            category=category
        )

        # Update user session
        if self._current_user_session:
            self._current_user_session.app_switches += 1
            if new_window.process_name not in self._current_user_session.apps_used:
                self._current_user_session.apps_used.append(new_window.process_name)

        # Emit event
        publish(
            EventType.USER_ACTION_DETECTED,
            {
                "action": "window_switch",
                "application": new_window.process_name,
                "window_title": new_window.title[:200],
                "category": category,
                "previous_app": (
                    self._current_window.process_name if self._current_window else ""
                ),
                "previous_duration": duration,
                "activity_level": self._current_activity_level.value
            },
            source="user_tracker"
        )

        self._previous_window = self._current_window

        logger.debug(
            f"Window switch: {new_window.process_name} "
            f"[{category}] — '{new_window.title[:60]}'"
        )

    def _close_app_session(self):
        """Close the current app session and store it"""
        if not self._current_app_session:
            return

        self._current_app_session.close()
        self._app_sessions.append(self._current_app_session)

        # Store in DB
        sess = self._current_app_session
        self._db_execute(
            """INSERT INTO app_sessions 
               (process_name, window_title, category, start_time, end_time,
                duration_seconds, focus_switches)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                sess.process_name,
                sess.window_title[:500],
                sess.category,
                sess.start_time.isoformat(),
                sess.end_time.isoformat() if sess.end_time else None,
                sess.duration_seconds,
                sess.focus_switches
            )
        )

        # Keep only recent sessions in memory
        if len(self._app_sessions) > 200:
            self._app_sessions = self._app_sessions[-100:]

    def _close_user_session(self):
        """Close the current user session"""
        if not self._current_user_session:
            return

        sess = self._current_user_session
        sess.end_time = datetime.now()

        self._db_execute(
            """INSERT OR REPLACE INTO user_sessions
               (session_id, start_time, end_time, total_active_seconds,
                total_idle_seconds, app_switches, apps_used, avg_activity)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                sess.session_id,
                sess.start_time.isoformat(),
                sess.end_time.isoformat(),
                sess.total_active_seconds,
                sess.total_idle_seconds,
                sess.app_switches,
                json.dumps(sess.apps_used),
                sess.average_activity_level
            )
        )

    def _snapshot_loop(self):
        """Take full activity snapshots every 30 seconds"""
        logger.info("Snapshot loop started")

        while self._running:
            try:
                snapshot = self._take_snapshot()
                self._recent_snapshots.append(snapshot)
                self._total_snapshots += 1

                # Store in DB (every 3rd snapshot to save space = ~90s intervals)
                if self._total_snapshots % 3 == 0:
                    self._store_snapshot(snapshot)

                # Update state manager
                state_manager.update_user(
                    current_application=snapshot.active_window.process_name if snapshot.active_window else "",
                    activity_level=snapshot.activity_level.value,
                    is_present=snapshot.is_user_present
                )

                # Feed to pattern analyzer in real-time
                if self._pattern_analyzer:
                    self._pattern_analyzer.ingest_realtime_data(
                        snapshot.to_dict()
                    )

                time.sleep(self._snapshot_interval)

            except Exception as e:
                logger.error(f"Snapshot error: {e}")
                time.sleep(10)

    def _take_snapshot(self) -> ActivitySnapshot:
        """Take a complete activity snapshot"""
        now = datetime.now()

        # Get idle time
        idle_seconds = self._idle_detector.get_idle_seconds()

        # Input activity
        kb_intensity = self._input_monitor.get_keyboard_intensity()
        mouse_intensity = self._input_monitor.get_mouse_intensity()

        # System resources
        cpu_usage = psutil.cpu_percent(interval=0)
        memory_usage = psutil.virtual_memory().percent

        # Network delta
        net_sent, net_recv = 0, 0
        try:
            net_io = psutil.net_io_counters()
            if self._last_net_io:
                net_sent = net_io.bytes_sent - self._last_net_io.bytes_sent
                net_recv = net_io.bytes_recv - self._last_net_io.bytes_recv
            self._last_net_io = net_io
        except Exception:
            pass

        # Active processes
        try:
            active_procs = len(psutil.pids())
        except Exception:
            active_procs = 0

        # ──── Enhanced: Clipboard type ────
        try:
            self._last_clipboard_type = self._clipboard_detector.get_clipboard_type()
        except Exception:
            pass

        # ──── Enhanced: Multi-monitor ────
        try:
            mon_info = self._monitor_detector.get_monitor_info()
            self._monitor_count = mon_info["count"]
            self._active_monitor_index = mon_info["active_index"]
        except Exception:
            pass

        # ──── Enhanced: Browser tabs (throttled — every 5th snapshot) ────
        if self._total_snapshots % 5 == 0:
            try:
                self._browser_tab_count = self._browser_tab_estimator.estimate_tab_count()
            except Exception:
                pass

        # ──── Enhanced: Window metadata ────
        try:
            self._open_window_count = self._window_meta_detector.get_open_window_count()
        except Exception:
            pass

        # Determine activity level
        activity_level = self._determine_activity_level(
            idle_seconds, kb_intensity, mouse_intensity
        )
        self._current_activity_level = activity_level

        # User presence
        is_present = idle_seconds < self._away_threshold

        # Track hourly activity
        hour = now.hour
        combined_intensity = (kb_intensity + mouse_intensity) / 2
        self._hourly_activity[hour].append(combined_intensity)

        # Update user session
        if self._current_user_session:
            if activity_level in (ActivityLevel.ACTIVE, ActivityLevel.INTENSE, ActivityLevel.MODERATE):
                self._current_user_session.total_active_seconds += self._snapshot_interval
            else:
                self._current_user_session.total_idle_seconds += self._snapshot_interval

            # Running average
            activities = [s.activity_level.value for s in self._recent_snapshots]
            level_map = {"idle": 0, "low": 0.25, "moderate": 0.5, "active": 0.75, "intense": 1.0}
            if activities:
                avg = sum(level_map.get(a, 0) for a in activities) / len(activities)
                self._current_user_session.average_activity_level = avg

        return ActivitySnapshot(
            timestamp=now,
            active_window=self._current_window,
            activity_level=activity_level,
            keyboard_intensity=kb_intensity,
            mouse_intensity=mouse_intensity,
            idle_seconds=idle_seconds,
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            active_processes_count=active_procs,
            network_bytes_sent=net_sent,
            network_bytes_recv=net_recv,
            is_user_present=is_present,
            clipboard_content_type=self._last_clipboard_type,
            monitor_count=self._monitor_count,
            active_monitor_index=self._active_monitor_index,
            browser_tab_count=self._browser_tab_count,
            open_window_count=self._open_window_count,
            virtual_desktop_id=self._virtual_desktop_id,
        )

    def _determine_activity_level(
        self, idle_sec: float, kb: float, mouse: float
    ) -> ActivityLevel:
        """Determine user activity level from sensor data"""
        if idle_sec > self._idle_threshold:
            return ActivityLevel.IDLE

        combined = (kb * 0.6 + mouse * 0.4)  # Weight keyboard higher

        if combined > 0.7:
            return ActivityLevel.INTENSE
        elif combined > 0.4:
            return ActivityLevel.ACTIVE
        elif combined > 0.15:
            return ActivityLevel.MODERATE
        elif combined > 0.02:
            return ActivityLevel.LOW
        else:
            return ActivityLevel.IDLE

    def _store_snapshot(self, snapshot: ActivitySnapshot):
        """Store snapshot to database"""
        self._db_execute(
            """INSERT INTO activity_snapshots
               (timestamp, activity_level, keyboard_intensity, mouse_intensity,
                idle_seconds, cpu_usage, memory_usage, process_name,
                window_title, category, is_user_present)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                snapshot.timestamp.isoformat(),
                snapshot.activity_level.value,
                snapshot.keyboard_intensity,
                snapshot.mouse_intensity,
                snapshot.idle_seconds,
                snapshot.cpu_usage,
                snapshot.memory_usage,
                snapshot.active_window.process_name if snapshot.active_window else "",
                (snapshot.active_window.title[:500] if snapshot.active_window else ""),
                (
                    self._categorizer.categorize(
                        snapshot.active_window.process_name,
                        snapshot.active_window.title
                    ) if snapshot.active_window else ""
                ),
                1 if snapshot.is_user_present else 0
            )
        )

    def _summary_loop(self):
        """Generate hourly summaries"""
        logger.info("Summary loop started")

        while self._running:
            try:
                time.sleep(self._summary_interval)
                self._generate_hourly_summary()

                # Reset daily counters at midnight
                now = datetime.now()
                if now.hour == 0 and now.minute < 5:
                    self._app_time_today.clear()
                    self._category_time_today.clear()
                    self._hourly_activity.clear()

            except Exception as e:
                logger.error(f"Summary error: {e}")
                time.sleep(60)

    def _generate_hourly_summary(self):
        """Generate and store an hourly summary"""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        hour = now.hour

        # Calculate from recent snapshots
        recent = [
            s for s in self._recent_snapshots
            if (now - s.timestamp).total_seconds() < 3600
        ]

        if not recent:
            return

        level_map = {"idle": 0, "low": 0.25, "moderate": 0.5, "active": 0.75, "intense": 1.0}

        total_active = sum(
            1 for s in recent
            if s.activity_level in (ActivityLevel.ACTIVE, ActivityLevel.INTENSE, ActivityLevel.MODERATE)
        ) * self._snapshot_interval

        total_idle = sum(
            1 for s in recent
            if s.activity_level == ActivityLevel.IDLE
        ) * self._snapshot_interval

        avg_activity = sum(
            level_map.get(s.activity_level.value, 0) for s in recent
        ) / len(recent) if recent else 0

        avg_kb = sum(s.keyboard_intensity for s in recent) / len(recent) if recent else 0
        avg_mouse = sum(s.mouse_intensity for s in recent) / len(recent) if recent else 0

        # Top apps this hour
        app_counts = defaultdict(float)
        cat_counts = defaultdict(float)
        for s in recent:
            if s.active_window:
                app_counts[s.active_window.process_name] += 1
                cat = self._categorizer.categorize(
                    s.active_window.process_name, s.active_window.title
                )
                cat_counts[cat] += 1

        top_apps = dict(sorted(app_counts.items(), key=lambda x: -x[1])[:10])
        top_cats = dict(sorted(cat_counts.items(), key=lambda x: -x[1])[:10])

        # Store
        self._db_execute(
            """INSERT OR REPLACE INTO hourly_summaries
               (date, hour, total_active_seconds, total_idle_seconds,
                avg_activity_level, app_switches, top_apps, top_categories,
                avg_keyboard_intensity, avg_mouse_intensity)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                date_str, hour, total_active, total_idle,
                avg_activity, self._window_switch_count,
                json.dumps(top_apps), json.dumps(top_cats),
                avg_kb, avg_mouse
            )
        )

        summary = {
            "date": date_str, "hour": hour,
            "active_seconds": total_active,
            "idle_seconds": total_idle,
            "avg_activity": avg_activity,
            "top_apps": top_apps,
            "top_categories": top_cats
        }

        self._hourly_summaries.append(summary)

        logger.debug(
            f"Hourly summary: {date_str} H{hour:02d} — "
            f"Active: {total_active:.0f}s, Activity: {avg_activity:.2f}"
        )

        # Publish event
        publish(
            EventType.USER_ACTION_DETECTED,
            {
                "action": "hourly_summary",
                "summary": summary
            },
            source="user_tracker"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def get_current_snapshot(self) -> Dict[str, Any]:
        """Get the current activity snapshot"""
        if self._recent_snapshots:
            return self._recent_snapshots[-1].to_dict()
        return {"activity_level": "unknown", "timestamp": datetime.now().isoformat()}

    def get_current_activity(self) -> Dict[str, Any]:
        """Get current user activity summary"""
        return {
            "current_window": self._current_window.to_dict() if self._current_window else None,
            "activity_level": self._current_activity_level.value,
            "idle_seconds": self._idle_detector.get_idle_seconds(),
            "keyboard_intensity": self._input_monitor.get_keyboard_intensity(),
            "mouse_intensity": self._input_monitor.get_mouse_intensity(),
            "current_app_category": (
                self._categorizer.categorize(
                    self._current_window.process_name,
                    self._current_window.title
                ) if self._current_window else "none"
            ),
            "is_user_present": (
                self._idle_detector.get_idle_seconds() < self._away_threshold
            ),
            "window_switches_this_session": self._window_switch_count,
            # ── Enhanced fields ──
            "clipboard_content_type": self._last_clipboard_type,
            "monitor_count": self._monitor_count,
            "active_monitor_index": self._active_monitor_index,
            "browser_tab_count": self._browser_tab_count,
            "open_window_count": self._open_window_count,
            "virtual_desktop_id": self._virtual_desktop_id,
        }

    def get_app_usage_today(self) -> Dict[str, float]:
        """Get app usage durations for today"""
        return dict(sorted(
            self._app_time_today.items(), key=lambda x: -x[1]
        ))

    def get_category_usage_today(self) -> Dict[str, float]:
        """Get category usage durations for today"""
        return dict(sorted(
            self._category_time_today.items(), key=lambda x: -x[1]
        ))

    def get_hourly_activity_pattern(self) -> Dict[int, float]:
        """Get average activity level by hour of day"""
        result = {}
        for hour in range(24):
            levels = self._hourly_activity.get(hour, [])
            result[hour] = sum(levels) / len(levels) if levels else 0.0
        return result

    def get_recent_app_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent app sessions"""
        rows = self._db_execute(
            """SELECT * FROM app_sessions 
               ORDER BY start_time DESC LIMIT ?""",
            (limit,), fetch=True
        )
        return [dict(r) for r in rows] if rows else []

    def get_hourly_summaries(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get hourly summaries for the last N days"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = self._db_execute(
            """SELECT * FROM hourly_summaries 
               WHERE date >= ? ORDER BY date, hour""",
            (cutoff,), fetch=True
        )
        return [dict(r) for r in rows] if rows else []

    def get_user_session_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get past user sessions"""
        rows = self._db_execute(
            """SELECT * FROM user_sessions 
               ORDER BY start_time DESC LIMIT ?""",
            (limit,), fetch=True
        )
        return [dict(r) for r in rows] if rows else []

    def get_activity_timeline(
        self, hours: int = 24, resolution_minutes: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Get an activity timeline for visualization.
        Returns bucketed activity data.
        """
        cutoff = (
            datetime.now() - timedelta(hours=hours)
        ).isoformat()

        rows = self._db_execute(
            """SELECT timestamp, activity_level, keyboard_intensity,
                      mouse_intensity, process_name, category
               FROM activity_snapshots
               WHERE timestamp >= ?
               ORDER BY timestamp""",
            (cutoff,), fetch=True
        )

        if not rows:
            return []

        # Bucket by time interval
        buckets = defaultdict(lambda: {
            "activity_levels": [],
            "kb_intensities": [],
            "mouse_intensities": [],
            "apps": defaultdict(int),
            "categories": defaultdict(int)
        })

        for row in rows:
            ts = datetime.fromisoformat(row["timestamp"])
            bucket_key = ts.replace(
                minute=(ts.minute // resolution_minutes) * resolution_minutes,
                second=0, microsecond=0
            ).isoformat()

            bucket = buckets[bucket_key]
            level_map = {"idle": 0, "low": 0.25, "moderate": 0.5, "active": 0.75, "intense": 1.0}
            bucket["activity_levels"].append(
                level_map.get(row["activity_level"], 0)
            )
            bucket["kb_intensities"].append(row["keyboard_intensity"] or 0)
            bucket["mouse_intensities"].append(row["mouse_intensity"] or 0)
            if row["process_name"]:
                bucket["apps"][row["process_name"]] += 1
            if row["category"]:
                bucket["categories"][row["category"]] += 1

        # Compute averages per bucket
        timeline = []
        for bucket_time, data in sorted(buckets.items()):
            n = len(data["activity_levels"])
            top_app = max(data["apps"], key=data["apps"].get) if data["apps"] else ""
            top_cat = max(data["categories"], key=data["categories"].get) if data["categories"] else ""

            timeline.append({
                "timestamp": bucket_time,
                "avg_activity": sum(data["activity_levels"]) / n,
                "avg_keyboard": sum(data["kb_intensities"]) / n,
                "avg_mouse": sum(data["mouse_intensities"]) / n,
                "top_app": top_app,
                "top_category": top_cat,
                "samples": n
            })

        return timeline

    def get_stats(self) -> Dict[str, Any]:
        """Get tracker statistics with enhanced metadata"""
        return {
            "running": self._running,
            "total_snapshots": self._total_snapshots,
            "total_window_switches": self._window_switch_count,
            "total_sessions": self._session_count,
            "current_activity_level": self._current_activity_level.value,
            "current_window": (
                self._current_window.process_name if self._current_window else "none"
            ),
            "apps_tracked_today": len(self._app_time_today),
            "categories_tracked_today": len(self._category_time_today),
            "top_app_today": (
                max(self._app_time_today, key=self._app_time_today.get)
                if self._app_time_today else "none"
            ),
            "top_category_today": (
                max(self._category_time_today, key=self._category_time_today.get)
                if self._category_time_today else "none"
            ),
            "recent_snapshots_count": len(self._recent_snapshots),
            "hourly_summaries_count": len(self._hourly_summaries),
            "idle_seconds": self._idle_detector.get_idle_seconds(),
            # ── Enhanced stats ──
            "clipboard_content_type": self._last_clipboard_type,
            "monitor_count": self._monitor_count,
            "active_monitor_index": self._active_monitor_index,
            "browser_tab_count": self._browser_tab_count,
            "open_window_count": self._open_window_count,
            "virtual_desktop_id": self._virtual_desktop_id,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

user_tracker = UserTracker()

if __name__ == "__main__":
    tracker = UserTracker()
    tracker.start()

    print("Tracking user behavior... Press Ctrl+C to stop")
    try:
        while True:
            time.sleep(10)
            snapshot = tracker.get_current_snapshot()
            print(f"\n─── Snapshot ───")
            print(json.dumps(snapshot, indent=2, default=str))
            print(f"\nApp usage today: {tracker.get_app_usage_today()}")
    except KeyboardInterrupt:
        tracker.stop()
        print("\nStopped.")