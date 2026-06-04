"""
NEXUS AI — Persistent Skill Acquisition
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

When NEXUS successfully solves a novel problem, it extracts the
reasoning strategy as a reusable "skill" and stores it permanently.

On future similar queries, matching skills are injected as context:
"Here's how you solved this before" — enabling genuine learning
from experience rather than solving everything from scratch.

Architecture:
  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
  │ Successful   │───▶│ Skill        │───▶│ Skill        │
  │ Agentic Run  │    │ Extractor    │    │ Store        │
  └──────────────┘    └──────────────┘    └──────────────┘
                                                │
  ┌──────────────┐    ┌──────────────┐          │
  │ Future Query │───▶│ Skill        │◀─────────┘
  │              │    │ Matcher      │
  └──────────────┘    └──────────────┘
"""

import json
import threading
import hashlib
import uuid
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATA_DIR
from utils.logger import get_logger

logger = get_logger("skill_memory")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Skill:
    """A reusable problem-solving pattern extracted from experience."""
    skill_id: str = field(default_factory=lambda: str(uuid.uuid4())[:10])
    name: str = ""
    description: str = ""

    # Matching
    trigger_keywords: List[str] = field(default_factory=list)
    query_type: str = "unknown"
    trigger_pattern: str = ""  # Natural language description of when to use

    # The strategy
    strategy_name: str = ""
    strategy_steps: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    cognitive_engines_used: List[str] = field(default_factory=list)

    # Example
    example_query: str = ""
    example_response_summary: str = ""

    # Performance
    times_used: int = 0
    times_succeeded: int = 0
    avg_quality_score: float = 0.0
    total_quality_score: float = 0.0

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_used: str = ""

    @property
    def success_rate(self) -> float:
        if self.times_used == 0:
            return 0.0
        return self.times_succeeded / self.times_used

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["success_rate"] = self.success_rate
        return d

    def to_prompt_context(self) -> str:
        """Format this skill as a prompt injection."""
        steps_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(self.strategy_steps))
        tools_text = f"\n  Tools: {', '.join(self.tools_used)}" if self.tools_used else ""

        return (
            f"[Previously Learned Skill: {self.name}]\n"
            f"When you encounter: {self.trigger_pattern}\n"
            f"Approach ({self.strategy_name}):\n"
            f"{steps_text}{tools_text}\n"
            f"Success rate: {self.success_rate:.0%} over {self.times_used} uses"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SKILL MEMORY
# ═══════════════════════════════════════════════════════════════════════════════

class SkillMemory:
    """
    Persistent storage and retrieval of learned problem-solving skills.

    Core operations:
    1. extract_skill() — After a successful agentic run, extract the strategy
    2. match_skills() — Find relevant skills for a new query
    3. record_usage() — Track how well a skill works when reused
    """

    _instance = None
    _lock = threading.Lock()

    SKILL_QUALITY_THRESHOLD = 0.65  # Min critique score to extract a skill
    MAX_SKILLS = 200
    MAX_SKILLS_PER_QUERY = 3

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._data_dir = Path(DATA_DIR) / "skill_memory"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._skills: List[Skill] = []
        self._keyword_index: Dict[str, List[str]] = defaultdict(list)  # keyword → [skill_id]

        self._load_data()
        self._rebuild_index()

        logger.info(f"[SKILL-MEMORY] Initialized with {len(self._skills)} learned skills")

    # ─────────────────────────────────────────────────────────────────────────
    # SKILL EXTRACTION
    # ─────────────────────────────────────────────────────────────────────────

    def extract_skill(
        self,
        query: str,
        response: str,
        quality_score: float,
        strategy_name: str = "direct",
        tools_used: List[str] = None,
        reasoning_steps: List[str] = None,
        query_type: str = "unknown",
    ) -> Optional[Skill]:
        """
        Extract a reusable skill from a successful interaction.

        Only extracts if quality_score > threshold and the query
        represents a novel problem type.
        """
        if quality_score < self.SKILL_QUALITY_THRESHOLD:
            return None

        if strategy_name == "direct":
            return None  # Direct responses aren't interesting skills

        # Check for duplicate skills
        if self._is_duplicate(query, strategy_name):
            return None

        # Extract keywords from the query for future matching
        keywords = self._extract_keywords(query)

        # Generate a skill name and description
        name = self._generate_skill_name(query, query_type)
        trigger = self._generate_trigger_pattern(query, query_type)

        # Build the strategy steps
        steps = reasoning_steps or [
            f"Use {strategy_name} reasoning approach",
            "Break the problem into components",
            "Solve each component",
            "Synthesize the final answer",
        ]

        skill = Skill(
            name=name,
            description=f"Learned from solving: {query[:100]}",
            trigger_keywords=keywords,
            query_type=query_type,
            trigger_pattern=trigger,
            strategy_name=strategy_name,
            strategy_steps=steps[:6],  # Cap at 6 steps
            tools_used=tools_used or [],
            example_query=query[:200],
            example_response_summary=response[:200],
            times_used=1,
            times_succeeded=1,
            avg_quality_score=quality_score,
            total_quality_score=quality_score,
        )

        self._skills.append(skill)

        # Enforce max skills (remove lowest performing)
        if len(self._skills) > self.MAX_SKILLS:
            self._skills.sort(key=lambda s: s.avg_quality_score * (s.times_used ** 0.5))
            self._skills = self._skills[-self.MAX_SKILLS:]

        self._rebuild_index()
        self._save_data()

        logger.info(f"[SKILL-MEMORY] Skill extracted: '{name}' "
                   f"(strategy={strategy_name}, score={quality_score:.2f})")

        return skill

    def _is_duplicate(self, query: str, strategy: str) -> bool:
        """Check if a similar skill already exists."""
        query_keywords = set(self._extract_keywords(query))
        for skill in self._skills:
            if skill.strategy_name != strategy:
                continue
            overlap = len(query_keywords & set(skill.trigger_keywords))
            if overlap >= len(query_keywords) * 0.7:
                return True
        return False

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract matching keywords from text."""
        # Simple keyword extraction — remove stop words and short words
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "shall", "can", "to", "of", "in", "for",
            "on", "with", "at", "by", "from", "as", "into", "through", "during",
            "before", "after", "above", "below", "between", "under", "and", "but",
            "or", "nor", "not", "so", "yet", "both", "either", "neither", "each",
            "every", "all", "any", "few", "more", "most", "other", "some", "such",
            "no", "only", "same", "than", "too", "very", "just", "because", "this",
            "that", "these", "those", "i", "me", "my", "you", "your", "it", "its",
            "we", "they", "them", "what", "which", "who", "how", "when", "where",
            "why", "if", "then", "else", "about",
        }

        words = text.lower().split()
        # Remove punctuation and filter
        keywords = []
        for w in words:
            w = w.strip(".,!?;:'\"()[]{}").strip()
            if len(w) > 2 and w not in stop_words:
                keywords.append(w)

        return keywords[:15]  # Cap at 15 keywords

    def _generate_skill_name(self, query: str, query_type: str) -> str:
        """Generate a concise name for the skill."""
        # Take first few meaningful words
        keywords = self._extract_keywords(query)[:4]
        if keywords:
            return f"{query_type.title()}: {' '.join(keywords[:3]).title()}"
        return f"{query_type.title()} Skill"

    def _generate_trigger_pattern(self, query: str, query_type: str) -> str:
        """Generate a natural language description of when to use this skill."""
        templates = {
            "math": "a mathematical or calculation question involving",
            "coding": "a coding/programming task involving",
            "debugging": "a debugging or error-fixing task involving",
            "planning": "a planning or design question about",
            "analysis": "an analytical question requiring evaluation of",
            "creative": "a creative task involving",
            "philosophical": "a philosophical or abstract question about",
            "technical": "a technical explanation question about",
            "factual": "a factual question about",
        }
        prefix = templates.get(query_type, "a question about")
        keywords = self._extract_keywords(query)[:4]
        return f"{prefix} {', '.join(keywords)}"

    # ─────────────────────────────────────────────────────────────────────────
    # SKILL MATCHING
    # ─────────────────────────────────────────────────────────────────────────

    def match_skills(self, query: str, query_type: str = None) -> List[Skill]:
        """
        Find relevant skills for a new query.

        Uses keyword overlap + query type matching.
        Returns top matching skills sorted by relevance.
        """
        query_keywords = set(self._extract_keywords(query))
        if not query_keywords:
            return []

        scored_skills: List[tuple] = []

        for skill in self._skills:
            score = 0.0

            # Keyword overlap score (0-1)
            skill_keywords = set(skill.trigger_keywords)
            if skill_keywords:
                overlap = len(query_keywords & skill_keywords)
                keyword_score = overlap / max(len(query_keywords), 1)
                score += keyword_score * 0.6

            # Query type match bonus
            if query_type and skill.query_type == query_type:
                score += 0.25

            # Performance bonus — prefer skills that work well
            if skill.times_used > 0:
                performance = skill.avg_quality_score * min(1.0, skill.times_used / 5.0)
                score += performance * 0.15

            if score > 0.2:  # Minimum relevance threshold
                scored_skills.append((score, skill))

        # Sort by score, return top N
        scored_skills.sort(key=lambda x: x[0], reverse=True)
        return [skill for _, skill in scored_skills[:self.MAX_SKILLS_PER_QUERY]]

    def get_skill_context(self, query: str, query_type: str = None) -> str:
        """
        Get matching skills formatted as prompt context.

        This is the primary integration point — called during context assembly.
        """
        matched = self.match_skills(query, query_type)
        if not matched:
            return ""

        sections = []
        for skill in matched:
            sections.append(skill.to_prompt_context())

        return "\n\n[Learned Skills — Apply if Relevant]\n" + \
               "\n\n".join(sections)

    # ─────────────────────────────────────────────────────────────────────────
    # USAGE TRACKING
    # ─────────────────────────────────────────────────────────────────────────

    def record_usage(self, skill_id: str, quality_score: float) -> None:
        """Record that a skill was used and how well it performed."""
        for skill in self._skills:
            if skill.skill_id == skill_id:
                skill.times_used += 1
                skill.total_quality_score += quality_score
                skill.avg_quality_score = skill.total_quality_score / skill.times_used
                skill.last_used = datetime.now().isoformat()

                if quality_score >= self.SKILL_QUALITY_THRESHOLD:
                    skill.times_succeeded += 1

                logger.debug(f"[SKILL-MEMORY] Skill '{skill.name}' used "
                           f"(score={quality_score:.2f}, total_uses={skill.times_used})")

                self._save_data()
                return

    # ─────────────────────────────────────────────────────────────────────────
    # INDEX
    # ─────────────────────────────────────────────────────────────────────────

    def _rebuild_index(self) -> None:
        """Rebuild the keyword → skill index."""
        self._keyword_index.clear()
        for skill in self._skills:
            for keyword in skill.trigger_keywords:
                self._keyword_index[keyword].append(skill.skill_id)

    # ─────────────────────────────────────────────────────────────────────────
    # PERSISTENCE
    # ─────────────────────────────────────────────────────────────────────────

    def _save_data(self) -> None:
        """Save skills to disk."""
        try:
            data = {
                "skills": [s.to_dict() for s in self._skills],
                "saved_at": datetime.now().isoformat(),
            }
            path = self._data_dir / "skills.json"
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"[SKILL-MEMORY] Save failed: {e}")

    def _load_data(self) -> None:
        """Load skills from disk."""
        try:
            path = self._data_dir / "skills.json"
            if not path.exists():
                return

            with open(path, "r") as f:
                data = json.load(f)

            for sd in data.get("skills", []):
                # Filter to valid fields only
                valid_fields = {k for k in Skill.__dataclass_fields__}
                filtered = {k: v for k, v in sd.items() if k in valid_fields}
                self._skills.append(Skill(**filtered))

        except Exception as e:
            logger.warning(f"[SKILL-MEMORY] Load failed (starting fresh): {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # PUBLIC STATS
    # ─────────────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get skill memory statistics."""
        by_type = defaultdict(int)
        for s in self._skills:
            by_type[s.query_type] += 1

        return {
            "total_skills": len(self._skills),
            "total_keywords_indexed": len(self._keyword_index),
            "skills_by_query_type": dict(by_type),
            "avg_success_rate": (
                sum(s.success_rate for s in self._skills) / max(1, len(self._skills))
            ),
            "most_used_skills": [
                {"name": s.name, "uses": s.times_used, "score": round(s.avg_quality_score, 2)}
                for s in sorted(self._skills, key=lambda x: x.times_used, reverse=True)[:5]
            ],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

skill_memory = SkillMemory()
