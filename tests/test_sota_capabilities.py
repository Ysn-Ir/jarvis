"""
Test Suite for SOTA Autonomous Desktop Agent Capabilities
Validates:
1. Open-Interpreter Universal Python & PowerShell Code Execution
2. Live Web Knowledge Retrieval & Web Scraping (DuckDuckGo & BeautifulSoup)
3. Microsoft UFO Windows UI Automation Control Layer
4. Deep Filesystem Pro (Read, List, Search)
5. Autonomous ReAct Agent Loop leveraging SOTA tools with Groq 120B
"""

import sys
from pathlib import Path

# Ensure UTF-8 stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure project root is importable
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from laya.tools.code_interpreter import get_code_interpreter
from laya.tools.web_intelligence import get_web_intelligence
from laya.tools.ufo_controller import get_ufo_controller
from laya.tools.filesystem_pro import get_filesystem_pro
from laya.orchestrator.engine import get_orchestrator
from laya.router.taxonomy import RouteDecision, ExecutionPath


def test_code_interpreter():
    print("\n--- 1. Testing Open-Interpreter Code Execution ---")
    ci = get_code_interpreter()

    # Python Execution
    py_code = """
import math
vals = [math.factorial(n) for n in range(1, 6)]
print(f'Factorials: {vals}')
"""
    py_res = ci.run_python(py_code)
    print(f"Python Output: {py_res.strip()}")
    assert "Factorials: [1, 2, 6, 24, 120]" in py_res, f"Unexpected Python output: {py_res}"

    # PowerShell Execution
    ps_res = ci.run_powershell("Get-Date -Format 'yyyy-MM-dd'")
    print(f"PowerShell Output: {ps_res.strip()}")
    assert len(ps_res.strip()) >= 8, f"Unexpected PowerShell output: {ps_res}"
    print("  ✅ Open-Interpreter Python & PowerShell Execution Verified!")


def test_web_intelligence():
    print("\n--- 2. Testing Live Web Intelligence ---")
    wi = get_web_intelligence()

    # Live Web Search
    search_res = wi.live_web_search("Python official release", max_results=2)
    print(f"Web Search Preview:\n{search_res[:300]}...")
    assert len(search_res) > 20, "Web search returned empty or short result"

    # Webpage Content Scraping
    page_res = wi.fetch_webpage_content("https://example.com")
    print(f"Webpage Fetch Preview:\n{page_res[:200]}...")
    assert "Example Domain" in page_res, f"Failed to extract title/content from example.com: {page_res}"
    print("  ✅ Live Web Search & Web Scraping Verified!")


def test_ufo_controller():
    print("\n--- 3. Testing Microsoft UFO Windows UI Automation ---")
    ufo = get_ufo_controller()

    # List open windows
    wins = ufo.list_open_windows()
    print(f"Open Windows Preview:\n{wins[:250]}...")
    assert "active visible" in wins.lower() or "application windows" in wins.lower()

    # Inspect active window controls
    controls = ufo.inspect_window_controls(max_depth=2)
    print(f"UIA Controls Preview:\n{controls[:250]}...")
    assert len(controls) > 10, "UIA inspection returned empty"
    print("  ✅ Microsoft UFO Windows UI Automation Layer Verified!")


def test_filesystem_pro():
    print("\n--- 4. Testing Deep Filesystem Pro ---")
    fs = get_filesystem_pro()

    # List directory
    ls_res = fs.list_directory("desktop")
    print(f"Directory Listing Preview:\n{ls_res[:250]}...")
    assert "Directory listing" in ls_res, f"Unexpected listing result: {ls_res}"

    # Create and read back a test file
    test_file = Path.home() / "Desktop" / "laya_sota_verify.txt"
    test_file.write_text("Laya SOTA Autonomous Agent Verification", encoding="utf-8")

    try:
        read_res = fs.read_file_content("desktop/laya_sota_verify.txt")
        print(f"Read File Content:\n{read_res.strip()}")
        assert "Laya SOTA Autonomous Agent Verification" in read_res

        # Search filesystem
        search_res = fs.search_filesystem("laya_sota_verify*", root_dir="desktop")
        print(f"Search Results:\n{search_res.strip()}")
        assert "laya_sota_verify.txt" in search_res
    finally:
        if test_file.exists():
            test_file.unlink()

    print("  ✅ Filesystem Pro (Read, List, Search) Verified!")


def test_react_agent_with_sota_tools():
    print("\n--- 5. Testing ReAct Perception-Action with SOTA Tools ---")
    orchestrator = get_orchestrator()

    # Query requiring Python code calculation
    decision = RouteDecision(
        path=ExecutionPath.REASONING_PATH,
        action="autonomous_task",
        params={"raw_query": "Calculate 17 to the power of 4 divided by 7 using python and tell me the answer."}
    )
    result = orchestrator.execute(decision)
    print(f"ReAct Agent Result: {result}")
    assert len(result) > 5, "ReAct agent returned empty response"
    print("  ✅ ReAct Agent End-to-End Execution with SOTA Tools Verified!")


if __name__ == "__main__":
    print("=" * 65)
    print("🚀 RUNNING SOTA AUTONOMOUS CAPABILITIES TEST SUITE")
    print("=" * 65)

    test_code_interpreter()
    test_web_intelligence()
    test_ufo_controller()
    test_filesystem_pro()
    test_react_agent_with_sota_tools()

    print("\n" + "=" * 65)
    print("🎉 ALL SOTA AUTONOMOUS CAPABILITIES PASSED 100%!")
    print("=" * 65)
