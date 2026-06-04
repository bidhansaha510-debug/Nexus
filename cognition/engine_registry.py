"""
NEXUS AI — Engine Registry
Declarative adapter table mapping engine keys to their methods.

Each engine can have multiple methods. The router picks the best
method based on sub-pattern matching against the user's input.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Callable, Any


@dataclass
class EngineMethod:
    """A single callable method on an engine."""
    name: str
    invoke: Callable        # (cognition, user_input) -> Any
    format_result: Callable # (raw_result) -> str
    sub_patterns: List[str] = field(default_factory=list)
    # Contract fields (Tier 2 #6)
    input_type: str = "text"        # "text", "dict", "list"
    output_type: str = "text"       # "text", "dict", "dataclass", "list"
    description: str = ""           # Natural language description


@dataclass
class EngineAdapter:
    """All methods available for one engine."""
    key: str
    methods: List[EngineMethod]
    default: int = 0  # index of default method
    description: str = ""  # Natural language capability (Tier 3 #7)


ENGINE_REGISTRY: Dict[str, EngineAdapter] = {}


def _reg(key, methods, default=0, description=""):
    ENGINE_REGISTRY[key] = EngineAdapter(key=key, methods=methods, default=default, description=description)

ALL_ENGINE_KEYS = list(ENGINE_REGISTRY.keys())


# ─── Formatting helpers ──────────────────────────────────────────────────────

def _safe(fn, r, fallback=""):
    try:
        return fn(r) if r else fallback
    except Exception:
        return fallback


def _trunc(s: str, length: int) -> str:
    """Helper for slicing strings cleanly for Pyre"""
    return "".join(c for i, c in enumerate(s) if i < length)

def _fmt(r, max_len=150):
    """Safely extract readable text from any result type (dict, dataclass, str, list)."""
    if r is None:
        return ""
    if isinstance(r, str):
        return _trunc(r, max_len)
    if isinstance(r, dict):
        # Try common keys
        for key in ("summary", "result", "insight", "description", "text", "analysis",
                     "output", "response", "explanation", "answer", "content"):
            val = r.get(key)
            if val:
                return _trunc(str(val), max_len)
        # Fall back to first non-empty string value
        for v in r.values():
            if isinstance(v, str) and v.strip():
                return _trunc(v, max_len)
    if isinstance(r, list):
        items = [_trunc(str(x), 60) for i, x in enumerate(r) if i < 3 and x]
        return _trunc("; ".join(items), max_len) if items else ""
    # Dataclass / object — try common attrs
    for attr in ("summary", "result", "insight", "description", "text"):
        if hasattr(r, attr):
            val = getattr(r, attr)
            if val:
                return _trunc(str(val), max_len)
    return _trunc(str(r), max_len)


# ═════════════════════════════════════════════════════════════════════════════
# REASONING ENGINES
# ═════════════════════════════════════════════════════════════════════════════

_reg("causal", [
    EngineMethod("analyze_causes",
        invoke=lambda c, i: c.causal_reasoning.analyze_causes(i),
        format_result=lambda r: _safe(lambda r: f"Causal chain: {'; '.join(f'{l.cause} → {l.effect}' for l in r.links[:3])}", r),
        sub_patterns=["why did", "root cause", "what caused", "reason for"]),
    EngineMethod("predict_effects",
        invoke=lambda c, i: c.causal_reasoning.predict_effects(i),
        format_result=lambda r: f"Effects: {'; '.join(str(e.get('effect',''))[:60] for i, e in enumerate(r or []) if i < 3)}" if r else "",
        sub_patterns=["what will happen", "consequence of", "effect of", "result of"]),
    EngineMethod("find_root_cause",
        invoke=lambda c, i: c.causal_reasoning.find_root_cause([i]),
        format_result=lambda r: _safe(lambda r: f"Root cause: {_fmt(r)}", r),
        sub_patterns=["root cause", "underlying reason", "fundamental issue"]),
    EngineMethod("diagnose",
        invoke=lambda c, i: c.causal_reasoning.diagnose(i),
        format_result=lambda r: _safe(lambda r: f"Diagnosis: {_fmt(r)}", r),
        sub_patterns=["diagnose", "what is wrong with", "troubleshoot"]),
], description="Identifies causes, effects, root causes, and causal chains in situations and events")

_reg("decision", [
    EngineMethod("analyze_decision",
        invoke=lambda c, i: c.decision_theory.analyze_decision(i),
        format_result=lambda r: _safe(lambda r: f"Recommended: {r.recommended} (confidence: {r.confidence:.2f})", r),
        sub_patterns=["should i", "decide between", "which option"]),
    EngineMethod("analyze_tradeoffs",
        invoke=lambda c, i: c.decision_theory.analyze_tradeoffs(i),
        format_result=lambda r: _safe(lambda r: f"Tradeoffs: {_fmt(r)}", r),
        sub_patterns=["pros and cons", "tradeoff", "trade-off", "advantages"]),
    EngineMethod("multi_criteria",
        invoke=lambda c, i: c.decision_theory.multi_criteria_decision(i),
        format_result=lambda r: _safe(lambda r: f"Multi-criteria: {_fmt(r)}", r),
        sub_patterns=["multiple factors", "criteria", "multi-criteria", "weighted criteria", "score options", "rank alternatives"]),
], description="Analyzes decisions, tradeoffs, and multi-criteria choices to find optimal outcomes")

_reg("ethics", [
    EngineMethod("evaluate",
        invoke=lambda c, i: c.ethical_reasoning.evaluate(i),
        format_result=lambda r: _safe(lambda r: f"Ethical: {r.overall_verdict.value} ({r.overall_score:.2f})" + (f" — {', '.join(r.concerns[:2])}" if r.concerns else ""), r),
        sub_patterns=["ethical", "moral", "right or wrong"]),
    EngineMethod("resolve_dilemma",
        invoke=lambda c, i: c.ethical_reasoning.resolve_dilemma(i),
        format_result=lambda r: _safe(lambda r: f"Dilemma resolution: {_fmt(r)}", r),
        sub_patterns=["dilemma", "torn between", "ethical conflict"]),
    EngineMethod("dilemma_resolver",
        invoke=lambda c, i: c.ethical_reasoning.dilemma_resolver(i),
        format_result=lambda r: _safe(lambda r: f"Resolution: {_fmt(r)}", r),
        sub_patterns=["moral dilemma", "ethically complex", "no right answer"]),
], description="Evaluates ethical implications, moral dilemmas, and provides principled guidance")

_reg("logic", [
    EngineMethod("validate_argument",
        invoke=lambda c, i: c.logical_reasoning.validate_argument(i),
        format_result=lambda r: _safe(lambda r: f"Logic: {'valid' if r.is_valid else 'invalid'} ({r.soundness_score:.2f})" + (f" — fallacies: {', '.join(f.value for f in r.fallacies[:2])}" if r.fallacies else ""), r),
        sub_patterns=["logically", "valid argument", "fallacy"]),
    EngineMethod("detect_fallacies",
        invoke=lambda c, i: c.logical_reasoning.detect_fallacies(i),
        format_result=lambda r: _safe(lambda r: f"Fallacies: {_fmt(r)}", r),
        sub_patterns=["logical fallacy", "bad argument", "flawed reasoning"]),
    EngineMethod("build_proof",
        invoke=lambda c, i: c.logical_reasoning.build_proof(i),
        format_result=lambda r: _safe(lambda r: f"Proof: {_fmt(r)}", r),
        sub_patterns=["prove that", "proof", "demonstrate"]),
    EngineMethod("proof_chain",
        invoke=lambda c, i: c.logical_reasoning.proof_chain(i),
        format_result=lambda r: _safe(lambda r: f"Proof chain: {_fmt(r)}", r),
        sub_patterns=["step by step proof", "deductive chain", "logical chain"]),
], description="Validates logical arguments, detects fallacies, and constructs formal proofs")

_reg("probability", [
    EngineMethod("estimate_probability",
        invoke=lambda c, i: c.probabilistic_reasoning.estimate_probability(i),
        format_result=lambda r: f"Probability: {r.get('probability','?')} (confidence: {r.get('confidence','?')})" if r else "",
        sub_patterns=["probability of", "how likely", "chances of"]),
    EngineMethod("bayesian_update",
        invoke=lambda c, i: c.probabilistic_reasoning.bayesian_update(i),
        format_result=lambda r: _safe(lambda r: f"Bayesian: {_fmt(r)}", r),
        sub_patterns=["given that", "bayesian", "update belief", "new evidence"]),
    EngineMethod("assess_risk",
        invoke=lambda c, i: c.probabilistic_reasoning.assess_risk(i),
        format_result=lambda r: _safe(lambda r: f"Risk: {_fmt(r)}", r),
        sub_patterns=["risk of", "risk assessment", "how risky"]),
], description="Estimates probabilities, performs Bayesian reasoning, and assesses risks")

_reg("hypothesis", [
    EngineMethod("generate_hypotheses",
        invoke=lambda c, i: c.hypothesis.generate_hypotheses(i, count=2),
        format_result=lambda r: f"Hypotheses: {'; '.join(h.statement[:80] for h in r[:2])}" if r else "",
        sub_patterns=["hypothesis", "theory about", "explain why"]),
    EngineMethod("design_experiment",
        invoke=lambda c, i: c.hypothesis.design_experiment(i),
        format_result=lambda r: _safe(lambda r: f"Experiment: {r.design[:120]}", r),
        sub_patterns=["experiment", "test this", "how to verify"]),
    EngineMethod("evaluate_evidence",
        invoke=lambda c, i: c.hypothesis.evaluate_evidence(i, ""),
        format_result=lambda r: _safe(lambda r: f"Evidence: {_fmt(r)}", r),
        sub_patterns=["evidence for", "data shows", "research shows"]),
    EngineMethod("falsify",
        invoke=lambda c, i: c.hypothesis.falsify(i),
        format_result=lambda r: _safe(lambda r: f"Falsification: {_fmt(r)}", r),
        sub_patterns=["disprove", "falsify", "what would prove this wrong"]),
], description="Generates hypotheses, designs experiments, evaluates evidence, and tests falsifiability")

_reg("counterfactual", [
    EngineMethod("what_if",
        invoke=lambda c, i: c.counterfactual_reasoning.what_if(i),
        format_result=lambda r: _safe(lambda r: f"Counterfactual: {r.scenario[:80]} → plausibility: {r.plausibility.value if hasattr(r.plausibility,'value') else r.plausibility}", r),
        sub_patterns=["what if", "imagine if", "had i done"]),
    EngineMethod("regret_analysis",
        invoke=lambda c, i: c.counterfactual_reasoning.regret_analysis(i),
        format_result=lambda r: _safe(lambda r: f"Regret analysis: {_fmt(r)}", r),
        sub_patterns=["regret", "should have", "wish i had"]),
    EngineMethod("find_pivot_points",
        invoke=lambda c, i: c.counterfactual_reasoning.find_pivot_points(i),
        format_result=lambda r: _safe(lambda r: f"Pivot points: {_fmt(r)}", r),
        sub_patterns=["turning point", "critical moment", "pivot"]),
    EngineMethod("timeline_divergence",
        invoke=lambda c, i: c.counterfactual_reasoning.timeline_divergence(i, ""),
        format_result=lambda r: _safe(lambda r: f"Divergence: {_fmt(r)}", r),
        sub_patterns=["alternate timeline", "diverge", "butterfly effect"]),
], description="Explores what-if scenarios, alternative timelines, and regret analysis")

_reg("dialectic", [
    EngineMethod("dialectic",
        invoke=lambda c, i: c.dialectical_reasoning.dialectic(i),
        format_result=lambda r: _safe(lambda r: f"Thesis: {r.thesis[:50]} | Antithesis: {r.antithesis[:50]} | Synthesis: {r.synthesis[:50]}", r),
        sub_patterns=["both sides", "thesis", "opposing view"]),
    EngineMethod("steelman",
        invoke=lambda c, i: c.dialectical_reasoning.steelman(i),
        format_result=lambda r: _safe(lambda r: f"Steelman: {_fmt(r)}", r),
        sub_patterns=["strongest version", "steelman", "best argument for"]),
    EngineMethod("socratic_questioning",
        invoke=lambda c, i: c.dialectical_reasoning.socratic_questioning(i),
        format_result=lambda r: _safe(lambda r: f"Socratic: {_fmt(r)}", r),
        sub_patterns=["question this", "socratic", "challenge this"]),
], description="Examines opposing viewpoints through thesis-antithesis-synthesis and Socratic questioning")

_reg("philosophy", [
    EngineMethod("philosophize",
        invoke=lambda c, i: c.philosophical_reasoning.philosophize(i),
        format_result=lambda r: _safe(lambda r: f"Philosophy ({r.branch.value}): {r.synthesis[:80]}", r),
        sub_patterns=["philosophically", "meaning of", "consciousness"]),
    EngineMethod("thought_experiment",
        invoke=lambda c, i: c.philosophical_reasoning.thought_experiment(i),
        format_result=lambda r: _safe(lambda r: f"Thought experiment: {_fmt(r)}", r),
        sub_patterns=["thought experiment", "imagine a world", "suppose that"]),
    EngineMethod("existential_analysis",
        invoke=lambda c, i: c.philosophical_reasoning.existential_analysis(i),
        format_result=lambda r: _safe(lambda r: f"Existential: {_fmt(r)}", r),
        sub_patterns=["existential", "purpose of", "meaning of life"]),
], description="Deep philosophical analysis including existential questions and thought experiments")


# ═════════════════════════════════════════════════════════════════════════════
# INTELLIGENCE ENGINES
# ═════════════════════════════════════════════════════════════════════════════

_reg("emotional", [
    EngineMethod("empathize",
        invoke=lambda c, i: c.emotional_intelligence.empathize(i),
        format_result=lambda r: _safe(lambda r: f"Emotional: {', '.join(r.detected_emotions[:3])} — {r.suggested_response[:100]}", r),
        sub_patterns=["i feel", "i'm feeling", "emotionally"]),
    EngineMethod("emotional_coaching",
        invoke=lambda c, i: c.emotional_intelligence.emotional_coaching(i),
        format_result=lambda r: _safe(lambda r: f"Coaching: {_fmt(r)}", r),
        sub_patterns=["help me with", "struggling with", "how to deal with"]),
    EngineMethod("analyze_emotional_dynamics",
        invoke=lambda c, i: c.emotional_intelligence.analyze_emotional_dynamics(i),
        format_result=lambda r: _safe(lambda r: f"Dynamics: {_fmt(r)}", r),
        sub_patterns=["emotional dynamic", "tension between", "conflict with"]),
    EngineMethod("emotional_forecast",
        invoke=lambda c, i: c.emotional_intelligence.emotional_forecast(i),
        format_result=lambda r: _safe(lambda r: f"Forecast: {_fmt(r)}", r),
        sub_patterns=["how will i feel", "emotional trajectory", "predict my mood"]),
], description="Recognizes emotions, provides empathy, and analyzes emotional dynamics")

_reg("emotional_reg", [
    EngineMethod("regulate",
        invoke=lambda c, i: c.emotional_regulation.regulate(i),
        format_result=lambda r: _safe(lambda r: f"Regulation ({r.strategy.value}): {r.reframed_thought[:100]}", r),
        sub_patterns=["calm me down", "regulate", "manage my"]),
    EngineMethod("reappraise",
        invoke=lambda c, i: c.emotional_regulation.reappraise(i),
        format_result=lambda r: _safe(lambda r: f"Reappraisal: {_fmt(r)}", r),
        sub_patterns=["reframe this", "think about it differently", "silver lining"]),
    EngineMethod("coping_plan",
        invoke=lambda c, i: c.emotional_regulation.coping_plan(i),
        format_result=lambda r: _safe(lambda r: f"Coping: {_fmt(r)}", r),
        sub_patterns=["coping strategy", "how to cope", "self-care"]),
    EngineMethod("grounding_exercise",
        invoke=lambda c, i: c.emotional_regulation.grounding_exercise(i),
        format_result=lambda r: _safe(lambda r: f"Grounding: {_fmt(r)}", r),
        sub_patterns=["ground me", "grounding exercise", "panic attack", "anxiety technique"]),
], description="Helps regulate emotions through reappraisal, coping strategies, and grounding")

_reg("mind", [
    EngineMethod("infer_mental_state",
        invoke=lambda c, i: c.theory_of_mind.infer_mental_state(i),
        format_result=lambda r: _safe(lambda r: f"Mental state: emotions={', '.join(r.emotions[:2])}, desires={', '.join(r.desires[:2])}" if r.emotions else "", r),
        sub_patterns=["they think", "their perspective", "what are they feeling"]),
    EngineMethod("predict_reaction",
        invoke=lambda c, i: c.theory_of_mind.predict_reaction(i),
        format_result=lambda r: _safe(lambda r: f"Predicted reaction: {_fmt(r)}", r),
        sub_patterns=["how will they react", "their reaction", "they would feel"]),
], description="Infers mental states, predicts reactions, and models theory of mind")

_reg("social", [
    EngineMethod("analyze_social_situation",
        invoke=lambda c, i: c.social_cognition.analyze_social_situation(i),
        format_result=lambda r: _safe(lambda r: f"Social: cohesion={r.group_cohesion:.2f}, conflict={r.conflict_level:.2f}", r),
        sub_patterns=["social dynamics", "group dynamics"]),
    EngineMethod("detect_influence",
        invoke=lambda c, i: c.social_cognition.detect_influence(i),
        format_result=lambda r: _safe(lambda r: f"Influence: {_fmt(r)}", r),
        sub_patterns=["being manipulated", "influence tactics", "peer pressure"]),
    EngineMethod("assess_trust",
        invoke=lambda c, i: c.social_cognition.assess_trust(i),
        format_result=lambda r: _safe(lambda r: f"Trust: {_fmt(r)}", r),
        sub_patterns=["can i trust", "trustworthy", "reliable"]),
    EngineMethod("power_dynamics",
        invoke=lambda c, i: c.social_cognition.power_dynamics(i),
        format_result=lambda r: _safe(lambda r: f"Power: {_fmt(r)}", r),
        sub_patterns=["power dynamic", "who is in charge", "hierarchy", "authority"]),
], description="Analyzes social dynamics, influence tactics, trust, and power structures")

_reg("cultural", [
    EngineMethod("analyze_cultural_context",
        invoke=lambda c, i: c.cultural_intelligence.analyze_cultural_context(i),
        format_result=lambda r: _safe(lambda r: f"Cultural: {r.cultural_context[:100]} (sensitivity: {r.sensitivity_score:.2f})", r),
        sub_patterns=["cultural context", "cross-cultural"]),
    EngineMethod("cultural_translation",
        invoke=lambda c, i: c.cultural_intelligence.cultural_translation(i),
        format_result=lambda r: _safe(lambda r: f"Translation: {_fmt(r)}", r),
        sub_patterns=["cultural difference", "in their culture", "etiquette"]),
    EngineMethod("bridge_cultures",
        invoke=lambda c, i: c.cultural_intelligence.bridge_cultures(i),
        format_result=lambda r: _safe(lambda r: f"Bridge: {_fmt(r)}", r),
        sub_patterns=["bridge cultures", "common ground between cultures", "cultural harmony"]),
], description="Understands cultural contexts, bridges cultural differences, and advises on etiquette")

_reg("linguistic", [
    EngineMethod("analyze_text",
        invoke=lambda c, i: c.linguistic_intelligence.analyze_text(i),
        format_result=lambda r: _safe(lambda r: f"Text: register={r.register}, tone={r.tone}, formality={r.formality:.2f}", r),
        sub_patterns=["writing style", "tone of", "rhetoric"]),
    EngineMethod("style_transfer",
        invoke=lambda c, i: c.linguistic_intelligence.style_transfer(i),
        format_result=lambda r: _safe(lambda r: f"Rewritten: {_fmt(r)}", r),
        sub_patterns=["rephrase this", "rewrite this", "more formal", "less formal"]),
    EngineMethod("analyze_rhetoric",
        invoke=lambda c, i: c.linguistic_intelligence.analyze_rhetoric(i),
        format_result=lambda r: _safe(lambda r: f"Rhetoric: {_fmt(r)}", r),
        sub_patterns=["persuasive", "rhetoric", "argument structure", "rhetorical devices", "persuasion technique", "ethos pathos logos"]),
], description="Analyzes writing style, tone, rhetoric, and performs style transfer")

_reg("narrative", [
    EngineMethod("analyze_narrative",
        invoke=lambda c, i: c.narrative_intelligence.analyze_narrative(i),
        format_result=lambda r: _safe(lambda r: f"Narrative: arc={r.narrative_arc}, themes={', '.join(r.themes[:2])}", r),
        sub_patterns=["story about", "narrative", "plot of"]),
    EngineMethod("generate_story",
        invoke=lambda c, i: c.narrative_intelligence.generate_story(i),
        format_result=lambda r: _safe(lambda r: f"Story: {_fmt(r)}", r),
        sub_patterns=["tell me a story", "once upon", "write a story"]),
    EngineMethod("extract_moral",
        invoke=lambda c, i: c.narrative_intelligence.extract_moral(i),
        format_result=lambda r: _safe(lambda r: f"Moral: {_fmt(r)}", r),
        sub_patterns=["moral of", "lesson from", "takeaway"]),
    EngineMethod("story_arc_design",
        invoke=lambda c, i: c.narrative_intelligence.story_arc_design(i),
        format_result=lambda r: _safe(lambda r: f"Story arc: {_fmt(r)}", r),
        sub_patterns=["design a story", "story arc", "plot structure", "hero's journey"]),
], description="Analyzes narratives, generates stories, extracts morals, and designs story arcs")

_reg("humor", [
    EngineMethod("analyze_humor",
        invoke=lambda c, i: c.humor_intelligence.analyze_humor(i),
        format_result=lambda r: f"Humor: {r.get('humor_type','?')} — {r.get('explanation','')[:100]}" if r else "",
        sub_patterns=["that's funny", "humor in"]),
    EngineMethod("generate_joke",
        invoke=lambda c, i: c.humor_intelligence.generate_joke(i),
        format_result=lambda r: _safe(lambda r: f"Joke: {_fmt(r)}", r),
        sub_patterns=["tell me a joke", "make me laugh", "pun about"]),
    EngineMethod("witty_remark",
        invoke=lambda c, i: c.humor_intelligence.witty_remark(i),
        format_result=lambda r: _safe(lambda r: f"Witty: {_fmt(r)}", r),
        sub_patterns=["witty response", "clever comeback"]),
], description="Analyzes humor, generates jokes, and crafts witty remarks")

_reg("wisdom", [
    EngineMethod("seek_wisdom",
        invoke=lambda c, i: c.wisdom.seek_wisdom(i),
        format_result=lambda r: _safe(lambda r: f"Wisdom: {r.wisdom[:120]}", r),
        sub_patterns=["wise advice", "sage advice", "wisdom about"]),
    EngineMethod("life_lesson",
        invoke=lambda c, i: c.wisdom.life_lesson(i),
        format_result=lambda r: _safe(lambda r: f"Life lesson: {_fmt(r)}", r),
        sub_patterns=["life lesson", "learn from", "experience taught"]),
    EngineMethod("long_term_view",
        invoke=lambda c, i: c.wisdom.long_term_view(i),
        format_result=lambda r: _safe(lambda r: f"Long-term: {_fmt(r)}", r),
        sub_patterns=["long term", "in 5 years", "big picture"]),
    EngineMethod("interpret_proverb",
        invoke=lambda c, i: c.wisdom.interpret_proverb(i),
        format_result=lambda r: _safe(lambda r: f"Proverb: {_fmt(r)}", r),
        sub_patterns=["proverb", "saying means", "old saying"]),
    EngineMethod("paradox_resolution",
        invoke=lambda c, i: c.wisdom.paradox_resolution(i),
        format_result=lambda r: _safe(lambda r: f"Paradox: {_fmt(r)}", r),
        sub_patterns=["paradox", "contradiction", "seems contradictory"]),
], description="Provides sage advice, life lessons, long-term perspective, and resolves paradoxes")


# ═════════════════════════════════════════════════════════════════════════════
# CREATIVE ENGINES
# ═════════════════════════════════════════════════════════════════════════════

_reg("creative", [
    EngineMethod("brainstorm",
        invoke=lambda c, i: c.creative_synthesis.brainstorm(i, count=2),
        format_result=lambda r: f"Ideas: {'; '.join(x.description[:60] for x in r[:2])}" if r else "",
        sub_patterns=["brainstorm", "creative solution", "innovative idea"]),
    EngineMethod("innovate",
        invoke=lambda c, i: c.creative_synthesis.innovate(i),
        format_result=lambda r: _safe(lambda r: f"Innovation: {_fmt(r)}", r),
        sub_patterns=["invent", "novel approach", "original idea"]),
    EngineMethod("reframe",
        invoke=lambda c, i: c.creative_synthesis.reframe(i),
        format_result=lambda r: _safe(lambda r: f"Reframe: {_fmt(r)}", r),
        sub_patterns=["look at it differently", "reframe", "different angle"]),
    EngineMethod("scamper",
        invoke=lambda c, i: c.creative_synthesis.scamper(i),
        format_result=lambda r: _safe(lambda r: f"SCAMPER: {_fmt(r)}", r),
        sub_patterns=["scamper", "substitute combine adapt", "systematic creativity"]),
], description="Brainstorms ideas, innovates solutions, reframes problems, and applies SCAMPER")

_reg("dream", [
    EngineMethod("dream",
        invoke=lambda c, i: c.dream_engine.dream(i),
        format_result=lambda r: _safe(lambda r: f"Dream: {r.narrative[:120]}", r),
        sub_patterns=["dream about", "surreal", "wild idea"]),
    EngineMethod("free_associate",
        invoke=lambda c, i: c.dream_engine.free_associate(i),
        format_result=lambda r: _safe(lambda r: f"Associations: {_fmt(r)}", r),
        sub_patterns=["free associate", "stream of consciousness"]),
    EngineMethod("incubate",
        invoke=lambda c, i: c.dream_engine.incubate(i),
        format_result=lambda r: _safe(lambda r: f"Incubation: {_fmt(r)}", r),
        sub_patterns=["let it simmer", "subconscious", "sleep on it"]),
    EngineMethod("lucid_dream",
        invoke=lambda c, i: c.dream_engine.lucid_dream(i),
        format_result=lambda r: _safe(lambda r: f"Lucid dream: {_fmt(r)}", r),
        sub_patterns=["lucid dream", "vivid dream", "dream sequence"]),
], description="Generates surreal dreamscapes, free associations, and subconscious exploration")

_reg("music", [
    EngineMethod("analyze_music",
        invoke=lambda c, i: c.musical_cognition.analyze_music(i),
        format_result=lambda r: f"Music: mood={r.get('mood','?')}, genre={r.get('genre','?')}" if r else "",
        sub_patterns=["music about", "song about"]),
    EngineMethod("emotion_to_music",
        invoke=lambda c, i: c.musical_cognition.emotion_to_music(i),
        format_result=lambda r: _safe(lambda r: f"Musical mood: {_fmt(r)}", r),
        sub_patterns=["sounds like", "musical feel", "soundtrack for"]),
    EngineMethod("compose_motif",
        invoke=lambda c, i: c.musical_cognition.compose_motif(i),
        format_result=lambda r: _safe(lambda r: f"Motif: {_fmt(r)}", r),
        sub_patterns=["compose", "musical motif", "melody for"]),
], description="Analyzes musical elements, maps emotions to music, and composes motifs")

_reg("visual", [
    EngineMethod("visualize",
        invoke=lambda c, i: c.visual_imagination.visualize(i),
        format_result=lambda r: f"Visual: {r.get('description','')[:120]}" if r else "",
        sub_patterns=["visualize", "picture this", "imagine the scene"]),
    EngineMethod("describe_diagram",
        invoke=lambda c, i: c.visual_imagination.describe_diagram(i),
        format_result=lambda r: _safe(lambda r: f"Diagram: {_fmt(r)}", r),
        sub_patterns=["diagram of", "illustration of", "sketch of"]),
    EngineMethod("scene_evolution",
        invoke=lambda c, i: c.visual_imagination.scene_evolution(i),
        format_result=lambda r: _safe(lambda r: f"Evolution: {_fmt(r)}", r),
        sub_patterns=["evolve this scene", "how it changes over time", "time lapse"]),
], description="Creates mental visualizations, describes diagrams, and imagines scene evolution")

_reg("conceptual_blend", [
    EngineMethod("blend",
        invoke=lambda c, i: c.conceptual_blending.blend(i, "general knowledge"),
        format_result=lambda r: _safe(lambda r: f"Blend: {r.novel_concept[:120]}", r),
        sub_patterns=["combine", "merge ideas", "blend concepts"]),
    EngineMethod("multi_blend",
        invoke=lambda c, i: c.conceptual_blending.multi_blend(i),
        format_result=lambda r: _safe(lambda r: f"Multi-blend: {_fmt(r)}", r),
        sub_patterns=["fuse together", "hybrid of", "mashup"]),
    EngineMethod("triple_blend",
        invoke=lambda c, i: c.conceptual_blending.triple_blend(i, "technology", "nature"),
        format_result=lambda r: _safe(lambda r: f"Triple blend: {_fmt(r)}", r),
        sub_patterns=["blend three", "triple fusion", "three-way mashup"]),
], description="Blends and fuses concepts to create novel hybrid ideas")

_reg("analogy_gen", [
    EngineMethod("generate_analogy",
        invoke=lambda c, i: c.analogy_generator.generate_analogy(i),
        format_result=lambda r: _safe(lambda r: f"Analogy: {r.mapping[:120]}", r),
        sub_patterns=["analogy for", "explain like i'm five", "eli5"]),
    EngineMethod("explain_by_analogy",
        invoke=lambda c, i: c.analogy_generator.explain_by_analogy(i),
        format_result=lambda r: _safe(lambda r: f"Explanation: {_fmt(r)}", r),
        sub_patterns=["in simple terms", "think of it as"]),
    EngineMethod("deep_analogy",
        invoke=lambda c, i: c.analogy_generator.deep_analogy(i),
        format_result=lambda r: _safe(lambda r: f"Deep analogy: {_fmt(r)}", r),
        sub_patterns=["deep analogy", "structural mapping", "profound comparison"]),
], description="Generates analogies and explanations using relatable comparisons")

_reg("analogy", [
    EngineMethod("find_analogy",
        invoke=lambda c, i: c.analogical_reasoning.find_analogy(i, "common experience"),
        format_result=lambda r: _safe(lambda r: f"Analogy: {r.summary[:150]}", r),
        sub_patterns=["similar to", "compare to", "analogous"]),
    EngineMethod("apply_analogy",
        invoke=lambda c, i: c.analogical_reasoning.apply_analogy(i),
        format_result=lambda r: _safe(lambda r: f"Applied: {_fmt(r)}", r),
        sub_patterns=["apply this to", "use the same approach"]),
], description="Finds structural analogies between domains and applies cross-domain reasoning")


# ═════════════════════════════════════════════════════════════════════════════
# COGNITIVE ENGINES
# ═════════════════════════════════════════════════════════════════════════════

_reg("attention", [
    EngineMethod("focus",
        invoke=lambda c, i: c.attention_control.focus(i),
        format_result=lambda r: f"Focus: {r.get('strategy','')[:120]}" if r else "",
        sub_patterns=["help me focus", "can't focus", "need to focus"]),
    EngineMethod("prioritize",
        invoke=lambda c, i: c.attention_control.prioritize(i),
        format_result=lambda r: _safe(lambda r: f"Priority: {_fmt(r)}", r),
        sub_patterns=["prioritize", "most important", "what first"]),
    EngineMethod("prioritize_tasks",
        invoke=lambda c, i: c.attention_control.prioritize_tasks(i),
        format_result=lambda r: _safe(lambda r: f"Task priority: {_fmt(r)}", r),
        sub_patterns=["eisenhower matrix", "task priority", "what should i do first"]),
], description="Helps focus attention, prioritize tasks, and manage cognitive load")

_reg("working_memory", [
    EngineMethod("buffer_item",
        invoke=lambda c, i: c.working_memory.buffer_item(i),
        format_result=lambda r: f"Buffered: {r.get('status','stored')}" if r else "",
        sub_patterns=["remember this", "keep in mind", "hold that thought"]),
    EngineMethod("get_context",
        invoke=lambda c, i: c.working_memory.get_context(i),
        format_result=lambda r: _safe(lambda r: f"Context: {_fmt(r)}", r),
        sub_patterns=["what did we discuss", "earlier we said", "as i said"]),
    EngineMethod("synthesize_context",
        invoke=lambda c, i: c.working_memory.synthesize_context(i),
        format_result=lambda r: _safe(lambda r: f"Synthesis: {_fmt(r)}", r),
        sub_patterns=["synthesize context", "connect the dots", "put it together"]),
], description="Buffers and synthesizes conversational context for continuity")

_reg("self_model", [
    EngineMethod("check_capability",
        invoke=lambda c, i: c.self_model.check_capability(i),
        format_result=lambda r: f"Capability: {'can handle' if r.get('can_handle') else 'limited'}" if r else "",
        sub_patterns=["can you do", "are you able", "your capability"]),
    EngineMethod("self_assess",
        invoke=lambda c, i: c.self_model.self_assess(i),
        format_result=lambda r: _safe(lambda r: f"Self-assessment: {_fmt(r)}", r),
        sub_patterns=["how confident", "your limitation", "what are you"]),
    EngineMethod("capability_gap",
        invoke=lambda c, i: c.self_model.capability_gap(i),
        format_result=lambda r: _safe(lambda r: f"Gap analysis: {_fmt(r)}", r),
        sub_patterns=["capability gap", "skill gap", "what am i missing"]),
], description="Assesses AI capabilities, limitations, and identifies skill gaps")

_reg("error_detect", [
    EngineMethod("detect_errors",
        invoke=lambda c, i: c.error_detection.detect_errors(i),
        format_result=lambda r: f"Errors: {len(r.get('errors',[]))} found" if r and r.get('errors') else "No errors.",
        sub_patterns=["find errors", "what's wrong", "check this"]),
    EngineMethod("fact_check",
        invoke=lambda c, i: c.error_detection.fact_check(i),
        format_result=lambda r: _safe(lambda r: f"Fact check: {_fmt(r)}", r),
        sub_patterns=["fact check", "is this true", "verify this"]),
    EngineMethod("find_logical_fallacies",
        invoke=lambda c, i: c.error_detection.find_logical_fallacies(i),
        format_result=lambda r: _safe(lambda r: f"Fallacies: {_fmt(r)}", r),
        sub_patterns=["inconsistency", "flawed logic"]),
    # premortem removed — consolidated into 'adversarial' engine
], description="Finds errors, fact-checks claims, and detects logical inconsistencies")

_reg("curiosity", [
    EngineMethod("generate_questions",
        invoke=lambda c, i: c.curiosity_drive.generate_questions(i),
        format_result=lambda r: f"Questions: {'; '.join(q[:60] for q in r.get('questions',[])[:3])}" if r and r.get('questions') else "",
        sub_patterns=["curious about", "i wonder", "explore this"]),
    EngineMethod("deep_dive",
        invoke=lambda c, i: c.curiosity_drive.deep_dive(i),
        format_result=lambda r: _safe(lambda r: f"Deep dive: {_fmt(r)}", r),
        sub_patterns=["dig deeper", "tell me more", "elaborate on"]),
    EngineMethod("rabbit_hole",
        invoke=lambda c, i: c.curiosity_drive.rabbit_hole(i),
        format_result=lambda r: _safe(lambda r: f"Rabbit hole: {_fmt(r)}", r),
        sub_patterns=["rabbit hole", "follow the thread", "go deeper"]),
], description="Generates deep questions, enables deep dives, and follows intellectual threads")

_reg("transfer", [
    EngineMethod("transfer",
        invoke=lambda c, i: c.transfer_learning.transfer(i),
        format_result=lambda r: f"Transfer: {r.get('transferred_insight','')[:120]}" if r else "",
        sub_patterns=["apply this to", "use in another context"]),
    EngineMethod("map_skills",
        invoke=lambda c, i: c.transfer_learning.map_skills(i),
        format_result=lambda r: _safe(lambda r: f"Skills map: {_fmt(r)}", r),
        sub_patterns=["transferable skills", "related skills"]),
    EngineMethod("cross_pollinate",
        invoke=lambda c, i: c.transfer_learning.cross_pollinate(i, ""),
        format_result=lambda r: _safe(lambda r: f"Cross-pollination: {_fmt(r)}", r),
        sub_patterns=["cross pollinate", "borrow from", "what can we learn from"]),
], description="Transfers knowledge across domains, maps skills, and cross-pollinates ideas")

_reg("perspective", [
    EngineMethod("take_perspective",
        invoke=lambda c, i: c.perspective_taking.take_perspective(i),
        format_result=lambda r: _safe(lambda r: f"Perspective ({r.perspective[:30]}): {r.worldview[:100]}", r),
        sub_patterns=["from their perspective", "in their shoes"]),
    EngineMethod("multi_perspective",
        invoke=lambda c, i: c.perspective_taking.multi_perspective(i),
        format_result=lambda r: _safe(lambda r: f"Multiple views: {_fmt(r)}", r),
        sub_patterns=["different perspectives", "all sides"]),
    EngineMethod("check_bias",
        invoke=lambda c, i: c.perspective_taking.check_bias(i),
        format_result=lambda r: _safe(lambda r: f"Bias check: {_fmt(r)}", r),
        sub_patterns=["am i biased", "bias in", "blind spot"]),
    EngineMethod("role_reversal",
        invoke=lambda c, i: c.perspective_taking.role_reversal(i),
        format_result=lambda r: _safe(lambda r: f"Role reversal: {_fmt(r)}", r),
        sub_patterns=["role reversal", "walk in their shoes", "swap perspectives"]),
], description="Takes different perspectives, identifies biases, and enables role reversal")

_reg("flexibility", [
    EngineMethod("shift_perspective",
        invoke=lambda c, i: c.cognitive_flexibility.shift_perspective(i),
        format_result=lambda r: _safe(lambda r: f"Alt perspective ({r.new_perspectives[0].get('perspective_type','?')}): {r.new_perspectives[0].get('viewpoint','')[:100]}" if r.new_perspectives else "", r),
        sub_patterns=["alternatively", "another way", "different perspective"]),
    EngineMethod("reverse_thinking",
        invoke=lambda c, i: c.cognitive_flexibility.reverse_thinking(i),
        format_result=lambda r: _safe(lambda r: f"Reverse: {_fmt(r)}", r),
        sub_patterns=["opposite approach", "reverse", "flip it"]),
    EngineMethod("paradigm_shift",
        invoke=lambda c, i: c.cognitive_flexibility.paradigm_shift(i),
        format_result=lambda r: _safe(lambda r: f"Paradigm shift: {_fmt(r)}", r),
        sub_patterns=["paradigm shift", "challenge assumption", "rethink everything"]),
], description="Shifts thinking, reverses assumptions, and enables paradigm shifts")

_reg("common_sense", [
    EngineMethod("judge_plausibility",
        invoke=lambda c, i: c.common_sense.judge_plausibility(i),
        format_result=lambda r: _safe(lambda r: f"Plausibility: {r.plausibility.value} ({r.domain.value})", r),
        sub_patterns=["common sense", "is it plausible", "realistic"]),
    EngineMethod("practical_advice",
        invoke=lambda c, i: c.common_sense.practical_advice(i),
        format_result=lambda r: _safe(lambda r: f"Practical: {_fmt(r)}", r),
        sub_patterns=["practically speaking", "practical advice"]),
    EngineMethod("sanity_check",
        invoke=lambda c, i: c.common_sense.sanity_check(i),
        format_result=lambda r: _safe(lambda r: f"Sanity check: {_fmt(r)}", r),
        sub_patterns=["sanity check", "does this make sense", "sniff test"]),
], description="Judges plausibility, provides practical advice, and performs sanity checks")


# ═════════════════════════════════════════════════════════════════════════════
# STRATEGIC ENGINES
# ═════════════════════════════════════════════════════════════════════════════

_reg("planning", [
    EngineMethod("create_plan",
        invoke=lambda c, i: c.planning.create_plan(i),
        format_result=lambda r: _safe(lambda r: f"Plan ({len(r.steps)} steps): {'; '.join(s.description for s in r.steps[:3])}", r),
        sub_patterns=["make a plan", "steps to", "action plan"]),
    EngineMethod("evaluate_plan",
        invoke=lambda c, i: c.planning.evaluate_plan(i),
        format_result=lambda r: _safe(lambda r: f"Evaluation: {_fmt(r)}", r),
        sub_patterns=["evaluate this plan", "is this a good plan"]),
    EngineMethod("contingency_plan",
        invoke=lambda c, i: c.planning.contingency_plan(i),
        format_result=lambda r: _safe(lambda r: f"Contingency: {_fmt(r)}", r),
        sub_patterns=["contingency plan", "plan b", "backup plan", "what if it fails"]),
], description="Creates action plans, evaluates strategies, and designs contingency plans")

_reg("negotiation", [
    EngineMethod("strategize",
        invoke=lambda c, i: c.negotiation_intelligence.strategize(i),
        format_result=lambda r: f"Strategy: {r.get('strategy','')[:80]}" if r else "",
        sub_patterns=["negotiate", "negotiation strategy"]),
    EngineMethod("find_compromise",
        invoke=lambda c, i: c.negotiation_intelligence.find_compromise(i),
        format_result=lambda r: _safe(lambda r: f"Compromise: {_fmt(r)}", r),
        sub_patterns=["compromise", "meet in the middle", "win-win"]),
    EngineMethod("persuasion_plan",
        invoke=lambda c, i: c.negotiation_intelligence.persuasion_plan(i),
        format_result=lambda r: _safe(lambda r: f"Persuasion: {_fmt(r)}", r),
        sub_patterns=["persuade them", "convince them"]),
    EngineMethod("win_win",
        invoke=lambda c, i: c.negotiation_intelligence.win_win(i),
        format_result=lambda r: _safe(lambda r: f"Win-win: {_fmt(r)}", r),
        sub_patterns=["win-win solution", "mutual benefit", "both sides happy"]),
], description="Develops negotiation strategies, finds compromises, and plans persuasion")

_reg("game_theory", [
    EngineMethod("analyze_game",
        invoke=lambda c, i: c.game_theory.analyze_game(i),
        format_result=lambda r: f"Game: {r.get('game_type','?')} — equilibrium: {r.get('equilibrium','?')}" if r else "",
        sub_patterns=["game theory", "strategic move", "nash equilibrium"]),
    EngineMethod("predict_behavior",
        invoke=lambda c, i: c.game_theory.predict_behavior(i, ""),
        format_result=lambda r: _safe(lambda r: f"Prediction: {_fmt(r)}", r),
        sub_patterns=["rational behavior", "they would do"]),
    EngineMethod("design_mechanism",
        invoke=lambda c, i: c.game_theory.design_mechanism(i),
        format_result=lambda r: _safe(lambda r: f"Mechanism: {_fmt(r)}", r),
        sub_patterns=["incentive design", "mechanism design"]),
], description="Analyzes strategic interactions, predicts rational behavior, and designs mechanisms")

_reg("adversarial", [
    EngineMethod("red_team",
        invoke=lambda c, i: c.adversarial_thinking.red_team(i),
        format_result=lambda r: _safe(lambda r: f"Red team: {len(r.vulnerabilities)} vulns, resilience: {r.overall_resilience:.2f}", r),
        sub_patterns=["red team", "attack vector", "vulnerability"]),
    EngineMethod("premortem",
        invoke=lambda c, i: c.adversarial_thinking.premortem(i),
        format_result=lambda r: _safe(lambda r: f"Premortem: {_fmt(r)}", r),
        sub_patterns=["premortem", "what could go wrong", "failure mode"]),
    EngineMethod("devils_advocate",
        invoke=lambda c, i: c.adversarial_thinking.devils_advocate(i),
        format_result=lambda r: _safe(lambda r: f"Devil's advocate: {_fmt(r)}", r),
        sub_patterns=["devil's advocate", "argue against", "poke holes"]),
    EngineMethod("vulnerability_chain",
        invoke=lambda c, i: c.adversarial_thinking.vulnerability_chain(i),
        format_result=lambda r: _safe(lambda r: f"Vulnerability chain: {_fmt(r)}", r),
        sub_patterns=["chain of vulnerabilities", "attack chain", "exploit path"]),
], description="Red-teams ideas, performs premortem analysis, and plays devil advocate")

_reg("debate", [
    EngineMethod("build_argument",
        invoke=lambda c, i: c.debate.build_argument(i),
        format_result=lambda r: _safe(lambda r: f"Argument ({r.strength.value}): {r.claim[:100]}", r),
        sub_patterns=["debate this", "argue for", "make a case"]),
    EngineMethod("generate_rebuttal",
        invoke=lambda c, i: c.debate.generate_rebuttal(i),
        format_result=lambda r: _safe(lambda r: f"Rebuttal: {_fmt(r)}", r),
        sub_patterns=["rebuttal to", "counter this", "respond to"]),
    EngineMethod("structured_debate",
        invoke=lambda c, i: c.debate.structured_debate(i),
        format_result=lambda r: _safe(lambda r: f"Debate: {_fmt(r)}", r),
        sub_patterns=["full debate", "pro and con"]),
], description="Builds arguments, generates rebuttals, and facilitates structured debates")

_reg("constraint", [
    EngineMethod("check_feasibility",
        invoke=lambda c, i: c.constraint_solver.check_feasibility(i),
        format_result=lambda r: f"Feasibility: {r.get('feasibility','?')}" if r else "",
        sub_patterns=["is it feasible", "constraint", "resource limit"]),
    EngineMethod("optimize",
        invoke=lambda c, i: c.constraint_solver.optimize(i),
        format_result=lambda r: _safe(lambda r: f"Optimized: {_fmt(r)}", r),
        sub_patterns=["optimize", "best allocation", "maximize"]),
], description="Checks feasibility within constraints and optimizes resource allocation")

_reg("systems", [
    EngineMethod("model_system",
        invoke=lambda c, i: c.systems_thinking.model_system(i),
        format_result=lambda r: _safe(lambda r: f"System: {r.name} — {len(r.components)} components", r),
        sub_patterns=["complex system", "interconnected", "ecosystem"]),
    EngineMethod("find_leverage_points",
        invoke=lambda c, i: c.systems_thinking.find_leverage_points(i),
        format_result=lambda r: _safe(lambda r: f"Leverage: {_fmt(r)}", r),
        sub_patterns=["leverage point", "biggest impact", "where to intervene"]),
    EngineMethod("analyze_feedback_loops",
        invoke=lambda c, i: c.systems_thinking.analyze_feedback_loops(i),
        format_result=lambda r: _safe(lambda r: f"Feedback loops: {_fmt(r)}", r),
        sub_patterns=["feedback loop", "vicious cycle", "virtuous cycle"]),
], description="Models complex systems, finds leverage points, and analyzes feedback loops")

_reg("synthesis", [
    EngineMethod("extract_insights",
        invoke=lambda c, i: c.information_synthesis.extract_insights(i),
        format_result=lambda r: f"Insights: {'; '.join(x.get('insight','')[:50] for x in r.get('insights',[])[:3])}" if r and r.get('insights') else "",
        sub_patterns=["key takeaways", "bottom line", "distill"]),
    EngineMethod("executive_summary",
        invoke=lambda c, i: c.information_synthesis.executive_summary(i),
        format_result=lambda r: _safe(lambda r: f"Summary: {_fmt(r)}", r),
        sub_patterns=["summarize", "executive summary", "boil down"]),
    EngineMethod("build_framework",
        invoke=lambda c, i: c.information_synthesis.build_framework(i),
        format_result=lambda r: _safe(lambda r: f"Framework: {_fmt(r)}", r),
        sub_patterns=["framework for", "mental model", "structured approach"]),
    EngineMethod("meta_analysis",
        invoke=lambda c, i: c.information_synthesis.meta_analysis(i),
        format_result=lambda r: _safe(lambda r: f"Meta-analysis: {_fmt(r)}", r),
        sub_patterns=["meta analysis", "synthesize research", "consensus view"]),
], description="Extracts insights, creates summaries, builds frameworks, and performs meta-analysis")


# ═════════════════════════════════════════════════════════════════════════════
# REMAINING ENGINES
# ═════════════════════════════════════════════════════════════════════════════

_reg("spatial", [
    EngineMethod("build_spatial_model",
        invoke=lambda c, i: c.spatial_reasoning.build_spatial_model(i),
        format_result=lambda r: _safe(lambda r: f"Spatial: {len(r.entities)} entities, {len(r.relations)} relations", r),
        sub_patterns=["where is", "layout of", "position of"]),
    EngineMethod("find_path",
        invoke=lambda c, i: c.spatial_reasoning.find_path(i),
        format_result=lambda r: _safe(lambda r: f"Path: {_fmt(r)}", r),
        sub_patterns=["route to", "navigate to", "direction to"]),
], description="Builds spatial models, reasons about locations, and finds paths")

_reg("temporal", [
    EngineMethod("estimate_duration",
        invoke=lambda c, i: c.temporal_reasoning.estimate_duration(i),
        format_result=lambda r: _safe(lambda r: f"Time: {r.expected} (range: {r.minimum}–{r.maximum})", r),
        sub_patterns=["how long", "duration of"]),
    EngineMethod("build_timeline",
        invoke=lambda c, i: c.temporal_reasoning.build_timeline(i),
        format_result=lambda r: _safe(lambda r: f"Timeline: {_fmt(r)}", r),
        sub_patterns=["timeline of", "sequence of", "chronology"]),
    EngineMethod("create_schedule",
        invoke=lambda c, i: c.temporal_reasoning.create_schedule(i),
        format_result=lambda r: _safe(lambda r: f"Schedule: {_fmt(r)}", r),
        sub_patterns=["schedule for", "when should"]),
    EngineMethod("timeline_analysis",
        invoke=lambda c, i: c.temporal_reasoning.timeline_analysis(i),
        format_result=lambda r: _safe(lambda r: f"Timeline analysis: {_fmt(r)}", r),
        sub_patterns=["timeline analysis", "temporal pattern", "historical sequence"]),
], description="Estimates durations, builds timelines, creates schedules, and analyzes temporal patterns")

_reg("knowledge", [
    EngineMethod("build_knowledge_graph",
        invoke=lambda c, i: c.knowledge_integration.build_knowledge_graph(i),
        format_result=lambda r: _safe(lambda r: f"Knowledge: {r.topic} — {len(r.nodes)} nodes in {', '.join(r.domains[:2])}", r),
        sub_patterns=["connection between", "how does x relate"]),
    EngineMethod("find_connections",
        invoke=lambda c, i: c.knowledge_integration.find_connections(i),
        format_result=lambda r: _safe(lambda r: f"Connections: {_fmt(r)}", r),
        sub_patterns=["link between", "interdisciplinary"]),
    EngineMethod("knowledge_gap",
        invoke=lambda c, i: c.knowledge_integration.knowledge_gap(i),
        format_result=lambda r: _safe(lambda r: f"Knowledge gap: {_fmt(r)}", r),
        sub_patterns=["knowledge gap", "what do i not know", "learning path"]),
], description="Builds knowledge graphs, finds connections, and identifies learning gaps")

_reg("intuition", [
    EngineMethod("gut_feeling",
        invoke=lambda c, i: c.intuition.gut_feeling(i),
        format_result=lambda r: _safe(lambda r: f"Intuition: {r.gut_feeling} (trust: {'yes' if r.should_trust else 'caution'})", r),
        sub_patterns=["gut feeling", "instinct", "something feels off"]),
    EngineMethod("recognize_patterns",
        invoke=lambda c, i: c.intuition.recognize_patterns(i),
        format_result=lambda r: _safe(lambda r: f"Pattern: {_fmt(r)}", r),
        sub_patterns=["pattern in", "i notice", "trending"]),
    EngineMethod("vibe_check",
        invoke=lambda c, i: c.intuition.vibe_check(i),
        format_result=lambda r: _safe(lambda r: f"Vibe: {_fmt(r)}", r),
        sub_patterns=["vibe of", "sense that"]),
    EngineMethod("pattern_alert",
        invoke=lambda c, i: c.intuition.pattern_alert(i),
        format_result=lambda r: _safe(lambda r: f"Alert: {_fmt(r)}", r),
        sub_patterns=["pattern alert", "anomaly", "something is off", "weak signal"]),
], description="Provides gut feelings, recognizes patterns, and alerts on anomalies")

_reg("moral_imagination", [
    EngineMethod("envision_alternatives",
        invoke=lambda c, i: c.moral_imagination.envision_alternatives(i),
        format_result=lambda r: _safe(lambda r: f"Moral vision: {r.alternative[:120]}", r),
        sub_patterns=["ideal world", "how things should be"]),
    EngineMethod("empathy_mapping",
        invoke=lambda c, i: c.moral_imagination.empathy_mapping(i),
        format_result=lambda r: _safe(lambda r: f"Empathy map: {_fmt(r)}", r),
        sub_patterns=["empathy for", "understand their suffering"]),
], description="Envisions ethical alternatives and creates empathy maps")


# ═════════════════════════════════════════════════════════════════════════════
# ULTIMATE ADVANCEMENT ENGINES
# ═════════════════════════════════════════════════════════════════════════════

_reg("quantum_cognition", [
    EngineMethod("superpose",
        invoke=lambda c, i: c.quantum_cognition.superpose(i),
        format_result=lambda r: _safe(lambda r: f"Quantum: {r.collapsed_answer[:120]} (confidence: {r.confidence:.2f})", r),
        sub_patterns=["superposition", "all possibilities", "multiple hypotheses"]),
    EngineMethod("entangle",
        invoke=lambda c, i: c.quantum_cognition.entangle(i),
        format_result=lambda r: _safe(lambda r: f"Entangled: {_fmt(r)}", r),
        sub_patterns=["hidden correlation", "entangle", "deep connection"]),
    EngineMethod("collapse",
        invoke=lambda c, i: c.quantum_cognition.collapse(i),
        format_result=lambda r: _safe(lambda r: f"Collapsed: {_fmt(r)}", r),
        sub_patterns=["resolve ambiguity", "definitive answer", "collapse"]),
    EngineMethod("tunnel",
        invoke=lambda c, i: c.quantum_cognition.tunnel(i),
        format_result=lambda r: _safe(lambda r: f"Tunneled: {_fmt(r)}", r),
        sub_patterns=["bypass barrier", "tunnel through", "unconventional solution"]),
], description="Quantum-inspired superposition reasoning, entanglement analysis, and barrier tunneling")

_reg("swarm", [
    EngineMethod("swarm_solve",
        invoke=lambda c, i: c.swarm_intelligence.swarm_solve(i),
        format_result=lambda r: _safe(lambda r: f"Swarm: {r.consensus[:120]} ({len(r.agents)} agents)", r),
        sub_patterns=["collective intelligence", "swarm solve", "crowd wisdom"]),
    EngineMethod("stigmergy",
        invoke=lambda c, i: c.swarm_intelligence.stigmergy(i),
        format_result=lambda r: _safe(lambda r: f"Stigmergy: {_fmt(r)}", r),
        sub_patterns=["pheromone", "indirect coordination", "stigmergy"]),
    EngineMethod("flocking",
        invoke=lambda c, i: c.swarm_intelligence.flocking(i),
        format_result=lambda r: _safe(lambda r: f"Flocking: {_fmt(r)}", r),
        sub_patterns=["align ideas", "flock", "coordinate"]),
    EngineMethod("hive_mind",
        invoke=lambda c, i: c.swarm_intelligence.hive_mind(i),
        format_result=lambda r: _safe(lambda r: f"Hive mind: {_fmt(r)}", r),
        sub_patterns=["committee", "hive mind", "panel of experts"]),
], description="Emergent collective intelligence from swarms of diverse virtual agents")

_reg("prophecy", [
    EngineMethod("prophecy",
        invoke=lambda c, i: c.temporal_prophecy.prophecy(i),
        format_result=lambda r: _safe(lambda r: f"Prophecy: {r.most_likely[:120]} ({len(r.branches)} branches)", r),
        sub_patterns=["predict future", "what will happen next", "future scenario"]),
    EngineMethod("timeline_map",
        invoke=lambda c, i: c.temporal_prophecy.timeline_map(i),
        format_result=lambda r: _safe(lambda r: f"Timeline: {_fmt(r)}", r),
        sub_patterns=["map consequences", "cascade of effects", "timeline of consequences"]),
    EngineMethod("convergence_analysis",
        invoke=lambda c, i: c.temporal_prophecy.convergence_analysis(i),
        format_result=lambda r: _safe(lambda r: f"Convergence: {_fmt(r)}", r),
        sub_patterns=["converging trends", "inflection point", "tipping point"]),
    EngineMethod("black_swan_scan",
        invoke=lambda c, i: c.temporal_prophecy.black_swan_scan(i),
        format_result=lambda r: _safe(lambda r: f"Black swan: {_fmt(r)}", r),
        sub_patterns=["black swan", "unlikely event", "surprise risk"]),
], description="Deep future scenario modeling with branching timelines and black swan detection")

_reg("evolution", [
    EngineMethod("stress_evolve",
        invoke=lambda c, i: c.adversarial_evolution.stress_evolve(i),
        format_result=lambda r: _safe(lambda r: f"Evolved: {r.final_form[:120]} (fitness +{r.fitness_improvement:.2f})", r),
        sub_patterns=["evolve this", "harden", "anti-fragile"]),
    EngineMethod("mutation_test",
        invoke=lambda c, i: c.adversarial_evolution.mutation_test(i),
        format_result=lambda r: _safe(lambda r: f"Mutation: {_fmt(r)}", r),
        sub_patterns=["mutate", "perturbation", "what if i change"]),
    EngineMethod("survival_of_fittest",
        invoke=lambda c, i: c.adversarial_evolution.survival_of_fittest(i),
        format_result=lambda r: _safe(lambda r: f"Fittest: {_fmt(r)}", r),
        sub_patterns=["tournament", "survival of fittest", "compete"]),
    EngineMethod("immune_response",
        invoke=lambda c, i: c.adversarial_evolution.immune_response(i),
        format_result=lambda r: _safe(lambda r: f"Immune: {_fmt(r)}", r),
        sub_patterns=["build defenses", "immune", "adapt to threat"]),
], description="Self-attacking anti-fragility through evolutionary stress testing and mutation")

_reg("cross_dimensional", [
    EngineMethod("hypercube_analyze",
        invoke=lambda c, i: c.cross_dimensional_reasoning.hypercube_analyze(i),
        format_result=lambda r: _safe(lambda r: f"Hypercube ({r.dimensions_analyzed}D): {r.insight[:120]}", r),
        sub_patterns=["multi-dimensional", "hypercube", "all dimensions"]),
    EngineMethod("dimensional_collapse",
        invoke=lambda c, i: c.cross_dimensional_reasoning.dimensional_collapse(i),
        format_result=lambda r: _safe(lambda r: f"Collapsed: {_fmt(r)}", r),
        sub_patterns=["simplify complexity", "reduce dimensions", "collapse"]),
    EngineMethod("fractal_pattern",
        invoke=lambda c, i: c.cross_dimensional_reasoning.fractal_pattern(i),
        format_result=lambda r: _safe(lambda r: f"Fractal: {_fmt(r)}", r),
        sub_patterns=["fractal", "self-similar", "pattern at every scale"]),
    EngineMethod("dimensional_bridge",
        invoke=lambda c, i: c.cross_dimensional_reasoning.dimensional_bridge(i),
        format_result=lambda r: _safe(lambda r: f"Bridge: {_fmt(r)}", r),
        sub_patterns=["structural bridge", "isomorphism", "domain bridge"]),
], description="N-dimensional pattern mapping, fractal detection, and cross-domain structural bridging")

_reg("existential", [
    EngineMethod("resolve_paradox",
        invoke=lambda c, i: c.existential_calculus.resolve_paradox(i),
        format_result=lambda r: _safe(lambda r: f"Paradox [{r.truth_value}]: {r.resolution[:120]}", r),
        sub_patterns=["paradox", "self-referential", "contradictory"]),
    EngineMethod("godel_check",
        invoke=lambda c, i: c.existential_calculus.godel_check(i),
        format_result=lambda r: _safe(lambda r: f"Gödel: {_fmt(r)}", r),
        sub_patterns=["incompleteness", "undecidable", "godel"]),
    EngineMethod("strange_loop",
        invoke=lambda c, i: c.existential_calculus.strange_loop(i),
        format_result=lambda r: _safe(lambda r: f"Strange loop: {_fmt(r)}", r),
        sub_patterns=["strange loop", "tangled hierarchy", "self-reference"]),
    EngineMethod("koan_solve",
        invoke=lambda c, i: c.existential_calculus.koan_solve(i),
        format_result=lambda r: _safe(lambda r: f"Koan: {_fmt(r)}", r),
        sub_patterns=["koan", "unanswerable", "dissolve the question"]),
], description="Paradox resolution, Gödelian analysis, strange loop detection, and koan dissolution")


# Auto-generated — always in sync
ALL_ENGINE_KEYS = list(ENGINE_REGISTRY.keys())


# ═════════════════════════════════════════════════════════════════════════════
# ENGINE CHAINS — pipelines where outputs feed into next engine
# ═════════════════════════════════════════════════════════════════════════════

ENGINE_CHAINS = {
    "deep_analysis": {
        "engines": ["causal", "counterfactual", "decision"],
        "patterns": ["why did this happen and what should i", "analyze this deeply", "full analysis"],
        "description": "Root cause → What-if → Decision recommendation",
    },
    "emotional_support": {
        "engines": ["emotional", "emotional_reg", "wisdom"],
        "patterns": ["i'm really struggling", "help me cope", "i'm devastated"],
        "description": "Empathize → Regulate → Offer wisdom",
    },
    "critical_thinking": {
        "engines": ["logic", "error_detect", "hypothesis"],
        "patterns": ["is this argument valid", "check this reasoning", "verify this claim"],
        "description": "Validate logic → Find errors → Generate alternatives",
    },
    "creative_exploration": {
        "engines": ["creative", "conceptual_blend", "analogy_gen"],
        "patterns": ["help me create something new", "innovative solution needed", "creative breakthrough"],
        "description": "Brainstorm → Blend concepts → Explain by analogy",
    },
    "strategic_planning": {
        "engines": ["systems", "game_theory", "planning"],
        "patterns": ["strategic plan for", "how to approach this strategically", "long-term strategy"],
        "description": "Model system → Analyze dynamics → Create plan",
    },
    "philosophical_inquiry": {
        "engines": ["philosophy", "dialectic", "wisdom"],
        "patterns": ["what is the meaning of", "deep question about", "philosophical implications"],
        "description": "Philosophize → Dialectical thinking → Wisdom",
    },
    "quantum_deep_analysis": {
        "engines": ["quantum_cognition", "cross_dimensional", "prophecy"],
        "patterns": ["quantum deep analysis", "analyze from all dimensions", "ultimate analysis"],
        "description": "Superposition → N-dimensional mapping → Future projection",
    },
    "antifragile_evolution": {
        "engines": ["adversarial", "evolution", "swarm"],
        "patterns": ["make this bulletproof", "ultimate stress test", "evolve and harden"],
        "description": "Red team → Evolve through attacks → Swarm validate",
    },
    "paradox_exploration": {
        "engines": ["existential", "philosophy", "wisdom"],
        "patterns": ["deep paradox", "unanswerable question about", "existential crisis"],
        "description": "Paradox resolution → Philosophical grounding → Wisdom",
    },
}


# ═════════════════════════════════════════════════════════════════════════════
# ENGINE DEPENDENCIES — ordering constraints for dynamic chain construction
# Maps engine_key → list of engines whose output it can consume (predecessors).
# When both are selected, the predecessor runs first and its output feeds forward.
# ═════════════════════════════════════════════════════════════════════════════

ENGINE_DEPENDENCIES: Dict[str, List[str]] = {
    # Reasoning chains: cause → what-if → decision
    "decision": ["causal"],
    "counterfactual": ["causal"],

    # Emotional pipeline: understand → regulate
    "emotional_reg": ["emotional"],

    # Critical pipeline: logic → error check
    "error_detect": ["logic"],

    # Creative pipeline: brainstorm → blend → analogy
    "conceptual_blend": ["creative"],
    "analogy_gen": ["conceptual_blend"],

    # Strategic pipeline: systems → planning
    "planning": ["systems"],
    "game_theory": ["systems"],

    # Philosophical pipeline: philosophy → dialectic → wisdom
    "dialectic": ["philosophy"],

    # Theory of Mind → Perspective
    "perspective": ["mind"],

    # Hypothesis → experiment design
    "hypothesis": ["curiosity"],

    # Advancement pipeline: quantum \u2192 cross-dimensional \u2192 prophecy
    "cross_dimensional": ["quantum_cognition"],
    "prophecy": ["cross_dimensional"],

    # Evolution pipeline: adversarial \u2192 evolution \u2192 swarm
    "evolution": ["adversarial"],
    "swarm": ["evolution"],

    # Existential pipeline: existential \u2192 philosophy
    "existential": ["philosophy"],
}


def validate_dependencies():
    """Check for circular dependencies via topological sort at startup."""
    visited = set()
    visiting = set()

    def _visit(node):
        if node in visiting:
            raise ValueError(f"Circular dependency detected involving engine: {node}")
        if node in visited:
            return
        visiting.add(node)
        for dep in ENGINE_DEPENDENCIES.get(node, []):
            _visit(dep)
        visiting.remove(node)
        visited.add(node)

    for key in ENGINE_DEPENDENCIES:
        _visit(key)


def get_execution_order(selected_engines: list) -> list:
    """Return engines sorted by dependency order (predecessors first)."""
    # Build in-degree map for selected engines only
    order = []
    remaining = set(selected_engines)

    # Simple topological insertion
    while remaining:
        # Find engines with no unresolved dependencies
        ready = []
        for engine in remaining:
            deps = ENGINE_DEPENDENCIES.get(engine, [])
            unresolved = [d for d in deps if d in remaining]
            if not unresolved:
                ready.append(engine)

        if not ready:
            # Cycle or no progress — just add remaining in original order
            for e in selected_engines:
                if e in remaining:
                    order.append(e)
            break

        for e in ready:
            if e in remaining:
                order.append(e)
                remaining.discard(e)

    return order


# Validate at module load time
try:
    validate_dependencies()
except ValueError as e:
    import warnings
    warnings.warn(f"Engine dependency issue: {e}")
