"""
Jarvis Computer Use Agent (4.0)
See -> Think -> Act loop powered by Groq vision (llama-4-scout).
Executes arbitrary tasks on any visible application using pyautogui.
Protected by Laya destructive safety gate.
"""
import base64
import json
import os
import re
import sys
import time
import pyautogui
from io import BytesIO
from PIL import ImageGrab
from typing import Dict, Any, List, Optional, Tuple

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from jarvis_config import (
    BASE_DIR,
    GROQ_VISION_MODEL,
    COMPUTER_USE_MAX_STEPS,
    COMPUTER_USE_STEP_DELAY,
)

# Safety: pyautogui fail-safe (move mouse to top-left corner to abort)
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

MAX_STEPS = COMPUTER_USE_MAX_STEPS
STEP_DELAY = COMPUTER_USE_STEP_DELAY

VISION_SYSTEM_PROMPT = """You are Jarvis, an AI assistant controlling a Windows computer.
You receive a screenshot of the current screen and a user goal.
You must decide the SINGLE next action to take to progress toward that goal.

Respond ONLY with a valid JSON object. No explanation. No markdown. Only JSON.

Action types and their schemas:
- click: {"type": "click", "x": int, "y": int, "button": "left"|"right"|"middle"}
- double_click: {"type": "double_click", "x": int, "y": int}
- right_click: {"type": "right_click", "x": int, "y": int}
- type: {"type": "type", "text": "string to type", "enter": true|false}
- hotkey: {"type": "hotkey", "keys": ["ctrl", "c"]}
- scroll: {"type": "scroll", "x": int, "y": int, "clicks": int}
- open_app: {"type": "open_app", "app": "app name or command"}
- wait: {"type": "wait", "ms": int}
- done: {"type": "done", "result": "summary of what was accomplished"}
- failed: {"type": "failed", "reason": "why it cannot be done"}

Rules:
- Use EXACT pixel coordinates from the image dimensions provided (0,0 is top-left).
- For typing: first click on the target text field/window, then emit the type action.
- For hotkeys: use lowercase key names (ctrl, alt, shift, enter, tab, win, f4, etc.).
- If the required app is not visible or open, use open_app first.
- After completing the task, return done.
- If truly impossible (e.g. required software missing), return failed.
- NEVER delete files, format drives, or perform shutdown unless explicitly confirmed.
"""


def capture_screen():
    """
    Captures the current screen and returns (b64_jpeg, scale_x, scale_y, scaled_w, scaled_h).
    Handles high-DPI scaling so model coordinates map accurately to physical mouse clicks.
    """
    img = None

    # 1. mss — direct Win32 GDI, fastest and most compatible
    try:
        import mss
        from PIL import Image as _PILImage
        with mss.MSS() as sct:
            mon = sct.monitors[1]  # Primary monitor
            raw = sct.grab(mon)
            img = _PILImage.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
    except Exception:
        pass

    # 2. pyautogui fallback
    if img is None:
        try:
            img = pyautogui.screenshot()
        except Exception:
            pass

    # 3. ImageGrab fallback
    if img is None:
        try:
            img = ImageGrab.grab()
        except Exception:
            pass

    if img is None:
        raise RuntimeError(
            "Screen capture unavailable in this terminal session.\n"
            "Run jarvis_voice.py directly in a normal Windows terminal (not through an IDE subprocess) "
            "for Computer Use to work. The Computer Use agent requires an interactive desktop session."
        )

    orig_w, orig_h = img.size

    # Cap maximum dimension to 1920x1080 for speed, while maintaining aspect ratio
    max_w, max_h = 1920, 1080
    if orig_w > max_w or orig_h > max_h:
        ratio = min(max_w / orig_w, max_h / orig_h)
        scaled_w = int(orig_w * ratio)
        scaled_h = int(orig_h * ratio)
        img = img.resize((scaled_w, scaled_h))
    else:
        scaled_w, scaled_h = orig_w, orig_h

    scale_x = orig_w / scaled_w
    scale_y = orig_h / scaled_h

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=82)
    b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
    return b64_str, scale_x, scale_y, scaled_w, scaled_h


def parse_action_json(raw: str) -> Dict[str, Any]:
    """Cleans markdown fences and extracts valid JSON action object."""
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        # Fallback: scan for first { to matching or last }
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise


