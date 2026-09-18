import asyncio
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from core.config import settings
from core.database import engine, AsyncSessionLocal
from models.base import Base
from models.admin import Admin
import models  # Ensure all models are registered in metadata


async def init_database():
    """
    1. Barcha jadvallarni yaratadi (mavjud bo'lsa o'tkazib yuboradi).
    2. ADMIN_TELEGRAM_ID .env o'zgaruvchisidan bazaga sinxronlaydi.
    """
    print("Connecting to database and creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created/verified successfully.")

    async with AsyncSessionLocal() as session:
        # Sync admin from ADMIN_TELEGRAM_ID env var
        admin_id = settings.ADMIN_TELEGRAM_ID
        if admin_id and admin_id != 0:
            existing = await session.execute(select(Admin).where(Admin.telegram_id == admin_id))
            if not existing.scalar_one_or_none():
                session.add(Admin(telegram_id=admin_id))
                await session.commit()
                print(f"Admin {admin_id} added to database from ADMIN_TELEGRAM_ID env var.")
            else:
                print(f"Admin {admin_id} already exists in database.")
        else:
            print("WARNING: ADMIN_TELEGRAM_ID is not set in .env — no admin was added!")

        # Show current admin list
        all_admins = await session.execute(select(Admin.telegram_id))
        ids = [row[0] for row in all_admins.fetchall()]
        print(f"Current admins in DB: {ids}")

    print("Database initialization complete.")


if __name__ == "__main__":
    asyncio.run(init_database())
