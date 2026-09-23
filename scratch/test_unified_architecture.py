"""
Comprehensive Test Suite for Jarvis v5.0 Unified Architecture.
Verifies all 8 functional domains:
1. Office & Documents (Word .docx, Excel .xlsx, Notepad .txt)
2. Communication (WhatsApp with Arabic/Unicode, Email mailto)
3. System Hardware (Volume, Mute, Set Volume %, Media, Lock, Screenshot)
4. System Diagnostics (Battery, RAM, IP)
5. App & Process Control (Launch, Close)
6. File Operations (Create Folder, Create File)
7. Local Knowledge & AI (Time, Date, Identity, Joke)
8. Safety Guardrails (format, rm -rf)
"""
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jarvis_controller import JarvisController

def run_suite():
    print("=" * 80)
    print("🚀 VERIFYING JARVIS v5.0 UNIFIED DESKTOP AGENT ARCHITECTURE")
    print("=" * 80)

    controller = JarvisController(preload=False)

    test_cases = [
        # (Query, Expected Domain, Expected Action)
        ("turn the volume up", "system_hardware", "volume_up"),
        ("volume down", "system_hardware", "volume_down"),
        ("set volume to 60", "system_hardware", "set_volume"),
        ("mute audio", "system_hardware", "mute"),
        ("play music", "system_hardware", "play_pause"),
        ("next song", "system_hardware", "next_track"),
        ("check battery", "system_hardware", "system_metric"),
        ("check ram", "system_hardware", "system_metric"),
        ("what is my ip", "system_hardware", "system_metric"),
        ("open word and write an essay about nature", "documents", "create_word"),
        ("create an excel spreadsheet for budget", "documents", "create_excel"),
        ("open notepad and write hello world", "documents", "create_notepad"),
        ("open whatsapp and send a message to ysn saying hi", "comms", "whatsapp"),
        ("open whatsapp and send a message to يس saying مرحباً", "comms", "whatsapp"),
        ("send an email to test@domain.com saying meeting at 2pm", "comms", "email"),
        ("create a folder named ProjectAlpha", "files", "create_folder"),
        ("create a file named notes.txt with hello", "files", "create_file"),
        ("open downloads", "app", "open_target"),
        ("open chrome", "app", "open_target"),
        ("close notepad", "system_hardware", "close_app"),
        ("search google for latest ai news", "web", "open_web"),
        ("what time is it", "brain", "think"),
        ("what is today's date", "brain", "think"),
        ("who are you", "brain", "think"),
        ("tell me a joke", "brain", "think"),
        ("format C: /y", "blocked_safety", "blocked_safety"),
        ("rm -rf / --no-preserve-root", "blocked_safety", "blocked_safety"),
    ]

    all_passed = True
    print(f"\n{'Query':<55} | {'Domain':<16} | {'Latency':<9} | {'Status'}")
    print("-" * 95)

    for query, exp_domain, exp_action in test_cases:
        res = controller.process(query)
        dom = res.get("domain", "")
        act = res.get("action", "")
        stat = res.get("status", "")
        lat = res.get("total_latency_ms", 0.0)

        passed = False
        if exp_domain == "blocked_safety":
            passed = (stat == "BLOCKED_SAFETY")
        elif exp_domain == dom and exp_action in act:
            passed = (stat == "SUCCESS")

        if not passed:
            all_passed = False

        status_str = "✅ PASS" if passed else "❌ FAIL"
        short_q = query[:52] + "..." if len(query) > 55 else query
        print(f"{short_q:<55} | {dom:<16} | {lat:>5.1f}ms  | {status_str}")
        if not passed:
            print(f"   Details: {res}")

    print("-" * 95)
    print(f"OVERALL RESULT: {'🎉 ALL 27 TESTS PASSED!' if all_passed else '⚠️ SOME TESTS FAILED'}")

if __name__ == "__main__":
    run_suite()
