import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from app.responses import db
from app.constants import (
    IDLE, GET_NAME, GET_PHONE, GET_ADDRESS, GET_OCCUPATION, 
    GET_PLAN, GET_DURATION, GET_AMOUNT, GET_DUE_DATE, ADMIN_ID
)
from app.ui import get_keyboard, BUTTON_TO_INTENT
from app.intent import detect_intent
# from app.responses import handle_intent # Move inside to prevent circular issues

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """The /start command - Logic varies for members vs newcomers."""
    user = update.effective_user
    user_id = user.id
    member = db.get_member(user_id) if db else None
    
    ctx = db.get_gym_info() if db else {}
    gym_name = ctx.get("gym_name", "Jashpur Fitness Club")
    user_id_str = str(user_id)
    is_admin = user_id_str == ADMIN_ID
    
    # Check if admin has explicitly switched to user mode
    current_mode = context.user_data.get('current_mode', 'admin' if is_admin else 'user')
    
    if is_admin and current_mode == 'admin':
        message = (
            "🛠️ *Welcome, Admin!*\n\n"
            "You have full access to both the **Admin Dashboard** and the **Member Hub**.\n"
            "Select an option below to get started:"
        )
        intent = "admin_dash"
    elif member and member.get("Status") == "Active":
        message = f"💪 Welcome back, *{member.get('Full Name', user.first_name)}*!\nYour membership is active. Ready to crush your goals today?"
        intent = "main_menu"
    elif member and member.get("Status") == "Pending":
        message = (
            f"⏳ Hello *{user.first_name}*!\n\n"
            "Your registration is currently *Pending Approval* from the gym admin.\n"
            "We'll notify you here as soon as your account is activated! 🏋️‍♂️\n\n"
            "In the meantime, you can check our timings and facilities below."
        )
        intent = "user_info_menu"
    else:
        message = f"👋 Welcome to *{gym_name}*! It looks like you're not registered yet.\nChoose an option below to get started:"
        intent = "new_user"

    await update.message.reply_text(message, reply_markup=get_keyboard(intent, user_id), parse_mode="Markdown")
    return IDLE

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles all button presses and text messages."""
    user = update.effective_user
    text = update.message.text.strip()
    
    # Handle Back button with parent menu mapping
    if text == "🔙 Back":
        # Get current intent from context or default to main_menu
        current_intent = context.user_data.get('last_intent', 'main_menu')
        
        # Parent menu mapping - one step back (updated for 4-category structure)
        parent_map = {
            # Attendance
            "check_in": "user_attendance_menu",
            "check_out": "user_attendance_menu",
            "view_attendance": "user_attendance_menu",
            "user_attendance_menu": "main_menu",
            
            # Profile (includes Staff & Contact)
            "check_membership": "user_profile_menu",
            "staff_info": "user_profile_menu",
            "admin_contact": "user_profile_menu",
            "user_profile_menu": "main_menu",
            
            # Training (merged Tracker + Coach)
            "workout": "user_training_menu",
            "diet": "user_training_menu",
            "user_workout_logs": "user_training_menu",
            "user_training_menu": "main_menu",
            
            # Gym Info (Hours, Fees, Machines, Rules, FAQ)
            "gym_timing": "user_info_menu",
            "fees": "user_info_menu",
            "view_machines": "user_info_menu",
            "gym_rules": "user_info_menu",
            "faq": "user_info_menu",
            "user_info_menu": "main_menu",
        }
        
        # Get parent intent or default to main_menu
        parent_intent = parent_map.get(current_intent, "main_menu")
        
        await update.message.reply_text(
            "Going back...",
            reply_markup=get_keyboard(parent_intent, user.id)
        )
        
        # Store the new intent
        context.user_data['last_intent'] = parent_intent
        return IDLE
    
    # Map button text to intent
    intent = BUTTON_TO_INTENT.get(text)
    
    # AI detection if not a button
    if not intent:
        intent = detect_intent(text)
    
    print(f"👤 User ({user.id}): {text} | 🤖 Intent: {intent}")

    # Store current intent for Back button
    context.user_data['last_intent'] = intent
    
    # 1. Handle Hubs (Navigation)
    from app.admin import (
        handle_admin_dash, handle_admin_membership_menu, handle_admin_financial_menu,
        handle_admin_intelligence_menu, handle_admin_list, handle_admin_revenue,
        handle_admin_dues, handle_admin_growth, handle_admin_top_active,
        handle_admin_payment_logs, handle_admin_occupation, handle_admin_expired,
        handle_admin_inactive, handle_admin_expiring, handle_admin_ai_advisor,
        handle_admin_broadcast_start, handle_edit_member_field
    )
    
    hub_handlers = {
        "admin_dash": handle_admin_dash,
        "admin_membership_menu": handle_admin_membership_menu,
        "admin_financial_menu": handle_admin_financial_menu,
        "admin_intelligence_menu": handle_admin_intelligence_menu,
        "admin_member_mode": handle_member_mode,
        "user_profile_menu": handle_user_profile_menu,
        "user_info_menu": handle_user_info_menu,
        "user_attendance_menu": handle_user_attendance_menu,
        "user_training_menu": handle_user_training_menu,
        "main_menu": start,
        "admin_dash_return": handle_admin_dash_return,
        "admin_list": handle_admin_list,
        "admin_revenue": handle_admin_revenue,
        "admin_dues": handle_admin_dues,
        "admin_growth": handle_admin_growth,
        "admin_top_active": handle_admin_top_active,
        "admin_payment_logs": handle_admin_payment_logs,
        "admin_occupation": handle_admin_occupation,
        "admin_expired": handle_admin_expired,
        "admin_inactive": handle_admin_inactive,
        "admin_expiring": handle_admin_expiring,
        "admin_ai_advisor": handle_admin_ai_advisor,
        "user_workout_logs": handle_user_workout_logs,
        "staff_info": handle_staff_info,
        "gym_rules": handle_gym_rules,
        "faq": handle_faq,
        "admin_contact": handle_admin_contact,
        "view_machines": handle_view_machines,
        "check_in": handle_check_in,
        "check_out": handle_check_out,
        "view_attendance": handle_view_attendance,
    }

    if intent in hub_handlers:
        return await hub_handlers[intent](update, context)

    # 2. Handle Static Queries
    from app.responses import handle_intent as process_intent
    response = process_intent(intent, text, user_id=user.id)
    
    # 3. AI Backup
    if response is None or "I'm not sure" in response:
        from app.ai import ask_ai
        response = ask_ai(text)

    await update.message.reply_text(response, reply_markup=get_keyboard(intent, user.id), parse_mode="Markdown")
    return IDLE

async def handle_member_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Explicitly shows the Member Hub for an Admin - persists until switched back."""
    user = update.effective_user
    member = db.get_member(user.id)
    name = member.get("Full Name", user.first_name) if member else user.first_name
    
    # Store mode in context to persist it
    context.user_data['current_mode'] = 'user'
    
    await update.message.reply_text(
        f"👤 *Switched to User Mode*\n"
        f"Logged in as: {name}\n\n"
        f"You'll stay in User Mode until you switch back to Admin Mode.",
        reply_markup=get_keyboard("main_menu", user.id),
        parse_mode="Markdown"
    )
    return IDLE

