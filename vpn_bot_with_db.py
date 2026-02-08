import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import config
import random
import string
from datetime import datetime, timedelta
from database import get_db, User, Subscription, VPNKey

logging.basicConfig(level=logging.INFO)

print("=" * 60)
print("🤖 VPN BOT WITH DATABASE")
print("=" * 60)

TARIFFS = config.Config.TARIFFS

def main_menu():
    keyboard = [
        [InlineKeyboardButton("💰 Пополнить баланс", callback_data="deposit")],
        [InlineKeyboardButton("📊 Мой баланс", callback_data="balance")],
        [InlineKeyboardButton("🔑 Мои ключи", callback_data="keys")],
        [InlineKeyboardButton("🛒 Купить тариф", callback_data="tariffs")],
        [InlineKeyboardButton("📞 Поддержка", callback_data="support")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_or_create_user(db, telegram_id, username, full_name):
    """Получить или создать пользователя"""
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            balance=0.0
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"✅ Создан новый пользователь: {user.id}")
    return user

def generate_vpn_key(name):
    """Генерация демо VPN ключа"""
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    servers = ["us.vpn.example.com", "de.vpn.example.com", "sg.vpn.example.com"]
    server = random.choice(servers)
    return f"ss://chacha20-ietf-poly1305:{password}@{server}:443/?outline=1#{name}"

async def start(update: Update, context):
    """Команда /start"""
    db = next(get_db())
    user = update.effective_user
    
    # Создаем/получаем пользователя в БД
    db_user = get_or_create_user(db, user.id, user.username, user.full_name)
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n"
        f"💰 Ваш баланс: {db_user.balance} руб\n\n"
        f"Выберите действие:",
        reply_markup=main_menu()
    )

