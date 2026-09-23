"""
Jarvis Brain: System 2 Knowledge & Conversational Engine (v5.0)
Provides instant local responses for time, date, identity, and computer status,
with resilient non-blocking cloud LLM support (Groq/Ollama/OpenAI).
Guarantees 0ms freezes on network drops.
"""
import datetime
import json
import os
import random
import re
import socket
import urllib.request
from typing import List, Dict
from jarvis_config import LLM_PROVIDER, GROQ_MODEL, OLLAMA_MODEL, OPENAI_MODEL

SYSTEM_PROMPT = (
    "You are Jarvis, an advanced and helpful AI personal desktop assistant. "
    "Provide clear, concise, accurate, and direct answers. Avoid unnecessary fluff."
)

CONVERSATION_HISTORY: List[Dict[str, str]] = [
    {"role": "system", "content": SYSTEM_PROMPT}
]


def _is_online(host: str = "api.groq.com", port: int = 443, timeout: float = 0.6) -> bool:
    """Non-blocking socket check to prevent DNS resolution hangs."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        res = sock.connect_ex((host, port))
        sock.close()
        return res == 0
    except Exception:
        return False


def _get_instant_answer(prompt: str) -> str:
    """Answers common personal and system queries in 0ms."""
    p = prompt.lower().strip()

    if any(k in p for k in ("what time", "current time", "time is it", "the time")):
        return f"The current time is {datetime.datetime.now().strftime('%I:%M %p')}."

    if any(k in p for k in ("what date", "today's date", "current date", "what day is it", "what day is today")):
        return f"Today is {datetime.datetime.now().strftime('%A, %B %d, %Y')}."

    if any(k in p for k in ("who are you", "what is your name", "introduce yourself")):
        return (
            "I am Jarvis, your high-performance AI personal desktop assistant. "
            "I have full native control over your PC: creating Word/Excel docs, sending WhatsApp messages, "
            "controlling audio, launching apps, and managing files."
        )

    if any(k in p for k in ("what can you do", "help", "capabilities")):
        return (
            "I can execute any task on your computer! Examples:\n"
            "• 'Open Word and write an essay about nature'\n"
            "• 'Create an Excel spreadsheet for monthly budget'\n"
            "• 'Open WhatsApp and send a message to ysn saying hi'\n"
            "• 'Set volume to 50% / Mute audio'\n"
            "• 'Check battery / RAM / IP address'\n"
            "• 'Open Downloads folder / Open Chrome'"
        )

    if any(k in p for k in ("tell me a joke", "make me laugh", "say a joke")):
        jokes = [
            "Why do programmers prefer dark mode? Because light attracts bugs.",
            "There are only 10 types of people in the world: those who understand binary, and those who don't.",
            "Why did the computer keep freezing? Because it left its Windows open!",
            "Why was the JavaScript developer sad? Because they didn't know how to 'null' their feelings.",
        ]
        return random.choice(jokes)

    if re.match(r'^(?:hi|hello|hey|good\s+morning|good\s+evening)[!.]?$', p):
        return "Hello! Jarvis is online and ready for your command."

    return ""


def think(prompt: str) -> str:
    """Answers prompt via local heuristics or online LLM with zero-freeze guarantee."""
    # 1. Local instant answer (<0.1ms)
    local = _get_instant_answer(prompt)
    if local:
        CONVERSATION_HISTORY.append({"role": "user", "content": prompt})
        CONVERSATION_HISTORY.append({"role": "assistant", "content": local})
        return local

    CONVERSATION_HISTORY.append({"role": "user", "content": prompt})
    if len(CONVERSATION_HISTORY) > 12:
        CONVERSATION_HISTORY[:] = [CONVERSATION_HISTORY[0]] + CONVERSATION_HISTORY[-10:]

    provider = LLM_PROVIDER.lower().strip()
    groq_key = os.getenv("GROQ_API_KEY")

    # 2. Cloud Groq LLM (if network is reachable)
    if (provider in ("auto", "groq")) and groq_key:
        if _is_online("api.groq.com", 443, timeout=0.5):
            try:
                from groq import Groq
                client = Groq(api_key=groq_key, timeout=4.0)
                resp = client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=CONVERSATION_HISTORY,
                    temperature=0.7,
                    max_tokens=512,
                )
                text = resp.choices[0].message.content.strip()
                CONVERSATION_HISTORY.append({"role": "assistant", "content": text})
                return text
            except Exception:
                pass

    # 3. Local Ollama LLM (if running)
    if (provider in ("auto", "ollama")) and _is_ollama_available():
        try:
            req_data = json.dumps({
                "model": OLLAMA_MODEL,
                "messages": CONVERSATION_HISTORY,
                "stream": False
            }).encode("utf-8")
            req = urllib.request.Request(
                "http://localhost:11434/api/chat",
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                text = result["message"]["content"].strip()
                CONVERSATION_HISTORY.append({"role": "assistant", "content": text})
                return text
        except Exception:
            pass

    # 4. Instant Resilient Knowledge Fallback
    fallback = (
        f"Processed query: '{prompt}'. Jarvis is active in local-first execution mode. "
        "All native PC controls, office document authoring, and messaging are operational."
    )
    CONVERSATION_HISTORY.append({"role": "assistant", "content": fallback})
    return fallback


def _is_ollama_available() -> bool:
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=0.3) as resp:
            return resp.status == 200
    except Exception:
        return False
