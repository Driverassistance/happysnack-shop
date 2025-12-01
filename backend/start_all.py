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
    from config import settings
    
    # +++ НАЧАЛО ИЗМЕНЕНИЙ: ДОБАВЛЕНЫ ИМПОРТЫ И РЕГИСТРАЦИЯ +++

    # 1. Импортируем все необходимые обработчики из вашей папки 'handlers'
    #    и другие важные компоненты.
    # 1. Импортируем каждый модуль обработчика НАПРЯМУЮ из папки 'handlers'
    from handlers import common_handlers
    from handlers import registration_handlers
    from handlers import catalog_handlers
    from handlers import cart_handlers
    from handlers import order_handlers
    from handlers import profile_handlers
    from handlers import admin_handlers
    from handlers import manager_handlers
    from handlers import ai_handlers

    from middlewares.db_middleware import DbSessionMiddleware
    from database import SessionLocal
    from utils.bot_commands import set_bot_commands

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("🤖 Starting bot...")

    bot = Bot(token=settings.BOT_TOKEN, parse_mode="HTML")
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # 2. Подключаем middleware для работы с базой данных в каждом хендлере.
    #    Это позволяет не передавать сессию БД в каждую функцию вручную.
    dp.update.middleware(DbSessionMiddleware(session_pool=SessionLocal))

    # 3. Регистрируем все роутеры (обработчики) в правильном порядке.
    #    Порядок важен: сначала более специфичные, потом общие.
    logger.info("Including routers...")
    dp.include_router(admin_handlers.router)
    dp.include_router(manager_handlers.router)
    dp.include_router(registration_handlers.router)
    dp.include_router(common_handlers.router)
    dp.include_router(catalog_handlers.router)
    dp.include_router(cart_handlers.router)
    dp.include_router(order_handlers.router)
    dp.include_router(profile_handlers.router)
    dp.include_router(ai_handlers.router) # Роутер для AI-агента
    logger.info("All routers included.")

    # 4. Устанавливаем команды, которые будут видны в меню Telegram (/start, /help и т.д.).
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
