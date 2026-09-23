"""
Jarvis Core Engine (v5.0 Unified Architecture)
The deterministic native OS execution arsenal.
Provides sub-second, error-free execution across all computer domains.
"""
import ctypes
import datetime
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import pyautogui
import pyperclip

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from jarvis_config import DOCUMENTS_DIR, SCREENSHOT_DIR, SPECIAL_FOLDERS, WEB_SHORTCUTS
from jarvis_app_finder import UniversalAppFinder


# ============================================================================
# 1. DOCUMENT & OFFICE ENGINE
# ============================================================================
class DocumentEngine:
    """Creates formatted Word (.docx), Excel (.xlsx), and text documents natively."""

    @staticmethod
    def _synthesize_essay(topic: str) -> Dict[str, Any]:
        clean = re.sub(r'^(?:an?\s+)?(?:essay|report|note|doc|article)\s+(?:about|on)\s+', '', topic.strip(), flags=re.I)
        title = clean.title() or "Essay"
        t_low = clean.lower()

        if "nature" in t_low:
            return {
                "title": "An Exploration of Nature: Balance, Beauty, and Vitality",
                "paragraphs": [
                    "Nature represents the primordial foundation of all life on Earth. From ancient mountain ranges to undisturbed forest ecosystems, the natural world maintains a delicate equilibrium that sustains every organism.",
                    "In our modern technological era, the connection between humanity and the environment has never been more crucial. Scientific research consistently demonstrates that immersion in natural surroundings reduces stress, enhances cognitive function, and fosters psychological resilience.",
                    "Preserving biodiversity and protecting our natural heritage is an urgent existential imperative. Sustainable practices, environmental stewardship, and conservation ensure that future generations inherit a flourishing and resilient planet."
                ]
            }
        elif "quantum" in t_low:
            return {
                "title": "Understanding Quantum Computing: Fundamentals and Horizons",
                "paragraphs": [
                    "Quantum computing harnesses the principles of quantum mechanics, such as superposition and entanglement, to perform complex computational calculations exponentially faster than classical silicon systems.",
                    "Key applications include cryptographic resilience, molecular modeling for drug development, and large-scale logistical optimization.",
                    "As fault-tolerant quantum hardware advances, hybrid quantum-classical algorithms will drive unprecedented breakthroughs across science and industry."
                ]
            }
        else:
            return {
                "title": f"Document: {title}",
                "paragraphs": [
                    f"This document presents an overview and analysis concerning {clean}.",
                    f"Key considerations regarding {clean} emphasize structured investigation, strategic planning, and practical implementation to achieve optimal results.",
                    f"In summary, continuous examination of {clean} delivers actionable insights and advances productive understanding across related domains."
                ]
            }

    @classmethod
    def create_word(cls, topic: str, content: Optional[str] = None, open_doc: bool = True) -> str:
        """Generates a styled .docx file via python-docx and launches Microsoft Word."""
        try:
            import docx
            from docx.shared import Inches, Pt
            from docx.enum.text import WD_ALIGN_PARAGRAPH

            doc = docx.Document()
            for s in doc.sections:
                s.top_margin = Inches(1)
                s.bottom_margin = Inches(1)
                s.left_margin = Inches(1)
                s.right_margin = Inches(1)

            if content and len(content.split()) > 15:
                p_head = doc.add_heading(topic.title() or "Document", level=1)
                p_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
                doc.add_paragraph()
                for chunk in content.split("\n\n"):
                    if chunk.strip():
                        p = doc.add_paragraph(chunk.strip())
                        p.paragraph_format.line_spacing = 1.15
                        p.paragraph_format.space_after = Pt(8)
            else:
                synth = cls._synthesize_essay(topic)
                p_head = doc.add_heading(synth["title"], level=1)
                p_head.alignment = WD_ALIGN_PARAGRAPH.CENTER
                doc.add_paragraph()
                for para in synth["paragraphs"]:
                    p = doc.add_paragraph(para)
                    p.paragraph_format.line_spacing = 1.2
                    p.paragraph_format.space_after = Pt(10)

            slug = re.sub(r'[^a-zA-Z0-9_\-]', '_', topic[:25]).strip('_') or "Document"
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{slug}_{ts}.docx"
            file_path = DOCUMENTS_DIR / filename
            doc.save(str(file_path))

            if open_doc:
                os.startfile(str(file_path))
            return f"Created Microsoft Word document '{filename}' in Documents and opened it."
        except Exception as e:
            return cls.create_note(topic, content=content)

    @classmethod
    def create_excel(cls, title: str, rows: Optional[List[List[Any]]] = None) -> str:
        """Generates a styled .xlsx spreadsheet via openpyxl and launches Excel."""
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = title[:30] if title else "Sheet1"

            # Header
            header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
            header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

            data = rows or [
                ["Item / Category", "Description", "Status", "Date"],
                ["Task 1", "Initial project review", "Completed", datetime.date.today().strftime("%Y-%m-%d")],
                ["Task 2", "Architecture optimization", "In Progress", datetime.date.today().strftime("%Y-%m-%d")],
                ["Task 3", "System verification", "Pending", datetime.date.today().strftime("%Y-%m-%d")],
            ]

            for r_idx, row in enumerate(data, 1):
                for c_idx, val in enumerate(row, 1):
                    cell = ws.cell(row=r_idx, column=c_idx, value=val)
                    if r_idx == 1:
                        cell.fill = header_fill
                        cell.font = header_font
                        cell.alignment = Alignment(horizontal="center")

            slug = re.sub(r'[^a-zA-Z0-9_\-]', '_', title[:25]).strip('_') or "Sheet"
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{slug}_{ts}.xlsx"
            file_path = DOCUMENTS_DIR / filename
            wb.save(str(file_path))
            os.startfile(str(file_path))
            return f"Created Excel spreadsheet '{filename}' and opened in Excel."
        except Exception as e:
            return f"Error creating Excel spreadsheet: {e}"

    @classmethod
    def create_note(cls, title: str, content: Optional[str] = None) -> str:
        """Generates a text note and launches Notepad."""
        try:
            if not content:
                synth = cls._synthesize_essay(title)
                body = f"{synth['title']}\n" + "=" * len(synth['title']) + "\n\n" + "\n\n".join(synth['paragraphs'])
            else:
                body = content.strip()

            slug = re.sub(r'[^a-zA-Z0-9_\-]', '_', title[:25]).strip('_') or "Note"
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{slug}_{ts}.txt"
            file_path = DOCUMENTS_DIR / filename

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(body)

            subprocess.Popen(f'notepad.exe "{file_path}"', shell=True)
            return f"Created note '{filename}' and opened in Notepad."
        except Exception as e:
            return f"Error creating note: {e}"


