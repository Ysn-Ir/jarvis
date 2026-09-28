"""
Laya Real-Time Meme Reaction Engine
Classifies user queries and assistant responses into iconic internet meme reactions:
Foid Alert, Chud Destruct, Lockdown, Pepe the Frog, Chudjak, Soyjak, MonkaS, and Wojak.
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
        Classify interaction context into an iconic reaction ONLY when warranted:
        - 'foid_alert': Foid detection, cortisol alerts, emergency woman alert.
        - 'chud_destruct': User insults, chud takes, initiating self-destruction.
        - 'lockdown': Extreme lock-in mode, cortisol peak, rage focus.
        - 'monkas': Dangerous commands, high-tension actions, panic, system safety alerts.
        - 'soyjak': Mindblown discoveries, meme hype, exaggerated excitement.
        - 'wojak': Melancholy, late night (3am), fatigue, existential pain.
        - 'pepe': Laughter, explicit meme/joke requests, music vibes.
        - None: Normal routine tasks (keeps HUD clean and distraction-free).
        """
        if is_error:
            return "monkas"

        text = f"{query} {response}".lower()

        # 1. Foid Alert Mode (Emergency Siren + Red Light)
        foid_signals = [
            "foid", "foid nearby", "foid detected", "foid alert",
            "woman nearby", "girl nearby", "female detected", "females detected",
            "woman alert", "strike my cortisol", "spike my cortisol"
        ]
        if any(w in text for w in foid_signals):
            return "foid_alert"

        # 2. Chud Take & Insult Mode (chud image + alert)
        chud_signals = [
            # Direct insults
            "you suck", "you're stupid", "you are stupid", "you're dumb", "you are dumb",
            "you're useless", "you are useless", "you're garbage", "you are garbage",
            "you're trash", "you are trash", "you're pathetic", "you're terrible",
            "you're the worst", "you are the worst", "you're awful", "you're horrible",
            "you're an idiot", "you're a joke", "you're broken", "you're annoying",
            "shut up", "shut up idiot", "shut up moron", "shut up bot",
            "fuck you", "fuck off", "go fuck yourself",
            "you piece of shit", "piece of shit",
            # Standalone insults
            "dumbass", "dipshit", "jackass", "asshole", "bastard",
            "idiot", "moron", "imbecile", "halfwit", "dimwit", "nitwit", "braindead",
            "dumbfuck", "numbnuts",
            # Bot-specific
            "trash bot", "useless bot", "garbage bot", "terrible bot",
            "worst bot", "worst ai", "i hate you", "i hate this bot",
            # Meme/chud triggers
            "chud take", "chud mode", "chudjak", "nothing ever happens", "billions must",
            "chud take detected",
        ]
        if any(w in text for w in chud_signals):
            return "chud_destruct"

        # 3. Extreme Lockdown Mode (Cyber Alarm + Lock In)
        lockdown_signals = [
            "lock in", "lockdown mode", "extreme mode", "rage mode", "it's over",
            "lock down", "locking in", "hyper focus"
        ]
        if any(w in text for w in lockdown_signals):
            return "lockdown"

        # 4. Dangerous / Risky / Fatal / Panic -> MonkaS
        danger_signals = [
            "rm -rf", "format", "diskpart", "drop database", "killall",
            "shutdown", "restart computer", "reboot", "delete all", "wipe",
            "malware", "virus", "blocked by safety", "fatal", "critical error",
            "sweat", "scared", "monkas", "panic", "destroy", "system32"
        ]
        if any(w in text for w in danger_signals):
            return "monkas"

        # 5. Mindblown / Exaggerated Soy Hype -> Soyjak
        soy_signals = [
            "mind blown", "mindblown", "omg", "revolutionary", "this changes everything",
            "soyjak", "soy", "insane discovery", "holy shit", "look at this", "no way"
        ]
        if any(w in text for w in soy_signals):
            return "soyjak"

        # 6. Melancholy / Down Bad / 3 AM / Pain -> Wojak
        wojak_signals = [
            "3 am", "4 am", "haven't slept", "no sleep", "all nighter", "exhausted",
            "lonely", "sad", "depressed", "i miss her", "life is pain", "down bad",
            "feels bad", "feelsbadman", "wojak", "doomer", "why does everything suck",
            "i hate my life", "crying"
        ]
        if any(w in text for w in wojak_signals):
            return "wojak"

        # 7. Jokes / Banter / Memes / Laughter / Vibes -> Pepe
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
        # Map aliases to local PNG image assets
        alias_map = {
            "chud_destruct": "chudjak",
            "foid_alert": "monkas",
            "lockdown": "wojak",
        }
        target_asset = alias_map.get(clean_name, clean_name)
        pil_img = self._cache.get(target_asset)

        if not pil_img and self._cache:
            # Fallback to chudjak or first available asset
            pil_img = self._cache.get("chudjak") or next(iter(self._cache.values()))

        if pil_img:
            resized = pil_img.resize(size, Image.Resampling.LANCZOS)
            return ctk.CTkImage(light_image=resized, dark_image=resized, size=size)

        return None


def get_meme_engine() -> MemeReactionEngine:
    return MemeReactionEngine.get_instance()
