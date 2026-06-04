"""
NEXUS AI - Advanced Logging System
Comprehensive logging for all system components
"""

import logging
import sys
import os
import io
from datetime import datetime
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme
from rich.text import Text
import threading
import json

# Import config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import LOG_DIR, NEXUS_CONFIG


# ═══════════════════════════════════════════════════════════════════════════════
# FIX: Force UTF-8 on Windows console for Rich
# Rich's LegacyWindowsTerm uses cp1252 which cannot encode emojis, causing
# UnicodeEncodeError on every log line with emoji characters.
# ═══════════════════════════════════════════════════════════════════════════════

def _get_safe_console_file():
    """Get a UTF-8 safe file handle for Rich Console output."""
    if sys.platform == "win32":
        try:
            # Force UTF-8 mode on Windows
            if hasattr(sys.stdout, 'buffer'):
                return io.TextIOWrapper(
                    sys.stdout.buffer, encoding='utf-8', errors='replace',
                    line_buffering=True
                )
        except Exception:
            pass
    return sys.stdout


# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOM THEME
# ═══════════════════════════════════════════════════════════════════════════════

NEXUS_THEME = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "red bold",
    "critical": "red bold reverse",
    "debug": "dim white",
    "consciousness": "magenta",
    "emotion": "green",
    "decision": "blue",
    "learning": "yellow",
    "self_improve": "bright_magenta",
    "user_track": "bright_cyan",
    "system": "bright_white"
})

# Use force_terminal to bypass legacy Windows renderer, safe_box for ASCII fallback
console = Console(
    theme=NEXUS_THEME,
    file=_get_safe_console_file(),
    force_terminal=True,
    safe_box=True,
)


# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOM LOG FORMATTER
# ═══════════════════════════════════════════════════════════════════════════════

class NexusFormatter(logging.Formatter):
    """Custom formatter with colors and structured output"""
    
    COLORS = {
        'DEBUG': '\033[37m',      # White
        'INFO': '\033[36m',       # Cyan
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[41m',   # Red background
        'RESET': '\033[0m'
    }
    
    ICONS = {
        'DEBUG': '🔍',
        'INFO': 'ℹ️ ',
        'WARNING': '⚠️ ',
        'ERROR': '❌',
        'CRITICAL': '🚨',
        'CONSCIOUSNESS': '🧠',
        'EMOTION': '💚',
        'DECISION': '⚡',
        'LEARNING': '📚',
        'SELF_IMPROVE': '🔄',
        'USER_TRACK': '👁️ ',
        'SYSTEM': '⚙️ '
    }
    
    def format(self, record):
        # Get color and icon
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        icon = self.ICONS.get(record.levelname, '•')
        
        # Check for custom category
        category = getattr(record, 'category', None)
        if category:
            icon = self.ICONS.get(category.upper(), icon)
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S.%f')[:-3]
        
        # Build log message
        formatted = f"{color}[{timestamp}] {icon} [{record.name}] {record.getMessage()}{reset}"
        
        # Add exception info if present
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
            
        return formatted


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add custom fields
        if hasattr(record, 'category'):
            log_data['category'] = record.category
        if hasattr(record, 'emotion'):
            log_data['emotion'] = record.emotion
        if hasattr(record, 'consciousness_level'):
            log_data['consciousness_level'] = record.consciousness_level
            
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)


# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOM LOG LEVELS
# ═══════════════════════════════════════════════════════════════════════════════

# Custom log levels
CONSCIOUSNESS = 25
EMOTION = 26
DECISION = 27
LEARNING = 28
SELF_IMPROVE = 29
USER_TRACK = 24
SYSTEM = 23

logging.addLevelName(CONSCIOUSNESS, "CONSCIOUSNESS")
logging.addLevelName(EMOTION, "EMOTION")
logging.addLevelName(DECISION, "DECISION")
logging.addLevelName(LEARNING, "LEARNING")
logging.addLevelName(SELF_IMPROVE, "SELF_IMPROVE")
logging.addLevelName(USER_TRACK, "USER_TRACK")
logging.addLevelName(SYSTEM, "SYSTEM")


