"""
NEXUS AI - Main Entry Point
Phase 10: Core Brain + LLM Interactive Console + Self-Evolution Commands

This is a minimal runner to test the brain before the full UI is built.
"""

import sys
import signal
import time
import json
from pathlib import Path
from datetime import datetime
import argparse     # <--- ADD THIS
import traceback    # <--- ADD THIS

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import NEXUS_CONFIG, EmotionType, print_config
from utils.logger import print_startup_banner, get_logger, log_system
from core.nexus_brain import NexusBrain, nexus_brain

logger = get_logger("main")


class NexusConsole:
    """
    Simple console interface for testing NEXUS Brain
    Will be replaced by full UI in Phase 11
    """

    def __init__(self):
        self.brain = nexus_brain
        self.running = False

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
        print("    /quit      — Shutdown NEXUS")

    def _interaction_loop(self):
        """Main interaction loop"""
        while self.running:
            try:
                # Show emotion indicator
                emotion = self.brain._state.emotional.primary_emotion.value
                intensity = self.brain._state.emotional.primary_intensity
                emotion_bar = self._emotion_bar(intensity)

                user_input = input(
                    f"\n  [{emotion} {emotion_bar}] You: "
                ).strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    self._handle_command(user_input)
                    continue

                # Process input and stream response
                print(
                    f"\n  🤖 {NEXUS_CONFIG.personality.name}: ",
                    end="",
                    flush=True,
                )

                response = self.brain.process_input_stream(
                    user_input,
                    token_callback=lambda token: print(token, end="", flush=True),
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

        if self.brain.is_running:
            self.brain.stop()

        print(f"  ✅ {NEXUS_CONFIG.personality.name} has entered dormant state.")
        print("  Until next time... 🌙\n")

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
    args = parser.parse_args()

    # Determine mode: Default to Console unless --gui is specifically requested
    run_gui = args.gui and not args.console

    if run_gui:
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