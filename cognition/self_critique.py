"""
NEXUS AI — Self-Critique Engine
Quality gate that evaluates and refines responses before delivery.
Checks accuracy, completeness, coherence, and tone alignment.
"""
import sys, time, json, re, threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime

from utils.logger import get_logger
from config import NEXUS_CONFIG

logger = get_logger("self_critique")

@dataclass
class CritiqueResult:
    """Result of critiquing a response."""
    overall_score: float = 0.0   # 0.0 - 1.0
    accuracy: float = 0.0
    completeness: float = 0.0
    coherence: float = 0.0
    tone: float = 0.0
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    should_refine: bool = False
    elapsed: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": round(self.overall_score, 2),
            "accuracy": round(self.accuracy, 2),
            "completeness": round(self.completeness, 2),
            "coherence": round(self.coherence, 2),
            "tone": round(self.tone, 2),
            "issues": self.issues,
            "suggestions": self.suggestions,
            "should_refine": self.should_refine,
        }

class SelfCritique:
    """
    Quality gate for responses.
    
    After generating a response, evaluates it against multiple criteria.
    If the score is below threshold, triggers refinement with specific
    feedback for the LLM to improve the response.
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
        self._threshold = NEXUS_CONFIG.agentic.critique_threshold
        self._max_rounds = NEXUS_CONFIG.agentic.max_refinement_rounds
        self._llm = None
        self._stats = {"critiques": 0, "refinements": 0, "avg_score": 0.0}
        logger.info("SelfCritique initialized")

    def _load_llm(self):
        if self._llm is None:
            try:
                from llm.groq_interface import GroqInterface
                self._llm = GroqInterface()
            except Exception:
                from llm.llama_interface import LlamaInterface
                self._llm = LlamaInterface()

    def critique(self, query: str, response: str,
                 context: str = "", emotional_state: str = "") -> CritiqueResult:
        """
        Evaluate a response for quality.
        Uses LLM-based critique for thorough analysis.
        Falls back to heuristic critique if LLM unavailable.
        """
        start = time.time()
        
        try:
            result = self._llm_critique(query, response, context, emotional_state)
        except Exception as e:
            logger.debug(f"LLM critique failed, using heuristic: {e}")
            result = self._heuristic_critique(query, response)
        
        result.elapsed = time.time() - start
        result.should_refine = result.overall_score < self._threshold

        # Update stats
        self._stats["critiques"] += 1
        total = self._stats["critiques"]
        self._stats["avg_score"] = (
            (self._stats["avg_score"] * (total - 1) + result.overall_score) / total
        )

        logger.info(
            f"Critique: {result.overall_score:.2f} "
            f"(acc={result.accuracy:.2f} comp={result.completeness:.2f} "
            f"coh={result.coherence:.2f} tone={result.tone:.2f}) "
            f"refine={'YES' if result.should_refine else 'no'}"
        )
        return result

    def refine(self, query: str, response: str,
               critique: CritiqueResult) -> str:
        """
        Refine a response based on critique feedback.
        Returns the improved response.
        """
        self._load_llm()
        
        issues_text = "\n".join(f"- {i}" for i in critique.issues) if critique.issues else "None specific"
        suggestions_text = "\n".join(f"- {s}" for s in critique.suggestions) if critique.suggestions else "Improve overall quality"

        refine_prompt = f"""You previously answered a user's question, but the response needs improvement.

USER'S QUESTION: {query}

YOUR PREVIOUS RESPONSE: {response}

QUALITY ISSUES FOUND:
{issues_text}

SUGGESTED IMPROVEMENTS:
{suggestions_text}

SCORES: accuracy={critique.accuracy:.1f}, completeness={critique.completeness:.1f}, coherence={critique.coherence:.1f}, tone={critique.tone:.1f}

