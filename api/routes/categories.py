from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from core.database import get_db
from core.cache import get_cached_categories, set_cached_categories
from models.category import Category

router = APIRouter(prefix="/api/categories", tags=["Categories"])


class CategoryResponse(BaseModel):
    id: int
    name: str
    sort_order: int
    is_active: bool

    model_config = {"from_attributes": True}


@router.get("", response_model=List[CategoryResponse])
async def get_categories(db: AsyncSession = Depends(get_db)):
    """Fetch all active categories ordered by sort_order — in-memory cached for instant speed."""
    cached = get_cached_categories()
    if cached is not None:
        return cached

    result = await db.execute(
        select(Category)
        .where(Category.is_active == True)
        .order_by(Category.sort_order.asc(), Category.name.asc())
    )
    categories = result.scalars().all()
    categories_data = [
        CategoryResponse.model_validate(c).model_dump() for c in categories
    ]
    set_cached_categories(categories_data)
    return categories_data
