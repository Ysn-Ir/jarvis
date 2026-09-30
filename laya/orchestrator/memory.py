"""
Laya Durable Memory Store
Mem0-style extracted-fact persistence using local SQLite.
Stores user preferences, facts, and state across sessions with structured task & event architecture.
"""

import sqlite3
import datetime
import threading
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from laya.config import MEMORY_DB_PATH


class MemoryStore:
    _instance: Optional["MemoryStore"] = None

    def __init__(self, db_path: Path = MEMORY_DB_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()
        self.clean_messy_memory()
        self._start_reminder_daemon()

    @classmethod
    def get_instance(cls) -> "MemoryStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0, isolation_level=None)
        try:
            conn.execute("PRAGMA busy_timeout=5000;")
        except Exception:
            pass
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._get_connection()
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
            except Exception:
                pass
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                fire_at TIMESTAMP NOT NULL,
                fired INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                due_date TEXT,
                priority TEXT DEFAULT 'normal',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.close()

    def clean_messy_memory(self):
        """Clean up conflicting historical entries, set correct username to Yasin, and prune conversational noise."""
        with self._lock:
            conn = None
            try:
                conn = self._get_connection()
                cur = conn.cursor()
                # 1. Update user profile to Yasin
                cur.execute("INSERT OR REPLACE INTO user_profile (key, value, updated_at) VALUES ('name', 'Yasin', CURRENT_TIMESTAMP)")
                cur.execute("INSERT OR REPLACE INTO user_profile (key, value, updated_at) VALUES ('role', 'AI Engineer', CURRENT_TIMESTAMP)")

                # 2. Delete conflicting / garbage facts
                cur.execute("DELETE FROM facts WHERE fact LIKE '%Thomas%' OR fact LIKE '%Khalil%' OR fact LIKE '%my name isn%'")
                cur.execute("DELETE FROM facts WHERE LENGTH(fact) < 5")
                cur.execute("DELETE FROM facts WHERE fact LIKE '%who are you%' OR fact LIKE '%what time%' OR fact LIKE '%you suck%'")

                # 3. Add clean fact for Yasin
                cur.execute("INSERT OR IGNORE INTO facts (fact, category) VALUES ('User\\'s name is Yasin', 'general')")
            except Exception:
                pass
            finally:
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass

    def add_fact(self, fact: str, category: str = "general") -> str:
        """Store an extracted durable fact or preference with strict noise filtering and semantic resolution."""
        clean_fact = fact.strip()
        if not clean_fact or len(clean_fact) < 4:
            return "Cannot store empty or trivial memory."

        low = clean_fact.lower()

        # Guardrails: filter out conversational debris, questions, and system commands
        if any(low.startswith(p) for p in [
            "who are you", "what is", "how do", "can you", "could you", "please",
            "open ", "close ", "scroll ", "turn off", "stop ", "launch ", "click ",
            "type ", "search "
        ]):
            return "Ignored command as durable memory."
        if any(w in low for w in ["you suck", "shut up", "idiot", "dumb", "trash", "useless", "lol", "lmao", "test test", "foid"]):
            return "Filtered out banter from memory."

        # Semantic parsing: User Name
        name_m = re.search(r"\b(?:my\s+name\s+is|i\s+am\s+called|call\s+me)\s+([a-zA-Z\s\-]+)", clean_fact, re.I)
        if name_m:
            extracted_name = name_m.group(1).strip().strip(".!?,")
            if extracted_name.lower() not in ["ready", "done", "trying", "fine", "here", "sorry"]:
                self.set_profile("name", extracted_name)
                # Prune old name facts
                try:
                    conn = self._get_connection()
                    conn.execute("DELETE FROM facts WHERE fact LIKE 'User%name is%' OR fact LIKE 'my name is%'")
                    conn.commit()
                    conn.close()
                except Exception:
                    pass
                return f"Understood. Your name is {extracted_name}."

        # Semantic parsing: User Role / Profession
        role_m = re.search(r"\b(?:i\s+work\s+as\s+(?:an?|the)?|my\s+(?:role|job|profession)\s+is)\s+([a-zA-Z\s\-]+)", clean_fact, re.I)
        if role_m:
            extracted_role = role_m.group(1).strip().strip(".!?,")
            self.set_profile("role", extracted_role)
            return f"Got it. Your role is {extracted_role}."

        try:
            conn = self._get_connection()
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

    @staticmethod
    def _parse_natural_due_time(time_str: str) -> Optional[datetime.datetime]:
        """Parse natural language date/time strings into a concrete datetime object."""
        if not time_str:
            return None
        text = time_str.lower().strip()
        now = datetime.datetime.now()

        # Relative delay: "in X minutes / seconds / hours"
        rel_m = re.search(r"(\d+(?:\.\d+)?)\s*(seconds?|secs?|minutes?|mins?|hours?|hrs?)", text)
        if rel_m and ("in " in text or "after " in text or len(text.split()) <= 4):
            val = float(rel_m.group(1))
            unit = rel_m.group(2)
            if "sec" in unit:
                return now + datetime.timedelta(seconds=val)
            elif "min" in unit:
                return now + datetime.timedelta(minutes=val)
            elif "hour" in unit or "hr" in unit:
                return now + datetime.timedelta(hours=val)

        # "tomorrow at 3pm" / "tomorrow 15:30" / "tomorrow"
        is_tomorrow = "tomorrow" in text
        time_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text.replace("tomorrow", ""))
        target_date = (now + datetime.timedelta(days=1)) if is_tomorrow else now

        if time_match and time_match.group(1):
            h = int(time_match.group(1))
            m = int(time_match.group(2)) if time_match.group(2) else 0
            meridiem = time_match.group(3)
            if meridiem == "pm" and h < 12:
                h += 12
            elif meridiem == "am" and h == 12:
                h = 0
            target_dt = target_date.replace(hour=h, minute=m, second=0, microsecond=0)
            if not is_tomorrow and target_dt <= now:
                target_dt += datetime.timedelta(days=1)
            return target_dt

        if is_tomorrow:
            # Default tomorrow morning 9:00 AM
            return target_date.replace(hour=9, minute=0, second=0, microsecond=0)

        return None

    def add_reminder(
        self,
        message: str,
        minutes: float = 0,
        hours: float = 0,
        seconds: float = 0,
        due_time: str = ""
    ) -> str:
        """Schedule a real-time timer or date/event reminder with second precision and natural time parsing."""
        clean_msg = message.strip()
        target_dt = None

        if due_time:
            target_dt = self._parse_natural_due_time(due_time)

        if not target_dt:
            time_m = re.search(r"\b(?:tomorrow\s+at\s+\d+(?::\d+)?\s*(?:am|pm)?|tomorrow|\bat\s+\d+(?::\d+)?\s*(?:am|pm)?|tonight\s+at\s+\d+(?:am|pm)?|in\s+\d+\s*(?:mins?|minutes?|hours?|secs?|seconds?))\b", clean_msg, re.I)
            if time_m:
                extracted = time_m.group(0)
                target_dt = self._parse_natural_due_time(extracted)
                clean_msg = clean_msg.replace(extracted, "").strip()

        if not target_dt:
            total_seconds = seconds + minutes * 60 + hours * 3600
            if total_seconds > 0:
                target_dt = datetime.datetime.now() + datetime.timedelta(seconds=total_seconds)

        if not target_dt or target_dt <= datetime.datetime.now():
            return "Reminder time must be in the future (e.g. 'in 5 minutes', 'tomorrow at 3pm')."

        delta_sec = (target_dt - datetime.datetime.now()).total_seconds()
        human_time = self._format_delta(delta_sec)
        dt_str = target_dt.strftime("%Y-%m-%d %H:%M:%S")

        is_timer = clean_msg.lower().startswith("timer")

        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO reminders (message, fire_at) VALUES (?, ?)",
                (clean_msg, dt_str),
            )
            conn.commit()
            conn.close()

            if is_timer:
                return f"Timer set for {human_time}."
            else:
                formatted_dt = target_dt.strftime("%I:%M %p") if target_dt.date() == datetime.date.today() else target_dt.strftime("%b %d at %I:%M %p")
                return f"Reminder set for {formatted_dt}: '{clean_msg}'."
        except Exception as e:
            return f"Failed to set reminder: {e}"

    @staticmethod
    def _format_delta(seconds: float) -> str:
        """Human-readable time delta string."""
        seconds = int(max(1, seconds))
        if seconds < 60:
            return f"{seconds} second{'s' if seconds != 1 else ''}"
        if seconds < 3600:
            m = seconds // 60
            s = seconds % 60
            return f"{m} minute{'s' if m != 1 else ''}{f' {s}s' if s else ''}"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h} hour{'s' if h != 1 else ''}{f' {m}m' if m else ''}"

    def _start_reminder_daemon(self):
        """High-precision daemon polling every 1 second for exact timer and reminder alarms."""
        def _poll():
            while True:
                try:
                    self._fire_due_reminders()
                except Exception:
                    pass
                time.sleep(1.0)

        t = threading.Thread(target=_poll, daemon=True, name="LayaReminderDaemon")
        t.start()

    def _fire_due_reminders(self):
        """Fire any reminders that are due and mark them as fired."""
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = None
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, message FROM reminders WHERE fired=0 AND fire_at <= ?",
                (now_str,)
            )
            due = cursor.fetchall()
            for r_id, message in due:
                cursor.execute("UPDATE reminders SET fired=1 WHERE id=?", (r_id,))
                self._dispatch_reminder(message)
            conn.commit()
        except Exception as e:
            # print error for debugging
            pass
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def _dispatch_reminder(self, message: str):
        """Fire reminder via spoken TTS and native Windows toast notification."""
        clean_text = message.strip()
        is_timer = clean_text.lower().startswith("timer")

        if is_timer:
            label = re.sub(r"^timer(?::\s*|\s+for\s+|\s+)?", "", clean_text, flags=re.I).strip()
            spoken_alert = f"Time's up! Your timer for '{label}' has finished." if label and label.lower() != "timer" else "Time's up! Your timer has finished."
            toast_title = "Laya Timer Alert"
        else:
            spoken_alert = f"Reminder: {clean_text}"
            toast_title = "Laya Scheduled Reminder"

        # Windows toast notification
        try:
            import subprocess
            safe_msg = spoken_alert.replace("'", "").replace('"', "")
            ps_cmd = (
                '[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null;'
                '$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);'
                + f'$template.GetElementsByTagName("text")[0].InnerText = "{toast_title}";'
                + f'$template.GetElementsByTagName("text")[1].InnerText = "{safe_msg}";'
                + '[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Laya").Show([Windows.UI.Notifications.ToastNotification]::new($template))'
            )
            subprocess.Popen(
                ["powershell", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                creationflags=0x08000000  # CREATE_NO_WINDOW
            )
        except Exception:
            pass

        # Speak aloud via TTS
        try:
            from laya.audio.tts import get_tts_engine
            get_tts_engine().speak(spoken_alert)
        except Exception:
            pass

    def list_reminders(self) -> str:
        """Return all active pending timers and reminders."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT message, fire_at FROM reminders WHERE fired=0 ORDER BY fire_at"
            )
            rows = cursor.fetchall()
            conn.close()
            if not rows:
                return "No pending timers or reminders."
            lines = [f"• {msg} (at {ft})" for msg, ft in rows]
            return "Pending timers and reminders:\n" + "\n".join(lines)
        except Exception as e:
            return f"Error listing reminders: {e}"

    def cancel_reminders(self, query: str = "") -> str:
        """Cancel pending timers or reminders."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            clean_q = (query or "").strip().lower()
            if not clean_q or clean_q in ["all", "everything", "all reminders", "all timers"]:
                cursor.execute("UPDATE reminders SET fired=1 WHERE fired=0")
                count = cursor.rowcount
                conn.commit()
                conn.close()
                if count > 0:
                    return f"Cancelled {count} pending timer{'s' if count != 1 else ''}."
                return "No active timers or reminders were pending."
            else:
                cursor.execute("UPDATE reminders SET fired=1 WHERE fired=0 AND LOWER(message) LIKE ?", (f"%{clean_q}%",))
                count = cursor.rowcount
                conn.commit()
                conn.close()
                if count > 0:
                    return f"Cancelled {count} reminder{'s' if count != 1 else ''} matching '{query}'."
                return f"No pending reminders found matching '{query}'."
        except Exception as e:
            return f"Error cancelling reminders: {e}"

    # -------------------------------------------------------------
    # Structured Task Management
    # -------------------------------------------------------------
    def add_task(self, title: str, due_date: Optional[str] = None, priority: str = "normal") -> str:
        """Add a structured task or to-do item."""
        clean_title = title.strip()
        if not clean_title:
            return "Task title cannot be empty."
        with self._lock:
            conn = None
            try:
                conn = self._get_connection()
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO tasks (title, due_date, priority, status) VALUES (?, ?, ?, 'pending')",
                    (clean_title, due_date, priority)
                )
                due_str = f" (due {due_date})" if due_date else ""
                return f"Added task: '{clean_title}'{due_str}."
            except Exception as e:
                return f"Failed to add task: {e}"
            finally:
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass

    def list_tasks(self, status: str = "pending") -> str:
        """List tasks by status ('pending', 'completed', or 'all')."""
        with self._lock:
            conn = None
            try:
                conn = self._get_connection()
                cur = conn.cursor()
                if status == "all":
                    cur.execute("SELECT id, title, due_date, status FROM tasks ORDER BY id DESC LIMIT 15")
                else:
                    cur.execute("SELECT id, title, due_date, status FROM tasks WHERE status = ? ORDER BY id DESC LIMIT 15", (status,))
                rows = cur.fetchall()
                if not rows:
                    return f"No {status} tasks found."
                lines = []
                for t_id, t_title, t_due, t_status in rows:
                    d_str = f" [Due: {t_due}]" if t_due else ""
                    s_icon = "✓" if t_status == "completed" else "○"
                    lines.append(f"{s_icon} #{t_id}: {t_title}{d_str}")
                return "Active Tasks:\n" + "\n".join(lines)
            except Exception as e:
                return f"Error reading tasks: {e}"
            finally:
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass

    def complete_task(self, query: str) -> str:
        """Mark a task as completed by ID or title keyword."""
        with self._lock:
            conn = None
            try:
                conn = self._get_connection()
                cur = conn.cursor()
                clean_q = query.strip()
                if clean_q.isdigit():
                    cur.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (int(clean_q),))
                else:
                    cur.execute("UPDATE tasks SET status = 'completed' WHERE status = 'pending' AND LOWER(title) LIKE ?", (f"%{clean_q.lower()}%",))
                count = cur.rowcount
                if count > 0:
                    return f"Completed {count} task{'s' if count != 1 else ''}."
                return f"No pending task found matching '{query}'."
            except Exception as e:
                return f"Error completing task: {e}"
            finally:
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass

    def clear_memory(self, query: str = "") -> str:
        """Clear memory facts or reset session state."""
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            clean_q = (query or "").strip().lower()
            if clean_q in ["all", "everything", "reset"]:
                cur.execute("DELETE FROM facts")
                cur.execute("DELETE FROM tasks")
                cur.execute("DELETE FROM reminders")
                conn.commit()
                conn.close()
                self.clean_messy_memory()
                return "Reset memory facts and tasks to clean baseline."
            elif clean_q in ["tasks", "all tasks"]:
                cur.execute("DELETE FROM tasks")
                conn.commit()
                conn.close()
                return "Cleared all tasks."
            elif clean_q in ["facts", "all facts"]:
                cur.execute("DELETE FROM facts")
                conn.commit()
                conn.close()
                self.clean_messy_memory()
                return "Cleared all facts."
            else:
                cur.execute("DELETE FROM facts WHERE LOWER(fact) LIKE ?", (f"%{clean_q}%",))
                cnt = cur.rowcount
                conn.commit()
                conn.close()
                return f"Removed {cnt} fact{'s' if cnt != 1 else ''} matching '{query}'."
        except Exception as e:
            return f"Error clearing memory: {e}"


    def search_facts(self, query: str) -> str:
        """Search memory for relevant facts using keyword matching."""
        q_words = [w.lower() for w in query.split() if len(w) > 2]
        if not q_words:
            return self.get_all_summary()

        try:
            conn = self._get_connection()
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
            conn = self._get_connection()
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
            conn = self._get_connection()
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
            conn = self._get_connection()
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
            conn = self._get_connection()
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
            conn = self._get_connection()
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
