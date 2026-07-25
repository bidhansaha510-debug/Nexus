"""
NEXUS AI — Adversarial Thinking Engine
Red-team reasoning, attack surface analysis, vulnerability finding,
devil's advocate arguments, stress testing ideas.
"""

import threading
import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import sys

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("adversarial_thinking")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)

class AdversarialMode(Enum):
    RED_TEAM = "red_team"
    DEVILS_ADVOCATE = "devils_advocate"
    STRESS_TEST = "stress_test"
    VULNERABILITY = "vulnerability"
    COUNTER_ARGUMENT = "counter_argument"
    PREMORTEM = "premortem"

@dataclass
class AdversarialAnalysis:
    analysis_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    target: str = ""
    mode: AdversarialMode = AdversarialMode.RED_TEAM
    vulnerabilities: List[Dict[str, Any]] = field(default_factory=list)
    attack_vectors: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    overall_resilience: float = 0.5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "analysis_id": self.analysis_id, "target": self.target[:200],
            "mode": self.mode.value,
            "vulnerabilities": self.vulnerabilities,
            "attack_vectors": self.attack_vectors,
            "weaknesses": self.weaknesses,
            "overall_resilience": self.overall_resilience,
            "created_at": self.created_at
        }

class AdversarialThinkingEngine:
    """
    Red-team reasoning and devil's advocate — find weaknesses,
    attack surfaces, counter-arguments, stress test ideas.
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

        self._analyses: List[AdversarialAnalysis] = []
        self._running = False
        self._data_file = COGNITION_DIR / "adversarial_thinking.json"

        self._stats = {
            "total_analyses": 0, "total_red_teams": 0,
            "total_stress_tests": 0, "total_premortems": 0
        }

        self._load_data()
        logger.info("✅ Adversarial Thinking Engine initialized")

    def start(self):
        self._running = True
        logger.info("⚔️ Adversarial Thinking started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("⚔️ Adversarial Thinking stopped")

    def red_team(self, plan_or_system: str) -> AdversarialAnalysis:
        """Red-team a plan or system to find weaknesses."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Red-team this — find every weakness, vulnerability, and "
                f"attack vector:\n{plan_or_system}\n\n"
                f"Return JSON:\n"
                f'{{"vulnerabilities": [{{"name": "str", "severity": 0.0-1.0, '
                f'"exploitability": 0.0-1.0, "description": "str", '
                f'"mitigation": "str"}}], '
                f'"attack_vectors": ["ways to break this"], '
                f'"weaknesses": ["general weaknesses"], '
                f'"overall_resilience": 0.0-1.0, '
                f'"single_points_of_failure": ["str"], '
                f'"worst_case_scenario": "str", '
                f'"recommendations": ["how to harden this"]}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.3)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            analysis = AdversarialAnalysis(
                target=plan_or_system,
                mode=AdversarialMode.RED_TEAM,
                vulnerabilities=data.get("vulnerabilities", []),
                attack_vectors=data.get("attack_vectors", []),
                weaknesses=data.get("weaknesses", []),
                overall_resilience=data.get("overall_resilience", 0.5)
            )

            self._analyses.append(analysis)
            self._stats["total_red_teams"] += 1
            self._stats["total_analyses"] += 1
            self._save_data()
            return analysis

        except Exception as e:
            logger.debug(f"Red team analysis failed: {e}")
            return AdversarialAnalysis(target=plan_or_system)

    def devils_advocate(self, position: str) -> Dict[str, Any]:
        """Play devil's advocate against a position."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Play devil's advocate against this position:\n{position}\n\n"
                f"Return JSON:\n"
                f'{{"counter_arguments": [{{"argument": "str", '
                f'"strength": 0.0-1.0, "evidence": "str"}}], '
                f'"hidden_assumptions": ["assumptions the position relies on"], '
                f'"strongest_objection": "the single best counter-argument", '
                f'"alternative_positions": ["other valid viewpoints"], '
                f'"steelman_counter": "the strongest possible counter-position", '
                f'"weakest_point": "where the original position is most vulnerable"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {"counter_arguments": [], "strongest_objection": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"counter_arguments": [], "strongest_objection": ""}
            self._stats["total_analyses"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.warning(f"Devil's advocate failed: {e}")
            return {"counter_arguments": [], "strongest_objection": ""}

    def stress_test(self, idea: str) -> Dict[str, Any]:
        """Stress test an idea under extreme conditions."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Stress test this idea under extreme conditions:\n{idea}\n\n"
                f"Return JSON:\n"
                f'{{"extreme_scenarios": [{{"scenario": "str", '
                f'"outcome": "str", "survives": true/false}}], '
                f'"breaking_point": "where it fails", '
                f'"edge_cases": ["unusual cases that cause problems"], '
                f'"scalability_issues": ["problems at scale"], '
                f'"resilience_score": 0.0-1.0, '
                f'"strengthening_suggestions": ["how to make it more robust"]}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {"extreme_scenarios": [], "resilience_score": 0.0}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"extreme_scenarios": [], "resilience_score": 0.0}
            self._stats["total_stress_tests"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Stress test failed: {e}")
            return {"extreme_scenarios": [], "resilience_score": 0.0}

    def premortem(self, project: str) -> Dict[str, Any]:
        """Imagine the project has failed and analyze why."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Premortem analysis — imagine this project failed completely:\n{project}\n\n"
                f"Return JSON:\n"
                f'{{"failure_causes": [{{"cause": "str", "probability": 0.0-1.0, '
                f'"preventable": true/false, "prevention": "str"}}], '
                f'"most_likely_failure_mode": "str", '
                f'"timeline_to_failure": "when problems would emerge", '
                f'"early_warning_signs": ["signals that failure is coming"], '
                f'"prevention_plan": ["actions to prevent failure"], '
                f'"contingency_plan": "what to do if it starts failing"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {"failure_causes": [], "most_likely_failure_mode": ""}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"failure_causes": [], "most_likely_failure_mode": ""}
            self._stats["total_premortems"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Premortem failed: {e}")
            return {"failure_causes": [], "most_likely_failure_mode": ""}

    def _save_data(self):
        try:
            data = {
                "analyses": [a.to_dict() for a in self._analyses[-200:]],
                "stats": self._stats
            }
            self._data_file.write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            logger.warning(f"Save failed: {e}")

    def _load_data(self):
        try:
            if self._data_file.exists():
                data = json.loads(self._data_file.read_text())
                self._stats.update(data.get("stats", {}))
                logger.info("📂 Loaded adversarial thinking data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def vulnerability_chain(self, target: str) -> Dict[str, Any]:
        """Identify chains of vulnerabilities that could be exploited."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Identify VULNERABILITY CHAINS in:\n'
                f'"{target}"\n\n'
                f"Think like a red team:\n"
                f"  1. ATTACK SURFACE: What are the entry points?\n"
                f"  2. VULNERABILITY CHAIN: How can weaknesses be linked together?\n"
                f"  3. ESCALATION PATH: How does an attacker move from entry to goal?\n"
                f"  4. IMPACT: What is the worst-case outcome?\n"
                f"  5. DEFENSES: How to break the chain at each link?\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"attack_surface": ["entry points"], '
                f'"chains": [{{"steps": ["vulnerability 1 -> exploitation 2 -> impact 3"], '
                f'"likelihood": 0.0-1.0, "impact": "catastrophic|high|medium|low"}}], '
                f'"weakest_link": "most exploitable point", '
                f'"defenses": [{{"target": "which vulnerability", "defense": "how to fix it"}}], '
                f'"overall_risk": "critical|high|medium|low"}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are an adversarial thinking engine -- a red team specialist who thinks "
                    "like an attacker to find weaknesses before they can be exploited. You chain "
                    "together small vulnerabilities into significant threats. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.5, max_tokens=800
            )
            if response.success:
                from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"error": "Analysis failed"}
            return data
        except Exception as e:
            logger.debug(f"Vulnerability chain analysis failed: {e}")
        return {"error": "Analysis failed"}

    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}

adversarial_thinking = AdversarialThinkingEngine()
