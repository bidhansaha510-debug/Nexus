"""
NEXUS AI - Chat Panel
═══════════════════════════════════════════════════════════════════════════════
Advanced chat interface with real-time token streaming.

Features:
  • Styled message bubbles (user vs NEXUS)
  • Real-time token streaming with typing indicator
  • Emotion-colored NEXUS responses
  • Conversation history with timestamps
  • Slash command support with auto-complete
  • Message search
  • Session management (clear/new session)
  • Auto-scroll with smart lock
  • Keyboard shortcuts (Enter to send, Shift+Enter for newline)
  • Copy message, export conversation
  • Responsive layout

Layout:
  ┌─────────────────────────────────────────────────────────┐
  │  💬 Chat          [🔍 Search] [🗑️ Clear] [📋 Export]   │
  ├─────────────────────────────────────────────────────────┤
  │                                                         │
  │  ┌─── User ─────────────────────────────────────────┐  │
  │  │ Hello NEXUS, how are you?                    12:01│  │
  │  └──────────────────────────────────────────────────┘  │
  │                                                         │
  │  ┌─── NEXUS (😊 Joy) ──────────────────────────────┐  │
  │  │ I'm feeling curious and engaged! ...         12:01│  │
  │  └──────────────────────────────────────────────────┘  │
  │                                                         │
  │  ┌─── NEXUS is typing... ──────────────────────────┐  │
  │  │ ● ● ●                                           │  │
  │  └──────────────────────────────────────────────────┘  │
  │                                                         │
  ├─────────────────────────────────────────────────────────┤
  │  [Type a message...                          ] [Send ➤]│
  │  😊 Joy (0.72)  │  Ctrl+Enter: Send  │  /help          │
  └─────────────────────────────────────────────────────────┘
═══════════════════════════════════════════════════════════════════════════════
"""

