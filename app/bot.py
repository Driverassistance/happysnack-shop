"""
Telegram бот для HappySnack B2B Shop
Обновленная версия с улучшенным onboarding
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
    """Команда /start - приветствие и главное меню"""
    db = SessionLocal()
    
    user = db.query(User).filter(
        User.telegram_id == message.from_user.id
    ).first()
    
    if not user:
        # НОВЫЙ ПОЛЬЗОВАТЕЛЬ - ЗНАКОМИМ С КОМПАНИЕЙ
        logger.info(f"🆕 NEW USER: {message.from_user.username or 'No username'} | ID: {message.from_user.id}")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏢 О компании HappySnack", callback_data="about_company")],
            [InlineKeyboardButton(text="📦 Что мы предлагаем", callback_data="our_products")],
            [InlineKeyboardButton(text="💰 Условия работы", callback_data="work_terms")],
            [InlineKeyboardButton(text="📞 Контакты", callback_data="contacts")],
            [InlineKeyboardButton(text="✅ Хочу начать работать!", callback_data="start_registration")]
        ])
        
        await message.answer(
            "👋 Добро пожаловать в <b>HappySnack B2B Shop</b>!\n\n"
            "🏪 Мы — один из крупнейших дистрибьюторов качественных снеков "
            "и напитков в Казахстане с опытом работы более 10 лет.\n\n"
            "🎯 <b>Работаем только с B2B клиентами:</b>\n"
            "• Магазины и супермаркеты\n"
            "• Кафе и рестораны\n"
            "• Киоски и автозаправки\n"
            "• Оптовые компании\n\n"
            f"<code>Ваш Telegram ID: {message.from_user.id}</code>\n"
            "<i>(Сохраните на случай если понадобится)</i>\n\n"
            "👇 <b>Узнайте больше о нас перед регистрацией:</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        db.close()
        return
    
    # СУЩЕСТВУЮЩИЙ ПОЛЬЗОВАТЕЛЬ
    client = db.query(Client).filter(Client.user_id == user.id).first()
    
    if user.role == "client":
        if not client:
            # Клиента нет - предлагаем регистрацию
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Зарегистрироваться", callback_data="start_registration")]
            ])
            await message.answer(
                "❌ Профиль клиента не найден.\n\n"
                "Пожалуйста, пройдите регистрацию:",
                reply_markup=keyboard
            )
        elif client.status == "pending":
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
                f"🤖 Напишите мне что-нибудь и я помогу с заказом!",
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
    await message.answer(
        "❌ Действие отменено.\n\n"
        "Используйте /start для начала."
    )

# ============================================
# ONBOARDING - ЗНАКОМСТВО С КОМПАНИЕЙ
# ============================================

@dp.callback_query(F.data == "about_company")
async def callback_about_company(callback: types.CallbackQuery):
    """Информация о компании"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Наш ассортимент", callback_data="our_products")],
        [InlineKeyboardButton(text="💰 Условия работы", callback_data="work_terms")],
        [InlineKeyboardButton(text="✅ Готов зарегистрироваться", callback_data="start_registration")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_start")]
    ])
    
    await callback.message.edit_text(
        "🏢 <b>О компании HappySnack</b>\n\n"
        "📊 <b>Мы на рынке более 10 лет</b>\n"
        "Начинали с небольшого склада, сегодня — лидеры по продаже ПОП Корна "
        "дистрибьюторов FMCG в Алматы.\n\n"
        "🎖 <b>Официальный дистрибьютор:</b>\n"
        "• HAPPY CORN (Euro Foods) — эксклюзивно!\n"
        "• Более 15 известных брендов снеков\n"
        "• Ведущие производители напитков\n\n"
        "🚚 <b>Логистика:</b>\n"
        "• Собственный склад 500м²\n"
        "• Доставка по Алматы каждый день\n"
        "• Современная система учета\n\n"
        "👥 <b>Команда:</b>\n"
        "Профессиональных торговых представителей\n\n"
        "💪 <b>Почему выбирают нас:</b>\n"
        "✅ Широкий ассортимент всегда в наличии\n"
        "✅ Конкурентные цены от производителя\n"
        "✅ Гибкие условия для постоянных клиентов\n"
        "✅ Быстрая доставка\n"
        "✅ Индивидуальный подход к каждому клиенту\n"
        "✅ Профессиональная поддержка",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == "our_products")
