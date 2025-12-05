"""
HappySnack B2B Telegram Bot
Обновленная версия с WebApp, рассылками и скидками
"""
import asyncio
import logging
import os
import sys
import json
from datetime import datetime
from typing import Optional

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
    WebAppInfo
)
from sqlalchemy import create_engine, BigInteger, func
from sqlalchemy.orm import sessionmaker

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from database import Base, SessionLocal
from models.user import User, Client
from models.product import Product, Category
from models.order import Order, OrderItem
from models.bonus import BonusTransaction
from models.analytics import AnalyticsEvent, ClientMetrics

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
DATABASE_URL = os.getenv("DATABASE_URL")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-domain.com")
ANALYTICS_ENABLED = os.getenv("ANALYTICS_ENABLED", "true").lower() == "true"

# Инициализация бота
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация БД
engine = create_engine(DATABASE_URL)

# Модель торговых представителей
from sqlalchemy import Column, Integer, String, Boolean
from database import Base as DBBase

class SalesRepresentative(DBBase):
    __tablename__ = "sales_representatives"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    telegram_id = Column(BigInteger, unique=True, nullable=True)
    phone = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

# AI ассистент
try:
    from ai_agent import SalesAssistant
    sales_assistant = SalesAssistant()
    logger.info("✅ AI Assistant initialized")
except Exception as e:
    logger.warning(f"⚠️ AI Assistant not available: {e}")
    sales_assistant = None

# ============================================
# FSM STATES
# ============================================

class RegistrationStates(StatesGroup):
    waiting_for_company_name = State()
    waiting_for_bin_iin = State()
    waiting_for_address = State()
    waiting_for_phone = State()

class BroadcastStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_photo = State()
    confirmation = State()

# ============================================
# АНАЛИТИКА
# ============================================

def log_analytics_event(event_type: str, telegram_id: int, username: Optional[str] = None, metadata: dict = None):
    """Логирование события аналитики"""
    if not ANALYTICS_ENABLED:
        return
    
    db = SessionLocal()
    try:
        event = AnalyticsEvent(
            event_type=event_type,
            telegram_id=telegram_id,
            username=username,
            event_metadata=metadata or {}
        )
        db.add(event)
        db.commit()
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        db.rollback()
    finally:
        db.close()

# ============================================
# УТИЛИТЫ
# ============================================

def validate_bin(bin_iin: str) -> bool:
    """Валидация БИН/ИИН (12 цифр)"""
    return bin_iin.isdigit() and len(bin_iin) == 12

def validate_phone(phone: str) -> tuple[bool, str]:
    """Валидация и форматирование телефона"""
    cleaned = ''.join(filter(str.isdigit, phone))
    
    if cleaned.startswith('8') and len(cleaned) == 11:
        cleaned = '7' + cleaned[1:]
    
    if cleaned.startswith('7') and len(cleaned) == 11:
        return True, f"+{cleaned}"
    
    return False, phone

def calculate_first_order_discount(total: float) -> tuple[float, int]:
    """Расчет скидки на первый заказ"""
    if total >= 50000:
        return total * 0.20, 20
    elif total >= 25000:
        return total * 0.15, 15
    elif total >= 15000:
        return total * 0.10, 10
    return 0, 0

# ============================================
# КЛАВИАТУРЫ
# ============================================

