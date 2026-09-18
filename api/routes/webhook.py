import logging
from fastapi import APIRouter, Request, Response, status
from aiogram.types import Update

from bot.bot_instance import bot, dp
from core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Webhook"])


@router.post(settings.WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    """
    Receives webhook updates from Telegram Bot API and feeds them into aiogram Dispatcher.
    """
    try:
        data = await request.json()
        update = Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot, update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error processing telegram update: {e}", exc_info=True)
        # Always return 200 to Telegram so it doesn't repeatedly retry failed updates
        return Response(status_code=status.HTTP_200_OK)
