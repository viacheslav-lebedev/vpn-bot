from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import config

def main_menu(is_admin=False):
    keyboard = [
        [InlineKeyboardButton("🆓 Пробный тариф", callback_data="tariff_trial")],
        [InlineKeyboardButton("💰 Пополнить баланс", callback_data="balance_deposit")],
        [InlineKeyboardButton("📊 Мой баланс", callback_data="balance_info")],
        [InlineKeyboardButton("🛒 Купить тариф", callback_data="buy_tariff")],
        [InlineKeyboardButton("🔑 Мои ключи", callback_data="my_keys")],
        [InlineKeyboardButton("📞 Техподдержка", url="https://t.me/IdazaneRenn")]
    ]
    
    if is_admin:
        keyboard.append([InlineKeyboardButton("👑 Админ панель", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(keyboard)

def tariffs_keyboard(user_trial_used=False):
    keyboard = []
    
    if not user_trial_used:
        trial_tariff = config.Config.TARIFFS["trial"]
        keyboard.append([
            InlineKeyboardButton(
                f"🆓 {trial_tariff['name']} - БЕСПЛАТНО", 
                callback_data="tariff_trial"
            )
        ])
    
    for tariff_id in ["1day", "1month", "3months", "6months"]:
        tariff = config.Config.TARIFFS[tariff_id]
        keyboard.append([
            InlineKeyboardButton(
                f"{tariff['name']} - {tariff['price']}₽", 
                callback_data=f"tariff_{tariff_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def deposit_amounts_keyboard():
    amounts = [50, 100, 200, 500, 1000]
    keyboard = []
    
    row = []
    for amount in amounts:
        row.append(InlineKeyboardButton(f"{amount}₽", callback_data=f"deposit_{amount}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)

def back_to_main():
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Главное меню", callback_data="main_menu")]])
