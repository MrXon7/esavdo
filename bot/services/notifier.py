import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto

from bot.bot_instance import bot
from core.config import settings
from models.order import Order, OrderStatus
from models.product import Product
from models.settings import StoreSettings

logger = logging.getLogger(__name__)

STATUS_TRANSLATIONS = {
    OrderStatus.PENDING.value: "⏳ Kutilmoqda",
    OrderStatus.CONFIRMED.value: "✅ Tasdiqlandi",
    OrderStatus.PREPARING.value: "👨‍🍳 Tayyorlanmoqda",
    OrderStatus.DELIVERING.value: "🛵 Yetkazilmoqda",
    OrderStatus.COMPLETED.value: "🎉 Yakunlandi",
    OrderStatus.CANCELLED.value: "❌ Bekor qilindi",
}

STATUS_MESSAGES = {
    OrderStatus.CONFIRMED.value: "Buyurtmangiz muvaffaqiyatli tasdiqlandi! Tez orada tayyorlashga kirishamiz.",
    OrderStatus.PREPARING.value: "Buyurtmangiz tayyorlanmoqda.",
    OrderStatus.DELIVERING.value: "Buyurtmangiz yetkazilmoqda. Kuryerimiz tez orada siz bilan bog'lanadi.",
    OrderStatus.COMPLETED.value: "Buyurtmangiz muvaffaqiyatli topshirildi. Bizni tanlaganingiz uchun tashakkur!",
    OrderStatus.CANCELLED.value: "Afsuski, buyurtmangiz bekor qilindi. Batafsil ma'lumot uchun do'kon ma'muriyatiga murojaat qiling.",
}