async def button_handler(update: Update, context):
    """Обработчик кнопок"""
    query = update.callback_query
    await query.answer()
    db = next(get_db())
    user = query.from_user
    
    # Получаем пользователя
    db_user = get_or_create_user(db, user.id, user.username, user.full_name)
    
    if query.data == "main":
        await query.edit_message_text(
            f"📱 Главное меню\n💰 Баланс: {db_user.balance} руб",
            reply_markup=main_menu()
        )
    
    elif query.data == "deposit":
        await query.edit_message_text(
            "💰 Введите сумму (10-5000 руб):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="main")]])
        )
        context.user_data['awaiting_amount'] = True
    
    elif query.data == "balance":
        # Получаем активные подписки
        active_subs = db.query(Subscription).filter(
            Subscription.user_id == db_user.id,
            Subscription.is_active == True,
            Subscription.end_date > datetime.utcnow()
        ).all()
        
        sub_text = ""
        for sub in active_subs:
            days_left = (sub.end_date - datetime.utcnow()).days
            sub_text += f"• {sub.tariff} - осталось {days_left} дней\n"
        
        text = f"📊 **Ваш баланс:** {db_user.balance} руб\n\n"
        if active_subs:
            text += f"**Активные подписки:**\n{sub_text}"
        else:
            text += "У вас нет активных подписок."
        
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu())
    
    elif query.data == "keys":
        # Получаем ключи пользователя
        keys = db.query(VPNKey).filter(VPNKey.user_id == db_user.id).all()
        
        if keys:
            text = "🔑 **Ваши VPN ключи:**\n\n"
            for i, key in enumerate(keys, 1):
                text += f"{i}. {key.name} (создан: {key.created_at.strftime('%d.%m.%Y')})\n"
            
            text += "\nНапишите номер ключа чтобы получить его."
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu())
            context.user_data['awaiting_key_number'] = True
        else:
            await query.edit_message_text(
                "🔑 У вас пока нет VPN ключей.\nКупите тариф чтобы получить ключ.",
                reply_markup=main_menu()
            )
    
    elif query.data == "tariffs":
        text = "🛒 **Доступные тарифы:**\n\n"
        for tariff_id, tariff in TARIFFS.items():
            text += f"• **{tariff['name']}** - {tariff['price']} руб ({tariff['days']} дней)\n"
        
        keyboard = []
        for tariff_id in TARIFFS.keys():
            name = TARIFFS[tariff_id]["name"]
            keyboard.append([InlineKeyboardButton(f"Купить {name}", callback_data=f"buy_{tariff_id}")])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="main")])
        
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data.startswith("buy_"):
        tariff_id = query.data.replace("buy_", "")
        tariff = TARIFFS.get(tariff_id)
        
        if tariff:
            # Проверяем баланс
            if db_user.balance >= tariff['price']:
                # Списание денег
                db_user.balance -= tariff['price']
                
                # Создаем подписку
                subscription = Subscription(
                    user_id=db_user.id,
                    tariff=tariff['name'],
                    price=tariff['price'],
                    start_date=datetime.utcnow(),
                    end_date=datetime.utcnow() + timedelta(days=tariff['days']),
                    is_active=True
                )
                db.add(subscription)
                
                # Генерируем VPN ключ
                vpn_key = generate_vpn_key(tariff['name'])
                
                # Сохраняем ключ в БД
                vpn_key_record = VPNKey(
                    user_id=db_user.id,
                    key_id=f"key_{user.id}_{int(datetime.utcnow().timestamp())}",
                    key=vpn_key,
                    name=tariff['name']
                )
                db.add(vpn_key_record)
                
                db.commit()
                
                # Отправляем подтверждение
                await query.edit_message_text(
                    f"✅ **Покупка успешна!**\n\n"
                    f"Тариф: {tariff['name']}\n"
                    f"Цена: {tariff['price']} руб\n"
                    f"Срок: {tariff['days']} дней\n"
                    f"Остаток баланса: {db_user.balance} руб\n\n"
                    f"Ключ отправлен отдельным сообщением.",
                    parse_mode="Markdown",
                    reply_markup=main_menu()
                )
                
                # Отправляем ключ
                await context.bot.send_message(
                    chat_id=user.id,
                    text=f"🔑 **Ваш VPN ключ:**\n\n`{vpn_key}`\n\nИспользуйте в Outline приложении.",
                    parse_mode="Markdown"
                )
            else:
                await query.edit_message_text(
                    f"❌ **Недостаточно средств!**\n\n"
                    f"Нужно: {tariff['price']} руб\n"
                    f"На балансе: {db_user.balance} руб\n\n"
                    f"Пополните баланс.",
                    parse_mode="Markdown",
                    reply_markup=main_menu()
                )
    
    elif query.data == "support":
        await query.edit_message_text(
            "📞 **Поддержка**\n\n"
            "По вопросам:\n• @your_support\n\n"
            "⏰ 24/7",
            parse_mode="Markdown",
            reply_markup=main_menu()
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
                # Пополняем баланс
                db_user.balance += amount
                db.commit()
                
                await update.message.reply_text(
                    f"✅ **Баланс пополнен на {amount} руб!**\n\n"
                    f"Новый баланс: {db_user.balance} руб",
                    parse_mode="Markdown",
                    reply_markup=main_menu()
                )
                context.user_data.pop('awaiting_amount', None)
            else:
                await update.message.reply_text("⚠️ Сумма должна быть от 10 до 5000 руб")
        except:
            await update.message.reply_text("⚠️ Введите число (например: 500)")
    
    elif context.user_data.get('awaiting_key_number'):
        try:
            key_num = int(text)
            keys = db.query(VPNKey).filter(VPNKey.user_id == db_user.id).all()
            
            if 1 <= key_num <= len(keys):
                key = keys[key_num - 1]
                await update.message.reply_text(
                    f"🔑 **Ключ {key_num}:**\n\n"
                    f"Название: {key.name}\n"
                    f"Создан: {key.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"**Ключ для подключения:**\n`{key.key}`",
                    parse_mode="Markdown",
                    reply_markup=main_menu()
                )
            else:
                await update.message.reply_text(f"⚠️ Нет ключа с номером {key_num}")
        except:
            await update.message.reply_text("⚠️ Введите номер ключа")
        
        context.user_data.pop('awaiting_key_number', None)
    
    else:
        await update.message.reply_text(
            f"💰 Баланс: {db_user.balance} руб\n\n"
            f"Используйте кнопки меню для навигации.",
            reply_markup=main_menu()
        )

def main():
    try:
        token = config.Config.BOT_TOKEN
        print(f"🚀 Запуск бота с БД...")
        
        app = Application.builder().token(token).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        app.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()
