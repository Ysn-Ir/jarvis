"""
Laya Real-Time Meme Reaction Engine
Classifies user queries and assistant responses into iconic internet meme reactions:
Gigachad, Pepe the Frog, Chudjak, Soyjak, MonkaS, and Wojak (Feels Guy).
Loads local optimized assets for zero-latency HUD rendering.
"""

import os
from pathlib import Path
from typing import Optional, Tuple, Dict
from PIL import Image
import customtkinter as ctk

from laya.config import ROOT_DIR

MEMES_DIR = ROOT_DIR / "data" / "memes"


class MemeReactionEngine:
    _instance: Optional["MemeReactionEngine"] = None

    def __init__(self):
        self.memes_dir = MEMES_DIR
        self._cache: Dict[str, Image.Image] = {}
        self._load_local_assets()

    @classmethod
    def get_instance(cls) -> "MemeReactionEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_local_assets(self):
        """Pre-load local PNG meme images."""
        if not self.memes_dir.exists():
            return

        for p in self.memes_dir.glob("*.png"):
            name = p.stem.lower()
            try:
                img = Image.open(p).convert("RGBA")
                self._cache[name] = img
            except Exception:
                pass

    def classify_reaction(self, query: str = "", response: str = "", is_error: bool = False) -> Optional[str]:
        """
        Classify interaction context into an iconic meme reaction ONLY when warranted:
        - 'monkas': Dangerous commands, high-tension actions, panic, system safety alerts.
        - 'chudjak': Hot takes, user roasts, complaints, 'nothing ever happens', absurdity.
        - 'soyjak': Mindblown discoveries, meme hype, exaggerated excitement.
        - 'wojak': Melancholy, late night (3am), fatigue, existential pain.
        - 'gigachad': Wholesome praise, based moments, absolute wins, king/goat compliments.
        - 'pepe': Laughter, explicit meme/joke requests, music vibes.
        - None: Normal routine tasks (keeps HUD clean and distraction-free).
        """
        if is_error:
            return "monkas"

        text = f"{query} {response}".lower()

        # 1. Dangerous / Risky / Fatal / Panic -> MonkaS
        danger_signals = [
            "rm -rf", "format", "diskpart", "drop database", "killall",
            "shutdown", "restart computer", "reboot", "delete all", "wipe",
            "malware", "virus", "blocked by safety", "fatal", "critical error",
            "sweat", "scared", "monkas", "panic", "destroy", "system32"
        ]
        if any(w in text for w in danger_signals):
            return "monkas"

        # 2. Hot takes / Absurdity / Roasts / Chudjak
        hot_take_signals = [
            "hot take", "unpopular opinion", "nothing ever happens", "billions must",
            "chud", "chudjak", "javascript is better", "vim is trash", "python is slow",
            "who needs tests", "push to main", "earth is flat", "skill issue",
            "why is it slow", "so slow", "broken", "you suck", "are you dumb",
            "are you stupid", "annoying", "useless", "trash", "boring"
        ]
        if any(w in text for w in hot_take_signals):
            return "chudjak"

        # 3. Mindblown / Exaggerated Soy Hype -> Soyjak
        soy_signals = [
            "mind blown", "mindblown", "omg", "revolutionary", "this changes everything",
            "soyjak", "soy", "insane discovery", "holy shit", "look at this", "no way"
        ]
        if any(w in text for w in soy_signals):
            return "soyjak"

        # 4. Melancholy / Down Bad / 3 AM / Pain -> Wojak
        wojak_signals = [
            "3 am", "4 am", "haven't slept", "no sleep", "all nighter", "exhausted",
            "lonely", "sad", "depressed", "i miss her", "life is pain", "down bad",
            "feels bad", "feelsbadman", "wojak", "doomer", "why does everything suck",
            "i hate my life", "crying"
        ]
        if any(w in text for w in wojak_signals):
            return "wojak"

        # 5. Wholesome Praise / Based / Chad Victory -> GigaChad
        gigachad_signals = [
            "gigachad", "giga chad", "based", "you're the goat", "goat",
            "you are awesome", "i love you", "king", "legend", "absolute cinema",
            "we did it", "flawless", "promoted", "we won", "victory",
            "you saved my life", "thank you so much", "pure perfection", "proud of you"
        ]
        if any(w in text for w in gigachad_signals):
            return "gigachad"

        # 6. Jokes / Banter / Memes / Laughter / Vibes -> Pepe
        pepe_signals = [
            "haha", "hahaha", "lol", "lmao", "rofl", "kek",
            "tell me a joke", "tell a joke", "make me laugh", "joke",
            "tell me a meme", "show me a meme", "give me a meme", "share a meme",
            "pepe", "feels good man", "feelsgoodman", "suggest a song", "music vibe"
        ]
        if any(w in text for w in pepe_signals):
            return "pepe"

        # Default for normal, routine, focused tasks: NO MEME (clean HUD)
        return None

    def get_ctk_image(self, reaction_name: str, size: Tuple[int, int] = (64, 64)) -> Optional[ctk.CTkImage]:
        """Return a CTkImage for the given reaction name."""
        clean_name = reaction_name.lower().strip()
        pil_img = self._cache.get(clean_name)

        if not pil_img and self._cache:
            # Fallback to gigachad or first available
            pil_img = self._cache.get("gigachad") or next(iter(self._cache.values()))

        if pil_img:
            resized = pil_img.resize(size, Image.Resampling.LANCZOS)
            return ctk.CTkImage(light_image=resized, dark_image=resized, size=size)

        return None


def get_meme_engine() -> MemeReactionEngine:
    return MemeReactionEngine.get_instance()
