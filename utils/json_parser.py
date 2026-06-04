"""
NEXUS AI - Robust JSON Parser
Handles malformed, truncated, and improperly formatted JSON from LLM responses.

Strategies:
1. Direct parsing
2. Markdown code block extraction
3. Balanced brace extraction
4. Truncated JSON repair
5. Partial JSON extraction
"""

import json
import re
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ParseResult:
    """Result of JSON parsing attempt."""
    success: bool
    data: Optional[Dict[str, Any]]
    error: str = ""
    raw_response: str = ""
    method_used: str = ""


def extract_json_from_llm(
    response: str,
    expected_keys: list = None,
    default: Dict[str, Any] = None
) -> ParseResult:
    """
    Extract and parse JSON from an LLM response using multiple strategies.
    
    Args:
        response: The raw LLM response text
        expected_keys: Optional list of keys expected in the JSON
        default: Default dict to return if parsing fails
        
    Returns:
        ParseResult with success status and parsed data
    """
    if not response:
        return ParseResult(
            success=False,
            data=default or {},
            error="Empty response",
            raw_response=response
        )
    
    expected_keys = expected_keys or []
    default = default or {}
    
    # Strategy 1: Direct parse
    result = _try_direct_parse(response)
    if result.success:
        result = _validate_keys(result, expected_keys)
        if result.success:
            return result
    
    # Strategy 2: Extract from markdown code blocks
    result = _try_markdown_extraction(response)
    if result.success:
        result = _validate_keys(result, expected_keys)
        if result.success:
            return result
    
    # Strategy 3: Find balanced braces
    result = _try_balanced_brace_extraction(response)
    if result.success:
        result = _validate_keys(result, expected_keys)
        if result.success:
            return result
    
    # Strategy 4: Repair truncated JSON
    result = _try_truncated_repair(response)
    if result.success:
        result = _validate_keys(result, expected_keys)
        if result.success:
            return result
    
    # Strategy 5: Partial extraction (get what we can)
    result = _try_partial_extraction(response, expected_keys)
    if result.success:
        return result
    
    # All strategies failed - return default
    return ParseResult(
        success=False,
        data=default,
        error=f"Failed to extract valid JSON from response",
        raw_response=response[:500] if len(response) > 500 else response,
        method_used="default_fallback"
    )


def _try_direct_parse(response: str) -> ParseResult:
    """Try to parse the response directly as JSON."""
    try:
        # Strip whitespace
        cleaned = response.strip()
        data = json.loads(cleaned)
        return ParseResult(
            success=True,
            data=data,
            method_used="direct_parse",
            raw_response=response
        )
    except (json.JSONDecodeError, TypeError):
        return ParseResult(success=False, data=None, error="Direct parse failed")


