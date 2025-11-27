"""
Скрипт для инициализации дефолтных настроек системы
"""
from sqlalchemy.orm import Session
from database import SessionLocal
from models.settings import SystemSetting

def init_default_settings():
    db = SessionLocal()
    
    default_settings = [
        {"key": "bonus_percent_default", "value": "2.0", "type": "float", "description": "Процент начисления бонусов от суммы заказа"},
        {"key": "bonus_expiry_months", "value": "6", "type": "int", "description": "Срок действия бонусов в месяцах"},
        {"key": "bonus_max_use_percent", "value": "30", "type": "int", "description": "Максимальный процент оплаты заказа бонусами"},
        {"key": "credit_limit_default", "value": "500000", "type": "float", "description": "Кредитный лимит по умолчанию (₸)"},
        {"key": "payment_delay_default", "value": "14", "type": "int", "description": "Отсрочка платежа по умолчанию (дней)"},
        {"key": "min_order_amount", "value": "10000", "type": "float", "description": "Минимальная сумма заказа (₸)"},
    ]
    
    existing_keys = {s.key for s in db.query(SystemSetting).all()}
    
    added = 0
    for setting in default_settings:
        if setting["key"] not in existing_keys:
            db_setting = SystemSetting(**setting)
            db.add(db_setting)
            added += 1
    
    db.commit()
    db.close()
    
    print(f"✅ Добавлено настроек: {added}")

if __name__ == "__main__":
    init_default_settings()
