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
            "name": "set_reminder",
            "description": "Set a timed reminder. When the time comes, Laya will speak the reminder aloud and show a Windows notification. Use when the user says things like 'remind me to X in Y minutes', 'remind me to call someone at 3pm', 'set a timer for X', or 'remember to X in Y hours'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "What to remind the user about (e.g. 'call mom', 'take your medicine', 'check the oven')"},
                    "minutes": {"type": "number", "description": "Minutes from now to fire the reminder (can be fractional, e.g. 1.5 for 90 seconds). Use 0 if specifying hours or seconds only."},
                    "hours": {"type": "number", "description": "Hours from now. Use 0 if specifying minutes only."},
                    "seconds": {"type": "number", "description": "Additional seconds. Usually 0 unless precision matters."}
                },
                "required": ["message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_reminders",
            "description": "List all pending (not yet fired) reminders or timers that have been scheduled.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_reminders",
            "description": "Cancel or clear pending timers or reminders. Use when the user says 'cancel timer', 'stop timer', 'clear reminders', or 'cancel all timers'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Optional keyword or 'all' to cancel all timers/reminders"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "turn_screen_off",
            "description": "Turn off the physical computer screen, monitor, or display immediately.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "turn_screen_on",
            "description": "Turn on or wake up the computer screen/monitor/display.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sleep_system",
            "description": "Put the computer/system into sleep or suspend state immediately.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lock_workstation",
            "description": "Lock the Windows computer screen or workstation immediately.",
            "parameters": {
                "type": "object",
                "properties": {
                    "delay_sec": {"type": "integer", "description": "Optional delay in seconds before locking (default 0)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "record_screen",
            "description": "Start, stop, or toggle screen video recording to Videos/Captures (.mp4 format).",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration": {"type": "integer", "description": "Optional recording duration in seconds (0 for indefinite until stopped)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "stop_screen_recording",
            "description": "Stop any active screen recording and save the video file.",
            "parameters": {
                "type": "object",
                "properties": {}
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
    },
    {
        "type": "function",
        "function": {
            "name": "drag_window_relative",
            "description": "Drag the mouse from a relative start coordinate to a relative end coordinate inside a window (0.0 to 1.0 percentages).",
            "parameters": {
                "type": "object",
                "properties": {
                    "title_keyword": {"type": "string", "description": "Target window title substring"},
                    "start_rel_x": {"type": "number", "description": "Starting relative X ratio (0.0 to 1.0)"},
                    "start_rel_y": {"type": "number", "description": "Starting relative Y ratio (0.0 to 1.0)"},
                    "end_rel_x": {"type": "number", "description": "Ending relative X ratio (0.0 to 1.0)"},
                    "end_rel_y": {"type": "number", "description": "Ending relative Y ratio (0.0 to 1.0)"},
                    "duration": {"type": "number", "description": "Drag movement duration in seconds, default 0.4"}
                },
                "required": ["title_keyword", "start_rel_x", "start_rel_y", "end_rel_x", "end_rel_y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "draw_relative_shape",
            "description": "Draw a clean geometric shape (square, circle, triangle, star, heart) inside a drawing window canvas (e.g. Paint) using relative percentages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title_keyword": {"type": "string", "description": "Drawing window title substring (e.g. 'Paint')"},
                    "shape": {"type": "string", "enum": ["square", "circle", "triangle", "star", "heart"], "description": "Geometric shape to draw"},
                    "center_rel_x": {"type": "number", "description": "Relative X center ratio (0.0 to 1.0), default 0.5"},
                    "center_rel_y": {"type": "number", "description": "Relative Y center ratio (0.0 to 1.0), default 0.5"},
                    "size_rel": {"type": "number", "description": "Relative size ratio of the shape (0.05 to 0.5), default 0.25"}
                },
                "required": ["title_keyword", "shape"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_message",
            "description": "Send a chat message to a contact or phone number via Telegram or WhatsApp.",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient": {"type": "string", "description": "Contact name, username, or phone number"},
                    "message": {"type": "string", "description": "Text message content to send"}
                },
                "required": ["recipient", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_telegram",
            "description": "Send a direct message to a contact or username specifically on Telegram.",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient": {"type": "string", "description": "Telegram username or contact name"},
                    "message": {"type": "string", "description": "Text message content"}
                },
                "required": ["recipient", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_whatsapp",
            "description": "Send a direct message to a contact specifically on WhatsApp.",
            "parameters": {
                "type": "object",
                "properties": {
                    "contact": {"type": "string", "description": "WhatsApp contact name or phone number"},
                    "message": {"type": "string", "description": "Text message content"}
                },
                "required": ["contact", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "telegram_broadcast",
            "description": "Broadcast a message to all Telegram contacts, chats, or active users.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Announcement or broadcast message content to send to all contacts"}
                },
                "required": ["message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "telegram_sync_contacts",
            "description": "Fetch and synchronize all contacts from user's Telegram account into local address book.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "telegram_list_contacts",
            "description": "List and display contacts from the Telegram account.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_to_file",
            "description": "Write or append text content directly to a file (creates the file if needed). Use for saving notes, logs, data, or code to the filesystem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Target filename or path (e.g. 'notes.txt', 'desktop/log.txt')"},
                    "content": {"type": "string", "description": "Text content to write to the file"}
                },
                "required": ["filename", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_to_notepad",
            "description": "Open Notepad (or use the currently active Notepad window) and type or paste the given text into it. Optionally saves to a named .txt file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to type or paste into Notepad"},
                    "filename": {"type": "string", "description": "Optional .txt filename to save to (e.g. 'ideas.txt'); if omitted, types directly into open Notepad"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_search",
            "description": "Search the web using Google or YouTube in the default browser and navigate to the results page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query terms"},
                    "engine": {"type": "string", "enum": ["google", "youtube", "bing", "duckduckgo"], "description": "Search engine to use (default: google)"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browser_open_url",
            "description": "Navigate the browser to a specific URL directly.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL (e.g. 'https://github.com', 'https://reddit.com/r/python')"}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "answer_question",
            "description": "Return a direct spoken answer to the user's question without calling any additional tools. Use when you have enough information to answer from memory, context, or general knowledge.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Complete answer text to speak to the user"}
                },
                "required": ["text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "zoom_window_region",
            "description": "Zoom into and magnify a specific region of any window or the full screen and display it in a floating HUD overlay. Use when the user says 'zoom in', 'magnify', 'show me a closer look', 'zoom into the corner/center/top-right', etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "enum": ["center", "top-left", "top-right", "bottom-left", "bottom-right", "top", "bottom", "left", "right", "custom"],
                        "description": "Named region to zoom into. Use 'center' for middle, 'top-left', 'top-right', 'bottom-left', 'bottom-right' for corners, 'top'/'bottom'/'left'/'right' for edges."
                    },
                    "title_keyword": {
                        "type": "string",
                        "description": "Optional window title to zoom (e.g. 'Chrome', 'Explorer', 'Paint'). Leave empty to zoom the full screen."
                    },
                    "zoom_factor": {
                        "type": "number",
                        "description": "Magnification multiplier, e.g. 2.0 for 2×, 3.0 for 3× zoom. Default is 2.5."
                    },
                    "rel_x": {"type": "number", "description": "Custom region anchor X (0.0–1.0), used only when region='custom'"},
                    "rel_y": {"type": "number", "description": "Custom region anchor Y (0.0–1.0), used only when region='custom'"},
                    "rel_w": {"type": "number", "description": "Custom region width ratio (0.0–1.0), used only when region='custom'"},
                    "rel_h": {"type": "number", "description": "Custom region height ratio (0.0–1.0), used only when region='custom'"}
                },
                "required": ["region"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scroll_window",
            "description": "Scroll up, down, left, or right inside the active window or any named application window (browser, File Explorer, document, terminal, etc.). Use for 'scroll up/down', 'scroll in Chrome', 'go to top/bottom', 'page down', etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["up", "down", "left", "right", "page_up", "page_down", "top", "bottom"],
                        "description": "Scroll direction. 'top'/'bottom' jumps to start/end (Ctrl+Home/End). 'page_up'/'page_down' scrolls one full page."
                    },
                    "amount": {
                        "type": "integer",
                        "description": "Number of scroll notches (default 5). More = scroll further."
                    },
                    "title_keyword": {
                        "type": "string",
                        "description": "Optional window title to scroll (e.g. 'Chrome', 'Explorer', 'Notepad'). Empty means active window."
                    }
                },
                "required": ["direction"]
            }
        }
    }
]

