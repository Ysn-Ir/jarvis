"""
Continuous Wake-Word, Universal Trigger & Real-Time Barge-In Engine
Monitors microphone stream with low-overhead dynamic VAD and CUDA-accelerated
phonetic keyword spotting for configurable wake phrases ('call', 'assistant', 'computer', 'jarvis', 'hey', etc.).
Supports single-pass utterances ('Call open Spotify and play synthwave') and live voice interruption
even while processing or speaking.
"""

import sys
import os
import re
import time
import queue
import threading
from typing import Optional, Callable, List, Tuple, Set

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
    WAKE_PHRASES,
)
from laya.tools.interrupt_manager import request_interrupt, is_interrupt_requested

INTERRUPT_KEYWORDS_REGEX = r"\b(?:stop|shut\s*up|quiet|cancel|silence|halt|pause|abort|wait|freeze|hold\s*on)\b"


def compile_wake_patterns() -> Tuple[re.Pattern, Set[str]]:
    """Build dynamic regex matching any configured wake phrase or trigger word."""
    all_phrases = list(WAKE_PHRASES)
    raw_env = os.getenv("WAKE_PHRASES", "").split(",")
    for p in raw_env:
        p_clean = p.strip().lower()
        if p_clean and p_clean not in all_phrases:
            all_phrases.append(p_clean)

    for p in ["metalhead","scrapbox","clanka","clanker","call", "assistant", "computer", "jarvis", "system", "hey", "yo"]:
        if p not in all_phrases:
            all_phrases.append(p)

    escaped = [re.escape(p) for p in all_phrases]
    combined = "|".join(escaped)

    pattern = re.compile(rf"\b(?:hey|hi|hello|ok|okay)?[\s,]*(?:{combined})\b", re.IGNORECASE)
    non_cmd = set(all_phrases) | {"hey", "hi", "hello", "ok", "okay", "please", "call"}
    return pattern, non_cmd


