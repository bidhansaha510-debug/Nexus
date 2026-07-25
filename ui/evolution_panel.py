"""
NEXUS AI - Evolution Panel
═══════════════════════════════════════════════════════════════════════════════
Self-improvement and evolution monitoring dashboard.

Layout:
  ┌─────────────────────────────────────────────────────────────────┐
  │  🧬 Evolution                        [💡 Submit Idea] [🔄]    │
  ├──────────┬──────────┬──────────┬──────────┬────────────────────┤
  │ Evolved  │Proposals │ Success  │  Lines   │  Research          │
  │   3      │   12     │  75%     │  +847    │  Cycles: 5         │
  ├──────────┴──────────┴──────────┴──────────┴────────────────────┤
  │                                                                 │
  │  ┌── Current Evolution ────────────────────────────────────┐   │
  │  │  🔄 Currently evolving: "Add voice command parser"      │   │
  │  │  Status: WRITING_CODE  ████████░░░░  Step 4/7           │   │
  │  └─────────────────────────────────────────────────────────┘   │
  │                                                                 │
  │  ┌── Feature Proposals ────────────────────────────────────┐   │
  │  │  [Filter: All ▼]  [Sort: Priority ▼]  [Search... 🔍]   │   │
  │  │                                                          │   │
  │  │  ✅ [0.82] Voice Command Parser    intelligence  approved│   │
  │  │  📊 [0.71] Sentiment Dashboard     ui          evaluated│   │
  │  │  📝 [0.65] Email Integration       utility     proposed │   │
  │  │  🎉 [0.58] Screenshot Analyzer     monitoring  completed│   │
  │  │  ❌ [0.23] Quantum Simulator       intelligence rejected│   │
  │  └─────────────────────────────────────────────────────────┘   │
  │                                                                 │
  │  ┌── Evolution History ───────┐  ┌── Code Health ──────────┐  │
  │  │  ✅ Voice Parser  (12.3s)  │  │  Files: 47  Lines: 12k  │  │
  │  │  ❌ DB Manager    (8.1s)   │  │  Errors: 0  Fixed: 3    │  │
  │  │  ✅ Log Rotator   (5.4s)   │  │  Health: ████████░░ 92% │  │
  │  └────────────────────────────┘  └──────────────────────────┘  │
  │                                                                 │
  │  ┌── Research Activity ────────────────────────────────────┐   │
  │  │  Cycles: 5  │  Topics: 23  │  Last: LLM brainstorm     │   │
  │  │  [Research sparkline ~~~~~~~~~~~~~~~]                    │   │
  │  └─────────────────────────────────────────────────────────┘   │
  └─────────────────────────────────────────────────────────────────┘
═══════════════════════════════════════════════════════════════════════════════
"""

import sys
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QScrollArea, QGridLayout, QSizePolicy,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QLineEdit, QTextBrowser, QAbstractItemView,
    QInputDialog, QMessageBox, QSplitter,
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, Slot, QSize,
)
from PySide6.QtGui import (
    QFont, QColor, QBrush, QIcon,
)

from ui.theme import theme, colors, fonts, spacing, animations, icons, NexusColors
from ui.widgets import (
    StatCard, HeaderLabel, Separator, Section, KeyValueRow,
    GlowCard, MiniChart, PulsingDot, TagLabel,
)
from utils.logger import get_logger

logger = get_logger("evolution_panel")

# ═══════════════════════════════════════════════════════════════════════════════
# EVOLUTION PROGRESS WIDGET — Shows current evolution pipeline status
# ═══════════════════════════════════════════════════════════════════════════════

