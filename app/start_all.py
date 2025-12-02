import os
import uvicorn

if __name__ == "__main__":
    print("🔄 Initializing database...")
    try:
        from init_db import init_database
        init_database()
    except Exception as e:
        print(f"⚠️ Database init error: {e}")
    
    port = int(os.getenv("PORT", 8000))
    print(f"✅ Starting API on port {port}")
    
    from main import app
    uvicorn.run(app, host="0.0.0.0", port=port)