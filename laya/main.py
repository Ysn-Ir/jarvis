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

from laya.config import FAST_PATH_BUDGET_MS
from laya.router import get_intent_router, ExecutionPath
from laya.fast_path import get_fast_path_executor
from laya.orchestrator import get_orchestrator
from laya.audio import get_tts_engine, get_stt_engine, AudioCapture


class LayaAssistant:
    def __init__(self):
        self.router = get_intent_router()
        self.fast_path = get_fast_path_executor()
        self.orchestrator = get_orchestrator()
        self.tts = get_tts_engine()
        self.conversation_history: List[Dict[str, str]] = []

    def handle_command(
        self,
        query: str,
        speak: bool = True,
        step_callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Process natural language query through the 3-tier execution architecture with multi-turn memory."""
        t_start = time.perf_counter()

        # Step 1: Sub-millisecond routing
        t_route_0 = time.perf_counter()
        decision = self.router.route(query)
        dt_router = (time.perf_counter() - t_route_0) * 1000

        result_text = ""

        # Step 2: Route Dispatch
        if decision.path == ExecutionPath.BLOCKED_SAFETY:
            result_text = "Action blocked by safety gate: Destructive operations are not permitted."
            if speak:
                self.tts.speak("Action blocked by safety gate.")

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

            if speak:
                self.tts.speak(result_text)

        elif decision.path == ExecutionPath.REASONING_PATH:
            result_text = self.orchestrator.execute(
                decision,
                history=self.conversation_history,
                step_callback=step_callback,
            )
            if speak:
                self.tts.speak(result_text)

        elif decision.path == ExecutionPath.CLARIFY:
            result_text = decision.clarification_prompt or "Could you clarify what you would like me to do?"
            if speak:
                self.tts.speak(result_text)

        else:
            result_text = f"Unhandled path: {decision.path}"

        dt_total = (time.perf_counter() - t_start) * 1000

        # Step 3: Record into multi-turn conversation memory
        self.conversation_history.append({"role": "user", "content": query})
        self.conversation_history.append({"role": "assistant", "content": result_text})
        if len(self.conversation_history) > 16:
            self.conversation_history = self.conversation_history[-16:]

        # Log timings
        status_flag = "⚡ [FAST-PATH]" if decision.path == ExecutionPath.FAST_PATH else "🧠 [REASONING]"
        print(f"\n{status_flag} {result_text}")
        print(f"⏱️  [Timing] Router={dt_router:.2f}ms | Total={dt_total:.2f}ms")

        return result_text

    def run_voice_loop(self):
        """Interactive voice loop with Push-to-Talk or Dynamic VAD."""
        print("\n" + "=" * 65)
        print("🎙️  LAYA VOICE INTERFACE ACTIVE")
        print("   - Press [ENTER] to speak")
        print("   - Type 'exit' to quit")
        print("=" * 65 + "\n")

        self.tts.speak("Laya is listening.")
        stt = get_stt_engine()
        capture = AudioCapture()

        while True:
            try:
                user_input = input("\n[Enter to Speak / or type query] > ").strip()
                if user_input.lower() in ["exit", "quit", "q"]:
                    print("Exiting Laya. Goodbye!")
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

    assistant = LayaAssistant()

    if args.hud:
        from laya.ui.hud import launch_hud
        print("🚀 Launching Laya Desktop HUD...")
        launch_hud(assistant_instance=assistant)
    elif args.voice:
        assistant.run_voice_loop()
    elif args.query:
        full_query = " ".join(args.query)
        assistant.handle_command(full_query, speak=False)
    else:
        # Launch HUD as the default modern experience
        from laya.ui.hud import launch_hud
        print("🚀 Launching Laya Desktop HUD (use --voice for CLI voice)...")
        launch_hud(assistant_instance=assistant)


if __name__ == "__main__":
    main()
