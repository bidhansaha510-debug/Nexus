"""
Diagnostic script: tries to start NEXUS and captures ALL errors.
"""
import os, sys, io, traceback, subprocess

# Force UTF-8
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

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

# Patch subprocess
_original_popen_init = subprocess.Popen.__init__
def _utf8_popen_init(self, *args, **kwargs):
    text_mode = kwargs.get('text') or kwargs.get('universal_newlines')
    if text_mode:
        kwargs.setdefault('encoding', 'utf-8')
        kwargs.setdefault('errors', 'replace')
    _original_popen_init(self, *args, **kwargs)
subprocess.Popen.__init__ = _utf8_popen_init

# Fix six/pynput
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

# Step 1: Import config
print("=" * 60)
print("STEP 1: Import config")
try:
    from config import NEXUS_CONFIG, EmotionType, print_config
    print("  OK: config imported")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()
    errors.append(("config import", str(e)))

# Step 2: Import logger
print("\nSTEP 2: Import logger")
try:
    from utils.logger import print_startup_banner, get_logger, log_system
    logger = get_logger("diag")
    print("  OK: logger imported")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()
    errors.append(("logger import", str(e)))

# Step 3: Import NexusBrain
print("\nSTEP 3: Import NexusBrain")
try:
    from core.nexus_brain import NexusBrain, nexus_brain
    print("  OK: NexusBrain imported")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()
    errors.append(("NexusBrain import", str(e)))

# Step 4: Import file_processor
print("\nSTEP 4: Import file_processor")
try:
    from utils.file_processor import file_processor, FileAttachment, get_supported_extensions
    print("  OK: file_processor imported")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()
    errors.append(("file_processor import", str(e)))

# Step 5: Try brain.start()
print("\nSTEP 5: brain.start()")
try:
    nexus_brain.start()
    print("  OK: brain started")
except Exception as e:
    print(f"  FAIL: {e}")
    traceback.print_exc()
    errors.append(("brain.start()", str(e)))

# Summary
print("\n" + "=" * 60)
print(f"TOTAL ERRORS: {len(errors)}")
for label, msg in errors:
    print(f"  [{label}] {msg}")
print("=" * 60)

# Exit cleanly
try:
    nexus_brain.stop()
except:
    pass
sys.exit(len(errors))
