from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# --- ИСПРАВЛЕННЫЕ ИМПОРТЫ ---
from app.config import settings
from app.api import router as api_router
# ----------------------------

app = FastAPI(
    title="HappySnack Shop API",
    description="API для магазина закусок в Telegram",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Настройка CORS (чтобы фронтенд мог общаться с бэкендом)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене лучше указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение статики (картинки товаров и т.д.)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Подключение роутеров API
app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {
        "message": "Welcome to HappySnack Shop API!",
        "docs": "/docs",
        "status": "ok"
    }