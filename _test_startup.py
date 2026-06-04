"""Test startup: import everything, call brain.start(), report any errors."""
import os
import sys
import io
import traceback
import subprocess

# Force UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'
if sys.stdout and sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr and sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    try:
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

# Monkey-patch Popen for UTF-8
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

# Phase 1: Test imports
print("=" * 60)
print("PHASE 1: Testing imports")
print("=" * 60)

import_tests = [
    ("config", "from config import NEXUS_CONFIG, EmotionType, print_config"),
    ("utils.logger", "from utils.logger import print_startup_banner, get_logger, log_system"),
    ("core.nexus_brain", "from core.nexus_brain import NexusBrain, nexus_brain"),
    ("utils.file_processor", "from utils.file_processor import file_processor, FileAttachment, get_supported_extensions"),
    ("llm.llama_interface", "from llm.llama_interface import llm"),
    ("core.pc_control_agent", "from core.pc_control_agent import pc_control_agent"),
    ("cognition", "import cognition"),
    ("consciousness", "import consciousness"),
    ("emotions", "import emotions"),
    ("learning", "import learning"),
    ("memory", "import memory"),
    ("monitoring", "import monitoring"),
    ("personality", "import personality"),
    ("self_improvement", "import self_improvement"),
    ("body", "import body"),
]

for name, stmt in import_tests:
    try:
        exec(stmt)
        print(f"  OK  {name}")
    except Exception as e:
        err_msg = f"FAIL {name}: {type(e).__name__}: {e}"
        print(f"  {err_msg}")
        errors.append(err_msg)
        traceback.print_exc()
        print()

# Phase 2: Test brain.start()
print()
print("=" * 60)
print("PHASE 2: Testing brain.start()")
print("=" * 60)

try:
    from core.nexus_brain import nexus_brain
    nexus_brain.start()
    print("  OK  brain.start() succeeded")
except Exception as e:
    err_msg = f"FAIL brain.start(): {type(e).__name__}: {e}"
    print(f"  {err_msg}")
    errors.append(err_msg)
    traceback.print_exc()

# Phase 3: Test PC control agent
print()
print("=" * 60)
print("PHASE 3: Testing pc_control_agent.start()")
print("=" * 60)

try:
    from core.pc_control_agent import pc_control_agent
    pc_control_agent.start()
    print("  OK  pc_control_agent.start() succeeded")
except Exception as e:
    err_msg = f"FAIL pc_control_agent.start(): {type(e).__name__}: {e}"
    print(f"  {err_msg}")
    errors.append(err_msg)
    traceback.print_exc()

# Summary
print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)
if errors:
    print(f"  {len(errors)} ERROR(S) FOUND:")
    for e in errors:
        print(f"    - {e}")
    sys.exit(1)
else:
    print("  ALL CLEAN - Zero errors!")
    sys.exit(0)
