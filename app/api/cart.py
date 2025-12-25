from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.user import User, Client
from models.product import Product
from models.order import CartItem
from schemas import Cart, CartItemCreate, CartItemUpdate
from api.auth import get_current_user, get_current_client
from utils import calculate_personal_price

router = APIRouter()

@router.get("/", response_model=Cart)
async def get_cart(user: User = Depends(get_current_user), client: Client = Depends(get_current_client), db: Session = Depends(get_db)):
    db_items = db.query(CartItem).filter(CartItem.user_id == user.id).all()
    items = []
    total = 0.0
    for db_item in db_items:
        p = db_item.product
        if not p or not p.is_active: continue
        price = calculate_personal_price(p.price, client.discount_percent)
        subtotal = price * db_item.quantity
        items.append({
            "id": db_item.id,
            "product_id": p.id,
            "product_name": p.name,
            "price": price,
            "quantity": db_item.quantity,
            "subtotal": subtotal,
            "photo_url": f"/static/products/{p.photo_file_id}.jpg" if p.photo_file_id else None
        })
        total += subtotal
    return {"items": items, "total": total}

@router.post("/add", response_model=Cart)
async def add_to_cart(item_in: CartItemCreate, user: User = Depends(get_current_user), client: Client = Depends(get_current_client), db: Session = Depends(get_db)):
    existing = db.query(CartItem).filter(CartItem.user_id == user.id, CartItem.product_id == item_in.product_id).first()
    if existing:
        existing.quantity += item_in.quantity
    else:
        db.add(CartItem(user_id=user.id, product_id=item_in.product_id, quantity=item_in.quantity))
    db.commit()
    return await get_cart(user, client, db)

@router.put("/{item_id}", response_model=Cart)
async def update_cart_item(item_id: int, update: CartItemUpdate, user: User = Depends(get_current_user), client: Client = Depends(get_current_client), db: Session = Depends(get_db)):
    item = db.query(CartItem).filter(CartItem.id == item_id, CartItem.user_id == user.id).first()
    if not item: raise HTTPException(status_code=404, detail="Item not found")
    item.quantity = update.quantity
    db.commit()
    return await get_cart(user, client, db)

@router.delete("/{item_id}", response_model=Cart)
async def remove_from_cart(item_id: int, user: User = Depends(get_current_user), client: Client = Depends(get_current_client), db: Session = Depends(get_db)):
    db.query(CartItem).filter(CartItem.id == item_id, CartItem.user_id == user.id).delete()
    db.commit()
    return await get_cart(user, client, db)
