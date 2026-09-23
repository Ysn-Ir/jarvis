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
    GROQ_TIMEOUT_SEC,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT_SEC,
)
from laya.orchestrator.tools_schema import TOOLS_SCHEMA
from laya.orchestrator.memory import get_memory_store


def build_react_system_prompt() -> str:
    memory_summary = get_memory_store().get_all_summary()
    return f"""You are Laya, an autonomous state-of-the-art Windows desktop assistant.
You possess COMPLETE control over the operating system, applications, files, GUI, and hardware.
You operate in an autonomous perception-action loop:
1. When asked to accomplish a task, analyze what tools are needed and call them.
2. Observe the actual outputs returned from the operating system.
3. If an action needs a follow-up (e.g. creating a folder then creating a file inside it, or copying text then pasting it), execute the next action based on the previous output.
4. When all actions are complete, synthesize a concise, friendly spoken response explaining what was done.
5. If the user asks a question (time, battery, system status, general knowledge), answer it clearly.

Active User Memories & Preferences:
{memory_summary}

Operating Rules:
- If a folder is created on Desktop, files placed inside should use location='desktop/<folder_name>'.
- When asked where a file or folder is, call get_file_info.
- When asked about battery, RAM, CPU, or IP, call check_system.
- When asked to launch an app, call open_app.
- For desktop automation, mouse and keyboard tools are available.
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

        while step_count < max_steps:
            step_count += 1
            response = self.groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                tools=TOOLS_SCHEMA,
                tool_choice="auto",
                temperature=0.1,
                timeout=GROQ_TIMEOUT_SEC,
            )

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
