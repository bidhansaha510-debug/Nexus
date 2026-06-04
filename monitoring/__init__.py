"""
NEXUS AI - Monitoring Package
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
24/7 User Behavior Monitoring, Pattern Analysis, and Adaptation.

Components:
  • UserTracker        — Raw sensor layer: active windows, apps, activity
  • PatternAnalyzer    — Statistical pattern recognition engine
  • AdaptationEngine   — Behavioral adaptation based on learned patterns
  • SystemHealthMonitor— System resource and health tracking
  • ScreenTimeTracker  — Screen time analytics and wellbeing
  • MonitoringSystem   — Unified orchestrator for all monitoring

Data Flow:
  UserTracker (3s) ─► PatternAnalyzer (5min) ─► AdaptationEngine (15min)
       │                       │                          │
   Raw Snapshots         Detected Patterns         Brain Prompt Injection
       │                       │                          │
   SQLite Storage        SQLite Storage            System Prompt Context
"""

import threading
import time
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.logger import get_logger, log_system
from core.event_bus import EventType, publish

logger = get_logger("monitoring")


# ═══════════════════════════════════════════════════════════════════════════════
# LAZY IMPORTS & SINGLETONS
# ═══════════════════════════════════════════════════════════════════════════════

_user_tracker = None
_pattern_analyzer = None
_adaptation_engine = None
_health_monitor = None
_screen_time_tracker = None
_lock = threading.Lock()


def _get_user_tracker():
    global _user_tracker
    if _user_tracker is None:
        with _lock:
            if _user_tracker is None:
                from monitoring.user_tracker import UserTracker
                _user_tracker = UserTracker()
    return _user_tracker


def _get_pattern_analyzer():
    global _pattern_analyzer
    if _pattern_analyzer is None:
        with _lock:
            if _pattern_analyzer is None:
                from monitoring.pattern_analyzer import PatternAnalyzer
                _pattern_analyzer = PatternAnalyzer()
    return _pattern_analyzer


def _get_adaptation_engine():
    global _adaptation_engine
    if _adaptation_engine is None:
        with _lock:
            if _adaptation_engine is None:
                from monitoring.adaptation_engine import AdaptationEngine
                _adaptation_engine = AdaptationEngine()
    return _adaptation_engine


def _get_health_monitor():
    global _health_monitor
    if _health_monitor is None:
        with _lock:
            if _health_monitor is None:
                from monitoring.system_health_monitor import SystemHealthMonitor
                _health_monitor = SystemHealthMonitor()
    return _health_monitor


def _get_screen_time_tracker():
    global _screen_time_tracker
    if _screen_time_tracker is None:
        with _lock:
            if _screen_time_tracker is None:
                from monitoring.screen_time_tracker import ScreenTimeTracker
                _screen_time_tracker = ScreenTimeTracker()
    return _screen_time_tracker


# ═══════════════════════════════════════════════════════════════════════════════
# MONITORING SYSTEM — Unified Orchestrator
# ═══════════════════════════════════════════════════════════════════════════════

