"""
Laya Dynamic Tool Registry
Implements on-demand tool discovery (search_tools) to prevent context bloat.
"""

from typing import Dict, Any, List, Callable, Optional


class ToolRegistry:
    _instance: Optional["ToolRegistry"] = None

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._register_default_tools()

    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, name: str, description: str, tier: int, handler: Callable, parameters: Optional[Dict[str, Any]] = None):
        self._tools[name] = {
            "name": name,
            "description": description,
            "tier": tier,
            "handler": handler,
            "parameters": parameters or {},
        }

    def _register_default_tools(self):
        from laya.tools.tier1_native import get_tier1_tools
        t1 = get_tier1_tools()

        self.register(
            name="create_word_document",
            description="Create a formatted Microsoft Word document (.docx) with executive overview, analysis, and recommendations.",
            tier=1,
            handler=t1.create_word_document,
            parameters={"topic": "string", "content": "optional string"},
        )
        self.register(
            name="create_excel_sheet",
            description="Create a structured Microsoft Excel spreadsheet (.xlsx) with styled headers, currency formatting, and auto-calculated formulas.",
            tier=1,
            handler=t1.create_excel_sheet,
            parameters={"topic": "string"},
        )
        self.register(
            name="create_notepad_note",
            description="Create a text note with timestamp and open it in Notepad.",
            tier=1,
            handler=t1.create_notepad_note,
            parameters={"content": "string"},
        )
        self.register(
            name="send_whatsapp",
            description="Send a WhatsApp message to a contact or active conversation with full Unicode support.",
            tier=1,
            handler=t1.send_whatsapp,
            parameters={"contact": "string", "message": "string"},
        )
        self.register(
            name="send_telegram",
            description="Send a Telegram message to a contact, username, or active conversation with full Unicode support.",
            tier=1,
            handler=t1.send_telegram,
            parameters={"contact": "string", "message": "string"},
        )
        self.register(
            name="send_email",
            description="Draft and open an email in the default mail client.",
            tier=1,
            handler=t1.send_email,
            parameters={"recipient": "string", "subject": "optional string", "body": "string"},
        )
        def _check_emails_handler(limit: int = 5, unread_only: bool = True) -> str:
            from laya.tools.email_reader import get_email_manager
            res = get_email_manager().check_emails(limit=limit, unread_only=unread_only)
            return res.get("summary") or res.get("spoken", "Checked emails.")

        self.register(
            name="check_emails",
            description="Check recent or unread emails and generate an executive report summary.",
            tier=1,
            handler=_check_emails_handler,
            parameters={"limit": "optional int", "unread_only": "optional bool"},
        )
        self.register(
            name="web_search",
            description="Perform a web search in the default web browser.",
            tier=1,
            handler=t1.web_search,
            parameters={"query": "string"},
        )
        self.register(
            name="youtube_search",
            description="Open YouTube and search for video, creator, or topic.",
            tier=1,
            handler=t1.youtube_search,
            parameters={"query": "string"},
        )
        self.register(
            name="open_url",
            description="Open a web URL directly in the default browser.",
            tier=1,
            handler=t1.open_url,
            parameters={"url": "string"},
        )

        from laya.tools.tier2_os_mcp import get_tier2_tools
        t2 = get_tier2_tools()
        self.register(
            name="create_folder",
            description="Create a folder at specified location ('desktop', 'documents', custom path) or current folder.",
            tier=2,
            handler=t2.create_folder,
            parameters={"folder_name": "string", "location": "optional string"},
        )
        self.register(
            name="create_file",
            description="Create any file (.py, .txt, .json, etc.) with custom content at specified location.",
            tier=2,
            handler=t2.create_file,
            parameters={"filename": "string", "content": "optional string", "location": "optional string"},
        )
        self.register(
            name="get_file_info",
            description="Get the full path, size, and location of the last created or referenced file/folder.",
            tier=2,
            handler=t2.get_file_info,
            parameters={"query": "optional string"},
        )

        from laya.tools.window_organizer import get_window_organizer
        wo = get_window_organizer()
        self.register(
            name="organize_windows",
            description="Organize and tile open desktop application windows into a specified geometric layout ('grid', 'split', 'columns', 'golden_ratio', 'cascade', 'focus', 'creative').",
            tier=2,
            handler=wo.organize,
            parameters={"layout": "optional string", "target_apps": "optional list"},
        )

        from laya.tools.computer_use import get_computer_use_tools
        cu = get_computer_use_tools()
        self.register(
            name="draw_shape",
            description="Draw parametric geometric shapes and sketches (circle, heart, spiral, star, square, triangle, smiley, flower) in MS Paint or active canvas.",
            tier=2,
            handler=cu.draw_shape,
            parameters={"shape_type": "string", "radius": "optional integer", "center_x": "optional integer", "center_y": "optional integer"},
        )

        from laya.orchestrator.memory import get_memory_store
        mem = get_memory_store()
        self.register(
            name="set_reminder",
            description="Schedule a timed reminder that alerts the user via TTS and Windows desktop toast notification. Use when user says 'remind me to X in Y minutes/hours'.",
            tier=1,
            handler=mem.add_reminder,
            parameters={"message": "string", "minutes": "optional float", "hours": "optional float", "seconds": "optional float"},
        )
        self.register(
            name="list_reminders",
            description="List all scheduled pending reminders that have not yet fired.",
            tier=1,
            handler=mem.list_reminders,
            parameters={},
        )

        from laya.fast_path.executor import get_fast_path_executor
        fp = get_fast_path_executor()
        self.register(
            name="record_screen",
            description="Start, stop, or toggle screen video recording to Videos/Captures (.mp4 format).",
            tier=1,
            handler=fp.record_screen,
            parameters={"duration": "optional int"},
        )
        self.register(
            name="stop_screen_recording",
            description="Stop any active screen recording and save the video.",
            tier=1,
            handler=fp.stop_screen_recording,
            parameters={},
        )
        self.register(
            name="cancel_reminders",
            description="Cancel or clear pending reminders or timers.",
            tier=1,
            handler=mem.cancel_reminders,
            parameters={"query": "optional string"},
        )
        self.register(
            name="turn_screen_off",
            description="Turn off the physical computer monitor/display instantly.",
            tier=1,
            handler=fp.turn_screen_off,
            parameters={},
        )
        self.register(
            name="turn_screen_on",
            description="Wake up or turn on the computer monitor/display.",
            tier=1,
            handler=fp.turn_screen_on,
            parameters={},
        )
        self.register(
            name="sleep_system",
            description="Put the computer into sleep/suspend state immediately.",
            tier=1,
            handler=fp.sleep_system,
            parameters={},
        )
        self.register(
            name="lock_workstation",
            description="Lock the computer screen or workstation immediately.",
            tier=1,
            handler=fp.lock_workstation,
            parameters={"delay_sec": "optional integer"},
        )
        self.register(
            name="start_screen_recording",
            description="Start recording screen video continuously.",
            tier=1,
            handler=fp.start_screen_recording,
            parameters={"duration": "optional int"},
        )
        self.register(
            name="record_camera_video",
            description="Record or toggle camera video.",
            tier=1,
            handler=fp.record_camera_video,
            parameters={"duration": "optional int"},
        )
        self.register(
            name="start_camera_recording",
            description="Start recording camera video continuously.",
            tier=1,
            handler=fp.start_camera_recording,
            parameters={"duration": "optional int"},
        )
        self.register(
            name="stop_camera_recording",
            description="Stop active camera video recording.",
            tier=1,
            handler=fp.stop_camera_recording,
            parameters={},
        )
        self.register(
            name="stop_all_recordings",
            description="Stop all active screen and camera recordings.",
            tier=1,
            handler=fp.stop_all_recordings,
            parameters={},
        )
        self.register(
            name="save_user_fact",
            description="Save a durable fact about the user.",
            tier=1,
            handler=mem.add_fact,
            parameters={"fact": "string"},
        )
        self.register(
            name="update_user_profile",
            description="Update user profile attribute.",
            tier=1,
            handler=mem.set_profile,
            parameters={"key": "string", "value": "string"},
        )
        self.register(
            name="who_am_i",
            description="Recall user identity and profile from durable memory.",
            tier=1,
            handler=fp.who_am_i,
            parameters={},
        )

    def search_tools(self, query: str) -> List[Dict[str, Any]]:
        """Dynamic tool discovery to avoid over-tooling prompt degradation."""
        q = query.lower()
        results = []
        for name, meta in self._tools.items():
            if q in name or any(word in meta["description"].lower() for word in q.split()):
                results.append({
                    "name": meta["name"],
                    "description": meta["description"],
                    "tier": meta["tier"],
                    "parameters": meta["parameters"],
                })
        return results if results else list(self._tools.values())[:5]

    def execute(self, tool_name: str, **kwargs) -> Any:
        if tool_name not in self._tools:
            raise ValueError(f"Tool '{tool_name}' not found in registry.")
        handler = self._tools[tool_name]["handler"]
        return handler(**kwargs)


def get_tool_registry() -> ToolRegistry:
    return ToolRegistry.get_instance()
