import multiprocessing
import uvicorn
import os
import asyncio
import logging

# --- Функция для запуска веб-сервера (без изменений) ---
def run_web_server():
    """Запускает FastAPI приложение с помощью uvicorn."""
    print("🔄 Checking database...")
    try:
        from init_db import init_database
        init_database()
    except Exception as e:
        print(f"⚠️ Database init error: {e}")

    port = int(os.getenv("PORT", 10000))
    print(f"✅ Starting API on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

# --- Функция для запуска телеграм-бота (ДОПОЛНЕНА) ---
async def start_bot_main():
    """Основная асинхронная функция для запуска бота."""
    from aiogram import Bot, Dispatcher
    from aiogram.fsm.storage.memory import MemoryStorage
    
    # +++ НАЧАЛО ИЗМЕНЕНИЙ: ИСПОЛЬЗУЕМ АБСОЛЮТНЫЕ ИМПОРТЫ +++

    # 1. Импортируем все, используя полный путь от корня 'backend'
    from backend.config import settings
    from backend.handlers import common_handlers
    from backend.handlers import registration_handlers
    from backend.handlers import catalog_handlers
    from backend.handlers import cart_handlers
    from backend.handlers import order_handlers
    from backend.handlers import profile_handlers
    from backend.handlers import admin_handlers
    from backend.handlers import manager_handlers
    from backend.handlers import ai_handlers
    
    from backend.middlewares.db_middleware import DbSessionMiddleware
    from backend.database import SessionLocal
    from backend.utils.bot_commands import set_bot_commands

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("🤖 Starting bot...")

    bot = Bot(token=settings.BOT_TOKEN, parse_mode="HTML")
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.update.middleware(DbSessionMiddleware(session_pool=SessionLocal))

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
    logger.info("All routers included.")

    await set_bot_commands(bot)
    
    # +++ КОНЕЦ ИЗМЕНЕНИЙ +++
    
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("...Webhook deleted. Starting polling...")
    await dp.start_polling(bot)


def run_telegram_bot():
    """Обёртка для запуска асинхронной функции бота."""
    print("🚀 Starting Telegram bot process...")
    try:
        asyncio.run(start_bot_main())
    except (KeyboardInterrupt, SystemExit):
        print("...Bot process stopped!")

# --- Главный блок, который запускает всё (без изменений) ---
if __name__ == '__main__':
    web_process = multiprocessing.Process(target=run_web_server)
    bot_process = multiprocessing.Process(target=run_telegram_bot)

    print("🔥 Starting all processes...")
    
    web_process.start()
    bot_process.start()

    web_process.join()
    bot_process.join()

    print("✅ All processes finished.")
