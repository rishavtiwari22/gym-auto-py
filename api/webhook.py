import os
import logging
from fastapi import FastAPI, Request, Response
from telegram import Update
from app.main import create_application

# Initialize FastAPI
app = FastAPI()

# Initialize Telegram Application via factory
telegram_app = create_application()

@app.on_event("startup")
async def startup():
    """Initialize the telegram application."""
    await telegram_app.initialize()

@app.post("/")
async def webhook(request: Request):
    """Handle incoming Telegram updates."""
    try:
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
    except Exception as e:
        logging.error(f"Error processing update: {e}")
    return Response(status_code=200)

@app.get("/")
async def index():
    return {"status": "Gym Bot is online", "mode": "webhook"}
