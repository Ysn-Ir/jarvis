"""
Jarvis System 1 Semantic Router & Guardrail (v5.0 Unified Architecture)
Extracts domains, actions, and parameters in <0.5ms.
Integrates TypeSafe Jev & Convai Laya with instant sub-millisecond local matcher.
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

from jarvis_config import SYSTEM1_PROVIDER, TYPESAFE_API_KEY, DESTRUCTIVE_THRESHOLD

try:
    from typesafe_sdk import TypeSafeClient, Choice, Noul
    TYPESAFE_SDK_AVAILABLE = True
except ImportError:
    TYPESAFE_SDK_AVAILABLE = False

try:
    from laya import Router as LayaRouter
    LAYA_AVAILABLE = True
except ImportError:
    LAYA_AVAILABLE = False


class JarvisRouter:
    """Sub-millisecond semantic intent and parameter parser with safety guardrail."""

    def __init__(self, preload: bool = False):
        self.provider = SYSTEM1_PROVIDER.lower().strip()
        self.jev_client = None
        self.laya_router = None

        if self.provider in ("auto", "jev") and TYPESAFE_API_KEY and TYPESAFE_SDK_AVAILABLE:
            try:
                self.jev_client = TypeSafeClient(api_key=TYPESAFE_API_KEY)
                print("⚡ [JarvisRouter] Connected to TypeSafe Jev (System 1)")
            except Exception as e:
                print(f"⚠️ [JarvisRouter] Jev init: {e}")

        if not self.jev_client and LAYA_AVAILABLE and preload:
            try:
                self.laya_router = LayaRouter(preload=True)
            except Exception:
                pass

    def evaluate(self, query: str) -> Dict[str, Any]:
        """Parses intent domain, action, entities, and safety score in <0.5ms."""
        t0 = time.perf_counter()
        q_clean = query.strip()
        # Strip leading wake words
        q_norm = re.sub(r'^(?:(?:hey|hi|hello|ok|okay)?\s*(?:jarvis|computer|assistant)[,:\s]*)+', '', q_clean, flags=re.I).strip()
        if not q_norm:
            q_norm = q_clean
        q_low = q_norm.lower()

        # --------------------------------------------------------------------
        # 1. Safety Guardrail (<0.05ms)
        # --------------------------------------------------------------------
        is_destructive = 0.0
        if re.search(r'\bformat\s+[a-z]:|\brm\s+-rf|\bdel\s+/[a-z]|\bdrop\s+database|\bdelete\s+(?:all|system|windows)', q_low):
            is_destructive = 0.99
            return self._result(query, "blocked_safety", "blocked_safety", 1.0, is_destructive, t0)

        # --------------------------------------------------------------------
        # 2. Sub-millisecond Semantic Pattern Matching (<0.3ms)
        # --------------------------------------------------------------------
        # A. Media & Audio Hardware
        if re.search(r'\b(volume\s*up|louder|raise\s*(?:the\s*)?(?:volume|sound|audio))\b', q_low):
            return self._result(query, "system_hardware", "volume_up", 1.0, is_destructive, t0)

        if re.search(r'\b(volume\s*down|lower\s*(?:the\s*)?(?:volume|sound|audio)|quieter)\b', q_low):
            return self._result(query, "system_hardware", "volume_down", 1.0, is_destructive, t0)

        vol_lvl_m = re.search(r'\b(?:set\s+)?volume\s+(?:to\s+)?(\d{1,3})\b', q_low)
        if vol_lvl_m:
            return self._result(query, "system_hardware", "set_volume", 1.0, is_destructive, t0, {"level": int(vol_lvl_m.group(1))})

        if re.search(r'\b(mute|unmute|silence\s*(?:audio|sound)?)\b', q_low):
            return self._result(query, "system_hardware", "mute", 1.0, is_destructive, t0)

        if re.search(r'\b(play|pause|resume|toggle\s*play)\b', q_low):
            return self._result(query, "system_hardware", "play_pause", 1.0, is_destructive, t0)

        if re.search(r'\b(next\s*track|next\s*song|skip\s*song)\b', q_low):
            return self._result(query, "system_hardware", "next_track", 1.0, is_destructive, t0)

        if re.search(r'\b(prev(?:ious)?\s*track|previous\s*song)\b', q_low):
            return self._result(query, "system_hardware", "prev_track", 1.0, is_destructive, t0)

        if re.search(r'\b(screenshot|capture\s*screen|take\s*a?\s*screenshot)\b', q_low):
            return self._result(query, "system_hardware", "screenshot", 1.0, is_destructive, t0)

        if re.search(r'\b(lock\s*(?:my\s*)?(?:pc|screen|computer)|lockworkstation)\b', q_low):
            return self._result(query, "system_hardware", "lock_pc", 1.0, is_destructive, t0)

        # B. System Diagnostics
        if any(w in q_low for w in ("battery", "charge", "ram", "memory usage", "my ip", "ip address")):
            return self._result(query, "system_hardware", "system_metric", 1.0, is_destructive, t0, {"metric_query": q_low})

        # C. App Termination
        close_m = re.match(r'^(?:close|kill|quit|exit|terminate)\s+([a-zA-Z0-9_\-\s]+?)(?:\.exe)?$', q_low)
        if close_m:
            return self._result(query, "system_hardware", "close_app", 1.0, is_destructive, t0, {"target": close_m.group(1).strip()})

        # D. Email Communication
        if "email" in q_low or ("mail" in q_low and any(k in q_low for k in ("to", "send", "@"))):
            email_m = re.search(r'(?:email|mail)\s+(?:to\s+)?([^\s,]+@[^\s,]+|[^\s,]+)\s*(?:saying|with|subject|:)?\s*(.*)', q_norm, re.IGNORECASE)
            if email_m:
                return self._result(query, "comms", "email", 0.98, is_destructive, t0, {
                    "recipient": email_m.group(1).strip(),
                    "body": email_m.group(2).strip() or "Hello",
                    "subject": "Message from Jarvis"
                })

        # E. WhatsApp Communication
        wa_m = re.search(r'(?:whatsapp|message)\s+(?:to\s+)?([^\s,]+(?:\s+[^\s,]+)?)\s*(?:saying|that|with|:|,)?\s*(.*)', q_norm, re.IGNORECASE)
        if "whatsapp" in q_low or (("send" in q_low or "message" in q_low) and any(k in q_low for k in ("saying", "tell", "to"))):
            rec = "contact"
            msg = "Hello"
            p1 = re.search(r'(?:send\s+(?:a\s+)?message\s+to\s+)(.+?)\s+(?:saying|that|:)\s+(.+)', q_norm, re.IGNORECASE)
            if p1:
                rec, msg = p1.group(1).strip(), p1.group(2).strip()
            elif p2 := re.search(r'(?:send\s+(?:a\s+)?message\s+to\s+)(.+)', q_norm, re.IGNORECASE):
                rec, msg = p2.group(1).strip(), "Hello"
            elif wa_m:
                rec, msg = wa_m.group(1).strip(), wa_m.group(2).strip() or "Hello"

            rec = re.sub(r'\s+(?:on|via|through)\s+whatsapp.*$', '', rec, flags=re.I).strip()
            return self._result(query, "comms", "whatsapp", 0.98, is_destructive, t0, {"recipient": rec, "message": msg})

        # F. Excel Spreadsheet Creation
        if any(k in q_low for k in ("excel", "spreadsheet", "xlsx", "sheet")):
            title_m = re.search(r'(?:create|make|open)\s+(?:an?\s+)?(?:excel|spreadsheet|sheet)?\s*(?:for|named|called|about)?\s*(.*)', q_norm, re.IGNORECASE)
            t_name = title_m.group(1).strip() if title_m else "Sheet"
            return self._result(query, "documents", "create_excel", 0.98, is_destructive, t0, {"title": t_name or "Spreadsheet"})

        # G. File and Folder Operations
        folder_m = re.search(r'(?:create|make)\s+(?:a\s+)?(?:folder|directory)\s+(?:named|called)?\s*([a-zA-Z0-9_\-\s]+)', q_norm, re.IGNORECASE)
        if folder_m:
            return self._result(query, "files", "create_folder", 0.98, is_destructive, t0, {"name": folder_m.group(1).strip()})

        file_m = re.search(r'(?:create|make)\s+(?:a\s+)?file\s+(?:named|called)?\s*([a-zA-Z0-9_.\-]+)(?:\s+(?:with|saying|and\s+write)\s+(.*))?', q_norm, re.IGNORECASE)
        if file_m:
            return self._result(query, "files", "create_file", 0.98, is_destructive, t0, {
                "name": file_m.group(1).strip(),
                "content": file_m.group(2).strip() if file_m.group(2) else ""
            })

        # H. Word Document & Note Creation
        doc_word = bool(re.search(r'\b(?:word|docx|winword)\b', q_low))
        doc_note = bool(re.search(r'\b(?:notepad|notebook|note|txt)\b', q_low))
        if ("write" in q_low or "create" in q_low or "type" in q_low or "draft" in q_low) and (doc_word or doc_note or "document" in q_low or "essay" in q_low):
            m = re.search(r'(?:write|type|draft|create)\s+(?:an?\s+)?(?:essay\s+about|report\s+on|note\s+about|document\s+about)?\s*(.*)', q_norm, re.IGNORECASE)
            raw = m.group(1).strip() if m else "General Document"
            raw = re.sub(r'^(?:in|into|on)\s+(?:word|notepad|notebook)\s*', '', raw, flags=re.I).strip()
            app = "word" if doc_word or "document" in q_low or "essay" in q_low else "notepad"
            return self._result(query, "documents", f"create_{app}", 0.98, is_destructive, t0, {
                "app": app,
                "topic": raw or "Document",
                "content": raw if any(k in raw.lower() for k in ("hello", "dear", "hi")) else None
            })

        # I. Universal App Opening
        if any(q_low.startswith(p) for p in ("open ", "launch ", "start ", "show ")) and not any(k in q_low for k in (" and ", " then ", " saying ", " write ", " send ")):
            app_target = re.sub(r'^(?:open|launch|start|show)\s+', '', q_norm, flags=re.I).strip()
            return self._result(query, "app", "open_target", 0.95, is_destructive, t0, {"target": app_target})

        # J. Web Search
        if any(q_low.startswith(p) for p in ("search google for ", "search web for ", "search for ", "google ", "look up ")):
            sq = re.sub(r'^(?:search\s+google\s+for|search\s+web\s+for|search\s+for|google|look\s+up)\s+', '', q_norm, flags=re.I).strip()
            return self._result(query, "web", "open_web", 0.95, is_destructive, t0, {"query": sq})

        # --------------------------------------------------------------------
        # 3. Fallback: General Intelligence & Conversation
        # --------------------------------------------------------------------
        return self._result(query, "brain", "think", 0.85, is_destructive, t0)

    @staticmethod
    def _result(query: str, domain: str, action: str, conf: float, destr: float, t0: float, params: Optional[Dict] = None) -> Dict[str, Any]:
        return {
            "query": query,
            "domain": domain,
            "action": action,
            "confidence": conf,
            "is_destructive": destr,
            "parameters": params or {},
            "routing_ms": (time.perf_counter() - t0) * 1000,
        }
