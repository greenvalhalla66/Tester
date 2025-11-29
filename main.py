from telegram import Update, ForceReply
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
)
import threading
import time
from config import TOKEN, ADMIN_ID, SECONDS_PER_TICK
from db import init_db, get_user, create_user, update_balance, get_rate
from referral import process_referral, generate_referral_link
from admin import admin_panel, edit_rate, handle_admin_input
from payment import generate_qr_payment

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    ref_id = None

    # Обработка реферальной ссылки
    if context.args and context.args[0].startswith("ref"):
        ref_id = int(context.args[0][3:])

    create_user(user_id, ref_id)
    process_referral(user_id, ref_id)

    update.message.reply_text(
        f"Привет! Твой баланс: {get_user(user_id)[2]} руб.\n"
        f"Реферальная ссылка: {generate_referral_link(user_id)}"
    )

def balance(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if user:
        update.message.reply_text(f"Баланс: {user[2]:.2f} руб.")

def pay(update: Update, context: CallbackContext):
    try:
        amount = float(context.args[0])
        generate_qr_payment(update, context, amount)
    except:
        update.message.reply_text("Используйте: /pay <сумма>")

def tick():
    rate = get_rate()
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    for row in cursor.fetch