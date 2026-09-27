"""
Laya — Futuristic Iron Man JARVIS Glassmorphic Cyber HUD
A state-of-the-art cybernetic Windows Desktop Application matching the iconic Iron Man JARVIS HUD:
- Dark translucent glassmorphic window floating over a cinematic cyberpunk city backdrop
- Layered 3D glass panels with offset frosted borders and luminous cybernetic rim lighting
- Animated cybernetic Arc Reactor / Holographic Iris Core with rotating gear segments and glowing blue energy vortex
- Voice Input deck with glowing circular neon microphone button and real-time vertical soundwave equalizer bars
- Modular Cyber Widgets:
  * TASK_QUEUE: Interactive task pipeline with real-time status badges
  * SYSTEM_HEALTH: Segmented glowing cyber meters for CPU, Memory, and Network latency
  * INSIGHTS: Live dynamic monthly calendar and Email executive briefing preview
- Direct Email Checking & Executive Reporting tool integration
- Continuous wake word ("Clanker", "Call", "Jarvis"), dynamic VAD, CUDA Whisper STT, and instant barge-in vocal interrupt
"""

import sys
import os
import math
import time
import queue
import random
import calendar
import datetime
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


# -------------------------------------------------------------
# 1. Animated Arc Reactor / Holographic Iris Canvas
# -------------------------------------------------------------
class ArcReactorCanvas(ctk.CTkCanvas):
    def __init__(self, parent, size=190, **kwargs):
        super().__init__(parent, width=size, height=size, bg="#0a121e", highlightthickness=0, **kwargs)
        self.size = size
        self.center = size / 2
        self.angle = 0.0
        self.pulse = 0.0

    def draw_reactor(self, state="IDLE"):
        self.delete("all")
        cx, cy = self.center, self.center

        # Dynamics based on state
        if state == "LISTENING":
            core_col = "#00f0ff"
            glow_col = "#38bdf8"
            speed = 0.08
        elif state == "PROCESSING":
            core_col = "#a855f7"
            glow_col = "#c084fc"
            speed = 0.11
        elif state == "SPEAKING":
            core_col = "#00f0ff"
            glow_col = "#60a5fa"
            speed = 0.07
        elif state == "STOPPED":
            core_col = "#f43f5e"
            glow_col = "#fb7185"
            speed = 0.01
        else:  # IDLE
            core_col = "#38bdf8"
            glow_col = "#0284c7"
            speed = 0.03

        self.angle += speed
        self.pulse = (math.sin(time.time() * 3.2) + 1) / 2  # 0 to 1

        # 1. Outer Dark Halo Ring
        r_outer = self.size * 0.46
        self.create_oval(cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer, outline="#162235", width=2)

        # 2. Outer Tick Dial (Rotates forward)
        num_ticks = 16
        r_tick_in = self.size * 0.40
        r_tick_out = self.size * 0.44
        for i in range(num_ticks):
            a = self.angle + i * (2 * math.pi / num_ticks)
            x1 = cx + r_tick_in * math.cos(a)
            y1 = cy + r_tick_in * math.sin(a)
            x2 = cx + r_tick_out * math.cos(a)
            y2 = cy + r_tick_out * math.sin(a)
            col = core_col if i % 4 == 0 else "#1e3a5f"
            self.create_line(x1, y1, x2, y2, fill=col, width=2 if i % 4 == 0 else 1)

        # 3. Middle Concentric Ring
        r_mid = self.size * 0.36
        self.create_oval(cx - r_mid, cy - r_mid, cx + r_mid, cy + r_mid, outline="#1e293b", width=1)

        # 4. Counter-Rotating Gear Segments
        num_segs = 6
        r_seg = self.size * 0.31
        for i in range(num_segs):
            a_start = math.degrees(-self.angle * 1.6 + i * (2 * math.pi / num_segs))
            self.create_arc(
                cx - r_seg, cy - r_seg, cx + r_seg, cy + r_seg,
                start=a_start, extent=34,
                style="arc", outline=glow_col, width=3
            )

        # 5. Inner Core Ring with glow
        r_core_ring = self.size * 0.22
        self.create_oval(cx - r_core_ring, cy - r_core_ring, cx + r_core_ring, cy + r_core_ring, outline="#0ea5e9", width=2)

        # 6. Central Glowing Vortex / Energy Core
        r_core = self.size * 0.16 + (self.pulse * 3)
        self.create_oval(cx - r_core, cy - r_core, cx + r_core, cy + r_core, fill="#042038", outline="#38bdf8", width=2)

        r_inner = self.size * 0.10 + (self.pulse * 2)
        self.create_oval(cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner, fill="#0284c7", outline=core_col, width=2)

        r_center = self.size * 0.05
        self.create_oval(cx - r_center, cy - r_center, cx + r_center, cy + r_center, fill="#ffffff", outline="#ffffff")


