"""
Laya Window Geometry & Relative Mouse Navigation
Inspects window geometry (position, width, height, client bounds) and performs
relative coordinate navigation and drawing with zero pixel guesswork across different resolutions.
"""

import time
import win32gui
import win32con
import win32api
import pyautogui
from typing import Optional, Dict, Any, Tuple, List

from laya.tools.win32_utils import robust_bring_to_front, find_window_by_query

pyautogui.FAILSAFE = False


class WindowGeometryManager:
    _instance: Optional["WindowGeometryManager"] = None

    @classmethod
    def get_instance(cls) -> "WindowGeometryManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_window_geometry(self, title_keyword: str) -> Dict[str, Any]:
        """
        Return the exact position, dimensions, and center of a target window.
        """
        win = find_window_by_query(title_keyword)
        if not win or not win.get("hwnd"):
            return {"error": f"No visible window found matching '{title_keyword}'"}

        hwnd = win["hwnd"]
        full_title = win["title"]

        rect = win32gui.GetWindowRect(hwnd)
        left, top, right, bottom = rect
        width = max(1, right - left)
        height = max(1, bottom - top)

        return {
            "hwnd": hwnd,
            "title": full_title,
            "left": left,
            "top": top,
            "right": right,
            "bottom": bottom,
            "width": width,
            "height": height,
            "center_x": left + width // 2,
            "center_y": top + height // 2,
        }

    def click_window_relative(
        self,
        title_keyword: str,
        rel_x: float,
        rel_y: float,
        button: str = "left",
        clicks: int = 1,
    ) -> str:
        """
        Bring the target window to front and click at relative coordinates (0.0 to 1.0).
        Example: rel_x=0.5, rel_y=0.5 clicks the exact center of the window.
        """
        geo = self.get_window_geometry(title_keyword)
        if "error" in geo:
            return geo["error"]

        hwnd = geo["hwnd"]
        robust_bring_to_front(hwnd)
        time.sleep(0.15)

        # Refresh geometry after bring to front in case it was restored from minimized
        rect = win32gui.GetWindowRect(hwnd)
        left, top, right, bottom = rect
        width = max(1, right - left)
        height = max(1, bottom - top)

        # Clamp relative percentages
        rx = max(0.01, min(0.99, rel_x))
        ry = max(0.01, min(0.99, rel_y))

        abs_x = left + int(width * rx)
        abs_y = top + int(height * ry)

        pyautogui.moveTo(abs_x, abs_y, duration=0.15)
        pyautogui.click(abs_x, abs_y, clicks=clicks, button=button)
        return f"Clicked relative position ({rx:.2f}, {ry:.2f}) -> screen ({abs_x}, {abs_y}) on '{geo['title']}'."

    def mouse_move_relative(self, title_keyword: str, rel_x: float, rel_y: float) -> str:
        """Move the mouse to a position relative to the target window."""
        geo = self.get_window_geometry(title_keyword)
        if "error" in geo:
            return geo["error"]

        hwnd = geo["hwnd"]
        robust_bring_to_front(hwnd)
        time.sleep(0.1)

        rect = win32gui.GetWindowRect(hwnd)
        left, top, right, bottom = rect
        width = max(1, right - left)
        height = max(1, bottom - top)

        abs_x = left + int(width * rel_x)
        abs_y = top + int(height * rel_y)

        pyautogui.moveTo(abs_x, abs_y, duration=0.2)
        return f"Moved mouse to ({abs_x}, {abs_y}) relative to '{geo['title']}'."


def get_window_geometry_manager() -> WindowGeometryManager:
    return WindowGeometryManager.get_instance()
