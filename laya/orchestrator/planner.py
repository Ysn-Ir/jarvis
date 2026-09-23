"""
Laya Autonomous Multi-Turn Agentic Planner
Uses Groq Qwen/Qwen3.8-27B to decompose ANY natural language instruction into
a sequence of executable tool actions with full conversational history and durable memory.
"""

import os
import json
import re
from typing import Dict, Any, List, Optional
import dotenv

from laya.orchestrator.memory import get_memory_store

dotenv.load_dotenv()


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
- create_file(filename: str, content: str = "", location: str = ""): Create ANY file (.py, .txt, .html, .json, etc.) with custom content in current folder or at location ('desktop', etc.).
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
- take_screenshot(): Capture screen.
- lock_workstation(): Lock computer screen.
- check_system(metric: str): Check 'battery', 'ram', 'cpu', or 'ip'.
- run_powershell(command: str): Run arbitrary PowerShell commands for system tasks.
- answer_question(text: str): Speak back direct answers to questions, date/time, jokes, or conversational responses.

CRITICAL RULES:
1. When asked to create a folder on Desktop, use create_folder with location='desktop'.
2. When asked to create a file 'in this folder', use create_file with location=''.
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
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = None
        if self.api_key:
            try:
                from groq import Groq
                self.client = Groq(api_key=self.api_key)
            except Exception:
                self.client = None

    @classmethod
    def get_instance(cls) -> "AgentPlanner":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def plan(self, utterance: str, history: Optional[List[Dict[str, str]]] = None) -> Optional[Dict[str, Any]]:
        """Decompose arbitrary instruction into structured action plan with multi-turn context."""
        if not self.client:
            return None

        # Build messages payload with conversation history
        messages = [{"role": "system", "content": build_system_prompt()}]

        if history:
            # Include the last 6 turns for context
            for msg in history[-6:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ["user", "assistant"] and content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": utterance})

        try:
            resp = self.client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1,
                timeout=3.0,
            )
            raw = resp.choices[0].message.content
            plan_data = json.loads(raw)
            if "actions" in plan_data and isinstance(plan_data["actions"], list):
                return plan_data
        except Exception as e:
            # If JSON formatting fails (e.g. conversational prompt), try without forced json_object
            try:
                resp = self.client.chat.completions.create(
                    model="qwen/qwen3.8-27b",
                    messages=messages,
                    temperature=0.2,
                    timeout=2.0,
                )
                raw_text = resp.choices[0].message.content.strip()
                # Try to extract JSON block
                json_match = re.search(r"\{[\s\S]*\}", raw_text)
                if json_match:
                    plan_data = json.loads(json_match.group(0))
                    if "actions" in plan_data:
                        return plan_data
                return {
                    "actions": [{"tool": "answer_question", "args": {"text": raw_text}}],
                    "spoken_summary": raw_text,
                }
            except Exception as ex2:
                print(f"[Planner Warning] LLM planning failed: {ex2}")

        return None


def get_agent_planner() -> AgentPlanner:
    return AgentPlanner.get_instance()