def call_vision_llm(goal: str, screenshot_b64: str, history: List[Dict], img_w: int, img_h: int) -> Dict[str, Any]:
    """Sends screenshot + goal to Groq vision model and gets back a structured action."""
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        return {"type": "failed", "reason": "No GROQ_API_KEY found. Set it in .env to enable Computer Use."}

    try:
        from groq import Groq
        client = Groq(api_key=groq_key)

        history_str = ""
        if history:
            history_str = "\n\nPrevious actions taken:\n" + "\n".join(
                f"Step {i+1}: {json.dumps(a)}" for i, a in enumerate(history)
            )

        messages = [
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"GOAL: {goal}\n"
                            f"SCREEN DIMENSIONS: {img_w}x{img_h} pixels (0,0 is top-left, {img_w-1},{img_h-1} is bottom-right).\n"
                            f"{history_str}\n\n"
                            "What is the next single action to take? Respond with ONLY a JSON object."
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{screenshot_b64}"
                        }
                    }
                ]
            }
        ]

        # Prioritized list of vision models
        models_to_try = [
            GROQ_VISION_MODEL,
            "qwen/qwen3.8-27b",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "llama-3.2-11b-vision-preview",
        ]
        # Remove duplicates while preserving order
        models_to_try = list(dict.fromkeys(models_to_try))

        last_err = None
        for model in models_to_try:
            try:
                completion = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=256,
                )
                raw = completion.choices[0].message.content.strip()
                return parse_action_json(raw)
            except Exception as e:
                last_err = e
                continue

        return {"type": "failed", "reason": f"All vision models failed. Last error: {last_err}"}

    except Exception as e:
        return {"type": "failed", "reason": str(e)}


