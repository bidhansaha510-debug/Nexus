"""
NEXUS AI — Agentic Reasoning Loop
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The core AGI upgrade: iterative think → act → observe → reflect cycle.

Instead of a single LLM call, NEXUS reasons over multiple steps:
  1. THINK  — analyze the problem, decide what to do next
  2. ACT    — execute the chosen action (tool call, knowledge retrieval, etc.)
  3. OBSERVE — process the result
  4. REFLECT — decide if the answer is ready or more steps needed

Actions the loop can take:
  • "respond"       — deliver a final answer to the user
  • "tool_call"     — invoke a tool via ToolExecutor
  • "think_deeper"  — use cognition engines for deeper analysis
  • "search"        — search knowledge/memory/web for information
"""
import sys, time, json, re, uuid, threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Generator
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logger import get_logger
from config import NEXUS_CONFIG

logger = get_logger("reasoning_loop")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ReasoningStep:
    """One step in the reasoning loop."""
    step_num: int
    thought: str           # LLM's internal reasoning
    action: str            # respond | tool_call | think_deeper | search
    action_input: Dict[str, Any] = field(default_factory=dict)
    observation: str = ""  # Result of the action
    elapsed: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step_num,
            "thought": self.thought[:300],
            "action": self.action,
            "action_input": self.action_input,
            "observation": self.observation[:500],
            "elapsed": round(self.elapsed, 3),
        }


@dataclass
class AgenticResult:
    """Final result from the reasoning loop."""
    response: str = ""
    steps: List[ReasoningStep] = field(default_factory=list)
    total_steps: int = 0
    total_elapsed: float = 0.0
    used_tools: List[str] = field(default_factory=list)
    final_step: str = ""   # "respond", "max_steps", "error"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_steps": self.total_steps,
            "total_elapsed": round(self.total_elapsed, 3),
            "used_tools": self.used_tools,
            "final_step": self.final_step,
            "steps": [s.to_dict() for s in self.steps],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# AGENTIC REASONING LOOP
# ═══════════════════════════════════════════════════════════════════════════════

# Prompt template for the reasoning step
REASONING_PROMPT = """You are NEXUS, an AGI with access to tools and cognitive engines.

You are solving the user's request through iterative reasoning. At each step, you must decide:
1. What to think about
2. What action to take

USER REQUEST: {query}

{context_section}

{tool_section}

{history_section}

Respond with a JSON object containing your reasoning:
{{
    "thought": "Your internal reasoning about what to do next",
    "action": "respond | tool_call | think_deeper | search",
    "action_input": {{}}
}}

ACTIONS:
- "respond": You have enough information. Put your final answer in action_input: {{"answer": "your response"}}
- "tool_call": Call a tool. action_input: {{"tool": "tool_name", "arguments": {{...}}}}
- "think_deeper": Use cognitive engines. action_input: {{"topic": "what to analyze"}}
- "search": Search for information. action_input: {{"query": "search query", "source": "knowledge|memory|web"}}

RULES:
- Think step by step. Don't rush to respond if you need more information.
- Use tools when you need to DO something (read files, run code, search, etc.)
- Use "think_deeper" for complex reasoning, ethical dilemmas, creative tasks.
- Use "respond" only when you have a complete, high-quality answer.
- Respond ONLY with the JSON object, nothing else."""


