from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from db import get_rate, set_rate, get_user

def admin_panel(update, context):
    rate = get_rate()
    keyboard = [
        [InlineKeyboardButton(f!Ставка: {rate} руб/сек", callback_data="edit_rate")],
        [InlineKeyboardButton("Пользователи", callback_data="list_users")],
        [InlineKeyboardButton("Пополнения", callback_data="list_payments")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Админ‑панель:", reply_markup=reply_markup)

def edit_rate(update, context):
    query = update.callback_query
    query.answer()
    query.edit_message_text("Введите новую ставку (руб/сек):")
    context.user_data['waiting_for_rate'] = True

def handle_admin_input(update, context):
    if context.user_data.get('waiting_for_rate'):
        try:
            new_rate = float(update.message.text)
            set_rate(new_rate)
            update.message.reply_text(f"Ставка обновлена: {new_rate} руб/сек")
        except:
            update.message.reply_text("Ошибка: введите число.")
        context.user_data['waiting_for_rate'] = False
