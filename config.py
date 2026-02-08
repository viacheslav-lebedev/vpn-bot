import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8518710020:AAHvXuuUlhMZExOvdzBSNklTKwziVFLYFQs")
    ADMIN_ID = int(os.getenv("ADMIN_ID", "1968521836"))
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot.db")
    
    # Payments - РЕАЛЬНЫЕ ПЛАТЕЖИ
    YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "1268613")
    YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "live_1W-BjdaH24ZmXjS3No3nLgys6NRSlurBfv0WI9ZDu5I")
    PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "yookassa")
    
    # Outlines VPN - ВАШ СЕРВЕР
    OUTLINES_API_URL = os.getenv("OUTLINES_API_URL", "https://45.135.182.168:443")
    OUTLINES_API_KEY = os.getenv("OUTLINES_API_KEY", "ваш_ключ_outlines")
    OUTLINES_SERVER_ID = os.getenv("OUTLINES_SERVER_ID", "default")
    
    # Тарифы
    TARIFFS = {
        "trial": {"name": "Пробный (30 дней)", "price": 0, "days": 30, "limit_gb": 5},
        "1day": {"name": "Дневной", "price": 10, "days": 1, "limit_gb": 2},
        "1month": {"name": "1 месяц", "price": 150, "days": 30, "limit_gb": 20},
        "3months": {"name": "3 месяца", "price": 400, "days": 90, "limit_gb": 50},
        "6months": {"name": "6 месяцев", "price": 600, "days": 180, "limit_gb": 100},
    }
    
    # Настройки платежей
    PAYMENT_SUCCESS_URL = "https://t.me/vpn_outline_shop_bot"
    PAYMENT_DESCRIPTION = "Оплата VPN услуг"
    SUPPORT_USERNAME = "IdazaneRenn"  # Ваш username для техподдержки

# Настройка ЮKassa
try:
    from yookassa import Configuration
    Configuration.account_id = Config.YOOKASSA_SHOP_ID
    Configuration.secret_key = Config.YOOKASSA_SECRET_KEY
    print(f"✅ ЮKassa настроен (Shop ID: {Config.YOOKASSA_SHOP_ID})")
except ImportError:
    print("⚠️ Библиотека yookassa не установлена")
