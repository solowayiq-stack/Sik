import os
import time
import threading
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = '8949626248:AAGqNFnXWKYRiDmrLFoaklyGnDPItM6kBFo'
ADMIN_ID = 8898807224
DEFAULT_CARD = "6037701684660316"

bot = telebot.TeleBot(TOKEN)

# وب‌سرور برای راضی کردن پورت رندر
app = Flask('')

@app.route('/')
def home():
    return "Bot is active and running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# دیکشنری‌ها برای ذخیره موقت وضعیت و اطلاعات کاربر
user_states = {}
user_data = {}
admin_upload_sessions = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_states[user_id] = "waiting_for_gb"
    user_data[user_id] = {}
    
    bot.send_message(
        message.chat.id, 
        "سلام کاکو! خوش اومدی به ربات تخصصی کانفیگ.\n\n"
        "📦 لطفاً **حجم دلخواه** خود رو بین **۱۰ تا ۶۰۰ گیگابایت** به عدد بنویس (مثلاً: 50):"
    )

@bot.message_handler(func=lambda message: message.from_user.id in user_states and message.from_user.id != ADMIN_ID)
def handle_text_steps(message):
    user_id = message.from_user.id
    state = user_states[user_id]
    text = message.text.strip()
    
    if not text.isdigit():
        bot.reply_to(message, "کاکو فقط عدد وارد کن! دوباره امتحان کن:")
        return
        
    number = int(text)
    
    if state == "waiting_for_gb":
        if 10 <= number <= 600:
            user_data[user_id]['gb'] = number
            user_states[user_id] = "waiting_for_days"
            bot.reply_to(
                message, 
                f"حجم انتخابی: {number} گیگ ✅\n\n"
                f"⏳ حالا **تعداد روز (مدت زمان)** رو بین **۳۰ تا ۱۸۰ روز** وارد کن (مثلاً: 30 یا 90):"
            )
        else:
            bot.reply_to(message, "⚠️ حجم انتخابی باید بین **۱۰ تا ۶۰۰ گیگ** باشه کاکو. دوباره وارد کن:")
            
    elif state == "waiting_for_days":
        if 30 <= number <= 180:
            user_data[user_id]['days'] = number
            user_states[user_id] = "waiting_for_price_announcement"
            
            gb = user_data[user_id]['gb']
            days = number
            
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton("✍️ اعلام قیمت و نام صاحب کارت", callback_data=f"setprice_{user_id}"))
            
            bot.send_message(
                ADMIN_ID,
                f"🚨 **درخواست خرید جدید!**\n\n"
                f"👤 کاربر: `{user_id}`\n"
                f"📦 حجم: *{gb} گیگ*\n"
                f"📅 مدت زمان: *{days} روز*\n\n"
                f"لطفاً دکمه‌ی بالا رو بزن تا قیمت و نام صاحب کارت رو وارد کنی:",
                reply_markup=markup,
                parse_mode="Markdown"
            )
            
            bot.reply_to(
                message, 
                f"✅ مشخصات سفارشت ثبت شد:\n📦 حجم: {gb} گیگ\n📅 مدت: {days} روز\n\n"
                f"⏳ درخواست شما برای ادمین ارسال شد. لطفاً چند دقیقه منتظر بمون تا قیمت نهایی بهت اعلام بشه کاکو!"
            )
        else:
            bot.reply_to(message, "⚠️ مدت زمان باید بین **۳۰ تا ۱۸۰ روز** باشه کاکو. دوباره وارد کن:")

@bot.callback_query_handler(func=lambda call: call.data.startswith("setprice_"))
def ask_admin_for_price(call):
    user_id = call.data.split("_")[1]
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id, 
        f"مبلغ و نام صاحب کارت رو به این شکل بفرست کاکو (اول مبلغ، بعد یک فاصله، بعد نام صاحب کارت):\nمثال:\n`370000 محمد`",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, send_price_to_user, user_id)

