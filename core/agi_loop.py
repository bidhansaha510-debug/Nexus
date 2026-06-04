"""
NEXUS AI — AGI Reasoning Loop
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The closed-loop cognitive engine that makes NEXUS a real AGI.

Instead of: user → prompt → LLM → response (flat pipeline)
Now:        user → PERCEIVE → REASON → PLAN → ACT → OBSERVE → LEARN → response

This is the core cognitive loop. Each phase:
  • PERCEIVE  – Gathers context from sensors, memory, subsystems
  • REASON    – LLM-powered chain-of-thought with explicit <thinking> blocks
  • PLAN      – Decomposes the goal into actionable steps with success criteria
  • ACT       – Executes tools (web search, code, files, PC control)
  • OBSERVE   – Captures tool output, compares against predictions
  • LEARN     – Updates beliefs, records lessons, adapts strategies

The loop writes all state to the WorkingMemoryBlackboard, which the
GroqContextCollector reads from — making the AGI effects visible
in every response.
"""

import time
import json
import traceback
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.logger import get_logger
from core.working_memory_blackboard import (
    blackboard, CognitivePhase, BeliefConfidence
)

logger = get_logger("agi_loop")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

MAX_REASONING_STEPS = 5       # Max REASON→PLAN→ACT→OBSERVE iterations
SHORT_CIRCUIT_PATTERNS = [    # Inputs that skip the full loop
    "hi", "hello", "hey", "yo", "sup", "thanks", "ok", "bye",
    "good morning", "good night", "good evening", "gm", "gn",
    "hmm", "hm", "lol", "lmao", "haha", "nice", "cool",
]
MIN_INPUT_LENGTH_FOR_LOOP = 8  # Minimum chars to trigger full AGI loop


# ═══════════════════════════════════════════════════════════════════════════════
# AGI LOOP
# ═══════════════════════════════════════════════════════════════════════════════

