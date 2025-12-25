"""
Конфигурация базы данных
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Для продакшена используем PostgreSQL, для локалки - SQLite
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./shop.db"
)

# Принудительно меняем на psycopg (v3) для ЛЮБОГО postgresql URL
if "postgres" in DATABASE_URL:
    # Удаляем старые префиксы
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://")
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")
    # На всякий случай убираем дубликаты
    DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg+psycopg://", "postgresql+psycopg://")

# Настройки подключения
if "postgresql" in DATABASE_URL:
    engine = create_engine(DATABASE_URL)
else:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
