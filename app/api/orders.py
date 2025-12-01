"""
API для работы с заказами
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from database import get_db
from models.user import User, Client
from models.product import Product
from models.order import Order, OrderItem, OrderHistory
from models.bonus import BonusTransaction
from models.settings import SystemSetting
from schemas import Order as OrderSchema, OrderCreate, OrdersList
from api.auth import get_current_user, get_current_client
from api.cart import get_cart_key, carts
from utils import generate_order_number, calculate_personal_price, calculate_bonus_amount
from notifications import notifier

router = APIRouter()

@router.post("/", response_model=OrderSchema)
async def create_order(
    order_data: OrderCreate,
    user: User = Depends(get_current_user),
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db)
):
    """
    Создать заказ из корзины
    """
    # Получаем товары из корзины или из order_data.items
    if order_data.items:
        items_to_order = order_data.items
    else:
        # Берем из корзины
        cart_key = get_cart_key(user.id)
        cart_items = carts.get(cart_key, [])
        
        if not cart_items:
            raise HTTPException(status_code=400, detail="Cart is empty")
        
        items_to_order = [{'product_id': item['product_id'], 'quantity': item['quantity']} for item in cart_items]
    
    # Рассчитываем сумму заказа
    total = 0.0
    order_items = []
    
    for item in items_to_order:
        product = db.query(Product).filter(
            Product.id == item.product_id,
            Product.is_active == True
        ).first()
        
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        
        if product.stock < item.quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {product.name}"
            )
        
        personal_price = calculate_personal_price(product.price, client.discount_percent)
        subtotal = personal_price * item.quantity
        total += subtotal
        
        order_items.append({
            'product_id': product.id,
            'product_name': product.name,
            'quantity': item.quantity,
            'price': personal_price,
            'subtotal': subtotal
        })
    
    # Проверяем минимальную сумму заказа
    min_order = db.query(SystemSetting).filter(
        SystemSetting.key == "min_order_amount"
    ).first()
    
    if min_order and total < float(min_order.value):
        raise HTTPException(
            status_code=400,
            detail=f"Minimum order amount is {min_order.value} тенге"
        )
    
    # Применяем бонусы
    bonus_used = 0.0
    if order_data.bonus_to_use > 0:
        if order_data.bonus_to_use > client.bonus_balance:
            raise HTTPException(status_code=400, detail="Insufficient bonus balance")
        
        # Проверяем макс % оплаты бонусами
        max_bonus_percent = db.query(SystemSetting).filter(
            SystemSetting.key == "bonus_max_use_percent"
        ).first()
        
        max_bonus_amount = total * (float(max_bonus_percent.value) / 100) if max_bonus_percent else total * 0.3
        
        bonus_used = min(order_data.bonus_to_use, max_bonus_amount, client.bonus_balance)
    
    discount_amount = total * (client.discount_percent / 100)
    final_total = total - bonus_used
    
    # Проверяем кредитный лимит
    if client.debt + final_total > client.credit_limit:
        raise HTTPException(
            status_code=400,
            detail="Credit limit exceeded"
        )
    
    # Создаем заказ
    order = Order(
        order_number=generate_order_number(),
        client_id=client.id,
        manager_id=client.manager_id,
        total=total,
        bonus_used=bonus_used,
        discount_amount=discount_amount,
        final_total=final_total,
        status="new",
        delivery_address=order_data.delivery_address or client.address,
        delivery_date=order_data.delivery_date,
        delivery_time_slot=order_data.delivery_time_slot,
        comment=order_data.comment
    )
    db.add(order)
    db.flush()
    
    # Добавляем товары в заказ
    for item_data in order_items:
        order_item = OrderItem(
            order_id=order.id,
            **item_data
        )
        db.add(order_item)
        
        # Уменьшаем остаток
        product = db.query(Product).filter(Product.id == item_data['product_id']).first()
        product.stock -= item_data['quantity']
    
    # Списываем бонусы
    if bonus_used > 0:
        client.bonus_balance -= bonus_used
        bonus_tx = BonusTransaction(
            client_id=client.id,
            amount=-bonus_used,
            type="spend",
            order_id=order.id,
            description=f"Списание бонусов по заказу {order.order_number}"
        )
        db.add(bonus_tx)
    
    # Увеличиваем долг
    client.debt += final_total
    
    # Записываем историю
    history = OrderHistory(
        order_id=order.id,
        status="new",
        changed_by=user.id,
        comment="Заказ создан"
    )
    db.add(history)
    
    db.commit()
    db.refresh(order)
    
    # Очищаем корзину
    cart_key = get_cart_key(user.id)
    if cart_key in carts:
        carts[cart_key] = []
    
    # TODO: Отправить уведомление менеджеру
    try:
        await notifier.notify_new_order(order, db)
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
    return order

@router.get("/", response_model=OrdersList)
async def get_orders(
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db)
):
    """
    Получить список заказов
    """
    query = db.query(Order).filter(Order.client_id == client.id)
    
    if status:
        query = query.filter(Order.status == status)
    
    total_count = query.count()
    orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        'orders': orders,
        'total_count': total_count
    }

@router.get("/{order_id}", response_model=OrderSchema)
async def get_order(
    order_id: int,
    user: User = Depends(get_current_user),
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db)
):
    """
    Получить детали заказа
    """
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.client_id == client.id
    ).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return order

@router.post("/{order_id}/repeat", response_model=OrderSchema)
async def repeat_order(
    order_id: int,
    user: User = Depends(get_current_user),
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db)
):
    """
    Повторить заказ (скопировать товары в новый заказ)
    """
    old_order = db.query(Order).filter(
        Order.id == order_id,
        Order.client_id == client.id
    ).first()
    
    if not old_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Создаем новый заказ с теми же товарами
    items = [
        {'product_id': item.product_id, 'quantity': item.quantity}
        for item in old_order.items
    ]
    
    order_data = OrderCreate(
        items=items,
        delivery_address=old_order.delivery_address,
        comment="Повтор заказа #" + old_order.order_number
    )
    
    return await create_order(order_data, user, client, db)