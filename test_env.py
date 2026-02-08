import os
from dotenv import load_dotenv

load_dotenv()

print("=== Проверка .env ===")
print(f"BOT_TOKEN: {os.getenv('BOT_TOKEN')}")
print(f"Длина токена: {len(os.getenv('BOT_TOKEN', ''))}")
print(f"ADMIN_ID: {os.getenv('ADMIN_ID')}")
print(f"DATABASE_URL: {os.getenv('DATABASE_URL')}")
