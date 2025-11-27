"""
Инициализация настроек AI-агента
"""
from database import SessionLocal
from models.ai_settings import AIAgentSettings
from datetime import time

def init_ai_settings():
    db = SessionLocal()
    
    # Проверяем есть ли уже настройки
    existing = db.query(AIAgentSettings).first()
    
    if not existing:
        settings = AIAgentSettings(
            enabled=True,
            send_time=time(10, 0),
            send_days="1,2,3,4,5",  # Пн-Пт
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
        print("✅ AI settings initialized")
    else:
        print("ℹ️ AI settings already exist")
    
    db.close()

if __name__ == "__main__":
    init_ai_settings()