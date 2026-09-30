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
import threading
from pathlib import Path
from typing import Dict, Any, Optional

import re
import pyautogui
import pyperclip
import psutil
import win32api
import win32gui
import win32con

from laya.config import APP_REGISTRY, FOLDER_ALIASES, DOCS_DIR, REAL_DESKTOP_DIR


class FastPathExecutor:
    _instance: Optional["FastPathExecutor"] = None

    def __init__(self):
        self.last_created_folder: Optional[str] = None
        self._screen_recorder_thread: Optional[threading.Thread] = None
        self._screen_recorder_stop = threading.Event()
        self._screen_recorder_file: Optional[Path] = None
        self._camera_recorder_thread: Optional[threading.Thread] = None
        self._camera_recorder_stop = threading.Event()
        self._camera_recorder_file: Optional[Path] = None
        self._battery_warned = False
        self._start_battery_sentinel()

    @classmethod
    def get_instance(cls) -> "FastPathExecutor":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_reminder(self, message: str, minutes: float = 0, hours: float = 0, seconds: float = 0) -> str:
        """Schedule a timed reminder instantly via MemoryStore."""
        from laya.orchestrator.memory import get_memory_store
        return get_memory_store().add_reminder(
            message=message,
            minutes=float(minutes),
            hours=float(hours),
            seconds=float(seconds)
        )

    def list_reminders(self) -> str:
        """List all pending reminders instantly."""
        from laya.orchestrator.memory import get_memory_store
        return get_memory_store().list_reminders()

    def cancel_reminders(self, query: str = "") -> str:
        """Cancel pending reminders or timers."""
        from laya.orchestrator.memory import get_memory_store
        return get_memory_store().cancel_reminders(query=query)

    # -------------------------------------------------------------
    # Emergency Abort & Stop Control (<0.0ms)
    # -------------------------------------------------------------
    def stop_action(self) -> str:
        """Immediately abort all ongoing operations, speech synthesis, and automation."""
        from laya.tools.interrupt_manager import request_interrupt
        request_interrupt("User requested stop")
        if self._screen_recorder_thread and self._screen_recorder_thread.is_alive():
            try:
                self.stop_screen_recording()
            except Exception:
                pass
        try:
            from laya.audio.tts import get_tts_engine
            get_tts_engine().stop()
        except Exception:
            pass
        return "Stopped."

    def open_folder(self, folder_name: str = "desktop") -> str:
        raw = (folder_name or "desktop").lower().strip()
        # Clean filler prefixes
        clean = re.sub(r"^(?:the\s+|a\s+)?folder\s+(?:on|in)\s+(?:the\s+)?", "", raw).strip()
        clean = re.sub(r"^(?:the\s+|a\s+)?", "", clean).strip()
        clean = re.sub(r"\s+folder$", "", clean).strip()
        clean = re.sub(r"^(?:in|on)\s+(?:the\s+)?(?:desktop|bureau)$", "desktop", clean).strip()

        desktop_path = REAL_DESKTOP_DIR

        # Check pronoun / recent folder resolution: "open it", "open them", "open that folder"
        if clean in ["it", "them", "that", "this", "the folder", "that folder", "this folder", "recent", "created", "the created folder", "recent folder"]:
            candidate = self.last_created_folder
            if not candidate:
                try:
                    from laya.tools.tier2_os_mcp import get_tier2_tools
                    candidate = get_tier2_tools().last_created_dir
                except Exception:
                    pass
            if candidate and Path(candidate).exists():
                os.startfile(str(candidate))
                return f"Opened folder '{Path(candidate).name}'."

        if not clean or clean in ["desktop", "the desktop", "my desktop", "bureau", "le bureau", "mon bureau"]:
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

    def sleep_system(self) -> str:
        """Put computer into sleep/suspend state immediately."""
        try:
            # powrprof.dll SetSuspendState(bHibernate=False, bForce=True, bWakeupEventsDisabled=False)
            res = ctypes.windll.powrprof.SetSuspendState(0, 1, 0)
            if res:
                return "Putting computer to sleep."
        except Exception:
            pass
        try:
            subprocess.run("rundll32.exe powrprof.dll,SetSuspendState 0,1,0", shell=True)
            return "Putting computer to sleep."
        except Exception as e:
            return f"Failed to put computer to sleep: {e}"

    def shutdown_system(self) -> str:
        subprocess.run(["shutdown", "/s", "/t", "30"], check=False)
        return "System shutdown scheduled in 30 seconds. Say 'abort shutdown' to cancel."

    def restart_system(self) -> str:
        subprocess.run(["shutdown", "/r", "/t", "30"], check=False)
        return "System restart scheduled in 30 seconds. Say 'abort shutdown' to cancel."

    def turn_screen_off(self) -> str:
        """Turn off the physical display/monitor immediately using Windows PostMessage."""
        try:
            # SC_MONITORPOWER = 0xF170, 2 = monitor off, -1 = HWND_BROADCAST
            win32gui.PostMessage(win32con.HWND_BROADCAST, win32con.WM_SYSCOMMAND, 0xF170, 2)
            return "Turned off the screen."
        except Exception as e:
            # Fallback via powershell command
            try:
                subprocess.Popen(
                    ["powershell", "-Command", "(Add-Type '[DllImport(\"user32.dll\")]public static extern int SendMessage(int hWnd, int hMsg, int wParam, int lParam);' -Name a -PassThru)::SendMessage(-1, 0x0112, 0xF170, 2)"],
                    creationflags=0x08000000
                )
                return "Turned off the screen."
            except Exception:
                return f"Failed to turn off screen: {e}"

    def turn_screen_on(self) -> str:
        """Wake up the display by simulating mouse movement."""
        try:
            win32gui.PostMessage(win32con.HWND_BROADCAST, win32con.WM_SYSCOMMAND, 0xF170, -1)
            pyautogui.moveRel(1, 0)
            pyautogui.moveRel(-1, 0)
            return "Turned on the screen."
        except Exception as e:
            return f"Failed to turn on screen: {e}"


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

    def record_screen(self, duration: int = 0) -> str:
        """Toggle or record screen. If duration > 0, records for that many seconds. If currently recording, stops it."""
        if self._screen_recorder_thread and self._screen_recorder_thread.is_alive():
            return self.stop_screen_recording()
        return self.start_screen_recording(duration=duration)

    def start_screen_recording(self, duration: int = 0) -> str:
        """Start capturing screen video to Videos/Captures using native mss + OpenCV."""
        if self._screen_recorder_thread and self._screen_recorder_thread.is_alive():
            return "Screen recording is already in progress. Say 'stop recording' to finish."

        out_dir = Path.home() / "Videos" / "Captures"
        out_dir.mkdir(parents=True, exist_ok=True)
        filename = f"screen_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        filepath = out_dir / filename
        self._screen_recorder_file = filepath
        self._screen_recorder_stop.clear()

        def _record_worker():
            try:
                import mss
                import cv2
                import numpy as np
                with mss.mss() as sct:
                    monitor = sct.monitors[1]
                    width = monitor["width"]
                    height = monitor["height"]
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    fps = 15.0
                    out = cv2.VideoWriter(str(filepath), fourcc, fps, (width, height))
                    start_time = time.time()
                    frame_delay = 1.0 / fps

                    while not self._screen_recorder_stop.is_set():
                        t0 = time.time()
                        img = np.array(sct.grab(monitor))
                        frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                        out.write(frame)

                        if duration > 0 and (time.time() - start_time) >= duration:
                            break

                        elapsed = time.time() - t0
                        if elapsed < frame_delay:
                            time.sleep(frame_delay - elapsed)

                    out.release()
            except Exception as e:
                # Fallback to Xbox Game Bar hotkey
                try:
                    pyautogui.hotkey('win', 'alt', 'r')
                except Exception:
                    pass

        self._screen_recorder_thread = threading.Thread(target=_record_worker, daemon=True, name="ScreenRecorderThread")
        self._screen_recorder_thread.start()

        if duration > 0:
            return f"Recording screen for {duration} seconds to Videos/Captures/{filename}."
        return f"Screen recording started. Video is saving to Videos/Captures/{filename}. Say 'stop recording' when done."

    def stop_screen_recording(self) -> str:
        """Stop active screen recording."""
        if not (self._screen_recorder_thread and self._screen_recorder_thread.is_alive()):
            # Also send win+alt+r in case Xbox Game Bar was running
            try:
                pyautogui.hotkey('win', 'alt', 'r')
            except Exception:
                pass
            return "No active screen recording was running (or toggled Windows Game Bar)."

        self._screen_recorder_stop.set()
        self._screen_recorder_thread.join(timeout=3.0)
        saved_file = self._screen_recorder_file
        if saved_file and saved_file.exists():
            return f"Screen recording stopped. Saved to {saved_file.name} in Videos/Captures."
        return "Screen recording stopped."

    def record_camera_video(self, duration: int = 0) -> str:
        """Toggle or record camera video asynchronously without blocking. If duration > 0, records for that many seconds. If currently recording, stops it."""
        if self._camera_recorder_thread and self._camera_recorder_thread.is_alive():
            return self.stop_camera_recording()
        return self.start_camera_recording(duration=duration)

    def start_camera_recording(self, duration: int = 0) -> str:
        """Start capturing webcam video in the background without blocking the assistant."""
        if self._camera_recorder_thread and self._camera_recorder_thread.is_alive():
            return "Camera recording is already in progress. Say 'stop camera recording' when finished."

        out_dir = Path.home() / "Videos" / "Captures"
        out_dir.mkdir(parents=True, exist_ok=True)
        filename = f"webcam_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        filepath = out_dir / filename
        self._camera_recorder_file = filepath
        self._camera_recorder_stop.clear()

        def _cam_worker():
            try:
                import cv2
                cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    print("[Camera Recorder] Unable to open webcam.", file=sys.stderr)
                    return

                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                fps = 20.0
                out = cv2.VideoWriter(str(filepath), fourcc, fps, (width, height))
                start_time = time.time()
                frame_delay = 1.0 / fps

                while not self._camera_recorder_stop.is_set():
                    t0 = time.time()
                    ret, frame = cap.read()
                    if not ret:
                        break
                    out.write(frame)

                    if duration > 0 and (time.time() - start_time) >= duration:
                        break

                    elapsed = time.time() - t0
                    if elapsed < frame_delay:
                        time.sleep(frame_delay - elapsed)

                cap.release()
                out.release()
            except Exception as e:
                print(f"[Camera Recorder Error] {e}", file=sys.stderr)

        self._camera_recorder_thread = threading.Thread(target=_cam_worker, daemon=True, name="CameraRecorderThread")
        self._camera_recorder_thread.start()

        if duration > 0:
            return f"Recording camera for {duration} seconds to Videos/Captures/{filename}."
        return f"Camera recording started. Saving to Videos/Captures/{filename}. Say 'stop camera recording' when finished."

    def stop_camera_recording(self) -> str:
        """Stop active camera recording."""
        if not (self._camera_recorder_thread and self._camera_recorder_thread.is_alive()):
            return "No active camera recording was in progress."

        self._camera_recorder_stop.set()
        self._camera_recorder_thread.join(timeout=3.0)
        saved = self._camera_recorder_file
        if saved and saved.exists():
            return f"Camera recording stopped. Saved to {saved.name} in Videos/Captures."
        return "Camera recording stopped."

    def stop_all_recordings(self) -> str:
        """Stop any active screen or camera recordings."""
        stopped = []
        if self._screen_recorder_thread and self._screen_recorder_thread.is_alive():
            stopped.append(self.stop_screen_recording())
        if self._camera_recorder_thread and self._camera_recorder_thread.is_alive():
            stopped.append(self.stop_camera_recording())
        if stopped:
            return " ".join(stopped)
        return "No active recordings were running."

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
        last_target_folder = None
        for act in actions:
            if is_interrupt_requested():
                return "Stopped."
            action_name = act.get("action")
            params = dict(act.get("params", {}))

            # Propagate target folder from create_folder to subsequent open_folder
            if action_name == "open_folder":
                fol = params.get("folder_name", "")
                if fol in ["it", "them", "that", "the folder", ""] and last_target_folder:
                    params["folder_name"] = last_target_folder

            handler = getattr(self, action_name, None)
            if handler:
                try:
                    res = handler(**params)
                    results.append(str(res))
                    if action_name in ["create_folder", "create_and_open_folder"]:
                        last_target_folder = params.get("folder_name")
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

    def create_and_open_folder(self, folder_name: str = "New Folder", location: str = "desktop") -> str:
        """Create a new folder instantly on Desktop, Bureau, or specified directory and reveal it in Windows Explorer."""
        raw_name = (folder_name or "New Folder").strip()
        clean_name = re.sub(r"\s+(?:and\s+)?open\s+(?:it|them|that|the\s+folder).*", "", raw_name, flags=re.I).strip()
        if not clean_name or clean_name.lower() in ["folder", "a folder", "new"]:
            clean_name = "New Folder"

        res = self.create_folder(folder_name=clean_name, location=location)
        if self.last_created_folder and Path(self.last_created_folder).exists():
            os.startfile(self.last_created_folder)
            loc_label = "Bureau" if location.lower() in ["bureau", "le bureau", "mon bureau"] else location.title()
            return f"Created folder '{Path(self.last_created_folder).name}' in {loc_label} and opened it in File Explorer."
        return res

    def create_folder(self, folder_name: str, location: str = "desktop") -> str:
        """Create a new folder instantly on Desktop, Bureau, or in specified folder."""
        raw_name = (folder_name or "New Folder").strip()
        should_open = bool(re.search(r"\s+(?:and\s+)?open\s+(?:it|them|that|the\s+folder)", raw_name, re.I))
        clean_name = re.sub(r"\s+(?:and\s+)?open\s+(?:it|them|that|the\s+folder).*", "", raw_name, flags=re.I).strip()
        if not clean_name or clean_name.lower() in ["folder", "a folder", "new"]:
            clean_name = "New Folder"

        base = REAL_DESKTOP_DIR
        loc_clean = (location or "desktop").lower().strip()
        if loc_clean not in ["desktop", "the desktop", "bureau", "le bureau", "mon bureau", ""]:
            if loc_clean in FOLDER_ALIASES:
                base = Path(FOLDER_ALIASES[loc_clean])
            elif Path(location).exists():
                base = Path(location)

        target = base / clean_name
        target.mkdir(parents=True, exist_ok=True)
        self.last_created_folder = str(target.resolve())

        try:
            from laya.tools.tier2_os_mcp import get_tier2_tools
            get_tier2_tools().last_created_dir = str(target.resolve())
        except Exception:
            pass

        loc_label = "Bureau" if loc_clean in ["bureau", "le bureau", "mon bureau"] else base.name
        if should_open:
            os.startfile(str(target.resolve()))
            return f"Created folder '{clean_name}' in {loc_label} and opened it in File Explorer."

        return f"Created folder '{clean_name}' at '{target.resolve()}'."

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

    def telegram_call(self, contact: str = "", recipient: str = "", call_type: str = "voice") -> str:
        """Call a contact on Telegram instantly with zero LLM delay."""
        target_name = (contact or recipient or "").strip()
        from laya.tools.contacts_store import get_contacts_store
        c_record = get_contacts_store().get_contact(target_name)
        target = (c_record.get("telegram") if c_record else None) or target_name.lstrip("@")
        clean_user = target.lstrip("@")

        from laya.tools.win32_utils import ensure_desktop_access, robust_bring_to_front, find_window_by_query
        ensure_desktop_access()

        # Open the chat via tg:// deep-link — most reliable way to reach a specific user
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
            pyautogui.hotkey("ctrl", "u")  # Ctrl+U triggers voice call in Telegram Desktop
            return f"Initiated Telegram voice call to '{target_name}'."

        # Fallback: let TelegramManager try
        try:
            from laya.tools.telegram_client import TelegramManager
            return TelegramManager.get_instance().start_call(recipient=target, call_type=call_type)
        except Exception:
            pass
        return f"Opened Telegram for '{target_name}'. Use Ctrl+U to start a call."

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
    # Instant Messaging (Telegram & WhatsApp Fast Path)
    # -------------------------------------------------------------
    def telegram_send_message(self, recipient: str = "", contact: str = "", message: str = "") -> str:
        """Send message to a contact or active conversation on Telegram."""
        return self.telegram_message(recipient=recipient or contact, message=message)

    def telegram_message(self, recipient: str = "", contact: str = "", message: str = "") -> str:
        """Send message to a contact or active conversation on Telegram."""
        from laya.tools.telegram_client import TelegramManager
        target = recipient or contact or ""
        return TelegramManager.get_instance().send_message(recipient=target, message=message)

    def send_telegram(self, recipient: str = "", contact: str = "", message: str = "") -> str:
        return self.telegram_message(recipient=recipient, contact=contact, message=message)


    def whatsapp_message(self, contact: str = "", recipient: str = "", message: str = "") -> str:
        """Send a message to a contact, phone number, or the active/latest conversation on WhatsApp."""
        import urllib.parse
        target_name = (contact or recipient or "").strip()
        msg_body = (message or "").strip()

        is_latest = target_name.lower() in [
            "latest", "recent", "current", "latest conversation", "last conversation",
            "current chat", "last chat", "this chat", "the latest conversation",
            "active chat", "active conversation", "the active chat", ""
        ]

        from laya.tools.win32_utils import ensure_desktop_access, find_window_by_query, robust_bring_to_front
        from laya.tools.contacts_store import get_contacts_store
        import win32gui

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
            return self._dispatch_whatsapp(win_query=find_window_by_query("whatsapp"), is_latest=is_latest, target_name=target_name, msg_body=msg_body)
        finally:
            if hud_lowered:
                try:
                    LayaHUD._active_instance.attributes("-topmost", True)
                except Exception:
                    pass

    def _dispatch_whatsapp(self, win_query, is_latest: bool, target_name: str, msg_body: str) -> str:
        from laya.tools.win32_utils import robust_bring_to_front, find_window_by_query
        from laya.tools.contacts_store import get_contacts_store
        import win32gui

        win = win_query
        if not win or not win.get("hwnd"):
            try:
                os.startfile("whatsapp://")
                time.sleep(1.5)
                win = find_window_by_query("whatsapp")
            except Exception:
                pass

        if is_latest:
            if win and win.get("hwnd"):
                hwnd = win["hwnd"]
                robust_bring_to_front(hwnd)
                time.sleep(0.3)
                pyautogui.press("escape")
                time.sleep(0.1)
                try:
                    rect = win32gui.GetWindowRect(hwnd)
                except Exception:
                    rect = None
                if rect:
                    # In WhatsApp, click first chat in list if needed to ensure conversation is open
                    first_chat_x = rect[0] + 220
                    first_chat_y = rect[1] + 240
                    pyautogui.click(first_chat_x, first_chat_y)
                    time.sleep(0.3)
                    input_x = rect[0] + int((rect[2] - rect[0]) * 0.65)
                    input_y = rect[3] - 45
                    pyautogui.click(input_x, input_y)
                    time.sleep(0.1)
                if msg_body:
                    pyperclip.copy(msg_body)
                    pyautogui.hotkey("ctrl", "v")
                    time.sleep(0.2)
                    pyautogui.press("enter")
                    return f"Dispatched WhatsApp message to active conversation: '{msg_body}'"
                return "Focused active WhatsApp conversation."
            else:
                return "WhatsApp is not currently running. Please open WhatsApp first."

        # Contact specified:
        contact_data = get_contacts_store().get_contact(target_name)
        phone = ""
        if contact_data:
            phone = contact_data.get("whatsapp") or contact_data.get("phone") or ""
        elif re.match(r"^\+?[0-9\s\-()]{7,20}$", target_name):
            phone = re.sub(r"[^\d+]", "", target_name)

        if phone:
            clean_phone = re.sub(r"[^\d]", "", phone)
            enc_msg = urllib.parse.quote(msg_body)
            uri = f"whatsapp://send?phone={clean_phone}&text={enc_msg}"
            try:
                os.startfile(uri)
                time.sleep(1.2)
                pyautogui.press("enter")
                return f"Sent WhatsApp message to {target_name} ({phone}): '{msg_body}'"
            except Exception as e:
                print(f"[WhatsApp] Protocol send note: {e}")

        # Fallback to UI search:
        if win and win.get("hwnd"):
            hwnd = win["hwnd"]
            robust_bring_to_front(hwnd)
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.2)
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.05)
            pyperclip.copy(target_name)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.6)
            pyautogui.press("down")
            time.sleep(0.15)
            pyautogui.press("enter")
            time.sleep(0.4)
            try:
                rect = win32gui.GetWindowRect(hwnd)
            except Exception:
                rect = None
            if rect:
                input_x = rect[0] + int((rect[2] - rect[0]) * 0.65)
                input_y = rect[3] - 45
                pyautogui.click(input_x, input_y)
                time.sleep(0.1)
            if msg_body:
                pyperclip.copy(msg_body)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.2)
                pyautogui.press("enter")
                return f"Sent WhatsApp message to {target_name}: '{msg_body}'"
            return f"Opened WhatsApp chat with {target_name}."

        return f"Could not find or open WhatsApp chat for {target_name}."

    def send_whatsapp(self, contact: str = "", recipient: str = "", message: str = "") -> str:
        return self.whatsapp_message(contact=contact, recipient=recipient, message=message)

    # -------------------------------------------------------------
    # 3 Extreme Meme Modes (Foid Alert, Chud Destruct, Lockdown)
    # -------------------------------------------------------------
    def foid_alert_mode(self) -> str:
        """Trigger emergency siren alert and red lighting for foid detection."""
        from laya.audio.meme_audio import play_meme_audio
        play_meme_audio("foid_alert")
        try:
            from laya.ui.hud import LayaHUD
            if hasattr(LayaHUD, "_active_instance") and LayaHUD._active_instance:
                LayaHUD._active_instance.msg_queue.put(("extreme_mode", "foid_alert"))
        except Exception:
            pass
        return "🚨 FOID ALERT: Foid detected nearby! Foid, foid, go away, strike my cortisol another day!"

    def chud_self_destruct(self) -> str:
        """Trigger chud take detection, display chudjak image, and initiate self-destruction."""
        from laya.audio.meme_audio import play_meme_audio
        play_meme_audio("chud_destruct")
        try:
            from laya.ui.hud import LayaHUD
            if hasattr(LayaHUD, "_active_instance") and LayaHUD._active_instance:
                LayaHUD._active_instance.msg_queue.put(("extreme_mode", "chud_destruct"))
        except Exception:
            pass
        return "💥 CHUD TAKE DETECTED: Oh, something happened! Chud take detected! Initiating self destruction sequence in 10, 9, 8, 7, 6, 5, 4, 3, 2, 1... Core meltdown complete. Goodbye."

    def extreme_lockdown_mode(self) -> str:
        """Trigger extreme lockdown mode with cyber strobe and alert."""
        from laya.audio.meme_audio import play_meme_audio
        play_meme_audio("lockdown")
        try:
            from laya.ui.hud import LayaHUD
            if hasattr(LayaHUD, "_active_instance") and LayaHUD._active_instance:
                LayaHUD._active_instance.msg_queue.put(("extreme_mode", "lockdown"))
        except Exception:
            pass
        return "⚡ EXTREME LOCKDOWN: Extreme lockdown mode activated. Cortisol levels critical. Locking in."

    # -------------------------------------------------------------
    # Meme Reaction Trigger
    # -------------------------------------------------------------
    def trigger_meme(self, meme_name: str) -> str:
        """Trigger meme reaction immediately."""
        from laya.ui.meme_engine import get_meme_engine
        from laya.audio.meme_audio import play_meme_audio, get_meme_voice_quip
        archetype = get_meme_engine().classify_reaction(meme_name, meme_name) or "chudjak"
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
            "Alert! Foid detected nearby! Foid, foid, go away, strike my cortisol another day!",
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
            "Need extreme lockdown productivity? Put on DVRST - 'Close Eyes' or Kordhell phonk.",
            "For chill debugging: Lofi Girl hip-hop beats or C418 - 'Subwoofer Lullaby'.",
            "Heavy cyberpunk momentum: Perturbator or Carpenter Brut - 'Turbo Killer'.",
        ]
        return random.choice(tracks)

    # -------------------------------------------------------------
    # User Profile & Durable Memory Fast Paths
    # -------------------------------------------------------------
    def save_user_fact(self, fact: str) -> str:
        """Store a durable fact learned from user experience into SQLite."""
        from laya.orchestrator.memory import get_memory_store
        clean_fact = fact.strip()
        if not clean_fact:
            return "What would you like me to remember?"
        return get_memory_store().add_fact(clean_fact)

    def update_user_profile(self, key: str, value: str) -> str:
        """Update a specific user profile field (name, role, location, etc.)."""
        from laya.orchestrator.memory import get_memory_store
        k = key.strip().lower()
        v = value.strip()
        res = get_memory_store().set_profile(k, v)
        # Also store as fact for semantic recall
        get_memory_store().add_fact(f"User's {k} is {v}")
        return f"Got it. I've updated your {k} to '{v}' in memory."

    def who_am_i(self) -> str:
        """Recall everything learned about the user across sessions."""
        from laya.orchestrator.memory import get_memory_store
        mem = get_memory_store()
        profile = mem.get_user_profile()
        facts_summary = mem.get_all_summary()

        name = profile.get("name") or profile.get("username")
        role = profile.get("role") or profile.get("profession") or profile.get("job")

        intro = []
        if name:
            intro.append(f"you are {name}")
        if role:
            intro.append(f"working as a {role}")
        for k, v in profile.items():
            if k not in ["name", "username", "role", "profession", "job"]:
                intro.append(f"{k}: {v}")

        if intro:
            details_str = ", ".join(intro)
            return f"From our history: {details_str}. {facts_summary}"
        return f"You are the boss here. I have our memory database online. Tell me your name, role, or what to remember anytime!"

    # -------------------------------------------------------------
    # Proactive Intelligence: Daily Briefing & Battery Sentinel
    # -------------------------------------------------------------
    def _start_battery_sentinel(self):
        """Proactive battery sentinel monitoring for low battery alerts."""
        def _sentinel_worker():
            while True:
                try:
                    batt = psutil.sensors_battery()
                    if batt:
                        if batt.power_plugged:
                            self._battery_warned = False
                        elif batt.percent <= 15 and not self._battery_warned:
                            self._battery_warned = True
                            from laya.orchestrator.memory import get_memory_store
                            name = get_memory_store().get_profile("name", "sir")
                            warn_msg = f"Warning {name}: Laptop battery is at {int(batt.percent)}% and discharging. Please connect power."
                            from laya.audio.tts import get_tts_engine
                            get_tts_engine().speak(warn_msg)
                except Exception:
                    pass
                time.sleep(60)

        t = threading.Thread(target=_sentinel_worker, daemon=True, name="BatterySentinelThread")
        t.start()

    def get_daily_briefing(self) -> str:
        """Charismatic, JARVIS-style executive daily briefing."""
        from laya.orchestrator.memory import get_memory_store
        mem = get_memory_store()
        profile = mem.get_user_profile()
        name = profile.get("name", "Khalil")

        # Time of day greeting
        hour = datetime.datetime.now().hour
        greeting = "Good morning" if 5 <= hour < 12 else ("Good afternoon" if 12 <= hour < 18 else "Good evening")

        # Battery status
        batt_str = ""
        try:
            batt = psutil.sensors_battery()
            if batt:
                plugged = "charging" if batt.power_plugged else "on battery"
                batt_str = f"Battery is at {int(batt.percent)}% ({plugged})."
        except Exception:
            pass

        # Pending reminders
        pending_str = ""
        try:
            import sqlite3
            conn = sqlite3.connect(str(mem.db_path))
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM reminders WHERE fired=0")
            count = cur.fetchone()[0]
            conn.close()
            if count > 0:
                pending_str = f"You have {count} pending reminder{'s' if count != 1 else ''} scheduled."
            else:
                pending_str = "No pending reminders."
        except Exception:
            pass

        # Active workspace windows
        active_apps_str = ""
        try:
            from laya.orchestrator.react_agent import get_active_desktop_environment
            env = get_active_desktop_environment()
            for line in env.split("\n"):
                if "Visible Windows:" in line:
                    active_apps_str = f"Current active windows: {line.replace('Visible Windows:', '').strip()}."
        except Exception:
            pass

        parts = [f"{greeting} {name}.", "All systems are operational."]
        if batt_str:
            parts.append(batt_str)
        if pending_str:
            parts.append(pending_str)
        if active_apps_str:
            parts.append(active_apps_str)
        parts.append("Standing by for your command.")

        return " ".join(parts)

    # -------------------------------------------------------------
    # Screen Eyes: On-Demand Zero-GPU Visual Inspection
    # -------------------------------------------------------------
    def inspect_screen(self, query: str = "") -> str:
        """On-demand screen visual inspector. Uses UIA and focused window analysis with zero background overhead."""
        # 1. Inspect active foreground window controls
        fg_info = ""
        title = "Desktop"
        try:
            from laya.tools.ufo_controller import get_ufo_controller
            fg_info = get_ufo_controller().inspect_window_controls(max_depth=2)
        except Exception:
            pass

        try:
            hwnd = win32gui.GetForegroundWindow()
            t = win32gui.GetWindowText(hwnd).strip()
            if t:
                title = t
        except Exception:
            pass

        prompt_query = query.strip() or "Describe what is on my screen or diagnose any visible error."
        try:
            from laya.orchestrator.react_agent import run_single_prompt
            prompt = (
                f"User Question: '{prompt_query}'.\n"
                f"Foreground Application: '{title}'.\n"
                f"Visible UI Controls & Content Hierarchy:\n{fg_info[:1600]}\n\n"
                f"Give a razor-sharp, helpful, and witty 1-2 sentence spoken explanation of what is on screen or diagnosing the error, in JARVIS style."
            )
            res = run_single_prompt(prompt)
            if res and len(res.strip()) > 5:
                return res.strip()
        except Exception:
            pass

        return f"You are currently viewing '{title}'. Active window elements: {fg_info[:180]}."

    # NOTE: browser_search, browser_open_url, play_youtube are defined above (lines ~569-534)
    # Keeping them as single canonical definitions to avoid Python override shadowing.

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
        return "UI displayed."

    def toggle_hud_mode(self, mode: str = "") -> str:
        """Toggle HUD between compact floating island pill and full interface."""
        try:
            from laya.ui.hud import LayaHUD
            hud = getattr(LayaHUD, "_active_instance", None)
            if not hud:
                return "HUD interface is not running."

            target = (mode or "").lower().strip()
            if target in ["compact", "mini", "pill", "island"]:
                if not hud.is_collapsed:
                    hud.after(0, hud._toggle_collapse_animated)
                return "Switched HUD to compact floating island mode."
            elif target in ["full", "expand", "max", "maximize"]:
                if hud.is_collapsed:
                    hud.after(0, hud._toggle_collapse_animated)
                return "Expanded HUD to full interface mode."
            else:
                hud.after(0, hud._toggle_collapse_animated)
                state = "compact floating island" if not hud.is_collapsed else "full HUD"
                return f"Toggled HUD to {state}."
        except Exception as e:
            return f"Failed to switch HUD mode: {e}"

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
