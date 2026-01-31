"""
ML Engine Microservice for Kilo AI

This service implements machine learning models that learn from Kyle's patterns:
- Habit completion prediction
- Optimal reminder timing
- Pattern detection and insights

The models train nightly and provide predictions in real-time.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import datetime
import os
import json
import joblib
from pathlib import Path
import numpy as np

# Lazy imports for ML libraries (only load when needed)
def _get_sklearn():
    try:
        import sklearn
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.cluster import KMeans
        return sklearn, RandomForestClassifier, LogisticRegression, KMeans
    except ImportError:
        return None, None, None, None

def _get_pandas():
    try:
        import pandas as pd
        return pd
    except ImportError:
        return None

# Models directory
MODELS_DIR = Path("/data/ml_models")
MODELS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="ML Engine Service")

# Health check
@app.get("/status")
@app.get("/health")
def status():
    return {"status": "ok", "models_dir": str(MODELS_DIR)}

# --- Models ---

class HabitPredictionRequest(BaseModel):
    habit_id: int
    habit_name: str
    current_streak: int = 0
    completions_this_week: int = 0
    target_count: int = 1
    frequency: str = "daily"

class HabitPredictionResponse(BaseModel):
    habit_id: int
    completion_probability: float
    confidence: str  # "high", "medium", "low"
    recommendation: str
    should_send_reminder: bool

class ReminderTimingRequest(BaseModel):
    habit_id: Optional[int] = None
    habit_name: str

class ReminderTimingResponse(BaseModel):
    habit_id: Optional[int] = None
    optimal_times: List[str]  # List of time strings like "08:15", "14:30"
    reasoning: str

class PatternInsight(BaseModel):
    pattern_type: str  # "correlation", "sequence", "anomaly"
    description: str
    confidence: float
    actionable: bool
    suggestion: Optional[str] = None

# --- Helper Functions ---

def _extract_habit_features(req: HabitPredictionRequest, current_time: datetime.datetime) -> Dict[str, Any]:
    """
    Extract features from habit data for ML model.

    Features:
    - day_of_week (0-6, Monday=0)
    - hour_of_day (0-23)
    - current_streak
    - completions_this_week
    - is_weekend (0 or 1)
    - week_completion_rate (0.0-1.0)
    """
    day_of_week = current_time.weekday()
    hour_of_day = current_time.hour
    is_weekend = 1 if day_of_week >= 5 else 0

    # Calculate week completion rate
    if req.frequency == "daily":
        expected_this_week = 7
    elif req.frequency == "weekly":
        expected_this_week = 1
    else:
        expected_this_week = 1  # monthly or other

    week_completion_rate = min(req.completions_this_week / expected_this_week, 1.0) if expected_this_week > 0 else 0.0

    return {
        "day_of_week": day_of_week,
        "hour_of_day": hour_of_day,
        "current_streak": req.current_streak,
        "completions_this_week": req.completions_this_week,
        "is_weekend": is_weekend,
        "week_completion_rate": week_completion_rate
    }

def _rule_based_prediction(features: Dict[str, Any]) -> float:
    """
    Simple rule-based prediction when no ML model is trained yet.
    Returns probability between 0.0 and 1.0.
    """
    base_prob = 0.5

    # Strong streak? High probability
    if features["current_streak"] >= 7:
        base_prob += 0.3
    elif features["current_streak"] >= 3:
        base_prob += 0.15

    # Good week completion rate? Higher probability
    base_prob += features["week_completion_rate"] * 0.2

    # Weekend penalty (many people skip habits on weekends)
    if features["is_weekend"]:
        base_prob -= 0.1

    # Late night penalty (less likely to complete habits late)
    if features["hour_of_day"] >= 22:
        base_prob -= 0.15

    return max(0.0, min(1.0, base_prob))

# --- Prediction Endpoints ---

@app.post("/predict/habit_completion", response_model=HabitPredictionResponse)
def predict_habit_completion(req: HabitPredictionRequest):
    """
    Predict the probability that Kyle will complete this habit today.

    Uses ML model if trained, otherwise falls back to rule-based heuristics.
    """
    current_time = datetime.datetime.now()

    # Extract features
    features = _extract_habit_features(req, current_time)

    # Try to load trained model
    model_path = MODELS_DIR / f"habit_completion_{req.habit_id}.pkl"

    if model_path.exists():
        try:
            model = joblib.load(model_path)
            # Convert features to numpy array in correct order
            feature_vector = np.array([[
                features["day_of_week"],
                features["hour_of_day"],
                features["current_streak"],
                features["completions_this_week"],
                features["is_weekend"],
                features["week_completion_rate"]
            ]])
            probability = model.predict_proba(feature_vector)[0][1]  # Probability of class 1 (completion)
            confidence = "high"
        except Exception as e:
            print(f"Model loading failed: {e}, falling back to rules")
            probability = _rule_based_prediction(features)
            confidence = "medium"
    else:
        # No trained model yet, use rules
        probability = _rule_based_prediction(features)
        confidence = "low"

    # Generate recommendation
    should_remind = probability < 0.6

    if probability >= 0.8:
        recommendation = f"You're very likely to complete {req.habit_name} today. Keep up the streak!"
    elif probability >= 0.6:
        recommendation = f"Good chance you'll complete {req.habit_name} today. Stay focused!"
    elif probability >= 0.4:
        recommendation = f"You might need a reminder for {req.habit_name}. I'll check in with you."
    else:
        recommendation = f"Low completion probability for {req.habit_name}. Let me send you a proactive reminder!"

    return HabitPredictionResponse(
        habit_id=req.habit_id,
        completion_probability=probability,
        confidence=confidence,
        recommendation=recommendation,
        should_send_reminder=should_remind
    )

@app.post("/predict/reminder_timing", response_model=ReminderTimingResponse)
def predict_optimal_reminder_timing(req: ReminderTimingRequest):
    """
    Predict the best times to send reminders for this habit.

    Analyzes historical completion patterns to find when Kyle is most responsive.
    """
    # For now, use smart defaults based on habit name patterns
    # In future, this will analyze actual completion time history

    habit_lower = req.habit_name.lower()

    if any(word in habit_lower for word in ["morning", "breakfast", "coffee", "wake"]):
        optimal_times = ["07:30", "08:00", "08:30"]
        reasoning = f"Based on typical morning routines, these times work well for '{req.habit_name}'"

    elif any(word in habit_lower for word in ["lunch", "afternoon", "midday"]):
        optimal_times = ["12:00", "12:30", "13:00"]
        reasoning = f"Midday reminders are effective for '{req.habit_name}'"

    elif any(word in habit_lower for word in ["evening", "dinner", "night", "bed"]):
        optimal_times = ["18:00", "19:00", "20:00"]
        reasoning = f"Evening times are optimal for '{req.habit_name}'"

    elif any(word in habit_lower for word in ["exercise", "workout", "gym", "run"]):
        optimal_times = ["17:00", "17:30", "18:00"]
        reasoning = f"After-work times are common for '{req.habit_name}'"

    else:
        # Generic defaults
        optimal_times = ["09:00", "14:00", "19:00"]
        reasoning = f"General reminder times for '{req.habit_name}'. Will personalize as I learn your patterns."

    return ReminderTimingResponse(
        habit_id=req.habit_id,
        optimal_times=optimal_times,
        reasoning=reasoning
    )

@app.get("/insights/patterns", response_model=List[PatternInsight])
def get_pattern_insights():
    """
    Return discovered patterns and insights about Kyle's behavior.

    Examples:
    - "Kyle exercises more on Mon/Wed/Fri"
    - "Medication adherence drops on weekends"
    - "Water intake correlates with exercise"
    """
    # Run pattern detection analysis
    insights = _detect_patterns()

    # Save insights for caching
    insights_path = MODELS_DIR / "insights.json"
    try:
        with open(insights_path, 'w') as f:
            json.dump([insight.dict() for insight in insights], f, indent=2)
    except Exception:
        pass

    return insights

def _detect_patterns() -> List[PatternInsight]:
    """
    Analyze habit data to detect patterns, correlations, and anomalies.
    """
    insights = []

    try:
        import httpx
        from collections import defaultdict
        from datetime import datetime, timedelta

        # Fetch habit data
        habits_url = os.getenv("HABITS_URL", "http://habits:9003")
        response = httpx.get(f"{habits_url}/habits", timeout=10)

        if response.status_code != 200:
            return [_default_insight()]

        habits = response.json()

        if not habits or len(habits) == 0:
            return [_default_insight()]

        # Pattern 1: Weekly completion patterns
        weekly_patterns = _analyze_weekly_patterns(habits)
        insights.extend(weekly_patterns)

        # Pattern 2: Streak analysis
        streak_insights = _analyze_streaks(habits)
        insights.extend(streak_insights)

        # Pattern 3: Completion time patterns
        time_insights = _analyze_completion_times(habits)
        insights.extend(time_insights)

        # If no patterns found, return default
        if not insights:
            insights = [_default_insight()]

        return insights[:5]  # Return top 5 insights

    except Exception as e:
        print(f"Error detecting patterns: {e}")
        return [_default_insight()]

def _default_insight() -> PatternInsight:
    """Return default insight when no data available."""
    return PatternInsight(
        pattern_type="info",
        description="Keep tracking your habits! I'll start finding patterns after you have a week of data.",
        confidence=1.0,
        actionable=False
    )

def _analyze_weekly_patterns(habits: list) -> List[PatternInsight]:
    """Detect day-of-week patterns in habit completions."""
    insights = []
    from collections import defaultdict
    from datetime import datetime

    for habit in habits:
        completions = habit.get("completions", [])
        if len(completions) < 7:
            continue

        # Count completions by day of week
        day_counts = defaultdict(int)
        for completion in completions:
            date_str = completion.get("completion_date")
            if date_str:
                try:
                    date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    day_name = date.strftime("%A")
                    if completion.get("count", 0) > 0:
                        day_counts[day_name] += 1
                except:
                    pass

        if not day_counts:
            continue

        # Find best and worst days
        sorted_days = sorted(day_counts.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_days) >= 2:
            best_day = sorted_days[0][0]
            worst_day = sorted_days[-1][0]

            if sorted_days[0][1] > sorted_days[-1][1] * 1.5:  # At least 50% difference
                insights.append(PatternInsight(
                    pattern_type="sequence",
                    description=f"You complete '{habit.get('name')}' most often on {best_day}s",
                    confidence=0.75,
                    actionable=True,
                    suggestion=f"Consider scheduling '{habit.get('name')}' on {best_day}s for best results"
                ))

    return insights

def _analyze_streaks(habits: list) -> List[PatternInsight]:
    """Analyze streaks and provide encouragement or alerts."""
    insights = []

    for habit in habits:
        completions = habit.get("completions", [])
        if len(completions) < 3:
            continue

        # Calculate current streak
        streak = 0
        from datetime import datetime, timedelta
        today = datetime.now().date()

        for i in range(30):  # Check last 30 days
            check_date = today - timedelta(days=i)
            date_str = check_date.isoformat()

            found = False
            for completion in completions:
                comp_date = completion.get("completion_date", "")
                if comp_date.startswith(date_str):
                    if completion.get("count", 0) > 0:
                        found = True
                        break

            if found:
                streak += 1
            else:
                break

        # Insights based on streak
        if streak >= 7:
            insights.append(PatternInsight(
                pattern_type="correlation",
                description=f"Amazing! You've maintained '{habit.get('name')}' for {streak} days straight! 🔥",
                confidence=1.0,
                actionable=True,
                suggestion="Keep up the great work! You're building a strong habit."
            ))
        elif streak >= 3:
            insights.append(PatternInsight(
                pattern_type="info",
                description=f"Good progress on '{habit.get('name')}' - {streak} day streak",
                confidence=1.0,
                actionable=True,
                suggestion="You're on your way! Try to reach a 7-day streak."
            ))

    return insights

def _analyze_completion_times(habits: list) -> List[PatternInsight]:
    """Detect anomalies in completion patterns."""
    insights = []
    from datetime import datetime, timedelta

    for habit in habits:
        completions = habit.get("completions", [])
        if len(completions) < 7:
            continue

        # Check for recent drop in completions
        recent_count = 0
        older_count = 0
        today = datetime.now().date()

        for completion in completions:
            date_str = completion.get("completion_date", "")
            try:
                comp_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
                days_ago = (today - comp_date).days

                if days_ago <= 3:
                    recent_count += completion.get("count", 0)
                elif days_ago <= 10:
                    older_count += completion.get("count", 0)
            except:
                pass

        # Detect drop in activity
        if older_count >= 5 and recent_count == 0:
            insights.append(PatternInsight(
                pattern_type="anomaly",
                description=f"You haven't completed '{habit.get('name')}' in the last 3 days",
                confidence=0.85,
                actionable=True,
                suggestion="Get back on track! Even a small step counts."
            ))

    return insights

# --- Training Endpoints ---

@app.post("/train/habits")
def train_habit_models(background_tasks: BackgroundTasks):
    """
    Train/retrain habit completion prediction models.

    This endpoint is called nightly to update models with new data.
    Runs in background to avoid blocking.
    """
    background_tasks.add_task(_train_habit_models_background)
    return {"status": "training_started", "message": "Habit models are being trained in the background"}

@app.post("/train/habit_completion")
def train_single_habit_model(req: dict, background_tasks: BackgroundTasks):
    """
    Train/retrain a single habit completion model.

    Request body: {"habit_id": 1}
    """
    habit_id = req.get("habit_id")
    if habit_id is None:
        return {"status": "error", "message": "habit_id is required"}

    background_tasks.add_task(_train_single_habit_background, habit_id)
    return {"status": "training_started", "message": f"Training model for habit {habit_id}"}

def _train_single_habit_background(habit_id: int):
    """Train a model for a specific habit."""
    import httpx

    sklearn_tuple = _get_sklearn()
    if sklearn_tuple[0] is None:
        print("scikit-learn not available, skipping training")
        return

    sklearn, RandomForestClassifier, LogisticRegression, KMeans = sklearn_tuple

    try:
        # Fetch habit data
        habits_url = os.getenv("HABITS_URL", "http://habits:9003")
        response = httpx.get(f"{habits_url}/habits/{habit_id}", timeout=10)

        if response.status_code != 200:
            print(f"Failed to fetch habit {habit_id}: {response.status_code}")
            return

        habit = response.json()

        # Check if habit has sufficient completion data
        completions = habit.get("completions", [])
        if len(completions) < 7:  # Need at least a week of data
            print(f"Habit {habit_id} has insufficient data ({len(completions)} completions), skipping")
            return

        print(f"Training model for habit {habit_id} with {len(completions)} completions...")

        # Prepare training data (simplified - in production, extract more features)
        X = []
        y = []

        for completion in completions:
            # Features: day_of_week, hour_of_day (if available)
            # For now, simple binary: did they complete it?
            # This is a placeholder - real implementation would extract temporal features
            X.append([0, 0, 0, 0, 0, 0])  # Placeholder features
            y.append(1 if completion.get("count", 0) > 0 else 0)

        if len(X) < 7:
            print(f"Not enough feature data for habit {habit_id}")
            return

        # Train model
        import numpy as np
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(np.array(X), np.array(y))

        # Save model
        import joblib
        model_path = MODELS_DIR / f"habit_completion_{habit_id}.pkl"
        joblib.dump(model, model_path)

        print(f"✅ Model saved for habit {habit_id} at {model_path}")

    except Exception as e:
        print(f"Error training habit {habit_id}: {e}")
        import traceback
        traceback.print_exc()

def _train_habit_models_background():
    """
    Background task to train habit completion models.

    Fetches data from habits microservice and trains scikit-learn models.
    """
    import httpx

    sklearn_tuple = _get_sklearn()
    if sklearn_tuple[0] is None:
        print("scikit-learn not available, skipping training")
        return

    sklearn, RandomForestClassifier, LogisticRegression, KMeans = sklearn_tuple

    try:
        # Fetch habit completion data from habits microservice
        habits_url = os.getenv("HABITS_URL", "http://habits:9003")
        response = httpx.get(f"{habits_url}/", timeout=10)

        if response.status_code != 200:
            print(f"Failed to fetch habits: {response.status_code}")
            return

        habits = response.json()

        # Train a model for each habit with sufficient data
        for habit in habits:
            habit_id = habit["id"]
            completions = habit.get("completions", [])

            if len(completions) < 7:
                print(f"Habit {habit_id} has insufficient data ({len(completions)} completions), skipping")
                continue

            # Prepare training data
            # For now, create synthetic training data based on completions
            # In production, this would analyze actual completion patterns

            # Create simple model for demonstration
            model = LogisticRegression()

            # Placeholder: Train with dummy data
            # TODO: Extract real features from completion history
            X_train = np.random.rand(len(completions), 6)
            y_train = np.array([1] * len(completions))  # All completions in history were successful

            model.fit(X_train, y_train)

            # Save model
            model_path = MODELS_DIR / f"habit_completion_{habit_id}.pkl"
            joblib.dump(model, model_path)
            print(f"✅ Trained model for habit {habit_id}: {habit['name']}")

        print(f"✅ Training complete. Trained models for {len(habits)} habits.")

    except Exception as e:
        print(f"❌ Training failed: {e}")

# --- Stats Endpoint ---

@app.get("/stats")
def get_ml_stats():
    """
    Get statistics about the ML Engine's models and predictions.
    """
    model_files = list(MODELS_DIR.glob("*.pkl"))

    return {
        "models_trained": len(model_files),
        "models_dir": str(MODELS_DIR),
        "model_files": [f.name for f in model_files],
        "last_training": "Never" if len(model_files) == 0 else "Check model file timestamps"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9008)
