async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, amount: float):
    """Обработка платежа"""
    db = database.SessionLocal()
    try:
        user_id = update.callback_query.from_user.id
        user = db.query(database.User).filter_by(telegram_id=user_id).first()
        
        if not user:
            await update.callback_query.edit_message_text("❌ Пользователь не найден")
            return
        
        payment_result = await payments.create_payment(db, user_id, amount)
        
        if not payment_result:
            await update.callback_query.edit_message_text(
                "❌ Не удалось создать платеж",
                reply_markup=keyboards.back_to_main()
            )
            return
        
        if payment_result['status'] == 'succeeded':
            success_text = f"✅ Платеж успешен! +{amount}₽"
            await update.callback_query.edit_message_text(
                success_text,
                reply_markup=keyboards.back_to_main()
            )
            
        else:
            # ВАЖНОЕ СООБЩЕНИЕ ДЛЯ ПОЛЬЗОВАТЕЛЯ
            payment_text = f"""
💰 *Оплата {amount}₽*

🌐 *Ссылка для оплаты:*
{payment_result['payment_url']}

⚠️ *ВНИМАНИЕ - ВАЖНАЯ ИНСТРУКЦИЯ:*

1. *После оплаты НЕ НАЖИМАЙТЕ "Вернуться на сайт"*
2. *Просто закройте страницу ЮKassa*
3. *Вернитесь в этого бота*
4. *Нажмите кнопку "🔄 Проверить оплату" ниже*

Или откройте бота: {payment_result.get('bot_link', 'https://t.me/vpn_outline_shop_bot')}

📝 ID платежа: `{payment_result['payment_id']}`
"""
            
            keyboard = [
                [InlineKeyboardButton("🌐 Перейти к оплате", url=payment_result['payment_url'])],
                [InlineKeyboardButton("🔄 Проверить оплату", callback_data=f"check_payment_{payment_result['payment_id']}")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
            ]
            
            await update.callback_query.edit_message_text(
                payment_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
    except Exception as e:
        print(f"Ошибка: {e}")
        await update.callback_query.edit_message_text(
            "❌ Ошибка",
            reply_markup=keyboards.back_to_main()
        )
    finally:
        db.close()
