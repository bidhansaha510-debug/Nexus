"""
NEXUS AI - Pattern Analyzer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Statistical pattern recognition engine that processes raw tracking
data from UserTracker and extracts meaningful behavioral patterns.

Analysis Domains:
  • Temporal patterns    — when the user works, peak hours, routines
  • Application patterns — favorite apps, usage sequences, categories
  • Workflow patterns    — app transition chains, task groupings
  • Productivity patterns— focus sessions, distraction frequency
  • Communication style  — typing speed, message length patterns
  • Anomaly detection    — unusual behavior deviations
  • User personality     — inferred traits from behavior

All patterns are persisted in SQLite and updated incrementally.
"""

import threading
import time
import sqlite3
import json
import math
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import defaultdict, deque, Counter
from enum import Enum, auto

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from utils.logger import get_logger, log_learning
from core.event_bus import EventType, publish, Event
from core.state_manager import state_manager

logger = get_logger("pattern_analyzer")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class PatternType(Enum):
    TEMPORAL = "temporal"
    APP_USAGE = "app_usage"
    WORKFLOW = "workflow"
    PRODUCTIVITY = "productivity"
    COMMUNICATION = "communication"
    ANOMALY = "anomaly"
    PERSONALITY = "personality"


class DaySegment(Enum):
    EARLY_MORNING = "early_morning"      # 5-8
    MORNING = "morning"                   # 8-12
    AFTERNOON = "afternoon"               # 12-17
    EVENING = "evening"                   # 17-21
    NIGHT = "night"                       # 21-1
    LATE_NIGHT = "late_night"             # 1-5

    @classmethod
    def from_hour(cls, hour: int) -> "DaySegment":
        if 5 <= hour < 8:
            return cls.EARLY_MORNING
        elif 8 <= hour < 12:
            return cls.MORNING
        elif 12 <= hour < 17:
            return cls.AFTERNOON
        elif 17 <= hour < 21:
            return cls.EVENING
        elif 21 <= hour or hour < 1:
            return cls.NIGHT
        else:
            return cls.LATE_NIGHT


class ProductivityLevel(Enum):
    DEEP_FOCUS = "deep_focus"
    PRODUCTIVE = "productive"
    MIXED = "mixed"
    DISTRACTED = "distracted"
    IDLE = "idle"


@dataclass
class TemporalPattern:
    """When the user is active"""
    most_active_hours: List[int] = field(default_factory=list)
    least_active_hours: List[int] = field(default_factory=list)
    avg_session_start: float = 9.0       # avg hour of day they start
    avg_session_end: float = 17.0        # avg hour of day they stop
    most_active_day_segment: str = "morning"
    weekly_pattern: Dict[int, float] = field(default_factory=dict)  # dow → avg activity
    typical_session_duration_hours: float = 4.0
    is_night_owl: bool = False
    is_early_bird: bool = False
    consistency_score: float = 0.5       # 0=chaotic, 1=very routine

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AppUsagePattern:
    """What apps the user uses most"""
    top_apps: Dict[str, float] = field(default_factory=dict)           # app → hours
    top_categories: Dict[str, float] = field(default_factory=dict)     # category → hours
    avg_app_session_minutes: float = 10.0
    app_diversity_score: float = 0.5      # 0=single app, 1=many apps
    browser_dominant: bool = False
    code_dominant: bool = False
    primary_workflow: str = "general"     # "developer", "writer", "designer", etc.
    app_loyalty: Dict[str, float] = field(default_factory=dict)        # app → loyalty 0-1

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WorkflowPattern:
    """How the user transitions between apps"""
    common_sequences: List[List[str]] = field(default_factory=list)    # frequent app chains
    transition_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    avg_switches_per_hour: float = 10.0
    multitasking_score: float = 0.5       # 0=sequential, 1=heavy switcher
    common_app_pairs: List[Tuple[str, str]] = field(default_factory=list)
    task_clusters: List[List[str]] = field(default_factory=list)       # apps used together

    def to_dict(self) -> dict:
        d = asdict(self)
        # Convert tuples to lists for JSON
        d["common_app_pairs"] = [list(p) for p in self.common_app_pairs]
        return d


@dataclass
class ProductivityPattern:
    """How productive/focused the user is"""
    avg_focus_duration_minutes: float = 15.0
    max_focus_duration_minutes: float = 60.0
    avg_break_duration_minutes: float = 5.0
    distraction_frequency_per_hour: float = 3.0
    productive_hours: List[int] = field(default_factory=list)
    distraction_apps: List[str] = field(default_factory=list)
    focus_apps: List[str] = field(default_factory=list)
    daily_productivity_score: float = 0.5
    focus_trend: str = "stable"           # "improving", "declining", "stable"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class UserPersonalityInference:
    """Personality traits inferred from behavior"""
    # Big Five approximations from behavior
    openness: float = 0.5           # diverse apps/topics → high
    conscientiousness: float = 0.5  # consistent schedule, focused → high
    extraversion: float = 0.5       # communication apps heavy → high
    agreeableness: float = 0.5      # hard to infer, default
    neuroticism: float = 0.5        # erratic patterns → higher

    # Behavioral traits
    is_developer: bool = False
    is_creative: bool = False
    is_researcher: bool = False
    is_gamer: bool = False
    is_social: bool = False
    is_organized: bool = False
    is_multitasker: bool = False
    work_style: str = "balanced"    # "deep_worker", "multitasker", "browser_based", etc.
    tech_proficiency: float = 0.5   # 0=novice, 1=expert
    estimated_age_group: str = "unknown"  # "teen", "young_adult", "adult", "senior"

    # Preferences
    preferred_complexity: str = "moderate"  # "simple", "moderate", "complex"
    communication_preference: str = "balanced"  # "brief", "balanced", "verbose"
    
    confidence: float = 0.1         # how confident we are in these inferences

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DetectedAnomaly:
    """An unusual behavior deviation"""
    anomaly_type: str = ""
    description: str = ""
    severity: float = 0.0           # 0-1
    timestamp: str = ""
    baseline: str = ""
    observed: str = ""
    detection_method: str = "threshold"  # "threshold", "z_score", "iqr"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class EnergyCurve:
    """Activity intensity over a session's lifetime"""
    ramp_up_minutes: float = 0.0      # time to reach peak
    peak_level: float = 0.0           # highest avg activity
    peak_hour: int = 0                # hour of peak
    wind_down_minutes: float = 0.0    # time from peak to end
    curve_shape: str = "flat"          # "ramp_up", "peak_valley", "steady", "flat"
    normalized_curve: List[float] = field(default_factory=list)  # 10 buckets

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PredictiveSchedule:
    """Predicted next-day behavior"""
    predicted_start_hour: float = 9.0
    predicted_end_hour: float = 17.0
    predicted_peak_hours: List[int] = field(default_factory=list)
    predicted_active_minutes: float = 0.0
    predicted_top_app: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DistractionCascade:
    """Rapid app-switching triggered by a distraction app"""
    trigger_app: str = ""
    cascade_length: int = 0           # how many switches followed
    duration_seconds: float = 0.0
    apps_visited: List[str] = field(default_factory=list)
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WeeklyComparison:
    """This week vs last week deltas"""
    this_week_active_minutes: float = 0.0
    last_week_active_minutes: float = 0.0
    delta_percent: float = 0.0
    this_week_focus_avg: float = 0.0
    last_week_focus_avg: float = 0.0
    focus_delta_percent: float = 0.0
    this_week_switches: int = 0
    last_week_switches: int = 0
    productivity_trend: str = "stable"  # "improving", "declining", "stable"

    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# STATISTICAL HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def safe_mean(values: list, default: float = 0.0) -> float:
    return statistics.mean(values) if values else default

def safe_stdev(values: list, default: float = 0.0) -> float:
    return statistics.stdev(values) if len(values) >= 2 else default

def safe_median(values: list, default: float = 0.0) -> float:
    return statistics.median(values) if values else default

