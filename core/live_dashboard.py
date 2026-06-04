"""
NEXUS AI — Live Action Dashboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Real-time web dashboard to WATCH NEXUS controlling the PC.

Shows:
  • Live thought stream — what NEXUS is thinking each cycle
  • Action feed — every physical action (mouse, keyboard, commands)
  • System vitals — CPU, RAM, disk
  • Control panel — start/stop/pause, adjust interval

Uses Server-Sent Events (SSE) for zero-latency real-time updates.
"""

import threading
import json
import time
import queue
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.logger import get_logger

logger = get_logger("live_dashboard")

# ── The HTML is inlined to keep deployment simple ──
DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NEXUS — Live PC Control</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;600&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#06060c;--surface:#0d0d18;--surface2:#14142a;--border:#1a1a3e;
  --accent:#00d4ff;--accent2:#7b61ff;--green:#00ff88;--red:#ff4466;
  --orange:#ff8844;--yellow:#ffcc00;--text:#e8e8f0;--muted:#6e6e8a;
  --glass:rgba(13,13,24,0.7);
}
body{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;
  overflow-x:hidden;min-height:100vh}

/* ── Header ── */
.header{display:flex;align-items:center;justify-content:space-between;
  padding:16px 28px;border-bottom:1px solid var(--border);
  background:linear-gradient(180deg,rgba(0,212,255,0.03) 0%,transparent 100%)}
.header .logo{display:flex;align-items:center;gap:14px}
.header .logo h1{font-size:22px;font-weight:700;
  background:linear-gradient(135deg,var(--accent),var(--accent2));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent}
.header .logo .pulse{width:12px;height:12px;border-radius:50%;
  background:var(--green);box-shadow:0 0 12px var(--green);
  animation:pulse 2s infinite}
.header .logo .pulse.paused{background:var(--orange);box-shadow:0 0 12px var(--orange)}
.header .logo .pulse.stopped{background:var(--red);box-shadow:0 0 12px var(--red);animation:none}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:0.5;transform:scale(0.8)}}
.header .status{font-family:'JetBrains Mono',monospace;font-size:13px;color:var(--muted)}
.header .controls{display:flex;gap:10px}
.header .controls button{padding:8px 18px;border:1px solid var(--border);border-radius:8px;
  background:var(--surface2);color:var(--text);font-size:13px;cursor:pointer;
  transition:all 0.2s;font-family:'Inter',sans-serif;font-weight:500}
.header .controls button:hover{border-color:var(--accent);
  box-shadow:0 0 15px rgba(0,212,255,0.15)}
.header .controls button.danger:hover{border-color:var(--red);
  box-shadow:0 0 15px rgba(255,68,102,0.15)}
.header .controls button.active{background:var(--accent);color:#000;border-color:var(--accent)}

/* ── Main Layout ── */
.main{display:grid;grid-template-columns:1fr 1.4fr 1fr;gap:0;height:calc(100vh - 65px)}

/* ── Panels ── */
.panel{border-right:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden}
.panel:last-child{border-right:none}
.panel-header{padding:14px 20px;border-bottom:1px solid var(--border);
  background:var(--surface);display:flex;align-items:center;justify-content:space-between}
.panel-header h2{font-size:14px;font-weight:600;color:var(--accent);text-transform:uppercase;
  letter-spacing:1.5px}
.panel-header .badge{font-family:'JetBrains Mono',monospace;font-size:11px;
  padding:3px 8px;border-radius:4px;background:var(--surface2);color:var(--muted)}
.panel-content{flex:1;overflow-y:auto;padding:12px;scrollbar-width:thin;
  scrollbar-color:var(--border) transparent}
.panel-content::-webkit-scrollbar{width:5px}
.panel-content::-webkit-scrollbar-track{background:transparent}
.panel-content::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}

/* ── Thought Stream ── */
.thought-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;
  padding:14px;margin-bottom:10px;animation:slideIn 0.3s ease;position:relative;overflow:hidden}
.thought-card::before{content:'';position:absolute;top:0;left:0;width:3px;height:100%;
  background:linear-gradient(180deg,var(--accent2),var(--accent))}
.thought-card .cycle{font-family:'JetBrains Mono',monospace;font-size:11px;
  color:var(--accent);margin-bottom:6px}
