from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from core.database import get_db
from core.cache import get_cached_products, set_cached_products
from models.product import Product, ProductImage
from models.category import Category

router = APIRouter(prefix="/api/products", tags=["Products"])


class ProductImageSchema(BaseModel):
    id: int
    file_id: str
    sort_order: int

    model_config = {"from_attributes": True}


class ProductListResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: float
    category_id: Optional[int] = None
    is_active: bool
    images: List[ProductImageSchema] = []

    model_config = {"from_attributes": True}


class ProductDetailResponse(ProductListResponse):
    pass


@router.get("", response_model=List[ProductListResponse])
async def get_products(
    category_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch active products with optional category and search filters.
    Caches the full active catalog in RAM for instantaneous response.
    """
    cached_all = get_cached_products()

    if cached_all is None:
        query = (
            select(Product)
            .where(Product.is_active == True)
            .options(selectinload(Product.images))
            .order_by(Product.id.desc())
        )
        result = await db.execute(query)
        products = result.scalars().all()
        cached_all = [
            ProductListResponse.model_validate(p).model_dump() for p in products
        ]
        set_cached_products(cached_all)

    # Filter in memory if parameters provided
    filtered = cached_all
    if category_id is not None:
        filtered = [p for p in filtered if p.get("category_id") == category_id]

    if search:
        st = search.strip().lower()
        filtered = [p for p in filtered if st in (p.get("name") or "").lower()]

    return filtered


@router.get("/{product_id}", response_model=ProductDetailResponse)
async def get_product_detail(product_id: int, db: AsyncSession = Depends(get_db)):
    """Fetch a single active product by ID — checks RAM cache first."""
    cached_all = get_cached_products()
    if cached_all:
        for p in cached_all:
            if p.get("id") == product_id:
                return p

    result = await db.execute(
        select(Product)
        .where(Product.id == product_id, Product.is_active == True)
        .options(selectinload(Product.images))
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")
    return product
