"""
Jarvis Master Controller (v5.0 Unified Architecture)
Orchestrates System 1 routing, safety gating, and deterministic OS execution.
"""
import sys
import time
from typing import Dict, Any

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from jarvis_config import DESTRUCTIVE_THRESHOLD
from jarvis_router import JarvisRouter
from jarvis_core import DocumentEngine, CommsEngine, SystemEngine, AppEngine, FileEngine, GUIEngine
import jarvis_brain as brain


class JarvisController:
    """Master controller for the Jarvis Autonomous PC Assistant."""

    def __init__(self, preload: bool = False):
        t0 = time.perf_counter()
        self.router = JarvisRouter(preload=preload)
        init_ms = (time.perf_counter() - t0) * 1000
        print(f"🤖 [Jarvis] Master Controller online ({init_ms:.1f}ms)!\n")

    def process(self, query: str) -> Dict[str, Any]:
        """Processes any natural language query and dispatches to the optimal native engine."""
        t_start = time.perf_counter()

        # Step 1: System 1 Semantic Routing & Guardrail (<0.5ms)
        decision = self.router.evaluate(query)
        domain = decision.get("domain", "brain")
        action = decision.get("action", "think")
        params = decision.get("parameters", {})
        is_destructive = decision.get("is_destructive", 0.0)

        # Step 2: Safety Gate Check
        if is_destructive >= DESTRUCTIVE_THRESHOLD or domain == "blocked_safety":
            return {
                **decision,
                "status": "BLOCKED_SAFETY",
                "message": f"⚠️ Action blocked: High destructive risk score ({is_destructive:.2f}). Operation aborted for system safety.",
                "total_latency_ms": (time.perf_counter() - t_start) * 1000,
            }

        # Step 3: Deterministic Execution
        action_msg = ""
        action_start = time.perf_counter()

        try:
            # 1. Documents & Office
            if domain == "documents":
                if action == "create_excel":
                    action_msg = DocumentEngine.create_excel(title=params.get("title", "Sheet"))
                elif "word" in action:
                    action_msg = DocumentEngine.create_word(topic=params.get("topic", "Document"), content=params.get("content"))
                else:
                    action_msg = DocumentEngine.create_note(title=params.get("topic", "Note"), content=params.get("content"))

            # 2. Communication (WhatsApp & Email)
            elif domain == "comms":
                if action == "email":
                    action_msg = CommsEngine.compose_email(
                        recipient=params.get("recipient", ""),
                        subject=params.get("subject", "Message from Jarvis"),
                        body=params.get("body", "")
                    )
                else:
                    action_msg = CommsEngine.send_whatsapp(
                        recipient=params.get("recipient", "contact"),
                        message=params.get("message", "Hello")
                    )

            # 3. System Hardware & Diagnostics
            elif domain == "system_hardware":
                if action == "volume_up":
                    action_msg = SystemEngine.volume_up()
                elif action == "volume_down":
                    action_msg = SystemEngine.volume_down()
                elif action == "set_volume":
                    action_msg = SystemEngine.set_volume(level=params.get("level", 50))
                elif action == "mute":
                    action_msg = SystemEngine.mute()
                elif action == "play_pause":
                    action_msg = SystemEngine.play_pause()
                elif action == "next_track":
                    action_msg = SystemEngine.next_track()
                elif action == "prev_track":
                    action_msg = SystemEngine.prev_track()
                elif action == "screenshot":
                    action_msg = SystemEngine.take_screenshot()
                elif action == "lock_pc":
                    action_msg = SystemEngine.lock_pc()
                elif action == "system_metric":
                    action_msg = SystemEngine.get_system_metrics(params.get("metric_query", query)) or "System metric unavailable."
                elif action == "close_app":
                    action_msg = SystemEngine.close_app(params.get("target", ""))
                else:
                    action_msg = f"Executed {action}."

            # 4. App & Web
            elif domain == "app":
                action_msg = AppEngine.open_target(params.get("target", query))
            elif domain == "web":
                action_msg = AppEngine.open_web(params.get("query", query), search=True)

            # 5. File Operations
            elif domain == "files":
                if action == "create_folder":
                    action_msg = FileEngine.create_folder(params.get("name", "New Folder"))
                else:
                    action_msg = FileEngine.create_file(params.get("name", "file.txt"), content=params.get("content", ""))

            # 6. Conversational Brain & General AI
            else:
                action_msg = brain.think(query)

        except Exception as e:
            action_msg = f"Error executing {action}: {e}"

        exec_ms = (time.perf_counter() - action_start) * 1000
        total_ms = (time.perf_counter() - t_start) * 1000

        return {
            **decision,
            "status": "SUCCESS",
            "message": action_msg,
            "exec_ms": exec_ms,
            "total_latency_ms": total_ms,
        }
