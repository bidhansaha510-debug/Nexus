
import unittest
import json
import shutil
from pathlib import Path
import sys

# Ensure the project root is in sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATA_DIR
from cognition.cognitive_flexibility import CognitiveFlexibilityEngine

class TestCognitiveFlexibilityFix(unittest.TestCase):
    def setUp(self):
        self.test_dir = DATA_DIR / "cognition"
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.test_dir / "cognitive_flexibility.json"
        
        # Backup existing file if it exists
        self.backup_file = self.data_file.with_suffix(".test_bak")
        if self.data_file.exists():
            shutil.move(self.data_file, self.backup_file)

    def tearDown(self):
        # Restore backup
        if self.backup_file.exists():
            shutil.move(self.backup_file, self.data_file)
        elif self.data_file.exists():
            self.data_file.unlink()

    def test_empty_file(self):
        """Test that an empty file is handled gracefully."""
        self.data_file.touch()
        engine = CognitiveFlexibilityEngine()
        # Force reload to test _load_data logic
        engine._load_data()
        self.assertEqual(engine._stats["total_perspective_shifts"], 0)

    def test_corrupt_file(self):
        """Test that a corrupt file is handled and backed up."""
        self.data_file.write_text("{invalid json")
        engine = CognitiveFlexibilityEngine()
        engine._load_data()
        
        self.assertEqual(engine._stats["total_perspective_shifts"], 0)
        self.assertTrue(self.data_file.with_suffix(".json.bak").exists())
        self.assertEqual(self.data_file.with_suffix(".json.bak").read_text(), "{invalid json")

if __name__ == "__main__":
    unittest.main()
