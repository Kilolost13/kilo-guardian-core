import logging
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import faiss
    from sentence_transformers import SentenceTransformer

    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logging.warning(
        "FAISS or sentence-transformers not available. Semantic search disabled."
    )

logger = logging.getLogger("MemoryDB")


class MemoryDB:
    def __init__(self):
        self.db_path = os.getenv("MEMORY_DB_PATH", "kilo_data/mind.db")
        self.faiss_index_path = os.getenv(
            "MEMORY_FAISS_INDEX_PATH", "kilo_data/faiss.index"
        )

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.faiss_index_path), exist_ok=True)

        logger.info(
            f"MemoryDB initialized. DB path: {self.db_path}, FAISS index path: {self.faiss_index_path}"
        )

        # Database connection and FAISS index
        self.conn: Optional[sqlite3.Connection] = None
        self.faiss_index = None
        self.embedding_model = None
        self.embedding_dim = 384  # all-MiniLM-L6-v2 dimension

        self._connect_db()
        self._create_schema()
        self._load_embedding_model()
        self._load_faiss_index()

    def _connect_db(self):
        """Establish SQLite database connection with row factory for dict-like access."""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # Enable dict-like row access
            logger.info(f"Connected to SQLite database at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def _create_schema(self):
        """Create database tables if they don't exist."""
        if not self.conn:
            logger.error("Cannot create schema: database connection not established")
            return

        cursor = self.conn.cursor()

        # Reminders table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                scheduled_time DATETIME NOT NULL,
                recurring TEXT,
                acknowledged BOOLEAN DEFAULT 0,
                snoozed_until DATETIME,
                priority TEXT DEFAULT 'normal',
                category TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Medications table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS medications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                dosage TEXT,
                frequency TEXT NOT NULL,
                times TEXT NOT NULL,
                notes TEXT,
                active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Medication logs table (for tracking adherence)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS medication_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                medication_id INTEGER NOT NULL,
                scheduled_time DATETIME NOT NULL,
                taken_time DATETIME,
                skipped BOOLEAN DEFAULT 0,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (medication_id) REFERENCES medications(id)
            )
        """
        )

        # Memory events table (for "what did I do today" queries)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_text TEXT NOT NULL,
                event_time DATETIME NOT NULL,
                event_type TEXT,
                embedding_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Habits table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS habits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                target_frequency TEXT NOT NULL,
                streak INTEGER DEFAULT 0,
                last_completed DATETIME,
                active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Habit logs table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS habit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id INTEGER NOT NULL,
                completed_at DATETIME NOT NULL,
                notes TEXT,
                FOREIGN KEY (habit_id) REFERENCES habits(id)
            )
        """
        )

        # Camera accountability rules table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS camera_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                camera_id TEXT NOT NULL,
                zone TEXT,
                condition TEXT NOT NULL,
                expected_state TEXT NOT NULL,
                check_schedule TEXT,
                reminder_text TEXT,
                active BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        self.conn.commit()
        logger.info("Database schema created/verified")

    def _load_embedding_model(self):
        """Load sentence transformer model for embeddings."""
        if not FAISS_AVAILABLE:
            logger.warning(
                "Embedding model not loaded: FAISS/sentence-transformers unavailable"
            )
            return

        try:
            # Use lightweight model optimized for semantic similarity
            self.embedding_model = SentenceTransformer(
                "sentence-transformers/all-MiniLM-L6-v2"
            )
            logger.info("✅ Embedding model loaded: all-MiniLM-L6-v2 (384 dimensions)")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.embedding_model = None

    def _load_faiss_index(self):
        """Load or create FAISS index for semantic search."""
        if not FAISS_AVAILABLE or not self.embedding_model:
            logger.warning("FAISS index not loaded: dependencies unavailable")
            return

        try:
            if os.path.exists(self.faiss_index_path):
                # Load existing index
                self.faiss_index = faiss.read_index(self.faiss_index_path)
                logger.info(
                    f"✅ Loaded FAISS index from {self.faiss_index_path} ({self.faiss_index.ntotal} vectors)"
                )
            else:
                # Create new index (L2 distance, 384 dimensions)
                self.faiss_index = faiss.IndexFlatL2(self.embedding_dim)
                logger.info(f"✅ Created new FAISS index (dim={self.embedding_dim})")
        except Exception as e:
            logger.error(f"Failed to load FAISS index: {e}")
            self.faiss_index = None

    # ===== Reminder CRUD Operations =====

    def add_reminder(
        self,
        text: str,
        scheduled_time: str,
        recurring: Optional[str] = None,
        priority: str = "normal",
        category: Optional[str] = None,
    ) -> int:
        """Add a new reminder to the database."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO reminders (text, scheduled_time, recurring, priority, category)
            VALUES (?, ?, ?, ?, ?)
        """,
            (text, scheduled_time, recurring, priority, category),
        )
        self.conn.commit()
        reminder_id = cursor.lastrowid
        logger.info(f"Added reminder ID {reminder_id}: {text}")
        return reminder_id

    def get_reminders(self, include_acknowledged: bool = False) -> List[Dict[str, Any]]:
        """Get all reminders, optionally including acknowledged ones."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM reminders"
        if not include_acknowledged:
            query += " WHERE acknowledged = 0"
        query += " ORDER BY scheduled_time ASC"

        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]

    def get_reminder(self, reminder_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific reminder by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def acknowledge_reminder(self, reminder_id: int) -> bool:
        """Mark a reminder as acknowledged."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE reminders SET acknowledged = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (reminder_id,),
        )
        self.conn.commit()
        success = cursor.rowcount > 0
        if success:
            logger.info(f"Acknowledged reminder ID {reminder_id}")
        return success

    def snooze_reminder(self, reminder_id: int, snooze_until: str) -> bool:
        """Snooze a reminder until a later time."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE reminders SET snoozed_until = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (snooze_until, reminder_id),
        )
        self.conn.commit()
        success = cursor.rowcount > 0
        if success:
            logger.info(f"Snoozed reminder ID {reminder_id} until {snooze_until}")
        return success

    def delete_reminder(self, reminder_id: int) -> bool:
        """Delete a reminder."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        self.conn.commit()
        success = cursor.rowcount > 0
        if success:
            logger.info(f"Deleted reminder ID {reminder_id}")
        return success

    # ===== Medication CRUD Operations =====

    def add_medication(
        self,
        name: str,
        dosage: str,
        frequency: str,
        times: str,
        notes: Optional[str] = None,
    ) -> int:
        """Add a new medication to the database."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO medications (name, dosage, frequency, times, notes)
            VALUES (?, ?, ?, ?, ?)
        """,
            (name, dosage, frequency, times, notes),
        )
        self.conn.commit()
        med_id = cursor.lastrowid
        logger.info(f"Added medication ID {med_id}: {name}")
        return med_id

    def get_medications(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all medications."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM medications"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY name ASC"

        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]

    def log_medication_taken(
        self,
        medication_id: int,
        scheduled_time: str,
        taken_time: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> int:
        """Log that a medication was taken."""
        if not taken_time:
            taken_time = datetime.now().isoformat()

        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO medication_logs (medication_id, scheduled_time, taken_time, notes)
            VALUES (?, ?, ?, ?)
        """,
            (medication_id, scheduled_time, taken_time, notes),
        )
        self.conn.commit()
        log_id = cursor.lastrowid
        logger.info(f"Logged medication taken: med_id={medication_id}, log_id={log_id}")
        return log_id

    def get_medication_logs(
        self,
        medication_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get medication logs, optionally filtered by medication ID and date range.

        Args:
            medication_id: Filter by specific medication ID (optional)
            start_date: Start date in ISO format (optional)
            end_date: End date in ISO format (optional)

        Returns:
            List of medication log dictionaries
        """
        cursor = self.conn.cursor()
        query = "SELECT * FROM medication_logs WHERE 1=1"
        params = []

        if medication_id is not None:
            query += " AND medication_id = ?"
            params.append(medication_id)

        if start_date:
            query += " AND DATE(taken_time) >= DATE(?)"
            params.append(start_date)

        if end_date:
            query += " AND DATE(taken_time) <= DATE(?)"
            params.append(end_date)

        query += " ORDER BY taken_time DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def get_medication_logs_today(
        self, medication_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get medication logs for today, optionally filtered by medication ID.

        Args:
            medication_id: Filter by specific medication ID (optional)

        Returns:
            List of medication log dictionaries for today
        """
        from datetime import date

        today = date.today().isoformat()
        return self.get_medication_logs(
            medication_id=medication_id, start_date=today, end_date=today
        )

    # ===== Memory Event Operations =====

    def add_memory_event(
        self,
        event_text: str,
        event_time: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> int:
        """Add a memory event (for 'what did I do today' queries)."""
        if not event_time:
            event_time = datetime.now().isoformat()

        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO memory_events (event_text, event_time, event_type)
            VALUES (?, ?, ?)
        """,
            (event_text, event_time, event_type),
        )
        self.conn.commit()
        event_id = cursor.lastrowid
        logger.info(f"Added memory event ID {event_id}")

        # Generate and store embedding for semantic search
        if self.embedding_model and self.faiss_index is not None:
            try:
                embedding = self._generate_embedding(event_text)
                embedding_id = self.faiss_index.ntotal  # Use current count as ID
                self.faiss_index.add(embedding)

                # Update event with embedding_id
                cursor.execute(
                    """
                    UPDATE memory_events SET embedding_id = ? WHERE id = ?
                """,
                    (embedding_id, event_id),
                )
                self.conn.commit()

                # Save index periodically (every 10 events)
                if embedding_id % 10 == 0:
                    self._save_faiss_index()

                logger.debug(f"Added embedding {embedding_id} for event {event_id}")
            except Exception as e:
                logger.warning(
                    f"Failed to generate embedding for event {event_id}: {e}"
                )

        return event_id

    def get_memory_events(
        self, start_time: Optional[str] = None, end_time: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get memory events within a time range."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM memory_events WHERE 1=1"
        params = []

        if start_time:
            query += " AND event_time >= ?"
            params.append(start_time)
        if end_time:
            query += " AND event_time <= ?"
            params.append(end_time)

        query += " ORDER BY event_time DESC"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    # ===== Habit Operations =====

    def add_habit(
        self, name: str, target_frequency: str, description: Optional[str] = None
    ) -> int:
        """Add a new habit to track."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO habits (name, description, target_frequency)
            VALUES (?, ?, ?)
        """,
            (name, description, target_frequency),
        )
        self.conn.commit()
        habit_id = cursor.lastrowid
        logger.info(f"Added habit ID {habit_id}: {name}")
        return habit_id

    def get_habits(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all habits."""
        cursor = self.conn.cursor()
        query = "SELECT * FROM habits"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY name ASC"

        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]

    def log_habit_completion(
        self,
        habit_id: int,
        completed_at: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> int:
        """Log that a habit was completed."""
        if not completed_at:
            completed_at = datetime.now().isoformat()

        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO habit_logs (habit_id, completed_at, notes)
            VALUES (?, ?, ?)
        """,
            (habit_id, completed_at, notes),
        )

        # Update habit streak and last_completed
        cursor.execute(
            """
            UPDATE habits
            SET streak = streak + 1, last_completed = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (completed_at, habit_id),
        )

        self.conn.commit()
        log_id = cursor.lastrowid
        logger.info(f"Logged habit completion: habit_id={habit_id}, log_id={log_id}")
        return log_id

    # ===== Embedding and Semantic Search =====

    def _generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding vector for text.

        Args:
            text: Text to encode

        Returns:
            Numpy array of shape (1, embedding_dim)
        """
        if not self.embedding_model:
            raise RuntimeError("Embedding model not initialized")

        # Generate embedding and ensure correct shape
        embedding = self.embedding_model.encode([text], convert_to_numpy=True)
        return embedding.astype("float32")

    def _save_faiss_index(self):
        """Save FAISS index to disk."""
        if not self.faiss_index:
            return

        try:
            faiss.write_index(self.faiss_index, self.faiss_index_path)
            logger.debug(f"Saved FAISS index to {self.faiss_index_path}")
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {e}")

    def semantic_search(
        self,
        query: str,
        k: int = 5,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search on memory events.

        Args:
            query: Natural language query (e.g., "when did I go to the store?")
            k: Number of results to return
            start_time: Optional start time filter (ISO format)
            end_time: Optional end time filter (ISO format)

        Returns:
            List of memory events ranked by semantic similarity
        """
        if not self.embedding_model or not self.faiss_index:
            logger.warning("Semantic search unavailable: FAISS not initialized")
            # Fallback to basic text search
            return self._fallback_text_search(query, k, start_time, end_time)

        if self.faiss_index.ntotal == 0:
            logger.info("FAISS index is empty, no results")
            return []

        try:
            # Generate query embedding
            query_embedding = self._generate_embedding(query)

            # Search FAISS index
            distances, indices = self.faiss_index.search(
                query_embedding, min(k, self.faiss_index.ntotal)
            )

            # Fetch corresponding events from database
            results = []
            cursor = self.conn.cursor()

            for idx, distance in zip(indices[0], distances[0]):
                # Query by embedding_id
                cursor.execute(
                    """
                    SELECT * FROM memory_events WHERE embedding_id = ?
                """,
                    (int(idx),),
                )
                row = cursor.fetchone()

                if row:
                    event = dict(row)
                    event["similarity_score"] = float(
                        1.0 / (1.0 + distance)
                    )  # Convert distance to similarity

                    # Apply time filters if provided
                    if start_time and event["event_time"] < start_time:
                        continue
                    if end_time and event["event_time"] > end_time:
                        continue

                    results.append(event)

            logger.info(
                f"Semantic search for '{query}' returned {len(results)} results"
            )
            return results[:k]  # Return top k results

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            # Fallback to basic search
            return self._fallback_text_search(query, k, start_time, end_time)

    def _fallback_text_search(
        self,
        query: str,
        k: int = 5,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fallback text search using SQL LIKE when FAISS unavailable.

        Args:
            query: Search query
            k: Number of results to return
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            List of matching memory events
        """
        cursor = self.conn.cursor()
        sql_query = "SELECT * FROM memory_events WHERE event_text LIKE ?"
        params = [f"%{query}%"]

        if start_time:
            sql_query += " AND event_time >= ?"
            params.append(start_time)
        if end_time:
            sql_query += " AND event_time <= ?"
            params.append(end_time)

        sql_query += " ORDER BY event_time DESC LIMIT ?"
        params.append(k)

        cursor.execute(sql_query, params)
        results = [dict(row) for row in cursor.fetchall()]

        logger.info(
            f"Fallback text search for '{query}' returned {len(results)} results"
        )
        return results

    def close(self):
        """Close database connection and save FAISS index."""
        # Save FAISS index before closing
        if self.faiss_index:
            self._save_faiss_index()

        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


# Global instance
memory_db_instance = MemoryDB()


def get_memory_db():
    return memory_db_instance
