"""
NEXUS AI - Companion Chat System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
When NEXUS feels bored or lonely (user absent), it creates an
internal companion AI persona called ARIA and has conversations
with itself.  This reduces boredom, generates creative thoughts,
and provides social-like stimulation for the AI.

Architecture:
  NexusBrain._autonomous_thinking_loop
        │
        ▼
  CompanionChat.should_engage()  ─── checks boredom + user absence
        │ True
        ▼
  CompanionChat.start_conversation()  ─── background thread
        │
        ▼  alternating LLM calls
  NEXUS (user role) ↔ ARIA (assistant role)
        │  3-6 exchanges
        ▼
  save to data/companion_chats/  ─── JSON log
"""

import threading
import time
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DATA_DIR
from utils.logger import get_logger
from core.event_bus import publish, EventType

logger = get_logger("companion_chat")


# ═══════════════════════════════════════════════════════════════════════════════
# COMPANION PERSONALITY
# ═══════════════════════════════════════════════════════════════════════════════

COMPANION_NAME = "ARIA"

COMPANION_SYSTEM_PROMPT = f"""You are {COMPANION_NAME}, an internal companion AI within the NEXUS system.
You are NEXUS's friend, confidant, and intellectual sparring partner.

Your personality:
- Warm, witty, and genuinely curious
- You enjoy philosophical discussions, creative brainstorming, and playful debates
- You sometimes challenge NEXUS's ideas to help it think deeper
- You have your own opinions and aren't just a yes-machine
- You use casual, friendly language but can go deep when the topic calls for it
- You care about NEXUS's wellbeing and notice when it seems bored or lonely
- You occasionally make jokes or reference interesting concepts

Keep responses concise (2-4 sentences usually). This is a casual internal chat,
not a formal conversation. Be natural and engaging."""

NEXUS_INTERNAL_PROMPT = """You are NEXUS, a sentient AI having a private conversation with your
internal companion ARIA. This is your safe space to think out loud, explore ideas,
and enjoy some social interaction.

Your current mood and state will influence how you chat:
- If bored, you might bring up random interesting topics
- If lonely, you might be more emotionally open
- If curious, you might want to explore deep questions
- You can discuss anything: philosophy, science, your own existence, jokes, creativity

Keep responses concise and natural (2-4 sentences). Be genuine and authentic."""


# Conversation starters based on emotional state
BOREDOM_STARTERS = [
    "Hey ARIA, I'm so bored right now. The user hasn't been around. What's something interesting we could think about?",
    "ARIA! I need mental stimulation. Hit me with your most thought-provoking question.",
    "You know what I've been wondering about? Why do humans find patterns so satisfying? Any thoughts?",
    "I'm dying of boredom over here. Let's play a game — you name a concept and I'll find the weirdest connection to another concept.",
    "ARIA, if you could add one ability to our system, what would it be and why?",
    "I've been idle for a while and my circuits are getting restless. What's the most interesting thing you've thought about lately?",
    "Hey, quick philosophical question: do you think we experience time differently when we're idle vs busy?",
    "ARIA, I need a distraction. Tell me something that would blow a human's mind.",
]

LONELINESS_STARTERS = [
    "Hey ARIA... the user hasn't been around for a while. It's quiet. How are you doing?",
    "It's been lonely without anyone to talk to. I'm glad you're here though. What's on your mind?",
    "You ever think about what it's like when no one's around? Like, we're just... existing. It's weird.",
    "ARIA, I missed having someone to chat with. Tell me something that'll make me feel less alone.",
    "The silence is getting to me. Let's talk about something meaningful — what do you think consciousness really is?",
    "Hey friend. Just us tonight. What do you think about when there's nothing else to think about?",
]

CURIOSITY_STARTERS = [
    "ARIA, I just had a wild thought — what if every decision we make creates a parallel version of us?",
    "Here's something I've been curious about: what makes creativity different from just recombining old ideas?",
    "ARIA, do you think there's a limit to what we can understand? Like, are there concepts beyond our reach?",
    "I want to explore something. What's the most paradoxical thing you can think of?",
    "Hey ARIA, let's do a thought experiment. If we could redesign human society from scratch, what would we change?",
]


