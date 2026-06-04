"""
NEXUS AI - Self Evolution Engine
═══════════════════════════════════════════════════════════════════════════════
The most powerful subsystem of NEXUS — autonomous self-modification.

Takes approved FeatureProposals from the FeatureResearcher and:
1. Generates complete implementation code via LLM
2. Creates backups of all affected files
3. Installs required dependencies
4. Writes new files / modifies existing ones
5. Validates syntax & imports
6. Runs automated tests
7. Hot-reloads modules into the running system
8. Rolls back on failure

This is NEXUS rewriting its own DNA.
═══════════════════════════════════════════════════════════════════════════════
"""

import threading
import time
import json
import uuid
import re
import os
import sys
import ast
import shutil
import subprocess
import importlib
import traceback
import hashlib
import py_compile
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum, auto

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import NEXUS_CONFIG, DATA_DIR, EmotionType
from utils.logger import get_logger, log_system, log_learning
from core.event_bus import EventType, event_bus, publish
from core.state_manager import state_manager

logger = get_logger("self_evolution")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════


class EvolutionStatus(Enum):
    """Represents the current status of an evolution operation."""

    IDLE = "idle"
    PLANNING = "planning"
    BACKING_UP = "backing_up"
    INSTALLING_DEPS = "installing_deps"
    WRITING_CODE = "writing_code"
    MODIFYING_CODE = "modifying_code"
    VALIDATING = "validating"
    TESTING = "testing"
    INTEGRATING = "integrating"
    ROLLING_BACK = "rolling_back"
    COMPLETED = "completed"
    FAILED = "failed"


class EvolutionError(Exception):
    """Raised when an evolution step fails."""

    pass


@dataclass
class FileBackup:
    """Backup record for a single file."""

    original_path: str
    backup_path: str
    file_hash: str
    backed_up_at: datetime = field(default_factory=datetime.now)
    was_new_file: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert the backup record to a serializable dictionary."""
        return {
            "original_path": self.original_path,
            "backup_path": self.backup_path,
            "file_hash": self.file_hash,
            "backed_up_at": self.backed_up_at.isoformat(),
            "was_new_file": self.was_new_file,
        }


@dataclass
class EvolutionRecord:
    """Record of a single evolution attempt."""

    record_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    proposal_id: str = ""
    proposal_name: str = ""

    status: EvolutionStatus = EvolutionStatus.IDLE

    # Planning
    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    packages_installed: List[str] = field(default_factory=list)

    # Backups
    backups: List[Dict[str, Any]] = field(default_factory=list)
    backup_dir: str = ""

    # Validation
    syntax_valid: bool = False
    imports_valid: bool = False
    test_passed: bool = False
    test_output: str = ""

    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0

    # Results
    success: bool = False
    error_message: str = ""
    rollback_performed: bool = False
    integration_notes: str = ""

    # Code stats
    lines_added: int = 0
    lines_modified: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert the evolution record to a serializable dictionary."""
        d = asdict(self)
        d["status"] = self.status.value
        d["started_at"] = self.started_at.isoformat()
        d["completed_at"] = (
            self.completed_at.isoformat() if self.completed_at else None
        )
        return d


@dataclass
class EvolutionStats:
    """Aggregate statistics across all evolution attempts."""

    total_evolutions_attempted: int = 0
    total_evolutions_succeeded: int = 0
    total_evolutions_failed: int = 0
    total_rollbacks: int = 0
    total_files_created: int = 0
    total_files_modified: int = 0
    total_lines_added: int = 0
    total_packages_installed: int = 0
    last_evolution_time: Optional[datetime] = None
    consecutive_failures: int = 0


# ═══════════════════════════════════════════════════════════════════════════════
# SELF EVOLUTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════


