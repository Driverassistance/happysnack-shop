import sys
sys.path.insert(0, 'app')
import os
os.environ['DATABASE_URL'] = 'postgresql+psycopg://postgres:beMFWsfOaMhIpswJxyHrWAKbEntsGCag@interchange.proxy.rlwy.net:51828/railway'

from database import SessionLocal
from models.order import Order

db = SessionLocal()
orders = db.query(Order).all()

if orders:
    print(f"✅ Найдено {len(orders)} заказов:")
    for o in orders:
        print(f"  - Заказ #{o.order_number}, сумма: {o.total}₸, статус: {o.status}")
else:
    print("❌ Заказов нет")

db.close()
