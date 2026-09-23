"""
Laya High-Speed Local STT Engine
Uses faster-whisper with GPU CUDA float16 or CPU int8 acceleration.
"""

import sys
import threading
import time
import numpy as np
from typing import Optional
from faster_whisper import WhisperModel

from laya.config import (
    WHISPER_MODEL_NAME,
    WHISPER_DEVICE,
    WHISPER_COMPUTE_TYPE,
)


class STTEngine:
    _instance: Optional["STTEngine"] = None
    _lock = threading.Lock()

    def __init__(
        self,
        model_name: str = WHISPER_MODEL_NAME,
        device: str = WHISPER_DEVICE,
        compute_type: str = WHISPER_COMPUTE_TYPE,
    ):
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.model: Optional[WhisperModel] = None
        self._init_model()

    def _init_model(self):
        try:
            print(f"[STT] Loading faster-whisper ({self.model_name}) on {self.device} ({self.compute_type})...")
            t0 = time.time()
            self.model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
            print(f"[STT] Model loaded successfully in {(time.time() - t0)*1000:.1f}ms")
        except Exception as e:
            print(f"[STT Warning] Failed loading on {self.device} ({e}). Falling back to CPU int8...", file=sys.stderr)
            try:
                self.device = "cpu"
                self.compute_type = "int8"
                self.model = WhisperModel(
                    self.model_name,
                    device="cpu",
                    compute_type="int8",
                )
                print("[STT] CPU fallback model loaded successfully.")
            except Exception as ex:
                print(f"[STT Error] Fatal error loading Whisper model: {ex}", file=sys.stderr)
                self.model = None

    @classmethod
    def get_instance(cls) -> "STTEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def transcribe(self, audio_data: np.ndarray) -> str:
        """
        Transcribe normalized 1D float32 audio numpy array at 16kHz.
        Returns transcribed text string.
        """
        if self.model is None or audio_data is None or len(audio_data) == 0:
            return ""

        try:
            # Low latency inference: beam_size=1, condition_on_previous_text=False
            segments, info = self.model.transcribe(
                audio_data,
                beam_size=1,
                temperature=0.0,
                language="en",
                condition_on_previous_text=False,
                vad_filter=False, # We already ran dynamic VAD on input
            )
            text_parts = [segment.text.strip() for segment in segments]
            result = " ".join(text_parts).strip()
            return result
        except Exception as e:
            print(f"[STT Error] Transcription failed: {e}", file=sys.stderr)
            return ""


def get_stt_engine() -> STTEngine:
    return STTEngine.get_instance()


if __name__ == "__main__":
    stt = get_stt_engine()
    # Test with 1 second of silence
    dummy = np.zeros(16000, dtype=np.float32)
    print("Testing dummy transcription:", stt.transcribe(dummy))
