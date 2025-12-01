"""
API для работы с товарами
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models.product import Category, Product
from models.user import User, Client
from schemas import (
    Category as CategorySchema,
    Product as ProductSchema,
    ProductWithPrice
)
from api.auth import get_current_user, get_current_client
from utils import calculate_personal_price

router = APIRouter()

@router.get("/categories", response_model=List[CategorySchema])
async def get_categories(
    db: Session = Depends(get_db)
):
    """
    Получить список всех активных категорий
    """
    categories = db.query(Category).filter(
        Category.is_active == True
    ).order_by(Category.sort_order).all()
    
    return categories

@router.get("/", response_model=List[ProductWithPrice])
async def get_products(
    category_id: Optional[int] = Query(None, description="Фильтр по категории"),
    search: Optional[str] = Query(None, description="Поиск по названию"),
    skip: int = Query(0, ge=0, description="Пропустить N товаров"),
    limit: int = Query(50, ge=1, le=100, description="Лимит товаров"),
    user: User = Depends(get_current_user),
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db)
):
    """
    Получить список товаров с персональными ценами
    """
    query = db.query(Product).filter(Product.is_active == True)
    
    # Фильтр по категории
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    # Поиск по названию
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    
    # Сортировка и пагинация
    query = query.order_by(Product.sort_order, Product.name)
    products = query.offset(skip).limit(limit).all()
    
    # Добавляем персональные цены
    result = []
    for product in products:
        personal_price = calculate_personal_price(
            product.price,
            client.discount_percent
        )
        discount_applied = product.price - personal_price
        
        product_dict = {
            **ProductSchema.model_validate(product).model_dump(),
            "personal_price": personal_price,
            "discount_applied": discount_applied
        }
        result.append(product_dict)
    
    return result

@router.get("/{product_id}", response_model=ProductWithPrice)
async def get_product(
    product_id: int,
    user: User = Depends(get_current_user),
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db)
):
    """
    Получить детали товара с персональной ценой
    """
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.is_active == True
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Рассчитываем персональную цену
    personal_price = calculate_personal_price(
        product.price,
        client.discount_percent
    )
    discount_applied = product.price - personal_price
    
    product_dict = {
        **ProductSchema.model_validate(product).model_dump(),
        "personal_price": personal_price,
        "discount_applied": discount_applied
    }
    
    return product_dict

@router.get("/{product_id}/recommendations", response_model=List[ProductWithPrice])
async def get_product_recommendations(
    product_id: int,
    limit: int = Query(4, ge=1, le=10),
    user: User = Depends(get_current_user),
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db)
):
    """
    Получить рекомендованные товары ("Часто берут вместе")
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Получаем рекомендации (пока просто товары из той же категории)
    # TODO: Добавить логику на основе ProductRecommendation
    recommendations = db.query(Product).filter(
        Product.category_id == product.category_id,
        Product.id != product_id,
        Product.is_active == True
    ).limit(limit).all()
    
    # Добавляем персональные цены
    result = []
    for rec_product in recommendations:
        personal_price = calculate_personal_price(
            rec_product.price,
            client.discount_percent
        )
        discount_applied = rec_product.price - personal_price
        
        product_dict = {
            **ProductSchema.model_validate(rec_product).model_dump(),
            "personal_price": personal_price,
            "discount_applied": discount_applied
        }
        result.append(product_dict)
    
    return result