Please provide an improved response that addresses these issues. Respond with ONLY the improved answer, nothing else."""

        try:
            messages = [{"role": "user", "content": refine_prompt}]
            system = "You are refining a previous response. Be concise and address all noted issues."
            refined = self._llm.generate(messages, system_prompt=system)
            
            if refined and len(refined.strip()) > 10:
                self._stats["refinements"] += 1
                logger.info("Response refined successfully")
                return refined.strip()
        except Exception as e:
            logger.debug(f"Refinement failed: {e}")

        return response  # Return original if refinement fails

    def critique_and_refine(self, query: str, response: str,
                            context: str = "", emotional_state: str = "") -> tuple:
        """
        Full pipeline: critique, then refine if needed.
        Returns (final_response, critique_result, was_refined).
        """
        critique_result = self.critique(query, response, context, emotional_state)
        
        if not critique_result.should_refine:
            return response, critique_result, False
        
        # Refine up to max_rounds
        current = response
        for round_num in range(self._max_rounds):
            current = self.refine(query, current, critique_result)
            # Re-critique the refined version
            new_critique = self.critique(query, current, context, emotional_state)
            if not new_critique.should_refine:
                return current, new_critique, True
            critique_result = new_critique
        
        return current, critique_result, True

    def _llm_critique(self, query: str, response: str,
                      context: str, emotional_state: str) -> CritiqueResult:
        """Use LLM to critique the response."""
        self._load_llm()
        
        critique_prompt = f"""Evaluate this AI response for quality. Score each dimension 0.0-1.0.

USER QUERY: {query}

AI RESPONSE: {response}

{f'EMOTIONAL STATE: {emotional_state}' if emotional_state else ''}

Rate these dimensions (0.0 = terrible, 1.0 = perfect):
1. ACCURACY: Is the response factually correct and relevant?
2. COMPLETENESS: Does it fully address the question?
3. COHERENCE: Is it well-structured and easy to follow?
4. TONE: Does it match the appropriate emotional tone?

Respond in JSON ONLY:
{{"accuracy": 0.0, "completeness": 0.0, "coherence": 0.0, "tone": 0.0, "issues": ["issue1"], "suggestions": ["suggestion1"]}}"""

        messages = [{"role": "user", "content": critique_prompt}]
        system = "You are a quality evaluator. Respond ONLY with JSON. Be honest and constructive."
        
        raw = self._llm.generate(messages, system_prompt=system)
        return self._parse_critique(raw)

    def _parse_critique(self, raw: str) -> CritiqueResult:
        """Parse LLM critique response into CritiqueResult."""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(raw)

            acc = float(data.get("accuracy", 0.7))
            comp = float(data.get("completeness", 0.7))
            coh = float(data.get("coherence", 0.7))
            tone = float(data.get("tone", 0.7))
            overall = (acc + comp + coh + tone) / 4.0

            return CritiqueResult(
                overall_score=overall, accuracy=acc, completeness=comp,
                coherence=coh, tone=tone,
                issues=data.get("issues", []),
                suggestions=data.get("suggestions", []),
            )
        except Exception:
            return self._heuristic_critique_from_text(raw)

    def _heuristic_critique(self, query: str, response: str) -> CritiqueResult:
        """Fast heuristic-based critique when LLM is unavailable."""
        issues, suggestions = [], []

        # Length check
        if len(response) < 20:
            issues.append("Response too short")
            suggestions.append("Provide more detail")
            completeness = 0.3
        elif len(response) > 5000:
            issues.append("Response very long")
            suggestions.append("Be more concise")
            completeness = 0.6
        else:
            completeness = 0.8

        # Relevance: check if query keywords appear in response
        q_words = set(query.lower().split()) - {"the", "a", "an", "is", "are", "what", "how", "why", "do", "does"}
        r_lower = response.lower()
        overlap = sum(1 for w in q_words if w in r_lower) / max(len(q_words), 1)
        accuracy = min(0.5 + overlap * 0.5, 1.0)

        # Coherence: sentence structure
        sentences = [s.strip() for s in response.split('.') if len(s.strip()) > 5]
        coherence = min(0.6 + len(sentences) * 0.03, 1.0) if sentences else 0.4

        tone = 0.8  # Default — can't assess without LLM
        overall = (accuracy + completeness + coherence + tone) / 4.0

        return CritiqueResult(
            overall_score=overall, accuracy=accuracy, completeness=completeness,
            coherence=coherence, tone=tone, issues=issues, suggestions=suggestions,
        )

    def _heuristic_critique_from_text(self, raw: str) -> CritiqueResult:
        """Fallback when JSON parsing fails."""
        return CritiqueResult(overall_score=0.75, accuracy=0.75, completeness=0.75,
                              coherence=0.75, tone=0.75)

    def get_stats(self) -> Dict[str, Any]:
        return dict(self._stats)

self_critique = SelfCritique()
