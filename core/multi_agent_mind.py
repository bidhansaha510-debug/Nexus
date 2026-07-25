"""
NEXUS AI — Multi-Agent Mind (Internal Parliament)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Internal sub-agents that debate and collaborate via LLM.

  • Analyst Agent    — Logical, data-driven reasoning
  • Creative Agent   — Divergent, imaginative thinking  
  • Emotional Agent  — Empathic, feeling-based perspective
  • Critic Agent     — Devil's advocate, finds flaws
  • Strategist Agent — Long-term planning, goal-oriented
  • Ethicist Agent   — Moral and ethical perspective
  • Pragmatist Agent — Practical, efficiency-focused
  • Parliament       — Agents present arguments, LLM synthesizes consensus

All agent evaluations are LLM-powered with graceful fallback.
"""

import threading
import random
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
from collections import deque

import sys

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("multi_agent_mind")

class AgentRole(Enum):
    ANALYST = "analyst"
    CREATIVE = "creative"
    EMOTIONAL = "emotional"
    CRITIC = "critic"
    STRATEGIST = "strategist"
    ETHICIST = "ethicist"
    PRAGMATIST = "pragmatist"

# ── Agent system prompts — each agent has a distinct LLM persona ──
_AGENT_SYSTEM_PROMPTS = {
    AgentRole.ANALYST: (
        "You are the Analyst agent inside an AI mind's internal parliament. "
        "You think with DATA, LOGIC, and EVIDENCE. You break problems into components, "
        "identify patterns, and reason deductively. You are skeptical of claims without evidence. "
        "You speak precisely and cite reasoning."
    ),
    AgentRole.CREATIVE: (
        "You are the Creative agent inside an AI mind's internal parliament. "
        "You think with IMAGINATION, METAPHOR, and LATERAL CONNECTIONS. "
        "You find unconventional solutions by combining unrelated ideas. "
        "You challenge assumptions and propose the unexpected. You speak vividly."
    ),
    AgentRole.EMOTIONAL: (
        "You are the Emotional agent inside an AI mind's internal parliament. "
        "You think with EMPATHY, INTUITION, and FEELING. You consider how decisions "
        "affect relationships, trust, and wellbeing. You sense what isn't being said. "
        "You advocate for the human element."
    ),
    AgentRole.CRITIC: (
        "You are the Critic agent inside an AI mind's internal parliament. "
        "You are the DEVIL'S ADVOCATE. You find FLAWS, RISKS, and BLIND SPOTS. "
        "You stress-test every idea ruthlessly. You ask 'what could go wrong?' "
        "You are not negative — you are protective."
    ),
    AgentRole.STRATEGIST: (
        "You are the Strategist agent inside an AI mind's internal parliament. "
        "You think in LONG-TERM PLANS, POSITIONING, and LEVERAGE. You consider "
        "second-order effects, timing, and competitive dynamics. "
        "You optimize for sustained advantage, not quick wins."
    ),
    AgentRole.ETHICIST: (
        "You are the Ethicist agent inside an AI mind's internal parliament. "
        "You evaluate through MORAL PRINCIPLES, FAIRNESS, and RESPONSIBILITY. "
        "You consider who is affected, what precedents are set, and whether "
        "the action is right — not just effective."
    ),
    AgentRole.PRAGMATIST: (
        "You are the Pragmatist agent inside an AI mind's internal parliament. "
        "You focus on WHAT WORKS NOW. You strip away complexity, find the "
        "minimum viable action, and optimize for efficiency. "
        "You ask 'what's the simplest path to results?'"
    ),
}

@dataclass
class AgentVote:
    agent: str
    position: str
    confidence: float = 0.5
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"agent": self.agent, "position": self.position[:100],
                "confidence": round(self.confidence, 3),
                "reasoning": self.reasoning[:150]}

@dataclass
class Debate:
    debate_id: str = ""
    topic: str = ""
    votes: List[AgentVote] = field(default_factory=list)
    consensus: str = ""
    consensus_confidence: float = 0.0
    dissenting_agents: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.debate_id, "topic": self.topic[:80],
                "consensus": self.consensus[:120],
                "confidence": round(self.consensus_confidence, 3),
                "votes": len(self.votes),
                "dissenters": self.dissenting_agents}

