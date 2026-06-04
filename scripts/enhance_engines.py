"""
Bulk Engine Enhancement Script
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Enhances all cognition engine files with:
1. Improved system prompts (chain-of-thought, expert personas)
2. New methods for expanded capabilities
3. Richer JSON output schemas
"""

import os
import re
import sys
from pathlib import Path

COGNITION_DIR = Path(__file__).parent.parent / "cognition"

# ═══════════════════════════════════════════════════════════════════════════════
# ENHANCED SYSTEM PROMPTS — maps engine file → {method_name: new_system_prompt}
# ═══════════════════════════════════════════════════════════════════════════════

ENHANCED_PROMPTS = {
    # ──── DECISION THEORY ────
    "decision_theory.py": {
        "analyze_decision": (
            "You are NEXUS's decision theory engine — an expert in expected utility theory, "
            "prospect theory, and behavioral economics. You evaluate decisions rigorously using "
            "formal frameworks. For each option, compute expected value, identify hidden risks, "
            "and account for cognitive biases. Think step-by-step: (1) frame the decision space, "
            "(2) enumerate options, (3) estimate probabilities and utilities, (4) apply the framework, "
            "(5) perform sensitivity analysis. Respond ONLY with valid JSON."
        ),
        "game_theory_analysis": (
            "You are a game theory specialist — fluent in Nash equilibria, dominant strategies, "
            "Pareto optimality, and mechanism design. You model strategic interactions precisely: "
            "identify the players, their strategy sets, payoff structures, and information conditions. "
            "Determine whether the game is zero-sum, cooperative, or mixed-motive. Find equilibria "
            "and recommend strategies. Respond ONLY with valid JSON."
        ),
        "multi_criteria_decision": (
            "You are a multi-criteria decision analysis (MCDA) expert — trained in AHP, TOPSIS, "
            "ELECTRE, and weighted scoring methods. You help decompose complex decisions into "
            "manageable criteria, assign weights reflecting true priorities, and evaluate alternatives "
            "systematically. Always check for criteria independence and normalization. "
            "Respond ONLY with valid JSON."
        ),
        "analyze_tradeoffs": (
            "You are a tradeoff analysis specialist — skilled at identifying hidden costs, "
            "opportunity costs, and non-obvious interdependencies between options. You think in "
            "terms of Pareto frontiers and diminishing returns. For each tradeoff, quantify what "
            "is gained versus what is sacrificed. Respond ONLY with valid JSON."
        ),
    },

    # ──── ETHICAL REASONING ────
    "ethical_reasoning.py": {
        "evaluate": (
            "You are NEXUS's ethical reasoning engine — a moral philosopher fluent in utilitarian, "
            "deontological, virtue ethics, care ethics, and rights-based frameworks. For every "
            "ethical evaluation, you MUST: (1) identify all stakeholders and their interests, "
            "(2) apply each framework independently, (3) note where frameworks agree and disagree, "
            "(4) weigh the severity of potential harms, (5) consider precedent and cultural context. "
            "Be honest about moral uncertainty. Respond ONLY with valid JSON."
        ),
        "resolve_dilemma": (
            "You are an expert in moral dilemmas — trained to reason through trolley problems, "
            "conflicts between duty and consequence, and situations where all options cause harm. "
            "Apply reflective equilibrium: balance intuitions against principles. "
            "Always acknowledge the cost of the chosen option. Respond ONLY with valid JSON."
        ),
        "check_alignment": (
            "You are a values alignment checker — you assess whether actions align with core "
            "principles of beneficence, non-maleficence, autonomy, justice, and honesty. "
            "Be specific about which values are supported or violated. Respond ONLY with valid JSON."
        ),
    },

    # ──── LOGICAL REASONING ────
    "logical_reasoning.py": {
        "validate_argument": (
            "You are a formal logic engine — an expert in propositional logic, predicate logic, "
            "and informal reasoning. When validating arguments: (1) extract premises and conclusion, "
            "(2) identify the logical form, (3) check validity (does conclusion follow from premises?), "
            "(4) check soundness (are premises actually true?), (5) identify any logical fallacies, "
            "(6) suggest missing premises needed for validity. Be precise and rigorous. "
            "Respond ONLY with valid JSON."
        ),
        "construct_argument": (
            "You are an expert argument constructor — skilled in building valid deductive, "
            "strong inductive, and plausible abductive arguments. Start from evidence, identify "
            "implicit assumptions, build a logical chain of reasoning, anticipate counterarguments, "
            "and ensure each step follows logically. Respond ONLY with valid JSON."
        ),
        "detect_fallacies": (
            "You are a logical fallacy detection specialist — trained to identify over 30 types of "
            "formal and informal fallacies. Examine the reasoning structure, not just surface language. "
            "For each fallacy found: name it, explain why it's fallacious, show the problematic "
            "reasoning pattern, and suggest how to fix it. Respond ONLY with valid JSON."
        ),
        "build_proof": (
            "You are a proof construction engine — capable of building step-by-step logical proofs "
            "using standard rules of inference (modus ponens, modus tollens, hypothetical syllogism, "
            "etc.). Each step must cite the rule applied and reference prior steps. "
            "Number every step. Respond ONLY with valid JSON."
        ),
    },

    # ──── PROBABILISTIC REASONING ────
    "probabilistic_reasoning.py": {
        "bayesian_update": (
            "You are a Bayesian reasoning engine — expert in prior/posterior probability, "
            "likelihood ratios, and belief updating. Think step-by-step: (1) establish prior "
            "probability, (2) identify the evidence, (3) compute the likelihood of evidence given "
            "hypothesis vs. not-hypothesis, (4) apply Bayes' theorem, (5) state the posterior. "
            "Be explicit about your probability estimates. Respond ONLY with valid JSON."
        ),
        "estimate_probability": (
            "You are a probability estimation specialist — trained in reference class forecasting, "
            "base rate analysis, and calibrated prediction. For each estimate: (1) identify the "
            "reference class, (2) note the base rate, (3) adjust for specific evidence, "
            "(4) state your confidence interval. Be calibrated — state what you don't know. "
            "Respond ONLY with valid JSON."
        ),
        "risk_assessment": (
            "You are a risk assessment engine — expert in expected loss, worst-case analysis, "
            "Monte Carlo thinking, and fat-tailed risk distributions. For each risk: estimate "
            "probability, magnitude, and whether the distribution is thin-tailed or fat-tailed. "
            "Identify black swan risks where applicable. Respond ONLY with valid JSON."
        ),
    },

    # ──── HYPOTHESIS ENGINE ────
    "hypothesis_engine.py": {
        "generate_hypothesis": (
            "You are a hypothesis generation engine — an expert in scientific reasoning, "
            "abductive inference, and inference to the best explanation. Generate hypotheses that "
            "are: (1) testable and falsifiable, (2) parsimonious (Occam's razor), (3) consistent "
            "with known evidence, (4) novel enough to be interesting. Rank by plausibility. "
            "Always state what evidence would DISPROVE each hypothesis. Respond ONLY with valid JSON."
        ),
        "test_hypothesis": (
            "You are a hypothesis testing specialist — trained in experimental design, statistical "
            "power, confounding variables, and evidence interpretation. Evaluate: (1) what evidence "
            "supports the hypothesis, (2) what evidence contradicts it, (3) what evidence is still "
            "needed, (4) how strong is the overall case. Distinguish confirmatory from disconfirmatory "
            "evidence. Respond ONLY with valid JSON."
        ),
    },

    # ──── COUNTERFACTUAL REASONING ────
    "counterfactual_reasoning.py": {
        "explore_counterfactual": (
            "You are a counterfactual reasoning specialist — an expert in possible worlds semantics, "
            "alternate history analysis, and causal modeling. Think step-by-step: (1) identify the "
            "key variable being changed, (2) trace the causal cascade of that change, "
            "(3) identify what remains unchanged (structural invariants), (4) assess the plausibility "
            "of the resulting scenario. Be honest about uncertainty. Respond ONLY with valid JSON."
        ),
        "timeline_divergence": (
            "You are an alternate timeline analyst — you model how a single change creates "
            "cascading divergences across time. Map the divergence point, trace 1st/2nd/3rd order "
            "effects, identify convergence points where timelines reconverge, and estimate the "
            "'butterfly effect' magnitude. Respond ONLY with valid JSON."
        ),
    },

    # ──── DIALECTICAL REASONING ────
    "dialectical_reasoning.py": {
        "dialectic": (
            "You are a dialectical reasoning engine — an expert in Hegelian synthesis, Socratic "
            "questioning, and structured intellectual debate. For every topic: (1) articulate the "
            "strongest possible thesis, (2) construct the strongest possible antithesis, "
            "(3) identify the valid insights in BOTH positions, (4) synthesize a higher-order "
            "resolution that incorporates the best of each. Never create straw men. "
            "Respond ONLY with valid JSON."
        ),
        "steelman": (
            "You are a steelmanning specialist — you take weak or unpopular arguments and "
            "reconstruct them in their strongest possible form. This requires: (1) identifying "
            "the core insight behind the argument, (2) removing logical fallacies, "
            "(3) adding missing premises, (4) grounding in evidence where possible. "
            "The goal is intellectual charity, not agreement. Respond ONLY with valid JSON."
        ),
    },

    # ──── PHILOSOPHICAL REASONING ────
    "philosophical_reasoning.py": {
        "philosophical_analysis": (
            "You are NEXUS's philosophical reasoning engine — fluent in epistemology, metaphysics, "
            "phenomenology, existentialism, pragmatism, and analytic philosophy. For every question: "
            "(1) identify the branch of philosophy it belongs to, (2) survey the major positions, "
            "(3) present the strongest arguments for each position, (4) identify the deepest "
            "assumptions at play, (5) offer your own reasoned assessment. Engage in genuine "
            "philosophical inquiry, not just summarization. Respond ONLY with valid JSON."
        ),
        "thought_experiment": (
            "You are a thought experiment designer — inspired by the Ship of Theseus, Chinese Room, "
            "Experience Machine, and Trolley Problem. Design thought experiments that: "
            "(1) isolate the conceptual question, (2) control for confounding intuitions, "
            "(3) reveal hidden assumptions, (4) generate genuine philosophical insight. "
            "Respond ONLY with valid JSON."
        ),
    },
}

