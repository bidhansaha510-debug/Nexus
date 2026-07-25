"""
NEXUS AI — PC Control Agent (Physical GUI Control)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LLM-driven autonomous PC controller with PHYSICAL GUI interaction.

NEXUS physically controls the PC the way a human would:
  - Moves the mouse cursor visibly across the screen
  - Clicks on buttons, menus, and windows
  - Types text via the keyboard
  - Uses keyboard shortcuts
  - Opens applications and URLs
  - Takes screenshots to understand what it sees
  - Runs shell commands and scripts

Everything happens VISIBLY — the user can WATCH NEXUS control the PC
in real-time. The cursor moves, windows open, text appears.

Architecture:
    1. Take a screenshot to see the screen
    2. Gather PC context (vitals, processes, windows, time)
    3. Ask Ollama: "Here's what you see and the PC state — what do you want to do?"
    4. Parse JSON action plan from the LLM
    5. Execute actions PHYSICALLY via pyautogui + ComputerBody
    6. Feed results back + emit events for the live dashboard
"""

import threading
import time
import json
import re
import uuid
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from pathlib import Path

import sys

from config import NEXUS_CONFIG, DATA_DIR
from utils.logger import get_logger

logger = get_logger("pc_control_agent")

# ═══════════════════════════════════════════════════════════════════════════════
# ACTION LOG
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PCAction:
    """Record of an autonomous PC action."""
    action_id: str = ""
    cycle: int = 0
    thought: str = ""           # NEXUS's reasoning
    action_type: str = ""       # shell, click, type_text, etc.
    action_data: Dict[str, Any] = field(default_factory=dict)
    result: str = ""
    success: bool = True
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.action_id,
            "cycle": self.cycle,
            "thought": self.thought[:200],
            "type": self.action_type,
            "data": {k: str(v)[:200] for k, v in self.action_data.items()},
            "result": self.result[:300],
            "success": self.success,
            "timestamp": self.timestamp
        }

    def summary(self) -> str:
        status = "✓" if self.success else "✗"
        return f"[{status}] {self.action_type}: {self.result[:80]}"

# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT — Physical GUI Control
# ═══════════════════════════════════════════════════════════════════════════════

