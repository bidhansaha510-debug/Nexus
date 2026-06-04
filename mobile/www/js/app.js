/*
 * NEXUS AI Mobile — Connection & WebView Logic
 */

// ══════════════════════════════════════════════
// CONSTANTS & STATE
// ══════════════════════════════════════════════
const STORAGE_KEY = 'nexus_server_url';
const HISTORY_KEY = 'nexus_server_history';
const MAX_HISTORY = 5;
const HEALTH_TIMEOUT = 8000;  // ms
const SCAN_TIMEOUT = 5000;    // ms per server scan

// ── PRIMARY PERMANENT SERVER ──
const PRIMARY_SERVER = 'http://nexusaisystems.qzz.io';
const PRIMARY_TIMEOUT = 6000; // ms — timeout for primary auto-connect

let currentServerUrl = '';
let isConnected = false;
let isScanning = false;
let splashDone = false;

// ══════════════════════════════════════════════
// CANDIDATE SERVER URLs
// ══════════════════════════════════════════════
const CLOUDFLARE_KEY = 'nexus_cloudflare_url';

function getCandidateServers() {
    const candidates = [
        { url: PRIMARY_SERVER, label: 'Primary ☁️' },
        { url: 'http://localhost:5000', label: 'Local' },
        { url: 'http://127.0.0.1:5000', label: 'Local' },
        { url: 'http://192.168.1.2:5000', label: 'LAN' },
        { url: 'http://192.168.1.3:5000', label: 'LAN' },
        { url: 'http://192.168.1.4:5000', label: 'LAN' },
        { url: 'http://192.168.1.5:5000', label: 'LAN' },
        { url: 'http://192.168.1.6:5000', label: 'LAN' },
        { url: 'http://192.168.1.7:5000', label: 'LAN' },
        { url: 'http://192.168.1.8:5000', label: 'LAN' },
        { url: 'http://192.168.1.9:5000', label: 'LAN' },
        { url: 'http://192.168.1.10:5000', label: 'LAN' },
        { url: 'http://192.168.0.2:5000', label: 'LAN' },
        { url: 'http://192.168.0.3:5000', label: 'LAN' },
        { url: 'http://192.168.0.4:5000', label: 'LAN' },
        { url: 'http://192.168.0.5:5000', label: 'LAN' },
        { url: 'http://192.168.0.100:5000', label: 'LAN' },
        { url: 'http://192.168.1.100:5000', label: 'LAN' },
        { url: 'http://10.0.0.2:5000', label: 'LAN' },
        { url: 'http://10.0.0.5:5000', label: 'LAN' },
        { url: 'https://nexus-ai.onrender.com', label: 'Cloud' },
    ];

    // Always include the last-known Cloudflare tunnel URL (persisted across sessions)
    const savedCfUrl = localStorage.getItem(CLOUDFLARE_KEY);
    if (savedCfUrl && savedCfUrl !== PRIMARY_SERVER) {
        candidates.splice(1, 0, { url: savedCfUrl, label: 'Tunnel ☁️' });
    }

    // Add any servers from history that aren't already in the list
    const history = getHistory();
    const existingUrls = new Set(candidates.map(c => c.url));
    for (const histUrl of history) {
        if (!existingUrls.has(histUrl)) {
            const isCloud = histUrl.includes('.onrender.com') || histUrl.includes('.render.com')
                || histUrl.includes('ngrok') || histUrl.includes('trycloudflare');
            candidates.push({ url: histUrl, label: isCloud ? 'Cloud' : 'Saved' });
            existingUrls.add(histUrl);
        }
    }

    return candidates;
}

