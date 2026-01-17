import os

from telegram.ext import ConversationHandler

# --- States for Conversations ---
IDLE = ConversationHandler.END
(
    GET_NAME, GET_PHONE, GET_ADDRESS, GET_OCCUPATION, 
    GET_PLAN, GET_DURATION, GET_AMOUNT, GET_DUE_DATE
) = range(8)

# Admin states
ADMIN_SEARCH = 9
ADMIN_BROADCAST = 10
RENEW_AMOUNT = 11
RENEW_DURATION = 12
ADMIN_TARGETED_BROADCAST = 13
EDIT_MEMBER_FIELD = 14  # FIX #1: Edit member state

# --- Config ---
ADMIN_ID = os.getenv("ADMIN_ID")
