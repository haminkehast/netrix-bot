# admin_panel.py
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import database
from config import ADMIN_ID
import time
from datetime import datetime
from shop_data import SHOP_DATA

# ================= ایجاد جدول تنظیمات در دیتابیس =================
def init_settings_db():
    conn = database.get_db_connection()
    if not conn:
        return
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT)''')
    conn.commit()
    cursor.close()
    conn.close()

def get_setting(key, default=""):
    conn = database.get_db_connection()
    if not conn:
        return default
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key=%s", (key,))
    res = cursor.fetchone()
    cursor.close()
    conn.close()
    return res[0] if res else default

def register_admin_handlers(bot):
    init_settings_db()

    # ================= 1. منوی اصلی مدیریت (داشبورد) =================
    @bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
    def admin_main_menu(call):
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        if int(call.from_user.id) != int(ADMIN_ID): return
        
        text = (
            "⚙️ **پنل مدیریت مرکزی NETRIX**\n\n"
            "مدیریت محترم، به سیستم یکپارچه کنترل خوش آمدید 🌹\n"
            "جهت بررسی و مدیریت بخش‌های مختلف، از منوی زیر استفاده کنید:"
        )
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("📊 آمار و مانیتورینگ سیستم", callback_data="admin_stats_menu"),
            InlineKeyboardButton("🗄 مدیریت انبار و کانفیگ‌ها", callback_data="inventory"),
            InlineKeyboardButton("⚙️ تنظیمات ربات (متن و قیمت‌ها)", callback_data="admin_settings"),
            InlineKeyboardButton("👥 مدیریت کاربران و کیف پول", callback_data="admin_users"),
            InlineKeyboardButton("🧾 گزارش آخرین فروش‌ها", callback_data="admin_recent_sales"),
            InlineKeyboardButton("🏆 لیست برترین خریداران", callback_data="admin_top_buyers"),
            InlineKeyboardButton("📣 ارسال پیام همگانی (پیشرفته)", callback_data="admin_broadcast_adv"),
            InlineKeyboardButton("🔙 بازگشت به منوی ربات", callback_data="main")
        )
        try: bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        except: bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

    @bot.message_handler(commands=['admin'])
    def admin_command(message):
        bot.clear_step_handler_by_chat_id(message.chat.id)
        if int(message.from_user.id) == int(ADMIN_ID):
            class FakeCall:
                def __init__(self, message):
                    self.message = message
                    self.from_user = message.from_user
            admin_main_menu(FakeCall(message))


    # ================= 2. تنظیمات پیشرفته (قیمت و متن) =================
    @bot.callback_query_handler(func=lambda call: call.data == "admin_settings")
    def admin_settings_menu(call):
        if int(call.from_user.id) != int(ADMIN_ID): return
        text = "⚙️ **تنظیمات پیشرفته سیستم**\n\nمدیر گرامی، در این بخش می‌توانید بدون نیاز به کدنویسی، قیمت‌ها و متن‌های ربات را به صورت زنده تغییر دهید:"
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("💲 ویرایش زنده قیمت سرویس‌ها", callback_data="edit_prices_main"),
            InlineKeyboardButton("📝 ویرایش متن‌های ربات", callback_data="edit_texts_main"),
            InlineKeyboardButton("🔙 بازگشت به داشبورد", callback_data="admin_panel")
        )
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    # ----------- ویرایش قیمت‌ها -----------
    @bot.callback_query_handler(func=lambda call: call.data == "edit_prices_main")
    def edit_prices_main(call):
        if int(call.from_user.id) != int(ADMIN_ID): return
        text = "💲 **ویرایش قیمت‌ها**\n\nلطفاً دسته‌بندی سرویس مورد نظر را جهت تغییر قیمت انتخاب کنید:"
        markup = InlineKeyboardMarkup(row_width=1)
        for shop_key, cat_info in SHOP_DATA.items():
            markup.add(InlineKeyboardButton(cat_info['title'], callback_data=f"edpr_c_{shop_key}"))
        markup.add(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("edpr_c_"))
    def edit_prices_cat(call):
        if int(call.from_user.id) != int(ADMIN_ID): return
        shop_key = call.data.split("_")[2]
        cat_info = SHOP_DATA[shop_key]
        text = f"💲 **سرویس:** {cat_info['title']}\n\nلطفاً مدت زمان مورد نظر را انتخاب کنید:"
        markup = InlineKeyboardMarkup(row_width=1)
        for month_id, month_info in cat_info['months'].items():
            markup.add(InlineKeyboardButton(month_info['title'], callback_data=f"edpr_m_{shop_key}_{month_id}"))
        markup.add(InlineKeyboardButton("🔙 بازگشت", callback_data="edit_prices_main"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("edpr_m_"))
    def edit_prices_month(call):
        if int(call.from_user.id) != int(ADMIN_ID): return
        parts = call.data.split("_")
        shop_key, month_id = parts[2], parts[3]
        month_info = SHOP_DATA[shop_key]['months'][month_id]
        
        text = f"💲 **انتخاب حجم**\n\nبسته مورد نظر را جهت ویرایش قیمت کلیک کنید:"
        markup = InlineKeyboardMarkup(row_width=1)
        for idx, pkg in enumerate(month_info['packages']):
            pkg_name, price = pkg
            markup.add(InlineKeyboardButton(f"{pkg_name} - {price:,} تومان", callback_data=f"edpr_p_{shop_key}_{month_id}_{idx}"))
        markup.add(InlineKeyboardButton("🔙 بازگشت", callback_data=f"edpr_c_{shop_key}"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("edpr_p_"))
    def edit_prices_ask(call):
        if int(call.from_user.id) != int(ADMIN_ID): return
        parts = call.data.split("_")
        shop_key, month_id, pkg_idx = parts[2], parts[3], int(parts[4])
        pkg_name, old_price = SHOP_DATA[shop_key]['months'][month_id]['packages'][pkg_idx]

        text = (
            f"💲 **ویرایش قیمت نهایی**\n\n"
            f"🔹 سرویس: {SHOP_DATA[shop_key]['title']}\n"
            f"📦 بسته: {pkg_name}\n"
            f"💵 قیمت فعلی: **{old_price:,}** تومان\n\n"
            f"👇 لطفاً قیمت جدید را به **تومان** (فقط عدد انگلیسی) وارد کنید:"
        )
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("لغو ❌", callback_data=f"edpr_m_{shop_key}_{month_id}"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(call.message, process_new_price, bot, shop_key, month_id, pkg_idx)

    def process_new_price(message, bot, shop_key, month_id, pkg_idx):
        if message.text in ["/start", "/admin"]: return
        if not message.text.isdigit():
            bot.send_message(message.chat.id, "❌ قیمت باید فقط شامل اعداد باشد. عملیات لغو شد.", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings")))
            return

        new_price = int(message.text)
        
        # تغییر در حافظه ربات
        SHOP_DATA[shop_key]['months'][month_id]['packages'][pkg_idx][1] = new_price

        # بازنویسی مستقیم روی فایل shop_data.py
        try:
            with open('shop_data.py', 'w', encoding='utf-8') as f:
                json_str = json.dumps(SHOP_DATA, ensure_ascii=False, indent=4)
                import re
                formatted_str = re.sub(r'\[\s*"([^"]+)",\s*(\d+)\s*\]', r'("\1", \2)', json_str)
                f.write(f"SHOP_DATA = {formatted_str}\n")
                
            bot.send_message(message.chat.id, f"✅ قیمت جدید (**{new_price:,} تومان**) با موفقیت ذخیره شد و در لحظه برای تمامی کاربران اعمال گردید!", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت به تنظیمات", callback_data="admin_settings")))
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ خطا در ذخیره‌سازی فایل: {e}")

    # ----------- ویرایش متن‌ها -----------
    @bot.callback_query_handler(func=lambda call: call.data == "edit_texts_main")
    def edit_texts_main(call):
        if int(call.from_user.id) != int(ADMIN_ID): return
        text = "📝 **مدیریت متن‌های ربات**\n\nیکی از متن‌های زیر را جهت ویرایش انتخاب کنید:"
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("متن راهنمای پشتیبانی ☎️", callback_data="edtxt_support"),
            InlineKeyboardButton("متن سوالات متداول ❓", callback_data="edtxt_faq"),
            InlineKeyboardButton("متن هدیه اولین خرید 🎁", callback_data="edtxt_gift"),
            InlineKeyboardButton("🔙 بازگشت", callback_data="admin_settings")
        )
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("edtxt_"))
    def edit_texts_ask(call):
        if int(call.from_user.id) != int(ADMIN_ID): return
        text_key = call.data.split("_")[1]
        text_names = {"support": "پشتیبانی", "faq": "سوالات متداول", "gift": "هدیه اولین خرید"}
        name = text_names.get(text_key, "")

        text = f"📝 **ویرایش متن ({name})**\n\nلطفاً متن جدید خود را به همراه اموجی‌ها و رعایت فاصله‌ها ارسال کنید:\n\n💡 *از مارک‌داون (مثل **متن پررنگ**) نیز می‌توانید استفاده کنید.*"
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("لغو ❌", callback_data="edit_texts_main"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(call.message, process_new_text, bot, text_key)

    def process_new_text(message, bot, text_key):
        if message.text in ["/start", "/admin"]: return
        conn = database.get_db_connection()
        if not conn:
            bot.send_message(message.chat.id, "❌ خطای اتصال به دیتابیس.")
            return
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO settings (key, value) VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """, (text_key, message.text))
        conn.commit()
        cursor.close()
        conn.close()
        bot.send_message(message.chat.id, "✅ متن جدید با موفقیت در سیستم مرکزی ذخیره شد!", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت به تنظیمات", callback_data="admin_settings")))


    # ================= 3. آمار و مانیتورینگ =================
    @bot.callback_query_handler(func=lambda call: call.data == "admin_stats_menu")
    def admin_stats_menu(call):
        if int(call.from_user.id) != int(ADMIN_ID): return
        
        conn = database.get_db_connection()
        if not conn:
            bot.answer_callback_query(call.id, "❌ خطای اتصال به دیتابیس.", show_alert=True)
            return
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), SUM(balance) FROM users")
        user_res = cursor.fetchone()
        total_users, total_balance = (user_res[0] or 0), (user_res[1] or 0)
        
        cursor.execute("SELECT status, COUNT(*) FROM configs GROUP BY status")
        configs = cursor.fetchall()
        total_sold, total_available = 0, 0
        for status, count in configs:
            if status == 'sold': total_sold += count
            elif status == 'available': total_available += count
            
        cursor.execute("SELECT plan_id, COUNT(*) FROM configs WHERE status = 'available' GROUP BY plan_id HAVING COUNT(*) < 5")
        low_stock = cursor.fetchall()
        cursor.close()
        conn.close()
        
        low_stock_text = "\n✅ **وضعیت انبار:** تمامی قفسه‌ها موجودی کافی دارند."
        if low_stock:
            low_stock_text = "\n⚠️ **هشدار! موجودی قفسه‌های زیر رو به اتمام است:**\n"
            for plan, count in low_stock:
                plan_name = f"تست رایگان" if str(plan).startswith("test_") else f"پلن {plan}"
                low_stock_text += f"🔻 {plan_name}: فقط {count} عدد!\n"

        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        text = (
            f"📊 **آمار زنده و جامع سیستم**\n⏱ `{now}`\n\n"
            f"👥 **بخش کاربران:**\n🔹 کل کاربران: `{total_users:,}` نفر\n💰 موجودی کل کیف‌پول‌ها: `{total_balance:,}` تومان\n\n"
            f"🗄 **بخش فروشگاه:**\n✅ کل فروش: `{total_sold:,}` عدد\n📦 موجودی کل انبار: `{total_available:,}` عدد\n{low_stock_text}"
        )
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت به داشبورد", callback_data="admin_panel"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")


    # ================= 4. مدیریت کاربران =================
    @bot.callback_query_handler(func=lambda call: call.data == "admin_users")
    def admin_users_menu(call):
        if int(call.from_user.id) != int(ADMIN_ID): return
        text = "👥 **مدیریت کاربران**\n\n🔍 لطفاً **آیدی عددی (User ID)** کاربر را ارسال کنید:"
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 لغو و بازگشت", callback_data="admin_panel"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(call.message, process_admin_user_search, bot)

    def process_admin_user_search(message, bot):
        if message.text in ["/start", "/admin"]: return
        if not message.text.isdigit():
            bot.send_message(message.chat.id, "❌ آیدی نامعتبر.", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")))
            return
            
        target_id = int(message.text.strip())
        try:
            balance = database.get_balance(target_id)
            user_stats = database.get_user_stats(target_id) or {}
            conn = database.get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM configs WHERE owner_id = %s AND status = 'sold'", (target_id,))
                configs_count = cursor.fetchone()[0]
                cursor.close()
                conn.close()
            else:
                configs_count = 0
            
            text = (
                f"👤 **پروفایل کاربر:** `{target_id}`\n\n"
                f"💰 موجودی کیف پول: **{balance:,}** تومان\n"
                f"🛒 تعداد خریدهای موفق: **{configs_count}** عدد\n"
                f"💵 مجموع تراکنش‌ها: **{user_stats.get('total_spent', 0):,}** تومان\n\n"
                "⚙️ جهت مدیریت از گزینه‌های زیر استفاده کنید:"
            )
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(InlineKeyboardButton("➕ افزایش موجودی", callback_data=f"adm_addbal_{target_id}"), InlineKeyboardButton("➖ کسر موجودی", callback_data=f"adm_dedbal_{target_id}"))
            markup.add(InlineKeyboardButton("📦 مشاهده اشتراک‌ها", callback_data=f"adm_viewsubs_{target_id}"), InlineKeyboardButton("✉️ ارسال پیام مستقیم", callback_data=f"adm_pm_{target_id}"))
            markup.add(InlineKeyboardButton("🔙 بازگشت به داشبورد", callback_data="admin_panel"))
            bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
        except:
            bot.send_message(message.chat.id, "❌ کاربر یافت نشد.", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")))

    @bot.callback_query_handler(func=lambda call: call.data.startswith("adm_addbal_") or call.data.startswith("adm_dedbal_"))
    def admin_balance_action(call):
        if int(call.from_user.id) != int(ADMIN_ID): return
        action, target_id = call.data.split("_")[1:3]
        action_name = "شارژ" if action == "addbal" else "کسر از"
        text = f"💵 **{action_name} کیف پول**\n\nمبلغ را به **تومان** (فقط عدد) وارد کنید:"
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 لغو و بازگشت", callback_data="admin_users"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(call.message, process_admin_balance_change, bot, target_id, action)

    def process_admin_balance_change(message, bot, target_id, action):
        if message.text in ["/start", "/admin"]: return
        if not message.text.isdigit(): return bot.send_message(message.chat.id, "❌ مبلغ نامعتبر است.")
        amount, current_balance = int(message.text), database.get_balance(int(target_id))
        
        if action == "dedbal" and amount > current_balance:
            return bot.send_message(message.chat.id, "❌ موجودی کافی نیست!", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")))
            
        if action == "addbal":
            database.update_balance(int(target_id), amount)
            action_text = f"✅ مبلغ **{amount:,}** تومان افزوده شد."
            try: bot.send_message(int(target_id), f"🎉 مبلغ **{amount:,}** تومان توسط مدیریت به حساب شما افزوده شد.", parse_mode="Markdown")
            except: pass
        else:
            database.update_balance(int(target_id), -amount)
            action_text = f"✅ مبلغ **{amount:,}** تومان کسر شد."
            try: bot.send_message(int(target_id), f"⚠️ مبلغ **{amount:,}** تومان توسط مدیریت از حساب شما کسر گردید.", parse_mode="Markdown")
            except: pass
            
        bot.send_message(message.chat.id, action_text, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")))

    @bot.callback_query_handler(func=lambda call: call.data.startswith("adm_viewsubs_"))
    def admin_view_user_subs(call):
        if int(call.from_user.id) != int(ADMIN_ID): return
        target_id = call.data.split("_")[2]
        conn = database.get_db_connection()
        if not conn:
            return bot.answer_callback_query(call.id, "❌ خطای اتصال به دیتابیس.", show_alert=True)
        cursor = conn.cursor()
        cursor.execute("SELECT id, config_text, plan_id FROM configs WHERE owner_id = %s AND status = 'sold'", (target_id,))
        configs = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not configs: return bot.answer_callback_query(call.id, "هیچ اشتراک فعالی ندارد.", show_alert=True)
            
        text = f"📦 **اشتراک‌های کاربر:** `{target_id}`\n\n"
        for idx, (c_id, c_text, p_id) in enumerate(configs, 1):
            short_link = c_text if len(c_text) < 25 else c_text[:15] + "..." + c_text[-10:]
            text += f"{idx}. آیدی: {c_id} | پلن: {p_id}\nلینک: `{short_link}`\n\n"
            
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_users"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("adm_pm_"))
    def admin_pm_user(call):
        if int(call.from_user.id) != int(ADMIN_ID): return
        target_id = call.data.split("_")[2]
        text = f"✉️ **ارسال پیام شخصی به:** `{target_id}`\n\nمتن پیام خود را بفرستید:"
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 لغو و بازگشت", callback_data="admin_users"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(call.message, process_admin_pm, bot, target_id)

    def process_admin_pm(message, bot, target_id):
        if message.text in ["/start", "/admin"]: return
        try:
            bot.send_message(int(target_id), f"💬 **پیام جدید از مدیریت:**\n\n{message.text}", parse_mode="Markdown")
            bot.send_message(message.chat.id, f"✅ پیام با موفقیت ارسال شد.", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")))
        except:
            bot.send_message(message.chat.id, "❌ کاربر ربات را بلاک کرده است.", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")))


    # ================= 5. آخرین فروش‌ها و برترین‌ها =================
    @bot.callback_query_handler(func=lambda call: call.data == "admin_recent_sales")
    def admin_recent_sales(call):
        if int(call.from_user.id) != int(ADMIN_ID): return
        conn = database.get_db_connection()
        if not conn:
            return bot.answer_callback_query(call.id, "❌ خطای اتصال به دیتابیس.", show_alert=True)
        cursor = conn.cursor()
        cursor.execute("SELECT id, owner_id, plan_id FROM configs WHERE status = 'sold' ORDER BY id DESC LIMIT 10")
        recent = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not recent: return bot.answer_callback_query(call.id, "فروشی ثبت نشده است.", show_alert=True)
            
        text = "🧾 **گزارش 10 فروش اخیر:**\n\n"
        for idx, (c_id, owner, p_id) in enumerate(recent, 1):
            plan_name = "تست رایگان" if str(p_id).startswith("test") else f"پلن {p_id}"
            text += f"🔹 {idx}. خریدار: `{owner}`\n   🛒 {plan_name} (ID:{c_id})\n\n"
            
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data == "admin_top_buyers")
    def admin_top_buyers(call):
        if int(call.from_user.id) != int(ADMIN_ID): return
        conn = database.get_db_connection()
        if not conn:
            return bot.answer_callback_query(call.id, "❌ خطای اتصال به دیتابیس.", show_alert=True)
        cursor = conn.cursor()
        cursor.execute("SELECT owner_id, COUNT(*) as c FROM configs WHERE status = 'sold' GROUP BY owner_id ORDER BY c DESC LIMIT 10")
        top_buyers = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not top_buyers: return bot.answer_callback_query(call.id, "رکوردی وجود ندارد.", show_alert=True)
            
        text = "🏆 **لیست 10 خریدار برتر:**\n\n"
        for idx, (owner_id, count) in enumerate(top_buyers, 1):
            medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "🏅"
            text += f"{medal} رتبه {idx}: کاربر `{owner_id}` (تعداد: {count})\n"
            
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")


    # ================= 6. پیام همگانی پیشرفته =================
    @bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast_adv")
    def admin_broadcast_menu(call):
        if int(call.from_user.id) != int(ADMIN_ID): return
        text = "📣 **ارسال پیام همگانی**\n\nپیام خود را (متن، عکس، ویدیو) بفرستید:"
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 لغو", callback_data="admin_panel"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(call.message, process_admin_broadcast_content, bot)

    def process_admin_broadcast_content(message, bot):
        if message.text in ["/start", "/admin"]: return
        broadcast_data = {'message_id': message.message_id, 'chat_id': message.chat.id}
        text = "🔘 **افزودن دکمه شیشه‌ای (اختیاری)**\n\nجهت افزودن لینک، از فرمت زیر استفاده کنید:\n`نام دکمه - http://link.com`\n\nدر غیر این صورت روی ارسال بدون دکمه کلیک کنید:"
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("🚀 ارسال بدون دکمه", callback_data=f"bcast_none_{message.message_id}"), InlineKeyboardButton("لغو ❌", callback_data="admin_panel"))
        msg = bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_admin_broadcast_button, bot, broadcast_data)

    def process_admin_broadcast_button(message, bot, broadcast_data):
        if message.text in ["/start", "/admin"]: return
        button_info = None
        if "-" in message.text:
            try:
                parts = message.text.split("-", 1)
                if parts[1].strip().startswith("http"): button_info = (parts[0].strip(), parts[1].strip())
            except: pass

        if not button_info: return bot.send_message(message.chat.id, "❌ فرمت دکمه اشتباه بود.")
        execute_broadcast(bot, message.chat.id, broadcast_data['chat_id'], broadcast_data['message_id'], button_info)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("bcast_none_"))
    def bypass_broadcast_button(call):
        if int(call.from_user.id) != int(ADMIN_ID): return
        msg_id = call.data.split("_")[2]
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        execute_broadcast(bot, call.message.chat.id, call.message.chat.id, int(msg_id), None)

    def execute_broadcast(bot, admin_chat_id, source_chat_id, source_msg_id, button_info):
        bot.send_message(admin_chat_id, "⏳ در حال ارسال به کاربران...")
        conn = database.get_db_connection()
        if not conn:
            return bot.send_message(admin_chat_id, "❌ خطای اتصال به دیتابیس.")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        
        success, failed = 0, 0
        reply_markup = InlineKeyboardMarkup().add(InlineKeyboardButton(button_info[0], url=button_info[1])) if button_info else None
            
        for user in users:
            try:
                if reply_markup: bot.copy_message(user[0], source_chat_id, source_msg_id, reply_markup=reply_markup)
                else: bot.copy_message(user[0], source_chat_id, source_msg_id)
                success += 1
                time.sleep(0.05)
            except: failed += 1
                
        bot.send_message(admin_chat_id, f"📣 **گزارش نهایی:**\n\n✅ ارسال موفق: `{success}`\n❌ ناموفق (بلاک): `{failed}`", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")), parse_mode="Markdown")
