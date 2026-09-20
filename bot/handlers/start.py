import re
from aiogram import Router, types
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from core.config import settings
from core.cache import is_admin_id

router = Router(name="start_router")


def _get_base_url() -> str:
    base_url = settings.effective_base_url
    return base_url if base_url else "https://example.com"


@router.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject = None):
    """
    Super-tezkor /start handleri:
    - Mahsulot deep-link bilan kelingan bo'lsa, to'g'ridan-to'g'ri o'sha mahsulot sahifasini ochish tugmasini beradi.
    - Xotiradagi keshdan admin ekanligini 0ms da tekshiradi (DB so'rovsiz!).
    - Agar admin bo'lsa, 'Admin Panel' tugmasini ham chiqaradi.
    """
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "Mijoz"
    store_name = settings.STORE_NAME
    store_desc = settings.STORE_DESCRIPTION

    base_url = _get_base_url()
    app_url = f"{base_url}/"
    admin_app_url = f"{base_url}/admin/"

    # Zero-DB check: in-memory check (0.0001ms)
    is_admin = is_admin_id(user_id)

    # Check for deep-linked product (e.g. /start prod_12 or /start 12)
    product_id = None
    if command and command.args:
        match = re.search(r"(?:prod_)?(\d+)", command.args)
        if match:
            try:
                product_id = int(match.group(1))
            except ValueError:
                pass

    if product_id:
        product_app_url = f"{base_url}/?product_id={product_id}"
        buttons = [
            [
                InlineKeyboardButton(
                    text="🛍 Mahsulotni ko'rish va xarid qilish",
                    web_app=WebAppInfo(url=product_app_url),
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🏪 {store_name} — Barcha mahsulotlar",
                    web_app=WebAppInfo(url=app_url),
                )
            ]
        ]
        if is_admin:
            buttons.append([
                InlineKeyboardButton(
                    text="⚙️ Admin Panelini ochish",
                    web_app=WebAppInfo(url=admin_app_url),
                )
            ])
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        welcome_text = (
            f"Assalomu alaykum, <b>{first_name}</b>!\n\n"
            f"Tanlagan mahsulotingizni ochish va buyurtma berish uchun quyidagi tugmani bosing 👇"
        )
        await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")
        return

    buttons = [
        [
            InlineKeyboardButton(
                text=f"🛍 {store_name} — Do'konga kirish",
                web_app=WebAppInfo(url=app_url),
            )
        ]
    ]

    # Agar admin bo'lsa, Admin Panel tugmasini qo'shamiz
    if is_admin:
        buttons.append([
            InlineKeyboardButton(
                text="⚙️ Admin Panelini ochish",
                web_app=WebAppInfo(url=admin_app_url),
            )
        ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    welcome_text = (
        f"Assalomu alaykum, <b>{first_name}</b>!\n\n"
        f"<b>{store_name}</b> rasmiy savdo botiga xush kelibsiz!\n"
    )
    if store_desc:
        welcome_text += f"<i>{store_desc}</i>\n\n"

    if is_admin:
        welcome_text += "👑 <b>Siz admin huquqiga egasiz!</b>\nAdmin panel orqali mahsulotlar va buyurtmalarni boshqarishingiz mumkin 👇"
    else:
        welcome_text += "Do'konimiz katalogini ko'rish va xarid qilish uchun pastdagi tugmani bosing 👇"

    await message.answer(welcome_text, reply_markup=keyboard)


@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """
    /admin buyrug'i orqali to'g'ridan-to'g'ri Admin Panelini ochish.
    """
    user_id = message.from_user.id
    is_admin = is_admin_id(user_id)

    if not is_admin:
        await message.answer("❌ Kechirasiz, sizda admin huquqi yo'q.")
        return

    base_url = _get_base_url()
    admin_app_url = f"{base_url}/admin/"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚙️ Boshqaruv Panelini ochish",
                    web_app=WebAppInfo(url=admin_app_url),
                )
            ]
        ]
    )
    await message.answer("👑 <b>Admin Paneli</b>\nQuyidagi tugma orqali boshqaruv paneliga kiring:", reply_markup=keyboard)
