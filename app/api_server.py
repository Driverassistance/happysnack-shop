"""
import logging
logger = logging.getLogger(__name__)
API сервер для Telegram WebApp и Admin Dashboard
Полная версия со всеми endpoints
"""
from aiohttp import web
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, func, desc
import json
import os
from datetime import datetime, timedelta

from models.user import User, Client, SalesRepresentative
from models.product import Product, Category
from models.order import Order, OrderItem
import logging
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+psycopg://')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# ============================================
# WEBAPP ENDPOINTS (существующие)
# ============================================

async def get_catalog(request):
    """Получить каталог товаров для WebApp"""
    try:
        user_id = int(request.query.get('user_id')) if request.query.get('user_id') else None
        
        db = SessionLocal()
        
        user = db.query(User).filter(User.telegram_id == user_id).first()
        is_first_order = False
        
        if user and user.client:
            is_first_order = not user.client.first_order_discount_used
        
        categories = db.query(Category).filter(Category.is_active == True).order_by(Category.sort_order).all()
        categories_data = [
            {
                'id': cat.id,
                'name': cat.name,
                'icon': get_category_icon(cat.name)
            }
            for cat in categories
        ]
        
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

# ============================================
# БЛОК 1: УПРАВЛЕНИЕ ТОВАРАМИ
# ============================================

async def get_products(request):
    """Получить список всех товаров"""
    try:
        db = SessionLocal()
        
        # Фильтры
        category_id = request.query.get('category_id')
        is_active = request.query.get('is_active')
        
        query = db.query(Product)
        
        if category_id:
            query = query.filter(Product.category_id == int(category_id))
        if is_active is not None:
            query = query.filter(Product.is_active == (is_active.lower() == 'true'))
        
        products = query.order_by(Product.name).all()
        
        products_data = [
            {
                'id': p.id,
                'name': p.name,
                'price': float(p.price),
                'stock': p.stock,
                'category_id': p.category_id,
                'is_active': p.is_active,
                'photo_file_id': p.photo_file_id
            }
            for p in products
        ]
        
        db.close()
        return web.json_response(products_data)
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def get_product(request):
    """Получить один товар"""
    try:
        product_id = int(request.match_info['id'])
        db = SessionLocal()
        
        product = db.query(Product).filter(Product.id == product_id).first()
        
        if not product:
            db.close()
            return web.json_response({'error': 'Product not found'}, status=404)
        
        product_data = {
            'id': product.id,
            'name': product.name,
            'price': float(product.price),
            'stock': product.stock,
            'category_id': product.category_id,
            'is_active': product.is_active,
            'photo_file_id': product.photo_file_id
        }
        
        db.close()
        return web.json_response(product_data)
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def create_product(request):
    """Создать новый товар"""
    try:
        data = await request.json()
        db = SessionLocal()
        
        product = Product(
            name=data['name'],
            price=float(data['price']),
            stock=int(data.get('stock', 0)),
            category_id=int(data['category_id']),
            is_active=data.get('is_active', True)
        )
        
        db.add(product)
        db.commit()
        db.refresh(product)
        
        product_data = {
            'id': product.id,
            'name': product.name,
            'price': float(product.price),
            'stock': product.stock,
            'category_id': product.category_id,
            'is_active': product.is_active
        }
        
        db.close()
        return web.json_response(product_data, status=201)
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def update_product(request):
    """Обновить товар"""
    try:
        product_id = int(request.match_info['id'])
        data = await request.json()
        db = SessionLocal()
        
        product = db.query(Product).filter(Product.id == product_id).first()
        
        if not product:
            db.close()
            return web.json_response({'error': 'Product not found'}, status=404)
        
        if 'name' in data:
            product.name = data['name']
        if 'price' in data:
            product.price = float(data['price'])
        if 'stock' in data:
            product.stock = int(data['stock'])
        if 'category_id' in data:
            product.category_id = int(data['category_id'])
        if 'is_active' in data:
            product.is_active = data['is_active']
        
        db.commit()
        db.close()
        
        return web.json_response({'success': True})
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def delete_product(request):
    """Удалить товар (мягкое удаление)"""
    try:
        product_id = int(request.match_info['id'])
        db = SessionLocal()
        
        product = db.query(Product).filter(Product.id == product_id).first()
        
        if not product:
            db.close()
            return web.json_response({'error': 'Product not found'}, status=404)
        
        product.is_active = False
        db.commit()
        db.close()
        
        return web.json_response({'success': True})
        
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
        
        photo_data = await field.read()
        
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
            tmp.write(photo_data)
            tmp_path = tmp.name
        
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

