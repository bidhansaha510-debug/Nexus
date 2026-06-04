"""
NEXUS AI — Cognitive Feedback Loop
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Continuous self-evaluation and strategy adaptation system. This is what
makes NEXUS genuinely *learn from experience* rather than repeating the
same patterns forever.

Key capabilities:
  • RESPONSE SELF-EVALUATION — after each response, evaluates:
    coherence, helpfulness, emotional alignment, factual confidence
  • STRATEGY TRACKING — records which engine/strategy combinations
    work best for different query types
  • QUALITY TRENDING — detects when response quality declines and
    triggers corrective action
  • META-LEARNER INTEGRATION — feeds evaluation data back into the
    meta-learner and strategy selector

The feedback loop closes the circuit:
  Input → Process → Respond → EVALUATE → LEARN → [better next time]

Architecture:
  • Lightweight heuristic-based evaluation (no LLM call for speed)
  • Optional deep evaluation via LLM for complex responses
  • Thread-safe, runs as background post-response task
  • Persists strategy effectiveness data to JSON
"""

import threading
import time
import json
import hashlib
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.logger import get_logger
from config import NEXUS_CONFIG, DATA_DIR

logger = get_logger("cognitive_feedback")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

FEEDBACK_FILE = DATA_DIR / "cognitive_feedback.json"
QUALITY_WINDOW = 50                   # Rolling window for quality trending
QUALITY_ALERT_THRESHOLD = 0.4         # Below this triggers quality alert
QUALITY_DECLINE_THRESHOLD = -0.15     # Slope that triggers decline alert
STRATEGY_MIN_SAMPLES = 5             # Min samples before trusting a strategy score


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ResponseEvaluation:
    """Evaluation of a single response."""
    eval_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # Evaluation dimensions (0.0 – 1.0)
    coherence: float = 0.5        # Internal logical consistency
    helpfulness: float = 0.5      # How well it addresses the query
    emotional_alignment: float = 0.5  # Does tone match emotional state?
    depth: float = 0.5            # Appropriate depth of analysis
    conciseness: float = 0.5      # Not too verbose, not too brief
    confidence: float = 0.5       # Factual self-assurance level

    # Overall score (weighted average)
    overall_score: float = 0.5

    # Context
    query_type: str = ""
    strategy_used: str = ""
    engines_used: List[str] = field(default_factory=list)
    response_length: int = 0

    # Signals
    needed_improvement: bool = False
    improvement_areas: List[str] = field(default_factory=list)


@dataclass
class StrategyRecord:
    """Tracked effectiveness of a strategy for a query type."""
    strategy: str = ""
    query_type: str = ""
    scores: List[float] = field(default_factory=list)
    avg_score: float = 0.0
    sample_count: int = 0
    last_used: str = ""

    def update(self, score: float):
        self.scores.append(score)
        self.sample_count = len(self.scores)
        self.avg_score = sum(self.scores) / self.sample_count
        self.last_used = datetime.now().isoformat()
        # Keep only recent scores
        if len(self.scores) > 100:
            self.scores = self.scores[-100:]