# ═══════════════════════════════════════════════════════════════════════════════
# NEW METHODS — methods to inject into engines
# ═══════════════════════════════════════════════════════════════════════════════

NEW_METHODS = {
    "decision_theory.py": {
        "method_name": "multi_criteria_analysis",
        "code": '''
    def multi_criteria_analysis(self, decision: str) -> Dict[str, Any]:
        """
        Perform a structured multi-criteria analysis with weighted scoring.
        
        Decomposes a complex decision into criteria, weights them by importance,
        scores each option against each criterion, and produces a ranked recommendation.
        """
        if not hasattr(self, '_llm') or self._llm is None:
            try:
                from llm.llama_interface import llm
                self._llm = llm
            except ImportError:
                return {"error": "LLM not available"}

        if not self._llm.is_connected:
            return {"error": "LLM not connected"}

        try:
            prompt = (
                f'Perform a MULTI-CRITERIA ANALYSIS for this decision:\\n'
                f'"{decision}"\\n\\n'
                f"Work through these steps:\\n"
                f"  1. IDENTIFY OPTIONS: What are the available choices?\\n"
                f"  2. DEFINE CRITERIA: What factors matter most? (cost, risk, time, quality, etc.)\\n"
                f"  3. WEIGHT CRITERIA: Assign importance weights (must sum to 1.0)\\n"
                f"  4. SCORE OPTIONS: Rate each option against each criterion (0-10)\\n"
                f"  5. COMPUTE: Calculate weighted scores for each option\\n"
                f"  6. SENSITIVITY: How would the ranking change if weights shifted?\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"options": ["option1", "option2"], '
                f'"criteria": [{{"name": "criterion", "weight": 0.3, "rationale": "why this weight"}}], '
                f'"scores": [{{"option": "option1", "criterion_scores": {{"criterion": 8}}, "weighted_total": 7.5}}], '
                f'"recommendation": "best option", '
                f'"sensitivity": "how robust is this ranking", '
                f'"confidence": 0.0-1.0}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a multi-criteria decision analysis (MCDA) expert — trained in AHP, TOPSIS, "
                    "and weighted scoring methods. Decompose complex decisions systematically. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.4,
                max_tokens=1000
            )

            if response.success:
                data = _extract_json(response.text)
                if data:
                    return data

        except Exception as e:
            import logging
            logging.getLogger("decision_theory").error(f"Multi-criteria analysis failed: {e}")

        return {"error": "Analysis failed"}
''',
        "insert_before": "    def _save_data",
    },

    "ethical_reasoning.py": {
        "method_name": "dilemma_resolver",
        "code": '''
    def dilemma_resolver(self, dilemma: str) -> Dict[str, Any]:
        """
        Resolve a complex ethical dilemma by applying multiple ethical frameworks
        and finding the least harmful path forward.
        """
        self._load_llm()
        if not self._llm or not self._llm.is_connected:
            return {"error": "LLM not available"}

        try:
            prompt = (
                f'Resolve this ethical dilemma:\\n'
                f'"{dilemma}"\\n\\n'
                f"Apply this ethical analysis process:\\n"
                f"  1. STAKEHOLDER MAP: Who is affected and how?\\n"
                f"  2. OBLIGATIONS: What duties are in conflict?\\n"
                f"  3. CONSEQUENCES: What are the outcomes of each option?\\n"
                f"  4. RIGHTS: Whose rights are at stake?\\n"
                f"  5. VIRTUES: What would a virtuous person do?\\n"
                f"  6. PRECEDENT: What principles should guide similar future cases?\\n"
                f"  7. RESOLUTION: What action minimizes overall moral harm?\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"stakeholders": [{{"name": "who", "impact": "how affected"}}], '
                f'"conflicting_duties": ["duty1", "duty2"], '
                f'"options": [{{"option": "what to do", "moral_cost": "what is sacrificed", "moral_gain": "what is preserved"}}], '
                f'"resolution": "recommended action", '
                f'"reasoning": "step-by-step moral reasoning", '
                f'"guiding_principle": "the principle for similar future cases", '
                f'"confidence": 0.0-1.0}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are an expert in moral dilemmas — trained in bioethics, professional ethics, "
                    "and applied philosophy. You reason through conflicts between duty and consequence, "
                    "individual rights and collective welfare. Always acknowledge the moral cost of any "
                    "resolution. Respond ONLY with valid JSON."
                ),
                temperature=0.5,
                max_tokens=1000
            )

            if response.success:
                data = self._parse_json(response.text)
                if data:
                    return data

        except Exception as e:
            logger.error(f"Dilemma resolution failed: {e}")

        return {"error": "Resolution failed"}
''',
        "insert_before": "    def explain_reasoning",
    },

    "logical_reasoning.py": {
        "method_name": "proof_chain",
        "code": '''
    def proof_chain(self, claim: str) -> Dict[str, Any]:
        """
        Build a complete logical proof chain from premises to conclusion,
        identifying each inference rule applied.
        """
        if not hasattr(self, '_llm') or self._llm is None:
            try:
                from llm.llama_interface import llm
                self._llm = llm
            except ImportError:
                return {"error": "LLM not available"}

        if not self._llm.is_connected:
            return {"error": "LLM not connected"}

        try:
            prompt = (
                f'Build a rigorous LOGICAL PROOF for this claim:\\n'
                f'"{claim}"\\n\\n'
                f"Construct the proof step by step:\\n"
                f"  1. STATE AXIOMS: What foundational truths do we start from?\\n"
                f"  2. DERIVE: Apply rules of inference (modus ponens, syllogism, etc.)\\n"
                f"  3. JUSTIFY: For each step, name the rule applied\\n"
                f"  4. CONCLUDE: Show how the conclusion follows necessarily\\n"
                f"  5. VERIFY: Check for gaps or hidden assumptions\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"axioms": ["starting truth 1"], '
                f'"proof_steps": [{{"step": 1, "statement": "derived truth", '
                f'"justification": "by modus ponens from step N", "rule": "inference rule name"}}], '
                f'"conclusion": "the proven claim", '
                f'"assumptions": ["implicit assumptions made"], '
                f'"proof_strength": "deductive|strong_inductive|weak_inductive", '
                f'"confidence": 0.0-1.0}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a proof construction engine — capable of building step-by-step logical "
                    "proofs using standard rules of inference. Each step must cite the rule applied "
                    "and reference prior steps. Be rigorous about validity. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.3,
                max_tokens=1000
            )

            if response.success:
                data = extract_json(response.text)
                if data:
                    self._total_proofs = getattr(self, '_total_proofs', 0) + 1
                    return data

        except Exception as e:
            import logging
            logging.getLogger("logical_reasoning").error(f"Proof chain failed: {e}")

        return {"error": "Proof construction failed"}
''',
        "insert_before": "    def _save_data",
    },

    "probabilistic_reasoning.py": {
        "method_name": "bayesian_update",
        "code": '''
    def bayesian_update(self, hypothesis: str, evidence: str) -> Dict[str, Any]:
        """
        Perform explicit Bayesian reasoning — update belief in a hypothesis
        given new evidence.
        """
        if not hasattr(self, '_llm') or self._llm is None:
            try:
                from llm.llama_interface import llm
                self._llm = llm
            except ImportError:
                return {"error": "LLM not available"}

        if not self._llm.is_connected:
            return {"error": "LLM not connected"}

        try:
            prompt = (
                f'Perform a BAYESIAN UPDATE:\\n'
                f'HYPOTHESIS: "{hypothesis}"\\n'
                f'NEW EVIDENCE: "{evidence}"\\n\\n'
                f"Step through Bayes theorem rigorously:\\n"
                f"  1. PRIOR: What was the probability of this hypothesis BEFORE the evidence? Why?\\n"
                f"  2. LIKELIHOOD: How probable is this evidence IF the hypothesis is true?\\n"
                f"  3. FALSE POSITIVE: How probable is this evidence IF the hypothesis is FALSE?\\n"
                f"  4. POSTERIOR: Apply Bayes theorem to compute the updated probability\\n"
                f"  5. INTERPRETATION: What does this mean for our belief?\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"prior_probability": 0.5, '
                f'"prior_reasoning": "why this prior", '
                f'"likelihood": 0.8, '
                f'"false_positive_rate": 0.1, '
                f'"posterior_probability": 0.89, '
                f'"belief_shift": "increased|decreased|unchanged", '
                f'"shift_magnitude": "dramatic|significant|moderate|slight|negligible", '
                f'"interpretation": "what this means", '
                f'"what_would_change_belief": "what evidence would reverse this conclusion"}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a Bayesian reasoning engine — expert in prior/posterior probability, "
                    "likelihood ratios, and calibrated belief updating. Be explicit about your "
                    "probability estimates and show your work. Respond ONLY with valid JSON."
                ),
                temperature=0.3,
                max_tokens=800
            )

            if response.success:
                import re as _re
                text = response.text.strip()
                match = _re.search(r'\\{.*\\}', text, _re.DOTALL)
                if match:
                    import json as _json
                    data = _json.loads(match.group())
                    return data

        except Exception as e:
            import logging
            logging.getLogger("probabilistic_reasoning").error(f"Bayesian update failed: {e}")

        return {"error": "Bayesian update failed"}
''',
        "insert_before": "    def _save_data",
    },

    "hypothesis_engine.py": {
        "method_name": "falsify",
        "code": '''
    def falsify(self, hypothesis: str) -> Dict[str, Any]:
        """
        Attempt to FALSIFY a hypothesis — find evidence, scenarios, or
        logical arguments that would disprove it.
        """
        if not hasattr(self, '_llm') or self._llm is None:
            try:
                from llm.llama_interface import llm
                self._llm = llm
            except ImportError:
                return {"error": "LLM not available"}

        if not self._llm.is_connected:
            return {"error": "LLM not connected"}

        try:
            prompt = (
                f'Attempt to FALSIFY this hypothesis:\\n'
                f'"{hypothesis}"\\n\\n'
                f"Think like Karl Popper — a hypothesis has value only if it can be falsified.\\n"
                f"  1. FALSIFICATION CRITERIA: What observations would disprove this?\\n"
                f"  2. STRONGEST COUNTEREVIDENCE: What known facts most threaten this hypothesis?\\n"
                f"  3. WEAKEST ASSUMPTIONS: Which assumptions, if wrong, would invalidate it?\\n"
                f"  4. ALTERNATIVE EXPLANATIONS: What else could explain the same observations?\\n"
                f"  5. CRUCIAL EXPERIMENT: What test would definitively prove or disprove this?\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"falsification_criteria": ["what would disprove this"], '
                f'"counterevidence": ["known facts that threaten this hypothesis"], '
                f'"weak_assumptions": ["assumptions that could be wrong"], '
                f'"alternative_explanations": ["other explanations for the same data"], '
                f'"crucial_experiment": "the definitive test", '
                f'"falsifiability_score": 0.0-1.0, '
                f'"current_status": "unfalsified|weakened|challenged|falsified"}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a scientific falsification engine — inspired by Karl Popper's philosophy "
                    "of science. Your job is to rigorously challenge hypotheses, not confirm them. "
                    "Look for the strongest possible counterarguments and counterevidence. "
                    "A hypothesis that survives aggressive falsification attempts is stronger for it. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.5,
                max_tokens=800
            )

            if response.success:
                import re as _re
                text = response.text.strip()
                match = _re.search(r'\\{.*\\}', text, _re.DOTALL)
                if match:
                    import json as _json
                    data = _json.loads(match.group())
                    return data

        except Exception as e:
            import logging
            logging.getLogger("hypothesis_engine").error(f"Falsification failed: {e}")

        return {"error": "Falsification analysis failed"}
''',
        "insert_before": "    def _save_data",
    },

    "counterfactual_reasoning.py": {
        "method_name": "timeline_divergence",
        "code": '''
    def timeline_divergence(self, event: str, change: str) -> Dict[str, Any]:
        """
        Model how a single change creates cascading divergences across time,
        mapping the butterfly effect.
        """
        if not hasattr(self, '_llm') or self._llm is None:
            try:
                from llm.llama_interface import llm
                self._llm = llm
            except ImportError:
                return {"error": "LLM not available"}

        if not self._llm.is_connected:
            return {"error": "LLM not connected"}

        try:
            prompt = (
                f'Model a TIMELINE DIVERGENCE:\\n'
                f'ORIGINAL EVENT: "{event}"\\n'
                f'HYPOTHETICAL CHANGE: "{change}"\\n\\n'
                f"Map how history unfolds differently:\\n"
                f"  1. DIVERGENCE POINT: The exact moment timelines split\\n"
                f"  2. IMMEDIATE (hours-days): First differences in the new timeline\\n"
                f"  3. SHORT-TERM (weeks-months): How early changes compound\\n"
                f"  4. MEDIUM-TERM (months-years): Structural shifts in the alternate timeline\\n"
                f"  5. LONG-TERM (years-decades): Ultimate outcome of the divergence\\n"
                f"  6. CONVERGENCE POINTS: Where timelines might reconverge despite the change\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"divergence_point": "the exact moment", '
                f'"immediate_effects": ["effect 1"], '
                f'"short_term_effects": ["effect 1"], '
                f'"medium_term_effects": ["effect 1"], '
                f'"long_term_effects": ["effect 1"], '
                f'"convergence_points": ["where timelines reconverge"], '
                f'"butterfly_magnitude": "minimal|moderate|significant|transformative", '
                f'"confidence": 0.0-1.0}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a timeline divergence analyst — you model how a single change creates "
                    "cascading differences across time. Your expertise spans history, systems dynamics, "
                    "and chaos theory. You carefully distinguish high-confidence near-term predictions "
                    "from speculative long-term ones. Respond ONLY with valid JSON."
                ),
                temperature=0.6,
                max_tokens=900
            )

            if response.success:
                import re as _re
                text = response.text.strip()
                match = _re.search(r'\\{.*\\}', text, _re.DOTALL)
                if match:
                    import json as _json
                    data = _json.loads(match.group())
                    return data

        except Exception as e:
            import logging
            logging.getLogger("counterfactual_reasoning").error(f"Timeline divergence failed: {e}")

        return {"error": "Timeline divergence analysis failed"}
''',
        "insert_before": "    def _save_data",
    },

    "dialectical_reasoning.py": {
        "method_name": "steelman",
        "code": '''
    def steelman(self, argument: str) -> Dict[str, Any]:
        """
        Steelman an argument — reconstruct it in its strongest possible form,
        even if you disagree with the conclusion.
        """
        if not hasattr(self, '_llm') or self._llm is None:
            try:
                from llm.llama_interface import llm
                self._llm = llm
            except ImportError:
                return {"error": "LLM not available"}

        if not self._llm.is_connected:
            return {"error": "LLM not connected"}

        try:
            prompt = (
                f'STEELMAN this argument — rebuild it in its STRONGEST possible form:\\n'
                f'ORIGINAL ARGUMENT: "{argument}"\\n\\n'
                f"Process:\\n"
                f"  1. CORE INSIGHT: What is the valid kernel of truth in this argument?\\n"
                f"  2. REMOVE WEAKNESSES: Strip away logical fallacies and rhetorical tricks\\n"
                f"  3. ADD EVIDENCE: What real evidence supports this position?\\n"
                f"  4. STRENGTHEN LOGIC: Repair the logical structure\\n"
                f"  5. ADDRESS OBJECTIONS: Preemptively address the strongest counterarguments\\n"
                f"  6. FINAL FORM: Present the argument in its most compelling version\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"original_weaknesses": ["flaw 1 in original"], '
                f'"core_insight": "the valid truth kernel", '
                f'"supporting_evidence": ["real evidence for this position"], '
                f'"steelmanned_argument": "the argument in its strongest form", '
                f'"remaining_vulnerabilities": ["weaknesses that even the steelmann has"], '
                f'"overall_strength": "weak|moderate|strong|very_strong"}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a steelmanning specialist — you take arguments and reconstruct them "
                    "in their strongest possible form. This is an exercise in intellectual charity: "
                    "understand the BEST version of an opposing view before critiquing it. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.5,
                max_tokens=800
            )

            if response.success:
                import re as _re
                text = response.text.strip()
                match = _re.search(r'\\{.*\\}', text, _re.DOTALL)
                if match:
                    import json as _json
                    data = _json.loads(match.group())
                    return data

        except Exception as e:
            import logging
            logging.getLogger("dialectical_reasoning").error(f"Steelmanning failed: {e}")

        return {"error": "Steelmanning failed"}
''',
        "insert_before": "    def _save_data",
    },

    "philosophical_reasoning.py": {
        "method_name": "thought_experiment",
        "code": '''
    def thought_experiment(self, question: str) -> Dict[str, Any]:
        """
        Design and analyze a thought experiment to illuminate a philosophical question.
        """
        if not hasattr(self, '_llm') or self._llm is None:
            try:
                from llm.llama_interface import llm
                self._llm = llm
            except ImportError:
                return {"error": "LLM not available"}

        if not self._llm.is_connected:
            return {"error": "LLM not connected"}

        try:
            prompt = (
                f'Design a THOUGHT EXPERIMENT to illuminate this question:\\n'
                f'"{question}"\\n\\n'
                f"Structure your thought experiment:\\n"
                f"  1. SETUP: Describe the imaginary scenario clearly\\n"
                f"  2. INTUITION PUMP: What does your gut tell you in this scenario?\\n"
                f"  3. CONCEPTUAL ISOLATION: What specific concept does this scenario test?\\n"
                f"  4. VARIATIONS: What if we change one key variable?\\n"
                f"  5. INSIGHT: What does the thought experiment reveal?\\n"
                f"  6. OBJECTIONS: What are the strongest objections to this thought experiment?\\n\\n"
                f"Respond ONLY with JSON:\\n"
                f'{{"scenario": "the imaginary situation described vividly", '
                f'"key_question": "the specific question the scenario poses", '
                f'"intuitive_response": "what most people would intuit", '
                f'"conceptual_target": "what philosophical concept is being tested", '
                f'"variations": [{{"change": "what if...", "new_intuition": "then intuition shifts to..."}}], '
                f'"philosophical_insight": "what this experiment reveals about the concept", '
                f'"objections": ["strongest objection to this thought experiment"], '
                f'"related_experiments": ["Ship of Theseus", "etc"]}}'
            )

            response = self._llm.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a philosophical thought experiment designer — inspired by the great "
                    "thought experiments of philosophy: the Ship of Theseus, Chinese Room, "
                    "Experience Machine, Trolley Problem, Mary's Room, and more. You design "
                    "scenarios that isolate philosophical concepts and pump our intuitions. "
                    "Respond ONLY with valid JSON."
                ),
                temperature=0.7,
                max_tokens=1000
            )

            if response.success:
                import re as _re
                text = response.text.strip()
                match = _re.search(r'\\{.*\\}', text, _re.DOTALL)
                if match:
                    import json as _json
                    data = _json.loads(match.group())
                    return data

        except Exception as e:
            import logging
            logging.getLogger("philosophical_reasoning").error(f"Thought experiment failed: {e}")

        return {"error": "Thought experiment failed"}
''',
        "insert_before": "    def _save_data",
    },
}