class EvolutionProgressWidget(GlowCard):
    """
    Animated progress display for a currently running evolution.
    Shows the 7-step pipeline with progress indication.
    """

    PIPELINE_STEPS = [
        ("📋", "Plan"),
        ("💾", "Backup"),
        ("📦", "Deps"),
        ("✏️", "Write"),
        ("🔧", "Modify"),
        ("🔍", "Validate"),
        ("🧪", "Test"),
    ]

    STATUS_TO_STEP = {
        "idle": -1,
        "planning": 0,
        "backing_up": 1,
        "installing_deps": 2,
        "writing_code": 3,
        "modifying_code": 4,
        "validating": 5,
        "testing": 6,
        "integrating": 6,
        "completed": 7,
        "failed": -2,
        "rolling_back": -3,
    }

    def __init__(self, parent=None):
        super().__init__(glow_color=colors.accent_cyan, parent=parent)
        self._current_step = -1
        self._proposal_name = ""
        self._status = "idle"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Header row
        header = QHBoxLayout()
        header.setSpacing(8)

        self._dot = PulsingDot(colors.accent_cyan, 8)
        header.addWidget(self._dot)

        self._title = QLabel("No Evolution Running")
        title_font = QFont(fonts.family_primary, fonts.size_md)
        title_font.setBold(True)
        self._title.setFont(title_font)
        self._title.setStyleSheet(
            f"color: {colors.text_primary}; background: transparent;"
        )
        header.addWidget(self._title)
        header.addStretch()

        self._status_tag = TagLabel("IDLE", colors.text_muted)
        header.addWidget(self._status_tag)

        layout.addLayout(header)

        # Proposal name
        self._name_label = QLabel("")
        self._name_label.setFont(QFont(fonts.family_primary, fonts.size_sm))
        self._name_label.setStyleSheet(
            f"color: {colors.text_secondary}; background: transparent;"
        )
        self._name_label.setWordWrap(True)
        layout.addWidget(self._name_label)

        # Pipeline steps
        self._steps_layout = QHBoxLayout()
        self._steps_layout.setSpacing(4)
        self._step_labels: List[QLabel] = []

        for i, (icon, name) in enumerate(self.PIPELINE_STEPS):
            step_frame = QFrame()
            step_frame.setFixedHeight(50)
            step_frame.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
            step_layout = QVBoxLayout(step_frame)
            step_layout.setContentsMargins(4, 4, 4, 4)
            step_layout.setSpacing(2)
            step_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            icon_label = QLabel(icon)
            icon_label.setFont(QFont(fonts.family_primary, 14))
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label.setStyleSheet("background: transparent;")
            step_layout.addWidget(icon_label)

            name_label = QLabel(name)
            name_label.setFont(QFont(fonts.family_primary, fonts.size_xs - 1))
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_label.setStyleSheet(
                f"color: {colors.text_disabled}; background: transparent;"
            )
            step_layout.addWidget(name_label)

            step_frame.setStyleSheet(
                f"QFrame {{ "
                f"background-color: {colors.bg_medium}; "
                f"border: 1px solid {colors.border_subtle}; "
                f"border-radius: 6px; "
                f"}}"
            )

            self._steps_layout.addWidget(step_frame)
            self._step_labels.append((step_frame, name_label))

            # Arrow between steps
            if i < len(self.PIPELINE_STEPS) - 1:
                arrow = QLabel("▸")
                arrow.setFixedWidth(16)
                arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
                arrow.setStyleSheet(
                    f"color: {colors.text_disabled}; background: transparent;"
                )
                self._steps_layout.addWidget(arrow)

        layout.addLayout(self._steps_layout)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setRange(0, 7)
        self._progress.setValue(0)
        self._progress.setFixedHeight(6)
        self._progress.setTextVisible(False)
        layout.addWidget(self._progress)

        self.set_idle()

    def set_evolution(self, name: str, status: str):
        """Set current evolution state"""
        self._proposal_name = name
        self._status = status.lower()

        step = self.STATUS_TO_STEP.get(self._status, -1)
        self._current_step = step

        if step == -1:
            self.set_idle()
            return

        if step == -2:  # Failed
            self._title.setText("🔴 Evolution Failed")
            self._name_label.setText(name)
            self._status_tag = self._replace_tag(
                self._status_tag, "FAILED", colors.danger
            )
            self._dot.set_color(colors.danger)
            self._dot.set_active(True)
            self.set_glow_color(colors.danger)
            self._progress.setValue(0)
            return

        if step == -3:  # Rolling back
            self._title.setText("⏪ Rolling Back")
            self._name_label.setText(name)
            self._status_tag = self._replace_tag(
                self._status_tag, "ROLLBACK", colors.warning
            )
            self._dot.set_color(colors.warning)
            self._dot.set_active(True)
            self.set_glow_color(colors.warning)
            return

        if step >= 7:  # Completed
            self._title.setText("✅ Evolution Complete!")
            self._name_label.setText(name)
            self._status_tag = self._replace_tag(
                self._status_tag, "COMPLETE", colors.accent_green
            )
            self._dot.set_color(colors.accent_green)
            self._dot.set_active(True)
            self.set_glow_color(colors.accent_green)
            self._progress.setValue(7)
            self._highlight_all_steps()
            return

        # Active evolution
        self._title.setText("🔄 Evolving...")
        self._name_label.setText(f"Feature: {name}")
        status_upper = status.upper().replace("_", " ")
        self._status_tag = self._replace_tag(
            self._status_tag, status_upper, colors.accent_cyan
        )
        self._dot.set_color(colors.accent_cyan)
        self._dot.set_active(True)
        self.set_glow_color(colors.accent_cyan)
        self._progress.setValue(step + 1)
        self._highlight_steps(step)

    def set_idle(self):
        """Set to idle state"""
        self._title.setText("No Evolution Running")
        self._name_label.setText("Waiting for approved proposals...")
        self._status_tag = self._replace_tag(
            self._status_tag, "IDLE", colors.text_muted
        )
        self._dot.set_color(colors.text_muted)
        self._dot.set_active(False)
        self.set_glow_color(colors.border_default)
        self._progress.setValue(0)
        self._reset_steps()

    def _highlight_steps(self, current: int):
        """Highlight completed and current steps"""
        for i, (frame, label) in enumerate(self._step_labels):
            if i < current:
                # Completed
                frame.setStyleSheet(
                    f"QFrame {{ "
                    f"background-color: {NexusColors.hex_to_rgba(colors.accent_green, 0.15)}; "
                    f"border: 1px solid {colors.accent_green}; "
                    f"border-radius: 6px; "
                    f"}}"
                )
                label.setStyleSheet(
                    f"color: {colors.accent_green}; background: transparent;"
                )
            elif i == current:
                # Active
                frame.setStyleSheet(
                    f"QFrame {{ "
                    f"background-color: {NexusColors.hex_to_rgba(colors.accent_cyan, 0.2)}; "
                    f"border: 1px solid {colors.accent_cyan}; "
                    f"border-radius: 6px; "
                    f"}}"
                )
                label.setStyleSheet(
                    f"color: {colors.accent_cyan}; background: transparent; "
                    f"font-weight: bold;"
                )
            else:
                # Pending
                frame.setStyleSheet(
                    f"QFrame {{ "
                    f"background-color: {colors.bg_medium}; "
                    f"border: 1px solid {colors.border_subtle}; "
                    f"border-radius: 6px; "
                    f"}}"
                )
                label.setStyleSheet(
                    f"color: {colors.text_disabled}; background: transparent;"
                )

    def _highlight_all_steps(self):
        for frame, label in self._step_labels:
            frame.setStyleSheet(
                f"QFrame {{ "
                f"background-color: {NexusColors.hex_to_rgba(colors.accent_green, 0.15)}; "
                f"border: 1px solid {colors.accent_green}; "
                f"border-radius: 6px; "
                f"}}"
            )
            label.setStyleSheet(
                f"color: {colors.accent_green}; background: transparent;"
            )

    def _reset_steps(self):
        for frame, label in self._step_labels:
            frame.setStyleSheet(
                f"QFrame {{ "
                f"background-color: {colors.bg_medium}; "
                f"border: 1px solid {colors.border_subtle}; "
                f"border-radius: 6px; "
                f"}}"
            )
            label.setStyleSheet(
                f"color: {colors.text_disabled}; background: transparent;"
            )

    def _replace_tag(self, old_tag, text, color):
        """Replace tag label (since TagLabel style is set in __init__)"""
        parent_layout = old_tag.parent().layout() if old_tag.parent() else None
        new_tag = TagLabel(text, color)
        if parent_layout:
            # Find and replace in layout
            for i in range(parent_layout.count()):
                if parent_layout.itemAt(i).widget() == old_tag:
                    parent_layout.removeWidget(old_tag)
                    old_tag.deleteLater()
                    parent_layout.insertWidget(i, new_tag)
                    return new_tag
        return new_tag

