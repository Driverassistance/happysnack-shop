# backend/handlers/__init__.py

from . import common_handlers
from . import registration_handlers
from . import catalog_handlers
from . import cart_handlers
from . import order_handlers
from . import profile_handlers
from . import admin_handlers
from . import manager_handlers
from . import ai_handlers

__all__ = [
    "common_handlers",
    "registration_handlers",
    "catalog_handlers",
    "cart_handlers",
    "order_handlers",
    "profile_handlers",
    "admin_handlers",
    "manager_handlers",
    "ai_handlers",
]
