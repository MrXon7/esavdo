from fastapi import APIRouter
from bot.bot_instance import bot
from core.config import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    """Diagnostic health check endpoint for Render, self-ping, and Telegram bot status."""
    wh_info = {}
    try:
        wh = await bot.get_webhook_info()
        wh_info = {
            "url": wh.url,
            "pending_updates": wh.pending_update_count,
            "last_error": wh.last_error_message,
        }
    except Exception as e:
        wh_info = {"error": str(e)}

    db_info = {}
    try:
        from core.database import AsyncSessionLocal, engine
        from sqlalchemy import text
        db_info["driver"] = engine.url.drivername
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1;"))
            db_info["status"] = "connected"
    except Exception as e:
        db_info["status"] = "disconnected"
        db_info["error"] = str(e)

    return {
        "status": "ok",
        "store": settings.STORE_NAME,
        "effective_base_url": settings.effective_base_url,
        "effective_webhook_url": settings.effective_webhook_url,
        "telegram_webhook": wh_info,
        "database": db_info,
    }
