"""
Laya Telegram Authenticator (GUI + CLI)
Authenticates your Telegram account for 100% silent, background messaging,
reading, contact sync, and broadcasting.

Usage:
1. GUI Mode (Recommended - opens friendly setup window):
   python -m laya.tools.telegram_login

2. Command-Line Mode:
   python -m laya.tools.telegram_login --api_id <ID> --api_hash <HASH> --phone <+PHONE>

Credentials are saved to:
- ~/.laya/telegram.session
- .env (TELEGRAM_API_ID, TELEGRAM_API_HASH)
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path
from typing import Optional

REPO_DIR = Path(r"c:\Users\khali\OneDrive\Bureau\learning\datascience\projects\jev")
ENV_PATH = REPO_DIR / ".env"
try:
    from dotenv import load_dotenv
    load_dotenv(ENV_PATH)
except Exception:
    pass

SESSION_PATH = Path.home() / ".laya" / "telegram.session"


def save_env_credentials(api_id: str, api_hash: str):
    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            lines = [l for l in f.readlines() if not l.startswith(("TELEGRAM_API_ID=", "TELEGRAM_API_HASH="))]
    lines.append(f"TELEGRAM_API_ID={api_id}\n")
    lines.append(f"TELEGRAM_API_HASH={api_hash}\n")
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)
    os.environ["TELEGRAM_API_ID"] = str(api_id)
    os.environ["TELEGRAM_API_HASH"] = str(api_hash)


async def perform_telethon_login(api_id: int, api_hash: str, phone: str, get_code_fn, get_password_fn=None):
    from telethon import TelegramClient
    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    client = TelegramClient(str(SESSION_PATH), api_id, api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        await client.send_code_request(phone)
        code = get_code_fn() if callable(get_code_fn) else str(get_code_fn)
        try:
            await client.sign_in(phone=phone, code=code)
        except Exception as e:
            if "Two-steps verification is enabled" in str(e) or "SessionPasswordNeededError" in type(e).__name__:
                if get_password_fn:
                    pwd = get_password_fn() if callable(get_password_fn) else str(get_password_fn)
                    await client.sign_in(password=pwd)
                else:
                    raise e
            else:
                raise e

    me = await client.get_me()
    save_env_credentials(str(api_id), api_hash)
    await client.disconnect()
    return me


def launch_gui_authenticator(default_api_id="", default_api_hash=""):
    import tkinter as tk
    from tkinter import messagebox, ttk

    root = tk.Tk()
    root.title("Laya Telegram Setup")
    root.geometry("480x420")
    root.resizable(False, False)
    root.configure(bg="#121214")

    # Header
    header = tk.Label(root, text="✦ LAYA TELEGRAM SETUP", font=("Segoe UI", 14, "bold"), fg="#ffffff", bg="#121214")
    header.pack(pady=(18, 6))

    sub = tk.Label(root, text="Obtain free API credentials at https://my.telegram.org", font=("Segoe UI", 9), fg="#8e8e93", bg="#121214")
    sub.pack(pady=(0, 16))

    form_frame = tk.Frame(root, bg="#121214")
    form_frame.pack(fill="x", padx=30)

    # API ID
    tk.Label(form_frame, text="API ID:", font=("Segoe UI", 10, "bold"), fg="#e5e5ea", bg="#121214").grid(row=0, column=0, sticky="w", pady=4)
    id_entry = tk.Entry(form_frame, font=("Segoe UI", 10), bg="#1c1c1f", fg="#ffffff", insertbackground="#ffffff", relief="flat")
    id_entry.grid(row=0, column=1, sticky="ew", pady=4, padx=(10, 0))
    if default_api_id:
        id_entry.insert(0, default_api_id)

    # API Hash
    tk.Label(form_frame, text="API Hash:", font=("Segoe UI", 10, "bold"), fg="#e5e5ea", bg="#121214").grid(row=1, column=0, sticky="w", pady=4)
    hash_entry = tk.Entry(form_frame, font=("Segoe UI", 10), bg="#1c1c1f", fg="#ffffff", insertbackground="#ffffff", relief="flat")
    hash_entry.grid(row=1, column=1, sticky="ew", pady=4, padx=(10, 0))
    if default_api_hash:
        hash_entry.insert(0, default_api_hash)

    # Phone Number
    tk.Label(form_frame, text="Phone Number:", font=("Segoe UI", 10, "bold"), fg="#e5e5ea", bg="#121214").grid(row=2, column=0, sticky="w", pady=4)
    phone_entry = tk.Entry(form_frame, font=("Segoe UI", 10), bg="#1c1c1f", fg="#ffffff", insertbackground="#ffffff", relief="flat")
    phone_entry.grid(row=2, column=1, sticky="ew", pady=4, padx=(10, 0))
    phone_entry.insert(0, "+")

    # Telegram Login Code
    tk.Label(form_frame, text="SMS/Telegram Code:", font=("Segoe UI", 10, "bold"), fg="#e5e5ea", bg="#121214").grid(row=3, column=0, sticky="w", pady=4)
    code_entry = tk.Entry(form_frame, font=("Segoe UI", 10), bg="#1c1c1f", fg="#ffffff", insertbackground="#ffffff", relief="flat", state="disabled")
    code_entry.grid(row=3, column=1, sticky="ew", pady=4, padx=(10, 0))

    # 2FA Password (if enabled)
    tk.Label(form_frame, text="2FA Password (Optional):", font=("Segoe UI", 10), fg="#8e8e93", bg="#121214").grid(row=4, column=0, sticky="w", pady=4)
    pwd_entry = tk.Entry(form_frame, font=("Segoe UI", 10), bg="#1c1c1f", fg="#ffffff", insertbackground="#ffffff", relief="flat", show="*")
    pwd_entry.grid(row=4, column=1, sticky="ew", pady=4, padx=(10, 0))

    form_frame.columnconfigure(1, weight=1)

    status_lbl = tk.Label(root, text="Fill credentials and click 'Send Code'", font=("Segoe UI", 9), fg="#a1a1aa", bg="#121214")
    status_lbl.pack(pady=(16, 8))

    import threading
    import concurrent.futures

    # --------------------------------------------------------------------------
    # One persistent background event loop — created once, never closed.
    # The TelegramClient is bound to this loop from connect() through disconnect().
    # Both "Send Code" and "Verify" run on the SAME loop so the connection stays valid.
    # --------------------------------------------------------------------------
    _bg_loop = asyncio.new_event_loop()
    _bg_thread = threading.Thread(
        target=_bg_loop.run_forever,
        daemon=True,
        name="LayaTelegramLoginLoop",
    )
    _bg_thread.start()

    client_holder = {}  # shares the live client between Send Code → Verify steps

    def _submit(coro, done_cb):
        """Submit a coroutine to the persistent loop; call done_cb(result, err) on main thread."""
        future = asyncio.run_coroutine_threadsafe(coro, _bg_loop)

        def _wait():
            try:
                result = future.result(timeout=30)
                root.after(0, lambda: done_cb(result, None))
            except Exception as e:
                root.after(0, lambda err=e: done_cb(None, err))

        threading.Thread(target=_wait, daemon=True).start()

    def on_request_code():
        api_id_val = id_entry.get().strip()
        api_hash_val = hash_entry.get().strip()
        phone_val = phone_entry.get().strip()

        if not api_id_val or not api_hash_val or len(phone_val) < 8:
            messagebox.showerror("Error", "Please provide valid API ID, API Hash, and Phone Number.")
            return

        status_lbl.configure(text="Connecting to Telegram servers...", fg="#38bdf8")
        btn_request.configure(state="disabled")

        async def _req():
            from telethon import TelegramClient
            SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
            client = TelegramClient(str(SESSION_PATH), int(api_id_val), api_hash_val,
                                    loop=_bg_loop)
            await client.connect()
            if await client.is_user_authorized():
                me = await client.get_me()
                save_env_credentials(api_id_val, api_hash_val)
                await client.disconnect()
                return ("already", me)
            await client.send_code_request(phone_val)
            # Keep client alive — do NOT disconnect here
            client_holder["client"] = client
            client_holder["phone"] = phone_val
            client_holder["api_id"] = api_id_val
            client_holder["api_hash"] = api_hash_val
            return ("code_sent", None)

        def _on_done(result, err):
            if err:
                status_lbl.configure(text=f"Error: {err}", fg="#f87171")
                btn_request.configure(state="normal")
                return
            kind, me = result
            if kind == "already":
                status_lbl.configure(text=f"Already logged in as {me.first_name}!", fg="#4ade80")
                messagebox.showinfo("Success", f"Already logged in as {me.first_name} (@{me.username or 'No username'})")
                root.destroy()
            else:
                code_entry.configure(state="normal")
                code_entry.focus()
                btn_verify.configure(state="normal")
                status_lbl.configure(text="Code sent! Enter it below and click Verify.", fg="#4ade80")

        _submit(_req(), _on_done)

    def on_verify():
        code_val = code_entry.get().strip()
        pwd_val = pwd_entry.get().strip()
        client = client_holder.get("client")
        phone_val = client_holder.get("phone", phone_entry.get().strip())
        api_id_val = client_holder.get("api_id", id_entry.get().strip())
        api_hash_val = client_holder.get("api_hash", hash_entry.get().strip())
        needs_2fa = client_holder.get("needs_2fa", False)

        if not client:
            messagebox.showerror("Error", "Please send the code first.")
            return

        # ── State 2: user already got SessionPasswordNeededError, now submitting password ──
        if needs_2fa:
            if not pwd_val:
                status_lbl.configure(
                    text="Enter your Telegram cloud password in the field above, then click Verify again.",
                    fg="#f87171"
                )
                pwd_entry.configure(bg="#3a1212")
                pwd_entry.focus()
                return

            status_lbl.configure(text="Verifying 2FA password...", fg="#38bdf8")

            async def _do_2fa():
                await client.sign_in(password=pwd_val)
                me = await client.get_me()
                save_env_credentials(api_id_val, api_hash_val)
                await client.disconnect()
                return me

            def _on_2fa(me, err):
                if err:
                    status_lbl.configure(text=f"Wrong password: {err}", fg="#f87171")
                    pwd_entry.configure(bg="#3a1212")
                    return
                status_lbl.configure(text=f"Logged in as {me.first_name}!", fg="#4ade80")
                messagebox.showinfo("Success", f"Logged in as {me.first_name} (@{me.username or 'No username'})!\nTelegram API is ready.")
                root.destroy()

            _submit(_do_2fa(), _on_2fa)
            return

        # ── State 1: First verify with code ──
        if not code_val:
            messagebox.showerror("Error", "Please enter the code received on Telegram.")
            return

        status_lbl.configure(text="Verifying code...", fg="#38bdf8")

        async def _sign_in():
            try:
                await client.sign_in(phone=phone_val, code=code_val)
            except Exception as e:
                if "Two-steps verification" in str(e) or "SessionPasswordNeededError" in type(e).__name__:
                    raise RuntimeError("2FA_NEEDED")
                raise
            me = await client.get_me()
            save_env_credentials(api_id_val, api_hash_val)
            await client.disconnect()
            return me

        def _on_verify_done(me, err):
            if err:
                if "2FA_NEEDED" in str(err):
                    client_holder["needs_2fa"] = True
                    pwd_entry.configure(state="normal", bg="#1c2e1c")
                    pwd_entry.delete(0, "end")
                    pwd_entry.focus()
                    status_lbl.configure(
                        text="Telegram requires your cloud password. Enter it above and click Verify.",
                        fg="#fbbf24"
                    )
                else:
                    status_lbl.configure(text=f"Verification failed: {err}", fg="#f87171")
                return
            status_lbl.configure(text=f"Logged in as {me.first_name}!", fg="#4ade80")
            messagebox.showinfo("Success", f"Logged in as {me.first_name} (@{me.username or 'No username'})!\nTelegram API messaging is now active.")
            root.destroy()

        _submit(_sign_in(), _on_verify_done)


    btn_frame = tk.Frame(root, bg="#121214")


    btn_frame.pack(pady=12)

    btn_request = tk.Button(
        btn_frame,
        text="1. Send Code",
        font=("Segoe UI", 10, "bold"),
        bg="#2563eb",
        fg="#ffffff",
        activebackground="#1d4ed8",
        relief="flat",
        padx=14,
        pady=6,
        command=on_request_code,
    )
    btn_request.pack(side="left", padx=8)

    btn_verify = tk.Button(
        btn_frame,
        text="2. Verify & Connect",
        font=("Segoe UI", 10, "bold"),
        bg="#16a34a",
        fg="#ffffff",
        activebackground="#15803d",
        relief="flat",
        padx=14,
        pady=6,
        state="disabled",
        command=on_verify,
    )
    btn_verify.pack(side="left", padx=8)

    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="Laya Telegram Setup")
    parser.add_argument("--api_id", help="Telegram API ID")
    parser.add_argument("--api_hash", help="Telegram API Hash")
    parser.add_argument("--phone", help="Telegram Phone number")
    parser.add_argument("--code", help="Telegram login verification code")
    parser.add_argument("--password", help="Telegram 2FA password")
    parser.add_argument("--cli", action="store_true", help="Force command-line interface")
    args = parser.parse_args()

    api_id = args.api_id or os.getenv("TELEGRAM_API_ID", "").strip()
    api_hash = args.api_hash or os.getenv("TELEGRAM_API_HASH", "").strip()

    # If all CLI parameters provided, perform non-interactive login
    if api_id and api_hash and args.phone and args.code:
        try:
            me = asyncio.run(perform_telethon_login(int(api_id), api_hash, args.phone, args.code, args.password))
            print(f"✅ Success! Logged in as: {me.first_name} (@{me.username or 'No username'})")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Login failed: {e}")
            sys.exit(1)

    # Launch GUI if in desktop environment and not forced CLI
    if not args.cli:
        try:
            launch_gui_authenticator(default_api_id=api_id, default_api_hash=api_hash)
            return
        except Exception as ex:
            print(f"[GUI Note] Falling back to CLI mode: {ex}")

    # Fallback CLI
    print("=" * 65)
    print("✦ LAYA TELEGRAM CLI SETUP")
    print("=" * 65)
    if not api_id:
        api_id = input("Enter your Telegram API ID: ").strip()
    if not api_hash:
        api_hash = input("Enter your Telegram API Hash: ").strip()
    phone = args.phone or input("Enter your Phone (+123456789): ").strip()

    from telethon import TelegramClient
    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    client = TelegramClient(str(SESSION_PATH), int(api_id), api_hash)

    async def _cli_login():
        await client.start(phone=phone)
        me = await client.get_me()
        save_env_credentials(api_id, api_hash)
        print(f"\n✅ SUCCESS! Logged in as: {me.first_name} (@{me.username or 'No username'})")
        await client.disconnect()

    asyncio.run(_cli_login())


if __name__ == "__main__":
    main()
