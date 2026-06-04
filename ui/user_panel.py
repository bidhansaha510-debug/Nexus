"""
NEXUS AI - User Profile Panel (Advanced)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Rich user profile dashboard showing learned behaviors, personality,
session analytics, app usage patterns, and relationship dynamics.

Layout:
  ┌─────────────────────────────────────────────────────────────────┐
  │  👤 User Profile                                                │
  │  ──────────────────────────────────────────────────── pink      │
  │                                                                  │
  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
  │  │Relation  │ │Interact  │ │ Sessions │ │ Active   │           │
  │  │ Gauge    │ │  Count   │ │  Count   │ │  Hours   │           │
  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
  │                                                                  │
  │  ▼ 🎭 Current Activity                                          │
  │  ┌──────────────────────────────────────────────────────────┐   │
  │  │  [●  Present]  App: code.exe  │  Category: Development  │   │
  │  │  Idle: 12s  │  Mood: Happy   │  Activity: Normal        │   │
  │  └──────────────────────────────────────────────────────────┘   │
  │                                                                  │
  │  ▼ 🧬 Personality Traits                                        │
  │  ┌──────────────────────────────────────────────────────────┐   │
  │  │  [Radar/Bar chart of personality traits]                 │   │
  │  └──────────────────────────────────────────────────────────┘   │
  │                                                                  │
  │  ▼ 📊 Learned Profile                                           │
  │  ▼ 📱 App Usage                                                 │
  │  ▼ 🕐 Active Hours Heatmap                                     │
  │  ▼ 📈 Session Analytics                                         │
  │  ▼ 🔧 Preferences & Patterns                                   │
  └─────────────────────────────────────────────────────────────────┘
"""
import sys
import math
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QProgressBar, QGridLayout, QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush,
    QPainterPath
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ui.theme import theme, colors, fonts, spacing, icons
from ui.widgets import (
    HeaderLabel, StatCard, Section, KeyValueRow, TagLabel,
    CircularGauge, MiniChart, PulsingDot, GlowCard,
)
from utils.logger import get_logger

logger = get_logger("user_panel")


# ═══════════════════════════════════════════════════════════════════════════════
# PERSONALITY RADAR CHART
# ═══════════════════════════════════════════════════════════════════════════════