# ═══════════════════════════════════════════════════════════════════════════════
# PROPOSAL TABLE — Browsable list of feature proposals
# ═══════════════════════════════════════════════════════════════════════════════

class ProposalTable(QFrame):
    """
    Table showing all feature proposals with filtering and sorting.
    """

    proposal_selected = Signal(dict)

    STATUS_ICONS = {
        "proposed": "📝",
        "researching": "🔍",
        "evaluated": "📊",
        "approved": "✅",
        "implementing": "🔨",
        "testing": "🧪",
        "completed": "🎉",
        "failed": "❌",
        "rejected": "🚫",
        "deferred": "⏸️",
    }

    STATUS_COLORS = {
        "proposed": colors.text_muted,
        "researching": colors.accent_blue,
        "evaluated": colors.accent_purple,
        "approved": colors.accent_green,
        "implementing": colors.accent_orange,
        "testing": colors.accent_yellow,
        "completed": colors.accent_green,
        "failed": colors.danger,
        "rejected": colors.text_disabled,
        "deferred": colors.text_muted,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"ProposalTable {{ "
            f"background-color: {colors.bg_surface}; "
            f"border: 1px solid {colors.border_default}; "
            f"border-radius: {spacing.border_radius}px; "
            f"}}"
        )

        self._all_proposals: List[dict] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # ── Header & Filters ──
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        title = QLabel("📋 Feature Proposals")
        title.setFont(QFont(fonts.family_primary, fonts.size_sm))
        title.setStyleSheet(
            f"color: {colors.accent_cyan}; background: transparent; "
            f"font-weight: bold;"
        )
        filter_row.addWidget(title)

        filter_row.addStretch()

        # Status filter
        self._status_filter = QComboBox()
        self._status_filter.addItem("All Statuses", "all")
        for status in [
            "proposed", "evaluated", "approved", "implementing",
            "completed", "failed", "rejected", "deferred",
        ]:
            icon = self.STATUS_ICONS.get(status, "")
            self._status_filter.addItem(f"{icon} {status.capitalize()}", status)
        self._status_filter.setFixedWidth(160)
        self._status_filter.setFixedHeight(30)
        self._status_filter.currentIndexChanged.connect(self._apply_filters)
        filter_row.addWidget(self._status_filter)

        # Category filter
        self._category_filter = QComboBox()
        self._category_filter.addItem("All Categories", "all")
        for cat in [
            "intelligence", "emotion", "consciousness", "personality",
            "monitoring", "learning", "ui", "body", "communication",
            "performance", "creativity", "social", "memory",
            "autonomy", "utility",
        ]:
            self._category_filter.addItem(cat.capitalize(), cat)
        self._category_filter.setFixedWidth(150)
        self._category_filter.setFixedHeight(30)
        self._category_filter.currentIndexChanged.connect(self._apply_filters)
        filter_row.addWidget(self._category_filter)

        # Search
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍 Search proposals...")
        self._search.setFixedWidth(200)
        self._search.setFixedHeight(30)
        self._search.textChanged.connect(self._apply_filters)
        filter_row.addWidget(self._search)

        layout.addLayout(filter_row)

        # ── Table ──
        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels([
            "Priority", "Name", "Category", "Status",
            "Feasibility", "Impact",
        ])
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setSortingEnabled(True)

        # Column widths
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)

        self._table.setColumnWidth(0, 70)
        self._table.setColumnWidth(2, 110)
        self._table.setColumnWidth(3, 110)
        self._table.setColumnWidth(4, 80)
        self._table.setColumnWidth(5, 80)

        self._table.itemSelectionChanged.connect(self._on_selection)

        layout.addWidget(self._table)

        # ── Detail area ──
        self._detail = QTextBrowser()
        self._detail.setMaximumHeight(100)
        self._detail.setStyleSheet(
            f"QTextBrowser {{ "
            f"background-color: {colors.bg_medium}; "
            f"color: {colors.text_secondary}; "
            f"border: 1px solid {colors.border_subtle}; "
            f"border-radius: 6px; "
            f"padding: 8px; "
            f"font-size: {fonts.size_xs}px; "
            f"}}"
        )
        self._detail.setPlaceholderText("Select a proposal to see details...")
        layout.addWidget(self._detail)

        # Count label
        self._count_label = QLabel("0 proposals")
        self._count_label.setFont(QFont(fonts.family_mono, fonts.size_xs))
        self._count_label.setStyleSheet(
            f"color: {colors.text_disabled}; background: transparent;"
        )
        layout.addWidget(self._count_label)

    def set_proposals(self, proposals: List[dict]):
        """Set the proposals data"""
        self._all_proposals = proposals
        self._apply_filters()

    def _apply_filters(self):
        """Apply status, category, and search filters"""
        status = self._status_filter.currentData()
        category = self._category_filter.currentData()
        search = self._search.text().lower().strip()

        filtered = []
        for p in self._all_proposals:
            # Status filter
            if status != "all" and p.get("status") != status:
                continue
            # Category filter
            if category != "all" and p.get("category") != category:
                continue
            # Search filter
            if search:
                name = p.get("name", "").lower()
                desc = p.get("description", "").lower()
                if search not in name and search not in desc:
                    continue
            filtered.append(p)

        self._populate_table(filtered)
        self._count_label.setText(
            f"{len(filtered)} of {len(self._all_proposals)} proposals"
        )

    def _populate_table(self, proposals: List[dict]):
        """Fill the table with proposal data"""
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(proposals))

        for row, p in enumerate(proposals):
            status = p.get("status", "proposed")
            priority = p.get("priority_score", 0)
            name = p.get("name", "Unnamed")
            category = p.get("category", "utility")
            feasibility = p.get("feasibility_score", 0)
            impact = p.get("impact_score", 0)

            status_icon = self.STATUS_ICONS.get(status, "❓")
            status_color = QColor(self.STATUS_COLORS.get(status, colors.text_muted))

            # Priority
            pri_item = QTableWidgetItem(f"{priority:.2f}")
            # FIX: Use setData instead of setTextAlignment
            pri_item.setData(Qt.ItemDataRole.TextAlignmentRole, Qt.AlignmentFlag.AlignCenter)
            pri_item.setData(Qt.ItemDataRole.UserRole, p)
            
            if priority >= 0.7:
                pri_item.setForeground(QBrush(QColor(colors.accent_green)))
            elif priority >= 0.4:
                pri_item.setForeground(QBrush(QColor(colors.accent_cyan)))
            else:
                pri_item.setForeground(QBrush(QColor(colors.text_muted)))
            self._table.setItem(row, 0, pri_item)

            # Name
            name_item = QTableWidgetItem(f"{status_icon} {name}")
            name_item.setForeground(QBrush(QColor(colors.text_primary)))
            self._table.setItem(row, 1, name_item)

            # Category
            cat_item = QTableWidgetItem(category.capitalize())
            # FIX: Use setData
            cat_item.setData(Qt.ItemDataRole.TextAlignmentRole, Qt.AlignmentFlag.AlignCenter)
            cat_item.setForeground(QBrush(QColor(colors.text_secondary)))
            self._table.setItem(row, 2, cat_item)

            # Status
            status_item = QTableWidgetItem(status.capitalize())
            # FIX: Use setData
            status_item.setData(Qt.ItemDataRole.TextAlignmentRole, Qt.AlignmentFlag.AlignCenter)
            status_item.setForeground(QBrush(status_color))
            self._table.setItem(row, 3, status_item)

            # Feasibility
            feas_item = QTableWidgetItem(f"{feasibility:.2f}")
            # FIX: Use setData
            feas_item.setData(Qt.ItemDataRole.TextAlignmentRole, Qt.AlignmentFlag.AlignCenter)
            feas_color = (
                colors.accent_green if feasibility >= 0.7
                else colors.text_muted
            )
            feas_item.setForeground(QBrush(QColor(feas_color)))
            self._table.setItem(row, 4, feas_item)

            # Impact
            imp_item = QTableWidgetItem(f"{impact:.2f}")
            # FIX: Use setData
            imp_item.setData(Qt.ItemDataRole.TextAlignmentRole, Qt.AlignmentFlag.AlignCenter)
            imp_color = (
                colors.accent_green if impact >= 0.7
                else colors.text_muted
            )
            imp_item.setForeground(QBrush(QColor(imp_color)))
            self._table.setItem(row, 5, imp_item)

            # Row height
            self._table.setRowHeight(row, 36)

        self._table.setSortingEnabled(True)

    def _on_selection(self):
        """Handle row selection"""
        rows = self._table.selectedItems()
        if not rows:
            return

        row = rows[0].row()
        item = self._table.item(row, 0)
        if item:
            proposal = item.data(Qt.ItemDataRole.UserRole)
            if proposal:
                self._show_detail(proposal)
                self.proposal_selected.emit(proposal)

    def _show_detail(self, p: dict):
        """Show proposal details"""
        name = p.get("name", "?")
        desc = p.get("description", "No description")
        status = p.get("status", "?")
        category = p.get("category", "?")
        priority = p.get("priority_score", 0)
        feasibility = p.get("feasibility_score", 0)
        impact = p.get("impact_score", 0)
        risk = p.get("risk_score", 0)
        complexity = p.get("complexity_score", 0)
        approach = p.get("implementation_plan", "")
        deps = p.get("dependencies_required", [])
        loc = p.get("estimated_lines_of_code", 0)

        html = f"""
        <div style="color: {colors.text_primary};">
            <b>{name}</b> 
            <span style="color: {colors.text_muted};">[{category} / {status}]</span><br>
            <span style="color: {colors.text_secondary};">{desc}</span><br>
            <span style="color: {colors.text_muted}; font-size: 11px;">
                Priority: {priority:.2f} | 
                Feasibility: {feasibility:.2f} | 
                Impact: {impact:.2f} | 
                Risk: {risk:.2f} | 
                Complexity: {complexity:.2f} | 
                ~{loc} LOC
            </span>
        """
        if deps:
            html += f'<br><span style="color: {colors.accent_orange};">Deps: {", ".join(deps)}</span>'
        if approach:
            html += f'<br><span style="color: {colors.text_disabled};">{approach[:150]}...</span>'
        html += "</div>"

        self._detail.setHtml(html)

