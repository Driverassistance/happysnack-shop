"""
Unified startup script for Railway
Runs both BOT and API server simultaneously
"""
import asyncio
import logging
import os
from aiohttp import web

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_bot():
    """Запуск Telegram бота"""
    logger.info("🤖 Starting Telegram Bot...")
    from app.bot import main as bot_main
    await bot_main()

async def run_api():
    """Запуск API сервера"""
    logger.info("🌐 Starting API Server...")
    from app.api_server import create_app
    
    app = create_app()
    port = int(os.getenv('PORT', 8080))
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"✅ API Server running on port {port}")
    
    # Держим API запущенным
    await asyncio.Event().wait()

async def main():
    """Запуск бота и API одновременно"""
    logger.info("🚀 Starting HappySnack unified service...")
    
    try:
        await asyncio.gather(
            run_bot(),
            run_api()
        )
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
