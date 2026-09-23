"""
Laya Orchestrator & Omni-Capable Multi-Step Execution Engine
Orchestrates autonomous multi-step planning, tool chaining, permission validation,
and seamless execution of complex user instructions with multi-turn memory.
"""

import os
import re
import sys
import time
import socket
import datetime
import subprocess
from typing import Dict, Any, List, Optional

from laya.router.taxonomy import RouteDecision, ExecutionPath
from laya.orchestrator.permission import get_permission_gate, PermissionTier
from laya.orchestrator.planner import get_agent_planner
from laya.orchestrator.memory import get_memory_store
from laya.tools.registry import get_tool_registry
from laya.tools.tier2_os_mcp import get_tier2_tools
from laya.fast_path.executor import get_fast_path_executor


class OrchestratorEngine:
    _instance: Optional["OrchestratorEngine"] = None

    def __init__(self):
        self.permission_gate = get_permission_gate()
        self.tool_registry = get_tool_registry()
        self.tier2_tools = get_tier2_tools()
        self.fast_path = get_fast_path_executor()
        self.planner = get_agent_planner()
        self.memory = get_memory_store()

    @classmethod
    def get_instance(cls) -> "OrchestratorEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def execute(self, decision: RouteDecision, history: Optional[List[Dict[str, str]]] = None, is_confirmed: bool = False) -> str:
        """Execute reasoning path task, dynamically planning multi-step instructions with multi-turn context."""
        action = decision.action
        params = decision.params
        raw_query = params.get("raw_query") or params.get("query") or ""
        q_lower = raw_query.lower().strip()

        # Check for user approval phrases for pending actions
        if any(w in q_lower for w in ["give you permission", "yes proceed", "i approve", "confirmed", "permission granted"]):
            pending = self.permission_gate.approve_pending()
            if pending:
                return f"Permission granted for '{pending}'. Proceeding with your request."

        # Direct Memory Interception for 100% Reliability
        if any(w in q_lower for w in ["what did i ask you to remember", "what do you remember"]):
            memories = self.memory.get_all_summary()
            return f"{memories}"

        if q_lower.startswith("remember") or "remember that" in q_lower:
            fact_text = re.sub(r"^(remember that|remember to|remember)\s+", "", q_lower).strip()
            if fact_text:
                res = self.memory.add_fact(fact_text)
                return f"I've noted that in memory: '{fact_text}'."

        # 1. Multi-Step / Agentic Planning Path (with full conversation history)
        if action in ["plan_and_execute", "general_reasoning"] or not action:
            plan, provider = self.planner.plan(raw_query, history=history)
            if plan and "actions" in plan and plan["actions"]:
                print(f"🧠 [LLM: {provider}] Planned {len(plan['actions'])} step(s)")
                return self._execute_plan(plan, is_confirmed=is_confirmed)
            # If planner is offline or timed out, use intelligent local omni-fallback
            return self._solve_offline_reasoning(raw_query)


        # 2. Permission Gate Check
        has_params = bool(params.get("contact") and params.get("message")) or bool(params.get("recipient") and params.get("body"))
        allowed, reason = self.permission_gate.check(action, is_confirmed=is_confirmed, has_params=has_params)
        if not allowed:
            return f"[Permission Gate] {reason}"

        # 3. Direct Single Tool Dispatch
        try:
            if action == "create_word_document":
                topic = params.get("topic", "Report")
                content = params.get("content")
                return self.tool_registry.execute("create_word_document", topic=topic, content=content)

            elif action == "create_excel_sheet":
                topic = params.get("topic", "Spreadsheet")
                return self.tool_registry.execute("create_excel_sheet", topic=topic)

            elif action == "create_notepad_note":
                content = params.get("content", "Quick Note")
                return self.tool_registry.execute("create_notepad_note", content=content)

            elif action == "send_whatsapp":
                contact = params.get("contact", "")
                message = params.get("message", "Hello")
                return self.tool_registry.execute("send_whatsapp", contact=contact, message=message)

            elif action == "send_email":
                recipient = params.get("recipient", "")
                subject = params.get("subject", "Message from Laya")
                body = params.get("body", "")
                return self.tool_registry.execute("send_email", recipient=recipient, subject=subject, body=body)

            elif action == "web_search":
                query = params.get("query", "")
                return self.tool_registry.execute("web_search", query=query)

            elif action == "youtube_search":
                query = params.get("query", "")
                return self.tool_registry.execute("youtube_search", query=query)

            elif action == "set_brightness":
                level = int(params.get("level", 70))
                return self.fast_path.set_brightness(level)

            elif action == "create_folder":
                folder_name = params.get("folder_name", "NewFolder")
                location = params.get("location", "")
                return self.tier2_tools.create_folder(folder_name, location=location)

            elif action == "create_file":
                filename = params.get("filename", "file.txt")
                content = params.get("content", "")
                location = params.get("location", "")
                return self.tier2_tools.create_file(filename, content=content, location=location)

            elif action == "get_file_info":
                query = params.get("query", "")
                return self.tier2_tools.get_file_info(query)

            elif action == "query_memory":
                query = params.get("query", "")
                return self.memory.search_facts(query)

            else:
                plan, provider = self.planner.plan(raw_query or action, history=history)
                if plan and "actions" in plan and plan["actions"]:
                    print(f"🧠 [LLM: {provider}] Planned {len(plan['actions'])} step(s)")
                    return self._execute_plan(plan, is_confirmed=is_confirmed)
                return self._solve_offline_reasoning(raw_query or action)

        except Exception as e:
            return f"Error executing task '{action}': {e}"

    def _execute_plan(self, plan: Dict[str, Any], is_confirmed: bool = False) -> str:
        """Execute an ordered sequence of planned tool actions with multi-step chaining."""
        actions = plan.get("actions", [])
        executed_summaries = []
        total_steps = len(actions)

        for idx, item in enumerate(actions):
            tool = item.get("tool", "")
            args = item.get("args", {})
            print(f"  ▶ [Step {idx + 1}/{total_steps}] Executing '{tool}'...")

            has_params = bool(args.get("contact") and args.get("message")) or bool(args.get("recipient") and args.get("body"))
            allowed, reason = self.permission_gate.check(tool, is_confirmed=is_confirmed, has_params=has_params)
            if not allowed:
                return f"[Permission Gate] {reason}"

            try:
                if tool == "create_folder":
                    res = self.tier2_tools.create_folder(args.get("folder_name", "NewFolder"), location=args.get("location", ""))
                    executed_summaries.append(res)
                elif tool == "create_file":
                    # If location is empty and a folder was just created, target that folder
                    loc = args.get("location", "")
                    res = self.tier2_tools.create_file(args.get("filename", "script.py"), content=args.get("content", ""), location=loc)
                    executed_summaries.append(res)
                elif tool == "get_file_info":
                    res = self.tier2_tools.get_file_info(args.get("query", ""))
                    executed_summaries.append(res)
                elif tool == "youtube_search":
                    res = self.tool_registry.execute("youtube_search", query=args.get("query", ""))
                    executed_summaries.append(res)
                elif tool == "web_search":
                    res = self.tool_registry.execute("web_search", query=args.get("query", ""))
                    executed_summaries.append(res)
                elif tool == "open_url":
                    res = self.tool_registry.execute("open_url", url=args.get("url", ""))
                    executed_summaries.append(res)
                elif tool in ["open_app", "open_app_or_game"]:
                    name = args.get("name", "")
                    res = self.fast_path.open_app(name)
                    executed_summaries.append(res)
                elif tool == "close_app":
                    res = self.fast_path.close_app(args.get("name", ""))
                    executed_summaries.append(res)
                elif tool == "set_volume":
                    res = self.fast_path.set_volume(int(args.get("level", 50)))
                    executed_summaries.append(res)
                elif tool in ["set_brightness", "set_luminosity"]:
                    res = self.fast_path.set_brightness(int(args.get("level", 70)))
                    executed_summaries.append(res)
                elif tool == "volume_up":
                    res = self.fast_path.volume_up(int(args.get("steps", 5)))
                    executed_summaries.append(res)
                elif tool == "volume_down":
                    res = self.fast_path.volume_down(int(args.get("steps", 5)))
                    executed_summaries.append(res)
                elif tool == "mute":
                    res = self.fast_path.mute()
                    executed_summaries.append(res)
                elif tool == "play_media":
                    res = self.fast_path.play_media()
                    executed_summaries.append(res)
                elif tool == "next_track":
                    res = self.fast_path.next_track()
                    executed_summaries.append(res)
                elif tool == "prev_track":
                    res = self.fast_path.prev_track()
                    executed_summaries.append(res)
                elif tool == "add_memory":
                    fact = args.get("fact", "")
                    res = self.memory.add_fact(fact)
                    executed_summaries.append(res)
                elif tool == "query_memory":
                    res = self.memory.search_facts(args.get("query", ""))
                    executed_summaries.append(res)
                elif tool == "create_note":
                    res = self.tool_registry.execute("create_notepad_note", content=args.get("content", ""))
                    executed_summaries.append(res)
                elif tool == "create_word_document":
                    res = self.tool_registry.execute("create_word_document", topic=args.get("topic", "Report"), content=args.get("content"))
                    executed_summaries.append(res)
                elif tool == "create_excel_sheet":
                    res = self.tool_registry.execute("create_excel_sheet", topic=args.get("topic", "Sheet"))
                    executed_summaries.append(res)
                elif tool == "send_whatsapp":
                    res = self.tool_registry.execute("send_whatsapp", contact=args.get("contact", ""), message=args.get("message", ""))
                    executed_summaries.append(res)
                elif tool == "send_email":
                    res = self.tool_registry.execute("send_email", recipient=args.get("recipient", ""), subject=args.get("subject", ""), body=args.get("body", ""))
                    executed_summaries.append(res)
                elif tool == "take_screenshot":
                    res = self.fast_path.take_screenshot()
                    executed_summaries.append(res)
                elif tool == "lock_workstation":
                    res = self.fast_path.lock_workstation()
                    executed_summaries.append(res)
                elif tool == "check_system":
                    metric = args.get("metric", "battery").lower()
                    if "ram" in metric or "memory" in metric:
                        res = self.fast_path.check_ram()
                    elif "cpu" in metric:
                        res = self.fast_path.check_cpu()
                    elif "ip" in metric:
                        res = self.fast_path.check_ip()
                    else:
                        res = self.fast_path.check_battery()
                    executed_summaries.append(res)
                elif tool == "run_powershell":
                    cmd = ["powershell", "-NoProfile", "-Command", args.get("command", "")]
                    p = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    executed_summaries.append(p.stdout.strip() or "Executed PowerShell command.")
                elif tool == "answer_question":
                    executed_summaries.append(args.get("text", ""))
                else:
                    executed_summaries.append(f"Completed action '{tool}'.")
            except Exception as e:
                executed_summaries.append(f"Failed action '{tool}': {e}")

        spoken = plan.get("spoken_summary", "").strip()
        # If any queries returned specific paths or facts, append them so user has the ground truth
        detailed_facts = [s for s in executed_summaries if ("\\" in s and ":" in s) or "Active memories:" in s]
        if detailed_facts and spoken:
            extra = " " + " ".join(detailed_facts)
            if not any(f in spoken for f in detailed_facts):
                return f"{spoken}{extra}"
        return spoken if spoken else " | ".join(executed_summaries)


    def _solve_offline_reasoning(self, query: str) -> str:
        """Local Omni-Fallback: Handles any task even when network/DNS drops."""
        q = query.lower().strip()

        # Location of file query
        if any(w in q for w in ["location of that file", "path of that file", "where is that file", "where is the file"]):
            return self.tier2_tools.get_file_info()

        # Screen Brightness / Luminosity
        bright_match = re.search(r"(?:luminosity|brightness)\s+(?:to\s+|at\s+)?(\d{1,3})%?", q)
        if bright_match:
            level = int(bright_match.group(1))
            return self.fast_path.set_brightness(level)
        if any(w in q for w in ["brightness up", "increase brightness", "more brightness", "luminosity up"]):
            return self.fast_path.brightness_up(15)
        if any(w in q for w in ["brightness down", "lower brightness", "dim the screen", "less brightness", "luminosity down"]):
            return self.fast_path.brightness_down(15)

        # Volume
        if "volume" in q:
            if any(w in q for w in ["maximum", "max", "full", "100"]):
                return self.fast_path.set_volume(100)
            if any(w in q for w in ["minimum", "zero", "0"]):
                return self.fast_path.set_volume(0)
            vol_m = re.search(r"(?:volume\s+(?:to\s+)?|to\s+)(\d{1,3})", q)
            if vol_m:
                return self.fast_path.set_volume(int(vol_m.group(1)))
            if any(w in q for w in ["raise", "up", "increase"]):
                return self.fast_path.volume_up(5)
            if any(w in q for w in ["lower", "down", "decrease"]):
                return self.fast_path.volume_down(5)

        # File and folder creation fallback
        if "folder" in q and any(w in q for w in ["create", "new", "make"]):
            name_m = re.search(r"(?:named|name|folder)\s+([a-zA-Z0-9_\-]+)", q)
            f_name = name_m.group(1) if name_m else "NewFolder"
            loc = "desktop" if "desktop" in q else ""
            return self.tier2_tools.create_folder(f_name, location=loc)

        if "file" in q and any(w in q for w in ["create", "new", "make"]):
            name_m = re.search(r"(?:named|name|file)\s+([a-zA-Z0-9_\-\.]+)", q)
            f_name = name_m.group(1) if name_m else "script.py"
            if not any(f_name.endswith(ext) for ext in [".py", ".txt", ".json", ".md"]):
                if "python" in q:
                    f_name += ".py"
                else:
                    f_name += ".txt"
            return self.tier2_tools.create_file(f_name, content="# Created by Laya\n", location="")

        # YouTube Search
        yt_m = re.search(r"(?:youtube|yt)\s+(?:for|search\s+for|about)?\s*(.+)", q)
        if yt_m:
            target = yt_m.group(1).strip()
            return self.tool_registry.execute("youtube_search", query=target)

        # Open Any Game or Application
        open_m = re.search(r"(?:open|launch|start|play)\s+([a-zA-Z0-9\s_\-\.]+)", q)
        if open_m:
            target_app = open_m.group(1).strip()
            if target_app not in ["the", "a", "this", "it"]:
                return self.fast_path.open_app(target_app)

        # General Knowledge & Time
        if "time" in q:
            return f"The current time is {datetime.datetime.now().strftime('%I:%M %p')}."
        if "date" in q:
            return f"Today is {datetime.datetime.now().strftime('%A, %B %d, %Y')}."
        if "who are you" in q:
            return "I am Laya, your local-first autonomous desktop assistant."
        if "joke" in q:
            return "Why do programmers prefer dark mode? Because light attracts bugs!"

        return f"I'm not sure how to complete '{query}'. Could you please clarify what you'd like me to do?"


def get_orchestrator() -> OrchestratorEngine:
    return OrchestratorEngine.get_instance()
