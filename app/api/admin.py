"""
API для администраторов и менеджеров
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Header
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from typing import List, Optional
from datetime import datetime, timedelta
from database import get_db
from models.user import User, Client
from models.product import Product, Category
from models.order import Order, OrderItem, OrderHistory
from models.settings import SystemSetting
from schemas import (
    Product as ProductSchema,
    ProductCreate,
    ProductUpdate,
    Category as CategorySchema,
    Client as ClientSchema,
    Order as OrderSchema,
    DashboardStats
)
from api.auth import get_current_user
from config import settings
from notifications import notifier
import logging

logger = logging.getLogger(__name__)
# ============================================
# AUTHENTICATION ДЛЯ ДАШБОРДА
# ============================================

def get_admin_from_header(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Получить админа по telegram_id (для веб-дашборда)
    Временное решение до полноценной аутентификации
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization required")
    
    try:
        telegram_id = int(authorization)
    except:
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return user
router = APIRouter()

def get_admin_user(
    user: User = Depends(get_current_user)
) -> User:
    """
    Проверяет что пользователь - админ или менеджер
    """
    if user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return user

# ============================================
# ТОВАРЫ
# ============================================

@router.get("/products", response_model=List[ProductSchema])
async def admin_get_products(
    category_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(get_admin_from_header),
    db: Session = Depends(get_db)
):
    """
    Получить все товары (включая неактивные)
    """
    query = db.query(Product)
    
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)
    
    products = query.order_by(Product.sort_order, Product.name).offset(skip).limit(limit).all()
    
    return products

@router.post("/products", response_model=ProductSchema)
async def admin_create_product(
    product: ProductCreate,
    admin: User = Depends(get_admin_from_header),
    db: Session = Depends(get_db)
):
    """
    Создать новый товар
    """
    # Проверяем что категория существует
    category = db.query(Category).filter(Category.id == product.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    db_product = Product(
        **product.model_dump(),
        is_active=True,
        sort_order=0
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    return db_product

@router.put("/products/{product_id}", response_model=ProductSchema)
async def admin_update_product(
    product_id: int,
    product_update: ProductUpdate,
    admin: User = Depends(get_admin_from_header),
    db: Session = Depends(get_db)
):
    """
    Обновить товар
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    update_data = product_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(product, field, value)
    
    product.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(product)
    
    return product

