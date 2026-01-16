"""
Payment Due Reminder Scheduler
Runs daily at 9 AM to check for payments due tomorrow and send reminders
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging

logger = logging.getLogger(__name__)

async def check_payment_dues(bot, db, admin_id):
    """Check for payments due tomorrow and send reminders to admin and users."""
    try:
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%d-%m-%Y")
        logger.info(f"🔔 Checking for payment dues on {tomorrow}")
        
        # Get all members with dues tomorrow
        members_with_dues = db.get_members_with_due_date(tomorrow)
        
        if not members_with_dues:
            logger.info("✅ No payment dues tomorrow")
            return
        
        logger.info(f"📊 Found {len(members_with_dues)} members with dues tomorrow")
        
        for member in members_with_dues:
            user_id = member.get('User ID')
            name = member.get('Full Name', 'Member')
            phone = member.get('Phone', 'N/A')
            plan = member.get('Plan', 'N/A')
            duration = member.get('Duration (Months)', 'N/A')
            due_amount = member.get('Due Amount', '0')
            due_date = member.get('Due Date', tomorrow)
            
            # Skip if no due amount
            if not due_amount or due_amount == '0':
                continue
            
            # Send admin notification with inline buttons
            await send_admin_due_reminder(
                bot, admin_id, user_id, name, phone, 
                plan, duration, due_amount, due_date
            )
            
            # Send user reminder
            await send_user_due_reminder(
                bot, user_id, name, due_amount, due_date
            )
        
        logger.info("✅ Payment reminders sent successfully")
        
    except Exception as e:
        logger.error(f"❌ Error checking payment dues: {e}")
        import traceback
        traceback.print_exc()

async def send_admin_due_reminder(bot, admin_id, user_id, name, phone, plan, duration, due_amount, due_date):
    """Send payment reminder to admin with inline buttons."""
    try:
        message = (
            f"💰 *PAYMENT DUE REMINDER*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 *Name*: {name}\n"
            f"📱 *Phone*: {phone}\n"
            f"💳 *Plan*: {plan} ({duration} months)\n\n"
            f"⚠️ *Due Amount*: ₹{due_amount}\n"
            f"📅 *Due Date*: Tomorrow ({due_date})\n"
        )
        
        # Inline buttons for admin action
        keyboard = [
            [
                InlineKeyboardButton("✅ Mark as Paid", callback_data=f"paid_{user_id}"),
                InlineKeyboardButton("⏰ Not Paid Yet", callback_data=f"notpaid_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await bot.send_message(
            chat_id=admin_id,
            text=message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
        logger.info(f"✅ Admin reminder sent for {name}")
        
    except Exception as e:
        logger.error(f"❌ Error sending admin reminder: {e}")

async def send_user_due_reminder(bot, user_id, name, due_amount, due_date):
    """Send payment reminder to user."""
    try:
        message = (
            f"💰 *Payment Reminder*\n"
            f"━━━━━━━━━━━━━━\n\n"
            f"Hello {name}! 👋\n\n"
            f"Your payment is due tomorrow:\n"
            f"• *Amount*: ₹{due_amount}\n"
            f"• *Due Date*: {due_date}\n\n"
            f"Please make the payment at your earliest convenience.\n\n"
            f"Thank you! 🙏"
        )
        
        await bot.send_message(
            chat_id=user_id,
            text=message,
            parse_mode="Markdown"
        )
        
        logger.info(f"✅ User reminder sent to {name}")
        
    except Exception as e:
        logger.error(f"❌ Error sending user reminder to {user_id}: {e}")

def start_scheduler(bot, db, admin_id):
    """Start the payment reminder scheduler."""
    scheduler = AsyncIOScheduler()
    
    # Run daily at 9:00 AM
    scheduler.add_job(
        check_payment_dues,
        'cron',
        hour=9,
        minute=0,
        args=[bot, db, admin_id]
    )
    
    # Don't call scheduler.start() here - it will be started by the event loop
    logger.info("🚀 Payment reminder scheduler configured (runs daily at 9:00 AM)")
    
    return scheduler
