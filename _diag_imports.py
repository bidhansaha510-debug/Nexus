"""Minimal diagnostics - just imports, no brain.start()"""
import sys, io, os, subprocess, traceback, warnings, logging

os.environ["TQDM_DISABLE"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

_orig = subprocess.Popen.__init__
def _p(self, *a, **k):
    if k.get('text') or k.get('universal_newlines'):
        k.setdefault('encoding', 'utf-8'); k.setdefault('errors', 'replace')
    _orig(self, *a, **k)
subprocess.Popen.__init__ = _p

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
try:
    import six
except ImportError: pass
for _imp in sys.meta_path:
    if type(_imp).__name__ == '_SixMetaPathImporter':
        if not hasattr(_imp, '_path'): _imp._path = None
        if not hasattr(type(_imp), '_path'): type(_imp)._path = None

errors = []
def test(mod, label=None):
    label = label or mod
    try:
        __import__(mod, fromlist=[''])
        print(f"OK   {label}")
        return True
    except Exception as e:
        msg = f"FAIL {label}: {type(e).__name__}: {e}"
        print(msg)
        errors.append(msg)
        # Show just last 3 lines of traceback
        for line in traceback.format_exc().strip().split('\n')[-3:]:
            print(f"     {line}")
        return False

modules = [
    "config", "utils.logger", "utils.file_processor", "utils.resilience",
    "utils.metrics", "utils.json_parser", "utils.json_utils",
    "llm", "llm.llama_interface", "llm.groq_interface",
    "llm.context_manager", "llm.prompt_engine", "llm.llm_router",
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
    "core.nexus_brain",
    "emotions", "personality", "memory",
    "cognition", "consciousness", "monitoring",
    "learning", "self_improvement",
]

print("=" * 60)
print("IMPORT TEST")
print("=" * 60)
for m in modules:
    test(m)

print(f"\n{'=' * 60}")
print(f"ERRORS: {len(errors)}")
for e in errors:
    print(f"  {e}")
print(f"{'=' * 60}")
