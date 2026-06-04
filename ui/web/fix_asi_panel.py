"""
Fix ASI panel in script.js:
1. Remove the floating createASIPanel / updateASIPanel code (Phase 1 injection)
2. Remove the Phase 2 updateASI2Panel code
3. Insert a clean dashboard-integrated updateASIEngines function
   that reads from the /api/stats response's asi_engines key and
   updates the HTML elements already present in index.html
"""
import re

SCRIPT_PATH = r"d:\NEXUS\ui\web\static\script.js"

# ── New integrated updater ──
INTEGRATED_JS = r"""

// ═══════════════════════════════════════════════════════════════════════════════
// ASI ENGINES — DASHBOARD INTEGRATED UPDATER
// ═══════════════════════════════════════════════════════════════════════════════

function updateASIEngines(asiData) {
    if (!asiData) return;

    // ─── Phase 1: ASI Superintelligence Section ───

    // Singularity
    var s = asiData.singularity || {};
    _asi('dash-asi-iq', s.composite_iq ? s.composite_iq.toFixed(1) : '—');
    _asi('dash-asi-velocity', (s.improvement_velocity || 0).toFixed(4));
    _asi('dash-asi-compound', (s.compound_multiplier || 1.0).toFixed(3));
    var iqBar = document.getElementById('dash-asi-iq-bar');
    if (iqBar) iqBar.style.width = Math.min(100, ((s.composite_iq || 50) / 200) * 100) + '%';

    // Creator
    var c = asiData.creator || {};
    _asi('dash-asi-creations', c.total_creations || 0);
    _asi('dash-asi-genres', c.genres_invented || 0);
    _asi('dash-asi-fusions', c.cross_domain_fusions || 0);
    _asi('dash-asi-symphonies', c.symphonies_composed || 0);

    // Genesis
    var g = asiData.genesis || {};
    _asi('dash-asi-problems', g.total_problems || 0);
    _asi('dash-asi-solutions', g.total_solutions || 0);
    _asi('dash-asi-goals', g.total_goals || 0);

    // Empathy
    var em = asiData.empathy || {};
    _asi('dash-asi-predictions', em.predictions_made || 0);
    _asi('dash-asi-profiles', em.profiles_built || 0);
    _asi('dash-asi-negotiations', em.negotiations || 0);

    // Orchestrator
    var o = asiData.orchestrator || {};
    var health = o.overall_health || 0;
    _asi('dash-asi-health', Math.round(health * 100) + '%');
    var hBar = document.getElementById('dash-asi-health-bar');
    if (hBar) hBar.style.width = (health * 100) + '%';
    _asi('dash-asi-anomalies', o.active_anomalies || 0);
    _asi('dash-asi-cycles', o.synthesis_cycles || 0);

    // ─── Phase 2: ASI Advanced Section ───

    // Oracle Predictor
    var op = asiData.oracle_predictor || {};
    _asi('dash-asi2-predictions', op.total_predictions || 0);
    _asi('dash-asi2-pred-detail', op.total_predictions || 0);
    _asi('dash-asi2-variables', op.variables_processed || 0);
    _asi('dash-asi2-cascades', op.cascade_chains_traced || 0);
    _asi('dash-asi2-domains', op.domains_monitored || 8);
    var opBar = document.getElementById('dash-asi2-oracle-bar');
    if (opBar) opBar.style.width = Math.min(100, (op.prediction_cycles || 0) * 5) + '%';

    // Multidisciplinary Synthesizer
    var ms = asiData.multidisciplinary_synthesizer || {};
    _asi('dash-asi2-syntheses', ms.total_syntheses || 0);
    _asi('dash-asi2-synth-detail', ms.total_syntheses || 0);
    _asi('dash-asi2-domains-mastered', ms.domains_mastered || 20);
    _asi('dash-asi2-breakthroughs', ms.breakthroughs_generated || 0);
    _asi('dash-asi2-novelty', (ms.avg_novelty_score || 0).toFixed(2));

    // Computronium Optimizer
    var co = asiData.computronium_optimizer || {};
    var eff = ((co.current_efficiency || 1.0) * 100).toFixed(0) + '%';
    _asi('dash-asi2-efficiency', eff);
    _asi('dash-asi2-eff-detail', eff);
    _asi('dash-asi2-optimizations', co.total_optimizations || 0);
    _asi('dash-asi2-theories', co.theories_generated || 0);
    var coBar = document.getElementById('dash-asi2-compute-bar');
    if (coBar) coBar.style.width = Math.min(100, (co.current_efficiency || 1.0) * 100) + '%';

    // Scientific Genesis
    var sg = asiData.scientific_genesis || {};
    _asi('dash-asi2-discoveries', sg.total_discoveries || 0);
    _asi('dash-asi2-disc-detail', sg.total_discoveries || 0);
    _asi('dash-asi2-problems-solved', sg.problems_solved || 0);
    _asi('dash-asi2-significance', (sg.avg_significance || 0).toFixed(2));

    // Neural Integration
    var ni = asiData.neural_integration || {};
    _asi('dash-asi2-bandwidth', (ni.bandwidth_achieved || 1.0).toFixed(1) + 'x');
    _asi('dash-asi2-protocols', ni.protocols_developed || 0);
    _asi('dash-asi2-concepts-tx', ni.concepts_transmitted || 0);
    _asi('dash-asi2-comprehension', ((ni.avg_comprehension || 0) * 100).toFixed(0) + '%');
}

function _asi(id, val) {
    var el = document.getElementById(id);
    if (el) el.textContent = val;
}
"""

