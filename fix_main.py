with open('main.py', 'w', encoding='utf-8') as f:
    f.write('''# -*- coding: utf-8 -*-
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import config

logging.basicConfig(level=logging.INFO)
print("BOT STARTING")

def menu():
    kb = [[InlineKeyboardButton("Deposit", callback_data="deposit")],
          [InlineKeyboardButton("Balance", callback_data="balance")]]
    return InlineKeyboardMarkup(kb)

async def start(update, context):
    await update.message.reply_text("Hello!", reply_markup=menu())

async def btn(update, context):
    query = update.callback_query
    await query.answer()
    if query.data == "deposit":
        await query.edit_message_text("Enter amount:")

def main():
    try:
        token = config.Config.BOT_TOKEN
        app = Application.builder().token(token).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(btn))
        app.run_polling()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()''')
print("File created")
