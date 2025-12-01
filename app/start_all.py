# app/start_all.py

import multiprocessing
import uvicorn
import os
import asyncio
import logging
import sys
import pathlib

# ======================================================================
# БЛОК №1: НАСТРОЙКА ПУТЕЙ (ОСТАЕТСЯ БЕЗ ИЗМЕНЕНИЙ)
# ----------------------------------------------------------------------
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
# ======================================================================


# ======================================================================
# БЛОК №2: ИМПОРТЫ (КЛЮЧЕВОЕ ИЗМЕНЕНИЕ)
# Мы импортируем КАЖДЫЙ модуль напрямую, а не через пакет 'app.handlers'.
# Это самое надежное решение.
# ----------------------------------------------------------------------
from app.main import app as fastapi_app
from app.init_db import init_database
from app.config import settings
from app.database import SessionLocal
from app.middlewares.db_middleware import DbSessionMiddleware
from app.utils.bot_commands import set_bot_commands

# --- ПРЯМОЙ ИМПОРТ КАЖДОГО ОБРАБОТЧИКА ---
from app.handlers import common_handlers
from app.handlers import registration_handlers
from app.handlers import catalog_handlers
from app.handlers import cart_handlers
from app.handlers import order_handlers
from app.handlers import profile_handlers
from app.handlers import admin_handlers
from app.handlers import manager_handlers
from app.handlers import ai_handlers
# -----------------------------------------

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
# ======================================================================


# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# --- Функции запуска (без изменений) ---
def run_web_server():
    logger.info("[WEB] Starting process...")
    try:
        init_database()
        logger.info("[WEB] Database initialization complete.")
    except Exception as e:
        logger.error(f"[WEB] Database init error: {e}", exc_info=True)
        return

    os.chdir(PROJECT_ROOT / 'app')
    port = int(os.getenv("PORT", 10000))
    logger.info(f"[WEB] Starting FastAPI server on port {port}")
    uvicorn.run(fastapi_app, host="0.0.0.0", port=port, reload=False, workers=1)

async def start_bot_main():
    logger.info("[BOT] Starting async process...")
    bot = Bot(token=settings.BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(DbSessionMiddleware(session_pool=SessionLocal))
    
    routers = [
        admin_handlers.router, manager_handlers.router, registration_handlers.router,
        common_handlers.router, catalog_handlers.router, cart_handlers.router,
        order_handlers.router, profile_handlers.router, ai_handlers.router
    ]
    dp.include_routers(*routers)
    logger.info("[BOT] All routers included.")
    
    await set_bot_commands(bot)
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("[BOT] Starting polling...")
    await dp.start_polling(bot)

def run_telegram_bot():
    logger.info("[BOT] Preparing to start process...")
    try:
        asyncio.run(start_bot_main())
    except Exception as e:
        logger.error(f"[BOT] An unexpected error occurred: {e}", exc_info=True)

# --- Главный блок (без изменений) ---
if __name__ == '__main__':
    if sys.platform == 'darwin':
        multiprocessing.set_start_method('spawn', force=True)

    logger.info("🔥 Main process started. Initializing subprocesses...")
    
    web_process = multiprocessing.Process(target=run_web_server, name="WebServer")
    bot_process = multiprocessing.Process(target=run_telegram_bot, name="TelegramBot")

    web_process.start()
    bot_process.start()
    web_process.join()
    bot_process.join()

    logger.info("✅ All processes finished.")
