# database.py
import sqlite3
import random
import string

def init_db():
    conn = sqlite3.connect('netrix.db')
    cursor = conn.cursor()
    
    # جدول کاربران
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            referral_code TEXT UNIQUE,
            inviter_id INTEGER,
            total_purchases INTEGER DEFAULT 0,
            total_spent INTEGER DEFAULT 0,
            name TEXT
        )
    ''')
    
    # ================= ارتقای هوشمند دیتابیس =================
    # این بخش ستون‌های جدید حسابداری رو بدون پاک شدن اطلاعات قبلی به دیتابیس اضافه میکنه
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN total_deposited INTEGER DEFAULT 0")
    except:
        pass # اگر از قبل وجود داشت ارور نمیده

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN deposit_count INTEGER DEFAULT 0")
    except:
        pass
        
    # همگام‌سازی اکانت‌های قدیمی: اگر کسی از قبل پولی در کیفش دارد، همان را به عنوان اولین تراکنش کلش ثبت کن
    cursor.execute('UPDATE users SET total_deposited = balance, deposit_count = 1 WHERE balance > 0 AND total_deposited = 0')
    # =========================================================

    # جدول کانفیگ‌ها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_text TEXT,
            status TEXT DEFAULT 'available',
            plan_id INTEGER,
            owner_id INTEGER
        )
    ''')
    
    # جداول دسته‌بندی و محصولات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            parent_id INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            name TEXT,
            duration TEXT,
            price INTEGER
        )
    ''')
    
    # جدول تراکنش‌ها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            type TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("🗄 ساختار دیتابیس NETRIX با موفقیت ارتقا یافت (بخش مالی هوشمند شد).")

def generate_referral_code():
    while True:
        code = "NX" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        conn = sqlite3.connect('netrix.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE referral_code = ?', (code,))
        if not cursor.fetchone():
            conn.close()
            return code
        conn.close()

# تابع ثبت نام ارتقا یافته برای دریافت لینک دعوت
def add_user(user_id, name="User", inviter_code=None):
    conn = sqlite3.connect('netrix.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    
    if not cursor.fetchone():
        ref_code = generate_referral_code()
        inviter_id = None
        
        # اگر کاربر با لینک دعوت کسی وارد شده باشد
        if inviter_code:
            cursor.execute('SELECT user_id FROM users WHERE referral_code = ?', (inviter_code,))
            inviter_row = cursor.fetchone()
            if inviter_row:
                inviter_id = inviter_row[0]
                
        cursor.execute('''
            INSERT INTO users (user_id, referral_code, name, inviter_id) 
            VALUES (?, ?, ?, ?)
        ''', (user_id, ref_code, name, inviter_id))
        conn.commit()
    conn.close()

def get_user_stats(user_id):
    conn = sqlite3.connect('netrix.db')
    cursor = conn.cursor()
    
    # فراخوانی دقیق ستون‌های حسابداری جدید
    cursor.execute('SELECT referral_code, name, total_deposited, balance, deposit_count FROM users WHERE user_id = ?', (user_id,))
    data = cursor.fetchone()
    
    cursor.execute('SELECT COUNT(*) FROM users WHERE inviter_id = ?', (user_id,))
    referral_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM transactions WHERE user_id = ? AND type = "purchase"', (user_id,))
    order_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM configs WHERE owner_id = ? AND status = "sold"', (user_id,))
    active_services = cursor.fetchone()[0]
    
    conn.close()
    
    if data:
        return {
            'ref_code': data[0],
            'name': data[1],
            'total_spent': data[2],         # این کلید مقادیرِ تراکنش کل (Total Deposited) را به ظاهر ربات می‌فرستد
            'balance': data[3],
            'transactions_count': data[4],  # این کلید تعداد دفعات شارژ را می‌فرستد
            'orders_count': order_count,
            'referrals_count': referral_count,
            'active_services': active_services
        }
    return None

def get_balance(user_id):
    conn = sqlite3.connect('netrix.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0]
    return 0

# تابع مالی کاملا ایزوله و منطقی
def update_balance(user_id, amount):
    conn = sqlite3.connect('netrix.db')
    cursor = conn.cursor()
    
    if amount > 0:
        # حالت اول: ادمین یا سیستم کاربر را شارژ می‌کند (افزایش موجودی + افزایش تراکنش کل + یک تراکنش موفق)
        cursor.execute('''
            UPDATE users 
            SET balance = balance + ?, 
                total_deposited = total_deposited + ?, 
                deposit_count = deposit_count + 1 
            WHERE user_id = ?
        ''', (amount, amount, user_id))
        
        cursor.execute('INSERT INTO transactions (user_id, amount, type) VALUES (?, ?, ?)', (user_id, amount, 'deposit'))
    else:
        # حالت دوم: خرید سرویس یا کسر دستی (فقط کسر از موجودی، بدون دست زدن به تراکنش کل)
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        
        # ثبت در تاریخچه به عنوان کسر/خرید
        cursor.execute('INSERT INTO transactions (user_id, amount, type) VALUES (?, ?, ?)', (user_id, amount, 'deduction'))
        
    conn.commit()
    conn.close()