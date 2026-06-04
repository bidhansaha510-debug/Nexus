"""
NEXUS AI - Knowledge Panel (Advanced)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Real-time command center for NEXUS's knowledge & learning systems.

Layout:
  ┌─────────────────────────────────────────────────────────────────┐
  │  📚 Knowledge Base                                              │
  │  ──────────────────────────────────────────────────────── cyan   │
  │                                                                  │
  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
  │  │ Knowledge │ │ Curiosity│ │ Research │ │ Confidence│           │
  │  │  Gauge    │ │  Gauge   │ │  Gauge   │ │  Gauge   │           │
  │  │   42      │ │   7      │ │   12     │ │   72%    │           │
  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
  │                                                                  │
  │  [Search bar ___________________________] [🔍 Search]           │
  │                                                                  │
  │  ▶ 🔮 Curiosity Queue (7 active)                                │
  │  ┌──────────────────────────────────────┐                       │
  │  │  ● BURNING  quantum consciousness    │  ┌─ Detail ────────┐ │
  │  │  ● HIGH     emergent AI behavior     │  │ Topic: ...      │ │
  │  │  ● MODERATE philosophy of mind       │  │ Question: ...   │ │
  │  │  ● LOW      fractal mathematics      │  │ Related: [tags] │ │
  │  └──────────────────────────────────────┘  └──────────────────┘ │
  │                                                                  │
  │  ▶ 📚 Recent Learnings                                          │
  │  ┌──────────────────────────────────────┐                       │
  │  │  📖 Wikipedia: Quantum Entanglement  │                       │
  │  │  🌐 Web: Neural Architecture Search  │                       │
  │  │  🔬 Research: Consciousness Studies  │                       │
  │  └──────────────────────────────────────┘                       │
  │                                                                  │
  │  ▶ 📊 Learning Activity  [sparkline ~~~~~~~~~~~~]               │
  │  ▶ 🏷️ Top Topics  [tag] [tag] [tag] [tag]                      │
  └─────────────────────────────────────────────────────────────────┘
"""
import sys
import math
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QTextBrowser, QSplitter, QScrollArea, QGridLayout,
    QSizePolicy, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QTimer, QSize, Signal
