from aiogram import Router, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from core.config import settings

router = Router(name="start_router")


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    """
    Super-tezkor /start handleri:
    Hech qanday database so'rovlari yo'q!
    Faqat salomlashish xabari va Mini App ochuvchi tugmani darhol qaytaradi.
    Foydalanuvchi Mini App'ga kirgach, tizim uning huquqiga qarab ishlaydi.
    """
    first_name = message.from_user.first_name or "Mijoz"
    store_name = settings.STORE_NAME
    store_desc = settings.STORE_DESCRIPTION

    base_url = settings.RENDER_EXTERNAL_URL.rstrip("/")
    if not base_url and settings.WEBHOOK_URL:
        base_url = settings.WEBHOOK_URL.replace("/telegram-webhook", "").rstrip("/")

    app_url = f"{base_url}/" if base_url else "https://example.com"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🛍 {store_name} — Do'konga kirish",
                    web_app=WebAppInfo(url=app_url),
                )
            ]
        ]
    )

    welcome_text = (
        f"Assalomu alaykum, <b>{first_name}</b>!\n\n"
        f"<b>{store_name}</b> rasmiy savdo botiga xush kelibsiz!\n"
    )
    if store_desc:
        welcome_text += f"<i>{store_desc}</i>\n\n"
    welcome_text += "Do'konimiz katalogini ko'rish va xarid qilish uchun pastdagi tugmani bosing 👇"

    await message.answer(welcome_text, reply_markup=keyboard)
