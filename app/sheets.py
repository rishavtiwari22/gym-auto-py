import gspread

try:
    # OAuth flow (opens browser first time or uses authorized_user.json)
    gc = gspread.oauth(credentials_filename="credentials.json")

    # Open the spreadsheet
    sheet = gc.open("GymAutomationDB")

    # Select worksheets
    members = sheet.worksheet("Members")
    attendance = sheet.worksheet("Attendance")

    print("✅ Google Sheets connected via OAuth")
except Exception as e:
    print(f"❌ Error connecting to Google Sheets: {e}")
