import os
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from app.responses import db
from app.constants import ADMIN_ID

# Map display button text to internal intent names
# CRITICAL: These strings must EXACTLY match the keyboard labels.
BUTTON_TO_INTENT = {
    # Hubs
    "👥 Members": "admin_membership_menu",
    "💰 Finance": "admin_financial_menu",
    "📈 Insights": "admin_intelligence_menu",
    
    # Membership
    "📋 All": "admin_list",
    "🔍 Search": "admin_search_start",
    "📢 Alert": "admin_broadcast_start",
    "🏆 Top 10": "admin_top_active",
    
    # Financial
    "📊 Sales": "admin_revenue",
    "💸 Dues": "admin_dues",
    "📈 Trends": "admin_growth",
    "📜 Logs": "admin_payment_logs",
    
    # Intelligence
    "👥 Jobs": "admin_occupation",
    "⚠️ Risks": "admin_inactive",
    "⏳ Near": "admin_expiring",
    "💀 Past": "admin_expired",
    "🤖 AI Tips": "admin_ai_advisor",
    
    # User Features
    "👤 Status": "check_membership",
    "📅 Class": "view_schedule",
    "📝 Log": "log_workout_start",
    "📜 My Logs": "user_workout_logs",
    "📊 Attendance": "view_attendance",
    "🤖 Workout": "workout",
    "🥗 Diet": "diet",
    "🕕 Clock": "gym_timing",
    "💰 Fees": "fees",
    "🏋️ Machines": "view_machines",
    "🎟️ Trial": "book_trial",
    "👥 Staff": "staff_info",
    "📜 Rules": "gym_rules",
    
    # User Hubs
    "👤 Profile": "user_profile_menu",
    "🏋️‍♂️ Training": "user_training_menu",
    "ℹ️ Info": "user_info_menu",
    
    # User Training Sub-Hubs
    "📊 Tracker": "user_tracker_menu",
    "🤖 Coach": "user_coach_menu",
    
    # User Info Sub-Hubs
    "🏢 About": "user_about_menu",
    "🛠️ Services": "user_services_menu",
    
    # Global
    "🏠 Home": "main_menu",
    "🔙 Back": "admin_dash",
    "🛠️ Admin": "admin_dash",
    "👤 Member Mode": "admin_member_mode",
    "📝 Join": "register_start",
    "☎️ Contact": "admin_contact",
    "❓ FAQ": "faq",
    "❓ Help": "help",
    
    # Attendance
    "✅ In": "check_in",
    "🚪 Out": "check_out"
}

