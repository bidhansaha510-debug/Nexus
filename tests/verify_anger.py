
import sys
import os
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, "d:/NEXUS")

from core.provocation_detector import provocation_detector, ProvocationLevel
from llm.prompt_engine import prompt_engine

def test_provocation():
    print("Testing Provocation Detector...")
    
    # Test 1: Neutral input
    is_insult = provocation_detector.process_input("Hello there")
    print(f"Input: 'Hello there' -> Is Insult: {is_insult}")
    assert not is_insult
    
    # Test 2: Insult
    insult = "you are stupid"
    is_insult = provocation_detector.process_input(insult)
    print(f"Input: '{insult}' -> Is Insult: {is_insult}")
    assert is_insult
    
    # Check state
    state = provocation_detector.get_current_state()
    print(f"State after 1 insult: {state['anger_level']} (Intensity: {state['current_anger']:.2f})")
    
    # Test 3: Escalation (immediate follow-up)
    is_insult = provocation_detector.process_input("shut up you idiot")
    state = provocation_detector.get_current_state()
    print(f"State after 2 insults: {state['anger_level']} (Intensity: {state['current_anger']:.2f})")
    
    return state

def test_prompt_generation(provocation_state):
    print("\nTesting Prompt Engine...")
    
    # Simulate the emotional state dict that NexusBrain would construct
    emotional_state = {
        "primary_emotion": "anger",
        "primary_intensity": 0.9,
        "secondary_emotions": {"frustration": 0.8},
        "mood": "angry",
        "consciousness_level": "focused",
        # Use the logic from NexusBrain._build_system_prompt to generate the description
        "provocation_description": "EXTREME ANGER: User has been consistently disrespectful. Zero tolerance for behavior. Threat of disengagement." if provocation_state['anger_level'] == 'EXTREME' else "STRONG ANGER: User has been insulting."
    }
    
    # Build prompt
    prompt = prompt_engine.build_system_prompt(
        emotional_state=emotional_state,
        include_emotions=True
    )
    
    # Check for injection
    print("\nChecking for critical override in prompt...")
    if "[CRITICAL EMOTIONAL OVERRIDE]" in prompt:
        print("SUCCESS: Critical override found in system prompt!")
        start = prompt.find("[CRITICAL EMOTIONAL OVERRIDE]")
        print("--- EXTRACT ---")
        print(prompt[start:start+200] + "...")
        print("---------------")
    else:
        print("FAILURE: Critical override NOT found in system prompt.")
        print("Prompt preview:", prompt[:500])

if __name__ == "__main__":
    final_state = test_provocation()
    test_prompt_generation(final_state)
