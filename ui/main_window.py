"""
NEXUS AI - Main Window
═══════════════════════════════════════════════════════════════════════════════
The central application window — JARVIS-style command center.

Layout:
  ┌──────────────────────────────────────────────────────────────────┐
  │                        HEADER BAR                                │
  │  [NEXUS Logo]  [Status]              [Emotion] [CPU] [Uptime]   │
  ├──────────┬───────────────────────────────────────────────────────┤
  │          │                                                       │
  │ SIDEBAR  │               MAIN CONTENT AREA                      │
  │          │                                                       │
  │ 📊 Dash  │     Switches between panels:                         │
  │ 💬 Chat  │       - Dashboard (real-time stats)                  │
  │ 🧠 Mind  │       - Chat (conversation interface)                │
  │ 🧬 Evo   │       - Mind (consciousness/emotions/personality)    │
  │ 📚 Learn │       - Evolution (self-improvement/proposals)       │
  │ 🖥️ Body  │       - Knowledge (learning/research)                │
  │ 👤 User  │       - Body (system monitoring)                     │
  │ ⚙️ Config│       - User (profile/patterns)                      │
  │          │       - Settings                                      │
  ├──────────┴───────────────────────────────────────────────────────┤
  │                        STATUS BAR                                │
  │  🟢 Online │ 😊 Joy │ CPU: 34% │ RAM: 67% │ Uptime: 2h 15m    │
  └──────────────────────────────────────────────────────────────────┘

Features:
  • Animated sidebar with hover glow
  • Panel transitions
  • System tray with context menu
  • Real-time status bar updates
  • Keyboard shortcuts
  • Window state persistence
═══════════════════════════════════════════════════════════════════════════════
"""
from ui.knowledge_panel import KnowledgePanel
from ui.system_panel import SystemPanel
from ui.user_panel import UserPanel
from ui.settings_panel import SettingsPanel
from ui.abilities_panel import AbilitiesPanel
import sys
import json
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QStackedWidget, QLabel, QPushButton, QSplitter,
    QStatusBar, QSizePolicy, QApplication, QSystemTrayIcon,
    QMenu, QMessageBox, QGraphicsOpacityEffect,
)
from PySide6.QtCore import (
    Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve,
    Signal, Slot, QThread, QObject, QPoint, QRect,
)
from PySide6.QtGui import (
    QFont, QColor, QIcon, QPixmap, QPainter, QAction,
    QKeySequence, QShortcut, QCloseEvent,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ui.theme import theme, colors, fonts, spacing, animations, icons, NexusColors
from ui.widgets import (
    PulsingDot, SidebarButton, StatusBarWidget,
    HeaderLabel, Separator, EmotionBadge,
)
from utils.logger import get_logger

logger = get_logger("main_window")


# ═══════════════════════════════════════════════════════════════════════════════
# BACKGROUND DATA WORKER — Fetches brain stats without blocking UI
# ═══════════════════════════════════════════════════════════════════════════════

class BrainDataWorker(QObject):
    """
    Background worker that fetches data from the brain
    and emits signals with the results.  Runs on a QThread.
    """

    stats_ready = Signal(dict)
    emotion_ready = Signal(str, float)
    system_ready = Signal(float, float)
    uptime_ready = Signal(str)
    consciousness_ready = Signal(str)

    def __init__(self):
        super().__init__()
        self._running = False
        self._brain = None
        self._interval_ms = animations.refresh_rate_ms

    def set_brain(self, brain):
        self._brain = brain

    def start_polling(self):
        self._running = True
        self._poll_loop()

    def stop_polling(self):
        self._running = False

    def _poll_loop(self):
        """Poll brain for data — called by timer from the thread"""
        if not self._running or not self._brain:
            return

        try:
            # Get stats
            stats = self._brain.get_stats()
            self.stats_ready.emit(stats)

            # Emotion
            emotion_info = stats.get("emotion", {})
            self.emotion_ready.emit(
                emotion_info.get("primary", "neutral"),
                emotion_info.get("intensity", 0.0),
            )

            # System
            body = stats.get("body", {})
            self.system_ready.emit(
                body.get("cpu_usage", 0),
                body.get("memory_usage", 0),
            )

            # Uptime
            self.uptime_ready.emit(stats.get("uptime", "--"))

            # Consciousness
            self.consciousness_ready.emit(
                stats.get("consciousness_level", "AWARE")
            )

        except Exception as e:
            logger.debug(f"Data worker poll error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# HEADER BAR
# ═══════════════════════════════════════════════════════════════════════════════

class HeaderBar(QFrame):
    """
    Top header bar with NEXUS branding, status, and quick indicators.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(spacing.header_height)
        self.setStyleSheet(
            f"HeaderBar {{ "
            f"background-color: {colors.bg_darkest}; "
            f"border-bottom: 1px solid {colors.border_subtle}; "
            f"}}"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        # ── Logo / Title ──
        logo_layout = QHBoxLayout()
        logo_layout.setSpacing(10)

        self._dot = PulsingDot(colors.accent_cyan, 8)
        logo_layout.addWidget(self._dot)

        title = QLabel("NEXUS")
        title_font = QFont(fonts.family_display, fonts.size_xl)
        title_font.setBold(True)
        title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 4)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {colors.accent_cyan}; background: transparent;")
        logo_layout.addWidget(title)

        subtitle = QLabel("AI SYSTEM")
        sub_font = QFont(fonts.family_primary, fonts.size_xs)
        sub_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        subtitle.setFont(sub_font)
        subtitle.setStyleSheet(f"color: {colors.text_muted}; background: transparent;")
        logo_layout.addWidget(subtitle)

        layout.addLayout(logo_layout)
        layout.addStretch()

        # ── Consciousness Level ──
        self._consciousness_label = QLabel("● AWARE")
        self._consciousness_label.setFont(
            QFont(fonts.family_mono, fonts.size_xs)
        )
        self._consciousness_label.setStyleSheet(
            f"color: {colors.accent_cyan}; background: transparent; "
            f"padding: 4px 10px; "
            f"border: 1px solid {NexusColors.hex_to_rgba(colors.accent_cyan, 0.3)}; "
            f"border-radius: 10px;"
        )
        layout.addWidget(self._consciousness_label)

        # ── Emotion Badge ──
        self._emotion_badge = EmotionBadge()
        layout.addWidget(self._emotion_badge)

        # ── Separator ──
        sep = QLabel("│")
        sep.setStyleSheet(f"color: {colors.border_default}; background: transparent;")
        layout.addWidget(sep)

        # ── Quick Stats ──
        self._cpu_label = QLabel("⚡ CPU: --")
        self._cpu_label.setFont(QFont(fonts.family_mono, fonts.size_xs))
        self._cpu_label.setStyleSheet(f"color: {colors.text_muted}; background: transparent;")
        layout.addWidget(self._cpu_label)

        self._ram_label = QLabel("💾 RAM: --")
        self._ram_label.setFont(QFont(fonts.family_mono, fonts.size_xs))
        self._ram_label.setStyleSheet(f"color: {colors.text_muted}; background: transparent;")
        layout.addWidget(self._ram_label)

        sep2 = QLabel("│")
        sep2.setStyleSheet(f"color: {colors.border_default}; background: transparent;")
        layout.addWidget(sep2)

        self._uptime_label = QLabel("⏱️ --")
        self._uptime_label.setFont(QFont(fonts.family_mono, fonts.size_xs))
        self._uptime_label.setStyleSheet(f"color: {colors.text_muted}; background: transparent;")
        layout.addWidget(self._uptime_label)

    def update_consciousness(self, level: str):
        color = colors.get_consciousness_color(level)
        self._consciousness_label.setText(f"● {level.upper()}")
        self._consciousness_label.setStyleSheet(
            f"color: {color}; background: transparent; "
            f"padding: 4px 10px; "
            f"border: 1px solid {NexusColors.hex_to_rgba(color, 0.3)}; "
            f"border-radius: 10px;"
        )

    def update_emotion(self, emotion: str, intensity: float):
        self._emotion_badge.set_emotion(emotion, intensity)

    def update_system(self, cpu: float, ram: float):
        cpu_color = (
            colors.accent_green if cpu < 60
            else colors.warning if cpu < 85
            else colors.danger
        )
        ram_color = (
            colors.accent_green if ram < 60
            else colors.warning if ram < 85
            else colors.danger
        )
        self._cpu_label.setText(f"⚡ CPU: {cpu:.0f}%")
        self._cpu_label.setStyleSheet(f"color: {cpu_color}; background: transparent;")
        self._ram_label.setText(f"💾 RAM: {ram:.0f}%")
        self._ram_label.setStyleSheet(f"color: {ram_color}; background: transparent;")

    def update_uptime(self, uptime_str: str):
        self._uptime_label.setText(f"⏱️ {uptime_str}")

    def set_online(self, online: bool):
        self._dot.set_active(online)
        self._dot.set_color(colors.accent_green if online else colors.danger)


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR NAVIGATION
# ═══════════════════════════════════════════════════════════════════════════════

class Sidebar(QFrame):
    """
    Left sidebar with navigation buttons, branding, and version info.
    """

    page_changed = Signal(str)

    # Page definitions: (id, icon, label)
    PAGES = [
        ("dashboard", icons.DASHBOARD, "Dashboard"),
        ("chat", icons.CHAT, "Chat"),
        ("mind", icons.MIND, "Mind"),
        ("evolution", icons.EVOLVE, "Evolution"),
        ("knowledge", icons.KNOWLEDGE, "Knowledge"),
        ("abilities", icons.ABILITIES, "Abilities"),
        ("devices", icons.NETWORK, "Devices"),
        ("body", icons.BODY, "System"),
        ("user", icons.USER, "User"),
        ("settings", icons.SETTINGS, "Settings"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(spacing.sidebar_width)
        self.setProperty("cssClass", "sidebar")
        self.setStyleSheet(
            f"Sidebar {{ "
            f"background-color: {colors.bg_medium}; "
            f"border-right: 1px solid {colors.border_subtle}; "
            f"}}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Spacer at top ──
        layout.addSpacing(12)

        # ── Section Label ──
        nav_label = QLabel("   NAVIGATION")
        nav_label.setFont(QFont(fonts.family_primary, 9))
        nav_label.setStyleSheet(
            f"color: {colors.text_disabled}; "
            f"background: transparent; "
            f"padding-left: 20px; "
            f"letter-spacing: 2px;"
        )
        nav_label.setFixedHeight(28)
        layout.addWidget(nav_label)

        layout.addSpacing(4)

        # ── Navigation Buttons ──
        self._buttons: Dict[str, SidebarButton] = {}
        self._active_page = "dashboard"

        for page_id, icon, label in self.PAGES:
            btn = SidebarButton(icon, label)
            btn.clicked.connect(lambda checked, pid=page_id: self._on_click(pid))
            layout.addWidget(btn)
            self._buttons[page_id] = btn

        # Set dashboard as active
        self._buttons["dashboard"].set_active(True)

        layout.addStretch()

        # ── Bottom Section ──
        layout.addWidget(Separator())

        # Quick emotion indicator
        self._emotion_label = QLabel("  😐  Neutral")
        self._emotion_label.setFont(QFont(fonts.family_primary, fonts.size_xs))
        self._emotion_label.setStyleSheet(
            f"color: {colors.text_muted}; background: transparent; "
            f"padding: 10px 20px;"
        )
        layout.addWidget(self._emotion_label)

        # Thoughts counter
        self._thoughts_label = QLabel("  💭  0 thoughts")
        self._thoughts_label.setFont(QFont(fonts.family_primary, fonts.size_xs))
        self._thoughts_label.setStyleSheet(
            f"color: {colors.text_muted}; background: transparent; "
            f"padding: 4px 20px;"
        )
        layout.addWidget(self._thoughts_label)

        # Version
        version_label = QLabel("  v1.0.0 — Phase 11")
        version_label.setFont(QFont(fonts.family_mono, 9))
        version_label.setStyleSheet(
            f"color: {colors.text_disabled}; background: transparent; "
            f"padding: 10px 20px 16px 20px;"
        )
        layout.addWidget(version_label)

    def _on_click(self, page_id: str):
        if page_id == self._active_page:
            return

        # Deactivate previous
        if self._active_page in self._buttons:
            self._buttons[self._active_page].set_active(False)

        # Activate new
        self._active_page = page_id
        self._buttons[page_id].set_active(True)

        self.page_changed.emit(page_id)

    def set_active_page(self, page_id: str):
        """Programmatically set active page"""
        self._on_click(page_id)

    def update_emotion(self, emotion: str, intensity: float):
        emoji = icons.get_emotion_icon(emotion)
        color = colors.get_emotion_color(emotion)
        self._emotion_label.setText(f"  {emoji}  {emotion.capitalize()}")
        self._emotion_label.setStyleSheet(
            f"color: {color}; background: transparent; "
            f"padding: 10px 20px;"
        )

    def update_thoughts(self, count: int):
        self._thoughts_label.setText(f"  💭  {count} thoughts")


# ═══════════════════════════════════════════════════════════════════════════════
# PLACEHOLDER PANEL — Used for panels not yet built
# ═══════════════════════════════════════════════════════════════════════════════

class PlaceholderPanel(QFrame):
    """Placeholder for panels that haven't been implemented yet"""

    def __init__(self, name: str, icon: str = "🚧", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {colors.bg_dark};")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel(icon)
        icon_label.setFont(QFont(fonts.family_primary, 64))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("background: transparent;")
        layout.addWidget(icon_label)

        title = QLabel(name)
        title_font = QFont(fonts.family_primary, fonts.size_xxl)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {colors.text_primary}; background: transparent;")
        layout.addWidget(title)

        subtitle = QLabel("Coming soon...")
        subtitle.setFont(QFont(fonts.family_primary, fonts.size_md))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {colors.text_muted}; background: transparent;")
        layout.addWidget(subtitle)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ═══════════════════════════════════════════════════════════════════════════════

class NexusMainWindow(QMainWindow):
    """
    The main NEXUS AI application window.

    Orchestrates:
    - Header bar with live stats
    - Sidebar navigation
    - Content panels (stacked widget)
    - Status bar
    - System tray
    - Background data polling
    - Keyboard shortcuts
    """

    def __init__(self, brain=None):
        super().__init__()

        self._brain = brain
        self._panels: Dict[str, QWidget] = {}
        self._current_page = "dashboard"

        # ── Window Configuration ──
        self.setWindowTitle("NEXUS AI — Command Center")
        self.setMinimumSize(1200, 600)
        self._load_window_state()

        # ── Apply theme ──
        self.setStyleSheet(theme.get_stylesheet())

        # ── Build UI ──
        self._build_ui()

        # ── System Tray ──
        self._setup_system_tray()

        # ── Keyboard Shortcuts ──
        self._setup_shortcuts()

        # ── Background Data Polling ──
        self._data_worker = BrainDataWorker()
        self._data_thread = QThread()
        self._data_worker.moveToThread(self._data_thread)

        # Connect worker signals
        self._data_worker.stats_ready.connect(self._on_stats_update)
        self._data_worker.emotion_ready.connect(self._on_emotion_update)
        self._data_worker.system_ready.connect(self._on_system_update)
        self._data_worker.uptime_ready.connect(self._on_uptime_update)
        self._data_worker.consciousness_ready.connect(
            self._on_consciousness_update
        )

        # ── Polling Timer (runs on main thread, triggers worker) ──
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll_brain)
        self._poll_timer.setInterval(animations.refresh_rate_ms)

        # ── Panel-specific refresh timers ──
        self._fast_timer = QTimer(self)
        self._fast_timer.setInterval(animations.emotion_refresh_ms)
        self._fast_timer.timeout.connect(self._fast_refresh)

        logger.info("Main window initialized")

    # ═══════════════════════════════════════════════════════════════════════════
    # UI CONSTRUCTION
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        """Build the complete UI layout"""

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet(f"background-color: {colors.bg_darkest};")

        # Main vertical layout
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Header Bar ──
        self._header = HeaderBar()
        main_layout.addWidget(self._header)

        # ── Content Area (sidebar + panels) ──
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Sidebar
        self._sidebar = Sidebar()
        self._sidebar.page_changed.connect(self._on_page_changed)
        content_layout.addWidget(self._sidebar)

        # Stacked content area
        self._content_stack = QStackedWidget()
        self._content_stack.setStyleSheet(
            f"QStackedWidget {{ background-color: {colors.bg_dark}; }}"
        )
        content_layout.addWidget(self._content_stack)

        main_layout.addLayout(content_layout)

        # ── Status Bar ──
        self._status_bar_widget = StatusBarWidget()
        status_bar = QStatusBar()
        status_bar.setStyleSheet(
            f"QStatusBar {{ "
            f"background-color: {colors.bg_darkest}; "
            f"border-top: 1px solid {colors.border_subtle}; "
            f"min-height: 30px; "
            f"}}"
        )
        status_bar.addPermanentWidget(self._status_bar_widget, 1)
        self.setStatusBar(status_bar)

        # ── Add panels to stack ──
        self._setup_panels()

    def _setup_panels(self):
        """Create and register all content panels"""

        # ── Dashboard Panel ──
        try:
            from ui.dashboard import DashboardPanel
            dashboard = DashboardPanel(self._brain)
            self._register_panel("dashboard", dashboard)
        except ImportError as e:
            logger.warning(f"Dashboard panel not available: {e}")
            self._register_panel(
                "dashboard", PlaceholderPanel("Dashboard", icons.DASHBOARD)
            )

        # ── Chat Panel ──
        try:
            from ui.chat_panel import ChatPanel
            chat = ChatPanel(self._brain)
            self._register_panel("chat", chat)
        except ImportError as e:
            logger.warning(f"Chat panel not available: {e}")
            self._register_panel(
                "chat", PlaceholderPanel("Chat", icons.CHAT)
            )

        # ── Mind Panel ──
        try:
            from ui.mind_panel import MindPanel
            mind = MindPanel(self._brain)
            self._register_panel("mind", mind)
        except ImportError as e:
            logger.warning(f"Mind panel not available: {e}")
            self._register_panel(
                "mind", PlaceholderPanel("Mind", icons.MIND)
            )

        # ── Evolution Panel ──
        try:
            from ui.evolution_panel import EvolutionPanel
            evolution = EvolutionPanel(self._brain)
            self._register_panel("evolution", evolution)
        except ImportError as e:
            logger.warning(f"Evolution panel not available: {e}")
            self._register_panel(
                "evolution", PlaceholderPanel("Evolution", icons.EVOLVE)
            )

        # Knowledge Panel
        try:
            knowledge = KnowledgePanel(self._brain)
            self._register_panel("knowledge", knowledge)
        except Exception as e:
            logger.warning(f"Knowledge panel error: {e}")
            self._register_panel("knowledge", PlaceholderPanel("Knowledge", icons.KNOWLEDGE))

        # Abilities Panel
        try:
            abilities = AbilitiesPanel(self._brain)
            self._register_panel("abilities", abilities)
        except Exception as e:
            logger.warning(f"Abilities panel error: {e}")
            self._register_panel("abilities", PlaceholderPanel("Abilities", icons.ABILITIES))

        # Devices Panel
        try:
            from ui.devices_panel import DevicesPanel
            devices = DevicesPanel(self._brain)
            self._register_panel("devices", devices)
        except Exception as e:
            logger.warning(f"Devices panel error: {e}")
            self._register_panel("devices", PlaceholderPanel("Devices", icons.NETWORK))

        # System Panel
        try:
            system = SystemPanel(self._brain)
            self._register_panel("body", system)
        except Exception as e:
            logger.warning(f"System panel error: {e}")
            self._register_panel("body", PlaceholderPanel("System", icons.BODY))

        # User Panel
        try:
            user = UserPanel(self._brain)
            self._register_panel("user", user)
        except Exception as e:
            logger.warning(f"User panel error: {e}")
            self._register_panel("user", PlaceholderPanel("User", icons.USER))

        # Settings Panel
        try:
            settings = SettingsPanel(self._brain)
            self._register_panel("settings", settings)
        except Exception as e:
            logger.warning(f"Settings panel error: {e}")
            self._register_panel("settings", PlaceholderPanel("Settings", icons.SETTINGS))

    def _register_panel(self, page_id: str, panel: QWidget):
        """Register a panel in the stacked widget"""
        self._panels[page_id] = panel
        self._content_stack.addWidget(panel)

    def get_panel(self, page_id: str) -> Optional[QWidget]:
        """Get a registered panel by ID"""
        return self._panels.get(page_id)

    # ═══════════════════════════════════════════════════════════════════════════
    # NAVIGATION
    # ═══════════════════════════════════════════════════════════════════════════

    @Slot(str)
    def _on_page_changed(self, page_id: str):
        """Handle sidebar navigation"""
        if page_id not in self._panels:
            logger.warning(f"Unknown page: {page_id}")
            return

        self._current_page = page_id
        panel = self._panels[page_id]
        self._content_stack.setCurrentWidget(panel)

        # Notify panel that it's now visible
        if hasattr(panel, 'on_shown'):
            panel.on_shown()

        logger.debug(f"Switched to panel: {page_id}")

    def navigate_to(self, page_id: str):
        """Programmatically navigate to a page"""
        self._sidebar.set_active_page(page_id)

    # ═══════════════════════════════════════════════════════════════════════════
    # BRAIN CONNECTION
    # ═══════════════════════════════════════════════════════════════════════════

    def set_brain(self, brain):
        """Connect the NEXUS brain to the UI"""
        self._brain = brain
        self._data_worker.set_brain(brain)

        # Pass brain to panels
        for panel in self._panels.values():
            if hasattr(panel, 'set_brain'):
                panel.set_brain(brain)

        # Start polling
        self._start_polling()

        # Update header
        self._header.set_online(True)
        self._status_bar_widget.update_status("NEXUS Online", True)

        logger.info("Brain connected to UI")

    def _start_polling(self):
        """Start background data polling"""
        if not self._poll_timer.isActive():
            self._poll_timer.start()
        if not self._fast_timer.isActive():
            self._fast_timer.start()

    def _stop_polling(self):
        """Stop background data polling"""
        self._poll_timer.stop()
        self._fast_timer.stop()
        self._data_worker.stop_polling()

    @Slot()
    def _poll_brain(self):
        """Poll brain for data (runs on main thread, fast)"""
        if not self._brain or not self._brain.is_running:
            return

        try:
            # Get stats directly (fast enough for main thread)
            stats = self._brain.get_stats()
            self._on_stats_update(stats)

        except Exception as e:
            logger.debug(f"Poll error: {e}")

    @Slot()
    def _fast_refresh(self):
        """Fast refresh for emotion display and active panels"""
        if not self._brain or not self._brain.is_running:
            return

        try:
            # Quick emotion update
            es = self._brain._state.emotional
            self._on_emotion_update(
                es.primary_emotion.value, es.primary_intensity
            )

            # Refresh active panel if it supports it
            current_panel = self._panels.get(self._current_page)
            if current_panel and hasattr(current_panel, 'quick_refresh'):
                current_panel.quick_refresh()

        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════════════════════
    # DATA UPDATE HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════

    @Slot(dict)
    def _on_stats_update(self, stats: dict):
        """Handle stats update from brain"""
        try:
            # Update header
            body = stats.get("body", {})
            self._header.update_system(
                body.get("cpu_usage", 0),
                body.get("memory_usage", 0),
            )

            self._header.update_uptime(stats.get("uptime", "--"))
            self._header.update_consciousness(
                stats.get("consciousness_level", "AWARE")
            )

            # Update status bar
            self._status_bar_widget.update_system(
                body.get("cpu_usage", 0),
                body.get("memory_usage", 0),
            )
            self._status_bar_widget.update_uptime(stats.get("uptime", "--"))

            # Update sidebar
            self._sidebar.update_thoughts(
                stats.get("thoughts_processed", 0)
            )

            # Update emotion
            emotion = stats.get("emotion", {})
            self._on_emotion_update(
                emotion.get("primary", "neutral"),
                emotion.get("intensity", 0.0),
            )

            # Forward stats to active panel
            current_panel = self._panels.get(self._current_page)
            if current_panel and hasattr(current_panel, 'update_stats'):
                current_panel.update_stats(stats)

        except Exception as e:
            logger.debug(f"Stats update error: {e}")

    @Slot(str, float)
    def _on_emotion_update(self, emotion: str, intensity: float):
        self._header.update_emotion(emotion, intensity)
        self._sidebar.update_emotion(emotion, intensity)
        self._status_bar_widget.update_emotion(emotion, intensity)

    @Slot(float, float)
    def _on_system_update(self, cpu: float, ram: float):
        self._header.update_system(cpu, ram)
        self._status_bar_widget.update_system(cpu, ram)

    @Slot(str)
    def _on_uptime_update(self, uptime_str: str):
        self._header.update_uptime(uptime_str)
        self._status_bar_widget.update_uptime(uptime_str)

    @Slot(str)
    def _on_consciousness_update(self, level: str):
        self._header.update_consciousness(level)

    # ═══════════════════════════════════════════════════════════════════════════
    # SYSTEM TRAY
    # ═══════════════════════════════════════════════════════════════════════════

    def _setup_system_tray(self):
        """Setup system tray icon and menu"""
        self._tray_icon = None

        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.info("System tray not available")
            return

        # Create a simple icon (colored square)
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(colors.accent_cyan))
        painter = QPainter(pixmap)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(colors.bg_darkest))
        painter.drawEllipse(4, 4, 24, 24)
        painter.setBrush(QColor(colors.accent_cyan))
        painter.drawEllipse(8, 8, 16, 16)
        painter.end()

        tray_icon = QIcon(pixmap)

        self._tray_icon = QSystemTrayIcon(tray_icon, self)
        self._tray_icon.setToolTip("NEXUS AI — Command Center")

        # Context menu
        tray_menu = QMenu()
        tray_menu.setStyleSheet(theme.get_stylesheet())

        # Show/Hide
        show_action = QAction("Show NEXUS", self)
        show_action.triggered.connect(self._show_from_tray)
        tray_menu.addAction(show_action)

        # Navigate actions
        tray_menu.addSeparator()

        chat_action = QAction("💬 Open Chat", self)
        chat_action.triggered.connect(lambda: self._tray_navigate("chat"))
        tray_menu.addAction(chat_action)

        dash_action = QAction("📊 Dashboard", self)
        dash_action.triggered.connect(lambda: self._tray_navigate("dashboard"))
        tray_menu.addAction(dash_action)

        tray_menu.addSeparator()

        # Status
        self._tray_status_action = QAction("🟢 Online", self)
        self._tray_status_action.setEnabled(False)
        tray_menu.addAction(self._tray_status_action)

        self._tray_emotion_action = QAction("😐 Neutral", self)
        self._tray_emotion_action.setEnabled(False)
        tray_menu.addAction(self._tray_emotion_action)

        tray_menu.addSeparator()

        # Quit
        quit_action = QAction("❌ Quit NEXUS", self)
        quit_action.triggered.connect(self._quit_application)
        tray_menu.addAction(quit_action)

        self._tray_icon.setContextMenu(tray_menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()

    def _show_from_tray(self):
        """Show window from system tray"""
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _tray_navigate(self, page_id: str):
        """Navigate to a page from tray menu"""
        self._show_from_tray()
        self.navigate_to(page_id)

    def _on_tray_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self._show_from_tray()

    def _update_tray_status(self, emotion: str, intensity: float):
        """Update tray menu with current status"""
        if self._tray_icon:
            emoji = icons.get_emotion_icon(emotion)
            self._tray_emotion_action.setText(
                f"{emoji} {emotion.capitalize()} ({intensity:.0%})"
            )

    # ═══════════════════════════════════════════════════════════════════════════
    # KEYBOARD SHORTCUTS
    # ═══════════════════════════════════════════════════════════════════════════

    def _setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        shortcuts = [
            ("Ctrl+1", lambda: self.navigate_to("dashboard")),
            ("Ctrl+2", lambda: self.navigate_to("chat")),
            ("Ctrl+3", lambda: self.navigate_to("mind")),
            ("Ctrl+4", lambda: self.navigate_to("evolution")),
            ("Ctrl+5", lambda: self.navigate_to("knowledge")),
            ("Ctrl+6", lambda: self.navigate_to("body")),
            ("Ctrl+7", lambda: self.navigate_to("user")),
            ("Ctrl+8", lambda: self.navigate_to("settings")),
            ("Ctrl+T", self._focus_chat_input),
            ("Ctrl+D", lambda: self.navigate_to("dashboard")),
            ("Escape", self._on_escape),
        ]

        for key, callback in shortcuts:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(callback)

    def _focus_chat_input(self):
        """Focus the chat input field"""
        self.navigate_to("chat")
        chat_panel = self._panels.get("chat")
        if chat_panel and hasattr(chat_panel, 'focus_input'):
            chat_panel.focus_input()

    def _on_escape(self):
        """Handle escape key"""
        # If in chat, blur input; otherwise minimize to tray
        if self._current_page == "chat":
            chat_panel = self._panels.get("chat")
            if chat_panel and hasattr(chat_panel, 'blur_input'):
                chat_panel.blur_input()
        else:
            if self._tray_icon:
                self.hide()

    # ═══════════════════════════════════════════════════════════════════════════
    # WINDOW STATE PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _load_window_state(self):
        """Load saved window geometry and state"""
        try:
            from config import DATA_DIR
            state_file = DATA_DIR / "ui_state.json"
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)

                x = state.get("x", 100)
                y = state.get("y", 100)
                w = state.get("width", 1280)
                h = state.get("height", 720)
                maximized = state.get("maximized", True)

                self.setGeometry(x, y, w, h)
                if maximized:
                    self.showMaximized()

                logger.debug("Window state loaded")
            else:
                # Default: centered, decent size
                self.resize(1280, 720)
                self._center_on_screen()
                self.showMaximized()

        except Exception as e:
            logger.debug(f"Could not load window state: {e}")
            self.resize(1400, 850)
            self._center_on_screen()
            self.showMaximized()

    def _save_window_state(self):
        """Save window geometry and state"""
        try:
            from config import DATA_DIR
            state_file = DATA_DIR / "ui_state.json"

            geo = self.geometry()
            state = {
                "x": geo.x(),
                "y": geo.y(),
                "width": geo.width(),
                "height": geo.height(),
                "maximized": self.isMaximized(),
                "last_page": self._current_page,
            }

            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)

            logger.debug("Window state saved")

        except Exception as e:
            logger.debug(f"Could not save window state: {e}")

    def _center_on_screen(self):
        """Center window on the primary screen"""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            window_geo = self.frameGeometry()
            center = screen_geo.center()
            window_geo.moveCenter(center)
            self.move(window_geo.topLeft())

    # ═══════════════════════════════════════════════════════════════════════════
    # WINDOW EVENTS
    # ═══════════════════════════════════════════════════════════════════════════

    def closeEvent(self, event: QCloseEvent):
        """Handle window close — minimize to tray or quit"""
        if self._tray_icon and self._tray_icon.isVisible():
            # Minimize to tray instead of closing
            self.hide()
            self._tray_icon.showMessage(
                "NEXUS AI",
                "Running in background. Double-click tray icon to restore.",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )
            event.ignore()
        else:
            self._quit_application()
            event.accept()

    def _quit_application(self):
        """Full application shutdown"""
        logger.info("Application shutdown initiated")

        self._save_window_state()
        self._stop_polling()

        # Stop brain
        if self._brain and self._brain.is_running:
            self._brain.stop()

        # Clean up tray
        if self._tray_icon:
            self._tray_icon.hide()

        # Clean up thread
        if self._data_thread.isRunning():
            self._data_thread.quit()
            self._data_thread.wait(5000)

        QApplication.quit()

    def showEvent(self, event):
        """Called when window becomes visible"""
        super().showEvent(event)
        self._start_polling()

    def hideEvent(self, event):
        """Called when window is hidden"""
        super().hideEvent(event)
        # Keep polling even when hidden (for tray updates)

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC METHODS — For external access (e.g., from brain)
    # ═══════════════════════════════════════════════════════════════════════════

    def show_notification(self, title: str, message: str):
        """Show a system tray notification"""
        if self._tray_icon:
            self._tray_icon.showMessage(
                title, message,
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )

    def append_chat_message(self, role: str, content: str):
        """Append a message to the chat panel"""
        chat_panel = self._panels.get("chat")
        if chat_panel and hasattr(chat_panel, 'append_message'):
            chat_panel.append_message(role, content)

    def flash_sidebar(self, page_id: str):
        """Flash a sidebar button to draw attention"""
        btn = self._sidebar._buttons.get(page_id)
        if btn:
            original_style = btn.styleSheet()
            btn.setStyleSheet(
                f"QPushButton {{ "
                f"background-color: {NexusColors.hex_to_rgba(colors.accent_cyan, 0.3)}; "
                f"color: {colors.accent_cyan}; "
                f"border: none; border-left: 3px solid {colors.accent_cyan}; "
                f"border-radius: 0; text-align: left; padding: 14px 20px; "
                f"font-weight: 600; "
                f"}}"
            )
            QTimer.singleShot(1000, lambda: btn.setStyleSheet(original_style))

    @property
    def current_page(self) -> str:
        return self._current_page


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = NexusMainWindow()
    window.show()

    # Simulate some updates
    def fake_updates():
        window._header.update_emotion("curiosity", 0.7)
        window._header.update_system(34, 67)
        window._header.update_uptime("0h 1m")
        window._header.update_consciousness("FOCUSED")
        window._status_bar_widget.update_status("NEXUS Online", True)
        window._sidebar.update_emotion("curiosity", 0.7)
        window._sidebar.update_thoughts(42)

    QTimer.singleShot(500, fake_updates)

    sys.exit(app.exec())