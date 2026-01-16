"""
Vercel serverless function to handle Telegram webhook updates.
"""
import os
import json
import logging
from http.server import BaseHTTPRequestHandler
import asyncio

from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from dotenv import load_dotenv

# Import your existing modules
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.intent import detect_intent
from app.responses import handle_intent, db
from app.ai import ask_ai, GYM_CONTEXT

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main message handler for all user interactions."""
    if not update.message or not update.message.text:
        return

    user_id = update.effective_user.id
    user_message = update.message.text.strip()

    try:
        intent = detect_intent(user_message)
        response = handle_intent(intent, user_message, user_id=user_id)

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
    """Admin command to register a new member."""
    if str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized.")
        return

    try:
        args = context.args
        if len(args) < 3:
            await update.message.reply_text(
                "💡 Usage: `/add_member <user_id> <fullname> <plan>`",
                parse_mode="Markdown"
            )
            return

        target_id = args[0]
        full_name = " ".join(args[1:-1])
        plan = args[-1]

        if db:
            db.add_member(target_id, full_name, plan)
            await update.message.reply_text(
                f"✅ *Member Registered*\nName: {full_name}\nID: {target_id}\nPlan: {plan}",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("⚠️ Database is offline.")
    except Exception as e:
        logger.error(f"Error in add_member: {e}")
        await update.message.reply_text(f"❌ Failed to add member: {e}")


async def process_update(update_data: dict):
    """Process incoming Telegram update."""
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Add handlers
    application.add_handler(CommandHandler("add_member", add_member))
    application.add_handler(CommandHandler("start", handle_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Initialize the application
    await application.initialize()

    # Process the update
    update = Update.de_json(update_data, application.bot)
    await application.process_update(update)

    # Shutdown
    await application.shutdown()


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler."""

    def do_GET(self):
        """Health check endpoint."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "message": "Gym Bot is running!"}).encode())

    def do_POST(self):
        """Handle incoming webhook from Telegram."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            update_data = json.loads(post_data.decode('utf-8'))

            # Run the async handler
            asyncio.run(process_update(update_data))

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())

        except Exception as e:
            logger.error(f"Webhook error: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())
