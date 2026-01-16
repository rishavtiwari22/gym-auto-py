from typing import Optional
from app.db import DatabaseManager
from app.ai import ask_ai
import os

# Initialize DatabaseManager carefully
try:
    db = DatabaseManager()
except Exception:
    db = None


def handle_intent(intent: str, user_message: str, user_id: Optional[int] = None) -> str:
    """
    Handles detected intents by returning a formatted response.
    All logic is centralized here to prevent AI from chatting directly.
    """
    # Fetch dynamic gym context
    ctx = db.get_gym_info() if db else {}
    gym_name = ctx.get("gym_name", "our gym")
    timings = ctx.get("timings", {})
    fees = ctx.get("fees", {})
    facilities = ctx.get("facilities", [])
    
    # 1. Basic Conversational Intents
    if intent == "greeting":
        return f"👋 Hello! Welcome to *{gym_name}*. I'm your Fitness Assistant. How can I help you reach your goals today?"

    if intent == "goodbye":
        return "🙌 You're very welcome! Keep pushing your limits. See you next time! 🏋️‍♂️"

    if intent == "help":
        return (
            "🤖 *How can I help you today?*\n"
            "━━━━━━━━━━━━━━\n"
            "• 🕕 *Timings*: When do we open?\n"
            "• 💰 *Fees*: Membership pricing.\n"
            "• 🏋️‍♂️ *Facilities*: What's inside?\n"
            "• 🎟️ *Trial*: Grab a free pass!\n"
            "• 👤 *Status*: Your membership info.\n"
            "• 🏋️‍♂️ *Plans*: AI Workout/Diet plans."
        )

    # 2. Information Intents
    if intent == "gym_timing":
        mon_sat = timings.get("monday_to_saturday", "6 AM - 10 PM")
        sun = timings.get("sunday", "8 AM - 12 PM")
        return (
            f"🕕 *Gym Timings*\n━━━━━━━━━━━━━━\n"
            f"📅 *Mon - Sat*: {mon_sat}\n"
            f"☀️ *Sunday*: {sun}\n\n"
            "Come sweat with us today! 🏋️‍♂️"
        )

    if intent == "fees":
        if not fees:
            return "💰 Membership details are being updated. Please check back soon!"
        
        fee_lines = []
        for plan, price in fees.items():
            display_name = plan.replace("_", " ").title()
            fee_lines.append(f"• *{display_name}*: {price}")
        
        fee_list = "\n".join(fee_lines)
        return (
            f"💰 *Our Membership Plans*\n━━━━━━━━━━━━━━\n"
            f"{fee_list}\n\n"
            f"✨ *Special Offer*: Ask about our transformation plans for maximum value!"
        )

    if intent == "view_facilities":
        fac_list = "\n".join([f"• {f}" for f in facilities])
        return (
            f"🏋️‍♂️ *Our Premium Facilities*\n━━━━━━━━━━━━━━\n"
            f"{fac_list or 'Contact us for details.'}\n\n"
            "Everything you need to reach your peak performance! 🔥"
        )

    if intent == "book_trial":
        return (
            "🎟️ *Claim your 1-Day Trial Pass!*\n━━━━━━━━━━━━━━\n"
            "We're excited to have you at *Jashpur Fitness Club*! To book your trial, we just need a few basic details for your digital pass.\n\n"
            "Click **📝 Join** to get started and select 'Trial' when prompted! 🚀"
        )

    # 3. AI-Powered Plan Generation (Internalized)
    if intent == "workout":
        print(f"🧠 Generating Workout Plan for: {user_message}")
        return ask_ai(f"Create a professional gym workout plan based on this request: {user_message}. Keep it concise and formatted with bullet points.")

    if intent == "diet":
        print(f"🥗 Generating Diet Plan for: {user_message}")
        return ask_ai(f"Create a professional gym diet plan based on this request: {user_message}. Keep it concise and formatted with bullet points.")

    # 4. Database Intents
    if intent == "check_membership":
        if not db:
            return "⚠️ Membership system is offline."
        
        details = db.get_member(user_id)
        if details:
            return (
                f"👤 *Your Membership Profile*\n"
                f"━━━━━━━━━━━━━━\n"
                f"🆔 *User ID*: `{details.get('User ID')}`\n"
                f"👤 *Name*: {details.get('Full Name')}\n"
                f"📱 *Phone*: {details.get('Phone', 'N/A')}\n"
                f"📍 *Address*: {details.get('Address', 'N/A')}\n"
                f"💼 *Occupation*: {details.get('Occupation', 'Other')}\n\n"
                f"💳 *Subscription Details*\n"
                f"• *Current Plan*: {details.get('Plan')}\n"
                f"• *Duration*: {details.get('Duration (Months)', 1)} months\n"
                f"• *Amount Paid*: ₹{details.get('Amount Paid', '0')}\n"
                f"• *Joined On*: {details.get('Join Date')}\n"
                f"📅 *Expiry Date*: {details.get('Expiry Date', 'N/A')}\n\n"
                f"⚡ *Current Status*: {details.get('Status')}\n"
                f"━━━━━━━━━━━━━━\n"
                f"💪 _Keep up the great work!_"
            )
        return "❌ Membership records not found for your ID. Please contact the gym admin to register."

    if intent == "view_schedule":
        if not db:
            return "⚠️ Schedule system is offline."
        
        classes = db.get_classes()
        if not classes:
            return "📅 No classes are currently scheduled."
        
        schedule_text = "📅 *Class Schedule*\n━━━━━━━━━━━━━━\n"
        for c in classes:
            schedule_text += f"• *{c.get('Class Name')}*\n  🕒 {c.get('Time')} | 👤 {c.get('Instructor')}\n"
        return schedule_text

    if intent == "log_workout":
        if not db:
            return "⚠️ Workout logging is offline."
        
        # Check if user actually provided details
        if len(user_message.split()) <= 1 and (user_message.lower() == "log" or "📝" in user_message):
            return "📝 I'm ready! Use the format: `Log [workout name]` (e.g., *Log Running 30 mins*) and I'll save it for you."
        
        # Parsing logic (AI assisted for simplicity and robustness)
        extraction_prompt = f"Extract workout details from this message: '{user_message}'. Return JSON with keys: type, duration, notes. Example: 'Log Running 30m' -> {{'type': 'Running', 'duration': '30m', 'notes': ''}}. If duration or notes are missing, use '60m' for duration and empty string for notes. Reply ONLY with JSON."
        import json
        try:
            raw_json = ask_ai(extraction_prompt).strip()
            # Clean possible markdown wrap
            if "```json" in raw_json:
                raw_json = raw_json.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_json:
                raw_json = raw_json.split("```")[1].split("```")[0].strip()
            
            data = json.loads(raw_json)
            w_type = data.get("type", "Workout")
            w_dur = data.get("duration", "60m")
            w_notes = data.get("notes", "")
            
            db.log_workout(user_id, w_type, w_dur, w_notes)
            return f"✅ *Workout Logged!*\n━━━━━━━━━━━━━━\n🏋️‍♂️ *Type*: {w_type}\n🕒 *Duration*: {w_dur}\n📝 *Notes*: {w_notes or 'None'}\n\nKeep it up! 💪"
        except Exception as e:
            print(f"Error logging workout: {e}")
            return "❌ Sorry, I couldn't understand those workout details. Please try: `Log [Activity] [Duration]`"

    # 5. Fallback for Unknown
    return (
        "🤔 I'm not sure I understand that. I'm specialized in gym-related queries like timings, fees, class schedules, and workout plans.\n\n"
        "Type /help to see what I can do!"
    )
