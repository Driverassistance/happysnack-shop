import sys
sys.path.insert(0, 'app')
import os
os.environ['DATABASE_URL'] = 'postgresql+psycopg://postgres:beMFWsfOaMhIpswJxyHrWAKbEntsGCag@interchange.proxy.rlwy.net:51828/railway'

from database import SessionLocal
from models.user import User, Client

db = SessionLocal()
user = db.query(User).filter(User.telegram_id == 473294026).first()

if user:
    print(f"✅ User найден: {user.id}")
    if user.client:
        print(f"✅ Client найден: {user.client.id}")
    else:
        print("❌ Client НЕ НАЙДЕН - создаём!")
        client = Client(
            user_id=user.id,
            company_name="Тестовый клиент",
            status='active',
            first_order_discount=10
        )
        db.add(client)
        db.commit()
        print("✅ Client создан!")
else:
    print("❌ User не найден")

db.close()
