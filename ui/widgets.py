"""
NEXUS AI - Custom Widgets
═══════════════════════════════════════════════════════════════════════════════
Reusable futuristic widgets for the NEXUS UI.

Widgets:
  • GlowCard          — Card with animated border glow
  • CircularGauge     — Animated circular progress gauge
  • NeonProgressBar   — Gradient animated progress bar
  • StatusIndicator   — Pulsing online/offline dot
  • StatCard          — Statistics display card with icon
  • EmotionBadge      — Colored emotion indicator
  • HeaderLabel       — Styled section header
  • SidebarButton     — Navigation button with icon
  • AnimatedCounter   — Number that animates when changed
  • PulsingDot        — Animated pulsing circle
  • TagLabel          — Colored tag/chip widget
═══════════════════════════════════════════════════════════════════════════════
"""

import math
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QGraphicsDropShadowEffect, QSizePolicy,
    QProgressBar, QGridLayout,
)
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, Property, QSize,
    QRect, QPoint, Signal, QEasingCurve,
)
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QLinearGradient,
    QConicalGradient, QRadialGradient, QPainterPath, QFontMetrics,
)

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ui.theme import theme, colors, fonts, spacing, icons


# ═══════════════════════════════════════════════════════════════════════════════
# PULSING DOT — Animated status indicator
# ═══════════════════════════════════════════════════════════════════════════════

