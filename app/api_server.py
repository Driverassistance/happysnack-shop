"""
API сервер для Telegram WebApp
"""
from aiohttp import web
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import json
import os

from models.user import User, Client
from models.product import Product, Category
from models.order import Order, OrderItem

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

async def get_catalog(request):
    """Получить каталог товаров"""
    try:
        user_id = request.query.get('user_id')
        
        db = SessionLocal()
        
        # Проверяем первый ли это заказ
        user = db.query(User).filter(User.telegram_id == user_id).first()
        is_first_order = False
        
        if user and user.client:
            is_first_order = not user.client.first_order_discount_used
        
        # Загружаем категории
        categories = db.query(Category).filter(Category.is_active == True).order_by(Category.sort_order).all()
        categories_data = [
            {
                'id': cat.id,
                'name': cat.name,
                'icon': get_category_icon(cat.name)
            }
            for cat in categories
        ]
        
        # Загружаем товары
        products = db.query(Product).filter(Product.is_active == True, Product.stock > 0).all()
        products_data = [
            {
                'id': prod.id,
                'name': prod.name,
                'price': float(prod.price),
                'stock': prod.stock,
                'category_id': prod.category_id,
                'photo_url': f'/api/photo/{prod.photo_file_id}' if prod.photo_file_id else None
            }
            for prod in products
        ]
        
        db.close()
        
        return web.json_response({
            'products': products_data,
            'categories': categories_data,
            'is_first_order': is_first_order
        })
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

def get_category_icon(name):
    """Получить иконку категории"""
    icons = {
        'Попкорн': '🍿',
        'Чипсы': '🥔',
        'Батончики': '🍫',
        'Хлебцы': '🍞',
        'Напитки': '🥤',
        'Выпечка': '🥐'
    }
    return icons.get(name, '📦')

async def serve_webapp(request):
    """Отдать webapp файлы"""
    file_path = request.match_info.get('path', 'index.html')
    
    if file_path == '':
        file_path = 'index.html'
    
    try:
        with open(f'app/webapp/{file_path}', 'r', encoding='utf-8') as f:
            content = f.read()
        
        content_type = 'text/html'
        if file_path.endswith('.js'):
            content_type = 'application/javascript'
        elif file_path.endswith('.css'):
            content_type = 'text/css'
        elif file_path.endswith('.json'):
            content_type = 'application/json'
        
        return web.Response(text=content, content_type=content_type)
    except FileNotFoundError:
        return web.Response(status=404)

def create_app():
    app = web.Application()
    
    # API routes
    app.router.add_get('/api/catalog', get_catalog)
    
    # WebApp routes
    app.router.add_get('/', serve_webapp)
    app.router.add_get('/{path:.*}', serve_webapp)
    
    return app

if __name__ == '__main__':
    app = create_app()
    web.run_app(app, host='0.0.0.0', port=8080)
