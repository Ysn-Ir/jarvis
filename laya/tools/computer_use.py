"""
Laya Computer Use & GUI Automation Tools
Direct mouse control, keyboard simulation, hotkeys, clipboard management,
and screen coordinate interaction for full desktop autonomy.
"""

import time
from pathlib import Path
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
        """Capture full desktop screenshot, save to Pictures/Screenshots, and open it."""
        try:
            import datetime as _dt
            import os as _os
            out_dir = Path.home() / "Pictures" / "Screenshots"
            out_dir.mkdir(parents=True, exist_ok=True)
            fname = filename or f"screenshot_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            path = out_dir / fname
            # Try PIL ImageGrab first (better quality), fallback to pyautogui
            try:
                from PIL import ImageGrab
                img = ImageGrab.grab(all_screens=False)
                img.save(str(path))
                w, h = img.width, img.height
            except Exception:
                img = pyautogui.screenshot()
                img.save(str(path))
                w, h = img.width, img.height
            try:
                _os.startfile(str(path))
            except Exception:
                pass
            return f"Screenshot captured ({w}x{h}) and saved to {path.name}."
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
                from laya.tools.interrupt_manager import is_interrupt_requested
                if is_interrupt_requested():
                    return
                pyautogui.moveTo(int(points_list[0][0]), int(points_list[0][1]))
                time.sleep(0.04)
                pyautogui.mouseDown(button="left")
                try:
                    for px, py in points_list[1:]:
                        if is_interrupt_requested():
                            break
                        pyautogui.moveTo(int(px), int(py))
                        time.sleep(pause_sec)
                finally:
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

    # -------------------------------------------------------------
    # Zoom / Magnify Region
    # -------------------------------------------------------------
    def zoom_window_region(
        self,
        region: str = "center",
        title_keyword: str = "",
        zoom_factor: float = 2.5,
        rel_x: float = 0.5,
        rel_y: float = 0.5,
        rel_w: float = 0.4,
        rel_h: float = 0.4,
    ) -> str:
        """
        Capture and magnify a region of any window (or full screen) and display it
        in a floating, transparent always-on-top HUD that auto-closes after 5 seconds.

        region   : "center", "top-left", "top-right", "bottom-left", "bottom-right",
                   "top", "bottom", "left", "right", or "custom" (uses rel_x/y/w/h).
        title_keyword : Window title substring to magnify (empty = full screen).
        zoom_factor   : Magnification multiplier (default 2.5×).
        rel_x/y/w/h   : Relative anchor point & size when region="custom" (0.0–1.0).
        """
        import threading
        import datetime

        try:
            from PIL import ImageGrab, Image, ImageTk
            import tkinter as tk
        except ImportError:
            return "Zoom requires Pillow and tkinter (both are already installed with Python on Windows)."

        try:
            # --- Determine capture rectangle ---
            if title_keyword:
                from laya.tools.win32_utils import find_window_by_query, robust_bring_to_front
                import win32gui
                win = find_window_by_query(title_keyword)
                if not win or not win.get("hwnd"):
                    return f"No window found matching '{title_keyword}'."
                hwnd = win["hwnd"]
                robust_bring_to_front(hwnd)
                time.sleep(0.15)
                rect = win32gui.GetWindowRect(hwnd)
                wx, wy, wr, wb = rect
                ww, wh = wr - wx, wb - wy
            else:
                import pyautogui as _pag
                sw, sh = _pag.size()
                wx, wy, ww, wh = 0, 0, sw, sh

            # --- Map named region to relative coords ---
            region_map = {
                "center":       (0.25, 0.25, 0.5, 0.5),
                "top-left":     (0.0,  0.05, 0.45, 0.45),
                "top-right":    (0.55, 0.05, 0.45, 0.45),
                "bottom-left":  (0.0,  0.55, 0.45, 0.4),
                "bottom-right": (0.55, 0.55, 0.45, 0.4),
                "top":          (0.1,  0.05, 0.8, 0.35),
                "bottom":       (0.1,  0.6,  0.8, 0.35),
                "left":         (0.0,  0.1,  0.35, 0.8),
                "right":        (0.65, 0.1,  0.35, 0.8),
            }
            key = region.lower().strip().replace("_", "-")
            if key in region_map:
                rx, ry, rw, rh = region_map[key]
            else:
                rx, ry, rw, rh = rel_x, rel_y, rel_w, rel_h

            # Clamp to window bounds
            cap_x = wx + int(ww * max(0.0, rx))
            cap_y = wy + int(wh * max(0.0, ry))
            cap_w = max(30, int(ww * min(1.0, rw)))
            cap_h = max(30, int(wh * min(1.0, rh)))

            # --- Capture & zoom ---
            img = ImageGrab.grab(bbox=(cap_x, cap_y, cap_x + cap_w, cap_y + cap_h), all_screens=False)
            zoom_factor = max(1.2, min(6.0, float(zoom_factor)))
            zoomed_w = int(cap_w * zoom_factor)
            zoomed_h = int(cap_h * zoom_factor)
            img_zoomed = img.resize((zoomed_w, zoomed_h), Image.LANCZOS)

            # Cap display size to 80% of screen
            import pyautogui as _pag2
            scr_w, scr_h = _pag2.size()
            disp_w = min(zoomed_w, int(scr_w * 0.8))
            disp_h = min(zoomed_h, int(scr_h * 0.8))
            if disp_w < zoomed_w or disp_h < zoomed_h:
                img_zoomed = img_zoomed.resize((disp_w, disp_h), Image.LANCZOS)

            label_txt = f"{zoom_factor:.1f}× zoom — {region} — {cap_w}×{cap_h}px → {disp_w}×{disp_h}px"

            def _show_hud():
                root = tk.Tk()
                root.title("Laya Zoom")
                root.overrideredirect(True)
                root.attributes("-topmost", True)
                root.attributes("-alpha", 0.96)

                # Position: center of screen
                win_x = (scr_w - disp_w) // 2
                win_y = (scr_h - disp_h) // 2 - 30
                root.geometry(f"{disp_w}x{disp_h + 44}+{win_x}+{win_y}")
                root.configure(bg="#0a0a14")

                # Header bar
                header = tk.Frame(root, bg="#0d1b2a", height=30)
                header.pack(fill=tk.X, side=tk.TOP)
                tk.Label(
                    header, text=f"  🔍  LAYA ZOOM  ·  {label_txt}  ·  Click to dismiss",
                    bg="#0d1b2a", fg="#00d4ff",
                    font=("Segoe UI", 9, "bold"), anchor="w"
                ).pack(side=tk.LEFT, padx=6, pady=4)

                # Image canvas
                tk_img = ImageTk.PhotoImage(img_zoomed)
                canvas = tk.Canvas(root, width=disp_w, height=disp_h, bg="#000010", highlightthickness=0)
                canvas.pack(fill=tk.BOTH, expand=True)
                canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)

                # Subtle cyan border
                canvas.create_rectangle(1, 1, disp_w - 1, disp_h - 1,
                                         outline="#00d4ff", width=2)

                def _close(_=None):
                    root.destroy()

                root.bind("<Button-1>", _close)
                root.bind("<Escape>", _close)
                root.bind("<Return>", _close)

                # Auto-close after 6 seconds
                root.after(6000, _close)
                root.mainloop()

            t = threading.Thread(target=_show_hud, daemon=True)
            t.start()

            return f"Zoomed {zoom_factor:.1f}× into {region} region ({cap_w}×{cap_h}px) of '{title_keyword or 'screen'}'."

        except Exception as e:
            return f"Zoom failed: {e}"

    # -------------------------------------------------------------
    # Smart Window Scroll
    # -------------------------------------------------------------
    def scroll_window(
        self,
        direction: str = "down",
        amount: int = 5,
        title_keyword: str = "",
    ) -> str:
        """
        Scroll inside any named window (file explorer, browser, document, etc.)
        by moving the cursor to that window's center then scrolling.

        direction    : "up", "down", "left", "right", "page_up", "page_down",
                       "top" (Ctrl+Home), "bottom" (Ctrl+End).
        amount       : Number of scroll notches (default 5).
        title_keyword: Window title to scroll (empty = active window).
        """
        try:
            direction = direction.lower().strip()

            # Focus the target window if specified
            if title_keyword:
                from laya.tools.win32_utils import find_window_by_query, robust_bring_to_front
                import win32gui
                win = find_window_by_query(title_keyword)
                if win and win.get("hwnd"):
                    hwnd = win["hwnd"]
                    robust_bring_to_front(hwnd)
                    time.sleep(0.15)
                    rect = win32gui.GetWindowRect(hwnd)
                    cx = (rect[0] + rect[2]) // 2
                    cy = (rect[1] + rect[3]) // 2
                    pyautogui.moveTo(cx, cy, duration=0.1)
                else:
                    return f"No window found matching '{title_keyword}'."
            else:
                # Keep focus on current active window
                pos = pyautogui.position()
                pyautogui.moveTo(pos.x, pos.y)

            # Keyboard-based navigation for page-level and edge jumps
            if direction in ["page_down", "pagedown", "page down"]:
                pyautogui.press("pagedown")
                return f"Page down in '{title_keyword or 'active window'}'."

            elif direction in ["page_up", "pageup", "page up"]:
                pyautogui.press("pageup")
                return f"Page up in '{title_keyword or 'active window'}'."

            elif direction in ["top", "home", "beginning"]:
                pyautogui.hotkey("ctrl", "home")
                return f"Jumped to top of '{title_keyword or 'active window'}'."

            elif direction in ["bottom", "end"]:
                pyautogui.hotkey("ctrl", "end")
                return f"Jumped to bottom of '{title_keyword or 'active window'}'."

            elif direction in ["left"]:
                pyautogui.hscroll(-abs(amount))
                return f"Scrolled left {amount} notches in '{title_keyword or 'active window'}'."

            elif direction in ["right"]:
                pyautogui.hscroll(abs(amount))
                return f"Scrolled right {amount} notches in '{title_keyword or 'active window'}'."

            elif direction in ["up"]:
                pyautogui.scroll(abs(amount))
                return f"Scrolled up {amount} notches in '{title_keyword or 'active window'}'."

            else:  # default: down
                pyautogui.scroll(-abs(amount))
                return f"Scrolled down {amount} notches in '{title_keyword or 'active window'}'."

        except Exception as e:
            return f"Scroll failed: {e}"


def get_computer_use_tools() -> ComputerUseTools:
    return ComputerUseTools.get_instance()
