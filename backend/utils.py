"""
Вспомогательные функции
"""
import hashlib
import hmac
from urllib.parse import parse_qs
from config import settings
from datetime import datetime

def verify_telegram_webapp_data(init_data: str) -> dict:
    """
    Проверяет подлинность данных от Telegram WebApp
    
    Args:
        init_data: Строка InitData от Telegram
        
    Returns:
        dict с данными пользователя или None если невалидно
    """
    try:
        # Парсим данные
        parsed = parse_qs(init_data)
        
        # Извлекаем hash
        received_hash = parsed.get('hash', [None])[0]
        if not received_hash:
            return None
        
        # Удаляем hash из данных для проверки
        data_check_string_parts = []
        for key in sorted(parsed.keys()):
            if key != 'hash':
                values = parsed[key]
                for value in values:
                    data_check_string_parts.append(f"{key}={value}")
        
        data_check_string = '\n'.join(data_check_string_parts)
        
        # Вычисляем secret key
        secret_key = hmac.new(
            key=b"WebAppData",
            msg=settings.BOT_TOKEN.encode(),
            digestmod=hashlib.sha256
        ).digest()
        
        # Вычисляем hash
        calculated_hash = hmac.new(
            key=secret_key,
            msg=data_check_string.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        # Сравниваем
        if calculated_hash != received_hash:
            return None
        
        # Возвращаем данные пользователя
        import json
        user_data = json.loads(parsed.get('user', ['{}'])[0])
        
        return {
            'telegram_id': user_data.get('id'),
            'username': user_data.get('username'),
            'first_name': user_data.get('first_name'),
            'last_name': user_data.get('last_name')
        }
        
    except Exception as e:
        print(f"Error verifying webapp data: {e}")
        return None

def generate_order_number() -> str:
    """Генерирует уникальный номер заказа"""
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d%H%M%S")
    return f"ORD-{timestamp}"

def calculate_bonus_amount(total: float, bonus_percent: float) -> float:
    """Рассчитывает сумму бонусов к начислению"""
    return round(total * (bonus_percent / 100), 2)

def calculate_personal_price(base_price: float, discount_percent: float) -> float:
    """Рассчитывает персональную цену с учетом скидки"""
    discount = base_price * (discount_percent / 100)
    return round(base_price - discount, 2)