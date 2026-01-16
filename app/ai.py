import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Global client variable (initialized on first use)
_client = None

def get_client():
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("❌ OPENAI_API_KEY is missing in your .env file.")
        _client = OpenAI(api_key=api_key)
    return _client

# Load Gym Knowledge Base - Now dynamic via DatabaseManager
def get_gym_context():
    try:
        from app.responses import db
        if db:
            return db.get_gym_info()
    except Exception as e:
        print(f"⚠️ Error getting dynamic gym context: {e}")
    
    # Fallback to local file if DB/Sheets fails
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    INFO_PATH = os.path.join(BASE_DIR, "gym_info.json")
    try:
        if os.path.exists(INFO_PATH):
            with open(INFO_PATH, "r") as f:
                return json.load(f)
    except: pass
    return {}

def ask_ai(prompt: str) -> str:
    context = get_gym_context()
    
    system_prompt = f"""
You are an intelligent assistant for {context.get('gym_name', 'our gym')}. 
Use the following gym information to answer user queries:
{json.dumps(context, indent=2)}

If the user asks about something not in the information above, provide a helpful general response or suggest they contact the gym staff at {context.get('contact', {}).get('phone', 'the counter')}.
"""
    try:
        client = get_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ AI Error: {e}"
