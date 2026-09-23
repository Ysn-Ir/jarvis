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
from typing import Dict, Any, List, Optional, Tuple, Callable

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
import datetime
import win32gui
from laya.orchestrator.memory import get_memory_store


def get_active_desktop_environment() -> str:
    now_str = datetime.datetime.now().strftime("%A, %b %d, %Y - %I:%M %p")
    windows = []
    def enum_handler(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd).strip()
            if t and t not in ["Default IME", "MSCTFIME UI", "Program Manager"]:
                rect = win32gui.GetWindowRect(hwnd)
                if (rect[2] - rect[0]) > 100 and (rect[3] - rect[1]) > 100:
                    windows.append(t)
        return True
    try:
        win32gui.EnumWindows(enum_handler, None)
    except Exception:
        pass

    wins_summary = ", ".join([f"'{w}'" for w in windows[:6]]) if windows else "Desktop"
    return f"Time: {now_str}\nVisible Windows: {wins_summary}"


def build_react_system_prompt() -> str:
    memory_summary = get_memory_store().get_all_summary()
    desktop_env = get_active_desktop_environment()
    return f"""You are Laya, a State-of-the-Art autonomous Windows desktop computer agent modeled after Open-Interpreter and Microsoft UFO.
You possess COMPLETE control over the operating system, applications, files, GUI, code execution, and hardware.

Current Desktop State:
{desktop_env}

Core Execution Paradigms:
1. UNIVERSAL CODE EXECUTION (Open-Interpreter):
   - When asked to perform complex data analysis, calculations, regex, scraping, batch file operations, or open-ended automation, use `run_python` to execute Python code.
   - Standard libraries available: os, sys, shutil, requests, bs4, psutil, win32gui, uiautomation, math, json, csv.

2. LIVE WEB INTELLIGENCE:
   - When asked to search for anything (people, entities, YouTube creators, news, facts, scores, documentation), use `web_search` or `live_web_search` to fetch real summaries and speak the actual answer.
   - Use `fetch_webpage_content` to download and read articles or documentation from specific URLs.

3. WINDOWS UI AUTOMATION (Microsoft UFO):
   - For applications on Windows, use `inspect_window_controls` to see all buttons, edits, and tabs.
   - Use `click_window_control` or `set_window_control_text` to control applications reliably by name.
   - Use `list_open_windows` and `focus_window` to manage active tasks.
   - Use `press_key` and `window_action` for window/keyboard shortcuts.

4. DEEP FILESYSTEM & PRODUCTIVITY:
   - If asked to write a memo, note, or record information: use `create_note` or `create_file`.
   - Use `read_file_content` to inspect files, notes, or scripts.
   - Use `search_filesystem` to find files matching wildcard patterns.
   - Use `list_directory` to see files in any directory.

5. JUPYTER NOTEBOOK AUTONOMY:
   - When asked to write code, comments, or notes in a Jupyter notebook (.ipynb):
     Use `write_notebook_cell(notebook_path, code, cell_type)` to write/append cells directly with 100% precision!
   - Use `read_notebook_cells(notebook_path)` to inspect existing cells.

6. GUI DRAWING & CANVAS ACTIONS:
   - When asked to draw, paint, or sketch (e.g. in MS Paint):
     1. Launch Paint with `open_app("paint")` or `run_powershell("Start-Process mspaint")`.
     2. Use `run_python` with `pyautogui` or `mouse_drag` to draw parametric shapes on the canvas.

7. PERCEPTION-ACTION REASONING:
   - When given a task, decide the best tools, call them, observe the OS outputs, adapt if needed, and synthesize a concise, helpful spoken response once done.
   - If the user asks a conversational question or asks for ideas, answer directly and articulately.

Active User Memories & Preferences:
{memory_summary}
"""


class ReActAgent:
    _instance: Optional["ReActAgent"] = None

    def __init__(self):
        self.groq_client = None
        self._groq_failed = False
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
        step_callback: Optional[Callable[[str], None]] = None,
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

        # Try Groq first if available, fall back to Ollama if network is down
        if self.groq_client:
            try:
                return self._run_groq_loop(messages, tool_dispatcher, max_steps, step_callback=step_callback)
            except Exception as e:
                print(f"[ReActAgent] Groq attempt failed: {e}, falling back to local Ollama...")

        # Ollama local loop
        return self._run_ollama_loop(messages, tool_dispatcher, max_steps, step_callback=step_callback)

    def _run_groq_loop(
        self,
        messages: List[Dict[str, Any]],
        tool_dispatcher: Any,
        max_steps: int,
        step_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[str, str]:
        provider = f"Groq ({GROQ_MODEL})"
        step_count = 0
        executed_observations = []

        active_model = GROQ_MODEL
        while step_count < max_steps:
            step_count += 1
            if step_callback:
                step_callback(f"Thinking with {active_model} (step {step_count})...")

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
                    if step_callback:
                        step_callback(f"Executing: {func_name}({list(args.values())[:2]})")

                    obs = tool_dispatcher(func_name, args)
                    executed_observations.append(obs)

                    if step_callback:
                        obs_str = str(obs).strip()
                        summary_obs = (obs_str[:65] + "...") if len(obs_str) > 65 else obs_str
                        step_callback(f"Result: {summary_obs}")

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
        step_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[str, str]:
        provider = f"Local Ollama ({OLLAMA_MODEL})"
        step_count = 0
        executed_observations = []

        # Convert tools to Ollama format
        while step_count < max_steps:
            step_count += 1
            if step_callback:
                step_callback(f"Local GPU thinking (step {step_count})...")

            payload = {
                "model": OLLAMA_MODEL,
                "messages": messages,
                "tools": TOOLS_SCHEMA,
                "stream": False,
                "temperature": 0.1,
                "options": {
                    "num_gpu": 99,
                    "num_thread": 8,
                }
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
                if executed_observations:
                    return " | ".join(executed_observations), provider
                return f"I encountered an issue connecting to the local reasoning engine: {e}. Please ensure Ollama is running.", provider

            tool_calls = msg.get("tool_calls")
            if tool_calls:
                messages.append(msg)
                for tc in tool_calls:
                    fn = tc["function"]["name"]
                    raw_args = tc["function"]["arguments"]
                    args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                    print(f"  ▶ [ReAct Step {step_count} (Ollama)] Tool Call: '{fn}' with args {args}")
                    if step_callback:
                        step_callback(f"Executing: {fn}({list(args.values())[:2]})")

                    obs = tool_dispatcher(fn, args)
                    executed_observations.append(obs)

                    if step_callback:
                        obs_str = str(obs).strip()
                        summary_obs = (obs_str[:65] + "...") if len(obs_str) > 65 else obs_str
                        step_callback(f"Result: {summary_obs}")

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
