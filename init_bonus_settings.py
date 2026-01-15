from database import SessionLocal
from app.models.settings import SystemSetting

def init_settings():
    db = SessionLocal()
    try:
        settings = [
            # Бонусная система
            {'key': 'bonus_earn_percent', 'value': '3', 'type': 'int', 'description': 'Процент начисления бонусов'},
            {'key': 'bonus_max_use_percent', 'value': '70', 'type': 'int', 'description': 'Максимум оплаты бонусами (%)'},
            {'key': 'bonus_expiry_days', 'value': '30', 'type': 'int', 'description': 'Срок действия бонусов (дней)'},
            
            # Финансы
            {'key': 'min_order_amount', 'value': '10000', 'type': 'int', 'description': 'Минимальная сумма заказа (₸)'},
            
            # Порог 1 - Бесплатная доставка
            {'key': 'tier1_threshold', 'value': '15000', 'type': 'int', 'description': 'Порог 1: сумма (₸)'},
            {'key': 'tier1_emoji', 'value': '🚚', 'type': 'string', 'description': 'Порог 1: эмодзи'},
            {'key': 'tier1_title', 'value': 'Бесплатная доставка', 'type': 'string', 'description': 'Порог 1: название'},
            {'key': 'tier1_message', 'value': 'Добавьте ещё на {amount}₸ и получите бесплатную доставку!', 'type': 'string', 'description': 'Порог 1: сообщение'},
            
            # Порог 2 - Подарок
            {'key': 'tier2_threshold', 'value': '25000', 'type': 'int', 'description': 'Порог 2: сумма (₸)'},
            {'key': 'tier2_emoji', 'value': '🥤', 'type': 'string', 'description': 'Порог 2: эмодзи'},
            {'key': 'tier2_title', 'value': 'Упаковка кваса в подарок', 'type': 'string', 'description': 'Порог 2: название'},
            {'key': 'tier2_message', 'value': 'Ещё {amount}₸ и упаковка кваса ваша!', 'type': 'string', 'description': 'Порог 2: сообщение'},
            {'key': 'tier2_gift_product_id', 'value': '0', 'type': 'int', 'description': 'Порог 2: ID подарочного товара'},
            
            # Порог 3 - Скидка
            {'key': 'tier3_threshold', 'value': '50000', 'type': 'int', 'description': 'Порог 3: сумма (₸)'},
            {'key': 'tier3_emoji', 'value': '💰', 'type': 'string', 'description': 'Порог 3: эмодзи'},
            {'key': 'tier3_title', 'value': '5% скидка на заказ', 'type': 'string', 'description': 'Порог 3: название'},
            {'key': 'tier3_message', 'value': 'До скидки 5% осталось всего {amount}₸!', 'type': 'string', 'description': 'Порог 3: сообщение'},
        ]
        
        for s in settings:
            existing = db.query(SystemSetting).filter(SystemSetting.key == s['key']).first()
            if not existing:
                setting = SystemSetting(**s)
                db.add(setting)
                print(f"✅ {s['key']}")
            else:
                print(f"⚠️  {s['key']} уже есть")
        
        db.commit()
        print("\n🎉 Готово!")
    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_settings()
