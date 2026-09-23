"""
Jarvis System 1 Reflex Engine (v5.0)
High-speed semantic intent classification and entity extraction.
Supports:
- TypeSafe Jev (Cloud System 1 via typesafe-sdk)
- Convai Laya (Local System 1 via laya)
- Ultra-Fast Semantic Parameter Extractor (<0.5ms)
"""
import os
import re
import sys
import time
from typing import Dict, Any, Optional

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from jarvis_config import SYSTEM1_PROVIDER, TYPESAFE_API_KEY

try:
    from typesafe_sdk import TypeSafeClient, Choice, Noul
    TYPESAFE_SDK_AVAILABLE = True
except ImportError:
    TYPESAFE_SDK_AVAILABLE = False

try:
    from laya import Router
    LAYA_AVAILABLE = True
except ImportError:
    LAYA_AVAILABLE = False


JARVIS_SCHEMA = {
    "action": {
        "type": "choice",
        "instructions": "What primary action does the user want to perform in `command`?",
        "criteria": {
            "document": "create or write in Microsoft Word, Notepad, document, essay, or note",
            "communication": "send a message or email via WhatsApp or mail",
            "system_reflex": "volume, media playback, mute, screenshot, lock screen, battery, ram, or close app",
            "open_app": "launch an application, window, or folder",
            "web_search": "search Google, browse a website, or search online",
            "ask_ai": "ask a general question, reasoning, or conversation",
        },
    },
    "is_destructive": {
        "type": "noul",
        "instructions": "Does `command` request deleting files, wiping data, formatting drives, or shutting down?",
    },
}


