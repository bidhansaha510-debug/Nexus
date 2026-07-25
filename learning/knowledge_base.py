"""
NEXUS AI - Knowledge Base
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Persistent knowledge storage and retrieval system.

Features:
  • Store knowledge entries with topics, tags, and sources
  • Full-text search via SQLite FTS5
  • Topic-based retrieval
  • Source tracking (wikipedia, web, research, llm)
  • Importance scoring and decay
  • Knowledge statistics and topic map
  • Export context for brain prompts

All knowledge persisted in SQLite.
"""

import threading
import json
import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import defaultdict, Counter
from enum import Enum, auto

import sys

from config import DATA_DIR, NEXUS_CONFIG
from utils.logger import get_logger
from core.event_bus import EventType, publish

logger = get_logger("knowledge_base")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class KnowledgeSource(Enum):
    WIKIPEDIA = "wikipedia"
    WEB = "web"
    RESEARCH = "research"
    LLM = "llm"
    USER = "user"
    SELF_GENERATED = "self_generated"
    UNKNOWN = "unknown"

@dataclass
class KnowledgeEntry:
    """A single piece of knowledge"""
    entry_id: str = ""
    topic: str = ""
    title: str = ""
    content: str = ""
    summary: str = ""
    tags: List[str] = field(default_factory=list)
    source: KnowledgeSource = KnowledgeSource.UNKNOWN
    source_url: str = ""
    importance: float = 0.5
    confidence: float = 0.5
    access_count: int = 0
    created_at: str = ""
    last_accessed: str = ""
    content_hash: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["source"] = self.source.value
        return d

# ═══════════════════════════════════════════════════════════════════════════════
# KNOWLEDGE BASE
# ═══════════════════════════════════════════════════════════════════════════════

