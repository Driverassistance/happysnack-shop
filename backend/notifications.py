"""
Сервис уведомлений через Telegram
"""
import httpx
import logging
from typing import List, Optional
from config import settings
from sqlalchemy.orm import Session
from models.user import User, Client
from models.order import Order

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Отправка уведомлений через Telegram Bot API"""
    
    def __init__(self):
        self.api_url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}"
    
    async def send_message(
        self, 
        chat_id: int, 
        text: str, 
        parse_mode: str = "HTML"
    ) -> bool:
        """Отправить сообщение"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": parse_mode
                    },
                    timeout=10.0
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send telegram message: {e}")
            return False
    
    async def notify_new_order(self, order: Order, db: Session):
        """Уведомление о новом заказе менеджеру"""
        try:
            client = db.query(Client).filter(Client.id == order.client_id).first()
            
            if not client or not order.manager_id:
                return False
            
            manager = db.query(User).filter(User.id == order.manager_id).first()
            
            if not manager:
                return False
            
            text = (
                f"🔔 <b>НОВЫЙ ЗАКАЗ!</b>\n\n"
                f"📦 Заказ: <b>{order.order_number}</b>\n"
                f"🏪 Клиент: <b>{client.company_name}</b>\n"
                f"💰 Сумма: <b>{order.final_total:,.0f}₸</b>\n"
                f"📅 Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                f"📝 Товаров: {len(order.items)} позиций\n\n"
                f"Используйте /order_{order.id} для управления"
            )
            
            return await self.send_message(manager.telegram_id, text)
            
        except Exception as e:
            logger.error(f"Error notifying new order: {e}")
            return False
    
    async def notify_order_status_changed(
        self, 
        order: Order, 
        new_status: str,
        db: Session
    ):
        """Уведомление клиента об изменении статуса заказа"""
        try:
            client = db.query(Client).filter(Client.id == order.client_id).first()
            
            if not client:
                return False
            
            user = db.query(User).filter(User.id == client.user_id).first()
            
            if not user:
                return False
            
            status_messages = {
                'confirmed': '✅ Ваш заказ подтвержден!\n\nМы начали сборку заказа.',
                'preparing': '📦 Ваш заказ собирается!\n\nСкоро отправим в доставку.',
                'delivering': '🚚 Ваш заказ в пути!\n\nСкоро доставим.',
                'delivered': f'✅ Ваш заказ доставлен!\n\n🎁 Начислено бонусов: {order.bonus_used:,.0f}₸\n\nСпасибо за заказ! 🙏',
                'cancelled': '❌ Ваш заказ отменен.\n\nСвяжитесь с менеджером для уточнения.'
            }
            
            message = status_messages.get(
                new_status, 
                f'📊 Статус заказа изменен на: {new_status}'
            )
            
            text = (
                f"<b>Заказ {order.order_number}</b>\n\n"
                f"{message}"
            )
            
            return await self.send_message(user.telegram_id, text)
            
        except Exception as e:
            logger.error(f"Error notifying status change: {e}")
            return False
    
    async def notify_new_client(self, client: Client, db: Session):
        """Уведомление админов о новом клиенте на модерации"""
        try:
            # Получаем всех админов
            admins = db.query(User).filter(User.role == "admin").all()
            
            user = db.query(User).filter(User.id == client.user_id).first()
            
            text = (
                f"👤 <b>НОВАЯ РЕГИСТРАЦИЯ!</b>\n\n"
                f"🏪 Компания: <b>{client.company_name}</b>\n"
                f"🆔 БИН: {client.bin_iin or 'не указан'}\n"
                f"📍 Адрес: {client.address or 'не указан'}\n"
                f"👤 Telegram: @{user.username if user.username else 'нет username'}\n\n"
                f"Используйте /pending для модерации\n"
                f"или /approve_{client.id} для быстрого одобрения"
            )
            
            success_count = 0
            for admin in admins:
                if await self.send_message(admin.telegram_id, text):
                    success_count += 1
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error notifying new client: {e}")
            return False
    
    async def notify_low_stock(self, product_name: str, stock: int, db: Session):
        """Уведомление админов о низком остатке товара"""
        try:
            admins = db.query(User).filter(User.role == "admin").all()
            
            text = (
                f"⚠️ <b>НИЗКИЙ ОСТАТОК!</b>\n\n"
                f"📦 Товар: <b>{product_name}</b>\n"
                f"📊 Остаток: <b>{stock} шт</b>\n\n"
                f"Пополните склад!"
            )
            
            success_count = 0
            for admin in admins:
                if await self.send_message(admin.telegram_id, text):
                    success_count += 1
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error notifying low stock: {e}")
            return False
    
    async def notify_client_approved(self, client: Client, db: Session):
        """Уведомление клиента об одобрении регистрации"""
        try:
            user = db.query(User).filter(User.id == client.user_id).first()
            
            if not user:
                return False
            
            text = (
                f"✅ <b>Ваша регистрация одобрена!</b>\n\n"
                f"Теперь вы можете делать заказы.\n"
                f"Используйте /start для начала работы.\n\n"
                f"💰 Ваш бонусный баланс: {client.bonus_balance:,.0f}₸\n"
                f"💳 Кредитный лимит: {client.credit_limit:,.0f}₸\n"
                f"🎁 Скидка: {client.discount_percent}%"
            )
            
            return await self.send_message(user.telegram_id, text)
            
        except Exception as e:
            logger.error(f"Error notifying client approval: {e}")
            return False

# Создаем глобальный экземпляр
notifier = TelegramNotifier()