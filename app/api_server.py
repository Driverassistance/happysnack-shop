"""
API сервер для Telegram WebApp
"""
from aiohttp import web
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import json
import os

from models.user import User, Client, SalesRepresentative
from models.product import Product, Category
from models.order import Order, OrderItem

DATABASE_URL = os.getenv("DATABASE_URL")
# Принудительно используем psycopg3 драйвер
if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://')
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
        with open(f'webapp/{file_path}', 'r', encoding='utf-8') as f:
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


async def get_sales_reps(request):
    """Получить всех торговых представителей"""
    try:
        db = SessionLocal()
        reps = db.query(SalesRepresentative).all()
        
        reps_data = [
            {
                'id': rep.id,
                'name': rep.name,
                'telegram_id': rep.telegram_id,
                'phone': rep.phone,
                'is_active': rep.is_active
            }
            for rep in reps
        ]
        
        db.close()
        return web.json_response(reps_data)
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def update_sales_rep(request):
    """Обновить торгового представителя"""
    try:
        rep_id = int(request.match_info['id'])
        data = await request.json()
        
        db = SessionLocal()
        rep = db.query(SalesRepresentative).filter(SalesRepresentative.id == rep_id).first()
        
        if not rep:
            db.close()
            return web.json_response({'error': 'Not found'}, status=404)
        
        rep.name = data.get('name', rep.name)
        rep.telegram_id = data.get('telegram_id')
        rep.phone = data.get('phone')
        rep.is_active = data.get('is_active', False)
        
        db.commit()
        db.close()
        
        return web.json_response({'success': True})
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def add_sales_rep(request):
    """Добавить торгового представителя"""
    try:
        data = await request.json()
        
        db = SessionLocal()
        
        rep = SalesRepresentative(
            name=data['name'],
            telegram_id=data.get('telegram_id'),
            phone=data.get('phone'),
            is_active=bool(data.get('telegram_id') and data.get('phone'))
        )
        
        db.add(rep)
        db.commit()
        db.refresh(rep)
        
        rep_data = {
            'id': rep.id,
            'name': rep.name,
            'telegram_id': rep.telegram_id,
            'phone': rep.phone,
            'is_active': rep.is_active
        }
        
        db.close()
        return web.json_response(rep_data, status=201)
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def upload_product_photo(request):
    """Загрузить фото товара"""
    try:
        product_id = int(request.match_info['id'])
        
        reader = await request.multipart()
        field = await reader.next()
        
        if field.name != 'photo':
            return web.json_response({'error': 'No photo field'}, status=400)
        
        # Читаем файл
        photo_data = await field.read()
        
        # Сохраняем во временный файл
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
            tmp.write(photo_data)
            tmp_path = tmp.name
        
        # TODO: Загрузить в Telegram и получить file_id
        # Пока просто сохраняем локально
        photo_file_id = f"local_{product_id}"
        
        db = SessionLocal()
        product = db.query(Product).filter(Product.id == product_id).first()
        
        if not product:
            db.close()
            return web.json_response({'error': 'Product not found'}, status=404)
        
        product.photo_file_id = photo_file_id
        db.commit()
        db.close()
        
        import os
        os.unlink(tmp_path)
        
        return web.json_response({'success': True, 'file_id': photo_file_id})
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

def create_app():
    app = web.Application()
    
    # API routes
    app.router.add_get('/api/catalog', get_catalog)
    app.router.add_get('/api/admin/sales_reps', get_sales_reps)
    app.router.add_post('/api/admin/sales_reps', add_sales_rep)
    app.router.add_put('/api/admin/sales_reps/{id}', update_sales_rep)
    app.router.add_post('/api/admin/products/{id}/photo', upload_product_photo)
    
    # Dashboard static files
    app.router.add_static('/admin', 'static/admin', name='admin')
    
    # WebApp routes
    app.router.add_get('/', serve_webapp)
    app.router.add_get('/{path:.*}', serve_webapp)
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 8080))
    web.run_app(app, host='0.0.0.0', port=port)