.thought-card .text{font-size:13px;line-height:1.6;color:var(--text);opacity:0.9}
.thought-card .time{font-size:11px;color:var(--muted);margin-top:8px}

/* ── Action Feed ── */
.action-card{background:var(--surface);border:1px solid var(--border);border-radius:10px;
  padding:14px;margin-bottom:8px;animation:slideIn 0.3s ease;
  transition:border-color 0.3s}
.action-card:hover{border-color:var(--accent)}
.action-card.success{border-left:3px solid var(--green)}
.action-card.fail{border-left:3px solid var(--red)}
.action-card .action-header{display:flex;align-items:center;gap:8px;margin-bottom:6px}
.action-card .action-icon{font-size:16px}
.action-card .action-type{font-family:'JetBrains Mono',monospace;font-size:12px;
  font-weight:600;text-transform:uppercase;letter-spacing:0.5px}
.action-card .action-type.mouse{color:var(--accent)}
.action-card .action-type.keyboard{color:var(--accent2)}
.action-card .action-type.system{color:var(--orange)}
.action-card .action-type.file{color:var(--green)}
.action-card .action-type.screen{color:var(--yellow)}
.action-card .reason{font-size:12px;color:var(--muted);margin-bottom:4px;font-style:italic}
.action-card .result{font-family:'JetBrains Mono',monospace;font-size:12px;
  background:var(--bg);padding:8px 10px;border-radius:6px;margin-top:6px;
  line-height:1.5;word-break:break-all;max-height:80px;overflow-y:auto}
.action-card .meta{display:flex;justify-content:space-between;align-items:center;
  margin-top:8px;font-size:11px;color:var(--muted)}
.action-card .status-badge{padding:2px 8px;border-radius:4px;font-size:10px;font-weight:600}
.action-card .status-badge.ok{background:rgba(0,255,136,0.15);color:var(--green)}
.action-card .status-badge.err{background:rgba(255,68,102,0.15);color:var(--red)}

/* ── Vitals ── */
.vital-gauge{background:var(--surface);border:1px solid var(--border);border-radius:10px;
  padding:14px;margin-bottom:10px}
.vital-gauge .label{font-size:12px;color:var(--muted);margin-bottom:6px;
  display:flex;justify-content:space-between}
