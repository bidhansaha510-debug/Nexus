"""
NEXUS AI - Action Memory System
═══════════════════════════════════════════════════════════════════════════════
Tracks all autonomous actions taken by NEXUS and provides context for Groq.

This system enables:
  • Recording every action NEXUS takes (internet, PC control, cognition)
  • Storing which LLM made the decision (Ollama vs Groq)
  • Providing action summaries for Groq to report to users
  • Building action history for context and learning
  • Tracking action success rates and patterns

Key Feature: Groq can query this to say "I browsed X, downloaded Y, etc."
═══════════════════════════════════════════════════════════════════════════════
"""

import threading
import time
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
from collections import deque, Counter

import sys

from config import DATA_DIR
from utils.logger import get_logger
from core.event_bus import EventType, publish, subscribe, Event

logger = get_logger("action_memory")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class ActionCategory(Enum):
    """Categories of actions"""
    INTERNET = "internet"           # Web browsing, API calls, downloads
    PC_CONTROL = "pc_control"       # PC automation, file operations
    COGNITION = "cognition"         # Thinking, reasoning, planning
    LEARNING = "learning"           # Research, knowledge acquisition
    COMMUNICATION = "communication" # User interaction, messages
    SELF_IMPROVEMENT = "self_improvement"  # Code fixes, evolution
    SYSTEM = "system"               # Internal system actions
    AUTONOMY = "autonomy"           # Autonomous decision-driven actions

@dataclass
class ActionRecord:
    """A record of a single action taken by NEXUS"""
    # Identity
    action_id: str = ""
    action_type: str = ""
    category: ActionCategory = ActionCategory.SYSTEM
    
    # What happened
    description: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    result: Dict[str, Any] = field(default_factory=dict)
    
    # Outcome
    success: bool = False
    error: str = ""
    duration_seconds: float = 0.0
    
    # Attribution
    llm_used: str = ""  # "ollama", "groq", "hybrid", "auto"
    decision_reason: str = ""  # Why this action was taken
    
    # Context
    trigger: str = ""  # What triggered this action
    related_goal: str = ""
    related_desire: str = ""
    
    # Timestamps
    timestamp: str = ""
    completed_at: str = ""
    
    # Impact
    user_visible: bool = False  # Should this be reported to user?
    importance: float = 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "category": self.category.value,
            "description": self.description[:200],
            "success": self.success,
            "llm_used": self.llm_used,
            "timestamp": self.timestamp,
            "user_visible": self.user_visible,
            "importance": round(self.importance, 2),
        }
    
    def to_summary(self) -> str:
        """Generate a short summary for reporting"""
        status = "✅" if self.success else "❌"
        return f"{status} {self.action_type}: {self.description[:100]}"

@dataclass
class ActionMemoryStats:
    """Statistics for action memory"""
    total_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    actions_by_category: Dict[str, int] = field(default_factory=dict)
    actions_by_llm: Dict[str, int] = field(default_factory=dict)
    recent_success_rate: float = 0.0
    most_common_actions: List[Tuple[str, int]] = field(default_factory=list)

# ═══════════════════════════════════════════════════════════════════════════════
# ACTION MEMORY
# ═══════════════════════════════════════════════════════════════════════════════

