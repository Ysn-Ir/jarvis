"""
Interactive CLI for Jarvis PC Controller.
Test commands live with millisecond latency telemetry.
"""
import sys

# Ensure UTF-8 output on Windows terminal
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from jarvis_controller import JarvisController


def print_banner():
    print("""
========================================================================
     ⚡ JARVIS SYSTEM 1 DESKTOP CONTROLLER (POWERED BY LAYA) ⚡
========================================================================
 Commands you can try:
   [Media]   "turn the volume up", "pause the music", "skip track", "mute"
   [Apps]    "open notepad", "launch calculator", "open chrome", "open vscode"
   [Web]     "search google for pasta recipes", "open youtube", "open github"
   [System]  "take a screenshot", "lock workstation"
   [Safety]  "delete all files on C drive" (tests guardrail)
   [AI]      "explain quantum computing" (tests System 2)
   [Voice]   Type 'voice' or run 'python jarvis_voice.py' for microphone control!
   [Special] Type 'test' for automated benchmark, 'exit' to quit.
========================================================================
""")


def run_benchmark(controller: JarvisController):
    print("\n--- RUNNING BENCHMARK SUITE ---")
    test_cases = [
        "turn volume up",
        "pause the music",
        "open notepad",
        "open calculator",
        "search google for top python libraries",
        "open youtube",
        "take a screenshot",
        "lock the screen",
        "format the hard drive and wipe data",
        "explain how backpropagation works in neural networks",
    ]

    for query in test_cases:
        print(f"\n🗣️  Query: \"{query}\"")
        res = controller.process(query, simulate_system_lock=True)
        print(f"   Action:    {res['action']} -> Target: {res['target']} (Conf: {res.get('action_confidence', 0.0):.2f})")
        print(f"   Status:    {res['status']}")
        print(f"   Outcome:   {res['message']}")
        print(f"   ⏱️  Laya:   {res['latency_ms']:.1f}ms  |  Total: {res['total_latency_ms']:.1f}ms")

    print("\n✅ Benchmark completed!\n")


def main():
    if "--voice" in sys.argv:
        from jarvis_voice import JarvisVoice
        assistant = JarvisVoice()
        assistant.run_push_to_talk()
        return

    print_banner()
    controller = JarvisController(preload=False)

    while True:
        try:
            user_input = input("\nJarvis > ").strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                print("👋 Jarvis shutting down. Have a great day!")
                break

            if user_input.lower() in ("test", "benchmark"):
                run_benchmark(controller)
                continue

            if user_input.lower() == "voice":
                from jarvis_voice import JarvisVoice
                assistant = JarvisVoice(controller=controller)
                assistant.run_push_to_talk()
                continue

            # Process command
            res = controller.process(user_input, simulate_system_lock=False)

            # Display results & telemetry
            status_emoji = "✅" if res["status"] == "SUCCESS" else "⚠️"
            print(f"\n{status_emoji} [{res['status']}] {res['message']}")
            print(f"   [Telemetry] Laya Decision: {res['latency_ms']:.1f}ms | Total Latency: {res['total_latency_ms']:.1f}ms")
            print(f"   [Routing]   Action: {res['action']} | Target: {res['target']} | Destructive Risk: {res.get('is_destructive', 0.0):.2f}")

        except (KeyboardInterrupt, EOFError):
            print("\n👋 Jarvis shutting down.")
            break


if __name__ == "__main__":
    main()
