"""
Laya Runtime Configuration, Credentials, Model Switching & Audit Logging Manager
Provides hot-swappable runtime control over:
- Local LLM execution (Ollama Mistral / DeepSeek-R1) with auto-daemon launch
- External API keys & endpoints (OpenAI, Groq, OpenRouter, Mistral AI, Gemini, Custom)
- Live platform credentials (Gmail, Telegram, Discord, Instagram)
- Persistent browser session directory for logged-in social accounts
- Thread-safe structured audit logging (~/.laya/laya_runtime.log + live UI stream)
"""

import os
import json
import time
import socket
import subprocess
import threading
from collections import deque
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

try:
    import dotenv
    _root_env = Path(__file__).resolve().parent.parent / ".env"
    if _root_env.exists():
        dotenv.load_dotenv(_root_env, override=False)
except Exception:
    pass

LAYA_HOME_DIR = Path.home() / ".laya"
LAYA_HOME_DIR.mkdir(parents=True, exist_ok=True)

RUNTIME_CREDS_FILE = LAYA_HOME_DIR / "runtime_credentials.json"
RUNTIME_LOG_FILE = LAYA_HOME_DIR / "laya_runtime.log"
BROWSER_PROFILE_DIR = LAYA_HOME_DIR / "browser_profile"
BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)


def _mask_secret(val: str) -> str:
    """Safely mask API keys and passwords for logs and status summaries."""
    s = (val or "").strip()
    if not s:
        return ""
    if len(s) <= 8:
        return "*" * len(s)
    return f"{s[:4]}...{s[-4:]}"


