import asyncio
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from core.database import engine, AsyncSessionLocal
from models.base import Base
from models.settings import StoreSettings
from models.admin import Admin
import models  # Ensure all models are registered in metadata


async def init_database(initial_admin_id: int | None = None):
    print("Connecting to database and creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created successfully.")

    async with AsyncSessionLocal() as session:
        # Check store settings
        result = await session.execute(select(StoreSettings).where(StoreSettings.id == 1))
        setting = result.scalar_one_or_none()
        if not setting:
            default_setting = StoreSettings(
                id=1,
                store_name="Mening do'konim",
                store_description="Sifatli va qulay xaridlar platformasi",
                currency="so'm"
            )
            session.add(default_setting)
            print("Default store settings created.")

        # Check initial admin if supplied
        if initial_admin_id:
            admin_res = await session.execute(select(Admin).where(Admin.telegram_id == initial_admin_id))
            if not admin_res.scalar_one_or_none():
                new_admin = Admin(telegram_id=initial_admin_id)
                session.add(new_admin)
                print(f"Admin with telegram_id={initial_admin_id} created.")

        await session.commit()
    print("Database initialization complete.")


if __name__ == "__main__":
    admin_arg = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else None
    asyncio.run(init_database(admin_arg))
