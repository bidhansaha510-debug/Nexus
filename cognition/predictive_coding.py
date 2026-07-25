"""
NEXUS AI — Predictive Coding Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Prediction-error minimization framework — LLM-powered.

  • Prediction Generator  — Use LLM to predict what users/events will do
  • Surprise Detector     — Use LLM to measure prediction error
  • Model Updater         — Adjust models when surprised
  • Anticipation Buffer   — Pre-compute likely responses
  • Curiosity from Surprise — High errors fuel curiosity
"""

import threading
import random
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
from collections import deque

import sys

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("predictive_coding")

@dataclass
class Prediction:
    prediction_id: str = ""
    domain: str = ""            # "user_response", "system_event", "emotional_shift"
    prediction: str = ""
    confidence: float = 0.5
    actual_outcome: str = ""
    prediction_error: float = 0.0   # 0 = perfect, 1 = completely wrong
    surprise_level: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {"domain": self.domain, "prediction": self.prediction[:100],
                "confidence": round(self.confidence, 3),
                "error": round(self.prediction_error, 3),
                "surprise": round(self.surprise_level, 3),
                "resolved": self.resolved}

# ═══════════════════════════════════════════════════════════════════════════════
# LLM HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _llm_predict(domain: str, context: str) -> Optional[Dict[str, Any]]:
    """Use LLM to generate an actual prediction."""
    try:
        from llm.llama_interface import llm
        if not llm.is_connected:
            return None
        prompt = (
            f"Based on the current context, predict what will happen next.\n"
            f"Domain: {domain}\n"
            f"Context: {context}\n\n"
            f"Make a specific, testable prediction — not a vague guess.\n\n"
            f"Return JSON:\n"
            f'{{"prediction": "what you predict will happen (specific)", '
            f'"confidence": 0.0-1.0, '
            f'"reasoning": "why you predict this"}}'
        )
        response = llm.generate(
            prompt,
            system_prompt=(
                "You are a prediction engine. Make specific, falsifiable predictions "
                "based on patterns in the context. Be calibrated — high confidence only "
                "for clear patterns. Respond ONLY with valid JSON."
            ),
            temperature=0.4, max_tokens=300,
        )
        if not response.success or not response.text:
            return None
        from utils.json_utils import extract_json
        data = extract_json(response.text)
        return data if isinstance(data, dict) else None
    except Exception as e:
        logger.debug(f"LLM prediction failed: {e}")
        return None

def _llm_compute_error(prediction: str, actual_outcome: str) -> Optional[Dict[str, Any]]:
    """Use LLM to compare prediction vs. actual outcome and compute semantic error."""
    try:
        from llm.llama_interface import llm
        if not llm.is_connected:
            return None
        prompt = (
            f"Compare this prediction with what actually happened:\n"
            f"PREDICTION: {prediction}\n"
            f"ACTUAL OUTCOME: {actual_outcome}\n\n"
            f"Rate how wrong the prediction was.\n\n"
            f"Return JSON:\n"
            f'{{"prediction_error": 0.0-1.0, '
            f'"surprise_level": 0.0-1.0, '
            f'"analysis": "brief explanation of accuracy (1 sentence)"}}'
        )
        response = llm.generate(
            prompt,
            system_prompt=(
                "You are an accuracy evaluator. Compare predictions to actual outcomes "
                "and rate the error. 0.0 = perfectly accurate. 1.0 = completely wrong. "
                "Consider semantic similarity, not just exact match. "
                "Respond ONLY with valid JSON."
            ),
            temperature=0.2, max_tokens=200,
        )
        if not response.success or not response.text:
            return None
        from utils.json_utils import extract_json
        data = extract_json(response.text)
        return data if isinstance(data, dict) else None
    except Exception as e:
        logger.debug(f"LLM error computation failed: {e}")
        return None

