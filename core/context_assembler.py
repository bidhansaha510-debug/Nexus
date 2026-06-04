"""
NEXUS AI — Context Assembler
Unified RAG pipeline — assembles context from memory, knowledge,
conversation, world model, and cognition engines.
"""
import sys, time, threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.logger import get_logger
from config import NEXUS_CONFIG

logger = get_logger("context_assembler")

@dataclass
class ContextChunk:
    source: str       # memory, knowledge, conversation, world_model, cognition
    content: str
    relevance: float  # 0.0 - 1.0
    token_estimate: int
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AssembledContext:
    chunks: List[ContextChunk] = field(default_factory=list)
    total_tokens: int = 0
    sources_used: List[str] = field(default_factory=list)
    elapsed: float = 0.0

    def to_string(self) -> str:
        if not self.chunks:
            return ""
        sections: Dict[str, List[str]] = {}
        for c in self.chunks:
            sections.setdefault(c.source, []).append(c.content)
        headers = {"memory": "RELEVANT MEMORIES", "knowledge": "KNOWLEDGE BASE",
                   "conversation": "RECENT CONVERSATION", "world_model": "USER PATTERNS",
                   "cognition": "COGNITIVE INSIGHTS"}
        parts = []
        for src, items in sections.items():
            parts.append(f"[{headers.get(src, src.upper())}]")
            for it in items:
                parts.append(f"  • {it}")
            parts.append("")
        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        return {"total_tokens": self.total_tokens, "sources_used": self.sources_used,
                "chunk_count": len(self.chunks), "elapsed": round(self.elapsed, 3)}

class ContextAssembler:
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
        self._token_budget = NEXUS_CONFIG.agentic.context_token_budget
        self._parallel = NEXUS_CONFIG.agentic.context_sources_parallel
        logger.info(f"ContextAssembler initialized (budget: {self._token_budget} tokens)")

    def assemble(self, query: str, token_budget: int = None,
                 include_sources: List[str] = None,
                 conversation_history: List[Dict[str, str]] = None) -> AssembledContext:
        budget = token_budget or self._token_budget
        start = time.time()
        sources = include_sources or ["memory", "knowledge", "conversation", "world_model", "cognition"]
        retrievers = {
            "memory": lambda: self._retrieve_memories(query),
            "knowledge": lambda: self._retrieve_knowledge(query),
            "conversation": lambda: self._retrieve_conversation(conversation_history),
            "world_model": lambda: self._retrieve_world_model(query),
            "cognition": lambda: self._retrieve_cognition(query),
        }
        all_chunks: List[ContextChunk] = []
        if self._parallel:
            with ThreadPoolExecutor(max_workers=5) as ex:
                futs = {ex.submit(retrievers[s]): s for s in sources if s in retrievers}
                for f in as_completed(futs, timeout=10):
                    try:
                        all_chunks.extend(f.result())
                    except Exception as e:
                        logger.warning(f"Source {futs[f]} failed: {e}")
        else:
            for s in sources:
                if s in retrievers:
                    try:
                        all_chunks.extend(retrievers[s]())
                    except Exception as e:
                        logger.warning(f"Source {s} failed: {e}")
        ranked = self._rank_and_deduplicate(all_chunks)
        final = self._fit_to_budget(ranked, budget)
        total_tokens = sum(c.token_estimate for c in final)
        result = AssembledContext(chunks=final, total_tokens=total_tokens,
                                  sources_used=list(set(c.source for c in final)),
                                  elapsed=time.time() - start)
        logger.info(f"Context: {len(final)} chunks, {total_tokens} tok, {result.elapsed:.2f}s")
        return result

    def _retrieve_memories(self, query: str, limit: int = 8) -> List[ContextChunk]:
        chunks = []
        try:
            from core.memory_system import memory_system
            results = memory_system.search(query, limit=limit)
            if results and isinstance(results, list):
                for i, r in enumerate(results):
                    text = str(r.get("content", r)) if isinstance(r, dict) else str(r)
                    rel = r.get("score", 0.8 - i*0.05) if isinstance(r, dict) else 0.8 - i*0.05
                    chunks.append(ContextChunk("memory", text[:500], float(rel), len(text[:500])//4))
        except Exception as e:
            logger.debug(f"Memory retrieval: {e}")
        return chunks

    def _retrieve_knowledge(self, query: str, limit: int = 5) -> List[ContextChunk]:
        chunks = []
        try:
            from learning import learning_system
            results = learning_system.search_knowledge(query, limit=limit)
            if results and isinstance(results, list):
                for i, r in enumerate(results):
                    text = str(r.get("content", r)) if isinstance(r, dict) else str(r)
                    chunks.append(ContextChunk("knowledge", text[:500], 0.75 - i*0.05, len(text[:500])//4))
        except Exception as e:
            logger.debug(f"Knowledge retrieval: {e}")
        return chunks

    def _retrieve_conversation(self, history: List[Dict[str, str]] = None) -> List[ContextChunk]:
        chunks = []
        if not history:
            return chunks
        recent = history[-10:]
        for i, turn in enumerate(recent):
            content = turn.get("content", "")
            if content:
                text = f"{turn.get('role','user')}: {content[:300]}"
                chunks.append(ContextChunk("conversation", text,
                              0.6 + (i/len(recent))*0.3, len(text)//4))
        return chunks

    def _retrieve_world_model(self, query: str) -> List[ContextChunk]:
        chunks = []
        try:
            from cognition.world_model import world_model
            if world_model and hasattr(world_model, 'get_user_predictions'):
                preds = world_model.get_user_predictions(query)
                if preds:
                    text = str(preds)[:400]
                    chunks.append(ContextChunk("world_model", text, 0.65, len(text)//4))
        except Exception as e:
            logger.debug(f"World model: {e}")
        return chunks

    def _retrieve_cognition(self, query: str) -> List[ContextChunk]:
        chunks = []
        try:
            from cognition.cognitive_router import cognitive_router
            if cognitive_router:
                insights = cognitive_router.route(query, depth="shallow")
                if insights and hasattr(insights, 'results'):
                    for r in insights.results:
                        if r.success and r.insight:
                            text = f"[{r.engine_name}] {r.insight[:300]}"
                            chunks.append(ContextChunk("cognition", text, r.confidence, len(text)//4))
        except Exception as e:
            logger.debug(f"Cognition: {e}")
        return chunks

    def _rank_and_deduplicate(self, chunks: List[ContextChunk]) -> List[ContextChunk]:
        sorted_c = sorted(chunks, key=lambda c: c.relevance, reverse=True)
        seen, unique = [], []
        for c in sorted_c:
            low = c.content.lower().strip()
            if not any(low[:50] == s[:50] for s in seen if len(low) > 20 and len(s) > 20):
                unique.append(c)
                seen.append(low)
        return unique

    def _fit_to_budget(self, ranked: List[ContextChunk], budget: int) -> List[ContextChunk]:
        selected, used = [], 0
        sources_seen: set = set()
        # First pass: one chunk per source
        for c in ranked:
            if c.source not in sources_seen and used + c.token_estimate <= budget:
                selected.append(c); used += c.token_estimate; sources_seen.add(c.source)
        # Second pass: fill remaining budget
        for c in ranked:
            if c not in selected and used + c.token_estimate <= budget:
                selected.append(c); used += c.token_estimate
        return selected

    def get_stats(self) -> Dict[str, Any]:
        return {"token_budget": self._token_budget, "parallel": self._parallel}

context_assembler = ContextAssembler()
