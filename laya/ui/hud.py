"""
Laya Futuristic Desktop HUD — Cluely-Inspired Dynamic Island
Floating translucent glass capsule with animated audio waveform visualizer,
subtle neon glow borders, single-pass continuous wake word, and real-time step streaming.
"""

import sys
import os
import math
import time
import queue
import random
import threading
from typing import Optional, Callable, List

import customtkinter as ctk

from laya.audio import get_tts_engine, get_stt_engine, AudioCapture
from laya.audio.wake_word import get_wake_word_detector, WakeWordDetector
from laya.fast_path.executor import get_fast_path_executor


class LayaHUD(ctk.CTk):
    def __init__(self, assistant_instance=None):
        super().__init__()

        self.assistant = assistant_instance
        self.tts = get_tts_engine()
        self.stt = get_stt_engine()
        self.capture = AudioCapture()

        # Thread Communication
        self.msg_queue: queue.Queue = queue.Queue()
        self.is_recording = False
        self.is_processing = False
        self.is_collapsed = False
        self.current_state = "IDLE"  # IDLE, LISTENING, PROCESSING, SPEAKING

        # Window Dimensions
        self.title("Laya AI")
        self.hud_width = 440
        self.hud_height = 490
        self.pill_height = 66

        # Position top-right
        screen_w = self.winfo_screenwidth()
        pos_x = max(20, screen_w - self.hud_width - 35)
        pos_y = 35
        self.geometry(f"{self.hud_width}x{self.hud_height}+{pos_x}+{pos_y}")

        # Cluely-Style Glass Styling
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.94)

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Futuristic Obsidian & Cyberpunk Neon Palette
        self.COLOR_BG = "#070a13"
        self.COLOR_CAPSULE = "#0d1322"
        self.COLOR_CARD = "#11182c"
        self.COLOR_CYAN = "#00f0ff"
        self.COLOR_PURPLE = "#a855f7"
        self.COLOR_GREEN = "#10b981"
        self.COLOR_AMBER = "#f59e0b"
        self.COLOR_TEXT_DIM = "#94a3b8"
        self.COLOR_TEXT_WHITE = "#f8fafc"

        self.configure(fg_color=self.COLOR_BG)

        # Drag tracking
        self._drag_x = 0
        self._drag_y = 0

        # Animation state for waveform
        self._wave_phase = 0.0
        self._wave_bars = [4] * 18

        # Build Interface
        self._build_dynamic_island()
        self._build_expanded_body()

        # Initialize Wake Word
        self.wake_detector: Optional[WakeWordDetector] = None
        self._init_wake_word()

        # Animation & Queue Polling
        self.after(35, self._drain_queue)
        self.after(40, self._animate_waveform)

    # -------------------------------------------------------------
    # 1. Dynamic Island Top Capsule
    # -------------------------------------------------------------
    def _build_dynamic_island(self):
        """Top capsule: Branding, Animated Waveform Visualizer, State Pill, Controls."""
        self.island_frame = ctk.CTkFrame(
            self,
            fg_color=self.COLOR_CAPSULE,
            corner_radius=22,
            border_width=1,
            border_color="#1e293b",
            height=58,
        )
        self.island_frame.pack(fill="x", padx=10, pady=(10, 4))
        self.island_frame.pack_propagate(False)

        # Draggable header
        self.island_frame.bind("<Button-1>", self._start_drag)
        self.island_frame.bind("<B1-Motion>", self._on_drag)

        # Glowing Logo
        self.brand_label = ctk.CTkLabel(
            self.island_frame,
            text="✦ LAYA",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=self.COLOR_CYAN,
        )
        self.brand_label.pack(side="left", padx=(14, 6))
        self.brand_label.bind("<Button-1>", self._start_drag)
        self.brand_label.bind("<B1-Motion>", self._on_drag)

        # Canvas Waveform Visualizer
        self.canvas_wave = ctk.CTkCanvas(
            self.island_frame,
            width=110,
            height=28,
            bg=self.COLOR_CAPSULE,
            highlightthickness=0,
        )
        self.canvas_wave.pack(side="left", padx=(2, 6), pady=14)
        self.canvas_wave.bind("<Button-1>", self._start_drag)
        self.canvas_wave.bind("<B1-Motion>", self._on_drag)

        # Status Badge Pill
        self.state_badge = ctk.CTkLabel(
            self.island_frame,
            text="● READY",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=self.COLOR_GREEN,
            fg_color="#062e1e",
            corner_radius=12,
            padx=10,
            pady=2,
        )
        self.state_badge.pack(side="left", padx=4)

        # Close Button
        self.close_btn = ctk.CTkButton(
            self.island_frame,
            text="✕",
            width=26,
            height=26,
            fg_color="#182234",
            hover_color="#ef4444",
            text_color="#94a3b8",
            font=ctk.CTkFont(size=11, weight="bold"),
            corner_radius=13,
            command=self._on_close,
        )
        self.close_btn.pack(side="right", padx=(4, 10))

        # Collapse Button
        self.collapse_btn = ctk.CTkButton(
            self.island_frame,
            text="─",
            width=26,
            height=26,
            fg_color="#182234",
            hover_color="#334155",
            text_color="#94a3b8",
            font=ctk.CTkFont(size=11, weight="bold"),
            corner_radius=13,
            command=self._toggle_collapse,
        )
        self.collapse_btn.pack(side="right", padx=2)

    # -------------------------------------------------------------
    # 2. Expanded Glass Body
    # -------------------------------------------------------------
    def _build_expanded_body(self):
        """Content container: Transcript Bubble, Live Step Feed, Results, and Input."""
        self.body_container = ctk.CTkFrame(self, fg_color="transparent")
        self.body_container.pack(fill="both", expand=True, padx=10, pady=(2, 10))

        # A. User Utterance Glass Card
        self.bubble_frame = ctk.CTkFrame(
            self.body_container,
            fg_color=self.COLOR_CARD,
            corner_radius=16,
            border_width=1,
            border_color="#1e293b",
        )
        self.bubble_frame.pack(fill="x", pady=(0, 6))

        self.query_text = ctk.CTkLabel(
            self.bubble_frame,
            text="Listening for voice... (Say 'Hey Laya' or 'Jarvis')",
            font=ctk.CTkFont(family="Segoe UI", size=12, slant="italic"),
            text_color=self.COLOR_TEXT_DIM,
            wraplength=400,
            justify="left",
            padx=14,
            pady=10,
        )
        self.query_text.pack(fill="x", anchor="w")

        # B. Real-Time Action Ticker (Live Step Feed)
        self.step_container = ctk.CTkFrame(
            self.body_container,
            fg_color="#0a0f1d",
            corner_radius=14,
            border_width=1,
            border_color="#1e293b",
        )
        self.step_container.pack(fill="x", pady=(0, 6))

        self.step_header = ctk.CTkLabel(
            self.step_container,
            text="✦ LIVE INTEL & ACTIONS",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color=self.COLOR_CYAN,
        )
        self.step_header.pack(anchor="w", padx=12, pady=(6, 2))

        self.step_box = ctk.CTkTextbox(
            self.step_container,
            fg_color="transparent",
            text_color="#38bdf8",
            font=ctk.CTkFont(family="Consolas", size=10),
            height=70,
            wrap="word",
        )
        self.step_box.pack(fill="x", padx=6, pady=(0, 6))
        self.step_box.insert("end", "Autonomous desktop agent armed. RTX 4050 active.\n")
        self.step_box.configure(state="disabled")

        # C. Output / Spoken Response Card
        self.result_container = ctk.CTkFrame(
            self.body_container,
            fg_color=self.COLOR_CARD,
            corner_radius=16,
            border_width=1,
            border_color="#1e293b",
        )
        self.result_container.pack(fill="both", expand=True, pady=(0, 6))

        self.result_header = ctk.CTkLabel(
            self.result_container,
            text="✦ ASSISTANT RESPONSE",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color=self.COLOR_PURPLE,
        )
        self.result_header.pack(anchor="w", padx=12, pady=(6, 2))

        self.result_box = ctk.CTkTextbox(
            self.result_container,
            fg_color="transparent",
            text_color=self.COLOR_TEXT_WHITE,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            wrap="word",
        )
        self.result_box.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.result_box.insert(
            "end",
            "I am ready. Try saying:\n"
            "• 'Hey Laya open paint and draw a heart'\n"
            "• 'Hey Laya search youtube for lo-fi'\n"
            "• 'Hey Laya raise the volume by 10 percent'"
        )
        self.result_box.configure(state="disabled")

        # D. Input Bar (Pill Entry, Mic Button, Send)
        self.input_pill = ctk.CTkFrame(
            self.body_container,
            fg_color=self.COLOR_CAPSULE,
            corner_radius=22,
            border_width=1,
            border_color="#1e293b",
            height=46,
        )
        self.input_pill.pack(fill="x")
        self.input_pill.pack_propagate(False)

        # Mic Trigger
        self.mic_btn = ctk.CTkButton(
            self.input_pill,
            text="🎙️",
            width=34,
            height=34,
            fg_color="#182234",
            hover_color=self.COLOR_PURPLE,
            font=ctk.CTkFont(size=14),
            corner_radius=17,
            command=self._on_mic_click,
        )
        self.mic_btn.pack(side="left", padx=(6, 4), pady=6)

        # Text Prompt Field
        self.input_field = ctk.CTkEntry(
            self.input_pill,
            placeholder_text="Type command or ask anything...",
            fg_color="transparent",
            border_width=0,
            text_color=self.COLOR_TEXT_WHITE,
            font=ctk.CTkFont(family="Segoe UI", size=12),
        )
        self.input_field.pack(side="left", fill="x", expand=True, padx=4, pady=6)
        self.input_field.bind("<Return>", lambda e: self._on_submit_text())

        # Send Arrow
        self.send_btn = ctk.CTkButton(
            self.input_pill,
            text="➤",
            width=32,
            height=32,
            fg_color=self.COLOR_CYAN,
            text_color="#000000",
            hover_color="#38bdf8",
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=16,
            command=self._on_submit_text,
        )
        self.send_btn.pack(side="right", padx=(4, 6), pady=7)

    # -------------------------------------------------------------
    # 3. Waveform Animation (Futuristic Audio Visualizer)
    # -------------------------------------------------------------
    def _animate_waveform(self):
        """Draws animated glowing soundwave bars on the canvas based on active state."""
        self._wave_phase += 0.25
        w = 110
        h = 28
        bar_count = 14
        bar_width = 4
        bar_spacing = 3

        self.canvas_wave.delete("all")

        # Calculate heights based on state
        for i in range(bar_count):
            if self.current_state == "IDLE":
                # Gentle breathing wave
                bh = int(3 + 3 * math.sin(self._wave_phase * 0.7 + i * 0.5))
                color = "#334155"
            elif self.current_state == "LISTENING":
                # High energy reactive audio wave
                bh = int(4 + 9 * abs(math.sin(self._wave_phase * 1.6 + i * 0.8)))
                color = self.COLOR_CYAN
            elif self.current_state == "PROCESSING":
                # Scanning neon sweep
                sweep_pos = (math.sin(self._wave_phase * 1.2) + 1.0) * 0.5 * bar_count
                dist = abs(i - sweep_pos)
                bh = int(max(3, 14 - dist * 4))
                color = self.COLOR_AMBER
            elif self.current_state == "SPEAKING":
                # Rhythmic speech pulses
                bh = int(4 + 10 * abs(math.cos(self._wave_phase * 1.4 + i * 0.6)))
                color = self.COLOR_PURPLE
            else:
                bh = 4
                color = "#334155"

            x0 = 8 + i * (bar_width + bar_spacing)
            y0 = (h - bh) // 2
            x1 = x0 + bar_width
            y1 = y0 + bh

            self.canvas_wave.create_rectangle(x0, y0, x1, y1, fill=color, outline="")

        self.after(40, self._animate_waveform)

    # -------------------------------------------------------------
    # 4. Drag & Window Controls
    # -------------------------------------------------------------
    def _start_drag(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event):
        x = self.winfo_x() + (event.x - self._drag_x)
        y = self.winfo_y() + (event.y - self._drag_y)
        self.geometry(f"+{x}+{y}")

    def _on_close(self):
        if self.wake_detector:
            self.wake_detector.stop()
        self.destroy()
        sys.exit(0)

    def _toggle_collapse(self):
        if not self.is_collapsed:
            self.body_container.pack_forget()
            self.geometry(f"{self.hud_width}x{self.pill_height}")
            self.collapse_btn.configure(text="□")
            self.is_collapsed = True
        else:
            self.geometry(f"{self.hud_width}x{self.hud_height}")
            self.body_container.pack(fill="both", expand=True, padx=10, pady=(2, 10))
            self.collapse_btn.configure(text="─")
            self.is_collapsed = False

    def _expand_if_collapsed(self):
        if self.is_collapsed:
            self._toggle_collapse()

    # -------------------------------------------------------------
    # 5. Instant Wake Word & Single-Pass Utterance Integration
    # -------------------------------------------------------------
    def _init_wake_word(self):
        try:
            self.wake_detector = get_wake_word_detector(
                on_wake=self._on_wake_heard,
                on_command=self._on_direct_command_heard,
            )
            self.wake_detector.start()
        except Exception as e:
            print(f"[HUD] Wake word note: {e}")

    def _on_wake_heard(self):
        """User said only wake word ('Hey Laya' / 'Jarvis') -> listen for speech."""
        self.msg_queue.put(("wake_trigger", None))

    def _on_direct_command_heard(self, command_text: str):
        """User spoke wake word + command together -> execute immediately!"""
        self.msg_queue.put(("direct_command", command_text))

    # -------------------------------------------------------------
    # 6. User Input Triggers
    # -------------------------------------------------------------
    def _on_mic_click(self):
        if self.is_recording or self.is_processing:
            return
        if self.wake_detector:
            self.wake_detector.pause()
        self._start_voice_recording_thread()

    def _on_submit_text(self):
        query = self.input_field.get().strip()
        if not query or self.is_processing:
            return
        self.input_field.delete(0, "end")
        self._start_command_execution(query)

    def _start_voice_recording_thread(self):
        self._expand_if_collapsed()
        self.is_recording = True
        self.current_state = "LISTENING"
        self._set_state_badge("● LISTENING", self.COLOR_CYAN, "#083344")
        self.query_text.configure(text="Listening...", text_color=self.COLOR_CYAN)

        threading.Thread(target=self._record_and_transcribe_worker, daemon=True).start()

    def _record_and_transcribe_worker(self):
        try:
            self.tts.stop()
            audio_data = self.capture.record_until_silence(max_duration_sec=7.0)
            if audio_data is None or len(audio_data) == 0:
                self.msg_queue.put(("reset_idle", None))
                return

            self.msg_queue.put(("state", "PROCESSING"))
            transcript = self.stt.transcribe(audio_data)
            if not transcript or not transcript.strip():
                self.msg_queue.put(("reset_idle", None))
                return

            self.msg_queue.put(("direct_command", transcript))

        except Exception as ex:
            self.msg_queue.put(("reset_idle", None))

    def _start_command_execution(self, query: str):
        self._expand_if_collapsed()
        if self.wake_detector:
            self.wake_detector.pause()

        self.current_state = "PROCESSING"
        self._set_state_badge("● PROCESSING", self.COLOR_AMBER, "#451a03")
        self.query_text.configure(text=f"\"{query}\"", text_color=self.COLOR_TEXT_WHITE)

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
            self.msg_queue.put(("result", result, dt_ms))

        except Exception as e:
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
                        self._set_state_badge("● PROCESSING", self.COLOR_AMBER, "#451a03")

                elif kind == "step":
                    self._append_step(str(args[0]))

                elif kind == "result":
                    res_text, dt_ms = args[0], args[1]
                    self._render_result(res_text, dt_ms)

                elif kind == "reset_idle":
                    self.current_state = "IDLE"
                    self._set_state_badge("● READY", self.COLOR_GREEN, "#062e1e")
                    self.query_text.configure(text="Listening for voice... (Say 'Hey Laya')", text_color=self.COLOR_TEXT_DIM)
                    if self.wake_detector:
                        self.wake_detector.resume()

                elif kind == "post_execution":
                    self.current_state = "SPEAKING"
                    self._set_state_badge("● COMPLETE", self.COLOR_PURPLE, "#2e1065")
                    if self.wake_detector:
                        self.wake_detector.resume()

        except queue.Empty:
            pass

        self.after(35, self._drain_queue)

    def _set_state_badge(self, text: str, fg: str, bg: str):
        self.state_badge.configure(text=text, text_color=fg, fg_color=bg)

    def _append_step(self, step_text: str):
        self.step_box.configure(state="normal")
        t_str = time.strftime("%H:%M:%S")
        self.step_box.insert("end", f"[{t_str}] {step_text}\n")
        self.step_box.see("end")
        self.step_box.configure(state="disabled")

    def _render_result(self, result_text: str, dt_ms: float):
        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.insert("end", result_text)
        self.result_box.configure(state="disabled")

        if dt_ms > 0:
            self.step_header.configure(text=f"✦ LIVE INTEL & ACTIONS ({dt_ms:.0f}ms)")


def launch_hud(assistant_instance=None):
    app = LayaHUD(assistant_instance=assistant_instance)
    app.mainloop()


if __name__ == "__main__":
    launch_hud()
