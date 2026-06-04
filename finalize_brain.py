import re

path = 'd:/NEXUS/core/nexus_brain.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add imports
if 'from utils.resilience import health_registry' not in content:
    content = content.replace(
        'from utils.logger import (',
        'from utils.resilience import health_registry, safe_start\nfrom utils.metrics import metrics\nfrom utils.logger import ('
    )
    content = content.replace(
        'print_startup_banner\n)',
        'print_startup_banner, log_startup_summary\n)'
    )

# 2. Add metrics at the end of start(self)
# Find the exact end of start(self). The method ends before def stop(self):
start_idx = content.find('    def start(self):')
end_idx = content.find('    def stop(self):', start_idx)

start_method = content[start_idx:end_idx]

metrics_code = """
        # Record startup metrics
        startup_ms = (datetime.now() - self._startup_time).total_seconds() * 1000
        metrics.histogram("nexus_brain_startup_duration_seconds").observe(startup_ms / 1000.0)
        report = health_registry.get_report()
        metrics.gauge("nexus_modules_healthy").set(report['healthy'])
        metrics.gauge("nexus_modules_failed").set(report['failed'])
        
        log_startup_summary()
"""

# If not already added
if 'log_startup_summary()' not in start_method:
    # Insert it right before the end
    # We strip trailing whitespace from start_method and add it
    start_method = start_method.rstrip() + "\n" + metrics_code + "\n\n"
    content = content[:start_idx] + start_method + content[end_idx:]

# 3. Add is_running and get_health_report()
methods_code = """
    @property
    def is_running(self) -> bool:
        \"\"\"Return whether the Nexus brain is running.\"\"\"
        return self._running
        
    def get_health_report(self) -> dict:
        \"\"\"Return the current system health report.\"\"\"
        return health_registry.get_report()

    def stop(self):"""

if 'def get_health_report(self)' not in content:
    content = content.replace('    def stop(self):', methods_code)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Finalized perfectly!")
