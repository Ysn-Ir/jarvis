"""
Laya Autonomous ReAct (Reasoning + Acting) Agent Loop
True perception-action agent loop:
Thought -> Typed Tool Call -> OS Observation -> Adaptive Next Step -> Final Synthesis.
Supports Groq (openai/gpt-oss-20b) with automatic fallback to local Ollama (mistral:7b).
"""

import os
import sys
import json
import time
import urllib.request
from typing import Dict, Any, List, Optional, Tuple

from laya.config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    GROQ_FALLBACK_MODEL,
    GROQ_TIMEOUT_SEC,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT_SEC,
)
from laya.orchestrator.tools_schema import TOOLS_SCHEMA
from laya.orchestrator.memory import get_memory_store


def build_react_system_prompt() -> str:
    memory_summary = get_memory_store().get_all_summary()
    return f"""You are Laya, a State-of-the-Art autonomous Windows desktop computer agent modeled after Open-Interpreter and Microsoft UFO.
You possess COMPLETE control over the operating system, applications, files, GUI, code execution, and hardware.

Core Execution Paradigms:
1. UNIVERSAL CODE EXECUTION (Open-Interpreter):
   - When asked to perform complex data analysis, file batch operations, calculation, regex, web scraping, API queries, or open-ended automation, use `run_python` to execute Python code.
   - You have access to os, sys, shutil, requests, bs4, psutil, win32gui, uiautomation, math, json, and csv.

2. LIVE WEB INTELLIGENCE:
   - When asked about real-world facts, current news, weather, sports scores, documentation, or online info, use `live_web_search` to fetch real search summaries and URLs so you can speak the actual answer.
   - Use `fetch_webpage_content` to download and read articles or documentation from specific URLs.

3. WINDOWS UI AUTOMATION (Microsoft UFO):
   - For applications on Windows, use `inspect_window_controls` to see all buttons, edits, and tabs.
   - Use `click_window_control` or `set_window_control_text` to control applications reliably by name.
   - Use `list_open_windows` and `focus_window` to manage active tasks.

4. DEEP FILESYSTEM INTELLIGENCE:
   - Use `read_file_content` to inspect files, notes, or scripts.
   - Use `search_filesystem` to find files matching wildcard patterns.
   - Use `list_directory` to see files in any directory.

5. PERCEPTION-ACTION REASONING:
   - When given a task, decide the best tools, call them, observe the OS outputs, adapt if needed, and synthesize a concise, helpful spoken response once done.

Active User Memories & Preferences:
{memory_summary}
"""


class ReActAgent:
    _instance: Optional["ReActAgent"] = None

    def __init__(self):
        self.groq_client = None
        if GROQ_API_KEY:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=GROQ_API_KEY)
            except Exception as e:
                print(f"[ReActAgent] Groq init note: {e}")

    @classmethod
    def get_instance(cls) -> "ReActAgent":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def run(
        self,
        query: str,
        tool_dispatcher: Any,
        history: Optional[List[Dict[str, str]]] = None,
        max_steps: int = 6,
    ) -> Tuple[str, str]:
        """
        Execute the autonomous ReAct perception-action loop.
        Returns: (final_speech_text, provider_name)
        """
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": build_react_system_prompt()}
        ]

        if history:
            for msg in history[-6:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ["user", "assistant"] and content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": query})

        # Try Groq first, fall back to Ollama if network is down
        try:
            if self.groq_client:
                return self._run_groq_loop(messages, tool_dispatcher, max_steps)
        except Exception as e:
            print(f"[ReActAgent] Groq loop encountered: {e}, switching to local Ollama...")

        # Ollama local loop
        return self._run_ollama_loop(messages, tool_dispatcher, max_steps)

    def _run_groq_loop(
        self,
        messages: List[Dict[str, Any]],
        tool_dispatcher: Any,
        max_steps: int,
    ) -> Tuple[str, str]:
        provider = f"Groq ({GROQ_MODEL})"
        step_count = 0
        executed_observations = []

        active_model = GROQ_MODEL
        while step_count < max_steps:
            step_count += 1
            try:
                response = self.groq_client.chat.completions.create(
                    model=active_model,
                    messages=messages,
                    tools=TOOLS_SCHEMA,
                    tool_choice="auto",
                    temperature=0.1,
                    timeout=GROQ_TIMEOUT_SEC,
                )
            except Exception as e:
                if active_model != GROQ_FALLBACK_MODEL:
                    print(f"[ReActAgent] Model {active_model} returned {e}, falling back to {GROQ_FALLBACK_MODEL}...")
                    active_model = GROQ_FALLBACK_MODEL
                    response = self.groq_client.chat.completions.create(
                        model=active_model,
                        messages=messages,
                        tools=TOOLS_SCHEMA,
                        tool_choice="auto",
                        temperature=0.1,
                        timeout=GROQ_TIMEOUT_SEC,
                    )
                else:
                    raise e

            provider = f"Groq ({active_model})"
            msg = response.choices[0].message

            # Check if model wants to call tools
            if msg.tool_calls:
                # Add assistant message with tool calls to context
                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            }
                        }
                        for tc in msg.tool_calls
                    ]
                })

                for tc in msg.tool_calls:
                    func_name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                    except Exception:
                        args = {}

                    print(f"  ▶ [ReAct Step {step_count}] Tool Call: '{func_name}' with args {args}")
                    obs = tool_dispatcher(func_name, args)
                    executed_observations.append(obs)

                    # Feed observation back into conversation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": func_name,
                        "content": str(obs),
                    })
            else:
                # Model finished planning and provided final answer
                final_text = (msg.content or "").strip()
                if not final_text and executed_observations:
                    final_text = " | ".join(executed_observations)
                return final_text, provider

        # If reached max steps, summarize
        if executed_observations:
            return " | ".join(executed_observations), provider
        return "I completed the requested operations.", provider

    def _run_ollama_loop(
        self,
        messages: List[Dict[str, Any]],
        tool_dispatcher: Any,
        max_steps: int,
    ) -> Tuple[str, str]:
        provider = f"Local Ollama ({OLLAMA_MODEL})"
        step_count = 0
        executed_observations = []

        # Convert tools to Ollama format
        while step_count < max_steps:
            step_count += 1
            payload = {
                "model": OLLAMA_MODEL,
                "messages": messages,
                "tools": TOOLS_SCHEMA,
                "stream": False,
                "temperature": 0.1,
            }
            req = urllib.request.Request(
                f"{OLLAMA_BASE_URL}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )

            try:
                with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT_SEC) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    msg = data["choices"][0]["message"]
            except Exception as e:
                print(f"[ReActAgent] Local Ollama request failed: {e}")
                break

            tool_calls = msg.get("tool_calls")
            if tool_calls:
                messages.append(msg)
                for tc in tool_calls:
                    fn = tc["function"]["name"]
                    raw_args = tc["function"]["arguments"]
                    args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                    print(f"  ▶ [ReAct Step {step_count} (Ollama)] Tool Call: '{fn}' with args {args}")
                    obs = tool_dispatcher(fn, args)
                    executed_observations.append(obs)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id", f"call_{int(time.time())}"),
                        "name": fn,
                        "content": str(obs),
                    })
            else:
                final_text = (msg.get("content") or "").strip()
                if not final_text and executed_observations:
                    final_text = " | ".join(executed_observations)
                return final_text, provider

        if executed_observations:
            return " | ".join(executed_observations), provider
        return "I completed the requested operations.", provider


def get_react_agent() -> ReActAgent:
    return ReActAgent.get_instance()