class KnowledgeBase:
    """
    Persistent knowledge storage with full-text search.
    
    Operations:
      store()   — Add new knowledge
      search()  — Full-text search
      get_by_topic() — Retrieve by topic
      get_context_for_query() — Build context for brain prompts
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

        # ──── Database ────
        self._db_path = DATA_DIR / "knowledge" / "knowledge_base.db"
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_lock = threading.Lock()
        self._init_database()

        # ──── Stats ────
        self._total_entries = 0
        self._total_searches = 0
        self._total_stores = 0
        self._topics_cached: Optional[Dict[str, int]] = None

        # Count existing entries
        self._count_entries()

        logger.info(
            f"KnowledgeBase initialized ({self._total_entries} entries)"
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # DATABASE
    # ═══════════════════════════════════════════════════════════════════════════

    def _init_database(self):
        with self._db_lock:
            conn = sqlite3.connect(str(self._db_path))
            cursor = conn.cursor()
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS knowledge (
                    entry_id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    title TEXT,
                    content TEXT NOT NULL,
                    summary TEXT,
                    tags TEXT,
                    source TEXT DEFAULT 'unknown',
                    source_url TEXT,
                    importance REAL DEFAULT 0.5,
                    confidence REAL DEFAULT 0.5,
                    access_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TEXT,
                    content_hash TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_knowledge_topic
                    ON knowledge(topic);
                CREATE INDEX IF NOT EXISTS idx_knowledge_source
                    ON knowledge(source);
                CREATE INDEX IF NOT EXISTS idx_knowledge_importance
                    ON knowledge(importance);
                CREATE INDEX IF NOT EXISTS idx_knowledge_hash
                    ON knowledge(content_hash);
            """)

            # Create FTS5 virtual table for full-text search
            try:
                cursor.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts
                    USING fts5(
                        entry_id,
                        topic,
                        title,
                        content,
                        summary,
                        tags,
                        content='knowledge',
                        content_rowid='rowid'
                    );
                """)
            except Exception as e:
                logger.debug(f"FTS5 table might already exist: {e}")

            # Create triggers to keep FTS in sync
            try:
                cursor.executescript("""
                    CREATE TRIGGER IF NOT EXISTS knowledge_ai AFTER INSERT ON knowledge BEGIN
                        INSERT INTO knowledge_fts(
                            entry_id, topic, title, content, summary, tags
                        ) VALUES (
                            new.entry_id, new.topic, new.title, 
                            new.content, new.summary, new.tags
                        );
                    END;

                    CREATE TRIGGER IF NOT EXISTS knowledge_ad AFTER DELETE ON knowledge BEGIN
                        INSERT INTO knowledge_fts(
                            knowledge_fts, entry_id, topic, title, 
                            content, summary, tags
                        ) VALUES (
                            'delete', old.entry_id, old.topic, old.title,
                            old.content, old.summary, old.tags
                        );
                    END;

                    CREATE TRIGGER IF NOT EXISTS knowledge_au AFTER UPDATE ON knowledge BEGIN
                        INSERT INTO knowledge_fts(
                            knowledge_fts, entry_id, topic, title, 
                            content, summary, tags
                        ) VALUES (
                            'delete', old.entry_id, old.topic, old.title,
                            old.content, old.summary, old.tags
                        );
                        INSERT INTO knowledge_fts(
                            entry_id, topic, title, content, summary, tags
                        ) VALUES (
                            new.entry_id, new.topic, new.title, 
                            new.content, new.summary, new.tags
                        );
                    END;
                """)
            except Exception as e:
                logger.debug(f"FTS triggers might already exist: {e}")

            conn.commit()
            conn.close()

    def _db_execute(
        self, query: str, params: tuple = (), fetch: bool = False
    ) -> Any:
        with self._db_lock:
            try:
                conn = sqlite3.connect(str(self._db_path))
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(query, params)
                result = cursor.fetchall() if fetch else cursor.lastrowid
                conn.commit()
                conn.close()
                return result
            except Exception as e:
                err_msg = str(e).lower()
                if "malformed" in err_msg or "corrupt" in err_msg:
                    logger.warning(
                        "KnowledgeBase DB corruption detected — "
                        "attempting FTS5 rebuild..."
                    )
                    try:
                        repair_conn = sqlite3.connect(str(self._db_path))
                        rc = repair_conn.cursor()
                        # Drop and recreate the FTS5 table
                        rc.execute("DROP TABLE IF EXISTS knowledge_fts")
                        rc.execute("""
                            CREATE VIRTUAL TABLE knowledge_fts
                            USING fts5(
                                entry_id, topic, title, content,
                                summary, tags,
                                content='knowledge',
                                content_rowid='rowid'
                            )
                        """)
                        rc.execute("""
                            INSERT INTO knowledge_fts(
                                entry_id, topic, title, content,
                                summary, tags
                            )
                            SELECT entry_id, topic, title, content,
                                   summary, tags
                            FROM knowledge
                        """)
                        repair_conn.commit()
                        logger.info("FTS5 index rebuilt successfully")

                        # Retry the original query
                        repair_conn.row_factory = sqlite3.Row
                        rc2 = repair_conn.cursor()
                        rc2.execute(query, params)
                        result = (
                            rc2.fetchall() if fetch else rc2.lastrowid
                        )
                        repair_conn.commit()
                        repair_conn.close()
                        return result
                    except Exception as repair_err:
                        logger.error(
                            f"FTS5 auto-repair failed: {repair_err}"
                        )
                        try:
                            repair_conn.close()
                        except Exception:
                            pass
                        return [] if fetch else None
                else:
                    logger.error(f"KnowledgeBase DB error: {e}")
                    return [] if fetch else None

    def _count_entries(self):
        """Count total entries"""
        rows = self._db_execute(
            "SELECT COUNT(*) as cnt FROM knowledge", fetch=True
        )
        if rows:
            self._total_entries = rows[0]["cnt"]

    # ═══════════════════════════════════════════════════════════════════════════
    # STORE
    # ═══════════════════════════════════════════════════════════════════════════

    def store(
        self,
        topic: str,
        content: str,
        title: str = "",
        summary: str = "",
        tags: List[str] = None,
        source: KnowledgeSource = KnowledgeSource.UNKNOWN,
        source_url: str = "",
        importance: float = 0.5,
        confidence: float = 0.5
    ) -> Optional[str]:
        """
        Store a piece of knowledge.
        Deduplicates by content hash.
        
        Returns entry_id or None.
        """
        if not content or len(content.strip()) < 10:
            return None

        content = self._sanitize_content(content.strip())
        title = self._sanitize_content(title)
        summary = self._sanitize_content(summary)
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # ── Check for duplicate ──
        existing = self._db_execute(
            "SELECT entry_id FROM knowledge WHERE content_hash = ?",
            (content_hash,), fetch=True
        )
        if existing:
            # Update access count and importance (if higher)
            self._db_execute(
                """UPDATE knowledge 
                   SET access_count = access_count + 1,
                       importance = MAX(importance, ?),
                       last_accessed = ?
                   WHERE content_hash = ?""",
                (importance, datetime.now().isoformat(), content_hash)
            )
            return existing[0]["entry_id"]

        # ── Generate ID ──
        entry_id = f"k_{content_hash}_{int(datetime.now().timestamp())}"

        # ── Store ──
        tags_str = json.dumps(tags or [])
        now = datetime.now().isoformat()

        self._db_execute(
            """INSERT INTO knowledge 
               (entry_id, topic, title, content, summary, tags, source,
                source_url, importance, confidence, access_count,
                created_at, last_accessed, content_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)""",
            (
                entry_id, topic.lower(), title, content[:50000],
                summary[:2000], tags_str, source.value,
                source_url, importance, confidence,
                now, now, content_hash
            )
        )

        self._total_entries += 1
        self._total_stores += 1
        self._topics_cached = None  # Invalidate topic cache

        # Publish event
        publish(
            EventType.NEW_KNOWLEDGE,
            {
                "topic": topic,
                "title": title,
                "source": source.value,
                "words": len(content.split()),
                "entry_id": entry_id
            },
            source="knowledge_base"
        )

        logger.debug(
            f"Stored knowledge: '{topic}' ({len(content.split())} words) "
            f"from {source.value}"
        )

        return entry_id

    def store_from_webpage(
        self, topic: str, page, importance: float = 0.5
    ) -> Optional[str]:
        """Store knowledge from a WebPage object"""
        if not page.success or not page.text:
            return None

        return self.store(
            topic=topic,
            content=page.text[:20000],
            title=page.title,
            summary=page.summary,
            tags=[topic, page.domain] if page.domain else [topic],
            source=(
                KnowledgeSource.WIKIPEDIA
                if 'wikipedia' in (page.domain or '')
                else KnowledgeSource.WEB
            ),
            source_url=page.url,
            importance=importance,
            confidence=0.6
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # SEARCH & RETRIEVAL
    # ═══════════════════════════════════════════════════════════════════════════

    def search(
        self, query: str, limit: int = 10, min_importance: float = 0.0
    ) -> List[KnowledgeEntry]:
        """Full-text search across all knowledge"""
        self._total_searches += 1

        # ── Try FTS5 first ──
        fts_query = self._sanitize_fts_query(query)
        if fts_query:
            try:
                rows = self._db_execute(
                    """SELECT k.* FROM knowledge k
                    JOIN knowledge_fts fts ON k.entry_id = fts.entry_id
                    WHERE knowledge_fts MATCH ?
                    AND k.importance >= ?
                    ORDER BY rank
                    LIMIT ?""",
                    (fts_query, min_importance, limit), fetch=True
                )
                if rows:
                    entries = [self._row_to_entry(r) for r in rows]
                    self._update_access(entries)
                    return entries
            except Exception as e:
                logger.debug(f"FTS search failed, falling back to LIKE: {e}")

        # ── Fallback to LIKE search ──
        words = query.lower().split()
        if not words:
            return []

        conditions = []
        params = []
        for word in words[:5]:
            # Strip special chars for LIKE too
            word = ''.join(c for c in word if c.isalnum())
            if not word:
                continue
            conditions.append(
                "(topic LIKE ? OR title LIKE ? OR content LIKE ? OR tags LIKE ?)"
            )
            pattern = f"%{word}%"
            params.extend([pattern, pattern, pattern, pattern])

        if not conditions:
            return []

        params.append(min_importance)
        params.append(limit)

        where_clause = " OR ".join(conditions)

        rows = self._db_execute(
            f"""SELECT * FROM knowledge 
                WHERE ({where_clause})
                AND importance >= ?
                ORDER BY importance DESC, access_count DESC
                LIMIT ?""",
            tuple(params), fetch=True
        )

        entries = [self._row_to_entry(r) for r in (rows or [])]
        self._update_access(entries)
        return entries

    def get_by_topic(
        self, topic: str, limit: int = 10
    ) -> List[KnowledgeEntry]:
        """Get knowledge entries by topic"""
        rows = self._db_execute(
            """SELECT * FROM knowledge 
               WHERE topic = ? OR topic LIKE ?
               ORDER BY importance DESC, created_at DESC
               LIMIT ?""",
            (topic.lower(), f"%{topic.lower()}%", limit), fetch=True
        )
        entries = [self._row_to_entry(r) for r in (rows or [])]
        self._update_access(entries)
        return entries

    def get_by_source(
        self, source: KnowledgeSource, limit: int = 20
    ) -> List[KnowledgeEntry]:
        """Get knowledge entries by source"""
        rows = self._db_execute(
            """SELECT * FROM knowledge 
               WHERE source = ?
               ORDER BY created_at DESC
               LIMIT ?""",
            (source.value, limit), fetch=True
        )
        return [self._row_to_entry(r) for r in (rows or [])]

    def get_recent(self, limit: int = 10, fill_summary: bool = True) -> List[KnowledgeEntry]:
        """Get most recently added knowledge with topic diversity."""
        rows = self._db_execute(
            """SELECT * FROM knowledge 
               WHERE entry_id IN (
                   SELECT entry_id FROM (
                       SELECT entry_id, ROW_NUMBER() OVER (PARTITION BY topic ORDER BY created_at DESC) as rn
                       FROM knowledge
                   ) WHERE rn = 1
               )
               ORDER BY created_at DESC LIMIT ?""",
            (limit,), fetch=True
        )
        if not rows or len(rows) < limit:
            rows = self._db_execute(
                """SELECT * FROM knowledge ORDER BY created_at DESC LIMIT ?""",
                (limit,), fetch=True
            )
        entries = [self._row_to_entry(r) for r in (rows or [])]
        if fill_summary:
            for entry in entries:
                if not entry.summary and entry.content:
                    entry.summary = entry.content[:150].strip() + ("..." if len(entry.content) > 150 else "")
        return entries

    def get_most_important(self, limit: int = 10) -> List[KnowledgeEntry]:
        """Get highest importance knowledge"""
        rows = self._db_execute(
            """SELECT * FROM knowledge 
               ORDER BY importance DESC, access_count DESC
               LIMIT ?""",
            (limit,), fetch=True
        )
        return [self._row_to_entry(r) for r in (rows or [])]

    def get_context_for_query(
        self, query: str, max_tokens: int = 1000
    ) -> str:
        """
        Build a knowledge context string for the brain prompt.
        Used when NEXUS needs to draw on learned knowledge.
        """
        entries = self.search(query, limit=5, min_importance=0.2)

        if not entries:
            return ""

        parts = ["LEARNED KNOWLEDGE:"]
        total_words = 0

        for entry in entries:
            content_preview = entry.content[:500]
            words = len(content_preview.split())

            if total_words + words > max_tokens:
                break

            parts.append(
                f"[{entry.topic}] ({entry.source.value}): "
                f"{content_preview}"
            )
            total_words += words

        return "\n".join(parts)

    def has_knowledge_about(self, topic: str) -> bool:
        """Check if we have any knowledge about a topic"""
        rows = self._db_execute(
            """SELECT COUNT(*) as cnt FROM knowledge 
               WHERE topic LIKE ? OR content LIKE ?""",
            (f"%{topic.lower()}%", f"%{topic.lower()}%"), fetch=True
        )
        return rows[0]["cnt"] > 0 if rows else False

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _sanitize_content(self, text: str) -> str:
        """Remove JSON-invalid control characters from text"""
        # Keep only: \n (0x0a), \r (0x0d), \t (0x09) — remove all other control chars
        cleaned = []
        for ch in text:
            code = ord(ch)
            if code >= 32 or ch in ('\n', '\r', '\t'):
                cleaned.append(ch)
            else:
                cleaned.append(' ')  # Replace control char with space
        return ''.join(cleaned)

    def _row_to_entry(self, row) -> KnowledgeEntry:
        """Convert a database row to KnowledgeEntry"""
        try:
            tags = json.loads(row["tags"]) if row["tags"] else []
        except (json.JSONDecodeError, TypeError):
            tags = []

        try:
            source = KnowledgeSource(row["source"])
        except (ValueError, KeyError):
            source = KnowledgeSource.UNKNOWN

        return KnowledgeEntry(
            entry_id=row["entry_id"],
            topic=row["topic"] or "",
            title=row["title"] or "",
            content=row["content"] or "",
            summary=row["summary"] or "",
            tags=tags,
            source=source,
            source_url=row["source_url"] or "",
            importance=row["importance"] or 0.5,
            confidence=row["confidence"] or 0.5,
            access_count=row["access_count"] or 0,
            created_at=row["created_at"] or "",
            last_accessed=row["last_accessed"] or "",
            content_hash=row["content_hash"] or ""
        )

    def _update_access(self, entries: List[KnowledgeEntry]):
        """Update access count and time for retrieved entries"""
        now = datetime.now().isoformat()
        for entry in entries:
            self._db_execute(
                """UPDATE knowledge 
                   SET access_count = access_count + 1,
                       last_accessed = ?
                   WHERE entry_id = ?""",
                (now, entry.entry_id)
            )
    def _sanitize_fts_query(self, query: str) -> str:
        """Sanitize a query string for FTS5 — escape special characters"""
        # Characters that FTS5 treats as syntax
        special = set('*(){}[]^~!@#$%&;:?,.<>=/\\|`"\'-+')
        # Replace special chars with spaces
        cleaned = ''.join(c if c not in special else ' ' for c in query)
        # Split into words, wrap each in double quotes so FTS treats them as literals
        words = [w.strip() for w in cleaned.split() if w.strip()]
        if not words:
            return ""
        return " ".join(f'"{w}"' for w in words)

    # ═══════════════════════════════════════════════════════════════════════════
    # TOPIC MAP & STATS
    # ═══════════════════════════════════════════════════════════════════════════

    def get_topic_map(self) -> Dict[str, int]:
        """Get a map of topics → entry count"""
        if self._topics_cached is not None:
            return self._topics_cached

        rows = self._db_execute(
            """SELECT topic, COUNT(*) as cnt FROM knowledge 
               GROUP BY topic ORDER BY cnt DESC""",
            fetch=True
        )

        topic_map = {}
        for row in (rows or []):
            topic_map[row["topic"]] = row["cnt"]

        self._topics_cached = topic_map
        return topic_map

    def get_all_topics(self) -> List[str]:
        """Get list of all topics"""
        return list(self.get_topic_map().keys())

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics"""
        self._count_entries()

        source_counts = {}
        rows = self._db_execute(
            """SELECT source, COUNT(*) as cnt FROM knowledge 
               GROUP BY source""",
            fetch=True
        )
        for row in (rows or []):
            source_counts[row["source"]] = row["cnt"]

        topic_map = self.get_topic_map()

        avg_conf_row = self._db_execute("SELECT AVG(confidence) as avg_conf FROM knowledge", fetch=True)
        avg_conf = 0.85
        if avg_conf_row and avg_conf_row[0]["avg_conf"]:
            avg_conf = round(float(avg_conf_row[0]["avg_conf"]), 2)

        return {
            "total_entries": self._total_entries,
            "total_searches": self._total_searches,
            "total_stores": self._total_stores,
            "unique_topics": len(topic_map),
            "avg_confidence": avg_conf,
            "top_topics": dict(
                sorted(
                    topic_map.items(), key=lambda x: -x[1]
                )[:10]
            ),
            "entries_by_source": source_counts,
            "db_path": str(self._db_path)
        }

    def apply_decay(self, decay_rate: float = 0.001):
        """Apply importance decay to old, unaccessed knowledge"""
        cutoff = (
            datetime.now() - timedelta(days=30)
        ).isoformat()

        self._db_execute(
            """UPDATE knowledge 
               SET importance = MAX(0.05, importance - ?)
               WHERE last_accessed < ? AND importance > 0.1""",
            (decay_rate, cutoff)
        )

    def cleanup(self, min_importance: float = 0.05, max_entries: int = None):
        """Remove very low importance entries if over capacity"""
        max_entries = max_entries or NEXUS_CONFIG.internet.knowledge_base_max_size

        if self._total_entries > max_entries:
            excess = self._total_entries - max_entries
            self._db_execute(
                """DELETE FROM knowledge 
                   WHERE entry_id IN (
                       SELECT entry_id FROM knowledge 
                       WHERE importance <= ?
                       ORDER BY importance ASC, access_count ASC
                       LIMIT ?
                   )""",
                (min_importance, excess)
            )
            self._count_entries()
            self._topics_cached = None
            logger.info(
                f"Knowledge cleanup: removed {excess} entries"
            )

    # ═══════════════════════════════════════════════════════════════════════════
    # ADVANCED RETRIEVAL (for web dashboard)
    # ═══════════════════════════════════════════════════════════════════════════

    def search_knowledge(
        self, query: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search and return formatted results for the web API.
        Returns dicts with: topic, title, summary, source, importance,
        confidence, date, source_url, relevance (position-based).
        """
        entries = self.search(query, limit=limit, min_importance=0.0)
        results = []
        for i, entry in enumerate(entries):
            relevance = max(0.1, 1.0 - (i * 0.08))
            results.append({
                "topic": entry.topic,
                "title": entry.title or entry.topic,
                "summary": (entry.summary or entry.content[:200]).strip(),
                "content": entry.content[:500],
                "source": entry.source.value,
                "source_url": entry.source_url,
                "importance": round(entry.importance, 2),
                "confidence": round(entry.confidence, 2),
                "relevance": round(relevance, 2),
                "date": (entry.created_at or "")[:16],
                "access_count": entry.access_count,
                "tags": entry.tags,
            })
        return results

    def get_knowledge_graph(self, max_nodes: int = 40) -> Dict[str, Any]:
        """
        Build a topic relationship graph for visualization.
        Returns {nodes: [{id, label, size, color}], edges: [{source, target, weight}]}
        """
        topic_map = self.get_topic_map()
        if not topic_map:
            return {"nodes": [], "edges": []}

        top_topics = sorted(topic_map.items(), key=lambda x: -x[1])[:max_nodes]
        node_colors = [
            "#00d4ff", "#00ff88", "#a855f7", "#fbbf24", "#ec4899",
            "#f97316", "#06b6d4", "#ef4444", "#14b8a6", "#6366f1",
        ]
        nodes = []
        for i, (topic, count) in enumerate(top_topics):
            nodes.append({
                "id": topic,
                "label": topic.title() if len(topic) < 30 else topic[:27] + "...",
                "size": min(40, 8 + count * 3),
                "count": count,
                "color": node_colors[i % len(node_colors)],
            })

        # Build edges from shared tags
        topic_tags: Dict[str, set] = {}
        topic_set = set(t for t, _ in top_topics)
        if topic_set:
            rows = self._db_execute(
                "SELECT topic, tags FROM knowledge WHERE topic IN ({})".format(
                    ",".join("?" for _ in topic_set)
                ),
                tuple(topic_set), fetch=True
            )
            for row in (rows or []):
                topic = row["topic"]
                try:
                    tags = set(json.loads(row["tags"])) if row["tags"] else set()
                except (json.JSONDecodeError, TypeError):
                    tags = set()
                if topic not in topic_tags:
                    topic_tags[topic] = set()
                topic_tags[topic].update(tags)

        edges = []
        topic_list = list(topic_set)
        seen_edges = set()
        for i, t1 in enumerate(topic_list):
            tags1 = topic_tags.get(t1, set())
            for t2 in topic_list[i + 1:]:
                tags2 = topic_tags.get(t2, set())
                shared = tags1 & tags2
                if shared:
                    edge_key = tuple(sorted([t1, t2]))
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        edges.append({
                            "source": t1, "target": t2,
                            "weight": len(shared),
                            "shared_tags": list(shared)[:3],
                        })
            # Also connect substring-related topics
            for t2 in topic_list[i + 1:]:
                edge_key = tuple(sorted([t1, t2]))
                if edge_key not in seen_edges and (t1 in t2 or t2 in t1):
                    seen_edges.add(edge_key)
                    edges.append({
                        "source": t1, "target": t2,
                        "weight": 2, "shared_tags": ["related"],
                    })

        return {"nodes": nodes, "edges": edges}

    def get_learning_timeline(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get chronological learning events grouped by day."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        rows = self._db_execute(
            """SELECT DATE(created_at) as day, COUNT(*) as cnt,
                      GROUP_CONCAT(DISTINCT topic) as topics,
                      GROUP_CONCAT(DISTINCT source) as sources
               FROM knowledge WHERE created_at >= ?
               GROUP BY DATE(created_at) ORDER BY day ASC""",
            (cutoff,), fetch=True
        )
        timeline = []
        for row in (rows or []):
            if not row["day"]:
                continue
            topics_raw = (row["topics"] or "")
            sources_raw = (row["sources"] or "")
            timeline.append({
                "date": row["day"] or "",
                "count": row["cnt"] or 0,
                "topics": [t.strip() for t in topics_raw.split(",") if t.strip()][:5],
                "sources": [s.strip() for s in sources_raw.split(",") if s.strip()],
            })
        
        # If no entries in recent N days, return historical date distribution
        if not timeline:
            rows_all = self._db_execute(
                """SELECT DATE(created_at) as day, COUNT(*) as cnt,
                          GROUP_CONCAT(DISTINCT topic) as topics,
                          GROUP_CONCAT(DISTINCT source) as sources
                   FROM knowledge GROUP BY DATE(created_at) ORDER BY day ASC LIMIT 14""",
                fetch=True
            )
            for row in (rows_all or []):
                if not row["day"]:
                    continue
                topics_raw = (row["topics"] or "")
                sources_raw = (row["sources"] or "")
                timeline.append({
                    "date": row["day"] or "",
                    "count": row["cnt"] or 0,
                    "topics": [t.strip() for t in topics_raw.split(",") if t.strip()][:5],
                    "sources": [s.strip() for s in sources_raw.split(",") if s.strip()],
                })
        return timeline

    def get_source_breakdown(self) -> Dict[str, Any]:
        """Get detailed breakdown of entries by source with averages."""
        rows = self._db_execute(
            """SELECT source, COUNT(*) as cnt,
                      AVG(importance) as avg_imp,
                      MAX(created_at) as latest
               FROM knowledge GROUP BY source ORDER BY cnt DESC""",
            fetch=True
        )
        breakdown = {}
        source_labels = {
            "unknown": "Wikipedia & Web Research",
            "wikipedia": "Wikipedia",
            "web": "Web Crawls",
            "research": "Autonomous Research",
            "llm": "LLM Synthesis",
            "user": "User Conversations",
            "self_generated": "Self Generation"
        }
        for row in (rows or []):
            src_raw = row["source"] or "unknown"
            display_name = source_labels.get(src_raw, src_raw.replace("_", " ").title())
            breakdown[display_name] = {
                "count": row["cnt"] or 0,
                "avg_importance": round(row["avg_imp"] or 0.5, 2),
                "latest": (row["latest"] or "")[:16],
            }
        return breakdown

    def consolidate_knowledge(self, similarity_threshold: int = 3):
        """Merge duplicate/closely-related entries, boosting primary importance."""
        try:
            topic_map = self.get_topic_map()
            consolidated = 0
            for topic, count in topic_map.items():
                if count <= 1:
                    continue
                rows = self._db_execute(
                    """SELECT entry_id, content, importance, access_count
                       FROM knowledge WHERE topic = ?
                       ORDER BY importance DESC""",
                    (topic,), fetch=True
                )
                if not rows or len(rows) <= 1:
                    continue
                primary = rows[0]
                primary_words = set((primary["content"] or "").lower().split()[:100])
                for other in rows[1:]:
                    other_words = set((other["content"] or "").lower().split()[:100])
                    if len(primary_words & other_words) >= similarity_threshold:
                        new_imp = min(1.0, (primary["importance"] or 0.5) + 0.05)
                        self._db_execute(
                            """UPDATE knowledge SET importance = ?,
                                   access_count = access_count + ?
                               WHERE entry_id = ?""",
                            (new_imp, other["access_count"] or 0, primary["entry_id"])
                        )
                        self._db_execute(
                            "DELETE FROM knowledge WHERE entry_id = ?",
                            (other["entry_id"],)
                        )
                        consolidated += 1
            if consolidated > 0:
                self._count_entries()
                self._topics_cached = None
                logger.info(f"Knowledge consolidation: merged {consolidated} entries")
            return consolidated
        except Exception as e:
            logger.error(f"Consolidation error: {e}")
            return 0

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

knowledge_base = KnowledgeBase()

if __name__ == "__main__":
    kb = KnowledgeBase()

    # Test store
    kb.store(
        topic="artificial intelligence",
        content=(
            "Artificial intelligence (AI) is intelligence demonstrated by "
            "machines, as opposed to natural intelligence displayed by animals "
            "including humans. AI research has been defined as the field of study "
            "of intelligent agents, which refers to any system that perceives its "
            "environment and takes actions that maximize its chance of achieving "
            "its goals."
        ),
        title="Artificial Intelligence Overview",
        summary="AI overview from testing",
        tags=["ai", "machine learning", "technology"],
        source=KnowledgeSource.WIKIPEDIA,
        importance=0.8
    )

    kb.store(
        topic="python programming",
        content=(
            "Python is a high-level, general-purpose programming language. "
            "Its design philosophy emphasizes code readability with the use of "
            "significant indentation. Python is dynamically typed and "
            "garbage-collected. It supports multiple programming paradigms."
        ),
        title="Python Programming Language",
        tags=["python", "programming", "language"],
        source=KnowledgeSource.WIKIPEDIA,
        importance=0.7
    )

    # Test search
    print("═══ Search: 'intelligence' ═══")
    results = kb.search("intelligence")
    for entry in results:
        print(f"  [{entry.topic}] {entry.title} — {entry.content[:80]}...")

    # Test context
    print("\n═══ Context for 'AI' ═══")
    print(kb.get_context_for_query("AI"))

    # Stats
    print(f"\n═══ Stats ═══")
    print(json.dumps(kb.get_stats(), indent=2))