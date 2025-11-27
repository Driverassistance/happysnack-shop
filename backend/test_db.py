"""
Простой тест подключения к БД и проверка данных
"""
from database import SessionLocal
from models.settings import SystemSetting

def test_connection():
    print("🔍 Проверка подключения к базе данных...")
    
    db = SessionLocal()
    
    try:
        # Проверяем настройки
        settings_count = db.query(SystemSetting).count()
        print(f"✅ Настроек в базе: {settings_count}")
        
        if settings_count > 0:
            print("\n📋 Примеры:")
            for s in db.query(SystemSetting).limit(3).all():
                print(f"   {s.key} = {s.value}")
            print("\n🎉 База работает отлично!")
        else:
            print("❌ Настройки не загрузились")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_connection()
