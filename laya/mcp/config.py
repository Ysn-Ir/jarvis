"""
Laya MCP (Model Context Protocol) Server Configurations
Defines 12 production-ready, standardized MCP servers across:
- Windows Desktop & OS Control (windows-mcp)
- Persistent Web & Social Automation (@playwright/mcp with persistent user-data-dir)
- Filesystem & Knowledge Graph Memory (@modelcontextprotocol/server-filesystem & memory)
- Web HTTP & Readability Fetch (mcp-server-fetch)
- Email / Gmail IMAP+SMTP (mcp-email-server)
- Personal Telegram MTProto (@dikacode/telegram-mcp)
- Discord Server & DM Automation (@pasympa/discord-mcp)
- Instagram Graph API & Web (@mcpware/instagram-mcp)
- Microsoft Office Suite (office-powerpoint-mcp-server, office-word-mcp-server, excel-mcp-server)
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any

HOME_DIR = str(Path.home())
LAYA_HOME_DIR = Path.home() / ".laya"
LAYA_HOME_DIR.mkdir(parents=True, exist_ok=True)

PLAYWRIGHT_PROFILE_DIR = LAYA_HOME_DIR / "browser_profile"
PLAYWRIGHT_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

TELEGRAM_SESSION_DIR = LAYA_HOME_DIR / "telegram_mcp_session"
TELEGRAM_SESSION_DIR.mkdir(parents=True, exist_ok=True)


def build_runtime_server_env(server_name: str, static_env: Dict[str, str]) -> Dict[str, str]:
    """Build fresh live environment variables for an MCP server from current os.environ."""
    env = dict(os.environ)
    env.update(static_env or {})

    if server_name == "email":
        user = os.getenv("EMAIL_USER", "").strip()
        pwd = os.getenv("EMAIL_PASSWORD", "").strip()
        imap_host = os.getenv("EMAIL_IMAP_SERVER", "").strip()
        if not imap_host and user:
            low = user.lower()
            if "gmail.com" in low:
                imap_host = "imap.gmail.com"
            elif "outlook.com" in low or "hotmail.com" in low:
                imap_host = "outlook.office365.com"
            elif "yahoo.com" in low:
                imap_host = "imap.mail.yahoo.com"
            else:
                imap_host = "imap.gmail.com"
        smtp_host = os.getenv("EMAIL_SMTP_SERVER", "").strip()
        if not smtp_host and imap_host:
            smtp_host = "smtp.gmail.com" if "gmail" in imap_host else imap_host.replace("imap.", "smtp.")

        env["PYTHONUNBUFFERED"] = "1"
        if user and pwd:
            env.update({
                "MCP_EMAIL_SERVER_ACCOUNT_NAME": "primary",
                "MCP_EMAIL_SERVER_FULL_NAME": "Laya User",
                "MCP_EMAIL_SERVER_EMAIL_ADDRESS": user,
                "MCP_EMAIL_SERVER_USER_NAME": user,
                "MCP_EMAIL_SERVER_PASSWORD": pwd,
                "MCP_EMAIL_SERVER_IMAP_HOST": imap_host or "imap.gmail.com",
                "MCP_EMAIL_SERVER_IMAP_PORT": os.getenv("EMAIL_IMAP_PORT", "993"),
                "MCP_EMAIL_SERVER_SMTP_HOST": smtp_host or "smtp.gmail.com",
                "MCP_EMAIL_SERVER_SMTP_PORT": os.getenv("EMAIL_SMTP_PORT", "465"),
            })

    elif server_name == "telegram":
        env["TELEGRAM_UPDATE_CHECK"] = "0"
        env["TELEGRAM_ALLOW_ALL_CHATS"] = "true"
        env["TELEGRAM_SESSION_PATH"] = str(TELEGRAM_SESSION_DIR / "session")
        for key in ("TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TELEGRAM_PHONE"):
            val = os.getenv(key, "").strip()
            if val:
                env[key] = val

    elif server_name == "discord":
        env["DISCORD_MCP_TOOLSETS"] = os.getenv("DISCORD_MCP_TOOLSETS", "discovery,messages")
        token = os.getenv("DISCORD_TOKEN", "").strip()
        if token:
            env["DISCORD_TOKEN"] = token

    elif server_name == "instagram":
        for key in ("INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_ACCOUNT_ID", "INSTAGRAM_API_VERSION"):
            val = os.getenv(key, "").strip()
            if val:
                env[key] = val

    return env


DEFAULT_MCP_SERVERS: Dict[str, Dict[str, Any]] = {
    # 1. Windows Desktop Automation & OS Control (CursorTouch Windows-MCP)
    "windows": {
        "command": sys.executable,
        "args": ["-m", "windows_mcp", "serve", "--transport", "stdio"],
        "description": "Native Windows OS automation, UIA Snapshot, Click, Type, Shortcut, PowerShell, Process, Registry",
        "enabled": True,
    },

    # 2. Microsoft Official Playwright MCP Server (Persistent Profile)
    "browser": {
        "command": "npx",
        "args": ["-y", "@playwright/mcp@latest", "--user-data-dir", str(PLAYWRIGHT_PROFILE_DIR)],
        "description": "Persistent Chromium browser automation (YouTube, Discord Web, Instagram Web, WhatsApp Web, Gmail Web, Spotify)",
        "enabled": True,
    },

    # 3. Anthropic Official Filesystem MCP Server
    "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", HOME_DIR],
        "description": "Anthropic official sandboxed filesystem operations",
        "enabled": True,
    },

    # 4. Anthropic Official Knowledge Graph Memory Server
    "memory": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
        "env": {
            "MEMORY_FILE_PATH": str(LAYA_HOME_DIR / "memory_graph.jsonl")
        },
        "description": "Anthropic official persistent knowledge graph memory store across sessions",
        "enabled": True,
    },

    # 5. Official MCP Web Fetch Server
    "fetch": {
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "description": "Official MCP server for HTTP requests and web content extraction",
        "enabled": True,
    },

    # 6. Production Email / Gmail IMAP+SMTP MCP Server
    "email": {
        "command": "uvx",
        "args": ["mcp-email-server", "stdio"],
        "description": "Full IMAP/SMTP email control (read, search, send, forward, reply, drafts, flags) for Gmail/Outlook/IMAP",
        "enabled": True,
    },

    # 7. Production Telegram MTProto Account MCP Server
    "telegram": {
        "command": "npx",
        "args": ["-y", "@dikacode/telegram-mcp"],
        "description": "Full personal Telegram account control over MTProto (chats, messages, contacts, login, media)",
        "enabled": True,
    },

    # 8. Production Discord MCP Server
    "discord": {
        "command": "npx",
        "args": ["-y", "@pasympa/discord-mcp"],
        "description": "Discord guild, channel, DM, and message automation via MCP",
        "enabled": True,
    },

    # 9. Production Instagram Graph MCP Server
    "instagram": {
        "command": "npx",
        "args": ["-y", "@mcpware/instagram-mcp"],
        "description": "Instagram Graph API MCP server for posts, comments, DMs, reels, hashtags, analytics",
        "enabled": True,
    },

    # 10. Microsoft PowerPoint MCP Server
    "powerpoint": {
        "command": "uvx",
        "args": ["--with", "mcp<2", "--from", "office-powerpoint-mcp-server", "ppt_mcp_server.exe"],
        "description": "Full Microsoft PowerPoint presentation creation, slides, layouts, styling, charts",
        "enabled": True,
    },

    # 11. Microsoft Word MCP Server
    "word": {
        "command": "uvx",
        "args": ["--from", "office-word-mcp-server", "word_mcp_server.exe"],
        "description": "Full Microsoft Word (.docx) document creation, editing, headings, tables, formatting",
        "enabled": True,
    },

    # 12. Microsoft Excel MCP Server
    "excel": {
        "command": "uvx",
        "args": ["excel-mcp-server", "stdio"],
        "description": "Full Microsoft Excel (.xlsx) workbook, sheets, formulas, charts, formatting",
        "enabled": True,
    },
}
