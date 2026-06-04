"""
NEXUS AI — ASI Web UI Injector
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Injects the ASI status panel JavaScript into script.js.
Handles UTF-16-LE encoding used by the existing script.js.

Usage:
    python inject_asi_ui.py
"""

import os, sys, re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT_JS = SCRIPT_DIR / "static" / "script.js"

# ═══════════════════════════════════════════════════════════════════════════════
# ASI PANEL JAVASCRIPT CODE
# ═══════════════════════════════════════════════════════════════════════════════

ASI_PANEL_JS = r"""

// ═══════════════════════════════════════════════════════════════════════════════
// ASI ENGINE STATUS PANEL — Artificial Superintelligence Visual Dashboard
// ═══════════════════════════════════════════════════════════════════════════════

function createASIPanel() {
    // Check if panel already exists
    if (document.getElementById('asi-panel')) return;

    const panel = document.createElement('div');
    panel.id = 'asi-panel';
    panel.innerHTML = `
        <div class="asi-panel-container" style="
            background: linear-gradient(135deg, rgba(10,0,30,0.95), rgba(25,0,50,0.9));
            border: 1px solid rgba(138,43,226,0.4);
            border-radius: 16px;
            padding: 20px;
            margin: 15px 0;
            backdrop-filter: blur(12px);
            box-shadow: 0 0 30px rgba(138,43,226,0.15), inset 0 0 60px rgba(75,0,130,0.1);
        ">
            <div style="display:flex; align-items:center; margin-bottom:16px; gap:10px;">
                <span style="font-size:22px;">🌌</span>
                <h3 style="margin:0; color:#e0b0ff; font-size:16px; letter-spacing:2px; text-transform:uppercase;
                    text-shadow: 0 0 10px rgba(200,100,255,0.5);">
                    ASI Engine Status
                </h3>
                <span id="asi-pulse" style="width:10px;height:10px;border-radius:50%;background:#a855f7;
                    box-shadow:0 0 8px #a855f7;animation:asiPulse 2s infinite;margin-left:auto;"></span>
            </div>

            <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px;">
                <!-- Singularity Engine -->
                <div class="asi-card" style="background:rgba(100,0,200,0.15);border:1px solid rgba(147,51,234,0.3);
                    border-radius:12px;padding:14px;">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                        <span style="font-size:18px;">⚡</span>
                        <span style="color:#c084fc;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:1px;">Singularity</span>
                    </div>
                    <div id="asi-iq" style="font-size:28px;font-weight:700;color:#e9d5ff;
                        text-shadow:0 0 15px rgba(167,139,250,0.5);">—</div>
                    <div style="color:#a78bfa;font-size:10px;margin-top:2px;">IQ SCORE</div>
                    <div style="margin-top:8px;height:4px;background:rgba(88,28,135,0.4);border-radius:2px;overflow:hidden;">
                        <div id="asi-iq-bar" style="height:100%;width:50%;background:linear-gradient(90deg,#7c3aed,#a855f7);
                            border-radius:2px;transition:width 1s ease;"></div>
                    </div>
                    <div style="display:flex;justify-content:space-between;margin-top:6px;">
                        <span style="color:#8b5cf6;font-size:10px;">Velocity: <span id="asi-velocity">0</span></span>
                        <span style="color:#8b5cf6;font-size:10px;">×<span id="asi-compound">1.00</span></span>
                    </div>
                </div>

                <!-- Transcendent Creator -->
                <div class="asi-card" style="background:rgba(200,50,100,0.12);border:1px solid rgba(236,72,153,0.3);
                    border-radius:12px;padding:14px;">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                        <span style="font-size:18px;">🎭</span>
                        <span style="color:#f472b6;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:1px;">Creator</span>
                    </div>
                    <div id="asi-creations" style="font-size:28px;font-weight:700;color:#fce7f3;
                        text-shadow:0 0 15px rgba(244,114,182,0.5);">0</div>
                    <div style="color:#ec4899;font-size:10px;margin-top:2px;">TOTAL CREATIONS</div>
                    <div style="display:flex;gap:12px;margin-top:8px;">
                        <div style="text-align:center;">
                            <div id="asi-genres" style="color:#fbcfe8;font-size:16px;font-weight:600;">0</div>
                            <div style="color:#db2777;font-size:9px;">Genres</div>
                        </div>
                        <div style="text-align:center;">
                            <div id="asi-fusions" style="color:#fbcfe8;font-size:16px;font-weight:600;">0</div>
                            <div style="color:#db2777;font-size:9px;">Fusions</div>
                        </div>
                        <div style="text-align:center;">
                            <div id="asi-symphonies" style="color:#fbcfe8;font-size:16px;font-weight:600;">0</div>
                            <div style="color:#db2777;font-size:9px;">Works</div>
                        </div>
                    </div>
                </div>

                <!-- Goal Genesis -->
                <div class="asi-card" style="background:rgba(0,150,100,0.12);border:1px solid rgba(16,185,129,0.3);
                    border-radius:12px;padding:14px;">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                        <span style="font-size:18px;">🌍</span>
                        <span style="color:#34d399;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:1px;">Genesis</span>
                    </div>
                    <div id="asi-problems" style="font-size:28px;font-weight:700;color:#d1fae5;
                        text-shadow:0 0 15px rgba(52,211,153,0.5);">0</div>
                    <div style="color:#10b981;font-size:10px;margin-top:2px;">PROBLEMS FOUND</div>
                    <div style="display:flex;gap:12px;margin-top:8px;">
                        <div style="text-align:center;">
                            <div id="asi-solutions" style="color:#a7f3d0;font-size:16px;font-weight:600;">0</div>
                            <div style="color:#059669;font-size:9px;">Solutions</div>
                        </div>
                        <div style="text-align:center;">
                            <div id="asi-goals" style="color:#a7f3d0;font-size:16px;font-weight:600;">0</div>
                            <div style="color:#059669;font-size:9px;">Goals</div>
                        </div>
                    </div>
                </div>

                <!-- Super Empathy -->
                <div class="asi-card" style="background:rgba(200,100,0,0.12);border:1px solid rgba(251,146,60,0.3);
                    border-radius:12px;padding:14px;">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                        <span style="font-size:18px;">💖</span>
                        <span style="color:#fb923c;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:1px;">Empathy</span>
                    </div>
                    <div id="asi-predictions" style="font-size:28px;font-weight:700;color:#fed7aa;
                        text-shadow:0 0 15px rgba(251,146,60,0.5);">0</div>
                    <div style="color:#f97316;font-size:10px;margin-top:2px;">PREDICTIONS</div>
                    <div style="display:flex;gap:12px;margin-top:8px;">
                        <div style="text-align:center;">
                            <div id="asi-profiles" style="color:#ffedd5;font-size:16px;font-weight:600;">0</div>
                            <div style="color:#ea580c;font-size:9px;">Profiles</div>
                        </div>
                        <div style="text-align:center;">
                            <div id="asi-negotiations" style="color:#ffedd5;font-size:16px;font-weight:600;">0</div>
                            <div style="color:#ea580c;font-size:9px;">Negotiations</div>
                        </div>
                    </div>
                </div>

                <!-- Omniscient Orchestrator -->
                <div class="asi-card" style="background:rgba(0,100,200,0.12);border:1px solid rgba(56,189,248,0.3);
                    border-radius:12px;padding:14px;">
                    <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                        <span style="font-size:18px;">🌐</span>
                        <span style="color:#38bdf8;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:1px;">Orchestrator</span>
                    </div>
                    <div id="asi-health" style="font-size:28px;font-weight:700;color:#bae6fd;
                        text-shadow:0 0 15px rgba(56,189,248,0.5);">—</div>
                    <div style="color:#0ea5e9;font-size:10px;margin-top:2px;">SYSTEM HEALTH</div>
                    <div style="margin-top:8px;height:4px;background:rgba(7,89,133,0.4);border-radius:2px;overflow:hidden;">
                        <div id="asi-health-bar" style="height:100%;width:100%;background:linear-gradient(90deg,#0284c7,#38bdf8);
                            border-radius:2px;transition:width 1s ease;"></div>
                    </div>
                    <div style="display:flex;justify-content:space-between;margin-top:6px;">
                        <span style="color:#0ea5e9;font-size:10px;">Anomalies: <span id="asi-anomalies">0</span></span>
                        <span style="color:#0ea5e9;font-size:10px;">Cycles: <span id="asi-cycles">0</span></span>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Add animation keyframes
    if (!document.getElementById('asi-styles')) {
        const style = document.createElement('style');
        style.id = 'asi-styles';
        style.textContent = `
            @keyframes asiPulse {
                0%, 100% { opacity: 1; box-shadow: 0 0 8px #a855f7; }
                50% { opacity: 0.4; box-shadow: 0 0 16px #a855f7; }
            }
            .asi-card:hover {
                transform: translateY(-2px);
                transition: transform 0.3s ease;
            }
            .asi-card {
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }
            .asi-card:hover {
                box-shadow: 0 4px 20px rgba(138,43,226,0.2);
            }
        `;
        document.head.appendChild(style);
    }

    // Insert at appropriate location in dashboard
    const dashboard = document.querySelector('.dashboard-content, .main-content, #dashboard, main, .content');
    if (dashboard) {
        dashboard.insertBefore(panel, dashboard.firstChild);
    } else {
        document.body.appendChild(panel);
    }
}

function updateASIPanel(data) {
    // Create panel if not exists
    if (!document.getElementById('asi-panel')) {
        createASIPanel();
    }

    if (!data) return;

    // ── Singularity Engine ──
    const singularity = data.singularity || {};
    const iq = singularity.composite_iq || 50;
    const el_iq = document.getElementById('asi-iq');
    if (el_iq) el_iq.textContent = iq.toFixed(1);
    const el_bar = document.getElementById('asi-iq-bar');
    if (el_bar) el_bar.style.width = Math.min(100, (iq / 200) * 100) + '%';
    const el_vel = document.getElementById('asi-velocity');
    if (el_vel) el_vel.textContent = (singularity.improvement_velocity || 0).toFixed(4);
    const el_comp = document.getElementById('asi-compound');
    if (el_comp) el_comp.textContent = (singularity.compound_multiplier || 1.0).toFixed(3);

    // ── Transcendent Creator ──
    const creator = data.creator || {};
    const el_cr = document.getElementById('asi-creations');
    if (el_cr) el_cr.textContent = creator.total_creations || 0;
    const el_ge = document.getElementById('asi-genres');
    if (el_ge) el_ge.textContent = creator.genres_invented || 0;
    const el_fu = document.getElementById('asi-fusions');
    if (el_fu) el_fu.textContent = creator.cross_domain_fusions || 0;
    const el_sy = document.getElementById('asi-symphonies');
    if (el_sy) el_sy.textContent = creator.symphonies_composed || 0;

    // ── Goal Genesis ──
    const genesis = data.genesis || {};
    const el_pr = document.getElementById('asi-problems');
    if (el_pr) el_pr.textContent = genesis.total_problems || 0;
    const el_so = document.getElementById('asi-solutions');
    if (el_so) el_so.textContent = genesis.total_solutions || 0;
    const el_go = document.getElementById('asi-goals');
    if (el_go) el_go.textContent = genesis.total_goals || 0;

    // ── Super Empathy ──
    const empathy = data.empathy || {};
    const el_pred = document.getElementById('asi-predictions');
    if (el_pred) el_pred.textContent = empathy.predictions_made || 0;
    const el_prof = document.getElementById('asi-profiles');
    if (el_prof) el_prof.textContent = empathy.profiles_built || 0;
    const el_neg = document.getElementById('asi-negotiations');
    if (el_neg) el_neg.textContent = empathy.negotiations || 0;

    // ── Omniscient Orchestrator ──
    const orchestrator = data.orchestrator || {};
    const health = orchestrator.overall_health || 0;
    const el_h = document.getElementById('asi-health');
    if (el_h) el_h.textContent = Math.round(health * 100) + '%';
    const el_hb = document.getElementById('asi-health-bar');
    if (el_hb) el_hb.style.width = (health * 100) + '%';
    const el_an = document.getElementById('asi-anomalies');
    if (el_an) el_an.textContent = orchestrator.active_anomalies || 0;
    const el_cy = document.getElementById('asi-cycles');
    if (el_cy) el_cy.textContent = orchestrator.synthesis_cycles || 0;
}

// Auto-create ASI panel when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', createASIPanel);
} else {
    createASIPanel();
}

// ═══════════════════════════════════════════════════════════════════════════════
// END ASI PANEL
// ═══════════════════════════════════════════════════════════════════════════════
"""


def inject():
    """Read script.js (UTF-16-LE), append ASI panel code, write back."""
    if not SCRIPT_JS.exists():
        print(f"ERROR: {SCRIPT_JS} not found")
        sys.exit(1)

    # Read existing content
    with open(SCRIPT_JS, "r", encoding="utf-16-le") as f:
        content = f.read()

    # Check if already injected
    if "ASI ENGINE STATUS PANEL" in content:
        print("✅ ASI panel already injected in script.js — skipping")
        return

    # Append ASI panel code
    content += ASI_PANEL_JS

    # Write back in same encoding
    with open(SCRIPT_JS, "w", encoding="utf-16-le") as f:
        f.write(content)

    print(f"✅ ASI panel injected into {SCRIPT_JS}")
    print(f"   Added {len(ASI_PANEL_JS.splitlines())} lines of JavaScript")


if __name__ == "__main__":
    inject()
