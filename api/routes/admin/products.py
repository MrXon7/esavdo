from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from core.database import get_db
from api.deps import get_current_admin
from models.admin import Admin
from models.product import Product, ProductImage
from models.image import UploadedImage
from bot.services.notifier import announce_product_to_group
from core.cache import invalidate_catalog_cache

router = APIRouter(prefix="/api/admin/products", tags=["Admin - Products"])


class AdminProductImageSchema(BaseModel):
    id: int
    file_id: str
    sort_order: int

    model_config = {"from_attributes": True}


class AdminProductResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: float
    category_id: Optional[int] = None
    is_active: bool
    images: List[AdminProductImageSchema] = []

    model_config = {"from_attributes": True}


class CreateProductRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    category_id: Optional[int] = None
    is_active: bool = True
    image_file_ids: List[str] = []


class UpdateProductRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    category_id: Optional[int] = None
    is_active: Optional[bool] = None
    image_file_ids: Optional[List[str]] = None


@router.get("", response_model=List[AdminProductResponse])
async def list_products_admin(
    current_admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: List all products including inactive ones."""
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.images))
        .order_by(Product.id.desc())
    )
    return result.scalars().all()


@router.post("", response_model=AdminProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product_admin(
    req: CreateProductRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Create new product and link selected image file_ids."""
    product = Product(
        name=req.name.strip(),
        description=req.description.strip() if req.description else None,
        price=req.price,
        category_id=req.category_id,
        is_active=req.is_active,
    )
    db.add(product)
    await db.flush()

    # Link images
    if req.image_file_ids:
        for idx, file_id in enumerate(req.image_file_ids):
            img = ProductImage(
                product_id=product.id,
                file_id=file_id,
                sort_order=idx,
            )
            db.add(img)

        # Mark corresponding uploaded_images as used
        await db.execute(
            update(UploadedImage)
            .where(UploadedImage.file_id.in_(req.image_file_ids))
            .values(is_used=True)
        )

    await db.commit()
    invalidate_catalog_cache()

    # Re-fetch with images
    result = await db.execute(
        select(Product)
        .where(Product.id == product.id)
        .options(selectinload(Product.images))
    )
    return result.scalar_one()


@router.patch("/{product_id}", response_model=AdminProductResponse)
async def update_product_admin(
    product_id: int,
    req: UpdateProductRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Update product details and optionally replace images."""
    result = await db.execute(
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.images))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")

    if req.name is not None:
        product.name = req.name.strip()
    if req.description is not None:
        product.description = req.description.strip() if req.description else None
    if req.price is not None:
        product.price = req.price
    if req.category_id is not None:
        product.category_id = req.category_id
    if req.is_active is not None:
        product.is_active = req.is_active

    if req.image_file_ids is not None:
        # Clear existing images
        for existing_img in list(product.images):
            await db.delete(existing_img)

        # Add new images
        for idx, file_id in enumerate(req.image_file_ids):
            img = ProductImage(
                product_id=product.id,
                file_id=file_id,
                sort_order=idx,
            )
            db.add(img)

        # Mark corresponding uploaded_images as used
        if req.image_file_ids:
            await db.execute(
                update(UploadedImage)
                .where(UploadedImage.file_id.in_(req.image_file_ids))
                .values(is_used=True)
            )

    await db.commit()
    invalidate_catalog_cache()

    result = await db.execute(
        select(Product)
        .where(Product.id == product.id)
        .options(selectinload(Product.images))
    )
    return result.scalar_one()


@router.delete("/{product_id}")
async def delete_product_admin(
    product_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Delete product."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")

    await db.delete(product)
    await db.commit()
    invalidate_catalog_cache()
    return {"status": "success", "message": "Mahsulot muvaffaqiyatli o'chirildi"}


@router.post("/{product_id}/announce")
async def announce_product(
    product_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Announce product to Telegram group."""
    success = await announce_product_to_group(product_id, db)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="E'lon yuborilmadi. PRODUCT_ANNOUNCE_GROUP_ID sozlamasini tekshiring.",
        )
    return {"status": "success", "message": "Mahsulot guruhga e'lon qilindi"}
