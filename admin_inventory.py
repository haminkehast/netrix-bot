from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import database
from config import ADMIN_ID
from shop_data import SHOP_DATA

CATEGORIES = {
    "1": "مولتی لوکیشن VIP 🥇",
    "2": "مولتی لوکیشن اقتصادی 🥈",
    "3": "مولتی لوکیشن نامحدود ♾",
    "4": "آی‌پی ثابت آلمان 🇩🇪",
    "5": "آی‌پی ثابت آمریکا 🇺🇸 (پیشنهادی) 🇺🇸"
}

def register_admin_inventory_handlers(bot):
    
    @bot.callback_query_handler(func=lambda call: call.data == "inventory")
    def inventory_main_menu(call):
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        if int(call.from_user.id) != int(ADMIN_ID): return
            
        text = "🗄 **مدیریت انبار کانفیگ‌های NETRIX**\n\nجهت مشاهده موجودی و مدیریت کانفیگ‌ها، روی دسته‌بندی مورد نظر کلیک کنید:"
        markup = InlineKeyboardMarkup(row_width=1)
        
        for cat_id, cat_name in CATEGORIES.items():
            markup.add(InlineKeyboardButton(cat_name, callback_data=f"inv_view_{cat_id}"))
            
        markup.add(InlineKeyboardButton("🎁 اشتراک‌های تست (رایگان)", callback_data="inv_test_cat"))
        markup.add(InlineKeyboardButton("➕ افزایش موجودی (شارژ انبار)", callback_data="inv_add_select"))
        markup.row(InlineKeyboardButton("🔍 جستجوی اشتراک", callback_data="inv_search"), InlineKeyboardButton("🧾 فاکتور فروش", callback_data="inv_export"))
        markup.add(InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data="main")) # مشکل دکمه بازگشت به پنل ادمین
        
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data == "inv_test_cat")
    def inv_test_cat(call):
        if int(call.from_user.id) != int(ADMIN_ID): return
        text = "🎁 **انبار اشتراک‌های تست**\n\nلطفاً قفسه تست مورد نظر را برای مشاهده موجودی انتخاب کنید:"
        markup = InlineKeyboardMarkup(row_width=1)
        for cat_id, cat_name in CATEGORIES.items():
            markup.add(InlineKeyboardButton(f"تست {cat_name.split(' ')[-2]} {cat_name.split(' ')[-1]}", callback_data=f"inv_view_test_{cat_id}"))
        markup.add(InlineKeyboardButton("🔙 بازگشت به انبار", callback_data="inventory"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data == "inv_add_select")
    def inv_add_select_category(call):
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        if int(call.from_user.id) != int(ADMIN_ID): return
        
        text = "📥 **افزایش موجودی انبار**\n\nلطفاً قفسه مورد نظر برای ورود و شارژ را انتخاب کنید:"
        markup = InlineKeyboardMarkup(row_width=1)
        for cat_id, cat_name in CATEGORIES.items():
            markup.add(InlineKeyboardButton(cat_name, callback_data=f"inv_view_{cat_id}"))
        
        markup.add(InlineKeyboardButton("🎁 شارژ اشتراک‌های تست", callback_data="inv_add_test_cat"))
        markup.add(InlineKeyboardButton("🔙 بازگشت به انبار", callback_data="inventory"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data == "inv_add_test_cat")
    def inv_add_test_cat(call):
        if int(call.from_user.id) != int(ADMIN_ID): return
        text = "📥 **شارژ انبار تست رایگان**\n\nلطفاً دسته‌بندی مورد نظر برای شارژ تست را انتخاب کنید:"
        markup = InlineKeyboardMarkup(row_width=1)
        for cat_id, cat_name in CATEGORIES.items():
            markup.add(InlineKeyboardButton(f"تست {cat_name.split(' ')[-2]} {cat_name.split(' ')[-1]}", callback_data=f"inv_add_to_test_{cat_id}"))
        markup.add(InlineKeyboardButton("🔙 بازگشت", callback_data="inv_add_select"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("inv_view_"))
    def inv_view_category(call):
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        if int(call.from_user.id) != int(ADMIN_ID): return
        
        cat_id = call.data.replace("inv_view_", "")
        conn = database.sqlite3.connect('netrix.db')
        cursor = conn.cursor()
        
        is_test = cat_id.startswith("test_")
        
        if is_test:
            real_cat_id = cat_id.split("_")[1]
            cat_name = f"تست رایگان {CATEGORIES.get(real_cat_id, 'نامشخص').split(' ')[-2]}"
            cursor.execute("SELECT id, config_text, status, plan_id FROM configs WHERE plan_id = ?", (cat_id,))
        else:
            cat_name = CATEGORIES.get(cat_id, "نامشخص")
            search_pattern = f"{cat_id}\\_%"
            cursor.execute("SELECT id, config_text, status, plan_id FROM configs WHERE (plan_id = ? OR plan_id LIKE ? ESCAPE '\\')", (cat_id, search_pattern))
            
        configs = cursor.fetchall()
        conn.close()

        total_available = 0
        total_sold = 0
        for c in configs:
            if c[2] == 'available': total_available += 1
            else: total_sold += 1

        text = f"🗂 **انبار اختصاصی:** `{cat_name}`\n\n"
        text += f"📦 **موجودی کل:** {total_available} 🟢 | {total_sold} 🔴\n\n"
        
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton("➕ شارژ این قفسه", callback_data=f"inv_add_to_{cat_id}"))

        if not configs:
            text += "⚠️ این قفسه در حال حاضر خالی است."
        else:
            text += "👇 لیست اکانت‌ها (برای مشاهده جزئیات کلیک کنید):"
            for config in configs:
                c_id, c_text, c_status, c_plan_id = config
                short_id = c_text[-15:] if len(c_text) >= 15 else c_text
                icon = "🔴" if c_status == "sold" else "🟢"
                btn_text = f"{icon} {short_id} | {cat_name}"
                markup.row(
                    InlineKeyboardButton("🗑", callback_data=f"inv_del_{c_id}_{cat_id}"),
                    InlineKeyboardButton(btn_text, callback_data=f"inv_detail_{c_id}")
                )

        back_data = "inv_test_cat" if is_test else "inventory"
        markup.add(InlineKeyboardButton("🔙 بازگشت", callback_data=back_data))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("inv_del_"))
    def inv_delete_config(call):
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        if int(call.from_user.id) != int(ADMIN_ID): return
        
        parts = call.data.split("_")
        c_id = parts[2]
        cat_id = "_".join(parts[3:])
        
        conn = database.sqlite3.connect('netrix.db')
        cursor = conn.cursor()
        cursor.execute('DELETE FROM configs WHERE id = ?', (c_id,))
        conn.commit()
        conn.close()
        
        bot.answer_callback_query(call.id, "✅ اشتراک حذف شد", show_alert=False)
        call.data = f"inv_view_{cat_id}"
        inv_view_category(call)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("inv_add_to_"))
    def inv_add_step1(call):
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        if int(call.from_user.id) != int(ADMIN_ID): return
        
        cat_id = call.data.replace("inv_add_to_", "")
        
        if cat_id.startswith("test_"):
            real_cat_id = cat_id.split("_")[1]
            cat_name = f"تست {CATEGORIES.get(real_cat_id, 'نامشخص').split(' ')[-2]}"
            text = f"🔗 **شارژ قفسه:** `{cat_name}`\n\nلطفاً لینک‌های سابسکریپشن تست را بفرستید.\n💡 *هر لینک را در یک خط جدید (Enter) قرار دهید.*"
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 لغو و بازگشت", callback_data=f"inv_view_{cat_id}"))
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
            bot.register_next_step_handler(call.message, inv_add_step2, cat_id, cat_id)
            return

        shop_keys_mapping = {"1": "vip", "2": "eco", "3": "unlim", "4": "ger", "5": "usa"}
        shop_key = shop_keys_mapping.get(cat_id)
        cat_info = SHOP_DATA.get(shop_key) if shop_key else None

        if cat_info:
            text = f"📍 **{cat_info['title']}**\n\nلطفاً مدت زمان اشتراک را انتخاب کنید:"
            markup = InlineKeyboardMarkup(row_width=1)
            for month_id, month_info in cat_info["months"].items():
                markup.add(InlineKeyboardButton(month_info["title"], callback_data=f"inv_add_dur_{shop_key}_{month_id}_{cat_id}"))
            markup.add(InlineKeyboardButton("🔙 بازگشت به قفسه", callback_data=f"inv_view_{cat_id}"))
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("inv_add_dur_"))
    def inv_add_show_pkgs(call):
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        if int(call.from_user.id) != int(ADMIN_ID): return
        
        parts = call.data.split("_")
        shop_key = parts[3]
        month_id = parts[4]
        cat_id = parts[5]
        cat_info = SHOP_DATA.get(shop_key)
        month_info = cat_info["months"][month_id]

        text = f"📍 **{cat_info['title']}**\n\nلطفاً پلن مورد نظر خود را انتخاب کنید:"
        markup = InlineKeyboardMarkup(row_width=1)
        for idx, pkg in enumerate(month_info["packages"]):
            pkg_name, price = pkg
            btn_text = f"{pkg_name} - {price:,} تومان" if "نامحدود" in pkg_name else f"{pkg_name} {month_info['title']} - {price:,} تومان"
            markup.add(InlineKeyboardButton(btn_text, callback_data=f"inv_add_pkg_{shop_key}_{month_id}_{idx}_{cat_id}"))
        markup.add(InlineKeyboardButton("🔙 بازگشت به زمان‌ها", callback_data=f"inv_add_to_{cat_id}"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("inv_add_pkg_"))
    def inv_add_ask_links(call):
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        if int(call.from_user.id) != int(ADMIN_ID): return
        
        parts = call.data.split("_")
        shop_key = parts[3]
        month_id = parts[4]
        pkg_idx = parts[5]
        cat_id = parts[6]
        
        cat_info = SHOP_DATA.get(shop_key)
        month_title = cat_info["months"][month_id]["title"]
        pkg_name = cat_info["months"][month_id]["packages"][int(pkg_idx)][0]

        full_plan_id = f"{cat_id}_{month_id}_{pkg_idx}"
        display_name = f"{cat_info['title']} | {pkg_name}" if "نامحدود" in pkg_name else f"{cat_info['title']} | {pkg_name} {month_title}"

        text = f"🔗 **شارژ قفسه:** `{display_name}`\n\nلطفاً لینک‌های سابسکریپشن خود را بفرستید.\n💡 *هر لینک را در یک خط جدید (Enter) قرار دهید.*"
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 لغو و بازگشت", callback_data=f"inv_add_dur_{shop_key}_{month_id}_{cat_id}"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(call.message, inv_add_step2, full_plan_id, cat_id)

    def inv_add_step2(message, plan_id, main_cat_id=None):
        if message.text in ["/start", "/admin"]: return
        if main_cat_id is None: main_cat_id = str(plan_id).split('_')[0]
            
        lines = message.text.split('\n')
        added_count, dup_count = 0, 0
        conn = database.sqlite3.connect('netrix.db')
        cursor = conn.cursor()
        for line in lines:
            link = line.strip()
            if link:
                cursor.execute('SELECT COUNT(*) FROM configs WHERE config_text = ?', (link,))
                if cursor.fetchone()[0] == 0:
                    cursor.execute('INSERT INTO configs (config_text, status, plan_id) VALUES (?, ?, ?)', (link, 'available', str(plan_id)))
                    added_count += 1
                else: dup_count += 1
        conn.commit()
        conn.close()

        text = f"✅ تعداد **{added_count}** کانفیگ جدید با موفقیت به انبار اضافه شد!\n"
        if dup_count > 0: text += f"⚠️ تعداد **{dup_count}** کانفیگ تکراری بود و نادیده گرفته شد."
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("مشاهده قفسه 🗂", callback_data=f"inv_view_{main_cat_id}"))
        bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data == "inv_export")
    def inv_export_btn(call):
        if int(call.from_user.id) != int(ADMIN_ID): return
        conn = database.sqlite3.connect('netrix.db')
        cursor = conn.cursor()
        cursor.execute("SELECT plan_id, COUNT(*) FROM configs WHERE status = 'sold' GROUP BY plan_id")
        sold_stats = cursor.fetchall()
        conn.close()

        if not sold_stats:
            bot.answer_callback_query(call.id, "⚠️ تا این لحظه هیچ فروشی ثبت نشده است.", show_alert=True)
            return

        text = "🧾 **فاکتور فروش (آمار کلی)**\n\n"
        total_sold = 0
        shop_keys_mapping = {"1": "vip", "2": "eco", "3": "unlim", "4": "ger", "5": "usa"}
        for plan_id, count in sold_stats:
            total_sold += count
            display_name = str(plan_id)
            if str(plan_id).startswith("test_"):
                real_id = str(plan_id).split("_")[1]
                display_name = f"تست رایگان {CATEGORIES.get(real_id, '').split(' ')[-2]}"
            elif plan_id and "_" in str(plan_id):
                try:
                    parts = str(plan_id).split("_")
                    shop_key = shop_keys_mapping.get(parts[0])
                    m_id = parts[1]
                    p_idx = int(parts[2])
                    c_info = SHOP_DATA.get(shop_key)
                    if c_info:
                        m_info = c_info["months"].get(m_id)
                        pkg_name = m_info["packages"][p_idx][0]
                        display_name = f"{pkg_name} {m_info['title']} | {c_info['title']}"
                except: pass
            text += f"🔹 {display_name}: **{count}** عدد\n"
            
        text += f"\n📦 **مجموع کل اکانت‌های فروخته شده:** {total_sold} عدد"
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت به انبار", callback_data="inventory"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data == "inv_search")
    def inv_search_btn(call):
        if int(call.from_user.id) != int(ADMIN_ID): return
        text = "🔍 **جستجوی کانفیگ / کاربر**\n\nلطفاً بخشی از لینک کانفیگ (مثلاً چند حرف آخر) یا آیدی عددی خریدار را بفرستید:"
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 لغو و بازگشت", callback_data="inventory"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(call.message, process_inv_search, bot)

    def process_inv_search(message, bot):
        if message.text in ["/start", "/admin"]: return
        query = message.text.strip()
        conn = database.sqlite3.connect('netrix.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, config_text, status, owner_id FROM configs WHERE config_text LIKE ? OR owner_id = ? LIMIT 15', (f'%{query}%', query if query.isdigit() else -1))
        results = cursor.fetchall()
        conn.close()

        if not results:
            bot.send_message(message.chat.id, "❌ هیچ اشتراکی با این مشخصات در انبار یافت نشد.", reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت به انبار", callback_data="inventory")))
            return

        text = f"🔍 **نتایج جستجو برای:** `{query}`\n\n"
        for r in results:
            c_id, c_text, c_status, owner = r
            icon = "🔴 فروخته شده" if c_status == 'sold' else "🟢 موجود در انبار"
            owner_text = f"\n👤 خریدار: `{owner}`" if owner else ""
            short_link = c_text if len(c_text) < 25 else c_text[:15] + "..." + c_text[-10:]
            text += f"🔹 آیدی سیستم: {c_id}\nوضعیت: {icon}{owner_text}\nلینک: `{short_link}`\n\n"
        bot.send_message(message.chat.id, text, reply_markup=InlineKeyboardMarkup().add(InlineKeyboardButton("🔙 بازگشت به انبار", callback_data="inventory")), parse_mode="Markdown")