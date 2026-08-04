from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import database
from shop_data import SHOP_DATA
from config import LOG_GROUP_ID, LOG_TOPIC_ID
import time
from datetime import datetime

try: import requests
except: requests = None

def format_bytes(b):
    if b is None: return "نامشخص"
    b = int(b)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if b < 1024.0: return f"{b:.2f} {unit}"
        b /= 1024.0
    return f"{b:.2f} PB"

def get_marzban_stats(link):
    if not requests or not link or not str(link).startswith("http"): return None
    try:
        res = requests.get(link, timeout=5, headers={'User-Agent': 'v2ray'})
        info = res.headers.get('Subscription-Userinfo') or res.headers.get('subscription-userinfo')
        if info:
            data = {}
            for part in info.split(';'):
                if '=' in part:
                    k, v = part.strip().split('=')
                    data[k.strip()] = int(v.strip())
            return data
    except: pass
    return None

def register_user_panel_handlers(bot):

    @bot.callback_query_handler(func=lambda call: call.data == "free_test")
    def free_test_menu(call):
        text = "🎁 **دریافت تست رایگان**\n\nلطفاً سرویس مورد نظر خود را برای دریافت تست انتخاب کنید:\n(شما از هر سرویس فقط **۱ بار** می‌توانید تست بگیرید)"
        markup = InlineKeyboardMarkup(row_width=1)
        CATEGORIES = {"1": "مولتی لوکیشن VIP 🥇", "2": "مولتی لوکیشن اقتصادی 🥈", "3": "مولتی لوکیشن نامحدود ♾", "4": "آی‌پی ثابت آلمان 🇩🇪", "5": "آی‌پی ثابت آمریکا 🇺🇸 (پیشنهادی) 🇺🇸"}
        for cat_id, cat_name in CATEGORIES.items(): markup.add(InlineKeyboardButton(cat_name, callback_data=f"get_test_{cat_id}"))
        markup.add(InlineKeyboardButton("بازگشت به منو 🔙", callback_data="main"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("get_test_"))
    def process_free_test(call):
        cat_id = call.data.split("_")[2]
        plan_id = f"test_{cat_id}"
        user_id = call.from_user.id
        CATEGORIES = {"1": "مولتی لوکیشن VIP", "2": "مولتی لوکیشن اقتصادی", "3": "مولتی لوکیشن نامحدود", "4": "آی‌پی ثابت آلمان", "5": "آی‌پی ثابت آمریکا"}
        cat_name = CATEGORIES.get(cat_id, "نامشخص")
        
        conn = database.sqlite3.connect('netrix.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM configs WHERE owner_id = ? AND plan_id = ?", (user_id, plan_id))
        if cursor.fetchone()[0] > 0:
            conn.close()
            bot.answer_callback_query(call.id, f"❌ شما قبلاً تست {cat_name} را دریافت کرده‌اید!", show_alert=True)
            return
            
        cursor.execute("SELECT id, config_text FROM configs WHERE plan_id = ? AND status = 'available' LIMIT 1", (plan_id,))
        config = cursor.fetchone()
        
        if not config:
            conn.close()
            bot.answer_callback_query(call.id, f"⚠️ متاسفانه ظرفیت تست {cat_name} تکمیل است.", show_alert=True)
            return
            
        config_id, config_text = config
        cursor.execute("UPDATE configs SET status = 'sold', owner_id = ? WHERE id = ?", (user_id, config_id))
        cursor.execute("SELECT COUNT(*) FROM configs WHERE plan_id = ? AND status = 'available'", (plan_id,))
        remaining_stock = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        
        admin_report = f"🎁 **یک تست رایگان دریافت شد!**\n\n👤 آیدی کاربر: `{user_id}`\n🔹 سرویس: تست {cat_name}\n🔗 کانفیگ تحویل داده شده:\n`{config_text}`\n\n📊 **موجودی باقی‌مانده این تست:** {remaining_stock} عدد"
        try: bot.send_message(LOG_GROUP_ID, admin_report, message_thread_id=LOG_TOPIC_ID, parse_mode="Markdown")
        except: pass
        
        bot.answer_callback_query(call.id, "✅ تست شما فعال شد!", show_alert=False)
        text = f"اطلاعات اشتراک تست شما\n🔮 نام سرویس: {cat_name}\n🔋حجم سرویس: 0.2 گیگ\n⏰ مدت سرویس: 1 روز⁮⁮ ⁮⁮\nو لینک اشتارک:\n\n`{config_text}`"
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("بازگشت به منو 🔙", callback_data="main"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data == "account")
    def account_menu(call):
        user_id = call.from_user.id
        username = f"\u200E@{call.from_user.username}".replace("_", "\\_") if call.from_user.username else "ندارد"
        first_name = call.from_user.first_name.replace("_", "\\_").replace("*", "") if call.from_user.first_name else "کاربر"
        
        try:
            balance = database.get_balance(user_id)
            user_stats = database.get_user_stats(user_id) or {}
        except:
            balance = 0
            user_stats = {}

        conn = database.sqlite3.connect('netrix.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM configs WHERE owner_id = ? AND status = 'sold'", (user_id,))
        real_orders_count = cursor.fetchone()[0]
        conn.close()

        total_spent = user_stats.get('total_spent', 0)
        transactions_count = user_stats.get('transactions_count', 0)
        referrals_count = user_stats.get('referrals_count', 0)
        orders_count = real_orders_count
        active_services = real_orders_count
        ref_code = user_stats.get('ref_code', f"NX{str(user_id)[-5:]}")
        account_status = "کاربر VIP 🌟" if total_spent >= 1000000 else "کاربر عادی 👤"
        
        text = (
            f"👤 **حساب کاربری شما در NETRIX**\n\n"
            f"🔻 **مشخصات شما:**\n"
            f"🛡 شناسه: `{user_id}`\n"
            f"🏖 نام کاربری: {username}\n"
            f"🧑‍💼 نام: **{first_name}**\n"
            f"☑️ وضعیت اکانت: **{account_status}**\n"
            f"🔗 لینک دعوت شما:\n`https://t.me/Asedrkdbxhbot?start={ref_code}`\n\n"
            f"🔻 **کیف پول و تراکنش‌ها:**\n"
            f"💰 موجودی: **{balance:,}** تومان\n"
            f"💵 تراکنش کل: **{total_spent:,}** تومان\n"
            f"🗒 تعداد تراکنش‌ها: **{transactions_count}**\n\n"
            f"🔻 **سرویس‌ها و زیرمجموعه:**\n"
            f"📑 تعداد سفارشات: **{orders_count}**\n"
            f"🟢 سرویس‌های فعال: **{active_services}**\n"
            f"👥 تعداد زیرمجموعه: **{referrals_count}**"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💵 شارژ کیف پول", callback_data="wallet"))
        markup.add(InlineKeyboardButton("بازگشت به منو 🔙", callback_data="main"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data == "my_subs")
    def my_subscriptions(call):
        user_id = call.from_user.id
        conn = database.sqlite3.connect('netrix.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, plan_id FROM configs WHERE owner_id = ? AND status = 'sold'", (user_id,))
        user_configs = cursor.fetchall()
        conn.close()

        if not user_configs:
            text = "🎁 **هدیه ویژه اولین خرید!**\n\nشما هنوز هیچ اشتراکی در NETRIX ندارید.\nهمین الان اولین خرید خود را انجام دهید و **10% تخفیف** به صورت خودکار روی سفارشتان اعمال خواهد شد!\n\n👇 جهت استفاده از این فرصت روی دکمه زیر کلیک کنید:"
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🛒 خرید اولین اشتراک (10% تخفیف)", callback_data="shop_main"))
            markup.add(InlineKeyboardButton("بازگشت به منو 🔙", callback_data="main"))
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
            return

        text = "اشتراک‌های من 📦\n\nلیست سرویس‌های شما:\n👇 برای مشاهده جزئیات و دریافت لینک اتصال، روی سرویس مورد نظر کلیک کنید."
        markup = InlineKeyboardMarkup(row_width=1)
        shop_keys_mapping = {"1": "vip", "2": "eco", "3": "unlim", "4": "ger", "5": "usa"}
        
        for c_id, p_id in user_configs:
            display_name = "اشتراک نامشخص"
            if str(p_id).startswith("test_"):
                real_id = str(p_id).split("_")[1]
                CATEGORIES_TEST = {"1": "VIP", "2": "اقتصادی", "3": "نامحدود", "4": "آلمان", "5": "آمریکا"}
                display_name = f"تست رایگان {CATEGORIES_TEST.get(real_id, '')}"
            elif p_id and "_" in str(p_id):
                try:
                    parts = str(p_id).split("_")
                    shop_key = shop_keys_mapping.get(parts[0])
                    m_id = parts[1]
                    p_idx = int(parts[2])
                    c_info = SHOP_DATA.get(shop_key)
                    if c_info:
                        m_info = c_info["months"].get(m_id)
                        pkg_name = m_info["packages"][p_idx][0]
                        display_name = f"{c_info['title']} | {pkg_name} {m_info['title']}"
                except: pass
            markup.add(InlineKeyboardButton(f"{display_name} 🟢", callback_data=f"sub_detail_{c_id}"))
        
        markup.add(InlineKeyboardButton("بازگشت به منو 🔙", callback_data="main"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("sub_detail_") or call.data.startswith("sub_update_"))
    def sub_details(call):
        c_id = call.data.split("_")[2]
        conn = database.sqlite3.connect('netrix.db')
        cursor = conn.cursor()
        cursor.execute("SELECT config_text, plan_id FROM configs WHERE id = ?", (c_id,))
        config = cursor.fetchone()
        conn.close()

        if not config:
            bot.answer_callback_query(call.id, "❌ این اشتراک یافت نشد.", show_alert=True)
            return

        config_text, p_id = config
        stats = get_marzban_stats(config_text)
        now = datetime.now().strftime("%H:%M:%S")
        
        if stats:
            total = stats.get('total', 0)
            used = stats.get('upload', 0) + stats.get('download', 0)
            remain = total - used if total > used else 0
            expire_ts = stats.get('expire', 0)
            days_left = f"{max(0, int((expire_ts - time.time()) / 86400))} روز" if expire_ts else "نامحدود"
            remain_str = format_bytes(remain)
            used_str = format_bytes(used)
            down_str = format_bytes(stats.get('download', 0))
            up_str = format_bytes(stats.get('upload', 0))
        else:
            remain_str, used_str, down_str, up_str, days_left = "نامشخص (نیاز به اتصال)", "نامشخص", "نامشخص", "نامشخص", "نامشخص"

        text = (
            f"اطلاعات سرویس شما: 📡\n\nوضعیت اشتراک: 🟢 فعال\nشناسه اشتراک: `NETRIX-{c_id}`\n"
            f"حجم باقی مانده: **{remain_str}**\nمقدار مصرف: **{used_str}**\nدانلود: **{down_str}**\nآپلود: **{up_str}**\nاعتبار زمانی: **{days_left}**\n\n"
            f"🔗 لینک اتصال (سابسکریپشن):\n`{config_text}`\n\n💡 برای کپی کردن، روی لینک بالا کلیک کنید.\n⏱ آخرین بروزرسانی: {now}"
        )
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(InlineKeyboardButton("🔄 آپدیت اطلاعات", callback_data=f"sub_update_{c_id}"))
        markup.add(InlineKeyboardButton("آموزش 📱", callback_data="tutorial"), InlineKeyboardButton("تمدید 🔄", callback_data=f"renew_{c_id}"))
        markup.add(InlineKeyboardButton("بازگشت به لیست 🔙", callback_data="my_subs"))
        
        if call.data.startswith("sub_update_"):
            try:
                bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
                bot.answer_callback_query(call.id, "✅ اطلاعات با موفقیت بروزرسانی شد!", show_alert=False)
            except: bot.answer_callback_query(call.id, "⚠️ اطلاعات از قبل بروز است.", show_alert=False)
        else: bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data == "tutorial" or call.data.startswith("renew_"))
    def coming_soon(call): bot.answer_callback_query(call.id, "🚀 این بخش به زودی فعال می‌شود!", show_alert=True)

    @bot.callback_query_handler(func=lambda call: call.data == "support")
    def support_menu(call):
        text = "☎️ **مرکز پشتیبانی هوشمند NETRIX**\n\nکاربر گرامی، تیم پشتیبانی ما آماده پاسخگویی به سوالات و رفع مشکلات شماست.\n\n💡 *پیشنهاد می‌کنیم پیش از ارسال پیام به پشتیبانی، ابتدا بخش «سوالات متداول» را مطالعه فرمایید؛ شاید پاسخ شما آنجا باشد.*\n\n👇 جهت ادامه، یکی از گزینه‌های زیر را انتخاب کنید:"
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("💬 ارتباط با پشتیبانی", url="https://t.me/NetrixVIPSupport"), InlineKeyboardButton("❓ سوالات متداول", callback_data="faq"), InlineKeyboardButton("🔙 بازگشت به منو", callback_data="main"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data == "faq")
    def faq_menu(call):
        text = "❓ **سوالات متداول (FAQ)**\n\n**۱. چگونه حساب خود را شارژ کنم؟**\nاز منوی اصلی وارد بخش «کیف پول من» شده و مبلغ مورد نظر را برای دریافت فاکتور انتخاب کنید.\n\n**۲. سرویس‌ها چقدر اعتبار دارند؟**\nبسته به نوع اشتراکی که تهیه می‌کنید، زمان و حجم آن در بخش «اشتراک‌های من» به صورت لحظه‌ای قابل مشاهده است.\n\n**۳. تأیید رسید پرداخت چقدر زمان می‌برد؟**\nرسیدهای شما به صورت خودکار و در کمتر از ۱ دقیقه توسط تیم پشتیبانی بررسی و اعمال می‌شوند.\n"
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت به پشتیبانی", callback_data="support"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")