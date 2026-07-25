"""
NEXUS AI — Predictive Threat Modeling
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Predicts incoming threats using network pattern analysis, CVE trend
forecasting, social media sentiment correlation, and temporal modeling.

Architecture:
  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
  │ NETWORK      │    │  CVE TRENDS  │    │  SENTIMENT   │
  │ Anomaly Det. │    │  Forecasting │    │  Correlation │
  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
         │                   │                    │
  ┌──────▼───────────────────▼────────────────────▼───────┐
  │                PREDICTION ENGINE                       │
  │   • Exponential smoothing forecaster                  │
  │   • Anomaly detection (z-score, IQR)                  │
  │   • Attack pattern recognition                        │
  │   • Temporal correlation w/ temporal_prophecy.py       │
  │   • Risk scoring and probability estimation           │
  └───────────────────────────────────────────────────────┘
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import hashlib
import json
import math
import os
import re
import sys
import threading
import time
import traceback
import uuid
from collections import Counter, deque, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from config import DATA_DIR
from utils.logger import get_logger, log_system
from core.event_bus import EventType, event_bus, publish

logger = get_logger("threat_modeling")

# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class ThreatPredictionType(Enum):
    NETWORK_ANOMALY = "network_anomaly"
    CVE_SPIKE = "cve_spike"
    SENTIMENT_SHIFT = "sentiment_shift"
    ATTACK_PATTERN = "attack_pattern"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    BEHAVIORAL_ANOMALY = "behavioral_anomaly"
    TEMPORAL_CORRELATION = "temporal_correlation"

class RiskLevel(Enum):
    NEGLIGIBLE = "negligible"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"

class AnomalyType(Enum):
    SPIKE = "spike"
    DROP = "drop"
    PATTERN_BREAK = "pattern_break"
    CYCLIC_DEVIATION = "cyclic_deviation"
    TREND_REVERSAL = "trend_reversal"

@dataclass
class TimeSeriesPoint:
    """A single data point in a time series."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    value: float = 0.0
    label: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ThreatPrediction:
    """A predicted threat event."""
    prediction_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    prediction_type: str = "network_anomaly"
    risk_level: str = "moderate"
    probability: float = 0.5
    title: str = ""
    description: str = ""
    predicted_timeframe: str = ""
    confidence: float = 0.5
    indicators: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    expires_at: str = ""
    verified: Optional[bool] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def summary(self) -> str:
        return f"[{self.risk_level.upper()}] {self.title} (p={self.probability:.0%})"

@dataclass
class AttackPattern:
    """A recognized attack pattern."""
    pattern_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    indicators: List[str] = field(default_factory=list)
    frequency: int = 0
    last_seen: str = ""
    avg_severity: float = 0.0
    typical_targets: List[str] = field(default_factory=list)
    related_cves: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class NetworkBaseline:
    """Baseline network metrics for anomaly detection."""
    metric_name: str = ""
    avg_value: float = 0.0
    std_deviation: float = 0.0
    min_value: float = 0.0
    max_value: float = 0.0
    sample_count: int = 0
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def z_score(self, value: float) -> float:
        """Calculate z-score for a value against this baseline."""
        if self.std_deviation == 0:
            return 0.0
        return (value - self.avg_value) / self.std_deviation

@dataclass
class ThreatModelStats:
    """Statistics for the threat modeling engine."""
    total_predictions: int = 0
    accurate_predictions: int = 0
    false_positives: int = 0
    total_anomalies_detected: int = 0
    total_patterns_recognized: int = 0
    active_predictions: int = 0
    avg_confidence: float = 0.0
    prediction_accuracy: float = 0.0
    network_baselines_tracked: int = 0
    last_analysis_time: Optional[str] = None
    risk_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# ═══════════════════════════════════════════════════════════════════════════════
# TIME SERIES FORECASTER
# ═══════════════════════════════════════════════════════════════════════════════

