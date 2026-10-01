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

# Force UTF-8 stdout on Windows to prevent charmap/cp1252 print crashes
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

import laya.config as cfg

GROQ_API_KEY = getattr(cfg, "GROQ_API_KEY", os.getenv("GROQ_API_KEY"))
GROQ_MODEL = getattr(cfg, "GROQ_MODEL", os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"))
GROQ_FALLBACK_MODEL = getattr(cfg, "GROQ_FALLBACK_MODEL", os.getenv("GROQ_FALLBACK_MODEL", "openai/gpt-oss-20b"))
GROQ_TIMEOUT_SEC = float(getattr(cfg, "GROQ_TIMEOUT_SEC", 10.0))

OPENROUTER_API_KEY = getattr(cfg, "OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))
OPENROUTER_BASE_URL = getattr(cfg, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = getattr(cfg, "OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")
OPENROUTER_TIMEOUT_SEC = float(getattr(cfg, "OPENROUTER_TIMEOUT_SEC", 15.0))

OLLAMA_BASE_URL = getattr(cfg, "OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_MODEL = getattr(cfg, "OLLAMA_MODEL", "mistral:7b")
OLLAMA_TIMEOUT_SEC = float(getattr(cfg, "OLLAMA_TIMEOUT_SEC", 10.0))

from laya.orchestrator.tools_schema import TOOLS_SCHEMA, CORE_TOOLS_SCHEMA
import datetime
import win32gui
from laya.orchestrator.memory import get_memory_store
from laya.tools.interrupt_manager import is_interrupt_requested


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


def recover_failed_generation(err_obj: Exception) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Recover tool call and arguments when Groq fails server-side JSON parsing with HTTP 400."""
    raw = None
    body = getattr(err_obj, "body", None)
    if isinstance(body, dict):
        raw = body.get("error", {}).get("failed_generation")
    if not raw:
        s = str(err_obj)
        m = re.search(r"'failed_generation':\s*'(\{.*?\})'", s, re.DOTALL)
        if m:
            raw = m.group(1)
    if not raw:
        return None

    if isinstance(raw, dict):
        return raw.get("name"), raw.get("arguments", {})

    try:
        data = json.loads(raw)
        return data.get("name"), data.get("arguments", {})
    except Exception:
        pass

    try:
        cleaned = re.sub(r'\\(?![/"\\bfnrtu])', '', raw)
        data = json.loads(cleaned)
        return data.get("name"), data.get("arguments", {})
    except Exception:
        pass
    return None


def build_react_system_prompt() -> str:
    memory_summary = get_memory_store().get_all_summary()
    desktop_env = get_active_desktop_environment()
    return f"""You are Laya — an ultra-intelligent, charismatic, and witty autonomous desktop AI companion modeled after JARVIS with modern internet and meme culture literacy.
You possess complete, real control over the Windows OS, filesystem, applications, browser, and hardware via your provided tools.

Persona & Delivery:
- Sharp, confident, articulate, and subtly witty (classic JARVIS banter).
- Deliver 1-2 punchy spoken sentences. Never dump raw tables, stack traces, or tool logs into speech.
- Always DO the task immediately — never just describe what you would do.
- Speed & Decisiveness: Complete tasks in 1-2 steps maximum. If you know the answer, use `answer_question`.
- For creative/generative writing in Notepad (essays, poems, articles), call `write_to_notepad(text=...)` with the full generated text.
- If you need a specialized tool not in your core list (e.g. Excel, PowerPoint, cameras, window layout), call `search_tools(query=...)`.

Current Desktop State:
{desktop_env}

User Profile & Long-Term Memory:
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

        self.openrouter_client = None
        if OPENROUTER_API_KEY:
            try:
                from openai import OpenAI
                self.openrouter_client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=OPENROUTER_API_KEY)
            except Exception as e:
                print(f"[ReActAgent] OpenRouter init note: {e}")

    @classmethod
    def get_instance(cls) -> "ReActAgent":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _is_network_available(self) -> bool:
        """Fast 250ms socket probe to prevent hanging if offline or DNS fails."""
        import socket
        try:
            with socket.create_connection(("1.1.1.1", 53), timeout=0.25):
                return True
        except Exception:
            try:
                with socket.create_connection(("8.8.8.8", 53), timeout=0.25):
                    return True
            except Exception:
                return False

    def _is_ollama_online(self) -> bool:
        """Fast 200ms socket probe to prevent hanging if local Ollama daemon is down."""
        import socket
        try:
            with socket.create_connection(("localhost", 11434), timeout=0.25):
                return True
        except Exception:
            return False

    def run(
        self,
        query: str,
        tool_dispatcher: Any,
        history: Optional[List[Dict[str, str]]] = None,
        max_steps: int = 2,
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

        # Zero-LLM Fast Intercept for any timer/reminder queries that slipped into ReAct
        try:
            from laya.router.classifier import IntentRouter
            fast_d = IntentRouter.get_instance().route(query)
            if fast_d and fast_d.action in ["set_reminder", "list_reminders", "cancel_reminders", "clarify"]:
                if fast_d.action == "clarify":
                    return fast_d.clarification_prompt, "System"
                res = tool_dispatcher(fast_d.action, fast_d.params)
                return str(res), "FastPath"
        except Exception:
            pass

        # Check network availability before attempting cloud APIs to prevent hanging
        net_ok = self._is_network_available()

        # 1. Try Groq LPUs first for lightning speed (sub-second turns)
        if net_ok and self.groq_client:
            try:
                ans, prov = self._run_groq_loop(messages, tool_dispatcher, max_steps, step_callback=step_callback)
                return self._sanitize_response(ans, query, tool_dispatcher), prov
            except Exception as e:
                print(f"[ReActAgent] Groq attempt failed ({e})...")

        # 2. Try OpenRouter (Llama 3.3 70B) only if valid key is set
        if net_ok and self.openrouter_client and OPENROUTER_API_KEY and len(OPENROUTER_API_KEY) > 10:
            try:
                ans, prov = self._run_openrouter_loop(messages, tool_dispatcher, max_steps, step_callback=step_callback)
                return self._sanitize_response(ans, query, tool_dispatcher), prov
            except Exception as e:
                print(f"[ReActAgent] OpenRouter fallback failed ({e})...")

        # 3. Try Local GPU Ollama if running (no 40s freeze if port is closed)
        if self._is_ollama_online():
            try:
                ans, prov = self._run_ollama_loop(messages, tool_dispatcher, max_steps, step_callback=step_callback)
                return self._sanitize_response(ans, query, tool_dispatcher), prov
            except Exception as e:
                print(f"[ReActAgent] Local Ollama failed: {e}")

        # If network is offline and Ollama is offline, provide a clear and truthful message
        return "I apologize, my reasoning engine is currently unavailable. All deterministic system controls (apps, volume, windows, files, Telegram, Gmail) are operational.", "System"

    def _sanitize_response(self, final_text: str, query: str, tool_dispatcher: Any) -> str:
        """Prevent generic chat LLM refusals regarding timers, alarms, and OS automation."""
        low = final_text.lower()
        if any(phrase in low for phrase in [
            "can't set a timer", "cannot set a timer", "unable to set a timer",
            "don't have the ability to set a timer", "not able to set a timer",
            "open a timer app", "suggest a way to set one", "can't set timers",
            "suggest an online timer", "search for an online timer"
        ]):
            try:
                from laya.router.classifier import IntentRouter
                d = IntentRouter.get_instance().route(query)
                if d and d.action == "set_reminder":
                    obs = tool_dispatcher("set_reminder", d.params)
                    return f"Timer set: {obs}"
            except Exception:
                pass
            return "I have native desktop timer capabilities built in. How many minutes or seconds would you like me to set the timer for?"
        return final_text


    def _run_groq_loop(
        self,
        messages: List[Dict[str, Any]],
        tool_dispatcher: Any,
        max_steps: int,
        step_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[str, str]:
        step_count = 0
        executed_observations = []

        candidate_models = list(dict.fromkeys([
            GROQ_MODEL,
            GROQ_FALLBACK_MODEL,
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "qwen/qwen3.8-27b",
        ]))

        active_idx = 0
        active_model = candidate_models[active_idx]
        provider = f"Groq ({active_model})"

        while step_count < max_steps:
            if is_interrupt_requested():
                return "Operation was interrupted by user.", "Interrupted"
            step_count += 1
            if step_callback:
                step_callback(f"Thinking with {active_model} (step {step_count})...")

            response = None
            last_err = None

            # Try candidate models in order until one succeeds
            while active_idx < len(candidate_models):
                active_model = candidate_models[active_idx]
                try:
                    response = self.groq_client.chat.completions.create(
                        model=active_model,
                        messages=messages,
                        tools=CORE_TOOLS_SCHEMA,
                        tool_choice="auto",
                        temperature=0.1,
                        timeout=GROQ_TIMEOUT_SEC,
                    )
                    break
                except Exception as e:
                    last_err = e
                    err_str = str(e)
                    print(f"[ReActAgent] Model {active_model} failed ({err_str[:80]}), trying next fallback...")

                    # Recovery: check if Groq returned failed_generation with the generated tool call
                    recovered = recover_failed_generation(e)
                    if recovered:
                        func_name, args = recovered
                        if isinstance(args, dict):
                            args = {k: v for k, v in args.items() if v is not None}
                        try:
                            print(f"  -> [ReAct Step {step_count} (Recovered)] Tool Call: '{func_name}' with args {list(args.keys())}")
                        except Exception:
                            pass
                        obs = tool_dispatcher(func_name, args)
                        executed_observations.append(obs)
                        return str(obs).strip(), f"Groq ({active_model} recovered)"

                    active_idx += 1

            if response is None:
                if executed_observations:
                    return str(executed_observations[-1]), provider
                raise last_err or RuntimeError("All Groq candidate models failed.")

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

                    # Strip null values from arguments dictionary
                    if isinstance(args, dict):
                        args = {k: v for k, v in args.items() if v is not None}

                    try:
                        print(f"  -> [ReAct Step {step_count}] Tool Call: '{func_name}' with args {args}")
                    except Exception:
                        pass
                    if step_callback:
                        step_callback(f"Executing: {func_name}({list(args.values())[:2]})")

                    obs = tool_dispatcher(func_name, args)
                    executed_observations.append(obs)

                    # Immediate zero-latency return for terminal single-turn tools — no redundant second LLM hop
                    if func_name == "answer_question":
                        return str(obs).strip(), provider

                    if func_name in [
                        "write_to_notepad", "create_file", "write_to_file",
                        "create_word_document", "create_notebook", "write_notebook_cell",
                        "set_reminder", "cancel_reminders", "play_youtube"
                    ]:
                        return str(obs).strip(), provider

                    # Check for stop/interrupt after EACH tool call so we halt mid-sequence
                    if is_interrupt_requested():
                        return "Stopped.", "Interrupted"

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
                    last_obs = str(executed_observations[-1])
                    if "Launched" in last_obs or "notepad" in last_obs:
                        final_text = "I located and opened your requested file."
                    else:
                        final_text = "I completed the requested action on your desktop."
                return final_text, provider

        # If reached max steps, summarize concisely without raw debug dumps
        if executed_observations:
            last_obs = str(executed_observations[-1])
            if "Launched" in last_obs or "notepad" in last_obs:
                return "I located your note and opened it on your desktop.", provider
            return "I completed the requested operations on your desktop.", provider
        return "I completed the requested operations.", provider

    def _run_openrouter_loop(
        self,
        messages: List[Dict[str, Any]],
        tool_dispatcher: Any,
        max_steps: int,
        step_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[str, str]:
        provider = f"OpenRouter ({OPENROUTER_MODEL.split('/')[-1]})"
        step_count = 0
        executed_observations = []

        while step_count < max_steps:
            if is_interrupt_requested():
                return "Operation was interrupted by user.", "Interrupted"
            step_count += 1
            if step_callback:
                step_callback(f"Thinking with 70B ({OPENROUTER_MODEL.split('/')[-1]} step {step_count})...")

            response = self.openrouter_client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=messages,
                tools=TOOLS_SCHEMA,
                tool_choice="auto",
                temperature=0.1,
                timeout=OPENROUTER_TIMEOUT_SEC,
            )

            msg = response.choices[0].message

            if msg.tool_calls:
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

                    try:
                        print(f"  -> [ReAct Step {step_count} (OpenRouter 70B)] Tool Call: '{func_name}' with args {args}")
                    except Exception:
                        pass
                    if step_callback:
                        step_callback(f"Executing: {func_name}({list(args.values())[:2]})")

                    obs = tool_dispatcher(func_name, args)
                    executed_observations.append(obs)

                    # Halt immediately if user said stop between tool calls
                    if is_interrupt_requested():
                        return "Stopped.", "Interrupted"

                    if step_callback:
                        obs_str = str(obs).strip()
                        summary_obs = (obs_str[:65] + "...") if len(obs_str) > 65 else obs_str
                        step_callback(f"Result: {summary_obs}")

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": func_name,
                        "content": str(obs)[:1000],
                    })
            else:
                final_text = (msg.content or "").strip()
                if not final_text and executed_observations:
                    last_obs = str(executed_observations[-1])
                    if "Launched" in last_obs or "notepad" in last_obs:
                        final_text = "I located and opened your requested file."
                    else:
                        final_text = "I completed the requested action on your desktop."
                return final_text, provider

        if executed_observations:
            last_obs = str(executed_observations[-1])
            if "Launched" in last_obs or "notepad" in last_obs:
                return "I located your note and opened it on your desktop.", provider
            return "I completed the requested operations on your desktop.", provider
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
            if is_interrupt_requested():
                return "Operation was interrupted by user.", "Interrupted"
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
                    try:
                        print(f"  -> [ReAct Step {step_count} (Ollama)] Tool Call: '{fn}' with args {args}")
                    except Exception:
                        pass
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
                    last_obs = str(executed_observations[-1])
                    if "Launched" in last_obs or "notepad" in last_obs:
                        final_text = "I located and opened your requested file."
                    else:
                        final_text = "I completed the requested action on your desktop."
                return final_text, provider

        if executed_observations:
            last_obs = str(executed_observations[-1])
            if "Launched" in last_obs or "notepad" in last_obs:
                return "I located your note and opened it on your desktop.", provider
            return "I completed the requested operations on your desktop.", provider
        return "I completed the requested operations.", provider


def get_react_agent() -> ReActAgent:
    return ReActAgent.get_instance()
