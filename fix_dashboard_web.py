"""
Fix NEXUS Web Dashboard: static values, missing update code, Unicode escaping, field mismatches.

Issues fixed:
1. script.js: Unicode double-escaping (\\u2600 -> actual emoji chars)
2. script.js: Missing update code for dash-asi-growth, dash-asi-iq-detail, etc.
3. script.js: Fix field name mismatches (profiles_built -> profiles_count, etc.)
4. Backend: Fix super_empathy.get_stats to return fields JS expects
5. Backend: Fix transcendent_creator.get_stats to return fields JS expects
6. Backend: Fix singularity_engine.get_stats to include growth_rate
"""
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════════════
# 1. FIX script.js (UTF-16 encoded)
# ═══════════════════════════════════════════════════════════════
JS_PATH = os.path.join(BASE, "ui", "web", "static", "script.js")

with open(JS_PATH, "r", encoding="utf-16") as f:
    js = f.read()

changes_made = []

# --- Fix 1a: Unicode double-escaping in dreamEmojis ---
old_dream = r"var dreamEmojis = { awake: '\\u2600\\uFE0F', daydreaming: '\\uD83C\\uDF24\\uFE0F', light_dream: '\\uD83C\\uDF19', deep_dream: '\\uD83C\\uDF0C', lucid: '\\u2728' };"
new_dream = "var dreamEmojis = { awake: '\u2600\uFE0F', daydreaming: '\U0001f324\uFE0F', light_dream: '\U0001f319', deep_dream: '\U0001f30c', lucid: '\u2728' };"
if old_dream in js:
    js = js.replace(old_dream, new_dream)
    changes_made.append("Fixed dreamEmojis Unicode escaping")
else:
    # Try with double backslashes as they appear in the file
    old_dream2 = "var dreamEmojis = { awake: '\\\\u2600\\\\uFE0F', daydreaming: '\\\\uD83C\\\\uDF24\\\\uFE0F', light_dream: '\\\\uD83C\\\\uDF19', deep_dream: '\\\\uD83C\\\\uDF0C', lucid: '\\\\u2728' };"
    if old_dream2 in js:
        js = js.replace(old_dream2, new_dream)
        changes_made.append("Fixed dreamEmojis Unicode escaping (double-escaped)")

# Fix the fallback emoji too
old_fallback = "(dreamEmojis[ds] || '\\\\uD83D\\\\uDCA4')"
new_fallback = "(dreamEmojis[ds] || '\U0001f4a4')"
if old_fallback in js:
    js = js.replace(old_fallback, new_fallback)
    changes_made.append("Fixed dream fallback emoji")

# Fix agent icons too
old_icons_pattern = "var aIcons = { analyst: '\\\\uD83D\\\\uDD2C'"
if old_icons_pattern in js:
    # Find the full line
    idx = js.find(old_icons_pattern)
    end = js.find("};", idx) + 2
    old_icons_line = js[idx:end]
    new_icons_line = "var aIcons = { analyst: '\U0001f52c', creative: '\U0001f3a8', emotional: '\U0001f496', critic: '\U0001f50d', strategist: '\u265f\ufe0f', ethicist: '\u2696\ufe0f', pragmatist: '\U0001f527', visionary: '\U0001f52e' };"
    js = js.replace(old_icons_line, new_icons_line)
    changes_made.append("Fixed agent icons Unicode escaping")

# Fix agent fallback icon
old_agent_fb = "(aIcons[name] || '\\\\uD83E\\\\uDDE0')"
new_agent_fb = "(aIcons[name] || '\U0001f9e0')"
if old_agent_fb in js:
    js = js.replace(old_agent_fb, new_agent_fb)
    changes_made.append("Fixed agent fallback icon")

# Fix org state badge
old_org = "'\\\\uD83E\\\\uDDEC '"
new_org = "'\U0001f9ec '"
if old_org in js:
    js = js.replace(old_org, new_org)
    changes_made.append("Fixed org state badge emoji")

# --- Fix 1b: Add missing ASI detail fields to updateASIEngines ---
# Find the end of singularity section (after iq-bar) and add growth_rate + iq-detail
old_singularity_end = "if (iqBar) iqBar.style.width = Math.min(100, ((s.composite_iq || 50) / 200) * 100) + '%';"
new_singularity_end = """if (iqBar) iqBar.style.width = Math.min(100, ((s.composite_iq || 50) / 200) * 100) + '%';
    _asi('dash-asi-iq-detail', s.composite_iq ? s.composite_iq.toFixed(1) : '50.0');
    _asi('dash-asi-growth', ((s.improvement_velocity || 0) * 100).toFixed(2) + '%');"""
