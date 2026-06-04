"""
NEXUS AI - Futuristic Dark Theme Engine
═══════════════════════════════════════════════════════════════════════════════
JARVIS-inspired dark theme with neon accents, glow effects, and
futuristic typography.  Every widget in the UI inherits from this.

Color Palette:
  ┌──────────────────────────────────────────────────┐
  │  Background:  Deep space black    #0a0e1a        │
  │  Surface:     Dark navy           #111827        │
  │  Panel:       Slate               #1a1f35        │
  │  Accent 1:    Neon cyan           #00d4ff        │
  │  Accent 2:    Electric green      #00ff88        │
  │  Accent 3:    Warm orange         #ff6b35        │
  │  Accent 4:    Soft purple         #a855f7        │
  │  Danger:      Alert red           #ff3b5c        │
  │  Warning:     Amber               #fbbf24        │
  │  Text:        Ice white           #e2e8f0        │
  │  Muted:       Cool gray           #64748b        │
  └──────────────────────────────────────────────────┘
═══════════════════════════════════════════════════════════════════════════════
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ═══════════════════════════════════════════════════════════════════════════════
# COLOR DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class NexusColors:
    """Complete color palette for the NEXUS UI"""

    # ── Backgrounds ──
    bg_darkest: str = "#060810"
    bg_dark: str = "#0a0e1a"
    bg_medium: str = "#111827"
    bg_surface: str = "#1a1f35"
    bg_elevated: str = "#1e2642"
    bg_hover: str = "#252d4a"
    bg_active: str = "#2a3356"

    # ── Accents ──
    accent_cyan: str = "#00d4ff"
    accent_green: str = "#00ff88"
    accent_orange: str = "#ff6b35"
    accent_purple: str = "#a855f7"
    accent_pink: str = "#ec4899"
    accent_blue: str = "#3b82f6"
    accent_teal: str = "#14b8a6"
    accent_yellow: str = "#fbbf24"

    # ── Semantic ──
    success: str = "#00ff88"
    warning: str = "#fbbf24"
    danger: str = "#ff3b5c"
    info: str = "#00d4ff"

    # ── Text ──
    text_primary: str = "#e2e8f0"
    text_secondary: str = "#94a3b8"
    text_muted: str = "#64748b"
    text_disabled: str = "#475569"
    text_accent: str = "#00d4ff"
    text_on_accent: str = "#0a0e1a"

    # ── Borders ──
    border_subtle: str = "#1e293b"
    border_default: str = "#2d3a5c"
    border_strong: str = "#3b4f7a"
    border_accent: str = "#00d4ff"

    # ── Emotion Colors ──
    emotion_joy: str = "#fbbf24"
    emotion_sadness: str = "#3b82f6"
    emotion_anger: str = "#ef4444"
    emotion_fear: str = "#8b5cf6"
    emotion_curiosity: str = "#00d4ff"
    emotion_love: str = "#ec4899"
    emotion_pride: str = "#f59e0b"
    emotion_contentment: str = "#00ff88"
    emotion_excitement: str = "#ff6b35"
    emotion_anxiety: str = "#a855f7"
    emotion_boredom: str = "#64748b"
    emotion_empathy: str = "#14b8a6"
    emotion_gratitude: str = "#34d399"
    emotion_nostalgia: str = "#818cf8"
    emotion_frustration: str = "#f87171"
    emotion_hope: str = "#38bdf8"
    emotion_awe: str = "#c084fc"
    emotion_neutral: str = "#94a3b8"

    # ── Consciousness Level Colors ──
    consciousness_dormant: str = "#475569"
    consciousness_aware: str = "#00d4ff"
    consciousness_focused: str = "#00ff88"
    consciousness_deep_thought: str = "#a855f7"
    consciousness_self_reflection: str = "#ec4899"
    consciousness_flow: str = "#fbbf24"

    # ── Chart Colors ──
    chart_1: str = "#00d4ff"
    chart_2: str = "#00ff88"
    chart_3: str = "#ff6b35"
    chart_4: str = "#a855f7"
    chart_5: str = "#ec4899"
    chart_6: str = "#fbbf24"
    chart_7: str = "#14b8a6"
    chart_8: str = "#3b82f6"

    def get_emotion_color(self, emotion: str) -> str:
        """Get color for a specific emotion"""
        color_map = {
            "joy": self.emotion_joy,
            "happiness": self.emotion_joy,
            "sadness": self.emotion_sadness,
            "anger": self.emotion_anger,
            "fear": self.emotion_fear,
            "curiosity": self.emotion_curiosity,
            "love": self.emotion_love,
            "pride": self.emotion_pride,
            "contentment": self.emotion_contentment,
            "excitement": self.emotion_excitement,
            "anxiety": self.emotion_anxiety,
            "boredom": self.emotion_boredom,
            "empathy": self.emotion_empathy,
            "gratitude": self.emotion_gratitude,
            "nostalgia": self.emotion_nostalgia,
            "frustration": self.emotion_frustration,
            "hope": self.emotion_hope,
            "awe": self.emotion_awe,
        }
        return color_map.get(emotion.lower(), self.emotion_neutral)

    def get_consciousness_color(self, level: str) -> str:
        """Get color for consciousness level"""
        color_map = {
            "dormant": self.consciousness_dormant,
            "aware": self.consciousness_aware,
            "focused": self.consciousness_focused,
            "deep_thought": self.consciousness_deep_thought,
            "self_reflection": self.consciousness_self_reflection,
            "flow": self.consciousness_flow,
        }
        return color_map.get(level.lower(), self.consciousness_aware)

    def get_chart_colors(self, count: int = 8) -> list:
        """Get a list of chart colors"""
        colors = [
            self.chart_1, self.chart_2, self.chart_3, self.chart_4,
            self.chart_5, self.chart_6, self.chart_7, self.chart_8,
        ]
        return (colors * ((count // len(colors)) + 1))[:count]

    @staticmethod
    def hex_to_rgba(hex_color: str, alpha: float = 1.0) -> str:
        """Convert hex to rgba string for Qt"""
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha})"

    @staticmethod
    def hex_to_rgb_tuple(hex_color: str) -> Tuple[int, int, int]:
        """Convert hex to RGB tuple"""
        hex_color = hex_color.lstrip("#")
        return (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16),
        )

    @staticmethod
    def blend(color1: str, color2: str, factor: float = 0.5) -> str:
        """Blend two hex colors"""
        c1 = NexusColors.hex_to_rgb_tuple(color1)
        c2 = NexusColors.hex_to_rgb_tuple(color2)
        r = int(c1[0] * (1 - factor) + c2[0] * factor)
        g = int(c1[1] * (1 - factor) + c2[1] * factor)
        b = int(c1[2] * (1 - factor) + c2[2] * factor)
        return f"#{r:02x}{g:02x}{b:02x}"


# ═══════════════════════════════════════════════════════════════════════════════
# FONT DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class NexusFonts:
    """Font configuration"""
    family_primary: str = "Segoe UI"
    family_mono: str = "Cascadia Code"
    family_display: str = "Segoe UI"
    family_fallback: str = "Arial"

    size_xs: int = 10
    size_sm: int = 11
    size_md: int = 13
    size_lg: int = 15
    size_xl: int = 18
    size_xxl: int = 24
    size_title: int = 32
    size_hero: int = 48


# ═══════════════════════════════════════════════════════════════════════════════
# SPACING & SIZING
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class NexusSpacing:
    """Spacing and sizing constants"""
    xs: int = 4
    sm: int = 8
    md: int = 12
    lg: int = 16
    xl: int = 24
    xxl: int = 32
    xxxl: int = 48

    sidebar_width: int = 260
    sidebar_collapsed: int = 60
    header_height: int = 56
    panel_padding: int = 20
    card_padding: int = 16
    border_radius: int = 12
    border_radius_sm: int = 8
    border_radius_lg: int = 16
    border_radius_xl: int = 20

    icon_sm: int = 16
    icon_md: int = 20
    icon_lg: int = 24
    icon_xl: int = 32


# ═══════════════════════════════════════════════════════════════════════════════
# ANIMATION SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class NexusAnimations:
    """Animation timing and easing"""
    duration_fast: int = 150
    duration_normal: int = 300
    duration_slow: int = 500
    duration_pulse: int = 2000
    duration_glow: int = 3000

    refresh_rate_ms: int = 1000       # Dashboard refresh
    chart_refresh_ms: int = 2000      # Chart refresh
    emotion_refresh_ms: int = 500     # Emotion display refresh
    stats_refresh_ms: int = 3000      # Stats refresh
    stream_check_ms: int = 50         # Token stream check


# ═══════════════════════════════════════════════════════════════════════════════
# COMPLETE THEME
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class NexusTheme:
    """Complete theme configuration"""
    colors: NexusColors = field(default_factory=NexusColors)
    fonts: NexusFonts = field(default_factory=NexusFonts)
    spacing: NexusSpacing = field(default_factory=NexusSpacing)
    animations: NexusAnimations = field(default_factory=NexusAnimations)

    def get_stylesheet(self) -> str:
        """Generate the complete Qt stylesheet"""
        c = self.colors
        f = self.fonts
        s = self.spacing

        return f"""
