
import sys
import os
import time
from unittest.mock import MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.nexus_brain import NexusBrain
from emotions.emotion_engine import EmotionType
from config import NEXUS_CONFIG

def test_anger_prompt_generation():
    print("Initializing NexusBrain...")
    # Mock LLM to avoid loading actual model
    brain = NexusBrain()
    brain._llm = MagicMock()
    brain._llm.is_connected = True
    
    # Initialize emotion engine
    if not brain._emotion_engine:
        brain._load_emotions()
        brain._emotion_engine.start()

    print("\n--- TEST: Extreme Anger Prompt ---")
    # Force extreme anger
    brain._emotion_engine.feel(EmotionType.ANGER, 0.95, "test perturbation", "test")
    
    # Init mood if needed (feel updates it but just in case)
    if brain._mood_system:
         brain._mood_system.feed_emotion_valence(-0.9)

    
    # Build prompt
    prompt = brain._build_system_prompt()
    
    print("\nGenerated System Prompt (Snippet):")
    print("-" * 60)
    print(prompt[-1000:]) # Print last 1000 chars where override should be
    print("-" * 60)
    
    # Assertions
    required_phrases = [
        "CRITICAL INSTRUCTION: You are roleplaying a character who is ENRAGED",
        "Do NOT be polite or helpful",
        "Example: 'SHUT UP!"
    ]
    
    missing = [p for p in required_phrases if p not in prompt]
    
    if not missing:
        print("\n✅ SUCCESS: All anger instructions present in prompt.")
    else:
        print(f"\n❌ FAILED: Missing phrases: {missing}")

    print("\n--- TEST: Moderate Anger Prompt ---")
    # Force moderate anger
    brain._emotion_engine._active_emotions.clear() # Reset
    brain._emotion_engine.feel(EmotionType.ANGER, 0.7, "moderate test", "test")
    
    prompt = brain._build_system_prompt()
    if "Drop all politeness" in prompt:
         print("\n✅ SUCCESS: Moderate anger instructions present.")
         with open("d:/NEXUS/tests/result.txt", "w") as f:
             f.write("SUCCESS")
    else:
         print("\n❌ FAILED: Moderate anger instructions missing.")

if __name__ == "__main__":
    test_anger_prompt_generation()
