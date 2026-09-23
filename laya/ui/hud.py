"""
Laya State-of-the-Art Futuristic Desktop HUD (Heads-Up Display)
Frameless, semi-transparent, draggable desktop overlay with non-blocking
multi-threaded execution, real-time ReAct step streaming, and always-on wake word.
"""

import sys
import os
import time
import queue
import threading
from typing import Optional, Callable

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

        # Thread communication queue
        self.msg_queue: queue.Queue = queue.Queue()
        self.is_recording = False
        self.is_processing = False
        self.is_collapsed = False

        # Configure Window
        self.title("Laya HUD")
        self.hud_width = 460
        self.hud_height = 560
        self.collapsed_height = 56

        # Position at top-right of primary screen
        screen_w = self.winfo_screenwidth()
        pos_x = max(20, screen_w - self.hud_width - 30)
        pos_y = 40
        self.geometry(f"{self.hud_width}x{self.hud_height}+{pos_x}+{pos_y}")

        # Modern Frameless & Transparent Styling
        self.overrideredirect(True)          # Frameless
        self.attributes("-topmost", True)      # Always on top
        self.attributes("-alpha", 0.94)        # Glass transparency

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Color Palette: Deep Slate Glass with Cyan & Violet Accents
        self.BG_MAIN = "#0b0f19"
        self.BG_CARD = "#131b2e"
        self.BG_FEED = "#0d1322"
        self.ACCENT_CYAN = "#00d2ff"
        self.ACCENT_VIOLET = "#7928ca"
        self.TEXT_MUTED = "#8b949e"
        self.TEXT_BRIGHT = "#f0f6fc"

        self.configure(fg_color=self.BG_MAIN)

        # Dragging State
        self._drag_x = 0
        self._drag_y = 0

        # Build GUI Components
        self._build_header()
        self._build_status_bar()
        self._build_main_content()
        self._build_controls()

        # Setup Wake Word Engine
        self.wake_detector: Optional[WakeWordDetector] = None
        self._init_wake_word()

        # Start periodic queue polling (30ms)
        self.after(30, self._drain_queue)

    def _build_header(self):
        """Header bar with title, telemetry badge, and window controls."""
        self.header_frame = ctk.CTkFrame(self, fg_color=self.BG_CARD, corner_radius=12, height=44)
        self.header_frame.pack(fill="x", padx=8, pady=(8, 4))
        self.header_frame.pack_propagate(False)

        # Enable dragging by clicking anywhere on header
        self.header_frame.bind("<Button-1>", self._start_drag)
        self.header_frame.bind("<B1-Motion>", self._on_drag)

        # Branding
        self.logo_label = ctk.CTkLabel(
            self.header_frame,
            text="⚡ LAYA OS",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=self.ACCENT_CYAN,
        )
        self.logo_label.pack(side="left", padx=(14, 8))
        self.logo_label.bind("<Button-1>", self._start_drag)
        self.logo_label.bind("<B1-Motion>", self._on_drag)

        # Telemetry Pill (GPU & Engine)
        self.gpu_badge = ctk.CTkLabel(
            self.header_frame,
            text="RTX 4050 • CUDA",
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color="#38ef7d",
            fg_color="#092816",
            corner_radius=6,
            padx=8,
            pady=2,
        )
        self.gpu_badge.pack(side="left", padx=4)

        # Window Controls: Collapse & Close
        self.close_btn = ctk.CTkButton(
            self.header_frame,
            text="✕",
            width=28,
            height=28,
            fg_color="#21262d",
            hover_color="#da3633",
            text_color="#c9d1d9",
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=8,
            command=self._on_close,
        )
        self.close_btn.pack(side="right", padx=(4, 10))

        self.collapse_btn = ctk.CTkButton(
            self.header_frame,
            text="─",
            width=28,
            height=28,
            fg_color="#21262d",
            hover_color="#30363d",
            text_color="#c9d1d9",
            font=ctk.CTkFont(size=12, weight="bold"),
            corner_radius=8,
            command=self._toggle_collapse,
        )
        self.collapse_btn.pack(side="right", padx=2)

    def _build_status_bar(self):
        """Status indicator pill."""
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent", height=30)
        self.status_frame.pack(fill="x", padx=12, pady=(2, 6))

        self.status_pill = ctk.CTkLabel(
            self.status_frame,
            text="● IDLE — Say 'Hey Laya' or 'Jarvis'",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#00ff88",
            fg_color="#092314",
            corner_radius=10,
            padx=12,
            pady=3,
        )
        self.status_pill.pack(side="left")

    def _build_main_content(self):
        """Container for query view, live step feed, and results card."""
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.pack(fill="both", expand=True, padx=8, pady=2)

        # 1. User Query Card
        self.query_frame = ctk.CTkFrame(self.content_container, fg_color=self.BG_CARD, corner_radius=10)
        self.query_frame.pack(fill="x", pady=(0, 6))

        self.query_label = ctk.CTkLabel(
            self.query_frame,
            text="Waiting for voice command...",
            font=ctk.CTkFont(family="Segoe UI", size=12, slant="italic"),
            text_color=self.TEXT_MUTED,
            wraplength=420,
            justify="left",
            padx=12,
            pady=8,
        )
        self.query_label.pack(fill="x", anchor="w")

        # 2. Live Action / Step Stream Feed (Activity ticker)
        self.feed_header = ctk.CTkLabel(
            self.content_container,
            text="LIVE ACTIVITY FEED",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=self.TEXT_MUTED,
        )
        self.feed_header.pack(anchor="w", padx=6, pady=(2, 2))

        self.feed_box = ctk.CTkTextbox(
            self.content_container,
            fg_color=self.BG_FEED,
            text_color=self.ACCENT_CYAN,
            font=ctk.CTkFont(family="Consolas", size=10),
            corner_radius=10,
            height=100,
            wrap="word",
        )
        self.feed_box.pack(fill="x", pady=(0, 6))
        self.feed_box.insert("end", "System ready. RTX 4050 GPU accelerated.\n")
        self.feed_box.configure(state="disabled")

        # 3. Final Results Card
        self.result_header = ctk.CTkLabel(
            self.content_container,
            text="RESPONSE & OUTPUT",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=self.TEXT_MUTED,
        )
        self.result_header.pack(anchor="w", padx=6, pady=(2, 2))

        self.result_box = ctk.CTkTextbox(
            self.content_container,
            fg_color=self.BG_CARD,
            text_color=self.TEXT_BRIGHT,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            corner_radius=10,
            wrap="word",
        )
        self.result_box.pack(fill="both", expand=True, pady=(0, 6))
        self.result_box.insert("end", "Hello! I am Laya, your autonomous desktop assistant.\nSay 'Hey Laya' or click the microphone to speak.")
        self.result_box.configure(state="disabled")

    def _build_controls(self):
        """Bottom controls: text entry, send button, and manual mic button."""
        self.controls_frame = ctk.CTkFrame(self, fg_color=self.BG_CARD, corner_radius=12, height=52)
        self.controls_frame.pack(fill="x", padx=8, pady=(2, 8))
        self.controls_frame.pack_propagate(False)

        # Mic Button
        self.mic_btn = ctk.CTkButton(
            self.controls_frame,
            text="🎙️",
            width=38,
            height=38,
            fg_color="#1f293d",
            hover_color=self.ACCENT_VIOLET,
            font=ctk.CTkFont(size=16),
            corner_radius=10,
            command=self._on_mic_click,
        )
        self.mic_btn.pack(side="left", padx=(8, 6), pady=7)

        # Text input entry
        self.input_entry = ctk.CTkEntry(
            self.controls_frame,
            placeholder_text="Ask Laya or type command...",
            fg_color="#0b0f19",
            border_color="#212936",
            text_color=self.TEXT_BRIGHT,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            corner_radius=8,
            height=36,
        )
        self.input_entry.pack(side="left", fill="x", expand=True, padx=4, pady=7)
        self.input_entry.bind("<Return>", lambda e: self._on_send_text())

        # Send Button
        self.send_btn = ctk.CTkButton(
            self.controls_frame,
            text="➤",
            width=36,
            height=36,
            fg_color=self.ACCENT_CYAN,
            text_color="#000000",
            hover_color="#00a3cc",
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8,
            command=self._on_send_text,
        )
        self.send_btn.pack(side="right", padx=(4, 8), pady=7)

    # -------------------------------------------------------------
    # Drag & Window Controls
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
        """Toggle between full HUD and compact floating pill."""
        if not self.is_collapsed:
            self.content_container.pack_forget()
            self.status_frame.pack_forget()
            self.controls_frame.pack_forget()
            self.geometry(f"{self.hud_width}x{self.collapsed_height}")
            self.collapse_btn.configure(text="□")
            self.is_collapsed = True
        else:
            self.geometry(f"{self.hud_width}x{self.hud_height}")
            self.status_frame.pack(fill="x", padx=12, pady=(2, 6))
            self.content_container.pack(fill="both", expand=True, padx=8, pady=2)
            self.controls_frame.pack(fill="x", padx=8, pady=(2, 8))
            self.collapse_btn.configure(text="─")
            self.is_collapsed = False

    # -------------------------------------------------------------
    # Wake Word Integration
    # -------------------------------------------------------------
    def _init_wake_word(self):
        """Start the always-on wake word detector in background."""
        try:
            self.wake_detector = get_wake_word_detector(on_wake=self._on_wake_triggered)
            self.wake_detector.start()
        except Exception as e:
            print(f"[HUD] Wake word initialization note: {e}")

    def _on_wake_triggered(self):
        """Callback from background wake-word thread."""
        self.msg_queue.put(("wake_word_heard", None))

    # -------------------------------------------------------------
    # User Input Handlers
    # -------------------------------------------------------------
    def _on_mic_click(self):
        if self.is_recording or self.is_processing:
            return
        if self.wake_detector:
            self.wake_detector.pause()
        self._start_voice_capture_thread()

    def _on_send_text(self):
        query = self.input_entry.get().strip()
        if not query or self.is_processing:
            return
        self.input_entry.delete(0, "end")
        self._start_execution_thread(query)

    def _start_voice_capture_thread(self):
        """Launch background speech recording & Whisper transcription thread."""
        self.is_recording = True
        self.set_status("LISTENING", "● LISTENING... (Speak now)", "#ffaa00", "#332200")
        self.query_label.configure(text="Listening...", text_color=self.ACCENT_CYAN)

        threading.Thread(target=self._voice_worker, daemon=True).start()

    def _voice_worker(self):
        """Non-blocking background worker for audio capture and STT."""
        try:
            self.tts.stop()  # Stop any active speech playback
            audio_data = self.capture.record_until_silence(max_duration_sec=7.0)
            if audio_data is None or len(audio_data) == 0:
                self.msg_queue.put(("status", ("IDLE", "● IDLE — No speech detected", "#00ff88", "#092314")))
                self.msg_queue.put(("resume_wake", None))
                self.is_recording = False
                return

            self.msg_queue.put(("status", ("PROCESSING", "● TRANSCRIBING (Whisper CUDA)...", "#00d2ff", "#002b3d")))
            transcript = self.stt.transcribe(audio_data)

            if not transcript or len(transcript.strip()) == 0:
                self.msg_queue.put(("status", ("IDLE", "● IDLE — Could not transcribe", "#00ff88", "#092314")))
                self.msg_queue.put(("resume_wake", None))
                self.is_recording = False
                return

            self.msg_queue.put(("user_query", transcript))
            self._execute_command_worker(transcript)

        except Exception as e:
            self.msg_queue.put(("step", f"Audio error: {e}"))
            self.msg_queue.put(("status", ("IDLE", "● IDLE — Ready", "#00ff88", "#092314")))
            self.msg_queue.put(("resume_wake", None))
            self.is_recording = False

    def _start_execution_thread(self, query: str):
        """Launch background command execution thread."""
        if self.wake_detector:
            self.wake_detector.pause()
        self.query_label.configure(text=f"\"{query}\"", text_color=self.TEXT_BRIGHT)
        self.set_status("PROCESSING", "● PROCESSING...", "#00d2ff", "#002b3d")

        threading.Thread(target=lambda: self._execute_command_worker(query), daemon=True).start()

    def _execute_command_worker(self, query: str):
        """Background thread executing Laya 3-tier routing and ReAct loop."""
        self.is_processing = True
        try:
            def on_step(step_msg: str):
                self.msg_queue.put(("step", step_msg))

            if self.assistant:
                res = self.assistant.handle_command(query, speak=True, step_callback=on_step)
            else:
                res = f"Simulated output for query: {query}"

            self.msg_queue.put(("result", res))
        except Exception as e:
            self.msg_queue.put(("result", f"Execution error: {e}"))
        finally:
            self.is_processing = False
            self.is_recording = False
            self.msg_queue.put(("status", ("IDLE", "● IDLE — Say 'Hey Laya' or 'Jarvis'", "#00ff88", "#092314")))
            self.msg_queue.put(("resume_wake", None))

    # -------------------------------------------------------------
    # Thread-Safe GUI Event Processing
    # -------------------------------------------------------------
    def _drain_queue(self):
        """Processes messages queued by background worker threads."""
        try:
            while True:
                kind, data = self.msg_queue.get_nowait()

                if kind == "wake_word_heard":
                    if not self.is_recording and not self.is_processing:
                        if self.is_collapsed:
                            self._toggle_collapse()
                        self._start_voice_capture_thread()

                elif kind == "resume_wake":
                    if self.wake_detector:
                        self.wake_detector.resume()

                elif kind == "status":
                    st_name, text, fg, bg = data
                    self.set_status(st_name, text, fg, bg)

                elif kind == "user_query":
                    self.query_label.configure(text=f"\"{data}\"", text_color=self.TEXT_BRIGHT)

                elif kind == "step":
                    self.append_feed(str(data))

                elif kind == "result":
                    self.set_result(str(data))

        except queue.Empty:
            pass

        # Reschedule check in 30ms
        self.after(30, self._drain_queue)

    def set_status(self, mode: str, text: str, fg: str, bg: str):
        """Update status pill."""
        self.status_pill.configure(text=text, text_color=fg, fg_color=bg)

    def append_feed(self, step_text: str):
        """Append a step to the real-time activity feed."""
        self.feed_box.configure(state="normal")
        timestamp = time.strftime("%H:%M:%S")
        self.feed_box.insert("end", f"[{timestamp}] {step_text}\n")
        self.feed_box.see("end")
        self.feed_box.configure(state="disabled")

    def set_result(self, result_text: str):
        """Render final response in the result card."""
        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.insert("end", result_text)
        self.result_box.configure(state="disabled")


def launch_hud(assistant_instance=None):
    """Launcher entry point for the Laya Desktop HUD."""
    app = LayaHUD(assistant_instance=assistant_instance)
    app.mainloop()


if __name__ == "__main__":
    launch_hud()
