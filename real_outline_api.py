import requests
import json

class RealOutlineAPI:
    def __init__(self, api_url, api_key):
        """
        api_url: https://ваш_сервер:12345/abcdef1234567890
        api_key: ваш_32_символьный_api_ключ
        """
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        print(f"🔗 Подключение к Outline: {self.api_url[:30]}...")
    
    def test_connection(self):
        """Проверить подключение к API"""
        try:
            response = requests.get(
                f"{self.api_url}/server",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                print("✅ Подключение к Outline успешно!")
                server_info = response.json()
                print(f"📡 Сервер: {server_info.get('name', 'N/A')}")
                print(f"📍 Местоположение: {server_info.get('location', 'N/A')}")
                return True
            else:
                print(f"❌ Ошибка API: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return False
    
    def create_key(self, name, data_limit_bytes=None):
        """Создать настоящий VPN ключ"""
        data = {"name": name}
        if data_limit_bytes:
            data["data_limit"] = {"bytes": data_limit_bytes}
        
        try:
            response = requests.post(
                f"{self.api_url}/access-keys",
                headers=self.headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 201:
                key_data = response.json()
                print(f"✅ Создан ключ: {name}")
                return {
                    'id': key_data['id'],
                    'name': name,
                    'access_url': key_data['accessUrl'],  # Настоящий рабочий ключ!
                    'password': key_data.get('password', ''),
                    'port': key_data.get('port', ''),
                    'method': key_data.get('method', '')
                }
            else:
                print(f"❌ Ошибка создания ключа: {response.status_code}")
                print(f"Ответ: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Исключение при создании ключа: {e}")
            return None
    
    def delete_key(self, key_id):
        """Удалить ключ"""
        try:
            response = requests.delete(
                f"{self.api_url}/access-keys/{key_id}",
                headers=self.headers,
                timeout=10
            )
            success = response.status_code == 204
            if success:
                print(f"✅ Удален ключ: {key_id}")
            return success
        except Exception as e:
            print(f"❌ Ошибка удаления ключа: {e}")
            return False
    
    def list_keys(self):
        """Получить список всех ключей"""
        try:
            response = requests.get(
                f"{self.api_url}/access-keys",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data.get('accessKeys', [])
            return []
        except Exception as e:
            print(f"❌ Ошибка получения ключей: {e}")
            return []
    
    def get_key_metrics(self, key_id):
        """Получить статистику использования ключа"""
        try:
            response = requests.get(
                f"{self.api_url}/access-keys/{key_id}/metrics",
                headers=self.headers,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None

# ===== ТЕСТ =====
if __name__ == "__main__":
    print("🔧 Тест Outline API")
    print("=" * 50)
    
    # Введите ваши данные здесь:
    API_URL = input("Введите API URL Outline сервера: ").strip()
    API_KEY = input("Введите API ключ: ").strip()
    
    if not API_URL or not API_KEY:
        print("❌ Данные не введены!")
        exit()
    
    outline = RealOutlineAPI(API_URL, API_KEY)
    
    if outline.test_connection():
        print("\n📊 Создаем тестовый ключ...")
        test_key = outline.create_key("Тестовый ключ от бота")
        
        if test_key:
            print(f"\n✅ Ключ создан успешно!")
            print(f"🔑 Название: {test_key['name']}")
            print(f"🔗 Ключ для подключения:\n{test_key['access_url']}")
            
            print("\n📋 Список всех ключей:")
            keys = outline.list_keys()
            for key in keys:
                print(f"  • {key.get('name', 'Без имени')} - {key.get('id', 'N/A')}")
        else:
            print("❌ Не удалось создать ключ")
    else:
        print("❌ Не удалось подключиться к Outline серверу")
        print("\n💡 Проверьте:")
        print("1. API URL и ключ")
        print("2. Доступность сервера из сети")
        print("3. Брандмауэр и порты")
