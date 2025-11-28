"""
Главное приложение FastAPI
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from config import settings

app = FastAPI(
    title="HappySnack B2B Shop",
    description="Telegram Mini App для B2B продаж",
    version="1.0.0"
)
# +++ НАЧАЛО ВРЕМЕННОГО КОДА ДЛЯ ОТЛАДКИ +++
import logging
from database import SessionLocal
from models.user import User

# Настраиваем логирование, чтобы видеть сообщения в логах Render
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.on_event("startup")
def print_all_users_on_startup():
    """Эта функция выполнится один раз при старте сервера."""
    logger.info("--- [DEBUG] ПРОВЕРКА ПОЛЬЗОВАТЕЛЕЙ В БАЗЕ ДАННЫХ ---")
    db = SessionLocal()
    try:
        # Пытаемся получить всех пользователей из таблицы 'users'
        all_users = db.query(User).all()
        
        if not all_users:
            logger.warning("--- [DEBUG] ВНИМАНИЕ: Таблица 'users' пуста! ---")
        else:
            logger.info(f"--- [DEBUG] Найдено пользователей: {len(all_users)} ---")
            # Выводим информацию по каждому пользователю
            for user in all_users:
                logger.info(
                    f"--- [DEBUG] Пользователь: id={user.id}, "
                    f"telegram_id={user.telegram_id}, "
                    f"username='{user.username}', "
                    f"role='{user.role}'"
                )
    except Exception as e:
        # Если произойдет ошибка при подключении или запросе к БД
        logger.error(f"--- [DEBUG] КРИТИЧЕСКАЯ ОШИБКА при запросе к БД: {e} ---")
    finally:
        db.close()
    logger.info("--- [DEBUG] ПРОВЕРКА ПОЛЬЗОВАТЕЛЕЙ ЗАВЕРШЕНА ---")

# +++ КОНЕЦ ВРЕМЕННОГО КОДА ДЛЯ ОТЛАДКИ +++

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Подключаем роутеры (ДО if __name__!)
from api import auth
from api import products
from api import cart
from api import orders
from api import admin
from api import ai_dashboard

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(cart.router, prefix="/api/cart", tags=["Cart"])
app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(ai_dashboard.router, prefix="/api/ai", tags=["AI Dashboard"])

@app.get("/")
async def root():
    return {
        "message": "HappySnack B2B Shop API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health():
    return {"status": "ok"}

