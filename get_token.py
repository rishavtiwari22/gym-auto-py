import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def main():
    """Shows basic usage of the Sheets API.
    Prints the token JSON for use in Render.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("❌ Error: credentials.json not found in this folder.")
                return
            
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    print("\n" + "="*50)
    print("✅ AUTHENTICATION SUCCESSFUL!")
    print("="*50)
    print("\nCOPY THE JSON CONTENT BELOW FOR RENDER:")
    print("-" * 50)
    print(creds.to_json())
    print("-" * 50)
    print("\nPut this entire JSON blob (including { and }) into an Environment Variable named:")
    print("GOOGLE_OAUTH_TOKEN")
    print("="*50)

if __name__ == '__main__':
    main()
