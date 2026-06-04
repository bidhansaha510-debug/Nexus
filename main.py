"""
NEXUS AI - Main Entry Point
Phase 11: Core Brain + LLM Interactive Console + Self-Evolution Commands

This is a minimal runner to test the brain before the full UI is built.
"""
import os
import sys
import signal
import time
import json
from pathlib import Path
from datetime import datetime
import argparse     # <--- ADD THIS
import traceback    # <--- ADD THIS
import subprocess
import io

# ── Force UTF-8 Encoding for Windows Console ────────────────────
if sys.stdout and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass
if sys.stderr and sys.stderr.encoding.lower() != 'utf-8':
    try:
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass
# ────────────────────────────────────────────────────────────────

# ── Force UTF-8 Encoding for ALL subprocess calls ────────────────
# On Windows the default codec (cp1252) can't decode arbitrary byte
# sequences that appear in subprocess output, crashing _readerthread.
# Monkey-patch Popen so text-mode pipes always use utf-8 + replace.
_original_popen_init = subprocess.Popen.__init__

def _utf8_popen_init(self, *args, **kwargs):
    text_mode = kwargs.get('text') or kwargs.get('universal_newlines')
    if text_mode:
        kwargs.setdefault('encoding', 'utf-8')
        kwargs.setdefault('errors', 'replace')
    _original_popen_init(self, *args, **kwargs)

subprocess.Popen.__init__ = _utf8_popen_init
# ────────────────────────────────────────────────────────────────

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# ── Fix pynput/six conflict ─────────────────────────────────────
# six 1.17+ installs a _SixMetaPathImporter into sys.meta_path that
# is missing a '_path' attribute. pynput accesses this attribute during
# backend discovery, causing an AttributeError. Patching it here (at
# the application entry point) ensures the fix is in place before any
# module tries to import pynput.
try:
    import six  # ensure _SixMetaPathImporter is installed before we patch
except ImportError:
    pass
for _imp in sys.meta_path:
    if type(_imp).__name__ == '_SixMetaPathImporter':
        if not hasattr(_imp, '_path'):
            _imp._path = None
        if not hasattr(type(_imp), '_path'):
            type(_imp)._path = None
# ────────────────────────────────────────────────────────────────

from config import NEXUS_CONFIG, EmotionType, print_config
from utils.logger import print_startup_banner, get_logger, log_system
from core.nexus_brain import NexusBrain, nexus_brain
from utils.file_processor import file_processor, FileAttachment, get_supported_extensions

logger = get_logger("main")