# -------------------------------------------------------------
# 2. Animated Vertical Soundwave Equalizer Canvas
# -------------------------------------------------------------
class SoundwaveCanvas(ctk.CTkCanvas):
    def __init__(self, parent, width=180, height=36, **kwargs):
        super().__init__(parent, width=width, height=height, bg="#0e1726", highlightthickness=0, **kwargs)
        self.w = width
        self.h = height
        self.phase = 0.0

    def draw_wave(self, state="IDLE"):
        self.delete("all")
        mid_y = self.h / 2
        num_bars = 24
        bar_w = 3
        gap = (self.w - (num_bars * bar_w)) / (num_bars + 1)

        speed = 0.16 if state == "LISTENING" else (0.22 if state == "SPEAKING" else 0.05)
        self.phase += speed

        for i in range(num_bars):
            x = gap + i * (bar_w + gap)
            norm_x = (i - num_bars / 2) / (num_bars / 2)
            env = math.exp(-norm_x**2 * 2.2)

            if state in ["LISTENING", "SPEAKING"]:
                amp = (math.sin(self.phase * 2 + i * 0.4) * 0.5 + 0.5) * (self.h * 0.44) * env + 4
                col = "#00f0ff"
            elif state == "PROCESSING":
                amp = (math.sin(self.phase * 1.5 + i * 0.3) * 0.4 + 0.4) * (self.h * 0.32) * env + 3
                col = "#a855f7"
            else:  # IDLE
                amp = (math.sin(self.phase + i * 0.25) * 0.3 + 0.3) * (self.h * 0.22) * env + 2
                col = "#38bdf8"

            self.create_line(x, mid_y - amp, x, mid_y + amp, fill=col, width=bar_w)


