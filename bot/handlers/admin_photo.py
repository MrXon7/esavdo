import logging
from aiogram import Router, F, types
from sqlalchemy.dialects.postgresql import insert

from core.database import AsyncSessionLocal
from core.cache import get_cached_admin_ids, set_cached_admin_ids
from models.admin import Admin
from models.image import UploadedImage
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = Router(name="admin_photo_router")


async def _is_admin(telegram_id: int) -> bool:
    """Check if user is admin — RAM cache first, DB fallback."""
    cached = get_cached_admin_ids()
    if cached is not None:
        return telegram_id in cached

    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Admin.telegram_id))
            ids = set(row[0] for row in result.fetchall())
            set_cached_admin_ids(ids)
            return telegram_id in ids
    except Exception as e:
        logger.error(f"Error checking admin in photo upload: {e}")
        return False


@router.message(F.photo)
async def handle_photo_upload(message: types.Message):
    """
    Captures incoming photos from administrators and stores file_id into uploaded_images.
    Optimised for minimum latency:
    - Admin check: in-memory cache (<1ms)
    - DB write: single atomic INSERT ON CONFLICT DO NOTHING
    """
    user_id = message.from_user.id

    # 1. Quick in-memory admin check (0ms)
    if not await _is_admin(user_id):
        await message.answer(
            "Rahmat! Buyurtma berish uchun /start bosing va do'konimiz Mini App'idan foydalaning."
        )
        return

    # 2. Get highest resolution photo
    file_id = message.photo[-1].file_id

    # 3. Single-query atomic insert
    try:
        async with AsyncSessionLocal() as session:
            stmt = (
                insert(UploadedImage)
                .values(
                    file_id=file_id,
                    uploaded_by_telegram_id=user_id,
                    is_used=False,
                )
                .on_conflict_do_nothing(index_elements=[UploadedImage.file_id])
            )
            result = await session.execute(stmt)
            await session.commit()

            if result.rowcount > 0:
                await message.reply(
                    "📸 <b>Rasm qabul qilindi va galereyaga saqlandi!</b>\n\n"
                    "Admin Mini App paneliga o'tib, yangi mahsulot qo'shishda shu rasmni tanlashingiz mumkin."
                )
            else:
                await message.reply("Bu rasm avval yuklangan.")
    except Exception as e:
        logger.error(f"Photo save failed: {e}")
        await message.reply("Rasmni saqlashda xatolik yuz berdi.")