.vital-gauge .label span{font-family:'JetBrains Mono',monospace;font-weight:600;color:var(--text)}
.vital-bar{height:6px;background:var(--bg);border-radius:3px;overflow:hidden}
.vital-bar .fill{height:100%;border-radius:3px;transition:width 1s ease,background 1s ease}
.vital-bar .fill.ok{background:linear-gradient(90deg,var(--green),#00cc66)}
.vital-bar .fill.warn{background:linear-gradient(90deg,var(--orange),var(--yellow))}
.vital-bar .fill.danger{background:linear-gradient(90deg,var(--red),var(--orange))}

.stats-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:14px}
.stat-box{background:var(--surface);border:1px solid var(--border);border-radius:8px;
  padding:10px;text-align:center}
.stat-box .num{font-family:'JetBrains Mono',monospace;font-size:20px;font-weight:700;
  color:var(--accent)}
.stat-box .lbl{font-size:11px;color:var(--muted);margin-top:2px}

/* ── Animations ── */
@keyframes slideIn{from{opacity:0;transform:translateY(-10px)}to{opacity:1;transform:translateY(0)}}
@keyframes glow{0%,100%{box-shadow:0 0 5px rgba(0,212,255,0.1)}
  50%{box-shadow:0 0 20px rgba(0,212,255,0.3)}}

/* ── Connection Status ── */
.connection-bar{position:fixed;bottom:0;left:0;right:0;height:3px;z-index:100}
.connection-bar.connected{background:var(--green)}
.connection-bar.disconnected{background:var(--red);animation:pulse 1s infinite}

/* ── Empty State ── */
.empty-state{text-align:center;padding:40px 20px;color:var(--muted)}
.empty-state .icon{font-size:40px;margin-bottom:12px;opacity:0.5}
.empty-state p{font-size:13px;line-height:1.6}
</style>
</head>
<body>

<div class="header">
  <div class="logo">
    <div class="pulse" id="statusPulse"></div>
    <h1>NEXUS — Live PC Control</h1>
  </div>
  <div class="status" id="statusText">Connecting...</div>
  <div class="controls">
    <button onclick="sendControl('resume')" id="btnResume">▶ Resume</button>
    <button onclick="sendControl('pause')" id="btnPause">⏸ Pause</button>
    <button onclick="sendControl('stop')" class="danger" id="btnStop">⏹ Stop</button>
    <button onclick="clearFeed()" id="btnClear">🗑 Clear</button>
  </div>
</div>

<div class="main">
  <!-- Left: Thought Stream -->
  <div class="panel">
    <div class="panel-header">
      <h2>🧠 Thought Stream</h2>
      <span class="badge" id="thoughtCount">0</span>
    </div>
    <div class="panel-content" id="thoughtFeed">
      <div class="empty-state">
        <div class="icon">🧠</div>
        <p>Waiting for NEXUS to start thinking...<br>Thoughts will appear here in real-time.</p>
      </div>
    </div>
  </div>

  <!-- Center: Action Feed -->
  <div class="panel">
    <div class="panel-header">
      <h2>⚡ Action Feed</h2>
      <span class="badge" id="actionCount">0</span>
    </div>
    <div class="panel-content" id="actionFeed">
      <div class="empty-state">
        <div class="icon">🖱️</div>
        <p>Waiting for NEXUS to act...<br>Mouse movements, clicks, typing, and commands will appear here.</p>
      </div>
    </div>
  </div>

  <!-- Right: System Vitals -->
  <div class="panel">
    <div class="panel-header">
      <h2>💻 System & Stats</h2>
      <span class="badge" id="cycleCount">Cycle 0</span>
    </div>
    <div class="panel-content" id="vitalsFeed">
      <div class="vital-gauge">
        <div class="label">CPU <span id="cpuVal">0%</span></div>
        <div class="vital-bar"><div class="fill ok" id="cpuBar" style="width:0%"></div></div>
      </div>
      <div class="vital-gauge">
        <div class="label">RAM <span id="ramVal">0%</span></div>
        <div class="vital-bar"><div class="fill ok" id="ramBar" style="width:0%"></div></div>
      </div>
      <div class="vital-gauge">
        <div class="label">Disk <span id="diskVal">0%</span></div>
        <div class="vital-bar"><div class="fill ok" id="diskBar" style="width:0%"></div></div>
      </div>

      <div class="stats-grid">
        <div class="stat-box"><div class="num" id="statCycles">0</div><div class="lbl">Cycles</div></div>
        <div class="stat-box"><div class="num" id="statActions">0</div><div class="lbl">Actions</div></div>
        <div class="stat-box"><div class="num" id="statGUI">0</div><div class="lbl">GUI Actions</div></div>
        <div class="stat-box"><div class="num" id="statSuccess">0</div><div class="lbl">Success Rate</div></div>
      </div>
    </div>
  </div>
</div>

<div class="connection-bar disconnected" id="connectionBar"></div>

<script>
const API = '';
let thoughtCount = 0, actionCount = 0;
let autoScroll = true;

const ICONS = {
  move_mouse:'🖱️',click:'🖱️',double_click:'🖱️',right_click:'🖱️',scroll:'🔄',drag:'↕️',
  type_text:'⌨️',press_key:'⌨️',hotkey:'⌨️',
  shell:'💻',powershell:'💻',python:'🐍',
  open_app:'🚀',open_url:'🌐',
  read_file:'📖',write_file:'📝',list_dir:'📂',delete_file:'🗑️',move_file:'📦',
  screenshot:'📸',notify:'🔔',set_wallpaper:'🖼️',
  think:'💭',wait:'⏳',system_info:'📊'
};
const TYPE_CLASS = {
  move_mouse:'mouse',click:'mouse',double_click:'mouse',right_click:'mouse',scroll:'mouse',drag:'mouse',
  type_text:'keyboard',press_key:'keyboard',hotkey:'keyboard',
  screenshot:'screen',
  shell:'system',powershell:'system',python:'system',open_app:'system',open_url:'system',
  read_file:'file',write_file:'file',list_dir:'file',delete_file:'file',move_file:'file',
};

function connectSSE() {
  const es = new EventSource(API + '/api/live/events');
  es.onopen = () => {
    document.getElementById('connectionBar').className = 'connection-bar connected';
    document.getElementById('statusText').textContent = 'Connected — streaming live events';
  };
  es.onmessage = (e) => {
    try { handleEvent(JSON.parse(e.data)); } catch(err) { console.error(err); }
  };
  es.onerror = () => {
    document.getElementById('connectionBar').className = 'connection-bar disconnected';
    document.getElementById('statusText').textContent = 'Disconnected — reconnecting...';
  };
}

function handleEvent(ev) {
  switch(ev.type) {
    case 'thought': addThought(ev); break;
    case 'action_start': addActionStart(ev); break;
    case 'action_result': updateActionResult(ev); break;
    case 'cycle_start': onCycleStart(ev); break;
    case 'cycle_end': onCycleEnd(ev); break;
    case 'vitals': updateVitals(ev); break;
    case 'stats': updateStats(ev); break;
    case 'agent_started': setStatus('running'); break;
    case 'agent_stopped': setStatus('stopped'); break;
    case 'agent_paused': setStatus('paused'); break;
    case 'agent_resumed': setStatus('running'); break;
  }
}

function addThought(ev) {
  const feed = document.getElementById('thoughtFeed');
  if(thoughtCount === 0) feed.innerHTML = '';
  thoughtCount++;
  document.getElementById('thoughtCount').textContent = thoughtCount;
  const card = document.createElement('div');
  card.className = 'thought-card';
  card.innerHTML = `
    <div class="cycle">Cycle ${ev.cycle || '?'}</div>
    <div class="text">${escHtml(ev.thought || '')}</div>
    <div class="time">${new Date(ev.timestamp).toLocaleTimeString()}</div>`;
  feed.insertBefore(card, feed.firstChild);
  if(feed.children.length > 100) feed.removeChild(feed.lastChild);
}

function addActionStart(ev) {
  const feed = document.getElementById('actionFeed');
  if(actionCount === 0) feed.innerHTML = '';
  actionCount++;
  document.getElementById('actionCount').textContent = actionCount;
  const icon = ICONS[ev.action_type] || '❓';
  const cls = TYPE_CLASS[ev.action_type] || 'system';
  const card = document.createElement('div');
  card.className = 'action-card';
  card.id = `action-${ev.cycle}-${ev.index}`;
  card.innerHTML = `
    <div class="action-header">
      <span class="action-icon">${icon}</span>
      <span class="action-type ${cls}">${ev.action_type}</span>
      <span style="flex:1"></span>
      <span class="status-badge" id="badge-${ev.cycle}-${ev.index}">⏳ Running</span>
    </div>
    <div class="reason">${escHtml(ev.reason || '')}</div>
    <div class="result" id="result-${ev.cycle}-${ev.index}">Executing...</div>
    <div class="meta">
      <span>${new Date(ev.timestamp).toLocaleTimeString()}</span>
      <span>Action ${ev.index}/${ev.total}</span>
    </div>`;
  feed.insertBefore(card, feed.firstChild);
  if(feed.children.length > 200) feed.removeChild(feed.lastChild);
}

function updateActionResult(ev) {
  const card = document.getElementById(`action-${ev.cycle}-${ev.index}`);
  if(!card) return;
  card.className = `action-card ${ev.success ? 'success' : 'fail'}`;
  const badge = document.getElementById(`badge-${ev.cycle}-${ev.index}`);
  if(badge) {
    badge.className = `status-badge ${ev.success ? 'ok' : 'err'}`;
    badge.textContent = ev.success ? '✓ Done' : '✗ Failed';
  }
  const result = document.getElementById(`result-${ev.cycle}-${ev.index}`);
  if(result) result.textContent = ev.result || '(no output)';
}

function onCycleStart(ev) {
  document.getElementById('cycleCount').textContent = `Cycle ${ev.cycle}`;
}
function onCycleEnd(ev) {
  document.getElementById('statCycles').textContent = ev.cycle;
}

function updateVitals(ev) {
  setGauge('cpu', ev.cpu || 0);
  setGauge('ram', ev.ram || 0);
  setGauge('disk', ev.disk || 0);
}

function setGauge(id, val) {
  document.getElementById(`${id}Val`).textContent = val.toFixed(0) + '%';
  const bar = document.getElementById(`${id}Bar`);
  bar.style.width = val + '%';
  bar.className = `fill ${val > 85 ? 'danger' : val > 60 ? 'warn' : 'ok'}`;
}

function updateStats(ev) {
  document.getElementById('statCycles').textContent = ev.cycles || 0;
  document.getElementById('statActions').textContent = ev.actions || 0;
  document.getElementById('statGUI').textContent = ev.gui_actions || 0;
  const total = (ev.successful || 0) + (ev.failed || 0);
  const rate = total > 0 ? ((ev.successful || 0) / total * 100).toFixed(0) + '%' : '-';
  document.getElementById('statSuccess').textContent = rate;
}

function setStatus(state) {
  const pulse = document.getElementById('statusPulse');
  pulse.className = `pulse ${state === 'running' ? '' : state}`;
  document.getElementById('statusText').textContent =
    state === 'running' ? 'NEXUS is actively controlling this PC' :
    state === 'paused' ? 'Paused — NEXUS is waiting' :
    'Stopped';
}

function sendControl(action) {
  fetch(API + '/api/live/control', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({action})
  }).then(r => r.json()).then(d => console.log('Control:', d));
}

