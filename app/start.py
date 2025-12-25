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
    from bot import main as bot_main
    await bot_main()

async def run_api():
    """Запуск API сервера"""
    logger.info("🌐 Starting API Server...")
    from api_server import create_app
    
    app = create_app()
    port = int(os.getenv('PORT', 8080))
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"✅ API Server running on port {port}")
    
    await asyncio.Event().wait()

async def main():
    """Запуск бота и API одновременно"""
    logger.info("🚀 Starting HappySnack unified service...")
    
    # Database initialization
    try:
        from database import Base, engine
        from models.user import User, Client, SalesRepresentative
        from models.product import Product, Category
        from models.order import Order, OrderItem
        from models.bonus import BonusTransaction
        from models.ai_log import AIConversation, AIProactiveMessage
        from models.ai_settings import AIAgentSettings
        from models.analytics import AnalyticsEvent, ClientMetrics
        
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables ready")
    except Exception as e:
        logger.error(f"❌ Database init failed: {e}")
        raise
    
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
