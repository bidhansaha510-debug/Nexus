import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# Use actual config definitions
from config import EmotionType, NEXUS_CONFIG
import config

test_log_dir = Path(__file__).parent / "test_logs"
test_log_dir.mkdir(exist_ok=True)
config.LOG_DIR = test_log_dir
config.BASE_DIR = PROJECT_ROOT
NEXUS_CONFIG.log_level = 'INFO'

from emotions.emotion_engine import EmotionEngine

class TestEmotionValence(unittest.TestCase):
    def test_anger_impact(self):
        engine = EmotionEngine()
        
        # 1. Neutral State check (mocked startup)
        engine._active_emotions.clear()
        print(f"Base Valence: {engine.get_valence()}")
        
        # 2. Add Happiness (Positive)
        # We manually inject because affect() triggers complex logic
        # But let's try calling affect() since we mocked active_emotions? No, we need to populate self._active_emotions
        
        # Manually trigger affect logic (simplified)
        print("Injecting Joy (0.8)")
        engine.feel(EmotionType.JOY, 0.8, "Test Joy")
        val_happy = engine.get_valence()
        print(f"Valence (Joy 0.8): {val_happy:.2f}")
        # Logic: (1.0 * 0.8) / 0.8 = 1.0 (clamped?)
        self.assertGreater(val_happy, 0.5)
        
        # 3. Add Anger (Conflict)
        print("Injecting Anger (0.4)")
        engine.feel(EmotionType.ANGER, 0.4, "Test Anger")
        val_conflict = engine.get_valence()
        print(f"Valence (Joy 0.8 + Anger 0.4): {val_conflict:.2f}")
        
        # Expected: 
        # Weighted Valence: (Joy(0.8)*1.0 + Anger(0.4)*-0.8*2(penalty)) / (0.8 + 0.4*2)
        # = (0.8 - 0.64) / (1.6) = 0.16 / 1.6 = 0.1
        # Hard cap: Anger > 0.3 (0.4) -> max_allowed = 0.4 - 0.4 = 0.0
        # Final valence should be min(0.1, 0.0) = 0.0
        
        self.assertLessEqual(val_conflict, 0.1)
        
        # 4. High Anger
        print("Injecting Anger (0.8)")
        engine.feel(EmotionType.ANGER, 0.8, "Rage")
        val_rage = engine.get_valence()
        print(f"Valence (Joy 0.8 + Anger 0.8): {val_rage:.2f}")
        
        # Hard cap: Anger > 0.3 (0.8) -> max_allowed = 0.4 - 0.8 = -0.4
        self.assertLessEqual(val_rage, -0.2)
        print("Test Passed: Valence capped correctly.")

if __name__ == "__main__":
    unittest.main()
