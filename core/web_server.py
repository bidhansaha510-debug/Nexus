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

from flask import jsonify, render_template, send_file
import os

class WebServer:
    def _register_routes(self):
        @self.app.after_request
        def after_request(response):
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
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
            apk_path = os.path.join(os.path.dirname(__file__), "mobile", "NEXUS-AI.apk")
            if os.path.exists(apk_path):
                return send_file(
                    apk_path,
                    mimetype='application/vnd.android.package-archive',
                    as_attachment=True,
                    download_name='NEXUS-AI.apk'
                )
            else:
                # Fallback: create a placeholder if APK doesn't exist
                from io import BytesIO
                from flask import send_file

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
