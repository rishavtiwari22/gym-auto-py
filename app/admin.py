import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
import datetime

from app.responses import db
from app.ai import ask_ai
from app.constants import (
    IDLE, ADMIN_SEARCH, ADMIN_BROADCAST, 
    RENEW_AMOUNT, RENEW_DURATION, ADMIN_TARGETED_BROADCAST,
    ADMIN_ID
)
from app.ui import get_keyboard, format_member_card

logger = logging.getLogger(__name__)

async def handle_admin_dash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for the Admin Dashboard."""
    if str(update.effective_user.id) != ADMIN_ID:
        return IDLE
        
    await update.message.reply_text(
        "🛠️ *Admin Dashboard Hub*\nChoose a category to manage your gym:",
        reply_markup=get_keyboard("admin_dash", update.effective_user.id),
        parse_mode="Markdown"
    )
    return IDLE

async def handle_admin_membership_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Membership Hub Sub-menu."""
    if str(update.effective_user.id) != ADMIN_ID:
        return IDLE
    await update.message.reply_text(
        "👥 *Membership Hub*\nManage your members and communication:",
        reply_markup=get_keyboard("admin_membership_menu", update.effective_user.id),
        parse_mode="Markdown"
    )
    return IDLE

async def handle_admin_financial_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Financial Hub Sub-menu."""
    if str(update.effective_user.id) != ADMIN_ID:
        return IDLE
    await update.message.reply_text(
        "💰 *Financial Hub*\nTrack your revenue and payments:",
        reply_markup=get_keyboard("admin_financial_menu", update.effective_user.id),
        parse_mode="Markdown"
    )
    return IDLE

async def handle_admin_intelligence_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Intelligence Hub Sub-menu."""
    if str(update.effective_user.id) != ADMIN_ID:
        return IDLE
    await update.message.reply_text(
        "📈 *Intelligence Hub*\nAnalyze gym data and AI insights:",
        reply_markup=get_keyboard("admin_intelligence_menu", update.effective_user.id),
        parse_mode="Markdown"
    )
    return IDLE