@router.delete("/products/{product_id}")
async def admin_delete_product(
    product_id: int,
    admin: User = Depends(get_admin_from_header),
    db: Session = Depends(get_db)
):
    """
    Удалить товар (мягкое удаление - делаем неактивным)
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.is_active = False
    db.commit()
    
    return {"message": "Product deleted"}

# ============================================
# КАТЕГОРИИ
# ============================================

@router.post("/categories", response_model=CategorySchema)
async def admin_create_category(
    name: str,
    sort_order: int = 0,
    admin: User = Depends(get_admin_from_header),
    db: Session = Depends(get_db)
):
    """
    Создать категорию
    """
    category = Category(
        name=name,
        sort_order=sort_order,
        is_active=True
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    
    return category

# ============================================
# КЛИЕНТЫ
# ============================================

@router.get("/clients", response_model=List[ClientSchema])
async def admin_get_clients(
    status: Optional[str] = Query(None, description="pending, active, blocked"),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(get_admin_from_header),
    db: Session = Depends(get_db)
):
    """
    Получить список клиентов
    """
    query = db.query(Client)
    
    if status:
        query = query.filter(Client.status == status)
    
    if search:
        query = query.filter(
            or_(
                Client.company_name.ilike(f"%{search}%"),
                Client.bin_iin.ilike(f"%{search}%")
            )
        )
    
    # Для менеджера - только его клиенты
    if admin.role == "manager":
        query = query.filter(Client.manager_id == admin.id)
    
    clients = query.order_by(Client.created_at.desc()).offset(skip).limit(limit).all()
    
    return clients

@router.get("/clients/{client_id}", response_model=ClientSchema)
async def admin_get_client(
    client_id: int,
    admin: User = Depends(get_admin_from_header),
    db: Session = Depends(get_db)
):
    """
    Получить детали клиента
    """
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Менеджер видит только своих
    if admin.role == "manager" and client.manager_id != admin.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return client

@router.put("/clients/{client_id}", response_model=ClientSchema)
async def admin_update_client(
    client_id: int,
    discount_percent: Optional[float] = None,
    credit_limit: Optional[float] = None,
    payment_delay_days: Optional[int] = None,
    manager_id: Optional[int] = None,
    admin: User = Depends(get_admin_from_header),
    db: Session = Depends(get_db)
):
    """
    Обновить параметры клиента
    """
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if discount_percent is not None:
        client.discount_percent = discount_percent
    
    if credit_limit is not None:
        client.credit_limit = credit_limit
    
    if payment_delay_days is not None:
        client.payment_delay_days = payment_delay_days
    
    if manager_id is not None:
        # Проверяем что менеджер существует
        manager = db.query(User).filter(
            User.id == manager_id,
            User.role == "manager"
        ).first()
        
        if not manager:
            raise HTTPException(status_code=404, detail="Manager not found")
        
        client.manager_id = manager_id
    
    db.commit()
    db.refresh(client)
    
    return client

@router.post("/clients/{client_id}/approve")
async def admin_approve_client(
    client_id: int,
    admin: User = Depends(get_admin_from_header),
    db: Session = Depends(get_db)
):
    """
    Одобрить регистрацию клиента
    """
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if client.status != "pending":
        raise HTTPException(status_code=400, detail="Client is not pending")
    
    client.status = "active"
    client.approved_at = datetime.utcnow()
    
    db.commit()
    
    # TODO: Отправить уведомление клиенту
    try:
        await notifier.notify_client_approved(client, db)
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
    return {"message": "Client approved"}

@router.post("/clients/{client_id}/block")
async def admin_block_client(
    client_id: int,
    admin: User = Depends(get_admin_from_header),
    db: Session = Depends(get_db)
):
    """
    Заблокировать клиента
    """
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    client.status = "blocked"
    
    # Блокируем пользователя
    user = db.query(User).filter(User.id == client.user_id).first()
    if user:
        user.is_active = False
    
    db.commit()
    
    return {"message": "Client blocked"}

# ============================================
# ЗАКАЗЫ
# ============================================

@router.get("/orders", response_model=List[OrderSchema])
async def admin_get_orders(
    status: Optional[str] = Query(None),
    client_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    admin: User = Depends(get_admin_from_header),
    db: Session = Depends(get_db)
):
    """
    Получить список заказов
    """
    query = db.query(Order)
    
    # Менеджер видит только заказы своих клиентов
    if admin.role == "manager":
        query = query.filter(Order.manager_id == admin.id)
    
    if status:
        query = query.filter(Order.status == status)
    
    if client_id:
        query = query.filter(Order.client_id == client_id)
    
    if date_from:
        query = query.filter(Order.created_at >= datetime.fromisoformat(date_from))
    
    if date_to:
        query = query.filter(Order.created_at <= datetime.fromisoformat(date_to))
    
    orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
    
    return orders

@router.put("/orders/{order_id}/status")
async def admin_update_order_status(
    order_id: int,
    new_status: str = Query(..., description="new, confirmed, preparing, delivering, delivered, cancelled"),
    comment: Optional[str] = None,
    admin: User = Depends(get_admin_from_header),
    db: Session = Depends(get_db)
):
    """
    Изменить статус заказа
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Менеджер может менять только заказы своих клиентов
    if admin.role == "manager" and order.manager_id != admin.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    old_status = order.status
    order.status = new_status
    order.updated_at = datetime.utcnow()
    
    if new_status == "delivered":
        order.delivered_at = datetime.utcnow()
        
        # Начисляем бонусы
        from models.settings import SystemSetting
        from models.bonus import BonusTransaction
        from utils import calculate_bonus_amount
        from dateutil.relativedelta import relativedelta
        
        bonus_percent_setting = db.query(SystemSetting).filter(
            SystemSetting.key == "bonus_percent_default"
        ).first()
        
        bonus_expiry_setting = db.query(SystemSetting).filter(
            SystemSetting.key == "bonus_expiry_months"
        ).first()
        
        bonus_percent = float(bonus_percent_setting.value) if bonus_percent_setting else 2.0
        expiry_months = int(bonus_expiry_setting.value) if bonus_expiry_setting else 6
        
        bonus_amount = calculate_bonus_amount(order.total, bonus_percent)
        
        if bonus_amount > 0:
            client = db.query(Client).filter(Client.id == order.client_id).first()
            client.bonus_balance += bonus_amount
            
            expires_at = datetime.utcnow() + relativedelta(months=expiry_months)
            
            bonus_tx = BonusTransaction(
                client_id=client.id,
                amount=bonus_amount,
                type="earn",
                order_id=order.id,
                description=f"Начисление бонусов за заказ {order.order_number}",
                expires_at=expires_at
            )
            db.add(bonus_tx)
    
    # Записываем историю
    history = OrderHistory(
        order_id=order.id,
        status=new_status,
        changed_by=admin.id,
        comment=comment or f"Статус изменен: {old_status} → {new_status}"
    )
    db.add(history)
    
    db.commit()
    try:
        await notifier.notify_order_status_changed(order, new_status, db)
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
    
    return {"message": "Order status updated"}
    # TODO: Отправить уведомление клиенту
    
    return {"message": "Order status updated"}

