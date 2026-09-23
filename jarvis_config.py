"""
Jarvis Configuration & Constants (v5.0 Unified Architecture)
Single source of truth for paths, thresholds, and engine settings.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Base directories
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DOCUMENTS_DIR = Path.home() / "Documents" / "JarvisDocs"
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

SCREENSHOT_DIR = BASE_DIR / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

# Safety thresholds
DESTRUCTIVE_THRESHOLD = 0.70  # Commands scoring >= 0.70 are blocked for system safety

# System 1 Typed Decision Engine (Jev / Laya)
SYSTEM1_PROVIDER = os.getenv("JARVIS_SYSTEM1_PROVIDER", "auto")
TYPESAFE_API_KEY = os.getenv("TYPESAFE_API_KEY")

# System 2 Generative LLM Config
LLM_PROVIDER = os.getenv("JARVIS_LLM_PROVIDER", "auto")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Voice & Speech Settings
WAKE_WORDS = ["jarvis", "hey jarvis", "computer"]
WHISPER_MODEL = "base.en"       # Offline cached int8 CPU model (~200ms)
VOICE_SAMPLE_RATE = 16000
TTS_ENABLED = True
TTS_ENGINE = os.getenv("JARVIS_TTS_ENGINE", "sapi5")  # 'sapi5' (0ms offline) or 'edge'
TTS_RATE = 190                  # SAPI5 speaking rate (words per minute)
TTS_VOICE = "en-US-GuyNeural"   # Edge TTS voice if online
TTS_EDGE_RATE = "+10%"

# Windows Special Folder Mappings
SPECIAL_FOLDERS = {
    "downloads": "explorer.exe shell:Downloads",
    "download": "explorer.exe shell:Downloads",
    "documents": "explorer.exe shell:Personal",
    "desktop": "explorer.exe shell:Desktop",
    "pictures": "explorer.exe shell:My Pictures",
    "videos": "explorer.exe shell:My Video",
    "music": "explorer.exe shell:My Music",
}

# Web Shortcuts
WEB_SHORTCUTS = {
    "youtube": "https://www.youtube.com",
    "spotify": "start spotify",
    "github": "https://www.github.com",
    "google": "https://www.google.com",
    "reddit": "https://www.reddit.com",
    "chatgpt": "https://chatgpt.com",
}
