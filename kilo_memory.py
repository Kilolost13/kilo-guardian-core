#!/usr/bin/env python3
"""
Kilo Memory System - Persistent storage of user preferences and facts
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict, Any


class KiloMemory:
    """Manages Kilo's persistent memory of user preferences and facts"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            # Store in the working directory
            db_path = os.path.join(
                os.path.dirname(__file__),
                "kilo_memory.db"
            )

        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize the database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # User facts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact_key TEXT NOT NULL UNIQUE,
                fact_value TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Interaction history table (for pattern learning)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                command_type TEXT NOT NULL,
                user_message TEXT NOT NULL,
                kilo_response TEXT,
                cluster_state TEXT
            )
        """)

        # Cluster usage patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cluster_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL,
                service_name TEXT,
                memory_usage REAL,
                notes TEXT
            )
        """)

        conn.commit()
        conn.close()

    def teach_fact(self, fact_key: str, fact_value: str, category: str = "general") -> bool:
        """Store a new fact or update existing one"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            now = datetime.now().isoformat()

            cursor.execute("""
                INSERT INTO user_facts (fact_key, fact_value, category, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(fact_key) DO UPDATE SET
                    fact_value = ?,
                    category = ?,
                    updated_at = ?
            """, (fact_key, fact_value, category, now, now, fact_value, category, now))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error storing fact: {e}")
            return False

    def recall_fact(self, fact_key: str) -> Optional[str]:
        """Retrieve a stored fact"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT fact_value FROM user_facts WHERE fact_key = ?",
                (fact_key,)
            )

            result = cursor.fetchone()
            conn.close()

            return result[0] if result else None
        except Exception as e:
            print(f"Error recalling fact: {e}")
            return None

    def get_all_facts(self) -> List[Dict[str, Any]]:
        """Get all stored facts for injection into system prompt"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT fact_key, fact_value, category, updated_at
                FROM user_facts
                ORDER BY category, fact_key
            """)

            facts = []
            for row in cursor.fetchall():
                facts.append({
                    "key": row[0],
                    "value": row[1],
                    "category": row[2],
                    "updated_at": row[3]
                })

            conn.close()
            return facts
        except Exception as e:
            print(f"Error getting all facts: {e}")
            return []

    def log_interaction(self, command_type: str, user_message: str,
                       kilo_response: str = "", cluster_state: str = ""):
        """Log an interaction for pattern analysis"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO interactions
                (timestamp, command_type, user_message, kilo_response, cluster_state)
                VALUES (?, ?, ?, ?, ?)
            """, (datetime.now().isoformat(), command_type, user_message,
                  kilo_response, cluster_state))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error logging interaction: {e}")

    def log_cluster_action(self, action: str, service_name: str = "",
                          memory_usage: float = 0.0, notes: str = ""):
        """Log cluster actions for pattern learning"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO cluster_patterns
                (timestamp, action, service_name, memory_usage, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (datetime.now().isoformat(), action, service_name, memory_usage, notes))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error logging cluster action: {e}")

    def get_memory_summary(self) -> str:
        """Get a summary of stored knowledge for system prompt injection"""
        facts = self.get_all_facts()

        if not facts:
            return ""

        summary = "\n=== KILO'S LEARNED KNOWLEDGE ===\n"

        # Group by category
        by_category = {}
        for fact in facts:
            cat = fact["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(fact)

        for category, items in by_category.items():
            summary += f"\n{category.upper()}:\n"
            for item in items:
                summary += f"  - {item['key']}: {item['value']}\n"

        summary += "\nIMPORTANT: Use this learned knowledge when answering. Don't suggest things the user has already rejected or configured differently.\n"

        return summary


# Singleton instance
_memory_instance: Optional[KiloMemory] = None

def get_kilo_memory() -> KiloMemory:
    """Get the global memory instance"""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = KiloMemory()
    return _memory_instance
