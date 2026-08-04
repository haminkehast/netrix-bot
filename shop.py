# shop.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from shop_data import SHOP_DATA
from keyboards import get_back_markup
import database
from config import LOG_GROUP_ID, LOG_TOPIC_ID 

def register_shop_handlers(bot):
    @bot.callback_query_handler(func=lambda call: call.data == "shop_main" or call.data.startswith("cat_") or call.data.startswith("dur_") or call.data.startswith("factor_") or call.data.startswith("pay_"))
    def shop_callbacks(call):
        chat_id = call.message.chat.id
        msg_id = call.message.message_id
        data = call.data
        user_id = call.from_user.id

        if data == "shop_main":
            markup = InlineKeyboardMarkup(row_width=1)
            for cat_id, cat_info in SHOP_DATA.items():
                markup.add(InlineKeyboardButton(cat_info["title"], callback_data=f"cat_{cat_id}"))
            markup.add(InlineKeyboardButton("بازگشت به منوی اصلی 🔙", callback_data="main"))
            bot.edit_message_text("🛒 **فروشگاه NETRIX**\n\nلطفاً دسته‌بندی مورد نظر خود را انتخاب کنید:", chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")

        elif data.startswith("cat_"):
            cat_id = data.split("_")[1]
            cat_info = SHOP_DATA.get(cat_id)
            markup = InlineKeyboardMarkup(row_width=1)
            for month_id, month_info in cat_info["months"].items():
                markup.add(InlineKeyboardButton(month_info["title"], callback_data=f"dur_{cat_id}_{month_id}"))
            markup.add(InlineKeyboardButton("بازگشت 🔙", callback_data="shop_main")) 
            bot.edit_message_text(f"📍 **{cat_info['title']}**\n\nلطفاً مدت زمان اشتراک را انتخاب کنید:", chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")

        elif data.startswith("dur_"):
            _, cat_id, month_id = data.split("_")
            cat_info = SHOP_DATA[cat_id]
            month_info = cat_info["months"][month_id]
            
            markup = InlineKeyboardMarkup(row_width=1)
            for idx, pkg in enumerate(month_info["packages"]):
                pkg_name, price = pkg
                btn_text = f"{pkg_name} - {price:,} تومان" if "نامحدود" in pkg_name else f"{pkg_name} {month_info['title']} - {price:,} تومان"
                markup.add(InlineKeyboardButton(btn_text, callback_data=f"factor_{cat_id}_{month_id}_{idx}"))
            markup.add(InlineKeyboardButton("بازگشت 🔙", callback_data=f"cat_{cat_id}")) 
            bot.edit_message_text(f"📍 **{cat_info['title']}**\n\nلطفاً پلن مورد نظر خود را انتخاب کنید:", chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")

        elif data.startswith("factor_"):
            _, cat_id, month_id, pkg_idx = data.split("_")
            pkg_idx = int(pkg_idx)
            cat_info = SHOP_DATA[cat_id]
            month_title = cat_info["months"][month_id]["title"]
            pkg_name, price = cat_info["months"][month_id]["packages"][pkg_idx]
            balance = database.get_balance(user_id)
            
            invoice_text = (
                "🧾 **پیش‌فاکتور سفارش شما:**\n\n"
                f"🔹 **سرویس:** {cat_info['title']}\n"
                f"📦 **حجم:** {pkg_name}\n"
                f"⏳ **زمان:** {month_title}\n"
                f"💵 **مبلغ قابل پرداخت:** {price:,} تومان\n\n"
                f"💰 **موجودی فعلی کیف پول شما:** {balance:,} تومان\n\n"
                "آیا از خرید خود اطمینان دارید؟"
            )
            markup = InlineKeyboardMarkup(row_width=1)
            markup.add(InlineKeyboardButton("✅ پرداخت با موجودی کیف پول", callback_data=f"pay_{cat_id}_{month_id}_{pkg_idx}"))
            markup.add(InlineKeyboardButton("💳 شارژ کیف پول", callback_data="charge_wallet"))
            markup.add(InlineKeyboardButton("بازگشت 🔙", callback_data=f"dur_{cat_id}_{month_id}"))
            bot.edit_message_text(invoice_text, chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")

        elif data.startswith("pay_"):
            _, cat_id, month_id, pkg_idx = data.split("_")
            cat_info = SHOP_DATA[cat_id]
            month_title = cat_info["months"][month_id]["title"]
            pkg_name, price = cat_info["months"][month_id]["packages"][int(pkg_idx)]
            
            balance = database.get_balance(user_id)
            
            if balance < price:
                bot.answer_callback_query(call.id, "⚠️ اعتبار کافی نیست. لطفاً کیف پول خود را شارژ کنید.", show_alert=True)
            else:
                shop_to_cat = {"vip": "1", "eco": "2", "unlim": "3", "ger": "4", "usa": "5"}
                db_cat_id = shop_to_cat.get(cat_id)
                plan_id = f"{db_cat_id}_{month_id}_{pkg_idx}"
                
                conn = database.sqlite3.connect('netrix.db')
                cursor = conn.cursor()
                
                cursor.execute('SELECT id, config_text FROM configs WHERE plan_id = ? AND status = "available" LIMIT 1', (plan_id,))
                config = cursor.fetchone()
                
                if not config:
                    conn.close()
                    text_out_of_stock = (
                        "❌ **متاسفانه این سرویس در حال حاضر در انبار ناموجود است.**\n\n"
                        "💬 لطفاً از طریق دکمه زیر به پشتیبانی اطلاع دهید تا در سریع‌ترین زمان ممکن برای شما شارژ شود."
                    )
                    markup = InlineKeyboardMarkup(row_width=1)
                    markup.add(InlineKeyboardButton("ارتباط با پشتیبانی 👨‍💻", url="https://t.me/NetrixVIPSupport"))
                    markup.add(InlineKeyboardButton("بازگشت 🔙", callback_data=f"dur_{cat_id}_{month_id}"))
                    bot.edit_message_text(text_out_of_stock, chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")
                    return
                    
                config_id, config_text = config
                cursor.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (price, user_id))
                cursor.execute('UPDATE configs SET status = "sold", owner_id = ? WHERE id = ?', (user_id, config_id))
                
                cursor.execute('SELECT COUNT(*) FROM configs WHERE plan_id = ? AND status = "available"', (plan_id,))
                remaining_stock = cursor.fetchone()[0]
                conn.commit()
                conn.close()

                # تنظیم فرمت جدید و ارسال پیام به گروه
                admin_report = (
                    "🛍 **یک خرید جدید انجام شد!**\n\n"
                    f"👤 آیدی خریدار: `{user_id}`\n"
                    f"🔹 سرویس: {cat_info['title']}\n"
                    f"📦 حجم: {pkg_name}\n"
                    f"⏳ زمان: {month_title}\n"
                    f"💳 مبلغ پرداخت شده: {price:,} تومان\n"
                    f"🔗 کانفیگ تحویل داده شده:\n`{config_text}`\n\n"
                    f"📊 **موجودی باقی‌مانده این پلن در انبار:** {remaining_stock} عدد"
                )
                try:
                    bot.send_message(LOG_GROUP_ID, admin_report, message_thread_id=LOG_TOPIC_ID, parse_mode="Markdown")
                except: pass

                bot.answer_callback_query(call.id, "✅ خرید با موفقیت انجام شد!", show_alert=False)
                
                success_text = (
                    f"🎉 **خرید شما با موفقیت انجام شد!**\n\n"
                    f"🔹 **سرویس:** {cat_info['title']}\n"
                    f"📦 **حجم:** {pkg_name}\n"
                    f"⏳ **زمان:** {month_title}\n"
                    f"💳 **مبلغ کسر شده:** {price:,} تومان\n\n"
                    "👇 **لینک اتصال شما:**\n"
                    f"`{config_text}`\n\n"
                    "💡 برای مشاهده و مدیریت اشتراک خود می‌توانید از بخش «📦 اشتراک‌های من» اقدام کنید."
                )
                markup = InlineKeyboardMarkup(row_width=1)
                markup.add(InlineKeyboardButton("📦 اشتراک‌های من", callback_data="my_subs"))
                markup.add(InlineKeyboardButton("بازگشت به منوی اصلی 🔙", callback_data="main"))
                bot.edit_message_text(success_text, chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")