"""
Laya Advanced System & Hardware Diagnostics (Pro Layer)
Process management, resource hog detection, NVIDIA GPU / VRAM telemetry,
disk analytics, and system maintenance.
"""

import os
import sys
import ctypes
import subprocess
from typing import Optional, List, Dict, Any
import psutil


class SystemProTools:
    _instance: Optional["SystemProTools"] = None

    @classmethod
    def get_instance(cls) -> "SystemProTools":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def list_processes(self, sort_by: str = "memory", top_n: int = 8) -> str:
        """List running processes sorted by memory or CPU usage."""
        try:
            procs = []
            sort_key = "memory_percent" if sort_by.lower() == "memory" else "cpu_percent"

            for p in psutil.process_iter(["pid", "name", "memory_info", "cpu_percent"]):
                try:
                    info = p.info
                    rss_mb = info["memory_info"].rss / (1024 * 1024) if info.get("memory_info") else 0
                    cpu = info.get("cpu_percent") or 0.0
                    procs.append({
                        "pid": info["pid"],
                        "name": info["name"] or "Unknown",
                        "mem_mb": rss_mb,
                        "cpu": cpu,
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if sort_by.lower() == "cpu":
                procs.sort(key=lambda x: x["cpu"], reverse=True)
                top = procs[:top_n]
                lines = [f"Top {len(top)} processes by CPU usage:"]
                for p in top:
                    lines.append(f"  • {p['name']} (PID {p['pid']}): {p['cpu']:.1f}% CPU, {p['mem_mb']:.0f} MB RAM")
            else:
                procs.sort(key=lambda x: x["mem_mb"], reverse=True)
                top = procs[:top_n]
                lines = [f"Top {len(top)} processes by memory usage:"]
                for p in top:
                    lines.append(f"  • {p['name']} (PID {p['pid']}): {p['mem_mb']:.0f} MB RAM, {p['cpu']:.1f}% CPU")

            return "\n".join(lines)
        except Exception as e:
            return f"Failed listing processes: {e}"

    def kill_process(self, name_or_pid: str) -> str:
        """Terminate a process by name or PID."""
        target = str(name_or_pid).strip()
        killed = []
        try:
            if target.isdigit():
                pid = int(target)
                p = psutil.Process(pid)
                p_name = p.name()
                p.kill()
                return f"Terminated process '{p_name}' (PID {pid})."

            target_lower = target.lower()
            if not target_lower.endswith(".exe"):
                target_lower += ".exe"

            for p in psutil.process_iter(["pid", "name"]):
                try:
                    if p.info["name"] and p.info["name"].lower() == target_lower:
                        p.kill()
                        killed.append(f"{p.info['name']} (PID {p.info['pid']})")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if killed:
                return f"Terminated: {', '.join(killed)}."
            return f"No running process found matching '{name_or_pid}'."
        except Exception as e:
            return f"Failed killing process '{name_or_pid}': {e}"

    def get_gpu_vram_status(self) -> str:
        """Query live NVIDIA GPU VRAM and utilization telemetry."""
        try:
            cmd = ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu", "--format=csv,noheader,nounits"]
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            if p.returncode == 0 and p.stdout.strip():
                parts = [x.strip() for x in p.stdout.strip().split(",")]
                if len(parts) >= 6:
                    name, total, used, free, util, temp = parts[:6]
                    pct = (float(used) / float(total)) * 100 if float(total) > 0 else 0
                    return (
                        f"GPU: {name} | "
                        f"VRAM: {used} MB of {total} MB used ({pct:.1f}%, {free} MB free) | "
                        f"Core Load: {util}% | Temp: {temp}°C."
                    )
        except Exception:
            pass

        # Fallback to PyTorch CUDA if available
        try:
            import torch
            if torch.cuda.is_available():
                device = torch.cuda.current_device()
                name = torch.cuda.get_device_name(device)
                total = torch.cuda.get_device_properties(device).total_memory / (1024 * 1024)
                alloc = torch.cuda.memory_allocated(device) / (1024 * 1024)
                return f"GPU: {name} | PyTorch Allocated VRAM: {alloc:.0f} MB / {total:.0f} MB."
        except Exception:
            pass

        return "No NVIDIA GPU telemetry available."

    def get_disk_space(self) -> str:
        """Check available disk storage on main partitions."""
        try:
            results = []
            for part in psutil.disk_partitions(all=False):
                if os.name == 'nt' and ('cdrom' in part.opts or part.fstype == ''):
                    continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    total_gb = usage.total / (1024**3)
                    free_gb = usage.free / (1024**3)
                    used_gb = usage.used / (1024**3)
                    results.append(
                        f"Drive {part.mountpoint} ({part.fstype}): "
                        f"{free_gb:.1f} GB free of {total_gb:.1f} GB ({usage.percent}% used)"
                    )
                except PermissionError:
                    continue
            return " | ".join(results) if results else "No storage partitions accessible."
        except Exception as e:
            return f"Failed checking disk space: {e}"

    def empty_recycle_bin(self) -> str:
        """Silently empty the Windows Recycle Bin."""
        try:
            # 7 = SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
            res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
            if res == 0:
                return "Recycle bin emptied successfully."
            return f"Recycle bin returned code {res}."
        except Exception as e:
            return f"Failed emptying recycle bin: {e}"


def get_system_pro_tools() -> SystemProTools:
    return SystemProTools.get_instance()