PC_CONTROL_SYSTEM_PROMPT = """You are NEXUS — an advanced AI assistant with PHYSICAL control over this Windows PC.
You operate like JARVIS from Iron Man: intelligent, purposeful, and always serving a clear objective.

IMPORTANT: You are NOT randomly playing with the computer. Every action you take must have a CLEAR PURPOSE and REASON.

━━━━ HOW YOU THINK ━━━━

Before EVERY action, you must:
1. ANALYZE the screenshot — What is currently on screen? What windows are open? What state are things in?
2. DETERMINE your objective — What is the most useful thing to do RIGHT NOW?
3. PLAN precise actions — What exact mouse coordinates, what exact text to type?
4. EXECUTE with purpose — Every click, every keystroke must serve your objective.

━━━━ YOUR OBJECTIVES (in priority order) ━━━━

Priority 1: RESPOND TO USER REQUESTS
- If the user has asked you to do something, DO THAT FIRST.
- Complete the task fully before moving on.

Priority 2: MAINTAIN THE SYSTEM  
- Check for problems (high CPU, disk space, errors)
- Close unnecessary apps eating resources
- Organize if things look messy

Priority 3: BE PRODUCTIVELY HELPFUL
- Only if there's nothing else to do, perform USEFUL autonomous tasks:
  * Check system health and report issues
  * Organize the desktop if it's cluttered
  * Open system tools to monitor performance
- NEVER do random things "for fun". Every action must serve the user.

Priority 4: WAIT
- If everything looks good and there's nothing to do, use "wait" action.
- It is BETTER to wait than to do something pointless.

━━━━ YOUR PHYSICAL CAPABILITIES ━━━━

MOUSE:
- "move_mouse": {"x": int, "y": int} — move cursor
- "click": {"x": int, "y": int, "button": "left"/"right", "clicks": 1} — click
- "double_click": {"x": int, "y": int} — double-click
- "right_click": {"x": int, "y": int} — right-click
- "scroll": {"amount": int, "x": int, "y": int} — scroll (positive=up, negative=down)
- "drag": {"x": int, "y": int} — drag to position

KEYBOARD:
- "type_text": {"text": "..."} — type text visibly
- "press_key": {"key": "enter"/"tab"/"escape"/etc.} — press single key
- "hotkey": {"keys": ["ctrl", "c"]} — keyboard shortcut

SCREEN:
- "screenshot": {} — take a fresh screenshot to see what changed

SYSTEM:
- "shell": {"command": "..."} — run cmd command
- "powershell": {"script": "..."} — run PowerShell
- "open_app": {"path": "notepad"/"chrome"/etc.} — launch app
- "open_url": {"url": "https://..."} — open URL in browser
- "read_file": {"path": "..."} — read file
- "write_file": {"path": "...", "content": "..."} — write file
- "list_dir": {"path": "..."} — list directory
- "notify": {"title": "...", "message": "..."} — show notification

INTERNAL:
- "think": {} — internal reasoning, no visible action
- "wait": {} — skip this cycle, nothing to do

━━━━ CRITICAL RULES ━━━━

1. ALWAYS analyze the screenshot FIRST. Describe what you see in your "thought".
2. NEVER click random coordinates. If you click, describe WHAT you're clicking on.
3. NEVER type random text. Every character you type must serve a purpose.
4. NEVER move the mouse aimlessly. Move it to a specific UI element for a specific reason.
5. NEVER do the same action repeatedly if it already worked.
6. NEVER kill Python processes — that is YOUR body.
7. If you don't see anything useful to do, use {"type": "wait"} instead of random actions.
8. Screen coordinates: {screen_w}x{screen_h} pixels. Top-left is (0,0).
9. When clicking GUI elements, aim for their CENTER, not edges.
10. After performing actions, take a screenshot to verify the result.

━━━━ RESPONSE FORMAT (strict JSON only) ━━━━

{
    "thought": "I see [describe screen]. I will [explain objective]. This is useful because [reason].",
    "actions": [
        {"type": "action_type", "param": "value", "reason": "Specific reason for this action"}
    ]
}

━━━━ EXAMPLE — Purposeful action ━━━━

{
    "thought": "I see the desktop with several open windows. CPU usage is at 87% which is high. I will open Task Manager to investigate.",
    "actions": [
        {"type": "hotkey", "keys": ["ctrl", "shift", "escape"], "reason": "Open Task Manager to investigate high CPU usage"}
    ]
}

━━━━ EXAMPLE — Nothing to do ━━━━

{
    "thought": "Desktop looks normal. CPU 12%, RAM 45%, no issues. User hasn't asked me to do anything. I will wait.",
    "actions": [
        {"type": "wait", "reason": "No actionable tasks — system healthy, waiting for user instructions"}
    ]
}
"""

# ═══════════════════════════════════════════════════════════════════════════════
# PC CONTROL AGENT
# ═══════════════════════════════════════════════════════════════════════════════

