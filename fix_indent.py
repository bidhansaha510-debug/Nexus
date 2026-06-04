import os
import glob

cognition_dir = "d:\\NEXUS\\cognition"
files = glob.glob(os.path.join(cognition_dir, "*.py"))

bad_block = """            try:
                from utils.json_utils import extract_json
            data = extract_json(response.text)
            if not data:
                raise ValueError("Empty or invalid JSON from LLM")
            except json.JSONDecodeError:"""

good_block = """            try:
                from utils.json_utils import extract_json
                data = extract_json(response.text)
                if not data:
                    raise ValueError("Empty or invalid JSON from LLM")
            except json.JSONDecodeError:"""

count = 0
for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    if bad_block in content:
        content = content.replace(bad_block, good_block)
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
        count += 1
        print(f"Fixed {os.path.basename(f)}")

print(f"Fixed {count} files.")