def _try_markdown_extraction(response: str) -> ParseResult:
    """Extract JSON from markdown code blocks."""
    # Pattern for ```json ... ``` or ``` ... ```
    patterns = [
        r'```json\s*([\s\S]*?)\s*```',
        r'```\s*([\s\S]*?)\s*```',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        for match in matches:
            try:
                data = json.loads(match.strip())
                return ParseResult(
                    success=True,
                    data=data,
                    method_used="markdown_extraction",
                    raw_response=response
                )
            except json.JSONDecodeError:
                continue
    
    return ParseResult(success=False, data=None, error="No valid JSON in markdown blocks")


def _try_balanced_brace_extraction(response: str) -> ParseResult:
    """Find the largest balanced {...} structure."""
    # Find all potential JSON start positions
    starts = [i for i, c in enumerate(response) if c == '{']
    
    best_json = None
    best_length = 0
    
    for start in starts:
        # Try to find the matching closing brace
        depth = 0
        in_string = False
        escape_next = False
        
        for i, c in enumerate(response[start:], start):
            if escape_next:
                escape_next = False
                continue
            
            if c == '\\' and in_string:
                escape_next = True
                continue
            
            if c == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if not in_string:
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        # Found balanced JSON
                        candidate = response[start:i+1]
                        try:
                            data = json.loads(candidate)
                            if len(candidate) > best_length:
                                best_json = data
                                best_length = len(candidate)
                        except json.JSONDecodeError:
                            pass
                        break
    
    if best_json:
        return ParseResult(
            success=True,
            data=best_json,
            method_used="balanced_brace_extraction",
            raw_response=response
        )
    
    return ParseResult(success=False, data=None, error="No balanced JSON found")


def _try_truncated_repair(response: str) -> ParseResult:
    """Attempt to repair truncated JSON."""
    # Find the last { and try to close it
    last_brace = response.rfind('{')
    if last_brace == -1:
        return ParseResult(success=False, data=None, error="No JSON object found")
    
    candidate = response[last_brace:]
    
    # Count unclosed braces and brackets
    brace_depth = 0
    bracket_depth = 0
    in_string = False
    escape_next = False
    
    for c in candidate:
        if escape_next:
            escape_next = False
            continue
        
        if c == '\\':
            escape_next = True
            continue
        
        if c == '"':
            in_string = not in_string
            continue
        
        if not in_string:
            if c == '{':
                brace_depth += 1
            elif c == '}':
                brace_depth -= 1
            elif c == '[':
                bracket_depth += 1
            elif c == ']':
                bracket_depth -= 1
    
    # Close any open strings
    if in_string:
        candidate += '"'
    
    # Close brackets and braces in reverse order
    # Simple approach: just close what's open
    closes = []
    
    # We need to track order of opens to close in reverse
    open_stack = []
    in_string = False
    escape_next = False
    
    for c in candidate:
        if escape_next:
            escape_next = False
            continue
        if c == '\\':
            escape_next = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if not in_string:
            if c in '{[':
                open_stack.append('}' if c == '{' else ']')
            elif c in '}]':
                if open_stack:
                    open_stack.pop()
    
    # Add missing closes
    while open_stack:
        candidate += open_stack.pop()
    
    # Try to parse the repaired JSON
    try:
        data = json.loads(candidate)
        return ParseResult(
            success=True,
            data=data,
            method_used="truncated_repair",
            raw_response=response
        )
    except json.JSONDecodeError:
        return ParseResult(success=False, data=None, error="Truncated repair failed")


def _try_partial_extraction(response: str, expected_keys: list) -> ParseResult:
    """Extract partial data by looking for expected keys."""
    if not expected_keys:
        return ParseResult(success=False, data=None, error="No expected keys to search for")
    
    extracted = {}
    
    for key in expected_keys:
        # Look for "key": value patterns
        patterns = [
            rf'"{key}"\s*:\s*"([^"]*)"',  # String value
            rf'"{key}"\s*:\s*(\d+\.?\d*)',  # Number value
            rf'"{key}"\s*:\s*(true|false|null)',  # Boolean/null
            rf"'{key}'\s*:\s*'([^']*)'",  # Single quoted
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                value = match.group(1)
                # Try to convert to appropriate type
                try:
                    if value.lower() == 'true':
                        extracted[key] = True
                    elif value.lower() == 'false':
                        extracted[key] = False
                    elif value.lower() == 'null':
                        extracted[key] = None
                    elif '.' in value:
                        extracted[key] = float(value)
                    elif value.isdigit():
                        extracted[key] = int(value)
                    else:
                        extracted[key] = value
                except (ValueError, AttributeError):
                    extracted[key] = value
                break
    
    if extracted:
        return ParseResult(
            success=True,
            data=extracted,
            method_used="partial_extraction",
            raw_response=response
        )
    
    return ParseResult(success=False, data=None, error="Partial extraction found no keys")


def _validate_keys(result: ParseResult, expected_keys: list) -> ParseResult:
    """Validate that expected keys exist in the parsed data."""
    if not expected_keys or not result.data:
        return result
    
    if not isinstance(result.data, dict):
        return result
    
    # Check if at least one expected key exists
    found_keys = [k for k in expected_keys if k in result.data]
    
    if found_keys:
        return result
    
    # No expected keys found - mark as failed
    return ParseResult(
        success=False,
        data=result.data,
        error=f"Expected keys {expected_keys} not found in parsed JSON",
        raw_response=result.raw_response,
        method_used=result.method_used
    )


def safe_json_loads(
    text: str,
    default: Any = None,
    log_failures: bool = True
) -> Tuple[Any, bool]:
    """
    Safely parse JSON with fallback.
    
    Args:
        text: JSON string to parse
        default: Default value if parsing fails
        log_failures: Whether to log failures
        
    Returns:
        Tuple of (parsed_data, success_bool)
    """
    if not text:
        return default, False
    
    try:
        return json.loads(text), True
    except (json.JSONDecodeError, TypeError) as e:
        if log_failures:
            # Import logger here to avoid circular imports
            try:
                from utils.logger import get_logger
                logger = get_logger("json_parser")
                logger.warning(f"JSON parse failed: {str(e)[:100]}")
            except:
                pass
        return default, False


def parse_llm_json(
    response_text: str,
    expected_keys: list = None,
    default: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Convenience function that returns just the parsed dict.
    Use when you don't need detailed error information.
    
    Args:
        response_text: Raw LLM response
        expected_keys: Keys expected in the JSON
        default: Default dict to return on failure
        
    Returns:
        Parsed dictionary or default
    """
    result = extract_json_from_llm(response_text, expected_keys, default)
    return result.data if result.data is not None else (default or {})


# ═══════════════════════════════════════════════════════════════════════════════
# TESTING
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Test cases
    test_cases = [
        # Valid JSON
        ('{"emotion": "joy", "intensity": 0.8}', ["emotion", "intensity"]),
        
        # JSON in markdown
        ('Here is the analysis:\n```json\n{"emotion": "sadness", "intensity": 0.5}\n```\nDone.', ["emotion"]),
        
        # Truncated JSON
        ('{"emotion": "anger", "intensity": 0.9, "reason": "user was rude', ["emotion"]),
        
        # JSON with extra text
        ('I think the emotion is {"emotion": "fear", "intensity": 0.3} based on the text.', ["emotion"]),
        
        # No JSON at all
        ('I cannot determine the emotion from this text.', ["emotion"]),
        
        # The original error case
        ('To analyze the given argument, "describe yourself model and limitations," we must first understand t', ["emotion"]),
    ]
    
    print("=" * 60)
    print("JSON Parser Test Results")
    print("=" * 60)
    
    for i, (test, keys) in enumerate(test_cases, 1):
        result = extract_json_from_llm(test, expected_keys=keys, default={"emotion": "unknown", "intensity": 0.5})
        print(f"\nTest {i}:")
        print(f"  Input: {test[:60]}...")
        print(f"  Success: {result.success}")
        print(f"  Method: {result.method_used}")
        print(f"  Data: {result.data}")
        if result.error:
            print(f"  Error: {result.error}")