async def callback_our_products(callback: types.CallbackQuery):
    """Наш ассортимент"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Условия работы", callback_data="work_terms")],
        [InlineKeyboardButton(text="📞 Контакты", callback_data="contacts")],
        [InlineKeyboardButton(text="✅ Хочу начать работать!", callback_data="start_registration")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_start")]
    ])
    
    await callback.message.edit_text(
        "📦 <b>Наш ассортимент</b>\n\n"
        "🍿 <b>ПОПКОРН (наш ХИТ!):</b>\n"
        "• HAPPY CORN — официальный дистрибьютор\n"
        "• 15+ вкусов\n"
        "• Разные форматы: 700г, 100г, 200г, коробки\n"
        "• Маржа для вас: до 60%!\n\n"
        "🥔 <b>ЧИПСЫ:</b>\n"
        "• Happy Crisp, Real Chips\n"
        "• Papa Nachos, GRAMZZ\n"
        "• И другие популярные бренды\n\n"
        "🍪 <b>СНЕКИ И БАТОНЧИКИ:</b>\n"
        "• Здоровый Перекус\n"
        "• Ever GO, Хлебцы\n"
        "🥤 <b>НАПИТКИ:</b>\n"
        "• Живой Квас, Витаминизированая вода\n"
        "• NITRO Fresh, NITRO энергетики\n"
        "🥐 <b>ВЫПЕЧКА:</b>\n"
        "• Круассаны\n"
        "• Кексы, трубочки\n"
        "• Всегда Свежая и вкусная\n\n"
        "💡 <b>Постоянно добавляем новинки!</b>\n"
        "Следим за трендами и предлагаем только то, что продается.",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == "work_terms")
async def callback_work_terms(callback: types.CallbackQuery):
    """Условия работы"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Связаться с менеджером", callback_data="contacts")],
        [InlineKeyboardButton(text="✅ Всё понятно, регистрируюсь!", callback_data="start_registration")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_start")]
    ])
    
    await callback.message.edit_text(
        "💰 <b>Условия работы с HappySnack</b>\n\n"
        "💳 <b>КРЕДИТНЫЙ ЛИМИТ:</b>\n"
        "• Новым клиентам: до 500,000₸\n"
        "• Постоянным клиентам: индивидуально\n"
        "• Без залогов и сложных процедур\n\n"
        "📅 <b>ОТСРОЧКА ПЛАТЕЖА:</b>\n"
        "• Стандарт: 14 дней\n"
        "• Для постоянных: до 30 дней\n\n"
        "💵 <b>СКИДКИ:</b>\n"
        "• Персональные скидки от 5%\n"
        "• Акции на хиты продаж\n"
        "• Бонусы за объем\n\n"
        "🎁 <b>БОНУСНАЯ ПРОГРАММА:</b>\n"
        "• 2% от каждого заказа — бонусами\n"
        "• Оплачивайте до 20% заказа бонусами\n"
        "• Бонусы не сгорают 6 месяцев\n\n"
        "🚚 <b>ДОСТАВКА:</b>\n"
        "• По Алматы — бесплатно от 10,000₸\n"
        "• Доставка каждый день\n"
        "• Удобное время по договоренности\n\n"
        "📦 <b>МИНИМАЛЬНЫЙ ЗАКАЗ:</b>\n"
        "• От 20,000₸\n\n"
        "🤝 <b>ПОДДЕРЖКА:</b>\n"
        "• Личный менеджер\n"
        "• AI-ассистент 24/7 в этом боте\n"
        "• Помощь с выкладкой и продажами\n\n"
        "❓ <b>Остались вопросы?</b>\n"
        "Свяжитесь с нашим менеджером — всё расскажем!",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == "contacts")
