"""
NEXUS AI — Semantic Intent Classifier
Hybrid intent detection: embeddings + keywords + LLM fallback.

Architecture:
  • Layer 1: Fast keyword scan (< 1ms) — catches explicit intent
  • Layer 2: Semantic similarity (< 50ms) — catches implicit intent
  • Layer 3: LLM classification — only when layers 1+2 are ambiguous

This solves the critical bottleneck where keyword-only matching fails to
detect implicit reasoning needs like:
  - "My friend died yesterday" → emotional support needed
  - "I'm struggling with purpose" → philosophical/existential
  - "Is democracy failing?" → political/ethical analysis
  - "How do computers actually think?" → philosophical/technical
"""

import re
import threading
import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
from collections import OrderedDict

# Handle optional numpy import gracefully since it's required for semantic embeddings
try:
    import numpy as np
except ImportError:
    np = None

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger
from cognition.engine_registry import ENGINE_REGISTRY, ALL_ENGINE_KEYS

logger = get_logger("intent_classifier")


# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE SEMANTIC DESCRIPTIONS
# ═══════════════════════════════════════════════════════════════════════════════
# These descriptions capture the *essence* of what each engine handles,
# enabling semantic matching for implicit intent detection.

ENGINE_DESCRIPTIONS: Dict[str, Dict[str, Any]] = {
    # ─── Reasoning Engines ───
    "causal": {
        "description": "Understanding why things happen, cause-effect relationships, root causes, consequences, diagnosing problems, explaining reasons behind events",
        "examples": [
            "why did this happen",
            "what caused this",
            "root cause analysis",
            "consequence of actions",
            "chain of events",
        ],
        "keywords": ["cause", "effect", "why", "because", "reason", "consequence", "result", "due to"],
    },
    "decision": {
        "description": "Making choices between options, weighing tradeoffs, analyzing pros and cons, decision support, cost-benefit analysis, selecting best alternatives",
        "examples": [
            "should I choose",
            "which option is better",
            "weighing my options",
            "pros and cons",
            "difficult choice",
        ],
        "keywords": ["choose", "decide", "option", "choice", "should", "better", "tradeoff", "alternative"],
    },
    "ethics": {
        "description": "Questions about right and wrong, moral dilemmas, fairness, justice, ethical implications, what ought to be, principles of conduct",
        "examples": [
            "is this morally right",
            "ethical dilemma",
            "what's the right thing to do",
            "moral implications",
            "fairness and justice",
        ],
        "keywords": ["moral", "ethical", "right", "wrong", "fair", "justice", "dilemma", "should"],
    },
    "logic": {
        "description": "Valid reasoning, logical arguments, detecting fallacies, syllogisms, deduction, induction, proof construction, rational analysis",
        "examples": [
            "is this argument valid",
            "logical fallacy",
            "does this follow",
            "prove that",
            "rational reasoning",
        ],
        "keywords": ["logic", "valid", "argument", "fallacy", "proof", "rational", "deduction", "reasoning"],
    },
    "probability": {
        "description": "Uncertainty quantification, likelihood estimation, chances, odds, risk assessment, Bayesian reasoning, statistical thinking",
        "examples": [
            "how likely is this",
            "what are the odds",
            "probability of success",
            "risk assessment",
            "uncertain outcome",
        ],
        "keywords": ["probability", "likely", "chance", "odds", "risk", "uncertain", "statistics"],
    },
    "hypothesis": {
        "description": "Generating and testing hypotheses, scientific reasoning, explaining observations, designing experiments, falsification, theory building",
        "examples": [
            "my theory is",
            "possible explanation",
            "test this hypothesis",
            "why might this be",
            "scientific investigation",
        ],
        "keywords": ["hypothesis", "theory", "explain", "test", "experiment", "evidence", "investigate"],
    },
    "counterfactual": {
        "description": "What-if scenarios, alternate realities, imagining different outcomes, regret analysis, counterfactual thinking, possible worlds",
        "examples": [
            "what if I had done",
            "alternate outcome",
            "could have been different",
            "if only",
            "imagining alternatives",
        ],
        "keywords": ["what if", "imagine if", "alternate", "counterfactual", "could have", "would have"],
    },
    "dialectic": {
        "description": "Examining opposing viewpoints, thesis and antithesis, steelmanning arguments, Socratic questioning, dialectical reasoning",
        "examples": [
            "both sides of the argument",
            "strongest counterargument",
            "thesis and antithesis",
            "Socratic dialogue",
            "opposing perspective",
        ],
        "keywords": ["opposing", "both sides", "counterargument", "thesis", "antithesis", "dialectical"],
    },
    "philosophy": {
        "description": "Deep existential questions, consciousness, free will, meaning of life, metaphysics, epistemology, ontology, philosophical inquiry",
        "examples": [
            "what is the meaning of life",
            "do we have free will",
            "nature of consciousness",
            "existential questions",
            "philosophical inquiry",
        ],
        "keywords": ["philosophy", "meaning", "existence", "consciousness", "free will", "metaphysics", "ontology"],
    },

    # ─── Intelligence Engines ───
    "emotional": {
        "description": "Understanding and responding to emotions, empathy, emotional support, feelings, emotional intelligence, detecting emotional states",
        "examples": [
            "I feel so sad",
            "my friend died",
            "emotional support",
            "understanding my feelings",
            "going through a hard time",
        ],
        "keywords": ["feel", "emotion", "sad", "happy", "angry", "hurt", "pain", "grief", "joy", "struggling"],
    },
    "emotional_reg": {
        "description": "Managing emotions, emotional regulation, coping strategies, calming down, self-care, emotional balance, stress management",
        "examples": [
            "help me calm down",
            "manage my anxiety",
            "cope with stress",
            "emotional balance",
            "self-care strategies",
        ],
        "keywords": ["calm", "cope", "manage", "regulate", "stress", "anxiety", "overwhelmed", "grounding"],
    },
    "mind": {
        "description": "Understanding others' thoughts, intentions, and mental states, theory of mind, inferring what others think or feel, perspective of others",
        "examples": [
            "what are they thinking",
            "their perspective on this",
            "why would they do that",
            "understanding their motives",
            "their intentions",
        ],
        "keywords": ["they think", "their perspective", "their intention", "they feel", "understand them"],
    },
    "social": {
        "description": "Group dynamics, social influence, peer pressure, power dynamics, social norms, trust issues, manipulation detection, social situations",
        "examples": [
            "social dynamics in my group",
            "being manipulated",
            "trust issues with friends",
            "power dynamics",
            "social pressure",
        ],
        "keywords": ["social", "group", "dynamic", "influence", "trust", "manipulated", "peer", "hierarchy"],
    },
    "cultural": {
        "description": "Cross-cultural understanding, cultural context, multicultural sensitivity, cultural traditions, intercultural communication",
        "examples": [
            "cultural differences",
            "in another culture",
            "multicultural perspective",
            "cultural etiquette",
            "cross-cultural understanding",
        ],
        "keywords": ["cultural", "culture", "tradition", "multicultural", "intercultural", "etiquette"],
    },
    "linguistic": {
        "description": "Language analysis, writing style, rhetoric, tone, formality, rephrasing, persuasive communication, linguistic nuances",
        "examples": [
            "rewrite this more formally",
            "analyze the tone",
            "make this more persuasive",
            "rhetorical analysis",
            "change the style",
        ],
        "keywords": ["rewrite", "rephrase", "tone", "style", "formal", "rhetoric", "persuasive", "language"],
    },
    "narrative": {
        "description": "Storytelling, narrative structure, plot analysis, character development, moral of stories, creating narratives",
        "examples": [
            "tell me a story",
            "narrative structure",
            "character analysis",
            "plot development",
            "moral of the story",
        ],
        "keywords": ["story", "narrative", "plot", "character", "tale", "storytelling"],
    },
    "humor": {
        "description": "Understanding and generating humor, jokes, wit, comedy, making people laugh, humor analysis",
        "examples": [
            "tell me a joke",
            "make me laugh",
            "something funny",
            "witty comeback",
            "comedy analysis",
        ],
        "keywords": ["joke", "funny", "laugh", "humor", "witty", "comedy", "hilarious"],
    },
    "wisdom": {
        "description": "Life lessons, sage advice, long-term perspective, timeless wisdom, big picture thinking, deeper understanding",
        "examples": [
            "wise advice needed",
            "life lesson",
            "long-term perspective",
            "big picture understanding",
            "timeless wisdom",
        ],
        "keywords": ["wisdom", "wise", "advice", "lesson", "long-term", "perspective", "sage"],
    },

    # ─── Creative Engines ───
    "creative": {
        "description": "Generating novel ideas, brainstorming, innovative solutions, thinking outside the box, creative problem-solving",
        "examples": [
            "brainstorm ideas",
            "creative solution",
            "innovative approach",
            "think outside the box",
            "novel concept",
        ],
        "keywords": ["creative", "brainstorm", "innovative", "novel", "idea", "invent", "original"],
    },
    "dream": {
        "description": "Subconscious exploration, surreal associations, dream-like thinking, free association, unconscious connections",
        "examples": [
            "dream interpretation",
            "surreal imagery",
            "subconscious thoughts",
            "free association",
            "stream of consciousness",
        ],
        "keywords": ["dream", "surreal", "subconscious", "unconscious", "association", "imaginative"],
    },
    "music": {
        "description": "Musical understanding, melody, rhythm, harmony, song composition, musical analysis, emotional qualities of music",
        "examples": [
            "musical composition",
            "melody and harmony",
            "song analysis",
            "rhythm patterns",
            "musical mood",
        ],
        "keywords": ["music", "song", "melody", "rhythm", "harmony", "chord", "compose", "symphony"],
    },
    "visual": {
        "description": "Visual imagination, mental imagery, spatial visualization, describing scenes, diagram thinking, visual concepts",
        "examples": [
            "visualize this",
            "mental image",
            "picture this scene",
            "diagram description",
            "visual concept",
        ],
        "keywords": ["visualize", "picture", "image", "diagram", "scene", "imagine", "visual"],
    },
    "conceptual_blend": {
        "description": "Combining concepts, merging ideas, creating hybrid concepts, cross-domain synthesis, conceptual innovation",
        "examples": [
            "combine these ideas",
            "merge concepts",
            "hybrid approach",
            "fusion of ideas",
            "blend concepts",
        ],
        "keywords": ["combine", "merge", "blend", "hybrid", "fusion", "synthesize", "mashup"],
    },
    "analogy_gen": {
        "description": "Creating analogies, explaining through metaphors, simplifying complex ideas, ELI5, comparative explanations",
        "examples": [
            "explain like I'm five",
            "analogy for this",
            "metaphor for",
            "simple explanation",
            "think of it like",
        ],
        "keywords": ["analogy", "metaphor", "like", "similar", "simple", "eli5", "compare"],
    },
    "analogy": {
        "description": "Finding similarities, analogical reasoning, structural mapping, comparative analysis, applying patterns across domains",
        "examples": [
            "similar to",
            "comparable situation",
            "analogous case",
            "parallel structure",
            "same pattern",
        ],
        "keywords": ["similar", "analogous", "compare", "parallel", "like", "reminds", "pattern"],
    },

    # ─── Cognitive Engines ───
    "attention": {
        "description": "Focus management, prioritization, distraction handling, attention control, task prioritization, concentration strategies",
        "examples": [
            "can't focus",
            "help me prioritize",
            "too many distractions",
            "attention problems",
            "overwhelmed by tasks",
        ],
        "keywords": ["focus", "attention", "prioritize", "distract", "concentrate", "overwhelm", "multitask"],
    },
    "working_memory": {
        "description": "Holding information in mind, context tracking, remembering previous points, mental scratchpad, active information",
        "examples": [
            "remember this for later",
            "keep in mind",
            "what did we discuss",
            "previous context",
            "hold that thought",
        ],
        "keywords": ["remember", "context", "previous", "earlier", "discussed", "keep in mind", "recall"],
    },
    "self_model": {
        "description": "Self-awareness, capability assessment, understanding one's own abilities and limitations, self-reflection",
        "examples": [
            "can you do this",
            "what are your capabilities",
            "your limitations",
            "self-assessment",
            "know yourself",
        ],
        "keywords": ["can you", "capability", "limitation", "able to", "self", "your ability"],
    },
    "error_detect": {
        "description": "Finding mistakes, fact-checking, detecting errors, inconsistencies, verification, debugging reasoning",
        "examples": [
            "find errors in this",
            "fact check this claim",
            "what's wrong with",
            "verify accuracy",
            "is this correct",
        ],
        "keywords": ["error", "mistake", "wrong", "incorrect", "verify", "check", "fact", "bug"],
    },
    "curiosity": {
        "description": "Exploration, deep diving into topics, generating questions, intellectual curiosity, discovering more, rabbit holes",
        "examples": [
            "curious about",
            "want to know more",
            "dig deeper",
            "explore this topic",
            "tell me more",
        ],
        "keywords": ["curious", "wonder", "explore", "more", "interesting", "fascinating", "dig deeper"],
    },
    "transfer": {
        "description": "Applying knowledge across domains, transferable skills, cross-domain learning, using experience in new contexts",
        "examples": [
            "apply this elsewhere",
            "transfer this skill",
            "use in another context",
            "cross-domain application",
            "leverage experience",
        ],
        "keywords": ["apply", "transfer", "cross-domain", "use in", "leverage", "adapt"],
    },
    "perspective": {
        "description": "Taking different viewpoints, empathetic perspective, seeing from other angles, role reversal, multiple perspectives",
        "examples": [
            "from their perspective",
            "see it another way",
            "walk in their shoes",
            "different viewpoint",
            "understand their side",
        ],
        "keywords": ["perspective", "viewpoint", "angle", "side", "shoes", "empathize", "understand"],
    },
    "flexibility": {
        "description": "Cognitive flexibility, shifting perspectives, adapting thinking, paradigm shifts, alternative approaches",
        "examples": [
            "think differently",
            "another way to approach",
            "paradigm shift",
            "flexible thinking",
            "adapt my approach",
        ],
        "keywords": ["flexible", "adapt", "alternative", "shift", "different way", "reverse", "flip"],
    },
    "common_sense": {
        "description": "Practical judgment, everyday reasoning, plausibility checking, sanity checks, real-world knowledge",
        "examples": [
            "is this plausible",
            "common sense approach",
            "practical judgment",
            "does this make sense",
            "sanity check",
        ],
        "keywords": ["common sense", "practical", "plausible", "realistic", "obvious", "sensible"],
    },

    # ─── Strategic Engines ───
    "planning": {
        "description": "Creating plans, breaking down goals, step-by-step strategies, action plans, roadmaps, project planning",
        "examples": [
            "create a plan",
            "steps to achieve",
            "action plan",
            "how do I start",
            "project roadmap",
        ],
        "keywords": ["plan", "steps", "strategy", "roadmap", "action", "goal", "achieve", "project"],
    },
    "negotiation": {
        "description": "Negotiation strategy, persuasion, compromise, making deals, conflict resolution, win-win solutions",
        "examples": [
            "negotiate better terms",
            "persuade someone",
            "find compromise",
            "deal making",
            "win-win solution",
        ],
        "keywords": ["negotiate", "persuade", "compromise", "deal", "convince", "agreement", "settlement"],
    },
    "game_theory": {
        "description": "Strategic interaction, Nash equilibrium, competitive dynamics, game-theoretic analysis, optimal strategies",
        "examples": [
            "game theory analysis",
            "strategic move",
            "competitive strategy",
            "optimal play",
            "Nash equilibrium",
        ],
        "keywords": ["game theory", "strategy", "equilibrium", "competitive", "optimal", "payoff", "zero-sum"],
    },
    "adversarial": {
        "description": "Red teaming, finding vulnerabilities, adversarial thinking, security analysis, attack vectors, defensive thinking",
        "examples": [
            "red team this",
            "find weaknesses",
            "vulnerability analysis",
            "attack vectors",
            "stress test",
        ],
        "keywords": ["vulnerable", "attack", "weakness", "red team", "exploit", "security", "threat"],
    },
    "debate": {
        "description": "Building arguments, debate preparation, rebuttals, structured argumentation, persuasive discourse",
        "examples": [
            "build an argument",
            "debate preparation",
            "counter-argument",
            "rebuttal needed",
            "argue for",
        ],
        "keywords": ["debate", "argue", "argument", "rebuttal", "claim", "counter", "persuade"],
    },
    "constraint": {
        "description": "Working within constraints, feasibility analysis, optimization under limits, resource allocation",
        "examples": [
            "is this feasible",
            "optimize under constraints",
            "resource limits",
            "constrained optimization",
            "allocation problem",
        ],
        "keywords": ["constraint", "feasible", "limit", "optimize", "resource", "allocation", "restrict"],
    },
    "systems": {
        "description": "Complex systems analysis, feedback loops, emergence, interconnected parts, system dynamics, leverage points",
        "examples": [
            "system analysis",
            "feedback loops",
            "interconnected parts",
            "emergent behavior",
            "complex dynamics",
        ],
        "keywords": ["system", "complex", "interconnected", "feedback", "emergence", "ripple", "cycle"],
    },
    "synthesis": {
        "description": "Synthesizing information, summarizing, extracting insights, combining knowledge, executive summaries",
        "examples": [
            "summarize this",
            "extract key insights",
            "synthesize information",
            "bottom line",
            "key takeaways",
        ],
        "keywords": ["summarize", "synthesize", "extract", "insight", "key", "bottom line", "takeaway"],
    },

    # ─── Remaining Engines ───
    "spatial": {
        "description": "Spatial reasoning, navigation, layout, position, distance, orientation, mental maps",
        "examples": [
            "spatial arrangement",
            "navigate this space",
            "layout design",
            "position relative to",
            "distance between",
        ],
        "keywords": ["spatial", "navigate", "layout", "position", "distance", "where", "location"],
    },
    "temporal": {
        "description": "Time reasoning, duration estimation, sequencing, scheduling, timelines, chronological thinking",
        "examples": [
            "how long will this take",
            "timeline for project",
            "sequence of events",
            "time estimation",
            "schedule planning",
        ],
        "keywords": ["time", "duration", "schedule", "timeline", "sequence", "chronological", "when"],
    },
    "knowledge": {
        "description": "Knowledge integration, connecting domains, interdisciplinary thinking, knowledge graphs, finding connections",
        "examples": [
            "connect these ideas",
            "interdisciplinary approach",
            "knowledge connection",
            "relate these domains",
            "link between concepts",
        ],
        "keywords": ["knowledge", "connect", "relate", "interdisciplinary", "domain", "link", "integrate"],
    },
    "intuition": {
        "description": "Intuitive reasoning, gut feelings, pattern recognition, unconscious insights, vibes, hunches",
        "examples": [
            "gut feeling about",
            "something feels off",
            "intuitive sense",
            "my hunch",
            "trusting intuition",
        ],
        "keywords": ["intuition", "gut", "feeling", "hunch", "vibe", "instinct", "sense"],
    },
    "moral_imagination": {
        "description": "Envisioning better futures, moral possibilities, ideal worlds, ethical imagination, human flourishing",
        "examples": [
            "ideal world",
            "envision better future",
            "moral possibilities",
            "how things should be",
            "ethical vision",
        ],
        "keywords": ["ideal", "envision", "better world", "should be", "moral vision", "flourishing", "utopia"],
    },
}

