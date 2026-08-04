import psycopg2
import random
import string
import os

# آدرس دیتابیس ابری شما (در مرحله بعد این لینک را می‌گیریم و اینجا می‌گذاریم)
DB_URL = os.environ.get("DATABASE_URL", "آدرس_دیتابیس_شما_اینجا_قرار_میگیرد")

def get_connection():
    # اتصال به دیتابیس آنلاین
    return psycopg2.connect(DB_URL)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # جدول کاربران
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            balance BIGINT DEFAULT 0,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            referral_code TEXT UNIQUE,
            inviter_id BIGINT,
            total_purchases BIGINT DEFAULT 0,
            total_spent BIGINT DEFAULT 0,
            name TEXT,
            total_deposited BIGINT DEFAULT 0,
            deposit_count INTEGER DEFAULT 0
        )
    ''')
    
    # همگام‌سازی اکانت‌های قدیمی (در دیتابیس جدید)
    cursor.execute('UPDATE users SET total_deposited = balance, deposit_count = 1 WHERE balance > 0 AND total_deposited = 0')

    # جدول کانفیگ‌ها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configs (
            id SERIAL PRIMARY KEY,
            config_text TEXT,
            status TEXT DEFAULT 'available',
            plan_id INTEGER,
            owner_id BIGINT
        )
    ''')
    
    # جداول دسته‌بندی و محصولات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            name TEXT,
            parent_id INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            category_id INTEGER,
            name TEXT,
            duration TEXT,
            price BIGINT
        )
    ''')
    
    # جدول تراکنش‌ها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            amount BIGINT,
            type TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()
    print("🗄 ساختار دیتابیس ابری NETRIX با موفقیت راه‌اندازی شد.")

def generate_referral_code():
    while True:
        code = "NX" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE referral_code = %s', (code,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return code
        cursor.close()
        conn.close()

# تابع ثبت نام ارتقا یافته
def add_user(user_id, name="User", inviter_code=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users WHERE user_id = %s', (user_id,))
    
    if not cursor.fetchone():
        ref_code = generate_referral_code()
        inviter_id = None
        
        # اگر کاربر با لینک دعوت کسی وارد شده باشد
        if inviter_code:
            cursor.execute('SELECT user_id FROM users WHERE referral_code = %s', (inviter_code,))
            inviter_row = cursor.fetchone()
            if inviter_row:
                inviter_id = inviter_row[0]
                
        cursor.execute('''
            INSERT INTO users (user_id, referral_code, name, inviter_id) 
            VALUES (%s, %s, %s, %s)
        ''', (user_id, ref_code, name, inviter_id))
        conn.commit()
    cursor.close()
    conn.close()

def get_user_stats(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT referral_code, name, total_deposited, balance, deposit_count FROM users WHERE user_id = %s', (user_id,))
    data = cursor.fetchone()
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE inviter_id = %s', (user_id,))
    referral_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM transactions WHERE user_id = %s AND type = %s', (user_id, 'purchase'))
    order_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM configs WHERE owner_id = %s AND status = %s', (user_id, 'sold'))
    active_services = cursor.fetchone()[0]
    
    cursor.close()
    conn.close()
    
    if data:
        return {
            'ref_code': data[0],
            'name': data[1],
            'total_spent': data[2],         
            'balance': data[3],
            'transactions_count': data[4],  
            'orders_count': order_count,
            'referrals_count': referral_count,
            'active_services': active_services
        }
    return None

def get_balance(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE user_id = %s', (user_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    if result:
        return result[0]
    return 0

# تابع مالی کاملا ایزوله و منطقی
def update_balance(user_id, amount):
    conn = get_connection()
    cursor = conn.cursor()
    
    if amount > 0:
        cursor.execute('''
            UPDATE users 
            SET balance = balance + %s, 
                total_deposited = total_deposited + %s, 
                deposit_count = deposit_count + 1 
            WHERE user_id = %s
        ''', (amount, amount, user_id))
        
        cursor.execute('INSERT INTO transactions (user_id, amount, type) VALUES (%s, %s, %s)', (user_id, amount, 'deposit'))
    else:
        cursor.execute('UPDATE users SET balance = balance + %s WHERE user_id = %s', (amount, user_id))
        cursor.execute('INSERT INTO transactions (user_id, amount, type) VALUES (%s, %s, %s)', (user_id, amount, 'deduction'))
        
    conn.commit()
    cursor.close()
    conn.close()
