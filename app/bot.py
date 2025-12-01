"""
Telegram бот для HappySnack B2B Shop
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import settings
from database import SessionLocal
from models.user import User, Client
from models.order import Order
from datetime import datetime
from sqlalchemy import func
from ai_agent import sales_assistant
import json
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Состояние для AI-чата
class AIChat(StatesGroup):
    talking = State()

print(f"🤖 Sales Assistant initialized: {sales_assistant is not None}")
if sales_assistant:
    print(f"✅ Claude API Key: {settings.CLAUDE_API_KEY[:20]}...")
else:
    print("❌ Sales Assistant is None!")
# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()
ai_conversations = {}
# ============================================
# КОМАНДЫ
# ============================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """
    Команда /start - приветствие и главное меню
    """
    db = SessionLocal()
    
    user = db.query(User).filter(
        User.telegram_id == message.from_user.id
    ).first()
    
    if not user:
        # Новый пользователь
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="ℹ️ О компании", callback_data="about")],
            [InlineKeyboardButton(text="📞 Контакты", callback_data="contacts")]
        ])
        
        await message.answer(
            "👋 Добро пожаловать в <b>HappySnack B2B Shop</b>!\n\n"
            "🏪 Мы - дистрибьютор качественных снеков и напитков в Казахстане.\n\n"
            "📦 В нашем ассортименте:\n"
            "• HAPPY CORN попкорн\n"
            "• Чипсы известных брендов\n"
            "• Снеки и сухарики\n"
            "• Напитки\n"
            "• Выпечка\n\n"
            "🚀 <b>Интернет-магазин скоро откроется!</b>\n\n"
            "А пока свяжитесь с нами для оформления заказа 👇",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    else:
        client = db.query(Client).filter(Client.user_id == user.id).first()
        
        if user.role == "client":
            if client.status == "pending":
                await message.answer(
                    "⏳ Ваша регистрация на модерации.\n\n"
                    "Мы свяжемся с вами в ближайшее время!"
                )
            elif client.status == "active":
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="📦 Мои заказы", callback_data="my_orders"),
                        InlineKeyboardButton(text="👤 Профиль", callback_data="profile")
                    ],
                    [InlineKeyboardButton(text="💬 Связаться с менеджером", callback_data="contact_manager")]
                ])
                
                await message.answer(
                    f"👋 С возвращением, <b>{client.company_name}</b>!\n\n"
                    f"💰 Ваш бонусный баланс: <b>{client.bonus_balance:.0f}₸</b>\n"
                    f"💳 Доступный кредит: <b>{(client.credit_limit - client.debt):.0f}₸</b>\n\n"
                    f"🚀 <b>Интернет-магазин скоро откроется!</b>\n\n"
                    "Используйте команды:\n"
                    "/orders - Мои заказы\n"
                    "/profile - Мой профиль",
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            else:
                await message.answer(
                    "🚫 Ваш аккаунт заблокирован.\n\n"
                    "Свяжитесь с менеджером для уточнения."
                )
        elif user.role in ["admin", "manager"]:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👔 Админ-панель", callback_data="open_admin_panel")],
                [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
                [
                    InlineKeyboardButton(text="📦 Заказы", callback_data="admin_orders"),
                    InlineKeyboardButton(text="👥 Клиенты", callback_data="admin_clients")
                ]
            ])
            
            await message.answer(
                f"👋 Привет, {'администратор' if user.role == 'admin' else 'менеджер'}!\n\n"
                "Выберите действие:",
                parse_mode="HTML",
                reply_markup=keyboard
            )
    
    db.close()
# ============================================
# АДМИН КОМАНДЫ
# ============================================

def is_admin_or_manager(telegram_id: int) -> bool:
    """Проверка что пользователь админ или менеджер"""
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    db.close()
    return user and user.role in ["admin", "manager"]

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Админ-панель"""
    if not is_admin_or_manager(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="📦 Заказы", callback_data="admin_orders")
        ],
        [
            InlineKeyboardButton(text="👥 Клиенты", callback_data="admin_clients"),
            InlineKeyboardButton(text="📦 Товары", callback_data="admin_products")
        ],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
    ])
    
    await message.answer(
        "👔 <b>Админ-панель</b>\n\n"
        "Выберите раздел:\n\n"
        "<i>💡 Для выхода нажмите «Главное меню» или отправьте /start</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
@dp.message(Command("aistart"))
async def cmd_ai_start_scheduler(message: types.Message):
    """
    Запустить автоматические проактивные сообщения
    """
    if not is_admin_or_manager(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return
    
    from scheduler import proactive_messenger
    
    try:
        proactive_messenger.start()
        await message.answer(
            "✅ <b>AI-агент запущен!</b>\n\n"
            "📅 Расписание: каждый день в 10:00\n"
            "🤖 Агент будет автоматически:\n"
            "• Анализировать клиентов\n"
            "• Находить кому писать\n"
            "• Отправлять персональные сообщения\n\n"
            "Для тестового запуска используй /aitest",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка запуска: {str(e)}")

@dp.message(Command("aistop"))
async def cmd_ai_stop_scheduler(message: types.Message):
    """
    Остановить автоматические сообщения
    """
    if not is_admin_or_manager(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return
    
    from scheduler import proactive_messenger
    
    try:
        proactive_messenger.stop()
        await message.answer(
            "🛑 <b>AI-агент остановлен</b>\n\n"
            "Автоматические сообщения отключены.",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка остановки: {str(e)}")

@dp.message(Command("aitest"))
async def cmd_ai_test_run(message: types.Message):
    """
    Тестовый запуск AI-агента (сейчас)
    """
    if not is_admin_or_manager(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return
    
    await message.answer(
        "🧪 <b>Запускаю тестовый анализ...</b>\n\n"
        "Агент сейчас проанализирует всех клиентов и отправит сообщения.\n"
        "Это может занять 1-2 минуты...",
        parse_mode="HTML"
    )
    
    from scheduler import proactive_messenger
    
    try:
        await proactive_messenger.test_run()
        await message.answer(
            "✅ <b>Тест завершен!</b>\n\n"
            "Проверь сообщения клиентам.",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error in AI test: {e}")
        await message.answer(f"❌ Ошибка: {str(e)}")

@dp.message(Command("aistatus"))
async def cmd_ai_status(message: types.Message):
    """
    Статус AI-агента
    """
    if not is_admin_or_manager(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return
    
    from scheduler import proactive_messenger
    
    status = "🟢 Работает" if proactive_messenger.is_running else "🔴 Остановлен"
    
    await message.answer(
        f"📊 <b>Статус AI-агента</b>\n\n"
        f"Статус: {status}\n"
        f"Расписание: Ежедневно в 10:00\n\n"
        f"<b>Команды:</b>\n"
        f"/aistart - Запустить\n"
        f"/aistop - Остановить\n"
        f"/aitest - Тестовый запуск сейчас\n"
        f"/aianalyze - Показать кому писать",
        parse_mode="HTML"
    )
@dp.message(Command("pending"))
async def cmd_pending(message: types.Message):
    """Список клиентов на модерации"""
    if not is_admin_or_manager(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return
    
    db = SessionLocal()
    
    pending_clients = db.query(Client).filter(
        Client.status == "pending"
    ).order_by(Client.created_at.desc()).limit(10).all()
    
    if not pending_clients:
        await message.answer("✅ Нет клиентов на модерации")
        db.close()
        return
    
    text = "⏳ <b>Клиенты на модерации:</b>\n\n"
    
    for client in pending_clients:
        user = db.query(User).filter(User.id == client.user_id).first()
        text += (
            f"🏪 <b>{client.company_name}</b>\n"
            f"   ID: {client.id}\n"
            f"   БИН: {client.bin_iin or 'не указан'}\n"
            f"   Адрес: {client.address or 'не указан'}\n"
            f"   Telegram: @{user.username or 'нет username'}\n"
            f"   Дата: {client.created_at.strftime('%d.%m.%Y')}\n"
            f"   /approve_{client.id} или /reject_{client.id}\n\n"
        )
    
    await message.answer(text, parse_mode="HTML")
    db.close()

@dp.message(Command("neworders"))
async def cmd_new_orders(message: types.Message):
    """Новые заказы"""
    if not is_admin_or_manager(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return
    
    db = SessionLocal()
    
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
    
    query = db.query(Order).filter(Order.status == "new")
    
    # Менеджер видит только свои
    if user.role == "manager":
        query = query.filter(Order.manager_id == user.id)
    
    orders = query.order_by(Order.created_at.desc()).limit(10).all()
    
    if not orders:
        await message.answer("✅ Нет новых заказов")
        db.close()
        return
    
    text = "🆕 <b>Новые заказы:</b>\n\n"
    
    for order in orders:
        client = db.query(Client).filter(Client.id == order.client_id).first()
        text += (
            f"📦 <b>Заказ {order.order_number}</b>\n"
            f"   ID: {order.id}\n"
            f"   Клиент: {client.company_name}\n"
            f"   Сумма: {order.final_total:.0f}₸\n"
            f"   Товаров: {len(order.items)} позиций\n"
            f"   Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"   /order_{order.id}\n\n"
        )
    
    await message.answer(text, parse_mode="HTML")
    db.close()
@dp.message(Command("myid"))
async def cmd_myid(message: types.Message):
    """Узнать свой ID"""
    await message.answer(f"Ваш Telegram ID: <code>{message.from_user.id}</code>", parse_mode="HTML")
@dp.message(lambda message: message.text and message.text.startswith("/approve_"))
async def cmd_approve_client(message: types.Message):
    """Одобрить клиента"""
    if not is_admin_or_manager(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return
    
    try:
        client_id = int(message.text.split("_")[1])
    except:
        await message.answer("❌ Неверный формат команды")
        return
    
    db = SessionLocal()
    
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        await message.answer("❌ Клиент не найден")
        db.close()
        return
    
    if client.status != "pending":
        await message.answer("❌ Клиент уже обработан")
        db.close()
        return
    
    # Одобряем
    client.status = "active"
    client.approved_at = datetime.utcnow()
    
    # Назначаем менеджера если это менеджер одобряет
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
    if user.role == "manager" and not client.manager_id:
        client.manager_id = user.id
    
    db.commit()
    
    # Уведомляем клиента
    from notifications import notifier
    try:
        await notifier.notify_client_approved(client, db)
    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        pass
    
    await message.answer(
        f"✅ Клиент <b>{client.company_name}</b> одобрен!",
        parse_mode="HTML"
    )
    
    db.close()

@dp.message(lambda message: message.text and message.text.startswith("/reject_"))
async def cmd_reject_client(message: types.Message):
    """Отклонить клиента"""
    if not is_admin_or_manager(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return
    
    try:
        client_id = int(message.text.split("_")[1])
    except:
        await message.answer("❌ Неверный формат команды")
        return
    
    db = SessionLocal()
    
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        await message.answer("❌ Клиент не найден")
        db.close()
        return
    
    client.status = "blocked"
    db.commit()
    
    await message.answer(
        f"❌ Клиент <b>{client.company_name}</b> отклонен",
        parse_mode="HTML"
    )
    
    db.close()

@dp.message(lambda message: message.text and message.text.startswith("/order_"))
async def cmd_order_details(message: types.Message):
    """Детали заказа"""
    if not is_admin_or_manager(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return
    
    try:
        order_id = int(message.text.split("_")[1])
    except:
        await message.answer("❌ Неверный формат команды")
        return
    
    db = SessionLocal()
    
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if not order:
        await message.answer("❌ Заказ не найден")
        db.close()
        return
    
    client = db.query(Client).filter(Client.id == order.client_id).first()
    
    text = (
        f"📦 <b>Заказ {order.order_number}</b>\n\n"
        f"🏪 Клиент: <b>{client.company_name}</b>\n"
        f"📍 Адрес: {order.delivery_address or client.address}\n"
        f"📅 Дата доставки: {order.delivery_date or 'не указана'}\n"
        f"⏰ Время: {order.delivery_time_slot or 'не указано'}\n\n"
        f"💰 Сумма: {order.total:.0f}₸\n"
        f"🎁 Бонусы списано: {order.bonus_used:.0f}₸\n"
        f"💵 Итого: <b>{order.final_total:.0f}₸</b>\n\n"
        f"📝 <b>Товары:</b>\n"
    )
    
    for item in order.items:
        text += f"   • {item.product_name} x{item.quantity} = {item.subtotal:.0f}₸\n"
    
    text += f"\n📊 Статус: <b>{order.status}</b>\n"
    
    if order.comment:
        text += f"\n💬 Комментарий: {order.comment}\n"
    
    # Кнопки действий
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_order_{order_id}"),
            InlineKeyboardButton(text="📦 Собирается", callback_data=f"prepare_order_{order_id}")
        ],
        [
            InlineKeyboardButton(text="🚚 В доставке", callback_data=f"deliver_order_{order_id}"),
            InlineKeyboardButton(text="✅ Доставлен", callback_data=f"complete_order_{order_id}")
        ],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_order_{order_id}")]
    ])
    
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    
    db.close()

# ============================================
# CALLBACK HANDLERS ДЛЯ АДМИНА
# ============================================

@dp.callback_query(lambda c: c.data.startswith("confirm_order_"))
async def callback_confirm_order(callback: types.CallbackQuery):
    """Подтвердить заказ"""
    if not is_admin_or_manager(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    order_id = int(callback.data.split("_")[2])
    
    db = SessionLocal()
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if order:
        order.status = "confirmed"
        order.updated_at = datetime.utcnow()
        
        # История
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        history = OrderHistory(
            order_id=order.id,
            status="confirmed",
            changed_by=user.id,
            comment="Заказ подтвержден менеджером"
        )
        db.add(history)
        db.commit()
        
        # Уведомляем клиента
        client = db.query(Client).filter(Client.id == order.client_id).first()
        client_user = db.query(User).filter(User.id == client.user_id).first()
        
        try:
            await bot.send_message(
                chat_id=client_user.telegram_id,
                text=(
                    f"✅ Ваш заказ <b>{order.order_number}</b> подтвержден!\n\n"
                    f"Мы начали сборку заказа."
                ),
                parse_mode="HTML"
            )
        except:
            pass
        
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ <b>Статус обновлен: confirmed</b>",
            parse_mode="HTML"
        )
        await callback.answer("✅ Заказ подтвержден")
    
    db.close()

@dp.callback_query(lambda c: c.data.startswith("prepare_order_"))
async def callback_prepare_order(callback: types.CallbackQuery):
    """Заказ собирается"""
    if not is_admin_or_manager(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    order_id = int(callback.data.split("_")[2])
    
    db = SessionLocal()
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if order:
        order.status = "preparing"
        order.updated_at = datetime.utcnow()
        db.commit()
        
        await callback.message.edit_text(
            callback.message.text + "\n\n📦 <b>Статус обновлен: preparing</b>",
            parse_mode="HTML"
        )
        await callback.answer("📦 Заказ собирается")
    
    db.close()

@dp.callback_query(lambda c: c.data.startswith("deliver_order_"))
async def callback_deliver_order(callback: types.CallbackQuery):
    """Заказ в доставке"""
    if not is_admin_or_manager(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    order_id = int(callback.data.split("_")[2])
    
    db = SessionLocal()
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if order:
        order.status = "delivering"
        order.updated_at = datetime.utcnow()
        db.commit()
        
        # Уведомляем клиента
        client = db.query(Client).filter(Client.id == order.client_id).first()
        client_user = db.query(User).filter(User.id == client.user_id).first()
        
        try:
            await bot.send_message(
                chat_id=client_user.telegram_id,
                text=(
                    f"🚚 Ваш заказ <b>{order.order_number}</b> в пути!\n\n"
                    f"Скоро доставим."
                ),
                parse_mode="HTML"
            )
        except:
            pass
        
        await callback.message.edit_text(
            callback.message.text + "\n\n🚚 <b>Статус обновлен: delivering</b>",
            parse_mode="HTML"
        )
        await callback.answer("🚚 Заказ в доставке")
    
    db.close()

@dp.callback_query(lambda c: c.data.startswith("complete_order_"))
async def callback_complete_order(callback: types.CallbackQuery):
    """Заказ доставлен"""
    if not is_admin_or_manager(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    order_id = int(callback.data.split("_")[2])
    
    db = SessionLocal()
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if order:
        from models.bonus import BonusTransaction
        from models.settings import SystemSetting
        from utils import calculate_bonus_amount
        from dateutil.relativedelta import relativedelta
        
        order.status = "delivered"
        order.delivered_at = datetime.utcnow()
        order.updated_at = datetime.utcnow()
        
        # Начисляем бонусы
        bonus_percent_setting = db.query(SystemSetting).filter(
            SystemSetting.key == "bonus_percent_default"
        ).first()
        
        bonus_expiry_setting = db.query(SystemSetting).filter(
            SystemSetting.key == "bonus_expiry_months"
        ).first()
        
        bonus_percent = float(bonus_percent_setting.value) if bonus_percent_setting else 2.0
        expiry_months = int(bonus_expiry_setting.value) if bonus_expiry_setting else 6
        
        bonus_amount = calculate_bonus_amount(order.total, bonus_percent)
        
        if bonus_amount > 0:
            client = db.query(Client).filter(Client.id == order.client_id).first()
            client.bonus_balance += bonus_amount
            
            expires_at = datetime.utcnow() + relativedelta(months=expiry_months)
            
            bonus_tx = BonusTransaction(
                client_id=client.id,
                amount=bonus_amount,
                type="earn",
                order_id=order.id,
                description=f"Начисление бонусов за заказ {order.order_number}",
                expires_at=expires_at
            )
            db.add(bonus_tx)
        
        db.commit()
        
        # Уведомляем клиента
        client = db.query(Client).filter(Client.id == order.client_id).first()
        client_user = db.query(User).filter(User.id == client.user_id).first()
        
        try:
            await bot.send_message(
                chat_id=client_user.telegram_id,
                text=(
                    f"✅ Заказ <b>{order.order_number}</b> доставлен!\n\n"
                    f"🎁 Начислено бонусов: <b>{bonus_amount:.0f}₸</b>\n"
                    f"💰 Ваш баланс: <b>{client.bonus_balance:.0f}₸</b>\n\n"
                    f"Спасибо за заказ! 🙏"
                ),
                parse_mode="HTML"
            )
        except:
            pass
        
        await callback.message.edit_text(
            callback.message.text + f"\n\n✅ <b>Статус: delivered</b>\n🎁 Начислено {bonus_amount:.0f}₸ бонусов",
            parse_mode="HTML"
        )
        await callback.answer("✅ Заказ доставлен, бонусы начислены")
    
    db.close()

@dp.callback_query(lambda c: c.data.startswith("cancel_order_"))
async def callback_cancel_order(callback: types.CallbackQuery):
    """Отменить заказ"""
    if not is_admin_or_manager(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    order_id = int(callback.data.split("_")[2])
    
    db = SessionLocal()
    order = db.query(Order).filter(Order.id == order_id).first()
    
    if order:
        order.status = "cancelled"
        order.updated_at = datetime.utcnow()
        
        # Возвращаем остатки
        for item in order.items:
            from models.product import Product
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                product.stock += item.quantity
        
        # Возвращаем бонусы если были списаны
        if order.bonus_used > 0:
            from models.bonus import BonusTransaction
            client = db.query(Client).filter(Client.id == order.client_id).first()
            client.bonus_balance += order.bonus_used
            
            bonus_tx = BonusTransaction(
                client_id=client.id,
                amount=order.bonus_used,
                type="earn",
                order_id=order.id,
                description=f"Возврат бонусов (отмена заказа {order.order_number})"
            )
            db.add(bonus_tx)
        
        # Уменьшаем долг
        client = db.query(Client).filter(Client.id == order.client_id).first()
        client.debt -= order.final_total
        
        db.commit()
        
        await callback.message.edit_text(
            callback.message.text + "\n\n❌ <b>Заказ отменен</b>",
            parse_mode="HTML"
        )
        await callback.answer("❌ Заказ отменен")
    
    db.close()
@dp.callback_query(F.data == "open_admin_panel")
@dp.callback_query(F.data == "open_admin_panel")
async def callback_open_admin_panel(callback: types.CallbackQuery):
    """Открыть админ-панель"""
    if not is_admin_or_manager(callback.from_user.id):
        await callback.answer("❌ У вас нет доступа к админ-панели", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
            InlineKeyboardButton(text="📦 Заказы", callback_data="admin_orders")
        ],
        [
            InlineKeyboardButton(text="👥 Клиенты", callback_data="admin_clients"),
            InlineKeyboardButton(text="📦 Товары", callback_data="admin_products")
        ],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
    ])
    
    await callback.message.answer(
        "👔 <b>Админ-панель</b>\n\n"
        "Выберите раздел:\n\n"
        "<i>💡 Для выхода нажмите «Главное меню» или отправьте /start</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    
    await callback.answer()
@dp.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: types.CallbackQuery):
    """Статистика"""
    if not is_admin_or_manager(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    db = SessionLocal()
    from datetime import timedelta
    
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Сегодня
    today_orders = db.query(Order).filter(
        func.date(Order.created_at) == today
    ).count()
    
    today_revenue = db.query(func.sum(Order.final_total)).filter(
        func.date(Order.created_at) == today
    ).scalar() or 0.0
    
    # Неделя
    week_orders = db.query(Order).filter(
        Order.created_at >= week_ago
    ).count()
    
    week_revenue = db.query(func.sum(Order.final_total)).filter(
        Order.created_at >= week_ago
    ).scalar() or 0.0
    
    # Месяц
    month_orders = db.query(Order).filter(
        Order.created_at >= month_ago
    ).count()
    
    month_revenue = db.query(func.sum(Order.final_total)).filter(
        Order.created_at >= month_ago
    ).scalar() or 0.0
    
    # Клиенты
    active_clients = db.query(Client).filter(Client.status == "active").count()
    pending_clients = db.query(Client).filter(Client.status == "pending").count()
    
    # Товары
    from models.product import Product
    low_stock = db.query(Product).filter(
        Product.is_active == True,
        Product.stock < 50
    ).count()
    
    text = (
        f"📊 <b>Статистика HappySnack</b>\n\n"
        f"<b>📅 Сегодня:</b>\n"
        f"   Заказов: {today_orders}\n"
        f"   Выручка: {today_revenue:,.0f}₸\n\n"
        f"<b>📅 За неделю:</b>\n"
        f"   Заказов: {week_orders}\n"
        f"   Выручка: {week_revenue:,.0f}₸\n\n"
        f"<b>📅 За месяц:</b>\n"
        f"   Заказов: {month_orders}\n"
        f"   Выручка: {month_revenue:,.0f}₸\n\n"
        f"<b>👥 Клиенты:</b>\n"
        f"   Активных: {active_clients}\n"
        f"   На модерации: {pending_clients}\n\n"
        f"<b>📦 Товары:</b>\n"
        f"   Низкий остаток: {low_stock}"
    )
    
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()
    
    db.close()
@dp.message(Command("orders"))
async def cmd_orders(message: types.Message):
    """Команда /orders - список заказов"""
    db = SessionLocal()
    
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
    
    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start")
        db.close()
        return
    
    if user.role == "client":
        client = db.query(Client).filter(Client.user_id == user.id).first()
        orders = db.query(Order).filter(
            Order.client_id == client.id
        ).order_by(Order.created_at.desc()).limit(5).all()
        
        if not orders:
            await message.answer("У вас пока нет заказов")
        else:
            text = "📦 <b>Ваши последние заказы:</b>\n\n"
            
            for order in orders:
                status_emoji = {
                    "new": "🆕",
                    "confirmed": "✅",
                    "preparing": "📦",
                    "delivering": "🚚",
                    "delivered": "✅",
                    "cancelled": "❌"
                }.get(order.status, "❓")
                
                text += (
                    f"{status_emoji} <b>Заказ {order.order_number}</b>\n"
                    f"   Сумма: {order.final_total:.0f}₸\n"
                    f"   Статус: {order.status}\n"
                    f"   Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                )
            
            await message.answer(text, parse_mode="HTML")
    
    db.close()

@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    """Команда /profile - профиль пользователя"""
    db = SessionLocal()
    
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
    
    if not user:
        await message.answer("❌ Вы не зарегистрированы. Используйте /start")
        db.close()
        return
    
    if user.role == "client":
        client = db.query(Client).filter(Client.user_id == user.id).first()
        
        manager_name = "Не назначен"
        if client.manager_id:
            manager = db.query(User).filter(User.id == client.manager_id).first()
            if manager:
                manager_name = manager.username or f"ID: {manager.telegram_id}"
        
        total_orders = db.query(Order).filter(Order.client_id == client.id).count()
        
        text = (
            f"👤 <b>Профиль</b>\n\n"
            f"🏪 Компания: <b>{client.company_name}</b>\n"
            f"📍 Адрес: {client.address or 'Не указан'}\n"
            f"🆔 БИН/ИИН: {client.bin_iin or 'Не указан'}\n\n"
            f"💰 Бонусы: <b>{client.bonus_balance:.0f}₸</b>\n"
            f"💳 Долг: <b>{client.debt:.0f}₸</b>\n"
            f"💳 Кредитный лимит: <b>{client.credit_limit:.0f}₸</b>\n"
            f"💵 Доступно: <b>{(client.credit_limit - client.debt):.0f}₸</b>\n\n"
            f"🎁 Скидка: <b>{client.discount_percent}%</b>\n"
            f"📅 Отсрочка платежа: <b>{client.payment_delay_days} дней</b>\n\n"
            f"👔 Ваш менеджер: {manager_name}\n"
            f"📦 Всего заказов: {total_orders}"
        )
        
        await message.answer(text, parse_mode="HTML")
    
    db.close()
@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    """Профиль клиента"""
    # ... весь существующий код ...
    db.close()
@dp.message(Command("ai"))
async def cmd_ai_chat(message: types.Message, state: FSMContext):
    """
    Общение с AI-помощником
    """
    db = SessionLocal()
    
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
    
    if not user:
        await message.answer("❌ Вы не зарегистрированы")
        db.close()
        return
    
    # Админы могут тестировать с любым клиентом
    if user.role in ["admin", "manager"]:
        client = db.query(Client).filter(Client.status == "active").first()
        if not client:
            await message.answer("❌ Нет активных клиентов для теста")
            db.close()
            return
    elif user.role == "client":
        client = db.query(Client).filter(Client.user_id == user.id).first()
        if not client or client.status != "active":
            await message.answer("❌ Ваш аккаунт неактивен")
            db.close()
            return
    else:
        await message.answer("❌ Неизвестная роль")
        db.close()
        return
    
    # Инициализируем диалог
    if message.from_user.id not in ai_conversations:
        ai_conversations[message.from_user.id] = []
    
    # Сохраняем клиента в state
    await state.update_data(client_id=client.id)
    await state.set_state(AIChat.talking)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Завершить диалог", callback_data="end_ai_chat")]
    ])
    
    await message.answer(
        "🤖 <b>AI-Помощник HappySnack</b>\n\n"
        "Привет! Я помогу тебе:\n"
        "• Выбрать товары\n"
        "• Оформить заказ\n"
        "• Ответить на вопросы\n"
        "• Дать рекомендации\n\n"
        "Просто напиши свой вопрос! 👇",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    
    db.close()

# Обработчик сообщений для AI-чата
@dp.message(AIChat.talking)
async def handle_ai_message(message: types.Message, state: FSMContext):
    """
    Обработка сообщений в режиме AI-чата
    """
    print(f"📝 Got AI message from {message.from_user.id}: {message.text}")
    
    if not sales_assistant:
        print("❌ Sales assistant is None")
        await message.answer("❌ AI-помощник временно недоступен")
        return
    
    print("✅ Sales assistant OK, processing...")
    
    db = SessionLocal()
    
    # Получаем client_id из state
    data = await state.get_data()
    client_id = data.get('client_id')
    
    if not client_id:
        print("❌ Client ID not in state")
        await message.answer("❌ Ошибка: клиент не найден. Начните заново с /ai")
        db.close()
        return
    
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        print(f"❌ Client not found: {client_id}")
        await message.answer("❌ Клиент не найден")
        db.close()
        return
    
    print(f"✅ Client found: {client.company_name}")
    
    # Показываем что бот печатает
    await message.bot.send_chat_action(message.chat.id, "typing")
    
    try:
        # Получаем историю диалога
        history = ai_conversations.get(message.from_user.id, [])
        
        print(f"📚 History length: {len(history)}")
        
        # Получаем ответ от AI
        print("🤖 Calling Claude API...")
        response = await sales_assistant.chat_with_client(
            client=client,
            user_message=message.text,
            conversation_history=history,
            db=db
        )
        
        print(f"✅ Got response: {response[:100]}...")
        
        # Сохраняем в историю
        history.append({"role": "user", "content": message.text})
        history.append({"role": "assistant", "content": response})
        
        # Ограничиваем историю последними 10 сообщениями
        if len(history) > 10:
            history = history[-10:]
        
        ai_conversations[message.from_user.id] = history
        
        # Отправляем ответ
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Завершить диалог", callback_data="end_ai_chat")]
        ])
        
        await message.answer(response, reply_markup=keyboard)
        from models.ai_log import AIConversation
        ai_conv = AIConversation(
            client_id=client.id,
            user_message=message.text,
            ai_response=response
        )
        db.add(ai_conv)
        db.commit()
    except Exception as e:
        logger.error(f"Error in AI chat: {e}")
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        await message.answer(
            "😅 Извини, что-то пошло не так. Попробуй еще раз или свяжись с менеджером."
        )
    
    db.close()

@dp.callback_query(F.data == "end_ai_chat")
async def callback_end_ai_chat(callback: types.CallbackQuery, state: FSMContext):
    """
    Завершить диалог с AI
    """
    if callback.from_user.id in ai_conversations:
        del ai_conversations[callback.from_user.id]
    
    await state.clear()
    
    await callback.message.answer(
        "✅ Диалог завершен!\n\n"
        "Для нового диалога используй /ai"
    )
    await callback.answer()
  
@dp.message(Command("aianalyze"))
async def cmd_ai_analyze(message: types.Message):
    """
    Проанализировать всех клиентов AI-агентом
    """
    if not is_admin_or_manager(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return
    
    if not sales_assistant:
        await message.answer("❌ AI-помощник не настроен")
        return
    
    await message.answer("🤖 Запускаю анализ клиентов...")
    
    db = SessionLocal()
    
    try:
        # Находим клиентов которым нужно написать
        clients_to_contact = await sales_assistant.find_clients_to_contact(db)
        
        if not clients_to_contact:
            await message.answer("✅ Все клиенты в порядке, никому писать не нужно")
            db.close()
            return
        
        text = f"🎯 <b>Найдено клиентов для контакта: {len(clients_to_contact)}</b>\n\n"
        
        for item in clients_to_contact[:5]:  # Показываем первых 5
            client = item['client']
            text += (
                f"🏪 <b>{client.company_name}</b>\n"
                f"   Причина: {item['reason']}\n"
                f"   Последний заказ: {item['days_since_last']} дней назад\n"
                f"   Бонусы: {client.bonus_balance:,.0f}₸\n"
                f"   /aicontact_{client.id}\n\n"
            )
        
        if len(clients_to_contact) > 5:
            text += f"... и еще {len(clients_to_contact) - 5} клиентов"
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error in AI analyze: {e}")
        await message.answer(f"❌ Ошибка анализа: {str(e)}")
    
    db.close()

@dp.message(lambda message: message.text and message.text.startswith("/aicontact_"))
async def cmd_ai_contact_client(message: types.Message):
    """
    AI-анализ конкретного клиента и отправка сообщения
    """
    if not is_admin_or_manager(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return
    
    if not sales_assistant:
        await message.answer("❌ AI-помощник не настроен")
        return
    
    try:
        client_id = int(message.text.split("_")[1])
    except:
        await message.answer("❌ Неверный формат команды")
        return
    
    db = SessionLocal()
    
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        await message.answer("❌ Клиент не найден")
        db.close()
        return
    
    await message.answer(f"🤖 Анализирую клиента <b>{client.company_name}</b>...", parse_mode="HTML")
    
    try:
        # Получаем анализ от AI
        analysis = await sales_assistant.analyze_client(client, db)
        
        text = (
            f"📊 <b>AI-Анализ: {client.company_name}</b>\n\n"
            f"<b>Писать клиенту:</b> {'✅ Да' if analysis['should_contact'] else '❌ Нет'}\n"
            f"<b>Причина:</b> {analysis['reason']}\n\n"
        )
        
        if analysis['recommendations']:
            text += f"<b>Рекомендации:</b>\n"
            for rec in analysis['recommendations']:
                text += f"• {rec}\n"
            text += "\n"
        
        text += f"<b>Тайминг:</b> {analysis['timing']}\n\n"
        
        if analysis['should_contact'] and analysis['message']:
            text += f"<b>Предложенное сообщение:</b>\n\n{analysis['message']}\n\n"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Отправить это сообщение", callback_data=f"send_ai_msg_{client_id}")],
                [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_ai_msg_{client_id}")]
            ])
            
            # Сохраняем сообщение для отправки
            if not hasattr(message.bot, 'pending_ai_messages'):
                message.bot.pending_ai_messages = {}
            message.bot.pending_ai_messages[client_id] = analysis['message']
            
            await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
        else:
            await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error analyzing client: {e}")
        await message.answer(f"❌ Ошибка анализа: {str(e)}")
    
    db.close()

@dp.callback_query(lambda c: c.data.startswith("send_ai_msg_"))
async def callback_send_ai_message(callback: types.CallbackQuery):
    """
    Отправить AI-сообщение клиенту
    """
    if not is_admin_or_manager(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    client_id = int(callback.data.split("_")[3])
    
    db = SessionLocal()
    
    client = db.query(Client).filter(Client.id == client_id).first()
    
    if not client:
        await callback.answer("❌ Клиент не найден", show_alert=True)
        db.close()
        return
    
    user = db.query(User).filter(User.id == client.user_id).first()
    
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        db.close()
        return
    
    # Получаем сообщение
    if not hasattr(callback.bot, 'pending_ai_messages') or client_id not in callback.bot.pending_ai_messages:
        await callback.answer("❌ Сообщение не найдено", show_alert=True)
        db.close()
        return
    
    ai_message = callback.bot.pending_ai_messages[client_id]
    
    # Отправляем клиенту
    try:
        await bot.send_message(
            chat_id=user.telegram_id,
            text=ai_message
        )
        
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ <b>Сообщение отправлено клиенту!</b>",
            parse_mode="HTML"
        )
        
        # Удаляем из pending
        del callback.bot.pending_ai_messages[client_id]
        
        await callback.answer("✅ Отправлено!")
        
    except Exception as e:
        logger.error(f"Error sending AI message: {e}")
        await callback.answer(f"❌ Ошибка отправки: {str(e)}", show_alert=True)
    
    db.close()  
    
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Команда /help - помощь"""
    text = (
        "📖 <b>Доступные команды:</b>\n\n"
        "/start - Главное меню\n"
        "/orders - Мои заказы\n"
        "/profile - Мой профиль\n"
        "/help - Помощь\n\n"
        "💬 Для связи с менеджером используйте кнопку в меню"
    )
    
    await message.answer(text, parse_mode="HTML")
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Список команд"""
    
    help_text = """
📖 <b>Доступные команды:</b>

<b>Для клиентов:</b>
/start - Главное меню
/orders - Мои заказы
/profile - Мой профиль
/ai - 🤖 AI-Помощник (новое!)
/help - Справка

<b>Для админов/менеджеров:</b>
/admin - Админ-панель
/pending - Клиенты на модерации
/neworders - Новые заказы
/aianalyze - 🤖 AI-анализ клиентов (новое!)
"""
    
    await message.answer(help_text, parse_mode="HTML")
# ============================================
# CALLBACK HANDLERS
# ============================================

@dp.callback_query(F.data == "about")
async def callback_about(callback: types.CallbackQuery):
    """О компании"""
    text = (
        "🏢 <b>О компании HappySnack</b>\n\n"
        "Мы работаем на рынке дистрибуции более 20 лет.\n\n"
        "📦 Поставляем:\n"
        "• HAPPY CORN (официальный дистрибьютор)\n"
        "• Широкий ассортимент снеков\n"
        "• Напитки известных брендов\n\n"
        "🚚 Доставка по Алматы\n"
        "💳 Отсрочка платежа\n"
        "🎁 Бонусная программа"
    )
    
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "contacts")
async def callback_contacts(callback: types.CallbackQuery):
    """Контакты"""
    text = (
        "📞 <b>Контакты HappySnack</b>\n\n"
        "📱 Телефон: +7 XXX XXX XX XX\n"
        "✉️ Email: info@happysnack.kz\n"
        "📍 Адрес: г. Алматы, ул. ...\n\n"
        "💬 Telegram: @YourManager\n\n"
        "⏰ Режим работы:\n"
        "Пн-Пт: 9:00 - 18:00\n"
        "Сб: 9:00 - 15:00\n"
        "Вс: Выходной"
    )
    
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "my_orders")
async def callback_my_orders(callback: types.CallbackQuery):
    """Мои заказы"""
    await cmd_orders(callback.message)
    await callback.answer()

@dp.callback_query(F.data == "profile")
async def callback_profile(callback: types.CallbackQuery):
    """Профиль"""
    await cmd_profile(callback.message)
    await callback.answer()

@dp.callback_query(F.data == "contact_manager")
async def callback_contact_manager(callback: types.CallbackQuery):
    """Связаться с менеджером"""
    await callback.message.answer(
        "💬 Свяжитесь с вашим менеджером:\n\n"
        "@YourManagerUsername\n"
        "или напишите нам: +7 XXX XXX XX XX"
    )
    await callback.answer()
@dp.callback_query(F.data == "admin_orders")
@dp.callback_query(F.data == "admin_orders")
async def callback_admin_orders(callback: types.CallbackQuery):
    """Заказы"""
    if not is_admin_or_manager(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    db = SessionLocal()
    
    user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
    
    query = db.query(Order).filter(Order.status == "new")
    
    if user.role == "manager":
        query = query.filter(Order.manager_id == user.id)
    
    orders = query.order_by(Order.created_at.desc()).limit(10).all()
    
    if not orders:
        await callback.message.answer("✅ Нет новых заказов")
        db.close()
        await callback.answer()
        return
    
    text = "🆕 <b>Новые заказы:</b>\n\n"
    
    for order in orders:
        client = db.query(Client).filter(Client.id == order.client_id).first()
        text += (
            f"📦 <b>Заказ {order.order_number}</b>\n"
            f"   ID: {order.id}\n"
            f"   Клиент: {client.company_name}\n"
            f"   Сумма: {order.final_total:.0f}₸\n"
            f"   Товаров: {len(order.items)} позиций\n"
            f"   Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"   /order_{order.id}\n\n"
        )
    
    await callback.message.answer(text, parse_mode="HTML")
    db.close()
    await callback.answer()

@dp.callback_query(F.data == "admin_clients")
async def callback_admin_clients(callback: types.CallbackQuery):
    """Клиенты"""
    if not is_admin_or_manager(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    db = SessionLocal()
    
    pending_clients = db.query(Client).filter(
        Client.status == "pending"
    ).order_by(Client.created_at.desc()).limit(10).all()
    
    if not pending_clients:
        await callback.message.answer("✅ Нет клиентов на модерации")
        db.close()
        await callback.answer()
        return
    
    text = "⏳ <b>Клиенты на модерации:</b>\n\n"
    
    for client in pending_clients:
        user = db.query(User).filter(User.id == client.user_id).first()
        text += (
            f"🏪 <b>{client.company_name}</b>\n"
            f"   ID: {client.id}\n"
            f"   БИН: {client.bin_iin or 'не указан'}\n"
            f"   Адрес: {client.address or 'не указан'}\n"
            f"   Telegram: @{user.username or 'нет username'}\n"
            f"   Дата: {client.created_at.strftime('%d.%m.%Y')}\n"
            f"   /approve_{client.id} или /reject_{client.id}\n\n"
        )
    
    await callback.message.answer(text, parse_mode="HTML")
    db.close()
    await callback.answer()

@dp.callback_query(F.data == "admin_products")
@dp.callback_query(F.data == "admin_products")
async def callback_admin_products(callback: types.CallbackQuery):
    """Товары"""
    await callback.message.answer(
        "📦 <b>Управление товарами</b>\n\n"
        "Для управления товарами используйте:\n\n"
        "🌐 <b>Веб-дашборд:</b>\n"
        "http://localhost:8000/static/admin/index.html\n\n"
        "Там вы можете:\n"
        "• Просматривать все товары\n"
        "• Добавлять новые\n"
        "• Редактировать цены и остатки\n"
        "• Импортировать прайс из Excel\n"
        "• Переключать вид (список/плитка)",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_settings")
async def callback_admin_settings(callback: types.CallbackQuery):
    """Настройки"""
    await callback.message.answer(
        "⚙️ <b>Настройки системы</b>\n\n"
        "Для управления настройками используйте веб-дашборд:\n"
        "http://localhost:8000/static/admin/index.html\n\n"
        "Там вы можете изменить:\n"
        "• Бонусы\n"
        "• Скидки\n"
        "• Кредитные лимиты\n"
        "• Отсрочку платежа\n"
        "• И многое другое",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_main")
@dp.callback_query(F.data == "back_to_main")
async def callback_back_to_main(callback: types.CallbackQuery):
    """Вернуться в главное меню"""
    db = SessionLocal()
    
    user = db.query(User).filter(
        User.telegram_id == callback.from_user.id
    ).first()
    
    if not user:
        await callback.message.answer("❌ Вы не зарегистрированы")
        db.close()
        await callback.answer()
        return
    
    # Удаляем старое сообщение
    try:
        await callback.message.delete()
    except:
        pass
    
    # Показываем главное меню
    client = db.query(Client).filter(Client.user_id == user.id).first()
    
    if user.role in ["admin", "manager"]:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👔 Админ-панель", callback_data="open_admin_panel")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [
                InlineKeyboardButton(text="📦 Заказы", callback_data="admin_orders"),
                InlineKeyboardButton(text="👥 Клиенты", callback_data="admin_clients")
            ]
        ])
        
        await callback.message.answer(
            f"👋 Привет, {'администратор' if user.role == 'admin' else 'менеджер'}!\n\n"
            "Выберите действие:",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    elif user.role == "client" and client:
        if client.status == "active":
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="📦 Мои заказы", callback_data="my_orders"),
                    InlineKeyboardButton(text="👤 Профиль", callback_data="profile")
                ],
                [InlineKeyboardButton(text="💬 Связаться с менеджером", callback_data="contact_manager")]
            ])
            
            await callback.message.answer(
                f"👋 С возвращением, <b>{client.company_name}</b>!\n\n"
                f"💰 Ваш бонусный баланс: <b>{client.bonus_balance:.0f}₸</b>\n"
                f"💳 Доступный кредит: <b>{(client.credit_limit - client.debt):.0f}₸</b>",
                parse_mode="HTML",
                reply_markup=keyboard
            )
    
    db.close()
    await callback.answer()
# ============================================
# ЗАПУСК БОТА
# ============================================
@dp.callback_query(F.data == "back_to_main")
async def callback_back_to_main(callback: types.CallbackQuery):
    """Вернуться в главное меню"""
    await callback.message.delete()
    await cmd_start(callback.message)
    await callback.answer()
async def main():
    """Запуск бота"""
    logger.info("🤖 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())