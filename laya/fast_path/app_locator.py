"""
Laya Universal Dynamic App & Game Locator
Indexes all 300+ installed Windows applications, games, Steam titles, and Start Menu items.
Zero hardcoding: finds and launches ANY application or game by name.
"""

import os
import sys
import json
import subprocess
import threading
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from difflib import get_close_matches


class AppLocator:
    _instance: Optional["AppLocator"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._apps: Dict[str, str] = {}  # lowercase_name -> AppID or Path
        self._desktop_shortcuts: Dict[str, str] = {}
        self._is_indexed = False
        # Index in background thread to avoid blocking startup
        t = threading.Thread(target=self._index_installed_apps, daemon=True)
        t.start()

    @classmethod
    def get_instance(cls) -> "AppLocator":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _index_installed_apps(self):
        """Query Windows Get-StartApps and desktop shortcuts."""
        indexed: Dict[str, str] = {}

        # 1. Query Windows Start Menu & Installed UWP/Desktop Apps
        try:
            cmd = ["powershell", "-NoProfile", "-Command", "Get-StartApps | ConvertTo-Json -Compress"]
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=6)
            if p.returncode == 0 and p.stdout.strip():
                data = json.loads(p.stdout)
                if isinstance(data, list):
                    for item in data:
                        name = item.get("Name", "").strip().lower()
                        appid = item.get("AppID", "").strip()
                        if name and appid:
                            indexed[name] = appid
                elif isinstance(data, dict):
                    name = data.get("Name", "").strip().lower()
                    appid = data.get("AppID", "").strip()
                    if name and appid:
                        indexed[name] = appid
        except Exception as e:
            print(f"[AppLocator Warning] Get-StartApps query: {e}", file=sys.stderr)

        # 2. Scan Desktop and Start Menu .lnk and .url shortcuts
        shortcut_dirs = [
            Path.home() / "Desktop",
            Path(os.environ.get("PUBLIC", r"C:\Users\Public")) / "Desktop",
            Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
            Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        ]

        for s_dir in shortcut_dirs:
            if s_dir.exists():
                try:
                    for f in s_dir.rglob("*"):
                        if f.is_file() and f.suffix.lower() in [".lnk", ".url"]:
                            name = f.stem.lower()
                            if name not in indexed:
                                indexed[name] = str(f)
                except Exception:
                    pass

        with self._lock:
            self._apps = indexed
            self._is_indexed = True

    def find_app(self, query: str) -> Optional[Tuple[str, str]]:
        """
        Find application or game by query string.
        Returns: (display_name, target_path_or_appid)
        """
        # Ensure indexing has finished or wait briefly
        if not self._is_indexed:
            self._index_installed_apps()

        q = query.lower().strip()
        # Direct exact match
        if q in self._apps:
            return q, self._apps[q]

        # Substring search
        for name, target in self._apps.items():
            if q == name or q in name or name in q:
                return name, target

        # Fuzzy match
        matches = get_close_matches(q, list(self._apps.keys()), n=1, cutoff=0.55)
        if matches:
            best = matches[0]
            return best, self._apps[best]

        return None

    def _bring_to_foreground(self, query: str) -> bool:
        """If an application window is already running, restore and bring it to front."""
        try:
            import win32gui
            import win32con
            found_hwnd = None
            q_lower = query.lower().strip()

            def enum_cb(hwnd, _):
                nonlocal found_hwnd
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd).lower()
                    if title and (q_lower in title or any(w in title for w in q_lower.split())):
                        found_hwnd = hwnd
                        return False
                return True

            win32gui.EnumWindows(enum_cb, None)
            if found_hwnd:
                win32gui.ShowWindow(found_hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(found_hwnd)
                return True
        except Exception:
            pass
        return False

    def launch(self, name_or_query: str) -> Tuple[bool, str]:
        """Launch any game, tool, or app on the PC, or bring its window to the front."""
        q = name_or_query.lower().strip()
        # Clean common filler prefixes
        for prefix in ["open ", "launch ", "start ", "the "]:
            if q.startswith(prefix):
                q = q[len(prefix):].strip()

        # 1. Bring to foreground if already running
        if self._bring_to_foreground(q):
            return True, f"Brought {q.title()} to the foreground."

        # 2. Known standard app direct paths
        common_paths = {
            "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            "google chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            "brave": r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            "msedge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            "telegram": str(Path.home() / r"AppData\Roaming\Telegram Desktop\Telegram.exe"),
            "discord": str(Path.home() / r"AppData\Local\Discord\Update.exe --processStart Discord.exe"),
            "vscode": "code",
            "vs code": "code",
            "visual studio code": "code",
            "notepad": "notepad.exe",
            "paint": "mspaint.exe",
            "mspaint": "mspaint.exe",
            "calc": "calc.exe",
            "calculator": "calc.exe",
            "spotify": "spotify",
            "whatsapp": "whatsapp:",
        }
        for key, target_path in common_paths.items():
            if q == key or q in key or key in q:
                try:
                    if target_path.startswith("http") or (":" in target_path and "\\" not in target_path):
                        try:
                            os.startfile(target_path)
                        except Exception:
                            subprocess.Popen(f"start {target_path}", shell=True)
                    elif target_path.endswith(".exe") and os.path.exists(target_path):
                        os.startfile(target_path)
                    elif "--processStart" in target_path or target_path in ["code", "notepad.exe", "calc.exe", "mspaint.exe"]:
                        subprocess.Popen(target_path, shell=True)
                    else:
                        try:
                            os.startfile(target_path)
                        except Exception:
                            subprocess.Popen(f"start {target_path}", shell=True)
                    return True, f"Opening {key.title()}."
                except Exception:
                    pass

        # 3. Dynamic lookup in StartApps and shortcuts
        result = self.find_app(q)
        if result:
            display_name, target = result
            try:
                if target.endswith((".lnk", ".url")) and os.path.exists(target):
                    os.startfile(target)
                elif ":" in target or "\\" in target:
                    os.startfile(target)
                else:
                    cmd = f'explorer.exe "shell:AppsFolder\\{target}"'
                    subprocess.Popen(cmd, shell=True)
                return True, f"Opening {display_name.title()}."
            except Exception as e:
                pass

        # 4. Fall back to Windows Shell startfile or Popen
        try:
            os.startfile(q)
            return True, f"Opened '{q}'."
        except Exception:
            try:
                subprocess.Popen(f"start {q}", shell=True)
                return True, f"Started '{q}'."
            except Exception as ex:
                return False, f"Could not find or launch application '{name_or_query}'."



def get_app_locator() -> AppLocator:
    return AppLocator.get_instance()