# ============================================================================
# 2. COMMUNICATION & MESSAGING ENGINE
# ============================================================================
class CommsEngine:
    """Fast WhatsApp and Email automation with full Unicode and Arabic support."""

    @classmethod
    def send_whatsapp(cls, recipient: str, message: str) -> str:
        rec_clean = recipient.strip().strip("'\"")
        msg_clean = message.strip().strip("'\"")

        # 1. Direct phone number protocol
        if re.match(r'^\+?[0-9\s\-]{7,20}$', rec_clean):
            num = re.sub(r'[^0-9]', '', rec_clean)
            import urllib.parse
            url = f"whatsapp://send?phone={num}&text={urllib.parse.quote(msg_clean)}"
            try:
                os.startfile(url)
                time.sleep(2.0)
                pyautogui.press("enter")
                return f"Sent WhatsApp message to {rec_clean}."
            except Exception:
                pass

        # 2. WhatsApp Desktop automation via clipboard
        try:
            finder = UniversalAppFinder()
            finder.open_target("whatsapp")
            time.sleep(1.2)

            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.3)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("backspace")
            time.sleep(0.1)

            # Paste contact name (supports Arabic like 'يس' cleanly)
            pyperclip.copy(rec_clean)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.8)
            pyautogui.press("enter")
            time.sleep(0.5)

            # Paste and send message
            pyperclip.copy(msg_clean)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.2)
            pyautogui.press("enter")
            return f"Sent WhatsApp message to '{rec_clean}'."
        except Exception as e:
            return f"Could not send WhatsApp message: {e}"

    @classmethod
    def compose_email(cls, recipient: str, subject: str = "Message from Jarvis", body: str = "") -> str:
        try:
            import urllib.parse
            s_enc = urllib.parse.quote(subject.strip())
            b_enc = urllib.parse.quote(body.strip())
            url = f"mailto:{recipient.strip()}?subject={s_enc}&body={b_enc}"
            os.startfile(url)
            return f"Opened email draft to {recipient} with subject '{subject}'."
        except Exception as e:
            return f"Error drafting email: {e}"


