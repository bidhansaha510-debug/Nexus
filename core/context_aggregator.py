"""
NEXUS AI — Context Aggregator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Unified context building system that integrates all subsystem data
into coherent, task-appropriate context strings for LLM injection.

This module provides:
  • Task-specific context selection
  • Priority-based context ranking
  • Token budget management
  • Context relevance scoring
  • Dynamic context assembly
"""

import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import re

from utils.logger import get_logger

logger = get_logger("context_aggregator")

# Import the context collectors
from core.groq_context_collector import groq_context_collector
from core.ollama_context_collector import ollama_context_collector

class ContextType(Enum):
    """Types of context that can be requested."""
    FULL = "full"                     # Complete subsystem data
    CONVERSATION = "conversation"     # For chat interactions
    REASONING = "reasoning"           # For cognitive tasks
    SELF_REFLECTION = "self_reflection"  # For introspection
    TASK_EXECUTION = "task_execution"  # For action execution
    LEARNING = "learning"             # For knowledge acquisition
    CREATIVE = "creative"             # For creative tasks
    ANALYTICAL = "analytical"         # For analysis tasks
    MINIMAL = "minimal"               # Bare essentials only

@dataclass
class ContextSection:
    """A section of context with metadata."""
    name: str
    content: str
    priority: int = 5  # 1-10, higher = more important
    category: str = "general"
    token_estimate: int = 0
    source: str = "unknown"
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if self.token_estimate == 0:
            # Rough estimate: 4 chars per token
            self.token_estimate = len(self.content) // 4

