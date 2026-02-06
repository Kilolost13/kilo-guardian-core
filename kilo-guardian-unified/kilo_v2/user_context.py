# kilo_v2/user_context.py
"""
User Context Manager - Core intelligence layer
Tracks user preferences, conversation history, learned patterns, and tier information.
This layer feeds context to reasoning engine, plugins, and persona system.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("UserContext")


class UserContext:
    """
    Represents a single user's context including:
    - Subscription tier (home/pro/business)
    - Conversation history
    - Learned preferences
    - User-taught facts
    - Environment knowledge (devices, schedules, locations)
    """

    def __init__(self, user_id: str, tier: str = "home", db_path: Optional[str] = None):
        self.user_id = user_id
        self.tier = tier
        self.db_path = db_path or "kilo_data/user_contexts.db"

        # In-memory cache for fast access
        self.conversation_history: List[Dict[str, Any]] = []
        self.preferences: Dict[str, Any] = {}
        self.learned_facts: Dict[str, Any] = {}
        self.environment: Dict[str, Any] = {}

        # Initialize database
        self._init_db()

        # Load existing context
        self._load_from_db()

        logger.info(f"✅ UserContext initialized for user '{user_id}' (tier: {tier})")

    def _init_db(self):
        """Create database tables if they don't exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Conversation history table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                query TEXT NOT NULL,
                response TEXT NOT NULL,
                plugin_used TEXT,
                sentiment TEXT,
                metadata TEXT
            )
        """
        )

        # User preferences table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id TEXT PRIMARY KEY,
                tier TEXT NOT NULL,
                preferences TEXT NOT NULL,
                learned_facts TEXT,
                environment TEXT,
                last_updated REAL NOT NULL
            )
        """
        )

        # Learned patterns table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS learned_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                pattern_data TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                last_seen REAL NOT NULL
            )
        """
        )

        conn.commit()
        conn.close()

    def _load_from_db(self):
        """Load user context from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Load preferences
        cursor.execute(
            """
            SELECT tier, preferences, learned_facts, environment 
            FROM user_preferences 
            WHERE user_id = ?
        """,
            (self.user_id,),
        )

        row = cursor.fetchone()
        if row:
            self.tier = row[0]
            self.preferences = json.loads(row[1]) if row[1] else {}
            self.learned_facts = json.loads(row[2]) if row[2] else {}
            self.environment = json.loads(row[3]) if row[3] else {}

        # Load recent conversation history (last 50 messages)
        cursor.execute(
            """
            SELECT timestamp, query, response, plugin_used, sentiment, metadata
            FROM conversation_history
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 50
        """,
            (self.user_id,),
        )

        self.conversation_history = [
            {
                "timestamp": row[0],
                "query": row[1],
                "response": row[2],
                "plugin_used": row[3],
                "sentiment": row[4],
                "metadata": json.loads(row[5]) if row[5] else {},
            }
            for row in cursor.fetchall()
        ]
        self.conversation_history.reverse()  # Chronological order

        conn.close()

    def add_interaction(
        self,
        query: str,
        response: str,
        plugin_used: Optional[str] = None,
        sentiment: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ):
        """
        Record a query/response interaction.
        This builds conversation history for context-aware responses.
        """
        timestamp = datetime.now().timestamp()

        interaction = {
            "timestamp": timestamp,
            "query": query,
            "response": response,
            "plugin_used": plugin_used,
            "sentiment": sentiment,
            "metadata": metadata or {},
        }

        self.conversation_history.append(interaction)

        # Keep only recent history in memory (last 50)
        if len(self.conversation_history) > 50:
            self.conversation_history.pop(0)

        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO conversation_history 
            (user_id, timestamp, query, response, plugin_used, sentiment, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                self.user_id,
                timestamp,
                query,
                response,
                plugin_used,
                sentiment,
                json.dumps(metadata) if metadata else None,
            ),
        )

        conn.commit()
        conn.close()

        # Learn from this interaction
        self._extract_patterns(query, response, plugin_used)

    def _extract_patterns(self, query: str, response: str, plugin_used: Optional[str]):
        """
        Analyze interaction to learn user patterns.
        This is where the AI "learns" about the user over time.
        """
        query_lower = query.lower()

        # Learn preferred plugins
        if plugin_used:
            if "preferred_plugins" not in self.preferences:
                self.preferences["preferred_plugins"] = {}

            plugin_count = self.preferences["preferred_plugins"].get(plugin_used, 0)
            self.preferences["preferred_plugins"][plugin_used] = plugin_count + 1

        # Learn time patterns (when user asks certain things)
        hour = datetime.now().hour
        if "query_time_patterns" not in self.preferences:
            self.preferences["query_time_patterns"] = {}

        time_slot = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"
        if time_slot not in self.preferences["query_time_patterns"]:
            self.preferences["query_time_patterns"][time_slot] = []

        self.preferences["query_time_patterns"][time_slot].append(plugin_used or "chat")

        # Learn verbosity preference (does user ask follow-up questions?)
        if len(self.conversation_history) > 1:
            prev = self.conversation_history[-2]
            time_diff = datetime.now().timestamp() - prev["timestamp"]

            # Quick follow-up suggests they want more detail
            if time_diff < 120:  # Within 2 minutes
                if "wants_detail" not in self.preferences:
                    self.preferences["wants_detail"] = 0
                self.preferences["wants_detail"] += 1

        # Auto-save preferences periodically
        if len(self.conversation_history) % 5 == 0:
            self._save_preferences()

    def _save_preferences(self):
        """Persist preferences to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO user_preferences
            (user_id, tier, preferences, learned_facts, environment, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                self.user_id,
                self.tier,
                json.dumps(self.preferences),
                json.dumps(self.learned_facts),
                json.dumps(self.environment),
                datetime.now().timestamp(),
            ),
        )

        conn.commit()
        conn.close()

    def set_preference(self, key: str, value: Any):
        """Explicitly set a user preference."""
        self.preferences[key] = value
        self._save_preferences()
        logger.info(f"Set preference for user '{self.user_id}': {key} = {value}")

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        return self.preferences.get(key, default)

    def teach_fact(self, fact_key: str, fact_value: Any, category: str = "general"):
        """
        User teaches the AI a fact about themselves or their environment.
        Example: "My drone is a DJI Mavic 3" -> learned_facts['drone']['model'] = 'DJI Mavic 3'
        """
        if category not in self.learned_facts:
            self.learned_facts[category] = {}

        self.learned_facts[category][fact_key] = {
            "value": fact_value,
            "learned_at": datetime.now().isoformat(),
            "confidence": 1.0,  # User-provided facts are 100% confident
        }

        self._save_preferences()
        logger.info(
            f"User '{self.user_id}' taught fact: {category}.{fact_key} = {fact_value}"
        )

    def get_fact(self, fact_key: str, category: str = "general") -> Optional[Any]:
        """Retrieve a learned fact."""
        if category in self.learned_facts and fact_key in self.learned_facts[category]:
            return self.learned_facts[category][fact_key]["value"]
        return None

    def update_environment(self, key: str, value: Any):
        """
        Update knowledge about user's environment.
        Examples: devices, locations, schedules, home layout
        """
        self.environment[key] = {
            "value": value,
            "updated_at": datetime.now().isoformat(),
        }
        self._save_preferences()

    def get_context_summary(self, include_history: bool = True) -> Dict[str, Any]:
        """
        Generate a context summary to pass to reasoning engine and plugins.
        This is the key method that feeds context downstream.
        """
        summary = {
            "user_id": self.user_id,
            "tier": self.tier,
            "preferences": self.preferences,
            "environment": self.environment,
            "learned_facts": self.learned_facts,
        }

        if include_history and self.conversation_history:
            # Include last 5 interactions for immediate context
            summary["recent_history"] = self.conversation_history[-5:]

            # Summarize patterns
            summary["patterns"] = {
                "most_used_plugins": self._get_top_plugins(5),
                "typical_query_time": self._get_typical_time(),
                "interaction_count": len(self.conversation_history),
            }

        return summary

    def get_prompt_context(self, max_history: int = 3) -> str:
        """
        Generate natural language context to inject into LLM prompts.
        This helps the AI understand the user better.
        """
        context_parts = []

        # User tier context
        tier_desc = {
            "home": "a home user",
            "pro": "a professional user with technical expertise",
            "business": "an enterprise customer requiring formal communication",
        }
        context_parts.append(f"User is {tier_desc.get(self.tier, 'a user')}.")

        # Learned facts
        if self.learned_facts:
            facts_str = []
            for category, facts in self.learned_facts.items():
                for key, data in facts.items():
                    facts_str.append(f"{key}: {data['value']}")
            if facts_str:
                context_parts.append(f"Known facts: {'; '.join(facts_str[:5])}")

        # Preferences
        if self.preferences.get("wants_detail", 0) > 5:
            context_parts.append("User prefers detailed explanations.")

        # Recent conversation context
        if self.conversation_history and max_history > 0:
            recent = self.conversation_history[-max_history:]
            context_parts.append(
                f"Recent conversation context: {len(recent)} prior interactions."
            )

            # Add brief summary of last query
            if recent:
                last = recent[-1]
                context_parts.append(f"Last query was about: {last['query'][:50]}...")

        return " ".join(context_parts)

    def _get_top_plugins(self, limit: int = 5) -> List[tuple]:
        """Get most frequently used plugins."""
        plugin_counts = self.preferences.get("preferred_plugins", {})
        sorted_plugins = sorted(plugin_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_plugins[:limit]

    def _get_typical_time(self) -> str:
        """Determine when user typically interacts."""
        time_patterns = self.preferences.get("query_time_patterns", {})
        if not time_patterns:
            return "unknown"

        max_time = max(time_patterns.items(), key=lambda x: len(x[1]))
        return max_time[0]

    def clear_history(self, days_to_keep: int = 30):
        """
        Clear old conversation history (tier-dependent retention).
        Business: 7 years, Pro: 1 year, Home: 30 days
        """
        retention_days = {"home": 30, "pro": 365, "business": 365 * 7}

        days = retention_days.get(self.tier, days_to_keep)
        cutoff = datetime.now().timestamp() - (days * 86400)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            DELETE FROM conversation_history
            WHERE user_id = ? AND timestamp < ?
        """,
            (self.user_id, cutoff),
        )

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        logger.info(f"Cleared {deleted} old interactions for user '{self.user_id}'")

        return deleted


class UserContextManager:
    """
    Global manager for user contexts.
    Handles multiple users and provides context to the reasoning engine.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or "kilo_data/user_contexts.db"
        self.active_contexts: Dict[str, UserContext] = {}
        logger.info("✅ UserContextManager initialized")

    def get_context(self, user_id: str = "default", tier: str = "home") -> UserContext:
        """
        Get or create user context.
        In single-user appliance mode, user_id is typically 'default'.
        """
        if user_id not in self.active_contexts:
            self.active_contexts[user_id] = UserContext(
                user_id=user_id, tier=tier, db_path=self.db_path
            )

        return self.active_contexts[user_id]

    def get_context_for_request(self, headers: Dict[str, str]) -> UserContext:
        """
        Extract user context from HTTP request headers.
        Checks for user ID and tier from auth/license.
        """
        # In single-user mode, always use 'default'
        user_id = headers.get("x-user-id", "default")
        tier = headers.get("x-user-tier", "home")

        return self.get_context(user_id=user_id, tier=tier)


# Global singleton
_context_manager: Optional[UserContextManager] = None


def get_context_manager() -> UserContextManager:
    """Get or create the global context manager."""
    global _context_manager
    if _context_manager is None:
        _context_manager = UserContextManager()
    return _context_manager
