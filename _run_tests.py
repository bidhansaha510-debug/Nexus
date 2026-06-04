"""Run pytest and capture clean output to a file."""
import subprocess
import sys
import os

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['COLUMNS'] = '200'
os.environ['NO_COLOR'] = '1'

result = subprocess.run(
    [sys.executable, '-m', 'pytest',
     'tests/test_startup.py',
     'tests/test_event_bus.py', 
     'tests/test_memory_system.py',
     'tests/test_state_manager.py',
     'tests/test_llm_integration.py',
     'tests/test_cognition.py',
     'tests/test_subsystems.py',
     '-v', '--tb=long', '--no-header', '-p', 'no:rich'],
    capture_output=True, text=True, encoding='utf-8', errors='replace',
    cwd=r'd:\NEXUS'
)

with open(r'd:\NEXUS\_test_results.txt', 'w', encoding='utf-8') as f:
    f.write("=== STDOUT ===\n")
    f.write(result.stdout)
    f.write("\n=== STDERR ===\n")
    f.write(result.stderr)
    f.write(f"\n=== EXIT CODE: {result.returncode} ===\n")

print(f"Exit code: {result.returncode}")
print("Output written to _test_results.txt")
