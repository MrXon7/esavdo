import asyncio
import os
import sys

# Windows UTF-8 stdout fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from core.config import settings
from core.database import engine, AsyncSessionLocal
from core.cache import set_cached_admin_ids
from models.base import Base
from models.admin import Admin
import models  # ensure all models are registered
from bot.bot_instance import bot, dp
from bot.handlers import register_all_handlers


async def sync_and_warm_cache():
    """
    1. Jadvallarni yaratish (mavjud bo'lsa o'tkazib yuboradi).
    2. ADMIN_TELEGRAM_ID env o'zgaruvchisidan bazaga sinxronlash.
    3. Adminlar ro'yxatini RAM xotirasiga yuklash.
    """
    print(f"[*] Do'kon: '{settings.STORE_NAME}'")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[+] Jadvallar tayyor.")

    try:
        async with AsyncSessionLocal() as session:
            # 1. Sync admin from env
            if settings.ADMIN_TELEGRAM_ID and settings.ADMIN_TELEGRAM_ID != 0:
                existing = await session.execute(
                    select(Admin).where(Admin.telegram_id == settings.ADMIN_TELEGRAM_ID)
                )
                if not existing.scalar_one_or_none():
                    session.add(Admin(telegram_id=settings.ADMIN_TELEGRAM_ID))
                    await session.commit()
                    print(f"[+] Admin {settings.ADMIN_TELEGRAM_ID} bazaga qo'shildi.")
                else:
                    print(f"[+] Admin {settings.ADMIN_TELEGRAM_ID} allaqachon mavjud.")
            else:
                print("[!] ADMIN_TELEGRAM_ID .env da belgilanmagan!")

            # 2. Load all admin IDs into RAM cache
            admin_res = await session.execute(select(Admin.telegram_id))
            admin_ids = set(row[0] for row in admin_res.fetchall())
            set_cached_admin_ids(admin_ids)
            print(f"[OK] Adminlar xotiraga yuklandi: {admin_ids}")

    except Exception as e:
        print(f"[!] Xatolik (bot ishlashda davom etadi): {e}")


async def main():
    print("=== ESavdo Telegram Bot - Local Polling Mode ===")
    register_all_handlers(dp)

    # Sync & warm-up
    await sync_and_warm_cache()

    # Drop any existing webhook
    await bot.delete_webhook(drop_pending_updates=True)
    me = await bot.get_me()
    print(f"\n[+] Bot faol: @{me.username} ({me.first_name})")
    print("[+] Telegram'da botingizga /start yuboring!")
    print("[+] To'xtatish: Ctrl + C\n")

    try:
        await dp.start_polling(bot, polling_timeout=20)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
