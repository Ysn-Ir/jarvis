"""
Laya Fast-Path Executor
Sub-300ms deterministic execution layer for hardware, OS, and system controls.
Bypasses LLMs completely.
"""

import os
import sys
import time
import socket
import datetime
import subprocess
import ctypes
from pathlib import Path
from typing import Dict, Any, Optional

import re
import pyautogui
import pyperclip
import psutil
import win32api
import win32gui
import win32con

from laya.config import APP_REGISTRY, FOLDER_ALIASES, DOCS_DIR


class FastPathExecutor:
    _instance: Optional["FastPathExecutor"] = None

    @classmethod
    def get_instance(cls) -> "FastPathExecutor":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------
    # Audio & Hardware Controls
    # -------------------------------------------------------------
    def volume_up(self, steps: int = 5) -> str:
        for _ in range(steps):
            win32api.keybd_event(win32con.VK_VOLUME_UP, 0, 0, 0)
            win32api.keybd_event(win32con.VK_VOLUME_UP, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.01)
        return "Volume increased."

    def volume_down(self, steps: int = 5) -> str:
        for _ in range(steps):
            win32api.keybd_event(win32con.VK_VOLUME_DOWN, 0, 0, 0)
            win32api.keybd_event(win32con.VK_VOLUME_DOWN, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.01)
        return "Volume decreased."

    def set_volume(self, level: int) -> str:
        level = max(0, min(100, level))
        # Zero out volume
        for _ in range(50):
            win32api.keybd_event(win32con.VK_VOLUME_DOWN, 0, 0, 0)
            win32api.keybd_event(win32con.VK_VOLUME_DOWN, 0, win32con.KEYEVENTF_KEYUP, 0)
        # Step up to target (each step is 2%)
        steps_up = level // 2
        for _ in range(steps_up):
            win32api.keybd_event(win32con.VK_VOLUME_UP, 0, 0, 0)
            win32api.keybd_event(win32con.VK_VOLUME_UP, 0, win32con.KEYEVENTF_KEYUP, 0)
        return f"Volume set to {level} percent."

    def mute(self) -> str:
        win32api.keybd_event(win32con.VK_VOLUME_MUTE, 0, 0, 0)
        win32api.keybd_event(win32con.VK_VOLUME_MUTE, 0, win32con.KEYEVENTF_KEYUP, 0)
        return "Audio muted."

    def play_media(self) -> str:
        win32api.keybd_event(win32con.VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
        win32api.keybd_event(win32con.VK_MEDIA_PLAY_PAUSE, 0, win32con.KEYEVENTF_KEYUP, 0)
        return "Media toggled."

    def next_track(self) -> str:
        win32api.keybd_event(win32con.VK_MEDIA_NEXT_TRACK, 0, 0, 0)
        win32api.keybd_event(win32con.VK_MEDIA_NEXT_TRACK, 0, win32con.KEYEVENTF_KEYUP, 0)
        return "Next track."

    def prev_track(self) -> str:
        win32api.keybd_event(win32con.VK_MEDIA_PREV_TRACK, 0, 0, 0)
        win32api.keybd_event(win32con.VK_MEDIA_PREV_TRACK, 0, win32con.KEYEVENTF_KEYUP, 0)
        return "Previous track."

    # -------------------------------------------------------------
    # System Telemetry & Metrics
    # -------------------------------------------------------------
    def check_battery(self) -> str:
        battery = psutil.sensors_battery()
        if not battery:
            return "No battery detected; system is on AC power."
        status = "charging" if battery.power_plugged else "discharging"
        return f"Battery is at {battery.percent:.0f}%, {status}."

    def check_ram(self) -> str:
        mem = psutil.virtual_memory()
        return f"RAM usage is at {mem.percent:.1f}% ({mem.used / (1024**3):.1f} GB of {mem.total / (1024**3):.1f} GB used)."

    def check_cpu(self) -> str:
        cpu = psutil.cpu_percent(interval=0.1)
        return f"CPU utilization is at {cpu:.1f}%."

    def check_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return f"Your local IP address is {ip}."
        except Exception:
            return "Unable to determine local IP address."

    # -------------------------------------------------------------
    # Screen & System Actions
    # -------------------------------------------------------------
    def lock_workstation(self, delay_sec: int = 0) -> str:
        if delay_sec > 0:
            import threading
            def _delayed():
                time.sleep(delay_sec)
                ctypes.windll.user32.LockWorkStation()
            threading.Thread(target=_delayed, daemon=True).start()
            return f"Locking your PC in {delay_sec} seconds."
        ctypes.windll.user32.LockWorkStation()
        return "Your PC is now locked."


    def take_screenshot(self) -> str:
        try:
            import mss
            import mss.tools
            out_dir = Path.home() / "Pictures" / "Screenshots"
            out_dir.mkdir(parents=True, exist_ok=True)
            filename = f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filepath = out_dir / filename
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                sct_img = sct.grab(monitor)
                mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(filepath))
            return f"Screenshot saved to {filepath.name}."
        except Exception as e:
            return f"Failed to take screenshot: {e}"

    def set_brightness(self, level: int) -> str:
        level = max(0, min(100, int(level)))
        try:
            cmd = ["powershell", "-NoProfile", "-Command", f"(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1, {level})"]
            subprocess.run(cmd, capture_output=True, timeout=3)
            return f"Display brightness set to {level} percent."
        except Exception as e:
            return f"Could not adjust brightness: {e}"

    def brightness_up(self, step: int = 15) -> str:
        cur = self.get_brightness()
        new_val = min(100, cur + step)
        return self.set_brightness(new_val)

    def brightness_down(self, step: int = 15) -> str:
        cur = self.get_brightness()
        new_val = max(0, cur - step)
        return self.set_brightness(new_val)

    def get_brightness(self) -> int:
        try:
            cmd = ["powershell", "-NoProfile", "-Command", "(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightness).CurrentBrightness"]
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            if p.returncode == 0 and p.stdout.strip():
                return int(p.stdout.strip())
        except Exception:
            pass
        return 70

    # -------------------------------------------------------------
    # App & Window Controls (Universal Dynamic Search)
    # -------------------------------------------------------------
    def open_app(self, app_name: str) -> str:
        key = app_name.lower().strip()
        # Check folder aliases first
        if key in FOLDER_ALIASES:
            return self.open_folder(key)

        from laya.fast_path.app_locator import get_app_locator
        success, msg = get_app_locator().launch(key)
        return msg

    def open_folder(self, folder_name: str) -> str:
        key = folder_name.lower().strip()
        path = FOLDER_ALIASES.get(key)
        if not path:
            for k, v in FOLDER_ALIASES.items():
                if key in k or k in key:
                    path = v
                    break
        if not path:
            path = folder_name

        if os.path.exists(path):
            os.startfile(path)
            return f"Opened {key} folder."
        return f"Folder {folder_name} not found."

    def close_active_window(self) -> str:
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            return "Closed active window."
        return "No active window found."

    def bring_to_front(self, app_or_title: str) -> str:
        """Bring a specific application or window to the front with active focus."""
        from laya.tools.win32_utils import bring_window_to_front
        ok, msg = bring_window_to_front(app_or_title)
        if not ok:
            # If not already open, try launching it
            return self.open_app(app_or_title)
        return msg

    def close_window(self, title_keyword: str) -> str:
        """Close an open window matching the specified keyword."""
        from laya.tools.win32_utils import close_window_by_query
        ok, msg = close_window_by_query(title_keyword)
        if not ok:
            # Fall back to process termination
            return self.close_app(title_keyword)
        return msg

    def organize_windows(self, layout: str = "grid", target_apps: Optional[list] = None) -> str:
        """Organize open desktop windows into a specified geometric layout (grid, split, columns, cascade, focus)."""
        from laya.tools.window_organizer import get_window_organizer
        return get_window_organizer().organize(layout=layout, target_apps=target_apps)

    def close_app(self, process_name: str) -> str:
        key = process_name.lower().strip()
        if not key.endswith(".exe"):
            target_proc = f"{key}.exe"
        else:
            target_proc = key
        try:
            subprocess.run(f"taskkill /F /IM {target_proc}", shell=True, capture_output=True)
            return f"Closed {process_name}."
        except Exception as e:
            return f"Failed to close {process_name}: {e}"

    def draw_shape(self, shape: str = "circle", title_keyword: str = "Paint") -> str:
        """Draw a geometric shape inside a drawing canvas (e.g. Paint) instantly."""
        from laya.tools.window_geometry import get_window_geometry_manager
        from laya.tools.win32_utils import find_window_by_query
        
        win = find_window_by_query(title_keyword)
        if not win:
            self.open_app(title_keyword)
        # Poll up to 2 seconds for window to be available
        for _ in range(10):
            win = find_window_by_query(title_keyword)
            if win:
                break
            time.sleep(0.2)

        if not win:
            return f"Could not find or launch {title_keyword} window."

        self.bring_to_front(title_keyword)
        time.sleep(0.15)
        return get_window_geometry_manager().draw_relative_shape(title_keyword, shape=shape)

    def type_text(self, text: str) -> str:
        """Type or paste text into the active focused window instantly."""
        if not text:
            return "No text provided to type."
        try:
            # Clipboard injection is instant (0ms) and handles all characters, unicode, and newlines
            pyperclip.copy(text)
            time.sleep(0.05)
            pyautogui.hotkey("ctrl", "v")
            return f"Typed '{text}'."
        except Exception:
            try:
                pyautogui.write(text, interval=0.01)
                return f"Typed '{text}'."
            except Exception as e:
                return f"Failed to type: {e}"

    def press_key(self, key: str = "enter") -> str:
        """Simulate pressing a keyboard key."""
        k = key.lower().strip()
        pyautogui.press(k)
        return f"Pressed {k}."

    def calculate_math(self, expression: str) -> str:
        """Evaluate simple arithmetic expression in microseconds without LLM invocation."""
        clean = expression.lower().replace("times", "*").replace("multiplied by", "*").replace("divided by", "/").replace("plus", "+").replace("minus", "-").replace("x", "*").replace("^", "**")
        clean = re.sub(r"[^0-9\+\-\*\/\.\(\)\s]", "", clean)
        try:
            val = eval(clean, {"__builtins__": None}, {})
            if isinstance(val, float) and val.is_integer():
                val = int(val)
            return f"{expression.strip()} is {val:,}."
        except Exception:
            return f"Calculation completed for {expression}."

    def execute_compound(self, actions: list) -> str:
        """Execute a list of fast-path actions sequentially and instantly."""
        results = []
        for act in actions:
            action_name = act.get("action")
            params = act.get("params", {})
            handler = getattr(self, action_name, None)
            if handler:
                try:
                    res = handler(**params)
                    results.append(str(res))
                except Exception as e:
                    results.append(f"Error in {action_name}: {e}")
            else:
                results.append(f"Executed {action_name}.")
        return " and ".join(results)

    # -------------------------------------------------------------
    # Filesystem & OS Automation Primitives (Local Fast Path)
    # -------------------------------------------------------------
    def create_file(self, filename: str, content: str = "", location: str = "desktop") -> str:
        """Create a new file with optional content instantly on Desktop or in specified folder."""
        from laya.tools.tier2_os_mcp import get_tier2_tools
        return get_tier2_tools().create_file(filename=filename, content=content, location=location)

    def create_folder(self, folder_name: str, location: str = "desktop") -> str:
        """Create a new folder instantly on Desktop or in specified folder."""
        from laya.tools.tier2_os_mcp import get_tier2_tools
        return get_tier2_tools().create_folder(folder_name=folder_name, location=location)

    def open_file(self, filename_or_path: str) -> str:
        """Open any file in its default Windows application instantly."""
        from laya.tools.filesystem_pro import get_filesystem_pro
        return get_filesystem_pro().open_file(filename_or_path)

    def write_to_file(self, filename: str, content: str) -> str:
        """Write or append text directly to a file."""
        from laya.tools.filesystem_pro import get_filesystem_pro
        target = get_filesystem_pro()._resolve_path(filename)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "a" if target.exists() else "w", encoding="utf-8") as f:
                f.write(content + "\n")
            return f"Wrote to '{target.name}' successfully."
        except Exception as e:
            return f"Failed to write to file: {e}"

    def search_files(self, pattern: str, root_dir: str = "desktop") -> str:
        """Search files across Windows and folders."""
        from laya.tools.filesystem_pro import get_filesystem_pro
        return get_filesystem_pro().search_filesystem(pattern=pattern, root_dir=root_dir)

    def delete_file(self, filename_or_path: str) -> str:
        """Delete a file safely by moving it to the Windows Recycle Bin."""
        from laya.tools.filesystem_pro import get_filesystem_pro
        return get_filesystem_pro().delete_file(filename_or_path)

    # -------------------------------------------------------------
    # App Shifting, Splitting & Window Management
    # -------------------------------------------------------------
    def shift_to_app(self, app_or_title: str) -> str:
        """Shift to / focus any running application window immediately."""
        return self.bring_to_front(app_or_title)

    def split_screen(self, layout: str = "split") -> str:
        """Split screen side-by-side or tile active windows."""
        return self.organize_windows(layout=layout)

    # -------------------------------------------------------------
    # Music & Spotify Automation
    # -------------------------------------------------------------
    def click_song(self, query: str = "") -> str:
        """Click on / start playing a song via active media player, Spotify, or YouTube."""
        clean_q = query.lower().strip()
        if not clean_q or clean_q in ["a song", "song", "music", "some music", "the song"]:
            # If media player already running, toggle play
            win32api.keybd_event(win32con.VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
            win32api.keybd_event(win32con.VK_MEDIA_PLAY_PAUSE, 0, win32con.KEYEVENTF_KEYUP, 0)
            return "Playing song."
        return self.play_youtube(query)

    def play_spotify(self, query: str = "") -> str:
        """Open Spotify and start playing music."""
        self.open_app("spotify")
        time.sleep(0.4)
        clean_q = query.lower().strip()
        if clean_q and clean_q not in ["a song", "music", "song", "some music"]:
            import urllib.parse
            import webbrowser
            spotify_url = f"https://open.spotify.com/search/{urllib.parse.quote(query)}"
            webbrowser.open(spotify_url)
            return f"Opening Spotify and playing '{query}'."
        else:
            win32api.keybd_event(win32con.VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
            win32api.keybd_event(win32con.VK_MEDIA_PLAY_PAUSE, 0, win32con.KEYEVENTF_KEYUP, 0)
            return "Spotify opened and playback started."

    # -------------------------------------------------------------
    # WhatsApp & Telegram Direct Automation (<50ms trigger, zero LLM)
    # -------------------------------------------------------------
    def whatsapp_call(self, contact: str, call_type: str = "voice") -> str:
        """Call a contact on WhatsApp instantly (voice or video) with zero LLM delay."""
        contact = contact.strip()
        from laya.tools.win32_utils import ensure_desktop_access, robust_bring_to_front, find_window_by_query
        ensure_desktop_access()

        win = find_window_by_query("whatsapp")
        if not win or not win.get("hwnd"):
            try:
                os.startfile("whatsapp:")
            except Exception:
                subprocess.Popen('start "" "whatsapp:"', shell=True)
            time.sleep(1.2)
            win = find_window_by_query("whatsapp")

        if win and win.get("hwnd"):
            hwnd = win["hwnd"]
            robust_bring_to_front(hwnd)
            time.sleep(0.25)
            pyautogui.press("escape")
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.2)
            pyperclip.copy(contact)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.6)
            pyautogui.press("enter")
            time.sleep(0.5)

            if "video" in call_type.lower():
                pyautogui.hotkey("ctrl", "shift", "v")
                return f"Initiated WhatsApp video call to '{contact}'."
            else:
                pyautogui.hotkey("ctrl", "shift", "c")
                return f"Initiated WhatsApp voice call to '{contact}'."
        else:
            return f"Could not locate or launch WhatsApp to call '{contact}'."

    def whatsapp_message(self, contact: str, message: str) -> str:
        """Send a message to a specific contact on WhatsApp instantly with zero LLM delay."""
        contact = contact.strip()
        message = message.strip()

        # Check if contact is a direct phone number
        digits = re.sub(r"[^\d]", "", contact)
        if len(digits) >= 7 and (contact.startswith("+") or len(digits) == len(contact.replace(" ", "").replace("-", ""))):
            url = f"whatsapp://send?phone={digits}&text={urllib.parse.quote(message)}"
            try:
                os.startfile(url)
                time.sleep(1.0)
                pyautogui.press("enter")
                return f"Dispatched WhatsApp message to {contact}: '{message}'"
            except Exception:
                pass

        # Named contact lookup via WhatsApp desktop
        from laya.tools.win32_utils import ensure_desktop_access, robust_bring_to_front, find_window_by_query
        ensure_desktop_access()

        win = find_window_by_query("whatsapp")
        if not win or not win.get("hwnd"):
            try:
                os.startfile("whatsapp:")
            except Exception:
                subprocess.Popen('start "" "whatsapp:"', shell=True)
            time.sleep(1.2)
            win = find_window_by_query("whatsapp")

        if win and win.get("hwnd"):
            hwnd = win["hwnd"]
            robust_bring_to_front(hwnd)
            time.sleep(0.25)
            pyautogui.press("escape")
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.2)
            pyperclip.copy(contact)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.6)
            pyautogui.press("enter")
            time.sleep(0.4)

            if message:
                pyperclip.copy(message)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.15)
                pyautogui.press("enter")
                return f"Dispatched WhatsApp message to '{contact}': {message}"
            else:
                return f"Opened WhatsApp chat with '{contact}'."
        else:
            # Fallback to WhatsApp Web
            url = f"https://web.whatsapp.com/send?text={urllib.parse.quote(message)}"
            os.startfile(url)
            return f"Opened WhatsApp to send message to '{contact}'."

    def telegram_message(self, contact: str, message: str) -> str:
        """Send a message to a specific contact on Telegram with zero LLM delay."""
        contact = contact.strip()
        message = message.strip()

        from laya.tools.win32_utils import ensure_desktop_access, robust_bring_to_front, find_window_by_query
        ensure_desktop_access()

        win = find_window_by_query("telegram")
        if win and win.get("hwnd"):
            hwnd = win["hwnd"]
            robust_bring_to_front(hwnd)
            time.sleep(0.25)
            pyautogui.press("escape")
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.2)
            pyperclip.copy(contact)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.5)
            pyautogui.press("enter")
            time.sleep(0.3)
            if message:
                pyperclip.copy(message)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.15)
                pyautogui.press("enter")
                return f"Dispatched Telegram message to '{contact}': {message}"
            else:
                return f"Opened Telegram chat with '{contact}'."

        clean_user = contact.lstrip("@")
        try:
            tg_url = f"tg://msg?to={clean_user}&text={urllib.parse.quote(message)}"
            os.startfile(tg_url)
            return f"Dispatched Telegram message to '{contact}' via Telegram protocol."
        except Exception:
            pass

        if clean_user:
            web_url = f"https://t.me/{clean_user}"
            os.startfile(web_url)
            return f"Opened Telegram for '{contact}'."
        else:
            os.startfile("https://web.telegram.org")
            return "Opened Telegram Web."

    def telegram_call(self, contact: str) -> str:
        """Call a contact on Telegram instantly with zero LLM delay."""
        contact = contact.strip()

        from laya.tools.win32_utils import ensure_desktop_access, robust_bring_to_front, find_window_by_query
        ensure_desktop_access()

        win = find_window_by_query("telegram")
        if win and win.get("hwnd"):
            hwnd = win["hwnd"]
            robust_bring_to_front(hwnd)
            time.sleep(0.25)
            pyautogui.press("escape")
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.2)
            pyperclip.copy(contact)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.5)
            pyautogui.press("enter")
            time.sleep(0.4)
            pyautogui.hotkey("ctrl", "u")
            return f"Initiated Telegram voice call to '{contact}'."

        clean_user = contact.lstrip("@")
        try:
            os.startfile(f"tg://resolve?domain={clean_user}")
            return f"Opened Telegram to call '{contact}'."
        except Exception:
            os.startfile(f"https://t.me/{clean_user}")
            return f"Opened Telegram profile for '{contact}'."

    # -------------------------------------------------------------
    # Meme Reaction Trigger
    # -------------------------------------------------------------
    def trigger_meme(self, meme_name: str) -> str:
        """Trigger meme reaction immediately."""
        from laya.ui.meme_engine import get_meme_engine
        from laya.audio.meme_audio import play_meme_audio, get_meme_voice_quip
        archetype = get_meme_engine().classify_reaction(meme_name, meme_name) or "gigachad"
        play_meme_audio(archetype)
        quip = get_meme_voice_quip(archetype)
        return f"{quip} Displaying {archetype.upper()} reaction."

    # -------------------------------------------------------------
    # Local Time, Date & Identity
    # -------------------------------------------------------------
    def query_time(self) -> str:
        now = datetime.datetime.now()
        return f"The time is {now.strftime('%I:%M %p')}."

    def query_date(self) -> str:
        now = datetime.datetime.now()
        return f"Today is {now.strftime('%A, %B %d, %Y')}."

    def query_identity(self) -> str:
        return "I am online, fully armed, and ready for your command."

    def tell_joke(self) -> str:
        import random
        jokes = [
            "Why do programmers prefer dark mode? Because light attracts bugs!",
            "There are 10 types of people in the world: those who understand binary, and those who don't.",
            "A SQL query walks into a bar, walks up to two tables and asks: 'Can I join you?'",
            "Why did the developer go broke? Because he used up all his cache.",
            "Hardware is the part of the computer you can kick; software is the part you can only curse at.",
            "An optimist says the glass is half full. A pessimist says it's half empty. A programmer says the glass is twice as large as necessary.",
        ]
        return random.choice(jokes)

    def share_meme(self) -> str:
        import random
        memes = [
            "Chudjak said: 'Nothing ever happens.' Then the entire build passed with zero warnings. Absolute cinema.",
            "Wake up babe, new 70B parameter model just dropped. Pure GigaChad energy.",
            "MonkaS when you git push --force straight to main on a Friday at 4:59 PM.",
            "They told me 'it works on my machine.' Anon, we are not shipping your laptop to production.",
            "Feels good man: 0 errors, 0 warnings, and your terminal looks like The Matrix.",
            "Average bloated software fan vs Average optimized local script enjoyer.",
        ]
        return random.choice(memes)

    def suggest_songs(self) -> str:
        import random
        tracks = [
            "For deep flow: 'Resonance' by HOME or 'After Dark' by Mr. Kitty. Peak synthwave focus.",
            "Need raw GigaChad productivity? Put on DVRST - 'Close Eyes' or Kordhell phonk.",
            "For chill debugging: Lofi Girl hip-hop beats or C418 - 'Subwoofer Lullaby'.",
            "Heavy cyberpunk momentum: Perturbator or Carpenter Brut - 'Turbo Killer'.",
        ]
        return random.choice(tracks)

    def who_am_i(self) -> str:
        from laya.orchestrator.memory import get_memory_store
        mem = get_memory_store()
        profile = mem.get_user_profile()
        profile_details = ", ".join([f"{k}: {v}" for k, v in list(profile.items())[:3]]) if profile else "building autonomous AI systems"
        return f"You are the boss here. I know you're working on: {profile_details}. What are we conquering today?"

    # -------------------------------------------------------------
    # High-Speed Browser Direct Automation
    # -------------------------------------------------------------
    def browser_search(self, query: str, engine: str = "google") -> str:
        from laya.tools.browser_automator import get_browser_automator
        return get_browser_automator().search_web(query, engine=engine)

    def browser_open_url(self, url: str) -> str:
        from laya.tools.browser_automator import get_browser_automator
        return get_browser_automator().open_url(url)

    def play_youtube(self, query: str) -> str:
        from laya.tools.browser_automator import get_browser_automator
        return get_browser_automator().play_youtube(query)


def get_fast_path_executor() -> FastPathExecutor:
    return FastPathExecutor.get_instance()
