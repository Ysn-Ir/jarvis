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
        return "Why do programmers prefer dark mode? Because light attracts bugs!"

    # -------------------------------------------------------------
    # High-Speed Browser Direct Automation
    # -------------------------------------------------------------
    def browser_search(self, query: str, engine: str = "google") -> str:
        from laya.tools.browser_automator import get_browser_automator
        return get_browser_automator().search_web(query, engine=engine)

    def browser_open_url(self, url: str) -> str:
        from laya.tools.browser_automator import get_browser_automator
        return get_browser_automator().open_url(url)


def get_fast_path_executor() -> FastPathExecutor:
    return FastPathExecutor.get_instance()