# ============================================
# БЛОК 2: УПРАВЛЕНИЕ КАТЕГОРИЯМИ
# ============================================

async def get_categories(request):
    """Получить список категорий"""
    try:
        db = SessionLocal()
        categories = db.query(Category).order_by(Category.sort_order).all()
        
        categories_data = [
            {
                'id': cat.id,
                'name': cat.name,
                'is_active': cat.is_active,
                'sort_order': cat.sort_order
            }
            for cat in categories
        ]
        
        db.close()
        return web.json_response(categories_data)
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def create_category(request):
    """Создать категорию"""
    try:
        data = await request.json()
        db = SessionLocal()
        
        max_order = db.query(func.max(Category.sort_order)).scalar() or 0
        
        category = Category(
            name=data['name'],
            is_active=data.get('is_active', True),
            sort_order=max_order + 1
        )
        
        db.add(category)
        db.commit()
        db.refresh(category)
        
        category_data = {
            'id': category.id,
            'name': category.name,
            'is_active': category.is_active,
            'sort_order': category.sort_order
        }
        
        db.close()
        return web.json_response(category_data, status=201)
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def update_category(request):
    """Обновить категорию"""
    try:
        category_id = int(request.match_info['id'])
        data = await request.json()
        db = SessionLocal()
        
        category = db.query(Category).filter(Category.id == category_id).first()
        
        if not category:
            db.close()
            return web.json_response({'error': 'Category not found'}, status=404)
        
        if 'name' in data:
            category.name = data['name']
        if 'is_active' in data:
            category.is_active = data['is_active']
        if 'sort_order' in data:
            category.sort_order = int(data['sort_order'])
        
        db.commit()
        db.close()
        
        return web.json_response({'success': True})
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

# ============================================
# БЛОК 3: УПРАВЛЕНИЕ КЛИЕНТАМИ
# ============================================

async def get_clients(request):
    """Получить список клиентов"""
    try:
        db = SessionLocal()
        clients = db.query(Client).order_by(desc(Client.created_at)).all()
        
        clients_data = [
            {
                'id': c.id,
                'company_name': c.company_name,
                'contact_phone': c.contact_phone,
                'address': c.address,
                'bonus_balance': float(c.bonus_balance),
                'first_order_discount_used': c.first_order_discount_used,
                'created_at': c.created_at.isoformat() if c.created_at else None
            }
            for c in clients
        ]
        
        db.close()
        return web.json_response(clients_data)
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def get_client(request):
    """Получить детали клиента"""
    try:
        client_id = int(request.match_info['id'])
        db = SessionLocal()
        
        client = db.query(Client).filter(Client.id == client_id).first()
        
        if not client:
            db.close()
            return web.json_response({'error': 'Client not found'}, status=404)
        
        # Получаем заказы клиента
        orders = db.query(Order).filter(Order.client_id == client_id).order_by(desc(Order.created_at)).limit(10).all()
        
        client_data = {
            'id': client.id,
            'company_name': client.company_name,
            'contact_phone': client.contact_phone,
            'address': client.address,
            'bonus_balance': float(client.bonus_balance),
            'first_order_discount_used': client.first_order_discount_used,
            'created_at': client.created_at.isoformat() if client.created_at else None,
            'recent_orders': [
                {
                    'id': o.id,
                    'total_amount': float(o.total_amount),
                    'status': o.status,
                    'created_at': o.created_at.isoformat() if o.created_at else None
                }
                for o in orders
            ]
        }
        
        db.close()
        return web.json_response(client_data)
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def update_client(request):
    """Обновить клиента"""
    try:
        client_id = int(request.match_info['id'])
        data = await request.json()
        db = SessionLocal()
        
        client = db.query(Client).filter(Client.id == client_id).first()
        
        if not client:
            db.close()
            return web.json_response({'error': 'Client not found'}, status=404)
        
        if 'company_name' in data:
            client.company_name = data['company_name']
        if 'contact_phone' in data:
            client.contact_phone = data['contact_phone']
        if 'address' in data:
            client.address = data['address']
        if 'bonus_balance' in data:
            client.bonus_balance = float(data['bonus_balance'])
        
        db.commit()
        db.close()
        
        return web.json_response({'success': True})
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