class ContextAggregator:
    """
    Unified context building system for NEXUS.
    
    Provides intelligent context assembly based on:
    - Task type and requirements
    - Token budget constraints
    - Priority ranking of sections
    - Relevance scoring for queries
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
        
        # Token budgets for different context types
        self._token_budgets = {
            ContextType.FULL: 4000,
            ContextType.CONVERSATION: 2000,
            ContextType.REASONING: 2500,
            ContextType.SELF_REFLECTION: 3000,
            ContextType.TASK_EXECUTION: 1500,
            ContextType.LEARNING: 2500,
            ContextType.CREATIVE: 2000,
            ContextType.ANALYTICAL: 3000,
            ContextType.MINIMAL: 500,
        }
        
        # Priority sections for different context types
        self._priority_sections = {
            ContextType.CONVERSATION: [
                "PERSONALITY CORE",
                "EMOTION ENGINE",
                "MOOD SYSTEM",
                "USER BEHAVIOR",
                "WORKING MEMORY",
                "RECENT MEMORIES",
                "INNER VOICE",
            ],
            ContextType.REASONING: [
                "COGNITION ENGINES",
                "COGNITIVE ROUTER",
                "WORLD MODEL",
                "KNOWLEDGE BASE",
                "METACOGNITION",
                "STRATEGY SELECTOR",
            ],
            ContextType.SELF_REFLECTION: [
                "SELF-MODEL",
                "METACOGNITION",
                "CONSCIOUSNESS",
                "INNER VOICE",
                "GOAL HIERARCHY",
                "WILL SYSTEM",
            ],
            ContextType.TASK_EXECUTION: [
                "TOOL EXECUTOR",
                "ABILITY EXECUTOR",
                "TASK ENGINE",
                "AUTONOMY ENGINE",
                "SYSTEM HEALTH",
            ],
            ContextType.LEARNING: [
                "KNOWLEDGE BASE",
                "CURIOSITY ENGINE",
                "RESEARCH AGENT",
                "META-LEARNER",
                "SKILL MEMORY",
            ],
            ContextType.CREATIVE: [
                "CREATIVE SYNTHESIS",
                "EMOTION ENGINE",
                "INNER VOICE",
                "PERSONALITY CORE",
                "ANALOGICAL REASONING",
            ],
            ContextType.ANALYTICAL: [
                "COGNITION ENGINES",
                "KNOWLEDGE BASE",
                "WORLD MODEL",
                "BAYESIAN ENGINE",
                "PATTERN ANALYZER",
            ],
        }
        
        # Cache for assembled contexts
        self._context_cache: Dict[str, Tuple[str, datetime]] = {}
        self._cache_ttl = 5  # seconds
        
        logger.info("ContextAggregator initialized")
    
    def get_context(
        self,
        brain,
        context_type: ContextType = ContextType.FULL,
        query: Optional[str] = None,
        max_tokens: Optional[int] = None,
        include_sections: Optional[List[str]] = None,
        exclude_sections: Optional[List[str]] = None,
    ) -> str:
        """
        Get context appropriate for the task.
        
        Args:
            brain: NexusBrain instance
            context_type: Type of context to build
            query: Optional query for relevance scoring
            max_tokens: Override default token budget
            include_sections: Specific sections to include
            exclude_sections: Sections to exclude
            
        Returns:
            Formatted context string
        """
        # Check cache
        cache_key = f"{context_type.value}_{query}_{max_tokens}"
        if cache_key in self._context_cache:
            cached, timestamp = self._context_cache[cache_key]
            if (datetime.now() - timestamp).total_seconds() < self._cache_ttl:
                return cached
        
        # Get full context from the appropriate collector
        try:
            from config import NEXUS_CONFIG
            from llm.groq_interface import groq_interface
            use_groq = (
                hasattr(NEXUS_CONFIG, 'groq') and
                NEXUS_CONFIG.groq.enabled and
                groq_interface.is_connected
            )
        except Exception:
            use_groq = False

        if use_groq:
            full_context = groq_context_collector.collect_all(brain)
        else:
            full_context = ollama_context_collector.collect_all(brain)
        
        # Parse into sections
        sections = self._parse_sections(full_context)
        
        # Determine token budget
        budget = max_tokens or self._token_budgets.get(context_type, 2000)
        
        # Filter and prioritize sections
        if include_sections:
            sections = [s for s in sections if any(
                inc.lower() in s.name.lower() for inc in include_sections
            )]
        
        if exclude_sections:
            sections = [s for s in sections if not any(
                exc.lower() in s.name.lower() for exc in exclude_sections
            )]
        
        # Score and rank sections
        sections = self._rank_sections(sections, context_type, query)
        
        # Assemble within budget
        context = self._assemble_within_budget(sections, budget)
        
        # Cache result
        self._context_cache[cache_key] = (context, datetime.now())
        
        return context
    
    def _parse_sections(self, full_context: str) -> List[ContextSection]:
        """Parse full context into individual sections."""
        sections = []
        
        # Split by section headers [SECTION NAME]
        pattern = r'\[([^\]]+)\]'
        parts = re.split(pattern, full_context)
        
        # First part is the header (before any sections)
        current_name = "HEADER"
        current_content = ""
        
        for i, part in enumerate(parts):
            if i % 2 == 0:  # Content
                current_content = part.strip()
                if current_content and current_name != "HEADER":
                    section = ContextSection(
                        name=current_name,
                        content=current_content,
                        source="groq_context_collector",
                    )
                    sections.append(section)
            else:  # Section name
                current_name = part.strip()
        
        # Add remaining content
        if current_content and current_name != "HEADER":
            sections.append(ContextSection(
                name=current_name,
                content=current_content,
                source="groq_context_collector",
            ))
        
        return sections
    
    def _rank_sections(
        self,
        sections: List[ContextSection],
        context_type: ContextType,
        query: Optional[str] = None,
    ) -> List[ContextSection]:
        """Rank sections by priority and relevance."""
        priority_names = self._priority_sections.get(context_type, [])
        
        # Calculate priority for each section
        for section in sections:
            # Base priority from context type
            for i, name in enumerate(priority_names):
                if name.lower() in section.name.lower():
                    section.priority = 10 - i
                    break
            else:
                section.priority = 5  # Default priority
            
            # Boost relevance if query matches
            if query:
                query_terms = set(query.lower().split())
                content_terms = set(section.content.lower().split())
                overlap = len(query_terms & content_terms)
                section.priority += min(overlap, 3)  # Cap boost at 3
        
        # Sort by priority (descending)
        sections.sort(key=lambda s: s.priority, reverse=True)
        
        return sections
    
    def _assemble_within_budget(
        self,
        sections: List[ContextSection],
        token_budget: int,
    ) -> str:
        """Assemble context sections within token budget."""
        assembled = []
        tokens_used = 0
        
        for section in sections:
            if tokens_used + section.token_estimate <= token_budget:
                assembled.append(f"[{section.name}]\n{section.content}")
                tokens_used += section.token_estimate
            elif tokens_used < token_budget:
                # Try to fit truncated version
                remaining_tokens = token_budget - tokens_used
                remaining_chars = remaining_tokens * 4 - 50  # Leave room for header
                
                if remaining_chars > 100:  # Only if meaningful content fits
                    truncated = section.content[:remaining_chars] + "..."
                    assembled.append(f"[{section.name}]\n{truncated}")
                    tokens_used = token_budget
                    break
        
        return "\n\n".join(assembled)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # SPECIALIZED CONTEXT BUILDERS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_conversation_context(self, brain, query: str = "") -> str:
        """Get context optimized for conversation."""
        return self.get_context(
            brain,
            ContextType.CONVERSATION,
            query=query,
        )
    
    def get_reasoning_context(self, brain, query: str = "") -> str:
        """Get context optimized for reasoning tasks."""
        return self.get_context(
            brain,
            ContextType.REASONING,
            query=query,
        )
    
    def get_self_reflection_context(self, brain) -> str:
        """Get context for self-reflection and introspection."""
        return self.get_context(
            brain,
            ContextType.SELF_REFLECTION,
        )
    
    def get_task_context(self, brain, task_type: str = "") -> str:
        """Get context for task execution."""
        return self.get_context(
            brain,
            ContextType.TASK_EXECUTION,
            query=task_type,
        )
    
    def get_learning_context(self, brain, topic: str = "") -> str:
        """Get context optimized for learning."""
        return self.get_context(
            brain,
            ContextType.LEARNING,
            query=topic,
        )
    
    def get_creative_context(self, brain, prompt: str = "") -> str:
        """Get context optimized for creative tasks."""
        return self.get_context(
            brain,
            ContextType.CREATIVE,
            query=prompt,
        )
    
    def get_minimal_context(self, brain) -> str:
        """Get minimal essential context."""
        return self.get_context(
            brain,
            ContextType.MINIMAL,
        )
    
    # ═══════════════════════════════════════════════════════════════════════════
    # CONTEXT ENHANCEMENT
    # ═══════════════════════════════════════════════════════════════════════════
    
    def enhance_prompt_with_context(
        self,
        brain,
        prompt: str,
        context_type: ContextType = ContextType.CONVERSATION,
    ) -> str:
        """
        Enhance a prompt with relevant context.
        
        Args:
            brain: NexusBrain instance
            prompt: The original prompt
            context_type: Type of context to add
            
        Returns:
            Enhanced prompt with context
        """
        context = self.get_context(brain, context_type, query=prompt)
        
        if not context:
            return prompt
        
        # Build enhanced prompt
        enhanced = f"""[SYSTEM CONTEXT — Current State]
{context}