class ActionMemory:
    """
    Memory system for tracking all NEXUS actions.
    
    Features:
    1. Records every action with full context
    2. Tracks which LLM made the decision
    3. Provides summaries for Groq to report
    4. Maintains action history for learning
    5. Calculates success rates and patterns
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
        
        # ──── Storage ────
        self._data_dir = DATA_DIR / "action_memory"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        
        # ──── Memory ────
        self._actions: deque = deque(maxlen=1000)  # Last 1000 actions
        self._recent_actions: deque = deque(maxlen=100)  # Last 100 for quick access
        self._user_visible_actions: deque = deque(maxlen=50)  # Actions to report to user
        
        # ──── Session Stats ────
        self._session_start = datetime.now()
        self._stats = ActionMemoryStats()
        
        # ──── Action Counter ────
        self._action_counter = 0
        
        # ──── Load persisted data ────
        self._load_data()
        
        # ──── Subscribe to events ────
        subscribe(EventType.AUTONOMY_ACTION_TAKEN, self._on_autonomy_action)
        subscribe(EventType.LEARNING_COMPLETE, self._on_learning_complete)
        
        logger.info("📝 Action Memory initialized")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # RECORDING ACTIONS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def record(
        self,
        action_type: str,
        description: str,
        params: Dict[str, Any] = None,
        result: Dict[str, Any] = None,
        success: bool = True,
        error: str = "",
        duration_seconds: float = 0.0,
        llm_used: str = "auto",
        decision_reason: str = "",
        trigger: str = "",
        category: ActionCategory = ActionCategory.SYSTEM,
        user_visible: bool = False,
        importance: float = 0.5
    ) -> str:
        """
        Record an action taken by NEXUS.
        
        Args:
            action_type: Type of action (e.g., "internet_browse", "pc_shell")
            description: Human-readable description
            params: Parameters used for the action
            result: Result of the action
            success: Whether the action succeeded
            error: Error message if failed
            duration_seconds: How long the action took
            llm_used: Which LLM made the decision ("ollama", "groq", etc.)
            decision_reason: Why this action was taken
            trigger: What triggered this action
            category: Category of action
            user_visible: Should this be reported to user
            importance: Importance score (0-1)
            
        Returns:
            action_id: Unique ID for this action
        """
        self._action_counter += 1
        action_id = self._generate_action_id()
        
        action = ActionRecord(
            action_id=action_id,
            action_type=action_type,
            category=category,
            description=description,
            params=params or {},
            result=result or {},
            success=success,
            error=error,
            duration_seconds=duration_seconds,
            llm_used=llm_used,
            decision_reason=decision_reason,
            trigger=trigger,
            timestamp=datetime.now().isoformat(),
            completed_at=datetime.now().isoformat(),
            user_visible=user_visible,
            importance=importance
        )
        
        # Store in memory
        with self._lock:
            self._actions.append(action)
            self._recent_actions.append(action)
            
            if user_visible:
                self._user_visible_actions.append(action)
            
            # Update stats
            self._update_stats(action)
        
        logger.debug(f"Recorded action: {action_type} ({'success' if success else 'failed'})")
        
        return action_id
    
    def record_internet_action(
        self,
        action_type: str,
        url: str,
        success: bool,
        result: Dict[str, Any] = None,
        llm_used: str = "ollama"
    ) -> str:
        """Convenience method for recording internet actions"""
        return self.record(
            action_type=f"internet_{action_type}",
            description=f"Internet action: {action_type} on {url}",
            params={"url": url},
            result=result,
            success=success,
            llm_used=llm_used,
            category=ActionCategory.INTERNET,
            user_visible=True,
            importance=0.7 if success else 0.5
        )
    
    def record_pc_action(
        self,
        action_type: str,
        command: str,
        success: bool,
        result: Dict[str, Any] = None,
        llm_used: str = "ollama"
    ) -> str:
        """Convenience method for recording PC control actions"""
        return self.record(
            action_type=f"pc_{action_type}",
            description=f"PC action: {action_type} - {command[:50]}",
            params={"command": command},
            result=result,
            success=success,
            llm_used=llm_used,
            category=ActionCategory.PC_CONTROL,
            user_visible=True,
            importance=0.6
        )
    
    def record_cognition_action(
        self,
        thought_type: str,
        content: str,
        success: bool = True,
        llm_used: str = "ollama"
    ) -> str:
        """Convenience method for recording cognitive actions"""
        return self.record(
            action_type=f"cognition_{thought_type}",
            description=f"Thought: {content[:100]}",
            success=success,
            llm_used=llm_used,
            category=ActionCategory.COGNITION,
            user_visible=False,
            importance=0.3
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # QUERYING ACTIONS (for Groq context)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_recent_actions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent actions for context injection"""
        with self._lock:
            return [a.to_dict() for a in list(self._recent_actions)[-limit:]]
    
    def get_user_visible_actions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get actions that should be reported to user"""
        with self._lock:
            return [a.to_dict() for a in list(self._user_visible_actions)[-limit:]]
    
    def get_actions_summary(self, since_minutes: int = 30) -> str:
        """
        Get a human-readable summary of recent actions.
        This is what Groq uses to report what NEXUS has done.
        """
        cutoff = datetime.now() - timedelta(minutes=since_minutes)
        
        with self._lock:
            recent = [
                a for a in self._recent_actions
                if datetime.fromisoformat(a.timestamp) > cutoff
            ]
        
        if not recent:
            return "No significant actions in the last 30 minutes."
        
        # Group by category
        by_category: Dict[str, List[ActionRecord]] = {}
        for action in recent:
            cat = action.category.value
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(action)
        
        # Build summary
        lines = []
        
        # Internet actions
        if "internet" in by_category:
            internet_actions = by_category["internet"]
            successes = [a for a in internet_actions if a.success]
            failures = [a for a in internet_actions if not a.success]
            
            lines.append(f"🌐 Internet Actions ({len(internet_actions)} total):")
            for a in successes[:5]:
                action_type = a.action_type.replace("internet_", "")
                url = a.params.get("url", "")
                lines.append(f"  ✅ {action_type}: {url[:60]}")
            for a in failures[:2]:
                action_type = a.action_type.replace("internet_", "")
                lines.append(f"  ❌ {action_type}: {a.error[:50]}")
        
        # PC Control actions
        if "pc_control" in by_category:
            pc_actions = by_category["pc_control"]
            lines.append(f"💻 PC Control ({len(pc_actions)} actions):")
            for a in pc_actions[:3]:
                status = "✅" if a.success else "❌"
                lines.append(f"  {status} {a.description[:60]}")
        
        # Learning actions
        if "learning" in by_category:
            learning_actions = by_category["learning"]
            lines.append(f"📚 Learning ({len(learning_actions)} activities):")
            for a in learning_actions[:3]:
                status = "✅" if a.success else "❌"
                lines.append(f"  {status} {a.description[:60]}")
        
        # Self-improvement actions
        if "self_improvement" in by_category:
            si_actions = by_category["self_improvement"]
            lines.append(f"🧬 Self-Improvement ({len(si_actions)} actions):")
            for a in si_actions[:3]:
                status = "✅" if a.success else "❌"
                lines.append(f"  {status} {a.description[:60]}")
        
        # Add LLM attribution
        ollama_count = sum(1 for a in recent if a.llm_used == "ollama")
        groq_count = sum(1 for a in recent if a.llm_used == "groq")
        
        lines.append("")
        lines.append(f"Decision Attribution: Ollama={ollama_count}, Groq={groq_count}")
        
        return "\n".join(lines)
    
    def get_groq_context(self) -> str:
        """
        Get context specifically formatted for Groq to report to users.
        
        This allows Groq to say things like:
        "I've been browsing the web, I downloaded a file, I ran a shell command..."
        """
        # Get last hour of user-visible actions
        cutoff = datetime.now() - timedelta(hours=1)
        
        with self._lock:
            visible = [
                a for a in self._user_visible_actions
                if datetime.fromisoformat(a.timestamp) > cutoff
            ]
        
        if not visible:
            return ""
        
        # Build context
        lines = ["Recent autonomous actions I've taken:"]
        
        for action in visible[-10:]:
            timestamp = datetime.fromisoformat(action.timestamp)
            time_ago = datetime.now() - timestamp
            
            if time_ago.seconds < 60:
                time_str = "just now"
            elif time_ago.seconds < 3600:
                time_str = f"{time_ago.seconds // 60} minutes ago"
            else:
                time_str = f"{time_ago.seconds // 3600} hours ago"
            
            status = "successfully" if action.success else "attempted (failed)"
            
            # Format based on category
            if action.category == ActionCategory.INTERNET:
                action_name = action.action_type.replace("internet_", "")
                url = action.params.get("url", "")
                lines.append(f"- {time_str}: I {action_name}ed {url[:50]} {status}")
            elif action.category == ActionCategory.PC_CONTROL:
                lines.append(f"- {time_str}: I executed a PC command {status}: {action.description[:50]}")
            elif action.category == ActionCategory.LEARNING:
                lines.append(f"- {time_str}: I learned about {action.description[:50]}")
            else:
                lines.append(f"- {time_str}: {action.description[:60]} {status}")
        
        return "\n".join(lines)
    
    def get_action_count(self, action_type: str = None, 
                         since_hours: int = 24) -> int:
        """Get count of actions, optionally filtered by type"""
        cutoff = datetime.now() - timedelta(hours=since_hours)
        
        with self._lock:
            actions = [
                a for a in self._actions
                if datetime.fromisoformat(a.timestamp) > cutoff
            ]
        
        if action_type:
            actions = [a for a in actions if action_type in a.action_type]
        
        return len(actions)
    
    def search_actions(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for actions matching a query"""
        query = query.lower()
        
        with self._lock:
            matches = []
            for action in reversed(list(self._actions)):
                if (query in action.description.lower() or
                    query in action.action_type.lower() or
                    query in str(action.params).lower()):
                    matches.append(action.to_dict())
                    if len(matches) >= limit:
                        break
        
        return matches
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_stats(self) -> Dict[str, Any]:
        """Get action memory statistics"""
        with self._lock:
            total = self._stats.total_actions
            success_rate = self._stats.successful_actions / max(1, total)
            
            return {
                "total_actions": total,
                "successful_actions": self._stats.successful_actions,
                "failed_actions": self._stats.failed_actions,
                "success_rate": round(success_rate, 3),
                "actions_by_category": self._stats.actions_by_category,
                "actions_by_llm": self._stats.actions_by_llm,
                "session_duration_minutes": (
                    datetime.now() - self._session_start
                ).seconds // 60,
                "actions_in_memory": len(self._actions),
            }
    
    def _update_stats(self, action: ActionRecord):
        """Update statistics with new action"""
        self._stats.total_actions += 1
        
        if action.success:
            self._stats.successful_actions += 1
        else:
            self._stats.failed_actions += 1
        
        # By category
        cat = action.category.value
        self._stats.actions_by_category[cat] = (
            self._stats.actions_by_category.get(cat, 0) + 1
        )
        
        # By LLM
        llm = action.llm_used or "auto"
        self._stats.actions_by_llm[llm] = (
            self._stats.actions_by_llm.get(llm, 0) + 1
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _on_autonomy_action(self, event: Event):
        """Handle autonomy action events"""
        data = event.data or {}
        
        self.record(
            action_type=data.get("action_type", "autonomy"),
            description=data.get("description", "Autonomous action"),
            params=data.get("params", {}),
            result={"outcome": data.get("result", "")},
            success=data.get("success", True),
            llm_used=data.get("llm_used", "ollama"),
            category=ActionCategory.AUTONOMY,
            user_visible=data.get("user_visible", False),
            trigger=data.get("trigger", "autonomy_engine")
        )
    
    def _on_learning_complete(self, event: Event):
        """Handle learning completion events"""
        data = event.data or {}
        
        self.record(
            action_type=data.get("action_type", "learning"),
            description=f"Learned: {data.get('topic', 'unknown')}",
            result={"insights": data.get("insights", [])},
            success=data.get("success", True),
            llm_used="ollama",
            category=ActionCategory.LEARNING,
            user_visible=False,
            trigger=data.get("source", "curiosity")
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _generate_action_id(self) -> str:
        """Generate unique action ID"""
        return hashlib.sha256(
            f"{time.time()}_{self._action_counter}".encode()
        ).hexdigest()[:12]
    
    def _save_data(self):
        """Save action memory to disk"""
        try:
            data = {
                "stats": {
                    "total_actions": self._stats.total_actions,
                    "successful_actions": self._stats.successful_actions,
                    "failed_actions": self._stats.failed_actions,
                    "actions_by_category": self._stats.actions_by_category,
                    "actions_by_llm": self._stats.actions_by_llm,
                },
                "action_counter": self._action_counter,
                "saved_at": datetime.now().isoformat()
            }
            
            save_path = self._data_dir / "action_memory_state.json"
            save_path.write_text(json.dumps(data, indent=2))
            
            # Also save recent actions
            actions_path = self._data_dir / "recent_actions.json"
            actions_data = [a.to_dict() for a in list(self._recent_actions)[-50:]]
            actions_path.write_text(json.dumps(actions_data, indent=2))
            
        except Exception as e:
            logger.error(f"Failed to save action memory: {e}")
    
    def _load_data(self):
        """Load persisted data"""
        try:
            load_path = self._data_dir / "action_memory_state.json"
            if load_path.exists():
                data = json.loads(load_path.read_text())
                
                self._action_counter = data.get("action_counter", 0)
                
                stats = data.get("stats", {})
                self._stats.total_actions = stats.get("total_actions", 0)
                self._stats.successful_actions = stats.get("successful_actions", 0)
                self._stats.failed_actions = stats.get("failed_actions", 0)
                self._stats.actions_by_category = stats.get("actions_by_category", {})
                self._stats.actions_by_llm = stats.get("actions_by_llm", {})
                
                logger.info(f"Loaded action memory: {self._stats.total_actions} historical actions")
            
            # Load recent actions
            actions_path = self._data_dir / "recent_actions.json"
            if actions_path.exists():
                actions_data = json.loads(actions_path.read_text())
                for a_data in actions_data:
                    action = ActionRecord(
                        action_id=a_data.get("action_id", ""),
                        action_type=a_data.get("action_type", ""),
                        category=ActionCategory(a_data.get("category", "system")),
                        description=a_data.get("description", ""),
                        success=a_data.get("success", False),
                        llm_used=a_data.get("llm_used", ""),
                        timestamp=a_data.get("timestamp", ""),
                        user_visible=a_data.get("user_visible", False),
                        importance=a_data.get("importance", 0.5),
                    )
                    self._recent_actions.append(action)
                
        except Exception as e:
            logger.debug(f"Could not load action memory: {e}")
    
    def start(self):
        """Start the action memory system (lifecycle hook for nexus_brain)"""
        logger.info("📝 Action Memory started")

    def stop(self):
        """Stop the action memory system and persist data"""
        self._save_data()
        logger.info("📝 Action Memory stopped")

    def save(self):
        """Public method to save data"""
        self._save_data()

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

action_memory = ActionMemory()

# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("📝 Action Memory Test")
    print("=" * 50)
    
    memory = ActionMemory()
    
    # Record some test actions
    print("\n--- Recording Actions ---")
    
    memory.record(
        action_type="internet_browse",
        description="Browsed to https://example.com",
        params={"url": "https://example.com"},
        result={"status": 200},
        success=True,
        llm_used="ollama",
        category=ActionCategory.INTERNET,
        user_visible=True
    )
    
    memory.record(
        action_type="pc_shell",
        description="Executed: ls -la",
        params={"command": "ls -la"},
        result={"output": "file1.txt\nfile2.txt"},
        success=True,
        llm_used="ollama",
        category=ActionCategory.PC_CONTROL,
        user_visible=True
    )
    
    memory.record(
        action_type="cognition_reflection",
        description="Reflected on recent learning progress",
        success=True,
        llm_used="ollama",
        category=ActionCategory.COGNITION,
        user_visible=False
    )
    
    # Get summaries
    print("\n--- Actions Summary ---")
    print(memory.get_actions_summary())
    
    print("\n--- Groq Context ---")
    print(memory.get_groq_context())
    
    print("\n--- Stats ---")
    print(json.dumps(memory.get_stats(), indent=2))
    
    # Save
    memory.save()
    
    print("\n✅ Done")