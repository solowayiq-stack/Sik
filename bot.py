import time
import threading
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = '8949626248:AAGqNFnXWKYRiDmrLFoaklyGnDPItM6kBFo'
ADMIN_ID = 8898807224

bot = telebot.TeleBot(TOKEN)

# ساخت یک وب‌سرور فیک برای گول زدن رندر
app = Flask('')

@app.route('/')
def home():
    return "Bot is active and running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

# دیکشنری‌ها برای ذخیره موقت وضعیت و اطلاعات کاربر
user_states = {}
user_data = {}

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

@bot.message_handler(func=lambda message: message.from_user.id in user_states)
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
            markup.row(InlineKeyboardButton("✍️ اعلام قیمت به کاربر", callback_data=f"setprice_{user_id}"))
            
            bot.send_message(
                ADMIN_ID,
                f"🚨 **درخواست خرید جدید!**\n\n"
                f"👤 کاربر: `{user_id}`\n"
                f"📦 حجم: *{gb} گیگ*\n"
                f"📅 مدت زمان: *{days} روز*\n\n"
                f"لطفاً مبلغ رو محاسبه کن و به کاربر اعلام کن:",
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
        f"مبلغ نهایی (به تومان) رو برای کاربر با آیدی `{user_id}` همینجا به صورت عدد بفرست:",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, send_price_to_user, user_id)

def send_price_to_user(message, user_id):
    price = message.text.strip()
    target_user_id = int(user_id)
    
    user_data[target_user_id]['price'] = price
    user_states[target_user_id] = "waiting_for_receipt"
    
    bot.send_message(
        target_user_id,
        f"💳 **فاکتور سفارش شما آماده شد!**\n\n"
        f"💰 مبلغ قابل پرداخت: *{price} تومان*\n\n"
        f"لطفاً کارت به کارت کن و **عکس رسید واریزی** رو همینجا بفرست تا پس از تایید، کانفیگ‌ها برات ارسال بشن کاکو:",
        parse_mode="Markdown"
    )
    bot.reply_to(message, f"✅ قیمت {price} تومان برای کاربر ارسال شد.")

@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    
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

@bot.callback_query_handler(func=lambda call: call.data.startswith("accept_") or call.data.startswith("reject_"))
def admin_decision(call):
    data = call.data
    user_id = int(data.split("_")[1])
    
    if data.startswith("accept_"):
        turkey_config = "vless://turkey-config-link-here..."
        germany_config = "vless://germany-config-link-here..."
        
        bot.send_message(
            user_id, 
            f"🎉 **رسید شما تایید شد! ممنون از خریدتون کاکو.**\n\n"
            f"این هم کانفیگ‌های اختصاصی شما (ترکیه و آلمان):\n\n"
            f"🇹🇷 **کانفیگ ترکیه:**\n`{turkey_config}`\n\n"
            f"🇩🇪 **کانفیگ آلمان:**\n`{germany_config}`", 
            parse_mode="Markdown"
        )
        
        user_states.pop(user_id, None)
        user_data.pop(user_id, None)
        
        bot.answer_callback_query(call.id, "کانفیگ‌ها ارسال شدند.")
        bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption="✅ رسید تایید شد و کانفیگ‌ها ارسال گردید.")
        
    elif data.startswith("reject_"):
        bot.send_message(user_id, "❌ متأسفانه رسید واریزی شما تایید نشد کاکو. اگر مشکلی هست با پشتیبانی در ارتباط باش.")
        bot.answer_callback_query(call.id, "رسید رد شد.")
        bot.edit_message_caption(chat_id=call.message.chat.id, message_id=call.message.message_id, caption="❌ این رسید رد شد.")

if __name__ == "__main__":
    # استارت کردن وب‌سرور فیک در پس‌زمینه برای گول زدن رندر
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    # حلقه اصلی ربات تلگرام
    while True:
        try:
            print("Bot is starting with Web Server wrapper...")
            bot.infinity_polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"Error occurred: {e}")
            time.sleep(5)
