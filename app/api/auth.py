"""
API для аутентификации и регистрации
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from models.user import User, Client
from models.settings import SystemSetting
from schemas import (
    ClientCreate, 
    ClientProfile,
    User as UserSchema,
    Client as ClientSchema
)
from utils import verify_telegram_webapp_data

router = APIRouter()

def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    Получает текущего пользователя из Telegram WebApp InitData
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    user_data = verify_telegram_webapp_data(authorization)
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid authorization data")
    
    user = db.query(User).filter(
        User.telegram_id == user_data['telegram_id']
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is blocked")
    
    return user

def get_current_client(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Client:
    """
    Получает клиента текущего пользователя
    """
    if user.role != "client":
        raise HTTPException(status_code=403, detail="Only for clients")
    
    client = db.query(Client).filter(Client.user_id == user.id).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client profile not found")
    
    if client.status != "active":
        raise HTTPException(
            status_code=403, 
            detail=f"Client status: {client.status}"
        )
    
    return client

@router.post("/register", response_model=UserSchema)
async def register_client(
    client_data: ClientCreate,
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """
    Регистрация нового клиента
    """
    user_data = verify_telegram_webapp_data(authorization)
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid authorization data")
    
    existing_user = db.query(User).filter(
        User.telegram_id == user_data['telegram_id']
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="User already registered")
    
    user = User(
        telegram_id=user_data['telegram_id'],
        username=user_data.get('username'),
        role="client",
        is_active=True
    )
    db.add(user)
    db.flush()
    
    credit_limit = db.query(SystemSetting).filter(
        SystemSetting.key == "credit_limit_default"
    ).first()
    
    payment_delay = db.query(SystemSetting).filter(
        SystemSetting.key == "payment_delay_default"
    ).first()
    
    client = Client(
        user_id=user.id,
        company_name=client_data.company_name,
        address=client_data.address,
        bin_iin=client_data.bin_iin,
        status="pending",
        credit_limit=float(credit_limit.value) if credit_limit else 500000.0,
        payment_delay_days=int(payment_delay.value) if payment_delay else 14
    )
    db.add(client)
    db.commit()
    db.refresh(user)
    
    return user

@router.get("/me", response_model=ClientProfile)
async def get_my_profile(
    user: User = Depends(get_current_user),
    client: Client = Depends(get_current_client),
    db: Session = Depends(get_db)
):
    """
    Получить профиль текущего клиента
    """
    manager_name = None
    if client.manager_id:
        manager = db.query(User).filter(User.id == client.manager_id).first()
        if manager:
            manager_name = manager.username or f"ID: {manager.telegram_id}"
    
    return {
        "user": user,
        "client": client,
        "manager_name": manager_name
    }

@router.get("/check")
async def check_registration(
    authorization: str = Header(...),
    db: Session = Depends(get_db)
):
    """
    Проверить зарегистрирован ли пользователь
    """
    user_data = verify_telegram_webapp_data(authorization)
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid authorization data")
    
    user = db.query(User).filter(
        User.telegram_id == user_data['telegram_id']
    ).first()
    
    if not user:
        return {"registered": False, "status": None}
    
    client = db.query(Client).filter(Client.user_id == user.id).first()
    
    return {
        "registered": True,
        "status": client.status if client else None,
        "role": user.role
    }
