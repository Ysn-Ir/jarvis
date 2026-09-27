"""
Laya Universal Interruption & Barge-In Manager
Provides cross-thread cancellation tokens and instant abort controls
for speech synthesis, reasoning loops, automation tasks, and UI state.
"""

import threading
import sys
from typing import Optional, Callable, List

_abort_event = threading.Event()
_listeners: List[Callable[[], None]] = []
_lock = threading.Lock()


def request_interrupt(reason: str = "User interrupted"):
    """
    Trigger immediate abort across all running components.
    Stops TTS speech, halts ReAct reasoning loops, releases GUI locks, and resets UI.
    """
    _abort_event.set()
    print(f"\n🛑 [INTERRUPT] Abort signal triggered: {reason}", file=sys.stderr)

    # 1. Immediately cut off audio synthesis
    try:
        from laya.audio.tts import get_tts_engine
        get_tts_engine().stop()
    except Exception:
        pass

    # 2. Release any stuck mouse/keyboard states
    try:
        import pyautogui
        pyautogui.mouseUp()
    except Exception:
        pass

    # 3. Notify registered component listeners
    with _lock:
        for cb in _listeners:
            try:
                cb()
            except Exception:
                pass


def is_interrupt_requested() -> bool:
    """Check if an abort has been requested."""
    return _abort_event.is_set()


def reset_interrupt():
    """Clear abort state before starting a new task."""
    _abort_event.clear()


def register_interrupt_listener(callback: Callable[[], None]):
    """Register a callback to be called whenever interrupt is triggered."""
    with _lock:
        if callback not in _listeners:
            _listeners.append(callback)


def unregister_interrupt_listener(callback: Callable[[], None]):
    """Unregister an interrupt listener callback."""
    with _lock:
        if callback in _listeners:
            _listeners.remove(callback)
