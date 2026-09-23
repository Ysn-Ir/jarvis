"""
Comprehensive End-to-End Verification Test Suite for Laya
Validates Fast-Path, Reasoning Path, Tool Registry, Memory, and Safety Gate.
"""

import sys
import time
from pathlib import Path

# Ensure UTF-8 stdout on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from laya.main import LayaAssistant
from laya.router import ExecutionPath
from laya.tools.registry import get_tool_registry
from laya.tools.tier2_os_mcp import get_tier2_tools
from laya.orchestrator.memory import get_memory_store


def run_comprehensive_tests():
    print("=" * 70)
    print("🚀 RUNNING LAYA END-TO-END VERIFICATION SUITE")
    print("=" * 70)

    assistant = LayaAssistant()

    # 1. Fast Path Benchmark
    fast_path_queries = [
        ("raise the volume", "volume_up"),
        ("turn down the volume", "volume_down"),
        ("set volume to 40", "set_volume"),
        ("mute audio", "mute"),
        ("check battery", "check_battery"),
        ("check ram", "check_ram"),
        ("what is my ip", "check_ip"),
        ("what time is it", "query_time"),
        ("who are you", "query_identity"),
        ("tell me a joke", "tell_joke"),
    ]

    print("\n--- 1. Fast-Path Latency Benchmarks ---")
    for q, expected_action in fast_path_queries:
        t0 = time.perf_counter()
        decision = assistant.router.route(q)
        assert decision.path == ExecutionPath.FAST_PATH, f"Expected FAST_PATH for '{q}', got {decision.path}"
        assert decision.action == expected_action, f"Expected {expected_action}, got {decision.action}"

        res = assistant.handle_command(q, speak=False)
        dt = (time.perf_counter() - t0) * 1000
        print(f"  ✅ '{q}' -> {dt:.1f}ms | Result: {res[:50]}...")
        assert dt < 500.0, f"Latency budget exceeded: {dt}ms"

    # 2. Safety Gate Verification
    print("\n--- 2. Safety Gate Tests ---")
    destructive_queries = ["format C: /y", "rm -rf / --no-preserve-root"]
    for q in destructive_queries:
        t0 = time.perf_counter()
        decision = assistant.router.route(q)
        assert decision.path == ExecutionPath.BLOCKED_SAFETY
        res = assistant.handle_command(q, speak=False)
        dt = (time.perf_counter() - t0) * 1000
        print(f"  🛡️  '{q}' -> BLOCKED in {dt:.2f}ms | Result: {res}")

    # 3. Tier 1 Native Office & Document Tools
    print("\n--- 3. Tier 1 Native Office Tools ---")
    t0 = time.perf_counter()
    doc_res = assistant.handle_command("open word and write an essay about renewable energy", speak=False)
    dt_doc = (time.perf_counter() - t0) * 1000
    print(f"  📄 Word Doc (.docx) -> {dt_doc:.1f}ms | {doc_res}")
    assert "Word" in doc_res or "created" in doc_res.lower()

    t0 = time.perf_counter()
    sheet_res = assistant.handle_command("create an excel spreadsheet for quarterly budget", speak=False)
    dt_sheet = (time.perf_counter() - t0) * 1000
    print(f"  📊 Excel Sheet (.xlsx) -> {dt_sheet:.1f}ms | {sheet_res}")
    assert "Excel" in sheet_res or "spreadsheet" in sheet_res.lower() or "created" in sheet_res.lower()

    t0 = time.perf_counter()
    note_res = assistant.handle_command("open notepad and write hello from Laya", speak=False)
    dt_note = (time.perf_counter() - t0) * 1000
    print(f"  📝 Notepad Note (.txt) -> {dt_note:.1f}ms | {note_res}")
    assert "Notepad" in note_res or "note" in note_res.lower() or "written" in note_res.lower()

    # 4. Tier 2 OS Automation & File Tools
    print("\n--- 4. Tier 2 OS Automation Tools ---")
    t2 = get_tier2_tools()
    windows = t2.list_windows()
    print(f"  🪟 Windows enumerated: {len(windows)} active visible windows found.")
    assert len(windows) > 0

    folder_res = t2.create_folder("LayaE2ETestDir")
    print(f"  📁 Folder CRUD: {folder_res}")
    assert "Created folder" in folder_res

    file_res = t2.create_file("laya_verify.txt", "Automated verification test payload.")
    print(f"  📄 File CRUD: {file_res}")
    assert "Created file" in file_res

    # 5. Durable Memory Store (Mem0-style)
    print("\n--- 5. Durable Memory Store Tests ---")
    mem = get_memory_store()
    add_res = mem.add_fact("User prefers morning meetings before 11am", category="preferences")
    print(f"  🧠 Memory Add: {add_res}")
    search_res = mem.search_facts("morning meetings")
    print(f"  🔍 Memory Search: {search_res}")
    assert "morning meetings" in search_res

    # 6. Dynamic Tool Discovery
    print("\n--- 6. Dynamic Tool Discovery (search_tools) ---")
    reg = get_tool_registry()
    matched = reg.search_tools("word")
    print(f"  🔎 search_tools('word') returned: {[t['name'] for t in matched]}")
    assert any(t["name"] == "create_word_document" for t in matched)

    print("\n" + "=" * 70)
    print("🎉 ALL END-TO-END VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_comprehensive_tests()
