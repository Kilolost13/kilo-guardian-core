"""
User Profile Manager Plugin for Kilo Guardian
Stores and manages wizard setup data for AI context.
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from plugins.base_plugin import BasePlugin


class UserProfile(BasePlugin):
    """
    User profile management plugin.
    Stores wizard setup data and provides context to the AI.
    """

    def __init__(self):
        super().__init__()
        self.db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "user_data",
            "user_profile.db",
        )
        self._init_database()
        self._load_profile()

    def _init_database(self):
        """Initialize user profile database."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main profile table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                user_name TEXT,
                preferred_name TEXT,
                assistant_name TEXT DEFAULT 'Kilo',
                location_method TEXT,
                location_value TEXT,
                wizard_completed INTEGER DEFAULT 0,
                wizard_completed_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_updated TEXT
            )
        """
        )

        # Recognized faces table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS recognized_faces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                relation TEXT,
                image_data TEXT,
                face_encoding TEXT,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # News preferences table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS news_preferences (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                topics TEXT,
                sources TEXT,
                briefing_time TEXT DEFAULT 'ondemand',
                last_updated TEXT
            )
        """
        )

        # OAuth connections table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS oauth_connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT NOT NULL UNIQUE,
                connected_at TEXT DEFAULT CURRENT_TIMESTAMP,
                access_token TEXT,
                refresh_token TEXT,
                expires_at TEXT
            )
        """
        )

        # User interests/preferences table (from wizard)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT,
                category TEXT,
                source TEXT DEFAULT 'wizard',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_updated TEXT
            )
        """
        )

        # Initialize default profile if not exists
        cursor.execute("SELECT COUNT(*) FROM user_profile WHERE id = 1")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO user_profile (id) VALUES (1)")

        cursor.execute("SELECT COUNT(*) FROM news_preferences WHERE id = 1")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO news_preferences (id) VALUES (1)")

        conn.commit()
        conn.close()

    def _load_profile(self):
        """Load current profile into memory."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT user_name, preferred_name, assistant_name, wizard_completed FROM user_profile WHERE id = 1"
        )
        result = cursor.fetchone()
        conn.close()

        if result:
            self.user_name = result[0]
            self.preferred_name = result[1]
            self.assistant_name = result[2] or "Kilo"
            self.wizard_completed = bool(result[3])
        else:
            self.user_name = None
            self.preferred_name = None
            self.assistant_name = "Kilo"
            self.wizard_completed = False

    def get_name(self) -> str:
        return "user_profile"

    def get_keywords(self) -> list:
        return [
            "profile",
            "my name",
            "my info",
            "who am i",
            "preferences",
            "settings",
            "wizard",
            "setup",
        ]

    def run(self, query: str) -> dict:
        """Main execution method."""
        query_lower = query.lower()

        try:
            # Show profile
            if "show" in query_lower or "view" in query_lower:
                return self._show_profile()

            # Update profile
            if "update" in query_lower:
                return self._handle_update_profile()

            # Check wizard status
            if "wizard" in query_lower and "status" in query_lower:
                return self._get_wizard_status()

            # Default: show help
            return self._get_help()

        except Exception as e:
            return {"type": "error", "tool": "user_profile", "error": str(e)}

    def save_wizard_data(self, wizard_data: Dict) -> bool:
        """
        Save wizard setup data to database.
        Called by the wizard completion endpoint.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Save personal info
            personal = wizard_data.get("personal", {})
            cursor.execute(
                """
                UPDATE user_profile 
                SET user_name = ?, preferred_name = ?, assistant_name = ?,
                    wizard_completed = 1, wizard_completed_at = ?, last_updated = ?
                WHERE id = 1
                """,
                (
                    personal.get("userName"),
                    personal.get("preferredName"),
                    personal.get("assistantName", "Kilo"),
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )

            # Save faces
            faces = wizard_data.get("faces", [])
            for face in faces:
                cursor.execute(
                    """
                    INSERT INTO recognized_faces (name, relation, image_data)
                    VALUES (?, ?, ?)
                    """,
                    (face.get("name"), face.get("relation"), face.get("image")),
                )

            # Save news preferences
            news = wizard_data.get("news", {})
            cursor.execute(
                """
                UPDATE news_preferences
                SET topics = ?, sources = ?, briefing_time = ?, last_updated = ?
                WHERE id = 1
                """,
                (
                    news.get("topics"),
                    json.dumps(news.get("sources", [])),
                    news.get("briefingTime", "ondemand"),
                    datetime.now().isoformat(),
                ),
            )

            # Save location
            location = wizard_data.get("location", {})
            cursor.execute(
                """
                UPDATE user_profile
                SET location_method = ?, location_value = ?
                WHERE id = 1
                """,
                (location.get("method"), location.get("value")),
            )

            # Save OAuth connections
            oauth = wizard_data.get("oauth", {})
            for service in oauth.get("connected", []):
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO oauth_connections (service)
                    VALUES (?)
                    """,
                    (service,),
                )

            conn.commit()
            conn.close()

            # Reload profile
            self._load_profile()

            return True

        except Exception as e:
            print(f"Error saving wizard data: {e}")
            return False

    def get_context_for_ai(self) -> Dict[str, Any]:
        """
        Get user context for AI prompts.
        This provides personalized context to the AI.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get profile
        cursor.execute(
            """
            SELECT user_name, preferred_name, assistant_name, location_value 
            FROM user_profile WHERE id = 1
            """
        )
        profile = cursor.fetchone()

        # Get recognized faces
        cursor.execute("SELECT name, relation FROM recognized_faces")
        faces = [{"name": name, "relation": rel} for name, rel in cursor.fetchall()]

        # Get news preferences
        cursor.execute(
            "SELECT topics, sources, briefing_time FROM news_preferences WHERE id = 1"
        )
        news_pref = cursor.fetchone()

        conn.close()

        context = {
            "user": {
                "name": profile[0] if profile else None,
                "preferred_name": profile[1] if profile else None,
                "location": profile[3] if profile else None,
            },
            "assistant_name": profile[2] if profile and profile[2] else "Kilo",
            "household": {"members": faces},
            "preferences": {
                "news_topics": news_pref[0] if news_pref else None,
                "news_sources": (
                    json.loads(news_pref[1]) if news_pref and news_pref[1] else []
                ),
                "briefing_time": news_pref[2] if news_pref else "ondemand",
            },
            "wizard_completed": self.wizard_completed,
        }

        return context

    def _show_profile(self) -> dict:
        """Show user profile information."""
        context = self.get_context_for_ai()

        return {
            "type": "user_profile",
            "tool": "user_profile",
            "profile": context,
            "message": f"Profile for {context['user']['preferred_name'] or context['user']['name'] or 'User'}",
        }

    def _get_wizard_status(self) -> dict:
        """Get wizard completion status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT wizard_completed, wizard_completed_at FROM user_profile WHERE id = 1"
        )
        result = cursor.fetchone()
        conn.close()

        if result and result[0]:
            return {
                "type": "wizard_status",
                "tool": "user_profile",
                "completed": True,
                "completed_at": result[1],
                "message": "✅ Setup wizard has been completed",
            }
        else:
            return {
                "type": "wizard_status",
                "tool": "user_profile",
                "completed": False,
                "message": "⚠️ Setup wizard has not been completed. Run the wizard to personalize your experience.",
                "action": "Open the menu and select 'Setup Wizard' to get started.",
            }

    def _handle_update_profile(self) -> dict:
        """Handle profile update request."""
        return {
            "type": "interactive_form",
            "tool": "user_profile",
            "form": {
                "title": "Update Profile",
                "fields": [
                    {
                        "name": "preferred_name",
                        "type": "text",
                        "label": "Preferred Name",
                        "placeholder": "What should I call you?",
                    },
                    {
                        "name": "assistant_name",
                        "type": "text",
                        "label": "Assistant Name",
                        "placeholder": "What should you call me?",
                        "default": self.assistant_name,
                    },
                ],
            },
            "message": "Update your profile information",
        }

    def update_profile(
        self, preferred_name: Optional[str] = None, assistant_name: Optional[str] = None
    ) -> bool:
        """Update user profile."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        updates = []
        params = []

        if preferred_name is not None:
            updates.append("preferred_name = ?")
            params.append(preferred_name)

        if assistant_name is not None:
            updates.append("assistant_name = ?")
            params.append(assistant_name)

        if updates:
            updates.append("last_updated = ?")
            params.append(datetime.now().isoformat())
            params.append(1)  # WHERE id = 1

            cursor.execute(
                f"UPDATE user_profile SET {', '.join(updates)} WHERE id = ?", params
            )

            conn.commit()

        conn.close()

        # Reload profile
        self._load_profile()

        return True

    def get_preference(self, key: str) -> Optional[Any]:
        """Get a specific user preference."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT value FROM user_preferences WHERE key = ?", (key,))

        result = cursor.fetchone()
        conn.close()

        if result:
            try:
                return json.loads(result[0])
            except:
                return result[0]

        return None

    def set_preference(self, key: str, value: Any, category: str = "general") -> bool:
        """Set a user preference."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        value_str = json.dumps(value) if not isinstance(value, str) else value

        cursor.execute(
            """
            INSERT OR REPLACE INTO user_preferences 
            (key, value, category, last_updated)
            VALUES (?, ?, ?, ?)
            """,
            (key, value_str, category, datetime.now().isoformat()),
        )

        conn.commit()
        conn.close()

        return True

    def _get_help(self) -> dict:
        """Return help information."""
        return {
            "type": "profile_help",
            "tool": "user_profile",
            "content": {
                "message": "User Profile Manager - Your personalized AI context",
                "commands": [
                    "show profile - View your profile information",
                    "update profile - Change your name or assistant name",
                    "wizard status - Check if setup wizard has been completed",
                ],
                "features": [
                    "👤 Stores your personal information",
                    "👨‍👩‍👧‍👦 Recognizes household members",
                    "📰 Remembers your news preferences",
                    "🌍 Tracks your location for local info",
                    "🤖 Provides context to AI for personalized responses",
                ],
                "current_user": self.preferred_name or self.user_name or "Not set",
                "assistant_name": self.assistant_name,
                "wizard_completed": self.wizard_completed,
            },
        }

    def execute(self, query: str) -> dict:
        """Execute method for reasoning engine."""
        return self.run(query)