class PersonalityRadar(QWidget):
    """
    Animated radar/spider chart for visualizing personality traits.
    Draws a polygon shape for each trait's value on radial axes.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._traits: Dict[str, float] = {}
        self._phase = 0.0
        self.setMinimumHeight(200)
        self.setMinimumWidth(200)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(80)

    def set_traits(self, traits: Dict[str, float]):
        """traits = {'openness': 0.8, 'conscientiousness': 0.6, ...}"""
        self._traits = traits
        self.update()

    def _animate(self):
        self._phase += 0.015
        self.update()

    def paintEvent(self, event):
        if not self._traits:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        radius = min(w, h) * 0.38

        labels = list(self._traits.keys())
        values = list(self._traits.values())
        n = len(labels)
        if n < 3:
            painter.end()
            return

        angle_step = (2 * math.pi) / n

        # Draw grid rings (3 levels)
        for ring in [0.33, 0.66, 1.0]:
            pen = QPen(QColor(colors.border_subtle))
            pen.setWidthF(0.5)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            r = radius * ring
            # Draw polygon ring
            ring_path = QPainterPath()
            for i in range(n):
                angle = -math.pi / 2 + i * angle_step
                x = cx + r * math.cos(angle)
                y = cy + r * math.sin(angle)
                if i == 0:
                    ring_path.moveTo(x, y)
                else:
                    ring_path.lineTo(x, y)
            ring_path.closeSubpath()
            painter.drawPath(ring_path)

        # Draw axis lines
        pen = QPen(QColor(colors.border_subtle))
        pen.setWidthF(0.5)
        painter.setPen(pen)
        for i in range(n):
            angle = -math.pi / 2 + i * angle_step
            x2 = cx + radius * math.cos(angle)
            y2 = cy + radius * math.sin(angle)
            painter.drawLine(int(cx), int(cy), int(x2), int(y2))

        # Draw filled polygon for trait values
        value_path = QPainterPath()
        points = []
        for i in range(n):
            val = min(max(values[i], 0), 1.0)
            angle = -math.pi / 2 + i * angle_step
            r = radius * val
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            points.append((x, y))
            if i == 0:
                value_path.moveTo(x, y)
            else:
                value_path.lineTo(x, y)
        value_path.closeSubpath()

        # Fill with translucent accent
        fill_color = QColor(colors.accent_pink)
        fill_color.setAlpha(40)
        painter.setBrush(QBrush(fill_color))
        border_color = QColor(colors.accent_pink)
        border_color.setAlpha(180)
        pen = QPen(border_color)
        pen.setWidthF(2)
        painter.setPen(pen)
        painter.drawPath(value_path)

        # Draw dots at vertices
        for x, y in points:
            glow = QColor(colors.accent_pink)
            glow.setAlpha(60)
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(x) - 5, int(y) - 5, 10, 10)

            dot = QColor(colors.accent_pink)
            dot.setAlpha(220)
            painter.setBrush(QBrush(dot))
            painter.drawEllipse(int(x) - 3, int(y) - 3, 6, 6)

        # Draw labels
        font = QFont(fonts.family_primary, 9)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor(colors.text_secondary))

        for i, label in enumerate(labels):
            angle = -math.pi / 2 + i * angle_step
            lx = cx + (radius + 20) * math.cos(angle)
            ly = cy + (radius + 20) * math.sin(angle)
            # Format label
            display = label.replace("_", " ").title()
            val_pct = int(values[i] * 100)
            text = f"{display} ({val_pct}%)"
            painter.drawText(int(lx) - 50, int(ly) - 8, 100, 16,
                             Qt.AlignmentFlag.AlignCenter, text)

        # Center pulse
        pulse_alpha = int(15 + 10 * math.sin(self._phase * 2))
        center_color = QColor(colors.accent_pink)
        center_color.setAlpha(pulse_alpha)
        painter.setBrush(QBrush(center_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(cx) - 8, int(cy) - 8, 16, 16)

        painter.end()


# ═══════════════════════════════════════════════════════════════════════════════
# HOURS HEATMAP
# ═══════════════════════════════════════════════════════════════════════════════

class HoursHeatmap(QWidget):
    """24-hour heatmap showing typical active hours."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hours: List[int] = []
        self.setFixedHeight(60)
        self.setMinimumWidth(200)

    def set_hours(self, hours: List[int]):
        """hours = list of active hour indices (0-23)."""
        self._hours = hours
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cell_w = w / 24
        label_h = 14

        for hour in range(24):
            x = hour * cell_w
            is_active = hour in self._hours

            # Cell
            if is_active:
                intensity = 0.6 + 0.4 * (self._hours.count(hour) / max(len(self._hours), 1))
                color = QColor(colors.accent_pink)
                color.setAlpha(int(80 + 175 * min(intensity, 1.0)))
            else:
                color = QColor(colors.bg_medium)

            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)

            path = QPainterPath()
            path.addRoundedRect(float(x + 1), 0, float(cell_w - 2), float(h - label_h - 2),
                                3, 3)
            painter.drawPath(path)

            # Hour label
            font = QFont(fonts.family_primary, 7)
            painter.setFont(font)
            painter.setPen(QColor(colors.text_muted))
            if hour % 3 == 0:
                lbl = f"{hour}"
                painter.drawText(int(x), h - label_h, int(cell_w), label_h,
                                 Qt.AlignmentFlag.AlignCenter, lbl)

        painter.end()


# ═══════════════════════════════════════════════════════════════════════════════
# APP USAGE BAR
# ═══════════════════════════════════════════════════════════════════════════════

