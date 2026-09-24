"""
Laya Win32 Utilities & Rock-Solid Window Focus Management
Provides robust desktop station access, window enumeration, and reliable bring-to-front
handling that bypasses Windows 10/11 foreground lock restrictions.
"""

import sys
import time
import ctypes
from typing import List, Dict, Any, Optional, Tuple

import win32gui
import win32con
import win32process
import win32api


def ensure_desktop_access():
    """
    Binds the current thread to the interactive input desktop (WinSta0\\Default).
    Crucial for worker threads, background tasks, and subprocesses to see and manipulate windows.
    """
    try:
        user32 = ctypes.windll.user32
        h_desk = user32.OpenInputDesktop(0, False, 0x0100)  # MAXIMUM_ALLOWED / DESKTOP_ALL
        if h_desk:
            user32.SetThreadDesktop(h_desk)
    except Exception:
        pass


def get_desktop_work_area() -> Tuple[int, int, int, int]:
    """
    Get (left, top, right, bottom) of the primary monitor's work area,
    automatically excluding the Windows taskbar.
    """
    try:
        monitor = win32api.MonitorFromPoint((0, 0))
        info = win32api.GetMonitorInfo(monitor)
        return info["Work"]  # (left, top, right, bottom)
    except Exception:
        # Fallback to full screen metrics
        w = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        h = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        return (0, 0, w, h - 48)


def get_open_windows(min_size: Tuple[int, int] = (100, 100)) -> List[Dict[str, Any]]:
    """
    Return all visible, interactive top-level application windows.
    Excludes system utility/IME artifacts.
    """
    ensure_desktop_access()
    windows = []
    ignored_titles = {
        "Default IME", "MSCTFIME UI", "Program Manager", "Task Switching",
        "System tray overflow window.", "Battery Meter", "Shell Handwriting Canvas",
        "GDI+ Window (TabTip.exe)", "DesktopWindowXamlSource", "Windows Input Experience"
    }

    def enum_cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and not win32gui.IsIconic(hwnd):
            title = win32gui.GetWindowText(hwnd).strip()
            if title and title not in ignored_titles:
                rect = win32gui.GetWindowRect(hwnd)
                w = rect[2] - rect[0]
                h = rect[3] - rect[1]
                if w >= min_size[0] and h >= min_size[1]:
                    try:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    except Exception:
                        pid = 0
                    windows.append({
                        "hwnd": hwnd,
                        "title": title,
                        "rect": rect,
                        "width": w,
                        "height": h,
                        "pid": pid,
                    })
        elif win32gui.IsWindowVisible(hwnd) and win32gui.IsIconic(hwnd):
            # Include minimized windows
            title = win32gui.GetWindowText(hwnd).strip()
            if title and title not in ignored_titles:
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                except Exception:
                    pid = 0
                windows.append({
                    "hwnd": hwnd,
                    "title": title,
                    "rect": (0, 0, 0, 0),
                    "width": 0,
                    "height": 0,
                    "pid": pid,
                    "minimized": True,
                })
        return True

    try:
        win32gui.EnumWindows(enum_cb, None)
    except Exception:
        pass

    return windows


def find_window_by_query(query: str) -> Optional[Dict[str, Any]]:
    """Find the best matching window by application name or title keyword."""
    if not query or not query.strip():
        return None
    q = query.lower().strip()
    windows = get_open_windows(min_size=(50, 50))

    # 1. Exact match on title or app keyword
    for win in windows:
        if q == win["title"].lower():
            return win

    # 2. Substring match
    for win in windows:
        if q in win["title"].lower():
            return win

    # 3. Word boundary or partial match
    for win in windows:
        words = win["title"].lower().split()
        if any(q in word for word in words):
            return win

    return None


def robust_bring_to_front(hwnd: int) -> bool:
    """
    Brings a window to the front and gives it active focus.
    Bypasses Windows 10/11 foreground restrictions using thread attachment and SwitchToThisWindow.
    """
    if not hwnd or not win32gui.IsWindow(hwnd):
        return False

    ensure_desktop_access()

    try:
        # Restore if minimized
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

        fore_hwnd = win32gui.GetForegroundWindow()
        cur_thread_id = win32process.GetCurrentThreadId()
        fore_thread_id = win32process.GetWindowThreadProcessId(fore_hwnd)[0] if fore_hwnd else cur_thread_id
        target_thread_id = win32process.GetWindowThreadProcessId(hwnd)[0]

        attached = False
        if fore_thread_id != target_thread_id:
            try:
                ctypes.windll.user32.AttachThreadInput(cur_thread_id, target_thread_id, True)
                ctypes.windll.user32.AttachThreadInput(fore_thread_id, target_thread_id, True)
                attached = True
            except Exception:
                pass

        try:
            # Allow all processes to set foreground window
            ctypes.windll.user32.AllowSetForegroundWindow(-1)  # ASFW_ANY
        except Exception:
            pass

        # Simulate Alt key tap to unfreeze Windows foreground lock if needed
        try:
            win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
            win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
        except Exception:
            pass

        win32gui.BringWindowToTop(hwnd)
        win32gui.SetForegroundWindow(hwnd)

        try:
            # Force activation
            ctypes.windll.user32.SwitchToThisWindow(hwnd, True)
        except Exception:
            pass

        if attached:
            try:
                ctypes.windll.user32.AttachThreadInput(cur_thread_id, target_thread_id, False)
                ctypes.windll.user32.AttachThreadInput(fore_thread_id, target_thread_id, False)
            except Exception:
                pass

        return True
    except Exception as e:
        print(f"[Win32Utils] Bring to front warning: {e}")
        return False


def bring_window_to_front(query_or_hwnd: Any) -> Tuple[bool, str]:
    """
    Bring a window to the front given either an HWND or a natural title/app name.
    """
    if isinstance(query_or_hwnd, int):
        hwnd = query_or_hwnd
        title = win32gui.GetWindowText(hwnd) if win32gui.IsWindow(hwnd) else f"HWND {hwnd}"
        ok = robust_bring_to_front(hwnd)
        return (ok, f"Brought '{title}' to front." if ok else f"Could not focus HWND {hwnd}.")

    win = find_window_by_query(str(query_or_hwnd))
    if not win:
        return (False, f"No open window matching '{query_or_hwnd}' found.")

    ok = robust_bring_to_front(win["hwnd"])
    return (ok, f"Brought '{win['title']}' to the front." if ok else f"Failed to focus '{win['title']}'.")


def close_window_by_query(query: str) -> Tuple[bool, str]:
    """Gracefully close a window matching query using WM_CLOSE."""
    win = find_window_by_query(query)
    if not win:
        return (False, f"No open window matching '{query}' found.")

    try:
        win32gui.PostMessage(win["hwnd"], win32con.WM_CLOSE, 0, 0)
        return (True, f"Closed '{win['title']}'.")
    except Exception as e:
        return (False, f"Failed to close '{win['title']}': {e}")
