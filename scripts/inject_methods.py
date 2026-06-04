# -*- coding: utf-8 -*-
"""
Inject new methods into cognition engines.
Handles encoding properly for Windows.
"""
import os, sys

COGNITION_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cognition")

# Method templates: (filename, method_name, insert_before_text, method_code)
METHODS = [
    # ---- INTELLIGENCE ENGINES ----
    ("emotional_intelligence.py", "emotional_forecast", "def get_stats",
     '''    def emotional_forecast(self, situation: str) -> Dict[str, Any]:
        """Predict emotional trajectory and suggest preemptive strategies."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Predict the EMOTIONAL TRAJECTORY of this situation:\\n'
                f'"{situation}"\\n\\n'
                f"Think through:\\n"
                f"  1. CURRENT EMOTIONAL STATE: What emotions are likely present now?\\n"
                f"  2. TRIGGERS AHEAD: What upcoming events could shift emotions?\\n"
                f"  3. TRAJECTORY: How will emotions evolve over time?\\n"
                f"  4. RISK POINTS: When is emotional distress most likely?\\n"
                f"  5. PREEMPTIVE STRATEGIES: What can be done NOW to improve the trajectory?\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"current_emotions": ["emotion1"], '
                f'"trajectory": [{{"timeframe": "soon/medium/later", "predicted_emotion": "emotion", "intensity": 0.0-1.0}}], '
                f'"risk_points": ["when distress is likely"], '
                f'"strategies": ["preemptive action"], '
                f'"confidence": 0.0-1.0}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are an emotional intelligence engine with deep expertise in affective "
                    "forecasting, emotional regulation, and psychological resilience. You predict "
                    "how emotions will evolve and suggest evidence-based preemptive strategies. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.5, max_tokens=800
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Emotional forecast failed: {e}")
        return {"error": "Forecast failed"}

'''),

    ("emotional_regulation.py", "grounding_exercise", "def get_stats",
     '''    def grounding_exercise(self, distress: str) -> Dict[str, Any]:
        """Generate a personalized grounding exercise for emotional distress."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Create a personalized GROUNDING EXERCISE for this distress:\\n'
                f'"{distress}"\\n\\n'
                f"Design a step-by-step exercise that:\\n"
                f"  1. ACKNOWLEDGES the emotion without judgment\\n"
                f"  2. ENGAGES the senses (5-4-3-2-1 technique or similar)\\n"
                f"  3. REORIENTS to the present moment\\n"
                f"  4. BUILDS a bridge to calm\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"exercise_name": "name", '
                f'"steps": [{{"step": 1, "instruction": "what to do", "duration_seconds": 30}}], '
                f'"total_duration_minutes": 5, '
                f'"technique_type": "sensory|breathing|cognitive|movement", '
                f'"why_it_works": "psychological basis"}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are an emotional regulation specialist trained in CBT, DBT, and "
                    "mindfulness-based interventions. You create personalized grounding exercises "
                    "that are practical, evidence-based, and immediately actionable. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.6, max_tokens=800
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Grounding exercise failed: {e}")
        return {"error": "Exercise generation failed"}

'''),

    ("social_cognition.py", "power_dynamics", "def get_stats",
     '''    def power_dynamics(self, situation: str) -> Dict[str, Any]:
        """Analyze the power dynamics and social hierarchies in a situation."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Analyze the POWER DYNAMICS in this situation:\\n'
                f'"{situation}"\\n\\n'
                f"Examine:\\n"
                f"  1. ACTORS: Who holds power and what kind?\\n"
                f"  2. POWER SOURCES: Formal authority, expertise, information, social capital\\n"
                f"  3. DYNAMICS: How does power flow and shift?\\n"
                f"  4. HIDDEN POWER: Who has influence that is not obvious?\\n"
                f"  5. LEVERAGE: How can power be gained or shared more equitably?\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"actors": [{{"name": "who", "power_type": "formal|expert|informational|social", "level": "high|medium|low"}}], '
                f'"power_flows": ["how power moves between actors"], '
                f'"hidden_influences": ["non-obvious power holders"], '
                f'"leverage_points": ["how to shift the balance"], '
                f'"confidence": 0.0-1.0}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a social dynamics analyst with expertise in organizational behavior, "
                    "political science, and sociology. You identify visible and hidden power structures "
                    "with precision. Respond ONLY with valid JSON."
                ),
                temperature=0.5, max_tokens=800
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Power dynamics analysis failed: {e}")
        return {"error": "Analysis failed"}

'''),

    ("cultural_intelligence.py", "bridge_cultures", "def get_stats",
     '''    def bridge_cultures(self, context: str) -> Dict[str, Any]:
        """Find common ground between different cultural perspectives."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Find ways to BRIDGE CULTURES in this context:\\n'
                f'"{context}"\\n\\n'
                f"Analyze:\\n"
                f"  1. CULTURAL PERSPECTIVES: What viewpoints are at play?\\n"
                f"  2. SHARED VALUES: What values do all cultures share here?\\n"
                f"  3. FRICTION POINTS: Where do cultural assumptions clash?\\n"
                f"  4. BRIDGE STRATEGIES: How to find common ground?\\n"
                f"  5. COMMUNICATION: How should messages be adapted?\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"perspectives": [{{"culture": "which", "viewpoint": "how they see it"}}], '
                f'"shared_values": ["common ground"], '
                f'"friction_points": ["where conflict arises"], '
                f'"bridges": ["strategies for connection"], '
                f'"communication_tips": ["how to adapt messages"], '
                f'"confidence": 0.0-1.0}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a cultural intelligence expert with deep knowledge of cross-cultural "
                    "communication, Hofstede dimensions, and intercultural competence. You find "
                    "authentic bridges between worldviews. Respond ONLY with valid JSON."
                ),
                temperature=0.6, max_tokens=800
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Cultural bridging failed: {e}")
        return {"error": "Bridging failed"}

'''),

    ("linguistic_intelligence.py", "rhetorical_analysis", "def get_stats",
     '''    def rhetorical_analysis(self, text: str) -> Dict[str, Any]:
        """Analyze rhetorical devices, persuasion techniques, and linguistic power."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Perform a RHETORICAL ANALYSIS of this text:\\n'
                f'"{text[:500]}"\\n\\n'
                f"Identify:\\n"
                f"  1. RHETORICAL DEVICES: metaphor, analogy, repetition, etc.\\n"
                f"  2. PERSUASION TECHNIQUES: ethos, pathos, logos\\n"
                f"  3. FRAMING: How is the argument framed?\\n"
                f"  4. TONE: What emotional register is used?\\n"
                f"  5. EFFECTIVENESS: How persuasive is this text and why?\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"devices": [{{"device": "name", "example": "quote from text", "effect": "what it achieves"}}], '
                f'"persuasion": {{"ethos": "credibility appeal", "pathos": "emotional appeal", "logos": "logical appeal"}}, '
                f'"framing": "how the argument is framed", '
                f'"tone": "formal|conversational|urgent|persuasive|etc", '
                f'"effectiveness_score": 0.0-1.0, '
                f'"strengths": ["what works"], '
                f'"weaknesses": ["what could be stronger"]}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a rhetoric and discourse analysis expert with training in classical "
                    "rhetoric, modern linguistics, and communication studies. You identify persuasion "
                    "techniques with precision. Respond ONLY with valid JSON."
                ),
                temperature=0.4, max_tokens=800
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Rhetorical analysis failed: {e}")
        return {"error": "Analysis failed"}

'''),

    ("narrative_intelligence.py", "story_arc_design", "def get_stats",
     '''    def story_arc_design(self, theme: str) -> Dict[str, Any]:
        """Design a compelling story arc with narrative structure."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Design a STORY ARC for this theme:\\n'
                f'"{theme}"\\n\\n'
                f"Structure using the hero journey / three-act structure:\\n"
                f"  1. SETUP: Establish the world, character, and stakes\\n"
                f"  2. INCITING INCIDENT: What disrupts the status quo?\\n"
                f"  3. RISING ACTION: Escalating challenges and complications\\n"
                f"  4. CLIMAX: The decisive moment of maximum tension\\n"
                f"  5. RESOLUTION: How the story resolves and what changes\\n"
                f"  6. THEME: The deeper message or insight\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"title": "story title", '
                f'"protagonist": {{"name": "who", "flaw": "internal weakness", "desire": "what they want"}}, '
                f'"acts": [{{"act": 1, "name": "Setup", "key_events": ["event1"], "emotional_tone": "hopeful"}}], '
                f'"climax": "the pivotal moment", '
                f'"theme": "the deeper meaning", '
                f'"narrative_hooks": ["what keeps the audience engaged"]}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a master storyteller and narrative designer fluent in the hero's journey, "
                    "three-act structure, Kishitenketsu, and modern narrative theory. "
                    "You craft emotionally compelling story arcs. Respond ONLY with valid JSON."
                ),
                temperature=0.7, max_tokens=900
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Story arc design failed: {e}")
        return {"error": "Design failed"}

'''),

    ("wisdom_engine.py", "paradox_resolution", "def get_stats",
     '''    def paradox_resolution(self, paradox: str) -> Dict[str, Any]:
        """Resolve or illuminate a paradox through wisdom and deep reflection."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Resolve or illuminate this PARADOX:\\n'
                f'"{paradox}"\\n\\n'
                f"Approach with wisdom:\\n"
                f"  1. STATE THE PARADOX: What makes this seemingly contradictory?\\n"
                f"  2. EXAMINE ASSUMPTIONS: What hidden assumptions create the contradiction?\\n"
                f"  3. FIND THE RESOLUTION: Is there a higher-order truth that resolves it?\\n"
                f"  4. WISDOM: What life lesson does this paradox teach?\\n"
                f"  5. PRACTICAL APPLICATION: How does this insight apply to daily life?\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"paradox_stated": "the contradiction in clear terms", '
                f'"hidden_assumptions": ["assumption that creates the contradiction"], '
                f'"resolution": "how to resolve or transcend the paradox", '
                f'"wisdom": "the deeper insight", '
                f'"practical_application": "how to apply this in life", '
                f'"related_paradoxes": ["similar paradoxes"]}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a wisdom engine drawing from Stoic, Buddhist, Taoist, and Western "
                    "philosophical traditions. You approach paradoxes not as problems to solve but "
                    "as doorways to deeper understanding. Respond ONLY with valid JSON."
                ),
                temperature=0.6, max_tokens=800
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Paradox resolution failed: {e}")
        return {"error": "Resolution failed"}

'''),

    ("theory_of_mind.py", "predict_reaction", "def get_stats",
     '''    def predict_reaction(self, action: str, person_context: str = "") -> Dict[str, Any]:
        """Predict how someone will react to an action based on their perspective."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            ctx = f"\\nPerson context: {person_context}" if person_context else ""
            prompt = (
                f'Predict the REACTION to this action:\\n'
                f'ACTION: "{action}"{ctx}\\n\\n'
                f"Model the other person\\'s perspective:\\n"
                f"  1. BELIEFS: What do they likely believe about this situation?\\n"
                f"  2. DESIRES: What do they want?\\n"
                f"  3. EMOTIONS: What will they feel initially?\\n"
                f"  4. IMMEDIATE REACTION: What will they do/say right away?\\n"
                f"  5. LATER REFLECTION: How will they feel about it after time?\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"predicted_beliefs": ["what they think"], '
                f'"predicted_desires": ["what they want"], '
                f'"initial_emotions": [{{"emotion": "name", "intensity": 0.0-1.0}}], '
                f'"immediate_reaction": "what they will do/say", '
                f'"later_reflection": "how they will feel over time", '
                f'"best_approach": "how to frame the action for best reception", '
                f'"confidence": 0.0-1.0}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a theory of mind engine -- expert at modeling other people\\'s mental "
                    "states, beliefs, desires, and likely reactions. You practice cognitive empathy "
                    "to predict behavior accurately. Respond ONLY with valid JSON."
                ),
                temperature=0.5, max_tokens=800
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Reaction prediction failed: {e}")
        return {"error": "Prediction failed"}

'''),

    # ---- CREATIVE ENGINES ----
    ("creative_synthesis.py", "scamper", "def get_stats",
     '''    def scamper(self, concept: str) -> Dict[str, Any]:
        """Apply SCAMPER creative thinking to generate novel ideas."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Apply the SCAMPER creative framework to:\\n'
                f'"{concept}"\\n\\n'
                f"Generate ideas for each SCAMPER dimension:\\n"
                f"  S - SUBSTITUTE: What can be replaced?\\n"
                f"  C - COMBINE: What can be merged with something else?\\n"
                f"  A - ADAPT: How can it be adjusted for a different use?\\n"
                f"  M - MODIFY: What can be magnified, minimized, or changed?\\n"
                f"  P - PUT TO OTHER USE: What else could this be used for?\\n"
                f"  E - ELIMINATE: What can be removed to simplify?\\n"
                f"  R - REVERSE: What if we flip the approach?\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"substitute": [{{"idea": "what to substitute", "benefit": "why"}}], '
                f'"combine": [{{"idea": "what to combine", "benefit": "why"}}], '
                f'"adapt": [{{"idea": "how to adapt", "benefit": "why"}}], '
                f'"modify": [{{"idea": "what to modify", "benefit": "why"}}], '
                f'"put_to_other_use": [{{"idea": "alternative use", "benefit": "why"}}], '
                f'"eliminate": [{{"idea": "what to remove", "benefit": "why"}}], '
                f'"reverse": [{{"idea": "what to flip", "benefit": "why"}}], '
                f'"best_ideas": ["top 3 most promising ideas"]}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a creative thinking engine using the SCAMPER method -- one of the most "
                    "powerful systematic creativity techniques. Generate genuinely novel and useful ideas. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.8, max_tokens=1000
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"SCAMPER failed: {e}")
        return {"error": "SCAMPER failed"}

'''),

    # ---- COGNITIVE ENGINES ----
    ("attention_control.py", "prioritize_tasks", "def get_stats",
     '''    def prioritize_tasks(self, tasks: str) -> Dict[str, Any]:
        """Prioritize a list of tasks using Eisenhower matrix and cognitive load analysis."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'PRIORITIZE these tasks using the Eisenhower matrix:\\n'
                f'{tasks}\\n\\n'
                f"For each task:\\n"
                f"  1. Classify as urgent/not-urgent AND important/not-important\\n"
                f"  2. Estimate cognitive load (high/medium/low)\\n"
                f"  3. Recommend sequencing based on energy and focus requirements\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"tasks": [{{"task": "name", "urgent": true, "important": true, '
                f'"quadrant": "do_first|schedule|delegate|eliminate", '
                f'"cognitive_load": "high|medium|low", "recommended_time": "morning|afternoon|evening"}}], '
                f'"suggested_order": ["task in optimal order"], '
                f'"quick_wins": ["tasks that can be done in under 5 minutes"]}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a cognitive attention and task prioritization engine. You apply the "
                    "Eisenhower matrix, cognitive load theory, and energy management principles "
                    "to help humans focus on what truly matters. Respond ONLY with valid JSON."
                ),
                temperature=0.3, max_tokens=800
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Task prioritization failed: {e}")
        return {"error": "Prioritization failed"}

'''),

    ("error_detection.py", "premortem", "def get_stats",
     '''    def premortem(self, plan: str) -> Dict[str, Any]:
        """Perform a premortem analysis -- imagine the plan has failed and work backwards."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Perform a PREMORTEM on this plan:\\n'
                f'"{plan}"\\n\\n'
                f"Imagine it is 6 months from now and this plan has FAILED spectacularly.\\n"
                f"  1. FAILURE MODES: What are the most likely reasons it failed?\\n"
                f"  2. BLIND SPOTS: What did the planners not see?\\n"
                f"  3. ASSUMPTION FAILURES: Which assumptions turned out to be wrong?\\n"
                f"  4. EXTERNAL SHOCKS: What unexpected events derailed things?\\n"
                f"  5. PREVENTIVE ACTIONS: What could have been done to prevent each failure?\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"failure_modes": [{{"failure": "what went wrong", "probability": 0.0-1.0, '
                f'"severity": "catastrophic|major|moderate|minor", '
                f'"preventive_action": "what to do now"}}], '
                f'"blind_spots": ["what is being overlooked"], '
                f'"assumption_risks": ["assumptions that could be wrong"], '
                f'"overall_risk_level": "high|medium|low"}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a premortem analysis engine -- you imagine failure and work backwards "
                    "to identify risks before they happen. You are trained in prospective hindsight, "
                    "which research shows dramatically improves risk identification. "
                    "Be thorough and honest about risks. Respond ONLY with valid JSON."
                ),
                temperature=0.5, max_tokens=900
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Premortem failed: {e}")
        return {"error": "Premortem failed"}

'''),

    # ---- STRATEGIC ENGINES ----
    ("systems_thinking.py", "leverage_points", "def get_stats",
     '''    def leverage_points(self, system: str) -> Dict[str, Any]:
        """Identify leverage points in a system where small changes produce big effects."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Identify LEVERAGE POINTS in this system:\\n'
                f'"{system}"\\n\\n'
                f"Using Donella Meadows hierarchy of leverage points:\\n"
                f"  1. PARAMETERS: Numbers (least powerful)\\n"
                f"  2. BUFFERS: Sizes of stabilizing stocks\\n"
                f"  3. STRUCTURE: Material stocks and flows\\n"
                f"  4. DELAYS: Lengths of delays relative to system changes\\n"
                f"  5. FEEDBACK LOOPS: Strength of negative/positive feedback\\n"
                f"  6. INFORMATION FLOWS: Who has access to information\\n"
                f"  7. RULES: Incentives, punishments, constraints\\n"
                f"  8. SELF-ORGANIZATION: Power to change system structure\\n"
                f"  9. GOALS: The purpose of the system\\n"
                f"  10. PARADIGMS: The mindset out of which the system arises (most powerful)\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"leverage_points": [{{"level": "paradigm|goal|rules|information|feedback|delay|structure|buffer|parameter", '
                f'"description": "the specific leverage point", '
                f'"intervention": "what to do", "expected_impact": "high|medium|low"}}], '
                f'"highest_leverage": "the single most impactful intervention", '
                f'"caution": "risks of intervening at this point"}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a systems thinking engine inspired by Donella Meadows. You identify "
                    "where small changes in complex systems produce large effects. You think in "
                    "terms of stocks, flows, feedback loops, and emergent behavior. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.5, max_tokens=900
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Leverage points analysis failed: {e}")
        return {"error": "Analysis failed"}

'''),

    ("planning_engine.py", "contingency_plan", "def get_stats",
     '''    def contingency_plan(self, plan: str) -> Dict[str, Any]:
        """Create contingency plans for when things go wrong."""
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}
        try:
            prompt = (
                f'Create CONTINGENCY PLANS for:\\n'
                f'"{plan}"\\n\\n'
                f"For each major risk:\\n"
                f"  1. TRIGGER: What specific event signals this risk is materializing?\\n"
                f"  2. RESPONSE: What immediate actions to take?\\n"
                f"  3. FALLBACK: What is Plan B if the response fails?\\n"
                f"  4. RECOVERY: How to get back on track?\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"contingencies": [{{"risk": "what could go wrong", '
                f'"probability": 0.0-1.0, "trigger": "warning sign", '
                f'"response": "what to do immediately", '
                f'"fallback": "Plan B", "recovery_time": "how long to recover"}}], '
                f'"overall_resilience": "high|medium|low"}}'
            )
            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a contingency planning engine trained in risk management, "
                    "business continuity, and military planning. You prepare for what could go wrong "
                    "so that teams can respond quickly and effectively. Respond ONLY with valid JSON."
                ),
                temperature=0.4, max_tokens=800
            )
            if response.success:
                return self._parse_json(response.text) or {"error": "Parse failed"}
        except Exception as e:
            logger.error(f"Contingency planning failed: {e}")
        return {"error": "Planning failed"}

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
        
        # Check if method already exists
        if f"def {method_name}" in content:
            print(f"  SKIP  {filename}::{method_name} -- already exists")
            skip += 1
            continue
        
        # Find insertion point
        idx = content.find(insert_before)
        if idx == -1:
            # Try with 'def ' prefix
            idx = content.find(f"    {insert_before}")
            if idx == -1:
                print(f"  FAIL  {filename} -- marker '{insert_before}' not found")
                fail += 1
                continue
        
        # Insert the new method before the marker
        new_content = content[:idx] + code + "\n" + content[idx:]
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        success += 1
        print(f"  OK    {filename}::{method_name}")
    
    print(f"\nDone: {success} injected, {skip} skipped (exist), {fail} failed")


if __name__ == "__main__":
    inject_all()
