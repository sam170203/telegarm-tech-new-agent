#!/usr/bin/env python3
"""Get your Telegram chat ID by sending a message to the bot.

Loads TELEGRAM_BOT_TOKEN from .env (or the environment).
"""

import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    print("✗ TELEGRAM_BOT_TOKEN is not set. Add it to .env or export it.")
    sys.exit(1)


def get_chat_id():
    """Fetch the chat ID from the first message to the bot."""
    try:
        response = httpx.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        )
        data = response.json()

        if data.get("ok") and data.get("result"):
            update = data["result"][0]
            chat_id = update["message"]["chat"]["id"]
            username = update["message"]["from"].get("username", "unknown")

            print(f"✓ Chat ID found: {chat_id}")
            print(f"  Username: @{username}")
            print(f"\nAdd this to your .env file:")
            print(f"  TELEGRAM_CHAT_ID={chat_id}")
            return chat_id
        else:
            print("✗ No messages found yet.")
            print("  Send a message to your bot first, then run this again.")
            return None

    except Exception as e:
        print(f"✗ Error: {e}")
        return None


if __name__ == "__main__":
    chat_id = get_chat_id()
    sys.exit(0 if chat_id else 1)
