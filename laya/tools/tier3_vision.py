"""
Laya Tier 3 GUI Vision Fallback Agent
Last-resort screen-grounded action loop when neither native APIs (Tier 1)
nor Windows UI Automation accessibility trees (Tier 2) expose target controls.
"""

import time
from typing import Optional, Tuple
import pyautogui
import mss

from laya.audio.tts import get_tts_engine


class Tier3VisionAgent:
    _instance: Optional["Tier3VisionAgent"] = None

    def __init__(self):
        self.tts = get_tts_engine()

    @classmethod
    def get_instance(cls) -> "Tier3VisionAgent":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def announce_vision_fallback(self):
        """Mandatory latency notice per AGENTS.md Section 3.6."""
        self.tts.speak("I'll need to click through this manually, one moment.")

    def click_coordinate(self, x: int, y: int) -> str:
        """Click grounded screen coordinate."""
        try:
            self.announce_vision_fallback()
            time.sleep(0.5)
            pyautogui.moveTo(x, y, duration=0.2)
            pyautogui.click()
            return f"Clicked at coordinate ({x}, {y})."
        except Exception as e:
            return f"Vision click failed: {e}"

    def type_text(self, text: str) -> str:
        """Type text into active focused control."""
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            pyautogui.hotkey("ctrl", "v")
            return f"Entered text via clipboard buffer."
        except Exception as e:
            return f"Typing failed: {e}"


def get_vision_agent() -> Tier3VisionAgent:
    return Tier3VisionAgent.get_instance()
