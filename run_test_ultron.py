"""Run test_ultron_fixes.py and print output to ASCII file."""
import subprocess, sys

result = subprocess.run(
    [sys.executable, r"D:\NEXUS\test_ultron_fixes.py"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
    cwd=r"D:\NEXUS"
)
output = result.stdout + result.stderr
print(output)
with open(r"D:\NEXUS\test_ultron_result.txt", "w", encoding="utf-8") as f:
    f.write(output)
sys.exit(result.returncode)
