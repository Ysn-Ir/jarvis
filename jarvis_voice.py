import io
import os
import re
import sys
import time
import numpy as np
import scipy.signal
import sounddevice as sd
from faster_whisper import WhisperModel

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from jarvis_config import (
    WHISPER_MODEL,
    TTS_ENABLED,
    TTS_VOICE,
    TTS_EDGE_RATE,
)
from jarvis_tts import JarvisTTS
from jarvis_controller import JarvisController


class JarvisVoice:
    """High-fidelity voice interface for Jarvis assistant."""

    def __init__(self, controller: JarvisController = None):
        self.controller = controller or JarvisController(preload=False)
        
        # 1. Detect hardware native input sample rate
        dev = sd.query_devices(kind="input")
        self.device_name = dev["name"]
        self.hw_rate = int(dev.get("default_samplerate", 44100))
        print(f"🎤 [Audio] Detected Input: {self.device_name} @ {self.hw_rate}Hz")

        # 2. Initialize Text-to-Speech (Microsoft Edge Neural Voice)
        print("🔊 [Audio] Initializing Edge Neural Text-to-Speech...")
        self.tts = JarvisTTS(voice=TTS_VOICE, rate=TTS_EDGE_RATE)

        # 3. Initialize offline Whisper model
        print(f"🎙️ [STT] Loading offline Whisper model ('{WHISPER_MODEL}')...")
        self.stt_model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")

        # 4. Calibrate ambient room noise
        self.noise_floor = 0.002
        self.speech_threshold = 0.005
        self.calibrate_ambient()
        print("✅ Jarvis Voice Engine Ready!\n")

    def calibrate_ambient(self, duration: float = 0.5):
        """Measures ambient room noise to set dynamic speech threshold."""
        try:
            samples = int(duration * self.hw_rate)
            rec = sd.rec(samples, samplerate=self.hw_rate, channels=1, dtype="float32")
            sd.wait()
            rms = float(np.sqrt(np.mean(rec**2)))
            self.noise_floor = max(rms, 0.0005)
            # Sensitive trigger calibrated for laptop and headset mics
            self.speech_threshold = max(self.noise_floor * 1.35, 0.0018)
            print(f"📊 [Calibration] Noise floor: {self.noise_floor:.5f} | Trigger: {self.speech_threshold:.5f}")
        except Exception as e:
            self.noise_floor = 0.001
            self.speech_threshold = 0.002

    def speak(self, text: str, full: bool = False):
        """Speaks a response using Local SAPI5 or Edge TTS."""
        if not TTS_ENABLED or not self.tts or not text:
            return
        self.tts.speak(text, full=full)

    def record_until_silence(self, max_duration: float = 7.0, silence_limit: float = 0.8) -> np.ndarray:
        """
        Records at native hardware rate, showing a live VU volume meter.
        Auto-stops when speech ends.
        """
        chunk_size = int(self.hw_rate * 0.12)  # 120ms chunks
        chunks = []
        silence_chunks = 0
        max_silence_chunks = int(silence_limit / 0.12)
        has_spoken = False

        print("\n🎙️ [LISTENING] Speak your command now:")

        start_time = time.time()
        with sd.InputStream(samplerate=self.hw_rate, channels=1, dtype="float32") as stream:
            while (time.time() - start_time) < max_duration:
                chunk, _ = stream.read(chunk_size)
                rms = float(np.sqrt(np.mean(chunk**2)))
                chunks.append(chunk.flatten())

                # Live VU Volume Meter
                meter_level = min(int(rms * 1500), 20)
                meter_bar = "█" * meter_level + "░" * (20 - meter_level)
                state_label = "SPEAKING" if has_spoken else "WAITING"
                sys.stdout.write(f"\r   [{meter_bar}] {state_label} (Vol: {rms*1000:.1f})")
                sys.stdout.flush()

                # Dynamic Voice Activity Detection
                if rms > self.speech_threshold:
                    has_spoken = True
                    silence_chunks = 0
                elif has_spoken:
                    silence_chunks += 1
                    if silence_chunks >= max_silence_chunks:
                        break  # Finished speaking

        sys.stdout.write("\r" + " " * 60 + "\r")
        sys.stdout.flush()

        if not chunks:
            return np.array([], dtype="float32")

        raw_audio = np.concatenate(chunks)
        peak = float(np.max(np.abs(raw_audio)))

        # If audio has detectable energy above baseline, process even if VAD threshold was borderline
        if peak < 0.002 and not has_spoken:
            return np.array([], dtype="float32")

        # 1. Peak Normalization (Boosts quiet microphone inputs)
        if peak > 1e-5:
            normalized_audio = (raw_audio / peak) * 0.95
        else:
            normalized_audio = raw_audio

        # 2. Resample from hardware native rate (e.g. 44.1kHz) to 16kHz for Whisper
        if self.hw_rate != 16000:
            target_length = int(len(normalized_audio) * 16000 / self.hw_rate)
            audio_16k = scipy.signal.resample(normalized_audio, target_length).astype(np.float32)
        else:
            audio_16k = normalized_audio.astype(np.float32)

        return audio_16k

    def transcribe(self, audio_data: np.ndarray) -> str:
        """Transcribes 16kHz audio array using faster-whisper."""
        if len(audio_data) < 16000 * 0.4:
            return ""

        segments, _ = self.stt_model.transcribe(
            audio_data,
            beam_size=1,
            language="en",
            vad_filter=True,
            initial_prompt="Volume up, pause music, open Discord, launch app, search, what is."
        )
        text = " ".join([s.text for s in segments]).strip()
        return text

    def process_voice_command(self, query: str):
        """Processes query through JarvisController and provides voice feedback."""
        if not query:
            return

        # Strip leading wake words ("jarvis, ", "hey jarvis, ", etc.)
        clean_query = re.sub(
            r"^(?:(?:hey|hi|hello|ok|okay)?\s*(?:jarvis|computer|assistant)[,:\s]*)+",
            "",
            query.strip(),
            flags=re.IGNORECASE
        ).strip()
        # If user only said "jarvis", prompt them
        if not clean_query:
            clean_query = query.strip()

        print(f"\n[You]: \"{query}\"")
        if clean_query != query:
            print(f"[Parsed Command]: \"{clean_query}\"")
        res = self.controller.process(clean_query)

        routing_time = res.get('routing_ms', res.get('latency_ms', 0.0))
        total_time = res.get('total_latency_ms', 0.0)
        print(f"[Status]: [{res['status']}] {res['message'][:120]}")
        print(f"[Timing]: Router={routing_time:.1f}ms | Total={total_time:.1f}ms")

        if res["status"] == "BLOCKED_SAFETY":
            self.speak("Action was blocked for safety.")
        else:
            self.speak(res.get("message", "Done."))

    def run_push_to_talk(self):
        """Interactive Push-to-Talk Voice Loop."""
        print("=" * 65)
        print("🎙️ JARVIS 3.0 VOICE CONTROLLER (HIGH-FIDELITY AUDIO)")
        print("=" * 65)
        print("   • Press [Enter] to start speaking.")
        print("   • Speak: 'Turn volume up', 'Open Discord', 'What is my IP?', 'Open Downloads'")
        print("   • Type 'exit' to quit.")
        print("=" * 65)

        while True:
            try:
                cmd = input("\n[Press Enter to Speak, or type command] > ").strip()
                if cmd.lower() in ("exit", "quit", "q"):
                    self.speak("Goodbye!")
                    break

                if cmd:
                    # User typed command directly
                    self.process_voice_command(cmd)
                else:
                    # Record voice with live VU meter
                    audio = self.record_until_silence(max_duration=7.0, silence_limit=0.8)
                    if len(audio) == 0:
                        print("⚠️ No speech detected. Please speak closer to the mic.")
                        continue

                    t_start = time.perf_counter()
                    transcription = self.transcribe(audio)
                    stt_time = (time.perf_counter() - t_start) * 1000

                    if not transcription:
                        print("⚠️ Could not recognize speech. Please try again.")
                        continue

                    print(f"📝 Transcribed in {stt_time:.1f}ms: \"{transcription}\"")
                    self.process_voice_command(transcription)

            except (KeyboardInterrupt, EOFError):
                self.speak("Jarvis shutting down.")
                break


if __name__ == "__main__":
    assistant = JarvisVoice()
    assistant.run_push_to_talk()
