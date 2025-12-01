# backend/start_all.py

import multiprocessing
import uvicorn
import os
import asyncio
import logging

# ======================================================================
# ШАГ 1: РЕШЕНИЕ ПРОБЛЕМЫ С ПУТЯМИ (PYTHONPATH)
# Это самый важный блок. Он должен быть в самом верху.
# ----------------------------------------------------------------------
import sys
import pathlib

# Вычисляем путь к папке 'backend' и добавляем ее родителя (корень проекта) в sys.path
# Это позволяет использовать абсолютные импорты вида 'from backend.handlers ...'
# и гарантирует, что дочерние процессы (multiprocessing) унаследуют правильные пути.
PROJECT_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
# ======================================================================


# ======================================================================
# ШАГ 2: ИМПОРТЫ ПОСЛЕ НАСТРОЙКИ ПУТЕЙ
# Теперь, когда пути настроены, все абсолютные импорты будут работать.
# ----------------------------------------------------------------------
from backend.config import settings
from backend.handlers import (
    common_handlers, registration_handlers, catalog_handlers, cart_handlers,
    order_handlers, profile_handlers, admin_handlers, manager_handlers, ai_handlers
)
from backend.middlewares.db_middleware import DbSessionMiddleware
from backend.database import SessionLocal
from backend.utils.bot_commands import set_bot_commands
from backend.main import app as fastapi_app # Импортируем FastAPI приложение
from backend.init_db import init_database
# ======================================================================


# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# --- Функция для запуска веб-сервера ---
def run_web_server():
    """Запускает FastAPI приложение с помощью uvicorn."""
    logger.info("Preparing to start web server process...")
    try:
        # Инициализация БД из того же процесса, где будет работать API
        logger.info("🔄 [WEB] Initializing database...")
        init_database()
        logger.info("✅ [WEB] Database initialization complete.")
    except Exception as e:
        logger.error(f"⚠️ [WEB] Database init error: {e}")

    port = int(os.getenv("PORT", 10000))
    logger.info(f"✅ [WEB] Starting FastAPI server on port {port}")
    uvicorn.run(
        fastapi_app,
        host="0.0.0.0",
        port=port,
        reload=False, # reload=False обязательно для multiprocessing
        workers=1
    )

# --- Функция для запуска телеграм-бота ---
async def start_bot_main():
    """Основная асинхронная функция для запуска бота."""
    logger.info("🤖 [BOT] Starting bot...")

    bot = Bot(token=settings.BOT_TOKEN, parse_mode="HTML")
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Подключаем middleware для сессий БД
    dp.update.middleware(DbSessionMiddleware(session_pool=SessionLocal))
    logger.info("...[BOT] DB middleware registered.")

    # Регистрируем все роутеры
    logger.info("...[BOT] Including routers...")
    routers_to_include = [
        admin_handlers.router, manager_handlers.router, registration_handlers.router,
        common_handlers.router, catalog_handlers.router, cart_handlers.router,
        order_handlers.router, profile_handlers.router, ai_handlers.router
    ]
    dp.include_routers(*routers_to_include)
    logger.info("...[BOT] All routers included.")

    # Устанавливаем команды бота
    await set_bot_commands(bot)
    logger.info("...[BOT] Bot commands set.")

    # Удаляем вебхук и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("...[BOT] Webhook deleted. Starting polling...")
    await dp.start_polling(bot)

def run_telegram_bot():
    """Обёртка для запуска асинхронной функции бота."""
    logger.info("🚀 Preparing to start Telegram bot process...")
    try:
        asyncio.run(start_bot_main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("...[BOT] Bot process stopped!")
    except Exception as e:
        logger.error(f"💥 [BOT] An unexpected error occurred in bot process: {e}", exc_info=True)


# --- Главный блок, который запускает всё ---
if __name__ == '__main__':
    logger.info("🔥 Main process started. Initializing subprocesses...")
    
    # Создаем два отдельных процесса
    web_process = multiprocessing.Process(target=run_web_server, name="WebServer")
    bot_process = multiprocessing.Process(target=run_telegram_bot, name="TelegramBot")

    # Запускаем оба процесса
    web_process.start()
    logger.info(f"Started {web_process.name} with PID: {web_process.pid}")
    
    bot_process.start()
    logger.info(f"Started {bot_process.name} with PID: {bot_process.pid}")

    # Ожидаем их завершения
    web_process.join()
    bot_process.join()

    logger.info("✅ All processes finished.")

