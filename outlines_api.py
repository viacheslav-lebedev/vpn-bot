import requests
import json
import config
from typing import Optional, Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OutlinesAPI:
    """Класс для работы с Outline VPN API"""
    
    def __init__(self):
        self.base_url = config.Config.OUTLINES_API_URL.rstrip('/')
        self.api_key = config.Config.OUTLINES_API_KEY
        self.server_id = config.Config.OUTLINES_SERVER_ID
        
        # Настройки для самоподписанных сертификатов
        self.verify_ssl = False  # Если у вас самоподписанный сертификат
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"Outline API инициализирован: {self.base_url}")
    
    def create_key(self, name: str = "VPN Key", limit_gb: int = 10) -> Optional[Dict]:
        """
        Создать новый ключ в Outline
        Returns: {'id': 'key_id', 'accessUrl': 'ss://...', 'name': '...'}
        """
        try:
            url = f"{self.base_url}/{self.server_id}/access-keys"
            
            data_limit = limit_gb * 1024 * 1024 * 1024  # Конвертируем ГБ в байты
            
            payload = {
                "name": name,
                "limit": {"bytes": data_limit}
            }
            
            response = requests.post(
                url, 
                headers=self.headers, 
                json=payload, 
                verify=self.verify_ssl,
                timeout=30
            )
            
            if response.status_code == 201:
                key_data = response.json()
                logger.info(f"Создан ключ: {name}, ID: {key_data.get('id')}")
                return key_data
            else:
                logger.error(f"Ошибка создания ключа: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Исключение при создании ключа: {e}")
            return None
    
    def get_all_keys(self) -> List[Dict]:
        """Получить все ключи"""
        try:
            url = f"{self.base_url}/{self.server_id}/access-keys"
            response = requests.get(url, headers=self.headers, verify=self.verify_ssl, timeout=30)
            
            if response.status_code == 200:
                return response.json().get('accessKeys', [])
            else:
                logger.error(f"Ошибка получения ключей: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Исключение при получении ключей: {e}")
            return []
    
    def delete_key(self, key_id: str) -> bool:
        """Удалить ключ"""
        try:
            url = f"{self.base_url}/{self.server_id}/access-keys/{key_id}"
            response = requests.delete(url, headers=self.headers, verify=self.verify_ssl, timeout=30)
            
            if response.status_code == 204:
                logger.info(f"Ключ удален: {key_id}")
                return True
            else:
                logger.error(f"Ошибка удаления ключа: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Исключение при удалении ключа: {e}")
            return False
    
    def get_key(self, key_id: str) -> Optional[Dict]:
        """Получить информацию о конкретном ключе"""
        try:
            url = f"{self.base_url}/{self.server_id}/access-keys/{key_id}"
            response = requests.get(url, headers=self.headers, verify=self.verify_ssl, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Ошибка получения ключа {key_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Исключение при получении ключа: {e}")
            return None
    
    def update_key_limit(self, key_id: str, limit_gb: int) -> bool:
        """Обновить лимит трафика для ключа"""
        try:
            url = f"{self.base_url}/{self.server_id}/access-keys/{key_id}"
            
            data_limit = limit_gb * 1024 * 1024 * 1024
            
            payload = {
                "limit": {"bytes": data_limit}
            }
            
            response = requests.put(
                url, 
                headers=self.headers, 
                json=payload, 
                verify=self.verify_ssl,
                timeout=30
            )
            
            if response.status_code == 204:
                logger.info(f"Лимит обновлен для ключа {key_id}: {limit_gb}GB")
                return True
            else:
                logger.error(f"Ошибка обновления лимита: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Исключение при обновлении лимита: {e}")
            return False
    
    def get_server_info(self) -> Optional[Dict]:
        """Получить информацию о сервере"""
        try:
            url = f"{self.base_url}/{self.server_id}/server"
            response = requests.get(url, headers=self.headers, verify=self.verify_ssl, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Ошибка получения информации о сервере: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Исключение при получении информации о сервере: {e}")
            return None

# Создаем глобальный экземпляр API
outlines_api = OutlinesAPI()

def test_connection():
    """Тест подключения к Outline"""
    try:
        info = outlines_api.get_server_info()
        if info:
            logger.info(f"✅ Подключение к Outline успешно!")
            logger.info(f"   Сервер: {info.get('name', 'Unknown')}")
            logger.info(f"   Ключей создано: {len(outlines_api.get_all_keys())}")
            return True
        else:
            logger.error("❌ Не удалось подключиться к Outline")
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка теста подключения: {e}")
        return False

if __name__ == "__main__":
    # Тест при запуске напрямую
    test_connection()
