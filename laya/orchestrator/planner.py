"""
Laya Autonomous Multi-Turn Agentic Planner
Dual-Engine Intelligence:
1. Primary: Cloud Ultra-Fast Groq (openai/gpt-oss-20b) (~1.0s latency)
2. Secondary / Offline: Local Private Ollama (mistral:7b) via http://localhost:11434/v1
Decomposes ANY complex or multi-step natural language instruction into executable tool actions.
"""

import os
import json
import re
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple

from laya.config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    GROQ_TIMEOUT_SEC,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_TIMEOUT_SEC,
)
from laya.orchestrator.memory import get_memory_store


def build_system_prompt() -> str:
    memory_summary = get_memory_store().get_all_summary()
    return f"""You are the master brain of Laya, an autonomous Windows PC desktop assistant.
You possess COMPLETE control over the operating system, applications, files, and hardware.
You convert ANY user utterance into an ordered list of executable tool actions.
You maintain multi-turn conversational context and resolve pronouns ('it', 'that file', 'him', 'in this folder') based on conversation history.

Current System Memory:
{memory_summary}

Available Tools:
- create_folder(folder_name: str, location: str = ""): Create a directory. Location can be 'desktop', 'documents', 'downloads', a specific folder name, or empty for current folder.
- create_file(filename: str, content: str = "", location: str = ""): Create ANY file (.py, .txt, .html, .json, etc.) with custom content in current folder or at location ('desktop', 'desktop/<folder>', etc.).
- get_file_info(query: str = ""): Get the exact full path, size, and location of the last created or referenced file/folder.
- open_app(name: str): Launch any application, game, or utility (e.g., 'chrome', 'spotify', 'notepad', 'word', 'whatsapp', 'calc', steam games).
- close_app(name: str): Close application or window.
- set_brightness(level: int): Set display luminosity/brightness from 0 to 100%.
- set_volume(level: int): Set audio volume from 0 to 100% (use 100 for maximum).
- volume_up(steps: int = 5): Increase audio volume.
- volume_down(steps: int = 5): Decrease audio volume.
- mute(): Mute/unmute audio.
- play_media(): Toggle media play/pause.
- next_track() / prev_track(): Skip tracks.
- youtube_search(query: str): Search and open YouTube.
- web_search(query: str): Search Google or web.
- open_url(url: str): Open specific URL in browser.
- send_whatsapp(contact: str, message: str): Open WhatsApp and send message.
- send_email(recipient: str, subject: str = "", body: str = ""): Draft and open email.
- add_memory(fact: str): Store a fact or preference in durable memory when user says 'remember X'.
- query_memory(query: str): Retrieve stored facts or memories when user asks 'what did I ask you to remember?'.
- create_word_document(topic: str, content: str = ""): Create rich styled Word document (.docx).
- create_excel_sheet(topic: str): Create styled Excel spreadsheet (.xlsx).
- create_note(content: str): Open Notepad and write note content (.txt).
- take_screenshot(): Capture screen.
- lock_workstation(delay_sec: int = 0): Lock computer screen (optionally after delay_sec seconds).

- check_system(metric: str): Check 'battery', 'ram', 'cpu', or 'ip'.
- run_powershell(command: str): Run arbitrary PowerShell commands for system tasks.
- answer_question(text: str): Speak back direct answers to questions, date/time, jokes, or conversational responses.

CRITICAL RULES FOR MULTI-STEP TASKS:
1. When asked to perform MULTIPLE steps (e.g. "create folder X on desktop, and create a python file inside it, and open it in notepad"):
   Output ALL steps in chronological order in the "actions" array!
2. When creating a file inside a new folder, specify the location as the created folder or 'desktop/<folder_name>'.
3. When asked where a file or folder is located, use get_file_info.
4. When told 'remember X', call add_memory(fact='X').
5. When asked 'what did I ask you to remember?', call query_memory(query='all').
6. ALWAYS output a valid JSON object:
{{
  "actions": [
    {{"tool": "tool_name", "args": {{"param": "val"}}}}
  ],
  "spoken_summary": "Concise natural sentence explaining what was executed to speak to the user."
}}
"""