def entropy(counter: Counter) -> float:
    """Shannon entropy of a frequency distribution"""
    total = sum(counter.values())
    if total == 0:
        return 0.0
    probs = [c / total for c in counter.values() if c > 0]
    return -sum(p * math.log2(p) for p in probs)

def normalize_counter(counter: Counter, top_n: int = 20) -> Dict[str, float]:
    """Normalize a counter to proportions"""
    total = sum(counter.values())
    if total == 0:
        return {}
    return {
        k: round(v / total, 4)
        for k, v in counter.most_common(top_n)
    }


def z_score(value: float, values: list) -> float:
    """Calculate z-score of a value against a population"""
    if len(values) < 2:
        return 0.0
    mean = safe_mean(values)
    std = safe_stdev(values)
    if std == 0:
        return 0.0
    return (value - mean) / std


def iqr_outliers(values: list, factor: float = 1.5) -> Tuple[float, float]:
    """Return (lower_bound, upper_bound) using IQR method"""
    if len(values) < 4:
        return (float('-inf'), float('inf'))
    sorted_v = sorted(values)
    n = len(sorted_v)
    q1 = sorted_v[n // 4]
    q3 = sorted_v[3 * n // 4]
    iqr = q3 - q1
    return (q1 - factor * iqr, q3 + factor * iqr)


def bayesian_confidence(
    data_points: int, consistency: float = 0.5,
    min_points: int = 50, max_points: int = 5000
) -> float:
    """
    Bayesian-inspired confidence score.
    
    Increases with data volume (diminishing returns) and consistency.
    Returns 0.0 – 0.95.
    """
    # Volume factor: sigmoid-like curve
    volume = min(1.0, data_points / max_points)
    volume_factor = 1.0 - math.exp(-3.0 * volume)  # approaches 1.0
    
    # Minimum data gate
    if data_points < min_points:
        volume_factor *= data_points / min_points
    
    # Combine volume and consistency
    raw = volume_factor * 0.6 + consistency * 0.4
    return min(0.95, round(raw, 3))


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERN ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════

class PatternAnalyzer:
    """
    Processes raw tracking data and extracts statistical patterns.
    
    Data Flow:
    UserTracker → ingest_realtime_data() → internal buffers
    Periodic:   run_analysis() → pattern objects → SQLite storage
    On demand:  get_current_patterns(), get_user_profile()
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

        # ──── State ────
        self._running = False

        # ──── Pattern Objects ────
        self._temporal = TemporalPattern()
        self._app_usage = AppUsagePattern()
        self._workflow = WorkflowPattern()
        self._productivity = ProductivityPattern()
        self._personality = UserPersonalityInference()
        self._anomalies: List[DetectedAnomaly] = []

        # ──── Real-time Buffers ────
        self._realtime_buffer: deque = deque(maxlen=5000)
        self._window_sequence: deque = deque(maxlen=1000)   # recent app sequence
        self._activity_levels: deque = deque(maxlen=2000)    # (timestamp, level)
        self._hourly_activities: Dict[int, List[float]] = defaultdict(list)
        self._daily_app_time: Dict[str, float] = defaultdict(float)
        self._daily_category_time: Dict[str, float] = defaultdict(float)
        self._transition_counts: Dict[str, Dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self._focus_sessions: List[Dict[str, Any]] = []     # detected focus blocks
        self._app_session_durations: Dict[str, List[float]] = defaultdict(list)

        # ──── Long-term Accumulators ────
        self._total_app_time: Counter = Counter()
        self._total_category_time: Counter = Counter()
        self._total_transitions: int = 0
        self._total_snapshots_processed: int = 0
        self._days_tracked: int = 0
        self._analysis_count: int = 0
        self._last_analysis_time: Optional[datetime] = None

        # ──── Focus Tracking State ────
        self._current_focus_start: Optional[datetime] = None
        self._current_focus_app: str = ""
        self._focus_threshold_seconds: float = 120.0   # 2 min same app = focus

        # ──── Enhanced Analysis State ────
        self._energy_curve: EnergyCurve = EnergyCurve()
        self._predictive_schedule: PredictiveSchedule = PredictiveSchedule()
        self._distraction_cascades: List[DistractionCascade] = []
        self._weekly_comparison: WeeklyComparison = WeeklyComparison()
        self._bayesian_confidences: Dict[str, float] = {}  # pattern_type → confidence
        self._session_energy_buckets: List[List[float]] = [[] for _ in range(10)]
        self._distraction_apps: Set[str] = {
            "discord", "slack", "telegram", "whatsapp", "twitter",
            "reddit", "instagram", "facebook", "tiktok", "youtube"
        }
        self._cascade_tracking: Dict[str, Any] = {}
        self._daily_active_minutes_history: deque = deque(maxlen=30)
        self._daily_focus_minutes_history: deque = deque(maxlen=30)

        # ──── Database ────
        self._db_path = DATA_DIR / "user_profiles" / "patterns.db"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_lock = threading.Lock()
        self._init_database()

        # ──── Load Existing Patterns ────
        self._load_patterns()

        # ──── Threads ────
        self._analysis_thread: Optional[threading.Thread] = None
        self._analysis_interval = 300.0  # 5 minutes

        logger.info("PatternAnalyzer initialized")

    # ═══════════════════════════════════════════════════════════════════════════
    # DATABASE
    # ═══════════════════════════════════════════════════════════════════════════

    def _init_database(self):
        with self._db_lock:
            conn = sqlite3.connect(str(self._db_path))
            cursor = conn.cursor()
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    confidence REAL DEFAULT 0.0,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(pattern_type)
                );

                CREATE TABLE IF NOT EXISTS anomalies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    anomaly_type TEXT,
                    description TEXT,
                    severity REAL,
                    timestamp TEXT,
                    baseline TEXT,
                    observed TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS daily_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE NOT NULL,
                    total_active_seconds REAL,
                    total_idle_seconds REAL,
                    app_switches INTEGER,
                    top_apps TEXT,
                    top_categories TEXT,
                    avg_activity REAL,
                    productivity_score REAL,
                    focus_sessions INTEGER,
                    avg_focus_minutes REAL,
                    personality_snapshot TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS accumulators (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            conn.close()

    def _db_execute(self, query: str, params: tuple = (), fetch: bool = False):
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
                logger.error(f"Pattern DB error: {e}")
                return [] if fetch else None

    def _save_pattern(self, pattern_type: str, data: dict, confidence: float = 0.5):
        self._db_execute(
            """INSERT OR REPLACE INTO patterns (pattern_type, data, confidence, updated_at)
               VALUES (?, ?, ?, ?)""",
            (pattern_type, json.dumps(data, default=str), confidence,
             datetime.now().isoformat())
        )

    def _load_patterns(self):
        """Load previously saved patterns from DB"""
        rows = self._db_execute(
            "SELECT pattern_type, data, confidence FROM patterns", fetch=True
        )
        if not rows:
            return

        for row in rows:
            try:
                data = json.loads(row["data"])
                ptype = row["pattern_type"]

                if ptype == "temporal":
                    self._temporal = TemporalPattern(**{
                        k: v for k, v in data.items()
                        if k in TemporalPattern.__dataclass_fields__
                    })
                elif ptype == "app_usage":
                    self._app_usage = AppUsagePattern(**{
                        k: v for k, v in data.items()
                        if k in AppUsagePattern.__dataclass_fields__
                    })
                elif ptype == "workflow":
                    self._workflow = WorkflowPattern(**{
                        k: v for k, v in data.items()
                        if k in WorkflowPattern.__dataclass_fields__
                    })
                elif ptype == "productivity":
                    self._productivity = ProductivityPattern(**{
                        k: v for k, v in data.items()
                        if k in ProductivityPattern.__dataclass_fields__
                    })
                elif ptype == "personality":
                    self._personality = UserPersonalityInference(**{
                        k: v for k, v in data.items()
                        if k in UserPersonalityInference.__dataclass_fields__
                    })

                logger.debug(f"Loaded pattern: {ptype}")
            except Exception as e:
                logger.warning(f"Failed to load pattern {row['pattern_type']}: {e}")

        # Load accumulators
        acc_rows = self._db_execute(
            "SELECT key, value FROM accumulators", fetch=True
        )
        for row in (acc_rows or []):
            try:
                key = row["key"]
                value = json.loads(row["value"])
                if key == "total_app_time":
                    self._total_app_time = Counter(value)
                elif key == "total_category_time":
                    self._total_category_time = Counter(value)
                elif key == "total_transitions":
                    self._total_transitions = value
                elif key == "days_tracked":
                    self._days_tracked = value
                elif key == "analysis_count":
                    self._analysis_count = value
            except Exception:
                pass

        logger.info(f"Loaded {len(rows)} pattern types from database")

    def _save_accumulators(self):
        """Save long-term accumulators"""
        accumulators = {
            "total_app_time": dict(self._total_app_time.most_common(100)),
            "total_category_time": dict(self._total_category_time.most_common(50)),
            "total_transitions": self._total_transitions,
            "days_tracked": self._days_tracked,
            "analysis_count": self._analysis_count,
        }
        for key, value in accumulators.items():
            self._db_execute(
                """INSERT OR REPLACE INTO accumulators (key, value, updated_at)
                   VALUES (?, ?, ?)""",
                (key, json.dumps(value, default=str), datetime.now().isoformat())
            )

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        if self._running:
            return
        self._running = True

        self._analysis_thread = threading.Thread(
            target=self._analysis_loop,
            daemon=True,
            name="PatternAnalyzer-Analysis"
        )
        self._analysis_thread.start()

        logger.info("📊 PatternAnalyzer ACTIVE")

    def stop(self):
        if not self._running:
            return
        self._running = False

        # Final analysis & save
        try:
            self._run_all_analyses()
            self._save_all_patterns()
            self._save_accumulators()
        except Exception as e:
            logger.error(f"Error saving patterns on stop: {e}")

        if self._analysis_thread and self._analysis_thread.is_alive():
            self._analysis_thread.join(timeout=5.0)

        logger.info("PatternAnalyzer stopped")

    # ═══════════════════════════════════════════════════════════════════════════
    # DATA INGESTION
    # ═══════════════════════════════════════════════════════════════════════════

    def ingest_realtime_data(self, data: Dict[str, Any]):
        """
        Called by UserTracker with each activity snapshot.
        This is the primary data intake.
        """
        try:
            self._realtime_buffer.append(data)
            self._total_snapshots_processed += 1

            # Extract key fields
            timestamp = data.get("timestamp", datetime.now().isoformat())
            activity_level = data.get("activity_level", "idle")
            ts = datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else timestamp

            # Activity level tracking
            level_map = {"idle": 0, "low": 0.25, "moderate": 0.5, "active": 0.75, "intense": 1.0}
            level_val = level_map.get(activity_level, 0)
            self._activity_levels.append((ts, level_val))
            self._hourly_activities[ts.hour].append(level_val)

            # Window/app tracking
            window = data.get("active_window", {})
            if isinstance(window, dict):
                proc = window.get("process_name", "")
            else:
                proc = ""

            if proc and proc != "unknown":
                # Track app sequence for workflow analysis
                if (not self._window_sequence or
                        self._window_sequence[-1] != proc):
                    
                    # Record transition
                    if self._window_sequence:
                        prev = self._window_sequence[-1]
                        self._transition_counts[prev][proc] += 1
                        self._total_transitions += 1

                    self._window_sequence.append(proc)

                    # Focus session detection
                    self._track_focus_change(proc, ts)

                # Category tracking from snapshot data
                # (category should be in the data from UserTracker)

        except Exception as e:
            logger.debug(f"Ingest error: {e}")

    def ingest_snapshot(self, snapshot: Dict[str, Any]):
        """
        Called periodically by MonitoringSystem orchestrator.
        Same as ingest_realtime_data but from orchestrator.
        """
        self.ingest_realtime_data(snapshot)

    def _track_focus_change(self, new_app: str, timestamp: datetime):
        """Track when user switches apps for focus session detection"""
        if new_app == self._current_focus_app:
            return

        # Close previous focus session if it was long enough
        if (self._current_focus_start and self._current_focus_app and
                self._current_focus_app != "unknown"):
            duration = (timestamp - self._current_focus_start).total_seconds()
            
            self._app_session_durations[self._current_focus_app].append(duration)
            
            if duration >= self._focus_threshold_seconds:
                self._focus_sessions.append({
                    "app": self._current_focus_app,
                    "start": self._current_focus_start.isoformat(),
                    "end": timestamp.isoformat(),
                    "duration_minutes": round(duration / 60, 1),
                    "hour": self._current_focus_start.hour
                })

        # Start new focus tracking
        self._current_focus_app = new_app
        self._current_focus_start = timestamp

    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYSIS LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    def _analysis_loop(self):
        """Periodic analysis of accumulated data"""
        logger.info("Analysis loop started")

        # Wait for initial data
        time.sleep(60)

        while self._running:
            try:
                self._run_all_analyses()
                self._save_all_patterns()
                self._save_accumulators()

                self._analysis_count += 1
                self._last_analysis_time = datetime.now()

                logger.debug(
                    f"Analysis #{self._analysis_count} complete — "
                    f"{self._total_snapshots_processed} snapshots processed"
                )

                time.sleep(self._analysis_interval)

            except Exception as e:
                logger.error(f"Analysis loop error: {e}")
                time.sleep(30)

    def _run_all_analyses(self):
        """Run all analysis types"""
        self._analyze_temporal_patterns()
        self._analyze_app_usage()
        self._analyze_workflow()
        self._analyze_productivity()
        self._infer_personality()
        self._detect_anomalies()
        self._analyze_energy_curve()
        self._analyze_distraction_cascades()
        self._update_bayesian_confidences()

    def run_deep_analysis(self):
        """Deep analysis triggered by orchestrator (less frequent)"""
        logger.info("Running deep analysis...")
        self._run_all_analyses()

        # Additional deep tasks
        self._analyze_long_term_trends()
        self._generate_predictive_schedule()
        self._generate_weekly_comparison()
        self._save_daily_stats()

        self._save_all_patterns()
        self._save_accumulators()

        log_learning("Deep pattern analysis completed")

    def _save_all_patterns(self):
        """Save all current patterns to DB with Bayesian confidence"""
        self._save_pattern(
            "temporal", self._temporal.to_dict(),
            self._bayesian_confidences.get("temporal", 0.1)
        )
        self._save_pattern(
            "app_usage", self._app_usage.to_dict(),
            self._bayesian_confidences.get("app_usage", 0.1)
        )
        self._save_pattern(
            "workflow", self._workflow.to_dict(),
            self._bayesian_confidences.get("workflow", 0.1)
        )
        self._save_pattern(
            "productivity", self._productivity.to_dict(),
            self._bayesian_confidences.get("productivity", 0.1)
        )
        self._save_pattern(
            "personality", self._personality.to_dict(),
            self._bayesian_confidences.get("personality", 0.1)
        )
        self._save_pattern(
            "energy_curve", self._energy_curve.to_dict(),
            self._bayesian_confidences.get("energy_curve", 0.1)
        )
        self._save_pattern(
            "predictive_schedule", self._predictive_schedule.to_dict(),
            self._predictive_schedule.confidence
        )
        self._save_pattern(
            "weekly_comparison", self._weekly_comparison.to_dict(),
            self._bayesian_confidences.get("weekly_comparison", 0.1)
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # TEMPORAL ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════

    def _analyze_temporal_patterns(self):
        """Analyze when the user is active"""
        if not self._hourly_activities:
            return

        # Average activity by hour
        hourly_avg = {}
        for hour in range(24):
            values = self._hourly_activities.get(hour, [])
            hourly_avg[hour] = safe_mean(values)

        if not any(v > 0 for v in hourly_avg.values()):
            return

        # Most/least active hours
        sorted_hours = sorted(hourly_avg.items(), key=lambda x: -x[1])
        active_hours = [h for h, v in sorted_hours if v > 0.3]
        inactive_hours = [h for h, v in sorted_hours if v < 0.1]

        self._temporal.most_active_hours = active_hours[:6]
        self._temporal.least_active_hours = inactive_hours[:6]

        # Most active day segment
        segment_activity = defaultdict(list)
        for hour, avg in hourly_avg.items():
            segment = DaySegment.from_hour(hour)
            segment_activity[segment.value].append(avg)

        segment_avg = {
            seg: safe_mean(vals) for seg, vals in segment_activity.items()
        }
        if segment_avg:
            self._temporal.most_active_day_segment = max(
                segment_avg, key=segment_avg.get
            )

        # Night owl vs early bird
        late_activity = safe_mean(
            [hourly_avg.get(h, 0) for h in [22, 23, 0, 1, 2, 3]]
        )
        early_activity = safe_mean(
            [hourly_avg.get(h, 0) for h in [5, 6, 7, 8]]
        )

        self._temporal.is_night_owl = late_activity > 0.3 and late_activity > early_activity
        self._temporal.is_early_bird = early_activity > 0.3 and early_activity > late_activity

        # Session start/end estimation
        if active_hours:
            self._temporal.avg_session_start = float(min(active_hours))
            self._temporal.avg_session_end = float(max(active_hours))
            span = self._temporal.avg_session_end - self._temporal.avg_session_start
            self._temporal.typical_session_duration_hours = max(1.0, span)

        # Consistency score (low stdev across same hours = consistent)
        stdevs = []
        for hour in range(24):
            values = self._hourly_activities.get(hour, [])
            if len(values) >= 3:
                stdevs.append(safe_stdev(values))
        if stdevs:
            avg_stdev = safe_mean(stdevs)
            self._temporal.consistency_score = max(0.0, 1.0 - avg_stdev * 2)

    # ═══════════════════════════════════════════════════════════════════════════
    # APP USAGE ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════

    def _analyze_app_usage(self):
        """Analyze which apps the user uses most"""
        # Count app occurrences in recent data
        app_counter = Counter()
        cat_counter = Counter()

        for data in self._realtime_buffer:
            window = data.get("active_window", {})
            if isinstance(window, dict):
                proc = window.get("process_name", "")
                if proc and proc != "unknown":
                    app_counter[proc] += 1

                    # Categorize
                    from monitoring.user_tracker import AppCategorizer
                    title = window.get("title", "")
                    cat = AppCategorizer.categorize(proc, title)
                    cat_counter[cat] += 1

        if not app_counter:
            return

        # Update long-term accumulators
        self._total_app_time.update(app_counter)
        self._total_category_time.update(cat_counter)

        # Top apps (normalized)
        self._app_usage.top_apps = normalize_counter(self._total_app_time, 20)
        self._app_usage.top_categories = normalize_counter(self._total_category_time, 15)

        # App diversity
        total_apps_used = len(self._total_app_time)
        self._app_usage.app_diversity_score = min(1.0, total_apps_used / 30.0)

        # Dominant category
        if self._app_usage.top_categories:
            top_cat = max(self._app_usage.top_categories,
                         key=self._app_usage.top_categories.get)
            self._app_usage.browser_dominant = top_cat == "browser"
            self._app_usage.code_dominant = top_cat in ("code_editor", "terminal")

            # Infer primary workflow
            category_map = {
                "code_editor": "developer",
                "terminal": "developer",
                "browser": "web_based",
                "design": "creative",
                "communication": "communicator",
                "productivity": "knowledge_worker",
                "media": "content_consumer",
                "gaming": "gamer"
            }
            self._app_usage.primary_workflow = category_map.get(top_cat, "general")

        # Average app session duration
        all_durations = []
        for durations in self._app_session_durations.values():
            all_durations.extend(durations)
        if all_durations:
            self._app_usage.avg_app_session_minutes = safe_mean(all_durations) / 60.0

        # App loyalty (how consistently they use the same apps)
        if self._total_app_time:
            total = sum(self._total_app_time.values())
            loyalty = {}
            for app, count in self._total_app_time.most_common(10):
                loyalty[app] = round(count / total, 3)
            self._app_usage.app_loyalty = loyalty

    # ═══════════════════════════════════════════════════════════════════════════
    # WORKFLOW ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════

    def _analyze_workflow(self):
        """Analyze app transition patterns"""
        if not self._transition_counts:
            return

        # Build transition matrix (normalized)
        matrix = {}
        for from_app, targets in self._transition_counts.items():
            total = sum(targets.values())
            if total > 0:
                matrix[from_app] = {
                    to_app: round(count / total, 3)
                    for to_app, count in sorted(
                        targets.items(), key=lambda x: -x[1]
                    )[:10]
                }

        self._workflow.transition_matrix = matrix

        # Common app pairs (bidirectional)
        pair_counts = Counter()
        for from_app, targets in self._transition_counts.items():
            for to_app, count in targets.items():
                pair = tuple(sorted([from_app, to_app]))
                pair_counts[pair] += count

        self._workflow.common_app_pairs = [
            list(pair) for pair, _ in pair_counts.most_common(10)
        ]

        # Average switches per hour
        if self._activity_levels:
            hours_tracked = max(1, len(self._activity_levels) * 30 / 3600)
            self._workflow.avg_switches_per_hour = round(
                self._total_transitions / hours_tracked, 1
            )

        # Multitasking score
        switches_per_hour = self._workflow.avg_switches_per_hour
        self._workflow.multitasking_score = min(1.0, switches_per_hour / 30.0)

        # Detect common sequences (length 3)
        self._detect_sequences()

        # Detect task clusters (apps used within same time window)
        self._detect_task_clusters()

    def _detect_sequences(self):
        """Find frequently occurring app sequences of length 3"""
        if len(self._window_sequence) < 10:
            return

        seq_list = list(self._window_sequence)
        trigram_counts = Counter()

        for i in range(len(seq_list) - 2):
            # Only count if all three are different
            a, b, c = seq_list[i], seq_list[i+1], seq_list[i+2]
            if a != b and b != c:
                trigram_counts[(a, b, c)] += 1

        common = trigram_counts.most_common(5)
        self._workflow.common_sequences = [
            list(seq) for seq, count in common if count >= 3
        ]

    def _detect_task_clusters(self):
        """Detect apps that tend to be used in the same time window"""
        # Use a sliding window of 10 minutes over recent data
        if len(self._realtime_buffer) < 20:
            return

        window_size = 20  # ~10 min at 30s intervals
        co_occurrence = Counter()

        buffer_list = list(self._realtime_buffer)
        for i in range(0, len(buffer_list) - window_size, window_size // 2):
            window = buffer_list[i:i + window_size]
            apps_in_window = set()
            for data in window:
                w = data.get("active_window", {})
                if isinstance(w, dict):
                    proc = w.get("process_name", "")
                    if proc and proc != "unknown":
                        apps_in_window.add(proc)

            # Record co-occurrences
            apps = sorted(apps_in_window)
            for j in range(len(apps)):
                for k in range(j + 1, len(apps)):
                    co_occurrence[(apps[j], apps[k])] += 1

        # Find strong clusters
        strong_pairs = [
            pair for pair, count in co_occurrence.most_common(20)
            if count >= 3
        ]

        # Group into clusters using simple union-find
        if strong_pairs:
            clusters = self._cluster_from_pairs(strong_pairs)
            self._workflow.task_clusters = clusters[:5]

    def _cluster_from_pairs(
        self, pairs: List[Tuple[str, str]]
    ) -> List[List[str]]:
        """Simple union-find clustering from pairs"""
        parent = {}

        def find(x):
            if x not in parent:
                parent[x] = x
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for a, b in pairs:
            union(a, b)

        groups = defaultdict(set)
        for item in parent:
            groups[find(item)].add(item)

        return [sorted(group) for group in groups.values() if len(group) >= 2]

    # ═══════════════════════════════════════════════════════════════════════════
    # PRODUCTIVITY ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════

    def _analyze_productivity(self):
        """Analyze focus and productivity patterns"""
        if not self._focus_sessions:
            return

        # Focus session statistics
        focus_durations = [s["duration_minutes"] for s in self._focus_sessions]
        self._productivity.avg_focus_duration_minutes = round(
            safe_mean(focus_durations), 1
        )
        self._productivity.max_focus_duration_minutes = round(
            max(focus_durations) if focus_durations else 0, 1
        )

        # Focus apps (apps with longest focus sessions)
        focus_app_durations = defaultdict(list)
        for sess in self._focus_sessions:
            focus_app_durations[sess["app"]].append(sess["duration_minutes"])

        focus_apps_sorted = sorted(
            focus_app_durations.items(),
            key=lambda x: safe_mean(x[1]),
            reverse=True
        )
        self._productivity.focus_apps = [app for app, _ in focus_apps_sorted[:5]]

        # Distraction apps (opposite — frequent short switches)
        distraction_apps = []
        for app, durations in self._app_session_durations.items():
            if len(durations) >= 5:
                avg_dur = safe_mean(durations)
                if avg_dur < 30:  # Less than 30 seconds average
                    distraction_apps.append(app)
        self._productivity.distraction_apps = distraction_apps[:5]

        # Productive hours (hours with most focus sessions)
        focus_hours = Counter()
        for sess in self._focus_sessions:
            focus_hours[sess.get("hour", 12)] += 1
        self._productivity.productive_hours = [
            h for h, _ in focus_hours.most_common(4)
        ]

        # Distraction frequency
        if self._activity_levels:
            hours = max(1, len(self._activity_levels) * 30 / 3600)
            short_switches = sum(
                1 for durations in self._app_session_durations.values()
                for d in durations if d < 15
            )
            self._productivity.distraction_frequency_per_hour = round(
                short_switches / hours, 1
            )

        # Overall productivity score
        focus_ratio = (
            self._productivity.avg_focus_duration_minutes / 30.0
        )  # 30 min = perfect
        distraction_penalty = min(
            0.5, self._productivity.distraction_frequency_per_hour / 20.0
        )
        self._productivity.daily_productivity_score = round(
            max(0.0, min(1.0, focus_ratio - distraction_penalty)), 2
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSONALITY INFERENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _infer_personality(self):
        """Infer user personality traits from behavioral data"""
        p = self._personality

        # ──── Openness: App diversity + category diversity ────
        p.openness = min(1.0, self._app_usage.app_diversity_score * 1.5)

        # ──── Conscientiousness: Schedule consistency + focus ────
        consistency = self._temporal.consistency_score
        productivity = self._productivity.daily_productivity_score
        p.conscientiousness = round((consistency + productivity) / 2, 2)

        # ──── Extraversion: Communication app usage ────
        comm_fraction = self._app_usage.top_categories.get("communication", 0)
        social_fraction = self._app_usage.top_categories.get("social_media", 0)
        p.extraversion = min(1.0, (comm_fraction + social_fraction) * 3)

        # ──── Neuroticism: Erratic patterns, high switching ────
        switching = min(1.0, self._workflow.multitasking_score)
        inconsistency = 1.0 - self._temporal.consistency_score
        p.neuroticism = round((switching * 0.4 + inconsistency * 0.6), 2)

        # ──── Behavioral Flags ────
        top_cats = self._app_usage.top_categories

        p.is_developer = (
            top_cats.get("code_editor", 0) + top_cats.get("terminal", 0) > 0.2
        )
        p.is_creative = top_cats.get("design", 0) > 0.1
        p.is_gamer = top_cats.get("gaming", 0) > 0.1
        p.is_social = p.extraversion > 0.5
        p.is_researcher = (
            top_cats.get("browser", 0) > 0.3 and
            top_cats.get("documentation", 0) > 0.05
        )
        p.is_organized = p.conscientiousness > 0.6
        p.is_multitasker = self._workflow.multitasking_score > 0.5

        # ──── Work Style ────
        if p.is_developer:
            p.work_style = "developer"
        elif p.is_creative:
            p.work_style = "creative"
        elif self._productivity.avg_focus_duration_minutes > 20:
            p.work_style = "deep_worker"
        elif p.is_multitasker:
            p.work_style = "multitasker"
        else:
            p.work_style = "general"

        # ──── Tech Proficiency ────
        uses_terminal = top_cats.get("terminal", 0) > 0.05
        uses_code = top_cats.get("code_editor", 0) > 0.1
        uses_db = top_cats.get("database", 0) > 0.01
        tech_signals = sum([uses_terminal, uses_code, uses_db])
        p.tech_proficiency = min(1.0, tech_signals * 0.3 + 0.2)

        # ──── Communication Preference ────
        if p.is_social and p.extraversion > 0.6:
            p.communication_preference = "verbose"
        elif p.conscientiousness > 0.7 and not p.is_social:
            p.communication_preference = "brief"
        else:
            p.communication_preference = "balanced"

        # ──── Confidence ────
        data_points = self._total_snapshots_processed
        p.confidence = min(0.95, data_points / 5000.0 + 0.05)

    # ═══════════════════════════════════════════════════════════════════════════
    # ANOMALY DETECTION
    # ═══════════════════════════════════════════════════════════════════════════

    def _detect_anomalies(self):
        """Detect unusual behavior deviations using threshold, z-score, and IQR methods"""
        new_anomalies = []
        now = datetime.now()

        # 1. Unusual hour activity (threshold + z-score)
        current_hour = now.hour
        hour_history = self._hourly_activities.get(current_hour, [])
        expected = safe_mean(hour_history)
        recent_activity = []
        for ts, level in self._activity_levels:
            if (now - ts).total_seconds() < 600:  # last 10 min
                recent_activity.append(level)
        
        if recent_activity and len(hour_history) >= 5:
            actual = safe_mean(recent_activity)

            # Threshold method (original)
            if abs(actual - expected) > 0.4:
                new_anomalies.append(DetectedAnomaly(
                    anomaly_type="unusual_hour_activity",
                    description=(
                        f"Activity at hour {current_hour} is "
                        f"{'higher' if actual > expected else 'lower'} than usual"
                    ),
                    severity=min(1.0, abs(actual - expected)),
                    timestamp=now.isoformat(),
                    baseline=f"expected={expected:.2f}",
                    observed=f"actual={actual:.2f}",
                    detection_method="threshold"
                ))

            # Z-score method (more statistically robust)
            z = z_score(actual, hour_history)
            if abs(z) > 2.0 and len(hour_history) >= 10:
                new_anomalies.append(DetectedAnomaly(
                    anomaly_type="zscore_hour_anomaly",
                    description=(
                        f"Activity at hour {current_hour} is {abs(z):.1f} "
                        f"standard deviations {'above' if z > 0 else 'below'} normal"
                    ),
                    severity=min(1.0, abs(z) / 3.0),
                    timestamp=now.isoformat(),
                    baseline=f"mean={expected:.2f}, stdev={safe_stdev(hour_history):.2f}",
                    observed=f"actual={actual:.2f}, z={z:.2f}",
                    detection_method="z_score"
                ))

        # 2. Unusual app (app not in top 20)
        if self._window_sequence and self._total_app_time:
            recent_app = self._window_sequence[-1] if self._window_sequence else ""
            top_apps = set(
                app for app, _ in self._total_app_time.most_common(20)
            )
            if (recent_app and recent_app not in top_apps and
                    recent_app != "unknown" and
                    self._total_snapshots_processed > 100):
                new_anomalies.append(DetectedAnomaly(
                    anomaly_type="unusual_app",
                    description=f"User is using an uncommon app: {recent_app}",
                    severity=0.3,
                    timestamp=now.isoformat(),
                    baseline=f"top_apps={list(top_apps)[:5]}",
                    observed=f"current={recent_app}",
                    detection_method="threshold"
                ))

        # 3. Unusually high switching rate (threshold + IQR)
        if len(self._window_sequence) >= 20:
            recent_switches = len(set(
                list(self._window_sequence)[-20:]
            ))

            # Threshold method
            if recent_switches > 15:
                new_anomalies.append(DetectedAnomaly(
                    anomaly_type="high_switching",
                    description="User is switching between apps very rapidly",
                    severity=0.5,
                    timestamp=now.isoformat(),
                    baseline="normal_diversity≈5-10",
                    observed=f"recent_unique_apps={recent_switches}",
                    detection_method="threshold"
                ))

            # IQR method for switching rate
            if self._workflow.avg_switches_per_hour > 0 and self._analysis_count >= 3:
                switch_values = [self._workflow.avg_switches_per_hour]
                # Build a mini-history from focus sessions
                for s in self._focus_sessions[-50:]:
                    dur_h = s.get("duration_minutes", 0) / 60.0
                    if dur_h > 0:
                        switch_values.append(1.0 / dur_h)
                
                if len(switch_values) >= 4:
                    lower, upper = iqr_outliers(switch_values)
                    current_rate = recent_switches  # approximation
                    if current_rate > upper:
                        new_anomalies.append(DetectedAnomaly(
                            anomaly_type="iqr_switching_outlier",
                            description=(
                                f"App switching rate ({current_rate}) exceeds "
                                f"IQR upper bound ({upper:.1f})"
                            ),
                            severity=min(1.0, (current_rate - upper) / 10.0),
                            timestamp=now.isoformat(),
                            baseline=f"IQR_bounds=[{lower:.1f}, {upper:.1f}]",
                            observed=f"rate={current_rate}",
                            detection_method="iqr"
                        ))

        # 4. Focus session duration anomaly (z-score)
        if len(self._focus_sessions) >= 10:
            durations = [s["duration_minutes"] for s in self._focus_sessions]
            if self._focus_sessions:
                latest_dur = self._focus_sessions[-1]["duration_minutes"]
                z = z_score(latest_dur, durations)
                if abs(z) > 2.5:
                    new_anomalies.append(DetectedAnomaly(
                        anomaly_type="focus_duration_anomaly",
                        description=(
                            f"Focus session of {latest_dur:.0f} min is "
                            f"{'unusually long' if z > 0 else 'unusually short'}"
                        ),
                        severity=min(1.0, abs(z) / 3.5),
                        timestamp=now.isoformat(),
                        baseline=f"mean={safe_mean(durations):.1f}min, stdev={safe_stdev(durations):.1f}",
                        observed=f"duration={latest_dur:.1f}min, z={z:.2f}",
                        detection_method="z_score"
                    ))

        # 5. Activity level IQR anomaly (detect sustained unusual intensity)
        if len(self._activity_levels) >= 30:
            recent_30 = [level for _, level in list(self._activity_levels)[-30:]]
            all_levels = [level for _, level in self._activity_levels]
            if len(all_levels) >= 50:
                lower, upper = iqr_outliers(all_levels)
                recent_avg = safe_mean(recent_30)
                if recent_avg > upper or recent_avg < lower:
                    new_anomalies.append(DetectedAnomaly(
                        anomaly_type="sustained_intensity_anomaly",
                        description=(
                            f"Sustained {'high' if recent_avg > upper else 'low'} "
                            f"activity intensity ({recent_avg:.2f})"
                        ),
                        severity=min(1.0, abs(recent_avg - safe_mean(all_levels)) * 2),
                        timestamp=now.isoformat(),
                        baseline=f"IQR_bounds=[{lower:.2f}, {upper:.2f}]",
                        observed=f"recent_avg={recent_avg:.2f}",
                        detection_method="iqr"
                    ))

        # Store new anomalies
        for anomaly in new_anomalies:
            self._anomalies.append(anomaly)
            self._db_execute(
                """INSERT INTO anomalies 
                   (anomaly_type, description, severity, timestamp, baseline, observed)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (anomaly.anomaly_type, anomaly.description, anomaly.severity,
                 anomaly.timestamp, anomaly.baseline, anomaly.observed)
            )

        # Keep only recent anomalies in memory
        if len(self._anomalies) > 50:
            self._anomalies = self._anomalies[-30:]

    # ═══════════════════════════════════════════════════════════════════════════
    # LONG-TERM TRENDS
    # ═══════════════════════════════════════════════════════════════════════════

    def _analyze_long_term_trends(self):
        """Analyze trends over days/weeks"""
        # Check focus trend
        if len(self._focus_sessions) >= 10:
            recent = self._focus_sessions[-10:]
            older = self._focus_sessions[-20:-10] if len(self._focus_sessions) >= 20 else []

            if older:
                recent_avg = safe_mean([s["duration_minutes"] for s in recent])
                older_avg = safe_mean([s["duration_minutes"] for s in older])

                if recent_avg > older_avg * 1.1:
                    self._productivity.focus_trend = "improving"
                elif recent_avg < older_avg * 0.9:
                    self._productivity.focus_trend = "declining"
                else:
                    self._productivity.focus_trend = "stable"

    def _save_daily_stats(self):
        """Save daily summary to database"""
        today = datetime.now().strftime("%Y-%m-%d")

        try:
            self._db_execute(
                """INSERT OR REPLACE INTO daily_stats
                   (date, total_active_seconds, total_idle_seconds, app_switches,
                    top_apps, top_categories, avg_activity, productivity_score,
                    focus_sessions, avg_focus_minutes, personality_snapshot)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    today,
                    sum(1 for _, l in self._activity_levels if l > 0.2) * 30,
                    sum(1 for _, l in self._activity_levels if l <= 0.2) * 30,
                    self._total_transitions,
                    json.dumps(dict(self._total_app_time.most_common(10))),
                    json.dumps(dict(self._total_category_time.most_common(10))),
                    safe_mean([l for _, l in self._activity_levels]),
                    self._productivity.daily_productivity_score,
                    len(self._focus_sessions),
                    self._productivity.avg_focus_duration_minutes,
                    json.dumps(self._personality.to_dict())
                )
            )
        except Exception as e:
            logger.error(f"Failed to save daily stats: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # ENERGY CURVE ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════

    def _analyze_energy_curve(self):
        """
        Analyze how the user's activity level evolves over a session.
        Produces a normalized 10-bucket curve showing ramp-up, peak, and wind-down.
        """
        if len(self._activity_levels) < 20:
            return

        levels = [level for _, level in self._activity_levels]
        n = len(levels)
        bucket_size = max(1, n // 10)

        # Build 10-bucket normalized curve
        curve = []
        for i in range(10):
            start = i * bucket_size
            end = min(start + bucket_size, n)
            bucket = levels[start:end]
            curve.append(round(safe_mean(bucket), 3) if bucket else 0.0)

        self._energy_curve.normalized_curve = curve

        # Find peak
        if curve:
            peak_idx = curve.index(max(curve))
            self._energy_curve.peak_level = max(curve)

            # Map bucket index to approximate hour
            if self._activity_levels:
                first_ts = self._activity_levels[0][0]
                last_ts = self._activity_levels[-1][0]
                total_span = (last_ts - first_ts).total_seconds()
                peak_offset = (peak_idx / 10.0) * total_span
                peak_time = first_ts + timedelta(seconds=peak_offset)
                self._energy_curve.peak_hour = peak_time.hour

            # Ramp-up: buckets before peak
            ramp_buckets = peak_idx
            self._energy_curve.ramp_up_minutes = round(
                (ramp_buckets / 10.0) * (total_span / 60.0), 1
            ) if total_span > 0 else 0.0

            # Wind-down: buckets after peak
            wind_buckets = 9 - peak_idx
            self._energy_curve.wind_down_minutes = round(
                (wind_buckets / 10.0) * (total_span / 60.0), 1
            ) if total_span > 0 else 0.0

            # Curve shape classification
            first_third = safe_mean(curve[:3])
            mid_third = safe_mean(curve[3:7])
            last_third = safe_mean(curve[7:])

            if mid_third > first_third * 1.3 and mid_third > last_third * 1.3:
                self._energy_curve.curve_shape = "peak_valley"
            elif first_third < mid_third < last_third:
                self._energy_curve.curve_shape = "ramp_up"
            elif first_third > mid_third > last_third:
                self._energy_curve.curve_shape = "wind_down"
            elif abs(first_third - last_third) < 0.15:
                self._energy_curve.curve_shape = "steady"
            else:
                self._energy_curve.curve_shape = "variable"

    # ═══════════════════════════════════════════════════════════════════════════
    # DISTRACTION CASCADE DETECTION
    # ═══════════════════════════════════════════════════════════════════════════

    def _analyze_distraction_cascades(self):
        """
        Detect when opening a distraction app triggers rapid context switching.
        A cascade = distraction app followed by 4+ switches within 5 minutes.
        """
        if len(self._window_sequence) < 10:
            return

        sequence = list(self._window_sequence)[-50:]  # last 50 switches
        new_cascades = []

        for i, app in enumerate(sequence):
            app_lower = app.lower()
            is_distraction = any(
                d in app_lower for d in self._distraction_apps
            )

            if is_distraction:
                # Count rapid switches after this distraction app
                cascade_apps = []
                for j in range(i + 1, min(i + 10, len(sequence))):
                    cascade_apps.append(sequence[j])

                # A cascade is 4+ unique apps after a distraction trigger
                if len(set(cascade_apps)) >= 4:
                    cascade = DistractionCascade(
                        trigger_app=app,
                        cascade_length=len(cascade_apps),
                        apps_visited=cascade_apps[:8],
                        timestamp=datetime.now().isoformat()
                    )
                    new_cascades.append(cascade)

        # Deduplicate (only keep new ones)
        existing_triggers = set(
            c.trigger_app for c in self._distraction_cascades[-10:]
        )
        for cascade in new_cascades:
            if cascade.trigger_app not in existing_triggers:
                self._distraction_cascades.append(cascade)
                existing_triggers.add(cascade.trigger_app)

                # Fire event
                publish(
                    EventType.MONITORING_ANOMALY,
                    {
                        "type": "distraction_cascade",
                        "trigger": cascade.trigger_app,
                        "cascade_length": cascade.cascade_length
                    },
                    source="pattern_analyzer"
                )

        # Trim
        if len(self._distraction_cascades) > 30:
            self._distraction_cascades = self._distraction_cascades[-20:]

    # ═══════════════════════════════════════════════════════════════════════════
    # BAYESIAN CONFIDENCE SCORING
    # ═══════════════════════════════════════════════════════════════════════════

    def _update_bayesian_confidences(self):
        """Update confidence scores for each pattern type using Bayesian method"""
        data_points = self._total_snapshots_processed

        # Temporal: needs consistent hourly data
        temporal_consistency = self._temporal.consistency_score
        self._bayesian_confidences["temporal"] = bayesian_confidence(
            data_points, temporal_consistency, min_points=100
        )

        # App usage: consistency = how stable the top apps are
        app_consistency = 0.5
        if self._app_usage.top_apps:
            # If top 3 apps account for > 60% of time, higher consistency
            top_3_share = sum(
                list(self._app_usage.top_apps.values())[:3]
            )
            app_consistency = min(1.0, top_3_share * 1.5)
        self._bayesian_confidences["app_usage"] = bayesian_confidence(
            data_points, app_consistency, min_points=50
        )

        # Workflow: needs enough transitions
        workflow_consistency = min(
            1.0, self._total_transitions / 500.0
        )
        self._bayesian_confidences["workflow"] = bayesian_confidence(
            self._total_transitions, workflow_consistency, min_points=100
        )

        # Productivity: based on focus session consistency
        focus_consistency = 0.5
        if len(self._focus_sessions) >= 5:
            durations = [s["duration_minutes"] for s in self._focus_sessions[-20:]]
            cv = safe_stdev(durations) / safe_mean(durations) if safe_mean(durations) > 0 else 1.0
            focus_consistency = max(0.0, 1.0 - cv)  # lower CV = higher consistency
        self._bayesian_confidences["productivity"] = bayesian_confidence(
            data_points, focus_consistency, min_points=200
        )

        # Personality: needs lots of data
        self._bayesian_confidences["personality"] = bayesian_confidence(
            data_points, 0.3, min_points=500, max_points=10000
        )

        # Energy curve
        self._bayesian_confidences["energy_curve"] = bayesian_confidence(
            len(self._activity_levels), 0.5, min_points=100
        )

        # Weekly comparison
        self._bayesian_confidences["weekly_comparison"] = bayesian_confidence(
            self._days_tracked * 100, 0.5, min_points=700  # ~1 week
        )

        # Update personality confidence to match Bayesian
        self._personality.confidence = self._bayesian_confidences.get(
            "personality", self._personality.confidence
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # PREDICTIVE SCHEDULING
    # ═══════════════════════════════════════════════════════════════════════════

    def _generate_predictive_schedule(self):
        """
        Predict tomorrow's likely active hours and peak productivity windows
        based on historical hourly patterns and day-of-week patterns.
        """
        if not self._hourly_activities or self._analysis_count < 3:
            return

        ps = self._predictive_schedule

        # Predict active hours from hourly history
        hourly_avg = {}
        for hour in range(24):
            values = self._hourly_activities.get(hour, [])
            hourly_avg[hour] = safe_mean(values)

        # Predicted start: first hour with avg > 0.2
        for h in range(24):
            if hourly_avg.get(h, 0) > 0.2:
                ps.predicted_start_hour = float(h)
                break

        # Predicted end: last hour with avg > 0.2
        for h in range(23, -1, -1):
            if hourly_avg.get(h, 0) > 0.2:
                ps.predicted_end_hour = float(h)
                break

        # Predicted peak hours (top 3)
        sorted_hours = sorted(
            hourly_avg.items(), key=lambda x: -x[1]
        )
        ps.predicted_peak_hours = [h for h, v in sorted_hours[:3] if v > 0.3]

        # Predicted active minutes
        active_hours = sum(1 for h, v in hourly_avg.items() if v > 0.2)
        ps.predicted_active_minutes = active_hours * 60 * 0.6  # ~60% efficiency

        # Predicted top app
        if self._app_usage.top_apps:
            ps.predicted_top_app = list(self._app_usage.top_apps.keys())[0]

        # Confidence based on data volume and consistency
        ps.confidence = self._bayesian_confidences.get("temporal", 0.1)

    # ═══════════════════════════════════════════════════════════════════════════
    # WEEKLY COMPARISON
    # ═══════════════════════════════════════════════════════════════════════════

    def _generate_weekly_comparison(self):
        """
        Generate this-week vs last-week productivity deltas.
        """
        try:
            rows = self._db_execute(
                """SELECT date, total_active_seconds, avg_focus_minutes,
                          app_switches
                   FROM daily_stats
                   ORDER BY date DESC LIMIT 14""",
                fetch=True
            )

            if not rows or len(rows) < 7:
                return

            wc = self._weekly_comparison

            this_week = rows[:7]
            last_week = rows[7:14] if len(rows) >= 14 else []

            # This week totals
            wc.this_week_active_minutes = sum(
                (r["total_active_seconds"] or 0) / 60.0 for r in this_week
            )
            focus_vals = [
                r["avg_focus_minutes"] or 0 for r in this_week
            ]
            wc.this_week_focus_avg = safe_mean(focus_vals)
            wc.this_week_switches = sum(
                r["app_switches"] or 0 for r in this_week
            )

            if last_week:
                wc.last_week_active_minutes = sum(
                    (r["total_active_seconds"] or 0) / 60.0
                    for r in last_week
                )
                last_focus = [
                    r["avg_focus_minutes"] or 0 for r in last_week
                ]
                wc.last_week_focus_avg = safe_mean(last_focus)
                wc.last_week_switches = sum(
                    r["app_switches"] or 0 for r in last_week
                )

                # Deltas
                if wc.last_week_active_minutes > 0:
                    wc.delta_percent = round(
                        ((wc.this_week_active_minutes -
                          wc.last_week_active_minutes) /
                         wc.last_week_active_minutes) * 100, 1
                    )
                if wc.last_week_focus_avg > 0:
                    wc.focus_delta_percent = round(
                        ((wc.this_week_focus_avg -
                          wc.last_week_focus_avg) /
                         wc.last_week_focus_avg) * 100, 1
                    )

                # Overall trend
                if wc.focus_delta_percent > 10:
                    wc.productivity_trend = "improving"
                elif wc.focus_delta_percent < -10:
                    wc.productivity_trend = "declining"
                else:
                    wc.productivity_trend = "stable"

        except Exception as e:
            logger.error(f"Weekly comparison error: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def get_current_patterns(self) -> Dict[str, Any]:
        """Get all current patterns as a dictionary"""
        return {
            "temporal": self._temporal.to_dict(),
            "app_usage": self._app_usage.to_dict(),
            "workflow": self._workflow.to_dict(),
            "productivity": self._productivity.to_dict(),
            "anomalies": [a.to_dict() for a in self._anomalies[-10:]],
            "energy_curve": self._energy_curve.to_dict(),
            "predictive_schedule": self._predictive_schedule.to_dict(),
            "weekly_comparison": self._weekly_comparison.to_dict(),
            "distraction_cascades": [
                c.to_dict() for c in self._distraction_cascades[-5:]
            ],
            "confidences": dict(self._bayesian_confidences),
            "last_analysis": (
                self._last_analysis_time.isoformat()
                if self._last_analysis_time else None
            ),
            "analysis_count": self._analysis_count,
            "data_points": self._total_snapshots_processed
        }

    def get_user_profile(self) -> Dict[str, Any]:
        """Get the inferred user personality profile"""
        return {
            "personality": self._personality.to_dict(),
            "work_style": self._app_usage.primary_workflow,
            "schedule": {
                "is_night_owl": self._temporal.is_night_owl,
                "is_early_bird": self._temporal.is_early_bird,
                "most_active_segment": self._temporal.most_active_day_segment,
                "typical_hours": (
                    f"{self._temporal.avg_session_start:.0f}:00 - "
                    f"{self._temporal.avg_session_end:.0f}:00"
                ),
                "consistency": self._temporal.consistency_score
            },
            "productivity": {
                "score": self._productivity.daily_productivity_score,
                "avg_focus_minutes": self._productivity.avg_focus_duration_minutes,
                "trend": self._productivity.focus_trend,
                "best_hours": self._productivity.productive_hours
            },
            "top_activities": self._app_usage.top_categories,
            "confidence": self._personality.confidence
        }

    def get_temporal_summary(self) -> str:
        """Get human-readable temporal summary"""
        t = self._temporal
        if not t.most_active_hours:
            return "Not enough data yet to determine temporal patterns."

        parts = []
        if t.is_night_owl:
            parts.append("The user is a night owl")
        elif t.is_early_bird:
            parts.append("The user is an early bird")

        parts.append(
            f"Most active during {t.most_active_day_segment} hours"
        )
        parts.append(
            f"Typical session: {t.avg_session_start:.0f}:00 to "
            f"{t.avg_session_end:.0f}:00"
        )
        parts.append(
            f"Schedule consistency: {t.consistency_score:.0%}"
        )

        return ". ".join(parts) + "."

    def get_personality_summary(self) -> str:
        """Get human-readable personality summary"""
        p = self._personality
        if p.confidence < 0.1:
            return "Need more data to infer personality."

        traits = []
        if p.is_developer:
            traits.append("developer")
        if p.is_creative:
            traits.append("creative")
        if p.is_researcher:
            traits.append("researcher")
        if p.is_gamer:
            traits.append("gamer")
        if p.is_multitasker:
            traits.append("multitasker")
        if p.is_organized:
            traits.append("organized")
        if p.is_social:
            traits.append("social")

        type_str = ", ".join(traits) if traits else "general user"

        return (
            f"User type: {type_str}. "
            f"Work style: {p.work_style}. "
            f"Tech proficiency: {p.tech_proficiency:.0%}. "
            f"Communication preference: {p.communication_preference}. "
            f"Confidence: {p.confidence:.0%}."
        )

    def get_context_for_brain(self) -> str:
        """
        Get a concise context string for the NexusBrain prompt.
        This is what gets injected into the system prompt.
        """
        parts = []

        # Temporal
        if self._temporal.most_active_hours:
            parts.append(f"User schedule: {self.get_temporal_summary()}")

        # Personality
        if self._personality.confidence > 0.1:
            parts.append(f"User personality: {self.get_personality_summary()}")

        # Current productivity
        if self._productivity.daily_productivity_score > 0:
            parts.append(
                f"Current productivity: {self._productivity.daily_productivity_score:.0%} "
                f"(focus trend: {self._productivity.focus_trend})"
            )

        # Workflow
        if self._app_usage.primary_workflow != "general":
            parts.append(
                f"Primary workflow: {self._app_usage.primary_workflow}"
            )

        # Anomalies
        recent_anomalies = [
            a for a in self._anomalies
            if a.severity > 0.3
        ][-3:]
        if recent_anomalies:
            anomaly_strs = [a.description for a in recent_anomalies]
            parts.append(f"Notable behaviors: {'; '.join(anomaly_strs)}")

        return "\n".join(parts) if parts else ""

    def get_stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "total_snapshots_processed": self._total_snapshots_processed,
            "total_transitions_tracked": self._total_transitions,
            "analysis_count": self._analysis_count,
            "last_analysis": (
                self._last_analysis_time.isoformat()
                if self._last_analysis_time else None
            ),
            "patterns_detected": {
                "temporal": bool(self._temporal.most_active_hours),
                "app_usage": bool(self._app_usage.top_apps),
                "workflow": bool(self._workflow.transition_matrix),
                "productivity": self._productivity.daily_productivity_score > 0,
                "personality": self._personality.confidence > 0.1,
                "energy_curve": bool(self._energy_curve.normalized_curve),
                "predictive_schedule": self._predictive_schedule.confidence > 0.1,
                "distraction_cascades": len(self._distraction_cascades) > 0,
            },
            "confidences": dict(self._bayesian_confidences),
            "focus_sessions_detected": len(self._focus_sessions),
            "anomalies_detected": len(self._anomalies),
            "distraction_cascades_detected": len(self._distraction_cascades),
            "energy_curve_shape": self._energy_curve.curve_shape,
            "personality_confidence": self._personality.confidence,
            "buffer_size": len(self._realtime_buffer),
            "unique_apps_seen": len(self._total_app_time)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

pattern_analyzer = PatternAnalyzer()

if __name__ == "__main__":
    analyzer = PatternAnalyzer()
    analyzer.start()

    # Simulate data
    import random
    print("Simulating data ingestion...")
    for i in range(100):
        analyzer.ingest_realtime_data({
            "timestamp": datetime.now().isoformat(),
            "activity_level": random.choice(["idle", "low", "moderate", "active", "intense"]),
            "active_window": {
                "title": f"Test Window {i}",
                "process_name": random.choice([
                    "code", "chrome", "terminal", "discord", "explorer"
                ]),
                "pid": 1000 + i
            }
        })
        time.sleep(0.05)

    time.sleep(5)
    print(json.dumps(analyzer.get_current_patterns(), indent=2, default=str))
    print(f"\nProfile: {analyzer.get_personality_summary()}")
    print(f"Temporal: {analyzer.get_temporal_summary()}")
    analyzer.stop()