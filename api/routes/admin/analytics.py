import csv
import io
from datetime import datetime, date, timedelta, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Response
from sqlalchemy import select, func, desc, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from api.deps import get_current_admin
from models.admin import Admin
from models.order import Order, OrderItem, OrderStatus
from models.product import Product
from models.category import Category
from models.user import User

router = APIRouter(prefix="/api/admin/analytics", tags=["Admin - Analytics"])


@router.get("/dashboard")
async def get_dashboard_analytics(
    current_admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns high-level business analytics: revenue, order stats,
    low stock alerts, top selling products, and 7-day sales breakdown.
    """
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc)

    # 1. Revenue & Order counts
    # Total revenue (excluding cancelled orders)
    tot_rev_res = await db.execute(
        select(func.coalesce(func.sum(Order.total_price), 0.0))
        .where(Order.status != OrderStatus.CANCELLED.value)
    )
    total_revenue = float(tot_rev_res.scalar_one() or 0.0)

    # Today revenue
    today_rev_res = await db.execute(
        select(func.coalesce(func.sum(Order.total_price), 0.0))
        .where(
            Order.status != OrderStatus.CANCELLED.value,
            Order.created_at >= today_start,
        )
    )
    today_revenue = float(today_rev_res.scalar_one() or 0.0)

    # Total orders count
    tot_orders_res = await db.execute(select(func.count(Order.id)))
    total_orders = int(tot_orders_res.scalar_one() or 0)

    # Today orders count
    today_orders_res = await db.execute(
        select(func.count(Order.id)).where(Order.created_at >= today_start)
    )
    today_orders = int(today_orders_res.scalar_one() or 0)

    # Pending orders count
    pending_res = await db.execute(
        select(func.count(Order.id)).where(Order.status == OrderStatus.PENDING.value)
    )
    pending_orders = int(pending_res.scalar_one() or 0)

    # Completed orders count
    completed_res = await db.execute(
        select(func.count(Order.id)).where(Order.status == OrderStatus.COMPLETED.value)
    )
    completed_orders = int(completed_res.scalar_one() or 0)

    # 2. Low stock alert products (stock <= 5 and active)
    low_stock_res = await db.execute(
        select(Product)
        .where(Product.is_active == True, Product.stock_quantity <= 5)
        .order_by(Product.stock_quantity.asc())
        .limit(10)
    )
    low_stock_products = [
        {
            "id": p.id,
            "name": p.name,
            "stock_quantity": p.stock_quantity,
            "unit": p.unit,
            "price": float(p.price),
        }
        for p in low_stock_res.scalars().all()
    ]

    # 3. Top selling products
    top_selling_res = await db.execute(
        select(
            OrderItem.product_id,
            func.coalesce(Product.name, "O'chirilgan mahsulot").label("product_name"),
            func.sum(OrderItem.quantity).label("total_sold"),
            func.sum(OrderItem.quantity * OrderItem.price_at_order_time).label("total_revenue"),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .outerjoin(Product, Product.id == OrderItem.product_id)
        .where(Order.status != OrderStatus.CANCELLED.value)
        .group_by(OrderItem.product_id, Product.name)
        .order_by(desc("total_sold"))
        .limit(5)
    )
    top_selling = [
        {
            "product_id": row[0],
            "product_name": row[1],
            "total_sold": int(row[2] or 0),
            "total_revenue": float(row[3] or 0.0),
        }
        for row in top_selling_res.fetchall()
    ]

    # 4. Daily sales for last 7 days
    daily_sales = []
    week_days_uz = ["Dush", "Sesh", "Chor", "Pay", "Juma", "Shan", "Yak"]
    for i in range(6, -1, -1):
        d = (now - timedelta(days=i)).date()
        d_start = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc)
        d_end = d_start + timedelta(days=1)

        d_stats = await db.execute(
            select(
                func.count(Order.id),
                func.coalesce(func.sum(Order.total_price), 0.0),
            ).where(
                Order.created_at >= d_start,
                Order.created_at < d_end,
                Order.status != OrderStatus.CANCELLED.value,
            )
        )
        row = d_stats.fetchone()
        cnt = int(row[0] or 0) if row else 0
        rev = float(row[1] or 0.0) if row else 0.0

        daily_sales.append({
            "date": d.strftime("%d.%m"),
            "day_name": week_days_uz[d.weekday()],
            "orders_count": cnt,
            "revenue": rev,
        })

    return {
        "today_revenue": today_revenue,
        "total_revenue": total_revenue,
        "today_orders": today_orders,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "completed_orders": completed_orders,
        "low_stock_products": low_stock_products,
        "top_selling_products": top_selling,
        "daily_sales": daily_sales,
    }


@router.get("/export/orders")
async def export_orders_csv(
    current_admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Exports all orders as a UTF-8 BOM CSV compatible with Microsoft Excel.
    """
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.user),
            selectinload(Order.items).selectinload(OrderItem.product),
        )
        .order_by(Order.id.desc())
    )
    orders = result.scalars().all()

    output = io.StringIO()
    # Write UTF-8 BOM so Excel opens Uzbek characters without corruption
    output.write("\ufeff")
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Buyurtma ID",
        "Sana",
        "Mijoz",
        "Telefon",
        "Manzil",
        "To'lov turi",
        "Holati",
        "Jami summa (so'm)",
        "Mahsulotlar",
        "Izoh",
    ])

    status_map = {
        "pending": "Kutilmoqda",
        "confirmed": "Tasdiqlandi",
        "preparing": "Tayyorlanmoqda",
        "delivering": "Yetkazilmoqda",
        "completed": "Yakunlandi",
        "cancelled": "Bekor qilindi",
    }

    for o in orders:
        items_summary = "; ".join(
            f"{i.product.name if i.product else 'Mahsulot'} ({i.quantity} x {float(i.price_at_order_time):,.0f})"
            for i in o.items
        )
        date_str = o.created_at.strftime("%Y-%m-%d %H:%M") if o.created_at else ""
        customer_name = o.user.full_name if o.user else "Noma'lum"

        writer.writerow([
            o.id,
            date_str,
            customer_name,
            o.phone,
            o.address,
            "Naqd" if o.payment_type == "cash" else "Karta",
            status_map.get(o.status, o.status),
            f"{float(o.total_price):,.0f}",
            items_summary,
            o.notes or "",
        ])

    csv_data = output.getvalue()
    filename = f"buyurtmalar_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/products")
async def export_products_csv(
    current_admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Exports product inventory / stock report as a UTF-8 BOM CSV for Excel.
    """
    result = await db.execute(
        select(Product)
        .options(selectinload(Product.category))
        .order_by(Product.id.asc())
    )
    products = result.scalars().all()

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)

    writer.writerow([
        "ID",
        "Mahsulot nomi",
        "Kategoriya",
        "Hozirgi narxi (so'm)",
        "Eski narxi (so'm)",
        "Ombordagi qoldiq",
        "Birligi",
        "Holati",
    ])

    for p in products:
        cat_name = p.category.name if p.category else "Kategoriyasiz"
        old_p_str = f"{float(p.old_price):,.0f}" if p.old_price else ""
        writer.writerow([
            p.id,
            p.name,
            cat_name,
            f"{float(p.price):,.0f}",
            old_p_str,
            p.stock_quantity,
            p.unit or "dona",
            "Faol" if p.is_active else "Nofaol",
        ])

    csv_data = output.getvalue()
    filename = f"ombor_qoldiqlari_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

    return Response(
        content=csv_data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