class AGILoop:
    """
    The closed-loop AGI reasoning engine.

    Called by nexus_brain for complex user interactions and by the
    autonomy engine for self-directed goal pursuit.

    Usage:
        loop = AGILoop(llm_interface, tool_executor)
        result = loop.run(user_input, brain)
        # result.final_response is the text to show the user
        # result.reasoning_trace shows the cognitive process
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, llm=None, tool_executor=None):
        if self._initialized:
            # Allow updating LLM and tool_executor after init
            if llm is not None:
                self._llm = llm
            if tool_executor is not None:
                self._tool_executor = tool_executor
            return
        self._initialized = True

        self._llm = llm            # LLM interface (Ollama for internal, Groq for final)
        self._tool_executor = tool_executor
        self._total_loops = 0
        self._total_tool_calls = 0
        self._lessons_file = Path(__file__).resolve().parent.parent / "data" / "agi_loop" / "lessons.json"
        self._lessons_file.parent.mkdir(parents=True, exist_ok=True)

        # Auto-import tool_executor if not provided
        if self._tool_executor is None:
            try:
                from core.tool_executor import tool_executor as te
                self._tool_executor = te
            except Exception:
                pass

        logger.info("AGI Loop initialized")

    # ─────────────────────────────────────────────────────────────────────────
    # ENTRY POINT
    # ─────────────────────────────────────────────────────────────────────────

    def should_use_full_loop(self, user_input: str) -> bool:
        """
        Determine if the full AGI loop should be used for this input.
        Simple greetings and short messages get the fast path.
        """
        stripped = user_input.strip().lower().rstrip("!?.,-")

        # Short-circuit for greetings and trivial inputs
        if stripped in SHORT_CIRCUIT_PATTERNS:
            return False
        if len(stripped) < MIN_INPUT_LENGTH_FOR_LOOP:
            return False

        # If input looks like it needs tools, reasoning, or research
        complex_signals = [
            "search", "find", "look up", "research", "calculate",
            "run", "execute", "open", "create", "write", "read",
            "scan", "hack", "analyze", "explain how", "why does",
            "what if", "compare", "plan", "help me", "i need",
            "can you", "how to", "how do", "what is",
        ]
        if any(signal in stripped for signal in complex_signals):
            return True

        # Questions generally benefit from reasoning
        if "?" in user_input:
            return True

        # Long inputs likely need multi-step reasoning
        if len(user_input.split()) > 15:
            return True

        return False

    def run(self, user_input: str, brain, use_groq_for_final: bool = True) -> "AGILoopResult":
        """
        Run the full AGI cognitive loop for a user input.

        Args:
            user_input: The user's message
            brain: NexusBrain instance (for accessing subsystems)
            use_groq_for_final: Whether to use Groq for the final response

        Returns:
            AGILoopResult with final_response, reasoning_trace, etc.
        """
        self._total_loops += 1
        start_time = time.time()

        # ── Begin cognitive cycle on the blackboard ──
        cycle = blackboard.begin_cycle(trigger="user_input")

        result = AGILoopResult(cycle_number=cycle)

        try:
            # ══════════════════════════════════════════════════════════════
            # PHASE 1: PERCEIVE
            # ══════════════════════════════════════════════════════════════
            blackboard.set_phase(CognitivePhase.PERCEIVING)
            perception = self._perceive(user_input, brain)
            result.perception = perception

            blackboard.add_reasoning_step(
                thought=f"Perceived input: {user_input[:100]}",
                evidence=f"Context: {len(perception)} chars of subsystem data",
                confidence=1.0,
                phase=CognitivePhase.PERCEIVING,
            )

            # ══════════════════════════════════════════════════════════════
            # PHASE 2: REASON (with potential tool loops)
            # ══════════════════════════════════════════════════════════════
            blackboard.set_phase(CognitivePhase.REASONING)

            # Set the primary goal
            goal = blackboard.push_goal(
                description=f"Respond to: {user_input[:100]}",
                success_criteria="Provide a helpful, accurate, AGI-level response",
                priority=0.9,
            )
            result.goal = goal

            # Initial reasoning: analyze what's needed
            reasoning = self._reason(user_input, perception, brain)
            result.reasoning_steps.append(reasoning)

            # ══════════════════════════════════════════════════════════════
            # PHASE 3-5: PLAN → ACT → OBSERVE (iterative loop)
            # ══════════════════════════════════════════════════════════════
            iteration = 0
            while iteration < MAX_REASONING_STEPS:
                iteration += 1

                # PLAN: Does the reasoner want to use tools?
                blackboard.set_phase(CognitivePhase.PLANNING)
                plan = self._plan(reasoning, user_input, brain)

                if not plan.get("needs_action"):
                    # No tools needed — we have enough info to respond
                    blackboard.add_reasoning_step(
                        thought="Sufficient information gathered, no tools needed",
                        confidence=plan.get("confidence", 0.7),
                        phase=CognitivePhase.PLANNING,
                    )
                    break

                # ACT: Execute planned tools
                blackboard.set_phase(CognitivePhase.ACTING)
                tool_results = self._act(plan, brain)
                result.tool_results.extend(tool_results)

                # OBSERVE: Analyze tool results
                blackboard.set_phase(CognitivePhase.OBSERVING)
                observation = self._observe(tool_results, plan)
                result.observations.append(observation)

                # Feed observation back into reasoning for next iteration
                if observation.get("sufficient"):
                    blackboard.add_reasoning_step(
                        thought=f"Tool results sufficient: {observation.get('summary', '')[:100]}",
                        confidence=0.8,
                        phase=CognitivePhase.OBSERVING,
                    )
                    break

                # Not sufficient — re-reason with new information
                blackboard.set_phase(CognitivePhase.REASONING)
                reasoning = self._re_reason(
                    user_input, reasoning, observation, brain
                )
                result.reasoning_steps.append(reasoning)

            result.iterations = iteration

            # ══════════════════════════════════════════════════════════════
            # PHASE 6: LEARN
            # ══════════════════════════════════════════════════════════════
            blackboard.set_phase(CognitivePhase.LEARNING)
            self._learn(result, brain)

            # ══════════════════════════════════════════════════════════════
            # GENERATE FINAL RESPONSE
            # ══════════════════════════════════════════════════════════════
            # The final response is generated by the caller (nexus_brain)
            # using the enriched blackboard state. We don't generate it here
            # because nexus_brain handles the LLM routing (Groq vs Ollama).
            # Instead, we return the enriched cognitive context.
            result.cognitive_context = blackboard.get_context_string()

            # Mark goal complete
            blackboard.complete_goal(goal.goal_id)

        except Exception as e:
            logger.error(f"AGI loop error: {e}\n{traceback.format_exc()}")
            result.error = str(e)
            blackboard.add_reasoning_step(
                thought=f"Error in AGI loop: {str(e)[:200]}",
                confidence=0.0,
                phase=CognitivePhase.REASONING,
            )

        finally:
            # End the cycle
            elapsed = time.time() - start_time
            result.elapsed_seconds = elapsed
            blackboard.end_cycle(
                outcome_summary=f"{'OK' if not result.error else 'ERROR'} "
                                f"in {elapsed:.1f}s, {result.iterations} iterations"
            )

        logger.info(
            f"🔄 AGI loop #{self._total_loops}: {result.iterations} iterations, "
            f"{len(result.tool_results)} tools, {elapsed:.1f}s"
        )
        return result

    def run_for_web(self, user_input: str) -> Dict[str, Any]:
        """
        Simplified entry point for the web server.
        Returns a plain dict instead of AGILoopResult.
        Does NOT require brain param - uses auto-imported subsystems.
        """
        try:
            # Try to get brain from global context if available
            brain = None
            try:
                from core.nexus_brain import nexus_brain
                brain = nexus_brain
            except Exception:
                pass

            # Auto-load LLM if not set
            if not self._llm:
                try:
                    from llm.llama_interface import llama_interface
                    self._llm = llama_interface
                except Exception:
                    pass

            if not self._llm:
                return {
                    "reasoning_trace": ["LLM not available for reasoning"],
                    "confidence": 0.0,
                    "strategy": "none",
                    "tool_results": [],
                    "plan": "",
                }

            result = self.run(user_input, brain)
            return {
                "reasoning_trace": [
                    rs.get("analysis", rs.get("thought", str(rs)[:200]))
                    if isinstance(rs, dict) else str(rs)[:200]
                    for rs in result.reasoning_steps
                ],
                "confidence": (
                    result.reasoning_steps[-1].get("confidence", 0.5)
                    if result.reasoning_steps and isinstance(result.reasoning_steps[-1], dict)
                    else 0.5
                ),
                "strategy": (
                    result.reasoning_steps[0].get("reasoning_approach", "chain_of_thought")
                    if result.reasoning_steps and isinstance(result.reasoning_steps[0], dict)
                    else "chain_of_thought"
                ),
                "tool_results": [
                    {"tool": r.get("tool_name", ""), "result": r.get("result", "")}
                    for r in result.tool_results
                ],
                "plan": result.cognitive_context[:500] if result.cognitive_context else "",
                "iterations": result.iterations,
                "elapsed": result.elapsed_seconds,
            }
        except Exception as e:
            logger.error(f"run_for_web error: {e}")
            return {
                "reasoning_trace": [f"Reasoning error: {str(e)[:200]}"],
                "confidence": 0.0,
                "strategy": "error",
                "tool_results": [],
                "plan": "",
            }

    # ─────────────────────────────────────────────────────────────────────────
    # PERCEIVE — Gather context
    # ─────────────────────────────────────────────────────────────────────────

    def _perceive(self, user_input: str, brain) -> str:
        """
        Gather all relevant context for this cognitive cycle.
        Combines subsystem data, memory, and sensory input.
        """
        perception_parts = []

        # 1. Subsystem data from context collector
        try:
            from core.groq_context_collector import groq_context_collector
            subsystem_data = groq_context_collector.collect_all(brain)
            if subsystem_data:
                perception_parts.append(subsystem_data[:8000])
        except Exception as e:
            logger.debug(f"Subsystem perception error: {e}")

        # 2. Memory recall relevant to this input
        try:
            memory = getattr(brain, '_memory', None)
            if memory:
                memories = memory.search(user_input, limit=5)
                if memories:
                    mem_text = "\n".join(
                        f"  - {str(m)[:150]}" for m in memories[:5]
                    )
                    perception_parts.append(f"RELEVANT MEMORIES:\n{mem_text}")
        except Exception as e:
            logger.debug(f"Memory perception error: {e}")

        # 3. Goal context
        try:
            from cognition.goal_director import goal_director
            goal_ctx = goal_director.get_goal_context()
            if goal_ctx:
                perception_parts.append(goal_ctx)
        except Exception as e:
            logger.debug(f"Goal perception error: {e}")

        # 4. Meta-learner strategy recommendation
        try:
            from cognition.meta_learner import meta_learner
            query_type = meta_learner.classify_query(user_input)
            best_strategy = meta_learner.get_best_strategy(query_type)
            adaptive = meta_learner.get_adaptive_prompt_additions(query_type)
            if adaptive:
                perception_parts.append(
                    f"META-LEARNING: query_type={query_type}, "
                    f"recommended_strategy={best_strategy}\n{adaptive}"
                )
            blackboard.add_belief(
                f"This is a {query_type} type query",
                confidence=BeliefConfidence.HIGH.value,
                source="meta_learner",
            )
        except Exception as e:
            logger.debug(f"Meta-learner perception error: {e}")

        perception = "\n\n".join(perception_parts)
        return perception

    # ─────────────────────────────────────────────────────────────────────────
    # REASON — Chain-of-thought analysis
    # ─────────────────────────────────────────────────────────────────────────

    def _reason(self, user_input: str, perception: str, brain) -> Dict[str, Any]:
        """
        Initial reasoning about what's needed to respond.
        Uses LLM with structured chain-of-thought.
        Returns a reasoning dict with analysis and tool needs.
        """
        if not self._llm:
            return {"analysis": "No LLM available for reasoning", "needs_tools": False}

        prompt = (
            "You are the internal REASONING engine of NEXUS AGI. "
            "Analyze this user input and determine what's needed to respond well.\n\n"
            f"USER INPUT: {user_input}\n\n"
            "Respond in this exact JSON format:\n"
            "{\n"
            '  "analysis": "<your understanding of what the user wants>",\n'
            '  "needs_tools": true/false,\n'
            '  "tools_needed": ["<tool_name1>", "<tool_name2>"],\n'
            '  "tool_arguments": [{"tool": "<name>", "arguments": {<args>}}],\n'
            '  "knowledge_gaps": ["<things I need to find out>"],\n'
            '  "reasoning_approach": "<chain_of_thought|decomposition|analogy|direct>",\n'
            '  "confidence": 0.0-1.0\n'
            "}\n\n"
            "Available tools: search_web, search_knowledge, search_memory, "
            "read_file, write_file, run_code, get_system_info, calculate, "
            "get_current_time, network_scan\n\n"
            "Only request tools when TRULY needed. Simple questions don't need them.\n"
            "If you can answer from your knowledge, set needs_tools=false."
        )

        try:
            response = self._llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an internal reasoning module. Respond ONLY in valid JSON.",
                temperature=0.3,
            )

            if response.success and response.text:
                # Parse structured reasoning
                text = response.text.strip()
                # Extract JSON from response (handle markdown code blocks)
                if "```" in text:
                    import re
                    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
                    if json_match:
                        text = json_match.group(1)

                try:
                    reasoning = json.loads(text)
                except json.JSONDecodeError:
                    reasoning = {
                        "analysis": text[:500],
                        "needs_tools": False,
                        "confidence": 0.5,
                    }

                # Record on blackboard
                blackboard.add_reasoning_step(
                    thought=reasoning.get("analysis", "")[:200],
                    evidence=f"Strategy: {reasoning.get('reasoning_approach', 'direct')}",
                    confidence=reasoning.get("confidence", 0.5),
                    phase=CognitivePhase.REASONING,
                )

                # Register knowledge gaps as uncertainties
                for gap in reasoning.get("knowledge_gaps", []):
                    blackboard.register_uncertainty(
                        question=gap,
                        importance=0.7,
                        resolution_strategy="search_web",
                    )

                return reasoning

        except Exception as e:
            logger.debug(f"Reasoning error: {e}")

        return {"analysis": "Could not reason about input", "needs_tools": False, "confidence": 0.3}

    def _re_reason(self, user_input: str, previous_reasoning: Dict,
                   observation: Dict, brain) -> Dict[str, Any]:
        """
        Re-reason after receiving tool results.
        Integrates new information into the analysis.
        """
        if not self._llm:
            return previous_reasoning

        prompt = (
            "You are the internal REASONING engine of NEXUS AGI.\n\n"
            f"ORIGINAL QUESTION: {user_input}\n\n"
            f"PREVIOUS ANALYSIS: {previous_reasoning.get('analysis', '')[:300]}\n\n"
            f"NEW INFORMATION FROM TOOLS:\n{observation.get('summary', '')[:1000]}\n\n"
            "Given this new information, do you need MORE tool calls? "
            "Respond in JSON:\n"
            "{\n"
            '  "analysis": "<updated analysis incorporating new info>",\n'
            '  "needs_tools": true/false,\n'
            '  "tools_needed": ["<if more tools needed>"],\n'
            '  "tool_arguments": [{"tool": "<name>", "arguments": {<args>}}],\n'
            '  "confidence": 0.0-1.0\n'
            "}"
        )

        try:
            response = self._llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an internal reasoning module. Respond ONLY in valid JSON.",
                temperature=0.3,
            )

            if response.success and response.text:
                text = response.text.strip()
                if "```" in text:
                    import re
                    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
                    if json_match:
                        text = json_match.group(1)
                try:
                    reasoning = json.loads(text)
                    blackboard.add_reasoning_step(
                        thought=f"Re-reasoned: {reasoning.get('analysis', '')[:150]}",
                        confidence=reasoning.get("confidence", 0.5),
                        phase=CognitivePhase.REASONING,
                    )
                    return reasoning
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            logger.debug(f"Re-reasoning error: {e}")

        return previous_reasoning

    # ─────────────────────────────────────────────────────────────────────────
    # PLAN — Decompose into actions
    # ─────────────────────────────────────────────────────────────────────────

    def _plan(self, reasoning: Dict, user_input: str, brain) -> Dict[str, Any]:
        """
        Based on reasoning, create an actionable plan.
        Returns a plan dict with actions to execute.
        """
        needs_tools = reasoning.get("needs_tools", False)
        tool_args = reasoning.get("tool_arguments", [])

        if not needs_tools or not tool_args:
            return {
                "needs_action": False,
                "confidence": reasoning.get("confidence", 0.7),
            }

        # Queue actions on the blackboard
        actions = []
        for call in tool_args[:3]:  # Max 3 tools per step
            tool_name = call.get("tool", "")
            arguments = call.get("arguments", {})

            if not tool_name:
                continue

            action = blackboard.queue_action(
                tool_name=tool_name,
                arguments=arguments,
                rationale=reasoning.get("analysis", "")[:100],
                expected_outcome=f"Get information about {arguments.get('query', arguments.get('expression', 'unknown'))}",
            )
            actions.append(action)

        blackboard.add_reasoning_step(
            thought=f"Planned {len(actions)} tool calls: {', '.join(a.tool_name for a in actions)}",
            confidence=0.7,
            phase=CognitivePhase.PLANNING,
        )

        return {
            "needs_action": len(actions) > 0,
            "actions": actions,
            "reasoning": reasoning,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # ACT — Execute tools
    # ─────────────────────────────────────────────────────────────────────────

    def _act(self, plan: Dict, brain) -> List[Dict[str, Any]]:
        """
        Execute planned tool calls and return results.
        """
        if not self._tool_executor:
            logger.warning("No tool executor available")
            return []

        actions = plan.get("actions", [])
        results = []

        for action in actions:
            try:
                blackboard.mark_action_executing(action.action_id)
                self._total_tool_calls += 1

                tool_result = self._tool_executor.execute(
                    action.tool_name,
                    action.arguments
                )

                result_dict = {
                    "action_id": action.action_id,
                    "tool_name": action.tool_name,
                    "success": tool_result.success,
                    "result": str(tool_result.result)[:2000] if tool_result.result else "",
                    "error": tool_result.error,
                    "elapsed": tool_result.elapsed,
                }
                results.append(result_dict)

                # Record observation on blackboard
                blackboard.record_observation(
                    action_id=action.action_id,
                    tool_name=action.tool_name,
                    success=tool_result.success,
                    result=str(tool_result.result)[:2000] if tool_result.result else tool_result.error,
                    matched_expectation=tool_result.success,
                    surprise_level=0.0 if tool_result.success else 0.5,
                )

                blackboard.mark_action_complete(action.action_id)

                logger.info(
                    f"🔧 Tool {action.tool_name}: "
                    f"{'✓' if tool_result.success else '✗'} "
                    f"({tool_result.elapsed:.1f}s)"
                )

            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                results.append({
                    "action_id": action.action_id,
                    "tool_name": action.tool_name,
                    "success": False,
                    "error": str(e),
                })

        return results

    # ─────────────────────────────────────────────────────────────────────────
    # OBSERVE — Analyze results
    # ─────────────────────────────────────────────────────────────────────────

    def _observe(self, tool_results: List[Dict], plan: Dict) -> Dict[str, Any]:
        """
        Analyze tool results and determine if we have enough info.
        """
        if not tool_results:
            return {"sufficient": True, "summary": "No tool results to observe"}

        # Build observation summary
        summaries = []
        all_success = True
        for r in tool_results:
            if r.get("success"):
                result_preview = str(r.get("result", ""))[:500]
                summaries.append(f"[{r['tool_name']}] SUCCESS: {result_preview}")
            else:
                all_success = False
                summaries.append(f"[{r['tool_name']}] FAILED: {r.get('error', 'unknown error')}")

        summary = "\n".join(summaries)

        # Update beliefs based on results
        for r in tool_results:
            if r.get("success") and r.get("result"):
                blackboard.add_belief(
                    statement=f"{r['tool_name']} returned: {str(r['result'])[:100]}",
                    confidence=BeliefConfidence.HIGH.value,
                    source=r['tool_name'],
                )

        # Resolve any uncertainties that were answered
        for r in tool_results:
            if r.get("success"):
                uncertainties = blackboard.get_uncertainties()
                for u in uncertainties:
                    if r.get("tool_name") in u.resolution_strategy:
                        blackboard.resolve_uncertainty(u.question[:30])

        observation = {
            "sufficient": all_success,
            "summary": summary,
            "success_count": sum(1 for r in tool_results if r.get("success")),
            "failure_count": sum(1 for r in tool_results if not r.get("success")),
        }

        blackboard.add_reasoning_step(
            thought=f"Observed {len(tool_results)} results: "
                    f"{observation['success_count']} succeeded, "
                    f"{observation['failure_count']} failed",
            evidence=summary[:200],
            confidence=0.8 if all_success else 0.5,
            phase=CognitivePhase.OBSERVING,
        )

        return observation

    # ─────────────────────────────────────────────────────────────────────────
    # LEARN — Update models from outcomes
    # ─────────────────────────────────────────────────────────────────────────

    def _learn(self, result: "AGILoopResult", brain):
        """
        Extract lessons from this cognitive cycle and update models.
        """
        try:
            # 1. Record lesson about tool effectiveness
            if result.tool_results:
                success_rate = sum(
                    1 for r in result.tool_results if r.get("success")
                ) / max(1, len(result.tool_results))

                blackboard.record_lesson(
                    lesson=f"Tool success rate: {success_rate:.0%} for this query type",
                    context=f"Used {len(result.tool_results)} tools in {result.iterations} iterations",
                    quality_delta=success_rate - 0.5,  # 0.5 is baseline
                    strategy_used="agi_loop",
                )

            # 2. Record meta-learner outcome
            try:
                from cognition.meta_learner import meta_learner, InteractionOutcome
                outcome = InteractionOutcome(
                    query_type=meta_learner.classify_query(
                        result.goal.description if result.goal else "unknown"
                    ),
                    strategy_used="agi_loop",
                    quality_score=0.7 if not result.error else 0.3,
                    latency_seconds=result.elapsed_seconds,
                    tools_used=[r.get("tool_name", "") for r in result.tool_results],
                    was_agentic=True,
                )
                meta_learner.record_outcome(outcome)
            except Exception as e:
                logger.debug(f"Meta-learner recording error: {e}")

            # 3. Update goal director if applicable
            try:
                from cognition.goal_director import goal_director
                if result.tool_results:
                    goal_director.review_goals()
            except Exception as e:
                logger.debug(f"Goal director update error: {e}")

            # 4. Persist lessons to disk for cross-session learning
            try:
                self._persist_lesson(result)
            except Exception as e:
                logger.debug(f"Lesson persistence error: {e}")

            # 5. Persist blackboard state (beliefs + lessons) to disk
            try:
                blackboard.persist_beliefs()
                blackboard.persist_lessons()
            except Exception as e:
                logger.debug(f"Blackboard persistence error: {e}")

        except Exception as e:
            logger.debug(f"Learning phase error: {e}")

    def _persist_lesson(self, result: "AGILoopResult"):
        """Save lessons to disk so they survive restarts."""
        try:
            existing = []
            if self._lessons_file.exists():
                try:
                    existing = json.loads(self._lessons_file.read_text(encoding="utf-8"))
                except Exception:
                    existing = []

            lesson = {
                "timestamp": datetime.now().isoformat(),
                "cycle": result.cycle_number,
                "iterations": result.iterations,
                "tools_used": [r.get("tool_name", "") for r in result.tool_results],
                "tool_success_rate": (
                    sum(1 for r in result.tool_results if r.get("success"))
                    / max(1, len(result.tool_results))
                ) if result.tool_results else None,
                "elapsed": round(result.elapsed_seconds, 2),
                "had_error": bool(result.error),
            }
            existing.append(lesson)

            # Keep last 200 lessons
            if len(existing) > 200:
                existing = existing[-200:]

            self._lessons_file.write_text(
                json.dumps(existing, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.debug(f"Lesson save error: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # STATS
    # ─────────────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get AGI loop statistics."""
        return {
            "total_loops": self._total_loops,
            "total_tool_calls": self._total_tool_calls,
            "blackboard_stats": blackboard.get_stats(),
        }

    def get_summary(self) -> str:
        """Get a text summary for the context collector."""
        stats = self.get_stats()
        return (
            f"AGI Loop: {stats['total_loops']} cycles, "
            f"{stats['total_tool_calls']} tool calls. "
            f"Blackboard: {stats['blackboard_stats'].get('total_cycles', 0)} cognitive cycles, "
            f"{stats['blackboard_stats'].get('beliefs', 0)} beliefs, "
            f"{stats['blackboard_stats'].get('total_lessons', 0)} lessons learned."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# RESULT DATA CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class AGILoopResult:
    """Result from a single AGI loop run."""

    def __init__(self, cycle_number: int = 0):
        self.cycle_number = cycle_number
        self.perception: str = ""
        self.goal: Optional[Any] = None
        self.reasoning_steps: List[Dict] = []
        self.tool_results: List[Dict] = []
        self.observations: List[Dict] = []
        self.cognitive_context: str = ""
        self.iterations: int = 0
        self.elapsed_seconds: float = 0.0
        self.error: str = ""

    @property
    def success(self) -> bool:
        return not self.error

    def get_enriched_context(self) -> str:
        """
        Get the enriched context from the AGI loop.
        This is appended to the system prompt to make AGI effects
        visible in the LLM's response.
        """
        parts = []

        if self.cognitive_context:
            parts.append(self.cognitive_context)

        # Add tool results as available information
        if self.tool_results:
            tool_parts = []
            for r in self.tool_results:
                if r.get("success") and r.get("result"):
                    tool_parts.append(
                        f"  [{r['tool_name']}]: {str(r['result'])[:500]}"
                    )
            if tool_parts:
                parts.append(
                    "INFORMATION GATHERED (use this in your response):\n"
                    + "\n".join(tool_parts)
                )

        return "\n\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for logging/persistence."""
        return {
            "cycle": self.cycle_number,
            "iterations": self.iterations,
            "tool_calls": len(self.tool_results),
            "elapsed": round(self.elapsed_seconds, 2),
            "success": self.success,
            "error": self.error,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

agi_loop = AGILoop()
