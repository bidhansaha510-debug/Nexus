"""
NEXUS AI - Code Monitor
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
24/7 source code watcher that monitors all NEXUS .py files for:

  • Syntax errors         — ast.parse / py_compile failures
  • Import errors         — broken imports detected via importlib
  • Structural issues     — missing classes, broken signatures
  • File changes          — hash-based change detection
  • Runtime errors        — errors caught from event bus
  • Code quality warnings — bare excepts, TODO bombs, etc.

All errors are tracked in SQLite with full context.
Publishes CODE_ERROR_DETECTED events for the ErrorFixer to consume.
"""

import threading
import time
import ast
import sys
import os
import py_compile
import hashlib
import sqlite3
import json
import traceback
import importlib
import importlib.util
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import defaultdict, deque
from enum import Enum, auto

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR, BASE_DIR, NEXUS_CONFIG
from utils.logger import get_logger, log_system
from core.event_bus import EventType, publish, subscribe, Event

logger = get_logger("code_monitor")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class ErrorSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorType(Enum):
    SYNTAX = "syntax"
    IMPORT = "import"
    STRUCTURAL = "structural"
    RUNTIME = "runtime"
    QUALITY = "quality"
    COMPILATION = "compilation"


class FileStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class CodeError:
    """Represents a single detected error in source code"""
    error_id: str = ""
    file_path: str = ""
    file_name: str = ""
    error_type: ErrorType = ErrorType.SYNTAX
    severity: ErrorSeverity = ErrorSeverity.ERROR
    line_number: int = 0
    column: int = 0
    message: str = ""
    context_lines: str = ""          # surrounding code
    full_traceback: str = ""
    detected_at: str = ""
    fixed: bool = False
    fix_attempted: bool = False
    auto_fixable: bool = True        # whether LLM should attempt
    file_hash: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["error_type"] = self.error_type.value
        d["severity"] = self.severity.value
        return d


@dataclass
class FileInfo:
    """Tracked info about a source file"""
    path: str = ""
    relative_path: str = ""
    file_name: str = ""
    last_hash: str = ""
    last_modified: float = 0.0
    last_checked: str = ""
    status: FileStatus = FileStatus.UNKNOWN
    error_count: int = 0
    warning_count: int = 0
    line_count: int = 0
    size_bytes: int = 0
    has_syntax_error: bool = False
    has_import_error: bool = False
    last_error_message: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class MonitorStats:
    """Code monitor statistics"""
    total_files_tracked: int = 0
    total_scans: int = 0
    total_errors_found: int = 0
    total_errors_fixed: int = 0
    total_warnings: int = 0
    files_with_errors: int = 0
    files_healthy: int = 0
    last_scan_time: str = ""
    last_scan_duration_seconds: float = 0.0
    last_error_found: str = ""
    uptime_seconds: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# CODE ANALYZER — Static Analysis Tools
# ═══════════════════════════════════════════════════════════════════════════════

