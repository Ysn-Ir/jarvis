"""
Laya Monochromatic Luxury Glass HUD
State-of-the-art minimal transparent interface (Obsidian Black, Charcoal Gray, and Pure White).
Features:
- True translucent smoky glass window (-alpha 0.88, #07070a deep obsidian black, zero white artifacts)
- Prominent fluid holographic multi-harmonic sine wave visualizer (410x74px) with Gaussian amplitude envelope
- Real-time animated pulsing status beacon and pulsing mic aura
- Eased height transition animation between Full HUD (450x540) & Compact Floating Island (450x64)
- Single-pass continuous wake word ("Clanker", "Call", "Jarvis"), dynamic VAD, and instant barge-in vocal interrupt
- Native Email Checking & Executive Reporting integration (voice & one-click chip)
- Minimalist frosted action chips, live step streaming, and multi-turn response readout
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

# Ensure CTk appearance mode is strictly Dark BEFORE creating any widgets
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

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
# 1. Prominent Fluid Holographic Multi-Harmonic Waveform Canvas
# -------------------------------------------------------------
class ProminentFluidWaveform(ctk.CTkCanvas):
    def __init__(self, parent, width=410, height=72, **kwargs):
        super().__init__(parent, width=width, height=height, bg="#0d0d12", highlightthickness=0, **kwargs)
        self.w = width
        self.h = height
        self.phase = 0.0

    def draw_wave(self, state="IDLE"):
        self.delete("all")
        mid_y = self.h / 2
        w = self.w

        if state == "LISTENING":
            speed = 0.18
            amp1 = 20.0
            amp2 = 13.0
            amp3 = 8.0
        elif state == "PROCESSING":
            speed = 0.22
            amp1 = 14.0
            amp2 = 9.0
            amp3 = 6.0
        elif state == "SPEAKING":
            speed = 0.16
            amp1 = 22.0
            amp2 = 14.0
            amp3 = 9.0
        elif state == "STOPPED":
            speed = 0.02
            amp1 = 3.0
            amp2 = 2.0
            amp3 = 1.0
        else:  # IDLE
            speed = 0.05
            amp1 = 8.0
            amp2 = 5.0
            amp3 = 3.0

        self.phase += speed

        # 4 Layered Harmonic Sine Waves with Gaussian Bell-Curve Envelope
        pts1 = []
        pts2 = []
        pts3 = []
        pts4 = []

        step = 4
        for x in range(0, w + step, step):
            nx = (2.0 * x / w) - 1.0
            env = math.exp(-2.5 * (nx ** 2))

            y1 = mid_y + math.sin(x * 0.045 + self.phase) * amp1 * env
            y2 = mid_y + math.cos(x * 0.035 - self.phase * 0.85) * amp2 * env
            y3 = mid_y + math.sin(x * 0.060 + self.phase * 1.3) * amp3 * env
            y4 = mid_y + math.cos(x * 0.080 - self.phase * 1.1) * (amp3 * 0.7) * env

            pts1.extend([x, y1])
            pts2.extend([x, y2])
            pts3.extend([x, y3])
            pts4.extend([x, y4])

        # Deep ambient wave
        if len(pts4) >= 4:
            self.create_line(pts4, fill="#202028", width=1, smooth=True)
        # Mid slate wave
        if len(pts3) >= 4:
            self.create_line(pts3, fill="#363642", width=1, smooth=True)
        # Platinum secondary wave
        if len(pts2) >= 4:
            self.create_line(pts2, fill="#a1a1aa", width=1.5, smooth=True)
        # Pure white primary wave
        if len(pts1) >= 4:
            col = "#ffffff" if state in ["LISTENING", "SPEAKING"] else "#e4e4e7"
            if state == "STOPPED":
                col = "#f43f5e"
            self.create_line(pts1, fill=col, width=2, smooth=True)


# -------------------------------------------------------------
# 2. Main Laya Monochromatic Luxury Glass HUD
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

        # Thread Communication Queue
        self.msg_queue: queue.Queue = queue.Queue()
        self.is_recording = False
        self.is_processing = False
        self.is_collapsed = False
        self.is_pinned_top = True
        self.current_state = "STARTUP"
        self._animating_collapse = False

        # Unique Windows App ID for distinct Taskbar grouping
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("executive.desktop.assistant.1.0")
        except Exception:
            pass

        # Window Appearance & Geometry (Minimal Smooth Floating Capsule)
        self.title("Executive Assistant")
        self.hud_width = 450
        self.hud_height = 540
        self.pill_height = 64

        # Position at top-right of screen
        screen_w = self.winfo_screenwidth()
        pos_x = max(20, screen_w - self.hud_width - 35)
        pos_y = 35
        self.geometry(f"{self.hud_width}x{self.hud_height}+{pos_x}+{pos_y}")

        # Frameless, Always on Top, True Translucent Glass (Alpha 0.88, Never White)
        self.overrideredirect(True)
        self.attributes("-topmost", self.is_pinned_top)
        self.attributes("-alpha", 0.88)

        self._setup_taskbar_icon()

        # Refined Monochromatic Luxury Color Palette (Pure Black, Zinc Gray, White)
        self.CLR_BG = "#07070a"              # Deep Void Obsidian Glass
        self.CLR_CAPSULE = "#0e0e13"         # Frosted Charcoal Header
        self.CLR_CARD = "#121217"            # Dark Zinc Glass Card
        self.CLR_CARD_INNER = "#0a0a0d"      # Subtle Inner Well
        self.CLR_BORDER = "#22222a"          # Subtle Slate Border
        self.CLR_BORDER_GLOW = "#383844"     # Luminous Glass Rim
        self.CLR_WHITE = "#ffffff"           # Pure Brilliant White
        self.CLR_SILVER = "#e4e4e7"          # Crisp Platinum
        self.CLR_TEXT_DIM = "#8e8e93"        # Neutral Silver Subtext
        self.CLR_TEXT_MUTED = "#55555c"      # Muted Slate
        self.CLR_ROSE = "#f43f5e"            # Stop Accent
        self.CLR_EMERALD = "#10b981"         # Success / Online

        self.configure(fg_color=self.CLR_BG)

        # Drag tracking
        self._drag_x = 0
        self._drag_y = 0

        # Build Interface
        self._build_top_island()
        self._build_content_cards()

        # Keyboard shortcuts
        self.bind_all("<Escape>", lambda e: self._on_escape_pressed())
        self.report_callback_exception = self._on_tk_exception

        # Initialize Continuous Wake Word & Barge-In Engine in Background Thread
        self.wake_detector = None
        threading.Thread(target=self._async_bootstrap_neural_core, daemon=True).start()

        # Periodic Event & Waveform Animation Loops
        self.after(35, self._drain_queue)
        self.after(35, self._animation_loop)

    def _on_tk_exception(self, exc, val, tb):
        import traceback
        err_msg = "".join(traceback.format_exception(exc, val, tb))
        print(f"[HUD Uncaught UI Exception]\n{err_msg}", file=sys.stderr)

    # -------------------------------------------------------------
    # 1. Floating Dynamic Island Capsule (Top Header)
    # -------------------------------------------------------------
    def _build_top_island(self):
        self.island_frame = ctk.CTkFrame(
            self,
            fg_color=self.CLR_CAPSULE,
            corner_radius=20,
            border_width=1,
            border_color=self.CLR_BORDER,
            height=52,
        )
        self.island_frame.pack(fill="x", padx=10, pady=(10, 4))
        self.island_frame.pack_propagate(False)

        # Draggable header
        self.island_frame.bind("<Button-1>", self._start_drag)
        self.island_frame.bind("<B1-Motion>", self._on_drag)

        # Minimalist Brand Icon & Label
        self.brand_label = ctk.CTkLabel(
            self.island_frame,
            text="✦ ASSISTANT",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=self.CLR_WHITE,
        )
        self.brand_label.pack(side="left", padx=(14, 6))
        self.brand_label.bind("<Button-1>", self._start_drag)
        self.brand_label.bind("<B1-Motion>", self._on_drag)

        # Animated Glowing State Beacon Pill
        self.state_badge = ctk.CTkLabel(
            self.island_frame,
            text="● INITIALIZING",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=self.CLR_SILVER,
            fg_color="#181820",
            corner_radius=12,
            padx=10,
            pady=3,
        )
        self.state_badge.pack(side="left", padx=4)

        # Close Button
        self.close_btn = ctk.CTkButton(
            self.island_frame,
            text="✕",
            width=26,
            height=26,
            fg_color="#16161c",
            hover_color="#e11d48",
            text_color=self.CLR_TEXT_DIM,
            font=ctk.CTkFont(size=10, weight="bold"),
            corner_radius=13,
            command=self._on_close,
        )
        self.close_btn.pack(side="right", padx=(3, 10))

        # Collapse Button (Toggle Island / Full HUD with smooth glide animation)
        self.collapse_btn = ctk.CTkButton(
            self.island_frame,
            text="—",
            width=26,
            height=26,
            fg_color="#16161c",
            hover_color="#2b2b34",
            text_color=self.CLR_TEXT_DIM,
            font=ctk.CTkFont(size=10, weight="bold"),
            corner_radius=13,
            command=self._toggle_collapse_animated,
        )
        self.collapse_btn.pack(side="right", padx=2)

        # Stop / Shut Up Button (Immediate Barge-In)
        self.stop_btn = ctk.CTkButton(
            self.island_frame,
            text="■ STOP",
            width=56,
            height=26,
            fg_color="#16161c",
            hover_color="#33141e",
            text_color=self.CLR_ROSE,
            font=ctk.CTkFont(size=9, weight="bold"),
            corner_radius=13,
            command=self._on_stop_clicked,
        )
        self.stop_btn.pack(side="right", padx=2)

    # -------------------------------------------------------------
    # 2. Main Content Cards (Monochrome Glass Cards)
    # -------------------------------------------------------------
    def _build_content_cards(self):
        self.body_container = ctk.CTkFrame(self, fg_color="transparent")
        self.body_container.pack(fill="both", expand=True, padx=10, pady=(2, 10))

        # A. Prominent Fluid Holographic Waveform Card
        self.wave_card = ctk.CTkFrame(
            self.body_container,
            fg_color="#0d0d12",
            corner_radius=14,
            border_width=1,
            border_color="#202028",
            height=80,
        )
        self.wave_card.pack(fill="x", pady=(0, 6))
        self.wave_card.pack_propagate(False)

        self.waveform = ProminentFluidWaveform(
            self.wave_card,
            width=410,
            height=70,
        )
        self.waveform.pack(pady=5)

        # B. User Utterance Glass Card
        self.bubble_frame = ctk.CTkFrame(
            self.body_container,
            fg_color=self.CLR_CARD,
            corner_radius=12,
            border_width=1,
            border_color=self.CLR_BORDER,
        )
        self.bubble_frame.pack(fill="x", pady=(0, 6))

        self.query_text = ctk.CTkLabel(
            self.bubble_frame,
            text="Listening for voice... (Say 'Clanker', 'Jarvis', or 'Call')",
            font=ctk.CTkFont(family="Segoe UI", size=12, slant="italic"),
            text_color=self.CLR_TEXT_DIM,
            wraplength=400,
            justify="left",
            padx=14,
            pady=8,
        )
        self.query_text.pack(fill="x", anchor="w")

        # C. Real-Time Action Ticker (Live Step Stream)
        self.step_container = ctk.CTkFrame(
            self.body_container,
            fg_color=self.CLR_CARD_INNER,
            corner_radius=12,
            border_width=1,
            border_color=self.CLR_BORDER,
        )
        self.step_container.pack(fill="x", pady=(0, 6))

        self.step_header = ctk.CTkLabel(
            self.step_container,
            text="✦ LIVE ACTIONS & REASONING",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color=self.CLR_SILVER,
        )
        self.step_header.pack(anchor="w", padx=12, pady=(5, 2))

        self.step_box = ctk.CTkTextbox(
            self.step_container,
            fg_color="transparent",
            text_color=self.CLR_SILVER,
            font=ctk.CTkFont(family="Consolas", size=10),
            height=58,
            wrap="word",
        )
        self.step_box.pack(fill="x", padx=6, pady=(0, 5))
        self.step_box.insert("end", "[System] Autonomous desktop agent online. Voice & email ready.\n")
        self.step_box.configure(state="disabled")

        # D. Assistant Response Card
        self.result_container = ctk.CTkFrame(
            self.body_container,
            fg_color=self.CLR_CARD,
            corner_radius=14,
            border_width=1,
            border_color=self.CLR_BORDER,
        )
        self.result_container.pack(fill="both", expand=True, pady=(0, 6))

        self.response_header_frame = ctk.CTkFrame(self.result_container, fg_color="transparent")
        self.response_header_frame.pack(fill="x", padx=10, pady=(6, 2))

        self.result_header = ctk.CTkLabel(
            self.response_header_frame,
            text="✦ ASSISTANT RESPONSE",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color=self.CLR_SILVER,
        )
        self.result_header.pack(side="left")

        self.replay_btn = ctk.CTkButton(
            self.response_header_frame,
            text="🔊 Replay",
            width=58,
            height=20,
            fg_color="#181820",
            hover_color="#2b2b34",
            text_color=self.CLR_SILVER,
            font=ctk.CTkFont(size=9, weight="bold"),
            corner_radius=10,
            command=self._replay_last_speech,
        )
        self.replay_btn.pack(side="right")

        self.meme_image_label = ctk.CTkLabel(self.result_container, text="", fg_color="transparent")
        self.meme_image_label.pack_forget()

        self.result_box = ctk.CTkTextbox(
            self.result_container,
            fg_color="transparent",
            text_color=self.CLR_WHITE,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            wrap="word",
        )
        self.result_box.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        self.result_box.insert(
            "end",
            "Standing by. Try saying:\n"
            "• 'Check my emails'\n"
            "• 'Take a screenshot'\n"
            "• 'Zoom in the corner'\n"
            "• 'Open Spotify and play music'"
        )
        self.result_box.configure(state="disabled")

        # E. Minimalist Quick Action Chips Row
        self.chips_frame = ctk.CTkFrame(self.body_container, fg_color="transparent")
        self.chips_frame.pack(fill="x", pady=(0, 6))

        def make_chip(label, icon, fn):
            return ctk.CTkButton(
                self.chips_frame,
                text=f"{icon} {label}".strip(),
                font=ctk.CTkFont(family="Segoe UI", size=10),
                height=26,
                corner_radius=13,
                fg_color="#121217",
                hover_color="#1d1d24",
                border_width=1,
                border_color=self.CLR_BORDER,
                text_color=self.CLR_SILVER,
                command=fn,
            )

        make_chip("Emails", "✉️", self._on_check_emails_clicked).pack(side="left", padx=(0, 4))
        make_chip("Screenshot", "📸", lambda: self._trigger_fast("take_screenshot")).pack(side="left", padx=(0, 4))
        make_chip("Zoom", "🔍", lambda: self._trigger_fast("zoom_window_region", {"region": "center", "zoom_factor": 2.5})).pack(side="left", padx=(0, 4))
        make_chip("Paint", "🎨", lambda: self._trigger_fast("draw_shape", {"shape": "heart", "title_keyword": "Paint"})).pack(side="left", padx=(0, 4))
        make_chip("Telegram", "✈️", lambda: self._trigger_fast("telegram_launch")).pack(side="left", padx=(0, 4))
        make_chip("Lofi", "🎵", lambda: self._trigger_fast("play_youtube", {"query": "synthwave lofi chillhop mix"})).pack(side="left", padx=(0, 4))

        # F. Input Bar (Pill Entry, Mic Button, Pure White Send Button)
        self.input_pill = ctk.CTkFrame(
            self.body_container,
            fg_color=self.CLR_CAPSULE,
            corner_radius=20,
            border_width=1,
            border_color=self.CLR_BORDER,
            height=44,
        )
        self.input_pill.pack(fill="x")
        self.input_pill.pack_propagate(False)

        # Minimalist Mic Trigger with dynamic glow
        self.mic_btn = ctk.CTkButton(
            self.input_pill,
            text="🎙️",
            width=32,
            height=32,
            fg_color="#181820",
            hover_color="#2b2b34",
            border_width=1,
            border_color="#282834",
            font=ctk.CTkFont(size=13),
            corner_radius=16,
            command=self._on_mic_click,
        )
        self.mic_btn.pack(side="left", padx=(6, 4), pady=6)

        # Text Prompt Field
        self.input_field = ctk.CTkEntry(
            self.input_pill,
            placeholder_text="Ask Assistant, check emails, or type a command...",
            fg_color="transparent",
            border_width=0,
            text_color=self.CLR_WHITE,
            font=ctk.CTkFont(family="Segoe UI", size=12),
        )
        self.input_field.pack(side="left", fill="x", expand=True, padx=4, pady=6)
        self.input_field.bind("<Return>", lambda e: self._on_submit_text())

        # Apple/Vercel-Grade Pure White Send Button
        self.send_btn = ctk.CTkButton(
            self.input_pill,
            text="➔",
            width=30,
            height=30,
            fg_color=self.CLR_WHITE,
            text_color="#000000",
            hover_color=self.CLR_SILVER,
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=15,
            command=self._on_submit_text,
        )
        self.send_btn.pack(side="right", padx=(4, 6), pady=7)

    # -------------------------------------------------------------
    # 3. Dynamic Waveform, Glowing Beacon & Mic Glow Animation Loop
    # -------------------------------------------------------------
    def _animation_loop(self):
        try:
            self.waveform.draw_wave(self.current_state)

            # Pulsing state beacon
            pulse = (math.sin(time.time() * 4.5) + 1) / 2
            if self.current_state == "LISTENING":
                glow_val = int(140 + pulse * 115)
                self.state_badge.configure(text="● LISTENING", text_color=f"#{glow_val:02x}{glow_val:02x}{glow_val:02x}")
            elif self.current_state == "PROCESSING":
                self.state_badge.configure(text="● PROCESSING", text_color=self.CLR_SILVER)
            elif self.current_state == "SPEAKING":
                glow_val = int(180 + pulse * 75)
                self.state_badge.configure(text="● SPEAKING", text_color=f"#{glow_val:02x}{glow_val:02x}{glow_val:02x}")
            elif self.current_state == "STOPPED":
                self.state_badge.configure(text="● STOPPED", text_color=self.CLR_ROSE)
            else:  # IDLE / READY
                if self.is_core_ready:
                    self.state_badge.configure(text="● READY", text_color=self.CLR_SILVER)

            # Mic button pulsing glow when recording
            if self.current_state == "LISTENING":
                mic_pulse = (math.sin(time.time() * 6) + 1) / 2
                g = int(90 + mic_pulse * 165)
                self.mic_btn.configure(border_color=f"#{g:02x}{g:02x}{g:02x}", border_width=2)
            else:
                self.mic_btn.configure(border_color="#282834", border_width=1)

        except Exception:
            pass

        self.after(35, self._animation_loop)

    # -------------------------------------------------------------
    # 4. Drag, Eased Collapse Animation & Window Controls
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
        self.attributes("-topmost", True)

    def _toggle_collapse_animated(self):
        """Eased height interpolation between Full HUD (540px) and Capsule (64px)."""
        if self._animating_collapse:
            return

        self._animating_collapse = True
        target_h = self.pill_height if not self.is_collapsed else self.hud_height
        curr_h = self.winfo_height() or (self.hud_height if not self.is_collapsed else self.pill_height)

        steps = 8
        step_diff = (target_h - curr_h) / steps
        pos_x = self.winfo_x()
        pos_y = self.winfo_y()

        def step_anim(i=0):
            nonlocal curr_h
            if i < steps:
                curr_h += step_diff
                self.geometry(f"{self.hud_width}x{int(curr_h)}+{pos_x}+{pos_y}")
                self.after(16, lambda: step_anim(i + 1))
            else:
                self.geometry(f"{self.hud_width}x{target_h}+{pos_x}+{pos_y}")
                if not self.is_collapsed:
                    self.body_container.pack_forget()
                    self.collapse_btn.configure(text="□")
                    self.is_collapsed = True
                else:
                    self.body_container.pack(fill="both", expand=True, padx=10, pady=(2, 10))
                    self.collapse_btn.configure(text="—")
                    self.is_collapsed = False
                self._animating_collapse = False

        if not self.is_collapsed:
            self.body_container.pack_forget()

        step_anim()

    def _expand_if_collapsed(self):
        if self.is_collapsed:
            self._toggle_collapse_animated()

    # -------------------------------------------------------------
    # 5. Email Checking Handler
    # -------------------------------------------------------------
    def _on_check_emails_clicked(self):
        self.tts.stop()
        self._start_command_execution("check my emails")

    # -------------------------------------------------------------
    # 6. Continuous Single-Pass Wake Word & Neural Bootstrap
    # -------------------------------------------------------------
    def _async_bootstrap_neural_core(self):
        try:
            if not self.assistant:
                self.msg_queue.put(("boot_status", "Initializing Orchestrator..."))
                from laya.main import LayaAssistant
                self.assistant = LayaAssistant()

            self.msg_queue.put(("boot_status", "Loading CUDA Whisper..."))
            from laya.audio.stt import get_stt_engine
            self.stt = get_stt_engine()

            self.msg_queue.put(("boot_status", "Activating Wake Word Detector..."))
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

    def _on_interrupt_requested(self):
        print("[HUD] Interruption trigger received: aborting and silencing.")
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
        self._expand_if_collapsed()
        self.is_recording = True
        self.current_state = "LISTENING"
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
        self._expand_if_collapsed()
        if self.wake_detector:
            self.wake_detector.pause()

        self.current_state = "PROCESSING"
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
    # 7. Thread-Safe Event Drainer
    # -------------------------------------------------------------
    def _drain_queue(self):
        try:
            while True:
                kind, *args = self.msg_queue.get_nowait()

                if kind == "boot_status":
                    self.query_text.configure(text=f"✦ {args[0]}")

                elif kind == "core_ready":
                    self.current_state = "IDLE"
                    self.query_text.configure(
                        text="Listening for voice... (Say 'Clanker', 'Jarvis', or 'Call')",
                        text_color=self.CLR_TEXT_DIM,
                    )
                    self._play_startup_greeting()

                elif kind == "wake_trigger":
                    self._start_voice_recording_thread()

                elif kind == "direct_command":
                    self._start_command_execution(args[0])

                elif kind == "state":
                    st = args[0]
                    self.current_state = st

                elif kind == "step":
                    if not is_interrupt_requested():
                        self._append_step(str(args[0]))

                elif kind == "result":
                    res_text, dt_ms = args[0], args[1]
                    if self.current_state != "STOPPED" and not is_interrupt_requested():
                        self._render_result(res_text, dt_ms)

                elif kind == "barge_in_stop":
                    self.current_state = "STOPPED"
                    self.query_text.configure(text="Stopped. Listening...", text_color=self.CLR_WHITE)
                    if self.wake_detector:
                        self.wake_detector.resume()

                elif kind == "reset_idle":
                    if self.current_state != "STOPPED":
                        self.current_state = "IDLE"
                        self.query_text.configure(
                            text="Listening for voice... (Say 'Clanker', 'Jarvis', or 'Call')",
                            text_color=self.CLR_TEXT_DIM,
                        )
                    if self.wake_detector:
                        self.wake_detector.resume()

                elif kind == "extreme_mode":
                    self._handle_extreme_mode(args[0])

                elif kind == "post_execution":
                    if self.current_state != "STOPPED" and not is_interrupt_requested():
                        self.current_state = "SPEAKING"
                    if self.wake_detector:
                        self.wake_detector.resume()

        except queue.Empty:
            pass
        except Exception as e:
            print(f"[HUD Event Drain Note] {e}", file=sys.stderr)

        # Auto-reset badge and visualizer to READY once speech finishes
        try:
            if self.current_state == "SPEAKING" and not self.tts.is_speaking():
                self.current_state = "IDLE"
                self.query_text.configure(
                    text="Listening for voice... (Say 'Clanker', 'Jarvis', or 'Call')",
                    text_color=self.CLR_TEXT_DIM,
                )
        except Exception:
            pass

        finally:
            try:
                self.after(35, self._drain_queue)
            except Exception:
                pass

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

    def _handle_extreme_mode(self, mode_name: str):
        self._expand_if_collapsed()
        if mode_name == "foid_alert":
            self.state_badge.configure(text="🚨 FOID DETECTED", fg_color="#b91c1c", text_color="#ffffff")
            self._flash_border(["#ff1133", "#3a0008", "#ff1133", "#3a0008", "#ff1133", "#3a0008", "#ff1133", "#22222a"], interval_ms=180)
            self._render_result("🚨 FOID ALERT DETECTED:\nFoid, foid, go away, strike my cortisol another day!", 0)

        elif mode_name == "chud_destruct":
            self.state_badge.configure(text="⚠️ CHUD TAKE DETECTED", fg_color="#ea580c", text_color="#ffffff")
            chud_img = self.meme_engine.get_ctk_image("chudjak", size=(130, 130))
            if chud_img:
                self.result_box.pack_forget()
                self.meme_image_label.configure(image=chud_img)
                self.meme_image_label.pack(pady=(6, 4))
                self.result_box.pack(fill="both", expand=True, padx=8, pady=(0, 6))
            self._flash_border(["#ff4400", "#551100", "#ff4400", "#551100", "#ff4400", "#22222a"], interval_ms=200)
            self._render_result("💥 CHUD TAKE DETECTED:\nOh, something happened! Initiating self destruction mode in 3, 2, 1...\n[Self-Destruct Sequence Active — Closing App]", 0)
            # Physical self-destruction: close the application completely after 3.6s
            self.after(3600, self._on_close)

        elif mode_name == "lockdown":
            self.state_badge.configure(text="⚡ LOCKDOWN MODE", fg_color="#0284c7", text_color="#ffffff")
            self._flash_border(["#00f0ff", "#a855f7", "#00f0ff", "#a855f7", "#00f0ff", "#22222a"], interval_ms=160)
            self._render_result("⚡ EXTREME LOCKDOWN ACTIVATED:\nCortisol levels critical. Locking in.", 0)

    def _flash_border(self, color_seq: list, interval_ms: int = 180, idx: int = 0):
        if idx < len(color_seq):
            c = color_seq[idx]
            try:
                self.island_frame.configure(border_color=c)
                self.result_container.configure(border_color=c)
            except Exception:
                pass
            self.after(interval_ms, lambda: self._flash_border(color_seq, interval_ms, idx + 1))
        else:
            try:
                self.island_frame.configure(border_color=self.CLR_BORDER)
                self.result_container.configure(border_color=self.CLR_BORDER)
            except Exception:
                pass

    def _play_startup_greeting(self):
        try:
            greeting = self.memory_store.generate_startup_greeting()
            self._render_result(greeting, 0)
            self.tts.speak(greeting)
        except Exception as e:
            print(f"[HUD Greeting Note] {e}")


def launch_hud(assistant_instance=None):
    """Launch HUD desktop interface with automatic crash recovery."""
    while True:
        try:
            app = LayaHUD(assistant_instance=assistant_instance)
            app.mainloop()
            break  # Clean user exit
        except SystemExit:
            break
        except Exception as e:
            import traceback
            log_dir = Path.home() / ".laya"
            log_dir.mkdir(parents=True, exist_ok=True)
            with open(log_dir / "laya_crash.log", "a", encoding="utf-8") as f:
                f.write(f"\n[{time.ctime()}] Crash: {e}\n{traceback.format_exc()}\n")
            print(f"[HUD Protected Crash Recovery] {e}", file=sys.stderr)
            time.sleep(1.0)


if __name__ == "__main__":
    launch_hud()