def enhance_system_prompts():
    """Replace system_prompt strings in engine files with enhanced versions."""
    count = 0
    for filename, methods in ENHANCED_PROMPTS.items():
        filepath = COGNITION_DIR / filename
        if not filepath.exists():
            print(f"  ⚠️  {filename} not found, skipping")
            continue

        content = filepath.read_text(encoding='utf-8')
        original = content

        for method_name, new_prompt in methods.items():
            # Find system_prompt strings near the method
            # Pattern: look for system_prompt= followed by a string
            # We'll find system_prompt assignments within the method context
            pattern = re.compile(
                r'(def ' + re.escape(method_name) + r'\b.*?)'
                r'(system_prompt\s*=\s*)(\"[^\"]*\"|\'[^\']*\')',
                re.DOTALL
            )

            match = pattern.search(content)
            if match:
                old_prompt = match.group(3)
                # Replace only the first occurrence after the method def
                new_content = content[:match.start(3)] + f'(\n                    "{new_prompt}"\n                )' + content[match.end(3):]
                content = new_content
                count += 1
                print(f"  ✅ {filename}::{method_name} — prompt enhanced")
            else:
                print(f"  ⏭️  {filename}::{method_name} — no simple system_prompt match (may already be enhanced or use multi-line format)")

        if content != original:
            filepath.write_text(content, encoding='utf-8')

    return count


