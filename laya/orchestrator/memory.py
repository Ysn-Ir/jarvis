"""
Laya Durable Memory Store
Mem0-style extracted-fact persistence using local SQLite.
Stores user preferences, facts, and state across sessions.
"""

import sqlite3
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from laya.config import MEMORY_DB_PATH


class MemoryStore:
    _instance: Optional["MemoryStore"] = None

    def __init__(self, db_path: Path = MEMORY_DB_PATH):
        self.db_path = db_path
        self._init_db()

    @classmethod
    def get_instance(cls) -> "MemoryStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact TEXT UNIQUE NOT NULL,
                category TEXT DEFAULT 'general',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def add_fact(self, fact: str, category: str = "general") -> str:
        """Store an extracted durable fact or preference."""
        clean_fact = fact.strip()
        if not clean_fact:
            return "Cannot store empty fact."

        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO facts (fact, category) VALUES (?, ?)",
                (clean_fact, category),
            )
            conn.commit()
            conn.close()
            return f"Remembered: '{clean_fact}'"
        except Exception as e:
            return f"Failed to store memory: {e}"

    def search_facts(self, query: str) -> str:
        """Search memory for relevant facts using keyword matching."""
        q_words = [w.lower() for w in query.split() if len(w) > 2]
        if not q_words:
            return self.get_all_summary()

        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT id, fact, category FROM facts")
            rows = cursor.fetchall()
            conn.close()

            matches = []
            for row in rows:
                f_id, fact_text, cat = row
                lower_fact = fact_text.lower()
                if any(w in lower_fact for w in q_words):
                    matches.append(fact_text)

            if matches:
                return "Here is what I remember: " + "; ".join(matches)
            return "I don't have any specific notes on that topic yet."
        except Exception as e:
            return f"Error reading memory: {e}"

    def get_all_summary(self) -> str:
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT fact FROM facts ORDER BY id DESC LIMIT 10")
            rows = cursor.fetchall()

            cursor.execute("SELECT key, value FROM user_profile")
            profile_rows = cursor.fetchall()
            conn.close()

            parts = []
            if profile_rows:
                p_str = ", ".join(f"{k}: {v}" for k, v in profile_rows)
                parts.append(f"User Profile: [{p_str}]")
            if rows:
                parts.append("Facts: " + "; ".join(r[0] for r in rows))

            return " | ".join(parts) if parts else "No memories recorded yet."
        except Exception as e:
            return f"Error accessing memory: {e}"

    def set_profile(self, key: str, value: str) -> str:
        """Set a persistent user preference or profile attribute."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO user_profile (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (key.strip().lower(), value.strip())
            )
            conn.commit()
            conn.close()
            return f"Updated profile '{key}' to '{value}'."
        except Exception as e:
            return f"Failed to update profile: {e}"

    def get_profile(self, key: str, default: str = "") -> str:
        """Get a user profile attribute."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM user_profile WHERE key = ?", (key.strip().lower(),))
            row = cursor.fetchone()
            conn.close()
            return row[0] if row else default
        except Exception:
            return default

    def get_user_profile(self) -> Dict[str, str]:
        """Get all user profile attributes as a key-value dictionary."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM user_profile")
            rows = cursor.fetchall()
            conn.close()
            return {r[0]: r[1] for r in rows}
        except Exception:
            return {}

    def record_session(self) -> float:
        """Log current session and return elapsed hours since last session."""
        hours_since = -1.0
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT started_at FROM session_logs ORDER BY id DESC LIMIT 1")
            last = cursor.fetchone()
            if last:
                last_time = datetime.datetime.fromisoformat(last[0].replace(" ", "T"))
                delta = datetime.datetime.now() - last_time
                hours_since = delta.total_seconds() / 3600.0

            cursor.execute("INSERT INTO session_logs (started_at) VALUES (CURRENT_TIMESTAMP)")
            conn.commit()
            conn.close()
        except Exception:
            pass
        return hours_since

    def generate_startup_greeting(self) -> str:
        """Generate a witty, time-of-day and context-aware JARVIS greeting."""
        now = datetime.datetime.now()
        hour = now.hour
        hours_gap = self.record_session()

        user_name = self.get_profile("name", "")
        title = f", {user_name}" if user_name else ", sir"

        if 5 <= hour < 12:
            time_greeting = f"Good morning{title}. Systems are primed and ready."
        elif 12 <= hour < 17:
            time_greeting = f"Good afternoon{title}. What are we conquering today?"
        elif 17 <= hour < 22:
            time_greeting = f"Good evening{title}. Standing by for your instructions."
        else:
            time_greeting = f"Burning the midnight oil{title}? All systems are online. Let's get to work."

        # Add witty contextual quip
        if hours_gap > 24:
            time_greeting += " It's been a while. Good to have you back."

        return time_greeting


def get_memory_store() -> MemoryStore:
    return MemoryStore.get_instance()
