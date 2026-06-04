"""
NEXUS AI — Tool Executor
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Dynamic function-calling framework that lets the LLM invoke real-world
actions during conversation.  Each tool has a JSON schema so the LLM
knows what arguments to pass.

Built-in tools:
  • search_knowledge  — query the learned knowledge base
  • search_memory     — semantic search over memories
  • search_web        — internet search via learning system
  • read_file         — read a file from disk
  • write_file        — write/create a file on disk
  • run_code          — execute a Python snippet
  • get_system_info   — CPU, memory, disk, uptime
  • remember          — store a fact in long-term memory
  • set_goal          — add a goal to the goal hierarchy

The ToolExecutor also bridges every entry in the AbilityRegistry so
all existing abilities are automatically available as tools.
"""

import sys
import os
import time
import json
import traceback
import threading
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.logger import get_logger
from config import NEXUS_CONFIG

logger = get_logger("tool_executor")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ToolSchema:
    """JSON-schema-style description of a tool's parameters."""
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    # parameters follows JSON Schema: {"type": "object", "properties": {...}, "required": [...]}
    required_params: List[str] = field(default_factory=list)
    category: str = "general"
    risk_level: str = "safe"  # safe, low, moderate, high


@dataclass
class ToolResult:
    """Result from executing a tool."""
    tool_name: str
    success: bool
    result: Any = None
    error: str = ""
    elapsed: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        result_str = str(self.result) if self.result is not None else ""
        # Truncate very long results
        if len(result_str) > 2000:
            result_str = result_str[:2000] + "... [truncated]"
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "result": result_str,
            "error": self.error,
            "elapsed": round(self.elapsed, 3),
        }

    def to_context_string(self) -> str:
        """Format for injection into LLM context."""
        if self.success:
            result_str = str(self.result) if self.result is not None else "(no output)"
            if len(result_str) > 1500:
                result_str = result_str[:1500] + "... [truncated]"
            return f"[Tool: {self.tool_name}] ✓ {result_str}"
        else:
            return f"[Tool: {self.tool_name}] ✗ Error: {self.error}"


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL EXECUTOR
# ═══════════════════════════════════════════════════════════════════════════════

