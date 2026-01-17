import logging
from fastapi import FastAPI, Request, Response
from telegram import Update
from app.main import create_application

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI()

# Initialize Telegram Application via factory
telegram_app = create_application()

async def ensure_initialized():
    """Ensure the telegram application is initialized before use."""
    if not telegram_app._initialized:
        await telegram_app.initialize()

@app.on_event("startup")
async def startup():
    """Standard startup event for traditional servers."""
    await ensure_initialized()

@app.post("/")
async def webhook(request: Request):
    """Handle incoming Telegram updates."""
    try:
        # Ensure app is initialized (vital for serverless/cold starts)
        await ensure_initialized()
        
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
    except Exception as e:
        logger.error(f"❌ Error processing update: {e}", exc_info=True)
    return Response(status_code=200)

@app.get("/")
async def index():
    return {
        "status": "Gym Bot is online", 
        "mode": "webhook",
        "initialized": telegram_app._initialized if hasattr(telegram_app, '_initialized') else False
    }
