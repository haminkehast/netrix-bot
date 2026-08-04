# wallet.py
import random
import time
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CopyTextButton
from keyboards import get_main_markup, get_back_markup
import database
from config import LOG_GROUP_ID, LOG_TOPIC_ID

pending_payments = {}

def register_wallet_handlers(bot):

    def remind_invoice(chat_id, invoice_time):
        if pending_payments.get(chat_id) == invoice_time:
            remind_text = "⚠️ **کاربر گرامی، تنها ۲ دقیقه تا انقضای فاکتور شما باقی مانده است.**\nلطفاً هرچه سریع‌تر عکس یا متن رسید خود را ارسال کنید."
            try: bot.send_message(chat_id, remind_text, parse_mode="Markdown")
            except: pass

    def expire_invoice(chat_id, invoice_time):
        if pending_payments.get(chat_id) == invoice_time:
            pending_payments.pop(chat_id, None)
            bot.clear_step_handler_by_chat_id(chat_id)
            expire_text = (
                "⏳ **مهلت پرداخت به پایان رسید!**\n\n"
                "کاربر گرامی، مهلت ۱۰ دقیقه‌ای فاکتور شما به اتمام رسید و این شناسه منقضی شد.\n"
                "❌ لطفاً دیگر به این شناسه مبلغی واریز نکنید.\n\n"
                "در صورت نیاز به شارژ کیف پول، لطفاً مجدداً فاکتور جدید دریافت کنید."
            )
            try: bot.send_message(chat_id, expire_text, reply_markup=get_main_markup(chat_id), parse_mode="Markdown")
            except: pass

    def wait_for_receipt(message, base_amount, final_amount_toman):
        chat_id = message.chat.id
        
        if message.text == '/start':
            pending_payments.pop(chat_id, None)
            bot.clear_step_handler_by_chat_id(chat_id)
            bot.send_message(chat_id, "بازگشت به منوی اصلی 🏠", reply_markup=get_main_markup(chat_id))
            return

        if chat_id not in pending_payments:
            bot.clear_step_handler_by_chat_id(chat_id)
            bot.send_message(chat_id, "⚠️ مهلت پرداخت این فاکتور تمام شده است. لطفاً از منو فاکتور جدید دریافت کنید.", reply_markup=get_main_markup(chat_id))
            return

        if not message.photo and not message.text:
            bot.send_message(chat_id, "⚠️ لطفاً فقط **عکس رسید** یا **شماره پیگیری (متن)** را ارسال کنید. مجدداً تلاش کنید:", parse_mode="Markdown")
            bot.register_next_step_handler_by_chat_id(chat_id, wait_for_receipt, base_amount, final_amount_toman)
            return
            
        pending_payments.pop(chat_id, None)
        
        username = f"@{message.from_user.username}".replace("_", "\\_") if message.from_user.username else "ندارد"
        
        is_vip = False
        try:
            user_stats = database.get_user_stats(chat_id)
            if user_stats and user_stats.get('total_spent', 0) >= 1000000:
                is_vip = True
        except: pass
            
        vip_tag = "🚨 🌟 **[ درخواست ویژه از کاربر VIP ]** 🌟 🚨" if is_vip else ""
        
        admin_text = (
            f"🧾 **رسید جدید برای بررسی**\n{vip_tag}\n\n"
            f"👤 آیدی کاربر: `{chat_id}`\n"
            f"🏖 یوزرنیم: {username}\n"
            f"💰 مبلغ پایه (درخواستی): **{base_amount:,}** تومان\n"
            f"🔢 مبلغ واریز شده (با شناسه): **{final_amount_toman:,}** تومان\n"
        )
        
        admin_markup = InlineKeyboardMarkup(row_width=2)
        admin_markup.add(
            InlineKeyboardButton("✅ تایید و شارژ", callback_data=f"verify_{chat_id}_{base_amount}"),
            InlineKeyboardButton("❌ رد رسید", callback_data=f"reject_{chat_id}")
        )
        
        try:
            if message.photo:
                file_id = message.photo[-1].file_id
                bot.send_photo(LOG_GROUP_ID, file_id, caption=admin_text, reply_markup=admin_markup, message_thread_id=LOG_TOPIC_ID, parse_mode="Markdown")
            else:
                full_admin_text = admin_text + f"\n📝 **متن ارسالی کاربر (شماره پیگیری):**\n`{message.text}`"
                bot.send_message(LOG_GROUP_ID, full_admin_text, reply_markup=admin_markup, message_thread_id=LOG_TOPIC_ID, parse_mode="Markdown")
            
            success_text = (
                "🎉 **رسید شما با موفقیت دریافت شد!**\n\n"
                "⏳ همکاران ما در حال بررسی واریزی شما هستند. به محض تأیید، کیف پولتان به صورت خودکار شارژ شده و پیام آن از همینجا برایتان ارسال می‌شود.\n\n"
                "از همراهی و شکیبایی شما سپاسگزاریم 🌹"
            )
            bot.send_message(chat_id, success_text, reply_markup=get_main_markup(chat_id), parse_mode="Markdown")
            
        except Exception as e:
            print(f"❌ ارور در ارسال رسید به پشتیبانی: {e}")
            error_markup = InlineKeyboardMarkup()
            error_markup.add(InlineKeyboardButton("ارتباط با پشتیبانی ☎️", url="https://t.me/NetrixVIPSupport"))
            bot.send_message(chat_id, "⚠️ خطایی در سیستم رخ داد.\nلطفاً مستقیماً به پشتیبانی پیام دهید:", reply_markup=error_markup)

    def send_payment_details(chat_id, message_id, base_amount, is_edit=True):
        random_id = random.randint(100, 999)
        final_amount_toman = base_amount + random_id
        final_amount_rial = final_amount_toman * 10
        card_number = "5022291588054823"
        
        text = (
            f"💳 **درخواست شارژ کیف پول**\n\n"
            f"💰 مبلغ به تومان: `{final_amount_toman}`\n"
            f"💰 مبلغ به ریال: `{final_amount_rial}`\n\n"
            f"لطفاً مبلغ فوق را به شماره کارت زیر واریز کنید:\n\n"
            f"💳 شماره کارت: `{card_number}`\n"
            f"👤 به نام: **آقای حیدری**\n\n"
            f"⚠️ **توجه:** 3 رقم پایانی این مبلغ، شناسه اختصاصی تراکنش شما برای شناسایی و تأیید خودکار پرداخت سریع است، بنابراین مبلغ باید دقیقاً مطابق عدد اعلام‌شده واریز شود.\n\n"
            f"❌ در صورت واریز مبلغ بیشتر، کمتر یا رُند، سیستم قادر به شناسایی خودکار تراکنش نخواهد بود و برای بررسی و تأیید، نیاز به هماهنگی با پشتیبانی خواهید داشت.\n\n"
            f"⚡️ رسید شما بلافاصله پس از ارسال، در **کمتر از ۱ دقیقه** بررسی و کیف پولتان شارژ خواهد شد.\n\n"
            f"⏳ **شناسه این فاکتور تنها ۱۰ دقیقه اعتبار دارد.**\n\n"
            f"📸 پس از واریز، لطفاً **عکس رسید (اسکرین‌شات)** یا **شماره پیگیری تراکنش (متن)** را همینجا ارسال کنید."
        )
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("مبلغ تومان", copy_text=CopyTextButton(text=str(final_amount_toman))),
            InlineKeyboardButton("مبلغ ریال", copy_text=CopyTextButton(text=str(final_amount_rial)))
        )
        markup.add(InlineKeyboardButton("شماره کارت", copy_text=CopyTextButton(text=card_number)))
        markup.add(InlineKeyboardButton("لغو و بازگشت 🔙", callback_data="wallet"))
        
        try:
            if is_edit:
                bot.delete_message(chat_id, message_id)
                
            file_id = "AgACAgQAAxkBAAEhMGxqb3Ga8mkc7r3BXjfnagcP37_gBgACOg1rG7nygVMytvphPbV2twEAAwIAA3kAAz0E"
            bot.send_photo(chat_id, file_id, caption=text, parse_mode="Markdown", reply_markup=markup)
            
            invoice_time = time.time()
            pending_payments[chat_id] = invoice_time
            threading.Timer(480.0, remind_invoice, args=[chat_id, invoice_time]).start()
            threading.Timer(600.0, expire_invoice, args=[chat_id, invoice_time]).start()
            
        except Exception as e:
            print(f"❌ ارور: {e}")
            bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)
            
        bot.register_next_step_handler_by_chat_id(chat_id, wait_for_receipt, base_amount, final_amount_toman)

    def process_wallet_charge(message):
        chat_id = message.chat.id
        try:
            amount = int(message.text.replace(",", ""))
            if amount < 10000:
                bot.send_message(chat_id, "⚠️ حداقل مبلغ شارژ 10,000 تومان است.", reply_markup=get_main_markup(chat_id))
                return
            send_payment_details(chat_id, message.message_id, amount, is_edit=False)
        except ValueError:
            bot.send_message(chat_id, "⚠️ لطفاً مبلغ را عدد وارد کنید.", reply_markup=get_main_markup(chat_id))

    @bot.callback_query_handler(func=lambda call: call.data in ["wallet", "charge_wallet", "charge_custom"] or call.data.startswith("fastcharge_") or call.data.startswith("verify_") or call.data.startswith("reject_"))
    def wallet_callbacks(call):
        chat_id = call.message.chat.id
        msg_id = call.message.message_id
        data = call.data
        user_id = call.from_user.id if hasattr(call, 'from_user') else call.from_user.id
        
        try: bot.clear_step_handler_by_chat_id(chat_id)
        except: pass

        if data == "wallet":
            balance = database.get_balance(user_id)
            text = f"💳 **کیف پول من**\n\n💰 موجودی فعلی: **{balance:,}** تومان\n\nجهت افزایش موجودی کلیک کنید."
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton("شارژ کیف پول 💵", callback_data="charge_wallet"))
            markup.add(InlineKeyboardButton("بازگشت 🔙", callback_data="main"))
            bot.edit_message_text(text, chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")
            
        elif data == "charge_wallet":
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(InlineKeyboardButton("50,000 تومان", callback_data="fastcharge_50000"), InlineKeyboardButton("100,000 تومان", callback_data="fastcharge_100000"))
            markup.add(InlineKeyboardButton("150,000 تومان", callback_data="fastcharge_150000"), InlineKeyboardButton("200,000 تومان", callback_data="fastcharge_200000"))
            markup.add(InlineKeyboardButton("250,000 تومان", callback_data="fastcharge_250000"), InlineKeyboardButton("300,000 تومان", callback_data="fastcharge_300000"))
            markup.add(InlineKeyboardButton("مبلغ دلخواه ✍️", callback_data="charge_custom"))
            markup.add(InlineKeyboardButton("بازگشت 🔙", callback_data="wallet"))
            bot.edit_message_text("💵 یکی از مبالغ زیر را انتخاب کنید:", chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")

        elif data.startswith("fastcharge_"):
            amount = int(data.split("_")[1])
            send_payment_details(chat_id, msg_id, amount, is_edit=True)

        elif data == "charge_custom":
            msg = bot.edit_message_text("💵 لطفاً مبلغ مورد نظر خود را جهت شارژ به تومان وارد کنید\n(حداقل 10,000 تومان):", chat_id, msg_id, reply_markup=get_back_markup("charge_wallet"))
            bot.register_next_step_handler_by_chat_id(chat_id, process_wallet_charge)

        elif data.startswith("verify_"):
            parts = data.split("_")
            target_user = int(parts[1])
            base_amount = int(parts[2])
            charge_amount = base_amount + 1000
            
            database.update_balance(target_user, charge_amount)
            
            # حل باگ تایید رسید متنی یا عکسی و نمایش دائمی آیدی
            success_msg = f"✅ این رسید تایید و مبلغ {charge_amount:,} تومان به کیف پول کاربر اضافه شد.\n👤 آیدی کاربر: `{target_user}`"
            try:
                if call.message.content_type == 'photo':
                    bot.edit_message_caption(success_msg, chat_id=chat_id, message_id=msg_id)
                else:
                    bot.edit_message_text(success_msg, chat_id=chat_id, message_id=msg_id)
            except: pass
            
            try: bot.send_message(target_user, f"🎉 واریزی شما تایید و مبلغ **{charge_amount:,}** تومان به کیف پول اضافه شد.", parse_mode="Markdown")
            except: pass

        elif data.startswith("reject_"):
            target_user = int(data.split("_")[1])
            
            # حل باگ رد رسید متنی یا عکسی و نمایش دائمی آیدی
            reject_msg = f"❌ این رسید رد شد.\n👤 آیدی کاربر: `{target_user}`"
            try:
                if call.message.content_type == 'photo':
                    bot.edit_message_caption(reject_msg, chat_id=chat_id, message_id=msg_id)
                else:
                    bot.edit_message_text(reject_msg, chat_id=chat_id, message_id=msg_id)
            except: pass
            
            # اضافه شدن دکمه پشتیبانی به پیام کاربر
            error_markup = InlineKeyboardMarkup()
            error_markup.add(InlineKeyboardButton("ارتباط با پشتیبانی ☎️", url="https://t.me/NetrixVIPSupport"))
            try: bot.send_message(target_user, "⚠️ کاربر گرامی، متاسفانه رسید شما توسط پشتیبانی تایید نشد.\nجهت پیگیری، مستقیماً به پشتیبانی پیام دهید.", reply_markup=error_markup)
            except: pass
            
            # اضافه شدن دکمه پشتیبانی به پیام کاربر
            error_markup = InlineKeyboardMarkup()
            error_markup.add(InlineKeyboardButton("ارتباط با پشتیبانی ☎️", url="https://t.me/NetrixVIPSupport"))
            try: bot.send_message(target_user, "⚠️ کاربر گرامی، متاسفانه رسید شما توسط پشتیبانی تایید نشد.\nجهت پیگیری، مستقیماً به پشتیبانی پیام دهید.", reply_markup=error_markup)
            except: pass