"""
Запуск ТОЛЬКО бота для Railway
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings
from app.database import SessionLocal
from app.middlewares.db_middleware import DbSessionMiddleware
from app.utils.bot_commands import set_bot_commands

# Импортируем хендлеры
from app.handlers import (
    admin_handlers,
    manager_handlers,
    registration_handlers,
    common_handlers,
    catalog_handlers,
    cart_handlers,
    order_handlers,
    profile_handlers,
    ai_handlers
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Запуск бота"""
    logger.info("🤖 Starting bot on Railway...")
    
    bot = Bot(token=settings.BOT_TOKEN, parse_mode="HTML")
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Middleware
    dp.update.middleware(DbSessionMiddleware(session_pool=SessionLocal))
    
    # Подключаем роутеры
    logger.info("Including routers...")
    dp.include_router(admin_handlers.router)
    dp.include_router(manager_handlers.router)
    dp.include_router(registration_handlers.router)
    dp.include_router(common_handlers.router)
    dp.include_router(catalog_handlers.router)
    dp.include_router(cart_handlers.router)
    dp.include_router(order_handlers.router)
    dp.include_router(profile_handlers.router)
    dp.include_router(ai_handlers.router)
    logger.info("All routers included!")
    
    # Устанавливаем команды
    await set_bot_commands(bot)
    
    # Удаляем webhook
    await bot.delete_webhook(drop_pending_updates=True)
    
    logger.info("✅ Bot started! Polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())