"""
Laya — JARVIS-Style Voice Desktop Assistant
Master Entry Point (Voice, CLI, and One-Shot Execution) with Multi-Turn Memory
"""

import sys
import time
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Callable

# Ensure UTF-8 stdout on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure package is resolvable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import socket
from laya.config import FAST_PATH_BUDGET_MS
from laya.router import get_intent_router, ExecutionPath
from laya.fast_path import get_fast_path_executor
from laya.orchestrator import get_orchestrator
from laya.audio import get_tts_engine, get_stt_engine, AudioCapture

_single_instance_socket = None


def acquire_single_instance_lock(port: int = 49876) -> bool:
    """Ensure only one instance of Laya can run simultaneously across the system."""
    global _single_instance_socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        s.bind(("127.0.0.1", port))
        s.listen(1)
        _single_instance_socket = s
        return True
    except (OSError, socket.error):
        return False


class LayaAssistant:
    def __init__(self):
        self.router = get_intent_router()
        self.fast_path = get_fast_path_executor()
        self.orchestrator = get_orchestrator()
        self.tts = get_tts_engine()
        self.conversation_history: List[Dict[str, str]] = []

        # Warm up neural decision engine in background at startup
        try:
            from laya.router.laya_engine import get_laya_engine
            get_laya_engine()
        except Exception:
            pass

    def handle_command(
        self,
        query: str,
        speak: bool = True,
        step_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Process natural language query through the 3-tier execution architecture with multi-turn memory."""
        t_start = time.perf_counter()

        # CRITICAL: Clear any stale interrupt flag from a previous command before starting
        from laya.tools.interrupt_manager import reset_interrupt, is_interrupt_requested
        reset_interrupt()

        t_route_0 = time.perf_counter()
        decision = self.router.route(query)
        dt_router = (time.perf_counter() - t_route_0) * 1000

        result_text = ""

        # Step 2: Route Dispatch
        if decision.path == ExecutionPath.BLOCKED_SAFETY:
            result_text = "Action blocked by safety gate: Destructive operations are not permitted."

        elif decision.path == ExecutionPath.FAST_PATH:
            action = decision.action
            params = decision.params

            handler = getattr(self.fast_path, action, None)
            if handler:
                try:
                    result_text = handler(**params)
                except Exception as e:
                    result_text = f"Fast path execution error: {e}"
            else:
                result_text = f"Fast-path action '{action}' executed."

        elif decision.path == ExecutionPath.REASONING_PATH:
            result_text = self.orchestrator.execute(
                decision,
                history=self.conversation_history,
                step_callback=step_callback,
            )

        elif decision.path == ExecutionPath.CLARIFY:
            result_text = decision.clarification_prompt or "Could you clarify what you would like me to do?"

        else:
            result_text = f"Unhandled path: {decision.path}"

        dt_compute = (time.perf_counter() - t_start) * 1000

        # Contextual meme vocal reaction from Jarvis
        from laya.ui.meme_engine import get_meme_engine
        from laya.audio.meme_audio import get_meme_voice_quip
        reaction = get_meme_engine().classify_reaction(query, result_text, is_error=(decision.path == ExecutionPath.BLOCKED_SAFETY))
        spoken_text = result_text
        if reaction and reaction not in ["foid_alert", "chud_destruct", "lockdown"]:
            quip = get_meme_voice_quip(reaction)
            if quip and not any(w in result_text.lower() for w in [reaction, "chudjak", "monkas", "feels bad", "feels good"]):
                spoken_text = f"{quip}{result_text}"

        # Log timings immediately once result is computed
        status_flag = "⚡ [FAST-PATH]" if decision.path == ExecutionPath.FAST_PATH else "🧠 [REASONING]"
        print(f"\n{status_flag} {result_text}")
        print(f"⏱️  [Timing] Router={dt_router:.2f}ms | Compute={dt_compute:.2f}ms")

        from laya.tools.interrupt_manager import is_interrupt_requested
        if is_interrupt_requested():
            # Don't speak — TTS already stopped by interrupt handler
            return "Stopped."

        # Step 3: Record into multi-turn conversation memory
        self.conversation_history.append({"role": "user", "content": query})
        self.conversation_history.append({"role": "assistant", "content": result_text})
        if len(self.conversation_history) > 16:
            self.conversation_history = self.conversation_history[-16:]

        if speak:
            self.tts.speak(spoken_text)

        return result_text

    def run_voice_loop(self):
        """Interactive voice loop with Push-to-Talk or Dynamic VAD."""
        print("\n" + "=" * 65)
        print("🎙️  VOICE INTERFACE ACTIVE")
        print("   - Press [ENTER] to speak")
        print("   - Type 'exit' to quit")
        print("=" * 65 + "\n")

        self.tts.speak("Assistant is online and listening.")
        stt = get_stt_engine()
        capture = AudioCapture()

        while True:
            try:
                user_input = input("\n[Enter to Speak / or type query] > ").strip()
                if user_input.lower() in ["exit", "quit", "q"]:
                    print("Exiting assistant. Goodbye!")
                    break

                if user_input:
                    # Direct text command
                    self.handle_command(user_input, speak=True)
                else:
                    # Voice recording: stop any playing speech so mic doesn't record assistant audio
                    self.tts.stop()
                    print("🎤 Listening... (Speak now)")
                    audio_data = capture.record_until_silence(max_duration_sec=8.0)
                    if audio_data is None or len(audio_data) == 0:
                        print("⚠️  No speech detected.")
                        continue

                    print("🔄 Transcribing...")
                    t0 = time.time()
                    transcript = stt.transcribe(audio_data)
                    dt_stt = (time.time() - t0) * 1000

                    if not transcript:
                        print("⚠️  Could not recognize speech.")
                        continue

                    print(f"🗣️  You: \"{transcript}\" (STT: {dt_stt:.1f}ms)")
                    self.handle_command(transcript, speak=True)

            except KeyboardInterrupt:
                print("\nVoice session ended.")
                break
            except Exception as e:
                print(f"[Voice Error] {e}")


def main():
    parser = argparse.ArgumentParser(description="Laya Autonomous Desktop Assistant")
    parser.add_argument("query", nargs="*", help="Optional command to execute directly")
    parser.add_argument("--hud", action="store_true", help="Launch transparent desktop HUD interface with wake word")
    parser.add_argument("--voice", "-v", action="store_true", help="Launch interactive voice mode in console")
    args = parser.parse_args()

    # Enforce single instance for long-running voice & HUD listeners
    if args.hud or args.voice or not args.query:
        if not acquire_single_instance_lock():
            print("\n" + "=" * 65)
            print("⚠️  [Laya] Another instance of Laya is already running.")
            print("   Only one instance can run at a time to prevent audio device")
            print("   conflicts and duplicate execution.")
            print("   Please close the existing HUD/terminal window before launching a new one.")
            print("=" * 65 + "\n")
            sys.exit(0)

    if args.hud or not (args.voice or args.query):
        # FAST PATH: Launch HUD desktop app immediately without blocking
        from laya.ui.hud import launch_hud
        launch_hud()
        return

    assistant = LayaAssistant()

    if args.voice:
        assistant.run_voice_loop()
    elif args.query:
        full_query = " ".join(args.query)
        assistant.handle_command(full_query, speak=False)


if __name__ == "__main__":
    main()