def get_start_keyboard(is_registered: bool = False):
    """Главное меню"""
    if is_registered:
        keyboard = [
            [
                InlineKeyboardButton(
                    text="🛒 Открыть каталог",
                    web_app=WebAppInfo(url=WEBAPP_URL)
                )
            ],
            [
                InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
                InlineKeyboardButton(text="📋 Мои заказы", callback_data="my_orders")
            ],
            [
                InlineKeyboardButton(text="💎 Мои бонусы", callback_data="my_bonuses"),
                InlineKeyboardButton(text="📊 Статистика", callback_data="client_stats")
            ],
            [InlineKeyboardButton(text="📦 Что мы предлагаем", callback_data="products_info")],
            [InlineKeyboardButton(text="📞 Связаться с менеджером", callback_data="contact_manager")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton(text="✅ Хочу начать работать!", callback_data="start_registration")],
            [InlineKeyboardButton(text="📦 Что мы предлагаем", callback_data="products_info")],
            [InlineKeyboardButton(text="💰 Акции и специальные предложения", callback_data="promotions")],
            [InlineKeyboardButton(text="📞 Связаться с менеджером", callback_data="contact_manager")],
            [InlineKeyboardButton(text="🆘 Помощь", callback_data="help")]
        ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ============================================
# КОМАНДЫ
# ============================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Команда /start"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        
        # Логирование нового пользователя
        if not user:
            logger.info(f"🆕 NEW USER: {message.from_user.username or 'No username'} | ID: {message.from_user.id}")
            log_analytics_event("start", message.from_user.id, message.from_user.username)
        
        is_registered = bool(user and user.client and user.client.status in ["active", "pending"])
        
        welcome_text = (
            f"🍿 <b>Добро пожаловать в HappySnack!</b>\n\n"
            f"📱 <b>Ваш Telegram ID:</b> <code>{message.from_user.id}</code>\n\n"
        )
        
        if is_registered:
            client = user.client
            welcome_text += (
                f"👤 <b>{client.company_name}</b>\n"
                f"💰 Бонусный баланс: <b>{client.bonus_balance:,.0f}₸</b>\n\n"
                f"Выберите действие:"
            )
        else:
            welcome_text += (
                f"Мы предлагаем качественные снеки и напитки для вашего бизнеса!\n\n"
                f"🎁 <b>Специальное предложение:</b>\n"
                f"При регистрации - <b>5,000₸ бонусов</b> на первую покупку!\n\n"
                f"Что вас интересует?"
            )
        
        await message.answer(
            welcome_text,
            parse_mode="HTML",
            reply_markup=get_start_keyboard(is_registered)
        )
        
    finally:
        db.close()

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Статистика для админов"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    if not ANALYTICS_ENABLED:
        await message.answer("📊 Аналитика отключена")
        return
    
    db = SessionLocal()
    try:
        today = datetime.utcnow().date()
        
        # События за сегодня
        starts_today = db.query(AnalyticsEvent).filter(
            AnalyticsEvent.event_type == "start",
            func.date(AnalyticsEvent.created_at) == today
        ).count()
        
        regs_started_today = db.query(AnalyticsEvent).filter(
            AnalyticsEvent.event_type == "registration_started",
            func.date(AnalyticsEvent.created_at) == today
        ).count()
        
        regs_completed_today = db.query(AnalyticsEvent).filter(
            AnalyticsEvent.event_type == "registration_completed",
            func.date(AnalyticsEvent.created_at) == today
        ).count()
        
        approved_today = db.query(AnalyticsEvent).filter(
            AnalyticsEvent.event_type == "client_approved",
            func.date(AnalyticsEvent.created_at) == today
        ).count()
        
        # Всего клиентов
        total_clients = db.query(Client).count()
        active_clients = db.query(Client).filter(Client.status == "active").count()
        pending_clients = db.query(Client).filter(Client.status == "pending").count()
        
        stats_text = (
            f"📊 <b>Статистика системы</b>\n\n"
            f"🗓️ <b>Сегодня ({today.strftime('%d.%m.%Y')}):</b>\n"
            f"• Новых пользователей: {starts_today}\n"
            f"• Начато регистраций: {regs_started_today}\n"
            f"• Завершено регистраций: {regs_completed_today}\n"
            f"• Одобрено клиентов: {approved_today}\n\n"
            f"👥 <b>Клиенты:</b>\n"
            f"• Всего: {total_clients}\n"
            f"• Активных: {active_clients}\n"
            f"• На модерации: {pending_clients}\n"
        )
        
        await message.answer(stats_text, parse_mode="HTML")
        
    finally:
        db.close()

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message, state: FSMContext):
    """Массовая рассылка"""
    if message.from_user.id not in ADMIN_IDS:
        return
    
    await state.set_state(BroadcastStates.waiting_for_message)
    await message.answer(
        "📢 <b>Массовая рассылка</b>\n\n"
        "Напишите текст сообщения которое хотите отправить всем активным клиентам:",
        parse_mode="HTML"
    )