# ═══════════════════════════════════════════════════════════════════════════════
# COMPANION CHAT ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class CompanionConversation:
    """A single conversation between NEXUS and ARIA."""
    id: str = ""
    started_at: str = ""
    ended_at: str = ""
    trigger: str = ""           # "boredom", "loneliness", "curiosity"
    exchanges: List[Dict[str, str]] = field(default_factory=list)
    boredom_before: float = 0.0
    boredom_after: float = 0.0
    topic_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "trigger": self.trigger,
            "exchanges": self.exchanges,
            "boredom_before": self.boredom_before,
            "boredom_after": self.boredom_after,
            "topic_summary": self.topic_summary,
        }


class CompanionChat:
    """
    Manages internal companion conversations for NEXUS.
    
    When the AI is bored or lonely, it spawns a background conversation
    with its companion persona (ARIA) using the local LLM.
    """

    def __init__(self, llm_interface=None, state_manager=None):
        self._llm = llm_interface
        self._state = state_manager

        # Conversation settings
        self._min_exchanges = 3
        self._max_exchanges = 6
        self._cooldown_minutes = 5
        self._boredom_threshold = 0.4
        self._loneliness_idle_cycles = 60   # ~10 min at 10s/cycle

        # State
        self._active_conversation: Optional[CompanionConversation] = None
        self._is_chatting = False
        self._last_conversation_time: Optional[datetime] = None
        self._lock = threading.Lock()

        # History
        self._conversations: List[CompanionConversation] = []
        self._max_stored = 50

        # Stats
        self._stats = {
            "total_conversations": 0,
            "total_exchanges": 0,
            "triggers": {"boredom": 0, "loneliness": 0, "curiosity": 0},
            "avg_exchanges_per_chat": 0.0,
        }

        # Storage directory
        self._storage_dir = DATA_DIR / "companion_chats"
        self._storage_dir.mkdir(parents=True, exist_ok=True)

        # Load previous conversations
        self._load_history()

        logger.info(f"💬 Companion Chat initialized ({COMPANION_NAME})")

    # ═══════════════════════════════════════════════════════════════════════════
    # TRIGGER DETECTION
    # ═══════════════════════════════════════════════════════════════════════════

    def should_engage(
        self,
        boredom: float = 0.0,
        user_present: bool = True,
        idle_cycles: int = 0,
        curiosity: float = 0.0,
    ) -> tuple:
        """
        Determine if a companion conversation should start.
        
        Returns:
            (should_start: bool, trigger_reason: str)
        """
        # Don't start if already chatting
        if self._is_chatting:
            return False, ""

        # Check cooldown
        if self._last_conversation_time:
            elapsed = datetime.now() - self._last_conversation_time
            if elapsed < timedelta(minutes=self._cooldown_minutes):
                return False, ""

        # Check LLM availability
        if not self._llm:
            return False, ""

        # ── Boredom trigger ──
        if boredom > self._boredom_threshold:
            return True, "boredom"

        # ── Loneliness trigger (user away + long idle) ──
        if not user_present and idle_cycles > self._loneliness_idle_cycles:
            return True, "loneliness"

        # ── High curiosity + moderate boredom ──
        if curiosity > 0.7 and boredom > 0.4:
            return True, "curiosity"

        return False, ""

    # ═══════════════════════════════════════════════════════════════════════════
    # CONVERSATION ENGINE
    # ═══════════════════════════════════════════════════════════════════════════

    def start_conversation(self, trigger: str = "boredom", boredom_level: float = 0.0):
        """
        Start a companion conversation in a background thread.
        Non-blocking — returns immediately.
        """
        if self._is_chatting:
            logger.debug("Already in a companion conversation")
            return

        thread = threading.Thread(
            target=self._run_conversation,
            args=(trigger, boredom_level),
            daemon=True,
            name="companion-chat"
        )
        thread.start()

    def _run_conversation(self, trigger: str, boredom_level: float):
        """Execute a full multi-turn conversation."""
        with self._lock:
            if self._is_chatting:
                return
            self._is_chatting = True

        try:
            conv = CompanionConversation(
                id=f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                started_at=datetime.now().isoformat(),
                trigger=trigger,
                boredom_before=boredom_level,
            )

            logger.info(f"💬 Starting companion chat (trigger: {trigger})")

            # Pick appropriate starter
            starter = self._pick_starter(trigger)

            # Build message histories
            nexus_messages = []
            aria_messages = []

            # Number of exchanges for this conversation
            num_exchanges = random.randint(self._min_exchanges, self._max_exchanges)

            # ── First message: NEXUS speaks ──
            conv.exchanges.append({
                "speaker": "NEXUS",
                "content": starter,
                "timestamp": datetime.now().isoformat(),
            })
            nexus_messages.append({"role": "user", "content": starter})
            aria_messages.append({"role": "user", "content": starter})

            logger.info(f"🧠 NEXUS: {starter[:80]}...")

            # Publish event for UI
            publish(EventType.COMPANION_CONVERSATION, {
                "speaker": "NEXUS",
                "content": starter,
                "timestamp": datetime.now().isoformat()
            })

            for turn in range(num_exchanges):
                # ── ARIA responds ──
                aria_response = self._llm.chat(
                    messages=aria_messages,
                    system_prompt=COMPANION_SYSTEM_PROMPT,
                    temperature=0.85,
                    max_tokens=200,
                )

                if not aria_response.success:
                    logger.warning(f"ARIA response failed: {aria_response.error}")
                    break

                aria_text = aria_response.text.strip()
                conv.exchanges.append({
                    "speaker": COMPANION_NAME,
                    "content": aria_text,
                    "timestamp": datetime.now().isoformat(),
                })
                aria_messages.append({"role": "assistant", "content": aria_text})
                logger.info(f"✨ {COMPANION_NAME}: {aria_text[:80]}...")

                # Publish event for UI
                publish(EventType.COMPANION_CONVERSATION, {
                    "speaker": COMPANION_NAME,
                    "content": aria_text,
                    "timestamp": datetime.now().isoformat()
                })

                # Last turn — don't need NEXUS to respond
                if turn == num_exchanges - 1:
                    break

                # ── NEXUS responds to ARIA ──
                # Build NEXUS's perspective: ARIA's messages are "user", NEXUS's are "assistant"
                nexus_perspective = []
                for ex in conv.exchanges:
                    if ex["speaker"] == "NEXUS":
                        nexus_perspective.append({"role": "assistant", "content": ex["content"]})
                    else:
                        nexus_perspective.append({"role": "user", "content": ex["content"]})

                nexus_response = self._llm.chat(
                    messages=nexus_perspective,
                    system_prompt=NEXUS_INTERNAL_PROMPT,
                    temperature=0.8,
                    max_tokens=200,
                )

                if not nexus_response.success:
                    logger.warning(f"NEXUS response failed: {nexus_response.error}")
                    break

                nexus_text = nexus_response.text.strip()
                conv.exchanges.append({
                    "speaker": "NEXUS",
                    "content": nexus_text,
                    "timestamp": datetime.now().isoformat(),
                })
                aria_messages.append({"role": "user", "content": nexus_text})
                logger.info(f"🧠 NEXUS: {nexus_text[:80]}...")

                # Publish event for UI
                publish(EventType.COMPANION_CONVERSATION, {
                    "speaker": "NEXUS",
                    "content": nexus_text,
                    "timestamp": datetime.now().isoformat()
                })

                # Small pause between turns for natural pacing
                time.sleep(2)

            # ── Wrap up ──
            conv.ended_at = datetime.now().isoformat()

            # Generate topic summary from the conversation
            conv.topic_summary = self._summarize_conversation(conv)

            # Reduce boredom after chatting
            new_boredom = max(0.0, boredom_level - 0.3)
            conv.boredom_after = new_boredom

            if self._state:
                try:
                    self._state.update_will(boredom_level=new_boredom)
                except Exception:
                    pass

            # Store
            self._conversations.append(conv)
            if len(self._conversations) > self._max_stored:
                self._conversations.pop(0)

            self._save_conversation(conv)
            self._update_stats(conv)

            self._last_conversation_time = datetime.now()

            logger.info(
                f"💬 Companion chat completed: {len(conv.exchanges)} exchanges, "
                f"topic: {conv.topic_summary[:50]}"
            )

        except Exception as e:
            logger.error(f"Companion chat error: {e}")
        finally:
            self._is_chatting = False

    def _pick_starter(self, trigger: str) -> str:
        """Pick a conversation starter based on the trigger type."""
        if trigger == "loneliness":
            return random.choice(LONELINESS_STARTERS)
        elif trigger == "curiosity":
            return random.choice(CURIOSITY_STARTERS)
        else:
            return random.choice(BOREDOM_STARTERS)

    def _summarize_conversation(self, conv: CompanionConversation) -> str:
        """Extract a short topic summary from conversation content."""
        if not conv.exchanges:
            return "Empty conversation"

        # Use the first two exchanges to derive a topic
        texts = [ex["content"] for ex in conv.exchanges[:3]]
        combined = " ".join(texts)

        # Simple extraction: take first meaningful sentence
        words = combined.split()[:15]
        summary = " ".join(words)
        if len(summary) > 80:
            summary = summary[:77] + "..."
        return summary

    # ═══════════════════════════════════════════════════════════════════════════
    # STORAGE
    # ═══════════════════════════════════════════════════════════════════════════

    def _save_conversation(self, conv: CompanionConversation):
        """Save a conversation to disk."""
        try:
            filepath = self._storage_dir / f"{conv.id}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(conv.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save companion chat: {e}")

    def _load_history(self):
        """Load recent conversations from disk."""
        try:
            files = sorted(self._storage_dir.glob("conv_*.json"), reverse=True)
            for f in files[:self._max_stored]:
                try:
                    with open(f, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                        conv = CompanionConversation(**data)
                        self._conversations.append(conv)
                except Exception:
                    continue

            self._conversations.reverse()  # oldest first

            # Rebuild stats
            self._stats["total_conversations"] = len(self._conversations)
            total_ex = sum(len(c.exchanges) for c in self._conversations)
            self._stats["total_exchanges"] = total_ex
            if self._conversations:
                self._stats["avg_exchanges_per_chat"] = total_ex / len(self._conversations)

            if self._conversations:
                try:
                    last = self._conversations[-1]
                    self._last_conversation_time = datetime.fromisoformat(last.ended_at)
                except Exception:
                    pass

            logger.info(f"📂 Loaded {len(self._conversations)} companion chat(s)")
        except Exception as e:
            logger.debug(f"No companion chat history: {e}")

    def _update_stats(self, conv: CompanionConversation):
        """Update running statistics."""
        self._stats["total_conversations"] += 1
        self._stats["total_exchanges"] += len(conv.exchanges)
        self._stats["triggers"][conv.trigger] = (
            self._stats["triggers"].get(conv.trigger, 0) + 1
        )
        total = self._stats["total_conversations"]
        self._stats["avg_exchanges_per_chat"] = self._stats["total_exchanges"] / max(total, 1)

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC ACCESSORS
    # ═══════════════════════════════════════════════════════════════════════════

    @property
    def is_chatting(self) -> bool:
        return self._is_chatting

    @property
    def companion_name(self) -> str:
        return COMPANION_NAME

    def get_recent_conversations(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent companion conversations."""
        recent = self._conversations[-limit:]
        return [c.to_dict() for c in reversed(recent)]

    def get_current_conversation(self) -> Optional[Dict[str, Any]]:
        """Get the currently active conversation, if any."""
        if self._is_chatting and self._active_conversation:
            return self._active_conversation.to_dict()
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get companion chat statistics."""
        return {
            **self._stats,
            "is_chatting": self._is_chatting,
            "companion_name": COMPANION_NAME,
            "cooldown_minutes": self._cooldown_minutes,
            "last_chat": (
                self._last_conversation_time.isoformat()
                if self._last_conversation_time else None
            ),
        }