class AgentPlanner:
    _instance: Optional["AgentPlanner"] = None

    def __init__(self):
        self.groq_client = None
        if GROQ_API_KEY:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=GROQ_API_KEY)
            except Exception as e:
                print(f"[Planner] Groq SDK initialization note: {e}")

    @classmethod
    def get_instance(cls) -> "AgentPlanner":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def plan(self, utterance: str, history: Optional[List[Dict[str, str]]] = None) -> Tuple[Optional[Dict[str, Any]], str]:
        """
        Decompose instruction into structured multi-step actions.
        Cascades: Groq (cloud ultra-fast) -> Ollama (local offline) -> None.
        Returns: (plan_dict, provider_name)
        """
        messages = [{"role": "system", "content": build_system_prompt()}]

        if history:
            for msg in history[-6:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ["user", "assistant"] and content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": utterance})

        # 1. Try Primary: Groq Cloud LLM (Ultra-Fast)
        if self.groq_client:
            try:
                resp = self.groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    timeout=GROQ_TIMEOUT_SEC,
                )
                raw = resp.choices[0].message.content
                plan_data = self._clean_and_parse_json(raw)
                if plan_data and "actions" in plan_data and isinstance(plan_data["actions"], list):
                    return plan_data, f"Groq ({GROQ_MODEL})"
            except Exception as e:
                # Check if Groq returned failed_generation containing the tool arguments
                e_str = str(e)
                if "failed_generation" in e_str:
                    try:
                        fg_match = re.search(r"['\"]failed_generation['\"]\s*:\s*['\"](\{.*?\})['\"]", e_str)
                        if fg_match:
                            raw_fg = fg_match.group(1).replace('\\"', '"')
                            fg_data = json.loads(raw_fg)
                            if "name" in fg_data and "arguments" in fg_data:
                                return {
                                    "actions": [{"tool": fg_data["name"], "args": fg_data["arguments"]}],
                                    "spoken_summary": f"Executed action for {fg_data['name']}."
                                }, f"Groq ({GROQ_MODEL})"
                    except Exception:
                        pass

                # If json_object mode fails on conversational utterance, retry without forced json mode
                try:
                    resp = self.groq_client.chat.completions.create(
                        model=GROQ_MODEL,
                        messages=messages,
                        temperature=0.2,
                        timeout=5.0,
                    )
                    raw_text = resp.choices[0].message.content.strip()
                    plan_data = self._clean_and_parse_json(raw_text)
                    if plan_data and "actions" in plan_data:
                        return plan_data, f"Groq ({GROQ_MODEL})"
                    return {
                        "actions": [{"tool": "answer_question", "args": {"text": raw_text}}],
                        "spoken_summary": raw_text,
                    }, f"Groq ({GROQ_MODEL})"
                except Exception as ex_groq:
                    print(f"[Planner] Groq cloud inference unavailable ({ex_groq}), switching to local Ollama...")


        # 2. Try Secondary: Local Private Ollama (Local Offline Fallback)
        ollama_plan = self._call_ollama(messages)
        if ollama_plan:
            return ollama_plan, f"Local Ollama ({OLLAMA_MODEL})"

        return None, "Offline Rule Engine"

    def _call_ollama(self, messages: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """Call local Ollama server at http://localhost:11434/v1."""
        try:
            payload = {
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "temperature": 0.1,
            }
            req = urllib.request.Request(
                f"{OLLAMA_BASE_URL}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT_SEC) as response:
                res = json.loads(response.read().decode("utf-8"))
                raw = res["choices"][0]["message"]["content"]
                plan_data = self._clean_and_parse_json(raw)
                if plan_data and "actions" in plan_data:
                    return plan_data
                return {
                    "actions": [{"tool": "answer_question", "args": {"text": raw.strip()}}],
                    "spoken_summary": raw.strip(),
                }
        except Exception as e:
            print(f"[Planner] Local Ollama unavailable: {e}")
            return None

    def _clean_and_parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract and parse JSON safely from LLM output."""
        if not text:
            return None
        text = text.strip()
        # Direct parse
        try:
            return json.loads(text)
        except Exception:
            pass

        # Strip markdown ```json ... ``` blocks
        block_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
        if block_match:
            try:
                return json.loads(block_match.group(1))
            except Exception:
                pass

        # Regex scan for outermost { ... }
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass

        return None


def get_agent_planner() -> AgentPlanner:
    return AgentPlanner.get_instance()
