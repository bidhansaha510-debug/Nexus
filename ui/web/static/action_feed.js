/**
 * NEXUS AI — JARVIS Live Action Feed
 * ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 * 
 * Real-time action feed panel that shows NEXUS's thoughts, commands,
 * and physical actions as they happen — like Tony Stark's JARVIS HUD.
 * 
 * Connects to /api/live/stream via SSE and renders glassmorphic action
 * cards with smooth animations.
 */

class JarvisActionFeed {
    constructor() {
        this.eventSource = null;
        this.actions = [];
        this.maxActions = 50;
        this.panel = null;
        this.feedContainer = null;
        this.isVisible = false;
        this.isPaused = false;
        this.token = localStorage.getItem('nexus_token') || '';
    }

    // ── INITIALIZATION ──

    init() {
        this.createPanel();
        this.connectSSE();
        console.log('[JARVIS] Action feed initialized');
    }

    createPanel() {
        // Floating toggle button
        const toggleBtn = document.createElement('button');
        toggleBtn.id = 'jarvis-toggle';
        toggleBtn.innerHTML = '⚡';
        toggleBtn.title = 'NEXUS Live Actions';
        toggleBtn.onclick = () => this.toggle();
        document.body.appendChild(toggleBtn);

        // Main panel
        this.panel = document.createElement('div');
        this.panel.id = 'jarvis-panel';
        this.panel.className = 'jarvis-panel hidden';
        this.panel.innerHTML = `
            <div class="jarvis-header">
                <div class="jarvis-header-left">
                    <span class="jarvis-pulse"></span>
                    <span class="jarvis-title">NEXUS LIVE</span>
                    <span class="jarvis-badge" id="jarvis-count">0</span>
                </div>
                <div class="jarvis-header-right">
                    <button class="jarvis-btn" id="jarvis-pause" title="Pause">⏸</button>
                    <button class="jarvis-btn" id="jarvis-clear" title="Clear">🗑</button>
                    <button class="jarvis-btn" id="jarvis-close" title="Close">✕</button>
                </div>
            </div>
            <div class="jarvis-feed" id="jarvis-feed"></div>
            <div class="jarvis-status" id="jarvis-status">
                <span class="jarvis-status-dot"></span>
                <span id="jarvis-status-text">Connecting...</span>
            </div>
        `;
        document.body.appendChild(this.panel);

        this.feedContainer = document.getElementById('jarvis-feed');

        // Event listeners
        document.getElementById('jarvis-pause').onclick = () => this.togglePause();
        document.getElementById('jarvis-clear').onclick = () => this.clearFeed();
        document.getElementById('jarvis-close').onclick = () => this.toggle();

        // Pause on hover for reading
        this.feedContainer.addEventListener('mouseenter', () => { this.isPaused = true; });
        this.feedContainer.addEventListener('mouseleave', () => { this.isPaused = false; });
    }

    // ── SSE CONNECTION ──

