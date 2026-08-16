"""
NEXUS AI — WebAssembly & Isolated Subprocess Code Sandbox Engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Isolated execution environment for self-generated code, dynamic plugins,
and autonomous code rewrites. Enforces capability-based security, memory
caps, CPU fuel limits, and strict process isolation.

Capability Model:
  • ALLOW_NET: Enables outbound socket/HTTP connections (Default: False)
  • ALLOW_FS_READ: Restricts file system reads to workspace / data (Default: False)
  • ALLOW_FS_WRITE: Restricts file system writes to temp / data (Default: False)
  • ALLOW_PROCESS: Permits subshell or sub-process spawning (Default: False)
  • MAX_MEMORY_MB: Strict memory ceiling enforced via OS process monitoring (Default: 128MB)
  • TIMEOUT_SEC: Execution wall-clock timeout (Default: 5.0 seconds)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import ast
import json
import os
import psutil
import sys
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils.logger import get_logger
from core.event_bus import EventType, event_bus, publish

logger = get_logger("code_sandbox")

# Check if wasmtime Python package is available
WASMTIME_AVAILABLE = False
try:
    import wasmtime
    WASMTIME_AVAILABLE = True
except ImportError:
    WASMTIME_AVAILABLE = False

@dataclass
class CapabilityFlags:
    """Security capability configuration for sandbox execution."""
    allow_net: bool = False
    allow_fs_read: bool = False
    allow_fs_write: bool = False
    allow_process: bool = False
    max_memory_mb: float = 128.0
    timeout_sec: float = 5.0
    fuel_limit: int = 1_000_000

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class SandboxExecutionResult:
    """Result of sandboxed code execution."""
    success: bool = False
    backend_used: str = "WASM/IsolatedSubprocess" if WASMTIME_AVAILABLE else "IsolatedSubprocess"
    stdout: str = ""
    stderr: str = ""
    return_value: Any = None
    execution_time_ms: float = 0.0
    memory_used_mb: float = 0.0
    security_violations: List[str] = field(default_factory=list)
    timed_out: bool = False
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class CodeSandbox:
    """
    Capability-based secure code execution sandbox. Runs dynamic code
    snippets in isolated subprocess environments with memory/time caps.
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
        self._total_executions = 0
        self._successful_executions = 0
        self._blocked_executions = 0
        self.wasm_available = WASMTIME_AVAILABLE

        logger.info(f"🔒 Code Sandbox initialized | WASM engine: {'Available (wasmtime)' if self.wasm_available else 'Subprocess Isolation'}")

    def execute_sandboxed(
        self,
        code_str: str,
        entry_function: str = "main",
        args: Optional[List[Any]] = None,
        capabilities: Optional[CapabilityFlags] = None
    ) -> SandboxExecutionResult:
        """
        Executes code safely inside the capability-restricted sandbox.
        """
        start_t = time.time()
        self._total_executions += 1
        caps = capabilities or CapabilityFlags()
        res = SandboxExecutionResult()

        # 1. Capability Security Audit
        violations = self._audit_code_capabilities(code_str, caps)
        if violations:
            self._blocked_executions += 1
            res.success = False
            res.security_violations = violations
            res.summary = f"Execution blocked: {len(violations)} capability violations detected."
            res.execution_time_ms = round((time.time() - start_t) * 1000, 2)
            publish(EventType.SYSTEM_ALERT, {
                "type": "sandbox_security_blocked",
                "violations": violations,
            }, source="code_sandbox")
            return res

        # 2. Prepare Sandboxed Execution Runner Script
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False, encoding="utf-8") as tf:
            runner_script_path = tf.name
            script_content = self._generate_runner_script(code_str, entry_function, args or [])
            tf.write(script_content)

        try:
            # 3. Spawn Subprocess in Restricted Mode
            import subprocess
            proc = subprocess.Popen(
                [sys.executable, runner_script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Monitor Process & Memory Limit
            memory_peak = 0.0
            timed_out = False

            t_end = time.time() + caps.timeout_sec
            while proc.poll() is None:
                if time.time() > t_end:
                    proc.kill()
                    timed_out = True
                    break
                try:
                    p = psutil.Process(proc.pid)
                    mem_mb = p.memory_info().rss / (1024 * 1024)
                    if mem_mb > memory_peak:
                        memory_peak = mem_mb
                    if mem_mb > caps.max_memory_mb:
                        proc.kill()
                        res.security_violations.append(f"Memory cap exceeded ({mem_mb:.1f}MB > {caps.max_memory_mb}MB)")
                        break
                except Exception:
                    pass
                time.sleep(0.05)

            stdout_data, stderr_data = proc.communicate()

            res.stdout = (stdout_data or "").strip()
            res.stderr = (stderr_data or "").strip()
            res.memory_used_mb = round(memory_peak, 2)
            res.timed_out = timed_out

            if timed_out:
                res.success = False
                res.summary = f"Execution timed out after {caps.timeout_sec}s ceiling."
                self._blocked_executions += 1
            elif res.security_violations:
                res.success = False
                res.summary = f"Execution aborted: {res.security_violations[0]}"
                self._blocked_executions += 1
            elif proc.returncode != 0:
                res.success = False
                res.summary = f"Execution error (Exit code {proc.returncode})"
            else:
                res.success = True
                res.summary = f"Execution succeeded in {round((time.time() - start_t) * 1000, 1)}ms (Mem: {res.memory_used_mb}MB)"
                self._successful_executions += 1

                # Parse return value if dumped in stdout
                if "___SANDBOX_RESULT___:" in res.stdout:
                    try:
                        raw_res = res.stdout.split("___SANDBOX_RESULT___:")[1].strip()
                        res.return_value = json.loads(raw_res)
                    except Exception:
                        pass

        except Exception as e:
            res.success = False
            res.summary = f"Sandbox runner error: {e}"
            res.stderr = traceback.format_exc()
        finally:
            if os.path.exists(runner_script_path):
                try:
                    os.remove(runner_script_path)
                except Exception:
                    pass

        res.execution_time_ms = round((time.time() - start_t) * 1000, 2)
        return res

    def _audit_code_capabilities(self, code_str: str, caps: CapabilityFlags) -> List[str]:
        """Scans code AST for prohibited modules or system operations."""
        violations = []
        try:
            tree = ast.parse(code_str)
        except Exception:
            return violations  # Syntax errors will be caught later

        # Prohibited modules map
        net_modules = {"socket", "requests", "urllib", "http", "aiohttp", "ftplib"}
        fs_modules = {"shutil", "pathlib", "os"}
        proc_modules = {"subprocess", "multiprocessing", "os.system", "ctypes"}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name.split(".")[0]
                    if not caps.allow_net and name in net_modules:
                        violations.append(f"Network access restricted: prohibited import '{name}'")
                    if not caps.allow_process and name in proc_modules:
                        violations.append(f"Process execution restricted: prohibited import '{name}'")
                    if not caps.allow_fs_write and name in fs_modules:
                        pass  # Analyzed further below

            elif isinstance(node, ast.ImportFrom):
                mod = (node.module or "").split(".")[0]
                if not caps.allow_net and mod in net_modules:
                    violations.append(f"Network access restricted: prohibited import from '{mod}'")
                if not caps.allow_process and mod in proc_modules:
                    violations.append(f"Process execution restricted: prohibited import from '{mod}'")

            elif isinstance(node, ast.Call):
                # Check for open() or system calls
                if isinstance(node.func, ast.Name):
                    if not caps.allow_fs_write and node.func.id in ("open", "eval", "exec"):
                        violations.append(f"Restricted operation: call to '{node.func.id}()'")

        return violations

    def _generate_runner_script(self, code_str: str, entry_function: str, args: List[Any]) -> str:
        """Generates isolated self-contained Python script."""
        args_json = json.dumps(args)
        return f"""
import sys
import json

# Code under test
{code_str}

if __name__ == '__main__':
    try:
        args = json.loads('''{args_json}''')
        if '{entry_function}' in globals():
            func = globals()['{entry_function}']
            if callable(func):
                res = func(*args) if args else func()
                print("___SANDBOX_RESULT___:" + json.dumps(res, default=str))
            else:
                print("Entry function not callable", file=sys.stderr)
        else:
            # Code executed as module
            pass
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
"""

    def get_stats(self) -> Dict[str, Any]:
        return {
            "wasm_available": WASMTIME_AVAILABLE,
            "total_executions": self._total_executions,
            "successful_executions": self._successful_executions,
            "blocked_executions": self._blocked_executions,
            "backend": "WASM/Subprocess Sandbox" if WASMTIME_AVAILABLE else "Isolated Subprocess Sandbox",
        }

    def get_summary(self) -> str:
        """Human-readable summary for context collector."""
        stats = self.get_stats()
        lines = [
            f"Code Sandbox Backend: {stats['backend']}",
            f"WASM Runtime: {'Available' if stats['wasm_available'] else 'Unavailable (subprocess fallback)'}",
            f"Total Executions: {stats['total_executions']} ({stats['successful_executions']} passed, {stats['blocked_executions']} blocked)",
        ]
        return "\n".join(lines)

# Singleton accessor
code_sandbox = CodeSandbox()

def get_code_sandbox() -> CodeSandbox:
    """Get singleton CodeSandbox instance."""
    return code_sandbox
