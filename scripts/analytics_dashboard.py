#!/usr/bin/env python3
"""
AI Memory Assistant - Offline Analytics Dashboard
Air-gapped compatible - analyzes data locally without external services
"""

import sys
import json
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, List, Any, Optional

# Optional imports for visualizations
try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

# Add repository root to path
repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from ai_brain.db import get_session
from ai_brain.models import Memory

# Try to import optional models
try:
    from microservice.models import Med as Medication
    HAS_MEDICATION = True
except ImportError:
    HAS_MEDICATION = False
    Medication = None

try:
    from microservice.models import Reminder
    HAS_REMINDER = True
except ImportError:
    HAS_REMINDER = False
    Reminder = None

try:
    from microservice.models import Transaction
    HAS_TRANSACTION = True
except ImportError:
    HAS_TRANSACTION = False
    Transaction = None

# Try to import Conversation if it exists
try:
    from ai_brain.models import Conversation
    HAS_CONVERSATION = True
except ImportError:
    HAS_CONVERSATION = False
    Conversation = None

# Try to import User if it exists
try:
    from ai_brain.models import User
    HAS_USER = True
except ImportError:
    HAS_USER = False
    User = None


class AnalyticsDashboard:
    """Offline analytics dashboard for the AI Memory Assistant"""

    def __init__(self):
        self.session = get_session()
        self.data = {}
        self.insights = []

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive analytics report"""
        print("📊 Generating Analytics Report...")

        self._collect_data()
        self._analyze_patterns()
        self._generate_insights()
        self._create_visualizations()

        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": self._generate_summary(),
            "metrics": self.data,
            "insights": self.insights,
            "recommendations": self._generate_recommendations()
        }

        return report

    def _collect_data(self):
        """Collect all analytics data"""
        print("  📥 Collecting data...")

        # Memory analytics
        memories = self.session.query(Memory).all()
        self.data["total_memories"] = len(memories)

        # Conversation analytics
        if HAS_CONVERSATION:
            conversations = self.session.query(Conversation).all()
            self.data["total_conversations"] = len(conversations)
        else:
            conversations = []
            self.data["total_conversations"] = 0

        # Medication analytics
        if HAS_MEDICATION:
            medications = self.session.query(Medication).all()
            self.data["total_medications"] = len(medications)
        else:
            medications = []
            self.data["total_medications"] = 0

        # Reminder analytics
        if HAS_REMINDER:
            reminders = self.session.query(Reminder).all()
            self.data["total_reminders"] = len(reminders)
            self.data["completed_reminders"] = len([r for r in reminders if r.sent])  # Using 'sent' as completed indicator
        else:
            reminders = []
            self.data["total_reminders"] = 0
            self.data["completed_reminders"] = 0

        # Time-based analytics
        self._analyze_time_patterns(memories, conversations)

        # Content analytics
        self._analyze_content_patterns(memories)

        # User engagement
        self._analyze_user_engagement(conversations, memories)

    def _analyze_time_patterns(self, memories: List[Memory], conversations: List[Conversation]):
        """Analyze time-based patterns"""
        # Memories by day of week
        memory_days = [m.created_at.weekday() for m in memories if m.created_at]
        self.data["memories_by_day"] = dict(Counter(memory_days))

        # Memories by hour
        memory_hours = [m.created_at.hour for m in memories if m.created_at]
        self.data["memories_by_hour"] = dict(Counter(memory_hours))

        # Conversation frequency
        if HAS_CONVERSATION and conversations:
            conv_dates = [c.created_at.date() for c in conversations if c.created_at]
            self.data["conversations_by_date"] = dict(Counter(conv_dates))
        else:
            self.data["conversations_by_date"] = {}

        # Recent activity (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_memories = [m for m in memories if m.created_at and m.created_at > thirty_days_ago]
        if HAS_CONVERSATION:
            recent_conversations = [c for c in conversations if c.created_at and c.created_at > thirty_days_ago]
        else:
            recent_conversations = []

        self.data["recent_activity"] = {
            "memories_last_30_days": len(recent_memories),
            "conversations_last_30_days": len(recent_conversations),
            "avg_memories_per_day": len(recent_memories) / 30,
            "avg_conversations_per_day": len(recent_conversations) / 30
        }

    def _analyze_content_patterns(self, memories: List[Memory]):
        """Analyze content patterns in memories"""
        # Memory types distribution
        memory_types = [m.memory_type for m in memories]
        self.data["memory_types"] = dict(Counter(memory_types))

        # Importance distribution
        importance_levels = [m.importance for m in memories if m.importance]
        self.data["importance_distribution"] = dict(Counter(importance_levels))

        # Content length analysis
        content_lengths = [len(m.content) for m in memories if m.content]
        self.data["content_stats"] = {
            "avg_length": sum(content_lengths) / len(content_lengths) if content_lengths else 0,
            "max_length": max(content_lengths) if content_lengths else 0,
            "min_length": min(content_lengths) if content_lengths else 0
        }

        # Keyword analysis (simple word frequency)
        all_text = " ".join([m.content.lower() for m in memories if m.content])
        words = all_text.split()
        # Remove common stop words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must", "can", "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them", "my", "your", "his", "its", "our", "their"}
        filtered_words = [word for word in words if word not in stop_words and len(word) > 2]
        self.data["top_keywords"] = dict(Counter(filtered_words).most_common(20))

    def _analyze_user_engagement(self, conversations: List[Conversation], memories: List[Memory]):
        """Analyze user engagement patterns"""
        # Conversation length analysis
        message_counts = [len(c.messages) for c in conversations if c.messages]
        self.data["conversation_stats"] = {
            "avg_messages_per_conversation": sum(message_counts) / len(message_counts) if message_counts else 0,
            "max_messages": max(message_counts) if message_counts else 0,
            "total_messages": sum(message_counts)
        }

        # Memory creation patterns
        if memories:
            first_memory = min([m.created_at for m in memories if m.created_at])
            last_memory = max([m.created_at for m in memories if m.created_at])
            days_active = (last_memory - first_memory).days if first_memory and last_memory else 0

            self.data["engagement_stats"] = {
                "days_active": days_active,
                "memories_per_day": len(memories) / max(days_active, 1),
                "first_memory_date": first_memory.isoformat() if first_memory else None,
                "last_memory_date": last_memory.isoformat() if last_memory else None
            }

    def _analyze_patterns(self):
        """Analyze patterns and trends"""
        # Growth trends
        self._analyze_growth_trends()

        # Peak usage times
        self._analyze_peak_times()

        # Content themes
        self._analyze_content_themes()

    def _analyze_growth_trends(self):
        """Analyze growth trends over time"""
        memories = self.session.query(Memory).filter(Memory.created_at.isnot(None)).all()
        conversations = []
        if HAS_CONVERSATION:
            conversations = self.session.query(Conversation).filter(Conversation.created_at.isnot(None)).all()

        # Group by month
        memory_months = defaultdict(int)
        conversation_months = defaultdict(int)

        for memory in memories:
            if memory.created_at:
                month_key = memory.created_at.strftime("%Y-%m")
                memory_months[month_key] += 1

        for conv in conversations:
            if conv.created_at:
                month_key = conv.created_at.strftime("%Y-%m")
                conversation_months[month_key] += 1

        self.data["growth_trends"] = {
            "memories_by_month": dict(memory_months),
            "conversations_by_month": dict(conversation_months)
        }

    def _analyze_peak_times(self):
        """Analyze peak usage times"""
        memories = self.session.query(Memory).filter(Memory.created_at.isnot(None)).all()

        # Peak hours
        hour_counts = defaultdict(int)
        for memory in memories:
            if memory.created_at:
                hour_counts[memory.created_at.hour] += 1

        # Peak days
        day_counts = defaultdict(int)
        for memory in memories:
            if memory.created_at:
                day_counts[memory.created_at.weekday()] += 1

        peak_hour = max(hour_counts.items(), key=lambda x: x[1]) if hour_counts else (0, 0)
        peak_day = max(day_counts.items(), key=lambda x: x[1]) if day_counts else (0, 0)

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        self.data["peak_usage"] = {
            "peak_hour": peak_hour[0],
            "peak_hour_count": peak_hour[1],
            "peak_day": day_names[peak_day[0]],
            "peak_day_count": peak_day[1]
        }

    def _analyze_content_themes(self):
        """Analyze content themes and categories"""
        memories = self.session.query(Memory).all()

        # Categorize by themes
        themes = defaultdict(int)
        health_keywords = {"medication", "doctor", "health", "pain", "symptom", "treatment"}
        habit_keywords = {"exercise", "habit", "routine", "practice", "daily"}
        social_keywords = {"friend", "family", "meeting", "social", "relationship"}
        work_keywords = {"work", "job", "project", "meeting", "deadline"}

        for memory in memories:
            if memory.content:
                content_lower = memory.content.lower()

                if any(keyword in content_lower for keyword in health_keywords):
                    themes["health"] += 1
                elif any(keyword in content_lower for keyword in habit_keywords):
                    themes["habits"] += 1
                elif any(keyword in content_lower for keyword in social_keywords):
                    themes["social"] += 1
                elif any(keyword in content_lower for keyword in work_keywords):
                    themes["work"] += 1
                else:
                    themes["other"] += 1

        self.data["content_themes"] = dict(themes)

    def _generate_insights(self):
        """Generate actionable insights"""
        self.insights = []

        # Memory creation insights
        if self.data.get("recent_activity", {}).get("avg_memories_per_day", 0) < 1:
            self.insights.append({
                "type": "engagement",
                "priority": "high",
                "title": "Low Memory Creation Rate",
                "description": "You're creating less than 1 memory per day on average. Consider setting daily reflection reminders.",
                "action": "Set up daily prompts to record important moments and thoughts."
            })

        # Conversation insights
        if self.data.get("total_conversations", 0) > 0:
            avg_messages = self.data.get("conversation_stats", {}).get("avg_messages_per_conversation", 0)
            if avg_messages < 3:
                self.insights.append({
                    "type": "engagement",
                    "priority": "medium",
                    "title": "Short Conversations",
                    "description": "Your conversations with the AI are quite brief. Try asking more detailed questions!",
                    "action": "Experiment with deeper, more specific queries to get richer responses."
                })

        # Peak usage insights
        peak_hour = self.data.get("peak_usage", {}).get("peak_hour", 0)
        if 22 <= peak_hour or peak_hour <= 6:
            self.insights.append({
                "type": "wellness",
                "priority": "medium",
                "title": "Late Night Usage",
                "description": "You tend to use the system late at night. Consider morning reflection routines.",
                "action": "Try starting your day with a morning check-in instead of evening sessions."
            })

        # Content diversity insights
        memory_types = self.data.get("memory_types", {})
        if len(memory_types) < 3:
            self.insights.append({
                "type": "diversity",
                "priority": "low",
                "title": "Limited Memory Types",
                "description": "You're focusing on few types of memories. Try recording different aspects of your life.",
                "action": "Experiment with logging habits, health notes, and social interactions."
            })

        # Health tracking insights
        if self.data.get("content_themes", {}).get("health", 0) == 0:
            self.insights.append({
                "type": "health",
                "priority": "medium",
                "title": "Health Tracking Opportunity",
                "description": "You haven't recorded any health-related memories yet.",
                "action": "Consider tracking medications, symptoms, or wellness activities."
            })

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate overall summary"""
        total_memories = self.data.get("total_memories", 0)
        total_conversations = self.data.get("total_conversations", 0)
        recent_activity = self.data.get("recent_activity", {})

        # Calculate engagement score (0-100)
        engagement_score = min(100, (
            (recent_activity.get("avg_memories_per_day", 0) * 20) +
            (recent_activity.get("avg_conversations_per_day", 0) * 30) +
            (len(self.data.get("memory_types", {})) * 10) +
            min(20, total_memories / 5)
        ))

        # Determine activity level
        if engagement_score >= 80:
            activity_level = "Highly Active"
        elif engagement_score >= 60:
            activity_level = "Moderately Active"
        elif engagement_score >= 40:
            activity_level = "Lightly Active"
        else:
            activity_level = "Getting Started"

        return {
            "total_memories": total_memories,
            "total_conversations": total_conversations,
            "engagement_score": round(engagement_score, 1),
            "activity_level": activity_level,
            "days_active": self.data.get("engagement_stats", {}).get("days_active", 0),
            "insights_count": len(self.insights)
        }

    def _generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generate personalized recommendations"""
        recommendations = []

        # Based on usage patterns
        if self.data.get("total_memories", 0) < 10:
            recommendations.append({
                "category": "getting_started",
                "title": "Build Your Memory Foundation",
                "description": "Start by recording 5-10 important memories to establish patterns.",
                "priority": "high"
            })

        # Based on peak usage
        peak_hour = self.data.get("peak_usage", {}).get("peak_hour", 12)
        if peak_hour < 6 or peak_hour > 22:
            recommendations.append({
                "category": "wellness",
                "title": "Optimize Usage Timing",
                "description": "Consider shifting some activities to daytime hours for better balance.",
                "priority": "medium"
            })

        # Based on content diversity
        themes = self.data.get("content_themes", {})
        if len([t for t in themes.values() if t > 0]) < 3:
            recommendations.append({
                "category": "diversity",
                "title": "Expand Memory Categories",
                "description": "Try recording memories from different areas of your life.",
                "priority": "medium"
            })

        # Default recommendations
        if not recommendations:
            recommendations.extend([
                {
                    "category": "engagement",
                    "title": "Set Daily Goals",
                    "description": "Establish a daily routine for memory recording and reflection.",
                    "priority": "medium"
                },
                {
                    "category": "exploration",
                    "title": "Explore Advanced Features",
                    "description": "Try voice input, knowledge graph visualization, and progress tracking.",
                    "priority": "low"
                }
            ])

        return recommendations

    def _create_visualizations(self):
        """Create data visualizations (if matplotlib available)"""
        if not HAS_MATPLOTLIB:
            print("  ⚠️ Matplotlib not available, skipping visualizations")
            return

        try:
            # Memory types pie chart
            memory_types = self.data.get("memory_types", {})
            if memory_types:
                plt.figure(figsize=(8, 6))
                plt.pie(memory_types.values(), labels=memory_types.keys(), autopct='%1.1f%%')
                plt.title('Memory Types Distribution')
                plt.savefig('docs/memory_types_chart.png')
                plt.close()

            # Activity timeline
            growth_trends = self.data.get("growth_trends", {})
            memories_by_month = growth_trends.get("memories_by_month", {})
            if memories_by_month:
                months = sorted(memories_by_month.keys())
                counts = [memories_by_month[month] for month in months]

                plt.figure(figsize=(10, 6))
                plt.plot(months, counts, marker='o')
                plt.title('Memory Creation Over Time')
                plt.xlabel('Month')
                plt.ylabel('Number of Memories')
                plt.xticks(rotation=45)
                plt.tight_layout()
                plt.savefig('docs/activity_timeline.png')
                plt.close()

        except ImportError:
            print("  ⚠️ Matplotlib not available, skipping visualizations")
        except Exception as e:
            print(f"  ⚠️ Error creating visualizations: {e}")

    def export_report(self, format: str = "json") -> str:
        """Export the analytics report"""
        report = self.generate_report()

        if format == "json":
            return json.dumps(report, indent=2, default=str)
        elif format == "markdown":
            return self._format_markdown_report(report)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _format_markdown_report(self, report: Dict[str, Any]) -> str:
        """Format report as Markdown"""
        md = f"""# AI Memory Assistant - Analytics Report

