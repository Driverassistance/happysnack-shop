"""
API для работы с корзиной
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.user import User, Client
from models.product import Product
from models.order import Order, OrderItem
from schemas import Cart, CartItem as CartItemSchema, CartItemCreate, CartItemUpdate
from api.auth import get_current_user, get_current_client
from utils import calculate_personal_price

router = APIRouter()

# Временное хранилище корзины (в памяти)
# TODO: Перенести в БД (таблица cart)
carts = {}

def get_cart_key(user_id: int) -> str:
    return f"cart_{user_id}"

@router.get("/", response_model=Cart)
async def get_cart(
    user: User = Depends(get_current_user),
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db)
):
    """
    Получить корзину текущего пользователя
    """
    cart_key = get_cart_key(user.id)
    cart_items = carts.get(cart_key, [])
    
    items = []
    total = 0.0
    
    for cart_item in cart_items:
        product = db.query(Product).filter(
            Product.id == cart_item['product_id'],
            Product.is_active == True
        ).first()
        
        if not product:
            continue
        
        personal_price = calculate_personal_price(
            product.price,
            client.discount_percent
        )
        subtotal = personal_price * cart_item['quantity']
        total += subtotal
        
        items.append({
            'id': cart_item['id'],
            'product': product,
            'quantity': cart_item['quantity'],
            'subtotal': subtotal
        })
    
    return {
        'items': items,
        'total': total,
        'items_count': len(items)
    }

@router.post("/", response_model=Cart)
async def add_to_cart(
    item: CartItemCreate,
    user: User = Depends(get_current_user),
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db)
):
    """
    Добавить товар в корзину
    """
    # Проверяем что товар существует
    product = db.query(Product).filter(
        Product.id == item.product_id,
        Product.is_active == True
    ).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    cart_key = get_cart_key(user.id)
    
    if cart_key not in carts:
        carts[cart_key] = []
    
    # Проверяем есть ли товар уже в корзине
    existing_item = None
    for cart_item in carts[cart_key]:
        if cart_item['product_id'] == item.product_id:
            existing_item = cart_item
            break
    
    if existing_item:
        # Увеличиваем количество
        existing_item['quantity'] += item.quantity
    else:
        # Добавляем новый товар
        carts[cart_key].append({
            'id': len(carts[cart_key]) + 1,
            'product_id': item.product_id,
            'quantity': item.quantity
        })
    
    # Возвращаем обновленную корзину
    return await get_cart(user, client, db)

@router.put("/{item_id}", response_model=Cart)
async def update_cart_item(
    item_id: int,
    update: CartItemUpdate,
    user: User = Depends(get_current_user),
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db)
):
    """
    Изменить количество товара в корзине
    """
    cart_key = get_cart_key(user.id)
    cart_items = carts.get(cart_key, [])
    
    item_found = False
    for cart_item in cart_items:
        if cart_item['id'] == item_id:
            cart_item['quantity'] = update.quantity
            item_found = True
            break
    
    if not item_found:
        raise HTTPException(status_code=404, detail="Item not found in cart")
    
    return await get_cart(user, client, db)

@router.delete("/{item_id}", response_model=Cart)
async def remove_from_cart(
    item_id: int,
    user: User = Depends(get_current_user),
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db)
):
    """
    Удалить товар из корзины
    """
    cart_key = get_cart_key(user.id)
    cart_items = carts.get(cart_key, [])
    
    carts[cart_key] = [item for item in cart_items if item['id'] != item_id]
    
    return await get_cart(user, client, db)

@router.delete("/", response_model=Cart)
async def clear_cart(
    user: User = Depends(get_current_user),
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db)
):
    """
    Очистить корзину
    """
    cart_key = get_cart_key(user.id)
    carts[cart_key] = []
    
    return await get_cart(user, client, db)