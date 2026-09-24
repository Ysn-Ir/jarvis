"""
Laya Telegram Manager
Provides headless MTProto integration via Telethon with seamless fallback to
Windows protocol URIs (tg:// and t.me) for zero-latency messaging, reading, and searching.
"""

import os
import re
import sys
import time
import asyncio
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from laya.tools.contacts_store import get_contacts_store


class TelegramManager:
    _instance: Optional["TelegramManager"] = None

    def __init__(self):
        self.base_dir = Path.home() / ".laya"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.session_path = str(self.base_dir / "telegram.session")

        # Optional API keys from environment
        self.api_id = os.getenv("TELEGRAM_API_ID")
        self.api_hash = os.getenv("TELEGRAM_API_HASH")

        self._client = None
        self._loop = None

    @classmethod
    def get_instance(cls) -> "TelegramManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_or_create_loop(self):
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def _resolve_target(self, query: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Resolve contact name, alias, or raw username/phone."""
        contacts = get_contacts_store()
        contact = contacts.get_contact(query)
        if contact:
            target = contact.get("telegram") or contact.get("phone") or query
            return target.lstrip("@"), contact

        clean = query.strip().lstrip("@")
        return clean, None

    def is_headless_ready(self) -> bool:
        """Check if Telethon has saved credentials and an active session."""
        has_session = os.path.exists(self.session_path) or os.path.exists(f"{self.session_path}.session")
        return bool(self.api_id and self.api_hash and has_session)

    # -------------------------------------------------------------
    # 1. Send Message
    # -------------------------------------------------------------
    def send_message(self, recipient: str, message: str) -> str:
        """Send a message to a contact or username."""
        target, contact = self._resolve_target(recipient)
        display_name = contact["name"] if contact else target

        # Try headless Telethon if configured
        if self.is_headless_ready():
            try:
                loop = self._get_or_create_loop()
                result = loop.run_until_complete(self._telethon_send(target, message))
                if result:
                    return f"Sent Telegram message to {display_name}: '{message}'"
            except Exception as e:
                print(f"[TelegramManager] Headless send fallback: {e}")

        # Instant OS Protocol URI (Zero setup, works out of the box)
        try:
            tg_url = f"tg://msg?to={urllib.parse.quote(target)}&text={urllib.parse.quote(message)}"
            os.startfile(tg_url)
            return f"Opened Telegram message to {display_name}: '{message}'"
        except Exception:
            pass

        # Browser / Web Fallback
        web_url = f"https://t.me/{urllib.parse.quote(target)}" if target else "https://web.telegram.org"
        try:
            os.startfile(web_url)
            return f"Opened Telegram chat for {display_name} in browser."
        except Exception as e:
            return f"Failed to dispatch Telegram message: {e}"

    async def _telethon_send(self, target: str, message: str) -> bool:
        from telethon import TelegramClient
        client = TelegramClient(self.session_path, int(self.api_id), self.api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return False

        await client.send_message(target, message)
        await client.disconnect()
        return True

    # -------------------------------------------------------------
    # 2. Read Recent Messages
    # -------------------------------------------------------------
    def read_messages(self, recipient: str, limit: int = 5) -> str:
        """Read recent messages from a contact or chat."""
        target, contact = self._resolve_target(recipient)
        display_name = contact["name"] if contact else target

        if self.is_headless_ready():
            try:
                loop = self._get_or_create_loop()
                msgs = loop.run_until_complete(self._telethon_read(target, limit))
                if msgs:
                    formatted = [f"• {m['sender']}: {m['text']}" for m in msgs]
                    return f"Recent messages from {display_name}:\n" + "\n".join(formatted)
                return f"No recent messages found with {display_name}."
            except Exception as e:
                print(f"[TelegramManager] Headless read error: {e}")

        # Fallback: Open the chat so user can see it
        try:
            os.startfile(f"tg://resolve?domain={urllib.parse.quote(target)}")
            return f"Opened Telegram chat for {display_name}."
        except Exception:
            os.startfile(f"https://t.me/{urllib.parse.quote(target)}")
            return f"Opened Telegram profile for {display_name}."

    async def _telethon_read(self, target: str, limit: int) -> List[Dict[str, str]]:
        from telethon import TelegramClient
        client = TelegramClient(self.session_path, int(self.api_id), self.api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return []

        results = []
        async for message in client.iter_messages(target, limit=limit):
            sender = "Them" if message.out is False else "You"
            if message.text:
                results.append({"sender": sender, "text": message.text.strip()})

        await client.disconnect()
        return results

    # -------------------------------------------------------------
    # 3. Search Messages
    # -------------------------------------------------------------
    def search_messages(self, query: str, limit: int = 5) -> str:
        """Search messages globally across Telegram chats."""
        clean_q = query.strip()
        if not clean_q:
            return "Please specify a query to search in Telegram."

        if self.is_headless_ready():
            try:
                loop = self._get_or_create_loop()
                results = loop.run_until_complete(self._telethon_search(clean_q, limit))
                if results:
                    formatted = [f"• [{r['chat']}] {r['sender']}: {r['text']}" for r in results]
                    return f"Telegram search results for '{clean_q}':\n" + "\n".join(formatted)
                return f"No messages found matching '{clean_q}' on Telegram."
            except Exception as e:
                print(f"[TelegramManager] Search error: {e}")

        # Fallback: Open Telegram Desktop or Web search
        os.startfile(f"https://web.telegram.org/a/#?q={urllib.parse.quote(clean_q)}")
        return f"Opened Telegram search for '{clean_q}'."

    async def _telethon_search(self, query: str, limit: int) -> List[Dict[str, str]]:
        from telethon import TelegramClient
        client = TelegramClient(self.session_path, int(self.api_id), self.api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return []

        results = []
        async for message in client.iter_messages(None, search=query, limit=limit):
            chat_name = getattr(message.chat, "title", None) or getattr(message.chat, "first_name", "Chat")
            sender = "Them" if message.out is False else "You"
            if message.text:
                results.append({"chat": chat_name, "sender": sender, "text": message.text.strip()})

        await client.disconnect()
        return results


def get_telegram_manager() -> TelegramManager:
    return TelegramManager.get_instance()
