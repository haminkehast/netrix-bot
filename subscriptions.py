# subscriptions.py
import requests
import math
import time
import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import database

def format_bytes(size):
    if size == 0: return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size, 1024)))
    p = math.pow(1024, i)
    s = round(size / p, 2)
    return f"{s} {size_name[i]}"

def get_sub_info(sub_url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(sub_url, headers=headers, timeout=5)
        userinfo = response.headers.get('subscription-userinfo')
        
        if not userinfo: return None
        
        parts = userinfo.split(';')
        info = {}
        for part in parts:
            if '=' in part:
                key, val = part.strip().split('=')
                info[key.strip()] = int(val.strip())
        return info
    except:
        return None

def register_subscriptions_handlers(bot):
    
    @bot.callback_query_handler(func=lambda call: call.data == "my_subs")
    def my_subscriptions_menu(call):
        user_id = call.from_user.id
        
        conn = database.sqlite3.connect('netrix.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, config_text FROM configs WHERE owner_id = ? AND status = "sold"', (user_id,))
        user_configs = cursor.fetchall()
        
        cursor.execute('SELECT COUNT(*) FROM configs WHERE owner_id = ?', (user_id,))
        total_purchases_ever = cursor.fetchone()[0]
        
        conn.close()

        if not user_configs:
            markup = InlineKeyboardMarkup(row_width=1)
            if total_purchases_ever == 0:
                text = (
                    "📦 **اشتراک‌های من**\n\n"
                    "کاربر گرامی، شما در حال حاضر هیچ سرویس فعالی در NETRIX ندارید.\n\n"
                    "🎁 *پیشنهاد ویژه: برای اولین خرید خود از ۱۰٪ تخفیف بهره‌مند شوید!*"
                )
                markup.add(InlineKeyboardButton("🛒 خرید اولین سرویس (۱۰٪ تخفیف) 🎁", callback_data="shop_main"))
            else:
                text = (
                    "📦 **اشتراک‌های من**\n\n"
                    "کاربر گرامی، در حال حاضر هیچ سرویس فعالی ندارید (یا سرویس‌های شما منقضی شده‌اند)."
                )
                markup.add(InlineKeyboardButton("🛒 خرید سرویس جدید", callback_data="shop_main"))
                
            markup.add(InlineKeyboardButton("🔙 بازگشت به منو", callback_data="main"))
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        else:
            text = (
                "📦 **اشتراک‌های من**\n\n"
                "لیست سرویس‌های شما:\n"
                "👇 برای مشاهده جزئیات و دریافت لینک اتصال، روی سرویس مورد نظر کلیک کنید."
            )
            markup = InlineKeyboardMarkup(row_width=1)
            for index, config in enumerate(user_configs, start=1):
                config_id = config[0]
                markup.add(InlineKeyboardButton(f"🟢 اشتراک شماره {index}", callback_data=f"show_sub_{config_id}"))
            
            markup.add(InlineKeyboardButton("🔙 بازگشت به منو", callback_data="main"))
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("show_sub_"))
    def show_sub_details(call):
        config_id = call.data.split("_")[2]
        
        # اگر کاربر روی دکمه آپدیت کلیک کرده باشد، متن پاپ‌آپ کوتاهی نمایش می‌دهیم
        bot.answer_callback_query(call.id, "🔄 در حال دریافت اطلاعات جدید...", show_alert=False)
        
        conn = database.sqlite3.connect('netrix.db')
        cursor = conn.cursor()
        cursor.execute('SELECT config_text, plan_id FROM configs WHERE id = ?', (config_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            bot.answer_callback_query(call.id, "❌ سرویس یافت نشد!", show_alert=True)
            return
            
        sub_link = result[0]
        sub_info = get_sub_info(sub_link)
        
        if sub_info:
            total = sub_info.get('total', 0)
            upload = sub_info.get('upload', 0)
            download = sub_info.get('download', 0)
            used = upload + download
            rem_bytes = max(0, total - used) if total > 0 else 0
            expire_ts = sub_info.get('expire', 0)
            
            total_str = format_bytes(total)
            used_str = format_bytes(used)
            rem_str = format_bytes(rem_bytes)
            up_str = format_bytes(upload)
            down_str = format_bytes(download)
            
            if expire_ts == 0:
                days_left = "نامحدود"
                status = "فعال 🟢"
            else:
                current_time = int(time.time())
                if current_time > expire_ts:
                    days_left = "منقضی شده"
                    status = "منقضی 🔴"
                else:
                    days_left = f"{math.ceil((expire_ts - current_time) / 86400)} روز"
                    status = "فعال 🟢"
        else:
            total_str = "نامشخص"
            used_str = "نامشخص"
            rem_str = "نامشخص"
            up_str = "نامشخص"
            down_str = "نامشخص"
            days_left = "نامشخص"
            status = "در حال بررسی 🟡"

        current_time_str = datetime.datetime.now().strftime("%H:%M:%S")

        # قالب حرفه‌ای و دقیق درخواست شده
        text = (
            f"📡 **اطلاعات سرویس شما:**\n\n"
            f"وضعیت اشتراک:        {status}\n"
            f"شناسه اشتراک:        `NETRIX-{config_id}`\n"
            f"حجم باقی مانده:      `{rem_str}`\n"
            f"مقدار مصرف:          `{used_str}`\n"
            f"دانلود:              `{down_str}`\n"
            f"آپلود:               `{up_str}`\n"
            f"اعتبار زمانی:         `{days_left}`\n\n"
            f"🔗 **لینک اتصال (سابسکریپشن):**\n"
            f"`{sub_link}`\n\n"
            f"💡 *برای کپی کردن، روی لینک بالا کلیک کنید.*\n"
            f"⏱ آخرین بروزرسانی: `{current_time_str}`"
        )
        
        markup = InlineKeyboardMarkup(row_width=1)
        
        # دکمه آپدیت که دقیقاً همین تابع را دوباره فراخوانی می‌کند
        markup.add(InlineKeyboardButton("🔄 آپدیت اطلاعات", callback_data=f"show_sub_{config_id}"))
        
        # دکمه‌های جانبی در یک ردیف
        markup.row(
            InlineKeyboardButton("🔄 تمدید", callback_data="shop_main"),
            InlineKeyboardButton("📱 آموزش", callback_data="education")
        )
        
        # دکمه بازگشت در پایین
        markup.add(InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="my_subs"))
        
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        except Exception as e:
            # مدیریت خطای احتمالی تکراری بودن پیام
            pass