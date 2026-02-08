import requests
import json

API_URL = "https://45.135.182.168:4751/XTx2Eq4Mc4yQxm6nIBEpLw"

print("🔧 Тестирование Outline API")
print("=" * 50)

# 1. Проверка подключения
print("1. Проверка подключения...")
try:
    response = requests.get(f"{API_URL}/access-keys", verify=False, timeout=10)
    print(f"   Статус: {response.status_code}")
    print(f"   Ключей в системе: {len(response.json().get('accessKeys', []))}")
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

# 2. Попробуем создать ключ
print("\n2. Создание тестового ключа...")
try:
    data = {"name": "Test Key from Script"}
    response = requests.post(
        f"{API_URL}/access-keys",
        json=data,
        verify=False,
        timeout=10
    )
    print(f"   Статус: {response.status_code}")
    print(f"   Ответ: {response.text[:200]}")
    
    if response.status_code == 200:
        key_data = response.json()
        print(f"   ✅ Ключ создан!")
        print(f"   ID: {key_data.get('id')}")
        print(f"   Ключ: {key_data.get('accessUrl', '')[:80]}...")
    else:
        print("   ❌ Не удалось создать ключ")
        
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

# 3. Проверим лимиты
print("\n3. Проверка сервера...")
try:
    response = requests.get(f"{API_URL}/server", verify=False, timeout=10)
    if response.status_code == 200:
        server_info = response.json()
        print(f"   Имя: {server_info.get('name', 'N/A')}")
        print(f"   Местоположение: {server_info.get('location', 'N/A')}")
        print(f"   Порт для новых ключей: {server_info.get('portForNewAccessKeys', 'N/A')}")
except Exception as e:
    print(f"   ❌ Ошибка: {e}")

print("\n💡 Возможные проблемы:")
print("1. Достигнут лимит ключей на сервере")
print("2. Проблемы с портами (нужен свободный порт)")
print("3. Ошибка в API")
