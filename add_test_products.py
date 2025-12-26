import sys
sys.path.insert(0, 'app')

import os
os.environ['DATABASE_URL'] = 'postgresql+psycopg://postgres:beMFWsfOaMhIpswJxyHrWAKbEntsGCag@interchange.proxy.rlwy.net:51828/railway'

from database import SessionLocal
from models.product import Product, Category

db = SessionLocal()

# Создаём категорию
cat = db.query(Category).filter(Category.name == "Попкорн").first()
if not cat:
    cat = Category(name="Попкорн", is_active=True, sort_order=1)
    db.add(cat)
    db.commit()
    print("✅ Категория создана")
else:
    print("✅ Категория уже есть")

# Создаём товары (ВСЕ поля правильные)
products = [
    {"name": "HAPPY CORN Сырный 100г", "price": 450.0, "stock": 100},
    {"name": "HAPPY CORN Карамельный 100г", "price": 450.0, "stock": 100},
    {"name": "HAPPY CORN BBQ 100г", "price": 450.0, "stock": 100},
]

for p in products:
    exists = db.query(Product).filter(Product.name == p['name']).first()
    if not exists:
        product = Product(
            name=p['name'],
            price=p['price'],
            stock=p['stock'],
            category_id=cat.id,
            is_active=True
        )
        db.add(product)
        print(f"✅ Добавлен: {p['name']}")

db.commit()
print(f"\n✅ Готово! Обнови WebApp")
db.close()
