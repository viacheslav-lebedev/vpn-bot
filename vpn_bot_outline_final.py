import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import config
import requests
import random
import string
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# ===== НАСТРОЙКИ =====
ADMIN_IDS = config.Config.ADMIN_IDS
TARIFFS = config.Config.TARIFFS
OUTLINE_API_URL = "https://45.135.182.168:4751/XTx2Eq4Mc4yQxm6nIBEpLw"

# Отключаем предупреждения SSL
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ===== REAL OUTLINE API =====
def test_outline_connection():
    """Тест подключения к Outline"""
    try:
        response = requests.get(f"{OUTLINE_API_URL}/access-keys", verify=False, timeout=10)
        if response.status_code == 200:
            keys = response.json().get('accessKeys', [])
            return True, f"✅ Outline API доступен ({len(keys)} ключей)"
        else:
            return False, f"❌ Outline API недоступен (статус: {response.status_code})"
    except Exception as e:
        return False, f"❌ Ошибка подключения: {e}"

def create_outline_key(name):
    """Создать ключ в Outline - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        data = {"name": name}
        response = requests.post(
            f"{OUTLINE_API_URL}/access-keys",
            json=data,
            verify=False,
            timeout=10
        )
        
        # Outline возвращает 201 при успешном создании!
        if response.status_code in [200, 201]:  # Исправлено здесь!
            key_data = response.json()
            return {
                'success': True,
                'id': key_data['id'],
                'access_url': key_data['accessUrl'],
                'port': key_data.get('port'),
                'method': key_data.get('method', 'chacha20-ietf-poly1305'),
                'password': key_data.get('password', '')
            }
        else:
            return {
                'success': False,
                'error': f"API ошибка: {response.status_code}",
                'details': response.text[:200]
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f"Ошибка подключения: {str(e)}"
        }

def list_outline_keys():
    """Список ключей в Outline"""
    try:
        response = requests.get(f"{OUTLINE_API_URL}/access-keys", verify=False, timeout=10)
        if response.status_code == 200:
            return response.json().get('accessKeys', [])
        return []
    except:
        return []

# Проверяем подключение
connection_ok, connection_msg = test_outline_connection()
print(f"📡 {connection_msg}")

# ===== БАЗА ДАННЫХ =====
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    full_name = Column(String(200))
    balance = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    subscriptions = relationship("Subscription", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    keys = relationship("VPNKey", back_populates="user")

class Subscription(Base):
    __tablename__ = 'subscriptions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    tariff = Column(String(50))
    price = Column(Float)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    user = relationship("User", back_populates="subscriptions")

class Payment(Base):
    __tablename__ = 'payments'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    amount = Column(Float, nullable=False)
    payment_id = Column(String(100), unique=True)
    status = Column(String(20), default="pending")
    payment_method = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="payments")

class VPNKey(Base):
    __tablename__ = 'vpn_keys'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    key_id = Column(String(100))
    key = Column(String(500))
    name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="keys")

# Подключаемся к БД
engine = create_engine(config.Config.DATABASE_URL, echo=False)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===== ФУНКЦИИ =====
def is_admin(user_id):
    return user_id in ADMIN_IDS

def main_menu(user_id):
    keyboard = [
        [InlineKeyboardButton("💰 Пополнить баланс", callback_data="deposit")],
        [InlineKeyboardButton("📊 Мой баланс", callback_data="balance")],
        [InlineKeyboardButton("🔑 Мои ключи", callback_data="keys")],
        [InlineKeyboardButton("🛒 Купить тариф", callback_data="tariffs")],
    ]
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("👑 Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)

def get_or_create_user(db, telegram_id, username, full_name):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id, username=username, full_name=full_name)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def format_key_monospace(key_text, with_backticks=True):
    """Форматирование ключа в моноширинном виде"""
    if with_backticks:
        return f"```\n{key_text}\n```"
    else:
        # Альтернатива: используем <pre> тег для HTML
        return f"<pre>{key_text}</pre>"

# ===== ОСНОВНЫЕ ОБРАБОТЧИКИ =====
async def start(update: Update, context):
    db = next(get_db())
    user = update.effective_user
    db_user = get_or_create_user(db, user.id, user.username, user.full_name)
    
    outline_keys = list_outline_keys()
    
    text = (f"👋 Привет, {user.first_name}!\n"
            f"💰 Баланс: {db_user.balance} руб\n"
            f"🔐 {connection_msg}\n\n"
            f"Выберите действие:")
    
    await update.message.reply_text(text, reply_markup=main_menu(user.id))

async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    db = next(get_db())
    user = query.from_user
    db_user = get_or_create_user(db, user.id, user.username, user.full_name)
    
    if query.data == "admin_panel" and is_admin(user.id):
        outline_keys = list_outline_keys()
        text = (f"👑 <b>Админ-панель</b>\n\n"
                f"📊 Outline: {'✅ Работает' if connection_ok else '⚠️ Ошибка'}\n"
                f"🔑 Ключей в Outline: {len(outline_keys)}\n"
                f"👥 Пользователей: {db.query(User).count()}")
        
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("🔑 Outline ключи", callback_data="admin_outline_keys")],
            [InlineKeyboardButton("➕ Добавить баланс", callback_data="admin_add_balance")],
            [InlineKeyboardButton("🔄 Проверить Outline", callback_data="admin_check_outline")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main")]
        ]
        
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    elif query.data == "admin_check_outline" and is_admin(user.id):
        connection_ok, msg = test_outline_connection()
        outline_keys = list_outline_keys()
        await query.edit_message_text(
            f"🔄 <b>Проверка Outline:</b>\n\n{msg}\n"
            f"🔑 Ключей в системе: {len(outline_keys)}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")]])
        )
        return
    
    elif query.data == "admin_outline_keys" and is_admin(user.id):
        outline_keys = list_outline_keys()
        text = f"🔑 <b>Ключи в Outline:</b> ({len(outline_keys)})\n\n"
        for k in outline_keys[-10:]:  # Последние 10 ключей
            name = k.get('name', 'Без имени') or 'Без имени'
            port = k.get('port', 'N/A')
            text += f"• ID:{k.get('id')} - {name} (порт: {port})\n"
        
        if len(outline_keys) > 10:
            text += f"\n... и еще {len(outline_keys)-10} ключей"
        
        await query.edit_message_text(text, parse_mode="HTML", 
                                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")]]))
        return
    
    elif query.data == "admin_stats" and is_admin(user.id):
        total_users = db.query(User).count()
        total_payments = db.query(Payment).count()
        total_subs = db.query(Subscription).filter(Subscription.is_active == True).count()
        total_balance = db.query(func.sum(User.balance)).scalar() or 0
        
        outline_keys = list_outline_keys()
        
        text = (f"📊 <b>Статистика бота:</b>\n\n"
                f"👥 Пользователей: {total_users}\n"
                f"💳 Платежей: {total_payments}\n"
                f"📅 Активных подписок: {total_subs}\n"
                f"💰 Общий баланс: {total_balance:.2f} руб\n"
                f"🔑 Ключей в Outline: {len(outline_keys)}\n"
                f"📡 Outline: {'✅ Работает' if connection_ok else '⚠️ Демо'}")
        
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")]]))
        return
    
    # ОСТАЛЬНЫЕ КОМАНДЫ
    elif query.data == "main":
        await query.edit_message_text(
            f"📱 <b>Главное меню</b>\n💰 Баланс: {db_user.balance} руб",
            parse_mode="HTML",
            reply_markup=main_menu(user.id)
        )
    
    elif query.data == "deposit":
        await query.edit_message_text(
            "💰 <b>Пополнение баланса</b>\n\nВведите сумму (10-5000 руб):",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="main")]])
        )
        context.user_data['awaiting_amount'] = True
    
    elif query.data == "balance":
        active_subs = db.query(Subscription).filter(
            Subscription.user_id == db_user.id,
            Subscription.is_active == True,
            Subscription.end_date > datetime.utcnow()
        ).all()
        
        text = f"📊 <b>Ваш баланс:</b> {db_user.balance} руб\n\n"
        if active_subs:
            text += "<b>Активные подписки:</b>\n"
            for sub in active_subs:
                days = (sub.end_date - datetime.utcnow()).days
                text += f"• {sub.tariff} - осталось {days} дней\n"
        else:
            text += "У вас нет активных подписок."
        
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_menu(user.id))
    
    elif query.data == "keys":
        keys = db.query(VPNKey).filter(VPNKey.user_id == db_user.id).all()
        if keys:
            text = "🔑 <b>Ваши ключи:</b>\n\n"
            for i, k in enumerate(keys, 1):
                created = k.created_at.strftime('%d.%m.%Y')
                text += f"{i}. {k.name} (создан: {created})\n"
            text += "\nНапишите номер ключа:"
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=main_menu(user.id))
            context.user_data['awaiting_key_number'] = True
        else:
            await query.edit_message_text(
                "🔑 У вас нет ключей.\nКупите тариф!",
                reply_markup=main_menu(user.id)
            )
    
    elif query.data == "tariffs":
        text = "🛒 <b>Тарифы:</b>\n\n"
        for tid, t in TARIFFS.items():
            text += f"• <b>{t['name']}</b> - {t['price']} руб ({t['days']} дней)\n"
        
        keyboard = []
        for tid in TARIFFS.keys():
            name = TARIFFS[tid]["name"]
            keyboard.append([InlineKeyboardButton(f"Купить {name}", callback_data=f"buy_{tid}")])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="main")])
        
        await query.edit_message_text(text, parse_mode="HTML", 
                                    reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data.startswith("buy_"):
        tariff_id = query.data.replace("buy_", "")
        tariff = TARIFFS.get(tariff_id)
        
        if not tariff:
            await query.edit_message_text("❌ Тариф не найден", reply_markup=main_menu(user.id))
            return
        
        if db_user.balance < tariff['price']:
            await query.edit_message_text(
                f"❌ <b>Недостаточно средств!</b>\n\n"
                f"Нужно: {tariff['price']} руб\n"
                f"На балансе: {db_user.balance} руб",
                parse_mode="HTML",
                reply_markup=main_menu(user.id)
            )
            return
        
        # Списание баланса
        db_user.balance -= tariff['price']
        
        # Создаем подписку
        sub = Subscription(
            user_id=db_user.id,
            tariff=tariff['name'],
            price=tariff['price'],
            end_date=datetime.utcnow() + timedelta(days=tariff['days'])
        )
        db.add(sub)
        
        # Создаем VPN ключ через Outline API
        key_name = f"{tariff['name']} - user{user.id}"
        key_result = create_outline_key(key_name)
        
        if key_result['success']:
            # Реальный ключ создан
            key_text = key_result['access_url']
            key_id_in_outline = key_result['id']
            key_type = "🔐 РЕАЛЬНЫЙ"
            key_status = "✅ Этот ключ работает! Используйте в Outline приложении."
        else:
            # Демо-ключ (на случай ошибки)
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
            key_text = f"ss://chacha20-ietf-poly1305:{password}@45.135.182.168:34554/?outline=1#{key_name}"
            key_id_in_outline = f"demo_{random.randint(10000, 99999)}"
            key_type = "⚠️ ДЕМО"
            key_status = f"⚠️ Не удалось создать реальный ключ: {key_result.get('error', 'Unknown error')}"
        
        # Сохраняем в БД
        vpn_key = VPNKey(
            user_id=db_user.id,
            key_id=key_id_in_outline,
            key=key_text,
            name=tariff['name']
        )
        db.add(vpn_key)
        db.commit()
        
        # Отправляем подтверждение покупки
        await query.edit_message_text(
            f"✅ <b>Покупка успешна!</b>\n\n"
            f"Тариф: {tariff['name']}\n"
            f"Цена: {tariff['price']} руб\n"
            f"Остаток: {db_user.balance} руб\n"
            f"Тип ключа: {key_type}\n\n"
            f"Ключ отправлен отдельным сообщением.",
            parse_mode="HTML",
            reply_markup=main_menu(user.id)
        )
        
        # Отправляем ключ в МОНОШИРИННОМ ФОРМАТЕ
        key_msg = (f"🔑 <b>Ваш VPN ключ ({key_type}):</b>\n\n"
                   f"{format_key_monospace(key_text, with_backticks=True)}\n\n"
                   f"{key_status}")
        
        await context.bot.send_message(
            chat_id=user.id,
            text=key_msg,
            parse_mode="Markdown"  # Используем Markdown для ``` моноширинного формата
        )

async def handle_message(update: Update, context):
    """Обработчик сообщений"""
    text = update.message.text
    user = update.effective_user
    db = next(get_db())
    db_user = get_or_create_user(db, user.id, user.username, user.full_name)
    
    if context.user_data.get('awaiting_amount'):
        try:
            amount = float(text)
            if 10 <= amount <= 5000:
                db_user.balance += amount
                db.commit()
                await update.message.reply_text(
                    f"✅ <b>Пополнено {amount} руб!</b>\nНовый баланс: {db_user.balance} руб",
                    parse_mode="HTML",
                    reply_markup=main_menu(user.id)
                )
                context.user_data.pop('awaiting_amount', None)
            else:
                await update.message.reply_text("⚠️ Сумма должна быть от 10 до 5000 руб")
        except:
            await update.message.reply_text("⚠️ Введите число (например: 500)")
    
    elif context.user_data.get('awaiting_key_number'):
        try:
            num = int(text)
            keys = db.query(VPNKey).filter(VPNKey.user_id == db_user.id).all()
            if 1 <= num <= len(keys):
                key = keys[num-1]
                # Ключ в моноширинном формате
                key_formatted = format_key_monospace(key.key, with_backticks=True)
                await update.message.reply_text(
                    f"🔑 <b>Ключ {num}:</b> {key.name}\n\n{key_formatted}",
                    parse_mode="Markdown",
                    reply_markup=main_menu(user.id)
                )
            else:
                await update.message.reply_text(f"⚠️ Нет ключа с номером {num}")
        except:
            await update.message.reply_text("⚠️ Введите номер ключа")
        context.user_data.pop('awaiting_key_number', None)
    
    else:
        await update.message.reply_text(
            f"💰 Баланс: {db_user.balance} руб\n\nИспользуйте кнопки меню.",
            reply_markup=main_menu(user.id)
        )

# ===== ЗАПУСК БОТА =====
def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    print("=" * 60)
    print("🤖 VPN BOT С РЕАЛЬНЫМ OUTLINE API")
    print("=" * 60)
    print(f"📡 {connection_msg}")
    print(f"🔗 API URL: {OUTLINE_API_URL}")
    print(f"👑 Админы: {ADMIN_IDS}")
    print("=" * 60)
    
    try:
        token = config.Config.BOT_TOKEN
        app = Application.builder().token(token).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("✅ Бот запущен! Напишите /start в Telegram")
        print("📱 Username: @TopWorkVPN_bot")
        print("=" * 60)
        
        app.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()
