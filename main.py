from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
import config
import handlers
import database
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

async def check_subscriptions(context):
    """Ежедневная проверка подписок"""
    db = database.SessionLocal()
    try:
        today = datetime.utcnow()
        
        expired = db.query(database.Subscription).filter(
            database.Subscription.end_date < today,
            database.Subscription.is_active == True
        ).all()
        
        for sub in expired:
            sub.is_active = False
            keys = db.query(database.VPNKey).filter_by(user_id=sub.user_id, is_active=True).all()
            for key in keys:
                key.is_active = False
            
            try:
                await context.bot.send_message(
                    chat_id=sub.user.telegram_id,
                    text="⚠️ Ваша подписка истекла. Пожалуйста, продлите её."
                )
            except:
                pass
        
        db.commit()
        print(f"✓ Проверка подписок: деактивировано {len(expired)}")
    except Exception as e:
        print(f"✗ Ошибка проверки подписок: {e}")
    finally:
        db.close()

def main():
    # Инициализация базы
    print("🔧 Инициализация базы данных...")
    
    # Создаем приложение
    application = Application.builder().token(config.Config.BOT_TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("help", handlers.help_command))
    application.add_handler(CommandHandler("balance", handlers.balance_command))
    application.add_handler(CommandHandler("admin", handlers.admin_panel))  # Админ команда
    
    # Обработчик callback-кнопок
    application.add_handler(CallbackQueryHandler(handlers.button_handler))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
    
    # Планировщик
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_subscriptions, 'cron', hour=0, args=[application])
    scheduler.start()
    
    print("=" * 50)
    print("🤖 VPN Бот запущен!")
    print(f"👑 Админ ID: {config.Config.ADMIN_ID}")
    print(f"📁 База данных: {config.Config.DATABASE_URL}")
    print("=" * 50)
    
    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main()
