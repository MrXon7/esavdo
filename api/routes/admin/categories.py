from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from core.database import get_db
from core.cache import invalidate_catalog_cache
from api.deps import get_current_admin
from models.admin import Admin
from models.category import Category

router = APIRouter(prefix="/api/admin/categories", tags=["Admin - Categories"])


class CategorySchema(BaseModel):
    id: int
    name: str
    sort_order: int
    is_active: bool

    model_config = {"from_attributes": True}


class CreateCategoryRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sort_order: int = 0
    is_active: bool = True


class UpdateCategoryRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


@router.get("", response_model=List[CategorySchema])
async def list_categories_admin(
    current_admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: List all categories."""
    result = await db.execute(select(Category).order_by(Category.sort_order.asc(), Category.id.asc()))
    return result.scalars().all()


@router.post("", response_model=CategorySchema, status_code=status.HTTP_201_CREATED)
async def create_category_admin(
    req: CreateCategoryRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Create a new category."""
    cat = Category(
        name=req.name.strip(),
        sort_order=req.sort_order,
        is_active=req.is_active,
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    invalidate_catalog_cache()
    return cat


@router.patch("/{cat_id}", response_model=CategorySchema)
async def update_category_admin(
    cat_id: int,
    req: UpdateCategoryRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Update category."""
    result = await db.execute(select(Category).where(Category.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Kategoriya topilmadi")

    if req.name is not None:
        cat.name = req.name.strip()
    if req.sort_order is not None:
        cat.sort_order = req.sort_order
    if req.is_active is not None:
        cat.is_active = req.is_active

    await db.commit()
    await db.refresh(cat)
    invalidate_catalog_cache()
    return cat


@router.delete("/{cat_id}")
async def delete_category_admin(
    cat_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Delete category."""
    result = await db.execute(select(Category).where(Category.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Kategoriya topilmadi")

    await db.delete(cat)
    await db.commit()
    invalidate_catalog_cache()
    return {"status": "success", "message": "Kategoriya o'chirildi"}
