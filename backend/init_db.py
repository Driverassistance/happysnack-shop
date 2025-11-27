"""
Инициализация базы данных при первом запуске
"""
from database import engine, Base, SessionLocal
from models.user import User, Client
from models.product import Product, Category
from models.order import Order, OrderItem
from models.bonus import BonusTransaction
from models.ai_log import AIConversation, AIProactiveMessage
from models.ai_settings import AIAgentSettings
from datetime import time

def init_database():
    """Создаёт таблицы и начальные данные"""
    print("🔄 Initializing database...")
    
    # Создаём все таблицы
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created!")
    
    # Проверяем есть ли уже данные
    db = SessionLocal()
    
    try:
        # Проверяем AI settings
        existing_settings = db.query(AIAgentSettings).first()
        if not existing_settings:
            settings = AIAgentSettings(
                enabled=True,
                send_time=time(10, 0),
                send_days="1,2,3,4,5",
                exclude_holidays=True,
                trigger_days_no_order=14,
                trigger_bonus_amount=1000,
                trigger_bonus_expiry_days=7,
                max_messages_per_day=10,
                min_days_between_messages=3,
                sales_aggressiveness=5,
                excluded_dates=[]
            )
            db.add(settings)
            db.commit()
            print("✅ AI settings created!")
        
        # Создаём тестовую категорию если нет
        existing_cat = db.query(Category).first()
        if not existing_cat:
            category = Category(
                name="Чипсы",
                description="Популярные снеки"
            )
            db.add(category)
            db.commit()
            print("✅ Test category created!")
            
    except Exception as e:
        print(f"⚠️ Error during initialization: {e}")
        db.rollback()
    finally:
        db.close()
    
    print("✅ Database initialized successfully!")

if __name__ == "__main__":
    init_database()