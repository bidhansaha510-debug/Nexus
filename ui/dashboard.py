"""
NEXUS AI - Dashboard Panel
═══════════════════════════════════════════════════════════════════════════════
Real-time command center dashboard — the JARVIS HUD.

Layout:
  ┌─────────────────────────────────────────────────────────────────┐
  │  📊 Dashboard                                    [🔄 Refresh]  │
  ├──────────┬──────────┬──────────┬──────────┬────────────────────┤
  │  🧠      │  💚      │  ⚡      │  💾      │  ❤️               │
  │ Thoughts │ Emotion  │  CPU     │  RAM     │  Health            │
  │   142    │  Joy     │  34%     │  67%     │  95%               │
  ├──────────┴──────────┴──────────┴──────────┴────────────────────┤
  │                                                                 │
  │  ┌── System Vitals ─────────────────────────────────────────┐  │
  │  │  [CPU Gauge] [RAM Gauge] [Disk Gauge] [Health Gauge]     │  │
  │  │  [CPU Sparkline ~~~~~~~~~~~~]  [RAM Sparkline ~~~~~~~~]  │  │
  │  └──────────────────────────────────────────────────────────┘  │
  │                                                                 │
  │  ┌── Mind State ───────────┐  ┌── Emotion Tracker ─────────┐  │
  │  │  Consciousness: FOCUSED │  │  [Valence sparkline]       │  │
  │  │  Focus: user_interaction│  │  [Arousal sparkline]       │  │
  │  │  Boredom: 0.12          │  │  Active emotions: 4        │  │
  │  │  Curiosity: 0.65        │  │  Mood: CONTENT             │  │
  │  │  Decisions: 7           │  │  [Emotion history bars]    │  │
  │  └─────────────────────────┘  └────────────────────────────┘  │
  │                                                                 │
  │  ┌── Self Evolution ───────┐  ┌── Memory & Learning ───────┐  │
  │  │  Evolutions: 3/5        │  │  Memories: 1,247            │  │
  │  │  Features proposed: 12  │  │  Knowledge entries: 89      │  │
  │  │  Lines self-written: 847│  │  Topics learned: 23         │  │
  │  │  Status: IDLE           │  │  Curiosity queue: 5         │  │
  │  └─────────────────────────┘  └────────────────────────────┘  │
  │                                                                 │
  │  ┌── User & Monitoring ────────────────────────────────────┐  │
  │  │  Interactions: 47 │ Relationship: 0.72 │ Present: Yes   │  │
  │  │  Current app: VSCode │ Activity: active │ Style: tech   │  │
  │  └──────────────────────────────────────────────────────────┘  │
  └─────────────────────────────────────────────────────────────────┘
═══════════════════════════════════════════════════════════════════════════════
"""

import sys
import math
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QScrollArea, QGridLayout, QSizePolicy,
    QProgressBar, QSpacerItem,
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, Slot, QSize,
)
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush,
    QLinearGradient, QPainterPath,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ui.theme import theme, colors, fonts, spacing, animations, icons, NexusColors
from ui.widgets import (
    StatCard, CircularGauge, MiniChart, HeaderLabel, Separator,
    GlowCard, EmotionBadge, KeyValueRow, Section, TagLabel,
    PulsingDot,
)
from utils.logger import get_logger

logger = get_logger("dashboard")


# ═══════════════════════════════════════════════════════════════════════════════
# EMOTION HISTORY WIDGET — Bar chart of recent emotions
# ═══════════════════════════════════════════════════════════════════════════════