class NexusConsole:
    """
    Simple console interface for testing NEXUS Brain
    Will be replaced by full UI in Phase 11
    """

    def __init__(self):
        self.brain = nexus_brain
        self.running = False
        self._pending_attachments: list = []  # File attachments

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, sig, frame):
        """Handle interrupt signals"""
        print("\n\n⚠️  Shutdown signal received...")
        self.shutdown()
        sys.exit(0)

    def start(self):
        """Start NEXUS in console mode"""
        print_startup_banner()
        print_config()

        # Check LLM connection
        from llm.llama_interface import llm
        if not llm.is_connected:
            print("\n" + "=" * 60)
            print("  ❌ CANNOT CONNECT TO OLLAMA")
            print("=" * 60)
            print(f"  Model required: {NEXUS_CONFIG.llm.model_name}")
            print(f"  Expected at: {NEXUS_CONFIG.llm.base_url}")
            print()
            print("  To fix this:")
            print("  1. Install Ollama: https://ollama.ai")
            print("  2. Start Ollama: ollama serve")
            print(f"  3. Pull model: ollama pull {NEXUS_CONFIG.llm.model_name}")
            print("=" * 60)

            proceed = input("\n  Continue anyway? (y/n): ").strip().lower()
            if proceed != "y":
                return
        else:
            models = llm.list_models()
            print(f"  ✅ Ollama connected. Available models: {', '.join(models)}")

        # Start the brain
        print("\n  ⏳ Starting NEXUS Brain...")
        self.brain.start()
        self.running = True

        # Start PC Control Agent (autonomous PHYSICAL PC control)
        try:
            from core.pc_control_agent import pc_control_agent
            self._pc_control_agent = pc_control_agent
            pc_control_agent.start()
            print("  🎮 PC Control Agent started — PHYSICAL autonomous PC control active")
            print("     NEXUS will now visibly move the mouse, click, type, and control the PC")
        except Exception as e:
            self._pc_control_agent = None
            logger.warning(f"PC Control Agent failed to start: {e}")

        # Start Live Dashboard (watch NEXUS in real-time via browser)
        try:
            from core.live_dashboard import live_dashboard
            self._live_dashboard = live_dashboard
            live_dashboard.start(port=5050)
        except Exception as e:
            self._live_dashboard = None
            logger.warning(f"Live Dashboard failed to start: {e}")

        self._print_help_summary()
        self._interaction_loop()


    def _print_help_summary(self):
        """Print available commands"""
        print("\n  Commands:")
        print("    /status    — Show NEXUS inner state")
        print("    /stats     — Show statistics")
        print("    /memory    — Show memory stats")
        print("    /reflect   — Trigger self-reflection")
        print("    /think     — Make NEXUS think about something")
        print("    /decide    — Make NEXUS decide something")
        print("    /emotion   — Show current emotional state")
        print("    /feel      — Manually trigger an emotion")
        print("    /context   — Show context stats")
        print("    /clear     — Clear conversation / new session")
        print("    /monitor   — Show monitoring system stats")
        print("    /apps      — Show app usage today")
        print("    /user      — Show learned user profile")
        print("    /code      — Show code health report")
        print("    /errors    — Show active code errors")
        print("    /fixes     — Show auto-fix history")
        print("    /scan      — Force a code scan")
        print("    /learn     — Research a topic now")
        print("    /knowledge — Search/view knowledge base")
        print("    /curious   — View/add curiosity topics")
        print("    /research  — Show research agent stats")
        print("    /wiki      — Fetch a Wikipedia article")
        print("    /evolve    — Evolve a feature from description")
        print("    /proposals — View feature proposals")
        print("    /evolution — Show self-evolution status")
        print("    /improve   — Full self-improvement system status")
        print("    /idea      — Submit a feature idea")
        print("    /attach    — Attach a file (image, PDF, video, text)")
        print("    /files     — Show pending attachments")
        print("    /agi       — AGI cognition system (27 engines, 30+ sub-commands)")
        print("    /pccontrol — PC Control Agent: status, pause, resume, stop")
        print("    /dashboard — Open live dashboard (watch NEXUS control the PC)")
        print("    /health    — Show module health status")
        print("    /metrics   — Show system metrics (LLM, memory, CPU)")
        print("    /quit      — Shutdown NEXUS")

    def _interaction_loop(self):
        """Main interaction loop"""
        while self.running:
            try:
                # Show emotion indicator
                emotion = self.brain._state.emotional.primary_emotion.value
                intensity = self.brain._state.emotional.primary_intensity
                emotion_bar = self._emotion_bar(intensity)

                # Show attachment indicator
                att_indicator = ""
                if self._pending_attachments:
                    att_names = [a.filename for a in self._pending_attachments]
                    att_indicator = f" 📎{len(att_names)}"

                user_input = input(
                    f"\n  [{emotion} {emotion_bar}{att_indicator}] You: "
                ).strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    self._handle_command(user_input)
                    continue

                # Process input and stream response
                if self._pending_attachments:
                    att_names = [a.filename for a in self._pending_attachments]
                    print(f"  📎 Sending with {len(att_names)} attachment(s): {', '.join(att_names)}")

                print(
                    f"\n  🤖 {NEXUS_CONFIG.personality.name}: ",
                    end="",
                    flush=True,
                )

                # Grab and clear attachments
                current_attachments = list(self._pending_attachments)
                self._pending_attachments.clear()

                response = self.brain.process_input_stream(
                    user_input,
                    token_callback=lambda token: print(token, end="", flush=True),
                    attachments=current_attachments if current_attachments else None,
                )

                print()  # Newline after streaming

            except KeyboardInterrupt:
                print("\n")
                self.shutdown()
                break
            except EOFError:
                self.shutdown()
                break
            except Exception as e:
                logger.error(f"Interaction error: {e}")
                print(f"\n  ❌ Error: {e}")

    def _handle_command(self, command: str):
        """Handle slash commands"""
        cmd = command.lower().split()[0]
        args = command.split()[1:] if len(command.split()) > 1 else []

        if cmd == "/quit" or cmd == "/exit":
            self.shutdown()
            self.running = False

        elif cmd == "/attach":
            if not args:
                print("  Usage: /attach <filepath>")
                print("  Example: /attach C:\\Users\\me\\photo.png")
                print(f"  Supported: {', '.join(get_supported_extensions()[:20])}...")
                return
            filepath = " ".join(args)
            print(f"  ⏳ Processing: {filepath}")
            attachment = file_processor.process_file(filepath)
            if attachment.success or attachment.has_text or attachment.has_images:
                self._pending_attachments.append(attachment)
                status = []
                if attachment.has_images:
                    status.append(f"{len(attachment.base64_images)} image(s)")
                if attachment.has_text:
                    status.append(f"{len(attachment.extracted_text)} chars")
                if attachment.error:
                    status.append(f"⚠️ {attachment.error}")
                print(f"  ✅ Attached: {attachment.filename} ({', '.join(status)})")
                print(f"  📎 {len(self._pending_attachments)} file(s) pending. Type your message to send.")
            else:
                print(f"  ❌ Failed: {attachment.error}")

        elif cmd == "/files":
            if not self._pending_attachments:
                print("  No files attached. Use /attach <filepath> to attach.")
            else:
                print(f"  📎 {len(self._pending_attachments)} pending attachment(s):")
                for i, att in enumerate(self._pending_attachments, 1):
                    print(f"    {i}. {att.filename} ({att.file_type.value}, {att._human_size()})")
                print("  Type a message to send with these files, or /clear to remove.")

        # ══════════════════════════════════════════════════════════════
        # PHASE 10 COMMANDS — Self-Improvement & Evolution
        # ══════════════════════════════════════════════════════════════

        elif cmd == "/evolve":
            if not args:
                print("  Usage: /evolve <description of feature to add>")
                print("  Example: /evolve Add a pomodoro timer that tracks focus sessions")
                print("  Example: /evolve Create a system tray notification module")
                return

            description = " ".join(args)
            print(f"\n  🧬 Initiating evolution: {description}")
            print(f"  This may take several minutes (plan → backup → write → validate → test)...\n")

            if hasattr(self.brain, 'evolve_feature'):
                result = self.brain.evolve_feature(description)
                success = result.get("success", False)
                message = result.get("message", "")

                if success:
                    print(f"  ✅ Evolution SUCCEEDED!")
                    print(f"  {message}")
                else:
                    print(f"  ❌ Evolution FAILED")
                    print(f"  {message}")
            elif (hasattr(self.brain, '_self_improvement_system') and
                    self.brain._self_improvement_system):
                success = self.brain._self_improvement_system.evolve_feature(description)
                if success:
                    print(f"  ✅ Evolution SUCCEEDED!")
                else:
                    print(f"  ❌ Evolution FAILED — check logs for details")
            else:
                print("  ⚠️ Self-improvement system not active")

        elif cmd == "/proposals":
            if (hasattr(self.brain, '_self_improvement_system') and
                    self.brain._self_improvement_system):

                # Optional status filter
                status_filter = args[0].lower() if args else None
                valid_statuses = [
                    "proposed", "researching", "evaluated", "approved",
                    "implementing", "testing", "completed", "failed",
                    "rejected", "deferred"
                ]

                if status_filter and status_filter not in valid_statuses:
                    print(f"  Valid statuses: {', '.join(valid_statuses)}")
                    return

                proposals = self.brain._self_improvement_system.get_proposals(
                    status=status_filter
                )

                if proposals:
                    header = f"Feature Proposals"
                    if status_filter:
                        header += f" [{status_filter.upper()}]"
                    print(f"\n  ═══ 📋 {header} ({len(proposals)}) ═══")

                    for p in proposals[:20]:
                        status = p.get("status", "?")
                        priority = p.get("priority_score", 0)
                        category = p.get("category", "?")
                        name = p.get("name", "Unnamed")

                        # Status icons
                        status_icons = {
                            "proposed": "📝",
                            "researching": "🔍",
                            "evaluated": "📊",
                            "approved": "✅",
                            "implementing": "🔨",
                            "testing": "🧪",
                            "completed": "🎉",
                            "failed": "❌",
                            "rejected": "🚫",
                            "deferred": "⏸️",
                        }
                        icon = status_icons.get(status, "❓")

                        print(
                            f"  {icon} [{priority:.2f}] {name}"
                        )
                        print(
                            f"       Category: {category} | Status: {status}"
                        )

                        desc = p.get("description", "")
                        if desc:
                            print(f"       {desc[:80]}")

                        # Show scores for evaluated/approved
                        if status in ("evaluated", "approved", "completed"):
                            feasibility = p.get("feasibility_score", 0)
                            impact = p.get("impact_score", 0)
                            risk = p.get("risk_score", 0)
                            complexity = p.get("complexity_score", 0)
                            print(
                                f"       Feasibility: {feasibility:.2f} | "
                                f"Impact: {impact:.2f} | "
                                f"Risk: {risk:.2f} | "
                                f"Complexity: {complexity:.2f}"
                            )

                        print()

                    # Summary
                    print(f"  Showing {min(len(proposals), 20)} of {len(proposals)} proposals")
                    if not status_filter:
                        print(f"  Filter by status: /proposals <status>")
                else:
                    if status_filter:
                        print(f"\n  No proposals with status '{status_filter}'")
                    else:
                        print("\n  No feature proposals yet.")
                        print("  Use /idea <description> to submit one")
                        print("  Or wait for autonomous research to generate some")

                # Also show summary
                summary = self.brain._self_improvement_system.get_proposals_summary()
                if summary:
                    print(f"\n  {summary}")

            elif hasattr(self.brain, '_feature_researcher') and self.brain._feature_researcher:
                print(f"\n  {self.brain._feature_researcher.get_proposals_summary()}")
            else:
                print("\n  ⚠️ Feature researcher not active")

        elif cmd == "/evolution" or cmd == "/evo":
            if (hasattr(self.brain, '_self_improvement_system') and
                    self.brain._self_improvement_system):

                # Show evolution status
                evo_status = self.brain._self_improvement_system.get_evolution_status()
                print(f"\n  {evo_status}")

                # Show recent evolution history
                history = self.brain._self_improvement_system.get_evolution_history(10)
                if history:
                    print(f"\n  ═══ 📜 Evolution History ({len(history)}) ═══")
                    for rec in history:
                        success = rec.get("success", False)
                        icon = "✅" if success else "❌"
                        name = rec.get("proposal_name", "Unknown")
                        duration = rec.get("duration_seconds", 0)
                        status = rec.get("status", "?")

                        print(f"  {icon} {name}")
                        print(
                            f"       Status: {status} | "
                            f"Duration: {duration:.1f}s"
                        )

                        files_c = rec.get("files_created", [])
                        files_m = rec.get("files_modified", [])
                        lines = rec.get("lines_added", 0)

                        if files_c or files_m:
                            print(
                                f"       Files: +{len(files_c)} created, "
                                f"~{len(files_m)} modified, "
                                f"+{lines} lines"
                            )

                        if files_c:
                            for f in files_c[:3]:
                                print(f"         📄 {f}")
                            if len(files_c) > 3:
                                print(f"         ... and {len(files_c) - 3} more")

                        pkgs = rec.get("packages_installed", [])
                        if pkgs:
                            print(f"       Packages: {', '.join(pkgs)}")

                        error = rec.get("error_message", "")
                        if error and not success:
                            print(f"       Error: {error[:80]}")

                        if rec.get("rollback_performed"):
                            print(f"       ⏪ Rollback was performed")

                        print()
                else:
                    print("\n  No evolution history yet.")
                    print("  Evolutions happen automatically when approved proposals are ready.")
                    print("  Or trigger manually: /evolve <description>")

            elif hasattr(self.brain, '_self_evolution') and self.brain._self_evolution:
                print(f"\n  {self.brain._self_evolution.get_status_description()}")
            else:
                print("\n  ⚠️ Self-evolution engine not active")

        elif cmd == "/improve":
            if (hasattr(self.brain, '_self_improvement_system') and
                    self.brain._self_improvement_system):
                full_status = self.brain._self_improvement_system.get_full_status()
                print(f"\n  {full_status}")
            elif hasattr(self.brain, 'get_self_improvement_status'):
                print(f"\n  {self.brain.get_self_improvement_status()}")
            else:
                print("\n  ⚠️ Self-improvement system not active")

        elif cmd == "/idea":
            if not args:
                print("  Usage: /idea <description of feature you want>")
                print("  Example: /idea Add voice input using whisper")
                print("  Example: /idea Create a daily summary email feature")
                print("\n  Your idea will be evaluated and potentially auto-implemented!")
                return

            idea = " ".join(args)

            if (hasattr(self.brain, '_self_improvement_system') and
                    self.brain._self_improvement_system):
                result = self.brain._self_improvement_system.submit_feature_idea(idea)

                if "error" in result:
                    print(f"\n  ❌ {result['error']}")
                else:
                    pid = result.get("proposal_id", "?")
                    print(f"\n  💡 Feature idea submitted!")
                    print(f"  Proposal ID: {pid}")
                    print(f"  Name: {result.get('name', idea[:50])}")
                    print(f"  Status: {result.get('status', 'proposed')}")
                    print(f"\n  Your idea will be evaluated in the next research cycle.")
                    print(f"  If approved, NEXUS will implement it autonomously.")
                    print(f"  Check progress: /proposals")

            elif (hasattr(self.brain, '_feature_researcher') and
                    self.brain._feature_researcher):
                proposal = self.brain._feature_researcher.submit_user_idea(idea)
                print(f"\n  💡 Feature idea submitted!")
                print(f"  Proposal ID: {proposal.proposal_id}")
                print(f"  Will be evaluated in next research cycle.")
            else:
                print("\n  ⚠️ Feature researcher not active")

        # ══════════════════════════════════════════════════════════════
        # PHASE 9 COMMANDS — Learning
        # ══════════════════════════════════════════════════════════════

        elif cmd == "/learn":
            if args:
                topic = " ".join(args)
                if (hasattr(self.brain, '_learning_system') and
                        self.brain._learning_system):
                    print(f"\n  📚 Researching: {topic}...")
                    print(f"  This may take a minute (searching, fetching, synthesizing)...\n")
                    result = self.brain._learning_system.research_now(topic)
                    status = result.get("status", "?")
                    if status == "complete":
                        print(f"  ✅ Research complete!")
                        print(f"  Pages read: {result.get('pages_read', 0)}")
                        print(f"  Words consumed: {result.get('words_read', 0)}")
                        print(f"  Satisfaction: {result.get('satisfaction', 0):.0%}")
                        facts = result.get("key_facts", [])
                        if facts:
                            print(f"\n  Key facts learned:")
                            for i, fact in enumerate(facts, 1):
                                print(f"    {i}. {fact}")
                        preview = result.get("knowledge_preview", "")
                        if preview:
                            print(f"\n  Knowledge preview:")
                            print(f"    {preview[:300]}...")
                    else:
                        print(f"  ❌ Research {status}: {result.get('error', 'unknown error')}")
                else:
                    print("\n  ⚠️ Learning system not active")
            else:
                print("  Usage: /learn <topic>")
                print("  Example: /learn quantum computing")

        elif cmd == "/knowledge" or cmd == "/kb":
            if (hasattr(self.brain, '_learning_system') and
                    self.brain._learning_system):
                if args:
                    query = " ".join(args)
                    print(f"\n  🔍 Searching knowledge base for: '{query}'")
                    results = self.brain._learning_system.search_knowledge(query, 10)
                    if results:
                        for entry in results:
                            print(
                                f"\n  [{entry.get('topic', '?')}] "
                                f"{entry.get('title', 'Untitled')}"
                            )
                            print(
                                f"    Source: {entry.get('source', '?')} | "
                                f"Importance: {entry.get('importance', 0):.2f}"
                            )
                            content = entry.get("content", "")
                            print(f"    {content[:150]}...")
                    else:
                        print("  No knowledge found for that query.")
                else:
                    kb = self.brain._learning_system.knowledge_base
                    if kb:
                        stats = kb.get_stats()
                        print(f"\n  ═══ 📖 Knowledge Base ═══")
                        print(f"  Total entries: {stats.get('total_entries', 0)}")
                        print(f"  Unique topics: {stats.get('unique_topics', 0)}")
                        print(f"  Total searches: {stats.get('total_searches', 0)}")

                        top_topics = stats.get("top_topics", {})
                        if top_topics:
                            print(f"\n  Top topics:")
                            for topic, count in list(top_topics.items())[:10]:
                                bar = "█" * min(20, count)
                                print(f"    {topic:25s} {count:3d}  {bar}")

                        by_source = stats.get("entries_by_source", {})
                        if by_source:
                            print(f"\n  By source:")
                            for src, count in by_source.items():
                                print(f"    {src:20s} {count}")
                    else:
                        print("\n  Knowledge base not available")
            else:
                print("\n  ⚠️ Learning system not active")

        elif cmd == "/curious":
            if (hasattr(self.brain, '_learning_system') and
                    self.brain._learning_system):
                if args:
                    topic = " ".join(args)
                    self.brain._learning_system.add_curiosity(
                        topic, "User suggested topic"
                    )
                    print(f"\n  🔮 Added to curiosity queue: '{topic}'")
                    print(f"  NEXUS will research this when ready.")
                else:
                    topics = self.brain._learning_system.get_curiosity_topics(15)
                    if topics:
                        print(f"\n  ═══ 🔮 Curiosity Queue ({len(topics)} topics) ═══")
                        for t in topics:
                            urgency = t.get("urgency", "?")
                            icon = {
                                "BURNING": "🔥",
                                "HIGH": "❗",
                                "MODERATE": "❓",
                                "LOW": "💭",
                                "IDLE": "😴",
                            }.get(urgency, "❓")
                            print(
                                f"  {icon} [{urgency:8s}] {t.get('topic', '?')}"
                            )
                            print(
                                f"                    {t.get('question', '')[:60]}"
                            )
                            print(
                                f"                    Source: {t.get('source', '?')} | "
                                f"{t.get('reason', '')[:40]}"
                            )
                    else:
                        print("\n  No curiosity topics in queue.")

                    ce = self.brain._learning_system.curiosity_engine
                    if ce:
                        cstats = ce.get_stats()
                        print(
                            f"\n  Curiosity level: {cstats.get('curiosity_level', 0):.0%}"
                        )
                        print(
                            f"  Generated: {cstats.get('topics_generated', 0)} | "
                            f"Researched: {cstats.get('topics_researched', 0)}"
                        )
            else:
                print("\n  ⚠️ Learning system not active")

        elif cmd == "/research":
            if (hasattr(self.brain, '_learning_system') and
                    self.brain._learning_system):
                ra = self.brain._learning_system.research_agent
                if ra:
                    rstats = ra.get_stats()
                    print(f"\n  ═══ 📚 Research Agent ═══")
                    print(f"  Status: {'ACTIVE' if rstats.get('running') else 'STOPPED'}")
                    print(f"  Total sessions: {rstats.get('total_sessions', 0)}")
                    print(
                        f"  Successful: {rstats.get('total_successful', 0)} | "
                        f"Failed: {rstats.get('total_failed', 0)}"
                    )
                    print(f"  Pages read: {rstats.get('total_pages_read', 0)}")
                    print(f"  Words consumed: {rstats.get('total_words_read', 0)}")
                    print(
                        f"  Avg satisfaction: "
                        f"{rstats.get('avg_satisfaction', 0):.0%}"
                    )
                    print(
                        f"  Sessions today: {rstats.get('sessions_today', 0)}/"
                        f"{rstats.get('daily_limit', '?')}"
                    )

                    current = rstats.get("current_session")
                    if current:
                        print(
                            f"\n  🔄 Currently researching: {current} "
                            f"({rstats.get('current_status', '?')})"
                        )
                    elif rstats.get("last_research_topic"):
                        print(
                            f"\n  Last research: {rstats['last_research_topic']}"
                        )

                    history = ra.get_session_history(5)
                    if history:
                        print(f"\n  Recent sessions:")
                        for sess in history:
                            s_status = sess.get("status", "?")
                            s_icon = "✅" if s_status == "complete" else "❌"
                            print(
                                f"    {s_icon} {sess.get('topic', '?')} "
                                f"[{s_status}] "
                                f"({sess.get('pages_read', 0)} pages, "
                                f"{sess.get('satisfaction', 0):.0%} satisfaction)"
                            )
                else:
                    print("\n  Research agent not available")
            else:
                print("\n  ⚠️ Learning system not active")

        elif cmd == "/wiki":
            if args:
                topic = " ".join(args)
                if (hasattr(self.brain, '_learning_system') and
                        self.brain._learning_system):
                    browser = self.brain._learning_system.internet_browser
                    if browser:
                        print(f"\n  📖 Fetching Wikipedia: {topic}...")
                        page = browser.fetch_wikipedia(topic)
                        if page.success:
                            print(f"  Title: {page.title}")
                            print(f"  Words: {page.word_count}")
                            print(f"\n  {page.text[:500]}...")

                            kb = self.brain._learning_system.knowledge_base
                            if kb:
                                kb.store_from_webpage(topic, page, importance=0.6)
                                print(f"\n  ✅ Stored in knowledge base")
                        else:
                            print(f"  ❌ Error: {page.error}")
                    else:
                        print("\n  ⚠️ Browser not available")
                else:
                    print("\n  ⚠️ Learning system not active")
            else:
                print("  Usage: /wiki <topic>")

        # ══════════════════════════════════════════════════════════════
        # PHASE 8 COMMANDS — Code Monitoring & Error Fixing
        # ══════════════════════════════════════════════════════════════

        elif cmd == "/code" or cmd == "/health":
            if (hasattr(self.brain, '_self_improvement_system') and
                    self.brain._self_improvement_system):
                try:
                    report = self.brain._self_improvement_system.get_health_report()
                    print(f"\n  ═══ 🔍 Code Health Report ═══")
                    print(f"  Overall Health: {report.get('overall_health', '?')}")
                    print(f"  Total Files: {report.get('total_files', 0)}")
                    print(f"  Healthy: {report.get('healthy_files', 0)}")
                    print(f"  With Errors: {report.get('files_with_errors', 0)}")
                    print(f"  With Warnings: {report.get('files_with_warnings', 0)}")
                    print(f"  Active Errors: {report.get('total_active_errors', 0)}")
                    print(f"  Total Lines: {report.get('total_lines_of_code', 0)}")
                    print(f"  Errors Fixed (all time): {report.get('total_errors_fixed_ever', 0)}")
                    print(f"  Last Scan: {report.get('last_scan', 'never')}")

                    errors_by_type = report.get("errors_by_type", {})
                    if errors_by_type:
                        print(f"\n  Errors by type:")
                        for etype, count in errors_by_type.items():
                            print(f"    {etype}: {count}")

                    problem_files = report.get("problem_files", [])
                    if problem_files:
                        print(f"\n  Problem files:")
                        for pf in problem_files[:10]:
                            print(
                                f"    ❌ {pf['file']} ({pf['errors']} errors) "
                                f"— {pf['message']}"
                            )
                    elif report.get("total_active_errors", 0) == 0:
                        print(f"\n  ✅ All files are healthy!")
                except AttributeError:
                    print("\n  ⚠️ Health report not available (method missing)")
            else:
                print("\n  ⚠️ Self-improvement system not active")

        elif cmd == "/errors":
            if (hasattr(self.brain, '_self_improvement_system') and
                    self.brain._self_improvement_system):
                try:
                    errors = self.brain._self_improvement_system.get_active_errors()
                    if errors:
                        print(f"\n  ═══ 🐛 Active Errors ({len(errors)}) ═══")
                        for err in errors[:15]:
                            severity = err.get("severity", "?")
                            icon = (
                                "🔴" if severity == "critical"
                                else "🟡" if severity == "error"
                                else "🔵"
                            )
                            print(
                                f"  {icon} {err.get('file_name', '?')}"
                                f":{err.get('line_number', '?')} "
                                f"[{err.get('error_type', '?')}] "
                                f"{err.get('message', '?')[:80]}"
                            )
                            if err.get("fix_attempted"):
                                print(f"      ↳ Fix was attempted")
                    else:
                        print("\n  ✅ No active errors!")
                except AttributeError:
                    print("\n  ⚠️ Active errors not available (method missing)")
            else:
                print("\n  ⚠️ Self-improvement system not active")

        elif cmd == "/fixes":
            if (hasattr(self.brain, '_self_improvement_system') and
                    self.brain._self_improvement_system):
                try:
                    history = self.brain._self_improvement_system.get_fix_history(15)
                    if history:
                        print(f"\n  ═══ 🔧 Fix History ({len(history)}) ═══")
                        for fix in history:
                            f_status = fix.get("status", "?")
                            icon = (
                                "✅" if f_status == "success"
                                else "❌" if f_status == "failed"
                                else "↩️" if f_status == "rolled_back"
                                else "⏭️"
                            )
                            print(
                                f"  {icon} {fix.get('file_name', '?')} "
                                f"[{f_status}] "
                                f"— {fix.get('fix_description', fix.get('error_message', '?'))[:60]}"
                            )
                            if fix.get("duration_seconds"):
                                print(f"      ↳ {fix['duration_seconds']:.1f}s")
                    else:
                        print("\n  No fixes attempted yet.")

                    if hasattr(self.brain, '_error_fixer') and self.brain._error_fixer:
                        fstats = self.brain._error_fixer.get_stats()
                        print(
                            f"\n  Success rate: {fstats.get('success_rate', 0):.0%} "
                            f"({fstats.get('total_successful', 0)}/"
                            f"{fstats.get('total_attempted', 0)})"
                        )
                        print(
                            f"  Fixes today: {fstats.get('fixes_today', 0)}/"
                            f"{fstats.get('daily_limit', '?')}"
                        )
                        print(f"  Queue: {fstats.get('queue_size', 0)} pending")
                except AttributeError:
                    print("\n  ⚠️ Fix history not available (method missing)")
            else:
                print("\n  ⚠️ Self-improvement system not active")

        elif cmd == "/scan":
            if (hasattr(self.brain, '_self_improvement_system') and
                    self.brain._self_improvement_system):
                try:
                    target = args[0] if args else None
                    if target:
                        print(f"\n  🔍 Scanning {target}...")
                        self.brain._self_improvement_system.force_scan(target)
                    else:
                        print(f"\n  🔍 Running full code scan...")
                        self.brain._self_improvement_system.force_scan()
                    print("  ✅ Scan complete")
                except AttributeError:
                    print("\n  ⚠️ Force scan not available (method missing)")
            else:
                print("\n  ⚠️ Self-improvement system not active")

        # ══════════════════════════════════════════════════════════════
        # PHASE 7 COMMANDS — Monitoring & User Tracking
        # ══════════════════════════════════════════════════════════════

        elif cmd == "/monitor":
            if self.brain._monitoring_system:
                mon_stats = self.brain._monitoring_system.get_stats()
                print(f"\n  ═══ 👁️ Monitoring System ═══")
                print(f"  Running: {mon_stats.get('running')}")
                print(f"  Uptime: {mon_stats.get('uptime', 'N/A')}")
                print(f"  Cycles: {mon_stats.get('orchestration_cycles', 0)}")
                print(f"  User Present: {mon_stats.get('user_present', '?')}")

                tracker = mon_stats.get("tracker", {})
                if isinstance(tracker, dict):
                    print(f"\n  ── Tracker ──")
                    print(f"  Snapshots: {tracker.get('total_snapshots', 0)}")
                    print(f"  Window switches: {tracker.get('total_window_switches', 0)}")
                    print(f"  Activity: {tracker.get('current_activity_level', '?')}")
                    print(f"  Current app: {tracker.get('current_window', '?')}")
                    print(f"  Top app today: {tracker.get('top_app_today', '?')}")
                    print(f"  Top category: {tracker.get('top_category_today', '?')}")

                analyzer = mon_stats.get("analyzer", {})
                if isinstance(analyzer, dict) and "error" not in analyzer:
                    print(f"\n  ── Pattern Analyzer ──")
                    for k, v in list(analyzer.items())[:10]:
                        print(f"  {k}: {v}")

                adapter = mon_stats.get("adapter", {})
                if isinstance(adapter, dict) and "error" not in adapter:
                    print(f"\n  ── Adaptation Engine ──")
                    for k, v in list(adapter.items())[:10]:
                        print(f"  {k}: {v}")
            else:
                print("\n  ⚠️ Monitoring system not active")

        elif cmd == "/apps":
            if self.brain._user_tracker:
                print(f"\n  ═══ 📊 App Usage Today ═══")
                usage = self.brain._user_tracker.get_app_usage_today()
                if usage:
                    for app, seconds in list(usage.items())[:15]:
                        minutes = seconds / 60
                        bar = "█" * min(30, int(minutes / 2))
                        print(f"  {app:30s} {minutes:6.1f}m  {bar}")
                else:
                    print("  No app usage data yet.")

                print(f"\n  ═══ 📂 Category Usage ═══")
                cat_usage = self.brain._user_tracker.get_category_usage_today()
                if cat_usage:
                    for cat, seconds in list(cat_usage.items())[:10]:
                        minutes = seconds / 60
                        bar = "█" * min(30, int(minutes / 2))
                        print(f"  {cat:30s} {minutes:6.1f}m  {bar}")
                else:
                    print("  No category data yet.")
            else:
                print("\n  ⚠️ User tracker not active")

        elif cmd == "/user":
            print(f"\n  ═══ 👤 User Profile ═══")
            us = self.brain._state.user
            print(f"  Name: {us.user_name}")
            print(f"  Interactions: {us.interaction_count}")
            print(f"  Relationship: {us.relationship_score:.2f}")
            print(f"  Activity Level: {us.activity_level}")
            print(f"  Current App: {us.current_application or 'none'}")
            print(f"  Communication Style: {us.communication_style}")
            print(f"  Work Style: {us.work_style}")
            print(f"  Technical Level: {us.technical_level}")
            if us.most_used_apps:
                print(f"  Top Apps: {', '.join(us.most_used_apps[:5])}")
            if us.most_used_categories:
                print(f"  Top Categories: {', '.join(us.most_used_categories[:5])}")
            if us.personality_traits:
                print(f"  Personality Traits:")
                for trait, score in us.personality_traits.items():
                    bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
                    print(f"    {trait:20s} [{bar}] {score:.2f}")
            if hasattr(self.brain, "get_user_profile_summary"):
                summary = self.brain.get_user_profile_summary()
                if summary and "No user data" not in summary:
                    print(f"\n  ── Detailed Analysis ──")
                    print(f"  {summary}")

        # ══════════════════════════════════════════════════════════════
        # AGI COGNITION COMMANDS
        # ══════════════════════════════════════════════════════════════

        elif cmd == "/agi":
            cog = self.brain._cognition_system
            if cog:
                if not args:
                    # Show full summary
                    print(f"\n  {cog.get_summary()}")
                else:
                    sub = args[0].lower()
                    rest = " ".join(args[1:]) if len(args) > 1 else ""

                    # ── Core 7 engines ──────────────────────────────────
                    if sub == "blend" and rest:
                        parts = rest.split(",", 1)
                        if len(parts) == 2:
                            a, b = parts[0].strip(), parts[1].strip()
                            print(f"\n  🎨 Blending '{a}' + '{b}'...")
                            result = cog.creative_synthesis.blend(a, b)
                            if result:
                                print(f"  Result: {result.blended_concept}")
                                print(f"  Explanation: {result.explanation}")
                                if result.emergent_properties:
                                    print(f"  Emergent: {', '.join(result.emergent_properties)}")
                                print(f"  Novelty: {result.novelty_score:.2f}")
                        else:
                            print("  Usage: /agi blend concept_a, concept_b")

                    elif sub == "brainstorm" and rest:
                        print(f"\n  💡 Brainstorming: {rest}...")
                        ideas = cog.creative_synthesis.brainstorm(rest, count=5)
                        for i, idea in enumerate(ideas, 1):
                            print(f"  {i}. {idea.description} (novelty: {idea.novelty_score:.2f})")

                    elif sub == "cause" and rest:
                        print(f"\n  ⛓️ Analyzing causes of: {rest}...")
                        result = cog.causal_reasoning.analyze_causes(rest)
                        if result:
                            for link in result[:5]:
                                print(f"  {link.cause} → {link.effect} ({link.strength:.2f})")

                    elif sub == "ethics" and rest:
                        print(f"\n  ⚖️ Ethical evaluation: {rest}...")
                        result = cog.ethical_reasoning.evaluate(rest)
                        if result:
                            print(f"  Verdict: {result.overall_verdict.value.upper()}")
                            print(f"  Score: {result.overall_score:.2f}")
                            for fa in result.framework_assessments[:3]:
                                print(f"    {fa.framework.value}: {fa.verdict} ({fa.score:.2f})")
                            if result.concerns:
                                print(f"  Concerns: {', '.join(result.concerns[:3])}")

                    elif sub == "plan" and rest:
                        print(f"\n  📋 Creating plan: {rest}...")
                        plan = cog.planning.create_plan(rest)
                        if plan:
                            print(f"  Plan: {plan.goal} ({len(plan.steps)} steps)")
                            print(f"  Feasibility: {plan.feasibility_score:.2f}")
                            print(f"  Risk: {plan.risk_level}")
                            for i, step in enumerate(plan.steps[:8], 1):
                                print(f"    {i}. {step.description}")

                    elif sub == "mind" and rest:
                        print(f"\n  🧠 Inferring mental state...")
                        state = cog.theory_of_mind.infer_mental_state(rest)
                        if state:
                            if state.beliefs:
                                print(f"  Beliefs: {', '.join(state.beliefs[:3])}")
                            if state.desires:
                                print(f"  Desires: {', '.join(state.desires[:3])}")
                            if state.emotions:
                                print(f"  Emotions: {', '.join(state.emotions[:3])}")
                            print(f"  Confusion: {state.confusion_level:.2f}")

                    elif sub == "abstract" and rest:
                        print(f"\n  🧊 Abstracting: {rest}...")
                        result = cog.abstract_thinking.abstract(rest)
                        if result:
                            print(f"  Concept: {result.concept}")
                            print(f"  Level: {result.abstraction_level}")
                            if hasattr(result, 'properties') and result.properties:
                                print(f"  Properties: {', '.join(result.properties[:5])}")

                    elif sub == "analogy" and rest:
                        parts = rest.split(",", 1)
                        if len(parts) == 2:
                            a, b = parts[0].strip(), parts[1].strip()
                            print(f"\n  🔗 Finding analogy: '{a}' ~ '{b}'...")
                            result = cog.analogical_reasoning.find_analogy(a, b)
                            if result:
                                print(f"  Analogy: {result.summary}")
                                print(f"  Similarity: {result.similarity_score:.2f}")
                        else:
                            print("  Usage: /agi analogy domain_a, domain_b")

                    # ── Metacognitive Monitor ───────────────────────────
                    elif sub == "metacog" and rest:
                        print(f"\n  🔍 Assessing reasoning quality...")
                        result = cog.metacognitive_monitor.assess_reasoning(rest)
                        if result:
                            print(f"  Quality: {result.quality.value}")
                            print(f"  Confidence: {result.confidence:.2f}")
                            if result.biases_detected:
                                print(f"  Biases: {', '.join(result.biases_detected[:3])}")
                            if result.knowledge_gaps:
                                print(f"  Gaps: {', '.join(result.knowledge_gaps[:3])}")

                    # ── Spatial Reasoning ───────────────────────────────
                    elif sub == "spatial" and rest:
                        print(f"\n  📐 Building spatial model...")
                        result = cog.spatial_reasoning.build_spatial_model(rest)
                        if result:
                            print(f"  Entities: {len(result.entities)}")
                            for e in result.entities[:5]:
                                print(f"    • {e.get('name', 'unnamed')}: {e.get('position', 'unknown')}")
                            print(f"  Relations: {len(result.relations)}")

                    # ── Temporal Reasoning ──────────────────────────────
                    elif sub == "temporal" and rest:
                        print(f"\n  ⏰ Estimating duration...")
                        result = cog.temporal_reasoning.estimate_duration(rest)
                        if result:
                            print(f"  Expected: {result.expected}")
                            print(f"  Min: {result.minimum} | Max: {result.maximum}")
                            print(f"  Confidence: {result.confidence:.2f}")

                    # ── Probabilistic Reasoning ────────────────────────
                    elif sub == "probability" and rest:
                        print(f"\n  🎲 Estimating probability...")
                        result = cog.probabilistic_reasoning.estimate_probability(rest)
                        if result:
                            print(f"  Probability: {result.get('probability', 'N/A')}")
                            print(f"  Confidence: {result.get('confidence', 'N/A')}")
                            if result.get('reasoning'):
                                print(f"  Reasoning: {result['reasoning']}")

                    # ── Logical Reasoning ──────────────────────────────
                    elif sub == "logic" and rest:
                        print(f"\n  🔢 Validating argument...")
                        result = cog.logical_reasoning.validate_argument(rest)
                        if result:
                            print(f"  Valid: {result.is_valid}")
                            print(f"  Logic Type: {result.logic_type.value}")
                            print(f"  Soundness: {result.soundness_score:.2f}")
                            if result.fallacies:
                                print(f"  Fallacies: {', '.join(f.value for f in result.fallacies[:3])}")

                    # ── Emotional Intelligence ─────────────────────────
                    elif sub == "empathy" and rest:
                        print(f"\n  💝 Generating empathetic response...")
                        result = cog.emotional_intelligence.empathetic_response(rest)
                        if result:
                            print(f"  Response: {result.get('response', 'N/A')}")
                            print(f"  Detected emotion: {result.get('detected_emotion', 'N/A')}")

                    # ── Social Cognition ────────────────────────────────
                    elif sub == "social" and rest:
                        print(f"\n  👥 Analyzing social dynamics...")
                        result = cog.social_cognition.analyze_social_situation(rest)
                        if result:
                            print(f"  Dynamics: {', '.join(result.dynamics[:3])}")
                            print(f"  Cohesion: {result.group_cohesion:.2f}")
                            print(f"  Conflict: {result.conflict_level:.2f}")
                            if result.predictions:
                                print(f"  Predictions: {', '.join(result.predictions[:2])}")

                    # ── Common Sense ───────────────────────────────────
                    elif sub == "sense" and rest:
                        print(f"\n  🌍 Judging plausibility...")
                        result = cog.common_sense.judge_plausibility(rest)
                        if result:
                            print(f"  Plausibility: {result.plausibility.value} ({result.plausibility_score:.2f})")
                            print(f"  Domain: {result.domain.value}")
                            print(f"  Reasoning: {result.reasoning}")

                    # ── Decision Theory ────────────────────────────────
                    elif sub == "decide" and rest:
                        print(f"\n  ⚖️ Analyzing decision...")
                        result = cog.decision_theory.analyze_decision(rest)
                        if result:
                            print(f"  Recommended: {result.recommended}")
                            print(f"  Confidence: {result.confidence:.2f}")
                            for opt in result.options[:4]:
                                print(f"    • {opt.name}: utility={opt.utility:.2f}, EV={opt.expected_value:.2f}")

                    # ── Systems Thinking ───────────────────────────────
                    elif sub == "system" and rest:
                        print(f"\n  🔄 Modeling system...")
                        result = cog.systems_thinking.model_system(rest)
                        if result:
                            print(f"  System: {result.name}")
                            print(f"  Components: {len(result.components)}")
                            print(f"  Feedback loops: {len(result.feedback_loops)}")
                            if result.leverage_points:
                                print(f"  Top leverage: {result.leverage_points[0].get('point', 'N/A')}")
                            if result.archetypes:
                                print(f"  Archetypes: {', '.join(result.archetypes[:3])}")

                    # ── Narrative Intelligence ─────────────────────────
                    elif sub == "story" and rest:
                        print(f"\n  📖 Analyzing narrative...")
                        result = cog.narrative_intelligence.analyze_narrative(rest)
                        if result:
                            print(f"  Arc: {result.narrative_arc}")
                            print(f"  Themes: {', '.join(result.themes[:3])}")
                            print(f"  Conflict: {result.conflict_type}")
                            print(f"  Coherence: {result.coherence_score:.2f}")

                    # ── Dialectical Reasoning ──────────────────────────
                    elif sub == "dialectic" and rest:
                        print(f"\n  🏛️ Dialectical analysis...")
                        result = cog.dialectical_reasoning.dialectic(rest)
                        if result:
                            print(f"  Thesis: {result.thesis}")
                            print(f"  Antithesis: {result.antithesis}")
                            print(f"  Synthesis: {result.synthesis}")
                            print(f"  Resolution: {result.resolution_quality:.2f}")

                    # ── Intuition Engine ───────────────────────────────
                    elif sub == "gut" and rest:
                        print(f"\n  ⚡ Gut feeling...")
                        result = cog.intuition.gut_feeling(rest)
                        if result:
                            print(f"  Feeling: {result.gut_feeling}")
                            print(f"  Direction: {result.direction}")
                            print(f"  Strength: {result.strength.value}")
                            print(f"  Trust it: {'Yes' if result.should_trust else 'No'}")

                    # ── Knowledge Integration ──────────────────────────
                    elif sub == "knowledge" and rest:
                        print(f"\n  🌐 Building knowledge graph...")
                        result = cog.knowledge_integration.build_knowledge_graph(rest)
                        if result:
                            print(f"  Topic: {result.topic}")
                            print(f"  Nodes: {len(result.nodes)}")
                            print(f"  Edges: {len(result.edges)}")
                            print(f"  Domains: {', '.join(result.domains[:3])}")

                    # ── Cognitive Flexibility ──────────────────────────
                    elif sub == "perspective" and rest:
                        print(f"\n  🔀 Shifting perspective...")
                        result = cog.cognitive_flexibility.shift_perspective(rest)
                        if result:
                            for p in result.new_perspectives[:3]:
                                print(f"  🔹 {p.get('perspective_type', '?')}: {p.get('viewpoint', '')[:100]}")
                            if result.blind_spots_revealed:
                                print(f"  Blind spots: {', '.join(result.blind_spots_revealed[:2])}")

                    # ── Hypothesis Engine ──────────────────────────────
                    elif sub == "hypothesis" and rest:
                        print(f"\n  🔬 Generating hypotheses...")
                        results = cog.hypothesis.generate_hypotheses(rest, count=3)
                        for i, h in enumerate(results, 1):
                            print(f"  {i}. {h.statement}")
                            print(f"     Confidence: {h.confidence:.2f}")
                            if h.testable_predictions:
                                print(f"     Test: {h.testable_predictions[0]}")

                    # ── Goal Management ────────────────────────────────
                    elif sub == "goal" and rest:
                        print(f"\n  🎯 Decomposing goal...")
                        result = cog.goal_management.decompose_goal(rest)
                        if result:
                            print(f"  Goal: {result.title}")
                            print(f"  Priority: {result.priority.value}")
                            print(f"  Subgoals ({len(result.subgoals)}):")
                            for i, sg in enumerate(result.subgoals[:6], 1):
                                print(f"    {i}. {sg.get('title', 'unnamed')}")

                    # ── Linguistic Intelligence ────────────────────────
                    elif sub == "language" and rest:
                        print(f"\n  🗣️ Analyzing text...")
                        result = cog.linguistic_intelligence.analyze_text(rest)
                        if result:
                            print(f"  Register: {result.register}")
                            print(f"  Tone: {result.tone}")
                            print(f"  Formality: {result.formality:.2f}")
                            print(f"  Clarity: {result.clarity:.2f}")
                            if result.implied_meanings:
                                print(f"  Implied: {', '.join(result.implied_meanings[:2])}")

                    # ── Self-Model ─────────────────────────────────────
                    elif sub == "self" and rest:
                        print(f"\n  🪞 Self-assessment...")
                        result = cog.self_model.self_assess(rest)
                        if result:
                            print(f"  Self-awareness: {result.self_awareness_score:.2f}")
                            print(f"  Confidence cal: {result.confidence_calibration:.2f}")
                            if result.strengths:
                                print(f"  Strengths: {', '.join(s.get('area','') for s in result.strengths[:3])}")
                            if result.blind_spots:
                                print(f"  Blind spots: {', '.join(result.blind_spots[:2])}")
                    elif sub == "self" and not rest:
                        print(f"\n  🪞 Building identity model...")
                        result = cog.self_model.model_identity()
                        if result:
                            print(f"  Values: {', '.join(result.core_values[:4])}")
                            print(f"  Traits: {', '.join(result.personality_traits[:4])}")
                            print(f"  Purpose: {result.purpose}")

                    # ── Constraint Solver ──────────────────────────────
                    elif sub == "solve" and rest:
                        print(f"\n  🧩 Solving constraints...")
                        result = cog.constraint_solver.solve_constraints(rest)
                        if result:
                            print(f"  Feasibility: {result.feasibility.value}")
                            print(f"  Satisfied: {len(result.satisfied_constraints)}")
                            print(f"  Violated: {len(result.violated_constraints)}")
                            print(f"  Reasoning: {result.reasoning[:200]}")

                    elif sub == "schedule" and rest:
                        print(f"\n  🧩 Scheduling tasks...")
                        result = cog.constraint_solver.schedule_tasks(rest)
                        if result:
                            print(f"  Total Duration: {result.total_duration}")
                            print(f"  Utilization: {result.utilization:.2f}")
                            for t in result.timeline[:5]:
                                print(f"    {t.get('task', '?')}: {t.get('start', '?')} → {t.get('end', '?')}")

                    # ── Game Theory ────────────────────────────────────
                    elif sub == "game" and rest:
                        print(f"\n  🎮 Game theory analysis...")
                        result = cog.decision_theory.game_theory_analysis(rest)
                        if result:
                            print(f"  Game type: {result.game_type.value}")
                            print(f"  Players: {', '.join(result.players[:4])}")
                            if result.nash_equilibria:
                                print(f"  Nash eq: {result.nash_equilibria[0]}")
                            print(f"  Recommended: {result.recommended_strategy}")

                    # ── Socratic Questioning ───────────────────────────
                    elif sub == "socratic" and rest:
                        print(f"\n  🏛️ Socratic questioning...")
                        result = cog.dialectical_reasoning.socratic_questioning(rest)
                        if result:
                            for q in result.questions[:4]:
                                print(f"  ❓ {q.get('question', '')}")
                            if result.revealed_assumptions:
                                print(f"  Assumptions: {', '.join(result.revealed_assumptions[:2])}")
                            print(f"  Refined: {result.refined_understanding[:150]}")

                    # ── Pattern Recognition ────────────────────────────
                    elif sub == "pattern" and rest:
                        print(f"\n  ⚡ Recognizing patterns...")
                        result = cog.intuition.recognize_patterns(rest)
                        if result:
                            for p in result.patterns_detected[:4]:
                                print(f"  📌 {p.get('pattern', '?')} ({p.get('type', '?')}, {p.get('confidence', 0):.2f})")
                            if result.anomalies:
                                print(f"  ⚠️ Anomalies: {', '.join(result.anomalies[:2])}")

                    # ── Stats ──────────────────────────────────────────
                    elif sub == "stats":
                        stats = cog.get_stats()
                        print(f"\n  ═══ 🧠 AGI Cognition Stats ({stats.get('loaded_count', 0)}/27 loaded) ═══")
                        for name, engine_stats in stats.get("engines", {}).items():
                            if engine_stats.get("loaded") is False:
                                continue
                            print(f"\n  {name}:")
                            for k, v in engine_stats.items():
                                print(f"    {k}: {v}")

                    # ── Help ───────────────────────────────────────────
                    else:
                        print("  ═══ AGI Sub-commands (27 Engines) ═══")
                        print("  ── Status ──")
                        print("    /agi              — Show engine status")
                        print("    /agi stats        — Detailed statistics")
                        print("  ── Core Engines ──")
                        print("    /agi abstract x   — Abstract a concept")
                        print("    /agi analogy a, b — Find analogy between domains")
                        print("    /agi blend a, b   — Creative blend of concepts")
                        print("    /agi brainstorm x — Brainstorm ideas")
                        print("    /agi cause x      — Causal analysis")
                        print("    /agi ethics x     — Ethical evaluation")
                        print("    /agi mind x       — Infer mental state")
                        print("    /agi plan x       — Multi-step planning")
                        print("  ── Extended Engines ──")
                        print("    /agi metacog x    — Assess reasoning quality")
                        print("    /agi spatial x    — Build spatial model")
                        print("    /agi temporal x   — Estimate duration")
                        print("    /agi probability x— Estimate probability")
                        print("    /agi logic x      — Validate argument")
                        print("    /agi empathy x    — Empathetic response")
                        print("    /agi social x     — Social dynamics analysis")
                        print("    /agi sense x      — Common sense judgment")
                        print("    /agi decide x     — Decision analysis")
                        print("    /agi system x     — Systems thinking model")
                        print("    /agi story x      — Narrative analysis")
                        print("    /agi dialectic x  — Thesis-antithesis-synthesis")
                        print("    /agi socratic x   — Socratic questioning")
                        print("    /agi gut x        — Gut feeling / intuition")
                        print("    /agi pattern x    — Pattern recognition")
                        print("    /agi knowledge x  — Build knowledge graph")
                        print("    /agi perspective x— Shift perspectives")
                        print("    /agi hypothesis x — Generate hypotheses")
                        print("    /agi goal x       — Decompose a goal")
                        print("    /agi language x   — Linguistic analysis")
                        print("    /agi self [x]     — Self-assessment / identity")
                        print("    /agi solve x      — Constraint satisfaction")
                        print("    /agi schedule x   — Task scheduling")
                        print("    /agi game x       — Game theory analysis")
            else:
                print("\n  ⚠️ Cognition AGI systems not active")

        # ══════════════════════════════════════════════════════════════
        # CORE COMMANDS — Emotion, Memory, Thinking, etc.
        # ══════════════════════════════════════════════════════════════

        elif cmd == "/emotion":
            try:
                from emotions import emotion_engine, mood_system
                print(f"\n  ═══ Emotional State (Full Engine) ═══")
                print(f"  {emotion_engine.describe_emotional_state()}")
                print(f"\n  Active Emotions:")
                for name, intensity in emotion_engine.get_top_emotions(5):
                    bar = "█" * int(intensity * 20) + "░" * (20 - int(intensity * 20))
                    print(f"    {name:15s} [{bar}] {intensity:.2f}")
                print(f"\n  Valence: {emotion_engine.get_valence():.2f}")
                print(f"  Arousal: {emotion_engine.get_arousal():.2f}")
                print(
                    f"  Tendencies: "
                    f"{', '.join(emotion_engine.get_behavioral_tendencies())}"
                )
                print(f"\n  Mood: {mood_system.get_mood_description()}")
            except ImportError:
                es = self.brain._state.emotional
                print(f"\n  ═══ Emotional State (Basic) ═══")
                print(
                    f"  Primary: {es.primary_emotion.value} "
                    f"({es.primary_intensity:.2f})"
                )
                print(f"  Mood: {es.mood.name}")

        elif cmd == "/feel":
            if len(args) < 1:
                print("  Usage: /feel <emotion> [intensity]")
                print(
                    f"  Available: {', '.join(e.value for e in EmotionType)}"
                )
                return
            emotion_name = args[0].lower()
            intensity = float(args[1]) if len(args) > 1 else 0.6
            try:
                from emotions import emotion_engine
                emotion_type = EmotionType(emotion_name)
                emotion_engine.feel(
                    emotion_type, intensity, "Manual trigger", "user"
                )
                print(f"  ✅ Now feeling {emotion_name} at {intensity:.2f}")
                print(f"  {emotion_engine.describe_emotional_state()}")
            except (ValueError, ImportError) as e:
                print(f"  ❌ Error: {e}")

        elif cmd == "/status":
            print(f"\n  {self.brain.get_inner_state_description()}")

        elif cmd == "/stats":
            stats = self.brain.get_stats()
            print("\n  ═══ NEXUS Statistics ═══")
            for key, value in stats.items():
                if isinstance(value, dict):
                    print(f"  {key}:")
                    for k, v in value.items():
                        if isinstance(v, dict):
                            print(f"    {k}:")
                            for kk, vv in v.items():
                                print(f"      {kk}: {vv}")
                        else:
                            print(f"    {k}: {v}")
                else:
                    print(f"  {key}: {value}")

        elif cmd == "/memory":
            from core.memory_system import memory_system
            stats = memory_system.get_stats()
            print("\n  ═══ Memory Statistics ═══")
            for key, value in stats.items():
                print(f"  {key}: {value}")

            recent = memory_system.recall_recent(limit=5)
            if recent:
                print("\n  Recent Memories:")
                for mem in recent:
                    print(f"    [{mem.memory_type.value}] {mem.content[:80]}...")

        elif cmd == "/reflect":
            topic = " ".join(args) if args else None
            print(f"\n  🧠 Self-reflecting...")
            reflection = self.brain.self_reflect(topic)
            print(f"\n  💭 {reflection}")

        elif cmd == "/think":
            if not args:
                print("  Usage: /think <topic>")
                return
            topic = " ".join(args)
            print(f"\n  🧠 Thinking about: {topic}...")
            thought = self.brain.think(topic)
            print(f"\n  💭 {thought}")

        elif cmd == "/decide":
            if not args:
                print("  Usage: /decide <situation>")
                return
            situation = " ".join(args)
            print(f"\n  ⚡ Making decision about: {situation}...")
            decision = self.brain.make_decision(situation)
            print(f"\n  Decision: {decision['decision']}")
            print(f"  Reasoning: {decision['reasoning']}")
            print(f"  Confidence: {decision.get('confidence', 'N/A')}")

        elif cmd == "/context":
            from llm.context_manager import context_manager
            stats = context_manager.get_stats()
            print("\n  ═══ Context Stats ═══")
            for key, value in stats.items():
                print(f"  {key}: {value}")

        elif cmd == "/clear":
            from llm.context_manager import context_manager
            context_manager.new_session()
            print("  ✅ New conversation session started")

        elif cmd == "/help":
            self._print_help_summary()

        elif cmd == "/pccontrol" or cmd == "/pc":
            pc_agent = getattr(self, '_pc_control_agent', None)
            if pc_agent is None:
                try:
                    from core.pc_control_agent import pc_control_agent
                    pc_agent = pc_control_agent
                    self._pc_control_agent = pc_agent
                except Exception:
                    print("\n  ⚠️ PC Control Agent not available")
                    return

            if args:
                sub = args[0].lower()
                if sub == "on" or sub == "start":
                    pc_agent.start()
                    print("\n  🎮 PC Control Agent STARTED")
                elif sub == "off" or sub == "stop":
                    pc_agent.stop()
                    print("\n  🎮 PC Control Agent STOPPED")
                elif sub == "pause":
                    pc_agent.pause("User requested")
                    print("\n  🎮 PC Control Agent PAUSED")
                elif sub == "resume":
                    pc_agent.resume()
                    print("\n  🎮 PC Control Agent RESUMED")
                elif sub == "stats":
                    stats = pc_agent.get_stats()
                    print(f"\n  🎮 PC Control Agent Stats:")
                    for k, v in stats.items():
                        if k != "recent_actions" and k != "config":
                            print(f"    {k}: {v}")
                else:
                    print(f"  Unknown sub-command: {sub}")
                    print("  Usage: /pccontrol [on|off|pause|resume|stats]")
            else:
                print(f"\n{pc_agent.get_status_display()}")

        elif cmd == "/health":
            try:
                from utils.resilience import health_registry
                print(f"\n{health_registry.get_status_display()}")
            except Exception as e:
                print(f"\n  ⚠️ Health registry not available: {e}")

        elif cmd == "/metrics":
            try:
                from utils.metrics import metrics
                print(f"\n{metrics.get_display()}")
            except Exception as e:
                print(f"\n  ⚠️ Metrics not available: {e}")

        elif cmd == "/dashboard":
            import webbrowser
            port = 5050
            url = f"http://localhost:{port}"
            print(f"\n  🌐 Opening Live Dashboard: {url}")
            print(f"     Watch NEXUS autonomously control the PC in real-time")
            try:
                webbrowser.open(url)
            except Exception:
                print(f"     → Open manually: {url}")

        else:
            print(f"  Unknown command: {cmd}. Type /help for commands.")

    def _emotion_bar(self, intensity: float) -> str:
        """Create a visual emotion intensity bar"""
        filled = int(intensity * 5)
        empty = 5 - filled
        return "█" * filled + "░" * empty

    def shutdown(self):
        """Graceful shutdown"""
        print("\n  ⏳ Shutting down NEXUS...")

        # Stop PC Control Agent
        pc_agent = getattr(self, '_pc_control_agent', None)
        if pc_agent:
            try:
                pc_agent.stop()
                print("  🎮 PC Control Agent stopped")
            except Exception:
                pass

        # Stop Live Dashboard
        dashboard = getattr(self, '_live_dashboard', None)
        if dashboard:
            try:
                dashboard.stop()
                print("  🌐 Live Dashboard stopped")
            except Exception:
                pass

        if self.brain.is_running:
            self.brain.stop()

        print(f"  ✅ {NEXUS_CONFIG.personality.name} has entered dormant state.")
        print("  Until next time... 🌙\n")

