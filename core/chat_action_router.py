"""
NEXUS AI — Chat Action Router
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Intercepts chat messages, detects actionable commands, generates
action plans, and routes execution to the correct device.

"Open notepad" → detect intent → plan actions → execute on host PC
"Take a screenshot" from Android → execute via ADB on that phone
"""

import json
import re
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import sys

from config import NEXUS_CONFIG
from utils.logger import get_logger

logger = get_logger("chat_action_router")

# ═══════════════════════════════════════════════════════════════════════════════
# ACTION RESULT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ActionResult:
    """Result of executing a chat-driven action."""
    success: bool = False
    is_action: bool = False          # Was this an actionable command?
    thought: str = ""                # NEXUS's reasoning
    actions_planned: List[dict] = field(default_factory=list)
    actions_executed: List[dict] = field(default_factory=list)
    response_text: str = ""          # Natural language response to user
    target_device: str = ""          # Which device was targeted
    execution_time: float = 0.0
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

# ═══════════════════════════════════════════════════════════════════════════════
# INTENT DETECTION (Fast, local keyword-based + LLM fallback)
# ═══════════════════════════════════════════════════════════════════════════════

# Action trigger patterns — if message matches, it's likely actionable
ACTION_PATTERNS = [
    # App control
    (r'\b(open|launch|start|run|close|quit|exit|kill|stop)\s+\w+', 'app_control'),
    # File operations
    (r'\b(create|make|delete|remove|move|copy|rename)\s+(a\s+)?(file|folder|directory)', 'file_op'),
    # System
    (r'\b(take|capture)\s+(a\s+)?screenshot', 'screenshot'),
    (r'\b(set|change)\s+(the\s+)?wallpaper', 'wallpaper'),
    (r'\b(increase|decrease|mute|unmute|set)\s+(the\s+)?volume', 'volume'),
    (r'\b(lock|unlock|restart|shutdown|sleep)\s+(the\s+)?(pc|computer|screen|system)', 'system'),
    # Browser
    (r'\b(search|google|look\s+up|browse|go\s+to)\s+', 'browse'),
    (r'\bopen\s+(https?://|www\.)', 'open_url'),
    # Media
    (r'\b(play|pause|stop|next|previous|skip)\s+(the\s+)?(music|song|video|media)', 'media'),
    # Typing/input
    (r'\b(type|write|enter|input)\s+["\']', 'type_text'),
    # Click
    (r'\b(click|press|tap)\s+(on\s+)?', 'click'),
    # Keyboard shortcuts
    (r'\b(press|hit)\s+(ctrl|alt|shift|win|escape|enter|tab|f\d+)', 'hotkey'),
    # Notifications
    (r'\b(send|show)\s+(a\s+)?notification', 'notification'),
    # Timer/alarm
    (r'\b(set|start)\s+(a\s+)?(timer|alarm|reminder)', 'timer'),
    # Misc direct commands
    (r'\b(minimize|maximize|resize|move)\s+(the\s+)?window', 'window'),
    (r'\b(scroll|swipe)\s+(up|down|left|right)', 'scroll'),
]

# Conversational patterns — if message matches, it's NOT actionable
CONVERSATION_PATTERNS = [
    r'^(hi|hello|hey|good\s+(morning|evening|night)|how\s+are\s+you)',
    r'^(what|who|where|when|why|how)\s+(is|are|was|were|do|does|did|can|could|would|should)',
    r'^(tell\s+me|explain|describe|what\'s|whats)\s+',
    r'^(thank|thanks|thx|bye|goodbye|see\s+you)',
    r'\?$',  # Questions usually aren't actions
]

def detect_intent_fast(message: str) -> Tuple[bool, str, float]:
    """
    Fast keyword-based intent detection.
    Returns: (is_action, category, confidence)
    """
    msg_lower = message.lower().strip()

    # Check conversation patterns first (high-priority exclusion)
    for pattern in CONVERSATION_PATTERNS:
        if re.search(pattern, msg_lower):
            return False, "conversation", 0.9

    # Check action patterns
    for pattern, category in ACTION_PATTERNS:
        if re.search(pattern, msg_lower, re.IGNORECASE):
            return True, category, 0.85

    # Ambiguous — low confidence
    return False, "unknown", 0.3

