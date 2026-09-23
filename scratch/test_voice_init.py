import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jarvis_voice import JarvisVoice

t0 = time.perf_counter()
voice = JarvisVoice()
print(f"JarvisVoice initialized in {(time.perf_counter() - t0)*1000:.1f}ms")
print("Device:", voice.device_name)
print("Noise floor:", voice.noise_floor)
print("Speech threshold:", voice.speech_threshold)
print("TTS engine:", voice.tts.engine_type)
print("STT model loaded successfully!")
