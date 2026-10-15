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
            # Check products columns
            try:
                res = await session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'products';"))
                cols = [row[0] for row in res.fetchall()]
                db_info["product_columns"] = cols
            except Exception as e_col:
                db_info["columns_error"] = str(e_col)
            
            # Try a quick product query test
            try:
                from models.product import Product
                from sqlalchemy import select
                p_res = await session.execute(select(Product).limit(1))
                p = p_res.scalar_one_or_none()
                db_info["sample_product"] = p.name if p else "none"
            except Exception as e_prod:
                db_info["product_query_error"] = str(e_prod)
    except Exception as e:
        db_info["error"] = str(e)

    return {
        "status": "ok",
        "store": settings.STORE_NAME,
        "effective_base_url": settings.effective_base_url,
        "effective_webhook_url": settings.effective_webhook_url,
        "telegram_webhook": wh_info,
        "database": db_info,
    }