@dp.message(BroadcastStates.waiting_for_message)
async def broadcast_get_message(message: types.Message, state: FSMContext):
    """Получение текста рассылки"""
    await state.update_data(broadcast_text=message.text)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data="broadcast_add_photo"),
            InlineKeyboardButton(text="❌ Нет", callback_data="broadcast_no_photo")
        ]
    ])
    
    await message.answer("Добавить фото к сообщению?", reply_markup=keyboard)

@dp.callback_query(F.data == "broadcast_add_photo")
async def broadcast_add_photo(callback: types.CallbackQuery, state: FSMContext):
    """Запрос фото"""
    await state.set_state(BroadcastStates.waiting_for_photo)
    await callback.message.edit_text("Отправьте фото:")
    await callback.answer()

@dp.callback_query(F.data == "broadcast_no_photo")
async def broadcast_no_photo(callback: types.CallbackQuery, state: FSMContext):
    """Рассылка без фото"""
    await show_broadcast_confirmation(callback.message, state)
    await callback.answer()

@dp.message(BroadcastStates.waiting_for_photo, F.photo)
async def broadcast_get_photo(message: types.Message, state: FSMContext):
    """Получение фото"""
    photo = message.photo[-1]
    await state.update_data(broadcast_photo=photo.file_id)
    await show_broadcast_confirmation(message, state)

async def show_broadcast_confirmation(message: types.Message, state: FSMContext):
    """Подтверждение рассылки"""
    data = await state.get_data()
    broadcast_text = data.get('broadcast_text')
    
    db = SessionLocal()
    active_clients = db.query(Client).filter(Client.status == "active").count()
    db.close()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Отправить всем", callback_data="broadcast_send_all"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")
        ]
    ])
    
    await message.answer(
        f"📢 <b>Подтверждение рассылки</b>\n\n"
        f"Получателей: <b>{active_clients}</b> активных клиентов\n\n"
        f"Текст:\n{broadcast_text}\n\n"
        f"Отправить?",
        parse_mode="HTML",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "broadcast_send_all")
async def broadcast_send(callback: types.CallbackQuery, state: FSMContext):
    """Отправка рассылки"""
    data = await state.get_data()
    broadcast_text = data.get('broadcast_text')
    broadcast_photo = data.get('broadcast_photo')
    
    await callback.message.edit_text("⏳ Отправка рассылки...")
    
    db = SessionLocal()
    try:
        clients = db.query(Client).filter(Client.status == "active").all()
        
        success_count = 0
        fail_count = 0
        
        for client in clients:
            try:
                user = db.query(User).filter(User.id == client.user_id).first()
                if not user:
                    continue
                
                if broadcast_photo:
                    await bot.send_photo(
                        user.telegram_id,
                        photo=broadcast_photo,
                        caption=broadcast_text,
                        parse_mode="HTML"
                    )
                else:
                    await bot.send_message(
                        user.telegram_id,
                        broadcast_text,
                        parse_mode="HTML"
                    )
                
                success_count += 1
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                fail_count += 1
        
        await callback.message.edit_text(
            f"✅ <b>Рассылка завершена!</b>\n\n"
            f"Успешно: {success_count}\n"
            f"Ошибок: {fail_count}",
            parse_mode="HTML"
        )
        
    finally:
        db.close()
        await state.clear()
    
    await callback.answer()

@dp.callback_query(F.data == "broadcast_cancel")
async def broadcast_cancel(callback: types.CallbackQuery, state: FSMContext):
    """Отмена рассылки"""
    await state.clear()
    await callback.message.edit_text("❌ Рассылка отменена")
    await callback.answer()

# ============================================
# РЕГИСТРАЦИЯ
# ============================================

