import os

files = [
    r"d:\NEXUS\cognition\attention_control.py",
    r"d:\NEXUS\cognition\wisdom_engine.py",
    r"d:\NEXUS\cognition\emotional_intelligence.py",
    r"d:\NEXUS\cognition\decision_theory.py"
]

SAFE_PARSE = """
    @staticmethod
    def _safe_parse_json(text: str) -> dict:
        import json
        if not text or not text.strip(): return {}
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\\n", 1)[-1] if "\\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            try: return json.loads(cleaned[start:end + 1])
            except Exception: pass
        try: return json.loads(cleaned)
        except Exception: return {}
"""

for fn in files:
    with open(fn, 'r', encoding='utf-8') as f:
        content = f.read()

    if "def _safe_parse_json" not in content:
        content = content.replace("    def start(self):", SAFE_PARSE + "\n    def start(self):", 1)
        
    old_code = 'json.loads(response.text.strip().strip("```json").strip("```"))'
    new_code = 'self._safe_parse_json(response.text)'
    content = content.replace(old_code, new_code)
    
    content = content.replace('self._parse_json(response.text)', 'self._safe_parse_json(response.text)')
    
    with open(fn, 'w', encoding='utf-8') as f:
        f.write(content)

print("Fixed JSON parsers")
