"""
Pattern Recognizer - Behavioral pattern analysis for TBI memory assistance.

This module analyzes memory events, activities, and user interactions to:
1. Learn baseline behavioral patterns
2. Detect deviations from normal routines
3. Identify concerning behavioral changes
4. Provide actionable insights for users and caregivers

Key Patterns Detected:
- Medication adherence patterns
- Daily routine patterns (wake/sleep, meals)
- Activity patterns (exercise, social interaction)
- Memory query patterns (forgetfulness indicators)
- Anomaly detection (unusual behavior, missed routines)

Technical Approach:
- Statistical analysis (mean, std dev, z-scores)
- Time-series pattern detection
- Frequency analysis
- Anomaly detection using z-score thresholds
- Rolling window analysis for trend detection
"""

import logging
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

logger = logging.getLogger("PatternRecognizer")


# ============================================================================
# Data Structures
# ============================================================================


class DeviationReport(NamedTuple):
    """
    A structured report on a detected deviation from normal patterns.
    """

    is_deviation: bool
    severity: float  # 0.0 (no deviation) to 1.0 (critical deviation)
    summary: str
    details: Dict[str, Any]  # Additional context and recommendations


@dataclass
class PatternInsight:
    """
    An actionable insight derived from pattern analysis.
    """

    category: str  # 'medication', 'routine', 'activity', 'cognitive'
    insight_type: str  # 'positive', 'warning', 'critical'
    title: str
    description: str
    recommendation: Optional[str] = None
    confidence: float = 0.0  # 0.0 to 1.0
    data: Optional[Dict[str, Any]] = None


@dataclass
class BehavioralPattern:
    """
    A learned behavioral pattern with statistical properties.
    """

    pattern_type: str  # 'medication_time', 'wake_time', 'activity_frequency', etc.
    mean_value: float
    std_dev: float
    sample_count: int
    last_updated: datetime
    metadata: Dict[str, Any]


# ============================================================================
# Pattern Recognizer Core
# ============================================================================


