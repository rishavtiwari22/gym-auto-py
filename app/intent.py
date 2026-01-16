from app.ai import ask_ai

def get_gym_name():
    try:
        from app.responses import db
        if db:
            return db.get_gym_info().get("gym_name", "the gym")
    except:
        pass
    return "the gym"

def detect_intent(message: str) -> str:
    """Detects the user's intent using GPT-powered strict classification with gym context."""
    
    gym_name = get_gym_name()
    
    prompt = f"""
You are the AI brain of '{gym_name}'. 
Your ONLY job is to classify the user's message into the correct category (intent).

LISTED INTENTS:
- greeting: "Hi", "Hello", "Hey", "Good morning". 
- goodbye: "Bye", "Thanks", "Thank you", "See you later".
- help: "What can you do?", "Help me", "How does this work?", "/help", "/start".
- gym_timing: Questions about opening hours, closing hours, or Sunday timings.
- fees: Questions about price, membership cost, plans (Gold, Basic, Yearly).
- workout: Asking for an exercise routine, weight loss training, or "make me a plan".
- diet: Asking for food advice, meal plans, or "what should I eat?".
- log_workout: User reporting their exercise like "I did x reps" or "Add my workout".
- check_membership: User asking about their status, join date, or "Am I active?".
- view_schedule: Asking for class times, Yoga timings, or "What is on today?".
- view_facilities: Asking about equipment, machines, AC, showers, or "What do you have?".
- [NEW] register_start: Asking to join the gym, "Regsiter now", "Become a member", "Sign up", or "I want to join".
- book_trial: Asking to join for a day, "Can I try?", "Free trial", or "Trial pass".
- unknown: ONLY use if the message is completely spam or unrelated to anything above.

RULES:
1. Always prefer a specific gym intent over 'unknown'.
2. '/start' and '/help' are always the 'help' intent.
3. Be efficient. Choose the one that matches the core meaning.

User message: "{message}"

Reply ONLY with the exact intent name from the list above. No other text.
"""

    intent = ask_ai(prompt).lower().strip().replace(" ", "_")
    
    # Strict validation
    allowed_intents = [
        "greeting", "goodbye", "help", "gym_timing", "fees", 
        "workout", "diet", "log_workout", "check_membership", 
        "view_schedule", "view_facilities", "book_trial", "register_start", "unknown"
    ]
    if intent not in allowed_intents:
        return "unknown"
        
    return intent
