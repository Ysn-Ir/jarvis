"""
Laya Glassmorphic Desktop Assistant HUD
State-of-the-art Dark Glassmorphism interface featuring:
- Deep obsidian void with floating 3D reflective dark glass orbs
- Central floating frosted glass card with true optical Gaussian blur of the backdrop
- Razor-sharp 1px luminous border and specular rim highlight
- Minimalist editorial typography and outline pill tags matching luxury glassmorphism design
- Real-time holographic audio waveform visualizer (harmonic sine waves)
- Full voice pipeline: continuous wake word ("Clanker", "Call", "Jarvis"), dynamic VAD, CUDA Whisper, and barge-in vocal interrupt
- Instant fast-path actions, ReAct live reasoning, and Telegram integration
"""

import sys
import os
import math
import time
import queue
import random
import threading
from typing import Optional, Callable, List, Dict, Any
from pathlib import Path
import ctypes

# Ensure UTF-8 output
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

import customtkinter as ctk
from PIL import Image, ImageFilter, ImageDraw

try:
    import pywinstyles
    HAS_PYWINSTYLES = True
except ImportError:
    HAS_PYWINSTYLES = False

import psutil

from laya.audio.tts import get_tts_engine
from laya.audio.capture import AudioCapture
from laya.fast_path.executor import get_fast_path_executor
from laya.ui.meme_engine import get_meme_engine
from laya.orchestrator.memory import get_memory_store
from laya.audio.meme_audio import play_meme_audio
from laya.tools.interrupt_manager import (
    request_interrupt,
    is_interrupt_requested,
    reset_interrupt,
)
from laya.config import UI_VISIBILITY_MODE, WAKE_PHRASES