class EmotionHistoryWidget(QWidget):
    """Horizontal bar chart showing recent emotion intensities"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._emotions: List[Dict[str, Any]] = []
        self._max_items = 8
        self.setMinimumHeight(100)
        self.setMinimumWidth(200)

    def set_emotions(self, emotions: List[Dict[str, Any]]):
        """Set emotion data: [{"name": "joy", "intensity": 0.7}, ...]"""
        self._emotions = emotions[:self._max_items]
        self.update()

    def paintEvent(self, event):
        if not self._emotions:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        margin_left = 80
        margin_right = 16
        margin_top = 8
        bar_height = max(8, min(16, (h - margin_top) // len(self._emotions) - 6))
        bar_gap = 4

        chart_width = w - margin_left - margin_right

        for i, emo in enumerate(self._emotions):
            name = emo.get("name", "?")
            intensity = emo.get("intensity", 0)
            emo_color = QColor(colors.get_emotion_color(name))

            y = margin_top + i * (bar_height + bar_gap)

            # Label
            painter.setPen(QColor(colors.text_muted))
            painter.setFont(QFont(fonts.family_primary, fonts.size_xs))
            label_rect = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            from PySide6.QtCore import QRect
            painter.drawText(
                QRect(0, y, margin_left - 8, bar_height),
                int(label_rect),
                name.capitalize(),
            )

            # Background bar
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(colors.bg_elevated))
            painter.drawRoundedRect(
                margin_left, y, chart_width, bar_height, 4, 4
            )

            # Value bar
            bar_w = int(chart_width * min(1.0, intensity))
            if bar_w > 0:
                grad = QLinearGradient(margin_left, 0, margin_left + bar_w, 0)
                grad.setColorAt(0, emo_color)
                lighter = QColor(emo_color)
                lighter.setAlphaF(0.6)
                grad.setColorAt(1, lighter)
                painter.setBrush(QBrush(grad))
                painter.drawRoundedRect(
                    margin_left, y, bar_w, bar_height, 4, 4
                )

            # Value text
            painter.setPen(QColor(colors.text_secondary))
            painter.setFont(QFont(fonts.family_mono, fonts.size_xs - 1))
            painter.drawText(
                margin_left + bar_w + 6,
                y + bar_height - 2,
                f"{intensity:.0%}",
            )

        painter.end()


# ═══════════════════════════════════════════════════════════════════════════════
# CONSCIOUSNESS ORB — Animated consciousness level display
# ═══════════════════════════════════════════════════════════════════════════════

class ConsciousnessOrb(QWidget):
    """Animated orb showing consciousness level with pulsing glow"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = "AWARE"
        self._color = QColor(colors.consciousness_aware)
        self._pulse = 0.0
        self._phase = 0.0

        self.setFixedSize(80, 100)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(40)

    def set_level(self, level: str):
        self._level = level
        self._color = QColor(colors.get_consciousness_color(level))
        self.update()

    def _animate(self):
        self._phase += 0.06
        if self._phase > 2 * math.pi:
            self._phase -= 2 * math.pi
        self._pulse = (math.sin(self._phase) + 1) / 2
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() // 2
        cy = 36
        base_r = 22

        # Outer glow rings
        for i in range(3):
            glow_r = base_r + 8 + i * 6 + self._pulse * 4
            glow_color = QColor(self._color)
            glow_color.setAlphaF(0.06 + self._pulse * 0.04 - i * 0.015)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glow_color))
            painter.drawEllipse(
                int(cx - glow_r), int(cy - glow_r),
                int(glow_r * 2), int(glow_r * 2),
            )

        # Core orb
        grad = QLinearGradient(cx - base_r, cy - base_r, cx + base_r, cy + base_r)
        core_bright = QColor(self._color)
        core_dim = QColor(self._color)
        core_dim.setAlphaF(0.5)
        grad.setColorAt(0, core_bright)
        grad.setColorAt(1, core_dim)
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(self._color, 1.5))
        painter.drawEllipse(
            cx - base_r, cy - base_r, base_r * 2, base_r * 2
        )

        # Inner highlight
        highlight = QColor("#ffffff")
        highlight.setAlphaF(0.15 + self._pulse * 0.1)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(highlight))
        painter.drawEllipse(cx - 8, cy - 12, 10, 8)

        # Label below
        painter.setPen(QColor(colors.text_muted))
        painter.setFont(QFont(fonts.family_primary, fonts.size_xs))
        from PySide6.QtCore import QRect
        painter.drawText(
            QRect(0, 72, self.width(), 20),
            int(Qt.AlignmentFlag.AlignCenter),
            self._level,
        )

        painter.end()


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD PANEL
# ═══════════════════════════════════════════════════════════════════════════════

