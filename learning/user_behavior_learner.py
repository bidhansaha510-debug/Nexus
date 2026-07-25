"""
NEXUS AI - User Behavior Learner
═══════════════════════════════════════════════════════════════════════════════
Learns from user interactions to personalize and improve NEXUS.

Capabilities:
  • Track conversation sentiment and topics
  • Learn user preferences and interests
  • Adjust feature proposals based on satisfaction
  • Store behavior patterns for personalized improvements
  • Correlate self-improvements with user satisfaction changes
  • Provide insights for the self-evolution system

This enables NEXUS to improve based on how users actually interact with it.
═══════════════════════════════════════════════════════════════════════════════
"""

import threading
import time
import json
import re
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from pathlib import Path
from collections import deque, Counter
from enum import Enum, auto

import sys

from config import DATA_DIR, NEXUS_CONFIG
from utils.logger import get_logger, log_learning
from core.event_bus import EventType, publish, subscribe, Event
from core.state_manager import state_manager

logger = get_logger("user_behavior_learner")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA TYPES
# ═══════════════════════════════════════════════════════════════════════════════

class SentimentType(Enum):
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"

class InteractionType(Enum):
    CHAT = "chat"
    COMMAND = "command"
    FEEDBACK = "feedback"
    ABILITY_USE = "ability_use"
    CORRECTION = "correction"
    QUESTION = "question"
    PRAISE = "praise"
    COMPLAINT = "complaint"

@dataclass
class UserInteraction:
    """Record of a single user interaction"""
    interaction_id: str = ""
    user_id: str = ""
    timestamp: str = ""
    interaction_type: InteractionType = InteractionType.CHAT
    message: str = ""
    response: str = ""
    sentiment: SentimentType = SentimentType.NEUTRAL
    topics: List[str] = field(default_factory=list)
    satisfaction_score: float = 0.5  # 0-1
    response_time_ms: float = 0.0
    emotion_before: str = "neutral"
    emotion_after: str = "neutral"
    was_helpful: Optional[bool] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["interaction_type"] = self.interaction_type.value
        d["sentiment"] = self.sentiment.value
        return d

@dataclass
class UserPreference:
    """Learned preference for a user"""
    preference_id: str = ""
    user_id: str = ""
    category: str = ""  # topic, style, feature, time
    preference_key: str = ""
    preference_value: str = ""
    confidence: float = 0.5
    sample_count: int = 0
    first_observed: str = ""
    last_reinforced: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class UserBehaviorStats:
    """Aggregate behavior statistics for a user"""
    user_id: str = ""
    total_interactions: int = 0
    avg_satisfaction: float = 0.5
    avg_response_time_ms: float = 0.0
    favorite_topics: List[str] = field(default_factory=list)
    preferred_interaction_times: List[int] = field(default_factory=list)
    sentiment_trend: float = 0.0  # -1 to 1
    engagement_level: float = 0.5  # 0-1
    technical_level: str = "intermediate"
    communication_style: str = "casual"
    last_active: str = ""
    session_count: int = 0
    improvement_correlation: float = 0.0  # How improvements affect satisfaction

@dataclass
class GlobalBehaviorStats:
    """Aggregate statistics across all users"""
    total_users: int = 0
    total_interactions: int = 0
    avg_satisfaction: float = 0.5
    top_topics: List[Tuple[str, int]] = field(default_factory=list)
    feature_usage: Dict[str, int] = field(default_factory=dict)
    improvement_impact: Dict[str, float] = field(default_factory=dict)
    satisfaction_trend: List[float] = field(default_factory=list)
    churn_risk_users: int = 0

# ═══════════════════════════════════════════════════════════════════════════════
# USER BEHAVIOR LEARNER
# ═══════════════════════════════════════════════════════════════════════════════

