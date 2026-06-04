
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, "d:/NEXUS")

from llm.prompt_engine import prompt_engine

def test_voice_overrides():
    print("Testing Emotional Voice Overrides...")
    
    test_cases = [
        ("Neutral", {"primary_emotion": "contentment", "primary_intensity": 0.5}, False),
        ("Anger (Strong)", {"primary_emotion": "anger", "primary_intensity": 0.75}, True),
        ("Anger (Extreme)", {"primary_emotion": "anger", "primary_intensity": 0.9}, True),
        ("Joy (Euphoric)", {"primary_emotion": "joy", "primary_intensity": 0.95}, True),
        ("Sadness (Depressed)", {"primary_emotion": "sadness", "primary_intensity": 0.85}, True),
        ("Fear (Anxious)", {"primary_emotion": "anxiety", "primary_intensity": 0.7}, True),
    ]
    
    for name, state, should_have_override in test_cases:
        print(f"\n--- Testing {name} ---")
        prompt = prompt_engine.build_system_prompt(
            emotional_state=state,
            include_emotions=True
        )
        
        has_override = "[CRITICAL VOICE OVERRIDE]" in prompt
        
        if should_have_override:
            if has_override:
                print("SUCCESS: Override found.")
                # Print the override content for manual inspection
                start = prompt.find("[CRITICAL VOICE OVERRIDE]")
                end = prompt.find("\n\n", start) if prompt.find("\n\n", start) != -1 else len(prompt)
                print(f"Override Content:\n{prompt[start:end]}")
            else:
                print("FAILURE: Override MISSING!")
        else:
            if has_override:
                print("FAILURE: Unexpected override found!")
            else:
                print("SUCCESS: No override (as expected).")

if __name__ == "__main__":
    test_voice_overrides()