# ============================================
# СТАТИСТИКА
# ============================================

@router.get("/stats/dashboard", response_model=DashboardStats)
async def admin_get_dashboard_stats(
    admin: User = Depends(get_admin_from_header),
    db: Session = Depends(get_db)
):
    """
    Статистика для дашборда
    """
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    
    # Сегодняшние заказы
    today_orders_query = db.query(Order).filter(
        func.date(Order.created_at) == today
    )
    
    if admin.role == "manager":
        today_orders_query = today_orders_query.filter(Order.manager_id == admin.id)
    
    today_orders = today_orders_query.count()
    today_revenue = db.query(func.sum(Order.final_total)).filter(
        func.date(Order.created_at) == today
    ).scalar() or 0.0
    
    # За неделю
    week_orders_query = db.query(Order).filter(
        Order.created_at >= week_ago
    )
    
    if admin.role == "manager":
        week_orders_query = week_orders_query.filter(Order.manager_id == admin.id)
    
    week_orders = week_orders_query.count()
    week_revenue = db.query(func.sum(Order.final_total)).filter(
        Order.created_at >= week_ago
    ).scalar() or 0.0
    
    # Ожидают модерации
    pending_clients = db.query(Client).filter(Client.status == "pending").count()
    
    # Низкие остатки
    low_stock_setting = db.query(SystemSetting).filter(
        SystemSetting.key == "low_stock_threshold"
    ).first()
    threshold = int(low_stock_setting.value) if low_stock_setting else 10
    
    low_stock_products = db.query(Product).filter(
        Product.is_active == True,
        Product.stock < threshold
    ).count()
    
    return {
        "today_orders": today_orders,
        "today_revenue": today_revenue,
        "week_orders": week_orders,
        "week_revenue": week_revenue,
        "pending_clients": pending_clients,
        "low_stock_products": low_stock_products
    }
# ============================================
# ИМПОРТ ТОВАРОВ
# ============================================

