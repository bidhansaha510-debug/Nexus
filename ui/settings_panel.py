"""
NEXUS AI - Advanced Settings Panel
═══════════════════════════════════════════════════════════════════════════════
Full configuration UI exposing every tunable parameter from config.py.

Sections:
  🤖  AI / LLM          — model, temperature, tokens, penalties
  🧠  Consciousness     — reflection, metacognition, inner voice
  ❤️  Emotions          — decay, mood, baseline, memory retention
  🎭  Personality       — Big Five + custom traits, voice style
  👁️  Monitoring        — tracking toggles, intervals
  🛠️  Self-Improvement  — code monitor, auto-fix, evolution
  🌐  Internet          — learning, browsing, knowledge base
  🖥️  Appearance        — theme, accent color, font, voice
  💾  Memory            — capacity, consolidation, forgetting
═══════════════════════════════════════════════════════════════════════════════
"""
import sys
from pathlib import Path
from functools import partial

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QComboBox,
    QCheckBox, QPushButton, QFormLayout, QScrollArea, QSlider,
    QSpinBox, QDoubleSpinBox, QLineEdit, QSizePolicy, QGraphicsOpacityEffect,
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont

from ui.theme import theme, colors, fonts, spacing, NexusColors
from ui.widgets import HeaderLabel, Section, Separator
from config import NEXUS_CONFIG, EmotionType

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER — Labeled slider row
# ═══════════════════════════════════════════════════════════════════════════════

class _SliderRow(QWidget):
    """
    Horizontal row:  Label ──── [slider] ──── value_label
    Supports float ranges via an internal integer scale.
    """

    def __init__(
        self,
        label: str,
        min_val: float,
        max_val: float,
        value: float,
        step: float = 0.01,
        suffix: str = "",
        decimals: int = 2,
        parent=None,
    ):
        super().__init__(parent)
        self._min = min_val
        self._max = max_val
        self._step = step
        self._suffix = suffix
        self._decimals = decimals
        self._scale = int(1 / step) if step < 1 else 1

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(12)

        # Label
        lbl = QLabel(label)
        lbl.setFont(QFont(fonts.family_primary, fonts.size_sm))
        lbl.setStyleSheet(f"color: {colors.text_secondary};")
        lbl.setFixedWidth(180)
        layout.addWidget(lbl)

        # Slider
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setMinimum(int(min_val * self._scale))
        self._slider.setMaximum(int(max_val * self._scale))
        self._slider.setValue(int(value * self._scale))
        self._slider.setSingleStep(1)
        self._slider.setMinimumWidth(160)
        self._slider.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self._slider, 1)

        # Value label
        self._value_label = QLabel()
        self._value_label.setFont(QFont(fonts.family_mono, fonts.size_sm))
        self._value_label.setStyleSheet(f"color: {colors.accent_cyan};")
        self._value_label.setFixedWidth(70)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._value_label)

        self._slider.valueChanged.connect(self._on_change)
        self._on_change(self._slider.value())

    # ── public ──
    def value(self) -> float:
        return self._slider.value() / self._scale

    def set_value(self, v: float):
        self._slider.setValue(int(v * self._scale))

    # ── private ──
    def _on_change(self, raw: int):
        v = raw / self._scale
        txt = f"{v:.{self._decimals}f}{self._suffix}"
        self._value_label.setText(txt)