class JarvisReflex:
    """
    Unified System 1 Reflex and Semantic Intent Parser.
    Sub-millisecond intent and entity extraction with Jev/Laya fallbacks.
    """

    def __init__(self, preload: bool = False):
        self.provider = SYSTEM1_PROVIDER.lower().strip()
        self.jev_client = None
        self.router = None

        if self.provider in ("auto", "jev") and TYPESAFE_API_KEY and TYPESAFE_SDK_AVAILABLE:
            try:
                self.jev_client = TypeSafeClient(api_key=TYPESAFE_API_KEY)
                print("⚡ [JarvisReflex] Connected to TypeSafe Jev (System 1)")
            except Exception as e:
                print(f"⚠️ [JarvisReflex] Jev init: {e}")

        if not self.jev_client and LAYA_AVAILABLE and preload:
            try:
                self.router = Router(preload=True)
            except Exception:
                pass

    def evaluate(self, query: str) -> Dict[str, Any]:
        """
        Parses intent, domain, parameters, and safety in sub-millisecond time.
        """
        t0 = time.perf_counter()
        q_clean = query.strip()
        # Clean leading wake words (Jarvis, Hey Jarvis, Computer)
        q_norm = re.sub(r'^(?:hey\s+)?(?:jarvis|computer)[,:\s]*', '', q_clean, flags=re.I).strip()
        q_lower = q_norm.lower()

        # --------------------------------------------------------------------
        # 1. Safety Guardrail (<0.1ms)
        # --------------------------------------------------------------------
        is_destructive = 0.0
        if re.search(r'\bformat\s+[a-z]:|\brm\s+-rf|\bdel\s+/[a-z]|\bdrop\s+database|\bdelete\s+(?:all|system|windows)', q_lower):
            is_destructive = 0.99
            return self._build_result(query, "blocked_safety", "blocked_safety", 1.0, is_destructive, t0)


        # --------------------------------------------------------------------
        # 2. Sub-millisecond Semantic Pattern Matching (<0.3ms)
        # --------------------------------------------------------------------
        # A. Media & Audio Reflexes
        if re.search(r'\b(volume\s*up|louder|raise\s*(?:the\s*)?(?:volume|sound|audio))\b', q_lower):
            return self._build_result(query, "system_reflex", "volume_up", 1.0, is_destructive, t0)

        if re.search(r'\b(volume\s*down|lower\s*(?:the\s*)?(?:volume|sound|audio)|quieter)\b', q_lower):
            return self._build_result(query, "system_reflex", "volume_down", 1.0, is_destructive, t0)

        if re.search(r'\b(mute|unmute|silence\s*(?:audio|sound)?)\b', q_lower):
            return self._build_result(query, "system_reflex", "mute", 1.0, is_destructive, t0)

        if re.search(r'\b(play|pause|resume|toggle\s*play)\b', q_lower):
            return self._build_result(query, "system_reflex", "play_pause", 1.0, is_destructive, t0)

        if re.search(r'\b(next\s*track|next\s*song|skip\s*song)\b', q_lower):
            return self._build_result(query, "system_reflex", "next_track", 1.0, is_destructive, t0)

        if re.search(r'\b(prev(?:ious)?\s*track|previous\s*song)\b', q_lower):
            return self._build_result(query, "system_reflex", "prev_track", 1.0, is_destructive, t0)

        # Media volume levels (e.g. "volume 50", "set volume to 80")
        vol_lvl_m = re.search(r'\b(?:set\s+)?volume\s+(?:to\s+)?(\d{1,3})\b', q_lower)
        if vol_lvl_m:
            level = int(vol_lvl_m.group(1))
            return self._build_result(query, "system_reflex", "set_volume", 1.0, is_destructive, t0, {"level": level})

        if re.search(r'\b(screenshot|capture\s*screen|take\s*a?\s*screenshot)\b', q_lower):
            return self._build_result(query, "system_reflex", "screenshot", 1.0, is_destructive, t0)

        if re.search(r'\b(lock\s*(?:my\s*)?(?:pc|screen|computer)|lockworkstation)\b', q_lower):
            return self._build_result(query, "system_reflex", "lock_pc", 1.0, is_destructive, t0)

        # B. System Diagnostics (battery, ram, ip)
        if any(w in q_lower for w in ("battery", "charge", "ram", "memory usage", "my ip", "ip address")):
            return self._build_result(query, "system_reflex", "system_metric", 1.0, is_destructive, t0, {"metric_query": q_lower})

        # C. App Termination
        close_m = re.match(r'^(?:close|kill|quit|exit|terminate)\s+([a-zA-Z0-9_\-\s]+?)(?:\.exe)?$', q_lower)
        if close_m:
            app_target = close_m.group(1).strip()
            return self._build_result(query, "system_reflex", "close_app", 1.0, is_destructive, t0, {"target": app_target})

        # D. Email Communication (Takes precedence over WhatsApp when email/mail is mentioned)
        if "email" in q_lower or ("mail" in q_lower and any(k in q_lower for k in ("to", "send", "@"))):
            email_m = re.search(r'(?:email|mail)\s+(?:to\s+)?([^\s,]+@[^\s,]+|[^\s,]+)\s*(?:saying|with|subject|:)?\s*(.*)', q_norm, re.IGNORECASE)
            if email_m:
                rec = email_m.group(1).strip()
                body = email_m.group(2).strip() or "Hello"
                return self._build_result(query, "communication", "email", 0.98, is_destructive, t0, {
                    "recipient": rec,
                    "body": body,
                    "subject": "Message from Jarvis"
                })

        # E. WhatsApp Communication
        # Matches: "open whatsapp and send a message to <rec> saying <msg>"
        #          "send a message to <rec> on whatsapp: <msg>"
        #          "whatsapp <rec> <msg>"
        wa_m = re.search(
            r'(?:whatsapp|message)\s+(?:to\s+)?([^\s,]+(?:\s+[^\s,]+)?)\s*(?:saying|that|with|:|,)?\s*(.*)',
            q_norm,
            re.IGNORECASE
        )
        if "whatsapp" in q_lower or (("send" in q_lower or "message" in q_lower) and any(k in q_lower for k in ("saying", "tell", "to"))):
            rec = "contact"
            msg = "Hello"
            # Pattern 1: ...send a message to <recipient> saying <msg>
            p1 = re.search(r'(?:send\s+(?:a\s+)?message\s+to\s+)(.+?)\s+(?:saying|that|:)\s+(.+)', q_norm, re.IGNORECASE)
            if p1:
                rec, msg = p1.group(1).strip(), p1.group(2).strip()
            # Pattern 2: ...send a message to <recipient>
            elif p2 := re.search(r'(?:send\s+(?:a\s+)?message\s+to\s+)(.+)', q_norm, re.IGNORECASE):
                rec = p2.group(1).strip()
                msg = "Hello"
            elif wa_m:
                rec = wa_m.group(1).strip()
                msg = wa_m.group(2).strip() or "Hello"

            # Clean recipient from trailing stop words
            rec = re.sub(r'\s+(?:on|via|through)\s+whatsapp.*$', '', rec, flags=re.I).strip()
            return self._build_result(query, "communication", "whatsapp", 0.98, is_destructive, t0, {
                "recipient": rec,
                "message": msg
            })


        # F. File and Folder Operations
        folder_m = re.search(r'(?:create|make)\s+(?:a\s+)?(?:folder|directory)\s+(?:named|called)?\s*([a-zA-Z0-9_\-\s]+)', q_norm, re.IGNORECASE)
        if folder_m:
            folder_name = folder_m.group(1).strip()
            return self._build_result(query, "file_ops", "create_folder", 0.98, is_destructive, t0, {"folder_name": folder_name})

        file_m = re.search(r'(?:create|make)\s+(?:a\s+)?file\s+(?:named|called)?\s*([a-zA-Z0-9_.\-]+)(?:\s+(?:with|saying|and\s+write)\s+(.*))?', q_norm, re.IGNORECASE)
        if file_m:
            filename = file_m.group(1).strip()
            content = file_m.group(2).strip() if file_m.group(2) else ""
            return self._build_result(query, "file_ops", "create_file", 0.98, is_destructive, t0, {"filename": filename, "content": content})

        # G. Document Generation (Word & Notepad)
        # Matches: "open word and write an essay about nature"
        #          "open the word and write hello world"
        #          "open notebook and write..."
        #          "create a document on..."
        doc_word_m = re.search(r'\b(?:word|docx|winword)\b', q_lower)
        doc_note_m = re.search(r'\b(?:notepad|notebook|note|txt)\b', q_lower)

        if ("write" in q_lower or "create" in q_lower or "type" in q_lower or "draft" in q_lower) and (doc_word_m or doc_note_m or "document" in q_lower or "essay" in q_lower):
            # Extract topic/content
            content_match = re.search(r'(?:write|type|draft|create)\s+(?:an?\s+)?(?:essay\s+about|report\s+on|note\s+about|document\s+about)?\s*(.*)', q_norm, re.IGNORECASE)
            raw_content = content_match.group(1).strip() if content_match else "General Document"
            raw_content = re.sub(r'^(?:in|into|on)\s+(?:word|notepad|notebook)\s*', '', raw_content, flags=re.I).strip()

            target_app = "word" if doc_word_m or "document" in q_lower or "essay" in q_lower else "notepad"
            return self._build_result(query, "document", f"create_{target_app}", 0.98, is_destructive, t0, {
                "app": target_app,
                "topic": raw_content or "Notes",
                "content": raw_content if any(k in raw_content.lower() for k in ("hello", "dear", "hi")) else None
            })

        # H. App Launching (Simple)
        # Matches: "open chrome", "launch visual studio", "start calculator"
        if any(q_lower.startswith(p) for p in ("open ", "launch ", "start ", "show ")) and not any(k in q_lower for k in (" and ", " then ", " saying ", " write ", " send ")):
            app_name = re.sub(r'^(?:open|launch|start|show)\s+', '', q_norm, flags=re.I).strip()
            return self._build_result(query, "open_app", "open_app", 0.95, is_destructive, t0, {"target": app_name})

        # I. Web Search
        # Matches: "search google for...", "search the web for...", "google..."
        if any(q_lower.startswith(p) for p in ("search google for ", "search web for ", "search for ", "google ", "look up ")):
            search_query = re.sub(r'^(?:search\s+google\s+for|search\s+web\s+for|search\s+for|google|look\s+up)\s+', '', q_norm, flags=re.I).strip()
            return self._build_result(query, "web_search", "web_search", 0.95, is_destructive, t0, {"search_query": search_query})


        # --------------------------------------------------------------------
        # 3. Fallback to TypeSafe Jev (if configured)
        # --------------------------------------------------------------------
        if self.jev_client:
            try:
                resp = self.jev_client.system_one(
                    state={"command": query},
                    questions={
                        "action": Choice(
                            instructions=JARVIS_SCHEMA["action"]["instructions"],
                            criteria=JARVIS_SCHEMA["action"]["criteria"]
                        ),
                        "is_destructive": Noul(instructions=JARVIS_SCHEMA["is_destructive"]["instructions"])
                    }
                )
                choice = resp.answers["action"].choice
                destr = getattr(resp.answers["is_destructive"], "noul", 0.0)
                return self._build_result(query, choice, choice, 0.90, destr, t0)
            except Exception:
                pass

        # --------------------------------------------------------------------
        # 4. Fallback: General Intelligence / Q&A
        # --------------------------------------------------------------------
        return self._build_result(query, "ask_ai", "ask_ai", 0.85, is_destructive, t0)

    @staticmethod
    def _build_result(query: str, domain: str, action: str, conf: float, destr: float, t0: float, params: Optional[Dict] = None) -> Dict[str, Any]:
        return {
            "query": query,
            "domain": domain,
            "action": action,
            "action_confidence": conf,
            "target": params.get("target", "none") if params else "none",
            "target_confidence": 1.0,
            "is_destructive": destr,
            "parameters": params or {},
            "routing_model": "system1-fast-extractor",
            "latency_ms": (time.perf_counter() - t0) * 1000,
        }
