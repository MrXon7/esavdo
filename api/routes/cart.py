from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from core.database import get_db
from api.deps import get_current_user
from models.user import User
from models.product import Product
from models.cart import CartItem

router = APIRouter(prefix="/api/cart", tags=["Cart"])


class CartItemProductSchema(BaseModel):
    id: int
    name: str
    price: float
    is_active: bool
    images: List[dict] = []

    model_config = {"from_attributes": True}


class CartItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    product: Optional[CartItemProductSchema] = None

    model_config = {"from_attributes": True}


class AddToCartRequest(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1)


class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(ge=0)


@router.get("", response_model=List[CartItemResponse])
async def get_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all cart items for the authenticated user."""
    result = await db.execute(
        select(CartItem)
        .where(CartItem.user_id == current_user.id)
        .options(
            selectinload(CartItem.product).selectinload(Product.images)
        )
        .order_by(CartItem.id.asc())
    )
    items = result.scalars().all()
    
    # Format response with simplified product info
    response = []
    for item in items:
        prod_data = None
        if item.product:
            prod_data = {
                "id": item.product.id,
                "name": item.product.name,
                "price": float(item.product.price),
                "is_active": item.product.is_active,
                "images": [{"file_id": img.file_id} for img in item.product.images],
            }
        response.append({
            "id": item.id,
            "product_id": item.product_id,
            "quantity": item.quantity,
            "product": prod_data
        })
    return response


@router.post("", response_model=CartItemResponse, status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    req: AddToCartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a product to cart or increment its quantity if already present."""
    # Check if product exists and is active
    p_res = await db.execute(select(Product).where(Product.id == req.product_id, Product.is_active == True))
    product = p_res.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi yoki faol emas")

    # Check if already in cart
    c_res = await db.execute(
        select(CartItem).where(
            CartItem.user_id == current_user.id,
            CartItem.product_id == req.product_id
        )
    )
    cart_item = c_res.scalar_one_or_none()
    if cart_item:
        cart_item.quantity += req.quantity
    else:
        cart_item = CartItem(
            user_id=current_user.id,
            product_id=req.product_id,
            quantity=req.quantity
        )
        db.add(cart_item)

    await db.commit()
    await db.refresh(cart_item)
    return cart_item


@router.patch("/{item_id}")
async def update_cart_item(
    item_id: int,
    req: UpdateCartItemRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update cart item quantity. If quantity is 0, deletes the item."""
    c_res = await db.execute(
        select(CartItem).where(
            CartItem.id == item_id,
            CartItem.user_id == current_user.id
        )
    )
    cart_item = c_res.scalar_one_or_none()
    if not cart_item:
        raise HTTPException(status_code=404, detail="Savatdagi element topilmadi")

    if req.quantity <= 0:
        await db.delete(cart_item)
        await db.commit()
        return {"status": "deleted", "id": item_id}

    cart_item.quantity = req.quantity
    await db.commit()
    await db.refresh(cart_item)
    return {"status": "updated", "id": item_id, "quantity": cart_item.quantity}


@router.delete("/{item_id}")
async def remove_from_cart(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a single item from the cart."""
    c_res = await db.execute(
        select(CartItem).where(
            CartItem.id == item_id,
            CartItem.user_id == current_user.id
        )
    )
    cart_item = c_res.scalar_one_or_none()
    if not cart_item:
        raise HTTPException(status_code=404, detail="Savatdagi element topilmadi")

    await db.delete(cart_item)
    await db.commit()
    return {"status": "success", "message": "Element savatdan o'chirildi"}


@router.delete("")
async def clear_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Clear all items in user's cart."""
    result = await db.execute(select(CartItem).where(CartItem.user_id == current_user.id))
    items = result.scalars().all()
    for item in items:
        await db.delete(item)
    await db.commit()
    return {"status": "success", "message": "Savat tozalandi"}
