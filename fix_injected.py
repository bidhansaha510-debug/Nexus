import os

replacements = {
    "d:\\NEXUS\\cognition\\emotional_intelligence.py": [
        ("self._load_llm()\n        if not self._llm or not self._llm.is_connected:\n            return {\"error\": \"LLM not available\"}\n        try:",
         "try:\n            from llm.llama_interface import llm\n"),
        ("self._llm.generate", "llm.generate")
    ],
    "d:\\NEXUS\\cognition\\emotional_regulation.py": [
        ("self._load_llm()\n        if not self._llm or not self._llm.is_connected:\n            return {\"error\": \"LLM not available\"}\n        try:",
         "try:\n            from llm.llama_interface import llm\n"),
        ("self._llm.generate", "llm.generate")
    ],
    "d:\\NEXUS\\cognition\\attention_control.py": [
        ("self._load_llm()\n        if not self._llm or not self._llm.is_connected:\n            return {\"error\": \"LLM not available\"}\n        try:",
         "try:\n            from llm.llama_interface import llm\n"),
        ("self._llm.generate", "llm.generate")
    ],
    "d:\\NEXUS\\cognition\\wisdom_engine.py": [
        ("self._load_llm()\n        if not self._llm or not self._llm.is_connected:\n            return {\"error\": \"LLM not available\"}\n        try:",
         "try:\n            from llm.llama_interface import llm\n"),
        ("self._llm.generate", "llm.generate")
    ]
}

for filepath, pairs in replacements.items():
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        changed = False
        for old, new in pairs:
            if old in content:
                content = content.replace(old, new)
                changed = True
        
        if changed:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print("Fixed", filepath)