class AppUsageBar(QWidget):
    """Horizontal bar for a single app with name, category badge, and usage bar."""

    APP_COLORS = [
        "#ec4899", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b",
        "#ef4444", "#6366f1", "#14b8a6", "#84cc16", "#f97316",
    ]

    def __init__(self, rank: int, parent=None):
        super().__init__(parent)
        self._rank = rank
        self._name = ""
        self._color = self.APP_COLORS[rank % len(self.APP_COLORS)]

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)

        self._rank_label = QLabel(f"#{rank + 1}")
        self._rank_label.setFixedWidth(24)
        self._rank_label.setStyleSheet(
            f"color: {colors.text_muted}; font-size: 10px; font-weight: bold;"
        )
        layout.addWidget(self._rank_label)

        self._name_label = QLabel("—")
        self._name_label.setFixedWidth(130)
        self._name_label.setStyleSheet(
            f"color: {colors.text_primary}; font-size: 11px;"
        )
        layout.addWidget(self._name_label)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(8)
        self._bar.setStyleSheet(f"""
            QProgressBar {{ background: {colors.bg_dark}; border: none; border-radius: 4px; }}
            QProgressBar::chunk {{ background: {self._color}; border-radius: 4px; }}
        """)
        layout.addWidget(self._bar)

    def set_app(self, name: str, pct: float):
        self._name = name
        self._name_label.setText(name[:20])
        self._bar.setValue(int(min(pct, 100)))


# ═══════════════════════════════════════════════════════════════════════════════
# MOOD INDICATOR
# ═══════════════════════════════════════════════════════════════════════════════

MOOD_ICONS = {
    "neutral": "😐", "happy": "😊", "sad": "😢", "angry": "😠",
    "excited": "🎉", "anxious": "😰", "focused": "🎯", "tired": "😴",
    "curious": "🤔", "content": "😌", "frustrated": "😤",
}

MOOD_COLORS = {
    "neutral": colors.text_secondary, "happy": "#f7dc6f", "sad": "#45b7d1",
    "angry": "#ff4444", "excited": "#ff8c00", "anxious": "#dda0dd",
    "focused": colors.accent_cyan, "tired": "#888888", "curious": "#bb86fc",
    "content": colors.accent_green, "frustrated": "#ff6b6b",
}


# ═══════════════════════════════════════════════════════════════════════════════
# USER PANEL
# ═══════════════════════════════════════════════════════════════════════════════