class CodeAnalyzer:
    """Static analysis utilities for Python source files"""

    @staticmethod
    def check_syntax(file_path: str) -> Optional[CodeError]:
        """Check file for syntax errors using ast.parse"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                source = f.read()

            ast.parse(source, filename=file_path)
            return None  # No error

        except SyntaxError as e:
            context = CodeAnalyzer._get_context_lines(file_path, e.lineno or 0)
            return CodeError(
                error_id=f"syntax_{Path(file_path).stem}_{e.lineno}",
                file_path=file_path,
                file_name=Path(file_path).name,
                error_type=ErrorType.SYNTAX,
                severity=ErrorSeverity.CRITICAL,
                line_number=e.lineno or 0,
                column=e.offset or 0,
                message=str(e.msg) if hasattr(e, 'msg') else str(e),
                context_lines=context,
                full_traceback=traceback.format_exc(),
                detected_at=datetime.now().isoformat(),
                auto_fixable=True
            )
        except Exception as e:
            return CodeError(
                error_id=f"parse_{Path(file_path).stem}",
                file_path=file_path,
                file_name=Path(file_path).name,
                error_type=ErrorType.SYNTAX,
                severity=ErrorSeverity.ERROR,
                message=f"Parse error: {str(e)}",
                full_traceback=traceback.format_exc(),
                detected_at=datetime.now().isoformat(),
                auto_fixable=True
            )

    @staticmethod
    def check_compilation(file_path: str) -> Optional[CodeError]:
        """Check file compilation using py_compile"""
        try:
            py_compile.compile(file_path, doraise=True)
            return None
        except py_compile.PyCompileError as e:
            return CodeError(
                error_id=f"compile_{Path(file_path).stem}",
                file_path=file_path,
                file_name=Path(file_path).name,
                error_type=ErrorType.COMPILATION,
                severity=ErrorSeverity.CRITICAL,
                message=str(e),
                full_traceback=traceback.format_exc(),
                detected_at=datetime.now().isoformat(),
                auto_fixable=True
            )
        except Exception:
            return None  # Non-compilation errors handled elsewhere

    @staticmethod
    def check_imports(file_path: str) -> List[CodeError]:
        """Check for broken imports in a file"""
        errors = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                source = f.read()

            try:
                tree = ast.parse(source, filename=file_path)
            except SyntaxError:
                return []  # Syntax errors caught elsewhere

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name
                        error = CodeAnalyzer._check_single_import(
                            module_name, file_path, node.lineno
                        )
                        if error:
                            errors.append(error)

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        # Only check top-level external imports
                        # Skip relative imports within the project
                        if node.level == 0:
                            top_module = node.module.split('.')[0]
                            # Skip project-internal modules
                            project_modules = {
                                'core', 'consciousness', 'emotions',
                                'personality', 'body', 'monitoring',
                                'self_improvement', 'learning', 'llm',
                                'ui', 'companions', 'utils', 'config'
                            }
                            if top_module not in project_modules:
                                error = CodeAnalyzer._check_single_import(
                                    top_module, file_path, node.lineno
                                )
                                if error:
                                    errors.append(error)

        except Exception as e:
            logger.debug(f"Import check failed for {file_path}: {e}")

        return errors

    @staticmethod
    def _check_single_import(
        module_name: str, file_path: str, line_number: int
    ) -> Optional[CodeError]:
        """Check if a single import is resolvable"""
        # Skip standard library and common packages
        stdlib_and_common = {
            'os', 'sys', 'json', 'time', 'threading', 'datetime',
            'pathlib', 'typing', 'dataclasses', 'enum', 'abc',
            'collections', 'functools', 'itertools', 'math',
            'statistics', 'hashlib', 'uuid', 'copy', 'pickle',
            're', 'io', 'sqlite3', 'subprocess', 'platform',
            'signal', 'asyncio', 'concurrent', 'queue', 'weakref',
            'traceback', 'importlib', 'inspect', 'textwrap',
            'py_compile', 'ast', 'ctypes', 'logging',
            # Common third-party
            'psutil', 'requests', 'pynput', 'ollama',
        }

        top_module = module_name.split('.')[0]
        if top_module in stdlib_and_common:
            return None

        try:
            spec = importlib.util.find_spec(top_module)
            if spec is None:
                return CodeError(
                    error_id=f"import_{Path(file_path).stem}_{top_module}",
                    file_path=file_path,
                    file_name=Path(file_path).name,
                    error_type=ErrorType.IMPORT,
                    severity=ErrorSeverity.WARNING,
                    line_number=line_number,
                    message=f"Module '{module_name}' not found",
                    detected_at=datetime.now().isoformat(),
                    auto_fixable=False  # Can't auto-fix missing packages
                )
        except (ModuleNotFoundError, ValueError):
            return CodeError(
                error_id=f"import_{Path(file_path).stem}_{top_module}",
                file_path=file_path,
                file_name=Path(file_path).name,
                error_type=ErrorType.IMPORT,
                severity=ErrorSeverity.WARNING,
                line_number=line_number,
                message=f"Module '{module_name}' cannot be resolved",
                detected_at=datetime.now().isoformat(),
                auto_fixable=False
            )
        except Exception:
            pass  # Ignore other import resolution issues

        return None

    @staticmethod
    def check_quality(file_path: str) -> List[CodeError]:
        """Check for code quality issues"""
        warnings = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                source = ''.join(lines)

            try:
                tree = ast.parse(source, filename=file_path)
            except SyntaxError:
                return []

            file_name = Path(file_path).name

            for node in ast.walk(tree):
                # ── Bare except clauses ──
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None:
                        warnings.append(CodeError(
                            error_id=f"quality_{Path(file_path).stem}_bare_except_{node.lineno}",
                            file_path=file_path,
                            file_name=file_name,
                            error_type=ErrorType.QUALITY,
                            severity=ErrorSeverity.INFO,
                            line_number=node.lineno,
                            message="Bare 'except:' clause — consider catching specific exceptions",
                            detected_at=datetime.now().isoformat(),
                            auto_fixable=False
                        ))

                # ── Very long functions (>100 lines) ──
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if hasattr(node, 'end_lineno') and node.end_lineno:
                        func_length = node.end_lineno - node.lineno
                        if func_length > 100:
                            warnings.append(CodeError(
                                error_id=f"quality_{Path(file_path).stem}_long_func_{node.lineno}",
                                file_path=file_path,
                                file_name=file_name,
                                error_type=ErrorType.QUALITY,
                                severity=ErrorSeverity.INFO,
                                line_number=node.lineno,
                                message=(
                                    f"Function '{node.name}' is {func_length} lines long "
                                    f"— consider refactoring"
                                ),
                                detected_at=datetime.now().isoformat(),
                                auto_fixable=False
                            ))

            # ── TODO/FIXME/HACK counts ──
            todo_count = 0
            for i, line in enumerate(lines, 1):
                upper = line.upper()
                if any(tag in upper for tag in ['TODO', 'FIXME', 'HACK', 'XXX']):
                    todo_count += 1

            if todo_count > 10:
                warnings.append(CodeError(
                    error_id=f"quality_{Path(file_path).stem}_todos",
                    file_path=file_path,
                    file_name=file_name,
                    error_type=ErrorType.QUALITY,
                    severity=ErrorSeverity.INFO,
                    message=f"File has {todo_count} TODO/FIXME/HACK comments",
                    detected_at=datetime.now().isoformat(),
                    auto_fixable=False
                ))

            # ── Very large file (>1000 lines) ──
            if len(lines) > 1000:
                warnings.append(CodeError(
                    error_id=f"quality_{Path(file_path).stem}_large_file",
                    file_path=file_path,
                    file_name=file_name,
                    error_type=ErrorType.QUALITY,
                    severity=ErrorSeverity.INFO,
                    message=f"File is {len(lines)} lines — consider splitting",
                    detected_at=datetime.now().isoformat(),
                    auto_fixable=False
                ))

        except Exception as e:
            logger.debug(f"Quality check failed for {file_path}: {e}")

        return warnings[:10]  # Cap warnings per file

    @staticmethod
    def _get_context_lines(
        file_path: str, line_number: int, context: int = 5
    ) -> str:
        """Get surrounding lines of code for context"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()

            start = max(0, line_number - context - 1)
            end = min(len(lines), line_number + context)

            result = []
            for i in range(start, end):
                marker = ">>>" if i == line_number - 1 else "   "
                result.append(f"{marker} {i + 1:4d} | {lines[i].rstrip()}")

            return "\n".join(result)

        except Exception:
            return ""

    @staticmethod
    def get_file_hash(file_path: str) -> str:
        """Get SHA256 hash of file contents"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()[:16]
        except Exception:
            return ""

    @staticmethod
    def count_lines(file_path: str) -> int:
        """Count lines in a file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return sum(1 for _ in f)
        except Exception:
            return 0


