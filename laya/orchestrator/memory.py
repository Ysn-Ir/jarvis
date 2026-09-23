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
            conn.close()
            if not rows:
                return "No memories recorded yet."
            return "Active memories: " + "; ".join(r[0] for r in rows)
        except Exception as e:
            return f"Error accessing memory: {e}"


def get_memory_store() -> MemoryStore:
    return MemoryStore.get_instance()
