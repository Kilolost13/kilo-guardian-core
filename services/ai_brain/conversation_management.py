#!/usr/bin/env python3
"""
Advanced Conversation Management System for AI Brain

Manages goal-oriented conversations, tracks user objectives, and provides
contextual responses based on conversation history and user goals.
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages conversations with goal tracking and context awareness"""

    def __init__(self):
        self.active_conversations = {}
        self.conversation_history = defaultdict(list)
        self.user_goals = defaultdict(list)
        self.context_window_size = 10  # Number of recent exchanges to keep in context

    def start_conversation(self, conversation_id: str, user_id: str,
                          initial_context: Dict[str, Any] = None) -> str:
        """Start a new conversation session"""
        conversation = {
            "id": conversation_id,
            "user_id": user_id,
            "started_at": datetime.utcnow(),
            "status": "active",
            "goals": [],
            "context": initial_context or {},
            "turns": [],
            "metadata": {
                "total_turns": 0,
                "topics_discussed": set(),
                "goals_achieved": 0
            }
        }

        self.active_conversations[conversation_id] = conversation
        logger.info(f"Started conversation {conversation_id} for user {user_id}")
        return conversation_id

    def add_turn(self, conversation_id: str, user_message: str,
                ai_response: str, metadata: Dict[str, Any] = None) -> bool:
        """Add a conversation turn"""
        if conversation_id not in self.active_conversations:
            logger.warning(f"Conversation {conversation_id} not found")
            return False

        conversation = self.active_conversations[conversation_id]
        turn = {
            "timestamp": datetime.utcnow(),
            "user_message": user_message,
            "ai_response": ai_response,
            "metadata": metadata or {},
            "turn_number": conversation["metadata"]["total_turns"] + 1
        }

        conversation["turns"].append(turn)
        conversation["metadata"]["total_turns"] += 1

        # Update topics discussed
        topics = self._extract_topics(user_message)
        conversation["metadata"]["topics_discussed"].update(topics)

        # Maintain context window
        if len(conversation["turns"]) > self.context_window_size:
            conversation["turns"] = conversation["turns"][-self.context_window_size:]

        # Update conversation history
        self.conversation_history[conversation["user_id"]].append(turn)
        if len(self.conversation_history[conversation["user_id"]]) > 100:  # Limit history
            self.conversation_history[conversation["user_id"]] = self.conversation_history[conversation["user_id"]][-100:]

        return True

    def set_goals(self, conversation_id: str, goals: List[Dict[str, Any]]) -> bool:
        """Set goals for the conversation"""
        if conversation_id not in self.active_conversations:
            return False

        conversation = self.active_conversations[conversation_id]
        conversation["goals"] = goals

        # Also store in user goals
        user_id = conversation["user_id"]
        for goal in goals:
            goal_entry = {
                "goal": goal,
                "conversation_id": conversation_id,
                "set_at": datetime.utcnow(),
                "status": "active"
            }
            self.user_goals[user_id].append(goal_entry)

        logger.info(f"Set {len(goals)} goals for conversation {conversation_id}")
        return True

    def update_goal_progress(self, conversation_id: str, goal_index: int,
                           progress: float, status: str = None) -> bool:
        """Update progress on a conversation goal"""
        if conversation_id not in self.active_conversations:
            return False

        conversation = self.active_conversations[conversation_id]
        if goal_index >= len(conversation["goals"]):
            return False

        goal = conversation["goals"][goal_index]
        goal["progress"] = progress
        goal["last_updated"] = datetime.utcnow()

        if status:
            goal["status"] = status
            if status == "completed":
                conversation["metadata"]["goals_achieved"] += 1

        return True

    def get_conversation_context(self, conversation_id: str) -> Dict[str, Any]:
        """Get current conversation context"""
        if conversation_id not in self.active_conversations:
            return {}

        conversation = self.active_conversations[conversation_id]

        # Build context from recent turns and goals
        recent_turns = conversation["turns"][-3:]  # Last 3 turns
        active_goals = [g for g in conversation["goals"] if g.get("status") != "completed"]

        context = {
            "conversation_id": conversation_id,
            "user_id": conversation["user_id"],
            "turns_so_far": conversation["metadata"]["total_turns"],
            "active_goals": active_goals,
            "recent_topics": list(conversation["metadata"]["topics_discussed"]),
            "recent_turns": [
                {
                    "user": turn["user_message"][:100] + "..." if len(turn["user_message"]) > 100 else turn["user_message"],
                    "ai": turn["ai_response"][:100] + "..." if len(turn["ai_response"]) > 100 else turn["ai_response"],
                    "timestamp": turn["timestamp"]
                }
                for turn in recent_turns
            ],
            "goals_achieved": conversation["metadata"]["goals_achieved"]
        }

        return context

    def get_user_insights(self, user_id: str) -> Dict[str, Any]:
        """Get insights about user based on conversation history"""
        user_conversations = [c for c in self.active_conversations.values() if c["user_id"] == user_id]
        user_history = self.conversation_history.get(user_id, [])
        user_goals_history = self.user_goals.get(user_id, [])

        insights = {
            "total_conversations": len(user_conversations),
            "total_turns": len(user_history),
            "active_goals": len([g for g in user_goals_history if g.get("status") == "active"]),
            "completed_goals": len([g for g in user_goals_history if g.get("status") == "completed"]),
            "common_topics": self._get_common_topics(user_history),
            "conversation_patterns": self._analyze_conversation_patterns(user_history),
            "goal_success_rate": self._calculate_goal_success_rate(user_goals_history)
        }

        return insights

    def suggest_next_actions(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Suggest next actions based on conversation context"""
        if conversation_id not in self.active_conversations:
            return []

        conversation = self.active_conversations[conversation_id]
        suggestions = []

        # Check for goal progress
        active_goals = [g for g in conversation["goals"] if g.get("status") != "completed"]
        if active_goals:
            for goal in active_goals:
                progress = goal.get("progress", 0)
                if progress < 0.5:
                    suggestions.append({
                        "action": "focus_on_goal",
                        "goal": goal,
                        "reason": f"Goal '{goal.get('description', 'Unknown')}' needs attention",
                        "priority": "high"
                    })

        # Check conversation flow
        recent_turns = conversation["turns"][-2:]
        if len(recent_turns) >= 2:
            # Analyze if conversation is getting repetitive or stuck
            last_two_responses = [turn["ai_response"] for turn in recent_turns]
            if self._responses_similar(last_two_responses):
                suggestions.append({
                    "action": "change_topic",
                    "reason": "Conversation appears to be repetitive",
                    "priority": "medium"
                })

        # Check for natural conversation breaks
        if conversation["metadata"]["total_turns"] > 5:
            time_since_last_turn = datetime.utcnow() - conversation["turns"][-1]["timestamp"]
            if time_since_last_turn > timedelta(minutes=30):
                suggestions.append({
                    "action": "check_engagement",
                    "reason": "User may need re-engagement",
                    "priority": "low"
                })

        return suggestions

    def end_conversation(self, conversation_id: str, reason: str = "completed") -> bool:
        """End a conversation"""
        if conversation_id not in self.active_conversations:
            return False

        conversation = self.active_conversations[conversation_id]
        conversation["status"] = "ended"
        conversation["ended_at"] = datetime.utcnow()
        conversation["end_reason"] = reason

        # Archive conversation (in real implementation, would save to database)
        logger.info(f"Ended conversation {conversation_id}: {reason}")

        # Clean up active conversations after some time
        # For now, just mark as ended

        return True

    def _extract_topics(self, message: str) -> set:
        """Extract topics from a message (simplified)"""
        topics = set()

        # Simple keyword-based topic extraction
        message_lower = message.lower()

        topic_keywords = {
            "health": ["health", "medical", "medicine", "doctor", "hospital"],
            "habits": ["habit", "routine", "exercise", "walk", "run"],
            "medication": ["medication", "pills", "dose", "take"],
            "activity": ["activity", "active", "sedentary", "sitting"],
            "goals": ["goal", "achieve", "target", "objective"]
        }

        for topic, keywords in topic_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                topics.add(topic)

        return topics

    def _get_common_topics(self, history: List[Dict]) -> List[str]:
        """Get most common topics from conversation history"""
        topic_counts = defaultdict(int)

        for turn in history:
            topics = self._extract_topics(turn.get("user_message", ""))
            for topic in topics:
                topic_counts[topic] += 1

        # Return top 5 topics
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        return [topic for topic, count in sorted_topics[:5]]

    def _analyze_conversation_patterns(self, history: List[Dict]) -> Dict[str, Any]:
        """Analyze patterns in conversation history"""
        if not history:
            return {}

        # Analyze conversation length and frequency
        timestamps = [turn["timestamp"] for turn in history]
        if len(timestamps) > 1:
            intervals = [(timestamps[i] - timestamps[i-1]).total_seconds() / 3600
                        for i in range(1, len(timestamps))]  # hours

            avg_interval = sum(intervals) / len(intervals) if intervals else 0
            conversation_frequency = 24 / avg_interval if avg_interval > 0 else 0
        else:
            conversation_frequency = 0

        # Analyze message length patterns
        user_lengths = [len(turn.get("user_message", "")) for turn in history]
        ai_lengths = [len(turn.get("ai_response", "")) for turn in history]

        return {
            "conversation_frequency_per_day": conversation_frequency,
            "avg_user_message_length": sum(user_lengths) / len(user_lengths) if user_lengths else 0,
            "avg_ai_response_length": sum(ai_lengths) / len(ai_lengths) if ai_lengths else 0,
            "total_conversations": len(set(turn.get("conversation_id") for turn in history if turn.get("conversation_id")))
        }

    def _calculate_goal_success_rate(self, goals_history: List[Dict]) -> float:
        """Calculate goal success rate"""
        if not goals_history:
            return 0.0

        completed_goals = len([g for g in goals_history if g.get("status") == "completed"])
        return completed_goals / len(goals_history)

    def _responses_similar(self, responses: List[str]) -> bool:
        """Check if responses are similar (simplified)"""
        if len(responses) < 2:
            return False

        # Simple similarity check based on common words
        words1 = set(responses[0].lower().split())
        words2 = set(responses[1].lower().split())

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        if not union:
            return False

        jaccard_similarity = len(intersection) / len(union)
        return jaccard_similarity > 0.6  # 60% similarity threshold


class GoalOrientedAssistant:
    """Assistant that manages goal-oriented interactions"""

    def __init__(self, conversation_manager: ConversationManager):
        self.cm = conversation_manager
        self.goal_templates = {
            "health_improvement": {
                "description": "Improve overall health through habits and medication adherence",
                "steps": ["assess_current_habits", "set_medication_reminders", "track_progress", "provide_encouragement"],
                "duration_days": 30
            },
            "habit_formation": {
                "description": "Form a new positive habit",
                "steps": ["identify_habit", "create_reminder_system", "track_streaks", "celebrate_milestones"],
                "duration_days": 21
            },
            "medication_management": {
                "description": "Improve medication adherence and timing",
                "steps": ["review_schedule", "set_reminders", "track_adherence", "address_side_effects"],
                "duration_days": 14
            }
        }

    def create_goal_from_template(self, template_name: str, customization: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a goal from a template"""
        if template_name not in self.goal_templates:
            return {}

        template = self.goal_templates[template_name]
        goal = {
            "type": template_name,
            "description": template["description"],
            "steps": template["steps"].copy(),
            "duration_days": template["duration_days"],
            "progress": 0.0,
            "status": "active",
            "created_at": datetime.utcnow(),
            "customization": customization or {}
        }

        # Apply customizations
        if customization:
            if "description" in customization:
                goal["description"] = customization["description"]
            if "duration_days" in customization:
                goal["duration_days"] = customization["duration_days"]

        return goal

    def suggest_goals_based_on_context(self, user_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest goals based on user context and history"""
        suggestions = []

        # Analyze user context for goal suggestions
        health_indicators = user_context.get("health_indicators", [])
        habit_data = user_context.get("habit_data", [])
        medication_data = user_context.get("medication_data", [])

        # Suggest health improvement if sedentary
        if "sedentary" in health_indicators or len(habit_data) < 3:
            suggestions.append(self.create_goal_from_template("health_improvement"))

        # Suggest habit formation if few habits tracked
        if len(habit_data) < 5:
            suggestions.append(self.create_goal_from_template("habit_formation"))

        # Suggest medication management if medication issues detected
        med_adherence = user_context.get("medication_adherence", 1.0)
        if med_adherence < 0.8 and medication_data:
            suggestions.append(self.create_goal_from_template("medication_management"))

        return suggestions

    def track_goal_progress(self, goal: Dict[str, Any], user_actions: List[Dict]) -> Dict[str, Any]:
        """Track progress on a goal based on user actions"""
        goal_type = goal.get("type")
        progress = goal.get("progress", 0.0)

        # Update progress based on goal type and actions
        if goal_type == "habit_formation":
            habit_actions = [a for a in user_actions if a.get("type") == "habit_completed"]
            if habit_actions:
                # Simple progress calculation
                progress = min(1.0, progress + len(habit_actions) * 0.1)

        elif goal_type == "medication_management":
            med_actions = [a for a in user_actions if a.get("type") == "medication_taken"]
            if med_actions:
                progress = min(1.0, progress + len(med_actions) * 0.2)

        elif goal_type == "health_improvement":
            health_actions = [a for a in user_actions if a.get("type") in ["exercise", "healthy_eating"]]
            if health_actions:
                progress = min(1.0, progress + len(health_actions) * 0.05)

        goal["progress"] = progress
        goal["last_updated"] = datetime.utcnow()

        # Check if goal is completed
        if progress >= 1.0:
            goal["status"] = "completed"
            goal["completed_at"] = datetime.utcnow()

        return goal


# Global instances
conversation_manager = ConversationManager()
goal_assistant = GoalOrientedAssistant(conversation_manager)