"""
NEXUS AI - System Monitor Panel (Advanced)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Comprehensive real-time system resource monitoring dashboard.

Layout:
  ┌─────────────────────────────────────────────────────────────────┐
  │  🖥️ System Monitor                                              │
  │  ──────────────────────────────────────────────────── orange    │
  │                                                                  │
  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
  │  │   CPU    │ │   RAM    │ │   Disk   │ │ Network  │           │
  │  │  Gauge   │ │  Gauge   │ │  Gauge   │ │  Gauge   │           │
  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
  │                                                                  │
  │  ▼ ⚡ Real-time Performance                                     │
  │  ┌──────────────────────────────────────────────────────────┐   │
  │  │  CPU Usage     [█████████████████░░░░░░░░░] ~~~~~~~~~~~~ │   │
  │  │  RAM Usage     [████████████░░░░░░░░░░░░░░] ~~~~~~~~~~~~ │   │
  │  │  Network ↑↓    [                          ] ~~~~~~~~~~~~ │   │
  │  │  Disk I/O      [                          ] ~~~~~~~~~~~~ │   │
  │  └──────────────────────────────────────────────────────────┘   │
  │                                                                  │
  │  ▼ 🧩 Per-Core CPU                                              │
  │  ┌──────────────────────────────────────────────────────────┐   │
  │  │  Core 0 [████████████░░] 78%   Core 1 [███████░░░░] 52% │   │
  │  │  Core 2 [█████░░░░░░░░] 35%   Core 3 [██████████░] 89% │   │
  │  └──────────────────────────────────────────────────────────┘   │
  │                                                                  │
  │  ▼ 💾 Memory Breakdown                                          │
  │  ┌──────────────────────────────────────────────────────────┐   │
  │  │  [Used ██████░░░ Available] Total: 32 GB                 │   │
  │  │  Used: 24.8 GB  |  Available: 7.2 GB  |  Cached: 4.1 GB │   │
  │  │  Swap: 2.1 / 8.0 GB  (26%)                              │   │
  │  └──────────────────────────────────────────────────────────┘   │
  │                                                                  │
  │  ▼ 📋 Top Processes (by CPU)                                    │
  │  ┌──────────────────────────────────────────────────────────┐   │
  │  │  PID   Name             CPU%    MEM%    Status           │   │
  │  │  1234  python.exe       12.3    4.5     running          │   │
  │  │  5678  chrome.exe        8.1    12.3    running          │   │
  │  └──────────────────────────────────────────────────────────┘   │
  │                                                                  │
  │  ▶ 🧠 NEXUS Brain Resources                                    │
  │  ▶ 🖥️ Hardware Details                                          │
  └─────────────────────────────────────────────────────────────────┘
"""
import sys
import math
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

import psutil
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QProgressBar, QGridLayout, QScrollArea, QTableWidget,
    QTableWidgetItem, QHeaderView, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush,
    QLinearGradient, QPainterPath
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ui.theme import theme, colors, fonts, spacing, icons
from ui.widgets import HeaderLabel, CircularGauge, MiniChart, Section, StatCard, TagLabel


# ═══════════════════════════════════════════════════════════════════════════════
# STACKED BAR WIDGET - Memory / Swap visualisation
# ═══════════════════════════════════════════════════════════════════════════════

class StackedBar(QWidget):
    """Horizontal stacked bar with labeled segments."""

    def __init__(self, height: int = 22, parent=None):
        super().__init__(parent)
        self._segments: List[Dict[str, Any]] = []
        self.setFixedHeight(height)
        self.setMinimumWidth(120)

    def set_segments(self, segments: List[Dict[str, Any]]):
        """segments = [{'label': str, 'value': float, 'color': str}, ...]"""
        self._segments = segments
        self.update()

    def paintEvent(self, event):
        if not self._segments:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        total = sum(s.get("value", 0) for s in self._segments)
        if total <= 0:
            painter.end()
            return

        w, h = self.width(), self.height()
        x = 0
        radius = 4

        for seg in self._segments:
            val = seg.get("value", 0)
            if val <= 0:
                continue
            seg_w = max(2, int(w * val / total))
            color = QColor(seg.get("color", colors.accent_cyan))

            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)

            path = QPainterPath()
            path.addRoundedRect(float(x), 1, float(min(seg_w - 1, w - x)), float(h - 2),
                                radius, radius)
            painter.drawPath(path)

            # Label inside if large enough
            if seg_w > 60:
                font = QFont(fonts.family_primary, 9)
                font.setBold(True)
                painter.setFont(font)
                painter.setPen(QColor("#000000"))
                text = seg.get("label", "")
                painter.drawText(int(x), 1, seg_w, h - 2,
                                 Qt.AlignmentFlag.AlignCenter, text)

            x += seg_w

        painter.end()