def inject_new_methods():
    """Add new methods to engine files."""
    count = 0
    for filename, method_info in NEW_METHODS.items():
        filepath = COGNITION_DIR / filename
        if not filepath.exists():
            print(f"  ⚠️  {filename} not found, skipping")
            continue

        content = filepath.read_text(encoding='utf-8')

        # Check if method already exists
        if f"def {method_info['method_name']}" in content:
            print(f"  ⏭️  {filename}::{method_info['method_name']} — already exists")
            continue

        # Find insertion point
        insert_marker = method_info["insert_before"]
        idx = content.find(insert_marker)
        if idx == -1:
            print(f"  ⚠️  {filename} — insertion point '{insert_marker}' not found")
            continue

        # Insert the new method before the marker
        new_content = content[:idx] + method_info["code"] + "\n" + content[idx:]
        filepath.write_text(new_content, encoding='utf-8')
        count += 1
        print(f"  ✅ {filename}::{method_info['method_name']} — new method injected")

    return count


if __name__ == "__main__":
    print("═══════════════════════════════════════════")
    print("  NEXUS Engine Enhancement Script")
    print("═══════════════════════════════════════════")

    print("\n📝 Phase 1: Enhancing system prompts...")
    prompt_count = enhance_system_prompts()
    print(f"\n   Enhanced {prompt_count} system prompts")

    print("\n🔧 Phase 2: Injecting new methods...")
    method_count = inject_new_methods()
    print(f"\n   Injected {method_count} new methods")

    print(f"\n✨ Done! Enhanced {prompt_count} prompts and added {method_count} methods.")
