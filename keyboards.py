# keyboards.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_ID

def get_main_markup(user_id):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton("خرید اشتراک جدید 🛒", callback_data="shop_main"))
    markup.add(InlineKeyboardButton("اشتراک های من 📦", callback_data="my_subs"), 
               InlineKeyboardButton("کیف پول من 💳", callback_data="wallet"))
    markup.add(InlineKeyboardButton("دریافت تست رایگان 🎁", callback_data="free_test"), 
               InlineKeyboardButton("حساب کاربری 👤", callback_data="account"))
    markup.add(InlineKeyboardButton("آموزش استفاده 📚", callback_data="education"), 
               InlineKeyboardButton("پشتیبانی ☎️", callback_data="support"))
    if user_id == ADMIN_ID:
        markup.add(InlineKeyboardButton("انبار کانفیگ ها 🗄", callback_data="inventory"), 
                   InlineKeyboardButton("پنل مدیریت ⚙️", callback_data="admin_panel"))
    return markup

def get_back_markup(callback_data):
    return InlineKeyboardMarkup().add(InlineKeyboardButton("بازگشت 🔙", callback_data=callback_data))