"""
Laya Neural Decision Engine (Convai Innovations ModernBERT Router)
Non-autoregressive semantic intent classification (<40ms CPU latency).
Bypasses LLMs for natural colloquial voice commands without brittle regexes.
"""

import os
import sys
import re
import time
import importlib.util
from typing import Optional, Dict, Any, Tuple

from laya.router.taxonomy import ExecutionPath, RouteDecision


class LayaDecisionEngine:
    _instance: Optional["LayaDecisionEngine"] = None

    def __init__(self):
        self._router = None
        self._initialized = False
        self._questions = {
            "action": {
                "type": "choice",
                "instructions": "What desktop action should be taken for `command`?",
                "criteria": {
                    "volume_up": "increase, boost, or raise sound volume, turn up audio, louder",
                    "volume_down": "decrease, lower, or turn down sound volume, turn down audio, softer",
                    "open_folder": "open or explore folder on desktop or browse files",
                    "close_all_apps": "close or quit all applications, windows, or programs",
                    "open_gmail": "check or open email, gmail, or webmail inbox",
                    "telegram_launch": "open or launch telegram messages or telegram app",
                    "take_screenshot": "capture or take a screenshot of screen",
                    "other": "everything else, general questions, knowledge, or chat"
                }
            },
            "is_destructive": {
                "type": "noul",
                "instructions": "Does `command` ask to shut down, restart, format, or delete files?",
            }
        }
        self._init_router()

    @classmethod
    def get_instance(cls) -> "LayaDecisionEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _init_router(self):
        """Cleanly import official laya package from site-packages without shadowing local modules."""
        if self._initialized:
            return
        try:
            import site
            site_packages = site.getusersitepackages()
            site_laya = os.path.join(site_packages, "laya")

            if not os.path.exists(site_laya):
                # Search sys.path for installed site-packages directory
                for p in sys.path:
                    candidate = os.path.join(p, "laya")
                    if os.path.exists(candidate) and os.path.exists(os.path.join(candidate, "router.py")):
                        if "projects\\jev" not in os.path.abspath(candidate).lower():
                            site_laya = candidate
                            break

            if not os.path.exists(site_laya):
                print("[LayaEngine] Official laya package directory not found in site-packages.")
                return

            spec = importlib.util.spec_from_file_location(
                "official_laya",
                os.path.join(site_laya, "__init__.py"),
                submodule_search_locations=[site_laya]
            )
            if not spec or not spec.loader:
                print("[LayaEngine] Could not create module spec for official_laya.")
                return

            mod = importlib.util.module_from_spec(spec)
            sys.modules["official_laya"] = mod
            spec.loader.exec_module(mod)

            # Instantiate official laya.Router
            self._router = mod.Router()
            self._initialized = True
            print("[LayaEngine] Successfully initialized official Convai ModernBERT decision engine.")

            # Warmup prediction in background
            try:
                self._router.predict("raise the sound", self._questions)
            except Exception as we:
                print(f"[LayaEngine] Warmup note: {we}")

        except Exception as e:
            print(f"[LayaEngine] Initialization error: {e}")

    def predict_intent(self, text: str, original: str) -> Optional[RouteDecision]:
        """
        Evaluate utterance using official Laya ModernBERT neural router.
        Returns a RouteDecision if high-confidence desktop action, or None if reasoning/open-ended.
        """
        if not self._initialized or self._router is None:
            return None

        # Clean text
        clean = text.lower().strip()
        if len(clean) < 3:
            return None

        # Informational knowledge questions and explanations should NEVER trigger desktop actions
        info_prefixes = (
            "what is ", "what are ", "what was ", "what's ",
            "who is ", "who are ", "who was ", "who's ",
            "why is ", "why are ", "why do ", "why does ",
            "how is ", "how are ", "how does ", "how do ", "how to ",
            "when was ", "when is ", "where is ", "where are ",
            "explain ", "tell me about ", "describe ", "can you explain "
        )
        if clean.startswith(info_prefixes) or clean.endswith("?"):
            return None

        try:
            t0 = time.perf_counter()
            res = self._router.predict(clean, self._questions)
            dt = (time.perf_counter() - t0) * 1000

            action_res = res.get("answers", {}).get("action", {})
            choice = action_res.get("choice", "other")
            probs = action_res.get("probabilities", {})
            prob = probs.get(choice, 0.0)

            destructive_prob = res.get("answers", {}).get("is_destructive", {}).get("noul", 0.0)

            # If classified as 'other' or low probability, leave to reasoning / Groq LLM
            if choice == "other" or prob < 0.38:
                return None

            # 1. Volume Up
            if choice == "volume_up":
                if not any(w in clean for w in ["volume", "sound", "audio", "louder", "boost", "turn up", "raise", "higher", "make it louder"]):
                    return None
                num_m = re.search(r"\b(?:by\s+)?(\d{1,2})\s*(?:percent|%|steps?)?\b", clean)
                steps = (int(num_m.group(1)) // 2) if num_m else 8
                return RouteDecision(
                    path=ExecutionPath.FAST_PATH,
                    action="volume_up",
                    params={"steps": max(2, steps)},
                    confidence=prob,
                    reasoning=f"Laya neural router classified volume_up ({dt:.1f}ms, p={prob:.2f})."
                )

            # 2. Volume Down
            if choice == "volume_down":
                if not any(w in clean for w in ["volume", "sound", "audio", "quieter", "softer", "turn down", "lower", "decrease", "reduce"]):
                    return None
                num_m = re.search(r"\b(?:by\s+)?(\d{1,2})\s*(?:percent|%|steps?)?\b", clean)
                steps = (int(num_m.group(1)) // 2) if num_m else 8
                return RouteDecision(
                    path=ExecutionPath.FAST_PATH,
                    action="volume_down",
                    params={"steps": max(2, steps)},
                    confidence=prob,
                    reasoning=f"Laya neural router classified volume_down ({dt:.1f}ms, p={prob:.2f})."
                )

            # 3. Open Folder
            if choice == "open_folder":
                if not any(w in clean for w in ["folder", "desktop", "directory", "files", "explore", "browse"]):
                    return None
                # Check for target folder name
                folder = "desktop"
                folder_m = re.search(r"\b(?:open|explore|view)\s+(?:the\s+|a\s+)?folder\s+([a-zA-Z0-9_\-\.\s]+)", clean)
                if folder_m:
                    f_cand = folder_m.group(1).strip()
                    if f_cand not in ["this", "it", "that", "an app", "in desktop", "on desktop"]:
                        folder = f_cand
                elif "downloads" in clean:
                    folder = "downloads"
                elif "documents" in clean:
                    folder = "documents"
                elif "pictures" in clean:
                    folder = "pictures"

                return RouteDecision(
                    path=ExecutionPath.FAST_PATH,
                    action="open_folder",
                    params={"folder_name": folder},
                    confidence=prob,
                    reasoning=f"Laya neural router classified open_folder ({dt:.1f}ms, p={prob:.2f})."
                )

            # 4. Close All Applications
            if choice == "close_all_apps":
                if any(w in clean for w in ["shut down the computer", "shutdown", "turn off", "power off", "reboot", "restart", "computer", "pc"]):
                    return None
                if not any(w in clean for w in ["close", "quit", "exit", "kill", "close all", "terminate"]):
                    return None
                return RouteDecision(
                    path=ExecutionPath.FAST_PATH,
                    action="close_all_apps",
                    params={},
                    confidence=prob,
                    reasoning=f"Laya neural router classified close_all_apps ({dt:.1f}ms, p={prob:.2f})."
                )

            # 5. Open Gmail
            if choice == "open_gmail":
                if not any(w in clean for w in ["gmail", "email", "emails", "mail", "inbox", "webmail"]):
                    return None
                if any(w in clean for w in ["check", "read", "fetch", "summarize", "any new"]):
                    return RouteDecision(
                        path=ExecutionPath.FAST_PATH,
                        action="check_emails",
                        params={},
                        confidence=prob,
                        reasoning=f"Laya neural router classified check_emails ({dt:.1f}ms, p={prob:.2f})."
                    )
                return RouteDecision(
                    path=ExecutionPath.FAST_PATH,
                    action="open_webmail",
                    params={},
                    confidence=prob,
                    reasoning=f"Laya neural router classified open_webmail ({dt:.1f}ms, p={prob:.2f})."
                )

            # 6. Telegram Launch
            if choice == "telegram_launch":
                if "telegram" not in clean:
                    return None
                return RouteDecision(
                    path=ExecutionPath.FAST_PATH,
                    action="telegram_launch",
                    params={},
                    confidence=prob,
                    reasoning=f"Laya neural router classified telegram_launch ({dt:.1f}ms, p={prob:.2f})."
                )

            # 7. Take Screenshot
            if choice == "take_screenshot":
                if not any(w in clean for w in ["screenshot", "screen", "capture"]):
                    return None
                return RouteDecision(
                    path=ExecutionPath.FAST_PATH,
                    action="take_screenshot",
                    params={},
                    confidence=prob,
                    reasoning=f"Laya neural router classified take_screenshot ({dt:.1f}ms, p={prob:.2f})."
                )

            # 8. Open App
            if choice == "open_app":
                app_m = re.search(r"\b(?:open|launch|start|run)\s+(?:the\s+)?([a-zA-Z0-9_\-\.\s]+?)(?:\s+app|\s+program)?$", clean)
                app_name = app_m.group(1).strip() if app_m else ""
                if app_name and app_name not in ["this", "it", "something", "an app", "folder"]:
                    return RouteDecision(
                        path=ExecutionPath.FAST_PATH,
                        action="open_app",
                        params={"app_name": app_name},
                        confidence=prob,
                        reasoning=f"Laya neural router classified open_app ({dt:.1f}ms, p={prob:.2f})."
                    )

            # 9. System Power (Shutdown / Restart)
            if choice == "system_power":
                is_restart = any(w in clean for w in ["restart", "reboot"])
                return RouteDecision(
                    path=ExecutionPath.FAST_PATH,
                    action="restart_system" if is_restart else "shutdown_system",
                    params={},
                    safety_tier="RED",
                    confidence=prob,
                    reasoning=f"Laya neural router classified system power control (destructive={destructive_prob:.2f})."
                )

            # 10. Conversation History
            if choice == "conversation_history":
                return RouteDecision(
                    path=ExecutionPath.FAST_PATH,
                    action="get_conversation_history",
                    params={},
                    confidence=prob,
                    reasoning=f"Laya neural router classified conversation_history ({dt:.1f}ms, p={prob:.2f})."
                )

        except Exception as ex:
            print(f"[LayaEngine] Prediction error: {ex}")

        return None


def get_laya_engine() -> LayaDecisionEngine:
    return LayaDecisionEngine.get_instance()
