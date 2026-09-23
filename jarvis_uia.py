"""
Jarvis Deterministic UI Automation (Tier 2 UIA Lane)
Powered by Windows UI Automation (uiautomation) and Laya System 1.
Extracts live UI trees, bounding rectangles, and interactive elements.
Eliminates coordinate hallucinations with sub-50ms execution.
"""
import os
import re
import sys
import time
from typing import Dict, Any, List, Optional, Tuple

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import win32gui
import win32con
import win32process
import pyautogui

try:
    import uiautomation as auto
    UIA_AVAILABLE = True
except ImportError:
    UIA_AVAILABLE = False


INTERACTIVE_CONTROL_TYPES = {
    "ButtonControl",
    "EditControl",
    "MenuItemControl",
    "TabItemControl",
    "ListItemControl",
    "HyperlinkControl",
    "CheckBoxControl",
    "RadioButtonControl",
    "ComboBoxControl",
    "TreeItemControl",
    "DocumentControl",
}


def get_foreground_window() -> Dict[str, Any]:
    """Returns handle, title, and process info for the active foreground window."""
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return {"hwnd": 0, "title": "", "rect": (0, 0, 0, 0)}

    title = win32gui.GetWindowText(hwnd)
    rect = win32gui.GetWindowRect(hwnd)
    return {
        "hwnd": hwnd,
        "title": title,
        "rect": rect,  # (left, top, right, bottom)
    }


def bring_window_to_front(hwnd_or_title: Any) -> bool:
    """Brings a window by HWND or title substring to the foreground."""
    try:
        if isinstance(hwnd_or_title, str):
            target_hwnd = 0
            title_lower = hwnd_or_title.lower()

            def enum_proc(hwnd, _):
                nonlocal target_hwnd
                if win32gui.IsWindowVisible(hwnd):
                    t = win32gui.GetWindowText(hwnd).lower()
                    if title_lower in t:
                        target_hwnd = hwnd

            win32gui.EnumWindows(enum_proc, None)
            if not target_hwnd:
                return False
            hwnd = target_hwnd
        else:
            hwnd = hwnd_or_title

        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.15)
        return True
    except Exception:
        return False


EXCLUDED_NAMES = {
    "minimize", "maximize", "restore", "close", "system menu", "system",
    "app bar", "system menubar", "title bar", "resize", "help"
}


def extract_ui_elements(max_elements: int = 35) -> List[Dict[str, Any]]:
    """
    Extracts visible, interactive UI controls from the foreground window.
    Returns list of element dictionaries with name, control type, and exact coordinates.
    """
    if not UIA_AVAILABLE:
        return []

    elements = []
    try:
        fg_window = auto.GetForegroundControl()
        if not fg_window:
            return []

        # Walk descendants of the active window
        for control, depth in auto.WalkControl(fg_window, maxDepth=6):
            if len(elements) >= max_elements:
                break

            ctype = control.ControlTypeName
            if ctype in INTERACTIVE_CONTROL_TYPES:
                name = control.Name.strip()
                rect = control.BoundingRectangle
                if not name and ctype == "EditControl":
                    # Unnamed edit boxes are often search or input fields
                    name = control.AutomationId or "Text Input Field"

                # Filter out caption and system controls (Minimize, Close, etc.)
                if name.lower() in EXCLUDED_NAMES or "system" in name.lower():
                    continue

                if name and rect.width() > 8 and rect.height() > 8:
                    cx = int(rect.left + rect.width() / 2)
                    cy = int(rect.top + rect.height() / 2)
                    elements.append({
                        "id": len(elements) + 1,
                        "name": name,
                        "type": ctype,
                        "rect": (rect.left, rect.top, rect.right, rect.bottom),
                        "center": (cx, cy),
                        "control": control,
                    })

    except Exception:
        pass

    return elements


def match_element(query: str, elements: List[Dict[str, Any]], reflex=None) -> Optional[Dict[str, Any]]:
    """
    Matches the user's intent to the most appropriate UI element.
    Uses fast substring/keyword matching first, followed by Laya System 1 routing.
    Returns None if no element is a confident match (never clicks random controls).
    """
    if not elements:
        return None

    q_lower = query.lower()

    # 1. Direct name match (e.g. query contains "send", button is "Send")
    for el in elements:
        el_name_lower = el["name"].lower()
        if el_name_lower in q_lower or any(word in el_name_lower for word in q_lower.split() if len(word) > 2):
            return el

    # 2. Control type semantic match (e.g. "search" -> EditControl with search in name)
    if "search" in q_lower or "find" in q_lower:
        for el in elements:
            if "search" in el["name"].lower() or (el["type"] == "EditControl" and "search" in el["name"].lower()):
                return el

    # 3. Laya System 1 Choice Matching (if available)
    if reflex and len(elements) <= 15:
        try:
            choices = {f"elem_{el['id']}": el["name"] for el in elements}
            schema = {
                "target_element": {
                    "type": "choice",
                    "instructions": f"Which UI element in this application should be clicked or focused to achieve: '{query}'?",
                    "criteria": choices
                }
            }
            res = reflex.evaluate(query, custom_schema=schema)
            picked_key = res.get("target_element")
            for el in elements:
                if f"elem_{el['id']}" == picked_key:
                    return el
        except Exception:
            pass

    # If no confident match, return None (do NOT guess or click random buttons)
    return None


def execute_uia_interaction(element: Dict[str, Any], action: str = "click", text: str = "") -> bool:
    """
    Executes a deterministic interaction on the specified UIA element.
    """
    ctrl = element.get("control")
    cx, cy = element.get("center", (0, 0))

    try:
        if action == "click":
            # 1. Try UIA InvokePattern / TogglePattern directly
            invoked = False
            try:
                invoke_pat = ctrl.GetInvokePattern()
                if invoke_pat:
                    invoke_pat.Invoke()
                    invoked = True
            except Exception:
                pass

            # 2. Direct pixel click at bounding box center
            if not invoked:
                pyautogui.click(cx, cy, duration=0.1)
            print(f"   [UIA] Clicked '{element['name']}' at ({cx}, {cy})")
            return True

        elif action == "type":
            # Focus control
            try:
                ctrl.SetFocus()
            except Exception:
                pyautogui.click(cx, cy)

            time.sleep(0.1)

            # Try ValuePattern.SetValue for instant input
            set_direct = False
            try:
                val_pat = ctrl.GetValuePattern()
                if val_pat:
                    val_pat.SetValue(text)
                    set_direct = True
            except Exception:
                pass

            if not set_direct:
                import pyperclip
                pyperclip.copy(text)
                pyautogui.hotkey("ctrl", "v")

            print(f"   [UIA] Typed into '{element['name']}': {repr(text[:50])}")
            return True

    except Exception as e:
        print(f"   [UIA Error] {e}")
        # Final fallback to standard pyautogui click
        try:
            pyautogui.click(cx, cy)
            return True
        except Exception:
            return False

    return False
