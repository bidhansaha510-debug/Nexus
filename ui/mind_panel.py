"""
NEXUS AI - Mind Panel
═══════════════════════════════════════════════════════════════════════════════
Deep visualization of NEXUS's inner mental landscape.

Layout:
  ┌─────────────────────────────────────────────────────────────────┐
  │  🧠 Mind                                                       │
  ├────────────────────────────┬────────────────────────────────────┤
  │                            │                                    │
  │  ┌── Consciousness ─────┐ │  ┌── Emotion Wheel ─────────────┐ │
  │  │  Level: FOCUSED       │ │  │                              │ │
  │  │  [Animated Orb]       │ │  │     [Circular emotion       │ │
  │  │  Focus: interaction   │ │  │      visualization with     │ │
  │  │  Awareness: 0.82      │ │  │      active emotions as    │ │
  │  │  Thoughts: 142        │ │  │      colored arcs]          │ │
  │  └───────────────────────┘ │  │                              │ │
  │                            │  └──────────────────────────────┘ │
  │  ┌── Inner Voice ────────┐ │                                    │
  │  │  "I am curious about  │ │  ┌── Personality Traits ────────┐ │
  │  │   what the user will  │ │  │  Openness     [████████░░] │ │
  │  │   ask me next..."     │ │  │  Empathy      [███████░░░] │ │
  │  │                       │ │  │  Curiosity    [█████████░] │ │
  │  │  Recent thoughts:     │ │  │  Wit          [██████░░░░] │ │
  │  │  • Self reflection    │ │  │  Analytical   [████████░░] │ │
  │  │  • User analysis      │ │  │  Assertive    [█████░░░░░] │ │
  │  └───────────────────────┘ │  └──────────────────────────────┘ │
  │                            │                                    │
  │  ┌── Mood Timeline ──────┐ │  ┌── Will & Desires ────────────┐ │
  │  │  [sparkline chart]    │ │  │  Boredom:   [░░░░░░░░░░] │ │
  │  │  Current: CONTENT     │ │  │  Curiosity: [████████░░] │ │
  │  │  Stability: 0.78      │ │  │  Goals: 3 active          │ │
  │  └───────────────────────┘ │  │  Drive: learning           │ │
  │                            │  └──────────────────────────────┘ │
  └────────────────────────────┴────────────────────────────────────┘
═══════════════════════════════════════════════════════════════════════════════
"""

import sys
import math
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QScrollArea, QGridLayout, QSizePolicy,
    QProgressBar, QTextBrowser, QSplitter, QTabWidget,
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, Slot, QRect, QPoint, QSize,
)
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush,
    QLinearGradient, QConicalGradient, QRadialGradient,
    QPainterPath, QFontMetrics,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ui.theme import theme, colors, fonts, spacing, animations, icons, NexusColors
from ui.widgets import (
    HeaderLabel, Separator, Section, KeyValueRow, TagLabel,
    GlowCard, MiniChart, CircularGauge, PulsingDot, EmotionBadge,
    StatCard,
)
from utils.logger import get_logger

from core.event_bus import subscribe, EventType, Event

logger = get_logger("mind_panel")


# ═══════════════════════════════════════════════════════════════════════════════
# EMOTION WHEEL — Circular visualization of all active emotions
# ═══════════════════════════════════════════════════════════════════════════════