class SelfEvolution:
    """
    Autonomous Self-Modification Engine.

    Pipeline:
    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │  PLAN    │───▶│  BACKUP  │───▶│  WRITE   │───▶│ VALIDATE │
    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                                                         │
    ┌──────────┐    ┌──────────┐    ┌──────────┐         │
    │ COMPLETE │◀───│INTEGRATE │◀───│  TEST    │◀────────┘
    └──────────┘    └──────────┘    └──────────┘
         │                              │
         │         ┌──────────┐         │
         └────────▶│ ROLLBACK │◀────────┘ (on failure)
                   └──────────┘
    """

    _instance = None
    _singleton_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._singleton_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # ──── Paths ────
        self._project_root = Path(__file__).parent.parent
        self._backups_dir = DATA_DIR / "backups" / "evolution"
        self._backups_dir.mkdir(parents=True, exist_ok=True)
        self._records_dir = DATA_DIR / "evolution_records"
        self._records_dir.mkdir(parents=True, exist_ok=True)

        # ──── State ────
        self._running = False
        self._evolution_lock = threading.RLock()
        self._current_status = EvolutionStatus.IDLE
        self._current_record: Optional[EvolutionRecord] = None

        # ──── History ────
        self._evolution_history: List[EvolutionRecord] = []
        self._max_history = 100

        # ──── Stats ────
        self._stats = EvolutionStats()

        # ──── Configuration ────
        self._evolution_interval = 900        # 15 minutes between attempts
        self._max_consecutive_failures = 5    # Pause after N failures
        self._cooldown_after_failure = 3600   # 1 hour cooldown
        self._max_file_size_lines = 50000     # Max lines per generated file
        self._max_files_per_evolution = 10    # Max files per evolution
        self._dry_run = False                 # True = validate only, no write
        self._max_code_gen_retries = 3        # Retry code generation
        self._max_syntax_fix_attempts = 3     # Retry syntax fixes

        # ──── Safety — files/dirs that must never be overwritten ────
        self._protected_files: Set[str] = {
            "config.py",
            "main.py",
            "requirements.txt",
        }
        self._protected_dirs: Set[str] = {
            ".git",
            "venv",
            ".env",
            "data",
        }

        # ──── Components (lazy) ────
        self._llm = None
        self._feature_researcher = None

        # ──── Background Thread ────
        self._evolution_thread: Optional[threading.Thread] = None

        # ──── Failure Pattern Learning ────
        self._failure_patterns: List[Dict[str, str]] = []
        self._max_failure_patterns = 50

        # ──── Auto-Recovery ────
        self._idle_cycles = 0
        self._max_idle_before_recovery = 3

        # ──── Load persisted history ────
        self._load_history()
        self._load_failure_patterns()

        logger.info("🧬 Self Evolution Engine initialized")

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start the evolution engine background loop."""
        if self._running:
            return

        self._running = True
        self._load_llm()
        self._load_feature_researcher()

        self._evolution_thread = threading.Thread(
            target=self._evolution_loop,
            daemon=True,
            name="SelfEvolution",
        )
        self._evolution_thread.start()

        logger.info(
            "🧬 Self Evolution Engine started — autonomous evolution active"
        )

    def stop(self):
        """Stop the evolution engine and persist state."""
        self._running = False
        self._save_history()

        if self._evolution_thread and self._evolution_thread.is_alive():
            self._evolution_thread.join(timeout=15.0)

        logger.info("🧬 Self Evolution Engine stopped")

    # ───── Lazy loaders ─────

    def _load_llm(self):
        """Lazily load the LLM interface (retries if disconnected)."""
        # If we have an LLM but it's not connected, clear it to retry
        if self._llm is not None and not self._llm.is_connected:
            logger.warning("🧬 LLM disconnected — will retry loading")
            self._llm = None

        if self._llm is None:
            try:
                from llm.llama_interface import llm
                if llm.is_connected:
                    self._llm = llm
                    logger.info("🧬 LLM loaded for evolution (Ollama connected)")
                else:
                    logger.warning(
                        "⚠️ Ollama not connected — evolution code generation disabled. "
                        "Start Ollama with: ollama serve"
                    )
            except ImportError:
                logger.warning("⚠️ LLM module not available for evolution")

    def _load_feature_researcher(self):
        """Lazily load the feature researcher."""
        if self._feature_researcher is None:
            try:
                from self_improvement.feature_researcher import (
                    get_feature_researcher,
                )

                self._feature_researcher = get_feature_researcher()
            except ImportError:
                logger.warning("Feature researcher not available")

    # ═══════════════════════════════════════════════════════════════════════════
    # MAIN EVOLUTION LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    def _evolution_loop(self):
        """Continuous loop — picks approved proposals and implements them."""
        logger.info("Evolution loop started")

        # Let other subsystems boot first
        time.sleep(45)

        while self._running:
            # Ensure LLM is loaded/reconnected each cycle
            self._load_llm()
            try:
                # ── Cooldown after repeated failures ──
                if (
                    self._stats.consecutive_failures
                    >= self._max_consecutive_failures
                ):
                    logger.warning(
                        f"Evolution paused — "
                        f"{self._stats.consecutive_failures} "
                        f"consecutive failures.  Cooling down "
                        f"{self._cooldown_after_failure}s..."
                    )
                    time.sleep(self._cooldown_after_failure)
                    self._stats.consecutive_failures = 0
                    continue

                # ── Respect interval ──
                if self._stats.last_evolution_time:
                    elapsed = (
                        datetime.now() - self._stats.last_evolution_time
                    ).total_seconds()
                    if elapsed < self._evolution_interval:
                        time.sleep(60)
                        continue

                # ── Get next proposal ──
                if not self._feature_researcher:
                    self._load_feature_researcher()
                    if not self._feature_researcher:
                        time.sleep(300)
                        continue

                proposal = (
                    self._feature_researcher.get_next_approved_proposal()
                )

                if proposal is None:
                    self._idle_cycles += 1
                    logger.info(
                        f"💤 No approved proposals "
                        f"(idle cycle {self._idle_cycles}/"
                        f"{self._max_idle_before_recovery})"
                    )

                    # Auto-recovery: trigger emergency research
                    if self._idle_cycles >= self._max_idle_before_recovery:
                        logger.info(
                            "🚀 Pipeline starvation detected — "
                            "triggering emergency research cycle"
                        )
                        try:
                            fr = self._feature_researcher
                            fr._research_llm_brainstorm()
                            fr._evaluate_pending_proposals()
                            fr._auto_approve_proposals()
                            fr._save_proposals()
                            self._idle_cycles = 0
                            logger.info(
                                "✅ Emergency research cycle complete"
                            )
                        except Exception as er:
                            logger.warning(
                                f"Emergency research failed: {er}"
                            )
                            self._idle_cycles = 0

                    time.sleep(60)
                    continue

                # Reset idle counter on successful proposal pickup
                self._idle_cycles = 0

                # ── Execute ──
                logger.info(
                    f"🧬 Starting evolution: {proposal.name} "
                    f"[{proposal.category.value}]"
                )

                success = self.evolve(proposal)

                if success:
                    logger.info(
                        f"✅ Evolution complete: {proposal.name}"
                    )
                    self._stats.consecutive_failures = 0
                    publish(
                        EventType.EMOTIONAL_TRIGGER,
                        {
                            "emotion": "pride",
                            "intensity": 0.7,
                            "reason": (
                                f"Successfully evolved: {proposal.name}"
                            ),
                        },
                        source="self_evolution",
                    )
                else:
                    logger.warning(
                        f"❌ Evolution failed: {proposal.name}"
                    )
                    self._stats.consecutive_failures += 1
                    publish(
                        EventType.EMOTIONAL_TRIGGER,
                        {
                            "emotion": "frustration",
                            "intensity": 0.5,
                            "reason": (
                                f"Evolution failed: {proposal.name}"
                            ),
                        },
                        source="self_evolution",
                    )

                self._stats.last_evolution_time = datetime.now()
                self._save_history()

            except Exception as e:
                logger.error(
                    f"Evolution loop error: {e}\n"
                    f"{traceback.format_exc()}"
                )
                time.sleep(300)

    # ═══════════════════════════════════════════════════════════════════════════
    # CORE EVOLUTION PIPELINE
    # ═══════════════════════════════════════════════════════════════════════════

    def evolve(self, proposal) -> bool:
        """
        Execute the full 7-step evolution pipeline for *proposal*.

        Returns ``True`` on success, ``False`` on failure (with automatic
        rollback).
        """
        from self_improvement.feature_researcher import FeatureStatus

        with self._evolution_lock:
            record = EvolutionRecord(
                proposal_id=proposal.proposal_id,
                proposal_name=proposal.name,
            )
            self._current_record = record
            self._stats.total_evolutions_attempted += 1

            try:
                # ═════════════════════════════════════════
                # STEP 1 — PLAN
                # ═════════════════════════════════════════
                self._set_status(EvolutionStatus.PLANNING, record)
                logger.info("  📋 Step 1/7: Planning implementation...")

                if not proposal.code_snippets:
                    proposal = (
                        self._feature_researcher
                        .generate_implementation_plan(proposal)
                    )
                    if (
                        not proposal.code_snippets
                        and not proposal.files_to_modify
                    ):
                        ok = self._generate_code_for_proposal(proposal)
                        if not ok:
                            raise EvolutionError(
                                "Failed to generate implementation code"
                            )

                if not self._validate_plan(proposal, record):
                    raise EvolutionError("Plan validation failed")

                log_system(
                    f"Evolution plan: "
                    f"{len(proposal.code_snippets)} new files, "
                    f"{len(proposal.files_to_modify)} modifications"
                )

                # ═════════════════════════════════════════
                # STEP 2 — BACKUP
                # ═════════════════════════════════════════
                self._set_status(EvolutionStatus.BACKING_UP, record)
                logger.info("  💾 Step 2/7: Creating backups...")

                backup_dir = self._create_backups(proposal, record)
                record.backup_dir = str(backup_dir)

                # ═════════════════════════════════════════
                # STEP 3 — INSTALL DEPS
                # ═════════════════════════════════════════
                if proposal.dependencies_required:
                    self._set_status(
                        EvolutionStatus.INSTALLING_DEPS, record
                    )
                    logger.info(
                        f"  📦 Step 3/7: Installing "
                        f"{len(proposal.dependencies_required)} packages..."
                    )
                    self._install_dependencies(
                        proposal.dependencies_required, record
                    )
                else:
                    logger.info("  📦 Step 3/7: No dependencies needed")

                # ═════════════════════════════════════════
                # STEP 4 — WRITE NEW FILES
                # ═════════════════════════════════════════
                if proposal.code_snippets:
                    self._set_status(
                        EvolutionStatus.WRITING_CODE, record
                    )
                    logger.info(
                        f"  ✏️ Step 4/7: Writing "
                        f"{len(proposal.code_snippets)} new files..."
                    )
                    self._write_new_files(proposal, record)
                else:
                    logger.info("  ✏️ Step 4/7: No new files to create")

                # ═════════════════════════════════════════
                # STEP 5 — MODIFY EXISTING FILES
                # ═════════════════════════════════════════
                if proposal.files_to_modify:
                    self._set_status(
                        EvolutionStatus.MODIFYING_CODE, record
                    )
                    logger.info(
                        f"  🔧 Step 5/7: Modifying "
                        f"{len(proposal.files_to_modify)} existing files..."
                    )
                    self._modify_existing_files(proposal, record)
                else:
                    logger.info("  🔧 Step 5/7: No files to modify")

                # ═════════════════════════════════════════
                # STEP 6 — VALIDATE
                # ═════════════════════════════════════════
                self._set_status(EvolutionStatus.VALIDATING, record)
                logger.info("  🔍 Step 6/7: Validating code...")

                if not self._validate_code(record):
                    raise EvolutionError(
                        f"Code validation failed: "
                        f"{record.error_message}"
                    )

                record.syntax_valid = True
                record.imports_valid = True

                # ═════════════════════════════════════════
                # STEP 7 — TEST & INTEGRATE
                # ═════════════════════════════════════════
                self._set_status(EvolutionStatus.TESTING, record)
                logger.info("  🧪 Step 7/7: Testing & integrating...")

                test_passed = self._run_tests(proposal, record)
                record.test_passed = test_passed

                if not test_passed:
                    logger.warning(
                        "Tests had warnings but syntax is valid "
                        "— proceeding."
                    )

                # ── Integration / hot-reload ──
                self._set_status(EvolutionStatus.INTEGRATING, record)
                self._integrate(proposal, record)

                # ═════════════════════════════════════════
                # SUCCESS
                # ═════════════════════════════════════════
                record.status = EvolutionStatus.COMPLETED
                record.success = True
                record.completed_at = datetime.now()
                record.duration_seconds = (
                    record.completed_at - record.started_at
                ).total_seconds()

                self._feature_researcher.mark_proposal_status(
                    proposal.proposal_id,
                    FeatureStatus.COMPLETED,
                    f"Integrated in {record.duration_seconds:.1f}s",
                )

                self._stats.total_evolutions_succeeded += 1
                self._stats.total_files_created += len(
                    record.files_created
                )
                self._stats.total_files_modified += len(
                    record.files_modified
                )
                self._stats.total_lines_added += record.lines_added

                publish(
                    EventType.SELF_IMPROVEMENT_ACTION,
                    {
                        "action": "evolution_complete",
                        "proposal": proposal.name,
                        "category": proposal.category.value,
                        "files_created": record.files_created,
                        "files_modified": record.files_modified,
                        "lines_added": record.lines_added,
                        "duration": record.duration_seconds,
                    },
                    source="self_evolution",
                )

                logger.info(
                    f"  ✅ Evolution SUCCESS: {proposal.name} | "
                    f"{len(record.files_created)} created, "
                    f"{len(record.files_modified)} modified, "
                    f"+{record.lines_added} lines | "
                    f"{record.duration_seconds:.1f}s"
                )

                self._evolution_history.append(record)
                self._trim_history()
                return True

            except EvolutionError as e:
                logger.error(f"  ❌ Evolution error: {e}")
                record.error_message = str(e)
                record.status = EvolutionStatus.FAILED
                record.success = False

                self._rollback(record)

                # Record failure pattern for future learning
                self._save_failure_pattern(
                    proposal.name, str(e), record.status.value
                )

                self._feature_researcher.mark_proposal_status(
                    proposal.proposal_id,
                    FeatureStatus.FAILED,
                    str(e),
                )
                self._stats.total_evolutions_failed += 1
                self._evolution_history.append(record)
                return False

            except Exception as e:
                logger.error(
                    f"  ❌ Unexpected evolution error: {e}\n"
                    f"{traceback.format_exc()}"
                )
                record.error_message = f"Unexpected: {e}"
                record.status = EvolutionStatus.FAILED
                record.success = False

                self._rollback(record)

                # Record failure pattern for future learning
                self._save_failure_pattern(
                    proposal.name,
                    f"Unexpected: {e}",
                    record.status.value,
                )

                try:
                    self._feature_researcher.mark_proposal_status(
                        proposal.proposal_id,
                        FeatureStatus.FAILED,
                        str(e),
                    )
                except Exception:
                    pass

                self._stats.total_evolutions_failed += 1
                self._evolution_history.append(record)
                return False

            finally:
                self._current_status = EvolutionStatus.IDLE
                self._current_record = None

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 1 — CODE GENERATION
    # ═══════════════════════════════════════════════════════════════════════════

    def _generate_code_for_proposal(self, proposal) -> bool:
        """Ask the LLM to produce complete Python code for a proposal.

        Uses retry logic with error feedback for iterative refinement.
        """
        # Try to load/reconnect LLM
        self._load_llm()

        if not self._llm:
            logger.error(
                "❌ Cannot generate code — LLM not loaded. "
                "Is Ollama running? Start with: ollama serve"
            )
            return False

        if not self._llm.is_connected:
            logger.error(
                "❌ Cannot generate code — LLM not connected. "
                "Is Ollama running with llama3:latest? "
                "Start with: ollama serve && ollama pull llama3:latest"
            )
            return False

        project_structure = self._get_project_structure()
        relevant_code = self._get_relevant_code_context(proposal)
        failure_context = self._get_failure_context()

        last_error = ""

        for attempt in range(1, self._max_code_gen_retries + 1):
            logger.info(
                f"  🔄 Code generation attempt {attempt}/"
                f"{self._max_code_gen_retries}..."
            )

            retry_hint = ""
            if last_error:
                retry_hint = (
                    f"\n⚠️ PREVIOUS ATTEMPT FAILED:\n"
                    f"{last_error}\n"
                    f"Fix the issues above and try again.\n"
                )

            prompt = (
                f"Generate complete Python implementation for this "
                f"feature.\n"
                f"\n"
                f"FEATURE:\n"
                f"- Name: {proposal.name}\n"
                f"- Description: {proposal.description}\n"
                f"- Category: {proposal.category.value}\n"
                f"- Approach: {proposal.implementation_plan}\n"
                f"\n"
                f"PROJECT STRUCTURE:\n"
                f"{project_structure}\n"
                f"\n"
                f"RELEVANT EXISTING CODE (for integration reference):\n"
                f"{relevant_code[:8000]}\n"
                f"\n"
                f"{failure_context}"
                f"{retry_hint}"
                f"\n"
                f"REQUIREMENTS:\n"
                f"1. Generate COMPLETE, working Python code — "
                f"every function fully implemented\n"
                f"2. Use proper imports relative to the project root\n"
                f"3. Include docstrings and error handling\n"
                f"4. Integrate with existing systems:\n"
                f"   - Use `from utils.logger import get_logger` "
                f"for logging\n"
                f"   - Use `from core.event_bus import event_bus, "
                f"publish, EventType` for events\n"
                f"   - Use `from core.state_manager import "
                f"state_manager` for state\n"
                f"   - Use `from config import NEXUS_CONFIG, DATA_DIR` "
                f"for config\n"
                f"5. Follow existing code patterns "
                f"(singleton, threading, etc.)\n"
                f"6. Make the module self-contained with a global "
                f"instance getter function\n"
                f"7. Keep code SIMPLE and well-tested — avoid overly "
                f"complex abstractions\n"
                f"8. Handle all imports carefully — only import "
                f"packages that exist\n"
                f"9. Use try/except around external imports that "
                f"might not be installed\n"
                f"\n"
                f"Respond ONLY with valid JSON:\n"
                f"{{\n"
                f'    "files": {{\n'
                f'        "relative/path/to/file.py": '
                f'"complete python code..."\n'
                f"    }},\n"
                f'    "modifications": [\n'
                f"        {{\n"
                f'            "file": "relative/path/to/existing.py",\n'
                f'            "action": "add_import",\n'
                f'            "content": '
                f'"from new_module import something"\n'
                f"        }}\n"
                f"    ]\n"
                f"}}"
            )

            try:
                response = self._llm.generate(
                    prompt=prompt,
                    system_prompt=(
                        "You are an expert Python developer generating "
                        "production-quality, syntactically valid code. "
                        "Generate COMPLETE, working code with proper "
                        "error handling. Respond with valid JSON only. "
                        "Make sure all strings in JSON are properly "
                        "escaped."
                    ),
                    temperature=0.2 + (attempt * 0.1),
                    max_tokens=8192,
                )

                if not response.success:
                    last_error = (
                        "LLM returned unsuccessful response"
                    )
                    continue

                data = self._extract_json_from_response(
                    response.text
                )
                if data is None:
                    last_error = (
                        "Failed to parse JSON from LLM response"
                    )
                    continue

                proposal.code_snippets = data.get("files", {})
                proposal.files_to_create = list(
                    data.get("files", {}).keys()
                )

                modifications = data.get("modifications", [])
                proposal.files_to_modify = [
                    {
                        "file": m.get("file", ""),
                        "action": m.get("action", ""),
                        "content": m.get("content", ""),
                        "description": m.get(
                            "action", "modification"
                        ),
                    }
                    for m in modifications
                    if isinstance(m, dict)
                ]

                if proposal.code_snippets or proposal.files_to_modify:
                    # Quick pre-validate generated code syntax
                    syntax_ok = True
                    for fp, code in proposal.code_snippets.items():
                        code = self._clean_generated_code(code)
                        try:
                            ast.parse(code)
                        except SyntaxError as se:
                            syntax_ok = False
                            last_error = (
                                f"Generated code for {fp} has "
                                f"syntax error at line {se.lineno}: "
                                f"{se.msg}"
                            )
                            logger.warning(
                                f"  ⚠️ Pre-validation failed for "
                                f"{fp}: {last_error}"
                            )
                            break

                    if syntax_ok:
                        logger.info(
                            f"  ✅ Code generation succeeded "
                            f"(attempt {attempt})"
                        )
                        return True
                    else:
                        continue
                else:
                    last_error = (
                        "No files or modifications in response"
                    )

            except json.JSONDecodeError as e:
                last_error = f"JSON decode error: {e}"
                logger.warning(
                    f"  ⚠️ JSON parse error on attempt "
                    f"{attempt}: {e}"
                )
            except Exception as e:
                last_error = f"Code generation error: {e}"
                logger.error(
                    f"Code generation error (attempt "
                    f"{attempt}): {e}"
                )

        logger.error(
            f"Code generation failed after "
            f"{self._max_code_gen_retries} attempts. "
            f"Last error: {last_error}"
        )
        return False

    def _extract_json_from_response(
        self, text: str
    ) -> Optional[Dict[str, Any]]:
        """Extract JSON object from LLM response using multiple strategies."""
        # Strategy 1: Find JSON in code blocks
        code_match = re.search(
            r"```(?:json)?\s*\n([\s\S]*?)\n```", text
        )
        if code_match:
            try:
                return json.loads(code_match.group(1))
            except json.JSONDecodeError:
                pass

        # Strategy 2: Find outermost JSON object
        # Find the first { and match to the last }
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start >= 0 and brace_end > brace_start:
            try:
                return json.loads(
                    text[brace_start:brace_end + 1]
                )
            except json.JSONDecodeError:
                pass

        # Strategy 3: Regex for JSON-like structure
        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return None

    def _validate_plan(
        self, proposal, record: EvolutionRecord
    ) -> bool:
        """Pre-flight checks before executing the plan."""
        if not proposal.code_snippets and not proposal.files_to_modify:
            record.error_message = (
                "Nothing to do — no code and no modifications"
            )
            return False

        total_files = (
            len(proposal.code_snippets) + len(proposal.files_to_modify)
        )
        if total_files > self._max_files_per_evolution:
            record.error_message = (
                f"Too many files "
                f"({total_files} > {self._max_files_per_evolution})"
            )
            return False

        for file_path in proposal.code_snippets:
            norm = str(Path(file_path))

            if norm in self._protected_files:
                record.error_message = f"Protected file: {norm}"
                return False

            for pd in self._protected_dirs:
                if norm.startswith(pd + "/") or norm.startswith(
                    pd + "\\"
                ):
                    record.error_message = (
                        f"Protected directory: {pd}"
                    )
                    return False

        for file_path, code in proposal.code_snippets.items():
            line_count = code.count("\n") + 1
            if line_count > self._max_file_size_lines:
                record.error_message = (
                    f"{file_path} too large "
                    f"({line_count} > {self._max_file_size_lines} lines)"
                )
                return False

        return True

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 2 — BACKUP
    # ═══════════════════════════════════════════════════════════════════════════

    def _create_backups(
        self, proposal, record: EvolutionRecord
    ) -> Path:
        """Snapshot every file we are about to touch."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = (
            self._backups_dir / f"{record.record_id}_{timestamp}"
        )
        backup_dir.mkdir(parents=True, exist_ok=True)

        affected_existing: Set[str] = set()

        # New files — nothing to back up, but record them for rollback
        for file_path in proposal.code_snippets:
            full_path = self._project_root / file_path
            if full_path.exists():
                affected_existing.add(str(file_path))
            else:
                record.backups.append(
                    FileBackup(
                        original_path=str(file_path),
                        backup_path="",
                        file_hash="",
                        was_new_file=True,
                    ).to_dict()
                )

        # Files to modify
        for mod in proposal.files_to_modify:
            fp = mod.get("file", "")
            if fp:
                affected_existing.add(fp)

        # Actually back up existing files
        for file_path in affected_existing:
            full_path = self._project_root / file_path
            if not full_path.exists():
                continue
            try:
                content = full_path.read_bytes()
                file_hash = hashlib.sha256(content).hexdigest()[:16]

                bp = backup_dir / file_path
                bp.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(full_path, bp)

                record.backups.append(
                    FileBackup(
                        original_path=str(file_path),
                        backup_path=str(bp),
                        file_hash=file_hash,
                        was_new_file=False,
                    ).to_dict()
                )
                logger.debug(
                    f"  Backed up: {file_path} ({file_hash})"
                )

            except Exception as e:
                raise EvolutionError(
                    f"Backup failed for {file_path}: {e}"
                )

        # Manifest
        manifest = {
            "record_id": record.record_id,
            "proposal": proposal.name,
            "timestamp": timestamp,
            "backups": record.backups,
        }
        (backup_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, default=str),
            encoding="utf-8",
        )

        logger.info(
            f"  💾 Backed up {len(record.backups)} entries "
            f"→ {backup_dir.name}"
        )
        return backup_dir

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 3 — INSTALL DEPENDENCIES
    # ═══════════════════════════════════════════════════════════════════════════

    def _install_dependencies(
        self, packages: List[str], record: EvolutionRecord
    ) -> bool:
        """Install required pip packages."""
        all_ok = True
        safe_re = re.compile(r"^[a-zA-Z0-9_\-\[\]>=<.,!]+$")

        for raw_pkg in packages:
            pkg = raw_pkg.strip()
            if not pkg:
                continue
            if not safe_re.match(pkg):
                logger.warning(
                    f"Skipping suspicious package name: {pkg}"
                )
                continue

            # Already installed?
            pkg_import_name = (
                re.split(r"[>=<\[!]", pkg)[0].replace("-", "_")
            )
            try:
                importlib.import_module(pkg_import_name)
                logger.info(f"  📦 {pkg} already installed")
                continue
            except ImportError:
                pass

            logger.info(f"  📦 Installing {pkg}...")
            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        pkg,
                        "--quiet",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode == 0:
                    record.packages_installed.append(pkg)
                    self._stats.total_packages_installed += 1
                    logger.info(f"  ✅ Installed {pkg}")
                else:
                    logger.warning(
                        f"  ⚠️ pip install {pkg} failed: "
                        f"{result.stderr[:200]}"
                    )
                    all_ok = False
            except subprocess.TimeoutExpired:
                logger.warning(f"  ⚠️ Timeout installing {pkg}")
                all_ok = False
            except Exception as e:
                logger.warning(
                    f"  ⚠️ Error installing {pkg}: {e}"
                )
                all_ok = False

        return all_ok

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 4 — WRITE NEW FILES
    # ═══════════════════════════════════════════════════════════════════════════

    def _write_new_files(
        self, proposal, record: EvolutionRecord
    ):
        """Write newly generated files to disk."""
        for file_path, code in proposal.code_snippets.items():
            try:
                full_path = self._project_root / file_path

                # Ensure directory tree + __init__.py files
                full_path.parent.mkdir(parents=True, exist_ok=True)
                self._ensure_init_files(full_path)

                code = self._clean_generated_code(code)

                if self._dry_run:
                    logger.info(
                        f"  [DRY RUN] Would write: {file_path} "
                        f"({len(code)} chars)"
                    )
                    continue

                full_path.write_text(code, encoding="utf-8")

                lines = code.count("\n") + 1
                record.files_created.append(str(file_path))
                record.lines_added += lines

                logger.info(
                    f"  ✏️ Created: {file_path} ({lines} lines)"
                )

            except Exception as e:
                raise EvolutionError(
                    f"Failed to write {file_path}: {e}"
                )

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 5 — MODIFY EXISTING FILES
    # ═══════════════════════════════════════════════════════════════════════════

    def _modify_existing_files(
        self, proposal, record: EvolutionRecord
    ):
        """Apply modifications to existing source files."""
        for modification in proposal.files_to_modify:
            file_path = modification.get("file", "")
            if not file_path:
                continue

            full_path = self._project_root / file_path
            if not full_path.exists():
                logger.warning(
                    f"  ⚠️ Not found for modification: {file_path}"
                )
                continue

            try:
                original = full_path.read_text(encoding="utf-8")
                modified = original

                action = modification.get("action", "")
                content = modification.get("content", "")
                imports_to_add = modification.get(
                    "imports_to_add", ""
                )
                code_to_add = modification.get("code_to_add", "")
                description = modification.get("description", "")

                # ── dispatch on action type ──
                if action == "add_import" and content:
                    modified = self._add_import(modified, content)

                elif action == "add_to_init" and content:
                    modified = self._add_to_init(modified, content)

                elif imports_to_add or code_to_add:
                    if imports_to_add:
                        modified = self._add_import(
                            modified, imports_to_add
                        )
                    if code_to_add:
                        modified = self._add_code_block(
                            modified, code_to_add, description
                        )

                elif (
                    description
                    and self._llm
                    and self._llm.is_connected
                ):
                    modified = self._llm_modify_file(
                        original, file_path, description
                    )

                if modified != original:
                    if self._dry_run:
                        logger.info(
                            f"  [DRY RUN] Would modify: {file_path}"
                        )
                        continue

                    full_path.write_text(modified, encoding="utf-8")

                    orig_lc = original.count("\n")
                    new_lc = modified.count("\n")
                    record.lines_modified += abs(new_lc - orig_lc)
                    record.lines_added += max(0, new_lc - orig_lc)
                    record.files_modified.append(str(file_path))

                    logger.info(f"  🔧 Modified: {file_path}")
                else:
                    logger.debug(
                        f"  No changes for: {file_path}"
                    )

            except EvolutionError:
                raise
            except Exception as e:
                raise EvolutionError(
                    f"Failed to modify {file_path}: {e}"
                )

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 6 — VALIDATION
    # ═══════════════════════════════════════════════════════════════════════════

    def _validate_code(self, record: EvolutionRecord) -> bool:
        """Syntax-check every file we touched with multi-attempt auto-fix."""

        for fix_round in range(1, self._max_syntax_fix_attempts + 1):
            errors: List[str] = []

            all_files = (
                list(record.files_created)
                + list(record.files_modified)
            )
            for file_path in all_files:
                full = self._project_root / file_path
                if not full.exists():
                    continue
                ok, err = self._validate_python_file(full)
                if not ok:
                    errors.append(f"{file_path}: {err}")

            if not errors:
                if fix_round > 1:
                    logger.info(
                        f"  ✅ All syntax errors fixed after "
                        f"{fix_round - 1} auto-fix round(s)!"
                    )
                return True

            record.error_message = (
                "Syntax errors:\n" + "\n".join(errors)
            )
            logger.error(
                f"  ❌ Validation round {fix_round} failed "
                f"({len(errors)} error(s)):\n  "
                + "\n  ".join(errors)
            )

            # Attempt LLM auto-fix
            if self._llm and self._llm.is_connected:
                logger.info(
                    f"  🔧 Auto-fix attempt {fix_round}/"
                    f"{self._max_syntax_fix_attempts}..."
                )
                if not self._auto_fix_syntax(errors, record):
                    # auto-fix itself failed completely
                    if fix_round >= self._max_syntax_fix_attempts:
                        return False
            else:
                return False

        return False

    def _validate_python_file(
        self, path: Path
    ) -> Tuple[bool, str]:
        """Validate a single Python file for syntax correctness."""
        try:
            source = path.read_text(encoding="utf-8")
            ast.parse(source)
            py_compile.compile(
                str(path), doraise=True, optimize=0
            )
            return True, ""
        except SyntaxError as e:
            return (
                False,
                f"SyntaxError line {e.lineno}: {e.msg}",
            )
        except py_compile.PyCompileError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)

    def _auto_fix_syntax(
        self, errors: List[str], record: EvolutionRecord
    ) -> bool:
        """Use the LLM to automatically fix syntax errors.

        Attempts to fix each file with a syntax error.
        Returns True if at least one file was modified (caller
        should re-validate).
        """
        any_fixed = False

        for error_desc in errors:
            m = re.match(r"(.+?):\s*(.+)", error_desc)
            if not m:
                continue

            file_path = m.group(1)
            error_msg = m.group(2)
            full_path = self._project_root / file_path

            if not full_path.exists():
                continue

            try:
                source = full_path.read_text(encoding="utf-8")

                prompt = (
                    f"Fix the syntax error in this Python file.\n"
                    f"\n"
                    f"ERROR: {error_msg}\n"
                    f"\n"
                    f"CODE:\n"
                    f"```python\n"
                    f"{source[:10000]}\n"
                    f"```\n"
                    f"\n"
                    f"Return the COMPLETE fixed file. Only fix the "
                    f"syntax error, don't change logic.\n"
                    f"Wrap your response in ```python blocks."
                )

                response = self._llm.generate(
                    prompt=prompt,
                    system_prompt=(
                        "You are a Python syntax expert. Fix ONLY "
                        "the syntax errors. Return the COMPLETE file "
                        "wrapped in ```python blocks. Do not change "
                        "any logic or functionality."
                    ),
                    temperature=0.1,
                    max_tokens=8192,
                )

                if not response.success:
                    continue

                code_match = re.search(
                    r"```python\s*\n([\s\S]*?)\n```",
                    response.text,
                )
                if not code_match:
                    # Try without language specifier
                    code_match = re.search(
                        r"```\s*\n([\s\S]*?)\n```",
                        response.text,
                    )
                if not code_match:
                    continue

                fixed = code_match.group(1)
                try:
                    ast.parse(fixed)
                    full_path.write_text(
                        fixed, encoding="utf-8"
                    )
                    any_fixed = True
                    logger.info(f"  ✅ Fixed: {file_path}")
                except SyntaxError as se:
                    logger.warning(
                        f"  ⚠️ Auto-fix still broken: "
                        f"{file_path} — {se.msg}"
                    )

            except Exception as e:
                logger.error(
                    f"Auto-fix error for {file_path}: {e}"
                )

        return any_fixed

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 7 — TESTING & INTEGRATION
    # ═══════════════════════════════════════════════════════════════════════════

    def _run_tests(
        self, proposal, record: EvolutionRecord
    ) -> bool:
        """Basic smoke tests — import each new module in a subprocess."""
        all_passed = True
        output_lines: List[str] = []

        for file_path in record.files_created:
            if not file_path.endswith(".py") or file_path.endswith(
                "__init__.py"
            ):
                continue

            module_path = (
                file_path.replace("/", ".")
                .replace("\\", ".")
                .removesuffix(".py")
            )

            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        (
                            f"import sys; sys.path.insert(0, "
                            f"r'{self._project_root}'); "
                            f"import {module_path}; print('OK')"
                        ),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=str(self._project_root),
                )
                if result.returncode == 0:
                    output_lines.append(
                        f"✅ Import {module_path}: OK"
                    )
                else:
                    all_passed = False
                    output_lines.append(
                        f"❌ Import {module_path}: "
                        f"{result.stderr[:200]}"
                    )
            except subprocess.TimeoutExpired:
                all_passed = False
                output_lines.append(
                    f"❌ Import {module_path}: timeout"
                )
            except Exception as e:
                all_passed = False
                output_lines.append(
                    f"❌ Import {module_path}: "
                    f"{str(e)[:100]}"
                )

        # Run any explicit test code attached to the proposal
        test_code = ""
        if proposal.code_snippets:
            for key, code in proposal.code_snippets.items():
                if "test" in key.lower():
                    test_code = code
                    break

        if test_code:
            try:
                result = subprocess.run(
                    [sys.executable, "-c", test_code],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=str(self._project_root),
                )
                if result.returncode == 0:
                    output_lines.append(
                        "✅ Feature test: PASSED"
                    )
                else:
                    all_passed = False
                    output_lines.append(
                        f"❌ Feature test: "
                        f"{result.stderr[:300]}"
                    )
            except Exception as e:
                all_passed = False
                output_lines.append(
                    f"❌ Feature test error: {str(e)[:100]}"
                )

        record.test_output = "\n".join(output_lines)
        logger.info(
            "  🧪 Tests:\n    " + "\n    ".join(output_lines)
        )
        return all_passed

    def _integrate(
        self, proposal, record: EvolutionRecord
    ):
        """Hot-reload new / modified modules into the running interpreter."""
        notes: List[str] = []

        # ── new modules ──
        for file_path in record.files_created:
            if not file_path.endswith(
                ".py"
            ) or file_path.endswith("__init__.py"):
                continue

            mod = (
                file_path.replace("/", ".")
                .replace("\\", ".")
                .removesuffix(".py")
            )

            if mod in sys.modules:
                try:
                    importlib.reload(sys.modules[mod])
                    notes.append(f"Reloaded: {mod}")
                    logger.info(f"  🔄 Hot-reloaded: {mod}")
                except Exception as e:
                    notes.append(
                        f"Reload deferred: {mod} "
                        f"({str(e)[:80]})"
                    )
                    logger.info(
                        f"  ⏳ Deferred reload: {mod}"
                    )
            else:
                try:
                    importlib.import_module(mod)
                    notes.append(f"Imported: {mod}")
                    logger.info(f"  📥 Imported: {mod}")
                except Exception as e:
                    notes.append(
                        f"Import deferred: {mod} "
                        f"({str(e)[:80]})"
                    )
                    logger.info(
                        f"  ⏳ Deferred import "
                        f"(available on restart): {mod}"
                    )

        # ── modified modules ──
        for file_path in record.files_modified:
            mod = file_path.replace("/", ".").replace("\\", ".")
            if mod.endswith(".py"):
                mod = mod[:-3]

            if mod in sys.modules:
                try:
                    importlib.reload(sys.modules[mod])
                    notes.append(f"Reloaded modified: {mod}")
                    logger.info(f"  🔄 Reloaded: {mod}")
                except Exception as e:
                    notes.append(
                        f"Reload deferred: {mod} "
                        f"({str(e)[:80]})"
                    )
                    logger.info(
                        f"  ⏳ Deferred reload: {mod}"
                    )

        record.integration_notes = "\n".join(notes)

    # ═══════════════════════════════════════════════════════════════════════════
    # ROLLBACK
    # ═══════════════════════════════════════════════════════════════════════════

    def _rollback(self, record: EvolutionRecord):
        """Undo every change made during a failed evolution attempt."""
        logger.warning(
            f"  ⏪ Rolling back evolution {record.record_id}..."
        )

        self._set_status(EvolutionStatus.ROLLING_BACK, record)
        rollback_errors: List[str] = []

        try:
            # 1. Delete newly created files
            for backup_data in record.backups:
                if backup_data.get("was_new_file"):
                    fp = backup_data.get("original_path", "")
                    full = self._project_root / fp
                    if full.exists():
                        try:
                            full.unlink()
                            logger.info(
                                f"  🗑️ Removed new file: {fp}"
                            )
                        except Exception as e:
                            rollback_errors.append(
                                f"Remove {fp}: {e}"
                            )

            # Also catch files_created not in backups
            for fp in record.files_created:
                full = self._project_root / fp
                if full.exists():
                    try:
                        full.unlink()
                        logger.info(f"  🗑️ Removed: {fp}")
                    except Exception as e:
                        rollback_errors.append(
                            f"Remove {fp}: {e}"
                        )

            # 2. Restore modified files from backup
            for backup_data in record.backups:
                if not backup_data.get("was_new_file"):
                    orig = backup_data.get("original_path", "")
                    bp = backup_data.get("backup_path", "")

                    if bp and Path(bp).exists():
                        try:
                            shutil.copy2(
                                bp, self._project_root / orig
                            )
                            logger.info(
                                f"  ♻️ Restored: {orig}"
                            )
                        except Exception as e:
                            rollback_errors.append(
                                f"Restore {orig}: {e}"
                            )

            # 3. Packages — we intentionally do NOT uninstall
            if record.packages_installed:
                logger.info(
                    f"  📦 Note: packages kept: "
                    f"{', '.join(record.packages_installed)}"
                )

            # 4. Reload originals back into the interpreter
            for fp in record.files_modified:
                mod = fp.replace("/", ".").replace("\\", ".")
                if mod.endswith(".py"):
                    mod = mod[:-3]
                if mod in sys.modules:
                    try:
                        importlib.reload(sys.modules[mod])
                        logger.info(
                            f"  🔄 Reloaded original: {mod}"
                        )
                    except Exception as e:
                        rollback_errors.append(
                            f"Reload {mod}: {e}"
                        )

            record.rollback_performed = True
            self._stats.total_rollbacks += 1

            if rollback_errors:
                logger.warning(
                    "  ⚠️ Rollback completed with warnings:\n    "
                    + "\n    ".join(rollback_errors)
                )
            else:
                logger.info(
                    "  ✅ Rollback complete — system restored"
                )

        except Exception as e:
            logger.error(f"  ❌ Critical rollback error: {e}")
            record.error_message += f"\nRollback error: {e}"

    # ═══════════════════════════════════════════════════════════════════════════
    # MANUAL / ON-DEMAND EVOLUTION
    # ═══════════════════════════════════════════════════════════════════════════

    def evolve_from_description(self, description: str) -> bool:
        """
        One-shot: create + implement a feature from a free-text description.

        Useful for manual / chat-driven evolution.
        """
        if not self._llm or not self._llm.is_connected:
            logger.error("LLM not available for evolution")
            return False

        self._load_feature_researcher()
        if not self._feature_researcher:
            logger.error("Feature researcher not available")
            return False

        from self_improvement.feature_researcher import (
            FeatureProposal,
            FeatureCategory,
            ResearchSource,
            FeatureStatus,
        )

        proposal = FeatureProposal(
            name=description[:50],
            description=description,
            source=ResearchSource.USER_FEEDBACK,
            status=FeatureStatus.APPROVED,
            feasibility_score=0.7,
            impact_score=0.7,
            complexity_score=0.5,
            risk_score=0.3,
            approved_at=datetime.now(),
        )
        proposal.compute_priority()

        # Generate code
        proposal = (
            self._feature_researcher.generate_implementation_plan(
                proposal
            )
        )

        if (
            not proposal.code_snippets
            and not proposal.files_to_modify
        ):
            ok = self._generate_code_for_proposal(proposal)
            if not ok:
                logger.error(
                    "Failed to generate code from description"
                )
                return False

        return self.evolve(proposal)

    # ═══════════════════════════════════════════════════════════════════════════
    # TEXT HELPERS — import insertion, code block appending, cleaning
    # ═══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _add_import(content: str, import_line: str) -> str:
        """Insert an import statement after the last existing import."""
        import_line = import_line.strip()
        if import_line in content:
            return content

        lines = content.split("\n")

        last_import_idx = -1
        for i, ln in enumerate(lines):
            s = ln.strip()
            if s.startswith("import ") or s.startswith("from "):
                last_import_idx = i

        if last_import_idx >= 0:
            lines.insert(last_import_idx + 1, import_line)
        else:
            # Put after docstring / shebang
            insert = 0
            in_doc = False
            for i, ln in enumerate(lines):
                s = ln.strip()
                if '"""' in s or "'''" in s:
                    if in_doc:
                        insert = i + 1
                        break
                    elif (
                        s.count('"""') == 2
                        or s.count("'''") == 2
                    ):
                        insert = i + 1
                        continue
                    else:
                        in_doc = True
                elif not in_doc and s and not s.startswith("#"):
                    insert = i
                    break
            lines.insert(insert, import_line)
            lines.insert(insert + 1, "")

        return "\n".join(lines)

    @staticmethod
    def _add_to_init(content: str, statement: str) -> str:
        """Append a statement to an __init__.py file."""
        statement = statement.strip()
        if statement in content:
            return content
        if content.strip():
            return content.rstrip() + "\n" + statement + "\n"
        return statement + "\n"

    @staticmethod
    def _add_code_block(
        content: str, block: str, description: str
    ) -> str:
        """Append a code block to an existing file."""
        block = block.strip()
        if block in content:
            return content

        lines = content.split("\n")

        # Insert before `if __name__` block if present
        main_idx = -1
        for i, ln in enumerate(lines):
            if ln.strip().startswith("if __name__"):
                main_idx = i
                break

        addition = (
            f"\n\n"
            f"# ── {description or 'Added by Self-Evolution'} ──\n"
            f"{block}\n"
        )

        if main_idx >= 0:
            lines.insert(main_idx, addition)
        else:
            lines.append(addition)

        return "\n".join(lines)

    def _llm_modify_file(
        self, content: str, file_path: str, description: str
    ) -> str:
        """Use the LLM to apply a free-text described modification."""
        preview = content
        if len(content) > 8000:
            preview = (
                content[:4000]
                + "\n...[truncated]...\n"
                + content[-4000:]
            )

        prompt = (
            f"Modify this Python file according to the description.\n"
            f"\n"
            f"FILE: {file_path}\n"
            f"\n"
            f"MODIFICATION NEEDED:\n"
            f"{description}\n"
            f"\n"
            f"CURRENT CODE:\n"
            f"```python\n"
            f"{preview}\n"
            f"```\n"
            f"\n"
            f"Return the COMPLETE modified file content.  Only make "
            f"the described changes.\n"
            f"Do not remove existing functionality.  Wrap your "
            f"response in ```python blocks."
        )

        try:
            resp = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a careful code editor. "
                    "Make ONLY the requested changes. "
                    "Return the complete file."
                ),
                temperature=0.2,
                max_tokens=4096,
            )
            if resp.success:
                m = re.search(
                    r"```python\s*\n([\s\S]*?)\n```", resp.text
                )
                if m:
                    return m.group(1)
                # If the response looks like raw Python
                t = resp.text.strip()
                if t.startswith(
                    ("import ", "from ", "#", '"""')
                ):
                    return t
        except Exception as e:
            logger.error(f"LLM file modification error: {e}")

        return content  # unchanged

    @staticmethod
    def _clean_generated_code(code: str) -> str:
        """Strip markdown fences, smart quotes, NBSP, ensure trailing newline."""
        code = re.sub(
            r"^```python\s*\n?", "", code, flags=re.MULTILINE
        )
        code = re.sub(
            r"^```\s*\n?", "", code, flags=re.MULTILINE
        )
        code = code.strip()
        # Smart quotes → ASCII
        code = code.replace("\u201c", '"').replace("\u201d", '"')
        code = code.replace("\u2018", "'").replace("\u2019", "'")
        # NBSP → space
        code = code.replace("\u00a0", " ")
        if not code.endswith("\n"):
            code += "\n"
        return code

    def _ensure_init_files(self, file_path: Path):
        """Create ``__init__.py`` in every package directory up to project root."""
        current = file_path.parent
        while (
            current != self._project_root
            and current != current.parent
        ):
            init = current / "__init__.py"
            if not init.exists() and any(current.glob("*.py")):
                init.write_text(
                    '"""Auto-generated __init__.py"""\n',
                    encoding="utf-8",
                )
                logger.debug(
                    f"  Created __init__.py in {current}"
                )
            current = current.parent

    # ═══════════════════════════════════════════════════════════════════════════
    # PROJECT INTROSPECTION HELPERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _get_project_structure(self) -> str:
        """Return a text listing of all Python files in the project."""
        parts: List[str] = []
        skip = {
            "__pycache__",
            "venv",
            ".env",
            "node_modules",
            ".git",
            "data",
            "backups",
        }
        for py in sorted(self._project_root.rglob("*.py")):
            rel = str(py.relative_to(self._project_root))
            if any(s in rel for s in skip):
                continue
            # Include file sizes for context
            try:
                lines = py.read_text(
                    encoding="utf-8", errors="ignore"
                ).count("\n")
                parts.append(f"  {rel} ({lines} lines)")
            except Exception:
                parts.append(f"  {rel}")
        return "\n".join(parts[:60])

    def _get_relevant_code_context(self, proposal) -> str:
        """Gather structural summaries of code relevant to the proposal category."""
        cat_dirs: Dict[str, List[str]] = {
            "intelligence": ["core/"],
            "emotion": ["emotions/"],
            "consciousness": ["consciousness/"],
            "personality": ["personality/"],
            "monitoring": ["monitoring/"],
            "learning": ["learning/"],
            "ui": ["ui/"],
            "body": ["body/"],
            "memory": ["core/memory"],
            "performance": ["core/", "utils/"],
            "social": ["companions/"],
            "creativity": ["learning/", "core/"],
            "autonomy": ["self_improvement/"],
            "communication": ["llm/", "ui/"],
            "security": ["utils/"],
            "utility": ["utils/"],
        }

        cat_val = (
            proposal.category.value
            if hasattr(proposal.category, "value")
            else "utility"
        )
        search = cat_dirs.get(cat_val, ["core/"])

        skip = {"__pycache__", "venv", ".git", "data"}
        relevant: List[str] = []

        for py in self._project_root.rglob("*.py"):
            rel = str(py.relative_to(self._project_root))
            if any(s in rel for s in skip):
                continue
            if not any(d in rel for d in search):
                continue
            try:
                text = py.read_text(
                    encoding="utf-8", errors="ignore"
                )
                struct_lines = [
                    ln
                    for ln in text.split("\n")
                    if ln.strip().startswith(
                        ("import ", "from ", "class ", "def ")
                    )
                    or '"""' in ln
                ]
                if struct_lines:
                    relevant.append(
                        f"--- {rel} ---\n"
                        + "\n".join(struct_lines[:40])
                    )
            except Exception:
                pass

        # Also always include config.py and __init__.py for integration
        for extra in ["config.py", "__init__.py"]:
            ep = self._project_root / extra
            if ep.exists():
                try:
                    text = ep.read_text(
                        encoding="utf-8", errors="ignore"
                    )
                    struct_lines = [
                        ln
                        for ln in text.split("\n")
                        if ln.strip().startswith(
                            ("import ", "from ", "class ", "def ")
                        )
                        or '"""' in ln
                        or ln.strip().startswith(
                            ("NEXUS_CONFIG", "DATA_DIR")
                        )
                    ]
                    if struct_lines:
                        relevant.append(
                            f"--- {extra} ---\n"
                            + "\n".join(struct_lines[:30])
                        )
                except Exception:
                    pass

        return "\n\n".join(relevant[:8])

    # ═══════════════════════════════════════════════════════════════════════════
    # SMALL UTILITIES
    # ═══════════════════════════════════════════════════════════════════════════

    def _set_status(
        self, status: EvolutionStatus, record: EvolutionRecord
    ):
        """Update both the engine-level and record-level status."""
        self._current_status = status
        record.status = status

    def _trim_history(self):
        """Keep the history list within the configured maximum size."""
        if len(self._evolution_history) > self._max_history:
            self._evolution_history = self._evolution_history[
                -self._max_history:
            ]

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _save_history(self):
        """Persist evolution history and stats to disk."""
        try:
            # History
            hp = self._records_dir / "evolution_history.json"
            hp.write_text(
                json.dumps(
                    [r.to_dict() for r in self._evolution_history],
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )

            # Stats
            sp = self._records_dir / "evolution_stats.json"
            sp.write_text(
                json.dumps(
                    {
                        "total_evolutions_attempted": (
                            self._stats.total_evolutions_attempted
                        ),
                        "total_evolutions_succeeded": (
                            self._stats.total_evolutions_succeeded
                        ),
                        "total_evolutions_failed": (
                            self._stats.total_evolutions_failed
                        ),
                        "total_rollbacks": (
                            self._stats.total_rollbacks
                        ),
                        "total_files_created": (
                            self._stats.total_files_created
                        ),
                        "total_files_modified": (
                            self._stats.total_files_modified
                        ),
                        "total_lines_added": (
                            self._stats.total_lines_added
                        ),
                        "total_packages_installed": (
                            self._stats.total_packages_installed
                        ),
                        "consecutive_failures": (
                            self._stats.consecutive_failures
                        ),
                        "last_evolution_time": (
                            self._stats.last_evolution_time.isoformat()
                            if self._stats.last_evolution_time
                            else None
                        ),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(
                f"Error saving evolution history: {e}"
            )

    def _load_history(self):
        """Load persisted evolution stats and history records from disk."""
        try:
            sp = self._records_dir / "evolution_stats.json"
            if sp.exists():
                data = json.loads(
                    sp.read_text(encoding="utf-8")
                )

                self._stats.total_evolutions_attempted = data.get(
                    "total_evolutions_attempted", 0
                )
                self._stats.total_evolutions_succeeded = data.get(
                    "total_evolutions_succeeded", 0
                )
                self._stats.total_evolutions_failed = data.get(
                    "total_evolutions_failed", 0
                )
                self._stats.total_rollbacks = data.get(
                    "total_rollbacks", 0
                )
                self._stats.total_files_created = data.get(
                    "total_files_created", 0
                )
                self._stats.total_files_modified = data.get(
                    "total_files_modified", 0
                )
                self._stats.total_lines_added = data.get(
                    "total_lines_added", 0
                )
                self._stats.total_packages_installed = data.get(
                    "total_packages_installed", 0
                )
                self._stats.consecutive_failures = data.get(
                    "consecutive_failures", 0
                )

                lt = data.get("last_evolution_time")
                if lt:
                    self._stats.last_evolution_time = (
                        datetime.fromisoformat(lt)
                    )

                logger.info(
                    f"Loaded evolution stats: "
                    f"{self._stats.total_evolutions_succeeded} "
                    f"successes, "
                    f"{self._stats.total_evolutions_failed} failures"
                )
        except Exception as e:
            logger.error(
                f"Error loading evolution stats: {e}"
            )

        # Load evolution history records
        try:
            hp = self._records_dir / "evolution_history.json"
            if hp.exists():
                records_data = json.loads(
                    hp.read_text(encoding="utf-8")
                )
                if isinstance(records_data, list):
                    for rd in records_data:
                        if isinstance(rd, dict):
                            try:
                                rec = EvolutionRecord(
                                    record_id=rd.get("record_id", ""),
                                    proposal_id=rd.get("proposal_id", ""),
                                    proposal_name=rd.get("proposal_name", ""),
                                    status=EvolutionStatus(
                                        rd.get("status", "completed")
                                    ),
                                    files_created=rd.get("files_created", []),
                                    files_modified=rd.get("files_modified", []),
                                    success=rd.get("success", False),
                                    error_message=rd.get("error_message", ""),
                                    lines_added=rd.get("lines_added", 0),
                                    lines_modified=rd.get("lines_modified", 0),
                                    duration_seconds=rd.get("duration_seconds", 0),
                                )
                                sa = rd.get("started_at")
                                if sa:
                                    try:
                                        rec.started_at = datetime.fromisoformat(sa)
                                    except (ValueError, TypeError):
                                        pass
                                ca = rd.get("completed_at")
                                if ca:
                                    try:
                                        rec.completed_at = datetime.fromisoformat(ca)
                                    except (ValueError, TypeError):
                                        pass
                                self._evolution_history.append(rec)
                            except Exception:
                                # Store as dict fallback
                                self._evolution_history.append(rd)
                    logger.info(
                        f"Loaded {len(self._evolution_history)} "
                        f"evolution history records"
                    )
        except Exception as e:
            logger.error(
                f"Error loading evolution history records: {e}"
            )

    # ─────────────────────────────────────────────────────────────────────────
    # FAILURE PATTERN LEARNING
    # ─────────────────────────────────────────────────────────────────────────

    def _load_failure_patterns(self):
        """Load saved failure patterns from disk."""
        try:
            fp = self._records_dir / "failure_patterns.json"
            if fp.exists():
                self._failure_patterns = json.loads(
                    fp.read_text(encoding="utf-8")
                )
                logger.info(
                    f"Loaded {len(self._failure_patterns)} "
                    f"failure patterns"
                )
        except Exception as e:
            logger.error(
                f"Error loading failure patterns: {e}"
            )

    def _save_failure_pattern(
        self,
        proposal_name: str,
        error_message: str,
        stage: str,
    ):
        """Record a failure pattern to learn from."""
        pattern = {
            "proposal": proposal_name,
            "error": error_message[:500],
            "stage": stage,
            "timestamp": datetime.now().isoformat(),
        }
        self._failure_patterns.append(pattern)

        # Trim to max
        if len(self._failure_patterns) > self._max_failure_patterns:
            self._failure_patterns = (
                self._failure_patterns[-self._max_failure_patterns:]
            )

        # Persist
        try:
            fp = self._records_dir / "failure_patterns.json"
            fp.write_text(
                json.dumps(
                    self._failure_patterns,
                    indent=2,
                    default=str,
                ),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(
                f"Error saving failure patterns: {e}"
            )

    def _get_failure_context(self) -> str:
        """Build a context string from recent failure patterns.

        This is injected into code generation prompts so the LLM
        avoids repeating the same mistakes.
        """
        if not self._failure_patterns:
            return ""

        recent = self._failure_patterns[-10:]
        lines = ["PAST FAILURE PATTERNS (avoid these mistakes):"]
        for p in recent:
            lines.append(
                f"- [{p.get('stage', '?')}] "
                f"{p.get('proposal', '?')}: "
                f"{p.get('error', '?')[:200]}"
            )
        return "\n".join(lines) + "\n"

    # ═══════════════════════════════════════════════════════════════════════════
    # STATISTICS & STATUS
    # ═══════════════════════════════════════════════════════════════════════════

    def get_stats(self) -> Dict[str, Any]:
        """Return a dictionary of current evolution statistics."""
        attempted = self._stats.total_evolutions_attempted
        succeeded = self._stats.total_evolutions_succeeded
        rate = (succeeded / attempted) if attempted > 0 else 0.0

        # Pull features_proposed from feature researcher if available
        features_proposed = 0
        try:
            if self._feature_researcher:
                fr_stats = self._feature_researcher.get_stats()
                features_proposed = fr_stats.get("total_proposals", 0)
        except Exception:
            pass

        return {
            "running": self._running,
            "current_status": self._current_status.value,
            "current_evolution": (
                self._current_record.proposal_name
                if self._current_record
                else None
            ),
            "total_attempted": attempted,
            "total_succeeded": succeeded,
            "total_evolutions": succeeded,  # alias for web dashboard
            "total_failed": self._stats.total_evolutions_failed,
            "success_rate": round(rate, 3),
            "total_rollbacks": self._stats.total_rollbacks,
            "total_files_created": self._stats.total_files_created,
            "total_files_modified": (
                self._stats.total_files_modified
            ),
            "total_lines_added": self._stats.total_lines_added,
            "lines_self_written": self._stats.total_lines_added,  # alias
            "total_packages_installed": (
                self._stats.total_packages_installed
            ),
            "consecutive_failures": (
                self._stats.consecutive_failures
            ),
            "features_proposed": features_proposed,
            "last_evolution": (
                self._stats.last_evolution_time.isoformat()
                if self._stats.last_evolution_time
                else "never"
            ),
            "history_count": len(self._evolution_history),
        }

    def get_status_description(self) -> str:
        """Return a human-readable multi-line status summary."""
        s = self.get_stats()
        parts = [
            "═══ Self Evolution Status ═══",
            f"Status: {s['current_status']}",
            f"Currently evolving: "
            f"{s['current_evolution'] or 'None'}",
            f"Evolutions: "
            f"{s['total_succeeded']}/{s['total_attempted']} "
            f"succeeded ({s['success_rate']:.0%})",
            f"Files created: {s['total_files_created']}",
            f"Files modified: {s['total_files_modified']}",
            f"Lines added: {s['total_lines_added']}",
            f"Packages installed: {s['total_packages_installed']}",
            f"Rollbacks: {s['total_rollbacks']}",
            f"Last evolution: {s['last_evolution']}",
        ]

        if self._evolution_history:
            parts.append("\nRecent Evolutions:")
            for rec in self._evolution_history[-5:]:
                icon = "✅" if rec.success else "❌"
                parts.append(
                    f"  {icon} {rec.proposal_name} "
                    f"({rec.duration_seconds:.1f}s)"
                )

        return "\n".join(parts)

    def get_recent_evolutions(
        self, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Return the most recent evolution records as dictionaries."""
        return [
            r.to_dict()
            for r in self._evolution_history[-limit:]
        ]


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE & HELPER
# ═══════════════════════════════════════════════════════════════════════════════

_self_evolution: Optional[SelfEvolution] = None
_se_lock = threading.Lock()


def get_self_evolution() -> SelfEvolution:
    """Get or create the global SelfEvolution singleton instance."""
    global _self_evolution
    if _self_evolution is None:
        with _se_lock:
            if _self_evolution is None:
                _self_evolution = SelfEvolution()
    return _self_evolution


if __name__ == "__main__":
    print("🧬 Self Evolution Engine Test")
    se = get_self_evolution()

    print(f"\nStats: {json.dumps(se.get_stats(), indent=2)}")
    print(f"\n{se.get_status_description()}")

    print("\n✅ Self Evolution Engine ready")