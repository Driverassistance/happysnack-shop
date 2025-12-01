# backend/test_import.py
import sys
import pathlib

print("--- НАЧАЛО ТЕСТА ---")

# Шаг 1: Симулируем настройку путей, как в финальном решении
try:
    PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(PROJECT_ROOT))
    print(f"✅ Корень проекта '{PROJECT_ROOT.name}' добавлен в sys.path.")
    print(f"Теперь sys.path начинается с: {sys.path[0]}")
except Exception as e:
    print(f"💥 Ошибка на шаге 1: {e}")
    sys.exit(1)

# Шаг 2: Пытаемся выполнить проблемный импорт
try:
    print("\n--- Попытка импорта 'from app.handlers import common_handlers' ---")
    from app.handlers import common_handlers
    print("✅ УСПЕХ! Модуль 'common_handlers' успешно импортирован.")
    print(f"   -> Тип импортированного объекта: {type(common_handlers)}")
except ImportError as e:
    print(f"💥 ПРОВАЛ! Получена ожидаемая ошибка ImportError: {e}")
except Exception as e:
    print(f"💥 ПРОВАЛ! Получена неожиданная ошибка: {e}")

print("\n--- КОНЕЦ ТЕСТА ---")