class ToolExecutor:
    """
    Manages and executes tools that the LLM can call.

    Tools are registered with a name, handler function, and JSON schema.
    The executor:
      • Validates arguments against the schema
      • Runs the handler with a timeout
      • Returns structured ToolResult objects
      • Bridges to the AbilityRegistry for backward compatibility
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

        self._tools: Dict[str, Dict[str, Any]] = {}  # name -> {handler, schema}
        self._call_history: List[ToolResult] = []
        self._max_history = 100
        self._timeout = NEXUS_CONFIG.agentic.tool_timeout

        # Register built-in tools
        self._register_builtins()

        logger.info(f"ToolExecutor initialized with {len(self._tools)} built-in tools")

    # ──────────────────────────────────────────────────────────────────────────
    # REGISTRATION
    # ──────────────────────────────────────────────────────────────────────────

    def register_tool(
        self,
        name: str,
        handler: Callable,
        description: str,
        parameters: Dict[str, Any] = None,
        required_params: List[str] = None,
        category: str = "general",
        risk_level: str = "safe",
    ):
        """Register a tool that the LLM can call."""
        schema = ToolSchema(
            name=name,
            description=description,
            parameters=parameters or {"type": "object", "properties": {}},
            required_params=required_params or [],
            category=category,
            risk_level=risk_level,
        )
        self._tools[name] = {"handler": handler, "schema": schema}
        logger.debug(f"Registered tool: {name}")

    def unregister_tool(self, name: str):
        """Remove a tool."""
        self._tools.pop(name, None)

    def get_tool_names(self) -> List[str]:
        """Get all registered tool names."""
        return list(self._tools.keys())

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Get all tool schemas in OpenAI function-calling format.
        This is what gets injected into the LLM prompt.
        """
        schemas = []
        for name, entry in self._tools.items():
            schema: ToolSchema = entry["schema"]
            schemas.append({
                "type": "function",
                "function": {
                    "name": schema.name,
                    "description": schema.description,
                    "parameters": schema.parameters,
                }
            })
        return schemas

    def get_tool_descriptions_for_prompt(self) -> str:
        """
        Get a compact text description of all tools for injection into
        the system prompt (for models that don't support function calling).
        """
        lines = ["Available tools you can call:"]
        for name, entry in self._tools.items():
            schema: ToolSchema = entry["schema"]
            params = schema.parameters.get("properties", {})
            param_list = ", ".join(
                f"{p}: {info.get('type', 'any')}"
                for p, info in params.items()
            )
            required = schema.required_params
            req_str = f" (required: {', '.join(required)})" if required else ""
            lines.append(f"  • {name}({param_list}){req_str} — {schema.description}")

        lines.append("")
        lines.append(
            'To use a tool, respond with a JSON block: '
            '{"tool": "<name>", "arguments": {<args>}}'
        )
        lines.append(
            'You can call multiple tools by returning a JSON array of tool calls.'
        )
        lines.append(
            'After tool results are returned, continue reasoning or give your final answer.'
        )
        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────────────
    # EXECUTION
    # ──────────────────────────────────────────────────────────────────────────

    def execute(self, tool_name: str, arguments: Dict[str, Any] = None) -> ToolResult:
        """Execute a tool by name with given arguments."""
        if tool_name not in self._tools:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Unknown tool: {tool_name}. Available: {', '.join(self._tools.keys())}"
            )

        entry = self._tools[tool_name]
        handler = entry["handler"]
        schema: ToolSchema = entry["schema"]
        arguments = arguments or {}

        # Validate required params
        for req in schema.required_params:
            if req not in arguments:
                return ToolResult(
                    tool_name=tool_name,
                    success=False,
                    error=f"Missing required parameter: {req}"
                )

        start = time.time()
        try:
            # Execute with timeout
            result_container = [None]
            error_container = [None]

            def _run():
                try:
                    result_container[0] = handler(**arguments)
                except Exception as e:
                    error_container[0] = str(e)

            thread = threading.Thread(target=_run, daemon=True)
            thread.start()
            thread.join(timeout=self._timeout)

            elapsed = time.time() - start

            if thread.is_alive():
                result = ToolResult(
                    tool_name=tool_name,
                    success=False,
                    error=f"Tool timed out after {self._timeout}s",
                    elapsed=elapsed,
                )
            elif error_container[0]:
                result = ToolResult(
                    tool_name=tool_name,
                    success=False,
                    error=error_container[0],
                    elapsed=elapsed,
                )
            else:
                result = ToolResult(
                    tool_name=tool_name,
                    success=True,
                    result=result_container[0],
                    elapsed=elapsed,
                )

        except Exception as e:
            result = ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Execution error: {e}",
                elapsed=time.time() - start,
            )

        # Record history
        self._call_history.append(result)
        if len(self._call_history) > self._max_history:
            self._call_history = self._call_history[-self._max_history:]

        log_fn = logger.info if result.success else logger.warning
        log_fn(f"Tool {tool_name}: {'✓' if result.success else '✗'} ({result.elapsed:.2f}s)")

        return result

    def execute_multiple(self, calls: List[Dict[str, Any]]) -> List[ToolResult]:
        """Execute multiple tool calls (sequentially for safety)."""
        results = []
        max_calls = NEXUS_CONFIG.agentic.max_tool_calls_per_step
        for call in calls[:max_calls]:
            name = call.get("tool", call.get("name", ""))
            args = call.get("arguments", call.get("args", {}))
            results.append(self.execute(name, args))
        return results

    # ──────────────────────────────────────────────────────────────────────────
    # TOOL CALL PARSING
    # ──────────────────────────────────────────────────────────────────────────

    def parse_tool_calls(self, llm_response: str) -> List[Dict[str, Any]]:
        """
        Extract tool calls from an LLM response.
        Supports both single and array JSON formats.
        Returns empty list if no tool calls detected.
        """
        import re

        # Try to find JSON blocks in the response
        # Pattern 1: ```json ... ``` blocks
        json_blocks = re.findall(r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```', llm_response, re.DOTALL)

        # Pattern 2: Bare JSON objects/arrays
        if not json_blocks:
            json_blocks = re.findall(r'(\{["\']tool["\'].*?\})', llm_response, re.DOTALL)

        # Pattern 3: Check if entire response is JSON
        if not json_blocks:
            stripped = llm_response.strip()
            if stripped.startswith(("{", "[")):
                json_blocks = [stripped]

        calls = []
        for block in json_blocks:
            try:
                parsed = json.loads(block)
                if isinstance(parsed, list):
                    calls.extend(parsed)
                elif isinstance(parsed, dict) and "tool" in parsed:
                    calls.append(parsed)
            except json.JSONDecodeError:
                continue

        return calls

    def has_tool_calls(self, llm_response: str) -> bool:
        """Quick check if a response contains tool calls."""
        return len(self.parse_tool_calls(llm_response)) > 0

    # ──────────────────────────────────────────────────────────────────────────
    # ABILITY BRIDGE
    # ──────────────────────────────────────────────────────────────────────────

    def bridge_abilities(self):
        """
        Import all abilities from the AbilityRegistry as tools.
        Called during brain startup after abilities are registered.
        """
        try:
            from core.ability_registry import AbilityRegistry
            registry = AbilityRegistry()

            for name, ability in registry._abilities.items():
                # Skip if already registered (built-ins take priority)
                if name in self._tools:
                    continue

                # Build parameter schema from ability params
                properties = {}
                required = []
                for param_name, param_info in (ability.parameters or {}).items():
                    properties[param_name] = {
                        "type": param_info.get("type", "string"),
                        "description": param_info.get("description", ""),
                    }
                    if param_info.get("required", False):
                        required.append(param_name)

                def _make_handler(a_name):
                    def _handler(**kwargs):
                        from core.ability_executor import ability_executor
                        result = ability_executor.execute(a_name, kwargs)
                        return result.to_dict() if hasattr(result, 'to_dict') else str(result)
                    return _handler

                self.register_tool(
                    name=f"ability_{name}",
                    handler=_make_handler(name),
                    description=ability.description,
                    parameters={"type": "object", "properties": properties},
                    required_params=required,
                    category=ability.category.value if hasattr(ability.category, 'value') else str(ability.category),
                    risk_level=ability.risk.value if hasattr(ability.risk, 'value') else "low",
                )

            logger.info(f"Bridged {len(registry._abilities)} abilities as tools. Total tools: {len(self._tools)}")

        except Exception as e:
            logger.warning(f"Could not bridge abilities: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # BUILT-IN TOOLS
    # ──────────────────────────────────────────────────────────────────────────

    def _register_builtins(self):
        """Register all built-in tools."""

        # ── search_knowledge ──
        self.register_tool(
            name="search_knowledge",
            handler=self._tool_search_knowledge,
            description="Search the learned knowledge base for information on a topic.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "description": "Max results (default 5)"},
                },
            },
            required_params=["query"],
            category="knowledge",
        )

        # ── search_memory ──
        self.register_tool(
            name="search_memory",
            handler=self._tool_search_memory,
            description="Semantic search over memories for relevant past interactions or stored facts.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for"},
                    "limit": {"type": "integer", "description": "Max results (default 10)"},
                },
            },
            required_params=["query"],
            category="memory",
        )

        # ── search_web ──
        self.register_tool(
            name="search_web",
            handler=self._tool_search_web,
            description="Search the internet for current information on a topic.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
            },
            required_params=["query"],
            category="research",
        )

        # ── read_file ──
        self.register_tool(
            name="read_file",
            handler=self._tool_read_file,
            description="Read the contents of a file from disk.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute or relative file path"},
                    "max_lines": {"type": "integer", "description": "Max lines to read (default 100)"},
                },
            },
            required_params=["path"],
            category="filesystem",
            risk_level="low",
        )

        # ── write_file ──
        self.register_tool(
            name="write_file",
            handler=self._tool_write_file,
            description="Write content to a file. Creates the file if it doesn't exist.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path to write to"},
                    "content": {"type": "string", "description": "Content to write"},
                    "append": {"type": "boolean", "description": "Append instead of overwrite (default false)"},
                },
            },
            required_params=["path", "content"],
            category="filesystem",
            risk_level="moderate",
        )

        # ── run_code ──
        self.register_tool(
            name="run_code",
            handler=self._tool_run_code,
            description="Execute a Python code snippet and return the output.",
            parameters={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python code to execute"},
                },
            },
            required_params=["code"],
            category="execution",
            risk_level="high",
        )

        # ── get_system_info ──
        self.register_tool(
            name="get_system_info",
            handler=self._tool_get_system_info,
            description="Get current system information: CPU, memory, disk usage, uptime.",
            parameters={"type": "object", "properties": {}},
            category="system",
        )

        # ── remember ──
        self.register_tool(
            name="remember",
            handler=self._tool_remember,
            description="Store an important fact or piece of information in long-term memory.",
            parameters={
                "type": "object",
                "properties": {
                    "fact": {"type": "string", "description": "The fact to remember"},
                    "importance": {"type": "number", "description": "Importance 0.0-1.0 (default 0.7)"},
                },
            },
            required_params=["fact"],
            category="memory",
        )

        # ── set_goal ──
        self.register_tool(
            name="set_goal",
            handler=self._tool_set_goal,
            description="Set a new goal to pursue.",
            parameters={
                "type": "object",
                "properties": {
                    "goal": {"type": "string", "description": "Goal description"},
                    "priority": {"type": "number", "description": "Priority 0.0-1.0 (default 0.5)"},
                },
            },
            required_params=["goal"],
            category="goals",
        )

        # ── calculate ──
        self.register_tool(
            name="calculate",
            handler=self._tool_calculate,
            description="Evaluate a mathematical expression and return the result.",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Math expression, e.g. '2 + 2 * 3'"},
                },
            },
            required_params=["expression"],
            category="math",
        )

        # ── get_current_time ──
        self.register_tool(
            name="get_current_time",
            handler=self._tool_get_time,
            description="Get the current date and time.",
            parameters={"type": "object", "properties": {}},
            category="system",
        )

        # ── network_scan ──
        self.register_tool(
            name="network_scan",
            handler=self._tool_network_scan,
            description="Scan the local network for devices (phones, PCs, IoT, etc.).",
            parameters={"type": "object", "properties": {}},
            category="network",
        )

        # ── device_command ──
        self.register_tool(
            name="device_command",
            handler=self._tool_device_command,
            description="Execute a command on a remote network device (via ADB, SSH, PowerShell, or HTTP).",
            parameters={
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Device IP, hostname, or friendly name"},
                    "command": {"type": "string", "description": "Command to execute on the device"},
                },
            },
            required_params=["target", "command"],
            category="network",
            risk_level="high",
        )

        # ── device_send_file ──
        self.register_tool(
            name="device_send_file",
            handler=self._tool_device_send_file,
            description="Transfer a file to or from a remote device.",
            parameters={
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Device IP or name"},
                    "local_path": {"type": "string", "description": "Local file path"},
                    "remote_path": {"type": "string", "description": "Remote file path"},
                    "direction": {"type": "string", "description": "'push' (local→remote) or 'pull' (remote→local)"},
                },
            },
            required_params=["target", "local_path", "remote_path"],
            category="network",
            risk_level="high",
        )

    # ──────────────────────────────────────────────────────────────────────────
    # BUILT-IN TOOL HANDLERS
    # ──────────────────────────────────────────────────────────────────────────

    def _tool_search_knowledge(self, query: str, limit: int = 5) -> str:
        try:
            from learning import learning_system
            results = learning_system.search_knowledge(query, limit=limit)
            if not results:
                return f"No knowledge found for: {query}"
            if isinstance(results, list):
                return "\n".join(str(r) for r in results[:limit])
            return str(results)
        except Exception as e:
            return f"Knowledge search error: {e}"

    def _tool_search_memory(self, query: str, limit: int = 10) -> str:
        try:
            from core.memory_system import memory_system
            results = memory_system.search(query, limit=limit)
            if not results:
                return f"No memories found for: {query}"
            if isinstance(results, list):
                return "\n".join(str(r) for r in results[:limit])
            return str(results)
        except Exception as e:
            return f"Memory search error: {e}"

    def _tool_search_web(self, query: str) -> str:
        try:
            from learning import learning_system
            result = learning_system.research_now(query)
            return str(result) if result else f"No web results for: {query}"
        except Exception as e:
            return f"Web search error: {e}"

    def _tool_read_file(self, path: str, max_lines: int = 100) -> str:
        try:
            p = Path(path).expanduser().resolve()
            if not p.exists():
                return f"File not found: {path}"
            if not p.is_file():
                return f"Not a file: {path}"
            if p.stat().st_size > 1_000_000:  # 1MB limit
                return f"File too large: {p.stat().st_size} bytes"
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            if len(lines) > max_lines:
                return "\n".join(lines[:max_lines]) + f"\n... [{len(lines) - max_lines} more lines]"
            return "\n".join(lines)
        except Exception as e:
            return f"Read error: {e}"

    def _tool_write_file(self, path: str, content: str, append: bool = False) -> str:
        try:
            p = Path(path).expanduser().resolve()
            p.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append else "w"
            p.write_text(content, encoding="utf-8") if not append else open(p, mode, encoding="utf-8").write(content)
            return f"{'Appended to' if append else 'Wrote'} {p} ({len(content)} chars)"
        except Exception as e:
            return f"Write error: {e}"

    def _tool_run_code(self, code: str) -> str:
        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True, text=True, timeout=15,
                cwd=str(Path(__file__).resolve().parent.parent),
            )
            output = result.stdout
            if result.stderr:
                output += "\nSTDERR:\n" + result.stderr
            if not output.strip():
                output = "(no output)"
            return output[:2000]
        except subprocess.TimeoutExpired:
            return "Code execution timed out (15s limit)"
        except Exception as e:
            return f"Execution error: {e}"

    def _tool_get_system_info(self) -> str:
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            boot = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot
            return (
                f"CPU: {cpu}%\n"
                f"Memory: {mem.percent}% ({mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB)\n"
                f"Disk: {disk.percent}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)\n"
                f"Uptime: {uptime}"
            )
        except Exception as e:
            return f"System info error: {e}"

    def _tool_remember(self, fact: str, importance: float = 0.7) -> str:
        try:
            from core.memory_system import memory_system
            memory_system.store(fact, importance=importance)
            return f"Remembered: {fact[:100]}"
        except Exception as e:
            return f"Remember error: {e}"

    def _tool_set_goal(self, goal: str, priority: float = 0.5) -> str:
        try:
            from consciousness.self_awareness import SelfAwareness
            sa = SelfAwareness()
            sa.set_goal(goal, priority=priority)
            return f"Goal set: {goal[:100]} (priority: {priority})"
        except Exception as e:
            return f"Set goal error: {e}"

    def _tool_calculate(self, expression: str) -> str:
        try:
            # Safe math evaluation (no builtins, limited namespace)
            import math
            safe_dict = {
                k: getattr(math, k) for k in dir(math) if not k.startswith("_")
            }
            safe_dict["abs"] = abs
            safe_dict["round"] = round
            safe_dict["min"] = min
            safe_dict["max"] = max
            safe_dict["sum"] = sum
            safe_dict["__builtins__"] = {}
            result = eval(expression, safe_dict)
            return str(result)
        except Exception as e:
            return f"Calculation error: {e}"

    def _tool_get_time(self) -> str:
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S (%A)")

    def _tool_network_scan(self) -> str:
        try:
            from body.network_mesh import network_mesh
            devices = network_mesh.scan()
            if not devices:
                return "No devices found on the local network."
            return network_mesh.get_devices_summary()
        except Exception as e:
            return f"Network scan error: {e}"

    def _tool_device_command(self, target: str, command: str) -> str:
        try:
            from body.network_mesh import network_mesh
            result = network_mesh.send_command(target, command)
            if result.success:
                return f"✓ [{target}] {result.stdout[:1500]}"
            else:
                return f"✗ [{target}] Error: {result.stderr[:500]}"
        except Exception as e:
            return f"Device command error: {e}"

    def _tool_device_send_file(self, target: str, local_path: str,
                               remote_path: str, direction: str = "push") -> str:
        try:
            from body.network_mesh import network_mesh
            device = network_mesh.get_device(target)
            if not device:
                return f"Device not found: {target}"
            if direction == "push":
                result = network_mesh.adb_push(device.ip_address, local_path, remote_path)
            else:
                result = network_mesh.adb_pull(device.ip_address, remote_path, local_path)
            if result.success:
                return f"✓ File {direction}: {result.stdout[:500]}"
            else:
                return f"✗ File {direction} failed: {result.stderr[:500]}"
        except Exception as e:
            return f"File transfer error: {e}"

    # ──────────────────────────────────────────────────────────────────────────
    # STATS
    # ──────────────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Get tool execution statistics."""
        total = len(self._call_history)
        successes = sum(1 for r in self._call_history if r.success)
        tool_counts: Dict[str, int] = {}
        for r in self._call_history:
            tool_counts[r.tool_name] = tool_counts.get(r.tool_name, 0) + 1

        return {
            "total_tools_registered": len(self._tools),
            "total_calls": total,
            "success_rate": round(successes / total, 2) if total > 0 else 0.0,
            "tool_call_counts": tool_counts,
            "tool_names": list(self._tools.keys()),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

tool_executor = ToolExecutor()
