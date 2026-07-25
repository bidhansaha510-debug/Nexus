"""
NEXUS AI - Improvement Analytics
═══════════════════════════════════════════════════════════════════════════════
Analytics system for tracking and analyzing self-improvement effectiveness.

Features:
  • Proposal tracking and success rate analysis
  • Pattern identification in improvements
  • A/B testing framework for changes
  • User satisfaction correlation
  • Recommendation engine for future improvements
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
from collections import defaultdict
import random

import sys

from config import DATA_DIR
from utils.logger import get_logger
from core.event_bus import EventType, event_bus, publish

logger = get_logger("improvement_analytics")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ProposalRecord:
    """Record of a feature/fix proposal"""
    id: str = ""
    name: str = ""
    description: str = ""
    category: str = "feature"  # feature, fix, optimization, refactor
    priority: str = "medium"  # low, medium, high, critical
    status: str = "proposed"  # proposed, approved, implemented, tested, completed, failed
    created_at: str = ""
    approved_at: str = ""
    implemented_at: str = ""
    completed_at: str = ""
    implementer: str = "self"  # self, human
    lines_changed: int = 0
    files_changed: int = 0
    tests_passed: bool = False
    user_satisfaction: Optional[float] = None  # 0.0 to 1.0
    rollback_needed: bool = False
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class PatternRecord:
    """Identified pattern in improvements"""
    pattern_type: str = ""
    description: str = ""
    occurrence_count: int = 0
    success_rate: float = 0.0
    last_seen: str = ""
    examples: List[str] = field(default_factory=list)

@dataclass
class ABTest:
    """A/B test for comparing changes"""
    id: str = ""
    name: str = ""
    description: str = ""
    variant_a: str = ""  # Description of variant A
    variant_b: str = ""  # Description of variant B
    active: bool = True
    started_at: str = ""
    ended_at: str = ""
    sample_size_a: int = 0
    sample_size_b: int = 0
    success_a: int = 0
    success_b: int = 0
    winner: Optional[str] = None
    confidence: float = 0.0

# ═══════════════════════════════════════════════════════════════════════════════
# IMPROVEMENT ANALYTICS ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class ImprovementAnalytics:
    """
    Analytics engine for tracking and analyzing self-improvements.
    
    Provides insights into:
    - Which types of improvements are most successful
    - Patterns in bugs and fixes
    - User satisfaction correlation
    - Recommendations for future improvements
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
        self._data_dir = DATA_DIR / "self_improvement" / "analytics"
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._proposals_file = self._data_dir / "proposals.json"
        self._patterns_file = self._data_dir / "patterns.json"
        self._ab_tests_file = self._data_dir / "ab_tests.json"

        # ──── In-memory data ────
        self._proposals: Dict[str, ProposalRecord] = {}
        self._patterns: List[PatternRecord] = []
        self._ab_tests: Dict[str, ABTest] = {}

        # ──── Stats cache ────
        self._stats_cache: Dict[str, Any] = {}
        self._last_cache_update: Optional[datetime] = None
        self._cache_ttl = 60  # seconds

        # ──── Load data ────
        self._load_data()

        # ──── Event subscriptions ────
        self._register_events()

        logger.info("📊 Improvement Analytics initialized")

    # ═══════════════════════════════════════════════════════════════════════════
    # DATA PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _load_data(self):
        """Load persisted data from disk"""
        # Load proposals
        if self._proposals_file.exists():
            try:
                with open(self._proposals_file, 'r') as f:
                    data = json.load(f)
                    for pid, pdata in data.items():
                        self._proposals[pid] = ProposalRecord(**pdata)
                logger.debug(f"Loaded {len(self._proposals)} proposals")
            except Exception as e:
                logger.warning(f"Error loading proposals: {e}")

        # Load patterns
        if self._patterns_file.exists():
            try:
                with open(self._patterns_file, 'r') as f:
                    data = json.load(f)
                    self._patterns = [PatternRecord(**p) for p in data]
                logger.debug(f"Loaded {len(self._patterns)} patterns")
            except Exception as e:
                logger.warning(f"Error loading patterns: {e}")

        # Load A/B tests
        if self._ab_tests_file.exists():
            try:
                with open(self._ab_tests_file, 'r') as f:
                    data = json.load(f)
                    for tid, tdata in data.items():
                        self._ab_tests[tid] = ABTest(**tdata)
                logger.debug(f"Loaded {len(self._ab_tests)} A/B tests")
            except Exception as e:
                logger.warning(f"Error loading A/B tests: {e}")

    def _save_data(self):
        """Save data to disk"""
        try:
            # Save proposals
            with open(self._proposals_file, 'w') as f:
                json.dump(
                    {pid: p.to_dict() for pid, p in self._proposals.items()},
                    f, indent=2, default=str
                )

            # Save patterns
            with open(self._patterns_file, 'w') as f:
                json.dump([asdict(p) for p in self._patterns], f, indent=2, default=str)

            # Save A/B tests
            with open(self._ab_tests_file, 'w') as f:
                json.dump(
                    {tid: asdict(t) for tid, t in self._ab_tests.items()},
                    f, indent=2, default=str
                )
        except Exception as e:
            logger.error(f"Error saving analytics data: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT HANDLING
    # ═══════════════════════════════════════════════════════════════════════════

    def _register_events(self):
        """Subscribe to relevant events"""
        try:
            event_bus.subscribe(EventType.SELF_IMPROVEMENT_ACTION, self._on_improvement_event)
        except Exception:
            pass

    def _on_improvement_event(self, event):
        """Handle self-improvement events"""
        action = event.data.get("action", "")

        if action == "proposal_created":
            self._track_proposal(event.data)
        elif action == "proposal_approved":
            self._update_proposal_status(event.data.get("proposal_id"), "approved")
        elif action == "evolution_complete":
            self._update_proposal_status(
                event.data.get("proposal_id"), "completed",
                lines=event.data.get("lines_added", 0),
                files=event.data.get("files_created", 0)
            )
        elif action == "evolution_failed":
            self._update_proposal_status(event.data.get("proposal_id"), "failed")
        elif action == "rollback":
            self._mark_rollback(event.data.get("proposal_id"))

    # ═══════════════════════════════════════════════════════════════════════════
    # PROPOSAL TRACKING
    # ═══════════════════════════════════════════════════════════════════════════

    def _track_proposal(self, data: Dict[str, Any]):
        """Track a new proposal"""
        pid = data.get("proposal_id", data.get("id", self._generate_id()))
        name = data.get("name", data.get("title", "Unknown"))
        description = data.get("description", "")

        proposal = ProposalRecord(
            id=pid,
            name=name,
            description=description,
            category=data.get("category", "feature"),
            priority=data.get("priority", "medium"),
            created_at=datetime.now().isoformat(),
            tags=data.get("tags", []),
        )

        self._proposals[pid] = proposal
        self._save_data()
        self._invalidate_cache()

        logger.debug(f"Tracked new proposal: {name}")

    def _update_proposal_status(self, proposal_id: str, status: str, **kwargs):
        """Update proposal status"""
        if proposal_id not in self._proposals:
            # Create a minimal record
            self._proposals[proposal_id] = ProposalRecord(
                id=proposal_id,
                name=kwargs.get("name", "Unknown"),
                created_at=datetime.now().isoformat(),
            )

        proposal = self._proposals[proposal_id]
        proposal.status = status

        if status == "approved":
            proposal.approved_at = datetime.now().isoformat()
        elif status == "completed":
            proposal.completed_at = datetime.now().isoformat()
            proposal.lines_changed = kwargs.get("lines", 0)
            proposal.files_changed = kwargs.get("files", 0)

        for key, value in kwargs.items():
            if hasattr(proposal, key):
                setattr(proposal, key, value)

        self._save_data()
        self._invalidate_cache()

    def _mark_rollback(self, proposal_id: str):
        """Mark a proposal as rolled back"""
        if proposal_id in self._proposals:
            self._proposals[proposal_id].rollback_needed = True
            self._proposals[proposal_id].status = "rolled_back"
            self._save_data()
            self._invalidate_cache()

    def _generate_id(self) -> str:
        """Generate a unique ID"""
        return hashlib.md5(f"{time.time()}{random.random()}".encode()).hexdigest()[:12]

    def _invalidate_cache(self):
        """Invalidate the stats cache"""
        self._last_cache_update = None

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def get_stats(self) -> Dict[str, Any]:
        """Get analytics statistics"""
        # Check cache
        if self._last_cache_update and (datetime.now() - self._last_cache_update).total_seconds() < self._cache_ttl:
            return self._stats_cache

        # Calculate stats
        stats = {
            "total_proposals": len(self._proposals),
            "by_status": defaultdict(int),
            "by_category": defaultdict(int),
            "by_priority": defaultdict(int),
            "success_rate": 0.0,
            "avg_lines_changed": 0,
            "rollback_rate": 0.0,
            "patterns_identified": len(self._patterns),
            "ab_tests_active": sum(1 for t in self._ab_tests.values() if t.active),
        }

        completed = 0
        successful = 0
        total_lines = 0
        rollbacks = 0

        for proposal in self._proposals.values():
            stats["by_status"][proposal.status] += 1
            stats["by_category"][proposal.category] += 1
            stats["by_priority"][proposal.priority] += 1

            if proposal.status in ("completed", "failed"):
                completed += 1
                if proposal.status == "completed" and not proposal.rollback_needed:
                    successful += 1

            total_lines += proposal.lines_changed

            if proposal.rollback_needed:
                rollbacks += 1

        if completed > 0:
            stats["success_rate"] = successful / completed
            stats["rollback_rate"] = rollbacks / completed

        if len(self._proposals) > 0:
            stats["avg_lines_changed"] = total_lines / len(self._proposals)

        # Convert defaultdicts to regular dicts
        stats["by_status"] = dict(stats["by_status"])
        stats["by_category"] = dict(stats["by_category"])
        stats["by_priority"] = dict(stats["by_priority"])

        # Cache
        self._stats_cache = stats
        self._last_cache_update = datetime.now()

        return stats

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        return {
            "stats": self.get_stats(),
            "recent_proposals": [
                p.to_dict() for p in sorted(
                    self._proposals.values(),
                    key=lambda x: x.created_at,
                    reverse=True
                )[:10]
            ],
            "patterns": [asdict(p) for p in self._patterns[:10]],
            "ab_tests": [
                asdict(t) for t in self._ab_tests.values()
                if t.active
            ][:5],
            "recommendations": self.get_recommendations(),
        }

    def get_all_proposals(self, status: str = None) -> List[Dict[str, Any]]:
        """Get all proposals, optionally filtered by status"""
        proposals = list(self._proposals.values())

        if status:
            proposals = [p for p in proposals if p.status == status]

        return [p.to_dict() for p in sorted(proposals, key=lambda x: x.created_at, reverse=True)]

    def identify_patterns(self) -> List[Dict[str, Any]]:
        """Identify patterns in improvements"""
        # Clear old patterns
        self._patterns = []

        # Pattern: Categories with high success
        category_success = defaultdict(lambda: {"total": 0, "success": 0})
        for proposal in self._proposals.values():
            if proposal.status in ("completed", "failed"):
                category_success[proposal.category]["total"] += 1
                if proposal.status == "completed":
                    category_success[proposal.category]["success"] += 1

        for category, counts in category_success.items():
            if counts["total"] >= 3:
                rate = counts["success"] / counts["total"]
                self._patterns.append(PatternRecord(
                    pattern_type="category_success",
                    description=f"Category '{category}' has {rate:.0%} success rate",
                    occurrence_count=counts["total"],
                    success_rate=rate,
                    last_seen=datetime.now().isoformat(),
                ))

        # Pattern: Priority correlation
        priority_success = defaultdict(lambda: {"total": 0, "success": 0})
        for proposal in self._proposals.values():
            if proposal.status in ("completed", "failed"):
                priority_success[proposal.priority]["total"] += 1
                if proposal.status == "completed":
                    priority_success[proposal.priority]["success"] += 1

        for priority, counts in priority_success.items():
            if counts["total"] >= 3:
                rate = counts["success"] / counts["total"]
                self._patterns.append(PatternRecord(
                    pattern_type="priority_success",
                    description=f"Priority '{priority}' has {rate:.0%} success rate",
                    occurrence_count=counts["total"],
                    success_rate=rate,
                    last_seen=datetime.now().isoformat(),
                ))

        self._save_data()
        return [asdict(p) for p in self._patterns]

    def get_recommendations(self) -> List[Dict[str, Any]]:
        """Get recommendations for future improvements"""
        recommendations = []

        stats = self.get_stats()

        # Recommend based on success rates
        if stats["by_category"]:
            best_category = max(
                stats["by_category"].keys(),
                key=lambda c: stats["by_category"].get(c, 0)
            )
            recommendations.append({
                "type": "focus_category",
                "description": f"Focus on '{best_category}' improvements - most proposals",
                "confidence": 0.7,
            })

        # Recommend based on patterns
        for pattern in self._patterns:
            if pattern.success_rate > 0.7:
                recommendations.append({
                    "type": "pattern_insight",
                    "description": pattern.description,
                    "confidence": pattern.success_rate,
                })

        # Recommend A/B tests
        if stats["success_rate"] < 0.5:
            recommendations.append({
                "type": "ab_test",
                "description": "Consider A/B testing to improve success rate",
                "confidence": 0.6,
            })

        return recommendations[:5]

    def get_ab_tests(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """Get A/B tests"""
        tests = list(self._ab_tests.values())

        if active_only:
            tests = [t for t in tests if t.active]

        return [asdict(t) for t in tests]

    def create_ab_test(self, name: str, variant_a: str, variant_b: str, description: str = "") -> str:
        """Create a new A/B test"""
        test_id = self._generate_id()

        test = ABTest(
            id=test_id,
            name=name,
            description=description,
            variant_a=variant_a,
            variant_b=variant_b,
            started_at=datetime.now().isoformat(),
        )

        self._ab_tests[test_id] = test
        self._save_data()

        logger.info(f"Created A/B test: {name}")
        return test_id

    def record_ab_result(self, test_id: str, variant: str, success: bool):
        """Record a result for an A/B test"""
        if test_id not in self._ab_tests:
            return

        test = self._ab_tests[test_id]

        if variant == "a":
            test.sample_size_a += 1
            if success:
                test.success_a += 1
        elif variant == "b":
            test.sample_size_b += 1
            if success:
                test.success_b += 1

        # Check if we have a winner
        if test.sample_size_a >= 10 and test.sample_size_b >= 10:
            rate_a = test.success_a / test.sample_size_a
            rate_b = test.success_b / test.sample_size_b

            # Simple significance check
            if abs(rate_a - rate_b) > 0.2:
                test.winner = "a" if rate_a > rate_b else "b"
                test.confidence = abs(rate_a - rate_b)
                test.active = False
                test.ended_at = datetime.now().isoformat()

        self._save_data()

    def record_user_satisfaction(self, proposal_id: str, satisfaction: float):
        """Record user satisfaction for a proposal"""
        if proposal_id in self._proposals:
            self._proposals[proposal_id].user_satisfaction = satisfaction
            self._save_data()

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

improvement_analytics = ImprovementAnalytics()

if __name__ == "__main__":
    print("📊 Improvement Analytics Test\n")

    analytics = ImprovementAnalytics()

    # Test creating proposals
    print("Stats:", json.dumps(analytics.get_stats(), indent=2, default=str))

    print("\nRecommendations:", json.dumps(analytics.get_recommendations(), indent=2, default=str))

    print("\n✅ Analytics module working")
