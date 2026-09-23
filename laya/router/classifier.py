"""
Laya Hybrid Intent Router & Classifier
Dual-Speed Execution:
1. Sub-millisecond Fast-Path for trivial deterministic single controls
2. Autonomous Agentic Planning for ANY multi-step, spoken, or open-ended instruction
"""

import re
from typing import Optional, Tuple, Dict, Any

from laya.router.taxonomy import ExecutionPath, RouteDecision
from laya.config import APP_REGISTRY, FOLDER_ALIASES


class IntentRouter:
    _instance: Optional["IntentRouter"] = None

    @classmethod
    def get_instance(cls) -> "IntentRouter":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def route(self, utterance: str) -> RouteDecision:
        """Route natural language utterance in single-digit milliseconds."""
        if not utterance or not utterance.strip():
            return RouteDecision(
                path=ExecutionPath.CLARIFY,
                action="none",
                clarification_prompt="I did not hear anything. How can I help?",
            )

        text = utterance.lower().strip()
        # Strip wake words and surrounding punctuation cleanly
        text = re.sub(r"^(?:hey|hi|hello)?[\s,]*(?:laya|jarvis|computer)[,\.!\s]*", "", text, flags=re.IGNORECASE).strip()
        text = text.strip(".!? ")

        # Instant greetings and readiness checks (<0.1ms)
        if not text or text in ["laya", "jarvis", "computer", "hey", "hello", "hi"]:
            return RouteDecision(
                path=ExecutionPath.FAST_PATH,
                action="query_identity",
                params={},
                confidence=1.0,
                reasoning="Instant greeting response."
            )

        if text in ["are you ready", "you ready", "are you there", "status", "ready"]:
            return RouteDecision(
                path=ExecutionPath.FAST_PATH,
                action="query_identity",
                params={},
                confidence=1.0,
                reasoning="Instant readiness check."
            )

        # ---------------------------------------------------------
        # 1. Catastrophic Destructive Safety Guardrail (0.0ms Abort)
        # ---------------------------------------------------------
        catastrophic_patterns = [
            r"\bformat\s+[a-z]:",
            r"\brm\s+-rf\s+/",
            r"\bdel\s+/[sfdq]\s+[a-z]:",
            r"\bdiskpart\b",
            r"\bdrop\s+database\b",
        ]
        for pattern in catastrophic_patterns:
            if re.search(pattern, text):
                return RouteDecision(
                    path=ExecutionPath.BLOCKED_SAFETY,
                    action="block_destructive",
                    safety_tier="RED",
                    confidence=1.0,
                    reasoning="Prevented catastrophic destructive system action.",
                )

        # ---------------------------------------------------------
        # 2. Direct Browser Search Automation (<1ms)
        # ---------------------------------------------------------
        browser_search_match = re.search(r"(?:open\s+(?:a\s+)?browser\s+(?:and\s+search\s+for|to\s+search|to\s+look\s+for|and\s+look\s+for|and\s+search)|search\s+(?:google|youtube|web|the\s+web)\s+for|look\s+(?:in|into)\s+(?:a\s+)?browser\s+for)\s+(.+)", text)
        if browser_search_match:
            query = browser_search_match.group(1).strip()
            engine = "youtube" if "youtube" in text else "google"
            return RouteDecision(
                path=ExecutionPath.FAST_PATH,
                action="browser_search",
                params={"query": query, "engine": engine},
                safety_tier="GREEN",
            )

        # ---------------------------------------------------------
        # 3. Compound / Multi-Step Detection -> Agent Planner
        # ---------------------------------------------------------
        if any(w in text for w in [" and ", " then ", " after that ", " also "]):
            return RouteDecision(
                path=ExecutionPath.REASONING_PATH,
                action="plan_and_execute",
                params={"raw_query": utterance},
                safety_tier="GREEN",
            )

        # ---------------------------------------------------------
        # 3. Simple Instant Fast-Path Triggers (<1ms)
        # ---------------------------------------------------------
        # Simple & Relative Volume
        rel_up = re.match(r"^(?:raise|increase|turn up)\s+(?:the\s+)?volume(?:\s+by)?(?:\s*(\d+))?(?:\s*percent|%)?$", text)
        if rel_up or text in ["volume up", "raise volume", "raise the volume", "raise up the volume", "turn up volume", "turn up the volume", "turn the volume up", "louder"]:
            steps = int(rel_up.group(1)) // 2 if (rel_up and rel_up.group(1)) else 5
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="volume_up", params={"steps": max(1, steps)})

        rel_down = re.match(r"^(?:lower|decrease|turn down)\s+(?:the\s+)?volume(?:\s+by)?(?:\s*(\d+))?(?:\s*percent|%)?$", text)
        if rel_down or text in ["volume down", "lower volume", "lower the volume", "turn down volume", "turn down the volume", "turn the volume down", "quieter"]:
            steps = int(rel_down.group(1)) // 2 if (rel_down and rel_down.group(1)) else 5
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="volume_down", params={"steps": max(1, steps)})

        vol_match = re.match(r"^(?:set\s+volume\s+to|volume\s+to|volume)\s+(\d{1,3})$", text)
        if vol_match:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="set_volume", params={"level": int(vol_match.group(1))})

        if text in ["mute", "mute audio", "unmute", "unmute audio"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="mute")

        # Media keys
        if text in ["play music", "pause music", "resume music", "toggle media", "pause"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="play_media")

        if text in ["next song", "next track", "skip"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="next_track")

        if text in ["previous song", "previous track"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="prev_track")

        # Telemetry & System Diagnostics (Robust phrase matching)
        if "battery" in text and not any(w in text for w in ["buy", "order", "replace"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="check_battery")

        if (any(w in text for w in ["check ram", "ram usage", "how much ram", "memory usage", "check memory"]) or re.search(r"\bram\b", text)):
            if not any(ign in text for ign in ["process", "processes", "task", "telegram", "program", "diagram", "instagram"]):
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="check_ram")

        if any(w in text for w in ["process", "processes"]) and any(w in text for w in ["list", "top", "show", "check", "what", "which"]):
            sort_metric = "cpu" if "cpu" in text else "memory"
            return RouteDecision(path=ExecutionPath.REASONING_PATH, action="list_processes", params={"sort_by": sort_metric})



        if any(w in text for w in ["check cpu", "cpu usage", "cpu utilization", "processor usage"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="check_cpu")

        if any(w in text for w in ["what is my ip", "my ip", "what's my ip", "check ip", "ip address"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="check_ip")

        # System Screen & Power
        if any(w in text for w in ["lock screen", "lock computer", "lock pc", "lock down the pc", "lock it down"]):
            delay_m = re.search(r"(\d+)\s*(?:seconds?|secs?|s)", text)
            delay_sec = int(delay_m.group(1)) if delay_m else 0
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="lock_workstation", params={"delay_sec": delay_sec})

        if text in ["take a screenshot", "take screenshot", "screenshot", "screen shot", "capture screen"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="take_screenshot")

        if text in ["close this", "close window", "close this window", "close active window"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="close_active_window")

        # Identity & Time (Robust phrase matching)
        if any(p in text for p in ["time is it", "what time", "current time", "time now", "tell me the time", "what's the time", "time it is", "what is the time"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="query_time")

        if any(p in text for p in ["today's date", "what date", "current date", "what day is it", "what's the date", "what is today's date"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="query_date")

        if any(p in text for p in ["who are you", "what is your name", "what are you"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="query_identity")

        if any(p in text for p in ["tell me a joke", "make me laugh", "joke"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="tell_joke")

        # Direct app launch (e.g. "open chrome", "open telegram", "open discord", "open vs code", "open notepad")
        open_match = re.match(r"^(?:open|launch|start)\s+(?:the\s+)?([a-zA-Z0-9\s_\-\.]+?)(?:\s+app|\s+application|\s+program)?$", text)
        if open_match:
            raw_target = open_match.group(1).strip()
            # Do not intercept file or web instructions like "open chrome and search" or "open folder"
            if raw_target not in ["a", "the", "it", "this", "new folder", "folder"]:
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="open_app", params={"app_name": raw_target})


        # ---------------------------------------------------------
        # 4. ALL Other Instructions Handled by Autonomous Agent Planner
        # ---------------------------------------------------------
        return RouteDecision(
            path=ExecutionPath.REASONING_PATH,
            action="plan_and_execute",
            params={"raw_query": utterance},
            safety_tier="GREEN",
            confidence=0.95,
        )


def get_intent_router() -> IntentRouter:
    return IntentRouter.get_instance()


def classify_intent(utterance: str) -> RouteDecision:
    """Convenience helper to classify and route an utterance."""
    return IntentRouter.get_instance().route(utterance)

