"""
Запуск бота на Railway (без API)
"""
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    logger.info("🤖 Starting bot on Railway...")
    
    # Импортируем бота из основного файла
    from bot import bot, dp
    
    logger.info("✅ Bot initialized, starting polling...")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())