async def callback_contacts(callback: types.CallbackQuery):
    """Контакты"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Готов работать!", callback_data="start_registration")],
        [InlineKeyboardButton(text="◀️ В главное меню", callback_data="back_to_start")]
    ])
    
    await callback.message.edit_text(
        "📞 <b>Контакты HappySnack</b>\n\n"
        "📱 <b>Телефон:</b>\n"
        "+7 XXX XXX XX XX\n"
        "(звонки, WhatsApp)\n\n"
        "📧 <b>Email:</b>\n"
        "info@happysnack.kz\n\n"
        "📍 <b>Адрес склада:</b>\n"
        "г. Алматы, ул. ...\n"
        "(самовывоз возможен)\n\n"
        "💬 <b>Telegram:</b>\n"
        "@YourManager\n\n"
        "🕐 <b>Режим работы:</b>\n"
        "Пн-Пт: 9:00 - 18:00\n"
        "Сб: 9:00 - 15:00\n"
        "Вс: Выходной\n\n"
        "🤖 <b>AI-ассистент в этом боте работает 24/7!</b>\n"
        "После регистрации можете задавать любые вопросы.",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_start")
async def callback_back_to_start(callback: types.CallbackQuery):
    """Возврат в главное меню"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏢 О компании HappySnack", callback_data="about_company")],
        [InlineKeyboardButton(text="📦 Что мы предлагаем", callback_data="our_products")],
        [InlineKeyboardButton(text="💰 Условия работы", callback_data="work_terms")],
        [InlineKeyboardButton(text="📞 Контакты", callback_data="contacts")],
        [InlineKeyboardButton(text="✅ Хочу начать работать!", callback_data="start_registration")]
    ])
    
    await callback.message.edit_text(
        "👋 <b>HappySnack B2B Shop</b>\n\n"
        "🏪 Крупный дистрибьютор снеков и напитков в Казахстане\n\n"
        "👇 Выберите что вас интересует:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

# ============================================
# РЕГИСТРАЦИЯ
# ============================================

@dp.callback_query(F.data == "start_registration")
async def start_registration(callback: types.CallbackQuery, state: FSMContext):
    """Начало регистрации - показываем форму"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Заполнить форму", callback_data="fill_registration_form")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_registration")]
    ])
    
    await callback.message.answer(
        "📝 <b>Регистрация нового клиента</b>\n\n"
        "Для регистрации вам нужно будет указать:\n"
        "• Название компании\n"
        "• БИН/ИИН\n"
        "• Адрес магазина/склада\n"
        "• Контактный телефон\n\n"
        "⏱ Это займет ~2 минуты\n\n"
        "Готовы начать?",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == "fill_registration_form")
async def fill_registration_form(callback: types.CallbackQuery, state: FSMContext):
    """Начинаем заполнение формы"""
    await callback.message.answer(
        "1️⃣ <b>Шаг 1 из 4</b>\n\n"
        "Введите <b>название вашей компании</b>:\n\n"
        "<i>Например: ТОО \"Продукты Алматы\"</i>\n\n"
        "Для отмены используйте /cancel",
        parse_mode="HTML"
    )
    await state.set_state(RegistrationStates.waiting_for_company_name)
    await callback.answer()

@dp.callback_query(F.data == "cancel_registration")
async def cancel_registration(callback: types.CallbackQuery, state: FSMContext):
    """Отмена регистрации"""
    await state.clear()
    await callback.message.answer(
        "❌ Регистрация отменена.\n\n"
        "Если передумаете - используйте /start"
    )
    await callback.answer()

@dp.message(RegistrationStates.waiting_for_company_name)
async def process_company_name(message: types.Message, state: FSMContext):
    """Получаем название компании"""
    await state.update_data(company_name=message.text)
    
    await message.answer(
        "2️⃣ <b>Шаг 2 из 4</b>\n\n"
        "Введите <b>БИН/ИИН</b> вашей компании:\n\n"
        "<i>Например: 123456789012</i>",
        parse_mode="HTML"
    )
    await state.set_state(RegistrationStates.waiting_for_bin)

@dp.message(RegistrationStates.waiting_for_bin)
async def process_bin(message: types.Message, state: FSMContext):
    """Получаем БИН"""
    await state.update_data(bin_iin=message.text)
    
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
        "<i>Например: +7 777 123 45 67</i>",
        parse_mode="HTML"
    )
    await state.set_state(RegistrationStates.waiting_for_contact)

@dp.message(RegistrationStates.waiting_for_contact)
async def process_contact(message: types.Message, state: FSMContext):
    """Завершаем регистрацию"""
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
        
        # Создаём клиента
        client = Client(
            user_id=user.id,
            company_name=data['company_name'],
            bin_iin=data['bin_iin'],
            address=data['address'],
            phone=message.text,
            status="pending",
            credit_limit=500000.0,
            payment_delay_days=14,
            discount_percent=0.0,
            bonus_balance=0.0,
            debt=0.0
        )
        db.add(client)
        db.commit()
        
        await state.clear()
        
        await message.answer(
            "✅ <b>Регистрация успешно завершена!</b>\n\n"
            "⏳ Ваша заявка отправлена на рассмотрение.\n\n"
            "Мы проверим данные и свяжемся с вами в течение 24 часов.\n\n"
            "Спасибо за интерес к HappySnack! 🎉",
            parse_mode="HTML"
        )
        
        # Уведомляем админов С TELEGRAM ID
        for admin_id in settings.admin_ids:
            try:
                await bot.send_message(
                    admin_id,
                    f"🆕 <b>Новая заявка на регистрацию!</b>\n\n"
                    f"👤 <b>Telegram ID: <code>{message.from_user.id}</code></b>\n"
                    f"Username: @{message.from_user.username or 'нет'}\n"
                    f"Имя: {message.from_user.full_name}\n\n"
                    f"🏢 Компания: {data['company_name']}\n"
                    f"📋 БИН: {data['bin_iin']}\n"
                    f"📍 Адрес: {data['address']}\n"
                    f"📞 Телефон: {message.text}",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"Registration error: {e}")
        await message.answer(
            "❌ Произошла ошибка при регистрации.\n\n"
            "Попробуйте позже или свяжитесь с нами:\n"
            "📞 +7 XXX XXX XX XX"
        )
        await state.clear()
    finally:
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

@dp.callback_query(F.data == "open_admin_panel")
async def callback_open_admin_panel(callback: types.CallbackQuery):
    """Открыть веб-дашборд"""
    await callback.message.answer(
        "👔 <b>Веб-дашборд администратора</b>\n\n"
        f"Откройте в браузере:\n{settings.API_URL}/static/admin/index.html\n\n"
        "Там вы можете:\n"
        "• Управлять клиентами\n"
        "• Просматривать заказы\n"
        "• Редактировать товары\n"
        "• Настраивать систему\n"
        "• Смотреть статистику AI",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_settings")
async def callback_admin_settings(callback: types.CallbackQuery):
    """Настройки"""
    await callback.message.answer(
        "⚙️ <b>Настройки системы</b>\n\n"
        "Для управления настройками используйте веб-дашборд:\n"
        f"{settings.API_URL}/static/admin/index.html\n\n"
        "Там вы можете изменить:\n"
        "• Бонусы\n"
        "• Скидки\n"
        "• Кредитные лимиты\n"
        "• Отсрочку платежа\n"
        "• И многое другое",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: types.CallbackQuery):
    """Статистика"""
    db = SessionLocal()
    
    total_clients = db.query(Client).count()
    active_clients = db.query(Client).filter(Client.status == "active").count()
    pending_clients = db.query(Client).filter(Client.status == "pending").count()
    
    total_orders = db.query(Order).count()
    today_orders = db.query(Order).filter(
        func.date(Order.created_at) == datetime.utcnow().date()
    ).count()
    
    total_revenue = db.query(func.sum(Order.final_total)).scalar() or 0
    
    db.close()
    
    await callback.message.answer(
        "📊 <b>Статистика системы</b>\n\n"
        f"👥 <b>Клиенты:</b>\n"
        f"• Всего: {total_clients}\n"
        f"• Активных: {active_clients}\n"
        f"• На модерации: {pending_clients}\n\n"
        f"📦 <b>Заказы:</b>\n"
        f"• Всего: {total_orders}\n"
        f"• Сегодня: {today_orders}\n\n"
        f"💰 <b>Выручка:</b>\n"
        f"• Всего: {total_revenue:,.0f}₸",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_clients")
async def callback_admin_clients(callback: types.CallbackQuery):
    """Список клиентов"""
    db = SessionLocal()
    
    clients = db.query(Client).order_by(Client.id.desc()).limit(10).all()
    
    if not clients:
        await callback.message.answer("Клиенты не найдены.")
        await callback.answer()
        db.close()
        return
    
    text = "👥 <b>Последние 10 клиентов:</b>\n\n"
    
    for c in clients:
        status_emoji = {"pending": "⏳", "active": "✅", "blocked": "🚫"}.get(c.status, "❓")
        text += f"{status_emoji} <b>{c.company_name}</b>\n"
        text += f"   БИН: {c.bin_iin or '-'}\n"
        text += f"   Баланс: {c.bonus_balance:,.0f}₸ | Долг: {c.debt:,.0f}₸\n\n"
    
    text += f"🌐 Полный список в веб-дашборде:\n{settings.API_URL}/static/admin/index.html"
    
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()
    db.close()

@dp.callback_query(F.data == "admin_orders")
async def callback_admin_orders(callback: types.CallbackQuery):
    """Список заказов"""
    db = SessionLocal()
    
    orders = db.query(Order).order_by(Order.created_at.desc()).limit(10).all()
    
    if not orders:
        await callback.message.answer("Заказы не найдены.")
        await callback.answer()
        db.close()
        return
    
    text = "📦 <b>Последние 10 заказов:</b>\n\n"
    
    for o in orders:
        status_emoji = {
            "new": "🆕", "confirmed": "✅", "preparing": "📦",
            "delivering": "🚚", "delivered": "✔️", "cancelled": "❌"
        }.get(o.status, "❓")
        
        text += f"{status_emoji} <b>{o.order_number}</b>\n"
        text += f"   Сумма: {o.final_total:,.0f}₸\n"
        text += f"   Дата: {o.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
    
    text += f"🌐 Полный список в веб-дашборде:\n{settings.API_URL}/static/admin/index.html"
    
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()
    db.close()

# ============================================
# AI SALES ASSISTANT
# ============================================

@dp.message(F.text, ~F.text.startswith('/'))
async def handle_text_message(message: types.Message, state: FSMContext):
    """Обрабатываем все текстовые сообщения через AI"""
    
    # ПРОВЕРЯЕМ СОСТОЯНИЕ FSM - НЕ МЕШАЕМ РЕГИСТРАЦИИ!
    current_state = await state.get_state()
    if current_state is not None:
        # Пользователь в процессе регистрации - не мешаем
        return
    
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(
            User.telegram_id == message.from_user.id
        ).first()
        
        if not user:
            await message.answer(
                "❌ Вы не зарегистрированы.\n"
                "Используйте /start для начала."
            )
            return
        
        # Админы и менеджеры не используют AI для текста
        if user.role in ["admin", "manager"]:
            return
        
        client = db.query(Client).filter(Client.user_id == user.id).first()
        
        if not client:
            await message.answer(
                "❌ Профиль клиента не найден.\n"
                "Используйте /start для регистрации."
            )
            return
        
        if client.status != "active":
            await message.answer(
                "⏳ Ваш аккаунт ожидает одобрения администратором."
            )
            return
        
        # Показываем что бот печатает
        await bot.send_chat_action(message.chat.id, "typing")
        
        # Отправляем в AI
        try:
            response = await sales_assistant.handle_message(
                message.text,
                client.id,
                db
            )
            
            # Логируем диалог
            from models.ai_log import AIConversation
            conversation = AIConversation(
                client_id=client.id,
                user_message=message.text,
                ai_response=response
            )
            db.add(conversation)
            db.commit()
            
            await message.answer(response, parse_mode="HTML")
            
        except Exception as e:
            logger.error(f"AI error: {e}")
            await message.answer(
                "🤖 Извините, временные технические проблемы.\n"
                "Попробуйте позже или свяжитесь с менеджером:\n"
                "📞 +7 XXX XXX XX XX"
            )
            
    finally:
        db.close()

# ============================================
# ДОПОЛНИТЕЛЬНЫЕ CALLBACK HANDLERS
# ============================================

@dp.callback_query(F.data == "my_orders")
async def callback_my_orders(callback: types.CallbackQuery):
    """Мои заказы"""
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
    
    if not user:
        await callback.answer("Ошибка: пользователь не найден")
        db.close()
        return
    
    client = db.query(Client).filter(Client.user_id == user.id).first()
    if not client:
        await callback.answer("Ошибка: клиент не найден")
        db.close()
        return
    
    orders = db.query(Order).filter(
        Order.client_id == client.id
    ).order_by(Order.created_at.desc()).limit(10).all()
    
    if not orders:
        await callback.message.answer("У вас пока нет заказов.")
        await callback.answer()
        db.close()
        return
    
    text = "📦 <b>Ваши заказы:</b>\n\n"
    
    for o in orders:
        status_text = {
            "new": "Новый", "confirmed": "Подтвержден",
            "preparing": "Готовится", "delivering": "В доставке",
            "delivered": "Доставлен", "cancelled": "Отменен"
        }.get(o.status, o.status)
        
        text += f"🔹 <b>{o.order_number}</b>\n"
        text += f"   Сумма: {o.final_total:,.0f}₸\n"
        text += f"   Статус: {status_text}\n"
        text += f"   Дата: {o.created_at.strftime('%d.%m.%Y')}\n\n"
    
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()
    db.close()

@dp.callback_query(F.data == "profile")
async def callback_profile(callback: types.CallbackQuery):
    """Профиль клиента"""
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
    
    if not user:
        await callback.answer("Ошибка: пользователь не найден")
        db.close()
        return
    
    client = db.query(Client).filter(Client.user_id == user.id).first()
    if not client:
        await callback.answer("Ошибка: клиент не найден")
        db.close()
        return
    
    text = f"👤 <b>Профиль клиента</b>\n\n"
    text += f"🏢 Компания: {client.company_name}\n"
    text += f"📋 БИН/ИИН: {client.bin_iin or '-'}\n"
    text += f"📍 Адрес: {client.address or '-'}\n"
    text += f"📞 Телефон: {client.phone or '-'}\n\n"
    text += f"💰 Бонусный баланс: {client.bonus_balance:,.0f}₸\n"
    text += f"💳 Кредитный лимит: {client.credit_limit:,.0f}₸\n"
    text += f"📊 Текущий долг: {client.debt:,.0f}₸\n"
    text += f"✨ Доступно: {(client.credit_limit - client.debt):,.0f}₸\n\n"
    text += f"🎁 Персональная скидка: {client.discount_percent}%\n"
    text += f"📅 Отсрочка платежа: {client.payment_delay_days} дней"
    
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()
    db.close()

@dp.callback_query(F.data == "contact_manager")
async def callback_contact_manager(callback: types.CallbackQuery):
    """Связаться с менеджером"""
    await callback.message.answer(
        "📞 <b>Связаться с менеджером</b>\n\n"
        "📱 Телефон: +7 700 080 4848\n"
        "💬 Telegram: @YourManager\n"
        "📧 Email: info@happysnack.kz\n\n"
        "🕐 Режим работы:\n"
        "Пн-Пт: 9:00 - 18:00\n"
        "Сб-Вс: Выходной",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_main")
async def callback_back_to_main(callback: types.CallbackQuery):
    """Вернуться в главное меню"""
    await callback.message.answer("Используйте /start для перехода в главное меню")
    await callback.answer()

# ============================================
# ЗАПУСК БОТА
# ============================================

async def main():
    logger.info("🤖 Starting HappySnack Bot...")
    logger.info(f"Bot username: @{(await bot.get_me()).username}")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Bot stopped with error: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())