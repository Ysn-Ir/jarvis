"""
Laya Telegram One-Time Headless Authenticator
Run this script once to log into your Telegram account:
    python -m laya.tools.telegram_login
Saves the session to ~/.laya/telegram.session so Laya can send and read
messages silently in the background with zero GUI interaction.
"""

import os
import sys
import asyncio
from pathlib import Path

def main():
    print("=" * 65)
    print("✦ LAYA TELEGRAM ONE-TIME SETUP")
    print("=" * 65)
    print("\nTo enable 100% silent, background Telegram messaging & reading,")
    print("you need your free Telegram API credentials from https://my.telegram.org")
    print("=" * 65 + "\n")

    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")

    if not api_id:
        api_id = input("Enter your Telegram API ID: ").strip()
    if not api_hash:
        api_hash = input("Enter your Telegram API Hash: ").strip()

    if not api_id or not api_hash:
        print("❌ API ID and API Hash are required.")
        return

    base_dir = Path.home() / ".laya"
    base_dir.mkdir(parents=True, exist_ok=True)
    session_file = str(base_dir / "telegram.session")

    print(f"\nAuthenticating session with Telegram servers...")
    
    from telethon import TelegramClient

    async def authenticate():
        client = TelegramClient(session_file, int(api_id), api_hash)
        await client.start()
        me = await client.get_me()
        print(f"\n✅ SUCCESS! Logged in as: {me.first_name} (@{me.username or 'No username'})")
        print(f"Session saved to: {session_file}")
        print("\nSaving credentials to your .env file...")
        
        env_path = Path(r"c:\Users\khali\OneDrive\Bureau\learning\datascience\projects\jev\.env")
        lines = []
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                lines = [l for l in f.readlines() if not l.startswith(("TELEGRAM_API_ID=", "TELEGRAM_API_HASH="))]
        lines.append(f"TELEGRAM_API_ID={api_id}\n")
        lines.append(f"TELEGRAM_API_HASH={api_hash}\n")
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
            
        print("✅ Telegram headless mode is now fully enabled for Laya!")
        await client.disconnect()

    asyncio.run(authenticate())

if __name__ == "__main__":
    main()