# -----------------------------------------------------------------
# High-Efficiency Core Toolset (~1,400 tokens)
# Prevents context bloat and guarantees staying well under the 8,000 TPM limit
# -----------------------------------------------------------------
CORE_TOOL_NAMES = {
    "answer_question",
    "open_app",
    "close_app",
    "focus_window",
    "write_to_notepad",
    "write_to_file",
    "create_file",
    "open_file",
    "browser_search",
    "browser_open_url",
    "play_youtube",
    "scroll_window",
    "zoom_window_region",
    "draw_shape",
    "keyboard_type",
    "mouse_click",
    "check_system",
    "send_message",
    "set_reminder",
    "list_reminders",
    "cancel_reminders",
    "turn_screen_off",
    "turn_screen_on",
    "sleep_system",
    "lock_workstation",
    "record_screen",
    "stop_screen_recording",
}

CORE_TOOLS_SCHEMA: List[Dict[str, Any]] = [
    tool for tool in TOOLS_SCHEMA
    if tool.get("function", {}).get("name") in CORE_TOOL_NAMES
]

# Add on-demand tool discovery tool
CORE_TOOLS_SCHEMA.append({
    "type": "function",
    "function": {
        "name": "search_tools",
        "description": "Discover specialized tools from the full capability registry (e.g. Word .docx, Excel .xlsx, PowerShell execution, window geometry, system diagnostics). Use when the core tools cannot fulfill a specialized user request.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Keywords describing the capability needed (e.g. 'excel', 'word', 'powershell', 'kill')"}
            },
            "required": ["query"]
        }
    }
})


