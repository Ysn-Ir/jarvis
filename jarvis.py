"""
Jarvis Autonomous PC Assistant (v5.0 Unified Architecture)
Master CLI and Voice Interface.
Usage:
  python jarvis.py                  -> Interactive terminal controller
  python jarvis.py --voice          -> Push-to-talk voice controller
  python jarvis.py "<command>"      -> One-shot command execution
"""
import sys
import time

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from jarvis_controller import JarvisController


def main():
    args = sys.argv[1:]

    # Mode 1: Push-to-Talk Voice Interface
    if "--voice" in args or "-v" in args:
        from jarvis_voice import JarvisVoice
        voice = JarvisVoice()
        voice.run_push_to_talk()
        return

    controller = JarvisController()

    # Mode 2: One-shot Command Execution
    if args:
        command = " ".join([a for a in args if not a.startswith("-")])
        if command:
            res = controller.process(command)
            print(f"\n[Result]: {res['message']}")
            print(f"[Timing]: Router={res.get('routing_ms', 0):.1f}ms | Total={res.get('total_latency_ms', 0):.1f}ms")
            return

    # Mode 3: Interactive CLI
    print("=" * 65)
    print("🤖 JARVIS 5.0 UNIFIED DESKTOP AGENT (CLI INTERACTIVE)")
    print("=" * 65)
    print("Commands you can try:")
    print("  • 'Open Word and write an essay about nature'")
    print("  • 'Create an Excel spreadsheet for budget'")
    print("  • 'Open WhatsApp and send a message to ysn saying hello'")
    print("  • 'Turn the volume up / down / mute'")
    print("  • 'Check battery / RAM / IP address'")
    print("  • 'Open Downloads / Chrome / Spotify'")
    print("  • Type 'voice' to switch to Voice Mode, or 'exit' to quit.")
    print("=" * 65)

    while True:
        try:
            cmd = input("\nJarvis > ").strip()
            if not cmd:
                continue
            if cmd.lower() in ("exit", "quit", "q"):
                print("Jarvis shutting down. Goodbye!")
                break
            if cmd.lower() in ("voice", "mic"):
                from jarvis_voice import JarvisVoice
                voice = JarvisVoice(controller=controller)
                voice.run_push_to_talk()
                break

            res = controller.process(cmd)
            print(f"[{res['status']}] {res['message']}")
            routing_ms = res.get('routing_ms', res.get('latency_ms', 0))
            total_ms = res.get('total_latency_ms', 0)
            print(f"⚡ {routing_ms:.1f}ms router | {total_ms:.1f}ms total")

        except (KeyboardInterrupt, EOFError):
            print("\nExiting Jarvis.")
            break


if __name__ == "__main__":
    main()
