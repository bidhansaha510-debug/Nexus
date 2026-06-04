
import sys
import time
from typing import Dict, Any

# Mock for EventBus to avoid actual publishing
class MockEventBus:
    def publish(self, event_type, data, source):
        print(f"[EVENT] {event_type} from {source}: {data}")

# Add project root to path
sys.path.insert(0, "d:/NEXUS")

# Mock the publish function in event_bus module before importing detector
import core.event_bus
core.event_bus.publish = MockEventBus().publish

from core.provocation_detector import provocation_detector

def test_persistence_and_apology():
    print("Testing Emotional Persistence & Apology...")
    
    # 1. Trigger High Anger
    print("\n--- Phase 1: Escalation ---")
    provocation_detector.process_input("you are stupid")
    provocation_detector.process_input("you are useless")
    
    state = provocation_detector.get_current_state()
    anger_initial = state['current_anger']
    print(f"Initial Anger: {anger_initial:.2f}")
    
    if anger_initial < 0.6:
        print("FAILURE: Anger not high enough for test.")
        return

    # 2. Simulate Time Passage (Decay Check)
    print("\n--- Phase 2: Persistence Check ---")
    # Manually trigger the decay logic a few times
    print("Simulating passage of time (calling decrease_anger)...")
    provocation_detector._decrease_anger() 
    provocation_detector._decrease_anger()
    
    state = provocation_detector.get_current_state()
    anger_after_time = state['current_anger']
    print(f"Anger after simulation: {anger_after_time:.2f}")
    
    if anger_after_time >= anger_initial - 0.05:
        print("SUCCESS: Anger persisted (decay was negligible).")
    else:
        print(f"FAILURE: Anger decayed significantly! (-{anger_initial - anger_after_time:.2f})")

    # 3. Test Apology
    print("\n--- Phase 3: Apology ---")
    apology = "I am so sorry, I didn't mean it."
    print(f"User says: '{apology}'")
    provocation_detector.process_input(apology)
    
    state = provocation_detector.get_current_state()
    anger_after_apology = state['current_anger']
    print(f"Anger after apology: {anger_after_apology:.2f}")
    
    if anger_after_apology < anger_after_time:
        print("SUCCESS: Apology reduced anger.")
        if anger_after_apology < 0.3:
            print("SUCCESS: Anger reduced significantly.")
    else:
         print("FAILURE: Apology did NOT reduce anger.")

if __name__ == "__main__":
    test_persistence_and_apology()