Generated on: {report['generated_at']}

## 📊 Summary

- **Total Memories**: {report['summary']['total_memories']}
- **Total Conversations**: {report['summary']['total_conversations']}
- **Engagement Score**: {report['summary']['engagement_score']}/100
- **Activity Level**: {report['summary']['activity_level']}
- **Days Active**: {report['summary']['days_active']}
- **Insights Generated**: {report['summary']['insights_count']}

## 🔍 Key Metrics

### Memory Analytics
- **Memory Types**: {report['metrics'].get('memory_types', {})}
- **Importance Distribution**: {report['metrics'].get('importance_distribution', {})}
- **Content Stats**: {report['metrics'].get('content_stats', {})}

### Activity Patterns
- **Peak Usage**: {report['metrics'].get('peak_usage', {})}
- **Recent Activity**: {report['metrics'].get('recent_activity', {})}

### Content Themes
{chr(10).join([f"- **{theme.title()}**: {count}" for theme, count in report['metrics'].get('content_themes', {}).items()])}

## 💡 Insights

{chr(10).join([f"### {insight['priority'].title()} Priority: {insight['title']}" + chr(10) + f"{insight['description']}" + chr(10) + f"**Action**: {insight['action']}" + chr(10) for insight in report['insights']])}

## 🎯 Recommendations

