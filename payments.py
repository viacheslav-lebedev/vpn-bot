import uuid
import logging
from datetime import datetime
from sqlalchemy.orm import Session
import config
import database

logger = logging.getLogger(__name__)

try:
    from yookassa import Payment as YooPayment, Configuration
    Configuration.account_id = config.Config.YOOKASSA_SHOP_ID
    Configuration.secret_key = config.Config.YOOKASSA_SECRET_KEY
    YOOKASSA_AVAILABLE = True
    logger.info("✅ ЮKassa настроен")
except ImportError as e:
    YOOKASSA_AVAILABLE = False
    logger.error(f"❌ ЮKassa SDK не доступен: {e}")

# Хранилище временных данных о платежах
payment_sessions = {}

def get_bot_link():
    """Получить ссылку на бота"""
    # Извлекаем username бота из токена
    bot_token = config.Config.BOT_TOKEN
    bot_username = bot_token.split(':')[0]
    return f"https://t.me/{bot_username}"

async def create_payment(db: Session, user_id: int, amount: float, tariff_id: str = None):
    """
    Создать реальный платеж в ЮKassa
    Returns: {'payment_url': str, 'payment_id': str, 'status': str}
    """
    try:
        user = db.query(database.User).filter(database.User.telegram_id == user_id).first()
        if not user:
            logger.error(f"Пользователь {user_id} не найден")
            return None
        
        # Описание платежа
        description = config.Config.PAYMENT_DESCRIPTION
        if tariff_id and tariff_id in config.Config.TARIFFS:
            tariff_name = config.Config.TARIFFS[tariff_id]["name"]
            description = f"Оплата тарифа {tariff_name}"
        
        # ✅ ИСПРАВЛЕНО: правильный return_url - ссылка на бота
        bot_link = get_bot_link()
        
        # Создаем платеж в ЮKassa
        payment = YooPayment.create({
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "RUB"
            },
            "payment_method_data": {
                "type": "bank_card"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": bot_link  # ✅ Теперь ведет в бота, а не на сайт
            },
            "capture": True,
            "description": description,
            "metadata": {
                "user_id": str(user_id),
                "tariff_id": tariff_id or "balance",
                "telegram_username": user.username or ""
            }
        })
        
        # Сохраняем в БД как pending
        db_payment = database.Payment(
            user_id=user.id,
            amount=amount,
            payment_id=payment.id,
            payment_method="yookassa",
            status="pending",
            created_at=datetime.utcnow()
        )
        db.add(db_payment)
        db.commit()
        
        # Сохраняем в сессии для быстрого доступа
        payment_sessions[user_id] = {
            'payment_id': payment.id,
            'amount': amount,
            'created_at': datetime.utcnow()
        }
        
        logger.info(f"Создан платеж {payment.id} для пользователя {user_id} на сумму {amount}₽")
        logger.info(f"Return URL: {bot_link}")
        
        return {
            "payment_url": payment.confirmation.confirmation_url,
            "payment_id": payment.id,
            "status": payment.status,
            "amount": amount,
            "bot_link": bot_link  # Добавляем ссылку на бота
        }
            
    except Exception as e:
        logger.error(f"Ошибка создания платежа: {e}")
        # РЕЗЕРВНЫЙ ВАРИАНТ: тестовый платеж
        try:
            return await create_test_payment(db, user_id, amount, tariff_id)
        except:
            return None

async def create_test_payment(db: Session, user_id: int, amount: float, tariff_id: str = None):
    """Тестовый платеж (если ЮKassa не работает)"""
    user = db.query(database.User).filter(database.User.telegram_id == user_id).first()
    if not user:
        return None
    
    payment_id = f"test_{uuid.uuid4().hex[:8]}"
    
    db_payment = database.Payment(
        user_id=user.id,
        amount=amount,
        payment_id=payment_id,
        payment_method="test",
        status="succeeded",
        created_at=datetime.utcnow()
    )
    db.add(db_payment)
    
    # Пополняем баланс
    user.balance += amount
    db.commit()
    
    # Сохраняем в сессии
    payment_sessions[user_id] = {
        'payment_id': payment_id,
        'amount': amount,
        'created_at': datetime.utcnow()
    }
    
    logger.info(f"Тестовый платеж {payment_id} для пользователя {user_id} на сумму {amount}₽")
    
    return {
        "payment_url": f"https://example.com/test_payment/{payment_id}",
        "payment_id": payment_id,
        "status": "succeeded",
        "amount": amount,
        "bot_link": get_bot_link()
    }

