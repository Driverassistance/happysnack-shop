"""
Настройки AI-агента
"""
from sqlalchemy import Column, Integer, String, Boolean, Time, JSON
from datetime import time
from database import Base

class AIAgentSettings(Base):
    """Настройки AI-агента"""
    __tablename__ = "ai_agent_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Расписание
    enabled = Column(Boolean, default=True)
    send_time = Column(Time, default=time(10, 0))  # Время отправки
    send_days = Column(String(50), default="1,2,3,4,5")  # Дни недели (1=Пн, 7=Вс)
    exclude_holidays = Column(Boolean, default=True)
    
    # Триггеры (в днях)
    trigger_days_no_order = Column(Integer, default=14)  # Не заказывал X дней
    trigger_bonus_amount = Column(Integer, default=1000)  # Много бонусов
    trigger_bonus_expiry_days = Column(Integer, default=7)  # Бонусы сгорают через X дней
    
    # Лимиты
    max_messages_per_day = Column(Integer, default=10)  # Максимум сообщений в день
    min_days_between_messages = Column(Integer, default=3)  # Минимум дней между сообщениями одному клиенту
    
    # Агрессивность продаж (1-10)
    sales_aggressiveness = Column(Integer, default=5)  # 1=мягко, 10=агрессивно
    
    # Исключения (JSON массив дат)
    excluded_dates = Column(JSON, default=list)  # ["2025-01-01", "2025-05-09"]