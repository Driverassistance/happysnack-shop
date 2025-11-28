"""
Главное приложение FastAPI
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from config import settings

app = FastAPI(
    title="HappySnack B2B Shop",
    description="Telegram Mini App для B2B продаж",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Подключаем роутеры (ДО if __name__!)
from api import auth
from api import products
from api import cart
from api import orders
from api import admin
from api import ai_dashboard

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(cart.router, prefix="/api/cart", tags=["Cart"])
app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(ai_dashboard.router, prefix="/api/ai", tags=["AI Dashboard"])

@app.get("/")
async def root():
    return {
        "message": "HappySnack B2B Shop API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health():
    return {"status": "ok"}