class TimeSeriesForecaster:
    """Exponential smoothing forecaster for time series data."""

    def __init__(self, alpha: float = 0.3, beta: float = 0.1):
        self._alpha = alpha  # Level smoothing
        self._beta = beta    # Trend smoothing

    def forecast(self, series: List[float], steps: int = 5) -> List[float]:
        """Double exponential smoothing forecast."""
        if len(series) < 2:
            return [series[-1]] * steps if series else [0.0] * steps

        # Initialize
        level = series[0]
        trend = series[1] - series[0]

        # Fit
        for val in series[1:]:
            prev_level = level
            level = self._alpha * val + (1 - self._alpha) * (level + trend)
            trend = self._beta * (level - prev_level) + (1 - self._beta) * trend

        # Forecast
        forecasts = []
        for i in range(1, steps + 1):
            forecasts.append(level + i * trend)

        return forecasts

    def detect_trend(self, series: List[float]) -> str:
        """Detect overall trend direction."""
        if len(series) < 3:
            return "stable"

        # Simple linear regression slope
        n = len(series)
        x_mean = (n - 1) / 2
        y_mean = sum(series) / n

        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(series))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "stable"

        slope = numerator / denominator
        normalized_slope = slope / max(abs(y_mean), 0.001)

        if normalized_slope > 0.05:
            return "increasing"
        elif normalized_slope < -0.05:
            return "decreasing"
        return "stable"

# ═══════════════════════════════════════════════════════════════════════════════
# ANOMALY DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════

class AnomalyDetector:
    """Detects anomalies in metric streams using statistical methods."""

    def __init__(self):
        self._baselines: Dict[str, NetworkBaseline] = {}
        self._history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))
        self._lock = threading.Lock()

    def record_metric(self, metric_name: str, value: float):
        """Record a metric value and update baseline."""
        with self._lock:
            self._history[metric_name].append(value)
            self._update_baseline(metric_name)

    def _update_baseline(self, metric_name: str):
        """Update baseline statistics for a metric."""
        values = list(self._history[metric_name])
        if len(values) < 10:
            return

        avg = sum(values) / len(values)
        variance = sum((v - avg) ** 2 for v in values) / len(values)
        std = math.sqrt(variance)

        self._baselines[metric_name] = NetworkBaseline(
            metric_name=metric_name,
            avg_value=avg,
            std_deviation=std,
            min_value=min(values),
            max_value=max(values),
            sample_count=len(values),
        )

    def check_anomaly(self, metric_name: str, value: float,
                       threshold: float = 2.5) -> Optional[Dict[str, Any]]:
        """Check if a value is anomalous for the given metric."""
        baseline = self._baselines.get(metric_name)
        if not baseline or baseline.sample_count < 10:
            return None

        z = baseline.z_score(value)

        if abs(z) > threshold:
            anomaly_type = AnomalyType.SPIKE.value if z > 0 else AnomalyType.DROP.value
            return {
                "metric": metric_name,
                "value": value,
                "z_score": round(z, 2),
                "baseline_avg": round(baseline.avg_value, 2),
                "baseline_std": round(baseline.std_deviation, 2),
                "anomaly_type": anomaly_type,
                "severity": min(1.0, abs(z) / 5.0),
            }

        return None

    def detect_pattern_break(self, metric_name: str, window: int = 20) -> Optional[str]:
        """Detect if recent pattern differs from historical."""
        values = list(self._history.get(metric_name, []))
        if len(values) < window * 2:
            return None

        old_window = values[-window * 2:-window]
        new_window = values[-window:]

        old_avg = sum(old_window) / len(old_window)
        new_avg = sum(new_window) / len(new_window)

        change_pct = (new_avg - old_avg) / max(abs(old_avg), 0.001) * 100

        if abs(change_pct) > 30:
            return f"Pattern break: {metric_name} shifted {change_pct:+.1f}%"

        return None

    @property
    def baseline_count(self) -> int:
        return len(self._baselines)

    def get_all_baselines(self) -> Dict[str, Dict]:
        return {k: v.to_dict() for k, v in self._baselines.items()}

# ═══════════════════════════════════════════════════════════════════════════════
# ATTACK PATTERN RECOGNIZER
# ═══════════════════════════════════════════════════════════════════════════════

