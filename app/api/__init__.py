"""
Собираем все API роутеры
"""
from fastapi import APIRouter
from . import auth, products, cart, orders, admin, ai_dashboard

router = APIRouter()

# Подключаем все роутеры
router.include_router(auth.router, prefix="/auth", tags=["Auth"])
router.include_router(products.router, prefix="/products", tags=["Products"])
router.include_router(cart.router, prefix="/cart", tags=["Cart"])
router.include_router(orders.router, prefix="/orders", tags=["Orders"])
router.include_router(admin.router, prefix="/admin", tags=["Admin"])
router.include_router(ai_dashboard.router, prefix="/ai", tags=["AI Dashboard"])