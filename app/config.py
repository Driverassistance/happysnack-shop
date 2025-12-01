from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Telegram
    BOT_TOKEN: str
    WEBAPP_URL: str
    
    # Database
    DATABASE_URL: str = "sqlite:///./shop.db"
    
    # API
    SECRET_KEY: str
    API_URL: str = "http://localhost:8000"
    
    # Admin
    ADMIN_TELEGRAM_IDS: str
    ADMIN_TELEGRAM_ID: int
    CLAUDE_API_KEY: str = "dummy-key"
    
    class Config:
        env_file = ".env"
    
    @property
    def admin_ids(self) -> List[int]:
        """Парсим список ID администраторов"""
        return [int(x.strip()) for x in self.ADMIN_TELEGRAM_IDS.split(",")]

settings = Settings()