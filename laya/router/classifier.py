"""
Laya Hybrid Intent Router & Ultra-Fast Classifier
Dual-Speed Architecture:
1. Sub-millisecond Fast-Path & Compound Splitter for deterministic OS actions (<1ms)
2. Ultra-Fast LLM Intent Classifier (<250ms) using Groq for natural colloquial speech
3. Deep Multi-Step ReAct Planning strictly reserved for open-ended reasoning tasks
"""

import os
import re
import json
import time
from typing import Optional, Tuple, Dict, Any, List

from laya.router.taxonomy import ExecutionPath, RouteDecision
from laya.config import APP_REGISTRY, FOLDER_ALIASES, GROQ_API_KEY, GROQ_MODEL


class IntentRouter:
    _instance: Optional["IntentRouter"] = None

    @classmethod
    def get_instance(cls) -> "IntentRouter":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def route(self, utterance: str) -> RouteDecision:
        """Route natural language utterance with sub-millisecond reflex speed."""
        if not utterance or not utterance.strip():
            return RouteDecision(
                path=ExecutionPath.CLARIFY,
                action="none",
                clarification_prompt="I did not hear anything. How can I help you?",
            )

        text = utterance.lower().strip()
        # Clean leading conversational prefixes (Hey, Hi, Hello, OK, etc.)
        text = re.sub(r"^(?:hey|hi|hello|ok|okay)?[\s,]*(?:assistant|system|computer|jarvis|bot|laya|leia|layer)[,\.!\s]*", "", text, flags=re.IGNORECASE).strip()

        # Check for explicit phone/voice/video call requests BEFORE stripping "call"
        call_match = re.search(r"^(?:(?:can\s+you\s+)?(?:call|voice\s+call|video\s+call|phone|ring|make\s+a\s+call\s+to)\s+)(.+?)(?:\s+(?:on|via|through|in)\s+(telegram|whatsapp))?$", text, re.I)
        if call_match:
            callee = call_match.group(1).strip()
            platform = (call_match.group(2) or "telegram").lower().strip()
            CALL_EXCLUDE_PREFIXES = ("open", "launch", "play", "close", "show", "hide", "search", "send", "check", "take", "write", "create", "draw", "raise", "lower", "set", "mute", "unmute", "turn", "stop", "what", "how", "who", "where", "why")
            if callee and callee not in ["me", "i", "it", "my", "the", "a", "someone", "system", "assistant", "computer", "jarvis", "ready"]:
                if not callee.lower().startswith(CALL_EXCLUDE_PREFIXES):
                    if platform == "whatsapp":
                        return RouteDecision(path=ExecutionPath.FAST_PATH, action="whatsapp_call", params={"contact": callee, "call_type": "voice"})
                    else:
                        return RouteDecision(path=ExecutionPath.FAST_PATH, action="telegram_call", params={"recipient": callee, "call_type": "voice"})

        # Clean leading wake word "call" for other commands (e.g. "call open spotify" -> "open spotify")
        text = re.sub(r"^call[\s,]+", "", text, flags=re.IGNORECASE).strip()
        text = text.strip(".!? ")

        # Clean trailing conversational filler words (e.g. "scroll down now" -> "scroll down", "open chrome please" -> "open chrome")
        text = re.sub(r"\s+(?:now|please|for me|quickly|right now|a bit|a little bit)$", "", text, flags=re.IGNORECASE).strip()

        # Extreme Mode 1: Foid Alert Mode (<0.0ms)
        if re.search(r"\b(?:foid(?:\s+(?:nearby|detected|alert|warning))?|woman\s+nearby|girl\s+nearby|female\s+detected|females\s+detected|foid\s+foid\s+go\s+away|strike\s+my\s+cortisol|spike\s+my\s+cortisol)\b", text, re.I):
            return RouteDecision(
                path=ExecutionPath.FAST_PATH,
                action="foid_alert_mode",
                confidence=1.0,
                reasoning="Foid detected: activating emergency siren and red alert mode."
            )

        # Extreme Mode 2: Chud Take / Insult Mode (<0.0ms)
        # Broad pattern: catches most common insults and dismissals directed at the assistant
        if re.search(
            r"\b(?:"
            r"you\s+suck|you'?re?\s+(?:stupid|dumb|trash|useless|garbage|pathetic|terrible|awful|horrible|a\s+joke|an?\s+idiot|annoying|broken|bad)|you\s+(?:are|were)\s+(?:stupid|dumb|useless|garbage|terrible|bad)|shut\s+up(?:\s+(?:idiot|stupid|bot|dumbass|moron))?|"
            r"fuck\s+(?:you|off|this|that)|go\s+fuck\s+yourself|you\s+piece\s+of\s+(?:shit|garbage|trash|crap)|piece\s+of\s+(?:shit|garbage)|"
            r"dumbass|dipshit|jackass|asshole|bastard|motherfucker|dumb(?:ass|fuck)|braindead|brain\s+dead|"
            r"idiot|moron|imbecile|cretin|halfwit|dimwit|nitwit|twit|numbnuts|"
            r"trash\s+(?:bot|ai|assistant)|useless\s+(?:bot|ai|assistant|piece|garbage|shit)|garbage\s+(?:bot|ai|assistant)|"
            r"chud\s+take(?:\s+detected)?|chud\s+mode|activate\s+chud|chudjak|"
            r"nothing\s+ever\s+happens|billions\s+must|terrible\s+(?:bot|ai|assistant)|"
            r"i\s+hate\s+(?:you|this(?:\s+bot)?)|worst\s+(?:bot|ai|assistant)|"
            r"you'?re?\s+(?:the\s+)?worst|absolute\s+(?:garbage|trash|moron|idiot)|total\s+(?:garbage|trash)"
            r")\b",
            text, re.I
        ):
            return RouteDecision(
                path=ExecutionPath.FAST_PATH,
                action="chud_self_destruct",
                confidence=1.0,
                reasoning="User insult / chud take detected: activating chud alert and initiating self destruction."
            )

        # Extreme Mode 3: Extreme Lockdown Mode (<0.0ms)
        if re.search(r"\b(?:lock\s+in|lockdown\s+mode|extreme\s+mode|rage\s+mode|locking\s+in|hyper\s+focus\s+mode)\b", text, re.I):
            return RouteDecision(
                path=ExecutionPath.FAST_PATH,
                action="extreme_lockdown_mode",
                confidence=1.0,
                reasoning="Lock-in command: activating extreme lockdown mode."
            )

        # 0. Instant Stop, Cancel, Quiet, Abort (<0.0ms)
        if re.search(r"^(?:please\s+)?(?:stop|halt|cancel|abort|freeze|quiet|silence|be\s+quiet|shut\s*up|nevermind|never\s+mind|don't\s+do\s+that)(?:\s+(?:it|that|now|please|everything|all|talking))?$", text):
            return RouteDecision(
                path=ExecutionPath.FAST_PATH,
                action="stop_action",
                params={},
                confidence=1.0,
                reasoning="Instant abort/stop command."
            )

        # 1. Instant greetings and readiness checks (<0.1ms)
        if not text or text in ["call", "assistant", "system", "computer", "jarvis", "hey", "hello", "hi", "laya"]:
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

        # 2. Catastrophic Destructive Safety Guardrail (0.0ms Abort)
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

        # 3. Fast Compound Command Splitter (e.g. "open paint and draw a circle", "raise volume and mute")
        compound_decision = self._try_compound_fast_path(text)
        if compound_decision:
            return compound_decision

        # 4. Local Neural Intent Classifier: Official Laya ModernBERT (<40ms Local)
        # Evaluates natural colloquial speech FIRST via non-autoregressive decision model
        try:
            from laya.router.laya_engine import get_laya_engine
            laya_decision = get_laya_engine().predict_intent(text, utterance)
            if laya_decision:
                return laya_decision
        except Exception as e:
            pass

        # 5. Deterministic OS Fast-Path Patterns (<1ms)
        # Rock-solid zero-LLM dispatch evaluated right afterwards to guarantee full coverage and precision
        single_decision = self._route_single_deterministic(text, utterance)
        if single_decision:
            return single_decision

        # 6. Ultra-Fast LLM Intent Classifier Layer (<250ms on Groq)
        llm_decision = self._classify_with_fast_llm(utterance)
        if llm_decision:
            return llm_decision

        # 7. Fallback to Autonomous ReAct Agent Loop for genuinely open-ended tasks
        return RouteDecision(
            path=ExecutionPath.REASONING_PATH,
            action="plan_and_execute",
            params={"raw_query": utterance},
            safety_tier="GREEN",
            confidence=0.90,
        )

    # -------------------------------------------------------------
    # Fast Compound Command Splitter
    # -------------------------------------------------------------
    def _try_compound_fast_path(self, text: str) -> Optional[RouteDecision]:
        """Split compound instructions joined by 'and', 'then' and execute sequentially if deterministic."""
        # Avoid splitting YouTube search queries like "open youtube and search for ..."
        if "youtube and search" in text or "browser and search" in text or "google and search" in text:
            return None

        # Check for split tokens
        split_pattern = r"\b(?:and\s+then|then|after\s+that|and\s+also|and)\b"
        if not re.search(split_pattern, text):
            return None

        parts = [p.strip() for p in re.split(split_pattern, text) if p.strip()]
        if len(parts) < 2:
            return None

        decisions: List[RouteDecision] = []
        for i, part in enumerate(parts):
            # Pronoun resolution for compound actions: "create folder X and open it" or "create file X and open it"
            if i > 0 and re.match(r"^(?:open\s+(?:it|them|that|the\s+folder|that\s+folder|the\s+file|that\s+file)|open\s+it|open)$", part, re.I):
                if decisions and decisions[-1].action in ["create_folder", "create_and_open_folder"]:
                    target_fol = decisions[-1].params.get("folder_name") or "desktop"
                    decisions.append(RouteDecision(
                        path=ExecutionPath.FAST_PATH,
                        action="open_folder",
                        params={"folder_name": target_fol},
                        safety_tier="GREEN",
                        confidence=1.0,
                    ))
                    continue
                elif decisions and decisions[-1].action == "create_file":
                    target_file = decisions[-1].params.get("filename") or "it"
                    decisions.append(RouteDecision(
                        path=ExecutionPath.FAST_PATH,
                        action="open_file",
                        params={"filename_or_path": target_file},
                        safety_tier="GREEN",
                        confidence=1.0,
                    ))
                    continue

            # Pronoun resolution for write / append in compound chain:
            if i > 0 and re.search(r"^(?:write(?:\s+to\s+it)?|append(?:\s+to\s+it)?)\s+(.+)$", part, re.I):
                w_match = re.search(r"^(?:write(?:\s+to\s+it)?|append(?:\s+to\s+it)?)\s+(.+)$", part, re.I)
                act = "append_to_file" if "append" in part.lower() else "write_to_file"
                content = w_match.group(1).strip() if w_match else ""
                target_f = "it"
                if decisions and decisions[-1].action == "create_file":
                    target_f = decisions[-1].params.get("filename") or "it"
                decisions.append(RouteDecision(
                    path=ExecutionPath.FAST_PATH,
                    action=act,
                    params={"filename": target_f, "content": content} if act == "write_to_file" else {"filename_or_path": target_f, "content": content},
                    safety_tier="GREEN",
                    confidence=1.0,
                ))
                continue

            d = self._route_single_deterministic(part, part)
            if not d or d.path != ExecutionPath.FAST_PATH:
                return None
            decisions.append(d)

        actions_list = [{"action": d.action, "params": d.params} for d in decisions]
        return RouteDecision(
            path=ExecutionPath.FAST_PATH,
            action="execute_compound",
            params={"actions": actions_list},
            safety_tier="GREEN",
            confidence=1.0,
            reasoning=f"Compound fast-path sequence ({len(actions_list)} actions)."
        )

    # -------------------------------------------------------------
    # Single Deterministic Fast-Path Matcher
    # -------------------------------------------------------------
    def _route_single_deterministic(self, text: str, original: str) -> Optional[RouteDecision]:
        # 0. Interruption, Abort & UI Visibility (<0.0ms)
        if re.search(r"\b(?:stop|cancel|shut\s*up|abort|freeze|halt)\b", text) and len(text.split()) <= 3:
            if not re.search(r"\b(?:timer|timers|reminder|reminders|recording|download|downloads)\b", text, re.I):
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="stop_action")

        if re.search(r"\b(?:hide|dismiss|close|minimize)\s+(?:the\s+)?(?:ui|hud|window|overlay|assistant)\b|^hide$|^dismiss$", text):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="hide_hud")

        if re.search(r"\b(?:show|open|bring\s+up|display)\s+(?:the\s+)?(?:ui|hud|overlay)\b", text):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="show_hud")

        # 1. Universal Mute & Audio Silence (<0.0ms)
        if re.search(r"\b(?:mute|unmute|silence|be\s+quiet|shut\s+up|quiet)\b", text):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="mute")

        # 2. Volume Controls (<0.0ms)
        vol_set_match = re.search(r"\b(?:set\s+(?:the\s+)?(?:volume|sound|audio)\s+to|volume\s+to|sound\s+to|audio\s+to)\s+(\d{1,3})\b", text)
        if vol_set_match:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="set_volume", params={"level": int(vol_set_match.group(1))})

        rel_up = re.search(r"\b(?:raise|increase|turn\s+up|boost|higher|put\s+up)\s+(?:the\s+)?(?:volume|sound|audio)\b", text)
        if rel_up or text in ["volume up", "sound up", "raise volume", "raise sound", "raise the volume", "raise the sound", "turn up volume", "turn up sound", "turn up the volume", "turn up the sound", "louder", "make it louder", "higher sound", "boost sound"]:
            num_m = re.search(r"\b(?:by\s+)?(\d{1,2})\s*(?:percent|%|steps?)?\b", text)
            steps = (int(num_m.group(1)) // 2) if num_m else 8
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="volume_up", params={"steps": max(2, steps)})

        rel_down = re.search(r"\b(?:lower|decrease|turn\s+down|reduce|softer|quieter|put\s+down)\s+(?:the\s+)?(?:volume|sound|audio)\b", text)
        if rel_down or text in ["volume down", "sound down", "lower volume", "lower sound", "lower the volume", "lower the sound", "turn down volume", "turn down sound", "turn down the volume", "turn down the sound", "quieter", "make it quieter", "softer"]:
            num_m = re.search(r"\b(?:by\s+)?(\d{1,2})\s*(?:percent|%|steps?)?\b", text)
            steps = (int(num_m.group(1)) // 2) if num_m else 8
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="volume_down", params={"steps": max(2, steps)})

        # 2b. System Power, Sleep, Lock & Display Management (<0.0ms)
        if re.search(r"\b(?:put\s+(?:the\s+|my\s+)?(?:computer|pc|laptop|system|machine)\s+to\s+sleep|sleep\s+(?:the\s+|my\s+)?(?:computer|pc|laptop|system|machine)|suspend\s+(?:the\s+|my\s+)?(?:computer|pc|laptop|system)|go\s+to\s+sleep)\b", text, re.I) or text in [
            "sleep pc", "sleep computer", "sleep system", "put pc to sleep", "put computer to sleep", "sleep the pc", "sleep the computer", "suspend pc", "suspend computer"
        ]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="sleep_system", safety_tier="GREEN", confidence=1.0, reasoning="Instant computer sleep.")

        if re.search(r"\b(?:lock\s+(?:the\s+|my\s+)?(?:pc|computer|workstation|screen|machine|laptop|windows)|lock\s+it|^lock$)\b", text, re.I) or text in [
            "lock pc", "lock the pc", "lock my pc", "lock workstation", "lock computer", "lock screen", "lock the screen", "lock machine"
        ]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="lock_workstation", safety_tier="GREEN", confidence=1.0, reasoning="Instant screen lock.")

        if re.search(r"\b(?:turn\s+off\s+(?:the\s+)?(?:screen|display|monitor)|turn\s+(?:the\s+)?(?:screen|display|monitor)\s+off|(?:screen|display|monitor)\s+off|shut\s+off\s+(?:the\s+)?(?:screen|display|monitor)|sleep\s+(?:the\s+)?(?:screen|display|monitor)|put\s+(?:the\s+)?(?:screen|display|monitor)\s+to\s+sleep|blank\s+screen|turn\s+(?:the\s+)?screen\s+black)\b", text, re.I) or text in [
            "turn off screen", "turn off the screen", "turn the screen off", "screen off",
            "turn off display", "turn off the display", "turn the display off", "display off",
            "sleep screen", "sleep display", "turn off monitor", "turn off the monitor", "turn monitor off",
            "blank screen"
        ]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="turn_screen_off", safety_tier="GREEN", confidence=1.0, reasoning="Instant screen turn-off.")

        if re.search(r"\b(?:turn\s+on\s+(?:the\s+)?(?:screen|display|monitor)|turn\s+(?:the\s+)?(?:screen|display|monitor)\s+on|(?:screen|display|monitor)\s+on|wake\s+(?:up\s+)?(?:the\s+)?(?:screen|display|monitor))\b", text, re.I) or text in [
            "turn on screen", "turn on the screen", "turn the screen on", "screen on",
            "turn on display", "turn on the display", "turn the display on", "display on",
            "wake screen", "wake up screen", "wake display"
        ]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="turn_screen_on", safety_tier="GREEN", confidence=1.0, reasoning="Instant screen turn-on.")

        # 2c. Screen & Camera Video Recording Controls (<0.0ms)
        # Stop active recordings
        if any(w in text for w in ["stop camera recording", "stop camera video", "stop recording camera", "stop camera", "stop webcam"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="stop_camera_recording")
        if any(w in text for w in ["stop screen recording", "stop recording screen", "stop screen record"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="stop_screen_recording")
        if any(w in text for w in ["stop recording", "stop video recording", "stop the recording", "stop all recordings"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="stop_all_recordings")

        # Camera video recording (asynchronous, continuous by default unless duration given)
        cam_rec_match = re.search(
            r"\b(?:record\s+(?:the\s+|a\s+)?(?:camera|webcam|webcam\s+video|camera\s+video)|start\s+(?:a\s+)?(?:camera|webcam)\s+recording|record\s+video\s+(?:with|using|from)\s+(?:the\s+)?(?:camera|webcam))\b(?:\s+(?:for\s+)?(\d+)\s*(?:seconds?|secs?))?",
            text,
            re.I
        )
        if cam_rec_match:
            cam_dur = int(cam_rec_match.group(1)) if cam_rec_match.group(1) else 0
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="record_camera_video", params={"duration": cam_dur})

        if text in ["record video", "take video", "take a video", "record camera", "record a video", "video record"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="record_camera_video", params={"duration": 0})

        # Screen recording (asynchronous, continuous by default unless duration given)
        screen_rec_match = re.search(
            r"\b(?:record\s+(?:the\s+|my\s+)?screen|start\s+(?:a\s+)?screen\s+recording|start\s+(?:a\s+)?recording|screen\s+record|toggle\s+screen\s+recording)\b(?:\s+(?:for\s+)?(\d+)\s*(?:seconds?|secs?))?",
            text,
            re.I
        )
        if screen_rec_match:
            rec_dur = int(screen_rec_match.group(1)) if screen_rec_match.group(1) else 0
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="record_screen", params={"duration": rec_dur})

        # 3. Media & Song Controls (<0.0ms)
        if text in ["play music", "pause music", "resume music", "toggle media", "pause", "play", "stop music"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="play_media")
        if text in ["next song", "next track", "skip"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="next_track")
        if text in ["previous song", "previous track"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="prev_track")

        if text in ["play music", "launch music", "open music", "start music", "play some music", "listen to music"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="play_youtube", params={"query": "synthwave lofi chillhop mix"})

        click_song_match = re.search(r"\b(?:click\s+on\s+(?:a\s+)?song|play\s+(?:a\s+)?song|start\s+(?:a\s+)?song|launch\s+music|open\s+music)\b", text)
        if click_song_match:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="play_youtube", params={"query": "synthwave lofi chillhop mix"})

        spot_match = re.search(r"\b(?:open\s+spotify\s+(?:and\s+)?(?:play|launch|start)|play\s+(.+?)\s+on\s+spotify|play\s+spotify)\s*(.+)?$", text)
        if spot_match:
            song_q = (spot_match.group(1) or spot_match.group(2) or "").strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="play_spotify", params={"query": song_q})

        # 4. YouTube Direct Play & Search (<0.0ms)
        yt_play_match = re.match(
            r"^(?:can\s+you\s+|could\s+you\s+|please\s+)?(?:play|start|watch|listen\s+to|open\s+video(?:\s+of)?|launch\s+video(?:\s+of)?)\s+(.+?)(?:\s+(?:on|from|in)\s+youtube)?$",
            text,
            flags=re.IGNORECASE
        )
        if yt_play_match:
            raw_query = yt_play_match.group(1).strip()
            raw_query = re.sub(r"\s+(?:on|from|in)\s+youtube\b", "", raw_query, flags=re.IGNORECASE).strip()
            raw_query = re.sub(r"^(?:like|some|uh|um)\s+", "", raw_query, flags=re.IGNORECASE).strip()
            if not raw_query or raw_query in ["songs", "some songs", "music", "some music", "a song", "video", "a video", "videos"]:
                raw_query = "synthwave lofi chillhop mix"
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="play_youtube", params={"query": raw_query})

        yt_search_match = re.search(
            r"(?:open\s+youtube\s+(?:and\s+search\s+for|to\s+search|to\s+look\s+for|and\s+search)|search\s+(?:on\s+)?youtube\s+for|search\s+for\s+(.+?)\s+on\s+youtube)\s*(.+)?",
            text,
            flags=re.IGNORECASE
        )
        if yt_search_match:
            q = (yt_search_match.group(1) or yt_search_match.group(2) or "").strip()
            q = re.sub(r"^(?:like|for\s+like|some|uh|um)\s+", "", q, flags=re.IGNORECASE).strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="browser_search", params={"query": q, "engine": "youtube"})

        # 4b. Email & Gmail Checking & Opening (<0.0ms)
        if (
            re.search(r"\b(?:check|read|get|fetch|report|show|summarize|any\s+new)\s+(?:my\s+)?(?:emails?|inbox|gmail|mail)\b", text)
            or text in [
                "check email", "check emails", "check my email", "check my emails",
                "read email", "read emails", "read my emails", "email report",
                "report emails", "any emails", "emails", "my emails", "check gmail", "read gmail"
            ]
        ):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="check_emails")

        if (
            re.search(r"^(?:can\s+you\s+)?(?:open|launch|show|go\s+to|visit)\s+(?:my\s+)?(?:webmail|gmail|google\s+mail|inbox|emails?)$", text)
            or text in ["gmail", "webmail", "open gmail", "launch gmail", "show gmail"]
        ):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="open_webmail")

        # 4c. Telegram Launch & Messages (<0.0ms)
        if (
            re.search(r"^(?:can\s+you\s+)?(?:open|launch|start|show|bring\s+up|focus|switch\s+to)\s+(?:the\s+)?(?:my\s+)?telegram(?:\s+desktop|\s+messages|\s+app)?$", text)
            or re.search(r"^(?:open|launch|start|show|view|see)\s+(?:my\s+)?telegram(?:\s+messages|\s+app|\s+desktop)?$", text)
            or text in [
                "telegram", "telegram messages", "telegram app", "telegram desktop",
                "launch telegram", "open telegram", "show telegram", "start telegram",
                "launch telegram messages", "open telegram messages"
            ]
        ):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="telegram_launch")

        # 5. Direct Popular Websites (<0.0ms)
        website_match = re.search(r"^(?:open|go\s+to|visit|launch)\s+(youtube|google|reddit|github|twitter|x|netflix|amazon|twitch|wikipedia|chatgpt|spotify|gmail)(?:\.com|\.org|\.tv)?$", text)
        if website_match:
            site = website_match.group(1).strip().lower()
            site_urls = {
                "youtube": "https://youtube.com",
                "google": "https://google.com",
                "reddit": "https://reddit.com",
                "github": "https://github.com",
                "twitter": "https://x.com",
                "x": "https://x.com",
                "netflix": "https://netflix.com",
                "amazon": "https://amazon.com",
                "twitch": "https://twitch.tv",
                "wikipedia": "https://wikipedia.org",
                "chatgpt": "https://chatgpt.com",
                "spotify": "https://open.spotify.com",
                "gmail": "https://mail.google.com",
            }
            url = site_urls.get(site, f"https://{site}.com")
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="browser_open_url", params={"url": url})

        domain_match = re.match(r"^(?:open|go\s+to|visit)\s+([a-zA-Z0-9\-]+\.(?:com|org|net|io|tv|ai|gov|edu|dev|app|me)(?:/[^\s]*)?)$", text)
        if domain_match:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="browser_open_url", params={"url": "https://" + domain_match.group(1).strip()})

        # 6. General Browser Search & Web Lookups (<0.0ms)
        browser_search_match = re.search(r"(?:open\s+(?:a\s+)?browser\s+(?:and\s+search\s+for|to\s+search|to\s+look\s+for|and\s+search)|search\s+(?:google|web|the\s+web)\s+for|search\s+for|look\s+(?:in|into)\s+(?:a\s+)?browser\s+for|google)\s+(.+)", text)
        if browser_search_match:
            query = browser_search_match.group(1).strip()
            query = re.sub(r"^(?:like|for\s+like|some|uh|um)\s+", "", query, flags=re.IGNORECASE).strip()
            if query and not query.startswith("youtube"):
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="browser_search", params={"query": query, "engine": "google"})

        # 7. Filesystem: Create, Open, Write, Append, Search, Delete (<0.0ms)
        # 7a. Create file in folder: "create a file in (folder) called (name) [and open it] [with content ...]"
        create_file_in_fol = re.search(
            r"\b(?:create|make)\s+(?:a\s+)?(?:new\s+)?file\s+(?:in|inside|under)\s+(?:(?:(?:a|the)\s+)?folder\s+(?:called\s+|named\s+)?\s*)?([a-zA-Z0-9_\-\.\:\/\\]+?)\s+(?:called|named)\s+([a-zA-Z0-9_\-\.]+)(?:\s+(?:with|containing)\s+(.+?))?(?:\s+(?:and\s+)?(?:open\s+it|open))?$",
            text,
            re.I
        )
        if create_file_in_fol:
            target_loc = create_file_in_fol.group(1).strip()
            fname = create_file_in_fol.group(2).strip()
            fcontent = (create_file_in_fol.group(3) or "").strip()
            should_open = bool(re.search(r"\bopen\s+(?:it|the\s+file|that\s+file|open\s+it)\b", text, re.I))
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="create_file", params={"filename": fname, "content": fcontent, "location": target_loc, "open_after": should_open})

        # 7b. Create file called (name) in folder: "create a file called (name) in (folder) [and open it] [with content ...]"
        create_file_fol_after = re.search(
            r"\b(?:create|make)\s+(?:a\s+)?(?:new\s+)?file\s+(?:called|named)\s+([a-zA-Z0-9_\-\.]+)\s+(?:in|inside|under)\s+(?:(?:(?:a|the)\s+)?folder\s+(?:called\s+|named\s+)?\s*)?([a-zA-Z0-9_\-\.\:\/\\]+)(?:\s+(?:with|containing)\s+(.+?))?(?:\s+(?:and\s+)?(?:open\s+it|open))?$",
            text,
            re.I
        )
        if create_file_fol_after:
            fname = create_file_fol_after.group(1).strip()
            target_loc = create_file_fol_after.group(2).strip()
            fcontent = (create_file_fol_after.group(3) or "").strip()
            should_open = bool(re.search(r"\bopen\s+(?:it|the\s+file|that\s+file|open\s+it)\b", text, re.I))
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="create_file", params={"filename": fname, "content": fcontent, "location": target_loc, "open_after": should_open})

        # 7c. Standard create file: "create a file called notes.txt [with content ...]"
        create_file_match = re.search(
            r"\b(?:create|make|new)\s+(?:a\s+)?(?:new\s+)?file\s+(?:called\s+|named\s+)?([a-zA-Z0-9_\-\.]+)(?:\s+(?:with|containing)\s+(.+?))?(?:\s+(?:and\s+)?(?:open\s+it|open))?$",
            text,
            re.I
        )
        if create_file_match:
            fname = create_file_match.group(1).strip()
            fcontent = (create_file_match.group(2) or "").strip()
            should_open = bool(re.search(r"\bopen\s+(?:it|the\s+file|that\s+file|open\s+it)\b", text, re.I))
            if fname.lower() not in ["in", "on", "a", "the", "new", "folder"]:
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="create_file", params={"filename": fname, "content": fcontent, "open_after": should_open})

        create_file_direct = re.match(r"^(?:create|make)\s+([a-zA-Z0-9_\-\.]+\.(?:txt|py|md|json|csv|html|css|js))\s*(?:with\s+(.+))?$", text, re.I)
        if create_file_direct:
            fname = create_file_direct.group(1).strip()
            fcontent = (create_file_direct.group(2) or "").strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="create_file", params={"filename": fname, "content": fcontent})

        # 1. Create Folder with Specific Location: "create a folder in (bureau|desktop|documents|downloads) called <name> [and open it]"
        create_fol_loc_first = re.search(
            r"\b(?:create|make)\s+(?:a\s+)?(?:new\s+)?folder\s+(?:in|on)\s+(?:the\s+)?([a-zA-Z0-9_\-\.\:\/\\]+?)\s+(?:called|named)\s+([a-zA-Z0-9_\-\.\s]+?)(?:\s+(?:and\s+)?(?:open\s+(?:it|them|that|the\s+folder)|open\s+it))?$",
            text,
            re.I
        )
        if create_fol_loc_first:
            target_loc = create_fol_loc_first.group(1).strip()
            target_fol = create_fol_loc_first.group(2).strip()
            should_open = bool(re.search(r"\bopen\s+(?:it|them|that|the\s+folder|open\s+it)\b", text, re.I))
            act = "create_and_open_folder" if should_open else "create_folder"
            return RouteDecision(path=ExecutionPath.FAST_PATH, action=act, params={"folder_name": target_fol, "location": target_loc})

        # 2. Name first: "create a folder called <name> in (bureau|desktop|documents|downloads) [and open it]"
        create_fol_name_first = re.search(
            r"\b(?:create|make)\s+(?:a\s+)?(?:new\s+)?folder\s+(?:called\s+|named\s+)?([a-zA-Z0-9_\-\.\s]+?)\s+(?:in|on)\s+(?:the\s+)?([a-zA-Z0-9_\-\.\:\/\\]+?)(?:\s+(?:and\s+)?(?:open\s+(?:it|them|that|the\s+folder)|open\s+it))?$",
            text,
            re.I
        )
        if create_fol_name_first:
            target_fol = create_fol_name_first.group(1).strip()
            target_loc = create_fol_name_first.group(2).strip()
            if target_loc.lower() in ["bureau", "desktop", "documents", "downloads", "layadocs"] or ":" in target_loc or "/" in target_loc or "\\" in target_loc:
                should_open = bool(re.search(r"\bopen\s+(?:it|them|that|the\s+folder|open\s+it)\b", text, re.I))
                act = "create_and_open_folder" if should_open else "create_folder"
                return RouteDecision(path=ExecutionPath.FAST_PATH, action=act, params={"folder_name": target_fol, "location": target_loc})

        # 3. Create Folder and Open It (Direct Reflex)
        create_and_open = re.search(
            r"\b(?:create|make)\s+(?:a\s+)?(?:new\s+)?(?:folder\s+(?:called\s+|named\s+)?([a-zA-Z0-9_\-\.\s]+?)|folders?)\s+(?:and\s+)?(?:open\s+(?:it|them|that|the\s+folder)|open\s+it)\b",
            text,
            re.I
        )
        if create_and_open:
            fol_name = (create_and_open.group(1) or "New Folder").strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="create_and_open_folder", params={"folder_name": fol_name})

        create_folder_match = re.search(r"\b(?:create|make|new)\s+(?:a\s+)?(?:new\s+)?folder\s+(?:called\s+|named\s+)?([a-zA-Z0-9_\-\.\s]+)$", text)
        if create_folder_match:
            fol_name = create_folder_match.group(1).strip()
            if re.search(r"\s+(?:and\s+)?open\s+(?:it|them|that|the\s+folder)", fol_name, re.I):
                clean_name = re.sub(r"\s+(?:and\s+)?open\s+(?:it|them|that|the\s+folder).*", "", fol_name, flags=re.I).strip()
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="create_and_open_folder", params={"folder_name": clean_name or "New Folder"})
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="create_folder", params={"folder_name": fol_name})

        # Open Folders & Directories (<0.0ms)
        # Pronoun & Recent Folder Resolution: "open it", "open them", "open that folder", "open the created folder"
        if re.search(r"^(?:can\s+you\s+)?(?:open|launch|show|view|explore)\s+(?:it|them|that|the\s+folder|that\s+folder|the\s+created\s+folder|recent\s+folder|this\s+folder)$", text, re.I):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="open_folder", params={"folder_name": "it"})

        open_desktop_folder = re.search(
            r"^(?:can\s+you\s+)?(?:open|launch|show|view|explore)\s+(?:the\s+|a\s+)?(?:folder\s+(?:on|in)\s+(?:the\s+)?(?:desktop|bureau)|desktop\s+folder|bureau\s+folder|folder\s+in\s+(?:desktop|bureau)|folder\s+on\s+(?:desktop|bureau))$",
            text
        )
        if open_desktop_folder or text in ["open desktop", "open the desktop", "show desktop folder", "desktop folder", "open bureau", "open the bureau", "bureau folder", "show bureau"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="open_folder", params={"folder_name": "desktop"})

        open_folder_named = re.search(
            r"^(?:can\s+you\s+)?(?:open|launch|show|view|explore)\s+(?:the\s+|a\s+)?folder\s+([a-zA-Z0-9_\-\.\s]+?)(?:\s+(?:on|in)\s+(?:the\s+)?desktop)?$",
            text
        )
        if open_folder_named:
            f_name = open_folder_named.group(1).strip()
            if f_name not in ["this", "it", "that", "them", "an app", "app"]:
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="open_folder", params={"folder_name": f_name})

        open_folder_suffix = re.search(
            r"^(?:can\s+you\s+)?(?:open|launch|show|view|explore)\s+(?:the\s+|a\s+)?([a-zA-Z0-9_\-\.\s]+?)\s+folder$",
            text
        )
        if open_folder_suffix:
            f_name = open_folder_suffix.group(1).strip()
            if f_name not in ["this", "it", "that", "them", "an app", "app"]:
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="open_folder", params={"folder_name": f_name})

        # 7d. Write to file / Write to it:
        write_to_it = re.search(r"^(?:write|overwrite)\s+(?:to\s+(?:it|the\s+file|that\s+file)\s*(?::\s*|\s+)?|into\s+(?:it|the\s+file|that\s+file)\s*(?::\s*|\s+)?)(.+)$", text, re.I)
        if write_to_it:
            content = write_to_it.group(1).strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="write_to_file", params={"filename": "it", "content": content})

        write_suffix_it = re.search(r"^(?:write|overwrite)\s+(.+?)\s+(?:to|into|in)\s+(?:it|the\s+file|that\s+file)$", text, re.I)
        if write_suffix_it:
            content = write_suffix_it.group(1).strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="write_to_file", params={"filename": "it", "content": content})

        # 7e. Append to file / Append to it:
        append_to_it = re.search(r"^(?:append|add)\s+(?:to\s+(?:it|the\s+file|that\s+file)\s*(?::\s*|\s+)?|into\s+(?:it|the\s+file|that\s+file)\s*(?::\s*|\s+)?)(.+)$", text, re.I)
        if append_to_it:
            content = append_to_it.group(1).strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="append_to_file", params={"filename_or_path": "it", "content": content})

        append_suffix_it = re.search(r"^(?:append|add)\s+(.+?)\s+(?:to|into|in)\s+(?:it|the\s+file|that\s+file)$", text, re.I)
        if append_suffix_it:
            content = append_suffix_it.group(1).strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="append_to_file", params={"filename_or_path": "it", "content": content})

        # Standard write with explicit target filename:
        write_file_match = re.search(r"\b(?:write|append|add|put)\s+(.+?)\s+(?:to|into|in)\s+(?:(?:the\s+)?file\s+([a-zA-Z0-9_\-\.\/\\]+)|([a-zA-Z0-9_\-\.\/\\]+\.[a-zA-Z0-9]{1,5}))$", text, re.I)
        if write_file_match:
            content = write_file_match.group(1).strip()
            target_f = (write_file_match.group(2) or write_file_match.group(3) or "").strip()
            if target_f and target_f.lower() not in ["sleep", "lock", "screen", "display", "mute", "sound", "volume"]:
                act = "append_to_file" if "append" in text.lower() else "write_to_file"
                return RouteDecision(path=ExecutionPath.FAST_PATH, action=act, params={"filename": target_f, "content": content} if act == "write_to_file" else {"filename_or_path": target_f, "content": content})

        # 7f. Delete file: "delete it", "delete the file", "delete file <name>"
        if text.strip().lower() in ["delete it", "delete the file", "delete that file", "remove it", "remove the file"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="delete_file", params={"filename_or_path": "it"})

        delete_file_match = re.search(r"\b(?:delete|remove)\s+(?:the\s+)?file\s+(.+)$", text, re.I)
        if delete_file_match:
            target_f = delete_file_match.group(1).strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="delete_file", params={"filename_or_path": target_f})

        # 7g. Open file: "open the file", "open file <name>"
        if text.strip().lower() in ["open the file", "open that file", "open file"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="open_file", params={"filename_or_path": "it"})

        open_file_match = re.search(r"\b(?:open|read|view|show)\s+(?:the\s+)?file\s+(.+)$", text, re.I)
        if open_file_match:
            target_f = open_file_match.group(1).strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="open_file", params={"filename_or_path": target_f})

        search_file_match = re.search(r"\b(?:search\s+(?:for\s+)?(?:files?|folders?|documents?)|find\s+(?:file|folder)|locate\s+(?:file|folder))\s+(?:called\s+|named\s+)?([^\s,]+)", text)
        if search_file_match:
            pat = search_file_match.group(1).strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="search_files", params={"pattern": pat})

        search_win_match = re.search(r"\bsearch\s+(?:in\s+windows|in\s+folders?|windows|folders?)\s+(?:for\s+)?(.+)", text)
        if search_win_match:
            pat = search_win_match.group(1).strip()
            pat = re.sub(r"^for\s+", "", pat).strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="search_files", params={"pattern": pat})

        # 8. WhatsApp & Telegram Calling & Messaging (<0.0ms)
        # WhatsApp Calling
        wa_call_match = re.search(r"\b(?:make\s+a\s+)?(?:voice\s+|video\s+)?(?:call|ring|phone)\s+(?:to\s+)?(.+?)\s+(?:on|via|through)\s+whatsapp\b|\b(?:make\s+a\s+)?whatsapp\s+(?:voice\s+|video\s+)?call\s+(?:to\s+)?(.+)\b", text, re.I)
        if wa_call_match:
            target_c = (wa_call_match.group(1) or wa_call_match.group(2) or "").strip()
            call_type = "video" if "video" in text.lower() else "voice"
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="whatsapp_call", params={"contact": target_c, "call_type": call_type})

        # Telegram Calling
        tg_call_match = re.search(r"\b(?:make\s+a\s+)?(?:voice\s+|video\s+)?(?:call|ring|phone)\s+(?:to\s+)?(.+?)\s+(?:on|via|through)\s+telegram\b|\b(?:make\s+a\s+)?telegram\s+(?:voice\s+|video\s+)?call\s+(?:to\s+)?(.+)\b", text, re.I)
        if tg_call_match:
            target_c = (tg_call_match.group(1) or tg_call_match.group(2) or "").strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="telegram_call", params={"contact": target_c})

        # Broadcast Message to All Contacts / Users (<0.0ms)
        is_broadcast = bool(
            re.search(r"\b(?:broadcast|all\s+contacts|all\s+users|everyone|everybody|all\s+my\s+contacts)\b", text, re.I)
            and (
                re.search(r"\b(?:send|broadcast|message|messages|text|texts|tell|post|blast)\b", text, re.I)
                or "to all" in text
                or "to everyone" in text
                or "to everybody" in text
            )
        )
        if is_broadcast:
            # Extract message content if provided
            msg_m = re.search(r"(?:saying|that|with|say|:\s*)\s+(.+)$", text, re.I)
            b_msg = ""
            if msg_m:
                b_msg = msg_m.group(1).strip().strip(":'\" ")
                b_msg = re.sub(r"\s+(?:on|in|via)\s+telegram$", "", b_msg, flags=re.I).strip()
            if not b_msg:
                tg_colon_m = re.search(r"(?:on|to|in)?\s*telegram\s*[:]\s*(.+)$", text, re.I)
                if tg_colon_m:
                    b_msg = tg_colon_m.group(1).strip().strip(":'\" ")

            if b_msg:
                return RouteDecision(
                    path=ExecutionPath.FAST_PATH,
                    action="telegram_broadcast",
                    params={"message": b_msg},
                    confidence=1.0,
                    reasoning="Fast-path Telegram broadcast to all contacts/users."
                )
            else:
                return RouteDecision(
                    path=ExecutionPath.CLARIFY,
                    action="none",
                    clarification_prompt="What message would you like me to broadcast to all contacts?",
                    confidence=1.0,
                    reasoning="Instant clarification for missing broadcast message content."
                )

        # Telegram Setup & Credential Input (<0.0ms)
        if re.search(r"\b(?:login\s+to|connect|setup|authenticate)\s+telegram\b", text, re.I):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="telegram_launch_login")

        cred_match = re.search(r"(?:api\s+id|telegram\s+id)\s*(?:is\s*|:\s*|=\s*)?(\d+).*(?:api\s+hash|hash)\s*(?:is\s*|:\s*|=\s*)?([a-fA-F0-9]{20,})", text, re.I)
        if cred_match:
            return RouteDecision(
                path=ExecutionPath.FAST_PATH,
                action="telegram_save_credentials",
                params={"api_id": cred_match.group(1).strip(), "api_hash": cred_match.group(2).strip()}
            )

        # Telegram Contacts Management (Sync, List) (<0.0ms)
        if re.search(r"\b(?:sync|import|download|fetch|update)\s+(?:all\s+)?(?:telegram\s+)?contacts\b", text, re.I):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="telegram_sync_contacts")

        if re.search(r"\b(?:telegram\s+contacts|contacts\s+(?:in|on)\s+telegram|who\s+are\s+my\s+telegram\s+contacts|all\s+telegram\s+contacts|(?:list|show|view|get|display)\s+(?:all\s+)?telegram\s+contacts)\b", text, re.I):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="telegram_list_contacts")

        # WhatsApp Messaging (<0.0ms)
        wa_direct_latest = re.search(r"\b(?:send\s+(?:a\s+)?whatsapp(?:\s+message|\s+text)?|send\s+(?:a\s+)?(?:message|text)\s+(?:on|via|in|through)\s+whatsapp)\s*(?:saying|that|with|:)\s*(.+)$", text, re.I)
        if wa_direct_latest:
            target_m = (wa_direct_latest.group(1) or "").strip().strip(":'\" ")
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="whatsapp_message", params={"contact": "latest conversation", "message": target_m or "Hello!"})

        wa_msg_match = (
            re.search(r"\b(?:send\s+(?:a\s+)?whatsapp(?:\s+message|\s+text)?\s+to\s+)([a-zA-Z0-9_@\+\s]+?)(?:\s*(?:saying|that|with|:)\s*|\s*:\s*|\s+)(.+)$", text, re.I)
            or re.search(r"\b(?:send\s+(?:a\s+)?(?:message|text)\s+(?:on|via|in|through)\s+whatsapp\s+to\s+)([a-zA-Z0-9_@\+\s]+?)(?:\s*(?:saying|that|with|:)\s*|\s*:\s*|\s+)(.+)$", text, re.I)
            or re.search(r"\b(?:send\s+(?:a\s+)?(?:message|text)\s+to\s+)([a-zA-Z0-9_@\+\s]+?)\s+(?:on|via|in|through)\s+whatsapp(?:\s*(?:saying|that|with|:)\s*|\s*:\s*|\s+)(.+)$", text, re.I)
            or re.search(r"\b(?:message|text|tell)\s+([a-zA-Z0-9_@\+\s]+?)\s+(?:on|via|in|through)\s+whatsapp(?:\s*(?:saying|that|with|:)\s*|\s*:\s*|\s+)(.+)$", text, re.I)
            or re.search(r"\b(?:send\s+(?:a\s+)?whatsapp(?:\s+message|\s+text)?\s+to\s+)([a-zA-Z0-9_@\+\s]+)$", text, re.I)
            or re.search(r"\bwhatsapp\s+(?!call|video|voice|web)([a-zA-Z0-9_@\+\s]+?)(?:\s*(?:saying|that|with|:)\s*|\s*:\s*|\s+)(.+)$", text, re.I)
        )
        if wa_msg_match:
            target_c = wa_msg_match.group(1).strip()
            target_m = (wa_msg_match.group(2) or "").strip().strip(":'\" ") if (wa_msg_match.lastindex and wa_msg_match.lastindex >= 2) else ""
            if target_c.lower() not in ["message", "a message", "text", "a text", "call", "voice call", "video call"]:
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="whatsapp_message", params={"contact": target_c, "message": target_m or "Hello!"})

        # Telegram Messaging (<0.0ms)
        tg_direct_latest = re.search(r"\b(?:send\s+(?:a\s+)?telegram(?:\s+message|\s+text)?|send\s+(?:a\s+)?(?:message|text)\s+(?:on|via|in|through)\s+telegram)\s*(?:saying|that|with|:)\s*(.+)$", text, re.I)
        if tg_direct_latest:
            target_m = (tg_direct_latest.group(1) or "").strip().strip(":'\" ")
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="telegram_send_message", params={"recipient": "latest conversation", "message": target_m or "Hello!"})

        tg_msg_match = (
            re.search(r"\b(?:send\s+(?:a\s+)?telegram(?:\s+message|\s+text)?\s+to\s+)([a-zA-Z0-9_@\+\s]+?)(?:\s*(?:saying|that|with|:)\s*|\s*:\s*|\s+)(.+)$", text, re.I)
            or re.search(r"\b(?:send\s+(?:a\s+)?(?:message|text)\s+(?:on|via|in|through)\s+telegram\s+to\s+)([a-zA-Z0-9_@\+\s]+?)(?:\s*(?:saying|that|with|:)\s*|\s*:\s*|\s+)(.+)$", text, re.I)
            or re.search(r"\b(?:send\s+(?:a\s+)?(?:message|text)\s+to\s+)([a-zA-Z0-9_@\+\s]+?)\s+(?:on|via|in|through)\s+telegram(?:\s*(?:saying|that|with|:)\s*|\s*:\s*|\s+)(.+)$", text, re.I)
            or re.search(r"\b(?:message|text|tell)\s+([a-zA-Z0-9_@\+\s]+?)\s+(?:on|via|in|through)\s+telegram(?:\s*(?:saying|that|with|:)\s*|\s*:\s*|\s+)(.+)$", text, re.I)
            or re.search(r"\b(?:send\s+(?:a\s+)?telegram(?:\s+message|\s+text)?\s+to\s+)([a-zA-Z0-9_@\+\s]+)$", text, re.I)
            or re.search(r"\btelegram\s+(?!call|video|voice|for|messages?|contacts?|search)([a-zA-Z0-9_@\+\s]+?)(?:\s*(?:saying|that|with|:)\s*|\s*:\s*|\s+)(.+)$", text, re.I)
        )
        if tg_msg_match:
            target_c = tg_msg_match.group(1).strip()
            target_m = (tg_msg_match.group(2) or "").strip().strip(":'\" ") if (tg_msg_match.lastindex and tg_msg_match.lastindex >= 2) else ""
            if target_c.lower() in ["all", "everyone", "all contacts", "all my contacts", "all users", "everybody", "to all contacts", "users", "contacts"]:
                if not target_m:
                    return RouteDecision(
                        path=ExecutionPath.CLARIFY,
                        action="none",
                        clarification_prompt="What message would you like me to broadcast to all contacts?",
                        confidence=1.0,
                        reasoning="Clarification for missing broadcast message content."
                    )
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="telegram_broadcast", params={"message": target_m})
            if target_c.lower() not in ["message", "a message", "text", "a text", "call", "voice call", "video call"]:
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="telegram_send_message", params={"recipient": target_c, "message": target_m or "Hello!"})

        # Underspecified Messaging Prompts (<0.0ms Clarification, NEVER list contacts)
        if text in [
            "send something", "send a message", "send message", "send a text", "send text",
            "text someone", "write a message", "send a telegram", "send a whatsapp",
            "send something to someone", "send message to someone", "send text to someone",
            "send a text to someone", "send some text", "send msg"
        ]:
            return RouteDecision(
                path=ExecutionPath.CLARIFY,
                action="none",
                clarification_prompt="Who would you like me to message, and what should I say?",
                confidence=1.0,
                reasoning="Instant clarification for underspecified messaging request."
            )

        # ---------------------------------------------------------
        # Timers, Reminders & Tasks (<0.0ms Fast Path)
        # ---------------------------------------------------------
        # Word numbers converter for speech
        WORD_NUMS = {
            "one": 1.0, "two": 2.0, "three": 3.0, "four": 4.0, "five": 5.0, "six": 6.0, "seven": 7.0,
            "eight": 8.0, "nine": 9.0, "ten": 10.0, "eleven": 11.0, "twelve": 12.0, "fifteen": 15.0,
            "twenty": 20.0, "twenty five": 25.0, "thirty": 30.0, "forty": 40.0, "forty five": 45.0,
            "fifty": 50.0, "sixty": 60.0, "half an": 0.5, "half a": 0.5, "half": 0.5, "an": 1.0, "a": 1.0
        }
        def _to_num(v: str) -> float:
            v_clean = (v or "").lower().strip()
            if v_clean in WORD_NUMS:
                return WORD_NUMS[v_clean]
            try:
                return float(v_clean)
            except ValueError:
                return 0.0

        # 1. Timer / Reminder cancellation
        if re.search(r"\b(?:cancel|stop|clear|delete|remove)\s+(?:all\s+)?(?:the\s+)?(?:timers?|reminders?)\b", text, re.I) or text in [
            "cancel timer", "cancel timers", "stop timer", "stop the timer", "clear timers", "cancel all timers",
            "cancel reminder", "cancel reminders", "stop reminder", "clear reminders", "cancel all reminders"
        ]:
            cancel_match = re.search(r"\b(?:cancel|stop|clear|delete|remove)\s+(?:the\s+)?(?:timer|reminder)\s+(?:for\s+|called\s+|about\s+)?(.+)$", text, re.I)
            query_filter = cancel_match.group(1).strip() if cancel_match else ""
            if query_filter.lower() in ["all", "everything", "all timers", "all reminders"]:
                query_filter = "all"
            return RouteDecision(
                path=ExecutionPath.FAST_PATH,
                action="cancel_reminders",
                params={"query": query_filter},
                confidence=1.0,
                reasoning="Instant timer/reminder cancellation."
            )

        # 2. List Timers / Reminders
        if (
            re.search(r"^(?:list|show|view|get|check|what\s+are)(?:\s+(?:all|my|active|pending))?\s+(?:timers?|reminders?)$", text, re.I)
            or text in ["timers", "my timers", "reminders", "my reminders", "what are my reminders", "what are my timers", "active timers", "active reminders"]
        ):
            return RouteDecision(
                path=ExecutionPath.FAST_PATH,
                action="list_reminders",
                confidence=1.0,
                reasoning="Instant timer/reminder listing."
            )

        # 3. Bare timer without duration (Clarification reflex: NEVER fail or suggest external app)
        if re.search(r"^(?:(?:can|could|would)\s+you\s+(?:please\s+)?|please\s+)?(?:set(?:\s+me|\s+us)?|start|create|make|put(?:\s+on)?|give\s+me)?\s*(?:a\s+)?timer$", text, re.I) or text.strip().lower() in ["set a timer", "start a timer", "timer", "set timer", "make a timer", "put a timer", "set me a timer"]:
            return RouteDecision(
                path=ExecutionPath.CLARIFY,
                action="clarify",
                clarification_prompt="How many minutes or seconds should I set the timer for?",
                confidence=1.0,
                reasoning="Clarifying timer duration."
            )

        # 4. Time-first timer: "set a 5 minute timer [for pasta]", "start a 10 min timer", "5 minute timer", "10 min timer"
        t_first_match = re.search(
            r"^(?:(?:can|could|would)\s+you\s+(?:please\s+)?|please\s+)?(?:set(?:\s+me|\s+us)?|start|create|make|put(?:\s+on)?|give\s+me)?\s*(?:a\s+)?(\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty|fifty|half\s+an|half\s+a|half|an|a)\s*(seconds?|secs?|minutes?|mins?|hours?|hrs?)\s+timer(?:\s+(?:for|to|called|named|about)\s+(.+))?$",
            text,
            re.I
        )
        if t_first_match:
            n_val = _to_num(t_first_match.group(1))
            unit = t_first_match.group(2).lower()
            label = (t_first_match.group(3) or "timer").strip()
            secs = n_val if "sec" in unit else 0.0
            mins = n_val if "min" in unit else 0.0
            hrs = n_val if "hour" in unit or "hr" in unit else 0.0
            return RouteDecision(
                path=ExecutionPath.FAST_PATH,
                action="set_reminder",
                params={"message": f"Timer: {label}", "seconds": secs, "minutes": mins, "hours": hrs},
                confidence=1.0,
                reasoning="Instant time-first timer."
            )

        # 5. Standard timer: "set a timer for 5 minutes", "set me a timer for 10 minutes", "put a timer for 5 minutes", "timer for 10 minutes", "timer 5 mins"
        t_std_match = re.search(
            r"^(?:(?:can|could|would)\s+you\s+(?:please\s+)?|please\s+)?(?:set(?:\s+me|\s+us)?|start|create|make|put(?:\s+on)?|give\s+me|timer)(?:\s+(?:a\s+)?timer)?(?:\s+(?:for|of|at|to|in))?\s+(\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty|fifty|half\s+an|half\s+a|half|an|a)\s*(seconds?|secs?|minutes?|mins?|hours?|hrs?)(?:\s+(?:for|to|called|named|about)\s+(.+))?$",
            text,
            re.I
        )
        if t_std_match:
            n_val = _to_num(t_std_match.group(1))
            unit = t_std_match.group(2).lower()
            label = (t_std_match.group(3) or "timer").strip()
            secs = n_val if "sec" in unit else 0.0
            mins = n_val if "min" in unit else 0.0
            hrs = n_val if "hour" in unit or "hr" in unit else 0.0
            return RouteDecision(
                path=ExecutionPath.FAST_PATH,
                action="set_reminder",
                params={"message": f"Timer: {label}", "seconds": secs, "minutes": mins, "hours": hrs},
                confidence=1.0,
                reasoning="Instant standard timer scheduling."
            )

        # 6. Natural Language Reminders: "remind me in 5 minutes to check the oven", "in 10 minutes remind me to call mom", "remind me tomorrow at 3pm to call the doctor"
        r_time_first = re.search(
            r"^(?:can\s+you\s+|please\s+)?(?:remind\s+(?:me\s+)?in|in)\s+(\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|fifteen|twenty|thirty)\s*(seconds?|secs?|minutes?|mins?|hours?|hrs?)\s+(?:remind\s+me\s+)?(?:to\s+|about\s+)(.+)$",
            text,
            re.I
        )
        if r_time_first:
            n_val = _to_num(r_time_first.group(1))
            unit = r_time_first.group(2).lower()
            msg = r_time_first.group(3).strip()
            secs = n_val if "sec" in unit else 0.0
            mins = n_val if "min" in unit else 0.0
            hrs = n_val if "hour" in unit or "hr" in unit else 0.0
            return RouteDecision(
                path=ExecutionPath.FAST_PATH,
                action="set_reminder",
                params={"message": msg, "seconds": secs, "minutes": mins, "hours": hrs},
                confidence=1.0,
                reasoning="Instant time-first reminder."
            )

        r_std_match = re.search(
            r"^(?:can\s+you\s+|please\s+)?(?:remind\s+(?:me\s+)?(?:to\s+|about\s+)?|set\s+(?:a\s+)?reminder\s+(?:to\s+|for\s+)?)(.+?)\s+(?:in|after)\s+(\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|fifteen|twenty|thirty)\s*(seconds?|secs?|minutes?|mins?|hours?|hrs?)$",
            text,
            re.I
        )
        if r_std_match:
            rem_msg = r_std_match.group(1).strip()
            num_val = _to_num(r_std_match.group(2))
            unit = r_std_match.group(3).lower()
            secs = num_val if "sec" in unit else 0.0
            mins = num_val if "min" in unit else 0.0
            hrs = num_val if "hour" in unit or "hr" in unit else 0.0
            return RouteDecision(
                path=ExecutionPath.FAST_PATH,
                action="set_reminder",
                params={"message": rem_msg, "seconds": secs, "minutes": mins, "hours": hrs},
                confidence=1.0,
                reasoning="Instant timed reminder scheduling."
            )

        # 7. Natural date/time reminders: "remind me tomorrow at 3pm to call mom", "remind me to call Marcus at 6pm"
        r_natural_match = re.search(
            r"^(?:can\s+you\s+|please\s+)?(?:remind\s+me|set\s+(?:a\s+)?reminder)\s+(?:to\s+|about\s+)?(.+)$",
            text,
            re.I
        )
        if r_natural_match:
            rem_body = r_natural_match.group(1).strip()
            # If it mentions time keywords (tomorrow, today, tonight, at, pm, am, o'clock)
            if re.search(r"\b(?:tomorrow|today|tonight|at\s+\d+|in\s+\d+|am\b|pm\b|o'clock)\b", rem_body, re.I):
                return RouteDecision(
                    path=ExecutionPath.FAST_PATH,
                    action="set_reminder",
                    params={"message": rem_body, "seconds": 0, "minutes": 0, "hours": 0},
                    confidence=1.0,
                    reasoning="Instant natural-language reminder scheduling."
                )

        # 8. Task & Todo Management (<0.0ms)
        if text.strip().lower() in ["my tasks", "list tasks", "show tasks", "tasks", "what are my tasks", "view tasks", "pending tasks", "get tasks"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="list_tasks", params={"status": "all"})

        complete_task_match = re.search(r"\b(?:complete|finish|done|check\s+off|mark)\s+(?:the\s+)?task\s+(?:called\s+|named\s+)?(.+?)(?:\s+(?:as\s+)?(?:done|completed))?$", text, re.I)
        if complete_task_match:
            query = complete_task_match.group(1).strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="complete_task", params={"query": query})

        add_task_match = re.search(r"\b(?:add|create|new|schedule)\s+(?:a\s+)?task\s+(?:to\s+|called\s+|for\s+)?(.+)$", text, re.I)
        if add_task_match:
            t_title = add_task_match.group(1).strip()
            due_date = ""
            due_match = re.search(r"\s+(?:due\s+|by\s+)(tomorrow|today|next\s+week|monday|tuesday|wednesday|thursday|friday|saturday|sunday)$", t_title, re.I)
            if due_match:
                due_date = due_match.group(1).strip()
                t_title = t_title[:due_match.start()].strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="add_task", params={"title": t_title, "due_date": due_date})

        # 9. Memory Wipe & Reset
        if text.strip().lower() in ["clear memory", "reset memory", "wipe memory", "forget everything", "clear my memory", "reset my memory"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="clear_memory", params={})

        # Universal Cross-Platform Messaging (Telegram / WhatsApp) (<0.0ms)
        gen_msg_match = re.search(
            r"\b(?:send\s+(?:a\s+)?(?:message|text|something)\s+to|message|text|tell)\s+([a-zA-Z0-9_\-\.]+)(?:\s*(?:saying|that|with|:)\s*|\s*:\s*|\s+)(.*)$",
            text,
            re.I
        )
        if gen_msg_match:
            target_c = gen_msg_match.group(1).strip()
            target_m = (gen_msg_match.group(2) or "").strip().strip(":'\" ")
            if target_c.lower() in ["all", "everyone", "everybody", "all contacts", "all users", "all my contacts", "to all contacts", "users", "contacts"]:
                if not target_m:
                    return RouteDecision(
                        path=ExecutionPath.CLARIFY,
                        action="none",
                        clarification_prompt="What message would you like me to broadcast to all contacts?",
                        confidence=1.0,
                        reasoning="Clarification for missing broadcast message content."
                    )
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="telegram_broadcast", params={"message": target_m})

            if target_c.lower() not in ["me", "i", "it", "my", "the", "a", "someone", "joke", "story", "time", "date"]:
                if not target_m:
                    return RouteDecision(
                        path=ExecutionPath.CLARIFY,
                        action="none",
                        clarification_prompt=f"What message would you like me to send to {target_c}?",
                        confidence=1.0,
                        reasoning=f"Clarification for missing message body for {target_c}."
                    )
                return RouteDecision(
                    path=ExecutionPath.FAST_PATH,
                    action="send_message",
                    params={"recipient": target_c, "message": target_m}
                )

        # Contact Store Management (Add, Find, List, Delete) (<0.0ms)
        contact_del_match = re.search(r"\b(?:delete|remove)\s+contact\s+([a-zA-Z0-9_\-\.\s]+)$", text, re.I)
        if contact_del_match:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="contact_delete", params={"name": contact_del_match.group(1).strip()})

        contact_find_match = re.search(r"\b(?:find|search|lookup|who\s+is)\s+contact\s+([a-zA-Z0-9_\-\.\s]+)$", text, re.I)
        if contact_find_match:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="contact_find", params={"query": contact_find_match.group(1).strip()})

        if text in ["list contacts", "show contacts", "show my contacts", "all contacts", "my contacts", "get contacts"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="contact_list")

        contact_add_match = re.search(r"\b(?:add|create|save|new)\s+contact\s+([a-zA-Z0-9_\-\.\s]+?)(?:\s+with\s+|\s+phone\s+|\s+telegram\s+|\s+number\s+|$)(.*)", text, re.I)
        if contact_add_match and "contact" in text:
            c_name = contact_add_match.group(1).strip()
            c_rest = contact_add_match.group(2).strip()
            phone_m = re.search(r"(?:phone|number|mobile)\s*[:=]?\s*([+\d\s\-]+)", c_rest, re.I)
            tg_m = re.search(r"(?:telegram|tg)\s*[:=]?\s*@?([a-zA-Z0-9_]+)", c_rest, re.I)
            phone_val = phone_m.group(1).strip() if phone_m else ""
            tg_val = tg_m.group(1).strip() if tg_m else ""
            if not phone_val and re.search(r"[+\d]{7,}", c_rest):
                phone_val = re.search(r"[+\d]{7,}", c_rest).group(0)
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="contact_add", params={"name": c_name, "phone": phone_val, "telegram": tg_val})

        # Editor Line Navigation (<0.0ms)
        jump_match = re.search(r"\b(?:jump\s+to|go\s+to|navigate\s+to)\s+(?:the\s+)?line\s+(\d+)(?:\s+(?:in|of)\s+([a-zA-Z0-9\s_\-\.]+))?", text, re.I)
        if jump_match:
            line_num = int(jump_match.group(1))
            target_win = (jump_match.group(2) or "").strip()
            return RouteDecision(
                path=ExecutionPath.FAST_PATH,
                action="jump_to_line",
                params={"line_number": line_num, "title_keyword": target_win},
                confidence=1.0,
                reasoning="Instant editor line jump navigation via Ctrl+G."
            )

        # 9. App Shifting, Window Splitting & Geometry (<0.0ms)
        shift_app_match = re.search(r"\b(?:shift\s+to|switch\s+to|focus|bring\s+up|go\s+to|bring\s+to\s+front)\s+(?:the\s+)?([a-zA-Z0-9\s_\-\.]+?)(?:\s+window|\s+app)?$", text)
        if shift_app_match:
            target_app = shift_app_match.group(1).strip()
            if target_app not in ["this", "it", "window", "app"]:
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="shift_to_app", params={"app_or_title": target_app})

        split_match = re.search(r"\b(?:split\s+screens?|split\s+the\s+screen|tile\s+windows?|side\s+by\s+side|organize\s+(?:my\s+|the\s+)?windows?|arrange\s+(?:my\s+|the\s+)?windows?)\b", text)
        if split_match:
            layout = "split" if any(w in text for w in ["split", "side by side", "tile"]) else "grid"
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="split_screen", params={"layout": layout})

        # 9b. Window Scrolling & Zooming Navigation (<0.0ms)
        if text.strip().lower() in ["scroll down", "scroll up", "scroll to top", "scroll to bottom", "scroll left", "scroll right", "page down", "page up"]:
            direction = "down" if "down" in text.lower() else ("up" if "up" in text.lower() else "top")
            return RouteDecision(
                path=ExecutionPath.FAST_PATH,
                action="scroll_window",
                params={"direction": direction, "amount": 5, "title_keyword": ""},
                confidence=1.0,
                reasoning="Instant window scroll navigation."
            )

        scroll_match = re.search(
            r"\b(?:scroll|page)\s+(down|up|left|right|top|bottom|beginning|end|to\s+the\s+top|to\s+the\s+bottom)(?:\s+(?:by|for)?\s*(\d+)\s*(?:times|notches|clicks|steps)?)?(?:\s+(?:in|on|inside)\s+(?:the\s+)?([a-zA-Z0-9\s_\-\.]+?))?(?:\s+(?:a\s+bit|a\s+little|more|please|now))?$",
            text,
            flags=re.IGNORECASE
        )
        if scroll_match:
            raw_dir = scroll_match.group(1).lower().replace("to the ", "").strip()
            raw_amount = int(scroll_match.group(2)) if scroll_match.group(2) else 5
            raw_win = (scroll_match.group(3) or "").strip()
            if raw_win in ["window", "screen", "page", "it", "this"]:
                raw_win = ""
            return RouteDecision(
                path=ExecutionPath.FAST_PATH,
                action="scroll_window",
                params={"direction": raw_dir, "amount": raw_amount, "title_keyword": raw_win},
                confidence=1.0,
                reasoning="Instant window scroll navigation."
            )

        zoom_match = re.search(
            r"\bzoom\s+(?:in|into)\s*(?:on\s+|to\s+)?(?:the\s+)?(corner|top\s+left|top\s+right|bottom\s+left|bottom\s+right|middle|center|left|right|top|bottom)?(?:\s+(?:by|at)?\s*([0-9\.]+)\s*x)?(?:\s+(?:in|on|inside)\s+(?:the\s+)?([a-zA-Z0-9\s_\-\.]+?))?$",
            text,
            flags=re.IGNORECASE
        )
        if zoom_match:
            raw_reg = (zoom_match.group(1) or "center").strip()
            raw_factor = float(zoom_match.group(2)) if zoom_match.group(2) else 2.0
            raw_win = (zoom_match.group(3) or "").strip()
            if raw_win in ["window", "screen", "page", "it", "this"]:
                raw_win = ""
            return RouteDecision(
                path=ExecutionPath.FAST_PATH,
                action="zoom_window_region",
                params={"region": raw_reg, "zoom_factor": raw_factor, "title_keyword": raw_win},
                confidence=1.0,
                reasoning="Instant window zoom navigation."
            )

        # 10. Direct Math & Calculations (<0.1ms)
        if any(text.startswith(p) for p in ["what is ", "calculate ", "how much is ", "eval "]):
            expr = re.sub(r"^(?:what\s+is|calculate|how\s+much\s+is|eval)\s+", "", text).strip("? ")
            if re.search(r"\d+", expr) and any(op in expr for op in ["+", "-", "*", "/", "times", "divided", "plus", "minus", "x", "^", "%"]):
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="calculate_math", params={"expression": expr})

        # 11. Direct Text Typing & Key Pressing (<0.1ms)
        type_match = re.match(r"^(?:can\s+you\s+)?(?:type|write|enter|paste|input)\s+(?:the\s+words?\s+|the\s+text\s+|words?\s+|text\s+)?(.+)$", text)
        if type_match:
            raw_text = type_match.group(1).strip()
            if not any(raw_text.startswith(w) for w in ["an email", "email", "a letter", "code", "a script", "a story", "an essay", "notebook", "a post", "a document", "to file", "into file"]):
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="type_text", params={"text": raw_text})

        key_match = re.match(r"^(?:press|hit)\s+(?:the\s+)?(enter|return|space|tab|escape|esc|backspace|delete)$", text)
        if key_match:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="press_key", params={"key": key_match.group(1).strip()})

        # 12. Drawing Autonomy (<0.0ms)
        draw_match = re.search(r"\b(?:draw|paint|sketch)\s+(?:a\s+|an\s+)?([a-z]+(?:\s+[a-z]+)?)\s*(?:in\s+paint|on\s+paint)?\b", text)
        if draw_match:
            raw_shape = draw_match.group(1).strip()
            for s in ["circle", "heart", "star", "square", "triangle", "oval", "rectangle", "spiral", "smiley", "flower"]:
                if s in raw_shape:
                    return RouteDecision(path=ExecutionPath.FAST_PATH, action="draw_shape", params={"shape": s, "title_keyword": "Paint"})

        # 13. Window Close & Window Management (<0.0ms)
        if (
            re.search(r"^(?:can\s+you\s+)?(?:close|quit|exit|shut\s+down|kill)\s+(?:all\s+the\s+|all\s+)?(?:applications?|apps?|windows?|programs?)$", text)
            or text in ["close all", "close all apps", "close all windows", "close all applications", "quit all apps", "exit all", "close everything", "close all programs", "close the apps", "close all the application"]
        ):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="close_all_apps")

        if text in ["close this", "close this window", "close active window", "close window"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="close_active_window")

        # History & Past Queries (<0.0ms)
        if (
            re.search(r"\b(?:check|show|view|display|what\s+is)\s+(?:the\s+)?(?:conversation\s+)?history\b", text)
            or re.search(r"\bwhat\s+did\s+i\s+(?:ask|say)(?:\s+(?:earlier|before|previously|last))?\b", text)
            or any(p in text for p in ["check history", "check the history", "show history", "show the history", "what did i ask", "what did i say", "what was my last command", "repeat my last command"])
        ):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="get_conversation_history")

        # User Memory & Experience Recall (<0.0ms)
        if (
            re.search(r"\b(?:who\s+am\s+i|who\s+am\s+i\s+exactly|do\s+you\s+know\s+who\s+i\s+am|tell\s+me\s+about\s+myself|what\s+do\s+you\s+know\s+about\s+me|what\s+is\s+my\s+name|what['']s\s+my\s+name|my\s+profile)\b", text, re.I)
            or text in ["who am i", "who am i exactly", "what is my name", "whats my name", "what's my name", "tell me about myself", "do you remember me", "what do you know about me"]
        ):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="who_am_i", confidence=1.0, reasoning="Instant user identity recall.")

        if (
            re.search(r"\b(?:who\s+are\s+you|what\s+is\s+your\s+name|what['']s\s+your\s+name|what\s+can\s+you\s+do|introduce\s+yourself)\b", text, re.I)
            or text in ["who are you", "what are you", "what is your name", "whats your name", "what's your name", "introduce yourself"]
        ):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="query_identity", confidence=1.0, reasoning="Instant assistant identity response.")

        # User Facts & Preferences Memorization (<0.0ms)
        name_stmt = re.search(r"^(?:my\s+name\s+is|call\s+me|i\s+am\s+called)\s+([a-zA-Z\s\-]+)$", text, re.I)
        if name_stmt:
            u_name = name_stmt.group(1).strip()
            if u_name.lower() not in ["ready", "done", "trying", "going", "sorry", "here", "fine"]:
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="update_user_profile", params={"key": "name", "value": u_name}, confidence=1.0, reasoning="Instant user name memory.")

        role_stmt = re.search(r"^(?:i\s+am\s+a|i\s+work\s+as\s+a|my\s+job\s+is|my\s+profession\s+is)\s+([a-zA-Z\s\-]+)$", text, re.I)
        if role_stmt:
            u_role = role_stmt.group(1).strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="update_user_profile", params={"key": "role", "value": u_role}, confidence=1.0, reasoning="Instant user role memory.")

        loc_stmt = re.search(r"^(?:i\s+live\s+in|my\s+location\s+is|i\s+am\s+located\s+in)\s+([a-zA-Z\s\-]+)$", text, re.I)
        if loc_stmt:
            u_loc = loc_stmt.group(1).strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="update_user_profile", params={"key": "location", "value": u_loc}, confidence=1.0, reasoning="Instant user location memory.")

        rem_fact = re.search(r"^(?:remember\s+that|remember\s+to|please\s+remember\s+that|remember)\s+(.+)$", text, re.I)
        if rem_fact and not re.search(r"\b(?:in|after)\s+\d+\s*(?:sec|min|hour)", text, re.I):
            fact_val = rem_fact.group(1).strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="save_user_fact", params={"fact": fact_val}, confidence=1.0, reasoning="Instant fact memory.")

        # 14. Telemetry & Diagnostics (<0.0ms)
        if "battery" in text and not any(w in text for w in ["buy", "order", "replace"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="check_battery")
        if any(w in text for w in ["check ram", "ram usage", "how much ram", "memory usage"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="check_ram")
        if any(w in text for w in ["check cpu", "cpu usage", "how much cpu"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="check_cpu")
        if any(w in text for w in ["check ip", "what is my ip", "my ip address"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="check_ip")

        # System Power & Display Management (<0.0ms)
        if re.search(r"\b(?:put\s+(?:the\s+|my\s+)?(?:computer|pc|laptop|system|machine)\s+to\s+sleep|sleep\s+(?:the\s+|my\s+)?(?:computer|pc|laptop|system|machine)|suspend\s+(?:the\s+|my\s+)?(?:computer|pc|laptop|system)|go\s+to\s+sleep)\b", text, re.I) or text in [
            "sleep pc", "sleep computer", "sleep system", "put pc to sleep", "put computer to sleep", "sleep the pc", "sleep the computer", "suspend pc", "suspend computer"
        ]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="sleep_system", safety_tier="GREEN", confidence=1.0, reasoning="Instant computer sleep.")

        if re.search(r"\b(?:lock\s+(?:the\s+|my\s+)?(?:pc|computer|workstation|screen|machine|laptop|windows)|lock\s+it|^lock$)\b", text, re.I) or text in [
            "lock pc", "lock the pc", "lock my pc", "lock workstation", "lock computer", "lock screen", "lock the screen", "lock machine"
        ]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="lock_workstation", safety_tier="GREEN", confidence=1.0, reasoning="Instant screen lock.")

        if re.search(r"\b(?:turn\s+off\s+(?:the\s+)?(?:screen|display|monitor)|turn\s+(?:the\s+)?(?:screen|display|monitor)\s+off|(?:screen|display|monitor)\s+off|shut\s+off\s+(?:the\s+)?(?:screen|display|monitor)|sleep\s+(?:the\s+)?(?:screen|display|monitor)|put\s+(?:the\s+)?(?:screen|display|monitor)\s+to\s+sleep|blank\s+screen|turn\s+(?:the\s+)?screen\s+black)\b", text, re.I) or text in [
            "turn off screen", "turn off the screen", "turn the screen off", "screen off",
            "turn off display", "turn off the display", "turn the display off", "display off",
            "sleep screen", "sleep display", "turn off monitor", "turn off the monitor", "turn monitor off",
            "blank screen"
        ]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="turn_screen_off", safety_tier="GREEN", confidence=1.0, reasoning="Instant screen turn-off.")

        if re.search(r"\b(?:turn\s+on\s+(?:the\s+)?(?:screen|display|monitor)|turn\s+(?:the\s+)?(?:screen|display|monitor)\s+on|(?:screen|display|monitor)\s+on|wake\s+(?:up\s+)?(?:the\s+)?(?:screen|display|monitor))\b", text, re.I) or text in [
            "turn on screen", "turn on the screen", "turn the screen on", "screen on",
            "turn on display", "turn on the display", "turn the display on", "display on",
            "wake screen", "wake up screen", "wake display"
        ]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="turn_screen_on", safety_tier="GREEN", confidence=1.0, reasoning="Instant screen turn-on.")
        if any(w in text for w in ["take a screenshot", "screenshot", "capture screen"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="take_screenshot")

        # Screen Eyes: On-Demand Zero-GPU Visual Inspection (<0.0ms)
        if (
            re.search(r"\b(?:look\s+at\s+(?:the\s+|my\s+)?screen|what\s+is\s+on\s+(?:the\s+|my\s+)?screen|what['']s\s+on\s+(?:the\s+|my\s+)?screen|read\s+(?:the\s+|my\s+)?screen|inspect\s+(?:the\s+|my\s+)?screen|what\s+am\s+i\s+looking\s+at|what\s+is\s+this\s+error|explain\s+(?:this\s+)?error|diagnose\s+(?:this\s+)?error|view\s+(?:the\s+|my\s+)?screen)\b", text, re.I)
            or text in ["look at my screen", "look at the screen", "what's on my screen", "what is on my screen", "whats on my screen", "explain this error", "what is this error", "whats this error", "diagnose error", "read screen", "read my screen", "what am i looking at"]
        ):
            return RouteDecision(
                path=ExecutionPath.FAST_PATH,
                action="inspect_screen",
                params={"query": original},
                confidence=1.0,
                reasoning="Instant on-demand screen inspection."
            )

        # Proactive Intelligence: Daily Briefing & Status Report (<0.0ms)
        if (
            re.search(r"^(?:can\s+you\s+|please\s+)?(?:give\s+me\s+(?:a\s+)?)?(?:good\s+morning|morning\s+briefing|daily\s+briefing|daily\s+report|morning\s+report|brief\s+me|system\s+briefing|status\s+report|executive\s+briefing)\b", text, re.I)
            or text in ["good morning", "brief me", "morning briefing", "daily briefing", "daily report", "morning report", "status report", "give me a briefing"]
        ):
            return RouteDecision(
                path=ExecutionPath.FAST_PATH,
                action="get_daily_briefing",
                confidence=1.0,
                reasoning="Instant JARVIS daily executive briefing."
            )

        # Floating Glass HUD Mode Switching (<0.0ms)
        if (
            re.search(r"\b(?:compact\s+mode|mini\s+hud|island\s+mode|floating\s+pill|compact\s+hud|expand\s+hud|full\s+hud|maximize\s+hud|toggle\s+hud)\b", text, re.I)
            or text in ["compact mode", "mini hud", "island mode", "expand hud", "full hud", "compact hud", "floating pill"]
        ):
            hud_mode = "compact" if any(w in text for w in ["compact", "mini", "pill", "island"]) else "full"
            return RouteDecision(
                path=ExecutionPath.FAST_PATH,
                action="toggle_hud_mode",
                params={"mode": hud_mode},
                confidence=1.0,
                reasoning="Instant HUD mode switch."
            )

        if any(w in text for w in ["brightness up", "increase brightness", "brighter"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="brightness_up")
        if any(w in text for w in ["brightness down", "lower brightness", "dimmer"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="brightness_down")

        # Camera Photo & App Launch (<0.0ms)
        if any(w in text for w in ["take a photo", "take photo", "take a picture", "take picture", "take a selfie", "capture photo", "snap a photo", "snap photo", "take a snapshot"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="take_photo")
        if re.search(r"^(?:can\s+you\s+)?(?:open|launch|start|turn\s+on|show)\s+(?:the\s+)?(?:camera|webcam)$|^camera$|^webcam$", text, re.I):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="open_camera")

        # Telegram Messaging & Calls (<0.0ms)
        tg_send = re.search(
            r"(?:send\s+(?:a\s+)?(?:message|text)\s+(?:on|via|in|to)\s+telegram\s+to\s+([a-zA-Z0-9_@\s]+?)(?:\s*(?:saying|with|:|that)\s*(.+))?$|"
            r"message\s+([a-zA-Z0-9_@\s]+?)\s+on\s+telegram(?:\s*(?:saying|with|:|that)\s*(.+))?$|"
            r"send\s+telegram\s+(?:message\s+)?to\s+([a-zA-Z0-9_@\s]+?)(?:\s*(?:saying|with|:|that)\s*(.+))?$|"
            r"tell\s+([a-zA-Z0-9_@\s]+?)\s+on\s+telegram\s+(?:that\s+)?(.+)$)",
            text,
            flags=re.IGNORECASE
        )
        if tg_send:
            rec = tg_send.group(1) or tg_send.group(3) or tg_send.group(5) or tg_send.group(7) or ""
            msg = tg_send.group(2) or tg_send.group(4) or tg_send.group(6) or tg_send.group(8) or ""
            rec = rec.strip()
            msg = msg.strip().strip("'\"")
            if rec:
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="telegram_send_message", params={"recipient": rec, "message": msg or "Hello!"})

        if any(w in text for w in ["read telegram", "read messages on telegram", "check telegram messages", "check telegram", "read my telegram"]):
            chat_m = re.search(r"(?:from|with)\s+([a-zA-Z0-9_@\s]+)", text)
            chat = chat_m.group(1).strip() if chat_m else "me"
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="telegram_read_messages", params={"chat": chat, "limit": 5})

        tg_search = re.search(r"(?:search\s+telegram\s+for|search\s+for\s+(.+?)\s+on\s+telegram|find\s+telegram\s+message\s+(?:about\s+)?)\s*(.+)?", text)
        if tg_search:
            q = (tg_search.group(1) or tg_search.group(2) or "").strip()
            if q:
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="telegram_search_messages", params={"query": q, "limit": 5})

        tg_call = re.search(r"(?:call|voice\s+call)\s+([a-zA-Z0-9_@\s]+?)\s+(?:on|via|through)\s+telegram", text)
        if tg_call:
            rec = tg_call.group(1).strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="telegram_call", params={"contact": rec})

        # WhatsApp Calls & Messaging (<0.0ms)
        wa_call = re.search(r"(?:make\s+(?:a\s+)?)?(?:video\s+call|call|voice\s+call)\s+(.+?)(?:\s+(?:on|via|through)\s+whatsapp)?$", text)
        if wa_call and ("whatsapp" in text or "video call" in text):
            target = wa_call.group(1).strip()
            target = re.sub(r"\s+(?:on|via|through)\s+whatsapp\b", "", target, flags=re.IGNORECASE).strip()
            call_type = "video" if "video" in text else "voice"
            if target and target not in ["call", "someone", "whatsapp"]:
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="whatsapp_call", params={"contact": target, "call_type": call_type})

        wa_send = re.search(
            r"(?:send\s+(?:a\s+)?(?:message|text)\s+(?:on|via|in|to)\s+whatsapp\s+to\s+([a-zA-Z0-9_@\s\+]+?)(?:\s*(?:saying|with|:|that)\s*(.+))?$|"
            r"message\s+([a-zA-Z0-9_@\s\+]+?)\s+on\s+whatsapp(?:\s*(?:saying|with|:|that)\s*(.+))?$|"
            r"send\s+whatsapp\s+(?:message\s+)?to\s+([a-zA-Z0-9_@\s\+]+?)(?:\s*(?:saying|with|:|that)\s*(.+))?$|"
            r"tell\s+([a-zA-Z0-9_@\s\+]+?)\s+on\s+whatsapp\s+(?:that\s+)?(.+)$)",
            text,
            flags=re.IGNORECASE
        )
        if wa_send:
            rec = wa_send.group(1) or wa_send.group(3) or wa_send.group(5) or wa_send.group(7) or ""
            msg = wa_send.group(2) or wa_send.group(4) or wa_send.group(6) or wa_send.group(8) or ""
            rec = rec.strip()
            msg = msg.strip().strip("'\"")
            if rec:
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="whatsapp_message", params={"contact": rec, "message": msg or "Hello!"})

        # Contacts Book CRUD (<0.0ms)
        c_add = re.search(r"(?:add|save|create)\s+contact\s+([a-zA-Z0-9\s]+?)(?:\s+with\s+(?:phone|number)\s+([+\d\s\-]+))?(?:\s+(?:with\s+)?telegram\s+(@?[a-zA-Z0-9_]+))?$", text)
        if c_add:
            c_name = c_add.group(1).strip()
            c_phone = (c_add.group(2) or "").strip()
            c_tg = (c_add.group(3) or "").strip().lstrip("@")
            if c_name and c_name not in ["a", "the", "new", "someone"]:
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="contact_add", params={"name": c_name, "phone": c_phone, "telegram": c_tg})

        if re.search(r"^(?:list|show|view|display|get)(?:\s+all|\s+my)?\s+contacts$", text, re.I) or text in ["list contacts", "show contacts", "show my contacts", "all contacts", "my contacts", "get contacts", "saved contacts", "view contacts"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="contact_list")

        c_find = re.search(r"(?:find|search|lookup|who\s+is)\s+contact\s+([a-zA-Z0-9\s]+)", text)
        if c_find:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="contact_find", params={"query": c_find.group(1).strip()})

        c_del = re.search(r"(?:delete|remove)\s+contact\s+([a-zA-Z0-9\s]+)", text)
        if c_del:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="contact_delete", params={"name": c_del.group(1).strip()})

        # Red-Tier Safety Power Controls (<0.0ms)
        if any(w in text for w in ["shutdown the computer", "shut down computer", "turn off the computer", "power off computer", "turn off pc"]):
            return RouteDecision(
                path=ExecutionPath.FAST_PATH,
                action="shutdown_system",
                safety_tier="RED",
                confidence=1.0,
                reasoning="Requires explicit user confirmation before executing system power off."
            )
        if any(w in text for w in ["restart the computer", "restart computer", "reboot computer", "reboot pc"]):
            return RouteDecision(
                path=ExecutionPath.FAST_PATH,
                action="restart_system",
                safety_tier="RED",
                confidence=1.0,
                reasoning="Requires explicit user confirmation before executing system reboot."
            )

        # 15. Memes & Archetype Triggers (<0.0ms)
        meme_match = re.search(r"\b(based|chudjak|nothing\s+ever\s+happens|pepe|monkas|wojak|feels\s+good|feels\s+bad|galaxy\s+brain|it's\s+over|cringe)\b", text)
        if meme_match and ("meme" in text or text.startswith(("you are", "you're", "that's", "thats", "show", "tell")) or len(text.split()) <= 4):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="trigger_meme", params={"meme_name": meme_match.group(1).strip()})

        # 16. Underspecified Meta Instructions
        if text in ["open this and do this", "open that and do that", "open this and do that", "open something and do something", "open this"]:
            return RouteDecision(
                path=ExecutionPath.CLARIFY,
                action="none",
                clarification_prompt="Which application would you like me to open, and what task would you like me to perform?",
            )

        # 17. Open App (<0.0ms)
        if " and " not in text and " then " not in text:
            open_match = re.match(
                r"^(?:can\s+you\s+please\s+|could\s+you\s+please\s+|can\s+you\s+|could\s+you\s+|please\s+)?(?:open\s+up|bring\s+up|open|launch|start|run)\s+(?:the\s+)?([a-zA-Z0-9\s_\-\.]+?)(?:\s+app|\s+application|\s+program)?$",
                text,
                flags=re.IGNORECASE
            )
            if open_match:
                raw_target = open_match.group(1).strip()
                raw_target = re.sub(r"^up\s+", "", raw_target).strip()
                if not any(w in raw_target for w in [" and ", " then ", " do ", " this", " that", " something", "file "]):
                    if raw_target not in ["a", "the", "it", "this", "new folder", "something", "an app"]:
                        return RouteDecision(path=ExecutionPath.FAST_PATH, action="open_app", params={"app_name": raw_target})

        # 18. Close App (<0.0ms)
        close_match = re.match(
            r"^(?:can\s+you\s+|could\s+you\s+|please\s+)?(?:close\s+down|shut\s+down|close|quit|exit|kill)\s+(?:the\s+)?([a-zA-Z0-9\s_\-\.]+?)(?:\s+app|\s+application|\s+program)?$",
            text,
            flags=re.IGNORECASE
        )
        if close_match:
            raw_close = close_match.group(1).strip()
            raw_close = re.sub(r"^down\s+", "", raw_close).strip()
            if raw_close not in ["this", "it", "window", "active window", "the window", "computer", "pc"]:
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="close_window", params={"title_keyword": raw_close})

        # 19. Local Time, Date, Jokes & Personal Banter (<0.0ms)
        if any(w in text for w in ["what time is it", "tell me the time", "current time", "the time"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="query_time")
        if any(w in text for w in ["what is today's date", "what is the date", "today's date", "what day is it"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="query_date")
        if any(w in text for w in ["tell me a joke", "tell a joke", "say a joke"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="tell_joke")
        if any(w in text for w in ["tell me a meme", "share a meme", "give me a meme"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="share_meme")
        if any(w in text for w in ["suggest songs", "recommend music", "suggest music"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="suggest_songs")
        if any(w in text for w in ["who am i", "what is my name", "do you know me"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="who_am_i")
        if any(w in text for w in ["who are you", "what is your name", "who made you"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="query_identity")

        # 20. System Power (Red Tier) (<0.0ms)
        if any(w in text for w in ["shut down the computer", "shutdown computer", "turn off the pc", "turn off computer", "shut down pc", "restart computer", "reboot pc", "reboot computer"]):
            return RouteDecision(
                path=ExecutionPath.FAST_PATH,
                action="shutdown_system" if any(w in text for w in ["shut", "off"]) else "restart_system",
                params={},
                safety_tier="RED",
                confidence=1.0,
                reasoning="Requires user confirmation before power action."
            )

        return None

    # -------------------------------------------------------------
    # Ultra-Fast LLM Classifier Layer (<250ms)
    # -------------------------------------------------------------
    def _classify_with_fast_llm(self, utterance: str) -> Optional[RouteDecision]:
        """Fast ~200ms classifier on Groq to map colloquial natural language into direct fast-path actions."""
        if not GROQ_API_KEY:
            return None

        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY, timeout=2.5)

            system_prompt = (
                "You are the ultra-fast desktop intent classifier. Output ONLY a single compact JSON object.\n"
                "Allowed actions:\n"
                "- {\"action\": \"open_app\", \"app\": \"<name>\"}\n"
                "- {\"action\": \"close_app\", \"app\": \"<name>\"}\n"
                "- {\"action\": \"play_youtube\", \"query\": \"<title>\"}\n"
                "- {\"action\": \"browser_search\", \"query\": \"<query>\", \"engine\": \"google\"|\"youtube\"} (ONLY if user explicitly asks to search the web or google something)\n"
                "- {\"action\": \"open_url\", \"url\": \"<url>\"}\n"
                "- {\"action\": \"send_message\", \"recipient\": \"<name>\", \"message\": \"<text>\"}\n"
                "- {\"action\": \"telegram_send_message\", \"recipient\": \"<name>\", \"message\": \"<text>\"}\n"
                "- {\"action\": \"whatsapp_message\", \"contact\": \"<name>\", \"message\": \"<text>\"}\n"
                "- {\"action\": \"clarify\", \"prompt\": \"<question>\"}\n"
                "- {\"action\": \"volume_up\"} or {\"action\": \"volume_down\"} or {\"action\": \"set_volume\", \"level\": 50} or {\"action\": \"mute\"}\n"
                "- {\"action\": \"organize_windows\", \"layout\": \"grid\"|\"split\"|\"columns\"|\"focus\"}\n"
                "- {\"action\": \"draw_shape\", \"shape\": \"circle\"|\"heart\"|\"star\"|\"square\"|\"triangle\"}\n"
                "- {\"action\": \"check_battery\"} or {\"action\": \"check_ram\"} or {\"action\": \"check_cpu\"}\n"
                "- {\"action\": \"compound\", \"actions\": [{\"action\": \"open_app\", \"app\": \"paint\"}, {\"action\": \"draw_shape\", \"shape\": \"circle\"}]}\n"
                "- {\"action\": \"reasoning\"} (FOR ALL questions, explanations, knowledge queries, science, trivia, facts, e.g. 'what is X', 'who is Y', 'explain Z')\n"
            )

            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": utterance}
                ],
                max_tokens=60,
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            raw = response.choices[0].message.content.strip()
            data = json.loads(raw)
            act = data.get("action")

            if not act or act == "reasoning":
                return None

            if act == "compound":
                sub_acts = data.get("actions", [])
                formatted = []
                for sa in sub_acts:
                    a_name = sa.get("action")
                    if a_name == "open_app":
                        formatted.append({"action": "open_app", "params": {"app_name": sa.get("app", "")}})
                    elif a_name == "draw_shape":
                        formatted.append({"action": "draw_shape", "params": {"shape": sa.get("shape", "circle"), "title_keyword": "Paint"}})
                    elif a_name in ["volume_up", "volume_down", "mute", "play_media"]:
                        formatted.append({"action": a_name, "params": {}})
                if formatted:
                    return RouteDecision(
                        path=ExecutionPath.FAST_PATH,
                        action="execute_compound",
                        params={"actions": formatted},
                        safety_tier="GREEN",
                        confidence=0.95,
                        reasoning="LLM classified compound fast-path."
                    )

            if act == "open_app":
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="open_app", params={"app_name": data.get("app", "")})
            elif act == "close_app":
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="close_window", params={"title_keyword": data.get("app", "")})
            elif act == "play_youtube":
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="play_youtube", params={"query": data.get("query", "synthwave")})
            elif act == "browser_search":
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="browser_search", params={"query": data.get("query", ""), "engine": data.get("engine", "google")})
            elif act == "open_url":
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="browser_open_url", params={"url": data.get("url", "")})
            elif act == "send_message":
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="send_message", params={"recipient": data.get("recipient", ""), "message": data.get("message", "Hello!")})
            elif act == "telegram_send_message":
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="telegram_send_message", params={"recipient": data.get("recipient", ""), "message": data.get("message", "Hello!")})
            elif act == "whatsapp_message":
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="whatsapp_message", params={"contact": data.get("contact", "") or data.get("recipient", ""), "message": data.get("message", "Hello!")})
            elif act == "clarify":
                return RouteDecision(path=ExecutionPath.CLARIFY, action="none", clarification_prompt=data.get("prompt", "Who would you like me to message, and what should I say?"))
            elif act == "draw_shape":
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="draw_shape", params={"shape": data.get("shape", "circle"), "title_keyword": "Paint"})
            elif act == "organize_windows":
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="organize_windows", params={"layout": data.get("layout", "grid")})
            elif act in ["volume_up", "volume_down", "mute", "check_battery", "check_ram", "check_cpu", "play_media"]:
                return RouteDecision(path=ExecutionPath.FAST_PATH, action=act, params={})
            elif act == "set_volume":
                return RouteDecision(path=ExecutionPath.FAST_PATH, action="set_volume", params={"level": int(data.get("level", 50))})

        except Exception as e:
            pass

        return None


def get_intent_router() -> IntentRouter:
    return IntentRouter.get_instance()


def classify_intent(utterance: str) -> RouteDecision:
    """Convenience helper to classify and route an utterance."""
    return IntentRouter.get_instance().route(utterance)
