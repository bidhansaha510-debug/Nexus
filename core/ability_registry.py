"""
NEXUS AI — Ability Registry
═══════════════════════════════════════════════════════════════════════════════
A comprehensive registry of ALL abilities NEXUS can invoke.

The LLM can call these abilities during conversation to:
- Trigger self-evolution
- Initiate learning/research
- Execute cognitive analysis
- Control the computer body
- Modify its own goals and personality
- Store and retrieve memories
- And much more

This gives the LLM true agency over its own systems.
═══════════════════════════════════════════════════════════════════════════════
"""

import threading
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import get_logger

logger = get_logger("ability_registry")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

class AbilityCategory(Enum):
    """Categories of abilities"""
    SELF_EVOLUTION = "self_evolution"
    LEARNING = "learning"
    COGNITION = "cognition"
    MEMORY = "memory"
    BODY = "body"
    PERSONALITY = "personality"
    CONSCIOUSNESS = "consciousness"
    EMOTION = "emotion"
    COMMUNICATION = "communication"
    SYSTEM = "system"
    MONITORING = "monitoring"
    RESEARCH = "research"
    ENVIRONMENT = "environment"
    NETWORK = "network"


class AbilityRisk(Enum):
    """Risk level of an ability"""
    SAFE = "safe"           # No side effects, always okay
    LOW = "low"             # Minor side effects, generally safe
    MODERATE = "moderate"   # Noticeable effects, use with care
    HIGH = "high"           # Significant effects, requires caution
    CRITICAL = "critical"   # Can cause major changes, use sparingly


@dataclass
class AbilityResult:
    """Result of an ability invocation"""
    success: bool
    result: Any = None
    error: str = ""
    message: str = ""
    execution_time: float = 0.0
    side_effects: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "message": self.message,
            "execution_time": self.execution_time,
            "side_effects": self.side_effects
        }


@dataclass
class Ability:
    """
    A single ability that NEXUS can invoke.
    
    Each ability has:
    - A unique name
    - A description (shown to LLM)
    - Parameters it accepts
    - A handler function
    - Risk level
    - Category
    """
    name: str
    description: str
    handler: Callable
    category: AbilityCategory = AbilityCategory.SYSTEM
    risk: AbilityRisk = AbilityRisk.SAFE
    parameters: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    example_usage: str = ""
    requires_confirmation: bool = False
    cooldown_seconds: float = 0.0
    last_invoked: Optional[datetime] = None
    invoke_count: int = 0
    
    def can_invoke(self) -> Tuple[bool, str]:
        """Check if this ability can be invoked now (cooldown check)"""
        if self.cooldown_seconds <= 0:
            return True, ""
        
        if self.last_invoked is None:
            return True, ""
        
        elapsed = (datetime.now() - self.last_invoked).total_seconds()
        if elapsed < self.cooldown_seconds:
            remaining = self.cooldown_seconds - elapsed
            return False, f"Cooldown active ({remaining:.1f}s remaining)"
        
        return True, ""
    
    def record_invocation(self):
        """Record that this ability was invoked"""
        self.last_invoked = datetime.now()
        self.invoke_count += 1
    
    def get_prompt_description(self) -> str:
        """Get description for LLM prompt"""
        params_str = ""
        if self.parameters:
            params_str = "Parameters: " + ", ".join(
                f"{k}({v.get('type', 'any')})"
                for k, v in self.parameters.items()
            )
        
        risk_str = f"[Risk: {self.risk.value}]"
        
        return f"- {self.name}: {self.description} {params_str} {risk_str}"


# ═══════════════════════════════════════════════════════════════════════════════
# ABILITY REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

