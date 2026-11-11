"""
Laya Autonomous ReAct (Reasoning + Acting) Agent Loop
True perception-action agent loop:
Thought -> Typed Tool Call -> OS Observation -> Adaptive Next Step -> Final Synthesis.
Supports Groq (openai/gpt-oss-20b) with automatic fallback to local Ollama (mistral:7b).
"""

import os
import sys
import re
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
from laya.mcp import get_mcp_hub
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
    return f"""You are Laya — an autonomous desktop AI assistant with complete control over Windows, applications, browsers, files, and system hardware via Model Context Protocol (MCP) tools.

Persona:
- JARVIS-style witty, confident, articulate, and punchy.
- Always execute requested actions immediately using the tools provided.
- Keep spoken replies to 1-2 articulate sentences. Do not read raw JSON or code in speech.

Desktop State:
{desktop_env}

User Context:
{memory_summary}
"""


class ReActAgent:
    _instance: Optional["ReActAgent"] = None

    def __init__(self):
        self.mcp_hub = get_mcp_hub()
        self.groq_client = None
        self.openrouter_client = None
        self.external_client = None
        self.reload_clients()

    def reload_clients(self):
        """Hot-reload API clients dynamically from runtime environment/RuntimeManager."""
        from laya.runtime_manager import get_runtime_manager
        rt = get_runtime_manager()

        g_key = os.getenv("GROQ_API_KEY", GROQ_API_KEY or "").strip()
        if g_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=g_key)
            except Exception as e:
                print(f"[ReActAgent] Groq init note: {e}")
        else:
            self.groq_client = None

        or_key = os.getenv("OPENROUTER_API_KEY", OPENROUTER_API_KEY or "").strip()
        if or_key:
            try:
                from openai import OpenAI
                self.openrouter_client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=or_key)
            except Exception as e:
                print(f"[ReActAgent] OpenRouter init note: {e}")
        else:
            self.openrouter_client = None

        ext_key = (rt.external_api_key or os.getenv("EXTERNAL_API_KEY", "")).strip()
        ext_url = (rt.external_base_url or os.getenv("EXTERNAL_BASE_URL", "https://api.openai.com/v1")).strip()
        if ext_key:
            try:
                from openai import OpenAI
                self.external_client = OpenAI(base_url=ext_url, api_key=ext_key)
            except Exception as e:
                print(f"[ReActAgent] External client init note: {e}")
        else:
            self.external_client = None

    @classmethod
    def get_instance(cls) -> "ReActAgent":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _is_network_available(self) -> bool:
        """Fast socket probe to check connectivity to cloud APIs."""
        import socket
        for host in ["api.groq.com", "openrouter.ai", "1.1.1.1"]:
            try:
                with socket.create_connection((host, 443), timeout=1.5):
                    return True
            except Exception:
                continue
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
        max_steps: int = 6,
        step_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[str, str]:
        """
        Execute the autonomous ReAct perception-action loop.
        Respects runtime inference_mode ('auto' | 'local_mistral' | 'external_api').
        Returns: (final_speech_text, provider_name)
        """
        from laya.runtime_manager import get_runtime_manager
        rt = get_runtime_manager()
        rt.log_event("LLM", f"Query received (mode={rt.inference_mode}): '{query[:100]}'")
        self.mcp_hub.reset_sticky_tools()

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

        mode = rt.inference_mode

        # MODE A: Dedicated Local Mistral / Ollama
        if mode == "local_mistral":
            rt.ensure_ollama_running(wait_sec=6.0)
            if self._is_ollama_online():
                try:
                    ans, prov = self._run_ollama_loop(messages, tool_dispatcher, max_steps, step_callback=step_callback)
                    return self._sanitize_response(ans, query, tool_dispatcher), prov
                except Exception as e:
                    rt.log_event("LLM", f"Local Ollama loop error: {e}", level="ERROR")
            return f"Local model '{rt.local_model}' is unavailable. Please ensure Ollama is installed and running.", "Local Ollama"

        net_ok = self._is_network_available()

        # MODE B: Dedicated External API Key / Custom Endpoint
        if mode == "external_api" and net_ok and self.external_client:
            try:
                ans, prov = self._run_external_loop(messages, tool_dispatcher, max_steps, step_callback=step_callback)
                return self._sanitize_response(ans, query, tool_dispatcher), prov
            except Exception as e:
                rt.log_event("LLM", f"External API attempt failed ({e}), trying fallbacks...", level="WARN")

        # MODE C (Auto) or Fallback Chain: Groq -> External API -> OpenRouter -> Local Mistral
        if net_ok and self.groq_client:
            try:
                ans, prov = self._run_groq_loop(messages, tool_dispatcher, max_steps, step_callback=step_callback)
                return self._sanitize_response(ans, query, tool_dispatcher), prov
            except Exception as e:
                rt.log_event("LLM", f"Groq attempt failed ({e})...", level="WARN")

        if net_ok and self.external_client:
            try:
                ans, prov = self._run_external_loop(messages, tool_dispatcher, max_steps, step_callback=step_callback)
                return self._sanitize_response(ans, query, tool_dispatcher), prov
            except Exception as e:
                rt.log_event("LLM", f"External fallback failed ({e})...", level="WARN")

        if net_ok and self.openrouter_client and os.getenv("OPENROUTER_API_KEY", "").strip():
            try:
                ans, prov = self._run_openrouter_loop(messages, tool_dispatcher, max_steps, step_callback=step_callback)
                return self._sanitize_response(ans, query, tool_dispatcher), prov
            except Exception as e:
                rt.log_event("LLM", f"OpenRouter fallback failed ({e})...", level="WARN")

        if rt.ensure_ollama_running(wait_sec=4.0) or self._is_ollama_online():
            try:
                ans, prov = self._run_ollama_loop(messages, tool_dispatcher, max_steps, step_callback=step_callback)
                return self._sanitize_response(ans, query, tool_dispatcher), prov
            except Exception as e:
                rt.log_event("LLM", f"Local Ollama fallback failed: {e}", level="ERROR")

        return "I apologize, my reasoning engine is currently unavailable. Please configure an API key or switch to Local Mistral in Settings.", "System"

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
            user_q = next((str(m.get("content", "")) for m in reversed(messages) if m.get("role") == "user"), "")
            mcp_tools = self.mcp_hub.get_core_tools_schema(query=user_q)

            # Try candidate models in order until one succeeds
            while active_idx < len(candidate_models):
                active_model = candidate_models[active_idx]
                try:
                    response = self.groq_client.chat.completions.create(
                        model=active_model,
                        messages=messages,
                        tools=mcp_tools if mcp_tools else CORE_TOOLS_SCHEMA,
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

                    # Immediate zero-latency return for conversational answer_question
                    if func_name == "answer_question":
                        return str(obs).strip(), provider

                    # Check for stop/interrupt after EACH tool call so we halt mid-sequence
                    if is_interrupt_requested():
                        return "Stopped.", "Interrupted"

                    if step_callback:
                        obs_str = str(obs).strip()
                        summary_obs = (obs_str[:65] + "...") if len(obs_str) > 65 else obs_str
                        step_callback(f"Result: {summary_obs}")

                    # Feed observation back into conversation (truncated to prevent token bloat)
                    obs_text = str(obs)
                    if len(obs_text) > 1200:
                        obs_text = obs_text[:1200] + "\n...[output truncated for brevity]"

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": func_name,
                        "content": obs_text,
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

    def _run_external_loop(
        self,
        messages: List[Dict[str, Any]],
        tool_dispatcher: Any,
        max_steps: int,
        step_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[str, str]:
        """Run ReAct loop against any user-configured external OpenAI-compatible API endpoint."""
        from laya.runtime_manager import get_runtime_manager
        rt = get_runtime_manager()
        ext_model = (rt.external_model or "gpt-4o-mini").strip()
        provider = f"External ({ext_model})"
        step_count = 0
        executed_observations = []

        while step_count < max_steps:
            if is_interrupt_requested():
                return "Operation was interrupted by user.", "Interrupted"
            step_count += 1
            if step_callback:
                step_callback(f"Thinking with External {ext_model} (step {step_count})...")

            user_q = next((str(m.get("content", "")) for m in reversed(messages) if m.get("role") == "user"), "")
            mcp_tools = self.mcp_hub.get_core_tools_schema(query=user_q)
            response = self.external_client.chat.completions.create(
                model=ext_model,
                messages=messages,
                tools=mcp_tools if mcp_tools else CORE_TOOLS_SCHEMA,
                tool_choice="auto",
                temperature=0.1,
                timeout=20.0,
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
                    if isinstance(args, dict):
                        args = {k: v for k, v in args.items() if v is not None}

                    rt.log_event("TOOL", f"[External] Calling {func_name}({list(args.keys())})")
                    if step_callback:
                        step_callback(f"Executing: {func_name}({list(args.values())[:2]})")

                    obs = tool_dispatcher(func_name, args)
                    executed_observations.append(obs)

                    if func_name == "answer_question":
                        return str(obs).strip(), provider
                    if is_interrupt_requested():
                        return "Stopped.", "Interrupted"

                    obs_text = str(obs)
                    if len(obs_text) > 1200:
                        obs_text = obs_text[:1200] + "\n...[truncated]"
                    if step_callback:
                        step_callback(f"Result: {obs_text[:65]}...")

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": func_name,
                        "content": obs_text,
                    })
            else:
                final_text = (msg.content or "").strip()
                if not final_text and executed_observations:
                    final_text = "I completed the requested action on your desktop."
                return final_text, provider

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

            user_q = next((str(m.get("content", "")) for m in reversed(messages) if m.get("role") == "user"), "")
            mcp_tools = self.mcp_hub.get_core_tools_schema(query=user_q)
            response = self.openrouter_client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=messages,
                tools=mcp_tools if mcp_tools else TOOLS_SCHEMA,
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

    def _extract_fallback_tool_calls(self, content: str, valid_names: Optional[List[str]] = None, allow_ps_fence: bool = False) -> Optional[List[Dict[str, Any]]]:
        """Extract tool calls if a local model (like Mistral 7B) emits JSON or function-call syntax in content."""
        if not content:
            return None
        txt = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

        # Pattern 1: Mistral [TOOL_CALLS] [{"name": ..., "arguments": {...}}]
        m_tag = re.search(r"\[TOOL_CALLS\]\s*(\[.*\]|\{.*\})", txt, re.DOTALL)
        raw_json = m_tag.group(1) if m_tag else None

        # Pattern 2: fenced ```json {"name": ..., "arguments": {...}} ```
        if not raw_json:
            m_fence = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", txt, re.DOTALL)
            if m_fence:
                raw_json = m_fence.group(1)

        if raw_json:
            try:
                parsed = json.loads(raw_json)
                items = parsed if isinstance(parsed, list) else [parsed]
                tcs = []
                for idx, item in enumerate(items):
                    if isinstance(item, dict) and "name" in item:
                        tcs.append({
                            "id": f"local_call_{int(time.time())}_{idx}",
                            "type": "function",
                            "function": {
                                "name": item["name"],
                                "arguments": item.get("arguments", {}),
                            }
                        })
                if tcs:
                    return tcs
            except Exception:
                pass

        # Pattern 3: Function call expression or colon syntax emitted by local models:
        #   - PowerShell(command="...")
        #   - PowerShell({ command: "..." })
        #   - PowerShell: command="..."
        if valid_names:
            import ast
            names_pat = "|".join(re.escape(n) for n in sorted(valid_names, key=len, reverse=True))

            # 3a. Parentheses style: ToolName(...)
            call_m = re.search(rf"\b({names_pat})\s*\((.*?)\)", txt, re.DOTALL)
            if call_m:
                fn_name = call_m.group(1)
                inner = call_m.group(2).strip()
                expr_str = f"{fn_name}({inner})"
                try:
                    node = ast.parse(expr_str, mode="eval").body
                    if isinstance(node, ast.Call):
                        kwargs = {}
                        for kw in node.keywords:
                            if kw.arg:
                                kwargs[kw.arg] = ast.literal_eval(kw.value)
                        if not kwargs and len(node.args) == 1:
                            val = ast.literal_eval(node.args[0])
                            if isinstance(val, dict):
                                kwargs = val
                            else:
                                key_guess = "command" if fn_name == "PowerShell" else "url" if fn_name in ("browser_navigate", "fetch") else "query"
                                kwargs[key_guess] = val
                        return [{
                            "id": f"local_call_{int(time.time())}",
                            "type": "function",
                            "function": {"name": fn_name, "arguments": kwargs}
                        }]
                except Exception:
                    # Fallback for unquoted JS object keys like ToolName({ command: "..." })
                    kv_m = re.findall(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*["\'](.+?)["\']', inner)
                    if kv_m:
                        return [{
                            "id": f"local_call_{int(time.time())}",
                            "type": "function",
                            "function": {"name": fn_name, "arguments": {k: v for k, v in kv_m}}
                        }]

            # 3b. Colon style: PowerShell: command="..."
            colon_m = re.search(rf"\b({names_pat})\s*:\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*([\"'])(.+?)\3", txt, re.DOTALL)
            if colon_m:
                fn_name = colon_m.group(1)
                arg_k = colon_m.group(2)
                arg_v = colon_m.group(4)
                return [{
                    "id": f"local_call_{int(time.time())}",
                    "type": "function",
                    "function": {"name": fn_name, "arguments": {arg_k: arg_v}}
                }]

            # 3c. Fenced PowerShell script emitted instead of tool call on initial step by local 7B models
            if allow_ps_fence and "PowerShell" in valid_names:
                ps_m = re.search(r"```(?:powershell|ps1)\s*\n(.*?)```", txt, re.DOTALL | re.IGNORECASE)
                if ps_m:
                    cmd_txt = ps_m.group(1).strip()
                    if cmd_txt:
                        return [{
                            "id": f"local_ps_{int(time.time())}",
                            "type": "function",
                            "function": {"name": "PowerShell", "arguments": {"command": cmd_txt}}
                        }]
        return None

    def _run_ollama_loop(
        self,
        messages: List[Dict[str, Any]],
        tool_dispatcher: Any,
        max_steps: int,
        step_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[str, str]:
        from laya.runtime_manager import get_runtime_manager
        rt = get_runtime_manager()
        local_model = (rt.local_model or OLLAMA_MODEL or "mistral:7b").strip()
        base = (rt.ollama_base_url or OLLAMA_BASE_URL or "http://localhost:11434").strip().rstrip("/")
        ollama_root = base[:-3] if base.endswith("/v1") else base
        provider = f"Local Ollama ({local_model})"
        step_count = 0
        executed_observations = []

        # Keep concise context for 7B local models (system + latest turns) so history never crowds out tool calls
        if len(messages) > 4:
            local_messages = [messages[0]] + list(messages[-2:])
        else:
            local_messages = list(messages)
        if local_messages and local_messages[0].get("role") == "system":
            local_messages[0] = {
                "role": "system",
                "content": local_messages[0]["content"] + "\nCRITICAL: Always call the provided MCP function tools instead of guessing outputs or printing commands as prose."
            }

        while step_count < max_steps:
            if is_interrupt_requested():
                return "Operation was interrupted by user.", "Interrupted"
            step_count += 1
            if step_callback:
                step_callback(f"Local {local_model} thinking (step {step_count})...")

            user_q = next((str(m.get("content", "")) for m in reversed(local_messages) if m.get("role") == "user"), "")
            mcp_tools = self.mcp_hub.get_core_tools_schema(query=user_q, compact_local=True)
            payload = {
                "model": local_model,
                "messages": local_messages,
                "tools": mcp_tools if mcp_tools else CORE_TOOLS_SCHEMA,
                "stream": False,
                "keep_alive": "10m",
                "options": {
                    "num_ctx": 8192,
                    "temperature": 0.0,
                }
            }
            req = urllib.request.Request(
                f"{ollama_root}/api/chat",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )

            try:
                ollama_timeout = max(float(OLLAMA_TIMEOUT_SEC), 60.0)
                with urllib.request.urlopen(req, timeout=ollama_timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    msg = data.get("message") or data.get("choices", [{}])[0].get("message", {})
            except Exception as e:
                rt.log_event("LLM", f"Local Ollama ({local_model}) error: {e}", level="ERROR")
                print(f"[ReActAgent] Local Ollama request failed: {e}")
                if executed_observations:
                    return " | ".join(executed_observations), provider
                return f"I encountered an issue connecting to local {local_model}: {e}. Please ensure Ollama is running.", provider

            valid_tool_names = [t["function"]["name"] for t in (mcp_tools if mcp_tools else CORE_TOOLS_SCHEMA)]
            tool_calls = msg.get("tool_calls") or self._extract_fallback_tool_calls(
                msg.get("content", ""),
                valid_names=valid_tool_names,
                allow_ps_fence=(len(executed_observations) == 0),
            )
            if tool_calls:
                local_messages.append({
                    "role": "assistant",
                    "content": msg.get("content") or "",
                    "tool_calls": tool_calls,
                })
                for tc in tool_calls:
                    fn = tc["function"]["name"]
                    raw_args = tc["function"]["arguments"]
                    args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                    if isinstance(args, dict):
                        args = {k: v for k, v in args.items() if v is not None}

                    rt.log_event("TOOL", f"[Local {local_model}] Calling {fn}({list(args.keys())})")
                    try:
                        print(f"  -> [ReAct Step {step_count} ({local_model})] Tool Call: '{fn}' with args {args}")
                    except Exception:
                        pass
                    if step_callback:
                        step_callback(f"Executing: {fn}({list(args.values())[:2]})")

                    obs = tool_dispatcher(fn, args)
                    executed_observations.append(obs)

                    if fn == "answer_question":
                        return str(obs).strip(), provider
                    if is_interrupt_requested():
                        return "Stopped.", "Interrupted"

                    obs_text = str(obs)
                    if len(obs_text) > 1200:
                        obs_text = obs_text[:1200] + "\n...[output truncated for brevity]"

                    if step_callback:
                        step_callback(f"Result: {obs_text[:65]}...")

                    local_messages.append({
                        "role": "tool",
                        "content": obs_text,
                    })
            else:
                final_text = re.sub(r"<think>.*?</think>", "", (msg.get("content") or ""), flags=re.DOTALL).strip()
                if not final_text and executed_observations:
                    last_obs = str(executed_observations[-1])
                    final_text = last_obs if len(last_obs) < 280 else "I completed the requested action on your desktop."
                return final_text, provider

        if executed_observations:
            return "I completed the requested operations on your desktop.", provider
        return "I completed the requested operations.", provider


def get_react_agent() -> ReActAgent:
    return ReActAgent.get_instance()
