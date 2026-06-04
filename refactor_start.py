import re
import os

path = 'd:/NEXUS/core/nexus_brain.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Make sure we only modify within the `def start(self):` ... `def stop(self):` block
start_idx = content.find('    def start(self):')
end_idx = content.find('    def stop(self):', start_idx)

if start_idx == -1 or end_idx == -1:
    print("Could not find start/stop block")
    exit(1)

pre_content = content[:start_idx]
start_method = content[start_idx:end_idx]
post_content = content[end_idx:]

# Define patterns
# We want to find lines like:         self._load_consciousness()
# And replace with:
#         with health_registry.track_load("consciousness"):
#             self._load_consciousness()
import re

# Since there are multiple indentations, match the indentation
def repl_load(m):
    indent = m.group(1)
    name = m.group(2)
    return f'{indent}with health_registry.track_load("{name}"):\n{indent}    self._load_{name}()'

start_method = re.sub(r'^([ \t]+)self\._load_([a-zA-Z0-9_]+)\(\)$', repl_load, start_method, flags=re.MULTILINE)

# Now we need to replace `.start()` but be careful, we only want to replace it for modules that are conditionally started.
# A typical pattern is:
#         if self._foo:
#             self._foo.start()
#
# Some are simple:
#         self._event_bus.start() -> safe_start(self._event_bus, "event_bus")

def repl_start(m):
    indent = m.group(1)
    # The attribute usually matches the name, but not always.
    attr = m.group(2)
    # the name for health registry should be the attribute name without leading underscore
    name = attr.lstrip('_')
    return f'{indent}safe_start(self.{attr}, "{name}")'

start_method = re.sub(r'^([ \t]+)self\.([a-zA-Z0-9_]+)\.start\(\)$', repl_start, start_method, flags=re.MULTILINE)

# Also apply it for lines with `.start(...args)` if there are any
def repl_start_args(m):
    indent = m.group(1)
    attr = m.group(2)
    args = m.group(3)
    name = attr.lstrip('_')
    return f'{indent}safe_start(self.{attr}, "{name}", {args})'

start_method = re.sub(r'^([ \t]+)self\.([a-zA-Z0-9_]+)\.start\((.+?)\)$', repl_start_args, start_method, flags=re.MULTILINE)

content = pre_content + start_method + post_content

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Replaced successfully")
