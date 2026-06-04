"""Tests for autonomous action parsing and execution helpers."""

from pathlib import Path
import py_compile

import pytest

from core.nexus_brain import NexusBrain
from utils.json_parser import parse_llm_json


@pytest.fixture
def brain_shell():
    """Create a NexusBrain shell without running a second full initialization."""
    return NexusBrain.__new__(NexusBrain)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Search the web for quantum computing", "search_web"),
        ("Research how AI learns", "research_topic"),
        ("Browse Wikipedia for info", "browse_url"),
        ("Check CPU and system status", "explore_system"),
        ("Evolve and improve my capabilities", "evolve_self"),
        ("Post a thought on social media", "post_social"),
        ("Contemplate the meaning of life", ""),
        ("", ""),
    ],
)
def test_infer_action_from_text(brain_shell, text, expected):
    assert brain_shell._infer_action_from_text(text) == expected


@pytest.mark.parametrize(
    ("alias", "canonical"),
    [
        ("web_search", "search_web"),
        ("browse", "browse_url"),
        ("research", "research_topic"),
        ("think", "think_deeper"),
        ("search_web", "search_web"),
        ("reflect", "think_deeper"),
        ("upgrade", "evolve_self"),
    ],
)
def test_action_aliases(alias, canonical):
    assert NexusBrain._ACTION_ALIASES.get(alias, alias) == canonical


def test_parse_llm_json_for_decision_payload():
    result = parse_llm_json(
        (
            '{"decision": "search for AI news", "action": "web_search", '
            '"reasoning": "curious", "confidence": 0.8}'
        ),
        expected_keys=["decision"],
    )

    assert result["decision"] == "search for AI news"


def test_nexus_brain_syntax_is_valid():
    py_compile.compile(str(Path("core") / "nexus_brain.py"), doraise=True)
