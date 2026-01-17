import os
import requests
from dotenv import load_dotenv

load_dotenv()

def set_webhook():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ Error: BOT_TOKEN not found in .env")
        return

    vercel_url = input("Enter your Vercel Deployment URL (e.g., https://your-bot.vercel.app): ").strip()
    
    if not vercel_url.startswith("https://"):
        print("❌ Error: Vercel URL must start with https://")
        return

    # Clean up trailing slash to avoid double slashes
    vercel_url = vercel_url.rstrip("/")
    webhook_url = f"{vercel_url}/" 
    
    api_url = f"https://api.telegram.org/bot{token}/setWebhook?url={webhook_url}"
    
    print(f"🔄 Setting webhook to: {webhook_url}...")
    response = requests.get(api_url)
    if response.status_code == 200:
        print(f"✅ Webhook successfully set!")
        print(f"Response: {response.json()}")
    else:
        print(f"❌ Failed to set webhook. Status: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    set_webhook()
