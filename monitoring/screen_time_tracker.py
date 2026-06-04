"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    NEXUS — Screen Time Tracker                              ║
║                                                                            ║
║  Comprehensive screen time analytics: daily/weekly reports, per-app         ║
║  breakdowns, streak tracking, comparative analytics, wellbeing scoring,    ║
║  and SQLite-backed historical data.                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
import os
import sqlite3
import threading
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, date
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("NEXUS.ScreenTime")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class DailyReport:
    """Full screen time report for a single day"""
    date: str = ""
    total_active_minutes: float = 0.0
    total_idle_minutes: float = 0.0
    total_screen_minutes: float = 0.0

    # Per-app breakdown: app_name → minutes
    app_minutes: Dict[str, float] = field(default_factory=dict)
    # Per-category breakdown: category → minutes
    category_minutes: Dict[str, float] = field(default_factory=dict)

    # Sessions
    session_count: int = 0
    longest_session_minutes: float = 0.0
    avg_session_minutes: float = 0.0

    # Breaks
    break_count: int = 0
    avg_break_minutes: float = 0.0
    longest_no_break_minutes: float = 0.0

    # Time segments
    morning_minutes: float = 0.0    # 6-12
    afternoon_minutes: float = 0.0  # 12-18
    evening_minutes: float = 0.0    # 18-22
    night_minutes: float = 0.0     # 22-6

    # First and last activity
    first_activity_time: str = ""
    last_activity_time: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WeeklyReport:
    """Aggregated weekly screen time report"""
    week_start: str = ""
    week_end: str = ""

    total_active_minutes: float = 0.0
    daily_average_minutes: float = 0.0
    busiest_day: str = ""
    busiest_day_minutes: float = 0.0
    quietest_day: str = ""
    quietest_day_minutes: float = 0.0

    # Day-by-day totals
    daily_totals: Dict[str, float] = field(default_factory=dict)

    # Hourly heatmap: hour (0-23) → avg minutes active
    hourly_heatmap: Dict[int, float] = field(default_factory=dict)

    # Category breakdown
    category_totals: Dict[str, float] = field(default_factory=dict)

    # Comparison to previous week
    vs_previous_week_percent: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Streaks:
    """Streak tracking for engagement and wellbeing"""
    # Consecutive active days
    current_active_day_streak: int = 0
    longest_active_day_streak: int = 0

    # Longest single focus session (minutes)
    current_focus_streak_minutes: float = 0.0
    longest_focus_streak_minutes: float = 0.0

    # Break compliance (took a break within every 60 min)
    current_break_compliance_streak: int = 0   # days
    longest_break_compliance_streak: int = 0

    # No late-night usage streak
    current_no_late_night_streak: int = 0  # days
    longest_no_late_night_streak: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WellbeingScore:
    """Wellbeing score derived from screen time patterns"""
    overall: float = 0.5          # 0.0 (poor) to 1.0 (excellent)

    # Sub-scores
    break_regularity: float = 0.5    # Do they take regular breaks?
    session_balance: float = 0.5     # Balanced session durations?
    late_night_avoidance: float = 0.5  # Not using device late at night?
    variety: float = 0.5             # Do they use diverse apps/categories?
    consistency: float = 0.5         # Consistent daily patterns?

    # Recommendations
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ComparativeStats:
    """Today vs average comparison"""
    today_minutes: float = 0.0
    average_minutes: float = 0.0
    delta_percent: float = 0.0
    delta_label: str = "on par"  # "less than usual", "more than usual", "on par"

    today_top_app: str = ""
    usual_top_app: str = ""

    today_sessions: int = 0
    average_sessions: float = 0.0

    today_breaks: int = 0
    average_breaks: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# SCREEN TIME TRACKER
# ═══════════════════════════════════════════════════════════════════════════════


