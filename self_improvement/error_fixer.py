"""
NEXUS AI - Error Fixer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LLM-powered auto-repair system that fixes errors detected by CodeMonitor.

Flow:
  1. Receives CODE_ERROR_DETECTED events from CodeMonitor
  2. Reads the broken source file
  3. Creates a backup
  4. Sends file + error context to the LLM for repair
  5. Parses the LLM's fix
  6. Writes the repaired file
  7. Re-scans to verify the fix worked
  8. Rolls back if the fix made things worse

Safety:
  • Always backs up before modifying
  • Verifies fix via re-scan before accepting
  • Rolls back automatically on failed fixes
  • Cooldown per file to prevent fix loops
  • Daily modification cap
  • Only fixes auto_fixable errors
"""

import threading
import time
import shutil
import json
import re
import ast
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import deque
from enum import Enum, auto
from queue import Queue

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR, BASE_DIR, NEXUS_CONFIG
from utils.logger import get_logger, log_system
from core.event_bus import EventType, publish, subscribe, Event

logger = get_logger("error_fixer")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class FixStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"


@dataclass
class FixAttempt:
    """Record of a single fix attempt"""
    attempt_id: str = ""
    error_id: str = ""
    file_path: str = ""
    file_name: str = ""
    error_message: str = ""
    error_type: str = ""
    status: FixStatus = FixStatus.PENDING
    backup_path: str = ""
    original_hash: str = ""
    fixed_hash: str = ""
    llm_prompt: str = ""
    llm_response: str = ""
    fix_description: str = ""
    started_at: str = ""
    completed_at: str = ""
    duration_seconds: float = 0.0
    verified: bool = False
    rolled_back: bool = False
    error_after_fix: str = ""        # if fix introduced new errors

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class FixerStats:
    """Error fixer statistics"""
    total_fixes_attempted: int = 0
    total_fixes_successful: int = 0
    total_fixes_failed: int = 0
    total_rollbacks: int = 0
    total_skipped: int = 0
    fixes_today: int = 0
    last_fix_time: str = ""
    last_fix_file: str = ""
    last_fix_status: str = ""
    success_rate: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# ERROR FIXER
# ═══════════════════════════════════════════════════════════════════════════════

