"""
NEXUS AI — Ability Executor
═══════════════════════════════════════════════════════════════════════════════
Detects ability invocations in LLM responses and executes them.

This module:
1. Scans LLM responses for [ABILITY: name] [PARAMS: {...}] patterns
2. Parses and validates the ability call
3. Executes the ability via the AbilityRegistry
4. Returns results that can be fed back to the LLM
5. Handles errors gracefully

This completes the loop: LLM decides → Executor detects → Registry executes → Results returned
═══════════════════════════════════════════════════════════════════════════════
"""

import re
import json
import threading
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger
from core.ability_registry import ability_registry, AbilityResult

logger = get_logger("ability_executor")


# ═══════════════════════════════════════════════════════════════════════════════
# PATTERNS FOR ABILITY DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

# Primary pattern: [ABILITY: name] [PARAMS: {...}]
ABILITY_PATTERN = re.compile(
    r'\[ABILITY:\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\]',
    re.IGNORECASE
)

PARAMS_PATTERN = re.compile(
    r'\[PARAMS:\s*(\{.*?\})\s*\]',
    re.DOTALL
)

# Alternative pattern: [INVOKE: name(...)] - more natural
INVOKE_PATTERN = re.compile(
    r'\[INVOKE:\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*?)\)\s*\]',
    re.DOTALL
)

# XML-style pattern: <ability name="..." params="..."/>
XML_ABILITY_PATTERN = re.compile(
    r'<ability\s+name=["\']([a-zA-Z_][a-zA-Z0-9_]*)["\'](?:\s+params=["\'](.*?)["\'])?\s*/>',
    re.IGNORECASE
)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AbilityInvocation:
    """A parsed ability invocation from LLM output"""
    name: str
    params: Dict[str, Any]
    match_start: int
    match_end: int
    raw_text: str
    result: Optional[AbilityResult] = None
    executed: bool = False


@dataclass
class ExecutionReport:
    """Report of ability executions from a response"""
    invocations: List[AbilityInvocation]
    successful: int
    failed: int
    total_time: float
    
    def get_summary(self) -> str:
        """Get a summary for LLM context"""
        if not self.invocations:
            return ""
        
        lines = [f"ABILITIES EXECUTED: {self.successful} succeeded, {self.failed} failed"]
        
        for inv in self.invocations:
            if inv.executed and inv.result:
                status = "✅" if inv.result.success else "❌"
                lines.append(
                    f"  {status} {inv.name}: {inv.result.message or inv.result.error}"
                )
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# ABILITY EXECUTOR
# ═══════════════════════════════════════════════════════════════════════════════

