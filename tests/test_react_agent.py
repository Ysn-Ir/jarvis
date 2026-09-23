"""
Verification test for Autonomous ReAct Agent Loop and Native Function Calling.
"""

import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from laya.main import LayaAssistant
from laya.orchestrator.react_agent import get_react_agent
from laya.orchestrator.engine import get_orchestrator


def test_react_loop():
    print("\n" + "=" * 65)
    print("🤖 TESTING AUTONOMOUS REACT AGENT LOOP")
    print("=" * 65)

    assistant = LayaAssistant()

    # 1. Test Telemetry / Diagnostics via ReAct
    print("\n--- 1. Testing GPU VRAM & System Query ---")
    res1 = assistant.handle_command("Check my GPU VRAM status and utilization", speak=False)
    print(f"Result: {res1}")
    assert "RTX 4050" in res1 or "GPU" in res1, f"Unexpected GPU result: {res1}"

    # 2. Test Multi-Step Chaining: Desktop folder + file with code + location
    print("\n--- 2. Testing Multi-Step ReAct: Folder -> Python File -> Location ---")
    query2 = "On the desktop create a folder named ReActProject, inside it create a python file named hello.py that prints 'Autonomous Laya', and tell me where it is located."
    res2 = assistant.handle_command(query2, speak=False)
    print(f"Result: {res2}")

    # Verify physical file existence
    target_file = Path.home() / "Desktop" / "ReActProject" / "hello.py"
    assert target_file.exists(), f"File {target_file} was not created on disk!"
    with open(target_file, "r") as f:
        file_content = f.read()
    print(f"File verified on disk at: {target_file}")
    print(f"File contents: {repr(file_content)}")
    assert "Autonomous Laya" in file_content or "print" in file_content

    # 3. Test Process Management
    print("\n--- 3. Testing Process Management ---")
    res3 = assistant.handle_command("List the top processes by memory usage", speak=False)
    print(f"Result: {res3}")
    assert "processes by memory" in res3.lower() or "pid" in res3.lower(), f"Unexpected process result: {res3}"

    print("\n" + "=" * 65)
    print("🎉 ALL AUTONOMOUS REACT AGENT TESTS PASSED 100%!")
    print("=" * 65)


if __name__ == "__main__":
    test_react_loop()
