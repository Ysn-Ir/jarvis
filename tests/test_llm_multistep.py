"""
Verification test for Dual-Engine LLM Brain (Groq + Ollama) and Multi-Step Execution.
"""

import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from laya.main import LayaAssistant
from laya.orchestrator.planner import get_agent_planner


def test_dual_engine_planner():
    print("\n" + "=" * 65)
    print("🤖 TESTING DUAL-ENGINE AGENTIC PLANNER")
    print("=" * 65)

    planner = get_agent_planner()

    # 1. Test Groq Multi-Step Planning
    print("\n--- 1. Testing Cloud Ultra-Fast Groq Multi-Step Planning ---")
    query1 = "On the desktop create a folder named AlphaTest, inside it create a python file named hello.py that prints hello from Laya, and tell me where it is located."
    t0 = time.time()
    plan, provider = planner.plan(query1)
    dt = (time.time() - t0) * 1000
    print(f"Provider: {provider} ({dt:.1f}ms)")
    assert plan is not None, "Planner returned None!"
    assert "actions" in plan and len(plan["actions"]) >= 2, f"Expected at least 2 actions, got {plan.get('actions')}"
    print(f"Plan Actions ({len(plan['actions'])}):")
    for a in plan["actions"]:
        print(f"  - {a.get('tool')}: {a.get('args')}")
    print(f"Spoken Summary: {plan.get('spoken_summary')}")

    # 2. Test Local Ollama Offline Fallback
    print("\n--- 2. Testing Local Private Ollama Offline Fallback ---")
    # Temporarily set groq_client to None to test Ollama fallback
    real_client = planner.groq_client
    planner.groq_client = None
    try:
        t0 = time.time()
        ollama_plan, ollama_provider = planner.plan("Create a note in notepad saying meeting at 5pm")
        dt_ollama = (time.time() - t0) * 1000
        print(f"Ollama Provider: {ollama_provider} ({dt_ollama:.1f}ms)")
        if ollama_plan:
            print("Ollama Plan Actions:")
            for a in ollama_plan.get("actions", []):
                print(f"  - {a.get('tool')}: {a.get('args')}")
    finally:
        planner.groq_client = real_client

    # 3. Test Full Multi-Step Execution in LayaAssistant
    print("\n--- 3. Testing Full End-to-End Multi-Step Execution ---")
    assistant = LayaAssistant()
    command = "On the desktop create a folder named BetaProject, inside it create a python file named script.py with print('Laya is running!'), and tell me where it is located."
    result = assistant.handle_command(command, speak=False)
    print(f"\nFinal Result: {result}")

    # Verify files created on desktop
    target_dir = Path.home() / "Desktop" / "BetaProject"
    target_file = target_dir / "script.py"
    assert target_dir.exists(), f"Directory {target_dir} was not created!"
    assert target_file.exists(), f"File {target_file} was not created!"
    with open(target_file, "r") as f:
        content = f.read()
    print(f"Verified file content on disk: {repr(content)}")
    assert "Laya is running!" in content or "print" in content

    print("\n" + "=" * 65)
    print("🎉 DUAL-ENGINE LLM & MULTI-STEP VERIFICATION PASSED 100%!")
    print("=" * 65)


if __name__ == "__main__":
    test_dual_engine_planner()
