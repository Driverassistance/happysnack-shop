"""
Модель для аналитики и отслеживания воронки клиентов
"""
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, JSON, Index
from sqlalchemy.sql import func
from database import Base

class AnalyticsEvent(Base):
    """События для аналитики воронки"""
    __tablename__ = "analytics_events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # start, registration_started, registration_completed, first_order, etc
    telegram_id = Column(BigInteger, nullable=False, index=True)
    username = Column(String(100))
    metadata = Column(JSON)  # Дополнительная информация
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Составной индекс для быстрых запросов
    __table_args__ = (
        Index('idx_event_date', 'event_type', 'created_at'),
        Index('idx_user_event', 'telegram_id', 'event_type'),
    )

class ClientMetrics(Base):
    """Метрики клиента для отчетов"""
    __tablename__ = "client_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, nullable=False, index=True)
    telegram_id = Column(BigInteger, nullable=False, index=True)
    
    # Даты ключевых событий
    first_start_at = Column(DateTime(timezone=True))
    registration_started_at = Column(DateTime(timezone=True))
    registration_completed_at = Column(DateTime(timezone=True))
    first_approved_at = Column(DateTime(timezone=True))
    first_order_at = Column(DateTime(timezone=True))
    last_order_at = Column(DateTime(timezone=True))
    
    # Метрики
    total_orders = Column(Integer, default=0)
    total_spent = Column(Integer, default=0)  # В тенге
    total_bonus_earned = Column(Integer, default=0)
    total_bonus_used = Column(Integer, default=0)
    current_cashback_percent = Column(Integer, default=3)  # Текущий процент кэшбека
    
    # Источник
    referral_code = Column(String(50))  # Если пришел по реферальной ссылке
    utm_source = Column(String(100))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())