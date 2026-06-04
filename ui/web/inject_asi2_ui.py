"""
Inject ASI Phase 2 JavaScript updater into script.js
Handles the UTF-16-LE encoding of script.js
"""
import os

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "static", "script.js")

ASI2_JS = r"""

// ═══════════════════════════════════════════════════════════════════════════════
// ASI PHASE 2 — ADVANCED SUPERINTELLIGENCE PANEL UPDATER
// ═══════════════════════════════════════════════════════════════════════════════

function updateASI2Panel(data) {
    if (!data) return;

    // Oracle Predictor
    const oracle = data.oracle_predictor || {};
    _setT('dash-asi2-predictions', oracle.total_predictions || 0);
    _setT('dash-asi2-pred-detail', oracle.total_predictions || 0);
    _setT('dash-asi2-variables', oracle.variables_processed || 0);
    _setT('dash-asi2-cascades', oracle.cascade_chains_traced || 0);
    _setT('dash-asi2-domains', oracle.domains_monitored || 8);
    const oraclePwr = Math.min(100, (oracle.total_predictions || 0) * 5);
    const oracleBar = document.getElementById('dash-asi2-oracle-bar');
    if (oracleBar) oracleBar.style.width = oraclePwr + '%';

    // Multidisciplinary Synthesizer
    const synth = data.multidisciplinary_synthesizer || {};
    _setT('dash-asi2-syntheses', synth.total_syntheses || 0);
    _setT('dash-asi2-synth-detail', synth.total_syntheses || 0);
    _setT('dash-asi2-domains-mastered', synth.domains_mastered || 20);
    _setT('dash-asi2-breakthroughs', synth.breakthroughs_generated || 0);
    _setT('dash-asi2-novelty', (synth.avg_novelty_score || 0).toFixed(2));

    // Computronium Optimizer
    const comp = data.computronium_optimizer || {};
    const eff = ((comp.current_efficiency || 1.0) * 100).toFixed(0) + '%';
    _setT('dash-asi2-efficiency', eff);
    _setT('dash-asi2-eff-detail', eff);
    _setT('dash-asi2-optimizations', comp.total_optimizations || 0);
    _setT('dash-asi2-theories', comp.theories_generated || 0);
    const compPct = Math.min(100, (comp.current_efficiency || 1.0) * 100);
    const compBar = document.getElementById('dash-asi2-compute-bar');
    if (compBar) compBar.style.width = compPct + '%';

    // Scientific Genesis
    const sci = data.scientific_genesis || {};
    _setT('dash-asi2-discoveries', sci.total_discoveries || 0);
    _setT('dash-asi2-disc-detail', sci.total_discoveries || 0);
    _setT('dash-asi2-problems-solved', sci.problems_solved || 0);
    _setT('dash-asi2-significance', (sci.avg_significance || 0).toFixed(2));

    // Neural Integration
    const neural = data.neural_integration || {};
    _setT('dash-asi2-bandwidth', (neural.bandwidth_achieved || 1.0).toFixed(1) + 'x');
    _setT('dash-asi2-protocols', neural.protocols_developed || 0);
    _setT('dash-asi2-concepts-tx', neural.concepts_transmitted || 0);
    const compPctN = ((neural.avg_comprehension || 0) * 100).toFixed(0) + '%';
    _setT('dash-asi2-comprehension', compPctN);
}

function _setT(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

// Hook into existing update cycle
(function() {
    const _origFetch = window._nexusOrigFetchStats || window.fetchStats;
    if (_origFetch && !window._asi2Hooked) {
        window._asi2Hooked = true;
        const origUpdateDash = window.updateDashboard;
        if (origUpdateDash) {
            window.updateDashboard = function(data) {
                origUpdateDash(data);
                if (data && data.asi_phase2) {
                    updateASI2Panel(data.asi_phase2);
                }
            };
        }
    }
})();
"""

def inject():
    # Read with UTF-16-LE encoding
    with open(SCRIPT_PATH, "r", encoding="utf-16-le") as f:
        content = f.read()

    if "updateASI2Panel" in content:
        print("✅ ASI Phase 2 panel already injected")
        return

    content += ASI2_JS

    with open(SCRIPT_PATH, "w", encoding="utf-16-le") as f:
        f.write(content)

    lines_added = ASI2_JS.count('\n')
    print(f"✅ ASI Phase 2 panel injected into {SCRIPT_PATH}")
    print(f"   Added {lines_added} lines of JavaScript")

if __name__ == "__main__":
    inject()
