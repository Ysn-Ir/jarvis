"""
Laya Authentic Meme Music & Vocal Engine
Generates and plays authentic music riffs and vocal commentary for meme reactions:
- GigaChad: Drift Phonk beat (808 sub-bass + Phonk cowbell synth lead + drums)
- Pepe: Lo-Fi Chillhop music loop (Rhodes jazz 7th chords + vinyl beat)
- Chudjak: Sarcastic elevator jazz swing (walking bass + muted brass + rimshot)
- MonkaS: Cinematic tension soundtrack (heartbeat pulse + cello drone + suspense cluster)
- Wojak: Nostalgic synthwave ambient pad (analog synth chords + chorus)
- Soyjak: Bouncy jaunty ragtime piano stride jingle
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

VOICE_MEME_QUIPS = {
    "gigachad": "Absolute cinema. Pure GigaChad energy, sir. ",
    "monkas": "MonkaS... Sweating intensely over here. ",
    "chudjak": "Chudjak take detected. Nothing ever happens, sir. ",
    "wojak": "Feels bad man. Real Wojak 3 AM hours. ",
    "soyjak": "Holy soy! Pointing at the screen in pure excitement. ",
    "pepe": "Feels good man. Pepe approved. ",
}


def _generate_music_wavs():
    SOUNDS_DIR.mkdir(parents=True, exist_ok=True)

    def write_wav(filename: str, audio_float: np.ndarray):
        p = SOUNDS_DIR / filename
        if p.exists() and p.stat().st_size > 50000:
            return  # Authentic downloaded song already present
        audio_int16 = (np.clip(audio_float, -1.0, 1.0) * 32767).astype(np.int16)
        with wave.open(str(p), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())

    # 1. GigaChad: Authentic Drift Phonk Music Beat (~2.4s)
    dur_g = 2.4
    t_g = np.linspace(0, dur_g, int(SAMPLE_RATE * dur_g), endpoint=False)
    beat_g = 60.0 / 135.0  # 135 BPM
    bpm_t_g = t_g % beat_g

    # Phonk 808 kick on beat, punchy snare on offbeat
    kick = np.sin(2 * np.pi * 55 * np.exp(-18 * bpm_t_g)) * np.exp(-9 * bpm_t_g)
    snare = np.random.normal(0, 0.28, len(t_g)) * np.exp(-14 * ((t_g - beat_g * 0.5) % beat_g))
    hihat = np.random.normal(0, 0.12, len(t_g)) * np.exp(-25 * (t_g % (beat_g * 0.25)))

    # Phonk Cowbell Lead: F5 (698), G#5 (830), C6 (1046), A#5 (932)
    cowbell_melody = np.zeros_like(t_g)
    notes_g = [698.46, 830.61, 1046.50, 932.33, 830.61, 698.46]
    step_g = beat_g / 2.0
    for i, freq in enumerate(notes_g * 2):
        st = i * step_g
        if st + step_g > dur_g:
            break
        idx = (t_g >= st) & (t_g < st + step_g)
        nt = t_g[idx] - st
        # Characteristic metallic harmonics of Phonk cowbell
        cb = (np.sin(2*np.pi*freq*nt) + 0.65*np.sin(2*np.pi*freq*1.48*nt) + 0.3*np.sin(2*np.pi*freq*2.2*nt)) * np.exp(-11*nt)
        cowbell_melody[idx] = cb

    # 808 Distorted Sub-Bass Glide
    bass_g = np.sin(2 * np.pi * 46 * (1.0 - 0.08 * t_g) * t_g) * np.exp(-0.8 * t_g)
    bass_g = np.tanh(bass_g * 2.0) * 0.4

    phonk_mix = 0.38 * kick + 0.25 * snare + 0.15 * hihat + 0.40 * cowbell_melody + 0.35 * bass_g
    write_wav("gigachad.wav", phonk_mix * (1.0 - (t_g / dur_g) ** 4))

    # 2. Pepe: Warm Lo-Fi Chillhop Chord Groove (~2.6s)
    dur_p = 2.6
    t_p = np.linspace(0, dur_p, int(SAMPLE_RATE * dur_p), endpoint=False)
    # Vinyl dust layer
    vinyl = np.random.normal(0, 0.03, len(t_p)) * (np.random.random(len(t_p)) > 0.98)

    # Rhodes Electric Piano Chords (Dm7 -> G7 -> Cmaj7)
    rhodes = np.zeros_like(t_p)
    chords_p = [
        ([293.66, 349.23, 440.00, 523.25], 0.0, 0.9),   # Dm7
        ([196.00, 246.94, 293.66, 349.23], 0.9, 1.8),   # G7
        ([261.63, 329.63, 392.00, 493.88], 1.8, 2.6),   # Cmaj7
    ]
    for chord_freqs, c_start, c_end in chords_p:
        idx = (t_p >= c_start) & (t_p < c_end)
        ct = t_p[idx] - c_start
        chord_sig = np.zeros(len(ct))
        for f in chord_freqs:
            # Warm electric piano timbre with tremolo
            tremolo = 1.0 + 0.15 * np.sin(2 * np.pi * 5 * ct)
            chord_sig += (np.sin(2 * np.pi * f * ct) + 0.3 * np.sin(2 * np.pi * f * 2 * ct)) * tremolo * np.exp(-1.5 * ct)
        rhodes[idx] = chord_sig / len(chord_freqs)

    # Chillhop boom-bap kick and rimshot
    beat_p = 60.0 / 84.0  # 84 BPM
    kick_p = np.sin(2 * np.pi * 60 * np.exp(-12 * (t_p % beat_p))) * np.exp(-6 * (t_p % beat_p)) * 0.3
    rim_p = np.sin(2 * np.pi * 880 * ((t_p - beat_p*0.5) % beat_p)) * np.exp(-30 * ((t_p - beat_p*0.5) % beat_p)) * 0.25

    lofi_mix = 0.55 * rhodes + 0.25 * kick_p + 0.18 * rim_p + 0.08 * vinyl
    write_wav("pepe.wav", lofi_mix * (1.0 - (t_p / dur_p) ** 3))

    # 3. Chudjak: Sarcastic Elevator Jazz Swing (~2.2s)
    dur_c = 2.2
    t_c = np.linspace(0, dur_c, int(SAMPLE_RATE * dur_c), endpoint=False)
    # Walking double-bass descending line
    bass_notes = [174.61, 164.81, 155.56, 146.83] # F3 -> E3 -> Eb3 -> D3
    step_c = dur_c / 4.0
    jazz_bass = np.zeros_like(t_c)
    for i, bf in enumerate(bass_notes):
        st = i * step_c
        idx = (t_c >= st) & (t_c < st + step_c)
        bt = t_c[idx] - st
        jazz_bass[idx] = np.sin(2 * np.pi * bf * bt) * np.exp(-3.5 * bt)

    # Sarcastic muted trumpet slide at end
    idx_end = t_c >= 1.2
    te = t_c[idx_end] - 1.2
    slide_freq = np.linspace(350, 210, len(te))
    trumpet = np.sin(2 * np.pi * slide_freq * te) * (1.0 + 0.5 * np.sin(2*np.pi*slide_freq*2*te)) * (1.0 - te/1.0) * 0.4
    chud_mix = np.zeros_like(t_c)
    chud_mix += 0.5 * jazz_bass
    chud_mix[idx_end] += trumpet
    write_wav("chudjak.wav", chud_mix)

    # 4. MonkaS: Cinematic Suspense Soundtrack (~2.4s)
    dur_m = 2.4
    t_m = np.linspace(0, dur_m, int(SAMPLE_RATE * dur_m), endpoint=False)
    # Heavy cinematic heartbeat (thump-thump)
    hb_time = t_m % 0.8
    hb1 = np.sin(2 * np.pi * 48 * np.exp(-15 * hb_time)) * np.exp(-8 * hb_time)
    hb2 = np.sin(2 * np.pi * 44 * np.exp(-15 * ((hb_time - 0.2) % 0.8))) * np.exp(-8 * ((hb_time - 0.2) % 0.8))
    heartbeat = 0.5 * hb1 + 0.4 * hb2

    # Low dark cello drone
    drone = (np.sin(2 * np.pi * 65.4 * t_m) + 0.4 * np.sin(2 * np.pi * 130.8 * t_m)) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.5 * t_m))

    # Dissonant suspense string cluster
    tension_cluster = (np.sin(2 * np.pi * 880 * t_m) + np.sin(2 * np.pi * 932 * t_m)) * (t_m / dur_m) * 0.15

    # Cinematic sub-bass impact drop
    impact_t = np.clip(t_m, 0, 1.2)
    impact = np.sin(2 * np.pi * np.linspace(120, 32, len(impact_t)) * impact_t) * np.exp(-2.5 * impact_t) * 0.5
    monkas_mix = 0.4 * heartbeat + 0.3 * drone + tension_cluster + 0.4 * impact
    write_wav("monkas.wav", np.tanh(monkas_mix * 1.5) * 0.8)

    # 5. Wojak: Nostalgic Synthwave Night Drive Pad (~2.8s)
    dur_w = 2.8
    t_w = np.linspace(0, dur_w, int(SAMPLE_RATE * dur_w), endpoint=False)
    # Analog Synth Chorus Pad (D minor -> Bb major)
    pad = np.zeros_like(t_w)
    mid = dur_w / 2.0
    # D minor (D3, F3, A3)
    idx1 = t_w < mid
    t1 = t_w[idx1]
    pad1 = (np.sin(2*np.pi*146.83*t1) + np.sin(2*np.pi*174.61*t1) + np.sin(2*np.pi*220.0*t1)) / 3.0
    # Detuned chorus layer
    pad1 += 0.5 * (np.sin(2*np.pi*147.5*t1) + np.sin(2*np.pi*175.2*t1) + np.sin(2*np.pi*221.0*t1)) / 3.0
    pad[idx1] = pad1 * np.sin(np.pi * t1 / mid)

    # Bb major (Bb2, D3, F3)
    idx2 = t_w >= mid
    t2 = t_w[idx2] - mid
    pad2 = (np.sin(2*np.pi*116.54*t2) + np.sin(2*np.pi*146.83*t2) + np.sin(2*np.pi*174.61*t2)) / 3.0
    pad2 += 0.5 * (np.sin(2*np.pi*117.2*t2) + np.sin(2*np.pi*147.5*t2) + np.sin(2*np.pi*175.2*t2)) / 3.0
    pad[idx2] = pad2 * np.sin(np.pi * t2 / mid)

    wojak_mix = 0.65 * pad * (1.0 - (t_w / dur_w) ** 2)
    write_wav("wojak.wav", wojak_mix)

    # 6. Soyjak: Bouncy Ragtime Piano Stride (~2.0s)
    dur_s = 2.0
    t_s = np.linspace(0, dur_s, int(SAMPLE_RATE * dur_s), endpoint=False)
    step_s = 0.25
    ragtime = np.zeros_like(t_s)
    melody_s = [523.25, 587.33, 659.25, 783.99, 880.00, 1046.50, 783.99, 1046.50]
    for i, sf in enumerate(melody_s):
        st = i * step_s
        if st + step_s > dur_s:
            break
        idx = (t_s >= st) & (t_s < st + step_s)
        st_t = t_s[idx] - st
        note = (np.sin(2*np.pi*sf*st_t) + 0.4*np.sin(2*np.pi*sf*2*st_t)) * np.exp(-9 * st_t)
        ragtime[idx] = note

    clap = np.random.normal(0, 0.2, len(t_s)) * np.exp(-20 * (t_s % 0.5))
    soy_mix = 0.55 * ragtime + 0.25 * clap
    write_wav("soyjak.wav", soy_mix * (1.0 - (t_s / dur_s) ** 3))


class MemeAudioManager:
    _instance: Optional["MemeAudioManager"] = None

    def __init__(self):
        self._sound_cache: Dict[str, pygame.mixer.Sound] = {}
        _generate_music_wavs()
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
        """Play non-blocking music riff for the given meme reaction."""
        if not meme_name:
            return
        clean_name = meme_name.lower().strip()
        sound = self._sound_cache.get(clean_name)
        if sound:
            try:
                sound.play()
            except Exception:
                pass

    def get_voice_quip(self, meme_name: Optional[str]) -> str:
        """Return Jarvis's vocal meme commentary prefix."""
        if not meme_name:
            return ""
        clean = meme_name.lower().strip()
        return VOICE_MEME_QUIPS.get(clean, "")


def play_meme_audio(meme_name: Optional[str]):
    MemeAudioManager.get_instance().play(meme_name)

def get_meme_voice_quip(meme_name: Optional[str]) -> str:
    return MemeAudioManager.get_instance().get_voice_quip(meme_name)