def detect_intent_llm(message: str, brain) -> Tuple[bool, str, str]:
    """
    Use LLM for intent classification when fast detection is uncertain.
    Returns: (is_action, category, thought)
    """
    prompt = f"""Classify this user message as either an ACTIONABLE COMMAND or a CONVERSATION.

ACTIONABLE COMMAND = the user wants me to physically DO something on their device
(open apps, click things, type text, manage files, control media, take screenshots, etc.)

CONVERSATION = the user wants to talk, ask questions, get information, or chat.

User message: "{message}"

Reply with EXACTLY one line in this format:
ACTION|category|brief_thought
or
CHAT|topic|brief_thought

Examples:
- "open notepad" → ACTION|app_control|User wants me to launch Notepad
- "how are you?" → CHAT|greeting|User is saying hello
- "search for python tutorials" → ACTION|browse|User wants me to search the web
- "what is machine learning?" → CHAT|question|User asking for information"""

    try:
        import requests
        # Use Ollama for fast local classification
        resp = requests.post(
            f"{NEXUS_CONFIG.llm.base_url}/api/generate",
            json={
                "model": NEXUS_CONFIG.llm.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 50}
            },
            timeout=10
        )
        if resp.status_code == 200:
            text = resp.json().get("response", "").strip()
            parts = text.split("|", 2)
            if len(parts) >= 2:
                is_action = parts[0].strip().upper() == "ACTION"
                category = parts[1].strip()
                thought = parts[2].strip() if len(parts) > 2 else ""
                return is_action, category, thought
    except Exception as e:
        logger.warning(f"LLM intent detection failed: {e}")

    return False, "unknown", ""

# ═══════════════════════════════════════════════════════════════════════════════
# ACTION PLAN GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def generate_action_plan(message: str, device_type: str, brain) -> Optional[Dict]:
    """
    Ask the LLM to generate a structured action plan for a command.
    Returns the plan dict or None on failure.
    """
    if device_type in ("host_pc", "web_desktop"):
        platform_context = "Windows PC with full GUI access (mouse, keyboard, apps)"
        action_types = """Available action types:
- open_app: {app: "name"} — launch an application
- open_url: {url: "https://..."} — open URL in browser
- hotkey: {keys: ["ctrl", "c"]} — keyboard shortcut
- press_key: {key: "enter"} — single key press
- type_text: {text: "hello"} — type text
- click: {x: 500, y: 300} — click at coordinates
- shell: {command: "dir"} — run shell command
- powershell: {command: "Get-Process"} — run PowerShell
- screenshot: {} — take screenshot
- notify: {title: "Hi", message: "Done"} — show notification
- wait: {seconds: 2} — pause between steps
- think: {thought: "reasoning"} — internal thought"""
    elif device_type == "android_app":
        platform_context = "Android phone via ADB"
        action_types = """Available action types:
- shell: {command: "am start -n com.app/.Activity"} — ADB shell command
- open_app: {package: "com.android.chrome"} — launch Android app
- type_text: {text: "hello"} — input text via ADB
- press_key: {keycode: 3} — Android keycode (3=home, 4=back)
- screenshot: {} — capture screen
- notify: {title: "Hi", message: "Done"} — toast notification"""
    else:
        platform_context = "Remote device (limited control)"
        action_types = """Available action types:
- shell: {command: "command"} — remote shell command
- notify: {title: "Hi", message: "Done"} — notification"""

    prompt = f"""You are NEXUS, an AI controlling a {platform_context}.
The user said: "{message}"

Generate an action plan as a JSON object. Be PRECISE and PRACTICAL.

{action_types}

Reply with ONLY valid JSON in this exact format:
{{
  "thought": "Brief explanation of what you'll do",
  "actions": [
    {{"type": "action_type", ...params, "reason": "why this step"}}
  ],
  "response": "What to tell the user after completing this"
}}"""

    try:
        import requests
        resp = requests.post(
            f"{NEXUS_CONFIG.llm.base_url}/api/generate",
            json={
                "model": NEXUS_CONFIG.llm.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 500}
            },
            timeout=30
        )
        if resp.status_code == 200:
            text = resp.json().get("response", "").strip()
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                plan = json.loads(json_match.group())
                if "actions" in plan and isinstance(plan["actions"], list):
                    return plan
    except Exception as e:
        logger.error(f"Action plan generation failed: {e}")

    return None

# ═══════════════════════════════════════════════════════════════════════════════
# CHAT ACTION ROUTER (Main Class)
# ═══════════════════════════════════════════════════════════════════════════════

