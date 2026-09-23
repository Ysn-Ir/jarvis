"""
Laya Code Interpreter Engine (Open-Interpreter Paradigm)
Universal Python & PowerShell execution environment allowing Laya to solve
arbitrary computational, analytical, filesystem, and automation tasks.
"""

import sys
import subprocess
from typing import Optional


class CodeInterpreter:
    _instance: Optional["CodeInterpreter"] = None

    @classmethod
    def get_instance(cls) -> "CodeInterpreter":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def run_python(self, code: str, timeout_sec: int = 15) -> str:
        """
        Execute arbitrary Python code in the local environment and return stdout/stderr.
        Enables the agent to process data, query APIs, manipulate files, and solve open-ended tasks.
        """
        if not code or not code.strip():
            return "No Python code provided to execute."

        clean_code = code.strip()
        # Strip markdown code fences if model enclosed them
        if clean_code.startswith("```python"):
            clean_code = clean_code[len("```python"):].strip()
        elif clean_code.startswith("```"):
            clean_code = clean_code[len("```"):].strip()
        if clean_code.endswith("```"):
            clean_code = clean_code[:-3].strip()

        try:
            process = subprocess.run(
                [sys.executable, "-c", clean_code],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                encoding="utf-8",
                errors="replace"
            )

            stdout = process.stdout.strip()
            stderr = process.stderr.strip()

            if process.returncode != 0:
                err_msg = stderr or stdout or f"Exited with code {process.returncode}"
                return f"[Python Error - Exit Code {process.returncode}]:\n{err_msg}"

            if not stdout and not stderr:
                return "Python code executed successfully (no stdout returned)."

            output = stdout
            if stderr:
                output += f"\n[stderr]: {stderr}"

            # Limit length to avoid blowing context window
            if len(output) > 2500:
                output = output[:2500] + "\n... [Output truncated]"

            return output

        except subprocess.TimeoutExpired:
            return f"[Execution Timeout]: Python script timed out after {timeout_sec} seconds."
        except Exception as e:
            return f"[Execution Error]: {e}"

    def run_powershell(self, command: str, timeout_sec: int = 15) -> str:
        """
        Execute an arbitrary PowerShell command and return output.
        Non-blocking execution is used for GUI apps like Notepad and Explorer.
        """
        if not command or not command.strip():
            return "No PowerShell command provided."

        clean_cmd = command.strip()

        # Handle GUI launches without blocking
        lower_cmd = clean_cmd.lower()
        if any(w in lower_cmd for w in ["start ", "notepad", "explorer", "calc", "mspaint"]):
            try:
                subprocess.Popen(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", clean_cmd],
                    shell=True
                )
                return f"Launched command in background: '{clean_cmd}'."
            except Exception as e:
                return f"Failed to launch command: {e}"

        try:
            process = subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", clean_cmd],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                encoding="utf-8",
                errors="replace"
            )

            stdout = process.stdout.strip()
            stderr = process.stderr.strip()

            if process.returncode != 0:
                return f"[PowerShell Error - Exit Code {process.returncode}]:\n{stderr or stdout}"

            output = stdout or stderr or "PowerShell command executed successfully."
            if len(output) > 2500:
                output = output[:2500] + "\n... [Output truncated]"

            return output

        except subprocess.TimeoutExpired:
            return f"[PowerShell Timeout]: Command timed out after {timeout_sec} seconds."
        except Exception as e:
            return f"[PowerShell Execution Error]: {e}"


def get_code_interpreter() -> CodeInterpreter:
    return CodeInterpreter.get_instance()