@router.post("/products/import")
async def import_products(
    file: UploadFile = File(...),
    admin: User = Depends(get_admin_from_header),
    db: Session = Depends(get_db)
):
    """
    Массовый импорт товаров из Excel/CSV
    
    Формат файла:
    category_name | name | price | weight | package_size | stock | description
    """
    import pandas as pd
    import io
    
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="Поддерживаются только Excel и CSV файлы")
    
    try:
        # Читаем файл
        contents = await file.read()
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        # Проверяем обязательные колонки
        required_columns = ['category_name', 'name', 'price']
        missing = [col for col in required_columns if col not in df.columns]
        
        if missing:
            raise HTTPException(
                status_code=400, 
                detail=f"Отсутствуют обязательные колонки: {', '.join(missing)}"
            )
        
        # Обрабатываем товары
        created = 0
        updated = 0
        errors = []
        
        for idx, row in df.iterrows():
            try:
                # Находим или создаем категорию
                category = db.query(Category).filter(
                    Category.name == str(row['category_name']).strip()
                ).first()
                
                if not category:
                    category = Category(
                        name=str(row['category_name']).strip(),
                        is_active=True,
                        sort_order=0
                    )
                    db.add(category)
                    db.flush()
                
                # Проверяем существует ли товар
                product = db.query(Product).filter(
                    Product.name == str(row['name']).strip()
                ).first()
                
                if product:
                    # Обновляем существующий
                    product.price = float(row['price'])
                    product.category_id = category.id
                    
                    if 'weight' in row and pd.notna(row['weight']):
                        product.weight = str(row['weight'])
                    if 'package_size' in row and pd.notna(row['package_size']):
                        product.package_size = str(row['package_size'])
                    if 'stock' in row and pd.notna(row['stock']):
                        product.stock = int(row['stock'])
                    if 'description' in row and pd.notna(row['description']):
                        product.description = str(row['description'])
                    
                    product.updated_at = datetime.utcnow()
                    updated += 1
                else:
                    # Создаем новый
                    product = Product(
                        name=str(row['name']).strip(),
                        category_id=category.id,
                        price=float(row['price']),
                        weight=str(row['weight']) if 'weight' in row and pd.notna(row['weight']) else None,
                        package_size=str(row['package_size']) if 'package_size' in row and pd.notna(row['package_size']) else None,
                        stock=int(row['stock']) if 'stock' in row and pd.notna(row['stock']) else 0,
                        description=str(row['description']) if 'description' in row and pd.notna(row['description']) else None,
                        is_active=True,
                        sort_order=0
                    )
                    db.add(product)
                    created += 1
                
            except Exception as e:
                errors.append(f"Строка {idx + 2}: {str(e)}")
        
        db.commit()
        
        return {
            "success": True,
            "created": created,
            "updated": updated,
            "errors": errors,
            "total": len(df)
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Ошибка обработки файла: {str(e)}")

@router.get("/products/template")
async def download_template(
    admin: User = Depends(get_admin_from_header)
):
    """
    Скачать шаблон для импорта товаров
    """
    import pandas as pd
    from fastapi.responses import StreamingResponse
    import io
    
    # Создаем шаблон
    template_data = {
        'category_name': ['Попкорн', 'Чипсы', 'Снеки'],
        'name': ['HAPPY CORN Классический', 'Lays Original', 'Flint Сухарики'],
        'price': [500, 750, 380],
        'weight': ['100г', '150г', '80г'],
        'package_size': ['24 шт', '20 шт', '30 шт'],
        'stock': [100, 200, 150],
        'description': ['Попкорн классический', 'Чипсы классические', 'Сухарики со вкусом']
    }
    
    df = pd.DataFrame(template_data)
    
    # Сохраняем в Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Товары')
    
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename=products_template.xlsx'}
    )
# ============================================
# НАСТРОЙКИ
# ============================================

@router.get("/settings")
async def admin_get_settings(
    admin: User = Depends(get_admin_from_header),
    db: Session = Depends(get_db)
):
    """
    Получить все настройки системы
    """
    settings = db.query(SystemSetting).order_by(SystemSetting.key).all()
    
    return settings

@router.put("/settings/{key}")
async def admin_update_setting(
    key: str,
    value: str,
    admin: User = Depends(get_admin_from_header),
    db: Session = Depends(get_db)
):
    """
    Обновить настройку
    """
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    setting.value = value
    setting.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(setting)
    
    return setting