class UserPanel(QFrame):
    """
    Advanced User Profile panel with personality radar, relationship gauge,
    session analytics, app usage bars, active hours heatmap, and mood tracking.
    """

    def __init__(self, brain=None, parent=None):
        super().__init__(parent)
        self._brain = brain
        self.setStyleSheet(f"background-color: {colors.bg_dark};")

        self._relationship_history = [0.5] * 30

        self._build_ui()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(2000)

    # ═══════════════════════════════════════════════════════════════════════════
    # UI CONSTRUCTION
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background: {colors.bg_dark}; }}"
            f"QScrollBar:vertical {{ background: {colors.bg_dark}; width: 6px; }}"
            f"QScrollBar::handle:vertical {{ background: {colors.border_default}; "
            f"border-radius: 3px; min-height: 20px; }}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}"
        )

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # ── Header ──
        layout.addWidget(HeaderLabel("User Profile", icons.USER, colors.accent_pink))

        # ── Top Gauges Row ──
        gauges_row = QHBoxLayout()
        gauges_row.setSpacing(8)

        self._gauge_relation = CircularGauge("Relationship", 0, 100, colors.accent_pink, 130, 6)
        self._gauge_relation.set_suffix("%")
        self._gauge_interact = CircularGauge("Interactions", 0, 1000, colors.accent_cyan, 130, 6)
        self._gauge_sessions = CircularGauge("Sessions", 0, 500, colors.accent_purple, 130, 6)
        self._gauge_hours = CircularGauge("Active Hrs", 0, 1000, colors.accent_green, 130, 6)

        gauges_row.addWidget(self._gauge_relation)
        gauges_row.addWidget(self._gauge_interact)
        gauges_row.addWidget(self._gauge_sessions)
        gauges_row.addWidget(self._gauge_hours)
        layout.addLayout(gauges_row)

        # ── Current Activity Section ──
        activity_section = Section("Current Activity", "🎭", expanded=True)
        activity_layout = QVBoxLayout()

        # Presence row
        presence_row = QHBoxLayout()
        self._presence_dot = PulsingDot(colors.accent_green, 14)
        self._lbl_presence = QLabel("User Present")
        self._lbl_presence.setStyleSheet(
            f"color: {colors.accent_green}; font-weight: bold; font-size: 13px;"
        )
        presence_row.addWidget(self._presence_dot)
        presence_row.addWidget(self._lbl_presence)
        presence_row.addStretch()

        # Mood badge
        self._lbl_mood_icon = QLabel("😐")
        self._lbl_mood_icon.setStyleSheet("font-size: 24px;")
        self._lbl_mood_text = QLabel("Neutral")
        self._lbl_mood_text.setStyleSheet(
            f"color: {colors.text_secondary}; font-size: 13px; font-weight: bold;"
        )
        presence_row.addWidget(self._lbl_mood_icon)
        presence_row.addWidget(self._lbl_mood_text)
        activity_layout.addLayout(presence_row)

        # Activity detail grid
        act_grid = QGridLayout()
        act_grid.setSpacing(6)
        self._kv_app = KeyValueRow("Current App", "None")
        self._kv_category = KeyValueRow("Category", "—")
        self._kv_idle = KeyValueRow("Idle Time", "0s")
        self._kv_activity = KeyValueRow("Activity Level", "Normal")
        act_grid.addWidget(self._kv_app, 0, 0)
        act_grid.addWidget(self._kv_category, 0, 1)
        act_grid.addWidget(self._kv_idle, 1, 0)
        act_grid.addWidget(self._kv_activity, 1, 1)
        activity_layout.addLayout(act_grid)

        activity_section.add_layout(activity_layout)
        layout.addWidget(activity_section)

        # ── Personality Traits Section ──
        personality_section = Section("Personality Traits", "🧬", expanded=True)
        personality_layout = QVBoxLayout()

        self._radar = PersonalityRadar()
        self._radar.setMinimumHeight(240)
        personality_layout.addWidget(self._radar)

        # Trait bars below radar
        self._trait_bars_layout = QVBoxLayout()
        self._trait_bars_layout.setSpacing(4)
        self._trait_bar_widgets: Dict[str, QProgressBar] = {}
        personality_layout.addLayout(self._trait_bars_layout)

        personality_section.add_layout(personality_layout)
        layout.addWidget(personality_section)

        # ── Learned Profile Section ──
        profile_section = Section("Learned Profile", icons.USER, expanded=True)
        profile_grid = QGridLayout()
        profile_grid.setSpacing(6)

        self._kv_name = KeyValueRow("Name", "User", colors.accent_pink)
        self._kv_style = KeyValueRow("Comm Style", "Unknown")
        self._kv_tech = KeyValueRow("Tech Level", "Unknown")
        self._kv_work = KeyValueRow("Work Style", "Unknown")
        self._kv_avg_session = KeyValueRow("Avg Session", "—")
        self._kv_last_seen = KeyValueRow("Last Seen", "—")

        profile_grid.addWidget(self._kv_name, 0, 0)
        profile_grid.addWidget(self._kv_style, 0, 1)
        profile_grid.addWidget(self._kv_tech, 1, 0)
        profile_grid.addWidget(self._kv_work, 1, 1)
        profile_grid.addWidget(self._kv_avg_session, 2, 0)
        profile_grid.addWidget(self._kv_last_seen, 2, 1)

        profile_section.add_layout(profile_grid)
        layout.addWidget(profile_section)

        # ── Relationship Trend Section ──
        relation_section = Section("Relationship Trend", "❤️", expanded=True)
        relation_layout = QVBoxLayout()

        chart_row = QHBoxLayout()
        chart_lbl = QLabel("Score Over Time")
        chart_lbl.setStyleSheet(
            f"color: {colors.text_secondary}; font-weight: bold; font-size: 11px;"
        )
        self._relation_chart = MiniChart(colors.accent_pink, 50, 30)
        chart_row.addWidget(chart_lbl)
        chart_row.addWidget(self._relation_chart)
        relation_layout.addLayout(chart_row)

        relation_section.add_layout(relation_layout)
        layout.addWidget(relation_section)

        # ── App Usage Section ──
        apps_section = Section("Top Apps Used", "📱", expanded=False)
        apps_layout = QVBoxLayout()

        self._app_bars: List[AppUsageBar] = []
        for i in range(8):
            bar = AppUsageBar(i)
            self._app_bars.append(bar)
            apps_layout.addWidget(bar)

        # Category tags
        self._categories_label = QLabel("Top Categories:")
        self._categories_label.setStyleSheet(
            f"color: {colors.text_secondary}; font-size: 11px; font-weight: bold; "
            f"margin-top: 8px;"
        )
        apps_layout.addWidget(self._categories_label)
        self._categories_flow = QWidget()
        self._categories_flow_layout = QHBoxLayout(self._categories_flow)
        self._categories_flow_layout.setContentsMargins(0, 0, 0, 0)
        self._categories_flow_layout.setSpacing(6)
        apps_layout.addWidget(self._categories_flow)

        apps_section.add_layout(apps_layout)
        layout.addWidget(apps_section)

        # ── Active Hours Heatmap Section ──
        hours_section = Section("Active Hours", "🕐", expanded=False)
        hours_layout = QVBoxLayout()

        hours_legend = QHBoxLayout()
        for tag, clr in [("Active", colors.accent_pink), ("Inactive", colors.bg_medium)]:
            dot = QLabel(f"■ {tag}")
            dot.setStyleSheet(f"color: {clr}; font-size: 10px;")
            hours_legend.addWidget(dot)
        hours_legend.addStretch()
        hours_layout.addLayout(hours_legend)

        self._heatmap = HoursHeatmap()
        hours_layout.addWidget(self._heatmap)

        hours_section.add_layout(hours_layout)
        layout.addWidget(hours_section)

        # ── Session Analytics Section ──
        session_section = Section("Session Analytics", "📈", expanded=False)
        session_layout = QVBoxLayout()

        session_stats_row = QHBoxLayout()
        session_stats_row.setSpacing(8)
        self._stat_sessions = StatCard("📊", "Total Sessions", "0", colors.accent_purple)
        self._stat_active_time = StatCard("⏱️", "Total Active", "0h", colors.accent_green)
        self._stat_avg_session = StatCard("📏", "Avg Duration", "0m", colors.accent_cyan)
        session_stats_row.addWidget(self._stat_sessions)
        session_stats_row.addWidget(self._stat_active_time)
        session_stats_row.addWidget(self._stat_avg_session)
        session_layout.addLayout(session_stats_row)

        session_section.add_layout(session_layout)
        layout.addWidget(session_section)

        # ── Preferences & Patterns Section ──
        prefs_section = Section("Preferences & Patterns", "🔧", expanded=False)
        self._prefs_layout = QVBoxLayout()
        self._prefs_label = QLabel("No behavioral patterns learned yet.")
        self._prefs_label.setStyleSheet(
            f"color: {colors.text_secondary}; font-size: 12px;"
        )
        self._prefs_label.setWordWrap(True)
        self._prefs_layout.addWidget(self._prefs_label)
        prefs_section.add_layout(self._prefs_layout)
        layout.addWidget(prefs_section)

        layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def set_brain(self, brain):
        self._brain = brain
        self._refresh()

    # ═══════════════════════════════════════════════════════════════════════════
    # DATA REFRESH
    # ═══════════════════════════════════════════════════════════════════════════

    def _refresh(self):
        if not self._brain:
            return

        try:
            us = self._brain._state.user
        except Exception as e:
            logger.debug(f"Cannot access user state: {e}")
            return

        self._refresh_gauges(us)
        self._refresh_activity(us)
        self._refresh_personality(us)
        self._refresh_profile(us)
        self._refresh_relationship(us)
        self._refresh_apps(us)
        self._refresh_hours(us)
        self._refresh_sessions(us)
        self._refresh_preferences(us)

    def _refresh_gauges(self, us):
        """Update top gauges."""
        try:
            # Relationship: 0.0–1.0 → 0–100%
            rel_pct = us.relationship_score * 100
            self._gauge_relation.set_value(min(rel_pct, 100))

            self._gauge_interact.set_value(min(us.interaction_count, 1000))

            self._gauge_sessions.set_value(min(us.session_count, 500))

            hours = us.total_active_time_hours
            self._gauge_hours.set_value(min(hours, 1000))

        except Exception as e:
            logger.debug(f"Gauge refresh error: {e}")

    def _refresh_activity(self, us):
        """Update current activity section."""
        try:
            # Presence
            if us.is_present:
                self._presence_dot.set_color(colors.accent_green)
                self._presence_dot.set_active(True)
                self._lbl_presence.setText("User Present")
                self._lbl_presence.setStyleSheet(
                    f"color: {colors.accent_green}; font-weight: bold; font-size: 13px;"
                )
            else:
                self._presence_dot.set_color("#ff4444")
                self._presence_dot.set_active(False)
                self._lbl_presence.setText("User Away")
                self._lbl_presence.setStyleSheet(
                    f"color: #ff4444; font-weight: bold; font-size: 13px;"
                )

            # Mood
            mood = us.detected_mood.lower()
            mood_icon = MOOD_ICONS.get(mood, "😐")
            mood_color = MOOD_COLORS.get(mood, colors.text_secondary)
            self._lbl_mood_icon.setText(mood_icon)
            self._lbl_mood_text.setText(mood.capitalize())
            self._lbl_mood_text.setStyleSheet(
                f"color: {mood_color}; font-size: 13px; font-weight: bold;"
            )

            # Activity details
            app = us.current_application or "None"
            self._kv_app.set_value(app[:25] if len(app) > 25 else app)
            self._kv_category.set_value(us.current_app_category or "—")

            idle = us.idle_seconds
            if idle < 60:
                idle_str = f"{idle:.0f}s"
            elif idle < 3600:
                idle_str = f"{idle / 60:.0f}m"
            else:
                idle_str = f"{idle / 3600:.1f}h"
            self._kv_idle.set_value(idle_str)

            self._kv_activity.set_value(us.activity_level.capitalize())

        except Exception as e:
            logger.debug(f"Activity refresh error: {e}")

    def _refresh_personality(self, us):
        """Update personality radar chart and trait bars."""
        try:
            traits = us.personality_traits
            if not traits:
                return

            self._radar.set_traits(traits)

            # Update or create trait bars
            TRAIT_COLORS = [
                colors.accent_pink, colors.accent_purple, colors.accent_cyan,
                colors.accent_green, colors.accent_orange, "#f7dc6f",
                "#dda0dd", "#96ceb4", "#45b7d1", "#bb86fc",
            ]

            for i, (trait, value) in enumerate(traits.items()):
                if trait not in self._trait_bar_widgets:
                    # Create new trait bar
                    row = QHBoxLayout()
                    lbl = QLabel(trait.replace("_", " ").title())
                    lbl.setFixedWidth(110)
                    lbl.setStyleSheet(
                        f"color: {colors.text_secondary}; font-size: 11px;"
                    )
                    row.addWidget(lbl)

                    bar = QProgressBar()
                    bar.setRange(0, 100)
                    bar.setTextVisible(False)
                    bar.setFixedHeight(8)
                    color = TRAIT_COLORS[i % len(TRAIT_COLORS)]
                    bar.setStyleSheet(f"""
                        QProgressBar {{ background: {colors.bg_dark}; border: none; border-radius: 4px; }}
                        QProgressBar::chunk {{ background: {color}; border-radius: 4px; }}
                    """)
                    row.addWidget(bar)

                    pct_lbl = QLabel("0%")
                    pct_lbl.setFixedWidth(36)
                    pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    pct_lbl.setStyleSheet(
                        f"color: {color}; font-size: 10px; font-weight: bold;"
                    )
                    row.addWidget(pct_lbl)

                    self._trait_bars_layout.addLayout(row)
                    self._trait_bar_widgets[trait] = (bar, pct_lbl)

                bar, pct_lbl = self._trait_bar_widgets[trait]
                pct = int(value * 100)
                bar.setValue(pct)
                pct_lbl.setText(f"{pct}%")

        except Exception as e:
            logger.debug(f"Personality refresh error: {e}")

    def _refresh_profile(self, us):
        """Update learned profile key-value rows."""
        try:
            self._kv_name.set_value(us.user_name)
            self._kv_style.set_value(us.communication_style.capitalize() if us.communication_style != "unknown" else "Learning...")
            self._kv_tech.set_value(us.technical_level.capitalize() if us.technical_level != "unknown" else "Learning...")
            self._kv_work.set_value(us.work_style.capitalize() if us.work_style != "unknown" else "Learning...")

            if us.avg_session_duration_minutes > 0:
                mins = us.avg_session_duration_minutes
                if mins >= 60:
                    self._kv_avg_session.set_value(f"{mins / 60:.1f}h")
                else:
                    self._kv_avg_session.set_value(f"{mins:.0f}m")
            else:
                self._kv_avg_session.set_value("—")

            if us.last_interaction:
                try:
                    if isinstance(us.last_interaction, datetime):
                        dt = us.last_interaction
                    else:
                        dt = datetime.fromisoformat(str(us.last_interaction))
                    self._kv_last_seen.set_value(dt.strftime("%b %d, %H:%M"))
                except Exception:
                    self._kv_last_seen.set_value("—")

        except Exception as e:
            logger.debug(f"Profile refresh error: {e}")

    def _refresh_relationship(self, us):
        """Update relationship trend sparkline."""
        try:
            score = us.relationship_score
            self._relationship_history.append(score * 100)
            if len(self._relationship_history) > 30:
                self._relationship_history.pop(0)
            self._relation_chart.set_data(self._relationship_history)
        except Exception as e:
            logger.debug(f"Relationship refresh error: {e}")

    def _refresh_apps(self, us):
        """Update app usage bars and category tags."""
        try:
            apps = us.most_used_apps or []
            total = len(apps)

            for i, bar in enumerate(self._app_bars):
                if i < len(apps):
                    app_name = apps[i]
                    # Approximate usage: higher ranked = higher percentage
                    pct = max(10, 100 - (i * (80 / max(total, 1))))
                    bar.set_app(app_name, pct)
                    bar.setVisible(True)
                else:
                    bar.setVisible(False)

            # Categories
            categories = us.most_used_categories or []
            while self._categories_flow_layout.count():
                child = self._categories_flow_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            CAT_COLORS = [
                colors.accent_pink, colors.accent_purple, colors.accent_cyan,
                colors.accent_green, colors.accent_orange, "#45b7d1",
            ]
            for i, cat in enumerate(categories[:6]):
                tag = TagLabel(cat, CAT_COLORS[i % len(CAT_COLORS)])
                self._categories_flow_layout.addWidget(tag)
            self._categories_flow_layout.addStretch()

        except Exception as e:
            logger.debug(f"Apps refresh error: {e}")

    def _refresh_hours(self, us):
        """Update the active hours heatmap."""
        try:
            hours = us.typical_active_hours or []
            self._heatmap.set_hours(hours)
        except Exception as e:
            logger.debug(f"Hours refresh error: {e}")

    def _refresh_sessions(self, us):
        """Update session analytics stat cards."""
        try:
            self._stat_sessions.set_value(str(us.session_count))

            hours = us.total_active_time_hours
            if hours >= 24:
                self._stat_active_time.set_value(f"{hours / 24:.1f}d")
            elif hours >= 1:
                self._stat_active_time.set_value(f"{hours:.1f}h")
            else:
                self._stat_active_time.set_value(f"{hours * 60:.0f}m")

            avg = us.avg_session_duration_minutes
            if avg >= 60:
                self._stat_avg_session.set_value(f"{avg / 60:.1f}h")
            elif avg > 0:
                self._stat_avg_session.set_value(f"{avg:.0f}m")
            else:
                self._stat_avg_session.set_value("—")

        except Exception as e:
            logger.debug(f"Sessions refresh error: {e}")

    def _refresh_preferences(self, us):
        """Update preferences and behavior patterns display."""
        try:
            prefs = us.understood_preferences or {}
            patterns = us.behavior_patterns or {}

            if not prefs and not patterns:
                self._prefs_label.setText("No behavioral patterns learned yet. "
                                          "NEXUS will learn your preferences over time.")
                return

            lines = []
            if prefs:
                lines.append("🔹 <b>Understood Preferences:</b>")
                for key, val in list(prefs.items())[:10]:
                    display_key = key.replace("_", " ").title()
                    lines.append(f"&nbsp;&nbsp;• {display_key}: {val}")

            if patterns:
                lines.append("")
                lines.append("🔹 <b>Behavior Patterns:</b>")
                for key, val in list(patterns.items())[:10]:
                    display_key = key.replace("_", " ").title()
                    if isinstance(val, (list, dict)):
                        val_str = str(val)[:60]
                    elif isinstance(val, float):
                        val_str = f"{val:.2f}"
                    else:
                        val_str = str(val)[:40]
                    lines.append(f"&nbsp;&nbsp;• {display_key}: {val_str}")

            self._prefs_label.setText("<br>".join(lines))

        except Exception as e:
            logger.debug(f"Preferences refresh error: {e}")