from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from core.config import settings

router = APIRouter(prefix="/api/store-settings", tags=["Store Settings"])


class StoreSettingsResponse(BaseModel):
    id: int = 1
    store_name: str
    store_description: Optional[str] = None
    logo_file_id: Optional[str] = None
    contact_phone: Optional[str] = None
    currency: str = "so'm"


@router.get("", response_model=StoreSettingsResponse)
async def get_store_settings():
    """
    Public endpoint to fetch store branding and metadata directly from code config.
    Zero DB queries, instantaneous response!
    """
    return StoreSettingsResponse(
        id=1,
        store_name=settings.STORE_NAME,
        store_description=settings.STORE_DESCRIPTION or None,
        logo_file_id=settings.STORE_LOGO_FILE_ID or None,
        contact_phone=settings.STORE_CONTACT_PHONE or None,
        currency=settings.STORE_CURRENCY,
    )