# Ensure all registered engines have descriptions
for key in ALL_ENGINE_KEYS:
    if key not in ENGINE_DESCRIPTIONS:
        ENGINE_DESCRIPTIONS[key] = {
            "description": f"Engine for {key}",
            "examples": [],
            "keywords": [],
        } # type: ignore

# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE CLUSTERS — related engines that boost each other
# ═══════════════════════════════════════════════════════════════════════════════

ENGINE_CLUSTERS = {
    "emotional_support": ["emotional", "emotional_reg", "wisdom"],
    "reasoning": ["causal", "logic", "hypothesis", "probability"],
    "creative": ["creative", "conceptual_blend", "analogy_gen", "dream"],
    "strategic": ["planning", "game_theory", "adversarial", "negotiation"],
    "analytical": ["error_detect", "logic", "systems"],
    "philosophical": ["philosophy", "dialectic", "ethics", "moral_imagination"],
    "social_empathy": ["mind", "social", "perspective", "cultural"],
    "meta_cognitive": ["attention", "flexibility", "self_model", "working_memory"],
}

# Reverse lookup: engine_key → cluster names
_ENGINE_TO_CLUSTERS: Dict[str, List[str]] = {}
for _cluster_name, _cluster_engines in ENGINE_CLUSTERS.items():
    for _ekey in _cluster_engines:
        _ENGINE_TO_CLUSTERS.setdefault(_ekey, []).append(_cluster_name)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ScoredIntent:
    """A scored intent with engine key, score, and detection method."""
    engine_key: str
    score: float
    method: str  # "keyword", "semantic", "llm"
    confidence: float = 1.0
    matched_pattern: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# KEYWORD DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════