def execute_action(action: Dict[str, Any], scale_x: float = 1.0, scale_y: float = 1.0) -> bool:
    """
    Executes a single pyautogui action with coordinate scaling. Returns True on success.
    """
    atype = action.get("type", "")
    screen_w, screen_h = pyautogui.size()

    def _get_coords(act: Dict[str, Any]) -> Tuple[int, int]:
        raw_x = act.get("x")
        raw_y = act.get("y")

        # Check if coordinates were passed as a list/tuple in x, coordinate, point, or coords
        for key in ("x", "coordinate", "point", "coords", "location"):
            val = act.get(key)
            if isinstance(val, (list, tuple)) and len(val) >= 2:
                raw_x, raw_y = val[0], val[1]
                break

        try:
            x_coord = int(float(raw_x) * scale_x)
        except Exception:
            x_coord = screen_w // 2

        try:
            y_coord = int(float(raw_y) * scale_y)
        except Exception:
            y_coord = screen_h // 2

        return max(0, min(x_coord, screen_w - 1)), max(0, min(y_coord, screen_h - 1))

    try:
        if atype == "click":
            x, y = _get_coords(action)
            btn = action.get("button", "left")
            pyautogui.click(x, y, button=btn, duration=0.15)
            print(f"   [ACT] Click({btn}) at ({x}, {y})")

        elif atype == "double_click":
            x, y = _get_coords(action)
            pyautogui.doubleClick(x, y, duration=0.15)
            print(f"   [ACT] Double-click at ({x}, {y})")

        elif atype == "right_click":
            x, y = _get_coords(action)
            pyautogui.rightClick(x, y)
            print(f"   [ACT] Right-click at ({x}, {y})")

        elif atype == "type":
            text = action.get("text", "")
            import pyperclip
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
            if action.get("enter", False) or action.get("press_enter", False):
                time.sleep(0.15)
                pyautogui.press("enter")
            print(f"   [ACT] Typed: {repr(text[:60])}")

        elif atype == "hotkey":
            keys = action.get("keys", [])
            if keys:
                pyautogui.hotkey(*[k.lower() for k in keys])
                print(f"   [ACT] Hotkey: {'+'.join(keys)}")

        elif atype == "scroll":
            x = int(action.get("x", screen_w // 2) * scale_x)
            y = int(action.get("y", screen_h // 2) * scale_y)
            clicks = action.get("clicks", 3)
            pyautogui.scroll(clicks, x=x, y=y)
            print(f"   [ACT] Scroll {clicks} at ({x}, {y})")

        elif atype == "open_app":
            app = action.get("app", "")
            try:
                from jarvis_app_finder import UniversalAppFinder
                finder = UniversalAppFinder()
                res = finder.open_target(app)
                print(f"   [ACT] Open app: {app} -> {res}")
            except Exception:
                import subprocess
                subprocess.Popen(f'start "" "{app}"', shell=True)
                print(f"   [ACT] Open app (cmd fallback): {app}")
            time.sleep(2.0)

        elif atype == "wait":
            ms = action.get("ms", 500)
            time.sleep(ms / 1000)
            print(f"   [ACT] Wait {ms}ms")

        return True

    except pyautogui.FailSafeException:
        print("   [ABORT] Fail-safe triggered (mouse at top-left corner). Stopping.")
        return False
    except Exception as e:
        print(f"   [ACT ERROR] {e}")
        return False


from jarvis_direct_bridges import check_direct_bridge, execute_direct_bridge
from jarvis_uia import (
    extract_ui_elements,
    match_element,
    execute_uia_interaction,
    get_foreground_window,
    bring_window_to_front,
)


class ComputerUseAgent:
    """
    Tri-Modal Hybrid Computer Use Agent:
    - Tier 1: Direct OS / Protocol Bridges (<10ms)
    - Tier 2: Deterministic Windows UI Automation (<50ms)
    - Tier 3: Groq Multimodal Vision Fallback (~3s)
    """

    def __init__(self, reflex=None):
        self.reflex = reflex
        self._destructive_keywords = [
            "delete", "remove", "format", "wipe", "uninstall",
            "rm -rf", "del /f", "shutdown", "drop table"
        ]

    def _is_action_safe(self, action: Dict) -> bool:
        """Quick safety check on action content."""
        text_to_check = json.dumps(action).lower()
        for kw in self._destructive_keywords:
            if kw in text_to_check:
                return False
        return True

    def run_task(self, goal: str, confirm_destructive: bool = False) -> str:
        """
        Runs the Tri-Modal Hybrid Computer Use loop.
        Fastest and most accurate execution tier selected automatically.
        """
        print(f"\n[ComputerUse] Starting task: {goal}")

        # Tier 1: Check Direct OS / Protocol Bridges (<10ms)
        direct_match = check_direct_bridge(goal)
        if direct_match:
            print(f"⚡ [Tier 1 Direct Bridge] Routing to: {direct_match['bridge']}")
            res = execute_direct_bridge(direct_match)
            print(f"✅ [Tier 1 Result] {res}")
            return res

        print(f"[ComputerUse] Max {MAX_STEPS} steps | Fail-safe: move mouse to TOP-LEFT corner to abort\n")

        history: List[Dict] = []

        for step in range(1, MAX_STEPS + 1):
            print(f"--- Step {step}/{MAX_STEPS} ---")

            # Tier 2: Try Deterministic Windows UI Automation (<50ms)
            fg = get_foreground_window()
            elements = extract_ui_elements(max_elements=30)
            if elements:
                matched_el = match_element(goal, elements, reflex=self.reflex)
                if matched_el and len(history) == 0:
                    # First interaction with a known UIA control
                    print(f"   ⚡ [Tier 2 UIA] Interacting with: '{matched_el['name']}' ({matched_el['type']})")
                    act_type = "type" if matched_el["type"] == "EditControl" and any(k in goal.lower() for k in ("write", "type", "enter", "search")) else "click"
                    text_val = goal if act_type == "type" else ""
                    if execute_uia_interaction(matched_el, action=act_type, text=text_val):
                        history.append({"tier": "uia", "target": matched_el["name"], "action": act_type})
                        time.sleep(STEP_DELAY)
                        # If simple one-shot UI interaction (e.g. click a button), complete
                        if act_type == "click" and any(w in goal.lower() for w in ("click", "press", "select")):
                            return f"Clicked '{matched_el['name']}' via Windows UI Automation."

            # Tier 3: Multimodal Vision Fallback (Qwen 27B)
            try:
                screenshot_b64, scale_x, scale_y, img_w, img_h = capture_screen()
            except RuntimeError as e:
                return str(e)

            action = call_vision_llm(goal, screenshot_b64, history, img_w, img_h)
            print(f"   [THINK Vision] {action}")

            atype = action.get("type", "")

            # Terminal states
            if atype == "done":
                result = action.get("result", "Task completed.")
                print(f"\n[ComputerUse] DONE: {result}")
                return result

            if atype == "failed":
                reason = action.get("reason", "Unknown failure.")
                print(f"\n[ComputerUse] FAILED: {reason}")
                return f"Could not complete task: {reason}"

            # Safety gate for potentially destructive text/hotkey actions
            if not self._is_action_safe(action) and not confirm_destructive:
                print(f"\n[ComputerUse] BLOCKED: Potentially destructive action: {action}")
                return f"Action blocked for safety: {json.dumps(action)}"

            # Act
            success = execute_action(action, scale_x=scale_x, scale_y=scale_y)
            if not success:
                return "Task aborted (fail-safe or execution error)."

            history.append(action)
            time.sleep(STEP_DELAY)

        return f"Reached maximum steps ({MAX_STEPS}) without completing task. Last actions: {history[-3:]}"


if __name__ == "__main__":
    agent = ComputerUseAgent()
    # Quick test: open notepad and type hello world
    result = agent.run_task("Open Notepad and type 'Hello World from Jarvis!'")
    print(f"\nResult: {result}")