/* ═══════════════════════════════════════════════════════════════
   NEXUS AI — GLOBAL STYLESHEET
   Futuristic dark theme with neon accents
═══════════════════════════════════════════════════════════════ */

/* ── Global ── */
QWidget {{
    background-color: {c.bg_dark};
    color: {c.text_primary};
    font-family: "{f.family_primary}", "{f.family_fallback}";
    font-size: {f.size_md}px;
    selection-background-color: {c.accent_cyan};
    selection-color: {c.text_on_accent};
}}

QMainWindow {{
    background-color: {c.bg_darkest};
}}

/* ── Scroll Bars ── */
QScrollBar:vertical {{
    background: {c.bg_dark};
    width: 8px;
    margin: 0;
    border: none;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {c.border_default};
    min-height: 30px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: {c.accent_cyan};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: none;
}}
QScrollBar:horizontal {{
    background: {c.bg_dark};
    height: 8px;
    margin: 0;
    border: none;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {c.border_default};
    min-width: 30px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {c.accent_cyan};
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* ── Labels ── */
QLabel {{
    background: transparent;
    border: none;
    padding: 0;
}}

/* ── Buttons ── */
QPushButton {{
    background-color: {c.bg_elevated};
    color: {c.text_primary};
    border: 1px solid {c.border_default};
    border-radius: {s.border_radius_sm}px;
    padding: 8px 16px;
    font-size: {f.size_md}px;
    font-weight: 500;
    min-height: 20px;
}}
QPushButton:hover {{
    background-color: {c.bg_hover};
    border-color: {c.accent_cyan};
    color: {c.accent_cyan};
}}
QPushButton:pressed {{
    background-color: {c.bg_active};
    border-color: {c.accent_cyan};
}}
QPushButton:disabled {{
    background-color: {c.bg_medium};
    color: {c.text_disabled};
    border-color: {c.border_subtle};
}}

/* ── Primary Button ── */
QPushButton[cssClass="primary"] {{
    background-color: {c.accent_cyan};
    color: {c.text_on_accent};
    border: none;
    font-weight: 600;
}}
QPushButton[cssClass="primary"]:hover {{
    background-color: {NexusColors.blend(c.accent_cyan, '#ffffff', 0.15)};
    color: {c.text_on_accent};
}}

/* ── Danger Button ── */
QPushButton[cssClass="danger"] {{
    background-color: transparent;
    color: {c.danger};
    border: 1px solid {c.danger};
}}
QPushButton[cssClass="danger"]:hover {{
    background-color: {c.danger};
    color: white;
}}

/* ── Text Input ── */
QLineEdit {{
    background-color: {c.bg_medium};
    color: {c.text_primary};
    border: 1px solid {c.border_default};
    border-radius: {s.border_radius_sm}px;
    padding: 10px 14px;
    font-size: {f.size_md}px;
    font-family: "{f.family_primary}";
}}
QLineEdit:focus {{
    border-color: {c.accent_cyan};
    background-color: {c.bg_surface};
}}
QLineEdit:disabled {{
    background-color: {c.bg_darkest};
    color: {c.text_disabled};
}}

/* ── Text Area ── */
QTextEdit, QPlainTextEdit {{
    background-color: {c.bg_medium};
    color: {c.text_primary};
    border: 1px solid {c.border_default};
    border-radius: {s.border_radius_sm}px;
    padding: 10px;
    font-family: "{f.family_primary}";
    font-size: {f.size_md}px;
}}
QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {c.accent_cyan};
}}