# NOTE: INTENT_PATTERNS and _COMPILED_PATTERNS are imported lazily from
# cognitive_router to avoid circular imports.


class KeywordDetector:
    """Fast keyword-based intent detection using word-boundary regex."""

    def __init__(self, patterns: Optional[List[Tuple[List[str], str, float]]] = None):
        if patterns is not None:
            self.patterns = patterns
            self._compiled = None  # Will be set manually if needed
        else:
            from cognition.cognitive_router import INTENT_PATTERNS, _COMPILED_PATTERNS
            self.patterns = INTENT_PATTERNS
            self._compiled = _COMPILED_PATTERNS

    def scan(self, user_input: str) -> List[ScoredIntent]:
        """
        Scan input for keyword matches.
        Returns list of scored intents sorted by score descending.
        """
        scores: Dict[str, Tuple[float, List[str]]] = {}

        for compiled_patterns, engine_key, weight in self._compiled:
            matches = []
            for pat in compiled_patterns:
                match = pat.search(user_input)
                if match:
                    matches.append(match.group())

            if matches:
                match_count = len(matches)
                existing_score, existing_matches = scores.get(engine_key, (0, []))
                scores[engine_key] = (
                    existing_score + match_count * weight,
                    existing_matches + matches
                )

        results = []
        for engine_key, (score, matches) in scores.items():
            results.append(ScoredIntent(
                engine_key=engine_key,
                score=score,
                method="keyword",
                confidence=min(1.0, score / 3.0),  # Normalize confidence
                matched_pattern=matches[0] if matches else "",
            ))

        return sorted(results, key=lambda x: x.score, reverse=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SEMANTIC DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════

class SemanticDetector:
    """Embedding-based semantic intent detection."""

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
        self._embedding_service = None
        self._engine_embeddings: Dict[str, np.ndarray] = {}
        self._engine_texts: Dict[str, List[str]] = {}
        self._cache_lock = threading.Lock()
        self._similarity_cache: Dict[str, List[ScoredIntent]] = {}
        self._cache_max_size = 500

        # Pre-build semantic texts for each engine
        self._build_engine_texts()

    def _build_engine_texts(self):
        """Build rich semantic texts for each engine from descriptions."""
        for engine_key, data in ENGINE_DESCRIPTIONS.items():
            texts = []

            # Add main description
            if "description" in data:
                texts.append(data["description"])

            # Add examples
            if "examples" in data:
                texts.extend(data["examples"])

            # Add keywords in context
            if "keywords" in data:
                texts.extend([f"this relates to {kw}" for kw in data["keywords"]])

            self._engine_texts[engine_key] = texts

    def _load_embedding_service(self):
        """Lazily load the embedding service."""
        if self._embedding_service is None:
            try:
                from memory.embeddings import embedding_service
                self._embedding_service = embedding_service
            except Exception as e:
                logger.warning(f"Failed to load embedding service: {e}")
                return False
        return True

    def _get_engine_embeddings(self) -> Dict[str, Any]:
        """Get or compute embeddings for all engine descriptions.
        Returns dict of engine_key -> {"avg": averaged_embedding, "individuals": [per-text embeddings]}
        """
        if self._engine_embeddings:
            return self._engine_embeddings

        if not self._load_embedding_service() or np is None:
            return {}

        # Compute embeddings for each engine's semantic text
        for engine_key, texts in self._engine_texts.items():
            try:
                embeddings = self._embedding_service.encode_batch(texts)
                avg_embedding = np.mean(embeddings, axis=0)
                # Normalize average
                norm = np.linalg.norm(avg_embedding)
                if norm > 0:
                    avg_embedding = avg_embedding / norm
                # Normalize individuals for max-similarity matching
                normed_individuals = []
                for emb in embeddings:
                    n = np.linalg.norm(emb)
                    normed_individuals.append(emb / n if n > 0 else emb)
                self._engine_embeddings[engine_key] = {
                    "avg": avg_embedding,
                    "individuals": normed_individuals,
                }
            except Exception as e:
                logger.debug(f"Failed to embed engine {engine_key}: {e}")

        logger.info(f"Semantic embeddings computed for {len(self._engine_embeddings)} engines")
        return self._engine_embeddings

    def scan(self, user_input: str) -> List[ScoredIntent]:
        """
        Compute semantic similarity between user input and engine descriptions.
        Returns list of scored intents sorted by similarity descending.
        """
        # Check cache first
        import hashlib
        cache_key = hashlib.md5(user_input.encode()).hexdigest()[:16]
        with self._cache_lock:
            if cache_key in self._similarity_cache:
                return self._similarity_cache[cache_key]

        if not self._load_embedding_service():
            return []

        engine_embeddings = self._get_engine_embeddings()
        if not engine_embeddings:
            return []

        # Embed user input
        try:
            input_embedding = self._embedding_service.encode(user_input)
        except Exception as e:
            logger.debug(f"Failed to embed input: {e}")
            return []

        # Compute similarity with each engine (avg + max-similarity)
        results = []
        for engine_key, engine_data in engine_embeddings.items():
            try:
                avg_emb = engine_data["avg"]
                individuals = engine_data["individuals"]
                # Average similarity
                avg_sim = float(self._embedding_service.similarity(input_embedding, avg_emb))
                # Max similarity against individual examples (catches specific matches)
                max_sim = avg_sim
                if individuals:
                    for ind_emb in individuals:
                        sim = float(self._embedding_service.similarity(input_embedding, ind_emb))
                        if sim > max_sim:
                            max_sim = sim
                # Blend: 40% avg + 60% max (max-similarity catches specific matches better)
                blended = 0.4 * avg_sim + 0.6 * max_sim
                if blended > 0.15:
                    results.append(ScoredIntent(
                        engine_key=engine_key,
                        score=blended,
                        method="semantic",
                        confidence=blended,
                    ))
            except Exception:
                continue

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)

        # Cache results (limit cache size)
        with self._cache_lock:
            if len(self._similarity_cache) >= self._cache_max_size:
                keys_to_remove = [k for i, k in enumerate(self._similarity_cache.keys()) if i < 100]
                for k in keys_to_remove:
                    del self._similarity_cache[k]
            self._similarity_cache[cache_key] = results[:10]

        return results[:10]

    def clear_cache(self):
        """Clear the similarity cache."""
        with self._cache_lock:
            self._similarity_cache.clear()


