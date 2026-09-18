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
from models.product import Product
from models.user import User
from bot.services.notifier import notify_customer_order_status

router = APIRouter(prefix="/api/admin/orders", tags=["Admin - Orders"])


class AdminOrderItemSchema(BaseModel):
    id: int
    product_id: Optional[int] = None
    product_name: str
    quantity: int
    price_at_order_time: float
    image_file_id: Optional[str] = None

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


def _safe_image_id(order_item) -> Optional[str]:
    """Safely extract the first image file_id from an OrderItem.product.
    Returns None on any error (deleted product, missing images, etc.)
    """
    try:
        product = order_item.product
        if not product:
            return None
        images = getattr(product, "images", None)
        if not images:
            return None
        first = images[0] if images else None
        return getattr(first, "file_id", None) if first else None
    except Exception:
        return None


def _build_order_item_dict(i) -> dict:
    return {
        "id": i.id,
        "product_id": i.product_id,
        "product_name": (i.product.name if i.product else "O'chirilgan mahsulot"),
        "quantity": i.quantity,
        "price_at_order_time": float(i.price_at_order_time),
        "image_file_id": _safe_image_id(i),
    }


@router.get("", response_model=List[AdminOrderResponse])
async def list_orders_admin(
    status: Optional[str] = Query(None),
    current_admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Fetch all orders with product images, optionally filtered by status."""
    try:
        query = (
            select(Order)
            .options(
                selectinload(Order.user),
                selectinload(Order.items)
                .selectinload(OrderItem.product)
                .selectinload(Product.images),
            )
            .order_by(Order.id.desc())
        )

        if status:
            query = query.where(Order.status == status.strip())

        result = await db.execute(query)
        orders = result.scalars().all()

        resp = []
        for o in orders:
            try:
                items = [_build_order_item_dict(i) for i in o.items]
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
            except Exception as ex:
                # Log and skip malformed order — don't crash the whole list
                import logging
                logging.getLogger(__name__).warning(f"Buyurtma #{o.id} ni yuklashda xatolik: {ex}")
        return resp
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"list_orders_admin xatolik: {e}")
        raise HTTPException(status_code=500, detail=f"Buyurtmalarni yuklashda xatolik: {str(e)}")


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
            selectinload(Order.items)
            .selectinload(OrderItem.product)
            .selectinload(Product.images),
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

    items = [_build_order_item_dict(i) for i in order.items]

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


@router.delete("/{order_id}")
async def delete_order_admin(
    order_id: int,
    current_admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin: Completely delete a completed or cancelled order."""
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")

    if order.status not in [OrderStatus.COMPLETED.value, OrderStatus.CANCELLED.value]:
        raise HTTPException(
            status_code=400,
            detail="Faqat yakunlangan yoki bekor qilingan buyurtmalarni o'chirish mumkin",
        )

    await db.delete(order)
    await db.commit()
    return {"status": "success", "message": "Buyurtma butunlay o'chirildi"}
