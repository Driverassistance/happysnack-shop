"""
Миграция: создание таблиц аналитики (ИСПРАВЛЕННАЯ)
"""
import os
from sqlalchemy import create_engine, text

# ВСТАВЬ СВОЙ DATABASE_URL В КАВЫЧКАХ!
DATABASE_URL = "postgresql://happysnack:rj8pjdH24fVZLM1SblGbd5nPNWQ1HPzj@dpg-d4k1sps9c44c73elht1g-a.frankfurt-postgres.render.com/happysnack_8l9f"

print("🔄 Начинаем миграцию (ИСПРАВЛЕННАЯ ВЕРСИЯ)...")
print(f"📊 Подключение к БД...")

engine = create_engine(DATABASE_URL)

sql = """
-- Сначала удаляем старую таблицу если была с ошибкой
DROP TABLE IF EXISTS analytics_events CASCADE;
DROP TABLE IF EXISTS client_metrics CASCADE;

-- Таблица событий аналитики (ИСПРАВЛЕННАЯ)
CREATE TABLE analytics_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    telegram_id BIGINT NOT NULL,
    username VARCHAR(100),
    event_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

CREATE INDEX idx_analytics_event_type ON analytics_events(event_type);
CREATE INDEX idx_analytics_telegram_id ON analytics_events(telegram_id);
CREATE INDEX idx_analytics_created_at ON analytics_events(created_at);

-- Таблица метрик клиентов
CREATE TABLE client_metrics (
    id SERIAL PRIMARY KEY,
    client_id INTEGER NOT NULL,
    telegram_id BIGINT NOT NULL,
    first_start_at TIMESTAMP WITH TIME ZONE,
    registration_started_at TIMESTAMP WITH TIME ZONE,
    registration_completed_at TIMESTAMP WITH TIME ZONE,
    first_approved_at TIMESTAMP WITH TIME ZONE,
    first_order_at TIMESTAMP WITH TIME ZONE,
    last_order_at TIMESTAMP WITH TIME ZONE,
    total_orders INTEGER DEFAULT 0,
    total_spent BIGINT DEFAULT 0,
    total_bonus_earned INTEGER DEFAULT 0,
    total_bonus_used INTEGER DEFAULT 0,
    current_cashback_percent INTEGER DEFAULT 3,
    referral_code VARCHAR(50),
    utm_source VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_client_metrics_client_id ON client_metrics(client_id);
CREATE INDEX idx_client_metrics_telegram_id ON client_metrics(telegram_id);
"""

try:
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
        print("✅ Миграция успешно выполнена!")
        print("")
        print("📋 Проверяем таблицы...")
        
        # Проверка
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('analytics_events', 'client_metrics')
        """))
        
        tables = [row[0] for row in result]
        
        if 'analytics_events' in tables:
            print("  ✅ analytics_events создана")
        else:
            print("  ❌ analytics_events НЕ создана")
            
        if 'client_metrics' in tables:
            print("  ✅ client_metrics создана")
        else:
            print("  ❌ client_metrics НЕ создана")
            
        print("")
        print("🎉 Готово! Теперь замени файлы и пуши в Railway!")
        
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()