# ============================================
# БЛОК 4: УПРАВЛЕНИЕ ЗАКАЗАМИ
# ============================================

async def get_orders(request):
    """Получить список заказов"""
    try:
        db = SessionLocal()
        
        # Фильтры
        status = request.query.get('status')
        limit = int(request.query.get('limit', 100))
        
        query = db.query(Order)
        
        if status:
            query = query.filter(Order.status == status)
        
        orders = query.order_by(desc(Order.created_at)).limit(limit).all()
        
        orders_data = [
            {
                'id': o.id,
                'client_id': o.client_id,
                'client_name': o.client.company_name if o.client else 'Неизвестно',
                'total_amount': float(o.total_amount),
                'discount_amount': float(o.discount_amount),
                'status': o.status,
                'created_at': o.created_at.isoformat() if o.created_at else None
            }
            for o in orders
        ]
        
        db.close()
        return web.json_response(orders_data)
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def get_order(request):
    """Получить детали заказа"""
    try:
        order_id = int(request.match_info['id'])
        db = SessionLocal()
        
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            db.close()
            return web.json_response({'error': 'Order not found'}, status=404)
        
        items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        
        order_data = {
            'id': order.id,
            'client_id': order.client_id,
            'client_name': order.client.company_name if order.client else 'Неизвестно',
            'client_phone': order.client.contact_phone if order.client else None,
            'total_amount': float(order.total_amount),
            'discount_amount': float(order.discount_amount),
            'status': order.status,
            'created_at': order.created_at.isoformat() if order.created_at else None,
            'items': [
                {
                    'product_id': item.product_id,
                    'product_name': item.product.name if item.product else 'Удален',
                    'quantity': item.quantity,
                    'price': float(item.price)
                }
                for item in items
            ]
        }
        
        db.close()
        return web.json_response(order_data)
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def update_order_status(request):
    """Изменить статус заказа"""
    try:
        order_id = int(request.match_info['id'])
        data = await request.json()
        db = SessionLocal()
        
        order = db.query(Order).filter(Order.id == order_id).first()
        
        if not order:
            db.close()
            return web.json_response({'error': 'Order not found'}, status=404)
        
        new_status = data.get('status')
        if new_status not in ['pending', 'confirmed', 'delivered', 'cancelled']:
            db.close()
            return web.json_response({'error': 'Invalid status'}, status=400)
        
        order.status = new_status
        db.commit()
        db.close()
        
        return web.json_response({'success': True})
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

# ============================================
# БЛОК 5: СТАТИСТИКА
# ============================================