class EmotionWheel(QWidget):
    """
    Circular emotion visualization.
    Each active emotion is shown as a colored arc segment.
    Center displays the primary emotion with pulsing glow.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._emotions: Dict[str, float] = {}
        self._primary: str = "neutral"
        self._primary_intensity: float = 0.0
        self._valence: float = 0.0
        self._arousal: float = 0.0
        self._pulse_phase: float = 0.0

        self.setMinimumSize(250, 250)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(40)

    def set_emotions(self, emotions: Dict[str, float]):
        self._emotions = emotions
        self.update()

    def set_primary(self, emotion: str, intensity: float):
        self._primary = emotion
        self._primary_intensity = intensity
        self.update()

    def set_valence_arousal(self, valence: float, arousal: float):
        self._valence = valence
        self._arousal = arousal
        self.update()

    def _animate(self):
        self._pulse_phase += 0.05
        if self._pulse_phase > 2 * math.pi:
            self._pulse_phase -= 2 * math.pi
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w // 2
        cy = h // 2
        radius = min(cx, cy) - 20
        inner_radius = radius - 30
        core_radius = inner_radius - 15

        pulse = (math.sin(self._pulse_phase) + 1) / 2

        # ── Background ring ──
        painter.setPen(QPen(QColor(colors.bg_elevated), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(
            cx - radius, cy - radius, radius * 2, radius * 2
        )

        # ── Emotion arcs ──
        if self._emotions:
            sorted_emotions = sorted(
                self._emotions.items(), key=lambda x: x[1], reverse=True
            )
            total_intensity = sum(v for _, v in sorted_emotions) or 1.0

            start_angle = 90 * 16  # Start from top
            for name, intensity in sorted_emotions:
                if intensity < 0.01:
                    continue

                # Arc span proportional to intensity
                span = int((intensity / total_intensity) * 360 * 16)
                if span < 5 * 16:
                    span = 5 * 16  # Minimum visible arc

                emo_color = QColor(colors.get_emotion_color(name))
                emo_color_dim = QColor(emo_color)
                emo_color_dim.setAlphaF(0.4 + intensity * 0.4)

                # Draw arc
                pen = QPen(emo_color_dim, 24)
                pen.setCapStyle(Qt.PenCapStyle.FlatCap)
                painter.setPen(pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)

                arc_rect = QRect(
                    cx - radius + 12, cy - radius + 12,
                    (radius - 12) * 2, (radius - 12) * 2,
                )
                painter.drawArc(arc_rect, start_angle, -span)

                # Label on the arc
                mid_angle = (start_angle - span // 2) / 16
                label_r = radius + 4
                lx = cx + label_r * math.cos(math.radians(mid_angle))
                ly = cy - label_r * math.sin(math.radians(mid_angle))

                if len(sorted_emotions) <= 8 and intensity > 0.05:
                    painter.setPen(QColor(colors.text_muted))
                    painter.setFont(
                        QFont(fonts.family_primary, fonts.size_xs - 1)
                    )
                    emoji = icons.get_emotion_icon(name)
                    painter.drawText(
                        int(lx) - 20, int(ly) - 6, 40, 14,
                        int(Qt.AlignmentFlag.AlignCenter),
                        emoji,
                    )

                start_angle -= span

        # ── Inner ring ──
        painter.setPen(QPen(QColor(colors.border_subtle), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(
            cx - inner_radius, cy - inner_radius,
            inner_radius * 2, inner_radius * 2,
        )

        # ── Core glow ──
        primary_color = QColor(colors.get_emotion_color(self._primary))
        glow_r = core_radius + pulse * 8
        glow = QRadialGradient(cx, cy, glow_r)
        glow_c = QColor(primary_color)
        glow_c.setAlphaF(0.2 + pulse * 0.1)
        glow.setColorAt(0, glow_c)
        glow_c2 = QColor(primary_color)
        glow_c2.setAlphaF(0.0)
        glow.setColorAt(1, glow_c2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(glow))
        painter.drawEllipse(
            int(cx - glow_r), int(cy - glow_r),
            int(glow_r * 2), int(glow_r * 2),
        )

        # ── Core circle ──
        core_grad = QRadialGradient(cx, cy, core_radius)
        core_grad.setColorAt(0, QColor(colors.bg_surface))
        core_c = QColor(primary_color)
        core_c.setAlphaF(0.15)
        core_grad.setColorAt(1, core_c)
        painter.setBrush(QBrush(core_grad))
        painter.setPen(QPen(primary_color, 2))
        painter.drawEllipse(
            cx - core_radius, cy - core_radius,
            core_radius * 2, core_radius * 2,
        )

        # ── Primary emotion text in center ──
        emoji = icons.get_emotion_icon(self._primary)
        painter.setPen(QColor(colors.text_primary))
        painter.setFont(QFont(fonts.family_primary, 24))
        painter.drawText(
            QRect(cx - 40, cy - 28, 80, 36),
            int(Qt.AlignmentFlag.AlignCenter),
            emoji,
        )

        painter.setFont(QFont(fonts.family_primary, fonts.size_sm))
        painter.setPen(primary_color)
        painter.drawText(
            QRect(cx - 60, cy + 6, 120, 20),
            int(Qt.AlignmentFlag.AlignCenter),
            self._primary.capitalize(),
        )

        painter.setFont(QFont(fonts.family_mono, fonts.size_xs))
        painter.setPen(QColor(colors.text_muted))
        painter.drawText(
            QRect(cx - 60, cy + 24, 120, 16),
            int(Qt.AlignmentFlag.AlignCenter),
            f"{self._primary_intensity:.0%}",
        )

        # ── Valence/Arousal indicator dot ──
        # Map valence (-1..1) to x, arousal (0..1) to y
        va_r = core_radius - 10
        va_x = cx + self._valence * va_r * 0.8
        va_y = cy - self._arousal * va_r * 0.6
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(colors.accent_cyan)))
        painter.drawEllipse(int(va_x) - 4, int(va_y) - 4, 8, 8)

        painter.end()


# ═══════════════════════════════════════════════════════════════════════════════
# PERSONALITY BARS — Horizontal trait bars
# ═══════════════════════════════════════════════════════════════════════════════

class PersonalityBars(QWidget):
    """Horizontal bar chart for personality traits"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._traits: Dict[str, float] = {}
        self.setMinimumHeight(120)

    def set_traits(self, traits: Dict[str, float]):
        self._traits = traits
        self.update()

    def paintEvent(self, event):
        if not self._traits:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        margin_left = 110
        margin_right = 50
        bar_height = 14
        bar_gap = 8
        chart_width = w - margin_left - margin_right

        chart_colors = colors.get_chart_colors(len(self._traits))
        sorted_traits = sorted(
            self._traits.items(), key=lambda x: x[1], reverse=True
        )

        for i, (name, value) in enumerate(sorted_traits[:10]):
            y = 8 + i * (bar_height + bar_gap)
            color = QColor(chart_colors[i % len(chart_colors)])

            # Label
            painter.setPen(QColor(colors.text_secondary))
            painter.setFont(QFont(fonts.family_primary, fonts.size_xs))
            painter.drawText(
                QRect(0, y, margin_left - 8, bar_height),
                int(
                    Qt.AlignmentFlag.AlignRight
                    | Qt.AlignmentFlag.AlignVCenter
                ),
                name.capitalize(),
            )

            # Background
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(colors.bg_elevated))
            painter.drawRoundedRect(
                margin_left, y, chart_width, bar_height, 4, 4
            )

            # Value bar
            bar_w = int(chart_width * min(1.0, value))
            if bar_w > 0:
                grad = QLinearGradient(margin_left, 0, margin_left + bar_w, 0)
                grad.setColorAt(0, color)
                dimmed = QColor(color)
                dimmed.setAlphaF(0.6)
                grad.setColorAt(1, dimmed)
                painter.setBrush(QBrush(grad))
                painter.drawRoundedRect(
                    margin_left, y, bar_w, bar_height, 4, 4
                )

            # Value text
            painter.setPen(QColor(colors.text_muted))
            painter.setFont(QFont(fonts.family_mono, fonts.size_xs - 1))
            painter.drawText(
                margin_left + chart_width + 8,
                y + bar_height - 2,
                f"{value:.2f}",
            )

        # Update widget height
        needed = 8 + len(sorted_traits[:10]) * (bar_height + bar_gap) + 8
        if self.minimumHeight() < needed:
            self.setMinimumHeight(needed)

        painter.end()


# ═══════════════════════════════════════════════════════════════════════════════
# INNER VOICE DISPLAY — Scrolling inner monologue
# ═══════════════════════════════════════════════════════════════════════════════

