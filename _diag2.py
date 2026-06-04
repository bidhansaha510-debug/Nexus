"""
Diagnostic: capture ALL stdout/stderr to a file, then start brain.
"""
import os, sys, io, traceback, subprocess, time, threading
from pathlib import Path

OUTPUT_FILE = Path(__file__).parent / "_diag2_output.txt"

# Redirect everything to file
class Tee:
    def __init__(self, *targets):
        self.targets = targets
    def write(self, s):
        for t in self.targets:
            try:
                t.write(s)
                t.flush()
            except:
                pass
    def flush(self):
        for t in self.targets:
            try:
                t.flush()
            except:
                pass
    @property
    def encoding(self):
        return 'utf-8'
    @property
    def buffer(self):
        return self.targets[0].buffer if hasattr(self.targets[0], 'buffer') else self.targets[0]

f = open(OUTPUT_FILE, "w", encoding="utf-8", errors="replace")
sys.stdout = Tee(f, sys.__stdout__)
sys.stderr = Tee(f, sys.__stderr__)

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

print("=" * 60)
print("NEXUS STARTUP DIAGNOSTIC")
print("=" * 60)

errors_found = []

# Step 1: Imports
print("\n--- STEP 1: Core Imports ---")
try:
    from config import NEXUS_CONFIG, EmotionType, print_config
    print("  [OK] config")
except Exception as e:
    print(f"  [FAIL] config: {e}")
    traceback.print_exc()
    errors_found.append(f"config: {e}")

try:
    from utils.logger import print_startup_banner, get_logger, log_system
    print("  [OK] logger")
except Exception as e:
    print(f"  [FAIL] logger: {e}")
    traceback.print_exc()
    errors_found.append(f"logger: {e}")

try:
    from core.nexus_brain import NexusBrain, nexus_brain
    print("  [OK] NexusBrain")
except Exception as e:
    print(f"  [FAIL] NexusBrain: {e}")
    traceback.print_exc()
    errors_found.append(f"NexusBrain: {e}")

try:
    from utils.file_processor import file_processor, FileAttachment, get_supported_extensions
    print("  [OK] file_processor")
except Exception as e:
    print(f"  [FAIL] file_processor: {e}")
    traceback.print_exc()
    errors_found.append(f"file_processor: {e}")

# Step 2: Start brain with timeout
print("\n--- STEP 2: brain.start() ---")

start_error = [None]
def do_start():
    try:
        nexus_brain.start()
        print("  [OK] brain.start() completed")
    except Exception as e:
        start_error[0] = e
        print(f"  [FAIL] brain.start(): {e}")
        traceback.print_exc()
        errors_found.append(f"brain.start(): {e}")

t = threading.Thread(target=do_start, daemon=True)
t.start()
t.join(timeout=120)  # 2 min timeout

if t.is_alive():
    print("  [WARN] brain.start() still running after 120s (may hang in background)")
    # Check if brain is at least running
    if hasattr(nexus_brain, 'is_running') and nexus_brain.is_running:
        print("  [OK] brain.is_running = True (startup succeeded despite slow init)")
    else:
        print("  [WARN] brain.is_running = False")

# Step 3: Check module health
print("\n--- STEP 3: Module Health ---")
modules_to_check = [
    ('_emotion_engine', 'Emotion Engine'),
    ('_consciousness', 'Consciousness'),
    ('_monitoring_system', 'Monitoring System'),
    ('_learning_system', 'Learning System'),
    ('_self_improvement_system', 'Self Improvement'),
    ('_cognition_system', 'Cognition System'),
    ('_user_tracker', 'User Tracker'),
    ('_event_bus', 'Event Bus'),
]

for attr, name in modules_to_check:
    if hasattr(nexus_brain, attr):
        val = getattr(nexus_brain, attr)
        if val is None:
            print(f"  [WARN] {name} ({attr}) = None")
        else:
            print(f"  [OK] {name} ({attr}) = {type(val).__name__}")
    else:
        print(f"  [MISS] {name} ({attr}) not found on brain")

# Step 4: Stop
print("\n--- STEP 4: Shutdown ---")
try:
    nexus_brain.stop()
    print("  [OK] brain.stop() completed")
except Exception as e:
    print(f"  [FAIL] brain.stop(): {e}")
    traceback.print_exc()
    errors_found.append(f"brain.stop(): {e}")

# Summary
print("\n" + "=" * 60)
print(f"ERRORS FOUND: {len(errors_found)}")
for e in errors_found:
    print(f"  - {e}")
print("=" * 60)

f.close()
print(f"\nFull output written to: {OUTPUT_FILE}")
sys.exit(len(errors_found))
