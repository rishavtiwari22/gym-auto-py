# Comprehensive Guide: Building a Telegram & Google Sheets Automation System

This tutorial will take you from zero to a fully functional, cloud-deployed automation system using **Python**, **Telegram**, and **Google Sheets**.

---

## 🛠 Phase 1: Creating Your Telegram Bot
We will use **BotFather**, the official Telegram tool for creating bots.

1. **Open Telegram** and search for `@BotFather`.
2. **Start the Chat**: Press the **Start** button at the bottom.
3. **Create New Bot**: Type `/newbot` or click it in the menu.
4. **Choose a Name**: Type a name for your bot (e.g., `My Gym Assistant`).
5. **Choose a Username**: Type a unique username ending in `bot` (e.g., `super_gym_auto_bot`).
6. **Save your Token**: BotFather will reply with an **API Token** (a long string of numbers and letters). 
   > [!IMPORTANT]
   > Keep this token secret! You will need it later for your `.env` file.

---

## 📊 Phase 2: Setting Up the Google Sheets "Database"
We will use Google Sheets as a free and easy-to-view database.

### 1. Create the Sheet
1. Open [Google Sheets](https://sheets.new).
2. Create a new sheet named `Gym Automation DB`.
3. Create a worksheet named `members` with these headers in **Row 1**:
   `User ID | Full Name | Phone | Address | Occupation | Plan | Status | Joined Date`

### 2. Enable Google Cloud API
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. **Create Project**: 
   - Look at the top left (next to "Google Cloud"). Click the **Select a project** dropdown.
   - Click the blue **NEW PROJECT** button in the top right of that popup.
   - Enter `Gym Bot Project` and click the blue **CREATE** button.
3. **Wait for notification**: Wait for the bell icon (top right) to show it's created. Click **SELECT PROJECT**.
4. **Enable Apps**:
   - Click the **Search bar** at the top. Type `Google Sheets API`.
   - Click the first result. Press the big blue **ENABLE** button.
   - Search again for `Google Drive API`. Click it and press **ENABLE**.

### 3. Create Service Account (The "Robot" Account)
1. Using the Search bar, type `Service Accounts` and click it.
2. Click the **+ CREATE SERVICE ACCOUNT** button near the top.
3. **Step 1**: Type `gym-bot-manager` in the name field. Click **CREATE AND CONTINUE**.
4. **Step 2**: Click "Select a role". Type `Editor` and select **Project > Editor**. Click **CONTINUE**.
5. **Step 3**: Click **DONE**.
6. **Download the Key File**:
   - In the list, click the **Email address** of your new service account.
   - Click the **KEYS** tab at the top.
   - Click the **ADD KEY** dropdown -> **Create new key**.
   - Make sure **JSON** is selected. Click **CREATE**.
   - A file will download automatically (keep this safe!).
7. **Share the Sheet**:
   - Open your downloaded JSON file in a text editor.
   - Find the line `"client_email": "..."`. Copy the email address inside the quotes.
   - Go to your Google Sheet -> Click the green **Share** button.
   - Paste the email address. **Uncheck** "Notify people". Click **Share**.

---

## 💻 Phase 3: Project Structure & Local Setup
Create a folder for your project and add these files.

### 1. File Structure
```text
gym-automation/
├── app/
│   ├── __init__.py
│   ├── db.py          # Database logic
│   ├── user.py        # User interaction
│   └── admin.py       # Admin approval logic
├── .env               # Secrets (Token, IDs)
├── requirements.txt   # Dependencies
├── main.py            # Entry point
└── credentials.json   # Google Cloud Keys
```

### 2. Install Dependencies
Create a terminal in your folder and run:
```bash
pip install python-telegram-bot gspread oauth2client python-dotenv
```

---

## ⚙️ Phase 4: Writing the Code

### 1. The Database Layer (`app/db.py`)
We use `gspread` to talk to Google Sheets. Let's break it down:

````carousel
```python
# A. Setup & Authentication
import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)
sheet = client.open("Gym Automation DB").worksheet("members")
```
<!-- slide -->
```python
# B. Adding a Row
def add_member(user_id, name, status="Pending"):
    """Adds a new member to the sheet."""
    # We append a list representing one row
    sheet.append_row([str(user_id), name, "N/A", "N/A", status])
```
<!-- slide -->
```python
# C. Updating a Cell
def update_member_status(user_id, new_status):
    """Finds a user and updates their status."""
    cell = sheet.find(str(user_id))
    # Update row X, column 5 (Status)
    sheet.update_cell(cell.row, 5, new_status)
```
````

### 2. The User Flow (`app/user.py`)
Handling steps one-by-one:

````carousel
```python
# A. Start the Conversation
async def reg_start(update, context):
    await update.message.reply_text("👋 Welcome! What is your name?")
    return GET_NAME
```
<!-- slide -->
```python
# B. Save Name & Submit
async def reg_name(update, context):
    context.user_data['name'] = update.message.text
    
    # Save to Sheet as 'Pending'
    db.add_member(update.effective_user.id, update.message.text)
    
    await update.message.reply_text("✅ Submitted for approval!")
    return await notify_admin(update, context)
```
<!-- slide -->
```python
# C. Notify Admin with Buttons
async def notify_admin(update, context):
    keyboard = [[
        InlineKeyboardButton("✅ Approve", callback_data=f"appr_{user_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reje_{user_id}")
    ]]
    await context.bot.send_message(ADMIN_ID, "New request!", 
                                 reply_markup=InlineKeyboardMarkup(keyboard))
```
````

### 3. The Admin Logic (`app/admin.py`)
Processing the buttons:

````carousel
```python
# A. Get the Button Data
async def admin_callback(update, context):
    query = update.callback_query
    await query.answer() # Makes the 'loading' go away
    
    # data is 'appr_123' or 'reje_123'
    action, target_id = query.data.split("_")
```
<!-- slide -->
```python
# B. Handle Approval
if action == "appr":
    db.update_member_status(target_id, "Active")
    await query.edit_message_text("✅ Approved!")
    await context.bot.send_message(target_id, "Welcome!")
```
<!-- slide -->
```python
# C. Handle Rejection
elif action == "reje":
    db.update_member_status(target_id, "Rejected")
    await query.edit_message_text("❌ Rejected.")
```
````

---

## 🚀 Phase 5: Going Live (Deployment)
We use GitHub and Render to keep the bot running 24/7.

1. **GitHub**: Create a private repo and push your code. **DO NOT push credentials.json or .env**.
2. **Render**:
   - Create a Web Service.
   - Connect your GitHub repo.
   - Set **Environment Variables**: Add your `BOT_TOKEN`, `ADMIN_ID`, etc., in the Render Dashboard.
   - Set the Start Command: `python main.py`.

---

> [!TIP]
> **Pro Detail**: Always use `try...except` blocks when sending messages or updating sheets to prevent the bot from crashing if one service is slow!