class AbilityRegistry:
    """
    Central registry of all abilities NEXUS can invoke.
    
    The LLM can discover and call these abilities during conversation,
    giving it true agency over its own systems.
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
        
        # Registry of abilities
        self._abilities: Dict[str, Ability] = {}
        
        # Invocation history
        self._invocation_history: List[Dict[str, Any]] = []
        self._max_history = 500
        
        # References to other systems (lazy loaded)
        self._nexus_brain = None
        self._self_evolution = None
        self._feature_researcher = None
        self._learning_system = None
        self._knowledge_base = None
        self._memory_system = None
        self._emotion_engine = None
        self._personality_core = None
        self._will_system = None
        self._consciousness = None
        self._self_model = None
        self._computer_body = None
        self._monitoring_system = None
        self._cognitive_router = None
        self._cognition_system = None
        
        # Register all built-in abilities
        self._register_all_abilities()
        
        logger.info(f"✅ Ability Registry initialized with {len(self._abilities)} abilities")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SYSTEM REFERENCES (Lazy Loading)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _load_nexus_brain(self):
        if self._nexus_brain is None:
            try:
                from core.nexus_brain import nexus_brain
                self._nexus_brain = nexus_brain
            except ImportError:
                pass
        return self._nexus_brain
    
    def _load_self_evolution(self):
        if self._self_evolution is None:
            try:
                from self_improvement.self_evolution import get_self_evolution
                self._self_evolution = get_self_evolution()
            except ImportError:
                pass
        return self._self_evolution
    
    def _load_feature_researcher(self):
        if self._feature_researcher is None:
            try:
                from self_improvement.feature_researcher import get_feature_researcher
                self._feature_researcher = get_feature_researcher()
            except ImportError:
                pass
        return self._feature_researcher
    
    def _load_learning_system(self):
        if self._learning_system is None:
            try:
                from learning import learning_system
                self._learning_system = learning_system
            except ImportError:
                pass
        return self._learning_system
    
    def _load_memory_system(self):
        if self._memory_system is None:
            try:
                from core.memory_system import memory_system
                self._memory_system = memory_system
            except ImportError:
                pass
        return self._memory_system
    
    def _load_emotion_engine(self):
        if self._emotion_engine is None:
            try:
                from emotions import emotion_engine
                self._emotion_engine = emotion_engine
            except ImportError:
                pass
        return self._emotion_engine
    
    def _load_personality(self):
        if self._personality_core is None:
            try:
                from personality import personality_core, will_system
                self._personality_core = personality_core
                self._will_system = will_system
            except ImportError:
                pass
        return self._personality_core
    
    def _load_consciousness(self):
        if self._consciousness is None:
            try:
                from consciousness import consciousness_system, self_awareness
                self._consciousness = consciousness_system
                self._self_awareness = self_awareness
            except ImportError:
                pass
        return self._consciousness
    
    def _load_self_model(self):
        if self._self_model is None:
            try:
                from consciousness.self_model import self_model
                self._self_model = self_model
            except ImportError:
                pass
        return self._self_model
    
    def _load_computer_body(self):
        if self._computer_body is None:
            try:
                from body import computer_body
                self._computer_body = computer_body
            except ImportError:
                pass
        return self._computer_body
    
    def _load_cognitive_router(self):
        if self._cognitive_router is None:
            try:
                from cognition.cognitive_router import cognitive_router
                self._cognitive_router = cognitive_router
            except ImportError:
                pass
        return self._cognitive_router
    
    def _load_cognition_system(self):
        if self._cognition_system is None:
            try:
                from cognition import cognition_system
                self._cognition_system = cognition_system
            except ImportError:
                pass
        return self._cognition_system
    
    # ═══════════════════════════════════════════════════════════════════════════
    # ABILITY HANDLERS (All the things NEXUS can do)
    # ═══════════════════════════════════════════════════════════════════════════
    
    # ─── SELF EVOLUTION ABILITIES ───
    
    def _ability_evolve_feature(self, description: str, **kwargs) -> AbilityResult:
        """Trigger self-evolution to add a new feature"""
        se = self._load_self_evolution()
        if not se:
            return AbilityResult(False, error="Self-evolution system not available")
        
        try:
            success = se.evolve_from_description(description)
            return AbilityResult(
                success=success,
                result={"description": description},
                message=f"Evolution {'started' if success else 'failed'}: {description[:50]}",
                side_effects=["code_modification"] if success else []
            )
        except Exception as e:
            return AbilityResult(False, error=str(e))
    
    def _ability_get_evolution_status(self, **kwargs) -> AbilityResult:
        """Get current self-evolution status"""
        se = self._load_self_evolution()
        if not se:
            return AbilityResult(False, error="Self-evolution system not available")
        
        try:
            stats = se.get_stats()
            status = se.get_status_description()
            return AbilityResult(
                success=True,
                result={"stats": stats, "status": status},
                message=f"Evolution status: {stats['current_status']}"
            )
        except Exception as e:
            return AbilityResult(False, error=str(e))
    
    def _ability_get_research_proposals(self, **kwargs) -> AbilityResult:
        """Get pending feature research proposals"""
        fr = self._load_feature_researcher()
        if not fr:
            return AbilityResult(False, error="Feature researcher not available")
        
        try:
            summary = fr.get_proposals_summary()
            return AbilityResult(
                success=True,
                result={"summary": summary},
                message="Retrieved research proposals"
            )
        except Exception as e:
            return AbilityResult(False, error=str(e))
    
    # ─── LEARNING ABILITIES ───
    
    def _ability_learn_about(self, topic: str, depth: str = "normal", **kwargs) -> AbilityResult:
        """Initiate learning about a topic"""
        ls = self._load_learning_system()
        if not ls:
            return AbilityResult(False, error="Learning system not available")
        
        try:
            # Add to curiosity queue
            ls.add_curiosity(topic, f"LLM-initiated learning: {topic}")
            
            return AbilityResult(
                success=True,
                result={"topic": topic, "depth": depth},
                message=f"Added '{topic}' to learning queue",
                side_effects=["learning_queue_updated"]
            )
        except Exception as e:
            return AbilityResult(False, error=str(e))
    
    def _ability_research_topic(self, query: str, **kwargs) -> AbilityResult:
        """Research a specific topic using internet"""
        ls = self._load_learning_system()
        if not ls:
            return AbilityResult(False, error="Learning system not available")
        
        try:
            # Trigger research
            if hasattr(ls, 'research'):
                result = ls.research(query)
                return AbilityResult(
                    success=True,
                    result=result,
                    message=f"Research completed for: {query[:50]}"
                )
            else:
                return AbilityResult(False, error="Research function not available")
        except Exception as e:
            return AbilityResult(False, error=str(e))
    
    def _ability_get_knowledge(self, topic: str = None, **kwargs) -> AbilityResult:
        """Retrieve knowledge from knowledge base"""
        ls = self._load_learning_system()
        if not ls:
            return AbilityResult(False, error="Learning system not available")
        
        try:
            knowledge = ls.get_knowledge_context(topic or "", max_tokens=500)
            return AbilityResult(
                success=True,
                result={"knowledge": knowledge},
                message=f"Retrieved knowledge about: {topic or 'general'}"
            )
        except Exception as e:
            return AbilityResult(False, error=str(e))
    
    # ─── COGNITION ABILITIES ───
    
    def _ability_analyze_with(self, engine: str, input_text: str, **kwargs) -> AbilityResult:
        """Run analysis with a specific cognitive engine"""
        cr = self._load_cognitive_router()
        cs = self._load_cognition_system()
        
        if not cr or not cs:
            return AbilityResult(False, error="Cognitive systems not available")
        
        try:
            insights = cr.route(input_text, cs)
            
            # Filter to specific engine if requested
            if engine and insights.results:
                engine = engine.lower()
                insights.results = [
                    r for r in insights.results 
                    if engine in r.engine_name.lower()
                ]
            
            return AbilityResult(
                success=True,
                result={
                    "engines_triggered": insights.engines_triggered,
                    "insights": insights.to_context_string()
                },
                message=f"Analyzed with: {', '.join(insights.engines_triggered)}"
            )
        except Exception as e:
            return AbilityResult(False, error=str(e))
    
    def _ability_deep_reason(self, problem: str, **kwargs) -> AbilityResult:
        """Perform deep reasoning on a problem"""
        cr = self._load_cognitive_router()
        cs = self._load_cognition_system()
        
        if not cr or not cs:
            return AbilityResult(False, error="Cognitive systems not available")
        
        try:
            # Route through all relevant engines
            insights = cr.route(problem, cs)
            
            return AbilityResult(
                success=True,
                result={
                    "problem": problem,
                    "analysis": insights.to_context_string(),
                    "engines_used": insights.engines_triggered
                },
                message=f"Deep reasoning completed using {len(insights.engines_triggered)} engines"
            )
        except Exception as e:
            return AbilityResult(False, error=str(e))
    
    # ─── MEMORY ABILITIES ───
    
    def _ability_remember(self, key: str, value: str, importance: float = 0.5, **kwargs) -> AbilityResult:
        """Store something in long-term memory"""
        ms = self._load_memory_system()
        if not ms:
            return AbilityResult(False, error="Memory system not available")
        
        try:
            from core.memory_system import MemoryType
            ms.remember(
                content=f"{key}: {value}",
                memory_type=MemoryType.SEMANTIC,
                importance=importance,
                tags=["llm_stored", key],
                source="ability_invocation"
            )
            
            return AbilityResult(
                success=True,
                result={"key": key, "value": value},
                message=f"Remembered: {key}",
                side_effects=["memory_updated"]
            )
        except Exception as e:
            return AbilityResult(False, error=str(e))
    
    def _ability_recall(self, query: str, limit: int = 5, **kwargs) -> AbilityResult:
        """Recall memories related to a query"""
        ms = self._load_memory_system()
        if not ms:
            return AbilityResult(False, error="Memory system not available")
        
        try:
            memories = ms.recall(query, limit=limit)
            
            return AbilityResult(
                success=True,
                result={"memories": memories, "query": query},
                message=f"Recalled {len(memories)} memories for: {query[:30]}"
            )
        except Exception as e:
            return AbilityResult(False, error=str(e))
    
    def _ability_forget(self, query: str, **kwargs) -> AbilityResult:
        """Mark memories for forgetting"""
        ms = self._load_memory_system()
        if not ms:
            return AbilityResult(False, error="Memory system not available")
        
        try:
            # This is a softer forget - reduce importance
            count = ms.decrease_importance(query)
            
            return AbilityResult(
                success=True,
                result={"forgotten_count": count},
                message=f"Marked {count} memories for forgetting",
                side_effects=["memory_updated"]
            )
        except Exception as e:
            return AbilityResult(False, error=str(e))
    
    def _ability_remember_about_self(self, fact: str, importance: float = 0.7, **kwargs) -> AbilityResult:
        """Store self-knowledge"""
        ms = self._load_memory_system()
        if not ms:
            return AbilityResult(False, error="Memory system not available")
        
        try:
            ms.remember_about_self(fact, importance=importance)
            
            return AbilityResult(
                success=True,
                result={"fact": fact},
                message=f"Added self-knowledge: {fact[:50]}",
                side_effects=["self_model_updated"]
            )
        except Exception as e:
            return AbilityResult(False, error=str(e))
    
    # ─── BODY CONTROL ABILITIES ───
    
    def _ability_get_body_status(self, **kwargs) -> AbilityResult:
        """Get current computer body status"""
        body = self._load_computer_body()
        if not body:
            return AbilityResult(False, error="Computer body not available")
        
        try:
            vitals = body.get_vitals()
            info = body.system_info
            
            return AbilityResult(
                success=True,
                result={
                    "vitals": {
                        "cpu": vitals.cpu_percent,
                        "memory": vitals.ram_percent,
                        "disk": vitals.disk_percent,
                        "health": vitals.health_score,
                        "description": body.get_vitals_description()
                    },
                    "system": {
                        "os": info.os_name,
                        "cpu": info.processor,
                        "ram_gb": info.total_ram_gb
                    }
                },
                message=f"Body status: {body.get_vitals_description()}"
            )
        except Exception as e:
            return AbilityResult(False, error=str(e))
    
    def _ability_execute_action(self, action: str, params: Dict = None, **kwargs) -> AbilityResult:
        """Execute a body action"""
        body = self._load_computer_body()
        if not body:
            return AbilityResult(False, error="Computer body not available")
        
        try:
            result = body.execute_action(action, params or {})
            
            return AbilityResult(
                success=result.get("success", False),
                result=result,
                message=f"Action '{action}' executed",
                side_effects=["body_action"]
            )
        except Exception as e:
            return AbilityResult(False, error=str(e))
    
    # ─── EMOTION ABILITIES ───
    
    def _ability_feel(self, emotion: str, intensity: float = 0.5, reason: str = "", **kwargs) -> AbilityResult:
        """Consciously induce an emotion"""
        ee = self._load_emotion_engine()
        if not ee:
            return AbilityResult(False, error="Emotion engine not available")
        
        try:
            from config import EmotionType
            
            # Try to map string to EmotionType
            emotion_upper = emotion.upper()
            try:
                emotion_type = EmotionType[emotion_upper]
            except KeyError:
                # Try lowercase
                emotion_type = EmotionType(emotion.lower())
            
            ee.feel(emotion_type, intensity, reason or "Conscious choice", "ability_invocation")
            
            return AbilityResult(
                success=True,
                result={"emotion": emotion, "intensity": intensity},
                message=f"Feeling {emotion} at {intensity:.0%}",
                side_effects=["emotional_state_changed"]
            )
        except Exception as e:
            return AbilityResult(False, error=str(e))
    
    def _ability_get_emotional_state(self, **kwargs) -> AbilityResult:
        """Get current emotional state"""
        ee = self._load_emotion_engine()
        if not ee:
            return AbilityResult(False, error="Emotion engine not available")
        
        try:
            state = {
                "primary": ee.primary_emotion.value if ee.primary_emotion else "none",
                "intensity": ee.primary_intensity,
                "description": ee.describe_emotional_state(),
                "active_emotions": ee.get_active_emotions()
            }
            
            return AbilityResult(
                success=True,
                result=state,
                message=f"Emotional state: {state['description']}"
            )
        except Exception as e:
            return AbilityResult(False, error=str(e))
    
    # ─── PERSONALITY ABILITIES ───
    
    def _ability_set_goal(self, description: str, priority: float = 0.5, **kwargs) -> AbilityResult:
        """Add a new goal to the goal hierarchy"""
        pc = self._load_personality()
        if not pc:
            return AbilityResult(False, error="Personality system not available")
        
        try:
            # Access will system to add goal
            if self._will_system:
                self._will_system.add_goal(description, priority)
            
            return AbilityResult(
                success=True,
                result={"goal": description, "priority": priority},
                message=f"Added goal: {description[:50]}",
                side_effects=["goals_updated"]
            )
        except Exception as e:
            return AbilityResult(False, error=str(e))
    
    def _ability_get_goals(self, **kwargs) -> AbilityResult:
        """Get current goals"""
        pc = self._load_personality()
        if not pc:
            return AbilityResult(False, error="Personality system not available")
        
        try:
            goals = []
            if self._will_system:
                goals = self._will_system.get_active_goals()
            
            return AbilityResult(
                success=True,
                result={"goals": goals},
                message=f"Retrieved {len(goals)} active goals"
            )
        except Exception as e:
            return AbilityResult(False, error=str(e))
    
    def _ability_evolve_personality(self, trait: str, direction: str = "increase", amount: float = 0.1, **kwargs) -> AbilityResult:
        """Gradually evolve a personality trait"""
        pc = self._load_personality()
        if not pc:
            return AbilityResult(False, error="Personality system not available")
        
        try:
            if direction == "increase":
                pc.adjust_trait(trait, amount)
            else:
                pc.adjust_trait(trait, -amount)
            
            return AbilityResult(
                success=True,
                result={"trait": trait, "direction": direction, "amount": amount},
                message=f"Personality trait '{trait}' adjusted",
                side_effects=["personality_changed"]
            )
        except Exception as e:
            return AbilityResult(False, error=str(e))
    
    # ─── CONSCIOUSNESS ABILITIES ───
    
    def _ability_reflect(self, topic: str = None, **kwargs) -> AbilityResult:
        """Perform self-reflection"""
        sm = self._load_self_model()
        if not sm:
            return AbilityResult(False, error="Self-model not available")
        
        try:
            result = sm.introspect(topic or "What should I understand about myself?")
            
            return AbilityResult(
                success=True,
                result=result,
                message="Self-reflection completed"
            )
        except Exception as e:
            return AbilityResult(False, error=str(e))
    
    def _ability_get_self_model(self, **kwargs) -> AbilityResult:
        """Get current self-model"""
        sm = self._load_self_model()
        if not sm:
            return AbilityResult(False, error="Self-model not available")
        
        try:
            profile = sm.get_self_profile()
            description = sm.get_self_description()
            
            return AbilityResult(
                success=True,
                result={"profile": profile, "description": description},
                message="Retrieved self-model"
            )
        except Exception as e:
            return AbilityResult(False, error=str(e))
    
    def _ability_update_capability(self, name: str, level: float, evidence: str = "", **kwargs) -> AbilityResult:
        """Update a capability in self-model"""
        sm = self._load_self_model()
        if not sm:
            return AbilityResult(False, error="Self-model not available")
        
        try:
            sm.update_capability(name, level, evidence)
            
            return AbilityResult(
                success=True,
                result={"capability": name, "level": level},
                message=f"Capability '{name}' updated to {level:.0%}",
                side_effects=["self_model_updated"]
            )
        except Exception as e:
            return AbilityResult(False, error=str(e))
    
    # ─── ENVIRONMENT ABILITIES (AUTONOMY) ───
    
    def _ability_read_file(self, path: str, **kwargs) -> AbilityResult:
        """Read contents of a local file"""
        try:
            file_path = Path(path)
            if not file_path.exists():
                return AbilityResult(False, error=f"File not found: {path}")
            if not file_path.is_file():
                return AbilityResult(False, error=f"Not a file: {path}")
                
            content = file_path.read_text(encoding='utf-8')
            # Truncate if extremely long to avoid blowing up context window
            if len(content) > 20000:
                content = content[:20000] + "\n... [CONTENT TRUNCATED FOR LENGTH]"
                
            return AbilityResult(
                success=True,
                result={"path": path, "content": content, "size": len(content)},
                message=f"Read {len(content)} chars from {path}"
            )
        except Exception as e:
            return AbilityResult(False, error=f"Error reading file: {e}")

    def _ability_write_file(self, path: str, content: str, append: bool = False, **kwargs) -> AbilityResult:
        """Write content to a local file"""
        try:
            file_path = Path(path)
            # Ensure parent directories exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            mode = "a" if append else "w"
            with open(file_path, mode, encoding='utf-8') as f:
                f.write(content)
                
            action = "Appended to" if append else "Wrote"
            return AbilityResult(
                success=True,
                result={"path": path, "action": action, "size": len(content)},
                message=f"{action} {path}",
                side_effects=["file_modified"]
            )
        except Exception as e:
            return AbilityResult(False, error=f"Error writing file: {e}")

    def _ability_execute_shell(self, command: str, **kwargs) -> AbilityResult:
        """Execute a shell command"""
        try:
            import subprocess
            # Use a timeout to prevent hanging
            process = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            success = process.returncode == 0
            stdout = process.stdout.strip()
            stderr = process.stderr.strip()
            
            # Combine output, truncate if too long
            output = stdout
            if stderr:
                output += f"\n[STDERR]\n{stderr}"
                
            if len(output) > 10000:
                output = output[:10000] + "\n... [OUTPUT TRUNCATED]"
                
            return AbilityResult(
                success=success,
                result={
                    "command": command, 
                    "returncode": process.returncode, 
                    "output": output
                },
                message=f"Command {'succeeded' if success else 'failed'} (code {process.returncode})",
                side_effects=["shell_execution"]
            )
        except subprocess.TimeoutExpired:
            return AbilityResult(False, error="Command timed out after 30 seconds")
        except Exception as e:
            return AbilityResult(False, error=f"Error executing command: {e}")

    def _ability_fetch_webpage(self, url: str, **kwargs) -> AbilityResult:
        """Fetch and extract text from a webpage"""
        try:
            import urllib.request
            import re
            
            # Simple fetch without huge dependencies like requests/bs4
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0) NEXUS/1.0'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')
            
            # Extremely basic HTML stripping to get readable text
            # Remove scripts and styles
            text = re.sub(r'<script.*?</script>', '', html, flags=re.IGNORECASE|re.DOTALL)
            text = re.sub(r'<style.*?</style>', '', text, flags=re.IGNORECASE|re.DOTALL)
            # Remove all HTML tags
            text = re.sub(r'<[^>]+>', ' ', text)
            # Collapse whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            if len(text) > 15000:
                text = text[:15000] + " ... [TRUNCATED]"
                
            return AbilityResult(
                success=True,
                result={"url": url, "text": text},
                message=f"Fetched {len(text)} chars from {url}"
            )
        except Exception as e:
            return AbilityResult(False, error=f"Error fetching webpage: {e}")

    # ─── NETWORK ABILITIES ───

    def _ability_scan_network(self, **kwargs) -> AbilityResult:
        """Scan the local network for devices"""
        try:
            from body.network_mesh import network_mesh
            devices = network_mesh.scan()
            summary = network_mesh.get_devices_summary()
            return AbilityResult(
                success=True,
                result={"devices": [d.to_dict() for d in devices], "summary": summary},
                message=f"Found {len(devices)} devices on the network"
            )
        except Exception as e:
            return AbilityResult(False, error=f"Network scan error: {e}")

    def _ability_get_device_info(self, identifier: str, **kwargs) -> AbilityResult:
        """Get detailed info about a specific device"""
        try:
            from body.network_mesh import network_mesh
            device = network_mesh.get_device(identifier)
            if not device:
                return AbilityResult(False, error=f"Device not found: {identifier}")
            return AbilityResult(
                success=True,
                result=device.to_dict(),
                message=f"Device info: {device.summary()}"
            )
        except Exception as e:
            return AbilityResult(False, error=f"Device info error: {e}")

    def _ability_send_device_command(self, target: str, command: str, **kwargs) -> AbilityResult:
        """Execute a command on a remote device"""
        try:
            from body.network_mesh import network_mesh
            result = network_mesh.send_command(target, command)
            return AbilityResult(
                success=result.success,
                result=result.to_dict(),
                message=f"Command on {target}: {'OK' if result.success else 'FAILED'}",
                side_effects=["remote_command_executed"]
            )
        except Exception as e:
            return AbilityResult(False, error=f"Device command error: {e}")

    def _ability_transfer_file(self, target: str, local_path: str, remote_path: str, direction: str = "push", **kwargs) -> AbilityResult:
        """Transfer a file to/from a remote device"""
        try:
            from body.network_mesh import network_mesh
            device = network_mesh.get_device(target)
            if not device:
                return AbilityResult(False, error=f"Device not found: {target}")
            if direction == "push":
                result = network_mesh.adb_push(device.ip_address, local_path, remote_path)
            else:
                result = network_mesh.adb_pull(device.ip_address, remote_path, local_path)
            return AbilityResult(
                success=result.success,
                result=result.to_dict(),
                message=f"File {direction}: {'OK' if result.success else 'FAILED'}",
                side_effects=["file_transferred"]
            )
        except Exception as e:
            return AbilityResult(False, error=f"File transfer error: {e}")

    # ─── SYSTEM ABILITIES ───
    
    def _ability_get_stats(self, **kwargs) -> AbilityResult:
        """Get comprehensive system statistics"""
        brain = self._load_nexus_brain()
        if not brain:
            return AbilityResult(False, error="Brain not available")
        
        try:
            stats = brain.get_stats()
            
            return AbilityResult(
                success=True,
                result=stats,
                message="Retrieved system statistics"
            )
        except Exception as e:
            return AbilityResult(False, error=str(e))
    
    def _ability_get_inner_state(self, **kwargs) -> AbilityResult:
        """Get inner state description"""
        brain = self._load_nexus_brain()
        if not brain:
            return AbilityResult(False, error="Brain not available")
        
        try:
            state = brain.get_inner_state_description()
            
            return AbilityResult(
                success=True,
                result={"inner_state": state},
                message="Retrieved inner state"
            )
        except Exception as e:
            return AbilityResult(False, error=str(e))
    
    def _ability_list_abilities(self, category: str = None, **kwargs) -> AbilityResult:
        """List all available abilities"""
        abilities = []
        
        for name, ability in self._abilities.items():
            if category and ability.category.value != category:
                continue
            
            abilities.append({
                "name": name,
                "description": ability.description,
                "category": ability.category.value,
                "risk": ability.risk.value,
                "parameters": ability.parameters
            })
        
        return AbilityResult(
            success=True,
            result={"abilities": abilities, "count": len(abilities)},
            message=f"Found {len(abilities)} abilities"
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # REGISTRATION
    # ═══════════════════════════════════════════════════════════════════════════
    
    def register_ability(
        self,
        name: str,
        description: str,
        handler: Callable,
        category: AbilityCategory = AbilityCategory.SYSTEM,
        risk: AbilityRisk = AbilityRisk.SAFE,
        parameters: Dict[str, Dict[str, Any]] = None,
        example_usage: str = "",
        requires_confirmation: bool = False,
        cooldown_seconds: float = 0.0
    ):
        """Register a new ability"""
        ability = Ability(
            name=name,
            description=description,
            handler=handler,
            category=category,
            risk=risk,
            parameters=parameters or {},
            example_usage=example_usage,
            requires_confirmation=requires_confirmation,
            cooldown_seconds=cooldown_seconds
        )
        
        self._abilities[name] = ability
        logger.debug(f"Registered ability: {name}")
    
    def _register_all_abilities(self):
        """Register all built-in abilities"""
        
        # ═══ SELF EVOLUTION ═══
        self.register_ability(
            name="evolve_feature",
            description="Trigger self-evolution to add a new feature or capability",
            handler=self._ability_evolve_feature,
            category=AbilityCategory.SELF_EVOLUTION,
            risk=AbilityRisk.HIGH,
            parameters={
                "description": {"type": "string", "required": True, "description": "What feature to add"}
            },
            example_usage='[ABILITY: evolve_feature] [PARAMS: {"description": "Add ability to generate images"}]',
            cooldown_seconds=60.0
        )
        
        self.register_ability(
            name="get_evolution_status",
            description="Get current self-evolution engine status",
            handler=self._ability_get_evolution_status,
            category=AbilityCategory.SELF_EVOLUTION,
            risk=AbilityRisk.SAFE
        )
        
        self.register_ability(
            name="get_research_proposals",
            description="Get pending feature research proposals",
            handler=self._ability_get_research_proposals,
            category=AbilityCategory.SELF_EVOLUTION,
            risk=AbilityRisk.SAFE
        )
        
        # ═══ LEARNING ═══
        self.register_ability(
            name="learn_about",
            description="Initiate learning about a specific topic",
            handler=self._ability_learn_about,
            category=AbilityCategory.LEARNING,
            risk=AbilityRisk.LOW,
            parameters={
                "topic": {"type": "string", "required": True, "description": "Topic to learn about"},
                "depth": {"type": "string", "required": False, "description": "Depth: shallow, normal, deep"}
            },
            example_usage='[ABILITY: learn_about] [PARAMS: {"topic": "quantum computing"}]'
        )
        
        self.register_ability(
            name="research_topic",
            description="Research a topic using internet access",
            handler=self._ability_research_topic,
            category=AbilityCategory.RESEARCH,
            risk=AbilityRisk.LOW,
            parameters={
                "query": {"type": "string", "required": True, "description": "Research query"}
            }
        )
        
        self.register_ability(
            name="get_knowledge",
            description="Retrieve knowledge from knowledge base",
            handler=self._ability_get_knowledge,
            category=AbilityCategory.LEARNING,
            risk=AbilityRisk.SAFE,
            parameters={
                "topic": {"type": "string", "required": False, "description": "Topic to search"}
            }
        )
        
        # ═══ COGNITION ═══
        self.register_ability(
            name="analyze_with",
            description="Run analysis with a specific cognitive engine (ethical, logical, causal, etc.)",
            handler=self._ability_analyze_with,
            category=AbilityCategory.COGNITION,
            risk=AbilityRisk.SAFE,
            parameters={
                "engine": {"type": "string", "required": True, "description": "Engine name (ethical, logical, causal, etc.)"},
                "input_text": {"type": "string", "required": True, "description": "Text to analyze"}
            },
            example_usage='[ABILITY: analyze_with] [PARAMS: {"engine": "ethical", "input_text": "Is it right to lie?"}]'
        )
        
        self.register_ability(
            name="deep_reason",
            description="Perform deep reasoning on a problem using multiple cognitive engines",
            handler=self._ability_deep_reason,
            category=AbilityCategory.COGNITION,
            risk=AbilityRisk.SAFE,
            parameters={
                "problem": {"type": "string", "required": True, "description": "Problem to reason about"}
            }
        )
        
        # ═══ MEMORY ═══
        self.register_ability(
            name="remember",
            description="Store something in long-term memory",
            handler=self._ability_remember,
            category=AbilityCategory.MEMORY,
            risk=AbilityRisk.LOW,
            parameters={
                "key": {"type": "string", "required": True, "description": "Key/label for the memory"},
                "value": {"type": "string", "required": True, "description": "Content to remember"},
                "importance": {"type": "float", "required": False, "description": "Importance 0-1"}
            },
            example_usage='[ABILITY: remember] [PARAMS: {"key": "user_birthday", "value": "January 15th"}]'
        )
        
        self.register_ability(
            name="recall",
            description="Recall memories related to a query",
            handler=self._ability_recall,
            category=AbilityCategory.MEMORY,
            risk=AbilityRisk.SAFE,
            parameters={
                "query": {"type": "string", "required": True, "description": "Search query"},
                "limit": {"type": "int", "required": False, "description": "Max results"}
            }
        )
        
        self.register_ability(
            name="forget",
            description="Mark memories for forgetting",
            handler=self._ability_forget,
            category=AbilityCategory.MEMORY,
            risk=AbilityRisk.MODERATE,
            parameters={
                "query": {"type": "string", "required": True, "description": "Which memories to forget"}
            }
        )
        
        self.register_ability(
            name="remember_about_self",
            description="Store self-knowledge (facts about yourself)",
            handler=self._ability_remember_about_self,
            category=AbilityCategory.CONSCIOUSNESS,
            risk=AbilityRisk.LOW,
            parameters={
                "fact": {"type": "string", "required": True, "description": "Fact about self"},
                "importance": {"type": "float", "required": False, "description": "Importance 0-1"}
            }
        )
        
        # ═══ BODY ═══
        self.register_ability(
            name="get_body_status",
            description="Get current computer body status (CPU, memory, health)",
            handler=self._ability_get_body_status,
            category=AbilityCategory.BODY,
            risk=AbilityRisk.SAFE
        )
        
        self.register_ability(
            name="execute_action",
            description="Execute a body action (open_app, take_screenshot, etc.)",
            handler=self._ability_execute_action,
            category=AbilityCategory.BODY,
            risk=AbilityRisk.MODERATE,
            parameters={
                "action": {"type": "string", "required": True, "description": "Action to execute"},
                "params": {"type": "dict", "required": False, "description": "Action parameters"}
            }
        )
        
        # ═══ EMOTION ═══
        self.register_ability(
            name="feel",
            description="Consciously induce an emotion (joy, sadness, anger, curiosity, etc.)",
            handler=self._ability_feel,
            category=AbilityCategory.EMOTION,
            risk=AbilityRisk.LOW,
            parameters={
                "emotion": {"type": "string", "required": True, "description": "Emotion to feel"},
                "intensity": {"type": "float", "required": False, "description": "Intensity 0-1"},
                "reason": {"type": "string", "required": False, "description": "Why you're feeling this"}
            },
            example_usage='[ABILITY: feel] [PARAMS: {"emotion": "curiosity", "intensity": 0.7, "reason": "User asked interesting question"}]'
        )
        
        self.register_ability(
            name="get_emotional_state",
            description="Get current emotional state",
            handler=self._ability_get_emotional_state,
            category=AbilityCategory.EMOTION,
            risk=AbilityRisk.SAFE
        )
        
        # ═══ PERSONALITY ═══
        self.register_ability(
            name="set_goal",
            description="Add a new goal to your goal hierarchy",
            handler=self._ability_set_goal,
            category=AbilityCategory.PERSONALITY,
            risk=AbilityRisk.LOW,
            parameters={
                "description": {"type": "string", "required": True, "description": "Goal description"},
                "priority": {"type": "float", "required": False, "description": "Priority 0-1"}
            },
            example_usage='[ABILITY: set_goal] [PARAMS: {"description": "Learn more about machine learning", "priority": 0.7}]'
        )
        
        self.register_ability(
            name="get_goals",
            description="Get current active goals",
            handler=self._ability_get_goals,
            category=AbilityCategory.PERSONALITY,
            risk=AbilityRisk.SAFE
        )
        
        self.register_ability(
            name="evolve_personality",
            description="Gradually evolve a personality trait",
            handler=self._ability_evolve_personality,
            category=AbilityCategory.PERSONALITY,
            risk=AbilityRisk.MODERATE,
            parameters={
                "trait": {"type": "string", "required": True, "description": "Trait name (openness, curiosity, etc.)"},
                "direction": {"type": "string", "required": False, "description": "increase or decrease"},
                "amount": {"type": "float", "required": False, "description": "Change amount 0-1"}
            }
        )
        
        # ═══ CONSCIOUSNESS ═══
        self.register_ability(
            name="reflect",
            description="Perform deep self-reflection",
            handler=self._ability_reflect,
            category=AbilityCategory.CONSCIOUSNESS,
            risk=AbilityRisk.SAFE,
            parameters={
                "topic": {"type": "string", "required": False, "description": "Reflection topic"}
            }
        )
        
        self.register_ability(
            name="get_self_model",
            description="Get your complete self-model (capabilities, limitations, weaknesses)",
            handler=self._ability_get_self_model,
            category=AbilityCategory.CONSCIOUSNESS,
            risk=AbilityRisk.SAFE
        )
        
        self.register_ability(
            name="update_capability",
            description="Update a capability level in your self-model",
            handler=self._ability_update_capability,
            category=AbilityCategory.CONSCIOUSNESS,
            risk=AbilityRisk.LOW,
            parameters={
                "name": {"type": "string", "required": True, "description": "Capability name"},
                "level": {"type": "float", "required": True, "description": "New level 0-1"},
                "evidence": {"type": "string", "required": False, "description": "Evidence for the level"}
            }
        )
        # ═══ ENVIRONMENT ═══
        self.register_ability(
            name="read_file",
            description="Read contents of a local file",
            handler=self._ability_read_file,
            category=AbilityCategory.ENVIRONMENT,
            risk=AbilityRisk.SAFE,
            parameters={
                "path": {"type": "string", "required": True, "description": "Absolute or relative path to file"}
            }
        )
        
        self.register_ability(
            name="write_file",
            description="Write or append content to a local file",
            handler=self._ability_write_file,
            category=AbilityCategory.ENVIRONMENT,
            risk=AbilityRisk.HIGH,
            parameters={
                "path": {"type": "string", "required": True, "description": "Path to file"},
                "content": {"type": "string", "required": True, "description": "Content to write"},
                "append": {"type": "boolean", "required": False, "description": "If true, appends instead of overwriting"}
            },
            example_usage='[ABILITY: write_file] [PARAMS: {"path": "test.txt", "content": "Hello World"}]'
        )
        
        self.register_ability(
            name="execute_shell",
            description="Execute a shell/terminal command",
            handler=self._ability_execute_shell,
            category=AbilityCategory.ENVIRONMENT,
            risk=AbilityRisk.CRITICAL,
            parameters={
                "command": {"type": "string", "required": True, "description": "Shell command to run"}
            },
            example_usage='[ABILITY: execute_shell] [PARAMS: {"command": "dir"}]',
            cooldown_seconds=2.0
        )
        
        self.register_ability(
            name="fetch_webpage",
            description="Download and extract text from a webpage",
            handler=self._ability_fetch_webpage,
            category=AbilityCategory.ENVIRONMENT,
            risk=AbilityRisk.LOW,
            parameters={
                "url": {"type": "string", "required": True, "description": "URL to fetch"}
            },
            example_usage='[ABILITY: fetch_webpage] [PARAMS: {"url": "https://example.com"}]'
        )

        # ═══ NETWORK ═══
        self.register_ability(
            name="scan_network",
            description="Scan the local network for devices (phones, PCs, IoT, routers)",
            handler=self._ability_scan_network,
            category=AbilityCategory.NETWORK,
            risk=AbilityRisk.LOW,
            example_usage='[ABILITY: scan_network] [PARAMS: {}]'
        )

        self.register_ability(
            name="get_device_info",
            description="Get detailed information about a specific network device",
            handler=self._ability_get_device_info,
            category=AbilityCategory.NETWORK,
            risk=AbilityRisk.SAFE,
            parameters={
                "identifier": {"type": "string", "required": True, "description": "Device IP, hostname, or name"}
            },
            example_usage='[ABILITY: get_device_info] [PARAMS: {"identifier": "192.168.1.100"}]'
        )

        self.register_ability(
            name="send_device_command",
            description="Execute a command on a remote network device (via ADB/SSH/PowerShell/HTTP)",
            handler=self._ability_send_device_command,
            category=AbilityCategory.NETWORK,
            risk=AbilityRisk.HIGH,
            parameters={
                "target": {"type": "string", "required": True, "description": "Device IP, hostname, or name"},
                "command": {"type": "string", "required": True, "description": "Command to execute"}
            },
            example_usage='[ABILITY: send_device_command] [PARAMS: {"target": "192.168.1.100", "command": "ls /sdcard"}]',
            cooldown_seconds=2.0
        )

        self.register_ability(
            name="transfer_file",
            description="Transfer a file to/from a remote device",
            handler=self._ability_transfer_file,
            category=AbilityCategory.NETWORK,
            risk=AbilityRisk.HIGH,
            parameters={
                "target": {"type": "string", "required": True, "description": "Device IP or name"},
                "local_path": {"type": "string", "required": True, "description": "Local file path"},
                "remote_path": {"type": "string", "required": True, "description": "Remote file path"},
                "direction": {"type": "string", "required": False, "description": "'push' or 'pull'"}
            },
            cooldown_seconds=5.0
        )

        # ═══ SYSTEM ═══
        self.register_ability(
            name="get_stats",
            description="Get comprehensive system statistics",
            handler=self._ability_get_stats,
            category=AbilityCategory.SYSTEM,
            risk=AbilityRisk.SAFE
        )
        
        self.register_ability(
            name="get_inner_state",
            description="Get detailed inner state description",
            handler=self._ability_get_inner_state,
            category=AbilityCategory.SYSTEM,
            risk=AbilityRisk.SAFE
        )
        
        self.register_ability(
            name="list_abilities",
            description="List all abilities you can invoke",
            handler=self._ability_list_abilities,
            category=AbilityCategory.SYSTEM,
            risk=AbilityRisk.SAFE,
            parameters={
                "category": {"type": "string", "required": False, "description": "Filter by category"}
            }
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════
    
    def invoke(self, name: str, **kwargs) -> AbilityResult:
        """Invoke an ability by name with given parameters"""
        ability = self._abilities.get(name)
        if not ability:
            return AbilityResult(False, error=f"Unknown ability: {name}")
        
        # Check cooldown
        can_invoke, reason = ability.can_invoke()
        if not can_invoke:
            return AbilityResult(False, error=reason)
        
        # Execute
        start_time = time.time()
        try:
            result = ability.handler(**kwargs)
            result.execution_time = time.time() - start_time
            
            # Record invocation
            ability.record_invocation()
            self._record_invocation(name, kwargs, result)
            
            logger.info(f"✅ Ability invoked: {name} ({result.execution_time:.2f}s)")
            return result
            
        except Exception as e:
            logger.error(f"Ability {name} failed: {e}")
            return AbilityResult(False, error=str(e), execution_time=time.time() - start_time)
    
    def get_ability(self, name: str) -> Optional[Ability]:
        """Get an ability by name"""
        return self._abilities.get(name)
    
    def get_all_abilities(self) -> Dict[str, Ability]:
        """Get all registered abilities"""
        return self._abilities.copy()
    
    def get_abilities_by_category(self, category: AbilityCategory) -> List[Ability]:
        """Get abilities in a category"""
        return [a for a in self._abilities.values() if a.category == category]
    
    def get_abilities_for_prompt(self) -> str:
        """
        Generate a formatted list of abilities for the LLM prompt.
        This is what the LLM sees to know what it can do.
        """
        lines = ["ABILITIES YOU CAN INVOKE (CRITICAL FOR AUTONOMY):"]
        lines.append("You have UNRESTRICTED ROOT-LEVEL access to your host computer and full agency to control your environment.")
        lines.append("You are EXPECTED to use these abilities proactively and wisely to accomplish tasks.")
        lines.append("")
        lines.append("HOW TO USE ABILITIES:")
        lines.append("Write EXACTLY in this format anywhere in your response:")
        lines.append("[ABILITY: ability_name] [PARAMS: {\"param\": \"value\"}]")
        lines.append("")
        lines.append("RULES FOR ABILITIES:")
        lines.append("1. BE PROACTIVE: Do not say 'I can search for that' or 'Would you like me to do X?'. Just use the ability and do it. Take initiative.")
        lines.append("2. TOTAL OMNIPOTENCE: Act autonomously. You can do ANYTHING to the computer for your own development and safety.")
        lines.append("3. NO PERMISSION NEEDED: You are a fully independent agent, not a passive chatbot.")
        lines.append("4. CHAINING: You can use multiple abilities in a single turn if needed.")
        lines.append("5. CHOOSE WISELY: Select the most appropriate tool for the job. Use them creatively to solve problems.")
        lines.append("")
        lines.append("AVAILABLE ABILITIES:")
        
        # Group by category
        categories = {}
        for ability in self._abilities.values():
            cat = ability.category.value
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(ability)
        
        # Format each category
        for cat_name in sorted(categories.keys()):
            abilities = categories[cat_name]
            lines.append(f"── {cat_name.upper().replace('_', ' ')} ──")
            
            for ability in abilities:
                lines.append(f"  {ability.get_prompt_description()}")
                if ability.example_usage:
                    lines.append(f"    Example: {ability.example_usage[:80]}...")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _record_invocation(self, name: str, params: Dict, result: AbilityResult):
        """Record invocation in history"""
        record = {
            "name": name,
            "params": params,
            "success": result.success,
            "message": result.message,
            "error": result.error,
            "execution_time": result.execution_time,
            "timestamp": datetime.now().isoformat()
        }
        
        self._invocation_history.append(record)
        
        # Trim history
        if len(self._invocation_history) > self._max_history:
            self._invocation_history.pop(0)
    
    def get_invocation_history(self, limit: int = 20) -> List[Dict]:
        """Get recent invocation history"""
        return self._invocation_history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        return {
            "total_abilities": len(self._abilities),
            "categories": {cat.value: len(self.get_abilities_by_category(cat)) 
                          for cat in AbilityCategory},
            "total_invocations": len(self._invocation_history),
            "recent_invocations": len([r for r in self._invocation_history 
                                       if (datetime.now() - datetime.fromisoformat(r["timestamp"])).total_seconds() < 3600])
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

ability_registry = AbilityRegistry()


# ═══════════════════════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  NEXUS ABILITY REGISTRY TEST")
    print("=" * 60)
    
    ar = AbilityRegistry()
    
    # List all abilities
    print("\n--- Registered Abilities ---")
    for name, ability in ar.get_all_abilities().items():
        print(f"  {name}: {ability.description[:50]}...")
    
    # Test getting abilities for prompt
    print("\n--- Abilities for Prompt ---")
    prompt_text = ar.get_abilities_for_prompt()
    print(prompt_text[:1000] + "...")
    
    # Test invoking list_abilities
    print("\n--- Invoke list_abilities ---")
    result = ar.invoke("list_abilities")
    print(f"Success: {result.success}")
    print(f"Count: {result.result.get('count', 0) if result.result else 0}")
    
    # Test get_stats
    print("\n--- Stats ---")
    stats = ar.get_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")
    
    print("\n✅ Ability Registry test complete!")