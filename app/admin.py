import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
import datetime

from app.responses import db
from app.ai import ask_ai
from app.constants import (
    IDLE, ADMIN_SEARCH, ADMIN_BROADCAST, 
    RENEW_AMOUNT, RENEW_DURATION, ADMIN_TARGETED_BROADCAST,
    EDIT_MEMBER_FIELD, ADMIN_ID  # FIX: Added EDIT_MEMBER_FIELD
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
    """Lists all members - both active and inactive."""
    all_members = db.get_all_members()
    active_members = [m for m in all_members if m.get("Status") == "Active"]
    inactive_members = [m for m in all_members if m.get("Status") != "Active"]
    
    if not all_members:
        await update.message.reply_text("📭 No members found.")
        return IDLE
    
    from app.ui import format_member_list_concise
    
    # Active Members Section
    msg = f"✅ *Active Members ({len(active_members)})*\n━━━━━━━━━━━━━━\n\n"
    if active_members:
        for m in active_members:
            msg += format_member_list_concise(m) + "\n\n"  # Double newline for spacing
    else:
        msg += "_No active members_\n\n"
    
    # Inactive Members Section
    msg += f"🚫 *Inactive Members ({len(inactive_members)})*\n━━━━━━━━━━━━━━\n\n"
    if inactive_members:
        for m in inactive_members:
            msg += format_member_list_concise(m) + "\n\n"  # Double newline for spacing
    else:
        msg += "_No inactive members_\n\n"
    
    msg += f"📊 *Total: {len(all_members)} members*"
    msg += f"\n\n💡 _Use 🔍 Search to find individual members_"
        
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
    try:
        query = update.message.text
        results = db.search_members(query)
        if not results:
            await update.message.reply_text(f"🔍 No members found for `{query}`.")
            return IDLE
        
        # FIX #1: Show only the first match (most relevant)
        m = results[0]
        
        # Build single message with member details
        msg = format_member_card(m)
        is_active = m.get("Status") == "Active"
        status_toggle = "🚫 Deac" if is_active else "✅ Appr"
        action = "deac" if is_active else "appr"
        
        keyboard = [
            [
                InlineKeyboardButton(status_toggle, callback_data=f"{action}_{m['User ID']}"),
                InlineKeyboardButton("🔄 Renew", callback_data=f"renw_{m['User ID']}"),
                InlineKeyboardButton("✏️ Edit", callback_data=f"edit_{m['User ID']}")
            ],
            [
                InlineKeyboardButton("🗑 Delete", callback_data=f"delm_{m['User ID']}")
            ]
        ]
        await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

        # Show navigation buttons
        await update.message.reply_text(
            "📍 Use menu below to navigate:",
            reply_markup=get_keyboard("admin_membership_menu", update.effective_user.id)
        )
    except Exception as e:
        logger.error(f"Error in search: {e}")
        await update.message.reply_text("❌ Search error. Please try again.")
    
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
    """List ALL members with pending dues."""
    dues = db.get_dues_report()
    if not dues:
        await update.message.reply_text("✅ All accounts are clear! No pending dues.")
        return IDLE
    
    # Sort by due date (oldest first) if available
    def get_due_date(m):
        due_date = m.get('Due Date', '')
        if due_date:
            try:
                return datetime.datetime.strptime(due_date, "%Y-%m-%d")
            except:
                return datetime.datetime.max
        return datetime.datetime.max
    
    dues_sorted = sorted(dues, key=get_due_date)
    
    target_ids = []
    msg = "💸 *Pending Dues Report*\n━━━━━━━━━━━━━━\n"
    
    total_due = 0
    for m in dues_sorted:
        target_ids.append(str(m['User ID']))
        name = m['Full Name']
        status = m.get('Status', 'Pending')
        due_amount = m.get('Due Amount', '0')
        due_date = m.get('Due Date', 'N/A')
        
        # Calculate total
        try:
            amount = float(str(due_amount).replace('₹', '').replace(',', '').strip())
            total_due += amount
        except:
            amount = 0
        
        msg += f"• *{name}*\n"
        msg += f"  Status: {status} | Due: ₹{due_amount}\n"
        if due_date != 'N/A':
            msg += f"  Due Date: {due_date}\n"
        msg += "\n"
    
    msg += f"━━━━━━━━━━━━━━\n"
    msg += f"💰 *Total Pending*: ₹{total_due:.0f}\n"
    msg += f"📊 *Members*: {len(dues)}"
    
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
    """List ALL expired memberships with revenue context."""
    if str(update.effective_user.id) != ADMIN_ID: 
        return IDLE
    
    expired = db.get_expired_members()
    if not expired:
        await update.message.reply_text("✅ No expired memberships found.")
        return IDLE  # FIX: Return IDLE instead of nothing

    but_active = [m for m in expired if m.get("Status") == "Active"]
    others = [m for m in expired if m.get("Status") != "Active"]

    target_ids = []
    total_lost_revenue = 0
    
    if but_active:
        msg = "⚠️ *Expired but Active* (URGENT - Billing Issue):\n━━━━━━━━━━━━━━\n"
        for m in but_active:
            target_ids.append(str(m['User ID']))
            name = m['Full Name']
            days_expired = m.get('days_expired', 0)
            phone = m.get('Phone', 'N/A')
            
            try:
                last_payment = float(str(m.get('Amount Paid', '0')).replace('₹', '').replace(',', '').strip())
                total_lost_revenue += last_payment
            except:
                last_payment = 0
            
            msg += f"• *{name}*\n"
            msg += f"  Days Expired: {days_expired} | Last Payment: ₹{last_payment:.0f}\n"
            msg += f"  📱 {phone}\n\n"
        await update.message.reply_text(msg, parse_mode="Markdown")

    if others:
        msg = "💀 *Expired & Inactive*:\n━━━━━━━━━━━━━━\n"
        for m in others:
            target_ids.append(str(m['User ID']))
            name = m['Full Name']
            days_expired = m.get('days_expired', 0)
            phone = m.get('Phone', 'N/A')
            
            try:
                last_payment = float(str(m.get('Amount Paid', '0')).replace('₹', '').replace(',', '').strip())
            except:
                last_payment = 0
            
            msg += f"• *{name}*\n"
            msg += f"  Days Expired: {days_expired} | Last Payment: ₹{last_payment:.0f}\n"
            msg += f"  📱 {phone}\n\n"
        await update.message.reply_text(msg, parse_mode="Markdown")

    summary_msg = f"━━━━━━━━━━━━━━\n"
    summary_msg += f"💰 *Total Lost Revenue*: ₹{total_lost_revenue:.0f}\n"
    summary_msg += f"📅 *Total Expired*: {len(expired)}"
    await update.message.reply_text(summary_msg, parse_mode="Markdown")

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
    """Lists ALL inactive members with severity categorization."""
    users = db.get_retention_risk()
    if not users:
        await update.message.reply_text("✅ All members are active and logging workouts!")
        return IDLE
    
    # Categorize by severity
    early_warning = [m for m in users if 7 <= m.get('inactive_days', 0) < 15]
    at_risk = [m for m in users if 15 <= m.get('inactive_days', 0) < 30]
    critical = [m for m in users if m.get('inactive_days', 0) >= 30]
    
    target_ids = []
    total_revenue_risk = 0
    
    # Early Warning (7-14 days)
    if early_warning:
        msg = "� *Early Warning (7-14 days)*\n━━━━━━━━━━━━━━\n"
        for m in early_warning:
            target_ids.append(str(m['User ID']))
            name = m['Full Name']
            inactive_days = m.get('inactive_days', 0)
            plan = m.get('Plan', 'N/A')
            phone = m.get('Phone', 'N/A')
            
            try:
                amount = float(str(m.get('Amount Paid', '0')).replace('₹', '').replace(',', '').strip())
                duration = int(m.get('Duration (Months)', 1))
                monthly_value = amount / duration if duration > 0 else amount
                total_revenue_risk += monthly_value
            except:
                monthly_value = 0
            
            msg += f"• *{name}* ({plan})\n"
            msg += f"  Inactive: {inactive_days} days | Value: ₹{monthly_value:.0f}\n"
            msg += f"  📱 {phone}\n\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
    
    # At Risk (15-30 days)
    if at_risk:
        msg = "🟠 *At Risk (15-30 days)*\n━━━━━━━━━━━━━━\n"
        for m in at_risk:
            if str(m['User ID']) not in target_ids:
                target_ids.append(str(m['User ID']))
            name = m['Full Name']
            inactive_days = m.get('inactive_days', 0)
            plan = m.get('Plan', 'N/A')
            phone = m.get('Phone', 'N/A')
            
            try:
                amount = float(str(m.get('Amount Paid', '0')).replace('₹', '').replace(',', '').strip())
                duration = int(m.get('Duration (Months)', 1))
                monthly_value = amount / duration if duration > 0 else amount
                total_revenue_risk += monthly_value
            except:
                monthly_value = 0
            
            msg += f"• *{name}* ({plan})\n"
            msg += f"  Inactive: {inactive_days} days | Value: ₹{monthly_value:.0f}\n"
            msg += f"  📱 {phone}\n\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
    
    # Critical (30+ days)
    if critical:
        msg = "🔴 *Critical (30+ days)*\n━━━━━━━━━━━━━━\n"
        for m in critical:
            if str(m['User ID']) not in target_ids:
                target_ids.append(str(m['User ID']))
            name = m['Full Name']
            inactive_days = m.get('inactive_days', 0)
            plan = m.get('Plan', 'N/A')
            phone = m.get('Phone', 'N/A')
            
            try:
                amount = float(str(m.get('Amount Paid', '0')).replace('₹', '').replace(',', '').strip())
                duration = int(m.get('Duration (Months)', 1))
                monthly_value = amount / duration if duration > 0 else amount
                total_revenue_risk += monthly_value
            except:
                monthly_value = 0
            
            msg += f"• *{name}* ({plan})\n"
            msg += f"  Inactive: {inactive_days} days | Value: ₹{monthly_value:.0f}\n"
            msg += f"  📱 {phone}\n\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
    
    # Summary
    summary = f"━━━━━━━━━━━━━━\n"
    summary += f"🚨 *Revenue at Risk*: ₹{total_revenue_risk:.0f}\n"
    summary += f"📅 *Total Inactive*: {len(users)}\n"
    summary += f"  🟡 Early: {len(early_warning)} | 🟠 At Risk: {len(at_risk)} | 🔴 Critical: {len(critical)}"
    await update.message.reply_text(summary, parse_mode="Markdown")

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
    """List ALL memberships expiring soon with revenue context."""
    expiring = db.get_expiring_soon()
    if not expiring:
        await update.message.reply_text("✅ No memberships are expiring in the next 7 days.")
        return IDLE
    
    target_ids = []
    msg = "⚠️ *Expiring in 7 Days*\n━━━━━━━━━━━━━━\n"
    
    total_revenue_risk = 0
    for m in expiring:
        target_ids.append(str(m['User ID']))
        name = m['Full Name']
        days_left = m.get('days_left', 0)
        plan = m.get('Plan', 'N/A')
        phone = m.get('Phone', 'N/A')
        
        # Calculate monthly value
        try:
            amount_paid = float(str(m.get('Amount Paid', '0')).replace('₹', '').replace(',', '').strip())
            duration = int(m.get('Duration (Months)', 1))
            monthly_value = amount_paid / duration if duration > 0 else amount_paid
            total_revenue_risk += monthly_value
        except:
            monthly_value = 0
        
        msg += f"• *{name}*\n"
        msg += f"  Plan: {plan} | Days Left: {days_left}\n"
        msg += f"  💰 Monthly Value: ₹{monthly_value:.0f}\n"
        msg += f"  📱 {phone}\n\n"
    
    msg += f"━━━━━━━━━━━━━━\n"
    msg += f"🚨 *Revenue at Risk*: ₹{total_revenue_risk:.0f}\n"
    msg += f"📅 *Members Expiring*: {len(expiring)}"
    
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
    try:
        broadcast_text = update.message.text
        if broadcast_text == "❌ Cancel":
            await update.message.reply_text("Broadcast cancelled.", reply_markup=get_keyboard("admin_membership_menu", update.effective_user.id))
            return IDLE

        members = db.get_all_members(status="Active")
        success_count = 0
        fail_count = 0
        status_msg = await update.message.reply_text(f"📤 Sending to {len(members)} members...")

        # FIX #2: Single announcement message to members
        admin_formatted_msg = f"📢 *GYM ANNOUNCEMENT*\n\n{broadcast_text}"

        for m in members:
            try:
                await context.bot.send_message(chat_id=m['User ID'], text=admin_formatted_msg, parse_mode="Markdown")
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to broadcast to {m['User ID']}: {e}")
                fail_count += 1

        # FIX #2: Single merged message with navigation buttons
        await status_msg.edit_text(
            f"✅ *Broadcast Complete*\n\n📈 Results:\n• Sent: {success_count}\n• Failed: {fail_count}",
            parse_mode="Markdown"
        )
        # Removed automatic "Returning to Membership Hub" message - let user navigate manually
        await update.message.reply_text(
            "Broadcast sent successfully!",
            reply_markup=get_keyboard("admin_membership_menu", update.effective_user.id)
        )
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        await update.message.reply_text("❌ Broadcast failed. Please try again.")
    
    return IDLE

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles Admin Action buttons with error handling."""
    try:
        query = update.callback_query
        data = query.data
        parts = data.split("_")
        action = parts[0]
        target_user_id = parts[1] if len(parts) > 1 else None
        
        await query.answer()

        # FIX #1: Edit Member Handlers
        if action == "edit":
            member = db.get_member(target_user_id)
            if not member:
                await query.edit_message_text(f"❌ Member {target_user_id} not found.")
                return IDLE
            
            # FIX #2: Store user_id in context for edit flow
            context.user_data['edit_user_id'] = target_user_id
            
            msg = f"✏️ *Edit Member: {member['Full Name']}*\n\n"
            msg += f"📋 *Current Details:*\n"
            msg += f"• Name: {member.get('Full Name', 'N/A')}\n"
            msg += f"• Phone: {member.get('Phone', 'N/A')}\n"
            msg += f"• Address: {member.get('Address', 'N/A')}\n\n"
            msg += "Select what to edit:"
            
            keyboard = [
                [InlineKeyboardButton("✏️ Edit Name", callback_data=f"editname_{target_user_id}")],
                [InlineKeyboardButton("📱 Edit Phone", callback_data=f"editphone_{target_user_id}")],
                [InlineKeyboardButton("📍 Edit Address", callback_data=f"editaddr_{target_user_id}")],
                [InlineKeyboardButton("❌ Cancel", callback_data="editcancel")]
            ]
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            return IDLE
        
        elif action == "editname":
            # FIX #2: Ensure user_id is stored from callback
            context.user_data['edit_user_id'] = target_user_id
            context.user_data['edit_field'] = 'name'
            await query.edit_message_text("✏️ Please enter the new name:")
            return EDIT_MEMBER_FIELD
        
        elif action == "editphone":
            # FIX #2: Ensure user_id is stored from callback
            context.user_data['edit_user_id'] = target_user_id
            context.user_data['edit_field'] = 'phone'
            await query.edit_message_text("📱 Please enter the new phone number:")
            return EDIT_MEMBER_FIELD
        
        elif action == "editaddr":
            # FIX #2: Ensure user_id is stored from callback
            context.user_data['edit_user_id'] = target_user_id
            context.user_data['edit_field'] = 'address'
            await query.edit_message_text("📍 Please enter the new address:")
            return EDIT_MEMBER_FIELD
        
        elif action == "editcancel":
            await query.edit_message_text("❌ Edit cancelled.")
            return IDLE

        elif action == "appr":
            db.update_member_status(target_user_id, "Active")
            member = db.get_member(target_user_id)
            name = member.get("Full Name", "User") if member else "User"
            
            await query.edit_message_text(
                f"✅ *Application Approved*\n"
                f"━━━━━━━━━━━━━━\n"
                f"👤 Member: *{name}*\n"
                f"🆔 ID: `{target_user_id}`\n\n"
                f"Status updated to **Active**. User notified.",
                parse_mode="Markdown"
            )
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text="🎊 *Congratulations!*\nYour membership at *Jashpur Fitness Club* has been approved! Welcome! 💪",
                    reply_markup=get_keyboard("main_menu", int(target_user_id)),
                    parse_mode="Markdown"
                )
            except: pass
                
        elif action == "reje" or action == "deac":
            status = "Inactive"
            db.update_member_status(target_user_id, status)
            member = db.get_member(target_user_id)
            name = member.get("Full Name", "User") if member else "User"
            
            status_text = "Rejected" if action == "reje" else "Deactivated"
            await query.edit_message_text(
                f"🚫 *Application {status_text}*\n"
                f"━━━━━━━━━━━━━━\n"
                f"👤 Member: *{name}*\n"
                f"🆔 ID: `{target_user_id}`\n\n"
                f"Status updated to **Inactive**. User notified.",
                parse_mode="Markdown"
            )
            try:
                msg = "⚠️ *Membership Update*\nYour membership status has been updated to **Inactive**."
                if action == "reje":
                    msg = "❌ *Application Update*\nYour membership application has been **Rejected**. Please contact the admin for details."
                
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=msg,
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
    
    except Exception as e:
        logger.error(f"Admin callback error: {e}")
        try:
            await query.answer("❌ Action failed. Please try again.", show_alert=True)
        except:
            pass
    
    return IDLE

async def handle_edit_member_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles editing a specific member field."""
    try:
        user_id = context.user_data.get('edit_user_id')
        field = context.user_data.get('edit_field')
        new_value = update.message.text
        
        if not user_id or not field:
            await update.message.reply_text("❌ Edit session expired. Please search for the member again.")
            return IDLE
        
        member = db.get_member(user_id)
        if not member:
            await update.message.reply_text(f"❌ Member {user_id} not found.")
            return IDLE
        
        # Find the member row
        row_idx = -1
        for i, m in enumerate(db.data.get("members", [])):
            if str(m.get("User ID")) == str(user_id):
                row_idx = i + 2  # +1 for 1-indexing, +1 for headers
                break
        
        if row_idx == -1:
            await update.message.reply_text(f"❌ Could not find member row.")
            return IDLE
        
        # Update based on field
        if field == 'name':
            db.members_sheet.update_cell(row_idx, 2, new_value)  # Column B = Full Name
            await update.message.reply_text(
                f"✅ Name updated to: *{new_value}*",
                reply_markup=get_keyboard("admin_membership_menu", update.effective_user.id),
                parse_mode="Markdown"
            )
        elif field == 'phone':
            db.members_sheet.update_cell(row_idx, 3, new_value)  # Column C = Phone
            await update.message.reply_text(
                f"✅ Phone updated to: *{new_value}*",
                reply_markup=get_keyboard("admin_membership_menu", update.effective_user.id),
                parse_mode="Markdown"
            )
        elif field == 'address':
            db.members_sheet.update_cell(row_idx, 4, new_value)  # Column D = Address
            await update.message.reply_text(
                f"✅ Address updated to: *{new_value}*",
                reply_markup=get_keyboard("admin_membership_menu", update.effective_user.id),
                parse_mode="Markdown"
            )
        
        # Refresh cache
        db.refresh_cache(force=True)
        
        # Clear edit session
        context.user_data.pop('edit_user_id', None)
        context.user_data.pop('edit_field', None)
        
    except Exception as e:
        logger.error(f"Edit member error: {e}")
        await update.message.reply_text(
            f"❌ Error updating member. Please try again.",
            reply_markup=get_keyboard("admin_membership_menu", update.effective_user.id)
        )
    
    return IDLE

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
            summary = f"✅ *Renewal Successful!*\n👤 Member: {renewed_member['full_name']}\n💰 Paid: ₹{amount}\n📅 New Expiry: {renewed_member['expiry_date']}\n"
            await update.message.reply_text(summary, parse_mode="Markdown", reply_markup=get_keyboard("admin_membership_menu", update.effective_user.id))
            try:
                await context.bot.send_message(
                    chat_id=target_uid,
                    text=f"🔄 *Membership Renewed!*\nYour membership has been extended until **{renewed_member['expiry_date']}**. 💪",
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
