async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, amount: float):
    """Обработка платежа"""
    db = database.SessionLocal()
    try:
        user_id = update.callback_query.from_user.id
        user = db.query(database.User).filter_by(telegram_id=user_id).first()
        
        if not user:
            await update.callback_query.edit_message_text("❌ Пользователь не найден")
            return
        
        # Создаем платеж
        payment_result = await payments.create_payment(db, user_id, amount)
        
        if not payment_result:
            await update.callback_query.edit_message_text(
                "❌ Не удалось создать платеж. Попробуйте позже.",
                reply_markup=keyboards.back_to_main()
            )
            return
        
        if payment_result['status'] == 'succeeded':
            # Тестовый платеж - сразу пополняем
            success_text = f"""
✅ *Платеж успешен!*

💵 Сумма: *{amount}₽*
📊 Баланс пополнен
💰 Новый баланс: *{user.balance}₽*

ID платежа: `{payment_result['payment_id']}`
"""
            
            await update.callback_query.edit_message_text(
                success_text,
                parse_mode='Markdown',
                reply_markup=keyboards.back_to_main()
            )
            
        else:
            # РЕАЛЬНЫЙ ПЛАТЕЖ через ЮKassa
            payment_text = f"""
💰 *Оплата {amount}₽*

Для завершения оплаты перейдите по ссылке:
{payment_result['payment_url']}

📱 *Как вернуться в бота после оплаты:*
1. После оплаты НАЖМИТЕ КНОПКУ "Вернуться в магазин"
2. Или просто откройте бота: {payment_result.get('bot_link', 'https://t.me/vpn_outline_shop_bot')}
3. Нажмите /start или любую кнопку

🔄 *Автоматическая проверка:*
• Баланс пополнится автоматически при возвращении в бота
• Или нажмите "Проверить оплату"

⚠️ *Важно:*
• Ссылка действительна 30 минут
• ID платежа: `{payment_result['payment_id']}`
"""
            
            keyboard = [
                [InlineKeyboardButton("🌐 Перейти к оплате", url=payment_result['payment_url'])],
                [InlineKeyboardButton("🤖 Открыть бота", url=payment_result.get('bot_link', 'https://t.me/vpn_outline_shop_bot'))],
                [InlineKeyboardButton("🔄 Проверить оплату", callback_data=f"check_payment_{payment_result['payment_id']}")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ]
            
            await update.callback_query.edit_message_text(
                payment_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
    except Exception as e:
        print(f"Ошибка обработки платежа: {e}")
        await update.callback_query.edit_message_text(
            "❌ Произошла ошибка при создании платежа",
            reply_markup=keyboards.back_to_main()
        )
    finally:
        db.close()
