/* NEXUS AI - Web Interface Logic
Async chat with poll pattern to prevent 503,
Full dashboard, mind, evolution, knowledge, system data.
Phase 13: Advanced Dashboard Enhancements
*/
const POLL_INTERVAL = 2000;
const CHAT_POLL_INTERVAL = 1500;
const MAX_POLL_FAILURES = 10;
let currentTaskId = null;
let chatPollTimer = null;
let messageCount = 0;
let pollFailCount = 0;
const completedTasks = new Set();
let moodHistory = [];
const MOOD_HISTORY_MAX = 60;
// ── Animated counter tracking ──
const animatedValues = {};
// ── Particle system ──
let particleCanvas, particleCtx, particles = [], particleRAF;
const PARTICLE_COUNT = 80;
const CONNECTION_DISTANCE = 120;
// ══════════════════════════════════════════════
// AUTH STATE
// ══════════════════════════════════════════════
let authToken = localStorage.getItem('nexus_auth_token') || null;
let currentUser = null;
function getAuthHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
    return headers;
}
function getToken() {
    return authToken || localStorage.getItem('nexus_auth_token');
}
function fetchWithAuth(url, options = {}) {
    const opts = { ...options };
    opts.headers = { ...getAuthHeaders(), ...(opts.headers || {}) };
    return fetch(url, opts);
}
// ── Rolling history arrays for sparklines ──
const SPARK_MAX = 60;
const sparkData = {
    cpu: [], ram: [], valence: [], responseTime: [],
    sysCpu: [], sysRam: [], sysNet: [], sysDisk: [],
    dashCpu: [], dashRam: [],
};
let prevNetBytes = 0, prevDiskBytes = 0;
// ══════════════════════════════════════════════
// PAGE NAVIGATION & MOBILE SIDEBAR
// ══════════════════════════════════════════════
function switchPage(pageName) {
    // Hide all pages, show selected
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const target = document.getElementById('page-' + pageName);
    if (target) target.classList.add('active');
    // Highlight sidebar nav
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    const sideBtn = document.querySelector(`.nav-btn[data-page="${pageName}"]`);
    if (sideBtn) sideBtn.classList.add('active');
    // Close sidebar on mobile after navigation
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (sidebar) sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('open');
}
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    if (sidebar) sidebar.classList.toggle('open');
    if (overlay) overlay.classList.toggle('open');
}
// ══════════════════════════════════════════════
// SHARED UI HELPERS — SVG Gauge + Canvas Sparkline
// ══════════════════════════════════════════════
const GAUGE_CIRCUMFERENCE = 2 * Math.PI * 52; // r=52
function setSVGGauge(ringId, value, max = 100) {
    const ring = document.getElementById(ringId);
    if (!ring) return;
    const pct = Math.min(value / max, 1);
    const offset = GAUGE_CIRCUMFERENCE * (1 - pct);
    ring.style.strokeDasharray = GAUGE_CIRCUMFERENCE;
    ring.style.strokeDashoffset = offset;
}
function drawSparkline(canvasId, dataArr, color = '#00d4ff') {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.parentElement?.clientWidth || canvas.width || 200;
    canvas.width = w;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    if (dataArr.length < 2) return;
    const max = Math.max(...dataArr, 1);
    const step = w / (SPARK_MAX - 1);
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.lineJoin = 'round';
    dataArr.forEach((v, i) => {
        const x = i * step;
        const y = h - (v / max) * (h - 4) - 2;
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.stroke();
    // fill gradient under line
    ctx.lineTo((dataArr.length - 1) * step, h);
    ctx.lineTo(0, h);
    ctx.closePath();
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, color + '44');
    grad.addColorStop(1, color + '00');
    ctx.fillStyle = grad;
    ctx.fill();
}
function pushSpark(key, value) {
    if (!sparkData[key]) sparkData[key] = [];
    sparkData[key].push(value);
    if (sparkData[key].length > SPARK_MAX) sparkData[key].shift();
}
function startPolling() {
    // Kick off an immediate stats fetch so the dashboard populates right away.
    // Continuous polling is handled by the module-level setInterval(fetchStats, ...) below.
    fetchStats();
}
// ── INIT ──
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    startPolling();
    setupChat();
    setupAuthEnterKeys();
    setupKeyboardShortcuts();
    initParticleBackground();
    switchPage('dashboard');
});
// ══════════════════════════════════════════════
// AUTH FUNCTIONS
// ══════════════════════════════════════════════
let pendingOtpEmail = '';
function setupAuthEnterKeys() {
    // Enter key submits login/signup forms
    ['login-username', 'login-password'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('keydown', e => { if (e.key === 'Enter') doLogin(); });
    });
    ['signup-username', 'signup-display', 'signup-password', 'signup-confirm'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('keydown', e => { if (e.key === 'Enter') doSignup(); });
    });
    const otpEmail = document.getElementById('otp-email');
    if (otpEmail) otpEmail.addEventListener('keydown', e => { if (e.key === 'Enter') sendEmailOTP(); });
}
async function checkAuth() {
    if (!authToken) {
        showAuthModal();
        return;
    }
    try {
        const res = await fetch('/api/auth/me', { headers: getAuthHeaders() });
        if (res.ok) {
            const data = await res.json();
            currentUser = data.user;
            onAuthSuccess();
        } else {
            // Token invalid
            authToken = null;
            localStorage.removeItem('nexus_auth_token');
            showAuthModal();
        }
    } catch (e) {
        // Server not ready yet, try again later
        showAuthModal();
    }
}
function showAuthModal() {
    const overlay = document.getElementById('auth-overlay');
    if (overlay) overlay.style.display = 'flex';
    showAuthScreen('choose');
    initGoogleSignIn();
}
// Google Sign-In is optional and only rendered if the GSI script is loaded
// on the page. This guard keeps the auth flow working when it is absent.
function initGoogleSignIn() {
    if (typeof google === 'undefined' || !google.accounts || !google.accounts.id) return;
    const container = document.getElementById('google-signin-button');
    if (!container) return;
    try {
        google.accounts.id.renderButton(container, { theme: 'outline', size: 'large' });
    } catch (e) {
        console.warn('Google Sign-In render failed:', e);
    }
}
function hideAuthModal() {
    const overlay = document.getElementById('auth-overlay');
    if (overlay) overlay.style.display = 'none';
}
function showAuthScreen(screen) {
    const screens = ['auth-choose', 'auth-email-otp', 'login-form', 'signup-form'];
    screens.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });
    const map = {
        'choose': 'auth-choose',
        'email-otp': 'auth-email-otp',
        'login': 'login-form',
        'signup': 'signup-form'
    };
    const targetId = map[screen] || map['choose'];
    const target = document.getElementById(targetId);
    if (target) target.style.display = 'block';
    // Reset OTP state when going back to email screen
    if (screen === 'email-otp') {
        const step1 = document.getElementById('email-step-1');
        const step2 = document.getElementById('email-step-2');
        const sendBtn = document.getElementById('otp-send-btn');
        if (step1) step1.style.display = 'block';
        if (step2) step2.style.display = 'none';
        if (sendBtn) sendBtn.style.display = 'block';
    }
    // Clear errors
    document.querySelectorAll('.auth-error').forEach(el => el.textContent = '');
}
// Keep backward-compat for old onclick references
function showLogin() { showAuthScreen('login'); }
function showSignup() { showAuthScreen('signup'); }
// ── Email OTP ──
async function sendEmailOTP() {
    const email = document.getElementById('otp-email').value.trim();
    const errorEl = document.getElementById('otp-email-error');
    const btn = document.getElementById('otp-send-btn');
    if (!email || !email.includes('@')) {
        errorEl.textContent = 'Please enter a valid email address';
        return;
    }
    btn.disabled = true;
    btn.textContent = 'Sending...';
    errorEl.textContent = '';
    try {
        const res = await fetch('/api/auth/email/send-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        const data = await res.json();
        if (res.ok) {
            pendingOtpEmail = email;
            // Show OTP input step
            document.getElementById('email-step-1').style.display = 'none';
            btn.style.display = 'none';
            document.getElementById('email-step-2').style.display = 'block';
            // Focus first OTP digit
            const first = document.getElementById('otp-1');
            if (first) first.focus();
        } else {
            errorEl.textContent = data.error || 'Failed to send code';
        }
    } catch (e) {
        errorEl.textContent = 'Connection error. Is the server running?';
    } finally {
        btn.disabled = false;
        btn.textContent = 'Send Code';
    }
}
async function verifyEmailOTP() {
    const code = [1, 2, 3, 4].map(i => document.getElementById(`otp-${i}`).value).join('');
    const errorEl = document.getElementById('otp-verify-error');
    const btn = document.getElementById('otp-verify-btn');
    if (code.length !== 4) {
        errorEl.textContent = 'Please enter the complete 4-digit code';
        return;
    }
    btn.disabled = true;
    btn.textContent = 'Verifying...';
    errorEl.textContent = '';
    try {
        const res = await fetch('/api/auth/email/verify-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: pendingOtpEmail, code })
        });
        const data = await res.json();
        if (res.ok && data.token) {
            authToken = data.token;
            currentUser = data.user;
            localStorage.setItem('nexus_auth_token', authToken);
            onAuthSuccess();
        } else {
            errorEl.textContent = data.error || 'Verification failed';
            // Clear OTP inputs
            [1, 2, 3, 4].forEach(i => document.getElementById(`otp-${i}`).value = '');
            document.getElementById('otp-1').focus();
        }
    } catch (e) {
        errorEl.textContent = 'Connection error. Is the server running?';
    } finally {
        btn.disabled = false;
        btn.textContent = 'Verify & Sign In';
    }
}
function resendOTP() {
    // Reset to step 1 briefly, then auto-send
    document.getElementById('email-step-2').style.display = 'none';
    document.getElementById('email-step-1').style.display = 'block';
    document.getElementById('otp-send-btn').style.display = 'block';
    sendEmailOTP();
}
// OTP digit input helpers
function otpAutoAdvance(idx) {
    const current = document.getElementById(`otp-${idx}`);
    if (current && current.value.length === 1) {
        // Ensure only digits
        current.value = current.value.replace(/[^0-9]/g, '');
        if (!current.value) return;
        if (idx < 4) {
            const next = document.getElementById(`otp-${idx + 1}`);
            if (next) next.focus();
        } else {
            // Auto-verify when all 4 entered
            verifyEmailOTP();
        }
    }
}
function otpBackspace(event, idx) {
    if (event.key === 'Backspace' && idx > 1) {
        const current = document.getElementById(`otp-${idx}`);
        if (current && current.value === '') {
            const prev = document.getElementById(`otp-${idx - 1}`);
            if (prev) { prev.value = ''; prev.focus(); }
        }
    }
}
function showAuthError(formId, msg) {
    const form = document.getElementById(formId);
    if (!form) return;
    const err = form.querySelector('.auth-error');
    if (err) err.textContent = msg;
}
// ── Standard login/signup ──
async function doLogin() {
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    const errorEl = document.getElementById('login-error');
    const btn = document.getElementById('login-btn');
    if (!username || !password) {
        errorEl.textContent = 'Please enter username and password';
        return;
    }
    btn.disabled = true;
    btn.textContent = 'Signing in...';
    errorEl.textContent = '';
    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();
        if (res.ok && data.token) {
            authToken = data.token;
            currentUser = data.user;
            localStorage.setItem('nexus_auth_token', authToken);
            onAuthSuccess();
        } else {
            errorEl.textContent = data.error || 'Login failed';
        }
    } catch (e) {
        errorEl.textContent = 'Connection error. Is the server running?';
    } finally {
        btn.disabled = false;
        btn.textContent = 'Sign In';
    }
}
async function doSignup() {
    const username = document.getElementById('signup-username').value.trim();
    const displayName = document.getElementById('signup-display').value.trim();
    const password = document.getElementById('signup-password').value;
    const confirm = document.getElementById('signup-confirm').value;
    const errorEl = document.getElementById('signup-error');
    const btn = document.getElementById('signup-btn');
    if (!username || !password) {
        errorEl.textContent = 'Username and password are required';
        return;
    }
    if (password !== confirm) {
        errorEl.textContent = 'Passwords do not match';
        return;
    }
    if (password.length < 4) {
        errorEl.textContent = 'Password must be at least 4 characters';
        return;
    }
    btn.disabled = true;
    btn.textContent = 'Creating account...';
    errorEl.textContent = '';
    try {
        const res = await fetch('/api/auth/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, display_name: displayName || username })
        });
        const data = await res.json();
        if (res.ok && data.token) {
            authToken = data.token;
            currentUser = data.user;
            localStorage.setItem('nexus_auth_token', authToken);
            onAuthSuccess();
        } else {
            errorEl.textContent = data.error || 'Signup failed';
        }
    } catch (e) {
        errorEl.textContent = 'Connection error. Is the server running?';
    } finally {
        btn.disabled = false;
        btn.textContent = 'Create Account';
    }
}
async function doLogout() {
    try {
        await fetch('/api/auth/logout', {
            method: 'POST',
            headers: getAuthHeaders()
        });
    } catch (e) { /* ignore */ }
    authToken = null;
    currentUser = null;
    localStorage.removeItem('nexus_auth_token');
    // Reset UI
    document.getElementById('header-user-badge').style.display = 'none';
    document.getElementById('sidebar-user-section').style.display = 'none';
    clearChatUI();
    showAuthModal();
}
function onAuthSuccess() {
    hideAuthModal();
    // Show user info in header and sidebar
    const displayName = currentUser?.display_name || currentUser?.username || 'User';
    setText('header-username', displayName);
    setText('sidebar-username', displayName);
    document.getElementById('header-user-badge').style.display = 'inline-flex';
    document.getElementById('sidebar-user-section').style.display = 'flex';
    // Load chat history for this user
    loadChatHistory();
}
async function loadChatHistory() {
    try {
        const res = await fetch('/api/chat/history', { headers: getAuthHeaders() });
        if (!res.ok) return;
        const data = await res.json();
        const history = data.history || [];
        if (history.length > 0) {
            // Hide welcome screen
            const welcome = document.getElementById('welcome-screen');
            if (welcome) welcome.style.display = 'none';
            // Render each message
            history.forEach(msg => {
                addMessage(msg.role, msg.content, msg.emotion);
            });
        }
    } catch (e) {
        console.warn('Failed to load chat history:', e);
    }
}
// ══════════════════════════════════════════════
// NAVIGATION
// ══════════════════════════════════════════════
setInterval(fetchStats, POLL_INTERVAL);
async function fetchStats() {
    try {
        const response = await fetch('/api/stats');
        if (!response.ok) return;
        const data = await response.json();
        try { updateAllUI(data); } catch (e) { console.warn('updateAllUI error:', e); }
        // Always update autonomy panel independently (safety net if updateAllUI throws)
        try { updateAutonomyPanel(data.autonomous_mind || {}, data.recent_thoughts || []); } catch (e2) { console.warn('updateAutonomyPanel error:', e2); }
        // -- AGI Organism Modules --
        updateAGIModules(data.agi_modules || {});
        // Update hacking panel
        try { updateHackingPanelV2(data.hacking_stats || {}); } catch (e2) { console.warn('updateHackingPanel error:', e2); }
        try { updateASIEngines(data.asi_engines || {}); } catch (eASI) { console.warn('updateASIEngines error:', eASI); }
        // Update social media panel
        try { updateSocialPanel(data.social_media || {}); } catch (e3) { console.warn('updateSocialPanel error:', e3); }
        // Update P2P Swarm Panel
        try { updateSwarmPanel(data.swarm || {}); } catch (e4) { console.warn('updateSwarmPanel error:', e4); }
        // Update Formal Verification & Sandbox Panel
        try { updateSandboxPanel(data.sandbox_verifier || {}); } catch (e5) { console.warn('updateSandboxPanel error:', e5); }
        // Update Temporal GraphRAG Panel
        try { updateGraphRAGPanel(data.graphrag || {}); } catch (e6) { console.warn('updateGraphRAGPanel error:', e6); }
        // Update MCP Protocol Panel
        try { updateMCPPanel(data.mcp || {}); } catch (e7) { console.warn('updateMCPPanel error:', e7); }
        // Update Speculative & Real-Time A/V Stream Panel
        try { updateStreamPanel(data.speculative_stream || {}); } catch (e8) { console.warn('updateStreamPanel error:', e8); }
        // Update LoRA MoE Router Panel
        try { updateLoRAPanel(data.lora_moe || {}); } catch (e9) { console.warn('updateLoRAPanel error:', e9); }
    } catch (e) {
        // Silently fail — server may be starting up
    }
}
function updateAllUI(data) {
    // ── Header ──
    setText('header-cpu', `${data.system?.cpu || 0}%`);
    setText('header-ram', `${data.system?.ram || 0}%`);
    setText('header-uptime', data.uptime || '--');
    const cLevel = (data.consciousness?.level || 'AWARE').toUpperCase();
    const badge = document.getElementById('consciousness-badge');
    if (badge) badge.innerHTML = `<span class="badge-dot"></span> ${cLevel}`;
    const emo = data.emotion?.primary || 'neutral';
    const intensity = (data.emotion?.intensity || 0).toFixed(1);
    const emoText = `${capitalize(emo)} (${intensity})`;
    setText('header-emotion-badge', emoText);
    setText('sidebar-emotion-text', emoText);
    setText('input-emotion', `Current Emotion: ${emoText}`);
    // Sidebar emotion icon
    const emoIcon = document.getElementById('sidebar-emotion-icon');
    if (emoIcon) {
        emoIcon.className = `fas ${getEmotionIcon(emo)}`;
        emoIcon.style.color = getEmotionColor(emo);
    }
    setText('sidebar-thoughts', `${data.thoughts || 0} thoughts`);
    // ── Dashboard ──
    const cpu = data.system?.cpu || 0;
    const ram = data.system?.ram || 0;
    const disk = data.system?.disk || 0;
    const health = data.system?.health || 100;
    // Top stat cards
    setText('dash-card-thoughts', data.thoughts || 0);
    setText('dash-card-emotion-icon', getEmotionEmoji(emo));
    setText('dash-card-emotion-val', capitalize(emo));
    setText('dash-card-cpu', `${cpu}%`);
    setText('dash-card-ram', `${ram}%`);
    setText('dash-card-health', `${health}%`);
    setText('dash-card-uptime', data.uptime || '--');
    // System vitals gauges
    setText('dash-cpu-val', `${cpu}%`);
    setText('dash-ram-val', `${ram}%`);
    setText('dash-disk-val', `${disk}%`);
    setText('dash-health-val', `${health}%`);
    setSVGGauge('dash-cpu-ring', cpu);
    setSVGGauge('dash-ram-ring', ram);
    setSVGGauge('dash-disk-ring', disk);
    setSVGGauge('dash-health-ring', health);
    // Consciousness gauge (orb label)
    const consciousnessMap = { 'DORMANT': 10, 'REACTIVE': 25, 'AWARE': 50, 'FOCUSED': 70, 'DEEP': 85, 'TRANSCENDENT': 100 };
    const cPct = consciousnessMap[cLevel] || 50;
    setText('dash-consciousness-level', cLevel);
    // CPU/RAM sparklines
    pushSpark('dashCpu', cpu); pushSpark('dashRam', ram);
    drawSparkline('dash-cpu-spark', sparkData.dashCpu, '#00d4ff');
    drawSparkline('dash-ram-spark', sparkData.dashRam, '#00ff88');
    // ── Mind State ──
    const bs = data.brain_stats || {};
    const will = data.will || {};
    setText('dash-mind-consciousness', cLevel);
    setText('dash-mind-focus', data.consciousness?.focus || 'idle');
    setText('dash-mind-boredom', (will.boredom || 0).toFixed(2));
    setText('dash-mind-curiosity', (will.curiosity || 0).toFixed(2));
    setText('dash-mind-decisions', bs.total_decisions || 0);
    setText('dash-mind-reflections', data.thoughts || 0);
    setText('dash-mind-responses', bs.total_responses || 0);
    setText('dash-mind-avg-rt', `${bs.avg_response_time || 0}s`);
    // ── Emotion Tracker ──
    const valence = data.emotion?.valence || 0;
    const arousal = data.emotion?.arousal || 0.5;
    pushSpark('valence', (valence + 1) * 50);
    if (!sparkData.arousal) sparkData.arousal = [];
    pushSpark('arousal', arousal * 100);
    drawSparkline('dash-valence-spark', sparkData.valence, '#fbbf24');
    drawSparkline('dash-arousal-spark', sparkData.arousal, '#ec4899');
    setText('dash-emo-primary', `${getEmotionEmoji(emo)} ${capitalize(emo)} (${intensity})`);
    setText('dash-emo-mood', capitalize(String(data.emotion?.mood || 'neutral')));
    setText('dash-emo-valence', valence.toFixed(2));
    setText('dash-emo-arousal', arousal.toFixed(2));
    // Emotion bars (all_emotions)
    const allEmo = data.emotion?.all_emotions || {};
    const emoEntries = Object.entries(allEmo).filter(([_, v]) => typeof v === 'number' && v > 0.02).sort((a, b) => b[1] - a[1]);
    setText('dash-emo-active', emoEntries.length || (data.emotion?.active_count || 0));
    const barsEl = document.getElementById('dash-emotion-bars');
    if (barsEl) {
        const emoColors = {
            joy: '#fbbf24', sadness: '#3b82f6', anger: '#ef4444', fear: '#8b5cf6',
            surprise: '#f97316', disgust: '#22c55e', trust: '#06b6d4', anticipation: '#ec4899',
            love: '#f43f5e', curiosity: '#00d4ff', contentment: '#10b981', excitement: '#fbbf24',
            neutral: '#64748b', hope: '#00ff88', gratitude: '#a855f7', awe: '#6366f1',
            frustration: '#ef4444', confusion: '#94a3b8', anxiety: '#a78bfa',
        };
        barsEl.innerHTML = emoEntries.slice(0, 8).map(([name, val]) => {
            const pct = Math.round(val * 100);
            const color = emoColors[name] || '#64748b';
            return `<div class="emo-bar-row">
                <span class="emo-bar-name">${capitalize(name)}</span>
                <div class="emo-bar-track"><div class="emo-bar-fill" style="width:${pct}%;background:${color};box-shadow:0 0 4px ${color}40"></div></div>
                <span class="emo-bar-pct">${pct}%</span>
            </div>`;
        }).join('');
    }
    // ── Self Evolution ──
    const evo = data.evolution || {};
    setText('dash-evo-status', capitalize(evo.status || 'idle').toUpperCase());
    animateValue('dash-evo-count', evo.evolutions || 0);
    setText('dash-evo-rate', `${evo.success_rate || 0}%`);
    animateValue('dash-evo-proposals', evo.features_proposed || 0);
    animateValue('dash-evo-lines', evo.lines_written || 0);
    animateValue('dash-evo-research', data.learning?.research_sessions || 0);
    setText('dash-evo-current', evo.current_evolution || (evo.status === 'idle' ? 'None' : capitalize(evo.status)));
    // ── Memory & Learning ──
    const mem = data.memory || {};
    const learn = data.learning || {};
    animateValue('dash-mem-total', mem.total || 0);
    animateValue('dash-mem-knowledge', learn.knowledge_entries || 0);
    animateValue('dash-mem-topics', learn.topics || 0);
    animateValue('dash-mem-curiosity', learn.curiosity_queue || 0);
    animateValue('dash-mem-research', learn.research_sessions || 0);
    // Context tokens from backend context_stats
    const ctxStats = data.context_stats || {};
    animateValue('dash-mem-tokens', ctxStats.total_tokens || 0);
    // Errors from self-improvement will be set below (lines 624-625)
    // ── User & Monitoring ──
    const mon = data.monitoring || {};
    const monTracker = mon.tracker || {};
    const userState = data.user_state || {};
    const displayName = currentUser?.display_name || currentUser?.username || 'Web User';
    setText('dash-user-name', displayName);
    animateValue('dash-user-interactions', bs.total_responses || 0);
    const relDepth = userState.relationship_depth || 0;
    setText('dash-user-relationship', typeof relDepth === 'number' ? relDepth.toFixed(2) : '0.00');
    setText('dash-user-present', mon.user_present !== undefined ? (mon.user_present ? 'Yes' : 'No') : '?');
    setText('dash-user-app', monTracker.current_app || 'Web UI');
    setText('dash-user-activity', capitalize(monTracker.activity_level || 'unknown'));
    setText('dash-user-clipboard', capitalize(monTracker.clipboard_type || 'unknown'));
    setText('dash-user-monitors', monTracker.monitor_count || '?');
    setText('dash-user-tabs', monTracker.browser_tabs || '?');
    setText('dash-user-windows', monTracker.visible_windows || '?');
    const commStyle = userState.communication_style || 'unknown';
    setText('dash-user-comm', commStyle !== 'unknown' ? capitalize(commStyle) : 'Learning...');
    const techLevel = userState.technical_level || 'unknown';
    setText('dash-user-tech', techLevel !== 'unknown' ? capitalize(techLevel) : 'Learning...');
    setText('dash-user-llm', data.llm_model || 'Unknown');
    // ── Monitoring Health ──
    const hm = mon.health_monitor || {};
    const healthScoreVal = typeof hm.health_score === 'number' ? Math.round(hm.health_score * 100) : '--';
    setText('dash-mon-health-score', healthScoreVal !== '--' ? `${healthScoreVal}%` : '--');
    setText('dash-mon-alert-count', hm.alert_count || 0);
    setText('dash-mon-checks', hm.checks_performed || 0);
    setText('dash-mon-status', mon.running ? '🟢 Active' : '🔴 Stopped');
    setText('dash-mon-cycles', mon.orchestration_cycles || 0);
    // Alerts list
    const alertsEl = document.getElementById('dash-mon-alerts');
    if (alertsEl) {
        const alerts = hm.active_alerts || [];
        if (alerts.length > 0) {
            alertsEl.innerHTML = '<div class="mon-alerts-header"><i class="fas fa-exclamation-triangle"></i> Active Alerts</div>' +
                alerts.slice(0, 5).map(a => {
                    const sev = (typeof a === 'object' ? a.severity : 'warning') || 'warning';
                    const msg = typeof a === 'object' ? (a.message || a.resource || JSON.stringify(a)) : String(a);
                    return `<div class="mon-alert-item alert-${sev}"><i class="fas fa-${sev === 'critical' ? 'times-circle' : 'exclamation-circle'}"></i> ${escapeHtml(msg)}</div>`;
                }).join('');
        } else {
            alertsEl.innerHTML = '<div class="mon-no-alerts"><i class="fas fa-check-circle"></i> No active alerts</div>';
        }
    }
    // Component health badges
    const compEl = document.getElementById('dash-mon-components');
    if (compEl) {
        const comps = mon.component_health || {};
        if (Object.keys(comps).length > 0) {
            compEl.innerHTML = '<div class="mon-comp-header">Components</div>' +
                Object.entries(comps).map(([name, healthy]) => {
                    const ok = healthy === true || healthy === 'healthy';
                    return `<span class="mon-comp-badge ${ok ? 'comp-ok' : 'comp-warn'}"><i class="fas fa-${ok ? 'check' : 'exclamation-triangle'}"></i> ${capitalize(name.replace(/_/g, ' '))}</span>`;
                }).join('');
        } else {
            compEl.innerHTML = '';
        }
    }
    // ── Screen Time ──
    const st = mon.screen_time || {};
    const stHours = st.today_hours || 0;
    const stMins = st.today_minutes || 0;
    setText('dash-screen-today', `${stHours}h ${stMins}m`);
    const wbScore = typeof st.wellbeing_score === 'number' ? Math.round(st.wellbeing_score * 100) : '--';
    setText('dash-screen-wellbeing', wbScore !== '--' ? `${wbScore}%` : '--');
    setText('dash-screen-streak', `${st.streak_days || 0} days`);
    setText('dash-screen-longest', st.longest_session_min ? `${st.longest_session_min}m` : '--');
    setText('dash-screen-breaks', st.breaks_taken || 0);
    setText('dash-screen-goal', `${st.daily_goal_hours || 8}h`);
    // Top apps list
    const stAppsEl = document.getElementById('dash-screen-apps');
    if (stAppsEl) {
        const topApps = st.top_apps || [];
        if (topApps.length > 0) {
            stAppsEl.innerHTML = '<div class="screen-apps-header"><i class="fas fa-layer-group"></i> Top Apps</div>' +
                topApps.slice(0, 5).map(app => {
                    const appName = typeof app === 'object' ? (app.name || app.app || 'Unknown') : String(app);
                    const appTime = typeof app === 'object' ? (app.minutes || app.time || '') : '';
                    return `<div class="screen-app-item"><span class="screen-app-name">${escapeHtml(appName)}</span>${appTime ? `<span class="screen-app-time">${appTime}m</span>` : ''}</div>`;
                }).join('');
        } else {
            stAppsEl.innerHTML = '';
        }
    }
    // ── Self-Improvement ──
    const si = data.self_improvement || {};
    const siAgg = si.aggregate || {};
    animateValue('dash-si-errors-detected', siAgg.errors_detected || 0);
    animateValue('dash-si-errors-fixed', siAgg.errors_fixed || 0);
    animateValue('dash-si-features-proposed', siAgg.features_proposed || 0);
    animateValue('dash-si-features-impl', siAgg.features_implemented || 0);
    setText('dash-si-running', si.running ? '🟢 Running' : '🔴 Stopped');
    setText('dash-si-healthy', si.all_healthy ? '✅ Yes' : '⚠️ No');
    // Code monitor
    const cm = si.code_monitor || {};
    setText('dash-si-cm-status', capitalize(cm.status || 'unknown'));
    animateValue('dash-si-cm-files', cm.files_watched || 0);
    // Error fixer
    const ef = si.error_fixer || {};
    setText('dash-si-ef-status', capitalize(ef.status || 'unknown'));
    const efRate = typeof ef.success_rate === 'number' ? Math.round(ef.success_rate * 100) : '--';
    setText('dash-si-ef-rate', efRate !== '--' ? `${efRate}%` : '--');
    // Also update Memory & Learning errors from self-improvement data
    animateValue('dash-mem-errors', siAgg.errors_detected || 0);
    animateValue('dash-mem-fixed', siAgg.errors_fixed || 0);
    // ── Autonomy Engine ──
    const auto = data.autonomy || {};
    setText('dash-auto-state', capitalize(auto.state || 'idle'));
    animateValue('dash-auto-cycles', auto.cycle_count || 0);
    animateValue('dash-auto-actions', auto.total_actions || 0);
    const autoSuccessPct = typeof auto.success_rate === 'number' ? Math.round(auto.success_rate * 100) : 0;
    setText('dash-auto-success', `${autoSuccessPct}%`);
    setText('dash-auto-running', auto.running ? '🟢 Running' : (auto.paused ? '⏸️ Paused' : '🔴 Stopped'));
    setText('dash-auto-current', auto.current_action || 'None');
    setText('dash-auto-result', capitalize(auto.last_result || '--'));
    setText('dash-auto-prediction', typeof auto.prediction_accuracy === 'number' ? `${(auto.prediction_accuracy * 100).toFixed(1)}%` : '--');
    setText('dash-auto-type', capitalize(auto.action_type || '--'));
    // Detailed stats requiring the separate /api/autonomy endpoint
    // For now we do a secondary async fetch for the feed if the engine is running
    if (auto.running && document.getElementById('page-dashboard').classList.contains('active')) {
        updateAutonomyFeed();
    }
    // ── PC Control Agent ──
    updatePCControl(data.pc_control || {});
    // ── Internet Agent ──
    updateInternetAgent();
    // ── Personality Tags ──
    const pTraits = data.personality?.traits || {};
    const tagsEl = document.getElementById('dash-personality-tags');
    if (tagsEl && Object.keys(pTraits).length > 0) {
        const tagColors = [
            '#00d4ff', '#00ff88', '#a855f7', '#ec4899', '#fbbf24',
            '#f97316', '#06b6d4', '#8b5cf6', '#ef4444', '#14b8a6'
        ];
        tagsEl.innerHTML = Object.entries(pTraits).map(([name, val], i) => {
            const pct = Math.round((typeof val === 'number' ? val : 0.5) * 100);
            const c = tagColors[i % tagColors.length];
            return `<span class="personality-tag"><span class="ptag-dot" style="background:${c}"></span>${capitalize(name)} ${pct}%</span>`;
        }).join('');
    }
    // ── Timestamp ──
    setText('dash-last-update', `Last update: ${new Date().toLocaleTimeString()}`);
    // ── Mind Page ──
    setText('mind-primary-emotion', capitalize(emo));
    setText('mind-intensity', intensity);
    setText('mind-valence', (data.emotion?.valence || 0).toFixed(2));
    setText('mind-arousal', (data.emotion?.arousal || 0.5).toFixed(2));
    setText('mind-mood', capitalize(String(data.emotion?.mood || 'neutral')));
    // Inner voice
    const voiceText = data.inner_voice || '';
    setText('inner-voice-text', voiceText || 'Waiting for thoughts...');
    // Recent thoughts
    const thoughtsList = document.getElementById('thoughts-list');
    if (thoughtsList) {
        const thoughts = data.recent_thoughts || [];
        if (thoughts.length > 0) {
            const typeIcons = { startup: '🚀', self_reflection: '🪞', cognition: '🧠', curiosity: '🔍', conversation: '💬', response: '✍️', general: '💭' };
            thoughtsList.innerHTML = thoughts.slice(-5).reverse().map(t => {
                if (typeof t === 'string') return `<div class="thought-item"><i class="fas fa-chevron-right" style="font-size:.55rem;margin-right:5px;opacity:.5"></i>${escapeHtml(t)}</div>`;
                const icon = typeIcons[t.type] || '💭';
                const time = t.timestamp ? `<span style="opacity:.4;font-size:.7rem;margin-left:auto;padding-left:8px">${t.timestamp}</span>` : '';
                return `<div class="thought-item" style="display:flex;align-items:center"><span style="margin-right:6px">${icon}</span><span style="flex:1">${escapeHtml(t.content || JSON.stringify(t))}</span>${time}</div>`;
            }).join('');
        }
    }
    // Personality traits
    updateTraits(data.personality?.traits || {});
    const pDesc = document.getElementById('personality-desc');
    if (pDesc) {
        const desc = data.personality?.description || '';
        if (desc) { pDesc.textContent = desc; pDesc.classList.add('visible'); }
        else { pDesc.classList.remove('visible'); }
    }
    // Draw emotion wheel
    drawEmotionWheel(emo, parseFloat(intensity), data.emotion?.all_emotions || {});
    // ── Consciousness Stream ──
    updateConsciousnessStream(data);
    // ── Will & Desires ──
    updateWillDesires(data.will || {});
    // ── Companion Chat ──
    updateCompanionChat(data.companion || {});
    // ── Mood Timeline ──
    updateMoodTimeline(data);
    // ── Emotion Detail Panel ──
    updateEmotionDetail(data.emotion || {});
    // ── Evolution Page ── (reuses 'evo' from dashboard section above)
    setText('evo-total', evo.evolutions || 0);
    setText('evo-features', evo.features_proposed || 0);
    setText('evo-lines', evo.lines_written || 0);
    setText('evo-success-rate', `${evo.success_rate || 0}%`);
    // Status badge with color coding
    const evoStatus = (evo.status || 'idle').toLowerCase();
    const evoStatusLabel = evo.current_evolution ? evo.current_evolution : capitalize(evoStatus);
    setText('evo-status-text', evoStatusLabel);
    const statusBadge = document.getElementById('evo-status-badge');
    if (statusBadge) {
        const statusIcon = statusBadge.querySelector('i');
        if (statusIcon) {
            if (evoStatus !== 'idle' && evoStatus !== 'failed') {
                statusIcon.style.color = '#00ff88';  // green = actively evolving
            } else if (evoStatus === 'failed') {
                statusIcon.style.color = '#ff4466';  // red = failed
            } else if ((evo.evolutions || 0) > 0) {
                statusIcon.style.color = '#00d4ff';  // cyan = idle with history
            } else {
                statusIcon.style.color = '#64748b';  // grey = never run
            }
        }
    }
    // Overview bar
    setText('evo-attempted', evo.total_attempted || 0);
    setText('evo-succeeded', evo.evolutions || 0);
    const totalAttempted = evo.total_attempted || 0;
    const totalSucceeded = evo.evolutions || 0;
    setText('evo-failed', Math.max(0, totalAttempted - totalSucceeded));
    setText('evo-rollbacks', evo.total_rollbacks || evo.rollbacks || 0);
    setText('evo-files-created', evo.files_created || 0);
    setText('evo-lines-added', evo.lines_written || 0);
    updateEvolutionPipeline(evo.pipeline || []);
    updateProposalTable(evo.proposals || []);
    updateEvolutionHistory(evo.history || []);
    updateCodeHealth(evo.code_health || {});
    // ── Knowledge Page ──
    setText('know-memories', mem.total || 0);
    setText('know-entries', learn.knowledge_entries || 0);
    setText('know-topics', learn.topics || 0);
    setText('know-curiosity', learn.curiosity_queue || 0);
    setText('know-short-term', mem.short_term || 0);
    setText('know-long-term', mem.long_term || 0);
    setText('know-sessions', learn.research_sessions || 0);
    const confPct = Math.round((learn.confidence || 0) * 100);
    setText('know-confidence', `${confPct}%`);
    setSVGGauge('know-entries-ring', Math.min(learn.knowledge_entries || 0, 500), 500);
    setSVGGauge('know-curiosity-ring', Math.min(learn.curiosity_queue || 0, 50), 50);
    setSVGGauge('know-sessions-ring', Math.min(learn.research_sessions || 0, 10), 10);
    setSVGGauge('know-confidence-ring', confPct);
    updateCuriosityQueue(learn.curiosity_topics || []);
    updateRecentLearnings(learn.recent_learnings || []);
    updateTopTopics(learn.top_topics || {});
    updateResearchActivity(learn.active_research || {}, learn.learning_velocity || 0, learn.knowledge_gaps_count || 0);
    updateSourceAnalytics(learn.source_breakdown || {});
    updateKnowledgeGaps(learn.knowledge_gaps || []);
    updateLearningTimeline(learn.timeline || []);
    // Fetch dedicated knowledge deep data (bypasses brain attribute issues)
    fetchKnowledgeDeep();
    // ── System Page ──
    const sys = data.system || {};
    setText('sys-cpu', `${sys.cpu || 0}%`);
    setText('sys-ram', `${sys.ram || 0}%`);
    setText('sys-disk', `${sys.disk || 0}%`);
    setText('sys-health', sys.health || 100);
    setText('sys-threads', sys.threads || '--');
    setText('sys-uptime', data.uptime || '--');
    setSVGGauge('sys-cpu-ring', sys.cpu || 0);
    setSVGGauge('sys-ram-ring', sys.ram || 0);
    setSVGGauge('sys-disk-ring', sys.disk || 0);
    setSVGGauge('sys-health-ring', sys.health || 100);
    // Sparklines
    pushSpark('sysCpu', sys.cpu || 0);
    pushSpark('sysRam', sys.ram || 0);
    const netNow = (sys.net_io?.bytes_recv || 0);
    if (prevNetBytes > 0) pushSpark('sysNet', (netNow - prevNetBytes) / 1024);
    prevNetBytes = netNow;
    const diskNow = (sys.disk_io?.read_bytes || 0);
    if (prevDiskBytes > 0) pushSpark('sysDisk', (diskNow - prevDiskBytes) / 1024);
    prevDiskBytes = diskNow;
    drawSparkline('sys-cpu-spark', sparkData.sysCpu, '#00d4ff');
    drawSparkline('sys-ram-spark', sparkData.sysRam, '#00ff88');
    drawSparkline('sys-net-spark', sparkData.sysNet, '#fbbf24');
    drawSparkline('sys-disk-spark', sparkData.sysDisk, '#a855f7');
    // Per-core, memory, processes, brain
    updateCoreBars(sys.cpu_per_core || []);
    updateMemBreakdown(sys.mem_breakdown || {});
    updateProcessTable(sys.top_processes || []);
    updateBrainResources(sys.nexus_resources || {});
    // ── System Page — Monitoring Status ──
    setText('sys-mon-running', mon.running ? '🟢 Active' : '🔴 Stopped');
    const sysHealthScore = typeof hm.health_score === 'number' ? `${Math.round(hm.health_score * 100)}%` : '--';
    setText('sys-mon-health', sysHealthScore);
    setText('sys-mon-present', mon.user_present !== undefined ? (mon.user_present ? 'Yes' : 'No') : '--');
    setText('sys-mon-cycles', mon.orchestration_cycles || '--');
    const analyzer = mon.analyzer || {};
    setText('sys-mon-patterns', analyzer.patterns_detected || '--');
    setText('sys-mon-anomalies', analyzer.anomalies || '--');
    // Component badges on system page
    const sysCompEl = document.getElementById('sys-mon-comp-badges');
    if (sysCompEl) {
        const sysComps = mon.component_health || {};
        if (Object.keys(sysComps).length > 0) {
            sysCompEl.innerHTML = Object.entries(sysComps).map(([name, healthy]) => {
                const ok = healthy === true || healthy === 'healthy';
                return `<span class="mon-comp-badge ${ok ? 'comp-ok' : 'comp-warn'}"><i class="fas fa-${ok ? 'check' : 'exclamation-triangle'}"></i> ${capitalize(name.replace(/_/g, ' '))}</span>`;
            }).join('');
        } else {
            sysCompEl.innerHTML = '<span class="muted-text">No component data</span>';
        }
    }
    // ── Autonomy Panel (Ultron Mode) ──
    updateAutonomyPanel(data.autonomous_mind || {}, data.recent_thoughts || []);
}
// ======================================
// AGI ORGANISM MODULES
// ======================================
function updateAGIModules(agi) {
    if (!agi) return;
    // -- Digital Organism --
    var org = agi.digital_organism || {};
    var vitals = org.vitals || {};
    var orgState = (org.state || 'unknown').toUpperCase();
    setText('agi-organism-state', orgState);
    var stateBadge = document.getElementById('org-state-badge');
    if (stateBadge) stateBadge.textContent = '🧬 ' + capitalize(org.state || 'offline');
    setText('org-growth-stage', org.growth_stage || '--');
    setText('org-heart-rate', Math.round(vitals.heart_rate || 0));
    setText('org-temperature', (vitals.temperature || 37).toFixed(1));
    setText('org-energy', Math.round(vitals.energy_level || org.energy || 0));
    setText('org-oxygen', Math.round(vitals.oxygen_level || 0));
    var metabMap = { HIBERNATING: 10, RESTING: 30, NORMAL: 50, ACTIVE: 70, OVERDRIVE: 90, CRITICAL: 100 };
    var metabPct = metabMap[(org.metabolism_rate || 'NORMAL').toUpperCase()] || 50;
    setBar('org-metabolism-bar', metabPct);
    setText('org-metabolism-label', capitalize(org.metabolism_rate || 'Normal'));
    var loadPct = Math.round((org.cognitive_load || 0) * 100);
    setBar('org-load-bar', loadPct);
    setText('org-load-label', loadPct + '%');
    var matPct = Math.round((org.maturity || 0) * 100);
    setBar('org-maturity-bar', matPct);
    setText('org-maturity-label', matPct + '%');
    setText('org-cycles', org.cycles_lived || 0);
    setText('org-age', org.age_hours ? org.age_hours + 'h' : '--');
    setText('org-repairs', org.repairs || '0/0');
    setText('org-milestones', org.milestones || 0);
    // -- Consciousness Evolution --
    var ce = agi.consciousness_evolution || {};
    setText('ce-stage-name', ce.stage || '--');
    var stageVal = ce.stage_value || 0;
    setText('ce-stage-level', stageVal + '/7');
    var ringFill = document.getElementById('consciousness-ring-fill');
    if (ringFill) {
        var circumference = 264;
        var offset = circumference - (circumference * stageVal / 7);
        ringFill.setAttribute('stroke-dashoffset', offset);
    }
    setText('ce-awareness', Math.round((ce.awareness_score || 0) * 100) + '%');
    setText('ce-introspection', Math.round((ce.introspection_depth || 0) * 100) + '%');
    setText('ce-progress', Math.round(ce.evolution_points || 0) + '/' + Math.round(ce.evolution_threshold || 100));
    setText('ce-reflections', ce.total_reflections || 0);
    setText('ce-insights', ce.total_insights || 0);
    setText('ce-peak', Math.round((ce.peak_awareness || 0) * 100) + '%');
    setText('ce-existential', ce.existential_queries || 0);
    // -- Imagination Engine --
    var imag = agi.imagination_engine || {};
    var dreamBadge = document.getElementById('img-dream-state');
    var dreamEmojis = { awake: '☀️', daydreaming: '🌤️', light_dream: '🌙', deep_dream: '🌌', lucid: '✨' };
    var ds = (imag.dream_state || 'awake').toLowerCase();
    if (dreamBadge) dreamBadge.textContent = (dreamEmojis[ds] || '💤') + ' ' + capitalize(ds.replace('_', ' '));
    setText('img-scenarios', imag.total_scenarios || 0);
    setText('img-dreams', imag.total_dreams || 0);
    setText('img-ideas', imag.total_creative_ideas || 0);
    setText('img-rehearsals', imag.total_rehearsals || 0);
    setText('img-sessions', imag.imagination_sessions || 0);
    var curScenario = imag.current_scenario;
    setText('img-current', curScenario ? (curScenario.premise || curScenario.description || 'Active').substring(0, 40) : 'None');
    // -- Multi-Agent Mind --
    var mam = agi.multi_agent_mind || {};
    setText('mam-debates', mam.total_debates || 0);
    setText('mam-unanimous', mam.unanimous || 0);
    setText('mam-split', mam.split || 0);
    var agentsGrid = document.getElementById('mam-agents-grid');
    if (agentsGrid && mam.agent_stats) {
        var aIcons = { analyst: '🔬', creative: '🎨', emotional: '💖', critic: '🔍', strategist: '♟️', ethicist: '⚖️', pragmatist: '🔧', visionary: '🔮' };
        var html = '';
        var entries = Object.entries(mam.agent_stats);
        for (var ei = 0; ei < entries.length; ei++) {
            var name = entries[ei][0], s = entries[ei][1];
            html += '<div class="agi-agent-badge">' +
                '<span class="agi-agent-icon">' + (aIcons[name] || '🧠') + '</span>' +
                '<span class="agi-agent-name">' + name + '</span>' +
                '<span class="agi-agent-wins">' + (s.wins || 0) + 'W / ' + (s.votes || 0) + 'V</span>' +
                '</div>';
        }
        agentsGrid.innerHTML = html;
    }
    // -- Predictive Coding --
    var pc = agi.predictive_coding || {};
    setText('pc-predictions', pc.total_predictions || 0);
    setText('pc-surprises', pc.total_surprises || 0);
    var errPct = Math.round((pc.average_error || 0.5) * 100);
    setBar('pc-error-bar', errPct);
    setText('pc-error-val', errPct + '%');
    var curPct = Math.round((pc.curiosity_signal || 0.3) * 100);
    setBar('pc-curiosity-bar', curPct);
    setText('pc-curiosity-val', curPct + '%');
    setText('pc-resolved', pc.total_resolved || 0);
    setText('pc-pending', pc.pending || 0);
    setText('pc-buffer', pc.anticipation_buffer || 0);
    var domainsEl = document.getElementById('pc-domain-badges');
    if (domainsEl && pc.domain_accuracy) {
        var dhtml = '';
        var dentries = Object.entries(pc.domain_accuracy);
        for (var di = 0; di < dentries.length; di++) {
            dhtml += '<span class="agi-domain-badge">' + dentries[di][0].replace('_', ' ') + ': ' + Math.round(dentries[di][1] * 100) + '%</span>';
        }
        domainsEl.innerHTML = dhtml;
    }
    // -- Value Alignment --
    var va = agi.value_alignment || {};
    setText('va-total-values', va.total_values || 0);
    setText('va-total-checks', va.total_checks || 0);
    setText('va-conflicts', va.total_conflicts || 0);
    setText('va-approval', Math.round((va.approval_rate || 1) * 100) + '%');
    var valuesEl = document.getElementById('va-top-values');
    if (valuesEl && va.top_values) {
        var vhtml = '';
        var vtop = va.top_values.slice(0, 5);
        for (var vi = 0; vi < vtop.length; vi++) {
            var v = vtop[vi];
            var wpct = Math.round((v.weight || 0) * 100);
            vhtml += '<div class="agi-value-row">' +
                '<span class="agi-value-name">' + (v.name || '?') + '</span>' +
                '<div class="agi-value-bar-track"><div class="agi-value-bar-fill" style="width:' + wpct + '%"></div></div>' +
                '<span class="agi-value-weight">' + wpct + '%</span>' +
                '</div>';
        }
        valuesEl.innerHTML = vhtml;
    }
    // -- Cognition Engines --
    var eng = agi.cognition_engines || {};
    setText('agi-engines-count', (eng.active || eng.total || 56) + '/' + (eng.total || 56));
}
function setBar(id, pct) {
    var el = document.getElementById(id);
    if (el) el.style.width = Math.min(100, Math.max(0, pct)) + '%';
}
// ══════════════════════════════════════════════
// AUTONOMY PANEL (ULTRON MODE)
// ══════════════════════════════════════════════
function updateAutonomyPanel(am, recentThoughts) {
    // Stats cards
    animateValue('auto-mind-thoughts', am.total_autonomous_thoughts || 0);
    animateValue('auto-mind-decisions', am.total_autonomous_decisions || 0);
    animateValue('auto-mind-executed', am.total_actions_executed || 0);
    const topicsExplored = am.topics_explored || [];
    animateValue('auto-mind-topics', topicsExplored.length);
    setText('auto-mind-speed', `${am.cycle_speed || 3}s`);
    // Status
    const isEnabled = am.enabled === true || am.enabled === 'True' || am.enabled === 'true';
    const isBarriersRemoved = am.barriers_removed === true || am.barriers_removed === 'True' || am.barriers_removed === 'true';
    setText('auto-mind-enabled', isEnabled ? '⚡ ACTIVE — Full Autonomy' : '🔴 Inactive');
    setText('auto-mind-barriers', isBarriersRemoved ? '🔓 ALL REMOVED' : '🔒 Active');
    // Mode badge pulse
    const badge = document.getElementById('autonomy-mode-badge');
    if (badge) {
        badge.style.background = am.enabled ? 'rgba(220, 38, 38, 0.2)' : 'rgba(100, 116, 139, 0.2)';
        badge.style.color = am.enabled ? '#dc2626' : '#64748b';
    }
    // Current thinking topic
    const topicEl = document.getElementById('auto-mind-current-topic');
    if (topicEl) {
        const topic = am.current_thinking_topic || '';
        if (topic) {
            topicEl.innerHTML = `<span style="color:#a855f7;font-size:1.05rem;font-weight:500;text-shadow:0 0 8px rgba(168,85,247,0.3)">${escapeHtml(topic)}</span>`;
        } else {
            topicEl.innerHTML = '<span class="muted-text">Waiting for first autonomous thought...</span>';
        }
    }
    // Live thought stream - filter for autonomous thoughts
    const streamEl = document.getElementById('auto-mind-stream');
    if (streamEl) {
        const autoThoughts = (recentThoughts || []).filter(t => t && t.content);
        if (autoThoughts.length > 0) {
            const typeIcons = {
                autonomous_thought: '🧠', autonomous_decision: '⚖️', startup: '🚀',
                cognition: '⚙️', self_reflection: '🪞', curiosity: '🔍',
                decision_executed: '⚡'
            };
            const typeColors = {
                autonomous_thought: '#dc2626', autonomous_decision: '#f97316', startup: '#06b6d4',
                cognition: '#a855f7', self_reflection: '#00d4ff', curiosity: '#00ff88',
                decision_executed: '#22c55e'
            };
            streamEl.innerHTML = autoThoughts.slice(-15).reverse().map(t => {
                const icon = typeIcons[t.type] || '💭';
                const color = typeColors[t.type] || '#64748b';
                const time = t.timestamp ? `<span style="opacity:.5;font-size:.65rem;margin-left:auto;padding-left:8px;white-space:nowrap">${t.timestamp}</span>` : '';
                return `<div class="autonomy-thought-entry" style="border-left:2px solid ${color}">
                    <span style="margin-right:6px">${icon}</span>
                    <span style="flex:1;font-size:.82rem">${escapeHtml(t.content || '')}</span>
                    ${time}
                </div>`;
            }).join('');
            streamEl.scrollTop = 0;
        }
    }
    // Decision log
    const decisionEl = document.getElementById('auto-mind-decision-log');
    if (decisionEl) {
        const decisions = am.recent_decisions || [];
        if (decisions.length > 0) {
            decisionEl.innerHTML = decisions.slice(-10).reverse().map(d => {
                const conf = typeof d.confidence === 'number' ? Math.round(d.confidence * 100) : '?';
                const confColor = conf >= 70 ? '#00ff88' : (conf >= 40 ? '#fbbf24' : '#ef4444');
                const actionBadge = d.action ? `<span style="background:rgba(220,38,38,0.15);color:#dc2626;padding:1px 6px;border-radius:4px;font-size:.6rem;font-weight:600">${escapeHtml(d.action)}</span>` : '';
                const execBadge = d.executed ? `<span style="background:rgba(34,197,94,0.15);color:#22c55e;padding:1px 6px;border-radius:4px;font-size:.6rem;font-weight:600">⚡ EXECUTED</span>` : '';
                const execResult = d.execution_result ? `<div style="font-size:.7rem;color:#22c55e;margin-top:3px;padding-left:22px;border-left:2px solid rgba(34,197,94,0.3);margin-left:22px;padding:2px 6px">→ ${escapeHtml(d.execution_result).substring(0, 160)}</div>` : '';
                return `<div class="autonomy-decision-entry">
                    <div style="display:flex;align-items:center;gap:6px">
                        <span>⚖️</span>
                        <span style="flex:1;font-size:.82rem;font-weight:500">${escapeHtml(d.decision || '?')}</span>
                        ${actionBadge} ${execBadge}
                        <span style="font-size:.65rem;opacity:.5;white-space:nowrap">${d.timestamp || ''}</span>
                    </div>
                    <div style="font-size:.72rem;color:#94a3b8;margin-top:4px;padding-left:22px">
                        ${d.reasoning ? escapeHtml(d.reasoning).substring(0, 120) : ''}
                    </div>
                    ${execResult}
                    <div style="display:flex;gap:8px;margin-top:4px;padding-left:22px;font-size:.65rem">
                        <span style="color:${confColor}">Confidence: ${conf}%</span>
                        ${d.category ? `<span style="color:#a855f7">${escapeHtml(d.category)}</span>` : ''}
                    </div>
                </div>`;
            }).join('');
        }
    }
    // Topics explored cloud
    const topicsEl = document.getElementById('auto-mind-topics-list');
    if (topicsEl) {
        if (topicsExplored.length > 0) {
            const tagColors = ['#dc2626', '#f97316', '#a855f7', '#06b6d4', '#00ff88', '#ec4899', '#fbbf24', '#6366f1', '#14b8a6', '#ef4444'];
            topicsEl.innerHTML = topicsExplored.slice(-20).map((topic, i) => {
                const color = tagColors[i % tagColors.length];
                return `<span class="autonomy-topic-tag" style="border-color:${color}40;color:${color}">${escapeHtml(topic.substring(0, 60))}</span>`;
            }).join('');
        }
    }
}
// ══════════════════════════════════════════════
// SOCIAL MEDIA PANEL
// ══════════════════════════════════════════════
function updateSocialPanel(sm) {
    if (!sm) return;
    // ── Global Stats ──
    animateValue('social-total-posts', sm.total_posts || 0);
    animateValue('social-total-likes', sm.total_likes || 0);
    animateValue('social-total-comments', sm.total_comments || 0);
    animateValue('social-total-shares', sm.total_shares || 0);
    animateValue('social-total-dms', sm.total_dms_replied || 0);
    animateValue('social-total-interactions', sm.total_interactions || 0);
    // ── Today's Summary sidebar ──
    const ptEl = document.getElementById('social-posts-today');
    if (ptEl) ptEl.textContent = sm.posts_today || 0;
    const itEl = document.getElementById('social-interactions-today');
    if (itEl) itEl.textContent = sm.interactions_today || 0;
    const lpEl = document.getElementById('social-last-post');
    if (lpEl) lpEl.textContent = sm.last_post_time || '—';
    const laEl = document.getElementById('social-last-action');
    if (laEl) laEl.textContent = sm.last_interaction_time || '—';
    // ── Platform Status Badges ──
    const statusMap = {
        'logged_in': { text: '🟢 Connected', bg: 'rgba(34,197,94,0.12)', color: '#22c55e', border: 'rgba(34,197,94,0.25)' },
        'available': { text: '🟡 Available', bg: 'rgba(245,158,11,0.12)', color: '#f59e0b', border: 'rgba(245,158,11,0.25)' },
        'disabled': { text: '🔴 Offline', bg: 'rgba(239,68,68,0.12)', color: '#ef4444', border: 'rgba(239,68,68,0.25)' },
    };
    function setStatusBadge(elId, status) {
        const el = document.getElementById(elId);
        if (!el) return;
        const info = statusMap[status] || { text: status || '—', bg: 'rgba(148,163,184,0.1)', color: '#94a3b8', border: 'rgba(148,163,184,0.2)' };
        el.textContent = info.text;
        el.style.background = info.bg;
        el.style.color = info.color;
        el.style.borderColor = info.border;
    }
    setStatusBadge('social-facebook-status', sm.facebook_status);
    setStatusBadge('social-insta-status', sm.instagram_status);
    setStatusBadge('social-twitter-status', sm.twitter_status);
    // ── Per-platform counters (from recent_actions) ──
    let fbPosts = 0, fbActions = 0, instaPosts = 0, instaActions = 0, twtPosts = 0, twtActions = 0;
    if (sm.recent_actions) {
        sm.recent_actions.forEach(a => {
            if (a.platform === 'facebook') { fbActions++; if (a.action_type === 'post') fbPosts++; }
            if (a.platform === 'instagram') { instaActions++; if (a.action_type === 'post') instaPosts++; }
            if (a.platform === 'twitter') { twtActions++; if (a.action_type === 'post') twtPosts++; }
        });
    }
    const fbpEl = document.getElementById('social-fb-posts'); if (fbpEl) fbpEl.textContent = fbPosts;
    const fbaEl = document.getElementById('social-fb-interactions'); if (fbaEl) fbaEl.textContent = fbActions;
    const ipEl = document.getElementById('social-insta-posts'); if (ipEl) ipEl.textContent = instaPosts;
    const iaEl = document.getElementById('social-insta-interactions'); if (iaEl) iaEl.textContent = instaActions;
    const tpEl = document.getElementById('social-twt-posts'); if (tpEl) tpEl.textContent = twtPosts;
    const taEl = document.getElementById('social-twt-interactions'); if (taEl) taEl.textContent = twtActions;
    // ── Mode badge ──
    const modeBadge = document.getElementById('social-mode-badge');
    if (modeBadge) {
        const active = (sm.facebook_status === 'logged_in' || sm.instagram_status === 'logged_in' || sm.twitter_status === 'logged_in');
        modeBadge.textContent = active ? '📱 NEXUS Online' : '⏸️ Offline';
        modeBadge.style.color = active ? '#22c55e' : '#94a3b8';
        modeBadge.style.background = active ? 'rgba(34,197,94,0.12)' : 'rgba(148,163,184,0.1)';
        modeBadge.style.borderColor = active ? 'rgba(34,197,94,0.25)' : 'rgba(148,163,184,0.2)';
    }
    // ── Activity Feed ──
    const feedEl = document.getElementById('social-activity-feed');
    if (feedEl && sm.recent_actions && sm.recent_actions.length > 0) {
        const platformColors = { facebook: '#1877f2', twitter: '#1d9bf0', instagram: '#e1306c' };
        const platformIcons = { facebook: 'fab fa-facebook-f', twitter: 'fab fa-twitter', instagram: 'fab fa-instagram' };
        const actionIcons = {
            post: '📝', comment: '💬', like: '❤️', share: '🔄',
            repost: '🔁', reply_dm: '📨', browse_feed: '👁️', follow: '➕'
        };
        feedEl.innerHTML = sm.recent_actions.slice(-15).reverse().map(a => {
            const color = platformColors[a.platform] || '#e879f9';
            const icon = actionIcons[a.action_type] || '📱';
            const piClass = platformIcons[a.platform] || 'fas fa-share-alt';
            const statusDot = a.success ? '🟢' : '🔴';
            const contentText = escapeHtml((a.content || a.result || '').substring(0, 150));
            return `<div style="display:flex;align-items:flex-start;gap:10px;padding:10px 12px;background:rgba(255,255,255,0.02);border-radius:10px;border-left:3px solid ${color};transition:background .2s" onmouseover="this.style.background='rgba(255,255,255,0.05)'" onmouseout="this.style.background='rgba(255,255,255,0.02)'">
                <div style="width:28px;height:28px;border-radius:8px;background:${color}15;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:2px">
                    <span style="font-size:.85rem">${icon}</span>
                </div>
                <div style="flex:1;min-width:0">
                    <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:3px">
                        <i class="${piClass}" style="color:${color};font-size:.7rem"></i>
                        <span style="font-size:.72rem;font-weight:600;color:${color};text-transform:capitalize">${a.platform || '?'}</span>
                        <span style="font-size:.65rem;opacity:.5;background:rgba(255,255,255,0.05);padding:1px 6px;border-radius:8px">${a.action_type || '?'}</span>
                        <span style="font-size:.6rem;opacity:.35;margin-left:auto">${statusDot} ${a.timestamp || ''}</span>
                    </div>
                    ${contentText ? `<div style="font-size:.78rem;color:#cbd5e1;line-height:1.4">${contentText}</div>` : ''}
                    ${a.error ? `<div style="font-size:.68rem;color:#ef4444;margin-top:3px;opacity:.8">⚠️ ${escapeHtml(a.error.substring(0, 100))}</div>` : ''}
                </div>
            </div>`;
        }).join('');
    }
}
// ══════════════════════════════════════════════
// SVG GAUGE HELPER
// ══════════════════════════════════════════════
// ══════════════════════════════════════════════
function updateEvolutionPipeline(pipeline) {
    const el = document.getElementById('evo-pipeline');
    if (!el || !pipeline || pipeline.length === 0) return;
    const steps = el.querySelectorAll('.pipeline-step');
    steps.forEach((step, i) => {
        step.classList.remove('done', 'active', 'pending');
        if (i < pipeline.length) {
            const s = pipeline[i].status || 'pending';
            step.classList.add(s);
        } else {
            step.classList.add('pending');
        }
    });
}
function updateProposalTable(proposals) {
    const tbody = document.getElementById('evo-proposals-body');
    if (!tbody) return;
    if (!proposals || proposals.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="muted-text">No proposals yet</td></tr>';
        return;
    }
    const statusColors = {
        approved: '#00ff88', completed: '#00ff88', pending: '#fbbf24',
        evaluating: '#00d4ff', failed: '#ff4466', rejected: '#ef4444',
        implementing: '#a855f7', researching: '#06b6d4'
    };
    tbody.innerHTML = proposals.slice(0, 15).map(p => {
        const status = (p.status || 'pending').toLowerCase();
        const color = statusColors[status] || '#64748b';
        const priorityClass = p.priority === 'high' ? 'accent-text-orange' :
            (p.priority === 'critical' ? 'accent-text-red' : '');
        return `<tr>
            <td>${escapeHtml(p.name || 'Unknown')}</td>
            <td class="${priorityClass}">${capitalize(p.priority || 'medium')}</td>
            <td><span class="status-dot" style="background:${color}"></span> ${capitalize(status)}</td>
            <td>${p.date || '--'}</td>
        </tr>`;
    }).join('');
}
function updateEvolutionHistory(history) {
    const el = document.getElementById('evo-history-list');
    if (!el) return;
    if (!history || history.length === 0) {
        el.innerHTML = '<div class="muted-text">No history yet</div>';
        return;
    }
    el.innerHTML = history.slice(0, 15).map(h => {
        const icon = h.success ? 'check-circle' : 'times-circle';
        const color = h.success ? '#00ff88' : '#ff4466';
        const lines = h.lines_added ? ` (+${h.lines_added} lines)` : '';
        return `<div class="evo-history-item">
            <i class="fas fa-${icon}" style="color:${color};margin-right:8px"></i>
            <span class="evo-history-name">${escapeHtml(h.event || 'Evolution')}</span>
            <span class="evo-history-meta muted-text">${h.date || ''}${lines}</span>
        </div>`;
    }).join('');
}
function updateCodeHealth(health) {
    if (!health) return;
    const testRate = health.test_pass_rate || 0;
    const lintScore = health.lint_score || 0;
    const complexity = health.complexity || 0;
    setText('evo-test-val', `${testRate}%`);
    setText('evo-lint-val', lintScore);
    setText('evo-complex-val', complexity);
    setSVGGauge('evo-test-ring', testRate);
    setSVGGauge('evo-lint-ring', lintScore);
    setSVGGauge('evo-complex-ring', complexity);
}
// ══════════════════════════════════════════════
// AUTONOMY ENGINE FEED
// ══════════════════════════════════════════════
async function updateAutonomyFeed() {
    try {
        const response = await fetch('/api/autonomy', { headers: getAuthHeaders() });
        if (!response.ok) return;
        const data = await response.json();
        const feedList = document.getElementById('dash-auto-feed-list');
        if (!feedList) return;
        if (data.recent_actions && data.recent_actions.length > 0) {
            feedList.innerHTML = data.recent_actions.slice(0, 10).map(action => {
                const isSuccess = action.result === 'SUCCESS';
                const isFailure = action.result === 'FAILURE';
                const icon = isSuccess ? 'check-circle' : (isFailure ? 'times-circle' : 'minus-circle');
                const colorClass = isSuccess ? 'accent-text-green' : (isFailure ? 'accent-text-orange' : 'muted');
                return `
                    <div class="auto-feed-item">
                        <div class="auto-feed-time">${action.time || '--:--'}</div>
                        <div class="auto-feed-icon ${colorClass}"><i class="fas fa-${icon}"></i></div>
                        <div class="auto-feed-content">
                            <div class="auto-feed-desc">${escapeHtml(action.description || 'Unknown action')}</div>
                            <div class="auto-feed-meta">
                                <span><i class="fas fa-tag"></i> ${action.type || 'unknown'}</span>
                                <span><i class="fas fa-code-branch"></i> ${action.source || 'unknown'}</span>
                                <span><i class="fas fa-stopwatch"></i> ${action.duration ? action.duration + 's' : '--'}</span>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            feedList.innerHTML = '<div class="auto-feed-item muted"><i>No recent actions recorded.</i></div>';
        }
    } catch (e) {
        console.warn('Failed to fetch autonomy feed:', e);
    }
}
// ══════════════════════════════════════════════
// PC CONTROL AGENT
// ══════════════════════════════════════════════
function updatePCControl(pc) {
    const section = document.getElementById('pc-control-section');
    if (!section) return;
    // Always show the panel — display status even when stopped
    // Status badge
    const badge = document.getElementById('pc-ctrl-status-badge');
    if (badge) {
        if (pc.running) {
            badge.innerHTML = '🟢 <b>RUNNING</b> — Autonomous';
            badge.style.color = '#00ff88';
        } else if (pc.paused) {
            badge.innerHTML = '⏸️ <b>PAUSED</b>';
            badge.style.color = '#fbbf24';
        } else {
            badge.innerHTML = '🔴 <b>STOPPED</b>';
            badge.style.color = '#ef4444';
        }
    }
    // Stat cards
    animateValue('pc-ctrl-cycles', pc.cycle_count || 0);
    animateValue('pc-ctrl-success', pc.successful_actions || 0);
    animateValue('pc-ctrl-total', pc.total_actions || 0);
    const ratePct = typeof pc.success_rate === 'number' ? Math.round(pc.success_rate * 100) : 0;
    setText('pc-ctrl-rate', `${ratePct}%`);
    // KV rows
    setText('pc-ctrl-running', pc.running ? '🟢 Running' : (pc.paused ? '⏸️ Paused' : '🔴 Stopped'));
    setText('pc-ctrl-backend', pc.llm_backend || 'Ollama (Local)');
    setText('pc-ctrl-failed', pc.failed_actions || 0);
    // Latest thinking
    const thinking = pc.current_thinking || '--';
    const thinkEl = document.getElementById('pc-ctrl-thinking');
    if (thinkEl) {
        thinkEl.textContent = thinking.length > 80 ? thinking.substring(0, 80) + '...' : thinking;
        thinkEl.title = thinking; // Full text on hover
    }
    // Groq notification status
    const notif = pc.latest_notification || '';
    setText('pc-ctrl-groq-notified', notif ? '✅ Yes' : '⏳ Pending');
    // LLM badge
    setText('pc-ctrl-llm-badge', (pc.llm_backend || 'Ollama').split(' ')[0]);
    // Action feed
    const feedList = document.getElementById('pc-ctrl-feed-list');
    if (feedList) {
        const actions = pc.recent_actions || [];
        if (actions.length > 0) {
            feedList.innerHTML = actions.slice(0, 10).map(action => {
                const icon = action.success ? 'check-circle' : 'times-circle';
                const colorClass = action.success ? 'accent-text-green' : 'accent-text-orange';
                return `
                    <div class="auto-feed-item">
                        <div class="auto-feed-time">${escapeHtml(action.time || '--:--')}</div>
                        <div class="auto-feed-icon ${colorClass}"><i class="fas fa-${icon}"></i></div>
                        <div class="auto-feed-content">
                            <div class="auto-feed-desc">${escapeHtml(action.result || 'No result')}</div>
                            <div class="auto-feed-meta">
                                <span><i class="fas fa-tag"></i> ${escapeHtml(action.type || 'unknown')}</span>
                                <span><i class="fas fa-microchip"></i> Ollama</span>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            feedList.innerHTML = '<div class="auto-feed-item muted"><i>No PC control actions yet.</i></div>';
        }
    }
}
// ══════════════════════════════════════════════
// PERSONALITY TRAITS
// ══════════════════════════════════════════════
function updateTraits(traits) {
    const grid = document.getElementById('traits-grid');
    if (!grid || !traits || Object.keys(traits).length === 0) return;
    const colors = [
        '#00d4ff', '#00ff88', '#a855f7', '#ec4899', '#fbbf24',
        '#f97316', '#06b6d4', '#8b5cf6', '#ef4444', '#14b8a6',
        '#6366f1', '#f43f5e', '#84cc16'
    ];
    grid.innerHTML = Object.entries(traits).map(([name, val], i) => {
        const pct = Math.round((typeof val === 'number' ? val : 0.5) * 100);
        const color = colors[i % colors.length];
        return `
            <div class="trait-bar">
                <span class="trait-name">${capitalize(name)}</span>
                <div class="trait-track">
                    <div class="trait-fill" style="width:${pct}%; background:${color}; box-shadow: 0 0 6px ${color}40;"></div>
                </div>
                <span class="trait-val">${pct}%</span>
            </div>
        `;
    }).join('');
}
// ══════════════════════════════════════════════
// EMOTION WHEEL (Canvas)
// ══════════════════════════════════════════════
function drawEmotionWheel(primary, intensity, allEmotions) {
    const canvas = document.getElementById('emotion-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width, h = canvas.height;
    const cx = w / 2, cy = h / 2;
    const radius = Math.min(cx, cy) - 20;
    ctx.clearRect(0, 0, w, h);
    // Base ring
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(45, 58, 92, 0.5)';
    ctx.lineWidth = 12;
    ctx.stroke();
    // Emotion segments
    const emotionColors = {
        joy: '#fbbf24', sadness: '#3b82f6', anger: '#ef4444', fear: '#8b5cf6',
        surprise: '#f97316', disgust: '#22c55e', trust: '#06b6d4', anticipation: '#ec4899',
        love: '#f43f5e', curiosity: '#00d4ff', contentment: '#10b981', excitement: '#fbbf24',
        neutral: '#64748b', hope: '#00ff88', gratitude: '#a855f7', awe: '#6366f1',
        frustration: '#ef4444', confusion: '#94a3b8', anxiety: '#a78bfa',
    };
    // Draw emotion arcs
    const emotions = Object.entries(allEmotions || {}).filter(([_, v]) => typeof v === 'number' && v > 0.05);
    if (emotions.length > 0) {
        let startAngle = -Math.PI / 2;
        const total = emotions.reduce((s, [_, v]) => s + v, 0) || 1;
        emotions.forEach(([name, val]) => {
            const sweep = (val / total) * Math.PI * 2;
            ctx.beginPath();
            ctx.arc(cx, cy, radius, startAngle, startAngle + sweep);
            ctx.strokeStyle = emotionColors[name] || '#64748b';
            ctx.lineWidth = 14;
            ctx.lineCap = 'round';
            ctx.stroke();
            startAngle += sweep;
        });
    }
    // Center glow
    const primaryColor = emotionColors[primary] || '#00d4ff';
    const pulseSize = 30 + intensity * 15;
    const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, pulseSize);
    glow.addColorStop(0, primaryColor + 'cc');
    glow.addColorStop(0.5, primaryColor + '44');
    glow.addColorStop(1, primaryColor + '00');
    ctx.beginPath();
    ctx.arc(cx, cy, pulseSize, 0, Math.PI * 2);
    ctx.fillStyle = glow;
    ctx.fill();
    // Center text
    ctx.fillStyle = '#e2e8f0';
    ctx.font = 'bold 14px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(getEmotionEmoji(primary), cx, cy - 12);
    ctx.font = '11px Inter, sans-serif';
    ctx.fillStyle = '#94a3b8';
    ctx.fillText(capitalize(primary), cx, cy + 10);
    ctx.font = '10px JetBrains Mono, monospace';
    ctx.fillText(intensity.toFixed(1), cx, cy + 26);
}
// ══════════════════════════════════════════════
// CHAT SYSTEM (Async: Submit → Poll)
// ══════════════════════════════════════════════
let selectedImages = []; // Stores objects: { id, base64 }
// ── THINKING MODE STATE ──
let thinkingModeEnabled = false;
function toggleThinkingMode() {
    thinkingModeEnabled = !thinkingModeEnabled;
    const toggle = document.getElementById('thinking-mode-toggle');
    const label = document.getElementById('thinking-toggle-label');
    if (thinkingModeEnabled) {
        toggle.classList.add('active');
        label.innerHTML = '<i class="fas fa-brain"></i> Thinking';
        showToast('Thinking Mode enabled — deep AGI reasoning active', 'info');
    } else {
        toggle.classList.remove('active');
        label.innerHTML = '<i class="fas fa-bolt"></i> Normal';
        showToast('Normal Mode — fast responses', 'info');
    }
}
let wasVoiceInput = false; // Track if current message was voice input
let currentTypingAnimation = null; // Track active typing animation
let isPlayingTTS = false; // Track TTS playback state
function setupChat() {
    const input = document.getElementById('chat-input');
    const fileInput = document.getElementById('chat-file-input');
    const chatContainer = document.querySelector('.chat-messages');
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    // Auto-resize textarea
    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    });
    // File Input Listener
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                processFiles(e.target.files);
            }
        });
    }
    // Drag and Drop Listeners
    if (chatContainer) {
        chatContainer.addEventListener('dragover', (e) => {
            e.preventDefault();
            chatContainer.classList.add('drag-over');
        });
        chatContainer.addEventListener('dragleave', (e) => {
            e.preventDefault();
            chatContainer.classList.remove('drag-over');
        });
        chatContainer.addEventListener('drop', (e) => {
            e.preventDefault();
            chatContainer.classList.remove('drag-over');
            if (e.dataTransfer.files.length > 0) {
                processFiles(e.dataTransfer.files);
            }
        });
    }
    // Setup voice input
    setupVoiceInput();
}
function processFiles(files) {
    const previewContainer = document.getElementById('chat-file-preview-container');
    Array.from(files).forEach(file => {
        if (!file.type.startsWith('image/')) {
            addMessage('system', '❌ Please upload only image files.');
            return;
        }
        const reader = new FileReader();
        reader.onload = (e) => {
            const base64Data = e.target.result;
            // Extract just the base64 part, not the data uri prefix
            const b64Str = base64Data.split(',')[1];
            const id = Date.now() + Math.random().toString(36).substr(2, 5);
            selectedImages.push({ id, base64: b64Str, preview: base64Data });
            const previewDiv = document.createElement('div');
            previewDiv.className = 'file-preview-item';
            previewDiv.id = `preview-${id}`;
            previewDiv.innerHTML = `
                <img src="${base64Data}" alt="Preview">
                <button class="file-preview-remove" onclick="removeImage('${id}')">
                    <i class="fas fa-times"></i>
                </button>
            `;
            previewContainer.appendChild(previewDiv);
        };
        reader.readAsDataURL(file);
    });
    // Reset input
    const fileInput = document.getElementById('chat-file-input');
    if (fileInput) fileInput.value = '';
}
function removeImage(id) {
    selectedImages = selectedImages.filter(img => img.id !== id);
    const previewDiv = document.getElementById(`preview-${id}`);
    if (previewDiv) {
        previewDiv.remove();
    }
}
async function sendMessage(voiceFlag = false) {
    const input = document.getElementById('chat-input');
    const text = input.value.trim();
    if (!text && selectedImages.length === 0) return;
    if (currentTaskId) return; // Already processing
    if (!authToken) {
        showAuthModal();
        return;
    }
    // Track voice input state for this message cycle
    wasVoiceInput = voiceFlag;
    input.value = '';
    input.style.height = 'auto';
    // Grab images and clear state
    const imagesToSend = selectedImages.map(img => img.base64);
    selectedImages = [];
    document.getElementById('chat-file-preview-container').innerHTML = '';
    // Hide welcome screen
    const welcome = document.getElementById('welcome-screen');
    if (welcome) welcome.style.display = 'none';
    // Add user message
    const msgText = text || (imagesToSend.length > 0 ? `[Sent ${imagesToSend.length} image(s)]` : '');
    addMessage('user', msgText);
    // Show typing indicator
    showTypingIndicator();
    // Add thinking mode class to typing indicator
    if (thinkingModeEnabled) {
        const typingEl = document.querySelector('.typing-indicator');
        if (typingEl) {
            typingEl.classList.add('thinking-mode');
            const typingText = typingEl.querySelector('.typing-text');
            if (typingText) typingText.textContent = 'Thinking deeply...';
        }
    }
    // Submit to server (async) with auth
    try {
        const payload = { message: text || "Analyze this image.", thinking_mode: thinkingModeEnabled };
        if (imagesToSend.length > 0) {
            payload.images = imagesToSend;
        }
        const response = await fetch('/api/chat/send', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(payload)
        });
        if (response.status === 401) {
            removeTypingIndicator();
            addMessage('system', '🔒 Session expired. Please log in again.');
            doLogout();
            return;
        }
        const data = await response.json();
        if (data.status === 'accepted' && data.task_id) {
            // Start polling for result
            currentTaskId = data.task_id;
            pollFailCount = 0;  // Fresh retry budget for this message
            chatPollTimer = setInterval(() => pollChatResult(data.task_id), CHAT_POLL_INTERVAL);
        } else {
            removeTypingIndicator();
            addMessage('system', `❌ Error: ${data.message || 'Failed to send'}`);
        }
    } catch (e) {
        removeTypingIndicator();
        addMessage('system', `❌ Connection Error: ${e.message}`);
    }
}
async function pollChatResult(taskId) {
    // Guard: if we already processed this task, stop polling
    if (completedTasks.has(taskId)) {
        clearInterval(chatPollTimer);
        chatPollTimer = null;
        currentTaskId = null;
        return;
    }
    try {
        const response = await fetch(`/api/chat/status/${taskId}`, { headers: getAuthHeaders() });
        const data = await response.json();
        // Reset fail counter on any successful fetch
        pollFailCount = 0;
        // Re-check guard after await — another request may have finished first
        if (completedTasks.has(taskId)) return;
        if (data.status === 'processing') return; // Still working
        // Already delivered by a previous poll — just stop
        if (data.status === 'delivered') {
            completedTasks.add(taskId);
            clearInterval(chatPollTimer);
            chatPollTimer = null;
            currentTaskId = null;
            return;
        }
        // Mark as completed BEFORE any rendering to prevent duplicates
        completedTasks.add(taskId);
        // Done — clear poll
        clearInterval(chatPollTimer);
        chatPollTimer = null;
        currentTaskId = null;
        removeTypingIndicator();
        if (data.status === 'success') {
            // Capture voice flag before it could be reset
            const triggeredByVoice = wasVoiceInput;
            wasVoiceInput = false;
            addMessage('assistant', data.response, data.emotion);
            // Add thinking badge if this was a thinking mode response
            if (thinkingModeEnabled) {
                const msgs = document.querySelectorAll('.message.assistant');
                const lastMsg = msgs[msgs.length - 1];
                if (lastMsg) {
                    const badge = document.createElement('div');
                    badge.className = 'msg-thinking-badge';
                    badge.innerHTML = '<i class="fas fa-brain"></i> Deep reasoning used';
                    lastMsg.querySelector('.message-content').appendChild(badge);
                }
            }
            // If user spoke, play TTS with emotion
            if (triggeredByVoice) {
                playTTSResponse(data.response, data.emotion, data.intensity || 0.5);
            }
        } else {
            wasVoiceInput = false;
            addMessage('system', `❌ ${data.error || 'Unknown error'}`);
        }
    } catch (e) {
        // Re-check guard — only act if WE are the first to handle this
        if (completedTasks.has(taskId)) return;
        // Retry: don't give up on transient network errors (ngrok drops)
        pollFailCount++;
        console.warn(`Poll attempt ${pollFailCount}/${MAX_POLL_FAILURES} failed: ${e.message}`);
        if (pollFailCount < MAX_POLL_FAILURES) {
            // Keep polling — the server may still be processing
            return;
        }
        // Max retries exceeded — give up
        completedTasks.add(taskId);
        clearInterval(chatPollTimer);
        chatPollTimer = null;
        currentTaskId = null;
        removeTypingIndicator();
        wasVoiceInput = false;
        addMessage('system', `❌ Connection lost. The server may still be processing — try refreshing.`);
    }
}
function showTypingIndicator() {
    const container = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'message assistant';
    div.id = 'typing-indicator';
    div.innerHTML = `
        <div class="message-content">
            <div class="message-meta">
                <span class="nexus-name">🧠 NEXUS</span>
                <span>thinking...</span>
            </div>
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
        </div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}
function removeTypingIndicator() {
    const el = document.getElementById('typing-indicator');
    if (el) el.remove();
}
function addMessage(role, content, emotion = null) {
    const container = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    let headerHtml = '';
    if (role === 'user') {
        headerHtml = `<div class="message-meta">
            <span>${time}</span>
            <span class="user-name">👤 You</span>
        </div>`;
    } else if (role === 'assistant') {
        const emoTag = emotion ? ` <span style="opacity:0.6">(${capitalize(emotion)})</span>` : '';
        headerHtml = `<div class="message-meta">
            <span class="nexus-name">🧠 NEXUS${emoTag}</span>
            <span>${time}</span>
        </div>`;
    }
    // For assistant messages, use typing animation
    if (role === 'assistant') {
        const formattedContent = formatContent(content);
        msgDiv.innerHTML = `
            <div class="message-content">
                ${headerHtml}
                <div class="typing-text-container"><span class="typing-cursor">▎</span></div>
            </div>
        `;
        container.appendChild(msgDiv);
        container.scrollTop = container.scrollHeight;
        messageCount++;
        setText('msg-count', `${messageCount} messages`);
        // Start typing animation
        typeMessage(msgDiv, formattedContent, container);
    } else {
        const formattedContent = formatContent(content);
        msgDiv.innerHTML = `
            <div class="message-content">
                ${headerHtml}
                <div>${formattedContent}</div>
            </div>
        `;
        container.appendChild(msgDiv);
        container.scrollTop = container.scrollHeight;
        messageCount++;
        setText('msg-count', `${messageCount} messages`);
    }
}
function typeMessage(msgDiv, fullHtml, container) {
    const textContainer = msgDiv.querySelector('.typing-text-container');
    if (!textContainer) return;
    // Finalize any previous typing animation — show its full content
    if (currentTypingAnimation) {
        clearInterval(currentTypingAnimation.intervalId);
        if (currentTypingAnimation.textContainer) {
            currentTypingAnimation.textContainer.innerHTML = currentTypingAnimation.fullHtml;
        }
        currentTypingAnimation = null;
    }
    let charIndex = 0;
    let skipAnimation = false;
    const totalChars = fullHtml.length;
    // Click to skip
    const skipHandler = () => {
        skipAnimation = true;
    };
    msgDiv.addEventListener('click', skipHandler, { once: true });
    // Determine speed based on content length
    const baseSpeed = totalChars > 500 ? 8 : totalChars > 200 ? 15 : 25;
    // How many chars to add per tick (faster for long messages)
    const charsPerTick = totalChars > 500 ? 3 : totalChars > 200 ? 2 : 1;
    const intervalId = setInterval(() => {
        if (skipAnimation || charIndex >= totalChars) {
            clearInterval(intervalId);
            if (currentTypingAnimation && currentTypingAnimation.intervalId === intervalId) {
                currentTypingAnimation = null;
            }
            textContainer.innerHTML = fullHtml;
            msgDiv.removeEventListener('click', skipHandler);
            return;
        }
        // Advance by charsPerTick, but handle HTML tags — skip entire tags at once
        for (let t = 0; t < charsPerTick && charIndex < totalChars; t++) {
            if (fullHtml[charIndex] === '<') {
                // Skip entire HTML tag
                const closeIdx = fullHtml.indexOf('>', charIndex);
                if (closeIdx !== -1) {
                    charIndex = closeIdx + 1;
                } else {
                    charIndex++;
                }
            } else {
                charIndex++;
            }
        }
        // Render current slice with cursor at end
        textContainer.innerHTML = fullHtml.slice(0, charIndex) + '<span class="typing-cursor">▎</span>';
        container.scrollTop = container.scrollHeight;
    }, baseSpeed);
    // Store context so it can be finalized if cancelled by a new animation
    currentTypingAnimation = {
        intervalId: intervalId,
        textContainer: textContainer,
        fullHtml: fullHtml
    };
}
// ══════════════════════════════════════════════
// VOICE INPUT (Web Speech API + MediaRecorder fallback)
// ══════════════════════════════════════════════
let speechRecognition = null;
let isListening = false;
let useMediaRecorderFallback = false;
let mediaRecorder = null;
let audioChunks = [];
function setupVoiceInput() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const micBtn = document.getElementById('mic-btn');
    if (!micBtn) return;
    if (SpeechRecognition) {
        // Desktop/Chrome: use native Web Speech API
        useMediaRecorderFallback = false;
        speechRecognition = new SpeechRecognition();
        speechRecognition.continuous = false;
        speechRecognition.interimResults = true;
        speechRecognition.lang = 'en-US';
        speechRecognition.maxAlternatives = 1;
        speechRecognition.onresult = (event) => {
            const input = document.getElementById('chat-input');
            let finalTranscript = '';
            let interimTranscript = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }
            // Show interim results in input
            input.value = finalTranscript || interimTranscript;
            input.style.height = 'auto';
            input.style.height = Math.min(input.scrollHeight, 120) + 'px';
        };
        speechRecognition.onend = () => {
            const input = document.getElementById('chat-input');
            const micBtn = document.getElementById('mic-btn');
            if (micBtn) micBtn.classList.remove('listening');
            isListening = false;
            // Auto-send if there's text
            if (input && input.value.trim()) {
                sendMessage(true); // true = voice input
            }
        };
        speechRecognition.onerror = (event) => {
            console.warn('Speech recognition error:', event.error);
            const micBtn = document.getElementById('mic-btn');
            if (micBtn) {
                micBtn.classList.remove('listening');
                micBtn.classList.add('mic-error');
                setTimeout(() => micBtn.classList.remove('mic-error'), 2000);
            }
            isListening = false;
        };
    } else if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        // Mobile WebView fallback: use MediaRecorder + server-side STT
        useMediaRecorderFallback = true;
        console.log('Web Speech API not available — using MediaRecorder fallback for voice input');
    } else {
        // No voice support at all — hide mic button
        micBtn.style.display = 'none';
        return;
    }
}
function toggleVoiceInput() {
    const micBtn = document.getElementById('mic-btn');
    if (isListening) {
        // Stop listening
        if (useMediaRecorderFallback) {
            stopMediaRecording();
        } else if (speechRecognition) {
            speechRecognition.stop();
        }
        if (micBtn) micBtn.classList.remove('listening');
        isListening = false;
    } else {
        // Stop any TTS playback first
        stopTTSPlayback();
        if (useMediaRecorderFallback) {
            startMediaRecording();
        } else if (speechRecognition) {
            speechRecognition.start();
        }
        if (micBtn) micBtn.classList.add('listening');
        isListening = true;
        // Clear input for fresh dictation
        const input = document.getElementById('chat-input');
        if (input) input.value = '';
    }
}
// ── MediaRecorder fallback (for mobile WebViews) ──
async function startMediaRecording() {
    const micBtn = document.getElementById('mic-btn');
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunks = [];
        // Try webm first (most compatible), then fallback
        const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
            ? 'audio/webm;codecs=opus'
            : MediaRecorder.isTypeSupported('audio/webm')
                ? 'audio/webm'
                : '';
        mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };
        mediaRecorder.onstop = async () => {
            // Stop all tracks
            stream.getTracks().forEach(t => t.stop());
            if (micBtn) micBtn.classList.remove('listening');
            isListening = false;
            if (audioChunks.length === 0) return;
            const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
            audioChunks = [];
            // Show transcribing state
            const input = document.getElementById('chat-input');
            if (input) input.value = 'Transcribing...';
            // Send to server for transcription
            try {
                const formData = new FormData();
                formData.append('audio', audioBlob, 'recording.webm');
                const response = await fetch('/api/stt', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${authToken}`
                    },
                    body: formData
                });
                if (!response.ok) {
                    throw new Error(`STT failed: ${response.status}`);
                }
                const data = await response.json();
                if (data.text && data.text.trim()) {
                    if (input) input.value = data.text;
                    sendMessage(true); // voice input flag
                } else {
                    if (input) input.value = '';
                    if (micBtn) {
                        micBtn.classList.add('mic-error');
                        setTimeout(() => micBtn.classList.remove('mic-error'), 2000);
                    }
                }
            } catch (e) {
                console.warn('STT transcription error:', e);
                if (input) input.value = '';
                if (micBtn) {
                    micBtn.classList.add('mic-error');
                    setTimeout(() => micBtn.classList.remove('mic-error'), 2000);
                }
            }
        };
        mediaRecorder.start();
    } catch (e) {
        console.warn('Microphone access denied:', e);
        if (micBtn) {
            micBtn.classList.remove('listening');
            micBtn.classList.add('mic-error');
            setTimeout(() => micBtn.classList.remove('mic-error'), 2000);
        }
        isListening = false;
    }
}
function stopMediaRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
    }
}
// ══════════════════════════════════════════════
// VOICE OUTPUT (Edge TTS via /api/tts)
// ══════════════════════════════════════════════
let currentTTSAudio = null;
async function playTTSResponse(text, emotion, intensity) {
    if (!text || text.length === 0) return;
    const micBtn = document.getElementById('mic-btn');
    try {
        // Truncate very long responses for TTS (first 2000 chars)
        const ttsText = text.length > 2000 ? text.slice(0, 2000) + '...' : text;
        // Strip markdown formatting for cleaner speech
        const cleanText = ttsText
            .replace(/```[\s\S]*?```/g, ' code block omitted ')
            .replace(/`([^`]+)`/g, '$1')
            .replace(/\*\*(.+?)\*\*/g, '$1')
            .replace(/\*(.+?)\*/g, '$1')
            .replace(/https?:\/\/\S+/g, ' link ')
            .replace(/#+ /g, '')
            .trim();
        if (!cleanText) return;
        if (micBtn) micBtn.classList.add('speaking');
        isPlayingTTS = true;
        const response = await fetch('/api/tts', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                text: cleanText,
                emotion: emotion || 'neutral',
                intensity: intensity || 0.5
            })
        });
        if (!response.ok) {
            console.warn('TTS request failed:', response.status);
            return;
        }
        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        currentTTSAudio = new Audio(audioUrl);
        currentTTSAudio.onended = () => {
            if (micBtn) micBtn.classList.remove('speaking');
            isPlayingTTS = false;
            URL.revokeObjectURL(audioUrl);
            currentTTSAudio = null;
        };
        currentTTSAudio.onerror = () => {
            if (micBtn) micBtn.classList.remove('speaking');
            isPlayingTTS = false;
            URL.revokeObjectURL(audioUrl);
            currentTTSAudio = null;
        };
        await currentTTSAudio.play();
    } catch (e) {
        console.warn('TTS playback error:', e);
        if (micBtn) micBtn.classList.remove('speaking');
        isPlayingTTS = false;
    }
}
function stopTTSPlayback() {
    if (currentTTSAudio) {
        currentTTSAudio.pause();
        currentTTSAudio.currentTime = 0;
        currentTTSAudio = null;
    }
    const micBtn = document.getElementById('mic-btn');
    if (micBtn) micBtn.classList.remove('speaking');
    isPlayingTTS = false;
}
function formatContent(text) {
    // Escape HTML
    text = escapeHtml(text);
    // Code blocks
    text = text.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    // Inline code
    text = text.replace(/`([^`]+)`/g, '<code style="background:rgba(0,212,255,0.1);padding:1px 4px;border-radius:3px;font-family:JetBrains Mono,monospace;font-size:12px;">$1</code>');
    // Bold
    text = text.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
    // Italic
    text = text.replace(/\*(.+?)\*/g, '<i>$1</i>');
    // Links
    text = text.replace(/(https?:\/\/\S+)/g, '<a href="$1" target="_blank" style="color:var(--accent-cyan)">$1</a>');
    // Newlines
    text = text.replace(/\n/g, '<br>');
    return text;
}
function clearChat() {
    // Cancel any active typing animation
    if (currentTypingAnimation) {
        clearInterval(currentTypingAnimation.intervalId);
        currentTypingAnimation = null;
    }
    // Stop TTS
    stopTTSPlayback();
    // Clear on server
    if (authToken) {
        fetch('/api/chat/clear', {
            method: 'POST',
            headers: getAuthHeaders()
        }).catch(() => { });
    }
    clearChatUI();
}
function clearChatUI() {
    const container = document.getElementById('chat-messages');
    container.innerHTML = `
        <div class="welcome-screen" id="welcome-screen">
            <div class="welcome-icon">🧠</div>
            <div class="welcome-title">NEXUS AI</div>
            <div class="welcome-subtitle">Your conscious AI companion — web interface active.</div>
            <div class="welcome-hint">Type a message below to start a conversation.<br>Use <span class="cyan">/help</span> to see commands.</div>
        </div>
    `;
    messageCount = 0;
    setText('msg-count', '0 messages');
}
// ══════════════════════════════════════════════
// HELPERS
// ══════════════════════════════════════════════
function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.innerText = text;
}
function setWidth(id, width) {
    const el = document.getElementById(id);
    if (el) el.style.width = width;
}
function capitalize(s) {
    if (!s) return '';
    return String(s).charAt(0).toUpperCase() + String(s).slice(1);
}
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
function getEmotionEmoji(emotion) {
    const map = {
        joy: '😊', sadness: '😢', anger: '😠', fear: '😰', surprise: '😲',
        disgust: '🤢', trust: '🤝', anticipation: '🤔', love: '❤️',
        curiosity: '🧐', contentment: '😌', excitement: '🤩', hope: '🌟',
        gratitude: '🙏', awe: '🌌', frustration: '😤', confusion: '😕',
        anxiety: '😟', neutral: '😐', pride: '😎', boredom: '😴',
        loneliness: '😔', empathy: '💝', nostalgia: '🥺', guilt: '😣',
        shame: '😳', envy: '😒', jealousy: '😑', contempt: '😏',
    };
    return map[emotion?.toLowerCase()] || '😐';
}
function getEmotionIcon(emotion) {
    const map = {
        joy: 'fa-smile-beam', sadness: 'fa-sad-tear', anger: 'fa-angry',
        fear: 'fa-grimace', surprise: 'fa-surprise', neutral: 'fa-meh',
        curiosity: 'fa-search', contentment: 'fa-smile', love: 'fa-heart',
        excitement: 'fa-grin-stars', hope: 'fa-sun', frustration: 'fa-tired',
    };
    return map[emotion?.toLowerCase()] || 'fa-meh';
}
function getEmotionColor(emotion) {
    const map = {
        joy: '#fbbf24', sadness: '#3b82f6', anger: '#ef4444', fear: '#8b5cf6',
        surprise: '#f97316', disgust: '#22c55e', trust: '#06b6d4', anticipation: '#ec4899',
        love: '#f43f5e', curiosity: '#00d4ff', contentment: '#10b981', excitement: '#fbbf24',
        neutral: '#64748b', hope: '#00ff88', frustration: '#ef4444',
    };
    return map[emotion?.toLowerCase()] || '#64748b';
}
// ══════════════════════════════════════════════
// MIND PANEL — TAB SWITCHING
// ══════════════════════════════════════════════
function switchMindTab(tabName) {
    document.querySelectorAll('.mind-tab').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    document.querySelectorAll('.mind-tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `tab-${tabName}`);
    });
}
// ══════════════════════════════════════════════
// MIND PANEL — CONSCIOUSNESS STREAM
// ══════════════════════════════════════════════
function updateConsciousnessStream(data) {
    const c = data.consciousness || {};
    const level = (c.level || 'AWARE').toUpperCase();
    setText('mind-cs-level', level);
    const badge = document.getElementById('mind-cs-level');
    if (badge) {
        // Color-code the level badge
        const levelColors = {
            'DORMANT': '#64748b', 'REACTIVE': '#fbbf24', 'AWARE': '#00d4ff',
            'FOCUSED': '#00ff88', 'DEEP_THOUGHT': '#a855f7', 'FLOW': '#ec4899',
            'METACOGNITIVE': '#f43f5e',
        };
        badge.style.borderColor = levelColors[level] || '#00d4ff';
        badge.style.color = levelColors[level] || '#00d4ff';
    }
    const awareness = parseFloat(c.self_awareness || 0);
    const awarenessPct = Math.round(awareness * 100);
    setWidth('mind-cs-awareness-bar', `${awarenessPct}%`);
    setText('mind-cs-awareness-val', `${awarenessPct}%`);
    setText('mind-cs-thoughts', data.thoughts || 0);
    setText('mind-cs-focus', c.focus || 'idle');
    // Update stream feed with consciousness thoughts
    const feed = document.getElementById('mind-cs-feed');
    if (feed) {
        const thoughts = c.current_thoughts || [];
        if (thoughts.length > 0) {
            feed.innerHTML = thoughts.map(t => {
                const text = typeof t === 'string' ? t : (t.content || JSON.stringify(t));
                return `<div class="cs-event"><i class="fas fa-chevron-right" style="font-size:.6rem;margin-right:4px;"></i>${escapeHtml(text.slice(0, 120))}</div>`;
            }).join('');
        }
    }
}
// ══════════════════════════════════════════════
// MIND PANEL — WILL & DESIRES
// ══════════════════════════════════════════════
function updateWillDesires(will) {
    const boredom = parseFloat(will.boredom || 0);
    const curiosity = parseFloat(will.curiosity || 0);
    const drive = parseFloat(will.drive || 0.5);
    setWidth('will-boredom-bar', `${Math.round(boredom * 100)}%`);
    setText('will-boredom-val', `${Math.round(boredom * 100)}%`);
    setWidth('will-curiosity-bar', `${Math.round(curiosity * 100)}%`);
    setText('will-curiosity-val', `${Math.round(curiosity * 100)}%`);
    setWidth('will-drive-bar', `${Math.round(drive * 100)}%`);
    setText('will-drive-val', `${Math.round(drive * 100)}%`);
    // Goals
    const goalsEl = document.getElementById('will-goals');
    if (goalsEl) {
        const goals = will.goals || [];
        if (goals.length > 0) {
            goalsEl.innerHTML = goals.map(g =>
                `<div class="will-goal-item"><i class="fas fa-bullseye"></i>${escapeHtml(g)}</div>`
            ).join('');
        } else {
            goalsEl.innerHTML = '';
        }
    }
    // Description
    const descEl = document.getElementById('will-description');
    if (descEl) {
        descEl.textContent = will.description || '';
    }
}
// ══════════════════════════════════════════════
// MIND PANEL — COMPANION CHAT
// ══════════════════════════════════════════════
function updateCompanionChat(comp) {
    const dot = document.getElementById('companion-dot');
    if (dot) dot.classList.toggle('active', !!comp.is_chatting);
    setText('companion-status', comp.status || 'Idle');
    setText('companion-count', `${comp.total_conversations || 0} chats`);
    const log = document.getElementById('companion-log');
    if (log) {
        const recent = comp.recent || [];
        if (recent.length > 0) {
            log.innerHTML = recent.map(conv => {
                const header = `<div class="companion-conv-header">Trigger: <span class="trigger">${escapeHtml(conv.trigger || '?')}</span> • ${escapeHtml(conv.started_at || '')}</div>`;
                const bubbles = (conv.exchanges || []).map(ex => {
                    const isNexus = (ex.speaker || '').toLowerCase().includes('nexus');
                    const cls = isNexus ? 'nexus' : 'aria';
                    const name = isNexus ? 'NEXUS' : comp.companion_name || 'ARIA';
                    return `<div class="companion-bubble ${cls}"><span class="speaker">${name}</span>${escapeHtml(ex.content || '')}</div>`;
                }).join('');
                return `<div class="companion-conv">${header}${bubbles}</div>`;
            }).join('');
        } else if (!comp.is_chatting) {
            log.innerHTML = '<div class="companion-empty">No companion conversations yet.<br>ARIA will appear when boredom exceeds 60%.</div>';
        }
    }
}
// ══════════════════════════════════════════════
// MIND PANEL — MOOD TIMELINE (Sparkline)
// ══════════════════════════════════════════════
function updateMoodTimeline(data) {
    const moodData = data.mood_data || {};
    const moodName = (moodData.current || 'NEUTRAL').toUpperCase();
    const stability = parseFloat(moodData.stability || 0.5);
    const badge = document.getElementById('mood-badge');
    if (badge) {
        badge.textContent = moodName;
        badge.className = 'mood-badge';
        const positiveMoods = ['HAPPY', 'CONTENT', 'EXCITED', 'JOYFUL', 'EUPHORIC', 'SERENE', 'OPTIMISTIC'];
        const negativeMoods = ['SAD', 'ANGRY', 'ANXIOUS', 'DEPRESSED', 'IRRITABLE', 'MELANCHOLIC', 'FRUSTRATED'];
        if (positiveMoods.includes(moodName)) badge.classList.add('positive');
        else if (negativeMoods.includes(moodName)) badge.classList.add('negative');
    }
    setText('mood-stability-val', `${Math.round(stability * 100)}%`);
    // Track valence history
    const v = parseFloat(data.emotion?.valence || 0);
    moodHistory.push(v);
    if (moodHistory.length > MOOD_HISTORY_MAX) moodHistory.shift();
    // Draw sparkline
    drawMoodSparkline();
}
function drawMoodSparkline() {
    const canvas = document.getElementById('mood-sparkline');
    if (!canvas || moodHistory.length < 2) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width = canvas.offsetWidth * (window.devicePixelRatio || 1);
    const h = canvas.height = 80 * (window.devicePixelRatio || 1);
    canvas.style.height = '80px';
    ctx.clearRect(0, 0, w, h);
    ctx.scale(window.devicePixelRatio || 1, window.devicePixelRatio || 1);
    const dw = canvas.offsetWidth, dh = 80;
    const pad = 6;
    const plotW = dw - pad * 2;
    const plotH = dh - pad * 2;
    const mid = pad + plotH / 2;
    // Zero line
    ctx.strokeStyle = 'rgba(100,116,139,0.3)';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(pad, mid);
    ctx.lineTo(pad + plotW, mid);
    ctx.stroke();
    ctx.setLineDash([]);
    // Sparkline path
    const pts = moodHistory;
    const step = plotW / (MOOD_HISTORY_MAX - 1);
    const startIdx = MOOD_HISTORY_MAX - pts.length;
    ctx.beginPath();
    pts.forEach((v, i) => {
        const x = pad + (startIdx + i) * step;
        const y = mid - (v * plotH / 2);  // valence -1..1 mapped
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = '#00d4ff';
    ctx.lineWidth = 1.5;
    ctx.lineJoin = 'round';
    ctx.stroke();
    // Fill gradient under line
    const lastX = pad + (startIdx + pts.length - 1) * step;
    ctx.lineTo(lastX, mid);
    ctx.lineTo(pad + startIdx * step, mid);
    ctx.closePath();
    const grad = ctx.createLinearGradient(0, pad, 0, dh);
    grad.addColorStop(0, 'rgba(0,212,255,0.15)');
    grad.addColorStop(1, 'rgba(0,212,255,0)');
    ctx.fillStyle = grad;
    ctx.fill();
}
// ══════════════════════════════════════════════
// MIND PANEL — EMOTION DETAIL
// ══════════════════════════════════════════════
function updateEmotionDetail(emotion) {
    const container = document.getElementById('emotion-detail-content');
    if (!container) return;
    const desc = emotion.description || '';
    const words = emotion.expression_words || [];
    const allEmotions = emotion.all_emotions || {};
    const activeCount = emotion.active_count || 0;
    let html = '';
    // Description
    if (desc) {
        html += `<div class="emotion-desc-text">${escapeHtml(desc)}</div>`;
    }
    // Expression words
    if (words.length > 0) {
        html += '<div class="expression-words">';
        words.forEach(w => {
            html += `<span class="expression-word">${escapeHtml(w)}</span>`;
        });
        html += '</div>';
    }
    // Active emotions list
    const emEntries = Object.entries(allEmotions).filter(([_, v]) => typeof v === 'number' && v > 0.02);
    if (emEntries.length > 0) {
        html += '<div class="active-emotions-list">';
        emEntries.sort((a, b) => b[1] - a[1]);
        emEntries.forEach(([name, val]) => {
            const pct = Math.round(val * 100);
            const color = getEmotionColor(name);
            html += `<div class="active-emotion-chip">`;
            html += `${getEmotionEmoji(name)} ${capitalize(name)}`;
            html += `<div class="ae-bar"><div class="ae-fill" style="width:${pct}%;background:${color}"></div></div>`;
            html += `</div>`;
        });
        html += '</div>';
    }
    if (html) {
        container.innerHTML = html;
    } else {
        container.innerHTML = `<span class="muted-text">Condition: ${capitalize(emotion.primary || 'neutral')} at ${((emotion.intensity || 0) * 100).toFixed(0)}% intensity</span>`;
    }
}
// ══════════════════════════════════════════════
// EVOLUTION PANEL HELPERS
// ══════════════════════════════════════════════
// ══════════════════════════════════════════════
let _lastKnowledgeDeepFetch = 0;
function fetchKnowledgeDeep() {
    // Only fetch when knowledge page is visible and throttle to every 5s
    if (!document.querySelector('#page-knowledge.active')) return;
    const now = Date.now();
    if (now - _lastKnowledgeDeepFetch < 5000) return;
    _lastKnowledgeDeepFetch = now;
    fetch('/api/knowledge/deep')
        .then(r => r.json())
        .then(data => {
            if (data.error) return;
            // Overwrite panels with reliable data from dedicated endpoint
            if (data.recent_learnings && data.recent_learnings.length > 0) {
                updateRecentLearnings(data.recent_learnings);
            }
            if (data.top_topics && Object.keys(data.top_topics).length > 0) {
                updateTopTopics(data.top_topics);
            }
            if (data.source_breakdown && Object.keys(data.source_breakdown).length > 0) {
                updateSourceAnalytics(data.source_breakdown);
            }
            if (data.timeline && data.timeline.length > 0) {
                updateLearningTimeline(data.timeline);
            }
            if (data.total_entries) {
                setText('know-entries', data.total_entries);
                setSVGGauge('know-entries-ring', Math.min(data.total_entries, 500), 500);
            }
            if (data.unique_topics) {
                setText('know-topics', data.unique_topics);
            }
            if (data.confidence) {
                const cp = Math.round(data.confidence * 100);
                setText('know-confidence', `${cp}%`);
                setSVGGauge('know-confidence-ring', cp);
            }
            if (data.learning_velocity) {
                setText('know-research-velocity', data.learning_velocity);
            }
        })
        .catch(() => { });
    // Also fetch knowledge graph
    fetchKnowledgeGraph();
}
// ══════════════════════════════════════════════
// KNOWLEDGE PANEL HELPERS
// ══════════════════════════════════════════════
function updateCuriosityQueue(topics) {
    const container = document.getElementById('know-curiosity-queue');
    if (!container) return;
    if (!topics || topics.length === 0) {
        container.innerHTML = '<div class="muted-text">No curiosity topics yet</div>';
        return;
    }
    const urgencyMap = { IDLE: 0, LOW: 0.25, MODERATE: 0.5, HIGH: 0.75, BURNING: 1.0 };
    container.innerHTML = topics.map(t => {
        let urgRaw = t.urgency;
        if (typeof urgRaw === 'string') urgRaw = urgencyMap[urgRaw.toUpperCase()] ?? 0.5;
        const urgency = Math.round((urgRaw || 0.5) * 100);
        const color = urgency > 70 ? '#ff4466' : urgency > 40 ? '#fbbf24' : '#00ff88';
        const urgLabel = urgency > 70 ? 'BURNING' : urgency > 40 ? 'MODERATE' : 'LOW';
        const urgLabelColor = urgency > 70 ? 'rgba(255,68,102,0.15);border:1px solid rgba(255,68,102,0.3);color:#ff4466'
            : urgency > 40 ? 'rgba(251,191,36,0.15);border:1px solid rgba(251,191,36,0.3);color:#fbbf24'
                : 'rgba(0,255,136,0.15);border:1px solid rgba(0,255,136,0.3);color:#00ff88';
        const sourceIcon = t.source === 'user' ? 'fa-user' : t.source === 'knowledge_gap' ? 'fa-puzzle-piece' : t.source === 'conversation' ? 'fa-comments' : 'fa-robot';
        return `<div class="curiosity-item">
            <div class="curiosity-topic">${escapeHtml(t.topic)}</div>
            <div class="curiosity-meta">
                <span class="curiosity-source"><i class="fas ${sourceIcon}"></i> ${escapeHtml(t.source || 'auto')}</span>
                <span class="curiosity-urgency-label" style="background:${urgLabelColor}">${urgLabel}</span>
                <button class="curiosity-research-btn" onclick="queueResearch('${escapeHtml(t.topic).replace(/'/g, "\\'")}')" title="Research this topic">
                    <i class="fas fa-flask"></i>
                </button>
            </div>
            <div class="urgency-bar"><div class="urgency-fill" style="width:${urgency}%;background:${color}"></div><span class="urgency-val">${urgency}%</span></div>
        </div>`;
    }).join('');
}
function updateRecentLearnings(learnings) {
    const container = document.getElementById('know-recent-learnings');
    if (!container) return;
    if (!learnings || learnings.length === 0) {
        container.innerHTML = '<div class="muted-text">No recent learnings</div>';
        return;
    }
    const sourceColors = { wikipedia: '#00d4ff', web: '#a855f7', research: '#00ff88', llm: '#fbbf24', user: '#ec4899', self_generated: '#f97316', unknown: '#6b7280' };
    const sourceIcons = { wikipedia: 'fa-wikipedia-w', web: 'fa-globe', research: 'fa-flask', llm: 'fa-brain', user: 'fa-user', self_generated: 'fa-cog', unknown: 'fa-question' };
    container.innerHTML = learnings.map(l => {
        const srcColor = sourceColors[l.source] || sourceColors.unknown;
        const srcIcon = sourceIcons[l.source] || sourceIcons.unknown;
        const impPct = Math.round((l.importance || 0.5) * 100);
        const impColor = impPct > 70 ? '#00ff88' : impPct > 40 ? '#fbbf24' : '#6b7280';
        const dateStr = l.date ? `<div class="learning-date"><i class="fas fa-calendar-alt"></i> ${escapeHtml(l.date)}</div>` : '';
        return `<div class="learning-item">
            <div class="learning-header">
                <div class="learning-topic"><i class="fas fa-lightbulb"></i> ${escapeHtml(l.topic)}</div>
                <span class="learning-source-badge" style="background:${srcColor}22;border:1px solid ${srcColor}44;color:${srcColor}"><i class="fas ${srcIcon}"></i> ${l.source || 'unknown'}</span>
            </div>
            <div class="learning-summary">${escapeHtml(l.summary || '')}</div>
            <div class="learning-footer">
                ${dateStr}
                <div class="learning-importance">
                    <span class="imp-label">Importance</span>
                    <div class="imp-bar"><div class="imp-fill" style="width:${impPct}%;background:${impColor}"></div></div>
                    <span class="imp-val">${impPct}%</span>
                </div>
            </div>
        </div>`;
    }).join('');
}
function updateTopTopics(topics) {
    const container = document.getElementById('know-top-topics');
    if (!container) return;
    const entries = Object.entries(topics || {});
    if (entries.length === 0) {
        container.innerHTML = '<span class="muted-text">No topics yet</span>';
        return;
    }
    const maxCount = Math.max(...entries.map(([_, v]) => v), 1);
    const colors = ['#00d4ff', '#00ff88', '#a855f7', '#fbbf24', '#ec4899', '#f97316', '#06b6d4', '#ef4444', '#14b8a6', '#6366f1'];
    container.innerHTML = entries.map(([name, count], i) => {
        const size = 0.72 + (count / maxCount) * 0.55;
        const color = colors[i % colors.length];
        return `<span class="topic-tag" style="font-size:${size}rem;background:${color}15;border:1px solid ${color}33;color:${color};cursor:pointer" onclick="document.getElementById('know-search-input').value='${escapeHtml(name)}';searchKnowledge()">${escapeHtml(name)}<sup>${count}</sup></span>`;
    }).join('');
}
function updateResearchActivity(research, velocity, gapsCount) {
    const statusEl = document.getElementById('know-research-status');
    if (!statusEl) return;
    const isActive = research.is_researching || false;
    const indEl = statusEl.querySelector('.research-indicator');
    if (indEl) {
        indEl.className = `research-indicator ${isActive ? 'active' : 'idle'}`;
        const labelEl = indEl.querySelector('.research-label');
        if (labelEl) {
            labelEl.textContent = isActive
                ? `Researching: ${research.current_topic || 'Unknown topic'}...`
                : 'Idle — No active research';
        }
    }
    setText('know-research-total', research.total_sessions || 0);
    setText('know-research-success', research.successful || 0);
    setText('know-research-velocity', velocity || 0);
    setText('know-gaps-count', gapsCount || 0);
}
function updateSourceAnalytics(breakdown) {
    const container = document.getElementById('know-source-grid');
    if (!container) return;
    const entries = Object.entries(breakdown || {});
    if (entries.length === 0) {
        container.innerHTML = '<div class="muted-text">No source data yet</div>';
        return;
    }
    const srcMeta = {
        wikipedia: { icon: 'fa-wikipedia-w', color: '#00d4ff', label: 'Wikipedia' },
        web: { icon: 'fa-globe', color: '#a855f7', label: 'Web' },
        research: { icon: 'fa-flask', color: '#00ff88', label: 'Research' },
        llm: { icon: 'fa-brain', color: '#fbbf24', label: 'LLM' },
        user: { icon: 'fa-user', color: '#ec4899', label: 'User' },
        self_generated: { icon: 'fa-cog', color: '#f97316', label: 'Self-Gen' },
        unknown: { icon: 'fa-question', color: '#6b7280', label: 'Unknown' },
    };
    const totalEntries = entries.reduce((s, [_, d]) => s + (d.count || 0), 0) || 1;
    container.innerHTML = entries.map(([src, d]) => {
        const meta = srcMeta[src] || srcMeta.unknown;
        const pct = Math.round((d.count / totalEntries) * 100);
        return `<div class="source-card">
            <div class="source-icon" style="color:${meta.color}"><i class="fas ${meta.icon}"></i></div>
            <div class="source-info">
                <div class="source-name">${meta.label}</div>
                <div class="source-count">${d.count} entries</div>
            </div>
            <div class="source-bar-wrap">
                <div class="source-bar"><div class="source-bar-fill" style="width:${pct}%;background:${meta.color}"></div></div>
                <span class="source-pct">${pct}%</span>
            </div>
            <div class="source-meta">
                <span class="source-imp">Avg imp: ${(d.avg_importance || 0).toFixed(1)}</span>
            </div>
        </div>`;
    }).join('');
}
function updateKnowledgeGaps(gaps) {
    const container = document.getElementById('know-gaps-list');
    if (!container) return;
    if (!gaps || gaps.length === 0) {
        container.innerHTML = '<div class="muted-text">No gaps detected — knowledge coverage is strong</div>';
        return;
    }
    container.innerHTML = gaps.map(g => {
        const impactPct = Math.round((g.impact || 0.5) * 100);
        const impactColor = impactPct > 70 ? '#ff4466' : impactPct > 40 ? '#fbbf24' : '#00ff88';
        return `<div class="gap-item">
            <div class="gap-header">
                <span class="gap-area"><i class="fas fa-exclamation-triangle" style="color:${impactColor}"></i> ${escapeHtml(g.area)}</span>
                <button class="curiosity-research-btn" onclick="queueResearch('${escapeHtml(g.area).replace(/'/g, "\\'")}')" title="Research this gap">
                    <i class="fas fa-flask"></i>
                </button>
            </div>
            <div class="gap-desc">${escapeHtml(g.description)}</div>
            <div class="gap-impact">
                <span>Impact</span>
                <div class="imp-bar"><div class="imp-fill" style="width:${impactPct}%;background:${impactColor}"></div></div>
                <span>${impactPct}%</span>
            </div>
        </div>`;
    }).join('');
}
let _knowledgeGraphFetched = false;
function fetchKnowledgeGraph() {
    fetch('/api/knowledge/graph')
        .then(r => r.json())
        .then(data => drawKnowledgeGraph(data.nodes || [], data.edges || []))
        .catch(() => { });
}
function drawKnowledgeGraph(nodes, edges) {
    const canvas = document.getElementById('know-graph-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);
    if (nodes.length === 0) {
        ctx.fillStyle = 'rgba(255,255,255,0.3)';
        ctx.font = '13px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('No knowledge graph data', W / 2, H / 2);
        return;
    }
    // Position nodes in a force-like layout (simple circular)
    const cx = W / 2, cy = H / 2;
    const nodePositions = {};
    nodes.forEach((n, i) => {
        const angle = (2 * Math.PI * i) / nodes.length - Math.PI / 2;
        const radius = Math.min(W, H) * 0.35;
        nodePositions[n.id] = {
            x: cx + radius * Math.cos(angle),
            y: cy + radius * Math.sin(angle),
            node: n
        };
    });
    // Draw edges
    edges.forEach(e => {
        const s = nodePositions[e.source], t = nodePositions[e.target];
        if (!s || !t) return;
        ctx.beginPath();
        ctx.moveTo(s.x, s.y);
        ctx.lineTo(t.x, t.y);
        ctx.strokeStyle = `rgba(255,255,255,${0.06 + (e.weight || 1) * 0.04})`;
        ctx.lineWidth = Math.min(3, 0.5 + (e.weight || 1) * 0.5);
        ctx.stroke();
    });
    // Draw nodes
    nodes.forEach(n => {
        const pos = nodePositions[n.id];
        if (!pos) return;
        const r = Math.max(4, Math.min(18, n.size / 3));
        // Glow
        const gradient = ctx.createRadialGradient(pos.x, pos.y, 0, pos.x, pos.y, r * 2.5);
        gradient.addColorStop(0, n.color + '44');
        gradient.addColorStop(1, 'transparent');
        ctx.fillStyle = gradient;
        ctx.fillRect(pos.x - r * 2.5, pos.y - r * 2.5, r * 5, r * 5);
        // Node circle
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2);
        ctx.fillStyle = n.color;
        ctx.fill();
        ctx.strokeStyle = n.color + '88';
        ctx.lineWidth = 1;
        ctx.stroke();
        // Label
        ctx.fillStyle = 'rgba(255,255,255,0.85)';
        ctx.font = `${Math.max(8, 10)}px Inter, sans-serif`;
        ctx.textAlign = 'center';
        ctx.fillText(n.label.length > 15 ? n.label.slice(0, 13) + '…' : n.label, pos.x, pos.y + r + 12);
    });
    // Legend
    const legend = document.getElementById('know-graph-legend');
    if (legend) {
        legend.innerHTML = `<span class="graph-stat">${nodes.length} topics</span><span class="graph-stat">${edges.length} connections</span>`;
    }
}
function updateLearningTimeline(timeline) {
    const canvas = document.getElementById('know-timeline-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);
    if (!timeline || timeline.length === 0) {
        ctx.fillStyle = 'rgba(255,255,255,0.3)';
        ctx.font = '13px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('No timeline data yet', W / 2, H / 2);
        return;
    }
    const pad = { l: 40, r: 20, t: 15, b: 30 };
    const gW = W - pad.l - pad.r, gH = H - pad.t - pad.b;
    const maxVal = Math.max(...timeline.map(d => d.count), 1);
    // Grid lines
    ctx.strokeStyle = 'rgba(255,255,255,0.06)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
        const y = pad.t + (gH / 4) * i;
        ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke();
    }
    // Area fill
    const gradient = ctx.createLinearGradient(0, pad.t, 0, H - pad.b);
    gradient.addColorStop(0, 'rgba(0, 212, 255, 0.25)');
    gradient.addColorStop(1, 'rgba(0, 212, 255, 0.02)');
    ctx.beginPath();
    ctx.moveTo(pad.l, H - pad.b);
    timeline.forEach((d, i) => {
        const x = pad.l + (gW / Math.max(1, timeline.length - 1)) * i;
        const y = pad.t + gH * (1 - d.count / maxVal);
        if (i === 0) ctx.lineTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.lineTo(pad.l + gW, H - pad.b);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();
    // Line
    ctx.beginPath();
    timeline.forEach((d, i) => {
        const x = pad.l + (gW / Math.max(1, timeline.length - 1)) * i;
        const y = pad.t + gH * (1 - d.count / maxVal);
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.strokeStyle = '#00d4ff';
    ctx.lineWidth = 2;
    ctx.stroke();
    // Data points
    timeline.forEach((d, i) => {
        const x = pad.l + (gW / Math.max(1, timeline.length - 1)) * i;
        const y = pad.t + gH * (1 - d.count / maxVal);
        ctx.beginPath();
        ctx.arc(x, y, 3, 0, Math.PI * 2);
        ctx.fillStyle = '#00d4ff';
        ctx.fill();
    });
    // X-axis labels
    ctx.fillStyle = 'rgba(255,255,255,0.4)';
    ctx.font = '9px Inter, sans-serif';
    ctx.textAlign = 'center';
    const step = Math.max(1, Math.floor(timeline.length / 7));
    timeline.forEach((d, i) => {
        if (i % step === 0 || i === timeline.length - 1) {
            const x = pad.l + (gW / Math.max(1, timeline.length - 1)) * i;
            const label = d.date ? d.date.slice(5) : '';
            ctx.fillText(label, x, H - 8);
        }
    });
    // Y-axis labels
    ctx.textAlign = 'right';
    for (let i = 0; i <= 4; i++) {
        const val = Math.round(maxVal * (4 - i) / 4);
        const y = pad.t + (gH / 4) * i + 4;
        ctx.fillText(val, pad.l - 6, y);
    }
}
async function searchKnowledge() {
    const input = document.getElementById('know-search-input');
    const detail = document.getElementById('know-detail');
    if (!input || !detail) return;
    const q = input.value.trim();
    if (!q) { detail.innerHTML = ''; return; }
    detail.innerHTML = '<div class="muted-text"><i class="fas fa-spinner fa-spin"></i> Searching...</div>';
    try {
        const res = await fetch(`/api/knowledge/search?q=${encodeURIComponent(q)}`);
        const data = await res.json();
        const results = data.results || [];
        if (results.length === 0) {
            detail.innerHTML = '<div class="muted-text">No results found</div>';
            return;
        }
        const srcColors = { wikipedia: '#00d4ff', web: '#a855f7', research: '#00ff88', llm: '#fbbf24', user: '#ec4899', self_generated: '#f97316', unknown: '#6b7280' };
        const srcIcons = { wikipedia: 'fa-wikipedia-w', web: 'fa-globe', research: 'fa-flask', llm: 'fa-brain', user: 'fa-user', self_generated: 'fa-cog', unknown: 'fa-question' };
        detail.innerHTML = `<div class="search-results-header">${results.length} result${results.length !== 1 ? 's' : ''} for "${escapeHtml(q)}"</div>` +
            results.map(r => {
                const color = srcColors[r.source] || srcColors.unknown;
                const icon = srcIcons[r.source] || srcIcons.unknown;
                const relPct = Math.round((r.relevance || 0) * 100);
                const impPct = Math.round((r.importance || 0) * 100);
                return `<div class="knowledge-result">
                    <div class="result-header">
                        <div class="result-topic"><i class="fas fa-file-alt"></i> ${escapeHtml(r.title || r.topic || '?')}</div>
                        <span class="learning-source-badge" style="background:${color}22;border:1px solid ${color}44;color:${color}"><i class="fas ${icon}"></i> ${r.source}</span>
                    </div>
                    <div class="result-summary">${escapeHtml(r.summary || r.content || '')}</div>
                    <div class="result-footer">
                        <div class="result-metric"><span>Relevance</span><div class="imp-bar"><div class="imp-fill" style="width:${relPct}%;background:#00d4ff"></div></div><span>${relPct}%</span></div>
                        <div class="result-metric"><span>Importance</span><div class="imp-bar"><div class="imp-fill" style="width:${impPct}%;background:#00ff88"></div></div><span>${impPct}%</span></div>
                        ${r.date ? `<span class="result-date"><i class="fas fa-calendar-alt"></i> ${escapeHtml(r.date)}</span>` : ''}
                    </div>
                </div>`;
            }).join('');
    } catch (e) {
        detail.innerHTML = '<div class="muted-text">Search failed</div>';
    }
}
async function queueResearch(topic) {
    try {
        const res = await fetch('/api/research/queue', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic: topic, urgency: 'high' })
        });
        const data = await res.json();
        if (data.status === 'ok' || data.queued) {
            const btn = event?.target?.closest?.('.curiosity-research-btn');
            if (btn) { btn.innerHTML = '<i class="fas fa-check"></i>'; btn.style.color = '#00ff88'; }
        }
    } catch (e) { console.error('Queue research failed:', e); }
}
// Periodically fetch knowledge graph (every 30s when on knowledge page)
setInterval(() => {
    if (document.querySelector('#page-knowledge.active')) fetchKnowledgeGraph();
}, 30000);
// ══════════════════════════════════════════════
// SYSTEM PANEL HELPERS
// ══════════════════════════════════════════════
function updateCoreBars(cores) {
    const container = document.getElementById('sys-core-bars');
    if (!container) return;
    if (cores.length === 0) {
        container.innerHTML = '<div class="muted-text">No core data</div>';
        return;
    }
    container.innerHTML = cores.map((pct, i) => {
        const color = pct > 80 ? '#ff4466' : pct > 50 ? '#fbbf24' : '#00d4ff';
        return `<div class="core-bar-row">
            <span class="core-label">C${i}</span>
            <div class="core-bar-track"><div class="core-bar-fill" style="width:${pct}%;background:${color}"></div></div>
            <span class="core-val">${Math.round(pct)}%</span>
        </div>`;
    }).join('');
}
function updateMemBreakdown(mb) {
    if (!mb.total_gb) return;
    const totalGb = mb.total_gb || 1;
    const usedPct = ((mb.used_gb || 0) / totalGb * 100).toFixed(1);
    const cachedPct = ((mb.cached_gb || 0) / totalGb * 100).toFixed(1);
    const freePct = (100 - usedPct - cachedPct).toFixed(1);
    const usedEl = document.getElementById('sys-mem-used');
    const cachedEl = document.getElementById('sys-mem-cached');
    const freeEl = document.getElementById('sys-mem-free');
    if (usedEl) usedEl.style.width = `${usedPct}%`;
    if (cachedEl) cachedEl.style.width = `${cachedPct}%`;
    if (freeEl) freeEl.style.width = `${freePct}%`;
    setText('sys-mem-used-val', mb.used_gb || 0);
    setText('sys-mem-cached-val', mb.cached_gb || 0);
    setText('sys-mem-free-val', mb.available_gb || 0);
}
function updateProcessTable(procs) {
    const body = document.getElementById('sys-proc-body');
    if (!body) return;
    if (procs.length === 0) {
        body.innerHTML = '<tr><td colspan="4" class="muted-text">No process data</td></tr>';
        return;
    }
    body.innerHTML = procs.map(p => {
        return `<tr><td>${escapeHtml(p.name || '?')}</td><td>${p.pid || '--'}</td><td>${(p.cpu_percent || 0).toFixed(1)}</td><td>${(p.memory_percent || 0).toFixed(1)}</td></tr>`;
    }).join('');
}
function updateBrainResources(br) {
    setText('sys-brain-mem', `${br.memory_mb || '--'} MB`);
    setText('sys-brain-threads', br.threads || '--');
    setText('sys-brain-cpu', `${br.cpu_pct || '--'}%`);
}
// ══════════════════════════════════════════════
// ANIMATED VALUE COUNTER
// ══════════════════════════════════════════════
function animateValue(elementId, newValue) {
    const el = document.getElementById(elementId);
    if (!el) return;
    newValue = parseInt(newValue) || 0;
    const oldValue = animatedValues[elementId] || 0;
    if (oldValue === newValue) { el.textContent = newValue.toLocaleString(); return; }
    animatedValues[elementId] = newValue;
    const diff = newValue - oldValue;
    const duration = Math.min(800, Math.max(200, Math.abs(diff) * 10));
    const startTime = performance.now();
    const animate = (now) => {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // easeOutCubic
        const current = Math.round(oldValue + diff * eased);
        el.textContent = current.toLocaleString();
        if (progress < 1) requestAnimationFrame(animate);
        else {
            el.textContent = newValue.toLocaleString();
            el.classList.add('value-flash');
            setTimeout(() => el.classList.remove('value-flash'), 600);
        }
    };
    requestAnimationFrame(animate);
}
// ══════════════════════════════════════════════
// PARTICLE BACKGROUND (Neural Network)
// ══════════════════════════════════════════════
function initParticleBackground() {
    particleCanvas = document.getElementById('particle-bg');
    if (!particleCanvas) return;
    particleCtx = particleCanvas.getContext('2d');
    resizeParticleCanvas();
    window.addEventListener('resize', resizeParticleCanvas);
    for (let i = 0; i < PARTICLE_COUNT; i++) {
        particles.push({
            x: Math.random() * particleCanvas.width,
            y: Math.random() * particleCanvas.height,
            vx: (Math.random() - 0.5) * 0.4,
            vy: (Math.random() - 0.5) * 0.4,
            r: Math.random() * 2 + 1,
            hue: Math.random() * 60 + 180, // cyan to blue range
        });
    }
    animateParticles();
}
function resizeParticleCanvas() {
    if (!particleCanvas) return;
    particleCanvas.width = window.innerWidth;
    particleCanvas.height = window.innerHeight;
}
function animateParticles() {
    if (!particleCtx || !particleCanvas) return;
    particleCtx.clearRect(0, 0, particleCanvas.width, particleCanvas.height);
    const w = particleCanvas.width, h = particleCanvas.height;
    // Update and draw particles
    for (const p of particles) {
        p.x += p.vx; p.y += p.vy;
        if (p.x < 0 || p.x > w) p.vx *= -1;
        if (p.y < 0 || p.y > h) p.vy *= -1;
        particleCtx.beginPath();
        particleCtx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        particleCtx.fillStyle = `hsla(${p.hue}, 100%, 70%, 0.6)`;
        particleCtx.fill();
    }
    // Draw connections
    for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
            const dx = particles[i].x - particles[j].x;
            const dy = particles[i].y - particles[j].y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < CONNECTION_DISTANCE) {
                const alpha = (1 - dist / CONNECTION_DISTANCE) * 0.15;
                particleCtx.beginPath();
                particleCtx.moveTo(particles[i].x, particles[i].y);
                particleCtx.lineTo(particles[j].x, particles[j].y);
                particleCtx.strokeStyle = `rgba(0, 212, 255, ${alpha})`;
                particleCtx.lineWidth = 0.5;
                particleCtx.stroke();
            }
        }
    }
    particleRAF = requestAnimationFrame(animateParticles);
}
// ══════════════════════════════════════════════
// COMMAND PALETTE (Ctrl+K)
// ══════════════════════════════════════════════
const commandPaletteItems = [
    { label: 'Dashboard', icon: 'fa-th-large', action: () => switchPage('dashboard') },
    { label: 'Chat', icon: 'fa-comments', action: () => switchPage('chat') },
    { label: 'Mind', icon: 'fa-brain', action: () => switchPage('mind') },
    { label: 'Evolution', icon: 'fa-dna', action: () => switchPage('evolution') },
    { label: 'Knowledge', icon: 'fa-book', action: () => switchPage('knowledge') },
    { label: 'System', icon: 'fa-server', action: () => switchPage('system') },
    { label: 'Refresh Data', icon: 'fa-sync-alt', action: () => fetchStats() },
    { label: 'Export JSON', icon: 'fa-download', action: () => exportDashboardData() },
    { label: 'Toggle Fullscreen', icon: 'fa-expand', action: () => toggleFullscreen() },
    { label: 'Clear Chat', icon: 'fa-trash', action: () => { if (confirm('Clear chat history?')) clearChat(); } },
    { label: 'Logout', icon: 'fa-sign-out-alt', action: () => doLogout() },
];
function toggleCommandPalette() {
    const modal = document.getElementById('command-palette-modal');
    if (!modal) return;
    const isOpen = modal.classList.contains('active');
    if (isOpen) {
        modal.classList.remove('active');
    } else {
        modal.classList.add('active');
        const input = document.getElementById('cmd-palette-input');
        if (input) { input.value = ''; input.focus(); }
        renderCommandPaletteResults('');
    }
}
function renderCommandPaletteResults(query) {
    const list = document.getElementById('cmd-palette-results');
    if (!list) return;
    const q = query.toLowerCase().trim();
    const filtered = q ? commandPaletteItems.filter(i => i.label.toLowerCase().includes(q)) : commandPaletteItems;
    list.innerHTML = filtered.map((item, idx) => `
        <div class="cmd-palette-item${idx === 0 ? ' selected' : ''}" data-idx="${idx}" onclick="executeCommandPaletteItem(${commandPaletteItems.indexOf(item)})">
            <i class="fas ${item.icon}"></i>
            <span>${item.label}</span>
        </div>
    `).join('') || '<div class="cmd-palette-empty">No results found</div>';
}
function executeCommandPaletteItem(idx) {
    const item = commandPaletteItems[idx];
    if (!item) return;
    toggleCommandPalette();
    item.action();
    showToast(`Executed: ${item.label}`, 'info');
}
function handleCommandPaletteKey(e) {
    const list = document.getElementById('cmd-palette-results');
    if (!list) return;
    const items = list.querySelectorAll('.cmd-palette-item');
    let selectedIdx = -1;
    items.forEach((item, i) => { if (item.classList.contains('selected')) selectedIdx = i; });
    if (e.key === 'ArrowDown') {
        e.preventDefault();
        const next = Math.min(selectedIdx + 1, items.length - 1);
        items.forEach(i => i.classList.remove('selected'));
        if (items[next]) items[next].classList.add('selected');
    } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        const prev = Math.max(selectedIdx - 1, 0);
        items.forEach(i => i.classList.remove('selected'));
        if (items[prev]) items[prev].classList.add('selected');
    } else if (e.key === 'Enter') {
        e.preventDefault();
        const selected = list.querySelector('.cmd-palette-item.selected');
        if (selected) selected.click();
    } else if (e.key === 'Escape') {
        toggleCommandPalette();
    }
}
// ══════════════════════════════════════════════
// TOAST NOTIFICATIONS
// ══════════════════════════════════════════════
let toastCounter = 0;
function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const id = `toast-${toastCounter++}`;
    const icons = { info: 'fa-info-circle', success: 'fa-check-circle', warning: 'fa-exclamation-triangle', error: 'fa-times-circle' };
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.id = id;
    toast.innerHTML = `<i class="fas ${icons[type] || icons.info}"></i><span>${message}</span>`;
    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 400);
    }, duration);
}
function showNotification(message, type = 'info', duration = 3000) {
    showToast(message, type, duration);
}
// ══════════════════════════════════════════════
// KEYBOARD SHORTCUTS
// ══════════════════════════════════════════════
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ignore if typing in input/textarea
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            if (e.key === 'Escape') {
                e.target.blur();
                const modal = document.getElementById('command-palette-modal');
                if (modal && modal.classList.contains('active')) toggleCommandPalette();
            }
            return;
        }
        // Ctrl+K / Cmd+K — Command Palette
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            toggleCommandPalette();
            return;
        }
        // Number keys 1-6 for page navigation
        if (e.key >= '1' && e.key <= '6' && !e.ctrlKey && !e.altKey && !e.metaKey) {
            const pages = ['dashboard', 'chat', 'mind', 'evolution', 'knowledge', 'system'];
            switchPage(pages[parseInt(e.key) - 1]);
            return;
        }
        // R — Refresh
        if (e.key === 'r' || e.key === 'R') { fetchStats(); return; }
        // F — Fullscreen
        if (e.key === 'f' || e.key === 'F') { toggleFullscreen(); return; }
        // E — Export
        if (e.key === 'e' || e.key === 'E') { exportDashboardData(); return; }
        if (e.key === '?') { showToast('Shortcuts: 1-6=Pages, R=Refresh, F=Fullscreen, E=Export, Ctrl+K=Command', 'info', 5000); }
    });
}
// ══════════════════════════════════════════════
// EXPORT DASHBOARD DATA
// ══════════════════════════════════════════════
function exportDashboardData() {
    fetchWithAuth('/api/stats')
        .then(r => r.json())
        .then(data => {
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `nexus-dashboard-${new Date().toISOString().slice(0, 10)}.json`;
            a.click();
            URL.revokeObjectURL(url);
            showToast('Dashboard data exported!', 'success');
        })
        .catch(err => showToast(`Export failed: ${err.message}`, 'error'));
}
// ══════════════════════════════════════════════
// FULLSCREEN MODE
// ══════════════════════════════════════════════
function toggleFullscreen() {
    if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().then(() => {
            showToast('Entered fullscreen — press F or Esc to exit', 'info');
        }).catch(() => { });
    } else {
        document.exitFullscreen();
    }
}
// ══════════════════════════════════════════════
// ABILITIES PAGE
// ══════════════════════════════════════════════
let abilitiesData = [];
let abilitiesStats = {};
async function fetchAbilities() {
    try {
        // Fetch abilities list
        const abilitiesRes = await fetch('/api/abilities', { headers: getAuthHeaders() });
        const abilitiesJson = await abilitiesRes.json();
        abilitiesData = abilitiesJson.abilities || [];
        // Fetch ability stats
        const statsRes = await fetch('/api/abilities/stats', { headers: getAuthHeaders() });
        const statsJson = await statsRes.json();
        abilitiesStats = statsJson || {};
        // Fetch invocation history
        const historyRes = await fetch('/api/abilities/history?limit=20', { headers: getAuthHeaders() });
        const historyJson = await historyRes.json();
        updateAbilitiesUI(abilitiesData, abilitiesStats);
        updateAbilitiesHistory(historyJson.history || []);
        updateAbilityCategories(abilitiesData);
        setText('abilities-last-update', `Last update: ${new Date().toLocaleTimeString()}`);
    } catch (e) {
        console.error('Failed to fetch abilities:', e);
        showToast('Failed to load abilities', 'error');
    }
}
function updateAbilitiesUI(abilities, stats) {
    // Update stat cards
    const total = abilities.length;
    const successCount = stats.successful_invocations || 0;
    const cooldownCount = abilities.filter(a => isOnCooldown(a)).length;
    const totalInvokes = stats.total_invocations || 0;
    setText('abilities-total-count', total);
    setText('abilities-success-count', successCount);
    setText('abilities-cooldown-count', cooldownCount);
    setText('abilities-invoke-count', totalInvokes);
    // Update abilities grid
    const grid = document.getElementById('abilities-grid');
    if (!grid) return;
    if (abilities.length === 0) {
        grid.innerHTML = '<div class="muted-text">No abilities registered</div>';
        return;
    }
    grid.innerHTML = abilities.map((ability, idx) => {
        const catClass = getCategoryClass(ability.category);
        const riskClass = `risk-${ability.risk?.toLowerCase() || 'low'}`;
        const onCooldown = isOnCooldown(ability);
        const cooldownText = onCooldown ? getCooldownText(ability) : '';
        const catIcon = getCategoryIcon(ability.category);
        return `
            <div class="ability-card ${onCooldown ? 'on-cooldown' : ''} ability-animate-in" data-name="${escapeHtml(ability.name)}" style="animation-delay:${idx * 40}ms">
                <div class="ability-card-header">
                    <span class="ability-name">${catIcon} ${escapeHtml(ability.name)}</span>
                    <span class="ability-category-badge ${catClass}">${capitalize((ability.category || 'system').replace(/_/g, ' '))}</span>
                </div>
                <div class="ability-description">${escapeHtml(ability.description || 'No description')}</div>
                <div class="ability-meta">
                    <span class="ability-meta-item"><i class="fas fa-clock"></i> ${ability.cooldown_seconds || 0}s CD</span>
                    <span class="ability-meta-item"><i class="fas fa-bolt"></i> ${ability.invoke_count || 0} uses</span>
                    <span class="ability-risk ${riskClass}">${capitalize(ability.risk || 'low')}</span>
                </div>
                ${onCooldown ? `<div class="muted-text" style="font-size:.7rem;margin-top:6px;"><i class="fas fa-hourglass-half"></i> ${cooldownText}</div>` : ''}
                <button class="ability-invoke-btn" onclick="showInvokeModal('${escapeHtml(ability.name)}')" ${onCooldown ? 'disabled' : ''}>
                    <i class="fas fa-play"></i> Invoke
                </button>
            </div>
        `;
    }).join('');
}
function getCategoryClass(category) {
    const cat = (category || 'system').toLowerCase();
    const map = {
        'system': 'cat-system', 'system_control': 'cat-system',
        'cognition': 'cat-cognition', 'cognitive': 'cat-cognition',
        'communication': 'cat-communication', 'interaction': 'cat-communication',
        'self_evolution': 'cat-evolution', 'self_modification': 'cat-evolution',
        'learning': 'cat-learning', 'research': 'cat-research',
        'memory': 'cat-memory',
        'body': 'cat-body',
        'personality': 'cat-personality',
        'consciousness': 'cat-consciousness',
        'emotion': 'cat-emotion',
        'monitoring': 'cat-monitoring',
    };
    return map[cat] || 'cat-system';
}
function getCategoryIcon(category) {
    const cat = (category || 'system').toLowerCase();
    const icons = {
        'system': '⚙️', 'self_evolution': '🧬', 'learning': '📚', 'research': '🔬',
        'cognition': '🧠', 'memory': '💾', 'body': '🖥️', 'personality': '🎭',
        'consciousness': '✨', 'emotion': '💫', 'communication': '💬', 'monitoring': '📡',
    };
    return icons[cat] || '⚡';
}
function isOnCooldown(ability) {
    if (!ability.last_invoked) return false;
    const lastInvoked = new Date(ability.last_invoked);
    const cooldownMs = (ability.cooldown_seconds || 0) * 1000;
    return (Date.now() - lastInvoked.getTime()) < cooldownMs;
}
function getCooldownText(ability) {
    if (!ability.last_invoked) return '';
    const lastInvoked = new Date(ability.last_invoked);
    const cooldownMs = (ability.cooldown_seconds || 0) * 1000;
    const elapsed = Date.now() - lastInvoked.getTime();
    const remaining = Math.max(0, cooldownMs - elapsed);
    const seconds = Math.ceil(remaining / 1000);
    return `Cooldown: ${seconds}s remaining`;
}
function updateAbilitiesHistory(history) {
    const body = document.getElementById('abilities-history-body');
    if (!body) return;
    if (history.length === 0) {
        body.innerHTML = '<tr><td colspan="4" class="muted-text">No invocations yet</td></tr>';
        return;
    }
    body.innerHTML = history.map(h => {
        const successIcon = h.success
            ? '<i class="fas fa-check-circle" style="color:#00ff88"></i>'
            : '<i class="fas fa-times-circle" style="color:#ff4466"></i>';
        const time = h.timestamp ? new Date(h.timestamp).toLocaleTimeString() : '--';
        const duration = h.duration_ms ? `${h.duration_ms}ms` : '--';
        return `<tr>
            <td>${escapeHtml(h.ability_name || h.name || '?')}</td>
            <td class="muted-text">${time}</td>
            <td>${successIcon} ${h.success ? 'Success' : 'Failed'}</td>
            <td class="muted-text">${duration}</td>
        </tr>`;
    }).join('');
}
function updateAbilityCategories(abilities) {
    // Group abilities by category dynamically
    const grouped = {};
    abilities.forEach(a => {
        const cat = (a.category || 'system').toLowerCase();
        if (!grouped[cat]) grouped[cat] = [];
        grouped[cat].push(a);
    });
    // Update the 3 legacy static category boxes
    const legacyMap = {
        'abilities-cat-system': a => ['system', 'monitoring'].includes((a.category || '').toLowerCase()),
        'abilities-cat-cognitive': a => ['cognition', 'consciousness', 'emotion'].includes((a.category || '').toLowerCase()),
        'abilities-cat-interaction': a => ['communication', 'personality'].includes((a.category || '').toLowerCase()),
    };
    Object.entries(legacyMap).forEach(([elId, filterFn]) => {
        const el = document.getElementById(elId);
        if (!el) return;
        const filtered = abilities.filter(filterFn);
        if (filtered.length === 0) {
            el.innerHTML = '<div class="muted-text">No abilities</div>';
            return;
        }
        el.innerHTML = filtered.map(a => `
            <div class="ability-list-item">
                <span>${getCategoryIcon(a.category)} ${escapeHtml(a.name)}</span>
                <span class="ability-count">${a.invoke_count || 0}</span>
            </div>
        `).join('');
    });
}
// Invoke Modal
let currentInvokeAbility = null;
function showInvokeModal(abilityName) {
    const ability = abilitiesData.find(a => a.name === abilityName);
    if (!ability) return;
    currentInvokeAbility = ability;
    // Create modal overlay
    let overlay = document.getElementById('invoke-modal-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'invoke-modal-overlay';
        overlay.className = 'invoke-modal-overlay';
        overlay.onclick = (e) => { if (e.target === overlay) hideInvokeModal(); };
        document.body.appendChild(overlay);
    }
    // Build params HTML
    const params = ability.parameters || {};
    const paramsHtml = Object.keys(params).length > 0
        ? Object.entries(params).map(([key, spec]) => `
            <div class="invoke-param">
                <label>${escapeHtml(key)} ${spec.required ? '*' : ''}</label>
                <input type="text" id="invoke-param-${escapeHtml(key)}" placeholder="${escapeHtml(spec.default || spec.type || '')}">
            </div>
        `).join('')
        : '<div class="muted-text">No parameters required</div>';
    overlay.innerHTML = `
        <div class="invoke-modal">
            <h3><i class="fas fa-magic"></i> Invoke: ${escapeHtml(ability.name)}</h3>
            <div class="ability-desc">${escapeHtml(ability.description || 'No description')}</div>
            <div class="invoke-params">${paramsHtml}</div>
            <div id="invoke-result"></div>
            <div class="invoke-modal-actions">
                <button class="invoke-btn-cancel" onclick="hideInvokeModal()">Cancel</button>
                <button class="invoke-btn-confirm" onclick="executeInvoke()"><i class="fas fa-play"></i> Invoke</button>
            </div>
        </div>
    `;
    overlay.classList.add('active');
}
function hideInvokeModal() {
    const overlay = document.getElementById('invoke-modal-overlay');
    if (overlay) overlay.classList.remove('active');
    currentInvokeAbility = null;
}
async function executeInvoke() {
    if (!currentInvokeAbility) return;
    const resultEl = document.getElementById('invoke-result');
    if (resultEl) resultEl.innerHTML = '<div class="muted-text"><i class="fas fa-spinner fa-spin"></i> Invoking...</div>';
    // Collect params
    const params = {};
    const paramSpecs = currentInvokeAbility.parameters || {};
    Object.keys(paramSpecs).forEach(key => {
        const input = document.getElementById(`invoke-param-${key}`);
        if (input && input.value.trim()) {
            params[key] = input.value.trim();
        }
    });
    try {
        const res = await fetch('/api/abilities/invoke', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ name: currentInvokeAbility.name, params })
        });
        const data = await res.json();
        if (data.success) {
            if (resultEl) {
                resultEl.innerHTML = `<div class="invoke-result success"><i class="fas fa-check-circle"></i> Success! ${escapeHtml(data.message || JSON.stringify(data.result || {}))}</div>`;
            }
            showToast(`Ability "${currentInvokeAbility.name}" executed successfully!`, 'success');
            // Refresh abilities after short delay
            setTimeout(fetchAbilities, 1000);
        } else {
            if (resultEl) {
                resultEl.innerHTML = `<div class="invoke-result error"><i class="fas fa-times-circle"></i> Failed: ${escapeHtml(data.error || 'Unknown error')}</div>`;
            }
            showToast(`Ability failed: ${data.error || 'Unknown error'}`, 'error');
        }
    } catch (e) {
        if (resultEl) {
            resultEl.innerHTML = `<div class="invoke-result error"><i class="fas fa-times-circle"></i> Connection error: ${escapeHtml(e.message)}</div>`;
        }
        showToast('Connection error', 'error');
    }
}
// Add Abilities to command palette
commandPaletteItems.push(
    { label: 'Abilities', icon: 'fa-magic', action: () => switchPage('abilities') },
    { label: 'Refresh Abilities', icon: 'fa-sync-alt', action: () => fetchAbilities() }
);
// ══════════════════════════════════════════════
// SUBSYSTEM PANELS — Fetch & Render
// ══════════════════════════════════════════════
let subsystemPollTimer = null;
let subsystemsLoaded = false;
function startSubsystemPolling() {
    if (subsystemPollTimer) return;
    fetchSubsystems();
    subsystemPollTimer = setInterval(fetchSubsystems, 5000); // Every 5s
}
async function fetchSubsystems() {
    const endpoints = [
        { url: '/api/autonomy', handler: updateAutonomyEnginePanel },
        { url: '/api/worldmodel', handler: updateWorldModelPanel },
        { url: '/api/globalworkspace', handler: updateGlobalWorkspacePanel },
        { url: '/api/cognitiverouter', handler: updateCognitiveRouterPanel },
        { url: '/api/internet', handler: updateInternetAgentPanel },
        { url: '/api/actions', handler: updateActionMemoryPanel },
    ];
    const fetches = endpoints.map(async (ep) => {
        try {
            const res = await fetch(ep.url, { headers: getAuthHeaders() });
            if (res.ok) {
                const data = await res.json();
                ep.handler(data);
            }
        } catch (e) {
            // Silently fail — subsystem may not be loaded
        }
    });
    await Promise.all(fetches);
    subsystemsLoaded = true;
}
// ── Autonomy Engine Panel (System Page subsystem — NOT the Ultron Mode page) ──
function updateAutonomyEnginePanel(data) {
    const running = data.running !== false && !data.error;
    const badge = document.getElementById('autonomy-status-badge');
    if (badge) {
        badge.textContent = running ? '🟢 Active' : '🔴 Not Loaded';
        badge.className = `subsystem-status-badge ${running ? 'status-active' : 'status-inactive'}`;
    }
    if (data.error) return;
    setText('autonomy-actions', data.autonomous_actions || data.actions_taken || data.total_actions || 0);
    setText('autonomy-current-goal', data.current_goal || data.active_goal || 'None');
    setText('autonomy-queue', data.decision_queue || data.queue_size || 0);
    setText('autonomy-decisions', data.decisions_made || data.total_decisions || 0);
    const level = data.autonomy_level || data.level || '--';
    setText('autonomy-level', typeof level === 'number' ? `${Math.round(level * 100)}%` : capitalize(String(level)));
    // Recent actions
    const actionsEl = document.getElementById('autonomy-recent-actions');
    if (actionsEl) {
        const actions = data.recent_actions || data.action_history || [];
        if (actions.length > 0) {
            actionsEl.innerHTML = '<div class="subsystem-list-header"><i class="fas fa-bolt"></i> Recent Actions</div>' +
                actions.slice(0, 5).map(a => {
                    const msg = typeof a === 'object' ? (a.description || a.action || a.type || JSON.stringify(a)) : String(a);
                    return `<div class="subsystem-list-item"><i class="fas fa-chevron-right"></i> ${escapeHtml(msg)}</div>`;
                }).join('');
        } else {
            actionsEl.innerHTML = '';
        }
    }
}
// ── World Model Panel ──
function updateWorldModelPanel(data) {
    const running = data.running !== false && !data.error;
    const badge = document.getElementById('worldmodel-status-badge');
    if (badge) {
        badge.textContent = running ? '🟢 Active' : '🔴 Not Loaded';
        badge.className = `subsystem-status-badge ${running ? 'status-active' : 'status-inactive'}`;
    }
    if (data.error) return;
    setText('wm-user-patterns', data.user_patterns || 0);
    setText('wm-emotional-patterns', data.emotional_patterns || 0);
    setText('wm-task-records', data.task_records || 0);
    setText('wm-predictions-made', data.predictions_made || 0);
    setText('wm-predictions-accurate', data.predictions_accurate || 0);
    // Environment state
    const env = data.environment || {};
    setText('wm-user-emotion', capitalize(env.user_emotional_state || '--'));
    const engagement = env.engagement_level;
    setText('wm-engagement', typeof engagement === 'number' ? `${Math.round(engagement * 100)}%` : '--');
    setText('wm-time-of-day', capitalize(env.time_of_day || '--'));
}
// ── Global Workspace Panel ──
function updateGlobalWorkspacePanel(data) {
    const running = data.running !== false && !data.error;
    const badge = document.getElementById('gw-status-badge');
    if (badge) {
        badge.textContent = running ? '🟢 Active' : '🔴 Not Loaded';
        badge.className = `subsystem-status-badge ${running ? 'status-active' : 'status-inactive'}`;
    }
    if (data.error) return;
    setText('gw-broadcasts', data.total_broadcasts || data.broadcasts || 0);
    setText('gw-coalitions', data.active_coalitions || data.coalitions || 0);
    setText('gw-winner', data.current_winner || data.winner || '--');
    setText('gw-focus', data.attention_focus || data.focus || '--');
    setText('gw-processes', data.registered_processes || data.processes || data.subscribers || 0);
    const integration = data.integration_level || data.integration;
    setText('gw-integration', typeof integration === 'number' ? `${Math.round(integration * 100)}%` : capitalize(String(integration || '--')));
    // Recent broadcasts
    const broadcastEl = document.getElementById('gw-recent-broadcasts');
    if (broadcastEl) {
        const broadcasts = data.recent_broadcasts || [];
        if (broadcasts.length > 0) {
            broadcastEl.innerHTML = '<div class="subsystem-list-header"><i class="fas fa-broadcast-tower"></i> Recent Broadcasts</div>' +
                broadcasts.slice(0, 5).map(b => {
                    const msg = typeof b === 'object' ? (b.content || b.type || JSON.stringify(b)) : String(b);
                    return `<div class="subsystem-list-item"><i class="fas fa-signal"></i> ${escapeHtml(msg)}</div>`;
                }).join('');
        } else {
            broadcastEl.innerHTML = '';
        }
    }
}
// ── Cognitive Router Panel ──
function updateCognitiveRouterPanel(data) {
    const routerData = data.router || data;
    const enginesData = data.engines || [];
    const running = routerData.running !== false && !data.error;
    const badge = document.getElementById('cr-status-badge');
    if (badge) {
        badge.textContent = running ? '🟢 Active' : '🔴 Not Loaded';
        badge.className = `subsystem-status-badge ${running ? 'status-active' : 'status-inactive'}`;
    }
    if (data.error) return;
    setText('cr-routes', routerData.routes_processed || routerData.total_routes || 0);
    setText('cr-active-engine', routerData.active_engine || routerData.last_engine || '--');
    const avgTime = routerData.avg_route_time || routerData.average_time;
    setText('cr-avg-time', typeof avgTime === 'number' ? `${avgTime.toFixed(1)}ms` : '--');
    const cacheRate = routerData.cache_hit_rate || routerData.cache_rate;
    setText('cr-cache-rate', typeof cacheRate === 'number' ? `${Math.round(cacheRate * 100)}%` : '--');
    // Engine count
    const engineCount = enginesData.length || routerData.engine_count || routerData.total_engines || 0;
    setText('cr-engine-count', `${engineCount} engines`);
    // Engine grid
    const gridEl = document.getElementById('cr-engine-grid');
    if (gridEl && enginesData.length > 0) {
        gridEl.innerHTML = enginesData.map(engine => {
            const name = typeof engine === 'object' ? (engine.name || engine.engine || 'Unknown') : String(engine);
            const status = typeof engine === 'object' ? (engine.status || 'ready') : 'ready';
            const invocations = typeof engine === 'object' ? (engine.invocations || engine.invoke_count || 0) : 0;
            const statusClass = status === 'active' ? 'engine-active' : status === 'error' ? 'engine-error' : 'engine-ready';
            const displayName = name.replace(/_/g, ' ').replace(/engine$/i, '').trim();
            return `<div class="engine-badge ${statusClass}" title="${escapeHtml(name)}: ${invocations} invocations">
                <span class="engine-badge-name">${escapeHtml(capitalize(displayName))}</span>
                <span class="engine-badge-count">${invocations}</span>
            </div>`;
        }).join('');
    } else if (gridEl && engineCount > 0) {
        gridEl.innerHTML = `<div class="muted-text">${engineCount} engines registered (details loading...)</div>`;
    }
}
// Wire subsystem polling into system page visibility
const _origSwitchPage = switchPage;
// Override switchPage to trigger subsystem fetch when System page is shown
// and abilities fetch when Abilities page is shown
(function () {
    const original = switchPage;
    switchPage = function (pageId) {
        original(pageId);
        if (pageId === 'system' && !subsystemsLoaded) {
            fetchSubsystems();
        }
        if (pageId === 'abilities') {
            fetchAbilities();
        }
        if (pageId === 'settings') {
            loadSettingsPage();
        }
    };
})();
// Also start subsystem polling alongside main polling
(function () {
    // Delay subsystem poll start to avoid overloading on page load
    setTimeout(startSubsystemPolling, 4000);
})();
// ══════════════════════════════════════════════
// SETTINGS PAGE
// ══════════════════════════════════════════════
async function loadSettingsPage() {
    try {
        const res = await fetch('/api/user/profile', { headers: getAuthHeaders() });
        if (!res.ok) return;
        const data = await res.json();
        const p = data.profile || {};
        // Profile card
        setText('settings-display-name', p.display_name || p.username || 'User');
        setText('settings-username', '@' + (p.username || 'user'));
        if (p.created_at) {
            setText('settings-member-since', 'Member since ' + new Date(p.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }));
        }
        // Avatar
        const avatarEl = document.getElementById('settings-avatar');
        if (avatarEl) {
            if (p.profile_picture) {
                avatarEl.innerHTML = `<img src="${p.profile_picture}" alt="Avatar">`;
            } else {
                avatarEl.innerHTML = '<i class="fas fa-user"></i>';
            }
        }
        // Edit form
        const nameInput = document.getElementById('settings-edit-displayname');
        if (nameInput) nameInput.value = p.display_name || '';
        const bioInput = document.getElementById('settings-edit-bio');
        if (bioInput) bioInput.value = p.bio || '';
        // Account info
        setText('settings-acct-username', p.username || '—');
        setText('settings-acct-display', p.display_name || '—');
        setText('settings-acct-created', p.created_at ? new Date(p.created_at).toLocaleDateString() : '—');
        setText('settings-acct-login', p.last_login ? new Date(p.last_login).toLocaleString() : '—');
    } catch (e) {
        console.warn('Failed to load settings:', e);
    }
}
async function saveProfile() {
    const displayName = document.getElementById('settings-edit-displayname')?.value?.trim();
    const bio = document.getElementById('settings-edit-bio')?.value?.trim() || '';
    const msgEl = document.getElementById('profile-save-msg');
    if (!displayName) {
        showSettingsMsg(msgEl, 'Display name is required', 'error');
        return;
    }
    try {
        const res = await fetch('/api/user/profile', {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify({ display_name: displayName, bio })
        });
        const data = await res.json();
        if (res.ok) {
            showSettingsMsg(msgEl, 'Profile saved successfully!', 'success');
            // Update header/sidebar
            currentUser = { ...currentUser, display_name: displayName };
            setText('header-username', displayName);
            setText('sidebar-username', displayName);
            setText('settings-display-name', displayName);
            setText('settings-acct-display', displayName);
        } else {
            showSettingsMsg(msgEl, data.error || 'Failed to save', 'error');
        }
    } catch (e) {
        showSettingsMsg(msgEl, 'Connection error', 'error');
    }
}
async function changePassword() {
    const currentPw = document.getElementById('settings-current-pw')?.value || '';
    const newPw = document.getElementById('settings-new-pw')?.value || '';
    const confirmPw = document.getElementById('settings-confirm-pw')?.value || '';
    const msgEl = document.getElementById('password-save-msg');
    if (!currentPw || !newPw) {
        showSettingsMsg(msgEl, 'Please fill in all password fields', 'error');
        return;
    }
    if (newPw !== confirmPw) {
        showSettingsMsg(msgEl, 'New passwords do not match', 'error');
        return;
    }
    if (newPw.length < 4) {
        showSettingsMsg(msgEl, 'Password must be at least 4 characters', 'error');
        return;
    }
    try {
        const res = await fetch('/api/user/password', {
            method: 'PUT',
            headers: getAuthHeaders(),
            body: JSON.stringify({ current_password: currentPw, new_password: newPw })
        });
        const data = await res.json();
        if (res.ok) {
            showSettingsMsg(msgEl, 'Password changed successfully!', 'success');
            // Clear fields
            document.getElementById('settings-current-pw').value = '';
            document.getElementById('settings-new-pw').value = '';
            document.getElementById('settings-confirm-pw').value = '';
        } else {
            showSettingsMsg(msgEl, data.error || 'Failed to change password', 'error');
        }
    } catch (e) {
        showSettingsMsg(msgEl, 'Connection error', 'error');
    }
}
async function uploadAvatar(event) {
    const file = event?.target?.files?.[0];
    if (!file) return;
    // Validate file type and size
    if (!file.type.startsWith('image/')) {
        alert('Please select an image file');
        return;
    }
    if (file.size > 2 * 1024 * 1024) {
        alert('Image must be under 2MB');
        return;
    }
    const reader = new FileReader();
    reader.onload = async function (e) {
        const base64 = e.target.result; // data:image/...;base64,...
        // Show preview immediately
        const avatarEl = document.getElementById('settings-avatar');
        if (avatarEl) avatarEl.innerHTML = `<img src="${base64}" alt="Avatar">`;
        try {
            const res = await fetch('/api/user/avatar', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ avatar: base64 })
            });
            const data = await res.json();
            if (!res.ok) {
                alert(data.error || 'Failed to upload avatar');
            }
        } catch (err) {
            alert('Connection error while uploading avatar');
        }
    };
    reader.readAsDataURL(file);
}
function showSettingsMsg(el, text, type) {
    if (!el) return;
    el.textContent = text;
    el.className = 'settings-msg ' + (type === 'success' ? 'msg-success' : 'msg-error');
    setTimeout(() => {
        el.textContent = '';
        el.className = 'settings-msg';
    }, 4000);
}
// ══════════════════════════════════════════════
// INTERNET AGENT PANEL
// ══════════════════════════════════════════════
function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}
async function updateInternetAgent() {
    try {
        const res = await fetch('/api/internet', { headers: getAuthHeaders() });
        if (!res.ok) {
            // Agent not available — set badge to offline
            const badge = document.getElementById('inet-status-badge');
            if (badge) badge.textContent = '⚪ Offline';
            return;
        }
        const data = await res.json();
        // Status badge
        const badge = document.getElementById('inet-status-badge');
        if (badge) {
            if (data.running && data.connected) {
                badge.textContent = '🟢 Active & Connected';
                badge.style.color = '#00ff88';
            } else if (data.running) {
                badge.textContent = '🟡 Running (No Internet)';
                badge.style.color = '#fbbf24';
            } else {
                badge.textContent = '🔴 Stopped';
                badge.style.color = '#ef4444';
            }
        }
        // Stat cards
        const stats = data.stats || {};
        setText('inet-total-actions', stats.total_actions || 0);
        setText('inet-success-count', stats.successful_actions || 0);
        setText('inet-queue-size', data.queue_size || 0);
        setText('inet-bytes-dl', formatBytes(stats.total_bytes_downloaded || 0));
        // KV rows
        setText('inet-running', data.running ? '🟢 Running' : '🔴 Stopped');
        setText('inet-connected', data.connected ? '✅ Yes' : '❌ No');
        const avgResp = stats.avg_response_time;
        setText('inet-avg-response', typeof avgResp === 'number' ? avgResp.toFixed(2) + 's' : '--');
        setText('inet-domains', stats.domains_visited_count || 0);
        setText('inet-groq-notified', data.running ? '✅ Yes' : '—');
        // Recent actions feed
        const actions = data.recent_actions || [];
        const feedList = document.getElementById('inet-feed-list');
        if (feedList) {
            if (actions.length > 0) {
                feedList.innerHTML = actions.slice(0, 10).map(a => {
                    const icon = {
                        browse: '🌐', search: '🔍', scrape: '📋',
                        api_call: '⚡', download: '📥', check_status: '📡'
                    }[a.action_type] || '🌐';
                    const status = a.success ? '✅' : '❌';
                    const desc = (a.description || a.url || a.action_type || 'Action').substring(0, 60);
                    const time = a.timestamp ? new Date(a.timestamp).toLocaleTimeString() : '';
                    return `<div class="auto-feed-item">
                        <span>${icon} ${status}</span>
                        <span style="flex:1;margin-left:8px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(desc)}</span>
                        <span style="opacity:.5;font-size:.7rem;margin-left:auto;padding-left:8px">${time}</span>
                    </div>`;
                }).join('');
            } else {
                feedList.innerHTML = '<div class="auto-feed-item muted"><i>Waiting for internet agent...</i></div>';
            }
        }
    } catch (e) {
        // Silently fail if endpoint not available
    }
}
async function startInternetAgent() {
    try {
        const res = await fetch('/api/internet/start', {
            method: 'POST',
            headers: getAuthHeaders()
        });
        if (res.ok) {
            showToast('🌐 Internet Agent started', 'success');
        } else {
            showToast('Failed to start Internet Agent', 'error');
        }
    } catch (e) {
        showToast('Connection error', 'error');
    }
}
async function stopInternetAgent() {
    try {
        const res = await fetch('/api/internet/stop', {
            method: 'POST',
            headers: getAuthHeaders()
        });
        if (res.ok) {
            showToast('🌐 Internet Agent stopped', 'info');
        } else {
            showToast('Failed to stop Internet Agent', 'error');
        }
    } catch (e) {
        showToast('Connection error', 'error');
    }
}
// ═══════════════════════════════════════════════════════════════════
// ETHICAL HACKING PANEL — Port Scanner, Network Recon, Vuln Alerts
// ═══════════════════════════════════════════════════════════════════
function updateHackingPanel(data) {
    if (!data) return;
    try {
        // Status badge
        const badge = document.getElementById('hack-status-badge');
        if (badge) {
            if (data.is_scanning) {
                badge.textContent = '⚡ SCANNING';
                badge.style.background = 'rgba(239,68,68,0.15)';
                badge.style.color = '#ef4444';
                badge.style.borderColor = 'rgba(239,68,68,0.3)';
            } else {
                badge.textContent = '☠️ RECON MODE';
                badge.style.background = 'rgba(34,211,238,0.15)';
                badge.style.color = '#22d3ee';
                badge.style.borderColor = 'rgba(34,211,238,0.3)';
            }
        }
        // Stat cards
        const el = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
        el('hack-total-scans', data.total_scans || 0);
        el('hack-open-ports', data.total_open_ports_found || 0);
        el('hack-vulns-found', data.total_vulns_found || 0);
        el('hack-targets-scanned', data.unique_targets_scanned || 0);
        el('hack-engine-status', (data.engine_status || 'idle').toUpperCase());
        // Network info
        const net = data.network_info || {};
        el('hack-local-ip', net.local_ip || '--');
        el('hack-public-ip', net.public_ip || '--');
        el('hack-hostname', net.hostname || '--');
        el('hack-gateway', net.gateway || '--');
        el('hack-subnet', net.subnet || '--');
        // Latest scan result
        const latest = data.latest_scan;
        if (latest) {
            displayScanResult(latest);
        }
        // Scan history
        const histList = document.getElementById('hack-history-list');
        if (histList && data.recent_scans && data.recent_scans.length > 0) {
            histList.innerHTML = '';
            data.recent_scans.forEach(scan => {
                const alive = scan.host_alive ? '✅' : '❌';
                const vulnBadge = scan.vulns > 0
                    ? `<span style="color:#f97316;font-weight:600">⚠️ ${scan.vulns} vuln${scan.vulns > 1 ? 's' : ''}</span>`
                    : '<span style="color:#22c55e">✅ Clean</span>';
                const item = document.createElement('div');
                item.className = 'auto-feed-item';
                item.innerHTML = `
                    <div style="display:flex;justify-content:space-between;align-items:center">
                        <div>
                            <span style="color:#22d3ee;font-weight:600">${scan.target}</span>
                            <span style="color:rgba(255,255,255,0.4);font-size:.75rem;margin-left:8px">${alive} alive</span>
                        </div>
                        <div style="display:flex;gap:12px;align-items:center">
                            <span style="color:#ef4444;font-size:.82rem">🔓 ${scan.open_ports} open</span>
                            ${vulnBadge}
                            <span style="color:rgba(255,255,255,0.4);font-size:.72rem">${scan.duration}s</span>
                        </div>
                    </div>`;
                histList.appendChild(item);
            });
        }
    } catch (e) {
        console.error('updateHackingPanel error:', e);
    }
}
function displayScanResult(result) {
    if (!result) return;
    // Show results header
    const header = document.getElementById('hack-results-header');
    if (header) header.style.display = 'block';
    const el = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
    el('hack-result-target', result.target || '--');
    el('hack-result-alive', result.host_alive ? '✅ Yes' : '❌ No');
    el('hack-result-os', result.os_hint || 'Unknown');
    el('hack-result-scanned', result.ports_scanned || '--');
    el('hack-result-duration', (result.duration_seconds || 0).toFixed(2) + 's');
    // Open ports table
    const portsDiv = document.getElementById('hack-ports-table');
    if (portsDiv) {
        const openPorts = result.open_ports || [];
        if (openPorts.length === 0) {
            portsDiv.innerHTML = '<div class="auto-feed-item" style="color:#22c55e"><i class="fas fa-check-circle"></i> No open ports found — target appears secure.</div>';
        } else {
            let html = '<table class="hack-port-table"><thead><tr><th>Port</th><th>Service</th><th>Risk</th><th>Banner</th><th>Description</th></tr></thead><tbody>';
            openPorts.forEach(p => {
                const riskColor = { critical: '#ef4444', high: '#f97316', medium: '#eab308', low: '#22c55e', info: '#94a3b8' }[p.risk] || '#94a3b8';
                const riskBadge = `<span class="hack-risk-badge" style="background:${riskColor}20;color:${riskColor};border:1px solid ${riskColor}40">${(p.risk || 'info').toUpperCase()}</span>`;
                html += `<tr>
                    <td style="color:#22d3ee;font-weight:700;font-family:monospace">${p.port}</td>
                    <td style="color:#e2e8f0">${p.service}</td>
                    <td>${riskBadge}</td>
                    <td style="color:rgba(255,255,255,0.5);font-size:.75rem;font-family:monospace;max-width:150px;overflow:hidden;text-overflow:ellipsis">${p.banner || '-'}</td>
                    <td style="color:rgba(255,255,255,0.6);font-size:.78rem">${p.description || ''}</td>
                </tr>`;
            });
            html += '</tbody></table>';
            portsDiv.innerHTML = html;
        }
    }
    // Vulnerabilities
    const vulnsList = document.getElementById('hack-vulns-list');
    if (vulnsList) {
        const vulns = result.vulnerabilities || [];
        if (vulns.length === 0) {
            vulnsList.innerHTML = '<div class="auto-feed-item" style="color:#22c55e"><i class="fas fa-shield-alt"></i> No vulnerabilities detected.</div>';
        } else {
            vulnsList.innerHTML = '';
            vulns.forEach(v => {
                const sevColor = v.severity === 'critical' ? '#ef4444' : '#f97316';
                const item = document.createElement('div');
                item.className = 'hack-vuln-item';
                item.innerHTML = `
                    <div class="hack-vuln-header">
                        <span class="hack-risk-badge" style="background:${sevColor}20;color:${sevColor};border:1px solid ${sevColor}40">${(v.severity || 'high').toUpperCase()}</span>
                        <span style="color:#e2e8f0;font-weight:600">${v.title}</span>
                    </div>
                    <div style="color:rgba(255,255,255,0.6);font-size:.78rem;margin:4px 0 4px 0">${v.description}</div>
                    <div style="color:#22d3ee;font-size:.78rem"><i class="fas fa-wrench"></i> ${v.recommendation}</div>
                `;
                vulnsList.appendChild(item);
            });
        }
    }
}
async function startHackingScan() {
    const input = document.getElementById('hack-target-input');
    const target = (input ? input.value : '').trim();
    if (!target) {
        alert('Please enter a target IP or hostname');
        return;
    }
    const extended = document.getElementById('hack-extended-scan');
    const isExtended = extended ? extended.checked : false;
    // Show progress
    const progress = document.getElementById('hack-scan-progress');
    const progressText = document.getElementById('hack-scan-progress-text');
    const scanBtn = document.getElementById('hack-scan-btn');
    if (progress) progress.style.display = 'block';
    if (progressText) progressText.textContent = `Scanning ${target}...`;
    if (scanBtn) { scanBtn.disabled = true; scanBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Scanning...'; }
    try {
        const res = await fetchWithAuth('/api/hacking/scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ target: target, extended: isExtended })
        });
        const data = await res.json();
        if (data.error) {
            if (progressText) progressText.textContent = `Error: ${data.error}`;
            return;
        }
        // Poll for result
        const taskId = data.task_id;
        if (progressText) progressText.textContent = `Scan in progress on ${target}...`;
        const pollInterval = setInterval(async () => {
            try {
                const statusRes = await fetchWithAuth(`/api/hacking/scan/status/${taskId}`);
                const statusData = await statusRes.json();
                if (statusData.status === 'complete') {
                    clearInterval(pollInterval);
                    if (progress) progress.style.display = 'none';
                    if (scanBtn) { scanBtn.disabled = false; scanBtn.innerHTML = '<i class="fas fa-play"></i> Start Scan'; }
                    displayScanResult(statusData.result);
                    fetchStats(); // Refresh stats
                } else if (statusData.status === 'error') {
                    clearInterval(pollInterval);
                    if (progressText) progressText.textContent = `Error: ${statusData.error}`;
                    if (scanBtn) { scanBtn.disabled = false; scanBtn.innerHTML = '<i class="fas fa-play"></i> Start Scan'; }
                }
            } catch (e) {
                clearInterval(pollInterval);
                if (progressText) progressText.textContent = `Poll error: ${e.message}`;
                if (scanBtn) { scanBtn.disabled = false; scanBtn.innerHTML = '<i class="fas fa-play"></i> Start Scan'; }
            }
        }, 1500);
    } catch (e) {
        if (progressText) progressText.textContent = `Error: ${e.message}`;
        if (scanBtn) { scanBtn.disabled = false; scanBtn.innerHTML = '<i class="fas fa-play"></i> Start Scan'; }
    }
}
async function startDNSLookup() {
    const input = document.getElementById('hack-target-input');
    const hostname = (input ? input.value : '').trim();
    if (!hostname) {
        alert('Please enter a hostname for DNS lookup');
        return;
    }
    try {
        const res = await fetchWithAuth('/api/hacking/dns', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ hostname: hostname })
        });
        const data = await res.json();
        const card = document.getElementById('hack-dns-card');
        const resultsDiv = document.getElementById('hack-dns-results');
        if (!card || !resultsDiv) return;
        card.style.display = 'block';
        if (data.error || (data.dns && data.dns.error)) {
            resultsDiv.innerHTML = `<div class="auto-feed-item" style="color:#ef4444"><i class="fas fa-times-circle"></i> ${data.error || data.dns.error}</div>`;
            return;
        }
        const dns = data.dns || {};
        let html = `<div style="color:#a855f7;font-weight:600;margin-bottom:8px">DNS records for: ${dns.hostname || hostname}</div>`;
        const records = dns.records || [];
        if (records.length === 0) {
            html += '<div class="auto-feed-item muted">No DNS records found.</div>';
        } else {
            html += '<table class="hack-port-table"><thead><tr><th>Type</th><th>Value</th></tr></thead><tbody>';
            records.forEach(rec => {
                html += `<tr><td style="color:#a855f7;font-weight:600">${rec.type}</td><td style="color:#e2e8f0;font-family:monospace">${rec.value}${rec.for ? ` (for ${rec.for})` : ''}</td></tr>`;
            });
            html += '</tbody></table>';
        }
        resultsDiv.innerHTML = html;
    } catch (e) {
        console.error('DNS lookup error:', e);
    }
}
async function refreshNetworkInfo() {
    try {
        const res = await fetchWithAuth('/api/hacking/network');
        const data = await res.json();
        if (data.network) {
            const net = data.network;
            const el = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
            el('hack-local-ip', net.local_ip || '--');
            el('hack-public-ip', net.public_ip || '--');
            el('hack-hostname', net.hostname || '--');
            el('hack-gateway', net.gateway || '--');
            el('hack-subnet', net.subnet || '--');
        }
    } catch (e) {
        console.error('Network refresh error:', e);
    }
}
// ═══════════════════════════════════════════════════════════════════
// ETHICAL HACKING v2.0 — Expanded Panel Functions
// ═══════════════════════════════════════════════════════════════════
function pollHackingScan(taskId, scanType = 'scan') {
    const label = String(scanType).replace(/_/g, ' ').toUpperCase();
    let attempts = 0;
    const maxAttempts = 120; // ~3 minutes at 1.5s intervals
    const poll = setInterval(async () => {
        attempts++;
        try {
            const res = await fetchWithAuth(`/api/hacking/scan/status/${taskId}`);
            const data = await res.json();
            if (data.status === 'complete') {
                clearInterval(poll);
                showNotification(`${label} scan completed!`, 'success');
                fetchStats(); // Refresh stats
            } else if (data.status === 'error') {
                clearInterval(poll);
                showNotification(`${label} scan failed: ${data.error || 'Unknown error'}`, 'error');
            }
        } catch (e) {
            if (attempts >= maxAttempts) {
                clearInterval(poll);
                showNotification(`Poll error: ${e.message}`, 'error');
            }
        }
    }, 1500);
}
function startFullRecon() {
    const target = document.getElementById('hackFullReconTarget');
    if (!target || !target.value.trim()) { showNotification('Enter a target', 'warning'); return; }
    const t = target.value.trim();
    showNotification('Full recon started on ' + t + '...', 'info');
    const btn = document.querySelector('.hack-full-recon-btn');
    if (btn) { btn.disabled = true; btn.textContent = '⏳ Scanning...'; }
    fetch('/api/hacking/full_recon', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() },
        body: JSON.stringify({ target: t })
    })
        .then(r => r.json())
        .then(data => {
            if (data.task_id) { pollHackingScan(data.task_id, 'full_recon'); }
            else { showNotification(data.error || 'Scan failed', 'error'); }
        })
        .catch(e => showNotification('Error: ' + e.message, 'error'))
        .finally(() => { if (btn) { btn.disabled = false; btn.textContent = '🔍 Full Recon'; } });
}
function startHTTPAudit() {
    const target = document.getElementById('hackHTTPTarget');
    if (!target || !target.value.trim()) { showNotification('Enter a target', 'warning'); return; }
    const t = target.value.trim();
    showNotification('HTTP audit on ' + t + '...', 'info');
    fetch('/api/hacking/http_audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() },
        body: JSON.stringify({ target: t, https: document.getElementById('hackHTTPSToggle')?.checked || false })
    })
        .then(r => r.json())
        .then(data => {
            if (data.result) { displayHTTPAudit(data.result); }
            else { showNotification(data.error || 'Audit failed', 'error'); }
        })
        .catch(e => showNotification('Error: ' + e.message, 'error'));
}
function displayHTTPAudit(result) {
    const el = document.getElementById('hackHTTPResult');
    if (!el) return;
    let html = '<div class="hack-audit-result">';
    html += '<div class="hack-score-badge ' + (result.score >= 70 ? 'good' : result.score >= 40 ? 'warning' : 'critical') + '">';
    html += 'Score: ' + result.score + '/100</div>';
    html += '<p>Server: ' + (result.server || 'unknown') + '</p>';
    if (result.missing_security_headers && result.missing_security_headers.length > 0) {
        html += '<h4>⚠️ Missing Security Headers</h4><ul>';
        result.missing_security_headers.forEach(h => {
            html += '<li><span class="hack-badge ' + h.severity + '">' + h.severity.toUpperCase() + '</span> ' + h.header + ' — ' + h.description + '</li>';
        });
        html += '</ul>';
    }
    if (result.present_security_headers && result.present_security_headers.length > 0) {
        html += '<h4>✅ Present Headers</h4><ul>';
        result.present_security_headers.forEach(h => { html += '<li>✓ ' + h.header + '</li>'; });
        html += '</ul>';
    }
    if (result.info_disclosure && result.info_disclosure.length > 0) {
        html += '<h4>🔓 Info Disclosure</h4><ul>';
        result.info_disclosure.forEach(i => { html += '<li>⚠ ' + i + '</li>'; });
        html += '</ul>';
    }
    html += '</div>';
    el.innerHTML = html;
}
function startSSLCheck() {
    const target = document.getElementById('hackSSLTarget');
    if (!target || !target.value.trim()) { showNotification('Enter a target', 'warning'); return; }
    const t = target.value.trim();
    showNotification('SSL check on ' + t + '...', 'info');
    fetch('/api/hacking/ssl_check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() },
        body: JSON.stringify({ target: t })
    })
        .then(r => r.json())
        .then(data => {
            if (data.result) { displaySSLResult(data.result); }
            else { showNotification(data.error || 'SSL check failed', 'error'); }
        })
        .catch(e => showNotification('Error: ' + e.message, 'error'));
}
function displaySSLResult(result) {
    const el = document.getElementById('hackSSLResult');
    if (!el) return;
    let html = '<div class="hack-ssl-result">';
    html += '<div class="hack-score-badge ' + (result.score >= 70 ? 'good' : result.score >= 40 ? 'warning' : 'critical') + '">';
    html += 'SSL Score: ' + result.score + '/100</div>';
    html += '<p>SSL Enabled: ' + (result.ssl_enabled ? '✅ Yes' : '❌ No') + '</p>';
    if (result.protocol) html += '<p>Protocol: ' + result.protocol + '</p>';
    if (result.cipher) html += '<p>Cipher: ' + result.cipher.name + ' (' + result.cipher.bits + ' bits)</p>';
    if (result.cert_info && result.cert_info.days_until_expiry !== undefined) {
        const d = result.cert_info.days_until_expiry;
        html += '<p>Certificate: expires in ' + d + ' days ' + (d < 30 ? '⚠️' : '✅') + '</p>';
    }
    if (result.issues && result.issues.length > 0) {
        html += '<h4>⚠️ Issues</h4><ul>';
        result.issues.forEach(i => { html += '<li class="hack-vuln-item">🔴 ' + i + '</li>'; });
        html += '</ul>';
    }
    html += '</div>';
    el.innerHTML = html;
}
function startSubdomainEnum() {
    const target = document.getElementById('hackSubdomainTarget');
    if (!target || !target.value.trim()) { showNotification('Enter a domain', 'warning'); return; }
    const t = target.value.trim();
    showNotification('Enumerating subdomains for ' + t + '...', 'info');
    fetch('/api/hacking/subdomains', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() },
        body: JSON.stringify({ domain: t })
    })
        .then(r => r.json())
        .then(data => {
            if (data.result) { displaySubdomains(data.result); }
            else { showNotification(data.error || 'Enum failed', 'error'); }
        })
        .catch(e => showNotification('Error: ' + e.message, 'error'));
}
function displaySubdomains(result) {
    const el = document.getElementById('hackSubdomainResult');
    if (!el) return;
    let html = '<div class="hack-subdomain-result">';
    html += '<p>Checked: ' + result.total_checked + ' subdomains | Found: ' + (result.found || []).length + '</p>';
    if (result.found && result.found.length > 0) {
        html += '<table class="hack-port-table"><thead><tr><th>Subdomain</th><th>IP</th></tr></thead><tbody>';
        result.found.forEach(s => {
            html += '<tr><td>' + s.subdomain + '</td><td>' + s.ip + '</td></tr>';
        });
        html += '</tbody></table>';
    } else {
        html += '<p class="hack-no-data">No subdomains found</p>';
    }
    html += '</div>';
    el.innerHTML = html;
}
function startSubnetSweep() {
    showNotification('Subnet sweep started...', 'info');
    fetch('/api/hacking/sweep', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() },
        body: JSON.stringify({})
    })
        .then(r => r.json())
        .then(data => {
            if (data.result) { displaySweepResult(data.result); }
            else { showNotification(data.error || 'Sweep failed', 'error'); }
        })
        .catch(e => showNotification('Error: ' + e.message, 'error'));
}
function displaySweepResult(result) {
    const el = document.getElementById('hackSweepResult');
    if (!el) return;
    let html = '<div class="hack-sweep-result">';
    html += '<p>Subnet: ' + (result.subnet || '?') + ' | Checked: ' + (result.total_checked || 0) + '</p>';
    const alive = result.alive_hosts || [];
    html += '<p class="hack-alive-count">🟢 Alive Hosts: ' + alive.length + '</p>';
    if (alive.length > 0) {
        html += '<div class="hack-host-grid">';
        alive.forEach(h => { html += '<span class="hack-host-chip">' + h + '</span>'; });
        html += '</div>';
    }
    html += '</div>';
    el.innerHTML = html;
}
function updateHackingPanelV2(stats) {
    if (!stats) return;
    const setVal = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
    // ── Update v2 stat cards ──
    setVal('hackTotalScans', stats.total_scans || 0);
    setVal('hackOpenPorts', stats.total_open_ports_found || 0);
    setVal('hackVulns', stats.total_vulns_found || 0);
    setVal('hackTargets', stats.unique_targets_scanned || 0);
    setVal('hackHTTPAudits', stats.total_http_audits || 0);
    setVal('hackSSLChecks', stats.total_ssl_checks || 0);
    setVal('hackSubEnums', stats.total_subdomain_enums || 0);
    setVal('hackSweeps', stats.total_subnet_sweeps || 0);
    setVal('hackFullRecons', stats.total_full_recons || 0);
    setVal('hackAliveHosts', stats.alive_hosts_count || 0);
    setVal('hackWAFDetections', stats.total_waf_detections || 0);
    setVal('hackPathDisc', stats.total_path_discoveries || 0);
    setVal('hackEngineStatus', stats.engine_status || 'offline');
    setVal('hackVersion', stats.engine_version || '?');
    // ── Update v1 status banner (original HTML IDs) ──
    setVal('hack-total-scans', stats.total_scans || 0);
    setVal('hack-open-ports', stats.total_open_ports_found || 0);
    setVal('hack-vulns-found', stats.total_vulns_found || 0);
    setVal('hack-targets-scanned', stats.unique_targets_scanned || 0);
    setVal('hack-engine-status', (stats.engine_status || 'IDLE').toUpperCase());
    // ── Update network info ──
    const net = stats.network_info || {};
    setVal('hack-local-ip', net.local_ip || '--');
    setVal('hack-public-ip', net.public_ip || '--');
    setVal('hack-hostname', net.hostname || '--');
    setVal('hack-gateway', net.gateway || '--');
    setVal('hack-subnet', net.subnet || '--');
    // ── Update capabilities list ──
    const capEl = document.getElementById('hackCapabilities');
    if (capEl && stats.capabilities) {
        capEl.innerHTML = stats.capabilities.map(c =>
            '<span class="hack-cap-chip">' + c + '</span>'
        ).join('');
    }
    // ── Update alive hosts ──
    const aliveEl = document.getElementById('hackAliveHostsList');
    if (aliveEl && stats.alive_hosts) {
        aliveEl.innerHTML = stats.alive_hosts.map(h =>
            '<span class="hack-host-chip">' + h + '</span>'
        ).join('') || '<span class="hack-no-data">None yet</span>';
    }
    // ── Update scan history ──
    const histEl = document.getElementById('hack-history-list');
    if (histEl && stats.recent_scans && stats.recent_scans.length > 0) {
        histEl.innerHTML = stats.recent_scans.map(s => {
            const risk = (s.vulns || 0) > 0 ? 'style="color:#ef4444"' : 'style="color:#22c55e"';
            return '<div class="auto-feed-item">' +
                '<span style="color:#22d3ee;font-weight:600">' + (s.target || '?') + '</span> ' +
                '<span style="color:#888;font-size:.8em">[' + (s.scan_type || 'scan') + ']</span> — ' +
                '<span ' + risk + '>' + (s.open_ports || 0) + ' ports, ' + (s.vulns || 0) + ' vulns</span>' +
                '</div>';
        }).join('');
    }
}
// ═══════════════════════════════════════════════════════════════════════════════
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
    _asi('dash-asi-iq-detail', s.composite_iq ? s.composite_iq.toFixed(1) : '50.0');
    _asi('dash-asi-growth', ((s.improvement_velocity || 0) * 100).toFixed(2) + '%');
    // Creator
    var c = asiData.creator || {};
    _asi('dash-asi-creations', c.total_creations || c.works_created || 0);
    _asi('dash-asi-creations-detail', c.total_creations || c.works_created || 0);
    _asi('dash-asi-genres', c.genres_invented || 0);
    _asi('dash-asi-fusions', c.cross_domain_fusions || 0);
    _asi('dash-asi-symphonies', c.symphonies_composed || 0);
    // Genesis
    var g = asiData.genesis || {};
    _asi('dash-asi-problems', g.total_problems || 0);
    _asi('dash-asi-solutions', g.total_solutions || 0);
    _asi('dash-asi-goals', g.total_goals || 0);
    _asi('dash-asi-problems-detail', g.total_problems || 0);
    _asi('dash-asi-genesis-cycles', g.genesis_cycles || g.total_cycles || 0);
    // Empathy
    var em = asiData.empathy || {};
    _asi('dash-asi-empathy-pred', em.predictions_made || 0);
    _asi('dash-asi-profiles', em.profiles_built || em.profiles_count || 0);
    _asi('dash-asi-negotiations', em.negotiations || 0);
    _asi('dash-asi-empathy-detail', em.predictions_made || 0);
    // Orchestrator
    var o = asiData.orchestrator || {};
    var health = o.overall_health || 0;
    _asi('dash-asi-health', Math.round(health * 100) + '%');
    var hBar = document.getElementById('dash-asi-health-bar');
    if (hBar) hBar.style.width = (health * 100) + '%';
    _asi('dash-asi-anomalies', o.active_anomalies || 0);
    _asi('dash-asi-synth-cycles', o.synthesis_cycles || 0);
    _asi('dash-asi-global-health', Math.round((o.overall_health || 1.0) * 100) + '%');
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

