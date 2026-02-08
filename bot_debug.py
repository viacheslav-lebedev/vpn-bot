import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Включаем максимальное логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # ИЗМЕНИЛИ НА DEBUG!
)

async def start(update, context):
    print(f"📨 Получен /start от пользователя: {update.effective_user.id}")
    await update.message.reply_text("✅ Бот работает с логированием!")

async def echo(update, context):
    print(f"📨 Сообщение от {update.effective_user.id}: {update.message.text}")
    await update.message.reply_text(f"Вы написали: {update.message.text}")

TOKEN = "8518710020:AAHvXuuUlhMZExOvdzBSNklTKwziVFLYFQs"

print("="*60)
print("🤖 БОТ С ЛОГИРОВАНИЕМ ЗАПУЩЕН")
print("="*60)

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

app.run_polling(drop_pending_updates=True)
