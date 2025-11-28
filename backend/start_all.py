"""
Запуск только API (без бота)
"""
import os
import uvicorn

if __name__ == "__main__":
    # Инициализируем БД при первом запуске
    print("🔄 Checking database...")
    try:
        from init_db import init_database
        init_database()
    except Exception as e:
        print(f"⚠️ Database init error: {e}")
    
    # Запускаем только API
    port = int(os.getenv("PORT", 8000))
    print(f"✅ Starting API on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port)