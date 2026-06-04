"""
NEXUS AI — Connected Devices Panel
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Shows discovered network devices, their details, and available
interaction settings.

Layout:
  ┌─────────────────────────────────────────────────────────────────┐
  │ 🌐 Connected Devices                    [Scan Now] [Auto-scan] │
  ├──────────────┬──────────────────────────────────────────────────┤
  │  Device List │  📱 Device Detail                               │
  │              │                                                  │
  │  ● Phone     │  Name: Pixel 7                                  │
  │    Pixel 7   │  IP: 192.168.1.5                                │
  │              │  MAC: AA:BB:CC:DD:EE:FF                         │
  │  ● PC        │  Type: phone  │  OS: android                    │
  │    Desktop   │  Protocol: ADB                                  │
  │              │  Capabilities: shell, file_transfer, …           │
  │  ● Router    │  Open ports: 22, 80, 5555                        │
  │    Gateway   │  Last seen: 2 min ago                            │
  │              │                                                  │
  │              │  ── Quick Actions ──────────────────────         │
  │              │  [Ping]  [Shell]  [Send File]                   │
  └──────────────┴──────────────────────────────────────────────────┘
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QSplitter, QScrollArea, QSizePolicy,
    QListWidget, QListWidgetItem, QGridLayout, QTextEdit,
)
from PySide6.QtCore import Qt, QTimer, QSize, Signal
from PySide6.QtGui import QFont, QColor, QIcon

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ui.theme import theme, colors, fonts, spacing, animations, icons, NexusColors
from ui.widgets import PulsingDot, Section, StatCard
from utils.logger import get_logger

logger = get_logger("devices_panel")


# ═══════════════════════════════════════════════════════════════════════════════
# DEVICE TYPE ICONS
# ═══════════════════════════════════════════════════════════════════════════════

DEVICE_ICONS = {
    "phone": "📱",
    "tablet": "📱",
    "pc": "🖥️",
    "laptop": "💻",
    "router": "🌐",
    "iot": "🔌",
    "smart_tv": "📺",
    "printer": "🖨️",
    "server": "🗄️",
    "unknown": "❓",
}

PROTOCOL_LABELS = {
    "adb": ("ADB", colors.accent_green),
    "ssh": ("SSH", colors.accent_cyan),
    "ps_remote": ("PowerShell", colors.accent_purple),
    "http": ("HTTP", colors.warning),
    "none": ("None", colors.text_disabled),
}


# ═══════════════════════════════════════════════════════════════════════════════
# DEVICE CARD — compact card shown in the device list
# ═══════════════════════════════════════════════════════════════════════════════

class DeviceCard(QFrame):
    """Compact card representing a single device in the list."""

    clicked = Signal(str)  # emits device_id

    def __init__(self, device_data: dict, parent=None):
        super().__init__(parent)
        self._device_id = device_data.get("device_id", "")
        self._data = device_data
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(72)
        self._selected = False
        self._build(device_data)
        self._apply_style(False)

    def _build(self, d: dict):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Status dot
        self._dot = PulsingDot(colors.accent_green, 8)
        # Decide if online based on last_seen (within 5 minutes)
        try:
            ls = datetime.fromisoformat(d.get("last_seen", ""))
            diff = (datetime.now() - ls).total_seconds()
            online = diff < 300
        except Exception:
            online = False
        self._dot.set_active(online)
        self._dot.set_color(colors.accent_green if online else colors.text_disabled)
        layout.addWidget(self._dot)

        # Icon
        dtype = d.get("device_type", "unknown")
        icon_label = QLabel(DEVICE_ICONS.get(dtype, "❓"))
        icon_label.setFont(QFont(fonts.family_primary, 22))
        icon_label.setFixedWidth(32)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # Info column
        info = QVBoxLayout()
        info.setSpacing(2)

        name = d.get("friendly_name") or d.get("hostname") or d.get("ip_address", "Unknown")
        name_label = QLabel(name)
        name_label.setFont(QFont(fonts.family_primary, fonts.size_sm, QFont.Weight.Bold))
        name_label.setStyleSheet(f"color: {colors.text_primary}; background: transparent;")
        info.addWidget(name_label)

        # Subtitle: IP + type
        sub = f"{d.get('ip_address', '?')}  ·  {dtype}"
        sub_label = QLabel(sub)
        sub_label.setFont(QFont(fonts.family_mono, 9))
        sub_label.setStyleSheet(f"color: {colors.text_muted}; background: transparent;")
        info.addWidget(sub_label)

        layout.addLayout(info, 1)

        # Protocol badge
        proto = d.get("connection_protocol", "none")
        proto_label_text, proto_color = PROTOCOL_LABELS.get(proto, ("?", colors.text_disabled))
        badge = QLabel(proto_label_text)
        badge.setFont(QFont(fonts.family_mono, 9, QFont.Weight.Bold))
        badge.setStyleSheet(
            f"color: {proto_color}; background: {NexusColors.hex_to_rgba(proto_color, 0.15)}; "
            f"border: 1px solid {NexusColors.hex_to_rgba(proto_color, 0.3)}; "
            f"border-radius: 6px; padding: 2px 8px;"
        )
        badge.setFixedHeight(22)
        layout.addWidget(badge)

    def _apply_style(self, selected: bool):
        border = colors.accent_cyan if selected else colors.border_default
        bg = NexusColors.hex_to_rgba(colors.accent_cyan, 0.08) if selected else colors.bg_surface
        self.setStyleSheet(
            f"DeviceCard {{ background-color: {bg}; "
            f"border: 1px solid {border}; "
            f"border-radius: {spacing.border_radius}px; }}"
        )

    def set_selected(self, selected: bool):
        self._selected = selected
        self._apply_style(selected)

    def mousePressEvent(self, event):
        self.clicked.emit(self._device_id)
        super().mousePressEvent(event)


# ═══════════════════════════════════════════════════════════════════════════════
# DETAIL PANEL — right side showing full device info
# ═══════════════════════════════════════════════════════════════════════════════

class DeviceDetailPanel(QFrame):
    """Detailed view for a selected device."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"DeviceDetailPanel {{ background-color: {colors.bg_dark}; "
            f"border: none; }}"
        )
        self._device = None
        self._build_empty()

    def _build_empty(self):
        """Show the empty state."""
        self._clear()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("🌐")
        icon.setFont(QFont(fonts.family_primary, 48))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("background: transparent;")
        layout.addWidget(icon)

        msg = QLabel("Select a device to view details")
        msg.setFont(QFont(fonts.family_primary, fonts.size_md))
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet(f"color: {colors.text_muted}; background: transparent;")
        layout.addWidget(msg)

    def _clear(self):
        """Remove all child widgets."""
        if self.layout():
            while self.layout().count():
                child = self.layout().takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
                elif child.layout():
                    # Recursively clear sub-layouts
                    while child.layout().count():
                        sub = child.layout().takeAt(0)
                        if sub.widget():
                            sub.widget().deleteLater()

    def show_device(self, device: dict):
        """Populate the panel with device data."""
        self._device = device
        # Remove old layout
        old = self.layout()
        if old:
            self._clear()
            from PySide6.QtWidgets import QWidget as _QW
            _QW().setLayout(old)  # orphan old layout

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ background: transparent; border: none; }}"
        )

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        # ── Header ──
        header = QHBoxLayout()
        header.setSpacing(12)

        dtype = device.get("device_type", "unknown")
        icon_lbl = QLabel(DEVICE_ICONS.get(dtype, "❓"))
        icon_lbl.setFont(QFont(fonts.family_primary, 36))
        icon_lbl.setStyleSheet("background: transparent;")
        header.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        name = device.get("friendly_name") or device.get("hostname") or device.get("ip_address", "Unknown")
        title = QLabel(name)
        title.setFont(QFont(fonts.family_primary, fonts.size_xl, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {colors.accent_cyan}; background: transparent;")
        title_col.addWidget(title)

        subtitle = QLabel(f"{dtype.replace('_', ' ').title()}  ·  {device.get('device_os', 'unknown').title()}")
        subtitle.setFont(QFont(fonts.family_primary, fonts.size_sm))
        subtitle.setStyleSheet(f"color: {colors.text_secondary}; background: transparent;")
        title_col.addWidget(subtitle)

        header.addLayout(title_col, 1)
        layout.addLayout(header)

        # ── Separator ──
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {colors.border_subtle};")
        layout.addWidget(sep)

        # ── Info Grid ──
        info_sec = Section("Network Info", "🔗", expanded=True)
        grid = QGridLayout()
        grid.setSpacing(8)
        grid.setColumnMinimumWidth(0, 120)

        rows = [
            ("IP Address", device.get("ip_address", "—")),
            ("MAC Address", device.get("mac_address", "—")),
            ("Hostname", device.get("hostname", "—")),
            ("Device ID", device.get("device_id", "—")),
            ("Protocol", device.get("connection_protocol", "none").upper()),
            ("Last Seen", self._fmt_time(device.get("last_seen", ""))),
            ("First Seen", self._fmt_time(device.get("first_seen", ""))),
            ("Commands Run", str(device.get("commands_executed", 0))),
        ]

        for i, (label, value) in enumerate(rows):
            lbl = QLabel(label)
            lbl.setFont(QFont(fonts.family_primary, fonts.size_sm))
            lbl.setStyleSheet(f"color: {colors.text_muted}; background: transparent;")
            grid.addWidget(lbl, i, 0)

            val = QLabel(value)
            val.setFont(QFont(fonts.family_mono, fonts.size_sm))
            val.setStyleSheet(f"color: {colors.text_primary}; background: transparent;")
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(val, i, 1)

        info_sec.add_layout(grid)
        layout.addWidget(info_sec)

        # ── Open Ports ──
        ports = device.get("open_ports", [])
        if ports:
            port_sec = Section("Open Ports", "🔓", expanded=True)
            port_flow = QHBoxLayout()
            port_flow.setSpacing(6)
            for p in ports[:20]:  # cap at 20
                badge = QLabel(str(p))
                badge.setFont(QFont(fonts.family_mono, 9, QFont.Weight.Bold))
                badge.setStyleSheet(
                    f"color: {colors.accent_green}; "
                    f"background: {NexusColors.hex_to_rgba(colors.accent_green, 0.12)}; "
                    f"border: 1px solid {NexusColors.hex_to_rgba(colors.accent_green, 0.3)}; "
                    f"border-radius: 4px; padding: 2px 8px;"
                )
                badge.setFixedHeight(22)
                port_flow.addWidget(badge)
            port_flow.addStretch()
            port_sec.add_layout(port_flow)
            layout.addWidget(port_sec)

        # ── Capabilities ──
        caps = device.get("capabilities", [])
        if caps:
            cap_sec = Section("Capabilities", "⚡", expanded=True)
            cap_flow = QHBoxLayout()
            cap_flow.setSpacing(6)
            for c in caps:
                badge = QLabel(c.replace("_", " ").title())
                badge.setFont(QFont(fonts.family_primary, 9, QFont.Weight.Bold))
                badge.setStyleSheet(
                    f"color: {colors.accent_purple}; "
                    f"background: {NexusColors.hex_to_rgba(colors.accent_purple, 0.12)}; "
                    f"border: 1px solid {NexusColors.hex_to_rgba(colors.accent_purple, 0.3)}; "
                    f"border-radius: 4px; padding: 2px 8px;"
                )
                badge.setFixedHeight(22)
                cap_flow.addWidget(badge)
            cap_flow.addStretch()
            cap_sec.add_layout(cap_flow)
            layout.addWidget(cap_sec)

        # ── Last Command ──
        last_cmd = device.get("last_command", "")
        if last_cmd:
            cmd_sec = Section("Last Command", "💻", expanded=False)
            cmd_text = QLabel(last_cmd)
            cmd_text.setFont(QFont(fonts.family_mono, fonts.size_sm))
            cmd_text.setWordWrap(True)
            cmd_text.setStyleSheet(
                f"color: {colors.text_primary}; background: {colors.bg_medium}; "
                f"border-radius: 6px; padding: 8px;"
            )
            cmd_sec.add_widget(cmd_text)
            layout.addWidget(cmd_sec)

        # ── Quick Actions ──
        action_sec = Section("Quick Actions", "🚀", expanded=True)
        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        actions = [
            ("🏓 Ping", "ping"),
            ("💻 Shell", "shell"),
            ("📁 Send File", "send_file"),
        ]
        proto = device.get("connection_protocol", "none")
        for label, action_id in actions:
            btn = QPushButton(label)
            btn.setFixedHeight(34)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            enabled = proto != "none" or action_id == "ping"
            btn.setEnabled(enabled)
            btn.setProperty("cssClass", "primary" if enabled else "")
            if enabled:
                btn.setStyleSheet(
                    f"QPushButton {{ background: {NexusColors.hex_to_rgba(colors.accent_cyan, 0.15)}; "
                    f"color: {colors.accent_cyan}; border: 1px solid {NexusColors.hex_to_rgba(colors.accent_cyan, 0.4)}; "
                    f"border-radius: 6px; font-weight: 600; font-size: {fonts.size_sm}px; }} "
                    f"QPushButton:hover {{ background: {NexusColors.hex_to_rgba(colors.accent_cyan, 0.3)}; }}"
                )
            action_row.addWidget(btn)

        action_row.addStretch()
        action_sec.add_layout(action_row)
        layout.addWidget(action_sec)

        layout.addStretch()

        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _fmt_time(self, iso_str: str) -> str:
        """Convert ISO timestamp to relative time."""
        if not iso_str:
            return "—"
        try:
            dt = datetime.fromisoformat(iso_str)
            diff = (datetime.now() - dt).total_seconds()
            if diff < 60:
                return "just now"
            elif diff < 3600:
                return f"{int(diff // 60)} min ago"
            elif diff < 86400:
                return f"{int(diff // 3600)}h ago"
            else:
                return f"{int(diff // 86400)}d ago"
        except Exception:
            return iso_str[:19]


# ═══════════════════════════════════════════════════════════════════════════════
# DEVICES PANEL — main panel registered in the sidebar
# ═══════════════════════════════════════════════════════════════════════════════

class DevicesPanel(QFrame):
    """
    Connected Devices panel — lists discovered network devices, shows
    details, and exposes interaction controls.
    """

    def __init__(self, brain=None, parent=None):
        super().__init__(parent)
        self._brain = brain
        self._devices: Dict[str, dict] = {}
        self._cards: Dict[str, DeviceCard] = {}
        self._selected_id: Optional[str] = None

        self.setStyleSheet(f"DevicesPanel {{ background-color: {colors.bg_dark}; }}")
        self._build_ui()

        # Auto-refresh every 10 s
        self._timer = QTimer(self)
        self._timer.setInterval(10_000)
        self._timer.timeout.connect(self._refresh_devices)

    # ═══════════════════════════════════════════════════════════════════════════
    # UI CONSTRUCTION
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Top Toolbar ──
        toolbar = QFrame()
        toolbar.setFixedHeight(56)
        toolbar.setStyleSheet(
            f"QFrame {{ background-color: {colors.bg_darkest}; "
            f"border-bottom: 1px solid {colors.border_subtle}; }}"
        )
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(20, 0, 20, 0)
        tb_layout.setSpacing(12)

        title = QLabel("🌐  Connected Devices")
        title.setFont(QFont(fonts.family_primary, fonts.size_lg, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {colors.text_primary}; background: transparent;")
        tb_layout.addWidget(title)

        tb_layout.addStretch()

        # Device count
        self._count_label = QLabel("0 devices")
        self._count_label.setFont(QFont(fonts.family_mono, fonts.size_sm))
        self._count_label.setStyleSheet(f"color: {colors.text_muted}; background: transparent;")
        tb_layout.addWidget(self._count_label)

        # Scan button
        self._scan_btn = QPushButton("🔍  Scan Now")
        self._scan_btn.setFixedHeight(34)
        self._scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._scan_btn.setStyleSheet(
            f"QPushButton {{ background: {NexusColors.hex_to_rgba(colors.accent_cyan, 0.15)}; "
            f"color: {colors.accent_cyan}; border: 1px solid {NexusColors.hex_to_rgba(colors.accent_cyan, 0.4)}; "
            f"border-radius: 6px; padding: 0 16px; font-weight: 600; font-size: {fonts.size_sm}px; }} "
            f"QPushButton:hover {{ background: {NexusColors.hex_to_rgba(colors.accent_cyan, 0.3)}; }}"
        )
        self._scan_btn.clicked.connect(self._on_scan)
        tb_layout.addWidget(self._scan_btn)

        outer.addWidget(toolbar)

        # ── Splitter: list | detail ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(
            f"QSplitter::handle {{ background-color: {colors.border_subtle}; width: 1px; }}"
        )

        # LEFT: device list
        list_frame = QFrame()
        list_frame.setStyleSheet(
            f"QFrame {{ background-color: {colors.bg_dark}; border: none; }}"
        )
        list_layout = QVBoxLayout(list_frame)
        list_layout.setContentsMargins(8, 8, 4, 8)
        list_layout.setSpacing(6)

        # Scroll area for device cards
        self._list_scroll = QScrollArea()
        self._list_scroll.setWidgetResizable(True)
        self._list_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )
        self._list_container = QWidget()
        self._list_container.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)
        self._list_layout.addStretch()

        self._list_scroll.setWidget(self._list_container)
        list_layout.addWidget(self._list_scroll)

        # Empty state label
        self._empty_label = QLabel("No devices discovered yet.\nClick 'Scan Now' to search the network.")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setFont(QFont(fonts.family_primary, fonts.size_sm))
        self._empty_label.setStyleSheet(f"color: {colors.text_disabled}; background: transparent;")
        self._empty_label.setWordWrap(True)
        list_layout.addWidget(self._empty_label)

        splitter.addWidget(list_frame)

        # RIGHT: detail panel
        self._detail = DeviceDetailPanel()
        splitter.addWidget(self._detail)

        splitter.setSizes([300, 700])
        outer.addWidget(splitter, 1)

    # ═══════════════════════════════════════════════════════════════════════════
    # DATA
    # ═══════════════════════════════════════════════════════════════════════════

    def _refresh_devices(self):
        """Load device data from NetworkMesh."""
        try:
            from body.network_mesh import NetworkMesh
            mesh = NetworkMesh()
            device_list = mesh.get_devices(online_only=False)
            devices = {d.device_id: d.to_dict() for d in device_list}
        except Exception as e:
            logger.debug(f"Cannot load devices: {e}")
            devices = {}

        self._devices = devices
        self._rebuild_list()

    def _rebuild_list(self):
        """Recreate device cards from current data."""
        # Remove old cards
        for card in self._cards.values():
            card.setParent(None)
            card.deleteLater()
        self._cards.clear()

        # Remove stretch
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            # stretch items have no widget
            if item.widget():
                item.widget().setParent(None)

        if not self._devices:
            self._empty_label.show()
            self._count_label.setText("0 devices")
            self._list_layout.addStretch()
            return

        self._empty_label.hide()
        self._count_label.setText(f"{len(self._devices)} device{'s' if len(self._devices) != 1 else ''}")

        for dev_id, dev_data in sorted(self._devices.items(), key=lambda x: x[1].get("ip_address", "")):
            card = DeviceCard(dev_data)
            card.clicked.connect(self._on_device_selected)
            if dev_id == self._selected_id:
                card.set_selected(True)
            self._cards[dev_id] = card
            self._list_layout.addWidget(card)

        self._list_layout.addStretch()

    def _on_device_selected(self, device_id: str):
        """Handle device card click."""
        # Deselect previous
        if self._selected_id and self._selected_id in self._cards:
            self._cards[self._selected_id].set_selected(False)

        self._selected_id = device_id
        if device_id in self._cards:
            self._cards[device_id].set_selected(True)

        if device_id in self._devices:
            self._detail.show_device(self._devices[device_id])

    def _on_scan(self):
        """Trigger a manual network scan."""
        self._scan_btn.setText("⏳ Scanning…")
        self._scan_btn.setEnabled(False)

        # Run scan in background thread to avoid blocking UI
        import threading

        def _do_scan():
            try:
                from body.network_mesh import NetworkMesh
                mesh = NetworkMesh()
                mesh.scan()
            except Exception as e:
                logger.error(f"Scan failed: {e}")
            finally:
                # Schedule UI update back on main thread
                QTimer.singleShot(0, self._scan_complete)

        threading.Thread(target=_do_scan, daemon=True, name="device-scan").start()

    def _scan_complete(self):
        """Called after scan finishes."""
        self._scan_btn.setText("🔍  Scan Now")
        self._scan_btn.setEnabled(True)
        self._refresh_devices()

    # ═══════════════════════════════════════════════════════════════════════════
    # BRAIN INTERFACE
    # ═══════════════════════════════════════════════════════════════════════════

    def set_brain(self, brain):
        self._brain = brain

    def on_shown(self):
        """Called when the panel becomes visible."""
        self._refresh_devices()
        if not self._timer.isActive():
            self._timer.start()

    def on_hidden(self):
        """Called when the panel is hidden."""
        self._timer.stop()
