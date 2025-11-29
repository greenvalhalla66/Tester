import sqlite3

def init_db():
    conn = sqlite3.connect('bot.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0,
            referral_id INTEGER,
            referred_by INTEGER,
            is_admin BOOLEAN DEFAULT 0
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            qr_code TEXT,
            confirmed BOOLEAN DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_user(user_id, referred_by=None):
    conn = sqlite3.connect('bot.db')
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id, referred_by) VALUES (?, ?)",
        (user_id, referred_by)
    )
    conn.commit()
    conn.close()

def update_balance(user_id, amount):
    conn = sqlite3.connect('bot.db')
    conn.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id = ?",
        (amount, user_id)
    )
    conn.commit()
    conn.close()

def set_rate(new_rate):
    with open('rate.txt', 'w') as f:
        f.write(str(new_rate))

def get_rate():
    try:
        with open('rate.txt', 'r') as f:
            return float(f.read())
    except:
        return 0.01
""