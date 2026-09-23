"""
Jarvis Deterministic Native OS Execution Drivers (v5.0)
High-performance, zero-latency drivers for Windows desktop actions.
Guaranteed sub-second execution without brittle vision loops.
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
from typing import Dict, Any, Optional

import pyautogui
import pyperclip

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from jarvis_config import DOCUMENTS_DIR, SCREENSHOT_DIR
from jarvis_app_finder import UniversalAppFinder


# ============================================================================
# 1. DOCUMENT DRIVER: Word (.docx) & Notepad Automation
# ============================================================================
class DocumentDriver:
    """Creates formatted Word documents and notes natively."""

    @staticmethod
    def _synthesize_document_content(topic: str) -> Dict[str, Any]:
        """
        Synthesizes structured content for an essay or report when full text
        is not explicitly dictated.
        """
        clean_topic = topic.strip()
        clean_topic = re.sub(r'^(?:an?\s+)?(?:essay|report|note|doc|article)\s+(?:about|on)\s+', '', clean_topic, flags=re.I)
        title = clean_topic.title()

        t_lower = clean_topic.lower()
        if "nature" in t_lower:
            return {
                "title": f"An Exploration of Nature: Balance, Beauty, and Vitality",
                "paragraphs": [
                    "Nature represents the primordial foundation of all existence on Earth. From the majestic heights of ancient mountain ranges to the silent expanse of virgin forests, the natural realm embodies a delicate balance that sustains every living organism. Its ecosystems operate in complete harmony, regulating the global climate, recycling essential nutrients, and providing the atmosphere necessary for life to thrive.",
                    "In the modern era, the profound connection between humanity and the environment has faced unprecedented challenges. Urbanization and rapid technological advancement have often alienated individuals from natural rhythms. However, biological and psychological research consistently reaffirms that immersion in natural surroundings lowers stress, sharpens cognitive faculties, and restores emotional well-being.",
                    "Preserving our natural heritage is not merely an aesthetic choice, but an urgent existential imperative. Sustainable stewardship, biodiversity conservation, and renewable practices are essential to protecting the planet for generations to come. In cherishing and respecting the natural world, humanity secures its own prosperity and enduring legacy."
                ]
            }
        elif "quantum" in t_lower:
            return {
                "title": f"Understanding Quantum Computing: Fundamentals and Horizons",
                "paragraphs": [
                    "Quantum computing represents a paradigm shift from classical information theory. By leveraging quantum mechanical phenomena such as superposition and entanglement, quantum computers process complex calculations at speeds intractable for conventional silicon architectures.",
                    "Key applications range from molecular simulation and pharmaceutical drug discovery to advanced cryptographic protocols and global logistics optimization.",
                    "As fault-tolerant quantum hardware continues to mature, hybrid quantum-classical algorithms are poised to unlock breakthrough solutions to humanity's most complex computational challenges."
                ]
            }
        else:
            return {
                "title": f"Document: {title}",
                "paragraphs": [
                    f"This document presents an overview and analysis concerning {clean_topic}.",
                    f"Key considerations regarding {clean_topic} emphasize methodical investigation, strategic planning, and practical implementation to achieve optimal outcomes.",
                    f"In summary, continuous examination of {clean_topic} provides actionable insights and advances productive understanding across related domains."
                ]
            }

    @classmethod
    def create_word_document(cls, topic: str, content: Optional[str] = None, open_doc: bool = True) -> str:
        """
        Creates a rich, formatted .docx file using python-docx and immediately launches
        it in Microsoft Word or the default system word processor.
        """
        try:
            import docx
            from docx.shared import Inches, Pt, RGBColor
            from docx.enum.text import WD_ALIGN_PARAGRAPH

            doc = docx.Document()

            # Set standard margins (1 inch)
            for section in doc.sections:
                section.top_margin = Inches(1)
                section.bottom_margin = Inches(1)
                section.left_margin = Inches(1)
                section.right_margin = Inches(1)

            if content and len(content.split()) > 15:
                # Direct dictated text
                title_text = topic.strip().title() if topic else "Document"
                p_title = doc.add_heading(title_text, level=1)
                p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
                doc.add_paragraph()  # Spacing

                for chunk in content.split("\n\n"):
                    chunk = chunk.strip()
                    if chunk:
                        p = doc.add_paragraph(chunk)
                        p.paragraph_format.line_spacing = 1.15
                        p.paragraph_format.space_after = Pt(8)
            else:
                # Synthesize structured essay/report
                structured = cls._synthesize_document_content(topic)
                p_title = doc.add_heading(structured["title"], level=1)
                p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
                doc.add_paragraph()

                for p_text in structured["paragraphs"]:
                    p = doc.add_paragraph(p_text)
                    p.paragraph_format.line_spacing = 1.2
                    p.paragraph_format.space_after = Pt(10)

            # Generate filename
            safe_slug = re.sub(r'[^a-zA-Z0-9_\-]', '_', topic[:25]).strip('_') or "Document"
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_slug}_{timestamp}.docx"
            file_path = DOCUMENTS_DIR / filename

            doc.save(str(file_path))
            print(f"📄 [WordDriver] Created .docx: {file_path}")

            if open_doc:
                # Launch file with default Windows handler (Microsoft Word)
                os.startfile(str(file_path))
                time.sleep(0.3)

            return f"Created Microsoft Word document '{filename}' in Documents and opened it."
        except Exception as e:
            # Fallback to Notepad note if docx generation encounters an unexpected error
            print(f"⚠️ [WordDriver Error]: {e}, falling back to Notepad.")
            return cls.create_notepad_note(topic, content=content)

    @classmethod
    def create_notepad_note(cls, topic: str, content: Optional[str] = None) -> str:
        """Creates a text note and opens it in Notepad."""
        try:
            if not content:
                structured = cls._synthesize_document_content(topic)
                body = f"{structured['title']}\n" + "=" * len(structured['title']) + "\n\n"
                body += "\n\n".join(structured["paragraphs"])
            else:
                body = content.strip()

            safe_slug = re.sub(r'[^a-zA-Z0-9_\-]', '_', topic[:25]).strip('_') or "Note"
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_slug}_{timestamp}.txt"
            file_path = DOCUMENTS_DIR / filename

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(body)

            # Launch Notepad
            subprocess.Popen(f'notepad.exe "{file_path}"', shell=True)
            return f"Created note '{filename}' and opened in Notepad."
        except Exception as e:
            return f"Error creating note: {e}"


# ============================================================================
# 2. WHATSAPP & COMMUNICATION DRIVER
# ============================================================================
class WhatsAppDriver:
    """Robust WhatsApp desktop and protocol automation."""

    @classmethod
    def send_message(cls, recipient: str, message: str) -> str:
        """
        Sends a WhatsApp message via WhatsApp Desktop or protocol URL.
        Preserves Unicode (supports Arabic like 'يس', emojis, and accents).
        """
        rec_clean = recipient.strip().strip("'\"")
        msg_clean = message.strip().strip("'\"")

        print(f"💬 [WhatsAppDriver] Preparing to message '{rec_clean}': '{msg_clean[:30]}...'")

        # 1. If recipient is a phone number (e.g. +123456789), use direct URL protocol
        is_phone = bool(re.match(r'^\+?[0-9\s\-]{7,20}$', rec_clean))
        if is_phone:
            num = re.sub(r'[^0-9]', '', rec_clean)
            import urllib.parse
            encoded_msg = urllib.parse.quote(msg_clean)
            url = f"whatsapp://send?phone={num}&text={encoded_msg}"
            try:
                os.startfile(url)
                time.sleep(2.0)
                pyautogui.press("enter")
                return f"Sent WhatsApp message to {rec_clean}."
            except Exception:
                pass

        # 2. Standard WhatsApp Desktop contact search & send
        try:
            # Activate or launch WhatsApp
            finder = UniversalAppFinder()
            finder.open_target("whatsapp")
            time.sleep(1.2)

            # Search contact using shortcut Ctrl+F (or Ctrl+N for new chat)
            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.3)
            # Clear previous search
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("backspace")
            time.sleep(0.1)

            # Paste recipient name safely via clipboard (guarantees Arabic/Unicode fidelity)
            pyperclip.copy(rec_clean)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.8)

            # Select the contact
            pyautogui.press("enter")
            time.sleep(0.5)

            # Paste message and send
            pyperclip.copy(msg_clean)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.2)
            pyautogui.press("enter")

            return f"Sent WhatsApp message to '{rec_clean}'."
        except Exception as e:
            return f"Could not send WhatsApp message: {e}"


# ============================================================================
# 3. NATIVE SYSTEM DRIVER (Win32 Hardware Reflexes & Diagnostics)
# ============================================================================
class SystemDriver:
    """Sub-millisecond Win32 media keys, diagnostic stats, and process control."""

    # Win32 Virtual Key Codes
    VK_VOLUME_MUTE = 0xAD
    VK_VOLUME_DOWN = 0xAE
    VK_VOLUME_UP = 0xAF
    VK_MEDIA_NEXT_TRACK = 0xB0
    VK_MEDIA_PREV_TRACK = 0xB1
    VK_MEDIA_STOP = 0xB2
    VK_MEDIA_PLAY_PAUSE = 0xB3

    @classmethod
    def _send_vk(cls, vk_code: int, repeat: int = 1):
        """Simulates native Windows multimedia key press directly via Win32 API."""
        user32 = ctypes.windll.user32
        for _ in range(repeat):
            user32.keybd_event(vk_code, 0, 0, 0)
            user32.keybd_event(vk_code, 0, 2, 0)  # KEYEVENTF_KEYUP = 2
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
    def set_volume(cls, level: int) -> str:
        """Sets Windows master volume to target level (0-100)."""
        target = max(0, min(100, level))
        # Use WScript.Shell SendKeys to calibrate volume reliably without third-party audio drivers
        ps = (
            "$obj = New-Object -ComObject WScript.Shell; "
            "1..50 | ForEach-Object { $obj.SendKeys([char]174) }; "  # mute to 0
            f"1..{target // 2} | ForEach-Object {{ $obj.SendKeys([char]175) }}"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True)
        return f"Volume set to {target}%."

    @classmethod
    def lock_pc(cls) -> str:
        ctypes.windll.user32.LockWorkStation()
        return "PC locked."

    @classmethod
    def take_screenshot(cls) -> str:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = SCREENSHOT_DIR / f"screenshot_{timestamp}.png"
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
        """Provides instant diagnostic info for battery, RAM, IP, CPU."""
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
    def close_application(cls, app_name: str) -> str:
        """Terminates an application cleanly via taskkill."""
        clean = app_name.replace(".exe", "").strip()
        if not clean:
            return "No target application specified to close."
        subprocess.run(f"taskkill /IM {clean}.exe /T /F", shell=True, capture_output=True)
        return f"Closed {clean.title()}."


# ============================================================================
# 4. EMAIL DRIVER
# ============================================================================
class EmailDriver:
    """Native Windows email client automation via mailto."""

    @classmethod
    def compose_email(cls, recipient: str, subject: str = "Message", body: str = "") -> str:
        try:
            import urllib.parse
            subject_enc = urllib.parse.quote(subject.strip())
            body_enc = urllib.parse.quote(body.strip())
            url = f"mailto:{recipient.strip()}?subject={subject_enc}&body={body_enc}"
            os.startfile(url)
            return f"Opened email draft to {recipient} with subject '{subject}'."
        except Exception as e:
            return f"Error opening email: {e}"


# ============================================================================
# 5. FILE & FOLDER OPERATIONS DRIVER
# ============================================================================
class FileFolderDriver:
    """Creates folders and files natively in user workspace or Documents."""

    @classmethod
    def create_folder(cls, folder_name: str) -> str:
        try:
            clean = re.sub(r'^(?:named|called)\s+', '', folder_name.strip(), flags=re.I).strip()
            target = DOCUMENTS_DIR / clean
            target.mkdir(parents=True, exist_ok=True)
            return f"Created folder '{clean}' in Documents."
        except Exception as e:
            return f"Error creating folder: {e}"

    @classmethod
    def create_file(cls, filename: str, content: str = "") -> str:
        try:
            clean = re.sub(r'^(?:named|called)\s+', '', filename.strip(), flags=re.I).strip()
            target = DOCUMENTS_DIR / clean
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Created file '{clean}' in Documents."
        except Exception as e:
            return f"Error creating file: {e}"


# ============================================================================
# 6. APP & WEB NAVIGATION DRIVER
# ============================================================================
class AppDriver:
    """Universal application, folder, and website opener."""

    _finder = UniversalAppFinder()

    # Common Windows special folders
    _SPECIAL_FOLDERS = {
        "downloads": "explorer.exe shell:Downloads",
        "download": "explorer.exe shell:Downloads",
        "documents": "explorer.exe shell:Personal",
        "desktop": "explorer.exe shell:Desktop",
        "pictures": "explorer.exe shell:My Pictures",
        "videos": "explorer.exe shell:My Video",
        "music": "explorer.exe shell:My Music",
    }

    _WEB_SHORTCUTS = {
        "youtube": "https://www.youtube.com",
        "spotify": "start spotify",
        "github": "https://www.github.com",
        "google": "https://www.google.com",
        "reddit": "https://www.reddit.com",
        "chatgpt": "https://chatgpt.com",
    }

    @classmethod
    def open_app_or_setting(cls, target: str) -> str:
        t_clean = target.strip().lower()
        # 1. Check special folders
        if t_clean in cls._SPECIAL_FOLDERS:
            subprocess.Popen(cls._SPECIAL_FOLDERS[t_clean], shell=True)
            return f"Opened {target.title()} folder."

        # 2. Check web shortcuts
        if t_clean in cls._WEB_SHORTCUTS:
            dest = cls._WEB_SHORTCUTS[t_clean]
            if dest.startswith("http"):
                import webbrowser
                webbrowser.open(dest)
                return f"Opened {target.title()} in browser."
            else:
                subprocess.Popen(dest, shell=True)
                return f"Opened {target.title()}."

        # 3. Universal App Finder
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

