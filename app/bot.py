"""
Telegram бот для HappySnack B2B Shop
ПОЛНАЯ ОБНОВЛЕННАЯ ВЕРСИЯ
✅ AI работает ДО регистрации (агрессивно продает)
✅ Welcome бонус 5,000₸
✅ Валидация телефона и БИН
✅ Аналитика воронки
✅ Команда /stats
"""
import asyncio
import logging
import re  # ← ДОБАВЛЕНО для валидации
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import settings
from database import SessionLocal
from models.user import User, Client
from models.order import Order
from models.bonus import BonusTransaction  # ← ДОБАВЛЕНО
from datetime import datetime
from sqlalchemy import func
from ai_agent import sales_assistant
import json
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ← ДОБАВЛЕНО: импорт моделей аналитики
try:
    from models.analytics import AnalyticsEvent, ClientMetrics
    ANALYTICS_ENABLED = True
except ImportError:
    ANALYTICS_ENABLED = False
    logger.warning("Analytics models not found - analytics disabled")

# Состояние для AI-чата
class AIChat(StatesGroup):
    talking = State()

# Состояния для регистрации
class RegistrationStates(StatesGroup):
    waiting_for_company_name = State()
    waiting_for_bin = State()
    waiting_for_address = State()
    waiting_for_contact = State()

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
# ОСНОВНЫЕ КОМАНДЫ
# ============================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """
    Команда /start - приветствие и главное меню
    """
    db = SessionLocal()
    
    # ← ДОБАВЛЕНО: ЛОГИРУЕМ СОБЫТИЕ /start
    if ANALYTICS_ENABLED:
        try:
            analytics_event = AnalyticsEvent(
                event_type="start",
                telegram_id=message.from_user.id,
                username=message.from_user.username
            )
            db.add(analytics_event)
            db.commit()
        except Exception as e:
            logger.error(f"Analytics error: {e}")
    
    user = db.query(User).filter(
        User.telegram_id == message.from_user.id
    ).first()
    
    if not user:
        # НОВЫЙ ПОЛЬЗОВАТЕЛЬ - ONBOARDING
        logger.info(f"🆕 NEW USER: {message.from_user.username or 'No username'} | ID: {message.from_user.id}")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏢 О компании HappySnack", callback_data="about_company")],
            [InlineKeyboardButton(text="📦 Что мы предлагаем", callback_data="our_products")],
            [InlineKeyboardButton(text="💰 Условия работы", callback_data="work_terms")],
            [InlineKeyboardButton(text="📞 Контакты", callback_data="contacts")],
            [InlineKeyboardButton(text="✅ Хочу начать работать!", callback_data="start_registration")]
        ])
        
        await message.answer(
            f"👋 <b>Добро пожаловать в HappySnack B2B Shop!</b>\n\n"
            f"<code>Ваш Telegram ID: {message.from_user.id}</code>\n"
            f"<i>(Сохраните на случай если понадобится)</i>\n\n"
            f"🏪 Мы — один из крупнейших дистрибьюторов качественных снеков и напитков в Казахстане. "
            f"Работаем на рынке более 20 лет!\n\n"
            f"🎯 <b>Работаем только с B2B клиентами:</b>\n"
            f"• Магазины и супермаркеты\n"
            f"• Кафе и рестораны\n"
            f"• Киоски и автозаправки\n"
            f"• Оптовые компании\n\n"
            f"👇 <b>Узнайте больше о нас перед регистрацией:</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    else:
        # СУЩЕСТВУЮЩИЙ ПОЛЬЗОВАТЕЛЬ
        client = db.query(Client).filter(Client.user_id == user.id).first()
        
        if user.role == "client":
            if not client:
                await message.answer(
                    "❌ Профиль клиента не найден.\n\n"
                    "Пожалуйста, завершите регистрацию."
                )
            elif client.status == "pending":
                await message.answer(
                    "⏳ <b>Ваша заявка на рассмотрении</b>\n\n"
                    "🎁 После одобрения вы получите:\n"
                    "• 5,000₸ приветственных бонусов!\n"
                    "• Доступ к каталогу и ценам\n"
                    "• Персональные условия работы\n\n"
                    "Мы свяжемся с вами в течение 24 часов!\n\n"
                    "По вопросам: +7 XXX XXX XX XX",
                    parse_mode="HTML"
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
                    f"💰 Ваш бонусный баланс: <b>{client.bonus_balance:,.0f}₸</b>\n"
                    f"💳 Доступный кредит: <b>{(client.credit_limit - client.debt):,.0f}₸</b>\n\n"
                    f"Чем могу помочь? Напишите что вас интересует! 🚀",
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            else:
                await message.answer(
                    "🚫 Ваш аккаунт заблокирован.\n\n"
                    "Свяжитесь с менеджером: +7 XXX XXX XX XX"
                )
        elif user.role in ["admin", "manager"]:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
                [
                    InlineKeyboardButton(text="📦 Заказы", callback_data="admin_orders"),
                    InlineKeyboardButton(text="👥 Клиенты", callback_data="admin_clients")
                ]
            ])
            
            await message.answer(
                f"👋 Привет, {'администратор' if user.role == 'admin' else 'менеджер'}!\n\n"
                "Используйте:\n"
                "/admin - Админ-панель\n"
                "/stats - Статистика воронки",
                parse_mode="HTML",
                reply_markup=keyboard
            )
    
    db.close()

@dp.message(Command("myid"))
async def cmd_myid(message: types.Message):
    """Показать свой Telegram ID"""
    await message.answer(
        f"🆔 <b>Ваш Telegram ID:</b>\n\n"
        f"<code>{message.from_user.id}</code>\n\n"
        f"Username: @{message.from_user.username or 'не указан'}\n"
        f"Имя: {message.from_user.full_name}",
        parse_mode="HTML"
    )

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    """Отменить текущее действие"""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нечего отменять 🤷‍♂️")
        return
    
    await state.clear()
    await message.answer("❌ Действие отменено.\n\nИспользуйте /start для начала.")

# ← ДОБАВЛЕНО: КОМАНДА /stats ДЛЯ АНАЛИТИКИ
@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Статистика воронки (только для админов)"""
    
    if message.from_user.id not in settings.admin_ids:
        return
    
    if not ANALYTICS_ENABLED:
        await message.answer("❌ Аналитика отключена (нет таблиц в БД)")
        return
    
    db = SessionLocal()
    
    try:
        from datetime import datetime, timedelta
        today = datetime.utcnow().date()
        week_ago = today - timedelta(days=7)
        
        # Сегодня
        starts_today = db.query(AnalyticsEvent).filter(
            AnalyticsEvent.event_type == "start",
            func.date(AnalyticsEvent.created_at) == today
        ).count()
        
        reg_started_today = db.query(AnalyticsEvent).filter(
            AnalyticsEvent.event_type == "registration_started",
            func.date(AnalyticsEvent.created_at) == today
        ).count()
        
        reg_completed_today = db.query(AnalyticsEvent).filter(
            AnalyticsEvent.event_type == "registration_completed",
            func.date(AnalyticsEvent.created_at) == today
        ).count()
        
        # За неделю
        starts_week = db.query(AnalyticsEvent).filter(
            AnalyticsEvent.event_type == "start",
            func.date(AnalyticsEvent.created_at) >= week_ago
        ).count()
        
        reg_completed_week = db.query(AnalyticsEvent).filter(
            AnalyticsEvent.event_type == "registration_completed",
            func.date(AnalyticsEvent.created_at) >= week_ago
        ).count()
        
        # Всего
        total_clients = db.query(Client).count()
        pending_clients = db.query(Client).filter(Client.status == "pending").count()
        active_clients = db.query(Client).filter(Client.status == "active").count()
        
        # Конверсия
        conversion_week = (reg_completed_week / starts_week * 100) if starts_week > 0 else 0
        
        await message.answer(
            f"📊 <b>СТАТИСТИКА ВОРОНКИ</b>\n\n"
            f"<b>СЕГОДНЯ:</b>\n"
            f"• /start: {starts_today}\n"
            f"• Начали регистрацию: {reg_started_today}\n"
            f"• Завершили: {reg_completed_today}\n\n"
            f"<b>ЗА НЕДЕЛЮ:</b>\n"
            f"• /start: {starts_week}\n"
            f"• Завершили регистрацию: {reg_completed_week}\n"
            f"• Конверсия: {conversion_week:.1f}%\n\n"
            f"<b>ВСЕГО КЛИЕНТОВ:</b>\n"
            f"• Активных: {active_clients}\n"
            f"• На модерации: {pending_clients}\n"
            f"• Всего: {total_clients}",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Stats error: {e}", exc_info=True)
        await message.answer(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()

# ============================================
# ONBOARDING CALLBACKS
# ============================================

@dp.callback_query(F.data == "about_company")
async def callback_about_company(callback: types.CallbackQuery):
    """О компании"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Хочу начать работать!", callback_data="start_registration")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_start")]
    ])
    
    await callback.message.edit_text(
        "🏢 <b>О компании HappySnack</b>\n\n"
        "📅 <b>История:</b>\n"
        "Мы работаем на рынке дистрибуции более 20 лет и являемся одним из крупнейших "
        "поставщиков снеков и напитков в Алматы.\n\n"
        "🏆 <b>Наши преимущества:</b>\n"
        "• Официальный дистрибьютор HAPPY CORN\n"
        "• Собственный склад 500м²\n"
        "• Команда 11 человек\n"
        "• 7 торговых представителей\n"
        "• Собственная логистика\n\n"
        "💼 <b>С нами работают:</b>\n"
        "• 150+ магазинов в Алматы\n"
        "• Крупные сетевые супермаркеты\n"
        "• Кафе и рестораны\n"
        "• Киоски и автозаправки\n\n"
        "✨ <b>Почему выбирают нас:</b>\n"
        "• Широкий ассортимент (200+ позиций)\n"
        "• Конкурентные цены\n"
        "• Гибкие условия работы\n"
        "• Быстрая доставка каждый день\n"
        "• Персональный менеджер",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == "our_products")
async def callback_our_products(callback: types.CallbackQuery):
    """Наш ассортимент"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Хочу начать работать!", callback_data="start_registration")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_start")]
    ])
    
    await callback.message.edit_text(
        "📦 <b>Наш ассортимент</b>\n\n"
        "🍿 <b>ПОПКОРН HAPPY CORN (эксклюзивно!):</b>\n"
        "• 7 вкусов: сырный, карамельный, BBQ, острый, сладкий и др.\n"
        "• 5 видов фасовки (от малых до коробок)\n"
        "• Маржа: до 60% - самая высокая в категории!\n"
        "• Быстрая оборачиваемость: 2-3 дня\n\n"
        "🥔 <b>ЧИПСЫ:</b>\n"
        "• Papa Nachos\n"
        "• Real Chips\n"
        "• Gramzz\n"
        "• Happy Crisp\n"
        "Маржа: 25-35%\n\n"
        "🍫 <b>БАТОНЧИКИ:</b>\n"
        "• Здоровый перекус (протеиновые батончики)\n"
        "Маржа: 30-40%\n\n"
        "🍞 <b>ХЛЕБЦЫ</b>\n"
        "• Различные виды\n"
        "Маржа: 25-30%\n\n"
        "🥤 <b>НАПИТКИ:</b>\n"
        "• Живой квас (ржаной и овсяной)\n"
        "• NITRO (энергетический напиток)\n"
        "• NITRO Fresh (газированный напиток)\n"
        "• Витаминизированная вода\n"
        "• Salam TEA (чай)\n"
        "Маржа: 20-30%\n\n"
        "🥐 <b>СВЕЖАЯ ВЫПЕЧКА:</b>\n"
        "• Круассаны\n"
        "• Профитроли\n"
        "• Трубочки с кремом\n"
        "• Печенье\n"
        "Маржа: 25-35%\n\n"
        "✨ <b>Полный ассортимент доступен после регистрации!</b>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == "work_terms")
async def callback_work_terms(callback: types.CallbackQuery):
    """Условия работы"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Хочу начать работать!", callback_data="start_registration")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_start")]
    ])
    
    await callback.message.edit_text(
        "💰 <b>Условия работы</b>\n\n"
        "💳 <b>Кредитный лимит:</b>\n"
        "• Новым клиентам: до 500,000₸\n"
        "• Постоянным: индивидуально (до 2,000,000₸)\n\n"
        "📅 <b>Отсрочка платежа:</b>\n"
        "• Стандарт: 14 дней\n"
        "• Постоянным клиентам: до 30 дней\n\n"
        "💎 <b>Скидки:</b>\n"
        "• Персональные от 5%\n"
        "• Акции и специальные предложения\n"
        "• Скидки за объем\n\n"
        "🎁 <b>Бонусная программа:</b>\n"
        "• При регистрации: 5,000₸ сразу!\n"
        "• Кэшбек: от 3% до 10% (прогрессивный)\n"
        "• Можно оплатить до 20% заказа бонусами\n"
        "• Бонусы не сгорают 6 месяцев\n\n"
        "🚚 <b>Доставка:</b>\n"
        "• По Алматы: бесплатно от 30,000₸\n"
        "• Каждый день (кроме воскресенья)\n"
        "• Выбор времени доставки\n\n"
        "📦 <b>Минимальный заказ:</b>\n"
        "• От 20,000₸\n\n"
        "👨‍💼 <b>Поддержка:</b>\n"
        "• Личный менеджер\n"
        "• AI-ассистент 24/7\n"
        "• Помощь с выкладкой товара\n"
        "• Маркетинговые материалы",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == "contacts")
async def callback_contacts(callback: types.CallbackQuery):
    """Контакты"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Хочу начать работать!", callback_data="start_registration")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_start")]
    ])
    
    await callback.message.edit_text(
        "📞 <b>Контакты</b>\n\n"
        "🏢 <b>Название:</b> HappySnack\n\n"
        "📍 <b>Адрес склада:</b>\n"
        "г. Алматы, [ваш адрес]\n\n"
        "📞 <b>Телефон:</b>\n"
        "+7 XXX XXX XX XX\n\n"
        "📧 <b>Email:</b>\n"
        "info@happysnack.kz\n\n"
        "💬 <b>Telegram менеджера:</b>\n"
        "@happysnack_manager\n\n"
        "⏰ <b>Режим работы:</b>\n"
        "Пн-Пт: 9:00-18:00\n"
        "Сб: 9:00-15:00\n"
        "Вс: выходной\n\n"
        "🚚 <b>Доставка:</b>\n"
        "Ежедневно (кроме воскресенья)\n"
        "с 10:00 до 19:00",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_start")
async def callback_back_to_start(callback: types.CallbackQuery):
    """Вернуться в главное меню onboarding"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏢 О компании HappySnack", callback_data="about_company")],
        [InlineKeyboardButton(text="📦 Что мы предлагаем", callback_data="our_products")],
        [InlineKeyboardButton(text="💰 Условия работы", callback_data="work_terms")],
        [InlineKeyboardButton(text="📞 Контакты", callback_data="contacts")],
        [InlineKeyboardButton(text="✅ Хочу начать работать!", callback_data="start_registration")]
    ])
    
    await callback.message.edit_text(
        f"👋 <b>Добро пожаловать в HappySnack B2B Shop!</b>\n\n"
        f"🏪 Мы — один из крупнейших дистрибьюторов качественных снеков и напитков в Казахстане. "
        f"Работаем на рынке более 20 лет!\n\n"
        f"🎯 <b>Работаем только с B2B клиентами:</b>\n"
        f"• Магазины и супермаркеты\n"
        f"• Кафе и рестораны\n"
        f"• Киоски и автозаправки\n"
        f"• Оптовые компании\n\n"
        f"👇 <b>Узнайте больше о нас перед регистрацией:</b>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

# ============================================
# РЕГИСТРАЦИЯ (FSM)
# ============================================

@dp.callback_query(F.data == "start_registration")
async def start_registration(callback: types.CallbackQuery, state: FSMContext):
    """Начать регистрацию"""
    
    # ← ДОБАВЛЕНО: ЛОГИРУЕМ НАЧАЛО РЕГИСТРАЦИИ
    if ANALYTICS_ENABLED:
        try:
            db = SessionLocal()
            analytics_event = AnalyticsEvent(
                event_type="registration_started",
                telegram_id=callback.from_user.id,
                username=callback.from_user.username
            )
            db.add(analytics_event)
            db.commit()
            db.close()
        except Exception as e:
            logger.error(f"Analytics error: {e}")
    
    await callback.message.edit_text(
        "📝 <b>Регистрация нового клиента</b>\n\n"
        "Это займет всего 2 минуты!\n\n"
        "🎁 <b>После одобрения вы получите 5,000₸ бонусов!</b>\n\n"
        "1️⃣ <b>Шаг 1 из 4</b>\n\n"
        "Введите <b>название вашей компании</b>:\n\n"
        "<i>Например: ТОО \"Магазин 24/7\" или ИП Иванов</i>",
        parse_mode="HTML"
    )
    await callback.answer()
    await state.set_state(RegistrationStates.waiting_for_company_name)

@dp.message(RegistrationStates.waiting_for_company_name)
async def process_company_name(message: types.Message, state: FSMContext):
    """Получаем название компании"""
    await state.update_data(company_name=message.text)
    
    await message.answer(
        "2️⃣ <b>Шаг 2 из 4</b>\n\n"
        "Введите <b>БИН/ИИН</b> вашей компании:\n\n"
        "📋 Должен содержать ровно <b>12 цифр</b>\n\n"
        "<i>Например: 123456789012</i>",
        parse_mode="HTML"
    )
    await state.set_state(RegistrationStates.waiting_for_bin)

@dp.message(RegistrationStates.waiting_for_bin)
async def process_bin(message: types.Message, state: FSMContext):
    """Получаем БИН с валидацией"""
    
    # ← ДОБАВЛЕНО: ВАЛИДАЦИЯ БИН (ровно 12 цифр)
    bin_iin = re.sub(r'[^\d]', '', message.text)  # Убираем все кроме цифр
    
    if len(bin_iin) != 12:
        await message.answer(
            "❌ <b>Неверный формат БИН/ИИН!</b>\n\n"
            "БИН/ИИН должен содержать ровно <b>12 цифр</b>.\n\n"
            f"Вы ввели: <code>{message.text}</code> ({len(bin_iin)} цифр)\n\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    await state.update_data(bin_iin=bin_iin)
    
    await message.answer(
        "3️⃣ <b>Шаг 3 из 4</b>\n\n"
        "Введите <b>адрес</b> вашего магазина/склада:\n\n"
        "<i>Например: г. Алматы, ул. Абая 150</i>",
        parse_mode="HTML"
    )
    await state.set_state(RegistrationStates.waiting_for_address)

@dp.message(RegistrationStates.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    """Получаем адрес"""
    await state.update_data(address=message.text)
    
    await message.answer(
        "4️⃣ <b>Шаг 4 из 4 (последний!)</b>\n\n"
        "Введите <b>контактный телефон</b>:\n\n"
        "📱 Формат: +7 777 123 45 67 или 8 777 123 45 67\n\n"
        "<i>Например: +7 777 123 45 67</i>",
        parse_mode="HTML"
    )
    await state.set_state(RegistrationStates.waiting_for_contact)

@dp.message(RegistrationStates.waiting_for_contact)
async def process_contact(message: types.Message, state: FSMContext):
    """Завершаем регистрацию с валидацией телефона"""
    
    # ← ДОБАВЛЕНО: ВАЛИДАЦИЯ ТЕЛЕФОНА
    phone = re.sub(r'[^\d]', '', message.text)  # Убираем все кроме цифр
    
    # Проверяем формат +7XXXXXXXXXX или 8XXXXXXXXXX
    if len(phone) == 11 and phone.startswith(('7', '8')):
        # Нормализуем к формату +7XXXXXXXXXX
        if phone.startswith('8'):
            phone = '7' + phone[1:]
        formatted_phone = f"+{phone}"
    elif len(phone) == 10:
        # Если 10 цифр, добавляем +7
        formatted_phone = f"+7{phone}"
    else:
        await message.answer(
            "❌ <b>Неверный формат телефона!</b>\n\n"
            "Телефон должен быть в формате:\n"
            "• +7 777 123 45 67\n"
            "• 8 777 123 45 67\n"
            "• 7771234567\n\n"
            f"Вы ввели: <code>{message.text}</code> ({len(phone)} цифр)\n\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return
    
    db = SessionLocal()
    data = await state.get_data()
    
    try:
        # Создаём пользователя
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            role="client",
            is_active=True
        )
        db.add(user)
        db.flush()
        
        # Создаём клиента (бонус начислится при одобрении)
        client = Client(
            user_id=user.id,
            company_name=data['company_name'],
            bin_iin=data['bin_iin'],
            address=data['address'],
            contact_phone=formatted_phone,
            status="pending",
            credit_limit=500000.0,
            payment_delay_days=14,
            discount_percent=0.0,
            bonus_balance=0.0,  # Бонус начислится при одобрении
            debt=0.0
        )
        db.add(client)
        db.flush()
        
        # ← ДОБАВЛЕНО: ЛОГИРУЕМ ЗАВЕРШЕНИЕ РЕГИСТРАЦИИ
        if ANALYTICS_ENABLED:
            analytics_event = AnalyticsEvent(
                event_type="registration_completed",
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                event_metadata={
                    "client_id": client.id,
                    "company_name": data['company_name']
                }
            )
            db.add(analytics_event)
            
            # Создаем метрики клиента
            client_metrics = ClientMetrics(
                client_id=client.id,
                telegram_id=message.from_user.id,
                first_start_at=datetime.utcnow(),
                registration_completed_at=datetime.utcnow()
            )
            db.add(client_metrics)
        
        db.commit()
        
        await state.clear()
        
        await message.answer(
            "✅ <b>Регистрация успешно завершена!</b>\n\n"
            "⏳ Ваша заявка отправлена на рассмотрение.\n\n"
            "🎁 <b>После одобрения вы получите:</b>\n"
            "• 5,000₸ приветственных бонусов!\n"
            "• Доступ к каталогу и ценам\n"
            "• Персональные условия работы\n\n"
            "💡 <b>Сделайте первый заказ от 50,000₸ и получите еще 5,000₸ бонусов!</b>\n\n"
            "Мы проверим данные и свяжемся с вами в течение 24 часов.\n\n"
            "Спасибо за интерес к HappySnack! 🎉",
            parse_mode="HTML"
        )
        
        # Уведомляем админов С TELEGRAM ID И КНОПКОЙ
        for admin_id in settings.admin_ids:
            try:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="✅ Одобрить и начислить 5,000₸",
                        callback_data=f"approve_client_{client.id}"
                    )]
                ])
                
                await bot.send_message(
                    admin_id,
                    f"🆕 <b>Новая заявка на регистрацию!</b>\n\n"
                    f"👤 <b>Telegram ID: <code>{message.from_user.id}</code></b>\n"
                    f"Username: @{message.from_user.username or 'нет'}\n"
                    f"Имя: {message.from_user.full_name}\n\n"
                    f"🏢 Компания: {data['company_name']}\n"
                    f"📋 БИН: {data['bin_iin']}\n"
                    f"📍 Адрес: {data['address']}\n"
                    f"📞 Телефон: {formatted_phone}\n\n"
                    f"💰 Welcome бонус: 5,000₸ (начислится при одобрении)",
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при регистрации.\n\n"
            f"Ошибка: {str(e)}\n\n"
            "Попробуйте позже или свяжитесь с нами:\n"
            "📞 +7 XXX XXX XX XX"
        )
        await state.clear()
    finally:
        db.close()

# ← ДОБАВЛЕНО: CALLBACK ДЛЯ БЫСТРОГО ОДОБРЕНИЯ С WELCOME БОНУСОМ
@dp.callback_query(F.data.startswith("approve_client_"))
async def callback_approve_client_with_bonus(callback: types.CallbackQuery):
    """Одобрить клиента и начислить welcome бонус"""
    
    # Проверка что это админ
    if callback.from_user.id not in settings.admin_ids:
        await callback.answer("❌ У вас нет прав!", show_alert=True)
        return
    
    try:
        client_id = int(callback.data.split("_")[-1])
        
        db = SessionLocal()
        client = db.query(Client).filter(Client.id == client_id).first()
        
        if not client:
            await callback.answer("❌ Клиент не найден!", show_alert=True)
            db.close()
            return
        
        if client.status == "active":
            await callback.answer("✅ Клиент уже одобрен!", show_alert=True)
            db.close()
            return
        
        # ОДОБРЯЕМ + НАЧИСЛЯЕМ WELCOME БОНУС
        client.status = "active"
        client.bonus_balance = 5000.0  # WELCOME БОНУС!
        
        # Создаем транзакцию бонусов
        bonus_transaction = BonusTransaction(
            client_id=client.id,
            type="earned",
            amount=5000.0,
            description="🎁 Welcome бонус за регистрацию"
                    )
        db.add(bonus_transaction)
        
        # Обновляем метрики
        if ANALYTICS_ENABLED:
            metrics = db.query(ClientMetrics).filter(
                ClientMetrics.client_id == client.id
            ).first()
            if metrics:
                metrics.first_approved_at = datetime.utcnow()
                metrics.total_bonus_earned = 5000
            
            # Логируем событие
            analytics_event = AnalyticsEvent(
                event_type="client_approved",
                telegram_id=client.user.telegram_id,
                event_metadata={"client_id": client.id}
            )
            db.add(analytics_event)
        
        db.commit()
        
        # Уведомляем клиента
        user = client.user
        try:
            await bot.send_message(
                user.telegram_id,
                "🎉 <b>Отличные новости!</b>\n\n"
                "✅ Ваша регистрация одобрена!\n\n"
                "🎁 <b>На ваш счет начислено 5,000₸ приветственных бонусов!</b>\n\n"
                "Теперь вы можете:\n"
                "• Смотреть каталог и цены\n"
                "• Оформлять заказы\n"
                "• Использовать бонусы (до 20% от заказа)\n\n"
                "💡 Сделайте первый заказ от 50,000₸ и получите еще 5,000₸ бонусов!\n\n"
                "Готовы начать? Напишите мне что вас интересует! 🚀",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to notify client: {e}")
        
        # Обновляем сообщение админу
        await callback.message.edit_text(
            f"{callback.message.text}\n\n"
            f"✅ <b>ОДОБРЕНО!</b>\n"
            f"💰 Начислено 5,000₸ welcome бонусов\n"
            f"Одобрил: @{callback.from_user.username}",
            parse_mode="HTML"
        )
        
        await callback.answer("✅ Клиент одобрен! Welcome бонус начислен!", show_alert=True)
        
        db.close()
        
    except Exception as e:
        logger.error(f"Error approving client: {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

# ============================================
# AI АССИСТЕНТ - РАБОТАЕТ ДЛЯ ВСЕХ!
# ============================================

@dp.message(F.text, ~F.text.startswith('/'))
async def handle_text_message(message: types.Message, state: FSMContext):
    """
    ← ОБНОВЛЕНО: AI РАБОТАЕТ ДЛЯ ВСЕХ!
    Обрабатываем текстовые сообщения через AI
    """
    
    # КРИТИЧНО: ПРОВЕРЯЕМ FSM СОСТОЯНИЕ - НЕ МЕШАЕМ РЕГИСТРАЦИИ!
    current_state = await state.get_state()
    if current_state is not None:
        # Пользователь в процессе регистрации - не мешаем
        return
    
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(
            User.telegram_id == message.from_user.id
        ).first()
        
        # АДМИНЫ И МЕНЕДЖЕРЫ - пропускаем
        if user and user.role in ["admin", "manager"]:
            return
        
        # ПОКАЗЫВАЕМ ЧТО БОТ ПЕЧАТАЕТ
        await bot.send_chat_action(message.chat.id, "typing")
        
        # ВАРИАНТ 1: НЕ ЗАРЕГИСТРИРОВАН - AI ПРОДАЕТ РЕГИСТРАЦИЮ!
        if not user:
            # ПРОВЕРЯЕМ ТРИГГЕРНЫЕ СЛОВА ДЛЯ ЗАПУСКА РЕГИСТРАЦИИ
            trigger_words = ["да", "давай", "хочу", "согласен", "начнем", "начнём", "ок", "okay", "поехали", "погнали"]
            message_lower = message.text.lower().strip()
            
            # Если пользователь соглашается - ЗАПУСКАЕМ РЕГИСТРАЦИЮ
            if any(word == message_lower or message_lower.startswith(word + " ") for word in trigger_words):
                # Показываем начало регистрации
                await message.answer(
                    "📝 <b>Отлично! Начинаем регистрацию</b>\n\n"
                    "Это займет всего 2 минуты!\n\n"
                    "🎁 <b>После одобрения вы получите 5,000₸ бонусов!</b>\n\n"
                    "1️⃣ <b>Шаг 1 из 4</b>\n\n"
                    "Введите <b>название вашей компании</b>:\n\n"
                    "<i>Например: ТОО \"Магазин 24/7\" или ИП Иванов</i>",
                    parse_mode="HTML"
                )
                
                # ЛОГИРУЕМ НАЧАЛО РЕГИСТРАЦИИ
                if ANALYTICS_ENABLED:
                    analytics_event = AnalyticsEvent(
                        event_type="registration_started",
                        telegram_id=message.from_user.id,
                        username=message.from_user.username
                    )
                    db.add(analytics_event)
                    db.commit()
                
                # ЗАПУСКАЕМ FSM РЕГИСТРАЦИИ
                await state.set_state(RegistrationStates.waiting_for_company_name)
                return
            
            # ЛОГИРУЕМ СООБЩЕНИЕ ДО РЕГИСТРАЦИИ
            if ANALYTICS_ENABLED:
                analytics_event = AnalyticsEvent(
                    event_type="pre_registration_message",
                    telegram_id=message.from_user.id,
                    username=message.from_user.username,
                    event_metadata={"message": message.text[:100]}
                )
                db.add(analytics_event)
                db.commit()
            
            # AI ДЛЯ НЕЗАРЕГИСТРИРОВАННЫХ + КНОПКА РЕГИСТРАЦИИ
            if sales_assistant:
                try:
                    response = await sales_assistant.handle_message(
                        message.text,
                        client_id=None,
                        db=db,
                        is_registered=False
                    )
                    
                    # ДОБАВЛЯЕМ КНОПКУ РЕГИСТРАЦИИ
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text="✅ Зарегистрироваться",
                            callback_data="start_registration"
                        )]
                    ])
                    
                    await message.answer(response, parse_mode="HTML", reply_markup=keyboard)
                except Exception as e:
                    logger.error(f"AI error for unregistered: {e}")
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(
                            text="✅ Зарегистрироваться",
                            callback_data="start_registration"
                        )]
                    ])
                    await message.answer(
                        "🤖 Привет! Я AI-ассистент HappySnack!\n\n"
                        "🎁 <b>Специально для новых клиентов - 5,000₸ бонусов при регистрации!</b>\n\n"
                        "Чтобы я мог помочь вам с ценами и заказами, "
                        "пройдите быструю регистрацию - это 2 минуты!\n\n"
                        "Нажмите кнопку ниже чтобы начать! 👇",
                        parse_mode="HTML",
                        reply_markup=keyboard
                    )
            else:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="✅ Зарегистрироваться",
                        callback_data="start_registration"
                    )]
                ])
                await message.answer(
                    "🤖 Привет! Я AI-ассистент HappySnack!\n\n"
                    "🎁 <b>Специально для новых клиентов - 5,000₸ бонусов при регистрации!</b>\n\n"
                    "Нажмите кнопку ниже чтобы зарегистрироваться! 👇",
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            return
        
        # ВАРИАНТ 2: ЗАРЕГИСТРИРОВАН, НО НЕТ ПРОФИЛЯ КЛИЕНТА
        client = db.query(Client).filter(Client.user_id == user.id).first()
        if not client:
            await message.answer(
                "❌ Профиль клиента не найден.\n\n"
                "Пожалуйста, завершите регистрацию: /start"
            )
            return
        
        # ВАРИАНТ 3: ОЖИДАЕТ ОДОБРЕНИЯ
        if client.status == "pending":
            await message.answer(
                "⏳ Ваша заявка на рассмотрении.\n\n"
                "🎁 После одобрения вы получите 5,000₸ бонусов!\n\n"
                "Мы свяжемся с вами в течение 24 часов!\n\n"
                "По вопросам: +7 XXX XXX XX XX"
            )
            return
        
        # ВАРИАНТ 4: ЗАБЛОКИРОВАН
        if client.status == "blocked":
            await message.answer(
                "🚫 Ваш аккаунт заблокирован.\n\n"
                "Свяжитесь с менеджером: +7 XXX XXX XX XX"
            )
            return
        
        # ВАРИАНТ 5: АКТИВНЫЙ КЛИЕНТ - AI В ПОЛНУЮ СИЛУ!
        if client.status == "active":
            if not sales_assistant:
                await message.answer(
                    "🤖 AI-ассистент временно недоступен.\n\n"
                    "Свяжитесь с менеджером: +7 XXX XXX XX XX"
                )
                return
            
            try:
                response = await sales_assistant.handle_message(
                    message.text,
                    client.id,
                    db,
                    is_registered=True
                )
                
                await message.answer(response, parse_mode="HTML")
                
            except Exception as e:
                logger.error(f"AI error for client {client.id}: {e}", exc_info=True)
                await message.answer(
                    "🤖 Извините, временные технические проблемы.\n\n"
                    "Свяжитесь с менеджером:\n"
                    "📞 +7 XXX XXX XX XX"
                )
            
    finally:
        db.close()

# ============================================
# ОСТАЛЬНЫЕ CALLBACKS (мои заказы, профиль и т.д.)
# ============================================

@dp.callback_query(F.data == "my_orders")
async def callback_my_orders(callback: types.CallbackQuery):
    """Мои заказы"""
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
        
        orders = db.query(Order).filter(
            Order.client_id == client.id
        ).order_by(Order.created_at.desc()).limit(10).all()
        
        if not orders:
            await callback.message.edit_text(
                "📦 <b>У вас пока нет заказов</b>\n\n"
                "Напишите мне что вас интересует и я помогу оформить заказ!",
                parse_mode="HTML"
            )
        else:
            text = "📦 <b>Ваши последние заказы:</b>\n\n"
            for order in orders:
                text += (
                    f"🔸 {order.order_number}\n"
                    f"   💰 {order.final_total:,.0f}₸ | "
                    f"📊 {order.status}\n"
                    f"   📅 {order.created_at.strftime('%d.%m.%Y')}\n\n"
                )
            
            await callback.message.edit_text(text, parse_mode="HTML")
    finally:
        db.close()
        
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
            f"📞 Телефон: {client.phone}\n\n"
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

# ============================================
# ЗАПУСК БОТА
# ============================================

async def main():
    """Запуск бота"""
    logger.info("🚀 Starting HappySnack Bot...")
    logger.info(f"🤖 AI Assistant: {'✅ Enabled' if sales_assistant else '❌ Disabled'}")
    logger.info(f"📊 Analytics: {'✅ Enabled' if ANALYTICS_ENABLED else '❌ Disabled'}")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)
        raise
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())