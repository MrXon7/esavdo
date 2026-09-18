from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.security import validate_telegram_init_data
from models.user import User
from models.admin import Admin


async def get_current_user(
    x_telegram_init_data: Optional[str] = Header(None, alias="X-Telegram-Init-Data"),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extracts and validates Telegram initData, then finds or creates the user in DB.
    """
    init_data = x_telegram_init_data
    if not init_data and authorization:
        if authorization.startswith("tma "):
            init_data = authorization[4:].strip()
        elif authorization.startswith("Bearer "):
            init_data = authorization[7:].strip()
        else:
            init_data = authorization.strip()

    if not init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram autentifikatsiya ma'lumotlari (initData) topilmadi",
        )

    validated = validate_telegram_init_data(init_data, settings.BOT_TOKEN)
    if not validated or "user" not in validated:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Telegram autentifikatsiya ma'lumotlari yaroqsiz",
        )

    tg_user = validated["user"]
    telegram_id = int(tg_user.get("id"))
    first_name = tg_user.get("first_name", "")
    last_name = tg_user.get("last_name", "")
    full_name = f"{first_name} {last_name}".strip() or "Mijoz"
    username = tg_user.get("username")

    # Find or create user
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id=telegram_id,
            full_name=full_name,
            username=username,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        # Update user name/username if changed
        updated = False
        if user.full_name != full_name:
            user.full_name = full_name
            updated = True
        if user.username != username:
            user.username = username
            updated = True
        if updated:
            await db.commit()
            await db.refresh(user)

    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Admin:
    """
    Ensures that the current user is listed in the admins table.
    """
    result = await db.execute(
        select(Admin).where(Admin.telegram_id == current_user.telegram_id)
    )
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin huquqi talab qilinadi",
        )
    return admin