# ═══════════════════════════════════════════════════════════════════════════════
# LLM DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════

class LLMDetector:
    """LLM-based intent detection as fallback for ambiguous cases."""

    def __init__(self):
        self._llm = None

    def _load_llm(self):
        """Lazily load the LLM interface."""
        if self._llm is None:
            try:
                from llm.llama_interface import LlamaInterface, llm
                # Ensure type hinting for methods
                self._llm: LlamaInterface = llm
            except Exception as e:
                logger.warning(f"Failed to load LLM: {e}")
                return False
        return True

    def classify(self, user_input: str, candidate_engines: Optional[List[str]] = None) -> List[ScoredIntent]:
        """
        Use LLM to classify intent when keyword and semantic detection are ambiguous.
        """
        import json
        import re

        if not self._load_llm():
            return []

        # At this point, self._llm is either loaded or we returned False. 
        # But for type checkers, we need a local typed reference
        llm_instance = self._llm
        if not llm_instance or not hasattr(llm_instance, 'is_connected') or not llm_instance.is_connected:
            return []

        # Limit candidate engines if provided
        engine_list = candidate_engines[:15] if candidate_engines else ALL_ENGINE_KEYS[:20]
        engine_list_str = ", ".join(engine_list)

        try:
            # Assumes generate has this signature
            response = llm_instance.generate(
                prompt=(
                    f"Given this user message, identify the 1-3 most relevant cognitive engine keys "
                    f"from the list below. Each engine handles different types of reasoning.\n\n"
                    f"ENGINE KEYS: {engine_list_str}\n\n"
                    f"USER MESSAGE: \"{user_input}\"\n\n"
                    f"Respond ONLY with a JSON array of engine key strings. Example: [\"engine1\", \"engine2\"]"
                ),
                system_prompt="You are an intent classifier. Respond ONLY with a JSON array of engine key strings. No explanation.",
                temperature=0.1,
                max_tokens=80,
            )

            if response and getattr(response, "success", False):
                text = getattr(response, "text", "").strip()
                match = re.search(r'\[.*?\]', text, re.DOTALL)
                if match:
                    try:
                        keys = json.loads(match.group())
                        valid = [str(k) for k in keys if isinstance(k, str) and k in ENGINE_REGISTRY] if isinstance(keys, list) else []
                        results = []
                        for i, key in enumerate(valid):
                            if i >= 3: break
                            results.append(ScoredIntent(
                                engine_key=key,
                                score=0.9 - (i * 0.1),  # Decay score for later picks
                                method="llm",
                                confidence=0.8,
                            ))
                        return results
                    except json.JSONDecodeError:
                        pass

        except Exception as e:
            logger.debug(f"LLM intent detection failed: {e}")

        return []


