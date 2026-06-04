"""Test brain.start() and capture runtime errors"""
import sys, io, os, subprocess, traceback, warnings, logging, threading, time

os.environ["TQDM_DISABLE"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

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

# Set up logging to only capture errors
class ErrorCollector(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.ERROR)
        self.errors = []
    def emit(self, record):
        msg = self.format(record)
        self.errors.append(msg)
        # Also print to stdout immediately
        print(f"[CAPTURED ERROR] {record.name}: {record.getMessage()[:200]}")

collector = ErrorCollector()
collector.setFormatter(logging.Formatter('%(name)s: %(message)s'))

# Add to root logger
root_logger = logging.getLogger()
root_logger.addHandler(collector)
root_logger.setLevel(logging.DEBUG)

# Also monkey-patch threading to catch thread exceptions
original_errors = []
_original_run = threading.Thread.run
def patched_run(self):
    try:
        _original_run(self)
    except Exception as e:
        msg = f"Thread '{self.name}': {type(e).__name__}: {e}"
        original_errors.append(msg)
        print(f"[THREAD CRASH] {msg}")
        traceback.print_exc()
threading.Thread.run = patched_run

print("=" * 60)
print("BRAIN START TEST")
print("=" * 60)

from core.nexus_brain import nexus_brain

print("\nStarting brain...")
try:
    nexus_brain.start()
    print("brain.start() returned OK")
except Exception as e:
    print(f"brain.start() CRASHED: {type(e).__name__}: {e}")
    traceback.print_exc()

# Let it run for 15 seconds to catch background thread errors
print("\nWaiting 15 seconds to catch background errors...")
for i in range(15):
    time.sleep(1)
    sys.stdout.write(f"\r  {i+1}/15s")
    sys.stdout.flush()

print("\n\nStopping brain...")
try:
    nexus_brain.stop()
    print("brain.stop() OK")
except Exception as e:
    print(f"brain.stop() error: {e}")

# Wait a bit for threads to finish
time.sleep(2)

print(f"\n{'=' * 60}")
print(f"COLLECTED ERRORS FROM LOGGER: {len(collector.errors)}")
for i, e in enumerate(collector.errors, 1):
    # Truncate each line
    lines = e.split('\n')
    first_line = lines[0][:200]
    print(f"  {i}. {first_line}")
    # Print traceback if present
    for line in lines[1:6]:
        if 'Traceback' in line or 'Error' in line or 'File' in line:
            print(f"     {line[:200]}")

print(f"\nTHREAD CRASHES: {len(original_errors)}")
for e in original_errors:
    print(f"  - {e}")
print(f"{'=' * 60}")