# ═══════════════════════════════════════════════════════════════════════════════
# PER-CORE BAR - Animated progress bars for each CPU core
# ═══════════════════════════════════════════════════════════════════════════════

class CoreBar(QWidget):
    """A single CPU core usage bar with label and percentage."""

    def __init__(self, core_id: int, parent=None):
        super().__init__(parent)
        self._core_id = core_id
        self._value = 0.0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 1, 0, 1)
        layout.setSpacing(6)

        self._label = QLabel(f"Core {core_id}")
        self._label.setFixedWidth(52)
        self._label.setStyleSheet(
            f"color: {colors.text_secondary}; font-size: 10px; font-weight: 600;"
        )
        layout.addWidget(self._label)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(10)
        self._bar.setStyleSheet(f"""
            QProgressBar {{ background: {colors.bg_dark}; border: none; border-radius: 5px; }}
            QProgressBar::chunk {{ background: {colors.accent_orange}; border-radius: 5px; }}
        """)
        layout.addWidget(self._bar)

        self._pct = QLabel("0%")
        self._pct.setFixedWidth(36)
        self._pct.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._pct.setStyleSheet(
            f"color: {colors.text_primary}; font-size: 10px; font-weight: bold;"
        )
        layout.addWidget(self._pct)

    def set_value(self, pct: float):
        self._value = pct
        self._bar.setValue(int(pct))
        self._pct.setText(f"{pct:.0f}%")

        # Color code by intensity
        if pct >= 90:
            color = "#ff4444"
        elif pct >= 70:
            color = colors.accent_orange
        elif pct >= 40:
            color = "#ffcc00"
        else:
            color = colors.accent_green
        self._bar.setStyleSheet(f"""
            QProgressBar {{ background: {colors.bg_dark}; border: none; border-radius: 5px; }}
            QProgressBar::chunk {{ background: {color}; border-radius: 5px; }}
        """)


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PANEL
# ═══════════════════════════════════════════════════════════════════════════════