from PySide6.QtGui import (
    QFont, QColor, QIcon, QPainter, QPen, QBrush,
    QLinearGradient, QPainterPath
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ui.theme import theme, colors, fonts, spacing, icons
from ui.widgets import (
    HeaderLabel, Section, TagLabel, StatCard,
    CircularGauge, MiniChart, GlowCard, PulsingDot, Separator
)
from utils.logger import get_logger

logger = get_logger("knowledge_panel")


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

URGENCY_COLORS = {
    "BURNING":  "#ff4444",
    "HIGH":     "#ff8c00",
    "MODERATE": "#ffcc00",
    "LOW":      "#66ccff",
    "IDLE":     "#888888",
}

URGENCY_ICONS = {
    "BURNING":  "🔥",
    "HIGH":     "🔺",
    "MODERATE": "◆",
    "LOW":      "○",
    "IDLE":     "·",
}

SOURCE_ICONS = {
    "wikipedia":      "📖",
    "web":            "🌐",
    "research":       "🔬",
    "llm":            "🤖",
    "user":           "👤",
    "self_generated": "💭",
    "unknown":        "❓",
}

SOURCE_COLORS = {
    "wikipedia":      "#4ecdc4",
    "web":            "#45b7d1",
    "research":       "#96ceb4",
    "llm":            "#dda0dd",
    "user":           "#f7dc6f",
    "self_generated": "#bb86fc",
    "unknown":        "#888888",
}


# ═══════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE GRAPH MINI VISUALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

class KnowledgeNetworkWidget(QWidget):
    """
    Animated mini network graph showing knowledge topic connections.
    Renders floating nodes with connecting lines — purely visual.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._nodes: List[Dict[str, Any]] = []
        self._phase = 0.0
        self.setMinimumHeight(100)
        self.setMinimumWidth(200)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(60)

    def set_topics(self, topics: List[str]):
        """Set topic nodes for the visualization."""
        self._nodes = []
        if not topics:
            self.update()
            return

        for i, topic in enumerate(topics[:12]):
            angle = (2 * math.pi * i) / min(len(topics), 12)
            self._nodes.append({
                "label": topic[:18],
                "angle": angle,
                "radius_offset": (hash(topic) % 30) / 100.0,
                "speed": 0.002 + (hash(topic) % 10) * 0.0003,
            })
        self.update()

    def _animate(self):
        self._phase += 0.02
        self.update()

    def paintEvent(self, event):
        if not self._nodes:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        base_radius = min(w, h) * 0.35

        positions = []
        for node in self._nodes:
            angle = node["angle"] + self._phase * node["speed"]
            r = base_radius * (0.6 + node["radius_offset"])
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            positions.append((x, y, node["label"]))

        # Draw connections (faint lines between nearby nodes)
        pen = QPen(QColor(colors.accent_cyan))
        pen.setWidthF(0.5)
        for i, (x1, y1, _) in enumerate(positions):
            for j, (x2, y2, _) in enumerate(positions):
                if i >= j:
                    continue
                dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                if dist < base_radius * 1.2:
                    alpha = max(15, int(60 - dist / 3))
                    line_color = QColor(colors.accent_cyan)
                    line_color.setAlpha(alpha)
                    pen.setColor(line_color)
                    painter.setPen(pen)
                    painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # Draw nodes
        for x, y, label in positions:
            # Glow
            glow = QColor(colors.accent_cyan)
            glow.setAlpha(40)
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(x) - 6, int(y) - 6, 12, 12)

            # Core dot
            core = QColor(colors.accent_cyan)
            core.setAlpha(200)
            painter.setBrush(QBrush(core))
            painter.drawEllipse(int(x) - 3, int(y) - 3, 6, 6)

            # Label
            font = QFont(fonts.family_primary, 8)
            painter.setFont(font)
            painter.setPen(QColor(colors.text_secondary))
            painter.drawText(int(x) - 40, int(y) + 10, 80, 16,
                             Qt.AlignmentFlag.AlignCenter, label)

        # Center glow
        center_glow = QColor(colors.accent_purple)
        pulse = int(20 + 15 * math.sin(self._phase * 2))
        center_glow.setAlpha(pulse)
        painter.setBrush(QBrush(center_glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(cx) - 15, int(cy) - 15, 30, 30)

        painter.end()


# ═══════════════════════════════════════════════════════════════════════════════
# URGENCY BAR WIDGET
# ═══════════════════════════════════════════════════════════════════════════════

class UrgencyBar(QWidget):
    """Horizontal bar showing urgency distribution of curiosity topics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._distribution: Dict[str, int] = {}
        self.setFixedHeight(24)
        self.setMinimumWidth(100)

    def set_distribution(self, dist: Dict[str, int]):
        self._distribution = dist
        self.update()

    def paintEvent(self, event):
        if not self._distribution:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        total = sum(self._distribution.values())
        if total == 0:
            painter.end()
            return

        w, h = self.width(), self.height()
        x = 0
        radius = 4

        order = ["BURNING", "HIGH", "MODERATE", "LOW", "IDLE"]
        for urgency in order:
            count = self._distribution.get(urgency, 0)
            if count == 0:
                continue
            seg_w = max(8, int(w * count / total))

            color = QColor(URGENCY_COLORS.get(urgency, "#888"))
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)

            path = QPainterPath()
            path.addRoundedRect(float(x), 2, float(seg_w - 1), float(h - 4),
                                radius, radius)
            painter.drawPath(path)

            # Label inside segment
            if seg_w > 30:
                font = QFont(fonts.family_primary, 8)
                font.setBold(True)
                painter.setFont(font)
                painter.setPen(QColor("#000000"))
                painter.drawText(int(x), 2, seg_w, h - 4,
                                 Qt.AlignmentFlag.AlignCenter, str(count))

            x += seg_w

        painter.end()


# ═══════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE PANEL
# ═══════════════════════════════════════════════════════════════════════════════