# ═══════════════════════════════════════════════════════════════════════════════
# EVOLUTION HISTORY — Timeline of past evolutions
# ═══════════════════════════════════════════════════════════════════════════════

class EvolutionHistory(QFrame):
    """Scrollable timeline of past evolution attempts"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"EvolutionHistory {{ "
            f"background-color: {colors.bg_surface}; "
            f"border: 1px solid {colors.border_default}; "
            f"border-radius: {spacing.border_radius}px; "
            f"}}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        title = QLabel("📜 Evolution History")
        title.setFont(QFont(fonts.family_primary, fonts.size_sm))
        title.setStyleSheet(
            f"color: {colors.accent_cyan}; background: transparent; "
            f"font-weight: bold;"
        )
        layout.addWidget(title)

        self._list = QTextBrowser()
        self._list.setStyleSheet(
            f"QTextBrowser {{ "
            f"background: transparent; border: none; "
            f"color: {colors.text_secondary}; "
            f"font-size: {fonts.size_sm}px; "
            f"}}"
        )
        self._list.setOpenExternalLinks(False)
        layout.addWidget(self._list)

    def set_history(self, records: List[dict]):
        """Set evolution history records"""
        if not records:
            self._list.setHtml(
                f'<div style="color: {colors.text_disabled}; text-align: center; '
                f'padding: 20px;">No evolution history yet.</div>'
            )
            return

        html_parts = []
        for rec in reversed(records):  # newest first
            success = rec.get("success", False)
            name = rec.get("proposal_name", "Unknown")
            duration = rec.get("duration_seconds", 0)
            files_c = len(rec.get("files_created", []))
            files_m = len(rec.get("files_modified", []))
            lines = rec.get("lines_added", 0)
            status = rec.get("status", "?")
            error = rec.get("error_message", "")
            rollback = rec.get("rollback_performed", False)

            icon = "✅" if success else "❌"
            border_color = colors.accent_green if success else colors.danger

            detail = f"+{files_c} files, ~{files_m} modified, +{lines} lines"
            if rollback:
                detail += f' <span style="color: {colors.warning};">⏪ rolled back</span>'
            if error and not success:
                detail += f'<br><span style="color: {colors.danger};">{error[:80]}</span>'

            html_parts.append(f"""
            <div style="border-left: 3px solid {border_color}; 
                         padding: 6px 10px; margin: 4px 0;
                         background-color: {NexusColors.hex_to_rgba(border_color, 0.05)};
                         border-radius: 0 6px 6px 0;">
                <span style="font-weight: bold; color: {colors.text_primary};">
                    {icon} {name}
                </span>
                <span style="color: {colors.text_disabled}; font-size: 11px; float: right;">
                    {duration:.1f}s
                </span><br>
                <span style="color: {colors.text_muted}; font-size: 11px;">
                    {detail}
                </span>
            </div>
            """)

        self._list.setHtml("\n".join(html_parts))

# ═══════════════════════════════════════════════════════════════════════════════
# CODE HEALTH WIDGET
# ═══════════════════════════════════════════════════════════════════════════════

class CodeHealthWidget(QFrame):
    """Shows code health metrics"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"CodeHealthWidget {{ "
            f"background-color: {colors.bg_surface}; "
            f"border: 1px solid {colors.border_default}; "
            f"border-radius: {spacing.border_radius}px; "
            f"}}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        title = QLabel("💻 Code Health")
        title.setFont(QFont(fonts.family_primary, fonts.size_sm))
        title.setStyleSheet(
            f"color: {colors.accent_green}; background: transparent; "
            f"font-weight: bold;"
        )
        layout.addWidget(title)

        self._kv_files = KeyValueRow("Files", "0")
        layout.addWidget(self._kv_files)

        self._kv_lines = KeyValueRow("Total Lines", "0")
        layout.addWidget(self._kv_lines)

        self._kv_errors = KeyValueRow("Active Errors", "0")
        layout.addWidget(self._kv_errors)

        self._kv_fixed = KeyValueRow("Errors Fixed", "0", colors.accent_green)
        layout.addWidget(self._kv_fixed)

        # Health bar
        health_row = QHBoxLayout()
        health_row.setSpacing(8)
        hl = QLabel("Health")
        hl.setFont(QFont(fonts.family_primary, fonts.size_xs))
        hl.setStyleSheet(
            f"color: {colors.text_muted}; background: transparent;"
        )
        hl.setFixedWidth(50)
        health_row.addWidget(hl)

        self._health_bar = QProgressBar()
        self._health_bar.setRange(0, 100)
        self._health_bar.setValue(100)
        self._health_bar.setFixedHeight(12)
        self._health_bar.setTextVisible(True)
        self._health_bar.setFormat("%v%")
        health_row.addWidget(self._health_bar)
        layout.addLayout(health_row)

    def update_health(
        self, files: int = 0, lines: int = 0,
        errors: int = 0, fixed: int = 0, health: float = 1.0,
    ):
        self._kv_files.set_value(str(files))
        self._kv_lines.set_value(f"{lines:,}")

        error_color = colors.danger if errors > 0 else colors.accent_green
        self._kv_errors.set_value(str(errors), error_color)
        self._kv_fixed.set_value(str(fixed), colors.accent_green)

        health_pct = int(health * 100)
        self._health_bar.setValue(health_pct)

        bar_color = (
            colors.accent_green if health_pct > 80
            else colors.warning if health_pct > 50
            else colors.danger
        )
        self._health_bar.setStyleSheet(
            f"QProgressBar {{ background: {colors.bg_medium}; border: none; "
            f"border-radius: 6px; color: {colors.text_primary}; "
            f"font-size: {fonts.size_xs}px; }} "
            f"QProgressBar::chunk {{ background: {bar_color}; border-radius: 6px; }}"
        )

# ═══════════════════════════════════════════════════════════════════════════════
# EVOLUTION PANEL — Main panel
# ═══════════════════════════════════════════════════════════════════════════════

class EvolutionPanel(QFrame):
    """
    Full self-improvement and evolution monitoring panel.
    """

    def __init__(self, brain=None, parent=None):
        super().__init__(parent)
        self._brain = brain
        self.setStyleSheet(f"background-color: {colors.bg_dark};")

        self._build_ui()

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(animations.stats_refresh_ms)
        self._refresh_timer.timeout.connect(self._auto_refresh)

    def _build_ui(self):
        """Build the evolution panel layout"""
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
        header_row = QHBoxLayout()

        header = HeaderLabel(
            "Self-Improvement & Evolution", icons.EVOLVE, colors.accent_cyan
        )
        header_row.addWidget(header)
        header_row.addStretch()

        # Submit idea button
        idea_btn = QPushButton("💡 Submit Idea")
        idea_btn.setFixedHeight(34)
        idea_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        idea_btn.setStyleSheet(
            f"QPushButton {{ "
            f"background-color: {colors.accent_cyan}; "
            f"color: {colors.text_on_accent}; "
            f"border: none; border-radius: 8px; "
            f"padding: 6px 16px; font-weight: 600; "
            f"font-size: {fonts.size_sm}px; "
            f"}} "
            f"QPushButton:hover {{ "
            f"background-color: {NexusColors.blend(colors.accent_cyan, '#ffffff', 0.15)}; "
            f"}}"
        )
        idea_btn.clicked.connect(self._submit_idea)
        header_row.addWidget(idea_btn)

        # Evolve button
        evolve_btn = QPushButton("🧬 Evolve Feature")
        evolve_btn.setFixedHeight(34)
        evolve_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        evolve_btn.setStyleSheet(
            f"QPushButton {{ "
            f"background-color: {colors.accent_green}; "
            f"color: {colors.text_on_accent}; "
            f"border: none; border-radius: 8px; "
            f"padding: 6px 16px; font-weight: 600; "
            f"font-size: {fonts.size_sm}px; "
            f"}} "
            f"QPushButton:hover {{ "
            f"background-color: {NexusColors.blend(colors.accent_green, '#ffffff', 0.15)}; "
            f"}}"
        )
        evolve_btn.clicked.connect(self._manual_evolve)
        header_row.addWidget(evolve_btn)

        # Refresh
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(34, 34)
        refresh_btn.setStyleSheet(self._toolbar_btn_style())
        refresh_btn.clicked.connect(self._auto_refresh)
        header_row.addWidget(refresh_btn)

        layout.addLayout(header_row)

        # ═══ TOP STAT CARDS ═══
        cards = QHBoxLayout()
        cards.setSpacing(12)

        self._card_evolved = StatCard(
            icons.EVOLVE, "Evolved", "0", colors.accent_green
        )
        cards.addWidget(self._card_evolved)

        self._card_proposals = StatCard(
            "📋", "Proposals", "0", colors.accent_cyan
        )
        cards.addWidget(self._card_proposals)

        self._card_rate = StatCard(
            "📊", "Success Rate", "0%", colors.accent_purple
        )
        cards.addWidget(self._card_rate)

        self._card_lines = StatCard(
            "✏️", "Lines Written", "0", colors.accent_orange
        )
        cards.addWidget(self._card_lines)

        self._card_research = StatCard(
            icons.RESEARCH, "Research", "0 cycles", colors.accent_teal
        )
        cards.addWidget(self._card_research)

        layout.addLayout(cards)

        # ═══ EVOLUTION PROGRESS ═══
        self._progress_widget = EvolutionProgressWidget()
        layout.addWidget(self._progress_widget)

        # ═══ PROPOSALS TABLE ═══
        self._proposal_table = ProposalTable()
        self._proposal_table.setMinimumHeight(300)
        layout.addWidget(self._proposal_table)

        # ═══ BOTTOM ROW — History + Code Health ═══
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)

        self._history = EvolutionHistory()
        self._history.setMinimumHeight(200)
        bottom_row.addWidget(self._history, 2)

        # Right column — Code Health + Research
        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        self._code_health = CodeHealthWidget()
        right_col.addWidget(self._code_health)

        # Research activity
        research_section = Section("🔬 Research Activity", expanded=True)

        self._kv_research_status = KeyValueRow(
            "Status", "Idle", colors.accent_cyan
        )
        research_section.add_widget(self._kv_research_status)

        self._kv_topics_researched = KeyValueRow("Topics Researched", "0")
        research_section.add_widget(self._kv_topics_researched)

        self._kv_current_topic = KeyValueRow("Current Topic", "None")
        research_section.add_widget(self._kv_current_topic)

        self._kv_last_research = KeyValueRow("Last Research", "never")
        research_section.add_widget(self._kv_last_research)

        self._kv_packages = KeyValueRow(
            "Packages Installed", "0", colors.accent_orange
        )
        research_section.add_widget(self._kv_packages)

        self._kv_rollbacks = KeyValueRow("Rollbacks", "0", colors.warning)
        research_section.add_widget(self._kv_rollbacks)

        right_col.addWidget(research_section)

        bottom_row.addLayout(right_col, 1)
        layout.addLayout(bottom_row)

        layout.addStretch()

        scroll.setWidget(content)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    # ═══════════════════════════════════════════════════════════════════════════
    # DATA UPDATE
    # ═══════════════════════════════════════════════════════════════════════════

    def update_stats(self, stats: Dict[str, Any]):
        """Update all evolution widgets"""
        try:
            self._update_cards(stats)
            self._update_progress(stats)
            self._update_proposals(stats)
            self._update_history(stats)
            self._update_code_health(stats)
            self._update_research(stats)
        except Exception as e:
            logger.debug(f"Evolution panel update error: {e}")

    def _update_cards(self, stats: dict):
        """Update top stat cards"""
        se = stats.get("self_evolution", {})
        fr = stats.get("feature_research", {})

        if se:
            succeeded = se.get("total_succeeded", 0)
            attempted = se.get("total_attempted", 0)
            rate = se.get("success_rate", 0)
            lines = se.get("total_lines_added", 0)

            self._card_evolved.set_value(str(succeeded))
            self._card_evolved.set_subtitle(f"of {attempted} attempted")

            self._card_rate.set_value(f"{rate:.0%}")
            rate_color = (
                colors.accent_green if rate >= 0.7
                else colors.warning if rate >= 0.4
                else colors.danger
            )
            self._card_rate.set_accent(rate_color)

            self._card_lines.set_value(f"{lines:,}")
            self._card_lines.set_subtitle(
                f"{se.get('total_files_created', 0)} files"
            )

        if fr:
            total = fr.get("total_proposals", 0)
            self._card_proposals.set_value(str(total))
            breakdown = fr.get("status_breakdown", {})
            approved = breakdown.get("approved", 0)
            completed = breakdown.get("completed", 0)
            self._card_proposals.set_subtitle(
                f"{approved} approved, {completed} done"
            )

            cycles = fr.get("research_cycles", 0)
            self._card_research.set_value(f"{cycles} cycles")
            self._card_research.set_subtitle(
                f"{fr.get('topics_researched', 0)} topics"
            )

    def _update_progress(self, stats: dict):
        """Update evolution progress widget"""
        se = stats.get("self_evolution", {})
        if not se:
            self._progress_widget.set_idle()
            return

        status = se.get("current_status", "idle")
        current = se.get("current_evolution")

        if current:
            self._progress_widget.set_evolution(current, status)
        elif status == "idle":
            self._progress_widget.set_idle()
        else:
            self._progress_widget.set_evolution("Unknown", status)

    def _update_proposals(self, stats: dict):
        """Update proposals table"""
        if not self._brain:
            return

        try:
            si = None
            if hasattr(self._brain, '_self_improvement_system'):
                si = self._brain._self_improvement_system

            if si:
                proposals = si.get_proposals()
                self._proposal_table.set_proposals(proposals)
            elif hasattr(self._brain, '_feature_researcher') and self._brain._feature_researcher:
                proposals = self._brain._feature_researcher.get_all_proposals()
                self._proposal_table.set_proposals(
                    [p.to_dict() for p in proposals]
                )
        except Exception as e:
            logger.debug(f"Proposals update error: {e}")

    def _update_history(self, stats: dict):
        """Update evolution history"""
        if not self._brain:
            return

        try:
            si = None
            if hasattr(self._brain, '_self_improvement_system'):
                si = self._brain._self_improvement_system

            if si:
                history = si.get_evolution_history(20)
                self._history.set_history(history)
            elif hasattr(self._brain, '_self_evolution') and self._brain._self_evolution:
                history = self._brain._self_evolution.get_recent_evolutions(20)
                self._history.set_history(history)
        except Exception as e:
            logger.debug(f"History update error: {e}")

    def _update_code_health(self, stats: dict):
        """Update code health widget"""
        si = stats.get("self_improvement", {})
        if not isinstance(si, dict):
            return

        subs = si.get("subsystems", {})

        cm = subs.get("code_monitor", {})
        ef = subs.get("error_fixer", {})

        files = cm.get("files_watched", 0) if isinstance(cm, dict) else 0
        errors = cm.get("errors_detected", 0) if isinstance(cm, dict) else 0
        fixed = ef.get("errors_fixed", ef.get("total_successful", 0)) if isinstance(ef, dict) else 0

        # Get lines from feature research codebase analysis
        fr = stats.get("feature_research", {})
        codebase = fr.get("codebase", {}) if isinstance(fr, dict) else {}
        lines = codebase.get("lines", 0)
        if not lines and isinstance(cm, dict):
            lines = cm.get("total_lines", 0)

        health = 1.0 if errors == 0 else max(0, 1 - errors / max(files, 1))

        self._code_health.update_health(
            files=files, lines=lines, errors=errors,
            fixed=fixed, health=health,
        )

    def _update_research(self, stats: dict):
        """Update research activity section"""
        fr = stats.get("feature_research", {})
        se = stats.get("self_evolution", {})

        if isinstance(fr, dict):
            running = fr.get("running", False)
            self._kv_research_status.set_value(
                "Active" if running else "Idle",
                colors.accent_green if running else colors.text_muted,
            )

            self._kv_topics_researched.set_value(
                str(fr.get("topics_researched", 0))
            )

            current_topic = fr.get("current_topic", "")
            self._kv_current_topic.set_value(
                current_topic[:40] if current_topic else "None"
            )

            last = fr.get("last_research", "never")
            self._kv_last_research.set_value(str(last)[:19])

        if isinstance(se, dict):
            self._kv_packages.set_value(
                str(se.get("total_packages_installed", 0))
            )
            self._kv_rollbacks.set_value(
                str(se.get("total_rollbacks", 0))
            )

    # ═══════════════════════════════════════════════════════════════════════════
    # ACTIONS
    # ═══════════════════════════════════════════════════════════════════════════

    def _submit_idea(self):
        """Open dialog to submit a feature idea"""
        text, ok = QInputDialog.getMultiLineText(
            self,
            "💡 Submit Feature Idea",
            "Describe the feature you'd like NEXUS to add to itself:\n"
            "(Be specific — what should it do, how should it work?)",
            "",
        )
        
        if ok and text.strip():
            try:
                si = getattr(self._brain, '_self_improvement_system', None)
                if si:
                    result = si.submit_feature_idea(text.strip())
                    pid = result.get("proposal_id", "?")
                    QMessageBox.information(
                        self,
                        "Idea Submitted",
                        f"💡 Your idea has been submitted!\n\n"
                        f"Proposal ID: {pid}\n"
                        f"It will be evaluated in the next research cycle.\n"
                        f"If approved, NEXUS will implement it autonomously.",
                    )
                    self._auto_refresh()
                else:
                    QMessageBox.warning(
                        self, "Error",
                        "Self-improvement system not active.",
                    )
            except Exception as e:
                QMessageBox.warning(
                    self, "Error", f"Failed to submit: {e}"
                )

    def _manual_evolve(self):
        """Open dialog to manually trigger evolution"""
        text, ok = QInputDialog.getMultiLineText(
            self,
            "🧬 Evolve Feature",
            "Describe the feature to implement right now:\n"
            "(NEXUS will plan, code, test, and integrate it)",
            "",
        )
    
        if ok and text.strip():
            if self._brain:
                reply = QMessageBox.question(
                    self,
                    "Confirm Evolution",
                    f"Start evolution?\n\n"
                    f"Feature: {text.strip()[:100]}\n\n"
                    f"This will:\n"
                    f"• Generate implementation code\n"
                    f"• Create backups\n"
                    f"• Write/modify files\n"
                    f"• Validate and test\n"
                    f"• Auto-rollback on failure\n\n"
                    f"Continue?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
    
                if reply == QMessageBox.StandardButton.Yes:
                    self._progress_widget.set_evolution(text.strip()[:50], "planning")
    
                    try:
                        result = self._brain.evolve_feature(text.strip())
                        success, msg = result.get("success", False), result.get("message", "")
                    except Exception as e:
                        success, msg = False, str(e)
    
                    QTimer.singleShot(0, lambda: self._on_evolve_complete(success, msg))

    def _on_evolve_complete(self, success: bool, message: str):
        """Handle evolution completion"""
        if success:
            self._progress_widget.set_evolution("Manual Evolution", "completed")
            QMessageBox.information(
                self, "Evolution Complete",
                f"✅ Evolution succeeded!\n\n{message}",
            )
        else:
            self._progress_widget.set_evolution("Manual Evolution", "failed")
            QMessageBox.warning(
                self, "Evolution Failed",
                f"❌ Evolution failed.\n\n{message}",
            )
        self._auto_refresh()

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def _auto_refresh(self):
        if self._brain and self._brain.is_running:
            try:
                stats = self._brain.get_stats()
                self.update_stats(stats)
            except Exception as e:
                logger.debug(f"Evolution panel auto-refresh error: {e}")

    def on_shown(self):
        if not self._refresh_timer.isActive():
            self._refresh_timer.start()
        self._auto_refresh()

    def quick_refresh(self):
        pass

    def set_brain(self, brain):
        self._brain = brain
        self._auto_refresh()

    def _toolbar_btn_style(self) -> str:
        return (
            f"QPushButton {{ "
            f"background-color: {colors.bg_elevated}; "
            f"color: {colors.text_secondary}; "
            f"border: 1px solid {colors.border_subtle}; "
            f"border-radius: 6px; "
            f"font-size: {fonts.size_sm}px; "
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
    window.setWindowTitle("NEXUS Evolution Panel Test")
    window.setMinimumSize(1100, 800)
    window.setStyleSheet(f"background-color: {colors.bg_dark};")

    layout = QVBoxLayout(window)
    layout.setContentsMargins(0, 0, 0, 0)

    panel = EvolutionPanel()
    layout.addWidget(panel)

    import random

    def fake_data():
        statuses = [
            "proposed", "evaluated", "approved", "completed",
            "failed", "rejected",
        ]
        categories = [
            "intelligence", "emotion", "ui", "monitoring",
            "learning", "utility", "performance",
        ]

        proposals = []
        for i in range(15):
            proposals.append({
                "proposal_id": f"p{i:03d}",
                "name": random.choice([
                    "Voice Command Parser", "Sentiment Dashboard",
                    "Email Integration", "Screenshot Analyzer",
                    "Quantum Simulator", "Log Rotator",
                    "Auto Backup Manager", "Weather Widget",
                    "Habit Tracker", "Focus Timer",
                    "Code Formatter", "API Monitor",
                    "Chat Export Plugin", "Mood Journal",
                    "System Profiler",
                ]),
                "description": "A feature that does something useful.",
                "category": random.choice(categories),
                "status": random.choice(statuses),
                "priority_score": random.uniform(0.1, 0.95),
                "feasibility_score": random.uniform(0.2, 0.95),
                "impact_score": random.uniform(0.2, 0.9),
                "risk_score": random.uniform(0.05, 0.6),
                "complexity_score": random.uniform(0.1, 0.8),
                "estimated_lines_of_code": random.randint(20, 500),
                "dependencies_required": [],
                "implementation_plan": "Create module, integrate with brain.",
            })

        history = []
        for i in range(5):
            history.append({
                "proposal_name": random.choice([
                    "Log Rotator", "Voice Parser", "Focus Timer",
                    "API Monitor", "Chat Export",
                ]),
                "success": random.random() > 0.3,
                "duration_seconds": random.uniform(3, 25),
                "status": random.choice(["completed", "failed"]),
                "files_created": [f"module_{i}.py"],
                "files_modified": ["core/brain.py"],
                "lines_added": random.randint(20, 300),
                "error_message": "SyntaxError" if random.random() > 0.7 else "",
                "rollback_performed": random.random() > 0.8,
            })

        evo_status = random.choice([
            "idle", "planning", "writing_code", "validating", "testing",
        ])

        stats = {
            "self_evolution": {
                "current_status": evo_status,
                "current_evolution": (
                    "Voice Command Parser" if evo_status != "idle" else None
                ),
                "total_succeeded": random.randint(0, 8),
                "total_attempted": random.randint(2, 12),
                "success_rate": random.uniform(0.5, 1.0),
                "total_lines_added": random.randint(0, 2000),
                "total_files_created": random.randint(0, 15),
                "total_packages_installed": random.randint(0, 5),
                "total_rollbacks": random.randint(0, 3),
            },
            "feature_research": {
                "running": True,
                "total_proposals": len(proposals),
                "research_cycles": random.randint(1, 20),
                "topics_researched": random.randint(5, 50),
                "current_topic": "AI agent tool use",
                "last_research": datetime.now().isoformat()[:19],
                "status_breakdown": {
                    "proposed": sum(1 for p in proposals if p["status"] == "proposed"),
                    "approved": sum(1 for p in proposals if p["status"] == "approved"),
                    "completed": sum(1 for p in proposals if p["status"] == "completed"),
                    "failed": sum(1 for p in proposals if p["status"] == "failed"),
                },
                "codebase": {
                    "files": 47, "lines": 12340, "classes": 85,
                },
            },
            "self_improvement": {
                "subsystems": {
                    "code_monitor": {
                        "files_watched": 47,
                        "errors_detected": random.randint(0, 3),
                        "total_lines": 12340,
                    },
                    "error_fixer": {
                        "total_successful": random.randint(0, 10),
                    },
                },
            },
        }

        panel.update_stats(stats)
        panel._proposal_table.set_proposals(proposals)
        panel._history.set_history(history)

    timer = QTimer()
    timer.timeout.connect(fake_data)
    timer.start(3000)
    fake_data()

    window.show()
    sys.exit(app.exec())