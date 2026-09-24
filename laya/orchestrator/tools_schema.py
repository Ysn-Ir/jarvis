"""
Laya OpenAI-Compatible Native Tool Calling Schemas
Standardized JSON schemas for autonomous function calling across Groq and Ollama.
"""

from typing import List, Dict, Any

TOOLS_SCHEMA: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "create_folder",
            "description": "Create a new directory on the Windows file system. Location can be 'desktop', 'documents', 'downloads', a relative path like 'desktop/MyFolder', or empty for the active folder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_name": {"type": "string", "description": "Name of the folder to create"},
                    "location": {"type": "string", "description": "Base directory location (e.g. 'desktop', 'downloads', 'documents')"}
                },
                "required": ["folder_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_file",
            "description": "Create ANY text or script file (.py, .txt, .json, .md, .html, etc.) with custom content in the active directory or at a specified location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Filename with extension (e.g. 'script.py', 'notes.txt')"},
                    "content": {"type": "string", "description": "File body or code contents to write"},
                    "location": {"type": "string", "description": "Optional location path (e.g. 'desktop', 'desktop/MyFolder')"}
                },
                "required": ["filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_file",
            "description": "Open any existing file or document in its default application on Windows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Filename or path to open (e.g. 'notes.txt', 'desktop/data.csv')"}
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Delete a file or folder by sending it safely to the Windows Recycle Bin.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Filename or path of file/folder to delete"},
                    "permanent": {"type": "boolean", "description": "If true, bypasses Recycle Bin and permanently removes the file"}
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_file",
            "description": "Move a file or directory from source path to destination path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Source file or directory path"},
                    "destination": {"type": "string", "description": "Destination file or directory path"}
                },
                "required": ["source", "destination"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "copy_file",
            "description": "Copy a file or directory from source to destination.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "description": "Source file path"},
                    "destination": {"type": "string", "description": "Destination path or directory"}
                },
                "required": ["source", "destination"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "rename_file",
            "description": "Rename a file or folder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Current file path"},
                    "new_name": {"type": "string", "description": "New filename or folder name"}
                },
                "required": ["filepath", "new_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_notebook_cell",
            "description": "Write, append, or insert code or markdown cells into a Jupyter notebook (.ipynb) on the Desktop or in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "notebook_path": {"type": "string", "description": "Notebook filename or path (e.g. 'Untitled.ipynb', 'desktop/analysis.ipynb')"},
                    "code": {"type": "string", "description": "Code or markdown content to write into the cell"},
                    "cell_type": {"type": "string", "enum": ["code", "markdown"], "description": "Cell type, default is 'code'"}
                },
                "required": ["notebook_path", "code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_notebook_cells",
            "description": "Read and inspect all cells and code in a Jupyter notebook (.ipynb).",
            "parameters": {
                "type": "object",
                "properties": {
                    "notebook_path": {"type": "string", "description": "Notebook filename or path (e.g. 'Untitled.ipynb')"}
                },
                "required": ["notebook_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_info",
            "description": "Get the exact full path, size, and metadata of the most recently created or referenced file or folder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional filename or query to inspect"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Launch any installed application, browser, utility, or game, or bring its existing window to the foreground.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Application name (e.g. 'chrome', 'telegram', 'discord', 'vscode', 'notepad', 'spotify')"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "organize_windows",
            "description": "Organize and tile open desktop application windows into a specified clean geometric layout ('grid', 'split', 'columns', 'golden_ratio', 'cascade', 'focus', 'creative').",
            "parameters": {
                "type": "object",
                "properties": {
                    "layout": {
                        "type": "string",
                        "enum": ["grid", "split", "columns", "golden_ratio", "cascade", "focus", "creative"],
                        "description": "Geometric layout pattern to arrange open windows"
                    },
                    "apps": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional specific application names or titles to include in the arrangement"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "draw_shape",
            "description": "Draw parametric geometric figures and sketches (circle, heart, spiral, star, square, triangle, smiley, flower) directly onto the MS Paint canvas or active drawing window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "shape_type": {
                        "type": "string",
                        "enum": ["circle", "heart", "spiral", "star", "square", "triangle", "smiley", "flower"],
                        "description": "Type of geometric shape or sketch to draw"
                    },
                    "radius": {
                        "type": "integer",
                        "description": "Radius or size of the shape in pixels (default: 80)"
                    },
                    "center_x": {
                        "type": "integer",
                        "description": "Optional center X pixel coordinate (auto-detected if omitted)"
                    },
                    "center_y": {
                        "type": "integer",
                        "description": "Optional center Y pixel coordinate (auto-detected if omitted)"
                    }
                },
                "required": ["shape_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "close_app",
            "description": "Close an application by process name or active window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Process name or window title to close"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_folder",
            "description": "Open a folder in Windows File Explorer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder_name": {"type": "string", "description": "Folder alias ('desktop', 'downloads', 'documents') or directory path"}
                },
                "required": ["folder_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_brightness",
            "description": "Set display brightness / luminosity level (0 to 100).",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {"type": "integer", "description": "Brightness percentage from 0 to 100"}
                },
                "required": ["level"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_volume",
            "description": "Set audio master volume level (0 to 100).",
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {"type": "integer", "description": "Volume percentage from 0 to 100"}
                },
                "required": ["level"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lock_workstation",
            "description": "Lock the Windows workstation screen, optionally after a delay in seconds.",
            "parameters": {
                "type": "object",
                "properties": {
                    "delay_sec": {"type": "integer", "description": "Delay in seconds before locking (0 for immediate)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "take_screenshot",
            "description": "Capture a full-screen screenshot and save it to the Screenshots folder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {"type": "string", "description": "Optional custom path or filename"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Execute a real-time web search to look up facts, people, entities, YouTube channels, news, scores, or current world information. Returns verified summaries, snippets, and links so you can speak the answer directly.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query terms"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "youtube_search",
            "description": "Search YouTube for videos, channels, creators, or content and return video titles, channels, and details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Video or creator search query"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Open a specific URL in the default browser.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL starting with http:// or https://"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_word_document",
            "description": "Create a formatted Word document (.docx) on a given topic with styled headings and content, and open it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Document title / subject"},
                    "content": {"type": "string", "description": "Optional body text or essay paragraphs"}
                },
                "required": ["topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_excel_sheet",
            "description": "Create a styled Excel spreadsheet (.xlsx) with tables, headers, and formulas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Spreadsheet topic or budget name"}
                },
                "required": ["topic"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_note",
            "description": "Create a quick text note and open it immediately in Notepad.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Note content to write"}
                },
                "required": ["content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_whatsapp",
            "description": "Open WhatsApp and prepare or send a message to a contact.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact": {"type": "string", "description": "Contact name or phone number"},
                    "message": {"type": "string", "description": "Message text"}
                },
                "required": ["contact", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_memory",
            "description": "Persist an important user fact, preference, or reminder into durable SQLite memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fact": {"type": "string", "description": "The fact or preference to remember"}
                },
                "required": ["fact"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_memory",
            "description": "Search and retrieve stored user facts and preferences from durable memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Keyword or topic to retrieve (use 'all' for complete summary)"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_system",
            "description": "Query live system telemetry: battery percentage, RAM utilization, CPU load, or local IP address.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "enum": ["battery", "ram", "cpu", "ip"], "description": "Metric to inspect"}
                },
                "required": ["metric"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mouse_click",
            "description": "Simulate a physical mouse click at specific screen coordinates (x, y) or at the current cursor position.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "Horizontal screen coordinate"},
                    "y": {"type": "integer", "description": "Vertical screen coordinate"},
                    "button": {"type": "string", "enum": ["left", "right", "middle"], "description": "Mouse button"},
                    "clicks": {"type": "integer", "description": "Number of clicks (1 for single, 2 for double)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mouse_scroll",
            "description": "Scroll the mouse wheel up (positive) or down (negative).",
            "parameters": {
                "type": "object",
                "properties": {
                    "clicks": {"type": "integer", "description": "Amount to scroll (e.g. 5 for up, -5 for down)"}
                },
                "required": ["clicks"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "keyboard_type",
            "description": "Type text into the currently active or focused window as a human user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text string to type"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "keyboard_hotkey",
            "description": "Press a keyboard shortcut / hotkey combination (e.g. ['ctrl', 't'] for new tab, ['ctrl', 'w'] to close tab, ['alt', 'tab'] to switch app, ['win', 'd'] for desktop).",
            "parameters": {
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of key names to press in combination (e.g. ['ctrl', 'c'])"
                    }
                },
                "required": ["keys"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "press_key",
            "description": "Press a single keyboard key (e.g. 'enter', 'esc', 'tab', 'space', 'backspace', 'f5', 'up', 'down', 'left', 'right', 'pageup', 'pagedown').",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Key name to press (e.g. 'enter', 'space', 'esc', 'tab')"}
                },
                "required": ["key"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "window_action",
            "description": "Perform window state manipulation: 'maximize', 'minimize', 'restore', 'snap_left', 'snap_right', 'show_desktop', 'close_tab'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["maximize", "minimize", "restore", "snap_left", "snap_right", "show_desktop", "close_tab"],
                        "description": "Window action to perform"
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clipboard_copy",
            "description": "Copy arbitrary text to the Windows system clipboard.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to put on clipboard"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clipboard_read",
            "description": "Read the current text contents from the Windows system clipboard.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_processes",
            "description": "List running Windows processes sorted by memory or CPU usage to identify performance bottlenecks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sort_by": {"type": "string", "enum": ["memory", "cpu"], "description": "Sort metric"},
                    "top_n": {"type": "integer", "description": "Number of processes to return (default 8)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "kill_process",
            "description": "Terminate a frozen or unwanted application by process name or PID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name_or_pid": {"type": "string", "description": "Process name (e.g. 'chrome.exe', 'notepad') or numeric PID"}
                },
                "required": ["name_or_pid"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_gpu_vram_status",
            "description": "Query the NVIDIA GPU hardware for live VRAM memory usage, GPU core utilization, and temperature.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_disk_space",
            "description": "Check available storage space on system drives (C:, D:).",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_powershell",
            "description": "Execute an arbitrary PowerShell command on Windows for advanced administration.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "PowerShell command line"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Execute arbitrary Python code in the local environment and return stdout/stderr (Open-Interpreter paradigm). Use for calculations, complex data processing, scraping, API queries, file transformations, or solving any open-ended task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Python source code to execute"}
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "live_web_search",
            "description": "Execute a real-time live web search using DuckDuckGo to look up facts, news, documentation, scores, or current world information. Returns actual text summaries and URLs so you can speak the answer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query terms"},
                    "max_results": {"type": "integer", "description": "Number of results to retrieve (default 4)"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_webpage_content",
            "description": "Download and extract clean, readable text from any website or article URL for reading or summarization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full webpage URL (e.g. 'https://en.wikipedia.org/...')"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_window_controls",
            "description": "Inspect the Microsoft UI Automation (UIA) control hierarchy of the active foreground window. Returns all interactive controls (Buttons, Text Inputs, Tabs, Menu items) with their exact UI names.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "click_window_control",
            "description": "Directly click an interactive UI control (button, tab, menu) by name in the active window via Microsoft UI Automation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name or text of the control to click (e.g. 'File', 'Save', 'Search', 'Close')"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_window_control_text",
            "description": "Enter text into an input or edit box control in the active window via Microsoft UI Automation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name or ID of edit box (optional)"},
                    "text": {"type": "string", "description": "Text to set"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_open_windows",
            "description": "List all visible application windows currently open on the desktop with their window titles and HWNDs.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "focus_window",
            "description": "Bring an open application window to the foreground by its window title or application name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Window title or app name to focus"}
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file_content",
            "description": "Read the text contents of a file on the local system (scripts, notes, configs, csv, markdown, logs).",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to file (e.g. 'desktop/script.py' or absolute path)"},
                    "max_lines": {"type": "integer", "description": "Max lines to read (default 150)"}
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and subdirectories with sizes and modification dates in any folder (e.g. 'desktop', 'downloads', 'documents').",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path or alias ('desktop', 'downloads', 'documents')"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_filesystem",
            "description": "Search for files matching a wildcard pattern (e.g. '*.pdf', '*invoice*', '*.py') across a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Search pattern (e.g. '*.docx', '*budget*')"},
                    "root_dir": {"type": "string", "description": "Directory to search from (default 'desktop')"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "organize_directory",
            "description": "Organize unorganized files in a directory into categorized folders (Images, Documents, Installers, Code).",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Directory to organize (e.g. 'downloads', 'desktop')"}
                },
                "required": ["directory"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_window_geometry",
            "description": "Get the exact screen position, dimensions (width, height), and center coordinates of any visible window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title_keyword": {"type": "string", "description": "Window title substring (e.g. 'Chrome', 'Paint', 'Spotify', 'Notepad')"}
                },
                "required": ["title_keyword"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "click_window_relative",
            "description": "Bring target window to front and click at relative percentage coordinates (0.0 to 1.0). For example, (0.5, 0.5) is exact center; (0.36, 0.30) is top YouTube video.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title_keyword": {"type": "string", "description": "Target window title substring"},
                    "rel_x": {"type": "number", "description": "Relative X coordinate percentage from 0.0 to 1.0"},
                    "rel_y": {"type": "number", "description": "Relative Y coordinate percentage from 0.0 to 1.0"}
                },
                "required": ["title_keyword", "rel_x", "rel_y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "play_youtube",
            "description": "Search YouTube for a song, video, or topic and automatically start playing the top video using relative window navigation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Song title, artist, or video search query"}
                },
                "required": ["query"]
            }
        }
    }
]


