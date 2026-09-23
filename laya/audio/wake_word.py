"""
Laya Always-On Wake Word Detection Engine
Monitors microphone stream using low-overhead dynamic VAD and CUDA-accelerated
phonetic keyword spotting for 'Laya', 'Hey Laya', 'Jarvis', or 'Computer'.
"""

import sys
import os
import re
import time
import queue
import threading
from typing import Optional, Callable, List

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
import sounddevice as sd

from laya.config import (
    AUDIO_SAMPLE_RATE,
    AUDIO_CHANNELS,
    VAD_ENERGY_THRESHOLD,
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
)
from laya.audio.stt import get_stt_engine

WAKE_KEYWORDS: List[str] = [
    "laya", "leia", "layer", "liar", "laia", "leya",
    "jarvis", "computer", "hey laya", "hey jarvis"
]


class WakeWordDetector:
    _instance: Optional["WakeWordDetector"] = None

    def __init__(self, on_wake: Optional[Callable[[], None]] = None):
        self.on_wake = on_wake
        self.is_running = False
        self.is_listening_active = False  # Suppress wake word while actively executing a command
        self._thread: Optional[threading.Thread] = None
        self._stt = get_stt_engine()

    @classmethod
    def get_instance(cls, on_wake: Optional[Callable[[], None]] = None) -> "WakeWordDetector":
        if cls._instance is None:
            cls._instance = cls(on_wake=on_wake)
        elif on_wake:
            cls._instance.on_wake = on_wake
        return cls._instance

    def start(self):
        """Start always-on wake word listener thread."""
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        print("[WakeWord] Always-on wake word engine active (Say 'Hey Laya' or 'Jarvis')...")

    def stop(self):
        """Stop listening."""
        self.is_running = False

    def pause(self):
        """Temporarily pause detection during active speech processing."""
        self.is_listening_active = True

    def resume(self):
        """Resume wake word listening."""
        self.is_listening_active = False

    def _listen_loop(self):
        """Continuous audio stream loop monitoring for speech and keywords."""
        block_duration = 0.5  # 500ms blocks
        block_size = int(AUDIO_SAMPLE_RATE * block_duration)
        audio_buffer = []

        try:
            with sd.InputStream(
                samplerate=AUDIO_SAMPLE_RATE,
                channels=AUDIO_CHANNELS,
                dtype="float32",
                blocksize=block_size,
            ) as stream:
                while self.is_running:
                    if self.is_listening_active:
                        time.sleep(0.1)
                        continue

                    data, _ = stream.read(block_size)
                    audio_chunk = data.flatten()
                    energy = float(np.sqrt(np.mean(audio_chunk**2)))

                    # Speech detected by energy
                    if energy > VAD_ENERGY_THRESHOLD:
                        audio_buffer.append(audio_chunk)
                        # Accumulate ~1.2 seconds of speech
                        if len(audio_buffer) >= 2:
                            full_clip = np.concatenate(audio_buffer)
                            audio_buffer = []

                            # Quick CUDA transcription (~40-60ms)
                            try:
                                text = self._stt.transcribe(full_clip).lower().strip()
                                if text:
                                    # Check for wake words
                                    if any(re.search(rf"\b{w}\b", text) for w in WAKE_KEYWORDS):
                                        print(f"[WakeWord] Triggered: '{text}'")
                                        self.pause()
                                        if self.on_wake:
                                            self.on_wake()
                            except Exception:
                                pass
                    else:
                        # Clear buffer on silence
                        audio_buffer = []

        except Exception as e:
            print(f"[WakeWord Error] Stream stopped: {e}", file=sys.stderr)


def get_wake_word_detector(on_wake: Optional[Callable[[], None]] = None) -> WakeWordDetector:
    return WakeWordDetector.get_instance(on_wake=on_wake)