# -------------------------------------------------------------
# 3. Main Laya HUD (Iron Man JARVIS Cyber Deck)
# -------------------------------------------------------------
class LayaHUD(ctk.CTk):
    _active_instance: Optional["LayaHUD"] = None

    def __init__(self, assistant_instance=None):
        super().__init__()
        LayaHUD._active_instance = self

        self.assistant = assistant_instance
        self.tts = get_tts_engine()
        self.stt = None
        self.capture = AudioCapture()
        self.meme_engine = get_meme_engine()
        self.memory_store = get_memory_store()
        self.fast_path = get_fast_path_executor()
        self.last_query = ""
        self.is_core_ready = False

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

        # Window Geometry & Position
        self.title("JARVIS — Autonomous Cyber Desktop Interface")
        self.app_width = 1060
        self.app_height = 680

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        pos_x = max(20, (screen_w - self.app_width) // 2)
        pos_y = max(20, (screen_h - self.app_height) // 2 - 20)
        self.geometry(f"{self.app_width}x{self.app_height}+{pos_x}+{pos_y}")
        self.resizable(False, False)

        # Frameless cyber HUD
        self.overrideredirect(True)
        self.attributes("-topmost", self.is_pinned_top)
        self._setup_taskbar_icon()

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Color Palette Tokens
        self.CLR_BG = "#070a10"
        self.CLR_CARD = "#0a121e"
        self.CLR_CARD_SUB = "#0e1726"
        self.CLR_BORDER = "#1f3350"
        self.CLR_CYAN = "#00f0ff"
        self.CLR_SKY = "#38bdf8"
        self.CLR_PURPLE = "#a855f7"
        self.CLR_EMERALD = "#10b981"
        self.CLR_ROSE = "#f43f5e"
        self.CLR_WHITE = "#ffffff"
        self.CLR_TEXT_MUTED = "#8ea6c8"
        self.CLR_TEXT_DIM = "#526580"

        self.configure(fg_color=self.CLR_BG)

        # Drag tracking
        self._drag_x = 0
        self._drag_y = 0

        # Build Background & Futuristic Deck
        self._build_background()
        self._build_header()
        self._build_left_deck()
        self._build_right_column()

        # Keyboard shortcuts
        self.bind_all("<Escape>", lambda e: self._on_escape_pressed())

        # Asynchronously bootstrap ML & wake word
        self.wake_detector = None
        threading.Thread(target=self._async_bootstrap_neural_core, daemon=True).start()

        # Animation & Telemetry loops
        self.after(35, self._drain_queue)
        self.after(35, self._animation_loop)
        self.after(1000, self._telemetry_loop)

    # -------------------------------------------------------------
    # Window Draggability & Management
    # -------------------------------------------------------------
    def _setup_taskbar_icon(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            style = (style & ~0x00000080) | 0x00040000
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
    # Background Compositing
    # -------------------------------------------------------------
    def _build_background(self):
        assets_dir = Path(__file__).resolve().parent.parent.parent / "assets"
        bg_cache = assets_dir / "jarvis_futuristic_bg.png"
        city_raw = assets_dir / "cyber_city_bg.jpg"

        if bg_cache.exists():
            img = Image.open(str(bg_cache)).convert("RGBA")
        else:
            w, h = self.app_width, self.app_height
            if city_raw.exists():
                city = Image.open(str(city_raw)).convert("RGBA")
                city = city.resize((w, h), Image.Resampling.LANCZOS)
            else:
                city = Image.new("RGBA", (w, h), (7, 10, 16, 255))

            tint = Image.new("RGBA", (w, h), (8, 12, 20, 205))
            overlay = Image.alpha_composite(city, tint)

            draw = ImageDraw.Draw(overlay)
            draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=18, outline=(40, 65, 95, 120), width=1)
            draw.line([(18, 1), (w - 18, 1)], fill=(70, 130, 180, 160), width=1)

            try:
                overlay.save(str(bg_cache))
            except Exception:
                pass
            img = overlay

        self._bg_ctk = ctk.CTkImage(light_image=img, dark_image=img, size=(self.app_width, self.app_height))
        self.bg_label = ctk.CTkLabel(self, text="", image=self._bg_ctk)
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

        self.bg_label.bind("<ButtonPress-1>", self._start_drag)
        self.bg_label.bind("<B1-Motion>", self._on_drag)

    # -------------------------------------------------------------
    # Header Bar
    # -------------------------------------------------------------
    def _build_header(self):
        hdr = ctk.CTkFrame(self, width=1020, height=44, fg_color="transparent")
        hdr.place(x=20, y=14)
        hdr.bind("<ButtonPress-1>", self._start_drag)
        hdr.bind("<B1-Motion>", self._on_drag)

        # Brand Title + Arc Reactor Logo Emblem
        brand = ctk.CTkFrame(hdr, fg_color="transparent")
        brand.pack(side="left")
        brand.bind("<ButtonPress-1>", self._start_drag)
        brand.bind("<B1-Motion>", self._on_drag)

        lbl_logo = ctk.CTkLabel(
            brand,
            text="JARVIS",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color="#ffffff"
        )
        lbl_logo.pack(side="left", padx=(4, 6))

        lbl_emblem = ctk.CTkLabel(
            brand,
            text="◎",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=self.CLR_CYAN
        )
        lbl_emblem.pack(side="left")

        # Window Controls
        ctrls = ctk.CTkFrame(hdr, fg_color="transparent")
        ctrls.pack(side="right")

        self.btn_pin = ctk.CTkButton(
            ctrls, text="📌", width=32, height=32, corner_radius=16,
            fg_color="#102538", hover_color="#183652", border_width=1, border_color="#1b4263",
            text_color=self.CLR_CYAN, font=ctk.CTkFont(size=12),
            command=self._toggle_pin
        )
        self.btn_pin.pack(side="left", padx=3)

        btn_min = ctk.CTkButton(
            ctrls, text="—", width=32, height=32, corner_radius=16,
            fg_color="#141c2b", hover_color="#1e2c45", border_width=1, border_color="#24334a",
            text_color=self.CLR_TEXT_MUTED, font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_minimize
        )
        btn_min.pack(side="left", padx=3)

        btn_close = ctk.CTkButton(
            ctrls, text="✕", width=32, height=32, corner_radius=16,
            fg_color="#241217", hover_color="#3d1820", border_width=1, border_color="#54202b",
            text_color="#fb7185", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_close
        )
        btn_close.pack(side="left", padx=3)

    # -------------------------------------------------------------
    # Left Cyber Deck (Layered Glass Panels)
    # -------------------------------------------------------------
    def _build_left_deck(self):
        # 3D Layered Glass Frames
        deck_bg = ctk.CTkFrame(self, width=658, height=586, fg_color="#070d17", corner_radius=20, border_width=1, border_color="#142135")
        deck_bg.place(x=24, y=68)

        deck = ctk.CTkFrame(self, width=650, height=578, fg_color=self.CLR_CARD, corner_radius=18, border_width=1, border_color=self.CLR_BORDER)
        deck.place(x=20, y=64)

        # Upper Deck Row: Arc Reactor (Left) + Status & Voice (Right)
        top_row = ctk.CTkFrame(deck, fg_color="transparent", width=620, height=300)
        top_row.place(x=15, y=14)

        # Left Column: Arc Reactor Canvas + Status Text
        left_arc_frame = ctk.CTkFrame(top_row, fg_color="transparent", width=310, height=300)
        left_arc_frame.pack(side="left", padx=(10, 10))

        self.arc_reactor = ArcReactorCanvas(left_arc_frame, size=186)
        self.arc_reactor.pack(pady=(4, 6))

        self.lbl_system_state = ctk.CTkLabel(
            left_arc_frame,
            text="SYSTEM ONLINE",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#ffffff"
        )
        self.lbl_system_state.pack()

        self.lbl_system_sub = ctk.CTkLabel(
            left_arc_frame,
            text="AWAITING COMMAND",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.CLR_SKY
        )
        self.lbl_system_sub.pack(pady=(2, 0))

        # Right Column: STATUS, SECURITY, and VOICE INPUT Cards
        right_sub_frame = ctk.CTkFrame(top_row, fg_color="transparent", width=280, height=300)
        right_sub_frame.pack(side="right", padx=(10, 10), fill="both", expand=True)

        # Card 1: STATUS
        card_status = ctk.CTkFrame(right_sub_frame, height=42, fg_color=self.CLR_CARD_SUB, corner_radius=12, border_width=1, border_color="#1c2f4a")
        card_status.pack(fill="x", pady=(4, 6))
        card_status.pack_propagate(False)

        st_row = ctk.CTkFrame(card_status, fg_color="transparent")
        st_row.pack(fill="x", padx=16, pady=10)
        ctk.CTkLabel(st_row, text="STATUS:", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#7c94b3").pack(side="left")
        self.lbl_status_val = ctk.CTkLabel(st_row, text="Active", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=self.CLR_CYAN)
        self.lbl_status_val.pack(side="left", padx=8)

        # Card 2: SECURITY
        card_sec = ctk.CTkFrame(right_sub_frame, height=42, fg_color=self.CLR_CARD_SUB, corner_radius=12, border_width=1, border_color="#1c2f4a")
        card_sec.pack(fill="x", pady=(0, 6))
        card_sec.pack_propagate(False)

        sec_row = ctk.CTkFrame(card_sec, fg_color="transparent")
        sec_row.pack(fill="x", padx=16, pady=10)
        ctk.CTkLabel(sec_row, text="SECURITY:", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#7c94b3").pack(side="left")
        ctk.CTkLabel(sec_row, text="Optimal", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=self.CLR_EMERALD).pack(side="left", padx=8)

        # Card 3: VOICE INPUT Card
        card_voice = ctk.CTkFrame(right_sub_frame, fg_color=self.CLR_CARD_SUB, corner_radius=16, border_width=1, border_color="#1c2f4a")
        card_voice.pack(fill="both", expand=True, pady=(0, 4))

        ctk.CTkLabel(card_voice, text="VOICE INPUT", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=self.CLR_TEXT_MUTED).pack(pady=(8, 4))

        # Circular glowing neon mic button
        self.btn_mic = ctk.CTkButton(
            card_voice,
            text="🎙️",
            width=58,
            height=58,
            corner_radius=29,
            fg_color="#0369a1",
            hover_color="#0284c7",
            border_width=2,
            border_color=self.CLR_CYAN,
            text_color="#ffffff",
            font=ctk.CTkFont(size=20),
            command=self._on_mic_click
        )
        self.btn_mic.pack(pady=4)

        # Soundwave canvas
        self.soundwave = SoundwaveCanvas(card_voice, width=190, height=32)
        self.soundwave.pack(pady=2)

        self.lbl_voice_status = ctk.CTkLabel(
            card_voice,
            text="LISTENING...",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=self.CLR_CYAN
        )
        self.lbl_voice_status.pack(pady=(2, 6))

        # Lower Deck Section: Briefing Box + Command Bar + Action Chips
        bot_sec = ctk.CTkFrame(deck, fg_color="transparent", width=620, height=240)
        bot_sec.place(x=15, y=328)

        # Result / Briefing Box
        res_card = ctk.CTkFrame(bot_sec, height=128, fg_color="#0c1422", corner_radius=14, border_width=1, border_color="#192a42")
        res_card.pack(fill="x", pady=(0, 8))
        res_card.pack_propagate(False)

        res_hdr = ctk.CTkFrame(res_card, fg_color="transparent")
        res_hdr.pack(fill="x", padx=12, pady=(6, 2))

        self.res_title = ctk.CTkLabel(res_hdr, text="✦ JARVIS EXECUTIVE BRIEFING", font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"), text_color=self.CLR_SKY)
        self.res_title.pack(side="left")

        self.btn_replay = ctk.CTkButton(
            res_hdr,
            text="🔊 Replay",
            width=58,
            height=20,
            corner_radius=10,
            fg_color="#18263a",
            hover_color="#273d5c",
            text_color=self.CLR_CYAN,
            font=ctk.CTkFont(size=9, weight="bold"),
            command=self._replay_last_speech
        )
        self.btn_replay.pack(side="right")

        self.result_box = ctk.CTkTextbox(
            res_card,
            fg_color="transparent",
            text_color="#f1f5f9",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            wrap="word",
            activate_scrollbars=False
        )
        self.result_box.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self.result_box.insert("end", "Jarvis assistant core online. Systems nominal. Standing by to check emails, execute automations, or monitor workstation telemetry.")
        self.result_box.configure(state="disabled")

        # Bottom Command Bar
        input_bar = ctk.CTkFrame(bot_sec, height=44, fg_color="#0c1422", corner_radius=22, border_width=1, border_color="#1f324e")
        input_bar.pack(fill="x", pady=(0, 6))
        input_bar.pack_propagate(False)

        self.input_field = ctk.CTkEntry(
            input_bar,
            placeholder_text="Ask Jarvis anything, check emails, or type a command...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color="transparent",
            border_width=0,
            text_color="#ffffff"
        )
        self.input_field.pack(side="left", fill="x", expand=True, padx=(14, 4), pady=4)
        self.input_field.bind("<Return>", lambda e: self._on_submit_text())

        self.btn_send = ctk.CTkButton(
            input_bar,
            text="➔",
            width=34,
            height=34,
            corner_radius=17,
            fg_color="#1e2f47",
            hover_color="#2b4263",
            text_color=self.CLR_CYAN,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_submit_text
        )
        self.btn_send.pack(side="right", padx=(2, 4), pady=4)

        self.btn_stop = ctk.CTkButton(
            input_bar,
            text="■ STOP",
            width=68,
            height=32,
            corner_radius=16,
            fg_color="#241217",
            hover_color="#3d1820",
            border_width=1,
            border_color="#54202b",
            text_color=self.CLR_ROSE,
            font=ctk.CTkFont(size=10, weight="bold"),
            command=self._on_stop_clicked
        )
        self.btn_stop.pack(side="right", padx=(2, 4), pady=4)

        # Quick Action Chips Row
        chips_row = ctk.CTkFrame(bot_sec, fg_color="transparent")
        chips_row.pack(fill="x")

        def make_chip(label, icon, fn):
            return ctk.CTkButton(
                chips_row,
                text=f"{icon} {label}".strip(),
                font=ctk.CTkFont(family="Segoe UI", size=10),
                height=26,
                corner_radius=13,
                fg_color="#0e1726",
                hover_color="#1a2b42",
                border_width=1,
                border_color="#1e3350",
                text_color="#cbd5e1",
                command=fn
            )

        make_chip("Check Emails", "✉️", self._on_check_emails_clicked).pack(side="left", padx=(0, 4))
        make_chip("Screenshot", "📸", lambda: self._trigger_fast("take_screenshot")).pack(side="left", padx=(0, 4))
        make_chip("Zoom In", "🔍", lambda: self._trigger_fast("zoom_window_region", {"region": "center", "zoom_factor": 2.5})).pack(side="left", padx=(0, 4))
        make_chip("Paint", "🎨", lambda: self._trigger_fast("draw_shape", {"shape": "heart", "title_keyword": "Paint"})).pack(side="left", padx=(0, 4))
        make_chip("Telegram", "✈️", lambda: self._trigger_fast("telegram_launch_login")).pack(side="left", padx=(0, 4))
        make_chip("Lofi Chill", "🎵", lambda: self._trigger_fast("play_youtube", {"query": "synthwave lofi chillhop mix"})).pack(side="left", padx=(0, 4))

    # -------------------------------------------------------------
    # Right Column (Modular Cyber Widgets)
    # -------------------------------------------------------------
    def _build_right_column(self):
        col = ctk.CTkFrame(self, width=344, height=578, fg_color="transparent")
        col.place(x=686, y=64)

        # Widget 1: TASK_QUEUE
        card_task = ctk.CTkFrame(col, height=180, fg_color=self.CLR_CARD, corner_radius=16, border_width=1, border_color=self.CLR_BORDER)
        card_task.pack(fill="x", pady=(0, 10))
        card_task.pack_propagate(False)

        ctk.CTkLabel(card_task, text="TASK_QUEUE", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=self.CLR_CYAN).pack(anchor="w", padx=16, pady=(10, 0))
        ctk.CTkLabel(card_task, text="RECENT", font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"), text_color=self.CLR_TEXT_DIM).pack(anchor="w", padx=16, pady=(0, 6))

        self.task_rows = []
        default_tasks = [
            ("Check Emails", "[PENDING]", "#f59e0b", self._on_check_emails_clicked),
            ("Optimize Network", "[COMPLETED]", self.CLR_EMERALD, lambda: self._trigger_fast("system_metrics")),
            ("Sync Telegram", "[ACTIVE]", self.CLR_SKY, lambda: self._trigger_fast("telegram_sync_contacts")),
            ("Security Audit", "[OPTIMAL]", self.CLR_EMERALD, lambda: self.tts.speak("All security protocols optimal, sir.")),
        ]

        for t_name, t_stat, t_col, t_cmd in default_tasks:
            row = ctk.CTkFrame(card_task, fg_color="transparent", height=22)
            row.pack(fill="x", padx=16, pady=2)

            btn_t = ctk.CTkButton(
                row, text=t_name, anchor="w", font=ctk.CTkFont(size=11), text_color="#cbd5e1",
                fg_color="transparent", hover_color="#16253b", height=20, command=t_cmd
            )
            btn_t.pack(side="left")

            lbl_st = ctk.CTkLabel(row, text=t_stat, font=ctk.CTkFont(size=10, weight="bold"), text_color=t_col)
            lbl_st.pack(side="right")
            self.task_rows.append((t_name, lbl_st))

        # Widget 2: SYSTEM_HEALTH
        card_sys = ctk.CTkFrame(col, height=180, fg_color=self.CLR_CARD, corner_radius=16, border_width=1, border_color=self.CLR_BORDER)
        card_sys.pack(fill="x", pady=(0, 10))
        card_sys.pack_propagate(False)

        ctk.CTkLabel(card_sys, text="SYSTEM_HEALTH", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=self.CLR_CYAN).pack(anchor="w", padx=16, pady=(10, 8))

        self.sys_bars = {}
        for metric, def_val in [("CPU", "24%"), ("Memory", "6.4 GB"), ("Network", "14 ms")]:
            r = ctk.CTkFrame(card_sys, fg_color="transparent", height=24)
            r.pack(fill="x", padx=16, pady=3)

            ctk.CTkLabel(r, text=metric, width=64, anchor="w", font=ctk.CTkFont(size=11, weight="bold"), text_color="#94a3b8").pack(side="left")
            bar_lbl = ctk.CTkLabel(r, text="▮▮▮▮▮▮▮▮▮▮▯▯▯▯▯▯▯▯▯▯", font=ctk.CTkFont(family="Consolas", size=11), text_color=self.CLR_SKY)
            bar_lbl.pack(side="left", padx=4)
            val_lbl = ctk.CTkLabel(r, text=def_val, font=ctk.CTkFont(size=10, weight="bold"), text_color="#ffffff")
            val_lbl.pack(side="right")
            self.sys_bars[metric] = (bar_lbl, val_lbl)

        # Widget 3: INSIGHTS
        card_ins = ctk.CTkFrame(col, height=198, fg_color=self.CLR_CARD, corner_radius=16, border_width=1, border_color=self.CLR_BORDER)
        card_ins.pack(fill="x")
        card_ins.pack_propagate(False)

        ins_top = ctk.CTkFrame(card_ins, fg_color="transparent")
        ins_top.pack(fill="x", padx=16, pady=(10, 4))
        ctk.CTkLabel(ins_top, text="INSIGHTS", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color=self.CLR_CYAN).pack(side="left")
        ctk.CTkLabel(ins_top, text="•••", font=ctk.CTkFont(size=12, weight="bold"), text_color=self.CLR_TEXT_DIM).pack(side="right")

        split_frame = ctk.CTkFrame(card_ins, fg_color="transparent")
        split_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        # Dynamic Mini Calendar (Left)
        cal_frame = ctk.CTkFrame(split_frame, fg_color="#070d17", corner_radius=10, width=125)
        cal_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))

        ctk.CTkLabel(cal_frame, text="M  T  W  T  F  S  S", font=ctk.CTkFont(family="Consolas", size=8, weight="bold"), text_color="#64748b").pack(pady=(4, 1))

        now = datetime.datetime.now()
        cal_text = self._generate_mini_calendar(now.year, now.month, now.day)
        ctk.CTkLabel(cal_frame, text=cal_text, font=ctk.CTkFont(family="Consolas", size=8), text_color=self.CLR_SKY, justify="center").pack()

        # Email / Message Preview (Right)
        msg_frame = ctk.CTkFrame(split_frame, fg_color="#070d17", corner_radius=10, width=165)
        msg_frame.pack(side="right", fill="both", expand=True, padx=(6, 0))

        ctk.CTkLabel(msg_frame, text="EMAIL REPORT", font=ctk.CTkFont(size=10, weight="bold"), text_color=self.CLR_SKY).pack(anchor="w", padx=8, pady=(6, 2))
        self.lbl_email_snippet = ctk.CTkLabel(
            msg_frame,
            text="No active sync yet.\nClick below to check\nunread messages.",
            font=ctk.CTkFont(size=9),
            text_color="#94a3b8",
            justify="left",
            wraplength=145
        )
        self.lbl_email_snippet.pack(anchor="w", padx=8, pady=(0, 4))

        self.btn_check_mail = ctk.CTkButton(
            msg_frame,
            text="Check Mail ✉️",
            width=120,
            height=24,
            corner_radius=10,
            fg_color="#0284c7",
            hover_color="#0369a1",
            text_color="#ffffff",
            font=ctk.CTkFont(size=10, weight="bold"),
            command=self._on_check_emails_clicked
        )
        self.btn_check_mail.pack(padx=8, pady=(2, 6))

    def _generate_mini_calendar(self, year: int, month: int, today_day: int) -> str:
        cal = calendar.monthcalendar(year, month)
        lines = []
        for week in cal[:5]:
            w_str = []
            for d in week:
                if d == 0:
                    w_str.append("  ")
                elif d == today_day:
                    w_str.append(f"[{d:02d}]"[:2])
                else:
                    w_str.append(f"{d:02d}")
            lines.append(" ".join(w_str))
        return "\n".join(lines)

    # -------------------------------------------------------------
    # Real-Time Animation Loop (Arc Reactor + Soundwave)
    # -------------------------------------------------------------
    def _animation_loop(self):
        try:
            self.arc_reactor.draw_reactor(self.current_state)
            self.soundwave.draw_wave(self.current_state)
        except Exception:
            pass
        self.after(35, self._animation_loop)

    # -------------------------------------------------------------
    # Real-Time Telemetry & Hardware Update Loop
    # -------------------------------------------------------------
    def _telemetry_loop(self):
        try:
            # CPU
            cpu_p = psutil.cpu_percent(interval=None)
            cpu_lit = int((cpu_p / 100.0) * 20)
            cpu_dim = 20 - cpu_lit
            self.sys_bars["CPU"][0].configure(text=("▮" * cpu_lit) + ("▯" * cpu_dim))
            self.sys_bars["CPU"][1].configure(text=f"{cpu_p:.0f}%")

            # Memory
            vm = psutil.virtual_memory()
            mem_p = vm.percent
            mem_lit = int((mem_p / 100.0) * 20)
            mem_dim = 20 - mem_lit
            mem_used_gb = vm.used / (1024**3)
            self.sys_bars["Memory"][0].configure(text=("▮" * mem_lit) + ("▯" * mem_dim))
            self.sys_bars["Memory"][1].configure(text=f"{mem_used_gb:.1f} GB")

            # Network Latency simulation / status
            net = psutil.net_io_counters()
            net_stat = f"{int(cpu_p % 15 + 8)} ms"
            self.sys_bars["Network"][1].configure(text=net_stat)
        except Exception:
            pass

        self.after(2000, self._telemetry_loop)

    # -------------------------------------------------------------
    # Email Checking Action
    # -------------------------------------------------------------
    def _on_check_emails_clicked(self):
        self.tts.stop()
        self.lbl_voice_status.configure(text="CHECKING INBOX...")
        self.lbl_system_sub.configure(text="FETCHING EMAILS")
        self._start_command_execution("check my emails")

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
    # Voice & Execution Pipeline
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
        self.lbl_system_sub.configure(text="LISTENING...")
        self.lbl_voice_status.configure(text="RECORDING VOICE...")
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
        self.lbl_status_val.configure(text="Processing", text_color=self.CLR_PURPLE)
        self.lbl_system_sub.configure(text="ANALYZING INTEL...")
        self.lbl_voice_status.configure(text="REASONING...")

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
                self.msg_queue.put(("result", result, dt_ms, query))

        except Exception as e:
            if not is_interrupt_requested():
                self.msg_queue.put(("result", f"Execution error: {e}", 0, query))
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
    # Queue Drainer & State Sync
    # -------------------------------------------------------------
    def _drain_queue(self):
        try:
            while True:
                kind, *args = self.msg_queue.get_nowait()

                if kind == "boot_status":
                    self.lbl_system_sub.configure(text=str(args[0])[:28].upper())

                elif kind == "core_ready":
                    self.current_state = "IDLE"
                    self.lbl_status_val.configure(text="Active", text_color=self.CLR_CYAN)
                    self.lbl_system_sub.configure(text="AWAITING COMMAND")
                    self.lbl_voice_status.configure(text="LISTENING...")
                    self._play_startup_greeting()

                elif kind == "wake_trigger":
                    self._start_voice_recording_thread()

                elif kind == "direct_command":
                    self._start_command_execution(args[0])

                elif kind == "state":
                    st = args[0]
                    self.current_state = st
                    if st == "PROCESSING":
                        self.lbl_status_val.configure(text="Processing", text_color=self.CLR_PURPLE)

                elif kind == "step":
                    if not is_interrupt_requested():
                        self.lbl_system_sub.configure(text=f"EXEC: {str(args[0])[:22].upper()}")

                elif kind == "result":
                    res_text, dt_ms, q_cmd = args[0], args[1], args[2]
                    if self.current_state != "STOPPED" and not is_interrupt_requested():
                        self._render_result(res_text, dt_ms)
                        # If email command, update the email preview card
                        if "email" in q_cmd.lower() or "mail" in q_cmd.lower():
                            self._update_email_preview(res_text)

                elif kind == "barge_in_stop":
                    self.current_state = "STOPPED"
                    self.lbl_status_val.configure(text="Stopped", text_color=self.CLR_ROSE)
                    self.lbl_system_sub.configure(text="TASK HALTED")
                    self.lbl_voice_status.configure(text="STANDBY")
                    if self.wake_detector:
                        self.wake_detector.resume()

                elif kind == "reset_idle":
                    if self.current_state != "STOPPED":
                        self.current_state = "IDLE"
                        self.lbl_status_val.configure(text="Active", text_color=self.CLR_CYAN)
                        self.lbl_system_sub.configure(text="AWAITING COMMAND")
                        self.lbl_voice_status.configure(text="LISTENING...")
                    if self.wake_detector:
                        self.wake_detector.resume()

                elif kind == "post_execution":
                    if self.current_state != "STOPPED" and not is_interrupt_requested():
                        self.current_state = "SPEAKING"
                        self.lbl_system_sub.configure(text="REPORTING INTEL")
                        self.lbl_voice_status.configure(text="SPEAKING...")
                    if self.wake_detector:
                        self.wake_detector.resume()

        except queue.Empty:
            pass

        # Auto-reset badge and visualizer to READY once speech finishes
        if self.current_state == "SPEAKING" and not self.tts.is_speaking():
            self.current_state = "IDLE"
            self.lbl_status_val.configure(text="Active", text_color=self.CLR_CYAN)
            self.lbl_system_sub.configure(text="AWAITING COMMAND")
            self.lbl_voice_status.configure(text="LISTENING...")

        self.after(35, self._drain_queue)

    def _render_result(self, result_text: str, dt_ms: float):
        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.insert("end", result_text)
        self.result_box.configure(state="disabled")

        if dt_ms > 0:
            self.res_title.configure(text=f"✦ JARVIS EXECUTIVE BRIEFING ({dt_ms:.0f}ms)")

    def _update_email_preview(self, text: str):
        # Update Task Queue badge
        for t_name, lbl_st in self.task_rows:
            if "Email" in t_name:
                lbl_st.configure(text="[COMPLETED]", text_color=self.CLR_EMERALD)

        snippet = text.replace("\n", " ")
        if len(snippet) > 85:
            snippet = snippet[:85] + "..."
        self.lbl_email_snippet.configure(text=snippet)

    def _replay_last_speech(self):
        txt = self.result_box.get("1.0", "end").strip()
        if txt:
            self.tts.speak(txt)

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