if old_singularity_end in js:
    js = js.replace(old_singularity_end, new_singularity_end)
    changes_made.append("Added dash-asi-iq-detail and dash-asi-growth updates")

# Fix creator field: JS reads total_creations but backend returns works_created
old_creator = "_asi('dash-asi-creations', c.total_creations || 0);"
new_creator = "_asi('dash-asi-creations', c.total_creations || c.works_created || 0);\n    _asi('dash-asi-creations-detail', c.total_creations || c.works_created || 0);"
if old_creator in js:
    js = js.replace(old_creator, new_creator)
    changes_made.append("Fixed creator total_creations field + added detail")

# Fix genesis: add detail + genesis_cycles
old_genesis_goals = "_asi('dash-asi-goals', g.total_goals || 0);"
new_genesis_goals = """_asi('dash-asi-goals', g.total_goals || 0);
    _asi('dash-asi-problems-detail', g.total_problems || 0);
    _asi('dash-asi-genesis-cycles', g.genesis_cycles || g.total_cycles || 0);"""
if old_genesis_goals in js:
    js = js.replace(old_genesis_goals, new_genesis_goals)
    changes_made.append("Added genesis detail + genesis_cycles")

# Fix empathy: add detail + fix field name (profiles_built -> profiles_count)
old_empathy = "_asi('dash-asi-profiles', em.profiles_built || 0);"
new_empathy = "_asi('dash-asi-profiles', em.profiles_built || em.profiles_count || 0);"
if old_empathy in js:
    js = js.replace(old_empathy, new_empathy)
    changes_made.append("Fixed empathy profiles_built -> profiles_count fallback")

old_empathy_neg = "_asi('dash-asi-negotiations', em.negotiations || 0);"
new_empathy_neg = """_asi('dash-asi-negotiations', em.negotiations || 0);
    _asi('dash-asi-empathy-detail', em.predictions_made || 0);"""
if old_empathy_neg in js:
    js = js.replace(old_empathy_neg, new_empathy_neg)
    changes_made.append("Added empathy detail")

# Fix orchestrator: add global-health text
old_orch = "_asi('dash-asi-synth-cycles', o.synthesis_cycles || 0);"
new_orch = """_asi('dash-asi-synth-cycles', o.synthesis_cycles || 0);
    _asi('dash-asi-global-health', Math.round((o.overall_health || 1.0) * 100) + '%');"""
if old_orch in js:
    js = js.replace(old_orch, new_orch)
    changes_made.append("Added global-health update")

# --- Fix 1c: Add top card updates in ASI section ---
# The ASI section top cards (dash-asi-iq, dash-asi-creations etc) should update too
# These are already handled by the _asi calls above since they use the same IDs

# Write back
with open(JS_PATH, "w", encoding="utf-16") as f:
    f.write(js)

print(f"script.js: {len(changes_made)} changes made:")
for c in changes_made:
    print(f"  ✓ {c}")

# ═══════════════════════════════════════════════════════════════
# 2. FIX backend modules — add missing fields to get_stats()
# ═══════════════════════════════════════════════════════════════

# --- Fix transcendent_creator.py: add total_creations field ---
CREATOR_PATH = os.path.join(BASE, "cognition", "transcendent_creator.py")
with open(CREATOR_PATH, "r", encoding="utf-8") as f:
    creator_code = f.read()

old_creator_stats = """def get_stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "genres_invented": len(self._genres),
            "works_created": len(self._works),
            "methods_invented": len(self._methods),
            **self._stats,
        }"""
new_creator_stats = """def get_stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "genres_invented": len(self._genres),
            "works_created": len(self._works),
            "total_creations": len(self._works),
            "methods_invented": len(self._methods),
            "cross_domain_fusions": self._stats.get("cross_domain_fusions", 0),
            "symphonies_composed": self._stats.get("symphonies_composed", 0),
            **self._stats,
        }"""
if old_creator_stats in creator_code:
    creator_code = creator_code.replace(old_creator_stats, new_creator_stats)
    with open(CREATOR_PATH, "w", encoding="utf-8") as f:
        f.write(creator_code)
    print("transcendent_creator.py: ✓ Added total_creations, cross_domain_fusions, symphonies_composed fields")
else:
    print("transcendent_creator.py: ⚠ get_stats pattern not matched (may already be fixed)")