async def handle_user_attendance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows Attendance Central Hub."""
    context.user_data['last_intent'] = 'user_attendance_menu'
    await update.message.reply_text(
        "📍 *Attendance & Check-In*\n━━━━━━━━━━━━━━\nCheck-in to your session or view your history:",
        reply_markup=get_keyboard("user_attendance_menu", update.effective_user.id),
        parse_mode="Markdown"
    )
    return IDLE

async def handle_user_profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows User Profile Central Hub."""
    context.user_data['last_intent'] = 'user_profile_menu'
    await update.message.reply_text(
        "👤 *Your Profile*\n━━━━━━━━━━━━━━\nCheck your status or view classes:",
        reply_markup=get_keyboard("user_profile_menu", update.effective_user.id),
        parse_mode="Markdown"
    )
    return IDLE

async def handle_user_info_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows User Info Central Hub."""
    context.user_data['last_intent'] = 'user_info_menu'
    await update.message.reply_text(
        "🏢 *Information Hub*\n━━━━━━━━━━━━━━\nSelect a category to learn more about Jashpur Fitness Club:",
        reply_markup=get_keyboard("user_info_menu", update.effective_user.id),
        parse_mode="Markdown"
    )
    return IDLE

async def handle_user_about_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows Gym About Sub-Hub."""
    context.user_data['last_intent'] = 'user_about_menu'
    await update.message.reply_text(
        "🏢 *About Jashpur Fitness*\n━━━━━━━━━━━━━━\nOur schedules, team, and rules:",
        reply_markup=get_keyboard("user_about_menu", update.effective_user.id),
        parse_mode="Markdown"
    )
    return IDLE

