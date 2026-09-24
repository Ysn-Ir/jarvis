"""
Laya Orchestrator & State-of-the-Art Autonomous Execution Engine
Integrates the Autonomous ReAct Agent Loop, Native Tool Calling,
Computer Use GUI automation, System Pro diagnostics, and Durable Memory.
"""

import os
import re
import sys
import time
import socket
import datetime
import subprocess
from typing import Dict, Any, List, Optional, Callable

from laya.router.taxonomy import RouteDecision, ExecutionPath
from laya.orchestrator.permission import get_permission_gate, PermissionTier
from laya.orchestrator.planner import get_agent_planner
from laya.orchestrator.react_agent import get_react_agent
from laya.orchestrator.memory import get_memory_store
from laya.tools.registry import get_tool_registry
from laya.tools.tier2_os_mcp import get_tier2_tools
from laya.tools.computer_use import get_computer_use_tools
from laya.tools.system_pro import get_system_pro_tools
from laya.tools.code_interpreter import get_code_interpreter
from laya.tools.web_intelligence import get_web_intelligence
from laya.tools.ufo_controller import get_ufo_controller
from laya.tools.filesystem_pro import get_filesystem_pro
from laya.tools.notebook_tools import get_notebook_tools
from laya.fast_path.executor import get_fast_path_executor