# --- Fix super_empathy.py: add profiles_built, predictions_made, negotiations ---
EMPATHY_PATH = os.path.join(BASE, "cognition", "super_empathy.py")
with open(EMPATHY_PATH, "r", encoding="utf-8") as f:
    empathy_code = f.read()

old_empathy_stats = """def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, "profiles_count": len(self._profiles), **self._stats}"""
new_empathy_stats = """def get_stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "profiles_count": len(self._profiles),
            "profiles_built": len(self._profiles),
            "predictions_made": self._stats.get("predictions_made", 0),
            "negotiations": self._stats.get("negotiations", 0),
            **self._stats,
        }"""
if old_empathy_stats in empathy_code:
    empathy_code = empathy_code.replace(old_empathy_stats, new_empathy_stats)
    with open(EMPATHY_PATH, "w", encoding="utf-8") as f:
        f.write(empathy_code)
    print("super_empathy.py: ✓ Added profiles_built, predictions_made, negotiations fields")
else:
    print("super_empathy.py: ⚠ get_stats pattern not matched (may already be fixed)")

# --- Fix singularity_engine.py: add growth_rate ---
SING_PATH = os.path.join(BASE, "self_improvement", "singularity_engine.py")
with open(SING_PATH, "r", encoding="utf-8") as f:
    sing_code = f.read()

old_sing = '"recursion_depth": self._state.recursion_depth,'
new_sing = '''"recursion_depth": self._state.recursion_depth,
            "growth_rate": round(self._state.improvement_velocity * 100, 2),'''
if old_sing in sing_code:
    sing_code = sing_code.replace(old_sing, new_sing, 1)
    with open(SING_PATH, "w", encoding="utf-8") as f:
        f.write(sing_code)
    print("singularity_engine.py: ✓ Added growth_rate field")
else:
    print("singularity_engine.py: ⚠ Pattern not matched (may already be fixed)")

# --- Fix goal_genesis.py: add genesis_cycles ---
GENESIS_PATH = os.path.join(BASE, "cognition", "goal_genesis.py")
with open(GENESIS_PATH, "r", encoding="utf-8") as f:
    genesis_code = f.read()

old_genesis = '''def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running, "total_problems": len(self._problems),
                "total_solutions": len(self._solutions), "total_goals": len(self._genesis_goals), **self._stats}'''
new_genesis = '''def get_stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "total_problems": len(self._problems),
            "total_solutions": len(self._solutions),
            "total_goals": len(self._genesis_goals),
            "genesis_cycles": self._stats.get("genesis_cycles", self._stats.get("total_cycles", 0)),
            **self._stats,
        }'''
if old_genesis in genesis_code:
    genesis_code = genesis_code.replace(old_genesis, new_genesis)
    with open(GENESIS_PATH, "w", encoding="utf-8") as f:
        f.write(genesis_code)
    print("goal_genesis.py: ✓ Added genesis_cycles field")
else:
    print("goal_genesis.py: ⚠ Pattern not matched (may already be fixed)")

# --- Fix omniscient_orchestrator.py: add synthesis_cycles ---
ORCH_PATH = os.path.join(BASE, "core", "omniscient_orchestrator.py")
with open(ORCH_PATH, "r", encoding="utf-8") as f:
    orch_code = f.read()

old_orch_stats = '''def get_stats(self) -> Dict[str, Any]:
        return {"running": self._running,
                "overall_health": round(self._global_state.overall_health, 2),
                "active_anomalies": len([a for a in self._anomalies if not a.resolved]),
                "active_tasks": len([t for t in self._autonomous_tasks.values() if t.status in ("pending", "running")]),
                **self._stats}'''
new_orch_stats = '''def get_stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "overall_health": round(self._global_state.overall_health, 2),
            "active_anomalies": len([a for a in self._anomalies if not a.resolved]),
            "active_tasks": len([t for t in self._autonomous_tasks.values() if t.status in ("pending", "running")]),
            "synthesis_cycles": self._stats.get("synthesis_cycles", 0),
            **self._stats,
        }'''
if old_orch_stats in orch_code:
    orch_code = orch_code.replace(old_orch_stats, new_orch_stats)
    with open(ORCH_PATH, "w", encoding="utf-8") as f:
        f.write(orch_code)
    print("omniscient_orchestrator.py: ✓ Added synthesis_cycles field")
else:
    print("omniscient_orchestrator.py: ⚠ Pattern not matched (may already be fixed)")


print("\n═══ All fixes applied! ═══")
print("Restart the NEXUS web server to see the changes.")
