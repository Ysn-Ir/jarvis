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
            description="Send a WhatsApp message to a contact with full Unicode and multilingual support.",
            tier=1,
            handler=t1.send_whatsapp,
            parameters={"contact": "string", "message": "string"},
        )
        self.register(
            name="send_email",
            description="Draft and open an email in the default mail client.",
            tier=1,
            handler=t1.send_email,
            parameters={"recipient": "string", "subject": "optional string", "body": "string"},
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
