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

    def launch(self, name_or_query: str) -> Tuple[bool, str]:
        """Launch any game, tool, or app on the PC."""
        result = self.find_app(name_or_query)
        if not result:
            # Fall back to starting via Windows shell directly
            try:
                os.startfile(name_or_query)
                return True, f"Launched '{name_or_query}' directly."
            except Exception:
                try:
                    subprocess.Popen(name_or_query, shell=True)
                    return True, f"Started '{name_or_query}'."
                except Exception as ex:
                    return False, f"Could not find or launch application or game '{name_or_query}': {ex}"

        display_name, target = result
        try:
            if target.endswith((".lnk", ".url")):
                os.startfile(target)
            else:
                # Launch via Windows shell AppsFolder (works for ANY app/game registered in Windows)
                cmd = f'explorer.exe "shell:AppsFolder\\{target}"'
                subprocess.Popen(cmd, shell=True)
            return True, f"Opening {display_name.title()}."
        except Exception as e:
            return False, f"Failed launching {display_name}: {e}"


def get_app_locator() -> AppLocator:
    return AppLocator.get_instance()