class RuntimeManager:
    _instance: Optional["RuntimeManager"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._log_buffer: deque = deque(maxlen=300)
        self._log_listeners: List[Callable[[str], None]] = []
        self._rw_lock = threading.RLock()

        # Default runtime model settings
        self.inference_mode: str = os.getenv("LAYA_INFERENCE_MODE", "auto")  # "auto" | "local_mistral" | "external_api"
        self.local_model: str = os.getenv("OLLAMA_MODEL", "mistral:7b")
        self.ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")

        # External runtime API settings
        self.external_api_key: str = os.getenv("EXTERNAL_API_KEY", "")
        self.external_base_url: str = os.getenv("EXTERNAL_BASE_URL", "https://api.openai.com/v1")
        self.external_model: str = os.getenv("EXTERNAL_MODEL", "gpt-4o-mini")

        # Load persisted runtime settings/credentials if present
        self._load_persisted_state()
        self.log_event("SYSTEM", f"RuntimeManager initialized (mode={self.inference_mode}, local_model={self.local_model})")

    @classmethod
    def get_instance(cls) -> "RuntimeManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------
    # 1. Structured Audit & Live Activity Logging
    # -------------------------------------------------------------
    def subscribe_logs(self, callback: Callable[[str], None]):
        with self._rw_lock:
            if callback not in self._log_listeners:
                self._log_listeners.append(callback)

    def log_event(self, category: str, message: str, level: str = "INFO") -> str:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] [{level.upper()}] [{category.upper()}] {message}"
        with self._rw_lock:
            self._log_buffer.append(line)
            try:
                with open(RUNTIME_LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except Exception:
                pass
            listeners = list(self._log_listeners)

        for cb in listeners:
            try:
                cb(line)
            except Exception:
                pass
        return line

    def get_recent_logs(self, limit: int = 80) -> List[str]:
        with self._rw_lock:
            items = list(self._log_buffer)
        if not items and RUNTIME_LOG_FILE.exists():
            try:
                with open(RUNTIME_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                    lines = [ln.rstrip("\n") for ln in f.readlines()]
                return lines[-limit:]
            except Exception:
                pass
        return items[-limit:]

    def clear_logs(self):
        with self._rw_lock:
            self._log_buffer.clear()
            try:
                with open(RUNTIME_LOG_FILE, "w", encoding="utf-8") as f:
                    f.write("")
            except Exception:
                pass
        self.log_event("SYSTEM", "Runtime logs cleared.")

    # -------------------------------------------------------------
    # 2. Persistence & Runtime Environment Injection
    # -------------------------------------------------------------
    def _load_persisted_state(self):
        if not RUNTIME_CREDS_FILE.exists():
            return
        try:
            with open(RUNTIME_CREDS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            with self._rw_lock:
                if "inference_mode" in data:
                    self.inference_mode = data["inference_mode"]
                if "local_model" in data:
                    self.local_model = data["local_model"]
                if "ollama_base_url" in data:
                    self.ollama_base_url = data["ollama_base_url"]
                if "external_api_key" in data:
                    self.external_api_key = data["external_api_key"]
                if "external_base_url" in data:
                    self.external_base_url = data["external_base_url"]
                if "external_model" in data:
                    self.external_model = data["external_model"]

                env_vars = data.get("env", {})
                for k, v in env_vars.items():
                    if v is not None and str(v).strip():
                        os.environ[k] = str(v).strip()
        except Exception as e:
            self.log_event("SYSTEM", f"Failed loading persisted runtime state: {e}", level="WARN")

    def _save_persisted_state(self, env_updates: Optional[Dict[str, str]] = None):
        with self._rw_lock:
            data: Dict[str, Any] = {}
            if RUNTIME_CREDS_FILE.exists():
                try:
                    with open(RUNTIME_CREDS_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}

            data["inference_mode"] = self.inference_mode
            data["local_model"] = self.local_model
            data["ollama_base_url"] = self.ollama_base_url
            data["external_api_key"] = self.external_api_key
            data["external_base_url"] = self.external_base_url
            data["external_model"] = self.external_model

            env_map = data.get("env", {})
            if env_updates:
                for k, v in env_updates.items():
                    if v is not None and str(v).strip():
                        env_map[k] = str(v).strip()
            data["env"] = env_map

            try:
                with open(RUNTIME_CREDS_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except Exception as e:
                self.log_event("SYSTEM", f"Failed persisting runtime state: {e}", level="ERROR")

    # -------------------------------------------------------------
    # 3. Runtime Model & External API Key Switching
    # -------------------------------------------------------------
    def set_inference_mode(self, mode: str, local_model: Optional[str] = None) -> str:
        norm = (mode or "auto").strip().lower()
        alias_map = {
            "mistral": "local_mistral",
            "local": "local_mistral",
            "ollama": "local_mistral",
            "local_mistral": "local_mistral",
            "cloud": "auto",
            "groq": "auto",
            "auto": "auto",
            "external": "external_api",
            "external_api": "external_api",
            "custom": "external_api",
        }
        target_mode = alias_map.get(norm, "auto")
        with self._rw_lock:
            self.inference_mode = target_mode
            if local_model and local_model.strip():
                self.local_model = local_model.strip()
                os.environ["OLLAMA_MODEL"] = self.local_model
            os.environ["LAYA_INFERENCE_MODE"] = target_mode
            self._save_persisted_state({
                "LAYA_INFERENCE_MODE": target_mode,
                "OLLAMA_MODEL": self.local_model,
            })

        msg = f"Switched inference mode to '{self.inference_mode}' (local model: {self.local_model})"
        self.log_event("LLM", msg)

        if target_mode == "local_mistral":
            started = self.ensure_ollama_running()
            if not started:
                self.log_event("LLM", "Ollama daemon not reachable on localhost:11434 yet.", level="WARN")
        return msg

    def set_external_llm(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        activate: bool = True,
    ) -> str:
        clean_key = (api_key or "").strip()
        if not clean_key:
            return "Error: External API key cannot be empty."

        clean_url = (base_url or self.external_base_url or "https://api.openai.com/v1").strip()
        clean_model = (model or self.external_model or "gpt-4o-mini").strip()

        # Autodetect popular provider prefixes if user didn't pass custom base_url
        if not base_url:
            if clean_key.startswith("gsk_"):
                clean_url = "https://api.groq.com/openai/v1"
                if not model:
                    clean_model = "openai/gpt-oss-120b"
            elif clean_key.startswith("sk-or-"):
                clean_url = "https://openrouter.ai/api/v1"
                if not model:
                    clean_model = "meta-llama/llama-3.3-70b-instruct"
            elif clean_key.startswith("AIza"):
                clean_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
                if not model:
                    clean_model = "gemini-2.5-flash"

        with self._rw_lock:
            self.external_api_key = clean_key
            self.external_base_url = clean_url
            self.external_model = clean_model
            if activate:
                self.inference_mode = "external_api"

            env_updates = {
                "EXTERNAL_API_KEY": clean_key,
                "EXTERNAL_BASE_URL": clean_url,
                "EXTERNAL_MODEL": clean_model,
                "LAYA_INFERENCE_MODE": self.inference_mode,
            }
            if clean_key.startswith("gsk_"):
                env_updates["GROQ_API_KEY"] = clean_key
                os.environ["GROQ_API_KEY"] = clean_key
            elif clean_key.startswith("sk-or-"):
                env_updates["OPENROUTER_API_KEY"] = clean_key
                os.environ["OPENROUTER_API_KEY"] = clean_key

            os.environ.update(env_updates)
            self._save_persisted_state(env_updates)

        # Refresh live ReActAgent clients
        try:
            from laya.orchestrator.react_agent import get_react_agent
            get_react_agent().reload_clients()
        except Exception:
            pass

        msg = f"Updated external API runtime config (endpoint={clean_url}, model={clean_model}, key={_mask_secret(clean_key)}, active={activate})"
        self.log_event("LLM", msg)
        return msg

    # -------------------------------------------------------------
    # 4. Local Ollama (Mistral / DeepSeek) Auto-Management
    # -------------------------------------------------------------
    def is_ollama_online(self) -> bool:
        try:
            with socket.create_connection(("localhost", 11434), timeout=0.35):
                return True
        except Exception:
            return False

    def ensure_ollama_running(self, wait_sec: float = 5.0) -> bool:
        if self.is_ollama_online():
            return True

        self.log_event("LLM", "Ollama server offline — attempting headless background startup ('ollama serve')...")
        try:
            creation_flags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creation_flags,
            )
            deadline = time.time() + wait_sec
            while time.time() < deadline:
                if self.is_ollama_online():
                    self.log_event("LLM", "Local Ollama server came online on port 11434.")
                    return True
                time.sleep(0.25)
        except Exception as e:
            self.log_event("LLM", f"Could not auto-start Ollama daemon: {e}", level="WARN")
        return False

    def list_local_ollama_models(self) -> List[str]:
        models: List[str] = []
        # 1. Try live HTTP API if running
        if self.is_ollama_online():
            try:
                import urllib.request
                with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=1.5) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                    for m in payload.get("models", []):
                        name = m.get("name", "")
                        if name and name not in models:
                            models.append(name)
            except Exception:
                pass

        # 2. Scan disk manifests (~/.ollama/models/manifests) as reliable fallback
        manifests_dir = Path.home() / ".ollama" / "models" / "manifests" / "registry.ollama.ai" / "library"
        if manifests_dir.exists():
            try:
                for model_dir in manifests_dir.iterdir():
                    if model_dir.is_dir():
                        for tag_file in model_dir.iterdir():
                            if tag_file.is_file():
                                tag_name = f"{model_dir.name}:{tag_file.name}"
                                if tag_name not in models:
                                    models.append(tag_name)
            except Exception:
                pass

        return models or ["mistral:7b"]

    # -------------------------------------------------------------
    # 5. Runtime Platform Credentials (Gmail, Telegram, Discord, Instagram)
    # -------------------------------------------------------------
    def update_platform_credentials(self, platform: str, credentials: Dict[str, str]) -> str:
        p = (platform or "").strip().lower()
        env_updates: Dict[str, str] = {}

        if p in ["gmail", "email", "mail"]:
            if credentials.get("user"):
                env_updates["EMAIL_USER"] = credentials["user"].strip()
            if credentials.get("password"):
                env_updates["EMAIL_PASSWORD"] = credentials["password"].strip()
            if credentials.get("imap_server"):
                env_updates["EMAIL_IMAP_SERVER"] = credentials["imap_server"].strip()
            if credentials.get("smtp_server"):
                env_updates["EMAIL_SMTP_SERVER"] = credentials["smtp_server"].strip()

        elif p in ["telegram", "tg"]:
            if credentials.get("api_id"):
                env_updates["TELEGRAM_API_ID"] = credentials["api_id"].strip()
            if credentials.get("api_hash"):
                env_updates["TELEGRAM_API_HASH"] = credentials["api_hash"].strip()
            if credentials.get("bot_token"):
                env_updates["TELEGRAM_BOT_TOKEN"] = credentials["bot_token"].strip()
            if credentials.get("phone"):
                env_updates["TELEGRAM_PHONE"] = credentials["phone"].strip()

        elif p in ["discord"]:
            if credentials.get("token"):
                env_updates["DISCORD_TOKEN"] = credentials["token"].strip()
            if credentials.get("webhook_url"):
                env_updates["DISCORD_WEBHOOK_URL"] = credentials["webhook_url"].strip()

        elif p in ["instagram", "insta", "ig"]:
            if credentials.get("access_token"):
                env_updates["INSTAGRAM_ACCESS_TOKEN"] = credentials["access_token"].strip()
            if credentials.get("account_id"):
                env_updates["INSTAGRAM_ACCOUNT_ID"] = credentials["account_id"].strip()
            if credentials.get("username"):
                env_updates["INSTAGRAM_USERNAME"] = credentials["username"].strip()
            if credentials.get("password"):
                env_updates["INSTAGRAM_PASSWORD"] = credentials["password"].strip()

        elif p in ["groq"]:
            if credentials.get("api_key"):
                env_updates["GROQ_API_KEY"] = credentials["api_key"].strip()

        elif p in ["openrouter"]:
            if credentials.get("api_key"):
                env_updates["OPENROUTER_API_KEY"] = credentials["api_key"].strip()

        else:
            # Generic key=value passthrough
            for k, v in credentials.items():
                if v and str(v).strip():
                    env_updates[k.upper()] = str(v).strip()

        if not env_updates:
            return f"No valid credentials provided for '{platform}'."

        with self._rw_lock:
            os.environ.update(env_updates)
            self._save_persisted_state(env_updates)

        # Hot-reload target MCP server if already running in MCPHub
        srv_map = {
            "gmail": "email", "email": "email", "mail": "email",
            "telegram": "telegram", "tg": "telegram",
            "discord": "discord",
            "instagram": "instagram", "insta": "instagram", "ig": "instagram",
        }
        target_srv = srv_map.get(p)
        if target_srv:
            try:
                from laya.mcp import get_mcp_hub
                hub = get_mcp_hub()
                if getattr(hub, "_initialized", False):
                    threading.Thread(target=hub.reload_server, args=(target_srv,), daemon=True).start()
            except Exception:
                pass

        if p in ["groq", "openrouter"]:
            try:
                from laya.orchestrator.react_agent import get_react_agent
                get_react_agent().reload_clients()
            except Exception:
                pass

        masked_keys = ", ".join(
            f"{k}={_mask_secret(v) if any(s in k for s in ['KEY', 'PASS', 'HASH', 'TOKEN']) else v}"
            for k, v in env_updates.items()
        )
        msg = f"Updated runtime credentials for {p}: {masked_keys}"
        self.log_event("AUTH", msg)
        return msg

    def get_status_snapshot(self) -> Dict[str, Any]:
        return {
            "inference_mode": self.inference_mode,
            "local_model": self.local_model,
            "ollama_online": self.is_ollama_online(),
            "available_local_models": self.list_local_ollama_models(),
            "external_configured": bool(self.external_api_key),
            "external_base_url": self.external_base_url,
            "external_model": self.external_model,
            "groq_configured": bool(os.getenv("GROQ_API_KEY", "").strip()),
            "openrouter_configured": bool(os.getenv("OPENROUTER_API_KEY", "").strip()),
            "platforms": {
                "gmail": {"configured": bool(os.getenv("EMAIL_USER") and os.getenv("EMAIL_PASSWORD")), "user": os.getenv("EMAIL_USER", "")},
                "telegram": {"configured": bool(os.getenv("TELEGRAM_API_ID") and os.getenv("TELEGRAM_API_HASH")), "api_id": os.getenv("TELEGRAM_API_ID", "")},
                "discord": {"configured": bool(os.getenv("DISCORD_TOKEN")), "mode": "mcp_token" if os.getenv("DISCORD_TOKEN") else "persistent_browser"},
                "instagram": {"configured": bool(os.getenv("INSTAGRAM_ACCESS_TOKEN") or os.getenv("INSTAGRAM_USERNAME")), "account_id": os.getenv("INSTAGRAM_ACCOUNT_ID", os.getenv("INSTAGRAM_USERNAME", ""))},
                "browser_profile": str(BROWSER_PROFILE_DIR),
            },
        }


def get_runtime_manager() -> RuntimeManager:
    return RuntimeManager.get_instance()

