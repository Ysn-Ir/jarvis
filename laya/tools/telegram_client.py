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

        try:
            from dotenv import load_dotenv
            load_dotenv()
        except Exception:
            pass

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
        """Always create a fresh event loop in a new thread to avoid 'already running' conflicts."""
        import concurrent.futures
        return None  # Telethon async calls go through _run_async_safe

    def _run_async_safe(self, coro):
        """Run an async coroutine safely in an isolated thread with its own event loop."""
        import concurrent.futures
        result_holder = []
        error_holder = []

        def _thread_run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result_holder.append(loop.run_until_complete(coro))
            except Exception as e:
                error_holder.append(e)
            finally:
                loop.close()

        t = __import__('threading').Thread(target=_thread_run, daemon=True)
        t.start()
        t.join(timeout=12.0)
        if error_holder:
            raise error_holder[0]
        return result_holder[0] if result_holder else None

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

    def _ensure_telegram_window(self) -> Optional[Dict[str, Any]]:
        """Ensure Telegram Desktop is running, restored from tray, and ready."""
        from laya.tools.win32_utils import ensure_desktop_access, find_window_by_query, robust_bring_to_front
        ensure_desktop_access()
        win = find_window_by_query("telegram")
        if win and win.get("hwnd"):
            robust_bring_to_front(win["hwnd"])
            return win

        # If minimized to tray or closed, launch / restore Telegram Desktop
        tg_paths = [
            os.path.expandvars(r"%APPDATA%\Telegram Desktop\Telegram.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Telegram Desktop\Telegram.exe"),
            r"C:\Users\khali\AppData\Roaming\Telegram Desktop\Telegram.exe",
        ]
        launched = False
        for p in tg_paths:
            if os.path.exists(p):
                try:
                    os.startfile(p)
                    launched = True
                    break
                except Exception:
                    pass
        if not launched:
            try:
                os.startfile("tg://")
                launched = True
            except Exception:
                pass

        if launched:
            time.sleep(1.0)
            ensure_desktop_access()
            win = find_window_by_query("telegram")
            if win and win.get("hwnd"):
                robust_bring_to_front(win["hwnd"])
                return win
        return None

    # -------------------------------------------------------------
    # 0. Launch & Desktop Activation
    # -------------------------------------------------------------
    def open_telegram(self, target: str = "") -> str:
        """Launch or bring Telegram Desktop to front, optionally focusing a chat or contact."""
        target = (target or "").strip()
        if target:
            clean = target.lstrip("@").strip()
            if target.startswith("@") and re.match(r"^[a-zA-Z0-9_]{3,32}$", clean):
                try:
                    os.startfile(f"tg://resolve?domain={urllib.parse.quote(clean)}")
                    time.sleep(0.5)
                    self._ensure_telegram_window()
                    return f"Opened Telegram chat with @{clean}."
                except Exception:
                    pass
            elif re.match(r"^\+?\d{8,15}$", clean):
                try:
                    os.startfile(f"tg://resolve?phone={urllib.parse.quote(clean)}")
                    time.sleep(0.5)
                    self._ensure_telegram_window()
                    return f"Opened Telegram chat for {clean}."
                except Exception:
                    pass

        # General launch or bring to front
        win = self._ensure_telegram_window()
        if win:
            return "Telegram Desktop opened."

        # Fallback to protocol
        try:
            os.startfile("tg://")
            return "Launching Telegram."
        except Exception:
            pass

        # Fallback to web
        try:
            import webbrowser
            webbrowser.open("https://web.telegram.org")
            return "Opening Telegram Web in browser."
        except Exception as e:
            return f"Failed to launch Telegram: {e}"

    def launch_login_gui(self) -> str:
        """Launch the Telegram login authentication window."""
        import subprocess
        try:
            cmd = [sys.executable, "-m", "laya.tools.telegram_login"]
            subprocess.Popen(cmd)
            return "Telegram setup window opened."
        except Exception as e:
            return f"Could not launch Telegram login GUI: {e}"

    # -------------------------------------------------------------
    # 1. Send Message
    # -------------------------------------------------------------
    def send_message(self, recipient: str, message: str) -> str:
        """Send a message to a contact, username, or active conversation."""
        recipient = (recipient or "").strip()
        message = (message or "").strip()

        # Check if recipient is targeting the current/latest conversation
        is_latest = recipient.lower() in [
            "latest", "recent", "current", "latest conversation", "last conversation",
            "current chat", "last chat", "this chat", "the latest conversation",
            "active chat", "active conversation", "the active chat", ""
        ]

        from laya.tools.win32_utils import ensure_desktop_access, robust_bring_to_front
        ensure_desktop_access()

        hud_lowered = False
        try:
            from laya.ui.hud import LayaHUD
            if hasattr(LayaHUD, "_active_instance") and LayaHUD._active_instance:
                LayaHUD._active_instance.attributes("-topmost", False)
                hud_lowered = True
        except Exception:
            pass

        try:
            return self._send_message_impl(recipient=recipient, message=message, is_latest=is_latest)
        finally:
            if hud_lowered:
                try:
                    LayaHUD._active_instance.attributes("-topmost", True)
                except Exception:
                    pass

    def _send_message_impl(self, recipient: str, message: str, is_latest: bool) -> str:
        from laya.tools.win32_utils import robust_bring_to_front
        win = self._ensure_telegram_window()
        if not win or not win.get("hwnd"):
            # Launch Telegram Desktop
            tg_paths = [
                os.path.expandvars(r"%APPDATA%\Telegram Desktop\Telegram.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Telegram Desktop\Telegram.exe"),
            ]
            for tp in tg_paths:
                if os.path.exists(tp):
                    os.startfile(tp)
                    time.sleep(1.2)
                    win = self._ensure_telegram_window()
                    break

        import pyperclip
        import pyautogui

        if is_latest:
            if win and win.get("hwnd"):
                hwnd = win["hwnd"]
                robust_bring_to_front(hwnd)
                time.sleep(0.3)
                pyautogui.press("escape")
                time.sleep(0.1)
                import win32gui
                try:
                    rect = win32gui.GetWindowRect(hwnd)
                except Exception:
                    rect = None
                if rect:
                    input_x = rect[0] + int((rect[2] - rect[0]) * 0.6)
                    input_y = rect[3] - 40
                    pyautogui.click(input_x, input_y)
                    time.sleep(0.1)
                if message:
                    pyperclip.copy(message)
                    pyautogui.hotkey("ctrl", "v")
                    time.sleep(0.15)
                    pyautogui.press("enter")
                    return f"Dispatched message to active Telegram conversation: '{message}'"
                return "Focused active Telegram conversation."

        target, contact = self._resolve_target(recipient)
        display_name = contact["name"] if contact else target

        # Try headless Telethon if configured
        if self.is_headless_ready():
            try:
                result = self._run_async_safe(self._telethon_send(target, message))
                if result:
                    return f"Sent Telegram message to {display_name}: '{message}'"
            except Exception as e:
                print(f"[TelegramManager] Headless send fallback: {e}")

        # If Telethon API is not authenticated, abandon desktop GUI automation per user instructions
        return (
            f"Telegram API session is not authenticated. To send Telegram messages via API, "
            f"please authenticate by running 'python -m laya.tools.telegram_login' "
            f"using your configured API ID ({self.api_id or 'not set'})."
        )


    def call(self, recipient: str, call_type: str = "voice") -> str:
        """Call a contact on Telegram via desktop application."""
        target, contact = self._resolve_target(recipient)
        display_name = contact["name"] if contact else target

        from laya.tools.win32_utils import ensure_desktop_access, robust_bring_to_front, find_window_by_query
        ensure_desktop_access()
        win = find_window_by_query("telegram")
        if not win or not win.get("hwnd"):
            try:
                os.startfile(f"tg://resolve?domain={urllib.parse.quote(target)}")
                time.sleep(1.2)
                win = find_window_by_query("telegram")
            except Exception:
                pass

        if win and win.get("hwnd"):
            hwnd = win["hwnd"]
            robust_bring_to_front(hwnd)
            time.sleep(0.25)
            try:
                os.startfile(f"tg://resolve?domain={urllib.parse.quote(target)}")
                time.sleep(0.4)
            except Exception:
                pass
            robust_bring_to_front(hwnd)
            time.sleep(0.15)
            import pyautogui
            pyautogui.hotkey("ctrl", "u")
            return f"Initiated Telegram voice call to {display_name}."
        return f"Could not locate Telegram window to call {display_name}."

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
                msgs = self._run_async_safe(self._telethon_read(target, limit))
                if msgs:
                    formatted = [f"• {m['sender']}: {m['text']}" for m in msgs]
                    return f"Recent messages from {display_name}:\n" + "\n".join(formatted)
                return f"No recent messages found with {display_name}."
            except Exception as e:
                print(f"[TelegramManager] Headless read error: {e}")

        # Fallback: Open the chat so user can see it
        try:
            os.startfile(f"tg://resolve?domain={urllib.parse.quote(target.lstrip('@'))}")            
            return f"Opened Telegram chat for {display_name}."
        except Exception:
            os.startfile(f"https://t.me/{urllib.parse.quote(target.lstrip('@'))}")
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
                results = self._run_async_safe(self._telethon_search(clean_q, limit))
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

    # -------------------------------------------------------------
    # 4. Broadcast Message to All Contacts / Users
    # -------------------------------------------------------------
    def broadcast_message(self, message: str, limit: int = 30) -> str:
        """Broadcast a message to contacts and active user chats."""
        clean_msg = message.strip()
        if not clean_msg:
            return "Please specify the message content to broadcast."

        # 1. Telethon Headless Broadcast (Fast, Silent, Background)
        if self.is_headless_ready():
            try:
                count = self._run_async_safe(self._telethon_broadcast(clean_msg, limit))
                return f"Successfully broadcasted Telegram message to {count} users/contacts."
            except Exception as e:
                print(f"[TelegramManager] Headless broadcast error: {e}")

        # 2. Desktop UI Broadcast Fallback
        # If user has contacts in ContactsStore, send to all contacts with Telegram
        contacts_store = get_contacts_store()
        all_contacts = contacts_store.list_contacts()
        tg_contacts = [c for c in all_contacts if c.get("telegram") or c.get("phone")]

        if tg_contacts:
            sent_names = []
            for c in tg_contacts[:limit]:
                target = c.get("telegram") or c.get("name")
                self.send_message(target, clean_msg)
                sent_names.append(c["name"])
                time.sleep(0.5)
            return f"Broadcasted message to {len(sent_names)} saved contacts: {', '.join(sent_names)}."

        # If no contacts in store, cycle through recent active chats in Telegram Desktop
        from laya.tools.win32_utils import robust_bring_to_front
        win = self._ensure_telegram_window()
        if win and win.get("hwnd"):
            hwnd = win["hwnd"]
            robust_bring_to_front(hwnd)
            time.sleep(0.2)
            import pyautogui, pyperclip
            pyautogui.press("escape")
            time.sleep(0.1)

            # Send to current active chat, then cycle through next chats
            pyperclip.copy(clean_msg)
            count = 0
            for i in range(min(limit, 10)):
                robust_bring_to_front(hwnd)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.15)
                pyautogui.press("enter")
                count += 1
                time.sleep(0.3)
                # Switch to next chat down (Alt + Down in Telegram Desktop)
                pyautogui.hotkey("alt", "down")
                time.sleep(0.25)
            return f"Broadcasted Telegram message to {count} recent chats in Telegram Desktop."

        return "Could not locate Telegram Desktop or Telethon session to broadcast message."

    def save_credentials(self, api_id: str, api_hash: str) -> str:
        """Save Telegram API credentials into .env and reload them."""
        clean_id = api_id.strip()
        clean_hash = api_hash.strip()
        if not clean_id or not clean_hash:
            return "Please provide both a valid Telegram API ID and API Hash."

        self.api_id = clean_id
        self.api_hash = clean_hash

        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        try:
            content = ""
            if env_path.exists():
                content = env_path.read_text(encoding="utf-8")

            if "TELEGRAM_API_ID=" in content:
                content = re.sub(r"TELEGRAM_API_ID=.*", f"TELEGRAM_API_ID={clean_id}", content)
            else:
                content += f"\nTELEGRAM_API_ID={clean_id}"

            if "TELEGRAM_API_HASH=" in content:
                content = re.sub(r"TELEGRAM_API_HASH=.*", f"TELEGRAM_API_HASH={clean_hash}", content)
            else:
                content += f"\nTELEGRAM_API_HASH={clean_hash}"

            env_path.write_text(content.strip() + "\n", encoding="utf-8")
            os.environ["TELEGRAM_API_ID"] = clean_id
            os.environ["TELEGRAM_API_HASH"] = clean_hash
            return f"Telegram credentials successfully saved for API ID {clean_id}."
        except Exception as e:
            return f"Error saving credentials to .env: {e}"

    def launch_login_gui(self) -> str:
        """Launch the graphical Telegram Login setup window."""
        import subprocess
        script_path = Path(__file__).parent / "telegram_login.py"
        try:
            subprocess.Popen([sys.executable, str(script_path)], close_fds=True)
            return "Opened the Telegram Login window on your screen. Enter your API credentials to connect."
        except Exception as e:
            return f"Could not launch login window: {e}"

    async def _telethon_broadcast(self, message: str, limit: int = 30) -> int:
        from telethon import TelegramClient
        client = TelegramClient(self.session_path, int(self.api_id), self.api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return 0

        count = 0
        dialogs = await client.get_dialogs(limit=limit * 2)
        for d in dialogs:
            if d.is_user and not getattr(d.entity, "bot", False) and not getattr(d.entity, "is_self", False):
                try:
                    await client.send_message(d.entity, message)
                    count += 1
                    if count >= limit:
                        break
                    await asyncio.sleep(0.4)  # Anti-flood delay
                except Exception as ex:
                    print(f"[Telethon Broadcast] Failed to send to {d.name}: {ex}")

        await client.disconnect()
        return count

    # -------------------------------------------------------------
    # 5. Telegram Contacts Retrieval & Sync
    # -------------------------------------------------------------
    def get_telegram_contacts(self) -> List[Dict[str, Any]]:
        """Retrieve contacts from Telegram via Telethon or local store."""
        if self.is_headless_ready():
            try:
                return self._run_async_safe(self._telethon_get_contacts()) or []
            except Exception as e:
                print(f"[TelegramManager] get_contacts error: {e}")

        # Return contacts from local store that have telegram
        return [c for c in get_contacts_store().list_contacts() if c.get("telegram")]

    async def _telethon_get_contacts(self) -> List[Dict[str, Any]]:
        from telethon import TelegramClient
        from telethon.tl.functions.contacts import GetContactsRequest
        client = TelegramClient(self.session_path, int(self.api_id), self.api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return []

        contact_list = []
        try:
            result = await client(GetContactsRequest(hash=0))
            for user in getattr(result, "users", []):
                name = f"{getattr(user, 'first_name', '') or ''} {getattr(user, 'last_name', '') or ''}".strip()
                username = getattr(user, "username", "") or ""
                phone = getattr(user, "phone", "") or ""
                contact_list.append({
                    "name": name or username or "Unknown",
                    "username": username,
                    "phone": phone,
                    "id": user.id
                })
        except Exception as e:
            print(f"[Telethon] GetContactsRequest error: {e}")

        # Also get from recent dialogs (users you've chatted with)
        try:
            dialogs = await client.get_dialogs(limit=50)
            seen_ids = {c["id"] for c in contact_list}
            for d in dialogs:
                if d.is_user and not getattr(d.entity, "bot", False) and not getattr(d.entity, "is_self", False):
                    u = d.entity
                    if u.id not in seen_ids:
                        name = f"{getattr(u, 'first_name', '') or ''} {getattr(u, 'last_name', '') or ''}".strip()
                        contact_list.append({
                            "name": name or getattr(u, "username", "") or d.name,
                            "username": getattr(u, "username", "") or "",
                            "phone": getattr(u, "phone", "") or "",
                            "id": u.id
                        })
                        seen_ids.add(u.id)
        except Exception as e:
            print(f"[Telethon] Dialogs error: {e}")

        await client.disconnect()
        return contact_list

    def sync_telegram_contacts(self) -> str:
        """Fetch all contacts from Telegram and import them into Laya address book."""
        contacts = self.get_telegram_contacts()
        if not contacts:
            if not self.is_headless_ready():
                return (
                    "To automatically sync Telegram contacts, connect your Telegram API credentials in .env "
                    "or run 'python -m laya.tools.telegram_login'. You can also manually add contacts using "
                    "'Add contact [Name] with telegram [@username]'."
                )
            return "No contacts found on your Telegram account."

        cs = get_contacts_store()
        added = 0
        for c in contacts:
            name = c.get("name") or c.get("username")
            if name:
                cs.save_contact(
                    name=name,
                    telegram=c.get("username", ""),
                    phone=c.get("phone", "")
                )
                added += 1

        return f"Successfully imported and synced {added} Telegram contacts into Laya!"

    def list_telegram_contacts(self) -> str:
        """List contacts from Telegram."""
        contacts = self.get_telegram_contacts()
        if not contacts:
            # Fall back to local store
            cs = get_contacts_store()
            contacts = [c for c in cs.list_contacts() if c.get("telegram")]

        if not contacts:
            return "No Telegram contacts found. Say 'Sync telegram contacts' or add one via 'Add contact [Name] with telegram [@username]'."

        lines = []
        for c in contacts[:25]:
            t = f"@{c.get('username') or c.get('telegram')}" if (c.get("username") or c.get("telegram")) else ""
            p = c.get("phone", "")
            details = ", ".join(filter(None, [t, p]))
            lines.append(f"• {c['name']} ({details})" if details else f"• {c['name']}")

        header = f"Telegram Contacts ({len(contacts)} total):\n"
        return header + "\n".join(lines)


def win32gui_get_rect(hwnd: int):
    """Get window RECT via win32gui, returns (left, top, right, bottom) or None."""
    try:
        import win32gui as _w
        return _w.GetWindowRect(hwnd)  # (left, top, right, bottom)
    except Exception:
        return None


def get_telegram_manager() -> TelegramManager:
    return TelegramManager.get_instance()
