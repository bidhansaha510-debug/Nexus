"""
NEXUS AI - Abilities Panel
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Real-time view of all registered abilities, grouped by category,
with live activity status, invocation history, and invoke controls.

Layout:
  ┌─────────────────────────────────────────────────────────────────┐
  │  ⚡ Abilities                                                    │
  │  ──────────────────────────────────────────────────── pink       │
  │                                                                  │
  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
  │  │  Total   │ │ Invoked  │ │ Success  │ │ Cooldown │           │
  │  │   28     │ │    142   │ │   96%    │ │    2     │           │
  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
  │                                                                  │
  │  ▼ 📂 Abilities by Category                                     │
  │  ┌──────────────────────────────────────────────────────────┐   │
  │  │  🧬 Self Evolution (3)  │  📚 Learning (2)  │  ...      │   │
  │  │    evolve_feature   0   │    learn_about  5  │           │   │
  │  │    get_evo_status   3   │    get_knowledge 2 │           │   │
  │  └──────────────────────────────────────────────────────────┘   │
  │                                                                  │
  │  ▼ 🔴 Live System Activity                                      │
  │  ┌──────────────────────────────────────────────────────────┐   │
  │  │  Emotion Engine    : 😊 Joy (0.7)                        │   │
  │  │  Cognitive Router  : 50 engines ready                    │   │
  │  │  Self-Evolution    : Researching features...             │   │
  │  │  Memory System     : 142 memories stored                 │   │
  │  │  Last Ability Used : remember (2m ago)                   │   │
  │  └──────────────────────────────────────────────────────────┘   │
  │                                                                  │
  │  ▼ 📋 Invocation History                                        │
  │  ┌──────────────────────────────────────────────────────────┐   │
  │  │  Name       Success  Time     Timestamp                  │   │
  │  │  remember   ✅       0.02s   14:32:01                    │   │
  │  │  feel       ✅       0.01s   14:30:45                    │   │
  │  └──────────────────────────────────────────────────────────┘   │
  └─────────────────────────────────────────────────────────────────┘
"""

import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QGridLayout, QScrollArea, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ui.theme import theme, colors, fonts, spacing, icons
from ui.widgets import HeaderLabel, Section, StatCard, TagLabel


# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORY METADATA
# ═══════════════════════════════════════════════════════════════════════════════

CATEGORY_META = {
    "self_evolution":  {"icon": "🧬", "color": colors.accent_pink,   "label": "Self Evolution"},
    "learning":        {"icon": "📚", "color": "#3b82f6",            "label": "Learning"},
    "research":        {"icon": "🔬", "color": "#f59e0b",            "label": "Research"},
    "cognition":       {"icon": "🧠", "color": colors.accent_purple, "label": "Cognition"},
    "memory":          {"icon": "💾", "color": "#06b6d4",            "label": "Memory"},
    "body":            {"icon": "🖥️", "color": "#6366f1",            "label": "Body"},
    "emotion":         {"icon": "💫", "color": "#f43f5e",            "label": "Emotion"},
    "personality":     {"icon": "🎭", "color": "#f97316",            "label": "Personality"},
    "consciousness":   {"icon": "✨", "color": "#8b5cf6",            "label": "Consciousness"},
    "system":          {"icon": "⚙️", "color": colors.accent_cyan,   "label": "System"},
    "communication":   {"icon": "💬", "color": colors.accent_green,  "label": "Communication"},
    "monitoring":      {"icon": "📡", "color": "#14b8a6",            "label": "Monitoring"},
}

RISK_COLORS = {
    "safe":     colors.accent_green,
    "low":      colors.accent_cyan,
    "moderate": "#f59e0b",
    "high":     colors.danger,
    "critical": "#ff0000",
}


# ═══════════════════════════════════════════════════════════════════════════════
# ABILITY CARD WIDGET
# ═══════════════════════════════════════════════════════════════════════════════

