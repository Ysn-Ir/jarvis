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
        # Strip wake words
        text = re.sub(r"^(laya|jarvis|hey laya|hey jarvis|computer)[,\s]+", "", text)
        text = text.strip()

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
        # 2. Compound / Multi-Step Detection -> Always Route to Agent Planner
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
        # Simple Volume (without "to X" or "maximum")
        if text in ["volume up", "raise volume", "raise the volume", "raise up the volume", "turn up volume", "turn up the volume", "turn the volume up", "louder"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="volume_up", params={"steps": 5})

        if text in ["volume down", "lower volume", "lower the volume", "turn down volume", "turn down the volume", "turn the volume down", "quieter"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="volume_down", params={"steps": 5})

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

        # Telemetry
        if text in ["check battery", "battery", "battery level"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="check_battery")

        if text in ["check ram", "ram", "memory usage"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="check_ram")

        if text in ["check cpu", "cpu usage"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="check_cpu")

        if text in ["what is my ip", "my ip", "what's my ip"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="check_ip")

        # System Screen & Power
        if text in ["lock screen", "lock computer", "lock pc"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="lock_workstation")

        if text in ["take a screenshot", "take screenshot", "screenshot"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="take_screenshot")

        if text in ["close this", "close window", "close this window"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="close_active_window")

        # Identity & Time
        if text in ["what time is it", "current time", "what's the time", "time"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="query_time")

        if text in ["what is today's date", "today's date", "what date is it"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="query_date")

        if text in ["who are you", "what is your name"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="query_identity")

        if text in ["tell me a joke", "make me laugh", "joke"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="tell_joke")

        # Single word app launch (e.g. "open spotify", "open chrome")
        single_open = re.match(r"^(?:open|launch|start)\s+([a-zA-Z0-9]+)$", text)
        if single_open:
            app_key = single_open.group(1).strip()
            if app_key in APP_REGISTRY or app_key in FOLDER_ALIASES:
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="open_app", params={"app_name": app_key})

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