async def get_dashboard_stats(request):
    """Получить статистику для dashboard"""
    try:
        db = SessionLocal()
        
        # Период
        days = int(request.query.get('days', 30))
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Общая выручка
        total_revenue = db.query(func.sum(Order.total_amount)).filter(
            Order.created_at >= start_date
        ).scalar() or 0
        
        # Количество заказов
        total_orders = db.query(func.count(Order.id)).filter(
            Order.created_at >= start_date
        ).scalar() or 0
        
        # Новые клиенты
        new_clients = db.query(func.count(Client.id)).filter(
            Client.created_at >= start_date
        ).scalar() or 0
        
        # Топ товары (без фильтра по статусу заказа для начала)
        top_products_query = db.query(
            Product.name,
            func.sum(OrderItem.quantity).label('total_qty')
        ).join(OrderItem).join(Order).filter(
            Order.created_at >= start_date
        ).group_by(Product.id, Product.name).order_by(desc('total_qty')).limit(5)
        
        top_products = top_products_query.all()
        
        # Топ клиенты
        top_clients_query = db.query(
            Client.company_name,
            func.sum(Order.total_amount).label('total_spent')
        ).join(Order).filter(
            Order.created_at >= start_date
        ).group_by(Client.id, Client.company_name).order_by(desc('total_spent')).limit(5)
        
        top_clients = top_clients_query.all()
        
        stats_data = {
            'total_revenue': float(total_revenue),
            'total_orders': total_orders,
            'new_clients': new_clients,
            'avg_order': float(total_revenue / total_orders) if total_orders > 0 else 0,
            'top_products': [
                {'name': p[0] if p[0] else 'Без названия', 'quantity': int(p[1]) if p[1] else 0}
                for p in top_products
            ],
            'top_clients': [
                {'name': c[0] if c[0] else 'Без имени', 'total': float(c[1]) if c[1] else 0}
                for c in top_clients
            ]
        }
        
        db.close()
        return web.json_response(stats_data)
        
    except Exception as e:
        import traceback
        print(f"API Error in get_dashboard_stats: {e}")
        print(traceback.format_exc())
        db.close()
        return web.json_response({'error': str(e)}, status=500)

# ============================================
# БЛОК 6: НАСТРОЙКИ
# ============================================

async def get_settings(request):
    """Получить настройки системы"""
    try:
        settings = {
            'welcome_bonus': int(os.getenv('WELCOME_BONUS', 5000)),
            'min_order_amount': int(os.getenv('MIN_ORDER_AMOUNT', 10000)),
            'first_order_discount_10k': 10,
            'first_order_discount_20k': 15,
            'first_order_discount_30k': 20,
            'notifications_enabled': os.getenv('NOTIFICATIONS_ENABLED', 'true').lower() == 'true'
        }
        
        return web.json_response(settings)
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def update_settings(request):
    """Обновить настройки системы"""
    try:
        data = await request.json()
        
        # В production это нужно сохранять в БД
        # Пока возвращаем успех
        
        return web.json_response({'success': True})
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

# ============================================
# ТОРГОВЫЕ ПРЕДСТАВИТЕЛИ (существующие)
# ============================================

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

# ============================================
# СОЗДАНИЕ ПРИЛОЖЕНИЯ И МАРШРУТЫ
# ============================================


# ============================================
# ЛИЧНЫЙ КАБИНЕТ КЛИЕНТА - API ENDPOINTS
# ============================================

