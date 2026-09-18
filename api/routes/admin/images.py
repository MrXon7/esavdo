import os
import tempfile
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from core.database import get_db
from api.deps import get_current_admin
from models.admin import Admin
from models.image import UploadedImage
from models.product import ProductImage
from api.routes.images import CACHE_DIR, MEMORY_CACHE

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
    """
    Admin: Fetch images uploaded via Telegram bot.
    Automatically ensures is_used flag is accurate:
    - If file_id is currently used in ProductImage -> is_used = True
    - If file_id is NOT used anywhere in ProductImage -> is_used = False
    """
    # 1. Auto-sync is_used based on actual ProductImage relationships
    used_subquery = select(ProductImage.file_id).scalar_subquery()

    # Revert orphaned images to is_used = False
    await db.execute(
        update(UploadedImage)
        .where(
            UploadedImage.is_used == True,
            UploadedImage.file_id.not_in(used_subquery)
        )
        .values(is_used=False)
    )

    # Ensure attached images have is_used = True
    await db.execute(
        update(UploadedImage)
        .where(
            UploadedImage.is_used == False,
            UploadedImage.file_id.in_(used_subquery)
        )
        .values(is_used=True)
    )
    await db.commit()

    # 2. Query images
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
    """
    Admin: Delete an uploaded image record.
    Strict rule: Only allowed if the image is FREE (not used by any product).
    """
    result = await db.execute(select(UploadedImage).where(UploadedImage.id == image_id))
    img = result.scalar_one_or_none()
    if not img:
        raise HTTPException(status_code=404, detail="Rasm topilmadi")

    # Verify if it is currently attached to any product
    p_img_res = await db.execute(
        select(ProductImage.id).where(ProductImage.file_id == img.file_id).limit(1)
    )
    if img.is_used or p_img_res.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Ushbu rasm mahsulotga biriktirilgan (band). Uni o'chirish uchun avval mahsulotdan olib tashlang."
        )

    file_id = img.file_id

    # 1. Delete from database
    await db.delete(img)
    await db.commit()

    # 2. Purge from disk cache & memory cache if present
    try:
        if file_id in MEMORY_CACHE:
            MEMORY_CACHE.pop(file_id, None)

        cache_path = os.path.join(CACHE_DIR, f"{file_id}.cached")
        meta_path = os.path.join(CACHE_DIR, f"{file_id}.meta")
        if os.path.exists(cache_path):
            os.remove(cache_path)
        if os.path.exists(meta_path):
            os.remove(meta_path)
    except Exception as e:
        print(f"Warning: could not clean image cache file for {file_id}: {e}")

    return {"status": "success", "message": "Rasm butunlay o'chirildi"}
