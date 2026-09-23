"""
Laya Configuration & System Settings
"""

import os
from pathlib import Path
import torch
import dotenv

# Base Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
dotenv.load_dotenv(ROOT_DIR / ".env")

DOCS_DIR = Path.home() / "Documents" / "LayaDocs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_DB_PATH = DATA_DIR / "laya_memory.db"

# LLM Providers (Dual-Backend: Cloud Ultra-Fast Groq + Local Private Ollama)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# Default to ultra-fast qwen3.8-27b for sub-second tool turns; gpt-oss-120b for heavy fallback
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
GROQ_FALLBACK_MODEL = os.getenv("GROQ_FALLBACK_MODEL", "openai/gpt-oss-120b")
GROQ_TIMEOUT_SEC = 40.0

OLLAMA_BASE_URL = "http://localhost:11434/v1"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:7b")
OLLAMA_TIMEOUT_SEC = 40.0


# Audio Pipeline Settings
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_BLOCK_SIZE = 1024

# Voice Activity Detection (VAD) Settings
# 1.6s of trailing silence allows natural human speech pauses without cutting off
VAD_ENERGY_THRESHOLD = 0.005       # Speech onset sensitivity
VAD_SILENCE_LIMIT_SEC = 1.6        # Generous silence window before finalizing speech
VAD_MIN_SPEECH_SEC = 0.30         # Minimum speech length to avoid noise spikes

# Speech-to-Text (STT) Settings
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "small.en")
WHISPER_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
WHISPER_COMPUTE_TYPE = "float16" if torch.cuda.is_available() else "int8"

# Text-to-Speech (TTS) Settings
TTS_ENGINE = os.getenv("TTS_ENGINE", "edge-tts")      # "edge-tts" (Neural JARVIS) with "sapi5" fallback
EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "en-US-ChristopherNeural")  # Neural JARVIS voice
TTS_RATE = 190                    # Conversational speaking rate (words/min)
TTS_VOLUME = 1.0

# Latency Budgets (ms)
FAST_PATH_BUDGET_MS = 300.0

# Application Mappings
APP_REGISTRY = {
    "spotify": "spotify",
    "chrome": "chrome",
    "google chrome": "chrome",
    "browser": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "word": "winword",
    "microsoft word": "winword",
    "excel": "excel",
    "microsoft excel": "excel",
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "settings": "ms-settings:",
    "whatsapp": "whatsapp",
    "discord": "discord",
    "terminal": "wt",
    "cmd": "cmd",
    "powershell": "powershell",
    "explorer": "explorer",
}

# Special Windows Folders
FOLDER_ALIASES = {
    "downloads": str(Path.home() / "Downloads"),
    "documents": str(Path.home() / "Documents"),
    "desktop": str(Path.home() / "Desktop"),
    "pictures": str(Path.home() / "Pictures"),
    "music": str(Path.home() / "Music"),
    "videos": str(Path.home() / "Videos"),
    "layadocs": str(DOCS_DIR),
}

# Safety & Permission Tiers
GREEN_ACTIONS = [
    "volume_up", "volume_down", "set_volume", "mute",
    "play_media", "pause_media", "next_track", "prev_track",
    "check_battery", "check_ram", "check_cpu", "check_ip",
    "open_app", "open_folder", "create_document", "create_note", "create_sheet",
    "web_search", "query_time", "query_date", "query_memory",
]

YELLOW_ACTIONS = [
    "send_email", "send_whatsapp", "create_calendar_event",
    "modify_system_setting", "delete_user_file",
]

RED_ACTIONS = [
    "shutdown_system", "restart_system", "format_disk",
    "delete_system_directory", "kill_critical_process",
]