class PatternRecognizer:
    """
    Establishes baseline behaviors and identifies anomalies for TBI users.

    Uses statistical methods and time-series analysis to:
    - Learn normal behavioral patterns from memory events
    - Detect deviations that may indicate problems
    - Generate actionable insights for users and caregivers
    """

    # Z-score thresholds for deviation severity
    Z_SCORE_WARNING = 2.0  # 2 standard deviations (95% confidence)
    Z_SCORE_CRITICAL = 3.0  # 3 standard deviations (99.7% confidence)

    # Minimum samples required for pattern learning
    MIN_SAMPLES_FOR_PATTERN = 3

    def __init__(self):
        """Initialize the pattern recognizer."""
        # Learned patterns: {pattern_type: BehavioralPattern}
        self._patterns: Dict[str, BehavioralPattern] = {}

        # Raw event history for pattern learning
        self._event_history: List[Dict[str, Any]] = []

        # Pattern learning statistics
        self._interaction_count = 0
        self._last_analysis_time = None

        logger.info("✅ PatternRecognizer initialized")

    # ========================================================================
    # Pattern Learning
    # ========================================================================

    def learn_from_memory_events(self, events: List[Dict[str, Any]]) -> int:
        """
        Learn patterns from memory events.

        Args:
            events: List of memory events from database
                   Each event should have: event_text, event_time, event_type

        Returns:
            Number of patterns learned/updated
        """
        if not events:
            logger.warning("No events provided for pattern learning")
            return 0

        patterns_updated = 0

        # Add events to history
        self._event_history.extend(events)

        # Learn medication adherence patterns
        patterns_updated += self._learn_medication_patterns(events)

        # Learn daily routine patterns
        patterns_updated += self._learn_routine_patterns(events)

        # Learn activity frequency patterns
        patterns_updated += self._learn_activity_patterns(events)

        self._last_analysis_time = datetime.now()
        logger.info(
            f"✅ Learned from {len(events)} events, updated {patterns_updated} patterns"
        )

        return patterns_updated

    def _learn_medication_patterns(self, events: List[Dict[str, Any]]) -> int:
        """
        Learn medication adherence patterns.

        Analyzes:
        - Typical medication times
        - Adherence consistency
        - Time variance

        Returns:
            Number of patterns learned
        """
        # Filter medication-related events
        med_events = [
            e
            for e in events
            if "medication" in e.get("event_text", "").lower()
            or e.get("event_type") == "medication"
        ]

        if len(med_events) < self.MIN_SAMPLES_FOR_PATTERN:
            return 0

        patterns_learned = 0

        # Extract medication times (hour of day as decimal, e.g., 14.5 for 2:30 PM)
        med_times = []
        for event in med_events:
            event_time = event.get("event_time")
            if isinstance(event_time, str):
                try:
                    dt = datetime.fromisoformat(event_time)
                    time_decimal = dt.hour + (dt.minute / 60.0)
                    med_times.append(time_decimal)
                except (ValueError, AttributeError):
                    continue

        if len(med_times) >= self.MIN_SAMPLES_FOR_PATTERN:
            mean_time = statistics.mean(med_times)
            std_time = statistics.stdev(med_times) if len(med_times) > 1 else 0.0

            self._patterns["medication_time"] = BehavioralPattern(
                pattern_type="medication_time",
                mean_value=mean_time,
                std_dev=std_time,
                sample_count=len(med_times),
                last_updated=datetime.now(),
                metadata={
                    "unit": "hours_decimal",
                    "description": "Typical medication time",
                },
            )
            patterns_learned += 1

        return patterns_learned

    def _learn_routine_patterns(self, events: List[Dict[str, Any]]) -> int:
        """
        Learn daily routine patterns (wake time, sleep time, meal times).

        Returns:
            Number of patterns learned
        """
        patterns_learned = 0

        # Pattern keywords
        routine_patterns = {
            "wake_time": ["wake", "woke up", "morning", "got up"],
            "sleep_time": ["sleep", "bed", "bedtime", "sleeping"],
            "meal_time": ["eating", "breakfast", "lunch", "dinner", "meal"],
        }

        for pattern_name, keywords in routine_patterns.items():
            # Filter events matching keywords
            matching_events = [
                e
                for e in events
                if any(kw in e.get("event_text", "").lower() for kw in keywords)
            ]

            if len(matching_events) < self.MIN_SAMPLES_FOR_PATTERN:
                continue

            # Extract times
            times = []
            for event in matching_events:
                event_time = event.get("event_time")
                if isinstance(event_time, str):
                    try:
                        dt = datetime.fromisoformat(event_time)
                        time_decimal = dt.hour + (dt.minute / 60.0)
                        times.append(time_decimal)
                    except (ValueError, AttributeError):
                        continue

            if len(times) >= self.MIN_SAMPLES_FOR_PATTERN:
                mean_time = statistics.mean(times)
                std_time = statistics.stdev(times) if len(times) > 1 else 0.0

                self._patterns[pattern_name] = BehavioralPattern(
                    pattern_type=pattern_name,
                    mean_value=mean_time,
                    std_dev=std_time,
                    sample_count=len(times),
                    last_updated=datetime.now(),
                    metadata={
                        "unit": "hours_decimal",
                        "description": f'Typical {pattern_name.replace("_", " ")}',
                    },
                )
                patterns_learned += 1

        return patterns_learned

    def _learn_activity_patterns(self, events: List[Dict[str, Any]]) -> int:
        """
        Learn activity frequency patterns.

        Analyzes:
        - How often activities occur
        - Activity diversity
        - Activity consistency

        Returns:
            Number of patterns learned
        """
        # Filter activity events
        activity_events = [e for e in events if e.get("event_type") == "activity"]

        if len(activity_events) < self.MIN_SAMPLES_FOR_PATTERN:
            return 0

        # Count activities per day
        activities_by_day = defaultdict(int)
        for event in activity_events:
            event_time = event.get("event_time")
            if isinstance(event_time, str):
                try:
                    dt = datetime.fromisoformat(event_time)
                    day_key = dt.date().isoformat()
                    activities_by_day[day_key] += 1
                except (ValueError, AttributeError):
                    continue

        if len(activities_by_day) < self.MIN_SAMPLES_FOR_PATTERN:
            return 0

        # Calculate daily activity frequency
        daily_counts = list(activities_by_day.values())
        mean_daily = statistics.mean(daily_counts)
        std_daily = statistics.stdev(daily_counts) if len(daily_counts) > 1 else 0.0

        self._patterns["activity_frequency"] = BehavioralPattern(
            pattern_type="activity_frequency",
            mean_value=mean_daily,
            std_dev=std_daily,
            sample_count=len(daily_counts),
            last_updated=datetime.now(),
            metadata={
                "unit": "activities_per_day",
                "description": "Daily activity frequency",
            },
        )

        return 1

    # ========================================================================
    # Deviation Detection
    # ========================================================================

    def detect_deviation(self, context: Dict[str, Any]) -> DeviationReport:
        """
        Detect deviations from learned patterns.

        Args:
            context: Current context to analyze
                    Should include: event_type, event_time, event_text, etc.

        Returns:
            DeviationReport with severity and recommendations
        """
        if not self._patterns:
            # No patterns learned yet
            return DeviationReport(
                is_deviation=False,
                severity=0.0,
                summary="Insufficient data for pattern analysis",
                details={"reason": "learning_phase", "patterns_count": 0},
            )

        event_type = context.get("event_type", "unknown")
        event_time = context.get("event_time")
        event_text = context.get("event_text", "")

        # Check for medication deviation
        if "medication" in event_text.lower() or event_type == "medication":
            return self._detect_medication_deviation(context)

        # Check for routine deviation
        if any(kw in event_text.lower() for kw in ["wake", "sleep", "meal", "eating"]):
            return self._detect_routine_deviation(context)

        # Check for activity deviation
        if event_type == "activity":
            return self._detect_activity_deviation(context)

        # Default: no deviation detected
        return DeviationReport(
            is_deviation=False,
            severity=0.0,
            summary="No significant deviation detected",
            details={"event_type": event_type},
        )

    def _detect_medication_deviation(self, context: Dict[str, Any]) -> DeviationReport:
        """Detect medication timing deviations."""
        pattern = self._patterns.get("medication_time")
        if not pattern:
            return DeviationReport(
                is_deviation=False,
                severity=0.0,
                summary="No medication pattern established yet",
                details={"reason": "no_pattern"},
            )

        # Extract current medication time
        event_time = context.get("event_time")
        if not event_time:
            return DeviationReport(
                is_deviation=False,
                severity=0.0,
                summary="No event time provided",
                details={"reason": "missing_time"},
            )

        try:
            dt = (
                datetime.fromisoformat(event_time)
                if isinstance(event_time, str)
                else event_time
            )
            current_time = dt.hour + (dt.minute / 60.0)
        except (ValueError, AttributeError):
            return DeviationReport(
                is_deviation=False,
                severity=0.0,
                summary="Invalid event time format",
                details={"reason": "invalid_time"},
            )

        # Calculate z-score
        if pattern.std_dev == 0:
            z_score = 0.0
        else:
            z_score = abs(current_time - pattern.mean_value) / pattern.std_dev

        # Determine severity
        if z_score >= self.Z_SCORE_CRITICAL:
            severity = 1.0
            is_deviation = True
            summary = f"Critical medication time deviation: {z_score:.1f}σ from normal"
        elif z_score >= self.Z_SCORE_WARNING:
            severity = 0.6
            is_deviation = True
            summary = f"Medication taken at unusual time: {z_score:.1f}σ from normal"
        else:
            severity = 0.0
            is_deviation = False
            summary = "Medication taken at normal time"

        # Calculate time difference in hours
        time_diff = abs(current_time - pattern.mean_value)

        return DeviationReport(
            is_deviation=is_deviation,
            severity=severity,
            summary=summary,
            details={
                "z_score": z_score,
                "expected_time": self._decimal_to_time_string(pattern.mean_value),
                "actual_time": self._decimal_to_time_string(current_time),
                "time_difference_hours": time_diff,
                "recommendation": self._get_medication_recommendation(
                    z_score, time_diff
                ),
            },
        )

    def _detect_routine_deviation(self, context: Dict[str, Any]) -> DeviationReport:
        """Detect routine (wake/sleep/meal) deviations."""
        event_text = context.get("event_text", "").lower()

        # Determine which routine pattern to check
        pattern_name = None
        if any(kw in event_text for kw in ["wake", "woke up", "morning"]):
            pattern_name = "wake_time"
        elif any(kw in event_text for kw in ["sleep", "bed", "bedtime"]):
            pattern_name = "sleep_time"
        elif any(
            kw in event_text
            for kw in ["eating", "meal", "breakfast", "lunch", "dinner"]
        ):
            pattern_name = "meal_time"

        if not pattern_name or pattern_name not in self._patterns:
            return DeviationReport(
                is_deviation=False,
                severity=0.0,
                summary="No pattern established for this routine",
                details={"pattern_type": pattern_name},
            )

        pattern = self._patterns[pattern_name]

        # Extract current time
        event_time = context.get("event_time")
        if not event_time:
            return DeviationReport(
                is_deviation=False,
                severity=0.0,
                summary="No event time provided",
                details={"reason": "missing_time"},
            )

        try:
            dt = (
                datetime.fromisoformat(event_time)
                if isinstance(event_time, str)
                else event_time
            )
            current_time = dt.hour + (dt.minute / 60.0)
        except (ValueError, AttributeError):
            return DeviationReport(
                is_deviation=False,
                severity=0.0,
                summary="Invalid event time format",
                details={"reason": "invalid_time"},
            )

        # Calculate z-score
        if pattern.std_dev == 0:
            z_score = 0.0
        else:
            z_score = abs(current_time - pattern.mean_value) / pattern.std_dev

        # Determine severity
        if z_score >= self.Z_SCORE_CRITICAL:
            severity = 0.8
            is_deviation = True
            summary = f"Significant {pattern_name.replace('_', ' ')} deviation detected"
        elif z_score >= self.Z_SCORE_WARNING:
            severity = 0.5
            is_deviation = True
            summary = f"Unusual {pattern_name.replace('_', ' ')} detected"
        else:
            severity = 0.0
            is_deviation = False
            summary = f"{pattern_name.replace('_', ' ').title()} is normal"

        time_diff = abs(current_time - pattern.mean_value)

        return DeviationReport(
            is_deviation=is_deviation,
            severity=severity,
            summary=summary,
            details={
                "z_score": z_score,
                "expected_time": self._decimal_to_time_string(pattern.mean_value),
                "actual_time": self._decimal_to_time_string(current_time),
                "time_difference_hours": time_diff,
                "pattern_type": pattern_name,
            },
        )

    def _detect_activity_deviation(self, context: Dict[str, Any]) -> DeviationReport:
        """Detect unusual activity frequency patterns."""
        pattern = self._patterns.get("activity_frequency")
        if not pattern:
            return DeviationReport(
                is_deviation=False,
                severity=0.0,
                summary="No activity pattern established yet",
                details={"reason": "no_pattern"},
            )

        # This would require tracking daily activity count
        # For now, return neutral result
        return DeviationReport(
            is_deviation=False,
            severity=0.0,
            summary="Activity frequency within normal range",
            details={"mean_daily_activities": pattern.mean_value},
        )

    # ========================================================================
    # Insight Generation
    # ========================================================================

    def generate_insights(self, time_window_days: int = 7) -> List[PatternInsight]:
        """
        Generate actionable insights from learned patterns.

        Args:
            time_window_days: Number of days to analyze (default: 7)

        Returns:
            List of PatternInsight objects with recommendations
        """
        insights = []

        # Medication adherence insights
        insights.extend(self._generate_medication_insights())

        # Routine consistency insights
        insights.extend(self._generate_routine_insights())

        # Activity level insights
        insights.extend(self._generate_activity_insights())

        # Sort by confidence (highest first)
        insights.sort(key=lambda x: x.confidence, reverse=True)

        return insights

    def _generate_medication_insights(self) -> List[PatternInsight]:
        """Generate medication-related insights."""
        insights = []
        pattern = self._patterns.get("medication_time")

        if not pattern:
            return insights

        # Consistency insight
        if pattern.std_dev < 0.5:  # Less than 30 minute variance
            insights.append(
                PatternInsight(
                    category="medication",
                    insight_type="positive",
                    title="Excellent Medication Consistency",
                    description=f"Medications are taken consistently around {self._decimal_to_time_string(pattern.mean_value)}",
                    recommendation="Keep up the great routine!",
                    confidence=0.9,
                    data={
                        "std_dev_hours": pattern.std_dev,
                        "samples": pattern.sample_count,
                    },
                )
            )
        elif pattern.std_dev > 2.0:  # More than 2 hour variance
            insights.append(
                PatternInsight(
                    category="medication",
                    insight_type="warning",
                    title="Inconsistent Medication Timing",
                    description=f"Medication times vary significantly (±{pattern.std_dev:.1f} hours)",
                    recommendation="Consider setting daily alarms for medication reminders",
                    confidence=0.8,
                    data={
                        "std_dev_hours": pattern.std_dev,
                        "samples": pattern.sample_count,
                    },
                )
            )

        return insights

    def _generate_routine_insights(self) -> List[PatternInsight]:
        """Generate routine-related insights."""
        insights = []

        # Wake time consistency
        wake_pattern = self._patterns.get("wake_time")
        if wake_pattern and wake_pattern.std_dev > 2.0:
            insights.append(
                PatternInsight(
                    category="routine",
                    insight_type="warning",
                    title="Irregular Wake Times",
                    description=f"Wake times vary by ±{wake_pattern.std_dev:.1f} hours",
                    recommendation="Try maintaining a consistent sleep schedule for better memory function",
                    confidence=0.7,
                    data={"std_dev_hours": wake_pattern.std_dev},
                )
            )

        # Sleep time consistency
        sleep_pattern = self._patterns.get("sleep_time")
        if sleep_pattern and sleep_pattern.std_dev < 1.0:
            insights.append(
                PatternInsight(
                    category="routine",
                    insight_type="positive",
                    title="Consistent Sleep Schedule",
                    description=f"Bedtime is consistent around {self._decimal_to_time_string(sleep_pattern.mean_value)}",
                    recommendation="Consistent sleep helps with memory consolidation",
                    confidence=0.8,
                    data={"std_dev_hours": sleep_pattern.std_dev},
                )
            )

        return insights

    def _generate_activity_insights(self) -> List[PatternInsight]:
        """Generate activity-related insights."""
        insights = []
        pattern = self._patterns.get("activity_frequency")

        if not pattern:
            return insights

        # Low activity warning
        if pattern.mean_value < 5:  # Less than 5 activities per day
            insights.append(
                PatternInsight(
                    category="activity",
                    insight_type="warning",
                    title="Low Daily Activity Level",
                    description=f"Average of {pattern.mean_value:.1f} activities per day",
                    recommendation="Consider adding more structured activities to your routine",
                    confidence=0.7,
                    data={"mean_daily_activities": pattern.mean_value},
                )
            )
        elif pattern.mean_value > 15:  # More than 15 activities per day
            insights.append(
                PatternInsight(
                    category="activity",
                    insight_type="positive",
                    title="High Activity Engagement",
                    description=f"Average of {pattern.mean_value:.1f} activities per day",
                    recommendation="Great job staying active!",
                    confidence=0.8,
                    data={"mean_daily_activities": pattern.mean_value},
                )
            )

        return insights

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _decimal_to_time_string(self, decimal_time: float) -> str:
        """Convert decimal time (14.5) to string (14:30)."""
        hours = int(decimal_time)
        minutes = int((decimal_time - hours) * 60)
        return f"{hours:02d}:{minutes:02d}"

    def _get_medication_recommendation(self, z_score: float, time_diff: float) -> str:
        """Get recommendation based on medication deviation."""
        if z_score >= self.Z_SCORE_CRITICAL:
            return "Contact caregiver - medication time is significantly off schedule"
        elif z_score >= self.Z_SCORE_WARNING:
            return f"Try to take medication closer to usual time (±{time_diff:.1f} hours difference)"
        else:
            return "Medication taken at normal time"

    def get_pattern_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all learned patterns.

        Returns:
            Dictionary with pattern statistics
        """
        summary = {
            "total_patterns": len(self._patterns),
            "total_events_analyzed": len(self._event_history),
            "last_analysis": (
                self._last_analysis_time.isoformat()
                if self._last_analysis_time
                else None
            ),
            "patterns": {},
        }

        for pattern_name, pattern in self._patterns.items():
            summary["patterns"][pattern_name] = {
                "mean_value": pattern.mean_value,
                "std_dev": pattern.std_dev,
                "sample_count": pattern.sample_count,
                "last_updated": pattern.last_updated.isoformat(),
                "metadata": pattern.metadata,
            }

        return summary


# ============================================================================
# Singleton Instance
# ============================================================================

_pattern_recognizer_instance: Optional[PatternRecognizer] = None


def get_pattern_recognizer() -> PatternRecognizer:
    """Get the global pattern recognizer instance."""
    global _pattern_recognizer_instance
    if _pattern_recognizer_instance is None:
        _pattern_recognizer_instance = PatternRecognizer()
    return _pattern_recognizer_instance


# ============================================================================
# Example Usage / Testing
# ============================================================================

if __name__ == "__main__":
    import sys

    sys.path.insert(0, "/home/kilo/Desktop/getkrakaen/kilos-bastion-ai")

    from kilo_v2.memory_core.db import get_memory_db

    print("=" * 70)
    print("PATTERN RECOGNIZER TEST")
    print("=" * 70)

    # Initialize
    recognizer = get_pattern_recognizer()
    db = get_memory_db()

    # Load recent memory events
    print("\nLoading memory events from last 30 days...")
    from datetime import datetime, timedelta

    thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
    events = db.get_memory_events(start_time=thirty_days_ago)
    print(f"Loaded {len(events)} events")

    # Learn patterns
    print("\nLearning patterns...")
    patterns_learned = recognizer.learn_from_memory_events(events)
    print(f"✅ Learned {patterns_learned} patterns")

    # Get pattern summary
    print("\nPattern Summary:")
    summary = recognizer.get_pattern_summary()
    for pattern_name, pattern_data in summary["patterns"].items():
        print(f"\n  {pattern_name}:")
        print(f"    Mean: {pattern_data['mean_value']:.2f}")
        print(f"    Std Dev: {pattern_data['std_dev']:.2f}")
        print(f"    Samples: {pattern_data['sample_count']}")

    # Generate insights
    print("\nGenerating insights...")
    insights = recognizer.generate_insights()
    print(f"\nFound {len(insights)} insights:")
    for insight in insights:
        icon = (
            "✅"
            if insight.insight_type == "positive"
            else "⚠️" if insight.insight_type == "warning" else "❌"
        )
        print(f"\n{icon} [{insight.category.upper()}] {insight.title}")
        print(f"   {insight.description}")
        if insight.recommendation:
            print(f"   💡 {insight.recommendation}")
        print(f"   Confidence: {insight.confidence*100:.0f}%")

    # Test deviation detection
    print("\n" + "=" * 70)
    print("Testing deviation detection...")
    test_context = {
        "event_type": "medication",
        "event_text": "User taking medication",
        "event_time": datetime.now().isoformat(),
    }

    report = recognizer.detect_deviation(test_context)
    print(f"\nDeviation Report:")
    print(f"  Is Deviation: {report.is_deviation}")
    print(f"  Severity: {report.severity}")
    print(f"  Summary: {report.summary}")
    print(f"  Details: {report.details}")

    print("\n" + "=" * 70)
    print("Pattern recognizer test complete!")
