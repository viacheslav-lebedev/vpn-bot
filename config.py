import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot.db")
    
    # Payments
    YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
    YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
    
    # Outline VPN
    OUTLINES_API_URL = os.getenv("OUTLINES_API_URL")
    OUTLINES_API_KEY = os.getenv("OUTLINES_API_KEY")
    OUTLINES_SERVER_ID = os.getenv("OUTLINES_SERVER_ID", "default")
    
    # Tariffs
    TARIFFS = {
        "trial": {"name": "Пробный", "price": 0, "days": 30},
        "1month": {"name": "1 месяц", "price": 150, "days": 30},
        "3months": {"name": "3 месяца", "price": 400, "days": 90},
        "6months": {"name": "6 месяцев", "price": 600, "days": 180},
    }
