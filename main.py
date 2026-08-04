# main.py
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN
import database
from keyboards import get_main_markup
from telebot.types import ReplyKeyboardRemove

# فراخوانی ماژول‌های جداگانه
import wallet
import shop
import user_panel 
import subscriptions  
import admin_inventory  
import admin_panel

bot = telebot.TeleBot(BOT_TOKEN)

# ثبت دکمه‌ها و قابلیت‌های هر فایل در ربات
wallet.register_wallet_handlers(bot)
shop.register_shop_handlers(bot)
user_panel.register_user_panel_handlers(bot)  # این خط را اضافه کنید
subscriptions.register_subscriptions_handlers(bot)
admin_inventory.register_admin_inventory_handlers(bot)
admin_panel.register_admin_handlers(bot)

# ================= تنظیمات امنیتی و دسترسی =================
# آیدی عددی شما برای دسترسی به پنل مدیریت (می‌توانید با کاما آیدی‌های دیگر را اضافه کنید)
ADMINS = [7268118800,1953060486]
CHANNEL_ID = "@NetrixVIP"

def is_joined(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        if status in ['member', 'administrator', 'creator']:
            return True
        return False
    except Exception as e:
        # اگر ربات ادمین کانال نباشد، برای جلوگیری از قفل شدن، دسترسی باز می‌ماند
        print(f"Channel Check Error: {e}")
        return True 

def join_required_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📢 عضویت در کانال NETRIX", url=f"https://t.me/{CHANNEL_ID[1:]}"))
    markup.add(InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_join"))
    return markup

# ================= بخش استارت و منوی اصلی =================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    try: bot.clear_step_handler_by_chat_id(user_id)
    except: pass
    
    safe_name = message.from_user.first_name if message.from_user.first_name else "کاربر"
    try: database.add_user(user_id, name=safe_name)
    except: pass
    
    # بررسی عضویت اجباری
    if not is_joined(user_id):
        join_text = (
            "🌟 **همراه گرامی، درود!**\n\n"
            "جهت استفاده از خدمات سیستم هوشمند **NETRIX**، مطلع شدن از آخرین اخبار و دریافت تخفیف‌ها، لطفاً ابتدا در کانال رسمی ما عضو شوید.\n\n"
            "👇 پس از عضویت، روی دکمه «بررسی عضویت» کلیک کنید:"
        )
        bot.send_message(user_id, join_text, reply_markup=join_required_markup(), parse_mode="Markdown")
        return
    
    text = (
        "🌟 **درود بر شما همراه گرامی!**\n\n"
        "به سیستم هوشمند و یکپارچه **NETRIX** خوش آمدید. 🚀\n"
        "لطفاً از منوی زیر جهت مدیریت سرویس‌های خود استفاده کنید:"
    )
    bot.send_message(user_id, text, reply_markup=get_main_markup(user_id), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join_callback(call):
    user_id = call.from_user.id
    if is_joined(user_id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        text = (
            "🌟 **درود بر شما همراه گرامی!**\n\n"
            "به سیستم هوشمند و یکپارچه **NETRIX** خوش آمدید. 🚀\n"
            "لطفاً از منوی زیر جهت مدیریت سرویس‌های خود استفاده کنید:"
        )
        bot.send_message(user_id, text, reply_markup=get_main_markup(user_id), parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "⚠️ شما هنوز در کانال عضو نشده‌اید! لطفاً ابتدا عضو شوید.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "main")
def back_to_main(call):
    user_id = call.from_user.id
    if not is_joined(user_id):
        bot.answer_callback_query(call.id, "⚠️ لطفاً ابتدا در کانال عضو شوید.", show_alert=True)
        return
        
    text = (
        "🌟 **درود بر شما همراه گرامی!**\n\n"
        "به سیستم هوشمند و یکپارچه **NETRIX** خوش آمدید. 🚀\n"
        "لطفاً از منوی زیر جهت مدیریت سرویس‌های خود استفاده کنید:"
    )
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=get_main_markup(user_id), parse_mode="Markdown")


# ================= بخش پنل مدیریت کاملاً امن =================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    # مسدود کردن دسترسی برای افرادی که ادمین نیستند
    if message.chat.id not in ADMINS:
        return 
        
    bot.clear_step_handler_by_chat_id(message.chat.id)
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💵 شارژ / کسر دستی کیف پول", callback_data="admin_wallet_action"))
    bot.send_message(message.chat.id, "⚙️ **پنل مدیریت هوشمند NETRIX**\n\nلطفاً یک گزینه را انتخاب کنید:", reply_markup=markup, parse_mode="Markdown")

# مدیریت تمام دکمه‌های مربوط به پنل ادمین
@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def admin_callbacks(call):
    user_id = call.from_user.id
    
    # یک لایه امنیتی مضاعف برای دکمه‌های شیشه‌ای
    if user_id not in ADMINS:
        bot.answer_callback_query(call.id, "⛔️ شما دسترسی مدیریت ندارید!", show_alert=True)
        return
        
    if call.data == "admin_main":
        bot.clear_step_handler_by_chat_id(user_id)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💵 شارژ / کسر دستی کیف پول", callback_data="admin_wallet_action"))
        bot.edit_message_text("⚙️ **پنل مدیریت هوشمند NETRIX**\n\nلطفاً یک گزینه را انتخاب کنید:", user_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        
    elif call.data == "admin_wallet_action":
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("➕ افزایش موجودی", callback_data="admin_wallet_add"),
            InlineKeyboardButton("➖ کسر موجودی", callback_data="admin_wallet_sub")
        )
        markup.add(InlineKeyboardButton("🔙 بازگشت", callback_data="admin_main"))
        bot.edit_message_text("💰 **بخش مدیریت مالی**\n\nقصد انجام چه کاری را دارید؟", user_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        
    elif call.data in ["admin_wallet_add", "admin_wallet_sub"]:
        action = "افزایش ➕" if call.data == "admin_wallet_add" else "کسر ➖"
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data="admin_main"))
        
        text = f"شما بخش **{action}** را انتخاب کردید.\n\n👤 لطفاً **آیدی عددی** کاربری که قصد تغییر موجودی او را دارید بفرستید:"
        msg = bot.edit_message_text(text, user_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(msg, admin_wallet_step2, call.data)

def admin_wallet_step2(message, action_type):
    chat_id = message.chat.id
    if chat_id not in ADMINS: return
    
    # جلوگیری از تداخل دستورات
    if message.text and message.text.startswith('/'):
        bot.clear_step_handler_by_chat_id(chat_id)
        if message.text == '/start': send_welcome(message)
        elif message.text == '/admin': admin_panel(message)
        return
        
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data="admin_main"))
    
    if not message.text:
        msg = bot.send_message(chat_id, "⚠️ لطفاً فقط **آیدی عددی** ارسال کنید.\nمجدداً تلاش کنید:", reply_markup=markup)
        bot.register_next_step_handler(msg, admin_wallet_step2, action_type)
        return
        
    target_id = message.text.strip()
    if not target_id.isdigit():
        msg = bot.send_message(chat_id, "⚠️ **خطا:** آیدی وارد شده باید فقط شامل اعداد باشد.\nمجدداً تلاش کنید:", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(msg, admin_wallet_step2, action_type)
        return
        
    action_text = "افزایش" if action_type == "admin_wallet_add" else "کسر"
    msg = bot.send_message(chat_id, f"💰 **مرحله آخر:**\nمبلغ مورد نظر برای **{action_text}** به تومان را وارد کنید:", reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler_by_chat_id(chat_id, admin_wallet_step3, target_id, action_type)

def admin_wallet_step3(message, target_id, action_type):
    chat_id = message.chat.id
    if chat_id not in ADMINS: return
    
    if message.text and message.text.startswith('/'):
        bot.clear_step_handler_by_chat_id(chat_id)
        if message.text == '/start': send_welcome(message)
        elif message.text == '/admin': admin_panel(message)
        return
        
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data="admin_main"))
    
    if not message.text:
        msg = bot.send_message(chat_id, "⚠️ لطفاً فقط **عدد** ارسال کنید.\nمجدداً تلاش کنید:", reply_markup=markup)
        bot.register_next_step_handler(msg, admin_wallet_step3, target_id, action_type)
        return

    amount_str = message.text.replace(",", "").strip()
    if not amount_str.isdigit():
        msg = bot.send_message(chat_id, "⚠️ **خطا:** مبلغ باید فقط عدد باشد.\nمجدداً تلاش کنید:", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(msg, admin_wallet_step3, target_id, action_type)
        return
        
    amount = int(amount_str)
    if action_type == "admin_wallet_sub":
        amount = -amount
        
    try:
        database.update_balance(int(target_id), amount)
        action_done = "شارژ" if amount > 0 else "کسر"
        bot.send_message(chat_id, f"✅ **عملیات با موفقیت انجام شد!**\n\n👤 آیدی کاربر: `{target_id}`\n💰 وضعیت: {action_done}\n💵 مبلغ: **{abs(amount):,}** تومان", parse_mode="Markdown")
        
        # بازگشت اتوماتیک به پنل اصلی بعد از اتمام موفق کار
        main_markup = InlineKeyboardMarkup()
        main_markup.add(InlineKeyboardButton("💵 شارژ / کسر دستی کیف پول", callback_data="admin_wallet_action"))
        bot.send_message(chat_id, "⚙️ **پنل مدیریت هوشمند NETRIX**\n\nلطفاً یک گزینه را انتخاب کنید:", reply_markup=main_markup, parse_mode="Markdown")

        # ارسال نوتیفیکیشن به کاربر
        try:
            if amount > 0:
                bot.send_message(int(target_id), f"🎉 کاربر گرامی، حساب کاربری شما توسط مدیریت به مبلغ **{abs(amount):,}** تومان شارژ شد.", parse_mode="Markdown")
            else:
                bot.send_message(int(target_id), f"⚠️ کاربر گرامی، مبلغ **{abs(amount):,}** تومان توسط مدیریت از حساب شما کسر گردید.", parse_mode="Markdown")
        except: pass
        
    except Exception as e:
        bot.send_message(chat_id, f"❌ **خطای سیستم:**\n{e}", parse_mode="Markdown")

@bot.message_handler(commands=['clean'])
def clean_menu(message):
    bot.send_message(message.chat.id, "منوهای مزاحم پاک شدند! 🧹", reply_markup=ReplyKeyboardRemove())

    # ================= دستور موقت برای تست خرید =================
@bot.message_handler(commands=['testbuy'])
def test_buy_command(message):
    user_id = message.from_user.id
    conn = database.sqlite3.connect('netrix.db')
    cursor = conn.cursor()
    
    # پیدا کردن اولین کانفیگ آزاد در انبار
    cursor.execute('SELECT id FROM configs WHERE status = "available" LIMIT 1')
    config = cursor.fetchone()
    
    if config:
        config_id = config[0]
        # سند زدن کانفیگ به نام ادمین
        cursor.execute('UPDATE configs SET status = "sold", owner_id = ? WHERE id = ?', (user_id, config_id))
        conn.commit()
        bot.reply_to(message, f"🎉 تبریک! کانفیگ شماره `{config_id}` با موفقیت به نام شما سند خورد.\n\n👇 حالا برو از منوی اصلی دکمه **اشتراک‌های من 📦** رو بزن تا شاهکارت رو ببینی!")
    else:
        bot.reply_to(message, "❌ انبار خالیه! اول برو از پنل ادمین (دکمه انبار کانفیگ‌ها) چند تا لینک سابسکریپشن اضافه کن.")
        
    conn.close()
# ========================================================

if __name__ == "__main__":
    # این خط جا مونده بود که باید دیتابیس رو آپدیت کنه
    database.init_db() 
    
    print("🚀 ربات NETRIX با ساختار ماژولار روشن شد...")
    bot.infinity_polling()
    