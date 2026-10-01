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

    def drag_window_relative(
        self,
        title_keyword: str,
        start_rel_x: float,
        start_rel_y: float,
        end_rel_x: float,
        end_rel_y: float,
        duration: float = 0.4,
        button: str = "left",
    ) -> str:
        """
        Drag the mouse smoothly from a relative start position to a relative end position in a window.
        """
        geo = self.get_window_geometry(title_keyword)
        if "error" in geo:
            return geo["error"]

        hwnd = geo["hwnd"]
        robust_bring_to_front(hwnd)
        time.sleep(0.15)

        rect = win32gui.GetWindowRect(hwnd)
        left, top, right, bottom = rect
        width = max(1, right - left)
        height = max(1, bottom - top)

        sx = left + int(width * max(0.01, min(0.99, start_rel_x)))
        sy = top + int(height * max(0.01, min(0.99, start_rel_y)))
        ex = left + int(width * max(0.01, min(0.99, end_rel_x)))
        ey = top + int(height * max(0.01, min(0.99, end_rel_y)))

        pyautogui.moveTo(sx, sy, duration=0.15)
        pyautogui.mouseDown(button=button)
        time.sleep(0.05)
        pyautogui.moveTo(ex, ey, duration=max(0.1, duration))
        time.sleep(0.05)
        pyautogui.mouseUp(button=button)
        return f"Dragged from ({start_rel_x:.2f}, {start_rel_y:.2f}) to ({end_rel_x:.2f}, {end_rel_y:.2f}) on '{geo['title']}'."

    def draw_relative_shape(
        self,
        title_keyword: str,
        shape: str = "square",
        center_rel_x: float = 0.5,
        center_rel_y: float = 0.5,
        size_rel: float = 0.2,
    ) -> str:
        """
        Draw a geometric shape (square, circle, triangle, heart, star) relative to the target window canvas (e.g. Paint).
        """
        geo = self.get_window_geometry(title_keyword)
        if "error" in geo:
            return geo["error"]

        hwnd = geo["hwnd"]
        robust_bring_to_front(hwnd)
        time.sleep(0.15)

        rect = win32gui.GetWindowRect(hwnd)
        left, top, right, bottom = rect
        width = max(1, right - left)
        height = max(1, bottom - top)

        is_paint = any(w in geo.get("title", "").lower() or w in title_keyword.lower() for w in ["paint", "mspaint"])
        if is_paint:
            # In Win11 Paint, the ribbon/toolbar is ~165px high and status bar is ~40px
            canvas_top = top + 170
            canvas_bottom = max(canvas_top + 150, bottom - 45)
            canvas_left = left + 30
            canvas_right = max(canvas_left + 150, right - 30)
            c_width = canvas_right - canvas_left
            c_height = canvas_bottom - canvas_top
            cx = canvas_left + int(c_width * max(0.1, min(0.9, center_rel_x)))
            cy = canvas_top + int(c_height * max(0.1, min(0.9, center_rel_y)))
            radius = int(min(c_width, c_height) * max(0.05, min(0.35, size_rel / 2.0)))
        else:
            cx = left + int(width * max(0.05, min(0.95, center_rel_x)))
            cy = top + int(height * max(0.05, min(0.95, center_rel_y)))
            radius = int(min(width, height) * max(0.02, min(0.35, size_rel / 2.0)))

        import math
        shape_lower = shape.lower().strip()
        points: List[Tuple[int, int]] = []

        if shape_lower in ["circle", "round", "oval"]:
            steps = 36
            for i in range(steps + 1):
                angle = 2 * math.pi * (i / steps)
                px = cx + int(radius * math.cos(angle))
                py = cy + int(radius * math.sin(angle))
                points.append((px, py))

        elif shape_lower in ["triangle"]:
            for i in range(4):
                angle = -math.pi / 2 + (2 * math.pi * (i % 3) / 3)
                px = cx + int(radius * math.cos(angle))
                py = cy + int(radius * math.sin(angle))
                points.append((px, py))

        elif shape_lower in ["star"]:
            for i in range(11):
                angle = -math.pi / 2 + (i * math.pi / 5)
                r = radius if i % 2 == 0 else int(radius * 0.45)
                px = cx + int(r * math.cos(angle))
                py = cy + int(r * math.sin(angle))
                points.append((px, py))

        elif shape_lower in ["heart"]:
            for i in range(40):
                t = 2 * math.pi * (i / 39)
                x = 16 * (math.sin(t) ** 3)
                y = -(13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
                scale = radius / 16.0
                points.append((cx + int(x * scale), cy + int(y * scale)))

        else:  # default "square" or "rectangle"
            half = radius
            points = [
                (cx - half, cy - half),
                (cx + half, cy - half),
                (cx + half, cy + half),
                (cx - half, cy + half),
                (cx - half, cy - half),
            ]

        if not points:
            return "No points generated for shape."

        # 1. Focus canvas and ensure Pencil tool is selected if in Paint
        if is_paint:
            # Click the Pencil tool on the Paint toolbar ribbon (~left + 225, top + 75)
            ribbon_pencil_x = left + min(225, int(width * 0.22))
            ribbon_pencil_y = top + 75
            pyautogui.click(ribbon_pencil_x, ribbon_pencil_y)
            time.sleep(0.06)

        # Click inside canvas area to ensure focus
        pyautogui.click(cx, cy)
        time.sleep(0.06)

        # 2. Dense stroke interpolation for smooth inking without broken line segments
        def _get_interpolated_stroke(pts: List[Tuple[int, int]], step_px: int = 4) -> List[Tuple[int, int]]:
            res = [pts[0]]
            for i in range(len(pts) - 1):
                p1 = pts[i]
                p2 = pts[i + 1]
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                dist = (dx * dx + dy * dy) ** 0.5
                if dist < step_px:
                    res.append(p2)
                else:
                    n_steps = max(1, int(dist // step_px))
                    for s in range(1, n_steps + 1):
                        res.append((int(p1[0] + dx * s / n_steps), int(p1[1] + dy * s / n_steps)))
            return res

        stroke_points = _get_interpolated_stroke(points, step_px=4)

        # 3. Move to initial coordinate
        start_x, start_y = stroke_points[0]
        win32api.SetCursorPos((start_x, start_y))
        time.sleep(0.04)

        # 4. Real mouse down with left button to start inking
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        pyautogui.mouseDown(button="left")
        time.sleep(0.03)

        # 5. Smooth continuous inking drag across all parametric path points via Win32 MOUSEEVENTF_MOVE
        try:
            for pt in stroke_points[1:]:
                win32api.SetCursorPos((pt[0], pt[1]))
                win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, 0, 0, 0, 0)
                time.sleep(0.003)
        finally:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            pyautogui.mouseUp(button="left")

        time.sleep(0.04)
        return f"Successfully drew {shape} with ink on '{geo['title']}'."


def get_window_geometry_manager() -> WindowGeometryManager:
    return WindowGeometryManager.get_instance()
