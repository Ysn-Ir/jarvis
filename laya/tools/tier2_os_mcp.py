"""
Laya Tier 2 OS Automation & MCP-Compatible Tools
Standardized tools for window management, UI Automation (UIA) tree inspection,
and file system CRUD operations with intelligent location resolution.
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

import win32gui
import win32con
import uiautomation as uia

from laya.config import DOCS_DIR, FOLDER_ALIASES


class Tier2OSAutomationTools:
    _instance: Optional["Tier2OSAutomationTools"] = None

    def __init__(self):
        self.last_created_dir: str = str(Path.home() / "Desktop")
        self.last_created_file: str = ""

    @classmethod
    def get_instance(cls) -> "Tier2OSAutomationTools":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------
    # 1. Window Management
    # -------------------------------------------------------------
    def list_windows(self) -> List[Dict[str, Any]]:
        """List all visible top-level windows with their handles and titles."""
        windows = []

        def enum_handler(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    windows.append({
                        "hwnd": hwnd,
                        "title": title,
                        "class": win32gui.GetClassName(hwnd),
                    })
            return True

        try:
            win32gui.EnumWindows(enum_handler, None)
        except Exception:
            pass

        if not windows:
            import psutil
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    name = proc.info['name']
                    if name and not name.lower().startswith(("svchost", "system", "conhost")):
                        windows.append({
                            "hwnd": proc.info['pid'],
                            "title": name,
                            "class": "Process",
                        })
                except Exception:
                    pass

        return windows

    def focus_window(self, title_query: str) -> str:
        q = title_query.lower()
        windows = self.list_windows()
        for win in windows:
            if q in win["title"].lower():
                hwnd = win["hwnd"]
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                return f"Brought window '{win['title']}' to foreground."
        return f"No visible window matching '{title_query}' found."

    def close_window(self, title_query: str) -> str:
        q = title_query.lower()
        windows = self.list_windows()
        for win in windows:
            if q in win["title"].lower():
                hwnd = win["hwnd"]
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                return f"Closed window '{win['title']}'."
        return f"Window matching '{title_query}' not found."

    # -------------------------------------------------------------
    # 2. UI Automation (UIA) Tree Inspection & Clicking
    # -------------------------------------------------------------
    def query_uia_tree(self, max_depth: int = 3) -> str:
        try:
            fg_control = uia.GetForegroundControl()
            if not fg_control:
                return "No foreground window control found."

            lines = [f"Root: {fg_control.Name} ({fg_control.ControlTypeName})"]

            def walk(control, depth):
                if depth > max_depth:
                    return
                for child in control.GetChildren():
                    name = child.Name.strip() if child.Name else ""
                    c_type = child.ControlTypeName
                    if name:
                        lines.append(f"{'  '*depth}├── [{c_type}] '{name}' (ID: {child.AutomationId})")
                    walk(child, depth + 1)

            walk(fg_control, 1)
            return "\n".join(lines[:35])
        except Exception as e:
            return f"UIA tree inspection failed: {e}"

    def click_element_by_name(self, name: str) -> str:
        try:
            fg_control = uia.GetForegroundControl()
            if not fg_control:
                return "No active window found."

            target = fg_control.Control(searchDepth=5, Name=name)
            if target.Exists(maxSearchSeconds=1.0):
                rect = target.BoundingRectangle
                cx = (rect.left + rect.right) // 2
                cy = (rect.top + rect.bottom) // 2
                target.Click(simulateMove=False)
                return f"Clicked element '{name}' at ({cx}, {cy})."
            return f"Could not find accessible element with name '{name}'."
        except Exception as e:
            return f"Error clicking element '{name}': {e}"

    # -------------------------------------------------------------
    # 3. File System CRUD with Intelligent Location Resolution
    # -------------------------------------------------------------
    def _resolve_base_dir(self, location_hint: Optional[str] = None) -> Path:
        """Resolve location hint ('desktop', 'downloads', 'documents', custom path) to real directory."""
        if not location_hint or location_hint.strip() in ["", "here", "current", "this"]:
            if self.last_created_dir and Path(self.last_created_dir).exists():
                return Path(self.last_created_dir)
            return Path.home() / "Desktop"

        loc = location_hint.strip()
        loc_lower = loc.lower().replace("\\", "/")
        
        # Check sub-paths under desktop/documents/downloads
        if loc_lower.startswith("desktop/"):
            sub = loc[len("desktop/"):]
            return (Path.home() / "Desktop" / sub)
        elif loc_lower == "desktop":
            return Path.home() / "Desktop"

        if loc_lower.startswith("downloads/"):
            sub = loc[len("downloads/"):]
            return (Path.home() / "Downloads" / sub)
        elif "download" in loc_lower:
            return Path.home() / "Downloads"

        if loc_lower.startswith("documents/") or loc_lower.startswith("docs/"):
            prefix = "documents/" if loc_lower.startswith("documents/") else "docs/"
            sub = loc[len(prefix):]
            return (DOCS_DIR / sub)
        elif "document" in loc_lower or "docs" in loc_lower:
            return DOCS_DIR

        # Check if it's an existing folder name on desktop or in last_created_dir
        check_desktop = Path.home() / "Desktop" / loc
        if check_desktop.exists():
            return check_desktop

        check_last = Path(self.last_created_dir) / loc
        if check_last.exists():
            return check_last

        check_direct = Path(loc)
        if check_direct.exists():
            return check_direct

        return Path.home() / "Desktop"


    def create_folder(self, folder_name: str, location: Optional[str] = None) -> str:
        base = self._resolve_base_dir(location)
        target = base / folder_name
        target.mkdir(parents=True, exist_ok=True)
        self.last_created_dir = str(target.resolve())
        return f"Created folder '{folder_name}' at '{target.resolve()}'."

    def create_file(self, filename: str, content: str = "", location: Optional[str] = None) -> str:
        base = self._resolve_base_dir(location)
        target = base / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        self.last_created_file = str(target.resolve())
        return f"Created file '{filename}' at '{target.resolve()}'."

    def get_file_info(self, query: str = "") -> str:
        """Return the location and details of the last created or referenced file/folder."""
        if self.last_created_file and Path(self.last_created_file).exists():
            p = Path(self.last_created_file)
            return f"The file '{p.name}' is located at: {p.resolve()} (Size: {p.stat().st_size} bytes)."
        if self.last_created_dir and Path(self.last_created_dir).exists():
            p = Path(self.last_created_dir)
            return f"The current active folder is at: {p.resolve()}."
        return "No recently created file found in session."

    def list_files(self, directory: Optional[str] = None) -> List[str]:
        target = self._resolve_base_dir(directory)
        if not target.exists():
            return []
        return [f.name for f in target.iterdir() if f.is_file()]


def get_tier2_tools() -> Tier2OSAutomationTools:
    return Tier2OSAutomationTools.get_instance()
