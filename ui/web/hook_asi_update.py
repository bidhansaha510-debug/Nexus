"""Hook updateASIEngines into the fetchStats polling cycle in script.js"""

SCRIPT_PATH = r"d:\NEXUS\ui\web\static\script.js"

def hook():
    content = open(SCRIPT_PATH, "r", encoding="utf-16-le").read()

    if "updateASIEngines(data" in content:
        print("SKIP: updateASIEngines call already present in fetchStats")
        return

    # Find the hacking panel update call
    target = "updateHackingPanelV2(data.hacking_stats"
    idx = content.find(target)
    if idx == -1:
        target = "updateHackingPanel(data.hacking_stats"
        idx = content.find(target)
    if idx == -1:
        print("ERROR: Could not find hacking panel update call")
        return

    # Find the end of the surrounding try/catch block
    catch_idx = content.find("catch", idx)
    if catch_idx == -1:
        print("ERROR: Could not find catch block")
        return
    brace_idx = content.find("}", catch_idx)
    newline_idx = content.find("\n", brace_idx)
    insert_point = newline_idx + 1

    asi_call = "        try { updateASIEngines(data.asi_engines || {}); } catch (eASI) { console.warn('updateASIEngines error:', eASI); }\n"

    content = content[:insert_point] + asi_call + content[insert_point:]

    with open(SCRIPT_PATH, "w", encoding="utf-16-le") as f:
        f.write(content)

    print("OK: Added updateASIEngines(data.asi_engines) call to fetchStats")

if __name__ == "__main__":
    hook()