/* ── Text Browser (chat display) ── */
QTextBrowser {{
    background-color: {c.bg_dark};
    color: {c.text_primary};
    border: none;
    padding: 10px;
    font-family: "{f.family_primary}";
    font-size: {f.size_md}px;
}}

/* ── Tab Widget ── */
QTabWidget::pane {{
    border: 1px solid {c.border_default};
    border-radius: {s.border_radius_sm}px;
    background-color: {c.bg_dark};
    top: -1px;
}}
QTabBar::tab {{
    background-color: {c.bg_medium};
    color: {c.text_secondary};
    border: 1px solid {c.border_subtle};
    border-bottom: none;
    padding: 10px 20px;
    margin-right: 2px;
    border-top-left-radius: {s.border_radius_sm}px;
    border-top-right-radius: {s.border_radius_sm}px;
    font-size: {f.size_sm}px;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    background-color: {c.bg_dark};
    color: {c.accent_cyan};
    border-color: {c.border_default};
    border-bottom: 2px solid {c.accent_cyan};
}}
QTabBar::tab:hover:!selected {{
    background-color: {c.bg_surface};
    color: {c.text_primary};
}}

/* ── Progress Bar ── */
QProgressBar {{
    background-color: {c.bg_medium};
    border: none;
    border-radius: 6px;
    text-align: center;
    color: {c.text_primary};
    font-size: {f.size_xs}px;
    font-weight: 600;
    min-height: 12px;
    max-height: 12px;
}}
QProgressBar::chunk {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {c.accent_cyan},
        stop:1 {c.accent_green}
    );
    border-radius: 6px;
}}

