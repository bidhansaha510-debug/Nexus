"""
NEXUS AI - UI Package
═══════════════════════════════════════════════════════════════════════════════
Advanced futuristic UI for the NEXUS AI system.

Modules:
  theme.py          — Dark theme engine with neon accents
  widgets.py        — Custom animated widgets
  main_window.py    — Main application window
  chat_panel.py     — Chat conversation interface
  dashboard.py      — Real-time statistics dashboard
  mind_panel.py     — Consciousness/emotion/personality visualization
  evolution_panel.py — Self-improvement & evolution monitoring
═══════════════════════════════════════════════════════════════════════════════
"""

from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

__all__ = [
    "NexusMainWindow",
    "theme",
]


def get_main_window():
    """Get or create the main window instance"""
    from ui.main_window import NexusMainWindow
    return NexusMainWindow


def launch_ui(brain=None):
    """Launch the NEXUS UI application"""
    from PySide6.QtWidgets import QApplication
    from ui.main_window import NexusMainWindow
    from ui.theme import theme

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    app.setStyle("Fusion")
    app.setStyleSheet(theme.get_stylesheet())

    window = NexusMainWindow(brain=brain)
    window.show()

    if brain:
        window.set_brain(brain)

    return app, window