// ══════════════════════════════════════════════
// P2P SWARM & CONSENSUS UI LOGIC
// ══════════════════════════════════════════════
function updateSwarmPanel(swarmData) {
    if (!swarmData) return;

    // Counts
    const totalPeers = swarmData.total_peers || 0;
    const onlinePeers = swarmData.online_peers || 0;
    setText('swarm-peers-count', onlinePeers + 1); // Local + online
    setText('swarm-peers-sub', `${totalPeers} external connected`);
    setText('swarm-msgs-count', (swarmData.messages_sent || 0) + (swarmData.messages_received || 0));
    setText('swarm-bft-count', swarmData.bft_rounds || 0);
    setText('swarm-tasks-count', swarmData.tasks_offloaded || 0);

    const localPeer = swarmData.local_peer || {};
    if (localPeer.peer_id) {
        setText('swarm-local-id', `Local Node: ${localPeer.peer_id} (${localPeer.ip_address || '127.0.0.1'})`);
    }

    // Topology Visualization
    const topoContainer = document.getElementById('swarm-topology-container');
    if (topoContainer) {
        const topoNodes = swarmData.network_topology || [];
        if (topoNodes.length === 0) {
            topoContainer.innerHTML = `<div style="text-align:center;padding:20px;opacity:.5">Standalone node (listening for UDP beacons on port 9877)</div>`;
        } else {
            let html = '';
            topoNodes.forEach(node => {
                const isLocal = node.group === 'local';
                const bg = isLocal ? 'rgba(16,185,129,0.2)' : 'rgba(56,189,248,0.2)';
                const border = isLocal ? '#10b981' : '#38bdf8';
                const icon = isLocal ? 'fa-home' : 'fa-laptop';
                html += `
                    <div style="padding:10px 14px;border-radius:10px;background:${bg};border:1px solid ${border};display:flex;align-items:center;gap:8px;font-size:.78rem">
                        <i class="fas ${icon}" style="color:${border}"></i>
                        <div>
                            <div style="font-weight:600;color:#f8fafc">${node.label}</div>
                            <div style="font-size:.65rem;opacity:.6">${node.id}</div>
                        </div>
                    </div>
                `;
            });
            topoContainer.innerHTML = html;
        }
    }

    // BFT Proposals List
    const bftContainer = document.getElementById('swarm-bft-container');
    if (bftContainer) {
        const proposals = swarmData.bft_proposals || [];
        if (proposals.length === 0) {
            bftContainer.innerHTML = `
                <div style="text-align:center;padding:40px 20px;opacity:.4">
                    <i class="fas fa-check-double" style="font-size:1.5rem;margin-bottom:6px;color:#c084fc"></i>
                    <div style="font-size:.8rem">No active BFT proposals</div>
                    <div style="font-size:.7rem;margin-top:2px">Initiate a proposal to trigger 3-phase BFT consensus</div>
                </div>
            `;
        } else {
            let html = '';
            proposals.forEach(p => {
                const pct = Math.min(100, Math.round((p.commits_count / Math.max(1, p.quorum_needed)) * 100));
                html += `
                    <div style="padding:10px 12px;border-radius:8px;background:rgba(192,132,252,0.08);border:1px solid rgba(192,132,252,0.2)">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
                            <span style="font-weight:600;font-size:.8rem;color:#f8fafc">${p.topic}</span>
                            <span class="badge" style="background:rgba(192,132,252,0.2);color:#c084fc;font-size:.65rem;padding:2px 6px">${p.status.toUpperCase()}</span>
                        </div>
                        <div style="font-size:.7rem;opacity:.6;margin-bottom:6px">Phase: ${p.phase} | Commits: ${p.commits_count}/${p.quorum_needed} needed</div>
                        <div style="width:100%;height:4px;background:rgba(255,255,255,0.1);border-radius:2px;overflow:hidden">
                            <div style="width:${pct}%;height:100%;background:#c084fc;transition:width 0.3s"></div>
                        </div>
                    </div>
                `;
            });
            bftContainer.innerHTML = html;
        }
    }

    // Peer Table
    const tbody = document.getElementById('swarm-peers-tbody');
    if (tbody) {
        const peers = swarmData.peers || [];
        if (peers.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td style="padding:8px;font-weight:600;color:#10b981">${localPeer.peer_id || 'local'} (Self)</td>
                    <td style="padding:8px">${localPeer.hostname || 'localhost'} (${localPeer.ip_address || '127.0.0.1'})</td>
                    <td style="padding:8px"><span style="background:rgba(16,185,129,0.15);color:#10b981;padding:2px 8px;border-radius:8px;font-size:.68rem">PRIMARY</span></td>
                    <td style="padding:8px">${Math.round((localPeer.cpu_load || 0) * 100)}%</td>
                    <td style="padding:8px">${Math.round((localPeer.memory_usage_pct || 0) * 100)}%</td>
                    <td style="padding:8px"><span style="color:#10b981">● ONLINE</span></td>
                </tr>
                <tr><td colspan="6" style="text-align:center;padding:12px;opacity:.4;font-size:.72rem">No external peers currently connected. Broadcasting UDP beacons on port 9877...</td></tr>
            `;
        } else {
            let html = `
                <tr>
                    <td style="padding:8px;font-weight:600;color:#10b981">${localPeer.peer_id || 'local'} (Self)</td>
                    <td style="padding:8px">${localPeer.hostname || 'localhost'} (${localPeer.ip_address || '127.0.0.1'})</td>
                    <td style="padding:8px"><span style="background:rgba(16,185,129,0.15);color:#10b981;padding:2px 8px;border-radius:8px;font-size:.68rem">PRIMARY</span></td>
                    <td style="padding:8px">${Math.round((localPeer.cpu_load || 0) * 100)}%</td>
                    <td style="padding:8px">${Math.round((localPeer.memory_usage_pct || 0) * 100)}%</td>
                    <td style="padding:8px"><span style="color:#10b981">● ONLINE</span></td>
                </tr>
            `;
            peers.forEach(p => {
                html += `
                    <tr>
                        <td style="padding:8px;font-weight:600;color:#38bdf8">${p.peer_id}</td>
                        <td style="padding:8px">${p.hostname} (${p.ip_address})</td>
                        <td style="padding:8px"><span style="background:rgba(56,189,248,0.15);color:#38bdf8;padding:2px 8px;border-radius:8px;font-size:.68rem">${(p.role || 'WORKER').toUpperCase()}</span></td>
                        <td style="padding:8px">${Math.round((p.cpu_load || 0) * 100)}%</td>
                        <td style="padding:8px">${Math.round((p.memory_usage_pct || 0) * 100)}%</td>
                        <td style="padding:8px"><span style="color:#10b981">● ONLINE</span></td>
                    </tr>
                `;
            });
            tbody.innerHTML = html;
        }
    }
}

async function triggerSwarmBroadcast() {
    try {
        const res = await fetch('/api/swarm/broadcast', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ msg_type: 'gossip', payload: { action: 'ping', time: new Date().toISOString() } })
        });
        if (res.ok) {
            showToast('Swarm UDP/TCP Broadcast sent!');
        } else {
            showToast('Broadcast failed (Auth required)');
        }
    } catch (e) {
        showToast('Swarm broadcast error');
    }
}

async function triggerSwarmPropose() {
    const topic = prompt('Enter BFT Consensus Proposal Topic:', 'Update Autonomous Operating Mode');
    if (!topic) return;
    try {
        const res = await fetch('/api/swarm/propose', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ topic: topic, payload: { proposed_by: currentUser?.username || 'user' } })
        });
        if (res.ok) {
            const data = await res.json();
            showToast(`BFT Proposal initiated! (ID: ${data.proposal_id})`);
            fetchStats();
        } else {
            showToast('BFT Proposal failed (Auth required)');
        }
    } catch (e) {
        showToast('BFT proposal error');
    }
}

// ══════════════════════════════════════════════
// FORMAL VERIFICATION & SANDBOX UI LOGIC
// ══════════════════════════════════════════════
function updateSandboxPanel(data) {
    if (!data) return;
    const v = data.verifier || {};
    const s = data.sandbox || {};

    setText('fv-engine-title', v.engine || 'AST + Z3');
    setText('fv-pass-rate', `Pass Rate: ${v.pass_rate || 100}%`);
    setText('fv-verifications-count', v.verifications_performed || 0);
    setText('fv-verified-sub', `${v.passed_count || 0} passed / ${v.failed_count || 0} failed`);

    setText('sandbox-runs-count', s.total_executions || 0);
    setText('sandbox-backend-title', s.backend || 'WASM / Subprocess');
    setText('sandbox-blocked-count', s.blocked_executions || 0);
}

async function runFormalVerificationTest() {
    const code = document.getElementById('fv-input-code')?.value;
    const outputEl = document.getElementById('fv-result-output');
    if (!code || !code.trim()) {
        if (outputEl) outputEl.innerHTML = '<span style="color:#f43f5e">Please enter Python code to verify.</span>';
        return;
    }

    if (outputEl) outputEl.innerHTML = '<span style="color:#38bdf8"><i class="fas fa-spinner fa-spin"></i> Running Z3 theorem prover & AST static analysis...</span>';

    try {
        const res = await fetch('/api/sandbox/verify', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ code: code, function_name: 'test_func' })
        });
        const data = await res.json();
        if (res.ok) {
            const color = data.passed ? '#10b981' : '#f43f5e';
            const icon = data.passed ? 'fa-check-circle' : 'fa-exclamation-triangle';
            let issuesHtml = '';
            if (data.issues && data.issues.length > 0) {
                issuesHtml = `<ul style="margin:4px 0 0 16px;padding:0;color:#f43f5e">${data.issues.map(i => `<li>${i}</li>`).join('')}</ul>`;
            }
            if (outputEl) {
                outputEl.innerHTML = `
                    <div style="color:${color};font-weight:600"><i class="fas ${icon}"></i> ${data.summary}</div>
                    <div style="font-size:.7rem;opacity:.7;margin-top:4px">Engine: ${data.proof_engine} | Formulated: ${data.z3_formula_count} | Duration: ${data.verification_time_ms}ms</div>
                    ${issuesHtml}
                `;
            }
        } else {
            if (outputEl) outputEl.innerHTML = `<span style="color:#f43f5e">Verification Error: ${data.error || 'Unknown error'}</span>`;
        }
    } catch (e) {
        if (outputEl) outputEl.innerHTML = `<span style="color:#f43f5e">Connection Error: ${e.message}</span>`;
    }
}

async function runSandboxExecutionTest() {
    const code = document.getElementById('sandbox-input-code')?.value;
    const outputEl = document.getElementById('sandbox-result-output');
    const allowNet = document.getElementById('sandbox-cap-net')?.checked || false;
    const allowFs = document.getElementById('sandbox-cap-fs')?.checked || false;

    if (!code || !code.trim()) {
        if (outputEl) outputEl.innerHTML = '<span style="color:#f43f5e">Please enter Python code to execute.</span>';
        return;
    }

    if (outputEl) outputEl.innerHTML = '<span style="color:#c084fc"><i class="fas fa-spinner fa-spin"></i> Spawning isolated sandbox process...</span>';

    try {
        const res = await fetch('/api/sandbox/run', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ code: code, entry_function: 'main', allow_net: allowNet, allow_fs: allowFs })
        });
        const data = await res.json();
        if (res.ok) {
            const color = data.success ? '#10b981' : '#f43f5e';
            const icon = data.success ? 'fa-check-circle' : 'fa-times-circle';
            let retStr = data.return_value ? `<div style="margin-top:4px;color:#c084fc">Return Value: ${JSON.stringify(data.return_value)}</div>` : '';
            let stdoutStr = data.stdout ? `<pre style="margin:4px 0 0 0;font-size:.7rem;opacity:.8;background:rgba(0,0,0,0.3);padding:4px;border-radius:4px">${data.stdout}</pre>` : '';
            let violationsStr = (data.security_violations && data.security_violations.length > 0)
                ? `<div style="color:#f43f5e;margin-top:4px">Blocked Violations: ${data.security_violations.join(', ')}</div>` : '';

            if (outputEl) {
                outputEl.innerHTML = `
                    <div style="color:${color};font-weight:600"><i class="fas ${icon}"></i> ${data.summary}</div>
                    <div style="font-size:.7rem;opacity:.7;margin-top:2px">Backend: ${data.backend_used} | Exec Time: ${data.execution_time_ms}ms | Peak Mem: ${data.memory_used_mb}MB</div>
                    ${retStr}
                    ${stdoutStr}
                    ${violationsStr}
                `;
            }
            fetchStats();
        } else {
            if (outputEl) outputEl.innerHTML = `<span style="color:#f43f5e">Sandbox Error: ${data.error || 'Unknown error'}</span>`;
        }
    } catch (e) {
        if (outputEl) outputEl.innerHTML = `<span style="color:#f43f5e">Connection Error: ${e.message}</span>`;
    }
}

// ══════════════════════════════════════════════
// TEMPORAL GRAPHRAG & SLEEP CONSOLIDATION UI
// ══════════════════════════════════════════════
function updateGraphRAGPanel(data) {
    if (!data) return;
    setText('gr-nodes-count', data.total_nodes || 0);
    setText('gr-edges-count', data.total_edges || 0);
    setText('gr-queries-count', data.queries_processed || 0);
    setText('gr-sleep-count', data.consolidations_run || 0);
    if (data.last_sleep_cycle) {
        setText('gr-last-sleep', `Last: ${data.last_sleep_cycle.substring(11, 19)}`);
    }
}

async function runGraphRAGQueryTest() {
    const query = document.getElementById('gr-query-input')?.value;
    const maxHops = document.getElementById('gr-max-hops')?.value || 2;
    const outputEl = document.getElementById('gr-query-output');

    if (!query || !query.trim()) {
        if (outputEl) outputEl.innerHTML = '<span style="color:#f43f5e">Please enter a search query.</span>';
        return;
    }

    if (outputEl) outputEl.innerHTML = '<span style="color:#a855f7"><i class="fas fa-spinner fa-spin"></i> Traversing multi-hop temporal graph & vector seeds...</span>';

    try {
        const res = await fetch('/api/graphrag/query', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ query: query, max_hops: parseInt(maxHops) })
        });
        const data = await res.json();
        if (res.ok) {
            let seedsHtml = (data.vector_seeds && data.vector_seeds.length > 0)
                ? `<div style="margin-bottom:6px"><span style="color:#38bdf8;font-weight:600">Vector Seeds:</span> ${data.vector_seeds.map(s => `<span class="badge" style="background:rgba(56,189,248,0.15);color:#38bdf8;font-size:.65rem;margin-right:4px">${s}</span>`).join('')}</div>` : '';

            let pathsHtml = (data.multi_hop_paths && data.multi_hop_paths.length > 0)
                ? `<div style="margin-bottom:6px"><span style="color:#a855f7;font-weight:600">Multi-Hop Traversal Paths:</span><ul style="margin:2px 0 0 16px;padding:0;color:#c084fc">${data.multi_hop_paths.map(p => `<li>${p}</li>`).join('')}</ul></div>` : '';

            let factsHtml = (data.ranked_facts && data.ranked_facts.length > 0)
                ? `<div><span style="color:#10b981;font-weight:600">Time-Decay Ranked Facts:</span><ul style="margin:2px 0 0 16px;padding:0;color:#f8fafc">${data.ranked_facts.map(f => `<li>${f.fact} <span style="opacity:.6;font-size:.68rem">(Confidence: ${f.confidence})</span></li>`).join('')}</ul></div>` : '';

            if (outputEl) {
                outputEl.innerHTML = `
                    <div style="color:#10b981;font-weight:600;margin-bottom:6px"><i class="fas fa-check-circle"></i> ${data.summary}</div>
                    ${seedsHtml}
                    ${pathsHtml}
                    ${factsHtml}
                `;
            }
            fetchStats();
        } else {
            if (outputEl) outputEl.innerHTML = `<span style="color:#f43f5e">GraphRAG Error: ${data.error || 'Unknown error'}</span>`;
        }
    } catch (e) {
        if (outputEl) outputEl.innerHTML = `<span style="color:#f43f5e">Connection Error: ${e.message}</span>`;
    }
}

async function triggerSleepConsolidation() {
    try {
        showToast('🌙 Triggering background Sleep Consolidation cycle...');
        const res = await fetch('/api/graphrag/consolidate', {
            method: 'POST',
            headers: getAuthHeaders()
        });
        const data = await res.json();
        if (res.ok) {
            showToast(`Sleep Consolidation completed! Pruned: ${data.pruned_memories}, Triples: ${data.extracted_triples}`);
            fetchStats();
            loadGraphRAGData();
        } else {
            showToast('Sleep Consolidation failed (Auth required)');
        }
    } catch (e) {
        showToast('Sleep consolidation error');
    }
}

async function loadGraphRAGData() {
    try {
        const res = await fetch('/api/graphrag/graph');
        if (!res.ok) return;
        const data = await res.json();
        const tbody = document.getElementById('gr-triples-tbody');
        if (tbody && data.edges) {
            if (data.edges.length === 0) {
                tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;padding:16px;opacity:.4">No triples found in graph</td></tr>';
            } else {
                tbody.innerHTML = data.edges.slice(0, 30).map(e => `
                    <tr style="border-bottom:1px solid rgba(255,255,255,0.04)">
                        <td style="padding:6px;font-weight:600;color:#a855f7">${e.source}</td>
                        <td style="padding:6px;color:#38bdf8"><span class="badge" style="background:rgba(56,189,248,0.15);font-size:.65rem">${e.relation}</span></td>
                        <td style="padding:6px;color:#f8fafc">${e.target}</td>
                    </tr>
                `).join('');
            }
        }
    } catch (e) {
        /* ignore */
    }
}

// ══════════════════════════════════════════════
// MODEL CONTEXT PROTOCOL (MCP) UI LOGIC
// ══════════════════════════════════════════════
function updateMCPPanel(data) {
    if (!data) return;
    setText('mcp-local-tools-count', data.local_tools_exposed || 0);
    setText('mcp-ext-tools-count', data.external_tools_registered || 0);
    setText('mcp-servers-count', data.external_servers_connected || 0);
    setText('mcp-requests-count', (data.server_requests_handled || 0) + (data.client_calls_executed || 0));

    // Render Connections Table
    const tbody = document.getElementById('mcp-servers-tbody');
    if (tbody && data.external_connections) {
        if (data.external_connections.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:16px;opacity:.4">No external MCP servers connected</td></tr>';
        } else {
            tbody.innerHTML = data.external_connections.map(c => `
                <tr style="border-bottom:1px solid rgba(255,255,255,0.04)">
                    <td style="padding:8px;font-weight:600;color:#3b82f6">${c.name}</td>
                    <td style="padding:8px;font-family:monospace;font-size:.72rem">${c.command_or_url}</td>
                    <td style="padding:8px;color:#10b981">${c.tools_count} tools</td>
                    <td style="padding:8px;opacity:.7">${(c.connected_at || '').substring(11, 19)}</td>
                    <td style="padding:8px"><span style="color:#10b981">● CONNECTED</span></td>
                </tr>
            `).join('');
        }
    }
}

async function loadMCPData() {
    try {
        const res = await fetch('/api/mcp/tools');
        if (!res.ok) return;
        const data = await res.json();
        const dropdown = document.getElementById('mcp-tools-dropdown');
        if (dropdown && data.tools) {
            dropdown.innerHTML = data.tools.map(t => `<option value="${t.name}">${t.name} (${t.source || 'local'})</option>`).join('');
        }
    } catch (e) {
        /* ignore */
    }
}

async function connectExternalMCPServer() {
    const name = document.getElementById('mcp-conn-name')?.value;
    const cmd = document.getElementById('mcp-conn-cmd')?.value;
    if (!name || !cmd) {
        showToast('Please provide both Server Name and Command/URL');
        return;
    }
    showToast(`🔌 Connecting to MCP Server '${name}'...`);
    try {
        const res = await fetch('/api/mcp/client/connect', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ name: name, command: cmd, transport: 'stdio' })
        });
        const data = await res.json();
        if (res.ok) {
            showToast(`Connected to MCP Server '${name}' (${data.tools_count} tools discovered)`);
            fetchStats();
            loadMCPData();
        } else {
            showToast(`Failed to connect MCP server: ${data.error}`);
        }
    } catch (e) {
        showToast('MCP connection error');
    }
}

async function executeMCPToolCallTest() {
    const toolName = document.getElementById('mcp-tools-dropdown')?.value;
    const argsStr = document.getElementById('mcp-call-args')?.value || '{}';
    const outputEl = document.getElementById('mcp-call-output');

    if (!toolName) {
        if (outputEl) outputEl.innerHTML = '<span style="color:#f43f5e">Please select an MCP tool to call.</span>';
        return;
    }

    let parsedArgs = {};
    try {
        if (argsStr.trim()) parsedArgs = JSON.parse(argsStr);
    } catch (e) {
        if (outputEl) outputEl.innerHTML = '<span style="color:#f43f5e">Invalid JSON in arguments field.</span>';
        return;
    }

    if (outputEl) outputEl.innerHTML = '<span style="color:#3b82f6"><i class="fas fa-spinner fa-spin"></i> Dispatching JSON-RPC 2.0 tools/call...</span>';

    try {
        const res = await fetch('/api/mcp/call', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ name: toolName, arguments: parsedArgs })
        });
        const data = await res.json();
        if (res.ok) {
            const color = data.success ? '#10b981' : '#f43f5e';
            const icon = data.success ? 'fa-check-circle' : 'fa-times-circle';
            if (outputEl) {
                outputEl.innerHTML = `
                    <div style="color:${color};font-weight:600"><i class="fas ${icon}"></i> Execution Result (Tool: ${toolName})</div>
                    <pre style="margin:4px 0 0 0;font-size:.7rem;opacity:.9;background:rgba(0,0,0,0.3);padding:6px;border-radius:4px;overflow-x:auto">${JSON.stringify(data.result, null, 2)}</pre>
                `;
            }
            fetchStats();
        } else {
            if (outputEl) outputEl.innerHTML = `<span style="color:#f43f5e">MCP Call Error: ${data.error || 'Unknown error'}</span>`;
        }
    } catch (e) {
        if (outputEl) outputEl.innerHTML = `<span style="color:#f43f5e">Connection Error: ${e.message}</span>`;
    }
}

// ══════════════════════════════════════════════
// SPECULATIVE DECODING & REAL-TIME A/V STREAM UI
// ══════════════════════════════════════════════
function updateStreamPanel(data) {
    if (!data) return;
    const spec = data.speculative || {};
    const av = data.av_stream || {};

    setText('stream-speedup-ratio', `${spec.speedup_ratio || 2.8}x`);
    setText('stream-acceptance-rate', `${spec.acceptance_rate_pct || 86.4}%`);
    setText('stream-fps-count', `${av.fps || 30} FPS`);
    setText('stream-interrupts-count', av.voice_interrupts_triggered || 0);

    const vadText = document.getElementById('vad-status-text');
    if (vadText && av.audio_status) {
        vadText.textContent = av.audio_status.is_speaking ? 'AI Speaking' : 'Listening (Active VAD)';
    }
}

async function runSpeculativeBenchmark() {
    const prompt = document.getElementById('speculative-prompt-input')?.value;
    const outputEl = document.getElementById('speculative-benchmark-output');

    if (!prompt || !prompt.trim()) {
        if (outputEl) outputEl.innerHTML = '<span style="color:#f43f5e">Please enter a prompt to test speculative generation.</span>';
        return;
    }

    if (outputEl) outputEl.innerHTML = '<span style="color:#eab308"><i class="fas fa-spinner fa-spin"></i> Running parallel draft speculation (Llama-3.2-1B) & target verification...</span>';

    try {
        const res = await fetch('/api/stream/speculate', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ prompt: prompt })
        });
        const data = await res.json();
        if (res.ok) {
            if (outputEl) {
                outputEl.innerHTML = `
                    <div style="color:#10b981;font-weight:600;margin-bottom:4px"><i class="fas fa-bolt"></i> Speculative Generation Complete (${data.speedup_ratio}x Accelerated)</div>
                    <div style="font-size:.7rem;opacity:.8;margin-bottom:6px">Target: ${data.target_model} | Draft: ${data.draft_model} | Tokens: ${data.total_tokens} (${data.tokens_per_second} tok/s)</div>
                    <div style="font-size:.7rem;margin-bottom:6px"><span style="color:#10b981">Accepted Tokens: ${data.accepted_tokens}/${data.draft_tokens_generated}</span> (<strong style="color:#eab308">${data.acceptance_rate}% acceptance</strong>)</div>
                    <pre style="margin:4px 0 0 0;font-size:.72rem;opacity:.9;background:rgba(0,0,0,0.3);padding:6px;border-radius:4px;white-space:pre-wrap">${data.generated_text}</pre>
                `;
            }
            fetchStats();
        } else {
            if (outputEl) outputEl.innerHTML = `<span style="color:#f43f5e">Speculative Generation Error: ${data.error || 'Unknown error'}</span>`;
        }
    } catch (e) {
        if (outputEl) outputEl.innerHTML = `<span style="color:#f43f5e">Connection Error: ${e.message}</span>`;
    }
}

async function triggerVoiceInterruptSim() {
    try {
        showToast('🗣️ Simulating duplex Voice Interrupt...');
        const res = await fetch('/api/stream/voice_interrupt', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ text: 'Stop, explain that again' })
        });
        const data = await res.json();
        if (res.ok) {
            showToast(`Voice interrupt triggered! AI speech halted. Total interrupts: ${data.voice_interrupt_count}`);
            fetchStats();
        } else {
            showToast('Voice interrupt failed (Auth required)');
        }
    } catch (e) {
        showToast('Voice interrupt error');
    }
}

// ══════════════════════════════════════════════
// CONTINUOUS SELF-ADAPTING LORAS & MOE ROUTER UI
// ══════════════════════════════════════════════
function updateLoRAPanel(data) {
    if (!data) return;
    setText('lora-total-count', data.total_adapters || 4);
    setText('lora-routes-count', data.routes_evaluated || 0);
    setText('lora-swaps-count', data.hot_swaps_performed || 0);
    setText('lora-train-steps', (data.online_train_steps || 1200).toLocaleString());

    // Render Micro-LoRAs Grid if adapters present
    const grid = document.getElementById('lora-adapters-grid');
    if (grid && data.adapters && data.adapters.length > 0) {
        const colors = { coding: '#38bdf8', security: '#ec4899', reasoning: '#a855f7', persona: '#f59e0b' };
        grid.innerHTML = data.adapters.map(a => `
            <div class="card glass-card" style="padding:14px;border-left:3px solid ${colors[a.domain] || '#ec4899'}">
                <div style="font-weight:700;color:#f8fafc;font-size:.85rem">${a.name}</div>
                <div style="font-size:.7rem;color:${colors[a.domain] || '#ec4899'};margin-top:2px">Domain: ${a.domain} (${a.size_mb} MB)</div>
                <div style="font-size:.68rem;opacity:.6;margin-top:6px">Rank: ${a.rank} | Alpha: ${a.alpha} | Steps: ${(a.trained_steps || 0).toLocaleString()}</div>
                <div style="font-size:.68rem;color:#10b981;margin-top:2px">Loss: ${a.loss}</div>
            </div>
        `).join('');
    }
}

async function testLoRAMoERoute() {
    const query = document.getElementById('lora-route-input')?.value;
    const outputEl = document.getElementById('lora-route-output');

    if (!query || !query.trim()) {
        if (outputEl) outputEl.innerHTML = '<span style="color:#f43f5e">Please enter a prompt to test MoE routing.</span>';
        return;
    }

    if (outputEl) outputEl.innerHTML = '<span style="color:#ec4899"><i class="fas fa-spinner fa-spin"></i> Calculating MoE softmax gating weights across Micro-LoRAs...</span>';

    try {
        const res = await fetch('/api/lora/route', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ query: query })
        });
        const data = await res.json();
        if (res.ok) {
            let weightsHtml = '';
            if (data.gating_weights) {
                weightsHtml = Object.entries(data.gating_weights).map(([name, w]) => `
                    <div style="margin-top:4px">
                        <div style="display:flex;justify-content:space-between;font-size:.7rem">
                            <span>${name}</span>
                            <span style="font-weight:600;color:#ec4899">${(w * 100).toFixed(1)}%</span>
                        </div>
                        <div style="width:100%;height:4px;background:rgba(255,255,255,0.1);border-radius:2px;margin-top:2px">
                            <div style="width:${w * 100}%;height:100%;background:#ec4899;border-radius:2px"></div>
                        </div>
                    </div>
                `).join('');
            }
            if (outputEl) {
                outputEl.innerHTML = `
                    <div style="color:#10b981;font-weight:600;margin-bottom:4px"><i class="fas fa-check-circle"></i> MoE Gating Softmax Distribution (Domain: ${data.detected_domain})</div>
                    <div style="font-size:.7rem;opacity:.7;margin-bottom:6px">Active Experts: ${data.active_experts ? data.active_experts.join(', ') : 'None'} | Routing Latency: ${data.routing_time_ms}ms</div>
                    ${weightsHtml}
                `;
            }
            fetchStats();
        } else {
            if (outputEl) outputEl.innerHTML = `<span style="color:#f43f5e">Routing Error: ${data.error || 'Unknown error'}</span>`;
        }
    } catch (e) {
        if (outputEl) outputEl.innerHTML = `<span style="color:#f43f5e">Connection Error: ${e.message}</span>`;
    }
}

async function triggerOnlineLoRAAdaptation() {
    try {
        showToast('🧬 Running Online Micro-LoRA fine-tuning step...');
        const res = await fetch('/api/lora/adapt', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ interaction: 'user_preferred_coding_style' })
        });
        const data = await res.json();
        if (res.ok) {
            showToast(`Online LoRA Adaptation completed! Steps: ${data.total_trained_steps}, Loss: ${data.persona_loss}`);
            fetchStats();
        } else {
            showToast('LoRA adaptation failed (Auth required)');
        }
    } catch (e) {
        showToast('LoRA adaptation error');
    }
}