class AttackPatternRecognizer:
    """Recognizes known attack patterns from observed indicators."""

    def __init__(self):
        self._known_patterns: List[AttackPattern] = []
        self._build_pattern_library()

    def _build_pattern_library(self):
        """Build library of known attack patterns."""
        self._known_patterns = [
            AttackPattern(
                name="Port Scan Precursor",
                description="Sequential port scanning followed by targeted exploitation",
                indicators=["port_scan", "sequential_ports", "rapid_connections"],
                typical_targets=["web_servers", "database_servers"],
                avg_severity=5.0,
            ),
            AttackPattern(
                name="Brute Force Attack",
                description="Repeated authentication attempts with varied credentials",
                indicators=["failed_auth", "rapid_login_attempts", "credential_stuffing"],
                typical_targets=["ssh", "rdp", "web_login"],
                avg_severity=6.0,
            ),
            AttackPattern(
                name="Data Exfiltration",
                description="Unusual outbound data transfers suggesting data theft",
                indicators=["large_outbound", "unusual_destination", "encrypted_traffic", "dns_tunneling"],
                typical_targets=["database", "file_server"],
                avg_severity=8.0,
            ),
            AttackPattern(
                name="Lateral Movement",
                description="Internal network traversal after initial compromise",
                indicators=["internal_scan", "credential_reuse", "privilege_escalation"],
                typical_targets=["domain_controller", "internal_servers"],
                avg_severity=7.5,
            ),
            AttackPattern(
                name="Ransomware Deployment",
                description="Rapid file encryption across network shares",
                indicators=["mass_file_rename", "encryption_activity", "shadow_copy_delete"],
                typical_targets=["file_shares", "backup_servers"],
                avg_severity=9.5,
            ),
            AttackPattern(
                name="Supply Chain Attack",
                description="Compromise via trusted third-party software or updates",
                indicators=["modified_binary", "unsigned_update", "dependency_confusion"],
                typical_targets=["build_systems", "package_managers"],
                avg_severity=9.0,
            ),
            AttackPattern(
                name="DDoS Attack",
                description="Distributed denial of service via traffic flooding",
                indicators=["traffic_spike", "syn_flood", "amplification", "botnet_traffic"],
                typical_targets=["web_servers", "dns_servers"],
                avg_severity=6.5,
            ),
            AttackPattern(
                name="Crypto Mining",
                description="Unauthorized cryptocurrency mining on compromised systems",
                indicators=["high_cpu", "mining_pool_connection", "unusual_process"],
                typical_targets=["cloud_instances", "servers"],
                avg_severity=4.0,
            ),
        ]

    def match_pattern(self, observed_indicators: List[str]) -> List[Tuple[AttackPattern, float]]:
        """Match observed indicators against known patterns."""
        matches = []
        observed_set = set(i.lower() for i in observed_indicators)

        for pattern in self._known_patterns:
            pattern_indicators = set(i.lower() for i in pattern.indicators)
            overlap = observed_set & pattern_indicators

            if overlap:
                confidence = len(overlap) / len(pattern_indicators)
                matches.append((pattern, confidence))

        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    @property
    def pattern_count(self) -> int:
        return len(self._known_patterns)

# ═══════════════════════════════════════════════════════════════════════════════
# RISK SCORER
# ═══════════════════════════════════════════════════════════════════════════════

class RiskScorer:
    """Calculates overall risk score from multiple threat signals."""

    def __init__(self):
        self._risk_factors: Dict[str, float] = {}
        self._weights = {
            "network_anomalies": 0.25,
            "cve_trends": 0.15,
            "sentiment": 0.10,
            "attack_patterns": 0.25,
            "active_predictions": 0.15,
            "historical_accuracy": 0.10,
        }

    def update_factor(self, factor_name: str, value: float):
        """Update a risk factor (0-1 scale)."""
        self._risk_factors[factor_name] = max(0.0, min(1.0, value))

    def calculate_risk(self) -> float:
        """Calculate weighted risk score (0-10)."""
        score = 0.0
        total_weight = 0.0

        for factor, weight in self._weights.items():
            if factor in self._risk_factors:
                score += self._risk_factors[factor] * weight * 10
                total_weight += weight

        if total_weight > 0:
            score /= total_weight

        return round(min(10.0, score), 2)

    def get_risk_level(self) -> str:
        """Get qualitative risk level."""
        score = self.calculate_risk()
        if score < 2:
            return RiskLevel.NEGLIGIBLE.value
        elif score < 4:
            return RiskLevel.LOW.value
        elif score < 6:
            return RiskLevel.MODERATE.value
        elif score < 8:
            return RiskLevel.HIGH.value
        return RiskLevel.CRITICAL.value

    def get_factors(self) -> Dict[str, float]:
        return dict(self._risk_factors)

