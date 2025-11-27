"""
Модели для логирования AI-агента
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class AIConversation(Base):
    """История диалогов с AI"""
    __tablename__ = "ai_conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    user_message = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    client = relationship("Client", backref="ai_conversations")

class AIProactiveMessage(Base):
    """Проактивные сообщения от AI"""
    __tablename__ = "ai_proactive_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    reason = Column(String(255), nullable=False)  # Почему написали
    ai_analysis = Column(Text)  # JSON с анализом AI
    message_text = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    
    # Результат
    was_read = Column(Boolean, default=False)
    client_responded = Column(Boolean, default=False)
    resulted_in_order = Column(Boolean, default=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    
    # Relationships
    client = relationship("Client", backref="ai_proactive_messages")
    order = relationship("Order", backref="ai_proactive_messages")