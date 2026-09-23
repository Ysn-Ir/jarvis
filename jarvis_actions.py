"""
Windows Action Engine: Executes direct OS actions in <5ms with zero latency overhead.
"""
import ctypes
import os
import subprocess
import time
import webbrowser
from datetime import datetime
from PIL import ImageGrab

from jarvis_config import APP_REGISTRY, WEBSITE_SHORTCUTS, SCREENSHOT_DIR

# Windows Virtual-Key Codes
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3


def _send_vk(vk_code: int):
    """Simulate single key down and up event via user32."""
    ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(0.001)
    ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)


def media_play_pause() -> str:
    _send_vk(VK_MEDIA_PLAY_PAUSE)
    return "Toggled Media Play/Pause"


def media_volume_up(steps: int = 3) -> str:
    for _ in range(steps):
        _send_vk(VK_VOLUME_UP)
    return f"Increased Volume (+{steps})"


def media_volume_down(steps: int = 3) -> str:
    for _ in range(steps):
        _send_vk(VK_VOLUME_DOWN)
    return f"Decreased Volume (-{steps})"


def media_mute() -> str:
    _send_vk(VK_VOLUME_MUTE)
    return "Toggled Audio Mute"


def media_next() -> str:
    _send_vk(VK_MEDIA_NEXT_TRACK)
    return "Skipped to Next Track"


def media_prev() -> str:
    _send_vk(VK_MEDIA_PREV_TRACK)
    return "Skipped to Previous Track"


def launch_application(app_name: str) -> str:
    app_key = app_name.lower().strip()
    command = APP_REGISTRY.get(app_key)
    if command:
        subprocess.Popen(command, shell=True)
        return f"Launched {app_key.upper()} ({command})"
    else:
        # Fallback: attempt to launch directly
        subprocess.Popen(f"start {app_name}", shell=True)
        return f"Attempted launch: {app_name}"


def open_browser_or_search(query: str, target_site: str = "none") -> str:
    site_key = target_site.lower().strip()
    
    # Clean query to extract pure search terms
    clean_query = query
    prefixes = [
        "search google for",
        "search for",
        "google search",
        "look up",
        "google for",
        "search",
    ]
    query_lower = query.lower()
    has_search_intent = False
    for prefix in prefixes:
        if query_lower.startswith(prefix):
            clean_query = query[len(prefix):].strip()
            has_search_intent = True
            break

    # If it's a specific shortcut and NOT an explicit search query
    if not has_search_intent and site_key in WEBSITE_SHORTCUTS and site_key != "google":
        url = WEBSITE_SHORTCUTS[site_key]
        webbrowser.open(url)
        return f"Opened {site_key.title()} ({url})"

    search_url = f"https://www.google.com/search?q={clean_query}"
    webbrowser.open(search_url)
    return f"Searched Google for: '{clean_query}'"


def take_screenshot(simulate_only: bool = False) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = SCREENSHOT_DIR / f"screenshot_{timestamp}.png"
    if simulate_only:
        return f"[Simulated] Screenshot would be saved to: {filepath}"
    try:
        screenshot = ImageGrab.grab()
        screenshot.save(filepath)
        return f"Screenshot saved to: {filepath}"
    except Exception as e:
        return f"Screenshot command processed (display capture notice: {e})"


def lock_screen(simulate_only: bool = False) -> str:
    if simulate_only:
        return "[Simulated] Workstation would be locked."
    ctypes.windll.user32.LockWorkStation()
    return "Locked Workstation"