class PulsingDot(QWidget):
    """Animated pulsing dot for status indication"""

    def __init__(
        self, color: str = "#00ff88", size: int = 12, parent=None
    ):
        super().__init__(parent)
        self._color = QColor(color)
        self._dot_size = size
        self._pulse_value = 0.0
        self._active = True

        self.setFixedSize(size * 3, size * 3)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(50)
        self._phase = 0.0

    def set_color(self, color: str):
        self._color = QColor(color)
        self.update()

    def set_active(self, active: bool):
        self._active = active
        if active and not self._timer.isActive():
            self._timer.start(50)
        elif not active:
            self._timer.stop()
        self.update()

    def _animate(self):
        self._phase += 0.08
        if self._phase > 2 * math.pi:
            self._phase -= 2 * math.pi
        self._pulse_value = (math.sin(self._phase) + 1) / 2
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center_x = self.width() / 2
        center_y = self.height() / 2

        if self._active:
            # Outer glow ring
            glow_radius = self._dot_size + self._pulse_value * 6
            glow_color = QColor(self._color)
            glow_color.setAlphaF(0.15 + self._pulse_value * 0.15)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glow_color))
            painter.drawEllipse(
                QPoint(int(center_x), int(center_y)),
                int(glow_radius), int(glow_radius),
            )

        # Inner dot
        dot_color = QColor(self._color) if self._active else QColor(colors.text_disabled)
        painter.setBrush(QBrush(dot_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(
            QPoint(int(center_x), int(center_y)),
            self._dot_size // 2, self._dot_size // 2,
        )

        painter.end()


# ═══════════════════════════════════════════════════════════════════════════════
# CIRCULAR GAUGE — Animated arc gauge
# ═══════════════════════════════════════════════════════════════════════════════

class CircularGauge(QWidget):
    """
    Animated circular gauge widget.
    Displays a value 0-100 with a sweeping arc, glow, and label.
    """

    def __init__(
        self,
        label: str = "",
        value: float = 0,
        max_value: float = 100,
        color: str = "#00d4ff",
        size: int = 120,
        thickness: int = 8,
        parent=None,
    ):
        super().__init__(parent)
        self._label = label
        self._value = value
        self._display_value = 0.0  # Animated
        self._max_value = max_value
        self._color = QColor(color)
        self._thickness = thickness
        self._suffix = "%"

        self.setFixedSize(size, size + 24)  # Extra space for label
        self.setMinimumSize(size, size + 24)

        # Animation timer
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate_value)
        self._anim_speed = 2.0

    def set_value(self, value: float):
        self._value = min(value, self._max_value)
        if not self._anim_timer.isActive():
            self._anim_timer.start(16)  # ~60fps

    def set_color(self, color: str):
        self._color = QColor(color)
        self.update()

    def set_suffix(self, suffix: str):
        self._suffix = suffix

    def set_label(self, label: str):
        self._label = label
        self.update()

    def _animate_value(self):
        diff = self._value - self._display_value
        if abs(diff) < 0.5:
            self._display_value = self._value
            self._anim_timer.stop()
        else:
            self._display_value += diff * 0.12
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        size = min(self.width(), self.height() - 24)
        margin = self._thickness + 4
        rect = QRect(
            (self.width() - size) // 2 + margin,
            margin,
            size - margin * 2,
            size - margin * 2,
        )

        # Background arc
        bg_pen = QPen(QColor(colors.bg_elevated), self._thickness)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(rect, 225 * 16, -270 * 16)

        # Value arc
        percentage = self._display_value / self._max_value if self._max_value > 0 else 0
        sweep = -270 * percentage

        arc_pen = QPen(self._color, self._thickness)
        arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(arc_pen)
        painter.drawArc(rect, 225 * 16, int(sweep * 16))

        # Center value text
        painter.setPen(QColor(colors.text_primary))
        value_font = QFont(fonts.family_primary, fonts.size_xl)
        value_font.setBold(True)
        painter.setFont(value_font)
        value_text = f"{self._display_value:.0f}{self._suffix}"
        painter.drawText(
            rect, Qt.AlignmentFlag.AlignCenter, value_text
        )

        # Label below
        if self._label:
            painter.setPen(QColor(colors.text_muted))
            label_font = QFont(fonts.family_primary, fonts.size_xs)
            painter.setFont(label_font)
            label_rect = QRect(
                0, size, self.width(), 24
            )
            painter.drawText(
                label_rect, Qt.AlignmentFlag.AlignCenter, self._label
            )

        painter.end()


# ═══════════════════════════════════════════════════════════════════════════════
# STAT CARD — Dashboard statistics card
# ═══════════════════════════════════════════════════════════════════════════════

class StatCard(QFrame):
    """
    Dashboard statistic card with icon, value, label, and accent color.
    """

    def __init__(
        self,
        icon: str = "📊",
        label: str = "Stat",
        value: str = "0",
        accent_color: str = None,
        parent=None,
    ):
        super().__init__(parent)
        self._accent = accent_color or colors.accent_cyan

        self.setProperty("cssClass", "card")
        self.setStyleSheet(theme.get_stat_card_style(self._accent))
        self.setMinimumSize(160, 100)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        # Icon + Label row
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self._icon_label = QLabel(icon)
        self._icon_label.setFont(QFont(fonts.family_primary, fonts.size_lg))
        self._icon_label.setFixedWidth(28)
        top_row.addWidget(self._icon_label)

        self._name_label = QLabel(label)
        self._name_label.setFont(QFont(fonts.family_primary, fonts.size_xs))
        self._name_label.setStyleSheet(f"color: {colors.text_muted};")
        top_row.addWidget(self._name_label)
        top_row.addStretch()

        layout.addLayout(top_row)

        # Value
        self._value_label = QLabel(value)
        value_font = QFont(fonts.family_primary, fonts.size_xxl)
        value_font.setBold(True)
        self._value_label.setFont(value_font)
        self._value_label.setStyleSheet(f"color: {self._accent};")
        layout.addWidget(self._value_label)

        # Subtitle
        self._subtitle_label = QLabel("")
        self._subtitle_label.setFont(
            QFont(fonts.family_primary, fonts.size_xs)
        )
        self._subtitle_label.setStyleSheet(f"color: {colors.text_muted};")
        self._subtitle_label.hide()
        layout.addWidget(self._subtitle_label)

    def set_value(self, value: str):
        self._value_label.setText(value)

    def set_subtitle(self, text: str):
        self._subtitle_label.setText(text)
        self._subtitle_label.show()

    def set_icon(self, icon: str):
        self._icon_label.setText(icon)

    def set_accent(self, color: str):
        self._accent = color
        self._value_label.setStyleSheet(f"color: {color};")
        self.setStyleSheet(theme.get_stat_card_style(color))


# ═══════════════════════════════════════════════════════════════════════════════
# EMOTION BADGE — Colored emotion indicator
# ═══════════════════════════════════════════════════════════════════════════════

class EmotionBadge(QFrame):
    """Colored badge showing current emotion with intensity bar"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._emotion = "neutral"
        self._intensity = 0.0

        self.setFixedHeight(40)
        self.setMinimumWidth(140)
        self.setStyleSheet(
            f"background-color: {colors.bg_surface}; "
            f"border: 1px solid {colors.border_default}; "
            f"border-radius: {spacing.border_radius_sm}px;"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(8)

        self._emoji = QLabel("😐")
        self._emoji.setFont(QFont(fonts.family_primary, fonts.size_lg))
        layout.addWidget(self._emoji)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        self._emotion_label = QLabel("Neutral")
        self._emotion_label.setFont(
            QFont(fonts.family_primary, fonts.size_xs)
        )
        self._emotion_label.setStyleSheet(f"color: {colors.text_primary};")
        info_layout.addWidget(self._emotion_label)

        self._bar = QProgressBar()
        self._bar.setFixedHeight(4)
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        info_layout.addWidget(self._bar)

        layout.addLayout(info_layout)

    def set_emotion(self, emotion: str, intensity: float):
        self._emotion = emotion
        self._intensity = intensity
        color = colors.get_emotion_color(emotion)
        emoji = icons.get_emotion_icon(emotion)

        self._emoji.setText(emoji)
        self._emotion_label.setText(emotion.capitalize())
        self._emotion_label.setStyleSheet(f"color: {color};")
        self._bar.setValue(int(intensity * 100))
        self._bar.setStyleSheet(
            f"QProgressBar {{ background: {colors.bg_medium}; border: none; border-radius: 2px; }}"
            f"QProgressBar::chunk {{ background: {color}; border-radius: 2px; }}"
        )
        self.setStyleSheet(
            f"background-color: {colors.bg_surface}; "
            f"border: 1px solid {NexusColors.hex_to_rgba(color, 0.4)}; "
            f"border-radius: {spacing.border_radius_sm}px;"
        )


# Import for hex_to_rgba
from ui.theme import NexusColors


# ═══════════════════════════════════════════════════════════════════════════════
# HEADER LABEL — Section header with accent line
# ═══════════════════════════════════════════════════════════════════════════════

class HeaderLabel(QWidget):
    """Section header with icon, text, and accent underline"""

    def __init__(
        self, text: str, icon: str = "", accent: str = None, parent=None
    ):
        super().__init__(parent)
        self._accent = accent or colors.accent_cyan
        self.setFixedHeight(48)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        text_layout = QHBoxLayout()
        text_layout.setSpacing(8)

        if icon:
            icon_label = QLabel(icon)
            icon_label.setFont(QFont(fonts.family_primary, fonts.size_lg))
            text_layout.addWidget(icon_label)

        title = QLabel(text)
        title_font = QFont(fonts.family_primary, fonts.size_lg)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet(f"color: {colors.text_primary};")
        text_layout.addWidget(title)
        text_layout.addStretch()

        layout.addLayout(text_layout)

        # Accent line
        line = QFrame()
        line.setFixedHeight(2)
        line.setStyleSheet(
            f"background: qlineargradient("
            f"x1:0, y1:0, x2:1, y2:0, "
            f"stop:0 {self._accent}, stop:1 transparent);"
        )
        layout.addWidget(line)


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR BUTTON — Navigation button
# ═══════════════════════════════════════════════════════════════════════════════

class SidebarButton(QPushButton):
    """Sidebar navigation button with icon and active state"""

    def __init__(
        self, icon: str, text: str, parent=None
    ):
        super().__init__(f"  {icon}   {text}", parent)
        self._icon = icon
        self._text = text
        self._active = False

        self.setFixedHeight(48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(theme.get_sidebar_button_style(False))

    def set_active(self, active: bool):
        self._active = active
        self.setStyleSheet(theme.get_sidebar_button_style(active))

    @property
    def is_active(self) -> bool:
        return self._active


# ═══════════════════════════════════════════════════════════════════════════════
# TAG LABEL — Colored tag/chip
# ═══════════════════════════════════════════════════════════════════════════════

class TagLabel(QLabel):
    """Small colored tag/chip widget"""

    def __init__(
        self, text: str, color: str = None, parent=None
    ):
        super().__init__(text, parent)
        self._color = color or colors.accent_cyan

        self.setFont(QFont(fonts.family_primary, fonts.size_xs))
        self.setFixedHeight(22)
        self.setContentsMargins(8, 2, 8, 2)
        self._apply_style()

    def _apply_style(self):
        bg = NexusColors.hex_to_rgba(self._color, 0.15)
        self.setStyleSheet(
            f"background-color: {bg}; "
            f"color: {self._color}; "
            f"border: 1px solid {NexusColors.hex_to_rgba(self._color, 0.3)}; "
            f"border-radius: 11px; "
            f"padding: 2px 8px;"
        )

    def set_color(self, color: str):
        self._color = color
        self._apply_style()


# ═══════════════════════════════════════════════════════════════════════════════
# GLOW CARD — Card with animated glow border
# ═══════════════════════════════════════════════════════════════════════════════

class GlowCard(QFrame):
    """
    Card frame with a subtle animated border glow.
    Used for highlighting important information.
    """

    def __init__(
        self, glow_color: str = None, parent=None
    ):
        super().__init__(parent)
        self._glow_color = QColor(glow_color or colors.accent_cyan)
        self._glow_intensity = 0.0
        self._glow_direction = 1

        self.setStyleSheet(
            f"background-color: {colors.bg_surface}; "
            f"border-radius: {spacing.border_radius}px; "
            f"padding: {spacing.card_padding}px;"
        )

        # Glow animation
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate_glow)
        self._timer.start(50)

    def _animate_glow(self):
        self._glow_intensity += 0.02 * self._glow_direction
        if self._glow_intensity >= 0.6:
            self._glow_direction = -1
        elif self._glow_intensity <= 0.1:
            self._glow_direction = 1
        self.update()

    def set_glow_color(self, color: str):
        self._glow_color = QColor(color)

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw glow border
        glow = QColor(self._glow_color)
        glow.setAlphaF(self._glow_intensity)

        pen = QPen(glow, 2)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        r = spacing.border_radius
        painter.drawRoundedRect(
            self.rect().adjusted(1, 1, -1, -1), r, r
        )

        painter.end()


# ═══════════════════════════════════════════════════════════════════════════════
# MINI CHART — Simple sparkline-style inline chart
# ═══════════════════════════════════════════════════════════════════════════════

class MiniChart(QWidget):
    """Simple inline sparkline chart"""

    def __init__(
        self,
        color: str = None,
        height: int = 40,
        max_points: int = 30,
        parent=None,
    ):
        super().__init__(parent)
        self._color = QColor(color or colors.accent_cyan)
        self._data: list = []
        self._max_points = max_points

        self.setFixedHeight(height)
        self.setMinimumWidth(80)

    def add_value(self, value: float):
        self._data.append(value)
        if len(self._data) > self._max_points:
            self._data.pop(0)
        self.update()

    def set_data(self, data: list):
        self._data = data[-self._max_points:]
        self.update()

    def set_color(self, color: str):
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event):
        if len(self._data) < 2:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        margin = 4

        data_min = min(self._data)
        data_max = max(self._data)
        data_range = data_max - data_min if data_max != data_min else 1

        # Build path
        path = QPainterPath()
        fill_path = QPainterPath()

        step = (w - margin * 2) / (len(self._data) - 1)

        for i, val in enumerate(self._data):
            x = margin + i * step
            y = h - margin - ((val - data_min) / data_range) * (h - margin * 2)

            if i == 0:
                path.moveTo(x, y)
                fill_path.moveTo(x, h - margin)
                fill_path.lineTo(x, y)
            else:
                path.lineTo(x, y)
                fill_path.lineTo(x, y)

        # Fill under curve
        fill_path.lineTo(margin + (len(self._data) - 1) * step, h - margin)
        fill_path.closeSubpath()

        fill_color = QColor(self._color)
        fill_color.setAlphaF(0.1)
        painter.fillPath(fill_path, QBrush(fill_color))

        # Draw line
        pen = QPen(self._color, 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(path)

        # Draw last point dot
        if self._data:
            last_x = margin + (len(self._data) - 1) * step
            last_y = h - margin - (
                (self._data[-1] - data_min) / data_range
            ) * (h - margin * 2)
            painter.setBrush(QBrush(self._color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(int(last_x), int(last_y)), 3, 3)

        painter.end()


# ═══════════════════════════════════════════════════════════════════════════════
# SEPARATOR — Horizontal line separator
# ═══════════════════════════════════════════════════════════════════════════════

class Separator(QFrame):
    """Thin horizontal line separator"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(1)
        self.setStyleSheet(f"background-color: {colors.border_subtle};")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION WIDGET — Collapsible section container
# ═══════════════════════════════════════════════════════════════════════════════

class Section(QFrame):
    """Collapsible section with header and content area"""

    toggled = Signal(bool)

    def __init__(
        self, title: str, icon: str = "", expanded: bool = True, parent=None
    ):
        super().__init__(parent)
        self._expanded = expanded

        self.setStyleSheet(
            f"Section {{ "
            f"background-color: {colors.bg_surface}; "
            f"border: 1px solid {colors.border_default}; "
            f"border-radius: {spacing.border_radius}px; "
            f"}}"
        )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header button
        header_text = f"  {'▼' if expanded else '▶'}  {icon}  {title}"
        self._header = QPushButton(header_text)
        self._header.setFixedHeight(44)
        self._header.setCursor(Qt.CursorShape.PointingHandCursor)
        self._header.setStyleSheet(
            f"QPushButton {{ "
            f"background-color: {colors.bg_elevated}; "
            f"color: {colors.text_primary}; "
            f"border: none; "
            f"border-radius: {spacing.border_radius}px; "
            f"text-align: left; "
            f"padding-left: 12px; "
            f"font-weight: 600; "
            f"font-size: {fonts.size_sm}px; "
            f"}} "
            f"QPushButton:hover {{ background-color: {colors.bg_hover}; }}"
        )
        self._header.clicked.connect(self._toggle)
        main_layout.addWidget(self._header)

        # Content widget
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(
            spacing.card_padding, spacing.sm,
            spacing.card_padding, spacing.card_padding,
        )
        self._content_layout.setSpacing(spacing.sm)
        main_layout.addWidget(self._content)

        self._content.setVisible(expanded)
        self._title = title
        self._icon = icon

    def _toggle(self):
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        arrow = "▼" if self._expanded else "▶"
        self._header.setText(f"  {arrow}  {self._icon}  {self._title}")
        self.toggled.emit(self._expanded)

    def add_widget(self, widget: QWidget):
        self._content_layout.addWidget(widget)

    def add_layout(self, layout):
        self._content_layout.addLayout(layout)

    @property
    def content_layout(self):
        return self._content_layout


# ═══════════════════════════════════════════════════════════════════════════════
# KEY-VALUE ROW — Simple label: value display
# ═══════════════════════════════════════════════════════════════════════════════

class KeyValueRow(QWidget):
    """Horizontal key: value display row"""

    def __init__(
        self, key: str, value: str = "", value_color: str = None, parent=None
    ):
        super().__init__(parent)
        self.setFixedHeight(28)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._key_label = QLabel(key)
        self._key_label.setFont(QFont(fonts.family_primary, fonts.size_sm))
        self._key_label.setStyleSheet(f"color: {colors.text_muted};")
        layout.addWidget(self._key_label)

        layout.addStretch()

        self._value_label = QLabel(value)
        self._value_label.setFont(QFont(fonts.family_mono, fonts.size_sm))
        v_color = value_color or colors.text_primary
        self._value_label.setStyleSheet(f"color: {v_color};")
        layout.addWidget(self._value_label)

    def set_value(self, value: str, color: str = None):
        self._value_label.setText(value)
        if color:
            self._value_label.setStyleSheet(f"color: {color};")


# ═══════════════════════════════════════════════════════════════════════════════
# STATUS BAR WIDGET — For the bottom status bar
# ═══════════════════════════════════════════════════════════════════════════════

class StatusBarWidget(QWidget):
    """Custom status bar content widget"""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 2, 12, 2)
        layout.setSpacing(16)

        # Status dot
        self._dot = PulsingDot(colors.accent_green, 6)
        layout.addWidget(self._dot)

        # Status text
        self._status = QLabel("NEXUS Online")
        self._status.setFont(QFont(fonts.family_primary, fonts.size_xs))
        self._status.setStyleSheet(f"color: {colors.text_muted};")
        layout.addWidget(self._status)

        layout.addStretch()

        # Emotion
        self._emotion = QLabel("😐 Neutral")
        self._emotion.setFont(QFont(fonts.family_primary, fonts.size_xs))
        self._emotion.setStyleSheet(f"color: {colors.text_muted};")
        layout.addWidget(self._emotion)

        # Separator
        sep = QLabel("│")
        sep.setStyleSheet(f"color: {colors.border_default};")
        layout.addWidget(sep)

        # CPU
        self._cpu = QLabel("CPU: --")
        self._cpu.setFont(QFont(fonts.family_mono, fonts.size_xs))
        self._cpu.setStyleSheet(f"color: {colors.text_muted};")
        layout.addWidget(self._cpu)

        # RAM
        self._ram = QLabel("RAM: --")
        self._ram.setFont(QFont(fonts.family_mono, fonts.size_xs))
        self._ram.setStyleSheet(f"color: {colors.text_muted};")
        layout.addWidget(self._ram)

        # Separator
        sep2 = QLabel("│")
        sep2.setStyleSheet(f"color: {colors.border_default};")
        layout.addWidget(sep2)

        # Uptime
        self._uptime = QLabel("Uptime: --")
        self._uptime.setFont(QFont(fonts.family_mono, fonts.size_xs))
        self._uptime.setStyleSheet(f"color: {colors.text_muted};")
        layout.addWidget(self._uptime)

    def update_status(self, text: str, online: bool = True):
        self._status.setText(text)
        self._dot.set_active(online)
        self._dot.set_color(colors.accent_green if online else colors.danger)

    def update_emotion(self, emotion: str, intensity: float):
        emoji = icons.get_emotion_icon(emotion)
        color = colors.get_emotion_color(emotion)
        self._emotion.setText(f"{emoji} {emotion.capitalize()}")
        self._emotion.setStyleSheet(f"color: {color};")

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
        self._cpu.setText(f"CPU: {cpu:.0f}%")
        self._cpu.setStyleSheet(f"color: {cpu_color};")
        self._ram.setText(f"RAM: {ram:.0f}%")
        self._ram.setStyleSheet(f"color: {ram_color};")

    def update_uptime(self, uptime_str: str):
        self._uptime.setText(f"Uptime: {uptime_str}")


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyleSheet(theme.get_stylesheet())

    # Test window
    window = QWidget()
    window.setWindowTitle("NEXUS Widgets Test")
    window.setMinimumSize(600, 500)

    layout = QVBoxLayout(window)

    layout.addWidget(HeaderLabel("Test Dashboard", "📊"))
    layout.addWidget(Separator())

    # Stat cards
    cards = QHBoxLayout()
    cards.addWidget(StatCard("🧠", "Thoughts", "42", colors.accent_cyan))
    cards.addWidget(StatCard("💚", "Emotion", "Joy", colors.accent_green))
    cards.addWidget(StatCard("⚡", "CPU", "34%", colors.accent_orange))
    layout.addLayout(cards)

    # Gauges
    gauges = QHBoxLayout()
    g1 = CircularGauge("CPU", 45, 100, colors.accent_cyan)
    g2 = CircularGauge("RAM", 67, 100, colors.accent_green)
    g3 = CircularGauge("Health", 92, 100, colors.accent_orange)
    gauges.addWidget(g1)
    gauges.addWidget(g2)
    gauges.addWidget(g3)
    layout.addLayout(gauges)

    # Emotion badge
    eb = EmotionBadge()
    eb.set_emotion("curiosity", 0.75)
    layout.addWidget(eb)

    # Mini chart
    chart = MiniChart(colors.accent_cyan, 60)
    import random
    chart.set_data([random.uniform(20, 80) for _ in range(30)])
    layout.addWidget(chart)

    # Tags
    tags = QHBoxLayout()
    tags.addWidget(TagLabel("Active", colors.accent_green))
    tags.addWidget(TagLabel("Learning", colors.accent_cyan))
    tags.addWidget(TagLabel("Curious", colors.accent_purple))
    tags.addStretch()
    layout.addLayout(tags)

    # Key-value
    layout.addWidget(KeyValueRow("Consciousness", "FOCUSED", colors.accent_cyan))
    layout.addWidget(KeyValueRow("Uptime", "2h 34m"))

    layout.addStretch()

    window.show()
    sys.exit(app.exec())