import logging
from fastapi import FastAPI, Request, Response
from telegram import Update
from app.main import create_application
from app.responses import db
from app.constants import ADMIN_ID
from app.scheduler import start_scheduler
from contextlib import asynccontextmanager

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Telegram Application via factory
telegram_app = create_application()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI (replaces startup/shutdown events)."""
    # Initialize Bot
    if not telegram_app._initialized:
        await telegram_app.initialize()
    
    # Start Scheduler (for Render persistent background tasks)
    if db and ADMIN_ID:
        try:
            scheduler = start_scheduler(telegram_app.bot, db, ADMIN_ID)
            scheduler.start()
            logger.info("✅ Payment Reminder Scheduler started in lifespan.")
        except Exception as e:
            logger.error(f"❌ Failed to start scheduler in lifespan: {e}")
            
    yield
    # Shutdown logic if needed
    if telegram_app._initialized:
        await telegram_app.shutdown()

# Initialize FastAPI with Lifespan
app = FastAPI(lifespan=lifespan)

@app.post("/")
async def webhook(request: Request):
    """Handle incoming Telegram updates."""
    try:
        # Ensure initialized (vital for serverless cold starts)
        if not telegram_app._initialized:
            await telegram_app.initialize()
            
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)
        await telegram_app.process_update(update)
    except Exception as e:
        logger.error(f"❌ Error processing update: {e}", exc_info=True)
    return Response(status_code=200)

@app.get("/")
async def index():
    db_status = "Not Initialized"
    member_count = 0
    if db:
        db_status = "Connected" if db.members_sheet else "Connection Failed"
        member_count = len(db.data.get("members", []))
        
    return {
        "status": "Gym Bot is online", 
        "mode": "webhook",
        "initialized": telegram_app._initialized if hasattr(telegram_app, '_initialized') else False,
        "database": {
            "status": db_status,
            "members_loaded": member_count,
            "sheets_enabled": os.getenv("ENABLE_SHEETS", "true")
        }
    }
