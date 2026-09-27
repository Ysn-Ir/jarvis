"""
Laya Glassmorphic Desktop Application & Autonomous HUD
A state-of-the-art Glassmorphic Windows Desktop Application featuring:
- Native Windows Acrylic background blur (via pywinstyles)
- Translucent frosted glass panels, neon cyan/violet glowing accents, and crisp typography
- Dual-mode architecture: Full Desktop Application Dashboard & Compact Floating Island
- Multi-tab navigation: ✦ Assistant, ⚡ Automations, 📊 Telemetry, 🧠 Memory, ⚙️ Settings
- Real-time animated holographic audio waveform visualizer
- Single-pass continuous wake word ("Clanker", "Call", "Jarvis"), barge-in interrupt, and ReAct live streaming
"""

import sys
import os
import math
import time
import queue
import random
import threading
from typing import Optional, Callable, List, Dict, Any

# Ensure UTF-8 output
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

import customtkinter as ctk

try:
    import pywinstyles
    HAS_PYWINSTYLES = True
except ImportError:
    HAS_PYWINSTYLES = False

import psutil

from laya.audio import get_tts_engine, get_stt_engine, AudioCapture
from laya.audio.wake_word import get_wake_word_detector, WakeWordDetector
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
        self.stt = get_stt_engine()
        self.capture = AudioCapture()
        self.meme_engine = get_meme_engine()
        self.memory_store = get_memory_store()
        self.fast_path = get_fast_path_executor()
        self.last_query = ""

        # Thread Communication Queue
        self.msg_queue: queue.Queue = queue.Queue()
        self.is_recording = False
        self.is_processing = False
        self.is_island_mode = False  # False = Full App Dashboard, True = Floating Island
        self.is_pinned_top = True
        self.current_state = "IDLE"  # IDLE, LISTENING, PROCESSING, SPEAKING, STOPPED
        self._meme_dismiss_timer = None
        self._telemetry_timer = None

        # Window Appearance & Identity
        self.title("✦ LAYA — Autonomous Desktop Assistant")
        self.app_width = 840
        self.app_height = 640
        self.island_width = 460
        self.island_height = 80

        # Position centered / top-right
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        pos_x = max(40, (screen_w - self.app_width) // 2)
        pos_y = max(40, (screen_h - self.app_height) // 2 - 20)
        self.geometry(f"{self.app_width}x{self.app_height}+{pos_x}+{pos_y}")
        self.minsize(520, 560)

        # Window Topmost & Alpha
        self.attributes("-topmost", self.is_pinned_top)
        self.attributes("-alpha", 0.96)

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # -------------------------------------------------------------
        # Glassmorphism Color Palette Tokens
        # -------------------------------------------------------------
        self.CLR_BG = "#070b14"             # Deep frosted midnight void
        self.CLR_SURFACE = "#0f172a"        # Frosted glass panel
        self.CLR_CARD = "#131e33"           # Glass card surface
        self.CLR_CARD_HOVER = "#1a2942"     # Glass card hover
        self.CLR_BORDER = "#1e293b"         # Subtle crystal slate border
        self.CLR_BORDER_GLOW = "#38bdf8"    # Cyan neon glowing border
        self.CLR_CYAN = "#00f0ff"           # JARVIS Holographic Cyan
        self.CLR_PURPLE = "#a855f7"         # Cosmic Violet
        self.CLR_EMERALD = "#10b981"        # Online Ready Emerald
        self.CLR_ROSE = "#f43f5e"           # Stop / Emergency Rose
        self.CLR_WHITE = "#f8fafc"          # Pure Crystal White
        self.CLR_TEXT_MUTED = "#94a3b8"     # Frosted Ice Slate Subtext
        self.CLR_TEXT_DIM = "#64748b"       # Muted Ice Dim

        self.configure(fg_color=self.CLR_BG)

        # Apply Native Windows Acrylic Blur
        self._apply_acrylic_glass()

        # Drag tracking
        self._drag_x = 0
        self._drag_y = 0

        # Animation state for real-time waveform visualizer
        self._wave_phase = 0.0

        # Build Interface
        self._build_top_app_bar()
        self._build_main_dashboard()

        # Global hotkey bindings: ESC to interrupt & silence
        self.bind_all("<Escape>", lambda e: self._on_escape_pressed())

        # Initialize Continuous Wake Word & Barge-In Engine
        self.wake_detector: Optional[WakeWordDetector] = None
        self._init_wake_word()

        # Periodic Event & Animation Loops
        self.after(35, self._drain_queue)
        self.after(35, self._animate_waveform)
        self.after(500, self._play_startup_greeting)
        self.after(1000, self._update_telemetry_loop)

    def _apply_acrylic_glass(self):
        """Apply Windows 11/10 native Acrylic / Mica glassmorphic blur effect."""
        if HAS_PYWINSTYLES:
            try:
                pywinstyles.apply_style(self, "acrylic")
                pywinstyles.change_header_color(self, "#070b14")
            except Exception:
                try:
                    pywinstyles.apply_style(self, "mica")
                except Exception:
                    pass

    # -------------------------------------------------------------
    # 1. Custom Glassmorphic Top Application Bar
    # -------------------------------------------------------------
    def _build_top_app_bar(self):
        self.top_bar = ctk.CTkFrame(
            self,
            fg_color=self.CLR_SURFACE,
            corner_radius=18,
            border_width=1,
            border_color=self.CLR_BORDER,
            height=60,
        )
        self.top_bar.pack(fill="x", padx=12, pady=(12, 6))
        self.top_bar.pack_propagate(False)

        # Enable dragging from the top bar
        self.top_bar.bind("<Button-1>", self._start_drag)
        self.top_bar.bind("<B1-Motion>", self._on_drag)

        # Left: Brand Logo & Title
        self.brand_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.brand_frame.pack(side="left", padx=(14, 8))
        self.brand_frame.bind("<Button-1>", self._start_drag)
        self.brand_frame.bind("<B1-Motion>", self._on_drag)

        self.brand_icon = ctk.CTkLabel(
            self.brand_frame,
            text="✦",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=self.CLR_CYAN,
        )
        self.brand_icon.pack(side="left", padx=(0, 6))

        self.brand_label = ctk.CTkLabel(
            self.brand_frame,
            text="LAYA",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=self.CLR_WHITE,
        )
        self.brand_label.pack(side="left")

        # Center: Holographic Audio Waveform Visualizer
        self.canvas_wave = ctk.CTkCanvas(
            self.top_bar,
            width=140,
            height=30,
            bg=self.CLR_SURFACE,
            highlightthickness=0,
        )
        self.canvas_wave.pack(side="left", padx=10, pady=14)
        self.canvas_wave.bind("<Button-1>", self._start_drag)
        self.canvas_wave.bind("<B1-Motion>", self._on_drag)

        # State Indicator Pill (Glowing Glass Badge)
        self.state_badge = ctk.CTkLabel(
            self.top_bar,
            text="● READY",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=self.CLR_EMERALD,
            fg_color="#06281e",
            corner_radius=12,
            padx=12,
            pady=4,
        )
        self.state_badge.pack(side="left", padx=6)

        # Right Controls: Window Actions & Stop Button
        # Emergency STOP button
        self.stop_btn = ctk.CTkButton(
            self.top_bar,
            text="■ STOP",
            width=64,
            height=28,
            fg_color="#2b0e14",
            hover_color="#45121e",
            text_color=self.CLR_ROSE,
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            corner_radius=14,
            border_width=1,
            border_color="#7f1d1d",
            command=self._on_stop_clicked,
        )
        self.stop_btn.pack(side="right", padx=(4, 12))

        # Close Button
        self.close_btn = ctk.CTkButton(
            self.top_bar,
            text="✕",
            width=30,
            height=28,
            fg_color="#1e293b",
            hover_color="#e11d48",
            text_color=self.CLR_TEXT_MUTED,
            font=ctk.CTkFont(size=11, weight="bold"),
            corner_radius=14,
            command=self._on_close,
        )
        self.close_btn.pack(side="right", padx=2)

        # Minimize Button
        self.min_btn = ctk.CTkButton(
            self.top_bar,
            text="─",
            width=30,
            height=28,
            fg_color="#1e293b",
            hover_color="#334155",
            text_color=self.CLR_TEXT_MUTED,
            font=ctk.CTkFont(size=11, weight="bold"),
            corner_radius=14,
            command=self._on_minimize,
        )
        self.min_btn.pack(side="right", padx=2)

        # Island Mode Toggle Button
        self.island_btn = ctk.CTkButton(
            self.top_bar,
            text="🗖 Island",
            width=70,
            height=28,
            fg_color="#1e293b",
            hover_color="#38bdf8",
            text_color=self.CLR_TEXT_MUTED,
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            corner_radius=14,
            command=self._toggle_island_mode,
        )
        self.island_btn.pack(side="right", padx=2)

        # Pin / Always on Top Toggle
        self.pin_btn = ctk.CTkButton(
            self.top_bar,
            text="📌 Pinned",
            width=68,
            height=28,
            fg_color="#0e3a47",
            hover_color="#164e63",
            text_color=self.CLR_CYAN,
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            corner_radius=14,
            command=self._toggle_pin,
        )
        self.pin_btn.pack(side="right", padx=2)

    # -------------------------------------------------------------
    # 2. Main Glassmorphic Multi-Tab Dashboard
    # -------------------------------------------------------------
    def _build_main_dashboard(self):
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Styled Glassmorphic Tabview
        self.tabview = ctk.CTkTabview(
            self.main_container,
            fg_color=self.CLR_SURFACE,
            segmented_button_fg_color="#0a101d",
            segmented_button_selected_color="#1e293b",
            segmented_button_selected_hover_color="#273549",
            segmented_button_unselected_color="#0f172a",
            segmented_button_unselected_hover_color="#162035",
            corner_radius=16,
            border_width=1,
            border_color=self.CLR_BORDER,
        )
        self.tabview.pack(fill="both", expand=True)

        # Create Tabs
        self.tab_assistant = self.tabview.add("🎙️ Assistant")
        self.tab_automations = self.tabview.add("⚡ Automations")
        self.tab_telemetry = self.tabview.add("📊 Telemetry")
        self.tab_memory = self.tabview.add("🧠 Memory")
        self.tab_settings = self.tabview.add("⚙️ Settings")

        # Build individual tabs
        self._build_tab_assistant()
        self._build_tab_automations()
        self._build_tab_telemetry()
        self._build_tab_memory()
        self._build_tab_settings()

    # -------------------------------------------------------------
    # Tab 1: Assistant (Voice HUD & Interactive Chat Console)
    # -------------------------------------------------------------
    def _build_tab_assistant(self):
        tab = self.tab_assistant

        # User Query Glass Card
        self.query_card = ctk.CTkFrame(
            tab,
            fg_color=self.CLR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=self.CLR_BORDER,
        )
        self.query_card.pack(fill="x", padx=10, pady=(6, 8))

        self.query_label_header = ctk.CTkLabel(
            self.query_card,
            text="🗣️ VOICE INTEL / USER COMMAND",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=self.CLR_CYAN,
        )
        self.query_label_header.pack(anchor="w", padx=14, pady=(8, 2))

        self.query_text = ctk.CTkLabel(
            self.query_card,
            text="Listening for voice... (Say 'Clanker', 'Jarvis', or 'Call')",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=self.CLR_WHITE,
            wraplength=760,
            justify="left",
        )
        self.query_text.pack(fill="x", anchor="w", padx=14, pady=(2, 10))

        # Middle Splitted Area: Live Steps (Left) + Final Result (Right)
        self.middle_frame = ctk.CTkFrame(tab, fg_color="transparent")
        self.middle_frame.pack(fill="both", expand=True, padx=10, pady=4)
        self.middle_frame.columnconfigure(0, weight=1)
        self.middle_frame.columnconfigure(1, weight=1)
        self.middle_frame.rowconfigure(0, weight=1)

        # Left: Live ReAct Execution Steps
        self.step_card = ctk.CTkFrame(
            self.middle_frame,
            fg_color=self.CLR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=self.CLR_BORDER,
        )
        self.step_card.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        self.step_header = ctk.CTkLabel(
            self.step_card,
            text="✦ LIVE ACTIONS & REASONING",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=self.CLR_CYAN,
        )
        self.step_header.pack(anchor="w", padx=12, pady=(8, 4))

        self.step_box = ctk.CTkTextbox(
            self.step_card,
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=self.CLR_TEXT_MUTED,
            fg_color="#0a101d",
            corner_radius=10,
            border_width=0,
            wrap="word",
        )
        self.step_box.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.step_box.insert("end", "[System] Ready for voice commands or chat input.\n")
        self.step_box.configure(state="disabled")

        # Right: Final Spoken Answer / Output
        self.result_card = ctk.CTkFrame(
            self.middle_frame,
            fg_color=self.CLR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=self.CLR_BORDER,
        )
        self.result_card.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        self.result_header_frame = ctk.CTkFrame(self.result_card, fg_color="transparent")
        self.result_header_frame.pack(fill="x", padx=12, pady=(8, 4))

        self.result_header = ctk.CTkLabel(
            self.result_header_frame,
            text="✦ JARVIS RESPONSE",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=self.CLR_PURPLE,
        )
        self.result_header.pack(side="left")

        self.replay_btn = ctk.CTkButton(
            self.result_header_frame,
            text="🔊 Replay",
            width=58,
            height=20,
            fg_color="#1e293b",
            hover_color="#334155",
            font=ctk.CTkFont(size=9, weight="bold"),
            corner_radius=10,
            command=self._replay_last_speech,
        )
        self.replay_btn.pack(side="right", padx=2)

        self.result_box = ctk.CTkTextbox(
            self.result_card,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=self.CLR_WHITE,
            fg_color="#0a101d",
            corner_radius=10,
            border_width=0,
            wrap="word",
        )
        self.result_box.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.result_box.insert("end", "I am standing by to assist with your machine and automated workflows.")
        self.result_box.configure(state="disabled")

        # Bottom: Glassmorphic Interactive Input Bar
        self.input_card = ctk.CTkFrame(
            tab,
            fg_color=self.CLR_CARD,
            corner_radius=16,
            border_width=1,
            border_color=self.CLR_BORDER,
            height=54,
        )
        self.input_card.pack(fill="x", padx=10, pady=(6, 8))
        self.input_card.pack_propagate(False)

        # Mic Toggle Button
        self.mic_btn = ctk.CTkButton(
            self.input_card,
            text="🎙️",
            width=38,
            height=38,
            fg_color="#0e3a47",
            hover_color="#0891b2",
            text_color=self.CLR_CYAN,
            font=ctk.CTkFont(size=15),
            corner_radius=19,
            border_width=1,
            border_color="#155e75",
            command=self._on_mic_click,
        )
        self.mic_btn.pack(side="left", padx=(8, 6), pady=8)

        # Text Input Field
        self.input_field = ctk.CTkEntry(
            self.input_card,
            placeholder_text="Ask or command Laya (e.g. 'zoom in the corner', 'scroll down', 'draw a heart')...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#0a101d",
            text_color=self.CLR_WHITE,
            border_width=1,
            border_color=self.CLR_BORDER,
            corner_radius=12,
        )
        self.input_field.pack(side="left", fill="x", expand=True, padx=6, pady=8)
        self.input_field.bind("<Return>", lambda e: self._on_submit_text())

        # Send Button
        self.send_btn = ctk.CTkButton(
            self.input_card,
            text="Send ⏎",
            width=76,
            height=38,
            fg_color="#1d4ed8",
            hover_color="#2563eb",
            text_color=self.CLR_WHITE,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            corner_radius=12,
            command=self._on_submit_text,
        )
        self.send_btn.pack(side="right", padx=(4, 8), pady=8)

    # -------------------------------------------------------------
    # Tab 2: Automations (Instant One-Click Action Cards)
    # -------------------------------------------------------------
    def _build_tab_automations(self):
        tab = self.tab_automations

        scroll_frame = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll_frame.pack(fill="both", expand=True, padx=8, pady=8)

        actions = [
            ("📸 Capture Screenshot", "Save desktop screenshot & open immediately", "take_screenshot", lambda: self._trigger_fast("take_screenshot")),
            ("🔍 Zoom Corner", "Zoom in 2.5× into the corner in floating preview", "zoom_corner", lambda: self._trigger_fast("zoom_window_region", {"region": "corner", "zoom_factor": 2.5})),
            ("🔍 Zoom Center", "Magnify middle of the screen in floating HUD", "zoom_center", lambda: self._trigger_fast("zoom_window_region", {"region": "center", "zoom_factor": 2.5})),
            ("🎨 Draw Heart in Paint", "Open MS Paint & smoothly sketch a geometric heart", "draw_heart", lambda: self._trigger_fast("draw_shape", {"shape": "heart", "title_keyword": "Paint"})),
            ("🎨 Draw Star in Paint", "Open MS Paint & draw a five-point star", "draw_star", lambda: self._trigger_fast("draw_shape", {"shape": "star", "title_keyword": "Paint"})),
            ("📝 Quick Notepad Essay", "Generate and type cyber security notes in Notepad", "write_note", lambda: self._start_command_execution("write an essay about cyber security into notepad")),
            ("🎵 Play Chillhop Music", "Launch YouTube and auto-play top synthwave mix", "play_lofi", lambda: self._trigger_fast("play_youtube", {"query": "synthwave lofi chillhop mix"})),
            ("🗔 Tile Windows (Split)", "Organize desktop open windows into split screen", "split_win", lambda: self._trigger_fast("split_screen", {"layout": "split"})),
            ("🗔 Tile Windows (Grid)", "Arrange open application windows into a 2x2 grid", "grid_win", lambda: self._trigger_fast("split_screen", {"layout": "grid"})),
            ("🔒 Lock Workstation", "Lock your Windows workstation immediately", "lock_pc", lambda: self._trigger_fast("lock_workstation")),
            ("🌐 Open Google", "Launch default browser directly to Google search", "open_google", lambda: self._trigger_fast("browser_open_url", {"url": "https://google.com"})),
            ("🔋 Check Battery Life", "Inspect real-time laptop battery percentage and status", "check_battery", lambda: self._trigger_fast("check_battery")),
        ]

        # 2-Column Responsive Grid
        scroll_frame.columnconfigure(0, weight=1)
        scroll_frame.columnconfigure(1, weight=1)

        for idx, (title, desc, key, fn) in enumerate(actions):
            r = idx // 2
            c = idx % 2
            card = ctk.CTkFrame(
                scroll_frame,
                fg_color=self.CLR_CARD,
                corner_radius=14,
                border_width=1,
                border_color=self.CLR_BORDER,
                height=90,
            )
            card.grid(row=r, column=c, sticky="nsew", padx=6, pady=6)
            card.pack_propagate(False)

            t_lbl = ctk.CTkLabel(
                card,
                text=title,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color=self.CLR_WHITE,
            )
            t_lbl.pack(anchor="w", padx=12, pady=(8, 2))

            d_lbl = ctk.CTkLabel(
                card,
                text=desc,
                font=ctk.CTkFont(family="Segoe UI", size=10),
                text_color=self.CLR_TEXT_MUTED,
                wraplength=340,
                justify="left",
            )
            d_lbl.pack(anchor="w", padx=12, pady=(0, 6))

            btn = ctk.CTkButton(
                card,
                text="Execute ⚡",
                width=80,
                height=22,
                fg_color="#1e293b",
                hover_color="#0284c7",
                text_color=self.CLR_CYAN,
                font=ctk.CTkFont(size=10, weight="bold"),
                corner_radius=8,
                command=fn,
            )
            btn.pack(side="right", padx=10, pady=(0, 8))

    # -------------------------------------------------------------
    # Tab 3: Telemetry (Hardware & System Diagnostics)
    # -------------------------------------------------------------
    def _build_tab_telemetry(self):
        tab = self.tab_telemetry

        self.telemetry_container = ctk.CTkFrame(tab, fg_color="transparent")
        self.telemetry_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.telemetry_container.columnconfigure(0, weight=1)
        self.telemetry_container.columnconfigure(1, weight=1)

        # Gauge Cards
        self.cpu_card = self._create_metric_card(self.telemetry_container, 0, 0, "💻 CPU UTILIZATION", "0%", "#0284c7")
        self.ram_card = self._create_metric_card(self.telemetry_container, 0, 1, "🧠 RAM USAGE", "0 / 0 GB", "#8b5cf6")
        self.bat_card = self._create_metric_card(self.telemetry_container, 1, 0, "🔋 BATTERY STATUS", "Checking...", "#10b981")
        self.disk_card = self._create_metric_card(self.telemetry_container, 1, 1, "💾 DISK STORAGE", "0% used", "#f59e0b")

        # Network & GPU card
        self.info_card = ctk.CTkFrame(
            self.telemetry_container,
            fg_color=self.CLR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=self.CLR_BORDER,
        )
        self.info_card.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=6, pady=8)

        ctk.CTkLabel(
            self.info_card,
            text="✦ HARDWARE & ENGINE STATUS",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.CLR_CYAN,
        ).pack(anchor="w", padx=14, pady=(10, 4))

        self.info_text = ctk.CTkLabel(
            self.info_card,
            text="GPU: NVIDIA GeForce RTX 4050 Laptop GPU (CUDA Float16 Accelerated)\n"
                 "STT: faster-whisper (base.en with Silero VAD)\n"
                 "Reasoning Engine: Groq Ultra-Fast API (openai/gpt-oss-20b)\n"
                 "Wake Engine: Multi-phrase Barge-In Spying Active",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=self.CLR_WHITE,
            justify="left",
        )
        self.info_text.pack(fill="x", anchor="w", padx=14, pady=(2, 12))

    def _create_metric_card(self, parent, r, c, title, initial_val, color):
        card = ctk.CTkFrame(
            parent,
            fg_color=self.CLR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=self.CLR_BORDER,
            height=110,
        )
        card.grid(row=r, column=c, sticky="nsew", padx=6, pady=6)
        card.pack_propagate(False)

        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=color,
        ).pack(anchor="w", padx=14, pady=(10, 2))

        val_lbl = ctk.CTkLabel(
            card,
            text=initial_val,
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=self.CLR_WHITE,
        )
        val_lbl.pack(anchor="w", padx=14, pady=(4, 8))

        card.val_label = val_lbl
        return card

    def _update_telemetry_loop(self):
        try:
            # CPU
            cpu_p = psutil.cpu_percent(interval=None)
            if hasattr(self, "cpu_card"):
                self.cpu_card.val_label.configure(text=f"{cpu_p:.1f}%")

            # RAM
            vm = psutil.virtual_memory()
            ram_used_gb = vm.used / (1024**3)
            ram_total_gb = vm.total / (1024**3)
            if hasattr(self, "ram_card"):
                self.ram_card.val_label.configure(text=f"{ram_used_gb:.1f} / {ram_total_gb:.1f} GB ({vm.percent}%)")

            # Battery
            bat = psutil.sensors_battery()
            if hasattr(self, "bat_card"):
                if bat:
                    status = "⚡ Charging" if bat.power_plugged else "🔋 Discharging"
                    self.bat_card.val_label.configure(text=f"{bat.percent}% ({status})")
                else:
                    self.bat_card.val_label.configure(text="Desktop / AC Powered")

            # Disk
            disk = psutil.disk_usage("C:\\")
            if hasattr(self, "disk_card"):
                self.disk_card.val_label.configure(text=f"{disk.percent}% Used ({disk.free // (1024**3)} GB Free)")

        except Exception:
            pass

        self.after(2500, self._update_telemetry_loop)

    # -------------------------------------------------------------
    # Tab 4: Memory (Saved Facts & Context)
    # -------------------------------------------------------------
    def _build_tab_memory(self):
        tab = self.tab_memory

        header_frame = ctk.CTkFrame(tab, fg_color="transparent")
        header_frame.pack(fill="x", padx=12, pady=(10, 6))

        ctk.CTkLabel(
            header_frame,
            text="✦ DURABLE MEMORY (Mem0-Style Extracted Facts)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.CLR_CYAN,
        ).pack(side="left")

        ctk.CTkButton(
            header_frame,
            text="↻ Refresh",
            width=70,
            height=24,
            fg_color="#1e293b",
            hover_color="#334155",
            font=ctk.CTkFont(size=10, weight="bold"),
            corner_radius=10,
            command=self._refresh_memory_view,
        ).pack(side="right")

        self.memory_box = ctk.CTkTextbox(
            tab,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=self.CLR_WHITE,
            fg_color="#0a101d",
            corner_radius=12,
            border_width=1,
            border_color=self.CLR_BORDER,
            wrap="word",
        )
        self.memory_box.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self._refresh_memory_view()

        # Add Fact Frame
        add_frame = ctk.CTkFrame(tab, fg_color=self.CLR_CARD, corner_radius=14, border_width=1, border_color=self.CLR_BORDER)
        add_frame.pack(fill="x", padx=12, pady=(0, 10))

        self.mem_input = ctk.CTkEntry(
            add_frame,
            placeholder_text="Add durable fact (e.g. 'User prefers meetings after 10am')...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="#0a101d",
            border_width=0,
        )
        self.mem_input.pack(side="left", fill="x", expand=True, padx=10, pady=8)
        self.mem_input.bind("<Return>", lambda e: self._on_add_memory())

        ctk.CTkButton(
            add_frame,
            text="+ Remember",
            width=90,
            height=32,
            fg_color="#10b981",
            hover_color="#059669",
            text_color=self.CLR_WHITE,
            font=ctk.CTkFont(size=11, weight="bold"),
            corner_radius=10,
            command=self._on_add_memory,
        ).pack(side="right", padx=8, pady=8)

    def _refresh_memory_view(self):
        try:
            summary = self.memory_store.get_all_summary()
            self.memory_box.configure(state="normal")
            self.memory_box.delete("1.0", "end")
            self.memory_box.insert("end", summary)
            self.memory_box.configure(state="disabled")
        except Exception as e:
            self.memory_box.configure(state="normal")
            self.memory_box.delete("1.0", "end")
            self.memory_box.insert("end", f"Error loading memory facts: {e}")
            self.memory_box.configure(state="disabled")

    def _on_add_memory(self):
        txt = self.mem_input.get().strip()
        if txt:
            self.memory_store.add_fact(txt)
            self.mem_input.delete(0, "end")
            self._refresh_memory_view()

    # -------------------------------------------------------------
    # Tab 5: Settings & Configuration
    # -------------------------------------------------------------
    def _build_tab_settings(self):
        tab = self.tab_settings

        scroll_settings = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        scroll_settings.pack(fill="both", expand=True, padx=10, pady=10)

        # 1. Wake Phrases Section
        f1 = ctk.CTkFrame(scroll_settings, fg_color=self.CLR_CARD, corner_radius=14, border_width=1, border_color=self.CLR_BORDER)
        f1.pack(fill="x", pady=6)

        ctk.CTkLabel(f1, text="🎙️ WAKE WORDS & VOICE TRIGGERS", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=self.CLR_CYAN).pack(anchor="w", padx=14, pady=(10, 4))
        phrases_str = ", ".join(WAKE_PHRASES)
        ctk.CTkLabel(f1, text=f"Active Wake Phrases: {phrases_str}\n(Say any phrase followed by your command for single-pass instant execution)", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=self.CLR_TEXT_MUTED, justify="left").pack(anchor="w", padx=14, pady=(2, 10))

        # 2. Audio Engine
        f2 = ctk.CTkFrame(scroll_settings, fg_color=self.CLR_CARD, corner_radius=14, border_width=1, border_color=self.CLR_BORDER)
        f2.pack(fill="x", pady=6)

        ctk.CTkLabel(f2, text="⚡ NEURAL AUDIO PIPELINE", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=self.CLR_PURPLE).pack(anchor="w", padx=14, pady=(10, 4))
        ctk.CTkLabel(f2, text="STT Model: faster-whisper 'base.en' (CUDA float16, ~25ms latency)\n"
                             "VAD Engine: Silero VAD (Noise filtering & Hallucination rejection active)\n"
                             "TTS Voice: en-US-ChristopherNeural (Edge-TTS / SAPI5 fallback)",
                     font=ctk.CTkFont(family="Segoe UI", size=11), text_color=self.CLR_TEXT_MUTED, justify="left").pack(anchor="w", padx=14, pady=(2, 6))

        ctk.CTkButton(f2, text="Test Voice Speech 🔊", width=140, height=28, fg_color="#1e293b", hover_color="#334155", font=ctk.CTkFont(size=10, weight="bold"), corner_radius=10, command=lambda: self.tts.speak("JARVIS online and fully operational.")).pack(anchor="w", padx=14, pady=(2, 10))

        # 3. LLM Reasoning Backend
        f3 = ctk.CTkFrame(scroll_settings, fg_color=self.CLR_CARD, corner_radius=14, border_width=1, border_color=self.CLR_BORDER)
        f3.pack(fill="x", pady=6)

        ctk.CTkLabel(f3, text="🧠 CLOUD & LOCAL REASONING BACKEND", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=self.CLR_EMERALD).pack(anchor="w", padx=14, pady=(10, 4))
        ctk.CTkLabel(f3, text="Primary Cloud: Groq (openai/gpt-oss-20b) with CORE_TOOLS_SCHEMA (~1,400 tokens)\n"
                             "Fallback Cloud: Groq (qwen/qwen3.8-27b)\n"
                             "Private Local: Ollama (mistral:7b at localhost:11434)\n"
                             "Single-Instance Lock: Active on local port 49876",
                     font=ctk.CTkFont(family="Segoe UI", size=11), text_color=self.CLR_TEXT_MUTED, justify="left").pack(anchor="w", padx=14, pady=(2, 10))

    # -------------------------------------------------------------
    # 3. Mode Toggling (Full Application vs Floating Island)
    # -------------------------------------------------------------
    def _toggle_island_mode(self):
        if self.is_island_mode:
            # Switch to Full Application Dashboard
            self.is_island_mode = False
            self.main_container.pack(fill="both", expand=True, padx=12, pady=(0, 12))
            self.island_btn.configure(text="🗖 Island")
            self.geometry(f"{self.app_width}x{self.app_height}")
        else:
            # Switch to Compact Floating Island
            self.is_island_mode = True
            self.main_container.pack_forget()
            self.island_btn.configure(text="🗖 Full App")
            screen_w = self.winfo_screenwidth()
            pos_x = max(20, screen_w - self.island_width - 30)
            self.geometry(f"{self.island_width}x{self.island_height}+{pos_x}+30")

    def _toggle_pin(self):
        self.is_pinned_top = not self.is_pinned_top
        self.attributes("-topmost", self.is_pinned_top)
        if self.is_pinned_top:
            self.pin_btn.configure(text="📌 Pinned", fg_color="#0e3a47", text_color=self.CLR_CYAN)
        else:
            self.pin_btn.configure(text="📌 Unpinned", fg_color="#1e293b", text_color=self.CLR_TEXT_MUTED)

    def _on_minimize(self):
        self.iconify()

    def _on_close(self):
        # Clean shutdown: Stop audio, close wake detector, exit cleanly
        try:
            self.tts.stop()
            if self.wake_detector:
                self.wake_detector.stop()
        except Exception:
            pass
        self.destroy()
        sys.exit(0)

    def _trigger_fast(self, action: str, params: Optional[dict] = None):
        params = params or {}
        self.tabview.set("🎙️ Assistant")
        handler = getattr(self.fast_path, action, None)
        if handler:
            try:
                res = handler(**params)
                self._render_result(str(res), 50.0)
                self.tts.speak(str(res))
            except Exception as e:
                self._render_result(f"Action error: {e}", 0)

    # -------------------------------------------------------------
    # 4. Animated Holographic Waveform
    # -------------------------------------------------------------
    def _animate_waveform(self):
        try:
            self.canvas_wave.delete("all")
            w = 140
            h = 30
            mid_y = h / 2

            # Dynamics based on state
            if self.current_state == "LISTENING":
                amp = 10.0
                freq = 0.22
                speed = 0.35
                color = self.CLR_CYAN
            elif self.current_state == "PROCESSING":
                amp = 7.0
                freq = 0.35
                speed = 0.45
                color = self.CLR_PURPLE
            elif self.current_state == "SPEAKING":
                amp = 12.0
                freq = 0.18
                speed = 0.40
                color = self.CLR_CYAN
            elif self.current_state == "STOPPED":
                amp = 2.0
                freq = 0.10
                speed = 0.05
                color = self.CLR_ROSE
            else:  # IDLE
                amp = 3.5
                freq = 0.12
                speed = 0.10
                color = "#22d3ee"

            self._wave_phase += speed

            # Draw glowing multi-harmonic sine waves
            points_1 = []
            points_2 = []
            for x in range(0, w, 3):
                y1 = mid_y + math.sin(x * freq + self._wave_phase) * amp
                y2 = mid_y + math.cos(x * (freq * 0.7) - self._wave_phase) * (amp * 0.6)
                points_1.append((x, y1))
                points_2.append((x, y2))

            for i in range(len(points_1) - 1):
                self.canvas_wave.create_line(points_1[i][0], points_1[i][1], points_1[i+1][0], points_1[i+1][1], fill=color, width=2)
                self.canvas_wave.create_line(points_2[i][0], points_2[i][1], points_2[i+1][0], points_2[i+1][1], fill="#38bdf8", width=1)

        except Exception:
            pass

        self.after(35, self._animate_waveform)

    # -------------------------------------------------------------
    # 5. Drag & Window Move Logic
    # -------------------------------------------------------------
    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        x = self.winfo_x() + (event.x - self._drag_x)
        y = self.winfo_y() + (event.y - self._drag_y)
        self.geometry(f"+{x}+{y}")

    # -------------------------------------------------------------
    # 6. Wake Word & Barge-In Listeners
    # -------------------------------------------------------------
    def _init_wake_word(self):
        try:
            self.wake_detector = get_wake_word_detector(
                on_wake=self._on_wake_heard,
                on_command=self._on_direct_command_heard,
                on_interrupt=self._on_interrupt_requested,
            )
            self.wake_detector.start()
        except Exception as e:
            print(f"[HUD] Wake word note: {e}")

    def _on_interrupt_requested(self):
        print("[HUD] Interruption vocal trigger received: aborting and silencing.")
        request_interrupt("Vocal interruption")
        self.tts.stop()
        self.msg_queue.put(("barge_in_stop", None))

    def _on_stop_clicked(self):
        print("[HUD] STOP button clicked: aborting.")
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
        self._set_state_badge("● LISTENING", self.CLR_CYAN, "#06283b")
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
        self._set_state_badge("● PROCESSING", self.CLR_PURPLE, "#230f38")
        self.query_text.configure(text=f"\"{query}\"", text_color=self.CLR_WHITE)

        threading.Thread(target=lambda: self._execute_task_worker(query), daemon=True).start()

    def _execute_task_worker(self, query: str):
        self.is_processing = True
        t0 = time.time()
        try:
            def on_step(step_msg: str):
                self.msg_queue.put(("step", step_msg))

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

    # -------------------------------------------------------------
    # 7. Thread-Safe Event Drainer
    # -------------------------------------------------------------
    def _drain_queue(self):
        try:
            while True:
                kind, *args = self.msg_queue.get_nowait()

                if kind == "wake_trigger":
                    self._start_voice_recording_thread()

                elif kind == "direct_command":
                    cmd = args[0]
                    self._start_command_execution(cmd)

                elif kind == "state":
                    st = args[0]
                    self.current_state = st
                    if st == "PROCESSING":
                        self._set_state_badge("● PROCESSING", self.CLR_PURPLE, "#230f38")

                elif kind == "step":
                    if not is_interrupt_requested():
                        self._append_step(str(args[0]))

                elif kind == "result":
                    res_text, dt_ms = args[0], args[1]
                    if self.current_state != "STOPPED" and not is_interrupt_requested():
                        self._render_result(res_text, dt_ms)

                elif kind == "barge_in_stop":
                    self.current_state = "STOPPED"
                    self._set_state_badge("● STOPPED", self.CLR_ROSE, "#2e0811")
                    self.query_text.configure(text="Stopped. Listening...", text_color=self.CLR_WHITE)
                    if self.wake_detector:
                        self.wake_detector.resume()

                elif kind == "reset_idle":
                    if self.current_state != "STOPPED":
                        self.current_state = "IDLE"
                        self._set_state_badge("● READY", self.CLR_EMERALD, "#06281e")
                        self.query_text.configure(text="Listening for voice... (Say 'Clanker', 'Jarvis', or 'Call')", text_color=self.CLR_TEXT_MUTED)
                    if self.wake_detector:
                        self.wake_detector.resume()

                elif kind == "post_execution":
                    if self.current_state != "STOPPED" and not is_interrupt_requested():
                        self.current_state = "SPEAKING"
                        self._set_state_badge("● COMPLETE", self.CLR_WHITE, "#1e293b")
                    if self.wake_detector:
                        self.wake_detector.resume()

        except queue.Empty:
            pass

        # Auto-reset badge and visualizer to READY once speech finishes
        if self.current_state == "SPEAKING" and not self.tts.is_speaking():
            self.current_state = "IDLE"
            self._set_state_badge("● READY", self.CLR_EMERALD, "#06281e")
            self.query_text.configure(text="Listening for voice... (Say 'Clanker', 'Jarvis', or 'Call')", text_color=self.CLR_TEXT_MUTED)

        self.after(35, self._drain_queue)

    def _set_state_badge(self, text: str, fg: str, bg: str):
        self.state_badge.configure(text=text, text_color=fg, fg_color=bg)

    def _append_step(self, step_text: str):
        self.step_box.configure(state="normal")
        t_str = time.strftime("%H:%M:%S")
        self.step_box.insert("end", f"[{t_str}] {step_text}\n")
        self.step_box.see("end")
        self.step_box.configure(state="disabled")

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
            self.step_header.configure(text=f"✦ LIVE ACTIONS ({dt_ms:.0f}ms)")

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
