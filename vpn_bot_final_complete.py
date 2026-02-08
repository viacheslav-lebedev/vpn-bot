import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import config
import random
import string
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# ===== НАСТРОЙКИ ИЗ CONFIG =====
ADMIN_IDS = config.Config.ADMIN_IDS
TARIFFS = config.Config.TARIFFS

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

def admin_menu():
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users_0")],
        [InlineKeyboardButton("💳 Платежи", callback_data="admin_payments")],
        [InlineKeyboardButton("🔑 Ключи", callback_data="admin_keys")],
        [InlineKeyboardButton("➕ Добавить баланс", callback_data="admin_add_balance")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_or_create_user(db, telegram_id, username, full_name):
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id, username=username, full_name=full_name)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def generate_vpn_key(name):
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    server = random.choice(["us.vpn.com", "de.vpn.com", "sg.vpn.com"])
    return f"ss://chacha20-ietf-poly1305:{password}@{server}:443/?outline=1#{name}"

# ===== ОСНОВНЫЕ ОБРАБОТЧИКИ =====
async def start(update: Update, context):
    """Команда /start"""
    db = next(get_db())
    user = update.effective_user
    db_user = get_or_create_user(db, user.id, user.username, user.full_name)
    
    text = f"👋 Привет, {user.first_name}!\n💰 Баланс: {db_user.balance} руб\n\nВыберите действие:"
    await update.message.reply_text(text, reply_markup=main_menu(user.id))

