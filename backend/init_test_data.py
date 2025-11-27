"""
Скрипт для создания тестовых данных
"""
from database import SessionLocal
from models.user import User, Client
from models.product import Category, Product
from models.settings import SystemSetting
from datetime import datetime
import bcrypt

def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_test_data():
    db = SessionLocal()
    
    print("🚀 Создание тестовых данных...")
    
    # ============================================
    # 1. СОЗДАЕМ АДМИНА
    # ============================================
    print("\n👤 Создание админа...")
    
    admin_telegram_id = 123456789  # ЗАМЕНИ НА СВОЙ РЕАЛЬНЫЙ!
    
    existing_admin = db.query(User).filter(User.telegram_id == admin_telegram_id).first()
    
    if not existing_admin:
        admin = User(
            telegram_id=admin_telegram_id,
            username="admin",
            role="admin",
            is_active=True
        )
        db.add(admin)
        db.flush()
        print(f"✅ Создан админ: telegram_id={admin_telegram_id}")
    else:
        print(f"ℹ️  Админ уже существует")
    
    # ============================================
    # 2. СОЗДАЕМ МЕНЕДЖЕРА
    # ============================================
    print("\n👔 Создание менеджера...")
    
    manager_telegram_id = 987654321  # ЗАМЕНИ НА СВОЙ РЕАЛЬНЫЙ!
    
    existing_manager = db.query(User).filter(User.telegram_id == manager_telegram_id).first()
    
    if not existing_manager:
        manager = User(
            telegram_id=manager_telegram_id,
            username="manager_aigul",
            role="manager",
            is_active=True
        )
        db.add(manager)
        db.flush()
        print(f"✅ Создан менеджер: telegram_id={manager_telegram_id}")
    else:
        manager = existing_manager
        print(f"ℹ️  Менеджер уже существует")
    
    # ============================================
    # 3. СОЗДАЕМ ТЕСТОВОГО КЛИЕНТА
    # ============================================
    print("\n🏪 Создание тестового клиента...")
    
    client_telegram_id = 111222333  # ЗАМЕНИ НА СВОЙ РЕАЛЬНЫЙ!
    
    existing_client_user = db.query(User).filter(User.telegram_id == client_telegram_id).first()
    
    if not existing_client_user:
        client_user = User(
            telegram_id=client_telegram_id,
            username="test_client",
            role="client",
            is_active=True
        )
        db.add(client_user)
        db.flush()
        
        client = Client(
            user_id=client_user.id,
            company_name="Магазин Тестовый",
            address="г. Алматы, ул. Тестовая 1",
            bin_iin="123456789012",
            manager_id=manager.id,
            status="active",
            discount_percent=5.0,
            bonus_balance=1000.0,
            credit_limit=500000.0,
            debt=0.0,
            payment_delay_days=14
        )
        db.add(client)
        print(f"✅ Создан клиент: {client.company_name}")
    else:
        print(f"ℹ️  Клиент уже существует")
    
    # ============================================
    # 4. СОЗДАЕМ КАТЕГОРИИ
    # ============================================
    print("\n📁 Создание категорий...")
    
    categories_data = [
        {"name": "Попкорн", "sort_order": 1},
        {"name": "Чипсы", "sort_order": 2},
        {"name": "Снеки", "sort_order": 3},
        {"name": "Напитки", "sort_order": 4},
        {"name": "Выпечка", "sort_order": 5},
    ]
    
    categories = {}
    for cat_data in categories_data:
        existing = db.query(Category).filter(Category.name == cat_data["name"]).first()
        if not existing:
            category = Category(**cat_data, is_active=True)
            db.add(category)
            db.flush()
            categories[cat_data["name"]] = category
            print(f"✅ Создана категория: {cat_data['name']}")
        else:
            categories[cat_data["name"]] = existing
            print(f"ℹ️  Категория уже существует: {cat_data['name']}")
    
    # ============================================
    # 5. СОЗДАЕМ ТОВАРЫ
    # ============================================
    print("\n🛍️  Создание товаров...")
    
    products_data = [
        # Попкорн
        {"name": "HAPPY CORN Классический", "category": "Попкорн", "price": 500, "weight": "100г", "package_size": "24 шт", "stock": 156},
        {"name": "HAPPY CORN Сырный", "category": "Попкорн", "price": 520, "weight": "100г", "package_size": "24 шт", "stock": 89},
        {"name": "HAPPY CORN Карамельный", "category": "Попкорн", "price": 550, "weight": "100г", "package_size": "24 шт", "stock": 120},
        {"name": "HAPPY CORN Барбекю", "category": "Попкорн", "price": 520, "weight": "100г", "package_size": "24 шт", "stock": 67},
        
        # Чипсы
        {"name": "Lay's Классические", "category": "Чипсы", "price": 750, "weight": "150г", "package_size": "20 шт", "stock": 200},
        {"name": "Lay's Сметана-лук", "category": "Чипсы", "price": 750, "weight": "150г", "package_size": "20 шт", "stock": 180},
        {"name": "Pringles Original", "category": "Чипсы", "price": 1200, "weight": "165г", "package_size": "12 шт", "stock": 45},
        {"name": "Pringles Сметана", "category": "Чипсы", "price": 1200, "weight": "165г", "package_size": "12 шт", "stock": 38},
        
        # Снеки
        {"name": "Flint Max Сухарики", "category": "Снеки", "price": 380, "weight": "80г", "package_size": "30 шт", "stock": 250},
        {"name": "Flint Max Кириешки", "category": "Снеки", "price": 350, "weight": "70г", "package_size": "30 шт", "stock": 190},
        {"name": "Cheetos Сырные", "category": "Снеки", "price": 650, "weight": "130г", "package_size": "20 шт", "stock": 110},
        {"name": "Doritos Nacho", "category": "Снеки", "price": 800, "weight": "150г", "package_size": "20 шт", "stock": 95},
        
        # Напитки
        {"name": "Coca-Cola 0.5л", "category": "Напитки", "price": 250, "weight": "0.5л", "package_size": "24 шт", "stock": 300},
        {"name": "Fanta 0.5л", "category": "Напитки", "price": 250, "weight": "0.5л", "package_size": "24 шт", "stock": 280},
        {"name": "Sprite 0.5л", "category": "Напитки", "price": 250, "weight": "0.5л", "package_size": "24 шт", "stock": 260},
        {"name": "Red Bull 0.25л", "category": "Напитки", "price": 450, "weight": "0.25л", "package_size": "24 шт", "stock": 150},
        
        # Выпечка
        {"name": "Вафли Артек", "category": "Выпечка", "price": 180, "weight": "75г", "package_size": "40 шт", "stock": 320},
        {"name": "Печенье Юбилейное", "category": "Выпечка", "price": 320, "weight": "112г", "package_size": "30 шт", "stock": 210},
        {"name": "Круассан 7 Days", "category": "Выпечка", "price": 280, "weight": "60г", "package_size": "24 шт", "stock": 145},
        {"name": "Кекс Roshen", "category": "Выпечка", "price": 350, "weight": "65г", "package_size": "24 шт", "stock": 178},
    ]
    
    for prod_data in products_data:
        existing = db.query(Product).filter(Product.name == prod_data["name"]).first()
        if not existing:
            category = categories[prod_data["category"]]
            product = Product(
                name=prod_data["name"],
                category_id=category.id,
                description=f"Качественный продукт {prod_data['name']}",
                price=prod_data["price"],
                weight=prod_data["weight"],
                package_size=prod_data["package_size"],
                stock=prod_data["stock"],
                is_active=True,
                sort_order=0
            )
            db.add(product)
            print(f"✅ Создан товар: {prod_data['name']}")
        else:
            print(f"ℹ️  Товар уже существует: {prod_data['name']}")
    
    db.commit()
    db.close()
    
    print("\n" + "="*50)
    print("🎉 ТЕСТОВЫЕ ДАННЫЕ СОЗДАНЫ!")
    print("="*50)
    print(f"\n📊 Создано:")
    print(f"   • Категорий: {len(categories_data)}")
    print(f"   • Товаров: {len(products_data)}")
    print(f"   • Пользователей: 3 (админ, менеджер, клиент)")
    print(f"\n🔑 ВАЖНО:")
    print(f"   • Admin Telegram ID: {admin_telegram_id}")
    print(f"   • Manager Telegram ID: {manager_telegram_id}")
    print(f"   • Test Client Telegram ID: {client_telegram_id}")
    print(f"\n⚠️  ЗАМЕНИ эти ID на свои реальные в файле init_test_data.py!")

if __name__ == "__main__":
    create_test_data()