# ═══════════════════════════════════════════════════════════════════════════════
# CODE MONITOR
# ═══════════════════════════════════════════════════════════════════════════════

class CodeMonitor:
    """
    24/7 source code monitoring system.

    Watches all .py files in the NEXUS project directory.
    Detects changes via file hashing, runs analysis on changed files,
    and publishes errors for the ErrorFixer to handle.

    Data Flow:
      File System → change detection → analysis → errors
                                                    ↓
                                          CODE_ERROR_DETECTED event
                                                    ↓
                                              ErrorFixer
    """

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

        # ──── Configuration ────
        self._config = NEXUS_CONFIG.self_improvement
        self._project_root = BASE_DIR
        self._scan_interval = self._config.code_check_interval  # 60s default

        # ──── Directories to watch ────
        self._watch_dirs = [
            self._project_root / "core",
            self._project_root / "consciousness",
            self._project_root / "emotions",
            self._project_root / "personality",
            self._project_root / "body",
            self._project_root / "monitoring",
            self._project_root / "self_improvement",
            self._project_root / "learning",
            self._project_root / "llm",
            self._project_root / "ui",
            self._project_root / "companions",
            self._project_root / "utils",
        ]
        # Also watch root-level .py files
        self._watch_root_files = True

        # ──── Files to exclude ────
        self._exclude_patterns = {
            '__pycache__', '.git', '.venv', 'venv', 'env',
            'node_modules', '.idea', '.vscode', 'data'
        }
        self._exclude_files = {
            'setup.py', 'conftest.py'
        }

        # ──── State ────
        self._running = False
        self._tracked_files: Dict[str, FileInfo] = {}
        self._active_errors: Dict[str, CodeError] = {}  # error_id → error
        self._error_history: deque = deque(maxlen=500)
        self._recently_fixed: Set[str] = set()  # file paths recently fixed
        self._fix_cooldown: Dict[str, datetime] = {}  # file → last fix time
        self._stats = MonitorStats()
        self._startup_time: Optional[datetime] = None

        # ──── Error callbacks ────
        self._error_callbacks: List = []

        # ──── Database ────
        self._db_path = DATA_DIR / "backups" / "code_monitor.db"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_lock = threading.Lock()
        self._init_database()

        # ──── Threads ────
        self._scan_thread: Optional[threading.Thread] = None

        # ──── Subscribe to runtime errors ────
        subscribe(EventType.SYSTEM_ERROR, self._on_runtime_error)

        logger.info("CodeMonitor initialized")

    # ═══════════════════════════════════════════════════════════════════════════
    # DATABASE
    # ═══════════════════════════════════════════════════════════════════════════

    def _init_database(self):
        with self._db_lock:
            conn = sqlite3.connect(str(self._db_path))
            cursor = conn.cursor()
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS tracked_files (
                    path TEXT PRIMARY KEY,
                    relative_path TEXT,
                    file_name TEXT,
                    last_hash TEXT,
                    last_modified REAL,
                    last_checked TEXT,
                    status TEXT DEFAULT 'unknown',
                    error_count INTEGER DEFAULT 0,
                    warning_count INTEGER DEFAULT 0,
                    line_count INTEGER DEFAULT 0,
                    size_bytes INTEGER DEFAULT 0,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS code_errors (
                    error_id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    file_name TEXT,
                    error_type TEXT,
                    severity TEXT,
                    line_number INTEGER,
                    column_offset INTEGER,
                    message TEXT,
                    context_lines TEXT,
                    full_traceback TEXT,
                    detected_at TEXT,
                    fixed INTEGER DEFAULT 0,
                    fix_attempted INTEGER DEFAULT 0,
                    auto_fixable INTEGER DEFAULT 1,
                    file_hash TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS scan_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_time TEXT NOT NULL,
                    files_scanned INTEGER,
                    files_changed INTEGER,
                    errors_found INTEGER,
                    warnings_found INTEGER,
                    duration_seconds REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_errors_file
                    ON code_errors(file_path);
                CREATE INDEX IF NOT EXISTS idx_errors_type
                    ON code_errors(error_type);
                CREATE INDEX IF NOT EXISTS idx_errors_fixed
                    ON code_errors(fixed);
            """)
            conn.commit()
            conn.close()

    def _db_execute(
        self, query: str, params: tuple = (), fetch: bool = False
    ) -> Any:
        with self._db_lock:
            try:
                conn = sqlite3.connect(str(self._db_path))
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                result = cursor.fetchall() if fetch else cursor.lastrowid
                conn.commit()
                conn.close()
                return result
            except Exception as e:
                logger.error(f"Code monitor DB error: {e}")
                return [] if fetch else None

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start code monitoring"""
        if self._running:
            return
        if not self._config.code_monitoring_enabled:
            logger.info("Code monitoring is disabled in config")
            return

        self._running = True
        self._startup_time = datetime.now()

        # Initial full scan
        self._full_scan()

        # Start background scanning
        self._scan_thread = threading.Thread(
            target=self._scan_loop,
            daemon=True,
            name="CodeMonitor-Scanner"
        )
        self._scan_thread.start()

        log_system(
            f"🔍 CodeMonitor ACTIVE — watching {len(self._tracked_files)} files"
        )

    def stop(self):
        """Stop code monitoring"""
        if not self._running:
            return

        self._running = False

        if self._scan_thread and self._scan_thread.is_alive():
            self._scan_thread.join(timeout=5.0)

        logger.info("CodeMonitor stopped")

    # ═══════════════════════════════════════════════════════════════════════════
    # FILE DISCOVERY
    # ═══════════════════════════════════════════════════════════════════════════

    def _discover_files(self) -> List[Path]:
        """Find all .py files to monitor"""
        files = []

        # Root-level files
        if self._watch_root_files:
            for f in self._project_root.glob("*.py"):
                if f.name not in self._exclude_files:
                    files.append(f)

        # Package directories
        for watch_dir in self._watch_dirs:
            if not watch_dir.exists():
                continue

            for f in watch_dir.rglob("*.py"):
                # Check exclusions
                parts = set(f.relative_to(self._project_root).parts)
                if parts & self._exclude_patterns:
                    continue
                if f.name in self._exclude_files:
                    continue
                files.append(f)

        return sorted(set(files))

    # ═══════════════════════════════════════════════════════════════════════════
    # SCANNING
    # ═══════════════════════════════════════════════════════════════════════════

    def _scan_loop(self):
        """Background scanning loop"""
        logger.info(
            f"Code scan loop started (interval: {self._scan_interval}s)"
        )

        while self._running:
            try:
                time.sleep(self._scan_interval)
                self._incremental_scan()
            except Exception as e:
                logger.error(f"Scan loop error: {e}")
                time.sleep(30)

    def _full_scan(self):
        """Full scan of all files — runs on startup"""
        start = time.time()
        files = self._discover_files()
        errors_found = 0
        warnings_found = 0
        files_with_errors = 0

        for file_path in files:
            try:
                file_errors, file_warnings = self._analyze_file(file_path)
                errors_found += len(file_errors)
                warnings_found += len(file_warnings)
                if file_errors:
                    files_with_errors += 1
            except Exception as e:
                logger.debug(f"Error scanning {file_path}: {e}")

        elapsed = time.time() - start

        self._stats.total_files_tracked = len(self._tracked_files)
        self._stats.total_scans += 1
        self._stats.files_with_errors = files_with_errors
        self._stats.files_healthy = len(self._tracked_files) - files_with_errors
        self._stats.last_scan_time = datetime.now().isoformat()
        self._stats.last_scan_duration_seconds = round(elapsed, 2)

        # Log scan history
        self._db_execute(
            """INSERT INTO scan_history 
               (scan_time, files_scanned, files_changed, errors_found, 
                warnings_found, duration_seconds)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                datetime.now().isoformat(),
                len(files), len(files),  # All files on full scan
                errors_found, warnings_found, elapsed
            )
        )

        logger.info(
            f"Full scan complete: {len(files)} files, "
            f"{errors_found} errors, {warnings_found} warnings "
            f"({elapsed:.1f}s)"
        )

    def _incremental_scan(self):
        """Scan only files that have changed since last check"""
        start = time.time()
        files = self._discover_files()
        changed_files = []
        new_files = []
        removed_files = []

        current_paths = {str(f) for f in files}
        tracked_paths = set(self._tracked_files.keys())

        # Detect new files
        for file_path in files:
            path_str = str(file_path)
            if path_str not in self._tracked_files:
                new_files.append(file_path)
                continue

            # Check if file changed
            current_hash = CodeAnalyzer.get_file_hash(path_str)
            if current_hash != self._tracked_files[path_str].last_hash:
                changed_files.append(file_path)

        # Detect removed files
        for tracked_path in tracked_paths:
            if tracked_path not in current_paths:
                removed_files.append(tracked_path)

        # Remove tracked entries for deleted files
        for path in removed_files:
            del self._tracked_files[path]
            # Clear errors for removed files
            errors_to_remove = [
                eid for eid, err in self._active_errors.items()
                if err.file_path == path
            ]
            for eid in errors_to_remove:
                del self._active_errors[eid]

        # Analyze changed and new files
        errors_found = 0
        warnings_found = 0
        files_to_scan = changed_files + new_files

        for file_path in files_to_scan:
            try:
                # Skip files in cooldown (recently fixed by ErrorFixer)
                path_str = str(file_path)
                if path_str in self._fix_cooldown:
                    cooldown_end = self._fix_cooldown[path_str]
                    if datetime.now() < cooldown_end:
                        continue
                    else:
                        del self._fix_cooldown[path_str]

                file_errors, file_warnings = self._analyze_file(file_path)
                errors_found += len(file_errors)
                warnings_found += len(file_warnings)

            except Exception as e:
                logger.debug(f"Error scanning {file_path}: {e}")

        elapsed = time.time() - start

        # Update stats
        self._stats.total_scans += 1
        self._stats.total_files_tracked = len(self._tracked_files)
        self._stats.last_scan_time = datetime.now().isoformat()
        self._stats.last_scan_duration_seconds = round(elapsed, 2)

        # Count current errors
        error_files = set()
        for err in self._active_errors.values():
            if not err.fixed:
                error_files.add(err.file_path)
        self._stats.files_with_errors = len(error_files)
        self._stats.files_healthy = (
            len(self._tracked_files) - len(error_files)
        )

        if files_to_scan:
            # Store scan record
            self._db_execute(
                """INSERT INTO scan_history 
                   (scan_time, files_scanned, files_changed, errors_found, 
                    warnings_found, duration_seconds)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    datetime.now().isoformat(),
                    len(self._tracked_files),
                    len(files_to_scan),
                    errors_found, warnings_found, elapsed
                )
            )

            if errors_found > 0:
                logger.info(
                    f"Scan: {len(files_to_scan)} changed, "
                    f"{errors_found} errors found"
                )
            else:
                logger.debug(
                    f"Scan: {len(files_to_scan)} changed, "
                    f"all clean ({elapsed:.1f}s)"
                )

    def _analyze_file(
        self, file_path: Path
    ) -> Tuple[List[CodeError], List[CodeError]]:
        """
        Run all analysis checks on a single file.
        Returns (errors, warnings)
        """
        path_str = str(file_path)
        file_name = file_path.name

        # Update file tracking info
        current_hash = CodeAnalyzer.get_file_hash(path_str)
        file_stat = file_path.stat()

        file_info = FileInfo(
            path=path_str,
            relative_path=str(
                file_path.relative_to(self._project_root)
            ),
            file_name=file_name,
            last_hash=current_hash,
            last_modified=file_stat.st_mtime,
            last_checked=datetime.now().isoformat(),
            size_bytes=file_stat.st_size,
            line_count=CodeAnalyzer.count_lines(path_str)
        )

        errors: List[CodeError] = []
        warnings: List[CodeError] = []

        # ── 1. Syntax Check ──
        syntax_error = CodeAnalyzer.check_syntax(path_str)
        if syntax_error:
            syntax_error.file_hash = current_hash
            errors.append(syntax_error)
            file_info.has_syntax_error = True
            file_info.last_error_message = syntax_error.message

        # ── 2. Compilation Check (only if syntax is OK) ──
        if not syntax_error:
            compile_error = CodeAnalyzer.check_compilation(path_str)
            if compile_error:
                compile_error.file_hash = current_hash
                errors.append(compile_error)

        # ── 3. Import Check (only if syntax is OK) ──
        if not syntax_error:
            import_errors = CodeAnalyzer.check_imports(path_str)
            for imp_err in import_errors:
                imp_err.file_hash = current_hash
                if imp_err.severity == ErrorSeverity.WARNING:
                    warnings.append(imp_err)
                else:
                    errors.append(imp_err)
                    file_info.has_import_error = True

        # ── 4. Quality Check (only if syntax is OK) ──
        if not syntax_error:
            quality_warnings = CodeAnalyzer.check_quality(path_str)
            for qw in quality_warnings:
                qw.file_hash = current_hash
                warnings.append(qw)

        # ── Update file status ──
        if errors:
            file_info.status = FileStatus.ERROR
            file_info.error_count = len(errors)
        elif warnings:
            file_info.status = FileStatus.WARNING
            file_info.warning_count = len(warnings)
        else:
            file_info.status = FileStatus.HEALTHY
            file_info.error_count = 0
            file_info.warning_count = 0
            file_info.has_syntax_error = False
            file_info.has_import_error = False
            file_info.last_error_message = ""

        self._tracked_files[path_str] = file_info

        # ── Store file info in DB ──
        self._db_execute(
            """INSERT OR REPLACE INTO tracked_files 
               (path, relative_path, file_name, last_hash, last_modified,
                last_checked, status, error_count, warning_count,
                line_count, size_bytes, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                file_info.path, file_info.relative_path, file_info.file_name,
                file_info.last_hash, file_info.last_modified,
                file_info.last_checked, file_info.status.value,
                file_info.error_count, file_info.warning_count,
                file_info.line_count, file_info.size_bytes,
                datetime.now().isoformat()
            )
        )

        # ── Clear old errors for this file, register new ones ──
        old_error_ids = [
            eid for eid, err in self._active_errors.items()
            if err.file_path == path_str and not err.fixed
        ]
        for eid in old_error_ids:
            del self._active_errors[eid]

        # ── Register and publish new errors ──
        for error in errors:
            self._register_error(error)

        # ── Update stats ──
        self._stats.total_errors_found += len(errors)
        self._stats.total_warnings += len(warnings)
        if errors:
            self._stats.last_error_found = datetime.now().isoformat()

        return errors, warnings

    def _register_error(self, error: CodeError):
        """Register an error and publish event"""
        self._active_errors[error.error_id] = error
        self._error_history.append(error)

        # Store in DB
        self._db_execute(
            """INSERT OR REPLACE INTO code_errors 
               (error_id, file_path, file_name, error_type, severity,
                line_number, column_offset, message, context_lines,
                full_traceback, detected_at, fixed, fix_attempted,
                auto_fixable, file_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                error.error_id, error.file_path, error.file_name,
                error.error_type.value, error.severity.value,
                error.line_number, error.column, error.message,
                error.context_lines, error.full_traceback,
                error.detected_at, 0, 0,
                1 if error.auto_fixable else 0, error.file_hash
            )
        )

        # Publish event for ErrorFixer
        publish(
            EventType.CODE_ERROR_DETECTED,
            {
                "error_id": error.error_id,
                "file": error.file_name,
                "file_path": error.file_path,
                "error_type": error.error_type.value,
                "severity": error.severity.value,
                "line": error.line_number,
                "message": error.message,
                "auto_fixable": error.auto_fixable,
                "context": error.context_lines[:500]
            },
            source="code_monitor"
        )

        logger.warning(
            f"🐛 Error detected in {error.file_name}:{error.line_number} "
            f"[{error.error_type.value}] {error.message}"
        )

        # Notify callbacks
        for callback in self._error_callbacks:
            try:
                callback(error)
            except Exception as e:
                logger.debug(f"Error callback failed: {e}")

    def _on_runtime_error(self, event: Event):
        """Handle runtime errors reported via event bus"""
        data = event.data
        file_path = data.get("file_path", "")
        error_msg = data.get("error", "")
        tb = data.get("traceback", "")
        line = data.get("line_number", 0)

        if not file_path or not error_msg:
            return

        error = CodeError(
            error_id=f"runtime_{Path(file_path).stem}_{int(time.time())}",
            file_path=file_path,
            file_name=Path(file_path).name,
            error_type=ErrorType.RUNTIME,
            severity=ErrorSeverity.ERROR,
            line_number=line,
            message=error_msg,
            full_traceback=tb,
            detected_at=datetime.now().isoformat(),
            auto_fixable=True,
            file_hash=CodeAnalyzer.get_file_hash(file_path)
        )

        # Add context lines if we have a line number
        if line > 0:
            error.context_lines = CodeAnalyzer._get_context_lines(
                file_path, line
            )

        self._register_error(error)

    # ═══════════════════════════════════════════════════════════════════════════
    # ERROR MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════

    def mark_error_fixed(self, error_id: str):
        """Mark an error as fixed (called by ErrorFixer)"""
        if error_id in self._active_errors:
            self._active_errors[error_id].fixed = True
            self._stats.total_errors_fixed += 1

            # Update DB
            self._db_execute(
                "UPDATE code_errors SET fixed = 1 WHERE error_id = ?",
                (error_id,)
            )

            logger.info(f"✅ Error marked fixed: {error_id}")

    def mark_fix_attempted(self, error_id: str):
        """Mark that a fix was attempted (even if it failed)"""
        if error_id in self._active_errors:
            self._active_errors[error_id].fix_attempted = True

            self._db_execute(
                "UPDATE code_errors SET fix_attempted = 1 WHERE error_id = ?",
                (error_id,)
            )

    def set_file_cooldown(self, file_path: str, seconds: float = 120.0):
        """
        Set a cooldown on a file so it isn't immediately re-scanned
        after being modified by the ErrorFixer.
        """
        self._fix_cooldown[file_path] = (
            datetime.now() + timedelta(seconds=seconds)
        )

    def register_error_callback(self, callback):
        """Register a callback for when errors are detected"""
        if callback not in self._error_callbacks:
            self._error_callbacks.append(callback)

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def get_active_errors(self) -> List[Dict[str, Any]]:
        """Get all currently active (unfixed) errors"""
        return [
            err.to_dict() for err in self._active_errors.values()
            if not err.fixed
        ]

    def get_error_by_id(self, error_id: str) -> Optional[CodeError]:
        """Get a specific error by ID"""
        return self._active_errors.get(error_id)

    def get_file_status(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific file"""
        info = self._tracked_files.get(file_path)
        return info.to_dict() if info else None

    def get_all_file_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all tracked files"""
        return {
            path: info.to_dict()
            for path, info in self._tracked_files.items()
        }

    def get_health_report(self) -> Dict[str, Any]:
        """Get overall code health report"""
        total = len(self._tracked_files)
        healthy = sum(
            1 for f in self._tracked_files.values()
            if f.status == FileStatus.HEALTHY
        )
        with_errors = sum(
            1 for f in self._tracked_files.values()
            if f.status == FileStatus.ERROR
        )
        with_warnings = sum(
            1 for f in self._tracked_files.values()
            if f.status == FileStatus.WARNING
        )
        total_lines = sum(
            f.line_count for f in self._tracked_files.values()
        )
        total_size = sum(
            f.size_bytes for f in self._tracked_files.values()
        )

        active_errors = [
            e for e in self._active_errors.values() if not e.fixed
        ]
        error_by_type = defaultdict(int)
        for e in active_errors:
            error_by_type[e.error_type.value] += 1

        health_pct = (healthy / total * 100) if total > 0 else 100

        return {
            "overall_health": f"{health_pct:.0f}%",
            "total_files": total,
            "healthy_files": healthy,
            "files_with_errors": with_errors,
            "files_with_warnings": with_warnings,
            "total_active_errors": len(active_errors),
            "errors_by_type": dict(error_by_type),
            "total_errors_fixed_ever": self._stats.total_errors_fixed,
            "total_lines_of_code": total_lines,
            "total_size_kb": round(total_size / 1024, 1),
            "last_scan": self._stats.last_scan_time,
            "total_scans": self._stats.total_scans,
            "problem_files": [
                {
                    "file": info.relative_path,
                    "errors": info.error_count,
                    "message": info.last_error_message[:100]
                }
                for info in self._tracked_files.values()
                if info.status == FileStatus.ERROR
            ]
        }

    def get_error_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent error history"""
        return [
            err.to_dict()
            for err in list(self._error_history)[-limit:]
        ]

    def get_scan_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent scan history from DB"""
        rows = self._db_execute(
            """SELECT * FROM scan_history 
               ORDER BY scan_time DESC LIMIT ?""",
            (limit,), fetch=True
        )
        return [dict(r) for r in rows] if rows else []

    def force_scan(self, file_path: str = None):
        """Force an immediate scan of one file or all files"""
        if file_path:
            path = Path(file_path)
            if path.exists():
                self._analyze_file(path)
                logger.info(f"Force scanned: {file_path}")
        else:
            self._full_scan()
            logger.info("Force full scan complete")

    def get_file_content(self, file_path: str) -> Optional[str]:
        """Read a source file's content (used by ErrorFixer)"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Cannot read {file_path}: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        uptime = 0.0
        if self._startup_time:
            uptime = (datetime.now() - self._startup_time).total_seconds()

        return {
            "running": self._running,
            "total_files_tracked": self._stats.total_files_tracked,
            "total_scans": self._stats.total_scans,
            "total_errors_found": self._stats.total_errors_found,
            "total_errors_fixed": self._stats.total_errors_fixed,
            "total_warnings": self._stats.total_warnings,
            "files_healthy": self._stats.files_healthy,
            "files_with_errors": self._stats.files_with_errors,
            "active_errors": len([
                e for e in self._active_errors.values() if not e.fixed
            ]),
            "last_scan": self._stats.last_scan_time,
            "last_scan_duration": self._stats.last_scan_duration_seconds,
            "uptime_seconds": round(uptime, 0),
            "scan_interval": self._scan_interval
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

code_monitor = CodeMonitor()


if __name__ == "__main__":
    monitor = CodeMonitor()
    monitor.start()

    print("Monitoring source code... Press Ctrl+C to stop")
    try:
        time.sleep(5)  # Let initial scan complete

        print("\n═══ Health Report ═══")
        report = monitor.get_health_report()
        print(json.dumps(report, indent=2))

        print("\n═══ Active Errors ═══")
        errors = monitor.get_active_errors()
        for err in errors:
            print(
                f"  [{err['severity']}] {err['file_name']}:{err['line_number']}"
                f" — {err['message']}"
            )

        if not errors:
            print("  ✅ No errors found!")

        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        monitor.stop()
        print("\nStopped.")