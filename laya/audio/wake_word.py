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

INTERRUPT_KEYWORDS_REGEX = r"^(?:(?:hey|hi|ok|please)\s+)?(?:stop(?:\s+(?:talking|it|that|now|please))?|shut\s*up|be\s+quiet|quiet|cancel(?:\s+(?:it|that))?|silence|halt|abort|freeze)$"


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
    filler_words = {
        "hey", "hi", "hello", "ok", "okay", "please", "call",
        "mm-hmm", "mmhmm", "mhm", "uh-huh", "uhhuh", "hmm", "um", "uh", "ah",
        "yeah", "yep", "yes", "sure", "alright", "so", "well", "like", "you know"
    }
    non_cmd = set(all_phrases) | filler_words
    return pattern, non_cmd


_compiled_pat, NON_COMMAND_WORDS = compile_wake_patterns()
WAKE_KEYWORDS_REGEX = _compiled_pat.pattern


def is_echo_of_assistant(user_text: str, assistant_text: str = "") -> bool:
    """Detect if transcribed text matches the assistant's own spoken response or known assistant output patterns."""
    if not user_text:
        return False
    u_low = user_text.lower().strip()
    u_clean = re.sub(r"[^\w\s]", "", u_low).strip()
    if not u_clean:
        return False

    # 1. Signature prefixes and phrases spoken exclusively by the assistant
    assistant_signatures = [
        "created folder", "created file", "the file is located", "the folder is located",
        "reminder set for", "timer set for", "from our history", "active contact set to",
        "listening for voice", "listening follow-up", "action blocked by safety",
        "fast path execution", "fast-path action", "could not find or open",
        "assistant is online", "dispatched whatsapp", "dispatched telegram",
        "cannot open", "unhandled path", "playing youtube", "opened application",
        "volume set to", "volume increased", "volume decreased", "audio muted",
        "task completed", "saved contact", "weather in", "it is currently",
        "battery is at", "cpu usage is", "ram usage is", "ip address is",
        "i have set a reminder", "i have created", "here is what i remember"
    ]
    for sig in assistant_signatures:
        if u_clean.startswith(sig) or sig in u_clean:
            return True

    # 2. Direct comparison with assistant's last spoken text
    if assistant_text:
        a_low = assistant_text.lower().strip()
        a_clean = re.sub(r"[^\w\s]", "", a_low).strip()
        if a_clean:
            # Substring containment
            if u_clean in a_clean or a_clean in u_clean:
                return True
            u_words = set(u_clean.split())
            a_words = set(a_clean.split())
            if u_words and a_words:
                overlap = len(u_words & a_words)
                # If 40% or more of user words overlap with assistant's speech
                if overlap / len(u_words) >= 0.4:
                    return True

    return False


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
        self.follow_up_until: float = 0.0  # Conversational follow-up window
        self.follow_up_settle_until: float = 0.0  # Acoustic settling blanking window
        self.last_assistant_speech: str = ""
        self._flush_buffer_flag: bool = False
        self._tts_engine = None
        self._thread: Optional[threading.Thread] = None

        self.wake_pattern, self.non_command_words = compile_wake_patterns()

        # Lightweight, lightning-fast streaming Whisper model on CUDA (tiny.en: ~15ms)
        try:
            self._fast_stt = WhisperModel("tiny.en", device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)
        except Exception:
            self._fast_stt = WhisperModel("tiny.en", device="cpu", compute_type="int8")

    def _get_tts(self):
        if self._tts_engine is None:
            try:
                from laya.audio.tts import get_tts_engine
                self._tts_engine = get_tts_engine()
            except Exception:
                pass
        return self._tts_engine

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

    def open_follow_up(self, duration_sec: float = 7.0, prompt_text: str = ""):
        """Open a conversational follow-up window where speech is accepted without wake phrases."""
        now = time.time()
        self.follow_up_settle_until = now + 0.45  # 450ms acoustic reverberation settling delay
        self.follow_up_until = now + duration_sec
        self._flush_buffer_flag = True
        if prompt_text:
            self.last_assistant_speech = prompt_text.strip()
        self.resume()
        print(f"[WakeWord] Follow-up listening window open for {duration_sec}s (acoustic guard: 450ms).")

    def is_in_follow_up(self) -> bool:
        """Check if currently within the conversational follow-up window."""
        return time.time() < self.follow_up_until

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

                        if self._flush_buffer_flag:
                            speech_buffer = []
                            is_in_speech = False
                            silence_count = 0
                            self._flush_buffer_flag = False

                        audio_chunk = data.flatten()
                        energy = float(np.sqrt(np.mean(audio_chunk**2)))

                        # Check if assistant is currently speaking or in acoustic settling guard
                        tts = self._get_tts()
                        tts_active = bool(tts and tts.is_speaking())
                        now = time.time()

                        if tts_active:
                            # Assistant is actively speaking through the speakers.
                            # Drop speech_buffer so Laya's output NEVER accumulates as a user command.
                            speech_buffer = []
                            is_in_speech = False
                            silence_count = 0

                            # Detect vocal barge-in ONLY if energy is loud enough to pierce through playback
                            if energy > (VAD_ENERGY_THRESHOLD * 2.2):
                                speech_buffer.append(audio_chunk)
                                if len(speech_buffer) >= 12:
                                    self._process_interruption(speech_buffer)
                                    speech_buffer = []
                            continue

                        if now < self.follow_up_settle_until:
                            # Acoustic reverberation guard right after assistant speech stops:
                            # Discard speaker room-echo and soundcard latency
                            speech_buffer = []
                            is_in_speech = False
                            silence_count = 0
                            continue

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
                                # ~0.5s trailing silence for ultra-low latency response
                                limit_silence = 2
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
                self.follow_up_until = 0.0
                request_interrupt(f"Voice: '{text}'")
                if self.on_interrupt:
                    self.on_interrupt()
                return

            # 2. Wake Word Detection (Matches 'call', 'assistant', 'computer', 'jarvis', etc.)
            match = self.wake_pattern.search(text_lower)
            if match:
                self.follow_up_until = 0.0
                print(f"[WakeWord] Trigger heard: '{text}'")
                request_interrupt("New wake trigger")
                if self.on_interrupt:
                    self.on_interrupt()

                # Extract subsequent command from the same utterance
                raw_cmd = text[match.end():].strip().lstrip(",.!? ").strip()
                clean_cmd = self._clean_command(raw_cmd)

                is_real_command = bool(clean_cmd and clean_cmd.lower() not in self.non_command_words and len(clean_cmd) >= 3)

                if is_real_command:
                    # Echo check even with wake word (in case assistant quoted a wake phrase)
                    if is_echo_of_assistant(clean_cmd, self.last_assistant_speech):
                        print(f"[WakeWord] Rejected wake-phrase self-echo from assistant speech: '{clean_cmd}'")
                        return
                    print(f"[WakeWord] Single-pass command executing: '{clean_cmd}'")
                    self.pause()
                    if self.on_command:
                        self.on_command(clean_cmd)
                else:
                    print(f"[WakeWord] Wake trigger activated, awaiting follow-up voice...")
                    self.pause()
                    if self.on_wake:
                        self.on_wake()
                return

            # 3. Conversational Follow-Up Mode: accept natural follow-ups without repeating wake word
            if time.time() < self.follow_up_until:
                clean_cmd = self._clean_command(text)

                # Rejection 1: Acoustic self-echo of assistant's own speech
                if is_echo_of_assistant(clean_cmd, self.last_assistant_speech):
                    print(f"[WakeWord] Rejected acoustic self-echo from assistant speech: '{clean_cmd}'")
                    return

                # Rejection 2: Conversational acknowledgments / noise words
                if clean_cmd.lower() in [
                    "yeah", "yes", "yep", "uh", "um", "ah", "okay", "ok", "so", "and", "the", "a",
                    "thanks", "thank you", "cool", "nice", "alright", "got it", "sure", "yup", "no", "nope"
                ]:
                    print(f"[WakeWord] Ignored conversational acknowledgment in follow-up: '{clean_cmd}'")
                    return

                is_real_command = bool(clean_cmd and clean_cmd.lower() not in self.non_command_words and len(clean_cmd) >= 3)
                if is_real_command:
                    print(f"[WakeWord] Follow-up command heard without wake word: '{clean_cmd}'")
                    self.follow_up_until = 0.0
                    self.pause()
                    if self.on_command:
                        self.on_command(clean_cmd)
                    return

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
