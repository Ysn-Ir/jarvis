"""
Jarvis High-Speed TTS Engine (v5.0)
- Primary: Local Windows SAPI5 (pyttsx3) - 0ms latency, 100% offline, zero DNS freezes.
- Optional: Microsoft Edge Neural TTS (edge-tts) when network is active.
"""
import asyncio
import io
import os
import re
import sys
import threading
from typing import Optional

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from jarvis_config import TTS_ENGINE, TTS_RATE, TTS_VOICE, TTS_EDGE_RATE


class JarvisTTS:
    """Zero-lag, resilient Text-to-Speech engine."""

    def __init__(self, engine_type: str = None, voice: str = None, rate: int = None):
        self.engine_type = engine_type or TTS_ENGINE
        self.voice = voice or TTS_VOICE
        self.rate = rate or TTS_RATE
        self._lock = threading.Lock()
        self._pyttsx3_engine = None
        self._edge_available = False

        if self.engine_type == "edge":
            self._edge_available = self._check_edge_online()
            if self._edge_available:
                print(f"🔊 [TTS] Edge Neural Voice active: {self.voice}")
            else:
                print("🔊 [TTS] Edge offline. Using local SAPI5 (pyttsx3).")
                self._init_pyttsx3()
        else:
            print("🔊 [TTS] Local Windows SAPI5 active (Instant 0ms audio).")
            self._init_pyttsx3()

    def _check_edge_online(self) -> bool:
        """Non-blocking socket check with 0.8s timeout."""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.8)
            result = sock.connect_ex(("1.1.1.1", 53))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _init_pyttsx3(self):
        """Initializes local SAPI5 TTS engine cleanly."""
        try:
            import pyttsx3
            self._pyttsx3_engine = pyttsx3.init()
            self._pyttsx3_engine.setProperty("rate", self.rate)

            # Pick best voice (Zira or David)
            voices = self._pyttsx3_engine.getProperty("voices")
            if voices:
                selected_voice = voices[0].id
                for v in voices:
                    if "zira" in v.name.lower() or "david" in v.name.lower():
                        selected_voice = v.id
                        break
                self._pyttsx3_engine.setProperty("voice", selected_voice)
        except Exception as e:
            print(f"⚠️ [TTS] pyttsx3 init error: {e}")

    def _clean_text(self, text: str) -> str:
        """Strips markdown and emojis for clean speech articulation."""
        text = re.sub(r"```[\s\S]*?```", "code block", text)
        text = re.sub(r"`[^`]+`", "", text)
        text = re.sub(r"https?://\S+", "", text)
        text = re.sub(r"[*_#~>\[\]()]", "", text)
        text = re.sub(r"\[.*?\]", "", text)
        text = re.sub(r"[^\w\s.,!?:;'\"]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _shorten(self, text: str, max_sentences: int = 3) -> str:
        sentences = [s.strip() for s in re.split(r"[.!?]", text) if s.strip()]
        spoken = ". ".join(sentences[:max_sentences])
        return (spoken + ".") if spoken else text

    def speak(self, text: str, full: bool = False):
        if not text or not text.strip():
            return
        clean = self._clean_text(text)
        if not full:
            clean = self._shorten(clean)
        if not clean:
            return

        preview = clean[:80] + ("..." if len(clean) > 80 else "")
        print(f'🤖 [Jarvis]: "{preview}"')

        if self._edge_available:
            self._speak_edge(clean)
        else:
            self._speak_pyttsx3(clean)

    def _speak_pyttsx3(self, text: str):
        if not self._pyttsx3_engine:
            self._init_pyttsx3()
        if not self._pyttsx3_engine:
            return

        with self._lock:
            try:
                self._pyttsx3_engine.say(text)
                self._pyttsx3_engine.runAndWait()
            except Exception:
                # If engine state is dirty, re-initialize
                try:
                    import pyttsx3
                    self._pyttsx3_engine = pyttsx3.init()
                    self._pyttsx3_engine.setProperty("rate", self.rate)
                    self._pyttsx3_engine.say(text)
                    self._pyttsx3_engine.runAndWait()
                except Exception as e:
                    print(f"⚠️ [TTS Error]: {e}")

    def _speak_edge(self, text: str):
        try:
            asyncio.run(self._edge_async(text))
        except Exception:
            # Fall back to local SAPI5 immediately on any network drop
            self._edge_available = False
            self._speak_pyttsx3(text)

    async def _edge_async(self, text: str):
        import edge_tts
        communicate = edge_tts.Communicate(text, voice=self.voice, rate=TTS_EDGE_RATE)
        audio_bytes = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes.write(chunk["data"])
        audio_bytes.seek(0)
        data = audio_bytes.read()
        if data:
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            buf = io.BytesIO(data)
            pygame.mixer.music.load(buf, "mp3")
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)


_tts_instance = None


def get_tts(voice: Optional[str] = None) -> JarvisTTS:
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = JarvisTTS(voice=voice)
    return _tts_instance


if __name__ == "__main__":
    tts = get_tts()
    tts.speak("Jarvis speech engine online and ready.")
