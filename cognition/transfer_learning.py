"""
NEXUS AI — Transfer Learning Engine
Apply knowledge from one domain to another,
cross-domain skill mapping, learning acceleration.
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
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("transfer_learning")

COGNITION_DIR = DATA_DIR / "cognition"
COGNITION_DIR.mkdir(parents=True, exist_ok=True)


class TransferType(Enum):
    NEAR = "near"        # Similar domains
    FAR = "far"          # Distant domains
    NEGATIVE = "negative"  # Harmful transfer
    ANALOGICAL = "analogical"
    STRUCTURAL = "structural"
    PROCEDURAL = "procedural"


@dataclass
class KnowledgeTransfer:
    transfer_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    source_domain: str = ""
    target_domain: str = ""
    transfer_type: TransferType = TransferType.NEAR
    transferred_knowledge: List[str] = field(default_factory=list)
    adaptations_needed: List[str] = field(default_factory=list)
    transfer_effectiveness: float = 0.5
    risks: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "transfer_id": self.transfer_id,
            "source_domain": self.source_domain,
            "target_domain": self.target_domain,
            "transfer_type": self.transfer_type.value,
            "transferred_knowledge": self.transferred_knowledge,
            "adaptations_needed": self.adaptations_needed,
            "transfer_effectiveness": self.transfer_effectiveness,
            "risks": self.risks,
            "created_at": self.created_at
        }


class TransferLearningEngine:
    """
    Apply knowledge from one domain to another — cross-domain
    skill mapping, learning acceleration, adaptation strategies.
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

        self._transfers: List[KnowledgeTransfer] = []
        self._running = False
        self._data_file = COGNITION_DIR / "transfer_learning.json"

        self._stats = {
            "total_transfers": 0, "total_skill_maps": 0,
            "total_learning_plans": 0, "avg_effectiveness": 0.0
        }

        self._load_data()
        logger.info("✅ Transfer Learning Engine initialized")

    def start(self):
        self._running = True
        logger.info("🔄 Transfer Learning started")

    def stop(self):
        self._running = False
        self._save_data()
        logger.info("🔄 Transfer Learning stopped")

    def transfer(self, source_domain: str, target_domain: str) -> KnowledgeTransfer:
        """Transfer knowledge from source domain to target domain."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Transfer knowledge between domains:\n"
                f"Source: {source_domain}\nTarget: {target_domain}\n\n"
                f"Return JSON:\n"
                f'{{"transfer_type": "near|far|analogical|structural|procedural", '
                f'"transferred_knowledge": ["concepts/skills that transfer well"], '
                f'"adaptations_needed": ["modifications needed for the new domain"], '
                f'"transfer_effectiveness": 0.0-1.0, '
                f'"risks": ["potential negative transfer issues"], '
                f'"key_mappings": {{"source_concept": "target_equivalent"}}, '
                f'"learning_shortcut": "fastest way to leverage source knowledge"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {}

            tt_map = {t.value: t for t in TransferType}

            transfer = KnowledgeTransfer(
                source_domain=source_domain,
                target_domain=target_domain,
                transfer_type=tt_map.get(data.get("transfer_type", "near"), TransferType.NEAR),
                transferred_knowledge=data.get("transferred_knowledge", []),
                adaptations_needed=data.get("adaptations_needed", []),
                transfer_effectiveness=data.get("transfer_effectiveness", 0.5),
                risks=data.get("risks", [])
            )

            self._transfers.append(transfer)
            self._stats["total_transfers"] += 1
            self._save_data()
            return transfer

        except Exception as e:
            logger.debug(f"Knowledge transfer failed: {e}")
            return KnowledgeTransfer(source_domain=source_domain, target_domain=target_domain)

    def map_skills(self, existing_skills: str, target_role: str) -> Dict[str, Any]:
        """Map existing skills to a new role or domain."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Map existing skills to a new context:\n"
                f"Skills: {existing_skills}\nTarget: {target_role}\n\n"
                f"Return JSON:\n"
                f'{{"directly_applicable": ["skills that transfer 1:1"], '
                f'"partially_applicable": [{{"skill": "str", "adaptation": "str", '
                f'"transfer_rate": 0.0-1.0}}], '
                f'"gaps": ["skills needed but not present"], '
                f'"hidden_strengths": ["unexpected advantages from existing skills"], '
                f'"learning_priority": ["what to learn first"], '
                f'"estimated_ramp_up": "time estimate to become effective"}}'
            )
            response = llm.generate(prompt, max_tokens=500, temperature=0.4)
            if not response.success or not response.text:
                return {"directly_applicable": [], "gaps": []}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"directly_applicable": [], "gaps": []}
            self._stats["total_skill_maps"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Skill mapping failed: {e}")
            return {"directly_applicable": [], "gaps": []}

    def accelerate_learning(self, new_topic: str, background: str = "") -> Dict[str, Any]:
        """Create an accelerated learning plan leveraging existing knowledge."""
        try:
            from llm.llama_interface import llm
            prompt = (
                f"Create an accelerated learning plan:\n"
                f"New topic: {new_topic}\n"
                + (f"Background knowledge: {background}\n" if background else "") +
                f"\nReturn JSON:\n"
                f'{{"prerequisites_met": ["existing knowledge that helps"], '
                f'"analogies_to_leverage": ["connect new concepts to known ones"], '
                f'"learning_path": [{{"step": "str", "why": "str", '
                f'"connect_to_known": "str"}}], '
                f'"estimated_time": "str", '
                f'"efficiency_boost": "percentage faster than starting from scratch", '
                f'"common_misconceptions": ["things your background might make you assume wrongly"]}}'
            )
            response = llm.generate(prompt, max_tokens=600, temperature=0.4)
            if not response.success or not response.text:
                return {"learning_path": [], "estimated_time": "unknown"}
            from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"learning_path": [], "estimated_time": "unknown"}
            self._stats["total_learning_plans"] += 1
            self._save_data()
            return data
        except Exception as e:
            logger.debug(f"Learning acceleration failed: {e}")
            return {"learning_path": [], "estimated_time": "unknown"}

    def _save_data(self):
        try:
            data = {
                "transfers": [t.to_dict() for t in self._transfers[-200:]],
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
                logger.info("📂 Loaded transfer learning data")
        except Exception as e:
            logger.warning(f"Load failed: {e}")

    def cross_pollinate(self, domain_a: str, domain_b: str) -> Dict[str, Any]:
        """Transfer insights from one domain to solve problems in another."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'CROSS-POLLINATE between these domains:\n'
                f'SOURCE: "{domain_a}"\nTARGET: "{domain_b}"\n\n'
                f"Transfer knowledge:\n"
                f"  1. What works well in the source domain?\n"
                f"  2. What analogous problems exist in the target domain?\n"
                f"  3. How can source solutions be adapted for the target?\n"
                f"  4. What new innovations emerge from this transfer?\n\n"
                f"Respond ONLY with JSON:\n"
                f'{{"source_insights": ["key principles from source domain"], '
                f'"target_problems": ["problems in target domain"], '
                f'"transfers": [{{"source_principle": "what", "target_application": "how to apply", '
                f'"adaptation_needed": "what must change"}}], '
                f'"novel_innovations": ["genuinely new ideas from the transfer"], '
                f'"feasibility": 0.0-1.0}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a transfer learning engine -- you identify deep structural patterns "
                    "in one domain and apply them to solve problems in another. You are inspired "
                    "by biomimicry, cross-disciplinary innovation, and analogical reasoning. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.7, max_tokens=800
            )
            if response.success:
                from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                return {"error": "Transfer failed"}
            return data
        except Exception as e:
            logger.debug(f"Cross-pollination failed: {e}")
        return {"error": "Transfer failed"}


    def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, **self._stats}


transfer_learning = TransferLearningEngine()