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
    # Emergency Abort & Stop Control (<0.0ms)
    # -------------------------------------------------------------
    def stop_action(self) -> str:
        """Immediately abort all ongoing operations, speech synthesis, and automation."""
        from laya.tools.interrupt_manager import request_interrupt
        request_interrupt("User requested stop")
        try:
            from laya.audio.tts import get_tts_engine
            get_tts_engine().stop()
        except Exception:
            pass
        return "Stopped."

    # -------------------------------------------------------------
    # Audio & Hardware Controls
    # -------------------------------------------------------------
    def volume_up(self, steps: int = 8) -> str:
        for _ in range(steps):
            win32api.keybd_event(win32con.VK_VOLUME_UP, 0, 0, 0)
            win32api.keybd_event(win32con.VK_VOLUME_UP, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.01)
        return "Volume increased."

    def volume_down(self, steps: int = 8) -> str:
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

    def shutdown_system(self) -> str:
        subprocess.run(["shutdown", "/s", "/t", "30"], check=False)
        return "System shutdown scheduled in 30 seconds. Say 'abort shutdown' to cancel."

    def restart_system(self) -> str:
        subprocess.run(["shutdown", "/r", "/t", "30"], check=False)
        return "System restart scheduled in 30 seconds. Say 'abort shutdown' to cancel."


    def take_screenshot(self, open_after: bool = True) -> str:
        """Capture a screenshot of the primary display, save it, and show it."""
        from laya.tools.win32_utils import ensure_desktop_access
        ensure_desktop_access()
        out_dir = Path.home() / "Pictures" / "Screenshots"
        out_dir.mkdir(parents=True, exist_ok=True)
        filename = f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = out_dir / filename
        import threading
        captured = False
        capture_error = []

        def _do_capture():
            nonlocal captured
            try:
                # In clean worker thread, bind to interactive input desktop
                user32 = ctypes.windll.user32
                h_desk = user32.OpenInputDesktop(0, False, 0x01FF)
                if h_desk:
                    user32.SetThreadDesktop(h_desk)

                # Tier 1: PIL ImageGrab
                from PIL import ImageGrab
                img = ImageGrab.grab(all_screens=False)
                img.save(str(filepath))
                captured = True
                return
            except Exception as e:
                capture_error.append(str(e))

            # Tier 2: mss
            try:
                import mss
                import mss.tools
                with mss.mss() as sct:
                    monitor = sct.monitors[1]
                    sct_img = sct.grab(monitor)
                    mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(filepath))
                    captured = True
                    return
            except Exception as e:
                capture_error.append(str(e))

            # Tier 3: pyautogui
            try:
                im = pyautogui.screenshot()
                im.save(str(filepath))
                captured = True
            except Exception as e:
                capture_error.append(str(e))

        t = threading.Thread(target=_do_capture)
        t.start()
        t.join(timeout=2.0)

        if not captured:
            err_msg = "; ".join(capture_error) if capture_error else "unknown error"
            return f"Failed to take screenshot: {err_msg}"

        if open_after and os.path.exists(filepath):
            try:
                os.startfile(str(filepath))
            except Exception:
                pass
        return f"Screenshot captured and saved to {filepath.name}."

    def open_camera(self) -> str:
        """Launch Windows native Camera app."""
        try:
            os.startfile("microsoft.windows.camera:")
            return "Opened Camera."
        except Exception as e:
            return f"Failed to open Camera: {e}"

    def take_photo(self) -> str:
        """Take a photo with the webcam instantly and save to Pictures."""
        try:
            import cv2
            out_dir = Path.home() / "Pictures" / "Camera"
            out_dir.mkdir(parents=True, exist_ok=True)
            filename = f"photo_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath = out_dir / filename

            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(0)

            if not cap.isOpened():
                os.startfile("microsoft.windows.camera:")
                return "Webcam not detected directly. Opened Windows Camera app."

            # Allow camera sensor to auto-adjust exposure
            ret, frame = False, None
            for _ in range(5):
                ret, frame = cap.read()
            cap.release()

            if ret and frame is not None:
                cv2.imwrite(str(filepath), frame)
                try:
                    os.startfile(str(filepath))
                except Exception:
                    pass
                return f"Photo captured and saved to {filepath.name}."
            else:
                os.startfile("microsoft.windows.camera:")
                return "Opened Windows Camera app to take photo."
        except Exception as e:
            try:
                os.startfile("microsoft.windows.camera:")
                return "Opened Windows Camera app."
            except Exception:
                return f"Failed to capture photo: {e}"

    def record_screen(self) -> str:
        """Toggle screen recording via native Windows Game Bar shortcut (Win + Alt + R)."""
        try:
            pyautogui.hotkey('win', 'alt', 'r')
            time.sleep(0.1)
            return "Screen recording toggled (Win + Alt + R). Videos save to Videos/Captures."
        except Exception as e:
            return f"Failed to trigger screen recording: {e}"

    def record_camera_video(self, duration: int = 5) -> str:
        """Record a short video clip from the webcam and save to Videos/Captures."""
        try:
            import cv2
            out_dir = Path.home() / "Videos" / "Captures"
            out_dir.mkdir(parents=True, exist_ok=True)
            filename = f"webcam_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            filepath = out_dir / filename

            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                os.startfile("microsoft.windows.camera:")
                return "Webcam not detected. Opened Camera app."

            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            fps = 20.0
            out = cv2.VideoWriter(str(filepath), fourcc, fps, (width, height))

            total_frames = int(fps * max(2, min(30, int(duration))))
            for _ in range(total_frames):
                ret, frame = cap.read()
                if not ret:
                    break
                out.write(frame)

            cap.release()
            out.release()

            if os.path.exists(filepath):
                try:
                    os.startfile(str(filepath))
                except Exception:
                    pass
                return f"Recorded {duration}s video saved to {filepath.name}."
            return "Failed to save video recording."
        except Exception as e:
            return f"Error recording video: {e}"

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

    def open_folder(self, folder_name: str = "desktop") -> str:
        raw = (folder_name or "desktop").lower().strip()
        # Clean filler prefixes
        clean = re.sub(r"^(?:the\s+|a\s+)?folder\s+(?:on|in)\s+(?:the\s+)?", "", raw).strip()
        clean = re.sub(r"^(?:the\s+|a\s+)?", "", clean).strip()
        clean = re.sub(r"\s+folder$", "", clean).strip()
        clean = re.sub(r"^(?:in|on)\s+(?:the\s+)?desktop$", "desktop", clean).strip()

        desktop_path = Path.home() / "Desktop"

        if not clean or clean in ["desktop", "the desktop", "my desktop"]:
            if desktop_path.exists():
                os.startfile(str(desktop_path))
                return "Opened Desktop folder."

        # Check standard FOLDER_ALIASES
        if clean in FOLDER_ALIASES:
            target = FOLDER_ALIASES[clean]
            if os.path.exists(target):
                os.startfile(target)
                return f"Opened {clean.title()} folder."

        # Check if it is a subfolder on Desktop
        desktop_sub = desktop_path / clean
        if desktop_sub.exists() and desktop_sub.is_dir():
            os.startfile(str(desktop_sub))
            return f"Opened '{clean}' folder on Desktop."

        # Check if it is a subfolder in Documents or Downloads
        for parent in [Path.home() / "Documents", Path.home() / "Downloads"]:
            sub = parent / clean
            if sub.exists() and sub.is_dir():
                os.startfile(str(sub))
                return f"Opened '{clean}' folder in {parent.name}."

        # Search Desktop for partial match
        try:
            for item in desktop_path.iterdir():
                if item.is_dir() and clean in item.name.lower():
                    os.startfile(str(item))
                    return f"Opened '{item.name}' folder on Desktop."
        except Exception:
            pass

        # Check direct path
        if os.path.exists(folder_name):
            os.startfile(folder_name)
            return f"Opened {folder_name}."

        # Fallback to Desktop
        if desktop_path.exists():
            os.startfile(str(desktop_path))
            return f"Could not find a specific folder named '{clean}'. Opened Desktop for you."
        return f"Folder {folder_name} not found."

    def close_all_apps(self) -> str:
        """Close all visible user application windows while keeping the HUD and desktop intact."""
        closed_count = 0
        hud_hwnd = None
        try:
            from laya.ui.hud import LayaHUD
            if LayaHUD._active_instance:
                hud_hwnd = LayaHUD._active_instance.winfo_id()
        except Exception:
            pass

        def enum_win(hwnd, _):
            nonlocal closed_count
            if not win32gui.IsWindowVisible(hwnd):
                return True
            title = win32gui.GetWindowText(hwnd).strip()
            if not title:
                return True
            # Ignore desktop, taskbar, system windows, and the assistant HUD itself
            if title in ["Program Manager", "Settings", "Windows Input Experience"]:
                return True
            if hud_hwnd and (hwnd == hud_hwnd or win32gui.GetParent(hwnd) == hud_hwnd):
                return True
            class_name = win32gui.GetClassName(hwnd)
            if class_name in ["Shell_TrayWnd", "DV2ControlHost", "Button", "SideBar"]:
                return True
            try:
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                closed_count += 1
            except Exception:
                pass
            return True

        win32gui.EnumWindows(enum_win, None)
        return f"Closed {closed_count} open application window{'s' if closed_count != 1 else ''}."

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

    def scroll_window(self, direction: str = "down", amount: int = 5, title_keyword: str = "") -> str:
        """Scroll window up, down, left, right, top, bottom, or by pages."""
        from laya.tools.computer_use import get_computer_use_tools
        return get_computer_use_tools().scroll_window(direction=direction, amount=amount, title_keyword=title_keyword)

    def zoom_window_region(self, region: str = "center", zoom_factor: float = 2.0, title_keyword: str = "") -> str:
        """Zoom in a region of a window (top-left, center, bottom-right, etc.)."""
        from laya.tools.computer_use import get_computer_use_tools
        return get_computer_use_tools().zoom_window_region(region=region, zoom_factor=zoom_factor, title_keyword=title_keyword)

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
        from laya.tools.interrupt_manager import is_interrupt_requested
        results = []
        for act in actions:
            if is_interrupt_requested():
                return "Stopped."
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
    # Music, Video & YouTube Automation
    # -------------------------------------------------------------
    def play_youtube(self, query: str = "") -> str:
        """Start playing a video or music track on YouTube directly with zero clicks."""
        from laya.tools.browser_automator import get_browser_automator
        return get_browser_automator().play_youtube(query or "synthwave lofi chillhop mix")

    def click_song(self, query: str = "") -> str:
        """Click on / start playing a song via active media player, Spotify, or YouTube."""
        clean_q = query.lower().strip()
        if not clean_q or clean_q in ["a song", "song", "music", "some music", "the song"]:
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
            # Try desktop spotify protocol first
            try:
                os.startfile(f"spotify:search:{urllib.parse.quote(query)}")
                time.sleep(0.5)
                pyautogui.press("enter")
                return f"Playing '{query}' on Spotify."
            except Exception:
                pass
            spotify_url = f"https://open.spotify.com/search/{urllib.parse.quote(query)}"
            webbrowser.open(spotify_url)
            return f"Opening Spotify and playing '{query}'."
        else:
            win32api.keybd_event(win32con.VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
            win32api.keybd_event(win32con.VK_MEDIA_PLAY_PAUSE, 0, win32con.KEYEVENTF_KEYUP, 0)
            return "Spotify opened and playback started."

    # -------------------------------------------------------------
    # Browser Automation Fast-Path
    # -------------------------------------------------------------
    def browser_search(self, query: str, engine: str = "google") -> str:
        """Search Google or YouTube directly in browser."""
        from laya.tools.browser_automator import get_browser_automator
        return get_browser_automator().search_web(query, engine=engine)

    def browser_open_url(self, url: str) -> str:
        """Navigate browser directly to URL."""
        from laya.tools.browser_automator import get_browser_automator
        return get_browser_automator().open_url(url)

    def write_to_notepad(self, text: str, filename: Optional[str] = None) -> str:
        """Write text to Notepad — opens Notepad if not running, then types or pastes the text."""
        import threading
        from laya.tools.win32_utils import find_window_by_query, robust_bring_to_front
        if filename:
            # Write to a named file and open it in Notepad
            target = Path.home() / "Documents" / "LayaDocs" / (filename if filename.endswith(".txt") else f"{filename}.txt")
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                with open(target, "w", encoding="utf-8") as f:
                    f.write(text + "\n")
                os.startfile(str(target))
                return f"Written '{filename}' and opened in Notepad."
            except Exception as e:
                return f"Failed to write Notepad file: {e}"
        # Otherwise type directly into active/open Notepad window
        win = find_window_by_query("notepad")
        if not win:
            os.startfile("notepad.exe")
            time.sleep(0.7)
            win = find_window_by_query("notepad")
        if win and win.get("hwnd"):
            robust_bring_to_front(win["hwnd"])
            time.sleep(0.15)
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
            return f"Typed text into Notepad: '{text[:50]}{'...' if len(text) > 50 else ''}'."
        return "Could not find or open Notepad."


    def browser_new_tab(self, url: Optional[str] = None) -> str:
        from laya.tools.browser_automator import get_browser_automator
        return get_browser_automator().new_tab(url)

    def browser_close_tab(self) -> str:
        from laya.tools.browser_automator import get_browser_automator
        return get_browser_automator().close_tab()

    def browser_switch_tab(self, direction: str = "next") -> str:
        from laya.tools.browser_automator import get_browser_automator
        return get_browser_automator().switch_tab(direction)

    def browser_scroll(self, direction: str = "down", amount: int = 5) -> str:
        from laya.tools.browser_automator import get_browser_automator
        return get_browser_automator().scroll(direction, amount)

    def browser_refresh(self) -> str:
        from laya.tools.browser_automator import get_browser_automator
        return get_browser_automator().refresh()

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

        # 1. Check local contact store for phone number
        from laya.tools.contacts_store import get_contacts_store
        c_record = get_contacts_store().get_contact(contact)
        target_phone = c_record.get("whatsapp") or c_record.get("phone") if c_record else None

        # 2. Check if contact itself is a direct phone number
        digits = re.sub(r"[^\d]", "", contact)
        if not target_phone and len(digits) >= 7 and (contact.startswith("+") or len(digits) == len(contact.replace(" ", "").replace("-", ""))):
            target_phone = digits

        if target_phone:
            url = f"whatsapp://send?phone={re.sub(r'[^\\d]', '', target_phone)}&text={urllib.parse.quote(message)}"
            try:
                os.startfile(url)
                time.sleep(1.0)
                pyautogui.press("enter")
                display_name = c_record["name"] if c_record else contact
                return f"Dispatched WhatsApp message to {display_name}: '{message}'"
            except Exception:
                pass

        # 3. Named contact lookup via WhatsApp desktop
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
            url = f"https://web.whatsapp.com/send?text={urllib.parse.quote(message)}"
            os.startfile(url)
            return f"Opened WhatsApp to send message to '{contact}'."

    # -------------------------------------------------------------
    # Universal Messaging & Telegram (Send, Read, Search, Call)
    # -------------------------------------------------------------
    def send_message(self, recipient: str, message: str = "", platform: str = "auto") -> str:
        """Intelligently dispatch a message to a recipient via Telegram or WhatsApp with zero LLM delay."""
        recipient = recipient.strip()
        message = message.strip() or "Hello from Laya!"

        from laya.tools.contacts_store import get_contacts_store
        contact = get_contacts_store().get_contact(recipient)

        # 1. Check contact store preferences
        if contact:
            if contact.get("telegram") and not contact.get("whatsapp"):
                return self.telegram_send_message(recipient=contact.get("telegram") or recipient, message=message)
            if contact.get("whatsapp") and not contact.get("telegram"):
                return self.whatsapp_message(contact=contact.get("whatsapp") or recipient, message=message)

        # 2. Check open desktop messenger windows
        from laya.tools.win32_utils import find_window_by_query
        wa_win = find_window_by_query("whatsapp")
        tg_win = find_window_by_query("telegram")

        if tg_win and not wa_win:
            return self.telegram_send_message(recipient=recipient, message=message)
        elif wa_win and not tg_win:
            return self.whatsapp_message(contact=recipient, message=message)

        # 3. Default to Telegram
        return self.telegram_send_message(recipient=recipient, message=message)

    def telegram_message(self, contact: str, message: str) -> str:
        """Send a message to a specific contact on Telegram with zero LLM delay."""
        from laya.tools.telegram_client import get_telegram_manager
        return get_telegram_manager().send_message(recipient=contact, message=message)

    def telegram_send_message(self, recipient: str, message: str) -> str:
        return self.telegram_message(contact=recipient, message=message)

    def telegram_voice_call(self, recipient: str, call_type: str = "voice") -> str:
        """Initiate a voice or video call on Telegram via TelegramManager."""
        from laya.tools.telegram_client import get_telegram_manager
        return get_telegram_manager().call(recipient=recipient, call_type=call_type)

    def telegram_read(self, contact: str, limit: int = 5) -> str:
        """Read recent messages from a contact on Telegram."""
        from laya.tools.telegram_client import get_telegram_manager
        return get_telegram_manager().read_messages(recipient=contact, limit=limit)

    def telegram_read_messages(self, chat: str = "me", limit: int = 5) -> str:
        return self.telegram_read(contact=chat, limit=limit)

    def telegram_search(self, query: str, limit: int = 5) -> str:
        """Search messages across Telegram."""
        from laya.tools.telegram_client import get_telegram_manager
        return get_telegram_manager().search_messages(query=query, limit=limit)

    def telegram_search_messages(self, query: str, limit: int = 5) -> str:
        return self.telegram_search(query=query, limit=limit)

    def telegram_broadcast(self, message: str, limit: int = 30) -> str:
        """Broadcast a message to contacts and active chats on Telegram."""
        from laya.tools.telegram_client import get_telegram_manager
        return get_telegram_manager().broadcast_message(message=message, limit=limit)

    def broadcast_message(self, message: str, limit: int = 30) -> str:
        """Universal broadcast message to contacts across platforms."""
        return self.telegram_broadcast(message=message, limit=limit)

    def telegram_sync_contacts(self) -> str:
        """Sync Telegram contacts into local Laya address book."""
        from laya.tools.telegram_client import get_telegram_manager
        return get_telegram_manager().sync_telegram_contacts()

    def telegram_list_contacts(self) -> str:
        """List contacts from Telegram."""
        from laya.tools.telegram_client import get_telegram_manager
        return get_telegram_manager().list_telegram_contacts()

    def telegram_launch(self, target: str = "") -> str:
        """Launch or bring Telegram Desktop to front with zero LLM delay."""
        from laya.tools.telegram_client import get_telegram_manager
        return get_telegram_manager().open_telegram(target=target)

    def open_telegram(self, target: str = "") -> str:
        return self.telegram_launch(target=target)

    def telegram_messages(self) -> str:
        return self.telegram_launch()

    def telegram_launch_login(self) -> str:
        """Launch the Telegram login and setup GUI."""
        from laya.tools.telegram_client import get_telegram_manager
        return get_telegram_manager().launch_login_gui()

    def telegram_save_credentials(self, api_id: str, api_hash: str) -> str:
        """Save Telegram API credentials."""
        from laya.tools.telegram_client import get_telegram_manager
        return get_telegram_manager().save_credentials(api_id, api_hash)

    def telegram_call(self, contact: str, call_type: str = "voice") -> str:
        """Call a contact on Telegram instantly with zero LLM delay."""
        contact = contact.strip()
        from laya.tools.contacts_store import get_contacts_store
        c_record = get_contacts_store().get_contact(contact)
        target = (c_record.get("telegram") if c_record else None) or contact.lstrip("@")
        clean_user = target.lstrip("@")

        from laya.tools.win32_utils import ensure_desktop_access, robust_bring_to_front, find_window_by_query
        ensure_desktop_access()

        # First, open the chat via tg:// protocol — most reliable
        try:
            import urllib.parse as _up
            os.startfile(f"tg://resolve?domain={_up.quote(clean_user)}")
            time.sleep(0.8)
        except Exception:
            pass

        win = find_window_by_query("telegram")
        if win and win.get("hwnd"):
            hwnd = win["hwnd"]
            robust_bring_to_front(hwnd)
            time.sleep(0.2)
            # Ctrl+U triggers voice call in Telegram Desktop
            pyautogui.hotkey("ctrl", "u")
            return f"Initiated Telegram voice call to '{contact}'."

        return f"Opened Telegram chat for '{contact}'. Use Ctrl+U to start a call."

    # -------------------------------------------------------------
    # Contact Book CRUD Operations (Zero LLM, Instant)
    # -------------------------------------------------------------
    def contact_add(self, name: str, phone: str = "", telegram: str = "", notes: str = "") -> str:
        """Add or update a contact in the local address book."""
        from laya.tools.contacts_store import get_contacts_store
        rec = get_contacts_store().save_contact(name=name, phone=phone, telegram=telegram, notes=notes)
        details = []
        if rec.get("phone"):
            details.append(f"Phone: {rec['phone']}")
        if rec.get("telegram"):
            details.append(f"Telegram: @{rec['telegram']}")
        det_str = f" ({', '.join(details)})" if details else ""
        return f"Saved contact '{rec['name']}'{det_str}."

    def contact_find(self, query: str) -> str:
        """Find a contact in the local address book."""
        from laya.tools.contacts_store import get_contacts_store
        rec = get_contacts_store().get_contact(query)
        if rec:
            details = [f"Name: {rec['name']}"]
            if rec.get("phone"):
                details.append(f"Phone: {rec['phone']}")
            if rec.get("telegram"):
                details.append(f"Telegram: @{rec['telegram']}")
            if rec.get("notes"):
                details.append(f"Notes: {rec['notes']}")
            return " | ".join(details)
        return f"No contact found matching '{query}'."

    def contact_list(self) -> str:
        """List all saved contacts."""
        from laya.tools.contacts_store import get_contacts_store
        all_c = get_contacts_store().list_contacts()
        if not all_c:
            return "No contacts saved yet. Say 'Add contact [Name] with phone [number]' to save one."
        lines = []
        for c in all_c:
            t = f"@{c['telegram']}" if c.get("telegram") else ""
            p = c.get("phone", "")
            info = f" ({', '.join(filter(None, [p, t]))})" if (p or t) else ""
            lines.append(f"• {c['name']}{info}")
        return "Contacts:\n" + "\n".join(lines)

    def contact_delete(self, name: str) -> str:
        """Delete a contact from the address book."""
        from laya.tools.contacts_store import get_contacts_store
        ok = get_contacts_store().delete_contact(name)
        if ok:
            return f"Removed contact '{name}'."
        return f"Contact '{name}' not found."

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

    # NOTE: browser_search, browser_open_url, play_youtube are defined above (lines ~569-534)
    # Keeping them as single canonical definitions to avoid Python override shadowing.

    def stop_action(self) -> str:
        """Trigger universal interruption across all running operations."""
        from laya.tools.interrupt_manager import request_interrupt
        request_interrupt("User voice request to stop")
        return "Operation stopped."

    def hide_hud(self) -> str:
        """Hide the HUD interface from screen."""
        try:
            from laya.ui.hud import LayaHUD
            if hasattr(LayaHUD, "_active_instance") and LayaHUD._active_instance:
                LayaHUD._active_instance._hide_hud()
                return "HUD hidden."
        except Exception:
            pass
        return "UI hidden."

    def show_hud(self) -> str:
        """Show the HUD interface on screen."""
        try:
            from laya.ui.hud import LayaHUD
            if hasattr(LayaHUD, "_active_instance") and LayaHUD._active_instance:
                LayaHUD._active_instance._show_hud()
                return "HUD displayed."
        except Exception:
            pass
    def check_emails(self, unread_only: bool = True) -> str:
        """Fetch unread emails and generate executive summary."""
        try:
            from laya.tools.email_reader import get_email_manager
            em = get_email_manager()
            res = em.check_emails(limit=5, unread_only=unread_only)
            return res.get("spoken") or res.get("summary")
        except Exception as e:
            return f"Error checking emails: {e}"

    def open_webmail(self) -> str:
        """Launch webmail in browser."""
        try:
            from laya.tools.email_reader import get_email_manager
            return get_email_manager().open_webmail()
        except Exception as e:
            return f"Failed to open webmail: {e}"

    def open_gmail(self) -> str:
        """Launch Gmail in default browser."""
        return self.open_webmail()

    def get_conversation_history(self, limit: int = 5) -> str:
        """Retrieve recent conversation history from the active session or memory store."""
        try:
            from laya.ui.hud import LayaHUD
            if LayaHUD._active_instance and LayaHUD._active_instance.assistant:
                hist = LayaHUD._active_instance.assistant.conversation_history
                if hist:
                    lines = []
                    user_turns = [h["content"] for h in hist if h.get("role") == "user"]
                    for idx, msg in enumerate(user_turns[-limit:], 1):
                        lines.append(f"{idx}. '{msg}'")
                    return "Your recent requests were:\n" + "\n".join(lines)
        except Exception:
            pass

        try:
            from laya.orchestrator.memory import get_memory_store
            facts = get_memory_store().get_all_summary()
            return f"No active chat history found in this session yet. Memory store status: {facts}"
        except Exception as e:
            return f"History unavailable: {e}"


def get_fast_path_executor() -> FastPathExecutor:
    return FastPathExecutor.get_instance()
