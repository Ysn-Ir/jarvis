"""
Laya Autonomous Desktop Assistant — Standalone Executable Builder
Compiles the high-speed Windows launcher (Laya.exe) with custom JARVIS icon and desktop integration.
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path

# Ensure UTF-8 stdout on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent


def build():
    print("\n" + "=" * 65)
    print("🔨 LAYA DESKTOP ASSISTANT — EXECUTABLE BUILDER")
    print("=" * 65)

    icon_path = ROOT_DIR / "assets" / "laya_icon.ico"
    launcher_file = ROOT_DIR / "launcher.py"

    # 1. Create clean launcher entrypoint
    launcher_content = '''"""
Laya Autonomous Assistant Standalone Launcher
"""
import sys
import os
import subprocess
from pathlib import Path

def main():
    root = Path(__file__).resolve().parent
    if not (root / "laya").exists():
        root = Path(sys.executable).resolve().parent

    python_exe = sys.executable
    if "python" not in Path(python_exe).stem.lower():
        python_exe = "python"

    cmd = [python_exe, "-m", "laya.main", "--hud"]
    subprocess.run(cmd, cwd=str(root))

if __name__ == "__main__":
    main()
'''
    launcher_file.write_text(launcher_content, encoding="utf-8")
    print("✓ Created launcher entrypoint: launcher.py")

    # 2. PyInstaller command
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name=Laya",
        f"--icon={str(icon_path)}" if icon_path.exists() else "",
        str(launcher_file)
    ]
    cmd = [c for c in cmd if c]

    print(f"✓ Executing PyInstaller build...")
    result = subprocess.run(cmd, cwd=str(ROOT_DIR))

    if result.returncode == 0:
        dist_exe = ROOT_DIR / "dist" / "Laya.exe"
        target_exe = ROOT_DIR / "Laya.exe"
        if dist_exe.exists():
            shutil.copy2(dist_exe, target_exe)
            print(f"\n🎉 BUILD SUCCESSFUL!")
            print(f"   Binary generated: {target_exe}")
            print(f"   Size: {target_exe.stat().st_size / (1024*1024):.2f} MB")
            print("=" * 65 + "\n")
        # Cleanup temporary build files
        build_dir = ROOT_DIR / "build"
        dist_dir = ROOT_DIR / "dist"
        spec_file = ROOT_DIR / "Laya.spec"
        if build_dir.exists():
            shutil.rmtree(build_dir, ignore_errors=True)
        if dist_dir.exists():
            shutil.rmtree(dist_dir, ignore_errors=True)
        if spec_file.exists():
            spec_file.unlink(missing_ok=True)
        if launcher_file.exists():
            launcher_file.unlink(missing_ok=True)
    else:
        print(f"\n❌ Build failed with return code {result.returncode}")


if __name__ == "__main__":
    build()
