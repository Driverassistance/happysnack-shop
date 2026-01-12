from database import SessionLocal
from models.settings import SystemSetting

def init_settings():
    db = SessionLocal()
    try:
        settings = [
            # Бонусная система
            {'key': 'bonus_earn_percent', 'value': '3', 'type': 'int', 'description': 'Процент начисления бонусов от суммы заказа'},
            {'key': 'bonus_max_use_percent', 'value': '70', 'type': 'int', 'description': 'Максимальный процент оплаты бонусами от суммы заказа'},
            {'key': 'bonus_expiry_days', 'value': '30', 'type': 'int', 'description': 'Срок действия бонусов (дней)'},
            
            # Финансы
            {'key': 'min_order_amount', 'value': '10000', 'type': 'int', 'description': 'Минимальная сумма заказа (тенге)'},
            {'key': 'free_delivery_threshold', 'value': '15000', 'type': 'int', 'description': 'Порог бесплатной доставки (тенге)'},
            
            # Пороги подарков/мотиваторов
            {'key': 'tier1_threshold', 'value': '15000', 'type': 'int', 'description': 'Порог 1: Бесплатная доставка'},
            {'key': 'tier1_emoji', 'value': '🚚', 'type': 'string', 'description': 'Эмодзи для порога 1'},
            {'key': 'tier1_title', 'value': 'Бесплатная доставка', 'type': 'string', 'description': 'Название награды порога 1'},
            
            {'key': 'tier2_threshold', 'value': '25000', 'type': 'int', 'description': 'Порог 2: Упаковка кваса'},
            {'key': 'tier2_emoji', 'value': '🥤', 'type': 'string', 'description': 'Эмодзи для порога 2'},
            {'key': 'tier2_title', 'value': 'Упаковка кваса в подарок', 'type': 'string', 'description': 'Название награды порога 2'},
            
            {'key': 'tier3_threshold', 'value': '50000', 'type': 'int', 'description': 'Порог 3: Скидка 5%'},
            {'key': 'tier3_emoji', 'value': '💰', 'type': 'string', 'description': 'Эмодзи для порога 3'},
            {'key': 'tier3_title', 'value': '5% скидка на заказ', 'type': 'string', 'description': 'Название награды порога 3'},
        ]
        
        for s in settings:
            existing = db.query(SystemSetting).filter(SystemSetting.key == s['key']).first()
            if not existing:
                setting = SystemSetting(**s)
                db.add(setting)
                print(f"✅ Добавлено: {s['key']} = {s['value']}")
            else:
                print(f"⚠️  Уже есть: {s['key']}")
        
        db.commit()
        print("\n🎉 Настройки инициализированы!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_settings()