class LayaHUD(ctk.CTk):
    _active_instance: Optional["LayaHUD"] = None

    def __init__(self, assistant_instance=None):
        super().__init__()
        LayaHUD._active_instance = self

        self.assistant = assistant_instance
        self.tts = get_tts_engine()
        self.stt = None  # Loaded asynchronously in background thread for instant GUI launch
        self.capture = AudioCapture()
        self.meme_engine = get_meme_engine()
        self.memory_store = get_memory_store()
        self.fast_path = get_fast_path_executor()
        self.last_query = ""
        self.is_core_ready = False

        # Thread Communication Queue
        self.msg_queue: queue.Queue = queue.Queue()
        self.is_recording = False
        self.is_processing = False
        self.is_pinned_top = True
        self.current_state = "STARTUP"

        # Unique Windows App ID for distinct Taskbar grouping
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("jarvis.laya.desktop.assistant.1.0")
        except Exception:
            pass

        # Window Appearance & Geometry
        self.title("Laya — Autonomous Desktop Intelligence")
        self.app_width = 860
        self.app_height = 620

        # Center on screen
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        pos_x = max(20, (screen_w - self.app_width) // 2)
        pos_y = max(20, (screen_h - self.app_height) // 2 - 20)
        self.geometry(f"{self.app_width}x{self.app_height}+{pos_x}+{pos_y}")
        self.resizable(False, False)

        # Frameless floating glass card look
        self.overrideredirect(True)
        self.attributes("-topmost", self.is_pinned_top)

        # Attach taskbar icon for borderless window on Windows
        self._setup_taskbar_icon()

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Color Palette Tokens
        self.CLR_BG = "#060709"             # Obsidian space void
        self.CLR_CARD = "#0d131e"           # Frosted glass panel
        self.CLR_BORDER = "#1f2c42"         # Glass border
        self.CLR_BORDER_GLOW = "#38bdf8"    # Luminous Cyan highlight
        self.CLR_CYAN = "#00f0ff"           # JARVIS Hologram Cyan
        self.CLR_PURPLE = "#a855f7"         # Violet
        self.CLR_EMERALD = "#10b981"        # Ready Emerald
        self.CLR_ROSE = "#f43f5e"           # Stop Rose
        self.CLR_WHITE = "#ffffff"          # Pure Crystal White
        self.CLR_TEXT_MUTED = "#8e9bb0"     # Slate Subtext

        self.configure(fg_color=self.CLR_BG)

        # Drag tracking
        self._drag_x = 0
        self._drag_y = 0
        self._wave_phase = 0.0

        # Build Background & Glassmorphic Interface
        self._build_glassmorphic_layout()

        # Global hotkey bindings: ESC to interrupt & silence
        self.bind_all("<Escape>", lambda e: self._on_escape_pressed())

        # Initialize Continuous Wake Word & Barge-In Engine in Background Thread
        self.wake_detector = None
        threading.Thread(target=self._async_bootstrap_neural_core, daemon=True).start()

        # Periodic Event & Waveform Loops
        self.after(35, self._drain_queue)
        self.after(35, self._animate_waveform)

    # -------------------------------------------------------------
    # Window Management & Draggability
    # -------------------------------------------------------------
    def _setup_taskbar_icon(self):
        """Ensure borderless window has proper Taskbar icon and presence on Windows."""
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            style = (style & ~0x00000080) | 0x00040000  # WS_EX_APPWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)
        except Exception:
            pass

        icon_path = Path(__file__).resolve().parent.parent.parent / "assets" / "laya_icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        x = self.winfo_x() + (event.x - self._drag_x)
        y = self.winfo_y() + (event.y - self._drag_y)
        self.geometry(f"+{x}+{y}")

    def _toggle_pin(self):
        self.is_pinned_top = not self.is_pinned_top
        self.attributes("-topmost", self.is_pinned_top)
        if self.is_pinned_top:
            self.btn_pin.configure(text_color=self.CLR_CYAN, fg_color="#102538", border_color="#1b4263")
        else:
            self.btn_pin.configure(text_color=self.CLR_TEXT_MUTED, fg_color="#141c2b", border_color="#24334a")

    def _on_minimize(self):
        self.withdraw()
        # Restore on click from taskbar or re-invoke
        self.after(100, lambda: self.deiconify())

    def _on_close(self):
        try:
            self.tts.stop()
            if self.wake_detector:
                self.wake_detector.stop()
        except Exception:
            pass
        self.destroy()
        sys.exit(0)

    def _hide_hud(self):
        self.withdraw()

    def _show_hud(self):
        self.deiconify()
        self.lift()

    # -------------------------------------------------------------
    # Glassmorphism Composite Background & Layout
    # -------------------------------------------------------------
    def _get_or_create_background(self) -> ctk.CTkImage:
        assets_dir = Path(__file__).resolve().parent.parent.parent / "assets"
        bg_cache = assets_dir / "laya_glass_card_bg.png"
        raw_spheres = assets_dir / "glass_spheres_bg.jpg"

        if bg_cache.exists():
            img = Image.open(str(bg_cache)).convert("RGBA")
        else:
            # Composite on the fly
            w, h = self.app_width, self.app_height
            if raw_spheres.exists():
                bg = Image.open(str(raw_spheres)).convert("RGBA")
            else:
                bg = Image.new("RGBA", (w, h), (6, 7, 9, 255))
            bg = bg.resize((w, h), Image.Resampling.LANCZOS)

            pad_x, pad_y = 28, 24
            card_w = w - (pad_x * 2)
            card_h = h - (pad_y * 2)
            cx, cy = pad_x, pad_y

            crop = bg.crop((cx, cy, cx + card_w, cy + card_h))
            blurred = crop.filter(ImageFilter.GaussianBlur(radius=28))

            tint = Image.new("RGBA", (card_w, card_h), (10, 14, 22, 175))
            card_surface = Image.alpha_composite(blurred, tint)

            draw = ImageDraw.Draw(card_surface)
            radius = 22
            draw.rounded_rectangle([0, 0, card_w - 1, card_h - 1], radius=radius, outline=(255, 255, 255, 55), width=1)
            draw.line([(radius + 4, 1), (card_w - radius - 4, 1)], fill=(255, 255, 255, 125), width=1)

            mask = Image.new("L", (card_w, card_h), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle([0, 0, card_w - 1, card_h - 1], radius=radius, fill=255)

            bg.paste(card_surface, (cx, cy), mask)
            try:
                bg.save(str(bg_cache))
            except Exception:
                pass
            img = bg

        return ctk.CTkImage(light_image=img, dark_image=img, size=(self.app_width, self.app_height))

    def _build_glassmorphic_layout(self):
        # 1. Background image with optical blur of 3D spheres
        self.bg_image = self._get_or_create_background()
        self.bg_label = ctk.CTkLabel(self, text="", image=self.bg_image)
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        # Allow dragging by clicking anywhere on the wallpaper
        self.bg_label.bind("<ButtonPress-1>", self._start_drag)
        self.bg_label.bind("<B1-Motion>", self._on_drag)

        # 2. Central Floating Frosted Card Frame
        # Matches the optical blur boundaries: x=28, y=24, w=804, h=572
        self.card = ctk.CTkFrame(
            self,
            width=804,
            height=572,
            fg_color="transparent",
            corner_radius=22
        )
        self.card.place(x=28, y=24)

        # 3. Header Section (Typography & Window Controls)
        header_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        header_frame.pack(fill="x", padx=24, pady=(18, 0))

        # Dragging on header
        header_frame.bind("<ButtonPress-1>", self._start_drag)
        header_frame.bind("<B1-Motion>", self._on_drag)

        # Left: Editorial Typography matching user reference mockup
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left")
        title_box.bind("<ButtonPress-1>", self._start_drag)
        title_box.bind("<B1-Motion>", self._on_drag)

        self.title_1 = ctk.CTkLabel(
            title_box,
            text="Laya",
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=self.CLR_WHITE,
            anchor="w"
        )
        self.title_1.pack(anchor="w", pady=(0, 0))

        self.title_2 = ctk.CTkLabel(
            title_box,
            text="Intelligence.",
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=self.CLR_WHITE,
            anchor="w"
        )
        self.title_2.pack(anchor="w", pady=(0, 2))

        self.sub_label = ctk.CTkLabel(
            title_box,
            text="autonomous desktop intelligence.",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="normal"),
            text_color=self.CLR_TEXT_MUTED,
            anchor="w"
        )
        self.sub_label.pack(anchor="w")

        # Right: Minimalist Frosted Window Controls
        ctrls_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        ctrls_frame.pack(side="right", anchor="ne")

        self.btn_pin = ctk.CTkButton(
            ctrls_frame,
            text="📌",
            width=32,
            height=32,
            corner_radius=16,
            fg_color="#102538",
            hover_color="#183652",
            border_width=1,
            border_color="#1b4263",
            text_color=self.CLR_CYAN,
            font=ctk.CTkFont(size=12),
            command=self._toggle_pin
        )
        self.btn_pin.pack(side="left", padx=4)

        self.btn_min = ctk.CTkButton(
            ctrls_frame,
            text="—",
            width=32,
            height=32,
            corner_radius=16,
            fg_color="#141c2b",
            hover_color="#1e2c45",
            border_width=1,
            border_color="#24334a",
            text_color=self.CLR_TEXT_MUTED,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_minimize
        )
        self.btn_min.pack(side="left", padx=4)

        self.btn_close = ctk.CTkButton(
            ctrls_frame,
            text="✕",
            width=32,
            height=32,
            corner_radius=16,
            fg_color="#201118",
            hover_color="#3a1624",
            border_width=1,
            border_color="#542031",
            text_color="#fb7185",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_close
        )
        self.btn_close.pack(side="left", padx=4)

        # 4. Minimalist Outline Pill Badges (Directly echoing [ 4K ] [ PSD ] from mockup)
        badges_frame = ctk.CTkFrame(self.card, fg_color="transparent")
        badges_frame.pack(fill="x", padx=24, pady=(10, 8))

        def make_pill(text, border_col="#24334a", text_col="#94a3b8"):
            return ctk.CTkButton(
                badges_frame,
                text=text,
                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                height=22,
                corner_radius=11,
                fg_color="transparent",
                border_width=1,
                border_color=border_col,
                text_color=text_col,
                hover=False
            )

        make_pill("[ 4K ]").pack(side="left", padx=(0, 6))
        make_pill("[ FAST-PATH ]").pack(side="left", padx=(0, 6))
        make_pill("[ RTX 4050 ]").pack(side="left", padx=(0, 6))

        self.state_badge = make_pill("● INITIALIZING", "#7c3aed", "#c084fc")
        self.state_badge.pack(side="left", padx=(0, 6))

        # 5. Holographic Audio Waveform Visualizer
        self.wave_canvas = ctk.CTkCanvas(
            self.card,
            height=40,
            bg="#0a0f17",
            highlightthickness=0
        )
        self.wave_canvas.pack(fill="x", padx=24, pady=(2, 8))
        self.wave_canvas.bind("<ButtonPress-1>", self._start_drag)
        self.wave_canvas.bind("<B1-Motion>", self._on_drag)

        # 6. Live Intel & Response Glass Card
        self.transcript_panel = ctk.CTkFrame(
            self.card,
            fg_color="#0b101a",
            corner_radius=16,
            border_width=1,
            border_color=self.CLR_BORDER
        )
        self.transcript_panel.pack(fill="both", expand=True, padx=24, pady=(0, 8))

        # Query / Vocal Status Line
        self.query_header = ctk.CTkFrame(self.transcript_panel, fg_color="transparent")
        self.query_header.pack(fill="x", padx=16, pady=(10, 2))

        self.query_text = ctk.CTkLabel(
            self.query_header,
            text="Listening for voice... (Say 'Clanker', 'Jarvis', or 'Call')",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="normal"),
            text_color=self.CLR_TEXT_MUTED,
            anchor="w"
        )
        self.query_text.pack(side="left", fill="x", expand=True)

        self.replay_btn = ctk.CTkButton(
            self.query_header,
            text="🔊 Replay",
            width=64,
            height=20,
            corner_radius=10,
            fg_color="#141d2c",
            hover_color="#1e2c42",
            border_width=1,
            border_color="#24334a",
            text_color=self.CLR_CYAN,
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            command=self._replay_last_speech
        )
        self.replay_btn.pack(side="right")

        # Response Text Box
        self.result_box = ctk.CTkTextbox(
            self.transcript_panel,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=self.CLR_WHITE,
            fg_color="transparent",
            wrap="word",
            activate_scrollbars=False
        )
        self.result_box.pack(fill="both", expand=True, padx=12, pady=(2, 6))
        self.result_box.insert("end", "Jarvis assistant core online. Systems nominal, voice recognition active.")
        self.result_box.configure(state="disabled")

        # Ticker Status Line (Live actions / timings)
        self.ticker_label = ctk.CTkLabel(
            self.transcript_panel,
            text="✦ Core Ready | Single-pass continuous listening active",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="#526580",
            anchor="w"
        )
        self.ticker_label.pack(fill="x", padx=16, pady=(0, 8))

        # 7. Sleek Action Pills
        actions_bar = ctk.CTkFrame(self.card, fg_color="transparent")
        actions_bar.pack(fill="x", padx=24, pady=(0, 8))

        def make_action_chip(label, icon, cmd):
            return ctk.CTkButton(
                actions_bar,
                text=f"{icon} {label}".strip(),
                font=ctk.CTkFont(family="Segoe UI", size=11),
                height=28,
                corner_radius=14,
                fg_color="#101724",
                hover_color="#182338",
                border_width=1,
                border_color="#1e2c42",
                text_color="#cbd5e1",
                command=cmd
            )

        make_action_chip("Screenshot", "📸", lambda: self._trigger_fast("take_screenshot")).pack(side="left", padx=(0, 5))
        make_action_chip("Zoom In", "🔍", lambda: self._trigger_fast("zoom_window_region", {"region": "center", "zoom_factor": 2.5})).pack(side="left", padx=(0, 5))
        make_action_chip("Paint", "🎨", lambda: self._trigger_fast("draw_shape", {"shape": "heart", "title_keyword": "Paint"})).pack(side="left", padx=(0, 5))
        make_action_chip("Notepad", "📝", lambda: self._start_command_execution("write a quick note into notepad")).pack(side="left", padx=(0, 5))
        make_action_chip("Telegram", "✈️", lambda: self._trigger_fast("telegram_launch_login")).pack(side="left", padx=(0, 5))
        make_action_chip("Lofi Chill", "🎵", lambda: self._trigger_fast("play_youtube", {"query": "synthwave lofi chillhop mix"})).pack(side="left", padx=(0, 5))

        # 8. Bottom Floating Command Bar
        bottom_bar = ctk.CTkFrame(
            self.card,
            fg_color="#0c121d",
            corner_radius=22,
            border_width=1,
            border_color="#1f2c42",
            height=46
        )
        bottom_bar.pack(fill="x", padx=24, pady=(0, 16))
        bottom_bar.pack_propagate(False)

        # Glowing Mic Button
        self.mic_btn = ctk.CTkButton(
            bottom_bar,
            text="🎙️",
            width=36,
            height=36,
            corner_radius=18,
            fg_color="#0284c7",
            hover_color="#0369a1",
            text_color=self.CLR_WHITE,
            font=ctk.CTkFont(size=14),
            command=self._on_mic_click
        )
        self.mic_btn.pack(side="left", padx=(5, 8), pady=5)

        # Text Input Entry
        self.input_field = ctk.CTkEntry(
            bottom_bar,
            placeholder_text="Ask Jarvis anything or type a desktop command...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="transparent",
            border_width=0,
            text_color=self.CLR_WHITE
        )
        self.input_field.pack(side="left", fill="x", expand=True, padx=4, pady=5)
        self.input_field.bind("<Return>", lambda e: self._on_submit_text())

        # Send Button
        self.send_btn = ctk.CTkButton(
            bottom_bar,
            text="➔",
            width=36,
            height=36,
            corner_radius=18,
            fg_color="#182338",
            hover_color="#243452",
            border_width=1,
            border_color="#283b5c",
            text_color=self.CLR_CYAN,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_submit_text
        )
        self.send_btn.pack(side="right", padx=(4, 5), pady=5)

        # Emergency Stop Button
        self.stop_btn = ctk.CTkButton(
            bottom_bar,
            text="■ STOP",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            width=68,
            height=32,
            corner_radius=16,
            fg_color="#241217",
            hover_color="#3d1820",
            border_width=1,
            border_color="#54202b",
            text_color="#f43f5e",
            command=self._on_stop_clicked
        )
        self.stop_btn.pack(side="right", padx=(4, 4), pady=5)

    # -------------------------------------------------------------
    # Animated Holographic Waveform
    # -------------------------------------------------------------
    def _animate_waveform(self):
        try:
            self.wave_canvas.delete("all")
            w = self.wave_canvas.winfo_width() or 750
            h = self.wave_canvas.winfo_height() or 40
            mid_y = h / 2

            # Dynamics based on state
            if self.current_state == "LISTENING":
                amp = 11.0
                freq = 0.22
                speed = 0.35
                color = self.CLR_CYAN
            elif self.current_state == "PROCESSING":
                amp = 8.0
                freq = 0.32
                speed = 0.42
                color = self.CLR_PURPLE
            elif self.current_state == "SPEAKING":
                amp = 13.0
                freq = 0.18
                speed = 0.38
                color = self.CLR_CYAN
            elif self.current_state == "STOPPED":
                amp = 2.0
                freq = 0.10
                speed = 0.05
                color = self.CLR_ROSE
            else:  # IDLE
                amp = 3.5
                freq = 0.12
                speed = 0.09
                color = "#22d3ee"

            self._wave_phase += speed

            # Multi-harmonic sine lines
            points_1 = []
            points_2 = []
            for x in range(0, w, 4):
                y1 = mid_y + math.sin(x * freq + self._wave_phase) * amp * math.sin(x / w * math.pi)
                y2 = mid_y + math.cos(x * (freq * 0.75) - self._wave_phase) * (amp * 0.6) * math.sin(x / w * math.pi)
                points_1.append((x, y1))
                points_2.append((x, y2))

            for i in range(len(points_1) - 1):
                self.wave_canvas.create_line(points_1[i][0], points_1[i][1], points_1[i+1][0], points_1[i+1][1], fill=color, width=2)
                self.wave_canvas.create_line(points_2[i][0], points_2[i][1], points_2[i+1][0], points_2[i+1][1], fill="#a855f7", width=1)

        except Exception:
            pass

        self.after(35, self._animate_waveform)

    # -------------------------------------------------------------
    # Async Neural Engine & Wake Word Loading
    # -------------------------------------------------------------
    def _async_bootstrap_neural_core(self):
        try:
            if not self.assistant:
                self.msg_queue.put(("boot_status", "Initializing Orchestrator & Tool Registry..."))
                from laya.main import LayaAssistant
                self.assistant = LayaAssistant()

            self.msg_queue.put(("boot_status", "Loading CUDA Whisper speech engine..."))
            from laya.audio.stt import get_stt_engine
            self.stt = get_stt_engine()

            self.msg_queue.put(("boot_status", "Activating continuous barge-in wake detector..."))
            from laya.audio.wake_word import get_wake_word_detector
            self.wake_detector = get_wake_word_detector(
                on_wake=self._on_wake_heard,
                on_command=self._on_direct_command_heard,
                on_interrupt=self._on_interrupt_requested,
            )
            self.wake_detector.start()

            self.is_core_ready = True
            self.msg_queue.put(("core_ready", None))
        except Exception as e:
            print(f"[HUD Core Init Error] {e}")
            self.is_core_ready = True
            self.msg_queue.put(("core_ready", None))

    # -------------------------------------------------------------
    # Event Handlers & Voice Pipeline
    # -------------------------------------------------------------
    def _on_interrupt_requested(self):
        print("[HUD] Vocal interruption detected: aborting.")
        request_interrupt("Vocal interruption")
        self.tts.stop()
        self.msg_queue.put(("barge_in_stop", None))

    def _on_stop_clicked(self):
        print("[HUD] STOP clicked: aborting.")
        request_interrupt("Stop button clicked")
        self.tts.stop()
        self.msg_queue.put(("barge_in_stop", None))

    def _on_escape_pressed(self):
        print("[HUD] ESC pressed: aborting.")
        request_interrupt("ESC pressed")
        self.tts.stop()
        self.msg_queue.put(("barge_in_stop", None))

    def _on_wake_heard(self):
        self.deiconify()
        self.lift()
        self.tts.stop()
        self.msg_queue.put(("wake_trigger", None))

    def _on_direct_command_heard(self, command_text: str):
        self.deiconify()
        self.lift()
        self.tts.stop()
        self.msg_queue.put(("direct_command", command_text))

    def _on_mic_click(self):
        self.tts.stop()
        if self.is_recording:
            return
        if self.wake_detector:
            self.wake_detector.pause()
        self._start_voice_recording_thread()

    def _on_submit_text(self):
        self.tts.stop()
        query = self.input_field.get().strip()
        if not query:
            return
        self.input_field.delete(0, "end")
        self._start_command_execution(query)

    def _start_voice_recording_thread(self):
        self.deiconify()
        self.lift()
        self.is_recording = True
        self.current_state = "LISTENING"
        self._set_state_badge("● LISTENING", self.CLR_CYAN, "#0284c7")
        self.query_text.configure(text="Listening...", text_color=self.CLR_WHITE)
        threading.Thread(target=self._record_and_transcribe_worker, daemon=True).start()

    def _record_and_transcribe_worker(self):
        try:
            self.tts.stop()
            audio_data = self.capture.record_until_silence(max_duration_sec=15.0)
            if audio_data is None or len(audio_data) == 0:
                self.msg_queue.put(("reset_idle", None))
                return

            self.msg_queue.put(("state", "PROCESSING"))
            if self.stt is None:
                from laya.audio.stt import get_stt_engine
                self.stt = get_stt_engine()
            transcript = self.stt.transcribe(audio_data)
            if not transcript or not transcript.strip():
                self.msg_queue.put(("reset_idle", None))
                return

            self.msg_queue.put(("direct_command", transcript))

        except Exception:
            self.msg_queue.put(("reset_idle", None))

    def _start_command_execution(self, query: str):
        self.deiconify()
        self.lift()
        reset_interrupt()
        self.tts.stop()
        self.last_query = query
        if self.wake_detector:
            self.wake_detector.pause()

        self.current_state = "PROCESSING"
        self._set_state_badge("● PROCESSING", self.CLR_PURPLE, "#7c3aed")
        self.query_text.configure(text=f"\"{query}\"", text_color=self.CLR_WHITE)

        threading.Thread(target=lambda: self._execute_task_worker(query), daemon=True).start()

    def _execute_task_worker(self, query: str):
        self.is_processing = True
        t0 = time.time()
        try:
            def on_step(step_msg: str):
                self.msg_queue.put(("step", step_msg))

            if not self.assistant:
                from laya.main import LayaAssistant
                self.assistant = LayaAssistant()

            if self.assistant:
                result = self.assistant.handle_command(query, speak=True, step_callback=on_step)
            else:
                result = f"Completed command: {query}"

            dt_ms = (time.time() - t0) * 1000
            if not is_interrupt_requested():
                self.msg_queue.put(("result", result, dt_ms))

        except Exception as e:
            if not is_interrupt_requested():
                self.msg_queue.put(("result", f"Execution error: {e}", 0))
        finally:
            self.is_processing = False
            self.is_recording = False
            self.msg_queue.put(("post_execution", None))

    def _trigger_fast(self, action: str, params: Optional[dict] = None):
        params = params or {}
        handler = getattr(self.fast_path, action, None)
        if handler:
            try:
                res = handler(**params)
                self._render_result(str(res), 50.0)
                self.tts.speak(str(res))
            except Exception as e:
                self._render_result(f"Action error: {e}", 0)

    # -------------------------------------------------------------
    # Queue Drainer & State Updates
    # -------------------------------------------------------------
    def _drain_queue(self):
        try:
            while True:
                kind, *args = self.msg_queue.get_nowait()

                if kind == "boot_status":
                    self.query_text.configure(text=f"✦ {args[0]}")

                elif kind == "core_ready":
                    self.current_state = "IDLE"
                    self._set_state_badge("● READY", self.CLR_EMERALD, "#059669")
                    self.query_text.configure(
                        text="Listening for voice... (Say 'Clanker', 'Jarvis', or 'Call')",
                        text_color=self.CLR_TEXT_MUTED,
                    )
                    self._play_startup_greeting()

                elif kind == "wake_trigger":
                    self._start_voice_recording_thread()

                elif kind == "direct_command":
                    self._start_command_execution(args[0])

                elif kind == "state":
                    st = args[0]
                    self.current_state = st
                    if st == "PROCESSING":
                        self._set_state_badge("● PROCESSING", self.CLR_PURPLE, "#7c3aed")

                elif kind == "step":
                    if not is_interrupt_requested():
                        self.ticker_label.configure(text=f"⚡ {args[0]}")

                elif kind == "result":
                    res_text, dt_ms = args[0], args[1]
                    if self.current_state != "STOPPED" and not is_interrupt_requested():
                        self._render_result(res_text, dt_ms)

                elif kind == "barge_in_stop":
                    self.current_state = "STOPPED"
                    self._set_state_badge("● STOPPED", self.CLR_ROSE, "#e11d48")
                    self.query_text.configure(text="Stopped. Listening...", text_color=self.CLR_WHITE)
                    self.ticker_label.configure(text="✦ Vocal interrupt triggered: execution halted")
                    if self.wake_detector:
                        self.wake_detector.resume()

                elif kind == "reset_idle":
                    if self.current_state != "STOPPED":
                        self.current_state = "IDLE"
                        self._set_state_badge("● READY", self.CLR_EMERALD, "#059669")
                        self.query_text.configure(
                            text="Listening for voice... (Say 'Clanker', 'Jarvis', or 'Call')",
                            text_color=self.CLR_TEXT_MUTED
                        )
                    if self.wake_detector:
                        self.wake_detector.resume()

                elif kind == "post_execution":
                    if self.current_state != "STOPPED" and not is_interrupt_requested():
                        self.current_state = "SPEAKING"
                        self._set_state_badge("● COMPLETE", self.CLR_WHITE, "#334155")
                    if self.wake_detector:
                        self.wake_detector.resume()

        except queue.Empty:
            pass

        # Auto-reset badge and visualizer to READY once speech finishes
        if self.current_state == "SPEAKING" and not self.tts.is_speaking():
            self.current_state = "IDLE"
            self._set_state_badge("● READY", self.CLR_EMERALD, "#059669")
            self.query_text.configure(
                text="Listening for voice... (Say 'Clanker', 'Jarvis', or 'Call')",
                text_color=self.CLR_TEXT_MUTED
            )

        self.after(35, self._drain_queue)

    def _set_state_badge(self, text: str, fg_col: str, border_col: str):
        self.state_badge.configure(text=text, text_color=fg_col, border_color=border_col)

    def _replay_last_speech(self):
        txt = self.result_box.get("1.0", "end").strip()
        if txt:
            self.tts.speak(txt)

    def _render_result(self, result_text: str, dt_ms: float):
        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.insert("end", result_text)
        self.result_box.configure(state="disabled")

        if dt_ms > 0:
            self.ticker_label.configure(text=f"✦ Executed in {dt_ms:.0f}ms | Ready for next command")

    def _play_startup_greeting(self):
        try:
            greeting = self.memory_store.generate_startup_greeting()
            self._render_result(greeting, 0)
            self.tts.speak(greeting)
        except Exception as e:
            print(f"[HUD Startup Note] {e}")


def launch_hud(assistant_instance=None):
    app = LayaHUD(assistant_instance=assistant_instance)
    app.mainloop()


if __name__ == "__main__":
    launch_hud()
