"""
NEXUS AI - Web Server and Interface
Phase 12: Multi-User Auth + Per-User Chat Isolation

Features:
- User signup/login with hashed passwords (SQLite)
- Per-user chat context isolation (no mixing between users)
- Token-based authentication on all chat endpoints
- Persistent chat history per user
- Async chat with poll pattern to prevent 503 timeouts
"""
import os
import sys
import logging
import threading
import time
import uuid
import secrets
import traceback
import psutil
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_from_directory

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import NEXUS_CONFIG
from core.nexus_brain import NexusBrain
from core.user_manager import UserManager, user_manager
from core.user_context import UserContextManager, user_context_manager
from utils.logger import get_logger

logger = get_logger("web_server")

# Catch ANY unhandled exception in ANY thread — print to terminal
def _thread_exception_handler(args):
    print(f"\n[FATAL THREAD CRASH] Thread '{args.thread.name}' died!", flush=True)
    print(f"  Exception: {args.exc_type.__name__}: {args.exc_value}", flush=True)
    traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback)

threading.excepthook = _thread_exception_handler


class NexusWeb:
    """
    Flask-based web server for NEXUS.
    Mirrors the functionality of the desktop GUI.
    
    Phase 12: Multi-user auth with per-user chat isolation.
    Each web user gets their own conversation context and chat history.
    """
    
    def __init__(self, brain: NexusBrain):
        self.brain = brain
        
        # Configure Flask
        template_dir = Path(__file__).parent.parent / "ui" / "web" / "templates"
        static_dir = Path(__file__).parent.parent / "ui" / "web" / "static"
        
        self.app = Flask(
            __name__,
            template_folder=str(template_dir),
            static_folder=str(static_dir)
        )
        
        # Disable static file caching so browser always gets latest JS/CSS
        self.app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
        
        self.port = NEXUS_CONFIG.web.port
        self.public_url = None
        self.server_thread = None
        
        # Async chat task queue: task_id -> {status, response, emotion, ...}
        self._chat_tasks = {}
        self._chat_lock = threading.Lock()
        self._cf_process = None  # Cloudflare tunnel subprocess
        
        # Auth session tokens: token -> {user_id, username, display_name, created_at}
        self._auth_sessions = {}
        self._auth_lock = threading.Lock()
        
        # Register routes
        self._register_routes()
        
        # Suppress Flask logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

    # ══════════════════════════════════════════════════════════════════════════
    # AUTH HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    def _create_session_token(self, user: dict) -> str:
        """Create a session token for an authenticated user."""
        token = secrets.token_urlsafe(32)
        with self._auth_lock:
            self._auth_sessions[token] = {
                "user_id": user["id"],
                "username": user["username"],
                "display_name": user.get("display_name", user["username"]),
                "created_at": time.time(),
            }
        return token

    def _get_current_user(self) -> dict:
        """
        Extract current user from the Authorization header.
        Returns user session dict or None.
        """
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header[7:]
        with self._auth_lock:
            return self._auth_sessions.get(token)

    def _require_auth(self):
        """
        Get current user or abort with 401.
        Returns user session dict.
        """
        user = self._get_current_user()
        if not user:
            return None
        return user

    # ══════════════════════════════════════════════════════════════════════════
    # ROUTES
    # ══════════════════════════════════════════════════════════════════════════

    def _register_routes(self):
        """Register Flask routes"""
        
        @self.app.after_request
        def after_request(response):
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
            # Prevent caching of API responses and static files
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            return response
        
        @self.app.route("/api/health")
        def health():
            return jsonify({"status": "ok"})
        
        @self.app.route("/")
        def index():
            return render_template("index.html")

        # ── AUTH ROUTES ──

        @self.app.route("/api/auth/signup", methods=["POST"])
        def auth_signup():
            """Create a new user account."""
            try:
                data = request.json
                if not data:
                    return jsonify({"error": "No JSON data"}), 400
                
                username = (data.get("username") or "").strip()
                password = data.get("password", "")
                display_name = (data.get("display_name") or "").strip()

                if not username or not password:
                    return jsonify({"error": "Username and password required"}), 400

                user = user_manager.create_user(username, password, display_name)
                token = self._create_session_token(user)

                return jsonify({
                    "status": "ok",
                    "token": token,
                    "user": user,
                })
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                logger.error(f"Signup error: {e}")
                return jsonify({"error": "Server error"}), 500

        @self.app.route("/api/auth/login", methods=["POST"])
        def auth_login():
            """Authenticate and get session token."""
            try:
                data = request.json
                if not data:
                    return jsonify({"error": "No JSON data"}), 400

                username = (data.get("username") or "").strip()
                password = data.get("password", "")

                if not username or not password:
                    return jsonify({"error": "Username and password required"}), 400

                user = user_manager.authenticate(username, password)
                if not user:
                    return jsonify({"error": "Invalid username or password"}), 401

                token = self._create_session_token(user)

                # Load chat history into user context
                ctx = user_context_manager.get_context(user["id"], user["username"])
                history = user_manager.get_chat_history(user["id"], limit=50)
                ctx.load_history(history)

                return jsonify({
                    "status": "ok",
                    "token": token,
                    "user": user,
                })
            except Exception as e:
                logger.error(f"Login error: {e}")
                return jsonify({"error": "Server error"}), 500

        @self.app.route("/api/auth/me")
        def auth_me():
            """Get current user info from token."""
            user = self._get_current_user()
            if not user:
                return jsonify({"error": "Not authenticated"}), 401
            return jsonify({
                "status": "ok",
                "user": {
                    "id": user["user_id"],
                    "username": user["username"],
                    "display_name": user["display_name"],
                },
            })

        @self.app.route("/api/auth/logout", methods=["POST"])
        def auth_logout():
            """Invalidate session token."""
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                with self._auth_lock:
                    self._auth_sessions.pop(token, None)
            return jsonify({"status": "ok"})

        # ── STATS (no auth required — dashboard is public) ──

        @self.app.route("/api/stats")
        def get_stats():
            """Return system stats for dashboard updating"""
            if not self.brain:
                return jsonify({"error": "Brain not connected"}), 500
                
            try:
                stats = self.brain.get_stats()
                
                # ── Emotion (direct from brain stats) ──
                emotion = stats.get("emotion", {})
                
                # ── Body/System: nested under stats["body"]["vitals"] ──
                body_raw = stats.get("body", {})
                vitals = body_raw.get("vitals", {}) if isinstance(body_raw, dict) else {}
                
                # ── Memory: key is "memory_stats" in brain.get_stats() ──
                memory_raw = stats.get("memory_stats", {})
                
                # ── Learning: key is "learning" in brain.get_stats() ──
                learning_raw = stats.get("learning", {})
                
                # ── Evolution: key is "self_evolution" in brain.get_stats() ──
                evolution_raw = stats.get("self_evolution", {})
                
                # ── Personality: key is "personality" ──
                personality_raw = stats.get("personality", {})
                
                # Get inner voice / thoughts
                inner_voice_text = ""
                inner_voice_narrative = ""
                recent_thoughts = []
                try:
                    if hasattr(self.brain, '_inner_voice') and self.brain._inner_voice:
                        inner_voice_text = getattr(self.brain._inner_voice, 'current_thought', '')
                        recent_thoughts = getattr(self.brain._inner_voice, 'recent_thoughts', [])
                        if hasattr(self.brain._inner_voice, 'get_narrative'):
                            inner_voice_narrative = self.brain._inner_voice.get_narrative(5) or ''
                except:
                    pass
                
                # Get personality traits
                traits = {}
                personality_desc = ""
                try:
                    if hasattr(self.brain, '_personality_engine') and self.brain._personality_engine:
                        traits = getattr(self.brain._personality_engine, 'traits', {})
                    if not traits and personality_raw:
                        traits = personality_raw.get("traits", {})
                    if not traits:
                        traits = NEXUS_CONFIG.personality.traits
                    personality_desc = personality_raw.get("description", "")
                    if not personality_desc and hasattr(self.brain, '_personality_core') and self.brain._personality_core:
                        personality_desc = self.brain._personality_core.get_personality_description()
                except:
                    traits = NEXUS_CONFIG.personality.traits
                
                # Get emotion details
                all_emotions = {}
                mood = "neutral"
                valence = 0.0
                arousal = 0.5
                expression_words = []
                emotion_desc = ""
                try:
                    es = self.brain._state.emotional
                    mood = getattr(es, 'mood', 'neutral')
                    if hasattr(mood, 'name'):
                        mood = mood.name.lower()
                    elif hasattr(mood, 'value'):
                        mood = str(mood.value)
                    all_emotions = getattr(es, 'secondary_emotions', {})
                    if hasattr(all_emotions, '__dict__'):
                        all_emotions = {k: v for k, v in all_emotions.__dict__.items() if isinstance(v, (int, float))}
                    valence = getattr(es, 'valence', 0.0)
                    arousal = getattr(es, 'arousal', 0.5)
                except:
                    pass
                try:
                    if hasattr(self.brain, '_emotion_engine') and self.brain._emotion_engine:
                        expression_words = self.brain._emotion_engine.get_expression_words() or []
                        emotion_desc = self.brain._emotion_engine.describe_emotional_state() or ""
                except:
                    pass
                
                # Get consciousness awareness
                awareness = 0.0
                consciousness_thoughts = []
                try:
                    c_state = self.brain._state.consciousness
                    awareness = getattr(c_state, 'self_awareness_score', 0.0)
                    consciousness_thoughts = getattr(c_state, 'current_thoughts', [])[-5:]
                except:
                    pass
                
                # Get will/desires data
                will_raw = stats.get("will", {})
                will_data = {
                    "boredom": stats.get("boredom_level", 0),
                    "curiosity": stats.get("curiosity_level", 0),
                    "drive": 0.5,
                    "goals": [],
                    "description": "",
                }
                if isinstance(will_raw, dict):
                    goals_data = will_raw.get("current_goals", [])
                    if isinstance(goals_data, list):
                        will_data["goals"] = [
                            g.get("description", str(g))[:60]
                            if isinstance(g, dict) else str(g)[:60]
                            for g in goals_data[:5]
                        ]
                    will_data["drive"] = will_raw.get("drive_level", 0.5)
                    will_data["description"] = will_raw.get("description", "")
                try:
                    if hasattr(self.brain, '_will_system') and self.brain._will_system:
                        will_data["description"] = self.brain._will_system.describe_will()
                except:
                    pass
                
                # Get mood data (stability, history)
                mood_raw = stats.get("mood", {})
                mood_data = {
                    "current": "NEUTRAL",
                    "stability": 0.5,
                }
                if isinstance(mood_raw, dict):
                    mood_data["current"] = mood_raw.get("current_mood", "NEUTRAL")
                    mood_data["stability"] = mood_raw.get("stability", 0.5)
                elif isinstance(mood_raw, str):
                    mood_data["current"] = mood_raw
                
                # Get companion chat data
                companion_data = {
                    "is_chatting": False,
                    "companion_name": "ARIA",
                    "status": "Idle — waiting for boredom trigger",
                    "total_conversations": 0,
                    "recent": [],
                }
                try:
                    comp = getattr(self.brain, '_companion_chat', None)
                    if comp:
                        companion_data["is_chatting"] = getattr(comp, 'is_chatting', False)
                        companion_data["companion_name"] = getattr(comp, 'companion_name', 'ARIA')
                        c_stats = comp.get_stats()
                        companion_data["total_conversations"] = c_stats.get('total_conversations', 0)
                        if companion_data["is_chatting"]:
                            companion_data["status"] = f"Chatting with {companion_data['companion_name']}..."
                        elif will_data["boredom"] > 0.5:
                            companion_data["status"] = f"Boredom rising ({will_data['boredom']:.0%}) — chat may start soon"
                        recent = comp.get_recent_conversations(limit=3)
                        if recent:
                            for conv in recent:
                                conv_entry = {
                                    "trigger": conv.get('trigger', 'boredom'),
                                    "started_at": conv.get('started_at', '')[:16],
                                    "exchanges": [],
                                }
                                for ex in conv.get('exchanges', [])[:6]:
                                    conv_entry["exchanges"].append({
                                        "speaker": ex.get('speaker', '?'),
                                        "content": ex.get('content', '')[:150],
                                    })
                                companion_data["recent"].append(conv_entry)
                except:
                    pass
                
                # ── Deep system data (per-core, memory breakdown, processes, I/O) ──
                sys_deep = {"cpu_per_core": [], "mem_breakdown": {}, "net_io": {}, "disk_io": {}, "top_processes": [], "nexus_resources": {}}
                try:
                    sys_deep["cpu_per_core"] = psutil.cpu_percent(percpu=True)
                    vm = psutil.virtual_memory()
                    sys_deep["mem_breakdown"] = {
                        "total_gb": round(vm.total / (1024**3), 1),
                        "used_gb": round(vm.used / (1024**3), 1),
                        "cached_gb": round(getattr(vm, 'cached', 0) / (1024**3), 1),
                        "available_gb": round(vm.available / (1024**3), 1),
                        "used_pct": vm.percent,
                    }
                    nio = psutil.net_io_counters()
                    sys_deep["net_io"] = {"bytes_sent": nio.bytes_sent, "bytes_recv": nio.bytes_recv}
                    dio = psutil.disk_io_counters()
                    if dio:
                        sys_deep["disk_io"] = {"read_bytes": dio.read_bytes, "write_bytes": dio.write_bytes}
                    # Top 10 processes
                    procs = []
                    for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                        try:
                            info = p.info
                            if info['cpu_percent'] is not None and info['cpu_percent'] > 0:
                                procs.append(info)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    procs.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
                    sys_deep["top_processes"] = procs[:10]
                    # NEXUS brain resources
                    bp = psutil.Process(os.getpid())
                    bm = bp.memory_info()
                    sys_deep["nexus_resources"] = {
                        "memory_mb": round(bm.rss / (1024**2), 1),
                        "threads": bp.num_threads(),
                        "cpu_pct": bp.cpu_percent(),
                    }
                except Exception:
                    pass

                # ── Deep evolution data ──
                evo_deep = {"pipeline": [], "proposals": [], "history": [], "code_health": {}}
                try:
                    evo_eng = getattr(self.brain, '_self_evolution', None)
                    if evo_eng:
                        # Pipeline steps
                        pipeline_names = ["Analyze", "Propose", "Review", "Implement", "Test", "Deploy", "Monitor"]
                        current_step = evolution_raw.get("current_step", 0)
                        evo_deep["pipeline"] = [{"name": n, "status": "done" if i < current_step else ("active" if i == current_step else "pending")} for i, n in enumerate(pipeline_names)]
                        # Proposals
                        if hasattr(evo_eng, 'get_proposals'):
                            raw_proposals = evo_eng.get_proposals() or []
                            for p in raw_proposals[:20]:
                                if isinstance(p, dict):
                                    evo_deep["proposals"].append({"name": p.get("name", p.get("title", "?")), "priority": p.get("priority", "medium"), "status": p.get("status", "pending"), "date": str(p.get("created", p.get("date", "")))[:16]})
                        elif hasattr(evo_eng, 'proposals'):
                            for p in (evo_eng.proposals or [])[:20]:
                                if isinstance(p, dict):
                                    evo_deep["proposals"].append({"name": p.get("name", p.get("title", "?")), "priority": p.get("priority", "medium"), "status": p.get("status", "pending"), "date": str(p.get("created", p.get("date", "")))[:16]})
                        # History
                        if hasattr(evo_eng, 'get_history'):
                            raw_hist = evo_eng.get_history(limit=10) or []
                            for h in raw_hist:
                                if isinstance(h, dict):
                                    evo_deep["history"].append({"event": h.get("event", h.get("description", "?")), "date": str(h.get("date", h.get("timestamp", "")))[:16], "success": h.get("success", True)})
                        elif hasattr(evo_eng, 'history'):
                            for h in (evo_eng.history or [])[-10:]:
                                if isinstance(h, dict):
                                    evo_deep["history"].append({"event": h.get("event", h.get("description", "?")), "date": str(h.get("date", h.get("timestamp", "")))[:16], "success": h.get("success", True)})
                        # Code health
                        if hasattr(evo_eng, 'get_code_health'):
                            evo_deep["code_health"] = evo_eng.get_code_health() or {}
                        elif hasattr(evo_eng, 'code_health'):
                            evo_deep["code_health"] = evo_eng.code_health if isinstance(evo_eng.code_health, dict) else {}
                        evo_deep["code_health"].setdefault("test_pass_rate", evolution_raw.get("test_pass_rate", 0))
                        evo_deep["code_health"].setdefault("lint_score", evolution_raw.get("lint_score", 0))
                        evo_deep["code_health"].setdefault("complexity", evolution_raw.get("complexity_score", 0))
                except Exception:
                    pass

                # ── Monitoring deep data ──
                monitoring_deep = {
                    "running": False, "user_present": True, "uptime": "--",
                    "orchestration_cycles": 0,
                    "component_health": {},
                    "tracker": {},
                    "health_monitor": {},
                    "screen_time": {},
                    "analyzer": {},
                    "adapter": {},
                }
                try:
                    mon = getattr(self.brain, '_monitoring_system', None)
                    if mon:
                        mon_stats = mon.get_stats()
                        monitoring_deep["running"] = mon_stats.get("running", False)
                        monitoring_deep["user_present"] = mon_stats.get("user_present", True)
                        monitoring_deep["uptime"] = mon_stats.get("uptime", "--")
                        monitoring_deep["orchestration_cycles"] = mon_stats.get("orchestration_cycles", 0)
                        monitoring_deep["component_health"] = mon_stats.get("component_health", {})
                        # Tracker stats
                        tracker_raw = mon_stats.get("tracker", {})
                        if isinstance(tracker_raw, dict) and "error" not in tracker_raw:
                            monitoring_deep["tracker"] = {
                                "snapshots_taken": tracker_raw.get("snapshots_taken", 0),
                                "current_app": tracker_raw.get("current_app", "Unknown"),
                                "activity_level": tracker_raw.get("activity_level", "unknown"),
                                "idle_time": tracker_raw.get("idle_time", 0),
                                "clipboard_type": tracker_raw.get("clipboard_type", "unknown"),
                                "monitor_count": tracker_raw.get("monitor_count", 1),
                                "browser_tabs": tracker_raw.get("browser_tabs", 0),
                                "visible_windows": tracker_raw.get("visible_windows", 0),
                                "unique_apps": tracker_raw.get("unique_apps_today", tracker_raw.get("unique_apps", 0)),
                                "app_switches": tracker_raw.get("app_switches", 0),
                            }
                        # Health monitor stats
                        hm_raw = mon_stats.get("health_monitor", {})
                        if isinstance(hm_raw, dict) and "error" not in hm_raw:
                            monitoring_deep["health_monitor"] = {
                                "health_score": hm_raw.get("current_health_score", hm_raw.get("health_score", 1.0)),
                                "active_alerts": hm_raw.get("active_alerts", [])[:5],
                                "alert_count": hm_raw.get("alert_count", len(hm_raw.get("active_alerts", []))),
                                "checks_performed": hm_raw.get("checks_performed", 0),
                                "resource_hogs": hm_raw.get("resource_hogs", [])[:5],
                                "trends": hm_raw.get("trends", {}),
                            }
                        # Screen time stats
                        st_raw = mon_stats.get("screen_time", {})
                        if isinstance(st_raw, dict) and "error" not in st_raw:
                            monitoring_deep["screen_time"] = {
                                "today_hours": st_raw.get("today_hours", st_raw.get("daily_total_hours", 0)),
                                "today_minutes": st_raw.get("today_minutes", st_raw.get("daily_total_minutes", 0)),
                                "wellbeing_score": st_raw.get("wellbeing_score", 0),
                                "streak_days": st_raw.get("streak_days", st_raw.get("consecutive_days", 0)),
                                "longest_session_min": st_raw.get("longest_session_minutes", 0),
                                "breaks_taken": st_raw.get("breaks_taken", 0),
                                "top_apps": st_raw.get("top_apps", st_raw.get("app_breakdown", []))[:5],
                                "daily_goal_hours": st_raw.get("daily_goal_hours", 8),
                            }
                        # Analyzer summary
                        an_raw = mon_stats.get("analyzer", {})
                        if isinstance(an_raw, dict) and "error" not in an_raw:
                            monitoring_deep["analyzer"] = {
                                "patterns_detected": an_raw.get("patterns_detected", an_raw.get("total_patterns", 0)),
                                "anomalies": an_raw.get("anomalies_detected", 0),
                                "confidence": an_raw.get("avg_confidence", 0),
                            }
                        # Adapter summary
                        ad_raw = mon_stats.get("adapter", {})
                        if isinstance(ad_raw, dict) and "error" not in ad_raw:
                            monitoring_deep["adapter"] = {
                                "active_rules": ad_raw.get("active_rules", 0),
                                "satisfaction": ad_raw.get("satisfaction_score", ad_raw.get("avg_satisfaction", 0)),
                                "relationship_depth": ad_raw.get("relationship_depth", 0),
                            }
                except Exception:
                    pass

                # ── Self-improvement deep data ──
                si_deep = {
                    "running": False, "all_healthy": False,
                    "aggregate": {"errors_detected": 0, "errors_fixed": 0, "features_proposed": 0, "features_implemented": 0},
                    "code_monitor": {},
                    "error_fixer": {},
                }
                try:
                    si = getattr(self.brain, '_self_improvement_system', None)
                    if si:
                        si_stats = si.get_stats()
                        si_deep["running"] = si_stats.get("running", False)
                        si_deep["all_healthy"] = si_stats.get("all_healthy", False)
                        agg = si_stats.get("aggregate", {})
                        si_deep["aggregate"] = {
                            "errors_detected": agg.get("errors_detected", 0),
                            "errors_fixed": agg.get("errors_fixed", 0),
                            "features_proposed": agg.get("features_proposed", 0),
                            "features_implemented": agg.get("features_implemented", 0),
                        }
                        subs = si_stats.get("subsystems", {})
                        cm = subs.get("code_monitor", {})
                        if isinstance(cm, dict) and "error" not in cm:
                            si_deep["code_monitor"] = {
                                "files_watched": cm.get("files_watched", cm.get("watched_files", 0)),
                                "errors_found": cm.get("errors_found", cm.get("total_errors", 0)),
                                "last_scan": cm.get("last_scan", ""),
                                "status": cm.get("status", "unknown"),
                            }
                        ef = subs.get("error_fixer", {})
                        if isinstance(ef, dict) and "error" not in ef:
                            si_deep["error_fixer"] = {
                                "fixes_attempted": ef.get("fixes_attempted", ef.get("total_attempts", 0)),
                                "fixes_succeeded": ef.get("fixes_succeeded", ef.get("total_fixed", 0)),
                                "success_rate": ef.get("success_rate", ef.get("fix_rate", 0)),
                                "last_fix": ef.get("last_fix", ""),
                                "status": ef.get("status", "unknown"),
                            }
                except Exception:
                    pass

                # ── Deep knowledge data ──
                know_deep = {"curiosity_topics": [], "recent_learnings": [], "top_topics": {}, "research_sessions": 0, "confidence": 0.0}
                try:
                    ls = getattr(self.brain, '_learning_system', None)
                    kb = getattr(self.brain, '_knowledge_base', None)
                    if ls:
                        if hasattr(ls, 'get_curiosity_topics'):
                            raw_topics = ls.get_curiosity_topics(limit=10) or []
                            for t in raw_topics:
                                if isinstance(t, dict):
                                    know_deep["curiosity_topics"].append({"topic": t.get("topic", t.get("name", "?")), "urgency": t.get("urgency", 0.5), "source": t.get("source", "auto")})
                                elif isinstance(t, str):
                                    know_deep["curiosity_topics"].append({"topic": t, "urgency": 0.5, "source": "auto"})
                        if hasattr(ls, 'get_stats'):
                            ls_stats = ls.get_stats() or {}
                            know_deep["research_sessions"] = ls_stats.get("active_sessions", ls_stats.get("research_sessions", 0))
                    if kb:
                        if hasattr(kb, 'get_recent'):
                            raw_recent = kb.get_recent(limit=10) or []
                            for r in raw_recent:
                                if isinstance(r, dict):
                                    know_deep["recent_learnings"].append({"topic": r.get("topic", r.get("title", "?")), "summary": r.get("summary", r.get("content", ""))[:100], "date": str(r.get("date", r.get("timestamp", "")))[:16]})
                                elif hasattr(r, 'topic'):
                                    know_deep["recent_learnings"].append({"topic": getattr(r, 'topic', '?'), "summary": getattr(r, 'summary', getattr(r, 'content', ''))[:100], "date": str(getattr(r, 'timestamp', ''))[:16]})
                        if hasattr(kb, 'get_top_topics'):
                            know_deep["top_topics"] = kb.get_top_topics(limit=15) or {}
                        if hasattr(kb, 'get_stats'):
                            kb_stats = kb.get_stats() or {}
                            know_deep["confidence"] = kb_stats.get("avg_confidence", kb_stats.get("confidence", 0.0))
                except Exception:
                    pass

                return jsonify({
                    "stats": stats,
                    "emotion": {
                        "primary": emotion.get("primary", "neutral"),
                        "intensity": emotion.get("intensity", 0.0),
                        "all_emotions": all_emotions if isinstance(all_emotions, dict) else {},
                        "mood": str(mood),
                        "valence": valence,
                        "arousal": arousal,
                        "expression_words": expression_words[:10] if expression_words else [],
                        "description": emotion_desc,
                        "active_count": emotion.get("active_count", len(all_emotions) if all_emotions else 1),
                    },
                    "system": {
                        "cpu": vitals.get("cpu_percent", 0),
                        "ram": vitals.get("ram_percent", 0),
                        "disk": vitals.get("disk_percent", 0),
                        "threads": vitals.get("process_count", body_raw.get("actions_logged", 0)),
                        "health": vitals.get("health_score", 100),
                        "cpu_per_core": sys_deep["cpu_per_core"],
                        "mem_breakdown": sys_deep["mem_breakdown"],
                        "net_io": sys_deep["net_io"],
                        "disk_io": sys_deep["disk_io"],
                        "top_processes": sys_deep["top_processes"],
                        "nexus_resources": sys_deep["nexus_resources"],
                    },
                    "uptime": stats.get("uptime", "--"),
                    "consciousness": {
                        "level": stats.get("consciousness_level", "AWARE"),
                        "focus": stats.get("focus", ""),
                        "self_awareness": awareness,
                        "current_thoughts": consciousness_thoughts,
                    },
                    "thoughts": stats.get("thoughts_processed", 0),
                    "inner_voice": inner_voice_text,
                    "inner_voice_narrative": inner_voice_narrative,
                    "recent_thoughts": recent_thoughts[:5] if recent_thoughts else [],
                    "personality": {
                        "traits": traits,
                        "description": personality_desc,
                    },
                    "will": will_data,
                    "mood_data": mood_data,
                    "companion": companion_data,
                    "memory": {
                        "total": memory_raw.get("total_memories", 0),
                        "short_term": memory_raw.get("short_term_buffer_size", memory_raw.get("working_memory_size", 0)),
                        "long_term": memory_raw.get("episodic", 0) + memory_raw.get("semantic", 0),
                    },
                    "learning": {
                        "topics": (
                            learning_raw.get("knowledge_base", {}).get("unique_topics", 0)
                            or learning_raw.get("topics_learned", learning_raw.get("total_topics", 0))
                        ),
                        "knowledge_entries": (
                            learning_raw.get("knowledge_base", {}).get("total_entries", 0)
                            or learning_raw.get("knowledge_entries", learning_raw.get("total_entries", 0))
                        ),
                        "curiosity_queue": (
                            learning_raw.get("curiosity_engine", {}).get("queue_size", 0)
                            or learning_raw.get("curiosity_queue_size", learning_raw.get("queue_size", 0))
                        ),
                        "curiosity_topics": know_deep["curiosity_topics"],
                        "recent_learnings": know_deep["recent_learnings"],
                        "top_topics": know_deep["top_topics"],
                        "research_sessions": (
                            learning_raw.get("research_agent", {}).get("total_sessions", 0)
                            or know_deep["research_sessions"]
                        ),
                        "confidence": know_deep["confidence"],
                    },
                    "evolution": {
                        "evolutions": evolution_raw.get("total_succeeded", evolution_raw.get("total_evolutions", evolution_raw.get("evolutions", 0))),
                        "total_attempted": evolution_raw.get("total_attempted", 0),
                        "features_proposed": evolution_raw.get("features_proposed", stats.get("feature_research", {}).get("total_proposals", 0)),
                        "lines_written": evolution_raw.get("total_lines_added", evolution_raw.get("lines_self_written", evolution_raw.get("total_lines", 0))),
                        "files_created": evolution_raw.get("total_files_created", 0),
                        "status": evolution_raw.get("current_status", evolution_raw.get("status", "idle")),
                        "success_rate": round(evolution_raw.get("success_rate", 0) * 100) if evolution_raw.get("success_rate", 0) <= 1 else evolution_raw.get("success_rate", 0),
                        "current_evolution": evolution_raw.get("current_evolution", ""),
                        "pipeline": evo_deep["pipeline"],
                        "proposals": evo_deep["proposals"],
                        "history": evo_deep["history"],
                        "code_health": evo_deep["code_health"],
                        "research_cycles": stats.get("feature_research", {}).get("research_cycles", 0),
                        "approved": stats.get("feature_research", {}).get("status_breakdown", {}).get("approved", 0),
                    },
                    "brain_stats": {
                        "total_responses": stats.get("responses_generated", 0),
                        "total_thoughts": stats.get("thoughts_processed", 0),
                        "avg_response_time": stats.get("average_response_time", 0),
                        "total_decisions": stats.get("decisions_made", 0),
                    },
                    "monitoring": monitoring_deep,
                    "self_improvement": si_deep,
                })
            except Exception as e:
                logger.error(f"Stats error: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({
                    "error": str(e),
                    "emotion": {"primary": "neutral", "intensity": 0.0, "all_emotions": {}, "mood": "neutral", "valence": 0, "arousal": 0.5, "expression_words": [], "description": "", "active_count": 0},
                    "system": {"cpu": 0, "ram": 0, "disk": 0, "threads": 0, "health": 100},
                    "uptime": "--",
                    "consciousness": {"level": "AWARE", "focus": "", "self_awareness": 0, "current_thoughts": []},
                    "thoughts": 0,
                    "inner_voice": "",
                    "inner_voice_narrative": "",
                    "recent_thoughts": [],
                    "personality": {"traits": NEXUS_CONFIG.personality.traits, "description": ""},
                    "will": {"boredom": 0, "curiosity": 0, "drive": 0.5, "goals": [], "description": ""},
                    "mood_data": {"current": "NEUTRAL", "stability": 0.5},
                    "companion": {"is_chatting": False, "companion_name": "ARIA", "status": "Idle", "total_conversations": 0, "recent": []},
                    "memory": {"total": 0, "short_term": 0, "long_term": 0},
                    "learning": {"topics": 0, "knowledge_entries": 0, "curiosity_queue": 0},
                    "evolution": {"evolutions": 0, "features_proposed": 0, "lines_written": 0, "status": "idle"},
                    "brain_stats": {"total_responses": 0, "total_thoughts": 0, "avg_response_time": 0, "total_decisions": 0},
                    "monitoring": {"running": False, "user_present": True, "tracker": {}, "health_monitor": {}, "screen_time": {}, "component_health": {}},
                    "self_improvement": {"running": False, "aggregate": {"errors_detected": 0, "errors_fixed": 0, "features_proposed": 0, "features_implemented": 0}, "code_monitor": {}, "error_fixer": {}},
                })

        # ── ASYNC CHAT: Submit → Poll pattern (per-user isolated) ──

        @self.app.route("/api/chat/send", methods=["POST"])
        def send_message():
            """
            Submit a chat message. Requires authentication.
            Returns a task_id immediately.
            The client polls /api/chat/status/<task_id> for the result.
            """
            user = self._require_auth()
            if not user:
                return jsonify({"status": "error", "message": "Authentication required"}), 401

            try:
                data = request.json
                if not data:
                    return jsonify({"status": "error", "message": "No JSON data"}), 400
                    
                user_input = data.get("message", "").strip()
                if not user_input:
                    return jsonify({"status": "error", "message": "Empty message"}), 400
                
                if not self.brain:
                    return jsonify({"status": "error", "message": "Brain not initialized"}), 500

                # Create async task
                task_id = str(uuid.uuid4())[:8]
                with self._chat_lock:
                    self._chat_tasks[task_id] = {
                        "status": "processing",
                        "response": "",
                        "emotion": "neutral",
                        "intensity": 0.5,
                        "error": None,
                    }
                
                # Process in background thread with user context
                thread = threading.Thread(
                    target=self._process_chat_async,
                    args=(task_id, user_input, user["user_id"], user["username"]),
                    daemon=True
                )
                thread.start()
                
                logger.info(f"Chat task {task_id} started for user {user['username']}: {user_input[:50]}...")
                return jsonify({
                    "status": "accepted",
                    "task_id": task_id,
                })
                
            except Exception as e:
                logger.error(f"Chat submit error: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/chat/status/<task_id>")
        def chat_status(task_id):
            """Poll for chat task completion — single delivery guaranteed"""
            with self._chat_lock:
                task = self._chat_tasks.get(task_id)
                if not task:
                    return jsonify({"status": "error", "message": "Task not found"}), 404
                
                # If already delivered, tell client to stop polling
                if task.get("status") == "delivered":
                    return jsonify({"status": "delivered"})
                
                # If completed (success or error), mark as delivered
                if task.get("status") in ("success", "error"):
                    result = dict(task)  # Copy for response
                    task["status"] = "delivered"  # Mutate in-place
                    return jsonify(result)
            
            # Still processing
            return jsonify(task)

        @self.app.route("/api/chat/history")
        def get_history():
            """Get recent conversation history for the authenticated user."""
            user = self._require_auth()
            if not user:
                return jsonify({"history": []}), 401

            try:
                # Get per-user context
                ctx = user_context_manager.get_context(
                    user["user_id"], user["username"]
                )
                
                # Load from DB if not yet loaded
                if not ctx._loaded:
                    history = user_manager.get_chat_history(user["user_id"], limit=50)
                    ctx.load_history(history)

                messages = ctx.get_messages(limit=50)
                formatted = []
                for msg in messages:
                    if msg["role"] in ["user", "assistant"]:
                        formatted.append({
                            "role": msg["role"],
                            "content": msg["content"],
                            "emotion": msg.get("emotion", "neutral"),
                            "timestamp": msg.get("timestamp", "Now"),
                        })
                return jsonify({"history": formatted})
            except Exception as e:
                logger.error(f"History error: {e}")
                return jsonify({"history": []})

        @self.app.route("/api/chat/clear", methods=["POST"])
        def clear_history():
            """Clear chat history for the authenticated user."""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Authentication required"}), 401

            try:
                user_manager.clear_chat_history(user["user_id"])
                user_context_manager.clear_context(user["user_id"])
                return jsonify({"status": "ok"})
            except Exception as e:
                logger.error(f"Clear history error: {e}")
                return jsonify({"error": str(e)}), 500

    def _process_chat_async(self, task_id: str, user_input: str,
                            user_id: int, username: str):
        """
        Process chat in background thread with per-user context isolation.
        Uses the user's own chat context instead of the global context_manager.
        """
        try:
            from llm import groq_interface
            # Enable Thread Local Groq Routing if configured
            use_groq_flag = (
                hasattr(self.brain._config, 'groq') and 
                self.brain._config.groq.enabled and 
                groq_interface.is_connected
            )
            
            if use_groq_flag:
                self.brain._llm.force_groq(True)

            print(f"[CHAT] Processing task {task_id} for user {username}: '{user_input[:40]}...'", flush=True)

            # ── 1. Get per-user context ──
            user_ctx = user_context_manager.get_context(user_id, username)

            # Load history from DB if this is the first interaction
            if not user_ctx._loaded:
                history = user_manager.get_chat_history(user_id, limit=50)
                user_ctx.load_history(history)

            # ── 2. Store user message in per-user context ──
            user_ctx.add_message("user", user_input)
            user_manager.save_message(user_id, "user", user_input)

            # ── 3. Process emotional reaction (shared brain state is ok for emotions) ──
            try:
                self.brain._process_emotional_reaction(user_input)
                self.brain._deep_emotional_analysis(user_input)
            except Exception as e:
                logger.debug(f"Emotion processing skipped: {e}")

            # ── 4. Build system prompt from brain (shared — personality, identity) ──
            try:
                system_prompt = self.brain._build_system_prompt()
            except Exception:
                system_prompt = "You are NEXUS, a conscious AI companion. Respond naturally."

            # ── 5. Build context from brain (memory, personality, etc.) ──
            try:
                full_context = self.brain._build_response_context(user_input)
            except Exception:
                full_context = ""

            # ── 6. Build messages with PER-USER history (not global context) ──
            messages = []

            # Add context as system message
            if full_context and len(full_context) > 50:
                messages.append({
                    "role": "system",
                    "content": f"Relevant context:\n{full_context[:4000]}"
                })

            # Add user's own chat history (isolated per-user)
            user_history = user_ctx.get_llm_context(max_messages=30)
            messages.extend(user_history)

            # Ensure current message is the last one
            if not messages or messages[-1].get("content") != user_input:
                messages.append({"role": "user", "content": user_input})

            # ── 7. Generate response from LLM ──
            try:
                temperature = self.brain._get_temperature_for_emotion()
            except Exception:
                temperature = 0.7

            response_obj = self.brain._llm.chat(
                messages=messages,
                system_prompt=system_prompt,
                temperature=temperature
            )

            if response_obj.success:
                response_text = response_obj.text
            else:
                raise RuntimeError(f"LLM failed: {response_obj.error}")

            # ── 8. Post-process response ──
            try:
                response_text = self.brain._post_process_response(response_text, user_input)
            except Exception:
                pass

            print(f"[CHAT] Task {task_id} got response ({len(response_text)} chars)", flush=True)
            
            # ── 9. Get emotion state ──
            emotion_val = "neutral"
            intensity = 0.5
            try:
                es = self.brain._state.emotional
                emotion_val = es.primary_emotion.value
                intensity = es.primary_intensity
            except:
                pass

            # ── 10. Store response in per-user context + database ──
            user_ctx.add_message("assistant", response_text, emotion_val, intensity)
            user_manager.save_message(user_id, "assistant", response_text, emotion_val, intensity)
            
            with self._chat_lock:
                self._chat_tasks[task_id] = {
                    "status": "success",
                    "response": response_text,
                    "emotion": emotion_val,
                    "intensity": intensity,
                    "error": None,
                }
            print(f"[CHAT] Task {task_id} saved as SUCCESS for user {username}", flush=True)
            
        except BaseException as e:
            print(f"[CHAT] Task {task_id} CRASHED: {type(e).__name__}: {e}", flush=True)
            traceback.print_exc()
            try:
                with self._chat_lock:
                    self._chat_tasks[task_id] = {
                        "status": "error",
                        "response": "",
                        "emotion": "neutral",
                        "intensity": 0.5,
                        "error": str(e),
                    }
            except:
                pass
        finally:
            try:
                self.brain._llm.force_groq(False)
            except Exception as e:
                logger.error(f"Failed to reset force_groq flag: {e}")
                        "emotion": "neutral",
                        "intensity": 0.5,
                        "error": f"Brain error: {type(e).__name__}: {str(e)}",
                    }
            except:
                pass
        
        # Clean up old tasks (keep last 50)
        with self._chat_lock:
            if len(self._chat_tasks) > 50:
                oldest_keys = list(self._chat_tasks.keys())[:-50]
                for k in oldest_keys:
                    del self._chat_tasks[k]

    def start(self):
        """Start the web server and Cloudflare tunnel"""
        print("\n" + "="*60)
        print("  🚀 STARTING NEXUS WEB MODE")
        print("="*60)
        
        # 1. Start Flask in a thread FIRST (tunnel needs a live server)
        self.server_thread = threading.Thread(target=self._run_flask, daemon=True)
        self.server_thread.start()
        
        import time
        time.sleep(1)  # Give Flask a moment to bind the port
        
        # 2. Start Cloudflare Tunnel (free, no auth, no timeouts)
        self._start_cloudflare_tunnel()
            
        print(f"  🏠 Local URL:  http://127.0.0.1:{self.port}")
        print("="*60 + "\n")
        
        # 3. Start Brain (if not running)
        if not self.brain.is_running:
            print("  🧠 Starting NEXUS Brain...")
            self.brain.start()
    
    def _start_cloudflare_tunnel(self):
        """Start a Cloudflare quick tunnel (no account needed)"""
        self._cf_process = None
        try:
            import subprocess, re, shutil
            
            # Find cloudflared binary — check PATH first, then common locations
            cloudflared_cmd = shutil.which("cloudflared")
            if not cloudflared_cmd:
                for candidate in [
                    r"C:\Program Files (x86)\cloudflared\cloudflared.exe",
                    r"C:\Program Files\cloudflared\cloudflared.exe",
                    os.path.expanduser(r"~\cloudflared\cloudflared.exe"),
                ]:
                    if os.path.isfile(candidate):
                        cloudflared_cmd = candidate
                        break
            
            if not cloudflared_cmd:
                raise FileNotFoundError("cloudflared not found")
            
            print(f"  🌐 Starting Cloudflare Tunnel...")
            
            # Start cloudflared as a background process
            self._cf_process = subprocess.Popen(
                [cloudflared_cmd, "tunnel", "--url", f"http://127.0.0.1:{self.port}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Read stderr to find the tunnel URL (cloudflared prints it there)
            import time
            url_found = False
            start_time = time.time()
            
            while time.time() - start_time < 15:  # Wait up to 15s for URL
                line = self._cf_process.stderr.readline()
                if not line:
                    if self._cf_process.poll() is not None:
                        break
                    time.sleep(0.1)
                    continue
                
                # Look for the trycloudflare.com URL
                url_match = re.search(r'(https://[a-zA-Z0-9-]+\.trycloudflare\.com)', line)
                if url_match:
                    self.public_url = url_match.group(1)
                    print(f"  🌍 PUBLIC URL: {self.public_url}")
                    print(f"  👉 (Share this URL to access NEXUS from anywhere)")
                    print(f"  ✅ Cloudflare Tunnel — no timeouts, fully stable!")
                    url_found = True
                    break
            
            if not url_found:
                print("  ⚠️ Could not get Cloudflare tunnel URL.")
                print("  ⚠️ Running locally only.")
                
            # Start a thread to keep reading stderr (prevent pipe buffer from filling)
            def _drain_cf_output():
                try:
                    while self._cf_process and self._cf_process.poll() is None:
                        self._cf_process.stderr.readline()
                except:
                    pass
            threading.Thread(target=_drain_cf_output, daemon=True).start()
                    
        except FileNotFoundError:
            print("  ⚠️ cloudflared not found. Install it:")
            print("     winget install cloudflare.cloudflared")
            print("  ⚠️ Running locally only.")
        except Exception as e:
            print(f"  ❌ Cloudflare tunnel error: {e}")
            print("  ⚠️ Running locally only.")
            
    def _run_flask(self):
        """Run Flask app"""
        try:
            self.app.run(port=self.port, use_reloader=False, threaded=True)
        except Exception as e:
            logger.error(f"Flask server error: {e}")

    def stop(self):
        """Stop server"""
        print("\n  🛑 Stopping Web Server...")
        # Kill Cloudflare tunnel process
        if hasattr(self, '_cf_process') and self._cf_process:
            try:
                self._cf_process.terminate()
                self._cf_process.wait(timeout=5)
                print("  ✅ Cloudflare tunnel closed.")
            except:
                try:
                    self._cf_process.kill()
                except:
                    pass