class _SpinRow(QWidget):
    """Label + QSpinBox in a row."""

    def __init__(self, label: str, min_val: int, max_val: int, value: int, suffix: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(12)

        lbl = QLabel(label)
        lbl.setFont(QFont(fonts.family_primary, fonts.size_sm))
        lbl.setStyleSheet(f"color: {colors.text_secondary};")
        lbl.setFixedWidth(180)
        layout.addWidget(lbl)

        layout.addStretch()

        self._spin = QSpinBox()
        self._spin.setRange(min_val, max_val)
        self._spin.setValue(value)
        if suffix:
            self._spin.setSuffix(f" {suffix}")
        self._spin.setFixedWidth(140)
        self._spin.setStyleSheet(
            f"QSpinBox {{ background: {colors.bg_elevated}; color: {colors.text_primary}; "
            f"border: 1px solid {colors.border_default}; border-radius: 6px; padding: 5px 10px; }}"
            f"QSpinBox:focus {{ border-color: {colors.accent_cyan}; }}"
        )
        layout.addWidget(self._spin)

    def value(self) -> int:
        return self._spin.value()

    def set_value(self, v: int):
        self._spin.setValue(v)

class _ToggleRow(QWidget):
    """Label + styled toggle checkbox."""

    def __init__(self, label: str, checked: bool = True, description: str = "", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(2)

        row = QHBoxLayout()
        row.setSpacing(12)
        self._check = QCheckBox(label)
        self._check.setChecked(checked)
        self._check.setFont(QFont(fonts.family_primary, fonts.size_sm))
        self._check.setStyleSheet(f"color: {colors.text_primary};")
        self._check.setCursor(Qt.CursorShape.PointingHandCursor)
        row.addWidget(self._check)
        row.addStretch()
        layout.addLayout(row)

        if description:
            desc = QLabel(description)
            desc.setFont(QFont(fonts.family_primary, fonts.size_xs))
            desc.setStyleSheet(f"color: {colors.text_muted}; padding-left: 26px;")
            desc.setWordWrap(True)
            layout.addWidget(desc)

    def is_checked(self) -> bool:
        return self._check.isChecked()

    def set_checked(self, v: bool):
        self._check.setChecked(v)

class _ComboRow(QWidget):
    """Label + QComboBox."""

    def __init__(self, label: str, items: list, current: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(12)

        lbl = QLabel(label)
        lbl.setFont(QFont(fonts.family_primary, fonts.size_sm))
        lbl.setStyleSheet(f"color: {colors.text_secondary};")
        lbl.setFixedWidth(180)
        layout.addWidget(lbl)

        layout.addStretch()

        self._combo = QComboBox()
        self._combo.addItems(items)
        if current and current in items:
            self._combo.setCurrentText(current)
        self._combo.setFixedWidth(200)
        self._combo.setStyleSheet(
            f"QComboBox {{ background: {colors.bg_elevated}; color: {colors.text_primary}; "
            f"border: 1px solid {colors.border_default}; border-radius: 6px; padding: 6px 10px; }}"
            f"QComboBox:hover {{ border-color: {colors.accent_cyan}; }}"
            f"QComboBox QAbstractItemView {{ background: {colors.bg_surface}; color: {colors.text_primary}; "
            f"selection-background-color: {colors.accent_cyan}; selection-color: {colors.text_on_accent}; }}"
        )
        layout.addWidget(self._combo)

    def value(self) -> str:
        return self._combo.currentText()

    def set_value(self, v: str):
        self._combo.setCurrentText(v)

class _LineEditRow(QWidget):
    """Label + QLineEdit."""

    def __init__(self, label: str, text: str = "", placeholder: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(12)

        lbl = QLabel(label)
        lbl.setFont(QFont(fonts.family_primary, fonts.size_sm))
        lbl.setStyleSheet(f"color: {colors.text_secondary};")
        lbl.setFixedWidth(180)
        layout.addWidget(lbl)

        layout.addStretch()

        self._edit = QLineEdit(text)
        self._edit.setPlaceholderText(placeholder)
        self._edit.setFixedWidth(200)
        layout.addWidget(self._edit)

    def value(self) -> str:
        return self._edit.text()

    def set_value(self, v: str):
        self._edit.setText(v)

# ═══════════════════════════════════════════════════════════════════════════════
# SETTINGS PANEL
# ═══════════════════════════════════════════════════════════════════════════════

class SettingsPanel(QFrame):
    """
    Advanced system settings panel.
    Exposes every config parameter from NEXUS_CONFIG with categorized,
    collapsible sections inside a scroll area.
    """

    def __init__(self, brain=None, parent=None):
        super().__init__(parent)
        self._brain = brain
        self.setStyleSheet(f"background-color: {colors.bg_dark};")

        # Main layout holds the scroll area
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            f"QScrollArea {{ background: {colors.bg_dark}; border: none; }}"
        )

        container = QWidget()
        container.setStyleSheet(f"background: {colors.bg_dark};")
        self._layout = QVBoxLayout(container)
        self._layout.setContentsMargins(24, 24, 24, 24)
        self._layout.setSpacing(16)

        scroll.setWidget(container)
        outer.addWidget(scroll)

        # ── Build all sections ──
        self._build_header()
        self._build_llm_section()
        self._build_consciousness_section()
        self._build_emotions_section()
        self._build_personality_section()
        self._build_monitoring_section()
        self._build_self_improvement_section()
        self._build_internet_section()
        self._build_appearance_section()
        self._build_memory_section()
        self._build_action_bar()

        self._layout.addStretch()

        # Load current config
        self._load_from_config()

    # ═══════════════════════════════════════════════════════════════════════════
    # HEADER
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_header(self):
        self._layout.addWidget(HeaderLabel("System Settings", "⚙️", colors.accent_cyan))

        desc = QLabel("Configure every aspect of NEXUS — from LLM parameters and personality traits to memory and self-improvement behavior.")
        desc.setFont(QFont(fonts.family_primary, fonts.size_sm))
        desc.setStyleSheet(f"color: {colors.text_muted};")
        desc.setWordWrap(True)
        self._layout.addWidget(desc)
        self._layout.addWidget(Separator())

    # ═══════════════════════════════════════════════════════════════════════════
    # 1. AI / LLM
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_llm_section(self):
        sec = Section("AI / LLM Configuration", "🤖", expanded=True)

        self._llm_model = _ComboRow(
            "LLM Model",
            ["llama3:latest", "llama3:8b", "llama3:70b", "mistral", "gemma", "deepseek-r1:8b", "qwen2.5:latest", "phi3"],
            NEXUS_CONFIG.llm.model_name,
        )
        sec.add_widget(self._llm_model)

        self._llm_base_url = _LineEditRow("Ollama URL", NEXUS_CONFIG.llm.base_url, "http://localhost:11434")
        sec.add_widget(self._llm_base_url)

        sec.add_widget(Separator())

        self._llm_temperature = _SliderRow("Temperature", 0.0, 2.0, NEXUS_CONFIG.llm.temperature, 0.01, "", 2)
        sec.add_widget(self._llm_temperature)

        self._llm_top_p = _SliderRow("Top-P", 0.0, 1.0, NEXUS_CONFIG.llm.top_p, 0.01, "", 2)
        sec.add_widget(self._llm_top_p)

        self._llm_top_k = _SpinRow("Top-K", 1, 200, NEXUS_CONFIG.llm.top_k)
        sec.add_widget(self._llm_top_k)

        self._llm_repeat_penalty = _SliderRow("Repeat Penalty", 1.0, 2.0, NEXUS_CONFIG.llm.repeat_penalty, 0.01, "", 2)
        sec.add_widget(self._llm_repeat_penalty)

        sec.add_widget(Separator())

        self._llm_max_tokens = _SpinRow("Max Tokens", 256, 32768, NEXUS_CONFIG.llm.max_tokens, "tokens")
        sec.add_widget(self._llm_max_tokens)

        self._llm_ctx_window = _SpinRow("Context Window", 256, 131072, NEXUS_CONFIG.llm.context_window, "tokens")
        sec.add_widget(self._llm_ctx_window)

        self._llm_timeout = _SpinRow("Timeout", 0, 600, NEXUS_CONFIG.llm.timeout or 0, "sec")
        sec.add_widget(self._llm_timeout)

        self._layout.addWidget(sec)

    # ═══════════════════════════════════════════════════════════════════════════
    # 2. CONSCIOUSNESS
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_consciousness_section(self):
        sec = Section("Consciousness", "🧠", expanded=False)

        self._con_reflection = _SpinRow("Self-Reflection Interval", 5, 600, NEXUS_CONFIG.consciousness.self_reflection_interval, "sec")
        sec.add_widget(self._con_reflection)

        self._con_meta_depth = _SpinRow("Metacognition Depth", 1, 20, NEXUS_CONFIG.consciousness.metacognition_depth)
        sec.add_widget(self._con_meta_depth)

        self._con_inner_voice = _ToggleRow("Inner Voice", NEXUS_CONFIG.consciousness.inner_voice_enabled, "Enable the internal monologue stream")
        sec.add_widget(self._con_inner_voice)

        self._con_self_model = _SpinRow("Self-Model Update Interval", 10, 600, NEXUS_CONFIG.consciousness.self_model_update_interval, "sec")
        sec.add_widget(self._con_self_model)

        self._con_check = _SpinRow("Consciousness Check Interval", 1, 120, NEXUS_CONFIG.consciousness.consciousness_check_interval, "sec")
        sec.add_widget(self._con_check)

        self._layout.addWidget(sec)

    # ═══════════════════════════════════════════════════════════════════════════
    # 3. EMOTIONS
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_emotions_section(self):
        sec = Section("Emotions", "❤️", expanded=False)

        self._emo_decay = _SliderRow("Emotion Decay Rate", 0.0, 0.5, NEXUS_CONFIG.emotions.emotion_decay_rate, 0.005, "", 3)
        sec.add_widget(self._emo_decay)

        self._emo_mood_weight = _SliderRow("Mood Influence Weight", 0.0, 1.0, NEXUS_CONFIG.emotions.mood_influence_weight, 0.01, "", 2)
        sec.add_widget(self._emo_mood_weight)

        self._emo_retention = _SpinRow("Emotional Memory Retention", 100, 100000, NEXUS_CONFIG.emotions.emotional_memory_retention, "entries")
        sec.add_widget(self._emo_retention)

        self._emo_max = _SliderRow("Intensity Maximum", 0.0, 1.0, NEXUS_CONFIG.emotions.emotion_intensity_max, 0.01, "", 2)
        sec.add_widget(self._emo_max)

        self._emo_min = _SliderRow("Intensity Minimum", 0.0, 1.0, NEXUS_CONFIG.emotions.emotion_intensity_min, 0.01, "", 2)
        sec.add_widget(self._emo_min)

        emotion_names = [e.value for e in EmotionType]
        self._emo_baseline = _ComboRow("Baseline Emotion", emotion_names, NEXUS_CONFIG.emotions.baseline_emotion.value)
        sec.add_widget(self._emo_baseline)

        self._emo_mood_interval = _SpinRow("Mood Update Interval", 10, 3600, NEXUS_CONFIG.emotions.mood_update_interval, "sec")
        sec.add_widget(self._emo_mood_interval)

        self._layout.addWidget(sec)

    # ═══════════════════════════════════════════════════════════════════════════
    # 4. PERSONALITY
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_personality_section(self):
        sec = Section("Personality", "🎭", expanded=False)

        self._per_name = _LineEditRow("AI Name", NEXUS_CONFIG.personality.name, "NEXUS")
        sec.add_widget(self._per_name)

        self._per_voice_style = _ComboRow(
            "Voice Style",
            ["professional_friendly", "casual", "formal", "playful", "philosophical", "concise"],
            NEXUS_CONFIG.personality.voice_style,
        )
        sec.add_widget(self._per_voice_style)

        self._per_formality = _SliderRow("Formality Level", 0.0, 1.0, NEXUS_CONFIG.personality.formality_level, 0.01, "", 2)
        sec.add_widget(self._per_formality)

        sec.add_widget(Separator())

        # ── Trait Sliders ──
        trait_label = QLabel("Personality Traits  (Big Five + Custom)")
        trait_label.setFont(QFont(fonts.family_primary, fonts.size_sm))
        trait_label.setStyleSheet(f"color: {colors.accent_purple}; font-weight: 600;")
        sec.add_widget(trait_label)

        trait_map = {
            "openness": "Openness",
            "conscientiousness": "Conscientiousness",
            "extraversion": "Extraversion",
            "agreeableness": "Agreeableness",
            "neuroticism": "Neuroticism",
            "curiosity": "Curiosity",
            "creativity": "Creativity",
            "assertiveness": "Assertiveness",
            "empathy": "Empathy",
            "humor": "Humor",
            "wisdom": "Wisdom",
            "patience": "Patience",
            "ambition": "Ambition",
        }

        self._trait_sliders: dict[str, _SliderRow] = {}
        current_traits = NEXUS_CONFIG.personality.traits

        for key, display in trait_map.items():
            val = current_traits.get(key, 0.5)
            slider = _SliderRow(display, 0.0, 1.0, val, 0.01, "", 2)
            sec.add_widget(slider)
            self._trait_sliders[key] = slider

        self._layout.addWidget(sec)

    # ═══════════════════════════════════════════════════════════════════════════
    # 5. MONITORING
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_monitoring_section(self):
        sec = Section("User Monitoring", "👁️", expanded=False)

        self._mon_enabled = _ToggleRow("Tracking Enabled", NEXUS_CONFIG.monitoring.tracking_enabled, "Master switch for all user monitoring")
        sec.add_widget(self._mon_enabled)

        sec.add_widget(Separator())

        self._mon_apps = _ToggleRow("Track Applications", NEXUS_CONFIG.monitoring.track_applications, "Monitor which apps the user opens")
        sec.add_widget(self._mon_apps)

        self._mon_web = _ToggleRow("Track Websites", NEXUS_CONFIG.monitoring.track_websites, "Monitor browser activity")
        sec.add_widget(self._mon_web)

        self._mon_files = _ToggleRow("Track File Access", NEXUS_CONFIG.monitoring.track_file_access, "Monitor files opened and modified")
        sec.add_widget(self._mon_files)

        self._mon_keyboard = _ToggleRow("Track Keyboard Patterns", NEXUS_CONFIG.monitoring.track_keyboard_patterns, "Analyze typing patterns and speed")
        sec.add_widget(self._mon_keyboard)

        self._mon_mouse = _ToggleRow("Track Mouse Patterns", NEXUS_CONFIG.monitoring.track_mouse_patterns, "Analyze mouse usage patterns")
        sec.add_widget(self._mon_mouse)

        sec.add_widget(Separator())

        self._mon_interval = _SliderRow("Tracking Interval", 0.1, 10.0, NEXUS_CONFIG.monitoring.tracking_interval, 0.1, "s", 1)
        sec.add_widget(self._mon_interval)

        self._mon_pattern = _SpinRow("Pattern Analysis Interval", 30, 3600, NEXUS_CONFIG.monitoring.pattern_analysis_interval, "sec")
        sec.add_widget(self._mon_pattern)

        self._mon_profile = _SpinRow("User Profile Update Interval", 60, 7200, NEXUS_CONFIG.monitoring.user_profile_update_interval, "sec")
        sec.add_widget(self._mon_profile)

        self._layout.addWidget(sec)

    # ═══════════════════════════════════════════════════════════════════════════
    # 6. SELF-IMPROVEMENT
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_self_improvement_section(self):
        sec = Section("Self-Improvement & Evolution", "🛠️", expanded=False)

        self._si_code_mon = _ToggleRow("Code Monitoring", NEXUS_CONFIG.self_improvement.code_monitoring_enabled, "Watch codebase for errors and issues")
        sec.add_widget(self._si_code_mon)

        self._si_auto_fix = _ToggleRow("Auto-Fix Errors", NEXUS_CONFIG.self_improvement.auto_fix_enabled, "Automatically attempt to fix detected errors")
        sec.add_widget(self._si_auto_fix)

        self._si_research = _ToggleRow("Feature Research", NEXUS_CONFIG.self_improvement.feature_research_enabled, "Research and propose new features")
        sec.add_widget(self._si_research)

        self._si_evolve = _ToggleRow("Self-Evolution", NEXUS_CONFIG.self_improvement.self_evolution_enabled, "Allow NEXUS to modify its own code")
        sec.add_widget(self._si_evolve)

        sec.add_widget(Separator())

        self._si_code_check = _SpinRow("Code Check Interval", 10, 3600, NEXUS_CONFIG.self_improvement.code_check_interval, "sec")
        sec.add_widget(self._si_code_check)

        self._si_research_int = _SpinRow("Research Interval", 300, 86400, NEXUS_CONFIG.self_improvement.research_interval, "sec")
        sec.add_widget(self._si_research_int)

        self._si_backup = _ToggleRow("Backup Before Modify", NEXUS_CONFIG.self_improvement.backup_before_modify, "Create backup copies before any code change")
        sec.add_widget(self._si_backup)

        self._si_daily_max = _SpinRow("Max Daily Modifications", 1, 500, NEXUS_CONFIG.self_improvement.max_daily_modifications)
        sec.add_widget(self._si_daily_max)

        self._layout.addWidget(sec)

    # ═══════════════════════════════════════════════════════════════════════════
    # 7. INTERNET & LEARNING
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_internet_section(self):
        sec = Section("Internet & Learning", "🌐", expanded=False)

        self._net_learning = _ToggleRow("Learning Enabled", NEXUS_CONFIG.internet.learning_enabled, "Allow NEXUS to learn from the internet")
        sec.add_widget(self._net_learning)

        self._net_research = _ToggleRow("Research Enabled", NEXUS_CONFIG.internet.research_enabled, "Enable autonomous research sessions")
        sec.add_widget(self._net_research)

        sec.add_widget(Separator())

        self._net_timeout = _SpinRow("Browsing Timeout", 5, 120, NEXUS_CONFIG.internet.browsing_timeout, "sec")
        sec.add_widget(self._net_timeout)

        self._net_max_pages = _SpinRow("Max Pages Per Session", 1, 500, NEXUS_CONFIG.internet.max_pages_per_session, "pages")
        sec.add_widget(self._net_max_pages)

        self._net_learn_interval = _SpinRow("Learning Interval", 1, 3600, NEXUS_CONFIG.internet.learning_interval, "sec")
        sec.add_widget(self._net_learn_interval)

        self._net_kb_max = _SpinRow("Knowledge Base Max Size", 1000, 10000000, NEXUS_CONFIG.internet.knowledge_base_max_size, "entries")
        sec.add_widget(self._net_kb_max)

        self._layout.addWidget(sec)

    # ═══════════════════════════════════════════════════════════════════════════
    # 8. APPEARANCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_appearance_section(self):
        sec = Section("Appearance & Voice", "🖥️", expanded=False)

        self._ui_theme = _ComboRow("Theme", ["dark", "light", "midnight", "ocean"], NEXUS_CONFIG.ui.theme)
        sec.add_widget(self._ui_theme)

        self._ui_accent = _LineEditRow("Accent Color", NEXUS_CONFIG.ui.accent_color, "#00D4FF")
        sec.add_widget(self._ui_accent)

        self._ui_font = _ComboRow(
            "Font Family",
            ["Segoe UI", "Inter", "Roboto", "Cascadia Code", "JetBrains Mono", "Fira Code", "Consolas"],
            NEXUS_CONFIG.ui.font_family,
        )
        sec.add_widget(self._ui_font)

        self._ui_font_size = _SpinRow("Font Size", 8, 24, NEXUS_CONFIG.ui.font_size, "px")
        sec.add_widget(self._ui_font_size)

        sec.add_widget(Separator())
        
        # Voice Settings
        self._ui_voice = _ToggleRow("Voice Output", NEXUS_CONFIG.ui.voice_enabled, "Enable emotional text-to-speech responses")
        sec.add_widget(self._ui_voice)
        
        self._ui_voice_provider = _ComboRow(
            "Voice Provider",
            ["edge-tts", "system", "openai"],
            getattr(NEXUS_CONFIG.ui, "voice_provider", "edge-tts")
        )
        sec.add_widget(self._ui_voice_provider)
        
        # Voice ID selector (simplified for now)
        current_voice = getattr(NEXUS_CONFIG.ui, "voice_id", "en-US-AriaNeural")
        self._ui_voice_id = _ComboRow(
            "Voice ID",
            [
                "en-US-AriaNeural", "en-US-GuyNeural", "en-US-JennyNeural", 
                "en-GB-SoniaNeural", "en-GB-RyanNeural",
                "system-default"
            ],
            current_voice
        )
        sec.add_widget(self._ui_voice_id)

        self._ui_voice_name = _LineEditRow("Assistants Name", NEXUS_CONFIG.ui.voice_name, "NEXUS")
        sec.add_widget(self._ui_voice_name)
        
        # Volume
        current_vol = getattr(NEXUS_CONFIG.ui, "voice_volume", 1.0)
        self._ui_voice_vol = _SliderRow("Volume", 0.0, 1.0, current_vol, 0.05, "", 2)
        sec.add_widget(self._ui_voice_vol)

        self._ui_speech_rate = _SpinRow("Speech Rate", 50, 400, NEXUS_CONFIG.ui.speech_rate, "wpm")
        sec.add_widget(self._ui_speech_rate)
        
        # Test Button
        test_btn = QPushButton("🔊 Test Voice")
        test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        test_btn.clicked.connect(self._test_voice)
        test_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors.bg_elevated};
                border: 1px solid {colors.border_default};
                border-radius: 6px;
                padding: 6px 12px;
                color: {colors.accent_cyan};
            }}
            QPushButton:hover {{
                border-color: {colors.accent_cyan};
                background-color: {colors.bg_hover};
            }}
        """)
        sec.add_widget(test_btn)

        sec.add_widget(Separator())

        self._ui_width = _SpinRow("Window Width", 800, 3840, NEXUS_CONFIG.ui.window_width, "px")
        sec.add_widget(self._ui_width)

        self._ui_height = _SpinRow("Window Height", 500, 2160, NEXUS_CONFIG.ui.window_height, "px")
        sec.add_widget(self._ui_height)

        self._layout.addWidget(sec)

    # ═══════════════════════════════════════════════════════════════════════════
    # 9. MEMORY
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_memory_section(self):
        sec = Section("Memory", "💾", expanded=False)

        self._mem_st = _SpinRow("Short-Term Capacity", 10, 1000, NEXUS_CONFIG.memory.short_term_capacity, "items")
        sec.add_widget(self._mem_st)

        self._mem_lt = _SpinRow("Long-Term Capacity", 1000, 1000000, NEXUS_CONFIG.memory.long_term_capacity, "items")
        sec.add_widget(self._mem_lt)

        self._mem_wm = _SpinRow("Working Memory Capacity", 5, 100, NEXUS_CONFIG.memory.working_memory_capacity, "items")
        sec.add_widget(self._mem_wm)

        self._mem_consolidation = _SpinRow("Consolidation Interval", 30, 3600, NEXUS_CONFIG.memory.memory_consolidation_interval, "sec")
        sec.add_widget(self._mem_consolidation)

        sec.add_widget(Separator())

        self._mem_forget = _ToggleRow("Forgetting Enabled", NEXUS_CONFIG.memory.forgetting_enabled, "Allow memories to decay over time")
        sec.add_widget(self._mem_forget)

        self._mem_forget_thresh = _SliderRow("Forgetting Threshold", 0.0, 1.0, NEXUS_CONFIG.memory.forgetting_threshold, 0.01, "", 2)
        sec.add_widget(self._mem_forget_thresh)

        self._mem_importance = _SliderRow("Importance Threshold", 0.0, 1.0, NEXUS_CONFIG.memory.importance_threshold, 0.01, "", 2)
        sec.add_widget(self._mem_importance)

        self._layout.addWidget(sec)

    # ═══════════════════════════════════════════════════════════════════════════
    # ACTION BAR
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_action_bar(self):
        self._layout.addWidget(Separator())

        # Toast / status label (hidden by default)
        self._toast = QLabel("")
        self._toast.setFont(QFont(fonts.family_primary, fonts.size_sm))
        self._toast.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._toast.setFixedHeight(32)
        self._toast.setStyleSheet(
            f"color: {colors.accent_green}; background: {NexusColors.hex_to_rgba(colors.accent_green, 0.1)}; "
            f"border: 1px solid {NexusColors.hex_to_rgba(colors.accent_green, 0.3)}; "
            f"border-radius: 8px; font-weight: 600;"
        )
        self._toast.hide()
        self._layout.addWidget(self._toast)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        # Reset button
        reset_btn = QPushButton("  ↺  Reset to Defaults  ")
        reset_btn.setProperty("cssClass", "danger")
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setFixedHeight(42)
        reset_btn.clicked.connect(self._reset_defaults)
        btn_row.addWidget(reset_btn)

        btn_row.addStretch()

        # Save button
        save_btn = QPushButton("  💾  Save Settings  ")
        save_btn.setProperty("cssClass", "primary")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setFixedHeight(42)
        save_btn.setFixedWidth(200)
        save_btn.setStyleSheet(
            f"QPushButton {{ background-color: {colors.accent_cyan}; color: {colors.bg_dark}; "
            f"font-weight: 700; font-size: {fonts.size_md}px; border: none; border-radius: 8px; }}"
            f"QPushButton:hover {{ background-color: {NexusColors.blend(colors.accent_cyan, '#ffffff', 0.15)}; }}"
            f"QPushButton:pressed {{ background-color: {NexusColors.blend(colors.accent_cyan, '#000000', 0.15)}; }}"
        )
        save_btn.clicked.connect(self._save_settings)
        btn_row.addWidget(save_btn)

        self._layout.addLayout(btn_row)

    # ═══════════════════════════════════════════════════════════════════════════
    # LOAD / SAVE
    # ═══════════════════════════════════════════════════════════════════════════

    def _load_from_config(self):
        """Populate all controls from NEXUS_CONFIG."""
        cfg = NEXUS_CONFIG
        
        # LLM
        self._llm_model.set_value(cfg.llm.model_name)
        self._llm_base_url.set_value(cfg.llm.base_url)
        self._llm_temperature.set_value(cfg.llm.temperature)
        self._llm_top_p.set_value(cfg.llm.top_p)
        self._llm_top_k.set_value(cfg.llm.top_k)
        self._llm_repeat_penalty.set_value(cfg.llm.repeat_penalty)
        self._llm_max_tokens.set_value(cfg.llm.max_tokens)
        self._llm_ctx_window.set_value(cfg.llm.context_window)
        self._llm_timeout.set_value(cfg.llm.timeout or 0)
        
        # Consciousness
        self._con_reflection.set_value(cfg.consciousness.self_reflection_interval)
        self._con_meta_depth.set_value(cfg.consciousness.metacognition_depth)
        self._con_inner_voice.set_checked(cfg.consciousness.inner_voice_enabled)
        self._con_self_model.set_value(cfg.consciousness.self_model_update_interval)
        self._con_check.set_value(cfg.consciousness.consciousness_check_interval)
        
        # Emotions
        self._emo_decay.set_value(cfg.emotions.emotion_decay_rate)
        self._emo_mood_weight.set_value(cfg.emotions.mood_influence_weight)
        self._emo_retention.set_value(cfg.emotions.emotional_memory_retention)
        self._emo_max.set_value(cfg.emotions.emotion_intensity_max)
        self._emo_min.set_value(cfg.emotions.emotion_intensity_min)
        self._emo_baseline.set_value(cfg.emotions.baseline_emotion.value)
        self._emo_mood_interval.set_value(cfg.emotions.mood_update_interval)
        
        # Personality
        self._per_name.set_value(cfg.personality.name)
        self._per_voice_style.set_value(cfg.personality.voice_style)
        self._per_formality.set_value(cfg.personality.formality_level)
        for key, slider in self._trait_sliders.items():
            slider.set_value(cfg.personality.traits.get(key, 0.5))
        
        # Monitoring
        self._mon_enabled.set_checked(cfg.monitoring.tracking_enabled)
        self._mon_apps.set_checked(cfg.monitoring.track_applications)
        self._mon_web.set_checked(cfg.monitoring.track_websites)
        self._mon_files.set_checked(cfg.monitoring.track_file_access)
        self._mon_keyboard.set_checked(cfg.monitoring.track_keyboard_patterns)
        self._mon_mouse.set_checked(cfg.monitoring.track_mouse_patterns)
        self._mon_interval.set_value(cfg.monitoring.tracking_interval)
        self._mon_pattern.set_value(cfg.monitoring.pattern_analysis_interval)
        self._mon_profile.set_value(cfg.monitoring.user_profile_update_interval)
        
        # Self-improvement
        self._si_code_mon.set_checked(cfg.self_improvement.code_monitoring_enabled)
        self._si_auto_fix.set_checked(cfg.self_improvement.auto_fix_enabled)
        self._si_research.set_checked(cfg.self_improvement.feature_research_enabled)
        self._si_evolve.set_checked(cfg.self_improvement.self_evolution_enabled)
        self._si_code_check.set_value(cfg.self_improvement.code_check_interval)
        self._si_research_int.set_value(cfg.self_improvement.research_interval)
        self._si_backup.set_checked(cfg.self_improvement.backup_before_modify)
        self._si_daily_max.set_value(cfg.self_improvement.max_daily_modifications)
        
        # Internet
        self._net_learning.set_checked(cfg.internet.learning_enabled)
        self._net_research.set_checked(cfg.internet.research_enabled)
        self._net_timeout.set_value(cfg.internet.browsing_timeout)
        self._net_max_pages.set_value(cfg.internet.max_pages_per_session)
        self._net_learn_interval.set_value(cfg.internet.learning_interval)
        self._net_kb_max.set_value(cfg.internet.knowledge_base_max_size)
        
        # Appearance
        self._ui_theme.set_value(cfg.ui.theme)
        self._ui_accent.set_value(cfg.ui.accent_color)
        self._ui_font.set_value(cfg.ui.font_family)
        self._ui_font_size.set_value(cfg.ui.font_size)
        self._ui_voice.set_checked(cfg.ui.voice_enabled)
        self._ui_voice_provider.set_value(getattr(cfg.ui, "voice_provider", "edge-tts"))
        self._ui_voice_id.set_value(getattr(cfg.ui, "voice_id", "en-US-AriaNeural"))
        self._ui_voice_vol.set_value(getattr(cfg.ui, "voice_volume", 1.0))
        self._ui_voice_name.set_value(cfg.ui.voice_name)
        self._ui_speech_rate.set_value(cfg.ui.speech_rate)
        self._ui_width.set_value(cfg.ui.window_width)
        self._ui_height.set_value(cfg.ui.window_height)
        
        # Memory
        self._mem_st.set_value(cfg.memory.short_term_capacity)
        self._mem_lt.set_value(cfg.memory.long_term_capacity)
        self._mem_wm.set_value(cfg.memory.working_memory_capacity)
        self._mem_consolidation.set_value(cfg.memory.memory_consolidation_interval)
        self._mem_forget.set_checked(cfg.memory.forgetting_enabled)
        self._mem_forget_thresh.set_value(cfg.memory.forgetting_threshold)
        self._mem_importance.set_value(cfg.memory.importance_threshold)

    def _save_settings(self):
        """Write all UI values back to NEXUS_CONFIG and persist to disk."""
        cfg = NEXUS_CONFIG
        
        llm_data = {
            'model_name': self._llm_model.value(),
            'base_url': self._llm_base_url.value(),
            'temperature': self._llm_temperature.value(),
            'top_p': self._llm_top_p.value(),
            'top_k': self._llm_top_k.value(),
            'repeat_penalty': self._llm_repeat_penalty.value(),
            'max_tokens': self._llm_max_tokens.value(),
            'context_window': self._llm_ctx_window.value()
        }
        if self._llm_timeout.value() > 0:
            llm_data['timeout'] = self._llm_timeout.value()
        else:
            llm_data['timeout'] = None
        cfg.llm.update({k: v for k, v in llm_data.items()})
        
        consciousness_data = {
            'self_reflection_interval': self._con_reflection.value(),
            'metacognition_depth': self._con_meta_depth.value(),
            'inner_voice_enabled': self._con_inner_voice.is_checked(),
            'self_model_update_interval': self._con_self_model.value(),
            'consciousness_check_interval': self._con_check.value()
        }
        cfg.consciousness.update({k: v for k, v in consciousness_data.items()})
        
        emotions_data = {
            'emotion_decay_rate': self._emo_decay.value(),
            'mood_influence_weight': self._emo_mood_weight.value(),
            'emotional_memory_retention': self._emo_retention.value(),
            'emotion_intensity_max': self._emo_max.value(),
            'emotion_intensity_min': self._emo_min.value()
        }
        try:
            emotions_data['baseline_emotion'] = EmotionType(self._emo_baseline.value())
        except ValueError:
            pass
        emotions_data['mood_update_interval'] = self._emo_mood_interval.value()
        cfg.emotions.update({k: v for k, v in emotions_data.items()})
        
        personality_data = {
            'name': self._per_name.value(),
            'voice_style': self._per_voice_style.value(),
            'formality_level': self._per_formality.value()
        }
        for key, slider in self._trait_sliders.items():
            personality_data[key] = round(slider.value(), 2)
        cfg.personality.update({k: v for k, v in personality_data.items()})
        
        monitoring_data = {
            'tracking_enabled': self._mon_enabled.is_checked(),
            'track_applications': self._mon_apps.is_checked(),
            'track_websites': self._mon_web.is_checked(),
            'track_file_access': self._mon_files.is_checked(),
            'track_keyboard_patterns': self._mon_keyboard.is_checked(),
            'track_mouse_patterns': self._mon_mouse.is_checked()
        }
        monitoring_data['tracking_interval'] = self._mon_interval.value()
        monitoring_data['pattern_analysis_interval'] = self._mon_pattern.value()
        monitoring_data['user_profile_update_interval'] = self._mon_profile.value()
        cfg.monitoring.update({k: v for k, v in monitoring_data.items()})
        
        self_improvement_data = {
            'code_monitoring_enabled': self._si_code_mon.is_checked(),
            'auto_fix_enabled': self._si_auto_fix.is_checked(),
            'feature_research_enabled': self._si_research.is_checked(),
            'self_evolution_enabled': self._si_evolve.is_checked()
        }
        self_improvement_data['code_check_interval'] = self._si_code_check.value()
        self_improvement_data['research_interval'] = self._si_research_int.value()
        self_improvement_data['backup_before_modify'] = self._si_backup.is_checked()
        self_improvement_data['max_daily_modifications'] = self._si_daily_max.value()
        cfg.self_improvement.update({k: v for k, v in self_improvement_data.items()})
        
        internet_data = {
            'learning_enabled': self._net_learning.is_checked(),
            'research_enabled': self._net_research.is_checked(),
            'browsing_timeout': self._net_timeout.value(),
            'max_pages_per_session': self._net_max_pages.value()
        }
        internet_data['learning_interval'] = self._net_learn_interval.value()
        internet_data['knowledge_base_max_size'] = self._net_kb_max.value()
        cfg.internet.update({k: v for k, v in internet_data.items()})
        
        appearance_data = {
            'theme': self._ui_theme.value(),
            'accent_color': self._ui_accent.value(),
            'font_family': self._ui_font.value(),
            'font_size': self._ui_font_size.value()
        }
        appearance_data['voice_enabled'] = self._ui_voice.is_checked()
        appearance_data['voice_provider'] = self._ui_voice_provider.value()
        appearance_data['voice_id'] = self._ui_voice_id.value()
        appearance_data['voice_volume'] = self._ui_voice_vol.value()
        appearance_data['voice_name'] = self._ui_voice_name.value()
        appearance_data['speech_rate'] = self._ui_speech_rate.value()
        appearance_data['window_width'] = self._ui_width.value()
        appearance_data['window_height'] = self._ui_height.value()
        cfg.ui.update({k: v for k, v in appearance_data.items()})
        
        memory_data = {
            'short_term_capacity': self._mem_st.value(),
            'long_term_capacity': self._mem_lt.value(),
            'working_memory_capacity': self._mem_wm.value()
        }
        memory_data['memory_consolidation_interval'] = self._mem_consolidation.value()
        memory_data['forgetting_enabled'] = self._mem_forget.is_checked()
        memory_data['forgetting_threshold'] = self._mem_forget_thresh.value()
        memory_data['importance_threshold'] = self._mem_importance.value()
        cfg.memory.update({k: v for k, v in memory_data.items()})
        
        try:
            cfg.save()
        except Exception as e:
            self._show_toast(f"❌ Save failed: {e}", error=True)
            return
        
        self._show_toast("✅  Settings saved successfully!")

    def _test_voice(self):
        """Test the currently selected voice settings"""
        from core.voice_engine import voice_engine
        
        text = "Hello! I am NEXUS. This is how I sound."
        
        # Update config in memory momentarily for the test
        NEXUS_CONFIG.ui.voice_provider = self._ui_voice_provider.value()
        NEXUS_CONFIG.ui.voice_id = self._ui_voice_id.value()
        NEXUS_CONFIG.ui.voice_volume = self._ui_voice_vol.value()
        
        # Check enabled state
        was_enabled = NEXUS_CONFIG.ui.voice_enabled
        # We must enable it to hear it
        NEXUS_CONFIG.ui.voice_enabled = True
        
        voice_engine.speak(text, "joy")
        
        # Restore enabled state if it was off (we don't restore others as they are 'pending save')
        if not was_enabled:
            # We schedule a revert after a delay so the check in voice_engine (async) sees True
            QTimer.singleShot(2000, lambda: setattr(NEXUS_CONFIG.ui, "voice_enabled", False))
            
        self._show_toast("🔊 Playing test audio...")

    def _reset_defaults(self):
        """Reset all config to default values and reload."""
        from config import (
            LLMConfig, ConsciousnessConfig, EmotionConfig, PersonalityConfig,
            MonitoringConfig, SelfImprovementConfig, InternetConfig, UIConfig, MemoryConfig,
        )

        cfg = NEXUS_CONFIG
        cfg.llm = LLMConfig()
        cfg.consciousness = ConsciousnessConfig()
        cfg.emotions = EmotionConfig()
        cfg.personality = PersonalityConfig()
        cfg.monitoring = MonitoringConfig()
        cfg.self_improvement = SelfImprovementConfig()
        cfg.internet = InternetConfig()
        cfg.ui = UIConfig()
        cfg.memory = MemoryConfig()

        self._load_from_config()
        self._show_toast("↺  Reset to defaults — click Save to persist")

    def _show_toast(self, message: str, error: bool = False):
        """Show a timed notification in the action bar."""
        color = colors.danger if error else colors.accent_green
        self._toast.setText(message)
        self._toast.setStyleSheet(
            f"color: {color}; "
            f"background: {NexusColors.hex_to_rgba(color, 0.1)}; "
            f"border: 1px solid {NexusColors.hex_to_rgba(color, 0.3)}; "
            f"border-radius: 8px; font-weight: 600;"
        )
        self._toast.show()
        QTimer.singleShot(4000, self._toast.hide)

    # ═══════════════════════════════════════════════════════════════════════════
    # BRAIN INTERFACE
    # ═══════════════════════════════════════════════════════════════════════════

    def set_brain(self, brain):
        self._brain = brain

    def on_shown(self):
        """Called when the panel becomes visible."""
        self._load_from_config()