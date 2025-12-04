"""
Модели для аналитики и метрик
"""
from sqlalchemy import Column, Integer, String, BigInteger, DateTime, JSON
from sqlalchemy.sql import func
from database import Base
from datetime import datetime

class AnalyticsEvent(Base):
    """События аналитики (start, registration_started, и т.д.)"""
    __tablename__ = "analytics_events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    username = Column(String(100))
    event_metadata = Column(JSON)  # ← ИСПРАВЛЕНО: было metadata, теперь event_metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class ClientMetrics(Base):
    """Метрики клиента для аналитики"""
    __tablename__ = "client_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, nullable=False, index=True)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    
    # Временные метки ключевых событий
    first_start_at = Column(DateTime(timezone=True))
    registration_started_at = Column(DateTime(timezone=True))
    registration_completed_at = Column(DateTime(timezone=True))
    first_approved_at = Column(DateTime(timezone=True))
    first_order_at = Column(DateTime(timezone=True))
    last_order_at = Column(DateTime(timezone=True))
    
    # Метрики заказов
    total_orders = Column(Integer, default=0)
    total_spent = Column(BigInteger, default=0)  # в тиынах
    
    # Метрики бонусов
    total_bonus_earned = Column(Integer, default=0)
    total_bonus_used = Column(Integer, default=0)
    current_cashback_percent = Column(Integer, default=3)  # начальный 3%
    
    # Дополнительные данные
    referral_code = Column(String(50))
    utm_source = Column(String(100))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())