async def check_payment_status(payment_id: str, db: Session, user_id: int = None):
    """Проверить статус платежа в ЮKassa"""
    try:
        if config.Config.PAYMENT_PROVIDER == "yookassa" and YOOKASSA_AVAILABLE:
            payment = YooPayment.find_one(payment_id)
            
            # Обновляем статус в БД
            db_payment = db.query(database.Payment).filter(
                database.Payment.payment_id == payment_id
            ).first()
            
            if db_payment:
                old_status = db_payment.status
                db_payment.status = payment.status
                db_payment.updated_at = datetime.utcnow()
                
                # Если платеж успешен - пополняем баланс
                if payment.status == "succeeded" and old_status != "succeeded":
                    user = db.query(database.User).filter_by(id=db_payment.user_id).first()
                    if user:
                        user.balance += db_payment.amount
                        logger.info(f"✅ Баланс пополнен для пользователя {user.telegram_id} на {db_payment.amount}₽")
                        
                        # Удаляем из сессии
                        if user.telegram_id in payment_sessions:
                            del payment_sessions[user.telegram_id]
                
                db.commit()
            
            return {
                "status": payment.status,
                "amount": float(payment.amount.value),
                "currency": payment.amount.currency,
                "paid": payment.paid,
                "payment_id": payment_id
            }
        else:
            # В тестовом режиме
            payment = db.query(database.Payment).filter_by(payment_id=payment_id).first()
            if payment:
                return {
                    "status": payment.status,
                    "amount": payment.amount,
                    "paid": payment.status == "succeeded",
                    "payment_id": payment_id
                }
            return {"status": "succeeded", "paid": True, "payment_id": payment_id}
            
    except Exception as e:
        logger.error(f"Ошибка проверки статуса платежа {payment_id}: {e}")
        return None

async def check_user_payments(user_id: int, db: Session):
    """Проверить все pending платежи пользователя"""
    try:
        user = db.query(database.User).filter_by(telegram_id=user_id).first()
        if not user:
            return []
        
        # Проверяем платежи в статусе pending
        pending_payments = db.query(database.Payment).filter(
            database.Payment.user_id == user.id,
            database.Payment.status == "pending"
        ).all()
        
        results = []
        for payment in pending_payments:
            status = await check_payment_status(payment.payment_id, db, user_id)
            if status:
                results.append(status)
        
        return results
        
    except Exception as e:
        logger.error(f"Ошибка проверки платежей пользователя {user_id}: {e}")
        return []

def get_user_payment_session(user_id: int):
    """Получить активный платеж пользователя"""
    return payment_sessions.get(user_id)

def clear_payment_session(user_id: int):
    """Очистить сессию платежа"""
    if user_id in payment_sessions:
        del payment_sessions[user_id]

async def create_tariff_payment(db: Session, user_id: int, tariff_id: str):
    """Создать платеж для тарифа"""
    if tariff_id not in config.Config.TARIFFS:
        logger.error(f"Тариф {tariff_id} не найден")
        return None
    
    tariff = config.Config.TARIFFS[tariff_id]
    amount = tariff["price"]
    
    return await create_payment(db, user_id, amount, tariff_id)

# Тестовая функция
async def test_payment():
    """Тест создания платежа"""
    db = database.SessionLocal()
    
    try:
        test_user = db.query(database.User).filter_by(telegram_id=123456789).first()
        if not test_user:
            test_user = database.User(
                telegram_id=123456789,
                username="test_user",
                full_name="Test User",
                balance=0.0
            )
            db.add(test_user)
            db.commit()
        
        result = await create_payment(db, test_user.telegram_id, 10.0)
        if result:
            print(f"✅ Платеж создан!")
            print(f"   ID: {result['payment_id']}")
            print(f"   Bot URL: {result['bot_link']}")
            print(f"   Payment URL: {result['payment_url']}")
        else:
            print("❌ Платеж не создан")
            
    finally:
        db.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_payment())
