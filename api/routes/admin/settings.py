from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from core.database import get_db
from core.cache import invalidate_store_settings_cache
from api.deps import get_current_admin
from models.admin import Admin
from models.settings import StoreSettings

router = APIRouter(prefix="/api/admin/store-settings", tags=["Admin - Store Settings"])


class UpdateStoreSettingsRequest(BaseModel):
    store_name: Optional[str] = None
    store_description: Optional[str] = None
    logo_file_id: Optional[str] = None
    contact_phone: Optional[str] = None
    currency: Optional[str] = None


class StoreSettingsResponse(BaseModel):
    id: int
    store_name: str
    store_description: Optional[str] = None
    logo_file_id: Optional[str] = None
    contact_phone: Optional[str] = None
    currency: str

    model_config = {"from_attributes": True}


@router.patch("", response_model=StoreSettingsResponse)
async def update_store_settings(
    req: UpdateStoreSettingsRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin endpoint to update white-label store branding and metadata."""
    result = await db.execute(select(StoreSettings).where(StoreSettings.id == 1))
    settings_obj = result.scalar_one_or_none()
    if not settings_obj:
        settings_obj = StoreSettings(id=1)
        db.add(settings_obj)

    from core.config import settings

    if req.store_name is not None:
        val = req.store_name.strip()
        settings_obj.store_name = val
        settings.STORE_NAME = val
    if req.store_description is not None:
        val = req.store_description.strip()
        settings_obj.store_description = val
        settings.STORE_DESCRIPTION = val
    if req.logo_file_id is not None:
        val = req.logo_file_id.strip() if req.logo_file_id else None
        settings_obj.logo_file_id = val
        settings.STORE_LOGO_FILE_ID = val or ""
    if req.contact_phone is not None:
        val = req.contact_phone.strip() if req.contact_phone else None
        settings_obj.contact_phone = val
        settings.STORE_CONTACT_PHONE = val or ""
    if req.currency is not None:
        val = req.currency.strip()
        settings_obj.currency = val
        settings.STORE_CURRENCY = val

    await db.commit()
    await db.refresh(settings_obj)
    # Invalidate in-memory cache so bot picks up new name/branding immediately
    invalidate_store_settings_cache()
    return settings_obj