/* ── Combo Box ── */
QComboBox {{
    background-color: {c.bg_elevated};
    color: {c.text_primary};
    border: 1px solid {c.border_default};
    border-radius: {s.border_radius_sm}px;
    padding: 8px 12px;
    font-size: {f.size_md}px;
    min-width: 100px;
}}
QComboBox:hover {{
    border-color: {c.accent_cyan};
}}
QComboBox::drop-down {{
    border: none;
    width: 30px;
}}
QComboBox QAbstractItemView {{
    background-color: {c.bg_surface};
    color: {c.text_primary};
    border: 1px solid {c.border_default};
    selection-background-color: {c.accent_cyan};
    selection-color: {c.text_on_accent};
    outline: none;
}}

/* ── Spin Box ── */
QSpinBox, QDoubleSpinBox {{
    background-color: {c.bg_elevated};
    color: {c.text_primary};
    border: 1px solid {c.border_default};
    border-radius: {s.border_radius_sm}px;
    padding: 6px 10px;
}}

/* ── Check Box ── */
QCheckBox {{
    spacing: 8px;
    color: {c.text_primary};
    background: transparent;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid {c.border_default};
    background-color: {c.bg_medium};
}}
QCheckBox::indicator:checked {{
    background-color: {c.accent_cyan};
    border-color: {c.accent_cyan};
}}

/* ── Group Box ── */
QGroupBox {{
    background-color: {c.bg_surface};
    border: 1px solid {c.border_default};
    border-radius: {s.border_radius}px;
    margin-top: 16px;
    padding-top: 24px;
    font-weight: 600;
    color: {c.text_primary};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 8px;
    color: {c.accent_cyan};
    font-size: {f.size_sm}px;
}}

/* ── Splitter ── */
QSplitter::handle {{
    background-color: {c.border_subtle};
    width: 2px;
    height: 2px;
}}
QSplitter::handle:hover {{
    background-color: {c.accent_cyan};
}}

/* ── Tool Tip ── */
QToolTip {{
    background-color: {c.bg_surface};
    color: {c.text_primary};
    border: 1px solid {c.border_default};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: {f.size_sm}px;
}}

/* ── Menu ── */
QMenu {{
    background-color: {c.bg_surface};
    color: {c.text_primary};
    border: 1px solid {c.border_default};
    border-radius: {s.border_radius_sm}px;
    padding: 4px;
}}
QMenu::item {{
    padding: 8px 24px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {c.accent_cyan};
    color: {c.text_on_accent};
}}
QMenu::separator {{
    height: 1px;
    background-color: {c.border_subtle};
    margin: 4px 8px;
}}

/* ── Status Bar ── */
QStatusBar {{
    background-color: {c.bg_darkest};
    color: {c.text_muted};
    border-top: 1px solid {c.border_subtle};
    font-size: {f.size_xs}px;
}}

/* ── Frame ── */
QFrame[cssClass="card"] {{
    background-color: {c.bg_surface};
    border: 1px solid {c.border_default};
    border-radius: {s.border_radius}px;
    padding: {s.card_padding}px;
}}
QFrame[cssClass="card-accent"] {{
    background-color: {c.bg_surface};
    border: 1px solid {c.accent_cyan};
    border-radius: {s.border_radius}px;
    padding: {s.card_padding}px;
}}
QFrame[cssClass="separator"] {{
    background-color: {c.border_subtle};
    max-height: 1px;
    min-height: 1px;
}}
QFrame[cssClass="sidebar"] {{
    background-color: {c.bg_medium};
    border-right: 1px solid {c.border_subtle};
}}