def send_price_to_user(message, user_id):
    parts = message.text.strip().split(maxsplit=1)
    price = parts[0]
    holder_name = parts[1] if len(parts) > 1 else "مدیریت"
    
    target_user_id = int(user_id)
    
    user_data[target_user_id]['price'] = price
    user_states[target_user_id] = "waiting_for_receipt"
    
    bot.send_message(
        target_user_id,
        f"💳 **فاکتور سفارش شما آماده شد!**\n\n"
        f"💰 مبلغ قابل پرداخت: *{price} تومان*\n\n"
        f"💳 **شماره کارت مقصد:**\n`{DEFAULT_CARD}`\n"
        f"👤 **به نام:** {holder_name}\n\n"
        f"لطفاً کارت به کارت کن و **عکس رسید واریزی** رو همینجا بفرست تا پس از تایید، کانفیگ‌ها برات ارسال بشن کاکو:",
        parse_mode="Markdown"
    )
    bot.reply_to(message, f"✅ فاکتور شامل مبلغ {price} تومان و به نام «{holder_name}» برای کاربر ارسال شد.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    if user_id == ADMIN_ID:
        # اگر ادمین خودش توی چت عکس فرستاد و در حال آپلود فایل کانفیگ بود
        if ADMIN_ID in admin_upload_sessions:
            session = admin_upload_sessions[ADMIN_ID]
            session['files'].append(('photo', message.photo[-1].file_id, message.caption))
            bot.reply_to(message, f"📁 فایل/عکس کانفیگ اضافه شد. (تعداد کل: {len(session['files'])})\nاگر فایل دیگه‌ای نداری، دستور /done رو بفرست تا ارسال بشن.")
        return
        
    if user_states.get(user_id) != "waiting_for_receipt":
        bot.reply_to(message, "کاکو اول /start رو بزن و مراحل رو طی کن!")
        return
        
    data = user_data.get(user_id, {})
    gb = data.get('gb', '؟')
    days = data.get('days', '؟')
    price = data.get('price', '؟')
    
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ تایید و ارسال کانفیگ‌ها", callback_data=f"accept_{user_id}"),
        InlineKeyboardButton("❌ رد رسید", callback_data=f"reject_{user_id}")
    )
    
    bot.send_photo(
        ADMIN_ID, 
        message.photo[-1].file_id, 
        caption=f"📩 **رسید واریزی جدید!**\n\n"
                f"👤 کاربر: `{user_id}`\n"
                f"📦 حجم: *{gb} گیگ* | 📅 مدت: *{days} روز*\n"
                f"💰 مبلغ: *{price} تومان*\n\n"
                f"لطفاً رسید رو بررسی کن:",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    
    bot.reply_to(message, "⏳ رسید شما دریافت شد. در حال بررسی توسط مدیریت...")

# هندلر برای دریافت فایل‌های سندی (Document) از طرف ادمین
@bot.message_handler(content_types=['document'])
def handle_admin_document(message):
    if message.from_user.id == ADMIN_ID and ADMIN_ID in admin_upload_sessions:
        session = admin_upload_sessions[ADMIN_ID]
        session['files'].append(('document', message.document.file_id, message.caption))
        bot.reply_to(message, f"📁 فایل کانفیگ دریافت شد. (تعداد کل: {len(session['files'])})\nبرای اتمام و ارسال به کاربر، دستور /done رو بفرست.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("accept_") or call.data.startswith("reject_"))
def admin_decision(call):
    data = call.data
    action, user_id_str = data.split("_")
    user_id = int(user_id_str)
    
    if action == "accept":
        bot.answer_callback_query(call.id, "حالا فایل‌های کانفیگ رو بفرست.")
        admin_upload_sessions[ADMIN_ID] = {
            'target_user': user_id,
            'files': [],
            'msg_id': call.message.message_id
        }
        bot.send_message(
            ADMIN_ID,
            f"📥 **حالت آپلود فایل فعال شد!**\n\n"
            f"الان هر چندتا فایل کانفیگ (سند یا عکس) که می‌خوای پشت سر هم برای کاربر با آیدی `{user_id}` بفرست.\n"
            f"وقتی کار تموم شد، کافیه دستور `/done` رو بفرستی تا همه با هم برای کاربر ارسال بشن.",
            parse_mode="Markdown"
        )
        
    elif action == "reject":
        bot.send_message(user_id, "❌ متأسفانه رسید واریزی شما تایید نشد کاکو. اگر مشکلی هست با پشتیبانی در ارتباط باش.")
        bot.answer_callback_query(call.id, "رسید رد شد.")
        bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption="❌ این رسید رد شد.")

@bot.message_handler(commands=['done'])
def finish_upload(message):
    if message.from_user.id != ADMIN_ID:
        return
        
    if ADMIN_ID not in admin_upload_sessions:
        bot.reply_to(message, "کاکو شما در حال حاضر در حین آپلود کانفیگ نیستی!")
        return
        
    session = admin_upload_sessions[ADMIN_ID]
    user_id = session['target_user']
    files = session['files']
    original_msg_id = session['msg_id']
    
    if not files:
        bot.reply_to(message, "⚠️ هیچ فایلی ارسال نکودی کاکو! حداقل یک فایل بفرست یا با زدن /done لغو کن.")
        return
        
    bot.send_message(
        user_id, 
        f"🎉 **رسید شما تایید شد! ممنون از خریدتون کاکو.**\n\n"
        f"📁 **فایل‌های کانفیگ اختصاصی شما:**"
    )
    
    # ارسال فایل‌ها به کاربر
    for f_type, f_id, f_caption in files:
        if f_type == 'document':
            bot.send_document(user_id, f_id, caption=f_caption)
        elif f_type == 'photo':
            bot.send_photo(user_id, f_id, caption=f_caption)
            
    # پاکسازی وضعیت‌ها
    user_states.pop(user_id, None)
    user_data.pop(user_id, None)
    admin_upload_sessions.pop(ADMIN_ID, None)
    
    bot.reply_to(message, "✅ تمامی فایل‌های کانفیگ با موفقیت برای کاربر ارسال شدند!")
    try:
        bot.edit_message_caption(
            chat_id=ADMIN_ID, 
            message_id=original_msg_id, 
            caption="✅ رسید تایید شد و فایل‌های کانفیگ برای کاربر ارسال گردید."
        )
    except Exception:
        pass

if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    while True:
        try:
            print("Bot is starting with file upload support...")
            bot.infinity_polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"Error occurred: {e}")
            time.sleep(5)
