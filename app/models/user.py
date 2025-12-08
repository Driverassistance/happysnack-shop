from sqlalchemy import Column, Integer, BigInteger, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    role = Column(String, nullable=False)  # 'client', 'manager', 'admin'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    
    # Relationships - ЯВНО указываем foreign_keys!
    client = relationship(
        "Client", 
        back_populates="user", 
        uselist=False,
        foreign_keys="Client.user_id"  # ← Указываем какой FK использовать
    )
    
    orders_as_manager = relationship(
        "Order", 
        back_populates="manager",
        foreign_keys="Order.manager_id"  # ← Указываем какой FK использовать
    )

class Client(Base):
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    company_name = Column(String, nullable=False)
    address = Column(String)
    bin_iin = Column(String)
    contact_phone = Column(String)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="pending")  # pending, active, blocked
    discount_percent = Column(Float, default=0.0)
    bonus_balance = Column(Float, default=0.0)
    credit_limit = Column(Float, default=0.0)
    debt = Column(Float, default=0.0)
    payment_delay_days = Column(Integer, default=0)
    delivery_zone = Column(String, nullable=True)
    sales_rep_id = Column(Integer, ForeignKey("sales_representatives.id"), nullable=True)
    first_order_discount_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    
    # Relationships - ЯВНО указываем foreign_keys!
    user = relationship(
        "User", 
        back_populates="client",
        foreign_keys=[user_id]  # ← Указываем какой FK использовать
    )
    
    manager = relationship(
        "User",
        foreign_keys=[manager_id]  # ← Указываем какой FK использовать
    )
    
    sales_rep = relationship("SalesRepresentative", back_populates="clients")
    orders = relationship("Order", back_populates="client")
    bonus_transactions = relationship("BonusTransaction", back_populates="client")
class SalesRepresentative(Base):
    __tablename__ = 'sales_representatives'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    telegram_id = Column(BigInteger, unique=True, nullable=True)
    phone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    clients = relationship("Client", back_populates="sales_rep")
