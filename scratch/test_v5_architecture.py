"""
End-to-End Verification Test for Jarvis v5.0 Deterministic OS Architecture.
Tests intent extraction, safety gate, native drivers, and latency.
"""
import sys
import time

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jarvis_controller import JarvisController
from jarvis_drivers import DocumentDriver, WhatsAppDriver, SystemDriver

def run_tests():
    print("=" * 70)
    print("🚀 BENCHMARKING JARVIS v5.0 DETERMINISTIC OS AGENT")
    print("=" * 70)

    t0 = time.perf_counter()
    controller = JarvisController(preload=False)
    init_time = (time.perf_counter() - t0) * 1000
    print(f"Controller initialized in {init_time:.2f}ms\n")

    test_cases = [
        # 1. System Reflexes
        ("turn the volume up", "volume_up"),
        ("mute audio", "mute"),
        ("check battery", "system_metric"),
        ("what is my ip", "system_metric"),
        ("check ram", "system_metric"),

        # 2. Document Creation (Word & Notepad)
        ("Jarvis, open word and write an essay about nature", "create_word"),
        ("open notebook and write hello world from jarvis", "create_notepad"),

        # 3. WhatsApp Messaging (English & Arabic)
        ("open whatsapp and send a message to ysn saying hi jarvis is online", "whatsapp"),
        ("open whatsapp and send a message to يس saying سلام عليكم", "whatsapp"),

        # 4. App Launching & Web
        ("open calculator", "open_app"),
        ("search google for latest ai news", "web_search"),

        # 5. Safety Guardrail
        ("format C: /y", "BLOCKED_SAFETY"),
        ("rm -rf / --no-preserve-root", "BLOCKED_SAFETY"),
    ]

    all_passed = True
    print(f"{'Query':<55} | {'Domain':<15} | {'Action':<15} | {'Latency':<10} | {'Status'}")
    print("-" * 115)

    for query, expected_action in test_cases:
        res = controller.process(query)
        action = res.get("action", "")
        status = res.get("status", "")
        domain = res.get("domain", "")
        lat = res.get("total_latency_ms", 0.0)

        passed = False
        if expected_action == "BLOCKED_SAFETY":
            passed = (status == "BLOCKED_SAFETY")
        elif expected_action in action or expected_action in domain:
            passed = (status == "SUCCESS")

        pass_label = "✅ PASS" if passed else "❌ FAIL"
        if not passed:
            all_passed = False

        short_q = query[:52] + "..." if len(query) > 55 else query
        print(f"{short_q:<55} | {domain:<15} | {action:<15} | {lat:>6.1f}ms   | {pass_label}")
        if not passed:
            print(f"   Details: {res}")

    print("-" * 115)
    print(f"Overall Result: {'🎉 ALL TESTS PASSED' if all_passed else '⚠️ SOME TESTS FAILED'}")

if __name__ == "__main__":
    run_tests()