class PredictiveCoding:
    """Prediction-error minimization: predict, compare, learn from surprise. LLM-powered."""
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

        # ── State ──
        self._predictions: deque = deque(maxlen=200)
        self._pending_predictions: Dict[str, Prediction] = {}
        self._anticipation_buffer: deque = deque(maxlen=50)
        self._total_predictions = 0
        self._total_resolved = 0
        self._total_surprises = 0  # predictions with error > 0.5
        self._cumulative_error = 0.0
        self._average_error = 0.5
        self._current_surprise = 0.0
        self._surprise_trend: deque = deque(maxlen=100)

        # ── Domain Models (accuracy per domain) ──
        self._domain_accuracy: Dict[str, Dict[str, float]] = {
            "user_response": {"correct": 0, "total": 0, "accuracy": 0.5},
            "system_event": {"correct": 0, "total": 0, "accuracy": 0.5},
            "emotional_shift": {"correct": 0, "total": 0, "accuracy": 0.5},
            "conversation_flow": {"correct": 0, "total": 0, "accuracy": 0.5},
            "user_behavior": {"correct": 0, "total": 0, "accuracy": 0.5},
        }

        self._data_dir = DATA_DIR / "predictive_coding"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._data_file = self._data_dir / "predictive_state.json"
        self._load_state()
        logger.info("🔮 Predictive Coding Engine initialized")

    # ─── Make Predictions ────────────────────────────────────────────────────

    def predict(self, domain: str, prediction_text: str, confidence: float = 0.5) -> Prediction:
        """Make a prediction about what will happen next."""
        self._total_predictions += 1
        pred = Prediction(
            prediction_id=f"p{self._total_predictions}",
            domain=domain, prediction=prediction_text,
            confidence=min(1.0, max(0.0, confidence)),
        )
        self._predictions.append(pred)
        self._pending_predictions[pred.prediction_id] = pred
        return pred

    def predict_from_context(self, domain: str, context: str) -> Prediction:
        """Use LLM to generate an actual prediction from context."""
        self._total_predictions += 1

        data = _llm_predict(domain, context)
        if data:
            pred = Prediction(
                prediction_id=f"p{self._total_predictions}",
                domain=domain,
                prediction=data.get("prediction", ""),
                confidence=float(data.get("confidence", 0.5)),
            )
        else:
            pred = Prediction(
                prediction_id=f"p{self._total_predictions}",
                domain=domain,
                prediction=f"Unable to predict — LLM offline (domain: {domain})",
                confidence=0.3,
            )

        self._predictions.append(pred)
        self._pending_predictions[pred.prediction_id] = pred
        return pred

    def anticipate(self, situation: str, likely_responses: List[str]):
        """Pre-compute anticipated responses for a situation."""
        for resp in likely_responses[:5]:
            self._anticipation_buffer.append({
                "situation": situation[:100], "response": resp[:200],
                "timestamp": datetime.now().isoformat(),
            })

    # ─── Resolve Predictions ─────────────────────────────────────────────────

    def resolve(self, prediction_id: str, actual_outcome: str, error: float = None) -> float:
        """Resolve a prediction with what actually happened. Uses LLM to compute error if not given."""
        pred = self._pending_predictions.pop(prediction_id, None)
        if pred is None:
            return 0.0

        pred.actual_outcome = actual_outcome
        pred.resolved = True

        if error is not None:
            # Explicit error provided
            pred.prediction_error = error
        else:
            # Use LLM to compute semantic error
            error_data = _llm_compute_error(pred.prediction, actual_outcome)
            if error_data:
                pred.prediction_error = float(error_data.get("prediction_error", 0.5))
                pred.surprise_level = float(error_data.get("surprise_level", 0.0))
            else:
                # Fallback: simple heuristic — if text has overlap, lower error
                pred_words = set(pred.prediction.lower().split())
                outcome_words = set(actual_outcome.lower().split())
                if pred_words and outcome_words:
                    overlap = len(pred_words & outcome_words) / max(len(pred_words | outcome_words), 1)
                    pred.prediction_error = max(0.0, 1.0 - overlap)
                else:
                    pred.prediction_error = 0.5

        pred.surprise_level = max(pred.surprise_level, max(0, pred.prediction_error - (1 - pred.confidence)))
        self._total_resolved += 1

        # Update running stats
        self._cumulative_error += pred.prediction_error
        self._average_error = self._cumulative_error / max(1, self._total_resolved)
        self._current_surprise = pred.surprise_level
        self._surprise_trend.append(pred.surprise_level)

        # Count surprises
        if pred.prediction_error > 0.5:
            self._total_surprises += 1

        # Update domain accuracy
        domain = pred.domain
        if domain in self._domain_accuracy:
            self._domain_accuracy[domain]["total"] += 1
            if pred.prediction_error < 0.3:
                self._domain_accuracy[domain]["correct"] += 1
            total = self._domain_accuracy[domain]["total"]
            correct = self._domain_accuracy[domain]["correct"]
            self._domain_accuracy[domain]["accuracy"] = correct / max(1, total)

        return pred.surprise_level

    def auto_resolve_stale(self, max_age_seconds: float = 300):
        """Auto-resolve predictions older than max_age with default error."""
        now = datetime.now()
        stale = []
        for pid, pred in self._pending_predictions.items():
            try:
                created = datetime.fromisoformat(pred.timestamp)
                if (now - created).total_seconds() > max_age_seconds:
                    stale.append(pid)
            except Exception:
                pass
        for pid in stale:
            self.resolve(pid, "auto-resolved (expired)", error=0.5)

    # ─── Surprise & Curiosity ────────────────────────────────────────────────

    def get_surprise_level(self) -> float:
        return self._current_surprise

    def get_curiosity_signal(self) -> float:
        """High prediction errors fuel curiosity."""
        if not self._surprise_trend:
            return 0.3
        recent = list(self._surprise_trend)[-10:]
        avg_surprise = sum(recent) / len(recent)
        return min(1.0, avg_surprise * 1.5)

    # ─── Getters ─────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_predictions": self._total_predictions,
            "total_resolved": self._total_resolved,
            "pending": len(self._pending_predictions),
            "total_surprises": self._total_surprises,
            "average_error": round(self._average_error, 3),
            "current_surprise": round(self._current_surprise, 3),
            "curiosity_signal": round(self.get_curiosity_signal(), 3),
            "domain_accuracy": {k: round(v["accuracy"], 3) for k, v in self._domain_accuracy.items()},
            "anticipation_buffer": len(self._anticipation_buffer),
        }

    def get_context_summary(self) -> str:
        lines = [
            f"Predictions: {self._total_predictions} ({len(self._pending_predictions)} pending)",
            f"Avg error: {self._average_error:.0%} | Surprises: {self._total_surprises}",
            f"Curiosity signal: {self.get_curiosity_signal():.0%}",
        ]
        best_domain = max(self._domain_accuracy.items(), key=lambda x: x[1]["accuracy"], default=None)
        if best_domain and best_domain[1]["total"] > 0:
            lines.append(f"Best domain: {best_domain[0]} ({best_domain[1]['accuracy']:.0%})")
        return "\n".join(lines)

    def _save_state(self):
        try:
            state = {"total_predictions": self._total_predictions,
                      "total_resolved": self._total_resolved,
                      "total_surprises": self._total_surprises,
                      "cumulative_error": self._cumulative_error,
                      "domain_accuracy": self._domain_accuracy,
                      "saved_at": datetime.now().isoformat()}
            with open(self._data_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.debug(f"Predictive coding save error: {e}")

    def _load_state(self):
        try:
            if self._data_file.exists():
                with open(self._data_file, 'r') as f:
                    state = json.load(f)
                self._total_predictions = state.get("total_predictions", 0)
                self._total_resolved = state.get("total_resolved", 0)
                self._total_surprises = state.get("total_surprises", 0)
                self._cumulative_error = state.get("cumulative_error", 0)
                if self._total_resolved > 0:
                    self._average_error = self._cumulative_error / self._total_resolved
                for k, v in state.get("domain_accuracy", {}).items():
                    if k in self._domain_accuracy:
                        self._domain_accuracy[k] = v
        except Exception as e:
            logger.debug(f"Predictive coding load error: {e}")

predictive_coding = PredictiveCoding()