@dp.callback_query(F.data == "start_registration")
async def callback_start_registration(callback: types.CallbackQuery, state: FSMContext):
    """Начало регистрации"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        
        if user and user.client:
            await callback.answer("Вы уже зарегистрированы!", show_alert=True)
            return
        
        log_analytics_event("registration_started", callback.from_user.id, callback.from_user.username)
        
        await state.set_state(RegistrationStates.waiting_for_company_name)
        await callback.message.edit_text(
            "📝 <b>Регистрация (Шаг 1 из 4)</b>\n\n"
            "Введите название вашей компании:",
            parse_mode="HTML"
        )
        
    finally:
        db.close()
    
    await callback.answer()

@dp.message(RegistrationStates.waiting_for_company_name)
async def process_company_name(message: types.Message, state: FSMContext):
    """Получение названия компании"""
    await state.update_data(company_name=message.text)
    await state.set_state(RegistrationStates.waiting_for_bin_iin)
    
    await message.answer(
        "📝 <b>Регистрация (Шаг 2 из 4)</b>\n\n"
        "Введите БИН вашей компании (12 цифр):",
        parse_mode="HTML"
    )

@dp.message(RegistrationStates.waiting_for_bin_iin)
async def process_bin(message: types.Message, state: FSMContext):
    """Получение БИН"""
    bin_iin = message.text.strip()
    
    if not validate_bin(bin_iin):
        await message.answer(
            "❌ БИН должен содержать ровно 12 цифр.\n\n"
            "Попробуйте еще раз:"
        )
        return
    
    await state.update_data(bin_iin=bin_iin)
    await state.set_state(RegistrationStates.waiting_for_address)
    
    await message.answer(
        "📝 <b>Регистрация (Шаг 3 из 4)</b>\n\n"
        "Введите адрес вашей компании:",
        parse_mode="HTML"
    )

@dp.message(RegistrationStates.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    """Получение адреса"""
    await state.update_data(address=message.text)
    await state.set_state(RegistrationStates.waiting_for_phone)
    
    await message.answer(
        "📝 <b>Регистрация (Шаг 4 из 4)</b>\n\n"
        "Введите контактный телефон:\n"
        "Например: +7 777 123 45 67",
        parse_mode="HTML"
    )

@dp.message(RegistrationStates.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    """Получение телефона и завершение регистрации"""
    is_valid, formatted_phone = validate_phone(message.text)
    
    if not is_valid:
        await message.answer(
            "❌ Неверный формат телефона.\n\n"
            "Используйте формат: +7 XXX XXX XX XX\n"
            "Попробуйте еще раз:"
        )
        return
    
    data = await state.get_data()
    
    db = SessionLocal()
    try:
        # Создаем пользователя если не существует
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        if not user:
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                role="client",
                is_active=True
            )
            db.add(user)
            db.flush()
        
        # Создаем клиента
        client = Client(
            user_id=user.id,
            company_name=data['company_name'],
            bin_iin=data['bin_iin'],
            address=data['address'],
            contact_phone=formatted_phone,
            status="pending",
            bonus_balance=0.0,
            first_order_discount_used=False
        )
        db.add(client)
        db.commit()
        
        log_analytics_event(
            "registration_completed",
            message.from_user.id,
            message.from_user.username,
            {"company_name": data['company_name']}
        )
        
        # Уведомление клиенту
        await message.answer(
            "✅ <b>Регистрация завершена!</b>\n\n"
            "Ваша заявка отправлена на модерацию.\n"
            "Мы свяжемся с вами в ближайшее время!\n\n"
            "🎁 После одобрения вы получите <b>5,000₸ бонусов</b> на первую покупку!",
            parse_mode="HTML"
        )
        
        # Уведомление админам
        for admin_id in ADMIN_IDS:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="✅ Одобрить и начислить 5,000₸",
                    callback_data=f"approve_client_{client.id}"
                )],
                [InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"reject_client_{client.id}"
                )]
            ])
            
            await bot.send_message(
                admin_id,
                f"🆕 <b>Новая заявка на регистрацию</b>\n\n"
                f"👤 Имя: {message.from_user.first_name or 'Не указано'}\n"
                f"🏢 Компания: <b>{client.company_name}</b>\n"
                f"📋 БИН: {client.bin_iin}\n"
                f"📍 Адрес: {client.address}\n"
                f"📞 Телефон: {formatted_phone}\n\n"
                f"💬 Username: @{message.from_user.username or 'нет'}\n"
                f"🆔 Telegram ID: <code>{message.from_user.id}</code>",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        db.rollback()
        await message.answer(
            "❌ Произошла ошибка при регистрации.\n\n"
            "Попробуйте позже или свяжитесь с нами:\n"
            "📞 +7 XXX XXX XX XX"
        )
    finally:
        db.close()
        await state.clear()

@dp.callback_query(F.data.startswith("approve_client_"))
async def callback_approve_client(callback: types.CallbackQuery):
    """Одобрение клиента"""
    client_id = int(callback.data.split("_")[2])
    
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            await callback.answer("Клиент не найден", show_alert=True)
            return
        
        # Одобряем
        client.status = "active"
        client.approved_at = datetime.utcnow()
        client.bonus_balance = 5000.0
        
        # Создаем транзакцию бонусов
        bonus_transaction = BonusTransaction(
            client_id=client.id,
            amount=5000.0,
            type="earn",
            description="Welcome бонус при регистрации"
        )
        db.add(bonus_transaction)
        
        db.commit()
        
        log_analytics_event("client_approved", client.user.telegram_id, client.user.username)
        
        # Уведомление клиенту
        await bot.send_message(
            client.user.telegram_id,
            "🎉 <b>Отличные новости!</b>\n\n"
            "✅ Ваша регистрация одобрена!\n\n"
            "🎁 На ваш счет начислено <b>5,000₸</b> приветственных бонусов!\n\n"
            "Используйте их при первой покупке. Бонусы покрывают до 100% стоимости заказа.\n\n"
            "🛒 Откройте каталог и сделайте первый заказ!",
            parse_mode="HTML",
            reply_markup=get_start_keyboard(True)
        )
        
        await callback.message.edit_text(
            f"✅ Клиент <b>{client.company_name}</b> одобрен!\n"
            f"Начислено 5,000₸ бонусов.",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Approve error: {e}")
        db.rollback()
        await callback.answer("Ошибка одобрения", show_alert=True)
    finally:
        db.close()
    
    await callback.answer()

# ============================================
# ОБРАБОТКА WEBAPP
# ============================================

@dp.message(F.web_app_data)
async def handle_webapp_data(message: types.Message):
    """Обработка данных из WebApp"""
    try:
        data = json.loads(message.web_app_data.data)
        
        if data.get('action') == 'checkout':
            await process_webapp_order(message, data)
            
    except Exception as e:
        logger.error(f"WebApp data error: {e}")
        await message.answer("❌ Ошибка обработки заказа")

async def process_webapp_order(message: types.Message, order_data):
    """Обработка заказа из webapp"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        if not user or not user.client:
            await message.answer("❌ Клиент не найден")
            return
        
        client = user.client
        cart = order_data.get('cart', {})
        total = order_data.get('total', 0)
        
        # Применяем скидку на первый заказ
        discount = 0
        discount_percent = 0
        
        if not client.first_order_discount_used:
            discount, discount_percent = calculate_first_order_discount(total)
            if discount > 0:
                client.first_order_discount_used = True
        
        final_total = total - discount
        
        # Создаем заказ
        order = Order(
            client_id=client.id,
            status="pending",
            total_amount=final_total,
            discount_amount=discount,
            created_at=datetime.utcnow()
        )
        db.add(order)
        db.flush()
        
        # Добавляем товары
        items_text = ""
        for product_id, quantity in cart.items():
            product = db.query(Product).filter(Product.id == int(product_id)).first()
            if product:
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=quantity,
                    price=product.price
                )
                db.add(order_item)
                product.stock -= quantity
                items_text += f"• {product.name} × {quantity}\n"
        
        db.commit()
        
        # Сообщение клиенту
        discount_text = f"\n💎 Скидка -{discount_percent}%: -{discount:,.0f}₸" if discount > 0 else ""
        
        await message.answer(
            f"✅ <b>Заказ #{order.id} оформлен!</b>\n\n"
            f"📦 Товары:\n{items_text}\n"
            f"💰 Сумма: {total:,.0f}₸"
            f"{discount_text}\n"
            f"💵 <b>К оплате: {final_total:,.0f}₸</b>\n\n"
            f"⏰ Ожидайте звонка менеджера для подтверждения!",
            parse_mode="HTML"
        )
        
        # Уведомление торговому
        await notify_sales_rep_about_order(order, client, items_text, final_total)
        
    except Exception as e:
        logger.error(f"Order processing error: {e}")
        db.rollback()
        await message.answer("❌ Ошибка создания заказа")
    finally:
        db.close()

