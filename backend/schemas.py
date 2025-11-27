"""
Pydantic схемы для валидации данных API
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date

# ============================================
# ПОЛЬЗОВАТЕЛИ
# ============================================

class UserBase(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    phone: Optional[str] = None

class UserCreate(UserBase):
    role: str = "client"

class User(UserBase):
    id: int
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============================================
# КЛИЕНТЫ
# ============================================

class ClientBase(BaseModel):
    company_name: str
    address: Optional[str] = None
    bin_iin: Optional[str] = None

class ClientCreate(ClientBase):
    pass

class Client(ClientBase):
    id: int
    user_id: int
    status: str
    discount_percent: float
    bonus_balance: float
    credit_limit: float
    debt: float
    payment_delay_days: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ClientProfile(BaseModel):
    """Полный профиль клиента для фронтенда"""
    user: User
    client: Client
    manager_name: Optional[str] = None

# ============================================
# ТОВАРЫ
# ============================================

class CategoryBase(BaseModel):
    name: str
    sort_order: int = 0

class Category(CategoryBase):
    id: int
    is_active: bool
    
    class Config:
        from_attributes = True

class ProductBase(BaseModel):
    name: str
    category_id: int
    description: Optional[str] = None
    price: float
    weight: Optional[str] = None
    package_size: Optional[str] = None
    stock: int = 0

class ProductCreate(ProductBase):
    photo_file_id: Optional[str] = None

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category_id: Optional[int] = None
    description: Optional[str] = None
    price: Optional[float] = None
    weight: Optional[str] = None
    package_size: Optional[str] = None
    stock: Optional[int] = None
    photo_file_id: Optional[str] = None
    is_active: Optional[bool] = None

class Product(ProductBase):
    id: int
    photo_file_id: Optional[str] = None
    is_active: bool
    sort_order: int
    created_at: datetime
    category: Category
    
    class Config:
        from_attributes = True

class ProductWithPrice(Product):
    """Товар с персональной ценой клиента"""
    personal_price: float
    discount_applied: float

# ============================================
# КОРЗИНА
# ============================================

class CartItemBase(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)

class CartItemCreate(CartItemBase):
    pass

class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0)

class CartItem(BaseModel):
    id: int
    product: Product
    quantity: int
    subtotal: float
    
    class Config:
        from_attributes = True

class Cart(BaseModel):
    items: List[CartItem]
    total: float
    items_count: int

# ============================================
# ЗАКАЗЫ
# ============================================

class OrderItemBase(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)

class OrderCreate(BaseModel):
    items: List[OrderItemBase]
    delivery_address: Optional[str] = None
    delivery_date: Optional[date] = None
    delivery_time_slot: Optional[str] = None  # morning, afternoon, evening
    comment: Optional[str] = None
    bonus_to_use: float = 0.0
    promocode: Optional[str] = None

class OrderItem(BaseModel):
    id: int
    product_name: str
    quantity: int
    price: float
    subtotal: float
    
    class Config:
        from_attributes = True

class Order(BaseModel):
    id: int
    order_number: str
    total: float
    bonus_used: float
    discount_amount: float
    final_total: float
    status: str
    delivery_address: Optional[str] = None
    delivery_date: Optional[date] = None
    delivery_time_slot: Optional[str] = None
    comment: Optional[str] = None
    created_at: datetime
    items: List[OrderItem]
    
    class Config:
        from_attributes = True

class OrdersList(BaseModel):
    orders: List[Order]
    total_count: int

# ============================================
# БОНУСЫ
# ============================================

class BonusTransaction(BaseModel):
    id: int
    amount: float
    type: str  # earn, spend, expire
    description: str
    expires_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============================================
# СТАТИСТИКА
# ============================================

class ClientStats(BaseModel):
    total_orders: int
    total_spent: float
    average_order: float
    favorite_products: List[dict]

# ============================================
# АДМИНКА
# ============================================

class DashboardStats(BaseModel):
    today_orders: int
    today_revenue: float
    week_orders: int
    week_revenue: float
    pending_clients: int
    low_stock_products: int