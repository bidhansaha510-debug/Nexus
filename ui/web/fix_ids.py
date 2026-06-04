"""Fix ID mismatches in updateASIEngines function in script.js"""

SCRIPT_PATH = r"d:\NEXUS\ui\web\static\script.js"

REPLACEMENTS = {
    # Empathy predictions: JS used dash-asi-predictions, HTML uses dash-asi-empathy-pred
    "'dash-asi-predictions'": "'dash-asi-empathy-pred'",
    # Orchestrator cycles: JS used dash-asi-cycles, HTML uses dash-asi-synth-cycles  
    "'dash-asi-cycles'": "'dash-asi-synth-cycles'",
}

def fix():
    content = open(SCRIPT_PATH, "r", encoding="utf-16-le").read()
    fixed = 0
    for old, new in REPLACEMENTS.items():
        if old in content:
            content = content.replace(old, new)
            fixed += 1
            print(f"  Fixed: {old} -> {new}")
    
    if fixed > 0:
        with open(SCRIPT_PATH, "w", encoding="utf-16-le") as f:
            f.write(content)
        print(f"OK: Fixed {fixed} ID mismatches")
    else:
        print("No mismatches found (already correct)")

if __name__ == "__main__":
    fix()