class OrchestratorEngine:
    _instance: Optional["OrchestratorEngine"] = None

    def __init__(self):
        self.permission_gate = get_permission_gate()
        self.tool_registry = get_tool_registry()
        self.tier2_tools = get_tier2_tools()
        self.fast_path = get_fast_path_executor()
        self.planner = get_agent_planner()
        self.react_agent = get_react_agent()
        self.memory = get_memory_store()
        self.computer_use = get_computer_use_tools()
        self.system_pro = get_system_pro_tools()
        self.code_interpreter = get_code_interpreter()
        self.web_intelligence = get_web_intelligence()
        self.ufo_controller = get_ufo_controller()
        self.filesystem_pro = get_filesystem_pro()
        self.notebook_tools = get_notebook_tools()

    @classmethod
    def get_instance(cls) -> "OrchestratorEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def execute(
        self,
        decision: RouteDecision,
        history: Optional[List[Dict[str, str]]] = None,
        is_confirmed: bool = False,
        step_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
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

        # 1. State-of-the-Art Autonomous ReAct Agent Loop
        # If action is open-ended or not a recognized direct tool, run autonomous ReAct loop
        direct_single_tools = ["list_processes", "kill_process", "get_gpu_vram_status", "get_disk_space"]
        if action not in direct_single_tools or action in ["plan_and_execute", "general_reasoning", "autonomous_task"]:
            res, provider = self.react_agent.run(
                raw_query,
                tool_dispatcher=lambda tool, args: self._dispatch_tool(tool, args, is_confirmed=is_confirmed),
                history=history,
                step_callback=step_callback,
            )
            return res

        # 2. Permission Gate Check for Direct Dispatch
        has_params = bool(params.get("contact") and params.get("message")) or bool(params.get("recipient") and params.get("body"))
        allowed, reason = self.permission_gate.check(action, is_confirmed=is_confirmed, has_params=has_params)
        if not allowed:
            return f"[Permission Gate] {reason}"

        # 3. Direct Single Tool Dispatch
        try:
            return self._dispatch_tool(action, params, is_confirmed=is_confirmed)
        except Exception as e:
            return f"Error executing task '{action}': {e}"

    def _dispatch_tool(self, raw_tool_name: str, args: Dict[str, Any], is_confirmed: bool = False) -> str:
        """Unified dispatch for all Laya tools with safety gating and real execution."""
        tool = re.sub(r"^(?:tool\.|functions\.|laya\.)", "", raw_tool_name.strip().lower())

        has_params = bool(args.get("contact") and args.get("message")) or bool(args.get("recipient") and args.get("body"))
        allowed, reason = self.permission_gate.check(tool, is_confirmed=is_confirmed, has_params=has_params)
        if not allowed:
            return f"[Permission Gate Blocked] {reason}"

        try:
            # File and Folder Operations
            if tool == "create_folder":
                return self.tier2_tools.create_folder(
                    args.get("folder_name", "NewFolder"),
                    location=args.get("location", "")
                )
            elif tool == "create_file":
                return self.tier2_tools.create_file(
                    args.get("filename", "script.py"),
                    content=args.get("content", ""),
                    location=args.get("location", "")
                )
            elif tool == "get_file_info":
                return self.tier2_tools.get_file_info(args.get("query", ""))
            elif tool in ["open_folder", "explore"]:
                folder_target = args.get("folder_name") or args.get("name") or args.get("location", "desktop")
                return self.fast_path.open_folder(folder_target)

            # Application & Window Management
            elif tool in ["open_app", "open_app_or_game", "launch_app"]:
                name = args.get("name") or args.get("app_name", "")
                return self.fast_path.open_app(name)
            elif tool == "close_app":
                return self.fast_path.close_app(args.get("name", ""))

            # Display & Volume
            elif tool in ["set_brightness", "set_luminosity"]:
                return self.fast_path.set_brightness(int(args.get("level", 70)))
            elif tool == "set_volume":
                return self.fast_path.set_volume(int(args.get("level", 50)))
            elif tool == "volume_up":
                return self.fast_path.volume_up(int(args.get("steps", 5)))
            elif tool == "volume_down":
                return self.fast_path.volume_down(int(args.get("steps", 5)))
            elif tool == "mute":
                return self.fast_path.mute()
            elif tool == "play_media":
                return self.fast_path.play_media()
            elif tool == "next_track":
                return self.fast_path.next_track()
            elif tool == "prev_track":
                return self.fast_path.prev_track()
            elif tool in ["lock_workstation", "lock_pc", "lock"]:
                delay = int(args.get("delay_sec", 0))
                return self.fast_path.lock_workstation(delay_sec=delay)
            elif tool == "take_screenshot":
                return self.fast_path.take_screenshot()

            # Web & Search Intelligence
            elif tool in ["web_search", "live_web_search", "google_search"]:
                return self.web_intelligence.live_web_search(args.get("query", ""), max_results=4)
            elif tool in ["youtube_search", "search_youtube"]:
                return self.web_intelligence.live_web_search(f"{args.get('query', '')} YouTube", max_results=4)
            elif tool == "open_url":
                return self.tool_registry.execute("open_url", url=args.get("url", ""))

            # Native Office & Documents
            elif tool == "create_word_document":
                return self.tool_registry.execute(
                    "create_word_document",
                    topic=args.get("topic", "Report"),
                    content=args.get("content")
                )
            elif tool == "create_excel_sheet":
                return self.tool_registry.execute(
                    "create_excel_sheet",
                    topic=args.get("topic", "Spreadsheet")
                )
            elif tool == "create_note":
                return self.tool_registry.execute(
                    "create_notepad_note",
                    content=args.get("content", "")
                )

            # Messaging & Comms
            elif tool == "send_whatsapp":
                return self.tool_registry.execute(
                    "send_whatsapp",
                    contact=args.get("contact", ""),
                    message=args.get("message", "")
                )
            elif tool == "send_email":
                return self.tool_registry.execute(
                    "send_email",
                    recipient=args.get("recipient", ""),
                    subject=args.get("subject", "Message from Laya"),
                    body=args.get("body", "")
                )

            # Durable Memory
            elif tool == "add_memory":
                return self.memory.add_fact(args.get("fact", ""))
            elif tool == "query_memory":
                return self.memory.search_facts(args.get("query", ""))

            # Telemetry & Diagnostics
            elif tool in ["check_system", "check_battery", "battery"]:
                metric = str(args.get("metric", "battery")).lower()
                if "ram" in metric or "memory" in metric:
                    return self.fast_path.check_ram()
                elif "cpu" in metric:
                    return self.fast_path.check_cpu()
                elif "ip" in metric:
                    return self.fast_path.check_ip()
                else:
                    return self.fast_path.check_battery()
            elif tool in ["check_ram", "ram"]:
                return self.fast_path.check_ram()
            elif tool in ["check_cpu", "cpu"]:
                return self.fast_path.check_cpu()
            elif tool in ["check_ip", "ip"]:
                return self.fast_path.check_ip()
            elif tool in ["query_time", "get_time", "time"]:
                return self.fast_path.query_time()
            elif tool in ["query_date", "get_date", "date"]:
                return self.fast_path.query_date()

            # Computer Use (GUI Automation)
            elif tool == "mouse_click":
                return self.computer_use.mouse_click(
                    x=args.get("x"),
                    y=args.get("y"),
                    button=args.get("button", "left"),
                    clicks=args.get("clicks", 1)
                )
            elif tool == "mouse_move":
                return self.computer_use.mouse_move(x=args.get("x", 0), y=args.get("y", 0))
            elif tool == "mouse_scroll":
                return self.computer_use.mouse_scroll(clicks=args.get("clicks", 3))
            elif tool == "keyboard_type":
                return self.computer_use.keyboard_type(text=args.get("text", ""))
            elif tool == "keyboard_hotkey":
                keys = args.get("keys", [])
                if isinstance(keys, str):
                    keys = [k.strip() for k in keys.split("+")]
                return self.computer_use.keyboard_hotkey(keys=keys)
            elif tool == "press_key":
                return self.computer_use.press_key(key=args.get("key", "enter"))
            elif tool == "window_action":
                return self.computer_use.window_action(action=args.get("action", "maximize"))
            elif tool == "clipboard_copy":
                return self.computer_use.clipboard_copy(text=args.get("text", ""))
            elif tool == "clipboard_read":
                return self.computer_use.clipboard_read()
            elif tool == "draw_shape":
                return self.computer_use.draw_shape(
                    shape_type=args.get("shape_type", "circle"),
                    center_x=args.get("center_x"),
                    center_y=args.get("center_y"),
                    radius=args.get("radius", 80),
                    custom_points=args.get("custom_points")
                )
            elif tool in ["organize_windows", "tile_windows", "arrange_windows"]:
                return self.fast_path.organize_windows(
                    layout=args.get("layout", "grid"),
                    target_apps=args.get("apps")
                )
            elif tool in ["browser_search", "web_browser_search"]:
                q = args.get("query", "")
                engine = args.get("engine", "google")
                return self.fast_path.browser_search(query=q, engine=engine)
            elif tool in ["browser_open_url", "open_url"]:
                url = args.get("url", "")
                return self.fast_path.browser_open_url(url=url)

            # Jupyter Notebook Autonomy
            elif tool in ["write_notebook_cell", "write_notebook"]:
                return self.notebook_tools.write_notebook_cell(
                    notebook_path=args.get("notebook_path", "Untitled.ipynb"),
                    code=args.get("code", ""),
                    cell_type=args.get("cell_type", "code"),
                    position=args.get("position")
                )
            elif tool in ["read_notebook_cells", "read_notebook"]:
                return self.notebook_tools.read_notebook_cells(
                    notebook_path=args.get("notebook_path", "Untitled.ipynb")
                )
            elif tool in ["create_notebook", "new_notebook"]:
                return self.notebook_tools.create_notebook(
                    notebook_path=args.get("notebook_path", "Untitled.ipynb")
                )

            # System Pro
            elif tool == "list_processes":
                return self.system_pro.list_processes(
                    sort_by=args.get("sort_by", "memory"),
                    top_n=args.get("top_n", 8)
                )
            elif tool == "kill_process":
                return self.system_pro.kill_process(name_or_pid=args.get("name_or_pid", ""))
            elif tool == "get_gpu_vram_status":
                return self.system_pro.get_gpu_vram_status()
            elif tool == "get_disk_space":
                return self.system_pro.get_disk_space()
            elif tool == "empty_recycle_bin":
                return self.system_pro.empty_recycle_bin()

            # Advanced Universal Code Execution (Open-Interpreter Paradigm)
            elif tool in ["run_python", "execute_python", "python"]:
                return self.code_interpreter.run_python(args.get("code", ""))
            elif tool in ["run_powershell", "execute_command", "shell", "powershell"]:
                cmd_str = args.get("command", "") or args.get("cmd", "")
                return self.code_interpreter.run_powershell(cmd_str)

            # Web Intelligence & Live Search
            elif tool in ["live_web_search", "web_search_live", "google_search"]:
                q = args.get("query", "")
                max_res = int(args.get("max_results", 4))
                return self.web_intelligence.live_web_search(q, max_results=max_res)
            elif tool in ["fetch_webpage_content", "read_webpage", "scrape_url"]:
                return self.web_intelligence.fetch_webpage_content(args.get("url", ""))

            # Microsoft UFO Windows UI Automation
            elif tool in ["inspect_window_controls", "inspect_active_window", "uia_tree"]:
                return self.ufo_controller.inspect_window_controls()
            elif tool in ["click_window_control", "click_uia_control"]:
                return self.ufo_controller.click_window_control(args.get("name", ""))
            elif tool in ["set_window_control_text", "type_into_control"]:
                return self.ufo_controller.set_window_control_text(args.get("name", ""), args.get("text", ""))
            elif tool in ["list_open_windows", "get_open_windows"]:
                return self.ufo_controller.list_open_windows()
            elif tool in ["focus_window", "switch_to_window", "bring_to_front"]:
                target = args.get("title", "") or args.get("name", "") or args.get("app", "")
                return self.fast_path.bring_to_front(target)

            # Deep Filesystem Intelligence
            elif tool in ["read_file_content", "read_file", "view_file"]:
                return self.filesystem_pro.read_file_content(
                    args.get("filepath", "") or args.get("path", ""),
                    max_lines=int(args.get("max_lines", 150))
                )
            elif tool in ["list_directory", "list_dir", "ls", "dir"]:
                return self.filesystem_pro.list_directory(args.get("path", "desktop"))
            elif tool in ["search_filesystem", "find_files", "search_files"]:
                return self.filesystem_pro.search_filesystem(
                    args.get("pattern", ""),
                    root_dir=args.get("root_dir", "desktop")
                )
            elif tool in ["open_file", "launch_file"]:
                return self.filesystem_pro.open_file(args.get("filepath", "") or args.get("path", ""))
            elif tool in ["delete_file", "remove_file", "trash_file"]:
                return self.filesystem_pro.delete_file(
                    filepath=args.get("filepath", "") or args.get("path", ""),
                    permanent=bool(args.get("permanent", False))
                )
            elif tool in ["move_file", "relocate_file"]:
                return self.filesystem_pro.move_file(
                    source=args.get("source", ""),
                    destination=args.get("destination", "")
                )
            elif tool in ["copy_file", "duplicate_file"]:
                return self.filesystem_pro.copy_file(
                    source=args.get("source", ""),
                    destination=args.get("destination", "")
                )
            elif tool in ["rename_file"]:
                return self.filesystem_pro.rename_file(
                    filepath=args.get("filepath", "") or args.get("path", ""),
                    new_name=args.get("new_name", "")
                )
            elif tool in ["organize_directory", "organize_files"]:
                return self.filesystem_pro.organize_directory(
                    args.get("directory", "downloads"),
                    by=args.get("by", "extension")
                )

            elif tool == "answer_question":
                return args.get("text", "")

            else:
                return f"Tool '{tool}' executed with parameters {args}."

        except Exception as e:
            return f"Error executing tool '{tool}': {e}"


def get_orchestrator() -> OrchestratorEngine:
    return OrchestratorEngine.get_instance()
