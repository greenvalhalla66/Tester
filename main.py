import logging
import sqlite3
import os
import uuid
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import qrcode

#=== НАСТРОЙКИ ===
TOKEN = "8461887435:AAEFLMXQzzVStz7jVmjLL0eCSaf2rxN0g9g"  # ← Замените на токен от BotFather
ADMIN_ID = 8473087607  # ← Замените на свой Telegram ID
DB_NAME = "queue_bot.db"
QR_FOLDER = "qr_codes"

#=== ЛОГИРОВАНИЕ ===
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

#=== ИНИЦИАЛИЗАЦИЯ БД ===
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance REAL DEFAULT 0.0,
                ref_id INTEGER,
                level INTEGER DEFAULT 1
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS queue (
                user_id INTEGER PRIMARY KEY,
                qr_code TEXT,
                paid BOOLEAN DEFAULT FALSE,
                entry_time TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                amount REAL,
                status TEXT,  -- pending, paid, rejected
                created_at TIMESTAMP
            )
        """)
        conn.commit()

#=== СОЗДАНИЕ ПАПКИ ДЛЯ QR ===
if not os.path.exists(QR_FOLDER):
    os.makedirs(QR_FOLDER)

#=== КОМАНДА /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "no_username"
    ref_id = None

    if context.args:
        try:
            ref_id = int(context.args[0])
        except ValueError:
            logger.warning(f"Некорректный реферальный ID: {context.args[0]}")

    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO users (user_id, username, ref_id) VALUES (?, ?, ?)",
                (user_id, username, ref_id),
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Ошибка регистрации пользователя {user_id}: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
        return

    await update.message.reply_text(
        "Добро пожаловать!\n"
        "Используйте /menu для открытия главного меню."
    )

#=== КОМАНДА /menu ===
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Моя очередь", callback_data="queue")],
        [InlineKeyboardButton("Личный кабинет", callback_data="profile")],
        [InlineKeyboardButton("Реферальная программа", callback_data="ref")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Главное меню:", reply_markup=reply_markup)

#=== ОБРАБОТКА КНОПОК ===
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "queue":
        try:
            qr_path = os.path.join(QR_FOLDER, f"qr_{user_id}.png")
            if not os.path.exists(qr_path):
                qr = qrcode.make(f"queue://{user_id}")
                qr.save(qr_path)
            with open(qr_path, "rb") as qr_file:
                await query.message.reply_photo(qr_file)
            await query.message.reply_text(
                "Отсканируйте QR‑код и произведите оплату.\n"
                "После оплаты сообщите администратору ID платежа."
            )
        except Exception as e:
            logger.error(f"Ошибка генерации QR для {user_id}: {e}")
            await query.message.reply_text("Ошибка при генерации QR‑кода.")

    elif query.data == "profile":
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                user = cursor.execute(
                    "SELECT balance FROM users WHERE user_id = ?", (user_id,)
                ).fetchone()
            if user:
                balance = user[0]
                await query.message.reply_text(f"Баланс: {balance:.2f} ₽")
            else:
                await query.message.reply_text("Пользователь не найден.")
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения профиля {user_id}: {e}")
            await query.message.reply_text("Ошибка при получении данных.")

    elif query.data == "ref":
        ref_link = f"https://t.me/your_bot_username?start={user_id}"  # Replace with your bot username
        await query.message.reply_text(
            f"Ваша реферальная ссылка:\n{ref_link}\n\n"
            "Вы получаете:\n"
            "• 10% от платежей приглашённых на 1 уровне\n"
            "• 5% — на 2 уровне\n"
            "• 2% — на 3 уровне"
        )

    # Обработка подтверждения/отклонения платежа (админ)
    elif query.data.startswith("confirm_"):
        if query.from_user.id != ADMIN_ID:
            await query.message.reply_text("Доступ запрещён.")
            return
        payment_id = query.data.replace("confirm_", "")
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                # Проверяем, что платёж в статусе pending
                cursor.execute(
                    "SELECT user_id, amount FROM payments WHERE id = ? AND status = 'pending'",
                    (payment_id,),
                )
                payment = cursor.fetchone()
                if not payment:
                    await query.message.reply_text("Платёж не найден или уже обработан.")
                    return

                user_id, amount = payment

                # Обновляем статус платежа
                cursor.execute(
                    "UPDATE payments SET status = 'paid' WHERE id = ?",
                    (payment_id,),
                )
                # Обновляем очередь
                cursor.execute(
                    "UPDATE queue SET paid = TRUE, entry_time = ? WHERE user_id = ?",
                    (datetime.now(), user_id),
                )
                # Начисляем реферальные бонусы (упрощённо)
                await assign_referral_bonus(user_id, amount, conn)
                conn.commit()

            await query.message.reply_text(f"Платёж {payment_id} подтверждён.")
        except sqlite3.Error as e:
            logger.error(f"Ошибка подтверждения платежа {payment_id}: {e}")
            await query.message.reply_text("Ошибка при подтверждении платежа.")

    elif query.data.startswith("reject_"):
        if query.from_user.id != ADMIN_ID:
            await query.message.reply_text("Доступ запрещён.")
            return
        payment_id = query.data.replace("reject_", "")
        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE payments SET status = 'rejected' WHERE id = ? AND status = 'pending'",
                    (payment_id,),
                )
                conn.commit()
            await query.message.reply_text(f"Платёж {payment_id} отклонён.")
        except sqlite3.Error as e:
            logger.error(f"Ошибка отклонения платежа {payment_id}: {e}")
            await query.message.reply_text("Ошибка при отклонении платежа.")

async def assign_referral_bonus(user_id, amount, conn):
    """Assigns referral bonuses."""
    cursor = conn.cursor()
    # Get the referral chain for the user
    referral_chain = []
    current_user_id = user_id
    for level in range(1, 4):
        cursor.execute("SELECT ref_id FROM users WHERE user_id = ?", (current_user_id,))
        result = cursor.fetchone()
        if result and result[0]:
            referral_chain.append(result[0])
            current_user_id = result[0]
        else:
            break  # Stop if no referral found

    # Calculate and assign bonuses to referral levels.
    bonuses = {
        1: 0.10,  # 10%
        2: 0.05,  # 5%
        3: 0.02,  # 2%
    }
    for level, referrer_id in enumerate(referral_chain):
        if level + 1 <= 3:  # Only process up to 3 levels
            bonus_percentage = bonuses.get(level + 1, 0)
            bonus_amount = amount * bonus_percentage
            try:
                cursor.execute(
                    "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                    (bonus_amount, referrer_id),
                )
            except sqlite3.Error as e:
                logger.error(f"Error awarding bonus to {referrer_id}: {e}")
    conn.commit()

#=== ЗАПУСК БОТА ===
if __name__ == "__main__":
    init_db()  # Initialize the database when the script starts
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling()