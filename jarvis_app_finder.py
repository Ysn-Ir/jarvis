"""
Universal App, Folder, and Settings Finder for Windows.
Dynamically resolves and opens any installed application, shell folder, or setting.
"""
import difflib
import os
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple

# Windows Shell Special Folders
SHELL_FOLDERS = {
    "downloads": "shell:Downloads",
    "download": "shell:Downloads",
    "documents": "shell:Personal",
    "document": "shell:Personal",
    "desktop": "shell:Desktop",
    "pictures": "shell:My Pictures",
    "photos": "shell:My Pictures",
    "videos": "shell:My Video",
    "music": "shell:My Music",
    "recycle bin": "shell:RecycleBinFolder",
    "trash": "shell:RecycleBinFolder",
}

# Windows Settings URIs (ms-settings:)
SETTINGS_URIS = {
    "bluetooth": "ms-settings:bluetooth",
    "wifi": "ms-settings:network-wifi",
    "network": "ms-settings:network",
    "sound": "ms-settings:sound",
    "audio": "ms-settings:sound",
    "volume": "ms-settings:sound",
    "display": "ms-settings:display",
    "screen": "ms-settings:display",
    "battery": "ms-settings:batterysaver",
    "power": "ms-settings:powersleep",
    "storage": "ms-settings:storagesense",
    "apps": "ms-settings:appsfeatures",
    "installed apps": "ms-settings:appsfeatures",
    "windows update": "ms-settings:windowsupdate",
    "update": "ms-settings:windowsupdate",
    "notifications": "ms-settings:notifications",
    "settings": "ms-settings:",
}

# Common Desktop Web Shortcuts
WEB_SHORTCUTS = {
    "youtube": "https://www.youtube.com",
    "github": "https://github.com",
    "google": "https://www.google.com",
    "chatgpt": "https://chatgpt.com",
    "reddit": "https://www.reddit.com",
    "huggingface": "https://huggingface.co",
    "twitter": "https://x.com",
    "gmail": "https://mail.google.com",
}


class UniversalAppFinder:
    """Discovers and opens any application or location on Windows."""

    def __init__(self):
        self.apps: Dict[str, str] = {}
        self.refresh_index()

    def refresh_index(self):
        """Scans Windows Start Menu directories for all installed application shortcuts."""
        search_dirs = [
            Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
            Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        ]

        self.apps.clear()
        for s_dir in search_dirs:
            if s_dir.exists():
                for lnk in s_dir.rglob("*.lnk"):
                    clean_name = lnk.stem.lower().strip()
                    # Exclude uninstaller links
                    if "uninstall" not in clean_name and "remove" not in clean_name:
                        self.apps[clean_name] = str(lnk)

    def resolve(self, query: str) -> Tuple[Optional[str], str]:
        """
        Resolves query to an executable path, shell command, URI, or URL.
        Returns: (target_path_or_uri, target_type)
        """
        q = query.lower().strip()
        # Remove common request prefixes
        for pfx in ("open ", "launch ", "start ", "run ", "show "):
            if q.startswith(pfx):
                q = q[len(pfx):].strip()

        # 1. Check Shell Special Folders (Downloads, Desktop, etc.)
        if q in SHELL_FOLDERS:
            return SHELL_FOLDERS[q], "folder"
        for folder_name, folder_uri in SHELL_FOLDERS.items():
            if folder_name in q:
                return folder_uri, "folder"

        # 2. Check Windows Settings (Bluetooth, Wifi, Sound, etc.)
        if q in SETTINGS_URIS:
            return SETTINGS_URIS[q], "setting"
        for setting_name, setting_uri in SETTINGS_URIS.items():
            if setting_name in q:
                return setting_uri, "setting"

        # 3. Check Web Shortcuts (YouTube, GitHub, etc.)
        if q in WEB_SHORTCUTS:
            return WEB_SHORTCUTS[q], "url"
        for site_name, site_url in WEB_SHORTCUTS.items():
            if site_name in q:
                return site_url, "url"

        # 4. Check Exact or Prefix Match in Indexed Applications
        if q in self.apps:
            return self.apps[q], "app"

        # Partial substring match (e.g. "discord" in "discord")
        for app_name, lnk_path in self.apps.items():
            if q == app_name or q in app_name.split() or app_name.startswith(q):
                return lnk_path, "app"

        # Fuzzy match for typos (e.g. "disocrd" -> "discord")
        matches = difflib.get_close_matches(q, list(self.apps.keys()), n=1, cutoff=0.6)
        if matches:
            matched_app = matches[0]
            return self.apps[matched_app], "app"

        # 5. Fallback: Return raw query to be launched via Windows shell
        return q, "shell_cmd"

    def open_target(self, query: str) -> str:
        """Resolves target and opens it natively on Windows."""
        target, target_type = self.resolve(query)
        if not target:
            return f"Could not find anything matching '{query}'."

        try:
            if target_type in ("app", "folder"):
                os.startfile(target)
                display_name = Path(target).stem if target.endswith(".lnk") else target
                return f"Opened {display_name} ({target_type})"

            elif target_type in ("setting", "url"):
                os.startfile(target)
                return f"Opened {target} ({target_type})"

            else:
                # Raw command fallback via Windows start
                subprocess.Popen(f"start {target}", shell=True)
                return f"Launched command: '{target}'"

        except Exception as e:
            # Fallback to shell start
            try:
                subprocess.Popen(f"start {target}", shell=True)
                return f"Launched '{target}'"
            except Exception as e2:
                return f"Failed to open '{target}': {e2}"
