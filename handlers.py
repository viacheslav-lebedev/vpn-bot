from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
import payments
import outlines_api
import config
import keyboards
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user = update.effective_user
    
    # Регистрируем пользователя
    db = database.SessionLocal()
    try:
        existing = db.query(database.User).filter_by(telegram_id=user.id).first()
        if not existing:
            new_user = database.User(
                telegram_id=user.id,
                username=user.username,
                full_name=user.full_name,
                balance=0.0
            )
            db.add(new_user)
            db.commit()
            logger.info(f"Новый пользователь: {user.id}")
    except Exception as e:
        logger.error(f"Ошибка регистрации: {e}")
        db.rollback()
    finally:
        db.close()
    
    await update.message.reply_text(
        text=f"Привет, {user.first_name}! 👋\n\n"
             "Я бот для управления VPN на базе Outline.\n"
             "Выберите действие:",
        reply_markup=keyboards.main_menu()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    await update.message.reply_text(
        text="🤖 Доступные команды:\n"
             "/start - Главное меню\n"
             "/help - Эта справка\n"
             "/balance - Проверить баланс\n"
             "/admin - Панель администратора (если вы админ)\n\n"
             "Используйте кнопки для навигации."
    )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /balance"""
    db = database.SessionLocal()
    try:
        user = db.query(database.User).filter_by(telegram_id=update.effective_user.id).first()
        if user:
            await update.message.reply_text(f"💰 Ваш баланс: {user.balance} руб.")
        else:
            await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
    finally:
        db.close()

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /admin - только для администратора"""
    user_id = update.effective_user.id
    
    if user_id != config.Config.ADMIN_ID:
        await update.message.reply_text("❌ У вас нет прав администратора.")
        return
    
    await update.message.reply_text(
        text="👑 Панель администратора",
        reply_markup=keyboards.admin_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех inline-кнопок"""
    query = update.callback_query
    
    # Всегда отвечаем на callback_query
    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"Не удалось ответить на callback_query: {e}")
        # Продолжаем выполнение
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    logger.info(f"Кнопка: {callback_data} от {user_id}")
    
    # РОУТИНГ ПО CALLBACK_DATA
    if callback_data == "main_menu":
        await show_main_menu(query)
    
    elif callback_data == "show_tariffs":
        await show_tariffs(query)
    
    elif callback_data.startswith("tariff_"):
        tariff_id = callback_data.replace("tariff_", "")
        await handle_tariff_selection(query, user_id, tariff_id)
    
    elif callback_data.startswith("pay_"):
        tariff_id = callback_data.replace("pay_", "")
        await handle_payment(query, user_id, tariff_id)
    
    elif callback_data == "my_keys":
        await show_user_keys(query, user_id)
    
    elif callback_data == "balance":
        await show_balance(query, user_id)
    
    elif callback_data == "support":
        await show_support(query)
    
    # АДМИН КНОПКИ
    elif callback_data == "admin_stats":
        await admin_stats(query, user_id)
    
    elif callback_data == "admin_users":
        await admin_users(query, user_id)
    
    elif callback_data == "admin_keys":
        await admin_keys(query, user_id)
    
    elif callback_data == "admin_payments":
        await admin_payments(query, user_id)
    
    else:
        await query.edit_message_text(
            text="❌ Неизвестная команда",
            reply_markup=keyboards.main_menu()
        )
# ========== ОСНОВНЫЕ ФУНКЦИИ ==========

async def show_main_menu(query):
    """Показать главное меню"""
    await query.edit_message_text(
        text="Главное меню:",
        reply_markup=keyboards.main_menu()
    )

async def show_tariffs(query):
    """Показать тарифы"""
    await query.edit_message_text(
        text="Выберите тариф:",
        reply_markup=keyboards.tariffs_keyboard()
    )

async def handle_tariff_selection(query, user_id, tariff_id):
    """Обработка выбора тарифа"""
    tariff = config.Config.TARIFFS.get(tariff_id)
    
    if not tariff:
        await query.edit_message_text(
            text="❌ Тариф не найден.",
            reply_markup=keyboards.tariffs_keyboard()
        )
        return
    
    if tariff_id == "trial":
        # Пробный период
        await handle_trial_period(query, user_id)
    else:
        # Платный тариф
        await query.edit_message_text(
            text=f"📋 Тариф: {tariff['name']}\n"
                 f"💰 Цена: {tariff['price']} руб.\n"
                 f"⏳ Срок: {tariff['days']} дней\n\n"
                 f"Для оплаты нажмите кнопку ниже:",
            reply_markup=keyboards.payment_keyboard(tariff_id)
        )

async def handle_trial_period(query, user_id):
    """Обработка пробного периода"""
    db = database.SessionLocal()
    try:
        user = db.query(database.User).filter_by(telegram_id=user_id).first()
        if not user:
            await query.edit_message_text("❌ Пользователь не найден")
            return
        
        if user.trial_used:
            await query.edit_message_text(
                text="❌ Пробный период уже использован.",
                reply_markup=keyboards.main_menu()
            )
            return
        
        # Создаем VPN ключ
        api = outlines_api.OutlinesAPI()
        key_name = f"Пробный {user.telegram_id}"
        new_key = api.create_key(key_name, limit_gb=5)
        
        if new_key:
            # Сохраняем ключ в БД
            vpn_key = database.VPNKey(
                user_id=user.id,
                key_id=new_key.get('id'),
                name=key_name,
                access_url=new_key.get('accessUrl', ''),
                server_id=config.Config.OUTLINES_SERVER_ID,
                data_limit_gb=5
            )
            db.add(vpn_key)
            
            # Создаем подписку
            subscription = database.Subscription(
                user_id=user.id,
                tariff_id="trial",
                start_date=datetime.utcnow(),
                end_date=datetime.utcnow() + timedelta(days=30),
                is_active=True,
                vpn_key_id=vpn_key.id
            )
            db.add(subscription)
            
            # Отмечаем пробный период как использованный
            user.trial_used = True
            
            db.commit()
            
            # Отправляем ключ пользователю
            await query.edit_message_text(
                text=f"✅ Пробный период активирован на 30 дней!\n\n"
                     f"🔑 Ваш VPN ключ:\n"
                     f"`{new_key.get('accessUrl', '')}`\n\n"
                     f"📱 Используйте любой Shadowsocks клиент для подключения.",
                parse_mode="Markdown",
                reply_markup=keyboards.main_menu()
            )
            logger.info(f"Пробный период активирован для {user_id}")
        else:
            await query.edit_message_text(
                text="❌ Не удалось создать VPN ключ. Попробуйте позже.",
                reply_markup=keyboards.main_menu()
            )
            
    except Exception as e:
        logger.error(f"Ошибка пробного периода: {e}")
        await query.edit_message_text(
            text="❌ Произошла ошибка. Попробуйте позже.",
            reply_markup=keyboards.main_menu()
        )
        db.rollback()
    finally:
        db.close()

async def handle_payment(query, user_id, tariff_id):
    """Обработка оплаты"""
    tariff = config.Config.TARIFFS.get(tariff_id)
    
    if not tariff:
        await query.edit_message_text("❌ Тариф не найден")
        return
    
    db = database.SessionLocal()
    try:
        user = db.query(database.User).filter_by(telegram_id=user_id).first()
        if not user:
            await query.edit_message_text("❌ Пользователь не найден")
            return
        
        # Создаем платеж
        description = f"Тариф: {tariff['name']} ({tariff['days']} дней)"
        payment_result = payments.create_payment(
            user_id=user.id,
            amount=tariff['price'],
            description=description,
            tariff_id=tariff_id
        )
        
        if payment_result:
            await query.edit_message_text(
                text=f"💳 Для оплаты перейдите по ссылке:\n\n"
                     f"{payment_result['confirmation_url']}\n\n"
                     f"После оплаты баланс пополнится автоматически.",
                reply_markup=keyboards.main_menu()
            )
        else:
            await query.edit_message_text(
                text="❌ Не удалось создать платеж. Попробуйте позже.",
                reply_markup=keyboards.main_menu()
            )
            
    except Exception as e:
        logger.error(f"Ошибка создания платежа: {e}")
        await query.edit_message_text(
            text="❌ Произошла ошибка при создании платежа.",
            reply_markup=keyboards.main_menu()
        )
    finally:
        db.close()

async def show_user_keys(query, user_id):
    """Показать ключи пользователя"""
    db = database.SessionLocal()
    try:
        user = db.query(database.User).filter_by(telegram_id=user_id).first()
        if not user:
            await query.edit_message_text("❌ Пользователь не найден")
            return
        
        keys = db.query(database.VPNKey).filter_by(user_id=user.id).all()
        
        if not keys:
            await query.edit_message_text(
                text="У вас пока нет VPN ключей.",
                reply_markup=keyboards.main_menu()
            )
            return
        
        text = "🔑 Ваши VPN ключи:\n\n"
        for key in keys:
            text += f"• {key.name}\n"
            if key.access_url:
                text += f"  `{key.access_url[:50]}...`\n\n"
        
        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=keyboards.main_menu()
        )
        
    finally:
        db.close()

async def show_balance(query, user_id):
    """Показать баланс"""
    db = database.SessionLocal()
    try:
        user = db.query(database.User).filter_by(telegram_id=user_id).first()
        if user:
            await query.edit_message_text(
                text=f"💰 Ваш баланс: {user.balance} руб.",
                reply_markup=keyboards.main_menu()
            )
        else:
            await query.edit_message_text(
                text="❌ Пользователь не найден",
                reply_markup=keyboards.main_menu()
            )
    finally:
        db.close()

async def show_support(query):
    """Показать поддержку"""
    await query.edit_message_text(
        text="📞 Поддержка:\n\n"
             "По всем вопросам обращайтесь к администратору.\n"
             "Мы всегда готовы помочь!",
        reply_markup=keyboards.main_menu()
    )
# ========== АДМИН ФУНКЦИИ ==========

async def admin_stats(query, user_id):
    """Статистика для администратора"""
    if user_id != config.Config.ADMIN_ID:
        await query.edit_message_text("❌ Нет прав")
        return
    
    db = database.SessionLocal()
    try:
        users_count = db.query(database.User).count()
        payments_count = db.query(database.Payment).count()
        keys_count = db.query(database.VPNKey).count()
        active_subs = db.query(database.Subscription).filter_by(is_active=True).count()
        
        text = f"📊 Статистика:\n\n"
        text += f"👥 Пользователей: {users_count}\n"
        text += f"💳 Платежей: {payments_count}\n"
        text += f"🔑 VPN ключей: {keys_count}\n"
        text += f"✅ Активных подписок: {active_subs}\n"
        
        await query.edit_message_text(
            text=text,
            reply_markup=keyboards.admin_keyboard()
        )
        
    finally:
        db.close()

async def admin_users(query, user_id):
    """Список пользователей для администратора"""
    if user_id != config.Config.ADMIN_ID:
        await query.edit_message_text("❌ Нет прав")
        return
    
    db = database.SessionLocal()
    try:
        users = db.query(database.User).order_by(database.User.created_at.desc()).limit(10).all()
        
        text = "👥 Последние 10 пользователей:\n\n"
        for user in users:
            text += f"• ID: {user.telegram_id}\n"
            text += f"  Имя: {user.full_name or 'N/A'}\n"
            text += f"  Баланс: {user.balance} руб.\n"
            text += f"  Регистрация: {user.created_at.strftime('%Y-%m-%d')}\n\n"
        
        await query.edit_message_text(
            text=text,
            reply_markup=keyboards.admin_keyboard()
        )
        
    finally:
        db.close()

async def admin_keys(query, user_id):
    """Список ключей для администратора"""
    if user_id != config.Config.ADMIN_ID:
        await query.edit_message_text("❌ Нет прав")
        return
    
    db = database.SessionLocal()
    try:
        keys = db.query(database.VPNKey).order_by(database.VPNKey.created_at.desc()).limit(10).all()
        
        text = "🔑 Последние 10 VPN ключей:\n\n"
        for key in keys:
            text += f"• {key.name}\n"
            text += f"  Пользователь ID: {key.user_id}\n"
            text += f"  Создан: {key.created_at.strftime('%Y-%m-%d')}\n\n"
        
        await query.edit_message_text(
            text=text,
            reply_markup=keyboards.admin_keyboard()
        )
        
    finally:
        db.close()

async def admin_payments(query, user_id):
    """Список платежей для администратора"""
    if user_id != config.Config.ADMIN_ID:
        await query.edit_message_text("❌ Нет прав")
        return
    
    db = database.SessionLocal()
    try:
        payments_list = db.query(database.Payment).order_by(database.Payment.created_at.desc()).limit(10).all()
        
        text = "💳 Последние 10 платежей:\n\n"
        for payment in payments_list:
            status_emoji = "✅" if payment.status == "completed" else "⏳" if payment.status == "pending" else "❌"
            text += f"{status_emoji} {payment.amount} руб.\n"
            text += f"  Статус: {payment.status}\n"
            text += f"  Дата: {payment.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        
        await query.edit_message_text(
            text=text,
            reply_markup=keyboards.admin_keyboard()
        )
        
    finally:
        db.close()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    await update.message.reply_text(
        text="Используйте команды или кнопки меню.\n"
             "/start - главное меню"
    )
