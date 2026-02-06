"""
Interest Tracker Plugin for Kilo Guardian
Learns user interests and provides educational content during briefings.
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from plugins.base_plugin import BasePlugin


class InterestTracker(BasePlugin):
    """
    Interest tracking plugin for Kilo Guardian.
    Learns from user interactions, fetches relevant content, teaches new things.
    """

    def __init__(self):
        super().__init__()
        self.db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "user_data",
            "interests.db",
        )
        self._init_database()

    def _init_database(self):
        """Initialize the interests database."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # User interests table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_interests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                topic TEXT NOT NULL,
                relevance_score REAL DEFAULT 1.0,
                last_mentioned TEXT,
                mention_count INTEGER DEFAULT 1,
                source TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Learning content table (cached educational content)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS learning_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                content_type TEXT,
                title TEXT,
                summary TEXT,
                url TEXT,
                source TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                shown_to_user INTEGER DEFAULT 0
            )
        """
        )

        # User's knowledge level table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                skill_level TEXT DEFAULT 'beginner',
                last_taught TEXT,
                teaching_count INTEGER DEFAULT 0,
                user_feedback TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        conn.commit()
        conn.close()

    def get_name(self) -> str:
        return "interest_tracker"

    def get_keywords(self) -> list:
        return [
            "interest",
            "learn",
            "teach",
            "education",
            "hobby",
            "topic",
            "knowledge",
            "curious",
            "explain",
            "tell me about",
            "what is",
            "how does",
        ]

    def run(self, query: str) -> dict:
        """Main execution method."""
        query_lower = query.lower()

        try:
            # Show interests
            if "show" in query_lower and "interest" in query_lower:
                return self._show_interests()

            # Add interest
            if "add interest" in query_lower or "track interest" in query_lower:
                return self._handle_add_interest(query)

            # Teach me something
            if "teach" in query_lower or "learn something" in query_lower:
                return self._teach_something_new()

            # Get daily learning content
            if "daily" in query_lower and (
                "learn" in query_lower or "fact" in query_lower
            ):
                return self._get_daily_learning()

            # Default: show help
            return self._get_help()

        except Exception as e:
            return {"type": "error", "tool": "interest_tracker", "error": str(e)}

    def track_interest(
        self, category: str, topic: str, source: str = "user_input"
    ) -> bool:
        """Track a user interest."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if interest already exists
        cursor.execute(
            "SELECT id, relevance_score, mention_count FROM user_interests WHERE topic = ?",
            (topic,),
        )
        existing = cursor.fetchone()

        if existing:
            # Update existing interest
            interest_id, score, count = existing
            new_score = min(10.0, score + 0.5)  # Increase relevance, cap at 10
            cursor.execute(
                """
                UPDATE user_interests 
                SET relevance_score = ?, mention_count = ?, last_mentioned = ?
                WHERE id = ?
                """,
                (new_score, count + 1, datetime.now().isoformat(), interest_id),
            )
        else:
            # Add new interest
            cursor.execute(
                """
                INSERT INTO user_interests (category, topic, source, last_mentioned)
                VALUES (?, ?, ?, ?)
                """,
                (category, topic, source, datetime.now().isoformat()),
            )

        conn.commit()
        conn.close()
        return True

    def _show_interests(self) -> dict:
        """Show all tracked interests."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT category, topic, relevance_score, mention_count, last_mentioned
            FROM user_interests
            ORDER BY relevance_score DESC, last_mentioned DESC
            LIMIT 20
            """
        )

        interests = []
        for category, topic, score, count, last_mentioned in cursor.fetchall():
            interests.append(
                {
                    "category": category,
                    "topic": topic,
                    "relevance": round(score, 2),
                    "mentions": count,
                    "last_mentioned": last_mentioned,
                }
            )

        conn.close()

        return {
            "type": "interests_list",
            "tool": "interest_tracker",
            "interests": interests,
            "total_interests": len(interests),
        }

    def _handle_add_interest(self, query: str) -> dict:
        """Handle adding a new interest."""
        return {
            "type": "interactive_form",
            "tool": "interest_tracker",
            "form": {
                "title": "Add New Interest",
                "fields": [
                    {
                        "name": "category",
                        "type": "select",
                        "label": "Category",
                        "options": [
                            "Technology",
                            "Science",
                            "Art",
                            "Music",
                            "Sports",
                            "Cooking",
                            "Finance",
                            "Health",
                            "History",
                            "Literature",
                            "Other",
                        ],
                        "required": True,
                    },
                    {
                        "name": "topic",
                        "type": "text",
                        "label": "Topic",
                        "required": True,
                        "placeholder": "e.g., Machine Learning, Renaissance Art",
                    },
                ],
            },
            "message": "Tell me about something you're interested in learning",
        }

    def add_interest(self, category: str, topic: str) -> bool:
        """Add a new interest from form submission."""
        return self.track_interest(category, topic, "manual_entry")

    def _teach_something_new(self) -> dict:
        """Teach the user something based on their interests."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get top interests
        cursor.execute(
            """
            SELECT topic, category FROM user_interests
            ORDER BY relevance_score DESC, last_mentioned DESC
            LIMIT 5
            """
        )

        interests = cursor.fetchall()

        if not interests:
            conn.close()
            return {
                "type": "learning_content",
                "tool": "interest_tracker",
                "message": "I don't know your interests yet. Tell me what you'd like to learn about!",
                "suggestion": "Add some interests so I can tailor content for you.",
            }

        # Pick a random interest from top 5
        import random

        topic, category = random.choice(interests)

        # Check if we have cached content
        cursor.execute(
            """
            SELECT title, summary, url, source FROM learning_content
            WHERE topic LIKE ? AND shown_to_user = 0
            LIMIT 1
            """,
            (f"%{topic}%",),
        )

        cached = cursor.fetchone()

        if cached:
            title, summary, url, source = cached
            # Mark as shown
            cursor.execute(
                "UPDATE learning_content SET shown_to_user = 1 WHERE title = ?",
                (title,),
            )
            conn.commit()
            conn.close()

            return {
                "type": "learning_content",
                "tool": "interest_tracker",
                "topic": topic,
                "category": category,
                "title": title,
                "summary": summary,
                "url": url,
                "source": source,
            }

        conn.close()

        # Generate educational content (this would call an AI or fetch from web)
        return {
            "type": "learning_content",
            "tool": "interest_tracker",
            "topic": topic,
            "category": category,
            "title": f"Interesting Fact About {topic}",
            "summary": f"Based on your interest in {topic}, here's something fascinating: [AI would generate or fetch relevant content here]",
            "message": "💡 I'm learning about your interests to teach you new things!",
            "note": "Enable web search for AI to fetch real-time educational content.",
        }

    def _get_daily_learning(self) -> dict:
        """Get daily learning content tailored to user interests."""
        return self._teach_something_new()

    def get_briefing_content(self) -> Optional[Dict]:
        """
        Get interesting content for morning briefing.
        Called by briefing plugin to include personalized learning.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get top interest
        cursor.execute(
            """
            SELECT topic, category FROM user_interests
            ORDER BY relevance_score DESC
            LIMIT 1
            """
        )

        result = cursor.fetchone()
        conn.close()

        if not result:
            return None

        topic, category = result

        return {
            "type": "daily_learning",
            "topic": topic,
            "category": category,
            "message": f"Based on your interest in {topic}, here's something to ponder today:",
            "content": f"[AI would generate interesting content about {topic} here]",
        }

    def analyze_user_query(self, query: str) -> None:
        """
        Analyze user query to extract and track interests.
        This method should be called by the reasoning engine.
        """
        query_lower = query.lower()

        # Simple keyword-based interest extraction
        interest_keywords = {
            "Technology": [
                "ai",
                "machine learning",
                "programming",
                "computer",
                "software",
                "tech",
                "robot",
                "automation",
            ],
            "Science": [
                "physics",
                "chemistry",
                "biology",
                "space",
                "astronomy",
                "research",
                "experiment",
            ],
            "Art": [
                "painting",
                "drawing",
                "sculpture",
                "art",
                "artist",
                "gallery",
                "design",
            ],
            "Music": [
                "music",
                "song",
                "instrument",
                "band",
                "concert",
                "album",
                "melody",
            ],
            "Sports": [
                "football",
                "basketball",
                "tennis",
                "game",
                "sport",
                "team",
                "athlete",
            ],
            "Cooking": [
                "recipe",
                "cooking",
                "food",
                "baking",
                "cuisine",
                "chef",
                "meal",
            ],
            "Finance": [
                "money",
                "investment",
                "stock",
                "crypto",
                "budget",
                "finance",
                "trading",
            ],
            "Health": [
                "health",
                "fitness",
                "exercise",
                "nutrition",
                "wellness",
                "medical",
                "diet",
            ],
            "History": [
                "history",
                "historical",
                "ancient",
                "war",
                "civilization",
                "era",
                "century",
            ],
            "Literature": [
                "book",
                "novel",
                "author",
                "reading",
                "literature",
                "poetry",
                "story",
            ],
        }

        # Track any matching interests
        for category, keywords in interest_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    self.track_interest(category, keyword, "query_analysis")
                    break

    def _get_help(self) -> dict:
        """Return help information."""
        return {
            "type": "interest_help",
            "tool": "interest_tracker",
            "content": {
                "message": "Interest Tracker - Learn new things based on your interests",
                "commands": [
                    "show interests - See what topics I've learned you're interested in",
                    "add interest - Manually add a topic you want to learn about",
                    "teach me something - Get educational content based on your interests",
                    "daily learning - Get your daily interesting fact",
                ],
                "features": [
                    "🧠 Automatically learns your interests from conversations",
                    "📚 Provides tailored educational content",
                    "🎯 Tracks knowledge progression",
                    "🌅 Integrates with morning briefings",
                ],
                "note": "I track topics you mention frequently to personalize your learning experience.",
            },
        }

    def execute(self, query: str) -> dict:
        """Execute method for reasoning engine."""
        return self.run(query)