// ══════════════════════════════════════════════
// SPLASH SCREEN
// ══════════════════════════════════════════════
function initSplashNeuralBg() {
    const canvas = document.getElementById('splash-neural-bg');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    const nodes = [];
    const nodeCount = 30;
    for (let i = 0; i < nodeCount; i++) {
        nodes.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            vx: (Math.random() - 0.5) * 0.6,
            vy: (Math.random() - 0.5) * 0.6,
            radius: Math.random() * 2.5 + 1,
            alpha: Math.random() * 0.4 + 0.1,
        });
    }

    let frame;
    function draw() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Update and draw nodes
        for (const n of nodes) {
            n.x += n.vx;
            n.y += n.vy;
            if (n.x < 0 || n.x > canvas.width) n.vx *= -1;
            if (n.y < 0 || n.y > canvas.height) n.vy *= -1;

            ctx.beginPath();
            ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(0, 212, 255, ${n.alpha})`;
            ctx.fill();
        }

        // Draw connections
        for (let i = 0; i < nodes.length; i++) {
            for (let j = i + 1; j < nodes.length; j++) {
                const dx = nodes[i].x - nodes[j].x;
                const dy = nodes[i].y - nodes[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 150) {
                    const alpha = (1 - dist / 150) * 0.15;
                    ctx.beginPath();
                    ctx.moveTo(nodes[i].x, nodes[i].y);
                    ctx.lineTo(nodes[j].x, nodes[j].y);
                    ctx.strokeStyle = `rgba(0, 212, 255, ${alpha})`;
                    ctx.lineWidth = 0.8;
                    ctx.stroke();
                }
            }
        }

        frame = requestAnimationFrame(draw);
    }
    draw();

    // Stop animation when splash ends
    setTimeout(() => {
        cancelAnimationFrame(frame);
    }, 4200);
}

function createSplashParticles() {
    const container = document.getElementById('splash-particles');
    if (!container) return;

    for (let i = 0; i < 20; i++) {
        const particle = document.createElement('div');
        particle.className = 'splash-particle';
        const angle = (Math.PI * 2 * i) / 20;
        const distance = 60 + Math.random() * 80;
        const tx = Math.cos(angle) * distance;
        const ty = Math.sin(angle) * distance;
        particle.style.setProperty('--tx', `${tx}px`);
        particle.style.setProperty('--ty', `${ty}px`);
        particle.style.setProperty('--delay', `${0.8 + Math.random() * 0.6}s`);
        particle.style.setProperty('--size', `${2 + Math.random() * 4}px`);
        container.appendChild(particle);
    }
}

function hideSplash() {
    const splash = document.getElementById('splash-screen');
    if (!splash) return;
    splash.classList.add('splash-fade-out');
    setTimeout(() => {
        splash.style.display = 'none';
        splashDone = true;
    }, 600);
}

// ══════════════════════════════════════════════
// AUTO-CONNECT TO PRIMARY SERVER
// ══════════════════════════════════════════════
async function autoConnectPrimary() {
    // Update splash loader text
    const loaderText = document.querySelector('.splash-loader-text');
    if (loaderText) loaderText.textContent = 'Connecting to NEXUS...';

    try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), PRIMARY_TIMEOUT);

        const response = await fetch(`${PRIMARY_SERVER}/api/health`, {
            signal: controller.signal,
            mode: 'cors',
        });
        clearTimeout(timeout);

        if (response.ok) {
            const data = await response.json();
            if (data.status === 'ok') {
                // Primary server is online — connect!
                currentServerUrl = PRIMARY_SERVER;
                isConnected = true;
                localStorage.setItem(STORAGE_KEY, PRIMARY_SERVER);
                addToHistory(PRIMARY_SERVER);

                if (loaderText) loaderText.textContent = 'Connected!';

                // Wait for splash to finish, then load
                await waitForSplash();
                hideSplash();
                showLoading(PRIMARY_SERVER);
                setTimeout(() => loadWebUI(PRIMARY_SERVER), 400);
                return;
            }
        }
    } catch (e) {
        // Primary unreachable — fall back
    }

    // Primary failed — try saved URL
    const savedUrl = localStorage.getItem(STORAGE_KEY);
    if (savedUrl && savedUrl !== PRIMARY_SERVER) {
        if (loaderText) loaderText.textContent = 'Trying saved server...';
        try {
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), PRIMARY_TIMEOUT);

            const response = await fetch(`${savedUrl}/api/health`, {
                signal: controller.signal,
                mode: 'cors',
            });
            clearTimeout(timeout);

            if (response.ok) {
                const data = await response.json();
                if (data.status === 'ok') {
                    currentServerUrl = savedUrl;
                    isConnected = true;
                    addToHistory(savedUrl);

                    if (loaderText) loaderText.textContent = 'Connected!';
                    await waitForSplash();
                    hideSplash();
                    showLoading(savedUrl);
                    setTimeout(() => loadWebUI(savedUrl), 400);
                    return;
                }
            }
        } catch (e) {
            // Saved URL also failed
        }
    }

    // All auto-connect attempts failed — show connection screen
    if (loaderText) loaderText.textContent = 'Server unavailable';
    await waitForSplash();
    hideSplash();

    // Pre-fill the primary URL for easy retry
    const urlInput = document.getElementById('server-url');
    if (urlInput && !urlInput.value) {
        urlInput.value = savedUrl || PRIMARY_SERVER;
    }
}

function waitForSplash() {
    // Minimum splash display time: 3500ms from page load
    const elapsed = performance.now();
    const remaining = Math.max(0, 3500 - elapsed);
    return new Promise(resolve => setTimeout(resolve, remaining));
}

// ══════════════════════════════════════════════
// SERVER SCANNING
// ══════════════════════════════════════════════
async function scanForServers() {
    if (isScanning) return;
    isScanning = true;

    const scanBtn = document.getElementById('scan-btn');
    const scanIcon = document.getElementById('scan-icon');
    const scanLabel = document.getElementById('scan-label');
    const serverList = document.getElementById('server-list');
    const emptyMsg = document.getElementById('server-list-empty');

    // Update button state
    scanBtn.classList.add('scanning');
    scanIcon.className = 'fas fa-sync-alt';
    scanLabel.textContent = 'Scanning...';

    // Get all candidates
    const candidates = getCandidateServers();

    // Show placeholder cards
    if (emptyMsg) emptyMsg.style.display = 'none';
    serverList.innerHTML = candidates.slice(0, 6).map(c => `
        <div class="server-card scanning-card">
            <div class="server-card-status checking"></div>
            <div class="server-card-info">
                <div class="server-card-url">${escapeHtml(c.url)}</div>
                <div class="server-card-meta">
                    <span class="label">${c.label}</span>
                    <span>Checking...</span>
                </div>
            </div>
            <div class="server-card-action"><i class="fas fa-spinner fa-spin"></i></div>
        </div>
    `).join('');

    // Scan all in parallel — first pass
    const results = [];
    const discoveredCloudUrls = [];
    const scanPromises = candidates.map(async (candidate) => {
        const result = { url: candidate.url, label: candidate.label, online: false, latency: null };
        try {
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), SCAN_TIMEOUT);
            const start = performance.now();

            const response = await fetch(`${candidate.url}/api/health`, {
                signal: controller.signal,
                mode: 'cors',
            });
            clearTimeout(timeout);

            const elapsed = Math.round(performance.now() - start);

            if (response.ok) {
                const data = await response.json();
                if (data.status === 'ok') {
                    result.online = true;
                    result.latency = elapsed;

                    // If server reports a Cloudflare tunnel URL, save it and queue for scanning
                    if (data.public_url) {
                        // Persist the latest tunnel URL so it's available on any network
                        localStorage.setItem(CLOUDFLARE_KEY, data.public_url);
                        if (!candidates.some(c => c.url === data.public_url)) {
                            discoveredCloudUrls.push(data.public_url);
                        }
                    }
                }
            }
        } catch (e) {
            // Server unreachable — keep online = false
        }
        results.push(result);
        return result;
    });

    await Promise.allSettled(scanPromises);

    // Second pass — scan any Cloudflare tunnel URLs discovered from servers
    if (discoveredCloudUrls.length > 0) {
        const cloudPromises = discoveredCloudUrls.map(async (cloudUrl) => {
            // Skip if already in results
            if (results.some(r => r.url === cloudUrl)) return;
            const result = { url: cloudUrl, label: 'Tunnel', online: false, latency: null };
            try {
                const controller = new AbortController();
                const timeout = setTimeout(() => controller.abort(), SCAN_TIMEOUT);
                const start = performance.now();

                const response = await fetch(`${cloudUrl}/api/health`, {
                    signal: controller.signal,
                    mode: 'cors',
                });
                clearTimeout(timeout);

                const elapsed = Math.round(performance.now() - start);

                if (response.ok) {
                    const data = await response.json();
                    if (data.status === 'ok') {
                        result.online = true;
                        result.latency = elapsed;
                    }
                }
            } catch (e) {
                // Tunnel unreachable
            }
            results.push(result);
        });
        await Promise.allSettled(cloudPromises);
    }

    // Sort: online first, then by latency
    results.sort((a, b) => {
        if (a.online && !b.online) return -1;
        if (!a.online && b.online) return 1;
        if (a.online && b.online) return (a.latency || 9999) - (b.latency || 9999);
        return 0;
    });

    // Render results — show all online + first few offline
    const onlineResults = results.filter(r => r.online);
    const offlineResults = results.filter(r => !r.online).slice(0, 3);
    const displayResults = [...onlineResults, ...offlineResults];

    if (displayResults.length === 0) {
        serverList.innerHTML = `
            <div class="server-list-empty">
                <i class="fas fa-exclamation-circle"></i>
                <span>No NEXUS servers found. Start your server and try again.</span>
            </div>
        `;
    } else {
        serverList.innerHTML = displayResults.map(r => {
            const statusClass = r.online ? 'online' : 'offline';
            const statusText = r.online ? 'Online' : 'Offline';
            const latencyHtml = r.online && r.latency !== null
                ? `<span class="latency${r.latency > 2000 ? ' slow' : ''}">${r.latency}ms</span>`
                : '';
            const actionIcon = r.online
                ? '<i class="fas fa-chevron-right"></i>'
                : '<i class="fas fa-times"></i>';
            const clickHandler = r.online
                ? `onclick="selectDiscoveredServer('${escapeHtml(r.url)}')"` : '';

            return `
                <div class="server-card ${statusClass}" ${clickHandler}>
                    <div class="server-card-status ${statusClass}"></div>
                    <div class="server-card-info">
                        <div class="server-card-url">${escapeHtml(r.url)}</div>
                        <div class="server-card-meta">
                            <span class="label">${r.label}</span>
                            <span>${statusText}</span>
                            ${latencyHtml}
                        </div>
                    </div>
                    <div class="server-card-action">${actionIcon}</div>
                </div>
            `;
        }).join('');
    }

    // Reset button
    scanBtn.classList.remove('scanning');
    scanIcon.className = 'fas fa-sync-alt';
    scanLabel.textContent = 'Scan';
    isScanning = false;
}

function selectDiscoveredServer(url) {
    document.getElementById('server-url').value = url;
    connectToServer();
}

// ══════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    // Start splash animation immediately
    initSplashNeuralBg();
    createSplashParticles();

    // Initialize background particles (for connection screen)
    initParticles();
    loadRecentServers();

    // Enter key to connect
    const urlInput = document.getElementById('server-url');
    urlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') connectToServer();
    });

    // Close fab menu when tapping outside
    document.addEventListener('click', (e) => {
        const fabMenu = document.getElementById('fab-menu');
        if (fabMenu && !fabMenu.contains(e.target)) {
            document.getElementById('fab-options').classList.remove('open');
        }
    });

    // Auto-connect: try primary server first, then fallback
    // This runs during the splash animation
    autoConnectPrimary().then(() => {
        // If we didn't connect, show connection screen + auto-scan
        if (!isConnected) {
            setTimeout(() => scanForServers(), 500);
        }
    });
});

// ══════════════════════════════════════════════
// CONNECTION LOGIC
// ══════════════════════════════════════════════
async function connectToServer() {
    const urlInput = document.getElementById('server-url');
    const connectBtn = document.getElementById('connect-btn');
    const statusEl = document.getElementById('connect-status');
    const errorEl = document.getElementById('connect-error');

    let url = (urlInput.value || '').trim();
    if (!url) {
        showError('Please enter a server URL');
        return;
    }

    // Add protocol if missing
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        url = 'http://' + url;
    }
    // Remove trailing slash
    url = url.replace(/\/+$/, '');

    // Validate URL format
    try {
        new URL(url);
    } catch (e) {
        showError('Invalid URL format');
        return;
    }

    // Update UI — show loading
    connectBtn.disabled = true;
    connectBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Connecting...</span>';
    errorEl.textContent = '';
    statusEl.className = 'connect-status';
    statusEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span>Checking server...</span>';

    try {
        // Check if server is reachable via /api/health
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), HEALTH_TIMEOUT);

        const response = await fetch(`${url}/api/health`, {
            signal: controller.signal,
            mode: 'cors',
        });
        clearTimeout(timeout);

        if (!response.ok) {
            throw new Error(`Server returned ${response.status}`);
        }

        const data = await response.json();
        if (data.status !== 'ok') {
            throw new Error('Server health check failed');
        }

        // Success — save and connect
        currentServerUrl = url;
        isConnected = true;

        // Save to history
        if (document.getElementById('remember-server').checked) {
            localStorage.setItem(STORAGE_KEY, url);
        }
        addToHistory(url);

        // Show loading overlay
        showLoading(url);

        // Load the NEXUS web UI in the iframe
        setTimeout(() => {
            loadWebUI(url);
        }, 800);

    } catch (e) {
        let errorMsg = 'Could not connect to server';
        if (e.name === 'AbortError') {
            errorMsg = 'Connection timed out — check the URL';
        } else if (e.message.includes('Failed to fetch') || e.message.includes('NetworkError')) {
            errorMsg = 'Network error — is the server running?';
        } else if (e.message.includes('CORS')) {
            errorMsg = 'CORS error — server may not allow this connection';
        } else if (e.message) {
            errorMsg = e.message;
        }

        showError(errorMsg);
        statusEl.className = 'connect-status error';
        statusEl.innerHTML = `<i class="fas fa-exclamation-triangle"></i> <span>Connection failed</span>`;
    } finally {
        connectBtn.disabled = false;
        connectBtn.innerHTML = '<i class="fas fa-bolt"></i> <span>Connect</span>';
    }
}

function loadWebUI(url) {
    const frame = document.getElementById('nexus-frame');
    const connectScreen = document.getElementById('connect-screen');
    const loadingOverlay = document.getElementById('loading-overlay');
    const fabMenu = document.getElementById('fab-menu');

    frame.src = url;
    frame.style.display = 'block';

    frame.onload = () => {
        // Hide loading and connection screen
        loadingOverlay.style.display = 'none';
        connectScreen.style.display = 'none';
        fabMenu.style.display = 'block';
    };

    // Fallback — hide loading after timeout even if onload doesn't fire
    setTimeout(() => {
        loadingOverlay.style.display = 'none';
        connectScreen.style.display = 'none';
        fabMenu.style.display = 'block';
    }, 10000);
}

function showLoading(url) {
    const overlay = document.getElementById('loading-overlay');
    const urlLabel = document.getElementById('loading-url');
    overlay.style.display = 'flex';
    urlLabel.textContent = url;
}

function showError(msg) {
    const errorEl = document.getElementById('connect-error');
    errorEl.textContent = msg;
}

// ══════════════════════════════════════════════
// FAB MENU ACTIONS
// ══════════════════════════════════════════════
function toggleFabMenu() {
    const options = document.getElementById('fab-options');
    options.classList.toggle('open');
}

function refreshServer() {
    const frame = document.getElementById('nexus-frame');
    if (frame && currentServerUrl) {
        frame.src = currentServerUrl;
    }
    document.getElementById('fab-options').classList.remove('open');
}

function disconnectServer() {
    const frame = document.getElementById('nexus-frame');
    const connectScreen = document.getElementById('connect-screen');
    const fabMenu = document.getElementById('fab-menu');
    const statusEl = document.getElementById('connect-status');

    frame.src = '';
    frame.style.display = 'none';
    connectScreen.style.display = 'flex';
    fabMenu.style.display = 'none';
    isConnected = false;
    currentServerUrl = '';

    statusEl.className = 'connect-status';
    statusEl.innerHTML = '<i class="fas fa-link"></i> <span>Enter your NEXUS server address</span>';

    document.getElementById('fab-options').classList.remove('open');
}

function showServerInfo() {
    document.getElementById('fab-options').classList.remove('open');

    const overlay = document.createElement('div');
    overlay.className = 'toast-overlay';
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

    const connectedAt = new Date().toLocaleTimeString();

    overlay.innerHTML = `
        <div class="toast-box">
            <h3><i class="fas fa-server"></i> Server Info</h3>
            <div class="info-row">
                <span class="info-key">URL</span>
                <span class="info-val">${escapeHtml(currentServerUrl)}</span>
            </div>
            <div class="info-row">
                <span class="info-key">Status</span>
                <span class="info-val" style="color: var(--accent-green)">● Connected</span>
            </div>
            <div class="info-row">
                <span class="info-key">Session</span>
                <span class="info-val">${connectedAt}</span>
            </div>
            <button class="close-toast" onclick="this.closest('.toast-overlay').remove()">Close</button>
        </div>
    `;

    document.body.appendChild(overlay);
}

// ══════════════════════════════════════════════
// RECENT SERVERS
// ══════════════════════════════════════════════
function loadRecentServers() {
    const history = getHistory();
    const container = document.getElementById('recent-servers');
    const list = document.getElementById('recent-list');

    if (history.length === 0) {
        container.style.display = 'none';
        return;
    }

    container.style.display = 'block';
    list.innerHTML = history.map((url, i) => `
        <div class="recent-item" onclick="selectRecentServer('${escapeHtml(url)}')">
            <span class="recent-item-url">${escapeHtml(url)}</span>
            <button class="recent-item-remove" onclick="event.stopPropagation(); removeFromHistory(${i})">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `).join('');
}

function selectRecentServer(url) {
    document.getElementById('server-url').value = url;
    connectToServer();
}

function getHistory() {
    try {
        return JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]');
    } catch {
        return [];
    }
}

function addToHistory(url) {
    let history = getHistory();
    // Remove if already present
    history = history.filter(u => u !== url);
    // Add to front
    history.unshift(url);
    // Keep max
    if (history.length > MAX_HISTORY) history = history.slice(0, MAX_HISTORY);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    loadRecentServers();
}

function removeFromHistory(index) {
    let history = getHistory();
    history.splice(index, 1);
    localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    loadRecentServers();
}

// ══════════════════════════════════════════════
// PARTICLE BACKGROUND (lightweight version)
// ══════════════════════════════════════════════
let particles = [];
let particleCtx = null;
let particleAnimFrame = null;

function initParticles() {
    const canvas = document.getElementById('particle-bg');
    if (!canvas) return;

    particleCtx = canvas.getContext('2d');
    resizeCanvas(canvas);
    window.addEventListener('resize', () => resizeCanvas(canvas));

    // Create particles
    const count = 40;
    for (let i = 0; i < count; i++) {
        particles.push({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            vx: (Math.random() - 0.5) * 0.3,
            vy: (Math.random() - 0.5) * 0.3,
            size: Math.random() * 2 + 0.5,
            alpha: Math.random() * 0.4 + 0.1,
        });
    }

    animateParticles(canvas);
}

function resizeCanvas(canvas) {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
}

function animateParticles(canvas) {
    const ctx = particleCtx;
    const w = canvas.width;
    const h = canvas.height;

    ctx.clearRect(0, 0, w, h);

    // Update and draw particles
    for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;

        // Wrap around
        if (p.x < 0) p.x = w;
        if (p.x > w) p.x = 0;
        if (p.y < 0) p.y = h;
        if (p.y > h) p.y = 0;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0, 212, 255, ${p.alpha})`;
        ctx.fill();
    }

    // Draw connections
    const connDist = 100;
    for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
            const dx = particles[i].x - particles[j].x;
            const dy = particles[i].y - particles[j].y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < connDist) {
                const alpha = (1 - dist / connDist) * 0.12;
                ctx.beginPath();
                ctx.moveTo(particles[i].x, particles[i].y);
                ctx.lineTo(particles[j].x, particles[j].y);
                ctx.strokeStyle = `rgba(0, 212, 255, ${alpha})`;
                ctx.lineWidth = 0.5;
                ctx.stroke();
            }
        }
    }

    particleAnimFrame = requestAnimationFrame(() => animateParticles(canvas));
}

// ══════════════════════════════════════════════
// UTILS
// ══════════════════════════════════════════════
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
