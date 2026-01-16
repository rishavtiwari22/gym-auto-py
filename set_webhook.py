#!/usr/bin/env python3
"""
Script to set or delete the Telegram webhook for your bot.
Run this AFTER deploying to Vercel.

Usage:
    python set_webhook.py set <your-vercel-url>
    python set_webhook.py delete
"""
import sys
import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ BOT_TOKEN not found in .env file")
    sys.exit(1)


def set_webhook(url: str):
    """Set the webhook URL for your bot."""
    webhook_url = f"{url}/api/webhook"
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    
    response = requests.post(api_url, json={"url": webhook_url})
    result = response.json()
    
    if result.get("ok"):
        print(f"✅ Webhook set successfully!")
        print(f"   URL: {webhook_url}")
    else:
        print(f"❌ Failed to set webhook: {result}")


def delete_webhook():
    """Delete the webhook (switch back to polling mode)."""
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
    
    response = requests.post(api_url)
    result = response.json()
    
    if result.get("ok"):
        print("✅ Webhook deleted successfully!")
        print("   You can now use polling mode locally.")
    else:
        print(f"❌ Failed to delete webhook: {result}")


def get_webhook_info():
    """Get current webhook info."""
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
    
    response = requests.get(api_url)
    result = response.json()
    
    print("📋 Current Webhook Info:")
    print(f"   URL: {result.get('result', {}).get('url', 'Not set')}")
    print(f"   Pending updates: {result.get('result', {}).get('pending_update_count', 0)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python set_webhook.py set <your-vercel-url>")
        print("  python set_webhook.py delete")
        print("  python set_webhook.py info")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "set":
        if len(sys.argv) < 3:
            print("❌ Please provide your Vercel URL")
            print("   Example: python set_webhook.py set https://your-app.vercel.app")
            sys.exit(1)
        set_webhook(sys.argv[2])
    elif command == "delete":
        delete_webhook()
    elif command == "info":
        get_webhook_info()
    else:
        print(f"❌ Unknown command: {command}")
