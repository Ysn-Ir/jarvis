"""
Laya Procedural Meme Sound & Vocal Engine
Generates and plays iconic acoustic cues for meme reactions:
- GigaChad: Phonk sub-bass brass swell
- MonkaS: Dramatic suspense boom / shockwave
- Chudjak: Sarcastic descending brass slide ("womp womp")
- Pepe: Sparkly retro arpeggio chime ("feels good man")
- Soyjak: Cartoon spring/boing wobble
- Wojak: Melancholic ambient minor pad
"""

import os
import wave
import struct
import math
from pathlib import Path
from typing import Optional, Dict

import numpy as np
import pygame

from laya.config import ROOT_DIR

SOUNDS_DIR = ROOT_DIR / "data" / "sounds"
SAMPLE_RATE = 44100


def _generate_wavs_if_needed():
    SOUNDS_DIR.mkdir(parents=True, exist_ok=True)

    def write_wav(filename: str, audio_float: np.ndarray):
        p = SOUNDS_DIR / filename
        if p.exists() and p.stat().st_size > 500:
            return
        audio_int16 = (np.clip(audio_float, -1.0, 1.0) * 32767).astype(np.int16)
        with wave.open(str(p), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())

    # 1. GigaChad: Powerful Phonk sub-bass drop & brass punch (~1.2s)
    t = np.linspace(0, 1.2, int(SAMPLE_RATE * 1.2), endpoint=False)
    sub = np.sin(2 * np.pi * 55 * t) * np.exp(-2.5 * t)
    brass = (np.sin(2 * np.pi * 110 * t) + 0.5 * np.sin(2 * np.pi * 220 * t)) * np.exp(-3.0 * t)
    click = np.random.normal(0, 0.2, len(t)) * np.exp(-40.0 * t)
    gigachad_sound = 0.5 * sub + 0.4 * brass + 0.2 * click
    write_wav("gigachad.wav", gigachad_sound)

    # 2. MonkaS: Suspense low-end boom / dramatic drop (~1.0s)
    t = np.linspace(0, 1.0, int(SAMPLE_RATE * 1.0), endpoint=False)
    freq_sweep = np.linspace(160, 35, len(t))
    phase = 2 * np.pi * np.cumsum(freq_sweep) / SAMPLE_RATE
    boom = np.sin(phase) * np.exp(-3.5 * t)
    distortion = np.tanh(boom * 2.0)
    write_wav("monkas.wav", distortion * 0.7)

    # 3. Chudjak: Sarcastic descending "womp womp" slide (~1.2s)
    t1 = np.linspace(0, 0.5, int(SAMPLE_RATE * 0.5), endpoint=False)
    slide1 = np.sin(2 * np.pi * np.linspace(260, 180, len(t1)) * t1) * (1.0 - t1 / 0.5)
    t2 = np.linspace(0, 0.6, int(SAMPLE_RATE * 0.6), endpoint=False)
    slide2 = np.sin(2 * np.pi * np.linspace(220, 140, len(t2)) * t2) * (1.0 - t2 / 0.6)
    silence = np.zeros(int(SAMPLE_RATE * 0.1))
    chudjak_sound = np.concatenate([slide1, silence, slide2])
    write_wav("chudjak.wav", chudjak_sound * 0.5)

    # 4. Pepe: Cheerful retro 8-bit arpeggio chime (~0.9s)
    t_note = np.linspace(0, 0.25, int(SAMPLE_RATE * 0.25), endpoint=False)
    c5 = np.sin(2 * np.pi * 523.25 * t_note) * np.exp(-4 * t_note)
    e5 = np.sin(2 * np.pi * 659.25 * t_note) * np.exp(-4 * t_note)
    g5 = np.sin(2 * np.pi * 783.99 * t_note) * np.exp(-3 * t_note)
    c6 = np.sin(2 * np.pi * 1046.50 * t_note) * np.exp(-2.5 * t_note)
    pepe_sound = np.concatenate([c5, e5, g5, c6])
    write_wav("pepe.wav", pepe_sound * 0.4)

    # 5. Soyjak: High cartoon spring / boing wobble (~0.8s)
    t = np.linspace(0, 0.8, int(SAMPLE_RATE * 0.8), endpoint=False)
    modulator = np.sin(2 * np.pi * 20 * t) * 120
    carrier = np.sin(2 * np.pi * (500 + modulator) * t) * np.exp(-3.0 * t)
    write_wav("soyjak.wav", carrier * 0.45)

    # 6. Wojak: Melancholic soft minor ambient chord (~1.5s)
    t = np.linspace(0, 1.5, int(SAMPLE_RATE * 1.5), endpoint=False)
    d3 = np.sin(2 * np.pi * 146.83 * t)
    f3 = np.sin(2 * np.pi * 174.61 * t)
    a3 = np.sin(2 * np.pi * 220.00 * t)
    chord = (d3 + f3 + a3) / 3.0 * (1.0 - t / 1.5) ** 1.5
    write_wav("wojak.wav", chord * 0.4)


class MemeAudioManager:
    _instance: Optional["MemeAudioManager"] = None

    def __init__(self):
        self._sound_cache: Dict[str, pygame.mixer.Sound] = {}
        _generate_wavs_if_needed()
        self._init_mixer_and_load()

    @classmethod
    def get_instance(cls) -> "MemeAudioManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _init_mixer_and_load(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)
            for wav_file in SOUNDS_DIR.glob("*.wav"):
                name = wav_file.stem.lower()
                self._sound_cache[name] = pygame.mixer.Sound(str(wav_file))
        except Exception as e:
            print(f"[MemeAudio] Mixer init note: {e}")

    def play(self, meme_name: Optional[str]):
        """Play non-blocking sound cue for the given meme reaction."""
        if not meme_name:
            return
        clean_name = meme_name.lower().strip()
        sound = self._sound_cache.get(clean_name)
        if sound:
            try:
                sound.play()
            except Exception:
                pass


def play_meme_audio(meme_name: Optional[str]):
    MemeAudioManager.get_instance().play(meme_name)
