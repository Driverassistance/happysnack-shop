from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class BonusTransaction(Base):
    __tablename__ = "bonus_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    amount = Column(Float, nullable=False)  # Положительное = начисление, отрицательное = списание
    type = Column(String, nullable=False)  # earn, spend, expire
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    description = Column(Text)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    client = relationship("Client", back_populates="bonus_transactions")
    order = relationship("Order")