async def button_handler(update: Update, context):
    """Обработчик всех кнопок"""
    query = update.callback_query
    await query.answer()
    db = next(get_db())
    user = query.from_user
    db_user = get_or_create_user(db, user.id, user.username, user.full_name)
    
    # АДМИН КОМАНДЫ
    if query.data == "admin_panel" and is_admin(user.id):
        await query.edit_message_text("👑 **Админ-панель**", parse_mode="Markdown", reply_markup=admin_menu())
        return
    
    elif query.data == "admin_stats" and is_admin(user.id):
        total_users = db.query(User).count()
        total_payments = db.query(Payment).count()
        total_subs = db.query(Subscription).filter(Subscription.is_active == True).count()
        total_balance = db.query(func.sum(User.balance)).scalar() or 0
        
        text = (f"📊 **Статистика бота:**\n\n"
                f"👥 Пользователей: {total_users}\n"
                f"💳 Платежей: {total_payments}\n"
                f"📅 Активных подписок: {total_subs}\n"
                f"💰 Общий баланс: {total_balance:.2f} руб")
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=admin_menu())
        return
    
    elif query.data.startswith("admin_users_") and is_admin(user.id):
        page = int(query.data.split("_")[2])
        limit = 5
        users = db.query(User).order_by(User.id).offset(page * limit).limit(limit).all()
        total = db.query(User).count()
        
        text = f"👥 **Пользователи** (стр. {page+1}, всего: {total})\n\n"
        keyboard = []
        for u in users:
            text += f"{u.id}. @{u.username or u.full_name} - {u.balance} руб\n"
            keyboard.append([InlineKeyboardButton(f"👤 {u.id}. {u.username or u.full_name}", 
                           callback_data=f"admin_user_{u.id}")])
        
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("◀️ Назад", callback_data=f"admin_users_{page-1}"))
        if (page + 1) * limit < total:
            nav.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"admin_users_{page+1}"))
        if nav:
            keyboard.append(nav)
        
        keyboard.append([InlineKeyboardButton("🏠 Админ-панель", callback_data="admin_panel")])
        
        await query.edit_message_text(text, parse_mode="Markdown", 
                                    reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    elif query.data.startswith("admin_user_") and is_admin(user.id):
        user_id = int(query.data.split("_")[2])
        target = db.query(User).filter(User.id == user_id).first()
        
        if target:
            subs = db.query(Subscription).filter(Subscription.user_id == target.id).all()
            keys = db.query(VPNKey).filter(VPNKey.user_id == target.id).all()
            
            text = (f"👤 **Информация о пользователе:**\n\n"
                    f"ID: {target.id}\n"
                    f"Telegram: {target.telegram_id}\n"
                    f"Username: @{target.username or 'нет'}\n"
                    f"Имя: {target.full_name}\n"
                    f"💰 Баланс: {target.balance} руб\n"
                    f"📅 Регистрация: {target.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                    f"🔑 Ключей: {len(keys)}\n"
                    f"📊 Подписок: {len(subs)}")
            
            keyboard = [
                [InlineKeyboardButton("➕ Добавить баланс", callback_data=f"admin_add_to_{target.id}")],
                [InlineKeyboardButton("👥 К списку", callback_data="admin_users_0")],
                [InlineKeyboardButton("🏠 Админ-панель", callback_data="admin_panel")]
            ]
            await query.edit_message_text(text, parse_mode="Markdown", 
                                        reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    elif query.data.startswith("admin_add_to_") and is_admin(user.id):
        user_id = int(query.data.split("_")[3])
        context.user_data['admin_adding_to'] = user_id
        await query.edit_message_text(
            "💰 **Добавление баланса**\n\nВведите сумму:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="admin_panel")]])
        )
        return
    
    elif query.data == "admin_payments" and is_admin(user.id):
        payments = db.query(Payment).order_by(Payment.created_at.desc()).limit(10).all()
        text = "💳 **Последние 10 платежей:**\n\n"
        for p in payments:
            u = db.query(User).filter(User.id == p.user_id).first()
            name = f"@{u.username}" if u and u.username else f"ID:{p.user_id}"
            text += f"• {p.amount} руб - {name} - {p.status}\n"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=admin_menu())
        return
    
    elif query.data == "admin_keys" and is_admin(user.id):
        keys = db.query(VPNKey).order_by(VPNKey.created_at.desc()).limit(10).all()
        text = "🔑 **Последние 10 ключей:**\n\n"
        for k in keys:
            u = db.query(User).filter(User.id == k.user_id).first()
            name = f"@{u.username}" if u and u.username else f"ID:{k.user_id}"
            text += f"• {k.name} - {name}\n"
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=admin_menu())
        return
    
    elif query.data == "admin_add_balance" and is_admin(user.id):
        context.user_data['admin_adding'] = True
        await query.edit_message_text(
            "💰 **Добавление баланса**\n\nВведите: `ID_пользователя:сумма`\nПример: `123456789:500`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отмена", callback_data="admin_panel")]])
        )
        return
    
    # ОБЫЧНЫЕ КОМАНДЫ ПОЛЬЗОВАТЕЛЯ
    elif query.data == "main":
        await query.edit_message_text(
            f"📱 **Главное меню**\n💰 Баланс: {db_user.balance} руб",
            parse_mode="Markdown",
            reply_markup=main_menu(user.id)
        )
    
    elif query.data == "deposit":
        await query.edit_message_text(
            "💰 **Пополнение баланса**\n\nВведите сумму (10-5000 руб):",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="main")]])
        )
        context.user_data['awaiting_amount'] = True
    
    elif query.data == "balance":
        active_subs = db.query(Subscription).filter(
            Subscription.user_id == db_user.id,
            Subscription.is_active == True,
            Subscription.end_date > datetime.utcnow()
        ).all()
        
        text = f"📊 **Ваш баланс:** {db_user.balance} руб\n\n"
        if active_subs:
            text += "**Активные подписки:**\n"
            for sub in active_subs:
                days = (sub.end_date - datetime.utcnow()).days
                text += f"• {sub.tariff} - осталось {days} дней\n"
        else:
            text += "У вас нет активных подписок."
        
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu(user.id))
    
    elif query.data == "keys":
        keys = db.query(VPNKey).filter(VPNKey.user_id == db_user.id).all()
        if keys:
            text = "🔑 **Ваши ключи:**\n\n"
            for i, k in enumerate(keys, 1):
                text += f"{i}. {k.name} ({k.created_at.strftime('%d.%m.%Y')})\n"
            text += "\nНапишите номер ключа:"
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu(user.id))
            context.user_data['awaiting_key_number'] = True
        else:
            await query.edit_message_text(
                "🔑 У вас нет ключей.\nКупите тариф!",
                reply_markup=main_menu(user.id)
            )
    
    elif query.data == "tariffs":
        text = "🛒 **Тарифы:**\n\n"
        for tid, t in TARIFFS.items():
            text += f"• **{t['name']}** - {t['price']} руб ({t['days']} дней)\n"
        
        keyboard = []
        for tid in TARIFFS.keys():
            name = TARIFFS[tid]["name"]
            keyboard.append([InlineKeyboardButton(f"Купить {name}", callback_data=f"buy_{tid}")])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="main")])
        
        await query.edit_message_text(text, parse_mode="Markdown", 
                                    reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data.startswith("buy_"):
        tariff_id = query.data.replace("buy_", "")
        tariff = TARIFFS.get(tariff_id)
        
        if tariff and db_user.balance >= tariff['price']:
            db_user.balance -= tariff['price']
            
            sub = Subscription(
                user_id=db_user.id,
                tariff=tariff['name'],
                price=tariff['price'],
                end_date=datetime.utcnow() + timedelta(days=tariff['days'])
            )
            db.add(sub)
            
            key_text = generate_vpn_key(tariff['name'])
            vpn_key = VPNKey(
                user_id=db_user.id,
                key=key_text,
                name=tariff['name']
            )
            db.add(vpn_key)
            db.commit()
            
            await query.edit_message_text(
                f"✅ **Покупка успешна!**\n\n"
                f"Тариф: {tariff['name']}\n"
                f"Цена: {tariff['price']} руб\n"
                f"Остаток: {db_user.balance} руб\n\n"
                f"Ключ отправлен отдельно.",
                parse_mode="Markdown",
                reply_markup=main_menu(user.id)
            )
            
            await context.bot.send_message(
                chat_id=user.id,
                text=f"🔑 **Ваш VPN ключ:**\n\n`{key_text}`\n\nИспользуйте в Outline.",
                parse_mode="Markdown"
            )
        elif tariff:
            await query.edit_message_text(
                f"❌ **Недостаточно средств!**\n\n"
                f"Нужно: {tariff['price']} руб\n"
                f"На балансе: {db_user.balance} руб",
                parse_mode="Markdown",
                reply_markup=main_menu(user.id)
            )

async def handle_message(update: Update, context):
    """Обработчик сообщений"""
    text = update.message.text
    user = update.effective_user
    db = next(get_db())
    db_user = get_or_create_user(db, user.id, user.username, user.full_name)
    
    # АДМИН: Добавление баланса конкретному пользователю
    if 'admin_adding_to' in context.user_data and is_admin(user.id):
        try:
            amount = float(text)
            target_id = context.user_data['admin_adding_to']
            target = db.query(User).filter(User.id == target_id).first()
            
            if target:
                target.balance += amount
                db.commit()
                
                await update.message.reply_text(
                    f"✅ Пользователю {target.id} добавлено {amount} руб\n"
                    f"Новый баланс: {target.balance} руб",
                    reply_markup=admin_menu()
                )
                
                try:
                    await context.bot.send_message(
                        chat_id=target.telegram_id,
                        text=f"💰 Администратор добавил вам {amount} руб\nНовый баланс: {target.balance} руб"
                    )
                except:
                    pass
            else:
                await update.message.reply_text("❌ Пользователь не найден", reply_markup=admin_menu())
            
            context.user_data.pop('admin_adding_to', None)
            return
        except:
            await update.message.reply_text("❌ Введите число", reply_markup=admin_menu())
            return
    
    # АДМИН: Добавление баланса по формату ID:СУММА
    if context.user_data.get('admin_adding') and is_admin(user.id):
        if ":" in text:
            try:
                uid, amount = text.split(":")
                uid = int(uid.strip())
                amount = float(amount.strip())
                
                target = db.query(User).filter(User.telegram_id == uid).first()
                if not target:
                    target = db.query(User).filter(User.id == uid).first()
                
                if target:
                    target.balance += amount
                    db.commit()
                    
                    await update.message.reply_text(
                        f"✅ Пользователю {target.id} добавлено {amount} руб\n"
                        f"Новый баланс: {target.balance} руб",
                        reply_markup=admin_menu()
                    )
                    
                    try:
                        await context.bot.send_message(
                            chat_id=target.telegram_id,
                            text=f"💰 Администратор добавил вам {amount} руб\nНовый баланс: {target.balance} руб"
                        )
                    except:
                        pass
                else:
                    await update.message.reply_text("❌ Пользователь не найден", reply_markup=admin_menu())
            except:
                await update.message.reply_text("❌ Формат: ID:СУММА\nПример: 123456789:500", reply_markup=admin_menu())
        else:
            await update.message.reply_text("❌ Формат: ID:СУММА", reply_markup=admin_menu())
        
        context.user_data.pop('admin_adding', None)
        return
    
    # ПОЛЬЗОВАТЕЛЬ: Пополнение баланса
    if context.user_data.get('awaiting_amount'):
        try:
            amount = float(text)
            if 10 <= amount <= 5000:
                db_user.balance += amount
                db.commit()
                
                await update.message.reply_text(
                    f"✅ **Пополнено {amount} руб!**\n\nНовый баланс: {db_user.balance} руб",
                    parse_mode="Markdown",
                    reply_markup=main_menu(user.id)
                )
                context.user_data.pop('awaiting_amount', None)
            else:
                await update.message.reply_text("⚠️ Сумма 10-5000 руб")
        except:
            await update.message.reply_text("⚠️ Введите число")
    
    # ПОЛЬЗОВАТЕЛЬ: Получение ключа по номеру
    elif context.user_data.get('awaiting_key_number'):
        try:
            num = int(text)
            keys = db.query(VPNKey).filter(VPNKey.user_id == db_user.id).all()
            
            if 1 <= num <= len(keys):
                key = keys[num-1]
                await update.message.reply_text(
                    f"🔑 **Ключ {num}:**\n\n`{key.key}`",
                    parse_mode="Markdown",
                    reply_markup=main_menu(user.id)
                )
            else:
                await update.message.reply_text(f"⚠️ Нет ключа {num}")
        except:
            await update.message.reply_text("⚠️ Введите номер")
        
        context.user_data.pop('awaiting_key_number', None)
    
    else:
        await update.message.reply_text(
            f"💰 Баланс: {db_user.balance} руб\n\nИспользуйте кнопки меню.",
            reply_markup=main_menu(user.id)
        )

# ===== ЗАПУСК БОТА =====
def main():
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("🤖 VPN BOT - ПОЛНАЯ ВЕРСИЯ С АДМИН-ПАНЕЛЬЮ")
    print("=" * 60)
    print(f"👑 Админы: {ADMIN_IDS}")
    print(f"🤖 Бот: @TopWorkVPN_bot")
    print("=" * 60)
    
    try:
        token = config.Config.BOT_TOKEN
        app = Application.builder().token(token).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("admin", lambda u,c: button_handler(u,c) if is_admin(u.effective_user.id) else u.message.reply_text("⛔ Нет доступа")))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print("✅ Бот запущен! Напишите /start в Telegram")
        print("=" * 60)
        
        app.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()