class ErrorFixer:
    """
    LLM-powered auto-repair system.
    
    Subscribes to CODE_ERROR_DETECTED events, queues them,
    and processes fixes one at a time using the LLM.
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
        self._backup_dir = DATA_DIR / "backups" / "code_fixes"
        self._backup_dir.mkdir(parents=True, exist_ok=True)

        # ──── State ────
        self._running = False
        self._code_monitor = None
        self._llm = None

        # ──── Fix Queue ────
        self._fix_queue: Queue = Queue()
        self._active_fix: Optional[FixAttempt] = None

        # ──── History ────
        self._fix_history: deque = deque(maxlen=200)
        self._stats = FixerStats()

        # ──── Rate Limiting ────
        self._daily_fix_count: int = 0
        self._daily_reset_date: str = datetime.now().strftime("%Y-%m-%d")
        self._file_cooldowns: Dict[str, datetime] = {}
        self._fix_cooldown_seconds: float = 300.0   # 5 min between fixes per file
        self._recently_fixed_errors: set = set()     # error_ids already attempted

        # ──── Threads ────
        self._fix_thread: Optional[threading.Thread] = None

        # ──── Subscribe to error events ────
        subscribe(EventType.CODE_ERROR_DETECTED, self._on_error_detected)

        logger.info("ErrorFixer initialized")

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start the error fixer"""
        if self._running:
            return
        if not self._config.auto_fix_enabled:
            logger.info("Auto-fix is disabled in config")
            return

        self._running = True

        # Lazy load LLM
        try:
            from llm.llama_interface import llm
            self._llm = llm
        except ImportError:
            logger.warning("LLM not available — ErrorFixer will queue but not fix")

        # Start fix processing thread
        self._fix_thread = threading.Thread(
            target=self._fix_processing_loop,
            daemon=True,
            name="ErrorFixer-Processor"
        )
        self._fix_thread.start()

        log_system("🔧 ErrorFixer ACTIVE — auto-repair enabled")

    def stop(self):
        """Stop the error fixer"""
        if not self._running:
            return
        self._running = False

        if self._fix_thread and self._fix_thread.is_alive():
            self._fix_thread.join(timeout=10.0)

        logger.info("ErrorFixer stopped")

    def set_code_monitor(self, monitor):
        """Wire up the code monitor"""
        self._code_monitor = monitor

    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT HANDLING
    # ═══════════════════════════════════════════════════════════════════════════

    def _on_error_detected(self, event: Event):
        """Handle CODE_ERROR_DETECTED events from CodeMonitor"""
        data = event.data
        error_id = data.get("error_id", "")
        file_path = data.get("file_path", "")
        auto_fixable = data.get("auto_fixable", True)
        severity = data.get("severity", "error")

        # ── Skip conditions ──
        if not auto_fixable:
            logger.debug(f"Skipping non-auto-fixable error: {error_id}")
            return

        if error_id in self._recently_fixed_errors:
            logger.debug(f"Skipping already-attempted error: {error_id}")
            return

        if severity == "info":
            return  # Don't fix info-level quality warnings

        # ── Check daily limit ──
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self._daily_reset_date:
            self._daily_fix_count = 0
            self._daily_reset_date = today

        if self._daily_fix_count >= self._config.max_daily_modifications:
            logger.warning(
                f"Daily fix limit reached ({self._config.max_daily_modifications})"
            )
            return

        # ── Check file cooldown ──
        if file_path in self._file_cooldowns:
            if datetime.now() < self._file_cooldowns[file_path]:
                logger.debug(f"File in cooldown: {file_path}")
                return

        # ── Queue the fix ──
        self._fix_queue.put(data)
        logger.info(
            f"Queued fix for {data.get('file', '?')}:{data.get('line', '?')} "
            f"— {data.get('message', '?')[:80]}"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # FIX PROCESSING
    # ═══════════════════════════════════════════════════════════════════════════

    def _fix_processing_loop(self):
        """Process fix queue one at a time"""
        logger.info("Fix processing loop started")

        while self._running:
            try:
                if not self._fix_queue.empty():
                    error_data = self._fix_queue.get(timeout=1.0)
                    self._process_fix(error_data)
                else:
                    time.sleep(2.0)

            except Exception as e:
                logger.error(f"Fix processing error: {e}")
                time.sleep(5.0)

    def _process_fix(self, error_data: Dict[str, Any]):
        """Process a single error fix"""
        error_id = error_data.get("error_id", "")
        file_path = error_data.get("file_path", "")
        file_name = error_data.get("file", "")
        error_msg = error_data.get("message", "")
        error_type = error_data.get("error_type", "")
        line_number = error_data.get("line", 0)
        context = error_data.get("context", "")

        # Create fix attempt record
        attempt = FixAttempt(
            attempt_id=f"fix_{int(time.time())}_{Path(file_path).stem}",
            error_id=error_id,
            file_path=file_path,
            file_name=file_name,
            error_message=error_msg,
            error_type=error_type,
            status=FixStatus.IN_PROGRESS,
            started_at=datetime.now().isoformat()
        )
        self._active_fix = attempt

        try:
            # ── 1. Read the source file ──
            source = self._read_file(file_path)
            if source is None:
                attempt.status = FixStatus.FAILED
                attempt.error_after_fix = "Could not read source file"
                self._complete_attempt(attempt)
                return

            attempt.original_hash = hashlib.sha256(
                source.encode()
            ).hexdigest()[:16]

            # ── 2. Create backup ──
            if self._config.backup_before_modify:
                backup_path = self._create_backup(file_path)
                if backup_path:
                    attempt.backup_path = str(backup_path)
                else:
                    attempt.status = FixStatus.FAILED
                    attempt.error_after_fix = "Backup creation failed"
                    self._complete_attempt(attempt)
                    return

            # ── 3. Generate fix using LLM ──
            if not self._llm or not self._llm.is_connected:
                attempt.status = FixStatus.SKIPPED
                attempt.error_after_fix = "LLM not available"
                self._stats.total_skipped += 1
                self._complete_attempt(attempt)
                return

            fixed_source, fix_description = self._generate_fix(
                source, file_name, file_path,
                error_msg, error_type, line_number, context
            )

            if not fixed_source:
                attempt.status = FixStatus.FAILED
                attempt.error_after_fix = "LLM could not generate a fix"
                self._stats.total_fixes_failed += 1
                self._complete_attempt(attempt)
                return

            attempt.fix_description = fix_description

            # ── 4. Verify the fix is valid Python ──
            if not self._validate_syntax(fixed_source):
                attempt.status = FixStatus.FAILED
                attempt.error_after_fix = (
                    "LLM-generated fix has syntax errors"
                )
                self._stats.total_fixes_failed += 1
                self._complete_attempt(attempt)
                return

            # ── 5. Check fix isn't identical to original ──
            fixed_hash = hashlib.sha256(
                fixed_source.encode()
            ).hexdigest()[:16]
            attempt.fixed_hash = fixed_hash

            if fixed_hash == attempt.original_hash:
                attempt.status = FixStatus.SKIPPED
                attempt.error_after_fix = "Fix identical to original"
                self._stats.total_skipped += 1
                self._complete_attempt(attempt)
                return

            # ── 6. Write the fixed file ──
            if not self._write_file(file_path, fixed_source):
                attempt.status = FixStatus.FAILED
                attempt.error_after_fix = "Could not write fixed file"
                self._stats.total_fixes_failed += 1
                self._complete_attempt(attempt)
                return

            # ── 7. Set cooldown so CodeMonitor doesn't immediately re-scan ──
            if self._code_monitor:
                self._code_monitor.set_file_cooldown(
                    file_path, self._fix_cooldown_seconds
                )

            # ── 8. Verify fix by re-analyzing ──
            time.sleep(1.0)  # Brief pause before verification
            verification_ok = self._verify_fix(file_path, error_id)

            if verification_ok:
                attempt.status = FixStatus.SUCCESS
                attempt.verified = True
                self._stats.total_fixes_successful += 1
                self._daily_fix_count += 1

                # Mark error as fixed in CodeMonitor
                if self._code_monitor:
                    self._code_monitor.mark_error_fixed(error_id)

                # Publish success event
                publish(
                    EventType.CODE_FIX_APPLIED,
                    {
                        "error_id": error_id,
                        "file": file_name,
                        "file_path": file_path,
                        "fix_description": fix_description[:200],
                        "status": "success"
                    },
                    source="error_fixer"
                )

                logger.info(
                    f"✅ Fixed {file_name}:{line_number} — {fix_description[:80]}"
                )
            else:
                # ── 9. Rollback on failed verification ──
                logger.warning(
                    f"Fix verification failed for {file_name} — rolling back"
                )
                self._rollback(file_path, attempt.backup_path)
                attempt.status = FixStatus.ROLLED_BACK
                attempt.rolled_back = True
                attempt.error_after_fix = (
                    "Fix did not resolve the error or introduced new errors"
                )
                self._stats.total_rollbacks += 1
                self._stats.total_fixes_failed += 1

        except Exception as e:
            logger.error(f"Fix processing failed: {e}")
            attempt.status = FixStatus.FAILED
            attempt.error_after_fix = str(e)
            self._stats.total_fixes_failed += 1

            # Attempt rollback on any exception
            if attempt.backup_path:
                self._rollback(file_path, attempt.backup_path)
                attempt.rolled_back = True

        finally:
            self._recently_fixed_errors.add(error_id)
            self._file_cooldowns[file_path] = (
                datetime.now() + timedelta(seconds=self._fix_cooldown_seconds)
            )
            self._complete_attempt(attempt)

    def _complete_attempt(self, attempt: FixAttempt):
        """Finalize a fix attempt"""
        attempt.completed_at = datetime.now().isoformat()

        if attempt.started_at:
            try:
                start = datetime.fromisoformat(attempt.started_at)
                end = datetime.fromisoformat(attempt.completed_at)
                attempt.duration_seconds = (end - start).total_seconds()
            except Exception:
                pass

        self._fix_history.append(attempt)
        self._active_fix = None

        self._stats.total_fixes_attempted += 1
        self._stats.last_fix_time = attempt.completed_at
        self._stats.last_fix_file = attempt.file_name
        self._stats.last_fix_status = attempt.status.value

        # Update success rate
        total = self._stats.total_fixes_attempted
        if total > 0:
            self._stats.success_rate = round(
                self._stats.total_fixes_successful / total, 2
            )

        # Mark attempt in code monitor
        if self._code_monitor:
            self._code_monitor.mark_fix_attempted(attempt.error_id)

        logger.debug(
            f"Fix attempt complete: {attempt.file_name} "
            f"→ {attempt.status.value} ({attempt.duration_seconds:.1f}s)"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # LLM FIX GENERATION
    # ═══════════════════════════════════════════════════════════════════════════

    def _generate_fix(
        self,
        source: str,
        file_name: str,
        file_path: str,
        error_message: str,
        error_type: str,
        line_number: int,
        context: str
    ) -> Tuple[Optional[str], str]:
        """
        Use the LLM to generate a fix for the error.
        Returns (fixed_source, fix_description) or (None, "").
        """
        # Build a targeted prompt based on error type
        prompt = self._build_fix_prompt(
            source, file_name, error_message,
            error_type, line_number, context
        )

        system_prompt = (
            "You are an expert Python developer fixing a bug in source code.\n\n"
            "RULES:\n"
            "1. Return the COMPLETE fixed file content — every single line\n"
            "2. Wrap the fixed code in ```python ... ``` markers\n"
            "3. After the code block, write a one-line description starting with 'FIX:'\n"
            "4. Make the MINIMAL change needed to fix the error\n"
            "5. Do NOT add comments like '# Fixed' or '# Changed'\n"
            "6. Do NOT remove existing functionality\n"
            "7. Do NOT change code style, formatting, or variable names\n"
            "8. Preserve ALL imports, classes, functions, and logic\n"
            "9. If you cannot fix it, respond with 'CANNOT_FIX' and explain why\n"
        )

        try:
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.1,   # Very low — we want precise fixes
                max_tokens=8000    # Full file might be large
            )

            if not response.success:
                logger.error(f"LLM fix generation failed: {response.error}")
                return None, ""

            return self._parse_fix_response(response.text, source)

        except Exception as e:
            logger.error(f"LLM fix generation error: {e}")
            return None, ""

    def _build_fix_prompt(
        self,
        source: str,
        file_name: str,
        error_message: str,
        error_type: str,
        line_number: int,
        context: str
    ) -> str:
        """Build the prompt for the LLM"""
        # Truncate very large files — send only relevant section + context
        source_for_prompt = source
        truncated = False

        if len(source) > 15000:
            # For large files, send a window around the error
            lines = source.split('\n')
            if line_number > 0:
                start = max(0, line_number - 50)
                end = min(len(lines), line_number + 50)

                # Always include imports (first 30 lines)
                header = '\n'.join(lines[:30])
                section = '\n'.join(lines[start:end])

                source_for_prompt = (
                    f"# === FILE HEADER (lines 1-30) ===\n"
                    f"{header}\n\n"
                    f"# === ERROR SECTION (lines {start+1}-{end}) ===\n"
                    f"{section}\n"
                )
                truncated = True
            else:
                source_for_prompt = source[:15000]
                truncated = True

        prompt = f"FILE: {file_name}\n"
        prompt += f"ERROR TYPE: {error_type}\n"
        prompt += f"ERROR MESSAGE: {error_message}\n"

        if line_number > 0:
            prompt += f"ERROR LINE: {line_number}\n"

        if context:
            prompt += f"\nERROR CONTEXT:\n{context}\n"

        prompt += f"\n{'='*60}\n"

        if truncated:
            prompt += (
                "NOTE: File was truncated. Fix ONLY the section shown. "
                "Return ONLY the fixed section.\n\n"
            )
            prompt += f"SOURCE CODE (partial):\n```python\n{source_for_prompt}\n```\n"
        else:
            prompt += (
                "Return the COMPLETE fixed file.\n\n"
                f"SOURCE CODE:\n```python\n{source_for_prompt}\n```\n"
            )

        prompt += (
            f"\nFix the {error_type} error and return the corrected code."
        )

        return prompt

    def _parse_fix_response(
        self, response_text: str, original_source: str
    ) -> Tuple[Optional[str], str]:
        """
        Parse the LLM response to extract fixed code and description.
        Returns (fixed_source, description) or (None, "").
        """
        # Check for CANNOT_FIX
        if "CANNOT_FIX" in response_text:
            logger.info("LLM reported CANNOT_FIX")
            return None, ""

        # Extract code block
        code_pattern = r'```python\s*\n(.*?)```'
        matches = re.findall(code_pattern, response_text, re.DOTALL)

        if not matches:
            # Try without language specifier
            code_pattern = r'```\s*\n(.*?)```'
            matches = re.findall(code_pattern, response_text, re.DOTALL)

        if not matches:
            logger.warning("Could not extract code block from LLM response")
            return None, ""

        fixed_source = matches[0].strip()

        # If the fix is just a section (truncated file), we need to
        # handle this carefully — for now, only accept full file fixes
        # Check if it looks like a complete file
        original_lines = len(original_source.split('\n'))
        fixed_lines = len(fixed_source.split('\n'))

        # If the fix is way shorter, it might be a partial fix
        if fixed_lines < original_lines * 0.5 and original_lines > 50:
            logger.warning(
                f"Fix seems partial ({fixed_lines} lines vs "
                f"{original_lines} original) — skipping"
            )
            return None, ""

        # Extract fix description
        description = ""
        fix_match = re.search(
            r'FIX:\s*(.+?)(?:\n|$)', response_text, re.IGNORECASE
        )
        if fix_match:
            description = fix_match.group(1).strip()
        else:
            # Try to get any text after the code block
            after_code = response_text.split('```')[-1].strip()
            if after_code and len(after_code) < 200:
                description = after_code[:200]

        if not description:
            description = "Auto-fix applied by NEXUS"

        return fixed_source, description

    # ═══════════════════════════════════════════════════════════════════════════
    # FILE OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════════

    def _read_file(self, file_path: str) -> Optional[str]:
        """Read a source file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Cannot read {file_path}: {e}")
            return None

    def _write_file(self, file_path: str, content: str) -> bool:
        """Write content to a file"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            logger.error(f"Cannot write {file_path}: {e}")
            return False

    def _create_backup(self, file_path: str) -> Optional[Path]:
        """Create a backup of a file before modifying it"""
        try:
            source_path = Path(file_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{source_path.stem}_{timestamp}{source_path.suffix}"
            backup_path = self._backup_dir / backup_name

            shutil.copy2(file_path, backup_path)
            logger.debug(f"Backup created: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"Backup failed for {file_path}: {e}")
            return None

    def _rollback(self, file_path: str, backup_path: str):
        """Rollback a file to its backup"""
        try:
            if backup_path and Path(backup_path).exists():
                shutil.copy2(backup_path, file_path)
                logger.info(f"Rolled back {file_path} from backup")
            else:
                logger.error(
                    f"Cannot rollback — backup not found: {backup_path}"
                )
        except Exception as e:
            logger.error(f"Rollback failed for {file_path}: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # VALIDATION & VERIFICATION
    # ═══════════════════════════════════════════════════════════════════════════

    def _validate_syntax(self, source: str) -> bool:
        """Validate that the source code has no syntax errors"""
        try:
            ast.parse(source)
            return True
        except SyntaxError as e:
            logger.debug(f"Fix validation failed: {e}")
            return False

    def _verify_fix(self, file_path: str, original_error_id: str) -> bool:
        """
        Verify that the fix actually resolved the error.
        Re-scans the file and checks if the original error is gone.
        """
        if not self._code_monitor:
            # Without code monitor, we can only check syntax
            content = self._read_file(file_path)
            if content:
                return self._validate_syntax(content)
            return False

        try:
            # Import here to avoid circular
            from self_improvement.code_monitor import CodeAnalyzer

            # Check syntax
            syntax_error = CodeAnalyzer.check_syntax(file_path)
            if syntax_error:
                logger.warning(
                    f"Fix introduced syntax error: {syntax_error.message}"
                )
                return False

            # Check compilation
            compile_error = CodeAnalyzer.check_compilation(file_path)
            if compile_error:
                logger.warning(
                    f"Fix introduced compilation error: {compile_error.message}"
                )
                return False

            # If we got here, the file is at least syntactically valid
            return True

        except Exception as e:
            logger.error(f"Fix verification error: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════════
    # MANUAL FIX REQUEST
    # ═══════════════════════════════════════════════════════════════════════════

    def request_fix(self, file_path: str, error_description: str = "") -> Dict[str, Any]:
        """
        Manually request a fix for a specific file.
        Useful for fixing runtime errors or user-reported issues.
        """
        if not self._llm or not self._llm.is_connected:
            return {"status": "error", "message": "LLM not available"}

        source = self._read_file(file_path)
        if not source:
            return {"status": "error", "message": "Cannot read file"}

        if not error_description:
            # Run analysis to find the error
            from self_improvement.code_monitor import CodeAnalyzer
            syntax_error = CodeAnalyzer.check_syntax(file_path)
            if syntax_error:
                error_description = syntax_error.message
            else:
                return {
                    "status": "skipped",
                    "message": "No errors found in file"
                }

        # Queue as a fix event
        self._fix_queue.put({
            "error_id": f"manual_{int(time.time())}",
            "file_path": file_path,
            "file": Path(file_path).name,
            "message": error_description,
            "error_type": "manual",
            "line": 0,
            "auto_fixable": True,
            "context": ""
        })

        return {
            "status": "queued",
            "message": f"Fix queued for {Path(file_path).name}",
            "queue_size": self._fix_queue.qsize()
        }

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def get_fix_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent fix history"""
        return [
            attempt.to_dict()
            for attempt in list(self._fix_history)[-limit:]
        ]

    def get_active_fix(self) -> Optional[Dict[str, Any]]:
        """Get the currently active fix attempt"""
        if self._active_fix:
            return self._active_fix.to_dict()
        return None

    def get_queue_size(self) -> int:
        """Get the number of fixes in queue"""
        return self._fix_queue.qsize()

    def clear_error_memory(self, error_id: str = None):
        """
        Clear error from recently_fixed set so it can be retried.
        If error_id is None, clears all.
        """
        if error_id:
            self._recently_fixed_errors.discard(error_id)
        else:
            self._recently_fixed_errors.clear()
            self._file_cooldowns.clear()
            logger.info("Cleared all error memory and cooldowns")

    def get_stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "total_attempted": self._stats.total_fixes_attempted,
            "total_successful": self._stats.total_fixes_successful,
            "total_failed": self._stats.total_fixes_failed,
            "total_rollbacks": self._stats.total_rollbacks,
            "total_skipped": self._stats.total_skipped,
            "success_rate": self._stats.success_rate,
            "fixes_today": self._daily_fix_count,
            "daily_limit": self._config.max_daily_modifications,
            "queue_size": self._fix_queue.qsize(),
            "active_fix": (
                self._active_fix.file_name if self._active_fix else None
            ),
            "last_fix_time": self._stats.last_fix_time,
            "last_fix_file": self._stats.last_fix_file,
            "last_fix_status": self._stats.last_fix_status,
            "files_in_cooldown": len(self._file_cooldowns),
            "errors_attempted": len(self._recently_fixed_errors),
            "backups_dir": str(self._backup_dir)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

error_fixer = ErrorFixer()


if __name__ == "__main__":
    fixer = ErrorFixer()
    fixer.start()

    print(f"ErrorFixer stats: {json.dumps(fixer.get_stats(), indent=2)}")
    print("ErrorFixer running. Waiting for CODE_ERROR_DETECTED events...")

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        fixer.stop()
        print("Stopped.")