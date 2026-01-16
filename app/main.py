import os
import logging
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
    CommandHandler,
)
from dotenv import load_dotenv

from app.intent import detect_intent
from app.responses import handle_intent, db
from app.ai import ask_ai, GYM_CONTEXT

import warnings

# Silence deprecation warnings from libraries for a cleaner terminal
warnings.filterwarnings("ignore", category=FutureWarning)

# Configure Logging - set to WARNING to keep the terminal clean
logging.basicConfig(
    format='%(levelname)s: %(message)s',
    level=logging.WARNING
)
logger = logging.getLogger(__name__)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is missing in your .env file.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main message handler for all user interactions."""
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id
    user_message = update.message.text.strip()
    
    # Clean terminal output
    print(f"\n👤 User ({user_id}): {user_message}")

    try:
        # 1. Detect Intent
        intent = detect_intent(user_message)
        print(f"🤖 Intent: {intent}")

        # 2. Handle static/database specific queries
        response = handle_intent(intent, user_message, user_id=user_id)

        # 3. Use AI for logic if no static response is available
        if response is None:
            if intent == "workout":
                response = ask_ai(f"Create a gym workout plan for: {user_message}")
            elif intent == "diet":
                response = ask_ai(f"Create a gym diet plan for: {user_message}")
            else:
                response = ask_ai(user_message)

        await update.message.reply_text(response, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        await update.message.reply_text("⚠️ Sorry, I encountered an error. Please try again later.")


async def add_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to register a new member: /add_member <user_id> <fullname> <plan>"""
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized. This command is restricted to administrators.")
        return

    try:
        args = context.args
        if len(args) < 3:
            await update.message.reply_text("💡 Usage: `/add_member <user_id> <fullname> <plan>`\nExample: `/add_member 12345678 John Doe Gold`", parse_mode="Markdown")
            return
        
        target_id = args[0]
        full_name = " ".join(args[1:-1])
        plan = args[-1]
        
        if db:
            db.add_member(target_id, full_name, plan)
            await update.message.reply_text(f"✅ *Member Registered*\nName: {full_name}\nID: {target_id}\nPlan: {plan}", parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ Database is offline.")
    except Exception as e:
        logger.error(f"Error in add_member: {e}")
        await update.message.reply_text(f"❌ Failed to add member: {e}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by Updates."""
    logger.error(f"Exception while handling an update: {context.error}")


def main():
    """Start the bot."""
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Register error handler
    app.add_error_handler(error_handler)
    
    # Handlers
    app.add_handler(CommandHandler("add_member", add_member))
    app.add_handler(CommandHandler("start", handle_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    gym_name = GYM_CONTEXT.get('gym_name', 'Gym')
    print(f"🚀 {gym_name} Assistant is online and running...")
    app.run_polling()


if __name__ == "__main__":
    main()
