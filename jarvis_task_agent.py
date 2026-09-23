"""
Universal Computer Task Engine: Executes arbitrary Windows tasks safely using native tools & LLM planning.
Protected by Laya System 1 destructive safety gate.
"""
import os
import re
import socket
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Tuple

from jarvis_config import DESTRUCTIVE_THRESHOLD
from jarvis_reflex import JarvisReflex
import jarvis_llm as llm


class UniversalTaskAgent:
    """Safely executes any computer task on Windows."""

    def __init__(self, reflex: JarvisReflex = None):
        self.reflex = reflex or JarvisReflex(preload=False)

    def execute_task(self, task_description: str, auto_confirm: bool = False) -> Dict[str, Any]:
        """
        Interprets task, checks safety with Laya, and executes cleanly on Windows.
        """
        # 1. Check for quick built-in system routines
        quick_res = self._try_quick_system_task(task_description)
        if quick_res is not None:
            return {"status": "SUCCESS", "message": quick_res, "is_destructive": 0.0}

        # 2. Check for application termination tasks (e.g. "close chrome")
        close_res = self._try_close_app(task_description)
        if close_res is not None:
            return {"status": "SUCCESS", "message": close_res, "is_destructive": 0.1}

        # 3. For arbitrary tasks: Generate safe PowerShell action via System 2 LLM
        prompt = (
            f"Generate a single, clean Windows PowerShell command to perform this task: \"{task_description}\".\n"
            f"Rules:\n"
            f"- Return ONLY the command enclosed in ```powershell ... ``` or ```bash ... ```.\n"
            f"- Use safe, standard PowerShell cmdlets (e.g. New-Item, Get-ChildItem, Test-Connection, Start-Process).\n"
            f"- Do NOT add explanations or markdown text outside the code block."
        )

        llm_response = llm.query_system2_llm(prompt)
        cmd_match = re.search(r'```(?:powershell|bash|cmd)?\s*(.*?)\s*```', llm_response, re.DOTALL)
        if cmd_match:
            command = cmd_match.group(1).strip()
        else:
            # Fallback to the text if it looks like a one-liner
            command = llm_response.split('\n')[0].strip()

        if not command or "Error" in command:
            return {
                "status": "FAILED",
                "message": f"Could not determine safe command for task: {llm_response}",
                "is_destructive": 0.0
            }

        # 4. Laya Safety Gate: Verify the planned command for destructive risk in <35ms
        safety_eval = self.reflex.evaluate(f"Execute command: {command}")
        is_destructive = safety_eval.get("is_destructive", 0.0)

        if is_destructive >= DESTRUCTIVE_THRESHOLD and not auto_confirm:
            return {
                "status": "BLOCKED_SAFETY",
                "command": command,
                "message": f"⚠️ Destructive command flagged (risk {is_destructive:.2f}): `{command}`. Confirmation required.",
                "is_destructive": is_destructive
            }

        # 5. Execute Command
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                timeout=12
            )
            output = (res.stdout or res.stderr or "Task completed successfully.").strip()
            return {
                "status": "SUCCESS" if res.returncode == 0 else "ERROR",
                "command": command,
                "message": output if output else "Task completed with no output.",
                "is_destructive": is_destructive
            }
        except subprocess.TimeoutExpired:
            return {"status": "TIMEOUT", "message": f"Command timed out: `{command}`", "is_destructive": is_destructive}
        except Exception as e:
            return {"status": "ERROR", "message": f"Execution error: {e}", "is_destructive": is_destructive}

    def _try_quick_system_task(self, query: str) -> Any:
        """Handles fast common system stats without LLM overhead."""
        q = query.lower().strip()

        # IP Address
        if "my ip" in q or "ip address" in q:
            try:
                hostname = socket.gethostname()
                ip = socket.gethostbyname(hostname)
                return f"Local IP Address: {ip} (Hostname: {hostname})"
            except Exception:
                pass

        # Battery Status
        if "battery" in q or "charge" in q:
            try:
                import psutil
                battery = psutil.sensors_battery()
                if battery:
                    status = "Plugged in" if battery.power_plugged else "On battery"
                    return f"Battery: {battery.percent}% ({status})"
            except ImportError:
                # Use Windows WMIC / PowerShell fallback
                res = subprocess.run(
                    ["powershell", "-Command", "(Get-CimInstance -ClassName Win32_Battery).EstimatedChargeRemaining"],
                    capture_output=True, text=True
                )
                if res.stdout.strip():
                    return f"Battery remaining: {res.stdout.strip()}%"

        # RAM / Memory
        if "ram" in q or "memory usage" in q or "free memory" in q:
            res = subprocess.run(
                ["powershell", "-Command", "$m = Get-CimInstance Win32_OperatingSystem; [math]::Round(($m.FreePhysicalMemory / 1024 / 1024), 2)"],
                capture_output=True, text=True
            )
            if res.stdout.strip():
                return f"Free RAM: {res.stdout.strip()} GB"

        return None

    def _try_close_app(self, query: str) -> Any:
        """Handles closing applications cleanly (e.g. 'close chrome', 'exit notepad')."""
        q = query.lower().strip()
        for prefix in ("close ", "kill ", "quit ", "exit ", "terminate "):
            if q.startswith(prefix):
                target = q[len(prefix):].strip()
                # Remove common extensions
                clean_target = target.replace(".exe", "").strip()
                if clean_target:
                    subprocess.run(f"taskkill /IM {clean_target}.exe /T /F", shell=True, capture_output=True)
                    return f"Terminated application: {clean_target.title()}"
        return None
