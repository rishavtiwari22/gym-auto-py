import os
import logging
import warnings
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
    CommandHandler,
    ConversationHandler,
    CallbackQueryHandler
)
from dotenv import load_dotenv

# Silence deprecation warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# Configure Logging
logging.basicConfig(
    format='%(levelname)s: %(message)s',
    level=logging.WARNING
)
logger = logging.getLogger(__name__)

load_dotenv()

from app.intent import detect_intent
from app.responses import handle_intent, db
from app.ai import ask_ai
from app.ui import get_keyboard, BUTTON_TO_INTENT
from app.constants import (
    IDLE, GET_NAME, GET_PHONE, GET_ADDRESS, GET_OCCUPATION, 
    GET_PLAN, GET_DURATION, GET_AMOUNT, GET_DUE_DATE,
    ADMIN_SEARCH, ADMIN_BROADCAST, RENEW_AMOUNT, RENEW_DURATION,
    ADMIN_TARGETED_BROADCAST, EDIT_MEMBER_FIELD, ADMIN_ID
)

# Import handlers from modules
from app.user import (
    start, reg_start, reg_name, reg_phone, reg_address, reg_occupation,
    reg_plan, reg_duration, reg_amount, reg_due_date, reg_final,
    handle_member_mode, handle_user_profile_menu, handle_user_info_menu,
    handle_user_about_menu, handle_user_services_menu, handle_user_training_menu,
    handle_user_tracker_menu, handle_user_coach_menu, handle_user_workout_logs,
    handle_staff_info, handle_gym_rules, handle_faq, handle_admin_contact,
    handle_view_machines, handle_check_in, handle_check_out, handle_view_attendance,
    handle_admin_dash_return, handle_message, handle_user_attendance_menu  # Added handle_message, handle_user_attendance_menu
)
from app.admin import (
    handle_admin_dash, handle_admin_membership_menu, handle_admin_financial_menu,
    handle_admin_intelligence_menu, handle_admin_list, handle_admin_search_start,
    handle_admin_search_results, handle_admin_revenue, handle_admin_dues,
    handle_admin_growth, handle_admin_top_active, handle_admin_payment_logs,
    handle_admin_occupation, handle_admin_expired, handle_admin_inactive,
    handle_admin_expiring, handle_admin_ai_advisor, handle_admin_broadcast_start,
    handle_admin_broadcast_send, admin_callback, admin_renew_amount,
    admin_renew_duration, handle_admin_targeted_broadcast_send, handle_edit_member_field
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is missing in your .env file.")

# handle_message is now imported from app.user

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Error handling update: {context.error}")

def create_application():
    """Shared application factory for polling and webhooks."""
    app = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.TEXT & (filters.Regex("^📝 Join$") | filters.Regex("(?i)register") | filters.Regex("(?i)join")), reg_start),
            MessageHandler(filters.TEXT & filters.Regex("^🔍 Search$"), handle_admin_search_start),
            MessageHandler(filters.TEXT & filters.Regex("^📢 Alert$"), handle_admin_broadcast_start),
            CallbackQueryHandler(admin_callback),
            MessageHandler(filters.TEXT, handle_message),
        ],
        states={
            GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_name)],
            GET_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_phone)],
            GET_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_address)],
            GET_OCCUPATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_occupation)],
            GET_PLAN: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_plan)],
            GET_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_duration)],
            GET_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_amount)],
            GET_DUE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_due_date)],
            ADMIN_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_search_results)],
            ADMIN_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_broadcast_send)],
            RENEW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_renew_amount)],
            RENEW_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_renew_duration)],
            ADMIN_TARGETED_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_targeted_broadcast_send)],
            EDIT_MEMBER_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_member_field)],
        },
        fallbacks=[CommandHandler("start", start)], per_message=False,
    )

    app.add_handler(conv_handler)
    app.add_error_handler(error_handler)
    return app

def main():
    app = create_application()
    print("🚀 Gym Assistant is online (Polling mode)...")
    app.run_polling()

if __name__ == "__main__":
    main()