class ScreenTimeTracker:
    """
    Tracks and analyzes screen time patterns.

    Features:
    - Daily / weekly / monthly reports
    - Per-app and per-category time breakdowns
    - Streak tracking (active days, focus, breaks)
    - Comparative analytics (today vs average)
    - Wellbeing scoring
    - SQLite persistence
    """

    def __init__(self):
        # ── Configuration ──
        self._update_interval: float = 60.0       # seconds
        self._break_reminder_minutes: int = 60
        self._late_night_hour: int = 23
        self._streak_min_minutes: float = 30.0
        self._history_retention_days: int = 90

        # ── State ──
        self._running: bool = False
        self._update_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Today's accumulator
        self._today: DailyReport = DailyReport(
            date=date.today().isoformat()
        )
        self._current_date: str = date.today().isoformat()
        self._streaks: Streaks = Streaks()
        self._wellbeing: WellbeingScore = WellbeingScore()

        # Session tracking
        self._session_start: Optional[datetime] = None
        self._last_active_time: Optional[datetime] = None
        self._current_session_minutes: float = 0.0
        self._session_durations: List[float] = []
        self._break_durations: List[float] = []
        self._last_break_time: Optional[datetime] = None
        self._since_last_break_minutes: float = 0.0

        # Hourly accumulator for heatmap data
        self._hourly_active_minutes: Dict[int, float] = defaultdict(float)

        # Stats
        self._total_updates: int = 0
        self._start_time: Optional[datetime] = None

        # Database
        self._db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "screen_time.db"
        )
        self._db_conn: Optional[sqlite3.Connection] = None
        self._init_database()
        self._load_streaks()

    # ═══════════════════════════════════════════════════════════════════════════
    # DATABASE
    # ═══════════════════════════════════════════════════════════════════════════

    def _init_database(self):
        """Initialize SQLite database"""
        try:
            self._db_conn = sqlite3.connect(
                self._db_path, check_same_thread=False
            )
            self._db_conn.row_factory = sqlite3.Row
            self._db_conn.execute("PRAGMA journal_mode=WAL")
            self._db_conn.execute("PRAGMA synchronous=NORMAL")

            self._db_conn.executescript("""
                CREATE TABLE IF NOT EXISTS daily_reports (
                    date TEXT PRIMARY KEY,
                    total_active_minutes REAL DEFAULT 0,
                    total_idle_minutes REAL DEFAULT 0,
                    total_screen_minutes REAL DEFAULT 0,
                    session_count INTEGER DEFAULT 0,
                    longest_session_minutes REAL DEFAULT 0,
                    avg_session_minutes REAL DEFAULT 0,
                    break_count INTEGER DEFAULT 0,
                    avg_break_minutes REAL DEFAULT 0,
                    longest_no_break_minutes REAL DEFAULT 0,
                    morning_minutes REAL DEFAULT 0,
                    afternoon_minutes REAL DEFAULT 0,
                    evening_minutes REAL DEFAULT 0,
                    night_minutes REAL DEFAULT 0,
                    first_activity TEXT,
                    last_activity TEXT,
                    app_minutes_json TEXT,
                    category_minutes_json TEXT,
                    hourly_heatmap_json TEXT,
                    wellbeing_score REAL DEFAULT 0.5,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS streaks (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    data_json TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS weekly_reports (
                    week_start TEXT PRIMARY KEY,
                    report_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_daily_date
                    ON daily_reports(date);
            """)

            self._db_conn.commit()
            logger.debug("Screen time database initialized")

        except Exception as e:
            logger.error(f"Failed to init screen time DB: {e}")

    def _db_execute(
        self, query: str, params: tuple = (), fetch: bool = False
    ):
        try:
            if not self._db_conn:
                return [] if fetch else None
            cursor = self._db_conn.execute(query, params)
            if fetch:
                return [dict(row) for row in cursor.fetchall()]
            self._db_conn.commit()
            return None
        except Exception as e:
            logger.error(f"Screen time DB error: {e}")
            return [] if fetch else None

    def _load_streaks(self):
        """Load streaks from database"""
        rows = self._db_execute(
            "SELECT data_json FROM streaks WHERE id = 1", fetch=True
        )
        if rows and rows[0].get("data_json"):
            try:
                data = json.loads(rows[0]["data_json"])
                for k, v in data.items():
                    if hasattr(self._streaks, k):
                        setattr(self._streaks, k, v)
            except Exception:
                pass

    def _save_streaks(self):
        """Persist streaks to database"""
        self._db_execute(
            """INSERT OR REPLACE INTO streaks (id, data_json, updated_at)
               VALUES (1, ?, ?)""",
            (json.dumps(self._streaks.to_dict()), datetime.now().isoformat())
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        if self._running:
            return
        self._running = True
        self._start_time = datetime.now()

        self._update_thread = threading.Thread(
            target=self._update_loop,
            daemon=True,
            name="ScreenTimeTracker"
        )
        self._update_thread.start()
        logger.info("📊 ScreenTimeTracker ACTIVE")

    def stop(self):
        if not self._running:
            return
        self._running = False

        # Save current day's data
        self._save_daily_report()
        self._save_streaks()

        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join(timeout=5.0)

        if self._db_conn:
            try:
                self._db_conn.close()
            except Exception:
                pass

        logger.info("ScreenTimeTracker stopped")

    # ═══════════════════════════════════════════════════════════════════════════
    # UPDATE LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    def _update_loop(self):
        """Periodic update loop"""
        logger.info("Screen time update loop started")

        while self._running:
            try:
                self._check_day_rollover()
                self._compute_wellbeing()

                # Save periodically (every 5 min = 5 updates at 60s)
                self._total_updates += 1
                if self._total_updates % 5 == 0:
                    self._save_daily_report()
                    self._save_streaks()

                # Weekly report at end of week
                if (datetime.now().weekday() == 0 and
                        datetime.now().hour == 0 and
                        self._total_updates % 60 == 0):
                    self._generate_weekly_report()

                # Old data cleanup (once per day equivalent)
                if self._total_updates % 1440 == 0:
                    self._cleanup_old_data()

                time.sleep(self._update_interval)

            except Exception as e:
                logger.error(f"Screen time update error: {e}")
                time.sleep(30)

    def _check_day_rollover(self):
        """Handle transition to a new day"""
        today = date.today().isoformat()
        if today != self._current_date:
            # Save yesterday's report
            self._save_daily_report()
            self._update_streaks_on_rollover()

            # Reset for new day
            self._current_date = today
            self._today = DailyReport(date=today)
            self._session_durations.clear()
            self._break_durations.clear()
            self._hourly_active_minutes.clear()
            self._since_last_break_minutes = 0.0
            logger.info(f"Screen time: day rolled over to {today}")

    # ═══════════════════════════════════════════════════════════════════════════
    # DATA INGESTION (called by orchestrator)
    # ═══════════════════════════════════════════════════════════════════════════

    def ingest_activity(self, data: Dict[str, Any]):
        """
        Ingest real-time activity data from UserTracker.
        
        Expected keys:
          - activity_level: str (idle, low, moderate, active, intense)
          - active_window: dict with process_name, title, category
          - timestamp: ISO string
        """
        with self._lock:
            try:
                now = datetime.now()
                activity = data.get("activity_level", "idle")
                window = data.get("active_window", {})
                app = window.get("process_name", "unknown")
                category = window.get("category", "unknown")
                hour = now.hour

                is_active = activity not in ("idle",)

                if is_active:
                    # ── Active time ──
                    interval_minutes = self._update_interval / 60.0

                    self._today.total_active_minutes += interval_minutes
                    self._today.total_screen_minutes += interval_minutes

                    # App breakdown
                    self._today.app_minutes[app] = (
                        self._today.app_minutes.get(app, 0.0) +
                        interval_minutes
                    )

                    # Category breakdown
                    self._today.category_minutes[category] = (
                        self._today.category_minutes.get(category, 0.0) +
                        interval_minutes
                    )

                    # Time segment
                    if 6 <= hour < 12:
                        self._today.morning_minutes += interval_minutes
                    elif 12 <= hour < 18:
                        self._today.afternoon_minutes += interval_minutes
                    elif 18 <= hour < 22:
                        self._today.evening_minutes += interval_minutes
                    else:
                        self._today.night_minutes += interval_minutes

                    # Hourly heatmap
                    self._hourly_active_minutes[hour] += interval_minutes

                    # First/last activity
                    time_str = now.strftime("%H:%M")
                    if not self._today.first_activity_time:
                        self._today.first_activity_time = time_str
                    self._today.last_activity_time = time_str

                    # Session tracking
                    if self._session_start is None:
                        self._session_start = now
                        self._today.session_count += 1
                    self._last_active_time = now
                    self._current_session_minutes += interval_minutes
                    self._since_last_break_minutes += interval_minutes

                    # Track longest no-break stretch
                    if (self._since_last_break_minutes >
                            self._today.longest_no_break_minutes):
                        self._today.longest_no_break_minutes = (
                            self._since_last_break_minutes
                        )

                else:
                    # ── Idle time ──
                    interval_minutes = self._update_interval / 60.0
                    self._today.total_idle_minutes += interval_minutes

                    # Detect session end (idle for > 5 min)
                    if (self._last_active_time and
                            (now - self._last_active_time).total_seconds() > 300):
                        if self._current_session_minutes > 0:
                            self._session_durations.append(
                                self._current_session_minutes
                            )
                            if (self._current_session_minutes >
                                    self._today.longest_session_minutes):
                                self._today.longest_session_minutes = (
                                    self._current_session_minutes
                                )
                        self._session_start = None
                        self._current_session_minutes = 0.0

                        # Count as a break
                        self._today.break_count += 1
                        self._last_break_time = now
                        self._since_last_break_minutes = 0.0

                # Update averages
                if self._session_durations:
                    self._today.avg_session_minutes = (
                        sum(self._session_durations) /
                        len(self._session_durations)
                    )
                if self._break_durations:
                    self._today.avg_break_minutes = (
                        sum(self._break_durations) /
                        len(self._break_durations)
                    )

            except Exception as e:
                logger.error(f"Screen time ingest error: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # WELLBEING SCORING
    # ═══════════════════════════════════════════════════════════════════════════

    def _compute_wellbeing(self):
        """Calculate wellbeing score from today's patterns"""
        w = self._wellbeing
        t = self._today
        recs = []

        # ── Break regularity (0-1) ──
        if t.total_active_minutes > 30:
            expected_breaks = max(1, t.total_active_minutes / self._break_reminder_minutes)
            actual_breaks = t.break_count
            w.break_regularity = min(1.0, actual_breaks / expected_breaks)

            if w.break_regularity < 0.5:
                recs.append(
                    f"Take more breaks — you've gone {t.longest_no_break_minutes:.0f} min "
                    f"without one today"
                )
        else:
            w.break_regularity = 1.0

        # ── Session balance (0-1) ──
        if self._session_durations and len(self._session_durations) >= 2:
            avg = sum(self._session_durations) / len(self._session_durations)
            max_sess = max(self._session_durations)
            # Penalize if any session is >3x the average
            if avg > 0:
                balance_ratio = min(max_sess / avg, 5.0) / 5.0
                w.session_balance = max(0.0, 1.0 - balance_ratio + 0.4)
            else:
                w.session_balance = 0.5

            if max_sess > 120:
                recs.append(
                    f"Your longest session was {max_sess:.0f} min. "
                    f"Try breaking it into shorter chunks."
                )
        else:
            w.session_balance = 0.5

        # ── Late night avoidance (0-1) ──
        if t.night_minutes > 60:
            w.late_night_avoidance = max(0.0, 1.0 - (t.night_minutes / 180.0))
            recs.append(
                f"You spent {t.night_minutes:.0f} min on screen after 10 PM. "
                f"Consider winding down earlier."
            )
        elif t.night_minutes > 0:
            w.late_night_avoidance = max(0.3, 1.0 - (t.night_minutes / 180.0))
        else:
            w.late_night_avoidance = 1.0

        # ── Variety (0-1) ──
        if t.category_minutes:
            n_categories = len(t.category_minutes)
            total = sum(t.category_minutes.values())
            if total > 0 and n_categories > 1:
                # Normalized entropy
                import math
                probs = [v / total for v in t.category_minutes.values()]
                entropy = -sum(p * math.log2(p) for p in probs if p > 0)
                max_entropy = math.log2(n_categories)
                w.variety = min(1.0, entropy / max_entropy) if max_entropy > 0 else 0.5
            else:
                w.variety = 0.2
                if n_categories == 1:
                    recs.append(
                        "You've only used one type of application today. "
                        "Consider diversifying your activities."
                    )
        else:
            w.variety = 0.5

        # ── Consistency (0-1) ──
        # Compare today's total with recent daily averages
        recent_rows = self._db_execute(
            """SELECT total_active_minutes FROM daily_reports
               ORDER BY date DESC LIMIT 7""",
            fetch=True
        )
        if recent_rows and len(recent_rows) >= 3:
            avg_recent = sum(
                r["total_active_minutes"] for r in recent_rows
            ) / len(recent_rows)
            if avg_recent > 0:
                ratio = t.total_active_minutes / avg_recent
                # 1.0 means exactly on average; penalize deviations
                w.consistency = max(0.0, 1.0 - abs(1.0 - ratio) * 0.5)
            else:
                w.consistency = 0.5
        else:
            w.consistency = 0.5

        # ── Overall (weighted) ──
        w.overall = round(
            w.break_regularity * 0.25 +
            w.session_balance * 0.20 +
            w.late_night_avoidance * 0.25 +
            w.variety * 0.10 +
            w.consistency * 0.20,
            3
        )

        w.recommendations = recs[:5]

    # ═══════════════════════════════════════════════════════════════════════════
    # STREAKS
    # ═══════════════════════════════════════════════════════════════════════════

    def _update_streaks_on_rollover(self):
        """Update streaks when the day rolls over"""
        s = self._streaks
        t = self._today

        # Active day streak
        if t.total_active_minutes >= self._streak_min_minutes:
            s.current_active_day_streak += 1
            s.longest_active_day_streak = max(
                s.longest_active_day_streak, s.current_active_day_streak
            )
        else:
            s.current_active_day_streak = 0

        # Focus streak
        if self._session_durations:
            max_session = max(self._session_durations)
            s.current_focus_streak_minutes = max_session
            s.longest_focus_streak_minutes = max(
                s.longest_focus_streak_minutes, max_session
            )

        # Break compliance
        if t.longest_no_break_minutes <= self._break_reminder_minutes:
            s.current_break_compliance_streak += 1
            s.longest_break_compliance_streak = max(
                s.longest_break_compliance_streak,
                s.current_break_compliance_streak
            )
        else:
            s.current_break_compliance_streak = 0

        # Late night avoidance
        if t.night_minutes < 30:
            s.current_no_late_night_streak += 1
            s.longest_no_late_night_streak = max(
                s.longest_no_late_night_streak,
                s.current_no_late_night_streak
            )
        else:
            s.current_no_late_night_streak = 0

    # ═══════════════════════════════════════════════════════════════════════════
    # REPORTS
    # ═══════════════════════════════════════════════════════════════════════════

    def _save_daily_report(self):
        """Save today's report to database"""
        t = self._today
        try:
            self._db_execute(
                """INSERT OR REPLACE INTO daily_reports
                   (date, total_active_minutes, total_idle_minutes,
                    total_screen_minutes, session_count,
                    longest_session_minutes, avg_session_minutes,
                    break_count, avg_break_minutes,
                    longest_no_break_minutes,
                    morning_minutes, afternoon_minutes,
                    evening_minutes, night_minutes,
                    first_activity, last_activity,
                    app_minutes_json, category_minutes_json,
                    hourly_heatmap_json, wellbeing_score)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    t.date, t.total_active_minutes, t.total_idle_minutes,
                    t.total_screen_minutes, t.session_count,
                    t.longest_session_minutes, t.avg_session_minutes,
                    t.break_count, t.avg_break_minutes,
                    t.longest_no_break_minutes,
                    t.morning_minutes, t.afternoon_minutes,
                    t.evening_minutes, t.night_minutes,
                    t.first_activity_time, t.last_activity_time,
                    json.dumps(t.app_minutes, default=str),
                    json.dumps(t.category_minutes, default=str),
                    json.dumps(dict(self._hourly_active_minutes), default=str),
                    self._wellbeing.overall
                )
            )
        except Exception as e:
            logger.error(f"Failed to save daily report: {e}")

    def _generate_weekly_report(self):
        """Generate and persist a weekly report"""
        try:
            today = date.today()
            week_start = (today - timedelta(days=7)).isoformat()
            week_end = (today - timedelta(days=1)).isoformat()

            rows = self._db_execute(
                """SELECT * FROM daily_reports
                   WHERE date >= ? AND date <= ?
                   ORDER BY date ASC""",
                (week_start, week_end), fetch=True
            )

            if not rows:
                return

            wr = WeeklyReport(
                week_start=week_start,
                week_end=week_end
            )

            # Daily totals
            for row in rows:
                day = row["date"]
                mins = row["total_active_minutes"] or 0
                wr.daily_totals[day] = mins
                wr.total_active_minutes += mins

                # Category aggregation
                cat_json = row.get("category_minutes_json", "{}")
                if cat_json:
                    cats = json.loads(cat_json)
                    for cat, m in cats.items():
                        wr.category_totals[cat] = (
                            wr.category_totals.get(cat, 0.0) + m
                        )

                # Heatmap aggregation
                hm_json = row.get("hourly_heatmap_json", "{}")
                if hm_json:
                    hm = json.loads(hm_json)
                    for h, m in hm.items():
                        h_int = int(h)
                        wr.hourly_heatmap[h_int] = (
                            wr.hourly_heatmap.get(h_int, 0.0) + m
                        )

            # Averages
            n_days = len(rows)
            wr.daily_average_minutes = (
                wr.total_active_minutes / n_days if n_days > 0 else 0
            )

            # Busiest / quietest day
            if wr.daily_totals:
                wr.busiest_day = max(wr.daily_totals, key=wr.daily_totals.get)
                wr.busiest_day_minutes = wr.daily_totals[wr.busiest_day]
                wr.quietest_day = min(wr.daily_totals, key=wr.daily_totals.get)
                wr.quietest_day_minutes = wr.daily_totals[wr.quietest_day]

            # Average heatmap
            for h in wr.hourly_heatmap:
                wr.hourly_heatmap[h] = round(
                    wr.hourly_heatmap[h] / n_days, 1
                )

            # Previous week comparison
            prev_start = (today - timedelta(days=14)).isoformat()
            prev_end = (today - timedelta(days=8)).isoformat()
            prev_rows = self._db_execute(
                """SELECT SUM(total_active_minutes) as total
                   FROM daily_reports
                   WHERE date >= ? AND date <= ?""",
                (prev_start, prev_end), fetch=True
            )
            prev_total = (
                prev_rows[0]["total"] if prev_rows and prev_rows[0]["total"]
                else 0
            )
            if prev_total > 0:
                wr.vs_previous_week_percent = round(
                    ((wr.total_active_minutes - prev_total) / prev_total) * 100,
                    1
                )

            # Save
            self._db_execute(
                """INSERT OR REPLACE INTO weekly_reports
                   (week_start, report_json)
                   VALUES (?, ?)""",
                (week_start, json.dumps(wr.to_dict(), default=str))
            )

            logger.info(f"Weekly report generated: {week_start} to {week_end}")

        except Exception as e:
            logger.error(f"Failed to generate weekly report: {e}")

    def _cleanup_old_data(self):
        """Remove data older than retention period"""
        cutoff = (
            date.today() - timedelta(days=self._history_retention_days)
        ).isoformat()
        self._db_execute(
            "DELETE FROM daily_reports WHERE date < ?", (cutoff,)
        )
        self._db_execute(
            "DELETE FROM weekly_reports WHERE week_start < ?", (cutoff,)
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # COMPARATIVE ANALYTICS
    # ═══════════════════════════════════════════════════════════════════════════

    def get_today_vs_average(self) -> Dict[str, Any]:
        """Compare today's stats with historical average"""
        comp = ComparativeStats()
        comp.today_minutes = self._today.total_active_minutes
        comp.today_sessions = self._today.session_count
        comp.today_breaks = self._today.break_count

        # Get top app today
        if self._today.app_minutes:
            comp.today_top_app = max(
                self._today.app_minutes,
                key=self._today.app_minutes.get
            )

        # Historical averages
        rows = self._db_execute(
            """SELECT total_active_minutes, session_count,
                      break_count, app_minutes_json
               FROM daily_reports
               ORDER BY date DESC LIMIT 14""",
            fetch=True
        )

        if rows and len(rows) >= 3:
            comp.average_minutes = sum(
                r["total_active_minutes"] or 0 for r in rows
            ) / len(rows)
            comp.average_sessions = sum(
                r["session_count"] or 0 for r in rows
            ) / len(rows)
            comp.average_breaks = sum(
                r["break_count"] or 0 for r in rows
            ) / len(rows)

            # Most common top app historically
            app_counts = Counter()
            for r in rows:
                app_json = r.get("app_minutes_json", "{}")
                if app_json:
                    apps = json.loads(app_json)
                    if apps:
                        top = max(apps, key=apps.get)
                        app_counts[top] += 1
            if app_counts:
                comp.usual_top_app = app_counts.most_common(1)[0][0]

            # Delta
            if comp.average_minutes > 0:
                comp.delta_percent = round(
                    ((comp.today_minutes - comp.average_minutes) /
                     comp.average_minutes) * 100, 1
                )

                if comp.delta_percent > 15:
                    comp.delta_label = "more than usual"
                elif comp.delta_percent < -15:
                    comp.delta_label = "less than usual"
                else:
                    comp.delta_label = "on par"

        return comp.to_dict()

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def get_today_report(self) -> Dict[str, Any]:
        """Get today's screen time report"""
        with self._lock:
            return self._today.to_dict()

    def get_weekly_report(self) -> Optional[Dict[str, Any]]:
        """Get the most recent weekly report"""
        rows = self._db_execute(
            """SELECT report_json FROM weekly_reports
               ORDER BY week_start DESC LIMIT 1""",
            fetch=True
        )
        if rows and rows[0].get("report_json"):
            return json.loads(rows[0]["report_json"])
        return None

    def get_streaks(self) -> Dict[str, Any]:
        """Get current streak data"""
        return self._streaks.to_dict()

    def get_wellbeing_score(self) -> Dict[str, Any]:
        """Get current wellbeing score"""
        return self._wellbeing.to_dict()

    def get_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get daily reports for the last N days"""
        cutoff = (
            date.today() - timedelta(days=days)
        ).isoformat()
        rows = self._db_execute(
            """SELECT date, total_active_minutes, total_screen_minutes,
                      session_count, break_count, wellbeing_score,
                      morning_minutes, afternoon_minutes,
                      evening_minutes, night_minutes
               FROM daily_reports
               WHERE date > ?
               ORDER BY date ASC""",
            (cutoff,), fetch=True
        )
        return rows or []

    def get_context_for_brain(self) -> str:
        """
        Get concise screen time context for brain prompt injection.
        Only includes noteworthy information.
        """
        parts = []
        t = self._today

        if t.total_active_minutes > 0:
            hours = t.total_active_minutes / 60
            parts.append(
                f"Screen time today: {hours:.1f}h active "
                f"({t.session_count} sessions)"
            )

        # Comparative
        comp = self.get_today_vs_average()
        if comp.get("delta_label") != "on par" and comp.get("average_minutes", 0) > 0:
            parts.append(
                f"Today is {comp['delta_label']} "
                f"({comp['delta_percent']:+.0f}% vs average)"
            )

        # Break reminder
        if self._since_last_break_minutes > self._break_reminder_minutes:
            parts.append(
                f"User has been working {self._since_last_break_minutes:.0f} min "
                f"without a break"
            )

        # Wellbeing
        if self._wellbeing.overall < 0.4:
            parts.append(
                f"Wellbeing score low ({self._wellbeing.overall:.0%}): "
                f"{'; '.join(self._wellbeing.recommendations[:2])}"
            )

        # Streaks
        s = self._streaks
        if s.current_active_day_streak >= 5:
            parts.append(
                f"Active {s.current_active_day_streak}-day streak!"
            )

        return "\n".join(parts) if parts else ""

    def get_stats(self) -> Dict[str, Any]:
        """Get operational stats"""
        return {
            "running": self._running,
            "total_updates": self._total_updates,
            "today_active_minutes": self._today.total_active_minutes,
            "today_sessions": self._today.session_count,
            "today_breaks": self._today.break_count,
            "wellbeing_score": self._wellbeing.overall,
            "active_day_streak": self._streaks.current_active_day_streak,
            "since_last_break_min": self._since_last_break_minutes,
            "uptime": str(
                datetime.now() - self._start_time
            ) if self._start_time else "not started",
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

screen_time_tracker = ScreenTimeTracker()

if __name__ == "__main__":
    tracker = ScreenTimeTracker()
    tracker.start()

    # Simulate activity data
    import random
    print("Simulating screen time data...")

    apps = ["code", "chrome", "terminal", "discord", "explorer", "spotify"]
    categories = [
        "code_editor", "browser", "terminal",
        "communication", "file_manager", "media"
    ]

    for i in range(30):
        idx = random.randint(0, len(apps) - 1)
        tracker.ingest_activity({
            "activity_level": random.choice(
                ["idle", "low", "moderate", "active", "intense"]
            ),
            "active_window": {
                "process_name": apps[idx],
                "title": f"Window {i}",
                "category": categories[idx]
            },
            "timestamp": datetime.now().isoformat()
        })
        time.sleep(0.1)

    print("\nToday's Report:")
    print(json.dumps(tracker.get_today_report(), indent=2, default=str))
    print(f"\nWellbeing: {json.dumps(tracker.get_wellbeing_score(), indent=2)}")
    print(f"\nStreaks: {json.dumps(tracker.get_streaks(), indent=2)}")
    print(f"\nContext: {tracker.get_context_for_brain()}")

    tracker.stop()
