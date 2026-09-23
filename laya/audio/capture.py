"""
Laya Real-Time Audio Capture with Dynamic VAD
Uses sounddevice with real-time adaptive noise-floor VAD.
"""

import time
import numpy as np
import sounddevice as sd
from typing import Optional, Callable

from laya.config import (
    AUDIO_SAMPLE_RATE,
    AUDIO_CHANNELS,
    AUDIO_BLOCK_SIZE,
    VAD_ENERGY_THRESHOLD,
    VAD_SILENCE_LIMIT_SEC,
    VAD_MIN_SPEECH_SEC,
)


class AudioCapture:
    def __init__(
        self,
        sample_rate: int = AUDIO_SAMPLE_RATE,
        channels: int = AUDIO_CHANNELS,
        block_size: int = AUDIO_BLOCK_SIZE,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.block_size = block_size
        self.noise_floor = 0.003

    def record_until_silence(
        self,
        max_duration_sec: float = 15.0,
        energy_threshold: float = VAD_ENERGY_THRESHOLD,
        silence_limit_sec: float = VAD_SILENCE_LIMIT_SEC,
        on_speech_detected: Optional[Callable[[], None]] = None,
    ) -> Optional[np.ndarray]:
        """
        Record audio dynamically until speech ends using real-time adaptive VAD.
        Returns float32 1D numpy array normalized between [-1.0, 1.0].
        """
        recorded_chunks = []
        is_speaking = False
        silence_start_time = None
        speech_start_time = None
        start_time = time.time()

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            blocksize=self.block_size,
            dtype="float32",
        ) as stream:
            while True:
                # Max duration check
                if time.time() - start_time > max_duration_sec:
                    break

                chunk, overflowed = stream.read(self.block_size)
                flat_chunk = chunk.flatten()
                rms = float(np.sqrt(np.mean(flat_chunk**2)))

                # Update adaptive noise floor
                self.noise_floor = 0.98 * self.noise_floor + 0.02 * rms
                adaptive_threshold = max(energy_threshold, self.noise_floor * 2.0)

                if rms > adaptive_threshold:
                    if not is_speaking:
                        is_speaking = True
                        speech_start_time = time.time()
                        if on_speech_detected:
                            on_speech_detected()
                    recorded_chunks.append(flat_chunk)
                    silence_start_time = None
                else:
                    if is_speaking:
                        recorded_chunks.append(flat_chunk)
                        if silence_start_time is None:
                            silence_start_time = time.time()
                        elif time.time() - silence_start_time >= silence_limit_sec:
                            # Speech finished
                            break
                    else:
                        # Keep a small rolling buffer of pre-speech chunks (last 4 chunks = ~250ms)
                        recorded_chunks.append(flat_chunk)
                        if len(recorded_chunks) > 4:
                            recorded_chunks.pop(0)

        if not is_speaking or not recorded_chunks:
            return None

        # Check minimum speech length
        speech_duration = time.time() - (speech_start_time or start_time)
        if speech_duration < VAD_MIN_SPEECH_SEC:
            return None

        audio_data = np.concatenate(recorded_chunks, axis=0)
        return audio_data


if __name__ == "__main__":
    print("[AudioCapture] Testing dynamic VAD. Speak now...")
    capture = AudioCapture()
    audio = capture.record_until_silence(max_duration_sec=6.0)
    if audio is not None:
        print(f"[AudioCapture] Captured {len(audio)/16000:.2f}s of audio successfully!")
    else:
        print("[AudioCapture] No speech detected.")