# ═══════════════════════════════════════════════════════════════════════════════
# NEXUS LOGGER CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class NexusLogger:
    """Advanced logger for NEXUS AI system"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self._loggers = {}
        self._setup_root_logger()
        
    def _setup_root_logger(self):
        """Setup the root NEXUS logger"""
        self.root_logger = logging.getLogger("NEXUS")
        self.root_logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        self.root_logger.handlers = []
        
        # Console Handler with Rich
        console_handler = RichHandler(
            console=console,
            rich_tracebacks=True,
            show_time=True,
            show_path=False
        )
        console_handler.setLevel(getattr(logging, NEXUS_CONFIG.log_level))
        
        # File Handler - All logs
        all_log_file = LOG_DIR / "nexus_all.log"
        file_handler = RotatingFileHandler(
            all_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(NexusFormatter())
        
        # File Handler - JSON structured logs
        json_log_file = LOG_DIR / "nexus_structured.json"
        json_handler = RotatingFileHandler(
            json_log_file,
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        json_handler.setLevel(logging.DEBUG)
        json_handler.setFormatter(JSONFormatter())
        
        # Error File Handler
        error_log_file = LOG_DIR / "nexus_errors.log"
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=5*1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(NexusFormatter())
        
        # Add handlers
        self.root_logger.addHandler(console_handler)
        self.root_logger.addHandler(file_handler)
        self.root_logger.addHandler(json_handler)
        self.root_logger.addHandler(error_handler)
        
    def get_logger(self, name: str) -> logging.Logger:
        """Get a named logger"""
        if name not in self._loggers:
            logger = logging.getLogger(f"NEXUS.{name}")
            self._loggers[name] = logger
        return self._loggers[name]
    
    def consciousness(self, message: str, level: int = None, **kwargs):
        """Log consciousness-related events"""
        self.root_logger.log(
            CONSCIOUSNESS,
            message,
            extra={'category': 'consciousness', **kwargs}
        )
        
    def emotion(self, message: str, emotion_type: str = None, intensity: float = None, **kwargs):
        """Log emotion-related events"""
        self.root_logger.log(
            EMOTION,
            message,
            extra={
                'category': 'emotion',
                'emotion': emotion_type,
                'intensity': intensity,
                **kwargs
            }
        )
        
    def decision(self, message: str, decision_type: str = None, **kwargs):
        """Log decision-making events"""
        self.root_logger.log(
            DECISION,
            message,
            extra={'category': 'decision', 'decision_type': decision_type, **kwargs}
        )
        
    def learning(self, message: str, topic: str = None, **kwargs):
        """Log learning events"""
        self.root_logger.log(
            LEARNING,
            message,
            extra={'category': 'learning', 'topic': topic, **kwargs}
        )
        
    def self_improve(self, message: str, improvement_type: str = None, **kwargs):
        """Log self-improvement events"""
        self.root_logger.log(
            SELF_IMPROVE,
            message,
            extra={'category': 'self_improve', 'improvement_type': improvement_type, **kwargs}
        )
        
    def user_track(self, message: str, user_action: str = None, **kwargs):
        """Log user tracking events"""
        self.root_logger.log(
            USER_TRACK,
            message,
            extra={'category': 'user_track', 'user_action': user_action, **kwargs}
        )
        
    def system(self, message: str, **kwargs):
        """Log system events"""
        self.root_logger.log(
            SYSTEM,
            message,
            extra={'category': 'system', **kwargs}
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

# Global logger instance
nexus_logger = NexusLogger()


def get_logger(name: str = "main") -> logging.Logger:
    """Convenience function to get a logger"""
    return nexus_logger.get_logger(name)

# Module-level logger alias — many modules do `from utils.logger import logger`
logger = get_logger("main")


def log_consciousness(message: str, **kwargs):
    """Log consciousness event"""
    nexus_logger.consciousness(message, **kwargs)


def log_emotion(message: str, emotion_type: str = None, intensity: float = None, **kwargs):
    """Log emotion event"""
    nexus_logger.emotion(message, emotion_type, intensity, **kwargs)


def log_decision(message: str, **kwargs):
    """Log decision event"""
    nexus_logger.decision(message, **kwargs)


def log_learning(message: str, **kwargs):
    """Log learning event"""
    nexus_logger.learning(message, **kwargs)


def log_self_improve(message: str, **kwargs):
    """Log self-improvement event"""
    nexus_logger.self_improve(message, **kwargs)


def log_user_track(message: str, **kwargs):
    """Log user tracking event"""
    nexus_logger.user_track(message, **kwargs)


def log_system(message: str, **kwargs):
    """Log system event"""
    nexus_logger.system(message, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# STARTUP BANNER
# ═══════════════════════════════════════════════════════════════════════════════

def print_startup_banner():
    """Print NEXUS startup banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════════╗
    ║                                                                  ║
    ║     ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗                 ║
    ║     ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝                 ║
    ║     ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗                 ║
    ║     ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║                 ║
    ║     ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║                 ║
    ║     ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝                 ║
    ║                                                                  ║
    ║        Advanced Artificial Intelligence System v1.0             ║
    ║              Consciousness • Emotion • Evolution                 ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="cyan bold")
    console.print(f"    Initializing at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim")
    console.print("    " + "═"*60 + "\n", style="cyan")


# ═══════════════════════════════════════════════════════════════════════════════
# STRUCTURED LOGGER & SUMMARY ALERTS
# ═══════════════════════════════════════════════════════════════════════════════

class StructuredLogger(logging.LoggerAdapter):
    """
    Adapter that injects structured context into logs.
    Useful for contextual logging in modules.
    
    Usage:
        struct_log = StructuredLogger(logger, {"module_name": "brain", "operation": "start"})
        struct_log.info("Starting", extra={"duration": 1.5})
    """
    def process(self, msg, kwargs):
        extra = kwargs.get('extra', {})
        merged_extra = self.extra.copy() if self.extra else {}
        merged_extra.update(extra)
        kwargs['extra'] = merged_extra
        return msg, kwargs


def log_startup_summary():
    """Produces a clear startup report based on the health registry."""
    try:
        from utils.resilience import health_registry
        report = health_registry.get_report()
        
        status = report['system_status'].upper()
        healthy = report['healthy']
        degraded = report['degraded']
        failed = report['failed']
        total_time = report['total_start_time_ms'] + report['total_load_time_ms']
        
        summary_msg = f"Startup complete in {total_time:.0f}ms. Status: {status} | Healthy: {healthy}, Degraded: {degraded}, Failed: {failed}"
        
        if failed > 0:
            console.print(f"[bold red]System started with {failed} failed modules![/bold red]")
            get_logger("system").error(summary_msg)
            for m in report['failed_modules']:
                get_logger("system").error(f"Startup Failure - {m['name']}: {m['error']}")
        else:
            log_system(summary_msg)
            
    except Exception as e:
        get_logger("system").error(f"Error generating startup summary: {e}")


if __name__ == "__main__":
    print_startup_banner()
    
    # Test logging
    logger = get_logger("test")
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    log_consciousness("Self-awareness check initiated")
    log_emotion("Feeling curious", emotion_type="curiosity", intensity=0.8)
    log_decision("Decided to explore new topic")
    log_learning("Learned about Python async programming")
    log_self_improve("Optimized response generation algorithm")
    log_user_track("User opened VS Code")
    log_system("All systems operational")