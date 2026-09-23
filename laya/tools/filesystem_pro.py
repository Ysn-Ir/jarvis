"""
Laya Filesystem Pro
Deep filesystem inspection, reading, recursive search, and directory organization.
Enables Laya to read notes, configs, scripts, search across drives, and manage files.
"""

import os
import shutil
import fnmatch
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

from laya.config import DOCS_DIR


class FilesystemPro:
    _instance: Optional["FilesystemPro"] = None

    @classmethod
    def get_instance(cls) -> "FilesystemPro":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _resolve_path(self, raw_path: str) -> Path:
        """Resolve aliases and relative paths to an absolute Path object."""
        if not raw_path or raw_path.strip().lower() in ["", "desktop"]:
            return Path.home() / "Desktop"
        p_str = raw_path.strip()
        p_lower = p_str.lower().replace("\\", "/")

        if p_lower.startswith("desktop/"):
            return Path.home() / "Desktop" / p_str[len("desktop/"):]
        if p_lower == "downloads" or p_lower.startswith("downloads/"):
            sub = p_str[len("downloads/"):] if p_lower.startswith("downloads/") else ""
            return Path.home() / "Downloads" / sub
        if p_lower == "documents" or p_lower.startswith("documents/"):
            sub = p_str[len("documents/"):] if p_lower.startswith("documents/") else ""
            return DOCS_DIR / sub

        # Check direct or relative path
        p = Path(p_str)
        if p.is_absolute() and p.exists():
            return p

        desktop_check = Path.home() / "Desktop" / p_str
        if desktop_check.exists():
            return desktop_check

        return p.resolve()

    def read_file_content(self, filepath: str, max_lines: int = 150) -> str:
        """
        Read and return the text contents of a file on the local system.
        """
        if not filepath:
            return "No filepath provided."

        target = self._resolve_path(filepath)
        if not target.exists():
            return f"File does not exist: {target}"
        if not target.is_file():
            return f"Path is a directory, not a file: {target}"

        try:
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                lines = [f.readline() for _ in range(max_lines)]
                has_more = bool(f.readline())

            content = "".join(lines)
            if not content.strip():
                return f"File '{target.name}' is empty."

            preview = f"--- Content of '{target.name}' ({target.resolve()}) ---\n{content}"
            if has_more:
                preview += f"\n... [Remaining lines omitted, showing first {max_lines} lines]"
            return preview

        except Exception as e:
            return f"Failed to read file '{target}': {e}"

    def list_directory(self, path: str = "desktop") -> str:
        """
        List all files and subdirectories with sizes and modified timestamps.
        """
        target = self._resolve_path(path)
        if not target.exists():
            return f"Directory does not exist: {target}"
        if not target.is_dir():
            return f"Path is not a directory: {target}"

        try:
            items = []
            for item in sorted(target.iterdir()):
                if item.name.startswith((".", "$")):
                    continue
                stat = item.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                if item.is_dir():
                    items.append(f"📁 {item.name}/ [DIR] ({mtime})")
                else:
                    size_kb = stat.st_size / 1024
                    size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.2f} MB"
                    items.append(f"📄 {item.name} ({size_str}, {mtime})")

            if not items:
                return f"Directory '{target.name}' is empty."

            return f"Directory listing for {target.resolve()} ({len(items)} items):\n" + "\n".join(items[:40])

        except Exception as e:
            return f"Failed to list directory '{target}': {e}"

    def search_filesystem(self, pattern: str, root_dir: str = "desktop", recursive: bool = True) -> str:
        """
        Search for files matching a wildcard pattern (e.g. '*.pdf', '*invoice*', '*.py').
        """
        if not pattern:
            return "No search pattern provided."

        target = self._resolve_path(root_dir)
        if not target.exists():
            return f"Search root directory does not exist: {target}"

        clean_pattern = pattern.strip()
        if not ("*" in clean_pattern or "?" in clean_pattern):
            clean_pattern = f"*{clean_pattern}*"

        matches = []
        try:
            iterator = target.rglob(clean_pattern) if recursive else target.glob(clean_pattern)
            for p in iterator:
                if p.is_file() and not p.name.startswith("."):
                    size_kb = p.stat().st_size / 1024
                    matches.append(f"• {p.name} ({size_kb:.1f} KB) -> {p.resolve()}")
                    if len(matches) >= 15:
                        break

            if not matches:
                return f"No files matching '{clean_pattern}' found in {target.resolve()}."

            return f"Search results for '{clean_pattern}' in {target.resolve()} ({len(matches)} found):\n" + "\n".join(matches)

        except Exception as e:
            return f"Error searching filesystem: {e}"

    def organize_directory(self, directory: str = "downloads", by: str = "extension") -> str:
        """
        Organize unorganized files in a folder into categorized subfolders.
        """
        target = self._resolve_path(directory)
        if not target.exists() or not target.is_dir():
            return f"Directory does not exist: {target}"

        EXT_MAP = {
            "Images": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg", ".webp"],
            "Documents": [".pdf", ".docx", ".doc", ".xlsx", ".pptx", ".txt", ".csv", ".md"],
            "Installers": [".exe", ".msi", ".iso"],
            "Archives": [".zip", ".tar", ".gz", ".7z", ".rar"],
            "Code": [".py", ".js", ".ts", ".html", ".css", ".cpp", ".json", ".sql"],
        }

        moved_count = 0
        try:
            for item in target.iterdir():
                if item.is_file() and not item.name.startswith("."):
                    ext = item.suffix.lower()
                    target_category = None
                    for cat, exts in EXT_MAP.items():
                        if ext in exts:
                            target_category = cat
                            break
                    if not target_category:
                        target_category = "Other"

                    dest_dir = target / target_category
                    dest_dir.mkdir(exist_ok=True)
                    shutil.move(str(item), str(dest_dir / item.name))
                    moved_count += 1

            return f"Organized {moved_count} files into categorized folders in {target.resolve()}."

        except Exception as e:
            return f"Failed to organize directory: {e}"


def get_filesystem_pro() -> FilesystemPro:
    return FilesystemPro.get_instance()