async def get_client_profile(request):
    """Получить профиль клиента"""
    try:
        user_id = int(request.query.get('user_id'))
        db = SessionLocal()
        
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user or not user.client:
            db.close()
            return web.json_response({'error': 'Client not found'}, status=404)
        
        client = user.client
        
        # Определяем статус
        total_spent = db.query(func.sum(Order.total_amount)).filter(
            Order.client_id == client.id
        ).scalar() or 0
        
        if total_spent >= 500000:
            status = 'platinum'
            status_name = 'Платиновый'
        elif total_spent >= 200000:
            status = 'gold'
            status_name = 'Золотой'
        elif total_spent >= 50000:
            status = 'silver'
            status_name = 'Серебряный'
        else:
            status = 'bronze'
            status_name = 'Бронзовый'
        
        # Количество заказов
        orders_count = db.query(func.count(Order.id)).filter(
            Order.client_id == client.id
        ).scalar() or 0
        
        # Экономия
        total_discount = db.query(func.sum(Order.discount_amount)).filter(
            Order.client_id == client.id
        ).scalar() or 0
        
        profile_data = {
            'company_name': client.company_name,
            'phone': client.contact_phone,
            'address': client.address,
            'bonus_balance': float(client.bonus_balance),
            'status': status,
            'status_name': status_name,
            'orders_count': orders_count,
            'total_spent': float(total_spent),
            'total_saved': float(total_discount)
        }
        
        db.close()
        return web.json_response(profile_data)
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def get_client_orders(request):
    """Получить заказы клиента"""
    try:
        user_id = int(request.query.get('user_id'))
        limit = int(request.query.get('limit', 20))
        status = request.query.get('status')
        
        db = SessionLocal()
        
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user or not user.client:
            db.close()
            return web.json_response({'error': 'Client not found'}, status=404)
        
        query = db.query(Order).filter(Order.client_id == user.client.id)
        
        if status:
            query = query.filter(Order.status == status)
        
        orders = query.order_by(desc(Order.created_at)).limit(limit).all()
        
        orders_data = []
        for order in orders:
            items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
            
            orders_data.append({
                'id': order.id,
                'created_at': order.created_at.isoformat() if order.created_at else None,
                'status': order.status,
                'total_amount': float(order.total_amount),
                'discount_amount': float(order.discount_amount),
                'items_count': len(items),
                'items': [
                    {
                        'product_id': item.product_id,
                        'product_name': item.product.name if item.product else 'Удален',
                        'quantity': item.quantity,
                        'price': float(item.price)
                    }
                    for item in items
                ]
            })
        
        db.close()
        return web.json_response(orders_data)
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def repeat_order(request):
    """Повторить заказ - возвращает товары для добавления в корзину"""
    try:
        order_id = int(request.match_info['id'])
        db = SessionLocal()
        
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            db.close()
            return web.json_response({'error': 'Order not found'}, status=404)
        
        items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        
        cart_items = []
        for item in items:
            if item.product and item.product.is_active and item.product.stock > 0:
                cart_items.append({
                    'product_id': item.product_id,
                    'name': item.product.name,
                    'price': float(item.product.price),
                    'quantity': item.quantity
                })
        
        db.close()
        return web.json_response({'cart': cart_items})
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def get_client_favorites(request):
    """Получить избранные товары клиента"""
    try:
        user_id = int(request.query.get('user_id'))
        db = SessionLocal()
        
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user or not user.client:
            db.close()
            return web.json_response({'error': 'Client not found'}, status=404)
        
        # Топ 10 товаров по количеству заказов
        top_products = db.query(
            Product.id,
            Product.name,
            Product.price,
            Product.stock,
            func.sum(OrderItem.quantity).label('total_ordered')
        ).join(OrderItem).join(Order).filter(
            Order.client_id == user.client.id,
            Product.is_active == True
        ).group_by(Product.id, Product.name, Product.price, Product.stock).order_by(
            desc('total_ordered')
        ).limit(10).all()
        
        favorites = [
            {
                'product_id': p[0],
                'name': p[1],
                'price': float(p[2]),
                'stock': p[3],
                'total_ordered': p[4]
            }
            for p in top_products
        ]
        
        db.close()
        return web.json_response(favorites)
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def get_client_stats(request):
    """Получить статистику клиента"""
    try:
        user_id = int(request.query.get('user_id'))
        db = SessionLocal()
        
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user or not user.client:
            db.close()
            return web.json_response({'error': 'Client not found'}, status=404)
        
        client = user.client
        
        # Общая статистика
        total_orders = db.query(func.count(Order.id)).filter(
            Order.client_id == client.id
        ).scalar() or 0
        
        total_spent = db.query(func.sum(Order.total_amount)).filter(
            Order.client_id == client.id
        ).scalar() or 0
        
        total_saved = db.query(func.sum(Order.discount_amount)).filter(
            Order.client_id == client.id
        ).scalar() or 0
        
        avg_order = float(total_spent / total_orders) if total_orders > 0 else 0
        
        # Топ 5 товаров
        top_products = db.query(
            Product.name,
            func.sum(OrderItem.quantity).label('total_qty')
        ).join(OrderItem).join(Order).filter(
            Order.client_id == client.id
        ).group_by(Product.id, Product.name).order_by(
            desc('total_qty')
        ).limit(5).all()
        
        stats_data = {
            'total_orders': total_orders,
            'total_spent': float(total_spent),
            'total_saved': float(total_saved),
            'avg_order': avg_order,
            'top_products': [
                {'name': p[0], 'quantity': p[1]}
                for p in top_products
            ]
        }
        
        db.close()
        return web.json_response(stats_data)
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def submit_feedback(request):
    """Отправить отзыв/идею"""
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        feedback_type = data.get('type')  # 'feedback', 'idea', 'complaint'
        text = data.get('text')
        rating = data.get('rating')
        
        db = SessionLocal()
        
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user or not user.client:
            db.close()
            return web.json_response({'error': 'Client not found'}, status=404)
        
        # Начисляем бонусы
        bonus = 500 if feedback_type == 'feedback' else 1000 if feedback_type == 'idea' else 0
        
        if bonus > 0:
            user.client.bonus_balance += bonus
            db.commit()
        
        # TODO: Сохранить отзыв в БД (добавить таблицу Feedback)
        
        db.close()
        return web.json_response({
            'success': True,
            'bonus_added': bonus,
            'message': f'Спасибо! +{bonus}₸ бонусов начислено'
        })
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def get_current_survey(request):
    """Получить текущий опрос для клиента"""
    try:
        user_id = int(request.query.get('user_id'))
        
        # Простой месячный опрос
        from datetime import datetime
        current_month = datetime.utcnow().strftime('%B %Y')
        
        survey = {
            'id': f'monthly_{datetime.utcnow().strftime("%Y%m")}',
            'title': f'Опрос {current_month}',
            'bonus': 1000,
            'questions': [
                {
                    'id': 'q1',
                    'text': 'Что добавить в ассортимент?',
                    'type': 'multiple_choice',
                    'options': ['Шоколад', 'Больше напитков', 'Печенье', 'Другое']
                },
                {
                    'id': 'q2',
                    'text': 'Что улучшить?',
                    'type': 'multiple_choice',
                    'options': ['Быстрее доставка', 'Больше скидок', 'Упаковка', 'Другое']
                },
                {
                    'id': 'q3',
                    'text': 'Оцените работу за месяц',
                    'type': 'rating',
                    'max': 5
                },
                {
                    'id': 'q4',
                    'text': 'Комментарий (необязательно)',
                    'type': 'text',
                    'required': False
                }
            ]
        }
        
        return web.json_response(survey)
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def submit_survey(request):
    """Отправить заполненный опрос"""
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        survey_id = data.get('survey_id')
        answers = data.get('answers')
        
        db = SessionLocal()
        
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user or not user.client:
            db.close()
            return web.json_response({'error': 'Client not found'}, status=404)
        
        # Начисляем бонусы
        user.client.bonus_balance += 1000
        db.commit()
        
        # TODO: Сохранить ответы в БД
        
        db.close()
        return web.json_response({
            'success': True,
            'bonus_added': 1000,
            'message': 'Спасибо за участие! +1000₸ бонусов'
        })
        
    except Exception as e:
        print(f"API Error: {e}")
        return web.json_response({'error': str(e)}, status=500)

