"""
Laya Orchestrator & State-of-the-Art Autonomous Execution Engine
Integrates the Autonomous ReAct Agent Loop, Native Tool Calling,
and Model Context Protocol (MCP) servers for desktop and OS control.
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
from laya.mcp import get_mcp_hub
from laya.tools.registry import get_tool_registry
from laya.fast_path.executor import get_fast_path_executor


class OrchestratorEngine:
    _instance: Optional["OrchestratorEngine"] = None

    def __init__(self):
        self.permission_gate = get_permission_gate()
        self.mcp_hub = get_mcp_hub()
        self.tool_registry = get_tool_registry()
        self.fast_path = get_fast_path_executor()
        self.planner = get_agent_planner()
        self.react_agent = get_react_agent()
        self.memory = get_memory_store()

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
        """Unified dispatch exclusively powered by standard Model Context Protocol (MCP) servers."""
        tool = re.sub(r"^(?:tool\.|functions\.|laya\.)", "", raw_tool_name.strip())
        norm_tool = tool.lower()

        # Conversational answer passthrough
        if norm_tool == "answer_question":
            return args.get("text", "")

        # Permission & Safety Gate check
        has_params = bool(args)
        allowed, reason = self.permission_gate.check(norm_tool, is_confirmed=is_confirmed, has_params=has_params)
        if not allowed:
            return f"[Permission Gate Blocked] {reason}"

        # 1. Primary Execution: Model Context Protocol (MCP) Hub
        if self.mcp_hub.has_tool(tool):
            return self.mcp_hub.execute_tool_sync(tool, args)

        # 2. Local Durable Memory, Reminders & Timers
        if norm_tool in ["set_reminder", "add_reminder", "set_timer", "add_timer"]:
            return self.memory.add_reminder(
                message=args.get("message", "Reminder"),
                minutes=float(args.get("minutes", 0)),
                hours=float(args.get("hours", 0)),
                seconds=float(args.get("seconds", 0))
            )
        elif norm_tool in ["list_reminders", "get_reminders", "list_timers"]:
            return self.memory.list_reminders()
        elif norm_tool in ["cancel_reminders", "cancel_timer", "clear_reminders"]:
            return self.memory.cancel_reminders(query=args.get("query", ""))
        elif norm_tool in ["add_task", "create_task"]:
            return self.memory.add_task(
                title=args.get("title", ""),
                due_date=args.get("due_date", ""),
                priority=int(args.get("priority", 1))
            )
        elif norm_tool in ["list_tasks", "get_tasks"]:
            return self.memory.list_tasks(status=args.get("status", "all"))
        elif norm_tool in ["complete_task", "finish_task"]:
            return self.memory.complete_task(query=args.get("query", ""))
        elif norm_tool in ["delete_task", "remove_task"]:
            return self.memory.delete_task(query=args.get("query", ""))
        elif norm_tool in ["save_user_fact", "remember_fact", "remember"]:
            return self.memory.add_fact(args.get("fact", "") or args.get("text", ""))
        elif norm_tool in ["update_user_profile", "set_profile"]:
            return self.memory.set_profile(args.get("key", ""), args.get("value", ""))
        elif norm_tool in ["who_am_i", "get_user_profile"]:
            return self.fast_path.who_am_i()
        elif norm_tool in ["clear_memory", "reset_memory"]:
            return self.memory.clear_memory()

        # 3. Direct Fast Path Hardware Controls (Volume, Screen, Power)
        handler = getattr(self.fast_path, norm_tool, None)
        if handler and callable(handler):
            try:
                return str(handler(**args))
            except TypeError:
                return str(handler())

        # 4. Fallback execution directly on MCP Hub
        return self.mcp_hub.execute_tool_sync(tool, args)


def get_orchestrator() -> OrchestratorEngine:
    return OrchestratorEngine.get_instance()