# ============================================================================
# 3. SYSTEM & HARDWARE ENGINE
# ============================================================================
class SystemEngine:
    """Sub-millisecond Win32 multimedia hardware keys, diagnostics, and process lifecycle."""

    VK_VOLUME_MUTE = 0xAD
    VK_VOLUME_DOWN = 0xAE
    VK_VOLUME_UP = 0xAF
    VK_MEDIA_NEXT_TRACK = 0xB0
    VK_MEDIA_PREV_TRACK = 0xB1
    VK_MEDIA_PLAY_PAUSE = 0xB3

    @classmethod
    def _send_vk(cls, vk_code: int, repeat: int = 1):
        user32 = ctypes.windll.user32
        for _ in range(repeat):
            user32.keybd_event(vk_code, 0, 0, 0)
            user32.keybd_event(vk_code, 0, 2, 0)
            time.sleep(0.02)

    @classmethod
    def volume_up(cls, steps: int = 3) -> str:
        cls._send_vk(cls.VK_VOLUME_UP, repeat=steps)
        return "Volume increased."

    @classmethod
    def volume_down(cls, steps: int = 3) -> str:
        cls._send_vk(cls.VK_VOLUME_DOWN, repeat=steps)
        return "Volume decreased."

    @classmethod
    def set_volume(cls, level: int) -> str:
        target = max(0, min(100, level))
        ps = (
            "$obj = New-Object -ComObject WScript.Shell; "
            "1..50 | ForEach-Object { $obj.SendKeys([char]174) }; "
            f"1..{target // 2} | ForEach-Object {{ $obj.SendKeys([char]175) }}"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
        return f"Volume set to {target}%."

    @classmethod
    def mute(cls) -> str:
        cls._send_vk(cls.VK_VOLUME_MUTE)
        return "Volume muted / unmuted."

    @classmethod
    def play_pause(cls) -> str:
        cls._send_vk(cls.VK_MEDIA_PLAY_PAUSE)
        return "Media playback toggled."

    @classmethod
    def next_track(cls) -> str:
        cls._send_vk(cls.VK_MEDIA_NEXT_TRACK)
        return "Skipped to next track."

    @classmethod
    def prev_track(cls) -> str:
        cls._send_vk(cls.VK_MEDIA_PREV_TRACK)
        return "Skipped to previous track."

    @classmethod
    def lock_pc(cls) -> str:
        ctypes.windll.user32.LockWorkStation()
        return "PC locked."

    @classmethod
    def take_screenshot(cls) -> str:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = SCREENSHOT_DIR / f"screenshot_{ts}.png"
        try:
            import mss
            from PIL import Image as _PILImage
            with mss.MSS() as sct:
                mon = sct.monitors[1]
                raw = sct.grab(mon)
                img = _PILImage.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
                img.save(str(filepath))
                return f"Screenshot saved to {filepath.name}."
        except Exception:
            try:
                img = pyautogui.screenshot()
                img.save(str(filepath))
                return f"Screenshot saved to {filepath.name}."
            except Exception as e:
                return f"Screenshot unavailable (screen locked or background session): {e}"

    @classmethod
    def get_system_metrics(cls, query: str) -> Optional[str]:
        q = query.lower()
        if "battery" in q or "charge" in q:
            try:
                import psutil
                b = psutil.sensors_battery()
                if b:
                    plugged = "Charging" if b.power_plugged else "On battery"
                    return f"Battery is at {b.percent}% ({plugged})."
            except Exception:
                pass
            return "Battery information unavailable."

        if "ram" in q or "memory" in q:
            try:
                import psutil
                mem = psutil.virtual_memory()
                free_gb = mem.available / (1024**3)
                total_gb = mem.total / (1024**3)
                return f"Memory: {mem.percent}% used. {free_gb:.1f} GB free out of {total_gb:.1f} GB."
            except Exception:
                pass

        if "ip" in q or "network address" in q:
            try:
                hostname = socket.gethostname()
                ip = socket.gethostbyname(hostname)
                return f"Local IP Address: {ip} (Hostname: {hostname})."
            except Exception:
                pass

        return None

    @classmethod
    def close_app(cls, app_name: str) -> str:
        clean = app_name.replace(".exe", "").strip()
        if not clean:
            return "No target application specified to close."
        subprocess.run(f"taskkill /IM {clean}.exe /T /F", shell=True, capture_output=True)
        return f"Closed {clean.title()}."


# ============================================================================
# 4. APP & WEB NAVIGATION ENGINE
# ============================================================================
class AppEngine:
    """Universal application, folder, and web opener."""

    _finder = UniversalAppFinder()

    @classmethod
    def open_target(cls, target: str) -> str:
        t_clean = target.strip().lower()
        if t_clean in SPECIAL_FOLDERS:
            subprocess.Popen(SPECIAL_FOLDERS[t_clean], shell=True)
            return f"Opened {target.title()} folder."

        if t_clean in WEB_SHORTCUTS:
            dest = WEB_SHORTCUTS[t_clean]
            if dest.startswith("http"):
                import webbrowser
                webbrowser.open(dest)
                return f"Opened {target.title()} in browser."
            else:
                subprocess.Popen(dest, shell=True)
                return f"Opened {target.title()}."

        return cls._finder.open_target(target)

    @classmethod
    def open_web(cls, query: str, search: bool = False) -> str:
        import webbrowser
        if search or not query.startswith("http"):
            import urllib.parse
            url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        else:
            url = query
        webbrowser.open(url)
        return f"Opened web search for '{query}'."


# ============================================================================
# 5. FILE & FOLDER OPERATIONS ENGINE
# ============================================================================
class FileEngine:
    """Complete file and folder management on Windows."""

    @classmethod
    def create_folder(cls, folder_name: str) -> str:
        clean = re.sub(r'^(?:named|called)\s+', '', folder_name.strip(), flags=re.I).strip()
        target = DOCUMENTS_DIR / clean
        target.mkdir(parents=True, exist_ok=True)
        return f"Created folder '{clean}' in Documents."

    @classmethod
    def create_file(cls, filename: str, content: str = "") -> str:
        clean = re.sub(r'^(?:named|called)\s+', '', filename.strip(), flags=re.I).strip()
        target = DOCUMENTS_DIR / clean
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Created file '{clean}' in Documents."

    @classmethod
    def read_file(cls, path: str) -> str:
        p = Path(path)
        if not p.is_absolute():
            p = DOCUMENTS_DIR / path
        if not p.exists():
            return f"File '{path}' does not exist."
        try:
            return p.read_text(encoding="utf-8")[:1000]
        except Exception as e:
            return f"Error reading file: {e}"

    @classmethod
    def list_files(cls, directory: Optional[str] = None) -> str:
        d = Path(directory) if directory else DOCUMENTS_DIR
        if not d.exists():
            return f"Directory '{d}' does not exist."
        items = [f"{'📁' if p.is_dir() else '📄'} {p.name}" for p in d.iterdir()][:20]
        return f"Files in {d.name}:\n" + "\n".join(items) if items else f"Directory {d.name} is empty."


# ============================================================================
# 6. GUI & ACCESSIBILITY INTERACTION ENGINE
# ============================================================================
class GUIEngine:
    """Deterministic Windows UI Automation and input driver."""

    @classmethod
    def click_element_by_name(cls, name: str) -> str:
        """Finds a UI control by name in the foreground window and clicks it."""
        try:
            import uiautomation as auto
            fg = auto.GetForegroundControl()
            if not fg:
                return "No active window found."
            for ctrl, _ in auto.WalkControl(fg, maxDepth=5):
                if name.lower() in ctrl.Name.lower() and ctrl.BoundingRectangle.width() > 0:
                    rect = ctrl.BoundingRectangle
                    cx = rect.left + rect.width() // 2
                    cy = rect.top + rect.height() // 2
                    pyautogui.click(cx, cy)
                    return f"Clicked '{ctrl.Name}' at ({cx}, {cy})."
            return f"Could not find UI element matching '{name}'."
        except Exception as e:
            return f"UIA click error: {e}"

    @classmethod
    def type_text(cls, text: str, enter: bool = False) -> str:
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
        if enter:
            time.sleep(0.1)
            pyautogui.press("enter")
        return f"Typed: '{text[:40]}'."

    @classmethod
    def press_hotkey(cls, keys: List[str]) -> str:
        pyautogui.hotkey(*[k.lower() for k in keys])
        return f"Sent hotkey: {'+'.join(keys)}."

    @classmethod
    def scroll(cls, clicks: int = -3) -> str:
        pyautogui.scroll(clicks)
        return f"Scrolled {'down' if clicks < 0 else 'up'}."
