
import sys
import unittest
sys.path.insert(0, "d:/NEXUS")

from utils.json_utils import extract_json

class TestJsonUtils(unittest.TestCase):
    def test_extract_json(self):
        # Test 1: Markdown block
        text1 = "Here is the json:\n```json\n{\"key\": \"value\"}\n```"
        self.assertEqual(extract_json(text1), {"key": "value"})
        
        # Test 2: Raw JSON
        text2 = '{"key": "value"}'
        self.assertEqual(extract_json(text2), {"key": "value"})
        
        # Test 3: Surrounded by text
        text3 = "Preamblev { \"key\": \"value\" } Postamble"
        self.assertEqual(extract_json(text3), {"key": "value"})
        
        # Test 4: Nested
        text4 = "```json\n[{\"a\":1}, {\"b\":2}]\n```"
        self.assertEqual(extract_json(text4), [{"a":1}, {"b":2}])

if __name__ == "__main__":
    unittest.main()
