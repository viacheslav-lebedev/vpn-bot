import sys
sys.path.append('.')
import config
import database
from sqlalchemy.orm import Session

print("🧪 Тест платежной системы:")
print(f"ЮKassa Shop ID: {config.Config.YOOKASSA_SHOP_ID}")

# Проверка БД
db = database.SessionLocal()
try:
    # Проверяем таблицы
    from sqlalchemy import inspect
    inspector = inspect(db.bind)
    tables = inspector.get_table_names()
    print(f"✅ Таблицы в БД: {tables}")
    
    # Проверяем пользователей
    users = db.query(database.User).count()
    print(f"✅ Пользователей: {users}")
    
    # Проверяем платежи
    payments = db.query(database.Payment).count()
    print(f"✅ Платежей: {payments}")
    
finally:
    db.close()

# Проверка ЮKassa конфигурации
try:
    import yookassa
    yookassa.Configuration.account_id = config.Config.YOOKASSA_SHOP_ID
    yookassa.Configuration.secret_key = config.Config.YOOKASSA_SECRET_KEY
    print("✅ ЮKassa настроена корректно")
except Exception as e:
    print(f"❌ ЮKassa: {e}")
