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
        # Clean leading wake words (Hey Laya, Laya, Jarvis, etc.)
        text = re.sub(r"^(?:hey|hi|hello)?[\s,]*(?:laya|leia|layer|jarvis|computer)[,\.!\s]*", "", text, flags=re.IGNORECASE).strip()
        text = text.strip(".!? ")

        # 1. Instant greetings and readiness checks (<0.1ms)
        if not text or text in ["laya", "hey", "hello", "hi", "hey laya", "jarvis"]:
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

        # 4. Single Deterministic Fast-Path Patterns (<1ms)
        single_decision = self._route_single_deterministic(text, utterance)
        if single_decision:
            return single_decision

        # 5. Ultra-Fast LLM Intent Classifier Layer (<250ms on Groq)
        llm_decision = self._classify_with_fast_llm(utterance)
        if llm_decision:
            return llm_decision

        # 6. Fallback to Autonomous ReAct Agent Loop for genuinely open-ended tasks
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
        for part in parts:
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
        # 1. Universal Mute & Audio Silence (<0.0ms)
        if re.search(r"\b(?:mute|unmute|silence|be\s+quiet|shut\s+up|quiet)\b", text):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="mute")

        # 2. Volume Controls (<0.0ms)
        rel_up = re.match(r"^(?:can\s+you\s+)?(?:raise|increase|turn\s+up)\s+(?:the\s+)?(?:volume|sound)(?:\s+by)?(?:\s*(\d+))?(?:\s*percent|%)?$", text)
        if rel_up or text in ["volume up", "raise volume", "raise the volume", "turn up volume", "turn up the volume", "louder", "make it louder"]:
            steps = int(rel_up.group(1)) // 2 if (rel_up and rel_up.group(1)) else 5
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="volume_up", params={"steps": max(1, steps)})

        rel_down = re.match(r"^(?:can\s+you\s+)?(?:lower|decrease|turn\s+down)\s+(?:the\s+)?(?:volume|sound)(?:\s+by)?(?:\s*(\d+))?(?:\s*percent|%)?$", text)
        if rel_down or text in ["volume down", "lower volume", "lower the volume", "turn down volume", "turn down the volume", "quieter", "make it quieter"]:
            steps = int(rel_down.group(1)) // 2 if (rel_down and rel_down.group(1)) else 5
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="volume_down", params={"steps": max(1, steps)})

        vol_match = re.match(r"^(?:set\s+volume\s+to|volume\s+to|volume|sound\s+to)\s+(\d{1,3})$", text)
        if vol_match:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="set_volume", params={"level": int(vol_match.group(1))})

        # 3. Media & Song Controls (<0.0ms)
        if text in ["play music", "pause music", "resume music", "toggle media", "pause", "play", "stop music"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="play_media")
        if text in ["next song", "next track", "skip"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="next_track")
        if text in ["previous song", "previous track"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="prev_track")

        click_song_match = re.search(r"\b(?:click\s+on\s+(?:a\s+)?song|play\s+(?:a\s+)?song|start\s+(?:a\s+)?song|play\s+some\s+music|start\s+music)\b", text)
        if click_song_match:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="click_song", params={"query": ""})

        spot_match = re.search(r"\b(?:open\s+spotify\s+(?:and\s+)?(?:play|launch|start)|play\s+(.+?)\s+on\s+spotify|play\s+spotify)\s*(.+)?$", text)
        if spot_match:
            song_q = (spot_match.group(1) or spot_match.group(2) or "").strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="play_spotify", params={"query": song_q})

        # 4. YouTube Direct Play & Search (<0.0ms)
        yt_play_match = re.match(
            r"^(?:can\s+you\s+|could\s+you\s+|please\s+)?(?:play|start|listen\s+to)\s+(.+?)(?:\s+(?:on|from|in)\s+youtube)?$",
            text,
            flags=re.IGNORECASE
        )
        if yt_play_match and ("youtube" in text or any(w in text for w in ["song", "songs", "music", "track", "video"])):
            raw_query = yt_play_match.group(1).strip()
            raw_query = re.sub(r"\s+(?:on|from|in)\s+youtube\b", "", raw_query, flags=re.IGNORECASE).strip()
            raw_query = re.sub(r"^(?:like|some|uh|um)\s+", "", raw_query, flags=re.IGNORECASE).strip()
            if not raw_query or raw_query in ["songs", "some songs", "music", "some music"]:
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

        # 7. Filesystem: Create, Open, Write, Search, Delete (<0.0ms)
        create_file_match = re.search(r"\b(?:create|make|new)\s+(?:a\s+)?(?:new\s+)?file\s+(?:called\s+|named\s+)?([^\s,]+)(?:\s+(?:with|containing)\s+(.+))?", text)
        if create_file_match:
            fname = create_file_match.group(1).strip()
            fcontent = (create_file_match.group(2) or "").strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="create_file", params={"filename": fname, "content": fcontent})

        create_file_direct = re.match(r"^(?:create|make)\s+([a-zA-Z0-9_\-\.]+\.(?:txt|py|md|json|csv|html|css|js))\s*(?:with\s+(.+))?$", text)
        if create_file_direct:
            fname = create_file_direct.group(1).strip()
            fcontent = (create_file_direct.group(2) or "").strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="create_file", params={"filename": fname, "content": fcontent})

        create_folder_match = re.search(r"\b(?:create|make|new)\s+(?:a\s+)?(?:new\s+)?folder\s+(?:called\s+|named\s+)?([a-zA-Z0-9_\-\.\s]+)$", text)
        if create_folder_match:
            fol_name = create_folder_match.group(1).strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="create_folder", params={"folder_name": fol_name})

        open_file_match = re.search(r"\b(?:open|read|view|show)\s+(?:the\s+)?file\s+(.+)$", text)
        if open_file_match:
            target_f = open_file_match.group(1).strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="open_file", params={"filename_or_path": target_f})

        write_file_match = re.search(r"\b(?:write|append|add|put)\s+(.+?)\s+(?:to|into|in)\s+(?:the\s+)?(?:file\s+)?([a-zA-Z0-9_\-\.\/\\]+)$", text)
        if write_file_match:
            content = write_file_match.group(1).strip()
            target_f = write_file_match.group(2).strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="write_to_file", params={"filename": target_f, "content": content})

        search_file_match = re.search(r"\b(?:search\s+(?:for\s+)?(?:files?|folders?|documents?)|find\s+(?:file|folder)|locate\s+(?:file|folder))\s+(?:called\s+|named\s+)?([^\s,]+)", text)
        if search_file_match:
            pat = search_file_match.group(1).strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="search_files", params={"pattern": pat})

        search_win_match = re.search(r"\bsearch\s+(?:in\s+windows|in\s+folders?|windows|folders?)\s+(?:for\s+)?(.+)", text)
        if search_win_match:
            pat = search_win_match.group(1).strip()
            pat = re.sub(r"^for\s+", "", pat).strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="search_files", params={"pattern": pat})

        delete_file_match = re.search(r"\b(?:delete|remove)\s+(?:the\s+)?file\s+([^\s,]+)$", text)
        if delete_file_match:
            target_f = delete_file_match.group(1).strip()
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="delete_file", params={"filename_or_path": target_f})

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

        # WhatsApp Messaging
        wa_msg_match = re.search(r"\b(?:send\s+(?:a\s+)?message\s+(?:to\s+)?|message\s+|text\s+)(.+?)\s+(?:on|via|through)\s+whatsapp\s*(?:saying\s+|that\s+|with\s+|:\s*)?(.*)", text, re.I)
        if wa_msg_match:
            target_c = wa_msg_match.group(1).strip()
            target_m = wa_msg_match.group(2).strip() or "Hello from Laya"
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="whatsapp_message", params={"contact": target_c, "message": target_m})

        wa_quick_match = re.search(r"\b(?:send\s+whatsapp\s+to|whatsapp)\s+([a-zA-Z0-9_\-\.]+)\s+(?:saying\s+|that\s+|with\s+|:\s*)?(.*)", text, re.I)
        if wa_quick_match:
            target_c = wa_quick_match.group(1).strip()
            target_m = wa_quick_match.group(2).strip() or "Hello from Laya"
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="whatsapp_message", params={"contact": target_c, "message": target_m})

        # Telegram Messaging
        tg_msg_match = re.search(r"\b(?:send\s+(?:a\s+)?message\s+(?:to\s+)?|message\s+|text\s+)(.+?)\s+(?:on|via|through)\s+telegram\s*(?:saying\s+|that\s+|with\s+|:\s*)?(.*)", text, re.I)
        if tg_msg_match:
            target_c = tg_msg_match.group(1).strip()
            target_m = tg_msg_match.group(2).strip() or "Hello from Laya"
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="telegram_message", params={"contact": target_c, "message": target_m})

        tg_quick_match = re.search(r"\b(?:send\s+telegram\s+to|telegram)\s+([a-zA-Z0-9_\-\.]+)\s+(?:saying\s+|that\s+|with\s+|:\s*)?(.*)", text, re.I)
        if tg_quick_match:
            target_c = tg_quick_match.group(1).strip()
            target_m = tg_quick_match.group(2).strip() or "Hello from Laya"
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="telegram_message", params={"contact": target_c, "message": target_m})

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
        if text in ["close this", "close this window", "close active window", "close window"]:
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="close_active_window")

        # 14. Telemetry & Diagnostics (<0.0ms)
        if "battery" in text and not any(w in text for w in ["buy", "order", "replace"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="check_battery")
        if any(w in text for w in ["check ram", "ram usage", "how much ram", "memory usage"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="check_ram")
        if any(w in text for w in ["check cpu", "cpu usage", "how much cpu"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="check_cpu")
        if any(w in text for w in ["check ip", "what is my ip", "my ip address"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="check_ip")

        if any(w in text for w in ["lock pc", "lock the pc", "lock my pc", "lock workstation", "lock computer"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="lock_workstation")
        if any(w in text for w in ["take a screenshot", "screenshot", "capture screen"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="take_screenshot")
        if any(w in text for w in ["brightness up", "increase brightness", "brighter"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="brightness_up")
        if any(w in text for w in ["brightness down", "lower brightness", "dimmer"]):
            return RouteDecision(path=ExecutionPath.FAST_PATH, action="brightness_down")

        # 15. Memes & Archetype Triggers (<0.0ms)
        meme_match = re.search(r"\b(gigachad|based|chudjak|nothing\s+ever\s+happens|pepe|monkas|wojak|feels\s+good|feels\s+bad|galaxy\s+brain|it's\s+over|cringe)\b", text)
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
                "You are Laya's ultra-fast desktop intent classifier. Output ONLY a single compact JSON object.\n"
                "Allowed actions:\n"
                "- {\"action\": \"open_app\", \"app\": \"<name>\"}\n"
                "- {\"action\": \"close_app\", \"app\": \"<name>\"}\n"
                "- {\"action\": \"play_youtube\", \"query\": \"<title>\"}\n"
                "- {\"action\": \"browser_search\", \"query\": \"<query>\", \"engine\": \"google\"|\"youtube\"}\n"
                "- {\"action\": \"open_url\", \"url\": \"<url>\"}\n"
                "- {\"action\": \"volume_up\"} or {\"action\": \"volume_down\"} or {\"action\": \"set_volume\", \"level\": 50} or {\"action\": \"mute\"}\n"
                "- {\"action\": \"organize_windows\", \"layout\": \"grid\"|\"split\"|\"columns\"|\"focus\"}\n"
                "- {\"action\": \"draw_shape\", \"shape\": \"circle\"|\"heart\"|\"star\"|\"square\"|\"triangle\"}\n"
                "- {\"action\": \"check_battery\"} or {\"action\": \"check_ram\"} or {\"action\": \"check_cpu\"}\n"
                "- {\"action\": \"compound\", \"actions\": [{\"action\": \"open_app\", \"app\": \"paint\"}, {\"action\": \"draw_shape\", \"shape\": \"circle\"}]}\n"
                "- {\"action\": \"reasoning\"} (ONLY if complex multi-step reasoning, file coding, or open calculation is strictly needed)\n"
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
