from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from core.database import get_db
from api.deps import get_current_admin
from models.admin import Admin
from models.image import UploadedImage

router = APIRouter(prefix="/api/admin/uploaded-images", tags=["Admin - Images"])


class UploadedImageResponse(BaseModel):
    id: int
    file_id: str
    uploaded_by_telegram_id: int
    uploaded_at: datetime
    is_used: bool

    model_config = {"from_attributes": True}


@router.get("", response_model=List[UploadedImageResponse])
async def list_uploaded_images(
    is_used: Optional[bool] = Query(None),
    current_admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Fetch images uploaded via Telegram bot. Defaults to unused images if specified."""
    query = select(UploadedImage).order_by(UploadedImage.id.desc())
    if is_used is not None:
        query = query.where(UploadedImage.is_used == is_used)

    result = await db.execute(query)
    return result.scalars().all()


@router.delete("/{image_id}")
async def delete_uploaded_image(
    image_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Delete an uploaded image record."""
    result = await db.execute(select(UploadedImage).where(UploadedImage.id == image_id))
    img = result.scalar_one_or_none()
    if not img:
        raise HTTPException(status_code=404, detail="Rasm topilmadi")

    await db.delete(img)
    await db.commit()
    return {"status": "success", "message": "Rasm o'chirildi"}
