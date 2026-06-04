"""
Clean diagnostics - suppress progress bars, capture only errors.
"""
import sys
import io
import os
import subprocess
import traceback
import warnings
import logging

# Suppress ALL progress bars and warnings
os.environ["TQDM_DISABLE"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore")

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

# Suppress tqdm globally
try:
    import tqdm
    tqdm.tqdm.__init__.__defaults__ = tuple(
        True if i == 7 else v  # disable=True
        for i, v in enumerate(tqdm.tqdm.__init__.__defaults__ or [])
    )
except:
    pass

# Suppress logging below ERROR
logging.basicConfig(level=logging.ERROR)
for handler in logging.root.handlers:
    handler.setLevel(logging.ERROR)

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

def test_import(module_name, label=None):
    label = label or module_name
    try:
        # Suppress all logging during import
        logging.disable(logging.CRITICAL)
        mod = __import__(module_name, fromlist=[''])
        logging.disable(logging.NOTSET)
        print(f"  [OK]   {label}")
        return mod
    except Exception as e:
        logging.disable(logging.NOTSET)
        msg = f"{label}: {type(e).__name__}: {e}"
        print(f"  [FAIL] {msg}")
        tb = traceback.format_exc()
        # Only show last few lines of traceback
        tb_lines = tb.strip().split('\n')
        relevant = tb_lines[-5:] if len(tb_lines) > 5 else tb_lines
        for line in relevant:
            print(f"         {line}")
        errors.append(msg)
        return None

print("=" * 70)
print("NEXUS STARTUP DIAGNOSTICS (clean)")
print("=" * 70)

# 1. Core imports from main.py
print("\n--- Phase 1: Core Imports ---")
test_import("config")
test_import("utils.logger")
test_import("core.nexus_brain")
test_import("utils.file_processor")

# 2. LLM modules
print("\n--- Phase 2: LLM ---")
test_import("llm")
test_import("llm.llama_interface")
test_import("llm.groq_interface")
test_import("llm.context_manager")
test_import("llm.prompt_engine")
test_import("llm.llm_router")

# 3. Core modules
print("\n--- Phase 3: Core ---")
core_modules = [
    "core.event_bus", "core.state_manager", "core.memory_system",
    "core.context_aggregator", "core.context_assembler",
    "core.tool_executor", "core.user_context", "core.user_manager",
    "core.chat_session_manager", "core.companion_chat",
    "core.pc_control_agent", "core.voice_engine",
    "core.internet_agent", "core.perception_hub",
    "core.multi_persona", "core.multi_agent_mind",
    "core.groq_context_collector", "core.ollama_context_collector",
    "core.ability_registry", "core.ability_executor",
    "core.action_memory", "core.provocation_detector",
    "core.value_alignment", "core.neural_integration",
]
for m in core_modules:
    test_import(m)

# 4. Subsystems
print("\n--- Phase 4: Subsystems ---")
test_import("emotions")
test_import("personality")
test_import("memory")
test_import("cognition")
test_import("consciousness")
test_import("monitoring")
test_import("learning")
test_import("self_improvement")

# 5. Utils
print("\n--- Phase 5: Utils ---")
test_import("utils.resilience")
test_import("utils.metrics")
test_import("utils.json_parser")
test_import("utils.json_utils")

# 6. Brain start
print("\n--- Phase 6: Brain start() ---")
try:
    logging.disable(logging.CRITICAL)
    from core.nexus_brain import nexus_brain
    nexus_brain.start()
    logging.disable(logging.NOTSET)
    print("  [OK]   nexus_brain.start()")
except Exception as e:
    logging.disable(logging.NOTSET)
    msg = f"nexus_brain.start(): {type(e).__name__}: {e}"
    print(f"  [FAIL] {msg}")
    tb = traceback.format_exc()
    tb_lines = tb.strip().split('\n')
    relevant = tb_lines[-10:] if len(tb_lines) > 10 else tb_lines
    for line in relevant:
        print(f"         {line}")
    errors.append(msg)

# Summary
print("\n" + "=" * 70)
if errors:
    print(f"TOTAL ERRORS: {len(errors)}")
    for i, e in enumerate(errors, 1):
        print(f"  {i}. {e}")
else:
    print("ALL CLEAR - No errors found!")
print("=" * 70)

# Cleanup
try:
    nexus_brain.stop()
except:
    pass

sys.exit(len(errors))