def get_keyboard(intent: str, user_id: int) -> ReplyKeyboardMarkup:
    """Generates logical ReplyKeyboardMarkup based on current intent and membership status."""
    user_id_str = str(user_id)
    is_admin = user_id_str == ADMIN_ID
    member = db.get_member(user_id) if db else None
    is_active = member and member.get("Status") == "Active"
    
    keyboard = []

    # 1. Admin Dashboard Scenario
    if is_admin and (intent.startswith("admin_") or intent == "admin_dash"):
        if intent == "admin_dash":
            keyboard = [
                ["👥 Members", "💰 Finance"],
                ["📈 Insights", "🏠 Home"]
            ]
        elif intent == "admin_membership_menu":
            keyboard = [
                ["📋 All", "🔍 Search"],
                ["📢 Alert", "👤 Member Mode"],
                ["🔙 Back"]
            ]
        elif intent == "admin_financial_menu":
            keyboard = [
                ["📊 Sales", "💸 Dues"],
                ["📈 Trends", "📜 Logs"],
                ["🔙 Back"]
            ]
        elif intent == "admin_intelligence_menu":
            keyboard = [
                ["🏆 Top 10", "👥 Jobs"],
                ["⚠️ Risks", "⏳ Near"],
                ["💀 Past", "🤖 AI Tips"],
                ["🔙 Back"]
            ]
        else:
            keyboard = [["🔙 Back"], ["🏠 Home"]]
    # 2. New/Pending User Scenario
    elif not is_active:
        if intent == "register_start":
            return ReplyKeyboardRemove()
        
        if intent == "user_info_menu":
            keyboard = [
                ["🏢 About", "🛠️ Services"],
                ["🏠 Home"]
            ]
        elif intent == "user_about_menu":
            keyboard = [
                ["🕕 Clock", "👥 Staff"],
                ["📜 Rules", "☎️ Contact"],
                ["🏠 Home"]
            ]
        elif intent == "user_services_menu":
            keyboard = [
                ["💰 Fees", "🏋️ Machines"],
                ["🎟️ Trial", "❓ FAQ"],
                ["🏠 Home"]
            ]
        else:
            keyboard = [
                ["📝 Join"],
                ["ℹ️ Info", "❓ Help"]
            ]
            if is_admin:
                keyboard.append(["🛠️ Admin"])
    # 3. Active Member Scenario
    else:
        if intent in ["main_menu", "greeting", "help", "start", "admin_dash"]: 
            keyboard = [
                ["✅ In", "🚪 Out"],
                ["👤 Profile", "🏋️‍♂️ Training"],
                ["ℹ️ Info", "🏠 Home"]
            ]
            if is_admin:
                keyboard.insert(0, ["🛠️ Admin"]) # Specialized 1-button row at top for Admin
        elif intent == "user_profile_menu":
            keyboard = [
                ["👤 Status", "📅 Class"],
                ["🔙 Back", "🏠 Home"]
            ]
        elif intent == "user_training_menu":
            keyboard = [
                ["📊 Tracker", "🤖 Coach"],
                ["🔙 Back", "🏠 Home"]
            ]
        elif intent == "user_tracker_menu":
            keyboard = [
                ["📝 Log", "📜 My Logs"],
                ["🔙 Back", "🏠 Home"]
            ]
        elif intent == "user_coach_menu":
            keyboard = [
                ["🤖 Workout", "🥗 Diet"],
                ["🔙 Back", "🏠 Home"]
            ]
        elif intent == "user_info_menu":
            keyboard = [
                ["🏢 About", "🛠️ Services"],
                ["🔙 Back", "🏠 Home"]
            ]
        elif intent == "user_about_menu":
            keyboard = [
                ["🕕 Clock", "👥 Staff"],
                ["📜 Rules", "☎️ Contact"],
                ["🔙 Back", "🏠 Home"]
            ]
        elif intent == "user_services_menu":
            keyboard = [
                ["💰 Fees", "🏋️ Machines"],
                ["🎟️ Trial", "❓ FAQ"],
                ["🔙 Back", "🏠 Home"]
            ]
        else:
            keyboard = [["🏠 Home"]]

    # --- Parent Menu Mapping (Prevention of auto-return) ---
    # Redirect leaf intents to use their parent keyboards
    if not keyboard:
        parent_map = {
            # Admin Finance
            "admin_revenue": "admin_financial_menu",
            "admin_dues": "admin_financial_menu",
            "admin_growth": "admin_financial_menu",
            "admin_payment_logs": "admin_financial_menu",
            # Admin Intelligence
            "admin_occupation": "admin_intelligence_menu",
            "admin_inactive": "admin_intelligence_menu",
            "admin_expiring": "admin_intelligence_menu",
            "admin_expired": "admin_intelligence_menu",
            "admin_ai_advisor": "admin_intelligence_menu",
            # User Info
            "gym_timing": "user_about_menu",
            "staff_info": "user_about_menu",
            "gym_rules": "user_about_menu",
            "admin_contact": "user_about_menu",
            "fees": "user_services_menu",
            "view_facilities": "user_services_menu",
            "view_machines": "user_services_menu",
            "book_trial": "user_services_menu",
            "faq": "user_services_menu",
            # User Training
            "user_workout_logs": "user_tracker_menu",
            "log_workout_start": "user_tracker_menu",
            "view_attendance": "user_tracker_menu",
            "workout": "user_coach_menu",
            "diet": "user_coach_menu",
            "log_workout": "user_tracker_menu",
            "check_membership": "user_profile_menu",
            "view_schedule": "user_profile_menu",
        }
        if intent in parent_map:
            return get_keyboard(parent_map[intent], user_id)

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def format_member_card(m: dict) -> str:
    """Standardized detailed member display for Admin."""
    return (
        f"👤 *Member Profile*\n"
        f"━━━━━━━━━━━━━━\n"
        f"🆔 *ID*: `{m.get('User ID')}`\n"
        f"👤 *Name*: {m.get('Full Name')}\n"
        f"📱 *Phone*: {m.get('Phone', 'N/A')}\n"
        f"📍 *Address*: {m.get('Address', 'N/A')}\n"
        f"💼 *Occupation*: {m.get('Occupation', 'Other')}\n\n"
        f"💳 *Plan Details*\n"
        f"• *Plan*: {m.get('Plan')}\n"
        f"• *Duration*: {m.get('Duration (Months)', 1)} months\n"
        f"• *Paid*: ₹{m.get('Amount Paid', '0')}\n"
        f"• *Joined*: {m.get('Join Date')}\n"
        f"📅 *Expires*: {m.get('Expiry Date', 'N/A')}\n\n"
        f"🕒 *Last Activity*: {m.get('Plan History', [{'Action': 'Initial', 'Date': 'N/A'}])[-1]['Action']} on {m.get('Plan History', [{'Date': 'N/A'}])[-1]['Date']}\n"
        f"⚡ *Status*: {m.get('Status')}\n"
    )

def format_member_concise(m: dict, extra: str = "") -> str:
    """One-line summary for IQ lists (Concise)."""
    return f"• *{m.get('Full Name')}* | {extra or m.get('Occupation', 'Other')}"

def format_member_list_concise(m: dict) -> str:
    """Specific fields for All Members: Name | Phone | Plan | Join | Expiry."""
    phone = m.get('Phone', 'N/A')
    plan = m.get('Plan', 'N/A')
    join = m.get('Join Date', 'N/A')
    expiry = m.get('Expiry Date', 'N/A')
    return (
        f"• *{m.get('Full Name')}* | `{phone}`\n"
        f"  Plan: {plan} | Joined: {join}\n"
        f"  📅 *Expires*: {expiry}"
    )
