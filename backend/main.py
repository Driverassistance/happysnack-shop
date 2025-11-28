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
# +++ НАЧАЛО ВРЕМЕННОГО КОДА ДЛЯ СОЗДАНИЯ АДМИНА +++
import logging
from database import SessionLocal
from models.user import User
from config import settings  # Убедимся, что settings импортированы

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.on_event("startup")
def create_admin_on_startup():
    """
    Эта функция выполнится один раз при старте сервера.
    Она создает администратора, если его еще нет.
    """
    logger.info("--- [ADMIN CREATION] Проверка наличия администратора ---")
    
    # ВАЖНО: Убедитесь, что этот ID совпадает с тем, что в admin.js
    # Мы берем его из переменных окружения, как на вашем скриншоте.
    ADMIN_ID_TO_CREATE = settings.ADMIN_TELEGRAM_ID 
    
    if not ADMIN_ID_TO_CREATE:
        logger.error("--- [ADMIN CREATION] Переменная окружения ADMIN_TELEGRAM_ID не найдена!")
        return

    db = SessionLocal()
    try:
        # Проверяем, существует ли уже пользователь с таким ID
        existing_user = db.query(User).filter(User.telegram_id == ADMIN_ID_TO_CREATE).first()
        
        if existing_user:
            logger.info(f"--- [ADMIN CREATION] Администратор с telegram_id={ADMIN_ID_TO_CREATE} уже существует. Ничего не делаем.")
        else:
            logger.warning(f"--- [ADMIN CREATION] Администратор с telegram_id={ADMIN_ID_TO_CREATE} не найден. Создаем нового.")
            
            # Создаем нового пользователя
            new_admin = User(
                telegram_id=ADMIN_ID_TO_CREATE,
                username="admin",  # Можете поменять на любое имя
                first_name="Admin",
                last_name="User",
                role="admin",     # Устанавливаем роль администратора
                is_active=True
            )
            db.add(new_admin)
            db.commit()
            
            logger.info("--- [ADMIN CREATION] УСПЕШНО СОЗДАН НОВЫЙ АДМИНИСТРАТОР! ---")

    except Exception as e:
        logger.error(f"--- [ADMIN CREATION] Ошибка при создании администратора: {e} ---")
        db.rollback() # Откатываем изменения в случае ошибки
    finally:
        db.close()
    logger.info("--- [ADMIN CREATION] Проверка завершена ---")

# +++ КОНЕЦ ВРЕМЕННОГО КОДА ДЛЯ СОЗДАНИЯ АДМИНА +++

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