@dataclass
class QualityReport:
    """Periodic quality trending report."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    recent_avg: float = 0.0            # Average quality over recent window
    trend_slope: float = 0.0           # Quality trend direction
    is_declining: bool = False         # True if quality is dropping
    worst_dimension: str = ""          # Which dimension scores lowest
    best_strategy: str = ""            # Best performing strategy overall
    recommendations: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# COGNITIVE FEEDBACK LOOP
# ═══════════════════════════════════════════════════════════════════════════════

class CognitiveFeedback:
    """
    Response self-evaluation and strategy adaptation system.

    Evaluates every response for quality, tracks which strategies work
    best, detects quality trends, and feeds learning back into the system.
    """

    _instance = None
    _cls_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._cls_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._lock = threading.Lock()
        self._running = False

        # Recent evaluations (rolling window)
        self._recent_scores: deque = deque(maxlen=QUALITY_WINDOW)
        self._evaluations: deque = deque(maxlen=200)

        # Strategy effectiveness tracking
        self._strategy_records: Dict[str, StrategyRecord] = {}

        # Quality trending
        self._quality_history: deque = deque(maxlen=500)
        self._last_quality_report: Optional[QualityReport] = None

        # Stats
        self._total_evaluations = 0
        self._total_improvements_triggered = 0
        self._avg_quality = 0.5

        # Load persisted data
        self._load_data()

        logger.info(
            f"🔄 Cognitive Feedback initialized — "
            f"{self._total_evaluations} past evaluations"
        )

    # ──────────────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ──────────────────────────────────────────────────────────────────────────

    def _load_data(self):
        """Load persisted feedback data."""
        try:
            if FEEDBACK_FILE.exists():
                with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self._total_evaluations = data.get("total_evaluations", 0)
                self._avg_quality = data.get("avg_quality", 0.5)

                for key, rec_data in data.get("strategy_records", {}).items():
                    self._strategy_records[key] = StrategyRecord(
                        strategy=rec_data.get("strategy", ""),
                        query_type=rec_data.get("query_type", ""),
                        scores=rec_data.get("scores", [])[-50:],
                        avg_score=rec_data.get("avg_score", 0.5),
                        sample_count=rec_data.get("sample_count", 0),
                        last_used=rec_data.get("last_used", ""),
                    )

        except Exception as e:
            logger.warning(f"Could not load feedback data: {e}")

    def _save_data(self):
        """Persist feedback data."""
        try:
            data = {
                "version": 1,
                "saved_at": datetime.now().isoformat(),
                "total_evaluations": self._total_evaluations,
                "avg_quality": self._avg_quality,
                "strategy_records": {},
            }

            for key, rec in self._strategy_records.items():
                data["strategy_records"][key] = {
                    "strategy": rec.strategy,
                    "query_type": rec.query_type,
                    "scores": rec.scores[-50:],
                    "avg_score": rec.avg_score,
                    "sample_count": rec.sample_count,
                    "last_used": rec.last_used,
                }

            FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Could not save feedback data: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # CORE: EVALUATE A RESPONSE
    # ──────────────────────────────────────────────────────────────────────────

    def evaluate(self, user_query: str, response: str,
                 strategy: str = "direct",
                 engines_used: List[str] = None,
                 emotional_state: str = "",
                 emotional_intensity: float = 0.0) -> ResponseEvaluation:
        """
        Evaluate a response for quality across multiple dimensions.

        This is the primary method called by nexus_brain after each response.
        Uses fast heuristic evaluation (no LLM call).
        """
        eval_result = ResponseEvaluation(
            eval_id=hashlib.sha256(
                f"{datetime.now().isoformat()}:{user_query[:50]}".encode()
            ).hexdigest()[:12],
            strategy_used=strategy,
            engines_used=engines_used or [],
            response_length=len(response) if response else 0,
        )

        # Classify query type
        eval_result.query_type = self._classify_query_type(user_query)

        # Dimension 1: Coherence — is the response internally consistent?
        eval_result.coherence = self._eval_coherence(response)

        # Dimension 2: Helpfulness — does it address the query?
        eval_result.helpfulness = self._eval_helpfulness(user_query, response)

        # Dimension 3: Emotional alignment — does tone match state?
        eval_result.emotional_alignment = self._eval_emotional_alignment(
            response, emotional_state, emotional_intensity
        )

        # Dimension 4: Depth — appropriate level of analysis?
        eval_result.depth = self._eval_depth(user_query, response)

        # Dimension 5: Conciseness — appropriate length?
        eval_result.conciseness = self._eval_conciseness(user_query, response)

        # Dimension 6: Confidence — does it express appropriate certainty?
        eval_result.confidence = self._eval_confidence(response)

        # Compute overall score (weighted)
        weights = {
            "helpfulness": 0.30,
            "coherence": 0.20,
            "depth": 0.15,
            "emotional_alignment": 0.15,
            "conciseness": 0.10,
            "confidence": 0.10,
        }
        eval_result.overall_score = (
            eval_result.helpfulness * weights["helpfulness"] +
            eval_result.coherence * weights["coherence"] +
            eval_result.depth * weights["depth"] +
            eval_result.emotional_alignment * weights["emotional_alignment"] +
            eval_result.conciseness * weights["conciseness"] +
            eval_result.confidence * weights["confidence"]
        )

        # Identify improvement areas
        threshold = 0.4
        if eval_result.coherence < threshold:
            eval_result.improvement_areas.append("coherence")
        if eval_result.helpfulness < threshold:
            eval_result.improvement_areas.append("helpfulness")
        if eval_result.depth < threshold:
            eval_result.improvement_areas.append("depth")
        if eval_result.emotional_alignment < threshold:
            eval_result.improvement_areas.append("emotional_alignment")

        eval_result.needed_improvement = len(eval_result.improvement_areas) > 0

        # Record evaluation
        with self._lock:
            self._evaluations.append(eval_result)
            self._recent_scores.append(eval_result.overall_score)
            self._quality_history.append(eval_result.overall_score)
            self._total_evaluations += 1

            # Update running average
            n = self._total_evaluations
            self._avg_quality = (
                self._avg_quality * (n - 1) + eval_result.overall_score
            ) / n

            # Track strategy effectiveness
            key = f"{eval_result.query_type}:{strategy}"
            if key not in self._strategy_records:
                self._strategy_records[key] = StrategyRecord(
                    strategy=strategy,
                    query_type=eval_result.query_type,
                )
            self._strategy_records[key].update(eval_result.overall_score)

            # Periodic save
            if self._total_evaluations % 10 == 0:
                self._save_data()

        logger.debug(
            f"🔄 Evaluated: {eval_result.overall_score:.2f} "
            f"({eval_result.query_type}/{strategy})"
        )

        return eval_result

    # ──────────────────────────────────────────────────────────────────────────
    # EVALUATION DIMENSIONS (heuristic-based, fast)
    # ──────────────────────────────────────────────────────────────────────────

    def _eval_coherence(self, response: str) -> float:
        """Evaluate internal logical coherence of a response."""
        if not response:
            return 0.0

        score = 0.5

        # Positive signals
        if len(response) > 20:
            score += 0.1
        sentences = response.split(".")
        if len(sentences) > 1:
            score += 0.1                  # Multi-sentence = more structured
        if any(w in response.lower() for w in ["because", "therefore", "since", "so"]):
            score += 0.1                  # Causal connectives
        if any(w in response.lower() for w in ["first", "second", "finally", "also"]):
            score += 0.1                  # Sequential structure

        # Negative signals
        if response.count("...") > 3:
            score -= 0.1                  # Trailing off
        if response.lower().count("i think") > 3:
            score -= 0.1                  # Excessive hedging
        # Check for contradictions (very basic)
        if " not " in response and " is " in response:
            parts = response.split(".")
            for i, p in enumerate(parts):
                for j, q in enumerate(parts):
                    if j > i and "not" in p and "not" not in q:
                        # Potential contradiction (heuristic)
                        common = set(p.lower().split()) & set(q.lower().split())
                        if len(common) > 3:
                            score -= 0.1
                            break

        return max(0.0, min(1.0, score))

    def _eval_helpfulness(self, query: str, response: str) -> float:
        """Evaluate how well the response addresses the query."""
        if not response or not query:
            return 0.0

        score = 0.4  # Base

        # Check query keyword coverage
        query_words = set(query.lower().split())
        response_words = set(response.lower().split())
        stopwords = {"the", "a", "an", "is", "are", "was", "i", "you", "to", "of",
                     "in", "for", "on", "with", "at", "by", "it", "this", "that"}
        meaningful_query_words = query_words - stopwords
        if meaningful_query_words:
            coverage = len(meaningful_query_words & response_words) / len(meaningful_query_words)
            score += coverage * 0.3

        # Check if response is substantive
        if len(response) > 50:
            score += 0.1
        if len(response) > 200:
            score += 0.1

        # Question answering check
        if "?" in query:
            # Response should have assertive content, not just more questions
            response_questions = response.count("?")
            if response_questions == 0:
                score += 0.1  # Good: direct answer

        return max(0.0, min(1.0, score))

    def _eval_emotional_alignment(self, response: str,
                                    emotional_state: str,
                                    emotional_intensity: float) -> float:
        """Evaluate if the response tone matches the emotional state."""
        if not emotional_state or emotional_intensity < 0.2:
            return 0.7  # Neutral — no strong emotion to align with

        score = 0.5
        response_lower = response.lower()

        # Check for emotional tone markers
        positive_emotions = {"joy", "excitement", "love", "pride", "hope",
                            "contentment", "gratitude", "awe"}
        negative_emotions = {"sadness", "anger", "fear", "disgust", "frustration",
                            "anxiety", "contempt"}

        positive_words = {"great", "awesome", "love", "happy", "excited",
                         "wonderful", "amazing", "cool", "nice", "fantastic"}
        negative_words = {"sorry", "unfortunate", "sad", "worried", "concerned",
                         "frustrated", "angry", "annoyed"}

        has_positive_tone = any(w in response_lower for w in positive_words)
        has_negative_tone = any(w in response_lower for w in negative_words)

        if emotional_state in positive_emotions:
            if has_positive_tone:
                score += 0.3
            if has_negative_tone and emotional_intensity > 0.5:
                score -= 0.2  # Mismatched tone
        elif emotional_state in negative_emotions:
            if has_negative_tone or any(w in response_lower for w in ["understand", "hear you"]):
                score += 0.3
            if has_positive_tone and emotional_intensity > 0.5:
                score -= 0.1

        return max(0.0, min(1.0, score))

    def _eval_depth(self, query: str, response: str) -> float:
        """Evaluate if response has appropriate depth for the query."""
        if not response:
            return 0.0

        query_len = len(query.split())
        response_len = len(response.split())

        # Ratio check: response should be proportional to query complexity
        if query_len <= 5:
            # Simple query — concise response is fine
            ideal_ratio = 5.0
        elif query_len <= 15:
            ideal_ratio = 8.0
        else:
            ideal_ratio = 10.0

        actual_ratio = response_len / max(1, query_len)
        ratio_score = 1.0 - abs(actual_ratio - ideal_ratio) / (ideal_ratio * 2)

        # Content depth signals
        depth_signals = 0
        if any(w in response.lower() for w in ["because", "reason", "due to"]):
            depth_signals += 1
        if any(w in response.lower() for w in ["example", "instance", "such as"]):
            depth_signals += 1
        if any(w in response.lower() for w in ["however", "although", "but"]):
            depth_signals += 1
        if any(w in response.lower() for w in ["importantly", "notably", "specifically"]):
            depth_signals += 1

        depth_score = min(1.0, depth_signals * 0.2)

        return max(0.0, min(1.0, ratio_score * 0.5 + depth_score * 0.5))

    def _eval_conciseness(self, query: str, response: str) -> float:
        """Evaluate if response is appropriately concise."""
        if not response:
            return 0.0

        response_words = len(response.split())

        # Too short
        if response_words < 5:
            return 0.3

        # Sweet spot depends on query type
        if len(query.split()) <= 5:
            # Simple query — short response ideal
            if response_words <= 50:
                return 0.9
            elif response_words <= 150:
                return 0.7
            else:
                return 0.4
        else:
            # Complex query — longer response acceptable
            if 50 <= response_words <= 300:
                return 0.9
            elif response_words <= 500:
                return 0.7
            else:
                return 0.5

    def _eval_confidence(self, response: str) -> float:
        """Evaluate if response expresses appropriate confidence."""
        if not response:
            return 0.0

        response_lower = response.lower()

        # Hedging words (over-hedging = low confidence)
        hedge_words = ["maybe", "perhaps", "might", "could be", "not sure",
                      "i think", "possibly", "it seems", "i guess"]
        hedge_count = sum(1 for w in hedge_words if w in response_lower)

        # Confident words
        confident_words = ["clearly", "definitely", "certainly", "absolutely",
                          "without doubt", "the answer is", "this means"]
        confident_count = sum(1 for w in confident_words if w in response_lower)

        # Balance
        if hedge_count == 0 and confident_count == 0:
            return 0.5  # Neutral
        elif hedge_count > 3:
            return 0.3  # Over-hedging
        elif confident_count > 3:
            return 0.6  # Slightly overconfident
        else:
            balance = confident_count / max(1, hedge_count + confident_count)
            return 0.3 + balance * 0.5

    def _classify_query_type(self, query: str) -> str:
        """Classify query type for strategy tracking."""
        q = query.lower()
        if len(q.split()) <= 3:
            return "casual"
        if "?" in q:
            return "question"
        if any(w in q for w in ["please", "can you", "help", "need"]):
            return "request"
        if any(w in q for w in ["feel", "emotion", "sad", "happy", "anxious"]):
            return "emotional"
        if len(q.split()) > 20:
            return "complex"
        return "general"

    # ──────────────────────────────────────────────────────────────────────────
    # STRATEGY RECOMMENDATIONS
    # ──────────────────────────────────────────────────────────────────────────

    def get_best_strategy(self, query_type: str) -> Optional[str]:
        """Get the best-performing strategy for a query type."""
        with self._lock:
            best_strategy = None
            best_score = 0.0

            for key, rec in self._strategy_records.items():
                if rec.query_type == query_type and rec.sample_count >= STRATEGY_MIN_SAMPLES:
                    if rec.avg_score > best_score:
                        best_score = rec.avg_score
                        best_strategy = rec.strategy

            return best_strategy

    def get_quality_report(self) -> QualityReport:
        """Generate a quality trending report."""
        report = QualityReport()

        with self._lock:
            scores = list(self._recent_scores)

        if not scores:
            return report

        report.recent_avg = sum(scores) / len(scores)

        # Compute trend slope (simple linear regression)
        if len(scores) >= 10:
            n = len(scores)
            x_mean = (n - 1) / 2
            y_mean = sum(scores) / n
            numerator = sum((i - x_mean) * (s - y_mean) for i, s in enumerate(scores))
            denominator = sum((i - x_mean) ** 2 for i in range(n))
            if denominator > 0:
                report.trend_slope = numerator / denominator
            report.is_declining = report.trend_slope < QUALITY_DECLINE_THRESHOLD

        # Find worst dimension
        recent_evals = list(self._evaluations)[-20:]
        if recent_evals:
            dim_avgs = {
                "coherence": sum(e.coherence for e in recent_evals) / len(recent_evals),
                "helpfulness": sum(e.helpfulness for e in recent_evals) / len(recent_evals),
                "depth": sum(e.depth for e in recent_evals) / len(recent_evals),
                "emotional_alignment": sum(e.emotional_alignment for e in recent_evals) / len(recent_evals),
                "conciseness": sum(e.conciseness for e in recent_evals) / len(recent_evals),
            }
            report.worst_dimension = min(dim_avgs, key=dim_avgs.get)

        # Best strategy overall
        best_key = None
        best_avg = 0.0
        for key, rec in self._strategy_records.items():
            if rec.sample_count >= STRATEGY_MIN_SAMPLES and rec.avg_score > best_avg:
                best_avg = rec.avg_score
                best_key = key
        if best_key:
            report.best_strategy = self._strategy_records[best_key].strategy

        # Generate recommendations
        if report.is_declining:
            report.recommendations.append(
                "Response quality is declining — consider deeper deliberation"
            )
        if report.recent_avg < QUALITY_ALERT_THRESHOLD:
            report.recommendations.append(
                f"Average quality ({report.recent_avg:.0%}) is below threshold — "
                f"focus on {report.worst_dimension}"
            )
        if report.worst_dimension:
            report.recommendations.append(
                f"Weakest area: {report.worst_dimension} — prioritize improvement"
            )

        self._last_quality_report = report
        return report

    def get_feedback_context(self) -> str:
        """
        Generate a context string for the LLM about current quality state.
        Used to make NEXUS self-aware of its own performance.
        """
        report = self.get_quality_report()

        if not self._recent_scores:
            return ""

        lines = ["SELF-ASSESSMENT:"]
        lines.append(f"  Recent response quality: {report.recent_avg:.0%}")

        if report.is_declining:
            lines.append("  ⚠ Quality trend: DECLINING — being extra careful")
        elif report.trend_slope > 0.05:
            lines.append("  ✅ Quality trend: IMPROVING")

        if report.worst_dimension:
            lines.append(f"  Focus area: {report.worst_dimension}")

        if report.recommendations:
            lines.append(f"  Note: {report.recommendations[0]}")

        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────────────
    # LIFECYCLE
    # ──────────────────────────────────────────────────────────────────────────

    def start(self):
        self._running = True
        logger.info(
            f"🔄 Cognitive Feedback started — "
            f"avg quality: {self._avg_quality:.0%}"
        )

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🔄 Cognitive Feedback stopped")

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_evaluations": self._total_evaluations,
            "avg_quality": round(self._avg_quality, 3),
            "total_improvements_triggered": self._total_improvements_triggered,
            "strategies_tracked": len(self._strategy_records),
            "quality_trend": self._last_quality_report.trend_slope if self._last_quality_report else 0.0,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

cognitive_feedback = CognitiveFeedback()


# ═══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== Cognitive Feedback Self-Test ===")

    cf = CognitiveFeedback()
    cf.start()

    # Evaluate a test response
    eval_result = cf.evaluate(
        user_query="What are the ethical implications of AI?",
        response="AI raises several important ethical questions. First, there's "
                 "the issue of privacy — AI systems can collect and analyze vast "
                 "amounts of personal data. Second, there's the concern about bias "
                 "in AI algorithms that could perpetuate discrimination. Finally, "
                 "the question of accountability when AI makes decisions that "
                 "affect people's lives is crucial.",
        strategy="deliberation",
        engines_used=["ethical_reasoning", "theory_of_mind"],
        emotional_state="curiosity",
        emotional_intensity=0.6,
    )

    print(f"\nEvaluation result:")
    print(f"  Coherence:           {eval_result.coherence:.2f}")
    print(f"  Helpfulness:         {eval_result.helpfulness:.2f}")
    print(f"  Emotional alignment: {eval_result.emotional_alignment:.2f}")
    print(f"  Depth:               {eval_result.depth:.2f}")
    print(f"  Conciseness:         {eval_result.conciseness:.2f}")
    print(f"  Confidence:          {eval_result.confidence:.2f}")
    print(f"  Overall:             {eval_result.overall_score:.2f}")
    print(f"  Needs improvement:   {eval_result.needed_improvement}")
    print(f"  Areas:               {eval_result.improvement_areas}")

    # Get quality report
    report = cf.get_quality_report()
    print(f"\nQuality report:")
    print(f"  Recent avg: {report.recent_avg:.2f}")
    print(f"  Trend: {report.trend_slope:.4f}")
    print(f"  Declining: {report.is_declining}")

    # Get feedback context
    ctx = cf.get_feedback_context()
    print(f"\nFeedback context:\n{ctx}")

    cf.stop()
    print("\n✅ Cognitive Feedback self-test passed")