async def serve_profile_webapp(request):
    """Отдать файлы личного кабинета"""
    file_path = request.match_info.get('path', 'index.html')
    
    if file_path == '':
        file_path = 'index.html'
    
    try:
        with open(f'webapp_profile/{file_path}', 'r', encoding='utf-8') as f:
            content = f.read()
        
        content_type = 'text/html'
        if file_path.endswith('.js'):
            content_type = 'application/javascript'
        elif file_path.endswith('.css'):
            content_type = 'text/css'
        
        return web.Response(text=content, content_type=content_type)
    except FileNotFoundError:
        return web.Response(status=404)


async def create_order_from_webapp(request):
    """Создать заказ из WebApp"""
    try:
        data = await request.json()
        user_id = int(data.get('user_id'))
        cart = data.get('cart', {})
        
        db = SessionLocal()
        
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user or not user.client:
            db.close()
            return web.json_response({'error': 'Client not found'}, status=404)
        
        client = user.client
        
        # Считаем сумму
        total = 0
        items = []
        for product_id, qty in cart.items():
            product = db.query(Product).filter(Product.id == int(product_id)).first()
            if product:
                total += product.price * qty
                items.append(OrderItem(
                    product_id=product.id,
                    quantity=qty,
                    price=product.price
                ))
        
        # Создаём заказ
        order = Order(
            client_id=client.id,
            total_amount=total,
            status='pending'
        )
        db.add(order)
        db.flush()
        
        for item in items:
            item.order_id = order.id
            db.add(item)
        
        db.commit()
        
        return web.json_response({
            'success': True,
            'order_id': order.id,
            'total': total,
            'bonus_earned': 0
        })
        
    except Exception as e:
        print(f"Order error: {e}")
        return web.json_response({'error': str(e)}, status=500)
    # WebApp routes
    app.router.add_get('/api/catalog', get_catalog)
    
    # Admin - Товары
    app.router.add_get('/api/admin/products', get_products)
    app.router.add_get('/api/admin/products/{id}', get_product)
    app.router.add_post('/api/admin/products', create_product)
    app.router.add_put('/api/admin/products/{id}', update_product)
    app.router.add_delete('/api/admin/products/{id}', delete_product)
    app.router.add_post('/api/admin/products/{id}/photo', upload_product_photo)
    
    # Admin - Категории
    app.router.add_get('/api/admin/categories', get_categories)
    app.router.add_post('/api/admin/categories', create_category)
    app.router.add_put('/api/admin/categories/{id}', update_category)
    
    # Admin - Клиенты
    app.router.add_get('/api/admin/clients', get_clients)
    app.router.add_get('/api/admin/clients/{id}', get_client)
    app.router.add_put('/api/admin/clients/{id}', update_client)
    
    # Admin - Заказы
    app.router.add_get('/api/admin/orders', get_orders)
    app.router.add_get('/api/admin/orders/{id}', get_order)
    app.router.add_put('/api/admin/orders/{id}/status', update_order_status)
    
    # Admin - Статистика
    app.router.add_get('/api/admin/stats/dashboard', get_dashboard_stats)
    
    # Admin - Настройки
    app.router.add_get('/api/admin/settings', get_settings)
    app.router.add_put('/api/admin/settings', update_settings)
    
    # Admin - Торговые представители
    app.router.add_get('/api/admin/sales_reps', get_sales_reps)
    app.router.add_post('/api/admin/sales_reps', add_sales_rep)
    app.router.add_put('/api/admin/sales_reps/{id}', update_sales_rep)
    
    # Client Profile API
    app.router.add_get('/api/client/profile', get_client_profile)
    app.router.add_get('/api/client/orders', get_client_orders)
    app.router.add_post('/api/client/orders/{id}/repeat', repeat_order)
    app.router.add_get('/api/client/favorites', get_client_favorites)
    app.router.add_get('/api/client/stats', get_client_stats)
    app.router.add_post('/api/client/feedback', submit_feedback)
    app.router.add_get('/api/client/surveys/current', get_current_survey)
    app.router.add_post('/api/client/surveys/submit', submit_survey)
    app.router.add_post('/api/orders/create', create_order_from_webapp)
    
    # Profile WebApp
    app.router.add_get('/profile/', serve_profile_webapp)
    app.router.add_get('/profile/{path:.*}', serve_profile_webapp)
    
    # Dashboard static files
    app.router.add_static('/admin', 'static/admin', name='admin')
    
    # WebApp routes (должны быть в конце)
    app.router.add_get('/', serve_webapp)
    app.router.add_get('/{path:.*}', serve_webapp)
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 8080))
    web.run_app(app, host='0.0.0.0', port=port)
