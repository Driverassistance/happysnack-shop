# backend/start_all.py

import multiprocessing
import uvicorn
import os
import asyncio
import logging
import sys
import pathlib

# ======================================================================
# ФИНАЛЬНОЕ РЕШЕНИЕ ПРОБЛЕМЫ С ПУТЯМИ
# ----------------------------------------------------------------------
# Этот блок находит путь к папке 'backend' и добавляет ее в sys.path.
# Это делает все последующие импорты предсказуемыми и рабочими.
try:
    # Находим абсолютный путь к текущему файлу (start_all.py)
    current_file_path = pathlib.Path(__file__).resolve()
    # Находим родительскую папку 'backend'
    BACKEND_ROOT = current_file_path.parent
    
    # Проверяем, что мы нашли именно папку 'backend'
    if BACKEND_ROOT.name != 'backend':
        # Если нет, возможно, мы в какой-то другой структуре. Ищем 'backend'.
        for parent in current_file_path.parents:
            if parent.name == 'backend':
                BACKEND_ROOT = parent
                break
        else:
            raise FileNotFoundError("Не удалось найти корневую папку 'backend'.")

    # Добавляем папку 'backend' в начало путей поиска Python
    sys.path.insert(0, str(BACKEND_ROOT))
    
    # Меняем текущую рабочую директорию на 'backend'.
    # Это решает проблему 'RuntimeError: Directory 'static' does not exist'
    os.chdir(BACKEND_ROOT)

except Exception as e:
    print(f"КРИТИЧЕСКАЯ ОШИБКА при настройке путей: {e}")
    sys.exit(1)
# ======================================================================


# ======================================================================
# ИМПОРТЫ ПОСЛЕ НАСТРОЙКИ ПУТЕЙ
# Теперь все импорты должны быть относительными, так как мы работаем из 'backend'
# ----------------------------------------------------------------------
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from handlers import (
    common_handlers, registration_handlers, catalog_handlers, cart_handlers,
    order_handlers, profile_handlers, admin_handlers, manager_handlers, ai_handlers
)
from middlewares.db_middleware import DbSessionMiddleware
from database import SessionLocal
from utils.bot_commands import set_bot_commands
from main import app as fastapi_app
from init_db import init_database
# ======================================================================


# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# --- Функции запуска (без изменений) ---
def run_web_server():
    logger.info("Preparing to start web server process...")
    try:
        logger.info("🔄 [WEB] Initializing database...")
        init_database()
        logger.info("✅ [WEB] Database initialization complete.")
    except Exception as e:
        logger.error(f"⚠️ [WEB] Database init error: {e}", exc_info=True)
        return # Выходим, если БД не инициализировалась

    port = int(os.getenv("PORT", 10000))
    logger.info(f"✅ [WEB] Starting FastAPI server on port {port}")
    uvicorn.run(fastapi_app, host="0.0.0.0", port=port, reload=False, workers=1)

async def start_bot_main():
    logger.info("🤖 [BOT] Starting bot...")
    bot = Bot(token=settings.BOT_TOKEN, parse_mode="HTML")
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.update.middleware(DbSessionMiddleware(session_pool=SessionLocal))
    logger.info("...[BOT] DB middleware registered.")
    
    routers_to_include = [
        admin_handlers.router, manager_handlers.router, registration_handlers.router,
        common_handlers.router, catalog_handlers.router, cart_handlers.router,
        order_handlers.router, profile_handlers.router, ai_handlers.router
    ]
    dp.include_routers(*routers_to_include)
    logger.info("...[BOT] All routers included.")
    
    await set_bot_commands(bot)
    logger.info("...[BOT] Bot commands set.")
    
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("...[BOT] Webhook deleted. Starting polling...")
    await dp.start_polling(bot)

def run_telegram_bot():
    logger.info("🚀 Preparing to start Telegram bot process...")
    try:
        asyncio.run(start_bot_main())
    except Exception as e:
        logger.error(f"💥 [BOT] An unexpected error occurred in bot process: {e}", exc_info=True)

# --- Главный блок ---
if __name__ == '__main__':
    # Устанавливаем метод запуска 'spawn' для лучшей изоляции
    multiprocessing.set_start_method('spawn', force=True)
    
    logger.info("🔥 Main process started. Initializing subprocesses...")
    
    web_process = multiprocessing.Process(target=run_web_server, name="WebServer")
    bot_process = multiprocessing.Process(target=run_telegram_bot, name="TelegramBot")

    web_process.start()
    logger.info(f"Started {web_process.name} with PID: {web_process.pid}")
    
    bot_process.start()
    logger.info(f"Started {bot_process.name} with PID: {bot_process.pid}")

    web_process.join()
    bot_process.join()

    logger.info("✅ All processes finished.")