class ChatActionRouter:
    """
    The JARVIS brain — intercepts chat, detects actions, executes on correct device.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._brain = None
        self._action_history: List[Dict] = []
        self._history_lock = threading.Lock()
        self._event_bus = None
        logger.info("ChatActionRouter initialized — JARVIS mode ready")

    def set_brain(self, brain):
        self._brain = brain

    def set_event_bus(self, event_bus):
        """Connect to the PC Control Agent's event bus for live feed."""
        self._event_bus = event_bus

    def _emit_event(self, event_type: str, data: dict):
        """Emit event to live action feed."""
        if self._event_bus:
            try:
                self._event_bus({
                    "type": event_type,
                    "source": "chat_command",
                    "timestamp": datetime.now().isoformat(),
                    **data
                })
            except Exception:
                pass

    # ─────────────────────────────────────────────────────────────────────────
    # MAIN ENTRY POINT
    # ─────────────────────────────────────────────────────────────────────────

    def try_execute(self, message: str, device_session=None) -> Optional[ActionResult]:
        """
        Try to detect and execute an actionable command from a chat message.

        Returns ActionResult if the message was an action, None if it's conversation.
        """
        start = time.time()
        result = ActionResult()

        # Step 1: Fast intent detection
        is_action, category, confidence = detect_intent_fast(message)

        # Step 2: If uncertain, use LLM
        if confidence < 0.7:
            is_action_llm, category_llm, thought = detect_intent_llm(message, self._brain)
            if category_llm != "unknown":
                is_action = is_action_llm
                category = category_llm
                result.thought = thought

        if not is_action:
            return None  # Not an action — let normal chat handle it

        result.is_action = True
        logger.info(f"🎯 Action detected: [{category}] \"{message}\"")

        # Emit to live feed
        self._emit_event("action_detected", {
            "message": message,
            "category": category,
            "confidence": confidence,
        })

        # Step 3: Determine target device
        device_type = "host_pc"
        device_name = "Host PC"
        if device_session:
            device_type = device_session.device_type
            device_name = device_session.device_name
            result.target_device = device_name

        # Step 4: Generate action plan
        plan = generate_action_plan(message, device_type, self._brain)
        if not plan:
            result.success = False
            result.error = "Could not generate action plan"
            result.response_text = "I understood what you want, but I couldn't figure out the exact steps. Could you be more specific?"
            return result

        result.thought = plan.get("thought", "")
        result.actions_planned = plan.get("actions", [])
        result.response_text = plan.get("response", "Done!")

        self._emit_event("plan_generated", {
            "thought": result.thought,
            "actions": result.actions_planned,
            "target": device_name,
        })

        # Step 5: Execute actions on the correct device
        try:
            if device_type in ("host_pc",):
                executed = self._execute_on_host(result.actions_planned, message)
            elif device_type == "android_app":
                executed = self._execute_on_android(
                    result.actions_planned,
                    device_session.ip_address if device_session else "",
                    message
                )
            elif device_type == "web_desktop":
                executed = self._execute_on_remote_pc(
                    result.actions_planned,
                    device_session.ip_address if device_session else "",
                    message
                )
            else:
                executed = []
                result.response_text = (
                    f"I can't execute actions on your {device_name} right now — "
                    f"I don't have direct control over that device type."
                )

            result.actions_executed = executed
            result.success = len(executed) > 0

        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            result.success = False
            result.error = str(e)
            result.response_text = f"I tried but ran into an error: {e}"

        result.execution_time = time.time() - start

        self._emit_event("action_complete", {
            "success": result.success,
            "actions_executed": len(result.actions_executed),
            "time": result.execution_time,
            "response": result.response_text,
        })

        # Store in history
        with self._history_lock:
            self._action_history.append({
                "timestamp": datetime.now().isoformat(),
                "message": message,
                "category": category,
                "target": device_name,
                "success": result.success,
                "actions": len(result.actions_executed),
                "time": result.execution_time,
            })
            # Keep last 200
            if len(self._action_history) > 200:
                self._action_history = self._action_history[-200:]

        return result

    # ─────────────────────────────────────────────────────────────────────────
    # DEVICE-SPECIFIC EXECUTION
    # ─────────────────────────────────────────────────────────────────────────

    def _execute_on_host(self, actions: List[dict], reason: str) -> List[dict]:
        """Execute actions on the host PC via PCControlAgent."""
        executed = []
        try:
            # Import PCControlAgent and use its execution pipeline
            from core.pc_control_agent import PCControlAgent
            agent = PCControlAgent()

            # Ensure systems are loaded (computer_body, etc.)
            agent._load_systems()

            if not agent._computer_body:
                logger.error("Computer body not available for host execution")
                return [{"type": "error", "success": False, "error": "Computer body not loaded"}]

            for action in actions:
                action_type = action.get("type", "")

                # Skip internal-only actions
                if action_type in ("think", "wait"):
                    executed.append({**action, "success": True, "result": "Skipped (internal)"})
                    continue

                self._emit_event("executing", {
                    "action": action_type,
                    "detail": action.get("reason", ""),
                    "target": "Host PC",
                })

                try:
                    # PCControlAgent._execute_action takes (action_type, data_dict)
                    success, result_msg = agent._execute_action(action_type, action)
                    executed.append({
                        **action,
                        "success": success,
                        "result": result_msg,
                        "executed_at": datetime.now().isoformat(),
                    })
                    # Brief pause between actions for visual effect
                    time.sleep(0.5)
                except Exception as e:
                    logger.warning(f"Host action failed: {action_type} — {e}")
                    executed.append({
                        **action,
                        "success": False,
                        "error": str(e),
                    })

            # Mark task as complete in the autonomous loop's context
            try:
                agent.mark_task_complete(reason)
            except Exception:
                pass

        except ImportError:
            logger.error("PCControlAgent not available")
        except Exception as e:
            logger.error(f"Host execution error: {e}")

        return executed

    def _execute_on_android(self, actions: List[dict], ip: str, reason: str) -> List[dict]:
        """Execute actions on an Android device via ADB."""
        executed = []
        if not ip:
            return executed

        try:
            from body.network_mesh import NetworkMesh
            mesh = NetworkMesh()

            for action in actions:
                action_type = action.get("type", "")
                self._emit_event("executing", {
                    "action": action_type,
                    "detail": action.get("reason", ""),
                    "target": f"Android @ {ip}",
                })

                adb_cmd = self._translate_to_adb(action)
                if adb_cmd:
                    result = mesh.adb_command(ip, adb_cmd)
                    executed.append({
                        **action,
                        "adb_command": adb_cmd,
                        "success": result.success,
                        "output": result.stdout[:200] if result.stdout else "",
                    })
                else:
                    executed.append({**action, "success": False, "error": "Cannot translate to ADB"})

                time.sleep(0.3)

        except Exception as e:
            logger.error(f"Android execution error: {e}")

        return executed

    def _execute_on_remote_pc(self, actions: List[dict], ip: str, reason: str) -> List[dict]:
        """Execute actions on a remote PC via SSH or PowerShell."""
        executed = []
        if not ip:
            return executed

        try:
            from body.network_mesh import NetworkMesh
            mesh = NetworkMesh()
            device = mesh.get_device(ip)
            if not device:
                return executed

            for action in actions:
                action_type = action.get("type", "")
                self._emit_event("executing", {
                    "action": action_type,
                    "target": f"Remote PC @ {ip}",
                })

                if action_type in ("shell", "powershell"):
                    cmd = action.get("command", "")
                    if device.connection_protocol == "ssh":
                        result = mesh.ssh_command(ip, cmd)
                    else:
                        result = mesh.ps_remote_command(ip, cmd)
                    executed.append({
                        **action,
                        "success": result.success,
                        "output": result.stdout[:200] if result.stdout else "",
                    })
                elif action_type == "open_app":
                    app = action.get("app", "")
                    cmd = f"Start-Process '{app}'" if device.connection_protocol != "ssh" else app
                    if device.connection_protocol == "ssh":
                        result = mesh.ssh_command(ip, cmd)
                    else:
                        result = mesh.ps_remote_command(ip, cmd)
                    executed.append({**action, "success": result.success})
                else:
                    executed.append({**action, "success": False, "error": "Not supported remotely"})

                time.sleep(0.3)

        except Exception as e:
            logger.error(f"Remote PC execution error: {e}")

        return executed

    def _translate_to_adb(self, action: dict) -> Optional[str]:
        """Translate a generic action to an ADB shell command."""
        t = action.get("type", "")

        if t == "open_app":
            pkg = action.get("package", "")
            if pkg:
                return f"monkey -p {pkg} -c android.intent.category.LAUNCHER 1"
        elif t == "shell":
            return action.get("command", "")
        elif t == "type_text":
            text = action.get("text", "").replace(" ", "%s").replace("'", "\\'")
            return f"input text '{text}'"
        elif t == "press_key":
            keycode = action.get("keycode", "")
            return f"input keyevent {keycode}"
        elif t == "screenshot":
            return "screencap -p /sdcard/nexus_screenshot.png"
        elif t == "notify":
            title = action.get("title", "NEXUS")
            msg = action.get("message", "")
            return f"am broadcast -a android.intent.action.MAIN --es title '{title}' --es message '{msg}'"

        return None

    # ─────────────────────────────────────────────────────────────────────────
    # STATS
    # ─────────────────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        with self._history_lock:
            total = len(self._action_history)
            successful = sum(1 for a in self._action_history if a.get("success"))
            return {
                "total_actions": total,
                "successful": successful,
                "success_rate": successful / total if total > 0 else 0,
                "recent": self._action_history[-10:],
            }

    def get_recent_actions(self, limit: int = 20) -> List[dict]:
        with self._history_lock:
            return self._action_history[-limit:]

# Singleton
chat_action_router = ChatActionRouter()