async def handle_admin_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists all active members."""
    members = db.get_all_members(status="Active")
    if not members:
        await update.message.reply_text("📭 No active members found.")
        return IDLE
    
    msg = f"📋 *All Members ({len(members)})*\n━━━━━━━━━━━━━━\n"
    for m in members[:15]:
        from app.ui import format_member_list_concise
        msg += format_member_list_concise(m) + "\n"
    
    if len(members) > 15:
        msg += f"\n_Note: Showing first 15. Use Search for others._"
        
    await update.message.reply_text(msg, parse_mode="Markdown")
    return IDLE

async def handle_admin_search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the member search flow."""
    await update.message.reply_text(
        "🔍 *Find Member*\nPlease enter the **Name, ID, or Phone** of the member you want to manage:",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    return ADMIN_SEARCH

async def handle_admin_search_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays search results with management buttons."""
    query = update.message.text
    results = db.search_members(query)
    if not results:
        await update.message.reply_text(f"🔍 No members found for `{query}`.")
        return IDLE

    await update.message.reply_text(f"🔍 Found {len(results)} matches:")
    
    for m in results[:5]:
        # Keep Search detailed as it's for management actions
        msg = format_member_card(m)
        is_active = m.get("Status") == "Active"
        status_toggle = "🚫 Deac" if is_active else "✅ Appr"
        action = "deac" if is_active else "appr"
        
        keyboard = [
            [
                InlineKeyboardButton(status_toggle, callback_data=f"{action}_{m['User ID']}"),
                InlineKeyboardButton("🔄 Renew", callback_data=f"renw_{m['User ID']}")
            ],
            [
                InlineKeyboardButton("🗑 Delete", callback_data=f"delm_{m['User ID']}")
            ]
        ]
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    await update.message.reply_text(
        "☝️ Select an action or use menu below:",
        reply_markup=get_keyboard("admin_membership_menu", update.effective_user.id),
        parse_mode="Markdown"
    )
    return IDLE

async def handle_admin_revenue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show monthly revenue report."""
    stats = db.get_revenue_stats()
    members = db.get_all_members(status="Active")
    recent_detail = ""
    for m in members[:5]:
        recent_detail += f"• *{m['Full Name']}*: ₹{m.get('Amount Paid', '0')} ({m['Plan']})\n"

    msg = (
        f"📊 *Revenue Report: {stats['month_display']}*\n"
        f"━━━━━━━━━━━━━━\n"
        f"💰 *Total Revenue*: ₹{stats['total']}\n"
        f"👤 *New Members*: {stats['new_members']}\n"
        f"💳 *Avg/Member*: ₹{stats['total']/stats['new_members'] if stats['new_members'] > 0 else 0:.0f}\n\n"
        f"📝 *Recent Payments Breakdown:*\n"
        f"{recent_detail or 'No recent payments found.'}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
    return IDLE

async def handle_admin_dues(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List members with pending dues."""
    dues = db.get_dues_report()
    if not dues:
        await update.message.reply_text("✅ All accounts are clear! No pending dues.")
        return IDLE
    
    target_ids = []
    msg = "💸 *Pending Dues Report*\n━━━━━━━━━━━━━━\n"
    for m in dues[:15]:
        target_ids.append(str(m['User ID']))
        msg += f"• *{m['Full Name']}* | Owes ₹{m.get('due_amount', 0)}\n"
    await update.message.reply_text(msg, parse_mode="Markdown")

    context.user_data['bulk_targets'] = target_ids
    keyboard = [[
        InlineKeyboardButton("⏰ Remind All", callback_data="blkr_dues"),
        InlineKeyboardButton("📢 Message All", callback_data="blkm_dues")
    ]]
    await update.message.reply_text(
        f"🎯 *Group Actions*: Found {len(target_ids)} members with dues.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return IDLE

async def handle_admin_growth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show growth stats."""
    g = db.get_growth_stats()
    msg = (
        f"📈 *Growth Analysis: {g['month_name']}*\n\n"
        f"💵 *Revenue Growth*: {g['rev_growth']}\n"
        f"👥 *New Members*: {g['member_growth']}\n\n"
        f"Current Month: ₹{g['this_month']['revenue']}\n"
        f"Last Month: ₹{g['last_month']['revenue']}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")
    return IDLE

async def handle_admin_top_active(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows top 10 most active members."""
    top_members = db.get_top_active_members()
    if not top_members:
        await update.message.reply_text("📭 No workout activity found yet.")
        return IDLE
    
    msg = "🏆 *Gym Leaderboard (Most Active)*\n━━━━━━━━━━━━━━\n"
    for i, m in enumerate(top_members):
        medal = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "•"
        msg += f"{medal} *{m['Full Name']}*: {m['workout_count']} sessions\n"
    
    await update.message.reply_text(msg, parse_mode="Markdown")
    return IDLE

async def handle_admin_payment_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows last 5 payment transactions."""
    logs = db.get_recent_transactions()
    if not logs:
        await update.message.reply_text("📭 No transaction logs found.")
        return IDLE
    
    msg = "📜 *Recent Payment Logs*\n━━━━━━━━━━━━━━\n"
    for log in logs:
        msg += (
            f"📅 *{log.get('Date')}*\n"
            f"👤 {log.get('Full Name')} (ID: {log.get('User ID')})\n"
            f"💰 ₹{log.get('Amount')} ({log.get('Action')})\n"
            f"━━━━━━━━━━━━━━\n"
        )
    await update.message.reply_text(msg, parse_mode="Markdown")
    return IDLE

async def handle_admin_occupation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show member demographic breakdown."""
    occ_data = db.get_occupation_breakdown()
    if not occ_data:
        await update.message.reply_text("No member data found for analysis.")
        return IDLE
    
    total = sum(occ_data.values())
    msg = "👥 *Member Occupation Breakdown*\n\n"
    for occ, count in occ_data.items():
        pct = (count / total) * 100
        msg += f"• *{occ}*: {count} members ({pct:.0f}%)\n"
    
    msg += f"\n📊 *Total Active Members*: {total}"
    await update.message.reply_text(msg, parse_mode="Markdown")
    
    # Optionally list members concisely by occupation
    occ_list = "📋 *Member List by Job*\n━━━━━━━━━━━━━━\n"
    for m in db.get_all_members(status="Active")[:20]:
        occ_list += f"• *{m['Full Name']}*: {m.get('Occupation', 'Other')}\n"
    await update.message.reply_text(occ_list, parse_mode="Markdown")
    return IDLE

async def handle_admin_expired(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List expired memberships."""
    if str(update.effective_user.id) != ADMIN_ID: return
    
    expired = db.get_expired_members()
    if not expired:
        return await update.message.reply_text("✅ No expired memberships found.")

    await update.message.reply_text(f"💀 *Expired Memberships*: {len(expired)}")
    
    but_active = [m for m in expired if m.get("Status") == "Active"]
    others = [m for m in expired if m.get("Status") != "Active"]

    target_ids = []
    if but_active:
        msg = "⚠️ *Expired but Active* (Check Billing):\n━━━━━━━━━━━━━━\n"
        for m in but_active[:10]:
            target_ids.append(str(m['User ID']))
            msg += f"• *{m['Full Name']}* | {m.get('days_expired')} days ago\n"
        await update.message.reply_text(msg, parse_mode="Markdown")

    if others:
        msg = "💀 *Expired & Inactive*:\n━━━━━━━━━━━━━━\n"
        for m in others[:10]:
            target_ids.append(str(m['User ID']))
            msg += f"• *{m['Full Name']}* | {m.get('days_expired')} days ago\n"
        await update.message.reply_text(msg, parse_mode="Markdown")

    context.user_data['bulk_targets'] = target_ids
    keyboard = [[
        InlineKeyboardButton("⏰ Remind All", callback_data="blkr_expired"),
        InlineKeyboardButton("📢 Message All", callback_data="blkm_expired")
    ]]
    await update.message.reply_text(
        f"🎯 *Group Actions*: Found {len(target_ids)} expired members. Remind them all?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return IDLE

async def handle_admin_inactive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists inactive members."""
    users = db.get_retention_risk()
    if not users:
        await update.message.reply_text("✅ All members are active and logging workouts!")
        return IDLE
    
    target_ids = []
    msg = "🚫 *Inactive Members (7+ days)*\n━━━━━━━━━━━━━━\n"
    for m in users[:15]:
        target_ids.append(str(m['User ID']))
        msg += f"• *{m['Full Name']}* | {m.get('inactive_days', 'N/A')} days\n"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

    context.user_data['bulk_targets'] = target_ids
    keyboard = [[
        InlineKeyboardButton("⏰ Remind All", callback_data="blkr_risk"),
        InlineKeyboardButton("📢 Message All", callback_data="blkm_risk")
    ]]
    await update.message.reply_text(
        f"🎯 *Group Actions*: Found {len(target_ids)} inactive members. Reach out to them?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return IDLE

async def handle_admin_expiring(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List memberships expiring soon."""
    expiring = db.get_expiring_soon()
    if not expiring:
        await update.message.reply_text("✅ No memberships are expiring in the next 7 days.")
        return IDLE
    
    target_ids = []
    msg = "⚠️ *Expiring in 7 Days*\n━━━━━━━━━━━━━━\n"
    for m in expiring[:15]:
        target_ids.append(str(m['User ID']))
        msg += f"• *{m['Full Name']}* | {m.get('days_left')} left\n"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

    context.user_data['bulk_targets'] = target_ids
    keyboard = [[
        InlineKeyboardButton("⏰ Remind All", callback_data="blkr_expiring"),
        InlineKeyboardButton("📢 Message All", callback_data="blkm_expiring")
    ]]
    await update.message.reply_text(
        f"🎯 *Group Actions*: Found {len(target_ids)} members expiring soon. Take action?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return IDLE

async def handle_admin_ai_advisor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates AI suggestions."""
    try:
        stats = db.get_revenue_stats()
        risk = db.get_retention_risk()
        
        prompt = (
            f"You are a Senior Gym Manager. Here is the current data:\n"
            f"- Revenue this month: ₹{stats['total']}\n"
            f"- Members at risk: {len(risk)}\n"
            f"Give 3 short, professional 'Admin Tips' to improve the gym."
        )
        
        advice = ask_ai(prompt)
        if not advice or len(advice) < 10:
            advice = "1. Review inactive members list.\n2. Plan a weekend special class.\n3. Check gym equipment maintenance."
            
        await update.message.reply_text(
            f"💡 *AI Gym Advisor Suggestions*:\n\n{advice}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"AI Advisor error: {e}")
        await update.message.reply_text("⚠️ AI Advisor is currently offline.")
    return IDLE

async def handle_admin_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts global broadcast."""
    if str(update.effective_user.id) != ADMIN_ID:
        return IDLE

    await update.message.reply_text(
        "📢 *Global Broadcast*\nType the message you want to send to **ALL active members**.",
        reply_markup=ReplyKeyboardMarkup([["❌ Cancel"]], resize_keyboard=True),
        parse_mode="Markdown"
    )
    return ADMIN_BROADCAST

async def handle_admin_broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the broadcast message."""
    broadcast_text = update.message.text
    if broadcast_text == "❌ Cancel":
        await update.message.reply_text("Broadcast cancelled.", reply_markup=get_keyboard("admin_membership_menu", update.effective_user.id))
        return IDLE

    members = db.get_all_members(status="Active")
    success_count = 0
    fail_count = 0
    status_msg = await update.message.reply_text(f"📤 Sending to {len(members)} members...")

    admin_formatted_msg = f"📢 *GYM ANNOUNCEMENT*\n\n{broadcast_text}"

    for m in members:
        try:
            await context.bot.send_message(chat_id=m['User ID'], text=admin_formatted_msg, parse_mode="Markdown")
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to broadcast to {m['User ID']}: {e}")
            fail_count += 1

    await status_msg.edit_text(
        f"✅ *Broadcast Complete*\n\n📈 Results:\n• Sent: {success_count}\n• Failed: {fail_count}",
        parse_mode="Markdown"
    )
    await update.message.reply_text("Returning to Membership Hub.", reply_markup=get_keyboard("admin_membership_menu", update.effective_user.id))
    return IDLE

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles Admin Action buttons."""
    query = update.callback_query
    data = query.data
    parts = data.split("_")
    action = parts[0]
    target_user_id = parts[1] if len(parts) > 1 else None
    
    await query.answer()

    if action == "appr":
        db.update_member_status(target_user_id, "Active")
        await query.edit_message_text(f"✅ User `{target_user_id}` has been **Approved**.")
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text="🎊 *Congratulations!*\nYour membership at *Jashpur Fitness Club* has been approved! Welcome! 💪",
                reply_markup=get_keyboard("main_menu", int(target_user_id)),
                parse_mode="Markdown"
            )
        except: pass
            
    elif action == "reje" or action == "deac":
        db.update_member_status(target_user_id, "Inactive")
        status_text = "Rejected" if action == "reje" else "Deactivated"
        await query.edit_message_text(f"🚫 User `{target_user_id}` has been **{status_text}**.")
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text="⚠️ *Membership Update*\nYour membership status has been updated to **Inactive**.",
                reply_markup=ReplyKeyboardRemove(),
                parse_mode="Markdown"
            )
        except: pass

    elif action == "delm":
        db.delete_member(target_user_id)
        await query.edit_message_text(f"🗑 User `{target_user_id}` has been **Deleted Permanently**.")

    elif action == "renw":
        context.user_data['renew_target'] = target_user_id
        await query.edit_message_text(
            f"🔄 *Renewing Member* `{target_user_id}`\n\nStep 1/2: Please enter the **Amount Paid** (₹):",
            parse_mode="Markdown"
        )
        return RENEW_AMOUNT

    elif action == "blkr":
        targets = context.user_data.get('bulk_targets', [])
        if not targets:
            await query.edit_message_text("❌ No target users found.")
            return IDLE
        
        category = target_user_id 
        templates = {
            "expired": "🔴 *Membership Expired*\nPlease renew your membership to continue! 💪",
            "risk": "👋 *We Miss You!*\nCome back and hit your goals today. 🏋️‍♂️",
            "dues": "💸 *Payment Reminder*\nYou have pending dues on your account. 🙏",
            "expiring": "⏳ *Renewal Reminder*\nYour membership is expiring soon. 🏋️‍♂️"
        }
        text = templates.get(category, "👋 Quick reminder from your gym regarding your membership!")
        
        success = 0
        for uid in targets:
            try:
                await context.bot.send_message(chat_id=uid, text=text, parse_mode="Markdown")
                success += 1
            except: pass
        await query.edit_message_text(f"✅ *Reminders Sent*: {success}/{len(targets)} members notified.")

    elif action == "blkm":
        targets = context.user_data.get('bulk_targets', [])
        if not targets:
            await query.edit_message_text("❌ No target users found.")
            return IDLE
        await query.edit_message_text(f"📢 *Targeted Messaging*\n✍️ *Please type the custom message*:", parse_mode="Markdown")
        return ADMIN_TARGETED_BROADCAST

async def admin_renew_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collect renewal amount."""
    context.user_data['renew_amount'] = update.message.text
    await update.message.reply_text(
        "📝 *Step 2/2*: Enter the **Renewal Duration** (in months):",
        reply_markup=ReplyKeyboardMarkup([["1", "3", "6", "12"]], resize_keyboard=True),
        parse_mode="Markdown"
    )
    return RENEW_DURATION

async def admin_renew_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finalize renewal."""
    try:
        months = int(update.message.text)
        target_uid = context.user_data.get('renew_target')
        amount = context.user_data.get('renew_amount')
        renewed_member = db.renew_member(target_uid, amount, months)
        
        if renewed_member:
            summary = f"✅ *Renewal Successful!*\n👤 Member: {renewed_member['Full Name']}\n💰 Paid: ₹{amount}\n📅 New Expiry: {renewed_member['Expiry Date']}\n"
            await update.message.reply_text(summary, parse_mode="Markdown", reply_markup=get_keyboard("admin_membership_menu", update.effective_user.id))
            try:
                await context.bot.send_message(
                    chat_id=target_uid,
                    text=f"🔄 *Membership Renewed!*\nYour membership has been extended until **{renewed_member['Expiry Date']}**. 💪",
                    parse_mode="Markdown"
                )
            except: pass
        else:
            await update.message.reply_text("❌ Member not found.")
    except ValueError:
        await update.message.reply_text("⚠️ Please enter a valid number of months.")
        return RENEW_DURATION
    return IDLE

async def handle_admin_targeted_broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends custom message to targets."""
    msg_text = update.message.text
    targets = context.user_data.get('bulk_targets', [])
    if not targets:
        await update.message.reply_text("❌ No users to message.")
        return IDLE

    success = 0
    for uid in targets:
        try:
            await context.bot.send_message(chat_id=uid, text=msg_text, parse_mode="Markdown")
            success += 1
        except: pass
    await update.message.reply_text(f"✅ *Custom Messages Sent*: {success}/{len(targets)}")
    return IDLE