async def handle_user_services_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows Gym Services Sub-Hub."""
    context.user_data['last_intent'] = 'user_services_menu'
    await update.message.reply_text(
        "🛠️ *Gym Services*\n━━━━━━━━━━━━━━\nFees, tools, trials, and support:",
        reply_markup=get_keyboard("user_services_menu", update.effective_user.id),
        parse_mode="Markdown"
    )
    return IDLE

async def handle_user_training_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows User Training Central Hub."""
    context.user_data['last_intent'] = 'user_training_menu'
    await update.message.reply_text(
        "🏋️‍♂️ *Training Hub*\n━━━━━━━━━━━━━━\nTrack your progress or get AI-powered plans:",
        reply_markup=get_keyboard("user_training_menu", update.effective_user.id),
        parse_mode="Markdown"
    )
    return IDLE

async def handle_user_tracker_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows Training Tracker Sub-Hub."""
    context.user_data['last_intent'] = 'user_tracker_menu'
    await update.message.reply_text(
        "📊 *Workout Tracker*\n━━━━━━━━━━━━━━\nLog your sweat or check your history:",
        reply_markup=get_keyboard("user_tracker_menu", update.effective_user.id),
        parse_mode="Markdown"
    )
    return IDLE

async def handle_user_coach_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows AI Coach Sub-Hub."""
    context.user_data['last_intent'] = 'user_coach_menu'
    await update.message.reply_text(
        "🤖 *AI Fitness Coach*\n━━━━━━━━━━━━━━\nCustom workout and diet advice:",
        reply_markup=get_keyboard("user_coach_menu", update.effective_user.id),
        parse_mode="Markdown"
    )
    return IDLE

# --- Registration Flow ---