async def notify_admin_new_order(order_id: int, db: AsyncSession):
    """Sends new order notification to the admin group with inline action buttons."""
    if not settings.ADMIN_GROUP_ID:
        logger.warning("ADMIN_GROUP_ID sozlanmagan, buyurtma haqida xabar yuborilmadi.")
        return

    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.items).selectinload(Order.items.property.mapper.class_.product),
            selectinload(Order.user),
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        return

    # Use store currency directly from settings
    currency = settings.STORE_CURRENCY

    items_text = ""
    for idx, item in enumerate(order.items, start=1):
        prod_name = item.product.name if item.product else "O'chirilgan mahsulot"
        item_total = float(item.price_at_order_time) * item.quantity
        items_text += f"{idx}. {prod_name} — {item.quantity} x {float(item.price_at_order_time):,.0f} = {item_total:,.0f} {currency}\n"

    customer_name = order.user.full_name if order.user else "Noma'lum"
    payment_method = "Naqd pul" if order.payment_type == "cash" else "Karta orqali"

    notes_text = order.notes if order.notes else "Yo'q"
    msg_text = (
        f"🛒 <b>YANGI BUYURTMA #{order.id}</b>\n\n"
        f"👤 <b>Mijoz:</b> {customer_name}\n"
        f"📞 <b>Telefon:</b> {order.phone}\n"
        f"📍 <b>Manzil:</b> {order.address}\n"
        f"💳 <b>To'lov turi:</b> {payment_method}\n"
        f"📝 <b>Izoh:</b> {notes_text}\n\n"
        f"<b>Mahsulotlar:</b>\n{items_text}\n"
        f"💰 <b>Jami summa:</b> <b>{float(order.total_price):,.0f} {currency}</b>\n"
        f"📌 <b>Holati:</b> {STATUS_TRANSLATIONS.get(order.status, order.status)}"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Tasdiqlash", callback_data=f"order_confirm:{order.id}"
                ),
                InlineKeyboardButton(
                    text="❌ Rad etish", callback_data=f"order_cancel:{order.id}"
                ),
            ]
        ]
    )

    try:
        await bot.send_message(
            chat_id=settings.ADMIN_GROUP_ID,
            text=msg_text,
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.error(f"Adminga yangi buyurtma xabarini yuborishda xatolik: {e}")


async def notify_customer_order_status(
    telegram_id: int, order_id: int, new_status: str, store_name: str
):
    """Notifies customer via private chat when their order status changes."""
    status_label = STATUS_TRANSLATIONS.get(new_status, new_status)
    status_msg = STATUS_MESSAGES.get(new_status, f"Buyurtmangiz holati: {status_label}")

    text = (
        f"📦 <b>{store_name}</b>\n\n"
        f"Buyurtma <b>#{order_id}</b>\n"
        f"Yangi holat: <b>{status_label}</b>\n\n"
        f"{status_msg}"
    )

    try:
        await bot.send_message(chat_id=telegram_id, text=text)
    except Exception as e:
        logger.warning(f"Mijozga ({telegram_id}) buyurtma holati xabarini yuborishda xatolik: {e}")


async def announce_product_to_group(product_id: int, db: AsyncSession) -> bool:
    """Announces a product to the configured group/channel."""
    if not settings.PRODUCT_ANNOUNCE_GROUP_ID:
        return False

    result = await db.execute(
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.images))
    )
    product = result.scalar_one_or_none()
    if not product:
        return False

    store_name = settings.STORE_NAME
    currency = settings.STORE_CURRENCY

    # Telegram caption character limit is 1024; truncate safely if needed
    desc = (product.description or "").strip()
    if len(desc) > 600:
        desc = desc[:597] + "..."

    btn = None
    direct_link = ""
    try:
        me = await bot.get_me()
        if me.username:
            direct_link = f"https://t.me/{me.username}?start=prod_{product.id}"
            btn = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🛍 Buyurtma berish",
                            url=direct_link,
                        )
                    ]
                ]
            )
    except Exception:
        pass

    link_html = f'\n\n👉 <a href="{direct_link}"><b>[🛍 Buyurtma berish / Ko\'rish]</b></a>' if direct_link else ""
    caption = (
        f"🌟 <b>{store_name} — Yangi mahsulot!</b>\n\n"
        f"🏷 <b>{product.name}</b>\n"
        f"💰 <b>Narxi:</b> {float(product.price):,.0f} {currency}\n\n"
        f"{desc}"
        f"{link_html}"
    )

    images = product.images or []

    try:
        if len(images) > 1:
            # 2 to 10 photos: Send as Telegram Photo Album (MediaGroup)
            album_photos = images[:10]  # Telegram limit is 10
            media = []
            for idx, img in enumerate(album_photos):
                if idx == 0:
                    media.append(
                        InputMediaPhoto(
                            media=img.file_id,
                            caption=caption,
                            parse_mode="HTML",
                        )
                    )
                else:
                    media.append(InputMediaPhoto(media=img.file_id))

            await bot.send_media_group(
                chat_id=settings.PRODUCT_ANNOUNCE_GROUP_ID,
                media=media,
            )

            # Telegram does not allow inline buttons on media groups, so we send the button below
            if btn:
                await bot.send_message(
                    chat_id=settings.PRODUCT_ANNOUNCE_GROUP_ID,
                    text=f"🛒 <b>{product.name}</b> mahsulotiga buyurtma berish 👇",
                    reply_markup=btn,
                    parse_mode="HTML",
                )
        elif len(images) == 1:
            # Single photo with direct inline button
            await bot.send_photo(
                chat_id=settings.PRODUCT_ANNOUNCE_GROUP_ID,
                photo=images[0].file_id,
                caption=caption,
                reply_markup=btn,
                parse_mode="HTML",
            )
        else:
            # No photo: Send text with inline button
            await bot.send_message(
                chat_id=settings.PRODUCT_ANNOUNCE_GROUP_ID,
                text=caption,
                reply_markup=btn,
                parse_mode="HTML",
            )
        return True
    except Exception as e:
        logger.error(f"Mahsulotni guruhga e'lon qilishda xatolik: {e}")
        return False