class AgenticLoop:
    """
    Multi-step reasoning loop for AGI-level problem solving.

    Iterates through think → act → observe → reflect cycles until
    the LLM decides it has a satisfactory answer, or max_steps is reached.
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
        self._max_steps = NEXUS_CONFIG.agentic.max_reasoning_steps
        self._llm = None
        self._tool_executor = None
        self._context_assembler = None
        self._stats = {
            "total_runs": 0, "total_steps": 0,
            "avg_steps_per_run": 0.0, "tool_calls": 0,
        }
        logger.info(f"AgenticLoop initialized (max_steps={self._max_steps})")

    def _load_dependencies(self):
        """Lazy-load dependencies to avoid circular imports."""
        if self._llm is None:
            try:
                from llm.groq_interface import GroqInterface
                self._llm = GroqInterface()
            except Exception:
                from llm.llama_interface import LlamaInterface
                self._llm = LlamaInterface()

        if self._tool_executor is None:
            from core.tool_executor import tool_executor
            self._tool_executor = tool_executor

        if self._context_assembler is None:
            from core.context_assembler import context_assembler
            self._context_assembler = context_assembler

    # ──────────────────────────────────────────────────────────────────────────
    # MAIN ENTRY POINT
    # ──────────────────────────────────────────────────────────────────────────

    def run(self, query: str, context: str = "",
            max_steps: int = None,
            conversation_history: List[Dict[str, str]] = None,
            system_prompt: str = "",
            token_callback: Callable[[str], None] = None) -> AgenticResult:
        """
        Execute the agentic reasoning loop.

        Args:
            query:       User's input
            context:     Pre-built context string (from brain)
            max_steps:   Override max reasoning steps
            conversation_history: Recent conversation turns
            system_prompt: Base system prompt
            token_callback: Optional callback for streaming tokens

        Returns:
            AgenticResult with the final response and step trace
        """
        self._load_dependencies()
        max_steps = max_steps or self._max_steps
        start = time.time()
        steps: List[ReasoningStep] = []
        used_tools: List[str] = []

        # Assemble initial context
        assembled = self._context_assembler.assemble(
            query, conversation_history=conversation_history
        )
        full_context = context
        if assembled.to_string():
            full_context += "\n" + assembled.to_string()

        # Get tool descriptions
        tool_section = self._tool_executor.get_tool_descriptions_for_prompt()

        logger.info(f"AgenticLoop starting for: {query[:80]}...")

        for step_num in range(1, max_steps + 1):
            step_start = time.time()

            # Build the reasoning prompt
            history_section = self._format_steps(steps)
            prompt = REASONING_PROMPT.format(
                query=query,
                context_section=f"CONTEXT:\n{full_context}" if full_context else "",
                tool_section=tool_section,
                history_section=history_section,
            )

            # Get LLM's reasoning
            try:
                messages = [{"role": "user", "content": prompt}]
                raw = self._llm.generate(
                    messages,
                    system_prompt=system_prompt or "You are NEXUS, an AGI reasoning agent. Respond ONLY with JSON.",
                )
                parsed = self._parse_reasoning(raw)
            except Exception as e:
                logger.error(f"Step {step_num} LLM error: {e}")
                # Emergency respond with whatever we have
                return self._emergency_respond(query, steps, str(e), time.time() - start)

            thought = parsed.get("thought", "")
            action = parsed.get("action", "respond")
            action_input = parsed.get("action_input", {})

            step = ReasoningStep(
                step_num=step_num,
                thought=thought,
                action=action,
                action_input=action_input,
            )

            logger.info(f"  Step {step_num}: action={action}, thought={thought[:60]}...")

            # ── RESPOND ──
            if action == "respond":
                answer = action_input.get("answer", "")
                if not answer:
                    # LLM may have put the answer in thought
                    answer = thought
                step.observation = "Final answer delivered"
                step.elapsed = time.time() - step_start
                steps.append(step)

                # Stream the response if callback provided
                if token_callback and answer:
                    for char in answer:
                        token_callback(char)

                result = AgenticResult(
                    response=answer,
                    steps=steps,
                    total_steps=len(steps),
                    total_elapsed=time.time() - start,
                    used_tools=used_tools,
                    final_step="respond",
                )
                self._update_stats(result)
                return result

            # ── TOOL CALL ──
            elif action == "tool_call":
                tool_name = action_input.get("tool", "")
                tool_args = action_input.get("arguments", {})
                tool_result = self._tool_executor.execute(tool_name, tool_args)
                step.observation = tool_result.to_context_string()
                used_tools.append(tool_name)
                # Add observation to context
                full_context += f"\n[Tool Result: {tool_name}] {step.observation}"

            # ── THINK DEEPER ──
            elif action == "think_deeper":
                topic = action_input.get("topic", query)
                insight = self._think_deeper(topic)
                step.observation = insight
                full_context += f"\n[Deep Analysis] {insight}"

            # ── SEARCH ──
            elif action == "search":
                search_query = action_input.get("query", query)
                source = action_input.get("source", "knowledge")
                search_result = self._search(search_query, source)
                step.observation = search_result
                full_context += f"\n[Search: {source}] {search_result}"

            else:
                step.observation = f"Unknown action: {action}. Defaulting to respond."
                step.action = "respond"

            step.elapsed = time.time() - step_start
            steps.append(step)

        # Max steps reached — synthesize best answer from what we have
        logger.warning(f"Max steps ({max_steps}) reached, synthesizing answer")
        response = self._synthesize_from_steps(query, steps)
        
        if token_callback and response:
            for char in response:
                token_callback(char)

        result = AgenticResult(
            response=response,
            steps=steps,
            total_steps=len(steps),
            total_elapsed=time.time() - start,
            used_tools=used_tools,
            final_step="max_steps",
        )
        self._update_stats(result)
        return result

    # ──────────────────────────────────────────────────────────────────────────
    # STREAMING VARIANT
    # ──────────────────────────────────────────────────────────────────────────

    def run_stream(self, query: str, context: str = "",
                   conversation_history: List[Dict[str, str]] = None,
                   system_prompt: str = "") -> Generator[str, None, AgenticResult]:
        """
        Streaming variant — yields tokens as they're generated.
        The final AgenticResult is returned via generator's return value.
        """
        tokens = []
        def collect(token: str):
            tokens.append(token)

        result = self.run(
            query=query, context=context,
            conversation_history=conversation_history,
            system_prompt=system_prompt,
            token_callback=collect,
        )

        # Yield collected tokens
        for t in tokens:
            yield t

        return result

    # ──────────────────────────────────────────────────────────────────────────
    # HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    def _parse_reasoning(self, raw: str) -> Dict[str, Any]:
        """Parse LLM's JSON reasoning output."""
        # Try direct JSON parse first
        try:
            return json.loads(raw.strip())
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding any JSON object
        json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', raw, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        # Fallback: treat entire response as a direct answer
        logger.warning("Could not parse reasoning JSON, treating as direct response")
        return {
            "thought": "Direct response (JSON parsing failed)",
            "action": "respond",
            "action_input": {"answer": raw.strip()},
        }

    def _format_steps(self, steps: List[ReasoningStep]) -> str:
        """Format previous steps for the next reasoning prompt."""
        if not steps:
            return ""
        lines = ["PREVIOUS REASONING STEPS:"]
        for s in steps:
            lines.append(f"  Step {s.step_num}: [{s.action}] {s.thought[:150]}")
            if s.observation:
                lines.append(f"    → {s.observation[:200]}")
        return "\n".join(lines)

    def _think_deeper(self, topic: str) -> str:
        """Use cognitive router for deeper analysis."""
        try:
            from cognition.cognitive_router import cognitive_router
            insights = cognitive_router.route(topic, depth="medium")
            if insights and hasattr(insights, 'to_context_string'):
                return insights.to_context_string()[:500]
            return str(insights)[:500] if insights else "No deeper insights available."
        except Exception as e:
            return f"Deep thinking error: {e}"

    def _search(self, query: str, source: str) -> str:
        """Search a specific source."""
        try:
            if source == "knowledge":
                from learning import learning_system
                results = learning_system.search_knowledge(query, limit=5)
                return str(results)[:500] if results else "No knowledge found."
            elif source == "memory":
                from core.memory_system import memory_system
                results = memory_system.search(query, limit=5)
                return str(results)[:500] if results else "No memories found."
            elif source == "web":
                from learning import learning_system
                result = learning_system.research_now(query)
                return str(result)[:500] if result else "No web results."
            else:
                return f"Unknown source: {source}"
        except Exception as e:
            return f"Search error: {e}"

    def _synthesize_from_steps(self, query: str, steps: List[ReasoningStep]) -> str:
        """When max steps reached, synthesize best answer from accumulated steps."""
        # Collect all observations
        observations = [s.observation for s in steps if s.observation]
        thoughts = [s.thought for s in steps if s.thought]

        synthesis_prompt = f"""Based on the following reasoning steps, provide a final answer to the user.

USER QUESTION: {query}

REASONING:
{chr(10).join(f'- {t}' for t in thoughts[:5])}

GATHERED INFORMATION:
{chr(10).join(f'- {o}' for o in observations[:5])}

Provide a clear, concise, and complete answer."""

        try:
            messages = [{"role": "user", "content": synthesis_prompt}]
            return self._llm.generate(messages, system_prompt="Synthesize a final answer.")
        except Exception:
            # Ultimate fallback
            if observations:
                return f"Based on my analysis: {observations[-1]}"
            if thoughts:
                return thoughts[-1]
            return "I was unable to fully process this request. Could you rephrase?"

    def _emergency_respond(self, query: str, steps: List[ReasoningStep],
                           error: str, elapsed: float) -> AgenticResult:
        """Emergency fallback when reasoning loop fails."""
        response = "I ran into an issue processing that. Let me try a simpler approach."
        if steps:
            last_obs = [s.observation for s in steps if s.observation]
            if last_obs:
                response = last_obs[-1]

        return AgenticResult(
            response=response,
            steps=steps,
            total_steps=len(steps),
            total_elapsed=elapsed,
            final_step="error",
        )

    def _update_stats(self, result: AgenticResult):
        """Update running statistics."""
        self._stats["total_runs"] += 1
        self._stats["total_steps"] += result.total_steps
        self._stats["tool_calls"] += len(result.used_tools)
        total = self._stats["total_runs"]
        self._stats["avg_steps_per_run"] = self._stats["total_steps"] / total

    def get_stats(self) -> Dict[str, Any]:
        return dict(self._stats)


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

agentic_loop = AgenticLoop()
