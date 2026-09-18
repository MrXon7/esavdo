from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from core.config import settings
from core.database import get_db
from api.deps import get_current_admin
from models.admin import Admin
from models.order import Order, OrderItem, OrderStatus
from models.user import User
from bot.services.notifier import notify_customer_order_status

router = APIRouter(prefix="/api/admin/orders", tags=["Admin - Orders"])


class AdminOrderItemSchema(BaseModel):
    id: int
    product_id: Optional[int] = None
    product_name: str
    quantity: int
    price_at_order_time: float

    model_config = {"from_attributes": True}


class AdminUserSchema(BaseModel):
    id: int
    telegram_id: int
    full_name: str
    username: Optional[str] = None
    phone: Optional[str] = None

    model_config = {"from_attributes": True}


class AdminOrderResponse(BaseModel):
    id: int
    status: str
    address: str
    phone: str
    payment_type: str
    total_price: float
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    user: Optional[AdminUserSchema] = None
    items: List[AdminOrderItemSchema] = []

    model_config = {"from_attributes": True}


class UpdateOrderStatusRequest(BaseModel):
    status: str


@router.get("", response_model=List[AdminOrderResponse])
async def list_orders_admin(
    status: Optional[str] = Query(None),
    current_admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Fetch all orders, optionally filtered by status."""
    query = (
        select(Order)
        .options(
            selectinload(Order.user),
            selectinload(Order.items).selectinload(OrderItem.product),
        )
        .order_by(Order.id.desc())
    )

    if status:
        query = query.where(Order.status == status.strip())

    result = await db.execute(query)
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
            "user": o.user,
            "items": items,
        })
    return resp


@router.patch("/{order_id}/status", response_model=AdminOrderResponse)
async def update_order_status_admin(
    order_id: int,
    req: UpdateOrderStatusRequest,
    current_admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Update order status and automatically notify customer via bot."""
    valid_statuses = [s.value for s in OrderStatus]
    new_status = req.status.strip().lower()
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Noto'g'ri status. Mumkin bo'lgan statuslar: {', '.join(valid_statuses)}",
        )

    result = await db.execute(
        select(Order)
        .where(Order.id == order_id)
        .options(
            selectinload(Order.user),
            selectinload(Order.items).selectinload(OrderItem.product),
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")

    order.status = new_status
    await db.commit()
    await db.refresh(order)

    # Store name for notification
    store_name = settings.STORE_NAME

    # Notify customer if customer has telegram_id
    if order.user and order.user.telegram_id:
        try:
            await notify_customer_order_status(
                telegram_id=order.user.telegram_id,
                order_id=order.id,
                new_status=new_status,
                store_name=store_name,
            )
        except Exception:
            pass

    items = []
    for i in order.items:
        items.append({
            "id": i.id,
            "product_id": i.product_id,
            "product_name": i.product.name if i.product else "O'chirilgan mahsulot",
            "quantity": i.quantity,
            "price_at_order_time": float(i.price_at_order_time),
        })

    return {
        "id": order.id,
        "status": order.status,
        "address": order.address,
        "phone": order.phone,
        "payment_type": order.payment_type,
        "total_price": float(order.total_price),
        "notes": order.notes,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
        "user": order.user,
        "items": items,
    }
