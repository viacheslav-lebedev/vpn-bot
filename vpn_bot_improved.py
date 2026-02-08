import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import config
import random
import string

logging.basicConfig(level=logging.INFO)

print("=" * 60)
print("🤖 VPN BOT - IMPROVED VERSION")
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

def generate_vpn_key(name):
    """Генерация демо VPN ключа"""
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    servers = ["us.vpn.example.com", "de.vpn.example.com", "sg.vpn.example.com"]
    server = random.choice(servers)
    return f"ss://chacha20-ietf-poly1305:{password}@{server}:443/?outline=1#{name}"

async def start(update: Update, context):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\nВыберите действие:",
        reply_markup=main_menu()
    )

async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    
    if query.data == "main":
        await query.edit_message_text("📱 Главное меню:", reply_markup=main_menu())
    
    elif query.data == "deposit":
        await query.edit_message_text(
            "💰 Введите сумму (10-5000 руб):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="main")]])
        )
        context.user_data['awaiting_amount'] = True
    
    elif query.data == "balance":
        await query.edit_message_text(
            "📊 Баланс: 0 руб",
            reply_markup=main_menu()
        )
    
    elif query.data == "keys":
        await query.edit_message_text(
            "🔑 Ваши ключи VPN:\n\nКлючей нет. Купите тариф.",
            reply_markup=main_menu()
        )
    
    elif query.data == "tariffs":
        text = "🛒 Тарифы:\n\n"
        for tariff_id, tariff in TARIFFS.items():
            text += f"• {tariff['name']} - {tariff['price']} руб\n"
        
        keyboard = []
        for tariff_id in TARIFFS.keys():
            name = TARIFFS[tariff_id]["name"]
            keyboard.append([InlineKeyboardButton(f"Купить {name}", callback_data=f"buy_{tariff_id}")])
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="main")])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data.startswith("buy_"):
        tariff_id = query.data.replace("buy_", "")
        tariff = TARIFFS.get(tariff_id)
        
        if tariff:
            # Генерируем ключ
            vpn_key = generate_vpn_key(tariff['name'])
            
            # Показываем подтверждение с меню
            await query.edit_message_text(
                f"✅ Куплен тариф: {tariff['name']}\n"
                f"💰 Цена: {tariff['price']} руб\n\n"
                f"Ключ отправлен отдельным сообщением.",
                reply_markup=main_menu()  # ВОТ ЗДЕСЬ ВОЗВРАЩАЕМ МЕНЮ!
            )
            
            # Отправляем ключ
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=f"🔑 Ваш VPN ключ:\n\n`{vpn_key}`\n\nИспользуйте в Outline приложении.",
                parse_mode="Markdown"
            )
    
    elif query.data == "support":
        await query.edit_message_text(
            "📞 Поддержка: @your_support",
            reply_markup=main_menu()
        )

async def handle_message(update: Update, context):
    text = update.message.text
    
    if context.user_data.get('awaiting_amount'):
        try:
            amount = float(text)
            if 10 <= amount <= 5000:
                await update.message.reply_text(
                    f"✅ Пополнено {amount} руб!",
                    reply_markup=main_menu()  # Возвращаем меню
                )
                context.user_data.pop('awaiting_amount', None)
            else:
                await update.message.reply_text("Сумма 10-5000 руб")
        except:
            await update.message.reply_text("Введите число")
    else:
        await update.message.reply_text(
            "Используйте /start или кнопки меню",
            reply_markup=main_menu()  # Всегда показываем меню
        )

def main():
    try:
        token = config.Config.BOT_TOKEN
        print(f"🚀 Запуск бота...")
        
        app = Application.builder().token(token).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        app.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()
