"""
Запуск API и бота вместе
"""
import asyncio
import os
from multiprocessing import Process
import uvicorn

def run_api():
    """Запуск FastAPI"""
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)

def run_bot():
    """Запуск Telegram бота"""
    import bot
    asyncio.run(bot.main())

if __name__ == "__main__":
    # Инициализируем БД при первом запуске
    print("🔄 Checking database...")
    try:
        from init_db import init_database
        init_database()
    except Exception as e:
        print(f"⚠️ Database init error: {e}")
    
    # Запускаем API в отдельном процессе
    api_process = Process(target=run_api)
    api_process.start()
    
    print("✅ API started")
    
    # Запускаем бота в основном процессе
    print("🤖 Starting bot...")
    run_bot()