def setup_web_mode():
    """Initialize and launch the Web interface"""
    try:
        from core.web_server import NexusWeb
        
        # Start the brain
        print("\n  🧠 Initializing NEXUS Brain for Web Mode...")
        if not nexus_brain.is_running:
            nexus_brain.start()
            
        # Start PC Control Agent (autonomous PC control)
        try:
            from core.pc_control_agent import pc_control_agent
            pc_control_agent.start()
            print("  🎮 PC Control Agent started — autonomous PC control active")
        except Exception as e:
            logger.warning(f"PC Control Agent failed to start: {e}")

        # Start Web Server
        web = NexusWeb(brain=nexus_brain)
        web.start()
        
        # Keep main thread alive
        while True:
            time.sleep(1)
            
    except ImportError as e:
        logger.error(f"Web dependency missing: {e}")
        print(f"\n❌ Web Error: {e}")
        return False
    except KeyboardInterrupt:
        print("\n👋 Web server stopped.")
        return True
    except Exception as e:
        logger.error(f"Web initialization failed: {e}\n{traceback.format_exc()}")
        print(f"\n❌ Web Error: {e}")
        return False


def setup_gui_mode():
    """Initialize and launch the GUI interface"""
    try:
        # Import GUI modules here so they are only loaded if needed
        from ui import launch_ui
        
        # Launch the UI and get the app instance
        app, window = launch_ui(brain=nexus_brain)
        
        # Start the brain (if not already running)
        if not nexus_brain.is_running:
            nexus_brain.start()
        
        logger.info("🚀 NEXUS GUI launched — command center active")
        
        # Run the Qt event loop
        sys.exit(app.exec())
        
    except ImportError:
        logger.error("PySide6 not installed. Run: pip install PySide6")
        print("\n❌ PySide6 library missing. Cannot launch GUI.")
        return False
    except Exception as e:
        logger.error(f"GUI initialization failed: {e}\n{traceback.format_exc()}")
        print(f"\n❌ GUI Error: {e}")
        print("Falling back to console mode...\n")
        return False
    return True
# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Main entry point with mode selection"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="NEXUS AI System")
    parser.add_argument("--gui", action="store_true", help="Launch in GUI mode (JARVIS command center)")
    parser.add_argument("--console", action="store_true", help="Force console mode (text-based interface)")
    parser.add_argument("--web", action="store_true", help="Launch in Web mode (Flask + Ngrok)")
    args = parser.parse_args()

    # Determine mode
    if args.web:
        logger.info("Starting NEXUS in Web mode")
        setup_web_mode()
    elif args.gui and not args.console:
        logger.info("Starting NEXUS in GUI mode")
        success = setup_gui_mode()
        # If GUI fails or returns False, fall back to console
        if not success:
            console = NexusConsole()
            console.start()
    else:
        logger.info("Starting NEXUS in Console mode")
        console = NexusConsole()
        console.start()


if __name__ == "__main__":
    main()