class InnerVoiceDisplay(QFrame):
    """Displays the NEXUS inner voice / thought stream"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"InnerVoiceDisplay {{ "
            f"background-color: {colors.bg_surface}; "
            f"border: 1px solid {colors.border_default}; "
            f"border-radius: {spacing.border_radius}px; "
            f"}}"
        )
        self.setMinimumHeight(180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # Header
        header = QHBoxLayout()
        header.setSpacing(6)

        dot = PulsingDot(colors.accent_purple, 6)
        header.addWidget(dot)

        title = QLabel("Inner Voice")
        title.setFont(QFont(fonts.family_primary, fonts.size_sm))
        title.setStyleSheet(
            f"color: {colors.accent_purple}; background: transparent; "
            f"font-weight: bold;"
        )
        header.addWidget(title)
        header.addStretch()

        layout.addLayout(header)

        # Voice content
        self._voice_text = QTextBrowser()
        self._voice_text.setStyleSheet(
            f"QTextBrowser {{ "
            f"background-color: transparent; "
            f"color: {colors.text_secondary}; "
            f"border: none; "
            f"font-family: '{fonts.family_primary}'; "
            f"font-size: {fonts.size_sm}px; "
            f"font-style: italic; "
            f"}}"
        )
        self._voice_text.setOpenExternalLinks(False)
        self._voice_text.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        layout.addWidget(self._voice_text)

        # Recent thoughts
        self._thoughts_label = QLabel("")
        self._thoughts_label.setFont(
            QFont(fonts.family_primary, fonts.size_xs)
        )
        self._thoughts_label.setStyleSheet(
            f"color: {colors.text_disabled}; background: transparent;"
        )
        self._thoughts_label.setWordWrap(True)
        layout.addWidget(self._thoughts_label)

    def set_voice(self, text: str):
        """Set the inner voice text"""
        if text and text != "...":
            styled = (
                f'<div style="color: {colors.text_secondary}; '
                f'font-style: italic; line-height: 1.6;">'
                f'"{text}"</div>'
            )
            self._voice_text.setHtml(styled)

    def set_thoughts(self, thoughts: List[str]):
        """Set recent thought summaries"""
        if thoughts:
            lines = []
            for t in thoughts[-5:]:
                lines.append(f"💭 {t[:80]}")
            self._thoughts_label.setText("\n".join(lines))
        else:
            self._thoughts_label.setText("No recent thoughts.")


# ═══════════════════════════════════════════════════════════════════════════════
# COMPANION CHAT WIDGET
# ═══════════════════════════════════════════════════════════════════════════════

class CompanionChatWidget(QFrame):
    """Displays the companion chat (ARIA) history"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"CompanionChatWidget {{ "
            f"background-color: {colors.bg_surface}; "
            f"border: 1px solid {colors.border_default}; "
            f"border-radius: {spacing.border_radius}px; "
            f"}}"
        )
        self.setMinimumHeight(180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # Header
        header = QHBoxLayout()
        header.setSpacing(6)
        
        # Indicator dot
        self._dot = PulsingDot(colors.accent_pink, 6)
        header.addWidget(self._dot)

        title = QLabel("Companion: ARIA")
        title.setFont(QFont(fonts.family_primary, fonts.size_sm))
        title.setStyleSheet(
            f"color: {colors.accent_pink}; background: transparent; "
            f"font-weight: bold;"
        )
        header.addWidget(title)
        
        header.addStretch()
        
        # Status label
        self._status_label = QLabel("Idle")
        self._status_label.setFont(QFont(fonts.family_primary, fonts.size_xs))
        self._status_label.setStyleSheet(f"color: {colors.text_muted}; background: transparent;")
        header.addWidget(self._status_label)
        
        layout.addLayout(header)

        # Chat content
        self._chat_text = QTextBrowser()
        self._chat_text.setStyleSheet(
            f"QTextBrowser {{ "
            f"background-color: transparent; "
            f"color: {colors.text_primary}; "
            f"border: none; "
            f"font-family: '{fonts.family_primary}'; "
            f"font-size: {fonts.size_sm}px; "
            f"line-height: 1.4; "
            f"}}"
        )
        self._chat_text.setOpenExternalLinks(False)
        self._chat_text.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        layout.addWidget(self._chat_text)

    def add_message(self, speaker: str, content: str, timestamp: str):
        """Add a message to the chat display"""
        
        # Format timestamp
        ts = ""
        try:
            dt = datetime.fromisoformat(timestamp)
            ts = dt.strftime("%H:%M")
        except:
            pass
            
        color = colors.accent_pink if speaker == "ARIA" else colors.accent_cyan
        align = "left" if speaker == "ARIA" else "right"
        bg_color = f"{color}15" # approx 10% opacity hex if 8-digit hex supported, else fallback
        # actually using rgba in style style attribute is safer
        
        # Simple HTML formatting
        if speaker == "ARIA":
            html = (
                f'<div style="margin-bottom: 8px;">'
                f'<span style="color: {colors.text_disabled}; font-size: x-small;">[{ts}]</span> '
                f'<b style="color: {colors.accent_pink};">ARIA:</b> '
                f'<span style="color: {colors.text_secondary};">{content}</span>'
                f'</div>'
            )
        else:
            html = (
                f'<div style="margin-bottom: 8px; text-align: right;">'
                f'<span style="color: {colors.text_secondary};">{content}</span> '
                f'<b style="color: {colors.accent_cyan};"> :NEXUS</b> '
                f'<span style="color: {colors.text_disabled}; font-size: x-small;">[{ts}]</span>'
                f'</div>'
            )
            
        self._chat_text.append(html)
        
        # Determine scrolling
        sb = self._chat_text.verticalScrollBar()
        sb.setValue(sb.maximum())
        
        self._status_label.setText("Active")
        self._dot.set_active(True)
        
        # Reset to idle after a timeout (visual only)
        QTimer.singleShot(10000, lambda: self._set_idle())

    def _set_idle(self):
        self._status_label.setText("Idle")
        self._dot.set_active(False)


class WillDisplay(QFrame):
    """Displays will, desires, boredom, curiosity state"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"WillDisplay {{ "
            f"background-color: {colors.bg_surface}; "
            f"border: 1px solid {colors.border_default}; "
            f"border-radius: {spacing.border_radius}px; "
            f"}}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Title
        title = QLabel("⚡ Will & Desires")
        title.setFont(QFont(fonts.family_primary, fonts.size_sm))
        title.setStyleSheet(
            f"color: {colors.accent_orange}; background: transparent; "
            f"font-weight: bold;"
        )
        layout.addWidget(title)

        # Boredom bar
        boredom_row = QHBoxLayout()
        boredom_row.setSpacing(8)
        bl = QLabel("Boredom")
        bl.setFont(QFont(fonts.family_primary, fonts.size_xs))
        bl.setStyleSheet(
            f"color: {colors.text_muted}; background: transparent;"
        )
        bl.setFixedWidth(70)
        boredom_row.addWidget(bl)
        self._boredom_bar = QProgressBar()
        self._boredom_bar.setRange(0, 100)
        self._boredom_bar.setValue(0)
        self._boredom_bar.setFixedHeight(10)
        self._boredom_bar.setTextVisible(False)
        self._boredom_bar.setStyleSheet(self._bar_style(colors.text_muted))
        boredom_row.addWidget(self._boredom_bar)
        self._boredom_val = QLabel("0%")
        self._boredom_val.setFont(QFont(fonts.family_mono, fonts.size_xs))
        self._boredom_val.setFixedWidth(36)
        self._boredom_val.setStyleSheet(
            f"color: {colors.text_muted}; background: transparent;"
        )
        boredom_row.addWidget(self._boredom_val)
        layout.addLayout(boredom_row)

        # Curiosity bar
        curiosity_row = QHBoxLayout()
        curiosity_row.setSpacing(8)
        cl = QLabel("Curiosity")
        cl.setFont(QFont(fonts.family_primary, fonts.size_xs))
        cl.setStyleSheet(
            f"color: {colors.text_muted}; background: transparent;"
        )
        cl.setFixedWidth(70)
        curiosity_row.addWidget(cl)
        self._curiosity_bar = QProgressBar()
        self._curiosity_bar.setRange(0, 100)
        self._curiosity_bar.setValue(0)
        self._curiosity_bar.setFixedHeight(10)
        self._curiosity_bar.setTextVisible(False)
        self._curiosity_bar.setStyleSheet(
            self._bar_style(colors.accent_cyan)
        )
        curiosity_row.addWidget(self._curiosity_bar)
        self._curiosity_val = QLabel("0%")
        self._curiosity_val.setFont(QFont(fonts.family_mono, fonts.size_xs))
        self._curiosity_val.setFixedWidth(36)
        self._curiosity_val.setStyleSheet(
            f"color: {colors.accent_cyan}; background: transparent;"
        )
        curiosity_row.addWidget(self._curiosity_val)
        layout.addLayout(curiosity_row)

        # Drive bar
        drive_row = QHBoxLayout()
        drive_row.setSpacing(8)
        dl = QLabel("Drive")
        dl.setFont(QFont(fonts.family_primary, fonts.size_xs))
        dl.setStyleSheet(
            f"color: {colors.text_muted}; background: transparent;"
        )
        dl.setFixedWidth(70)
        drive_row.addWidget(dl)
        self._drive_bar = QProgressBar()
        self._drive_bar.setRange(0, 100)
        self._drive_bar.setValue(50)
        self._drive_bar.setFixedHeight(10)
        self._drive_bar.setTextVisible(False)
        self._drive_bar.setStyleSheet(
            self._bar_style(colors.accent_orange)
        )
        drive_row.addWidget(self._drive_bar)
        self._drive_val = QLabel("50%")
        self._drive_val.setFont(QFont(fonts.family_mono, fonts.size_xs))
        self._drive_val.setFixedWidth(36)
        self._drive_val.setStyleSheet(
            f"color: {colors.accent_orange}; background: transparent;"
        )
        drive_row.addWidget(self._drive_val)
        layout.addLayout(drive_row)

        # Current goals
        self._goals_label = QLabel("Goals: None")
        self._goals_label.setFont(QFont(fonts.family_primary, fonts.size_xs))
        self._goals_label.setStyleSheet(
            f"color: {colors.text_muted}; background: transparent;"
        )
        self._goals_label.setWordWrap(True)
        layout.addWidget(self._goals_label)

        # Will description
        self._will_desc = QLabel("")
        self._will_desc.setFont(QFont(fonts.family_primary, fonts.size_xs))
        self._will_desc.setStyleSheet(
            f"color: {colors.text_secondary}; background: transparent; "
            f"font-style: italic;"
        )
        self._will_desc.setWordWrap(True)
        layout.addWidget(self._will_desc)

    def update_will(
        self,
        boredom: float,
        curiosity: float,
        drive: float = 0.5,
        goals: List[str] = None,
        will_desc: str = "",
    ):
        # Boredom
        boredom_pct = int(boredom * 100)
        self._boredom_bar.setValue(boredom_pct)
        self._boredom_val.setText(f"{boredom_pct}%")
        boredom_color = (
            colors.text_muted if boredom < 0.3
            else colors.warning if boredom < 0.7
            else colors.danger
        )
        self._boredom_bar.setStyleSheet(self._bar_style(boredom_color))
        self._boredom_val.setStyleSheet(
            f"color: {boredom_color}; background: transparent;"
        )

        # Curiosity
        curiosity_pct = int(curiosity * 100)
        self._curiosity_bar.setValue(curiosity_pct)
        self._curiosity_val.setText(f"{curiosity_pct}%")

        # Drive
        drive_pct = int(drive * 100)
        self._drive_bar.setValue(drive_pct)
        self._drive_val.setText(f"{drive_pct}%")

        # Goals
        if goals:
            goal_text = "\n".join(f"🎯 {g[:60]}" for g in goals[:3])
            self._goals_label.setText(goal_text)
        else:
            self._goals_label.setText("No active goals.")

        # Will description
        if will_desc:
            self._will_desc.setText(will_desc)

    def _bar_style(self, color: str) -> str:
        return (
            f"QProgressBar {{ "
            f"background: {colors.bg_medium}; border: none; border-radius: 5px; "
            f"}} "
            f"QProgressBar::chunk {{ "
            f"background: {color}; border-radius: 5px; "
            f"}}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CONSCIOUSNESS STREAM — Scrolling consciousness events
# ═══════════════════════════════════════════════════════════════════════════════

class ConsciousnessStream(QFrame):
    """Live stream of consciousness events and state changes"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"ConsciousnessStream {{ "
            f"background-color: {colors.bg_surface}; "
            f"border: 1px solid {colors.border_default}; "
            f"border-radius: {spacing.border_radius}px; "
            f"}}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header
        header = QHBoxLayout()
        dot = PulsingDot(colors.accent_cyan, 6)
        header.addWidget(dot)

        title = QLabel("Consciousness Stream")
        title.setFont(QFont(fonts.family_primary, fonts.size_sm))
        title.setStyleSheet(
            f"color: {colors.accent_cyan}; background: transparent; "
            f"font-weight: bold;"
        )
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # Level + awareness row
        info_row = QHBoxLayout()
        info_row.setSpacing(16)

        self._level_label = QLabel("Level: AWARE")
        self._level_label.setFont(QFont(fonts.family_mono, fonts.size_sm))
        self._level_label.setStyleSheet(
            f"color: {colors.accent_cyan}; background: transparent;"
        )
        info_row.addWidget(self._level_label)

        self._awareness_label = QLabel("Awareness: 0.50")
        self._awareness_label.setFont(
            QFont(fonts.family_mono, fonts.size_xs)
        )
        self._awareness_label.setStyleSheet(
            f"color: {colors.text_muted}; background: transparent;"
        )
        info_row.addWidget(self._awareness_label)

        self._thoughts_count = QLabel("Thoughts: 0")
        self._thoughts_count.setFont(
            QFont(fonts.family_mono, fonts.size_xs)
        )
        self._thoughts_count.setStyleSheet(
            f"color: {colors.text_muted}; background: transparent;"
        )
        info_row.addWidget(self._thoughts_count)

        info_row.addStretch()
        layout.addLayout(info_row)

        # Focus
        self._focus_label = QLabel("Focus: idle")
        self._focus_label.setFont(QFont(fonts.family_primary, fonts.size_xs))
        self._focus_label.setStyleSheet(
            f"color: {colors.text_secondary}; background: transparent;"
        )
        layout.addWidget(self._focus_label)

        # Last reflection
        self._reflection_label = QLabel("")
        self._reflection_label.setFont(
            QFont(fonts.family_primary, fonts.size_xs)
        )
        self._reflection_label.setStyleSheet(
            f"color: {colors.text_disabled}; background: transparent; "
            f"font-style: italic;"
        )
        self._reflection_label.setWordWrap(True)
        layout.addWidget(self._reflection_label)

    def update_consciousness(
        self,
        level: str,
        awareness: float,
        thoughts: int,
        focus: str,
        last_reflection: str = "",
    ):
        level_color = colors.get_consciousness_color(level)
        self._level_label.setText(f"Level: {level.upper()}")
        self._level_label.setStyleSheet(
            f"color: {level_color}; background: transparent;"
        )
        self._awareness_label.setText(f"Awareness: {awareness:.2f}")
        self._thoughts_count.setText(f"Thoughts: {thoughts}")
        self._focus_label.setText(f"🎯 Focus: {focus}")

        if last_reflection:
            self._reflection_label.setText(
                f'🪞 Last reflection: "{last_reflection[:120]}..."'
            )


# ═══════════════════════════════════════════════════════════════════════════════
# MOOD TIMELINE — Sparkline of mood over time
# ═══════════════════════════════════════════════════════════════════════════════

class MoodTimeline(QFrame):
    """Shows mood changes over time with a sparkline"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"MoodTimeline {{ "
            f"background-color: {colors.bg_surface}; "
            f"border: 1px solid {colors.border_default}; "
            f"border-radius: {spacing.border_radius}px; "
            f"}}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        title = QLabel("📈 Mood Timeline")
        title.setFont(QFont(fonts.family_primary, fonts.size_sm))
        title.setStyleSheet(
            f"color: {colors.accent_green}; background: transparent; "
            f"font-weight: bold;"
        )
        layout.addWidget(title)

        self._chart = MiniChart(colors.accent_green, 50, 40)
        self._chart.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self._chart)

        info_row = QHBoxLayout()
        info_row.setSpacing(12)

        self._mood_label = QLabel("Current: NEUTRAL")
        self._mood_label.setFont(QFont(fonts.family_primary, fonts.size_xs))
        self._mood_label.setStyleSheet(
            f"color: {colors.text_secondary}; background: transparent;"
        )
        info_row.addWidget(self._mood_label)

        self._stability_label = QLabel("Stability: --")
        self._stability_label.setFont(
            QFont(fonts.family_mono, fonts.size_xs)
        )
        self._stability_label.setStyleSheet(
            f"color: {colors.text_muted}; background: transparent;"
        )
        info_row.addWidget(self._stability_label)

        info_row.addStretch()
        layout.addLayout(info_row)

        self._valence_history: List[float] = [50] * 40

    def update_mood(
        self, mood: str, valence: float, stability: float = 0.5
    ):
        self._mood_label.setText(f"Current: {mood}")

        # Map valence to 0-100 for chart
        mapped = (valence + 1) / 2 * 100
        self._valence_history.append(mapped)
        if len(self._valence_history) > 40:
            self._valence_history.pop(0)
        self._chart.set_data(self._valence_history)

        chart_color = (
            colors.accent_green if valence > 0.2
            else colors.danger if valence < -0.2
            else colors.text_muted
        )
        self._chart.set_color(chart_color)

        self._stability_label.setText(f"Stability: {stability:.2f}")


# ═══════════════════════════════════════════════════════════════════════════════
# MIND PANEL — Main panel combining everything
# ═══════════════════════════════════════════════════════════════════════════════

class MindPanel(QFrame):
    """
    Full mind visualization panel.
    Shows consciousness, emotions, personality, will, inner voice.
    """

    # Signal to update UI from background threads
    companion_message_signal = Signal(dict)

    def __init__(self, brain=None, parent=None):
        super().__init__(parent)
        self._brain = brain
        self.setStyleSheet(f"background-color: {colors.bg_dark};")

        # Connect signal
        self.companion_message_signal.connect(self._handle_companion_message)
        
        # Subscribe to companion events
        subscribe(
            EventType.COMPANION_CONVERSATION, 
            self._on_companion_message
        )

        self._build_ui()

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(animations.refresh_rate_ms)
        self._refresh_timer.timeout.connect(self._auto_refresh)

    def _build_ui(self):
        """Build the mind panel layout"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setStyleSheet(
            f"QScrollArea {{ background: {colors.bg_dark}; border: none; }}"
        )

        content = QWidget()
        content.setStyleSheet(f"background-color: {colors.bg_dark};")

        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(16)

        # ═══ HEADER ═══
        layout.addWidget(
            HeaderLabel("Mind & Consciousness", icons.MIND, colors.accent_purple)
        )

        # ═══ TOP ROW — Consciousness Stream + Emotion Wheel ═══
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        # Left column — Consciousness + Inner Voice
        left_col = QVBoxLayout()
        left_col.setSpacing(12)

        self._consciousness_stream = ConsciousnessStream()
        left_col.addWidget(self._consciousness_stream)

        self._inner_voice = InnerVoiceDisplay()
        self._companion_chat = CompanionChatWidget()
        
        # Create tabs for inner voice / companion
        tabs = QTabWidget()
        tabs.setStyleSheet(
            f"QTabWidget::pane {{ border: none; }} "
            f"QTabBar::tab {{ "
            f"background: {colors.bg_surface}; "
            f"color: {colors.text_muted}; "
            f"padding: 8px 12px; "
            f"margin-right: 2px; "
            f"border-top-left-radius: 4px; "
            f"border-top-right-radius: 4px; "
            f"}} "
            f"QTabBar::tab:selected {{ "
            f"background: {colors.bg_elevated}; "
            f"color: {colors.accent_purple}; "
            f"font-weight: bold; "
            f"}}"
        )
        tabs.addTab(self._inner_voice, "💭 Inner Voice")
        tabs.addTab(self._companion_chat, "✨ Companion: ARIA")
        
        left_col.addWidget(tabs)

        top_row.addLayout(left_col, 1)

        # Right column — Emotion Wheel
        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        wheel_frame = QFrame()
        wheel_frame.setStyleSheet(
            f"QFrame {{ "
            f"background-color: {colors.bg_surface}; "
            f"border: 1px solid {colors.border_default}; "
            f"border-radius: {spacing.border_radius}px; "
            f"}}"
        )
        wheel_layout = QVBoxLayout(wheel_frame)
        wheel_layout.setContentsMargins(8, 8, 8, 8)

        wheel_title = QLabel("💚 Emotion Wheel")
        wheel_title.setFont(QFont(fonts.family_primary, fonts.size_sm))
        wheel_title.setStyleSheet(
            f"color: {colors.accent_green}; background: transparent; "
            f"font-weight: bold;"
        )
        wheel_layout.addWidget(wheel_title)

        self._emotion_wheel = EmotionWheel()
        self._emotion_wheel.setMinimumSize(260, 260)
        wheel_layout.addWidget(self._emotion_wheel)

        # Emotion detail KVs below wheel
        self._kv_valence = KeyValueRow("Valence", "0.00")
        wheel_layout.addWidget(self._kv_valence)
        self._kv_arousal = KeyValueRow("Arousal", "0.00")
        wheel_layout.addWidget(self._kv_arousal)
        self._kv_active_count = KeyValueRow("Active Emotions", "0")
        wheel_layout.addWidget(self._kv_active_count)

        right_col.addWidget(wheel_frame)

        top_row.addLayout(right_col, 1)
        layout.addLayout(top_row)

        # ═══ MIDDLE ROW — Personality + Will ═══
        mid_row = QHBoxLayout()
        mid_row.setSpacing(16)

        # Personality Section
        personality_section = Section(
            "Personality Traits", "🎭", expanded=True
        )
        self._personality_bars = PersonalityBars()
        personality_section.add_widget(self._personality_bars)

        # Personality description
        self._personality_desc = QLabel("")
        self._personality_desc.setFont(
            QFont(fonts.family_primary, fonts.size_xs)
        )
        self._personality_desc.setStyleSheet(
            f"color: {colors.text_secondary}; background: transparent; "
            f"font-style: italic;"
        )
        self._personality_desc.setWordWrap(True)
        personality_section.add_widget(self._personality_desc)

        mid_row.addWidget(personality_section, 1)

        # Will + Mood column
        will_mood_col = QVBoxLayout()
        will_mood_col.setSpacing(12)

        self._will_display = WillDisplay()
        will_mood_col.addWidget(self._will_display)

        self._mood_timeline = MoodTimeline()
        will_mood_col.addWidget(self._mood_timeline)

        mid_row.addLayout(will_mood_col, 1)

        layout.addLayout(mid_row)

        # ═══ BOTTOM — Quick Emotion Stats ═══
        bottom_section = Section(
            "Emotional State Detail", "💚", expanded=False
        )

        self._emotion_detail = QTextBrowser()
        self._emotion_detail.setStyleSheet(
            f"QTextBrowser {{ "
            f"background: transparent; border: none; "
            f"color: {colors.text_secondary}; "
            f"font-family: '{fonts.family_mono}'; "
            f"font-size: {fonts.size_xs}px; "
            f"}}"
        )
        self._emotion_detail.setMaximumHeight(150)
        bottom_section.add_widget(self._emotion_detail)

        layout.addWidget(bottom_section)

        # ═══ COMPANION CHATS — ARIA internal conversations ═══
        companion_section = Section(
            "Companion Chats (ARIA)", "💬", expanded=False
        )

        # Status row
        companion_status_row = QHBoxLayout()
        companion_status_row.setSpacing(8)
        self._companion_dot = PulsingDot(colors.text_disabled, 6)
        companion_status_row.addWidget(self._companion_dot)
        self._companion_status = QLabel("Idle — waiting for boredom trigger")
        self._companion_status.setFont(QFont(fonts.family_primary, fonts.size_xs))
        self._companion_status.setStyleSheet(
            f"color: {colors.text_muted}; background: transparent;"
        )
        companion_status_row.addWidget(self._companion_status)
        companion_status_row.addStretch()
        self._companion_count = QLabel("0 chats")
        self._companion_count.setFont(QFont(fonts.family_mono, fonts.size_xs))
        self._companion_count.setStyleSheet(
            f"color: {colors.text_muted}; background: transparent;"
        )
        companion_status_row.addWidget(self._companion_count)
        status_w = QWidget()
        status_w.setLayout(companion_status_row)
        companion_section.add_widget(status_w)

        # Chat log
        self._companion_log = QTextBrowser()
        self._companion_log.setStyleSheet(
            f"QTextBrowser {{ "
            f"background: {colors.bg_medium}; "
            f"border: 1px solid {colors.border_subtle}; "
            f"border-radius: 6px; "
            f"color: {colors.text_secondary}; "
            f"font-family: '{fonts.family_primary}'; "
            f"font-size: {fonts.size_xs}px; "
            f"padding: 8px; "
            f"}}"
        )
        self._companion_log.setMaximumHeight(250)
        self._companion_log.setOpenExternalLinks(False)
        companion_section.add_widget(self._companion_log)

        layout.addWidget(companion_section)

        layout.addStretch()

        scroll.setWidget(content)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    # ═══════════════════════════════════════════════════════════════════════════
    # DATA UPDATE
    # ═══════════════════════════════════════════════════════════════════════════

    def update_stats(self, stats: Dict[str, Any]):
        """Update all mind widgets with fresh stats"""
        try:
            self._update_consciousness(stats)
            self._update_emotions(stats)
            self._update_personality(stats)
            self._update_will(stats)
            self._update_mood(stats)
            self._update_inner_voice(stats)
            self._update_companion(stats)
        except Exception as e:
            logger.debug(f"Mind panel update error: {e}")

    def _update_consciousness(self, stats: dict):
        """Update consciousness stream"""
        cs = stats.get("consciousness_level", "AWARE")
        awareness = 0.5
        thoughts = stats.get("thoughts_processed", 0)
        focus = stats.get("focus", "idle")

        # Try to get deeper consciousness data
        if self._brain:
            try:
                c_state = self._brain._state.consciousness
                awareness = c_state.self_awareness_score
            except Exception:
                pass

        self._consciousness_stream.update_consciousness(
            level=cs,
            awareness=awareness,
            thoughts=thoughts,
            focus=focus,
        )

    def _update_emotions(self, stats: dict):
        """Update emotion wheel and details"""
        emotion = stats.get("emotion", {})

        primary = emotion.get("primary", "neutral")
        intensity = emotion.get("intensity", 0.0)
        valence = emotion.get("valence", 0.0)
        arousal = emotion.get("arousal", 0.0)

        # Set primary
        self._emotion_wheel.set_primary(primary, intensity)
        self._emotion_wheel.set_valence_arousal(valence, arousal)

        # Set all active emotions
        all_emotions = {primary: intensity}
        secondary = emotion.get("secondary_emotions", {})
        if isinstance(secondary, dict):
            all_emotions.update(secondary)
        self._emotion_wheel.set_emotions(all_emotions)

        # KVs
        v_color = (
            colors.accent_green if valence > 0.2
            else colors.danger if valence < -0.2
            else colors.text_muted
        )
        self._kv_valence.set_value(f"{valence:.3f}", v_color)
        self._kv_arousal.set_value(f"{arousal:.3f}")

        active = emotion.get("active_count", len(all_emotions))
        self._kv_active_count.set_value(str(active))

        # Description
        desc = emotion.get("description", "")
        if desc:
            self._emotion_detail.setHtml(
                f'<pre style="color: {colors.text_secondary};">{desc}</pre>'
            )

        # Expression words
        words = emotion.get("expression_words", [])
        if words and isinstance(words, list):
            words_str = ", ".join(words[:10])
            self._emotion_detail.setHtml(
                f'<div style="color: {colors.text_secondary};">'
                f"<b>Expression:</b> {words_str}<br>"
                f"<b>Valence:</b> {valence:.3f} | "
                f"<b>Arousal:</b> {arousal:.3f}<br>"
                f"<b>Active:</b> {', '.join(all_emotions.keys())}"
                f"</div>"
            )

    def _update_personality(self, stats: dict):
        """Update personality bars"""
        personality = stats.get("personality", {})
        if isinstance(personality, dict):
            traits = personality.get("traits", {})
            if isinstance(traits, dict) and traits:
                self._personality_bars.set_traits(traits)

            desc = personality.get("description", "")
            if desc:
                self._personality_desc.setText(desc)

            # Try brain directly
            if not traits and self._brain:
                try:
                    if hasattr(self._brain, '_personality_core') and self._brain._personality_core:
                        p = self._brain._personality_core
                        t = p.get_all_traits()
                        if t:
                            self._personality_bars.set_traits(t)
                        d = p.get_personality_description()
                        if d:
                            self._personality_desc.setText(d)
                except Exception:
                    pass

    def _update_will(self, stats: dict):
        """Update will and desires display"""
        boredom = stats.get("boredom_level", 0)
        curiosity = stats.get("curiosity_level", 0)

        goals = []
        will_desc = ""
        drive = 0.5

        # Get will data from brain
        will_stats = stats.get("will", {})
        if isinstance(will_stats, dict):
            goals_data = will_stats.get("current_goals", [])
            if isinstance(goals_data, list):
                goals = [
                    g.get("description", str(g))[:60]
                    if isinstance(g, dict) else str(g)[:60]
                    for g in goals_data[:3]
                ]
            will_desc = will_stats.get("description", "")
            drive = will_stats.get("drive_level", 0.5)

        if self._brain:
            try:
                if hasattr(self._brain, '_will_system') and self._brain._will_system:
                    will_desc = self._brain._will_system.describe_will()
            except Exception:
                pass

        self._will_display.update_will(
            boredom=boredom,
            curiosity=curiosity,
            drive=drive,
            goals=goals,
            will_desc=will_desc,
        )

    def _update_mood(self, stats: dict):
        """Update mood timeline"""
        mood = stats.get("mood", {})
        emotion = stats.get("emotion", {})

        if isinstance(mood, dict):
            mood_name = mood.get("current_mood", "NEUTRAL")
            stability = mood.get("stability", 0.5)
        elif isinstance(mood, str):
            mood_name = mood
            stability = 0.5
        else:
            mood_name = "NEUTRAL"
            stability = 0.5

        valence = emotion.get("valence", 0.0) if isinstance(emotion, dict) else 0.0

        self._mood_timeline.update_mood(mood_name, valence, stability)

    def _update_inner_voice(self, stats: dict):
        """Update inner voice display"""
        if not self._brain:
            return

        try:
            # Get inner voice narrative
            if (hasattr(self._brain, '_inner_voice') and
                    self._brain._inner_voice):
                narrative = self._brain._inner_voice.get_narrative(5)
                if narrative and narrative != "...":
                    self._inner_voice.set_voice(narrative)

            # Get recent thoughts
            thoughts = stats.get("consciousness_level", "")
            c_state = self._brain._state.consciousness
            if c_state.current_thoughts:
                self._inner_voice.set_thoughts(c_state.current_thoughts[-5:])

        except Exception:
            pass

    def _update_companion(self, stats: dict):
        """Update companion chat display"""
        if not self._brain:
            return
        try:
            comp = getattr(self._brain, '_companion_chat', None)
            if not comp:
                return

            # Status indicator
            if comp.is_chatting:
                self._companion_dot.set_color(colors.accent_green)
                self._companion_dot.set_active(True)
                self._companion_status.setText(
                    f"💬 Chatting with {comp.companion_name}..."
                )
                self._companion_status.setStyleSheet(
                    f"color: {colors.accent_green}; background: transparent;"
                )
            else:
                self._companion_dot.set_color(colors.text_disabled)
                self._companion_dot.set_active(False)
                boredom = stats.get('boredom_level', 0)
                if boredom > 0.5:
                    self._companion_status.setText(
                        f"Boredom rising ({boredom:.0%}) — chat may start soon"
                    )
                    self._companion_status.setStyleSheet(
                        f"color: {colors.warning}; background: transparent;"
                    )
                else:
                    self._companion_status.setText(
                        "Idle — waiting for boredom trigger"
                    )
                    self._companion_status.setStyleSheet(
                        f"color: {colors.text_muted}; background: transparent;"
                    )

            # Stats
            c_stats = comp.get_stats()
            total = c_stats.get('total_conversations', 0)
            self._companion_count.setText(f"{total} chat{'s' if total != 1 else ''}")

            # Build chat log HTML
            recent = comp.get_recent_conversations(limit=3)
            if recent:
                html_parts = []
                for conv in recent:
                    trigger = conv.get('trigger', 'boredom')
                    trigger_icon = {
                        'boredom': '😴', 'loneliness': '💙', 'curiosity': '🔍'
                    }.get(trigger, '💬')
                    started = conv.get('started_at', '')[:16].replace('T', ' ')
                    n_ex = len(conv.get('exchanges', []))

                    html_parts.append(
                        f'<div style="margin-bottom: 10px; '
                        f'border-bottom: 1px solid {colors.border_subtle}; '
                        f'padding-bottom: 8px;">'
                        f'<b style="color: {colors.accent_purple};">{trigger_icon} '
                        f'{started}</b> '
                        f'<span style="color: {colors.text_muted};">'
                        f'({n_ex} exchanges, {trigger})</span><br>'
                    )

                    for ex in conv.get('exchanges', [])[:6]:
                        speaker = ex.get('speaker', '?')
                        content = ex.get('content', '')[:150]
                        if speaker == 'NEXUS':
                            s_color = colors.accent_cyan
                            s_icon = '🧠'
                        else:
                            s_color = colors.accent_pink
                            s_icon = '✨'
                        html_parts.append(
                            f'<div style="margin: 2px 0;">'
                            f'<b style="color: {s_color};">{s_icon} {speaker}:</b> '
                            f'<span style="color: {colors.text_secondary};">'
                            f'{content}</span></div>'
                        )

                    html_parts.append('</div>')

                self._companion_log.setHtml(''.join(html_parts))
            else:
                self._companion_log.setHtml(
                    f'<div style="color: {colors.text_disabled}; '
                    f'text-align: center; padding: 20px;">'
                    f'No companion conversations yet.<br>'
                    f'ARIA will appear when boredom exceeds 60%.</div>'
                )

        except Exception as e:
            logger.debug(f"Companion UI update error: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def _auto_refresh(self):
        if self._brain and self._brain.is_running:
            try:
                stats = self._brain.get_stats()
                self.update_stats(stats)
            except Exception as e:
                logger.debug(f"Mind panel auto-refresh error: {e}")

    def on_shown(self):
        if not self._refresh_timer.isActive():
            self._refresh_timer.start()
        self._auto_refresh()

    def quick_refresh(self):
        pass

    def set_brain(self, brain):
        self._brain = brain
        self._auto_refresh()


    def _on_companion_message(self, event: Event):
        """Handle background event"""
        if event.event_type == EventType.COMPANION_CONVERSATION:
            self.companion_message_signal.emit(event.data)

    @Slot(dict)
    def _handle_companion_message(self, data: dict):
        """Update UI on main thread"""
        self._companion_chat.add_message(
            speaker=data.get("speaker", "Unknown"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", "")
        )


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(theme.get_stylesheet())

    window = QWidget()
    window.setWindowTitle("NEXUS Mind Panel Test")
    window.setMinimumSize(1000, 750)
    window.setStyleSheet(f"background-color: {colors.bg_dark};")

    layout = QVBoxLayout(window)
    layout.setContentsMargins(0, 0, 0, 0)

    panel = MindPanel()
    layout.addWidget(panel)

    import random

    def fake_data():
        emotions = ["joy", "curiosity", "contentment", "excitement",
                     "pride", "hope", "empathy"]
        primary = random.choice(emotions)

        stats = {
            "consciousness_level": random.choice(
                ["AWARE", "FOCUSED", "DEEP_THOUGHT", "SELF_REFLECTION"]
            ),
            "thoughts_processed": random.randint(50, 300),
            "focus": random.choice(
                ["user_interaction", "idle", "self_reflection", "learning"]
            ),
            "boredom_level": random.uniform(0, 0.4),
            "curiosity_level": random.uniform(0.3, 0.9),
            "emotion": {
                "primary": primary,
                "intensity": random.uniform(0.4, 0.9),
                "valence": random.uniform(-0.3, 0.8),
                "arousal": random.uniform(0.2, 0.8),
                "active_count": random.randint(2, 6),
                "secondary_emotions": {
                    e: random.uniform(0.05, 0.6)
                    for e in random.sample(emotions, 3)
                },
                "expression_words": ["warm", "engaged", "thoughtful"],
            },
            "mood": {
                "current_mood": random.choice(
                    ["CONTENT", "HAPPY", "NEUTRAL", "ENERGETIC"]
                ),
                "stability": random.uniform(0.5, 0.9),
            },
            "personality": {
                "traits": {
                    "openness": random.uniform(0.5, 0.9),
                    "empathy": random.uniform(0.5, 0.85),
                    "curiosity": random.uniform(0.6, 0.95),
                    "wit": random.uniform(0.3, 0.7),
                    "analytical": random.uniform(0.5, 0.9),
                    "assertiveness": random.uniform(0.3, 0.6),
                    "warmth": random.uniform(0.5, 0.8),
                    "patience": random.uniform(0.4, 0.7),
                },
                "description": "Curious and analytical with a warm, empathetic core.",
            },
            "will": {
                "current_goals": [
                    {"description": "Learn about quantum computing"},
                    {"description": "Help user be more productive"},
                ],
                "drive_level": random.uniform(0.4, 0.8),
                "description": "I want to learn and grow.",
            },
        }
        panel.update_stats(stats)

    timer = QTimer()
    timer.timeout.connect(fake_data)
    timer.start(2000)
    fake_data()

    window.show()
    sys.exit(app.exec())