async def notify_sales_rep_about_order(order, client, items_text, total):
    """Уведомление торговому представителю"""
    db = SessionLocal()
    try:
        sales_rep = None
        if client.sales_rep_id:
            sales_rep = db.query(SalesRepresentative).filter(
                SalesRepresentative.id == client.sales_rep_id,
                SalesRepresentative.is_active == True
            ).first()
        
        message_text = (
            f"🆕 <b>НОВЫЙ ЗАКАЗ #{order.id}</b>\n\n"
            f"👤 Клиент: <b>{client.company_name}</b>\n"
            f"📞 Телефон: {client.contact_phone}\n\n"
            f"📦 Товары:\n{items_text}\n"
            f"💵 Сумма: <b>{total:,.0f}₸</b>\n\n"
            f"⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_order_{order.id}"),
                InlineKeyboardButton(text="📞 Позвонить", url=f"tel:{client.contact_phone}")
            ],
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_order_{order.id}")]
        ])
        
        # Уведомление торговому
        if sales_rep and sales_rep.telegram_id:
            await bot.send_message(
                sales_rep.telegram_id,
                message_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        
        # Уведомление админу
        for admin_id in ADMIN_IDS:
            await bot.send_message(
                admin_id,
                f"🆕 <b>НОВЫЙ ЗАКАЗ #{order.id}</b>\n\n"
                f"👤 {client.company_name}\n"
                f"💵 {total:,.0f}₸\n"
                f"👨‍💼 ТП: {sales_rep.name if sales_rep else 'Не назначен'}",
                parse_mode="HTML"
            )
                
    except Exception as e:
        logger.error(f"Notify sales rep error: {e}")
    finally:
        db.close()

# ============================================
# ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ (AI)
# ============================================

@dp.message(F.text, StateFilter(None))
async def handle_text_message(message: types.Message, state: FSMContext):
    """Обработка текстовых сообщений"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        is_registered = bool(user and user.client and user.client.status in ["active", "pending"])
        
        # Проверка триггерных слов для незарегистрированных
        if not is_registered:
            trigger_words = ["да", "давай", "хочу", "согласен", "начнем", "начнём", "ок", "okay", "поехали", "погнали"]
            message_lower = message.text.lower().strip()
            
            if any(word == message_lower or message_lower.startswith(word + " ") for word in trigger_words):
                # Запускаем регистрацию
                log_analytics_event("registration_started", message.from_user.id, message.from_user.username)
                await state.set_state(RegistrationStates.waiting_for_company_name)
                await message.answer(
                    "📝 <b>Регистрация (Шаг 1 из 4)</b>\n\n"
                    "Введите название вашей компании:",
                    parse_mode="HTML"
                )
                return
        
        # AI ассистент
        if sales_assistant:
            try:
                response = await sales_assistant.process_message(
                    message.text,
                    message.from_user.id,
                    is_registered
                )
                
                # Добавляем кнопку регистрации для незарегистрированных
                if not is_registered:
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text="✅ Зарегистрироваться",
                            callback_data="start_registration"
                        )]
                    ])
                    await message.answer(response, parse_mode="HTML", reply_markup=keyboard)
                    
                    log_analytics_event(
                        "pre_registration_message",
                        message.from_user.id,
                        message.from_user.username
                    )
                else:
                    await message.answer(response, parse_mode="HTML")
                    
            except Exception as e:
                logger.error(f"AI error: {e}")
                await message.answer(
                    "Извините, возникла ошибка. Попробуйте еще раз или свяжитесь с менеджером.",
                    reply_markup=get_start_keyboard(is_registered)
                )
        else:
            await message.answer(
                "Используйте кнопки меню для навигации 👇",
                reply_markup=get_start_keyboard(is_registered)
            )
            
    finally:
        db.close()

# ============================================
# CALLBACKS
# ============================================

@dp.callback_query(F.data == "products_info")
async def callback_products_info(callback: types.CallbackQuery):
    """Информация о продуктах"""
    products_text = (
        "📦 <b>Наш ассортимент</b>\n\n"
        
        "🍿 <b>Попкорн HAPPY CORN (эксклюзив!)</b>\n"
        "7 вкусов: сырный, карамельный, BBQ, острый, сладкий, соленый, классический\n"
        "5 видов фасовки: от 100г до коробок по 12шт\n"
        "💎 Маржа до 60% - самая высокая!\n\n"
        
        "🥔 <b>Чипсы:</b>\n"
        "• Papa Nachos (сырные, острые, BBQ, классические)\n"
        "• Real Chips (сметана-лук, краб, соль)\n"
        "• Gramzz (паприка, сметана)\n"
        "• Happy Crisp (сыр, BBQ)\n\n"
        
        "🍫 <b>Батончики «Здоровый перекус»:</b>\n"
        "Протеиновые: шоколад, ваниль, карамель\n"
        "Орехово-фруктовые\n\n"
        
        "🍞 <b>Хлебцы:</b>\n"
        "Ржаные, гречневые, рисовые, мультизлаковые\n\n"
        
        "🥤 <b>Напитки:</b>\n"
        "• Живой квас (ржаной, овсяной)\n"
        "• NITRO Energy (3 вкуса)\n"
        "• NITRO Fresh (лимон, апельсин)\n"
        "• Вода витаминизированная\n"
        "• Salam TEA (черный, зеленый)\n\n"
        
        "🥐 <b>Свежая выпечка:</b>\n"
        "Круассаны, профитроли, трубочки с кремом, печенье\n\n"
        
        "💡 Для просмотра полного каталога с ценами - зарегистрируйтесь!"
    )
    
    await callback.message.edit_text(
        products_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👈 Назад", callback_data="back_to_start")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "profile")
async def callback_profile(callback: types.CallbackQuery):
    """Профиль клиента"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        client = db.query(Client).filter(Client.user_id == user.id).first()
        if not client:
            await callback.answer("❌ Клиент не найден", show_alert=True)
            return
        
        text = (
            f"👤 <b>Ваш профиль</b>\n\n"
            f"🏢 Компания: <b>{client.company_name}</b>\n"
            f"📋 БИН: {client.bin_iin}\n"
            f"📍 Адрес: {client.address}\n"
            f"📞 Телефон: {client.contact_phone}\n\n"
            f"💰 <b>Финансы:</b>\n"
            f"• Бонусный баланс: <b>{client.bonus_balance:,.0f}₸</b>\n"
            f"• Кредитный лимит: {client.credit_limit:,.0f}₸\n"
            f"• Текущий долг: {client.debt:,.0f}₸\n"
            f"• Доступно: <b>{(client.credit_limit - client.debt):,.0f}₸</b>\n\n"
            f"💎 <b>Условия:</b>\n"
            f"• Скидка: {client.discount_percent}%\n"
            f"• Отсрочка: {client.payment_delay_days} дней\n\n"
            f"📊 Статус: <b>{client.status}</b>"
        )
        
        await callback.message.edit_text(text, parse_mode="HTML")
    finally:
        db.close()
    
    await callback.answer()

@dp.callback_query(F.data == "contact_manager")
async def callback_contact_manager(callback: types.CallbackQuery):
    """Связаться с менеджером"""
    await callback.message.edit_text(
        "💬 <b>Связь с менеджером</b>\n\n"
        "📞 Телефон: +7 XXX XXX XX XX\n"
        "💬 Telegram: @happysnack_manager\n"
        "📧 Email: info@happysnack.kz\n\n"
        "⏰ Режим работы:\n"
        "Пн-Пт: 9:00-18:00\n"
        "Сб: 9:00-15:00\n"
        "Вс: выходной",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_start")
async def callback_back(callback: types.CallbackQuery):
    """Назад в главное меню"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        is_registered = bool(user and user.client and user.client.status in ["active", "pending"])
        
        await callback.message.edit_text(
            "Выберите действие:",
            reply_markup=get_start_keyboard(is_registered)
        )
    finally:
        db.close()
    
    await callback.answer()

# ============================================
# ЗАПУСК БОТА
# ============================================

async def main():
    """Запуск бота"""
    logger.info("🚀 Starting HappySnack Bot...")
    logger.info(f"🤖 AI Assistant: {'✅ Enabled' if sales_assistant else '❌ Disabled'}")
    logger.info(f"📊 Analytics: {'✅ Enabled' if ANALYTICS_ENABLED else '❌ Disabled'}")
    logger.info(f"🌐 WebApp URL: {WEBAPP_URL}")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
        raise
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())