def fix():
    # Read UTF-16-LE
    with open(SCRIPT_PATH, "r", encoding="utf-16-le") as f:
        content = f.read()

    original_len = len(content)

    # 1. Remove Phase 1 floating panel code
    # Remove everything between ASI ENGINE STATUS PANEL markers
    pattern1 = r'// [═]+ *\n// ASI ENGINE STATUS PANEL.*?// END ASI PANEL\n// [═]+\s*'
    content = re.sub(pattern1, '', content, flags=re.DOTALL)

    # Also remove the createASIPanel function and DOMContentLoaded call if pattern didn't match
    if 'createASIPanel' in content:
        # Remove function createASIPanel() { ... }
        content = re.sub(
            r'function createASIPanel\(\)\s*\{.*?\n\}\s*\n',
            '', content, flags=re.DOTALL
        )
        # Remove function updateASIPanel(data) { ... }
        content = re.sub(
            r'function updateASIPanel\(data\)\s*\{.*?\n\}\s*\n',
            '', content, flags=re.DOTALL
        )
        # Remove DOMContentLoaded listener for ASI
        content = re.sub(
            r"// Auto-create ASI panel.*?createASIPanel\(\);\s*\}\s*\n",
            '', content, flags=re.DOTALL
        )
        # Remove asi-styles injection
        content = re.sub(
            r"if \(!document\.getElementById\('asi-styles'\)\).*?\}\s*\n",
            '', content, flags=re.DOTALL
        )

    # 2. Remove Phase 2 updateASI2Panel + _setT + hook code
    if 'updateASI2Panel' in content:
        content = re.sub(
            r'// [═]+ *\n// ASI PHASE 2.*?$',
            '', content, flags=re.DOTALL | re.MULTILINE
        )
        # Fallback: remove individual functions
        if 'updateASI2Panel' in content:
            content = re.sub(
                r'function updateASI2Panel\(data\)\s*\{.*?\n\}\s*\n',
                '', content, flags=re.DOTALL
            )
        if '_setT' in content:
            content = re.sub(
                r'function _setT\(id, val\)\s*\{.*?\n\}\s*\n',
                '', content, flags=re.DOTALL
            )
        # Remove hook IIFE
        content = re.sub(
            r'// Hook into existing.*?\}\)\(\);\s*\n',
            '', content, flags=re.DOTALL
        )

    # 3. Clean up excess blank lines
    content = re.sub(r'\n{4,}', '\n\n\n', content)

    # 4. Add the integrated updater
    content = content.rstrip() + '\n' + INTEGRATED_JS

    removed = original_len - len(content) + len(INTEGRATED_JS)

    # Write back in UTF-16-LE
    with open(SCRIPT_PATH, "w", encoding="utf-16-le") as f:
        f.write(content)

    print(f"✅ Fixed script.js:")
    print(f"   Removed ~{abs(removed)} chars of floating panel code")
    print(f"   Added integrated updateASIEngines function")
    print(f"   File size: {len(content)} chars")

if __name__ == "__main__":
    fix()
