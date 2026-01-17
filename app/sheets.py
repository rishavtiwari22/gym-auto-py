import gspread

import os
import json

try:
    # First check for Service Account JSON in environment (Vercel/Production)
    service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if service_account_json:
        try:
            creds_dict = json.loads(service_account_json)
            gc = gspread.service_account_from_dict(creds_dict)
        except json.JSONDecodeError:
            gc = gspread.service_account(filename=service_account_json)
    else:
        # Fallback to OAuth flow (Local/Dev)
        gc = gspread.oauth(credentials_filename="credentials.json")

    # Open the spreadsheet
    sheet = gc.open("GymAutomationDB")

    # Select worksheets
    members = sheet.worksheet("Members")
    attendance = sheet.worksheet("Attendance")

    print("✅ Google Sheets connected via OAuth")
except Exception as e:
    print(f"❌ Error connecting to Google Sheets: {e}")