class AbilityCard(QFrame):
    """Single ability display card with name, description, risk badge, invoke button."""

    def __init__(self, ability_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self._data = ability_data
        self.setStyleSheet(
            f"AbilityCard {{ background: {colors.bg_surface}; "
            f"border: 1px solid {colors.border_subtle}; "
            f"border-radius: 8px; padding: 10px; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Top row: name + risk
        top = QHBoxLayout()
        name = ability_data.get("name", "unknown")
        name_label = QLabel(name)
        name_label.setFont(QFont(fonts.family_primary, fonts.size_sm))
        name_label.setStyleSheet(f"color: {colors.text_primary}; font-weight: 600;")
        top.addWidget(name_label)

        top.addStretch()

        risk = ability_data.get("risk", "safe").lower()
        risk_color = RISK_COLORS.get(risk, colors.text_muted)
        risk_label = QLabel(risk.upper())
        risk_label.setFont(QFont(fonts.family_mono, 8))
        risk_label.setStyleSheet(
            f"color: {risk_color}; background: rgba(255,255,255,0.05); "
            f"padding: 2px 6px; border-radius: 4px; font-weight: bold;"
        )
        top.addWidget(risk_label)
        layout.addLayout(top)

        # Description
        desc = ability_data.get("description", "")
        if desc:
            desc_label = QLabel(desc[:80] + ("..." if len(desc) > 80 else ""))
            desc_label.setFont(QFont(fonts.family_primary, 9))
            desc_label.setStyleSheet(f"color: {colors.text_muted};")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)

        # Bottom row: invoke count + cooldown
        bottom = QHBoxLayout()
        invoke_count = ability_data.get("invoke_count", 0)
        count_label = QLabel(f"⚡ {invoke_count} uses")
        count_label.setFont(QFont(fonts.family_mono, 9))
        count_label.setStyleSheet(f"color: {colors.text_secondary};")
        bottom.addWidget(count_label)

        cd = ability_data.get("cooldown_seconds", 0)
        if cd > 0:
            cd_label = QLabel(f"⏱ {cd}s CD")
            cd_label.setFont(QFont(fonts.family_mono, 9))
            cd_label.setStyleSheet(f"color: {colors.text_muted};")
            bottom.addWidget(cd_label)

        bottom.addStretch()
        layout.addLayout(bottom)


# ═══════════════════════════════════════════════════════════════════════════════
# ABILITIES PANEL
# ═══════════════════════════════════════════════════════════════════════════════

class AbilitiesPanel(QFrame):
    """
    Comprehensive Abilities dashboard showing all registered abilities
    grouped by category, with live system activity and invocation history.
    """

    def __init__(self, brain=None, parent=None):
        super().__init__(parent)
        self._brain = brain
        self._abilities_data: List[Dict] = []
        self._stats_data: Dict = {}
        self._history_data: List[Dict] = []
        self.setStyleSheet(f"background-color: {colors.bg_dark};")

        self._build_ui()

        # Refresh timer (5s)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_data)
        self._timer.start(5000)

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
        layout.addWidget(HeaderLabel("Abilities", "⚡", colors.accent_pink))

        # ── Stats Row ──
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(8)
        self._stat_total = StatCard("⚡", "Total Abilities", "0", colors.accent_pink)
        self._stat_invocations = StatCard("📊", "Invocations", "0", colors.accent_cyan)
        self._stat_success = StatCard("✅", "Success Rate", "—", colors.accent_green)
        self._stat_cooldown = StatCard("⏱️", "On Cooldown", "0", "#f59e0b")
        for s in [self._stat_total, self._stat_invocations, self._stat_success, self._stat_cooldown]:
            stats_layout.addWidget(s)
        layout.addLayout(stats_layout)

        # ── Abilities by Category ──
        self._cat_section = Section("Abilities by Category", "📂", expanded=True)
        self._cat_layout = QVBoxLayout()
        self._cat_layout.setSpacing(8)

        # Placeholder
        self._cat_placeholder = QLabel("Loading abilities...")
        self._cat_placeholder.setStyleSheet(f"color: {colors.text_muted}; padding: 20px;")
        self._cat_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cat_layout.addWidget(self._cat_placeholder)

        self._cat_section.add_layout(self._cat_layout)
        layout.addWidget(self._cat_section)

        # ── Live System Activity ──
        self._activity_section = Section("Live System Activity", "🔴", expanded=True)
        self._activity_layout = QVBoxLayout()
        self._activity_layout.setSpacing(4)

        self._activity_labels: Dict[str, QLabel] = {}
        activity_items = [
            ("emotion",       "💫 Emotion Engine",      "Loading..."),
            ("cognition",     "🧠 Cognitive Router",     "Loading..."),
            ("evolution",     "🧬 Self-Evolution",       "Loading..."),
            ("memory",        "💾 Memory System",        "Loading..."),
            ("consciousness", "✨ Consciousness",        "Loading..."),
            ("body",          "🖥️ Computer Body",        "Loading..."),
            ("autonomy",      "🤖 Autonomy Engine",      "Loading..."),
            ("last_ability",  "⚡ Last Ability Used",    "None yet"),
        ]

        for key, label_text, default in activity_items:
            row = QHBoxLayout()
            row.setSpacing(12)

            name_lbl = QLabel(label_text)
            name_lbl.setFixedWidth(180)
            name_lbl.setFont(QFont(fonts.family_primary, fonts.size_sm))
            name_lbl.setStyleSheet(f"color: {colors.text_secondary}; font-weight: 600;")
            row.addWidget(name_lbl)

            val_lbl = QLabel(default)
            val_lbl.setFont(QFont(fonts.family_primary, fonts.size_sm))
            val_lbl.setStyleSheet(f"color: {colors.text_primary};")
            row.addWidget(val_lbl)
            row.addStretch()

            self._activity_labels[key] = val_lbl
            self._activity_layout.addLayout(row)

        self._activity_section.add_layout(self._activity_layout)
        layout.addWidget(self._activity_section)

        # ── Invocation History ──
        history_section = Section("Invocation History", "📋", expanded=False)
        hist_layout = QVBoxLayout()

        self._history_table = QTableWidget()
        self._history_table.setColumnCount(5)
        self._history_table.setHorizontalHeaderLabels(
            ["Ability", "Status", "Time", "Duration", "Message"]
        )
        self._history_table.setAlternatingRowColors(True)
        self._history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._history_table.verticalHeader().setVisible(False)
        self._history_table.setMinimumHeight(200)
        self._history_table.setStyleSheet(
            f"QTableWidget {{ background: {colors.bg_surface}; "
            f"border: 1px solid {colors.border_default}; "
            f"border-radius: 8px; font-size: 11px; "
            f"gridline-color: {colors.border_subtle}; }}"
            f"QTableWidget::item {{ padding: 4px 8px; }}"
            f"QHeaderView::section {{ background: {colors.bg_elevated}; "
            f"color: {colors.text_secondary}; border: none; "
            f"border-bottom: 1px solid {colors.border_default}; "
            f"padding: 6px 8px; font-weight: 600; font-size: 10px; }}"
        )

        header = self._history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._history_table.setColumnWidth(0, 140)
        self._history_table.setColumnWidth(1, 60)
        self._history_table.setColumnWidth(2, 80)
        self._history_table.setColumnWidth(3, 70)

        hist_layout.addWidget(self._history_table)
        history_section.add_layout(hist_layout)
        layout.addWidget(history_section)

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
        self._refresh_data()

    def on_shown(self):
        """Called when panel becomes visible."""
        self._refresh_data()

    # ═══════════════════════════════════════════════════════════════════════════
    # DATA REFRESH
    # ═══════════════════════════════════════════════════════════════════════════

    def _refresh_data(self):
        """Fetch abilities data from the registry and update the UI."""
        try:
            from core.ability_registry import ability_registry

            # Get all abilities
            abilities = []
            for name, ability in ability_registry.get_all_abilities().items():
                abilities.append({
                    "name": name,
                    "description": ability.description,
                    "category": ability.category.value,
                    "risk": ability.risk.value,
                    "parameters": ability.parameters,
                    "cooldown_seconds": ability.cooldown_seconds,
                    "invoke_count": ability.invoke_count,
                    "last_invoked": ability.last_invoked,
                })
            self._abilities_data = abilities

            # Get stats
            self._stats_data = ability_registry.get_stats()

            # Get history
            self._history_data = ability_registry.get_invocation_history(limit=20)

            # Update UI
            self._update_stat_cards()
            self._update_category_grid()
            self._update_activity()
            self._update_history_table()

        except Exception as e:
            self._cat_placeholder.setText(f"Error loading abilities: {e}")

    def _update_stat_cards(self):
        """Update the top stat cards."""
        total = len(self._abilities_data)
        self._stat_total.set_value(str(total))

        total_invocations = self._stats_data.get("total_invocations", 0)
        self._stat_invocations.set_value(str(total_invocations))

        # Success rate from history
        if self._history_data:
            successful = sum(1 for h in self._history_data if h.get("success"))
            rate = (successful / len(self._history_data)) * 100 if self._history_data else 0
            self._stat_success.set_value(f"{rate:.0f}%")
        else:
            self._stat_success.set_value("—")

        # Cooldown count
        cooldown_count = 0
        now = datetime.now()
        for a in self._abilities_data:
            last = a.get("last_invoked")
            cd = a.get("cooldown_seconds", 0)
            if last and cd > 0:
                if isinstance(last, str):
                    try:
                        last = datetime.fromisoformat(last)
                    except Exception:
                        continue
                if hasattr(last, 'timestamp'):
                    elapsed = (now - last).total_seconds()
                    if elapsed < cd:
                        cooldown_count += 1
        self._stat_cooldown.set_value(str(cooldown_count))

    def _update_category_grid(self):
        """Rebuild the category grid with ability cards."""
        # Clear existing
        while self._cat_layout.count():
            item = self._cat_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

        if not self._abilities_data:
            placeholder = QLabel("No abilities registered")
            placeholder.setStyleSheet(f"color: {colors.text_muted}; padding: 20px;")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._cat_layout.addWidget(placeholder)
            return

        # Group by category
        grouped: Dict[str, List[Dict]] = {}
        for a in self._abilities_data:
            cat = a.get("category", "system").lower()
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(a)

        # Build grid - 2 categories per row
        cats = list(grouped.keys())
        for i in range(0, len(cats), 2):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(12)

            for j in range(2):
                idx = i + j
                if idx >= len(cats):
                    row_layout.addStretch()
                    continue

                cat = cats[idx]
                abilities = grouped[cat]
                meta = CATEGORY_META.get(cat, {"icon": "⚡", "color": colors.text_muted, "label": cat.replace("_", " ").title()})

                # Category card frame
                card = QFrame()
                card.setStyleSheet(
                    f"QFrame {{ background: {colors.bg_surface}; "
                    f"border: 1px solid {colors.border_subtle}; "
                    f"border-radius: 10px; border-top: 3px solid {meta['color']}; }}"
                )
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(12, 10, 12, 10)
                card_layout.setSpacing(6)

                # Category header
                cat_header = QLabel(f"{meta['icon']} {meta['label']} ({len(abilities)})")
                cat_header.setFont(QFont(fonts.family_primary, fonts.size_sm))
                cat_header.setStyleSheet(
                    f"color: {meta['color']}; font-weight: 700; "
                    f"letter-spacing: 0.5px;"
                )
                card_layout.addWidget(cat_header)

                # Ability list inside category
                for ability in abilities:
                    ability_row = QHBoxLayout()
                    ability_row.setSpacing(8)

                    a_name = QLabel(ability["name"])
                    a_name.setFont(QFont(fonts.family_mono, 10))
                    a_name.setStyleSheet(f"color: {colors.text_primary};")
                    ability_row.addWidget(a_name)

                    ability_row.addStretch()

                    # Risk badge
                    risk = ability.get("risk", "safe").lower()
                    risk_color = RISK_COLORS.get(risk, colors.text_muted)
                    risk_lbl = QLabel(risk[0].upper())
                    risk_lbl.setFixedWidth(18)
                    risk_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    risk_lbl.setFont(QFont(fonts.family_mono, 8))
                    risk_lbl.setStyleSheet(
                        f"color: {risk_color}; font-weight: bold;"
                    )
                    risk_lbl.setToolTip(f"Risk: {risk}")
                    ability_row.addWidget(risk_lbl)

                    # Invoke count
                    count = ability.get("invoke_count", 0)
                    count_lbl = QLabel(str(count))
                    count_lbl.setFixedWidth(30)
                    count_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    count_lbl.setFont(QFont(fonts.family_mono, 10))
                    count_lbl.setStyleSheet(
                        f"color: {colors.accent_cyan if count > 0 else colors.text_disabled}; "
                        f"font-weight: bold;"
                    )
                    count_lbl.setToolTip(f"{count} invocations")
                    ability_row.addWidget(count_lbl)

                    card_layout.addLayout(ability_row)

                row_layout.addWidget(card, 1)

            self._cat_layout.addLayout(row_layout)

    def _update_activity(self):
        """Update live system activity from brain stats."""
        if not self._brain:
            return

        try:
            stats = self._brain.get_stats()

            # Emotion
            emo = stats.get("emotion", {})
            primary = emo.get("primary", "neutral")
            intensity = emo.get("intensity", 0.0)
            self._activity_labels["emotion"].setText(
                f"{primary.capitalize()} ({intensity:.1f})"
            )
            self._activity_labels["emotion"].setStyleSheet(
                f"color: {colors.get_emotion_color(primary)};"
            )

            # Cognition
            thoughts = stats.get("thoughts_processed", 0)
            self._activity_labels["cognition"].setText(
                f"{thoughts} thoughts processed"
            )

            # Evolution
            evo = stats.get("evolution", {})
            if isinstance(evo, dict):
                gen = evo.get("generation", 0)
                features = evo.get("features_added", 0)
                self._activity_labels["evolution"].setText(
                    f"Gen {gen} — {features} features added"
                )
            else:
                self._activity_labels["evolution"].setText("Active")

            # Memory
            mem = stats.get("memory", {})
            if isinstance(mem, dict):
                count = mem.get("total_memories", mem.get("count", 0))
                self._activity_labels["memory"].setText(f"{count} memories stored")
            else:
                self._activity_labels["memory"].setText("Active")

            # Consciousness
            c_level = stats.get("consciousness_level", "AWARE")
            self._activity_labels["consciousness"].setText(c_level)
            self._activity_labels["consciousness"].setStyleSheet(
                f"color: {colors.get_consciousness_color(c_level)}; font-weight: bold;"
            )

            # Body
            body = stats.get("body", {})
            if isinstance(body, dict):
                cpu = body.get("cpu_usage", 0)
                ram = body.get("memory_usage", 0)
                self._activity_labels["body"].setText(
                    f"CPU {cpu:.0f}% │ RAM {ram:.0f}%"
                )


            # Autonomy
            if hasattr(self._brain, '_autonomy_engine') and self._brain._autonomy_engine:
                self._activity_labels["autonomy"].setText("🟢 Active")
                self._activity_labels["autonomy"].setStyleSheet(
                    f"color: {colors.accent_green};"
                )
            else:
                self._activity_labels["autonomy"].setText("⚫ Not loaded")
                self._activity_labels["autonomy"].setStyleSheet(
                    f"color: {colors.text_disabled};"
                )

            # Last ability used
            if self._history_data:
                last = self._history_data[-1]
                name = last.get("name", "?")
                ts = last.get("timestamp", "")
                ago = ""
                if ts:
                    try:
                        dt = datetime.fromisoformat(ts)
                        elapsed = (datetime.now() - dt).total_seconds()
                        if elapsed < 60:
                            ago = f" ({elapsed:.0f}s ago)"
                        elif elapsed < 3600:
                            ago = f" ({elapsed/60:.0f}m ago)"
                        else:
                            ago = f" ({elapsed/3600:.1f}h ago)"
                    except Exception:
                        pass
                success = "✅" if last.get("success") else "❌"
                self._activity_labels["last_ability"].setText(
                    f"{success} {name}{ago}"
                )

        except Exception:
            pass

    def _update_history_table(self):
        """Update the invocation history table."""
        if not self._history_data:
            self._history_table.setRowCount(0)
            return

        # Show newest first
        history = list(reversed(self._history_data))
        self._history_table.setRowCount(len(history))

        for row, record in enumerate(history):
            name_item = QTableWidgetItem(record.get("name", "?"))
            success = record.get("success", False)
            status_item = QTableWidgetItem("✅" if success else "❌")
            status_item.setForeground(
                QColor(colors.accent_green) if success else QColor(colors.danger)
            )

            ts = record.get("timestamp", "")
            time_str = ""
            if ts:
                try:
                    dt = datetime.fromisoformat(ts)
                    time_str = dt.strftime("%H:%M:%S")
                except Exception:
                    time_str = ts[:8] if len(ts) >= 8 else ts
            time_item = QTableWidgetItem(time_str)

            exec_time = record.get("execution_time", 0)
            duration_item = QTableWidgetItem(f"{exec_time:.2f}s" if exec_time else "—")

            message = record.get("message", record.get("error", ""))
            msg_item = QTableWidgetItem(str(message)[:60] if message else "—")

            for col, item in enumerate([name_item, status_item, time_item, duration_item, msg_item]):
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter if col < 4
                    else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
                )
                self._history_table.setItem(row, col, item)

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _clear_layout(layout):
        """Recursively clear a layout."""
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                AbilitiesPanel._clear_layout(item.layout())
