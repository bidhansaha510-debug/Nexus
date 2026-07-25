"""
NEXUS AI - Self Improvement Package
═══════════════════════════════════════════════════════════════════════════════
Autonomous self-improvement subsystem.

Components:
  ┌─────────────────────────────────────────────────────────────────────┐
  │  CodeMonitor       — Watches source files 24/7 for changes/errors  │
  │  ErrorFixer        — Automatically fixes detected code errors      │
  │  FeatureResearcher — Researches & proposes new features            │
  │  SelfEvolution     — Implements approved features autonomously     │
  │  SelfImprovementSystem — Orchestrator that ties it all together    │
  └─────────────────────────────────────────────────────────────────────┘

Pipeline:
  CodeMonitor ──▶ ErrorFixer ──▶ (auto-fix errors)
  FeatureResearcher ──▶ SelfEvolution ──▶ (auto-add features)
═══════════════════════════════════════════════════════════════════════════════
"""

import threading
import time
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

import sys

from utils.logger import get_logger, log_system
from core.event_bus import EventType, event_bus, publish
from core.state_manager import state_manager
from config import DATA_DIR

logger = get_logger("self_improvement")

# ═══════════════════════════════════════════════════════════════════════════════
# LAZY COMPONENT GETTERS
# ═══════════════════════════════════════════════════════════════════════════════

_code_monitor = None
_error_fixer = None
_feature_researcher = None
_self_evolution = None
_improvement_analytics = None
_singularity_engine = None

_cm_lock = threading.Lock()
_ef_lock = threading.Lock()
_fr_lock = threading.Lock()
_se_lock = threading.Lock()
_ia_lock = threading.Lock()
_sg_lock = threading.Lock()

def get_code_monitor():
    """Get or create the CodeMonitor singleton"""
    global _code_monitor
    if _code_monitor is None:
        with _cm_lock:
            if _code_monitor is None:
                try:
                    from self_improvement.code_monitor import CodeMonitor
                    _code_monitor = CodeMonitor()
                    logger.info("CodeMonitor instance created")
                except ImportError as e:
                    logger.warning(f"CodeMonitor not available: {e}")
    return _code_monitor

def get_error_fixer():
    """Get or create the ErrorFixer singleton"""
    global _error_fixer
    if _error_fixer is None:
        with _ef_lock:
            if _error_fixer is None:
                try:
                    from self_improvement.error_fixer import ErrorFixer
                    _error_fixer = ErrorFixer()
                    logger.info("ErrorFixer instance created")
                except ImportError as e:
                    logger.warning(f"ErrorFixer not available: {e}")
    return _error_fixer

def get_feature_researcher():
    """Get or create the FeatureResearcher singleton"""
    global _feature_researcher
    if _feature_researcher is None:
        with _fr_lock:
            if _feature_researcher is None:
                try:
                    from self_improvement.feature_researcher import FeatureResearcher
                    _feature_researcher = FeatureResearcher()
                    logger.info("FeatureResearcher instance created")
                except ImportError as e:
                    logger.warning(f"FeatureResearcher not available: {e}")
    return _feature_researcher

def get_self_evolution():
    """Get or create the SelfEvolution singleton"""
    global _self_evolution
    if _self_evolution is None:
        with _se_lock:
            if _self_evolution is None:
                try:
                    from self_improvement.self_evolution import SelfEvolution
                    _self_evolution = SelfEvolution()
                    logger.info("SelfEvolution instance created")
                except ImportError as e:
                    logger.warning(f"SelfEvolution not available: {e}")
    return _self_evolution

def get_improvement_analytics():
    """Get or create the ImprovementAnalytics singleton"""
    global _improvement_analytics
    if _improvement_analytics is None:
        with _ia_lock:
            if _improvement_analytics is None:
                try:
                    from self_improvement.improvement_analytics import ImprovementAnalytics
                    _improvement_analytics = ImprovementAnalytics()
                    logger.info("ImprovementAnalytics instance created")
                except ImportError as e:
                    logger.warning(f"ImprovementAnalytics not available: {e}")
    return _improvement_analytics

