"""
Laya High-Speed Zero-Latency TTS Engine
Uses native Windows SAPI5 via pyttsx3. Guaranteed 0ms network latency.
"""

import sys
import threading
import queue
import time
from typing import Optional
import pyttsx3

from laya.config import TTS_RATE, TTS_VOLUME


class TTSEngine:
    _instance: Optional["TTSEngine"] = None
    _lock = threading.Lock()

    def __init__(self, rate: int = TTS_RATE, volume: float = TTS_VOLUME):
        self.rate = rate
        self.volume = volume
        self._queue: queue.Queue[str] = queue.Queue()
        self._stop_event = threading.Event()
        self._worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self._worker_thread.start()

    @classmethod
    def get_instance(cls) -> "TTSEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _speech_worker(self):
        """Worker thread executing SAPI5 calls safely in dedicated COM apartment."""
        try:
            engine = pyttsx3.init("sapi5")
            engine.setProperty("rate", self.rate)
            engine.setProperty("volume", self.volume)
            
            # Select English voice if available
            voices = engine.getProperty("voices")
            for v in voices:
                if "david" in v.name.lower() or "zira" in v.name.lower() or "english" in v.name.lower():
                    engine.setProperty("voice", v.id)
                    break
        except Exception as e:
            print(f"[TTS Error] Initializing SAPI5 failed: {e}", file=sys.stderr)
            engine = None

        while not self._stop_event.is_set():
            try:
                text = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if text and engine:
                try:
                    engine.say(text)
                    engine.runAndWait()
                except Exception as ex:
                    print(f"[TTS Error] Failed to speak: {ex}", file=sys.stderr)
            self._queue.task_done()

    def speak(self, text: str, block: bool = False):
        """Queue or immediately speak text."""
        if not text or not text.strip():
            return
        clean_text = text.strip()
        self._queue.put(clean_text)
        if block:
            self._queue.join()

    def stop(self):
        """Clear queue and stop worker."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except Exception:
                pass


def get_tts_engine() -> TTSEngine:
    return TTSEngine.get_instance()


if __name__ == "__main__":
    tts = get_tts_engine()
    tts.speak("Laya online. Voice engine initialized.", block=True)