class SystemPanel(QFrame):
    """
    Advanced System Monitor with gauges, per-core CPU, memory breakdown,
    network/disk I/O sparklines, top processes, and NEXUS brain resource stats.
    """

    def __init__(self, brain=None, parent=None):
        super().__init__(parent)
        self._brain = brain
        self.setStyleSheet(f"background-color: {colors.bg_dark};")

        # History buffers (50 points each)
        self._cpu_history = [0] * 50
        self._ram_history = [0] * 50
        self._net_send_history = [0] * 50
        self._net_recv_history = [0] * 50
        self._disk_read_history = [0] * 50
        self._disk_write_history = [0] * 50

        # Previous I/O counters for delta calculations
        self._prev_net_io = None
        self._prev_disk_io = None
        self._prev_time = time.time()

        # Peak values for display
        self._peak_cpu = 0.0
        self._peak_ram = 0.0

        self._build_ui()

        # Fast timer (1s) – gauges, charts, cores
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_stats)
        self._timer.start(1000)

        # Slower timer (5s) – process list, brain stats
        self._slow_timer = QTimer(self)
        self._slow_timer.timeout.connect(self._update_slow_stats)
        self._slow_timer.start(5000)

    # ═══════════════════════════════════════════════════════════════════════════
    # UI CONSTRUCTION
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        # Wrap in scroll area
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
        layout.addWidget(HeaderLabel("System Monitor", icons.BODY, colors.accent_orange))

        # ── Gauges Row ──
        gauges_layout = QHBoxLayout()
        gauges_layout.setSpacing(8)
        self._cpu_gauge = CircularGauge("CPU", 0, 100, colors.accent_orange, 150, 6)
        self._ram_gauge = CircularGauge("RAM", 0, 100, colors.accent_purple, 150, 6)
        self._disk_gauge = CircularGauge("Disk", 0, 100, colors.accent_cyan, 150, 6)
        self._net_gauge = CircularGauge("Network", 0, 100, colors.accent_green, 150, 6)

        for g in [self._cpu_gauge, self._ram_gauge, self._disk_gauge, self._net_gauge]:
            g.set_suffix("%")
            gauges_layout.addWidget(g)
        layout.addLayout(gauges_layout)

        # ── Real-time Performance Section ──
        perf_section = Section("Real-time Performance", icons.CPU, expanded=True)
        perf_layout = QVBoxLayout()
        perf_layout.setSpacing(8)

        # CPU sparkline
        perf_layout.addLayout(self._make_chart_row(
            "CPU Usage", colors.accent_orange, "_cpu_chart"
        ))
        # RAM sparkline
        perf_layout.addLayout(self._make_chart_row(
            "RAM Usage", colors.accent_purple, "_ram_chart"
        ))
        # Network send/recv sparklines
        perf_layout.addLayout(self._make_chart_row(
            "Net ↑ Send", colors.accent_green, "_net_send_chart"
        ))
        perf_layout.addLayout(self._make_chart_row(
            "Net ↓ Recv", colors.accent_cyan, "_net_recv_chart"
        ))
        # Disk I/O sparklines
        perf_layout.addLayout(self._make_chart_row(
            "Disk Read", "#96ceb4", "_disk_read_chart"
        ))
        perf_layout.addLayout(self._make_chart_row(
            "Disk Write", "#dda0dd", "_disk_write_chart"
        ))

        perf_section.add_layout(perf_layout)
        layout.addWidget(perf_section)

        # ── Per-Core CPU Section ──
        self._cores_section = Section("Per-Core CPU", "🧩", expanded=True)
        self._cores_layout = QGridLayout()
        self._cores_layout.setSpacing(2)
        self._core_bars: List[CoreBar] = []

        num_cores = psutil.cpu_count(logical=True) or 4
        for i in range(num_cores):
            bar = CoreBar(i)
            self._core_bars.append(bar)
            row = i // 2
            col = i % 2
            self._cores_layout.addWidget(bar, row, col)

        self._cores_section.add_layout(self._cores_layout)
        layout.addWidget(self._cores_section)

        # ── Memory Breakdown Section ──
        mem_section = Section("Memory Breakdown", "💾", expanded=True)
        mem_layout = QVBoxLayout()
        mem_layout.setSpacing(8)

        # RAM stacked bar
        self._ram_bar = StackedBar(24)
        mem_layout.addWidget(self._ram_bar)

        # RAM detail labels
        ram_detail_row = QHBoxLayout()
        self._lbl_ram_used = self._detail_label("Used: ...")
        self._lbl_ram_avail = self._detail_label("Available: ...")
        self._lbl_ram_cached = self._detail_label("Cached: ...")
        ram_detail_row.addWidget(self._lbl_ram_used)
        ram_detail_row.addWidget(self._lbl_ram_avail)
        ram_detail_row.addWidget(self._lbl_ram_cached)
        mem_layout.addLayout(ram_detail_row)

        # Swap bar
        swap_header = QLabel("Swap Memory")
        swap_header.setStyleSheet(
            f"color: {colors.text_secondary}; font-size: 11px; font-weight: bold; "
            f"text-transform: uppercase; letter-spacing: 1px; margin-top: 4px;"
        )
        mem_layout.addWidget(swap_header)
        self._swap_bar = StackedBar(18)
        mem_layout.addWidget(self._swap_bar)
        self._lbl_swap = self._detail_label("Swap: ...")
        mem_layout.addWidget(self._lbl_swap)

        mem_section.add_layout(mem_layout)
        layout.addWidget(mem_section)

        # ── Top Processes Section ──
        proc_section = Section("Top Processes (by CPU)", "📋", expanded=False)
        proc_layout = QVBoxLayout()

        self._proc_table = QTableWidget()
        self._proc_table.setColumnCount(5)
        self._proc_table.setHorizontalHeaderLabels(["PID", "Name", "CPU %", "MEM %", "Status"])
        self._proc_table.setAlternatingRowColors(True)
        self._proc_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._proc_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._proc_table.verticalHeader().setVisible(False)
        self._proc_table.setMinimumHeight(200)
        self._proc_table.setStyleSheet(f"""
            QTableWidget {{ background: {colors.bg_surface}; border: 1px solid {colors.border_default};
                           border-radius: 8px; font-size: 11px; gridline-color: {colors.border_subtle}; }}
            QTableWidget::item {{ padding: 4px 8px; }}
            QHeaderView::section {{ background: {colors.bg_elevated}; color: {colors.text_secondary};
                                   border: none; border-bottom: 1px solid {colors.border_default};
                                   padding: 6px 8px; font-weight: 600; font-size: 10px; }}
        """)

        header = self._proc_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self._proc_table.setColumnWidth(0, 60)
        self._proc_table.setColumnWidth(2, 65)
        self._proc_table.setColumnWidth(3, 65)
        self._proc_table.setColumnWidth(4, 80)

        proc_layout.addWidget(self._proc_table)
        proc_section.add_layout(proc_layout)
        layout.addWidget(proc_section)

        # ── NEXUS Brain Resources Section ──
        brain_section = Section("NEXUS Brain Resources", "🧠", expanded=False)
        brain_layout = QVBoxLayout()

        brain_stats_row = QHBoxLayout()
        brain_stats_row.setSpacing(8)
        self._stat_threads = StatCard("🧵", "Threads", "0", colors.accent_cyan)
        self._stat_memory = StatCard("🧠", "Brain RAM", "0 MB", colors.accent_purple)
        self._stat_uptime = StatCard("⏱️", "Uptime", "0s", colors.accent_green)
        brain_stats_row.addWidget(self._stat_threads)
        brain_stats_row.addWidget(self._stat_memory)
        brain_stats_row.addWidget(self._stat_uptime)
        brain_layout.addLayout(brain_stats_row)

        # Python process details
        self._lbl_py_pid = self._detail_label("PID: ...")
        self._lbl_py_threads = self._detail_label("Python Threads: ...")
        self._lbl_py_fds = self._detail_label("Open Files: ...")
        py_row = QHBoxLayout()
        py_row.addWidget(self._lbl_py_pid)
        py_row.addWidget(self._lbl_py_threads)
        py_row.addWidget(self._lbl_py_fds)
        brain_layout.addLayout(py_row)

        brain_section.add_layout(brain_layout)
        layout.addWidget(brain_section)

        # ── Hardware Details Section ──
        hw_section = Section("Hardware Details", icons.BODY, expanded=False)
        hw_grid = QGridLayout()
        hw_grid.setSpacing(6)

        self._lbl_cpu_name = self._detail_label("Processor: ...")
        self._lbl_cores_info = self._detail_label("Cores: ...")
        self._lbl_ram_total = self._detail_label("Total RAM: ...")
        self._lbl_boot_time = self._detail_label("Boot Time: ...")
        self._lbl_os_info = self._detail_label("OS: ...")
        self._lbl_python = self._detail_label("Python: ...")

        hw_grid.addWidget(self._lbl_cpu_name, 0, 0, 1, 2)
        hw_grid.addWidget(self._lbl_cores_info, 1, 0)
        hw_grid.addWidget(self._lbl_ram_total, 1, 1)
        hw_grid.addWidget(self._lbl_boot_time, 2, 0)
        hw_grid.addWidget(self._lbl_os_info, 2, 1)
        hw_grid.addWidget(self._lbl_python, 3, 0, 1, 2)

        # Peak stats row
        peak_row = QHBoxLayout()
        self._lbl_peak_cpu = self._detail_label("Peak CPU: 0%", colors.accent_orange)
        self._lbl_peak_ram = self._detail_label("Peak RAM: 0%", colors.accent_purple)
        peak_row.addWidget(self._lbl_peak_cpu)
        peak_row.addWidget(self._lbl_peak_ram)
        hw_grid.addLayout(peak_row, 4, 0, 1, 2)

        hw_section.add_layout(hw_grid)
        layout.addWidget(hw_section)

        layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPER UI BUILDERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _make_chart_row(self, label: str, color: str, attr_name: str):
        """Create a label + sparkline chart row and store chart as self.<attr_name>."""
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFixedWidth(85)
        lbl.setStyleSheet(
            f"color: {colors.text_secondary}; font-weight: bold; font-size: 11px;"
        )

        chart = MiniChart(color, 45, 50)
        setattr(self, attr_name, chart)

        # Value label on the right
        val_lbl = QLabel("0")
        val_lbl.setFixedWidth(65)
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        val_lbl.setStyleSheet(
            f"color: {color}; font-weight: bold; font-size: 11px;"
        )
        setattr(self, attr_name + "_val", val_lbl)

        row.addWidget(lbl)
        row.addWidget(chart)
        row.addWidget(val_lbl)
        return row

    def _detail_label(self, text: str, color: str = None) -> QLabel:
        """Create a styled detail label."""
        lbl = QLabel(text)
        c = color or colors.text_primary
        lbl.setStyleSheet(f"color: {c}; font-size: 12px;")
        return lbl

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def set_brain(self, brain):
        self._brain = brain
        self._populate_static_info()
        self._update_stats()
        self._update_slow_stats()

    # ═══════════════════════════════════════════════════════════════════════════
    # STATIC INFO (set once)
    # ═══════════════════════════════════════════════════════════════════════════

    def _populate_static_info(self):
        """Fill once-only hardware labels."""
        import platform

        try:
            proc = platform.processor() or "Unknown"
            self._lbl_cpu_name.setText(f"🔲 Processor: {proc}")
        except Exception:
            self._lbl_cpu_name.setText("🔲 Processor: Unknown")

        phys = psutil.cpu_count(logical=False) or "?"
        logical = psutil.cpu_count(logical=True) or "?"
        self._lbl_cores_info.setText(f"Cores: {phys} physical / {logical} logical")

        ram_gb = psutil.virtual_memory().total / (1024 ** 3)
        self._lbl_ram_total.setText(f"Total RAM: {ram_gb:.1f} GB")

        try:
            boot = datetime.fromtimestamp(psutil.boot_time())
            self._lbl_boot_time.setText(f"Boot: {boot.strftime('%b %d, %H:%M')}")
        except Exception:
            self._lbl_boot_time.setText("Boot: Unknown")

        os_info = f"{platform.system()} {platform.release()}"
        self._lbl_os_info.setText(f"OS: {os_info}")
        self._lbl_python.setText(f"🐍 Python {platform.python_version()}")

    # ═══════════════════════════════════════════════════════════════════════════
    # FAST UPDATE (every 1s)
    # ═══════════════════════════════════════════════════════════════════════════

    def _update_stats(self):
        """Update gauges, sparklines, per-core bars, memory breakdown."""
        now = time.time()
        dt = now - self._prev_time
        self._prev_time = now

        # ── CPU ──
        cpu = psutil.cpu_percent()
        self._cpu_gauge.set_value(cpu)
        self._cpu_history.append(cpu)
        self._cpu_history.pop(0)
        self._cpu_chart.set_data(self._cpu_history)
        self._cpu_chart_val.setText(f"{cpu:.1f}%")

        # Peak tracking
        if cpu > self._peak_cpu:
            self._peak_cpu = cpu
            self._lbl_peak_cpu.setText(f"⚡ Peak CPU: {cpu:.1f}%")

        # ── RAM ──
        mem = psutil.virtual_memory()
        ram_pct = mem.percent
        self._ram_gauge.set_value(ram_pct)
        self._ram_history.append(ram_pct)
        self._ram_history.pop(0)
        self._ram_chart.set_data(self._ram_history)
        self._ram_chart_val.setText(f"{ram_pct:.1f}%")

        if ram_pct > self._peak_ram:
            self._peak_ram = ram_pct
            self._lbl_peak_ram.setText(f"💾 Peak RAM: {ram_pct:.1f}%")

        # ── Disk ──
        try:
            disk = psutil.disk_usage('/') if sys.platform != 'win32' else psutil.disk_usage('C:\\')
            self._disk_gauge.set_value(disk.percent)
        except Exception:
            pass

        # ── Network I/O ──
        try:
            net_io = psutil.net_io_counters()
            if self._prev_net_io and dt > 0:
                send_rate = (net_io.bytes_sent - self._prev_net_io.bytes_sent) / dt
                recv_rate = (net_io.bytes_recv - self._prev_net_io.bytes_recv) / dt

                # Convert to KB/s
                send_kbs = send_rate / 1024
                recv_kbs = recv_rate / 1024

                self._net_send_history.append(send_kbs)
                self._net_send_history.pop(0)
                self._net_send_chart.set_data(self._net_send_history)
                self._net_send_chart_val.setText(self._fmt_rate(send_rate))

                self._net_recv_history.append(recv_kbs)
                self._net_recv_history.pop(0)
                self._net_recv_chart.set_data(self._net_recv_history)
                self._net_recv_chart_val.setText(self._fmt_rate(recv_rate))

                # Network gauge: use a logarithmic scale (0-100 MB/s mapped to 0-100%)
                total_kbs = send_kbs + recv_kbs
                if total_kbs > 0:
                    # log scale: 1 KB/s = 0%, 100 MB/s = 100%
                    net_pct = min(100, max(0, (math.log10(max(total_kbs, 1)) / 5) * 100))
                else:
                    net_pct = 0
                self._net_gauge.set_value(net_pct)

            self._prev_net_io = net_io
        except Exception:
            pass

        # ── Disk I/O ──
        try:
            disk_io = psutil.disk_io_counters()
            if self._prev_disk_io and dt > 0:
                read_rate = (disk_io.read_bytes - self._prev_disk_io.read_bytes) / dt
                write_rate = (disk_io.write_bytes - self._prev_disk_io.write_bytes) / dt

                read_kbs = read_rate / 1024
                write_kbs = write_rate / 1024

                self._disk_read_history.append(read_kbs)
                self._disk_read_history.pop(0)
                self._disk_read_chart.set_data(self._disk_read_history)
                self._disk_read_chart_val.setText(self._fmt_rate(read_rate))

                self._disk_write_history.append(write_kbs)
                self._disk_write_history.pop(0)
                self._disk_write_chart.set_data(self._disk_write_history)
                self._disk_write_chart_val.setText(self._fmt_rate(write_rate))

            self._prev_disk_io = disk_io
        except Exception:
            pass

        # ── Per-Core CPU ──
        try:
            per_core = psutil.cpu_percent(percpu=True)
            for i, pct in enumerate(per_core):
                if i < len(self._core_bars):
                    self._core_bars[i].set_value(pct)
        except Exception:
            pass

        # ── Memory Breakdown ──
        try:
            used_gb = mem.used / (1024 ** 3)
            avail_gb = mem.available / (1024 ** 3)
            cached_bytes = getattr(mem, 'cached', 0)
            cached_gb = cached_bytes / (1024 ** 3)

            self._ram_bar.set_segments([
                {"label": f"Used {used_gb:.1f}G", "value": mem.used, "color": colors.accent_orange},
                {"label": f"Cached {cached_gb:.1f}G", "value": cached_bytes, "color": colors.accent_purple}
                    if cached_bytes else {},
                {"label": f"Free {avail_gb:.1f}G", "value": mem.available, "color": colors.accent_green},
            ])
            self._lbl_ram_used.setText(f"Used: {used_gb:.1f} GB")
            self._lbl_ram_avail.setText(f"Available: {avail_gb:.1f} GB")
            self._lbl_ram_cached.setText(f"Cached: {cached_gb:.1f} GB" if cached_bytes else "Cached: N/A")

            # Swap
            swap = psutil.swap_memory()
            swap_used_gb = swap.used / (1024 ** 3)
            swap_total_gb = swap.total / (1024 ** 3)
            swap_free_gb = swap.free / (1024 ** 3)

            if swap.total > 0:
                self._swap_bar.set_segments([
                    {"label": f"Used {swap_used_gb:.1f}G", "value": swap.used, "color": "#ff8c00"},
                    {"label": f"Free {swap_free_gb:.1f}G", "value": swap.free, "color": "#45b7d1"},
                ])
                self._lbl_swap.setText(
                    f"Swap: {swap_used_gb:.1f} / {swap_total_gb:.1f} GB ({swap.percent:.0f}%)"
                )
            else:
                self._lbl_swap.setText("Swap: Disabled")

        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════════════════════
    # SLOW UPDATE (every 5s)
    # ═══════════════════════════════════════════════════════════════════════════

    def _update_slow_stats(self):
        """Update process list and NEXUS brain stats."""
        self._update_process_table()
        self._update_brain_stats()

    def _update_process_table(self):
        """Populate the top processes table."""
        try:
            procs = []
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    info = p.info
                    procs.append(info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Sort by CPU descending, take top 15
            procs.sort(key=lambda x: x.get('cpu_percent', 0) or 0, reverse=True)
            top = procs[:15]

            self._proc_table.setRowCount(len(top))
            for row, p in enumerate(top):
                pid_item = QTableWidgetItem(str(p.get('pid', '')))
                name_item = QTableWidgetItem(str(p.get('name', 'unknown'))[:30])
                cpu_item = QTableWidgetItem(f"{p.get('cpu_percent', 0):.1f}")
                mem_item = QTableWidgetItem(f"{p.get('memory_percent', 0):.1f}")
                status_item = QTableWidgetItem(str(p.get('status', '')))

                # Color code CPU usage
                cpu_val = p.get('cpu_percent', 0) or 0
                if cpu_val >= 50:
                    cpu_item.setForeground(QColor("#ff4444"))
                elif cpu_val >= 10:
                    cpu_item.setForeground(QColor(colors.accent_orange))
                else:
                    cpu_item.setForeground(QColor(colors.text_primary))

                # Color code memory usage
                mem_val = p.get('memory_percent', 0) or 0
                if mem_val >= 10:
                    mem_item.setForeground(QColor("#ff4444"))
                elif mem_val >= 3:
                    mem_item.setForeground(QColor(colors.accent_purple))

                # Status coloring
                status = p.get('status', '')
                if status == 'running':
                    status_item.setForeground(QColor(colors.accent_green))
                elif status == 'sleeping':
                    status_item.setForeground(QColor(colors.text_secondary))
                elif status in ('zombie', 'dead'):
                    status_item.setForeground(QColor("#ff4444"))

                for col, item in enumerate([pid_item, name_item, cpu_item, mem_item, status_item]):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter if col != 1
                                         else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                    self._proc_table.setItem(row, col, item)

        except Exception:
            pass

    def _update_brain_stats(self):
        """Update NEXUS brain resource stats."""
        try:
            import os
            proc = psutil.Process(os.getpid())
            mem_info = proc.memory_info()
            brain_mb = mem_info.rss / (1024 ** 2)
            threads = proc.num_threads()

            self._stat_memory.set_value(f"{brain_mb:.0f} MB")
            self._stat_threads.set_value(str(threads))

            # Uptime
            create_time = proc.create_time()
            uptime_sec = time.time() - create_time
            self._stat_uptime.set_value(self._fmt_duration(uptime_sec))

            self._lbl_py_pid.setText(f"PID: {os.getpid()}")
            self._lbl_py_threads.setText(f"Threads: {threads}")

            try:
                open_files = len(proc.open_files())
                self._lbl_py_fds.setText(f"Open Files: {open_files}")
            except (psutil.AccessDenied, Exception):
                self._lbl_py_fds.setText("Open Files: N/A")

            # Subtitles with trend
            if brain_mb > 500:
                self._stat_memory.set_subtitle("⚠ High usage")
            elif brain_mb > 200:
                self._stat_memory.set_subtitle("Normal")
            else:
                self._stat_memory.set_subtitle("Light")

        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════════════════════
    # FORMATTING HELPERS
    # ═══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _fmt_rate(bytes_per_sec: float) -> str:
        """Format a byte rate to human readable."""
        if bytes_per_sec >= 1024 ** 3:
            return f"{bytes_per_sec / (1024 ** 3):.1f} GB/s"
        elif bytes_per_sec >= 1024 ** 2:
            return f"{bytes_per_sec / (1024 ** 2):.1f} MB/s"
        elif bytes_per_sec >= 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        else:
            return f"{bytes_per_sec:.0f} B/s"

    @staticmethod
    def _fmt_duration(seconds: float) -> str:
        """Format seconds to human readable duration."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds / 60:.0f}m {seconds % 60:.0f}s"
        elif seconds < 86400:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            return f"{h}h {m}m"
        else:
            d = int(seconds // 86400)
            h = int((seconds % 86400) // 3600)
            return f"{d}d {h}h"