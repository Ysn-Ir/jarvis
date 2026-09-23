"""
Laya Jupyter Notebook Autonomous Tools
Direct programmatic read, write, and cell insertion for Jupyter (.ipynb) notebooks
with 100% JSON schema fidelity and instant execution.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, List


class NotebookTools:
    _instance: Optional["NotebookTools"] = None

    @classmethod
    def get_instance(cls) -> "NotebookTools":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _resolve_notebook_path(self, path_str: str) -> Path:
        """Resolve notebook path from desktop, current directory, or absolute path."""
        p = Path(path_str.strip().strip('"').strip("'"))
        if p.exists():
            return p

        # Check Desktop
        desktop = Path.home() / "Desktop"
        if (desktop / p.name).exists():
            return desktop / p.name

        # If extension missing, add .ipynb
        if not p.name.endswith(".ipynb"):
            if (desktop / f"{p.name}.ipynb").exists():
                return desktop / f"{p.name}.ipynb"
            if Path(f"{path_str}.ipynb").exists():
                return Path(f"{path_str}.ipynb")

        # Search desktop for any matching ipynb
        for f in desktop.glob("*.ipynb"):
            if p.name.lower() in f.name.lower():
                return f

        # Fallback to desktop path for new file creation
        if not p.is_absolute():
            return desktop / (p.name if p.name.endswith(".ipynb") else f"{p.name}.ipynb")
        return p

    def create_notebook(self, notebook_path: str) -> str:
        """Create a new empty Jupyter notebook (.ipynb)."""
        target = self._resolve_notebook_path(notebook_path)
        nb_data = {
            "cells": [],
            "metadata": {
                "language_info": {"name": "python", "version": "3.12"},
                "orig_nbformat": 4
            },
            "nbformat": 4,
            "nbformat_minor": 5
        }
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                json.dump(nb_data, f, indent=2)
            return f"Created Jupyter notebook at '{target}'."
        except Exception as e:
            return f"Failed to create notebook: {e}"

    def write_notebook_cell(
        self,
        notebook_path: str,
        code: str,
        cell_type: str = "code",
        position: Optional[int] = None
    ) -> str:
        """
        Append or insert a code or markdown cell into a Jupyter notebook (.ipynb).
        """
        target = self._resolve_notebook_path(notebook_path)
        if not target.exists():
            self.create_notebook(str(target))

        try:
            with open(target, "r", encoding="utf-8") as f:
                nb_data = json.load(f)

            if "cells" not in nb_data:
                nb_data["cells"] = []

            # Format code lines with newline characters
            source_lines = [line + "\n" for line in code.split("\n")]
            if source_lines and source_lines[-1].endswith("\n"):
                source_lines[-1] = source_lines[-1][:-1]

            new_cell: Dict[str, Any] = {
                "cell_type": "markdown" if cell_type.lower() == "markdown" else "code",
                "metadata": {},
                "source": source_lines,
            }
            if new_cell["cell_type"] == "code":
                new_cell["execution_count"] = None
                new_cell["outputs"] = []

            if position is not None and 0 <= position < len(nb_data["cells"]):
                nb_data["cells"].insert(position, new_cell)
                idx_msg = f"at position {position}"
            else:
                nb_data["cells"].append(new_cell)
                idx_msg = f"as cell #{len(nb_data['cells'])}"

            with open(target, "w", encoding="utf-8") as f:
                json.dump(nb_data, f, indent=2)

            preview = code[:45].replace("\n", " ") + ("..." if len(code) > 45 else "")
            return f"Successfully wrote {new_cell['cell_type']} cell {idx_msg} in '{target.name}': '{preview}'."

        except Exception as e:
            return f"Failed writing to notebook '{notebook_path}': {e}"

    def read_notebook_cells(self, notebook_path: str) -> str:
        """Read and summarize all cells in a Jupyter notebook (.ipynb)."""
        target = self._resolve_notebook_path(notebook_path)
        if not target.exists():
            return f"Notebook file '{notebook_path}' not found."

        try:
            with open(target, "r", encoding="utf-8") as f:
                nb_data = json.load(f)

            cells = nb_data.get("cells", [])
            if not cells:
                return f"Notebook '{target.name}' is empty (0 cells)."

            summaries = []
            for i, c in enumerate(cells):
                ctype = c.get("cell_type", "code")
                src = "".join(c.get("source", [])).strip()
                preview = src[:70].replace("\n", " ") + ("..." if len(src) > 70 else "")
                summaries.append(f"[{i+1}] ({ctype}) {preview}")

            return f"Notebook '{target.name}' ({len(cells)} cells):\n" + "\n".join(summaries[:15])

        except Exception as e:
            return f"Failed reading notebook: {e}"


def get_notebook_tools() -> NotebookTools:
    return NotebookTools.get_instance()
