"""
Laya State-of-the-Art Neural TTS Engine
Dual-Engine Text-to-Speech:
1. Primary: Microsoft Edge Neural Voices (Human/JARVIS-level realism, inflection, breathing)
2. Fallback: Native Windows SAPI5 (0ms offline fallback)
Non-blocking background playback queue via pygame.mixer.
"""

import sys
import os
import queue
import threading
import time
import asyncio
import re
from pathlib import Path
from typing import Optional
import pygame
import pyttsx3

from laya.config import TTS_ENGINE, TTS_RATE, TTS_VOLUME, ROOT_DIR, EDGE_TTS_VOICE

CACHE_DIR = ROOT_DIR / "data" / "tts_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class TTSEngine:
    _instance: Optional["TTSEngine"] = None
    _lock = threading.Lock()

    def __init__(self, rate: int = TTS_RATE, volume: float = TTS_VOLUME, voice: str = EDGE_TTS_VOICE):
        self.rate = rate
        self.volume = volume
        self.voice = voice
        self.engine_mode = TTS_ENGINE
        self._running = True
        self._queue: queue.Queue[str] = queue.Queue()
        self._stop_event = threading.Event()

        # Initialize audio playback mixer
        try:
            pygame.mixer.init()
        except Exception as e:
            print(f"[TTS Audio] Pygame mixer init note: {e}")

        # Initialize SAPI5 fallback
        self._sapi_engine = None
        try:
            self._sapi_engine = pyttsx3.init("sapi5")
            self._sapi_engine.setProperty("rate", self.rate)
            self._sapi_engine.setProperty("volume", self.volume)
            # Explicitly choose male voice (e.g. Microsoft David)
            voices = self._sapi_engine.getProperty("voices")
            for v in voices:
                v_name = (getattr(v, "name", "") or "").lower()
                v_gender = str(getattr(v, "gender", "") or "").lower()
                if "david" in v_name or "male" in v_gender or "male" in v_name:
                    self._sapi_engine.setProperty("voice", v.id)
                    break
        except Exception:
            pass

        # Start non-blocking background worker
        self._worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self._worker_thread.start()

        # Pre-warm Edge-TTS in background so first user utterance is instant
        threading.Thread(target=self._prewarm_neural_engine, daemon=True).start()

    @classmethod
    def get_instance(cls) -> "TTSEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _prewarm_neural_engine(self):
        """Pre-warm WebSocket/SSL connection to Edge-TTS servers."""
        try:
            import edge_tts
            warm_file = CACHE_DIR / "warm.mp3"
            async def _warm():
                comm = edge_tts.Communicate("Ready.", self.voice)
                await asyncio.wait_for(comm.save(str(warm_file)), timeout=2.5)
            asyncio.run(_warm())
        except Exception:
            pass

    def _speak_neural(self, text: str) -> bool:
        """Synthesize and play audio using Edge Neural TTS (startup voice: en-US-ChristopherNeural)."""
        import uuid
        try:
            import edge_tts
            # Clean text of markdown formatting for speech
            speech_text = re.sub(r"[*_#`~\[\]\(\)]", "", text)
            speech_text = re.sub(r"https?://\S+", "link", speech_text)
            speech_text = re.sub(r"\s+", " ", speech_text).strip()

            if not speech_text:
                return True

            # Use unique filename to avoid Windows file-locking collisions
            unique_id = uuid.uuid4().hex[:12]
            cache_file = CACHE_DIR / f"speech_{unique_id}.mp3"

            async def _synthesize():
                comm = edge_tts.Communicate(speech_text, self.voice)
                # Generous 9.0s timeout to allow multi-sentence synthesis without dropping speech
                await asyncio.wait_for(comm.save(str(cache_file)), timeout=9.0)

            # Attempt synthesis with 1 retry on connection glitch
            for attempt in range(2):
                try:
                    asyncio.run(_synthesize())
                    if cache_file.exists() and cache_file.stat().st_size > 100:
                        break
                except Exception as ex:
                    if attempt == 1:
                        print(f"[TTS Neural Error] {ex}", file=sys.stderr)
                    time.sleep(0.15)

            if cache_file.exists() and cache_file.stat().st_size > 100:
                for play_attempt in range(2):
                    try:
                        if not pygame.mixer.get_init():
                            pygame.mixer.init()
                        pygame.mixer.music.load(str(cache_file))
                        pygame.mixer.music.play()
                        while pygame.mixer.music.get_busy() and not self._stop_event.is_set():
                            time.sleep(0.04)
                        return True
                    except Exception as play_err:
                        if play_attempt == 0:
                            # Audio device may have changed — try full reinit
                            try:
                                pygame.mixer.quit()
                                time.sleep(0.1)
                                pygame.mixer.init()
                            except Exception:
                                pass
                        else:
                            print(f"[TTS Playback] Falling back to SAPI5: {play_err}", file=sys.stderr)
                    finally:
                        try:
                            pygame.mixer.music.unload()
                        except Exception:
                            pass
                try:
                    if cache_file.exists():
                        cache_file.unlink(missing_ok=True)
                except Exception:
                    pass
                return True
        except Exception as e:
            print(f"[TTS Engine Notice] Neural voice failed: {e}", file=sys.stderr)
            return False

        return False

    def _speak_sapi5(self, text: str):
        """Emergency offline fallback (only if network is completely down)."""
        if self._sapi_engine:
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except Exception:
                pass
            try:
                clean_text = re.sub(r"[*_#`~\[\]]", "", text).strip()
                self._sapi_engine.say(clean_text)
                self._sapi_engine.runAndWait()
            except Exception as ex:
                print(f"[SAPI5 Error] {ex}", file=sys.stderr)

    def _speech_worker(self):
        """Worker thread processing spoken output from queue."""
        while self._running:
            try:
                text = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if self._stop_event.is_set():
                self._queue.task_done()
                continue

            if text:
                success = False
                # User preference: exclusively use the startup voice (Edge-TTS ChristopherNeural)
                if not self._stop_event.is_set():
                    success = self._speak_neural(text)

                if not success and not self._stop_event.is_set():
                    # Only attempt SAPI5 if edge-tts completely failed
                    self._speak_sapi5(text)

            self._queue.task_done()

    def speak(self, text: str, block: bool = False):
        """Queue or speak text."""
        if not text or not text.strip():
            return
        clean_text = text.strip()
        self._queue.put(clean_text)
        if block:
            self._queue.join()

    def stop(self):
        """Immediately abort current speech playback and clear queue."""
        self._stop_event.set()
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
        except Exception:
            pass
        if self._sapi_engine:
            try:
                self._sapi_engine.stop()
            except Exception:
                pass
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except Exception:
                pass
        time.sleep(0.04)
        self._stop_event.clear()

    def is_speaking(self) -> bool:
        """Check if speech is currently outputting or queued."""
        try:
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                return True
        except Exception:
            pass
        return not self._queue.empty()



def get_tts_engine() -> TTSEngine:
    return TTSEngine.get_instance()


if __name__ == "__main__":
    tts = get_tts_engine()
    tts.speak("Laya neural voice is now active.", block=True)
