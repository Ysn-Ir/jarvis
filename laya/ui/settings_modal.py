"""
Laya Runtime Control Center Modal (CustomTkinter Dark Glass UI)
Allows live runtime switching between Cloud / Local Mistral (Ollama) / External API keys,
live credential configuration & hot-reloading of Gmail, Telegram, Discord, and Instagram MCP servers,
and real-time runtime/MCP/auth log monitoring.
"""

import threading
import webbrowser
import customtkinter as ctk
from typing import Optional

from laya.runtime_manager import get_runtime_manager


class RuntimeSettingsWindow(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Laya Runtime Control Center")
        self.geometry("620x620")
        self.configure(fg_color="#09090d")
        self.attributes("-topmost", True)

        self.rt = get_runtime_manager()
        self.status_label: Optional[ctk.CTkLabel] = None

        self._build_ui()
        self._refresh_status_and_logs()

    def _set_status(self, text: str, color: str = "#10b981"):
        if self.status_label and self.status_label.winfo_exists():
            self.status_label.configure(text=text, text_color=color)

    def _build_ui(self):
        # Top Header
        header = ctk.CTkFrame(self, fg_color="#111118", corner_radius=12, border_width=1, border_color="#23232f")
        header.pack(fill="x", padx=12, pady=(12, 6))

        ctk.CTkLabel(
            header,
            text="⚙ LAYA RUNTIME CONTROL CENTER",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#ffffff",
        ).pack(side="left", padx=14, pady=10)

        self.status_label = ctk.CTkLabel(
            header,
            text="● Ready",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#10b981",
        )
        self.status_label.pack(side="right", padx=14)

        # Tabbed Interface
        self.tabs = ctk.CTkTabview(
            self,
            fg_color="#101016",
            segmented_button_fg_color="#16161f",
            segmented_button_selected_color="#2b2b3d",
            segmented_button_unselected_color="#16161f",
            text_color="#e4e4e7",
        )
        self.tabs.pack(fill="both", expand=True, padx=12, pady=(4, 12))

        t_llm = self.tabs.add("AI Engine & API Key")
        t_accounts = self.tabs.add("Accounts & MCPs")
        t_logs = self.tabs.add("Live Logs")

        self._build_llm_tab(t_llm)
        self._build_accounts_tab(t_accounts)
        self._build_logs_tab(t_logs)

    # -------------------------------------------------------------
    # TAB 1: LLM Switching & External API Key
    # -------------------------------------------------------------
    def _build_llm_tab(self, parent):
        snap = self.rt.get_status_snapshot()

        # Section A: Inference Mode Switcher
        mode_card = ctk.CTkFrame(parent, fg_color="#14141d", corner_radius=12, border_width=1, border_color="#252534")
        mode_card.pack(fill="x", padx=8, pady=(8, 8))

        ctk.CTkLabel(mode_card, text="Active Inference Mode", font=ctk.CTkFont(size=12, weight="bold"), text_color="#ffffff").pack(anchor="w", padx=12, pady=(10, 4))

        mode_map_display = {
            "auto": "Auto (Cloud + Fallback)",
            "local_mistral": "Local Mistral (Ollama)",
            "external_api": "External API Key",
        }
        reverse_map = {v: k for k, v in mode_map_display.items()}

        self.mode_seg = ctk.CTkSegmentedButton(
            mode_card,
            values=list(mode_map_display.values()),
            command=lambda val: self._on_mode_change(reverse_map[val]),
        )
        self.mode_seg.set(mode_map_display.get(snap["inference_mode"], "Auto (Cloud + Fallback)"))
        self.mode_seg.pack(fill="x", padx=12, pady=(4, 10))

        # Section B: Local Ollama / Mistral Controls
        local_card = ctk.CTkFrame(parent, fg_color="#14141d", corner_radius=12, border_width=1, border_color="#252534")
        local_card.pack(fill="x", padx=8, pady=(0, 8))

        top_row = ctk.CTkFrame(local_card, fg_color="transparent")
        top_row.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(top_row, text="Local Model (Ollama)", font=ctk.CTkFont(size=12, weight="bold"), text_color="#ffffff").pack(side="left")
        self.ollama_badge = ctk.CTkLabel(top_row, text="Checking...", font=ctk.CTkFont(size=11))
        self.ollama_badge.pack(side="right")

        row_local = ctk.CTkFrame(local_card, fg_color="transparent")
        row_local.pack(fill="x", padx=12, pady=(4, 10))

        models = snap.get("available_local_models") or ["mistral:7b"]
        self.local_model_var = ctk.StringVar(value=snap.get("local_model", "mistral:7b"))
        self.local_menu = ctk.CTkOptionMenu(row_local, values=models, variable=self.local_model_var, width=210)
        self.local_menu.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            row_local, text="Use Local Mistral Now", width=150, fg_color="#2563eb", hover_color="#1d4ed8",
            command=self._activate_local_mistral
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            row_local, text="Start Ollama", width=100, fg_color="#27273a", hover_color="#383852",
            command=self._start_ollama_daemon
        ).pack(side="right")

        # Section C: External API Key Runtime Input
        ext_card = ctk.CTkFrame(parent, fg_color="#14141d", corner_radius=12, border_width=1, border_color="#252534")
        ext_card.pack(fill="both", expand=True, padx=8, pady=(0, 6))

        ctk.CTkLabel(ext_card, text="External API Key Configuration (Runtime)", font=ctk.CTkFont(size=12, weight="bold"), text_color="#ffffff").pack(anchor="w", padx=12, pady=(10, 4))

        presets_row = ctk.CTkFrame(ext_card, fg_color="transparent")
        presets_row.pack(fill="x", padx=12, pady=(2, 6))
        for label, url, mdl in [
            ("OpenAI", "https://api.openai.com/v1", "gpt-4o-mini"),
            ("Groq", "https://api.groq.com/openai/v1", "openai/gpt-oss-120b"),
            ("OpenRouter", "https://openrouter.ai/api/v1", "meta-llama/llama-3.3-70b-instruct"),
            ("Mistral AI", "https://api.mistral.ai/v1", "mistral-large-latest"),
            ("Gemini", "https://generativelanguage.googleapis.com/v1beta/openai/", "gemini-2.5-flash"),
        ]:
            ctk.CTkButton(
                presets_row, text=label, width=76, height=24, font=ctk.CTkFont(size=10),
                fg_color="#1e1e2b", hover_color="#2d2d40",
                command=lambda u=url, m=mdl: self._apply_ext_preset(u, m)
            ).pack(side="left", padx=(0, 4))

        self.ext_key_entry = ctk.CTkEntry(ext_card, placeholder_text="Paste External API Key (sk-..., gsk_..., AIza...)", show="*")
        if self.rt.external_api_key:
            self.ext_key_entry.insert(0, self.rt.external_api_key)
        self.ext_key_entry.pack(fill="x", padx=12, pady=4)

        self.ext_url_entry = ctk.CTkEntry(ext_card, placeholder_text="Base URL (e.g. https://api.openai.com/v1)")
        self.ext_url_entry.insert(0, snap.get("external_base_url", "https://api.openai.com/v1"))
        self.ext_url_entry.pack(fill="x", padx=12, pady=4)

        self.ext_model_entry = ctk.CTkEntry(ext_card, placeholder_text="Model ID (e.g. gpt-4o-mini, mistral-large-latest)")
        self.ext_model_entry.insert(0, snap.get("external_model", "gpt-4o-mini"))
        self.ext_model_entry.pack(fill="x", padx=12, pady=4)

        ctk.CTkButton(
            ext_card, text="Save & Activate External API Key", fg_color="#10b981", hover_color="#059669", text_color="#000000",
            font=ctk.CTkFont(weight="bold"), command=self._save_external_api
        ).pack(fill="x", padx=12, pady=(8, 10))

    def _apply_ext_preset(self, url: str, model: str):
        self.ext_url_entry.delete(0, "end")
        self.ext_url_entry.insert(0, url)
        self.ext_model_entry.delete(0, "end")
        self.ext_model_entry.insert(0, model)
        self._set_status(f"Preset loaded: {model}")

    def _on_mode_change(self, mode: str):
        msg = self.rt.set_inference_mode(mode, self.local_model_var.get())
        self._set_status(msg)

    def _activate_local_mistral(self):
        mdl = self.local_model_var.get()
        self._set_status(f"Starting Ollama & loading {mdl}...", "#f59e0b")
        def _bg():
            msg = self.rt.set_inference_mode("local_mistral", mdl)
            ok = self.rt.is_ollama_online()
            self.after(0, lambda: self._set_status(msg if ok else "Started mode, waiting on Ollama port 11434", "#10b981" if ok else "#f59e0b"))
            self.after(0, self._refresh_status_and_logs)
        threading.Thread(target=_bg, daemon=True).start()

    def _start_ollama_daemon(self):
        self._set_status("Launching Ollama daemon...", "#f59e0b")
        def _bg():
            ok = self.rt.ensure_ollama_running(wait_sec=6.0)
            self.after(0, lambda: self._set_status("Ollama Online (port 11434)" if ok else "Ollama failed to launch", "#10b981" if ok else "#f43f5e"))
            self.after(0, self._refresh_status_and_logs)
        threading.Thread(target=_bg, daemon=True).start()

    def _save_external_api(self):
        key = self.ext_key_entry.get().strip()
        url = self.ext_url_entry.get().strip()
        mdl = self.ext_model_entry.get().strip()
        msg = self.rt.set_external_llm(api_key=key, base_url=url, model=mdl, activate=True)
        self.mode_seg.set("External API Key")
        self._set_status(msg[:65], "#10b981" if "Updated" in msg else "#f43f5e")
        self._refresh_status_and_logs()

    # -------------------------------------------------------------
    # TAB 2: Social & Email Runtime Credentials + Hot MCP Reload
    # -------------------------------------------------------------
    def _build_accounts_tab(self, parent):
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # 1. Gmail / Email MCP
        gm = self._make_card(scroll, "✉️ Gmail / IMAP Email MCP (mcp-email-server)")
        self.gm_user = ctk.CTkEntry(gm, placeholder_text="Email address (e.g. you@gmail.com)")
        self.gm_pass = ctk.CTkEntry(gm, placeholder_text="App Password", show="*")
        self.gm_imap = ctk.CTkEntry(gm, placeholder_text="IMAP Server (default: imap.gmail.com)")
        import os
        if os.getenv("EMAIL_USER"): self.gm_user.insert(0, os.getenv("EMAIL_USER"))
        if os.getenv("EMAIL_IMAP_SERVER"): self.gm_imap.insert(0, os.getenv("EMAIL_IMAP_SERVER"))
        self.gm_user.pack(fill="x", padx=10, pady=3)
        self.gm_pass.pack(fill="x", padx=10, pady=3)
        self.gm_imap.pack(fill="x", padx=10, pady=3)
        ctk.CTkButton(gm, text="Save & Hot-Reload Email MCP", fg_color="#2563eb", command=self._save_gmail).pack(fill="x", padx=10, pady=(4, 8))

        # 2. Telegram MTProto MCP
        tg = self._make_card(scroll, "✈️ Telegram Personal MTProto MCP (@dikacode/telegram-mcp)")
        self.tg_id = ctk.CTkEntry(tg, placeholder_text="TELEGRAM_API_ID")
        self.tg_hash = ctk.CTkEntry(tg, placeholder_text="TELEGRAM_API_HASH", show="*")
        self.tg_phone = ctk.CTkEntry(tg, placeholder_text="Phone (+countrycode..., optional)")
        if os.getenv("TELEGRAM_API_ID"): self.tg_id.insert(0, os.getenv("TELEGRAM_API_ID"))
        if os.getenv("TELEGRAM_PHONE"): self.tg_phone.insert(0, os.getenv("TELEGRAM_PHONE"))
        self.tg_id.pack(fill="x", padx=10, pady=3)
        self.tg_hash.pack(fill="x", padx=10, pady=3)
        self.tg_phone.pack(fill="x", padx=10, pady=3)
        ctk.CTkButton(tg, text="Save & Hot-Reload Telegram MCP", fg_color="#0284c7", command=self._save_telegram).pack(fill="x", padx=10, pady=(4, 8))

        # 3. Discord MCP
        dc = self._make_card(scroll, "🎮 Discord MCP (@pasympa/discord-mcp + Persistent Web)")
        self.dc_token = ctk.CTkEntry(dc, placeholder_text="DISCORD_TOKEN (Bot Token)", show="*")
        self.dc_token.pack(fill="x", padx=10, pady=3)
        row_dc = ctk.CTkFrame(dc, fg_color="transparent")
        row_dc.pack(fill="x", padx=10, pady=(4, 8))
        ctk.CTkButton(row_dc, text="Save & Reload Discord MCP", fg_color="#4f46e5", command=self._save_discord).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(row_dc, text="Discord Web Login", fg_color="#27273a", command=lambda: self._open_persistent_web("https://discord.com/app")).pack(side="right", padx=(4, 0))

        # 4. Instagram MCP
        ig = self._make_card(scroll, "📸 Instagram MCP (@mcpware/instagram-mcp + Persistent Web)")
        self.ig_token = ctk.CTkEntry(ig, placeholder_text="INSTAGRAM_ACCESS_TOKEN (Graph API)", show="*")
        self.ig_acct = ctk.CTkEntry(ig, placeholder_text="INSTAGRAM_ACCOUNT_ID")
        self.ig_token.pack(fill="x", padx=10, pady=3)
        self.ig_acct.pack(fill="x", padx=10, pady=3)
        row_ig = ctk.CTkFrame(ig, fg_color="transparent")
        row_ig.pack(fill="x", padx=10, pady=(4, 8))
        ctk.CTkButton(row_ig, text="Save & Reload Instagram MCP", fg_color="#db2777", command=self._save_instagram).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(row_ig, text="Instagram Web Login", fg_color="#27273a", command=lambda: self._open_persistent_web("https://www.instagram.com")).pack(side="right", padx=(4, 0))

        # Live Connected MCPs Inventory
        inv = self._make_card(scroll, "🔌 Connected Production MCP Servers")
        self.mcp_inv_label = ctk.CTkLabel(inv, text="Loading MCP inventory...", justify="left", font=ctk.CTkFont(family="Consolas", size=10), text_color="#a1a1aa")
        self.mcp_inv_label.pack(anchor="w", padx=10, pady=(2, 8))

    def _make_card(self, parent, title: str) -> ctk.CTkFrame:
        f = ctk.CTkFrame(parent, fg_color="#14141d", corner_radius=12, border_width=1, border_color="#252534")
        f.pack(fill="x", padx=4, pady=(0, 8))
        ctk.CTkLabel(f, text=title, font=ctk.CTkFont(size=12, weight="bold"), text_color="#ffffff").pack(anchor="w", padx=10, pady=(8, 4))
        return f

    def _save_gmail(self):
        msg = self.rt.update_platform_credentials("gmail", {
            "user": self.gm_user.get(),
            "password": self.gm_pass.get(),
            "imap_server": self.gm_imap.get(),
        })
        self._set_status(msg[:65])
        self._refresh_status_and_logs()

    def _save_telegram(self):
        msg = self.rt.update_platform_credentials("telegram", {
            "api_id": self.tg_id.get(),
            "api_hash": self.tg_hash.get(),
            "phone": self.tg_phone.get(),
        })
        self._set_status(msg[:65])
        self._refresh_status_and_logs()

    def _save_discord(self):
        msg = self.rt.update_platform_credentials("discord", {
            "token": self.dc_token.get(),
        })
        self._set_status(msg[:65])
        self._refresh_status_and_logs()

    def _save_instagram(self):
        msg = self.rt.update_platform_credentials("instagram", {
            "access_token": self.ig_token.get(),
            "account_id": self.ig_acct.get(),
        })
        self._set_status(msg[:65])
        self._refresh_status_and_logs()

    def _open_persistent_web(self, url: str):
        self._set_status(f"Opening {url} in persistent Playwright session...")
        def _bg():
            try:
                from laya.mcp import get_mcp_hub
                get_mcp_hub().execute_tool_sync("browser_navigate", {"url": url})
                self.rt.log_event("AUTH", f"Opened persistent browser session at {url}")
            except Exception:
                webbrowser.open(url)
        threading.Thread(target=_bg, daemon=True).start()

    # -------------------------------------------------------------
    # TAB 3: Live Runtime Logs
    # -------------------------------------------------------------
    def _build_logs_tab(self, parent):
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.pack(fill="x", padx=6, pady=(6, 4))
        ctk.CTkLabel(bar, text="Audit, Model, Auth & MCP Logs", font=ctk.CTkFont(size=12, weight="bold"), text_color="#ffffff").pack(side="left")
        ctk.CTkButton(bar, text="Clear", width=65, height=24, fg_color="#3f1d28", hover_color="#e11d48", command=self._clear_logs).pack(side="right", padx=(4, 0))
        ctk.CTkButton(bar, text="Refresh", width=70, height=24, fg_color="#27273a", command=self._refresh_status_and_logs).pack(side="right")

        self.logs_box = ctk.CTkTextbox(parent, fg_color="#0a0a0f", text_color="#d4d4d8", font=ctk.CTkFont(family="Consolas", size=10), wrap="word")
        self.logs_box.pack(fill="both", expand=True, padx=6, pady=(2, 6))

    def _clear_logs(self):
        self.rt.clear_logs()
        self._refresh_status_and_logs()

    def _refresh_status_and_logs(self):
        if not self.winfo_exists():
            return
        try:
            snap = self.rt.get_status_snapshot()
            is_on = snap.get("ollama_online", False)
            self.ollama_badge.configure(
                text="● Ollama Online" if is_on else "● Ollama Offline",
                text_color="#10b981" if is_on else "#f59e0b"
            )

            try:
                from laya.mcp import get_mcp_hub
                srv_map = get_mcp_hub().get_connected_servers_summary()
                total = sum(srv_map.values())
                inv_lines = [f"• {k}: {v} tools" for k, v in sorted(srv_map.items())]
                inv_txt = f"Total Active MCP Tools: {total}\n" + ("\n".join(inv_lines) if inv_lines else "Bootstrapping...")
                self.mcp_inv_label.configure(text=inv_txt)
            except Exception:
                pass

            logs = self.rt.get_recent_logs(limit=80)
            self.logs_box.configure(state="normal")
            self.logs_box.delete("1.0", "end")
            self.logs_box.insert("end", "\n".join(logs) if logs else "No logs recorded yet.")
            self.logs_box.see("end")
            self.logs_box.configure(state="disabled")
        except Exception:
            pass