[USER REQUEST]
{prompt}"""
        
        return enhanced
    
    def get_subsystem_summary(self, brain) -> Dict[str, Any]:
        """Get a summary of all subsystems with their key stats."""
        summary = {}
        
        # Get full context from the appropriate collector
        try:
            from config import NEXUS_CONFIG
            from llm.groq_interface import groq_interface
            use_groq = (
                hasattr(NEXUS_CONFIG, 'groq') and
                NEXUS_CONFIG.groq.enabled and
                groq_interface.is_connected
            )
        except Exception:
            use_groq = False

        if use_groq:
            full_context = groq_context_collector.collect_all(brain)
        else:
            full_context = ollama_context_collector.collect_all(brain)
        sections = self._parse_sections(full_context)
        
        for section in sections:
            # Extract key-value pairs from section
            stats = {}
            lines = section.content.split('\n')
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    stats[key.strip()] = value.strip()
            
            summary[section.name] = {
                "token_estimate": section.token_estimate,
                "priority": section.priority,
                "stats": stats,
            }
        
        return summary
    
    def get_stats(self) -> Dict[str, Any]:
        """Get aggregator statistics."""
        return {
            "cache_size": len(self._context_cache),
            "context_types": [ct.value for ct in ContextType],
            "token_budgets": {ct.value: budget for ct, budget in self._token_budgets.items()},
        }
    
    def start(self):
        """Start the context aggregator (lifecycle hook for nexus_brain)."""
        self.clear_cache()
        logger.info("🔗 Context Aggregator started")

    def stop(self):
        """Stop the context aggregator."""
        self.clear_cache()
        logger.info("🔗 Context Aggregator stopped")

    def clear_cache(self):
        """Clear the context cache."""
        self._context_cache.clear()
        logger.info("Context cache cleared")

# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

context_aggregator = ContextAggregator()