# ═══════════════════════════════════════════════════════════════════════════════
# PREDICTIVE THREAT MODELER — MAIN ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class PredictiveThreatModeler:
    """
    Predictive Threat Modeling Engine for NEXUS.
    
    Combines network anomaly detection, CVE trend forecasting,
    attack pattern recognition, and sentiment analysis to predict
    incoming threats before they materialize.
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
        self._data_dir = Path(DATA_DIR) / "threat_modeling"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        # ──── Components ────
        self._forecaster = TimeSeriesForecaster()
        self._anomaly_detector = AnomalyDetector()
        self._pattern_recognizer = AttackPatternRecognizer()
        self._risk_scorer = RiskScorer()

        # ──── State ────
        self._running = False
        self._predictions: deque = deque(maxlen=500)
        self._active_predictions: List[ThreatPrediction] = []
        self._metric_streams: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

        # ──── Stats ────
        self._stats = ThreatModelStats()

        # ──── Configuration ────
        self._analysis_interval = 120   # seconds
        self._prediction_horizon = 3600  # predict 1 hour ahead
        self._anomaly_threshold = 2.5
        self._confidence_threshold = 0.3

        # ──── Background ────
        self._daemon_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # ──── Load state ────
        self._load_state()

        logger.info(
            f"🔮 Predictive Threat Modeler initialized | "
            f"{self._pattern_recognizer.pattern_count} attack patterns | "
            f"{self._stats.total_predictions} historical predictions"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        if self._running:
            return
        self._running = True
        self._daemon_thread = threading.Thread(
            target=self._daemon_loop, daemon=True, name="ThreatModeler",
        )
        self._daemon_thread.start()
        logger.info("🔮 Threat Modeler daemon started")

    def stop(self):
        self._running = False
        self._save_state()
        if self._daemon_thread and self._daemon_thread.is_alive():
            self._daemon_thread.join(timeout=10)

    # ═══════════════════════════════════════════════════════════════════════════
    # DAEMON LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    def _daemon_loop(self):
        time.sleep(90)
        logger.info("🔮 Threat Modeler daemon loop active")

        while self._running:
            try:
                self._collect_metrics()
                self._run_analysis()
                self._expire_predictions()
                self._update_risk_score()
                self._stats.last_analysis_time = datetime.now().isoformat()
                time.sleep(self._analysis_interval)

            except Exception as e:
                logger.error(f"🔮 Threat modeling loop error: {e}\n{traceback.format_exc()}")
                time.sleep(120)

    # ═══════════════════════════════════════════════════════════════════════════
    # METRIC COLLECTION
    # ═══════════════════════════════════════════════════════════════════════════

    def _collect_metrics(self):
        """Collect system metrics for analysis."""
        try:
            import psutil
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            net = psutil.net_io_counters()

            self.ingest_metric("cpu_usage", cpu)
            self.ingest_metric("memory_usage", mem)
            self.ingest_metric("network_bytes_sent", net.bytes_sent)
            self.ingest_metric("network_bytes_recv", net.bytes_recv)
            self.ingest_metric("network_connections", len(psutil.net_connections()))

            # Disk I/O
            try:
                disk = psutil.disk_io_counters()
                if disk:
                    self.ingest_metric("disk_read_bytes", disk.read_bytes)
                    self.ingest_metric("disk_write_bytes", disk.write_bytes)
            except Exception:
                pass

        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"Metric collection error: {e}")

    def ingest_metric(self, metric_name: str, value: float):
        """Ingest a metric value for analysis."""
        self._metric_streams[metric_name].append(value)
        self._anomaly_detector.record_metric(metric_name, value)

    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════

    def _run_analysis(self):
        """Run all analysis pipelines."""
        # 1. Anomaly detection on all metrics
        anomalies = self._detect_anomalies()

        # 2. Trend forecasting
        trend_predictions = self._forecast_trends()

        # 3. Pattern matching
        pattern_matches = self._match_patterns(anomalies)

        # 4. Generate predictions
        all_predictions = anomalies + trend_predictions + pattern_matches
        for pred in all_predictions:
            if pred.confidence >= self._confidence_threshold:
                self._predictions.append(pred)
                self._active_predictions.append(pred)
                self._stats.total_predictions += 1

                if pred.risk_level in (RiskLevel.HIGH.value, RiskLevel.CRITICAL.value):
                    publish(EventType.SYSTEM_ALERT, {
                        "type": "threat_prediction",
                        "title": pred.title,
                        "risk": pred.risk_level,
                        "probability": pred.probability,
                    }, source="threat_modeling")

        self._stats.active_predictions = len(self._active_predictions)

    def _detect_anomalies(self) -> List[ThreatPrediction]:
        """Detect anomalies across all metric streams."""
        predictions = []

        for metric_name, values in self._metric_streams.items():
            if len(values) < 20:
                continue

            current = values[-1]
            anomaly = self._anomaly_detector.check_anomaly(
                metric_name, current, self._anomaly_threshold
            )

            if anomaly:
                self._stats.total_anomalies_detected += 1
                severity = anomaly["severity"]

                risk = RiskLevel.LOW.value
                if severity > 0.7:
                    risk = RiskLevel.HIGH.value
                elif severity > 0.4:
                    risk = RiskLevel.MODERATE.value

                pred = ThreatPrediction(
                    prediction_type=ThreatPredictionType.NETWORK_ANOMALY.value,
                    risk_level=risk,
                    probability=min(0.9, severity),
                    title=f"Anomaly: {metric_name} ({anomaly['anomaly_type']})",
                    description=(
                        f"{metric_name} = {current:.1f} (baseline: {anomaly['baseline_avg']:.1f} "
                        f"± {anomaly['baseline_std']:.1f}, z-score: {anomaly['z_score']:.1f})"
                    ),
                    confidence=min(0.9, severity * 0.8),
                    indicators=[metric_name, anomaly["anomaly_type"]],
                    predicted_timeframe="next 30 minutes",
                    expires_at=(datetime.now() + timedelta(minutes=30)).isoformat(),
                )
                predictions.append(pred)

            # Pattern break detection
            pattern_msg = self._anomaly_detector.detect_pattern_break(metric_name)
            if pattern_msg:
                pred = ThreatPrediction(
                    prediction_type=ThreatPredictionType.BEHAVIORAL_ANOMALY.value,
                    risk_level=RiskLevel.MODERATE.value,
                    probability=0.5,
                    title=pattern_msg,
                    description=pattern_msg,
                    confidence=0.5,
                    indicators=[metric_name, "pattern_break"],
                    predicted_timeframe="next 1 hour",
                    expires_at=(datetime.now() + timedelta(hours=1)).isoformat(),
                )
                predictions.append(pred)

        return predictions

    def _forecast_trends(self) -> List[ThreatPrediction]:
        """Forecast metric trends and predict resource issues."""
        predictions = []

        for metric_name in ["cpu_usage", "memory_usage", "network_connections"]:
            values = list(self._metric_streams.get(metric_name, []))
            if len(values) < 20:
                continue

            # Forecast next 5 points
            forecast = self._forecaster.forecast(values[-50:], steps=5)
            trend = self._forecaster.detect_trend(values[-50:])

            # Check if forecast predicts concerning levels
            if metric_name in ("cpu_usage", "memory_usage"):
                max_forecast = max(forecast)
                if max_forecast > 90:
                    pred = ThreatPrediction(
                        prediction_type=ThreatPredictionType.RESOURCE_EXHAUSTION.value,
                        risk_level=RiskLevel.HIGH.value,
                        probability=min(0.9, max_forecast / 100),
                        title=f"Resource exhaustion predicted: {metric_name}",
                        description=(
                            f"{metric_name} trending {trend}, forecast peak: {max_forecast:.0f}%. "
                            f"Current: {values[-1]:.0f}%"
                        ),
                        confidence=0.6,
                        indicators=[metric_name, trend, "resource_exhaustion"],
                        recommended_actions=["Investigate high usage processes", "Scale resources"],
                        predicted_timeframe="next 30 minutes",
                        expires_at=(datetime.now() + timedelta(minutes=30)).isoformat(),
                    )
                    predictions.append(pred)

        return predictions

    def _match_patterns(self, anomalies: List[ThreatPrediction]) -> List[ThreatPrediction]:
        """Match detected anomalies against known attack patterns."""
        predictions = []

        # Collect all indicators from anomalies
        all_indicators = []
        for anomaly in anomalies:
            all_indicators.extend(anomaly.indicators)

        # Add system-level indicators
        cpu_values = list(self._metric_streams.get("cpu_usage", []))
        if cpu_values and cpu_values[-1] > 80:
            all_indicators.append("high_cpu")

        net_conn = list(self._metric_streams.get("network_connections", []))
        if net_conn and net_conn[-1] > 100:
            all_indicators.append("rapid_connections")

        if not all_indicators:
            return predictions

        matches = self._pattern_recognizer.match_pattern(all_indicators)
        for pattern, confidence in matches[:3]:
            if confidence >= 0.3:
                self._stats.total_patterns_recognized += 1
                pred = ThreatPrediction(
                    prediction_type=ThreatPredictionType.ATTACK_PATTERN.value,
                    risk_level=RiskLevel.HIGH.value if pattern.avg_severity > 7 else RiskLevel.MODERATE.value,
                    probability=confidence,
                    title=f"Attack pattern: {pattern.name}",
                    description=f"{pattern.description}. Confidence: {confidence:.0%}",
                    confidence=confidence,
                    indicators=pattern.indicators,
                    recommended_actions=[
                        f"Monitor {', '.join(pattern.typical_targets[:3])}",
                        "Enable enhanced logging",
                        "Review firewall rules",
                    ],
                    predicted_timeframe="next 1-4 hours",
                    expires_at=(datetime.now() + timedelta(hours=4)).isoformat(),
                )
                predictions.append(pred)

        return predictions

    def _expire_predictions(self):
        """Remove expired predictions."""
        now = datetime.now()
        self._active_predictions = [
            p for p in self._active_predictions
            if not p.expires_at or self._parse_time(p.expires_at, now) > now
        ]
        self._stats.active_predictions = len(self._active_predictions)

    def _parse_time(self, ts: str, default: datetime) -> datetime:
        try:
            return datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            return default

    def _update_risk_score(self):
        """Update overall risk score."""
        # Anomaly factor
        recent_anomalies = sum(
            1 for p in self._active_predictions
            if p.prediction_type == ThreatPredictionType.NETWORK_ANOMALY.value
        )
        self._risk_scorer.update_factor("network_anomalies", min(1.0, recent_anomalies / 5))

        # Attack pattern factor
        pattern_count = sum(
            1 for p in self._active_predictions
            if p.prediction_type == ThreatPredictionType.ATTACK_PATTERN.value
        )
        self._risk_scorer.update_factor("attack_patterns", min(1.0, pattern_count / 3))

        # Active predictions factor
        self._risk_scorer.update_factor(
            "active_predictions", min(1.0, len(self._active_predictions) / 10)
        )

        # Historical accuracy
        if self._stats.total_predictions > 0:
            accuracy = self._stats.accurate_predictions / self._stats.total_predictions
            self._risk_scorer.update_factor("historical_accuracy", 1.0 - accuracy)

        self._stats.risk_score = self._risk_scorer.calculate_risk()

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def get_predictions(self, active_only: bool = True, limit: int = 20) -> List[Dict]:
        if active_only:
            return [p.to_dict() for p in self._active_predictions[-limit:]]
        return [p.to_dict() for p in list(self._predictions)[-limit:]]

    def get_risk_score(self) -> float:
        return self._risk_scorer.calculate_risk()

    def get_risk_level(self) -> str:
        return self._risk_scorer.get_risk_level()

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "stats": self._stats.to_dict(),
            "risk_score": self._risk_scorer.calculate_risk(),
            "risk_level": self._risk_scorer.get_risk_level(),
            "risk_factors": self._risk_scorer.get_factors(),
            "active_predictions": len(self._active_predictions),
            "baselines_tracked": self._anomaly_detector.baseline_count,
            "attack_patterns": self._pattern_recognizer.pattern_count,
            "recent_predictions": [p.summary() for p in self._active_predictions[-5:]],
        }

    def get_summary(self) -> str:
        status = self.get_status()
        lines = [
            f"Running: {status['running']}",
            f"Risk Score: {status['risk_score']:.1f}/10 ({status['risk_level']})",
            f"Active Predictions: {status['active_predictions']}",
            f"Total Predictions: {self._stats.total_predictions}",
            f"Anomalies Detected: {self._stats.total_anomalies_detected}",
            f"Patterns Recognized: {self._stats.total_patterns_recognized}",
            f"Baselines Tracked: {status['baselines_tracked']}",
            f"Attack Patterns Known: {status['attack_patterns']}",
        ]
        if self._active_predictions:
            lines.append(f"Latest: {self._active_predictions[-1].summary()}")
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _save_state(self):
        try:
            state = {
                "stats": self._stats.to_dict(),
                "saved_at": datetime.now().isoformat(),
            }
            (self._data_dir / "threat_model_state.json").write_text(
                json.dumps(state, indent=2, default=str), encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Failed to save threat model state: {e}")

    def _load_state(self):
        try:
            state_file = self._data_dir / "threat_model_state.json"
            if state_file.exists():
                data = json.loads(state_file.read_text(encoding="utf-8"))
                for k, v in data.get("stats", {}).items():
                    if hasattr(self._stats, k):
                        setattr(self._stats, k, v)
        except Exception as e:
            logger.warning(f"Could not load threat model state: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

threat_modeler = PredictiveThreatModeler()

def get_threat_modeler() -> PredictiveThreatModeler:
    return threat_modeler
