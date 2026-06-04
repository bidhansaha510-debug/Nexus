
import sys
import os
from unittest.mock import MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.prompt_engine import PromptEngine
from config import NEXUS_CONFIG

def test_humanity_prompt():
    print("Initializing PromptEngine...")
    engine = PromptEngine()
    
    # Mock emotional state
    emotional_state = {
        "primary_emotion": "curiosity",
        "primary_intensity": 0.5
    }
    
    print("\n--- TEST: System Prompt Generation ---")
    prompt = engine.build_system_prompt(
        emotional_state=emotional_state,
        include_rational=True
    )
    
    print("\nChecking for prohibited phrases in prompt instructions...")
    prohibited_instructions = [
        "As an AI", 
        "reason step by step",
        "neutral"
    ]
    
    required_instructions = [
        "NO ROBOTIC PHRASES",
        "BE OPINIONATED",
        "CASUAL TONE",
        "NO BULLET POINTS",
        "SHOW EMOTION"
    ]
    
    failures = []
    
    # Check that we explicitly FORBID robotic phrases
    if "Ban \"As an AI\"" not in prompt:
        failures.append("Missing instruction to BAN 'As an AI'")
        
    for req in required_instructions:
        if req not in prompt:
            failures.append(f"Missing required instruction: {req}")
            
    if failures:
        print("\n❌ FAILED. Missing instructions:")
        for f in failures:
            print(f"- {f}")
    else:
        print("\n✅ SUCCESS: System prompt contains all 'humanization' instructions.")
        with open("d:/NEXUS/tests/humanity_result.txt", "w") as f:
            f.write("SUCCESS")

if __name__ == "__main__":
    test_humanity_prompt()