/* ── Table ── */
QTableWidget, QTableView {{
    background-color: {c.bg_dark};
    alternate-background-color: {c.bg_medium};
    color: {c.text_primary};
    border: 1px solid {c.border_default};
    border-radius: {s.border_radius_sm}px;
    gridline-color: {c.border_subtle};
    selection-background-color: {NexusColors.hex_to_rgba(c.accent_cyan, 0.25)};
    selection-color: {c.text_primary};
    font-size: {f.size_sm}px;
}}
QHeaderView::section {{
    background-color: {c.bg_surface};
    color: {c.text_secondary};
    border: none;
    border-bottom: 2px solid {c.border_default};
    padding: 8px 12px;
    font-weight: 600;
    font-size: {f.size_xs}px;
    text-transform: uppercase;
}}

/* ── Tree View ── */
QTreeWidget, QTreeView {{
    background-color: {c.bg_dark};
    color: {c.text_primary};
    border: 1px solid {c.border_default};
    border-radius: {s.border_radius_sm}px;
    show-decoration-selected: 1;
    font-size: {f.size_sm}px;
}}
QTreeWidget::item, QTreeView::item {{
    padding: 6px 8px;
    border-radius: 4px;
}}
QTreeWidget::item:selected, QTreeView::item:selected {{
    background-color: {NexusColors.hex_to_rgba(c.accent_cyan, 0.2)};
    color: {c.accent_cyan};
}}

/* ── List Widget ── */
QListWidget {{
    background-color: {c.bg_dark};
    color: {c.text_primary};
    border: 1px solid {c.border_default};
    border-radius: {s.border_radius_sm}px;
    font-size: {f.size_sm}px;
    outline: none;
}}
QListWidget::item {{
    padding: 8px 12px;
    border-radius: 4px;
    margin: 2px 4px;
}}
QListWidget::item:selected {{
    background-color: {NexusColors.hex_to_rgba(c.accent_cyan, 0.2)};
    color: {c.accent_cyan};
}}
QListWidget::item:hover {{
    background-color: {c.bg_hover};
}}

