"""
Laya UFO Controller (Microsoft UFO Windows UI Automation Paradigm)
Direct application control via native Windows UI Automation (UIA) tree inspection,
control clicking, text input, and window management without fragile pixel coordinates.
"""

from typing import Optional, List, Dict, Any
import win32gui
import win32con
import uiautomation as uia


class UFOController:
    _instance: Optional["UFOController"] = None

    @classmethod
    def get_instance(cls) -> "UFOController":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def list_open_windows(self) -> str:
        """List all visible application windows currently open on the desktop."""
        windows = []

        def enum_handler(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd).strip()
                if title and not title in ["Default IME", "MSCTFIME UI", "Program Manager"]:
                    rect = win32gui.GetWindowRect(hwnd)
                    width = rect[2] - rect[0]
                    height = rect[3] - rect[1]
                    if width > 100 and height > 100:
                        windows.append(f"• '{title}' (HWND: {hwnd})")
            return True

        try:
            win32gui.EnumWindows(enum_handler, None)
        except Exception as e:
            return f"Error enumerating windows: {e}"

        if not windows:
            return "No active visible desktop application windows found."

        return f"Currently active application windows ({len(windows)} found):\n" + "\n".join(windows[:12])

    def focus_window(self, title_query: str) -> str:
        """Bring a specific application window to the foreground."""
        if not title_query or not title_query.strip():
            return "No window title specified."
        from laya.tools.win32_utils import bring_window_to_front
        ok, msg = bring_window_to_front(title_query)
        return msg

    def inspect_window_controls(self, max_depth: int = 3) -> str:
        """
        Inspect the UI Automation control tree of the active foreground window.
        Returns all interactive buttons, inputs, tabs, and menu items.
        """
        try:
            fg = uia.GetForegroundControl()
            if not fg:
                return "No active foreground window found to inspect."

            title = fg.Name or "Active Window"
            c_type = fg.ControlTypeName
            lines = [f"Active Window: '{title}' [{c_type}]"]

            seen_controls = set()

            def walk(control, depth):
                if depth > max_depth:
                    return
                for child in control.GetChildren():
                    name = (child.Name or "").strip()
                    elem_type = child.ControlTypeName
                    auto_id = child.AutomationId or ""

                    # Filter for interactive controls
                    interactive_types = [
                        "ButtonControl", "EditControl", "TabItemControl",
                        "MenuItemControl", "CheckBoxControl", "ComboBoxControl",
                        "HyperlinkControl", "ListItemControl", "TreeItemControl"
                    ]

                    if name and (elem_type in interactive_types or len(name) > 1):
                        key = f"{elem_type}_{name}"
                        if key not in seen_controls:
                            seen_controls.add(key)
                            indent = "  " * depth
                            rect = child.BoundingRectangle
                            cx = (rect.left + rect.right) // 2
                            cy = (rect.top + rect.bottom) // 2
                            lines.append(f"{indent}├── [{elem_type}] '{name}' (pos: {cx},{cy})")

                    walk(child, depth + 1)

            walk(fg, 1)

            if len(lines) == 1:
                return f"Window '{title}' detected, but no standard interactive controls were exposed via UIA."

            return "\n".join(lines[:35])

        except Exception as e:
            return f"Failed to inspect window controls: {e}"

    def click_window_control(self, name: str) -> str:
        """
        Directly invoke or click an interactive UI element by name in the active window.
        """
        if not name or not name.strip():
            return "No control name provided."

        clean_name = name.strip()
        try:
            fg = uia.GetForegroundControl()
            if not fg:
                return "No active window found."

            # Search by exact name or substring
            target = fg.Control(searchDepth=5, Name=clean_name)
            if not target.Exists(maxSearchSeconds=1.0):
                # Try partial match
                for child in fg.GetChildren():
                    if child.Name and clean_name.lower() in child.Name.lower():
                        target = child
                        break

            if target and target.Exists(maxSearchSeconds=0.5):
                rect = target.BoundingRectangle
                cx = (rect.left + rect.right) // 2
                cy = (rect.top + rect.bottom) // 2
                try:
                    target.Click(simulateMove=False)
                except Exception:
                    import pyautogui
                    pyautogui.click(cx, cy)
                return f"Clicked UI control '{target.Name}' at ({cx}, {cy})."

            return f"Could not find accessible UI control matching '{clean_name}' in '{fg.Name}'."

        except Exception as e:
            return f"Error clicking control '{clean_name}': {e}"

    def set_window_control_text(self, name: str, text: str) -> str:
        """
        Set text into an input or edit box control in the active window.
        """
        if not text:
            return "No text provided to set."

        clean_name = name.strip()
        try:
            fg = uia.GetForegroundControl()
            if not fg:
                return "No active window found."

            target = fg.EditControl(searchDepth=5, Name=clean_name) if clean_name else fg.EditControl(searchDepth=3)
            if target.Exists(maxSearchSeconds=1.0):
                try:
                    target.SetValue(text)
                    return f"Set text in control '{target.Name}'."
                except Exception:
                    target.Click(simulateMove=False)
                    import pyperclip, pyautogui
                    pyperclip.copy(text)
                    pyautogui.hotkey("ctrl", "a")
                    pyautogui.hotkey("ctrl", "v")
                    return f"Pasted text into control '{target.Name}'."

            return f"Could not find an edit control matching '{clean_name}'."

        except Exception as e:
            return f"Error setting control text: {e}"


def get_ufo_controller() -> UFOController:
    return UFOController.get_instance()
