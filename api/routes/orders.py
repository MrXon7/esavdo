from typing import List, Optional
from datetime import datetime
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
from models.order import Order, OrderItem, OrderStatus
from bot.services.notifier import notify_admin_new_order

router = APIRouter(prefix="/api/orders", tags=["Orders"])


class CreateOrderRequest(BaseModel):
    address: str = Field(..., min_length=3)
    phone: str = Field(..., min_length=7)
    payment_type: str = Field(default="cash")
    notes: Optional[str] = None


class OrderItemDetailSchema(BaseModel):
    id: int
    product_id: Optional[int] = None
    product_name: str
    quantity: int
    price_at_order_time: float

    model_config = {"from_attributes": True}


class OrderDetailResponse(BaseModel):
    id: int
    status: str
    address: str
    phone: str
    payment_type: str
    total_price: float
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemDetailSchema] = []

    model_config = {"from_attributes": True}


@router.post("", response_model=OrderDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    req: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Checkout current user's cart items into a new pending order.
    Notifies admin group with inline confirmation buttons.
    """
    # 1. Fetch user's cart
    result = await db.execute(
        select(CartItem)
        .where(CartItem.user_id == current_user.id)
        .options(selectinload(CartItem.product))
    )
    cart_items = result.scalars().all()

    if not cart_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Savatingiz bo'sh. Buyurtma berish uchun mahsulot tanlang.",
        )

    # 2. Calculate total and check product availability
    total_price = 0.0
    for item in cart_items:
        if not item.product or not item.product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Savatdagi ayrim mahsulotlar mavjud emas yoki faol emas.",
            )
        total_price += float(item.product.price) * item.quantity

    # Update user phone if empty
    if req.phone and not current_user.phone:
        current_user.phone = req.phone

    # 3. Create Order
    new_order = Order(
        user_id=current_user.id,
        status=OrderStatus.PENDING.value,
        address=req.address.strip(),
        phone=req.phone.strip(),
        payment_type=req.payment_type.strip(),
        total_price=total_price,
        notes=req.notes.strip() if req.notes else None,
    )
    db.add(new_order)
    await db.flush()  # to obtain new_order.id

    # 4. Create OrderItems and clear cart
    order_items_response = []
    for item in cart_items:
        oi = OrderItem(
            order_id=new_order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price_at_order_time=item.product.price,
        )
        db.add(oi)
        order_items_response.append({
            "id": 0,
            "product_id": item.product_id,
            "product_name": item.product.name,
            "quantity": item.quantity,
            "price_at_order_time": float(item.product.price),
        })
        await db.delete(item)

    await db.commit()
    await db.refresh(new_order)

    # 5. Send notification to admin group
    try:
        await notify_admin_new_order(new_order.id, db)
    except Exception:
        pass

    return {
        "id": new_order.id,
        "status": new_order.status,
        "address": new_order.address,
        "phone": new_order.phone,
        "payment_type": new_order.payment_type,
        "total_price": float(new_order.total_price),
        "notes": new_order.notes,
        "created_at": new_order.created_at,
        "updated_at": new_order.updated_at,
        "items": order_items_response,
    }


@router.get("", response_model=List[OrderDetailResponse])
async def get_my_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve order history for the authenticated user."""
    result = await db.execute(
        select(Order)
        .where(Order.user_id == current_user.id)
        .options(
            selectinload(Order.items).selectinload(OrderItem.product)
        )
        .order_by(Order.id.desc())
    )
    orders = result.scalars().all()

    resp = []
    for o in orders:
        items = []
        for i in o.items:
            items.append({
                "id": i.id,
                "product_id": i.product_id,
                "product_name": i.product.name if i.product else "O'chirilgan mahsulot",
                "quantity": i.quantity,
                "price_at_order_time": float(i.price_at_order_time),
            })
        resp.append({
            "id": o.id,
            "status": o.status,
            "address": o.address,
            "phone": o.phone,
            "payment_type": o.payment_type,
            "total_price": float(o.total_price),
            "notes": o.notes,
            "created_at": o.created_at,
            "updated_at": o.updated_at,
            "items": items,
        })
    return resp