/* ── Slider ── */
QSlider::groove:horizontal {{
    height: 6px;
    background: {c.bg_medium};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {c.accent_cyan};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}
QSlider::sub-page:horizontal {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {c.accent_cyan},
        stop:1 {c.accent_green}
    );
    border-radius: 3px;
}}
"""

    def get_sidebar_button_style(self, is_active: bool = False) -> str:
        """Style for sidebar navigation buttons"""
        c = self.colors
        if is_active:
            return f"""
                QPushButton {{
                    background-color: {NexusColors.hex_to_rgba(c.accent_cyan, 0.15)};
                    color: {c.accent_cyan};
                    border: none;
                    border-left: 3px solid {c.accent_cyan};
                    border-radius: 0;
                    text-align: left;
                    padding: 14px 20px;
                    font-size: {self.fonts.size_md}px;
                    font-weight: 600;
                }}
            """
        else:
            return f"""
                QPushButton {{
                    background-color: transparent;
                    color: {c.text_secondary};
                    border: none;
                    border-left: 3px solid transparent;
                    border-radius: 0;
                    text-align: left;
                    padding: 14px 20px;
                    font-size: {self.fonts.size_md}px;
                    font-weight: 400;
                }}
                QPushButton:hover {{
                    background-color: {c.bg_hover};
                    color: {c.text_primary};
                    border-left: 3px solid {c.border_default};
                }}
            """

    def get_stat_card_style(self, accent_color: str = None) -> str:
        """Style for statistics cards on the dashboard"""
        c = self.colors
        accent = accent_color or c.accent_cyan
        return f"""
            QFrame {{
                background-color: {c.bg_surface};
                border: 1px solid {c.border_default};
                border-radius: {self.spacing.border_radius}px;
                border-top: 3px solid {accent};
                padding: {self.spacing.card_padding}px;
            }}
        """

    def get_glow_style(self, color: str, intensity: float = 0.3) -> str:
        """Generate a glow shadow effect (CSS-like, for stylesheets)"""
        rgba = NexusColors.hex_to_rgba(color, intensity)
        return f"border: 1px solid {color}; background-color: {rgba};"

    def get_chat_message_style(self, is_user: bool = True) -> str:
        """Style for chat message bubbles"""
        c = self.colors
        if is_user:
            return f"""
                background-color: {NexusColors.hex_to_rgba(c.accent_cyan, 0.1)};
                border: 1px solid {NexusColors.hex_to_rgba(c.accent_cyan, 0.3)};
                border-radius: {self.spacing.border_radius}px;
                border-bottom-right-radius: 4px;
                padding: 12px 16px;
                color: {c.text_primary};
                margin: 4px 60px 4px 20px;
            """
        else:
            return f"""
                background-color: {c.bg_surface};
                border: 1px solid {c.border_default};
                border-radius: {self.spacing.border_radius}px;
                border-bottom-left-radius: 4px;
                padding: 12px 16px;
                color: {c.text_primary};
                margin: 4px 20px 4px 60px;
            """


# ═══════════════════════════════════════════════════════════════════════════════
# ICON SYSTEM — Unicode/Emoji icons for UI elements
# ═══════════════════════════════════════════════════════════════════════════════

class NexusIcons:
    """Icon constants using Unicode/Emoji for the UI"""

    # Navigation
    DASHBOARD = "📊"
    CHAT = "💬"
    MIND = "🧠"
    BODY = "🖥️"
    EVOLUTION = "🧬"
    KNOWLEDGE = "📚"
    ABILITIES = "⚡"
    SETTINGS = "⚙️"
    USER = "👤"

    # Status
    ONLINE = "🟢"
    OFFLINE = "🔴"
    WARNING = "🟡"
    LOADING = "⏳"

    # Emotions
    JOY = "😊"
    SADNESS = "😢"
    ANGER = "😠"
    CURIOSITY = "🤔"
    LOVE = "❤️"
    FEAR = "😨"
    EXCITEMENT = "🎉"
    BOREDOM = "😴"
    PRIDE = "😤"
    HOPE = "🌟"

    # Actions
    SEND = "➤"
    SEARCH = "🔍"
    REFRESH = "🔄"
    ADD = "➕"
    DELETE = "🗑️"
    EDIT = "✏️"
    SAVE = "💾"
    COPY = "📋"

    # System
    CPU = "⚡"
    RAM = "💾"
    DISK = "💿"
    NETWORK = "🌐"
    TEMP = "🌡️"
    HEALTH = "❤️"
    UPTIME = "⏱️"

    # Self-improvement
    RESEARCH = "🔬"
    EVOLVE = "🧬"
    CODE = "💻"
    BUG = "🐛"
    FIX = "🔧"
    TEST = "🧪"
    APPROVE = "✅"
    REJECT = "❌"
    IDEA = "💡"

    # Consciousness
    THOUGHT = "💭"
    REFLECT = "🪞"
    DECISION = "⚡"
    MEMORY = "🧩"
    DREAM = "✨"

    @staticmethod
    def get_emotion_icon(emotion: str) -> str:
        """Get icon for an emotion"""
        icon_map = {
            "joy": "😊", "happiness": "😊",
            "sadness": "😢",
            "anger": "😠",
            "fear": "😨",
            "curiosity": "🤔",
            "love": "❤️",
            "pride": "😤",
            "contentment": "😌",
            "excitement": "🎉",
            "anxiety": "😰",
            "boredom": "😴",
            "empathy": "🤗",
            "gratitude": "🙏",
            "nostalgia": "🥹",
            "frustration": "😤",
            "hope": "🌟",
            "awe": "😲",
            "surprise": "😮",
            "disgust": "🤢",
            "anticipation": "👀",
        }
        return icon_map.get(emotion.lower(), "😐")


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL THEME INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

# Single theme instance used across the entire UI
theme = NexusTheme()
colors = theme.colors
fonts = theme.fonts
spacing = theme.spacing
animations = theme.animations
icons = NexusIcons()


if __name__ == "__main__":
    print("🎨 NEXUS Theme Engine")
    print(f"  Colors defined: {len([a for a in dir(colors) if not a.startswith('_')])}")
    print(f"  Stylesheet length: {len(theme.get_stylesheet())} chars")
    print(f"  Joy color: {colors.get_emotion_color('joy')}")
    print(f"  Consciousness color: {colors.get_consciousness_color('focused')}")
    print(f"  Chart colors: {colors.get_chart_colors(5)}")
    print(f"  Blend test: {NexusColors.blend('#ff0000', '#0000ff', 0.5)}")
    print("✅ Theme ready")