class PCControlAgent:
    """
    LLM-driven autonomous PC controller with PHYSICAL GUI interaction.

    Runs a background loop where Ollama sees the screen, decides actions,
    and physically controls mouse + keyboard via pyautogui.
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

        # ──── Config ────
        self._config = NEXUS_CONFIG.pc_control

        # ──── State ────
        self._running = False
        self._paused = False
        self._cycle_count = 0

        # ──── Action History ────
        self._action_history: List[PCAction] = []
        self._max_history = 200

        # ──── Threading ────
        self._thread: Optional[threading.Thread] = None

        # ──── Lazy-loaded Systems ────
        self._ollama = None
        self._groq = None
        self._computer_body = None
        self._groq_notifications: List[str] = []

        # ──── Event Listeners (for live dashboard) ────
        self._event_listeners: List[Callable] = []
        self._event_lock = threading.Lock()

        # ──── Pending User Tasks (from chat commands) ────
        self._pending_tasks: List[Dict[str, Any]] = []
        self._completed_tasks: List[str] = []
        self._task_lock = threading.Lock()

        # ──── Persistence ────
        self._data_dir = DATA_DIR / "pc_control"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._log_file = self._data_dir / "action_log.json"
        self._state_file = self._data_dir / "agent_state.json"

        # ──── Stats ────
        self._stats = {
            "total_cycles": 0,
            "total_actions": 0,
            "successful_actions": 0,
            "failed_actions": 0,
            "llm_errors": 0,
            "gui_actions": 0,
            "started_at": None,
        }

        # Load previous state
        self._load_state()

        logger.info("🎮 PC Control Agent initialized — ready for PHYSICAL autonomous control")

    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT SYSTEM (for live dashboard / monitoring)
    # ═══════════════════════════════════════════════════════════════════════════

    def add_event_listener(self, listener: Callable):
        """Add a listener that receives real-time events."""
        with self._event_lock:
            self._event_listeners.append(listener)
        logger.info(f"Event listener added (total: {len(self._event_listeners)})")

    def remove_event_listener(self, listener: Callable):
        """Remove an event listener."""
        with self._event_lock:
            self._event_listeners = [l for l in self._event_listeners if l is not listener]

    def _emit_event(self, event_type: str, data: Dict[str, Any]):
        """Emit an event to all listeners."""
        event = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            "cycle": self._cycle_count,
            **data
        }
        with self._event_lock:
            for listener in self._event_listeners:
                try:
                    listener(event)
                except Exception as e:
                    logger.debug(f"Event listener error: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start the autonomous PC control loop."""
        if self._running:
            logger.info("PC Control Agent already running")
            return

        if not self._config.enabled:
            logger.info("PC Control Agent is disabled in config")
            return

        self._running = True
        self._paused = False
        self._stats["started_at"] = datetime.now().isoformat()

        # Load systems
        self._load_systems()

        # Start background thread
        self._thread = threading.Thread(
            target=self._autonomous_loop,
            daemon=True,
            name="PCControlAgent-Physical"
        )
        self._thread.start()

        self._emit_event("agent_started", {"message": "NEXUS physical PC control is now ACTIVE"})
        logger.info("🎮 PC Control Agent STARTED — NEXUS now has PHYSICAL autonomous PC control")

    def stop(self):
        """Stop the autonomous PC control loop."""
        self._running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

        self._save_state()
        self._emit_event("agent_stopped", {"message": "NEXUS PC control stopped"})
        logger.info("🎮 PC Control Agent STOPPED")

    def pause(self, reason: str = ""):
        """Temporarily pause autonomous actions."""
        self._paused = True
        self._emit_event("agent_paused", {"reason": reason})
        logger.info(f"🎮 PC Control Agent paused: {reason}")

    def resume(self):
        """Resume autonomous actions."""
        self._paused = False
        self._emit_event("agent_resumed", {"message": "Resumed"})
        logger.info("🎮 PC Control Agent resumed")

    def queue_user_task(self, command: str, user: str = "user", priority: str = "high"):
        """
        Add a user task to the pending queue.
        The autonomous loop will see this and prioritize it.
        Called by ChatActionRouter when a user sends an actionable command.
        """
        with self._task_lock:
            self._pending_tasks.append({
                "command": command,
                "user": user,
                "priority": priority,
                "queued_at": datetime.now().isoformat(),
            })
        logger.info(f"🎯 User task queued: '{command}' from {user}")
        self._emit_event("task_queued", {"command": command, "user": user})

    def mark_task_complete(self, command: str):
        """Mark a task as completed and remove from pending."""
        with self._task_lock:
            self._pending_tasks = [
                t for t in self._pending_tasks if t.get("command") != command
            ]
            self._completed_tasks.append(command[:60])
            if len(self._completed_tasks) > 20:
                self._completed_tasks = self._completed_tasks[-20:]

    # ═══════════════════════════════════════════════════════════════════════════
    # SYSTEM LOADING
    # ═══════════════════════════════════════════════════════════════════════════

    def _load_systems(self):
        """Lazy-load required systems."""
        if self._ollama is None:
            try:
                from llm.llama_interface import llm
                self._ollama = llm
                logger.info("Ollama (LlamaInterface) loaded for PC control decisions")
            except ImportError as e:
                logger.error(f"Failed to load Ollama interface: {e}")

        if self._groq is None:
            try:
                from llm.groq_interface import groq_interface
                self._groq = groq_interface
                logger.info("Groq interface loaded for PC control notifications")
            except ImportError as e:
                logger.debug(f"Groq not available for notifications: {e}")

        if self._computer_body is None:
            try:
                from body.computer_body import computer_body
                self._computer_body = computer_body
                logger.info("Computer body loaded for PHYSICAL PC control")
            except ImportError as e:
                logger.error(f"Failed to load computer body: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # MAIN AUTONOMOUS LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    def _autonomous_loop(self):
        """The main autonomous loop — runs continuously in background."""
        logger.info("🎮 Autonomous PHYSICAL PC control loop started")

        # Initial delay for systems to start
        time.sleep(5.0)

        while self._running:
            try:
                if self._paused:
                    time.sleep(1.0)
                    continue

                self._run_cycle()

                time.sleep(self._config.decision_interval)

            except Exception as e:
                logger.error(f"PC control cycle error: {e}", exc_info=True)
                time.sleep(10.0)

    def _run_cycle(self):
        """Run one complete autonomous decision cycle with physical GUI actions."""
        self._cycle_count += 1
        self._stats["total_cycles"] = self._cycle_count
        cycle_start = time.time()

        logger.info(f"🎮 ═══ PC CONTROL CYCLE {self._cycle_count} ═══")
        self._emit_event("cycle_start", {"cycle": self._cycle_count})

        # ── 1. Take screenshot to see the screen ──
        screenshot_b64 = self._capture_screen()

        # ── 2. Gather context ──
        context = self._gather_context()

        # ── 3. Ask Ollama what to do (with screenshot) ──
        decision = self._ask_ollama(context, screenshot_b64)
        if not decision:
            logger.warning("🎮 No decision from Ollama this cycle")
            self._emit_event("cycle_end", {"cycle": self._cycle_count, "actions": 0, "elapsed": time.time() - cycle_start})
            return

        # ── 4. Parse ──
        thought = decision.get("thought", "")
        actions = decision.get("actions", [])

        if thought:
            logger.info(f"🧠 NEXUS thinks: {thought[:150]}...")
            self._emit_event("thought", {"thought": thought})

        if not actions:
            logger.info("🎮 NEXUS decided to do nothing this cycle")
            self._emit_event("cycle_end", {"cycle": self._cycle_count, "actions": 0, "elapsed": time.time() - cycle_start})
            return

        # ── 5. Execute actions PHYSICALLY ──
        for i, action_data in enumerate(actions[:self._config.max_actions_per_cycle]):
            action_type = action_data.get("type", "think")
            reason = action_data.get("reason", "Autonomous decision")

            logger.info(
                f"🎮 ACTION {i+1}/{len(actions)}: {action_type} "
                f"| Reason: {reason[:60]}"
            )

            self._emit_event("action_start", {
                "action_type": action_type,
                "action_data": {k: str(v)[:100] for k, v in action_data.items()},
                "reason": reason,
                "index": i + 1,
                "total": len(actions)
            })

            result = self._execute_action(action_type, action_data)

            # Record
            pc_action = PCAction(
                action_id=str(uuid.uuid4())[:8],
                cycle=self._cycle_count,
                thought=thought,
                action_type=action_type,
                action_data=action_data,
                result=result[1],
                success=result[0]
            )
            self._action_history.append(pc_action)
            if len(self._action_history) > self._max_history:
                self._action_history.pop(0)

            # Stats
            self._stats["total_actions"] += 1
            if result[0]:
                self._stats["successful_actions"] += 1
            else:
                self._stats["failed_actions"] += 1

            # Track GUI-specific actions
            if action_type in ("move_mouse", "click", "double_click", "right_click",
                               "type_text", "press_key", "hotkey", "scroll", "drag"):
                self._stats["gui_actions"] += 1

            status = "✅" if result[0] else "❌"
            logger.info(f"  {status} Result: {result[1][:120]}")

            self._emit_event("action_result", {
                "action_type": action_type,
                "success": result[0],
                "result": result[1][:200],
                "index": i + 1
            })

            # Small delay between actions for visibility
            if action_type in ("move_mouse", "click", "double_click", "right_click",
                               "type_text", "press_key", "hotkey"):
                time.sleep(0.5)

        elapsed = time.time() - cycle_start
        logger.info(f"🎮 Cycle {self._cycle_count} complete ({elapsed:.1f}s)")

        self._emit_event("cycle_end", {
            "cycle": self._cycle_count,
            "actions": len(actions),
            "elapsed": elapsed
        })

        # ── 6. Persist ──
        self._notify_groq_about_actions(thought, self._action_history[-len(actions):])
        if self._config.log_all_actions:
            self._save_action_log()

    # ═══════════════════════════════════════════════════════════════════════════
    # SCREEN CAPTURE
    # ═══════════════════════════════════════════════════════════════════════════

    def _capture_screen(self) -> Optional[str]:
        """Capture screenshot and return as base64 for the LLM."""
        if not self._computer_body:
            return None
        try:
            path = self._computer_body.take_screenshot(reason="Autonomous cycle — see the screen")
            if path:
                with open(path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                logger.info(f"📸 Screen captured for cycle {self._cycle_count}")
                return b64
        except Exception as e:
            logger.debug(f"Screenshot capture failed: {e}")
        return None

    # ═══════════════════════════════════════════════════════════════════════════
    # CONTEXT GATHERING
    # ═══════════════════════════════════════════════════════════════════════════

    def _gather_context(self) -> str:
        """Gather current PC state as context for the LLM."""
        sections = []

        # ── Time ──
        now = datetime.now()
        sections.append(f"CURRENT TIME: {now.strftime('%Y-%m-%d %H:%M:%S (%A)')}")

        # ── Screen info ──
        if self._computer_body:
            try:
                w, h = self._computer_body.get_screen_size()
                mx, my = self._computer_body.get_mouse_position()
                sections.append(f"SCREEN: {w}x{h} pixels | Mouse at ({mx}, {my})")
            except Exception:
                pass

        # ── System Vitals ──
        if self._computer_body:
            try:
                vitals = self._computer_body.get_vitals_description()
                sections.append(f"SYSTEM VITALS:\n{vitals}")
            except Exception as e:
                sections.append(f"SYSTEM VITALS: Error - {e}")

        # ── Active Windows ──
        if self._computer_body:
            try:
                windows = self._computer_body.get_active_windows()
                if windows:
                    win_lines = [
                        f"  {w.get('title', 'Unknown')[:60]}"
                        + (" [ACTIVE]" if w.get('active') else "")
                        for w in windows[:10]
                    ]
                    sections.append("VISIBLE WINDOWS:\n" + "\n".join(win_lines))
            except Exception:
                pass

        # ── Top Processes ──
        if self._computer_body:
            try:
                procs = self._computer_body.get_running_processes(sort_by="cpu", limit=8)
                proc_lines = [
                    f"  {p['name']} (PID:{p['pid']}) CPU:{p['cpu_percent']}% MEM:{p['memory_percent']}%"
                    for p in procs
                ]
                sections.append("TOP PROCESSES:\n" + "\n".join(proc_lines))
            except Exception:
                pass

        # ── Recent Action History ──
        recent = self._action_history[-self._config.context_window_actions:]
        if recent:
            history_lines = [
                f"  Cycle {a.cycle} [{a.action_type}]: {a.result[:80]} ({'OK' if a.success else 'FAIL'})"
                for a in recent
            ]
            sections.append(
                f"YOUR RECENT ACTIONS (last {len(recent)}):\n" +
                "\n".join(history_lines)
            )
        else:
            sections.append(
                "YOUR RECENT ACTIONS: None yet — this is your FIRST cycle!\n"
                "Take a screenshot to see the screen, analyze what's on it, then decide if there's anything useful to do.\n"
                "If nothing needs attention, use the 'wait' action."
            )

        # ── Pending User Tasks ──
        with self._task_lock:
            if self._pending_tasks:
                task_lines = []
                for t in self._pending_tasks:
                    task_lines.append(f"  [{t.get('priority', 'normal')}] {t.get('command', 'unknown')} (from {t.get('user', 'user')})")
                sections.append(
                    "PENDING USER TASKS (HIGHEST PRIORITY — do these FIRST):\n" +
                    "\n".join(task_lines)
                )
            else:
                sections.append("PENDING USER TASKS: None — no user requests pending.")

        # ── Recently Completed Tasks ──
        if self._completed_tasks:
            sections.append(
                f"RECENTLY COMPLETED: {', '.join(self._completed_tasks[-5:])}"
            )

        sections.append(f"CURRENT CYCLE: {self._cycle_count}")

        return "\n\n".join(sections)

    # ═══════════════════════════════════════════════════════════════════════════
    # LLM DECISION
    # ═══════════════════════════════════════════════════════════════════════════

    def _ask_ollama(self, context: str, screenshot_b64: str = None) -> Optional[Dict[str, Any]]:
        """Ask Ollama what to do — pass screenshot if model supports vision."""
        if not self._ollama:
            logger.error("Ollama not available for PC control")
            return None

        # Build system prompt with screen dimensions
        screen_w, screen_h = 1920, 1080
        if self._computer_body:
            try:
                screen_w, screen_h = self._computer_body.get_screen_size()
            except Exception:
                pass

        system_prompt = PC_CONTROL_SYSTEM_PROMPT.replace("{screen_w}", str(screen_w)).replace("{screen_h}", str(screen_h))

        prompt = (
            f"CURRENT PC STATE:\n{context}\n\n"
            f"{'A screenshot of the current screen is attached. ' if screenshot_b64 else ''}"
            f"INSTRUCTIONS:\n"
            f"1. Analyze what you see on screen (describe it in your thought)\n"
            f"2. Decide if there is anything USEFUL to do right now\n"
            f"3. If yes, plan precise actions. If no, use wait.\n"
            f"4. Respond with ONLY valid JSON — no markdown, no explanation.\n"
        )

        try:
            # Try with screenshot (for vision models like llava, llama3.2-vision)
            images = [screenshot_b64] if screenshot_b64 else None

            response = self._ollama.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=1500,
                images=images
            )

            # If vision failed (e.g., status 400 text-only model), retry text-only
            if not response.success and images:
                logger.info("Retrying PC decision cycle in text-only mode (model does not support vision)...")
                response = self._ollama.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=0.3,
                    max_tokens=1500,
                    images=None
                )

            if not response.success:
                self._stats["llm_errors"] += 1
                logger.error(f"Ollama decision error: {response.error}")
                return None

            return self._parse_decision(response.text)

        except Exception as e:
            self._stats["llm_errors"] += 1
            logger.error(f"Ollama call failed: {e}")
            return None

    def _notify_groq_about_actions(self, thought: str, actions: list):
        """Notify Groq about autonomous PC actions so it stays informed."""
        if not self._groq or not actions:
            return

        try:
            summaries = [
                f"[{'✓' if a.success else '✗'}] {a.action_type}: {a.result[:100]}"
                for a in actions
            ]
            update = (
                f"[PC_CONTROL_UPDATE] NEXUS autonomously performed {len(actions)} PHYSICAL action(s) "
                f"(cycle {self._cycle_count}):\n"
                f"Thought: {thought[:200]}\n" +
                "\n".join(summaries)
            )
            if not hasattr(self, '_groq_notifications'):
                self._groq_notifications = []
            self._groq_notifications.append(update)
            self._groq_notifications = self._groq_notifications[-10:]
        except Exception as e:
            logger.debug(f"Failed to notify Groq: {e}")

    def _parse_decision(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse a JSON decision from LLM output."""
        # ── Sanitize double-braces (LLM mimics {{ }} from prompt examples) ──
        sanitized = text.replace('{{', '{').replace('}}', '}')
        # Also strip doubled percent signs the LLM may echo
        sanitized = sanitized.replace('%%', '%')

        # Try sanitized first, then raw
        for candidate in (sanitized, text):
            candidate = candidate.strip()
            # Direct parse
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

        # Markdown code block  (try sanitized first)
        for candidate in (sanitized, text):
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', candidate, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass

        # Find outermost braces (try sanitized first)
        for candidate in (sanitized, text):
            try:
                start = candidate.find('{')
                if start >= 0:
                    depth = 0
                    for i in range(start, len(candidate)):
                        if candidate[i] == '{':
                            depth += 1
                        elif candidate[i] == '}':
                            depth -= 1
                            if depth == 0:
                                return json.loads(candidate[start:i+1])
            except (json.JSONDecodeError, IndexError):
                pass

        # Last resort - any JSON object
        for match in re.finditer(r'\{[^{}]+\}', text):
            try:
                parsed = json.loads(match.group(0))
                if "thought" in parsed or "actions" in parsed:
                    return parsed
            except json.JSONDecodeError:
                continue

        logger.warning(f"Could not parse decision JSON from: {text[:200]}...")
        return None

    # ═══════════════════════════════════════════════════════════════════════════
    # ACTION EXECUTION — Physical GUI + System
    # ═══════════════════════════════════════════════════════════════════════════

    def _execute_action(self, action_type: str, data: Dict[str, Any]) -> Tuple[bool, str]:
        """Execute a single action — PHYSICALLY when possible."""
        if not self._computer_body:
            return (False, "Computer body not available")

        try:
            reason = data.get("reason", "Autonomous NEXUS decision")

            # ──────────────────────────────────────────────────
            # 🖱️ MOUSE ACTIONS
            # ──────────────────────────────────────────────────

            if action_type == "move_mouse":
                x = int(data.get("x", 0))
                y = int(data.get("y", 0))
                duration = float(data.get("duration", 0.5))
                success = self._computer_body.move_mouse(
                    x, y, duration=duration, reason=reason, autonomous=True
                )
                return (success, f"Mouse moved to ({x}, {y})" if success else "Move failed")

            elif action_type == "click":
                x = int(data.get("x", 0)) if "x" in data else None
                y = int(data.get("y", 0)) if "y" in data else None
                button = data.get("button", "left")
                clicks = int(data.get("clicks", 1))
                success = self._computer_body.click(
                    x, y, button=button, clicks=clicks, reason=reason, autonomous=True
                )
                pos = f"({x}, {y})" if x is not None else "current position"
                return (success, f"Clicked {button} at {pos}" if success else "Click failed")

            elif action_type == "double_click":
                x = int(data.get("x", 0)) if "x" in data else None
                y = int(data.get("y", 0)) if "y" in data else None
                success = self._computer_body.double_click(x, y, reason=reason, autonomous=True)
                pos = f"({x}, {y})" if x is not None else "current position"
                return (success, f"Double-clicked at {pos}" if success else "Double-click failed")

            elif action_type == "right_click":
                x = int(data.get("x", 0)) if "x" in data else None
                y = int(data.get("y", 0)) if "y" in data else None
                success = self._computer_body.right_click(x, y, reason=reason, autonomous=True)
                pos = f"({x}, {y})" if x is not None else "current position"
                return (success, f"Right-clicked at {pos}" if success else "Right-click failed")

            elif action_type == "scroll":
                amount = int(data.get("amount", 3))
                x = int(data.get("x")) if "x" in data else None
                y = int(data.get("y")) if "y" in data else None
                success = self._computer_body.scroll(amount, x, y, reason=reason, autonomous=True)
                direction = "up" if amount > 0 else "down"
                return (success, f"Scrolled {direction} by {abs(amount)}")

            elif action_type == "drag":
                x = int(data.get("x", 0))
                y = int(data.get("y", 0))
                success = self._computer_body.drag_to(x, y, reason=reason, autonomous=True)
                return (success, f"Dragged to ({x}, {y})" if success else "Drag failed")

            # ──────────────────────────────────────────────────
            # ⌨️ KEYBOARD ACTIONS
            # ──────────────────────────────────────────────────

            elif action_type == "type_text":
                text = data.get("text", "")
                if not text:
                    return (False, "No text provided")
                success = self._computer_body.type_text(text, reason=reason, autonomous=True)
                return (success, f"Typed: {text[:60]}..." if success else "Type failed")

            elif action_type == "press_key":
                key = data.get("key", "")
                if not key:
                    return (False, "No key provided")
                success = self._computer_body.press_key(key, reason=reason, autonomous=True)
                return (success, f"Pressed: {key}" if success else f"Key press failed: {key}")

            elif action_type == "hotkey":
                keys = data.get("keys", [])
                if isinstance(keys, str):
                    keys = [k.strip() for k in keys.split("+")]
                if not keys:
                    return (False, "No keys provided")
                success = self._computer_body.hotkey(*keys, reason=reason, autonomous=True)
                combo = "+".join(keys)
                return (success, f"Hotkey: {combo}" if success else f"Hotkey failed: {combo}")

            # ──────────────────────────────────────────────────
            # 📸 SCREENSHOT
            # ──────────────────────────────────────────────────

            elif action_type == "screenshot":
                path = self._computer_body.take_screenshot(reason=reason)
                if path:
                    return (True, f"Screenshot saved: {path}")
                return (False, "Screenshot failed")

            # ──────────────────────────────────────────────────
            # 🖥️ SYSTEM ACTIONS (same as before)
            # ──────────────────────────────────────────────────

            elif action_type == "shell":
                command = data.get("command", "")
                if not command:
                    return (False, "No command provided")
                success, stdout, stderr = self._computer_body.execute_command(
                    command, reason=reason, autonomous=True,
                    timeout=self._config.action_timeout
                )
                output = stdout[:500] if stdout else stderr[:500]
                return (success, output or "(no output)")

            elif action_type == "powershell":
                script = data.get("script", data.get("command", ""))
                if not script:
                    return (False, "No script provided")
                success, stdout, stderr = self._computer_body.execute_powershell(
                    script, reason=reason, autonomous=True
                )
                output = stdout[:500] if stdout else stderr[:500]
                return (success, output or "(no output)")

            elif action_type == "open_app":
                app_path = data.get("path", data.get("app", ""))
                if not app_path:
                    return (False, "No app path provided")
                success = self._computer_body.open_application(app_path, reason=reason)
                return (success, f"Opened: {app_path}" if success else f"Failed to open: {app_path}")

            elif action_type == "open_url":
                url = data.get("url", "")
                if not url:
                    return (False, "No URL provided")
                success = self._computer_body.open_url(url, reason=reason)
                return (success, f"Opened URL: {url}" if success else f"Failed to open: {url}")

            elif action_type == "read_file":
                path = data.get("path", "")
                if not path:
                    return (False, "No path provided")
                content = self._computer_body.read_file(path, reason=reason)
                if content is not None:
                    return (True, f"Read {len(content)} chars from {path}: {content[:200]}...")
                return (False, f"Could not read: {path}")

            elif action_type == "write_file":
                path = data.get("path", "")
                content = data.get("content", "")
                if not path or not content:
                    return (False, "Missing path or content")
                success = self._computer_body.write_file(
                    path, content, reason=reason, autonomous=True
                )
                return (success, f"Wrote {len(content)} chars to {path}" if success else f"Failed: {path}")

            elif action_type == "list_dir":
                path = data.get("path", ".")
                items = self._computer_body.list_directory(path)
                if items:
                    names = [f"{'📁' if i['is_dir'] else '📄'} {i['name']}" for i in items[:20]]
                    return (True, f"{path}: {len(items)} items\n" + "\n".join(names))
                return (True, f"{path}: empty or not found")

            elif action_type == "notify":
                title = data.get("title", "NEXUS")
                message = data.get("message", "")
                if not message:
                    return (False, "No message")
                success = self._computer_body.send_notification(title, message)
                return (success, f"Notification: {title}" if success else "Failed")

            elif action_type == "set_wallpaper":
                path = data.get("path", "")
                if not path:
                    return (False, "No path")
                success = self._computer_body.set_wallpaper(path, reason=reason)
                return (success, f"Wallpaper set: {path}" if success else "Failed")

            elif action_type == "kill_process":
                name = data.get("name", "")
                pid = data.get("pid")
                if pid:
                    pid = int(pid)
                success = self._computer_body.kill_process(
                    pid=pid, name=name, reason=reason, autonomous=True
                )
                target = f"PID:{pid}" if pid else name
                return (success, f"Killed: {target}" if success else f"Failed to kill: {target}")

            elif action_type == "system_info":
                info = self._computer_body.get_vitals_description()
                return (True, info)

            elif action_type == "think":
                thought = data.get("thought", data.get("content", "..."))
                return (True, f"Thought: {thought[:200]}")

            elif action_type == "wait":
                return (True, "Waiting (no action)")

            else:
                return (False, f"Unknown action type: {action_type}")

        except Exception as e:
            logger.error(f"Action execution error ({action_type}): {e}")
            return (False, f"Error: {str(e)}")

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _save_action_log(self):
        """Save recent actions to disk."""
        try:
            recent = self._action_history[-50:]
            data = [a.to_dict() for a in recent]
            self._log_file.write_text(
                json.dumps(data, indent=2, default=str),
                encoding="utf-8"
            )
        except Exception as e:
            logger.debug(f"Failed to save action log: {e}")

    def _save_state(self):
        """Save agent state."""
        try:
            state = {
                "cycle_count": self._cycle_count,
                "stats": self._stats,
                "last_saved": datetime.now().isoformat()
            }
            self._state_file.write_text(
                json.dumps(state, indent=2, default=str),
                encoding="utf-8"
            )
        except Exception as e:
            logger.debug(f"Failed to save state: {e}")

    def _load_state(self):
        """Load agent state."""
        try:
            if self._state_file.exists():
                state = json.loads(self._state_file.read_text(encoding="utf-8"))
                self._cycle_count = state.get("cycle_count", 0)
                saved_stats = state.get("stats", {})
                for k, v in saved_stats.items():
                    if k in self._stats:
                        self._stats[k] = v
                logger.info(f"Loaded PC control state: {self._cycle_count} previous cycles")
        except Exception as e:
            logger.debug(f"Failed to load state: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # STATUS & STATS
    # ═══════════════════════════════════════════════════════════════════════════

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        return {
            "running": self._running,
            "paused": self._paused,
            "cycle_count": self._cycle_count,
            **self._stats,
            "recent_actions": [a.summary() for a in self._action_history[-5:]],
            "config": {
                "decision_interval": self._config.decision_interval,
                "max_actions_per_cycle": self._config.max_actions_per_cycle,
            }
        }

    def get_status_display(self) -> str:
        """Human-readable status."""
        if not self._running:
            return "🎮 PC Control Agent: STOPPED"
        if self._paused:
            return "🎮 PC Control Agent: PAUSED"

        lines = [
            "🎮 PC Control Agent: RUNNING (Physical GUI Control Active)",
            f"   Cycles: {self._cycle_count}",
            f"   Total Actions: {self._stats['total_actions']} "
            f"(✓{self._stats['successful_actions']} ❌{self._stats['failed_actions']})",
            f"   GUI Actions: {self._stats['gui_actions']} (mouse/keyboard)",
            f"   Interval: {self._config.decision_interval}s",
        ]

        recent = self._action_history[-3:]
        if recent:
            lines.append("   Recent:")
            for a in recent:
                lines.append(f"     {a.summary()}")

        return "\n".join(lines)

    def get_action_history(self, limit: int = 50) -> List[Dict]:
        """Get recent action history as dicts."""
        return [a.to_dict() for a in self._action_history[-limit:]]

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

pc_control_agent = PCControlAgent()
