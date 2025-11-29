from db import get_user, create_user

def generate_referral_link(user_id):
    return f"https://t.me/yourbot?start=ref{user_id}"

def process_referral(user_id, ref_id):
    if ref_id and user_id != ref_id:
        referrer = get_user(ref_id)
        if referrer:
            create_user(user_id, referred_by=ref_id)
            # Начислить бонус за привлечение
            from db import update_balance
            update_balance(ref_id, 10.0)  # +10 руб. за реферала
            return True
    return False
