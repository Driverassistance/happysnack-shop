"""
API для дашборда AI-агента
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, timedelta

from database import get_db
from models.user import User
from models.ai_log import AIConversation, AIProactiveMessage
from models.ai_settings import AIAgentSettings
from api.admin import get_admin_from_header

router = APIRouter()

@router.get("/stats")
async def get_ai_stats(
    days: int = Query(7, ge=1, le=90),
    admin: User = Depends(get_admin_from_header),
    db: Session = Depends(get_db)
):
    """
    Статистика работы AI-агента
    """
    date_from = datetime.utcnow() - timedelta(days=days)
    
    # Диалоги
    total_conversations = db.query(AIConversation).filter(
        AIConversation.created_at >= date_from
    ).count()
    
    unique_clients_chatted = db.query(func.count(func.distinct(AIConversation.client_id))).filter(
        AIConversation.created_at >= date_from
    ).scalar() or 0
    
    # Проактивные сообщения
    total_proactive = db.query(AIProactiveMessage).filter(
        AIProactiveMessage.sent_at >= date_from
    ).count()
    
    responded = db.query(AIProactiveMessage).filter(
        AIProactiveMessage.sent_at >= date_from,
        AIProactiveMessage.client_responded == True
    ).count()
    
    resulted_in_orders = db.query(AIProactiveMessage).filter(
        AIProactiveMessage.sent_at >= date_from,
        AIProactiveMessage.resulted_in_order == True
    ).count()
    
    # Конверсия
    response_rate = (responded / total_proactive * 100) if total_proactive > 0 else 0
    order_rate = (resulted_in_orders / total_proactive * 100) if total_proactive > 0 else 0
    
    return {
        "period_days": days,
        "conversations": {
            "total": total_conversations,
            "unique_clients": unique_clients_chatted
        },
        "proactive_messages": {
            "total": total_proactive,
            "responded": responded,
            "resulted_in_orders": resulted_in_orders,
            "response_rate": round(response_rate, 1),
            "order_conversion_rate": round(order_rate, 1)
        }
    }

@router.get("/conversations")
async def get_conversations(
    client_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    admin: User = Depends(get_admin_from_header),
    db: Session = Depends(get_db)
):
    """
    История диалогов с AI
    """
    query = db.query(AIConversation)
    
    if client_id:
        query = query.filter(AIConversation.client_id == client_id)
    
    conversations = query.order_by(
        AIConversation.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return [
        {
            "id": conv.id,
            "client_id": conv.client_id,
            "client_name": conv.client.company_name,
            "user_message": conv.user_message,
            "ai_response": conv.ai_response,
            "created_at": conv.created_at.isoformat()
        }
        for conv in conversations
    ]

@router.get("/proactive")
async def get_proactive_messages(
    client_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    admin: User = Depends(get_admin_from_header),
    db: Session = Depends(get_db)
):
    """
    История проактивных сообщений
    """
    query = db.query(AIProactiveMessage)
    
    if client_id:
        query = query.filter(AIProactiveMessage.client_id == client_id)
    
    messages = query.order_by(
        AIProactiveMessage.sent_at.desc()
    ).offset(skip).limit(limit).all()
    
    return [
        {
            "id": msg.id,
            "client_id": msg.client_id,
            "client_name": msg.client.company_name,
            "reason": msg.reason,
            "message_text": msg.message_text,
            "sent_at": msg.sent_at.isoformat(),
            "client_responded": msg.client_responded,
            "resulted_in_order": msg.resulted_in_order,
            "order_id": msg.order_id
        }
        for msg in messages
    ]

@router.get("/settings")
async def get_ai_settings(
    admin: User = Depends(get_admin_from_header),
    db: Session = Depends(get_db)
):
    """
    Получить настройки AI-агента
    """
    settings = db.query(AIAgentSettings).first()
    
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    
    return {
        "enabled": settings.enabled,
        "send_time": settings.send_time.strftime("%H:%M") if settings.send_time else "10:00",
        "send_days": settings.send_days,
        "exclude_holidays": settings.exclude_holidays,
        "trigger_days_no_order": settings.trigger_days_no_order,
        "trigger_bonus_amount": settings.trigger_bonus_amount,
        "trigger_bonus_expiry_days": settings.trigger_bonus_expiry_days,
        "max_messages_per_day": settings.max_messages_per_day,
        "min_days_between_messages": settings.min_days_between_messages,
        "sales_aggressiveness": settings.sales_aggressiveness,
        "excluded_dates": settings.excluded_dates or []
    }

@router.put("/settings")
async def update_ai_settings(
    data: dict,
    admin: User = Depends(get_admin_from_header),
    db: Session = Depends(get_db)
):
    """
    Обновить настройки AI-агента
    """
    settings = db.query(AIAgentSettings).first()
    
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    
    # Обновляем поля
    if "enabled" in data:
        settings.enabled = data["enabled"]
    if "send_time" in data:
        from datetime import datetime
        settings.send_time = datetime.strptime(data["send_time"], "%H:%M").time()
    if "send_days" in data:
        settings.send_days = data["send_days"]
    if "exclude_holidays" in data:
        settings.exclude_holidays = data["exclude_holidays"]
    if "trigger_days_no_order" in data:
        settings.trigger_days_no_order = data["trigger_days_no_order"]
    if "trigger_bonus_amount" in data:
        settings.trigger_bonus_amount = data["trigger_bonus_amount"]
    if "trigger_bonus_expiry_days" in data:
        settings.trigger_bonus_expiry_days = data["trigger_bonus_expiry_days"]
    if "max_messages_per_day" in data:
        settings.max_messages_per_day = data["max_messages_per_day"]
    if "min_days_between_messages" in data:
        settings.min_days_between_messages = data["min_days_between_messages"]
    if "sales_aggressiveness" in data:
        settings.sales_aggressiveness = data["sales_aggressiveness"]
    if "excluded_dates" in data:
        settings.excluded_dates = data["excluded_dates"]
    
    db.commit()
    
    return {"message": "Settings updated successfully"}