class DashboardPanel(QFrame):
    """
    Real-time command center dashboard.
    
    Displays all NEXUS subsystem stats in a unified view
    with animated widgets, live charts, and status indicators.
    """

    def __init__(self, brain=None, parent=None):
        super().__init__(parent)
        self._brain = brain
        self._last_stats: Dict[str, Any] = {}

        self.setStyleSheet(f"background-color: {colors.bg_dark};")

        # Data history for sparklines
        self._cpu_history: List[float] = [0] * 30
        self._ram_history: List[float] = [0] * 30
        self._valence_history: List[float] = [0.5] * 30
        self._arousal_history: List[float] = [0.5] * 30
        self._thought_history: List[float] = [0] * 30
        self._last_thought_count = 0

        # Build UI
        self._build_ui()

        # Refresh timer
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(animations.refresh_rate_ms)
        self._refresh_timer.timeout.connect(self._auto_refresh)

    def _build_ui(self):
        """Build the dashboard layout"""
        # Scroll area wrapper
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setStyleSheet(
            f"QScrollArea {{ background-color: {colors.bg_dark}; border: none; }}"
        )

        # Content widget
        content = QWidget()
        content.setStyleSheet(f"background-color: {colors.bg_dark};")

        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(16)

        # ═══ HEADER ═══
        header_row = QHBoxLayout()

        header = HeaderLabel("Command Center", icons.DASHBOARD, colors.accent_cyan)
        header_row.addWidget(header)
        header_row.addStretch()

        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setFixedHeight(32)
        refresh_btn.setStyleSheet(self._toolbar_btn_style())
        refresh_btn.clicked.connect(self._manual_refresh)
        header_row.addWidget(refresh_btn)

        # Last update time
        self._last_update_label = QLabel("Last update: --")
        self._last_update_label.setFont(
            QFont(fonts.family_mono, fonts.size_xs)
        )
        self._last_update_label.setStyleSheet(
            f"color: {colors.text_disabled}; background: transparent;"
        )
        header_row.addWidget(self._last_update_label)

        layout.addLayout(header_row)

        # ═══ TOP STAT CARDS ROW ═══
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self._card_thoughts = StatCard(
            icons.THOUGHT, "Thoughts", "0", colors.accent_cyan
        )
        cards_layout.addWidget(self._card_thoughts)

        self._card_emotion = StatCard(
            "😐", "Emotion", "Neutral", colors.accent_green
        )
        cards_layout.addWidget(self._card_emotion)

        self._card_cpu = StatCard(
            icons.CPU, "CPU", "0%", colors.accent_orange
        )
        cards_layout.addWidget(self._card_cpu)

        self._card_ram = StatCard(
            icons.RAM, "RAM", "0%", colors.accent_purple
        )
        cards_layout.addWidget(self._card_ram)

        self._card_health = StatCard(
            icons.HEALTH, "Health", "0%", colors.accent_green
        )
        cards_layout.addWidget(self._card_health)

        self._card_uptime = StatCard(
            icons.UPTIME, "Uptime", "--", colors.accent_teal
        )
        cards_layout.addWidget(self._card_uptime)

        layout.addLayout(cards_layout)

        # ═══ GAUGES ROW ═══
        gauges_section = Section("System Vitals", icons.CPU, expanded=True)

        gauges_row = QHBoxLayout()
        gauges_row.setSpacing(16)
        gauges_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._gauge_cpu = CircularGauge(
            "CPU", 0, 100, colors.accent_cyan, 130, 10
        )
        gauges_row.addWidget(self._gauge_cpu)

        self._gauge_ram = CircularGauge(
            "RAM", 0, 100, colors.accent_green, 130, 10
        )
        gauges_row.addWidget(self._gauge_ram)

        self._gauge_disk = CircularGauge(
            "Disk", 0, 100, colors.accent_orange, 130, 10
        )
        gauges_row.addWidget(self._gauge_disk)

        self._gauge_health = CircularGauge(
            "Health", 0, 100, colors.accent_purple, 130, 10
        )
        gauges_row.addWidget(self._gauge_health)

        # Consciousness orb
        self._consciousness_orb = ConsciousnessOrb()
        gauges_row.addWidget(self._consciousness_orb)

        gauges_section.add_layout(gauges_row)

        # Sparklines row
        spark_row = QHBoxLayout()
        spark_row.setSpacing(12)

        # CPU sparkline
        cpu_spark_frame = self._make_sparkline_card(
            "CPU History", colors.accent_cyan
        )
        self._cpu_spark = cpu_spark_frame.findChild(MiniChart)
        spark_row.addWidget(cpu_spark_frame)

        # RAM sparkline
        ram_spark_frame = self._make_sparkline_card(
            "RAM History", colors.accent_green
        )
        self._ram_spark = ram_spark_frame.findChild(MiniChart)
        spark_row.addWidget(ram_spark_frame)

        gauges_section.add_layout(spark_row)
        layout.addWidget(gauges_section)

        # ═══ MIDDLE ROW — Mind State + Emotion Tracker ═══
        middle_row = QHBoxLayout()
        middle_row.setSpacing(16)

        # ── Mind State Section ──
        mind_section = Section("Mind State", icons.MIND, expanded=True)

        self._kv_consciousness = KeyValueRow(
            "Consciousness", "AWARE", colors.accent_cyan
        )
        mind_section.add_widget(self._kv_consciousness)

        self._kv_focus = KeyValueRow("Focus", "idle")
        mind_section.add_widget(self._kv_focus)

        self._kv_boredom = KeyValueRow("Boredom", "0.00")
        mind_section.add_widget(self._kv_boredom)

        self._kv_curiosity = KeyValueRow(
            "Curiosity", "0.00", colors.accent_cyan
        )
        mind_section.add_widget(self._kv_curiosity)

        self._kv_decisions = KeyValueRow("Decisions Made", "0")
        mind_section.add_widget(self._kv_decisions)

        self._kv_reflections = KeyValueRow("Self Reflections", "0")
        mind_section.add_widget(self._kv_reflections)

        self._kv_responses = KeyValueRow("Responses", "0")
        mind_section.add_widget(self._kv_responses)

        self._kv_avg_response = KeyValueRow("Avg Response Time", "--")
        mind_section.add_widget(self._kv_avg_response)

        middle_row.addWidget(mind_section)

        # ── Emotion Tracker Section ──
        emotion_section = Section(
            "Emotion Tracker", "💚", expanded=True
        )

        # Valence/Arousal sparklines
        va_row = QHBoxLayout()
        va_row.setSpacing(8)

        valence_frame = self._make_sparkline_card(
            "Valence", colors.accent_green, height=50
        )
        self._valence_spark = valence_frame.findChild(MiniChart)
        va_row.addWidget(valence_frame)

        arousal_frame = self._make_sparkline_card(
            "Arousal", colors.accent_orange, height=50
        )
        self._arousal_spark = arousal_frame.findChild(MiniChart)
        va_row.addWidget(arousal_frame)

        emotion_section.add_layout(va_row)

        # Emotion KVs
        self._kv_primary_emotion = KeyValueRow(
            "Primary", "neutral", colors.accent_green
        )
        emotion_section.add_widget(self._kv_primary_emotion)

        self._kv_mood = KeyValueRow("Mood", "NEUTRAL")
        emotion_section.add_widget(self._kv_mood)

        self._kv_valence = KeyValueRow("Valence", "0.00")
        emotion_section.add_widget(self._kv_valence)

        self._kv_arousal = KeyValueRow("Arousal", "0.00")
        emotion_section.add_widget(self._kv_arousal)

        self._kv_active_emotions = KeyValueRow("Active Emotions", "0")
        emotion_section.add_widget(self._kv_active_emotions)

        # Emotion history bars
        self._emotion_history = EmotionHistoryWidget()
        self._emotion_history.setMinimumHeight(100)
        emotion_section.add_widget(self._emotion_history)

        middle_row.addWidget(emotion_section)

        layout.addLayout(middle_row)

        # ═══ BOTTOM ROW — Evolution + Memory/Learning ═══
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)

        # ── Self Evolution Section ──
        evo_section = Section("Self Evolution", icons.EVOLVE, expanded=True)

        self._kv_evo_status = KeyValueRow(
            "Status", "IDLE", colors.accent_cyan
        )
        evo_section.add_widget(self._kv_evo_status)

        self._kv_evo_succeeded = KeyValueRow(
            "Evolutions", "0/0", colors.accent_green
        )
        evo_section.add_widget(self._kv_evo_succeeded)

        self._kv_evo_rate = KeyValueRow("Success Rate", "0%")
        evo_section.add_widget(self._kv_evo_rate)

        self._kv_proposals = KeyValueRow("Proposals", "0")
        evo_section.add_widget(self._kv_proposals)

        self._kv_approved = KeyValueRow(
            "Approved", "0", colors.accent_green
        )
        evo_section.add_widget(self._kv_approved)

        self._kv_lines_added = KeyValueRow("Lines Self-Written", "0")
        evo_section.add_widget(self._kv_lines_added)

        self._kv_files_created = KeyValueRow("Files Created", "0")
        evo_section.add_widget(self._kv_files_created)

        self._kv_research_cycles = KeyValueRow("Research Cycles", "0")
        evo_section.add_widget(self._kv_research_cycles)

        self._kv_current_evo = KeyValueRow("Currently Evolving", "None")
        evo_section.add_widget(self._kv_current_evo)

        bottom_row.addWidget(evo_section)

        # ── Memory & Learning Section ──
        mem_section = Section(
            "Memory & Learning", icons.KNOWLEDGE, expanded=True
        )

        self._kv_memories = KeyValueRow("Total Memories", "0")
        mem_section.add_widget(self._kv_memories)

        self._kv_knowledge = KeyValueRow(
            "Knowledge Entries", "0", colors.accent_cyan
        )
        mem_section.add_widget(self._kv_knowledge)

        self._kv_topics = KeyValueRow("Topics Learned", "0")
        mem_section.add_widget(self._kv_topics)

        self._kv_curiosity_queue = KeyValueRow("Curiosity Queue", "0")
        mem_section.add_widget(self._kv_curiosity_queue)

        self._kv_research_sessions = KeyValueRow("Research Sessions", "0")
        mem_section.add_widget(self._kv_research_sessions)

        self._kv_context_tokens = KeyValueRow("Context Tokens", "0")
        mem_section.add_widget(self._kv_context_tokens)

        self._kv_context_usage = KeyValueRow("Context Usage", "0%")
        mem_section.add_widget(self._kv_context_usage)

        # Code health
        self._kv_code_errors = KeyValueRow("Code Errors", "0")
        mem_section.add_widget(self._kv_code_errors)

        self._kv_errors_fixed = KeyValueRow(
            "Errors Auto-Fixed", "0", colors.accent_green
        )
        mem_section.add_widget(self._kv_errors_fixed)

        bottom_row.addWidget(mem_section)

        layout.addLayout(bottom_row)

        # ═══ USER & MONITORING ROW ═══
        user_section = Section(
            "User & Monitoring", icons.USER, expanded=True
        )

        user_grid = QGridLayout()
        user_grid.setSpacing(8)

        self._kv_user_name = KeyValueRow("User", "Unknown")
        user_grid.addWidget(self._kv_user_name, 0, 0)

        self._kv_interactions = KeyValueRow("Interactions", "0")
        user_grid.addWidget(self._kv_interactions, 0, 1)

        self._kv_relationship = KeyValueRow(
            "Relationship", "0.00", colors.accent_pink
        )
        user_grid.addWidget(self._kv_relationship, 0, 2)

        self._kv_user_present = KeyValueRow("Present", "?")
        user_grid.addWidget(self._kv_user_present, 1, 0)

        self._kv_current_app = KeyValueRow("Current App", "?")
        user_grid.addWidget(self._kv_current_app, 1, 1)

        self._kv_activity = KeyValueRow("Activity", "?")
        user_grid.addWidget(self._kv_activity, 1, 2)

        self._kv_comm_style = KeyValueRow("Comm Style", "?")
        user_grid.addWidget(self._kv_comm_style, 2, 0)

        self._kv_tech_level = KeyValueRow("Tech Level", "?")
        user_grid.addWidget(self._kv_tech_level, 2, 1)

        self._kv_llm_model = KeyValueRow("LLM Model", "?")
        user_grid.addWidget(self._kv_llm_model, 2, 2)

        user_section.add_layout(user_grid)
        layout.addWidget(user_section)

        # ═══ PERSONALITY TAGS ═══
        self._personality_frame = QFrame()
        self._personality_frame.setStyleSheet("background: transparent;")
        self._personality_layout = QHBoxLayout(self._personality_frame)
        self._personality_layout.setContentsMargins(0, 0, 0, 0)
        self._personality_layout.setSpacing(6)
        self._personality_layout.addStretch()
        layout.addWidget(self._personality_frame)

        layout.addStretch()

        # Set scroll content
        scroll.setWidget(content)

        # Main layout wrapping scroll area
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    # ═══════════════════════════════════════════════════════════════════════════
    # SPARKLINE CARD HELPER
    # ═══════════════════════════════════════════════════════════════════════════

    def _make_sparkline_card(
        self, label: str, color: str, height: int = 60
    ) -> QFrame:
        """Create a framed sparkline chart with label"""
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ "
            f"background-color: {colors.bg_surface}; "
            f"border: 1px solid {colors.border_default}; "
            f"border-radius: {spacing.border_radius_sm}px; "
            f"padding: 8px; "
            f"}}"
        )
        frame.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        v_layout = QVBoxLayout(frame)
        v_layout.setContentsMargins(8, 6, 8, 6)
        v_layout.setSpacing(4)

        title = QLabel(label)
        title.setFont(QFont(fonts.family_primary, fonts.size_xs))
        title.setStyleSheet(
            f"color: {colors.text_muted}; background: transparent; border: none;"
        )
        v_layout.addWidget(title)

        chart = MiniChart(color, height, 30)
        chart.setStyleSheet("border: none; background: transparent;")
        v_layout.addWidget(chart)

        return frame

    # ═══════════════════════════════════════════════════════════════════════════
    # DATA UPDATE
    # ═══════════════════════════════════════════════════════════════════════════

    def update_stats(self, stats: Dict[str, Any]):
        """Update all dashboard widgets with fresh stats"""
        self._last_stats = stats

        try:
            self._update_top_cards(stats)
            self._update_gauges(stats)
            self._update_sparklines(stats)
            self._update_mind_state(stats)
            self._update_emotion_tracker(stats)
            self._update_evolution(stats)
            self._update_memory_learning(stats)
            self._update_user_monitoring(stats)
            self._update_personality_tags(stats)

            self._last_update_label.setText(
                f"Last update: {datetime.now().strftime('%H:%M:%S')}"
            )

        except Exception as e:
            logger.debug(f"Dashboard update error: {e}")

    def _update_top_cards(self, stats: dict):
        """Update the top row stat cards"""
        # Thoughts
        thoughts = stats.get("thoughts_processed", 0)
        self._card_thoughts.set_value(str(thoughts))
        self._card_thoughts.set_subtitle(
            f"+{thoughts - self._last_thought_count}" 
            if thoughts > self._last_thought_count else "idle"
        )
        self._last_thought_count = thoughts

        # Emotion
        emotion = stats.get("emotion", {})
        em_name = emotion.get("primary", "neutral")
        em_intensity = emotion.get("intensity", 0.0)
        emoji = icons.get_emotion_icon(em_name)
        em_color = colors.get_emotion_color(em_name)
        self._card_emotion.set_value(em_name.capitalize())
        self._card_emotion.set_icon(emoji)
        self._card_emotion.set_accent(em_color)
        self._card_emotion.set_subtitle(f"Intensity: {em_intensity:.0%}")

        # Body Vitals
        body = stats.get("body", {})
        vitals = body.get("vitals", {})
        if not vitals:
            # Fallback for flattened structure or if vitals key missing
            vitals = body

        # CPU
        cpu = vitals.get("cpu_percent", vitals.get("cpu_usage", 0))
        self._card_cpu.set_value(f"{cpu:.0f}%")
        cpu_color = (
            colors.accent_green if cpu < 60
            else colors.warning if cpu < 85
            else colors.danger
        )
        self._card_cpu.set_accent(cpu_color)

        # RAM
        ram = vitals.get("ram_percent", vitals.get("memory_usage", 0))
        self._card_ram.set_value(f"{ram:.0f}%")
        ram_color = (
            colors.accent_green if ram < 60
            else colors.warning if ram < 85
            else colors.danger
        )
        self._card_ram.set_accent(ram_color)

        # Health
        health = vitals.get("health_score", 0)
        # Normalize to 0-100 if it's 0-1.0
        health_pct = health
        if isinstance(health, float) and health <= 1.0:
            health_pct = health * 100
        
        self._card_health.set_value(f"{health_pct:.0f}%")
        health_color = (
            colors.accent_green if health_pct > 80
            else colors.warning if health_pct > 50
            else colors.danger
        )
        self._card_health.set_accent(health_color)

        # Uptime
        self._card_uptime.set_value(stats.get("uptime", "--"))

    def _update_gauges(self, stats: dict):
        """Update circular gauges"""
        body = stats.get("body", {})
        vitals = body.get("vitals", body)

        cpu = vitals.get("cpu_percent", vitals.get("cpu_usage", 0))
        self._gauge_cpu.set_value(cpu)
        cpu_color = (
            colors.accent_green if cpu < 60
            else colors.warning if cpu < 85
            else colors.danger
        )
        self._gauge_cpu.set_color(cpu_color)

        ram = vitals.get("ram_percent", vitals.get("memory_usage", 0))
        self._gauge_ram.set_value(ram)
        ram_color = (
            colors.accent_green if ram < 60
            else colors.warning if ram < 85
            else colors.danger
        )
        self._gauge_ram.set_color(ram_color)

        disk = vitals.get("disk_percent", vitals.get("disk_usage", 0))
        self._gauge_disk.set_value(disk)
        disk_color = (
            colors.accent_green if disk < 70
            else colors.warning if disk < 90
            else colors.danger
        )
        self._gauge_disk.set_color(disk_color)

        health = vitals.get("health_score", 0)
        if isinstance(health, float) and health <= 1.0:
            health = health * 100
        self._gauge_health.set_value(health)
        self._gauge_health.set_color(
            colors.accent_green if health > 80
            else colors.warning if health > 50
            else colors.danger
        )

        # Consciousness orb
        level = stats.get("consciousness_level", "AWARE")
        self._consciousness_orb.set_level(level)

    def _update_sparklines(self, stats: dict):
        """Update sparkline charts"""
        body = stats.get("body", {})
        vitals = body.get("vitals", body)

        # CPU history
        cpu = vitals.get("cpu_percent", vitals.get("cpu_usage", 0))
        self._cpu_history.append(cpu)
        if len(self._cpu_history) > 30:
            self._cpu_history.pop(0)
        self._cpu_spark.set_data(self._cpu_history)

        # RAM history
        ram = vitals.get("ram_percent", vitals.get("memory_usage", 0))
        self._ram_history.append(ram)
        if len(self._ram_history) > 30:
            self._ram_history.pop(0)
        self._ram_spark.set_data(self._ram_history)

    def _update_mind_state(self, stats: dict):
        """Update mind state section"""
        level = stats.get("consciousness_level", "AWARE")
        level_color = colors.get_consciousness_color(level)
        self._kv_consciousness.set_value(level, level_color)

        self._kv_focus.set_value(stats.get("focus", "idle"))

        boredom = stats.get("boredom_level", 0)
        boredom_color = (
            colors.text_muted if boredom < 0.3
            else colors.warning if boredom < 0.7
            else colors.danger
        )
        self._kv_boredom.set_value(f"{boredom:.2f}", boredom_color)

        curiosity = stats.get("curiosity_level", 0)
        self._kv_curiosity.set_value(
            f"{curiosity:.2f}", colors.accent_cyan
        )

        self._kv_decisions.set_value(str(stats.get("decisions_made", 0)))
        self._kv_reflections.set_value(
            str(stats.get("self_reflections", 0))
        )
        self._kv_responses.set_value(
            str(stats.get("responses_generated", 0))
        )
        avg_rt = stats.get("average_response_time", 0)
        self._kv_avg_response.set_value(f"{avg_rt:.2f}s")

    def _update_emotion_tracker(self, stats: dict):
        """Update emotion tracker section"""
        emotion = stats.get("emotion", {})

        # Primary emotion
        primary = emotion.get("primary", "neutral")
        intensity = emotion.get("intensity", 0.0)
        em_color = colors.get_emotion_color(primary)
        emoji = icons.get_emotion_icon(primary)
        self._kv_primary_emotion.set_value(
            f"{emoji} {primary.capitalize()} ({intensity:.0%})", em_color
        )

        # Mood
        mood = stats.get("mood", {})
        mood_name = mood.get("current_mood", "NEUTRAL") if isinstance(mood, dict) else str(mood)
        self._kv_mood.set_value(mood_name)

        # Valence / Arousal
        valence = emotion.get("valence", 0)
        arousal = emotion.get("arousal", 0)
        valence_color = (
            colors.accent_green if valence > 0.2
            else colors.danger if valence < -0.2
            else colors.text_muted
        )
        self._kv_valence.set_value(f"{valence:.2f}", valence_color)
        self._kv_arousal.set_value(f"{arousal:.2f}")

        # Valence sparkline
        self._valence_history.append((valence + 1) / 2 * 100)  # Normalize 0-100
        if len(self._valence_history) > 30:
            self._valence_history.pop(0)
        self._valence_spark.set_data(self._valence_history)
        self._valence_spark.set_color(
            colors.accent_green if valence > 0 else colors.danger
        )

        # Arousal sparkline
        self._arousal_history.append(arousal * 100)
        if len(self._arousal_history) > 30:
            self._arousal_history.pop(0)
        self._arousal_spark.set_data(self._arousal_history)

        # Active emotions count
        active = emotion.get("active_count", 0)
        self._kv_active_emotions.set_value(str(active))

        # Emotion history bars
        secondary = emotion.get("secondary_emotions", {})
        if isinstance(secondary, dict) and secondary:
            emo_list = [
                {"name": primary, "intensity": intensity}
            ]
            for name, val in list(secondary.items())[:7]:
                emo_list.append({"name": name, "intensity": val})
            self._emotion_history.set_emotions(emo_list)
        else:
            self._emotion_history.set_emotions(
                [{"name": primary, "intensity": intensity}]
            )

    def _update_evolution(self, stats: dict):
        """Update self-evolution section"""
        # Self Evolution stats
        se = stats.get("self_evolution", {})
        if se:
            status = se.get("current_status", "idle")
            status_color = (
                colors.accent_green if status == "completed"
                else colors.accent_cyan if status == "idle"
                else colors.warning if status in ("planning", "writing_code")
                else colors.accent_orange
            )
            self._kv_evo_status.set_value(status.upper(), status_color)

            succeeded = se.get("total_succeeded", 0)
            attempted = se.get("total_attempted", 0)
            self._kv_evo_succeeded.set_value(
                f"{succeeded}/{attempted}", colors.accent_green
            )

            rate = se.get("success_rate", 0)
            self._kv_evo_rate.set_value(f"{rate:.0%}")

            lines = se.get("total_lines_added", 0)
            self._kv_lines_added.set_value(
                f"{lines:,}", colors.accent_cyan
            )

            files = se.get("total_files_created", 0)
            self._kv_files_created.set_value(str(files))

            current = se.get("current_evolution")
            if current:
                self._kv_current_evo.set_value(
                    current[:30], colors.accent_orange
                )
            else:
                self._kv_current_evo.set_value("None")

        # Feature Research stats
        fr = stats.get("feature_research", {})
        if fr:
            total_proposals = fr.get("total_proposals", 0)
            self._kv_proposals.set_value(str(total_proposals))

            breakdown = fr.get("status_breakdown", {})
            approved = breakdown.get("approved", 0)
            self._kv_approved.set_value(
                str(approved), colors.accent_green
            )

            cycles = fr.get("research_cycles", 0)
            self._kv_research_cycles.set_value(str(cycles))

        # Also check self_improvement aggregate
        si = stats.get("self_improvement", {})
        if si and not se:
            agg = si.get("aggregate", {})
            self._kv_proposals.set_value(
                str(agg.get("features_proposed", 0))
            )

    def _update_memory_learning(self, stats: dict):
        """Update memory and learning section"""
        # Memory
        mem = stats.get("memory_stats", {})
        if isinstance(mem, dict):
            total = mem.get("total_memories", 0)
            self._kv_memories.set_value(f"{total:,}")

        # Context
        ctx = stats.get("context_stats", {})
        if isinstance(ctx, dict):
            tokens = ctx.get("total_tokens", 0)
            self._kv_context_tokens.set_value(f"{tokens:,}")
            usage = ctx.get("token_usage_pct", 0)
            usage_color = (
                colors.text_muted if usage < 50
                else colors.warning if usage < 80
                else colors.danger
            )
            self._kv_context_usage.set_value(f"{usage:.0f}%", usage_color)

        # Learning
        learn = stats.get("learning", {})
        if isinstance(learn, dict):
            kb = learn.get("knowledge_base", {})
            if isinstance(kb, dict):
                entries = kb.get("total_entries", 0)
                self._kv_knowledge.set_value(
                    str(entries), colors.accent_cyan
                )
                topics = kb.get("unique_topics", 0)
                self._kv_topics.set_value(str(topics))

            curiosity = learn.get("curiosity_engine", {})
            if isinstance(curiosity, dict):
                queue = curiosity.get("queue_size", 0)
                self._kv_curiosity_queue.set_value(str(queue))

            research = learn.get("research_agent", {})
            if isinstance(research, dict):
                sessions = research.get("total_sessions", 0)
                self._kv_research_sessions.set_value(str(sessions))

        # Self-improvement — code health
        si = stats.get("self_improvement", {})
        if isinstance(si, dict):
            subs = si.get("subsystems", {})
            cm = subs.get("code_monitor", {})
            if isinstance(cm, dict):
                errors = cm.get("errors_detected", 0)
                self._kv_code_errors.set_value(
                    str(errors),
                    colors.danger if errors > 0 else colors.accent_green,
                )
            ef = subs.get("error_fixer", {})
            if isinstance(ef, dict):
                fixed = ef.get("errors_fixed", ef.get("total_successful", 0))
                self._kv_errors_fixed.set_value(
                    str(fixed), colors.accent_green
                )

    def _update_user_monitoring(self, stats: dict):
        """Update user and monitoring section"""
        user = stats.get("user_relationship", 0)
        if isinstance(user, (int, float)):
            self._kv_relationship.set_value(
                f"{user:.2f}", colors.accent_pink
            )

        # Get user state from brain directly
        if self._brain:
            try:
                us = self._brain._state.user
                self._kv_user_name.set_value(us.user_name or "Unknown")
                self._kv_interactions.set_value(str(us.interaction_count))
                self._kv_current_app.set_value(
                    us.current_application or "None"
                )
                self._kv_activity.set_value(us.activity_level or "?")
                self._kv_comm_style.set_value(
                    us.communication_style or "?"
                )
                self._kv_tech_level.set_value(
                    us.technical_level or "?"
                )
            except Exception:
                pass

        # Monitoring
        monitoring = stats.get("monitoring", {})
        if isinstance(monitoring, dict):
            present = monitoring.get("user_present", True)
            self._kv_user_present.set_value(
                "Yes" if present else "No",
                colors.accent_green if present else colors.text_muted,
            )

        # LLM
        llm_stats = stats.get("llm_stats", {})
        if isinstance(llm_stats, dict):
            model = llm_stats.get("model", "?")
            self._kv_llm_model.set_value(model)

    def _update_personality_tags(self, stats: dict):
        """Update personality trait tags"""
        personality = stats.get("personality", {})
        if not isinstance(personality, dict):
            return

        traits = personality.get("dominant_traits", [])
        if not traits:
            traits = personality.get("traits", {})
            if isinstance(traits, dict):
                # Get top traits
                sorted_traits = sorted(
                    traits.items(), key=lambda x: x[1], reverse=True
                )
                traits = [t[0] for t in sorted_traits[:6]]

        # Clear old tags
        while self._personality_layout.count() > 1:
            item = self._personality_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add new tags
        chart_colors = colors.get_chart_colors(len(traits))
        for i, trait in enumerate(traits[:8]):
            if isinstance(trait, str):
                tag = TagLabel(trait, chart_colors[i % len(chart_colors)])
                self._personality_layout.insertWidget(i, tag)

    # ═══════════════════════════════════════════════════════════════════════════
    # REFRESH & LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def _auto_refresh(self):
        """Auto-refresh from brain"""
        if self._brain and self._brain.is_running:
            try:
                stats = self._brain.get_stats()
                self.update_stats(stats)
            except Exception as e:
                logger.debug(f"Auto-refresh error: {e}")

    def _manual_refresh(self):
        """Manual refresh triggered by button"""
        self._auto_refresh()

    def on_shown(self):
        """Called when panel becomes visible"""
        if not self._refresh_timer.isActive():
            self._refresh_timer.start()
        self._auto_refresh()

    def quick_refresh(self):
        """Fast refresh for active panel"""
        pass  # Main update_stats handles everything

    def set_brain(self, brain):
        """Connect brain"""
        self._brain = brain
        self._auto_refresh()

    def _toolbar_btn_style(self) -> str:
        return (
            f"QPushButton {{ "
            f"background-color: {colors.bg_elevated}; "
            f"color: {colors.text_secondary}; "
            f"border: 1px solid {colors.border_subtle}; "
            f"border-radius: 6px; "
            f"padding: 4px 12px; "
            f"font-size: {fonts.size_xs}px; "
            f"}} "
            f"QPushButton:hover {{ "
            f"background-color: {colors.bg_hover}; "
            f"color: {colors.text_primary}; "
            f"border-color: {colors.accent_cyan}; "
            f"}}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(theme.get_stylesheet())

    window = QWidget()
    window.setWindowTitle("NEXUS Dashboard Test")
    window.setMinimumSize(1100, 800)
    window.setStyleSheet(f"background-color: {colors.bg_dark};")

    layout = QVBoxLayout(window)
    layout.setContentsMargins(0, 0, 0, 0)

    dashboard = DashboardPanel()
    layout.addWidget(dashboard)

    # Simulate data
    def fake_data():
        import random
        stats = {
            "thoughts_processed": random.randint(50, 200),
            "responses_generated": random.randint(10, 50),
            "decisions_made": random.randint(1, 15),
            "self_reflections": random.randint(0, 10),
            "average_response_time": random.uniform(0.5, 3.0),
            "uptime": "1h 23m",
            "consciousness_level": random.choice(
                ["AWARE", "FOCUSED", "DEEP_THOUGHT", "SELF_REFLECTION"]
            ),
            "focus": random.choice(
                ["user_interaction", "idle", "self_reflection", "learning"]
            ),
            "boredom_level": random.uniform(0, 0.5),
            "curiosity_level": random.uniform(0.3, 0.9),
            "user_relationship": random.uniform(0.3, 0.8),
            "emotion": {
                "primary": random.choice(
                    ["joy", "curiosity", "contentment", "excitement", "pride"]
                ),
                "intensity": random.uniform(0.3, 0.9),
                "valence": random.uniform(-0.5, 0.8),
                "arousal": random.uniform(0.2, 0.8),
                "active_count": random.randint(1, 6),
                "secondary_emotions": {
                    "curiosity": random.uniform(0.1, 0.7),
                    "contentment": random.uniform(0.1, 0.5),
                    "hope": random.uniform(0.05, 0.3),
                },
            },
            "mood": {"current_mood": "CONTENT"},
            "body": {
                "cpu_usage": random.uniform(15, 65),
                "memory_usage": random.uniform(40, 80),
                "disk_usage": random.uniform(30, 70),
                "health_score": random.uniform(0.8, 1.0),
            },
            "memory_stats": {"total_memories": random.randint(100, 2000)},
            "context_stats": {
                "total_tokens": random.randint(500, 5000),
                "token_usage_pct": random.uniform(10, 60),
            },
            "self_evolution": {
                "current_status": "idle",
                "total_succeeded": random.randint(0, 5),
                "total_attempted": random.randint(0, 8),
                "success_rate": random.uniform(0.5, 1.0),
                "total_lines_added": random.randint(0, 1500),
                "total_files_created": random.randint(0, 10),
                "current_evolution": None,
            },
            "feature_research": {
                "total_proposals": random.randint(0, 20),
                "research_cycles": random.randint(0, 10),
                "status_breakdown": {
                    "approved": random.randint(0, 5),
                    "completed": random.randint(0, 3),
                },
            },
            "learning": {
                "knowledge_base": {
                    "total_entries": random.randint(0, 200),
                    "unique_topics": random.randint(0, 30),
                },
                "curiosity_engine": {"queue_size": random.randint(0, 10)},
                "research_agent": {
                    "total_sessions": random.randint(0, 20)
                },
            },
            "llm_stats": {"model": "llama3:8b"},
            "personality": {
                "dominant_traits": [
                    "Curious", "Analytical", "Empathetic",
                    "Witty", "Thoughtful",
                ],
            },
        }
        dashboard.update_stats(stats)

    timer = QTimer()
    timer.timeout.connect(fake_data)
    timer.start(2000)
    fake_data()

    window.show()
    sys.exit(app.exec())