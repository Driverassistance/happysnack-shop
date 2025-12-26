import sys
sys.path.insert(0, 'app')
import os
os.environ['DATABASE_URL'] = 'postgresql+psycopg://postgres:beMFWsfOaMhIpswJxyHrWAKbEntsGCag@interchange.proxy.rlwy.net:51828/railway'

from database import SessionLocal
from models.user import User, Client

db = SessionLocal()

# User уже создан (ID=1), создаём только Client
client = Client(
    user_id=1,
    company_name="HappySnack Test",
    status='active',
    discount_percent=0.0,
    first_order_discount_used=False
)
db.add(client)
db.commit()
print(f"✅ Client создан: ID={client.id}")

db.close()
