"""
Laya Autonomous Browser Automator
Direct high-speed browser interaction: URL opening, Google/YouTube search,
tab management, page navigation, and scrolling with zero coordinate guesswork.
"""

import time
import webbrowser
import urllib.parse
from typing import Optional, List
import pyautogui
import win32gui
import win32con

pyautogui.FAILSAFE = False


class BrowserAutomator:
    _instance: Optional["BrowserAutomator"] = None

    @classmethod
    def get_instance(cls) -> "BrowserAutomator":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _focus_browser(self) -> bool:
        """Find and focus an active browser window (Chrome, Edge, Firefox, Brave)."""
        browser_names = ["Google Chrome", "Microsoft​ Edge", "Edge", "Firefox", "Brave"]
        hwnd = None

        def enum_handler(h, _):
            nonlocal hwnd
            if win32gui.IsWindowVisible(h):
                title = win32gui.GetWindowText(h)
                for b in browser_names:
                    if b.lower() in title.lower():
                        hwnd = h
                        return False
            return True

        try:
            win32gui.EnumWindows(enum_handler, None)
        except Exception:
            pass

        if hwnd:
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.15)
                return True
            except Exception:
                pass
        return False

    def search_web(self, query: str, engine: str = "google") -> str:
        """Open web browser and search for query directly."""
        clean_q = query.strip()
        encoded = urllib.parse.quote_plus(clean_q)
        if engine.lower() == "youtube":
            url = f"https://www.youtube.com/results?search_query={encoded}"
        else:
            url = f"https://www.google.com/search?q={encoded}"

        webbrowser.open(url)
        time.sleep(0.3)
        self._focus_browser()
        return f"Opened browser and searched for '{clean_q}' on {engine.capitalize()}."

    def open_url(self, url: str) -> str:
        """Open a specific URL in the browser."""
        clean_url = url.strip()
        if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
            clean_url = "https://" + clean_url
        webbrowser.open(clean_url)
        time.sleep(0.3)
        self._focus_browser()
        return f"Navigated browser to {clean_url}."

    def new_tab(self, url: Optional[str] = None) -> str:
        """Open a new browser tab and optionally navigate."""
        self._focus_browser()
        pyautogui.hotkey("ctrl", "t")
        time.sleep(0.1)
        if url:
            return self.open_url(url)
        return "Opened new browser tab."

    def close_tab(self) -> str:
        """Close current browser tab."""
        self._focus_browser()
        pyautogui.hotkey("ctrl", "w")
        return "Closed active browser tab."

    def switch_tab(self, direction: str = "next") -> str:
        """Switch to next or previous tab."""
        self._focus_browser()
        if direction.lower() in ["prev", "previous", "left"]:
            pyautogui.hotkey("ctrl", "shift", "tab")
            return "Switched to previous tab."
        else:
            pyautogui.hotkey("ctrl", "tab")
            return "Switched to next tab."

    def scroll(self, direction: str = "down", amount: int = 5) -> str:
        """Scroll the active browser page."""
        self._focus_browser()
        clicks = -amount if direction.lower() == "down" else amount
        pyautogui.scroll(clicks * 100)
        return f"Scrolled page {direction}."

    def refresh(self) -> str:
        """Refresh current page."""
        self._focus_browser()
        pyautogui.hotkey("ctrl", "r")
        return "Refreshed browser page."

    def play_youtube(self, query: str) -> str:
        """
        Open YouTube, search for the query, and click the first video result using relative window geometry.
        """
        clean_q = query.strip()
        encoded = urllib.parse.quote_plus(clean_q)
        url = f"https://www.youtube.com/results?search_query={encoded}"

        webbrowser.open(url)
        time.sleep(1.0)
        self._focus_browser()
        time.sleep(0.5)

        # In standard YouTube desktop layout, the top video result is at rel_x=0.36, rel_y=0.30
        from laya.tools.window_geometry import get_window_geometry_manager
        geo_mgr = get_window_geometry_manager()

        for b_name in ["Chrome", "Edge", "Firefox", "Brave", "YouTube"]:
            res = geo_mgr.click_window_relative(b_name, rel_x=0.36, rel_y=0.30)
            if "error" not in res:
                return f"Started playing '{clean_q}' on YouTube."

        return f"Opened YouTube search for '{clean_q}'."


def get_browser_automator() -> BrowserAutomator:
    return BrowserAutomator.get_instance()