# ═══════════════════════════════════════════════════════════════════════════════
# HYBRID INTENT CLASSIFIER
# ═══════════════════════════════════════════════════════════════════════════════

class IntentClassifier:
    """
    Hybrid intent detection: embeddings + keywords + LLM fallback.

    Layer 1: Fast keyword scan (< 1ms)
    Layer 2: Semantic similarity against engine descriptions (< 50ms)
    Layer 3: LLM classification only if layers 1+2 are ambiguous
    """

    _instance = None
    _cls_lock = threading.Lock()

    # Thresholds for layer decisions
    KEYWORD_HIGH_CONFIDENCE = 2.5  # Skip other layers if keyword score this high (raised for more semantic coverage)
    SEMANTIC_HIGH_CONFIDENCE = 0.5  # Skip LLM if semantic score this high
    AMBIGUITY_THRESHOLD = 0.2  # Gap between top-2 scores below this = ambiguous
    CLUSTER_BOOST = 0.15  # Score boost for engines in the same cluster as top-scoring engine

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
        self._keyword_detector = KeywordDetector()
        self._semantic_detector = SemanticDetector()
        self._llm_detector = LLMDetector()

        self._stats = {
            "total_classifications": 0,
            "keyword_only": 0,
            "semantic_only": 0,
            "llm_used": 0,
            "hybrid": 0,
        }
        self._stats_lock = threading.Lock()

        logger.info("IntentClassifier initialized with hybrid detection (keyword + semantic + LLM)")

    def detect(self, user_input: str) -> List[ScoredIntent]:
        """
        Detect intent using hybrid approach.

        Layer 1: Fast keyword scan (< 1ms)
        Layer 2: Semantic similarity against engine descriptions (< 50ms)
        Layer 3: LLM classification only if layers 1+2 are ambiguous
        """
        start_time = time.time()

        with self._stats_lock:
            self._stats["total_classifications"] += 1

        # Layer 1: Fast keyword scan
        keyword_results = self._keyword_detector.scan(user_input)

        # Check if keyword results are high-confidence
        if keyword_results and keyword_results[0].score >= self.KEYWORD_HIGH_CONFIDENCE:
            with self._stats_lock:
                self._stats["keyword_only"] += 1
            logger.debug(f"Intent detected via keywords: {keyword_results[0].engine_key} (score: {keyword_results[0].score:.2f})")
            return keyword_results

        # Layer 2: Semantic similarity
        semantic_results = self._semantic_detector.scan(user_input)

        # Check if semantic results are high-confidence
        if semantic_results and semantic_results[0].score >= self.SEMANTIC_HIGH_CONFIDENCE:
            # Still merge with keyword results
            merged = self._merge_results(keyword_results, semantic_results)
            with self._stats_lock:
                self._stats["semantic_only"] += 1
            logger.debug(f"Intent detected via semantics: {merged[0].engine_key} (score: {merged[0].score:.2f})")
            return merged

        # Check if results are ambiguous
        if self._is_ambiguous(keyword_results, semantic_results):
            # Layer 3: LLM classification
            # Get candidate engines from keyword + semantic results
            candidates = list(set(
                [r.engine_key for r in keyword_results[:5]] +
                [r.engine_key for r in semantic_results[:5]]
            ))
            llm_results = self._llm_detector.classify(user_input, candidates)

            if llm_results:
                merged = self._merge_results(keyword_results, semantic_results, llm_results)
                with self._stats_lock:
                    self._stats["llm_used"] += 1
                logger.debug(f"Intent detected via LLM fallback: {merged[0].engine_key}")
                return merged

        # Merge keyword and semantic results
        merged = self._merge_results(keyword_results, semantic_results)

        with self._stats_lock:
            self._stats["hybrid"] += 1

        elapsed = time.time() - start_time
        logger.debug(f"Intent classification took {elapsed*1000:.1f}ms")

        return merged

    def _is_ambiguous(
        self,
        keyword_results: List[ScoredIntent],
        semantic_results: List[ScoredIntent]
    ) -> bool:
        """Check if the detection results are ambiguous and need LLM help."""
        # No results at all - definitely ambiguous
        if not keyword_results and not semantic_results:
            return True

        # Get top results from each
        all_results = keyword_results + semantic_results
        if len(all_results) < 2:
            return True

        # Sort by score
        all_results.sort(key=lambda x: x.score, reverse=True)

        # Check gap between top-2
        if len(all_results) >= 2:
            gap = all_results[0].score - all_results[1].score
            if gap < self.AMBIGUITY_THRESHOLD:
                return True

        # Low confidence top result
        if all_results[0].confidence < 0.3:
            return True

        return False

    def _merge_results(
        self,
        keyword_results: List[ScoredIntent],
        semantic_results: List[ScoredIntent],
        llm_results: List[ScoredIntent] = None
    ) -> List[ScoredIntent]:
        """Merge results from multiple detection methods."""
        merged: Dict[str, ScoredIntent] = {}

        # Add keyword results (weight: 1.0)
        for r in keyword_results:
            merged[r.engine_key] = ScoredIntent(
                engine_key=r.engine_key,
                score=r.score * 1.0,
                method=r.method,
                confidence=r.confidence,
                matched_pattern=r.matched_pattern,
            )

        # Add/merge semantic results (weight: 2.0 — boosted for better implicit detection)
        for r in semantic_results:
            if r.engine_key in merged:
                existing = merged[r.engine_key]
                merged[r.engine_key] = ScoredIntent(
                    engine_key=r.engine_key,
                    score=existing.score + r.score * 2.0,
                    method=f"{existing.method}+semantic",
                    confidence=max(existing.confidence, r.confidence),
                    matched_pattern=existing.matched_pattern,
                )
            else:
                merged[r.engine_key] = ScoredIntent(
                    engine_key=r.engine_key,
                    score=r.score * 2.0,
                    method=r.method,
                    confidence=r.confidence,
                )

        # Add/merge LLM results (weight: 1.2)
        if llm_results:
            for r in llm_results:
                if r.engine_key in merged:
                    existing = merged[r.engine_key]
                    merged[r.engine_key] = ScoredIntent(
                        engine_key=r.engine_key,
                        score=existing.score + r.score * 1.2,
                        method=f"{existing.method}+llm",
                        confidence=max(existing.confidence, r.confidence),
                        matched_pattern=existing.matched_pattern,
                    )
                else:
                    merged[r.engine_key] = ScoredIntent(
                        engine_key=r.engine_key,
                        score=r.score * 1.2,
                        method=r.method,
                        confidence=r.confidence,
                    )

        # Cluster boost: if multiple engines from the same cluster are detected, boost them
        engine_keys_in_merged = set(merged.keys())
        for cluster_name, cluster_engines in ENGINE_CLUSTERS.items():
            cluster_hits = engine_keys_in_merged & set(cluster_engines)
            if len(cluster_hits) >= 2:
                for ekey in cluster_hits:
                    merged[ekey] = ScoredIntent(
                        engine_key=ekey,
                        score=merged[ekey].score + self.CLUSTER_BOOST,
                        method=merged[ekey].method + "+cluster",
                        confidence=min(1.0, merged[ekey].confidence + 0.05),
                        matched_pattern=merged[ekey].matched_pattern,
                    )

        # Sort by score descending
        results = list(merged.values())
        results.sort(key=lambda x: x.score, reverse=True)

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get classification statistics."""
        with self._stats_lock:
            return dict(self._stats)


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

intent_classifier = IntentClassifier()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("NEXUS Intent Classifier Test")
    print("=" * 60)

    classifier = IntentClassifier()

    test_inputs = [
        # Implicit intent that keywords miss
        "My friend died yesterday",
        "I'm struggling with purpose",
        "Is democracy failing?",
        "How do computers actually think?",
        "Tell me a joke",  # Explicit keyword match
        "What if aliens existed",  # Counterfactual
        "I feel so lost in life",  # Emotional/philosophical
        "Why did the economy crash?",  # Causal (explicit)
        "Should I quit my job?",  # Decision (explicit)
    ]

    for user_input in test_inputs:
        print(f"\nInput: \"{user_input}\"")
        results = classifier.detect(user_input)

        if results:
            print(f"  Top engines:")
            for r in results[:3]:
                print(f"    - {r.engine_key}: score={r.score:.2f}, method={r.method}, confidence={r.confidence:.2f}")
        else:
            print("  No engines detected")

    print(f"\nClassifier stats: {classifier.get_stats()}")