class KnowledgePanel(QFrame):
    """
    Advanced Knowledge Base panel with gauges, sparklines, collapsible
    sections, network visualization, and rich detail view.
    """

    def __init__(self, brain=None, parent=None):
        super().__init__(parent)
        self._brain = brain
        self.setStyleSheet(f"background-color: {colors.bg_dark};")

        # Data caches
        self._curiosity_cache: list = []
        self._recent_cache: list = []
        self._search_cache: list = []
        self._knowledge_history: list = [0] * 30  # sparkline data

        self._build_ui()

        # Refresh timers
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_data)
        self._refresh_timer.start(5000)

        # Slower timer for network graph
        self._graph_timer = QTimer(self)
        self._graph_timer.timeout.connect(self._refresh_graph)
        self._graph_timer.start(15000)

    # ═══════════════════════════════════════════════════════════════════════════
    # UI CONSTRUCTION
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        # Scrollable main layout
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
        layout.addWidget(HeaderLabel("Knowledge Base", icons.KNOWLEDGE, colors.accent_cyan))

        # ── Gauges Row ──
        gauges_row = QHBoxLayout()
        gauges_row.setSpacing(12)

        self._gauge_entries = CircularGauge("Entries", 0, 500, colors.accent_cyan, 120, 6)
        self._gauge_curiosity = CircularGauge("Curious", 0, 50, colors.accent_purple, 120, 6)
        self._gauge_research = CircularGauge("Sessions", 0, 100, colors.accent_green, 120, 6)
        self._gauge_confidence = CircularGauge("Confidence", 0, 100, colors.accent_orange, 120, 6)
        self._gauge_confidence.set_suffix("%")

        gauges_row.addWidget(self._gauge_entries)
        gauges_row.addWidget(self._gauge_curiosity)
        gauges_row.addWidget(self._gauge_research)
        gauges_row.addWidget(self._gauge_confidence)
        layout.addLayout(gauges_row)

        # ── Search Bar ──
        search_row = QHBoxLayout()
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search local knowledge or web...")
        self._search_input.setStyleSheet(f"""
            QLineEdit {{ background: {colors.bg_medium}; border: 1px solid {colors.border_default};
                         border-radius: 8px; padding: 10px 14px; color: {colors.text_primary};
                         font-size: 13px; }}
            QLineEdit:focus {{ border: 1px solid {colors.accent_cyan}; }}
        """)
        self._search_input.returnPressed.connect(self._perform_search)
        search_row.addWidget(self._search_input)

        search_btn = QPushButton("🔍 Search")
        search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_btn.setStyleSheet(
            f"QPushButton {{ background-color: {colors.accent_cyan}; color: {colors.text_on_accent}; "
            f"border-radius: 8px; padding: 10px 20px; font-weight: bold; font-size: 13px; }}"
            f"QPushButton:hover {{ background-color: #33eeff; }}"
        )
        search_btn.clicked.connect(self._perform_search)
        search_row.addWidget(search_btn)
        layout.addLayout(search_row)

        # ── Main Splitter: Left Lists / Right Detail ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {colors.border_subtle}; }}"
        )

        # ─── Left Panel (scrollable lists) ───
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(8)

        # -- Curiosity Queue Section --
        self._curiosity_section = Section("Curiosity Queue", "🔮", expanded=True)
        curiosity_inner = QVBoxLayout()

        # Urgency distribution bar
        self._urgency_bar = UrgencyBar()
        curiosity_inner.addWidget(self._urgency_bar)

        self._curiosity_list = QListWidget()
        self._curiosity_list.setStyleSheet(self._list_style())
        self._curiosity_list.setMinimumHeight(120)
        self._curiosity_list.itemClicked.connect(self._show_curiosity_detail)
        curiosity_inner.addWidget(self._curiosity_list)

        self._curiosity_section.add_layout(curiosity_inner)
        left_layout.addWidget(self._curiosity_section)

        # -- Recent Learnings Section --
        self._recent_section = Section("Recent Learnings", "📚", expanded=True)
        recent_inner = QVBoxLayout()

        self._recent_list = QListWidget()
        self._recent_list.setStyleSheet(self._list_style())
        self._recent_list.setMinimumHeight(120)
        self._recent_list.itemClicked.connect(self._show_recent_detail)
        recent_inner.addWidget(self._recent_list)

        self._recent_section.add_layout(recent_inner)
        left_layout.addWidget(self._recent_section)

        # -- Learning Activity Section --
        self._activity_section = Section("Learning Activity", "📊", expanded=True)
        activity_inner = QVBoxLayout()

        # Sparkline chart
        chart_row = QHBoxLayout()
        chart_label = QLabel("Knowledge Growth")
        chart_label.setStyleSheet(
            f"color: {colors.text_secondary}; font-weight: bold; font-size: 12px;"
        )
        self._knowledge_chart = MiniChart(colors.accent_cyan, 50, 30)
        chart_row.addWidget(chart_label)
        chart_row.addWidget(self._knowledge_chart)
        activity_inner.addLayout(chart_row)

        # Stats cards row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)
        self._stat_pages = StatCard("📄", "Pages Read", "0", colors.accent_cyan)
        self._stat_words = StatCard("📝", "Words", "0", colors.accent_green)
        self._stat_researched = StatCard("✅", "Researched", "0", colors.accent_purple)
        stats_row.addWidget(self._stat_pages)
        stats_row.addWidget(self._stat_words)
        stats_row.addWidget(self._stat_researched)
        activity_inner.addLayout(stats_row)

        self._activity_section.add_layout(activity_inner)
        left_layout.addWidget(self._activity_section)

        # -- Top Topics Section --
        self._topics_section = Section("Top Topics", "🏷️", expanded=False)
        topics_inner = QVBoxLayout()

        self._topics_flow = QWidget()
        self._topics_flow_layout = QHBoxLayout(self._topics_flow)
        self._topics_flow_layout.setContentsMargins(0, 0, 0, 0)
        self._topics_flow_layout.setSpacing(6)
        topics_inner.addWidget(self._topics_flow)

        self._topics_section.add_layout(topics_inner)
        left_layout.addWidget(self._topics_section)

        left_layout.addStretch()
        splitter.addWidget(left_widget)

        # ─── Right Panel: Detail View ───
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.setSpacing(8)

        # Knowledge network visualization
        self._network_section = Section("Knowledge Map", "🧠", expanded=True)
        self._network_widget = KnowledgeNetworkWidget()
        self._network_widget.setMinimumHeight(140)
        self._network_section.add_widget(self._network_widget)
        right_layout.addWidget(self._network_section)

        # Detail browser
        self._detail_view = QTextBrowser()
        self._detail_view.setOpenExternalLinks(True)
        self._detail_view.setPlaceholderText("Select an item to view details...")
        self._detail_view.setStyleSheet(f"""
            QTextBrowser {{ background: {colors.bg_surface}; border: 1px solid {colors.border_default};
                            border-radius: 8px; padding: 16px; color: {colors.text_primary};
                            font-size: 13px; }}
        """)
        right_layout.addWidget(self._detail_view)

        splitter.addWidget(right_widget)
        splitter.setSizes([380, 620])
        layout.addWidget(splitter)

        scroll.setWidget(container)

        # Wrap in outer layout
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _list_style(self) -> str:
        """Shared stylesheet for list widgets."""
        return (
            f"QListWidget {{ background: {colors.bg_surface}; border: 1px solid {colors.border_default}; "
            f"border-radius: 8px; padding: 4px; color: {colors.text_primary}; "
            f"font-size: 13px; }} "
            f"QListWidget::item {{ padding: 7px 10px; border-radius: 4px; }} "
            f"QListWidget::item:selected {{ background: {colors.bg_medium}; "
            f"border-left: 3px solid {colors.accent_cyan}; }} "
            f"QListWidget::item:hover {{ background: {colors.bg_medium}; }}"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def set_brain(self, brain):
        """Connect the panel to the brain instance."""
        self._brain = brain
        self._refresh_data()
        self._refresh_graph()

    # ═══════════════════════════════════════════════════════════════════════════
    # DATA REFRESH
    # ═══════════════════════════════════════════════════════════════════════════

    def _refresh_data(self):
        """Fetch live data from the brain's learning subsystems."""
        if not self._brain:
            return

        self._refresh_gauges()
        self._refresh_curiosity()
        self._refresh_recent()
        self._refresh_activity()
        self._refresh_top_topics()

    def _refresh_gauges(self):
        """Update the gauge widgets with current stats."""
        try:
            ls = self._get_learning_system()
            if not ls:
                return

            stats = ls.get_stats()
            kb_stats = stats.get("knowledge_base", {})
            cur_stats = stats.get("curiosity", {})
            res_stats = stats.get("research", {})

            # Knowledge entries gauge
            total_entries = kb_stats.get("total_entries", 0) if not kb_stats.get("error") else 0
            self._gauge_entries.set_value(min(total_entries, 500))
            self._gauge_entries.set_label(f"Entries")

            # Active curiosity topics gauge
            active = cur_stats.get("active_topics", 0) if not cur_stats.get("error") else 0
            self._gauge_curiosity.set_value(min(active, 50))

            # Research sessions gauge
            sessions = res_stats.get("total_sessions", 0) if not res_stats.get("error") else 0
            self._gauge_research.set_value(min(sessions, 100))

            # Average confidence (from knowledge base)
            # Use total_entries as a proxy for confidence percentage
            if total_entries > 0:
                # Simple confidence heuristic: more entries = higher confidence
                conf = min(95, 30 + total_entries * 2)
            else:
                conf = 0
            self._gauge_confidence.set_value(conf)

            # Update sparkline
            self._knowledge_history.append(total_entries)
            if len(self._knowledge_history) > 30:
                self._knowledge_history.pop(0)
            self._knowledge_chart.set_data(self._knowledge_history)

        except Exception as e:
            logger.debug(f"Gauge refresh error: {e}")

    def _refresh_curiosity(self):
        """Populate the curiosity queue list."""
        try:
            ls = self._get_learning_system()
            if not ls:
                return

            topics = ls.get_curiosity_topics(20)
            self._curiosity_cache = topics

            # Update section title with count
            count = len(topics)
            self._curiosity_section._header.setText(
                f"  ▶  🔮  Curiosity Queue ({count} active)" if not self._curiosity_section._content.isVisible()
                else f"  ▼  🔮  Curiosity Queue ({count} active)"
            )

            # Update urgency distribution bar
            urgency_dist = {}
            for t in topics:
                urg = t.get("urgency", "MODERATE")
                urgency_dist[urg] = urgency_dist.get(urg, 0) + 1
            self._urgency_bar.set_distribution(urgency_dist)

            self._curiosity_list.clear()
            if not topics:
                item = QListWidgetItem("  No curiosity topics yet...")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                item.setForeground(QColor(colors.text_secondary))
                self._curiosity_list.addItem(item)
                return

            for t in topics:
                topic_name = t.get("topic", "Unknown")
                urgency = t.get("urgency", "MODERATE")
                source = t.get("source", "internal")
                color = URGENCY_COLORS.get(urgency, URGENCY_COLORS["MODERATE"])
                icon = URGENCY_ICONS.get(urgency, "◆")
                researched = t.get("researched", False)

                prefix = "✅" if researched else icon
                item = QListWidgetItem(f"  {prefix}  {topic_name}")
                item.setForeground(QColor(color))
                item.setToolTip(
                    f"Urgency: {urgency}\n"
                    f"Source: {source}\n"
                    f"Reason: {t.get('reason', 'N/A')}\n"
                    f"Question: {t.get('question', 'N/A')}"
                )
                self._curiosity_list.addItem(item)

        except Exception as e:
            logger.warning(f"Curiosity refresh error: {e}")

    def _refresh_recent(self):
        """Populate the recent learnings list."""
        try:
            kb = self._get_knowledge_base()
            if not kb:
                return

            entries = kb.get_recent(20)
            self._recent_cache = entries

            # Update section title
            count = len(entries)
            self._recent_section._header.setText(
                f"  ▶  📚  Recent Learnings ({count})" if not self._recent_section._content.isVisible()
                else f"  ▼  📚  Recent Learnings ({count})"
            )

            self._recent_list.clear()
            if not entries:
                item = QListWidgetItem("  No knowledge entries yet...")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                item.setForeground(QColor(colors.text_secondary))
                self._recent_list.addItem(item)
                return

            for entry in entries:
                src_val = entry.source.value if hasattr(entry.source, 'value') else str(entry.source)
                source_icon = SOURCE_ICONS.get(src_val, "📄")
                source_color = SOURCE_COLORS.get(src_val, colors.text_primary)
                title = entry.title or entry.topic or "Untitled"
                label = f"  {source_icon}  {title}"
                if len(label) > 55:
                    label = label[:52] + "..."

                item = QListWidgetItem(label)
                item.setForeground(QColor(source_color))
                item.setToolTip(
                    f"Topic: {entry.topic}\n"
                    f"Source: {src_val}\n"
                    f"Importance: {entry.importance:.0%}\n"
                    f"Confidence: {entry.confidence:.0%}\n"
                    f"Created: {entry.created_at}"
                )
                self._recent_list.addItem(item)

        except Exception as e:
            logger.warning(f"Recent learnings refresh error: {e}")

    def _refresh_activity(self):
        """Update the activity stats cards."""
        try:
            ls = self._get_learning_system()
            if not ls:
                return

            stats = ls.get_stats()
            res_stats = stats.get("research", {})
            cur_stats = stats.get("curiosity", {})

            if res_stats and not res_stats.get("error"):
                pages = res_stats.get("total_pages_read", 0)
                words = res_stats.get("total_words_read", 0)
                self._stat_pages.set_value(str(pages))
                # Format words nicely
                if words >= 1_000_000:
                    self._stat_words.set_value(f"{words / 1_000_000:.1f}M")
                elif words >= 1000:
                    self._stat_words.set_value(f"{words / 1000:.1f}K")
                else:
                    self._stat_words.set_value(str(words))

                last_topic = res_stats.get("last_research_topic", "")
                if last_topic:
                    self._stat_pages.set_subtitle(f"Last: {last_topic[:20]}")

            if cur_stats and not cur_stats.get("error"):
                researched = cur_stats.get("topics_researched", 0)
                self._stat_researched.set_value(str(researched))

        except Exception as e:
            logger.debug(f"Activity refresh error: {e}")

    def _refresh_top_topics(self):
        """Update the top topics tag cloud."""
        try:
            ls = self._get_learning_system()
            if not ls:
                return

            stats = ls.get_stats()
            kb_stats = stats.get("knowledge_base", {})
            top_topics = kb_stats.get("top_topics", {}) if not kb_stats.get("error") else {}

            # Clear existing tags
            while self._topics_flow_layout.count():
                child = self._topics_flow_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            if not top_topics:
                empty_label = QLabel("No topics yet")
                empty_label.setStyleSheet(f"color: {colors.text_secondary}; font-size: 12px;")
                self._topics_flow_layout.addWidget(empty_label)
                return

            topic_colors = [
                colors.accent_cyan, colors.accent_purple, colors.accent_green,
                colors.accent_orange, "#ff6b9d", "#45b7d1", "#96ceb4",
                "#dda0dd", "#f7dc6f", "#bb86fc"
            ]

            for i, (topic, count) in enumerate(list(top_topics.items())[:10]):
                tag = TagLabel(f"{topic} ({count})", topic_colors[i % len(topic_colors)])
                self._topics_flow_layout.addWidget(tag)

            self._topics_flow_layout.addStretch()

        except Exception as e:
            logger.debug(f"Top topics refresh error: {e}")

    def _refresh_graph(self):
        """Update the knowledge network visualization."""
        try:
            ls = self._get_learning_system()
            if not ls:
                return
            
            stats = ls.get_stats()
            kb_stats = stats.get("knowledge_base", {})
            top_topics = kb_stats.get("top_topics", {})
            
            topics = [key for key in (top_topics or {}).keys()][:12]
            self._network_widget.set_topics(topics)
            
        except Exception as e:
            logger.debug(f"Graph refresh error: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # SEARCH
    # ═══════════════════════════════════════════════════════════════════════════

    def _perform_search(self):
        """Search the knowledge base."""
        query = self._search_input.text().strip()
        if not query:
            return
        
        self._detail_view.setHtml(f"<h3 style='color:{colors.accent_cyan}'>🔍 Searching for '{query}'...</h3>")
        
        ls = self._get_learning_system()
        if not ls:
            self._detail_view.setHtml(f"<p style='color:{colors.text_secondary}'>Learning system not available yet.</p>")
            return
        
        try:
            results = list(ls.search_knowledge(query, limit=20))
            self._search_cache = results
            html = f"<h3 style='color:{colors.accent_cyan}'>Results for '{query}'</h3>"
            
            if not results:
                html += f"<p style='color:{colors.text_secondary}'>No local knowledge found.</p>"
            else:
                html += ''.join(self._build_search_results_html(query, result) for result in results)
                
            self._detail_view.setHtml(html)
        except Exception as e:
            logger.error(f"Knowledge search error: {e}")
            self._detail_view.setHtml(f"<p style='color:#ff6666'>Search error: {e}</p>")

    # ═══════════════════════════════════════════════════════════════════════════
    # DETAIL VIEWS
    # ═══════════════════════════════════════════════════════════════════════════

    def _show_curiosity_detail(self, item: QListWidgetItem):
        """Show detail for a clicked curiosity topic."""
        idx = self._curiosity_list.row(item)
        if not 0 <= idx < len(self._curosity_cache):
            return
    
        topic = self._curiosity_cache[idx]
        html = self._build_curiosity_html(topic)
        self._detail_view.setHtml(html)

    def _show_recent_detail(self, item: QListWidgetItem):
        """Show detail for a clicked recent knowledge entry."""
        idx = self._recent_list.row(item)
        if not 0 <= idx < len(self._recent_cache):
            return
        
        entry = self._recent_cache[idx]
        data = {"topic": str(entry)} if not hasattr(entry, "to_dict") else (entry.to_dict() if isinstance(entry, dict) else {"topic": str(entry)})
        html = self._build_knowledge_html(data)
        self._detail_view.setHtml(html)

    # ═══════════════════════════════════════════════════════════════════════════
    # HTML BUILDERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_curiosity_html(self, topic: dict) -> str:
        """Build rich HTML for a curiosity topic detail view."""
        urgency = topic.get("urgency", "MODERATE")
        urgency_color = URGENCY_COLORS.get(urgency, "#ffcc00")
        urgency_icon = URGENCY_ICONS.get(urgency, "◆")
    
        def get_status_badge():
            return f"<span style='background:#{'1a472a' if topic.get('researched') else urgency_color}; color:#{'#00ff88' if topic.get('researched') else urgency_color}; padding:3px 10px; border-radius:10px; font-size:11px;'>{'' if topic.get('researched') else f"{urgency_icon} {urgency}"}</span>"
    
        html = [
            f"<div style='font-family: \"Segoe UI\", sans-serif;'>",
            f"    <div style='margin-bottom: 12px;'>",
            f"        <h2 style='color:{colors.accent_purple}; margin: 0 0 6px 0; font-size: 18px;'>🔮 {topic.get('topic', 'Unknown')}</h2>",
            get_status_badge(),
            f"        <span style='color:{colors.text_secondary}; font-size:11px; margin-left:8px;'>Source: {topic.get('source', 'unknown')}</span>",
            "    </div>",
        ]
    
        if topic.get("question"):
            html.extend([
                f"    <div style='background:{colors.bg_medium}; padding:12px 14px; border-radius:8px; margin:10px 0; border-left: 3px solid {colors.accent_cyan};'>",
                f"        <div style='color:{colors.accent_cyan}; font-size:11px; font-weight:bold; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;'>Question</div>",
                f"        <span style='color:{colors.text_primary}; font-size:14px; line-height:1.5;'>{topic.get('question')}</span>",
                "    </div>",
            ])
    
        if topic.get("reason"):
            html.extend([
                f"    <div style='background:{colors.bg_medium}; padding:12px 14px; border-radius:8px; margin:10px 0; border-left: 3px solid {colors.accent_purple};'>",
                f"        <div style='color:{colors.accent_purple}; font-size:11px; font-weight:bold; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;'>Why Curious</div>",
                f"        <span style='color:{colors.text_primary}; font-size:13px;'>{topic.get('reason')}</span>",
                "    </div>",
            ])
    
        if topic.get("related_topics"):
            tags_html = " ".join(
                f"<span style='background:{colors.bg_dark}; color:{colors.accent_cyan}; padding:3px 10px; border-radius:12px; font-size:11px; display:inline-block; margin:2px;'>{r}</span>"
                for r in topic.get("related_topics")
            )
            html.extend([
                f"    <div style='margin: 12px 0;'>",
                f"        <div style='color:{colors.text_secondary}; font-size:11px; font-weight:bold; text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;'>Related Topics</div>",
                tags_html,
                "    </div>",
            ])
    
        if topic.get("search_queries"):
            queries_html = "".join(
                f"<div style='color:{colors.text_primary}; font-size:12px; padding:4px 0;'>🔎 {q}</div>"
                for q in topic.get("search_queries")
            )
            html.extend([
                f"    <div style='background:{colors.bg_medium}; padding:10px 14px; border-radius:8px; margin:10px 0;'>",
                f"        <div style='color:{colors.text_secondary}; font-size:11px; font-weight:bold; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;'>Search Queries</div>",
                queries_html,
                "    </div>",
            ])
    
        if topic.get("created_at"):
            html.extend([
                f"    <div style='color:{colors.text_secondary}; font-size:11px; margin-top:16px; padding-top:8px; border-top:1px solid {colors.border_subtle};'>",
                f"        Created: {topic.get('created_at')}",
                "    </div>",
            ])
    
        html.append("</div>")
        return "".join(html)

    def _build_knowledge_html(self, data: dict) -> str:
        """Build rich HTML for a knowledge entry detail view."""
        topic = data.get("topic", "Unknown")
        title = data.get("title", "") or topic
        content = data.get("content", "")
        summary = data.get("summary", "")
        source = data.get("source", "unknown")
        source_url = data.get("source_url", "")
        importance = data.get("importance", 0.5)
        confidence = data.get("confidence", 0.5)
        tags = data.get("tags", [])
        created = data.get("created_at", "")
        access_count = data.get("access_count", 0)
    
        imp_pct = int(importance * 100)
        conf_pct = int(confidence * 100)
    
        source_icon = SOURCE_ICONS.get(source, "📄")
        source_color = SOURCE_COLORS.get(source, colors.text_primary)
    
        html = f"""
        <div style="font-family: 'Segoe UI', sans-serif;">
            <div style="margin-bottom: 12px;">
                <h2 style="color:{source_color}; margin: 0 0 6px 0; font-size: 18px;">
                    {source_icon} {title}
                </h2>
                <span style="background:{source_color}22; color:{source_color}; padding:3px 10px;
                             border-radius:10px; font-size:11px;">
                    {source.upper()}
                </span>
                {"<a href='" + source_url + "' style='color:" + colors.accent_cyan + "; font-size:11px; margin-left:8px; text-decoration:none;'>🔗 Open Link</a>" if source_url else ""}
            </div>
    
            <!-- Metrics Row -->
            <div style="display:flex; gap:16px; margin:10px 0;">
                <div style="flex:1;">
                    <div style="color:{colors.text_secondary}; font-size:10px; text-transform:uppercase;
                                 letter-spacing:1px;">Importance</div>
                    <div style="background:{colors.bg_dark}; border-radius:4px; height:6px; margin-top:4px;">
                        <div style="background:{'green' if importance >= 0.7 else 'cyan' if importance >= 0.4 else colors.text_secondary}; width:{imp_pct}%%; height:100%;
                                   border-radius:4px;"></div>
                    </div>
                    <span style="color:{'green' if importance >= 0.7 else 'cyan' if importance >= 0.4 else colors.text_secondary}; font-size:12px; font-weight:bold;">{imp_pct}%</span>
                </div>
                <div style="flex:1;">
                    <div style="color:{colors.text_secondary}; font-size:10px; text-transform:uppercase;
                                 letter-spacing:1px;">Confidence</div>
                    <div style="background:{colors.bg_dark}; border-radius:4px; height:6px; margin-top:4px;">
                        <div style="background:{'green' if confidence >= 0.7 else 'orange' if confidence >= 0.4 else colors.text_secondary}; width:{conf_pct}%%; height:100%;
                                   border-radius:4px;"></div>
                    </div>
                    <span style="color:{'green' if confidence >= 0.7 else 'orange' if confidence >= 0.4 else colors.text_secondary}; font-size:12px; font-weight:bold;">{conf_pct}%</span>
                </div>
                <div>
                    <div style="color:{colors.text_secondary}; font-size:10px; text-transform:uppercase;
                                 letter-spacing:1px;">Accessed</div>
                    <span style="color:{colors.text_primary}; font-size:16px; font-weight:bold;">
                        {access_count}×
                    </span>
                </div>
            </div>
        """
        if summary:
            html += f"""
            <div style="background:{colors.bg_medium}; padding:12px 14px; border-radius:8px;
                         margin:10px 0; border-left: 3px solid {colors.accent_green};">
                <div style="color:{colors.accent_green}; font-size:11px; font-weight:bold;
                             text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;">
                    Summary
                </div>
                <span style="color:{colors.text_primary}; font-size:13px; line-height:1.6;">
                    {summary}
                </span>
            </div>
            """
        if content:
            display_content = content[:2000] + "..." if len(content) > 2000 else content
            display_content = (display_content
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br>")
            )
            html += f"""
            <div style="background:{colors.bg_medium}; padding:12px 14px; border-radius:8px;
                         margin:10px 0;">
                <div style="color:{colors.text_secondary}; font-size:11px; font-weight:bold;
                             text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">
                    Content
                </div>
                <div style="color:{colors.text_primary}; font-size:12px; line-height:1.6;
                             max-height:300px; overflow-y:auto;">
                    {display_content}
                </div>
            </div>
            """
        if tags:
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except Exception:
                    tags = [tags]
            tags_html = " ".join(
                f"<span style='background:{colors.bg_dark}; color:{colors.accent_purple}; "
                f"padding:3px 10px; border-radius:12px; font-size:11px; "
                f"display:inline-block; margin:2px;'>{t}</span>"
                for t in tags
            )
            html += f"""
            <div style="margin: 12px 0;">
                <div style="color:{colors.text_secondary}; font-size:11px; font-weight:bold;
                             text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">
                    Tags
                </div>
                {tags_html}
            </div>
            """
        if created:
            html += f"""
            <div style="color:{colors.text_secondary}; font-size:11px; margin-top:16px;
                         padding-top:8px; border-top:1px solid {colors.border_subtle};">
                📅 Created: {created} &nbsp;|&nbsp; 🏷️ Topic: {topic}
            </div>
            """
        html += "</div>"
        return html

    def _build_search_results_html(self, query: str, results: list) -> str:
        """Build HTML for search results."""
        html = f"""
        <div style='font-family: "Segoe UI", sans-serif;'>
            <h2 style='color:{colors.accent_cyan}; margin:0 0 4px 0; font-size:18px;'>
                🔍 Results for '{query}'
            </h2>
            <p style='color:{colors.text_secondary}; font-size: 12px; margin:0 0 12px 0;'>
                Found {len(results)} result{"s" if len(results) != 1 else ""}
            </p>
        """

        for i, r in enumerate(results):
            title = r.get("title", "") or r.get("topic", "Untitled")
            source = r.get("source", "unknown")
            source_icon = SOURCE_ICONS.get(source, "📄")
            source_color = SOURCE_COLORS.get(source, colors.text_primary)
            importance = r.get("importance", 0.5)
            summary = r.get("summary", "")
            content = r.get("content", "")

            preview = summary or (content[:200] + "..." if len(content) > 200 else content)
            preview = (preview
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", " ")
            )

            imp_pct = int(importance * 100)
            imp_color = "#00ff88" if importance >= 0.7 else colors.accent_cyan

            html += f"""
            <div style='margin:8px 0; padding:12px 14px; background:{colors.bg_medium};
                        border-radius:8px; border-left:3px solid {source_color};'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <b style='color:{source_color}; font-size:14px;'>
                        {source_icon} {title}
                    </b>
                    <span style='color:{imp_color}; font-size:11px; font-weight:bold;'>
                        ⬆ {imp_pct}%
                    </span>
                </div>
                <div style='color:{colors.text_primary}; font-size:12px; margin-top:6px;
                            line-height:1.5;'>
                    {preview}
                </div>
            </div>
            """

        html += "</div>"
        return html

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS — Safe access to brain subsystems
    # ═══════════════════════════════════════════════════════════════════════════

    def _get_learning_system(self):
        """Safely get the LearningSystem from the brain."""
        if not self._brain:
            return None
        if hasattr(self._brain, '_learning_system') and self._brain._learning_system:
            return self._brain._learning_system
        if hasattr(self._brain, '_load_learning'):
            try:
                self._brain._load_learning()
            except Exception as e:
                logger.debug(f"Could not load learning system: {e}")
        return getattr(self._brain, '_learning_system', None)

    def _get_knowledge_base(self):
        """Safely get the KnowledgeBase from the brain."""
        if not self._brain:
            return None
        kb = getattr(self._brain, '_knowledge_base_l', None)
        if kb:
            return kb
        ls = self._get_learning_system()
        if ls and hasattr(ls, 'knowledge_base'):
            return ls.knowledge_base
        return None

    def _get_curiosity_engine(self):
        """Safely get the CuriosityEngine from the brain."""
        if not self._brain:
            return None
        ce = getattr(self._brain, '_curiosity_engine_l', None)
        if ce:
            return ce
        ls = self._get_learning_system()
        if ls and hasattr(ls, 'curiosity_engine'):
            return ls.curiosity_engine
        return None