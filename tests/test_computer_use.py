"""
Unit tests for Computer Use (Mouse, Keyboard, Clipboard) and System Pro tools.
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


from laya.tools.computer_use import get_computer_use_tools
from laya.tools.system_pro import get_system_pro_tools


def test_computer_use():
    print("\n" + "=" * 65)
    print("🖱️ TESTING COMPUTER USE & GUI AUTOMATION TOOLS")
    print("=" * 65)

    cu = get_computer_use_tools()

    # 1. Clipboard Copy & Read
    print("\n--- 1. Testing Clipboard Automation ---")
    copy_res = cu.clipboard_copy("Laya State of the Art Autonomy")
    print(f"Copy: {copy_res}")
    read_res = cu.clipboard_read()
    print(f"Read: {read_res}")
    assert "Laya State of the Art Autonomy" in read_res

    # 2. Mouse Position
    print("\n--- 2. Testing Cursor Telemetry ---")
    pos_res = cu.get_mouse_position()
    print(f"Position: {pos_res}")
    assert "Cursor position" in pos_res and "Screen resolution" in pos_res

    # 3. Mouse Scroll
    print("\n--- 3. Testing Mouse Scroll ---")
    scroll_res = cu.mouse_scroll(clicks=2)
    print(f"Scroll: {scroll_res}")
    assert "Scrolled" in scroll_res


def test_system_pro():
    print("\n" + "=" * 65)
    print("⚡ TESTING SYSTEM PRO DIAGNOSTICS & MANAGEMENT")
    print("=" * 65)

    sp = get_system_pro_tools()

    # 1. GPU VRAM Telemetry
    print("\n--- 1. Testing Live GPU VRAM Telemetry ---")
    gpu_res = sp.get_gpu_vram_status()
    print(f"GPU: {gpu_res}")
    assert "GPU:" in gpu_res or "VRAM" in gpu_res

    # 2. Disk Space Analytics
    print("\n--- 2. Testing Disk Space Analytics ---")
    disk_res = sp.get_disk_space()
    print(f"Disk: {disk_res}")
    assert "Drive C:" in disk_res and "GB free" in disk_res

    # 3. Process Listing
    print("\n--- 3. Testing Process Resource Monitoring ---")
    proc_res = sp.list_processes(sort_by="memory", top_n=5)
    print(f"Processes:\n{proc_res}")
    assert "processes by memory" in proc_res.lower() and "PID" in proc_res

    print("\n" + "=" * 65)
    print("🎉 ALL COMPUTER USE & SYSTEM PRO TESTS PASSED 100%!")
    print("=" * 65)


if __name__ == "__main__":
    test_computer_use()
    test_system_pro()
