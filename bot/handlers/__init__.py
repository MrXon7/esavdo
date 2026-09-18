from aiogram import Dispatcher
from bot.handlers.start import router as start_router
from bot.handlers.admin_photo import router as admin_photo_router
from bot.handlers.admin_orders import router as admin_orders_router


def register_all_handlers(dp: Dispatcher):
    dp.include_router(start_router)
    dp.include_router(admin_photo_router)
    dp.include_router(admin_orders_router)