    connectSSE() {
        if (this.eventSource) {
            this.eventSource.close();
        }

        this.eventSource = new EventSource('/api/live/stream');

        this.eventSource.onopen = () => {
            this.setStatus('connected', 'Live');
        };

        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleEvent(data);
            } catch (e) {
                console.warn('[JARVIS] Parse error:', e);
            }
        };

        this.eventSource.onerror = () => {
            this.setStatus('disconnected', 'Reconnecting...');
            // Auto-reconnect is handled by EventSource
        };
    }

    // ── EVENT HANDLING ──

    handleEvent(data) {
        if (data.type === 'connected') {
            this.setStatus('connected', 'Live');
            return;
        }

        const card = this.createActionCard(data);
        if (card) {
            this.actions.unshift(data);
            if (this.actions.length > this.maxActions) {
                this.actions.pop();
                if (this.feedContainer.lastChild) {
                    this.feedContainer.lastChild.remove();
                }
            }

            // Animate in
            card.style.opacity = '0';
            card.style.transform = 'translateY(-20px)';
            this.feedContainer.prepend(card);

            requestAnimationFrame(() => {
                card.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            });

            // Update counter
            document.getElementById('jarvis-count').textContent = this.actions.length;

            // Pulse the toggle button
            const toggle = document.getElementById('jarvis-toggle');
            toggle.classList.add('jarvis-pulse-btn');
            setTimeout(() => toggle.classList.remove('jarvis-pulse-btn'), 600);
        }
    }

    createActionCard(data) {
        const card = document.createElement('div');
        card.className = `jarvis-card jarvis-${data.type || 'info'}`;

        const icon = this.getIcon(data);
        const title = this.getTitle(data);
        const detail = this.getDetail(data);
        const time = new Date().toLocaleTimeString('en-US', { hour12: false });
        const sourceTag = data.source === 'chat_command' ? '<span class="jarvis-tag chat">CHAT</span>' : 
                          data.source === 'autonomous' ? '<span class="jarvis-tag auto">AUTO</span>' : '';

        card.innerHTML = `
            <div class="jarvis-card-icon">${icon}</div>
            <div class="jarvis-card-body">
                <div class="jarvis-card-header">
                    <span class="jarvis-card-title">${title}</span>
                    ${sourceTag}
                    <span class="jarvis-card-time">${time}</span>
                </div>
                ${detail ? `<div class="jarvis-card-detail">${detail}</div>` : ''}
            </div>
            ${data.success !== undefined ? `<div class="jarvis-card-status ${data.success ? 'ok' : 'fail'}">${data.success ? '✓' : '✗'}</div>` : ''}
        `;

        return card;
    }

    getIcon(data) {
        const icons = {
            'action_detected': '🎯',
            'plan_generated': '📋',
            'executing': '⚡',
            'action_complete': '✅',
            'chat_action': '💬',
            'click': '🖱️',
            'type_text': '⌨️',
            'hotkey': '⌨️',
            'press_key': '⌨️',
            'open_app': '🚀',
            'open_url': '🌐',
            'shell': '💻',
            'powershell': '💻',
            'screenshot': '📸',
            'scroll': '📜',
            'move_mouse': '🖱️',
            'notify': '🔔',
            'think': '🧠',
            'wait': '⏳',
            'error': '❌',
        };
        return icons[data.type] || icons[data.action] || '⚡';
    }

    getTitle(data) {
        switch (data.type) {
            case 'action_detected': return `Intent: ${data.category || 'action'}`;
            case 'plan_generated': return `Plan: ${data.actions?.length || 0} steps`;
            case 'executing': return `Executing: ${data.action || '...'}`;
            case 'action_complete': return data.success ? 'Action Complete' : 'Action Failed';
            case 'chat_action': return `Command: ${(data.command || '').substring(0, 40)}`;
            default: return data.type || 'Event';
        }
    }

    getDetail(data) {
        if (data.thought) return `💭 ${data.thought}`;
        if (data.detail) return data.detail;
        if (data.message) return data.message;
        if (data.response) return data.response.substring(0, 100);
        if (data.command) return data.command;
        return '';
    }

    // ── CONTROLS ──

    toggle() {
        this.isVisible = !this.isVisible;
        this.panel.classList.toggle('hidden', !this.isVisible);
        document.getElementById('jarvis-toggle').classList.toggle('active', this.isVisible);
    }

    togglePause() {
        this.isPaused = !this.isPaused;
        document.getElementById('jarvis-pause').textContent = this.isPaused ? '▶' : '⏸';
    }

    clearFeed() {
        this.actions = [];
        this.feedContainer.innerHTML = '';
        document.getElementById('jarvis-count').textContent = '0';
    }

    setStatus(state, text) {
        const dot = document.querySelector('.jarvis-status-dot');
        const label = document.getElementById('jarvis-status-text');
        if (dot) {
            dot.className = `jarvis-status-dot ${state}`;
        }
        if (label) {
            label.textContent = text;
        }
    }

    destroy() {
        if (this.eventSource) {
            this.eventSource.close();
        }
    }
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.jarvisFeed = new JarvisActionFeed();
    window.jarvisFeed.init();
});