{chr(10).join([f"### {rec['category'].replace('_', ' ').title()}" + chr(10) + f"**{rec['title']}**" + chr(10) + f"{rec['description']}" + chr(10) + f"*Priority: {rec['priority'].title()}*" + chr(10) for rec in report['recommendations']])}

---
*Report generated by AI Memory Assistant Analytics Dashboard*
"""

        return md


def main():
    """Main entry point"""
    print("🤖 AI Memory Assistant - Offline Analytics Dashboard")
    print("=" * 60)

    # Generate analytics report
    dashboard = AnalyticsDashboard()
    report = dashboard.generate_report()

    # Print summary
    summary = report["summary"]
    print("\n📊 SUMMARY:")
    print(f"  Total Memories: {summary['total_memories']}")
    print(f"  Total Conversations: {summary['total_conversations']}")
    print(f"  Engagement Score: {summary['engagement_score']}/100")
    print(f"  Activity Level: {summary['activity_level']}")
    print(f"  Insights Generated: {summary['insights_count']}")

    # Export reports
    print("\n📄 Exporting Reports...")

    # JSON report
    with open("analytics_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    print("  ✓ JSON report: analytics_report.json")

    # Markdown report
    md_report = dashboard.export_report("markdown")
    with open("analytics_report.md", "w") as f:
        f.write(md_report)
    print("  ✓ Markdown report: analytics_report.md")

    # Print top insights
    if report["insights"]:
        print("\n💡 TOP INSIGHTS:")
        for i, insight in enumerate(report["insights"][:3], 1):
            print(f"  {i}. {insight['title']} ({insight['priority']})")

    print("\n✅ Analytics complete! Check analytics_report.md for full details.")
    print("=" * 60)


if __name__ == "__main__":
    main()