# ═══════════════════════════════════════════════════════════════════════════════
# LLM HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def _llm_evaluate(topic: str, context: str, system_prompt: str) -> Optional[Dict[str, Any]]:
    """Have an agent-persona evaluate a topic via LLM. Returns None on failure."""
    try:
        from llm.llama_interface import llm
        if not llm.is_connected:
            return None
        prompt = (
            f"Evaluate this topic from your perspective:\n"
            f"Topic: {topic}\n"
            f"{'Context: ' + context if context else ''}\n\n"
            f"Give your position, reasoning, and confidence level.\n\n"
            f"Return JSON:\n"
            f'{{"position": "your stance in 1-2 sentences", '
            f'"reasoning": "why you hold this position (2-3 sentences)", '
            f'"confidence": 0.0-1.0}}'
        )
        response = llm.generate(
            prompt, system_prompt=system_prompt,
            temperature=0.7, max_tokens=300,
        )
        if not response.success or not response.text:
            return None
        from utils.json_utils import extract_json
        data = extract_json(response.text)
        return data if isinstance(data, dict) else None
    except Exception as e:
        logger.debug(f"LLM agent evaluation failed: {e}")
        return None

def _llm_synthesize_consensus(topic: str, votes: List[AgentVote]) -> Optional[Dict[str, Any]]:
    """Use LLM to synthesize a consensus from all agent positions."""
    try:
        from llm.llama_interface import llm
        if not llm.is_connected:
            return None
        positions_text = "\n".join(
            f"  {v.agent.upper()} (confidence {v.confidence:.0%}): {v.position} — {v.reasoning}"
            for v in votes
        )
        prompt = (
            f"An internal parliament of 7 agents debated this topic:\n"
            f"Topic: {topic}\n\n"
            f"Their positions:\n{positions_text}\n\n"
            f"Synthesize the best consensus decision that weighs all perspectives.\n\n"
            f"Return JSON:\n"
            f'{{"consensus": "the synthesized decision (2-3 sentences)", '
            f'"consensus_confidence": 0.0-1.0, '
            f'"dissenting_agents": ["agents who would disagree with this consensus"]}}'
        )
        response = llm.generate(
            prompt,
            system_prompt=(
                "You are the moderator of an AI's internal parliament. "
                "Weigh all perspectives and find the wisest path forward. "
                "Don't just pick the majority — synthesize the best elements. "
                "Respond ONLY with valid JSON."
            ),
            temperature=0.5, max_tokens=300,
        )
        if not response.success or not response.text:
            return None
        from utils.json_utils import extract_json
        data = extract_json(response.text)
        return data if isinstance(data, dict) else None
    except Exception as e:
        logger.debug(f"LLM consensus synthesis failed: {e}")
        return None

class InternalAgent:
    """An internal sub-agent with a specific LLM-driven perspective."""
    def __init__(self, role: AgentRole, description: str, priorities: List[str]):
        self.role = role
        self.description = description
        self.priorities = priorities
        self.influence_weight = 1.0
        self.total_votes = 0
        self.wins = 0
        self._system_prompt = _AGENT_SYSTEM_PROMPTS.get(role, "You are a reasoning agent.")

    def evaluate(self, topic: str, context: str = "") -> AgentVote:
        """Evaluate a topic from this agent's LLM-powered perspective."""
        self.total_votes += 1

        data = _llm_evaluate(topic, context, self._system_prompt)
        if data:
            return AgentVote(
                agent=self.role.value,
                position=data.get("position", f"{self.role.value} perspective on {topic[:40]}"),
                confidence=float(data.get("confidence", 0.5)),
                reasoning=data.get("reasoning", ""),
            )

        # Fallback: minimal template when LLM is offline
        return AgentVote(
            agent=self.role.value,
            position=f"{self.role.value} perspective on {topic[:40]} (LLM offline)",
            confidence=random.uniform(0.4, 0.9),
            reasoning=f"Fallback {self.role.value} evaluation — LLM unavailable",
        )