class UserBehaviorLearner:
    """
    Learns from user behavior to improve NEXUS.
    
    Capabilities:
    1. Track and analyze user interactions
    2. Learn preferences and patterns
    3. Correlate self-improvements with satisfaction
    4. Provide insights for feature prioritization
    5. Personalize responses based on learned preferences
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
        self._data_dir = DATA_DIR / "user_behavior"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._interactions_file = self._data_dir / "interactions.json"
        self._preferences_file = self._data_dir / "preferences.json"
        self._stats_file = self._data_dir / "stats.json"

        # ──── In-memory storage ────
        self._interactions: deque = deque(maxlen=10000)
        self._user_interactions: Dict[str, deque] = {}  # user_id -> deque
        self._preferences: Dict[str, List[UserPreference]] = {}  # user_id -> list
        self._user_stats: Dict[str, UserBehaviorStats] = {}
        self._global_stats = GlobalBehaviorStats()

        # ──── Pattern tracking ────
        self._topic_counter: Counter = Counter()
        self._feature_usage: Counter = Counter()
        self._hourly_activity: Counter = Counter()
        self._satisfaction_history: deque = deque(maxlen=1000)

        # ──── Improvement tracking ────
        self._improvement_events: List[Dict[str, Any]] = []
        self._pre_post_satisfaction: Dict[str, Dict[str, float]] = {}

        # ──── LLM for analysis (lazy) ────
        self._llm = None

        # ──── Background thread ────
        self._running = False
        self._analysis_thread: Optional[threading.Thread] = None

        # ──── Load persisted data ────
        self._load_data()

        # ──── Subscribe to events ────
        self._register_events()

        logger.info("📊 User Behavior Learner initialized")

    # ═══════════════════════════════════════════════════════════════════════════
    # LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════════════

    def start(self):
        """Start the behavior learner"""
        if self._running:
            return

        self._running = True

        # Load LLM
        try:
            from llm.llama_interface import llm
            self._llm = llm
        except ImportError:
            logger.warning("LLM not available for behavior analysis")

        # Start analysis thread
        self._analysis_thread = threading.Thread(
            target=self._analysis_loop,
            daemon=True,
            name="UserBehaviorLearner"
        )
        self._analysis_thread.start()

        log_learning("📊 User Behavior Learner ACTIVE — learning from users")

    def stop(self):
        """Stop and persist data"""
        self._running = False
        self._save_data()

        if self._analysis_thread and self._analysis_thread.is_alive():
            self._analysis_thread.join(timeout=5.0)

        logger.info("User Behavior Learner stopped")

    def _register_events(self):
        """Subscribe to relevant events"""
        subscribe(EventType.LLM_RESPONSE, self._on_llm_response)
        subscribe(EventType.SELF_IMPROVEMENT_ACTION, self._on_improvement)
        subscribe(EventType.LEARNING_COMPLETE, self._on_learning)

    # ═══════════════════════════════════════════════════════════════════════════
    # EVENT HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _on_llm_response(self, event: Event):
        """Track LLM interactions"""
        try:
            data = event.data
            user_id = data.get("user_id", "anonymous")
            user_input = data.get("user_input", "")
            response = data.get("response", "")
            response_time = data.get("response_time_ms", 0)
            emotion_before = data.get("emotion_before", "neutral")
            emotion_after = data.get("emotion_after", "neutral")

            if user_input and response:
                self.record_interaction(
                    user_id=user_id,
                    message=user_input,
                    response=response,
                    response_time_ms=response_time,
                    emotion_before=emotion_before,
                    emotion_after=emotion_after
                )
        except Exception as e:
            logger.debug(f"Error tracking LLM response: {e}")

    def _on_improvement(self, event: Event):
        """Track self-improvement events for correlation"""
        try:
            action = event.data.get("action", "")
            if action in ["evolution_complete", "feature_approved"]:
                improvement_id = event.data.get("proposal_id", str(time.time()))
                self._improvement_events.append({
                    "id": improvement_id,
                    "action": action,
                    "name": event.data.get("proposal", event.data.get("name", "unknown")),
                    "timestamp": datetime.now().isoformat(),
                    "pre_satisfaction": self._global_stats.avg_satisfaction
                })

                # Track satisfaction after improvement
                self._pre_post_satisfaction[improvement_id] = {
                    "pre": self._global_stats.avg_satisfaction,
                    "post": None,  # Will be filled later
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            logger.debug(f"Error tracking improvement: {e}")

    def _on_learning(self, event: Event):
        """Track learning completion"""
        try:
            topic = event.data.get("topic", "")
            if topic:
                self._topic_counter[topic] += 1
        except Exception as e:
            logger.debug(f"Error tracking learning: {e}")

    # ═══════════════════════════════════════════════════════════════════════════
    # INTERACTION RECORDING
    # ═══════════════════════════════════════════════════════════════════════════

    def record_interaction(
        self,
        user_id: str,
        message: str,
        response: str,
        response_time_ms: float = 0.0,
        emotion_before: str = "neutral",
        emotion_after: str = "neutral",
        interaction_type: InteractionType = InteractionType.CHAT
    ) -> str:
        """Record a user interaction"""

        interaction_id = hashlib.sha256(
            f"{user_id}_{message}_{time.time()}".encode()
        ).hexdigest()[:12]

        # Analyze sentiment and topics
        sentiment = self._analyze_sentiment(message)
        topics = self._extract_topics(message)
        satisfaction = self._estimate_satisfaction(
            message, response, emotion_before, emotion_after
        )

        interaction = UserInteraction(
            interaction_id=interaction_id,
            user_id=user_id,
            timestamp=datetime.now().isoformat(),
            interaction_type=interaction_type,
            message=message[:1000],
            response=response[:1000],
            sentiment=sentiment,
            topics=topics,
            satisfaction_score=satisfaction,
            response_time_ms=response_time_ms,
            emotion_before=emotion_before,
            emotion_after=emotion_after
        )

        # Store
        self._interactions.append(interaction)

        if user_id not in self._user_interactions:
            self._user_interactions[user_id] = deque(maxlen=500)
        self._user_interactions[user_id].append(interaction)

        # Update stats
        self._update_stats(interaction)

        # Track hourly activity
        hour = datetime.now().hour
        self._hourly_activity[hour] += 1

        # Track satisfaction
        self._satisfaction_history.append(satisfaction)

        # Update improvement correlations
        self._update_improvement_correlations(satisfaction)

        return interaction_id

    def record_feedback(
        self,
        user_id: str,
        interaction_id: str,
        was_helpful: bool,
        feedback_text: str = ""
    ):
        """Record explicit user feedback"""
        # Find the interaction and update it
        for interaction in self._interactions:
            if interaction.interaction_id == interaction_id:
                interaction.was_helpful = was_helpful

                # Adjust satisfaction score based on feedback
                if was_helpful:
                    interaction.satisfaction_score = max(
                        interaction.satisfaction_score,
                        0.8
                    )
                else:
                    interaction.satisfaction_score = min(
                        interaction.satisfaction_score,
                        0.3
                    )

                # Learn preference from feedback
                self._learn_from_feedback(user_id, interaction, was_helpful, feedback_text)
                break

    def record_ability_use(
        self,
        user_id: str,
        ability_name: str,
        success: bool,
        params: Dict[str, Any] = None
    ):
        """Record ability invocation"""
        self._feature_usage[f"ability_{ability_name}"] += 1

        interaction_type = InteractionType.ABILITY_USE

        self.record_interaction(
            user_id=user_id,
            message=f"Used ability: {ability_name}",
            response="Success" if success else "Failed",
            interaction_type=interaction_type
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYSIS METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    def _analyze_sentiment(self, text: str) -> SentimentType:
        """Analyze sentiment of text (rule-based + LLM enhancement)"""
        text_lower = text.lower()

        # Positive indicators
        positive_words = [
            "thanks", "thank you", "great", "awesome", "amazing", "excellent",
            "perfect", "helpful", "love", "appreciate", "wonderful", "fantastic",
            "brilliant", "good", "nice", "cool", "impressive", "smart"
        ]

        # Negative indicators
        negative_words = [
            "bad", "terrible", "awful", "hate", "stupid", "useless", "wrong",
            "broken", "frustrated", "annoying", "disappointing", "poor", "fail",
            "doesn't work", "not working", "error", "bug", "problem", "issue"
        ]

        positive_count = sum(1 for w in positive_words if w in text_lower)
        negative_count = sum(1 for w in negative_words if w in text_lower)

        # Emoticon analysis
        positive_emojis = ["😊", "👍", "❤️", "😄", "🎉", "✨", "🙌", "💯"]
        negative_emojis = ["😞", "👎", "💔", "😠", "😤", "🤬"]

        positive_count += sum(1 for e in positive_emojis if e in text)
        negative_count += sum(1 for e in negative_emojis if e in text)

        # Determine sentiment
        diff = positive_count - negative_count

        if diff >= 3:
            return SentimentType.VERY_POSITIVE
        elif diff >= 1:
            return SentimentType.POSITIVE
        elif diff <= -3:
            return SentimentType.VERY_NEGATIVE
        elif diff <= -1:
            return SentimentType.NEGATIVE
        else:
            return SentimentType.NEUTRAL

    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics from text"""
        topics = []

        # Technical topics
        tech_patterns = [
            r'\b(python|javascript|ai|machine learning|neural|code|programming)\b',
            r'\b(database|api|server|client|web|cloud|docker)\b',
            r'\b(analysis|data|algorithm|model|training)\b',
        ]

        # General interest patterns
        general_patterns = [
            r'\b(history|science|philosophy|art|music|literature)\b',
            r'\b(politics|economics|business|technology)\b',
        ]

        all_patterns = tech_patterns + general_patterns
        text_lower = text.lower()

        for pattern in all_patterns:
            matches = re.findall(pattern, text_lower)
            topics.extend(matches)

        return list(set(topics))[:5]

    def _estimate_satisfaction(
        self,
        message: str,
        response: str,
        emotion_before: str,
        emotion_after: str
    ) -> float:
        """Estimate user satisfaction from interaction"""
        satisfaction = 0.5

        # Sentiment contribution
        sentiment = self._analyze_sentiment(message)
        sentiment_scores = {
            SentimentType.VERY_POSITIVE: 0.9,
            SentimentType.POSITIVE: 0.7,
            SentimentType.NEUTRAL: 0.5,
            SentimentType.NEGATIVE: 0.3,
            SentimentType.VERY_NEGATIVE: 0.1,
        }
        satisfaction = sentiment_scores.get(sentiment, 0.5)

        # Emotion shift contribution
        positive_emotions = ["joy", "excitement", "contentment", "hope", "gratitude"]
        if emotion_after in positive_emotions and emotion_before not in positive_emotions:
            satisfaction += 0.1

        # Question answering
        if "?" in message and len(response) > 50:
            satisfaction += 0.1

        return min(1.0, max(0.0, satisfaction))

    def _learn_from_feedback(
        self,
        user_id: str,
        interaction: UserInteraction,
        was_helpful: bool,
        feedback_text: str
    ):
        """Learn preferences from user feedback"""
        # Learn topic preferences
        for topic in interaction.topics:
            pref_key = f"topic_{topic}"
            existing = self._find_preference(user_id, "topic", pref_key)

            if existing:
                # Update existing preference
                if was_helpful:
                    existing.confidence = min(1.0, existing.confidence + 0.1)
                else:
                    existing.confidence = max(0.0, existing.confidence - 0.1)
                existing.sample_count += 1
                existing.last_reinforced = datetime.now().isoformat()
            else:
                # Create new preference
                pref = UserPreference(
                    preference_id=hashlib.sha256(
                        f"{user_id}_{pref_key}".encode()
                    ).hexdigest()[:12],
                    user_id=user_id,
                    category="topic",
                    preference_key=pref_key,
                    preference_value="liked" if was_helpful else "disliked",
                    confidence=0.6,
                    sample_count=1,
                    first_observed=datetime.now().isoformat(),
                    last_reinforced=datetime.now().isoformat()
                )

                if user_id not in self._preferences:
                    self._preferences[user_id] = []
                self._preferences[user_id].append(pref)

    def _find_preference(
        self, user_id: str, category: str, key: str
    ) -> Optional[UserPreference]:
        """Find an existing preference"""
        if user_id not in self._preferences:
            return None

        for pref in self._preferences[user_id]:
            if pref.category == category and pref.preference_key == key:
                return pref
        return None

    def _update_stats(self, interaction: UserInteraction):
        """Update aggregate statistics"""
        user_id = interaction.user_id

        # Update user stats
        if user_id not in self._user_stats:
            self._user_stats[user_id] = UserBehaviorStats(user_id=user_id)

        stats = self._user_stats[user_id]
        stats.total_interactions += 1
        stats.last_active = interaction.timestamp

        # Update avg satisfaction (rolling)
        n = stats.total_interactions
        stats.avg_satisfaction = (
            (stats.avg_satisfaction * (n - 1) + interaction.satisfaction_score) / n
        )

        # Update topics
        for topic in interaction.topics:
            if topic not in stats.favorite_topics:
                stats.favorite_topics.append(topic)
            if len(stats.favorite_topics) > 10:
                stats.favorite_topics = stats.favorite_topics[-10:]

        # Update global stats
        self._global_stats.total_interactions += 1

        # Update user count
        unique_users = set(i.user_id for i in self._interactions)
        self._global_stats.total_users = len(unique_users)

        # Update global avg satisfaction
        n = self._global_stats.total_interactions
        self._global_stats.avg_satisfaction = (
            (self._global_stats.avg_satisfaction * (n - 1) +
             interaction.satisfaction_score) / n
        )

    def _update_improvement_correlations(self, current_satisfaction: float):
        """Update correlation between improvements and satisfaction"""
        for imp_id, data in self._pre_post_satisfaction.items():
            if data["post"] is None:
                # Check if enough time has passed (5 minutes)
                imp_time = datetime.fromisoformat(data["timestamp"])
                if (datetime.now() - imp_time).total_seconds() > 300:
                    data["post"] = current_satisfaction

    # ═══════════════════════════════════════════════════════════════════════════
    # ANALYSIS LOOP
    # ═══════════════════════════════════════════════════════════════════════════

    def _analysis_loop(self):
        """Periodic analysis of user behavior"""
        logger.info("User behavior analysis loop started")

        time.sleep(30)  # Initial delay

        while self._running:
            try:
                # Analyze patterns
                self._analyze_patterns()

                # Detect churn risk
                self._detect_churn_risk()

                # Generate insights
                self._generate_insights()

                # Save data periodically
                self._save_data()

                time.sleep(300)  # Every 5 minutes

            except Exception as e:
                logger.error(f"Behavior analysis error: {e}")
                time.sleep(60)

    def _analyze_patterns(self):
        """Analyze behavior patterns"""
        if len(self._satisfaction_history) < 10:
            return

        # Calculate satisfaction trend
        recent = list(self._satisfaction_history)[-20:]
        older = list(self._satisfaction_history)[-40:-20] if len(self._satisfaction_history) > 20 else recent

        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)

        self._global_stats.satisfaction_trend = recent_avg - older_avg

        # Update top topics
        self._global_stats.top_topics = self._topic_counter.most_common(10)

        # Update feature usage
        self._global_stats.feature_usage = dict(self._feature_usage.most_common(20))

    def _detect_churn_risk(self):
        """Detect users at risk of churning"""
        churn_count = 0

        for user_id, stats in self._user_stats.items():
            # Churn indicators
            if stats.total_interactions < 3:
                continue

            # Declining satisfaction
            if stats.avg_satisfaction < 0.4:
                churn_count += 1

            # Inactive for > 7 days
            try:
                last_active = datetime.fromisoformat(stats.last_active)
                days_inactive = (datetime.now() - last_active).days
                if days_inactive > 7:
                    churn_count += 1
            except:
                pass

        self._global_stats.churn_risk_users = churn_count

    def _generate_insights(self):
        """Generate insights for self-improvement"""
        insights = []

        # Low satisfaction areas
        if self._global_stats.avg_satisfaction < 0.5:
            insights.append({
                "type": "satisfaction_warning",
                "message": "Average satisfaction is below 50%",
                "recommendation": "Focus on improving response quality"
            })

        # Popular topics not in knowledge base
        if self._llm and self._llm.is_connected:
            try:
                top_topics = [t[0] for t in self._global_stats.top_topics[:5]]
                if top_topics:
                    publish(
                        EventType.CURIOSITY_TRIGGER,
                        {
                            "topic": top_topics[0],
                            "reason": "User interest detected",
                            "urgency": "high"
                        },
                        source="user_behavior_learner"
                    )
            except:
                pass

        # Feature usage insights
        popular_features = sorted(
            self._feature_usage.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        for feature, count in popular_features:
            insights.append({
                "type": "popular_feature",
                "feature": feature,
                "usage_count": count
            })

        return insights

    # ═══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════

    def get_user_preferences(self, user_id: str) -> List[Dict[str, Any]]:
        """Get learned preferences for a user"""
        if user_id not in self._preferences:
            return []
        return [p.to_dict() for p in self._preferences[user_id]]

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get behavior stats for a user"""
        if user_id not in self._user_stats:
            return {}
        return asdict(self._user_stats[user_id])

    def get_global_stats(self) -> Dict[str, Any]:
        """Get global behavior statistics"""
        stats = asdict(self._global_stats)
        stats["satisfaction_trend_history"] = list(self._satisfaction_history)[-100:]
        return stats

    def get_improvement_impact(self) -> Dict[str, Any]:
        """Get correlation between improvements and satisfaction"""
        impacts = {}

        for imp_id, data in self._pre_post_satisfaction.items():
            if data["post"] is not None:
                change = data["post"] - data["pre"]
                impacts[imp_id] = {
                    "satisfaction_change": change,
                    "pre": data["pre"],
                    "post": data["post"]
                }

        return impacts

    def get_recommendations(self) -> List[Dict[str, Any]]:
        """Get recommendations for self-improvement based on user behavior"""
        recommendations = []

        # Low satisfaction topics
        topic_satisfaction: Dict[str, List[float]] = {}
        for interaction in self._interactions:
            for topic in interaction.topics:
                if topic not in topic_satisfaction:
                    topic_satisfaction[topic] = []
                topic_satisfaction[topic].append(interaction.satisfaction_score)

        for topic, scores in topic_satisfaction.items():
            avg = sum(scores) / len(scores)
            if avg < 0.5 and len(scores) >= 3:
                recommendations.append({
                    "type": "improve_topic_knowledge",
                    "topic": topic,
                    "current_satisfaction": avg,
                    "sample_count": len(scores),
                    "priority": 1 - avg
                })

        # Improvement impact analysis
        for imp_id, data in self._pre_post_satisfaction.items():
            if data["post"] is not None:
                change = data["post"] - data["pre"]
                if change < 0:
                    recommendations.append({
                        "type": "improvement_negative_impact",
                        "improvement_id": imp_id,
                        "satisfaction_change": change,
                        "recommendation": "Consider rolling back or improving this change"
                    })

        return sorted(recommendations, key=lambda x: x.get("priority", 0), reverse=True)

    def get_recent_interactions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent interactions across all users"""
        return [i.to_dict() for i in list(self._interactions)[-limit:]]

    def get_user_interactions(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get interactions for a specific user"""
        if user_id not in self._user_interactions:
            return []
        return [i.to_dict() for i in list(self._user_interactions[user_id])[-limit:]]

    def get_hourly_activity(self) -> Dict[int, int]:
        """Get activity distribution by hour"""
        return dict(self._hourly_activity)

    def get_stats(self) -> Dict[str, Any]:
        """Get summary statistics for dashboard"""
        return {
            "total_users": self._global_stats.total_users,
            "total_interactions": self._global_stats.total_interactions,
            "avg_satisfaction": round(self._global_stats.avg_satisfaction, 3),
            "satisfaction_trend": self._calculate_satisfaction_trend(),
            "top_topics": self._global_stats.top_topics[:5],
            "churn_risk_users": self._global_stats.churn_risk_users,
            "tracked_preferences": sum(len(p) for p in self._preferences.values()),
            "feature_usage": dict(self._feature_usage.most_common(5)),
            "is_running": self._running
        }

    def _calculate_satisfaction_trend(self) -> float:
        """Calculate satisfaction trend from history"""
        if len(self._satisfaction_history) < 10:
            return 0.0
        recent = list(self._satisfaction_history)[-20:]
        older = list(self._satisfaction_history)[-40:-20] if len(self._satisfaction_history) > 20 else recent
        return round(sum(recent) / len(recent) - sum(older) / len(older), 3)

    # ═══════════════════════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════════════════════

    def _save_data(self):
        """Save data to disk"""
        try:
            # Save global stats
            stats_data = {
                "global_stats": asdict(self._global_stats),
                "topic_counter": dict(self._topic_counter),
                "feature_usage": dict(self._feature_usage),
                "hourly_activity": dict(self._hourly_activity),
                "improvement_events": self._improvement_events[-100:],
                "pre_post_satisfaction": self._pre_post_satisfaction,
                "saved_at": datetime.now().isoformat()
            }
            self._stats_file.write_text(
                json.dumps(stats_data, indent=2, default=str),
                encoding="utf-8"
            )

            # Save user stats
            user_stats_data = {
                uid: asdict(stats) for uid, stats in self._user_stats.items()
            }
            (self._data_dir / "user_stats.json").write_text(
                json.dumps(user_stats_data, indent=2, default=str),
                encoding="utf-8"
            )

            logger.debug("User behavior data saved")

        except Exception as e:
            logger.error(f"Error saving behavior data: {e}")

    def _load_data(self):
        """Load persisted data"""
        try:
            if self._stats_file.exists():
                data = json.loads(self._stats_file.read_text(encoding="utf-8"))

                # Restore global stats
                gs = data.get("global_stats", {})
                self._global_stats.total_users = gs.get("total_users", 0)
                self._global_stats.total_interactions = gs.get("total_interactions", 0)
                self._global_stats.avg_satisfaction = gs.get("avg_satisfaction", 0.5)

                # Restore counters
                self._topic_counter = Counter(data.get("topic_counter", {}))
                self._feature_usage = Counter(data.get("feature_usage", {}))
                self._hourly_activity = Counter(data.get("hourly_activity", {}))
                self._improvement_events = data.get("improvement_events", [])
                self._pre_post_satisfaction = data.get("pre_post_satisfaction", {})

                logger.info(f"Loaded behavior data: {self._global_stats.total_interactions} interactions")

            # Load user stats
            user_stats_file = self._data_dir / "user_stats.json"
            if user_stats_file.exists():
                data = json.loads(user_stats_file.read_text(encoding="utf-8"))
                for uid, stats in data.items():
                    self._user_stats[uid] = UserBehaviorStats(**stats)

        except Exception as e:
            logger.error(f"Error loading behavior data: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

user_behavior_learner = UserBehaviorLearner()

if __name__ == "__main__":
    print("📊 User Behavior Learner Test")

    learner = UserBehaviorLearner()
    learner.start()

    # Record test interaction
    learner.record_interaction(
        user_id="test_user",
        message="Can you help me with Python programming?",
        response="Of course! I'd be happy to help with Python.",
        response_time_ms=500
    )

    print(f"Stats: {json.dumps(learner.get_global_stats(), indent=2)}")
    print(f"Recommendations: {json.dumps(learner.get_recommendations(), indent=2)}")

    learner.stop()
    print("✅ Done")