"""
Callback handler for payment due inline buttons
"""

from telegram import Update
from telegram.ext import ContextTypes
import logging

logger = logging.getLogger(__name__)

async def handle_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks for payment due reminders."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    # Parse callback data: "paid_USER_ID" or "notpaid_USER_ID"
    action, user_id = callback_data.split('_', 1)
    
    from app.db import db
    
    if action == "paid":
        # Mark due as paid
        success = db.mark_due_as_paid(int(user_id))
        
        if success:
            # Get member info for confirmation
            member = db.get_member(int(user_id))
            name = member.get('Full Name', 'Member') if member else 'Member'
            
            await query.edit_message_text(
                f"✅ *Payment Marked as Paid*\n"
                f"━━━━━━━━━━━━━━\n\n"
                f"👤 *Member*: {name}\n"
                f"💰 *Due Amount*: ₹0 (Cleared)\n\n"
                f"Payment record updated successfully!",
                parse_mode="Markdown"
            )
            
            logger.info(f"✅ Marked payment as paid for user {user_id}")
        else:
            await query.edit_message_text(
                "❌ Failed to update payment status. Please try again or update manually."
            )
            logger.error(f"❌ Failed to mark payment as paid for user {user_id}")
    
    elif action == "notpaid":
        # Just dismiss the notification
        await query.edit_message_text(
            f"⏰ *Payment Reminder Dismissed*\n"
            f"━━━━━━━━━━━━━━\n\n"
            f"The payment is still pending. You can follow up manually when needed."
        )
        logger.info(f"⏰ Payment reminder dismissed for user {user_id}")
