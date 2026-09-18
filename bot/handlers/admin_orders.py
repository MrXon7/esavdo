import asyncio
import logging
from aiogram import Router, F, types
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.database import AsyncSessionLocal
from core.cache import get_cached_store_settings, set_cached_store_settings
from models.admin import Admin
from models.order import Order, OrderStatus
from models.settings import StoreSettings
from bot.services.notifier import notify_customer_order_status, STATUS_TRANSLATIONS

logger = logging.getLogger(__name__)
from core.config import settings

router = Router(name="admin_orders_router")


@router.callback_query(F.data.startswith("order_confirm:") | F.data.startswith("order_cancel:"))
async def handle_order_action(query: types.CallbackQuery):
    """
    Handles inline buttons '✅ Tasdiqlash' and '❌ Rad etish' from admin group.
    """
    action, order_id_str = query.data.split(":", 1)
    if not order_id_str.isdigit():
        await query.answer("Noto'g'ri buyurtma ID", show_alert=True)
        return

    order_id = int(order_id_str)
    new_status = (
        OrderStatus.CONFIRMED.value
        if action == "order_confirm"
        else OrderStatus.CANCELLED.value
    )
    admin_name = query.from_user.full_name or "Admin"
    store_name = settings.STORE_NAME

    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Order)
            .where(Order.id == order_id)
            .options(selectinload(Order.user))
        )
        order = res.scalar_one_or_none()

        if not order:
            await query.answer("Buyurtma topilmadi!", show_alert=True)
            return

        if order.status != OrderStatus.PENDING.value:
            label = STATUS_TRANSLATIONS.get(order.status, order.status)
            await query.answer(
                f"Bu buyurtma allaqachon ko'rib chiqilgan: {label}",
                show_alert=True,
            )
            return

        order.status = new_status
        await session.commit()

        # Notify customer in background (don't block)
        if order.user and order.user.telegram_id:
            asyncio.create_task(
                notify_customer_order_status(
                    telegram_id=order.user.telegram_id,
                    order_id=order.id,
                    new_status=new_status,
                    store_name=store_name,
                )
            )

    # Update the group message
    status_emoji = "✅ TASDIQLANDI" if new_status == OrderStatus.CONFIRMED.value else "❌ BEKOR QILINDI"
    try:
        new_text = (
            f"{query.message.html_text}\n\n"
            f"➖➖➖➖➖➖➖➖➖➖\n"
            f"<b>Holat:</b> {status_emoji} ({admin_name} tomonidan)"
        )
        await query.message.edit_text(new_text, reply_markup=None)
    except Exception as e:
        logger.warning(f"Message edit failed: {e}")

    await query.answer(f"Buyurtma #{order_id} yangilandi!")
