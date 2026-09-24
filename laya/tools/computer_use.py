"""
Laya Computer Use & GUI Automation Tools
Direct mouse control, keyboard simulation, hotkeys, clipboard management,
and screen coordinate interaction for full desktop autonomy.
"""

import time
from typing import Optional, List, Tuple
import pyautogui
import pyperclip

# Safety settings: allow automation even if cursor is at screen boundaries
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05


class ComputerUseTools:
    _instance: Optional["ComputerUseTools"] = None

    @classmethod
    def get_instance(cls) -> "ComputerUseTools":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def mouse_click(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left", clicks: int = 1) -> str:
        """Click at (x, y) or at the current cursor location."""
        try:
            btn = button.lower() if button in ["left", "right", "middle"] else "left"
            if x is not None and y is not None:
                pyautogui.click(x=int(x), y=int(y), button=btn, clicks=int(clicks))
                return f"Mouse clicked {btn} ({clicks}x) at coordinates ({x}, {y})."
            pyautogui.click(button=btn, clicks=int(clicks))
            cur = pyautogui.position()
            return f"Mouse clicked {btn} ({clicks}x) at current position ({cur.x}, {cur.y})."
        except Exception as e:
            return f"Failed mouse click: {e}"

    def mouse_move(self, x: int, y: int) -> str:
        """Move cursor smoothly to (x, y)."""
        try:
            pyautogui.moveTo(int(x), int(y), duration=0.2)
            return f"Moved cursor to ({x}, {y})."
        except Exception as e:
            return f"Failed mouse move: {e}"

    def mouse_scroll(self, clicks: int = 3) -> str:
        """Scroll mouse wheel up (positive) or down (negative)."""
        try:
            pyautogui.scroll(int(clicks))
            direction = "up" if clicks > 0 else "down"
            return f"Scrolled mouse wheel {direction} by {abs(clicks)} clicks."
        except Exception as e:
            return f"Failed mouse scroll: {e}"

    def keyboard_type(self, text: str) -> str:
        """Type text into the currently active window."""
        try:
            if not text:
                return "No text provided to type."
            # If multiline or contains unicode, use clipboard paste for 100% fidelity
            if "\n" in text or any(ord(c) > 127 for c in text):
                old_clip = pyperclip.paste()
                pyperclip.copy(text)
                time.sleep(0.05)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.05)
                # Restore previous clipboard if desired
                return f"Typed text ({len(text)} chars) into active window via paste."
            else:
                pyautogui.write(text, interval=0.01)
                return f"Typed '{text}' into active window."
        except Exception as e:
            return f"Failed typing text: {e}"

    def keyboard_hotkey(self, keys: List[str]) -> str:
        """Execute a keyboard hotkey combination (e.g. ['ctrl', 't'])."""
        try:
            if not keys:
                return "No keys provided for hotkey."
            clean_keys = [str(k).lower().strip() for k in keys]
            # Map common synonyms
            key_map = {
                "control": "ctrl",
                "windows": "win",
                "super": "win",
                "cmd": "win",
                "return": "enter",
                "escape": "esc",
            }
            mapped = [key_map.get(k, k) for k in clean_keys]
            pyautogui.hotkey(*mapped)
            return f"Pressed shortcut: {' + '.join(mapped)}."
        except Exception as e:
            return f"Failed pressing hotkey: {e}"

    def clipboard_copy(self, text: str) -> str:
        """Copy string to system clipboard."""
        try:
            pyperclip.copy(text)
            preview = text[:40] + "..." if len(text) > 40 else text
            return f"Copied to clipboard: '{preview}'."
        except Exception as e:
            return f"Failed clipboard copy: {e}"

    def clipboard_read(self) -> str:
        """Read string from system clipboard."""
        try:
            content = pyperclip.paste()
            if not content:
                return "Clipboard is currently empty."
            return f"Clipboard contents: '{content}'."
        except Exception as e:
            return f"Failed reading clipboard: {e}"

    def press_key(self, key: str) -> str:
        """Press a single keyboard key (e.g. 'enter', 'esc', 'tab', 'space', 'backspace', 'f5')."""
        try:
            clean_key = str(key).lower().strip()
            pyautogui.press(clean_key)
            return f"Pressed key '{clean_key}'."
        except Exception as e:
            return f"Failed pressing key '{key}': {e}"

    def window_action(self, action: str) -> str:
        """Perform a quick window action: 'maximize', 'minimize', 'restore', 'snap_left', 'snap_right', 'show_desktop'."""
        try:
            act = action.lower().strip()
            if act in ["maximize", "max"]:
                pyautogui.hotkey("win", "up")
                return "Maximized active window."
            elif act in ["minimize", "min"]:
                pyautogui.hotkey("win", "down")
                return "Minimized active window."
            elif act in ["snap_left", "left"]:
                pyautogui.hotkey("win", "left")
                return "Snapped window to the left."
            elif act in ["snap_right", "right"]:
                pyautogui.hotkey("win", "right")
                return "Snapped window to the right."
            elif act in ["show_desktop", "desktop"]:
                pyautogui.hotkey("win", "d")
                return "Toggled desktop view."
            elif act in ["close", "close_tab"]:
                pyautogui.hotkey("ctrl", "w")
                return "Closed active tab."
            else:
                return f"Unknown window action: '{action}'."
        except Exception as e:
            return f"Window action failed: {e}"

    def get_mouse_position(self) -> str:
        """Get cursor position and primary screen resolution."""
        pos = pyautogui.position()
        size = pyautogui.size()
        return f"Cursor position: ({pos.x}, {pos.y}) | Screen resolution: {size.width}x{size.height}."

    def mouse_drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.3) -> str:
        """Click and drag from (start_x, start_y) to (end_x, end_y)."""
        try:
            pyautogui.moveTo(int(start_x), int(start_y))
            time.sleep(0.05)
            pyautogui.dragTo(int(end_x), int(end_y), duration=float(duration), button="left")
            return f"Dragged mouse from ({start_x}, {start_y}) to ({end_x}, {end_y})."
        except Exception as e:
            return f"Failed dragging mouse: {e}"

    def take_screenshot(self, filename: Optional[str] = None) -> str:
        """Capture full desktop screenshot and return screen dimensions and save path."""
        try:
            from laya.config import ROOT_DIR
            shots_dir = ROOT_DIR / "data" / "screenshots"
            shots_dir.mkdir(parents=True, exist_ok=True)
            fname = filename or f"screenshot_{int(time.time())}.png"
            path = shots_dir / fname
            im = pyautogui.screenshot()
            im.save(str(path))
            return f"Captured desktop screenshot ({im.width}x{im.height}) saved to {path}."
        except Exception as e:
            return f"Failed capturing screenshot: {e}"


    def draw_shape(
        self,
        shape_type: str = "circle",
        center_x: Optional[int] = None,
        center_y: Optional[int] = None,
        radius: int = 80,
        custom_points: Optional[List[Tuple[int, int]]] = None
    ) -> str:
        """
        Draw parametric geometric shapes or sketches in MS Paint or any canvas.
        Supported shapes: 'circle', 'heart', 'spiral', 'star', 'square', 'triangle', 'smiley', 'flower'.
        """
        import math
        try:
            # 1. Determine drawing center
            cx, cy = center_x, center_y
            if cx is None or cy is None:
                from laya.tools.win32_utils import find_window_by_query, robust_bring_to_front
                paint_win = find_window_by_query("paint")
                if paint_win:
                    robust_bring_to_front(paint_win["hwnd"])
                    time.sleep(0.15)
                    rect = paint_win["rect"]
                    # MS Paint canvas is positioned below the ribbon (approx +130px from top)
                    cx = (rect[0] + rect[2]) // 2
                    cy = max(rect[1] + 160, (rect[1] + rect[3]) // 2 + 30)
                else:
                    sz = pyautogui.size()
                    cx = sz.width // 2
                    cy = sz.height // 2

            r = max(20, min(400, int(radius)))
            clean_shape = str(shape_type).lower().strip()

            def _stroke(points_list: List[Tuple[int, int]], pause_sec: float = 0.012):
                if not points_list:
                    return
                pyautogui.moveTo(int(points_list[0][0]), int(points_list[0][1]))
                time.sleep(0.04)
                pyautogui.mouseDown(button="left")
                for px, py in points_list[1:]:
                    pyautogui.moveTo(int(px), int(py))
                    time.sleep(pause_sec)
                pyautogui.mouseUp(button="left")
                time.sleep(0.04)

            # 2. Compute stroke coordinates
            if custom_points:
                _stroke(custom_points)
                return f"Drew custom path with {len(custom_points)} points at ({cx}, {cy})."

            if clean_shape in ["circle", "round", "oval"]:
                pts = [
                    (cx + r * math.cos(2 * math.pi * i / 40), cy + r * math.sin(2 * math.pi * i / 40))
                    for i in range(41)
                ]
                _stroke(pts)

            elif clean_shape in ["heart", "love"]:
                # Parametric cardioid heart
                scale = r / 16.0
                pts = []
                for i in range(50):
                    t = 2 * math.pi * i / 49
                    hx = cx + (16 * (math.sin(t) ** 3)) * scale
                    hy = cy - (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)) * scale
                    pts.append((hx, hy))
                _stroke(pts)

            elif clean_shape in ["spiral"]:
                pts = []
                loops = 3
                steps = 60
                for i in range(steps + 1):
                    t = (2 * math.pi * loops) * (i / steps)
                    cur_r = (i / steps) * r
                    pts.append((cx + cur_r * math.cos(t), cy + cur_r * math.sin(t)))
                _stroke(pts)

            elif clean_shape in ["star"]:
                # 5-pointed star
                pts = []
                inner_r = r * 0.42
                for i in range(11):
                    angle = (i * math.pi / 5) - math.pi / 2
                    cur_r = r if i % 2 == 0 else inner_r
                    pts.append((cx + cur_r * math.cos(angle), cy + cur_r * math.sin(angle)))
                _stroke(pts, pause_sec=0.03)

            elif clean_shape in ["square", "rectangle", "box"]:
                pts = [
                    (cx - r, cy - r),
                    (cx + r, cy - r),
                    (cx + r, cy + r),
                    (cx - r, cy + r),
                    (cx - r, cy - r),
                ]
                _stroke(pts, pause_sec=0.04)

            elif clean_shape in ["triangle"]:
                pts = [
                    (cx, cy - r),
                    (cx + int(r * 0.866), cy + int(r * 0.5)),
                    (cx - int(r * 0.866), cy + int(r * 0.5)),
                    (cx, cy - r),
                ]
                _stroke(pts, pause_sec=0.04)

            elif clean_shape in ["smiley", "smile", "happy"]:
                # 1. Outer Face
                face_pts = [
                    (cx + r * math.cos(2 * math.pi * i / 36), cy + r * math.sin(2 * math.pi * i / 36))
                    for i in range(37)
                ]
                _stroke(face_pts)
                # 2. Left Eye
                eye_r = max(4, r // 8)
                left_eye_cx, left_eye_cy = cx - r // 3, cy - r // 4
                eye_pts = [
                    (left_eye_cx + eye_r * math.cos(2 * math.pi * i / 12), left_eye_cy + eye_r * math.sin(2 * math.pi * i / 12))
                    for i in range(13)
                ]
                _stroke(eye_pts, pause_sec=0.005)
                # 3. Right Eye
                right_eye_cx, right_eye_cy = cx + r // 3, cy - r // 4
                eye_pts_r = [
                    (right_eye_cx + eye_r * math.cos(2 * math.pi * i / 12), right_eye_cy + eye_r * math.sin(2 * math.pi * i / 12))
                    for i in range(13)
                ]
                _stroke(eye_pts_r, pause_sec=0.005)
                # 4. Smile Arc
                smile_pts = []
                smile_r = int(r * 0.6)
                for i in range(21):
                    angle = math.pi * 0.15 + (math.pi * 0.70) * (i / 20)
                    smile_pts.append((cx + smile_r * math.cos(angle), cy + smile_r * math.sin(angle) - r // 8))
                _stroke(smile_pts, pause_sec=0.015)

            elif clean_shape in ["flower", "rose"]:
                pts = []
                for i in range(80):
                    t = 2 * math.pi * i / 79
                    cur_r = r * math.cos(4 * t)
                    pts.append((cx + cur_r * math.cos(t), cy + cur_r * math.sin(t)))
                _stroke(pts)

            else:
                # Default to circle
                pts = [
                    (cx + r * math.cos(2 * math.pi * i / 36), cy + r * math.sin(2 * math.pi * i / 36))
                    for i in range(37)
                ]
                _stroke(pts)

            return f"Successfully drew a {clean_shape} (radius {r}px) on canvas at ({cx}, {cy})."
        except Exception as e:
            return f"Failed drawing shape: {e}"


def get_computer_use_tools() -> ComputerUseTools:
    return ComputerUseTools.get_instance()