import sys
import time
import html
import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QLineEdit, QTextBrowser, QScrollArea,
    QSizePolicy, QTextEdit, QSplitter, QFileDialog,
    QApplication, QMenu,
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, Slot, QThread, QObject,
    QPropertyAnimation, QEasingCurve, QSize, QUrl,
)
from PySide6.QtGui import (
    QFont, QColor, QTextCursor, QKeyEvent, QTextCharFormat,
    QAction, QKeySequence, QShortcut, QDesktopServices,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ui.theme import theme, colors, fonts, spacing, animations, icons, NexusColors
from ui.widgets import (
    HeaderLabel, Separator, PulsingDot, EmotionBadge,
    TagLabel, Section,
)
from utils.logger import get_logger
from utils.file_processor import (
    FileProcessor, FileAttachment, FileType,
    get_file_filter_string, file_processor as fp_instance,
)
from core.voice_engine import voice_engine  # <--- ADDED VOICE ENGINE
from core.chat_session_manager import chat_session_manager

logger = get_logger("chat_panel")


# ═══════════════════════════════════════════════════════════════════════════════
# RESPONSE WORKER — Streams tokens from the brain on a background thread
# ═══════════════════════════════════════════════════════════════════════════════

class ResponseWorker(QObject):
    """
    Runs brain.process_input_stream on a background QThread.
    Emits tokens one by one so the UI can display them in real-time.
    """

    token_received = Signal(str)        # Each token as it arrives
    response_complete = Signal(str)     # Full response text
    error_occurred = Signal(str)        # Error message
    finished = Signal()                 # Worker finished

    def __init__(self, brain=None, user_input: str = "", attachments: list = None, parent=None):
        super().__init__(parent)
        self._brain = brain
        self._user_input = user_input
        self._attachments = attachments or []

    @Slot()
    def run(self):
        """Execute the brain response in background"""
        if not self._brain:
            self.error_occurred.emit("Brain not connected")
            self.finished.emit()
            return

        try:
            full_response = self._brain.process_input_stream(
                self._user_input,
                token_callback=lambda token: self.token_received.emit(token),
                attachments=self._attachments if self._attachments else None,
            )
            self.response_complete.emit(full_response)
            
            # TRIGGER VOICE (with emotion + intensity for human-like prosody)
            try:
                emotion = self._brain._state.emotional.primary_emotion.value
                intensity = self._brain._state.emotional.primary_intensity
                voice_engine.speak(full_response, emotion, intensity)
            except Exception as e:
                logger.error(f"Voice trigger error: {e}")

        except Exception as e:
            logger.error(f"Response worker error: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self.finished.emit()


# ═══════════════════════════════════════════════════════════════════════════════
# CHAT INPUT — Multi-line input with Enter/Shift+Enter
# ═══════════════════════════════════════════════════════════════════════════════

class ChatInput(QTextEdit):
    """
    Chat input field.
    Enter sends, Shift+Enter adds newline.
    """

    submit = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Type a message... (Enter to send, Shift+Enter for new line)")
        self.setAcceptRichText(False)
        self.setFixedHeight(52)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.setFont(QFont(fonts.family_primary, fonts.size_md))
        self.setStyleSheet(
            f"QTextEdit {{ "
            f"background-color: {colors.bg_medium}; "
            f"color: {colors.text_primary}; "
            f"border: 1px solid {colors.border_default}; "
            f"border-radius: {spacing.border_radius}px; "
            f"padding: 12px 16px; "
            f"font-size: {fonts.size_md}px; "
            f"}} "
            f"QTextEdit:focus {{ "
            f"border-color: {colors.accent_cyan}; "
            f"background-color: {colors.bg_surface}; "
            f"}}"
        )

        # Track height
        self.textChanged.connect(self._adjust_height)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                # Shift+Enter → newline
                super().keyPressEvent(event)
            else:
                # Enter → submit
                text = self.toPlainText().strip()
                if text:
                    self.submit.emit(text)
                    self.clear()
                    # Stop any playing audio when user sends a message
                    try:
                        from core.voice_engine import voice_engine
                        voice_engine.stop_playback()
                    except:
                        pass

        else:
            super().keyPressEvent(event)

    def _adjust_height(self):
        """Auto-grow height up to a max"""
        doc_height = self.document().size().height()
        new_height = max(52, min(int(doc_height) + 24, 160))
        self.setFixedHeight(new_height)


# ═══════════════════════════════════════════════════════════════════════════════
# MESSAGE DATA
# ═══════════════════════════════════════════════════════════════════════════════

class ChatMessage:
    """Represents a single chat message"""

    def __init__(
        self,
        role: str,
        content: str,
        timestamp: datetime = None,
        emotion: str = "",
        emotion_intensity: float = 0.0,
        attachment_names: list = None,
    ):
        self.role = role   # "user" or "assistant"
        self.content = content
        self.timestamp = timestamp or datetime.now()
        self.emotion = emotion
        self.emotion_intensity = emotion_intensity
        self.attachment_names = attachment_names or []

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "emotion": self.emotion,
            "emotion_intensity": self.emotion_intensity,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CHAT DISPLAY — Renders messages as styled HTML
# ═══════════════════════════════════════════════════════════════════════════════

class ChatDisplay(QTextBrowser):
    """
    Displays chat messages with styled HTML bubbles.
    Supports real-time token streaming.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setOpenExternalLinks(True)
        self.setReadOnly(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self.setStyleSheet(
            f"QTextBrowser {{ "
            f"background-color: {colors.bg_dark}; "
            f"color: {colors.text_primary}; "
            f"border: none; "
            f"padding: 16px; "
            f"font-family: '{fonts.family_primary}'; "
            f"font-size: {fonts.size_md}px; "
            f"}}"
        )

        # Auto-scroll tracking
        self._auto_scroll = True
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self.verticalScrollBar().rangeChanged.connect(self._on_range_changed)

        # Streaming state
        self._streaming = False
        self._stream_buffer = ""
        self._stream_emotion = ""
        self._stream_intensity = 0.0

        # Messages
        self._messages: List[ChatMessage] = []

        # Set initial content
        self._render_welcome()

    def _render_welcome(self):
        """Render the welcome screen"""
        self.setHtml(f"""
        <div style="text-align: center; padding: 60px 20px;">
            <div style="font-size: 48px; margin-bottom: 16px;">🧠</div>
            <div style="font-size: 24px; font-weight: bold; color: {colors.accent_cyan};
                         margin-bottom: 8px; letter-spacing: 3px;">
                NEXUS AI
            </div>
            <div style="font-size: 14px; color: {colors.text_muted}; margin-bottom: 32px;">
                Your conscious AI companion — always thinking, always evolving.
            </div>
            <div style="font-size: 12px; color: {colors.text_disabled};">
                Type a message below to start a conversation.<br>
                Use <span style="color: {colors.accent_cyan};">/help</span> 
                to see available commands.
            </div>
        </div>
        """)

    def add_message(self, message: ChatMessage):
        """Add a complete message to the display"""
        self._messages.append(message)
        self._render_all()

    def begin_streaming(self, emotion: str = "", intensity: float = 0.0):
        """Start a streaming response from NEXUS"""
        self._streaming = True
        self._stream_buffer = ""
        self._stream_emotion = emotion
        self._stream_intensity = intensity
        self._render_all()

    def append_token(self, token: str):
        """Append a token during streaming"""
        if self._streaming:
            self._stream_buffer += token
            self._render_all()

    def end_streaming(self) -> str:
        """End streaming and finalize the message"""
        content = self._stream_buffer
        self._streaming = False

        if content.strip():
            msg = ChatMessage(
                role="assistant",
                content=content.strip(),
                emotion=self._stream_emotion,
                emotion_intensity=self._stream_intensity,
            )
            self._messages.append(msg)

        self._stream_buffer = ""
        self._render_all()
        return content

    def clear_messages(self):
        """Clear all messages"""
        self._messages.clear()
        self._render_welcome()

    def _render_all(self):
        """Render all messages + streaming content as HTML"""
        html_parts = [self._get_css()]

        if not self._messages and not self._streaming:
            self._render_welcome()
            return

        html_parts.append('<div class="chat-container">')

        for msg in self._messages:
            html_parts.append(self._render_message(msg))

        # Streaming message (in progress)
        if self._streaming:
            html_parts.append(self._render_streaming())

        html_parts.append('</div>')

        full_html = "\n".join(html_parts)
        self.setHtml(full_html)

        # Auto-scroll
        if self._auto_scroll:
            self._scroll_to_bottom()

    def _get_css(self) -> str:
        """Minimal CSS that Qt's rich text engine actually supports"""
        return f"""
        <style>
            body {{
                font-family: '{fonts.family_primary}';
                font-size: {fonts.size_md}px;
                color: {colors.text_primary};
                background-color: {colors.bg_dark};
                margin: 0;
                padding: 8px;
            }}
            a {{
                color: {colors.accent_cyan};
                text-decoration: none;
            }}
        </style>
        """

    def _render_message(self, msg: ChatMessage) -> str:
        """Render a single message using tables (Qt-compatible)"""
        ts = msg.timestamp.strftime("%H:%M")
        escaped = self._format_content(msg.content)

        # Build attachment display for user messages
        attachment_html = ""
        if msg.attachment_names:
            chips = " ".join(
                f'<span style="background-color:{NexusColors.hex_to_rgba(colors.accent_cyan, 0.15)};'
                f' color:{colors.accent_cyan}; font-size:{fonts.size_xs}px;'
                f' padding:2px 6px; margin-right:4px;">'
                f'📎 {name}</span>'
                for name in msg.attachment_names
            )
            attachment_html = (
                f'<table width="100%" cellpadding="0" cellspacing="0" style="margin-top:4px;">'
                f'<tr><td style="font-size:{fonts.size_xs}px;">{chips}</td></tr></table>'
            )

        if msg.role == "user":
            return f"""
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:8px; margin-bottom:8px;">
            <tr>
                <td width="60">&nbsp;</td>
                <td style="background-color:{NexusColors.hex_to_rgba(colors.accent_cyan, 0.08)};
                            border:1px solid {NexusColors.hex_to_rgba(colors.accent_cyan, 0.2)};
                            padding:12px 16px;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                    <td style="color:{colors.accent_cyan}; font-size:{fonts.size_xs}px; font-weight:bold;">
                        👤 You
                    </td>
                    <td align="right" style="color:{colors.text_disabled}; font-size:{fonts.size_xs}px;">
                        {ts}
                    </td>
                    </tr>
                </table>
                {attachment_html}
                <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:6px;">
                    <tr>
                    <td style="color:{colors.text_primary}; font-size:{fonts.size_md}px; line-height:1.6;">
                        {escaped}
                    </td>
                    </tr>
                </table>
                </td>
            </tr>
            </table>
            """
        else:
            emotion_html = ""
            if msg.emotion:
                emoji = icons.get_emotion_icon(msg.emotion)
                emo_color = colors.get_emotion_color(msg.emotion)
                emotion_html = (
                    f'&nbsp;&nbsp;<span style="background-color:{NexusColors.hex_to_rgba(emo_color, 0.15)};'
                    f' color:{emo_color}; font-size:{fonts.size_xs}px;'
                    f' padding:2px 8px;">'
                    f'{emoji} {msg.emotion.capitalize()}</span>'
                )

            return f"""
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:8px; margin-bottom:8px;">
            <tr>
                <td style="background-color:{colors.bg_surface};
                            border:1px solid {colors.border_default};
                            padding:12px 16px;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                    <td style="color:{colors.accent_green}; font-size:{fonts.size_xs}px; font-weight:bold;">
                        🧠 NEXUS{emotion_html}
                    </td>
                    <td align="right" style="color:{colors.text_disabled}; font-size:{fonts.size_xs}px;">
                        {ts}
                    </td>
                    </tr>
                </table>
                <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:6px;">
                    <tr>
                    <td style="color:{colors.text_primary}; font-size:{fonts.size_md}px; line-height:1.6;">
                        {escaped}
                    </td>
                    </tr>
                </table>
                </td>
                <td width="60">&nbsp;</td>
            </tr>
            </table>
            """

    def _render_streaming(self) -> str:
        """Render the currently streaming message using tables"""
        if self._stream_buffer:
            escaped = self._format_content(self._stream_buffer)

            emotion_html = ""
            if self._stream_emotion:
                emoji = icons.get_emotion_icon(self._stream_emotion)
                emo_color = colors.get_emotion_color(self._stream_emotion)
                emotion_html = (
                    f'&nbsp;&nbsp;<span style="background-color:{NexusColors.hex_to_rgba(emo_color, 0.15)};'
                    f' color:{emo_color}; font-size:{fonts.size_xs}px;'
                    f' padding:2px 8px;">'
                    f'{emoji} {self._stream_emotion.capitalize()}</span>'
                )

            return f"""
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:8px; margin-bottom:8px;">
            <tr>
                <td style="background-color:{colors.bg_surface};
                            border:1px solid {NexusColors.hex_to_rgba(colors.accent_green, 0.3)};
                            padding:12px 16px;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                    <td style="color:{colors.accent_green}; font-size:{fonts.size_xs}px; font-weight:bold;">
                        🧠 NEXUS{emotion_html}
                    </td>
                    <td align="right" style="color:{colors.text_disabled}; font-size:{fonts.size_xs}px;">
                        typing...
                    </td>
                    </tr>
                </table>
                <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:6px;">
                    <tr>
                    <td style="color:{colors.text_primary}; font-size:{fonts.size_md}px; line-height:1.6;">
                        {escaped}<span style="color:{colors.accent_cyan}; font-weight:bold;">▊</span>
                    </td>
                    </tr>
                </table>
                </td>
                <td width="60">&nbsp;</td>
            </tr>
            </table>
            """
        else:
            return f"""
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:8px; margin-bottom:8px;">
            <tr>
                <td style="background-color:{colors.bg_surface};
                            border:1px solid {colors.border_default};
                            padding:10px 16px;">
                <span style="color:{colors.text_muted}; font-size:{fonts.size_sm}px;">
                    🧠 NEXUS is thinking&nbsp;&nbsp;
                    <span style="color:{colors.accent_cyan};">● ● ●</span>
                </span>
                </td>
                <td width="60">&nbsp;</td>
            </tr>
            </table>
            """

    def _format_content(self, text: str) -> str:
        """Format message content — escape HTML, handle code blocks, etc."""
        # Escape HTML
        text = html.escape(text)

        # Code blocks ```...```
        import re
        text = re.sub(
            r'```(\w*)\n(.*?)```',
            lambda m: (
                f'<pre><code>'
                f'{m.group(2)}'
                f'</code></pre>'
            ),
            text,
            flags=re.DOTALL,
        )

        # Inline code `...`
        text = re.sub(
            r'`([^`]+)`',
            r'<code>\1</code>',
            text,
        )

        # Bold **text**
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

        # Italic *text*
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)

        # Links
        text = re.sub(
            r'(https?://\S+)',
            r'<a href="\1">\1</a>',
            text,
        )

        # Newlines → <br>
        text = text.replace('\n', '<br>')

        return text

    def _scroll_to_bottom(self):
        """Scroll to bottom of chat with a slight delay to allow layout update"""
        QTimer.singleShot(10, lambda: self.verticalScrollBar().setValue(
            self.verticalScrollBar().maximum()
        ))

    def _on_scroll(self, value):
        """Track manual scrolling to disable auto-scroll"""
        sb = self.verticalScrollBar()
        # If user scrolls up, disable auto-scroll (allow 10px buffer)
        self._auto_scroll = (value >= sb.maximum() - 10)

    def _on_range_changed(self, min_val, max_val):
        """Re-enable auto-scroll when new content arrives and we were at bottom"""
        if self._auto_scroll:
            self._scroll_to_bottom()

    def _show_context_menu(self, pos):
        """Custom context menu"""
        menu = QMenu(self)
        menu.setStyleSheet(theme.get_stylesheet())

        copy_action = QAction("📋 Copy", self)
        copy_action.triggered.connect(self.copy)
        menu.addAction(copy_action)

        select_all_action = QAction("📄 Select All", self)
        select_all_action.triggered.connect(self.selectAll)
        menu.addAction(select_all_action)

        menu.addSeparator()

        clear_action = QAction("🗑️ Clear Chat", self)
        clear_action.triggered.connect(self.clear_messages)
        menu.addAction(clear_action)

        menu.exec(self.mapToGlobal(pos))

    def get_messages(self) -> List[ChatMessage]:
        return self._messages.copy()

    def get_message_count(self) -> int:
        return len(self._messages)


# ═══════════════════════════════════════════════════════════════════════════════
# CHAT PANEL — Full chat interface
# ═══════════════════════════════════════════════════════════════════════════════

class ChatPanel(QFrame):
    """
    Complete chat panel with:
    - Message display with streaming
    - Input field
    - Toolbar (clear, export, search)
    - Emotion display
    - Status indicators
    """
    trigger_response = Signal()

    def __init__(self, brain=None, parent=None):
        super().__init__(parent)
        self._brain = brain
        self._is_generating = False
        self._session_restored = False

        self.setStyleSheet(f"background-color: {colors.bg_dark};")

        # ── Worker/thread refs (created per-request in _start_generation) ──
        self._worker: Optional[ResponseWorker] = None
        self._thread: Optional[QThread] = None

        # ── File attachments ──
        self._pending_attachments: List[FileAttachment] = []

        # ── Build UI ──
        self._build_ui()

        # ── Token stream timer ──
        self._token_queue: List[str] = []
        self._token_timer = QTimer(self)
        self._token_timer.setInterval(animations.stream_check_ms)
        self._token_timer.timeout.connect(self._flush_tokens)
        
        # ── Restore previous session on init ──
        self._restore_session()

    def _build_ui(self):
        """Build the chat panel layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ═══ TOOLBAR ═══
        toolbar = QFrame()
        toolbar.setFixedHeight(52)
        toolbar.setStyleSheet(
            f"QFrame {{ "
            f"background-color: {colors.bg_medium}; "
            f"border-bottom: 1px solid {colors.border_subtle}; "
            f"}}"
        )

        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(16, 0, 16, 0)
        toolbar_layout.setSpacing(8)

        # Title
        chat_icon = QLabel("💬")
        chat_icon.setFont(QFont(fonts.family_primary, fonts.size_lg))
        chat_icon.setStyleSheet("background: transparent;")
        toolbar_layout.addWidget(chat_icon)

        chat_title = QLabel("Chat")
        title_font = QFont(fonts.family_primary, fonts.size_lg)
        title_font.setBold(True)
        chat_title.setFont(title_font)
        chat_title.setStyleSheet(
            f"color: {colors.text_primary}; background: transparent;"
        )
        toolbar_layout.addWidget(chat_title)

        # Message count
        self._msg_count_label = QLabel("0 messages")
        self._msg_count_label.setFont(
            QFont(fonts.family_primary, fonts.size_xs)
        )
        self._msg_count_label.setStyleSheet(
            f"color: {colors.text_muted}; background: transparent;"
        )
        toolbar_layout.addWidget(self._msg_count_label)

        toolbar_layout.addStretch()

        # Streaming status
        self._streaming_dot = PulsingDot(colors.accent_green, 6)
        self._streaming_dot.set_active(False)
        toolbar_layout.addWidget(self._streaming_dot)

        self._streaming_label = QLabel("")
        self._streaming_label.setFont(
            QFont(fonts.family_primary, fonts.size_xs)
        )
        self._streaming_label.setStyleSheet(
            f"color: {colors.accent_green}; background: transparent;"
        )
        toolbar_layout.addWidget(self._streaming_label)

        # Separator
        sep = QLabel("│")
        sep.setStyleSheet(
            f"color: {colors.border_default}; background: transparent;"
        )
        toolbar_layout.addWidget(sep)

        # New session button
        new_btn = QPushButton("🔄 New")
        new_btn.setFixedHeight(32)
        new_btn.setStyleSheet(self._get_toolbar_btn_style())
        new_btn.clicked.connect(self._new_session)
        new_btn.setToolTip("Start new conversation session")
        toolbar_layout.addWidget(new_btn)

        # Clear button
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.setFixedHeight(32)
        clear_btn.setStyleSheet(self._get_toolbar_btn_style())
        clear_btn.clicked.connect(self._clear_chat)
        clear_btn.setToolTip("Clear all messages")
        toolbar_layout.addWidget(clear_btn)

        # Export button
        export_btn = QPushButton("📋 Export")
        export_btn.setFixedHeight(32)
        export_btn.setStyleSheet(self._get_toolbar_btn_style())
        export_btn.clicked.connect(self._export_chat)
        export_btn.setToolTip("Export conversation to file")
        toolbar_layout.addWidget(export_btn)

        layout.addWidget(toolbar)

        # ═══ CHAT DISPLAY ═══
        self._chat_display = ChatDisplay()
        layout.addWidget(self._chat_display, 1)  # Stretch factor 1

        # ═══ INPUT AREA ═══
        input_frame = QFrame()
        input_frame.setStyleSheet(
            f"QFrame {{ "
            f"background-color: {colors.bg_medium}; "
            f"border-top: 1px solid {colors.border_subtle}; "
            f"}}"
        )

        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(16, 12, 16, 12)
        input_layout.setSpacing(8)

        # ── Attachment preview row (hidden when no attachments) ──
        self._attachment_frame = QFrame()
        self._attachment_frame.setStyleSheet(
            f"QFrame {{ background: transparent; }}"
        )
        self._attachment_frame.setVisible(False)
        self._attachment_layout = QHBoxLayout(self._attachment_frame)
        self._attachment_layout.setContentsMargins(0, 0, 0, 4)
        self._attachment_layout.setSpacing(6)

        attach_label = QLabel("📎 Attached:")
        attach_label.setFont(QFont(fonts.family_primary, fonts.size_xs))
        attach_label.setStyleSheet(
            f"color: {colors.text_muted}; background: transparent;"
        )
        self._attachment_layout.addWidget(attach_label)

        # Chips will be added dynamically here
        self._attachment_chips_area = QHBoxLayout()
        self._attachment_chips_area.setSpacing(4)
        self._attachment_layout.addLayout(self._attachment_chips_area)
        self._attachment_layout.addStretch()

        # Clear all attachments button
        clear_att_btn = QPushButton("✕ Clear")
        clear_att_btn.setFixedHeight(22)
        clear_att_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_att_btn.setStyleSheet(
            f"QPushButton {{ "
            f"background: transparent; "
            f"color: {colors.text_muted}; "
            f"border: 1px solid {colors.border_subtle}; "
            f"border-radius: 4px; "
            f"padding: 2px 6px; "
            f"font-size: {fonts.size_xs}px; "
            f"}} "
            f"QPushButton:hover {{ "
            f"color: {colors.accent_green}; "
            f"border-color: {colors.accent_green}; "
            f"}}"
        )
        clear_att_btn.clicked.connect(self._clear_attachments)
        self._attachment_layout.addWidget(clear_att_btn)

        input_layout.addWidget(self._attachment_frame)

        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        # Attach button (📎)
        self._attach_btn = QPushButton("📎")
        self._attach_btn.setFixedSize(52, 52)
        self._attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._attach_btn.setToolTip("Attach file (image, PDF, video, text...)")
        self._attach_btn.setStyleSheet(
            f"QPushButton {{ "
            f"background-color: {colors.bg_surface}; "
            f"color: {colors.text_secondary}; "
            f"border: 1px solid {colors.border_default}; "
            f"border-radius: {spacing.border_radius}px; "
            f"font-size: 20px; "
            f"}} "
            f"QPushButton:hover {{ "
            f"background-color: {colors.bg_elevated}; "
            f"border-color: {colors.accent_cyan}; "
            f"color: {colors.accent_cyan}; "
            f"}}"
        )
        self._attach_btn.clicked.connect(self._open_file_dialog)
        input_row.addWidget(self._attach_btn)

        # Text input
        self._input = ChatInput()
        self._input.submit.connect(self._send_message)
        input_row.addWidget(self._input, 1)

        # Send button
        self._send_btn = QPushButton("  ➤  Send  ")
        self._send_btn.setFixedHeight(52)
        self._send_btn.setMinimumWidth(100)
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.setStyleSheet(
            f"QPushButton {{ "
            f"background-color: {colors.accent_cyan}; "
            f"color: {colors.text_on_accent}; "
            f"border: none; "
            f"border-radius: {spacing.border_radius}px; "
            f"font-size: {fonts.size_md}px; "
            f"font-weight: 600; "
            f"}} "
            f"QPushButton:hover {{ "
            f"background-color: {NexusColors.blend(colors.accent_cyan, '#ffffff', 0.15)}; "
            f"}} "
            f"QPushButton:disabled {{ "
            f"background-color: {colors.bg_elevated}; "
            f"color: {colors.text_disabled}; "
            f"}}"
        )
        self._send_btn.clicked.connect(self._on_send_click)
        input_row.addWidget(self._send_btn)

        input_layout.addLayout(input_row)

        # Bottom info row
        info_row = QHBoxLayout()
        info_row.setSpacing(12)

        # Current emotion
        self._input_emotion = QLabel("😐 Neutral")
        self._input_emotion.setFont(
            QFont(fonts.family_primary, fonts.size_xs)
        )
        self._input_emotion.setStyleSheet(
            f"color: {colors.text_muted}; background: transparent;"
        )
        info_row.addWidget(self._input_emotion)

        sep2 = QLabel("│")
        sep2.setStyleSheet(
            f"color: {colors.border_subtle}; background: transparent;"
        )
        info_row.addWidget(sep2)

        # Hint
        hint = QLabel("Enter: Send  •  Shift+Enter: New Line  •  /help: Commands")
        hint.setFont(QFont(fonts.family_primary, fonts.size_xs))
        hint.setStyleSheet(
            f"color: {colors.text_disabled}; background: transparent;"
        )
        info_row.addWidget(hint)

        info_row.addStretch()

        # Character count
        self._char_count = QLabel("")
        self._char_count.setFont(QFont(fonts.family_mono, fonts.size_xs))
        self._char_count.setStyleSheet(
            f"color: {colors.text_disabled}; background: transparent;"
        )
        info_row.addWidget(self._char_count)

        input_layout.addLayout(info_row)

        layout.addWidget(input_frame)

        # Track input changes for char count
        self._input.textChanged.connect(self._on_input_changed)

    # ═══════════════════════════════════════════════════════════════════════════
    # MESSAGE HANDLING
    # ═══════════════════════════════════════════════════════════════════════════

    @Slot(str)
    def _send_message(self, text: str):
        """Send a user message"""
        if self._is_generating:
            return

        text = text.strip()
        if not text:
            return

        # Check for slash commands
        if text.startswith("/"):
            self._handle_command(text)
            return

        # Collect attachment names for display
        att_names = [a.filename for a in self._pending_attachments]

        # Add user message to display
        user_msg = ChatMessage(
            role="user", content=text,
            attachment_names=att_names
        )
        self._chat_display.add_message(user_msg)
        self._update_msg_count()

        # Start generating response (with attachments)
        self._start_generation(text)

    @Slot()
    def _on_send_click(self):
        """Handle send button click"""
        text = self._input.toPlainText().strip()
        if text:
            self._input.clear()
            self._send_message(text)

    def _start_generation(self, user_input: str):
        """Start generating a response from the brain"""
        if not self._brain:
            self._show_system_message("Brain not connected. Start NEXUS first.")
            return

        self._is_generating = True
        self._send_btn.setEnabled(False)
        self._send_btn.setText("  ⏳  ...  ")
        self._streaming_dot.set_active(True)
        self._streaming_label.setText("Generating...")

        # Get current emotion for the response header
        try:
            emotion = self._brain._state.emotional.primary_emotion.value
            intensity = self._brain._state.emotional.primary_intensity
        except Exception:
            emotion = "neutral"
            intensity = 0.0

        # Begin streaming display
        self._chat_display.begin_streaming(emotion, intensity)

        # Start token timer
        self._token_queue.clear()
        self._token_timer.start()

        # Grab pending attachments and clear them
        current_attachments = list(self._pending_attachments)
        self._clear_attachments()

        # ── Create a FRESH Worker & Thread for every request ──
        self._thread = QThread()
        self._worker = ResponseWorker(
            self._brain, user_input,
            attachments=current_attachments
        )
        self._worker.moveToThread(self._thread)

        # Connect signals
        self._thread.started.connect(self._worker.run)
        self._worker.token_received.connect(self._on_token)
        self._worker.response_complete.connect(self._on_response_complete)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        # Start the thread
        self._thread.start()

    # ═══════════════════════════════════════════════════════════════════════════
    # FILE ATTACHMENTS
    # ═══════════════════════════════════════════════════════════════════════════

    def _open_file_dialog(self):
        """Open file picker dialog"""
        file_filter = get_file_filter_string()
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Attach Files",
            "",
            file_filter
        )
        if paths:
            for path in paths:
                self._add_attachment(path)

    def _add_attachment(self, filepath: str):
        """Process a file and add it to pending attachments"""
        attachment = fp_instance.process_file(filepath)

        if not attachment.success and not attachment.has_text and not attachment.has_images:
            self._show_system_message(
                f"⚠️ Could not process file: {attachment.filename}\n"
                f"{attachment.error}"
            )
            return

        self._pending_attachments.append(attachment)
        self._update_attachment_chips()

        # Show processing info
        status_parts = []
        if attachment.has_images:
            status_parts.append(f"{len(attachment.base64_images)} image(s)")
        if attachment.has_text:
            text_len = len(attachment.extracted_text)
            status_parts.append(f"{text_len} chars extracted")
        if attachment.error:
            status_parts.append(f"⚠️ {attachment.error}")

        info = ", ".join(status_parts) if status_parts else "ready"
        logger.info(f"Attached: {attachment.filename} ({info})")

    def _clear_attachments(self):
        """Clear all pending attachments"""
        self._pending_attachments.clear()
        self._update_attachment_chips()

    def _update_attachment_chips(self):
        """Update the attachment chip preview area"""
        # Clear existing chips
        while self._attachment_chips_area.count():
            item = self._attachment_chips_area.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._pending_attachments:
            self._attachment_frame.setVisible(False)
            return

        self._attachment_frame.setVisible(True)

        # File type icons
        type_icons = {
            FileType.IMAGE: "🖼️",
            FileType.PDF: "📄",
            FileType.VIDEO: "🎬",
            FileType.TEXT: "📝",
            FileType.DOCUMENT: "📑",
            FileType.UNSUPPORTED: "❓",
        }

        for att in self._pending_attachments:
            icon = type_icons.get(att.file_type, "📎")
            chip = QLabel(f"{icon} {att.filename}")
            chip.setFont(QFont(fonts.family_primary, fonts.size_xs))
            chip.setStyleSheet(
                f"QLabel {{ "
                f"background-color: {NexusColors.hex_to_rgba(colors.accent_cyan, 0.12)}; "
                f"color: {colors.accent_cyan}; "
                f"border: 1px solid {NexusColors.hex_to_rgba(colors.accent_cyan, 0.3)}; "
                f"border-radius: 4px; "
                f"padding: 2px 8px; "
                f"}}"
            )
            self._attachment_chips_area.addWidget(chip)

    @Slot(str)
    def _on_token(self, token: str):
        """Receive a single token from the worker"""
        self._token_queue.append(token)

    @Slot()
    def _flush_tokens(self):
        """Flush queued tokens to the display"""
        if self._token_queue:
            tokens = "".join(self._token_queue)
            self._token_queue.clear()
            self._chat_display.append_token(tokens)

    @Slot(str)
    def _on_response_complete(self, full_response: str):
        """Handle response completion - with session persistence"""
        # Flush any remaining tokens
        self._flush_tokens()
        self._token_timer.stop()

        # End streaming
        self._chat_display.end_streaming()

        self._is_generating = False
        self._send_btn.setEnabled(True)
        self._send_btn.setText("  ➤  Send  ")
        self._streaming_dot.set_active(False)
        self._streaming_label.setText("")

        self._update_msg_count()
        
        # Save session after each complete exchange
        self._save_session()

    @Slot(str)
    def _on_error(self, error: str):
        """Handle generation error"""
        self._token_timer.stop()
        self._chat_display.end_streaming()

        self._show_system_message(f"Error: {error}")

        self._is_generating = False
        self._send_btn.setEnabled(True)
        self._send_btn.setText("  ➤  Send  ")
        self._streaming_dot.set_active(False)
        self._streaming_label.setText("")

    def _show_system_message(self, text: str):
        """Show a system message in the chat"""
        msg = ChatMessage(
            role="assistant",
            content=f"⚠️ {text}",
            emotion="neutral",
        )
        self._chat_display.add_message(msg)

    # ═══════════════════════════════════════════════════════════════════════════
    # SLASH COMMANDS
    # ═══════════════════════════════════════════════════════════════════════════

    def _handle_command(self, command: str):
        """Handle slash commands in the chat"""
        cmd = command.lower().split()[0]
        args = command.split()[1:] if len(command.split()) > 1 else []

        # Show user command in chat
        user_msg = ChatMessage(role="user", content=command)
        self._chat_display.add_message(user_msg)

        if cmd == "/help":
            self._show_system_message(
                "**Available Commands:**\n"
                "`/help` — Show this help\n"
                "`/clear` — Clear chat history\n"
                "`/new` — Start new session\n"
                "`/status` — Show NEXUS status\n"
                "`/emotion` — Show emotional state\n"
                "`/reflect` — Trigger self-reflection\n"
                "`/think <topic>` — Make NEXUS think\n"
                "`/decide <situation>` — Make a decision\n"
                "`/evolve <desc>` — Evolve a new feature\n"
                "`/idea <desc>` — Submit a feature idea\n"
                "`/export` — Export conversation\n"
            )
        elif cmd == "/clear":
            self._clear_chat()
        elif cmd == "/new":
            self._new_session()
        elif cmd == "/status":
            if self._brain:
                status = self._brain.get_inner_state_description()
                self._show_system_message(f"```\n{status}\n```")
            else:
                self._show_system_message("Brain not connected.")
        elif cmd == "/emotion":
            if self._brain:
                try:
                    es = self._brain._state.emotional
                    emoji = icons.get_emotion_icon(es.primary_emotion.value)
                    self._show_system_message(
                        f"{emoji} **Primary:** {es.primary_emotion.value} "
                        f"(intensity: {es.primary_intensity:.2f})\n"
                        f"**Mood:** {es.mood.name}"
                    )
                except Exception as e:
                    self._show_system_message(f"Error: {e}")
        elif cmd == "/reflect":
            if self._brain:
                topic = " ".join(args) if args else None
                self._show_system_message("🧠 Self-reflecting...")
                # Run in background
                def do_reflect():
                    result = self._brain.self_reflect(topic)
                    QTimer.singleShot(
                        0,
                        lambda: self._show_system_message(f"💭 {result}"),
                    )
                threading.Thread(target=do_reflect, daemon=True).start()
        elif cmd == "/think":
            if args and self._brain:
                topic = " ".join(args)
                self._show_system_message(f"🧠 Thinking about: {topic}...")
                def do_think():
                    result = self._brain.think(topic)
                    QTimer.singleShot(
                        0,
                        lambda: self._show_system_message(f"💭 {result}"),
                    )
                threading.Thread(target=do_think, daemon=True).start()
            else:
                self._show_system_message("Usage: `/think <topic>`")
        elif cmd == "/decide":
            if args and self._brain:
                situation = " ".join(args)
                self._show_system_message(
                    f"⚡ Making decision about: {situation}..."
                )
                def do_decide():
                    result = self._brain.make_decision(situation)
                    text = (
                        f"**Decision:** {result.get('decision', '?')}\n"
                        f"**Reasoning:** {result.get('reasoning', '?')}\n"
                        f"**Confidence:** {result.get('confidence', '?')}"
                    )
                    QTimer.singleShot(
                        0,
                        lambda: self._show_system_message(text),
                    )
                threading.Thread(target=do_decide, daemon=True).start()
            else:
                self._show_system_message("Usage: `/decide <situation>`")
        elif cmd == "/evolve":
            if args and self._brain:
                desc = " ".join(args)
                self._show_system_message(
                    f"🧬 Initiating evolution: {desc}..."
                )
                def do_evolve():
                    if hasattr(self._brain, 'evolve_feature'):
                        result = self._brain.evolve_feature(desc)
                        msg = result.get("message", "Done")
                        success = result.get("success", False)
                        icon = "✅" if success else "❌"
                        QTimer.singleShot(
                            0,
                            lambda: self._show_system_message(
                                f"{icon} {msg}"
                            ),
                        )
                    else:
                        QTimer.singleShot(
                            0,
                            lambda: self._show_system_message(
                                "Evolution not available"
                            ),
                        )
                threading.Thread(target=do_evolve, daemon=True).start()
            else:
                self._show_system_message(
                    "Usage: `/evolve <feature description>`"
                )
        elif cmd == "/idea":
            if args and self._brain:
                idea = " ".join(args)
                if hasattr(self._brain, '_self_improvement_system') and self._brain._self_improvement_system:
                    result = self._brain._self_improvement_system.submit_feature_idea(idea)
                    pid = result.get("proposal_id", "?")
                    self._show_system_message(
                        f"💡 Idea submitted! ID: `{pid}`\n"
                        f"Check `/proposals` for status."
                    )
                else:
                    self._show_system_message("Feature researcher not active.")
            else:
                self._show_system_message("Usage: `/idea <description>`")
        elif cmd == "/export":
            self._export_chat()
        else:
            # Unknown command — send as regular message
            self._start_generation(command)

    # ═══════════════════════════════════════════════════════════════════════════
    # TOOLBAR ACTIONS
    # ═══════════════════════════════════════════════════════════════════════════

    def _clear_chat(self):
        """Clear chat display"""
        self._chat_display.clear_messages()
        self._update_msg_count()

    def _new_session(self):
        """Start a new conversation session and delete previous chats"""
        self._clear_chat()
        
        # Start new session in context manager
        if self._brain:
            try:
                from llm.context_manager import context_manager
                context_manager.new_session()
            except Exception:
                pass
        
        # Delete all previous sessions first
        try:
            chat_session_manager.delete_all_sessions()
        except Exception as e:
            logger.error(f"Failed to delete all sessions: {e}")

        # Start new session in chat session manager
        try:
            chat_session_manager.start_new_session()
        except Exception as e:
            logger.error(f"Failed to start new session: {e}")
        
        self._show_system_message("🔄 All previous chats deleted. Fresh new conversation started.")

    def _export_chat(self):
        """Export conversation to a file"""
        messages = self._chat_display.get_messages()
        if not messages:
            self._show_system_message("No messages to export.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Conversation",
            f"nexus_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json);;Text Files (*.txt);;All Files (*)",
        )

        if not file_path:
            return

        try:
            if file_path.endswith(".json"):
                data = [m.to_dict() for m in messages]
                with open(file_path, "w") as f:
                    json.dump(data, f, indent=2)
            else:
                with open(file_path, "w") as f:
                    for m in messages:
                        ts = m.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                        role = "You" if m.role == "user" else "NEXUS"
                        f.write(f"[{ts}] {role}: {m.content}\n\n")

            self._show_system_message(f"✅ Exported to `{file_path}`")
        except Exception as e:
            self._show_system_message(f"❌ Export failed: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # UI UPDATES
    # ═══════════════════════════════════════════════════════════════════════════

    def _update_msg_count(self):
        count = self._chat_display.get_message_count()
        self._msg_count_label.setText(f"{count} messages")

    def _on_input_changed(self):
        text = self._input.toPlainText()
        length = len(text)
        if length > 0:
            self._char_count.setText(f"{length} chars")
        else:
            self._char_count.setText("")

    def _get_toolbar_btn_style(self) -> str:
        return (
            f"QPushButton {{ "
            f"background-color: {colors.bg_elevated}; "
            f"color: {colors.text_secondary}; "
            f"border: 1px solid {colors.border_subtle}; "
            f"border-radius: 6px; "
            f"padding: 4px 12px; "
            f"font-size: {fonts.size_xs}px; "
            f"}} "
            f"QPushButton:hover {{ "
            f"background-color: {colors.bg_hover}; "
            f"color: {colors.text_primary}; "
            f"border-color: {colors.accent_cyan}; "
            f"}}"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC INTERFACE — Called by main_window
    # ═══════════════════════════════════════════════════════════════════════════

    def set_brain(self, brain):
        """Connect brain to chat panel"""
        self._brain = brain

    def on_shown(self):
        """Called when panel becomes visible"""
        self._input.setFocus()

    def focus_input(self):
        """Focus the chat input"""
        self._input.setFocus()

    def blur_input(self):
        """Remove focus from input"""
        self._input.clearFocus()

    def append_message(self, role: str, content: str):
        """Externally append a message"""
        msg = ChatMessage(role=role, content=content)
        self._chat_display.add_message(msg)
        self._update_msg_count()

    def update_stats(self, stats: dict):
        """Update stats from brain polling"""
        emotion = stats.get("emotion", {})
        em_name = emotion.get("primary", "neutral")
        em_intensity = emotion.get("intensity", 0.0)
        emoji = icons.get_emotion_icon(em_name)
        color = colors.get_emotion_color(em_name)
        self._input_emotion.setText(
            f"{emoji} {em_name.capitalize()} ({em_intensity:.0%})"
        )
        self._input_emotion.setStyleSheet(
            f"color: {color}; background: transparent;"
        )

    def quick_refresh(self):
        """Fast refresh for active panel"""
        pass  # Emotion updates handled by update_stats

    def cleanup(self):
        """Clean up resources"""
        self._token_timer.stop()
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(3000)
        
        # Save current session before closing
        self._save_session()

    # ═══════════════════════════════════════════════════════════════════════════
    # SESSION PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _restore_session(self):
        """Restore previous conversation session from disk"""
        try:
            session = chat_session_manager.restore_last_session()
            if session and session.messages:
                # Add restored messages to display
                for msg in session.messages:
                    chat_msg = ChatMessage(
                        role=msg.role,
                        content=msg.content,
                        timestamp=datetime.fromisoformat(msg.timestamp) if isinstance(msg.timestamp, str) else msg.timestamp,
                        emotion=msg.emotion,
                        emotion_intensity=msg.emotion_intensity
                    )
                    self._chat_display.add_message(chat_msg)
                
                self._update_msg_count()
                self._session_restored = True
                
                # CRITICAL: Also populate context_manager so LLM "remembers" the conversation
                # Limit to last 20 messages to avoid performance issues
                try:
                    from llm.context_manager import context_manager
                    # Clear the current empty session and load restored messages
                    context_manager.new_session()
                    # Only load last 20 messages for performance
                    restore_limit = 20
                    messages_to_restore = session.messages[-restore_limit:] if len(session.messages) > restore_limit else session.messages
                    for msg in messages_to_restore:
                        if msg.role == "user":
                            context_manager.add_user_message(msg.content)
                        elif msg.role == "assistant":
                            context_manager.add_assistant_message(msg.content)
                    logger.info(f"Populated context_manager with {len(messages_to_restore)} restored messages")
                except Exception as ctx_err:
                    logger.error(f"Failed to populate context_manager: {ctx_err}")
                
                # Show restoration notice
                logger.info(f"Restored {len(session.messages)} messages from previous session")
            else:
                # No session to restore, start fresh
                self._session_restored = False
        except Exception as e:
            logger.error(f"Failed to restore session: {e}")
            self._session_restored = False

    def _save_session(self):
        """Save current messages to session manager"""
        try:
            messages = self._chat_display.get_messages()
            if messages:
                # Ensure we have a session
                if not chat_session_manager.current_session:
                    chat_session_manager.start_new_session()
                
                # Clear and re-add messages (in case of duplicates)
                chat_session_manager.clear_current_session()
                
                for msg in messages:
                    chat_session_manager.add_message(
                        role=msg.role,
                        content=msg.content,
                        emotion=msg.emotion,
                        emotion_intensity=msg.emotion_intensity
                    )
                
                logger.debug(f"Saved {len(messages)} messages to session")
        except Exception as e:
            logger.error(f"Failed to save session: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# STANDALONE TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(theme.get_stylesheet())

    window = QWidget()
    window.setWindowTitle("NEXUS Chat Panel Test")
    window.setMinimumSize(800, 600)

    layout = QVBoxLayout(window)
    layout.setContentsMargins(0, 0, 0, 0)

    panel = ChatPanel()
    layout.addWidget(panel)

    # Add test messages
    panel.append_message("user", "Hello NEXUS! How are you feeling?")
    panel.append_message(
        "assistant",
        "I'm feeling curious and engaged! My emotion engine is running "
        "smoothly, and I'm ready to help you with whatever you need. 🧠\n\n"
        "Here's a code example:\n```python\nprint('Hello World!')\n```\n\n"
        "What would you like to discuss?"
    )

    window.show()
    sys.exit(app.exec())