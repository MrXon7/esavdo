import asyncio
import logging
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from core.config import settings
from core.database import engine, AsyncSessionLocal
from models.base import Base
from models.settings import StoreSettings
from bot.bot_instance import bot, dp
from bot.handlers import register_all_handlers

# Import routers
from api.routes.health import router as health_router
from api.routes.webhook import router as webhook_router
from api.routes.images import router as images_router
from api.routes.store import router as store_router
from api.routes.categories import router as categories_router
from api.routes.products import router as products_router
from api.routes.cart import router as cart_router
from api.routes.orders import router as orders_router

# Admin routers
from api.routes.admin.settings import router as admin_settings_router
from api.routes.admin.categories import router as admin_categories_router
from api.routes.admin.products import router as admin_products_router
from api.routes.admin.images import router as admin_images_router
from api.routes.admin.orders import router as admin_orders_router

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def self_ping_worker():
    """
    Background worker that pings RENDER_EXTERNAL_URL/health every 5 minutes
    to keep the Render Free tier service awake.
    """
    ping_url = settings.RENDER_EXTERNAL_URL.rstrip("/")
    if not ping_url:
        logger.info("RENDER_EXTERNAL_URL sozlanmagan, self-ping o'chirilgan.")
        return

    health_url = f"{ping_url}/health"
    logger.info(f"Self-ping xizmati ishga tushdi: {health_url} har {settings.SELF_PING_INTERVAL_SECONDS} soniyada.")

    async with httpx.AsyncClient(timeout=10.0) as client:
        while True:
            try:
                await asyncio.sleep(settings.SELF_PING_INTERVAL_SECONDS)
                resp = await client.get(health_url)
                logger.info(f"Self-ping muvaffaqiyatli: {resp.status_code}")
            except asyncio.CancelledError:
                logger.info("Self-ping to'xtatildi.")
                break
            except Exception as e:
                logger.warning(f"Self-ping xatosi: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Register aiogram bot handlers
    register_all_handlers(dp)
    logger.info("Aiogram routerlari ro'yxatdan o'tkazildi.")

    # 2. Ensure database tables and default store_settings exist
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with AsyncSessionLocal() as session:
            # Warm up admin IDs cache
            from core.cache import set_cached_admin_ids
            from models.admin import Admin as AdminModel
            from sqlalchemy import select as sa_select
            admin_res = await session.execute(sa_select(AdminModel.telegram_id))
            set_cached_admin_ids(set(row[0] for row in admin_res.fetchall()))
            logger.info("Ma'lumotlar bazasi va adminlar ro'yxati tekshirildi.")
    except Exception as e:
        logger.error(f"Bazani initsializatsiya qilishda xatolik: {e}")

    # 3. Setup Telegram Webhook if configured
    if settings.WEBHOOK_URL and "placeholder" not in settings.BOT_TOKEN:
        try:
            await bot.set_webhook(
                url=settings.WEBHOOK_URL,
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query", "my_chat_member"],
            )
            logger.info(f"Telegram Webhook o'rnatildi: {settings.WEBHOOK_URL}")
        except Exception as e:
            logger.error(f"Webhook o'rnatishda xatolik: {e}")
    else:
        logger.warning("WEBHOOK_URL yoki BOT_TOKEN sozlanmagan, webhook o'rnatilmadi.")

    # 4. Launch self-ping background task for Render free tier
    ping_task = asyncio.create_task(self_ping_worker())

    yield

    # Shutdown
    ping_task.cancel()
    try:
        await bot.session.close()
    except Exception:
        pass
    await engine.dispose()
    logger.info("Ilova to'xtatildi.")


app = FastAPI(
    title="Telegram E-Commerce Store API",
    description="Telegram Savdo Do'koni Boti va Mini App uchun backend API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. API routers (must be registered before static mounts)
app.include_router(health_router)
app.include_router(webhook_router)
app.include_router(images_router)
app.include_router(store_router)
app.include_router(categories_router)
app.include_router(products_router)
app.include_router(cart_router)
app.include_router(orders_router)

# Admin API routers
app.include_router(admin_settings_router)
app.include_router(admin_categories_router)
app.include_router(admin_products_router)
app.include_router(admin_images_router)
app.include_router(admin_orders_router)

from fastapi.responses import RedirectResponse

@app.get("/admin", include_in_schema=False)
async def redirect_admin():
    return RedirectResponse(url="/admin/")

# 2. Static files mounts for Customer Mini App and Admin Mini App
app.mount("/admin", StaticFiles(directory="frontend-admin", html=True), name="admin-frontend")
app.mount("/", StaticFiles(directory="frontend", html=True), name="customer-frontend")