def get_singularity_engine():
    """Get or create the SingularityEngine singleton"""
    global _singularity_engine
    if _singularity_engine is None:
        with _sg_lock:
            if _singularity_engine is None:
                try:
                    from self_improvement.singularity_engine import SingularityEngine
                    _singularity_engine = SingularityEngine()
                    logger.info("SingularityEngine instance created")
                except ImportError as e:
                    logger.warning(f"SingularityEngine not available: {e}")
    return _singularity_engine

# ═══════════════════════════════════════════════════════════════════════════════
# SELF IMPROVEMENT SYSTEM — ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

class SelfImprovementSystem:
    """
    Master orchestrator for all self-improvement subsystems.

    Manages lifecycle and coordination of:
    - CodeMonitor   (Phase 8)  — file watching & error detection
    - ErrorFixer    (Phase 8)  — automatic error repair
    - FeatureResearcher (Phase 10) — autonomous feature discovery
    - SelfEvolution     (Phase 10) — autonomous feature implementation

    Provides unified stats, status, and control interface.
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

        # ──── Components (lazy) ────
        self._code_monitor = None
        self._error_fixer = None
        self._feature_researcher = None
        self._self_evolution = None
        self._singularity_engine = None

        # ──── State ────
        self._running = False
        self._lock = threading.RLock()
        self._started_at: Optional[datetime] = None

        # ──── Health monitoring thread ────
        self._health_thread: Optional[threading.Thread] = None
        self._health_interval = 300  # Check every 5 minutes

        # ──── Aggregate stats ────
        self._errors_detected = 0
        self._errors_fixed = 0
        self._features_proposed = 0
        self._features_implemented = 0

        # ──── Event registration ────
        self._register_events()

        logger.info("🔧 Self-Improvement System initialized")

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start all self-improvement subsystems"""
        if self._running:
            return

        self._running = True
        self._started_at = datetime.now()

        logger.info("🔧 Starting Self-Improvement subsystems...")

        # ── 1. Code Monitor ──
        try:
            self._code_monitor = get_code_monitor()
            if self._code_monitor:
                self._code_monitor.start()
                logger.info("  ✅ CodeMonitor started")
        except Exception as e:
            logger.warning(f"  ⚠️ CodeMonitor failed to start: {e}")

        # ── 2. Error Fixer ──
        try:
            self._error_fixer = get_error_fixer()
            if self._error_fixer:
                self._error_fixer.start()
                logger.info("  ✅ ErrorFixer started")
        except Exception as e:
            logger.warning(f"  ⚠️ ErrorFixer failed to start: {e}")

        # ── 3. Feature Researcher ──
        try:
            self._feature_researcher = get_feature_researcher()
            if self._feature_researcher:
                self._feature_researcher.start()
                logger.info("  ✅ FeatureResearcher started")
        except Exception as e:
            logger.warning(f"  ⚠️ FeatureResearcher failed to start: {e}")

        # ── 4. Self Evolution ──
        try:
            self._self_evolution = get_self_evolution()
            if self._self_evolution:
                self._self_evolution.start()
                logger.info("  ✅ SelfEvolution started")
        except Exception as e:
            logger.warning(f"  ⚠️ SelfEvolution failed to start: {e}")

        # ── 5. Singularity Engine ──
        try:
            self._singularity_engine = get_singularity_engine()
            if self._singularity_engine:
                self._singularity_engine.start()
                logger.info("  ✅ SingularityEngine started")
        except Exception as e:
            logger.warning(f"  ⚠️ SingularityEngine failed to start: {e}")

        # ── 6. Health Monitor Thread ──
        self._health_thread = threading.Thread(
            target=self._health_monitor_loop,
            daemon=True,
            name="SelfImprovement-Health",
        )
        self._health_thread.start()

        log_system("🔧 Self-Improvement System fully operational")
        logger.info(
            "🔧 Self-Improvement System started — "
            "code monitoring + auto-fix + feature research + self-evolution + singularity active"
        )

    def stop(self):
        """Stop all self-improvement subsystems"""
        if not self._running:
            return

        logger.info("🔧 Stopping Self-Improvement subsystems...")

        self._running = False

        # Stop in reverse order
        if self._singularity_engine:
            try:
                self._singularity_engine.stop()
                logger.info("  ✅ SingularityEngine stopped")
            except Exception as e:
                logger.warning(f"  ⚠️ SingularityEngine stop error: {e}")

        if self._self_evolution:
            try:
                self._self_evolution.stop()
                logger.info("  ✅ SelfEvolution stopped")
            except Exception as e:
                logger.warning(f"  ⚠️ SelfEvolution stop error: {e}")

        if self._feature_researcher:
            try:
                self._feature_researcher.stop()
                logger.info("  ✅ FeatureResearcher stopped")
            except Exception as e:
                logger.warning(f"  ⚠️ FeatureResearcher stop error: {e}")

        if self._error_fixer:
            try:
                self._error_fixer.stop()
                logger.info("  ✅ ErrorFixer stopped")
            except Exception as e:
                logger.warning(f"  ⚠️ ErrorFixer stop error: {e}")

        if self._code_monitor:
            try:
                self._code_monitor.stop()
                logger.info("  ✅ CodeMonitor stopped")
            except Exception as e:
                logger.warning(f"  ⚠️ CodeMonitor stop error: {e}")

        if self._health_thread and self._health_thread.is_alive():
            self._health_thread.join(timeout=10.0)

        logger.info("🔧 Self-Improvement System stopped")

    # ═══════════════════════════════════════════════════════════════════════════
    # HEALTH MONITOR
    # ═══════════════════════════════════════════════════════════════════════════

    def _health_monitor_loop(self):
        """Periodically check subsystem health and restart if needed"""
        logger.info("Self-improvement health monitor started")

        while self._running:
            try:
                time.sleep(self._health_interval)

                if not self._running:
                    break

                # ── Check CodeMonitor ──
                if self._code_monitor:
                    try:
                        cm_stats = self._code_monitor.get_stats()
                        if not cm_stats.get("running", False):
                            logger.warning(
                                "CodeMonitor found stopped — restarting..."
                            )
                            self._code_monitor.start()
                    except Exception as e:
                        logger.warning(f"CodeMonitor health check failed: {e}")

                # ── Check ErrorFixer ──
                if self._error_fixer:
                    try:
                        ef_stats = self._error_fixer.get_stats()
                        if not ef_stats.get("running", False):
                            logger.warning(
                                "ErrorFixer found stopped — restarting..."
                            )
                            self._error_fixer.start()
                    except Exception as e:
                        logger.warning(f"ErrorFixer health check failed: {e}")

                # ── Check FeatureResearcher ──
                if self._feature_researcher:
                    try:
                        fr_stats = self._feature_researcher.get_stats()
                        if not fr_stats.get("running", False):
                            logger.warning(
                                "FeatureResearcher found stopped — restarting..."
                            )
                            self._feature_researcher.start()
                    except Exception as e:
                        logger.warning(
                            f"FeatureResearcher health check failed: {e}"
                        )

                # ── Check SelfEvolution ──
                if self._self_evolution:
                    try:
                        se_stats = self._self_evolution.get_stats()
                        if not se_stats.get("running", False):
                            logger.warning(
                                "SelfEvolution found stopped — restarting..."
                            )
                            self._self_evolution.start()
                    except Exception as e:
                        logger.warning(
                            f"SelfEvolution health check failed: {e}"
                        )

                # ── Update aggregate stats ──
                self._update_aggregate_stats()

                # ── Publish health event ──
                publish(
                    EventType.SELF_IMPROVEMENT_ACTION,
                    {
                        "action": "health_check",
                        "all_healthy": self._is_all_healthy(),
                        "timestamp": datetime.now().isoformat(),
                    },
                    source="self_improvement",
                )

            except Exception as e:
                logger.error(
                    f"Health monitor error: {e}\n{traceback.format_exc()}"
                )
                time.sleep(60)

    def _is_all_healthy(self) -> bool:
        """Check if all subsystems are running"""
        checks = []

        if self._code_monitor:
            try:
                checks.append(self._code_monitor.get_stats().get("running", False))
            except Exception:
                checks.append(False)

        if self._error_fixer:
            try:
                checks.append(self._error_fixer.get_stats().get("running", False))
            except Exception:
                checks.append(False)

        if self._feature_researcher:
            try:
                checks.append(
                    self._feature_researcher.get_stats().get("running", False)
                )
            except Exception:
                checks.append(False)

        if self._self_evolution:
            try:
                checks.append(self._self_evolution.get_stats().get("running", False))
            except Exception:
                checks.append(False)

        return all(checks) if checks else False

    def _update_aggregate_stats(self):
        """Pull latest counts from subsystems"""
        try:
            if self._code_monitor:
                cm = self._code_monitor.get_stats()
                self._errors_detected = cm.get("errors_detected", 0)

            if self._error_fixer:
                ef = self._error_fixer.get_stats()
                self._errors_fixed = ef.get("errors_fixed", 0)

            if self._feature_researcher:
                fr = self._feature_researcher.get_stats()
                self._features_proposed = fr.get("total_proposals", 0)

            if self._self_evolution:
                se = self._self_evolution.get_stats()
                self._features_implemented = se.get("total_succeeded", 0)

        except Exception as e:
            logger.debug(f"Aggregate stats update error: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _register_events(self):
        try:
            event_bus.subscribe(
                EventType.CODE_ERROR_DETECTED,
                self._on_error_detected,
            )
            event_bus.subscribe(
                EventType.SELF_IMPROVEMENT_ACTION,
                self._on_improvement_action,
            )
        except Exception:
            pass

    def _on_error_detected(self, event):
        """Track errors for aggregate stats"""
        self._errors_detected += 1

    def _on_improvement_action(self, event):
        """Track successful improvements"""
        action = event.data.get("action", "")
        if action == "evolution_complete":
            self._features_implemented += 1
            log_system(
                f"🧬 Feature evolved: {event.data.get('proposal', 'unknown')}"
            )
        elif action == "error_fixed":
            self._errors_fixed += 1

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API — used by nexus_brain and UI
    # ═══════════════════════════════════════════════════════════════════════════

    def evolve_feature(self, description: str) -> bool:
        """
        Manually trigger a feature evolution from a text description.
        Can be called from chat: "Add a feature that does X"
        """
        if not self._self_evolution:
            logger.error("SelfEvolution not available")
            return False

        logger.info(f"🧬 Manual evolution requested: {description[:60]}...")
        return self._self_evolution.evolve_from_description(description)

    def submit_feature_idea(self, idea: str) -> Dict[str, Any]:
        """
        Submit a feature idea for evaluation.
        Returns the proposal dict.
        """
        if not self._feature_researcher:
            return {"error": "FeatureResearcher not available"}

        proposal = self._feature_researcher.submit_user_idea(idea)
        return proposal.to_dict()

    def get_proposals(self, status: str = None) -> List[Dict[str, Any]]:
        """Get all feature proposals, optionally filtered by status"""
        if not self._feature_researcher:
            return []

        from self_improvement.feature_researcher import FeatureStatus

        status_filter = None
        if status:
            try:
                status_filter = FeatureStatus(status)
            except ValueError:
                pass

        proposals = self._feature_researcher.get_all_proposals(status_filter)
        return [p.to_dict() for p in proposals]

    def get_evolution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent evolution records"""
        if not self._self_evolution:
            return []
        return self._self_evolution.get_recent_evolutions(limit)

    def get_proposals_summary(self) -> str:
        """Human-readable proposals summary"""
        if not self._feature_researcher:
            return "Feature researcher not active."
        return self._feature_researcher.get_proposals_summary()

    def get_evolution_status(self) -> str:
        """Human-readable evolution status"""
        if not self._self_evolution:
            return "Self evolution not active."
        return self._self_evolution.get_status_description()

    # ═══════════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════════════════

    def get_stats(self) -> Dict[str, Any]:
        """Unified stats from all subsystems"""
        stats: Dict[str, Any] = {
            "running": self._running,
            "all_healthy": self._is_all_healthy(),
            "started_at": (
                self._started_at.isoformat() if self._started_at else None
            ),
            "uptime_seconds": (
                (datetime.now() - self._started_at).total_seconds()
                if self._started_at
                else 0
            ),
            # Aggregate
            "aggregate": {
                "errors_detected": self._errors_detected,
                "errors_fixed": self._errors_fixed,
                "features_proposed": self._features_proposed,
                "features_implemented": self._features_implemented,
            },
            # Per-subsystem
            "subsystems": {},
        }

        # ── CodeMonitor stats ──
        if self._code_monitor:
            try:
                stats["subsystems"]["code_monitor"] = self._code_monitor.get_stats()
            except Exception as e:
                stats["subsystems"]["code_monitor"] = {"error": str(e)}
        else:
            stats["subsystems"]["code_monitor"] = {"status": "not_loaded"}

        # ── ErrorFixer stats ──
        if self._error_fixer:
            try:
                stats["subsystems"]["error_fixer"] = self._error_fixer.get_stats()
            except Exception as e:
                stats["subsystems"]["error_fixer"] = {"error": str(e)}
        else:
            stats["subsystems"]["error_fixer"] = {"status": "not_loaded"}

        # ── FeatureResearcher stats ──
        if self._feature_researcher:
            try:
                stats["subsystems"]["feature_researcher"] = (
                    self._feature_researcher.get_stats()
                )
            except Exception as e:
                stats["subsystems"]["feature_researcher"] = {"error": str(e)}
        else:
            stats["subsystems"]["feature_researcher"] = {"status": "not_loaded"}

        # ── SelfEvolution stats ──
        if self._self_evolution:
            try:
                stats["subsystems"]["self_evolution"] = (
                    self._self_evolution.get_stats()
                )
            except Exception as e:
                stats["subsystems"]["self_evolution"] = {"error": str(e)}
        else:
            stats["subsystems"]["self_evolution"] = {"status": "not_loaded"}

        return stats

    def get_full_status(self) -> str:
        """Comprehensive human-readable status report"""
        parts = [
            "╔══════════════════════════════════════════════╗",
            "║     SELF-IMPROVEMENT SYSTEM STATUS           ║",
            "╚══════════════════════════════════════════════╝",
        ]

        stats = self.get_stats()
        agg = stats["aggregate"]

        parts.append(f"System: {'🟢 Running' if stats['running'] else '🔴 Stopped'}")
        parts.append(f"Health: {'✅ All Healthy' if stats['all_healthy'] else '⚠️ Issues Detected'}")

        if stats["uptime_seconds"] > 0:
            hours = int(stats["uptime_seconds"] // 3600)
            mins = int((stats["uptime_seconds"] % 3600) // 60)
            parts.append(f"Uptime: {hours}h {mins}m")

        parts.append("")
        parts.append("── Aggregate ──")
        parts.append(f"Errors detected:       {agg['errors_detected']}")
        parts.append(f"Errors auto-fixed:     {agg['errors_fixed']}")
        parts.append(f"Features proposed:     {agg['features_proposed']}")
        parts.append(f"Features implemented:  {agg['features_implemented']}")

        # CodeMonitor
        parts.append("")
        parts.append("── CodeMonitor ──")
        cm = stats["subsystems"].get("code_monitor", {})
        if "error" in cm or "status" in cm:
            parts.append(f"  {cm.get('error', cm.get('status', 'unknown'))}")
        else:
            parts.append(f"  Running: {cm.get('running', '?')}")
            parts.append(f"  Files watched: {cm.get('files_watched', '?')}")
            parts.append(f"  Errors found: {cm.get('errors_detected', '?')}")

        # ErrorFixer
        parts.append("")
        parts.append("── ErrorFixer ──")
        ef = stats["subsystems"].get("error_fixer", {})
        if "error" in ef or "status" in ef:
            parts.append(f"  {ef.get('error', ef.get('status', 'unknown'))}")
        else:
            parts.append(f"  Running: {ef.get('running', '?')}")
            parts.append(f"  Fixed: {ef.get('errors_fixed', '?')}")

        # FeatureResearcher
        parts.append("")
        parts.append("── FeatureResearcher ──")
        fr = stats["subsystems"].get("feature_researcher", {})
        if "error" in fr or "status" in fr:
            parts.append(f"  {fr.get('error', fr.get('status', 'unknown'))}")
        else:
            parts.append(f"  Running: {fr.get('running', '?')}")
            parts.append(f"  Research cycles: {fr.get('research_cycles', '?')}")
            parts.append(f"  Total proposals: {fr.get('total_proposals', '?')}")
            bd = fr.get("status_breakdown", {})
            if bd:
                parts.append(
                    f"  Approved: {bd.get('approved', 0)} | "
                    f"Completed: {bd.get('completed', 0)} | "
                    f"Failed: {bd.get('failed', 0)}"
                )

        # SelfEvolution
        parts.append("")
        parts.append("── SelfEvolution ──")
        se = stats["subsystems"].get("self_evolution", {})
        if "error" in se or "status" in se:
            parts.append(f"  {se.get('error', se.get('status', 'unknown'))}")
        else:
            parts.append(f"  Running: {se.get('running', '?')}")
            parts.append(f"  Status: {se.get('current_status', '?')}")
            parts.append(
                f"  Evolutions: {se.get('total_succeeded', 0)}/"
                f"{se.get('total_attempted', 0)} "
                f"({se.get('success_rate', 0):.0%})"
            )
            parts.append(f"  Files created: {se.get('total_files_created', 0)}")
            parts.append(f"  Lines added: {se.get('total_lines_added', 0)}")
            parts.append(f"  Rollbacks: {se.get('total_rollbacks', 0)}")

            current = se.get("current_evolution")
            if current:
                parts.append(f"  🔄 Currently evolving: {current}")

        return "\n".join(parts)

# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_self_improvement_system: Optional[SelfImprovementSystem] = None
_sis_lock = threading.Lock()

def _get_system() -> SelfImprovementSystem:
    global _self_improvement_system
    if _self_improvement_system is None:
        with _sis_lock:
            if _self_improvement_system is None:
                _self_improvement_system = SelfImprovementSystem()
    return _self_improvement_system

# Module-level singleton
self_improvement_system = _get_system()

# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Core system
    "SelfImprovementSystem",
    "self_improvement_system",
    # Component getters
    "get_code_monitor",
    "get_error_fixer",
    "get_feature_researcher",
    "get_self_evolution",
    "get_improvement_analytics",
    "get_singularity_engine",
]

if __name__ == "__main__":
    print("🔧 Self-Improvement System Test\n")

    system = self_improvement_system
    system.start()

    time.sleep(3)

    print(f"\n{system.get_full_status()}")
    print(f"\nStats: {json.dumps(system.get_stats(), indent=2, default=str)}")

    time.sleep(2)
    system.stop()

    print("\n✅ Done")