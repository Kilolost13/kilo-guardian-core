#!/usr/bin/env python3
"""
Predictive Modeling System for AI Brain

Implements predictive analytics for habits, health patterns, and user behavior
to provide proactive assistance and insights.
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import statistics
import logging

logger = logging.getLogger(__name__)


class PredictiveModel:
    """Base class for predictive models"""

    def __init__(self, model_type: str):
        self.model_type = model_type
        self.is_trained = False
        self.accuracy_score = 0.0

    def train(self, data: List[Dict]) -> bool:
        """Train the model with historical data"""
        raise NotImplementedError

    def predict(self, current_data: Dict) -> Dict[str, Any]:
        """Make predictions based on current data"""
        raise NotImplementedError

    def get_confidence(self) -> float:
        """Get prediction confidence score"""
        return self.accuracy_score


class HabitPredictor(PredictiveModel):
    """Predicts habit adherence and suggests interventions"""

    def __init__(self):
        super().__init__("habit_prediction")
        self.habit_patterns = {}
        self.intervention_suggestions = {
            "low_adherence": [
                "Consider setting a reminder for this habit",
                "Try breaking it into smaller, easier steps",
                "Find an accountability partner",
                "Reward yourself for completion"
            ],
            "inconsistent_timing": [
                "Try to do this at the same time each day",
                "Set a specific time-based reminder",
                "Create a routine around this habit"
            ],
            "weekend_dropoff": [
                "Maintain consistency on weekends too",
                "Schedule weekend reminders",
                "Focus on building momentum"
            ]
        }

    def train(self, habit_data: List[Dict]) -> bool:
        """Train on habit completion patterns"""
        if not habit_data:
            return False

        # Group by habit type
        by_habit = defaultdict(list)
        for entry in habit_data:
            habit_type = entry.get("event_type", "unknown")
            by_habit[habit_type].append(entry)

        # Analyze patterns for each habit
        for habit_type, entries in by_habit.items():
            pattern = self._analyze_habit_pattern(entries)
            self.habit_patterns[habit_type] = pattern

        self.is_trained = True
        self.accuracy_score = 0.75  # Estimated accuracy
        return True

    def predict(self, current_data: Dict) -> Dict[str, Any]:
        """Predict habit completion likelihood"""
        habit_type = current_data.get("event_type", "unknown")
        pattern = self.habit_patterns.get(habit_type, {})

        if not pattern:
            return {"prediction": "unknown", "confidence": 0.0}

        # Simple prediction based on recent performance
        recent_completion_rate = pattern.get("recent_completion_rate", 0.5)
        overall_trend = pattern.get("trend", 0)

        # Predict next completion
        base_probability = recent_completion_rate
        trend_adjustment = overall_trend * 0.1  # Trend influence
        prediction_prob = max(0, min(1, base_probability + trend_adjustment))

        # Generate interventions if needed
        interventions = []
        if prediction_prob < 0.5:
            issues = self._identify_habit_issues(pattern)
            for issue in issues:
                suggestions = self.intervention_suggestions.get(issue, [])
                interventions.extend(suggestions[:2])  # Limit suggestions

        return {
            "habit_type": habit_type,
            "completion_probability": prediction_prob,
            "confidence": self.accuracy_score,
            "trend": "improving" if overall_trend > 0 else "declining" if overall_trend < 0 else "stable",
            "suggested_interventions": interventions[:3],  # Top 3 suggestions
            "next_best_time": pattern.get("peak_time")
        }

    def _analyze_habit_pattern(self, entries: List[Dict]) -> Dict[str, Any]:
        """Analyze completion pattern for a habit"""
        if not entries:
            return {}

        # Sort by timestamp
        sorted_entries = sorted(entries, key=lambda x: x.get("timestamp", datetime.min))

        # Calculate completion rates
        completions = [e for e in entries if e.get("completed", False)]
        completion_rate = len(completions) / len(entries) if entries else 0

        # Recent performance (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_entries = [e for e in sorted_entries
                         if e.get("timestamp", datetime.min) > week_ago]
        recent_completion_rate = (
            len([e for e in recent_entries if e.get("completed", False)]) /
            len(recent_entries) if recent_entries else completion_rate
        )

        # Time-based patterns
        completion_times = [e.get("timestamp", datetime.min).hour
                          for e in completions if e.get("timestamp")]
        peak_time = statistics.mode(completion_times) if completion_times else None

        # Trend analysis (simple linear trend)
        if len(sorted_entries) > 5:
            recent_half = sorted_entries[-len(sorted_entries)//2:]
            recent_rate = len([e for e in recent_half if e.get("completed", False)]) / len(recent_half)
            trend = recent_rate - completion_rate
        else:
            trend = 0

        return {
            "completion_rate": completion_rate,
            "recent_completion_rate": recent_completion_rate,
            "peak_time": peak_time,
            "trend": trend,
            "total_entries": len(entries),
            "consistency_score": self._calculate_consistency(sorted_entries)
        }

    def _calculate_consistency(self, entries: List[Dict]) -> float:
        """Calculate habit consistency score"""
        if len(entries) < 2:
            return 0.0

        # Check for regular intervals
        timestamps = [e.get("timestamp") for e in entries if e.get("timestamp")]
        if len(timestamps) < 2:
            return 0.0

        intervals = []
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i-1]).total_seconds() / 3600  # hours
            intervals.append(interval)

        if not intervals:
            return 0.0

        # Consistency is inverse of interval variance
        try:
            mean_interval = statistics.mean(intervals)
            if mean_interval == 0:
                return 1.0
            variance = statistics.variance(intervals) if len(intervals) > 1 else 0
            consistency = 1.0 / (1.0 + variance / (mean_interval ** 2))
            return min(1.0, consistency)
        except:
            return 0.0

    def _identify_habit_issues(self, pattern: Dict) -> List[str]:
        """Identify potential issues with habit performance"""
        issues = []

        if pattern.get("recent_completion_rate", 0) < 0.5:
            issues.append("low_adherence")

        if pattern.get("consistency_score", 0) < 0.3:
            issues.append("inconsistent_timing")

        # Check for weekend dropoff (simplified)
        # In real implementation, would analyze day-of-week patterns

        return issues


class HealthPredictor(PredictiveModel):
    """Predicts health trends and medication adherence"""

    def __init__(self):
        super().__init__("health_prediction")
        self.health_patterns = {}

    def train(self, health_data: List[Dict]) -> bool:
        """Train on health and medication data"""
        if not health_data:
            return False

        # Analyze medication adherence patterns
        med_data = [d for d in health_data if d.get("source") == "meds"]
        if med_data:
            self._analyze_medication_patterns(med_data)

        # Analyze health metrics
        cam_data = [d for d in health_data if d.get("source") == "cam"]
        if cam_data:
            self._analyze_health_patterns(cam_data)

        self.is_trained = True
        self.accuracy_score = 0.7
        return True

    def predict(self, current_data: Dict) -> Dict[str, Any]:
        """Predict health status and recommendations"""
        source = current_data.get("source", "unknown")

        if source == "meds":
            return self._predict_medication_adherence(current_data)
        elif source == "cam":
            return self._predict_health_status(current_data)
        else:
            return {"prediction": "unknown", "confidence": 0.0}

    def _predict_medication_adherence(self, med_data: Dict) -> Dict[str, Any]:
        """Predict medication adherence likelihood"""
        med_name = med_data.get("name", "unknown")

        # Simple prediction based on historical patterns
        pattern = self.health_patterns.get(f"med_{med_name}", {})
        adherence_rate = pattern.get("adherence_rate", 0.8)

        # Time-based factors
        current_hour = datetime.utcnow().hour
        scheduled_times = med_data.get("schedule", [])

        # Check if current time is near scheduled time
        time_factor = 0.1  # Base time factor
        for scheduled in scheduled_times:
            if abs(current_hour - scheduled) <= 2:  # Within 2 hours
                time_factor = 1.0
                break

        prediction_prob = adherence_rate * time_factor

        reminders = []
        if prediction_prob < 0.7:
            reminders = [
                f"Don't forget to take {med_name}",
                f"It's time for your {med_name} medication",
                "Medication reminder: staying consistent is important for your health"
            ]

        return {
            "medication": med_name,
            "adherence_probability": prediction_prob,
            "confidence": self.accuracy_score,
            "scheduled_times": scheduled_times,
            "reminders": reminders
        }

    def _predict_health_status(self, cam_data: Dict) -> Dict[str, Any]:
        """Predict health status from camera data"""
        posture = cam_data.get("posture", "unknown")

        # Simple health insights based on posture/activity
        insights = []

        if posture == "sitting":
            sedentary_time = cam_data.get("sedentary_minutes", 0)
            if sedentary_time > 120:  # 2+ hours
                insights.append("You've been sitting for quite a while. Consider standing up and stretching.")
            elif sedentary_time > 60:
                insights.append("Good time for a quick stretch break!")

        elif posture == "standing":
            insights.append("Great! Staying active is good for your health.")

        return {
            "current_posture": posture,
            "health_insights": insights,
            "confidence": self.accuracy_score,
            "recommendations": self._generate_health_recommendations(cam_data)
        }

    def _generate_health_recommendations(self, cam_data: Dict) -> List[str]:
        """Generate personalized health recommendations"""
        recommendations = []

        # Based on activity patterns
        activity_level = cam_data.get("activity_level", "moderate")

        if activity_level == "low":
            recommendations.extend([
                "Try to incorporate more movement into your day",
                "Consider a short walk to boost your energy",
                "Remember: even 5 minutes of activity makes a difference"
            ])
        elif activity_level == "high":
            recommendations.append("Great job staying active! Keep it up!")

        return recommendations

    def _analyze_medication_patterns(self, med_data: List[Dict]):
        """Analyze medication adherence patterns"""
        by_medication = defaultdict(list)

        for entry in med_data:
            med_name = entry.get("name", "unknown")
            by_medication[med_name].append(entry)

        for med_name, entries in by_medication.items():
            taken_count = len([e for e in entries if e.get("taken", False)])
            adherence_rate = taken_count / len(entries) if entries else 0

            self.health_patterns[f"med_{med_name}"] = {
                "adherence_rate": adherence_rate,
                "total_doses": len(entries),
                "taken_count": taken_count
            }

    def _analyze_health_patterns(self, cam_data: List[Dict]):
        """Analyze health patterns from camera data"""
        posture_counts = defaultdict(int)

        for entry in cam_data:
            posture = entry.get("posture", "unknown")
            posture_counts[posture] += 1

        total_entries = len(cam_data)
        self.health_patterns["posture_distribution"] = {
            posture: count / total_entries
            for posture, count in posture_counts.items()
        }


class PredictiveAnalytics:
    """Main predictive analytics system"""

    def __init__(self):
        self.models = {
            "habits": HabitPredictor(),
            "health": HealthPredictor()
        }
        self.insights_cache = {}

    def train_all_models(self, memory_data: List[Dict]) -> Dict[str, bool]:
        """Train all predictive models with memory data"""
        training_results = {}

        # Prepare data for each model
        habit_data = [m for m in memory_data if "habit" in m.get("source", "").lower()]
        health_data = [m for m in memory_data if m.get("source") in ["meds", "cam"]]

        # Train habit predictor
        training_results["habits"] = self.models["habits"].train(habit_data)

        # Train health predictor
        training_results["health"] = self.models["health"].train(health_data)

        logger.info(f"Training completed: {training_results}")
        return training_results

    def generate_predictions(self, current_context: Dict) -> Dict[str, Any]:
        """Generate predictions for current context"""
        predictions = {}

        for model_name, model in self.models.items():
            if model.is_trained:
                try:
                    prediction = model.predict(current_context)
                    predictions[model_name] = prediction
                except Exception as e:
                    logger.error(f"Prediction failed for {model_name}: {e}")

        return predictions

    def get_proactive_insights(self, user_id: str = None) -> List[Dict[str, Any]]:
        """Generate proactive insights and recommendations"""
        insights = []

        # Check for cached insights (avoid spam)
        cache_key = f"{user_id}_{datetime.utcnow().date()}"
        if cache_key in self.insights_cache:
            return self.insights_cache[cache_key]

        # Generate insights based on patterns
        # This would integrate with the actual memory data in a real implementation

        # Example insights (would be data-driven)
        insights = [
            {
                "type": "habit_reminder",
                "priority": "high",
                "message": "Based on your patterns, now would be a great time for your evening walk",
                "confidence": 0.8
            },
            {
                "type": "health_check",
                "priority": "medium",
                "message": "You've been sitting for 2 hours. A quick stretch would be beneficial.",
                "confidence": 0.7
            },
            {
                "type": "medication_reminder",
                "priority": "high",
                "message": "Time for your medication - staying consistent is important!",
                "confidence": 0.9
            }
        ]

        # Cache insights for the day
        self.insights_cache[cache_key] = insights

        return insights


# Global instance
predictive_analytics = PredictiveAnalytics()