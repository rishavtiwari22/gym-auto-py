# Beginner's Guide: Create a "Visitor Log" Automation from Scratch

This tutorial focuses on building **ONE simple feature**: A bot that registers visitors, saves them to a Google Sheet, and asks an Admin for approval.

---

## 🏗 Step 1: The Foundations (No Coding Yet)

````carousel
```text
1. Get Your Bot Token
----------------------
- Open Telegram and chat with @BotFather.
- Use /newbot and follow the steps.
- COPY the API Token.
```
<!-- slide -->
```text
2. Setup Google Sheets
----------------------
- Create a new Google Sheet.
- Name it "Visitor Log".
- Column A: User ID
- Column B: Name
- Column C: Status (Pending/Approved)
```
<!-- slide -->
```text
3. Get Google Keys
------------------
- Go to Google Cloud Console.
- Create a project.
- Enable "Google Sheets API".
- Create a "Service Account" and download the JSON key.
- RENAME it to "creds.json".
- SHARE your Sheet with the email in the JSON file.
```
````

---

## 🛠 Step 2: Setting Up the "Brain" (.env)

Create a file named `.env` in your project folder. This stores your secrets:

```text
BOT_TOKEN=paste_your_telegram_token_here
ADMIN_ID=paste_your_telegram_id_here
SHEET_NAME=Visitor Log
```

---

## 🐍 Step 3: The Python Code (Small Chunks)

### A. The Database Layer (`database.py`)
This part talks to Google Sheets. 

````carousel
```python
# 1. Connect to Sheets
import gspread
from oauth2client.service_account import ServiceAccountCredentials

creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", 
        ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
client = gspread.authorize(creds)
sheet = client.open("Visitor Log").sheet1
```
<!-- slide -->
```python
# 2. Add a Visitor
def add_visitor(user_id, name):
    # Appends [ID, Name, Status] to the sheet
    sheet.append_row([str(user_id), name, "Pending"])
```
<!-- slide -->
```python
# 3. Approve a Visitor
def approve_visitor(user_id):
    # Find the user's ID in column A
    cell = sheet.find(str(user_id))
    # Update column C (3) to "Approved"
    sheet.update_cell(cell.row, 3, "Approved")
```
````

---

### B. The Bot Flow (`bot.py`)
This part manages the buttons and messages.

````carousel
```python
# 1. Start & Reply Keyboard
from telegram import ReplyKeyboardMarkup

async def start(update, context):
    # Simple button at the bottom
    keyboard = [["📝 Register as Visitor"]]
    await update.message.reply_text("Hello! Press the button to register:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
```
<!-- slide -->
```python
# 2. Register & Inline Buttons
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def handle_registration(update, context):
    user = update.effective_user
    # 1. Save to Sheet
    add_visitor(user.id, user.first_name)
    
    # 2. Notify Admin with Inline Buttons
    buttons = [[
        InlineKeyboardButton("✅ Approve", callback_data=f"appr_{user.id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reje_{user.id}")
    ]]
    await context.bot.send_message(ADMIN_ID, f"New visitor: {user.first_name}",
        reply_markup=InlineKeyboardMarkup(buttons))
```
<!-- slide -->
```python
# 3. Handling the Click (Callback)
async def handle_click(update, context):
    query = update.callback_query
    await query.answer()
    
    # data is 'appr_123...'
    action, user_id = query.data.split("_")
    
    if action == "appr":
        approve_visitor(user_id)
        await query.edit_message_text(f"Approved user {user_id}!")
        # Notify the visitor!
        await context.bot.send_message(user_id, "Welcome! You are approved.")
```
````

---

## 🚀 Step 4: Run It!

1. Install requirements: `pip install python-telegram-bot gspread oauth2client python-dotenv`
2. Run your bot: `python bot.py`
3. Send `/start` to your bot in Telegram!

---

> [!TIP]
> **Learning Point**: Every automation follows this flow: **User Input** ➔ **Save to Data** ➔ **Admin Approval** ➔ **Feedback**. 
