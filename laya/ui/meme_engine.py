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

    def classify_reaction(self, query: str = "", response: str = "", is_error: bool = False) -> str:
        """
        Classify interaction context into an iconic meme reaction in <0.05ms:
        - 'gigachad': Absolute win, clean execution, organization, praise.
        - 'pepe': Witty comebacks, jokes, music, songs, chill vibe.
        - 'chudjak': Sarcasm, user complaining, 'why is it slow', deadpan reaction.
        - 'soyjak': Excited discovery, search results, mindblown.
        - 'monkas': High-risk system actions, warnings, sweating.
        - 'wojak': Melancholy, late night, existential questions.
        """
        if is_error:
            return "monkas"

        text = f"{query} {response}".lower()

        # 1. High-tension / Danger / Sweat
        if any(w in text for w in ["shutdown", "restart", "delete", "format", "kill", "warning", "blocked by safety", "critical"]):
            return "monkas"

        # 2. Chudjak: user complaints, "why", deadpan, sarcastic
        if any(w in text for w in ["why", "slow", "broken", "annoying", "stupid", "nothing ever happens", "billions must", "chud"]):
            return "chudjak"

        # 3. Soyjak: excited discovery, look at this, pointing, found files
        if any(w in text for w in ["found", "discovered", "check this out", "omg", "look at", "matches found"]):
            return "soyjak"

        # 4. Wojak: melancholy, late night, sad, lonely
        if any(w in text for w in ["tired", "sad", "lonely", "late night", "2 am", "3 am", "depressed", "sigh"]):
            return "wojak"

        # 5. Pepe: jokes, memes, music, spotify, songs, laughter, banter
        if any(w in text for w in ["joke", "meme", "laugh", "song", "music", "spotify", "pepe", "haha", "cool", "fun"]):
            return "pepe"

        # 6. Gigachad: default for successful commands, clean execution, organization
        if any(w in text for w in ["organized", "brought", "closed", "opened", "created", "volume", "ready", "done", "complete", "flawless", "thank"]):
            return "gigachad"

        return "gigachad"

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