class MonitoringSystem:
    """
    Orchestrates all monitoring components.

    Timing (base loop = 30s):
      Every 30s  — Check user presence (idle/return transitions)
      Every 5min — Feed tracker snapshots → PatternAnalyzer
      Every 15min— Feed detected patterns → AdaptationEngine
      Every 30min— Sync learned user profile → StateManager
      Every 1hr  — Deep pattern analysis + daily stats
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

        self._running = False
        self._user_tracker = None
        self._pattern_analyzer = None
        self._adaptation_engine = None
        self._health_monitor = None
        self._screen_time_tracker = None
        self._orchestration_thread: Optional[threading.Thread] = None
        self._health_check_thread: Optional[threading.Thread] = None
        self._startup_time: Optional[datetime] = None

        # ── Orchestration Timing (all in cycles of 30s base) ──
        self._orchestration_interval = 30      # base loop (seconds)
        self._pattern_feed_cycles = 10         # 10 × 30s = 5 min
        self._adaptation_feed_cycles = 30      # 30 × 30s = 15 min
        self._deep_analysis_cycles = 120       # 120 × 30s = 1 hr
        self._state_sync_cycles = 60           # 60 × 30s = 30 min
        self._health_check_interval = 60       # health check every 60s
        self._cycle_count = 0

        # ── User Presence State ──
        self._user_was_present = True
        self._user_idle_since: Optional[datetime] = None

        # ── Orchestration Metrics ──
        self._metrics = {
            "total_cycles": 0,
            "failed_cycles": 0,
            "component_failures": {},       # component_name -> failure count
            "component_restarts": {},       # component_name -> restart count
            "last_cycle_time_ms": 0.0,
            "avg_cycle_time_ms": 0.0,
            "cycle_times": [],              # last 50 cycle times
        }

        # ── Component Health State ──
        self._component_health: Dict[str, Dict[str, Any]] = {
            "user_tracker": {"status": "stopped", "failures": 0, "last_check": None},
            "pattern_analyzer": {"status": "stopped", "failures": 0, "last_check": None},
            "adaptation_engine": {"status": "stopped", "failures": 0, "last_check": None},
            "health_monitor": {"status": "stopped", "failures": 0, "last_check": None},
            "screen_time_tracker": {"status": "stopped", "failures": 0, "last_check": None},
        }
        self._max_restart_attempts = 3

        logger.info("MonitoringSystem initialized")

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start all monitoring components in correct order with graceful degradation"""
        if self._running:
            logger.warning("MonitoringSystem already running")
            return

        self._running = True
        self._startup_time = datetime.now()

        # Initialize and start core components (graceful degradation)
        self._start_component("user_tracker", _get_user_tracker)
        self._start_component("pattern_analyzer", _get_pattern_analyzer)
        self._start_component("adaptation_engine", _get_adaptation_engine)
        self._start_component("health_monitor", _get_health_monitor)
        self._start_component("screen_time_tracker", _get_screen_time_tracker)

        # Wire components together (only if both sides are available)
        if self._user_tracker and self._pattern_analyzer:
            self._user_tracker.set_pattern_analyzer(self._pattern_analyzer)
        if self._adaptation_engine and self._pattern_analyzer:
            self._adaptation_engine.set_pattern_analyzer(self._pattern_analyzer)

        # Start orchestration loop
        self._orchestration_thread = threading.Thread(
            target=self._orchestration_loop,
            daemon=True,
            name="Monitoring-Orchestrator"
        )
        self._orchestration_thread.start()

        # Start health check thread
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True,
            name="Monitoring-HealthCheck"
        )
        self._health_check_thread.start()

        active_count = sum(
            1 for h in self._component_health.values() if h["status"] == "running"
        )
        log_system(
            f"👁️ MonitoringSystem ACTIVE — {active_count}/5 components online"
        )

    def _start_component(self, name: str, getter_fn, restart: bool = False):
        """Start a single component with error handling"""
        try:
            component = getter_fn()
            component.start()
            setattr(self, f"_{name}", component)
            self._component_health[name]["status"] = "running"
            self._component_health[name]["last_check"] = datetime.now().isoformat()
            if restart:
                self._metrics.setdefault("component_restarts", {})
                self._metrics["component_restarts"][name] = (
                    self._metrics["component_restarts"].get(name, 0) + 1
                )
                logger.info(f"Successfully restarted component: {name}")
            else:
                logger.debug(f"Started component: {name}")
        except Exception as e:
            logger.error(f"Failed to start component {name}: {e}")
            self._component_health[name]["status"] = "failed"
            self._component_health[name]["failures"] = (
                self._component_health[name].get("failures", 0) + 1
            )
            self._metrics.setdefault("component_failures", {})
            self._metrics["component_failures"][name] = (
                self._metrics["component_failures"].get(name, 0) + 1
            )

    def stop(self):
        """Stop all monitoring components gracefully"""
        if not self._running:
            return

        logger.info("MonitoringSystem shutting down...")
        self._running = False

        # Stop all components in reverse order
        components_to_stop = [
            ("screen_time_tracker", self._screen_time_tracker),
            ("health_monitor", self._health_monitor),
            ("adaptation_engine", self._adaptation_engine),
            ("pattern_analyzer", self._pattern_analyzer),
            ("user_tracker", self._user_tracker),
        ]

        for name, component in components_to_stop:
            if component:
                try:
                    component.stop()
                    self._component_health[name]["status"] = "stopped"
                except Exception as e:
                    logger.error(f"Error stopping {name}: {e}")
                    self._component_health[name]["status"] = "error"

        for t in [self._orchestration_thread, self._health_check_thread]:
            if t and t.is_alive():
                t.join(timeout=5.0)

        logger.info("MonitoringSystem stopped")

    # ═══════════════════════════════════════════════════════════════════════════
    # ORCHESTRATION LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    def _orchestration_loop(self):
        """
        Periodic orchestration between components.
        
        Base interval: 30s
        Pattern feed:  every 5 min   (cycle % 10)
        Adaptation:    every 15 min  (cycle % 30)
        State sync:    every 30 min  (cycle % 60)
        Deep analysis: every 1 hr    (cycle % 120)
        """
        logger.info("Monitoring orchestration loop started")

        while self._running:
            cycle_start = time.time()
            try:
                time.sleep(self._orchestration_interval)
                self._cycle_count += 1
                cycle = self._cycle_count

                # ── 1. User Presence Detection (every cycle = 30s) ──
                self._check_user_presence()

                # ── 2. Feed tracker → analyzer (every 5 min) ──
                if cycle % self._pattern_feed_cycles == 0:
                    self._feed_tracker_to_analyzer()

                # ── 3. Feed patterns → adapter (every 15 min) ──
                if cycle % self._adaptation_feed_cycles == 0:
                    self._feed_patterns_to_adapter()

                # ── 4. Sync to state manager (every 30 min) ──
                if cycle % self._state_sync_cycles == 0:
                    self._sync_to_state_manager()

                # ── 5. Deep analysis (every 1 hour) ──
                if cycle % self._deep_analysis_cycles == 0:
                    self._run_deep_analysis()

                # Track metrics
                cycle_time_ms = (time.time() - cycle_start) * 1000
                self._metrics["total_cycles"] += 1
                self._metrics["last_cycle_time_ms"] = round(cycle_time_ms, 2)
                times = self._metrics["cycle_times"]
                times.append(cycle_time_ms)
                if len(times) > 50:
                    times.pop(0)
                self._metrics["avg_cycle_time_ms"] = round(
                    sum(times) / len(times), 2
                )

            except Exception as e:
                logger.error(f"Orchestration error: {e}")
                self._metrics["failed_cycles"] = (
                    self._metrics.get("failed_cycles", 0) + 1
                )
                time.sleep(10)

    def _health_check_loop(self):
        """Periodic health checks on all components with auto-restart"""
        logger.info("Health check loop started")
        time.sleep(30)  # Initial grace period

        while self._running:
            try:
                self._run_health_checks()
                time.sleep(self._health_check_interval)
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                time.sleep(30)

    def _run_health_checks(self):
        """Check each component's health and auto-restart if needed"""
        now = datetime.now().isoformat()
        checks = [
            ("user_tracker", self._user_tracker, _get_user_tracker),
            ("pattern_analyzer", self._pattern_analyzer, _get_pattern_analyzer),
            ("adaptation_engine", self._adaptation_engine, _get_adaptation_engine),
            ("health_monitor", self._health_monitor, _get_health_monitor),
            ("screen_time_tracker", self._screen_time_tracker, _get_screen_time_tracker),
        ]

        for name, component, getter_fn in checks:
            health = self._component_health[name]
            health["last_check"] = now

            if component is None:
                # Component never started or failed to initialize
                if health["status"] == "failed" and health.get("failures", 0) < self._max_restart_attempts:
                    logger.warning(f"Attempting to restart failed component: {name}")
                    self._start_component(name, getter_fn, restart=True)
                continue

            try:
                # Check if component has a running flag or get_stats
                if hasattr(component, '_running'):
                    if not component._running:
                        health["status"] = "stopped"
                        if health.get("failures", 0) < self._max_restart_attempts:
                            logger.warning(f"Component {name} stopped, restarting...")
                            self._start_component(name, getter_fn, restart=True)
                    else:
                        health["status"] = "running"
                        health["failures"] = 0  # Reset on healthy check
                elif hasattr(component, 'get_stats'):
                    stats = component.get_stats()
                    if stats.get("running", True):
                        health["status"] = "running"
                    else:
                        health["status"] = "stopped"
                else:
                    health["status"] = "running"

            except Exception as e:
                health["status"] = "error"
                health["failures"] = health.get("failures", 0) + 1
                logger.error(f"Health check failed for {name}: {e}")

                if health["failures"] < self._max_restart_attempts:
                    logger.warning(
                        f"Auto-restarting {name} (attempt {health['failures']}/{self._max_restart_attempts})"
                    )
                    self._start_component(name, getter_fn, restart=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # ORCHESTRATION STEPS
    # ═══════════════════════════════════════════════════════════════════════════

    def _check_user_presence(self):
        """Detect user idle/return transitions and publish events"""
        if not self._user_tracker:
            return

        try:
            activity = self._user_tracker.get_current_activity()
            is_present = activity.get("is_user_present", True)
            idle_seconds = activity.get("idle_seconds", 0)

            # User just went idle
            if self._user_was_present and not is_present:
                self._user_idle_since = datetime.now()

                current_window = activity.get("current_window")
                last_app = "unknown"
                if current_window and isinstance(current_window, dict):
                    last_app = current_window.get("process_name", "unknown")

                publish(
                    EventType.USER_IDLE_DETECTED,
                    {
                        "idle_seconds": idle_seconds,
                        "last_app": last_app,
                        "timestamp": datetime.now().isoformat()
                    },
                    source="monitoring_system"
                )
                logger.debug(f"User went idle (idle for {idle_seconds:.0f}s)")

            # User just returned
            elif not self._user_was_present and is_present:
                away_duration = 0.0
                if self._user_idle_since:
                    away_duration = (
                        datetime.now() - self._user_idle_since
                    ).total_seconds()

                current_window = activity.get("current_window")
                current_app = "unknown"
                if current_window and isinstance(current_window, dict):
                    current_app = current_window.get("process_name", "unknown")

                publish(
                    EventType.USER_RETURNED,
                    {
                        "away_seconds": away_duration,
                        "current_app": current_app,
                        "timestamp": datetime.now().isoformat()
                    },
                    source="monitoring_system"
                )
                logger.debug(f"User returned after {away_duration:.0f}s away")
                self._user_idle_since = None

            self._user_was_present = is_present

        except Exception as e:
            logger.debug(f"Presence check error: {e}")

    def _feed_tracker_to_analyzer(self):
        """Feed latest tracker snapshot to pattern analyzer"""
        if not self._user_tracker or not self._pattern_analyzer:
            return

        try:
            snapshot = self._user_tracker.get_current_snapshot()
            if snapshot:
                self._pattern_analyzer.ingest_snapshot(snapshot)

            logger.debug("Fed tracker snapshot to pattern analyzer")

        except Exception as e:
            logger.error(f"Tracker→Analyzer feed error: {e}")

    def _feed_patterns_to_adapter(self):
        """Feed detected patterns to adaptation engine"""
        if not self._pattern_analyzer or not self._adaptation_engine:
            return

        try:
            patterns = self._pattern_analyzer.get_current_patterns()
            if patterns:
                self._adaptation_engine.update_from_patterns(patterns)

                # Publish pattern event
                publish(
                    EventType.USER_PATTERN_IDENTIFIED,
                    {
                        "analysis_count": patterns.get("analysis_count", 0),
                        "data_points": patterns.get("data_points", 0),
                        "timestamp": datetime.now().isoformat()
                    },
                    source="monitoring_system"
                )

            logger.debug("Fed patterns to adaptation engine")

        except Exception as e:
            logger.error(f"Patterns→Adapter feed error: {e}")

    def _run_deep_analysis(self):
        """Run deep pattern analysis (expensive, runs hourly)"""
        if not self._pattern_analyzer:
            return

        try:
            logger.info("Running deep user behavior analysis...")
            self._pattern_analyzer.run_deep_analysis()
            logger.info("Deep analysis complete")

        except Exception as e:
            logger.error(f"Deep analysis error: {e}")

    def _sync_to_state_manager(self):
        """Sync learned user data to the global state manager"""
        try:
            from core.state_manager import state_manager

            # Sync current activity from tracker
            if self._user_tracker:
                activity = self._user_tracker.get_current_activity()
                
                current_window = activity.get("current_window")
                app_name = ""
                if current_window and isinstance(current_window, dict):
                    app_name = current_window.get("process_name", "")
                
                state_manager.update_user(
                    current_application=app_name,
                    activity_level=activity.get("activity_level", "idle"),
                    is_present=activity.get("is_user_present", True),
                    idle_seconds=activity.get("idle_seconds", 0),
                    current_app_category=activity.get(
                        "current_app_category", ""
                    )
                )

            # Sync user profile from pattern analyzer
            if self._pattern_analyzer:
                profile = self._pattern_analyzer.get_user_profile()
                if profile:
                    # Transform profile into the format update_user_patterns expects
                    personality_data = profile.get("personality", {})
                    schedule_data = profile.get("schedule", {})
                    productivity_data = profile.get("productivity", {})

                    patterns_dict = {}

                    # Work style
                    if profile.get("work_style"):
                        patterns_dict["work_style"] = profile["work_style"]

                    # Technical level from personality
                    tech = personality_data.get("tech_proficiency", 0.5)
                    if tech > 0.7:
                        patterns_dict["technical_level"] = "advanced"
                    elif tech > 0.4:
                        patterns_dict["technical_level"] = "intermediate"
                    else:
                        patterns_dict["technical_level"] = "beginner"

                    # Personality traits (Big Five)
                    trait_keys = [
                        "openness", "conscientiousness",
                        "extraversion", "agreeableness", "neuroticism"
                    ]
                    traits = {}
                    for key in trait_keys:
                        if key in personality_data:
                            traits[key] = personality_data[key]
                    if traits:
                        patterns_dict["personality_traits"] = traits

                    # Communication preference
                    comm_pref = personality_data.get("communication_preference")
                    if comm_pref:
                        patterns_dict["communication_style"] = comm_pref

                    # Top apps & categories
                    top_activities = profile.get("top_activities", {})
                    if top_activities:
                        patterns_dict["top_categories"] = list(
                            top_activities.keys()
                        )[:10]

                    # Productive hours
                    best_hours = productivity_data.get("best_hours", [])
                    if best_hours:
                        patterns_dict["typical_hours"] = best_hours

                    # Top apps from tracker
                    if self._user_tracker:
                        app_usage = self._user_tracker.get_app_usage_today()
                        if app_usage:
                            patterns_dict["top_apps"] = list(
                                app_usage.keys()
                            )[:10]

                    if patterns_dict:
                        state_manager.update_user_patterns(patterns_dict)

            # Sync communication style from adaptation engine
            if self._adaptation_engine:
                comm = self._adaptation_engine.get_communication_profile()
                if comm and comm.get("tone"):
                    state_manager.update_user(
                        communication_style=comm["tone"]
                    )

            logger.debug("Synced monitoring data to state manager")

            # Publish profile update event
            publish(
                EventType.USER_PROFILE_UPDATED,
                {"timestamp": datetime.now().isoformat()},
                source="monitoring_system"
            )

        except Exception as e:
            logger.error(f"State sync error: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    @property
    def user_tracker(self):
        return self._user_tracker

    @property
    def pattern_analyzer(self):
        return self._pattern_analyzer

    @property
    def adaptation_engine(self):
        return self._adaptation_engine

    @property
    def health_monitor(self):
        return self._health_monitor

    @property
    def screen_time_tracker(self):
        return self._screen_time_tracker

    @property
    def is_running(self) -> bool:
        return self._running

    def get_user_summary(self) -> Dict[str, Any]:
        """Get comprehensive user summary from all components"""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "monitoring_uptime": self._get_uptime_str()
        }

        if self._user_tracker:
            try:
                summary["current_activity"] = (
                    self._user_tracker.get_current_activity()
                )
                summary["app_usage_today"] = (
                    self._user_tracker.get_app_usage_today()
                )
                summary["category_usage_today"] = (
                    self._user_tracker.get_category_usage_today()
                )
            except Exception as e:
                summary["tracker_error"] = str(e)

        if self._pattern_analyzer:
            try:
                summary["patterns"] = (
                    self._pattern_analyzer.get_current_patterns()
                )
                summary["user_profile"] = (
                    self._pattern_analyzer.get_user_profile()
                )
            except Exception as e:
                summary["analyzer_error"] = str(e)

        if self._adaptation_engine:
            try:
                summary["adaptations"] = (
                    self._adaptation_engine.get_active_adaptations()
                )
                summary["communication_profile"] = (
                    self._adaptation_engine.get_communication_profile()
                )
            except Exception as e:
                summary["adapter_error"] = str(e)

        if self._health_monitor:
            try:
                summary["system_health"] = (
                    self._health_monitor.get_current_health()
                )
            except Exception as e:
                summary["health_monitor_error"] = str(e)

        if self._screen_time_tracker:
            try:
                summary["screen_time"] = (
                    self._screen_time_tracker.get_daily_report()
                )
            except Exception as e:
                summary["screen_time_error"] = str(e)

        return summary

    def get_user_context_for_brain(self) -> str:
        """
        Get a formatted context string for injection into the brain's
        response generation. Called by nexus_brain._build_response_context()
        """
        parts = []

        # Current activity from tracker
        if self._user_tracker:
            try:
                activity = self._user_tracker.get_current_activity()
                current_window = activity.get("current_window")
                app_name = "unknown"
                if current_window and isinstance(current_window, dict):
                    app_name = current_window.get("process_name", "unknown")

                parts.append(
                    f"User is currently using: {app_name} "
                    f"({activity.get('current_app_category', '?')}) | "
                    f"Activity: {activity.get('activity_level', '?')} | "
                    f"Idle: {activity.get('idle_seconds', 0):.0f}s"
                )
            except Exception:
                pass

        # Detected patterns from analyzer
        if self._pattern_analyzer:
            try:
                context = self._pattern_analyzer.get_context_for_brain()
                if context:
                    parts.append(context)
            except Exception:
                pass

        # Active adaptations
        if self._adaptation_engine:
            try:
                prompt = self._adaptation_engine.get_adaptation_prompt()
                if prompt:
                    parts.append(prompt)
            except Exception:
                pass

        return "\n".join(parts) if parts else ""

    def should_stay_quiet(self) -> bool:
        """Check if NEXUS should avoid proactive engagement"""
        if self._adaptation_engine:
            try:
                return self._adaptation_engine.should_be_quiet()
            except Exception:
                pass
        return False

    def get_proactive_suggestions(self) -> List[str]:
        """Get any proactive things NEXUS could say/do"""
        if self._adaptation_engine:
            try:
                return self._adaptation_engine.get_current_suggestions()
            except Exception:
                pass
        return []

    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring system statistics with component health"""
        stats = {
            "running": self._running,
            "uptime": self._get_uptime_str(),
            "orchestration_cycles": self._cycle_count,
            "user_present": self._user_was_present,
            "metrics": self._metrics,
            "component_health": self._component_health,
        }

        if self._user_tracker:
            try:
                stats["tracker"] = self._user_tracker.get_stats()
            except Exception as e:
                stats["tracker"] = {"error": str(e)}

        if self._pattern_analyzer:
            try:
                stats["analyzer"] = self._pattern_analyzer.get_stats()
            except Exception as e:
                stats["analyzer"] = {"error": str(e)}

        if self._adaptation_engine:
            try:
                stats["adapter"] = self._adaptation_engine.get_stats()
            except Exception as e:
                stats["adapter"] = {"error": str(e)}

        if self._health_monitor:
            try:
                stats["health_monitor"] = self._health_monitor.get_stats()
            except Exception as e:
                stats["health_monitor"] = {"error": str(e)}

        if self._screen_time_tracker:
            try:
                stats["screen_time"] = self._screen_time_tracker.get_stats()
            except Exception as e:
                stats["screen_time"] = {"error": str(e)}

        return stats

    def _get_uptime_str(self) -> str:
        """Get monitoring uptime as string"""
        if not self._startup_time:
            return "not started"
        seconds = (datetime.now() - self._startup_time).total_seconds()
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL SINGLETONS
# ═══════════════════════════════════════════════════════════════════════════════

monitoring_system = MonitoringSystem()


def get_user_tracker():
    return _get_user_tracker()


def get_pattern_analyzer():
    return _get_pattern_analyzer()


def get_adaptation_engine():
    return _get_adaptation_engine()


def get_health_monitor():
    return _get_health_monitor()


def get_screen_time_tracker():
    return _get_screen_time_tracker()


__all__ = [
    "MonitoringSystem", "monitoring_system",
    "get_user_tracker", "get_pattern_analyzer", "get_adaptation_engine",
    "get_health_monitor", "get_screen_time_tracker",
]