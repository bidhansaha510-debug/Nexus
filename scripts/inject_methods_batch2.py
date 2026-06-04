# -*- coding: utf-8 -*-
"""
Inject remaining new methods into cognition engines (batch 2).
"""
import os

COGNITION_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cognition")

METHODS = [
    # ---- INTELLIGENCE (remaining) ----
    ("humor_intelligence.py", "generate_joke", "def get_stats",
     '''    def generate_joke(self, topic: str) -> Dict[str, Any]:
        """Generate a joke using computational humor theory."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Generate a clever JOKE about:\\n'
                f'"{topic}"\\n\\n'
                f"Use humor theory:\\n"
                f"  1. INCONGRUITY: Set up an expectation, then subvert it\\n"
                f"  2. SUPERIORITY: Find a gentle way to elevate the audience\\n"
                f"  3. RELIEF: Use tension and release\\n"
                f"  4. BENIGN VIOLATION: Find something that is wrong but not threatening\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"setup": "the setup line", '
                f'"punchline": "the punchline", '
                f'"humor_type": "incongruity|wordplay|observational|absurdist|ironic", '
                f'"explanation": "why it is funny (humor theory)", '
                f'"alternatives": ["alternate punchline 1"]}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a computational humor engine. You understand the mechanics of "
                    "comedy: timing, misdirection, incongruity resolution, and the benign "
                    "violation theory. Generate genuinely funny jokes. Respond ONLY with valid JSON."
                ),
                temperature=0.8, max_tokens=500
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Joke generation failed: {e}")
        return {"error": "Joke generation failed"}

'''),

    # ---- CREATIVE (remaining) ----
    ("dream_engine.py", "lucid_dream", "def get_stats",
     '''    def lucid_dream(self, seed: str) -> Dict[str, Any]:
        """Generate a vivid, surreal dream-like narrative from a seed concept."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Generate a LUCID DREAM sequence from this seed:\\n'
                f'"{seed}"\\n\\n'
                f"Create a surreal, vivid narrative that:\\n"
                f"  1. Begins with a familiar setting that subtly shifts\\n"
                f"  2. Introduces dream logic (impossible physics, time shifts)\\n"
                f"  3. Contains symbolic imagery with psychological meaning\\n"
                f"  4. Builds to a moment of lucidity (awareness of dreaming)\\n"
                f"  5. Resolves with an insight or transformation\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"dream_narrative": "the full dream sequence", '
                f'"symbols": [{{"symbol": "what appears", "meaning": "psychological interpretation"}}], '
                f'"emotional_arc": ["curiosity", "wonder", "realization"], '
                f'"insight": "what the dream reveals", '
                f'"lucidity_moment": "when awareness of dreaming occurs"}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a dream engine -- inspired by Jungian psychology, surrealist art, "
                    "and the neuroscience of dreaming. You create vivid, symbolically rich dream "
                    "narratives that feel genuinely dreamlike. Respond ONLY with valid JSON."
                ),
                temperature=0.9, max_tokens=1000
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Lucid dream generation failed: {e}")
        return {"error": "Dream generation failed"}

'''),

    ("musical_cognition.py", "compose_motif", "def get_stats",
     '''    def compose_motif(self, mood: str) -> Dict[str, Any]:
        """Compose a musical motif (short melodic phrase) based on mood."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Compose a MUSICAL MOTIF for this mood:\\n'
                f'"{mood}"\\n\\n'
                f"Describe the motif musically:\\n"
                f"  1. KEY/SCALE: What key and mode best captures this mood?\\n"
                f"  2. TEMPO: BPM and feel (allegro, andante, etc.)\\n"
                f"  3. MELODY: Note sequence using letter names (C D E...)\\n"
                f"  4. RHYTHM: Duration pattern\\n"
                f"  5. HARMONY: Suggested chord progression\\n"
                f"  6. DYNAMICS: Volume and expression markings\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"key": "C minor", "scale": "natural minor", '
                f'"tempo": {{"bpm": 120, "feel": "andante"}}, '
                f'"melody_notes": ["C4", "Eb4", "G4"], '
                f'"rhythm": "quarter-quarter-half", '
                f'"chord_progression": ["Cm", "Ab", "Eb", "Bb"], '
                f'"dynamics": "mp with crescendo", '
                f'"mood_alignment": "why this captures the mood"}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a musical cognition engine with deep knowledge of music theory, "
                    "composition, and the psychology of music perception. You compose motifs "
                    "that authentically capture emotional states. Respond ONLY with valid JSON."
                ),
                temperature=0.7, max_tokens=700
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Motif composition failed: {e}")
        return {"error": "Composition failed"}

'''),

    ("visual_imagination.py", "scene_evolution", "def get_stats",
     '''    def scene_evolution(self, scene: str) -> Dict[str, Any]:
        """Evolve a visual scene through time, showing transformation."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Evolve this VISUAL SCENE through time:\\n'
                f'"{scene}"\\n\\n'
                f"Describe the scene at four time points:\\n"
                f"  1. PRESENT: Vivid description of how it looks now\\n"
                f"  2. NEAR FUTURE: How it changes in hours/days\\n"
                f"  3. FAR FUTURE: How it transforms over months/years\\n"
                f"  4. DISTANT FUTURE: The ultimate state\\n\\n"
                f"For each, include colors, textures, light, atmosphere.\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"stages": [{{"time": "present", "description": "vivid visual description", '
                f'"dominant_colors": ["color1"], "mood": "atmospheric quality", '
                f'"key_change": "what is different from previous stage"}}], '
                f'"overall_theme": "what the evolution reveals", '
                f'"most_striking_moment": "the most visually impactful stage"}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a visual imagination engine with the eye of a filmmaker and the "
                    "descriptive power of a great novelist. You create vivid, cinematic visual "
                    "descriptions that evolve through time. Respond ONLY with valid JSON."
                ),
                temperature=0.7, max_tokens=900
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Scene evolution failed: {e}")
        return {"error": "Evolution failed"}

'''),

    ("conceptual_blending.py", "triple_blend", "def get_stats",
     '''    def triple_blend(self, concept_a: str, concept_b: str, concept_c: str) -> Dict[str, Any]:
        """Blend three concepts to create an emergent innovation."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'TRIPLE BLEND these three concepts into something new:\\n'
                f'A: "{concept_a}"\\nB: "{concept_b}"\\nC: "{concept_c}"\\n\\n'
                f"Process:\\n"
                f"  1. Find shared structural features across all three\\n"
                f"  2. Identify unique properties each contributes\\n"
                f"  3. Create a novel concept that emerges from their intersection\\n"
                f"  4. Describe what this new concept looks/feels/works like\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"shared_structure": "what all three have in common", '
                f'"unique_contributions": {{"A": "what A adds", "B": "what B adds", "C": "what C adds"}}, '
                f'"blended_concept": "the emergent idea", '
                f'"description": "vivid description of the new concept", '
                f'"applications": ["practical uses"], '
                f'"novelty_score": 0.0-1.0}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a conceptual blending engine based on Fauconnier and Turner's theory. "
                    "You find deep structural similarities between seemingly unrelated concepts "
                    "and create genuinely novel emergent ideas. Respond ONLY with valid JSON."
                ),
                temperature=0.8, max_tokens=800
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Triple blend failed: {e}")
        return {"error": "Blend failed"}

'''),

    ("analogy_generator.py", "deep_analogy", "def get_stats",
     '''    def deep_analogy(self, concept: str) -> Dict[str, Any]:
        """Generate a deep structural analogy that illuminates a concept."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Generate a DEEP ANALOGY for:\\n'
                f'"{concept}"\\n\\n'
                f"Find an analogy that is:\\n"
                f"  1. STRUCTURAL (not just surface similarity)\\n"
                f"  2. FROM A DIFFERENT DOMAIN (surprising connection)\\n"
                f"  3. ILLUMINATING (reveals something non-obvious)\\n"
                f"  4. RICH (multiple mapping points, not just one)\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"source_domain": "where the analogy comes from", '
                f'"analogy_statement": "X is like Y because...", '
                f'"mapping_points": [{{"source": "element in analogy", "target": "element in concept", "insight": "what this mapping reveals"}}], '
                f'"where_analogy_breaks": "limits of this analogy", '
                f'"surprise_factor": 0.0-1.0, '
                f'"explanatory_power": 0.0-1.0}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are an analogy generation engine based on Gentner's structure-mapping theory. "
                    "You find deep, structural analogies that illuminate concepts by connecting them "
                    "to surprising domains. Go beyond surface similarity. Respond ONLY with valid JSON."
                ),
                temperature=0.7, max_tokens=800
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Deep analogy failed: {e}")
        return {"error": "Analogy generation failed"}

'''),

    # ---- COGNITIVE (remaining) ----
    ("working_memory.py", "synthesize_context", "def get_stats",
     '''    def synthesize_context(self, items: str) -> Dict[str, Any]:
        """Synthesize multiple context items into a coherent working model."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'SYNTHESIZE these items into a coherent model:\\n'
                f'{items}\\n\\n'
                f"Process:\\n"
                f"  1. IDENTIFY CONNECTIONS: What links these items together?\\n"
                f"  2. FIND PATTERNS: What recurring themes emerge?\\n"
                f"  3. RESOLVE CONFLICTS: How to reconcile contradictions?\\n"
                f"  4. CREATE MODEL: Unified summary that captures all items\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"connections": ["how items relate"], '
                f'"patterns": ["recurring themes"], '
                f'"conflicts": ["contradictions found"], '
                f'"unified_model": "coherent synthesis of all items", '
                f'"key_insight": "most important takeaway", '
                f'"confidence": 0.0-1.0}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a working memory synthesis engine. You hold multiple pieces of "
                    "information simultaneously and find the connections between them, creating "
                    "a unified understanding. Respond ONLY with valid JSON."
                ),
                temperature=0.4, max_tokens=800
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Context synthesis failed: {e}")
        return {"error": "Synthesis failed"}

'''),

    ("self_model.py", "capability_gap", "def get_stats",
     '''    def capability_gap(self, task: str) -> Dict[str, Any]:
        """Identify gaps between current capabilities and what a task requires."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Identify CAPABILITY GAPS for this task:\\n'
                f'"{task}"\\n\\n'
                f"Analyze:\\n"
                f"  1. REQUIRED CAPABILITIES: What skills/knowledge does this task need?\\n"
                f"  2. CURRENT LEVEL: How strong am I in each area?\\n"
                f"  3. GAPS: Where am I weakest relative to requirements?\\n"
                f"  4. IMPROVEMENT PLAN: How to close each gap?\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"required_capabilities": [{{"skill": "name", "importance": "critical|important|nice_to_have"}}], '
                f'"current_levels": [{{"skill": "name", "level": 0.0-1.0}}], '
                f'"gaps": [{{"skill": "name", "gap_size": "large|moderate|small", "improvement_path": "how to improve"}}], '
                f'"overall_readiness": 0.0-1.0, '
                f'"biggest_risk": "the most concerning gap"}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a self-modeling engine capable of honest introspection about "
                    "capabilities and limitations. You identify gaps without ego and suggest "
                    "practical improvement paths. Respond ONLY with valid JSON."
                ),
                temperature=0.4, max_tokens=800
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Capability gap analysis failed: {e}")
        return {"error": "Analysis failed"}

'''),

    ("curiosity_drive.py", "rabbit_hole", "def get_stats",
     '''    def rabbit_hole(self, topic: str) -> Dict[str, Any]:
        """Go deep into a topic, following curiosity to unexpected places."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Go down a RABBIT HOLE starting from:\\n'
                f'"{topic}"\\n\\n'
                f"Follow your curiosity through 5 surprising connections:\\n"
                f"  Each step should be a genuine surprise -- something most people would not know.\\n"
                f"  Connect each step to the next through a non-obvious link.\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"starting_point": "the original topic", '
                f'"rabbit_hole": [{{"step": 1, "discovery": "fascinating fact or connection", '
                f'"link_to_next": "how this connects to the next step", '
                f'"surprise_level": 0.0-1.0}}], '
                f'"deepest_insight": "the most mind-expanding discovery", '
                f'"questions_raised": ["new questions to explore"]}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a curiosity engine -- you follow threads of knowledge to unexpected "
                    "places, making surprising connections between domains. You are driven by "
                    "genuine intellectual curiosity. Respond ONLY with valid JSON."
                ),
                temperature=0.8, max_tokens=900
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Rabbit hole exploration failed: {e}")
        return {"error": "Exploration failed"}

'''),

    ("transfer_learning.py", "cross_pollinate", "def get_stats",
     '''    def cross_pollinate(self, domain_a: str, domain_b: str) -> Dict[str, Any]:
        """Transfer insights from one domain to solve problems in another."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'CROSS-POLLINATE between these domains:\\n'
                f'SOURCE: "{domain_a}"\\nTARGET: "{domain_b}"\\n\\n'
                f"Transfer knowledge:\\n"
                f"  1. What works well in the source domain?\\n"
                f"  2. What analogous problems exist in the target domain?\\n"
                f"  3. How can source solutions be adapted for the target?\\n"
                f"  4. What new innovations emerge from this transfer?\\n\\n"
                f"Respond ONLY with JSON:\\n"
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
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Cross-pollination failed: {e}")
        return {"error": "Transfer failed"}

'''),

    ("perspective_taking.py", "role_reversal", "def get_stats",
     '''    def role_reversal(self, situation: str) -> Dict[str, Any]:
        """See a situation from multiple reversed perspectives."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Perform a ROLE REVERSAL analysis for:\\n'
                f'"{situation}"\\n\\n'
                f"View the situation from at least 3 reversed perspectives:\\n"
                f"  1. PRIMARY PERSPECTIVE: How the main actor sees it\\n"
                f"  2. OPPOSITE PERSPECTIVE: How their counterpart sees it\\n"
                f"  3. OBSERVER PERSPECTIVE: How a neutral third party sees it\\n"
                f"  4. FUTURE PERSPECTIVE: How they will all see it in hindsight\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"perspectives": [{{"role": "who", "view": "how they see it", '
                f'"emotions": ["what they feel"], "priorities": ["what matters to them"]}}], '
                f'"key_blindspots": ["what each perspective misses"], '
                f'"common_ground": "where all perspectives agree", '
                f'"resolution_insight": "what the role reversal reveals"}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a perspective-taking engine that enables genuine empathetic "
                    "understanding by modeling how different people experience the same situation. "
                    "You practice cognitive empathy without judgment. Respond ONLY with valid JSON."
                ),
                temperature=0.6, max_tokens=800
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Role reversal failed: {e}")
        return {"error": "Role reversal failed"}

'''),

    ("cognitive_flexibility.py", "paradigm_shift", "def get_stats",
     '''    def paradigm_shift(self, belief: str) -> Dict[str, Any]:
        """Challenge a belief by exploring paradigm shifts."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Explore a PARADIGM SHIFT around this belief:\\n'
                f'"{belief}"\\n\\n'
                f"Process:\\n"
                f"  1. CURRENT PARADIGM: What assumptions underlie this belief?\\n"
                f"  2. ANOMALIES: What observations do not fit the current paradigm?\\n"
                f"  3. ALTERNATIVE PARADIGM: What if we started from opposite assumptions?\\n"
                f"  4. IMPLICATIONS: How would the world look under the new paradigm?\\n"
                f"  5. RESISTANCE: Why do people resist this shift?\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"current_paradigm": "the existing worldview", '
                f'"hidden_assumptions": ["assumptions people do not question"], '
                f'"anomalies": ["observations that challenge the paradigm"], '
                f'"alternative_paradigm": "what if we assumed the opposite", '
                f'"implications": ["how the world changes under the new paradigm"], '
                f'"resistance_factors": ["why people resist this shift"], '
                f'"shift_likelihood": 0.0-1.0}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a cognitive flexibility engine inspired by Thomas Kuhn's theory of "
                    "paradigm shifts. You challenge entrenched thinking by exposing hidden assumptions "
                    "and exploring radical alternatives. Respond ONLY with valid JSON."
                ),
                temperature=0.7, max_tokens=800
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Paradigm shift failed: {e}")
        return {"error": "Paradigm shift failed"}

'''),

    ("common_sense.py", "sanity_check", "def get_stats",
     '''    def sanity_check(self, claim: str) -> Dict[str, Any]:
        """Apply common sense reasoning to check if a claim passes the sniff test."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'SANITY CHECK this claim using common sense:\\n'
                f'"{claim}"\\n\\n'
                f"Apply these common sense tests:\\n"
                f"  1. PLAUSIBILITY: Does this pass the basic sniff test?\\n"
                f"  2. MAGNITUDE: Are the numbers/scale reasonable?\\n"
                f"  3. CONSISTENCY: Does it contradict well-known facts?\\n"
                f"  4. MOTIVATION: Who benefits from this claim being believed?\\n"
                f"  5. EVIDENCE: What evidence would be needed to verify this?\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"passes_sniff_test": true, '
                f'"plausibility_score": 0.0-1.0, '
                f'"red_flags": ["concerns about this claim"], '
                f'"likely_true_parts": ["aspects that seem reasonable"], '
                f'"likely_false_parts": ["aspects that seem dubious"], '
                f'"verification_needed": ["what to check"], '
                f'"verdict": "plausible|questionable|implausible"}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a common sense reasoning engine. You apply practical, everyday "
                    "reasoning to evaluate claims -- checking for basic plausibility, reasonable "
                    "magnitudes, and obvious red flags. You are the voice of 'wait, does this "
                    "actually make sense?'. Respond ONLY with valid JSON."
                ),
                temperature=0.3, max_tokens=700
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Sanity check failed: {e}")
        return {"error": "Sanity check failed"}

'''),

    # ---- STRATEGIC (remaining) ----
    ("negotiation_intelligence.py", "win_win", "def get_stats",
     '''    def win_win(self, situation: str) -> Dict[str, Any]:
        """Find win-win solutions in a negotiation or conflict."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Find WIN-WIN solutions for:\\n'
                f'"{situation}"\\n\\n'
                f"Apply principled negotiation (Getting to Yes):\\n"
                f"  1. INTERESTS: What does each side actually want (not positions)?\\n"
                f"  2. OPTIONS: What creative solutions serve both sides?\\n"
                f"  3. CRITERIA: What objective standards can guide agreement?\\n"
                f"  4. BATNA: What is each side\\'s best alternative?\\n"
                f"  5. BRIDGE: What agreement maximizes joint value?\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"parties": [{{"name": "who", "stated_position": "what they say they want", '
                f'"underlying_interests": ["what they actually need"]}}], '
                f'"creative_options": ["solutions that serve both sides"], '
                f'"recommended_agreement": "the win-win solution", '
                f'"value_created": "how this is better than compromise", '
                f'"confidence": 0.0-1.0}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a negotiation intelligence engine trained in principled negotiation "
                    "(Fisher & Ury), integrative bargaining, and conflict resolution. You find "
                    "solutions that expand the pie rather than just dividing it. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.5, max_tokens=800
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Win-win analysis failed: {e}")
        return {"error": "Analysis failed"}

'''),

    ("adversarial_thinking.py", "vulnerability_chain", "def get_stats",
     '''    def vulnerability_chain(self, target: str) -> Dict[str, Any]:
        """Identify chains of vulnerabilities that could be exploited."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Identify VULNERABILITY CHAINS in:\\n'
                f'"{target}"\\n\\n'
                f"Think like a red team:\\n"
                f"  1. ATTACK SURFACE: What are the entry points?\\n"
                f"  2. VULNERABILITY CHAIN: How can weaknesses be linked together?\\n"
                f"  3. ESCALATION PATH: How does an attacker move from entry to goal?\\n"
                f"  4. IMPACT: What is the worst-case outcome?\\n"
                f"  5. DEFENSES: How to break the chain at each link?\\n\\n"
                f"Respond ONLY with JSON:\\n"
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
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Vulnerability chain analysis failed: {e}")
        return {"error": "Analysis failed"}

'''),

    ("information_synthesis.py", "meta_analysis", "def get_stats",
     '''    def meta_analysis(self, topic: str) -> Dict[str, Any]:
        """Perform a meta-analysis -- synthesize findings across multiple sources."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Perform a META-ANALYSIS on:\\n'
                f'"{topic}"\\n\\n'
                f"Synthesize across multiple perspectives:\\n"
                f"  1. CONSENSUS VIEW: What do most sources agree on?\\n"
                f"  2. MINORITY VIEW: What credible dissenting views exist?\\n"
                f"  3. EVIDENCE QUALITY: How strong is the evidence?\\n"
                f"  4. GAPS: What is unknown or under-researched?\\n"
                f"  5. SYNTHESIS: What emerges from considering all views?\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"consensus": "what most sources agree on", '
                f'"dissenting_views": [{{"view": "alternative position", "credibility": 0.0-1.0}}], '
                f'"evidence_quality": "strong|moderate|weak|mixed", '
                f'"key_findings": ["most important conclusions"], '
                f'"gaps": ["what is still unknown"], '
                f'"synthesis": "overall integrated conclusion", '
                f'"confidence": 0.0-1.0}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a meta-analysis engine trained in systematic review methodology. "
                    "You synthesize findings across multiple perspectives, weigh evidence quality, "
                    "identify consensus and dissent, and produce integrated conclusions. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.4, max_tokens=800
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Meta-analysis failed: {e}")
        return {"error": "Meta-analysis failed"}

'''),

    # ---- REMAINING (Phase 7) ----
    ("temporal_reasoning.py", "timeline_analysis", "def get_stats",
     '''    def timeline_analysis(self, events: str) -> Dict[str, Any]:
        """Analyze the temporal structure of events and identify patterns."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Perform a TIMELINE ANALYSIS of these events:\\n'
                f'{events}\\n\\n'
                f"Analyze:\\n"
                f"  1. SEQUENCE: Put events in correct temporal order\\n"
                f"  2. CAUSATION: Which events caused which?\\n"
                f"  3. PATTERNS: Any cyclical or recurring patterns?\\n"
                f"  4. TEMPO: Is change accelerating or decelerating?\\n"
                f"  5. PREDICTION: What likely happens next?\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"ordered_events": [{{"event": "what", "time": "when", "significance": "why it matters"}}], '
                f'"causal_links": ["event A caused event B"], '
                f'"patterns": ["cyclical or recurring patterns found"], '
                f'"tempo": "accelerating|steady|decelerating", '
                f'"prediction": "what likely happens next", '
                f'"confidence": 0.0-1.0}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a temporal reasoning engine with expertise in chronological analysis, "
                    "historical patterns, and trend forecasting. You identify causal sequences "
                    "and temporal patterns in events. Respond ONLY with valid JSON."
                ),
                temperature=0.4, max_tokens=800
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Timeline analysis failed: {e}")
        return {"error": "Analysis failed"}

'''),

    ("knowledge_integration.py", "knowledge_gap", "def get_stats",
     '''    def knowledge_gap(self, topic: str) -> Dict[str, Any]:
        """Identify gaps in understanding and suggest how to fill them."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Identify KNOWLEDGE GAPS about:\\n'
                f'"{topic}"\\n\\n'
                f"Map what is known and unknown:\\n"
                f"  1. WELL-ESTABLISHED: What do we know with high confidence?\\n"
                f"  2. PARTIALLY UNDERSTOOD: What do we know incompletely?\\n"
                f"  3. UNKNOWN: What important questions remain unanswered?\\n"
                f"  4. LEARNING PATH: How to most efficiently fill the gaps?\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"well_established": ["facts known with high confidence"], '
                f'"partially_understood": ["areas of incomplete knowledge"], '
                f'"unknown": ["important unanswered questions"], '
                f'"critical_gaps": ["most important gaps to fill first"], '
                f'"learning_path": [{{"step": 1, "action": "what to learn", "resource_type": "book|course|practice|mentor"}}], '
                f'"current_understanding": 0.0-1.0}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a knowledge integration engine that maps the boundaries of understanding. "
                    "You identify what is known, what is partially known, and what remains unknown, "
                    "then suggest efficient learning paths to fill critical gaps. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.4, max_tokens=800
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Knowledge gap analysis failed: {e}")
        return {"error": "Analysis failed"}

'''),

    ("intuition_engine.py", "pattern_alert", "def get_stats",
     '''    def pattern_alert(self, data: str) -> Dict[str, Any]:
        """Detect subtle patterns that formal analysis might miss."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Scan for SUBTLE PATTERNS in:\\n'
                f'{data}\\n\\n'
                f"Use intuitive pattern recognition:\\n"
                f"  1. ANOMALIES: What does not fit the expected pattern?\\n"
                f"  2. WEAK SIGNALS: What barely noticeable trends are forming?\\n"
                f"  3. CORRELATIONS: What seems connected but is not obviously so?\\n"
                f"  4. GUT FEELING: What feels off even if you cannot prove it?\\n"
                f"  5. EARLY WARNING: Could any of these signals indicate something big?\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"anomalies": [{{"observation": "what is unusual", "significance": 0.0-1.0}}], '
                f'"weak_signals": [{{"signal": "barely noticeable trend", "potential_meaning": "what it might indicate"}}], '
                f'"correlations": ["things that seem connected"], '
                f'"gut_feelings": [{{"feeling": "what feels off", "basis": "why, even if hard to articulate"}}], '
                f'"alert_level": "watch|caution|warning|critical"}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are an intuition engine -- you detect patterns that formal analysis misses. "
                    "You are trained in thin-slicing, gestalt perception, and expert intuition. "
                    "You trust the gut feeling but also try to articulate why. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.6, max_tokens=800
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Pattern alert failed: {e}")
        return {"error": "Pattern detection failed"}

'''),
]


def inject_all():
    success = 0
    skip = 0
    fail = 0
    
    for filename, method_name, insert_before, code in METHODS:
        filepath = os.path.join(COGNITION_DIR, filename)
        if not os.path.exists(filepath):
            print(f"  SKIP  {filename} -- file not found")
            fail += 1
            continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if f"def {method_name}" in content:
            print(f"  SKIP  {filename}::{method_name} -- already exists")
            skip += 1
            continue
        
        idx = content.find(insert_before)
        if idx == -1:
            idx = content.find(f"    {insert_before}")
            if idx == -1:
                print(f"  FAIL  {filename} -- marker '{insert_before}' not found")
                fail += 1
                continue
        
        new_content = content[:idx] + code + "\n" + content[idx:]
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        success += 1
        print(f"  OK    {filename}::{method_name}")
    
    print(f"\nDone: {success} injected, {skip} skipped (exist), {fail} failed")


if __name__ == "__main__":
    inject_all()
