"""
Добавить админа в базу
"""
from database import SessionLocal
from models.user import User

def add_admin(telegram_id: int):
    db = SessionLocal()
    
    # Проверяем есть ли уже
    existing = db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if existing:
        # Обновляем роль
        existing.role = "admin"
        existing.is_active = True
        print(f"✅ Пользователь {telegram_id} обновлен до admin")
    else:
        # Создаем нового
        admin = User(
            telegram_id=telegram_id,
            username="admin",
            role="admin",
            is_active=True
        )
        db.add(admin)
        print(f"✅ Создан новый админ: {telegram_id}")
    
    db.commit()
    db.close()

if __name__ == "__main__":
    # ЗАМЕНИ НА СВОЙ РЕАЛЬНЫЙ ID!
    my_telegram_id = 473294026 # ← СЮДА ВСТАВЬ СВОЙ ID
    
    add_admin(my_telegram_id)
    print("\n🎉 Готово! Теперь попробуй /admin в боте")