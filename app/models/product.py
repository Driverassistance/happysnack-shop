from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    products = relationship("Product", back_populates="category")

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    weight = Column(String, nullable=True)
    package_size = Column(String, nullable=True)
    stock = Column(Integer, default=0)
    photo_file_id = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    category = relationship("Category", back_populates="products")
    recommendations = relationship(
        "ProductRecommendation",
        foreign_keys="ProductRecommendation.product_id",
        back_populates="product"
    )

class ProductRecommendation(Base):
    __tablename__ = "product_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    recommended_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    weight = Column(Integer, default=1)
    
    # Relationships
    product = relationship("Product", foreign_keys=[product_id], back_populates="recommendations")
    recommended = relationship("Product", foreign_keys=[recommended_id])