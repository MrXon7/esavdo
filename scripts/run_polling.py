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
from core.database import AsyncSessionLocal
from core.cache import set_cached_admin_ids
from models.admin import Admin
from bot.bot_instance import bot, dp
from bot.handlers import register_all_handlers


async def warm_up_cache():
    """Pre-warm memory cache with admin IDs so photo uploads respond instantly."""
    print(f"[*] Do'kon: '{settings.STORE_NAME}'")
    try:
        async with AsyncSessionLocal() as session:
            admin_res = await session.execute(select(Admin.telegram_id))
            admin_ids = set(row[0] for row in admin_res.fetchall())
            set_cached_admin_ids(admin_ids)
            print(f"[+] Adminlar ro'yxati yuklandi: {len(admin_ids)} ta admin ({admin_ids})")

        print("[OK] Adminlar ro'yxati xotiraga olindi!")
    except Exception as e:
        print(f"[!] Keshni isitishda ogohlantirish (bot ishlashda davom etadi): {e}")


async def main():
    print("=== ESavdo Telegram Bot - Local Polling Mode ===")
    register_all_handlers(dp)

    # 1. Warm up cache
    await warm_up_cache()

    # 2. Drop any existing webhook
    await bot.delete_webhook(drop_pending_updates=True)
    me = await bot.get_me()
    print(f"\n[+] Bot faol: @{me.username} ({me.first_name})")
    print("[+] Telegram'da botingizga /start yuboring yoki rasm jo'nating!")
    print("[+] To'xtatish uchun: Ctrl + C\n")

    try:
        await dp.start_polling(bot, polling_timeout=20)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