function clearFeed() {
  document.getElementById('thoughtFeed').innerHTML = '<div class="empty-state"><div class="icon">🧠</div><p>Cleared.</p></div>';
  document.getElementById('actionFeed').innerHTML = '<div class="empty-state"><div class="icon">🖱️</div><p>Cleared.</p></div>';
  thoughtCount = 0; actionCount = 0;
  document.getElementById('thoughtCount').textContent = '0';
  document.getElementById('actionCount').textContent = '0';
}

function escHtml(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

// ── Poll status ──
function pollStatus() {
  fetch(API + '/api/live/status').then(r => r.json()).then(d => {
    if(d.vitals) updateVitals(d.vitals);
    if(d.stats) updateStats(d.stats);
    setStatus(d.state || 'stopped');
  }).catch(() => {});
}
setInterval(pollStatus, 5000);

connectSSE();
pollStatus();
</script>
</body>
</html>"""


class LiveDashboard:
    """
    Flask-based live dashboard server for watching NEXUS control the PC.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._app = None
        self._thread = None
        self._running = False
        self._port = 5050
        self._event_queues = []  # List of queues for SSE clients
        self._event_lock = threading.Lock()
        self._pc_agent = None
        self._computer_body = None

    def start(self, port: int = 5050):
        """Start the dashboard server."""
        if self._running:
            return

        self._port = port
        self._running = True

        # Load dependencies
        self._load_systems()

        # Hook into PC Control Agent events
        self._hook_agent()

        # Start Flask in background
        self._thread = threading.Thread(
            target=self._run_server,
            daemon=True,
            name="LiveDashboard"
        )
        self._thread.start()

        logger.info(f"🌐 Live Dashboard started at http://localhost:{port}")
        print(f"\n  🌐 NEXUS Live Dashboard: http://localhost:{port}")
        print(f"     Open in browser to watch NEXUS control the PC in real-time\n")

    def stop(self):
        self._running = False

    def _load_systems(self):
        try:
            from core.pc_control_agent import pc_control_agent
            self._pc_agent = pc_control_agent
        except Exception as e:
            logger.debug(f"Could not load PC agent: {e}")

        try:
            from body.computer_body import computer_body
            self._computer_body = computer_body
        except Exception as e:
            logger.debug(f"Could not load computer body: {e}")

    def _hook_agent(self):
        """Register as event listener on the PC Control Agent."""
        if self._pc_agent:
            self._pc_agent.add_event_listener(self._on_agent_event)
            logger.info("Dashboard hooked into PC Control Agent events")

            # Also start a vitals broadcaster
            threading.Thread(target=self._vitals_loop, daemon=True).start()

    def _on_agent_event(self, event: Dict[str, Any]):
        """Receive event from PC Control Agent and broadcast to SSE clients."""
        self._broadcast(event)

    def _vitals_loop(self):
        """Periodically broadcast system vitals."""
        while self._running:
            try:
                if self._computer_body:
                    v = self._computer_body.get_vitals()
                    self._broadcast({
                        "type": "vitals",
                        "cpu": v.cpu_percent,
                        "ram": v.ram_percent,
                        "disk": v.disk_percent,
                        "timestamp": datetime.now().isoformat()
                    })
                if self._pc_agent:
                    stats = self._pc_agent.get_stats()
                    self._broadcast({
                        "type": "stats",
                        "cycles": stats.get("cycle_count", 0),
                        "actions": stats.get("total_actions", 0),
                        "gui_actions": stats.get("gui_actions", 0),
                        "successful": stats.get("successful_actions", 0),
                        "failed": stats.get("failed_actions", 0),
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception:
                pass
            time.sleep(3.0)

    def _broadcast(self, event: Dict[str, Any]):
        """Send event to all connected SSE clients."""
        data = json.dumps(event, default=str)
        with self._event_lock:
            dead = []
            for q in self._event_queues:
                try:
                    q.put_nowait(data)
                except queue.Full:
                    dead.append(q)
            for q in dead:
                self._event_queues.remove(q)

    def _run_server(self):
        """Run Flask server."""
        try:
            from flask import Flask, Response, request, jsonify
        except ImportError:
            logger.error("Flask not installed — dashboard unavailable")
            return

        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'nexus-live-dashboard'

        @app.route('/')
        def index():
            return Response(DASHBOARD_HTML, mimetype='text/html')

        @app.route('/api/live/events')
        def sse():
            q = queue.Queue(maxsize=200)
            with self._event_lock:
                self._event_queues.append(q)

            def stream():
                try:
                    while self._running:
                        try:
                            data = q.get(timeout=30)
                            yield f"data: {data}\n\n"
                        except queue.Empty:
                            yield f"data: {json.dumps({'type':'ping'})}\n\n"
                finally:
                    with self._event_lock:
                        if q in self._event_queues:
                            self._event_queues.remove(q)

            return Response(stream(), mimetype='text/event-stream',
                          headers={'Cache-Control': 'no-cache',
                                   'X-Accel-Buffering': 'no'})

        @app.route('/api/live/status')
        def status():
            state = "stopped"
            vitals_data = {}
            stats_data = {}

            if self._pc_agent:
                s = self._pc_agent.get_stats()
                if s.get("running"):
                    state = "paused" if s.get("paused") else "running"
                stats_data = {
                    "cycles": s.get("cycle_count", 0),
                    "actions": s.get("total_actions", 0),
                    "gui_actions": s.get("gui_actions", 0),
                    "successful": s.get("successful_actions", 0),
                    "failed": s.get("failed_actions", 0),
                }

            if self._computer_body:
                try:
                    v = self._computer_body.get_vitals()
                    vitals_data = {"cpu": v.cpu_percent, "ram": v.ram_percent, "disk": v.disk_percent}
                except Exception:
                    pass

            return jsonify({"state": state, "vitals": vitals_data, "stats": stats_data})

        @app.route('/api/live/control', methods=['POST'])
        def control():
            data = request.get_json() or {}
            action = data.get("action", "")
            if not self._pc_agent:
                return jsonify({"error": "PC agent not available"})
            if action == "pause":
                self._pc_agent.pause("Dashboard control")
                return jsonify({"ok": True, "state": "paused"})
            elif action == "resume":
                self._pc_agent.resume()
                return jsonify({"ok": True, "state": "running"})
            elif action == "stop":
                self._pc_agent.stop()
                return jsonify({"ok": True, "state": "stopped"})
            elif action == "start":
                self._pc_agent.start()
                return jsonify({"ok": True, "state": "running"})
            return jsonify({"error": f"Unknown action: {action}"})

        @app.route('/api/live/history')
        def history():
            if self._pc_agent:
                return jsonify(self._pc_agent.get_action_history(50))
            return jsonify([])

        # Suppress Flask logs
        import logging as _logging
        _logging.getLogger('werkzeug').setLevel(_logging.WARNING)

        try:
            app.run(host='0.0.0.0', port=self._port, threaded=True, use_reloader=False)
        except Exception as e:
            logger.error(f"Dashboard server error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

live_dashboard = LiveDashboard()
