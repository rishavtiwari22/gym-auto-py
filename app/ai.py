import os
import json
from openai import OpenAI
try:
    import google.generativeai as genai
except ImportError:
    genai = None

from dotenv import load_dotenv

load_dotenv()

# Global client variables
_openai_client = None
_gemini_model = None

def get_ai_provider():
    """Determine which AI provider to use based on available keys."""
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("GEMINI_API_KEY") and genai:
        return "gemini"
    return None

def get_openai_client():
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            _openai_client = OpenAI(api_key=api_key)
    return _openai_client

def get_gemini_model():
    global _gemini_model
    if _gemini_model is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key and genai:
            genai.configure(api_key=api_key)
            _gemini_model = genai.GenerativeModel('gemini-1.5-flash')
    return _gemini_model

def get_gym_context():
    try:
        from app.responses import db
        if db:
            return db.get_gym_info()
    except Exception as e:
        print(f"⚠️ Error getting dynamic gym context: {e}")
    
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
    provider = get_ai_provider()
    
    system_prompt = f"""
You are an intelligent assistant for {context.get('gym_name', 'our gym')}. 
Use the following gym information to answer user queries:
{json.dumps(context, indent=2)}

If the user asks about something not in the information above, provide a helpful general response or suggest they contact the gym staff at {context.get('contact', {}).get('phone', 'the counter')}.
"""
    
    if provider == "openai":
        try:
            client = get_openai_client()
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
            return f"⚠️ OpenAI Error: {e}"
            
    elif provider == "gemini":
        try:
            model = get_gemini_model()
            full_prompt = f"{system_prompt}\n\nUser Question: {prompt}"
            response = model.generate_content(full_prompt)
            return response.text.strip()
        except Exception as e:
            return f"⚠️ Gemini Error: {e}"
            
    else:
        return "❌ AI Error: No API keys configured (OpenAI or Gemini)."
