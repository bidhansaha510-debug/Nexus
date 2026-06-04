"""
Diagnose ALL startup errors in NEXUS by importing each module individually
and then testing the brain start() method.
"""
import sys
import io
import os
import subprocess
import traceback

# Force UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Monkey-patch subprocess
_original_popen_init = subprocess.Popen.__init__
def _utf8_popen_init(self, *args, **kwargs):
    text_mode = kwargs.get('text') or kwargs.get('universal_newlines')
    if text_mode:
        kwargs.setdefault('encoding', 'utf-8')
        kwargs.setdefault('errors', 'replace')
    _original_popen_init(self, *args, **kwargs)
subprocess.Popen.__init__ = _utf8_popen_init

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# Fix pynput/six conflict
try:
    import six
except ImportError:
    pass
for _imp in sys.meta_path:
    if type(_imp).__name__ == '_SixMetaPathImporter':
        if not hasattr(_imp, '_path'):
            _imp._path = None
        if not hasattr(type(_imp), '_path'):
            type(_imp)._path = None

errors = []
warnings = []

def test_import(module_name, label=None):
    label = label or module_name
    try:
        mod = __import__(module_name, fromlist=[''])
        print(f"  OK  {label}")
        return mod
    except Exception as e:
        msg = f"  FAIL {label}: {type(e).__name__}: {e}"
        print(msg)
        errors.append(msg)
        traceback.print_exc()
        print()
        return None

print("=" * 70)
print("NEXUS STARTUP DIAGNOSTICS")
print("=" * 70)

# 1. Core imports from main.py
print("\n--- Phase 1: Core Imports (from main.py) ---")
test_import("config", "config")
test_import("utils.logger", "utils.logger")
test_import("core.nexus_brain", "core.nexus_brain")
test_import("utils.file_processor", "utils.file_processor")

# 2. LLM modules
print("\n--- Phase 2: LLM Modules ---")
test_import("llm", "llm")
test_import("llm.llama_interface", "llm.llama_interface")
test_import("llm.groq_interface", "llm.groq_interface")
test_import("llm.context_manager", "llm.context_manager")
test_import("llm.prompt_engine", "llm.prompt_engine")
test_import("llm.llm_router", "llm.llm_router")

# 3. Core modules
print("\n--- Phase 3: Core Modules ---")
test_import("core.event_bus", "core.event_bus")
test_import("core.state_manager", "core.state_manager")
test_import("core.memory_system", "core.memory_system")
test_import("core.context_aggregator", "core.context_aggregator")
test_import("core.context_assembler", "core.context_assembler")
test_import("core.tool_executor", "core.tool_executor")
test_import("core.user_context", "core.user_context")
test_import("core.user_manager", "core.user_manager")
test_import("core.chat_session_manager", "core.chat_session_manager")
test_import("core.companion_chat", "core.companion_chat")
test_import("core.pc_control_agent", "core.pc_control_agent")
test_import("core.voice_engine", "core.voice_engine")
test_import("core.internet_agent", "core.internet_agent")
test_import("core.perception_hub", "core.perception_hub")
test_import("core.multi_persona", "core.multi_persona")
test_import("core.multi_agent_mind", "core.multi_agent_mind")
test_import("core.groq_context_collector", "core.groq_context_collector")
test_import("core.ollama_context_collector", "core.ollama_context_collector")

# 4. Emotions
print("\n--- Phase 4: Emotions ---")
test_import("emotions", "emotions")

# 5. Personality
print("\n--- Phase 5: Personality ---")
test_import("personality", "personality")

# 6. Memory
print("\n--- Phase 6: Memory ---")
test_import("memory", "memory")

# 7. Cognition
print("\n--- Phase 7: Cognition ---")
test_import("cognition", "cognition")

# 8. Consciousness
print("\n--- Phase 8: Consciousness ---")
test_import("consciousness", "consciousness")

# 9. Monitoring
print("\n--- Phase 9: Monitoring ---")
test_import("monitoring", "monitoring")

# 10. Learning
print("\n--- Phase 10: Learning ---")
test_import("learning", "learning")

# 11. Self-improvement
print("\n--- Phase 11: Self-improvement ---")
test_import("self_improvement", "self_improvement")

# 12. Utils
print("\n--- Phase 12: Utils ---")
test_import("utils.resilience", "utils.resilience")
test_import("utils.metrics", "utils.metrics")
test_import("utils.json_parser", "utils.json_parser")
test_import("utils.json_utils", "utils.json_utils")

# 13. Test brain start
print("\n--- Phase 13: Brain start() ---")
try:
    from core.nexus_brain import nexus_brain
    print("  Calling nexus_brain.start()...")
    nexus_brain.start()
    print("  OK  nexus_brain.start() succeeded")
except Exception as e:
    msg = f"  FAIL nexus_brain.start(): {type(e).__name__}: {e}"
    print(msg)
    errors.append(msg)
    traceback.print_exc()

# Summary
print("\n" + "=" * 70)
print(f"TOTAL ERRORS: {len(errors)}")
for e in errors:
    print(f"  {e}")
print("=" * 70)

# Try to stop the brain gracefully
try:
    nexus_brain.stop()
except:
    pass