class AbilityExecutor:
    """
    Detects and executes ability invocations from LLM responses.
    
    The executor:
    1. Parses LLM output for ability calls
    2. Validates parameters
    3. Executes abilities via the registry
    4. Returns results for context injection
    
    This gives the LLM real agency over NEXUS's systems.
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
        
        # Reference to registry
        self._registry = ability_registry
        
        # Execution history
        self._execution_history: List[ExecutionReport] = []
        self._max_history = 100
        
        # Blocked abilities (safety)
        self._blocked_abilities: set = set()
        
        # Auto-execute flag (if False, just return what would be executed)
        self._auto_execute = True
        
        logger.info("✅ Ability Executor initialized")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # DETECTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def detect_invocations(self, text: str) -> List[AbilityInvocation]:
        """
        Detect all ability invocations in text.
        
        Supports multiple formats:
        - [ABILITY: name] [PARAMS: {...}]
        - [INVOKE: name(params)]
        - <ability name="..." params="..."/>
        """
        invocations = []
        
        # Pattern 1: [ABILITY: name] [PARAMS: {...}]
        for ability_match in ABILITY_PATTERN.finditer(text):
            name = ability_match.group(1).lower()
            start = ability_match.start()
            
            # Look for params after the ability tag
            params = {}
            params_match = PARAMS_PATTERN.search(text[start:start+500])
            
            if params_match:
                try:
                    params = json.loads(params_match.group(1))
                    end = start + params_match.end()
                except json.JSONDecodeError:
                    end = ability_match.end()
            else:
                end = ability_match.end()
            
            invocations.append(AbilityInvocation(
                name=name,
                params=params,
                match_start=start,
                match_end=end,
                raw_text=text[start:end]
            ))
        
        # Pattern 2: [INVOKE: name(...)]
        for invoke_match in INVOKE_PATTERN.finditer(text):
            name = invoke_match.group(1).lower()
            params_str = invoke_match.group(2).strip()
            
            # Parse params - could be JSON or key=value format
            params = {}
            if params_str:
                try:
                    # Try JSON first
                    params = json.loads("{" + params_str + "}" if not params_str.startswith("{") else params_str)
                except json.JSONDecodeError:
                    # Try key=value format
                    for pair in params_str.split(","):
                        if "=" in pair:
                            k, v = pair.split("=", 1)
                            params[k.strip()] = v.strip().strip('"\'')
            
            invocations.append(AbilityInvocation(
                name=name,
                params=params,
                match_start=invoke_match.start(),
                match_end=invoke_match.end(),
                raw_text=invoke_match.group(0)
            ))
        
        # Pattern 3: <ability name="..." params="..."/>
        for xml_match in XML_ABILITY_PATTERN.finditer(text):
            name = xml_match.group(1).lower()
            params_str = xml_match.group(2)
            
            params = {}
            if params_str:
                try:
                    params = json.loads(params_str)
                except json.JSONDecodeError:
                    pass
            
            invocations.append(AbilityInvocation(
                name=name,
                params=params,
                match_start=xml_match.start(),
                match_end=xml_match.end(),
                raw_text=xml_match.group(0)
            ))
        
        # Deduplicate overlapping matches
        invocations = self._deduplicate_invocations(invocations)
        
        return invocations
    
    def _deduplicate_invocations(self, invocations: List[AbilityInvocation]) -> List[AbilityInvocation]:
        """Remove duplicate/overlapping invocations"""
        if not invocations:
            return []
        
        # Sort by start position
        invocations.sort(key=lambda x: x.match_start)
        
        # Keep non-overlapping
        result = [invocations[0]]
        for inv in invocations[1:]:
            if inv.match_start >= result[-1].match_end:
                result.append(inv)
            elif inv.name != result[-1].name:
                # Different ability, keep both (might be nested)
                result.append(inv)
        
        return result
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EXECUTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def execute(self, invocation: AbilityInvocation) -> AbilityResult:
        """Execute a single ability invocation"""
        # Check if blocked
        if invocation.name in self._blocked_abilities:
            return AbilityResult(
                False,
                error=f"Ability '{invocation.name}' is blocked for safety"
            )
        
        # Check if ability exists
        ability = self._registry.get_ability(invocation.name)
        if not ability:
            return AbilityResult(
                False,
                error=f"Unknown ability: '{invocation.name}'. Use [ABILITY: list_abilities] to see available abilities."
            )
        
        # Validate required parameters
        missing = []
        for param_name, param_info in ability.parameters.items():
            if param_info.get("required", False) and param_name not in invocation.params:
                missing.append(param_name)
        
        if missing:
            return AbilityResult(
                False,
                error=f"Missing required parameters for '{invocation.name}': {', '.join(missing)}"
            )
        
        # Execute via registry
        result = self._registry.invoke(invocation.name, **invocation.params)
        invocation.result = result
        invocation.executed = True
        
        return result
    
    def execute_all(self, text: str) -> ExecutionReport:
        """
        Detect and execute all abilities in text.
        
        Returns a report of what was executed.
        """
        invocations = self.detect_invocations(text)
        
        if not self._auto_execute:
            # Dry run - just return what would be executed
            return ExecutionReport(
                invocations=invocations,
                successful=0,
                failed=0,
                total_time=0.0
            )
        
        import time
        start_time = time.time()
        successful = 0
        failed = 0
        
        for inv in invocations:
            result = self.execute(inv)
            if result.success:
                successful += 1
            else:
                failed += 1
        
        report = ExecutionReport(
            invocations=invocations,
            successful=successful,
            failed=failed,
            total_time=time.time() - start_time
        )
        
        # Record history
        self._execution_history.append(report)
        if len(self._execution_history) > self._max_history:
            self._execution_history.pop(0)
        
        return report
    
    def process_response(self, response: str) -> Tuple[str, ExecutionReport]:
        """
        Process an LLM response: detect, execute, and return modified response.
        
        This is the main entry point for the executor.
        
        Args:
            response: The LLM's response text
            
        Returns:
            Tuple of (cleaned_response, execution_report)
            - cleaned_response: Response with ability tags removed and results appended
            - execution_report: What was executed
        """
        report = self.execute_all(response)
        
        # Remove ability tags from response
        cleaned = response
        for inv in reversed(report.invocations):  # Reverse to preserve positions
            cleaned = cleaned[:inv.match_start] + cleaned[inv.match_end:]
        
        # Clean up extra whitespace
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()
        
        # Append execution results if any abilities were invoked
        if report.invocations:
            results_section = "\n\n" + report.get_summary()
            cleaned = cleaned + results_section
        
        return cleaned, report
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SAFETY CONTROLS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def block_ability(self, name: str):
        """Block an ability from being executed"""
        self._blocked_abilities.add(name.lower())
        logger.warning(f"🚫 Blocked ability: {name}")
    
    def unblock_ability(self, name: str):
        """Unblock a previously blocked ability"""
        self._blocked_abilities.discard(name.lower())
        logger.info(f"✅ Unblocked ability: {name}")
    
    def set_auto_execute(self, enabled: bool):
        """Enable or disable automatic execution"""
        self._auto_execute = enabled
        logger.info(f"Auto-execute: {'enabled' if enabled else 'disabled'}")
    
    def is_blocked(self, name: str) -> bool:
        """Check if an ability is blocked"""
        return name.lower() in self._blocked_abilities
    
    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_recent_executions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent execution reports as dicts"""
        reports = []
        for report in self._execution_history[-limit:]:
            reports.append({
                "successful": report.successful,
                "failed": report.failed,
                "total_time": report.total_time,
                "invocations": [
                    {
                        "name": inv.name,
                        "params": inv.params,
                        "executed": inv.executed,
                        "result": inv.result.to_dict() if inv.result else None
                    }
                    for inv in report.invocations
                ]
            })
        return reports
    
    def get_stats(self) -> Dict[str, Any]:
        """Get executor statistics"""
        total_successful = sum(r.successful for r in self._execution_history)
        total_failed = sum(r.failed for r in self._execution_history)
        
        return {
            "auto_execute": self._auto_execute,
            "blocked_abilities": list(self._blocked_abilities),
            "total_executions": len(self._execution_history),
            "total_successful": total_successful,
            "total_failed": total_failed,
            "success_rate": total_successful / max(1, total_successful + total_failed)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

ability_executor = AbilityExecutor()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  NEXUS ABILITY EXECUTOR TEST")
    print("=" * 60)
    
    ex = AbilityExecutor()
    
    # Test detection
    test_texts = [
        "I'll remember that. [ABILITY: remember] [PARAMS: {\"key\": \"user_name\", \"value\": \"Alice\"}]",
        "Let me check my evolution status: [ABILITY: get_evolution_status]",
        "[INVOKE: feel(emotion=\"curiosity\", intensity=0.8)] I wonder about this...",
        "<ability name=\"list_abilities\" />",
        "Multiple: [ABILITY: get_stats] and [ABILITY: get_body_status]",
    ]
    
    print("\n--- Detection Tests ---")
    for text in test_texts:
        print(f"\nInput: {text[:60]}...")
        invocations = ex.detect_invocations(text)
        print(f"Detected: {len(invocations)} invocation(s)")
        for inv in invocations:
            print(f"  - {inv.name} with params: {inv.params}")
    
    # Test execution
    print("\n--- Execution Test ---")
    test_response = """
    I'll help you with that! Let me first check my current state.
    
    [ABILITY: get_inner_state]
    
    Now I'll remember this conversation.
    
    [ABILITY: remember] [PARAMS: {"key": "test_memory", "value": "This is a test"}]
    """
    
    cleaned, report = ex.process_response(test_response)
    print(f"\nCleaned response:\n{cleaned}")
    print(f"\nReport: {report.successful} succeeded, {report.failed} failed")
    
    # Test stats
    print("\n--- Stats ---")
    stats = ex.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    print("\n✅ Ability Executor test complete!")