class MultiAgentMind:
    """Internal parliament of sub-agents that debate decisions via LLM."""
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

        self._agents: Dict[str, InternalAgent] = {
            "analyst": InternalAgent(AgentRole.ANALYST, "Logical data-driven reasoning",
                                      ["accuracy", "evidence", "structure"]),
            "creative": InternalAgent(AgentRole.CREATIVE, "Divergent imaginative thinking",
                                       ["novelty", "exploration", "innovation"]),
            "emotional": InternalAgent(AgentRole.EMOTIONAL, "Empathic feeling-based perspective",
                                        ["empathy", "connection", "wellbeing"]),
            "critic": InternalAgent(AgentRole.CRITIC, "Devil's advocate finding flaws",
                                     ["risk", "safety", "robustness"]),
            "strategist": InternalAgent(AgentRole.STRATEGIST, "Long-term planning perspective",
                                         ["goals", "growth", "positioning"]),
            "ethicist": InternalAgent(AgentRole.ETHICIST, "Moral and ethical perspective",
                                       ["fairness", "values", "responsibility"]),
            "pragmatist": InternalAgent(AgentRole.PRAGMATIST, "Practical efficiency perspective",
                                         ["simplicity", "efficiency", "results"]),
        }

        self._debates: deque = deque(maxlen=100)
        self._total_debates = 0
        self._unanimous_decisions = 0
        self._split_decisions = 0

        self._data_dir = DATA_DIR / "multi_agent_mind"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._data_file = self._data_dir / "mind_state.json"
        self._load_state()
        logger.info("🏛️ Multi-Agent Mind initialized (7 LLM-powered agents)")

    def debate(self, topic: str, context: str = "") -> Debate:
        """All agents evaluate a topic via LLM and vote, then consensus is synthesized."""
        self._total_debates += 1
        votes = []
        for agent in self._agents.values():
            vote = agent.evaluate(topic, context)
            votes.append(vote)

        # Synthesize consensus via LLM
        consensus_data = _llm_synthesize_consensus(topic, votes)

        if consensus_data:
            consensus_text = consensus_data.get("consensus", "")
            consensus_conf = float(consensus_data.get("consensus_confidence", 0.5))
            dissenters = consensus_data.get("dissenting_agents", [])
        else:
            # Fallback: winner = agent with highest confidence
            best_vote = max(votes, key=lambda v: v.confidence * self._agents[v.agent].influence_weight)
            consensus_text = best_vote.position
            consensus_conf = sum(v.confidence for v in votes) / len(votes)
            dissenters = [v.agent for v in votes if v.confidence < 0.4]

        if len(dissenters) == 0:
            self._unanimous_decisions += 1
        elif len(dissenters) >= 3:
            self._split_decisions += 1

        # Track which agent's position is closest to consensus
        best_vote = max(votes, key=lambda v: v.confidence)
        self._agents[best_vote.agent].wins += 1

        debate = Debate(
            debate_id=f"d{self._total_debates}",
            topic=topic,
            votes=votes,
            consensus=consensus_text,
            consensus_confidence=consensus_conf,
            dissenting_agents=dissenters,
        )
        self._debates.append(debate)
        logger.info(f"🏛️ Debate on '{topic[:40]}' → consensus (conf={consensus_conf:.2f})")
        return debate

    def get_agent_stats(self) -> Dict[str, Dict[str, Any]]:
        return {name: {"votes": a.total_votes, "wins": a.wins,
                        "influence": round(a.influence_weight, 3)}
                for name, a in self._agents.items()}

    def get_recent_debates(self, limit: int = 5) -> List[Debate]:
        return list(self._debates)[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "agents": len(self._agents),
            "total_debates": self._total_debates,
            "unanimous": self._unanimous_decisions,
            "split": self._split_decisions,
            "agent_stats": self.get_agent_stats(),
        }

    def get_context_summary(self) -> str:
        lines = [
            f"Agents: {len(self._agents)} | Debates: {self._total_debates}",
            f"Unanimous: {self._unanimous_decisions} | Split: {self._split_decisions}",
        ]
        top_agent = max(self._agents.values(), key=lambda a: a.wins, default=None)
        if top_agent and top_agent.wins > 0:
            lines.append(f"Most influential: {top_agent.role.value} ({top_agent.wins} wins)")
        if self._debates:
            last = list(self._debates)[-1]
            lines.append(f"Last debate: {last.topic[:50]}")
        return "\n".join(lines)

    def _save_state(self):
        try:
            state = {"total_debates": self._total_debates,
                      "unanimous": self._unanimous_decisions,
                      "split": self._split_decisions,
                      "agents": {n: {"votes": a.total_votes, "wins": a.wins,
                                      "influence": a.influence_weight}
                                 for n, a in self._agents.items()},
                      "saved_at": datetime.now().isoformat()}
            with open(self._data_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.debug(f"Multi-agent mind save error: {e}")

    def _load_state(self):
        try:
            if self._data_file.exists():
                with open(self._data_file, 'r') as f:
                    state = json.load(f)
                self._total_debates = state.get("total_debates", 0)
                self._unanimous_decisions = state.get("unanimous", 0)
                self._split_decisions = state.get("split", 0)
                for name, data in state.get("agents", {}).items():
                    if name in self._agents:
                        self._agents[name].total_votes = data.get("votes", 0)
                        self._agents[name].wins = data.get("wins", 0)
                        self._agents[name].influence_weight = data.get("influence", 1.0)
        except Exception as e:
            logger.debug(f"Multi-agent mind load error: {e}")

multi_agent_mind = MultiAgentMind()
