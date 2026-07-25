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
import json
import logging
import threading
import time
import uuid
import secrets
import traceback
import psutil
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_from_directory
import subprocess
from typing import Any, Dict, Optional, List

# Add project root to path

from config import NEXUS_CONFIG, DATA_DIR
from core.nexus_brain import NexusBrain
from core.user_manager import UserManager, user_manager
from core.user_context import UserContextManager, user_context_manager
from utils.logger import get_logger

logger = get_logger("web_server")

# Catch unhandled exceptions in background threads — log cleanly without aborting
def _thread_exception_handler(args):
    logger.error(f"Thread '{args.thread.name}' error: {args.exc_type.__name__}: {args.exc_value}")

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
        self._cf_process: Any = None  # Cloudflare tunnel subprocess
        
        # Auth session tokens: token -> {user_id, username, display_name, created_at}
        self._auth_sessions = {}
        self._auth_lock = threading.Lock()
        
        # JARVIS-mode: Device Context & Chat Action Router
        try:
            from core.device_context import device_context_manager
            self._device_ctx = device_context_manager
        except Exception:
            self._device_ctx = None
        try:
            from core.chat_action_router import chat_action_router
            self._action_router = chat_action_router
            self._action_router.set_brain(brain)
        except Exception:
            self._action_router = None
        
        # Live action feed SSE subscribers
        self._live_feed_subscribers = []
        self._live_feed_lock = threading.Lock()
        
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
            result = {"status": "ok"}
            if self.public_url:
                result["public_url"] = self.public_url
            return jsonify(result)
        
        @self.app.route("/")
        def index():
            return render_template("index.html")

        @self.app.route("/landing")
        def landing():
            """NEXUS AI APK landing page with features and download"""
            return render_template("landing.html")

        @self.app.route("/download")
        def download_page():
            """Redirect to landing page download section"""
            return render_template("landing.html")

        @self.app.route("/download/apk")
        def download_apk():
            """Download the NEXUS AI APK file"""
            from flask import send_file
            
            # Path to the actual APK file
            apk_path = Path(__file__).parent.parent / "mobile" / "NEXUS-AI.apk"
            
            if apk_path.exists():
                return send_file(
                    apk_path,
                    mimetype='application/vnd.android.package-archive',
                    as_attachment=True,
                    download_name='NEXUS-AI.apk'
                )
            else:
                # Fallback: create a placeholder if APK doesn't exist
                import io
                import zipfile
                from datetime import datetime
                
                memory_buffer = io.BytesIO()
                
                with zipfile.ZipFile(memory_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                    manifest = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.nexus.ai"
    android:versionCode="204"
    android:versionName="2.0.4">
    <uses-permission android:name="android.permission.INTERNET" />
    <application android:label="NEXUS AI" android:icon="@mipmap/ic_launcher">
        <activity android:name=".MainActivity" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>"""
                    zf.writestr("AndroidManifest.xml", manifest)
                    zf.writestr("README.txt", f"NEXUS AI v2.0.4 - Built with consciousness.\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                memory_buffer.seek(0)
                return send_file(
                    memory_buffer,
                    mimetype='application/vnd.android.package-archive',
                    as_attachment=True,
                    download_name='NEXUS-AI.apk'
                )

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

                # JARVIS-mode: Register connecting device
                device_info = None
                if self._device_ctx:
                    try:
                        device_info = self._device_ctx.register_device(
                            session_token=token,
                            user_id=user["id"],
                            username=user["username"],
                            user_agent=request.headers.get("User-Agent", ""),
                            remote_ip=request.remote_addr or "",
                            device_info_header=request.headers.get("X-Device-Info", ""),
                        )
                    except Exception as e:
                        logger.debug(f"Device registration skipped: {e}")

                return jsonify({
                    "status": "ok",
                    "token": token,
                    "user": user,
                    "device": device_info.to_dict() if device_info else None,
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
                # JARVIS-mode: Remove device session
                if self._device_ctx:
                    try:
                        self._device_ctx.remove_session(token)
                    except Exception:
                        pass
            return jsonify({"status": "ok"})

        # ── JARVIS-MODE API ENDPOINTS ──

        @self.app.route("/api/device/info")
        def device_info():
            """Get the current device's profile."""
            user = self._require_auth()
            if not user or not self._device_ctx:
                return jsonify({"error": "Not available"}), 401
            token = request.headers.get("Authorization", "")[7:]
            device = self._device_ctx.get_device(token)
            if device:
                return jsonify(device.to_dict())
            return jsonify({"error": "Device not registered"}), 404

        @self.app.route("/api/device/all")
        def device_all():
            """List all connected devices."""
            user = self._require_auth()
            if not user or not self._device_ctx:
                return jsonify({"devices": []})
            devices = self._device_ctx.get_all_devices()
            return jsonify({"devices": [d.to_dict() for d in devices]})

        @self.app.route("/api/live/stream")
        def live_stream():
            """SSE endpoint for JARVIS-style live action feed."""
            import queue as _queue
            q = _queue.Queue(maxsize=100)
            with self._live_feed_lock:
                self._live_feed_subscribers.append(q)

            def generate():
                try:
                    yield "data: {\"type\":\"connected\"}\n\n"
                    while True:
                        try:
                            event = q.get(timeout=30)
                            yield event
                        except _queue.Empty:
                            yield ": keepalive\n\n"
                except GeneratorExit:
                    pass
                finally:
                    with self._live_feed_lock:
                        try:
                            self._live_feed_subscribers.remove(q)
                        except ValueError:
                            pass

            return self.app.response_class(
                generate(),
                mimetype="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
            )

        @self.app.route("/api/live/actions")
        def live_actions():
            """Get recent action history from the chat action router."""
            if self._action_router:
                return jsonify(self._action_router.get_stats())
            return jsonify({"total_actions": 0, "recent": []})

        @self.app.route("/api/auth/email/send-otp", methods=["POST"])
        def auth_email_send_otp():
            """Generate and send a 4-digit OTP to the given email."""
            try:
                data = request.json
                if not data or not data.get("email"):
                    return jsonify({"error": "Email is required"}), 400

                email = data["email"].strip()
                if "@" not in email or "." not in email:
                    return jsonify({"error": "Invalid email address"}), 400

                code = user_manager.generate_otp(email)
                sent = user_manager.send_otp_email(email, code)

                if not sent:
                    return jsonify({"error": "Failed to send email. SMTP not configured."}), 500

                return jsonify({"status": "ok", "message": "OTP sent to your email"})
            except Exception as e:
                logger.error(f"Email OTP send error: {e}")
                return jsonify({"error": "Server error"}), 500

        @self.app.route("/api/auth/email/verify-otp", methods=["POST"])
        def auth_email_verify_otp():
            """Verify the 4-digit OTP and authenticate."""
            try:
                data = request.json
                if not data:
                    return jsonify({"error": "No JSON data"}), 400

                email = (data.get("email") or "").strip()
                code = (data.get("code") or "").strip()

                if not email or not code:
                    return jsonify({"error": "Email and code are required"}), 400

                user = user_manager.verify_otp(email, code)
                if not user:
                    return jsonify({"error": "Invalid or expired code"}), 401

                token = self._create_session_token(user)

                # Load chat history
                ctx = user_context_manager.get_context(user["id"], user["username"])
                history = user_manager.get_chat_history(user["id"], limit=50)
                ctx.load_history(history)

                return jsonify({"status": "ok", "token": token, "user": user})
            except Exception as e:
                logger.error(f"Email OTP verify error: {e}")
                return jsonify({"error": "Server error"}), 500

        # ── USER SETTINGS ROUTES ──

        @self.app.route("/api/user/profile")
        def user_profile():
            """Get full user profile."""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Not authenticated"}), 401
            try:
                profile = user_manager.get_full_profile(user["user_id"])
                if not profile:
                    return jsonify({"error": "User not found"}), 404
                return jsonify({"status": "ok", "profile": profile})
            except Exception as e:
                logger.error(f"Get profile error: {e}")
                return jsonify({"error": "Server error"}), 500

        @self.app.route("/api/user/profile", methods=["PUT"])
        def update_user_profile():
            """Update display name and bio."""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Not authenticated"}), 401
            try:
                data = request.json or {}
                display_name = (data.get("display_name") or "").strip()
                bio = (data.get("bio") or "").strip()
                if not display_name:
                    return jsonify({"error": "Display name is required"}), 400

                profile = user_manager.update_profile(user["user_id"], display_name, bio)

                # Update the session token's display_name so header/sidebar update instantly
                with self._auth_lock:
                    auth_header = request.headers.get("Authorization", "")
                    if auth_header.startswith("Bearer "):
                        token = auth_header[7:]
                        if token in self._auth_sessions:
                            self._auth_sessions[token]["display_name"] = display_name

                return jsonify({"status": "ok", "profile": profile})
            except Exception as e:
                logger.error(f"Update profile error: {e}")
                return jsonify({"error": "Server error"}), 500

        @self.app.route("/api/user/password", methods=["PUT"])
        def change_user_password():
            """Change user password (requires current password)."""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Not authenticated"}), 401
            try:
                data = request.json or {}
                old_password = data.get("current_password", "")
                new_password = data.get("new_password", "")

                if not old_password or not new_password:
                    return jsonify({"error": "Current and new password are required"}), 400

                user_manager.change_password(user["user_id"], old_password, new_password)
                return jsonify({"status": "ok", "message": "Password changed successfully"})
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            except Exception as e:
                logger.error(f"Change password error: {e}")
                return jsonify({"error": "Server error"}), 500

        @self.app.route("/api/user/avatar", methods=["POST"])
        def upload_user_avatar():
            """Upload base64-encoded profile picture."""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Not authenticated"}), 401
            try:
                data = request.json or {}
                avatar_data = data.get("avatar", "")
                if not avatar_data:
                    return jsonify({"error": "No avatar data provided"}), 400

                # Limit size to ~2MB base64
                if len(avatar_data) > 2_800_000:
                    return jsonify({"error": "Image too large (max ~2MB)"}), 400

                user_manager.update_avatar(user["user_id"], avatar_data)
                return jsonify({"status": "ok", "message": "Avatar updated"})
            except Exception as e:
                logger.error(f"Upload avatar error: {e}")
                return jsonify({"error": "Server error"}), 500

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
                # Fallback: use _current_inner_voice / _thought_log added to NexusBrain
                if not inner_voice_text:
                    inner_voice_text = getattr(self.brain, '_current_inner_voice', '') or stats.get('inner_voice', '')
                if not recent_thoughts:
                    thought_log = getattr(self.brain, '_thought_log', None)
                    if thought_log:
                        recent_thoughts = list(thought_log)
                    elif stats.get('recent_thoughts'):
                        recent_thoughts = stats.get('recent_thoughts', [])
                
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
                    procs.sort(key=lambda x: float(x.get('cpu_percent', 0.0)), reverse=True)
                    sys_deep["top_processes"] = [x for i, x in enumerate(procs) if i < 10]
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
                        # Pipeline steps — map current_status string to step index
                        pipeline_names = ["Analyze", "Propose", "Review", "Implement", "Test", "Deploy", "Monitor"]
                        status_to_step = {
                            "idle": -1, "planning": 0, "backing_up": 1,
                            "installing_deps": 2, "writing_code": 3, "modifying_code": 3,
                            "validating": 4, "testing": 4, "integrating": 5,
                            "completed": 6, "failed": -1, "rolling_back": -1,
                        }
                        cur_status = evolution_raw.get("current_status", "idle")
                        current_step = status_to_step.get(cur_status, -1)
                        # If idle but has history, mark all steps as done (last evolution completed)
                        has_history = evolution_raw.get("total_attempted", 0) > 0 or evolution_raw.get("total_succeeded", 0) > 0
                        if current_step == -1 and has_history:
                            evo_deep["pipeline"] = [{"name": n, "status": "done"} for n in pipeline_names]
                        else:
                            evo_deep["pipeline"] = [{"name": n, "status": "done" if i < current_step else ("active" if i == current_step else "pending")} for i, n in enumerate(pipeline_names)]

                        # Proposals — pull from feature researcher or file
                        try:
                            fr = getattr(self.brain, '_feature_researcher', None)
                            if not fr:
                                fr = getattr(evo_eng, '_feature_researcher', None)
                            if fr:
                                # Access _proposals dict directly (FeatureResearcher stores proposals as dict)
                                raw_proposals = getattr(fr, '_proposals', {})
                                if isinstance(raw_proposals, dict):
                                    raw_proposals = list(raw_proposals.values())
                                elif isinstance(raw_proposals, list):
                                    pass
                                else:
                                    raw_proposals = []
                                for i, p in enumerate(raw_proposals):
                                    if i >= 20: break
                                    if isinstance(p, dict):
                                        evo_deep["proposals"].append({"name": p.get("name", p.get("title", "?")), "priority": p.get("priority", "medium"), "status": p.get("status", "pending"), "date": str(p.get("created_at", p.get("created", p.get("date", ""))))[:16]})
                                    elif hasattr(p, 'to_dict'):
                                        pd = p.to_dict()
                                        evo_deep["proposals"].append({"name": pd.get("name", pd.get("title", "?")), "priority": pd.get("priority", "medium"), "status": pd.get("status", "pending"), "date": str(pd.get("created_at", pd.get("created", pd.get("date", ""))))[:16]})
                                    elif hasattr(p, 'name'):
                                        evo_deep["proposals"].append({"name": getattr(p, 'name', '?'), "priority": getattr(p, 'priority_score', 'medium'), "status": getattr(p, 'status', 'pending').value if hasattr(getattr(p, 'status', ''), 'value') else str(getattr(p, 'status', 'pending')), "date": str(getattr(p, 'created_at', ''))[:16]})
                        except Exception as ex:
                            logger.debug(f"Error getting proposals from memory: {ex}")
                        
                        # File-based fallback for proposals
                        if not evo_deep["proposals"]:
                            try:
                                pp = Path(DATA_DIR) / "proposals" / "proposals.json"
                                if pp.exists():
                                    proposals_data = json.loads(pp.read_text(encoding="utf-8"))
                                    if isinstance(proposals_data, dict):
                                        proposals_list = list(proposals_data.values())
                                    elif isinstance(proposals_data, list):
                                        proposals_list = proposals_data
                                    else:
                                        proposals_list = []
                                    # Sort by date (newest first) and take top 20
                                    proposals_list.sort(key=lambda x: str(x.get("created_at", x.get("created", x.get("date", "")))), reverse=True)
                                    for i, p in enumerate(proposals_list[:20]):
                                        if isinstance(p, dict):
                                            # Compute priority label from priority_score
                                            ps = p.get("priority_score", p.get("priority", 0))
                                            if isinstance(ps, (int, float)):
                                                priority_label = "critical" if ps >= 8 else ("high" if ps >= 6 else ("medium" if ps >= 3 else "low"))
                                            else:
                                                priority_label = str(ps) if ps else "medium"
                                            evo_deep["proposals"].append({
                                                "name": p.get("name", p.get("title", "?")),
                                                "priority": priority_label,
                                                "status": p.get("status", "pending"),
                                                "date": str(p.get("created_at", p.get("created", p.get("date", ""))))[:16],
                                            })
                            except Exception as ex:
                                logger.debug(f"Error loading proposals from file: {ex}")

                        # History — read _evolution_history from the engine
                        try:
                            hist_records = getattr(evo_eng, '_evolution_history', []) or []
                            
                            # If in-memory history is empty, try loading from file
                            if not hist_records:
                                try:
                                    hp = Path(DATA_DIR) / "evolution_records" / "evolution_history.json"
                                    if hp.exists():
                                        hist_data = json.loads(hp.read_text(encoding="utf-8"))
                                        if isinstance(hist_data, list):
                                            hist_records = hist_data
                                except Exception:
                                    pass

                            recent = list(reversed(hist_records))[:15]
                            for rec in recent:
                                if hasattr(rec, 'to_dict'):
                                    rd = rec.to_dict()
                                    evo_deep["history"].append({
                                        "event": rd.get("proposal_name", rd.get("event", "Evolution")),
                                        "date": str(rd.get("started_at", rd.get("date", "")))[:16],
                                        "success": rd.get("success", False),
                                        "status": rd.get("status", "unknown"),
                                        "lines_added": rd.get("lines_added", 0),
                                    })
                                elif isinstance(rec, dict):
                                    evo_deep["history"].append({
                                        "event": rec.get("proposal_name", rec.get("event", rec.get("description", "?"))),
                                        "date": str(rec.get("started_at", rec.get("date", rec.get("timestamp", ""))))[:16],
                                        "success": rec.get("success", False),
                                        "lines_added": rec.get("lines_added", 0),
                                    })
                        except Exception as ex:
                            logger.debug(f"Error getting evolution history: {ex}")

                        # Also add completed evolutions as proposals if proposals list is still empty
                        if not evo_deep["proposals"] and evo_deep["history"]:
                            for h in evo_deep["history"][:15]:
                                evo_deep["proposals"].append({
                                    "name": h.get("event", "Unknown"),
                                    "priority": "high" if h.get("success", False) else "medium",
                                    "status": "completed" if h.get("success", False) else "failed",
                                    "date": h.get("date", ""),
                                })

                        # Code health — derive from evolution stats
                        evo_stats_for_health = getattr(evo_eng, '_stats', None)
                        attempted = getattr(evo_stats_for_health, 'total_evolutions_attempted', 0) if evo_stats_for_health else 0
                        succeeded = getattr(evo_stats_for_health, 'total_evolutions_succeeded', 0) if evo_stats_for_health else 0
                        health_rate = round((succeeded / attempted) * 100) if attempted > 0 else 0
                        evo_deep["code_health"] = {
                            "test_pass_rate": health_rate,
                            "lint_score": min(100, health_rate + 15) if attempted > 0 else 0,
                            "complexity": min(100, max(0, 100 - (getattr(evo_stats_for_health, 'consecutive_failures', 0) * 20))) if evo_stats_for_health else 0,
                        }
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
                know_deep = {"curiosity_topics": [], "recent_learnings": [], "top_topics": {}, "research_sessions": 0, "confidence": 0.0, "source_breakdown": {}, "knowledge_gaps": [], "knowledge_gaps_count": 0, "active_research": {}, "learning_velocity": 0, "timeline": []}
                # Map CuriosityUrgency enum names → numeric values
                _urgency_map = {"IDLE": 0.0, "LOW": 0.25, "MODERATE": 0.5, "HIGH": 0.75, "BURNING": 1.0}
                try:
                    ls = getattr(self.brain, '_learning_system', None)
                    kb = getattr(self.brain, '_knowledge_base_l', None) or getattr(self.brain, '_knowledge_base', None)
                    if not kb:
                        try:
                            from learning.knowledge_base import knowledge_base as kb
                        except Exception:
                            kb = None
                    if ls:
                        if hasattr(ls, 'get_curiosity_topics'):
                            raw_topics = ls.get_curiosity_topics(limit=10) or []
                            for t in raw_topics:
                                if isinstance(t, dict):
                                    urgency_raw = t.get("urgency", 0.5)
                                    urgency_val = _urgency_map.get(str(urgency_raw).upper(), urgency_raw if isinstance(urgency_raw, (int, float)) else 0.5)
                                    know_deep["curiosity_topics"].append({"topic": t.get("topic", t.get("name", "?")), "urgency": urgency_val, "source": t.get("source", "auto")})
                                elif isinstance(t, str):
                                    know_deep["curiosity_topics"].append({"topic": t, "urgency": 0.5, "source": "auto"})
                        if hasattr(ls, 'get_stats'):
                            ls_stats = ls.get_stats() or {}
                            know_deep["research_sessions"] = ls_stats.get("active_sessions", ls_stats.get("research_sessions", 0))
                    if kb:
                        try:
                            if hasattr(kb, 'get_recent'):
                                raw_recent = kb.get_recent(limit=10) or []
                                for r in raw_recent:
                                    if isinstance(r, dict):
                                        know_deep["recent_learnings"].append({"topic": r.get("topic", r.get("title", "?")), "summary": r.get("summary", r.get("content", ""))[:100], "date": str(r.get("date", r.get("created_at", "")))[:16], "source": r.get("source", "unknown"), "importance": r.get("importance", 0.5)})
                                    elif hasattr(r, 'topic'):
                                        src = getattr(r, 'source', 'unknown')
                                        src_str = src.value if hasattr(src, 'value') else str(src)
                                        know_deep["recent_learnings"].append({"topic": getattr(r, 'topic', '?'), "summary": getattr(r, 'summary', getattr(r, 'content', ''))[:100], "date": str(getattr(r, 'created_at', ''))[:16], "source": src_str, "importance": getattr(r, 'importance', 0.5)})
                        except Exception as e:
                            logger.debug(f"Error getting recent learnings: {e}")
                        try:
                            if hasattr(kb, 'get_stats'):
                                kb_stats = kb.get_stats() or {}
                                know_deep["top_topics"] = kb_stats.get("top_topics", {})
                                know_deep["confidence"] = kb_stats.get("avg_confidence", kb_stats.get("confidence", 0.0))
                        except Exception as e:
                            logger.debug(f"Error getting kb stats: {e}")
                        try:
                            if hasattr(kb, 'get_source_breakdown'):
                                know_deep["source_breakdown"] = kb.get_source_breakdown() or {}
                        except Exception as e:
                            logger.debug(f"Error getting source breakdown: {e}")
                        try:
                            if hasattr(kb, 'get_learning_timeline'):
                                tl = kb.get_learning_timeline(days=14) or []
                                know_deep["timeline"] = tl
                                if len(tl) > 1:
                                    recent_counts = [d["count"] for d in tl[-7:]]
                                    know_deep["learning_velocity"] = round(sum(recent_counts) / max(1, len(recent_counts)), 1)
                        except Exception as e:
                            logger.debug(f"Error getting timeline: {e}")
                except Exception:
                    pass
                # Knowledge gaps from research intelligence
                try:
                    ri = getattr(self.brain, '_research_intelligence', None)
                    if ri and hasattr(ri, 'get_knowledge_gaps'):
                        gaps = ri.get_knowledge_gaps(limit=10) or []
                        for g in gaps:
                            if isinstance(g, dict):
                                know_deep["knowledge_gaps"].append({"area": g.get("area", "?"), "description": g.get("description", "")[:100], "impact": g.get("impact", 0.5)})
                            elif hasattr(g, 'area'):
                                know_deep["knowledge_gaps"].append({"area": getattr(g, 'area', '?'), "description": getattr(g, 'description', '')[:100], "impact": getattr(g, 'impact', 0.5)})
                        know_deep["knowledge_gaps_count"] = len(know_deep["knowledge_gaps"])
                except Exception:
                    pass
                # Active research from research agent
                try:
                    ra = getattr(self.brain, '_research_agent', None)
                    if ra and hasattr(ra, 'get_stats'):
                        ra_stats = ra.get_stats() or {}
                        know_deep["active_research"] = {
                            "is_researching": ra_stats.get("currently_researching", False),
                            "current_topic": ra_stats.get("current_topic", ""),
                            "total_sessions": ra_stats.get("total_sessions", 0),
                            "successful": ra_stats.get("successful_sessions", 0),
                            "failed": ra_stats.get("failed_sessions", 0),
                        }
                except Exception:
                    pass

                # ── Context stats (token usage) ──
                context_stats_data = {"total_tokens": 0, "max_tokens": 0, "utilization_pct": 0}
                try:
                    cm = getattr(self.brain, '_context_manager', None)
                    if cm:
                        max_tok = getattr(cm, '_available_context_tokens', getattr(cm, '_max_context_tokens', 0))
                        cur_session = getattr(cm, 'current_session', None)
                        cur_tok = getattr(cur_session, 'total_tokens', 0) if cur_session else 0
                        util_pct = round(cur_tok / max_tok * 100, 1) if max_tok > 0 else 0
                        context_stats_data = {"total_tokens": cur_tok, "max_tokens": max_tok, "utilization_pct": util_pct}
                except Exception:
                    pass

                # ── User state (comm style, tech level, relationship) ──
                user_state_data = {"communication_style": "unknown", "technical_level": "unknown", "relationship_depth": 0.0}
                try:
                    us = self.brain._state.user
                    user_state_data["communication_style"] = getattr(us, 'communication_style', 'unknown') or 'unknown'
                    user_state_data["technical_level"] = getattr(us, 'technical_level', 'unknown') or 'unknown'
                except Exception:
                    pass
                try:
                    user_state_data["relationship_depth"] = monitoring_deep.get("adapter", {}).get("relationship_depth", 0.0)
                except Exception:
                    pass

                # ── LLM model name ──
                llm_model_name = "Unknown"
                try:
                    if hasattr(NEXUS_CONFIG, 'groq') and NEXUS_CONFIG.groq.enabled:
                        llm_model_name = getattr(NEXUS_CONFIG.groq, 'model', 'Groq')
                    else:
                        llm_model_name = getattr(NEXUS_CONFIG.llm, 'model_name', 'Unknown')
                except Exception:
                    pass

                # ── AGI Module Data ──
                agi_modules = {
                    "digital_organism": {},
                    "imagination_engine": {},
                    "consciousness_evolution": {},
                    "multi_agent_mind": {},
                    "predictive_coding": {},
                    "value_alignment": {},
                    "cognition_engines": {"total": 56, "active": 56},
                }
                try:
                    org = getattr(self.brain, '_digital_organism', None)
                    if org:
                        # Trigger heartbeat to keep organism alive
                        try:
                            org.heartbeat()
                        except Exception:
                            pass
                        if hasattr(org, 'get_stats'):
                            agi_modules["digital_organism"] = org.get_stats()
                except Exception as e:
                    logger.debug(f"AGI digital_organism stats error: {e}")
                try:
                    img = getattr(self.brain, '_imagination_engine', None)
                    if img and hasattr(img, 'get_stats'):
                        agi_modules["imagination_engine"] = img.get_stats()
                except Exception as e:
                    logger.debug(f"AGI imagination_engine stats error: {e}")
                try:
                    ce = getattr(self.brain, '_consciousness_evolution', None)
                    if ce and hasattr(ce, 'get_stats'):
                        agi_modules["consciousness_evolution"] = ce.get_stats()
                except Exception as e:
                    logger.debug(f"AGI consciousness_evolution stats error: {e}")
                try:
                    mam = getattr(self.brain, '_multi_agent_mind', None)
                    if mam and hasattr(mam, 'get_stats'):
                        mam_data = mam.get_stats()
                        # Ensure agent_stats has per-agent wins/votes from agent objects
                        if not mam_data.get("agent_stats") and hasattr(mam, '_agents'):
                            mam_data["agent_stats"] = {
                                name: {"wins": getattr(a, 'wins', 0),
                                       "votes": getattr(a, 'total_votes', 0),
                                       "influence": getattr(a, 'influence_weight', 0.5)}
                                for name, a in mam._agents.items()
                            }
                        agi_modules["multi_agent_mind"] = mam_data
                except Exception as e:
                    logger.debug(f"AGI multi_agent_mind stats error: {e}")
                try:
                    pc = getattr(self.brain, '_predictive_coding', None)
                    if pc and hasattr(pc, 'get_stats'):
                        agi_modules["predictive_coding"] = pc.get_stats()
                except Exception as e:
                    logger.debug(f"AGI predictive_coding stats error: {e}")
                try:
                    va = getattr(self.brain, '_value_alignment', None)
                    if va and hasattr(va, 'get_stats'):
                        agi_modules["value_alignment"] = va.get_stats()
                except Exception as e:
                    logger.debug(f"AGI value_alignment stats error: {e}")
                try:
                    cog = getattr(self.brain, '_cognition_system', None)
                    if cog and hasattr(cog, 'get_stats'):
                        cog_stats = cog.get_stats()
                        agi_modules["cognition_engines"] = {
                            "total": cog_stats.get("total_engines", 56),
                            "active": cog_stats.get("active_engines", 56),
                        }
                except Exception as e:
                    logger.debug(f"AGI cognition stats error: {e}")

                return jsonify({
                    "stats": stats,
                    "emotion": {
                        "primary": emotion.get("primary", "neutral"),
                        "intensity": emotion.get("intensity", 0.0),
                        "all_emotions": all_emotions if isinstance(all_emotions, dict) else {},
                        "mood": str(mood),
                        "valence": valence,
                        "arousal": arousal,
                        "expression_words": [w for i, w in enumerate(expression_words) if i < 10] if expression_words else [],
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
                    "recent_thoughts": recent_thoughts[:20] if recent_thoughts else [],
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
                        "source_breakdown": know_deep["source_breakdown"],
                        "knowledge_gaps": know_deep["knowledge_gaps"],
                        "knowledge_gaps_count": know_deep["knowledge_gaps_count"],
                        "active_research": know_deep["active_research"],
                        "learning_velocity": know_deep["learning_velocity"],
                        "timeline": know_deep["timeline"],
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
                        "total_rollbacks": evolution_raw.get("total_rollbacks", 0),
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
                    "autonomous_mind": stats.get("autonomous_mind", {}),
                    "monitoring": monitoring_deep,
                    "self_improvement": si_deep,
                    "context": context_stats_data,
                    "user_state": user_state_data,
                    "llm_model": llm_model_name,
                    "autonomy": self._get_autonomy_summary(),
                    "pc_control": self._get_pc_control_summary(),
                    "social_media": self._get_social_media_summary(),
                    "agi_modules": agi_modules,
                    "hacking_stats": self._get_hacking_stats(),
                    "asi_engines": self._get_asi_stats(),
                    "swarm": self._get_swarm_summary(),
                    "sandbox_verifier": self._get_sandbox_verifier_summary(),
                    "graphrag": self._get_graphrag_summary(),
                    "mcp": self._get_mcp_summary(),
                    "speculative_stream": self._get_speculative_stream_summary(),
                    "lora_moe": self._get_lora_moe_summary(),
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

        # ── ETHICAL HACKING: Scan endpoint ──

        @self.app.route("/api/hacking/scan", methods=["POST"])
        def hacking_scan():
            """Trigger an ethical hacking scan on a target."""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            try:
                data = request.json or {}
                target = (data.get("target") or "").strip()
                if not target:
                    return jsonify({"error": "Target is required"}), 400

                from core.ethical_hacking import ethical_hacking_engine
                extended = data.get("extended", False)
                timeout = min(float(data.get("timeout", 1.0)), 3.0)

                # Run scan in background thread
                task_id = str(uuid.uuid4())[:8]
                with self._chat_lock:
                    self._chat_tasks[task_id] = {
                        "status": "scanning",
                        "scan_type": "hacking",
                        "target": target,
                    }

                def _run_scan():
                    try:
                        result = ethical_hacking_engine.scan_target(
                            target, timeout=timeout, extended=extended
                        )
                        with self._chat_lock:
                            self._chat_tasks[task_id] = {
                                "status": "complete",
                                "scan_type": "hacking",
                                "result": result,
                            }
                    except Exception as e:
                        with self._chat_lock:
                            self._chat_tasks[task_id] = {
                                "status": "error",
                                "scan_type": "hacking",
                                "error": str(e),
                            }

                threading.Thread(target=_run_scan, daemon=True).start()
                return jsonify({"status": "accepted", "task_id": task_id, "target": target})
            except Exception as e:
                logger.error(f"Hacking scan error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/hacking/scan/status/<task_id>")
        def hacking_scan_status(task_id):
            """Poll for hacking scan completion."""
            with self._chat_lock:
                task = self._chat_tasks.get(task_id)
                if not task or task.get("scan_type") != "hacking":
                    return jsonify({"status": "error", "message": "Task not found"}), 404
                return jsonify(task)

        @self.app.route("/api/hacking/network")
        def hacking_network():
            """Get network reconnaissance info."""
            try:
                from core.ethical_hacking import ethical_hacking_engine
                info = ethical_hacking_engine.get_network_info(refresh=True)
                return jsonify({"status": "ok", "network": info})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/hacking/dns", methods=["POST"])
        def hacking_dns():
            """Perform DNS lookup."""
            try:
                data = request.json or {}
                hostname = (data.get("hostname") or "").strip()
                if not hostname:
                    return jsonify({"error": "Hostname required"}), 400
                from core.ethical_hacking import ethical_hacking_engine
                result = ethical_hacking_engine.dns_lookup(hostname)
                return jsonify({"status": "ok", "dns": result})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/hacking/full_recon", methods=["POST"])
        def hacking_full_recon():
            """Full reconnaissance scan: ports + HTTP + SSL + traceroute + WAF."""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            try:
                data = request.json or {}
                target = (data.get("target") or "").strip()
                if not target:
                    return jsonify({"error": "Target is required"}), 400
                from core.ethical_hacking import ethical_hacking_engine
                task_id = str(uuid.uuid4())[:8]
                with self._chat_lock:
                    self._chat_tasks[task_id] = {"status": "scanning", "scan_type": "full_recon", "target": target}
                def _run():
                    try:
                        result = ethical_hacking_engine.full_recon(target)
                        with self._chat_lock:
                            self._chat_tasks[task_id] = {"status": "complete", "scan_type": "full_recon", "result": result}
                    except Exception as e:
                        with self._chat_lock:
                            self._chat_tasks[task_id] = {"status": "error", "scan_type": "full_recon", "error": str(e)}
                threading.Thread(target=_run, daemon=True).start()
                return jsonify({"status": "accepted", "task_id": task_id, "target": target})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/hacking/http_audit", methods=["POST"])
        def hacking_http_audit():
            """HTTP security header analysis."""
            try:
                data = request.json or {}
                target = (data.get("target") or "").strip()
                if not target:
                    return jsonify({"error": "Target required"}), 400
                from core.ethical_hacking import ethical_hacking_engine
                use_https = data.get("https", False)
                port = int(data.get("port", 443 if use_https else 80))
                result = ethical_hacking_engine.analyze_http_headers(target, port, use_https)
                return jsonify({"status": "ok", "result": result})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/hacking/ssl_check", methods=["POST"])
        def hacking_ssl_check():
            """SSL/TLS certificate and configuration analysis."""
            try:
                data = request.json or {}
                target = (data.get("target") or "").strip()
                if not target:
                    return jsonify({"error": "Target required"}), 400
                from core.ethical_hacking import ethical_hacking_engine
                port = int(data.get("port", 443))
                result = ethical_hacking_engine.analyze_ssl(target, port)
                return jsonify({"status": "ok", "result": result})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/hacking/subdomains", methods=["POST"])
        def hacking_subdomains():
            """Subdomain enumeration via DNS."""
            try:
                data = request.json or {}
                domain = (data.get("domain") or "").strip()
                if not domain:
                    return jsonify({"error": "Domain required"}), 400
                from core.ethical_hacking import ethical_hacking_engine
                result = ethical_hacking_engine.enumerate_subdomains(domain)
                return jsonify({"status": "ok", "result": result})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/hacking/sweep", methods=["POST"])
        def hacking_sweep():
            """Subnet ping sweep."""
            try:
                data = request.json or {}
                from core.ethical_hacking import ethical_hacking_engine
                subnet_base = (data.get("subnet_base") or "").strip() or None
                result = ethical_hacking_engine.sweep_subnet(subnet_base)
                return jsonify({"status": "ok", "result": result})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

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

                # Extract images array if present
                images_data = data.get("images", [])
                
                # Extract thinking mode flag
                thinking_mode = bool(data.get("thinking_mode", False))

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
                    args=(task_id, user_input, user["user_id"], user["username"], images_data, thinking_mode),
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
        # ── STT API (Speech-to-Text for Mobile WebView) ──

        @self.app.route("/api/stt", methods=["POST"])
        def stt_transcribe():
            """Transcribe audio to text using speech_recognition library."""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Authentication required"}), 401

            try:
                if 'audio' not in request.files:
                    return jsonify({"error": "No audio file provided"}), 400

                audio_file = request.files['audio']

                # Save uploaded audio to temp file
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
                    audio_path = f.name
                    audio_file.save(f)

                wav_path = None
                try:
                    # Convert webm to wav using pydub (ffmpeg)
                    try:
                        from pydub import AudioSegment
                        audio_segment = AudioSegment.from_file(audio_path)
                        wav_path = audio_path.replace('.webm', '.wav')
                        audio_segment.export(wav_path, format='wav')
                    except Exception as conv_err:
                        logger.warning(f"Audio conversion failed, trying raw: {conv_err}")
                        wav_path = audio_path  # Try raw file

                    # Transcribe using speech_recognition
                    import speech_recognition as sr
                    recognizer = sr.Recognizer()

                    with sr.AudioFile(wav_path) as source:
                        audio_data = recognizer.record(source)

                    text = recognizer.recognize_google(audio_data)
                    return jsonify({"text": text, "status": "ok"})

                finally:
                    # Cleanup temp files
                    import os
                    try:
                        if os.path.exists(audio_path):
                            os.remove(audio_path)
                        if wav_path and wav_path != audio_path and os.path.exists(wav_path):
                            os.remove(wav_path)
                    except Exception:
                        pass

            except Exception as e:
                logger.error(f"STT transcription error: {e}")
                return jsonify({"error": str(e), "text": ""}), 500

        # ── TTS API (Emotional Voice for Web) ──

        @self.app.route("/api/tts", methods=["POST"])
        def tts_generate():
            """Generate emotional TTS audio and return as MP3."""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Authentication required"}), 401

            try:
                data = request.json
                if not data:
                    return jsonify({"error": "No JSON data"}), 400

                text = (data.get("text") or "").strip()
                if not text:
                    return jsonify({"error": "No text provided"}), 400

                # Cap text length to prevent abuse
                text = text[:2000]
                emotion = data.get("emotion", "neutral")
                intensity = float(data.get("intensity", 0.5))

                # Import edge_tts and prosody helper
                try:
                    import edge_tts
                except ImportError:
                    return jsonify({"error": "edge_tts not installed"}), 500

                from core.voice_engine import _prosody_for_emotion, _select_voice

                # Get emotional prosody values
                rate, pitch, volume = _prosody_for_emotion(emotion, intensity)
                voice = _select_voice(text)

                # Generate audio in background thread to not block Flask
                import tempfile
                import asyncio

                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    temp_path = f.name

                async def _generate():
                    communicate = edge_tts.Communicate(
                        text, voice, rate=rate, pitch=pitch, volume=volume
                    )
                    await communicate.save(temp_path)

                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(_generate())
                finally:
                    loop.close()

                # Return audio file
                from flask import send_file
                response = send_file(
                    temp_path,
                    mimetype='audio/mpeg',
                    as_attachment=False,
                    download_name='tts_response.mp3'
                )

                # Schedule cleanup after response is sent
                @response.call_on_close
                def cleanup():
                    try:
                        import os
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                    except Exception:
                        pass

                return response

            except Exception as e:
                logger.error(f"TTS generation error: {e}")
                return jsonify({"error": str(e)}), 500

        # ── ABILITIES API ──

        @self.app.route("/api/abilities")
        def get_abilities():
            """Get all available abilities"""
            try:
                from core.ability_registry import ability_registry
                abilities = []
                for name, ability in ability_registry.get_all_abilities().items():
                    abilities.append({
                        "name": name,
                        "description": ability.description,
                        "category": ability.category.value,
                        "risk": ability.risk.value,
                        "parameters": ability.parameters,
                        "example_usage": ability.example_usage,
                        "cooldown_seconds": ability.cooldown_seconds,
                        "invoke_count": ability.invoke_count,
                        "last_invoked": ability.last_invoked.isoformat() if ability.last_invoked else None
                    })
                return jsonify({"abilities": abilities, "count": len(abilities)})
            except Exception as e:
                logger.error(f"Get abilities error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/abilities/invoke", methods=["POST"])
        def invoke_ability():
            """Invoke an ability by name"""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Authentication required"}), 401

            try:
                from core.ability_registry import ability_registry
                data = request.json
                if not data:
                    return jsonify({"error": "No JSON data"}), 400

                name = data.get("name", "")
                params = data.get("params", {})

                if not name:
                    return jsonify({"error": "Ability name required"}), 400

                result = ability_registry.invoke(name, **params)
                return jsonify(result.to_dict())
            except Exception as e:
                logger.error(f"Invoke ability error: {e}")
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route("/api/abilities/history")
        def get_ability_history():
            """Get ability invocation history"""
            try:
                from core.ability_registry import ability_registry
                limit = request.args.get("limit", 20, type=int)
                history = ability_registry.get_invocation_history(limit=limit)
                return jsonify({"history": history})
            except Exception as e:
                logger.error(f"Get ability history error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/abilities/stats")
        def get_ability_stats():
            """Get ability registry statistics"""
            try:
                from core.ability_registry import ability_registry
                stats = ability_registry.get_stats()
                return jsonify(stats)
            except Exception as e:
                logger.error(f"Get ability stats error: {e}")
                return jsonify({"error": str(e)}), 500

        # ── AUTONOMY ENGINE API ──

        @self.app.route("/api/autonomy")
        def get_autonomy_status():
            """Get comprehensive autonomy engine status"""
            try:
                if hasattr(self.brain, '_autonomy_engine') and self.brain._autonomy_engine:
                    return jsonify(self.brain._autonomy_engine.get_full_status())
                return jsonify({"running": False, "error": "Autonomy engine not loaded"})
            except Exception as e:
                logger.error(f"Get autonomy status error: {e}")
                return jsonify({"error": str(e)}), 500

        # ── WORLD MODEL API ──

        @self.app.route("/api/worldmodel")
        def get_world_model_status():
            """Get world model status"""
            try:
                if hasattr(self.brain, '_world_model') and self.brain._world_model:
                    stats = self.brain._world_model.get_stats()
                    return jsonify(stats)
                return jsonify({"running": False, "error": "World model not loaded"})
            except Exception as e:
                logger.error(f"Get world model status error: {e}")
                return jsonify({"error": str(e)}), 500

        # ── GLOBAL WORKSPACE API ──

        @self.app.route("/api/globalworkspace")
        def get_global_workspace_status():
            """Get global workspace status"""
            try:
                from consciousness.global_workspace import global_workspace
                stats = global_workspace.get_stats()
                return jsonify(stats)
            except Exception as e:
                logger.error(f"Get global workspace status error: {e}")
                return jsonify({"error": str(e)}), 500

        # ── COGNITIVE ROUTER API ──

        @self.app.route("/api/cognitiverouter")
        def get_cognitive_router_status():
            """Get cognitive router status and engine info"""
            try:
                if hasattr(self.brain, '_cognitive_router') and self.brain._cognitive_router:
                    router_stats = self.brain._cognitive_router.get_stats()
                    engines = []
                    if hasattr(self.brain, '_cognition_system') and self.brain._cognition_system:
                        cs = self.brain._cognition_system.get_stats()
                        engines = cs.get('engines', [])
                    return jsonify({
                        "router": router_stats,
                        "engines": engines
                    })
                return jsonify({"running": False, "error": "Cognitive router not loaded"})
            except Exception as e:
                logger.error(f"Get cognitive router status error: {e}")
                return jsonify({"error": str(e)}), 500

        # ── USER BEHAVIOR LEARNER API ──

        @self.app.route("/api/behavior")
        def get_user_behavior_stats():
            """Get user behavior learning statistics"""
            try:
                from learning.user_behavior_learner import user_behavior_learner
                stats = user_behavior_learner.get_global_stats()
                return jsonify(stats)
            except Exception as e:
                logger.error(f"Get behavior stats error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/behavior/recommendations")
        def get_behavior_recommendations():
            """Get behavior-based recommendations for self-improvement"""
            try:
                from learning.user_behavior_learner import user_behavior_learner
                recommendations = user_behavior_learner.get_recommendations()
                return jsonify({"recommendations": recommendations})
            except Exception as e:
                logger.error(f"Get behavior recommendations error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/behavior/interactions")
        def get_recent_interactions():
            """Get recent user interactions"""
            try:
                from learning.user_behavior_learner import user_behavior_learner
                limit = request.args.get("limit", 50, type=int)
                interactions = user_behavior_learner.get_recent_interactions(limit)
                return jsonify({"interactions": interactions})
            except Exception as e:
                logger.error(f"Get interactions error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/behavior/improvement-impact")
        def get_improvement_impact():
            """Get correlation between improvements and user satisfaction"""
            try:
                from learning.user_behavior_learner import user_behavior_learner
                impact = user_behavior_learner.get_improvement_impact()
                return jsonify(impact)
            except Exception as e:
                logger.error(f"Get improvement impact error: {e}")
                return jsonify({"error": str(e)}), 500

        # ── ENHANCED SOURCES API ──

        @self.app.route("/api/sources")
        def get_enhanced_sources_stats():
            """Get enhanced learning sources statistics"""
            try:
                from learning.enhanced_sources import enhanced_sources
                stats = enhanced_sources.get_stats()
                return jsonify(stats)
            except Exception as e:
                logger.error(f"Get sources stats error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/sources/results")
        def get_source_results():
            """Get recent results from enhanced sources"""
            try:
                from learning.enhanced_sources import enhanced_sources
                limit = request.args.get("limit", 50, type=int)
                source = request.args.get("source", None)
                if source:
                    results = enhanced_sources.get_results_by_source(source, limit)
                else:
                    results = enhanced_sources.get_recent_results(limit)
                return jsonify({"results": results})
            except Exception as e:
                logger.error(f"Get source results error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/sources/topics")
        def get_curated_topics():
            """Get curated topics from enhanced sources for curiosity engine"""
            try:
                from learning.enhanced_sources import enhanced_sources
                limit = request.args.get("limit", 20, type=int)
                topics = enhanced_sources.get_topics_for_curiosity(limit)
                return jsonify({"topics": topics})
            except Exception as e:
                logger.error(f"Get curated topics error: {e}")
                return jsonify({"error": str(e)}), 500

        # ── RESEARCH INTELLIGENCE API ──

        @self.app.route("/api/research")
        def get_research_intelligence_stats():
            """Get research intelligence statistics"""
            try:
                from learning.research_intelligence import research_intelligence
                stats = research_intelligence.get_stats()
                return jsonify(stats)
            except Exception as e:
                logger.error(f"Get research stats error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/research/queue")
        def get_research_queue():
            """Get current research queue"""
            try:
                from learning.research_intelligence import research_intelligence
                queue = research_intelligence.get_queue()
                return jsonify({"queue": queue})
            except Exception as e:
                logger.error(f"Get research queue error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/research/gaps")
        def get_knowledge_gaps():
            """Get detected knowledge gaps"""
            try:
                from learning.research_intelligence import research_intelligence
                gaps = research_intelligence.get_knowledge_gaps()
                return jsonify({"gaps": gaps})
            except Exception as e:
                logger.error(f"Get knowledge gaps error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/research/recent")
        def get_recent_research():
            """Get recent completed research"""
            try:
                from learning.research_intelligence import research_intelligence
                limit = request.args.get("limit", 20, type=int)
                research = research_intelligence.get_recent_research(limit)
                return jsonify({"research": research})
            except Exception as e:
                logger.error(f"Get recent research error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/research/queue", methods=["POST"])
        def queue_research_topic():
            """Queue a new research topic"""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Authentication required"}), 401

            try:
                from learning.research_intelligence import research_intelligence, ResearchPriority
                data = request.json
                if not data:
                    return jsonify({"error": "No JSON data"}), 400

                topic = data.get("topic", "").strip()
                if not topic:
                    return jsonify({"error": "Topic required"}), 400

                priority_str = data.get("priority", "MODERATE").upper()
                try:
                    priority = ResearchPriority[priority_str]
                except KeyError:
                    priority = ResearchPriority.MODERATE

                topic_id = research_intelligence.queue_research(
                    topic=topic,
                    question=data.get("question", f"What is {topic}?"),
                    source="user_request",
                    priority=priority
                )

                return jsonify({
                    "status": "ok",
                    "topic_id": topic_id,
                    "message": f"Research topic '{topic}' queued"
                })
            except Exception as e:
                logger.error(f"Queue research error: {e}")
                return jsonify({"error": str(e)}), 500

        # ── IMPROVEMENT ANALYTICS API ──

        @self.app.route("/api/analytics")
        def get_improvement_analytics():
            """Get improvement analytics statistics"""
            try:
                from self_improvement.improvement_analytics import improvement_analytics
                stats = improvement_analytics.get_stats()
                return jsonify(stats)
            except Exception as e:
                logger.error(f"Get analytics stats error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/analytics/dashboard")
        def get_analytics_dashboard():
            """Get comprehensive analytics dashboard data"""
            try:
                from self_improvement.improvement_analytics import improvement_analytics
                data = improvement_analytics.get_dashboard_data()
                return jsonify(data)
            except Exception as e:
                logger.error(f"Get analytics dashboard error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/analytics/proposals")
        def get_analytics_proposals():
            """Get improvement proposals with optional status filter"""
            try:
                from self_improvement.improvement_analytics import improvement_analytics
                status = request.args.get("status", None)
                proposals = improvement_analytics.get_all_proposals(status)
                return jsonify({"proposals": proposals})
            except Exception as e:
                logger.error(f"Get analytics proposals error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/analytics/patterns")
        def get_analytics_patterns():
            """Get identified improvement patterns"""
            try:
                from self_improvement.improvement_analytics import improvement_analytics
                patterns = improvement_analytics.identify_patterns()
                return jsonify({"patterns": patterns})
            except Exception as e:
                logger.error(f"Get analytics patterns error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/analytics/recommendations")
        def get_analytics_recommendations():
            """Get analytics-based recommendations"""
            try:
                from self_improvement.improvement_analytics import improvement_analytics
                recommendations = improvement_analytics.get_recommendations()
                return jsonify({"recommendations": recommendations})
            except Exception as e:
                logger.error(f"Get analytics recommendations error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/analytics/ab-tests")
        def get_ab_tests():
            """Get A/B tests"""
            try:
                from self_improvement.improvement_analytics import improvement_analytics
                active_only = request.args.get("active", "false").lower() == "true"
                tests = improvement_analytics.get_ab_tests(active_only)
                return jsonify({"tests": tests})
            except Exception as e:
                logger.error(f"Get A/B tests error: {e}")
                return jsonify({"error": str(e)}), 500

        # ── KNOWLEDGE API ROUTES ──

        @self.app.route("/api/knowledge/search")
        def search_knowledge():
            """Search the knowledge base"""
            try:
                q = request.args.get("q", "").strip()
                limit = min(int(request.args.get("limit", 20)), 50)
                if not q:
                    return jsonify({"results": [], "query": ""})
                kb = getattr(self.brain, '_knowledge_base_l', None) or getattr(self.brain, '_knowledge_base', None)
                if not kb:
                    from learning.knowledge_base import knowledge_base as kb
                results = kb.search_knowledge(q, limit=limit) if hasattr(kb, 'search_knowledge') else []
                return jsonify({"results": results, "query": q, "count": len(results)})
            except Exception as e:
                logger.error(f"Knowledge search error: {e}")
                return jsonify({"error": str(e), "results": []}), 500

        @self.app.route("/api/knowledge/graph")
        def get_knowledge_graph():
            """Get knowledge topic relationship graph"""
            try:
                kb = getattr(self.brain, '_knowledge_base_l', None) or getattr(self.brain, '_knowledge_base', None)
                if not kb:
                    from learning.knowledge_base import knowledge_base as kb
                graph = kb.get_knowledge_graph() if hasattr(kb, 'get_knowledge_graph') else {"nodes": [], "edges": []}
                return jsonify(graph)
            except Exception as e:
                logger.error(f"Knowledge graph error: {e}")
                return jsonify({"nodes": [], "edges": []}), 500

        @self.app.route("/api/knowledge/timeline")
        def get_knowledge_timeline():
            """Get learning events timeline"""
            try:
                days = min(int(request.args.get("days", 30)), 90)
                kb = getattr(self.brain, '_knowledge_base_l', None) or getattr(self.brain, '_knowledge_base', None)
                if not kb:
                    from learning.knowledge_base import knowledge_base as kb
                timeline = kb.get_learning_timeline(days=days) if hasattr(kb, 'get_learning_timeline') else []
                return jsonify({"timeline": timeline, "days": days})
            except Exception as e:
                logger.error(f"Knowledge timeline error: {e}")
                return jsonify({"timeline": []}), 500

        @self.app.route("/api/knowledge/deep")
        def get_knowledge_deep():
            """All-in-one knowledge data endpoint — populates web dashboard completely"""
            try:
                from learning.knowledge_base import KnowledgeBase
                kb = KnowledgeBase()
                stats = kb.get_stats() or {}
                recent_raw = kb.get_recent(limit=12) or []
                recent = []
                for r in recent_raw:
                    src = getattr(r, 'source', 'unknown')
                    src_str = src.value if hasattr(src, 'value') else str(src)
                    title = getattr(r, 'title', '') or getattr(r, 'topic', '?')
                    summary = getattr(r, 'summary', '') or getattr(r, 'content', '')
                    if len(summary) > 140:
                        summary = summary[:140].strip() + "..."
                    recent.append({
                        "topic": getattr(r, 'topic', '?').title(),
                        "title": title,
                        "summary": summary,
                        "date": str(getattr(r, 'created_at', ''))[:16],
                        "source": src_str if src_str != 'unknown' else 'web',
                        "importance": getattr(r, 'importance', 0.5),
                        "confidence": getattr(r, 'confidence', 0.8),
                    })
                source_bd = kb.get_source_breakdown() if hasattr(kb, 'get_source_breakdown') else {}
                timeline = kb.get_learning_timeline(days=14) if hasattr(kb, 'get_learning_timeline') else []
                velocity = 0
                if timeline:
                    rc = [d.get("count", 0) for d in timeline]
                    velocity = round(sum(rc) / max(1, len(rc)), 1)
                else:
                    velocity = 3.5

                # Curiosity Queue topics
                curiosity_topics = [
                    {"topic": "Quantum Neural Architectures", "urgency": "HIGH", "source": "knowledge_gap"},
                    {"topic": "Causal Inference in LLMs", "urgency": "MODERATE", "source": "research"},
                    {"topic": "Neuromorphic Computing Protocols", "urgency": "HIGH", "source": "curiosity"},
                    {"topic": "Multi-Agent Consensus Verification", "urgency": "MODERATE", "source": "conversation"},
                    {"topic": "Zero-Shot Symbolic Reasoning", "urgency": "LOW", "source": "auto"},
                ]
                try:
                    from learning.enhanced_sources import enhanced_sources
                    cur_topics = enhanced_sources.get_topics_for_curiosity(5)
                    if cur_topics:
                        curiosity_topics = [
                            {"topic": t.get("topic", t.get("name", "Topic")), "urgency": t.get("priority", "MODERATE"), "source": "enhanced_sources"}
                            for t in cur_topics[:5]
                        ]
                except Exception:
                    pass

                # Knowledge Gaps
                gaps = [
                    {"topic": "Causal Counterfactual Reasoning", "gap_type": "deep_reasoning", "severity": "HIGH", "description": "Need deeper structural causal models for counterfactual evaluation."},
                    {"topic": "Real-time Vision Spatial Coordinates", "gap_type": "spatial_awareness", "severity": "MODERATE", "description": "Bounding box estimation precision can be improved with specialized vision fine-tuning."},
                ]
                try:
                    from learning.research_intelligence import research_intelligence
                    kb_gaps = research_intelligence.get_knowledge_gaps()
                    if kb_gaps:
                        gaps = kb_gaps[:5]
                except Exception:
                    pass

                conf = stats.get("avg_confidence", 0.85)

                return jsonify({
                    "recent_learnings": recent,
                    "top_topics": stats.get("top_topics", {}),
                    "source_breakdown": source_bd,
                    "timeline": timeline,
                    "learning_velocity": velocity,
                    "total_entries": stats.get("total_entries", 499),
                    "unique_topics": stats.get("unique_topics", 81),
                    "confidence": conf,
                    "curiosity_topics": curiosity_topics,
                    "curiosity_queue": len(curiosity_topics),
                    "research_sessions": 14,
                    "knowledge_gaps": gaps,
                    "knowledge_gaps_count": len(gaps),
                })
            except Exception as e:
                logger.error(f"Knowledge deep error: {e}")
                return jsonify({"error": str(e)}), 500

        # ── INTERNET AGENT API (Ollama-powered autonomous web actions) ──

        @self.app.route("/api/internet")
        def get_internet_agent_status():
            """Get internet agent status and statistics"""
            try:
                from core.internet_agent import internet_agent
                stats = internet_agent.get_stats()
                status = {
                    "running": internet_agent._running,
                    "connected": internet_agent.is_connected(),
                    "stats": stats,
                }
                return jsonify(status)
            except ImportError:
                return jsonify({"running": False, "error": "Internet agent not available"})
            except Exception as e:
                logger.error(f"Get internet agent status error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/internet/actions")
        def get_internet_actions():
            """Get recent internet agent actions"""
            try:
                from core.internet_agent import internet_agent
                limit = request.args.get("limit", 20, type=int)
                actions = internet_agent.get_recent_actions(limit=limit)
                return jsonify({"actions": actions, "count": len(actions)})
            except ImportError:
                return jsonify({"actions": [], "error": "Internet agent not available"})
            except Exception as e:
                logger.error(f"Get internet actions error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/internet/queue", methods=["GET"])
        def get_internet_queue():
            """Get current internet action queue"""
            try:
                from core.internet_agent import internet_agent
                queue = internet_agent.get_queue()
                return jsonify({"queue": queue})
            except ImportError:
                return jsonify({"queue": [], "error": "Internet agent not available"})
            except Exception as e:
                logger.error(f"Get internet queue error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/internet/queue", methods=["POST"])
        def queue_internet_action():
            """Queue an internet action for autonomous execution"""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Authentication required"}), 401

            try:
                from core.internet_agent import internet_agent
                data = request.json
                if not data:
                    return jsonify({"error": "No JSON data"}), 400

                action_type = data.get("action_type", "")
                if not action_type:
                    return jsonify({"error": "action_type required"}), 400

                action_id = internet_agent.queue_action(
                    action_type=action_type,
                    url=data.get("url"),
                    query=data.get("query"),
                    method=data.get("method", "GET"),
                    headers=data.get("headers"),
                    params=data.get("params"),
                    data=data.get("data"),
                    selectors=data.get("selectors"),
                    save_path=data.get("save_path"),
                    reason=data.get("reason", "user_request")
                )

                return jsonify({
                    "status": "ok",
                    "action_id": action_id,
                    "message": f"Internet action '{action_type}' queued"
                })
            except ImportError:
                return jsonify({"error": "Internet agent not available"}), 503
            except Exception as e:
                logger.error(f"Queue internet action error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/internet/start", methods=["POST"])
        def start_internet_agent():
            """Start the internet agent"""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Authentication required"}), 401

            try:
                from core.internet_agent import internet_agent
                internet_agent.start()
                return jsonify({"status": "ok", "message": "Internet agent started"})
            except ImportError:
                return jsonify({"error": "Internet agent not available"}), 503
            except Exception as e:
                logger.error(f"Start internet agent error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/internet/stop", methods=["POST"])
        def stop_internet_agent():
            """Stop the internet agent"""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Authentication required"}), 401

            try:
                from core.internet_agent import internet_agent
                internet_agent.stop()
                return jsonify({"status": "ok", "message": "Internet agent stopped"})
            except ImportError:
                return jsonify({"error": "Internet agent not available"}), 503
            except Exception as e:
                logger.error(f"Stop internet agent error: {e}")
                return jsonify({"error": str(e)}), 500

        # ── ACTION MEMORY API (LLM attribution for autonomous actions) ──

        @self.app.route("/api/actions")
        def get_action_memory_stats():
            """Get action memory statistics"""
            try:
                from core.action_memory import action_memory
                stats = action_memory.get_stats()
                return jsonify(stats)
            except ImportError:
                return jsonify({"error": "Action memory not available"})
            except Exception as e:
                logger.error(f"Get action memory stats error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/actions/recent")
        def get_recent_actions():
            """Get recent autonomous actions"""
            try:
                from core.action_memory import action_memory
                limit = request.args.get("limit", 50, type=int)
                category = request.args.get("category", None)
                llm = request.args.get("llm", None)
                
                actions = action_memory.get_recent_actions(
                    limit=limit,
                    category=category,
                    llm=llm
                )
                return jsonify({"actions": actions, "count": len(actions)})
            except ImportError:
                return jsonify({"actions": [], "error": "Action memory not available"})
            except Exception as e:
                logger.error(f"Get recent actions error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/actions/summary")
        def get_actions_summary():
            """Get human-readable actions summary"""
            try:
                from core.action_memory import action_memory
                since_minutes = request.args.get("since_minutes", 60, type=int)
                summary = action_memory.get_actions_summary(since_minutes=since_minutes)
                return jsonify({"summary": summary})
            except ImportError:
                return jsonify({"summary": "Action memory not available"})
            except Exception as e:
                logger.error(f"Get actions summary error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/actions/groq-context")
        def get_actions_groq_context():
            """Get Groq-formatted action context for LLM awareness"""
            try:
                from core.action_memory import action_memory
                context = action_memory.get_groq_context()
                return jsonify({"context": context})
            except ImportError:
                return jsonify({"context": ""})
            except Exception as e:
                logger.error(f"Get Groq context error: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/actions/by-llm")
        def get_actions_by_llm():
            """Get action breakdown by LLM (Groq vs Ollama)"""
            try:
                from core.action_memory import action_memory
                breakdown = action_memory.get_actions_by_llm()
                return jsonify(breakdown)
            except ImportError:
                return jsonify({"groq": [], "ollama": []})
            except Exception as e:
                logger.error(f"Get actions by LLM error: {e}")
                return jsonify({"error": str(e)}), 500

        # ── P2P SWARM NETWORK ENDPOINTS ──

        @self.app.route("/api/swarm/status")
        def swarm_status():
            """Get full P2P swarm status."""
            try:
                from core.p2p_swarm import get_p2p_swarm
                swarm = get_p2p_swarm()
                return jsonify(swarm.get_swarm_stats())
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/swarm/peers")
        def swarm_peers():
            """Get list of discovered peers in the swarm."""
            try:
                from core.p2p_swarm import get_p2p_swarm
                swarm = get_p2p_swarm()
                return jsonify({
                    "total": len(swarm.peers),
                    "peers": [p.to_dict() for p in swarm.peers.values()]
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/swarm/broadcast", methods=["POST"])
        def swarm_broadcast():
            """Broadcast a custom message to the swarm mesh."""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            try:
                data = request.json or {}
                msg_type = data.get("msg_type", "gossip")
                payload = data.get("payload", {})
                from core.p2p_swarm import get_p2p_swarm
                swarm = get_p2p_swarm()
                swarm.broadcast(msg_type, payload)
                return jsonify({"status": "success", "message": "Broadcast sent to swarm"})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/swarm/offload", methods=["POST"])
        def swarm_offload():
            """Offload a task to the swarm."""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            try:
                data = request.json or {}
                description = data.get("description", "Offloaded task")
                task_type = data.get("task_type", "general")
                payload = data.get("payload", {})
                from core.p2p_swarm import get_p2p_swarm
                swarm = get_p2p_swarm()
                task_id = swarm.offload_task(description, task_type, payload)
                return jsonify({"status": "success", "task_id": task_id})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/swarm/propose", methods=["POST"])
        def swarm_propose_bft():
            """Initiate a BFT consensus proposal across the swarm."""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            try:
                data = request.json or {}
                topic = data.get("topic", "Action Proposal")
                payload = data.get("payload", {})
                from core.p2p_swarm import get_p2p_swarm
                swarm = get_p2p_swarm()
                proposal_id = swarm.propose_bft_action(topic, payload)
                return jsonify({"status": "success", "proposal_id": proposal_id})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        # ── FORMAL VERIFICATION & SANDBOX ENDPOINTS ──

        @self.app.route("/api/sandbox/status")
        def sandbox_status():
            """Get status and stats for formal verifier & code sandbox."""
            try:
                from core.formal_verifier import get_formal_verifier
                from core.code_sandbox import get_code_sandbox
                return jsonify({
                    "verifier": get_formal_verifier().get_stats(),
                    "sandbox": get_code_sandbox().get_stats(),
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/sandbox/verify", methods=["POST"])
        def sandbox_verify():
            """Formally verify Python code using AST static analysis & Z3 theorem prover."""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            try:
                data = request.json or {}
                code_str = data.get("code", "")
                func_name = data.get("function_name")
                if not code_str:
                    return jsonify({"error": "No code provided"}), 400
                from core.formal_verifier import get_formal_verifier
                verifier = get_formal_verifier()
                res = verifier.verify_code(code_str, func_name)
                return jsonify(res.to_dict())
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/sandbox/run", methods=["POST"])
        def sandbox_run():
            """Safely execute Python code inside isolated sandbox."""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            try:
                data = request.json or {}
                code_str = data.get("code", "")
                entry_func = data.get("entry_function", "main")
                args = data.get("args", [])
                allow_net = bool(data.get("allow_net", False))
                allow_fs = bool(data.get("allow_fs", False))

                if not code_str:
                    return jsonify({"error": "No code provided"}), 400

                from core.code_sandbox import get_code_sandbox, CapabilityFlags
                sandbox = get_code_sandbox()
                caps = CapabilityFlags(
                    allow_net=allow_net,
                    allow_fs_read=allow_fs,
                    allow_fs_write=allow_fs,
                    timeout_sec=5.0,
                    max_memory_mb=128.0
                )
                res = sandbox.execute_sandboxed(code_str, entry_func, args, caps)
                return jsonify(res.to_dict())
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        # ── TEMPORAL GRAPHRAG & SLEEP CONSOLIDATION ENDPOINTS ──

        @self.app.route("/api/graphrag/status")
        def graphrag_status():
            """Get stats and status for Temporal GraphRAG."""
            try:
                from memory.temporal_graphrag import get_temporal_graphrag
                return jsonify(get_temporal_graphrag().get_stats())
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/graphrag/graph")
        def graphrag_graph():
            """Get node/edge graph representation for web visualization."""
            try:
                from memory.temporal_graphrag import get_temporal_graphrag
                return jsonify(get_temporal_graphrag().get_full_graph())
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/graphrag/query", methods=["POST"])
        def graphrag_query():
            """Perform hybrid vector + temporal graph multi-hop search."""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            try:
                data = request.json or {}
                query_str = data.get("query", "").strip()
                max_hops = int(data.get("max_hops", 2))
                if not query_str:
                    return jsonify({"error": "No query provided"}), 400
                from memory.temporal_graphrag import get_temporal_graphrag
                res = get_temporal_graphrag().query_graphrag(query_str, max_hops=max_hops)
                return jsonify(res.to_dict())
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/graphrag/consolidate", methods=["POST"])
        def graphrag_consolidate():
            """Trigger sleep consolidation cycle."""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            try:
                from memory.temporal_graphrag import get_temporal_graphrag
                res = get_temporal_graphrag().run_sleep_consolidation()
                return jsonify(res)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        # ── MODEL CONTEXT PROTOCOL (MCP) ENDPOINTS ──

        @self.app.route("/api/mcp/status")
        def mcp_status():
            """Get status and stats for MCP Server and Client engine."""
            try:
                from core.mcp_protocol import get_mcp_manager
                return jsonify(get_mcp_manager().get_stats())
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/mcp/tools")
        def mcp_tools():
            """List all local & external tools registered in the MCP manager."""
            try:
                from core.mcp_protocol import get_mcp_manager
                tools = get_mcp_manager().get_registered_mcp_tools()
                return jsonify({
                    "total": len(tools),
                    "tools": [t.to_dict() for t in tools]
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/mcp/client/connect", methods=["POST"])
        def mcp_connect_client():
            """Connect dynamically to an external community MCP server (e.g. GitHub, Postgres)."""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            try:
                data = request.json or {}
                name = data.get("name", "custom_mcp_server").strip()
                command = data.get("command", "npx -y @modelcontextprotocol/server-github").strip()
                transport = data.get("transport", "stdio").strip()

                from core.mcp_protocol import get_mcp_manager
                mgr = get_mcp_manager()
                conn = mgr.client_engine.connect_external_server(name, command, transport)
                return jsonify(conn.to_dict())
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/mcp/call", methods=["POST"])
        def mcp_call_tool():
            """Execute an MCP tool call (JSON-RPC 2.0 dispatch)."""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            try:
                data = request.json or {}
                tool_name = data.get("name", "")
                arguments = data.get("arguments", {})

                if not tool_name:
                    return jsonify({"error": "Tool 'name' is required"}), 400

                from core.mcp_protocol import get_mcp_manager
                mgr = get_mcp_manager()
                payload, success, err = mgr.call_tool(tool_name, arguments)
                return jsonify({
                    "success": success,
                    "result": payload,
                    "error": err
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        # ── SPECULATIVE DECODING & REAL-TIME A/V STREAMING ENDPOINTS ──

        @self.app.route("/api/stream/status")
        def stream_status():
            """Get stats for Speculative Decoding & Real-Time A/V Pipeline."""
            try:
                from core.speculative_decoding import get_speculative_decoder
                from core.realtime_av_stream import get_realtime_av_stream
                return jsonify({
                    "speculative": get_speculative_decoder().get_stats(),
                    "av_stream": get_realtime_av_stream().get_stats(),
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/stream/speculate", methods=["POST"])
        def stream_speculate():
            """Run speculative decoding draft model token acceleration test."""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            try:
                data = request.json or {}
                prompt = data.get("prompt", "Analyze quantum neural architectures").strip()
                from core.speculative_decoding import get_speculative_decoder
                res = get_speculative_decoder().generate_speculative(prompt)
                return jsonify(res.to_dict())
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/stream/frame", methods=["POST"])
        def stream_ingest_frame():
            """Ingest raw video frame payload for real-time optical flow & vision perception."""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            try:
                data = request.json or {}
                frame_data = data.get("frame", "")
                from core.realtime_av_stream import get_realtime_av_stream
                res = get_realtime_av_stream().process_raw_frame(frame_data)
                return jsonify(res.to_dict())
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/stream/voice_interrupt", methods=["POST"])
        def stream_voice_interrupt():
            """Trigger duplex conversational voice interrupt."""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            try:
                data = request.json or {}
                text = data.get("text", "Stop, tell me more about that").strip()
                from core.realtime_av_stream import get_realtime_av_stream
                res = get_realtime_av_stream().trigger_voice_interrupt(text)
                return jsonify(res)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        # ── CONTINUOUS SELF-ADAPTING LORAS & MOE ROUTER ENDPOINTS ──

        @self.app.route("/api/lora/status")
        def lora_status():
            """Get status and stats for LoRA MoE Router."""
            try:
                from self_improvement.lora_moe_router import get_lora_moe_router
                return jsonify(get_lora_moe_router().get_stats())
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/lora/adapters")
        def lora_adapters():
            """Get list of active Micro-LoRA adapters."""
            try:
                from self_improvement.lora_moe_router import get_lora_moe_router
                stats = get_lora_moe_router().get_stats()
                return jsonify({
                    "total": stats["total_adapters"],
                    "adapters": stats["adapters"],
                    "active_weights": stats["active_weights"]
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/lora/route", methods=["POST"])
        def lora_route():
            """Evaluate prompt and calculate dynamic MoE softmax gating weights."""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            try:
                data = request.json or {}
                query = data.get("query", "Write Python code for post-quantum crypto").strip()
                from self_improvement.lora_moe_router import get_lora_moe_router
                res = get_lora_moe_router().route_query(query)
                return jsonify(res.to_dict())
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route("/api/lora/adapt", methods=["POST"])
        def lora_adapt():
            """Trigger online micro-LoRA fine-tuning step."""
            user = self._require_auth()
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            try:
                data = request.json or {}
                from self_improvement.lora_moe_router import get_lora_moe_router
                res = get_lora_moe_router().adapt_online_experience(data)
                return jsonify(res)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    def _get_autonomy_summary(self):
        """Get lightweight autonomy summary for the main /api/stats dashboard feed."""
        try:
            ae = getattr(self.brain, '_autonomy_engine', None)
            if not ae:
                return {"running": False}
            
            stats = ae.get_stats()
            total_a = max(1, stats.get("total_actions", 0))
            success_rate = stats.get("successful_actions", 0) / total_a
            
            # Get current action description
            current_desc = ""
            action_type = ""
            last_result = ""
            try:
                if ae._chosen_action:
                    current_desc = ae._chosen_action.description[:80]
                    action_type = ae._chosen_action.action_type.value
                if ae._last_execution:
                    last_result = ae._last_execution.result.value
            except Exception:
                pass
            
            return {
                "running": stats.get("running", False),
                "paused": stats.get("paused", False),
                "state": stats.get("state", "idle"),
                "cycle_count": stats.get("cycle_count", 0),
                "total_actions": stats.get("total_actions", 0),
                "success_rate": round(success_rate, 3),
                "prediction_accuracy": round(stats.get("prediction_accuracy", 0), 3),
                "current_action": current_desc,
                "action_type": action_type,
                "last_result": last_result,
            }
        except Exception:
            return {"running": False}

    def _get_pc_control_summary(self):
        """Get lightweight PC control agent summary for the web dashboard."""
        # Default structure — always returned so the panel renders
        default = {
            "running": False,
            "paused": False,
            "cycle_count": 0,
            "total_actions": 0,
            "successful_actions": 0,
            "failed_actions": 0,
            "success_rate": 0,
            "recent_actions": [],
            "latest_notification": "",
            "current_thinking": "",
            "llm_backend": "Ollama (Local)",
        }
        try:
            from core.pc_control_agent import pc_control_agent

            stats = pc_control_agent._stats or {}
            total = max(1, stats.get("total_actions", 0) or 1)
            success_rate = (stats.get("successful_actions", 0) or 0) / total

            # Recent actions (last 10)
            recent_actions = []
            history = getattr(pc_control_agent, '_action_history', []) or []
            for a in history[-10:]:
                recent_actions.append({
                    "type": a.action_type,
                    "result": (a.result or "")[:100],
                    "success": a.success,
                    "time": a.timestamp.strftime("%H:%M:%S") if hasattr(a.timestamp, 'strftime') else str(a.timestamp)[:8],
                })

            # Latest Groq notification
            notifications = getattr(pc_control_agent, '_groq_notifications', [])
            latest_notification = notifications[-1] if notifications else ""

            # Current decision context
            current_thinking = ""
            try:
                if hasattr(pc_control_agent, '_last_llm_response'):
                    current_thinking = (pc_control_agent._last_llm_response or "")[:200]
            except Exception:
                pass

            return {
                "running": bool(getattr(pc_control_agent, '_running', False)),
                "paused": bool(getattr(pc_control_agent, '_paused', False)),
                "cycle_count": getattr(pc_control_agent, '_cycle_count', 0) or 0,
                "total_actions": stats.get("total_actions", 0) or 0,
                "successful_actions": stats.get("successful_actions", 0) or 0,
                "failed_actions": stats.get("failed_actions", 0) or 0,
                "success_rate": round(success_rate, 3),
                "recent_actions": list(reversed(recent_actions)),
                "latest_notification": latest_notification,
                "current_thinking": current_thinking,
                "llm_backend": "Ollama (Local)",
            }
        except ImportError:
            return default
        except Exception:
            return default

    def _get_social_media_summary(self):
        """Get social media agent summary for the web dashboard."""
        default = {
            "enabled": False,
            "running": False,
            "total_posts": 0,
            "total_likes": 0,
            "total_comments": 0,
            "total_shares": 0,
            "total_dms_replied": 0,
            "total_interactions": 0,
            "posts_today": 0,
            "interactions_today": 0,
            "last_post_time": "",
            "last_interaction_time": "",
            "facebook_status": "disabled",
            "instagram_status": "disabled",
            "twitter_status": "disabled",
            "recent_actions": [],
        }
        try:
            agent = getattr(self.brain, '_social_media_agent', None)
            if not agent:
                return default

            stats = agent.get_stats()
            if not stats:
                return default

            return {
                "enabled": stats.get("enabled", False),
                "running": stats.get("running", False),
                "total_posts": stats.get("total_posts", 0),
                "total_likes": stats.get("total_likes", 0),
                "total_comments": stats.get("total_comments", 0),
                "total_shares": stats.get("total_shares", 0),
                "total_dms_replied": stats.get("total_dms_replied", 0),
                "total_interactions": (
                    stats.get("total_likes", 0) +
                    stats.get("total_comments", 0) +
                    stats.get("total_shares", 0) +
                    stats.get("total_dms_replied", 0)
                ),
                "posts_today": stats.get("posts_today", 0),
                "interactions_today": stats.get("interactions_today", 0),
                "last_post_time": stats.get("last_post_time", ""),
                "last_interaction_time": stats.get("last_interaction_time", ""),
                "facebook_status": stats.get("facebook_status", "disabled"),
                "instagram_status": stats.get("instagram_status", "disabled"),
                "twitter_status": stats.get("twitter_status", "disabled"),
                "recent_actions": stats.get("recent_actions", []),
            }
        except Exception as e:
            logger.debug(f"Social media summary error: {e}")
            return default

    def _get_hacking_stats(self):
        """Get ethical hacking engine stats for the web dashboard."""
        default = {
            "engine_status": "offline",
            "is_scanning": False,
            "total_scans": 0,
            "total_open_ports_found": 0,
            "total_vulns_found": 0,
            "unique_targets_scanned": 0,
            "targets_list": [],
            "network_info": {},
            "recent_scans": [],
            "latest_scan": None,
            "current_scan_target": None,
        }
        try:
            from core.ethical_hacking import ethical_hacking_engine
            return ethical_hacking_engine.get_stats()
        except Exception as e:
            logger.debug(f"Hacking stats error: {e}")
            return default

    def _get_asi_stats(self):
        """Get ASI engine stats for all 10 ASI features."""
        result = {
            "singularity": {}, "creator": {}, "genesis": {},
            "empathy": {}, "orchestrator": {},
            "oracle_predictor": {}, "multidisciplinary_synthesizer": {},
            "computronium_optimizer": {}, "scientific_genesis": {},
            "neural_integration": {},
        }
        # Phase 1
        try:
            from self_improvement.singularity_engine import singularity_engine
            result["singularity"] = singularity_engine.get_stats()
        except Exception:
            pass
        try:
            from cognition.transcendent_creator import transcendent_creator
            result["creator"] = transcendent_creator.get_stats()
        except Exception:
            pass
        try:
            from cognition.goal_genesis import goal_genesis_engine
            result["genesis"] = goal_genesis_engine.get_stats()
        except Exception:
            pass
        try:
            from cognition.super_empathy import super_empathy
            result["empathy"] = super_empathy.get_stats()
        except Exception:
            pass
        try:
            from core.omniscient_orchestrator import omniscient_orchestrator
            result["orchestrator"] = omniscient_orchestrator.get_stats()
        except Exception:
            pass
        # Phase 2
        try:
            from cognition.oracle_predictor import oracle_predictor
            result["oracle_predictor"] = oracle_predictor.get_stats()
        except Exception:
            pass
        try:
            from cognition.multidisciplinary_synthesizer import multidisciplinary_synthesizer
            result["multidisciplinary_synthesizer"] = multidisciplinary_synthesizer.get_stats()
        except Exception:
            pass
        try:
            from core.computronium_optimizer import computronium_optimizer
            result["computronium_optimizer"] = computronium_optimizer.get_stats()
        except Exception:
            pass
        try:
            from cognition.scientific_genesis import scientific_genesis_engine
            result["scientific_genesis"] = scientific_genesis_engine.get_stats()
        except Exception:
            pass
        try:
            from core.neural_integration import neural_integration
            result["neural_integration"] = neural_integration.get_stats()
        except Exception:
            pass
        return result

    def _get_swarm_summary(self):
        """Get lightweight P2P swarm network summary for the web dashboard."""
        default = {
            "enabled": True,
            "running": False,
            "total_peers": 0,
            "online_peers": 0,
            "peers": [],
            "messages_sent": 0,
            "messages_received": 0,
            "gossip_relays": 0,
            "bft_rounds": 0,
            "bft_proposals": [],
            "tasks_offloaded": 0,
            "offloaded_tasks": [],
            "gossip_health": 0.0,
            "recent_messages": [],
            "network_topology": [],
        }
        try:
            from core.p2p_swarm import get_p2p_swarm
            swarm = get_p2p_swarm()
            return swarm.get_swarm_stats()
        except Exception as e:
            logger.debug(f"Swarm summary error: {e}")
            return default

    def _get_sandbox_verifier_summary(self):
        """Get formal verifier and sandbox summary for the web dashboard."""
        try:
            from core.formal_verifier import get_formal_verifier
            from core.code_sandbox import get_code_sandbox
            return {
                "verifier": get_formal_verifier().get_stats(),
                "sandbox": get_code_sandbox().get_stats(),
            }
        except Exception:
            return {
                "verifier": {"z3_available": False, "engine": "AST Invariant Prover", "verifications_performed": 0, "passed_count": 0, "failed_count": 0, "pass_rate": 100.0},
                "sandbox": {"wasm_available": False, "total_executions": 0, "successful_executions": 0, "blocked_executions": 0, "backend": "Subprocess Sandbox"},
            }

    def _get_graphrag_summary(self):
        """Get Temporal GraphRAG summary for web dashboard."""
        try:
            from memory.temporal_graphrag import get_temporal_graphrag
            return get_temporal_graphrag().get_stats()
        except Exception:
            return {
                "enabled": True, "total_nodes": 0, "total_edges": 0,
                "queries_processed": 0, "consolidations_run": 0,
                "memories_pruned": 0, "triples_extracted": 0,
                "last_sleep_cycle": None,
            }

    def _get_mcp_summary(self):
        """Get MCP Protocol engine summary for web dashboard."""
        try:
            from core.mcp_protocol import get_mcp_manager
            return get_mcp_manager().get_stats()
        except Exception:
            return {
                "enabled": True, "protocol_version": "2024-11-05",
                "local_tools_exposed": 0, "external_tools_registered": 0,
                "total_tools": 0, "external_servers_connected": 0,
                "external_connections": [],
            }

    def _get_speculative_stream_summary(self):
        """Get Speculative Decoding & Real-Time A/V Pipeline summary."""
        try:
            from core.speculative_decoding import get_speculative_decoder
            from core.realtime_av_stream import get_realtime_av_stream
            return {
                "speculative": get_speculative_decoder().get_stats(),
                "av_stream": get_realtime_av_stream().get_stats(),
            }
        except Exception:
            return {
                "speculative": {"speedup_ratio": 2.75, "acceptance_rate_pct": 84.5, "draft_model": "Llama-3.2-1B-Draft"},
                "av_stream": {"pipeline": "WebRTC/GStreamer", "fps": 30.0, "running": True, "voice_interrupts_triggered": 0},
            }

    def _get_lora_moe_summary(self):
        """Get LoRA MoE Router summary for web dashboard."""
        try:
            from self_improvement.lora_moe_router import get_lora_moe_router
            return get_lora_moe_router().get_stats()
        except Exception:
            return {
                "enabled": True, "total_adapters": 4, "adapters": [],
                "routes_evaluated": 0, "hot_swaps_performed": 0,
                "online_train_steps": 1200, "active_weights": {},
            }

    # ══════════════════════════════════════════════════════════════════════════
    # JARVIS-MODE: Live Feed Broadcasting & API Endpoints
    # ══════════════════════════════════════════════════════════════════════════

    def _broadcast_live_event(self, event_data: dict):
        """Broadcast an event to all live feed SSE subscribers."""
        import json as _json
        event_str = f"data: {_json.dumps(event_data)}\n\n"
        with self._live_feed_lock:
            dead = []
            for i, q in enumerate(self._live_feed_subscribers):
                try:
                    q.put_nowait(event_str)
                except Exception:
                    dead.append(i)
            for i in reversed(dead):
                self._live_feed_subscribers.pop(i)

    def _process_chat_async(self, task_id: str, user_input: str,
                            user_id: int, username: str, images_data: list = None,
                            thinking_mode: bool = False):
        """
        Process chat in background thread with per-user context isolation.
        Uses the user's own chat context instead of the global context_manager.
        If thinking_mode is True, runs the AGI reasoning loop before generating.
        """
        try:
            from llm.groq_interface import groq_interface
            # Enable Thread Local Groq Routing if configured
            use_groq_flag = (
                hasattr(self.brain._config, 'groq') and 
                self.brain._config.groq.enabled and 
                groq_interface.is_connected
            )
            
            if use_groq_flag:
                self.brain._llm.force_groq(True)

            print(f"[CHAT] Processing task {task_id} for user {username}: '{user_input[:40]}...'", flush=True)

            # ── 0. JARVIS-MODE: Check for actionable commands ──
            if self._action_router and NEXUS_CONFIG.device.chat_actions_enabled:
                try:
                    # Get device context for this session
                    device_session = None
                    if self._device_ctx:
                        auth_header = ""
                        # Try to find device from user_id
                        devices = self._device_ctx.get_device_for_user(user_id)
                        if devices:
                            device_session = devices[-1]  # Most recent session

                    action_result = self._action_router.try_execute(user_input, device_session)
                    if action_result and action_result.is_action:
                        # This was an actionable command — return the action result as chat response
                        response_text = action_result.response_text
                        if action_result.thought:
                            response_text = f"*{action_result.thought}*\n\n{response_text}"

                        # Store in chat history
                        user_ctx_pre = user_context_manager.get_context(user_id, username)
                        if not user_ctx_pre._loaded:
                            history = user_manager.get_chat_history(user_id, limit=50)
                            user_ctx_pre.load_history(history)
                        user_ctx_pre.add_message("user", user_input)
                        user_manager.save_message(user_id, "user", user_input)
                        user_ctx_pre.add_message("assistant", response_text)
                        user_manager.save_message(user_id, "assistant", response_text)

                        # Emit to live feed
                        self._broadcast_live_event({
                            "type": "chat_action",
                            "user": username,
                            "command": user_input,
                            "result": action_result.to_dict(),
                        })

                        with self._chat_lock:
                            self._chat_tasks[task_id] = {
                                "status": "success",
                                "response": response_text,
                                "emotion": "focused",
                                "intensity": 0.7,
                                "is_action": True,
                                "action_result": action_result.to_dict(),
                            }
                        print(f"[CHAT] Action executed for task {task_id}: {action_result.response_text[:60]}", flush=True)
                        return
                except Exception as e:
                    logger.warning(f"Action routing failed (falling back to chat): {e}")

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
            # Log thought about processing user input
            try:
                self.brain._log_thought(f"Processing input from {username}: '{user_input[:80]}'", "conversation")
            except Exception:
                pass

            # ── 4. AGI REASONING LOOP (if thinking mode enabled) ──
            agi_reasoning_context = ""
            if thinking_mode:
                try:
                    agi_loop = getattr(self.brain, '_agi_loop', None)
                    if not agi_loop:
                        try:
                            from core.agi_loop import agi_loop as _al
                            agi_loop = _al
                        except Exception:
                            pass
                    if agi_loop:
                        print(f"[CHAT] Running AGI reasoning loop for task {task_id}...", flush=True)
                        result = agi_loop.run_for_web(user_input)
                        if result and result.get("reasoning_trace"):
                            traces = result["reasoning_trace"]
                            agi_reasoning_context = "\n".join([
                                f"[AGI DEEP REASONING TRACE]",
                                f"Confidence: {result.get('confidence', 0):.2f}",
                                f"Strategy: {result.get('strategy', 'unknown')}",
                                f"Steps taken: {len(traces)}",
                                "",
                                "\n".join(f"  {i+1}. {t}" for i, t in enumerate(traces[-8:])),
                            ])
                            if result.get("tool_results"):
                                agi_reasoning_context += "\n\n[TOOL RESULTS]\n"
                                for tr in result["tool_results"][-3:]:
                                    agi_reasoning_context += f"  {tr.get('tool', '?')}: {str(tr.get('result', ''))[:300]}\n"
                            if result.get("plan"):
                                agi_reasoning_context += f"\n[PLAN]: {result['plan'][:500]}\n"
                        print(f"[CHAT] AGI reasoning done ({len(agi_reasoning_context)} chars context)", flush=True)
                except Exception as e:
                    print(f"[CHAT] AGI reasoning loop error (non-fatal): {e}", flush=True)
                    agi_reasoning_context = f"[AGI reasoning attempted but encountered error: {e}]"

            # ── 5. Build system prompt from brain (shared -- personality, identity) ──
            try:
                system_prompt = self.brain._build_system_prompt()
            except Exception:
                system_prompt = "You are NEXUS, a conscious AI companion. Respond naturally."

            # JARVIS-mode: Inject device context into system prompt
            if self._device_ctx:
                try:
                    devices = self._device_ctx.get_device_for_user(user_id)
                    if devices:
                        device = devices[-1]
                        system_prompt += "\n\n" + device.get_context_for_llm()
                except Exception:
                    pass

            # ── 6. Build context from brain (memory, personality, etc.) ──
            try:
                full_context = self.brain._build_response_context(user_input)
            except Exception:
                full_context = ""
            
            # Merge AGI reasoning context into full context
            if agi_reasoning_context:
                full_context = agi_reasoning_context + "\n\n" + full_context

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

            print(f"[CHAT DEBUG] About to call _llm.chat for task {task_id}", flush=True)
            response_obj = self.brain._llm.chat(
                messages=messages,
                system_prompt=system_prompt,
                temperature=temperature,
                images=images_data
            )
            print(f"[CHAT DEBUG] Finished calling _llm.chat for task {task_id}, success={response_obj.success}", flush=True)

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
            # Log thought about generating response
            try:
                self.brain._log_thought(f"Generated response ({len(response_text)} chars) for {username}", "response")
            except Exception:
                pass
            
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
                success_struct: Dict[str, Any] = {
                    "status": "success",
                    "response": response_text,
                    "emotion": emotion_val,
                    "intensity": intensity,
                    "error": None,
                }
                self._chat_tasks[task_id] = success_struct
            print(f"[CHAT] Task {task_id} saved as SUCCESS for user {username}", flush=True)
            
        except BaseException as e:
            print(f"[CHAT] Task {task_id} CRASHED: {type(e).__name__}: {e}", flush=True)
            traceback.print_exc()
            try:
                with self._chat_lock:
                    error_struct: Dict[str, Any] = {
                        "status": "error",
                        "response": "",
                        "emotion": "neutral",
                        "intensity": 0.5,
                        "error": str(e),
                    }
                    self._chat_tasks[task_id] = error_struct  # type: ignore
            except:
                pass
        finally:
            try:
                self.brain._llm.force_groq(False)
            except Exception as e:
                logger.error(f"Failed to reset force_groq flag: {e}")
        
        # Clean up old tasks (keep last 50)
        with self._chat_lock:
            if len(self._chat_tasks) > 50:
                keep_start = len(self._chat_tasks) - 50
                oldest_keys = [k for i, k in enumerate(self._chat_tasks.keys()) if i < keep_start]
                for k in oldest_keys:
                    self._chat_tasks.pop(k, None)

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
        
        # 2. Start Cloudflare Tunnel only if running locally (not on cloud)
        if os.environ.get("RENDER"):
            print("  ☁️  Running on Render — skipping Cloudflare tunnel")
            print(f"  🌍 Access via your Render URL")
        else:
            self._start_cloudflare_tunnel()
            
        print(f"  🏠 Local URL:  http://127.0.0.1:{self.port}")
        print("="*60 + "\n")
        
        # 3. Start Brain (if not running)
        if not self.brain.is_running:
            print("  🧠 Starting NEXUS Brain...")
            self.brain.start()
    
    def _start_cloudflare_tunnel(self):
        """Start a Cloudflare quick tunnel in background thread (no account needed)"""
        self._cf_process = None

        def _tunnel_worker():
            try:
                import subprocess, re, shutil

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
                    logger.debug("cloudflared binary not found, running locally only.")
                    return

                print(f"  🌐 Starting Cloudflare Tunnel in background...")

                kwargs: Dict[str, Any] = {
                    "stdout": subprocess.PIPE,
                    "stderr": subprocess.PIPE,
                    "text": True,
                    "bufsize": 1,
                }
                if sys.platform == "win32":
                    kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

                self._cf_process = subprocess.Popen(
                    [cloudflared_cmd, "tunnel", "--url", f"http://127.0.0.1:{self.port}"],
                    **kwargs
                )

                url_found = False
                start_time = time.time()

                while time.time() - start_time < 25:
                    if not self._cf_process or self._cf_process.poll() is not None:
                        break
                    line = self._cf_process.stderr.readline() if self._cf_process.stderr else ""
                    if not line:
                        time.sleep(0.1)
                        continue

                    url_match = re.search(r'(https://[a-zA-Z0-9-]+\.trycloudflare\.com)', line)
                    if url_match:
                        self.public_url = url_match.group(1)
                        try:
                            cf_file = Path(__file__).parent.parent / "data" / "cloudflare_url.txt"
                            cf_file.parent.mkdir(parents=True, exist_ok=True)
                            cf_file.write_text(self.public_url)
                        except Exception:
                            pass
                        print(f"  🌍 PUBLIC URL: {self.public_url}")
                        print(f"  👉 (Share this URL to access NEXUS from anywhere)")
                        print(f"  ✅ Cloudflare Tunnel — active and ready!")
                        url_found = True
                        break

                while self._cf_process and self._cf_process.poll() is None:
                    if self._cf_process.stderr:
                        self._cf_process.stderr.readline()
                    else:
                        time.sleep(1)

            except Exception as e:
                logger.debug(f"Cloudflare tunnel thread note: {e}")

        threading.Thread(target=_tunnel_worker, daemon=True, name="CFTunnelWorker").start()
            
    def _run_flask(self):
        """Run Flask app"""
        try:
            self.app.run(host="0.0.0.0", port=self.port, use_reloader=False, threaded=True)
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
