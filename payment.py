import qrcode
import requests
from db import update_balance

def generate_qr_payment(update, context, amount):
    # Здесь должен быть вызов API Яндекс Pay для создания ссылки/QR
    # Для примера — генерируем QR с текстом
    qr = qrcode.make(f"yandex-pay://pay?amount={amount}")
    qr.save("payment.png")

    context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=open("payment.png", "rb"),
        caption=f"Оплатите {amount} руб. через Яндекс Pay"
    )

    # Сохраняем в БД для подтверждения
    conn = sqlite3.connect('bot.db')
    conn.execute(
        "INSERT INTO payments (user_id, amount, qr_code, confirmed) VALUES (?, ?, ?, 0)",
        (update.effective_user.id, amount, "dummy_qr_code")
    )
    conn.commit()
    conn.close()
