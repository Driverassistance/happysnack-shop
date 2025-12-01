# backend/start_all.py

# ======================================================================
# БЛОК №1: НАСТРОЙКА ПУТЕЙ. ВЫПОЛНЯЕТСЯ ПЕРВЫМ.
# Этот код гарантирует, что Python всегда знает, где находится папка 'backend'.
# ----------------------------------------------------------------------
import sys
import pathlib
import os

try:
    # Находим путь к текущему файлу (start_all.py)
    current_file_path = pathlib.Path(__file__).resolve()
    # Его родитель - это папка 'backend'
    BACKEND_ROOT = current_file_path.parent
    
    # Добавляем родителя 'backend' (корень проекта) в пути поиска.
    # Это позволяет Python понимать импорты вида 'from backend.handlers...'
    PROJECT_ROOT = BACKEND_ROOT.parent
    sys.path.insert(0, str(PROJECT_ROOT))
    
    # Меняем рабочую директорию на 'backend'.
    # Это решает проблему с поиском папки 'static' для FastAPI.
    os.chdir(BACKEND_ROOT)

except Exception as e:
    print(f"КРИТИЧЕСКАЯ ОШИБКА при настройке путей: {e}")
    sys.exit(1)
# ======================================================================


# ======================================================================
# БЛОК №2: ВСЕ ОСТАЛЬНЫЕ ИМПОРТЫ. ВЫПОЛНЯЮТСЯ ВТОРЫМИ.
# Теперь, когда пути настроены, все импорты должны быть абсолютными от корня проекта.
# ----------------------------------------------------------------------
import multiprocessing
import uvicorn
import asyncio
import logging

from backend.main import app as fastapi_app
from backend.init_db import init_database
from backend.config import settings
from backend.handlers import (
    common_handlers, registration_handlers, catalog_handlers, cart_handlers,
    order_handlers, profile_handlers, admin_handlers, manager_handlers, ai_handlers
)
from backend.middlewares.db_middleware import DbSessionMiddleware
from backend.database import SessionLocal
from backend.utils.bot_commands import set_bot_commands
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

# --- Главный блок ---
if __name__ == '__main__':
    if sys.version_info >= (3, 8) and sys.platform == 'darwin':
        multiprocessing.set_start_method('spawn', force=True)

    logger.info("🔥 Main process started. Initializing subprocesses...")
    
    web_process = multiprocessing.Process(target=run_web_server, name="WebServer")
    bot_process = multiprocessing.Process(target=run_telegram_bot, name="TelegramBot")

    web_process.start()
    bot_process.start()
    web_process.join()
    bot_process.join()

    logger.info("✅ All processes finished.")
