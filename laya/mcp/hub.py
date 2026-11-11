"""
Laya Model Context Protocol (MCP) Hub
Centralized, hot-reloadable MCP Client Manager.
Connects to 12 production-ready MCP servers over persistent stdio streams,
dynamically resolves query-relevant OpenAI tool schemas across 340+ tools,
supports live credential updates + per-server hot reloads at runtime,
and executes calls over JSON-RPC 2.0.
"""

import os
import re
import asyncio
import threading
import time
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple, Set
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from laya.mcp.config import DEFAULT_MCP_SERVERS, build_runtime_server_env


class MCPHub:
    _instance: Optional["MCPHub"] = None
    _lock = threading.Lock()

    def __init__(self, server_configs: Optional[Dict[str, Dict[str, Any]]] = None):
        self._server_configs = server_configs or DEFAULT_MCP_SERVERS
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True, name="LayaMCPHubLoop")
        self._thread.start()

        self._sessions: Dict[str, ClientSession] = {}
        self._tools_map: Dict[str, str] = {}  # normalized_tool_name -> server_name
        self._canonical_name_map: Dict[str, str] = {}  # normalized_tool_name -> exact_tool_name
        self._server_tools: Dict[str, List[Dict[str, Any]]] = {}  # server_name -> list of schema dicts
        self._tools_schema: List[Dict[str, Any]] = []
        self._ready_events: Dict[str, asyncio.Event] = {}
        self._stop_events: Dict[str, asyncio.Event] = {}
        self._sticky_tools: Set[str] = set()  # unlocked dynamically via search_tools
        self._data_lock = threading.RLock()
        self._running = True
        self._initialized = False

        # Start bootstrap
        self._init_thread = threading.Thread(target=self._bootstrap_all_servers, daemon=True, name="LayaMCPBootstrap")
        self._init_thread.start()

    @classmethod
    def get_instance(cls) -> "MCPHub":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _log(self, category: str, msg: str, level: str = "INFO"):
        try:
            from laya.runtime_manager import get_runtime_manager
            get_runtime_manager().log_event(category, msg, level=level)
        except Exception:
            pass

    def _run_event_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _bootstrap_all_servers(self):
        """Connect to all enabled servers concurrently and aggregate tools."""
        print("[MCPHub] Bootstrapping 12 production MCP servers...")
        self._log("MCP", "Bootstrapping production MCP servers...")
        t0 = time.perf_counter()
        threads = []

        for name, cfg in self._server_configs.items():
            if not cfg.get("enabled", True):
                continue
            t = threading.Thread(target=self._start_single_server_sync, args=(name, cfg), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=45.0)

        dt = (time.perf_counter() - t0) * 1000
        self._initialized = True
        total = len(self._tools_schema)
        print(f"[MCPHub] All MCP servers initialized in {dt:.0f}ms. Total tools aggregated: {total}")
        self._log("MCP", f"All MCP servers initialized in {dt:.0f}ms. Total tools: {total}")

    def _sanitize_schema(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: self._sanitize_schema(v) for k, v in obj.items() if k not in ("$schema", "additionalProperties", "exclusiveMinimum", "exclusiveMaximum")}
        if isinstance(obj, list):
            return [self._sanitize_schema(x) for x in obj]
        return obj

    def _rebuild_flat_schemas(self):
        with self._data_lock:
            flat: List[Dict[str, Any]] = []
            for srv_tools in self._server_tools.values():
                flat.extend(srv_tools)
            self._tools_schema = flat

    def _start_single_server_sync(self, name: str, cfg: Dict[str, Any]):
        cmd = cfg["command"]
        args = cfg.get("args", [])
        env = build_runtime_server_env(name, cfg.get("env", {}))

        params = StdioServerParameters(command=cmd, args=args, env=env)

        async def _init_events():
            ev_ready = asyncio.Event()
            ev_stop = asyncio.Event()
            self._ready_events[name] = ev_ready
            self._stop_events[name] = ev_stop
            return ev_ready, ev_stop

        fut_ev = asyncio.run_coroutine_threadsafe(_init_events(), self._loop)
        ready_ev, stop_ev = fut_ev.result(timeout=5.0)

        asyncio.run_coroutine_threadsafe(self._run_server_worker(name, params, ready_ev, stop_ev), self._loop)

        async def _wait_ready():
            await ready_ev.wait()

        fut = asyncio.run_coroutine_threadsafe(_wait_ready(), self._loop)
        try:
            fut.result(timeout=40.0)
        except Exception as ex:
            print(f"[MCPHub] Timeout or error initializing MCP server '{name}': {ex}")
            self._log("MCP", f"Timeout/error initializing server '{name}': {ex}", level="WARN")

    async def _run_server_worker(
        self,
        name: str,
        params: StdioServerParameters,
        ready_ev: asyncio.Event,
        stop_ev: asyncio.Event,
    ):
        try:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    self._sessions[name] = session

                    tools_res = await session.list_tools()
                    srv_schemas: List[Dict[str, Any]] = []
                    with self._data_lock:
                        # Remove old mappings belonging to this server
                        stale = [k for k, srv in self._tools_map.items() if srv == name]
                        for k in stale:
                            self._tools_map.pop(k, None)
                            self._canonical_name_map.pop(k, None)

                        for t in tools_res.tools:
                            tool_name = t.name
                            norm_name = tool_name.lower()

                            self._tools_map[norm_name] = name
                            self._canonical_name_map[norm_name] = tool_name

                            schema = getattr(t, "input_schema", getattr(t, "inputSchema", {}))
                            if hasattr(schema, "model_dump"):
                                schema = schema.model_dump()
                            elif not isinstance(schema, dict):
                                schema = {"type": "object", "properties": {}}
                            schema = self._sanitize_schema(schema)

                            desc = (t.description or "").strip()
                            if len(desc) > 220:
                                desc = desc[:217] + "..."
                            tagged_desc = f"[{name.upper()}] {desc}" if not desc.startswith("[") else desc

                            srv_schemas.append({
                                "type": "function",
                                "function": {
                                    "name": tool_name,
                                    "description": tagged_desc,
                                    "parameters": schema,
                                }
                            })

                        self._server_tools[name] = srv_schemas
                        self._rebuild_flat_schemas()

                    print(f"[MCPHub] [{name}] Ready with {len(tools_res.tools)} tools.")
                    self._log("MCP", f"[{name}] Ready with {len(tools_res.tools)} tools.")
                    ready_ev.set()

                    while self._running and not stop_ev.is_set():
                        await asyncio.sleep(0.2)

        except Exception as e:
            print(f"[MCPHub] [{name}] Server worker encountered issue: {e}")
            self._log("MCP", f"[{name}] Worker issue: {e}", level="WARN")
            ready_ev.set()
        finally:
            self._sessions.pop(name, None)

    def reload_server(self, name: str) -> str:
        """Hot-reload a specific MCP server at runtime (e.g. after updating Gmail/Telegram/Discord/Instagram keys)."""
        if name not in self._server_configs:
            return f"Unknown MCP server '{name}'."

        cfg = self._server_configs[name]
        if not cfg.get("enabled", True):
            return f"MCP server '{name}' is disabled."

        # Signal existing worker to stop cleanly
        old_stop = self._stop_events.get(name)
        if old_stop:
            try:
                self._loop.call_soon_threadsafe(old_stop.set)
            except Exception:
                pass
            time.sleep(0.4)

        self._log("MCP", f"Hot-reloading MCP server '{name}' with updated runtime environment...")
        self._start_single_server_sync(name, cfg)
        count = len(self._server_tools.get(name, []))
        return f"Reloaded MCP server '{name}' cleanly ({count} tools active)."

    def get_connected_servers_summary(self) -> Dict[str, int]:
        with self._data_lock:
            return {name: len(tools) for name, tools in self._server_tools.items()}

    def wait_until_ready(self, timeout: float = 25.0) -> bool:
        t_start = time.time()
        while not self._initialized and (time.time() - t_start) < timeout:
            time.sleep(0.05)
        return self._initialized

    def get_openai_tools_schema(self) -> List[Dict[str, Any]]:
        if not self._initialized:
            self.wait_until_ready(timeout=8.0)
        return list(self._tools_schema)

    def reset_sticky_tools(self):
        with self._data_lock:
            self._sticky_tools.clear()

    def activate_tools(self, tool_names: List[str]):
        with self._data_lock:
            for n in tool_names:
                self._sticky_tools.add(n.strip().lower())

    def _runtime_meta_schemas(self) -> List[Dict[str, Any]]:
        """Meta-tools for dynamic discovery and live runtime model/credential/log control."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_tools",
                    "description": "Search the full 340+ MCP tool catalog across all 12 servers (email, telegram, discord, instagram, powerpoint, word, excel, windows, browser) by keyword.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Keyword (e.g. 'telegram', 'email', 'powerpoint', 'word', 'excel', 'discord', 'instagram', 'drag')"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "runtime_switch_model",
                    "description": "Switch the active LLM engine at runtime between 'auto', 'local_mistral' (Ollama mistral:7b), or 'external_api'.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "mode": {"type": "string", "description": "One of: 'local_mistral', 'external_api', 'auto'"},
                            "local_model": {"type": "string", "description": "Optional local Ollama model (e.g. 'mistral:7b', 'deepseek-r1:8b')"}
                        },
                        "required": ["mode"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "runtime_set_external_api",
                    "description": "Configure an external LLM API key, endpoint URL, and model at runtime.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "api_key": {"type": "string"},
                            "base_url": {"type": "string", "description": "OpenAI-compatible base URL"},
                            "model": {"type": "string"}
                        },
                        "required": ["api_key"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "runtime_set_platform_credentials",
                    "description": "Update credentials at runtime for gmail, telegram, discord, or instagram and reload that platform's MCP server.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "platform": {"type": "string", "description": "'gmail', 'telegram', 'discord', or 'instagram'"},
                            "credentials": {"type": "object", "description": "Key-value pairs such as user/password, api_id/api_hash, token, access_token/account_id"}
                        },
                        "required": ["platform", "credentials"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "runtime_get_logs",
                    "description": "Retrieve recent Laya runtime, authentication, LLM, and MCP logs.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "description": "Max log lines to return (default 30)"}
                        }
                    }
                }
            },
        ]

    def get_core_tools_schema(self, query: str = "", compact_local: bool = False) -> List[Dict[str, Any]]:
        """
        Return lean universal core tools PLUS domain-specific MCP tools matching `query`
        and any tools unlocked via `search_tools`, staying safely inside token limits for Groq and local Mistral 7B.
        """
        if not self._initialized:
            self.wait_until_ready(timeout=8.0)

        q = (query or "").lower()

        if compact_local:
            # Ultra-compact schema set (~7-10 tools) optimized for 7B/8B local models
            universal_core = {
                "powershell", "app", "browser_navigate",
                "read_file", "write_file", "create_entities", "fetch"
            }
        else:
            universal_core = {
                # Windows OS
                "powershell", "app", "snapshot", "click", "type", "shortcut", "process",
                # Browser
                "browser_navigate", "browser_click", "browser_type", "browser_snapshot",
                # Filesystem
                "create_directory", "write_file", "read_file", "list_directory",
                # Memory & Fetch
                "create_entities", "read_graph", "fetch",
            }

        domain_servers: List[str] = []
        if any(w in q for w in ["email", "mail", "gmail", "inbox", "outlook", "imap", "smtp", "unread"]):
            domain_servers.append("email")
        if any(w in q for w in ["telegram", "tg"]):
            domain_servers.append("telegram")
        if any(w in q for w in ["discord", "guild", "channel", "server", "dm"]):
            domain_servers.append("discord")
        if any(w in q for w in ["instagram", "insta", "ig", "reel", "post", "story"]):
            domain_servers.append("instagram")
        if any(w in q for w in ["powerpoint", "pptx", "slide", "presentation", "deck"]):
            domain_servers.append("powerpoint")
        if any(w in q for w in ["word", "docx", "document", "report", "essay", "letter"]):
            domain_servers.append("word")
        if any(w in q for w in ["excel", "xlsx", "spreadsheet", "workbook", "sheet", "budget"]):
            domain_servers.append("excel")

        # Domain priority filters so oversized servers (like 69 Telegram tools) inject the most important ~10 tools first
        domain_priority_keywords = {
            "email": ["list_available_accounts", "list_emails_metadata", "get_emails_content", "send_email", "forward_email", "save_draft", "set_email_flags", "delete_emails"],
            "telegram": ["telegram_status", "telegram_me", "telegram_login", "telegram_setup", "send", "message", "chat", "dialog", "contact", "search"],
            "discord": ["list_guilds", "list_channels", "find_channel", "read_messages", "send_message", "reply_message", "send_dm"],
            "instagram": ["get_profile_info", "get_media_posts", "publish_media", "get_media_insights", "comment", "message"],
            "powerpoint": ["create_presentation", "add_slide", "populate_placeholder", "add_bullet", "save_presentation", "open_presentation", "manage_text"],
            "word": ["create_document", "add_heading", "add_paragraph", "get_document_text", "add_table", "list_available_documents"],
            "excel": ["create_workbook", "create_sheet", "describe_workbook", "read", "write", "cell", "export_csv"],
        }

        selected: List[Dict[str, Any]] = []
        seen_names: Set[str] = set()

        with self._data_lock:
            # 1. Include Universal Core + Sticky Discovered Tools
            for s in self._tools_schema:
                name = s["function"]["name"]
                low = name.lower()
                if (low in universal_core or low in self._sticky_tools) and low not in seen_names:
                    selected.append(s)
                    seen_names.add(low)

            # 2. Inject Domain-Relevant MCP Server Tools (capped to ~10 per domain to preserve token budget)
            for srv in domain_servers:
                srv_tools = self._server_tools.get(srv, [])
                prio = domain_priority_keywords.get(srv, [])
                added_for_srv = 0

                # First pass: prioritized essential tools
                for s in srv_tools:
                    if added_for_srv >= 10:
                        break
                    name = s["function"]["name"]
                    low = name.lower()
                    if low in seen_names:
                        continue
                    if not prio or any(pk in low for pk in prio):
                        selected.append(s)
                        seen_names.add(low)
                        added_for_srv += 1

                # Second pass: fill up to 8 if still sparse
                if added_for_srv < 6:
                    for s in srv_tools:
                        if added_for_srv >= 8:
                            break
                        name = s["function"]["name"]
                        low = name.lower()
                        if low not in seen_names:
                            selected.append(s)
                            seen_names.add(low)
                            added_for_srv += 1

        # 3. Expose runtime + discovery meta-tools (for local models, expose search_tools + runtime_switch_model)
        for meta in self._runtime_meta_schemas():
            mlow = meta["function"]["name"].lower()
            if compact_local and mlow not in ("search_tools", "runtime_switch_model"):
                continue
            if mlow not in seen_names:
                selected.append(meta)
                seen_names.add(mlow)

        return selected

    def search_tools(self, query: str) -> str:
        """Search all connected MCP servers and unlock matching tools for the next ReAct step."""
        q_tokens = [w.strip().lower() for w in query.split() if len(w.strip()) >= 2]
        matches = []
        unlocked = []

        with self._data_lock:
            for s in self._tools_schema:
                fn = s["function"]
                name = fn["name"]
                desc = fn["description"]
                haystack = f"{name} {desc}".lower()
                if any(tok in haystack for tok in q_tokens) or (query.lower() in haystack):
                    matches.append(f"- {name}: {desc[:120]}")
                    unlocked.append(name)
                if len(matches) >= 12:
                    break

        if unlocked:
            self.activate_tools(unlocked)
            return f"Found & unlocked {len(unlocked)} MCP tools for immediate use:\n" + "\n".join(matches)
        return f"No exact tool match for '{query}'. Try general tools like PowerShell, browser_navigate, email, telegram, discord, powerpoint, word, or excel."

    def has_tool(self, tool_name: str) -> bool:
        norm = tool_name.strip().lower()
        if norm in {"search_tools", "runtime_switch_model", "runtime_set_external_api", "runtime_set_platform_credentials", "runtime_get_logs"}:
            return True
        if norm in self._tools_map:
            return True
        return norm in [
            "open_app", "close_app", "launch_app", "run_powershell", "execute_command", "shell", "powershell",
            "take_screenshot", "screenshot", "mouse_click", "keyboard_type",
            "keyboard_hotkey", "create_folder", "create_file", "read_file",
            "list_directory", "scrape_url", "web_scrape", "kill_process",
            "list_processes", "send_notification",
        ]

    def _normalize_call(self, tool_name: str, arguments: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Map common aliases transparently to canonical live MCP tools."""
        norm = tool_name.strip().lower()
        args = dict(arguments or {})

        if norm in self._canonical_name_map:
            return self._canonical_name_map[norm], args

        if norm in ["open_app", "launch_app"]:
            name = args.get("name") or args.get("app_name") or args.get("app", "")
            return "App", {"mode": "launch", "name": name}

        elif norm == "close_app":
            name = args.get("name") or args.get("app_name") or args.get("app", "")
            return "App", {"mode": "close", "name": name}

        elif norm in ["run_powershell", "execute_command", "shell", "powershell"]:
            cmd = args.get("command") or args.get("cmd") or args.get("script", "")
            return "PowerShell", {"command": cmd}

        elif norm in ["take_screenshot", "screenshot"]:
            return "Screenshot", {}

        elif norm in ["mouse_click", "click"]:
            x, y = args.get("x"), args.get("y")
            loc = [x, y] if (x is not None and y is not None) else args.get("loc")
            payload = {}
            if loc:
                payload["loc"] = loc
            if args.get("button"):
                payload["button"] = args.get("button")
            return "Click", payload

        elif norm in ["keyboard_type", "type"]:
            payload = {"text": args.get("text", "")}
            if args.get("loc"):
                payload["loc"] = args.get("loc")
            return "Type", payload

        elif norm in ["keyboard_hotkey", "shortcut"]:
            keys = args.get("keys") or args.get("shortcut", "")
            if isinstance(keys, list):
                keys = "+".join(keys)
            return "Shortcut", {"keys": str(keys)}

        elif norm in ["create_folder", "mkdir"]:
            folder = args.get("folder_name") or args.get("name") or args.get("path", "NewFolder")
            loc = args.get("location", "")
            target_path = str(Path(loc) / folder) if loc else folder
            return "create_directory", {"path": target_path}

        elif norm in ["create_file", "write_to_file"]:
            filename = args.get("filename") or args.get("path", "file.txt")
            content = args.get("content") or args.get("text", "")
            loc = args.get("location", "")
            target_path = str(Path(loc) / filename) if loc else filename
            return "write_file", {"path": target_path, "content": content}

        elif norm in ["scrape_url", "web_scrape", "scrape"]:
            return "Scrape", {"url": args.get("url", "")}

        elif norm in ["list_processes", "process_list"]:
            return "Process", {"mode": "list"}

        elif norm == "kill_process":
            target = args.get("name_or_pid") or args.get("name") or args.get("pid", "")
            return "Process", {"mode": "kill", "name_or_pid": str(target)}

        elif norm in ["send_notification", "notification"]:
            return "Notification", {"title": args.get("title", "Laya"), "message": args.get("message") or args.get("text", "")}

        return tool_name, args

    def _handle_meta_tool(self, norm: str, args: Dict[str, Any]) -> Optional[str]:
        if norm == "search_tools":
            return self.search_tools(args.get("query", ""))

        if norm == "runtime_switch_model":
            from laya.runtime_manager import get_runtime_manager
            rt = get_runtime_manager()
            return rt.set_inference_mode(args.get("mode", "auto"), args.get("local_model"))

        if norm == "runtime_set_external_api":
            from laya.runtime_manager import get_runtime_manager
            rt = get_runtime_manager()
            return rt.set_external_llm(
                api_key=args.get("api_key", ""),
                base_url=args.get("base_url"),
                model=args.get("model"),
                activate=True,
            )

        if norm == "runtime_set_platform_credentials":
            from laya.runtime_manager import get_runtime_manager
            rt = get_runtime_manager()
            platform = (args.get("platform") or "").strip().lower()
            creds = args.get("credentials") or {}
            msg = rt.update_platform_credentials(platform, creds)
            srv_map = {"gmail": "email", "email": "email", "mail": "email", "telegram": "telegram", "tg": "telegram", "discord": "discord", "instagram": "instagram", "insta": "instagram", "ig": "instagram"}
            srv = srv_map.get(platform)
            if srv and srv in self._server_configs:
                reload_res = self.reload_server(srv)
                return f"{msg}\n{reload_res}"
            return msg

        if norm == "runtime_get_logs":
            from laya.runtime_manager import get_runtime_manager
            rt = get_runtime_manager()
            logs = rt.get_recent_logs(limit=int(args.get("limit", 30)))
            return "\n".join(logs) if logs else "No runtime logs recorded yet."

        return None

    async def _execute_async(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        meta_out = self._handle_meta_tool(tool_name.strip().lower(), arguments or {})
        if meta_out is not None:
            return meta_out

        canonical_name, normalized_args = self._normalize_call(tool_name, arguments)
        norm = canonical_name.strip().lower()

        server_name = self._tools_map.get(norm)
        if not server_name or server_name not in self._sessions:
            return f"Error: Tool '{tool_name}' ({canonical_name}) not found on any active MCP server."

        session = self._sessions[server_name]
        self._log("MCP", f"Calling [{server_name}] {canonical_name}({list(normalized_args.keys())})")
        try:
            res = await session.call_tool(canonical_name, normalized_args)
            parts = []
            for c in res.content:
                if hasattr(c, "text"):
                    parts.append(c.text)
                else:
                    parts.append(str(c))
            out = "\n".join(parts)
            return out if out else f"Tool '{canonical_name}' completed successfully."
        except Exception as e:
            self._log("MCP", f"Error on [{server_name}] {canonical_name}: {e}", level="ERROR")
            return f"MCP execution error on '{canonical_name}': {e}"

    def execute_tool_sync(self, tool_name: str, arguments: Dict[str, Any], timeout: float = 60.0) -> str:
        if not self._initialized:
            self.wait_until_ready(timeout=15.0)

        fut = asyncio.run_coroutine_threadsafe(self._execute_async(tool_name, arguments), self._loop)
        try:
            return fut.result(timeout=timeout)
        except Exception as e:
            return f"Error executing MCP tool '{tool_name}': {e}"


def get_mcp_hub() -> MCPHub:
    return MCPHub.get_instance()
