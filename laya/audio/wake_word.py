"""
Laya Instant Continuous Wake-Word & Single-Pass Speech Engine
Monitors microphone stream with low-overhead dynamic VAD and CUDA-accelerated
phonetic keyword spotting for 'Laya', 'Hey Laya', 'Jarvis', or 'Computer'.
Supports seamless single-pass utterance: 'Hey Laya open paint and draw a heart'
executes immediately without requiring the user to speak twice.
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
from faster_whisper import WhisperModel

from laya.config import (
    AUDIO_SAMPLE_RATE,
    AUDIO_CHANNELS,
    VAD_ENERGY_THRESHOLD,
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
)

WAKE_KEYWORDS_REGEX = r"\b(?:hey|hi|hello)?[\s,]+(?:laya|leia|layer|liar|laia|leya|jarvis|computer)\b|\b(?:laya|leia|jarvis|computer)\b"
NON_COMMAND_WORDS = {"laya", "leia", "layer", "liar", "laia", "leya", "jarvis", "computer", "hey", "hello", "hi"}


class WakeWordDetector:
    _instance: Optional["WakeWordDetector"] = None

    def __init__(
        self,
        on_wake: Optional[Callable[[], None]] = None,
        on_command: Optional[Callable[[str], None]] = None,
    ):
        self.on_wake = on_wake
        self.on_command = on_command
        self.is_running = False
        self.is_listening_active = False  # Suppress wake word while actively processing
        self._thread: Optional[threading.Thread] = None

        # Lightweight, lightning-fast streaming Whisper model on CUDA (tiny.en: ~15ms)
        try:
            self._fast_stt = WhisperModel("tiny.en", device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)
        except Exception:
            self._fast_stt = WhisperModel("tiny.en", device="cpu", compute_type="int8")

    @classmethod
    def get_instance(
        cls,
        on_wake: Optional[Callable[[], None]] = None,
        on_command: Optional[Callable[[str], None]] = None,
    ) -> "WakeWordDetector":
        if cls._instance is None:
            cls._instance = cls(on_wake=on_wake, on_command=on_command)
        else:
            if on_wake:
                cls._instance.on_wake = on_wake
            if on_command:
                cls._instance.on_command = on_command
        return cls._instance

    def start(self):
        """Start always-on wake word listener thread."""
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        print("[WakeWord] Always-on continuous wake word active (Say 'Hey Laya [command]' or 'Jarvis')...")

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
        block_duration = 0.25  # 250ms chunks
        block_size = int(AUDIO_SAMPLE_RATE * block_duration)

        speech_buffer: List[np.ndarray] = []
        is_in_speech = False
        silence_count = 0

        try:
            with sd.InputStream(
                samplerate=AUDIO_SAMPLE_RATE,
                channels=AUDIO_CHANNELS,
                dtype="float32",
                blocksize=block_size,
            ) as stream:
                while self.is_running:
                    if self.is_listening_active:
                        time.sleep(0.08)
                        speech_buffer.clear()
                        is_in_speech = False
                        silence_count = 0
                        continue

                    data, _ = stream.read(block_size)
                    audio_chunk = data.flatten()
                    energy = float(np.sqrt(np.mean(audio_chunk**2)))

                    if energy > VAD_ENERGY_THRESHOLD:
                        is_in_speech = True
                        silence_count = 0
                        speech_buffer.append(audio_chunk)
                        # Cap max continuous speech at 6 seconds
                        if len(speech_buffer) > 24:
                            self._process_speech(speech_buffer)
                            speech_buffer = []
                            is_in_speech = False
                    else:
                        if is_in_speech:
                            silence_count += 1
                            speech_buffer.append(audio_chunk)
                            # ~0.5s of silence after speech -> speech ended
                            if silence_count >= 2:
                                self._process_speech(speech_buffer)
                                speech_buffer = []
                                is_in_speech = False
                                silence_count = 0
                        else:
                            # Keep tiny rolling pre-roll buffer (1 chunk)
                            speech_buffer = [audio_chunk]

        except Exception as e:
            print(f"[WakeWord Error] Stream stopped: {e}", file=sys.stderr)

    def _process_speech(self, chunks: List[np.ndarray]):
        """Transcribe speech clip on CUDA and check for single-pass wake word & command."""
        if not chunks or len(chunks) < 2:
            return

        full_clip = np.concatenate(chunks)
        # Skip clips shorter than 0.4s
        if len(full_clip) < int(AUDIO_SAMPLE_RATE * 0.4):
            return

        try:
            segments, _ = self._fast_stt.transcribe(full_clip, beam_size=1)
            text = " ".join([s.text for s in segments]).strip()
            if not text:
                return

            text_lower = text.lower().strip()
            match = re.search(WAKE_KEYWORDS_REGEX, text_lower)
            if match:
                print(f"[WakeWord] Trigger heard: '{text}'")
                # Extract subsequent command from the same utterance
                raw_cmd = text[match.end():].strip().lstrip(",.!? ").strip()
                clean_cmd = re.sub(r"^(?:hey|hi|hello)?[\s,]*(?:laya|jarvis|computer)[,\.!\s]*", "", raw_cmd, flags=re.IGNORECASE).strip()

                is_real_command = bool(clean_cmd and clean_cmd.lower() not in NON_COMMAND_WORDS and len(clean_cmd) >= 3)

                if is_real_command:
                    print(f"[WakeWord] Single-pass command executing: '{clean_cmd}'")
                    self.pause()
                    if self.on_command:
                        self.on_command(clean_cmd)
                else:
                    print(f"[WakeWord] Wake trigger activated, awaiting follow-up voice...")
                    self.pause()
                    if self.on_wake:
                        self.on_wake()

        except Exception as ex:
            pass


def get_wake_word_detector(
    on_wake: Optional[Callable[[], None]] = None,
    on_command: Optional[Callable[[str], None]] = None,
) -> WakeWordDetector:
    return WakeWordDetector.get_instance(on_wake=on_wake, on_command=on_command)