class WakeWordDetector:
    _instance: Optional["WakeWordDetector"] = None

    def __init__(
        self,
        on_wake: Optional[Callable[[], None]] = None,
        on_command: Optional[Callable[[str], None]] = None,
        on_interrupt: Optional[Callable[[], None]] = None,
    ):
        self.on_wake = on_wake
        self.on_command = on_command
        self.on_interrupt = on_interrupt
        self.is_running = False
        self.is_listening_active = False  # True during active execution/speech
        self._thread: Optional[threading.Thread] = None

        self.wake_pattern, self.non_command_words = compile_wake_patterns()

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
        on_interrupt: Optional[Callable[[], None]] = None,
    ) -> "WakeWordDetector":
        if cls._instance is None:
            cls._instance = cls(on_wake=on_wake, on_command=on_command, on_interrupt=on_interrupt)
        else:
            if on_wake:
                cls._instance.on_wake = on_wake
            if on_command:
                cls._instance.on_command = on_command
            if on_interrupt:
                cls._instance.on_interrupt = on_interrupt
        return cls._instance

    def reload_phrases(self):
        """Reload wake phrases from configuration or environment."""
        self.wake_pattern, self.non_command_words = compile_wake_patterns()

    def start(self):
        """Start always-on wake word and barge-in listener thread."""
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        print("[WakeWord] Always-on listener active. Say 'Call [command]' or custom phrase to trigger...")

    def stop(self):
        """Stop listening."""
        self.is_running = False

    def pause(self):
        """Enter execution mode (monitor for interruptions & new triggers)."""
        self.is_listening_active = True

    def resume(self):
        """Return to idle listening mode."""
        self.is_listening_active = False

    def _listen_loop(self):
        """Continuous audio stream loop monitoring for speech, keywords, and interruptions with auto-reconnect."""
        block_duration = 0.25  # 250ms chunks
        block_size = int(AUDIO_SAMPLE_RATE * block_duration)

        while self.is_running:
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
                        try:
                            data, overflowed = stream.read(block_size)
                        except Exception as read_err:
                            time.sleep(0.05)
                            continue

                        audio_chunk = data.flatten()
                        energy = float(np.sqrt(np.mean(audio_chunk**2)))

                        if energy > VAD_ENERGY_THRESHOLD:
                            is_in_speech = True
                            silence_count = 0
                            speech_buffer.append(audio_chunk)

                            # Max continuous buffer limit: 12 seconds in normal mode, 4 seconds in interrupt mode
                            max_chunks = 16 if self.is_listening_active else 48
                            if len(speech_buffer) >= max_chunks:
                                if self.is_listening_active:
                                    self._process_interruption(speech_buffer)
                                else:
                                    self._process_speech(speech_buffer)
                                speech_buffer = []
                                is_in_speech = False
                        else:
                            if is_in_speech:
                                silence_count += 1
                                speech_buffer.append(audio_chunk)
                                # ~0.5s silence during active execution to be snappier, ~1.0s during idle
                                limit_silence = 2 if self.is_listening_active else 4
                                if silence_count >= limit_silence:
                                    if self.is_listening_active:
                                        self._process_interruption(speech_buffer)
                                    else:
                                        self._process_speech(speech_buffer)
                                    speech_buffer = []
                                    is_in_speech = False
                                    silence_count = 0
                            else:
                                # Rolling pre-roll buffer (~500ms)
                                speech_buffer = speech_buffer[-1:] + [audio_chunk] if speech_buffer else [audio_chunk]

            except Exception as e:
                if self.is_running:
                    print(f"[WakeWord Stream Reconnecting] {e}", file=sys.stderr)
                    time.sleep(1.0)

    def _clean_command(self, raw_text: str) -> str:
        """Strip leading wake prefixes, leaving only the clean user command."""
        cleaned = self.wake_pattern.sub("", raw_text).strip()
        cleaned = re.sub(r"^(?:call|hey|hi|hello|please)?[\s,]+", "", cleaned, flags=re.IGNORECASE).strip()
        return cleaned.strip(".!? ")

    def _process_speech(self, chunks: List[np.ndarray]):
        """Transcribe speech clip on CUDA and check for single-pass wake word & command."""
        if not chunks or len(chunks) < 2:
            return

        full_clip = np.concatenate(chunks)
        if len(full_clip) < int(AUDIO_SAMPLE_RATE * 0.35):
            return

        try:
            segments, _ = self._fast_stt.transcribe(full_clip, beam_size=1)
            text = " ".join([s.text for s in segments]).strip()
            if not text:
                return

            text_lower = text.lower().strip()

            # 1. Instant Vocal Barge-In: "Stop", "Quiet", "Shut up", "Cancel"
            if re.search(INTERRUPT_KEYWORDS_REGEX, text_lower):
                print(f"[WakeWord] Interruption heard: '{text}'")
                request_interrupt(f"Voice: '{text}'")
                if self.on_interrupt:
                    self.on_interrupt()
                return

            # 2. Wake Word Detection (Matches 'call', 'assistant', 'computer', 'jarvis', etc.)
            match = self.wake_pattern.search(text_lower)
            if match:
                print(f"[WakeWord] Trigger heard: '{text}'")
                request_interrupt("New wake trigger")
                if self.on_interrupt:
                    self.on_interrupt()

                # Extract subsequent command from the same utterance
                raw_cmd = text[match.end():].strip().lstrip(",.!? ").strip()
                clean_cmd = self._clean_command(raw_cmd)

                is_real_command = bool(clean_cmd and clean_cmd.lower() not in self.non_command_words and len(clean_cmd) >= 3)

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

    def _process_interruption(self, chunks: List[np.ndarray]):
        """Transcribe audio during active execution to detect barge-in keywords or new wake triggers."""
        if not chunks or len(chunks) < 2:
            return

        full_clip = np.concatenate(chunks)
        if len(full_clip) < int(AUDIO_SAMPLE_RATE * 0.25):
            return

        try:
            segments, _ = self._fast_stt.transcribe(full_clip, beam_size=1)
            text = " ".join([s.text for s in segments]).strip()
            if not text:
                return

            text_lower = text.lower().strip()

            # 1. Check for explicit interrupt words
            if re.search(INTERRUPT_KEYWORDS_REGEX, text_lower):
                print(f"\n🛑 [WakeWord] Active interruption detected: '{text}'")
                request_interrupt(f"Voice barge-in: '{text}'")
                if self.on_interrupt:
                    self.on_interrupt()
                return

            # 2. Check if user spoke a new wake trigger or call command to preempt
            match = self.wake_pattern.search(text_lower)
            if match:
                print(f"\n⚡ [WakeWord] Preempting active task with new trigger: '{text}'")
                request_interrupt(f"Preempting with new trigger: '{text}'")
                if self.on_interrupt:
                    self.on_interrupt()

                raw_cmd = text[match.end():].strip().lstrip(",.!? ").strip()
                clean_cmd = self._clean_command(raw_cmd)

                is_real_command = bool(clean_cmd and clean_cmd.lower() not in self.non_command_words and len(clean_cmd) >= 3)
                if is_real_command and self.on_command:
                    self.on_command(clean_cmd)
                elif self.on_wake:
                    self.on_wake()

        except Exception:
            pass


def get_wake_word_detector(
    on_wake: Optional[Callable[[], None]] = None,
    on_command: Optional[Callable[[str], None]] = None,
    on_interrupt: Optional[Callable[[], None]] = None,
) -> WakeWordDetector:
    return WakeWordDetector.get_instance(on_wake=on_wake, on_command=on_command, on_interrupt=on_interrupt)