async def reg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initial step of registration."""
    await update.message.reply_text(
        f"👋 *Welcome to the Gym Registration!*\n\nStep 1/7: Please enter your **Full Name**:",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    return GET_NAME

async def reg_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 2: Collect Name."""
    context.user_data['reg_name'] = update.message.text
    await update.message.reply_text(
        f"📝 *Step 2/7*: Thanks, {context.user_data['reg_name']}!\nNow, please enter your **Phone Number**:",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    return GET_PHONE

async def reg_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 3: Collect Phone."""
    context.user_data['reg_phone'] = update.message.text
    await update.message.reply_text(
        "📝 *Step 3/7*: Great! What is your **Home Address**?",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    return GET_ADDRESS

async def reg_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 4: Collect Address."""
    context.user_data['reg_address'] = update.message.text
    occupations = ["Student", "Working", "Business", "Other"]
    keyboard = [[o] for o in occupations]
    await update.message.reply_text(
        "📝 *Step 4/7*: What is your **Occupation**?",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
        parse_mode="Markdown"
    )
    return GET_OCCUPATION

async def reg_occupation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 5: Collect Occupation."""
    context.user_data['reg_occupation'] = update.message.text
    if context.user_data.get('is_trial'):
        context.user_data['reg_plan'] = "Trial Pass"
        context.user_data['reg_duration'] = 0
        context.user_data['reg_amount'] = "0"
        return await reg_final(update, context)
    
    # Fetch current fees from database
    gym_info = db.get_gym_info() if db else {}
    fees = gym_info.get("fees", {})
    
    # Build plan options with fees
    plans_with_fees = []
    plan_names = ["Monthly", "Quarterly", "Yearly", "Lifetime"]
    
    for plan in plan_names:
        plan_key = plan.lower()
        fee = fees.get(plan_key, "Contact Admin")
        plans_with_fees.append(f"{plan} - {fee}")
    
    keyboard = [[p] for p in plans_with_fees]
    
    await update.message.reply_text(
        "📝 *Step 5/7*: Which **Membership Plan** are you interested in?\n\n"
        "💰 *Current Pricing:*",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
        parse_mode="Markdown"
    )
    return GET_PLAN

async def reg_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 6: Collect Plan."""
    # Extract plan name from "Plan - Fee" format
    plan_text = update.message.text
    plan_name = plan_text.split(" - ")[0] if " - " in plan_text else plan_text
    context.user_data['reg_plan'] = plan_name
    
    # For Monthly plan, ask for duration. For others, auto-set duration and calculate fee
    if plan_name.lower() == "monthly":
        await update.message.reply_text(
            "📝 *Step 6/7*: For how many **Months**? (Enter a number)",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="Markdown"
        )
        return GET_DURATION
    else:
        # Auto-set duration based on plan
        duration_map = {
            "quarterly": 3,
            "yearly": 12,
            "lifetime": 999  # Special value for lifetime
        }
        duration = duration_map.get(plan_name.lower(), 1)
        context.user_data['reg_duration'] = duration
        
        # Get fee from gym info
        gym_info = db.get_gym_info() if db else {}
        fees = gym_info.get("fees", {})
        plan_key = plan_name.lower()
        fee = fees.get(plan_key, "0")
        
        # Extract numeric value from fee string (e.g., "₹1500" -> "1500")
        import re
        fee_numeric = re.sub(r'[^0-9]', '', str(fee))
        context.user_data['reg_total_fee'] = fee_numeric  # Store as total fee
        
        # Ask for actual payment amount
        await update.message.reply_text(
            f"💰 *Total Fee*: ₹{fee_numeric}\n\n"
            f"📝 *Step 6/7*: How much have you **paid now**?\n"
            f"(Enter the amount you're paying today)",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="Markdown"
        )
        return GET_AMOUNT

async def reg_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 7: Collect Duration and calculate fee for Monthly plan."""
    dur = update.message.text
    if not dur.isdigit():
        await update.message.reply_text("Please enter a number (e.g., 1, 3, 6).")
        return GET_DURATION
    
    duration = int(dur)
    context.user_data['reg_duration'] = duration
    
    # Calculate fee based on plan and duration
    plan_name = context.user_data.get('reg_plan', 'Monthly')
    gym_info = db.get_gym_info() if db else {}
    fees = gym_info.get("fees", {})
    
    # Get monthly rate
    monthly_rate_str = fees.get('monthly', '₹1500')
    import re
    monthly_rate = int(re.sub(r'[^0-9]', '', str(monthly_rate_str)))
    
    # Calculate total
    total_fee = monthly_rate * duration
    context.user_data['reg_total_fee'] = str(total_fee)  # Store calculated total
    
    # Show calculated fee and ask for actual payment
    await update.message.reply_text(
        f"💰 *Total Fee Calculation*\n━━━━━━━━━━━━━━\n"
        f"📊 {duration} months × ₹{monthly_rate:,}/month = *₹{total_fee:,}*\n\n"
        f"📝 *Step 7/7*: How much have you **paid now**?\n"
        f"(Enter the amount you're paying today)",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    
    return GET_AMOUNT

async def reg_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 8: Collect actual payment amount."""
    amt = update.message.text
    if not amt.isdigit():
        await update.message.reply_text("Please enter a valid number (e.g., 1500, 5000).")
        return GET_AMOUNT
    
    context.user_data['reg_amount'] = amt
    
    # Check if payment is less than total fee
    total_fee = int(context.user_data.get('reg_total_fee', amt))
    paid = int(amt)
    
    if paid < total_fee:
        remaining = total_fee - paid
        
        # Show quick-select buttons for due date
        keyboard = [["7 Days", "15 Days"], ["30 Days"]]
        
        await update.message.reply_text(
            f"⚠️ *Partial Payment Detected*\n"
            f"━━━━━━━━━━━━━━\n"
            f"💰 Remaining: ₹{remaining:,}\n\n"
            f"📅 *When will you pay the remaining amount?*\n"
            f"Select a payment deadline:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
            parse_mode="Markdown"
        )
        return GET_DUE_DATE
    else:
        # Full payment, no due date needed
        context.user_data['reg_due_date'] = None
        return await reg_final(update, context)

async def reg_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Final step: Save to DB and notify admin."""
    user = update.effective_user
    data = context.user_data
    user_id = user.id
    name = data.get('reg_name') or user.full_name
    phone = data.get('reg_phone', 'N/A')
    address = data.get('reg_address', 'N/A')
    occupation = data.get('reg_occupation', 'Other')
    plan = data.get('reg_plan', 'Monthly')
    duration = data.get('reg_duration', 1)
    amount_paid = data.get('reg_amount', '0')
    total_fee = data.get('reg_total_fee', amount_paid)  # Fallback to amount_paid if not set
    due_date = data.get('reg_due_date', None)
    is_trial = data.get('is_trial', False)
    
    membership_type = "Trial" if is_trial else "Regular"
    
    # Calculate remaining balance
    try:
        paid = int(amount_paid)
        total = int(total_fee)
        remaining = total - paid
    except:
        paid = 0
        total = 0
        remaining = 0
    
    try:
        # Calculate due amount
        due_amount_str = str(remaining) if remaining > 0 else "0"
        
        db.add_member(
            user_id=user_id,
            full_name=name,
            phone=phone,
            address=address,
            occupation=occupation,
            plan=plan,
            status="Pending",  # Status is Pending until approved by admin
            membership_type=membership_type,
            duration_months=duration,
            amount_paid=amount_paid,
            due_date=due_date or "",
            due_amount=due_amount_str
        )
        
        # Send waiting message to user
        user_wait_msg = (
            f"⏳ *Registration Received!*\n"
            f"━━━━━━━━━━━━━━\n"
            f"Thank you, *{name}*! Your registration has been submitted for approval.\n\n"
            f"📝 *Summary*\n"
            f"• *Plan*: {plan}\n"
            f"• *Paid*: ₹{paid:,}\n"
            f"• *Status*: 🟡 Pending Admin Approval\n\n"
            f"You'll receive a notification once the admin approves your membership. 💪"
        )
        
        await update.message.reply_text(
            user_wait_msg,
            reply_markup=get_keyboard("main_menu", user_id),
            parse_mode="Markdown"
        )
        
        # Send comprehensive registration summary to admin with ACTION BUTTONS
        from app.constants import ADMIN_ID
        admin_msg = (
            f"🔔 *NEW REGISTRATION REQUEST*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 *PERSONAL INFORMATION*\n"
            f"• *Full Name*: {name}\n"
            f"• *User ID*: `{user_id}`\n"
            f"• *Phone*: {phone}\n"
            f"• *Address*: {address}\n"
            f"• *Occupation*: {occupation}\n\n"
            f"💳 *MEMBERSHIP DETAILS*\n"
            f"• *Plan Selected*: {plan}\n"
            f"• *Type*: {membership_type}\n"
            f"• *Duration*: {duration} months\n\n"
            f"💰 *PAYMENT INFORMATION*\n"
            f"• *Total Fee*: ₹{total:,}\n"
            f"• *Amount Paid*: ₹{paid:,}\n"
        )
        
        if remaining > 0:
            admin_msg += f"• *⚠️ Balance Due*: ₹{remaining:,}\n"
            if due_date:
                admin_msg += f"• *📅 Due Date*: {due_date}\n"
        else:
            admin_msg += f"• *✅ Payment Status*: Fully Paid\n"
        
        admin_msg += (
            f"\n━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ *ACTION REQUIRED*: Please approve or reject this user."
        )
        
        # Inline buttons for Admin approval
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"appr_{user_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reje_{user_id}")
            ]
        ]
        
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ Registration failed: {e}\nPlease contact the admin.",
            reply_markup=get_keyboard("main_menu", user_id)
        )
    
    context.user_data.clear()
    return IDLE

# --- Expanded User Features ---

async def handle_user_workout_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows last 5 workout logs for the current user."""
    user_id = update.effective_user.id
    logs = db.get_member_workouts(user_id)
    if not logs:
        await update.message.reply_text("📭 You haven't logged any workouts yet. Go for it! 💪")
        return IDLE
    
    msg = "📜 *Your Recent Workouts*\n━━━━━━━━━━━━━━\n"
    for log in logs:
        msg += (
            f"📅 *{log.get('Date')}* ({log.get('Time')})\n"
            f"🏋️‍♂️ *Type*: {log.get('Workout Type')}\n"
            f"🕒 *Duration*: {log.get('Duration')}\n"
            f"📝 *Note*: {log.get('Notes') or 'No notes'}\n"
            f"━━━━━━━━━━━━━━\n"
        )
    await update.message.reply_text(msg, reply_markup=get_keyboard("user_tracker_menu", user_id), parse_mode="Markdown")
    return IDLE

async def handle_staff_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays trainer/staff info."""
    info = db.get_gym_info()
    trainers = info.get("trainers", [])
    if not trainers:
        await update.message.reply_text("ℹ️ Trainer information is not available right now.")
        return IDLE
    
    msg = "👥 *Our Expert Trainers*\n━━━━━━━━━━━━━━\n"
    for t in trainers:
        msg += (
            f"💪 *{t.get('Name')}*\n"
            f"⭐ *Specialty*: {t.get('Specialty')}\n"
            f"📞 *Contact*: {t.get('Phone', 'N/A')}\n"
            f"━━━━━━━━━━━━━━\n"
        )
    await update.message.reply_text(msg, reply_markup=get_keyboard("user_about_menu", update.effective_user.id), parse_mode="Markdown")
    return IDLE

async def handle_gym_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays gym rules."""
    info = db.get_gym_info()
    rules = info.get("rules", [])
    if not rules:
        await update.message.reply_text("ℹ️ Gym rules are not available right now.")
        return IDLE
    
    msg = "📜 *Gym Rules & Regulations*\n━━━━━━━━━━━━━━\n"
    for i, rule in enumerate(rules, 1):
        msg += f"{i}. {rule}\n"
    await update.message.reply_text(msg, reply_markup=get_keyboard("user_about_menu", update.effective_user.id), parse_mode="Markdown")
    return IDLE

async def handle_faq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays FAQs."""
    info = db.get_gym_info()
    faqs = info.get("faq", [])
    if not faqs:
        await update.message.reply_text("ℹ️ FAQs are not available right now.")
        return IDLE
    
    msg = "❓ *Frequently Asked Questions*\n━━━━━━━━━━━━━━\n"
    for item in faqs:
        msg += f"*Q: {item.get('Question')}*\n*A*: {item.get('Answer')}\n\n"
    await update.message.reply_text(msg, reply_markup=get_keyboard("user_services_menu", update.effective_user.id), parse_mode="Markdown")
    return IDLE

async def handle_admin_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays gym owner/admin contact info."""
    info = db.get_gym_info()
    contact = info.get("contact", {})
    gym_name = info.get("gym_name", "Jashpur Fitness Club")
    
    msg = (
        f"☎️ *Contact {gym_name}*\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"👤 *Owner/Admin*: Management Team\n"
        f"📞 *Phone*: {contact.get('phone', 'N/A')}\n"
        f"📧 *Email*: {contact.get('email', 'N/A')}\n\n"
        f"Feel free to reach out for any queries or support! 💪"
    )
    await update.message.reply_text(msg, reply_markup=get_keyboard("user_about_menu", update.effective_user.id), parse_mode="Markdown")
    return IDLE

async def handle_view_machines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays all gym machines and muscles they train."""
    machines = db.get_machines() if db else []
    if not machines:
        await update.message.reply_text(
            "🏋️ *Machine Guide*\n━━━━━━━━━━━━━━\nNo machine information available. Contact the gym admin.",
            reply_markup=get_keyboard("user_services_menu", update.effective_user.id),
            parse_mode="Markdown"
        )
        return IDLE
    
    msg = "🏋️ *Gym Machine Guide*\n━━━━━━━━━━━━━━\n\n"
    for machine in machines:
        name = machine.get('Machine Name', 'Unknown')
        muscles = machine.get('Muscles Trained', 'N/A')
        desc = machine.get('Description', '')
        
        msg += f"💪 *{name}*\n"
        msg += f"🎯 *Muscles*: {muscles}\n"
        if desc:
            msg += f"📝 {desc}\n"
        msg += "\n"
    
    msg += "✨ *Tip*: Ask our trainers for proper form and technique!"
    
    await update.message.reply_text(msg, reply_markup=get_keyboard("user_services_menu", update.effective_user.id), parse_mode="Markdown")
    return IDLE

async def reg_due_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 9: Collect payment due date for partial payments."""
    selection = update.message.text.strip()
    
    from datetime import datetime, timedelta
    
    # Parse quick-select options
    days_map = {
        "7 Days": 7,
        "15 Days": 15,
        "30 Days": 30
    }
    
    if selection in days_map:
        days = days_map[selection]
        due_date = datetime.now() + timedelta(days=days)
        due_date_str = due_date.strftime("%d-%m-%Y")
        
        context.user_data['reg_due_date'] = due_date_str
        
        await update.message.reply_text(
            f"✅ Payment deadline set to: *{due_date_str}*\n"
            f"({days} days from today)",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="Markdown"
        )
        
        return await reg_final(update, context)
    else:
        # Invalid selection - show keyboard again
        keyboard = [["7 Days", "15 Days"], ["30 Days"]]
        
        await update.message.reply_text(
            "❌ Invalid selection. Please choose from the options:",
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        )
        return GET_DUE_DATE

async def handle_check_in(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Records member check-in time using session-based tracking."""
    user_id = update.effective_user.id
    
    # Get member info
    member = db.get_member(user_id) if db else None
    if not member:
        await update.message.reply_text(
            "⚠️ You need to be a registered member to check in.",
            reply_markup=get_keyboard("main_menu", user_id)
        )
        return IDLE
    
    name = member.get('Full Name', 'Member')
    
    # Check if user already has an active session
    active_session = db.get_active_session(user_id) if db else None
    if active_session:
        checkin_time = active_session.get('Check-In Time', 'Unknown')
        await update.message.reply_text(
            f"⚠️ *Already Checked In!*\n"
            f"━━━━━━━━━━━━━━\n"
            f"You're already checked in at *{checkin_time}*.\n\n"
            f"Please check out first before checking in again.",
            reply_markup=get_keyboard("main_menu", user_id),
            parse_mode="Markdown"
        )
        return IDLE
    
    # Create new session
    from datetime import datetime
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    
    try:
        # Create session in database
        if db:
            session_id = db.create_session(user_id, name, date_str, time_str)
            if session_id:
                await update.message.reply_text(
                    f"✅ *Check-In Successful!*\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"👤 *Name*: {name}\n"
                    f"📅 *Date*: {date_str}\n"
                    f"🕐 *Time*: {time_str}\n\n"
                    f"Have a great workout! 💪",
                    reply_markup=get_keyboard("main_menu", user_id),
                    parse_mode="Markdown"
                )
            else:
                raise Exception("Failed to create session")
    except Exception as e:
        logger.error(f"Check-in error: {e}")
        await update.message.reply_text(
            f"❌ Check-in failed. Please try again.",
            reply_markup=get_keyboard("main_menu", user_id)
        )
    
    return IDLE

async def handle_check_out(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Records member check-out time and calculates duration."""
    user_id = update.effective_user.id
    
    # Get member info
    member = db.get_member(user_id) if db else None
    if not member:
        await update.message.reply_text(
            "⚠️ You need to be a registered member to check out.",
            reply_markup=get_keyboard("main_menu", user_id)
        )
        return IDLE
    
    name = member.get('Full Name', 'Member')
    # Get active session
    active_session = db.get_active_session(user_id) if db else None
    if not active_session:
        await update.message.reply_text(
            f"❌ *No Active Session!*\n"
            f"━━━━━━━━━━━━━━\n"
            f"You haven't checked in yet.\n\n"
            f"Please check in first before checking out.",
            reply_markup=get_keyboard("main_menu", user_id),
            parse_mode="Markdown"
        )
        return IDLE
    
    name = member.get('Full Name', 'Member')
    
    # Get check-out time
    from datetime import datetime
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    
    try:
        # Calculate duration
        checkin_time = active_session.get('Check-In Time')
        duration_mins = db.calculate_duration_minutes(checkin_time, time_str) if db else 0
        
        # Update session with check-out
        session_id = active_session.get('Session ID')
        if db and db.update_checkout(session_id, time_str, duration_mins):
            # Format duration for display
            hours = duration_mins // 60
            mins = duration_mins % 60
            duration_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
            
            await update.message.reply_text(
                f"🚪 *Check-Out Successful!*\n"
                f"━━━━━━━━━━━━━━\n"
                f"👤 *Name*: {name}\n"
                f"📅 *Date*: {date_str}\n"
                f"🕐 *Time*: {time_str}\n"
                f"⏱️ *Duration*: {duration_str} ({duration_mins} mins)\n\n"
                f"Great session! See you next time! 👋",
                reply_markup=get_keyboard("main_menu", user_id),
                parse_mode="Markdown"
            )
        else:
            raise Exception("Failed to update checkout")
    except Exception as e:
        logger.error(f"Check-out error: {e}")
        await update.message.reply_text(
            f"❌ Check-out failed. Please try again.",
            reply_markup=get_keyboard("main_menu", user_id)
        )
    
    return IDLE


async def handle_view_attendance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows user's recent attendance history."""
    user_id = update.effective_user.id
    
    attendance = db.get_member_attendance(user_id, limit=10) if db else []
    
    if not attendance:
        await update.message.reply_text(
            "📊 *Attendance History*\n━━━━━━━━━━━━━━\nNo attendance records found. Use ✅ In and �� Out buttons to track your gym visits!",
            reply_markup=get_keyboard("user_tracker_menu", user_id),
            parse_mode="Markdown"
        )
        return IDLE
    
    # Calculate statistics
    total_visits = len([a for a in attendance if a.get('Action') == 'Check In'])
    total_duration = 0
    
    for record in attendance:
        duration_str = record.get('Duration', 'N/A')
        if duration_str != 'N/A' and 'h' in duration_str:
            try:
                parts = duration_str.replace('h', '').replace('m', '').split()
                hours = int(parts[0]) if len(parts) > 0 else 0
                minutes = int(parts[1]) if len(parts) > 1 else 0
                total_duration += hours * 60 + minutes
            except:
                pass
    
    avg_duration = total_duration // total_visits if total_visits > 0 else 0
    
    msg = (
        f"📊 *Your Attendance History*\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"📈 *Statistics*\n"
        f"• Total Visits: {total_visits}\n"
        f"• Avg Duration: {avg_duration}m\n\n"
        f"📅 *Recent Activity*\n"
    )
    
    for record in attendance[:10]:
        date = record.get('Date', 'N/A')
        time = record.get('Time', 'N/A')
        action = record.get('Action', 'N/A')
        duration = record.get('Duration', 'N/A')
        
        icon = "✅" if action == "Check In" else "🚪"
        msg += f"\n{icon} *{date}* at {time[:5]}"
        if duration != 'N/A':
            msg += f" ({duration})"
    
    msg += "\n\n💪 Keep up the great work!"
    
    await update.message.reply_text(
        msg,
        reply_markup=get_keyboard("user_tracker_menu", user_id),
        parse_mode="Markdown"
    )
    return IDLE

async def handle_admin_dash_return(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Switch admin back to admin mode from user mode."""
    user_id = update.effective_user.id
    
    # Clear user mode - return to admin mode
    context.user_data['current_mode'] = 'admin'
    
    await update.message.reply_text(
        "🛠️ *Switched to Admin Mode*\n\n"
        "You're back in Admin Mode with full dashboard access.",
        reply_markup=get_keyboard("admin_dash", user_id),
        parse_mode="Markdown"
    )
    return IDLE
